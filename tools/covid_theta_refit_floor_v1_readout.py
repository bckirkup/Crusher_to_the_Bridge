#!/usr/bin/env python3
"""THETA-REFIT-01 floor falsifier readout: the Theta 1e6 probe row.

Pools the synced campaign cells (``aws s3 sync .../cells/ <dir>``) for
``covid_theta_refit_floor_v1`` — one row at Theta 1e6 (a decade below the
refit lattice floor), one arm, 20 seeds — and reports, per row:

* the audit: ``delivery.caregiver.mode`` resolves ``on`` and
  ``delivery.participation_propensity.mode`` resolves ``party`` on every
  cell (the shipped defaults — a missing or mismatched echo is a design
  defect, not a sim result), ``propensity_draw.units_drawn`` > 0, plus
  the fixed echoes (``presentation_draw_mode`` once_per_course,
  ``hand_reservoir_mode`` hygiene_cycle) and the index-geometry
  invariant;
* the v11-lineage clause on the row, verbatim: among takeoff seeds
  (recorded_onsets >= 10), the q05-q95 interval of recorded_onsets
  contains 197 AND the takeoff-seed median before_share is within 0.10
  of 0.173 — scored only at >= 5 takeoff seeds;
* the caregiver witness: the pooled ``caregiver`` route tally (aboard
  window / during quarantine) — the mechanism-set floor's signature,
  expected ~100-140 aboard-window by extrapolation of the 141-at-1e7
  floor;
* report-immediately rows: a clause pass (FLOOR-CROSSED candidates) and
  the shared truth/timing/fizzle flags.

The floor verdict (FLOOR-CERTIFIED / FLOOR-CROSSED / SUB-IGNITION) and
the seed-paired cross-run reads (vs the refit 1e7 boundary row, the v15
anchor row, and both CAREGIVER-ATTR-01 arms) are computed in the readout
doc — this tool emits the row-resolved clause map they are scored from.

Usage:
    python3 tools/covid_theta_refit_floor_v1_readout.py \\
        --cells campaign_results/covid_theta_refit_floor_v1/cells \\
        --design picard_framework/runs/covid_theta_refit_floor_v1_design.json \\
        --out telemetry_buffer/covid_theta_refit_floor_v1_readout.json
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulation_utils.paths import repo_root  # noqa: E402
from tools.covid_screen_readout_common import (  # noqa: E402
    DP_RECORD_SEED_SPEC,
    audit_caregiver_echo,
    audit_fixed_delivery_echoes,
    audit_index_geometry,
    audit_propensity_echo,
    caregiver_route_witness,
    clause_row_triggers,
    declared_propensity_caregiver_block,
    design_readout_main,
    propensity_row_stats,
)

REPO_ROOT = repo_root()

BASELINE_ARM = "D0_declared"


def audit_cell(payload: dict, declared: dict, theta: float) -> list[str]:
    """Return the audit violations for one cell payload."""
    failures: list[str] = []
    delivery = payload.get("delivery") or {}
    audit_propensity_echo(failures, payload, delivery, declared)
    audit_caregiver_echo(failures, delivery, declared)
    audit_fixed_delivery_echoes(failures, delivery)
    audit_index_geometry(failures, payload, DP_RECORD_SEED_SPEC)
    cell = payload.get("cell") or {}
    if cell.get("arm_id") != BASELINE_ARM:
        failures.append(
            f"cell.arm_id {cell.get('arm_id')!r} != {BASELINE_ARM!r}",
        )
    if payload.get("design_id") != "covid_theta_refit_floor_v1":
        failures.append(
            f"design_id {payload.get('design_id')!r} "
            "!= 'covid_theta_refit_floor_v1'",
        )
    return failures


def _row_stats(payloads: list[dict]) -> dict:
    """Takeoff-conditional stats + clause + the caregiver dose witness."""
    stats = propensity_row_stats(payloads)
    stats["caregiver_route_pooled"] = caregiver_route_witness(stats)
    return stats


def _row_triggers(theta: float, arm_id: str, stats: dict) -> dict | None:
    """Report-immediately rows: a clause pass or timing/fizzle flag."""
    return clause_row_triggers(theta, arm_id, stats)


def main(argv: list[str] | None = None) -> int:
    spec = {
        "repo_root": REPO_ROOT,
        "declared_fn": declared_propensity_caregiver_block,
        "audit_cell": audit_cell,
        "row_stats": _row_stats,
        "report_key": "triggered_rows",
        "row_triggers": _row_triggers,
    }
    return design_readout_main(argv, **spec)


if __name__ == "__main__":
    raise SystemExit(main())
