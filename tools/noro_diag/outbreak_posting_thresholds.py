"""Posting-threshold readout: reported cases per voyage vs the VSP cutoffs.

The A9 posting rule fires when the reported case attack rate reaches 3% on
either channel — i.e. reported cases >= 0.03 x complement on that channel
(spirit: >= 63 passenger reports or >= 27 crew reports). The anchor readout
reports the posted fraction itself but not how far the per-voyage report
counts sit from those wires. This tool groups a campaign's run rows by the
same cell key as ``outbreak_anchor_readout`` and tabulates, per cell:

- median/IQR/max reported passenger and crew cases per voyage,
- the count and Wilson 95% interval of voyages crossing each channel's
  posting cutoff alone,
- the joint posted count (either channel) as a cross-check against the
  anchor readout's ``posted`` column.

Usage (mirrors outbreak_anchor_readout.py)::

    .venv/bin/python tools/noro_diag/outbreak_posting_thresholds.py \
        --runs-dir s3://<bucket>/campaign/noro_outbreak_04/ \
        --tiers fl_spr_12d_scr fl_spr_12d_ren \
        --md-out ~/ob04_thresholds.md --json-out ~/ob04_thresholds.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from simulation_utils.paths import validated_open  # noqa: E402
from tools.diag.readout_common import rate_summary  # noqa: E402
from tools.noro_diag.outbreak_anchor_readout import (  # noqa: E402
    A9_POSTING_THRESHOLD,
    _cell_label,
    _fmt,
    _pct,
    _quant_cell,
    _quantiles,
    collect,
)


def _channel_block(
    cases: list[float], cutoff: float,
) -> dict[str, Any]:
    """Distribution + crossing count for one reporting channel."""
    q = _quantiles(cases)
    n_over = sum(c >= cutoff for c in cases)
    return {
        "quantiles": q,
        "max": max(cases) if cases else None,
        "n_over": n_over,
        "rate": rate_summary(n_over, len(cases)),
        "cutoff": cutoff,
    }


def _cell_block(runs: list[dict]) -> dict[str, Any]:
    pax_cases: list[float] = []
    crew_cases: list[float] = []
    cutoffs: list[tuple[float, float]] = []
    n_posted = 0
    for run in runs:
        row = run["anchor_row"]
        pax = row["reported_case_attack_rate_passenger"]
        crew = row["reported_case_attack_rate_crew"]
        p_comp = float(row["passenger_complement"])
        c_comp = float(row["crew_complement"])
        pax_cases.append(pax * p_comp)
        crew_cases.append(crew * c_comp)
        cutoffs.append(
            (A9_POSTING_THRESHOLD * p_comp, A9_POSTING_THRESHOLD * c_comp)
        )
        if pax >= A9_POSTING_THRESHOLD or crew >= A9_POSTING_THRESHOLD:
            n_posted += 1
    pax_cut = max(c for c, _ in cutoffs) if cutoffs else 0.0
    crew_cut = max(c for _, c in cutoffs) if cutoffs else 0.0
    return {
        "n": len(runs),
        "passenger": _channel_block(pax_cases, pax_cut),
        "crew": _channel_block(crew_cases, crew_cut),
        "n_posted": n_posted,
        "posted_rate": rate_summary(n_posted, len(runs)),
    }


def render_markdown(report: dict) -> str:
    out = [f"# {report.get('title') or 'Posting-threshold readout'}", ""]
    out += [
        "Reported cases per voyage vs the VSP posting cutoffs "
        "(>= 3% of channel complement).",
        "",
        "| cell | n | pax reports med [IQR] | pax max | pax over wire | "
        "crew reports med [IQR] | crew max | crew over wire | posted (either) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for label, block in report["cells"].items():
        p, c = block["passenger"], block["crew"]
        out.append(
            f"| {label} | {block['n']}"
            f" | {_quant_cell(p['quantiles'])}"
            f" | {_fmt(p['max'], 0)}"
            f" | {p['n_over']} of >={_fmt(p['cutoff'], 0)} ({_pct(p['rate'])})"
            f" | {_quant_cell(c['quantiles'])}"
            f" | {_fmt(c['max'], 0)}"
            f" | {c['n_over']} of >={_fmt(c['cutoff'], 0)} ({_pct(c['rate'])})"
            f" | {block['n_posted']} ({_pct(block['posted_rate'])}) |"
        )
    out += [""]
    return "\n".join(out)


def build_report(
    root: Path, tiers: list[str] | None = None, title: str = "",
) -> dict[str, Any]:
    cells = collect(root, tiers)
    report: dict[str, Any] = {"title": title, "cells": {}}
    for key, runs in sorted(cells.items(), key=lambda kv: _cell_label(kv[0])):
        report["cells"][_cell_label(key)] = _cell_block(runs)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-dir", required=True, type=Path)
    parser.add_argument("--tiers", nargs="*", default=None)
    parser.add_argument("--title", default="Posting-threshold readout")
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--md-out", type=Path, default=None)
    args = parser.parse_args()
    report = build_report(args.runs_dir, args.tiers, title=args.title)
    if args.md_out:
        allowed = (str(args.md_out.parent.resolve()),)
        with validated_open(
            str(args.md_out), "w", allowed_roots=allowed, encoding="utf-8",
        ) as fh:
            fh.write(render_markdown(report))
    if args.json_out:
        allowed = (str(args.json_out.parent.resolve()),)
        with validated_open(
            str(args.json_out), "w", allowed_roots=allowed, encoding="utf-8",
        ) as fh:
            json.dump(report, fh, indent=1, default=str)
    if not args.md_out and not args.json_out:
        print(render_markdown(report))


if __name__ == "__main__":
    main()
