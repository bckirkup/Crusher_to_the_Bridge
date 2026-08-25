"""Build a standardized campaign analysis bundle from result zips.

Usage::

    python3 -m picard_framework.analysis.campaign_bundle RESULTS_DIR --out analysis/
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from picard_framework.analysis._io import (
    ensure_out_dir,
    iter_result_zips,
    load_run_zip,
    safe_path,
    write_csv,
    write_json,
    write_timeseries_table,
)
from picard_framework.analysis.figures import write_standard_figures
from picard_framework.analysis.metrics import (
    RUN_SUMMARY_COLUMNS,
    build_aggregate_metrics,
    build_epoch_rows,
    build_factor_dictionary,
    build_run_summary_row,
    epoch_table_columns,
)
from picard_framework.analysis.pairwise import build_pairwise_deltas, write_pairwise_csv
from picard_framework.analysis.phylodynamics.campaign import write_campaign_tables


def build_bundle(results_dir: str, out_dir: str) -> dict[str, Any]:
    """Parse all campaign zips under ``results_dir`` into an analysis bundle.

    Returns a small manifest describing written artifacts.
    """
    out = ensure_out_dir(out_dir)
    run_rows: list[dict[str, Any]] = []
    epoch_rows: list[dict[str, Any]] = []
    skipped = 0

    for zip_path in iter_result_zips(results_dir):
        payload = load_run_zip(zip_path)
        if payload is None:
            skipped += 1
            print(f"  WARN: skip unreadable zip {os.path.basename(zip_path)}", file=sys.stderr)
            continue
        summary_row = build_run_summary_row(payload)
        run_rows.append(summary_row)
        epoch_rows.extend(build_epoch_rows(payload, summary_row))

    if not run_rows:
        raise SystemExit("No campaign summaries found; nothing written.")

    write_csv(os.path.join(out, "run_summary.csv"), run_rows, RUN_SUMMARY_COLUMNS)
    ts_name = write_timeseries_table(out, epoch_rows, epoch_table_columns())

    factor_dict = build_factor_dictionary(run_rows)
    aggregate = build_aggregate_metrics(run_rows)
    write_json(os.path.join(out, "factor_dictionary.json"), factor_dict)
    write_json(os.path.join(out, "aggregate_metrics.json"), aggregate)

    pairwise_rows = build_pairwise_deltas(run_rows, epoch_rows)
    pairwise_name = None
    if pairwise_rows:
        pairwise_name = write_pairwise_csv(out, pairwise_rows)

    fig_names = write_standard_figures(out, run_rows, epoch_rows)
    phylo = write_campaign_tables(out, results_dir)

    manifest = {
        "n_runs": len(run_rows),
        "n_epoch_rows": len(epoch_rows),
        "skipped_zips": skipped,
        "artifacts": {
            "run_summary": "run_summary.csv",
            "epoch_timeseries": ts_name,
            "factor_dictionary": "factor_dictionary.json",
            "aggregate_metrics": "aggregate_metrics.json",
            "pairwise_deltas": pairwise_name,
            "figures": fig_names,
            **phylo["artifacts"],
        },
        "phylodynamics": {
            key: value for key, value in phylo.items() if key != "artifacts"
        },
    }
    write_json(os.path.join(out, "bundle_manifest.json"), manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a standardized campaign analysis bundle from result zips",
    )
    parser.add_argument(
        "results_dir",
        help="Directory of <run_id>.zip campaign outputs",
    )
    parser.add_argument(
        "--out",
        default="analysis",
        help="Output directory for the analysis bundle (default: analysis/)",
    )
    args = parser.parse_args(argv)

    results_dir = safe_path(args.results_dir)
    out_dir = safe_path(args.out)
    manifest = build_bundle(results_dir, out_dir)
    print(
        f"Wrote bundle for {manifest['n_runs']} run(s) → {out_dir} "
        f"({manifest['n_epoch_rows']} epoch rows)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
