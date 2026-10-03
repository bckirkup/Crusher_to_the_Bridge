"""Shared machinery for the conditioned-array readout tools.

Every covid conditioned array (SEED-GEOM-V1, SUSCEPT-V1, ...) ships a
readout that loads synced cell payloads, audits each payload's echoes
against its arm's declared overrides, buckets payloads into
(theta, arm) rows, and scores the two anchors takeoff-conditional:
the record's 197 dated onsets / 0.173 before-share and the held-out
serology band [712, 960]. The per-campaign pieces — the declared-arm
projection, the per-cell audit, the row stats, and the trigger
grammar — stay in each campaign's own readout; this module carries
only the shared skeleton so the five-and-counting readout tools do
not drift copies of one another.

CLI paths are confined under the repository root (sync cells to
``campaign_results/<design>/cells/``); an audit failure is reported
per cell.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from collections.abc import Callable
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from picard_framework.covid_boarding_screen import (  # noqa: E402
    enumerate_cells,
    load_design,
)
from simulation_utils.paths import (  # noqa: E402
    resolve_child_path,
    resolve_repo_path,
    validated_open,
)

# The anchors every conditioned covid array is scored against: the
# record's 197 dated onsets with 34 of them (share 0.173) before day 17,
# and the held-out covid.H5 serology band. Takeoff requires a cell to
# have ignited at all (>= 10 recorded onsets); a row needs >= 5 takeoff
# seeds to be scored.
TAKEOFF_MIN_ONSETS = 10
T1_RECORDED = 197.0
T1_BEFORE_SHARE = 0.173
BEFORE_SHARE_TOL = 0.10
H5_BAND = (712.0, 960.0)
MIN_TAKEOFF_SEEDS = 5


def quantile(values: list[float], p: float) -> float | None:
    """Nearest-order-statistic quantile; None on an empty sample."""
    if not values:
        return None
    srt = sorted(values)
    i = min(len(srt) - 1, max(0, int(round(p * (len(srt) - 1)))))
    return float(srt[i])


def band_stats(values: list[float]) -> dict[str, float | None]:
    """Median and the q05-q95 reporting interval of one sample."""
    return {
        "median": quantile(values, 0.5),
        "q05": quantile(values, 0.05),
        "q95": quantile(values, 0.95),
    }


def declared_hand_mode(arm: dict, shipped_mode: str) -> dict:
    """The arm's declared hand-reservoir mode projection.

    An arm whose overrides leave ``transmission.hand_reservoir_mode``
    alone resolves the shipped default (``hygiene_cycle`` since
    NORO-HAND-PRACTICE-01, PR #804); each readout passes its own
    shipped-mode constant so a stale readout still audits what its
    design declared.
    """
    tx = (arm.get("overrides") or {}).get("transmission_overrides") or {}
    return {
        "hand_reservoir_mode": str(
            tx.get("hand_reservoir_mode", shipped_mode),
        ),
    }


def audit_hand_mode(payload: dict, declared: dict) -> list[str]:
    """Audit a cell's delivery-mode echo against its arm's declaration."""
    delivery = payload.get("delivery") or {}
    resolved_mode = delivery.get("hand_reservoir_mode")
    if resolved_mode == declared["hand_reservoir_mode"]:
        return []
    return [
        f"hand_reservoir_mode resolved {resolved_mode!r}, "
        f"declared {declared['hand_reservoir_mode']!r}",
    ]


def load_cell_payloads(cells_dir: str) -> dict[str, dict]:
    """Read every cell JSON under *cells_dir* (contained to the dir)."""
    payloads: dict[str, dict] = {}
    for name in sorted(os.listdir(cells_dir)):
        if not name.endswith(".json"):
            continue
        path = resolve_child_path(cells_dir, name)
        with validated_open(
            path, allowed_roots=(cells_dir,), encoding="utf-8",
        ) as fh:
            payloads[name] = json.load(fh)
    return payloads


def audit_all(
    payloads: dict[str, dict],
    cells: list[Any],
    declared_by_arm: dict[str, dict],
    audit_cell: Callable[[dict, dict, float], list[str]],
) -> tuple[dict[str, list[str]], dict[tuple, list[dict]]]:
    """Audit each payload against its arm's declaration, bucket by row.

    ``audit_cell(payload, declared, theta)`` returns the violations for
    one payload; payloads whose cell key is not on the declared lattice
    or whose arm is unknown are failures by construction.
    """
    by_key = {(c.theta, c.arm_id, c.seed): c for c in cells}
    audit_failures: dict[str, list[str]] = {}
    rows: dict[tuple, list[dict]] = {}
    for name, payload in payloads.items():
        cell = payload.get("cell") or {}
        key = (
            float(cell.get("theta")), cell.get("arm_id"),
            int(cell.get("seed")),
        )
        if key not in by_key:
            audit_failures[name] = ["cell key not in the declared lattice"]
            continue
        declared = declared_by_arm.get(cell.get("arm_id"))
        failures = (
            audit_cell(payload, declared, key[0])
            if declared is not None
            else [f"unknown arm {cell.get('arm_id')}"]
        )
        if failures:
            audit_failures[name] = failures
        rows.setdefault((key[0], key[1]), []).append(payload)
    return audit_failures, rows


def takeoff_split(payloads: list[dict]) -> tuple[list[dict], dict[str, list[float]]]:
    """Partition a row into takeoff cells and the scored observables.

    Returns the takeoff payloads plus the score vectors: all-cells
    recorded_onsets and before_share, takeoff recorded_onsets,
    infections_total, and before_share.
    """
    takeoff = [
        p for p in payloads
        if int(p["observables"]["recorded_onsets"]) >= TAKEOFF_MIN_ONSETS
    ]
    return takeoff, {
        "rec": [
            float(p["observables"]["recorded_onsets"]) for p in payloads
        ],
        "shares": [
            float(p["observables"]["onsets_before_split_day"])
            / float(p["observables"]["recorded_onsets"])
            for p in payloads
            if int(p["observables"]["recorded_onsets"]) > 0
        ],
        "t_rec": [
            float(p["observables"]["recorded_onsets"]) for p in takeoff
        ],
        "t_inf": [
            float(p["infections_total"]) for p in takeoff
            if p.get("infections_total") is not None
        ],
        "t_share": [
            float(p["observables"]["onsets_before_split_day"])
            / float(p["observables"]["recorded_onsets"])
            for p in takeoff
        ],
    }


def standard_row_stats(
    payloads: list[dict],
    extra_fields: Callable[[list[dict], dict], dict] | None = None,
) -> dict:
    """The quarantine-window row stats every conditioned array reports.

    Takeoff-conditional band stats on recorded_onsets / infections_total /
    before_share, the during-quarantine count + share, the pooled route /
    zone-class / role tallies, and the anchor legs. ``extra_fields`` is
    a campaign hook receiving (takeoff payloads, computed stats) and
    returning any campaign-specific keys (kink ratios, row_extra, ...).
    """
    takeoff, vectors = takeoff_split(payloads)
    during = [
        float(p["infections_during_quarantine"]) for p in takeoff
        if p.get("infections_during_quarantine") is not None
    ]
    before = [
        float(p["infections_before_quarantine"]) for p in takeoff
        if p.get("infections_before_quarantine") is not None
    ]
    during_share = [
        float(p["infections_during_quarantine"])
        / float(p["infections_total"])
        for p in takeoff
        if p.get("infections_during_quarantine") is not None
        and p.get("infections_total")
    ]
    aboard_route: Counter[str] = Counter()
    during_route: Counter[str] = Counter()
    during_zone: Counter[str] = Counter()
    during_role: Counter[str] = Counter()
    for p in takeoff:
        aboard_route.update(
            p.get("aboard_window_by_route")
            or (p.get("seed_ring") or {}).get("aboard_window_by_route")
            or {}
        )
        during_route.update(p.get("during_quarantine_by_route") or {})
        during_zone.update(
            p.get("during_quarantine_by_zone_class") or {}
        )
        during_role.update(p.get("during_quarantine_by_role") or {})

    med_during = quantile(during, 0.5)
    med_before = quantile(before, 0.5)
    med_share = quantile(during_share, 0.5)
    dominant = (
        med_during is not None and med_before is not None
        and med_during > med_before
    )
    legs = anchor_legs(len(takeoff), vectors["t_inf"], vectors["t_share"])
    stats = {
        "n": len(payloads),
        "takeoff_n": len(takeoff),
        "fizzle_majority": len(takeoff) * 2 < len(payloads),
        "before_share": {"median": quantile(vectors["shares"], 0.5)},
        "truth_leg_in_band": legs["truth_leg_in_band"],
        "timing_leg_in_band": legs["timing_leg_in_band"],
        "both_legs": legs["both_legs"],
        "during_share": {"median": med_share},
        "during_dominant": bool(dominant and legs["enough_takeoff"]),
        "aboard_window_by_route_pooled": dict(aboard_route),
        "during_quarantine_by_route_pooled": dict(during_route),
        "during_quarantine_by_zone_class_pooled": dict(during_zone),
        "during_quarantine_by_role_pooled": dict(during_role),
    }
    for key, vec in (
        ("recorded_onsets", vectors["rec"]),
        ("takeoff_recorded_onsets", vectors["t_rec"]),
        ("takeoff_infections_total", vectors["t_inf"]),
        ("takeoff_before_share", vectors["t_share"]),
        ("infections_before_quarantine", before),
        ("during_quarantine", during),
    ):
        stats[key] = band_stats(vec)
    if extra_fields is not None:
        stats.update(extra_fields(takeoff, stats))
    return stats


def row_trigger_report(
    theta: float,
    arm_id: str,
    stats: dict,
    kinds: list[str],
    fields: tuple[str, ...],
) -> dict:
    """One report-immediately entry: the trigger kinds plus the named
    stat blocks the row printed."""
    return {
        "theta": theta,
        "arm_id": arm_id,
        "triggers": kinds,
        **{name: stats[name] for name in fields},
    }


def row_triggers(
    theta: float,
    arm_id: str,
    stats: dict,
    kind_flags: tuple[tuple[str, str], ...],
    fields: tuple[str, ...],
) -> dict | None:
    """A campaign's whole ``row_triggers`` callback as data.

    ``kind_flags`` pairs a report label with the stats key that fires it
    (``("TRUTH-IN-BAND", "truth_leg_in_band")``); ``fields`` names the
    stat blocks copied into the entry. Returns None when nothing fires.
    """
    kinds = [label for label, flag in kind_flags if stats.get(flag)]
    if not kinds:
        return None
    return row_trigger_report(theta, arm_id, stats, kinds, fields)


def anchor_legs(
    takeoff_n: int,
    t_inf: list[float],
    t_share: list[float],
) -> dict[str, Any]:
    """The both-legs verdict fields every row carries."""
    med_inf = quantile(t_inf, 0.5)
    med_share = quantile(t_share, 0.5)
    enough = takeoff_n >= MIN_TAKEOFF_SEEDS
    in_band = (
        med_inf is not None and H5_BAND[0] <= med_inf <= H5_BAND[1]
    )
    timing_hit = (
        med_share is not None
        and abs(med_share - T1_BEFORE_SHARE) <= BEFORE_SHARE_TOL
    )
    return {
        "enough_takeoff": enough,
        "truth_leg_in_band": bool(in_band and enough),
        "timing_leg_in_band": bool(timing_hit and enough),
        "both_legs": bool(in_band and timing_hit and enough),
    }


def _default_row_line(label: str, stats: dict) -> str:
    """One printed row: takeoff mass, the three scored legs, flags."""

    def med(v: float | None) -> str:
        return "n/a" if v is None else f"{v:.3g}"

    ti = stats["takeoff_infections_total"]
    ts = stats["takeoff_before_share"]
    tr = stats["takeoff_recorded_onsets"]
    flags = [
        name
        for name, on in (
            ("TRUTH-IN-BAND", stats["truth_leg_in_band"]),
            ("TIMING-IN-BAND", stats["timing_leg_in_band"]),
            ("FIZZLE-MAJORITY", stats.get("fizzle_majority", False)),
            ("DURING-DOMINANT", stats.get("during_dominant", False)),
        )
        if on
    ]
    extra = f" {stats['row_extra']}" if stats.get("row_extra") else ""
    return (
        f"  {label}: takeoff {stats['takeoff_n']}/{stats['n']} "
        f"rec med {med(tr['median'])} "
        f"[{med(tr['q05'])},{med(tr['q95'])}] "
        f"inf med {med(ti['median'])} "
        f"[{med(ti['q05'])},{med(ti['q95'])}] "
        f"bshr med {med(ts['median'])}{extra} {' '.join(flags)}"
    )


def run_readout(
    argv: list[str] | None,
    *,
    repo_root: str,
    cells: list[Any],
    declared_by_arm: dict[str, dict],
    audit_cell: Callable[[dict, dict, float], list[str]],
    row_stats: Callable[[list[dict]], dict],
    report_key: str,
    row_triggers: Callable[[float, str, dict], dict | None],
    paired_rows: Callable[[dict[tuple, list[dict]]], dict] | None = None,
) -> int:
    """The readout CLI skeleton every conditioned array shares.

    ``row_triggers`` returns the report-immediately entry for one row
    (or None); entries collect under ``report_key`` and print at the
    end. A row's stats may set ``row_extra`` to append per-campaign
    columns to the printed line. ``paired_rows``, when given, receives
    the whole (theta, arm) -> payloads map once every row is scored and
    returns the cross-row block stored under ``report["paired_rows"]``
    (seed-paired deltas against the baseline arm and the like).
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--cells", required=True)
    parser.add_argument("--design", required=True)
    parser.add_argument("--out", default=None)
    parser.add_argument(
        "--allow-partial", action="store_true",
        help="read whatever cells exist (canary/incomplete arrays)",
    )
    args = parser.parse_args(argv)

    cells_dir = resolve_repo_path(repo_root, args.cells)
    payloads = load_cell_payloads(cells_dir)
    if not args.allow_partial and len(payloads) < len(cells):
        print(
            f"{len(payloads)} of {len(cells)} cells present; "
            "pass --allow-partial for a partial read",
            file=sys.stderr,
        )
        return 2

    audit_failures, rows = audit_all(
        payloads, cells, declared_by_arm, audit_cell,
    )
    report: dict[str, Any] = {
        "cells_found": len(payloads),
        "cells_expected": len(cells),
        "audit_failures": audit_failures,
        "rows": {},
        report_key: [],
    }
    for (theta, arm_id), row in sorted(rows.items()):
        stats = row_stats(row)
        report["rows"][f"theta={theta:.4g}|arm={arm_id}"] = stats
        trigger = row_triggers(theta, arm_id, stats)
        if trigger:
            report[report_key].append(trigger)
    if paired_rows is not None:
        report["paired_rows"] = paired_rows(rows)

    if args.out:
        out_path = resolve_repo_path(repo_root, args.out)
        with validated_open(
            out_path, "w", allowed_roots=(repo_root,), encoding="utf-8",
        ) as fh:
            json.dump(report, fh, indent=2, sort_keys=True)

    print(
        f"{report['cells_found']}/{report['cells_expected']} cells; "
        f"{len(audit_failures)} audit failures",
    )
    for label, stats in report["rows"].items():
        print(_default_row_line(label, stats))
    if report[report_key]:
        print(
            f"{report_key.upper()}:",
            json.dumps(report[report_key], indent=1),
        )
    return 0


def resolve_design_arg(argv: list[str] | None, repo_root: str) -> str:
    """Parse --design early so each tool can load its own design file."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--design", required=True)
    known, _ = parser.parse_known_args(argv)
    return resolve_repo_path(repo_root, known.design)


def fmt3g(v: float | None) -> str:
    """The report line's .3g placeholder for a missing median."""
    return "n/a" if v is None else f"{v:.3g}"


def audit_seed_echoes(ring: dict, record_seed_spec: dict) -> list[str]:
    """seed_spec echoes the record's seed on every arm (no seed_patch)."""
    failures: list[str] = []
    spec = ring.get("seed_spec") or {}
    for key, want in record_seed_spec.items():
        if spec.get(key) != want:
            failures.append(
                f"seed_spec.{key} {spec.get(key)} != record {want}"
            )
    if ring.get("seeded_count") != record_seed_spec["count"]:
        failures.append(
            f"seeded_count {ring.get('seeded_count')} "
            f"!= record {record_seed_spec['count']}",
        )
    bad = [
        h for h in ring.get("seeded_hosts") or []
        if h.get("role") != record_seed_spec["role"]
    ]
    if bad:
        failures.append(
            f"{len(bad)} seeded host(s) with role outside "
            f"{record_seed_spec['role']!r}",
        )
    return failures


def audit_seed_ring(payload: dict, record_seed_spec: dict) -> list[str]:
    """The seed_ring guard every conditioned cell audit starts with."""
    ring = payload.get("seed_ring")
    if not isinstance(ring, dict):
        return ["missing seed_ring block"]
    return audit_seed_echoes(ring, record_seed_spec)


def audit_observation_echoes(payload: dict, declared: dict) -> list[str]:
    """onset_recording + severity-eligibility echoes, when declared."""
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


# --- Propensity-family helpers -----------------------------------------
# Shared by the PROPENSITY-V1 clause canary and the PROPENSITY-CV-01 cv
# screen: both audit delivery.participation_propensity echoes plus the
# propensity_draw witnesses, score the same v11-lineage clause, and pair
# seeds against a baseline arm.

SHIPPED_PROPENSITY_MODE = "party"
SHIPPED_PROPENSITY_CV = 0.8
# Resolved-cv echo tolerance: cv is a float parameter, so audit by
# absolute difference, not equality.
CV_ECHO_TOL = 1e-9
# The frozen DP replay contract's seed geometry (no seed_patch).
DP_RECORD_SEED_SPEC = {
    "count": 1,
    "infection_age_days": 6.8,
    "onset_day": -1.0,
    "departure_day": 5.0,
    "role": "passenger",
}
# Symmetric recorded-onsets band around the 197 clause anchor, reported
# beside the clause and never selected on (v15 stage-2 convention).
MASS_NEAR_T1 = (T1_RECORDED / 2.0, T1_RECORDED * 2.0)


def declared_propensity_block(arm: dict) -> dict:
    """The arm's declared mode + cv (shipped defaults when unset)."""
    block = (arm.get("overrides") or {}).get("participation_propensity") or {}
    return {
        "propensity_mode": str(block.get("mode", SHIPPED_PROPENSITY_MODE)),
        "propensity_cv": float(block.get("cv", SHIPPED_PROPENSITY_CV)),
    }


def audit_propensity_echo(
    failures: list[str], payload: dict, delivery: dict, declared: dict,
) -> None:
    """delivery echo resolves mode (and cv when declared) + draw witnesses."""
    prop = delivery.get("participation_propensity")
    if not isinstance(prop, dict):
        failures.append(
            "delivery.participation_propensity missing — the arm key did "
            "not resolve (design defect)",
        )
        return
    want_mode = declared["propensity_mode"]
    if prop.get("mode") != want_mode:
        failures.append(
            f"participation_propensity.mode resolved {prop.get('mode')!r}, "
            f"declared {want_mode!r}",
        )
    want_cv = declared.get("propensity_cv")
    if want_mode != "off" and want_cv is not None:
        got_cv = prop.get("cv")
        try:
            cv_diff = abs(float(got_cv) - want_cv)
        except (TypeError, ValueError):
            cv_diff = float("inf")
        if cv_diff > CV_ECHO_TOL:
            failures.append(
                f"participation_propensity.cv resolved {got_cv!r}, "
                f"declared {want_cv!r}",
            )
    units = int((payload.get("propensity_draw") or {}).get("units_drawn", -1))
    if want_mode == "off":
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


def audit_fixed_delivery_echoes(
    failures: list[str], delivery: dict,
) -> None:
    """presentation_draw_mode once_per_course + hygiene_cycle hand mode."""
    for field, want in (
        ("presentation_draw_mode", "once_per_course"),
        ("hand_reservoir_mode", "hygiene_cycle"),
    ):
        if delivery.get(field) != want:
            failures.append(
                f"delivery.{field} {delivery.get(field)!r} != {want!r}",
            )


def audit_index_geometry(
    failures: list[str], payload: dict, record_seed_spec: dict,
) -> None:
    """Index onset −1.0 + day-0 shedding + float-tolerant seed_spec echo."""
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
    for key, want in record_seed_spec.items():
        got = spec.get(key)
        if got != want and not (
            isinstance(want, float)
            and isinstance(got, (int, float))
            and abs(float(got) - want) <= 1e-9
        ):
            failures.append(
                f"seed_spec.{key} is {spec.get(key)!r}, want {want!r}",
            )


def trajectory_clause(stats: dict[str, Any]) -> dict[str, Any]:
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


def mass_near_t1(takeoff: list[dict], _stats: dict) -> dict[str, Any]:
    """Share of takeoff seeds landing within [98.5, 394] of the anchor."""
    recs = [float(p["observables"]["recorded_onsets"]) for p in takeoff]
    if not recs:
        return {"mass_near_t1": None}
    lo, hi = MASS_NEAR_T1
    return {"mass_near_t1": sum(lo <= r <= hi for r in recs) / len(recs)}


def propensity_row_echo(takeoff: list[dict]) -> dict[str, Any]:
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


def propensity_row_stats(payloads: list[dict]) -> dict:
    """Takeoff-conditional stats + clause + propensity echoes per arm."""
    stats = standard_row_stats(payloads, extra_fields=mass_near_t1)
    stats["clause"] = trajectory_clause(stats)
    takeoff = [
        p for p in payloads
        if int(p["observables"]["recorded_onsets"]) >= TAKEOFF_MIN_ONSETS
    ]
    stats.update(propensity_row_echo(takeoff))
    clause = stats["clause"]
    verdict = "unscored" if not clause["scored"] else (
        "PASS" if clause["clause_ok"] else "FAIL"
    )
    stats["row_extra"] = (
        f"clause {verdict} "
        f"units {fmt3g(stats['propensity_units_drawn']['median'])}"
    )
    return stats


def payload_before_share(payload: dict) -> float | None:
    """before_share for one cell; None when nothing recorded."""
    rec = float(payload["observables"]["recorded_onsets"])
    if rec <= 0:
        return None
    return float(payload["observables"]["onsets_before_split_day"]) / rec


def seed_paired_deltas(row: list[dict], base: list[dict]) -> dict:
    """Seed-paired (row - base) delta bands on the scored legs.

    Both rows' takeoff cells pair; a seed where either row fizzled drops
    out (the fizzle margin itself is reported per row). Returns the
    pairing only — the caller adds its theta/arm/baseline keys.
    """
    base_by_seed = {
        int(p["cell"]["seed"]): p for p in base
        if int(p["observables"]["recorded_onsets"]) >= TAKEOFF_MIN_ONSETS
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
        if int(p["observables"]["recorded_onsets"]) < TAKEOFF_MIN_ONSETS:
            continue
        deltas["recorded_onsets"].append(
            float(p["observables"]["recorded_onsets"])
            - float(b["observables"]["recorded_onsets"])
        )
        row_share = payload_before_share(p)
        base_share = payload_before_share(b)
        if row_share is not None and base_share is not None:
            deltas["before_share"].append(row_share - base_share)
        if p.get("infections_total") is not None and (
            b.get("infections_total") is not None
        ):
            deltas["infections_total"].append(
                float(p["infections_total"]) - float(b["infections_total"])
            )
    return {
        "n_paired": len(deltas["recorded_onsets"]),
        **{f"delta_{k}": band_stats(v) for k, v in deltas.items()},
    }


def clause_row_triggers(
    theta: float, arm_id: str, stats: dict,
) -> dict | None:
    """Report-immediately rows: a clause pass on any arm."""
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


def design_readout_main(
    argv: list[str] | None,
    *,
    repo_root: str,
    declared_fn: Callable[[dict], dict],
    audit_cell: Callable[[dict, dict, float], list[str]],
    row_stats: Callable[[list[dict]], dict],
    report_key: str,
    row_triggers: Callable[[float, str, dict], dict | None],
    paired_rows_of: (
        Callable[
            [Any],
            Callable[[dict[tuple, list[dict]]], dict] | None,
        ]
        | None
    ) = None,
) -> int:
    """The shared main: design load -> enumerate_cells -> run_readout.

    ``paired_rows_of`` receives the loaded design and returns the
    ``paired_rows`` callable run_readout expects (None disables it) --
    a campaign needing the declared baseline arm binds it here rather
    than trusting payload load order.
    """
    design = load_design(
        resolve_design_arg(argv, repo_root), repo_root=repo_root,
    )
    return run_readout(
        argv,
        repo_root=repo_root,
        cells=enumerate_cells(design),
        declared_by_arm={
            arm["arm_id"]: declared_fn(arm) for arm in (design.arms or ())
        },
        audit_cell=audit_cell,
        row_stats=row_stats,
        report_key=report_key,
        row_triggers=row_triggers,
        paired_rows=(
            paired_rows_of(design) if paired_rows_of is not None else None
        ),
    )
