"""MEGA-IMPACT-01 baseline reanalysis — design inputs from the existing
NORO-MEGA-01 zips, without re-running a single voyage.

NORO-MEGA-01 recorded cell-level results (0/308 VSP, medians) but not the
per-voyage shape the mechanism scan is designed against. This tool reads
``summary.json`` by S3 range reads for every run zip under the campaign
prefix and emits:

- report-count distance to the posting thresholds (3% of each channel's
  complement, rounded up) — the per-voyage distribution, not just maxima;
- burst12 share — the largest 12-epoch window of ``new_infections`` over
  total aboard acquisitions (point-source outbreaks concentrate onset;
  propagated ramps spread it — food's declared target is the tail);
- still-climbing share and peak-epoch placement (the fleet that never
  crested before disembarkation);
- detection-epoch distribution among detected voyages.

Optionally ``--census-sample N`` additionally fetches the full
``growth_census.json.gz`` member of N stride-sampled zips (the ~200 MB
member, so keep N small) for the ``hosts[].dominant_pathway`` histogram —
the pathway mix aboard-acquired infections arrived by. Caregiver counters
are NOT in these summaries (they predate the mechanisms block); caregiver
effects on mega are measurable only in the new-arm runs.

Reads only; fits nothing.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from outbreak_anchor_readout import (  # noqa: E402
    _posted,
    _row_from_summary,
    _s3_client,
    _s3_member_blob,
    _s3_parse_uri,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from telemetry_buffer.observation_model.score_anchors import (  # noqa: E402
    A9_POSTING_THRESHOLD,
)
from tools.diag.readout_common import emit_report_outputs  # noqa: E402

_DEFAULT_PREFIX = (
    "s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_mega_01/"
)


def _window_share(infections: list[int], width: int = 12) -> float | None:
    """Largest `width`-epoch window's share of total aboard acquisitions.

    Point-source outbreaks concentrate onset into ~one incubation window;
    a propagated ramp spreads it. Returns None on voyages with no
    acquisitions.
    """
    total = sum(infections)
    if total <= 0:
        return None
    best = 0
    acc = sum(infections[:width])
    best = acc
    for i in range(width, len(infections)):
        acc += infections[i] - infections[i - width]
        if acc > best:
            best = acc
    return best / total


def _per_zip_row(summary: dict[str, Any], key_name: str) -> dict[str, Any]:
    """Distance-to-threshold and shape descriptors from one summary."""
    row = _row_from_summary(summary, key_name)
    anchor = row["anchor_row"]
    params = summary.get("parameters", {})
    pax_comp = int(anchor["passenger_complement"])
    crew_comp = int(anchor["crew_complement"])
    thr_pax = math.ceil(A9_POSTING_THRESHOLD * pax_comp)
    thr_crew = math.ceil(A9_POSTING_THRESHOLD * crew_comp)
    rep_pax = round(
        float(anchor["reported_case_attack_rate_passenger"]) * pax_comp
    )
    rep_crew = round(
        float(anchor["reported_case_attack_rate_crew"]) * crew_comp
    )
    ts = summary.get("timeseries") or []
    new_infect = [int(e.get("new_infections", 0) or 0) for e in ts]
    num_epochs = int(params.get("num_epochs") or len(new_infect) or 0)
    last_inf = row.get("last_infecting_epoch")
    return {
        "run_id": row["run_id"],
        "seed": row["seed"],
        "ignited": row["ignited"],
        "n_acquired": row["n_acquired"],
        "rep_pax": rep_pax,
        "rep_crew": rep_crew,
        "thr_pax": thr_pax,
        "thr_crew": thr_crew,
        "pax_ratio": rep_pax / thr_pax if thr_pax else 0.0,
        "crew_ratio": rep_crew / thr_crew if thr_crew else 0.0,
        "posted": _posted(anchor),
        "vsp_trigger_epoch": row.get("vsp_trigger_epoch"),
        "detection_epoch": row.get("detection_epoch"),
        "peak_epoch": row.get("peak_epoch"),
        "peak_prevalence": row.get("peak_prevalence"),
        "num_epochs": num_epochs,
        "still_climbing": (
            last_inf is not None and num_epochs
            and last_inf >= num_epochs - 2
        ),
        "burst12_share": _window_share(new_infect),
    }


def _quantiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"n": 0, "median": None, "p90": None, "max": None}
    ordered = sorted(values)
    n = len(ordered)

    def q(frac: float) -> float:
        pos = frac * (n - 1)
        lo = math.floor(pos)
        hi = math.ceil(pos)
        if lo == hi:
            return ordered[lo]
        return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)

    return {"n": n, "median": q(0.5), "p90": q(0.9), "max": ordered[-1]}


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    active = [r for r in rows if r["n_acquired"] > 0]
    detected = [r for r in rows if r["detection_epoch"] is not None]
    near = dict.fromkeys((0.80, 0.90, 0.95, 1.0), 0)
    for r in rows:
        gap = max(r["pax_ratio"], r["crew_ratio"])
        for b in near:
            if gap >= b:
                near[b] += 1
    burst = [r["burst12_share"] for r in active if r["burst12_share"] is not None]
    return {
        "n": len(rows),
        "ignited": sum(1 for r in rows if r["ignited"]),
        "acquired_pos": len(active),
        "posted": sum(1 for r in rows if r["posted"]),
        "vsp_triggered": sum(
            1 for r in rows if r["vsp_trigger_epoch"] is not None
        ),
        "rep_pax": _quantiles([float(r["rep_pax"]) for r in rows]),
        "rep_crew": _quantiles([float(r["rep_crew"]) for r in rows]),
        "pax_ratio": _quantiles([r["pax_ratio"] for r in rows]),
        "crew_ratio": _quantiles([r["crew_ratio"] for r in rows]),
        "within_threshold_share": near,
        "burst12_share": _quantiles([float(b) for b in burst]),
        "still_climbing": sum(1 for r in rows if r["still_climbing"]),
        "peak_epoch": _quantiles(
            [float(r["peak_epoch"]) for r in rows
             if r["peak_epoch"] is not None],
        ),
        "detection_epoch": _quantiles(
            [float(r["detection_epoch"]) for r in detected],
        ),
        "detected": len(detected),
    }


_PATHWAY_RE = re.compile(r'"dominant_pathway":\s*"?([a-z_]+)"?')


def _pathway_sample(
    keys: list[str], bucket: str, sample: int,
) -> dict[str, Any]:
    """Full census member on a stride sample: pathway histogram only.

    Regex-scans the decompressed member rather than ``json.loads`` —
    a 7000-host census parses to ~6-8 GB of dicts, which OOM-kills the
    dev box; the raw text is ~1.5 GB and the scan adds nothing. Each
    acquired host's ``dominant_pathway`` appears twice (acquisition row
    and host row), which doubles the counts but leaves the shares exact.
    """
    client = _s3_client()
    if not keys or sample <= 0:
        return {}
    step = max(1, len(keys) // sample)
    chosen = keys[::step][:sample]
    pathway_counts: dict[str, int] = defaultdict(int)
    total_hits = 0
    read = 0
    for key in chosen:
        blob = _s3_member_blob(
            client, bucket, key, "growth_census.json.gz",
        )
        if blob is None:
            continue
        try:
            text = gzip.decompress(blob).decode("utf-8")
        except (OSError, ValueError):
            continue
        del blob
        read += 1
        for match in _PATHWAY_RE.finditer(text):
            pathway_counts[match.group(1)] += 1
            total_hits += 1
        del text
    return {
        "zips_read": read,
        "pathway_mentions": total_hits,
        "pathway_counts": dict(
            sorted(
                pathway_counts.items(), key=lambda kv: -kv[1],
            ),
        ),
    }


def _list_keys(client, bucket: str, prefix: str, tier: str) -> list[str]:
    sub = f"{prefix}{tier}/"
    return [
        obj["Key"]
        for page in client.get_paginator("list_objects_v2").paginate(
            Bucket=bucket, Prefix=sub,
        )
        for obj in page.get("Contents", [])
        if obj["Key"].endswith(".zip")
    ]


def _render(report: dict[str, Any]) -> str:
    agg = report["aggregate"]
    lines = [
        "# NORO-MEGA-01 baseline reanalysis (MEGA-IMPACT design inputs)",
        "",
        "Status: measured — per-voyage shape + threshold-distance + "
        "pathway-mix descriptors of the existing NORO-MEGA-01 zips. "
        "Tool: `tools/noro_diag/mega_baseline_reanalysis.py` (regenerates "
        "this file). Complements `noro_onset_curve_01_readout.md`, which "
        "established the burst12>0.5 absence on this same cell.",
        "",
        f"Source: `{report['s3_prefix']}{report['tier']}/` — "
        f"{agg['n']} run zips, ranged `summary.json` reads only; "
        "census member touched only on the stride sample below.",
        "",
        "## Cell",
        "",
        "| n | ignited | acquired>0 | posted | VSP triggered | detected |",
        "|---|---|---|---|---|---|",
        f"| {agg['n']} | {agg['ignited']} | {agg['acquired_pos']} | "
        f"{agg['posted']} | {agg['vsp_triggered']} | {agg['detected']} |",
        "",
        "## Distance to the posting threshold",
        "",
        "Threshold = ceil(3% x channel complement) per voyage.",
        "",
        "| channel | median reports | p90 | max | median ratio | p90 | max |",
        "|---|---|---|---|---|---|---|",
    ]
    for ch, rep, ratio in (
        ("pax", "rep_pax", "pax_ratio"),
        ("crew", "rep_crew", "crew_ratio"),
    ):
        r, q = agg[rep], agg[ratio]
        lines.append(
            f"| {ch} | {_fmt_num(r['median'])} | {_fmt_num(r['p90'])} | "
            f"{_fmt_num(r['max'])} | "
            f"{_fmt(q['median'])} | {_fmt(q['p90'])} | {_fmt(q['max'])} |",
        )
    lines += [
        "",
        "Voyages whose best channel ratio reached a fraction of threshold:",
        "",
        "| >= 80% | >= 90% | >= 95% | >= 100% (posts) |",
        "|---|---|---|---|",
        f"| {agg['within_threshold_share'][0.8]} | "
        f"{agg['within_threshold_share'][0.9]} | "
        f"{agg['within_threshold_share'][0.95]} | "
        f"{agg['within_threshold_share'][1.0]} |",
        "",
        "## Onset shape",
        "",
        "| measure | median | p90 | max | n |",
        "|---|---|---|---|---|",
    ]
    b = agg["burst12_share"]
    lines.append(
        f"| burst12 share (12-epoch max window / total acq) | "
        f"{_fmt(b['median'])} | {_fmt(b['p90'])} | {_fmt(b['max'])} | {b['n']} |",
    )
    p = agg["peak_epoch"]
    lines.append(
        f"| peak epoch | {_fmt(p['median'])} | {_fmt(p['p90'])} | "
        f"{_fmt(p['max'])} | {p['n']} |",
    )
    d = agg["detection_epoch"]
    lines.append(
        f"| detection epoch (detected voyages) | {_fmt(d['median'])} | "
        f"{_fmt(d['p90'])} | {_fmt(d['max'])} | {d['n']} |",
    )
    lines += [
        "",
        f"Still-climbing voyages (last acquisition in the final 2 epochs): "
        f"{agg['still_climbing']}/{agg['n']}.",
        "",
        "## Pathway mix (stride sample)",
        "",
    ]
    ps = report.get("pathway_sample") or {}
    if ps:
        lines += [
            f"Zips read: {ps['zips_read']}; acquired-host pathway "
            f"mentions: {ps['pathway_mentions']} (acquisition row + host "
            "row counted once each).",
            "",
            "| dominant_pathway | mentions | share |",
            "|---|---|---|",
        ]
        for path, count in ps["pathway_counts"].items():
            share = count / ps["pathway_mentions"] if ps["pathway_mentions"] else 0
            lines.append(f"| {path} | {count} | {share:.3f} |")
    else:
        lines.append(
            "Not sampled (--census-sample 0). Caregiver counters are not "
            "in these summaries — they predate the mechanisms block.",
        )
    lines += [
        "",
        "Measured at campaign SHA + seeds recorded per zip; "
        "no parameters were fitted.",
    ]
    return "\n".join(lines) + "\n"


def _fmt(value: float | None) -> str:
    return "—" if value is None else f"{value:.3f}"


def _fmt_num(value: float | None) -> str:
    """Report counts render as integers; absent values as the dash."""
    if value is None:
        return "—"
    return f"{value:.0f}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--s3-prefix", default=_DEFAULT_PREFIX)
    parser.add_argument("--tier", default="fl_mega_12d_scr")
    parser.add_argument(
        "--census-sample", type=int, default=0,
        help="stride-sample N zips for the full census member "
             "(dominant_pathway histogram); each read is ~200 MB",
    )
    parser.add_argument("--md-out", type=Path, default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)

    client = _s3_client()
    bucket, prefix = _s3_parse_uri(args.s3_prefix)
    keys = sorted(_list_keys(client, bucket, prefix, args.tier))
    print(f"{len(keys)} zips under {args.s3_prefix}{args.tier}/", flush=True)

    def one(key: str) -> dict[str, Any] | None:
        blob = _s3_member_blob(client, bucket, key, "summary.json")
        if blob is None:
            return None
        try:
            return _per_zip_row(
                json.loads(blob), key.rsplit("/", 1)[-1],
            )
        except (json.JSONDecodeError, KeyError, RuntimeError):
            return None

    with ThreadPoolExecutor(max_workers=32) as pool:
        rows = [r for r in pool.map(one, keys) if r is not None]
    print(f"scored {len(rows)} summaries", flush=True)

    report = {
        "s3_prefix": args.s3_prefix,
        "tier": args.tier,
        "rows": rows,
        "aggregate": _aggregate(rows),
        "pathway_sample": _pathway_sample(
            keys, bucket, args.census_sample,
        ),
    }
    emit_report_outputs(report, _render(report), args.md_out, args.json_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
