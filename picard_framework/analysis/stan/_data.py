"""Shared helpers for norovirus Stan data prep (outbreak + trajectory)."""

from __future__ import annotations

import csv
import gzip
import os
from typing import Any

from picard_framework.analysis._io import allowed_roots
from picard_framework.analysis.metrics import coerce_bool, encode_trigger_status
from picard_framework.analysis.parse_run_id import is_norovirus
from simulation_utils.paths import validated_open

DEFAULT_D0 = 10.6
DEFAULT_VSP_REF = 0.05


def read_csv(path: str) -> list[dict[str, Any]]:
    with validated_open(
        path, allowed_roots=allowed_roots(), encoding="utf-8", newline=""
    ) as fh:
        return list(csv.DictReader(fh))


def read_epoch_table(analysis_dir: str) -> list[dict[str, Any]]:
    parquet_path = os.path.join(analysis_dir, "epoch_timeseries.parquet")
    gz_path = os.path.join(analysis_dir, "epoch_timeseries.csv.gz")
    csv_path = os.path.join(analysis_dir, "epoch_timeseries.csv")

    if os.path.isfile(parquet_path):
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq

            with validated_open(parquet_path, "rb", allowed_roots=allowed_roots()) as fh:
                data = fh.read()
            table = pq.read_table(pa.BufferReader(data))
            return table.to_pylist()
        except ImportError:
            pass

    if os.path.isfile(gz_path):
        with validated_open(gz_path, "rb", allowed_roots=allowed_roots()) as raw:
            with gzip.GzipFile(fileobj=raw, mode="rb") as gz:
                text = gz.read().decode("utf-8").splitlines()
        return list(csv.DictReader(text))

    if os.path.isfile(csv_path):
        return read_csv(csv_path)

    raise FileNotFoundError(
        f"No epoch_timeseries table under {analysis_dir} "
        "(expected .parquet, .csv.gz, or .csv)"
    )


def as_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def as_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def filter_norovirus_runs(run_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        r
        for r in run_rows
        if is_norovirus(r.get("pathogen"), r.get("pathogen_id"))
    ]


def filter_outbreak_runs(run_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in run_rows if coerce_bool(r.get("outbreak_occurred"))]


def _vsp_threshold_value(row: dict[str, Any]) -> float:
    thr = row.get("vsp_lockdown_threshold")
    if thr in (None, "", "never"):
        return 1.0
    return as_float(thr, 1.0)


def _factor_indices(
    rows: list[dict[str, Any]],
) -> tuple[list[str], list[str], dict[str, int], dict[str, int]]:
    platforms = sorted({str(r.get("platform_id") or "unknown") for r in rows})
    surveillances = sorted(
        {str(r.get("surveillance_strategy") or "none") for r in rows}
    )
    plat_idx = {p: i + 1 for i, p in enumerate(platforms)}
    surv_idx = {s: i + 1 for i, s in enumerate(surveillances)}
    return platforms, surveillances, plat_idx, surv_idx


def build_outbreak_stan_data(
    run_rows: list[dict[str, Any]],
    *,
    d0: float = DEFAULT_D0,
    vsp_ref: float = DEFAULT_VSP_REF,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Stage A: run-level Bernoulli outbreak data (norovirus only)."""
    noro = filter_norovirus_runs(run_rows)
    if not noro:
        raise ValueError("No norovirus runs found in run_summary")

    platforms, surveillances, plat_idx, surv_idx = _factor_indices(noro)
    N_runs = len(noro)
    data = {
        "N_runs": N_runs,
        "P": len(platforms),
        "S": len(surveillances),
        "outbreak": [1 if coerce_bool(r.get("outbreak_occurred")) else 0 for r in noro],
        "platform": [plat_idx[str(r.get("platform_id") or "unknown")] for r in noro],
        "surveillance": [
            surv_idx[str(r.get("surveillance_strategy") or "none")] for r in noro
        ],
        "dose_adj": [as_float(r.get("dose_adjustment"), d0) for r in noro],
        "vsp_threshold": [_vsp_threshold_value(r) for r in noro],
        "d0": float(d0),
        "vsp_ref": float(vsp_ref),
    }
    meta = {
        "stage": "outbreak",
        "platforms": platforms,
        "surveillances": surveillances,
        "run_ids": [str(r["run_id"]) for r in noro],
        "d0": float(d0),
        "vsp_ref": float(vsp_ref),
        "N_runs": N_runs,
        "n_outbreaks": int(sum(data["outbreak"])),
        "outbreak_rate": round(sum(data["outbreak"]) / N_runs, 4),
    }
    return data, meta


def build_trajectory_stan_data(
    run_rows: list[dict[str, Any]],
    epoch_rows: list[dict[str, Any]],
    *,
    d0: float = DEFAULT_D0,
    vsp_ref: float = DEFAULT_VSP_REF,
    outbreaks_only: bool = True,
    grainsize: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Stage B: epoch NegBin trajectory data (norovirus, optionally outbreaks only)."""
    noro = filter_norovirus_runs(run_rows)
    if outbreaks_only:
        noro = filter_outbreak_runs(noro)
    if not noro:
        raise ValueError("No norovirus runs found for trajectory stage")

    run_ids = [str(r["run_id"]) for r in noro]
    run_index = {rid: i for i, rid in enumerate(run_ids)}
    platforms, surveillances, plat_idx, surv_idx = _factor_indices(noro)

    epochs_by_run: dict[str, dict[int, dict[str, Any]]] = {rid: {} for rid in run_ids}
    max_epoch = 0
    for row in epoch_rows:
        rid = str(row.get("run_id"))
        if rid not in run_index:
            continue
        ep = as_int(row.get("epoch"), -1)
        if ep < 0:
            continue
        epochs_by_run[rid][ep] = row
        max_epoch = max(max_epoch, ep)
    T = max_epoch + 1
    if T < 1:
        raise ValueError("No epoch rows for trajectory runs")

    N_runs = len(noro)
    gs = grainsize if grainsize is not None else max(1, N_runs // 8)

    def _mat(field: str, default: int = 0) -> list[list[int]]:
        mat = [[default for _ in range(T)] for _ in range(N_runs)]
        for rid, by_ep in epochs_by_run.items():
            ri = run_index[rid]
            for t in range(T):
                point = by_ep.get(t)
                if point is None:
                    continue
                if field == "trigger_state":
                    if "trigger_state" in point and point["trigger_state"] != "":
                        mat[ri][t] = as_int(point["trigger_state"], 0)
                    else:
                        mat[ri][t] = encode_trigger_status(point.get("trigger_status"))
                else:
                    mat[ri][t] = as_int(point.get(field), default)
        return mat

    data = {
        "N_runs": N_runs,
        "T": T,
        "P": len(platforms),
        "S": len(surveillances),
        "grainsize": int(gs),
        "N_agents": [as_int(r.get("num_agents"), 1) for r in noro],
        "platform": [plat_idx[str(r.get("platform_id") or "unknown")] for r in noro],
        "surveillance": [
            surv_idx[str(r.get("surveillance_strategy") or "none")] for r in noro
        ],
        "dose_adj": [as_float(r.get("dose_adjustment"), d0) for r in noro],
        "vsp_threshold": [_vsp_threshold_value(r) for r in noro],
        "seed": [as_int(r.get("seed"), 0) for r in noro],
        "infected": _mat("infected"),
        "symptomatic": _mat("symptomatic"),
        "recovered": _mat("recovered"),
        "new_infections": _mat("new_infections"),
        "quarantined": _mat("quarantined"),
        "trigger_state": _mat("trigger_state"),
        "d0": float(d0),
        "vsp_ref": float(vsp_ref),
    }
    meta = {
        "stage": "trajectory",
        "outbreaks_only": outbreaks_only,
        "platforms": platforms,
        "surveillances": surveillances,
        "run_ids": run_ids,
        "d0": float(d0),
        "vsp_ref": float(vsp_ref),
        "N_runs": N_runs,
        "T": T,
        "grainsize": int(gs),
    }
    return data, meta


def cmdstan_available() -> bool:
    try:
        import cmdstanpy  # noqa: F401
        from cmdstanpy import cmdstan_path

        try:
            cmdstan_path()
            return True
        except Exception:
            return False
    except ImportError:
        return False
