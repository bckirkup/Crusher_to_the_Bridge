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

Shared enumeration / spec-lands / ring-recorder / truncated-run machinery
lives in ``tools/covid_assay_smoke.py``; this tool keeps only the
partner-rate axis checks and its design constants.

Usage:
    python3 tools/covid_partner_rate_smoke.py \
        [--design picard_framework/runs/covid_partner_rate_assay_v1_design.json]
        [--seed 20200205] [--spec-only]
"""

from __future__ import annotations

import os
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.covid_assay_smoke import (
    check_enumeration,
    check_spec_lands,
    drive,
    engine_rates,
    run_cell,
)

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


def _check_spec_lands(  # pragma: no cover - CLI-driven check
    design, cell, repo_root: str,
) -> None:
    """The arm's overrides must appear in the run spec the engine builds."""
    check_spec_lands(
        design, cell, repo_root,
        blocks=("activity_contacts", "droplet_field_split"),
    )


def _check_enumeration(  # pragma: no cover - kept as the tool's public check
    design, declared_cells: int,
) -> dict[str, list[int]]:
    """The dry-run count: enumeration must match the declared 180 cells."""
    return check_enumeration(design, declared_cells)


def _engine_rates(  # pragma: no cover - kept as the tool's public read-back
    tx_core,
) -> dict[str, dict[str, float]]:
    """The parsed per-role table the engine actually used."""
    return engine_rates(tx_core)


def _run_cell(  # pragma: no cover - runs a truncated sim, exercised by hand
    design, cell, repo_root: str,
) -> dict[str, Any]:
    """Run a truncated cell with the ring recorder and read back the engine."""
    return run_cell(design, cell, repo_root, RUN_EPOCHS)


def _check_binding(  # pragma: no cover - CLI-driven check
    _design, runs: dict[str, Any], report: dict[str, Any],
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
    drive(
        file_name=__file__,
        design_rel=DESIGN_REL,
        spec_check=_check_spec_lands,
        runtime_arms=RUNTIME_ARMS,
        cell_runner=_run_cell,
        binding_check=_check_binding,
        arm_line=lambda arm, r: (
            f"{arm}: ring_calls={r['ring_calls']} "
            f"mode={r['engine_droplet_split_mode']} "
            f"recorded={r['recorded_onsets']}"
        ),
        binding_line=lambda report: (
            f"ring binding: {report['ring_draw_mean_ratio']}"
        ),
    )


if __name__ == "__main__":
    main()
