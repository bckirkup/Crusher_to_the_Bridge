"""Local preflight smoke for covid_partner_rate_assay_v1 (campaign-preflight 1).

Proves the three things the frozen design assumes, before any Batch cell runs:

1. Spec-lands: every arm's ``transmission_overrides`` reaches the run spec —
   the rate arms carry the scaled ``activity_contacts`` block, the witness arm
   carries ``droplet_field_split.mode = off``, and the cell enumeration is the
   declared 180 cells in arm-major order.
2. Runtime binding (spec-lands-but-inert is a bug, not physics): truncated
   declared-replay runs at multiplier 1.00 vs 0.25 record the partner draws the
   proximity ring makes through ``_activity_contact_draw``; the ring-path draw
   means must scale ~4x, and ``sim.tx_core.activity_contacts`` must read back
   the scaled table — the engine's parsed value, not the JSON.
3. Contract: ``cell_payload`` on a truncated run still carries the declared
   fields (observables, index geometry, arm attribution block).

Usage:
    python3 tools/covid_partner_rate_smoke.py \
        [--design picard_framework/runs/covid_partner_rate_assay_v1_design.json]
        [--seed 20200205] [--spec-only]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engines.transmission_core import TransmissionCore
from picard_framework.covid_boarding_screen import (
    QuarantineAttributionLedger,
    cell_payload,
    enumerate_cells,
    load_design,
    prepare_cell_run_spec,
)
from picard_framework.covid_theta_fit import run_fit_spec
from simulation_utils.paths import confine_to_base, validated_open

DESIGN_REL = os.path.join(
    "picard_framework", "runs", "covid_partner_rate_assay_v1_design.json",
)
SHIPPED_RATES = {
    "cabin": 0.25,
    "corridor": 0.25,
    "work_service": 2.9,
    "work_other": 0.5,
    "dining_table": 2.0,
    "dining_venue": 2.0,
    "leisure": 1.0,
    "other": 0.0,
}
RUN_EPOCHS = 48

# Arm ids exercised at runtime: the shipped table, the deep-cut arm whose
# 0.25x scaling the design's declared counterfactual rests on, and the witness.
RUNTIME_ARMS = ("R0_declared", "R1_rate_0p25", "R8_pool_witness")

REQUIRED_PAYLOAD_KEYS = (
    "observables",
    "onset_curve",
    "index_onset_day",
    "index_shedding_at_day0",
    "arm_id",
    "during_quarantine_by_route",
    "quarantine_witness",
)


def _check_enumeration(  # pragma: no cover - CLI-driven check
    design, declared_cells: int,
) -> dict[str, list[int]]:
    """The dry-run count: enumeration must match the declared 180 cells."""
    cells = enumerate_cells(design)
    assert len(cells) == declared_cells, (
        f"enumerate_cells = {len(cells)} but the design declares {declared_cells}"
    )
    by_arm: dict[str, list[int]] = defaultdict(list)
    for idx, cell in enumerate(cells):
        by_arm[cell.arm_id].append(idx)
    assert len(by_arm) == len(design.arms), "an arm produced no cells"
    return {arm: [min(idxs), max(idxs)] for arm, idxs in by_arm.items()}


def _check_spec_lands(  # pragma: no cover - CLI-driven check
    design, cell, repo_root: str,
) -> None:
    """The arm's overrides must appear in the run spec the engine builds."""
    raw = prepare_cell_run_spec(design, cell, num_epochs=24, repo_root=repo_root)
    tx = raw.get("config_overrides", {}).get("transmission", {})
    overrides = design.arm_overrides(cell.arm_id).get(
        "transmission_overrides", {},
    )
    declared_rates = overrides.get("activity_contacts", {}).get(
        "rates_per_hour",
    )
    if declared_rates is None:
        assert "activity_contacts" not in tx, (
            f"{cell.arm_id}: unexpected activity_contacts override landed"
        )
    else:
        got = tx.get("activity_contacts", {}).get("rates_per_hour", {})
        assert got == declared_rates, (
            f"{cell.arm_id}: spec rates {got} != declared {declared_rates}"
        )
    declared_split = overrides.get("droplet_field_split")
    if declared_split is not None:
        assert tx.get("droplet_field_split") == declared_split, (
            f"{cell.arm_id}: droplet_field_split override did not land"
        )


def _install_ring_recorder() -> dict[str, list]:  # pragma: no cover
    """Tag partner draws made on the ring path (``_proximity_shedder_ids``).

    ``_proximity_shedder_ids`` calls ``_activity_contact_draw`` synchronously,
    so a depth counter on the instance tags ring-path draws without touching
    the engine's logic — the draw still happens once, on the same RNG call.
    """
    records: dict[str, list] = {
        "ring_draws": [],  # (activity, role, value) drawn inside the ring path
        "ring_calls": 0,
    }
    original_draw = TransmissionCore._activity_contact_draw
    original_ring = TransmissionCore._proximity_shedder_ids

    def drawing(core, target, unit_name, zone_name, hallway, epoch):
        value = original_draw(core, target, unit_name, zone_name, hallway, epoch)
        if getattr(core, "_ring_depth", 0) > 0:
            activity = core._contact_activity(
                target, unit_name, zone_name, hallway, epoch,
            )
            records["ring_draws"].append((activity, target.role, value))
        return value

    def ringing(core, target, shedders, n_occupants, unit_name, zone_name, epoch):
        core._ring_depth = getattr(core, "_ring_depth", 0) + 1
        try:
            records["ring_calls"] += 1
            return original_ring(
                core, target, shedders, n_occupants, unit_name, zone_name, epoch,
            )
        finally:
            core._ring_depth -= 1

    TransmissionCore._activity_contact_draw = drawing
    TransmissionCore._proximity_shedder_ids = ringing
    return records


def _engine_rates(  # pragma: no cover - CLI-driven check
    tx_core,
) -> dict[str, dict[str, float]]:
    """The parsed per-role table the engine actually used."""
    return {
        activity: dict(rates)
        for activity, rates in (tx_core.activity_contacts or {}).items()
    }


def _run_cell(  # pragma: no cover - runs a truncated sim, exercised by hand
    design, cell, repo_root: str,
) -> dict[str, Any]:
    """Run a truncated cell with the ring recorder and read back the engine."""
    records = _install_ring_recorder()
    raw = prepare_cell_run_spec(
        design, cell, num_epochs=RUN_EPOCHS, repo_root=repo_root,
    )
    ledger = QuarantineAttributionLedger()
    sim = run_fit_spec(raw, repo_root=repo_root, epoch_observer=ledger.observe)
    payload = cell_payload(design, cell, sim, ledger, raw)
    missing = [k for k in REQUIRED_PAYLOAD_KEYS if k not in payload]
    assert not missing, f"{cell.arm_id}: payload missing {missing}"
    assert abs(payload["index_onset_day"] + 1.0) < 1e-9
    assert payload["index_shedding_at_day0"] is True
    grouped: dict[str, list[int]] = defaultdict(list)
    for activity, _role, value in records["ring_draws"]:
        grouped[activity].append(value)
    return {
        "ring_calls": records["ring_calls"],
        "ring_draws": grouped,
        "engine_rates": _engine_rates(sim.tx_core),
        "engine_droplet_split_mode": sim.tx_core.droplet_field_split.mode,
        "recorded_onsets": payload["observables"]["recorded_onsets"],
    }


def _check_binding(  # pragma: no cover - CLI-driven check
    runs: dict[str, Any], report: dict[str, Any],
) -> None:
    """The multiplier must move the engine table and the ring's draws."""
    witness = runs["R8_pool_witness"]
    assert witness["engine_droplet_split_mode"] == "off"
    assert witness["ring_calls"] == 0 and not witness["ring_draws"], (
        "mode off must draw no proximity partners (the bit-identical baseline)"
    )
    for arm_id, mult in (("R0_declared", 1.0), ("R1_rate_0p25", 0.25)):
        engine = runs[arm_id]["engine_rates"]
        for activity, shipped in SHIPPED_RATES.items():
            for role in ("passenger", "crew"):
                expected = shipped * mult
                actual = engine.get(activity, {}).get(role)
                assert actual is not None and abs(actual - expected) < 1e-9, (
                    f"{arm_id} engine rate {activity}/{role}: "
                    f"{actual} != {expected}"
                )
    ratios: dict[str, float] = {}
    base = runs["R0_declared"]["ring_draws"]
    cut = runs["R1_rate_0p25"]["ring_draws"]
    pooled_base = [v for values in base.values() for v in values]
    pooled_cut = [v for values in cut.values() for v in values]
    assert pooled_base and pooled_cut, "the ring drew no partners"
    for activity in set(base) & set(cut):
        mean_base = sum(base[activity]) / len(base[activity])
        mean_cut = sum(cut[activity]) / len(cut[activity])
        if mean_base > 0 and len(base[activity]) >= 20:
            ratios[activity] = mean_cut / mean_base
    pooled_ratio = (sum(pooled_cut) / len(pooled_cut)) / (
        sum(pooled_base) / len(pooled_base)
    )
    report["ring_draw_mean_ratio"] = {
        "pooled": pooled_ratio,
        "expected": 0.25,
        "by_activity": ratios,
        "draws": {"base": len(pooled_base), "cut": len(pooled_cut)},
    }
    # Poisson means scale exactly with the multiplier, so the pooled ring-draw
    # ratio centres on 0.25; the band admits the activity-mix drift between
    # two diverging 48-epoch trajectories while still catching an inert axis
    # (ratio ~1.0) or a wrong-direction one (~4.0).
    assert 0.15 <= pooled_ratio <= 0.45, (
        f"ring draw mean ratio {pooled_ratio:.2f} — the multiplier does "
        "not bind the proximity ring (spec-lands but inert)"
    )


def main() -> None:  # pragma: no cover - CLI driver, exercised by hand
    parser = argparse.ArgumentParser()
    parser.add_argument("--design", default=DESIGN_REL)
    parser.add_argument("--seed", type=int, default=20200205)
    parser.add_argument(
        "--spec-only",
        action="store_true",
        help="enumeration + spec-lands checks only, no engine runs",
    )
    args = parser.parse_args()

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    design_path = confine_to_base(repo_root, args.design)
    design = load_design(design_path)
    with validated_open(
        design_path, "r", allowed_roots=(repo_root,), encoding="utf-8",
    ) as handle:
        declared_cells = int(json.load(handle)["cells"])

    report: dict[str, Any] = {"design_id": design.design_id}
    report["cell_blocks"] = _check_enumeration(design, declared_cells)
    print(f"enumeration: {declared_cells} cells, blocks {report['cell_blocks']}")

    seen: set[str] = set()
    for cell in enumerate_cells(design):
        if cell.arm_id not in seen:
            seen.add(cell.arm_id)
            _check_spec_lands(design, cell, repo_root)
    print(f"spec-lands: overrides reach the run spec on all {len(seen)} arms")

    if not args.spec_only:
        runs: dict[str, Any] = {}
        for arm_id in RUNTIME_ARMS:
            cell = next(
                c for c in enumerate_cells(design)
                if c.arm_id == arm_id and c.seed == args.seed
            )
            runs[arm_id] = _run_cell(design, cell, repo_root)
            print(
                f"{arm_id}: ring_calls={runs[arm_id]['ring_calls']} "
                f"mode={runs[arm_id]['engine_droplet_split_mode']} "
                f"recorded={runs[arm_id]['recorded_onsets']}",
            )
        report["runtime"] = {
            arm: {k: v for k, v in r.items() if k != "ring_draws"}
            for arm, r in runs.items()
        }
        _check_binding(runs, report)
        print(f"ring binding: {report['ring_draw_mean_ratio']}")

    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
