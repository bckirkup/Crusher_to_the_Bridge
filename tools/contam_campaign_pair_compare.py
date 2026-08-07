#!/usr/bin/env python3
"""
contam_campaign_pair_compare.py — join native vs ContamX campaign result zips.

Pairs on shared ``run_id`` (C13 Contam thin uses the same ids as C12c finecal
controls). Reads ``summary.json`` from each ``<run_id>.zip``.

Usage::

    python tools/contam_campaign_pair_compare.py \\
        --native-dir results/c12c_fine_calibration \\
        --contam-dir telemetry_buffer/c13_contam_thin \\
        --out-csv results/c13_contam_thin_pair_summary.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import zipfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_repo_path,
    validated_open,
)

_REPO_ROOT_STR = str(REPO_ROOT)

DERIVED_KEYS = (
    "attack_rate",
    "peak_prevalence",
    "outbreak_occurred",
    "peak_epoch",
    "detection_epoch",
    "detection_lag",
    "r_effective_at_peak",
    "total_quarantine_person_epochs",
    "final_susceptible_fraction",
)

PARAM_KEYS = (
    "platform_id",
    "pathogen",
    "dose_adjustment",
    "seed",
    "surveillance",
    "density_exponent",
    "num_agents",
    "num_epochs",
)


def _load_summary(zip_path: Path) -> dict[str, Any] | None:
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = [n for n in zf.namelist() if n.endswith("summary.json")]
            if not names:
                return None
            return json.loads(zf.read(names[0]).decode("utf-8"))
    except (zipfile.BadZipFile, json.JSONDecodeError, OSError) as exc:
        print(f"  WARN: skip {zip_path.name}: {exc}", file=sys.stderr)
        return None


def _index_zips(directory: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    if not directory.is_dir():
        return out
    for path in sorted(directory.glob("*.zip")):
        out[path.stem] = path
    return out


def _metric(summary: dict[str, Any], key: str) -> Any:
    derived = summary.get("derived") or {}
    if key in derived:
        return derived[key]
    # Fallback: SIR final infected / n_agents from parameters
    if key == "attack_rate":
        sir = summary.get("summary") or {}
        params = summary.get("parameters") or {}
        n = params.get("num_agents")
        infected = sir.get("n_infected")
        if n and infected is not None:
            return float(infected) / float(n)
    return None


def _param(summary: dict[str, Any], key: str) -> Any:
    params = summary.get("parameters") or {}
    return params.get(key)


def _delta(n_val: Any, c_val: Any) -> float | None:
    if isinstance(n_val, (int, float)) and isinstance(c_val, (int, float)):
        return float(c_val) - float(n_val)
    return None


def _build_pair_row(
    run_id: str,
    n_sum: dict[str, Any],
    c_sum: dict[str, Any],
) -> dict[str, Any]:
    row: dict[str, Any] = {"run_id": run_id}
    for key in PARAM_KEYS:
        # Prefer Contam params (includes transport_engine); fill from native
        val = _param(c_sum, key)
        if val is None:
            val = _param(n_sum, key)
        row[key] = val
    row["native_transport"] = _param(n_sum, "transport_engine") or "native"
    row["contam_transport"] = _param(c_sum, "transport_engine") or "contamx"
    for key in DERIVED_KEYS:
        n_val = _metric(n_sum, key)
        c_val = _metric(c_sum, key)
        row[f"native_{key}"] = n_val
        row[f"contam_{key}"] = c_val
        row[f"delta_{key}"] = _delta(n_val, c_val)
    return row


def _attack_rate_aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ar_deltas = [
        r["delta_attack_rate"]
        for r in rows
        if isinstance(r.get("delta_attack_rate"), (int, float))
    ]
    if not ar_deltas:
        return {}
    return {
        "delta_attack_rate_mean": statistics.mean(ar_deltas),
        "delta_attack_rate_median": statistics.median(ar_deltas),
        "delta_attack_rate_stdev": (
            statistics.stdev(ar_deltas) if len(ar_deltas) > 1 else 0.0
        ),
        "delta_attack_rate_min": min(ar_deltas),
        "delta_attack_rate_max": max(ar_deltas),
    }


def pair_rows(
    native_dir: Path,
    contam_dir: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    native_zips = _index_zips(native_dir)
    contam_zips = _index_zips(contam_dir)
    shared = sorted(set(native_zips) & set(contam_zips))
    native_only = sorted(set(native_zips) - set(contam_zips))
    contam_only = sorted(set(contam_zips) - set(native_zips))

    rows: list[dict[str, Any]] = []
    for run_id in shared:
        n_sum = _load_summary(native_zips[run_id])
        c_sum = _load_summary(contam_zips[run_id])
        if n_sum is None or c_sum is None:
            continue
        rows.append(_build_pair_row(run_id, n_sum, c_sum))

    aggregate: dict[str, Any] = {
        "n_native_zips": len(native_zips),
        "n_contam_zips": len(contam_zips),
        "n_paired": len(rows),
        "n_native_only": len(native_only),
        "n_contam_only": len(contam_only),
        "native_only_sample": native_only[:10],
        "contam_only_sample": contam_only[:10],
    }
    aggregate.update(_attack_rate_aggregate(rows))
    return rows, aggregate


def _resolve_cli_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return Path(resolve_repo_path(_REPO_ROOT_STR, str(path)))


def _csv_fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["run_id"]
    fieldnames = list(rows[0].keys())
    for row in rows[1:]:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    return fieldnames


def _write_pair_csv(out_csv: Path, rows: list[dict[str, Any]]) -> None:
    prepare_output_directory(
        str(out_csv.parent),
        allowed_roots=(_REPO_ROOT_STR,),
    )
    fieldnames = _csv_fieldnames(rows)
    with validated_open(
        str(out_csv),
        "w",
        allowed_roots=(_REPO_ROOT_STR,),
        encoding="utf-8",
        newline="",
    ) as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_pair_json(
    out_json: Path,
    aggregate: dict[str, Any],
    rows: list[dict[str, Any]],
) -> None:
    prepare_output_directory(
        str(out_json.parent),
        allowed_roots=(_REPO_ROOT_STR,),
    )
    payload = {"aggregate": aggregate, "rows": rows}
    with validated_open(
        str(out_json), "w", allowed_roots=(_REPO_ROOT_STR,), encoding="utf-8",
    ) as fh:
        json.dump(payload, fh, indent=2, default=str)
        fh.write("\n")


def _exit_code(rows: list[dict[str, Any]], aggregate: dict[str, Any]) -> int:
    """0 when pairs exist or Contam side is empty; 1 when Contam zips are unpaired."""
    if rows:
        return 0
    if aggregate["n_contam_zips"] == 0:
        return 0
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Pair native vs ContamX campaign result zips on run_id.",
    )
    parser.add_argument(
        "--native-dir",
        type=Path,
        required=True,
        help="Directory of native control <run_id>.zip files",
    )
    parser.add_argument(
        "--contam-dir",
        type=Path,
        required=True,
        help="Directory of ContamX <run_id>.zip files",
    )
    parser.add_argument(
        "--out-csv",
        type=Path,
        default=None,
        help="Write paired rows CSV (default: results/c13_contam_thin_pair_summary.csv)",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=None,
        help="Write aggregate + rows JSON",
    )
    args = parser.parse_args(argv)

    native_dir = _resolve_cli_path(args.native_dir)
    contam_dir = _resolve_cli_path(args.contam_dir)

    rows, aggregate = pair_rows(native_dir, contam_dir)
    print(json.dumps(aggregate, indent=2, default=str))
    if rows:
        mean_ar = aggregate.get("delta_attack_rate_mean")
        if mean_ar is not None:
            print(
                f"\n  paired={len(rows)}  "
                f"mean ΔAR (contam−native)={mean_ar:.4f}",
            )

    out_csv = args.out_csv
    if out_csv is None:
        out_csv = REPO_ROOT / "results" / "c13_contam_thin_pair_summary.csv"
    out_csv = _resolve_cli_path(out_csv)
    _write_pair_csv(out_csv, rows)
    print(f"  wrote {out_csv}")

    if args.out_json is not None:
        out_json = _resolve_cli_path(args.out_json)
        _write_pair_json(out_json, aggregate, rows)
        print(f"  wrote {out_json}")

    return _exit_code(rows, aggregate)


if __name__ == "__main__":
    raise SystemExit(main())
