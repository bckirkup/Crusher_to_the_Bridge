#!/usr/bin/env python3
"""Reports-per-voyage vs the VSP posting threshold, per cell.

The outbreak-anchor readout scores posting (A9: reported attack rate >= 3%
on either channel) but does not show how the underlying report counts sit
against the absolute thresholds a posting implies (~3% of complement on
each channel). This tool reuses that readout's collection layer
(``outbreak_anchor_readout.collect``: ranged-GET ``summary.json`` reads
from campaign-layout run zips under ``<root>/<tier>/<run_id>.zip``) and
emits, per cell:

- passenger/crew complements and the implied report thresholds
  (``ceil(3% * complement)`` per channel);
- the distribution of reported passenger/crew counts (median / p90 /
  max), over all runs and takeoff voyages only;
- per-channel threshold crossings and the posted count, so the gap
  between "reports/voyage" and "posts/voyage" is explicit.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_REPO_ROOT / "tools" / "noro_diag") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "tools" / "noro_diag"))

from telemetry_buffer.observation_model.score_anchors import (  # noqa: E402
    A9_POSTING_THRESHOLD,
)
from tools.diag.readout_common import emit_report_outputs  # noqa: E402
from tools.noro_diag.outbreak_anchor_readout import (  # noqa: E402
    _cell_label,
    _posted,
    collect,
)


def _report_row(run: dict[str, Any]) -> dict[str, Any]:
    """Project one collected run onto report counts + posting flags.

    Report counts are recovered as ``round(reported_AR * complement)``:
    the scorer stores the AR as ``count / complement``, so the product
    returns the integer count without a second zip read.
    """
    anchor = run["anchor_row"]
    pax_comp = int(anchor["passenger_complement"])
    crew_comp = int(anchor["crew_complement"])
    rep_pax = round(
        float(anchor["reported_case_attack_rate_passenger"]) * pax_comp
    )
    rep_crew = round(
        float(anchor["reported_case_attack_rate_crew"]) * crew_comp
    )
    return {
        "run_id": run["run_id"],
        "seed": run["seed"],
        "pax_comp": pax_comp,
        "crew_comp": crew_comp,
        "rep_pax": rep_pax,
        "rep_crew": rep_crew,
        "takeoff": bool(anchor["took_off"]),
        "posted": _posted(anchor),
    }


def _q(values: list[float], frac: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    pos = frac * (len(ordered) - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def _dist(values: list[float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "median": _q(values, 0.5),
        "p90": _q(values, 0.9),
        "max": max(values) if values else None,
    }


def summarise_cell(rows: list[dict]) -> dict[str, Any]:
    pax_comp = max((r["pax_comp"] for r in rows), default=0)
    crew_comp = max((r["crew_comp"] for r in rows), default=0)
    thr_pax = math.ceil(A9_POSTING_THRESHOLD * pax_comp)
    thr_crew = math.ceil(A9_POSTING_THRESHOLD * crew_comp)
    tk = [r for r in rows if r["takeoff"]]
    return {
        "n": len(rows),
        "n_takeoff": len(tk),
        "pax_comp": pax_comp,
        "crew_comp": crew_comp,
        "thr_pax": thr_pax,
        "thr_crew": thr_crew,
        "rep_pax": _dist([r["rep_pax"] for r in rows]),
        "rep_crew": _dist([r["rep_crew"] for r in rows]),
        "rep_pax_takeoff": _dist([r["rep_pax"] for r in tk]),
        "rep_crew_takeoff": _dist([r["rep_crew"] for r in tk]),
        "n_ge_pax": sum(1 for r in rows if r["rep_pax"] >= thr_pax),
        "n_ge_crew": sum(1 for r in rows if r["rep_crew"] >= thr_crew),
        "n_posted": sum(1 for r in rows if r["posted"]),
    }


def render_md(cells: dict[tuple, dict], label: str) -> str:
    lines = [
        f"# {label} — reports/voyage vs VSP posting thresholds",
        "",
        "Thresholds are `ceil(3% * complement)` per channel; a voyage posts "
        "when either channel's reported attack rate reaches 3%.",
        "",
        "| cell | n | takeoff | pax comp (thr) | crew comp (thr) |"
        " rep pax med/p90/max | rep crew med/p90/max |"
        " tk rep pax med/p90/max | tk rep crew med/p90/max |"
        " >=pax thr | >=crew thr | posted |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for key in sorted(cells, key=lambda k: _cell_label(k)):
        s = cells[key]

        def fmt(d: dict) -> str:
            if not d["n"]:
                return "--"
            return f"{d['median']:g}/{d['p90']:g}/{d['max']:g}"

        lines.append(
            f"| {_cell_label(key)} | {s['n']} | {s['n_takeoff']} "
            f"| {s['pax_comp']} ({s['thr_pax']}) "
            f"| {s['crew_comp']} ({s['thr_crew']}) "
            f"| {fmt(s['rep_pax'])} | {fmt(s['rep_crew'])} "
            f"| {fmt(s['rep_pax_takeoff'])} | {fmt(s['rep_crew_takeoff'])} "
            f"| {s['n_ge_pax']} | {s['n_ge_crew']} | {s['n_posted']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs-dir", required=True)
    ap.add_argument("--tiers", nargs="*", default=None)
    ap.add_argument("--label", default="campaign")
    ap.add_argument("--md-out", type=Path)
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()

    collected = collect(args.runs_dir, args.tiers)
    cells = {
        key: summarise_cell(
            [_report_row(run) for run in rows]
        )
        for key, rows in collected.items()
    }
    payload = {
        "label": args.label,
        "cells": {_cell_label(k): v for k, v in cells.items()},
    }
    emit_report_outputs(
        payload, render_md(cells, args.label), args.md_out, args.json_out
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
