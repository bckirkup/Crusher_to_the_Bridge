"""PROPENSITY-V1 readout: the clause canary at the Theta 1e9 anchor.

Pools the synced campaign cells (``aws s3 sync .../cells/ <dir>``) for
``covid_propensity_v1`` — one anchor point, 2 arms, 20 seeds — and
reports, per arm row:

* the propensity audit: ``delivery.participation_propensity`` echoes the
  arm's resolved mode (``party`` on D0_declared, ``off`` on PROP_OFF —
  a missing or mismatched echo is a design defect, not a sim result),
  ``propensity_draw.units_drawn`` is > 0 on every D0 cell and 0 on every
  PROP_OFF cell (the bit-identity witness), and the fixed echoes resolve
  (``presentation_draw_mode`` once_per_course, ``hand_reservoir_mode``
  hygiene_cycle);
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
    BEFORE_SHARE_TOL,
    MIN_TAKEOFF_SEEDS,
    T1_BEFORE_SHARE,
    T1_RECORDED,
    band_stats,
    design_readout_main,
    row_trigger_report,
    standard_row_stats,
)

REPO_ROOT = repo_root()

BASELINE_ARM = "D0_declared"
OFF_ARM = "PROP_OFF"
# An arm that declares no participation_propensity block resolves the
# shipped default (mode party since PROPENSITY-V1, PR #860).
SHIPPED_PROPENSITY_MODE = "party"
# Symmetric recorded-onsets band around the 197 clause anchor, reported
# beside the clause and never selected on (v15 stage-2 convention).
MASS_NEAR_TARGET = (T1_RECORDED / 2.0, T1_RECORDED * 2.0)
# The record's seed geometry is constant on this design (no seed_patch).
RECORD_SEED_SPEC = {
    "count": 1,
    "infection_age_days": 6.8,
    "onset_day": -1.0,
    "departure_day": 5.0,
    "role": "passenger",
}


def _declared(arm: dict) -> dict:
    """The arm's declared participation_propensity block (empty on D0)."""
    block = (arm.get("overrides") or {}).get("participation_propensity") or {}
    return {
        "propensity_mode": str(block.get("mode", SHIPPED_PROPENSITY_MODE)),
    }


def audit_cell(payload: dict, declared: dict, theta: float) -> list[str]:
    """Return the audit violations for one cell payload."""
    failures: list[str] = []
    delivery = payload.get("delivery") or {}
    _audit_propensity_echo(failures, payload, delivery, declared)
    _audit_fixed_echoes(failures, delivery)
    _audit_geometry(failures, payload)
    if payload.get("design_id") != "covid_propensity_v1":
        failures.append(
            f"design_id {payload.get('design_id')!r} "
            "!= 'covid_propensity_v1'",
        )
    return failures


def _audit_propensity_echo(
    failures: list[str], payload: dict, delivery: dict, declared: dict,
) -> None:
    prop = delivery.get("participation_propensity")
    if not isinstance(prop, dict):
        failures.append(
            "delivery.participation_propensity missing — the arm key did "
            "not resolve (design defect)",
        )
        return
    want = declared["propensity_mode"]
    if prop.get("mode") != want:
        failures.append(
            f"participation_propensity.mode resolved {prop.get('mode')!r}, "
            f"declared {want!r}",
        )
    units = int((payload.get("propensity_draw") or {}).get("units_drawn", -1))
    if want == "off":
        if units != 0:
            failures.append(
                f"off arm propensity_draw.units_drawn {units} != 0 "
                "(bit-identity witness broken)",
            )
    elif units <= 0:
        failures.append(
            f"armed cell propensity_draw.units_drawn {units} <= 0 "
            "(the draw never landed)",
        )


def _audit_fixed_echoes(failures: list[str], delivery: dict) -> None:
    for field, want in (
        ("presentation_draw_mode", "once_per_course"),
        ("hand_reservoir_mode", "hygiene_cycle"),
    ):
        if delivery.get(field) != want:
            failures.append(
                f"delivery.{field} {delivery.get(field)!r} != {want!r}",
            )


def _audit_geometry(failures: list[str], payload: dict) -> None:
    if float(payload.get("index_onset_day") or 0.0) != -1.0:
        failures.append(
            f"index_onset_day {payload.get('index_onset_day')!r} != -1.0",
        )
    if not payload.get("index_shedding_at_day0"):
        failures.append("index_shedding_at_day0 is false")
    ring = payload.get("seed_ring")
    if not isinstance(ring, dict):
        failures.append("missing seed_ring block")
        return
    spec = ring.get("seed_spec") or {}
    for key, want in RECORD_SEED_SPEC.items():
        got = spec.get(key)
        if got != want and not (
            isinstance(want, float)
            and isinstance(got, (int, float))
            and abs(float(got) - want) <= 1e-9
        ):
            failures.append(
                f"seed_spec.{key} is {spec.get(key)!r}, want {want!r}",
            )


def _clause(stats: dict[str, Any]) -> dict[str, Any]:
    """The verbatim v11 clause legs on one arm row's takeoff stats."""
    rec = stats["takeoff_recorded_onsets"]
    share = stats["takeoff_before_share"]
    scored = stats["takeoff_n"] >= MIN_TAKEOFF_SEEDS
    count_leg = bool(
        scored
        and rec["q05"] is not None
        and rec["q95"] is not None
        and rec["q05"] <= T1_RECORDED <= rec["q95"],
    )
    timing_leg = bool(
        scored
        and share["median"] is not None
        and abs(share["median"] - T1_BEFORE_SHARE) <= BEFORE_SHARE_TOL,
    )
    return {
        "scored": scored,
        "count_leg": count_leg,
        "timing_leg": timing_leg,
        "clause_ok": count_leg and timing_leg,
    }


def _mass_in_band(takeoff: list[dict], _stats: dict) -> dict[str, Any]:
    """Share of takeoff seeds landing within [98.5, 394] of the anchor."""
    recs = [float(p["observables"]["recorded_onsets"]) for p in takeoff]
    if not recs:
        return {"mass_near_t1": None}
    lo, hi = MASS_NEAR_TARGET
    return {"mass_near_t1": sum(lo <= r <= hi for r in recs) / len(recs)}


def _propensity_row_echo(takeoff: list[dict]) -> dict[str, Any]:
    """The draw telemetry pooled over the row's takeoff cells."""
    units = [
        float(p["propensity_draw"]["units_drawn"]) for p in takeoff
        if (p.get("propensity_draw") or {}).get("units_drawn") is not None
    ]
    medians = [
        float(p["propensity_draw"]["multiplier_median"]) for p in takeoff
        if (p.get("propensity_draw") or {}).get("multiplier_median")
        is not None
    ]
    q95s = [
        float(p["propensity_draw"]["multiplier_q95"]) for p in takeoff
        if (p.get("propensity_draw") or {}).get("multiplier_q95") is not None
    ]
    return {
        "propensity_units_drawn": band_stats(units),
        "propensity_multiplier_median": band_stats(medians),
        "propensity_multiplier_q95": band_stats(q95s),
    }


def _row_stats(payloads: list[dict]) -> dict:
    """Takeoff-conditional stats + clause + propensity echoes per arm."""
    stats = standard_row_stats(payloads, extra_fields=_mass_in_band)
    stats["clause"] = _clause(stats)
    takeoff = [
        p for p in payloads
        if int(p["observables"]["recorded_onsets"]) >= 10
    ]
    stats.update(_propensity_row_echo(takeoff))
    clause = stats["clause"]
    verdict = "unscored" if not clause["scored"] else (
        "PASS" if clause["clause_ok"] else "FAIL"
    )
    stats["row_extra"] = (
        f"clause {verdict} "
        f"units {_fmt(stats['propensity_units_drawn']['median'])}"
    )
    return stats


def _fmt(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.3g}"


def _before_share(payload: dict) -> float | None:
    rec = float(payload["observables"]["recorded_onsets"])
    if rec <= 0:
        return None
    return float(payload["observables"]["onsets_before_split_day"]) / rec


def _paired_off_vs_declared(
    theta: float, row: list[dict], base: list[dict],
) -> dict:
    """Seed-paired (PROP_OFF - D0_declared) deltas on the scored legs.

    The delta direction is off minus declared: what removing the
    mechanism changes. Both arms' takeoff cells pair; a seed where
    either arm fizzled drops out (the fizzle margin itself is reported
    per row).
    """
    base_by_seed = {
        int(p["cell"]["seed"]): p for p in base
        if int(p["observables"]["recorded_onsets"]) >= 10
    }
    deltas: dict[str, list[float]] = {
        "recorded_onsets": [],
        "before_share": [],
        "infections_total": [],
    }
    for p in row:
        seed = int(p["cell"]["seed"])
        b = base_by_seed.get(seed)
        if b is None:
            continue
        if int(p["observables"]["recorded_onsets"]) < 10:
            continue
        deltas["recorded_onsets"].append(
            float(p["observables"]["recorded_onsets"])
            - float(b["observables"]["recorded_onsets"])
        )
        arm_share = _before_share(p)
        base_share = _before_share(b)
        if arm_share is not None and base_share is not None:
            deltas["before_share"].append(arm_share - base_share)
        if p.get("infections_total") is not None and (
            b.get("infections_total") is not None
        ):
            deltas["infections_total"].append(
                float(p["infections_total"]) - float(b["infections_total"])
            )
    return {
        "theta": theta,
        "arm_id": OFF_ARM,
        "baseline": BASELINE_ARM,
        "n_paired": len(deltas["recorded_onsets"]),
        **{f"delta_{k}": band_stats(v) for k, v in deltas.items()},
    }


def _paired_rows(design: Any) -> Any:
    """Bind the D0 baseline for the PROP_OFF delta pairing."""

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
    clause = stats.get("clause") or {}
    kinds: list[str] = []
    if clause.get("clause_ok"):
        kinds.append("CLAUSE-PASS")
    for name, flag in (
        ("TRUTH-IN-BAND", stats["truth_leg_in_band"]),
        ("TIMING-IN-BAND", stats["timing_leg_in_band"]),
        ("FIZZLE-MAJORITY", stats["fizzle_majority"]),
    ):
        if flag:
            kinds.append(name)
    if not kinds:
        return None
    return row_trigger_report(
        theta, arm_id, stats, kinds,
        (
            "takeoff_recorded_onsets",
            "takeoff_before_share",
            "takeoff_infections_total",
            "propensity_units_drawn",
        ),
    )


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
