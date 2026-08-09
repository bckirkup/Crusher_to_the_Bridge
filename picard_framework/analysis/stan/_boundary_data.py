"""Shared helpers for boundary-pipeline Stan (Bernoulli + Beta-AR)."""
from __future__ import annotations

import math
from typing import Any

from picard_framework.analysis.metrics import coerce_bool
from picard_framework.analysis.parse_run_id import is_norovirus, resolve_initial_infected
from picard_framework.analysis.stan._data import (
    DEFAULT_D0,
    as_float,
    as_int,
    cmdstan_available,
    filter_outbreak_runs,
    read_csv,
)

# Re-export for callers
__all__ = [
    "DEFAULT_D0",
    "build_boundary_ar_stan_data",
    "build_boundary_outbreak_stan_data",
    "cmdstan_available",
    "filter_pathogen_runs",
    "matches_pathogen",
    "read_csv",
]

_PATHOGEN_TOKENS: dict[str, tuple[str, ...]] = {
    "norovirus": ("noro", "norwalk"),
    "sarscov2": ("sarscov2", "sars_cov2", "sars-cov-2", "covid"),
    "sars_cov2": ("sarscov2", "sars_cov2", "sars-cov-2", "covid"),
    "influenza": ("influenza", "flu"),
    "measles": ("measles",),
}


def matches_pathogen(
    pathogen_key: str,
    pathogen: str | None,
    pathogen_id: str | None = None,
) -> bool:
    key = str(pathogen_key or "").strip().lower().replace("-", "_")
    if key in {"noro", "norwalk"}:
        key = "norovirus"
    if key in {"covid", "covid19", "sars_cov_2"}:
        key = "sarscov2"
    if key == "norovirus":
        return is_norovirus(pathogen, pathogen_id)
    tokens = _PATHOGEN_TOKENS.get(key, (key,))
    for value in (pathogen, pathogen_id):
        if value is None:
            continue
        token = str(value).strip().lower().replace("-", "_")
        if any(t.replace("-", "_") in token for t in tokens):
            return True
    return False


def filter_pathogen_runs(
    run_rows: list[dict[str, Any]],
    pathogen: str,
) -> list[dict[str, Any]]:
    return [
        r
        for r in run_rows
        if matches_pathogen(pathogen, r.get("pathogen"), r.get("pathogen_id"))
    ]


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


def _log_k(row: dict[str, Any]) -> float:
    k = resolve_initial_infected(
        parameters=row,
        run_id=str(row.get("run_id") or ""),
    )
    if k is None:
        k = as_int(row.get("initial_infected"), 0)
    return math.log(max(int(k), 1))


def build_boundary_outbreak_stan_data(
    run_rows: list[dict[str, Any]],
    *,
    pathogen: str,
    d0: float = DEFAULT_D0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    rows = filter_pathogen_runs(run_rows, pathogen)
    if not rows:
        raise ValueError(f"No runs found for pathogen={pathogen!r}")

    platforms, surveillances, plat_idx, surv_idx = _factor_indices(rows)
    N_runs = len(rows)
    data = {
        "N_runs": N_runs,
        "P": len(platforms),
        "S": len(surveillances),
        "outbreak": [1 if coerce_bool(r.get("outbreak_occurred")) else 0 for r in rows],
        "platform": [plat_idx[str(r.get("platform_id") or "unknown")] for r in rows],
        "surveillance": [
            surv_idx[str(r.get("surveillance_strategy") or "none")] for r in rows
        ],
        "log_k": [_log_k(r) for r in rows],
        "dose_adj": [as_float(r.get("dose_adjustment"), d0) for r in rows],
        "d0": float(d0),
    }
    meta = {
        "stage": "boundary_outbreak",
        "pathogen": pathogen,
        "platforms": platforms,
        "surveillances": surveillances,
        "run_ids": [str(r["run_id"]) for r in rows],
        "d0": float(d0),
        "N_runs": N_runs,
        "n_outbreaks": int(sum(data["outbreak"])),
        "outbreak_rate": round(sum(data["outbreak"]) / N_runs, 4),
    }
    return data, meta


def build_boundary_ar_stan_data(
    run_rows: list[dict[str, Any]],
    *,
    pathogen: str,
    d0: float = DEFAULT_D0,
    outbreaks_only: bool = True,
    eps: float = 1e-4,
) -> tuple[dict[str, Any], dict[str, Any]]:
    rows = filter_pathogen_runs(run_rows, pathogen)
    if outbreaks_only:
        rows = filter_outbreak_runs(rows)
    if not rows:
        raise ValueError(f"No outbreak runs for pathogen={pathogen!r} Stage B")

    platforms, surveillances, plat_idx, surv_idx = _factor_indices(rows)
    ar_raw = [as_float(r.get("attack_rate"), 0.0) for r in rows]
    ar = [min(1.0 - eps, max(eps, a)) for a in ar_raw]
    N_runs = len(rows)
    data = {
        "N_runs": N_runs,
        "P": len(platforms),
        "S": len(surveillances),
        "ar": ar,
        "platform": [plat_idx[str(r.get("platform_id") or "unknown")] for r in rows],
        "surveillance": [
            surv_idx[str(r.get("surveillance_strategy") or "none")] for r in rows
        ],
        "log_k": [_log_k(r) for r in rows],
        "dose_adj": [as_float(r.get("dose_adjustment"), d0) for r in rows],
        "d0": float(d0),
    }
    meta = {
        "stage": "boundary_ar",
        "pathogen": pathogen,
        "platforms": platforms,
        "surveillances": surveillances,
        "run_ids": [str(r["run_id"]) for r in rows],
        "d0": float(d0),
        "N_runs": N_runs,
        "mean_ar": round(sum(ar) / N_runs, 6),
    }
    return data, meta
