"""INFO-SUPPRESS-V1 readout: mechanism-echo audit + recognition
witnesses + the both-legs test + seed-paired deltas vs D0 per row.

Pools the synced campaign cells (``aws s3 sync .../cells/ <dir>``) for
``covid_info_suppress_v1`` and reports, per (theta, arm) row:

* the mechanism audit — ``info_suppression`` carries the arm's declared
  block verbatim and the witness fields resolve: ``armed_epoch``
  non-null on IS cells (the mechanism fired) and null on D0 (off),
  ``closed_zones_applied`` == the declared venue list,
  ``self_isolated_count`` > 0 when a scope is declared, plus the
  constant-geometry ``seed_ring`` check;
* takeoff-seed medians and q05-q95 of recorded_onsets, infections_total
  and before_share (the two anchors: 197 / 0.173 at the RECORD's day-16
  boundary — arm-invariant — vs the H5 band [712, 960]);
* the recognition witnesses — armed_epoch and self_isolated_count
  distributions, crew-onset lag, and the post- arming acquisition mass
  (infections acquired on/after the armed day);
* the paired_rows block: seed-paired deltas vs D0_declared on the three
  conditioned observables — recorded_onsets, before_share,
  infections_total — restricted to seeds where BOTH cells are takeoff;
* the report-immediately triggers: CANNOT-FIRE (null armed_epoch on an
  IS cell), COMPOSITION-ONLY (the row-level before_share move is a
  takeoff-selection artifact — the task's named check), and the
  in-band truth/timing landings.

CLI paths are confined under the repository root (sync cells to
``campaign_results/<design>/cells/``); an audit failure is reported per
cell. The audit+score CLI skeleton is shared with the other conditioned
readouts in tools/covid_screen_readout_common.py.
"""

from __future__ import annotations

import os
import sys
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

# The record's seed geometry is constant on this design (no seed_patch).
RECORD_SEED_SPEC = {"count": 1, "onset_day": -1.0, "role": "passenger"}
BASELINE_ARM = "D0_declared"
TAKEOFF_MIN = 10
# The composition check: an unpaired row share move this large with a
# paired delta that straddles zero is takeoff selection, not mechanism.
COMPOSITION_ROW_MOVE = 0.05
# Declared block fields every info_suppression payload echoes back.
DECLARED_FIELDS = (
    "enabled",
    "trigger_status",
    "response_delay_hours",
    "self_isolation_scope",
    "closed_zones",
    "route_scalars",
)


def _declared(arm: dict) -> dict:
    """The arm's declared info_suppression block ({} on the baseline)."""
    ov = arm.get("overrides") or {}
    block = dict(ov.get("info_suppression") or {})
    return {
        "block": block,
        "enabled": bool(block.get("enabled", False)),
        "scope": block.get("self_isolation_scope"),
        "closed_zones": list(block.get("closed_zones") or []),
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


def _audit_echo_fields(block: dict, declared: dict) -> list[str]:
    """Declared fields echo back verbatim off the payload."""
    want = declared["block"]
    failures: list[str] = []
    for field_name in DECLARED_FIELDS:
        got = block.get(field_name)
        declared_val = want.get(field_name)
        match = True
        if field_name == "closed_zones":
            match = list(got or []) == list(declared_val or [])
        elif field_name == "route_scalars":
            match = dict(got or {}) == dict(declared_val or {})
        elif field_name == "enabled":
            match = bool(got) is bool(declared_val or False)
        else:
            match = got == declared_val
        if not match:
            failures.append(
                f"info_suppression.{field_name} {got} "
                f"!= declared {declared_val}",
            )
    return failures


def _audit_witnesses(block: dict, declared: dict) -> list[str]:
    """The live witness fields resolve as the declaration says."""
    failures: list[str] = []
    armed = block.get("armed_epoch")
    if not declared["enabled"]:
        if armed is not None:
            failures.append("D0 cell armed a disabled mechanism")
        return failures
    if armed is None:
        failures.append(
            "info_suppression armed_epoch is null -- the mechanism "
            "never fired (CANNOT-FIRE)",
        )
        return failures
    rec = block.get("recognition_epoch")
    if rec is None or int(rec) > int(armed):
        failures.append(
            f"recognition_epoch {rec} not <= armed_epoch {armed}",
        )
    if declared["scope"] and int(block.get("self_isolated_count") or 0) <= 0:
        failures.append(
            "self_isolated_count == 0 on a scoped arm",
        )
    if list(block.get("closed_zones_applied") or []) != list(
        declared["closed_zones"]
    ):
        failures.append("closed_zones_applied != declared closed_zones")
    if declared["closed_zones"] and sorted(
        block.get("closed_venue_ids_engine") or []
    ) != sorted(declared["closed_zones"]):
        failures.append("engine closed_venue_ids != declared closed_zones")
    return failures


def audit_cell(payload: dict, declared: dict, theta: float) -> list[str]:
    """Return the list of audit violations for one cell payload."""
    ring = payload.get("seed_ring")
    failures = (
        ["missing seed_ring block"]
        if not isinstance(ring, dict)
        else _audit_seed_echoes(ring)
    )
    block = payload.get("info_suppression")
    if not isinstance(block, dict):
        return failures + ["missing info_suppression block"]
    return (
        failures
        + _audit_echo_fields(block, declared)
        + _audit_witnesses(block, declared)
    )


def _info(p: dict) -> dict:
    return p.get("info_suppression") or {}


def _armed_day(p: dict) -> float | None:
    armed = _info(p).get("armed_epoch")
    return None if armed is None else float(armed) / 24.0  # clock-exempt: epoch->day on the hourly clock


def _post_arming_mass(p: dict) -> float | None:
    """Infections acquired on/after the armed day off acquisition_curve."""
    day = _armed_day(p)
    if day is None:
        return None
    by_day = (p.get("acquisition_curve") or {}).get("total_by_day") or {}
    return float(sum(c for d, c in by_day.items() if float(d) >= day))


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


def _row_stats(payloads: list[dict]) -> dict:
    """Takeoff-conditional medians + the recognition witnesses per row."""
    takeoff, vectors = takeoff_split(payloads)
    armed = [
        d for p in takeoff if (d := _armed_day(p)) is not None
    ]
    isolated = [
        float(_info(p)["self_isolated_count"])
        for p in takeoff
        if _info(p).get("self_isolated_count") is not None
    ]
    post = [
        m for p in takeoff if (m := _post_arming_mass(p)) is not None
    ]
    lags = [
        lag for p in takeoff if (lag := _crew_lag(p)) is not None
    ]
    legs = anchor_legs(len(takeoff), vectors["t_inf"], vectors["t_share"])
    med_armed = quantile(armed, 0.5)
    med_iso = quantile(isolated, 0.5)
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
        "enough_takeoff": legs["enough_takeoff"],
        "armed_day": band_stats(armed),
        "self_isolated_count": band_stats(isolated),
        "post_arming_mass": band_stats(post),
        "crew_lag_days": {"median": quantile(lags, 0.5)},
        "row_extra": (
            f"armed {_fmt(med_armed)} "
            f"iso {_fmt(med_iso)} "
            f"post {_fmt(quantile(post, 0.5))} "
            f"lag {_fmt(quantile(lags, 0.5))}"
        ),
    }


def _fmt(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.3g}"


def _share(p: dict) -> float | None:
    obs = p.get("observables") or {}
    rec = obs.get("recorded_onsets")
    if not rec:
        return None
    return float(obs["onsets_before_split_day"]) / float(rec)


def _paired_delta_row(
    theta: float, arm_id: str, row: list[dict], base: list[dict],
) -> dict:
    """Seed-paired (arm - D0) deltas on the conditioned observables."""
    base_by_seed = {
        int(p["cell"]["seed"]): p for p in base
        if int(p["observables"]["recorded_onsets"]) >= TAKEOFF_MIN
    }
    deltas: dict[str, list[float]] = {
        "recorded_onsets": [],
        "before_share": [],
        "infections_total": [],
        "post_arming_mass": [],
    }
    for p in row:
        seed = int((p.get("cell") or {}).get("seed"))
        b = base_by_seed.get(seed)
        if b is None:
            continue
        if int(p["observables"]["recorded_onsets"]) < TAKEOFF_MIN:
            continue
        deltas["recorded_onsets"].append(
            float(p["observables"]["recorded_onsets"])
            - float(b["observables"]["recorded_onsets"])
        )
        s_arm = _share(p)
        s_base = _share(b)
        if s_arm is not None and s_base is not None:
            deltas["before_share"].append(s_arm - s_base)
        if p.get("infections_total") is not None and (
            b.get("infections_total") is not None
        ):
            deltas["infections_total"].append(
                float(p["infections_total"]) - float(b["infections_total"])
            )
        m_arm = _post_arming_mass(p)
        m_base = _post_arming_mass(b)
        if m_arm is not None and m_base is not None:
            deltas["post_arming_mass"].append(m_arm - m_base)
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


def _composition_flag(
    stats: dict, paired: dict | None, base_stats: dict | None,
) -> bool:
    """Row-level share moved but the paired delta straddles zero."""
    if not paired or not base_stats:
        return False
    med_share = stats["takeoff_before_share"]["median"]
    base_share = base_stats["takeoff_before_share"]["median"]
    if med_share is None or base_share is None:
        return False
    if abs(med_share - base_share) < COMPOSITION_ROW_MOVE:
        return False
    delta = paired.get("delta_before_share") or {}
    lo, hi = delta.get("q05"), delta.get("q95")
    return lo is not None and hi is not None and lo <= 0.0 <= hi


def _row_triggers(
    theta: float, arm_id: str, stats: dict,
) -> dict | None:
    """The report-immediately rows (the baseline arm never triggers)."""
    if arm_id == BASELINE_ARM:
        return None
    kinds = [
        name
        for name, on in (
            ("TRUTH-IN-BAND", stats["truth_leg_in_band"]),
            ("TIMING-IN-BAND", stats["timing_leg_in_band"]),
            ("FIZZLE-MAJORITY", stats["fizzle_majority"]),
        )
        if on
    ]
    if not kinds:
        return None
    return {
        "theta": theta, "arm_id": arm_id, "triggers": kinds,
        "takeoff_infections_total": stats["takeoff_infections_total"],
        "takeoff_before_share": stats["takeoff_before_share"],
        "armed_day": stats["armed_day"],
        "self_isolated_count": stats["self_isolated_count"],
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
