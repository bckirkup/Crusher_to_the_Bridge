#!/usr/bin/env python3
"""IGNITION-01 readout: decompose the ~10-day-late exponential ignition.

Reads campaign cell payloads (sync an S3 block into the checkout first)
carrying ``seed_ring`` and ``acquisition_curve`` echoes and decomposes
why, at right-sized truth (theta=3.162e8, ``dp_theta_8p50`` / D0_declared
verbatim replay), most draws ignite ~10 d after the record's day-13-15
confinement peak while a minority ignite on time.

Per cell it reports the founder window: ``seed_spec`` (count, departure
day, infection age, onset day, role), the seeded host's realized zone
placement and ring sizes, ``aboard_window_acquisitions`` (every
non-seeded infection while the index was aboard), the clean bound
(index-attributable events before any secondary could shed), the
aboard-window by-day/by-route splits, cumulative infections at days
5/10/15, the ignition day (first day cumulative infections reach
IGNITION_MASS), before-quarantine mass, and the funnel_hosts median
infection day.

Pooled it reports the founder-yield distribution, the aboard-window
route totals, the takeoff-classified founder-vs-timing table, and the
post-founder growth fold (cum10 -> cum15) so "late ignition" separates
into founder-pool size (seed-ring / early-exposure structure) from
post-ignition growth rate (intrinsic dose timing).

Takeoff follows the scorer's gate: ``recorded_onsets >= 10``.
Record-timed = takeoff AND median infection day <= RECORD_MEDIAN_DAY
(the record peaked at confinement, days 13-15).

Usage:
    python3 tools/covid_ignition_readout.py \
        --cells <dir> [--cells <dir>] --out <json> [--out-md <md>]
"""
from __future__ import annotations

import argparse
import glob
import json
import statistics
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from simulation_utils.paths import resolve_repo_path, validated_open  # noqa: E402

IGNITION_MASS = 50
RECORD_MEDIAN_DAY = 15
TAKEOFF_MIN_ONSETS = 10
QUARANTINE_DAY = 16


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def _cell_record(path: str) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    obs = payload.get("observables") or {}
    sr = payload.get("seed_ring") or {}
    spec = sr.get("seed_spec") or {}
    hosts = sr.get("seeded_hosts") or []
    host = hosts[0] if hosts else {}
    daily = {
        int(k): v
        for k, v in (payload.get("acquisition_curve") or {})
        .get("total_by_day", {}).items()
    }

    def cum(day: int) -> int:
        return sum(v for d, v in daily.items() if d <= day)

    ignition = next(
        (d for d in range(0, 40) if cum(d) >= IGNITION_MASS), None)
    funnel = payload.get("funnel_hosts") or {}
    inf_days = [
        r["infection_day"] for r in funnel.values()
        if r.get("infection_day") is not None
    ]
    med_inf = _median([float(d) for d in inf_days])
    takeoff = int(obs.get("recorded_onsets") or 0) >= TAKEOFF_MIN_ONSETS
    return {
        "seed": payload["cell"]["seed"],
        "theta": payload["cell"]["theta"],
        "arm_id": payload.get("arm_id") or payload["cell"].get("arm_id"),
        "takeoff": takeoff,
        "recorded_onsets": obs.get("recorded_onsets"),
        "infections_before_quarantine":
            payload.get("infections_before_quarantine"),
        "median_infection_day": med_inf,
        "record_timed": takeoff and med_inf is not None
        and med_inf <= RECORD_MEDIAN_DAY,
        "cum5": cum(5),
        "cum10": cum(10),
        "cum15": cum(15),
        "growth_fold_10_15": (cum(15) / cum(10)) if cum(10) else None,
        "ignition_day": ignition,
        "seed_spec": spec,
        "index_agent_id": host.get("agent_id"),
        "index_role": host.get("role"),
        "index_agent_class": host.get("agent_class"),
        "index_home_zone": host.get("home_zone"),
        "index_dining_zone": host.get("dining_zone"),
        "index_work_zone": host.get("work_zone"),
        "cabin_ring_size": host.get("cabin_ring_size"),
        "table_ring_size": host.get("table_ring_size"),
        "aboard_window_acquisitions":
            sr.get("aboard_window_acquisitions"),
        "aboard_window_clean_bound": sr.get("aboard_window_clean_bound"),
        "first_secondary_shed_day": (
            (sr["first_secondary_shed_epoch"] / 24.0)  # clock-exempt: epoch->day on the hourly clock
            if sr.get("first_secondary_shed_epoch") is not None else None),
        "index_departure_day": (
            (sr["index_departure_epoch"] / 24.0)  # clock-exempt: epoch->day on the hourly clock
            if sr.get("index_departure_epoch") is not None else None),
        "aboard_window_by_route": sr.get("aboard_window_by_route") or {},
        "aboard_window_by_day": sr.get("aboard_window_by_day") or {},
        "aboard_window_day0": (sr.get("aboard_window_by_day") or {})
        .get("0", 0),
    }


def _summarize(records: list[dict]) -> dict:
    yields_ = [r["aboard_window_acquisitions"] or 0 for r in records]
    route_totals: dict[str, int] = {}
    for r in records:
        for route, n in r["aboard_window_by_route"].items():
            route_totals[route] = route_totals.get(route, 0) + int(n)
    folds = [
        r["growth_fold_10_15"] for r in records
        if r["growth_fold_10_15"] is not None
    ]
    timed = [r for r in records if r["record_timed"]]
    late = [r for r in records if r["takeoff"] and not r["record_timed"]]
    dead = [r for r in records if not r["takeoff"]]

    def ymed(group: list[dict]) -> float | None:
        return _median([r["aboard_window_acquisitions"] or 0
                        for r in group])

    return {
        "n_cells": len(records),
        "n_takeoff": len(timed) + len(late),
        "founder_yield": {
            "median": _median(yields_),
            "min": min(yields_) if yields_ else None,
            "max": max(yields_) if yields_ else None,
        },
        "founder_yield_median_record_timed": ymed(timed),
        "founder_yield_median_late": ymed(late),
        "founder_yield_median_dead": ymed(dead),
        "aboard_window_route_totals": route_totals,
        "growth_fold_10_15_median": _median(folds),
        "n_record_timed": len(timed),
        "n_late": len(late),
        "n_dead": len(dead),
    }


def _md(records: list[dict], summary: dict) -> str:
    lines = [
        "# COVID-IGNITION-01 readout",
        "",
        f"- cells: {summary['n_cells']} "
        f"(takeoff {summary['n_takeoff']}, record-timed "
        f"{summary['n_record_timed']}, late {summary['n_late']}, "
        f"dead {summary['n_dead']})",
        f"- founder yield (aboard-window acquisitions): median "
        f"{summary['founder_yield']['median']}, "
        f"{summary['founder_yield']['min']}–"
        f"{summary['founder_yield']['max']}",
        f"- founder yield median: record-timed "
        f"{summary['founder_yield_median_record_timed']}, late "
        f"{summary['founder_yield_median_late']}, dead "
        f"{summary['founder_yield_median_dead']}",
        f"- aboard-window route totals: "
        f"{summary['aboard_window_route_totals']}",
        f"- post-founder growth (cum10->cum15 fold) median: "
        f"{summary['growth_fold_10_15_median']}",
        "",
        "| seed | takeoff | record-timed | founder | clean | day0 | "
        "cum5 | cum10 | cum15 | fold | ign | before | med inf |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(records, key=lambda x: -(x["infections_before_quarantine"] or 0)):
        lines.append(
            f"| {r['seed']} | {'T' if r['takeoff'] else 'F'} | "
            f"{'T' if r['record_timed'] else 'F'} | "
            f"{r['aboard_window_acquisitions']} | "
            f"{r['aboard_window_clean_bound']} | "
            f"{r['aboard_window_day0']} | {r['cum5']} | {r['cum10']} | "
            f"{r['cum15']} | {r['growth_fold_10_15']} | "
            f"{r['ignition_day']} | {r['infections_before_quarantine']} | "
            f"{r['median_infection_day']} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells", action="append", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--out-md", default=None)
    args = parser.parse_args(argv)

    paths: list[str] = []
    for root in args.cells:
        cells_dir = resolve_repo_path(str(_REPO_ROOT), root)
        paths.extend(sorted(glob.glob(str(Path(cells_dir) / "cell_*.json"))))
    if not paths:
        print("no cell_*.json payloads found", file=sys.stderr)
        return 1
    records = [_cell_record(p) for p in paths]
    summary = _summarize(records)
    evidence = {
        "cells": records,
        "summary": summary,
        "gates": {
            "takeoff_min_onsets": TAKEOFF_MIN_ONSETS,
            "ignition_mass": IGNITION_MASS,
            "record_median_day": RECORD_MEDIAN_DAY,
            "quarantine_day": QUARANTINE_DAY,
        },
    }
    out_path = Path(resolve_repo_path(str(_REPO_ROOT), args.out))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with validated_open(
        str(out_path), "w", allowed_roots=(str(_REPO_ROOT),)
    ) as fh:
        fh.write(json.dumps(evidence, indent=1))
    if args.out_md:
        md_path = Path(resolve_repo_path(str(_REPO_ROOT), args.out_md))
        with validated_open(
            str(md_path), "w", allowed_roots=(str(_REPO_ROOT),)
        ) as fh:
            fh.write(_md(records, summary))
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
