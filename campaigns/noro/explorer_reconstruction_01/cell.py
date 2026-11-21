#!/usr/bin/env python3
"""WP3 Explorer reconstruction cell worker: one (tier, seed) voyage.

A manifest-tier worker (``--manifest --tier --index``). It differs from the
stock campaign cell in five ways, none of which touches the engine:

* the tier's ``introduction`` names a block in the manifest's
  ``introduction_blocks``; its ``explicit_seeds`` are composed into the
  spec's ``initiation`` beside the runner's own boarding block, so the
  tier's ``config_overrides`` stays the Paper-1 frozen block verbatim;
* the tier's ``complement`` names a declared role allocation; exact head
  counts are composed into ``ship_graph`` the same way (the engine otherwise
  splits the complement 70/30, not the investigation's 3,245 / 1,183) and
  the initialized counts are asserted before the first epoch;
* a tier may name a declared difference arm (contract section 2.9) in the
  manifest's ``arm_blocks``; its complete effective objects are composed
  the same way, and after initialization every declared path is read back
  from the merged config on arm and reference cells alike, so a paired
  cell that does not differ exactly as declared aborts before epoch 0;
* ``run.sentinel_line_list`` is armed, so the per-person onset line list
  survives ``compact`` retention;
* the archive carries day-binned onset and reporting curves, the
  introduction witness, the frozen-block witness, the hull-dependent
  effective mechanism state and the first epoch each response protocol was
  active.

``--epochs-override`` shortens the voyage for a local wiring check only;
Batch cells always run the tier's declared length.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_RUNNER_DIR = _REPO_ROOT / "picard_framework" / "runs" / "mega_cruise_campaign"
if str(_RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(_RUNNER_DIR))

from campaign_runner import engine_git_sha, generate_tier_runs  # noqa: E402

from engines.rhythm_layer import platform_has_rhythm_catalog  # noqa: E402
from picard_framework.simulation.ship_simulation import (  # noqa: E402
    ShipSimulation,
)
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_child_path,
)
from tools.diag.instrument_common import (  # noqa: E402
    materialized_picard_spec,
)
from tools.diag.json_io import validated_json_load  # noqa: E402
from tools.diag.manifest_args import add_manifest_args, index_run  # noqa: E402
from tools.diag.readout_common import write_run_zip  # noqa: E402
from tools.noro_diag.per_host_dose_challenge import (  # noqa: E402
    _attach_voyage_blocks,
)

ROLES = ("passenger", "crew")
# Frozen outside the block (contract section 2.5). Neither the shared job
# definition nor the campaign image sets it, so the worker pins it itself.
HASH_SEED = "1"
_SERIES_KEYS = {
    role: f"cumulative_reported_cases_{role}" for role in ROLES
}


def compose_introduction(
    spec: dict[str, Any], manifest: dict[str, Any], tier: str,
) -> str:
    """Add the tier's declared ``explicit_seeds`` to the spec; return its id.

    The runner already wrote ``initiation.boarding``; the seeds are added
    beside it, never in place of it (explicit seeds are additive with the
    boarding draw by construction).
    """
    name = str(manifest["tiers"][tier]["introduction"])
    block = manifest["introduction_blocks"][name]
    seeds = [dict(seed) for seed in block.get("explicit_seeds") or ()]
    if seeds:
        overrides = spec.setdefault("config_overrides", {})
        initiation = dict(overrides.get("initiation") or {})
        initiation["explicit_seeds"] = seeds
        overrides["initiation"] = initiation
    return name


def compose_complement(
    spec: dict[str, Any], manifest: dict[str, Any], tier: str,
) -> tuple[str, dict[str, int]]:
    """Declare the tier's head-count classes, if any; return (id, intended)."""
    name = str(manifest["tiers"][tier]["complement"])
    block = manifest["complement_blocks"][name]
    if block["agent_classes"] is not None:
        graph = spec.setdefault("config_overrides", {}).setdefault(
            "ship_graph", {},
        )
        graph["agent_classes"] = [dict(cls) for cls in block["agent_classes"]]
    return name, {role: int(block["intended"][role]) for role in ROLES}


REFERENCE_ARM = "reference"


def _leaf(tree: Any, dotted: str) -> Any:
    for key in dotted.split("."):
        tree = tree.get(key) if isinstance(tree, dict) else None
    return tree


def compose_arm(
    spec: dict[str, Any], manifest: dict[str, Any], tier: str,
) -> str:
    """Write the tier's declared arm objects into the spec; return its id.

    Applied after the runner's axes, as whole second-level objects (both
    config merges are one level deep). A reference tier composes nothing.
    """
    arm = str(manifest["tiers"][tier].get("arm", REFERENCE_ARM))
    if arm != REFERENCE_ARM:
        overrides = spec.setdefault("config_overrides", {})
        for key, value in manifest["arm_blocks"][arm]["effective_objects"].items():
            overrides[key] = json.loads(json.dumps(value))
    return arm


def arm_witness(
    manifest: dict[str, Any], arm: str, resolved: dict[str, Any],
    state: dict[str, Any],
) -> dict[str, Any]:
    """Every declared arm path as the engine resolved it, with mismatches.

    A reference cell must resolve each path to its baseline value and an
    arm cell to its arm value, so a pair differs on the declared paths and
    the two sides are known to be on opposite sides of each.
    """
    paths, mismatches = [], []
    for name, block in (manifest.get("arm_blocks") or {}).items():
        side = "arm" if name == arm else "baseline"
        for change in block["changed_paths"]:
            value = _leaf(resolved, change["path"])
            paths.append({**change, "declared_by": name, "resolved": value})
            if value != change[side]:
                mismatches.append(
                    f"{change['path']} resolved {value!r}, {side} declares "
                    f"{change[side]!r}",
                )
        if side != "arm":
            continue
        for key, wanted in block["effective_objects"].items():
            if resolved.get(key) != wanted:
                mismatches.append(f"{key} is not the declared object")
        for key, wanted in block["effective_state"].items():
            if state.get(key) != wanted:
                mismatches.append(f"{key} is {state.get(key)!r}")
    block = (manifest.get("arm_blocks") or {}).get(arm) or {}
    return {
        "arm": arm,
        "changed_paths": paths,
        "resolved_objects": {
            key: resolved.get(key) for key in block.get("effective_objects", {})
        },
        "mismatches": mismatches,
    }


def realized_complement(sim: Any) -> dict[str, int]:
    roles = [str(agent.role) for agent in sim.engine.agents]
    return {role: roles.count(role) for role in ROLES}


def initially_infected_agent_ids(sim: Any) -> set[int]:
    """Agents carrying an active infection at initialize.

    Everyone in this set boarded already infected: the declared explicit
    seeds plus any boarding-prevalence draw. Read it at initialize, before
    epoch 0, so an incident-aboard onset curve can exclude all prevalent
    boarders and not just the declared seeds.
    """
    infected: set[int] = set()
    for agent in sim.engine.agents:
        infections = getattr(agent, "infections", None) or {}
        for record in infections.values():
            status = (record or {}).get("status")
            if getattr(status, "name", status) == "INFECTED":
                infected.add(int(agent.agent_id))
                break
    return infected


def check_expected_state(
    manifest: dict[str, Any], tier: str, state: dict[str, Any],
) -> list[str]:
    """Requested/effective mechanism state vs the tier's declared state.

    ``tiers[tier]["expected_state"]`` declares each of ``rhythm_requested``,
    ``rhythm_layer_active`` and the exposure-cap pair for that hull and arm:
    requested and attached on hulls with a rhythm catalog, requested but
    absent on Explorer's exception, disabled and absent on the rhythm-off
    arms. An absent layer where the hull declares one is a mismatch here,
    not an arm-path resolution issue.
    """
    expected = manifest["tiers"][tier].get("expected_state") or {}
    return [
        f"{key} is {state.get(key)!r}, declared {want!r}"
        for key, want in expected.items()
        if state.get(key) != want
    ]


def effective_state(sim: Any, platform: str) -> dict[str, Any]:
    """Mechanisms whose effective state depends on the hull, read back.

    The exposure cap and the rhythm layer both apply only to platform ids
    carried by ``data/rhythm/event_catalogs.json``, so the same requested
    block can resolve to different mechanisms on different hulls.
    """
    transmission = sim.cfg.get("transmission") or {}
    return {
        "rhythm_catalog": bool(platform_has_rhythm_catalog(platform)),
        "exposure_cap_requested": bool(
            (transmission.get("exposure_cap") or {}).get("enabled", False),
        ),
        "exposure_cap_active": bool(sim.tx_core._exposure_cap_active),
        "rhythm_requested": bool(
            (sim.cfg.get("rhythm") or {}).get("enabled", True),
        ),
        "rhythm_layer_active": getattr(sim.engine, "_rhythm", None) is not None,
    }


def block_mismatches(
    block: Any, resolved: Any, prefix: str = "",
) -> tuple[int, list[dict[str, Any]]]:
    """(leaf count, leaves of ``block`` the merged config does not carry)."""
    if isinstance(block, dict):
        count, missing = 0, []
        for key, value in block.items():
            child = resolved.get(key) if isinstance(resolved, dict) else None
            sub_count, sub_missing = block_mismatches(
                value, child, f"{prefix}{key}.",
            )
            count += sub_count
            missing += sub_missing
        return count, missing
    if block == resolved:
        return 1, []
    return 1, [{"key": prefix[:-1], "pinned": block, "resolved": resolved}]


def day_index(clock: Any, epoch: int, n_days: int) -> int:
    """Voyage day (0 = embarkation day) an epoch falls on."""
    return min(int(clock.days_elapsed(int(epoch))), n_days - 1)


def onset_curves(
    cases: list[dict[str, Any]], declared_ids: set[int], clock: Any,
    n_days: int, prevalent_ids: set[int] | None = None,
) -> dict[str, Any]:
    """Day-binned line-list onsets per role, three labellings.

    ``all`` is first observed symptom aboard, the observed-onset curve.
    ``excluding_declared_seeds`` drops only the imposed seeds, so it still
    contains boarders already ill from the boarding draw. ``incident``
    drops every agent infected at initialize (``prevalent_ids``), the
    incident-onset comparator.
    """
    prevalent = prevalent_ids if prevalent_ids is not None else declared_ids
    every = {role: [0] * n_days for role in ROLES}
    aboard = {role: [0] * n_days for role in ROLES}
    incident = {role: [0] * n_days for role in ROLES}
    for case in cases:
        role = "crew" if case["crew"] else "passenger"
        pid = int(case["person_id"])
        day = day_index(clock, case["onset_epoch"], n_days)
        every[role][day] += 1
        if pid not in declared_ids:
            aboard[role][day] += 1
        if pid not in prevalent:
            incident[role][day] += 1
    return {
        "all": every,
        "excluding_declared_seeds": aboard,
        "incident": incident,
    }


def reporting_curves(
    series: list[dict[str, Any]], clock: Any, n_days: int,
) -> dict[str, Any]:
    """End-of-day cumulative reported cases per role and their increments."""
    cumulative = {role: [0] * n_days for role in ROLES}
    for row in series:
        day = day_index(clock, row["epoch"], n_days)
        for role in ROLES:
            cumulative[role][day] = int(row.get(_SERIES_KEYS[role], 0))
    for role in ROLES:
        for day in range(1, n_days):
            cumulative[role][day] = max(
                cumulative[role][day], cumulative[role][day - 1],
            )
    daily = {
        role: [
            values[day] - (values[day - 1] if day else 0)
            for day in range(n_days)
        ]
        for role, values in cumulative.items()
    }
    first = series[0] if series else {}
    return {
        "cumulative_end_of_day": cumulative,
        "daily_new": daily,
        "epoch_zero_cumulative": {
            role: int(first.get(_SERIES_KEYS[role], 0)) for role in ROLES
        },
    }


class ProtocolWatch:
    """First epoch, and epoch count, each response protocol was active."""

    def __init__(self) -> None:
        self.first_epoch: dict[str, int] = {}
        self.active_epochs: dict[str, int] = {}

    def observe(self, sim: Any, work: Any) -> None:
        engine = getattr(sim.proto_ctx, "protocol_engine", None)
        if engine is None:
            return
        for protocol_id in engine.get_active_protocols():
            self.first_epoch.setdefault(protocol_id, int(work.epoch))
            self.active_epochs[protocol_id] = (
                self.active_epochs.get(protocol_id, 0) + 1
            )


def introduction_witness(sim: Any, introduction: str) -> dict[str, Any]:
    """What the engine actually introduced, read back from the run."""
    engine = sim.engine
    role_by_id = {int(a.agent_id): str(a.role) for a in engine.agents}
    declared = [int(a) for a in getattr(engine, "explicit_seed_agent_ids", ())]
    reportable = sorted(
        int(a) for a in getattr(engine, "preboarding_reportable_ids", ())
    )
    return {
        "introduction": introduction,
        "initiation_manifest": getattr(engine, "initiation_manifest", None),
        "declared_seed_agent_ids": declared,
        "declared_seed_roles": [role_by_id.get(a) for a in declared],
        # The embarkation report counter. The VSP 4.1.1.2 reportable clause
        # is crew-only, so this never carries the five passengers.
        "preboarding_reportable": {
            role: sum(1 for a in reportable if role_by_id.get(a) == role)
            for role in ROLES
        },
        "complement": {
            role: sum(1 for r in role_by_id.values() if r == role)
            for role in ROLES
        },
    }


def run_cell(
    spec: dict[str, Any], manifest: dict[str, Any], tier: str,
    line_list_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run one voyage; return (summary payload, line-list document)."""
    introduction = compose_introduction(spec, manifest, tier)
    complement, intended = compose_complement(spec, manifest, tier)
    arm = compose_arm(spec, manifest, tier)
    platform = manifest["tiers"][tier]["platform"]
    spec["run"]["sentinel_line_list"] = os.path.relpath(
        line_list_path, _REPO_ROOT,
    )
    num_agents = int(spec["config_overrides"]["ship_graph"]["num_agents"])
    watch = ProtocolWatch()
    with materialized_picard_spec(spec, _REPO_ROOT) as picard_spec:
        sim = ShipSimulation(picard_spec, display=False)
        sim.initialize()
        realized = realized_complement(sim)
        if realized != intended:
            raise SystemExit(
                f"{tier}: initialized complement {realized} is not the "
                f"declared {intended} ({complement})",
            )
        prevalent_ids = initially_infected_agent_ids(sim)
        state = effective_state(sim, platform)
        state_mismatches = check_expected_state(manifest, tier, state)
        if state_mismatches:
            raise SystemExit(
                f"{tier}: effective state is not the tier's declared "
                f"state: {state_mismatches}",
            )
        declared_arm = arm_witness(manifest, arm, sim.cfg, state)
        if declared_arm["mismatches"]:
            raise SystemExit(
                f"{tier}: arm {arm} did not resolve as declared: "
                f"{declared_arm['mismatches']}",
            )
        sim.epoch_observer = watch.observe
        started = time.perf_counter()
        result = sim.run()
        wall_clock_s = time.perf_counter() - started
    line_list = validated_json_load(_REPO_ROOT, line_list_path)
    line_list_path.unlink()

    payload: dict[str, Any] = {}
    _attach_voyage_blocks(
        payload, spec, result, num_agents,
        natural_history_clock=manifest.get("natural_history_clock"),
    )
    clock = sim.engine.clock
    n_days = max(1, math.ceil(clock.days_elapsed(int(result.num_epochs))))
    witness = introduction_witness(sim, introduction)
    n_keys, mismatches = block_mismatches(
        manifest["tiers"][tier]["config_overrides"], sim.cfg,
    )
    payload.update({
        "campaign": manifest["campaign"],
        "tier": tier,
        "seed": int(spec["run"]["random_seed"]),
        "platform": platform,
        "num_epochs": int(result.num_epochs),
        "n_days": int(n_days),
        "engine_git_sha": engine_git_sha(),
        "python_hash_seed": os.environ.get("PYTHONHASHSEED"),
        "wall_clock_s": round(wall_clock_s, 1),
        "introduction": witness,
        "initially_infected_agent_ids": sorted(prevalent_ids),
        "complement_block": complement,
        "intended_complement": intended,
        "effective_state": state,
        "declared_arm": declared_arm,
        "generated_config_overrides": spec["config_overrides"],
        "frozen_block_witness": {
            "pinned_leaves": n_keys, "mismatches": mismatches,
        },
        "line_list_cases": len(line_list["clinical_cases"]),
        "onsets_by_day": onset_curves(
            line_list["clinical_cases"],
            set(witness["declared_seed_agent_ids"]), clock, n_days,
            prevalent_ids,
        ),
        "reporting_by_day": reporting_curves(
            payload["timeseries"], clock, n_days,
        ),
        "protocols": {
            "first_active_epoch": dict(sorted(watch.first_epoch.items())),
            "active_epochs": dict(sorted(watch.active_epochs.items())),
        },
    })
    return payload, line_list


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    add_manifest_args(parser, required=True)
    parser.add_argument("--pathogen-id", default="norwalk_gi")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--epochs-override", type=int, default=None,
        help="local wiring check only: shorten the voyage",
    )
    return parser.parse_args(argv)


def pin_hash_seed() -> None:
    """Re-execute under ``PYTHONHASHSEED=1`` unless already running so."""
    if os.environ.get("PYTHONHASHSEED") == HASH_SEED:
        return
    env = {**os.environ, "PYTHONHASHSEED": HASH_SEED}
    os.execve(sys.executable, [sys.executable, *sys.argv], env)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if argv is None:
        pin_hash_seed()
    manifest = validated_json_load(_REPO_ROOT, args.manifest)
    clock = manifest.get("natural_history_clock")
    runs = list(generate_tier_runs(
        manifest, args.tier,
        epochs_override=args.epochs_override,
        natural_history_clock=str(clock) if clock is not None else None,
    ))
    runs = index_run(runs, args.index, args.tier)
    out_dir = Path(prepare_output_directory(
        str(args.out), allowed_roots=(str(_REPO_ROOT),),
    ))
    for run_id, spec in runs:
        scratch = Path(resolve_child_path(
            str(out_dir), f"{args.tier}.{run_id}.line_list.json",
        ))
        payload, line_list = run_cell(spec, manifest, args.tier, scratch)
        payload["run_id"] = run_id
        zip_path = write_run_zip(
            out_dir, args.tier, run_id, payload,
            {"sentinel_line_list.json": json.dumps(line_list)},
        )
        print(
            f"seed {payload['seed']}: line_list={payload['line_list_cases']} "
            f"declared_seeds={len(payload['introduction']['declared_seed_agent_ids'])} "
            f"arm={payload['declared_arm']['arm']} "
            f"rhythm_layer={payload['effective_state']['rhythm_layer_active']} "
            f"block_mismatches={len(payload['frozen_block_witness']['mismatches'])} "
            f"wall={payload['wall_clock_s']}s -> {zip_path}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
