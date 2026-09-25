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

Shared enumeration / spec-lands / ring-recorder / truncated-run machinery
lives in ``tools/covid_assay_smoke.py``; this tool keeps only the
plume-dose and knockout axis checks and its design constants.

Usage:
    python3 tools/covid_plume_dose_smoke.py \
        [--design picard_framework/runs/covid_plume_dose_assay_v1_design.json]
        [--seed 20200205] [--spec-only]
"""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engines.transmission_core import TransmissionCore
from tools.covid_assay_smoke import (
    check_spec_lands,
    drive,
    engine_near_field,
    run_cell,
)

DESIGN_REL = os.path.join(
    "picard_framework", "runs", "covid_plume_dose_assay_v1_design.json",
)
SHIPPED_BETA = 204.0
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


def _check_spec_lands(  # pragma: no cover - CLI-driven check
    design, cell, repo_root: str,
) -> None:
    """All three override blocks must reach the run spec verbatim."""
    check_spec_lands(
        design,
        cell,
        repo_root,
        blocks=("near_field_air", "activity_contacts", "droplet_field_split"),
    )


def _stub_core(  # pragma: no cover - helper for the dose-formula check
    beta: float, hours_per_epoch: float = 0.5,
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
    return core._near_field_droplet_dose(
        "ZoneX",
        _stub_host(1),
        [(_stub_host(2), 1.0)],
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


def _run_cell(  # pragma: no cover - runs a truncated sim, exercised by hand
    design, cell, repo_root: str,
) -> dict[str, Any]:
    """Run a truncated cell, reading back the parsed near-field constants."""
    return run_cell(
        design,
        cell,
        repo_root,
        RUN_EPOCHS,
        extra_readback=lambda sim: {
            "engine_near_field": engine_near_field(sim.tx_core),
        },
    )


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
        drawn = knockout["ring_draws"].get(activity, [])
        assert all(v == 0 for v in drawn), (
            f"K1_dining_off drew partners on knocked-out {activity}"
        )
    report["knockout_ring_draws"] = {
        activity: len(values)
        for activity, values in knockout["ring_draws"].items()
    }


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
            f"beta={r['engine_near_field']['beta']} "
            f"mode={r['engine_droplet_split_mode']} "
            f"recorded={r['recorded_onsets']}"
        ),
    )


if __name__ == "__main__":
    main()
