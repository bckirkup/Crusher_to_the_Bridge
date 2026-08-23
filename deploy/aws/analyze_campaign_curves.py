#!/usr/bin/env python3
"""
analyze_campaign_curves.py — stack campaign shard curves into long-form tables.

After ``aggregate_results.py`` builds the scalar summary CSV, use this to pull
epidemic curves out of every shard zip for notebooks / plotting:

    python3 deploy/aws/analyze_campaign_curves.py ./results/ \
        --out-csv campaign_curves.csv \
        --out-frontiers campaign_frontiers.csv

Outputs:
  * ``--out-csv`` — one row per (run_id, epoch) with infected/recovered/…
    plus parsed sweep tags (oa*, imm*, comp*, init*) and summary ``derived``
    scalars repeated on each epoch row.
  * ``--out-frontiers`` — one row per run with attack_rate / peak_prevalence
    and the same sweep tags (for OA × immunity / compliance frontiers).
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any, Iterator

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from deploy.aws.path_safety import cwd_root, safe_path  # noqa: E402
from simulation_utils.paths import confine_to_base, validated_open  # noqa: E402

_TAG_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("oa", re.compile(r"(oa\d+)")),
    ("imm", re.compile(r"(imm\d+)")),
    ("comp", re.compile(r"(comp\d+)")),
    ("init", re.compile(r"(init\d+)")),
    ("filter", re.compile(r"_(merv\d+|hepa)_")),
    ("decay", re.compile(r"_(low|med|high|vhigh)_")),
)


def parse_run_tags(run_id: str) -> dict[str, str | None]:
    """Extract common campaign sweep tags from a run_id."""
    tags: dict[str, str | None] = dict.fromkeys(name for name, _ in _TAG_PATTERNS)
    for name, pat in _TAG_PATTERNS:
        m = pat.search(run_id)
        if m:
            tags[name] = m.group(1)
    return tags


def _zip_groups(names: list[str]) -> dict[str, dict[str, str]]:
    groups: dict[str, dict[str, str]] = {}
    for name in names:
        path = Path(name)
        if path.name not in {"summary.json", "timeseries.json"}:
            continue
        groups.setdefault(str(path.parent), {})[path.name] = name
    return groups


def iter_curve_rows(results_dir: Path) -> Iterator[dict[str, Any]]:
    """Yield long-form epoch rows for every run in each shard zip."""
    emitted_run_ids: set[str] = set()
    for zip_path in sorted(results_dir.rglob("*.zip")):
        try:
            with zipfile.ZipFile(zip_path) as zf:
                for prefix, group in _zip_groups(zf.namelist()).items():
                    ts_name = group.get("timeseries.json")
                    if not ts_name:
                        continue
                    try:
                        ts = json.loads(zf.read(ts_name).decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue
                    if not isinstance(ts, list):
                        continue

                    summary: dict[str, Any] = {}
                    sum_name = group.get("summary.json")
                    if sum_name:
                        try:
                            summary = json.loads(
                                zf.read(sum_name).decode("utf-8"),
                            )
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            summary = {}

                    fallback = Path(prefix).name if prefix != "." else zip_path.stem
                    run_id = str(summary.get("run_id") or fallback)
                    if run_id in emitted_run_ids:
                        continue
                    emitted_run_ids.add(run_id)
                    derived = summary.get("derived") or {}
                    tags = parse_run_tags(run_id)
                    for point in ts:
                        if not isinstance(point, dict):
                            continue
                        row: dict[str, Any] = {
                            "run_id": run_id,
                            "epoch": point.get("epoch"),
                            "susceptible": point.get("susceptible"),
                            "infected": point.get("infected"),
                            "symptomatic": point.get("symptomatic"),
                            "recovered": point.get("recovered"),
                            "immune": point.get("immune"),
                            "quarantined": point.get("quarantined"),
                            "isolated": point.get("isolated"),
                            "new_infections": point.get("new_infections"),
                            "total_pathogen_mass": point.get("total_pathogen_mass"),
                            "n_zones_contaminated": point.get("n_zones_contaminated"),
                            "max_concentration": point.get("max_concentration"),
                            "cumulative_cost_usd": point.get("cumulative_cost_usd"),
                            "cumulative_ois": point.get("cumulative_ois"),
                            "trigger_status": point.get("trigger_status"),
                            "attack_rate": derived.get("attack_rate"),
                            "peak_prevalence": derived.get("peak_prevalence"),
                            "peak_epoch": derived.get("peak_epoch"),
                            "detection_epoch": derived.get("detection_epoch"),
                            "r_effective_at_peak": derived.get("r_effective_at_peak"),
                        }
                        row.update(tags)
                        yield row
        except zipfile.BadZipFile:
            print(f"  WARN: {zip_path.name} is not a valid zip; skipping", file=sys.stderr)


def frontier_rows(curve_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse long-form curves to one scalar frontier row per run_id."""
    by_run: dict[str, dict[str, Any]] = {}
    for row in curve_rows:
        rid = str(row["run_id"])
        if rid in by_run:
            continue
        by_run[rid] = {
            "run_id": rid,
            "oa": row.get("oa"),
            "imm": row.get("imm"),
            "comp": row.get("comp"),
            "init": row.get("init"),
            "filter": row.get("filter"),
            "decay": row.get("decay"),
            "attack_rate": row.get("attack_rate"),
            "peak_prevalence": row.get("peak_prevalence"),
            "peak_epoch": row.get("peak_epoch"),
            "detection_epoch": row.get("detection_epoch"),
            "r_effective_at_peak": row.get("r_effective_at_peak"),
        }
    return list(by_run.values())


def _write_csv(path: str, rows: list[dict[str, Any]]) -> None:
    roots = (cwd_root(),)
    safe = confine_to_base(roots[0], path)
    if not rows:
        with validated_open(safe, "w", allowed_roots=roots, encoding="utf-8") as fh:
            fh.write("")
        return
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    with validated_open(safe, "w", allowed_roots=roots, encoding="utf-8") as fh:
        fh.write(buf.getvalue())


def write_outputs(
    results_dir: Path,
    out_csv: str,
    out_frontiers: str,
) -> int:
    rows = list(iter_curve_rows(results_dir))
    _write_csv(out_csv, rows)
    _write_csv(out_frontiers, frontier_rows(rows))
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stack campaign timeseries.json files into long-form CSVs",
    )
    parser.add_argument("results_dir", type=Path, help="Directory of shard zips")
    parser.add_argument(
        "--out-csv", type=Path, default=Path("campaign_curves.csv"),
        help="Long-form per-epoch CSV (default campaign_curves.csv)",
    )
    parser.add_argument(
        "--out-frontiers", type=Path, default=Path("campaign_frontiers.csv"),
        help="Per-run scalar frontier CSV (default campaign_frontiers.csv)",
    )
    args = parser.parse_args(argv)

    results_dir = Path(safe_path(args.results_dir))
    out_csv = safe_path(args.out_csv)
    out_frontiers = safe_path(args.out_frontiers)
    if not results_dir.is_dir():
        raise SystemExit(f"Not a directory: {results_dir}")

    n = write_outputs(results_dir, out_csv, out_frontiers)
    if n == 0:
        print("No timeseries found; nothing written.", file=sys.stderr)
        return 1
    print(f"Wrote {n} epoch-rows -> {out_csv}")
    print(f"Wrote frontiers -> {out_frontiers}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
