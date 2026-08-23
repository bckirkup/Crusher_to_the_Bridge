#!/usr/bin/env python3
"""
aggregate_results.py — merge campaign shard bundles into one table.

After collecting the shard uploads locally, e.g.::

    aws s3 sync s3://<bucket>/campaign/ ./results/

run::

    python3 deploy/aws/aggregate_results.py ./results/ \
        --out-csv campaign_summary.csv --out-json campaign_summary.json

Each shard zip contains nested ``<run_id>/summary.json`` and
``<run_id>/timeseries.json`` files. Legacy flat single-run zips remain
supported, and shard manifests provide parameter/derived rows for runs whose
artifacts are not in a downloaded zip. Nested keys in ``summary`` and
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


def _row_from_summary(
    data: dict[str, Any],
    *,
    run_id: str,
    n_ts_epochs: int | None,
) -> dict[str, Any]:
    row: dict[str, Any] = {"run_id": str(data.get("run_id") or run_id)}
    row["num_epochs"] = data.get("num_epochs")
    row["trigger_status"] = data.get("trigger_status")
    row.update(flatten(data.get("parameters", {}), "parameters"))
    row.update(flatten(data.get("summary", {}), "summary"))
    row.update(flatten(data.get("cost_accounting", {}), "cost"))
    row.update(flatten(data.get("derived", {}), "derived"))
    row["timeseries.present"] = n_ts_epochs is not None
    row["timeseries.n_epochs"] = n_ts_epochs
    return row


def _zip_groups(names: list[str]) -> dict[str, dict[str, str]]:
    groups: dict[str, dict[str, str]] = {}
    for name in names:
        path = Path(name)
        if path.name not in {"summary.json", "timeseries.json"}:
            continue
        groups.setdefault(str(path.parent), {})[path.name] = name
    return groups


def iter_summary_rows(zip_path: Path):
    """Yield one flattened row for each summary/timeseries pair in a zip.

    Older zips carry only ``summary`` / ``cost_accounting``; newer ones also
    carry ``derived`` scalar metrics, a ``parameters`` factor block, plus a
    separate ``timeseries.json``. All are handled; missing sections just leave
    those columns blank.
    """
    try:
        with zipfile.ZipFile(zip_path) as zf:
            for prefix, group in _zip_groups(zf.namelist()).items():
                try:
                    data = json.loads(
                        zf.read(group["summary.json"]).decode("utf-8"),
                    )
                except (KeyError, json.JSONDecodeError, UnicodeDecodeError):
                    continue
                n_ts_epochs: int | None = None
                ts_name = group.get("timeseries.json")
                if ts_name:
                    try:
                        ts = json.loads(zf.read(ts_name).decode("utf-8"))
                        n_ts_epochs = len(ts) if isinstance(ts, list) else None
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # Keep rows when optional timeseries data is malformed.
                        pass
                fallback = Path(prefix).name if prefix != "." else zip_path.stem
                yield _row_from_summary(
                    data,
                    run_id=fallback,
                    n_ts_epochs=n_ts_epochs,
                )
    except zipfile.BadZipFile:
        print(f"  WARN: {zip_path.name} is not a valid zip; skipping", file=sys.stderr)


def summary_from_zip(zip_path: Path) -> dict[str, Any] | None:
    """Return the first flattened run row from a zip, or None if absent."""
    return next(iter_summary_rows(zip_path), None)


def _manifest_rows(path: Path):
    try:
        with validated_open(
            str(path),
            encoding="utf-8",
            allowed_roots=(str(path.parents[0]),),
        ) as fh:
            entries = json.load(fh)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return
    if not isinstance(entries, list):
        return
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("run_id"), str):
            continue
        yield _row_from_summary(
            entry,
            run_id=entry["run_id"],
            n_ts_epochs=None,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate campaign shard bundles")
    parser.add_argument("results_dir", type=Path, help="Directory of shard zips and manifests")
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
    seen_run_ids: set[str] = set()
    for zp in zips:
        for row in iter_summary_rows(zp):
            run_id = str(row["run_id"])
            if run_id in seen_run_ids:
                continue
            seen_run_ids.add(run_id)
            rows.append(row)
    for manifest_path in sorted(results_dir.rglob("*.manifest.json")):
        for row in _manifest_rows(manifest_path):
            run_id = str(row["run_id"])
            if run_id in seen_run_ids:
                continue
            seen_run_ids.add(run_id)
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
