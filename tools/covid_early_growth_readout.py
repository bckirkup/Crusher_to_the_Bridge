#!/usr/bin/env python3
"""COVID early-growth decomposition: where does the record-timed mass overshoot
sit — early growth or post-quarantine tail?

Pure readout over committed campaign cell payloads (``cell_*.json`` files
carrying ``acquisition_curve.total_by_day`` + ``observables``). For each cell
it reports cumulative infections at the contract landmarks (days 5/10/15/16/
20/25/30/34, day 16 = quarantine day, day 17 = the covid.T1 onset split) and
the 5-day fold rates; per regime (record-timed ignition <= 9 vs late/none)
it medians the landmarks against the record's anchors:

  - infection band [712, 960] (covid.T3-implied truth band)
  - 34 recorded onsets before day 17, 163 on/after (covid.T1)
  - 197 recorded onsets total

Usage:
    python3 tools/covid_early_growth_readout.py --dir <cells dir> [--dir ...]
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

LANDMARKS = (5, 10, 15, 16, 20, 25, 30, 34)
RECORD_INFECTION_BAND = (712, 960)
RECORD_ONSETS_BEFORE_17 = 34
RECORD_ONSETS_TOTAL = 197


def _cum(acq: dict, upto: int) -> int:
    return sum(v for d, v in acq["total_by_day"].items() if int(d) <= upto)


def _ignition_day(payload: dict) -> int | None:
    """First day cumulative infections reach 50 (IGNITION_MASS), else None."""
    total = 0
    for d, v in sorted(payload["acquisition_curve"]["total_by_day"].items(),
                       key=lambda kv: int(kv[0])):
        total += v
        if total >= 50:
            return int(d)
    return None


def _row(path: Path) -> dict:
    c = json.loads(path.read_text())
    acq = c["acquisition_curve"]
    obs = c.get("observables", {})
    seed = c["cell"]["seed"]
    ign = _ignition_day(c)
    cum = {d: _cum(acq, d) for d in LANDMARKS}
    folds = {
        "d5-10": cum[10] / max(cum[5], 1),
        "d10-15": cum[15] / max(cum[10], 1),
        "d16-30": cum[30] / max(cum[16], 1),
    }
    return {
        "seed": seed,
        "ign": ign,
        "record_timed": ign is not None and ign <= 9,
        "founders": c.get("seed_ring", {}).get("aboard_window_acquisitions"),
        "onsets": obs.get("recorded_onsets"),
        "before": obs.get("onsets_before_split_day"),
        "cum": cum,
        "folds": folds,
    }


def _median(rows, key):
    vals = [r["cum"][key] for r in rows]
    return statistics.median(vals) if vals else float("nan")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", action="append", required=True)
    args = ap.parse_args()

    rows = []
    for d in args.dir:
        path = Path(d)
        if not path.is_dir():
            raise SystemExit(f"--dir {d} is not a directory")
        rows.extend(_row(f) for f in sorted(path.glob("cell_*.json")))
    if not rows:
        raise SystemExit(f"no cell_*.json found under {args.dir}")

    timed = [r for r in rows if r["record_timed"]]
    late = [r for r in rows if not r["record_timed"] and r["cum"][34] > 0]

    print("| seed | founders | ign | cum d5 | d10 | d15 | d16 | d30 | d34 |"
          " fold 5-10 | 10-15 | 16-30 | onsets | before17 |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        c, f = r["cum"], r["folds"]
        print(f"| {r['seed']} | {r['founders']} | {r['ign'] or '-'} | {c[5]}"
              f" | {c[10]} | {c[15]} | {c[16]} | {c[30]} | {c[34]}"
              f" | {f['d5-10']:.1f} | {f['d10-15']:.1f} | {f['d16-30']:.1f}"
              f" | {r['onsets']} | {r['before']} |")

    print(f"\nrecord-timed cells (ign<=9): n={len(timed)}")
    if timed:
        # day 15 is the last pre-quarantine day (quarantine opens day 16)
        print(f"  d15 (pre-quarantine) infections median"
              f" {_median(timed,15):.0f}"
              f" (record band {RECORD_INFECTION_BAND})")
        print(f"  d34 infections range"
              f" {min(r['cum'][34] for r in timed)}-"
              f"{max(r['cum'][34] for r in timed)}")
        post = [r["folds"]["d16-30"] for r in timed]
        print(f"  post-16 fold range {min(post):.1f}-{max(post):.1f}")
        before = [r["before"] for r in timed if r["before"] is not None]
        print(f"  before-17 recorded onsets median"
              f" {statistics.median(before):.0f} vs record"
              f" {RECORD_ONSETS_BEFORE_17}")
    print(f"late/non-igniting nonzero cells: n={len(late)}")
    if late:
        print(f"  d34 infections median {_median(late,34):.0f};"
              f" post-16 fold median"
              f" {statistics.median([r['folds']['d16-30'] for r in late]):.1f}")


if __name__ == "__main__":
    main()
