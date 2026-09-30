"""Shared skeleton for conditioned-array screen readouts.

The covid boarding-screen readouts (SEED-GEOM-V1, HEAT-V1 lineage) share
one shape: audit each cell's payload echoes against the arm's declared
constants, bucket by (theta, arm), and score takeoff-conditional rows
against the two anchors. This module holds the mechanics each design's
tool reuses with its own declared/audit/row semantics -- nothing here
knows which axis a design sweeps.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
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

TAKEOFF_MIN_ONSETS = 10
T1_RECORDED = 197.0
T1_BEFORE_SHARE = 0.173
BEFORE_SHARE_TOL = 0.10
H5_BAND = (712.0, 960.0)
MIN_TAKEOFF_SEEDS = 5


def q(values: list[float], p: float) -> float | None:
    if not values:
        return None
    srt = sorted(values)
    i = min(len(srt) - 1, max(0, int(round(p * (len(srt) - 1)))))
    return float(srt[i])


def med(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.3g}"


def takeoff_split(
    payloads: list[dict], min_onsets: int = TAKEOFF_MIN_ONSETS,
) -> dict[str, Any]:
    """Split a row's payloads into the takeoff-conditional primitives
    every screen's row stats consume."""
    obs = [p["observables"] for p in payloads]
    takeoff = [
        p for p, o in zip(payloads, obs)
        if int(o["recorded_onsets"]) >= min_onsets
    ]
    return {
        "obs": obs,
        "takeoff": takeoff,
        "rec": [float(o["recorded_onsets"]) for o in obs],
        "shares": [
            float(o["onsets_before_split_day"])
            / float(o["recorded_onsets"])
            for o in obs
            if int(o["recorded_onsets"]) > 0
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


def scored_row(split: dict[str, Any]) -> dict[str, Any]:
    """The anchor-scored fields every screen row carries: takeoff-conditional
    medians/quantiles of recorded_onsets, infections_total and
    before_share, plus the both-legs verdict flags."""
    t_rec = split["t_rec"]
    t_inf = split["t_inf"]
    t_share = split["t_share"]
    med_inf = q(t_inf, 0.5)
    med_share = q(t_share, 0.5)
    enough = len(split["takeoff"]) >= MIN_TAKEOFF_SEEDS
    in_band = (
        med_inf is not None and H5_BAND[0] <= med_inf <= H5_BAND[1]
    )
    timing_hit = (
        med_share is not None
        and abs(med_share - T1_BEFORE_SHARE) <= BEFORE_SHARE_TOL
    )
    return {
        "n": len(split["obs"]),
        "takeoff_n": len(split["takeoff"]),
        "recorded_onsets": {
            "median": q(split["rec"], 0.5), "q05": q(split["rec"], 0.05),
            "q95": q(split["rec"], 0.95),
        },
        "before_share": {"median": q(split["shares"], 0.5)},
        "takeoff_recorded_onsets": {
            "median": q(t_rec, 0.5), "q05": q(t_rec, 0.05),
            "q95": q(t_rec, 0.95),
        },
        "takeoff_infections_total": {
            "median": med_inf, "q05": q(t_inf, 0.05),
            "q95": q(t_inf, 0.95),
        },
        "takeoff_before_share": {
            "median": med_share, "q05": q(t_share, 0.05),
            "q95": q(t_share, 0.95),
        },
        "truth_leg_in_band": bool(in_band and enough),
        "timing_leg_in_band": bool(timing_hit and enough),
        "both_legs": bool(in_band and timing_hit and enough),
    }


def load_payloads(cells_dir: str) -> dict[str, dict]:
    """Read every cell JSON under *cells_dir* (contained to the dir)."""
    payloads: dict[str, dict] = {}
    for name in sorted(os.listdir(cells_dir)):
        if not name.endswith(".json"):
            continue
        path = resolve_child_path(cells_dir, name)
        with validated_open(
            path, "r", allowed_roots=(cells_dir,), encoding="utf-8",
        ) as fh:
            payloads[name] = json.load(fh)
    return payloads


def audit_all(
    payloads: dict[str, dict],
    cells: list,
    declared_by_arm: dict[str, dict],
    audit_fn: Callable[[dict, dict], list[str]],
) -> tuple[dict[str, list[str]], dict[tuple, list[dict]]]:
    """Audit each payload against its declared arm and bucket the cells
    by (theta, arm)."""
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
        failures = audit_fn(payload, declared) if declared else [
            f"unknown arm {cell.get('arm_id')}",
        ]
        if failures:
            audit_failures[name] = failures
        rows.setdefault((key[0], key[1]), []).append(payload)
    return audit_failures, rows


def run_readout(
    argv: list[str] | None,
    *,
    root: str,
    description: str | None,
    declared_fn: Callable[[dict], dict],
    audit_fn: Callable[[dict, dict], list[str]],
    row_stats_fn: Callable[[list[dict]], dict],
    row_line_fn: Callable[[dict], str],
    collect_fn: Callable[[dict, float, str, dict], None],
) -> dict | None:
    """The shared CLI: --cells/--design/--out/--allow-partial, audit +
    row stats + report write/print. ``collect_fn`` appends a design's
    own report extras (in-band landings, extended triggers) per row.
    Returns the assembled report, or None when a non-partial read found
    missing cells (exit code 2 path)."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--cells", required=True)
    parser.add_argument("--design", required=True)
    parser.add_argument("--out", default=None)
    parser.add_argument(
        "--allow-partial", action="store_true",
        help="read whatever cells exist (canary/incomplete arrays)",
    )
    args = parser.parse_args(argv)

    cells_dir = resolve_repo_path(root, args.cells)
    design_path = resolve_repo_path(root, args.design)
    design = load_design(design_path, repo_root=root)
    cells = enumerate_cells(design)
    declared_by_arm = {
        arm["arm_id"]: declared_fn(arm) for arm in (design.arms or ())
    }

    payloads = load_payloads(cells_dir)
    if not args.allow_partial and len(payloads) < len(cells):
        print(
            f"{len(payloads)} of {len(cells)} cells present; "
            "pass --allow-partial for a partial read",
            file=sys.stderr,
        )
        return None

    audit_failures, rows = audit_all(
        payloads, cells, declared_by_arm, audit_fn,
    )

    report: dict[str, Any] = {
        "cells_found": len(payloads),
        "cells_expected": len(cells),
        "audit_failures": audit_failures,
        "rows": {},
    }
    for (theta, arm_id), row in sorted(rows.items()):
        stats = row_stats_fn(row)
        label = f"theta={theta:.4g}|arm={arm_id}"
        report["rows"][label] = stats
        collect_fn(report, theta, arm_id, stats)

    if args.out:
        out_path = resolve_repo_path(root, args.out)
        with validated_open(
            out_path, "w", allowed_roots=(root,), encoding="utf-8",
        ) as fh:
            json.dump(report, fh, indent=2, sort_keys=True)

    print(
        f"{report['cells_found']}/{report['cells_expected']} cells; "
        f"{len(audit_failures)} audit failures",
    )
    for label, stats in report["rows"].items():
        print(f"  {label}: {row_line_fn(stats)}")
    return report


def print_extras(report: dict, keys: list[str]) -> None:
    """Print the non-empty report extras a design collected."""
    for key in keys:
        if report.get(key):
            print(key.upper() + ":", json.dumps(report[key], indent=1))
