"""Fit the single-ship sentinel attribution model (port hazards + renewal).

Usage::

    python3 -m picard_framework.analysis.stan.fit_sentinel_attribution \\
      picard_framework/analysis/sentinel/data/example_itinerary.json \\
      picard_framework/analysis/sentinel/data/example_observations.json \\
      --out sentinel_fit

``--smoke`` summarizes the bundled fixture posterior instead of sampling, so the
whole path (data assembly -> port hazards CSV) is exercised without CmdStan.
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from typing import Any

from picard_framework.analysis._io import (
    allowed_roots,
    ensure_out_dir,
    write_csv,
    write_json,
)
from picard_framework.analysis.sentinel.attribution import (
    HAZARD_COLUMNS,
    hazard_rows,
    load_fixture_posterior,
    onboard_summary,
    summarize_port_hazards,
)
from picard_framework.analysis.sentinel.exposure import (
    ascertainment_fraction,
    build_exposure_design,
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
from picard_framework.analysis.stan._sentinel_data import (
    build_sentinel_attribution_data,
)
from simulation_utils.paths import validated_open

_FIT_STATUS_JSON = "fit_status.json"
_STAN_FILE = "sentinel_attribution.stan"
_FIXTURE_DRAWS = 200
_FIXTURE_WARMUP = 2000
_FIXTURE_THIN = 4
_FIXTURE_DESCRIPTION = (
    "Reference posterior for the sentinel example voyage, drawn by "
    "picard_framework.analysis.stan._sentinel_reference (same log density as "
    "sentinel_attribution.stan). Smoke fixture only: it lets CI exercise the "
    "posterior-to-hazard path with no CmdStan toolchain, and is not a "
    "calibrated fit."
)


def stan_model_path() -> str:
    """Absolute path to the attribution model source."""
    return os.path.join(os.path.dirname(__file__), _STAN_FILE)


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


def _write_outputs(
    out: str,
    posterior: dict[str, list[float]],
    meta: dict[str, Any],
    pathogen: str,
) -> dict[str, Any]:
    estimates = summarize_port_hazards(posterior, meta, pathogen=pathogen)
    write_csv(
        os.path.join(out, "port_hazards.csv"),
        hazard_rows(estimates),
        list(HAZARD_COLUMNS),
    )
    onboard = onboard_summary(posterior)
    write_json(os.path.join(out, "onboard_summary.json"), onboard)
    return {
        "n_ports": len(estimates),
        "onboard": onboard,
        "hazard_mean": {e.port_id: e.hazard_mean for e in estimates},
    }


def fit_sentinel_attribution(
    itinerary_path: str,
    observations_path: str,
    out_dir: str,
    *,
    pathogen: str | None = None,
    reporting: float = 1.0,
    care_seeking: float = 1.0,
    testing: float = 1.0,
    sampler: SamplerOptions | None = None,
    smoke: bool = False,
    write_fixture: str | None = None,
) -> dict[str, Any]:
    """Assemble the data, fit (or summarize the fixture), and write outputs."""
    opts = sampler or SamplerOptions()
    out = ensure_out_dir(out_dir)
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
        raise SystemExit("observations do not match the itinerary:\n" + "\n".join(problems))

    resolved_pathogen = pathogen or default_pathogen()
    incubation, generation = delays_for_pathogen(
        resolved_pathogen,
        epoch_hours=voyage.epoch_duration_hours,
    )
    design = build_exposure_design(
        voyage,
        bundle,
        incubation,
        ascertainment=ascertainment_fraction(
            reporting=reporting, care_seeking=care_seeking, testing=testing,
        ),
    )
    data, meta = build_sentinel_attribution_data(
        design, voyage, bundle, incubation, generation,
    )
    meta["pathogen"] = resolved_pathogen
    write_json(os.path.join(out, "stan_data_meta.json"), meta)
    if not meta["port_resolution_adequate"]:
        print(
            f"warn: incubation IQR {meta['incubation_iqr_hours']} h is not shorter "
            f"than the {meta['min_inter_port_hours']} h inter-port interval; "
            "read the per-port estimates as a port-window set (spec 1.8)",
            file=sys.stderr,
        )

    if write_fixture:
        from picard_framework.analysis.stan._sentinel_reference import (
            reference_posterior,
        )

        generator = (
            "picard_framework.analysis.stan._sentinel_reference.reference_posterior"
            f"(draws={_FIXTURE_DRAWS}, warmup={_FIXTURE_WARMUP}, "
            f"thin={_FIXTURE_THIN}, seed={opts.seed})"
        )
        write_json(
            write_fixture,
            {
                "schema_version": "1.0.0",
                "description": _FIXTURE_DESCRIPTION,
                "generator": generator,
                "meta": meta,
                "draws": reference_posterior(
                    data,
                    draws=_FIXTURE_DRAWS,
                    warmup=_FIXTURE_WARMUP,
                    thin=_FIXTURE_THIN,
                    seed=opts.seed,
                ),
            },
        )
        status = {"status": "fixture", "path": write_fixture, "meta": meta}
        write_json(os.path.join(out, _FIT_STATUS_JSON), status)
        return status

    if smoke:
        posterior = load_fixture_posterior()
        status: dict[str, Any] = {
            "status": "smoke",
            "reason": "fixture posterior; no sampling",
            "meta": meta,
            "summary": _write_outputs(out, posterior, meta, resolved_pathogen),
        }
        write_json(os.path.join(out, _FIT_STATUS_JSON), status)
        return status

    if not cmdstan_available():
        status = {
            "status": "skipped",
            "reason": "cmdstanpy/CmdStan not installed",
            "meta": meta,
        }
        write_json(os.path.join(out, _FIT_STATUS_JSON), status)
        return status

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
        status = {"status": "error", "reason": str(exc), "meta": meta}
        write_json(os.path.join(out, _FIT_STATUS_JSON), status)
        print(f"sentinel attribution fit failed: {exc}", file=sys.stderr)
        return status

    _write_draws_csv(fit, os.path.join(out, "draws.csv"))
    status = {
        "status": "ok",
        "meta": meta,
        "summary": _write_outputs(out, _posterior_from_fit(fit), meta, resolved_pathogen),
    }
    write_json(os.path.join(out, _FIT_STATUS_JSON), status)
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Single-ship sentinel port-hazard attribution (Poisson offsets)",
    )
    parser.add_argument("itinerary")
    parser.add_argument("observations")
    parser.add_argument("--out", default="sentinel_attribution_fit")
    parser.add_argument(
        "--pathogen",
        default=None,
        help="delay-catalog key; defaults to the catalog's default_pathogen",
    )
    parser.add_argument("--reporting", type=float, default=1.0)
    parser.add_argument("--care-seeking", type=float, default=1.0)
    parser.add_argument("--testing", type=float, default=1.0)
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
        help="summarize the bundled fixture posterior instead of sampling",
    )
    parser.add_argument(
        "--write-fixture",
        default=None,
        metavar="PATH",
        help=(
            "regenerate the committed smoke fixture at PATH with the numpy "
            "reference sampler (no CmdStan); rerun after changing the priors"
        ),
    )
    args = parser.parse_args(argv)
    status = fit_sentinel_attribution(
        args.itinerary,
        args.observations,
        args.out,
        pathogen=args.pathogen,
        reporting=args.reporting,
        care_seeking=args.care_seeking,
        testing=args.testing,
        sampler=SamplerOptions(
            chains=args.chains,
            iter_sampling=args.iter_sampling,
            iter_warmup=args.iter_warmup,
            seed=args.seed,
            show_progress=args.show_progress,
        ),
        smoke=args.smoke,
        write_fixture=args.write_fixture,
    )
    print(status.get("status"), flush=True)
    return 0 if status.get("status") in {"ok", "smoke", "skipped", "fixture"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
