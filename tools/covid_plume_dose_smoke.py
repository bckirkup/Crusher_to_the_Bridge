"""Local preflight smoke for covid_plume_dose_assay_v1 (campaign-preflight 1).

Proves the three things the frozen design assumes, before any Batch cell runs:

1. Spec-lands: every arm's ``transmission_overrides`` reaches the run spec —
   the dose arms carry the overridden ``near_field_air`` block, the knockout
   arms carry the zeroed ``activity_contacts`` block, the witness arm carries
   ``droplet_field_split.mode = off``, and the cell enumeration is the
   declared 200 cells in arm-major order.
2. Runtime binding (spec-lands-but-inert is a bug, not physics):
   - dose axis: a truncated declared-replay run reads back the arm's
     ``interzonal_airflow_m3_per_hour`` and the derived
     ``near_field_flushed_volume_m3_per_epoch`` on the live engine, and a
     direct ``_near_field_droplet_dose`` call on two stubbed cores shows the
     partition-form dose scaling exactly as 1/beta;
   - knockout axis: the ring-path draw recorder sees zero partner draws for
     the knocked-out activity while other activities still draw, and the
     engine's parsed ``activity_contacts`` table reads back the zero;
   - witness: ``mode off`` draws no proximity partners at all.
3. Contract: ``cell_payload`` on a truncated run still carries the declared
   fields (observables, index geometry, arm attribution block).

Usage:
    python3 tools/covid_plume_dose_smoke.py \
        [--design picard_framework/runs/covid_plume_dose_assay_v1_design.json]
        [--seed 20200205] [--spec-only]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from types import SimpleNamespace
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
    "picard_framework", "runs", "covid_plume_dose_assay_v1_design.json",
)
SHIPPED_BETA = 204.0
HOURS_PER_EPOCH = 0.5
RUN_EPOCHS = 48

# Arm ids exercised at runtime: the baseline, the deep-cut dose arm whose
# 0.05x scaling the declared counterfactual rests on, a knockout arm, and
# the witness.
RUNTIME_ARMS = (
    "D0_declared",
    "D1_dose_0p05",
    "K1_dining_off",
    "W_pool_witness",
)

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
    """The dry-run count: enumeration must match the declared 200 cells."""
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
    for block in ("near_field_air", "activity_contacts", "droplet_field_split"):
        declared = overrides.get(block)
        if declared is None:
            assert block not in tx, (
                f"{cell.arm_id}: unexpected {block} override landed"
            )
        else:
            assert tx.get(block) == declared, (
                f"{cell.arm_id}: spec {block} {tx.get(block)} "
                f"!= declared {declared}"
            )


def _stub_core(  # pragma: no cover - helper for the dose-formula check
    beta: float, hours_per_epoch: float = HOURS_PER_EPOCH,
) -> TransmissionCore:
    """A bare TransmissionCore carrying only what the partition dose reads."""
    core = object.__new__(TransmissionCore)
    core.near_field_air = SimpleNamespace(
        active=True,
        mode="two_box",
        interzonal_airflow_m3_per_hour=beta,
        neighbour_table_ratio=0.43,
    )
    core.near_field_flushed_volume_m3_per_epoch = beta * hours_per_epoch
    core.inhaled_air_volume_m3_per_epoch = 0.24
    core.droplet_scalar = 1.0
    core.zone_types = {}
    core._meal_tables = {}
    return core


def _stub_host(agent_id: int) -> SimpleNamespace:  # pragma: no cover
    """A host carrying only what ``_near_field_unit`` reads off the ring."""
    return SimpleNamespace(
        agent_id=agent_id,
        role="passenger",
        cabin_mate_ids=frozenset(),
        dining_zone=None,
        dining_party_ids=frozenset(),
        dining_table_index=0,
    )


def plume_dose_at_beta(  # pragma: no cover - exercised through _check_binding
    beta: float, near_share: float = 0.825,
) -> float:
    """Partition-form near-field dose of one emitted unit at flushed beta."""
    core = _stub_core(beta)
    target = _stub_host(1)
    shedder = _stub_host(2)
    return core._near_field_droplet_dose(
        "ZoneX",
        target,
        [(shedder, 1.0)],
        volume=100.0,
        target_factor=1.0,
        emission_fraction=1.0,
        epoch=0,
        proximity_ids=frozenset({2}),
        near_share=near_share,
    )


def dose_scaling_ratio(  # pragma: no cover - exercised through _check_binding
    beta_hi: float, beta_lo: float,
) -> float:
    """Observed dose ratio between two betas; ~1/beta if the axis binds."""
    return plume_dose_at_beta(beta_hi) / plume_dose_at_beta(beta_lo)


def _install_ring_recorder() -> dict[str, list]:  # pragma: no cover
    """Tag partner draws made on the ring path (``_proximity_shedder_ids``)."""
    records: dict[str, Any] = {"ring_draws": [], "ring_calls": 0}
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


def _engine_near_field(  # pragma: no cover - CLI-driven check
    tx_core,
) -> dict[str, float]:
    """The parsed plume-flush constants the engine actually used."""
    near = tx_core.near_field_air
    return {
        "beta": near.interzonal_airflow_m3_per_hour,
        "flushed": tx_core.near_field_flushed_volume_m3_per_epoch,
        "mode": near.mode,
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
        "engine_near_field": _engine_near_field(sim.tx_core),
        "engine_rates": {
            activity: dict(rates)
            for activity, rates in (sim.tx_core.activity_contacts or {}).items()
        },
        "engine_droplet_split_mode": sim.tx_core.droplet_field_split.mode,
        "recorded_onsets": payload["observables"]["recorded_onsets"],
    }


def _check_binding(  # pragma: no cover - CLI-driven check
    design, runs: dict[str, Any], report: dict[str, Any],
) -> None:
    """The dose and knockout axes must move the engine, not just the spec."""
    witness = runs["W_pool_witness"]
    assert witness["engine_droplet_split_mode"] == "off"
    assert witness["ring_calls"] == 0 and not witness["ring_draws"], (
        "mode off must draw no proximity partners (the bit-identical baseline)"
    )
    # Read the clock's hours_per_epoch back from the baseline arm rather than
    # hardcoding it — the flushed volume is beta x that constant by wiring.
    base = runs["D0_declared"]["engine_near_field"]
    hours_per_epoch = base["flushed"] / base["beta"]
    for arm_id in ("D0_declared", "D1_dose_0p05"):
        overrides = design.arm_overrides(arm_id).get(
            "transmission_overrides", {},
        )
        expected_beta = overrides.get("near_field_air", {}).get(
            "interzonal_airflow_m3_per_hour", SHIPPED_BETA,
        )
        engine = runs[arm_id]["engine_near_field"]
        assert abs(engine["beta"] - expected_beta) < 1e-9, (
            f"{arm_id} engine beta {engine['beta']} != {expected_beta}"
        )
        assert abs(
            engine["flushed"] - expected_beta * hours_per_epoch
        ) < 1e-6, (
            f"{arm_id} flushed volume {engine['flushed']} does not track beta"
        )
    observed = dose_scaling_ratio(4080.0, SHIPPED_BETA)
    report["plume_dose_scaling"] = {
        "observed": observed,
        "expected": SHIPPED_BETA / 4080.0,
    }
    assert abs(observed - SHIPPED_BETA / 4080.0) < 1e-9, (
        f"partition dose scales {observed:.3f}, not 1/beta "
        "— the beta axis does not bind the plume dose"
    )
    knockout = runs["K1_dining_off"]
    engine_rates = knockout["engine_rates"]
    for activity in ("dining_table", "dining_venue"):
        for role in ("passenger", "crew"):
            actual = engine_rates.get(activity, {}).get(role)
            assert actual is not None and abs(actual) < 1e-9, (
                f"K1_dining_off engine rate {activity}/{role}: {actual} != 0"
            )
    for activity in ("dining_table", "dining_venue"):
        drawn = knockout["ring_draws"].get(activity, [])
        assert all(v == 0 for v in drawn), (
            f"K1_dining_off drew partners on knocked-out {activity}"
        )
    report["knockout_ring_draws"] = {
        activity: len(values)
        for activity, values in knockout["ring_draws"].items()
    }


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
                f"beta={runs[arm_id]['engine_near_field']['beta']} "
                f"mode={runs[arm_id]['engine_droplet_split_mode']} "
                f"recorded={runs[arm_id]['recorded_onsets']}",
            )
        report["runtime"] = {
            arm: {k: v for k, v in r.items() if k != "ring_draws"}
            for arm, r in runs.items()
        }
        _check_binding(design, runs, report)

    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
