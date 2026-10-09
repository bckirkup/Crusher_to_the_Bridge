#!/usr/bin/env python3
"""Early shared-dose event report — aggregates early_event_scan JSONL.

Reads the per-voyage rows emitted by ``early_event_scan.py`` (summary-only
and census passes joined on ``key``) and prints the markdown tables for the
early-event analysis document:

- coverage and posting counts per campaign cell;
- the frequencies leg: rate of >=1 early shared-dose event per voyage vs
  the posting rate, per cell;
- the size join: per-voyage *largest* early event on posted vs unposted
  voyages, the smallest voyage-max early event that ever preceded a
  posting, and a size-threshold conversion table (P(post | max early
  size >= t));
- the route decomposition: source_kind mix of early events and which arm
  produced the voyage-max early event on posted voyages.

An "early event" is a contamination object with ``seeded_epoch`` <= the
scan's early ceiling (object arms) or a pan-window serving event with
``start_epoch`` <= the ceiling (v1/independent/mega arms); size is
``servings_served`` / ``servings_taken`` respectively — see the scan
tool's docstring. Objects vs pan-window events are kept as separate event
forms (``f == "obj"`` / ``"ev"``); where an arm emits both, the object row
is the event unit and linked window servings roll up into it.

Reads local JSONL only; no AWS access needed.
"""

from __future__ import annotations

import argparse
import json
import statistics as stats
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from simulation_utils.paths import validated_open  # noqa: E402

_CUTS = (5, 10, 15, 20, 25, 30, 40, 50, 75, 100, 150, 200)
_KIND_SHORT = {
    "provisioned_lot": "lot",
    "ill_handler": "handler",
    "ill_diner": "diner",
}


def _load_rows(paths: list[str]) -> dict[str, dict]:
    """Join scan rows on key; census-bearing rows win field-wise."""
    rows: dict[str, dict] = {}
    for path in paths:
        with validated_open(
            str(path),
            encoding="utf-8",
            allowed_roots=(str(Path(path).resolve().parent),),
        ) as fh:
            for line in fh:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = row.get("key")
                if not key:
                    continue
                rows.setdefault(key, {}).update(
                    {k: v for k, v in row.items() if v is not None}
                )
    return rows


def _cell_of(row: dict) -> str:
    """fl_<hull>_12d_scr_<arm> / fl_mega_impact_<arm> / fl_mega_12d_scr."""
    tier = row["key"].rsplit("/", 2)[-2]
    if tier.startswith("fl_mega_12d_scr"):
        return "mega a0"
    if tier.startswith("fl_mega_impact_"):
        return f"mega {tier.removeprefix('fl_mega_impact_')}"
    parts = tier.split("_")
    if len(parts) >= 5 and parts[0] == "fl":
        return f"{parts[1]} {parts[-1]}"
    return tier


def _voyage_max_early(row: dict) -> int:
    census = row.get("census") or {}
    return max((int(e.get("t") or 0) for e in census.get("early") or []),
               default=0)


def _voyage_early_takers(row: dict) -> int:
    census = row.get("census") or {}
    return sum(int(e.get("t") or 0) for e in census.get("early") or [])


def _quantiles(xs: list[float]) -> dict:
    xs = sorted(xs)
    if not xs:
        return {"n": 0}
    def q(p: float) -> float:
        return xs[min(len(xs) - 1, int(p * len(xs)))]
    return {
        "n": len(xs),
        "med": round(stats.median(xs), 3),
        "p90": round(q(0.9), 3),
        "max": xs[-1],
        "min": xs[0],
    }


def _pct(num: int, den: int) -> str:
    return f"{100.0 * num / den:.1f}%" if den else "-"


def _coverage(cells: dict[str, list[dict]]) -> list[str]:
    lines = [
        "| cell | n voy | posted | censused | early>0 | post&census |",
        "|---|---|---|---|---|---|",
    ]
    for cell in sorted(cells):
        rows = cells[cell]
        cen = [r for r in rows if r.get("census") and not
               (r["census"] or {}).get("error")]
        early = [r for r in cen if (r["census"]["n_early_obj"]
                                    + r["census"]["n_early_ev"]) > 0]
        lines.append(
            f"| {cell} | {len(rows)} | {sum(r['posted'] for r in rows)}"
            f" | {len(cen)} | {len(early)}"
            f" | {sum(r['posted'] for r in cen)} |"
        )
    return lines


def _frequency_table(cells: dict[str, list[dict]]) -> list[str]:
    """Rate of >=1 early event per voyage vs posting rate, per cell."""
    lines = [
        "| cell | censused | >=1 early | early rate | posted (all voy)"
        " | posted in census | P(post \\| early) |",
        "|---|---|---|---|---|---|---|",
    ]
    for cell in sorted(cells):
        rows = cells[cell]
        cen = [r for r in rows if r.get("census") and not
               r["census"].get("error")]
        early = [r for r in cen if _voyage_max_early(r) > 0]
        post_cen = sum(r["posted"] for r in cen)
        post_early = sum(r["posted"] for r in early)
        lines.append(
            f"| {cell} | {len(cen)} | {len(early)}"
            f" | {_pct(len(early), len(cen))}"
            f" | {sum(r['posted'] for r in rows)}"
            f" ({_pct(sum(r['posted'] for r in rows), len(rows))})"
            f" | {post_cen} | {post_early}/{len(early)}"
            f" = {_pct(post_early, len(early))} |"
        )
    return lines


def _size_join(cells: dict[str, list[dict]], hull_prefix: str) -> list[str]:
    """Voyage-max early event size: posted vs unposted, per cell."""
    lines = [
        "| cell | posted n | max-early med [p90] posted"
        " | unposted n | max-early med [p90] unposted"
        " | smallest posted voyage max-early |",
        "|---|---|---|---|---|---|",
    ]
    for cell in sorted(cells):
        if not cell.startswith(hull_prefix):
            continue
        cen = [r for r in cells[cell] if r.get("census")
               and not r["census"].get("error")]
        posted = [_voyage_max_early(r) for r in cen if r["posted"]]
        unposted = [
            _voyage_max_early(r) for r in cen if not r["posted"]
        ]
        q_post = _quantiles(posted)
        q_un = _quantiles(unposted)
        med_post = (
            f"{q_post['med']:g} [{q_post['p90']:g}]" if posted else "-"
        )
        med_un = f"{q_un['med']:g} [{q_un['p90']:g}]" if unposted else "-"
        smallest = min(posted) if posted else "-"
        lines.append(
            f"| {cell} | {len(posted)} | {med_post} | {len(unposted)}"
            f" | {med_un} | {smallest} |"
        )
    return lines


def _threshold_table(rows: list[dict], label: str) -> list[str]:
    """P(post | voyage-max early size >= t) across takers cutoffs."""
    cen = [r for r in rows if r.get("census")
           and not r["census"].get("error")]
    lines = [
        f"| {label} | voyages >= cut | posted | conv |",
        "|---|---|---|---|",
    ]
    for t in _CUTS:
        over = [r for r in cen if _voyage_max_early(r) >= t]
        post = sum(r["posted"] for r in over)
        lines.append(
            f"| >={t} takers | {len(over)} | {post} |"
            f" {_pct(post, len(over))} |"
        )
    return lines


def _route_table(rows: list[dict], label: str) -> list[str]:
    """source_kind of each posted voyage's max early event + event mix."""
    cen = [r for r in rows if r.get("census")
           and not r["census"].get("error")]
    posted = [r for r in cen if r["posted"]]
    driver = Counter()
    for r in posted:
        early = (r["census"].get("early") or [])
        if not early:
            driver["(none)"] += 1
            continue
        top = max(early, key=lambda e: int(e.get("t") or 0))
        driver[_KIND_SHORT.get(top.get("k"), top.get("k") or "?")] += 1
    mix_post = Counter()
    mix_all = Counter()
    for r in cen:
        for e in r["census"].get("early") or []:
            k = _KIND_SHORT.get(e.get("k"), e.get("k") or "?")
            mix_all[k] += 1
            if r["posted"]:
                mix_post[k] += 1
    lines = [
        f"| {label} | lot | handler | diner | (none) |",
        "|---|---|---|---|---|",
    ]
    total_post = sum(mix_post.values())
    total_all = sum(mix_all.values())
    lines.append(
        "| early events, posted voyages |"
        + "".join(
            f" {mix_post.get(k, 0)} ({_pct(mix_post.get(k, 0), total_post)}) |"
            for k in ("lot", "handler", "diner")
        )
        + " - |"
    )
    lines.append(
        "| early events, all voyages |"
        + "".join(
            f" {mix_all.get(k, 0)} ({_pct(mix_all.get(k, 0), total_all)}) |"
            for k in ("lot", "handler", "diner")
        )
        + " - |"
    )
    lines.append(
        "| voyage-max early event arm, posted voyages |"
        + "".join(
            f" {driver.get(k, 0)} |"
            for k in ("lot", "handler", "diner")
        )
        + f" {driver.get('(none)', 0)} |"
    )
    return lines


def _hull_rows(cells: dict[str, list[dict]]) -> dict[str, list[dict]]:
    by_hull: dict[str, list[dict]] = defaultdict(list)
    for cell, rows in cells.items():
        hull = cell.split(" ", 1)[0]
        by_hull[hull].extend(rows)
    return by_hull


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rows", action="append", required=True,
                    help="JSONL rows file from early_event_scan.py")
    args = ap.parse_args()
    rows = _load_rows(args.rows)
    cells: dict[str, list[dict]] = defaultdict(list)
    for r in rows.values():
        if "posted" not in r:
            continue
        cells[_cell_of(r)].append(r)
    print(f"## coverage ({len(rows)} rows)\n")
    print("\n".join(_coverage(cells)))
    print("\n## frequency leg\n")
    print("\n".join(_frequency_table(cells)))
    print("\n## size join\n")
    print("\n".join(_size_join(cells, "")))
    by_hull = _hull_rows(cells)
    for hull in sorted(by_hull):
        print(f"\n## thresholds — {hull}\n")
        print("\n".join(_threshold_table(by_hull[hull], hull)))
        print(f"\n## routes — {hull}\n")
        print("\n".join(_route_table(by_hull[hull], hull)))


if __name__ == "__main__":
    main()
