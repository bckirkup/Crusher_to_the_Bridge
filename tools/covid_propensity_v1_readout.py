"""PROPENSITY-V1 readout: the clause canary at the Theta 1e9 anchor.

Pools the synced campaign cells (``aws s3 sync .../cells/ <dir>``) for
``covid_propensity_v1`` — one anchor point, 2 arms, 20 seeds — and
reports, per arm row:

* the propensity audit: ``delivery.participation_propensity`` echoes the
  arm's resolved mode and cv (``party`` on D0_declared, ``off`` on
  PROP_OFF — a missing or mismatched echo is a design defect, not a sim
  result), ``propensity_draw.units_drawn`` is > 0 on every D0 cell and 0
  on every PROP_OFF cell (the bit-identity witness), and the fixed
  echoes resolve (``presentation_draw_mode`` once_per_course,
  ``hand_reservoir_mode`` hygiene_cycle);
* the v11-lineage clause per arm, verbatim: among takeoff seeds
  (recorded_onsets >= 10), the q05-q95 interval of recorded_onsets
  contains 197 AND the takeoff-seed median before_share is within 0.10
  of 0.173 — scored only at >= 5 takeoff seeds, else "insufficient
  takeoff mass";
* the seed-paired delta distribution PROP_OFF -> D0_declared on
  recorded_onsets, before_share and infections_total — the mechanism's
  footprint at the anchor (the off arm is the pre-PROPENSITY tree under
  rhythm);
* report-immediately rows: a clause pass on either arm (the first
  DP-scale pass at anchor under this mechanism) and the shared
  truth/timing/fizzle flags.

Usage:
    python3 tools/covid_propensity_v1_readout.py \
        --cells campaign_results/covid_propensity_v1/cells \
        --design picard_framework/runs/covid_propensity_v1_design.json \
        --out telemetry_buffer/covid_propensity_v1_readout.json
"""

from __future__ import annotations

import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulation_utils.paths import repo_root  # noqa: E402
from tools.covid_screen_readout_common import (  # noqa: E402
    DP_RECORD_SEED_SPEC,
    audit_fixed_delivery_echoes,
    audit_index_geometry,
    audit_propensity_echo,
    clause_row_triggers,
    declared_propensity_block,
    design_readout_main,
    paired_rows_against_baseline,
    propensity_row_stats,
)

REPO_ROOT = repo_root()

BASELINE_ARM = "D0_declared"
OFF_ARM = "PROP_OFF"


def _declared(arm: dict) -> dict:
    """The arm's declared participation_propensity block (empty on D0)."""
    return declared_propensity_block(arm)


def audit_cell(payload: dict, declared: dict, theta: float) -> list[str]:
    """Return the audit violations for one cell payload."""
    failures: list[str] = []
    delivery = payload.get("delivery") or {}
    audit_propensity_echo(failures, payload, delivery, declared)
    audit_fixed_delivery_echoes(failures, delivery)
    audit_index_geometry(failures, payload, DP_RECORD_SEED_SPEC)
    if payload.get("design_id") != "covid_propensity_v1":
        failures.append(
            f"design_id {payload.get('design_id')!r} "
            "!= 'covid_propensity_v1'",
        )
    return failures


def _row_stats(payloads: list[dict]) -> dict:
    """Takeoff-conditional stats + clause + propensity echoes per arm."""
    return propensity_row_stats(payloads)


def _paired_rows(design: Any) -> Any:
    """Bind the D0 baseline for the PROP_OFF delta pairing.

    The delta direction is off minus declared: what removing the
    mechanism changes. Both arms' takeoff cells pair; a seed where
    either arm fizzled drops out (the fizzle margin itself is reported
    per row).
    """
    return paired_rows_against_baseline(OFF_ARM, BASELINE_ARM)


def _row_triggers(
    theta: float, arm_id: str, stats: dict,
) -> dict | None:
    """Report-immediately rows: a clause pass on either arm."""
    return clause_row_triggers(theta, arm_id, stats)


def main(argv: list[str] | None = None) -> int:
    return design_readout_main(
        argv,
        repo_root=REPO_ROOT,
        declared_fn=_declared,
        audit_cell=audit_cell,
        row_stats=_row_stats,
        report_key="triggered_rows",
        row_triggers=_row_triggers,
        paired_rows_of=_paired_rows,
    )


if __name__ == "__main__":
    raise SystemExit(main())
