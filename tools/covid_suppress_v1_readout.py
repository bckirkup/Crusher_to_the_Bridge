"""SUPPRESS-V1 readout: scheduled-slot audit echoes + the both-legs test
+ the suppression-shape discriminators per (theta, arm).

Pools the synced campaign cells (``aws s3 sync .../cells/ <dir>``) for
``covid_suppress_v1`` and reports, per (theta, arm) row:

* the scheduled-protocol audit — ``quarantine_witness.protocol_id`` /
  ``window_days`` vs the arm's declared slot, the constant-geometry
  ``seed_ring`` check, REF_M0P56's channel echoes, and the presence of
  the unconditional during-window tally block,
* takeoff-seed medians and q05-q95 of recorded_onsets, infections_total
  and before_share (the two anchors: 197 / 0.173 at the RECORD's day-16
  boundary — arm-invariant — vs the H5 band [712, 960]),
* the shape discriminators — before/during/after stratum mass vs the
  arm's own window, during-window zone/role/route concentration, the
  onset_curve kink at the arm's own start day, crew-onset lag,
  witness.activated fraction and confined_at_activation — the
  truncation / ceiling / deferral grammar the task names,
* the paired_rows block: seed-paired deltas vs D0_declared on the
  scored observables plus the post-arm-start acquisition mass (the
  deferral read) — timing landings are only real when the deltas are
  nonzero,
* the report-immediately triggers: in-band truth/timing landings,
  fizzle-majority rows, during-window-dominant rows, and the
  truncation signature. SOP017AH_D12 and SOP017_D40 are non-scoring
  (diagnostic / witness) and never satisfy a clause.

CLI paths are confined under the repository root (sync cells to
``campaign_results/<design>/cells/``); an audit failure is reported per
cell. The audit+score CLI skeleton is shared with the other conditioned
readouts in tools/covid_screen_readout_common.py.
"""

from __future__ import annotations

import os
import sys
from collections import Counter
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from picard_framework.covid_boarding_screen import (  # noqa: E402
    enumerate_cells,
    load_design,
)
from simulation_utils.paths import repo_root  # noqa: E402
from tools.covid_screen_readout_common import (  # noqa: E402
    anchor_legs,
    band_stats,
    quantile,
    resolve_design_arg,
    run_readout,
    takeoff_split,
)

REPO_ROOT = repo_root()

# The shipped slot on every non-swapped arm: SOP-017 days 16-30.
SHIPPED_PROTOCOL_ID = "SOP-017"
SHIPPED_WINDOW = (16, 30)
# The record's seed geometry is constant on this design (no seed_patch).
RECORD_SEED_SPEC = {"count": 1, "onset_day": -1.0, "role": "passenger"}
# Diagnostic/witness arms report their reads but never satisfy a clause.
NON_SCORING_ARMS = frozenset({"SOP017AH_D12", "SOP017_D40"})
BASELINE_ARM = "D0_declared"
# The shape grammar: days either side of an arm's own start for the
# onset-curve kink, and the zone classes the record's confined phase
# concentrated in (cabin-sharer + working crew).
KINK_HALF_WINDOW = 3
CONCENTRATION_ZONE_CLASSES = ("cabin", "crew_mess")
CONCENTRATION_SHARE = 0.5


def _declared(arm: dict) -> dict:
    """The arm's declared scheduled slot + channel expectations."""
    ov = arm.get("overrides") or {}
    window = ov.get("scheduled_protocol_window") or {}
    om = (
        (ov.get("pathogen_overrides") or {})
        .get("sars_cov2_resp", {})
        .get("observation_model", {})
    )
    return {
        "protocol_id": ov.get("scheduled_protocol_id", SHIPPED_PROTOCOL_ID),
        "window": [
            int(window.get("start_day", SHIPPED_WINDOW[0])),
            (
                int(window["end_day"])
                if window.get("end_day") is not None
                else SHIPPED_WINDOW[1]
            ),
        ],
        "onset_recording": om.get("onset_recording"),
        "eligibility": om.get("syndrome_case_eligibility_by_severity"),
        "scoring": arm["arm_id"] not in NON_SCORING_ARMS,
    }


def _audit_seed_echoes(ring: dict) -> list[str]:
    """seed_spec echoes the record's seed on every arm (no seed_patch)."""
    failures: list[str] = []
    spec = ring.get("seed_spec") or {}
    for key, want in RECORD_SEED_SPEC.items():
        if spec.get(key) != want:
            failures.append(
                f"seed_spec.{key} {spec.get(key)} != record {want}"
            )
    if ring.get("seeded_count") != RECORD_SEED_SPEC["count"]:
        failures.append(
            f"seeded_count {ring.get('seeded_count')} "
            f"!= record {RECORD_SEED_SPEC['count']}",
        )
    bad = [
        h for h in ring.get("seeded_hosts") or []
        if h.get("role") != RECORD_SEED_SPEC["role"]
    ]
    if bad:
        failures.append(
            f"{len(bad)} seeded host(s) with role outside "
            f"{RECORD_SEED_SPEC['role']!r}",
        )
    return failures


def _audit_slot_echoes(payload: dict, declared: dict) -> list[str]:
    """witness + during-window echoes vs the arm's declared slot."""
    witness = payload.get("quarantine_witness")
    if not isinstance(witness, dict):
        return ["missing quarantine_witness block"]
    failures: list[str] = []
    got_pid = witness.get("protocol_id")
    if got_pid != declared["protocol_id"]:
        failures.append(
            f"quarantine_witness.protocol_id {got_pid} "
            f"!= declared {declared['protocol_id']}",
        )
    if list(witness.get("window_days") or []) != declared["window"]:
        failures.append(
            f"quarantine_witness.window_days {witness.get('window_days')} "
            f"!= declared {declared['window']}",
        )
    if payload.get("infections_during_window") is None:
        failures.append("infections_during_window missing")
    for key in (
        "during_window_by_role",
        "during_window_by_zone_class",
        "during_window_by_route",
    ):
        if not isinstance(payload.get(key), dict):
            failures.append(f"{key} missing")
    return failures


def _audit_channel_echoes(payload: dict, declared: dict) -> list[str]:
    """The REF arm's channel echoes resolve as declared."""
    failures: list[str] = []
    if declared["onset_recording"] is not None and (
        payload.get("onset_recording") != declared["onset_recording"]
    ):
        failures.append("onset_recording echo != declared block")
    if declared["eligibility"] is not None and (
        payload.get("onset_eligibility_by_severity")
        != declared["eligibility"]
    ):
        failures.append(
            "onset_eligibility_by_severity echo != declared ladder",
        )
    return failures


def audit_cell(payload: dict, declared: dict, theta: float) -> list[str]:
    """Return the list of audit violations for one cell payload."""
    ring = payload.get("seed_ring")
    failures = (
        ["missing seed_ring block"]
        if not isinstance(ring, dict)
        else _audit_seed_echoes(ring)
    )
    return (
        failures
        + _audit_slot_echoes(payload, declared)
        + _audit_channel_echoes(payload, declared)
    )


def _witness(p: dict) -> dict:
    return p.get("quarantine_witness") or {}


def _arm_start(p: dict) -> int:
    """The arm's resolved start day, off the payload's own echo."""
    window = _witness(p).get("window_days") or [None]
    return int(window[0])


def _day_count(curve: dict, days: range) -> float:
    """Total counts in a day range off a {day: int | {role: int}} curve."""
    total = 0.0
    for d in days:
        value = curve.get(str(d)) or 0
        total += sum(value.values()) if isinstance(value, dict) else value
    return total


def _post_start_mass(p: dict, start: int) -> float:
    """Acquisitions on/after *start* off the acquisition_curve."""
    by_day = (p.get("acquisition_curve") or {}).get("total_by_day") or {}
    return float(sum(
        c for d, c in by_day.items() if int(d) >= start
    ))


def _start_kink(p: dict, start: int) -> float | None:
    """Post/pre mean daily recorded onsets across the arm's own start."""
    curve = p.get("onset_curve") or {}
    pre = _day_count(curve, range(start - KINK_HALF_WINDOW, start))
    post = _day_count(curve, range(start, start + KINK_HALF_WINDOW))
    if pre <= 0:
        return None
    return (post / KINK_HALF_WINDOW) / (pre / KINK_HALF_WINDOW)


def _crew_lag(p: dict) -> float | None:
    """Mean crew onset day - mean passenger onset day for one cell."""
    curve = p.get("onset_curve") or {}
    totals: dict[str, list[float]] = {}
    for day, roles in curve.items():
        for role, count in roles.items():
            acc = totals.setdefault(role, [0.0, 0.0])
            acc[0] += int(day) * count
            acc[1] += count
    crew = totals.get("crew")
    pax = totals.get("passenger")
    if not crew or not pax or not crew[1] or not pax[1]:
        return None
    return crew[0] / crew[1] - pax[0] / pax[1]


def _takeoff_window_stats(takeoff: list[dict]) -> dict:
    """Window-stratum medians + the firing/echo stats of one row."""
    during = [
        float(p["infections_during_window"])
        for p in takeoff
        if p.get("infections_during_window") is not None
    ]
    before = [
        float(p["infections_before_quarantine"])
        for p in takeoff
        if p.get("infections_before_quarantine") is not None
    ]
    after = [
        float(p["infections_after_quarantine"])
        for p in takeoff
        if p.get("infections_after_quarantine") is not None
    ]
    share = [
        float(p["infections_during_window"]) / float(p["infections_total"])
        for p in takeoff
        if p.get("infections_during_window") is not None
        and p.get("infections_total")
    ]
    return {
        "infections_before_window": band_stats(before),
        "infections_during_window": band_stats(during),
        "infections_after_window": band_stats(after),
        "during_window_share": {"median": quantile(share, 0.5)},
        "activated_fraction": (
            sum(1 for p in takeoff if _witness(p).get("activated"))
            / len(takeoff)
            if takeoff else 0.0
        ),
        "confined_at_activation": band_stats([
            float(_witness(p)["confined_at_activation"])
            for p in takeoff
            if _witness(p).get("confined_at_activation") is not None
        ]),
    }


def _pooled_during(takeoff: list[dict]) -> dict:
    """Pooled during-window mix + the concentration share of a row."""
    by_role: Counter[str] = Counter()
    by_zone: Counter[str] = Counter()
    by_route: Counter[str] = Counter()
    for p in takeoff:
        by_role.update(p.get("during_window_by_role") or {})
        by_zone.update(p.get("during_window_by_zone_class") or {})
        by_route.update(p.get("during_window_by_route") or {})
    total = sum(by_zone.values())
    concentrated = (
        sum(by_zone.get(z, 0) for z in CONCENTRATION_ZONE_CLASSES) / total
        if total else None
    )
    return {
        "during_window_by_role_pooled": dict(by_role),
        "during_window_by_zone_class_pooled": dict(by_zone),
        "during_window_by_route_pooled": dict(by_route),
        "during_window_cabin_mess_share": concentrated,
    }


def _row_stats(payloads: list[dict]) -> dict:
    """Takeoff-conditional medians + the shape discriminators per row."""
    takeoff, vectors = takeoff_split(payloads)
    kinks = [
        k for p in takeoff
        if (k := _start_kink(p, _arm_start(p))) is not None
    ]
    lags = [
        lag for p in takeoff
        if (lag := _crew_lag(p)) is not None
    ]
    med_during = None
    med_before = None
    window = _takeoff_window_stats(takeoff)
    pooled = _pooled_during(takeoff)
    med_during = window["infections_during_window"]["median"]
    med_before = window["infections_before_window"]["median"]
    during_dominant = (
        med_during is not None
        and med_before is not None
        and med_during > med_before
    )
    med_lag = quantile(lags, 0.5)
    concentrated = pooled["during_window_cabin_mess_share"]
    truncation = bool(
        during_dominant
        and concentrated is not None
        and concentrated > CONCENTRATION_SHARE
        and med_lag is not None
        and med_lag > 0.0
    )
    legs = anchor_legs(len(takeoff), vectors["t_inf"], vectors["t_share"])
    return {
        "n": len(payloads),
        "takeoff_n": len(takeoff),
        "fizzle_majority": len(takeoff) * 2 < len(payloads),
        "recorded_onsets": band_stats(vectors["rec"]),
        "before_share": {"median": quantile(vectors["shares"], 0.5)},
        "takeoff_recorded_onsets": band_stats(vectors["t_rec"]),
        "takeoff_infections_total": band_stats(vectors["t_inf"]),
        "takeoff_before_share": band_stats(vectors["t_share"]),
        "truth_leg_in_band": legs["truth_leg_in_band"],
        "timing_leg_in_band": legs["timing_leg_in_band"],
        "both_legs": legs["both_legs"],
        "during_dominant": bool(during_dominant and legs["enough_takeoff"]),
        "truncation_signature": bool(
            truncation and legs["enough_takeoff"]
        ),
        "arm_start_kink": {
            "post_over_pre_median": quantile(kinks, 0.5),
            "post_over_pre_q05": quantile(kinks, 0.05),
            "post_over_pre_q95": quantile(kinks, 0.95),
        },
        "crew_lag_days": {"median": med_lag},
        **window,
        **pooled,
        "row_extra": (
            f"dur {_fmt(med_during)} "
            f"shr {_fmt(window['during_window_share']['median'])} "
            f"kink {_fmt(quantile(kinks, 0.5))} "
            f"lag {_fmt(med_lag)}"
        ),
    }


def _fmt(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.3g}"


def _paired_delta_row(
    theta: float, arm_id: str, row: list[dict], base: list[dict],
) -> dict:
    """Seed-paired (arm - D0) deltas on the scored observables."""
    base_by_seed = {
        int(p["cell"]["seed"]): p for p in base
        if int(p["observables"]["recorded_onsets"]) >= 10
    }
    deltas: dict[str, list[float]] = {
        "recorded_onsets": [],
        "onsets_before_split_day": [],
        "infections_total": [],
        "infections_during_window": [],
        "post_start_mass": [],
        "crew_lag_days": [],
    }
    for p in row:
        cell = p.get("cell") or {}
        seed = int(cell.get("seed"))
        b = base_by_seed.get(seed)
        if b is None:
            continue
        if int(p["observables"]["recorded_onsets"]) < 10:
            continue
        start = _arm_start(p)
        deltas["recorded_onsets"].append(
            float(p["observables"]["recorded_onsets"])
            - float(b["observables"]["recorded_onsets"])
        )
        deltas["onsets_before_split_day"].append(
            float(p["observables"]["onsets_before_split_day"])
            - float(b["observables"]["onsets_before_split_day"])
        )
        if p.get("infections_total") is not None and (
            b.get("infections_total") is not None
        ):
            deltas["infections_total"].append(
                float(p["infections_total"]) - float(b["infections_total"])
            )
        if (
            p.get("infections_during_window") is not None
            and b.get("infections_during_window") is not None
        ):
            deltas["infections_during_window"].append(
                float(p["infections_during_window"])
                - float(b["infections_during_window"])
            )
        deltas["post_start_mass"].append(
            _post_start_mass(p, start) - _post_start_mass(b, start)
        )
        lag = _crew_lag(p)
        base_lag = _crew_lag(b)
        if lag is not None and base_lag is not None:
            deltas["crew_lag_days"].append(lag - base_lag)
    return {
        "theta": theta,
        "arm_id": arm_id,
        "n_paired": len(deltas["recorded_onsets"]),
        **{
            f"delta_{k}": band_stats(v) for k, v in deltas.items()
        },
    }


def _paired_rows(rows: dict[tuple, list[dict]]) -> dict:
    """Seed-paired deltas vs D0_declared for every arm, per theta."""
    out: dict[str, Any] = {}
    for (theta, arm_id), row in sorted(rows.items()):
        if arm_id == BASELINE_ARM:
            continue
        base = rows.get((theta, BASELINE_ARM)) or []
        out[f"theta={theta:.4g}|arm={arm_id}"] = _paired_delta_row(
            theta, arm_id, row, base,
        )
    return out


def _row_triggers(
    theta: float, arm_id: str, stats: dict,
) -> dict | None:
    """The report-immediately rows (non-scoring arms never trigger)."""
    if arm_id in NON_SCORING_ARMS:
        return None
    kinds = [
        name
        for name, on in (
            ("TRUTH-IN-BAND", stats["truth_leg_in_band"]),
            ("TIMING-IN-BAND", stats["timing_leg_in_band"]),
            ("FIZZLE-MAJORITY", stats["fizzle_majority"]),
            ("DURING-DOMINANT", stats["during_dominant"]),
            ("TRUNCATION-SIGNATURE", stats["truncation_signature"]),
        )
        if on
    ]
    if not kinds:
        return None
    return {
        "theta": theta, "arm_id": arm_id, "triggers": kinds,
        "takeoff_infections_total": stats["takeoff_infections_total"],
        "takeoff_before_share": stats["takeoff_before_share"],
        "infections_during_window": stats["infections_during_window"],
        "during_window_cabin_mess_share": (
            stats["during_window_cabin_mess_share"]
        ),
        "arm_start_kink": stats["arm_start_kink"],
        "crew_lag_days": stats["crew_lag_days"],
    }


def main(argv: list[str] | None = None) -> int:
    design = load_design(
        resolve_design_arg(argv, REPO_ROOT), repo_root=REPO_ROOT,
    )
    return run_readout(
        argv,
        repo_root=REPO_ROOT,
        cells=enumerate_cells(design),
        declared_by_arm={
            arm["arm_id"]: _declared(arm) for arm in (design.arms or ())
        },
        audit_cell=audit_cell,
        row_stats=_row_stats,
        report_key="triggered_rows",
        row_triggers=_row_triggers,
        paired_rows=_paired_rows,
    )


if __name__ == "__main__":
    raise SystemExit(main())
