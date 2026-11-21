#!/usr/bin/env python3
"""Paper-1 WP2 joint-evaluation cell: six outcome families from one run.

One voyage per array child, spec taken verbatim from the campaign manifest
tier (``generate_tier_runs``), so the tier's ``config_overrides`` reaches the
engine through the verified loader path. Nothing here changes engine
behaviour or adds an engine output field.

The output contract is ``OUTPUT_CONTRACT`` below: for each family, what the
worker requests, where it reads it, and how a missing source is recorded.
Every archive carries a ``families`` block with an explicit status per
family, so "not requested", "requested and empty" and "missing" are
distinguishable.

Input checks, made after the runner has applied every axis and the engine
has initialised (a failed check exits non-zero; no archive is written):

* the tier's effective ``config_overrides`` differs from the manifest's
  invariant baseline block on exactly the paths the tier declares;
* the runner changed no leaf the tier declared (the paths it added are
  recorded);
* every leaf of the run spec's ``config_overrides`` equals the
  engine-resolved ``sim.cfg``;
* the initialised passenger and crew counts equal the tier's intended
  counts, and so do the complements in the outcome payload.

Environment harvest: campaign runs use ``history_retention: compact``, whose
epoch record drops the ``observation_engine`` block. Swab and holding-tank
results are therefore read output-only through
``ShipSimulation.epoch_observer``. The observer reads results the epoch
already produced and draws nothing; ``--verify-draws`` measures that by
running the same spec with no observer and no line list and comparing
voyage fingerprints.

Zip members: ``summary.json`` (campaign anchor layout plus ``joint_eval``)
and ``joint_eval.json.gz`` (curves, environment rows, resolved config).
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

SCHEMA = "paper1_joint_eval_cell/2.0.0"
THRESHOLD = 0.03
MEMBER = "joint_eval.json.gz"
ABSENT = "<absent>"
DAY0_LABEL = (
    "day 0 includes pre-boarding AGE declarations seeded at embarkation "
    "(preboarding_reportable_ids); see preboarding_reported_*"
)
FIRST_ROLE_CLASSES = (
    "passenger_first", "crew_first", "same_epoch", "neither", "missing",
)
OUTPUT_CONTRACT: dict[str, dict[str, str]] = {
    "burden": {
        "request": "none (always emitted)",
        "source": "final-epoch summary cumulative_reported_cases_*, "
                  "cumulative_ever_ill_*, cumulative_ever_infected_*, "
                  "role complements",
    },
    "threshold": {
        "request": "none (always emitted)",
        "source": "derived.vsp_trigger_epoch (either channel at 3% of "
                  "that channel's complement)",
    },
    "size_distribution": {
        "request": "none; an ensemble property",
        "source": "seed ensemble of burden and threshold, computed by "
                  "readout.py -- no per-run field",
    },
    "first_role": {
        "request": "none (always emitted)",
        "source": "per-epoch cumulative_reported_cases_{passenger,crew} "
                  "over the role complement against 0.03; classes "
                  + " / ".join(FIRST_ROLE_CLASSES),
    },
    "curves": {
        "request": "run.sentinel_line_list set explicitly by this worker "
                   "(the campaign runner arms it only for shore-exposure "
                   "or variant-surveillance runs)",
        "source": "onsets: line-list clinical_cases.onset_epoch; reporting "
                  "curve: per-epoch cumulative_reported_cases_* (not the "
                  "line list's report_epoch, which is detection clamped to "
                  "onset)",
    },
    "environment": {
        "request": "output-only harvest via ShipSimulation.epoch_observer "
                   "(compact retention drops observation_engine)",
        "source": "work.swab_results (targeted surface swab, "
                  "surface_pool_density) and work.wastewater_ht_result "
                  "(holding-tank qPCR assay). The wastewater_sequencing "
                  "channel is a different instrument and is not harvested",
    },
}
ENV_UNITS = {
    "swab.epoch": "simulation epoch (hours since embarkation / "
                  "hours_per_epoch)",
    "swab.density": "genome copies per cm2 of high-touch area",
    "swab.recovered": "genome copies recovered per swab",
    "swab.lod": "genome copies per swab",
    "tank.concentration": "genome copies per litre of tank contents",
    "tank.lod": "genome copies per litre",
    "tank.loq": "genome copies per litre",
}


class ContractError(SystemExit):
    """An input check failed; the run writes no archive."""


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
            return ABSENT
        node = node[part]
    return node


def canonical_sha(tree: dict[str, Any]) -> str:
    blob = json.dumps(tree, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def changed_paths(
    baseline: dict[str, Any], effective: dict[str, Any],
) -> list[dict[str, Any]]:
    """Leaf paths on which *effective* differs from *baseline*."""
    base = dict(leaf_items(baseline))
    arm = dict(leaf_items(effective))
    return [
        {"path": path, "baseline": base.get(path, ABSENT),
         "arm": arm.get(path, ABSENT)}
        for path in sorted(set(base) | set(arm))
        if base.get(path, ABSENT) != arm.get(path, ABSENT)
    ]


def check_arm(manifest: dict[str, Any], tier_id: str) -> dict[str, Any]:
    """The tier differs from the baseline block only where it says it does."""
    design = manifest["joint_eval"]
    tier = manifest["tiers"][tier_id]
    meta = tier["joint_eval"]
    actual = changed_paths(design["baseline_block"], tier["config_overrides"])
    if actual != meta["changed_paths"]:
        raise ContractError(
            f"{tier_id}: effective config differs from the baseline on "
            f"{[c['path'] for c in actual]}, declared "
            f"{[c['path'] for c in meta['changed_paths']]}",
        )
    return {
        "arm": meta["arm"],
        "baseline_sha256": canonical_sha(design["baseline_block"]),
        "effective_sha256": canonical_sha(tier["config_overrides"]),
        "changed_paths": actual,
    }


def check_effective(
    sim: Any, tier_overrides: dict[str, Any], spec_overrides: dict[str, Any],
) -> dict[str, Any]:
    """Validate the config after the runner applied every axis.

    ``tier_overrides`` is what the manifest declared; ``spec_overrides`` is
    what ``generate_tier_runs`` produced from it; ``sim.cfg`` is what the
    engine resolved after ``initialize()``.
    """
    declared = dict(leaf_items(tier_overrides))
    spec = dict(leaf_items(spec_overrides))
    runner_changed = sorted(
        path for path, want in declared.items()
        if spec.get(path, ABSENT) != want
    )
    resolved = {path: get_path(sim.cfg, path) for path in spec}
    unresolved = sorted(p for p, want in spec.items() if resolved[p] != want)
    if runner_changed or unresolved:
        raise ContractError(
            f"effective config check failed: runner changed "
            f"{runner_changed}; engine resolved differently {unresolved}",
        )
    return {
        "n_declared_leaves": len(declared),
        "n_effective_leaves": len(spec),
        "runner_added_paths": sorted(set(spec) - set(declared)),
        "runner_changed_paths": runner_changed,
        "mismatched": unresolved,
        "resolved": resolved,
    }


def check_roles(
    sim: Any, intended: dict[str, int], where: str,
    counts: dict[str, int] | None = None,
) -> dict[str, int]:
    """Intended passenger/crew counts against the initialised agents."""
    if counts is None:
        agents = sim.engine.agents
        crew = sum(1 for a in agents if a.role == "crew")
        counts = {"passenger": len(agents) - crew, "crew": crew}
    want = {k: int(intended[k]) for k in ("passenger", "crew")}
    if counts != want:
        raise ContractError(
            f"role counts in {where} are {counts}, intended {want}",
        )
    return counts


class EnvRecorder:
    """Swab and holding-tank results read from the epoch scratch pad.

    Every swab is counted per epoch. A swab that recovered any copies keeps
    its own row (zone, epoch, amount, units via ``ENV_UNITS``, censoring);
    a swab that recovered nothing is represented by the per-epoch count
    alone, so the member stays bounded on the mega hull.
    """

    def __init__(self) -> None:
        self.epochs: list[dict[str, Any]] = []
        self.swabs: list[dict[str, Any]] = []
        self.tank: list[dict[str, Any]] = []
        self.zones: set[str] = set()

    def _swab_row(self, epoch: int, zone: str, swab: dict[str, Any]) -> None:
        if not (swab.get("recovered_copies") or 0) > 0:
            return
        self.swabs.append({
            "epoch": epoch,
            "zone": zone,
            "surface_class": swab.get("surface_class"),
            "density": swab.get("surface_density_copies_per_cm2"),
            "recovered": swab.get("recovered_copies"),
            "lod": swab.get("lod_copies_per_swab"),
            "detected": bool(swab.get("detected")),
            "censored_below_lod": bool(swab.get("censored_below_lod")),
        })

    def _tank_row(self, epoch: int, tank: dict[str, Any]) -> None:
        self.tank.append({
            "epoch": epoch,
            "instrument": tank.get("instrument"),
            "stream": tank.get("stream"),
            "concentration": tank.get("concentration_copies_per_l"),
            "lod": tank.get("lod_copies_per_l"),
            "loq": tank.get("loq_copies_per_l"),
            "detected": bool(tank.get("detected")),
            "quantifiable": bool(tank.get("quantifiable")),
            "censored_below_lod": bool(tank.get("censored_below_lod")),
        })

    def observe(self, _sim: Any, work: Any) -> None:
        epoch = int(work.epoch)
        swabs = getattr(work, "swab_results", None) or {}
        tank = getattr(work, "wastewater_ht_result", None)
        for zone, swab in swabs.items():
            self.zones.add(str(zone))
            self._swab_row(epoch, str(zone), swab)
        self.epochs.append({
            "epoch": epoch,
            "swab_n": len(swabs),
            "swab_detected": sum(1 for s in swabs.values() if s.get("detected")),
            "swab_censored": sum(
                1 for s in swabs.values() if s.get("censored_below_lod")
            ),
            "tank_assayed": tank is not None,
        })
        if tank is not None:
            self._tank_row(epoch, tank)


def _first_crossing(series: list[dict[str, Any]], role: str) -> int | None:
    for row in series:
        complement = row.get(f"{role}_complement") or 0
        count = row.get(f"cumulative_reported_cases_{role}") or 0
        if complement and count / complement >= THRESHOLD:
            return int(row["epoch"])
    return None


_ROLE_SERIES_KEYS = (
    "passenger_complement", "crew_complement",
    "cumulative_reported_cases_passenger", "cumulative_reported_cases_crew",
)


def first_role(series: list[dict[str, Any]]) -> dict[str, Any]:
    """Which role's cumulative reports reached 3% of its complement first.

    ``missing`` when the series is empty or lacks a role series or a
    positive complement -- never folded into ``neither``.
    """
    out: dict[str, Any] = {
        "threshold": THRESHOLD, "passenger_epoch": None, "crew_epoch": None,
    }
    usable = bool(series) and all(
        row.get(key) is not None for row in series for key in _ROLE_SERIES_KEYS
    ) and all(
        (series[-1].get(k) or 0) > 0
        for k in ("passenger_complement", "crew_complement")
    )
    if not usable:
        return {**out, "first_role": "missing"}
    pax = _first_crossing(series, "passenger")
    crew = _first_crossing(series, "crew")
    if pax is None and crew is None:
        role = "neither"
    elif crew is None or (pax is not None and pax < crew):
        role = "passenger_first"
    elif pax is None or crew < pax:
        role = "crew_first"
    else:
        role = "same_epoch"
    return {**out, "passenger_epoch": pax, "crew_epoch": crew, "first_role": role}


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
        "line_list_requested": True,
        "line_list_received": "clinical_cases" in line_list,
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


def environment(rec: EnvRecorder) -> dict[str, Any]:
    detected_swabs = [r for r in rec.swabs if r["detected"]]
    detected_tank = [r for r in rec.tank if r["detected"]]
    return {
        "harvest": "output-only via ShipSimulation.epoch_observer",
        "channels": {
            "swab": "targeted_surface_swab (surface_pool_density)",
            "tank": "wastewater_holding_tank qPCR assay",
            "not_harvested": "wastewater_sequencing",
        },
        "units": ENV_UNITS,
        "epochs_observed": len(rec.epochs),
        "zones_swabbed": sorted(rec.zones),
        "swab_total": sum(r["swab_n"] for r in rec.epochs),
        "swab_rows_kept": len(rec.swabs),
        "swab_rows_rule": "one row per swab with recovered copies > 0; "
                          "zero-recovery swabs are in swab_total only",
        "swab_detected_total": len(detected_swabs),
        "swab_censored_total": sum(
            1 for r in rec.swabs if r["censored_below_lod"]
        ),
        "swab_first_detected_epoch": min(
            (r["epoch"] for r in detected_swabs), default=None,
        ),
        "tank_assays": len(rec.tank),
        "tank_detected_total": len(detected_tank),
        "tank_censored_total": sum(
            1 for r in rec.tank if r["censored_below_lod"]
        ),
        "tank_first_detected_epoch": min(
            (r["epoch"] for r in detected_tank), default=None,
        ),
        "per_epoch": rec.epochs,
        "swab_rows": rec.swabs,
        "tank_rows": rec.tank,
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


VOYAGE_KEYS = (
    "parameters", "trigger_status", "timeseries", "derived", "summary",
    "cost_accounting", "role_checkpoints",
)


def fingerprint(voyage: dict[str, Any]) -> str:
    """Hash of the voyage blocks, engine commit excluded.

    ``parameters.engine_git_sha`` names the commit, not the draw, so a
    reproduction arm re-run on a later commit can still be bit-identical.
    Hashed after a JSON round trip so the same function applied to an
    archived ``summary.json`` (``readout.py``) gives the same digest.
    """
    body = json.loads(json.dumps(
        {k: voyage[k] for k in VOYAGE_KEYS if k in voyage}, default=str,
    ))
    body["parameters"] = {
        k: v for k, v in (body.get("parameters") or {}).items()
        if k != "engine_git_sha"
    }
    blob = json.dumps(body, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def _read_line_list(path: str) -> dict[str, Any]:
    if not Path(path).is_file():
        return {}
    return validated_json_load(REPO_ROOT, Path(path))


def run_voyage(
    spec_dict: dict[str, Any], clock: str | None, *, instrumented: bool,
    tier: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One voyage. ``instrumented=False`` is the draw-neutrality control.

    With *tier* given, the effective-config and role-count checks run after
    ``initialize()`` and before any epoch is stepped.
    """
    spec = json.loads(json.dumps(spec_dict))
    recorder = EnvRecorder()
    checks: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
        line_path = resolve_child_path(tmp, "sentinel_line_list.json")
        if instrumented:
            spec.setdefault("run", {})["sentinel_line_list"] = line_path
        with materialized_picard_spec(spec, REPO_ROOT) as picard_spec:
            sim = ShipSimulation(picard_spec, display=False)
            sim.initialize()
            if tier is not None:
                checks["effective_config"] = check_effective(
                    sim, tier["config_overrides"],
                    spec_dict.get("config_overrides") or {},
                )
                checks["roles_initialised"] = check_roles(
                    sim, tier["joint_eval"]["intended_roles"],
                    "initialised agents",
                )
            if instrumented:
                sim.epoch_observer = recorder.observe
            started = time.perf_counter()
            result = sim.run()
            wall = time.perf_counter() - started
            epochs_per_day = max(1, round(sim.clock.epochs_per_day))
        line_list = _read_line_list(line_path) if instrumented else {}
    num_agents = int(
        (spec_dict.get("config_overrides") or {})
        .get("ship_graph", {}).get("num_agents", 0),
    )
    voyage: dict[str, Any] = {}
    _attach_voyage_blocks(
        voyage, spec_dict, result, num_agents, natural_history_clock=clock,
    )
    if tier is not None:
        summary = voyage["summary"]
        checks["roles_payload"] = check_roles(
            sim, tier["joint_eval"]["intended_roles"], "outcome payload",
            counts={
                "passenger": int(summary.get("passenger_complement") or 0),
                "crew": int(summary.get("crew_complement") or 0),
            },
        )
    return {
        "voyage": voyage,
        "checks": checks,
        "recorder": recorder,
        "line_list": line_list,
        "epochs_per_day": epochs_per_day,
        "wall_clock_s": round(wall, 2),
    }


def family_status(
    scalars: dict[str, Any], curve_block: dict[str, Any],
    env_block: dict[str, Any], expected_epochs: int,
) -> dict[str, dict[str, str]]:
    """Explicit present/missing status per family, with the reason."""
    def status(ok: bool, reason: str) -> dict[str, str]:
        return {"status": "present" if ok else "missing", "reason": reason}

    burden_block = scalars["burden"]
    return {
        "burden": status(
            all(burden_block.get(k) is not None for k in (
                "rep_pax_n", "rep_crew_n",
                "passenger_complement", "crew_complement",
            )),
            "final-epoch role counts and complements",
        ),
        "threshold": status(
            "vsp_trigger_epoch" in scalars["threshold"],
            "derived.vsp_trigger_epoch key (null = did not post)",
        ),
        "size_distribution": status(
            True, "ensemble property; computed by readout.py",
        ),
        "first_role": status(
            scalars["first_role"]["first_role"] != "missing",
            "role cumulative series and complements",
        ),
        "curves": status(
            bool(curve_block["line_list_received"])
            and len(curve_block["reported_daily_passenger"])
            == curve_block["n_days"] > 0,
            "line list received (may hold zero cases) and reporting "
            "series covers every day",
        ),
        "environment": status(
            env_block["epochs_observed"] == expected_epochs
            and env_block["swab_total"] > 0
            and env_block["tank_assays"] > 0,
            "observer saw every epoch, with swabs and tank assays",
        ),
    }


def harvest(
    run: dict[str, Any], arm: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """(summary-side scalars, member payload) for the six families."""
    voyage = run["voyage"]
    series = voyage["timeseries"]
    curve_block = curves(series, run["line_list"], run["epochs_per_day"])
    env_block = environment(run["recorder"])
    posted_epoch = voyage["derived"].get("vsp_trigger_epoch")
    effective = run["checks"]["effective_config"]
    scalars: dict[str, Any] = {
        "schema": SCHEMA,
        "output_contract": OUTPUT_CONTRACT,
        "burden": burden(voyage),
        "threshold": {
            "vsp_trigger_epoch": posted_epoch,
            "posted": posted_epoch is not None,
        },
        "first_role": first_role(series),
        "curves": {
            k: curve_block[k] for k in (
                "line_list_requested", "line_list_received", "n_days",
                "day0_label", "preboarding_reported_passenger",
                "preboarding_reported_crew", "line_list_cases",
            )
        },
        "environment": {
            k: v for k, v in env_block.items()
            if k not in ("per_epoch", "swab_rows", "tank_rows", "zones_swabbed")
        },
        "voyage_fingerprint_sha256": fingerprint(voyage),
        "arm": arm,
        "effective_config": {
            k: v for k, v in effective.items() if k != "resolved"
        },
        "roles": {
            "initialised": run["checks"]["roles_initialised"],
            "payload": run["checks"]["roles_payload"],
        },
        "wall_clock_s": run["wall_clock_s"],
    }
    scalars["families"] = family_status(
        scalars, curve_block, env_block, len(series),
    )
    member = {
        "schema": SCHEMA,
        "curves": curve_block,
        "environment": env_block,
        "effective_config_resolved": effective["resolved"],
    }
    return scalars, member


def write_cell(
    out_dir: Path, tier: str, run_id: str, run: dict[str, Any],
    arm: dict[str, Any],
) -> Path:
    voyage = run["voyage"]
    scalars, member = harvest(run, arm)
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
    arm = check_arm(manifest, args.tier)
    tier = manifest["tiers"][args.tier]
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
        run = run_voyage(spec, clock, instrumented=True, tier=tier)
        zip_path = write_cell(out_dir, args.tier, run_id, run, arm)
        print(
            f"seed {spec['run']['random_seed']}: "
            f"posted={run['voyage']['derived'].get('vsp_trigger_epoch')} "
            f"roles={run['checks']['roles_initialised']} -> {zip_path}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
