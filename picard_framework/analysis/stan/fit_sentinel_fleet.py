"""Fit the fleet sentinel model (pooled port hazards, fleet-time, crew repeats).

Usage::

    python3 -m picard_framework.analysis.stan.fit_sentinel_fleet \\
      picard_framework/analysis/sentinel/data/example_fleet.json \\
      --out sentinel_fleet_fit

The manifest lists the voyages to pool::

    {"voyages": [{"itinerary": "...json", "observations": "...json"}, ...]}

Paths are resolved relative to the manifest, so a fleet manifest can sit beside
the itineraries it names.

``--engine numpy`` (the default when CmdStan is absent) samples the same density
with the reference walker in ``_sentinel_fleet_reference``, so the whole path —
manifest to pooled hazard CSV — is exercised without a Stan toolchain. Unlike the
single-ship runner there is no committed fixture posterior: a fleet posterior is
only readable next to the fleet that produced it, and a manifest is cheap to
resample.
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from typing import Any, Sequence

from picard_framework.analysis._io import (
    allowed_roots,
    ensure_out_dir,
    read_json,
    write_csv,
    write_json,
)
from picard_framework.analysis.sentinel.exposure import (
    ascertainment_fraction,
    build_exposure_design,
)
from picard_framework.analysis.sentinel.fleet import (
    FLEET_HAZARD_COLUMNS,
    VISIT_HAZARD_COLUMNS,
    crew_exposure_summary,
    fleet_hazard_rows,
    fleet_onboard_summary,
    fleet_time_summary,
    summarize_fleet_hazards,
    summarize_visit_hazards,
    visit_hazard_rows,
    wastewater_summary,
)
from picard_framework.analysis.sentinel.incubation import (
    default_pathogen,
    delays_for_pathogen,
)
from picard_framework.analysis.sentinel.itinerary import load_voyage
from picard_framework.analysis.sentinel.observations import (
    load_observation_bundle,
    validate_against_voyage,
)
from picard_framework.analysis.stan._data import cmdstan_available
from picard_framework.analysis.stan._sampler_options import SamplerOptions
from picard_framework.analysis.stan._sentinel_fleet_data import (
    FleetPriors,
    FleetVoyage,
    WastewaterOptions,
    build_sentinel_fleet_data,
)
from simulation_utils.paths import validated_open

_FIT_STATUS_JSON = "fit_status.json"
_STAN_FILE = "sentinel_fleet.stan"
_FLEET_TIME_COLUMNS = (
    "week",
    "log_effect_mean",
    "log_effect_q05",
    "log_effect_q95",
    "hazard_multiplier_mean",
)
_SMOKE_DRAWS = 60
_SMOKE_WARMUP = 200


def stan_model_path() -> str:
    """Absolute path to the fleet model source."""
    return os.path.join(os.path.dirname(__file__), _STAN_FILE)


def load_fleet_manifest(path: str) -> list[tuple[str, str]]:
    """``[(itinerary, observations), ...]`` from a fleet manifest.

    Relative entries resolve against the manifest's directory: the manifest is
    the fleet definition, and a fleet whose meaning depends on the caller's
    working directory is not reproducible.
    """
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"fleet manifest must be an object: {path}")
    entries = payload.get("voyages")
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"fleet manifest lists no voyages: {path}")
    base = os.path.dirname(os.path.abspath(path))

    def resolve(value: Any, field: str, index: int) -> str:
        if not isinstance(value, str) or not value:
            raise ValueError(f"voyage {index} in {path} has no {field}")
        return value if os.path.isabs(value) else os.path.join(base, value)

    pairs: list[tuple[str, str]] = []
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"voyage {i} in {path} is not an object")
        pairs.append(
            (
                resolve(entry.get("itinerary"), "itinerary", i),
                resolve(entry.get("observations"), "observations", i),
            ),
        )
    return pairs


def load_fleet_voyages(
    pairs: Sequence[tuple[str, str]],
    *,
    reporting: float = 1.0,
    care_seeking: float = 1.0,
    testing: float = 1.0,
    pathogen: str | None = None,
) -> tuple[list[FleetVoyage], str]:
    """Build one ``FleetVoyage`` per pair, refusing itinerary/observation mismatch."""
    resolved = pathogen or default_pathogen()
    voyages: list[FleetVoyage] = []
    ascertainment = ascertainment_fraction(
        reporting=reporting, care_seeking=care_seeking, testing=testing,
    )
    for itinerary_path, observations_path in pairs:
        bundle = load_observation_bundle(observations_path)
        voyage = load_voyage(
            itinerary_path,
            voyage_id=bundle.voyage_id,
            ship_id=bundle.ship_id,
            n_passengers=bundle.n_passengers,
            n_crew=bundle.n_crew,
            platform_class=bundle.platform_class,
            observation_end_epoch=bundle.observation_end_epoch,
        )
        problems = validate_against_voyage(bundle, voyage)
        if problems:
            raise ValueError(
                f"observations do not match the itinerary ({observations_path}):\n"
                + "\n".join(problems),
            )
        incubation, _ = delays_for_pathogen(
            resolved, epoch_hours=voyage.epoch_duration_hours,
        )
        voyages.append(
            FleetVoyage(
                design=build_exposure_design(
                    voyage, bundle, incubation, ascertainment=ascertainment,
                ),
                voyage=voyage,
                bundle=bundle,
            ),
        )
    return voyages, resolved


def _write_draws_csv(fit: Any, path: str) -> None:
    try:
        buf = io.StringIO()
        fit.draws_pd().to_csv(buf, index=False)
        with validated_open(
            path, "w", allowed_roots=allowed_roots(), encoding="utf-8",
        ) as fh:
            fh.write(buf.getvalue())
    except Exception as exc:
        print(f"warn: could not write draws: {exc}", file=sys.stderr)


def _posterior_from_fit(fit: Any) -> dict[str, list[float]]:
    draws = fit.draws_pd()
    return {str(col): [float(v) for v in draws[col]] for col in draws.columns}


def write_fleet_outputs(
    out: str,
    posterior: dict[str, list[float]],
    meta: dict[str, Any],
    pathogen: str,
) -> dict[str, Any]:
    """Pooled, per-visit, fleet-time, onboard, and crew summaries to ``out``."""
    ports = summarize_fleet_hazards(posterior, meta, pathogen=pathogen)
    write_csv(
        os.path.join(out, "fleet_port_hazards.csv"),
        fleet_hazard_rows(ports),
        list(FLEET_HAZARD_COLUMNS),
    )
    visits = summarize_visit_hazards(posterior, meta)
    write_csv(
        os.path.join(out, "visit_hazards.csv"),
        visit_hazard_rows(visits),
        list(VISIT_HAZARD_COLUMNS),
    )
    weeks = fleet_time_summary(posterior, meta)
    write_csv(
        os.path.join(out, "fleet_time.csv"), weeks, list(_FLEET_TIME_COLUMNS),
    )
    onboard = fleet_onboard_summary(posterior, meta)
    write_json(os.path.join(out, "onboard_summary.json"), onboard)
    crew = crew_exposure_summary(posterior)
    write_json(os.path.join(out, "crew_exposure.json"), crew)
    wastewater = wastewater_summary(posterior, meta)
    write_json(os.path.join(out, "wastewater_channel.json"), wastewater)
    return {
        "n_ports": len(ports),
        "n_visits": len(visits),
        "n_weeks": len(weeks),
        "onboard": onboard,
        "crew": crew,
        "wastewater": wastewater,
        "hazard_mean": {p.port_id: p.hazard_mean for p in ports},
        "fleet_time_confounded": sorted(
            p.port_id for p in ports if p.fleet_time_confounded
        ),
    }


def _resolve_engine(engine: str, *, smoke: bool) -> str:
    """``stan`` or ``numpy``; a smoke run is always the reference walker."""
    if smoke:
        return "numpy"
    if engine == "auto":
        return "stan" if cmdstan_available() else "numpy"
    return engine


def _warn_unresolved_ports(meta: dict[str, Any]) -> None:
    for voyage_meta in meta["voyages"]:
        if not voyage_meta["port_resolution_adequate"]:
            print(
                f"warn: voyage {voyage_meta['voyage_id']} has an incubation IQR "
                f"({meta['incubation_iqr_hours']} h) that is not shorter than its "
                "inter-port interval; read its ports as a port-window set (spec 1.8)",
                file=sys.stderr,
            )


def _numpy_status(
    data: dict[str, Any],
    meta: dict[str, Any],
    *,
    out: str,
    pathogen: str,
    opts: SamplerOptions,
    smoke: bool,
) -> dict[str, Any]:
    """Sample with the reference walker and summarize, labelled as not a NUTS fit."""
    from picard_framework.analysis.stan._sentinel_fleet_reference import (
        fleet_reference_posterior,
    )

    posterior = fleet_reference_posterior(
        data,
        draws=_SMOKE_DRAWS if smoke else opts.iter_sampling,
        warmup=_SMOKE_WARMUP if smoke else opts.iter_warmup,
        seed=opts.seed,
    )
    return {
        "status": "smoke" if smoke else "ok",
        "engine": "numpy_rw_mh",
        "reason": "reference walker; intervals are indicative, not a NUTS fit",
        "meta": meta,
        "summary": write_fleet_outputs(out, posterior, meta, pathogen),
    }


def _cmdstan_status(
    data: dict[str, Any],
    meta: dict[str, Any],
    *,
    out: str,
    pathogen: str,
    opts: SamplerOptions,
) -> dict[str, Any]:
    """Sample with CmdStan, or report why no posterior was produced."""
    if not cmdstan_available():
        return {
            "status": "skipped",
            "reason": "cmdstanpy/CmdStan not installed; --engine numpy to sample anyway",
            "meta": meta,
        }

    from cmdstanpy import CmdStanModel

    try:
        model = CmdStanModel(stan_file=stan_model_path())
        fit = model.sample(
            data=data,
            chains=opts.chains,
            parallel_chains=opts.chains,
            iter_sampling=opts.iter_sampling,
            iter_warmup=opts.iter_warmup,
            seed=opts.seed,
            show_progress=opts.show_progress,
        )
    except Exception as exc:
        print(f"sentinel fleet fit failed: {exc}", file=sys.stderr)
        return {"status": "error", "reason": str(exc), "meta": meta}

    _write_draws_csv(fit, os.path.join(out, "draws.csv"))
    return {
        "status": "ok",
        "engine": "cmdstan",
        "meta": meta,
        "summary": write_fleet_outputs(
            out, _posterior_from_fit(fit), meta, pathogen,
        ),
    }


def fit_sentinel_fleet(
    manifest_path: str,
    out_dir: str,
    *,
    pathogen: str | None = None,
    reporting: float = 1.0,
    care_seeking: float = 1.0,
    testing: float = 1.0,
    engine: str = "auto",
    sampler: SamplerOptions | None = None,
    smoke: bool = False,
    wastewater: bool = True,
    priors: FleetPriors | None = None,
) -> dict[str, Any]:
    """Assemble the fleet, sample, and write the pooled summaries."""
    opts = sampler or SamplerOptions()
    out = ensure_out_dir(out_dir)
    voyages, resolved_pathogen = load_fleet_voyages(
        load_fleet_manifest(manifest_path),
        reporting=reporting,
        care_seeking=care_seeking,
        testing=testing,
        pathogen=pathogen,
    )
    incubation, generation = delays_for_pathogen(
        resolved_pathogen,
        epoch_hours=voyages[0].voyage.epoch_duration_hours,
    )
    data, meta = build_sentinel_fleet_data(
        voyages,
        incubation,
        generation,
        priors=priors,
        wastewater=WastewaterOptions(
            enabled=wastewater, pathogen=resolved_pathogen,
        ),
    )
    meta["pathogen"] = resolved_pathogen
    write_json(os.path.join(out, "stan_data_meta.json"), meta)
    _warn_unresolved_ports(meta)

    if _resolve_engine(engine, smoke=smoke) == "numpy":
        status = _numpy_status(
            data,
            meta,
            out=out,
            pathogen=resolved_pathogen,
            opts=opts,
            smoke=smoke,
        )
    else:
        status = _cmdstan_status(
            data, meta, out=out, pathogen=resolved_pathogen, opts=opts,
        )
    write_json(os.path.join(out, _FIT_STATUS_JSON), status)
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fleet sentinel port-hazard attribution (pooled across voyages)",
    )
    parser.add_argument("manifest", help="fleet manifest listing itinerary/observation pairs")
    parser.add_argument("--out", default="sentinel_fleet_fit")
    parser.add_argument(
        "--pathogen",
        default=None,
        help="delay-catalog key; defaults to the catalog's default_pathogen",
    )
    parser.add_argument("--reporting", type=float, default=1.0)
    parser.add_argument("--care-seeking", type=float, default=1.0)
    parser.add_argument("--testing", type=float, default=1.0)
    parser.add_argument(
        "--engine",
        choices=("auto", "stan", "numpy"),
        default="auto",
        help="auto uses CmdStan when installed and the numpy reference otherwise",
    )
    parser.add_argument("--chains", type=int, default=4)
    parser.add_argument("--iter-sampling", type=int, default=1000)
    parser.add_argument("--iter-warmup", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1701)
    parser.add_argument(
        "--show-progress", action=argparse.BooleanOptionalAction, default=True,
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="short numpy run that exercises the output path without a real fit",
    )
    parser.add_argument(
        "--wastewater",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "include the wastewater read counts as a second observation of the "
            "incidence curve; --no-wastewater is the clinical-only baseline the "
            "channel's marginal value is measured against (spec 6)"
        ),
    )
    args = parser.parse_args(argv)
    status = fit_sentinel_fleet(
        args.manifest,
        args.out,
        pathogen=args.pathogen,
        reporting=args.reporting,
        care_seeking=args.care_seeking,
        testing=args.testing,
        engine=args.engine,
        sampler=SamplerOptions(
            chains=args.chains,
            iter_sampling=args.iter_sampling,
            iter_warmup=args.iter_warmup,
            seed=args.seed,
            show_progress=args.show_progress,
        ),
        smoke=args.smoke,
        wastewater=args.wastewater,
    )
    print(status.get("status"), flush=True)
    return 0 if status.get("status") in {"ok", "smoke", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
