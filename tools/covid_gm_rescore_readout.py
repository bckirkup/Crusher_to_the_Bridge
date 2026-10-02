"""COVID-GM-RESCORE-01 readout: pool the held-out Greg Mortimer re-score cells.

Reads the per-seed cell JSONs the Batch array wrote under
``campaign/covid_gm_rescore_v1/<sha>/cells/`` and pools them by (theta, arm)
into the numbers the design's freeze block declares: P(takeoff >= 10 recorded
onsets), day-20 campaign positives median/q05-q95 vs covid.H1's 128 of 217,
asymptomatic share vs covid.H2's 0.8125, recorded attack share vs covid.H3's
Willebrand IQR, takeoff-conditional positives (ignition vs size), onset timing,
and the seed-paired spike_decay - hygiene_cycle deltas (the held-out
counterpart of HAND-AB's DP read).

An audit failure is a cell whose resolved echoes do not match its arm's
declaration: ``delivery.hand_reservoir_mode`` must equal the arm's declared
mode, ``seed_ring.seed_spec`` must carry the declared seed (count == the
cell's imports axis, infection_age_days 0.0, role passenger), and
``aboard_total`` must be the declared 223.

``--pair-cells`` accepts a sibling design's synced cells directory (e.g. the
imports3 diagnostic dir passed while reading the scoring design, or the
scoring dir while reading imports3) and reports seed-paired deltas of this
design's anchor row against that dir's payloads at the same (theta, seed).

Usage:
    python3 tools/covid_gm_rescore_readout.py \
        --cells campaign_results/covid_gm_rescore_v1/cells \
        --design picard_framework/runs/covid_gm_rescore_v1_design.json \
        --out readout.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from picard_framework.covid_boarding_screen import (  # noqa: E402
    enumerate_cells,
    load_design,
)
from simulation_utils.paths import (  # noqa: E402
    resolve_repo_path,
    validated_open,
)
from tools.covid_screen_readout_common import (  # noqa: E402
    TAKEOFF_MIN_ONSETS,
    audit_all,
    audit_hand_mode,
    band_stats,
    declared_hand_mode,
    fmt3g,
    load_cell_payloads,
    quantile,
)

REPO_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))

# The shipped default arm (NORO-HAND-PRACTICE-01, PR #804): an arm whose
# overrides leave transmission.hand_reservoir_mode alone resolves this.
SHIPPED_HAND_MODE = "hygiene_cycle"
BASELINE_ARM = "hygiene_cycle"

# The hull's declared population; an aboard_total that is not this is a
# wrong-hull cell, a defect not a result.
GM_ABOARD = 223

# covid.H1 / covid.H2 / covid.H3 verbatim from data/observation/
# covid_fit_targets.json (held-out rows, grade A).
H1_POSITIVES = 128.0
H1_TESTED = 217.0
H1_SHARE = 0.5899
H2_SHARE = 0.8125
H2_TOL = 0.10
WILLEBRAND_IQR = (0.0003, 0.015)
WILLEBRAND_MEDIAN = 0.002

# Frozen in the design: a row "lands H1" when its campaign_positives median
# sits within 2x of 128 and its q05-q95 interval contains 128.
H1_MEDIAN_BAND = (64.0, 256.0)

# HAND-AB's DP read measured the repair suppressive-leaning: the held-out
# delta flags a reversal when spike_decay out-produces hygiene_cycle.
DELTA_REVERSAL_FIELDS = (
    "delta_recorded_onsets",
    "delta_campaign_positives",
    "delta_infections_total",
)


def _declared(arm: dict) -> dict:
    """The arm's declared hand-reservoir mode."""
    return declared_hand_mode(arm, SHIPPED_HAND_MODE)


def audit_cell(payload: dict, declared: dict, theta: float) -> list[str]:
    """Return the list of audit violations for one cell payload."""
    failures: list[str] = audit_hand_mode(payload, declared)
    cell = payload.get("cell") or {}
    ring = payload.get("seed_ring") or {}
    spec = ring.get("seed_spec") or {}
    if spec.get("count") != cell.get("imports"):
        failures.append(
            f"seed_spec.count {spec.get('count')!r} != cell imports "
            f"{cell.get('imports')!r}",
        )
    if abs(float(spec.get("infection_age_days", -1.0))) > 1e-9:
        failures.append(
            f"seed_spec.infection_age_days {spec.get('infection_age_days')!r} "
            "!= declared 0.0",
        )
    if spec.get("role") != "passenger":
        failures.append(
            f"seed_spec.role {spec.get('role')!r} != declared 'passenger'",
        )
    if "onset_day" in spec or "departure_day" in spec:
        failures.append(
            "seed_spec carries onset_day/departure_day -- GM's record "
            "declares neither",
        )
    if ring.get("seeded_count") != cell.get("imports"):
        failures.append(
            f"seeded_count {ring.get('seeded_count')!r} != imports "
            f"{cell.get('imports')!r}",
        )
    if int(payload.get("aboard_total") or 0) != GM_ABOARD:
        failures.append(
            f"aboard_total {payload.get('aboard_total')!r} != declared "
            f"{GM_ABOARD}",
        )
    return failures


def _obs(payload: dict, key: str) -> float:
    return float(payload["observables"][key])


def _onset_curve_median_day(payload: dict) -> float | None:
    """The day carrying half the cell's recorded onsets, or None."""
    total = 0
    for _day, roles in (payload.get("onset_curve") or {}).items():
        total += int(roles.get("passenger", 0)) + int(roles.get("crew", 0))
    if total <= 0:
        return None
    running = 0
    for day, roles in sorted(
        (payload.get("onset_curve") or {}).items(), key=lambda kv: int(kv[0])
    ):
        running += int(roles.get("passenger", 0)) + int(roles.get("crew", 0))
        if running * 2 >= total:
            return float(day)
    return None


def _row_stats(payloads: list[dict]) -> dict:
    """Per-(theta, arm) row stats against the frozen held-out anchors."""
    n = len(payloads)
    takeoff = [
        p for p in payloads
        if _obs(p, "recorded_onsets") >= TAKEOFF_MIN_ONSETS
    ]
    p_takeoff = len(takeoff) / n if n else None
    rec = [_obs(p, "recorded_onsets") for p in payloads]
    positives = [_obs(p, "campaign_positives") for p in payloads]
    specimens = [_obs(p, "campaign_specimens") for p in payloads]
    pos_share = [
        _obs(p, "campaign_positives") / _obs(p, "campaign_specimens")
        for p in payloads if _obs(p, "campaign_specimens") > 0
    ]
    asym = [
        _obs(p, "campaign_asymptomatic_positives")
        / _obs(p, "campaign_positives")
        for p in payloads if _obs(p, "campaign_positives") > 0
    ]
    aboard = [
        float(p.get("aboard_total") or 0.0) for p in payloads
    ]
    attack_rec = [
        r / a for r, a in zip(rec, aboard) if a > 0
    ]
    t_pos = [_obs(p, "campaign_positives") for p in takeoff]
    first_onset = [
        float(p["first_onset_day"]) for p in payloads
        if p.get("first_onset_day") is not None
    ]
    median_onset = [
        _onset_curve_median_day(p) for p in payloads
    ]
    median_onset = [v for v in median_onset if v is not None]
    pooled_curve: Counter[int] = Counter()
    for p in payloads:
        for day, roles in (p.get("onset_curve") or {}).items():
            pooled_curve[int(day)] += (
                int(roles.get("passenger", 0)) + int(roles.get("crew", 0))
            )

    pos_stats = band_stats(positives)
    med_pos = pos_stats["median"]
    h1_lands = (
        med_pos is not None
        and H1_MEDIAN_BAND[0] <= med_pos <= H1_MEDIAN_BAND[1]
        and pos_stats["q05"] is not None
        and pos_stats["q95"] is not None
        and pos_stats["q05"] <= H1_POSITIVES <= pos_stats["q95"]
    )
    asym_med = quantile(asym, 0.5)
    h2_hit = asym_med is not None and abs(asym_med - H2_SHARE) <= H2_TOL
    attack_med = quantile(attack_rec, 0.5)
    stats = {
        "n": n,
        "takeoff_n": len(takeoff),
        "p_takeoff": p_takeoff,
        "recorded_onsets": band_stats(rec),
        "takeoff_recorded_onsets": band_stats(
            [_obs(p, "recorded_onsets") for p in takeoff]
        ),
        "infections_total": band_stats(
            [float(p["infections_total"]) for p in payloads
             if p.get("infections_total") is not None]
        ),
        "campaign_specimens": band_stats(specimens),
        "campaign_positives": pos_stats,
        "campaign_positive_share": band_stats(pos_share),
        "asymptomatic_share": {
            "median": asym_med,
            "q05": quantile(asym, 0.05),
            "q95": quantile(asym, 0.95),
            "n_defined": len(asym),
        },
        "takeoff_conditional_campaign_positives": {
            "n": len(t_pos),
            **band_stats(t_pos),
        },
        "attack_share_recorded": {
            "median": attack_med,
            "q05": quantile(attack_rec, 0.05),
            "q95": quantile(attack_rec, 0.95),
            "willebrand_iqr": list(WILLEBRAND_IQR),
            "willebrand_median": WILLEBRAND_MEDIAN,
        },
        "first_onset_day": band_stats(first_onset),
        "median_onset_day": band_stats(median_onset),
        "onset_curve_pooled": {
            str(day): count for day, count in sorted(pooled_curve.items())
        },
        "h1_lands": bool(h1_lands),
        "h2_hit": bool(h2_hit),
    }
    stats["row_extra"] = (
        f"pos med {fmt3g(med_pos)} "
        f"[{fmt3g(pos_stats['q05'])},{fmt3g(pos_stats['q95'])}] "
        f"asym {fmt3g(asym_med)}"
    )
    return stats


def _row_triggers(theta: float, arm_id: str, stats: dict) -> dict | None:
    """The prompt's report-immediately rows, per (theta, arm)."""
    kinds: list[str] = []
    if stats["n"] >= 20 and (stats["p_takeoff"] or 0.0) < 0.05:
        kinds.append("DEAD-REGIME")
    if stats["h1_lands"]:
        kinds.append("H1-LANDS")
    if not kinds:
        return None
    return {
        "theta": theta,
        "arm_id": arm_id,
        "triggers": kinds,
        "p_takeoff": stats["p_takeoff"],
        "campaign_positives": stats["campaign_positives"],
        "asymptomatic_share": stats["asymptomatic_share"],
    }


def _cell_seed(payload: dict) -> int:
    return int((payload.get("cell") or {}).get("seed"))


def _seed_paired_delta(
    base: dict[int, dict], other: dict[int, dict],
) -> dict[str, Any]:
    """Seed-paired deltas of one arm's payloads against a baseline map."""
    deltas: dict[str, list[float]] = {k: [] for k in (
        "recorded_onsets", "campaign_positives", "infections_total",
    )}
    flips = 0
    for seed, b in base.items():
        a = other.get(seed)
        if a is None:
            continue
        b_rec = _obs(b, "recorded_onsets")
        a_rec = _obs(a, "recorded_onsets")
        deltas["recorded_onsets"].append(b_rec - a_rec)
        deltas["campaign_positives"].append(
            _obs(b, "campaign_positives") - _obs(a, "campaign_positives")
        )
        b_inf = b.get("infections_total")
        a_inf = a.get("infections_total")
        if b_inf is not None and a_inf is not None:
            deltas["infections_total"].append(float(b_inf) - float(a_inf))
        flips += int(
            (b_rec >= TAKEOFF_MIN_ONSETS) != (a_rec >= TAKEOFF_MIN_ONSETS)
        )
    out: dict[str, Any] = {
        "paired_seeds": len(deltas["recorded_onsets"]),
        "takeoff_class_flips": flips,
    }
    for key, vals in deltas.items():
        out[f"delta_{key}"] = band_stats(vals)
    return out


def _paired_rows(
    rows: dict[tuple, list[dict]],
    external: dict[tuple, list[dict]] | None,
) -> dict[str, Any]:
    """Seed-paired deltas: spike_decay vs hygiene_cycle per theta.

    The baseline arm is pinned (hygiene_cycle), never read off payload load
    order. ``external`` pairs this design's baseline rows against a sibling
    dir's payloads at the same (theta, seed) -- the imports3 diagnostic
    vs the scoring anchor, either direction.
    """
    out: dict[str, Any] = {}
    by_theta: dict[float, dict[str, dict[int, dict]]] = {}
    for (theta, arm_id), payloads in rows.items():
        seeded = {_cell_seed(p): p for p in payloads}
        by_theta.setdefault(float(theta), {})[str(arm_id)] = seeded
    for theta, arms in sorted(by_theta.items()):
        base = arms.get(BASELINE_ARM, {})
        for arm_id, cells in arms.items():
            if arm_id == BASELINE_ARM:
                continue
            key = f"theta={theta:.4g}|{BASELINE_ARM}_minus_{arm_id}"
            out[key] = _seed_paired_delta(base, cells)
    if external:
        out.update(_external_deltas(external, by_theta))
    return out


def _external_deltas(
    external: dict[tuple, list[dict]],
    by_theta: dict[float, dict[str, dict[int, dict]]],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for (theta, arm_id), payloads in external.items():
        seeded = {_cell_seed(p): p for p in payloads}
        for own_theta, arms in by_theta.items():
            if own_theta != float(theta):
                continue
            base = arms.get(BASELINE_ARM, {})
            key = (
                f"theta={theta:.4g}|{BASELINE_ARM}_minus_external:"
                f"{arm_id}"
            )
            out[key] = _seed_paired_delta(base, seeded)
    return out


def _bucket_external(
    payloads: dict[str, dict], pair_arm: str | None,
) -> dict[tuple, list[dict]]:
    """Group foreign cells by (theta, arm) for seed pairing."""
    rows: dict[tuple, list[dict]] = {}
    for payload in payloads.values():
        cell = payload.get("cell") or {}
        arm_id = cell.get("arm_id") if pair_arm is None else pair_arm
        rows.setdefault(
            (float(cell.get("theta")), arm_id), [],
        ).append(payload)
    return rows


def _delta_reversal_trigger(paired: dict[str, Any]) -> dict | None:
    """Flag when the held-out hand-arm delta reverses HAND-AB's DP sign.

    HAND-AB measured the repair suppressive-leaning: hygiene_cycle sits
    below spike_decay, so a positive median on every shared delta field
    is the declared report-immediately reversal.
    """
    for label, delta in paired.items():
        if not label.startswith("theta=") or "minus_external" in label:
            continue
        medians = [
            (delta.get(field) or {}).get("median")
            for field in DELTA_REVERSAL_FIELDS
        ]
        if (
            medians
            and all(m is not None for m in medians)
            and all(float(m) > 0.0 for m in medians)
        ):
            return {"paired_row": label, "triggers": ["DELTA-REVERSAL"]}
    return None


def _build_report(
    design: Any,
    cells: list[Any],
    payloads: dict[str, dict],
    external: dict[tuple, list[dict]] | None,
) -> dict[str, Any]:
    """Audit cells and pool them into the frozen per-row stats."""
    declared_by_arm = {
        arm["arm_id"]: _declared(arm) for arm in (design.arms or ())
    }
    audit_failures, rows = audit_all(
        payloads, cells, declared_by_arm, audit_cell,
    )
    report: dict[str, Any] = {
        "design_id": design.design_id,
        "cells_found": len(payloads),
        "cells_expected": len(cells),
        "audit_failures": audit_failures,
        "anchors": {
            "covid.H1": {"positives": H1_POSITIVES, "tested": H1_TESTED},
            "covid.H2": {"asymptomatic_share": H2_SHARE, "tol": H2_TOL},
            "covid.H3": {
                "median": WILLEBRAND_MEDIAN, "iqr": WILLEBRAND_IQR,
            },
        },
        "rows": {},
        "triggered_rows": [],
    }
    for (theta, arm_id), row in sorted(rows.items()):
        stats = _row_stats(row)
        report["rows"][f"theta={theta:.4g}|arm={arm_id}"] = stats
        trigger = _row_triggers(theta, arm_id, stats)
        if trigger:
            report["triggered_rows"].append(trigger)
    report["paired_rows"] = _paired_rows(rows, external)
    reversal = _delta_reversal_trigger(report["paired_rows"])
    if reversal:
        report["triggered_rows"].append(reversal)
    return report


def _print_report(report: dict[str, Any]) -> None:
    """The console summary: counts, one line per row, triggered rows."""
    print(
        f"{report['cells_found']}/{report['cells_expected']} cells; "
        f"{len(report['audit_failures'])} audit failures",
    )
    for label, stats in report["rows"].items():
        print(
            f"  {label}: takeoff {stats['takeoff_n']}/{stats['n']} "
            f"P={fmt3g(stats['p_takeoff'])} "
            f"pos med {fmt3g(stats['campaign_positives']['median'])} "
            f"[{fmt3g(stats['campaign_positives']['q05'])},"
            f"{fmt3g(stats['campaign_positives']['q95'])}] "
            f"asym {fmt3g(stats['asymptomatic_share']['median'])} "
            f"{'H1-LANDS' if stats['h1_lands'] else ''}"
        )
    if report["triggered_rows"]:
        print(
            "TRIGGERED_ROWS:",
            json.dumps(report["triggered_rows"], indent=1),
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cells", required=True)
    parser.add_argument("--design", required=True)
    parser.add_argument("--out", default=None)
    parser.add_argument("--pair-cells", default=None)
    parser.add_argument("--pair-arm", default=None)
    parser.add_argument(
        "--allow-partial", action="store_true",
        help="read whatever cells exist (canary/incomplete arrays)",
    )
    args = parser.parse_args(argv)

    design = load_design(
        resolve_repo_path(REPO_ROOT, args.design), repo_root=REPO_ROOT,
    )
    cells = enumerate_cells(design)
    cells_dir = resolve_repo_path(REPO_ROOT, args.cells)
    payloads = load_cell_payloads(cells_dir)
    if not args.allow_partial and len(payloads) < len(cells):
        print(
            f"{len(payloads)} of {len(cells)} cells present; "
            "pass --allow-partial for a partial read",
            file=sys.stderr,
        )
        return 2

    external = None
    if args.pair_cells:
        pair_dir = resolve_repo_path(REPO_ROOT, args.pair_cells)
        external = _bucket_external(
            load_cell_payloads(pair_dir), args.pair_arm,
        )
    report = _build_report(design, cells, payloads, external)
    if args.out:
        out_path = resolve_repo_path(REPO_ROOT, args.out)
        with validated_open(
            out_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8",
        ) as fh:
            json.dump(report, fh, indent=2, sort_keys=True)
    _print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
