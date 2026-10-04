"""CAREGIVER-ATTR-01 readout: the anchor-drift attribution canary.

Pools the synced campaign cells (``aws s3 sync .../cells/ <dir>``) for
``covid_caregiver_off_v1`` — one anchor point, 2 arms, 20 seeds — and
reports, per arm row:

* the caregiver audit: ``delivery.caregiver.mode`` echoes the arm's
  resolved mode (``on`` on D0_declared, ``off`` on CG_OFF — a missing
  or mismatched echo is a design defect, not a sim result), and the
  pooled route tallies carry the ``caregiver`` route dose on D0 and
  none on CG_OFF (the exercise witness, reported never gated);
* the propensity audit: ``delivery.participation_propensity.mode``
  echoes ``party`` on D0_declared and ``off`` on CG_OFF, and
  ``propensity_draw.units_drawn`` is > 0 on every D0 cell and 0 on
  every CG_OFF cell (the bit-identity witness), plus the fixed echoes
  (``presentation_draw_mode`` once_per_course, ``hand_reservoir_mode``
  hygiene_cycle);
* the v11-lineage clause per arm, verbatim: among takeoff seeds
  (recorded_onsets >= 10), the q05-q95 interval of recorded_onsets
  contains 197 AND the takeoff-seed median before_share is within 0.10
  of 0.173 — scored only at >= 5 takeoff seeds;
* the attribution deltas: seed-paired (CG_OFF - D0_declared) on
  recorded_onsets, before_share and infections_total inside the run —
  the combined caregiver+propensity footprint at the anchor. The
  cross-run pairings that complete the attribution (CG_OFF - PROP_OFF
  on the e0d43979 canary row, CG_OFF - v15 on the 6efec855 anchor row)
  are computed from those synced prefixes in the readout doc;
* report-immediately rows: a clause pass on either arm (the
  restoration verdict (a) — CAREGIVER-V1 is the mover) and the shared
  truth/timing/fizzle flags.

Usage:
    python3 tools/covid_caregiver_off_v1_readout.py \
        --cells campaign_results/covid_caregiver_off_v1/cells \
        --design picard_framework/runs/covid_caregiver_off_v1_design.json \
        --out telemetry_buffer/covid_caregiver_off_v1_readout.json
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
    propensity_row_stats,
    seed_paired_deltas,
)

REPO_ROOT = repo_root()

BASELINE_ARM = "D0_declared"
OFF_ARM = "CG_OFF"


def _declared(arm: dict) -> dict:
    """The arm's declared propensity block + resolved caregiver mode."""
    declared = declared_propensity_block(arm)
    caregiver = (
        (arm.get("overrides") or {}).get("transmission_overrides") or {}
    ).get("caregiver") or {}
    declared["caregiver_mode"] = str(caregiver.get("mode", "on"))
    return declared


def _audit_caregiver_echo(
    failures: list[str], delivery: dict, declared: dict,
) -> None:
    """delivery.caregiver.mode echoes the arm's resolved caregiver arm."""
    block = delivery.get("caregiver")
    if not isinstance(block, dict):
        failures.append(
            "delivery.caregiver missing — the arm key did not resolve "
            "(design defect)",
        )
        return
    want = declared["caregiver_mode"]
    if block.get("mode") != want:
        failures.append(
            f"caregiver.mode resolved {block.get('mode')!r}, "
            f"declared {want!r}",
        )


def audit_cell(payload: dict, declared: dict, theta: float) -> list[str]:
    """Return the audit violations for one cell payload."""
    failures: list[str] = []
    delivery = payload.get("delivery") or {}
    audit_propensity_echo(failures, payload, delivery, declared)
    _audit_caregiver_echo(failures, delivery, declared)
    audit_fixed_delivery_echoes(failures, delivery)
    audit_index_geometry(failures, payload, DP_RECORD_SEED_SPEC)
    if payload.get("design_id") != "covid_caregiver_off_v1":
        failures.append(
            f"design_id {payload.get('design_id')!r} "
            "!= 'covid_caregiver_off_v1'",
        )
    return failures


def _row_stats(payloads: list[dict]) -> dict:
    """Takeoff-conditional stats + clause + both mechanisms' echoes."""
    stats = propensity_row_stats(payloads)
    aboard = stats.get("aboard_window_by_route_pooled") or {}
    during = stats.get("during_quarantine_by_route_pooled") or {}
    stats["caregiver_route_pooled"] = {
        "aboard_window": aboard.get("caregiver", 0),
        "during_quarantine": during.get("caregiver", 0),
    }
    return stats


def _paired_off_vs_declared(
    theta: float, row: list[dict], base: list[dict],
) -> dict:
    """Seed-paired (CG_OFF - D0_declared) deltas on the scored legs.

    The delta direction is off minus declared: what removing the
    caregiver pathway (on the already-off propensity tree) changes
    against the shipped default. Both arms' takeoff cells pair; a seed
    where either arm fizzled drops out.
    """
    return {
        "theta": theta,
        "arm_id": OFF_ARM,
        "baseline": BASELINE_ARM,
        **seed_paired_deltas(row, base),
    }


def _paired_rows(design: Any) -> Any:
    """Bind the D0 baseline for the CG_OFF delta pairing."""

    def _pair(rows: dict[tuple, list[dict]]) -> dict:
        out: dict[str, Any] = {}
        for (theta, arm_id), row in sorted(rows.items()):
            if arm_id != OFF_ARM:
                continue
            base = rows.get((theta, BASELINE_ARM)) or []
            out[f"theta={theta:.4g}|arm={arm_id}"] = (
                _paired_off_vs_declared(theta, row, base)
            )
        return out

    return _pair


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
