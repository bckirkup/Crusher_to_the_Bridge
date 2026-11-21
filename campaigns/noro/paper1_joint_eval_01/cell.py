#!/usr/bin/env python3
"""Paper-1 WP2 joint-evaluation cell: six outcome families from one run.

One voyage per array child, spec taken verbatim from the campaign manifest
tier (``generate_tier_runs``), so the tier's ``config_overrides`` -- the
freeze contract's section 2 block -- reaches the engine through the verified
loader path. Nothing here changes engine behaviour or adds an engine output
field: every family is read from what the run already produces.

Families (freeze contract section 5):

1. burden by role      final-epoch ``cumulative_reported_cases_*`` + census
2. threshold timing    ``derived.vsp_trigger_epoch``
3. size distribution   the seed ensemble of 1 and 2 (readout side)
4. first role to 0.03  per-epoch ``cumulative_reported_cases_{passenger,crew}``
5. daily curves        onsets from ``run.sentinel_line_list``; reporting curve
                       from the per-epoch cumulative series. Day 0 of the
                       reporting curve includes pre-boarding AGE declarations
                       and is labelled so.
6. environment         surface swabs (``surface_pool_density``) and the
                       holding-tank wastewater assay

Family 6 note: campaign runs use ``history_retention: compact``, whose epoch
record drops the ``observation_engine`` block. The swab and holding-tank
results the engine computes every epoch are therefore read through
``ShipSimulation.epoch_observer`` (the read-only per-epoch hook the census
workers already use). The observer reads results the epoch already produced
and draws nothing; ``--verify-draws`` measures that claim by running the
same spec with no observer and no line list and comparing voyage
fingerprints.

Zip members: ``summary.json`` (campaign anchor layout plus ``joint_eval``
scalars) and ``joint_eval.json.gz`` (daily curves and environment series).
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_child_path,
)
from tools.diag.instrument_common import materialized_picard_spec  # noqa: E402
from tools.diag.json_io import validated_json_load  # noqa: E402
from tools.diag.manifest_args import (  # noqa: E402
    add_manifest_args,
    filter_runs_by_seeds,
    index_run,
)
from tools.diag.readout_common import write_run_zip  # noqa: E402

_CAMPAIGN_DIR = REPO_ROOT / "picard_framework" / "runs" / "mega_cruise_campaign"
if str(_CAMPAIGN_DIR) not in sys.path:
    sys.path.insert(0, str(_CAMPAIGN_DIR))

from campaign_runner import generate_tier_runs  # noqa: E402

from tools.noro_diag.per_host_dose_challenge import (  # noqa: E402
    _attach_voyage_blocks,
)

SCHEMA = "paper1_joint_eval_cell/1.0.0"
THRESHOLD = 0.03
MEMBER = "joint_eval.json.gz"
DAY0_LABEL = (
    "day 0 includes pre-boarding AGE declarations seeded at embarkation "
    "(preboarding_reportable_ids); see preboarding_reported_*"
)
FAMILY_KEYS = (
    "burden", "threshold", "first_role", "curves", "environment",
)


def leaf_items(tree: dict[str, Any], prefix: str = "") -> list[tuple[str, Any]]:
    """Dotted (path, value) pairs for every non-dict leaf."""
    out: list[tuple[str, Any]] = []
    for key, value in tree.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict) and value:
            out.extend(leaf_items(value, f"{path}."))
        else:
            out.append((path, value))
    return out


def get_path(tree: Any, dotted: str) -> Any:
    node = tree
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return "<absent>"
        node = node[part]
    return node


def config_echo(sim: Any, overrides: dict[str, Any]) -> dict[str, Any]:
    """The engine-resolved value of every leaf the tier overrides.

    Read from ``sim.cfg`` after ``initialize()`` -- the merged config the
    engine actually runs on, not the manifest that asked for it.
    """
    cfg = sim.cfg
    rows = {
        path: get_path(cfg, path) for path, _ in leaf_items(overrides)
    }
    mismatched = sorted(
        path for path, want in leaf_items(overrides) if rows[path] != want
    )
    canonical = json.dumps(overrides, sort_keys=True, separators=(",", ":"))
    return {
        "n_leaves": len(rows),
        "mismatched": mismatched,
        "resolved": rows,
        "overrides_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
    }


class EnvRecorder:
    """Per-epoch swab and holding-tank rows from the epoch scratch pad."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def observe(self, _sim: Any, work: Any) -> None:
        swabs = getattr(work, "swab_results", None) or {}
        tank = getattr(work, "wastewater_ht_result", None)
        detected = [s for s in swabs.values() if s.get("detected")]
        densities = [
            float(s.get("surface_density_copies_per_cm2") or 0.0)
            for s in swabs.values()
        ]
        row: dict[str, Any] = {
            "epoch": int(work.epoch),
            "swab_n": len(swabs),
            "swab_detected": len(detected),
            "swab_censored": sum(
                1 for s in swabs.values() if s.get("censored_below_lod")
            ),
            "swab_max_density": max(densities, default=0.0),
            "tank": tank is not None,
        }
        if tank is not None:
            row.update(
                tank_detected=bool(tank.get("detected")),
                tank_quantifiable=bool(tank.get("quantifiable")),
                tank_log10_copies_per_l=tank.get("log10_copies_per_l"),
            )
        self.rows.append(row)


def _first_crossing(series: list[dict[str, Any]], role: str) -> int | None:
    for row in series:
        complement = row.get(f"{role}_complement") or 0
        count = row.get(f"cumulative_reported_cases_{role}") or 0
        if complement and count / complement >= THRESHOLD:
            return int(row["epoch"])
    return None


def first_role(series: list[dict[str, Any]]) -> dict[str, Any]:
    pax = _first_crossing(series, "passenger")
    crew = _first_crossing(series, "crew")
    if pax is None and crew is None:
        role = "none"
    elif crew is None or (pax is not None and pax < crew):
        role = "passenger"
    elif pax is None or crew < pax:
        role = "crew"
    else:
        role = "tie"
    return {
        "threshold": THRESHOLD,
        "passenger_epoch": pax,
        "crew_epoch": crew,
        "first_role": role,
    }


def _daily_increments(
    series: list[dict[str, Any]], key: str, epochs_per_day: int,
) -> list[int]:
    """Per-day new counts from a cumulative per-epoch series.

    Day 0 is the cumulative value at the end of its last epoch, so it
    includes whatever the series was seeded with at embarkation.
    """
    out: list[int] = []
    previous = 0
    n_days = math.ceil(len(series) / epochs_per_day)
    for day in range(n_days):
        last = min((day + 1) * epochs_per_day, len(series)) - 1
        value = int(series[last].get(key) or 0)
        out.append(value - previous)
        previous = value
    return out


def _daily_onsets(
    cases: list[dict[str, Any]], n_days: int, epochs_per_day: int,
) -> dict[str, list[int]]:
    out = {"passenger": [0] * n_days, "crew": [0] * n_days}
    pre_boarding = 0
    for case in cases:
        onset = case.get("onset_epoch")
        if onset is None:
            continue
        if onset < 0:
            pre_boarding += 1
            continue
        day = min(int(onset) // epochs_per_day, n_days - 1)
        out["crew" if case.get("crew") else "passenger"][day] += 1
    out["pre_boarding_onsets"] = pre_boarding  # type: ignore[assignment]
    return out


def curves(
    series: list[dict[str, Any]], line_list: dict[str, Any],
    epochs_per_day: int,
) -> dict[str, Any]:
    n_days = math.ceil(len(series) / epochs_per_day) if series else 0
    first = series[0] if series else {}
    cases = line_list.get("clinical_cases") or []
    channels: dict[str, int] = {}
    for case in cases:
        channel = str(case.get("reported_via"))
        channels[channel] = channels.get(channel, 0) + 1
    return {
        "epochs_per_day": epochs_per_day,
        "n_days": n_days,
        "reporting_source": "per-epoch cumulative_reported_cases_* series",
        "onset_source": "run.sentinel_line_list clinical_cases.onset_epoch",
        "day0_label": DAY0_LABEL,
        "preboarding_reported_passenger": int(
            first.get("cumulative_reported_cases_passenger") or 0,
        ),
        "preboarding_reported_crew": int(
            first.get("cumulative_reported_cases_crew") or 0,
        ),
        "reported_daily_passenger": _daily_increments(
            series, "cumulative_reported_cases_passenger", epochs_per_day,
        ),
        "reported_daily_crew": _daily_increments(
            series, "cumulative_reported_cases_crew", epochs_per_day,
        ),
        "onsets_daily": _daily_onsets(cases, n_days, epochs_per_day),
        "line_list_cases": len(cases),
        "line_list_channels": channels,
    }


def environment(rows: list[dict[str, Any]], epochs_per_day: int) -> dict[str, Any]:
    tank_rows = [r for r in rows if r["tank"]]
    daily: list[dict[str, Any]] = []
    for start in range(0, len(rows), epochs_per_day):
        chunk = rows[start:start + epochs_per_day]
        logs = [
            r["tank_log10_copies_per_l"] for r in chunk
            if r.get("tank_log10_copies_per_l") is not None
        ]
        daily.append({
            "day": start // epochs_per_day,
            "swab_n": sum(r["swab_n"] for r in chunk),
            "swab_detected": sum(r["swab_detected"] for r in chunk),
            "swab_censored": sum(r["swab_censored"] for r in chunk),
            "swab_max_density": max(r["swab_max_density"] for r in chunk),
            "tank_assays": sum(1 for r in chunk if r["tank"]),
            "tank_detected": sum(1 for r in chunk if r.get("tank_detected")),
            "tank_max_log10_copies_per_l": max(logs, default=None),
        })
    return {
        "swab_source": "work.swab_results (surface_pool_density)",
        "tank_source": "work.wastewater_ht_result (holding_tank)",
        "epochs_observed": len(rows),
        "swab_total": sum(r["swab_n"] for r in rows),
        "swab_detected_total": sum(r["swab_detected"] for r in rows),
        "swab_first_detected_epoch": next(
            (r["epoch"] for r in rows if r["swab_detected"]), None,
        ),
        "tank_assays": len(tank_rows),
        "tank_detected_total": sum(1 for r in tank_rows if r["tank_detected"]),
        "tank_first_detected_epoch": next(
            (r["epoch"] for r in tank_rows if r["tank_detected"]), None,
        ),
        "daily": daily,
    }


def burden(voyage: dict[str, Any]) -> dict[str, Any]:
    summary = voyage["summary"]
    keys = (
        "passenger_complement", "crew_complement",
        "cumulative_reported_cases_passenger", "cumulative_reported_cases_crew",
        "cumulative_ever_ill_passenger", "cumulative_ever_ill_crew",
        "cumulative_ever_infected_passenger", "cumulative_ever_infected_crew",
    )
    out = {key: summary.get(key) for key in keys}
    out["rep_pax_n"] = out["cumulative_reported_cases_passenger"]
    out["rep_crew_n"] = out["cumulative_reported_cases_crew"]
    return out


def fingerprint(voyage: dict[str, Any]) -> str:
    """Hash of the voyage blocks, engine commit excluded.

    ``parameters.engine_git_sha`` names the commit, not the draw, so a
    labelled baseline re-run on a later commit can still be bit-identical.
    """
    body = dict(voyage)
    body["parameters"] = {
        k: v for k, v in (voyage.get("parameters") or {}).items()
        if k != "engine_git_sha"
    }
    blob = json.dumps(body, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


def _read_line_list(path: str) -> dict[str, Any]:
    if not Path(path).is_file():
        return {}
    return validated_json_load(REPO_ROOT, Path(path))


def run_voyage(
    spec_dict: dict[str, Any], clock: str | None, *, instrumented: bool,
) -> dict[str, Any]:
    """One voyage. ``instrumented=False`` is the draw-neutrality control."""
    spec = json.loads(json.dumps(spec_dict))
    recorder = EnvRecorder()
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
        line_path = resolve_child_path(tmp, "sentinel_line_list.json")
        if instrumented:
            spec.setdefault("run", {})["sentinel_line_list"] = line_path
        with materialized_picard_spec(spec, REPO_ROOT) as picard_spec:
            sim = ShipSimulation(picard_spec, display=False)
            sim.initialize()
            echo = config_echo(sim, spec_dict.get("config_overrides") or {})
            if instrumented:
                sim.epoch_observer = recorder.observe
            started = time.perf_counter()
            result = sim.run()
            wall = time.perf_counter() - started
            epochs_per_day = max(1, round(24.0 / sim.clock.hours_per_epoch))
        line_list = _read_line_list(line_path) if instrumented else {}
    num_agents = int(
        (spec_dict.get("config_overrides") or {})
        .get("ship_graph", {}).get("num_agents", 0),
    )
    voyage: dict[str, Any] = {}
    _attach_voyage_blocks(
        voyage, spec_dict, result, num_agents, natural_history_clock=clock,
    )
    return {
        "voyage": voyage,
        "echo": echo,
        "env_rows": recorder.rows,
        "line_list": line_list,
        "epochs_per_day": epochs_per_day,
        "wall_clock_s": round(wall, 2),
    }


def harvest(run: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """(summary-side scalars, member payload) for the six families."""
    voyage = run["voyage"]
    series = voyage["timeseries"]
    epd = run["epochs_per_day"]
    curve_block = curves(series, run["line_list"], epd)
    env_block = environment(run["env_rows"], epd)
    scalars = {
        "schema": SCHEMA,
        "burden": burden(voyage),
        "threshold": {
            "vsp_trigger_epoch": voyage["derived"].get("vsp_trigger_epoch"),
            "posted": voyage["derived"].get("vsp_trigger_epoch") is not None,
        },
        "first_role": first_role(series),
        "curves": {
            k: curve_block[k] for k in (
                "n_days", "day0_label", "preboarding_reported_passenger",
                "preboarding_reported_crew", "line_list_cases",
            )
        },
        "environment": {
            k: v for k, v in env_block.items() if k != "daily"
        },
        "voyage_fingerprint_sha256": fingerprint(voyage),
        "config_echo": {
            k: run["echo"][k] for k in
            ("n_leaves", "mismatched", "overrides_sha256")
        },
        "wall_clock_s": run["wall_clock_s"],
    }
    member = {
        "schema": SCHEMA,
        "curves": curve_block,
        "environment": env_block,
        "config_echo_resolved": run["echo"]["resolved"],
    }
    return scalars, member


def write_cell(
    out_dir: Path, tier: str, run_id: str, run: dict[str, Any],
) -> Path:
    voyage = run["voyage"]
    scalars, member = harvest(run)
    anchor = {
        "run_id": run_id,
        "parameters": voyage["parameters"],
        "num_epochs": len(voyage["timeseries"]),
        "trigger_status": voyage.get("trigger_status"),
        "summary": voyage["summary"],
        "cost_accounting": voyage["cost_accounting"],
        "derived": voyage["derived"],
        "timeseries": voyage["timeseries"],
        "joint_eval": scalars,
    }
    if "role_checkpoints" in voyage:
        anchor["role_checkpoints"] = voyage["role_checkpoints"]
    return write_run_zip(out_dir, tier, run_id, anchor, {
        MEMBER: gzip.compress(json.dumps(member).encode("utf-8")),
    })


def verify_draws(spec: dict[str, Any], clock: str | None) -> dict[str, Any]:
    """Instrumented vs uninstrumented voyage on the identical spec."""
    probe = fingerprint(run_voyage(spec, clock, instrumented=True)["voyage"])
    control = fingerprint(run_voyage(spec, clock, instrumented=False)["voyage"])
    return {
        "seed": int(spec["run"]["random_seed"]),
        "instrument": "epoch_observer(env)+sentinel_line_list",
        "instrumented_sha256": probe,
        "control_sha256": control,
        "voyage_fingerprint_equal": probe == control,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    add_manifest_args(parser, required=True)
    parser.add_argument("--seeds", type=int, nargs="*", default=None)
    parser.add_argument("--pathogen-id", type=str, default="norwalk_gi")
    parser.add_argument(
        "--epochs-override", type=int, default=None,
        help="smoke-only: override the tier's epoch count",
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--verify-draws", action="store_true",
        help="run each selected seed twice (instrumented vs control); "
             "writes verify_draws_<tier>.json and no cell zips",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = validated_json_load(REPO_ROOT, args.manifest)
    clock = manifest.get("natural_history_clock")
    runs = list(generate_tier_runs(
        manifest, args.tier, epochs_override=args.epochs_override,
        natural_history_clock=str(clock) if clock is not None else None,
    ))
    runs = filter_runs_by_seeds(
        index_run(runs, args.index, args.tier), args.seeds or None,
    )
    out_dir = Path(
        prepare_output_directory(str(args.out), allowed_roots=(str(REPO_ROOT),)),
    )
    if args.verify_draws:
        checks = [verify_draws(spec, clock) for _run_id, spec in runs]
        path = resolve_child_path(str(out_dir), f"verify_draws_{args.tier}.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"checks": checks}, handle, indent=1)
        print(json.dumps({"checks": checks}, indent=1))
        return 0 if all(c["voyage_fingerprint_equal"] for c in checks) else 1
    for run_id, spec in runs:
        run = run_voyage(spec, clock, instrumented=True)
        zip_path = write_cell(out_dir, args.tier, run_id, run)
        print(
            f"seed {spec['run']['random_seed']}: "
            f"posted={run['voyage']['derived'].get('vsp_trigger_epoch')} "
            f"echo_mismatch={len(run['echo']['mismatched'])} -> {zip_path}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
