"""Engine C: CmdStan NUTS calibration ladder for Sentinel designs."""

from __future__ import annotations

import json
import math
import os
import re
import time
from dataclasses import replace
from importlib import resources
from typing import Any, Mapping, Sequence

import numpy as np

from picard_framework.analysis._io import read_json
from picard_framework.analysis.sentinel.design_power import (
    Z90,
    SentinelDesign,
    _coverage,
    _interval,
    _truth_rates,
    build_design_data,
    ceiling_projection,
    load_design,
)
from picard_framework.analysis.stan._sentinel_fleet_data import expected_onsets_fleet

DEFAULT_LADDER = "picard_framework/analysis/sentinel/data/nuts_ladder.json"
NOMINAL_COVERAGE = 0.90
MIN_CLEAN_FRACTION = 0.90
MAX_COVERAGE_GAP = 0.05
NAN_REJECTION = "poisson_lpmf: Rate parameter"
ITERATION_PATTERN = re.compile(r"(?:iteration|Iteration)[: =]+(\d+)")


def load_ladder(path: str | None = None) -> dict[str, Any]:
    """Load and validate the authored NUTS ladder configuration."""
    if path is None:
        raw = resources.files("picard_framework.analysis.sentinel").joinpath(
            "data/nuts_ladder.json",
        ).read_text(encoding="utf-8")
        payload = json.loads(raw)
    else:
        payload = read_json(path)
    if not isinstance(payload, dict) or not isinstance(payload.get("rungs"), list):
        raise ValueError("NUTS ladder must contain a rungs list")
    if not payload["rungs"] or any("id" not in rung for rung in payload["rungs"]):
        raise ValueError("NUTS ladder rungs need ids")
    return payload


def enumerate_cells(ladder: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Enumerate rung, truth-ratio, replicate cells deterministically."""
    cells: list[dict[str, Any]] = []
    settings = ladder.get("settings", {})
    base_seed = int(settings.get("seed_base", 1701))
    for rung_index, rung in enumerate(ladder["rungs"]):
        ratios = rung.get("ratios", [2.0])
        for ratio_index, ratio in enumerate(ratios):
            for replicate in range(int(rung["replicates"])):
                cells.append(
                    {
                        "rung_index": rung_index,
                        "rung": str(rung["id"]),
                        "ratio": float(ratio),
                        "replicate": replicate,
                        "seed": base_seed
                        + 100000 * rung_index
                        + 1000 * ratio_index
                        + replicate,
                    },
                )
    return cells


def _rung_design(rung: Mapping[str, Any]) -> SentinelDesign:
    base = load_design(str(rung["preset"]))
    return replace(
        base,
        n_ports=int(rung["n_ports"]),
        n_ships=int(rung["n_ships"]),
        n_weeks=int(rung["n_weeks"]),
    )


def _simulate_onsets(
    data: Mapping[str, Any],
    design: SentinelDesign,
    ratio: float,
    seed: int,
) -> dict[str, Any]:
    means = expected_onsets_fleet(data, _truth_rates(data, design, ratio))
    rng = np.random.default_rng(seed)
    onsets: list[list[list[int]]] = []
    for voyage, expected in enumerate(means):
        padded = np.zeros((expected.shape[0], int(data["Tmax"])), dtype=int)
        padded[:, : int(data["T"][voyage])] = rng.poisson(expected)
        onsets.append(padded.tolist())
    simulated = dict(data)
    simulated["onsets"] = onsets
    return simulated


def _summary_diagnostics(fit: Any) -> dict[str, float]:
    summary = fit.summary()
    rhat = np.asarray(summary["R_hat"], dtype=float)
    ess = np.asarray(summary["ESS_bulk"], dtype=float)
    finite_rhat = rhat[np.isfinite(rhat)]
    finite_ess = ess[np.isfinite(ess)]
    return {
        "max_rhat": float(np.max(finite_rhat)) if finite_rhat.size else math.inf,
        "min_bulk_ess": float(np.min(finite_ess)) if finite_ess.size else 0.0,
    }


def _sampling_diagnostics(fit: Any, max_treedepth: int, iter_warmup: int) -> dict[str, Any]:
    draws = fit.draws_pd(vars=["divergent__", "treedepth__"])
    errors = fit.runset.get_err_msgs()
    nan_lines = [line for line in errors.splitlines() if NAN_REJECTION in line]
    iterations = [
        int(match.group(1))
        for match in (ITERATION_PATTERN.search(line) for line in nan_lines)
        if match
    ]
    summary = _summary_diagnostics(fit)
    return {
        "divergent_transitions": int(draws["divergent__"].sum()),
        "max_treedepth_hits": int((draws["treedepth__"] >= max_treedepth).sum()),
        "max_rhat": summary["max_rhat"],
        "min_bulk_ess": summary["min_bulk_ess"],
        "nan_rejection_count": len(nan_lines),
        "nan_rejection_latest_iteration": max(iterations) if iterations else None,
        "nan_rejection_after_warmup": bool(iterations and max(iterations) > iter_warmup),
        "nan_rejection_messages": nan_lines,
    }


def _posterior_quantities(
    fit: Any,
    data: Mapping[str, Any],
    ratio: float,
) -> dict[str, Any]:
    ports = np.asarray(data["visit_port"], dtype=int)
    hot = fit.stan_variable("lambda_port")[:, 0]
    background_draws = fit.stan_variable("lambda_port")[:, 1:]
    background = np.exp(np.mean(np.log(np.maximum(background_draws, 1.0e-18)), axis=1))
    ratio_draws = hot / background
    hot_visits = np.flatnonzero(ports == 1)
    visit_draws = fit.stan_variable("lambda_visit")
    visit_widths = [
        math.log(_interval(visit_draws[:, index])[1])
        - math.log(_interval(visit_draws[:, index])[0])
        for index in hot_visits
    ]
    ratio_low, _ = _interval(ratio_draws)
    return {
        "hot_width90_log": math.log(_interval(hot)[1]) - math.log(_interval(hot)[0]),
        "background_width90_log": math.log(_interval(background)[1]) - math.log(_interval(background)[0]),
        "ratio_width90_log": math.log(_interval(ratio_draws)[1]) - math.log(_interval(ratio_draws)[0]),
        "pooled_lambda_hot_coverage": _coverage(hot, float(data["_truth_hot"])),
        "pooled_lambda_background_coverage": _coverage(background, float(data["_truth_background"])),
        "ratio_coverage": _coverage(ratio_draws, ratio),
        "detected": bool(ratio_low > 1.0),
        "hot_visit_width90_log": float(np.mean(visit_widths)) if visit_widths else math.nan,
        "per_visit_hot_width90_log": visit_widths,
    }


def _clean(diagnostics: Mapping[str, Any]) -> bool:
    return (
        diagnostics["divergent_transitions"] == 0
        and diagnostics["max_rhat"] <= 1.01
        and diagnostics["min_bulk_ess"] >= 100.0
    )


def _model_path() -> str:
    return os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "stan",
        "sentinel_fleet.stan",
    )


def run_cell(
    ladder: Mapping[str, Any],
    *,
    rung_id: str,
    ratio: float,
    replicate: int,
    chains: int | None = None,
    iter_warmup: int | None = None,
    iter_sampling: int | None = None,
    adapt_delta: float | None = None,
    max_treedepth: int | None = None,
    seed: int | None = None,
    smoke: bool = False,
) -> dict[str, Any]:
    """Simulate and fit one Engine C cell with CmdStan NUTS."""
    rung_index, rung = next(
        (i, row) for i, row in enumerate(ladder["rungs"]) if row["id"] == rung_id
    )
    design = _rung_design(rung)
    settings = dict(ladder.get("settings", {}))
    ratios = [float(value) for value in rung.get("ratios", [2.0])]
    ratio_index = ratios.index(float(ratio))
    default_seed = (
        settings.get("seed_base", 1701)
        + 100000 * rung_index
        + 1000 * ratio_index
        + replicate
    )
    cell_seed = int(seed if seed is not None else default_seed)
    if smoke:
        design = replace(design, n_ships=2, n_weeks=1)
    data, meta = build_design_data(design)
    data["_truth_hot"] = design.lambda_background * ratio
    data["_truth_background"] = design.lambda_background
    simulated = _simulate_onsets(data, design, ratio, cell_seed)
    simulated.pop("_truth_hot", None)
    simulated.pop("_truth_background", None)
    from cmdstanpy import CmdStanModel, cmdstan_path

    model = CmdStanModel(stan_file=_model_path())
    started = time.monotonic()
    fit = model.sample(
        data=simulated,
        chains=2 if smoke else int(chains or settings["chains"]),
        parallel_chains=2 if smoke else int(chains or settings["chains"]),
        iter_warmup=100 if smoke else int(iter_warmup or settings["iter_warmup"]),
        iter_sampling=100 if smoke else int(iter_sampling or settings["iter_sampling"]),
        seed=cell_seed,
        adapt_delta=0.95 if smoke else float(adapt_delta or settings["adapt_delta"]),
        max_treedepth=12 if smoke else int(max_treedepth or settings["max_treedepth"]),
    )
    elapsed = time.monotonic() - started
    warmup = 100 if smoke else int(iter_warmup or settings["iter_warmup"])
    treedepth = 12 if smoke else int(max_treedepth or settings["max_treedepth"])
    diagnostics = _sampling_diagnostics(fit, treedepth, warmup)
    quantities = _posterior_quantities(
        fit,
        {**simulated, "_truth_hot": data["_truth_hot"], "_truth_background": data["_truth_background"]},
        ratio,
    )
    ceiling = ceiling_projection(design)
    diagnostics["clean"] = _clean(diagnostics) and not diagnostics["nan_rejection_after_warmup"]
    return {
        "engine": "nuts",
        "provenance": {
            "engine": "Engine C CmdStan NUTS",
            "cmdstan": cmdstan_path(),
            "cmdstan_version": os.path.basename(cmdstan_path()).replace("cmdstan-", ""),
            "smoke": smoke,
            "not_a_real_fit": smoke,
        },
        "rung": rung_id,
        "rung_index": rung_index,
        "geometry": {
            "preset": rung["preset"],
            "ports": design.n_ports,
            "ships": design.n_ships,
            "weeks": design.n_weeks,
            "voyages": int(simulated["V"]),
            "visits": int(simulated["NV"]),
            "epochs_per_voyage": int(simulated["Tmax"]),
        },
        "true_hot_ratio": ratio,
        "replicate": replicate,
        "seed": cell_seed,
        "sampler": {
            "chains": 2 if smoke else int(chains or settings["chains"]),
            "iter_warmup": 100 if smoke else int(iter_warmup or settings["iter_warmup"]),
            "iter_sampling": 100 if smoke else int(iter_sampling or settings["iter_sampling"]),
            "adapt_delta": 0.95 if smoke else float(adapt_delta or settings["adapt_delta"]),
            "max_treedepth": 12 if smoke else int(max_treedepth or settings["max_treedepth"]),
        },
        **quantities,
        **diagnostics,
        "engine_a_ceiling_width90_log_ratio": ceiling["sd_log_ratio"] * 2.0 * Z90,
        "wall_clock_seconds": elapsed,
        "simulated_onset_count": int(sum(sum(sum(row) for row in group) for group in simulated["onsets"])),
        "clean": diagnostics["clean"],
        "meta": meta,
    }


def _mean(rows: Sequence[Mapping[str, Any]], key: str) -> float:
    return float(np.mean([float(row[key]) for row in rows]))


def _rung_summary(rung_id: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    clean = [row for row in rows if row.get("clean")]
    clean_fraction = len(clean) / len(rows) if rows else 0.0
    coverage = _mean(clean, "ratio_coverage") if clean else None
    valid_coverage = coverage is not None and 0.85 <= coverage <= 0.95
    ceiling_width = _mean(clean, "engine_a_ceiling_width90_log_ratio") if clean else None
    factor = _mean(clean, "ratio_width90_log") / ceiling_width if clean and ceiling_width else None
    inconsistent = factor is not None and factor < 1.0
    return {
        "rung": rung_id,
        "n_cells": len(rows),
        "n_voyages": int(rows[0]["geometry"]["voyages"]) if rows else None,
        "n_clean": len(clean),
        "clean_fraction": clean_fraction,
        "reliable": clean_fraction >= MIN_CLEAN_FRACTION,
        "coverage_ratio": coverage,
        "coverage_gate": bool(valid_coverage),
        "calibration_factor_r": factor,
        "r_below_one_inconsistent": bool(inconsistent),
        "calibration_factor_usable": bool(valid_coverage and not inconsistent and factor is not None),
        "mean_ratio_width90_log": _mean(clean, "ratio_width90_log") if clean else None,
        "mean_hot_width90_log": _mean(clean, "hot_width90_log") if clean else None,
        "mean_background_width90_log": _mean(clean, "background_width90_log") if clean else None,
        "detection_power": _mean(clean, "detected") if clean else None,
        "coverage_note": (
            "two replicates cannot establish coverage"
            if rung_id == "C8"
            else None
        ),
    }


def _interpolate_mdhr(curve: Sequence[Mapping[str, Any]], target: float = 0.80) -> float | None:
    points = sorted(
        (float(row["true_hot_ratio"]), float(row["power"]))
        for row in curve
        if row.get("power") is not None
    )
    if not points or points[-1][1] < target:
        return None
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if y0 < target <= y1:
            if y1 == y0:
                return x1
            fraction = (target - y0) / (y1 - y0)
            return math.exp(math.log(x0) + fraction * (math.log(x1) - math.log(x0)))
    return points[0][0]


def _power_curve(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    grouped: dict[float, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(float(row["true_hot_ratio"]), []).append(row)
    curve = [
        {
            "true_hot_ratio": ratio,
            "power": _mean(group, "detected"),
            "ratio_coverage": _mean(group, "ratio_coverage"),
            "n_clean": len(group),
        }
        for ratio, group in sorted(grouped.items())
    ]
    return {"curve": curve, "mdhr_at_power_080": _interpolate_mdhr(curve)}


def aggregate_cells(directory: str, ladder: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Aggregate per-cell JSON files, retaining all clean-fraction accounting."""
    config = ladder or load_ladder()
    cells: list[dict[str, Any]] = []
    for root, _dirs, files in os.walk(directory):
        for name in sorted(files):
            if name.endswith(".json"):
                payload = read_json(os.path.join(root, name))
                if isinstance(payload, dict) and payload.get("engine") == "nuts":
                    cells.append(payload)
    by_rung: dict[str, list[dict[str, Any]]] = {}
    for cell in cells:
        by_rung.setdefault(str(cell["rung"]), []).append(cell)
    rungs = [_rung_summary(rung["id"], by_rung.get(rung["id"], [])) for rung in config["rungs"]]
    power = {
        rung: _power_curve(
            [cell for cell in by_rung.get(rung, []) if cell.get("clean")]
        )
        for rung in ("C3", "C6")
        if rung in by_rung
    }
    usable = [row for row in rungs if row["calibration_factor_usable"]]
    extrapolation = _extrapolate_caribbean(usable)
    return {
        "engine": "nuts_aggregate",
        "provenance": "Engine C CmdStan NUTS calibration ladder",
        "n_cells": len(cells),
        "rungs": rungs,
        "power_curves": power,
        "caribbean_extrapolation": extrapolation,
    }


def _extrapolate_caribbean(rungs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rungs:
        return {"status": "void", "reason": "no usable calibration rungs"}
    voyages = np.asarray([float(row["n_voyages"]) for row in rungs])
    factors = np.asarray([float(row["calibration_factor_r"]) for row in rungs])
    log_x = np.log(np.maximum(voyages, 1.0))
    log_y = np.log(factors)
    if len(rungs) == 1:
        r_hat = float(factors[0])
        slope = 0.0
        intercept = float(log_y[0])
        method = "constant_single_rung"
    else:
        slope, intercept = np.polyfit(log_x, log_y, 1)
        residual = log_y - (intercept + slope * log_x)
        stderr = math.sqrt(float(np.sum(residual**2) / max(len(rungs) - 2, 1)))
        slope_se = stderr / max(
            math.sqrt(float(np.sum((log_x - log_x.mean()) ** 2))),
            1.0e-12,
        )
        if abs(slope) <= 1.96 * slope_se:
            r_hat = float(math.exp(log_y.mean()))
            method = "constant_flat"
        else:
            r_hat = float(math.exp(intercept + slope * math.log(1440.0)))
            method = "trend"
    ceiling = ceiling_projection(replace(load_design("caribbean"), n_ships=120, n_weeks=12))
    adjusted = max(1.0, r_hat)
    return {
        "status": "ok",
        "method": method,
        "r_hat": r_hat,
        "r_hat_used": adjusted,
        "slope_log_r_on_log_voyages": slope,
        "extrapolation_decades": math.log10(1440.0 / 360.0),
        "caribbean_mdhr_ceiling": ceiling["mdhr"],
        "caribbean_mdhr_calibrated": math.exp(adjusted * math.log(ceiling["mdhr"])),
        "gate_verdict": "pass" if adjusted == r_hat and r_hat >= 1.0 else "inconsistent_r_below_one",
    }
