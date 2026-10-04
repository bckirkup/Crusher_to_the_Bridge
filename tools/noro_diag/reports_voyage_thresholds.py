#!/usr/bin/env python3
"""Reports-per-voyage vs the VSP posting threshold, per cell.

The outbreak-anchor readout scores posting (A9: reported attack rate >= 3%
on either channel) but does not show how the underlying report counts sit
against the absolute thresholds a posting implies (~3% of complement on
each channel). This tool streams ``summary.json`` from campaign-layout run
zips (``<root>/<tier>/<run_id>.zip``, S3 ranged GETs only) and emits, per
cell:

- passenger/crew complements and the implied report thresholds
  (``ceil(3% * complement)`` per channel);
- the distribution of ``cumulative_reported_cases_{passenger,crew}``
  (median / p90 / max), over all runs and takeoff voyages only;
- per-channel threshold crossings and the posted count, so the gap
  between "reports/voyage" and "posts/voyage" is explicit.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_REPO_ROOT / "tools" / "noro_diag") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "tools" / "noro_diag"))

from simulation_utils.paths import validated_open  # noqa: E402
from telemetry_buffer.observation_model.score_anchors import (  # noqa: E402
    A9_POSTING_THRESHOLD,
)
from tools.diag.readout_common import (  # noqa: E402
    iter_tier_zips,
    load_zip_json,
    seed_from_params,
)
from tools.noro_diag.outbreak_anchor_readout import (  # noqa: E402
    _cell_key,
    _cell_label,
    _s3_client,
    _s3_member_blob,
    _s3_parse_uri,
)

_MEMBER = "summary.json"


def _row_from_summary(summary: dict, fallback_name: str) -> dict[str, Any]:
    params = summary.get("parameters", {})
    summ = summary.get("summary", {})
    derived = summary.get("derived", {})
    pax_comp = int(summ.get("passenger_complement", 0) or 0)
    crew_comp = int(summ.get("crew_complement", 0) or 0)
    rep_pax = int(summ.get("cumulative_reported_cases_passenger", 0) or 0)
    rep_crew = int(summ.get("cumulative_reported_cases_crew", 0) or 0)
    return {
        "run_id": summary.get("run_id", fallback_name),
        "cell_key": _cell_key(params),
        "seed": seed_from_params(params),
        "pax_comp": pax_comp,
        "crew_comp": crew_comp,
        "rep_pax": rep_pax,
        "rep_crew": rep_crew,
        "rep_pax_ar": rep_pax / pax_comp if pax_comp else 0.0,
        "rep_crew_ar": rep_crew / crew_comp if crew_comp else 0.0,
        "takeoff": int(derived.get("peak_prevalence", 0) or 0) >= 10,
        "posted": bool(derived.get("vsp_trigger_epoch") is not None),
    }


def _list_keys(client, bucket: str, prefix: str, tiers: list[str] | None) -> list[str]:
    subs = [f"{prefix}{tier}/" for tier in tiers] if tiers else [prefix]
    return [
        obj["Key"]
        for sub in subs
        for page in client.get_paginator("list_objects_v2").paginate(
            Bucket=bucket, Prefix=sub
        )
        for obj in page.get("Contents", [])
        if obj["Key"].endswith(".zip")
    ]


def _collect_s3(s3_uri: str, tiers: list[str] | None) -> list[dict]:
    client = _s3_client()
    bucket, prefix = _s3_parse_uri(s3_uri)
    keys = _list_keys(client, bucket, prefix, tiers)

    def one(key: str) -> dict | None:
        try:
            blob = _s3_member_blob(client, bucket, key, _MEMBER)
            if blob is None:
                return None
            return _row_from_summary(
                json.loads(blob), key.rsplit("/", 1)[-1]
            )
        except (json.JSONDecodeError, KeyError, OSError):
            return None

    with ThreadPoolExecutor(max_workers=32) as pool:
        return [r for r in pool.map(one, keys) if r is not None]


def _collect_local(root: Path, tiers: list[str] | None) -> list[dict]:
    rows = []
    for _tier, zip_path in iter_tier_zips(root, tiers):
        summary = load_zip_json(zip_path, _MEMBER)
        if summary is not None:
            rows.append(_row_from_summary(summary, zip_path.stem))
    return rows


def collect(runs_dir: str, tiers: list[str] | None) -> dict[tuple, list[dict]]:
    if runs_dir.startswith("s3://"):
        rows = _collect_s3(runs_dir, tiers)
    else:
        rows = _collect_local(Path(runs_dir), tiers)
    cells: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        cells[tuple(row["cell_key"])].append(row)
    return dict(cells)


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

    cells = {
        key: summarise_cell(rows)
        for key, rows in collect(args.runs_dir, args.tiers).items()
    }
    payload = {
        "label": args.label,
        "cells": {_cell_label(k): v for k, v in cells.items()},
    }
    md = render_md(cells, args.label)
    if args.md_out:
        allowed = (str(args.md_out.parent.resolve()),)
        with validated_open(
            str(args.md_out), "w", allowed_roots=allowed, encoding="utf-8"
        ) as fh:
            fh.write(md)
    else:
        sys.stdout.write(md)
    if args.json_out:
        allowed = (str(args.json_out.parent.resolve()),)
        with validated_open(
            str(args.json_out), "w", allowed_roots=allowed, encoding="utf-8"
        ) as fh:
            json.dump(payload, fh, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
