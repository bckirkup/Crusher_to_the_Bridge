#!/usr/bin/env python3
"""
aggregate_results.py — merge per-run campaign result zips into one table.

After collecting the shard uploads locally, e.g.::

    aws s3 sync s3://<bucket>/campaign/ ./results/

run::

    python3 deploy/aws/aggregate_results.py ./results/ \
        --out-csv campaign_summary.csv --out-json campaign_summary.json

Each ``<run_id>.zip`` is expected to contain ``summary.json`` (written by
campaign_runner.run_simulation). Nested keys in ``summary`` and
``cost_accounting`` are flattened with dotted names so they land in one row.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from deploy.aws.path_safety import cwd_root, safe_path  # noqa: E402
from simulation_utils.paths import validated_open  # noqa: E402


def flatten(obj: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten nested dicts into dotted keys; scalars pass through."""
    flat: dict[str, Any] = {}
    if isinstance(obj, dict):
        for key, value in obj.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            flat.update(flatten(value, name))
    elif isinstance(obj, list):
        flat[prefix] = json.dumps(obj)
    else:
        flat[prefix] = obj
    return flat


def summary_from_zip(zip_path: Path) -> dict[str, Any] | None:
    """Read and flatten summary.json from a run zip, or None if absent.

    Older zips carry only ``summary`` / ``cost_accounting``; newer ones also
    carry ``derived`` scalar metrics, a ``parameters`` factor block, plus a
    separate ``timeseries.json``. All are handled; missing sections just leave
    those columns blank.
    """
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = [n for n in zf.namelist() if n.endswith("summary.json")]
            if not names:
                return None
            raw = zf.read(names[0]).decode("utf-8")
            ts_names = [n for n in zf.namelist() if n.endswith("timeseries.json")]
            n_ts_epochs: int | None = None
            if ts_names:
                try:
                    ts = json.loads(zf.read(ts_names[0]).decode("utf-8"))
                    n_ts_epochs = len(ts) if isinstance(ts, list) else None
                except json.JSONDecodeError:
                    n_ts_epochs = None
    except zipfile.BadZipFile:
        print(f"  WARN: {zip_path.name} is not a valid zip; skipping", file=sys.stderr)
        return None
    data = json.loads(raw)
    row: dict[str, Any] = {"run_id": data.get("run_id", zip_path.stem)}
    row["num_epochs"] = data.get("num_epochs")
    row["trigger_status"] = data.get("trigger_status")
    row.update(flatten(data.get("parameters", {}), "parameters"))
    row.update(flatten(data.get("summary", {}), "summary"))
    row.update(flatten(data.get("cost_accounting", {}), "cost"))
    row.update(flatten(data.get("derived", {}), "derived"))
    row["timeseries.present"] = n_ts_epochs is not None
    row["timeseries.n_epochs"] = n_ts_epochs
    return row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate campaign result zips")
    parser.add_argument("results_dir", type=Path, help="Directory of <run_id>.zip files")
    parser.add_argument("--out-csv", type=Path, default=Path("campaign_summary.csv"))
    parser.add_argument("--out-json", type=Path, default=Path("campaign_summary.json"))
    args = parser.parse_args(argv)

    # Canonicalize + confine all CLI-derived paths to the invocation directory.
    cwd = cwd_root()
    roots = (cwd,)
    results_dir = Path(safe_path(args.results_dir))
    out_csv = safe_path(args.out_csv)
    out_json = safe_path(args.out_json)

    if not results_dir.is_dir():
        raise SystemExit(f"Not a directory: {results_dir}")

    zips = sorted(results_dir.rglob("*.zip"))
    print(f"Found {len(zips)} zip(s) under {results_dir}")

    rows: list[dict[str, Any]] = []
    for zp in zips:
        row = summary_from_zip(zp)
        if row is not None:
            rows.append(row)

    if not rows:
        print("No summaries found; nothing written.", file=sys.stderr)
        return 1

    # Stable, union-of-all-keys column order (run_id first).
    columns: list[str] = ["run_id"]
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)

    with validated_open(out_json, "w", allowed_roots=roots, encoding="utf-8") as fh:
        json.dump(rows, fh, indent=2)

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    with validated_open(out_csv, "w", allowed_roots=roots, encoding="utf-8") as fh:
        fh.write(buf.getvalue())

    print(f"Wrote {len(rows)} rows -> {out_csv} and {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
