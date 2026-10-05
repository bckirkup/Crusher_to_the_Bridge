#!/usr/bin/env python3
"""DP-BELIEF-01-D4 readout: the quarantine-phase suppression arm.

Pools the synced campaign cells (``aws s3 sync .../cells/ <dir>``) for
``covid_quar_suppression_v1`` — two clause thetas (1e6, 7.9e6) x two arms
x 20 seeds — and reports, per row:

* the audit: ``delivery.caregiver.mode`` resolves ``on`` and
  ``delivery.participation_propensity.mode`` resolves ``party`` on every
  cell, ``propensity_draw.units_drawn`` > 0, the fixed echoes
  (``presentation_draw_mode`` once_per_course, ``hand_reservoir_mode``
  hygiene_cycle), and the index-geometry invariant;
* the suppression witness: every cell's ``quarantine_witness`` must echo
  the arm's scheduled protocol — ``SOP-017`` with a non-empty
  ``exempt_classes`` on D0_declared, ``SOP-017-ALLHANDS`` with
  ``exempt_classes == []`` on SOP017_ALLHANDS — plus ``window_days``
  ``[16, 30]`` and ``activated`` true. A missing or mismatched witness
  means the ``scheduled_protocol_id`` swap never reached the engine: a
  design defect, not a sim result;
* the v11-lineage clause per row, verbatim: among takeoff seeds
  (recorded_onsets >= 10), the q05-q95 interval of recorded_onsets
  contains 197 AND the takeoff-seed median before_share is within 0.10
  of 0.173 — scored only at >= 5 takeoff seeds;
* the D4 answer fields per row: the ``infections_during_quarantine``
  band read against the record-informed window [150, 350] (median and
  band membership), the ``infections_before_quarantine`` band (the
  unmoved check), the pooled during-window role tally's crew share, and
  the confined-passenger during-window bound;
* the seed-paired deltas SOP017_ALLHANDS vs the in-design D0_declared
  row at the same theta — recorded_onsets, before_share,
  infections_total, plus the D4-specific during-quarantine mass, its
  crew tally, and before-quarantine mass;
* the replication check: each in-design D0_declared cell must bit-match
  its measured shipped-default counterpart (floor 1e6 cells / bracket
  7.9e6 cells) modulo ``cell.index`` and ``design_id`` bookkeeping; a
  divergence is an image/drift defect, reported before any verdict.

The CONFINEMENT-CHANNEL / OPEN-PHASE / PARTIAL-SUPPRESSION / SUB-IGNITION
verdict is declared in the design's frozen grammar and stated in the
readout doc — this tool emits the row-resolved clause map, band reads,
deltas, witnesses, and the replication block it is scored from.

Usage:
    python3 tools/covid_quar_suppression_v1_readout.py \\
        --cells campaign_results/covid_quar_suppression_v1/cells \\
        --design picard_framework/runs/covid_quar_suppression_v1_design.json \\
        --out telemetry_buffer/covid_quar_suppression_v1_readout.json
"""

from __future__ import annotations

import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulation_utils.paths import repo_root  # noqa: E402
from tools.covid_cg_floor_v1_readout import replication_check  # noqa: E402
from tools.covid_screen_readout_common import (  # noqa: E402
    DP_RECORD_SEED_SPEC,
    TAKEOFF_MIN_ONSETS,
    audit_caregiver_echo,
    audit_fixed_delivery_echoes,
    audit_index_geometry,
    audit_propensity_echo,
    band_stats,
    clause_row_triggers,
    declared_propensity_caregiver_block,
    design_readout_main,
    propensity_row_stats,
    seed_paired_deltas,
)

REPO_ROOT = repo_root()

DESIGN_ID = "covid_quar_suppression_v1"
BASELINE_ARM = "D0_declared"
OFF_ARM = "SOP017_ALLHANDS"
DECLARED_PROTOCOL = "SOP-017"
OFF_PROTOCOL = "SOP-017-ALLHANDS"
WINDOW_DAYS = [16, 30]

# Record-informed during-quarantine band (days 16-30 acquisitions), from
# the believability map's F10/F11 derivation — frozen in the design's
# admissibility block before any cell ran.
RECORD_DURING_BAND = (150.0, 350.0)


def declared_suppression_block(arm: dict) -> dict:
    """Propensity/caregiver modes + the arm's expected protocol echo."""
    declared = declared_propensity_caregiver_block(arm)
    overrides = arm.get("overrides") or {}
    declared["protocol_id"] = str(
        overrides.get("scheduled_protocol_id") or DECLARED_PROTOCOL
    )
    declared["all_hands"] = declared["protocol_id"] == OFF_PROTOCOL
    return declared


def audit_quarantine_witness(
    failures: list[str], payload: dict, declared: dict,
) -> None:
    """quarantine_witness echoes the arm's scheduled-protocol swap."""
    witness = payload.get("quarantine_witness")
    if not isinstance(witness, dict):
        failures.append(
            "quarantine_witness missing — window tallies unverifiable "
            "(design defect)",
        )
        return
    want_protocol = declared["protocol_id"]
    got_protocol = witness.get("protocol_id")
    if got_protocol != want_protocol:
        failures.append(
            f"quarantine_witness.protocol_id {got_protocol!r} != "
            f"{want_protocol!r} (swap defect)",
        )
    if list(witness.get("window_days") or []) != WINDOW_DAYS:
        failures.append(
            f"quarantine_witness.window_days "
            f"{witness.get('window_days')!r} != {WINDOW_DAYS}",
        )
    if witness.get("activated") is not True:
        failures.append(
            "quarantine_witness.activated is not true — the confinement "
            "order never fired (design defect)",
        )
    exempt = witness.get("exempt_classes")
    if declared["all_hands"]:
        if exempt != []:
            failures.append(
                f"ALLHANDS exempt_classes {exempt!r} != [] "
                "(swap defect)",
            )
    elif not exempt:
        failures.append(
            "D0 exempt_classes empty — the declared SOP-017 crew "
            "exemption vanished (design defect)",
        )


def audit_cell(payload: dict, declared: dict, theta: float) -> list[str]:
    """Return the audit violations for one cell payload."""
    failures: list[str] = []
    delivery = payload.get("delivery") or {}
    audit_propensity_echo(failures, payload, delivery, declared)
    audit_caregiver_echo(failures, delivery, declared)
    audit_fixed_delivery_echoes(failures, delivery)
    audit_index_geometry(failures, payload, DP_RECORD_SEED_SPEC)
    audit_quarantine_witness(failures, payload, declared)
    cell = payload.get("cell") or {}
    if cell.get("arm_id") not in {BASELINE_ARM, OFF_ARM}:
        failures.append(
            f"cell.arm_id {cell.get('arm_id')!r} not in "
            f"{sorted({BASELINE_ARM, OFF_ARM})}",
        )
    if payload.get("design_id") != DESIGN_ID:
        failures.append(
            f"design_id {payload.get('design_id')!r} != {DESIGN_ID!r}",
        )
    return failures


def _crew_share(stats: dict) -> float | None:
    """Crew share of the pooled during-window role tally."""
    pooled = stats.get("during_quarantine_by_role_pooled") or {}
    crew = float(pooled.get("crew", 0))
    passenger = float(pooled.get("passenger", 0))
    if crew + passenger <= 0:
        return None
    return crew / (crew + passenger)


def _row_stats(payloads: list[dict]) -> dict:
    """Takeoff-conditional stats + clause + the D4 band witnesses."""
    stats = propensity_row_stats(payloads)
    during_med = (stats.get("during_quarantine") or {}).get("median")
    lo, hi = RECORD_DURING_BAND
    stats["during_band"] = list(RECORD_DURING_BAND)
    stats["during_median_in_band"] = (
        during_med is not None and lo <= during_med <= hi
    )
    stats["during_window_crew_share"] = _crew_share(stats)
    confined = [
        float(p["confined_passenger_infections_during_window"])
        for p in payloads
        if int(p["observables"]["recorded_onsets"]) >= TAKEOFF_MIN_ONSETS
        and p.get("confined_passenger_infections_during_window")
        is not None
    ]
    stats["confined_passenger_during_window"] = band_stats(confined)
    stats["row_extra"] = (
        f"during_med={during_med} "
        f"in_band={stats['during_median_in_band']} "
        f"crew_share={stats['during_window_crew_share']}"
    )
    return stats


def _row_triggers(theta: float, arm_id: str, stats: dict) -> dict | None:
    """Report-immediately rows: a clause flag and/or an in-band arm read."""
    trigger = clause_row_triggers(theta, arm_id, stats)
    med = (stats.get("during_quarantine") or {}).get("median")
    band_hit = (
        arm_id == OFF_ARM
        and stats.get("takeoff_n", 0) >= 5
        and med is not None
        and RECORD_DURING_BAND[0] <= med <= RECORD_DURING_BAND[1]
    )
    if not band_hit:
        return trigger
    if trigger is None:
        trigger = {"theta": theta, "arm_id": arm_id, "triggers": []}
    trigger["triggers"] = [*trigger["triggers"], "BAND-COLLAPSE"]
    trigger["during_median"] = med
    trigger["band"] = list(RECORD_DURING_BAND)
    return trigger


def _suppression_deltas(row: list[dict], base: list[dict]) -> dict:
    """seed_paired_deltas + the D4 during-window mass/role deltas."""
    out = seed_paired_deltas(row, base)
    base_by_seed = {int(p["cell"]["seed"]): p for p in base}
    deltas: dict[str, list[float]] = {
        "infections_during_quarantine": [],
        "during_crew": [],
        "infections_before_quarantine": [],
    }

    def _grab(payload: dict, key: str) -> float | None:
        if key == "during_crew":
            roles = payload.get("during_quarantine_by_role") or {}
            value = roles.get("crew")
        else:
            value = payload.get(key)
        return float(value) if value is not None else None

    for p in row:
        b = base_by_seed.get(int(p["cell"]["seed"]))
        if b is None:
            continue
        for key, vec in deltas.items():
            a_val, b_val = _grab(p, key), _grab(b, key)
            if a_val is not None and b_val is not None:
                vec.append(a_val - b_val)
    out.update(
        {f"delta_{k}": band_stats(v) for k, v in deltas.items()},
    )
    return out


def _pair_suppression(rows: dict[tuple, list[dict]]) -> dict:
    """SOP017_ALLHANDS rows seed-paired against same-theta D0_declared."""
    out: dict[str, Any] = {}
    for (theta, arm_id), row in sorted(rows.items()):
        if arm_id != OFF_ARM:
            continue
        base = rows.get((theta, BASELINE_ARM)) or []
        out[f"theta={theta:.4g}|arm={arm_id}"] = {
            "theta": theta,
            "arm_id": arm_id,
            "baseline": BASELINE_ARM,
            **_suppression_deltas(row, base),
        }
    return out


def _post_report(report: dict, cells_dir: str) -> None:
    """Append the D0 replication (drift witness) block to the report."""
    rep = replication_check(str(cells_dir))
    report["replication"] = rep
    for label, row in rep.items():
        if "skipped" in row:
            print(f"{label}: replication skipped — {row['skipped']}")
        else:
            print(
                f"{label}: {row['n_identical']}/{row['n_paired']} "
                f"bit-identical, max|delta| {row['max_abs_delta']:.4g}",
            )


def main(argv: list[str] | None = None) -> int:
    spec = {
        "repo_root": REPO_ROOT,
        "declared_fn": declared_suppression_block,
        "audit_cell": audit_cell,
        "row_stats": _row_stats,
        "report_key": "triggered_rows",
        "row_triggers": _row_triggers,
        "paired_rows_of": lambda _design: _pair_suppression,
        "post_report": _post_report,
    }
    return design_readout_main(argv, **spec)


if __name__ == "__main__":
    raise SystemExit(main())
