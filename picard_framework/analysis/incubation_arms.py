"""Paired-arm sensitivity harness: paper 2 recovery with and without incubation.

Protocol: ``docs/incubation_sensitivity_protocol.md`` — paired arms, same
seeds, one switch. The switch is whether the pathogen profile carries an
``incubation`` block:

* ``distribution`` — the merged behaviour (dose- and host-conditioned draw).
* ``fixed_onset`` — the pre-merge behaviour, the profile with the block
  stripped, which is what the in-flight paper 2 campaign generated.

Everything else (platform, population, itineraries, port hazards, seeds,
dose, density exponent, surveillance config) is held identical, so a
difference between arms is attributable to the incubation representation and
nothing else. Both arms are fitted with the *same* sentinel delay kernel, so
this measures how paper 2's conclusions move when the data-generating onset
process changes under a fixed analysis model — which is the misspecification
question paper 2's MDHR and port-separability claims rest on.

Usage::

    python -m picard_framework.analysis.incubation_arms simulate \\
      --out results/incubation_arms --arm distribution
    python -m picard_framework.analysis.incubation_arms fit \\
      --out results/incubation_arms
    python -m picard_framework.analysis.incubation_arms compare \\
      --out results/incubation_arms
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics
import time
from dataclasses import dataclass, replace
from typing import Any, Mapping, Sequence

from picard_framework import PicardRunSpec, ShipSimulation
from picard_framework.analysis._io import (
    allowed_roots,
    ensure_out_dir,
    read_json,
    write_csv,
    write_json,
)
from picard_framework.analysis.sentinel_recovery_postprocess import (
    RECOVERY_COLUMNS,
    cell_id,
    cells_from_out,
    fit_cell,
    port_day_ids,
    prepare_observations,
    score_cell,
    write_cell_manifests,
)
from picard_framework.analysis.stan._data import cmdstan_available
from picard_framework.analysis.stan._sampler_options import SamplerOptions
from picard_framework.pathogen_overrides import (
    isolate_arm_overrides,
    load_pathogen_bundle,
)
from picard_framework.runs.mega_cruise_campaign import sentinel_recovery
from simulation_utils.paths import validate_path_component, validated_open

ARM_DISTRIBUTION = "distribution"
ARM_FIXED = "fixed_onset"
ARMS = (ARM_DISTRIBUTION, ARM_FIXED)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MANIFEST_PATH = os.path.join(
    "picard_framework",
    "runs",
    "mega_cruise_campaign",
    "sentinel_synthetic_recovery_v1_manifest.json",
)
BUNDLE_DIR = os.path.join("data", "pathogens")

DEFAULT_SEEDS = (300, 301, 302, 303, 304, 305)
DEFAULT_ITINERARIES = ("standard", "reversed", "staggered")
DEFAULT_PLATFORM = "classic_cruise_1900"
DEFAULT_NUM_AGENTS = 1910
DEFAULT_HAZARD_PROFILE = "uniform_high"
DEFAULT_FLEET_CONFIG = "fleet_crossed"
DEFAULT_R_ONBOARD = 1.0
DEFAULT_SURVEILLANCE = "syndromic"

ONSET_COLUMNS = (
    "arm",
    "run_id",
    "person_id",
    "port_id",
    "exposure_epoch",
    "onset_epoch",
    "incubation_hours",
)
COMPARISON_COLUMNS = (
    "cell_id",
    "port_id",
    "lambda_true",
    "lambda_mean_distribution",
    "lambda_mean_fixed_onset",
    "rel_bias_distribution",
    "rel_bias_fixed_onset",
    "width_distribution",
    "width_fixed_onset",
    "width_ratio",
    "covered_distribution",
    "covered_fixed_onset",
)


@dataclass(frozen=True)
class ArmsDesign:
    """One recovery cell, run identically in both arms."""

    platform: str = DEFAULT_PLATFORM
    num_agents: int = DEFAULT_NUM_AGENTS
    epochs: int = 168
    itineraries: tuple[str, ...] = DEFAULT_ITINERARIES
    seeds: tuple[int, ...] = DEFAULT_SEEDS
    hazard_profile: str = DEFAULT_HAZARD_PROFILE
    fleet_config: str = DEFAULT_FLEET_CONFIG
    r_onboard: float = DEFAULT_R_ONBOARD
    pathogen: str = ""  # empty: take the manifest's sole pathogen config
    surveillance: str = DEFAULT_SURVEILLANCE


def read_repo_json(relative_path: str) -> Any:
    """Read a catalog input from the repository, independent of the CWD."""
    with validated_open(
        os.path.join(REPO_ROOT, relative_path),
        allowed_roots=(REPO_ROOT,),
        encoding="utf-8",
    ) as fh:
        return json.load(fh)


def load_manifest(path: str | None = None) -> dict[str, Any]:
    """Load the sentinel recovery campaign manifest."""
    return read_repo_json(path or MANIFEST_PATH)


def hazards_for_profile(
    manifest: Mapping[str, Any],
    hazard_profile: str,
) -> dict[str, float]:
    """Port hazards the campaign associates with ``hazard_profile``."""
    for tier in (manifest.get("tiers") or {}).values():
        if str(tier.get("hazard_profile") or "") != hazard_profile:
            continue
        hazards = (tier.get("shore_exposure") or {}).get("port_hazards") or {}
        return {str(k): float(v) for k, v in hazards.items()}
    raise SystemExit(f"manifest has no hazard profile named {hazard_profile!r}")


def strip_incubation(profile: Mapping[str, Any]) -> dict[str, Any]:
    """The profile as it was before the incubation block existed."""
    return {k: v for k, v in profile.items() if k != "incubation"}


def bundle_profiles(bundle_id: str) -> dict[str, dict[str, Any]]:
    """Pathogen profiles for a catalog bundle id."""
    return load_pathogen_bundle(
        os.path.join(REPO_ROOT, BUNDLE_DIR, f"{bundle_id}.json"),
    )


def arm_pathogen_overrides(
    *,
    arm: str,
    profiles: Mapping[str, Mapping[str, Any]],
    pathogen_id: str,
    base_overrides: Mapping[str, Any] | None,
    dose_adjustment: float,
    n_init: int,
) -> dict[str, Any]:
    """Run-spec pathogen overrides for one arm — the only thing that differs."""
    if arm not in ARMS:
        raise SystemExit(f"unknown arm {arm!r}")
    over: dict[str, Any] = {
        key: (list(val) if isinstance(val, list) else val)
        for key, val in (base_overrides or {}).items()
    }
    if arm == ARM_FIXED:
        profile = profiles.get(pathogen_id)
        if profile is None:
            raise SystemExit(f"bundle has no profile for {pathogen_id!r}")
        if "incubation" not in profile:
            raise SystemExit(
                f"{pathogen_id} carries no incubation block, so the paired-arm "
                "switch would be a no-op",
            )
        over["add"] = [*(over.get("add") or []), strip_incubation(profile)]
    patch = dict(over.get(pathogen_id) or {})
    patch["dose_adjustment"] = float(dose_adjustment)
    patch["initial_infected"] = int(n_init)
    over[pathogen_id] = patch
    return over


def voyage_run_id(arm: str, variant: str, seed: int) -> str:
    """Filesystem-safe per-voyage id, unique within an arm."""
    return validate_path_component(f"{arm}__{variant}__s{int(seed)}", label="run_id")


def _surveillance_override(
    manifest: Mapping[str, Any],
    name: str,
) -> dict[str, Any]:
    cfgs = manifest.get("surveillance_configs") or {}
    cfg = cfgs.get(name)
    if not isinstance(cfg, dict):
        raise SystemExit(f"manifest has no surveillance config named {name!r}")
    return dict(cfg)


def run_spec_payload(
    design: ArmsDesign,
    *,
    manifest: Mapping[str, Any],
    arm: str,
    variant: str,
    seed: int,
    run_id: str,
    voyage: Mapping[str, Any],
    pathogen_overrides: Mapping[str, Any],
    bundle: str,
    line_list_path: str,
) -> dict[str, Any]:
    """Picard run spec for one voyage of one arm."""
    defaults = manifest.get("defaults") or {}
    alpha = float(defaults.get("density_exponent", 0.75))
    config: dict[str, Any] = {
        "ship_graph": {"num_agents": int(design.num_agents)},
        "transmission": {
            "contact_mode": "density_dependent",
            "density_dependent": {"exponent": alpha},
        },
        "voyage": dict(voyage),
        "voyage_id": run_id,
        **_surveillance_override(manifest, design.surveillance),
    }
    return {
        "schema_version": "1.0.0",
        "catalog": {
            "platform_id": design.platform,
            "pathogen_bundle_id": bundle,
        },
        "run": {
            "random_seed": int(seed),
            "num_epochs": int(design.epochs),
            "write_ground_truth": False,
            "history_retention": "compact",
            "sentinel_line_list": line_list_path,
        },
        "legacy_yaml": os.path.join("crusher_labs", "config.yaml"),
        "pathogen_overrides": dict(pathogen_overrides),
        "config_overrides": config,
        "actors": [],
        "incentives": {},
        "notes": f"incubation paired arm={arm} itinerary={variant} seed={seed}",
    }


def voyage_params(
    design: ArmsDesign,
    *,
    arm: str,
    variant: str,
    seed: int,
    run_id: str,
    hazards: Mapping[str, float],
    dose_adjustment: float,
    n_init: int,
) -> dict[str, Any]:
    """``meta.json`` for the extract layout the fleet fitter consumes."""
    return {
        "run_id": run_id,
        "arm": arm,
        "platform_id": design.platform,
        "num_agents": int(design.num_agents),
        "pathogen": design.pathogen,
        "surveillance": design.surveillance,
        "itinerary_variant": variant,
        "seed": int(seed),
        "epochs": int(design.epochs),
        "dose_adjustment": float(dose_adjustment),
        "initial_infected": int(n_init),
        "R_onboard": float(design.r_onboard),
        "hazard_profile": design.hazard_profile,
        "fleet_config": design.fleet_config,
        "port_hazards": {str(k): float(v) for k, v in hazards.items()},
    }


def realized_incubations(observations: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Onset minus shore-exposure epoch, per case with a known introduction."""
    hours = float(observations.get("epoch_duration_hours") or 1.0)
    intro = {
        str(rec.get("person_id")): rec
        for rec in observations.get("truth_introductions") or []
        if isinstance(rec, dict)
    }
    rows: list[dict[str, Any]] = []
    for case in observations.get("clinical_cases") or []:
        if not isinstance(case, dict):
            continue
        rec = intro.get(str(case.get("person_id")))
        if rec is None or case.get("onset_epoch") is None:
            continue
        span = (int(case["onset_epoch"]) - int(rec.get("epoch") or 0)) * hours
        if span <= 0:
            continue
        rows.append(
            {
                "person_id": str(case.get("person_id")),
                "port_id": str(rec.get("port_id") or ""),
                "exposure_epoch": int(rec.get("epoch") or 0),
                "onset_epoch": int(case["onset_epoch"]),
                "incubation_hours": span,
            },
        )
    return rows


def onset_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Median / IQR of realized incubation, the arm's onset signature."""
    values = sorted(float(r["incubation_hours"]) for r in rows)
    if not values:
        return {"n": 0, "median_hours": float("nan"), "iqr_hours": float("nan")}
    if len(values) < 4:
        return {
            "n": len(values),
            "median_hours": statistics.median(values),
            "iqr_hours": float("nan"),
        }
    q1, _q2, q3 = statistics.quantiles(values, n=4, method="inclusive")
    return {
        "n": len(values),
        "median_hours": statistics.median(values),
        "iqr_hours": q3 - q1,
        "mean_hours": statistics.fmean(values),
    }


def simulate_voyage(
    design: ArmsDesign,
    *,
    manifest: Mapping[str, Any],
    arm: str,
    variant: str,
    seed: int,
    hazards: Mapping[str, float],
    profiles: Mapping[str, Mapping[str, Any]],
    pathogen_id: str,
    base_overrides: Mapping[str, Any] | None,
    bundle: str,
    arm_dir: str,
) -> dict[str, Any]:
    """Run one voyage and return its extract record."""
    defaults = manifest.get("defaults") or {}
    dose = float(defaults.get("dose_adjustment", 10.6))
    n_init = sentinel_recovery.initial_infected(dict(hazards), design.r_onboard)
    run_id = voyage_run_id(arm, variant, seed)
    dest = ensure_out_dir(os.path.join(arm_dir, "voyages", run_id))
    days = sentinel_recovery.stamp_port_hazards(
        sentinel_recovery.itinerary_days(dict(manifest), variant),
        dict(hazards),
    )
    voyage = sentinel_recovery.voyage_override(
        days=days,
        r_onboard=float(design.r_onboard),
        epochs=int(design.epochs),
        embarkation_date=str(manifest.get("embarkation_date", "2026-01-10")),
    )
    overrides = arm_pathogen_overrides(
        arm=arm,
        profiles=profiles,
        pathogen_id=pathogen_id,
        base_overrides=base_overrides,
        dose_adjustment=dose,
        n_init=n_init,
    )
    line_list = os.path.join(dest, "line_list.json")
    spec_path = os.path.join(dest, "run_spec.json")
    write_json(
        spec_path,
        run_spec_payload(
            design,
            manifest=manifest,
            arm=arm,
            variant=variant,
            seed=seed,
            run_id=run_id,
            voyage=voyage,
            pathogen_overrides=overrides,
            bundle=bundle,
            line_list_path=line_list,
        ),
    )
    started = time.time()
    run = PicardRunSpec.from_picard_json(REPO_ROOT, spec_path)
    sim = ShipSimulation(run, display=False)
    sim.run()
    sim.finalize(display=False)
    raw = read_json(line_list)
    params = voyage_params(
        design,
        arm=arm,
        variant=variant,
        seed=seed,
        run_id=run_id,
        hazards=hazards,
        dose_adjustment=dose,
        n_init=n_init,
    )
    params["wall_seconds"] = round(time.time() - started, 1)
    return {
        "run_id": run_id,
        "params": params,
        "itinerary": {"schema_version": "1.0", "voyage": voyage},
        "observations": prepare_observations(raw, run_id, port_day_ids(voyage)),
    }


def _voyage_entry(record: Mapping[str, Any]) -> dict[str, Any]:
    run_id = str(record["run_id"])
    params = record["params"]
    return {
        "run_id": run_id,
        "hazard_profile": str(params["hazard_profile"]),
        "fleet_config": str(params["fleet_config"]),
        "R_onboard": float(params["R_onboard"]),
        "port_hazards": dict(params["port_hazards"]),
        "itinerary": os.path.join("voyages", run_id, "itinerary.json"),
        "observations": os.path.join("voyages", run_id, "observations.json"),
    }


def write_voyage_record(arm_dir: str, record: Mapping[str, Any]) -> None:
    """Persist one voyage in the layout ``cells_from_out`` expects."""
    dest = os.path.join(arm_dir, "voyages", str(record["run_id"]))
    write_json(os.path.join(dest, "itinerary.json"), record["itinerary"])
    write_json(os.path.join(dest, "observations.json"), record["observations"])
    write_json(os.path.join(dest, "meta.json"), record["params"])


def simulate_arm(
    design: ArmsDesign,
    arm: str,
    out_root: str,
    *,
    manifest: Mapping[str, Any] | None = None,
    skip_existing: bool = True,
) -> str:
    """Simulate every voyage of one arm; write the extract layout and onsets."""
    man = dict(manifest or load_manifest())
    design = replace(design, pathogen=resolve_pathogen_key(man, design.pathogen))
    hazards = hazards_for_profile(man, design.hazard_profile)
    bundle, pathogen_id, base_overrides = _pathogen_config(man, design.pathogen)
    profiles = bundle_profiles(bundle)
    arm_dir = ensure_out_dir(os.path.join(out_root, arm))
    entries: list[dict[str, Any]] = []
    onsets: list[dict[str, Any]] = []
    for variant in design.itineraries:
        for seed in design.seeds:
            record = _voyage_or_cached(
                design,
                manifest=man,
                arm=arm,
                variant=variant,
                seed=seed,
                hazards=hazards,
                profiles=profiles,
                pathogen_id=pathogen_id,
                base_overrides=base_overrides,
                bundle=bundle,
                arm_dir=arm_dir,
                skip_existing=skip_existing,
            )
            entries.append(_voyage_entry(record))
            onsets.extend(
                {"arm": arm, "run_id": record["run_id"], **row}
                for row in realized_incubations(record["observations"])
            )
    _write_arm_index(arm_dir, design, entries, onsets)
    return arm_dir


def _voyage_or_cached(
    design: ArmsDesign,
    *,
    arm: str,
    variant: str,
    seed: int,
    arm_dir: str,
    skip_existing: bool,
    **kwargs: Any,
) -> dict[str, Any]:
    run_id = voyage_run_id(arm, variant, seed)
    dest = os.path.join(arm_dir, "voyages", run_id)
    obs_path = os.path.join(dest, "observations.json")
    if skip_existing and os.path.isfile(obs_path):
        print(f"[{arm}] reuse {run_id}", flush=True)
        return {
            "run_id": run_id,
            "params": read_json(os.path.join(dest, "meta.json")),
            "itinerary": read_json(os.path.join(dest, "itinerary.json")),
            "observations": read_json(obs_path),
        }
    print(f"[{arm}] simulate {run_id}", flush=True)
    record = simulate_voyage(
        design,
        arm=arm,
        variant=variant,
        seed=seed,
        arm_dir=arm_dir,
        **kwargs,
    )
    write_voyage_record(arm_dir, record)
    cases = len(record["observations"].get("clinical_cases") or [])
    print(
        f"[{arm}] {run_id} cases={cases} "
        f"seconds={record['params'].get('wall_seconds')}",
        flush=True,
    )
    return record


def _write_arm_index(
    arm_dir: str,
    design: ArmsDesign,
    entries: Sequence[Mapping[str, Any]],
    onsets: Sequence[Mapping[str, Any]],
) -> None:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        cid = cell_id(
            str(entry["hazard_profile"]),
            str(entry["fleet_config"]),
            float(entry["R_onboard"]),
        )
        grouped.setdefault(cid, []).append(dict(entry))
    write_json(
        os.path.join(arm_dir, "cells.json"),
        {cid: [v["run_id"] for v in rows] for cid, rows in grouped.items()},
    )
    write_cell_manifests(grouped, arm_dir)
    write_csv(os.path.join(arm_dir, "onsets.csv"), list(onsets), ONSET_COLUMNS)
    write_json(
        os.path.join(arm_dir, "onset_summary.json"),
        {
            "platform_id": design.platform,
            "num_agents": design.num_agents,
            "hazard_profile": design.hazard_profile,
            "fleet_config": design.fleet_config,
            "n_voyages": len(entries),
            **onset_summary(onsets),
        },
    )


def resolve_pathogen_key(manifest: Mapping[str, Any], pathogen: str) -> str:
    """Manifest pathogen-config key, defaulting to the sole one declared."""
    configs = manifest.get("pathogen_configs") or {}
    if pathogen:
        return pathogen
    if len(configs) != 1:
        raise SystemExit(
            "manifest declares several pathogen configs; name one explicitly",
        )
    return str(next(iter(configs)))


def _pathogen_config(
    manifest: Mapping[str, Any],
    pathogen: str,
) -> tuple[str, str, dict[str, Any] | None]:
    configs = manifest.get("pathogen_configs") or {}
    cfg = configs.get(resolve_pathogen_key(manifest, pathogen))
    if not isinstance(cfg, dict):
        raise SystemExit(f"manifest has no pathogen config named {pathogen!r}")
    overrides = cfg.get("overrides")
    if isinstance(overrides, list):
        overrides = {"remove": list(overrides)}
    bundle = str(cfg.get("bundle") or "active_profiles")
    pathogen_id = str(cfg["pathogen_id"])
    return (
        bundle,
        pathogen_id,
        isolate_arm_overrides(
            bundle,
            pathogen_id,
            dict(overrides) if isinstance(overrides, dict) else None,
        ),
    )


def fit_arm(
    arm_dir: str,
    *,
    engine: str,
    sampler: SamplerOptions,
    force: bool = False,
    pathogen: str | None = None,
) -> list[dict[str, Any]]:
    """Fit every cell of one arm and write its recovery table."""
    rows: list[dict[str, Any]] = []
    for cell in cells_from_out(arm_dir):
        status = fit_cell(
            cell,
            engine=engine,
            sampler=sampler,
            force=force,
            pathogen=pathogen,
        )
        rows.extend(score_cell(cell, status))
    write_csv(os.path.join(arm_dir, "recovery.csv"), rows, list(RECOVERY_COLUMNS))
    return rows


def read_recovery(arm_dir: str) -> list[dict[str, str]]:
    """Rows of a previously written ``recovery.csv``."""
    path = os.path.join(arm_dir, "recovery.csv")
    with validated_open(
        path, allowed_roots=allowed_roots(), encoding="utf-8", newline="",
    ) as fh:
        return list(csv.DictReader(fh))


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def _rel_bias(mean: float, true: float) -> float:
    if not true:
        return float("nan")
    return (mean - true) / true


def compare_rows(
    distribution: Sequence[Mapping[str, Any]],
    fixed: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Join the two arms' recovery tables on (cell, port)."""
    keyed = {
        (str(r["cell_id"]), str(r["port_id"])): r for r in fixed
    }
    out: list[dict[str, Any]] = []
    for row in distribution:
        key = (str(row["cell_id"]), str(row["port_id"]))
        other = keyed.get(key)
        if other is None:
            continue
        out.append(_comparison_row(row, other))
    return sorted(out, key=lambda r: (r["cell_id"], r["port_id"]))


def _comparison_row(
    dist: Mapping[str, Any],
    fixed: Mapping[str, Any],
) -> dict[str, Any]:
    true = _as_float(dist.get("lambda_true"))
    d_mean = _as_float(dist.get("lambda_mean"))
    f_mean = _as_float(fixed.get("lambda_mean"))
    d_width = _as_float(dist.get("lambda_q95")) - _as_float(dist.get("lambda_q05"))
    f_width = _as_float(fixed.get("lambda_q95")) - _as_float(fixed.get("lambda_q05"))
    ratio = d_width / f_width if f_width else float("nan")
    return {
        "cell_id": str(dist["cell_id"]),
        "port_id": str(dist["port_id"]),
        "lambda_true": true,
        "lambda_mean_distribution": d_mean,
        "lambda_mean_fixed_onset": f_mean,
        "rel_bias_distribution": _rel_bias(d_mean, true),
        "rel_bias_fixed_onset": _rel_bias(f_mean, true),
        "width_distribution": d_width,
        "width_fixed_onset": f_width,
        "width_ratio": ratio,
        "covered_distribution": _as_bool(dist.get("lambda_covered")),
        "covered_fixed_onset": _as_bool(fixed.get("lambda_covered")),
    }


def coverage_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """Ports whose 90% interval covers λ_p, per arm."""
    return {
        "n": len(rows),
        "covered_distribution": sum(1 for r in rows if r["covered_distribution"]),
        "covered_fixed_onset": sum(1 for r in rows if r["covered_fixed_onset"]),
    }


def _mean_abs_rel_bias(rows: Sequence[Mapping[str, Any]], key: str) -> float:
    values = [abs(float(r[key])) for r in rows if not math.isnan(float(r[key]))]
    return statistics.fmean(values) if values else float("nan")


def _report_lines(
    rows: Sequence[Mapping[str, Any]],
    onsets: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    counts = coverage_counts(rows)
    lines = [
        "# Incubation sensitivity: paper 2 port attribution, paired arms",
        "",
        "One switch: the pathogen profile's `incubation` block. Same seeds,",
        "itineraries, platform, hazards, dose and fitted delay kernel.",
        "",
        "## Realized onset (simulator truth)",
        "",
        "| arm | onsets | median h | IQR h |",
        "|---|---:|---:|---:|",
    ]
    for arm in ARMS:
        summary = onsets.get(arm) or {}
        lines.append(
            f"| {arm} | {summary.get('n', 0)} | "
            f"{_as_float(summary.get('median_hours')):.1f} | "
            f"{_as_float(summary.get('iqr_hours')):.1f} |",
        )
    lines += [
        "",
        "## Port-hazard recovery",
        "",
        f"- rows compared: {counts['n']}",
        f"- λ_p covered (distribution): {counts['covered_distribution']}/{counts['n']}",
        f"- λ_p covered (fixed onset): {counts['covered_fixed_onset']}/{counts['n']}",
        "- mean |relative bias| distribution: "
        f"{_mean_abs_rel_bias(rows, 'rel_bias_distribution'):.3f}",
        "- mean |relative bias| fixed onset: "
        f"{_mean_abs_rel_bias(rows, 'rel_bias_fixed_onset'):.3f}",
        "",
        "| cell | port | true λ | mean (dist) | mean (fixed) | width ratio |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['cell_id']} | {row['port_id']} | {row['lambda_true']:.4g} | "
            f"{row['lambda_mean_distribution']:.4g} | "
            f"{row['lambda_mean_fixed_onset']:.4g} | {row['width_ratio']:.3f} |",
        )
    return lines


def write_comparison(
    out_root: str,
    rows: Sequence[Mapping[str, Any]],
    onsets: Mapping[str, Mapping[str, Any]],
) -> str:
    """Write ``arms_comparison.csv`` plus the markdown report."""
    write_csv(
        os.path.join(out_root, "arms_comparison.csv"),
        list(rows),
        list(COMPARISON_COLUMNS),
    )
    path = os.path.join(out_root, "arms_report.md")
    with validated_open(
        path, "w", allowed_roots=allowed_roots(), encoding="utf-8",
    ) as fh:
        fh.write("\n".join(_report_lines(rows, onsets)) + "\n")
    return path


def _design_from_args(args: argparse.Namespace) -> ArmsDesign:
    return ArmsDesign(
        platform=args.platform,
        num_agents=args.num_agents,
        epochs=args.epochs,
        itineraries=tuple(args.itinerary) or DEFAULT_ITINERARIES,
        seeds=tuple(args.seed) or DEFAULT_SEEDS,
        hazard_profile=args.hazard_profile,
        fleet_config=args.fleet_config,
        r_onboard=args.r_onboard,
    )


def _sampler_from_args(args: argparse.Namespace) -> tuple[str, SamplerOptions]:
    engine = args.engine
    if engine == "auto" and not cmdstan_available():
        print("CmdStan not available; using numpy reference walker", flush=True)
        engine = "numpy"
    return engine, SamplerOptions(
        chains=args.chains,
        iter_sampling=args.iter_sampling,
        iter_warmup=args.iter_warmup,
        seed=args.fit_seed,
        show_progress=True,
    )


def _add_design_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--platform", default=DEFAULT_PLATFORM)
    parser.add_argument("--num-agents", type=int, default=DEFAULT_NUM_AGENTS)
    parser.add_argument("--epochs", type=int, default=168)
    parser.add_argument(
        "--itinerary", action="append", default=[], help="repeatable template name",
    )
    parser.add_argument("--seed", action="append", type=int, default=[])
    parser.add_argument("--hazard-profile", default=DEFAULT_HAZARD_PROFILE)
    parser.add_argument("--fleet-config", default=DEFAULT_FLEET_CONFIG)
    parser.add_argument("--r-onboard", type=float, default=DEFAULT_R_ONBOARD)


def _add_fit_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--engine", choices=("auto", "stan", "numpy"), default="auto")
    parser.add_argument("--chains", type=int, default=2)
    parser.add_argument("--iter-sampling", type=int, default=400)
    parser.add_argument("--iter-warmup", type=int, default=1600)
    parser.add_argument("--fit-seed", type=int, default=1701)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--pathogen", default=None)


def build_parser() -> argparse.ArgumentParser:
    """CLI for the three stages."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=os.path.join("results", "incubation_arms"))
    sub = parser.add_subparsers(dest="stage", required=True)
    sim = sub.add_parser("simulate", help="run voyages for one or both arms")
    sim.add_argument("--arm", action="append", default=[], choices=list(ARMS))
    sim.add_argument("--rerun", action="store_true", help="ignore cached voyages")
    _add_design_arguments(sim)
    fit = sub.add_parser("fit", help="fit the fleet model per arm")
    fit.add_argument("--arm", action="append", default=[], choices=list(ARMS))
    _add_fit_arguments(fit)
    sub.add_parser("compare", help="difference the two arms")
    return parser


def _stage_simulate(args: argparse.Namespace, out_root: str) -> int:
    design = _design_from_args(args)
    manifest = load_manifest()
    for arm in args.arm or list(ARMS):
        simulate_arm(
            design,
            arm,
            out_root,
            manifest=manifest,
            skip_existing=not args.rerun,
        )
    return 0


def _stage_fit(args: argparse.Namespace, out_root: str) -> int:
    engine, sampler = _sampler_from_args(args)
    for arm in args.arm or list(ARMS):
        rows = fit_arm(
            os.path.join(out_root, arm),
            engine=engine,
            sampler=sampler,
            force=args.force,
            pathogen=args.pathogen,
        )
        print(f"[{arm}] recovery rows={len(rows)}", flush=True)
    return 0


def _stage_compare(out_root: str) -> int:
    rows = compare_rows(
        read_recovery(os.path.join(out_root, ARM_DISTRIBUTION)),
        read_recovery(os.path.join(out_root, ARM_FIXED)),
    )
    onsets = {
        arm: read_json(os.path.join(out_root, arm, "onset_summary.json"))
        for arm in ARMS
    }
    path = write_comparison(out_root, rows, onsets)
    print(f"wrote {path} rows={len(rows)}", flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for the paired-arm harness."""
    args = build_parser().parse_args(argv)
    out_root = ensure_out_dir(args.out)
    if args.stage == "simulate":
        return _stage_simulate(args, out_root)
    if args.stage == "fit":
        return _stage_fit(args, out_root)
    return _stage_compare(out_root)


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
