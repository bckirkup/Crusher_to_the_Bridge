"""Build Step-2 Stan bundle: C12c + C14/C14b combined, with norovirus subsample.

Usage (from repo root)::

    python -u scripts/build_stan_step2_bundle.py
"""

from __future__ import annotations

import csv
import os
import random
import sys
from collections import defaultdict

import pyarrow.parquet as pq

from picard_framework.analysis._io import (
    ensure_out_dir,
    write_csv,
    write_json,
    write_timeseries_table,
)
from picard_framework.analysis.metrics import (
    RUN_SUMMARY_COLUMNS,
    build_aggregate_metrics,
    epoch_table_columns,
)
from picard_framework.analysis.parse_run_id import is_norovirus

ROOT = os.getcwd()
SOURCES = (
    ("c12c_fine_calibration", os.path.join(ROOT, "analysis", "c12c_fine_calibration")),
    ("c14", os.path.join(ROOT, "analysis", "c14")),
    ("c14b", os.path.join(ROOT, "analysis", "c14b")),
)
OUT = os.path.join(ROOT, "analysis", "analysis_stan_norovirus")
MAX_STAN_RUNS = 800
SEED = 1701


def read_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def stratified_sample(rows: list[dict], k: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        key = (
            str(r.get("analysis_source") or r.get("campaign") or ""),
            str(r.get("platform_id") or ""),
            str(r.get("surveillance_strategy") or ""),
            str(r.get("dose_adjustment") or ""),
            str(r.get("vsp_lockdown_threshold") or ""),
        )
        buckets[key].append(r)
    for key in buckets:
        # Seeded stratified subsample for Stan — not crypto/auth (python:S2245).
        rng.shuffle(buckets[key])  # NOSONAR
    keys = sorted(buckets.keys())
    chosen: list[dict] = []
    while len(chosen) < k and keys:
        progressed = False
        for key in list(keys):
            if buckets[key]:
                chosen.append(buckets[key].pop())
                progressed = True
                if len(chosen) >= k:
                    break
            else:
                keys.remove(key)
        if not progressed:
            break
    return chosen


def main() -> int:
    run_rows: list[dict] = []
    epoch_rows: list[dict] = []
    for label, src in SOURCES:
        rs_path = os.path.join(src, "run_summary.csv")
        if not os.path.isfile(rs_path):
            print(f"MISSING {rs_path}", file=sys.stderr)
            return 1
        print(f"loading {label} …", flush=True)
        runs = read_csv(rs_path)
        for r in runs:
            r["analysis_source"] = label
            for key in (
                "detection_epoch",
                "confirmation_epoch",
                "detection_lag",
                "attack_rate",
                "peak_prevalence",
                "peak_epoch",
            ):
                if r.get(key) == "":
                    r[key] = None
        run_rows.extend(runs)
        table = pq.read_table(os.path.join(src, "epoch_timeseries.parquet"))
        for row in table.to_pylist():
            row["analysis_source"] = label
            epoch_rows.append(row)
        print(f"  {len(runs)} runs", flush=True)

    ensure_out_dir(OUT)
    # Keep RUN_SUMMARY_COLUMNS order; analysis_source is extra metadata in JSON only.
    write_csv(os.path.join(OUT, "run_summary.csv"), run_rows, RUN_SUMMARY_COLUMNS)
    ts_name = write_timeseries_table(OUT, epoch_rows, epoch_table_columns())
    agg = build_aggregate_metrics(run_rows)
    agg["sources"] = [s[0] for s in SOURCES]
    write_json(os.path.join(OUT, "aggregate_metrics.json"), agg)
    write_json(
        os.path.join(OUT, "bundle_manifest.json"),
        {
            "n_runs": len(run_rows),
            "n_epoch_rows": len(epoch_rows),
            "sources": [s[0] for s in SOURCES],
            "artifacts": {
                "run_summary": "run_summary.csv",
                "epoch_timeseries": ts_name,
                "aggregate_metrics": "aggregate_metrics.json",
            },
        },
    )
    print(
        f"full bundle: {len(run_rows)} runs, {len(epoch_rows)} epochs → {OUT}",
        flush=True,
    )
    print(f"  outbreak_rate={agg.get('outbreak_rate')}", flush=True)

    noro = [r for r in run_rows if is_norovirus(r.get("pathogen"), r.get("pathogen_id"))]
    sample = (
        noro if len(noro) <= MAX_STAN_RUNS else stratified_sample(noro, MAX_STAN_RUNS, SEED)
    )
    ids = {r["run_id"] for r in sample}
    sample_epochs = [e for e in epoch_rows if str(e.get("run_id")) in ids]
    sample_out = os.path.join(OUT, "stan_sample")
    ensure_out_dir(sample_out)
    write_csv(os.path.join(sample_out, "run_summary.csv"), sample, RUN_SUMMARY_COLUMNS)
    sample_ts = write_timeseries_table(sample_out, sample_epochs, epoch_table_columns())
    write_json(
        os.path.join(sample_out, "bundle_manifest.json"),
        {
            "n_runs": len(sample),
            "n_epoch_rows": len(sample_epochs),
            "n_norovirus_source": len(noro),
            "subsample_max": MAX_STAN_RUNS,
            "seed": SEED,
            "artifacts": {
                "run_summary": "run_summary.csv",
                "epoch_timeseries": sample_ts,
            },
        },
    )
    by_src: dict[str, int] = defaultdict(int)
    for r in sample:
        by_src[str(r.get("analysis_source") or "?")] += 1
    print(
        f"stan_sample: {len(sample)}/{len(noro)} noro {dict(by_src)} → {sample_out}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
