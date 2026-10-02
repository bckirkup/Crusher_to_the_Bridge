#!/usr/bin/env python3
"""COVID-THETA-V15 stage-2 readout — the declared DP replay clause under
once_per_course (PRESENT-SHARE-01's shipped default).

The submitted set is the parent design's frozen theta_points rule applied
to the stage-1 surface; this tool audits that the cells under --cells are
exactly that rule's output (no row outside the rule, no ruled-in row
missing), then scores each landed row:

- per-cell audit: resolved delivery echoes (presentation_draw_mode ==
  once_per_course, hand_reservoir_mode == hygiene_cycle), the index
  geometry invariant (index_onset_day == -1.0 and index_shedding_at_day0),
  cell key on the declared stage-2 lattice, scoreable recorded_onsets;
- per-row clause: takeoff-conditional (recorded_onsets >= 10) q05-q95 of
  recorded_onsets contains 197 AND takeoff median before_share within
  0.10 of 0.173 — scored only when the row has >= 5 takeoff seeds
  (verbatim from the v11 clause);
- pairing: every submitted row pairs seed-for-seed against the
  covid_theta_screen_v13_stage2 cells (--parent-cells): per-seed deltas on
  recorded_onsets and takeoff-class flips.

Row roles: 'anchor' for the Theta 1e9 QUAR-ATTR-V2 row (always submitted,
never a candidate), 'selected' for stage-1-admissible lattice Thetas,
'flank' for rule-picked non-admissible neighbours, 'crossing' /
'crossing_neighbour' under the empty-but-crossed rule (b).

Usage:
    python3 tools/covid_theta_v15_stage2_readout.py \
        --cells campaign_results/covid_theta_screen_v15_stage2/cells \
        --design picard_framework/runs/covid_theta_screen_v15_stage2_design.json \
        --stage1-report telemetry_buffer/covid_theta_v15_readout.json \
        --parent-cells campaign_results/covid_theta_screen_v13_stage2/cells \
        --out telemetry_buffer/covid_theta_v15_stage2_readout.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

REPO_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from picard_framework.covid_boarding_screen import (  # noqa: E402
    enumerate_cells,
    load_design,
)
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_repo_path,
    validated_open,
)
from tools.covid_screen_readout_common import (  # noqa: E402
    BEFORE_SHARE_TOL,
    MIN_TAKEOFF_SEEDS,
    T1_BEFORE_SHARE,
    T1_RECORDED,
    load_cell_payloads,
    standard_row_stats,
)
from tools.covid_theta_v14_readout import (  # noqa: E402
    _pair_row_stats,
    _pairs,
    _row_side,
)

# The v15 audit contract verbatim from the design's audit_invariants block.
AUDIT_ECHOES = {
    "presentation_draw_mode": "once_per_course",
    "hand_reservoir_mode": "hygiene_cycle",
}
# Symmetric recorded-onsets band around the 197 clause anchor.
MASS_NEAR_TARGET = (T1_RECORDED / 2.0, T1_RECORDED * 2.0)


def _audit_cell(payload: dict[str, Any], design_id: str) -> list[str]:
    """One stage-2 cell against the replay contract."""
    failures: list[str] = []
    delivery = payload.get("delivery") or {}
    for field, want in AUDIT_ECHOES.items():
        got = delivery.get(field)
        if got != want:
            failures.append(f"delivery.{field} {got!r} != {want!r}")
    cell = payload.get("cell") or {}
    if cell.get("arm_id") != "once_per_course":
        failures.append(f"cell.arm_id {cell.get('arm_id')!r} != 'once_per_course'")
    if payload.get("design_id") != design_id:
        failures.append(
            f"design_id {payload.get('design_id')!r} != {design_id!r}",
        )
    if float(payload.get("index_onset_day") or 0.0) != -1.0:
        failures.append(
            f"index_onset_day {payload.get('index_onset_day')!r} != -1.0",
        )
    if not payload.get("index_shedding_at_day0"):
        failures.append("index_shedding_at_day0 not set")
    if (payload.get("observables") or {}).get("recorded_onsets") is None:
        failures.append("observables.recorded_onsets missing")
    return failures


def _row_roles(
    stage1: dict[str, Any],
    lattice: list[float],
    anchor: float,
) -> tuple[dict[float, str], list[dict[str, str]]]:
    """The parent's frozen theta_points rule applied to the stage-1 surface.

    Returns theta -> role plus report triggers. Rule (a): the admissible
    rows plus the nearest non-admissible lattice neighbour on each side.
    Rule (b) (admissible empty but interior medians cross): the straddling
    pair plus the adjacent interior rows. Rule (c) (illusory): no rows
    beyond the anchor, which always runs under rule (d).
    """
    roles: dict[float, str] = {anchor: "anchor"}
    triggers: list[dict[str, str]] = []
    admissible = sorted(stage1.get("admissible_thetas") or [])
    if admissible:
        roles.update(dict.fromkeys(admissible, "selected"))
        below = [t for t in lattice if t < min(admissible)]
        above = [t for t in lattice if t > max(admissible)]
        if below:
            roles[max(below)] = "flank"
        if above:
            roles[min(above)] = "flank"
        return roles, triggers
    interior = list(lattice[1:-1])
    interior_set = set(interior)
    surface = stage1.get("surface") or []
    sides = {
        e.get("theta"): _row_side(e) for e in surface
        if e.get("theta") in interior_set
    }
    ordered = [sides.get(t) for t in interior]
    crossings = [
        i for i in range(len(ordered) - 1)
        if ordered[i] == "floor" and ordered[i + 1] == "ceiling"
    ]
    if not crossings:
        return roles, triggers  # illusory: anchor still runs (rule d)
    if len(crossings) > 1:
        triggers.append({
            "trigger": "crossing_ambiguous",
            "detail": f"{len(crossings)} floor->ceiling transitions; "
                      "rule (b) submitted the first",
        })
    i = crossings[0]
    roles[interior[i]] = "crossing"
    roles[interior[i + 1]] = "crossing"
    if i - 1 >= 0:
        roles[interior[i - 1]] = "crossing_neighbour"
    if i + 2 < len(interior):
        roles[interior[i + 2]] = "crossing_neighbour"
    return roles, triggers


def _mass_in_band(takeoff: list[dict], _stats: dict) -> dict[str, Any]:
    """Share of takeoff seeds landing within [98.5, 394] of the anchor."""
    recs = [float(p["observables"]["recorded_onsets"]) for p in takeoff]
    if not recs:
        return {"mass_near_t1": None}
    lo, hi = MASS_NEAR_TARGET
    return {"mass_near_t1": sum(lo <= r <= hi for r in recs) / len(recs)}


def _clause(stats: dict[str, Any]) -> dict[str, Any]:
    """The verbatim v11 clause legs on one row's takeoff-conditional stats."""
    rec = stats["takeoff_recorded_onsets"]
    share = stats["takeoff_before_share"]
    scored = stats["takeoff_n"] >= MIN_TAKEOFF_SEEDS
    count_leg = bool(
        scored and rec["q05"] is not None and rec["q95"] is not None
        and rec["q05"] <= T1_RECORDED <= rec["q95"],
    )
    timing_leg = bool(
        scored and share["median"] is not None
        and abs(share["median"] - T1_BEFORE_SHARE) <= BEFORE_SHARE_TOL,
    )
    return {
        "scored": scored,
        "count_leg": count_leg,
        "timing_leg": timing_leg,
        "clause_ok": count_leg and timing_leg,
    }


def _row_summaries(
    rows: dict[float, list[dict]],
    roles: dict[float, str],
    seeds_per_row: int,
) -> dict[float, dict[str, Any]]:
    """Per-row takeoff stats, clause verdict, role, and completeness."""
    out: dict[float, dict[str, Any]] = {}
    for theta, payloads in sorted(rows.items()):
        stats = standard_row_stats(payloads, extra_fields=_mass_in_band)
        out[theta] = {
            "role": roles.get(theta, "unruled"),
            "n_cells": len(payloads),
            "complete": len(payloads) == seeds_per_row,
            "takeoff_n": stats["takeoff_n"],
            "takeoff_recorded_onsets": stats["takeoff_recorded_onsets"],
            "takeoff_before_share": stats["takeoff_before_share"],
            "takeoff_infections_total": stats["takeoff_infections_total"],
            "mass_near_t1": stats["mass_near_t1"],
            "clause": _clause(stats),
        }
    return out


def _print_rows(summaries: dict[float, dict[str, Any]]) -> None:
    for theta, s in summaries.items():
        rec, share, clause = (
            s["takeoff_recorded_onsets"],
            s["takeoff_before_share"],
            s["clause"],
        )
        band = (
            f"{rec['q05']:g}-{rec['q95']:g}"
            if rec["q05"] is not None else "unscored"
        )
        med = share["median"]
        if not clause["scored"]:
            verdict = "unscored"
        else:
            verdict = "PASS" if clause["clause_ok"] else "FAIL"
        print(
            f"theta {theta:g} [{s['role']}] takeoff {s['takeoff_n']} "
            f"rec band {band} share {med if med is not None else float('nan'):.3f} "
            f"clause {verdict}",
        )


def main(argv: list[str] | None = None) -> int:
    """Read out the v15 stage-2 cells against the frozen rule."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells", required=True)
    parser.add_argument("--design", required=True)
    parser.add_argument("--stage1-report", required=True)
    parser.add_argument("--parent-cells", default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    design = load_design(
        resolve_repo_path(REPO_ROOT, args.design), repo_root=REPO_ROOT,
    )
    with validated_open(
        resolve_repo_path(REPO_ROOT, args.stage1_report),
        allowed_roots=(REPO_ROOT,), encoding="utf-8",
    ) as fh:
        stage1 = json.load(fh)

    thetas = sorted(design.thetas)
    anchor, lattice = thetas[0], thetas[1:]
    roles, triggers = _row_roles(stage1, lattice, anchor)
    payloads = load_cell_payloads(args.cells)

    lattice_keys = {(c.theta, c.arm_id, c.seed) for c in enumerate_cells(design)}
    audit_failures: dict[str, list[str]] = {}
    rows: dict[float, list[dict]] = {}
    for name, payload in sorted(payloads.items()):
        cell = payload.get("cell") or {}
        key = (
            float(cell.get("theta") or -1.0),
            cell.get("arm_id"),
            int(cell.get("seed") or -1),
        )
        failures = _audit_cell(payload, design.design_id)
        if key not in lattice_keys:
            failures.append("cell key not in the declared lattice")
        if failures:
            audit_failures[name] = failures
        rows.setdefault(key[0], []).append(payload)

    submitted = set(rows)
    ruled = set(roles)
    missing = sorted(ruled - submitted)
    extra = sorted(submitted - ruled)
    if missing:
        triggers.append({
            "trigger": "rule_row_missing",
            "detail": f"ruled-in rows without cells: {missing}",
        })
    if extra:
        triggers.append({
            "trigger": "unruled_row_submitted",
            "detail": f"cells present outside the frozen rule: {extra}",
        })

    summaries = _row_summaries(rows, roles, design.seeds)
    pair_stats = None
    if args.parent_cells:
        parents = load_cell_payloads(args.parent_cells)
        pair_stats = _pair_row_stats(_pairs(payloads, parents))

    report = {
        "cells_found": len(payloads),
        "rule_rows": {f"{t:g}": r for t, r in sorted(roles.items())},
        "rule_missing_rows": missing,
        "rule_extra_rows": extra,
        "audit_failures": audit_failures,
        "rows": {f"{t:g}": s for t, s in summaries.items()},
        "paired_vs_v13_stage2": pair_stats,
        "report_immediately": triggers,
    }
    if args.out:
        out_path = resolve_repo_path(REPO_ROOT, args.out)
        prepare_output_directory(
            os.path.dirname(out_path) or REPO_ROOT,
            allowed_roots=(REPO_ROOT,),
        )
        with validated_open(
            out_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8",
        ) as fh:
            json.dump(report, fh, indent=2, default=str)
        print(f"readout written to {out_path}")
    _print_rows(summaries)
    print(
        f"{report['cells_found']} cells; {len(audit_failures)} audit "
        f"failures; {len(triggers)} report-immediately triggers",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
