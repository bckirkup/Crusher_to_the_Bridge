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
from collections.abc import Callable
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
