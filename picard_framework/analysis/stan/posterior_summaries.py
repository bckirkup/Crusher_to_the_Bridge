"""Summarize Stan posterior draws into campaign calibration tables."""

from __future__ import annotations

import csv
import math
import os
from types import SimpleNamespace
from typing import Any, Callable, Sequence

from picard_framework.analysis._io import (
    allowed_roots,
    ensure_out_dir,
    write_csv,
    write_timeseries_table,
)
from simulation_utils.paths import validated_open

VSP_SWEEP = (0.01, 0.03, 0.05, None)  # None disables the VSP threshold
DOSE_PROBABILITY_WINDOW_KEY = "p_dose_in_10.4_10.8"

_DOSE_ADJ_COLUMNS = [
    "parameter",
    "mean",
    "q05",
    "q50",
    "q95",
    "d0",
    DOSE_PROBABILITY_WINDOW_KEY,
    "note",
]
_PLATFORM_COLUMNS = [
    "platform",
    "alpha_mean",
    "alpha_q05",
    "alpha_q95",
    "risk_mean",
    "risk_q05",
    "risk_q95",
]
_SURVEILLANCE_COLUMNS = [
    "surveillance",
    "delta_mean",
    "delta_q05",
    "delta_q50",
    "delta_q95",
]
_VSP_COLUMNS = [
    "parameter",
    "mean",
    "q05",
    "q50",
    "q95",
    "compression_mean",
    "compression_q05",
    "compression_q95",
]
_PPC_AR_COLUMNS = [
    "run_index",
    "run_id",
    "obs_attack_rate",
    "pred_mean",
    "pred_q05",
    "pred_q50",
    "pred_q95",
]
_PPC_OUTBREAK_COLUMNS = [
    "run_index",
    "run_id",
    "obs_outbreak",
    "pred_mean",
    "pred_q05",
    "pred_q50",
    "pred_q95",
]
_PPC_CURVE_COLUMNS = [
    "vsp_threshold",
    "pred_ar_mean",
    "pred_ar_q05",
    "pred_ar_q50",
    "pred_ar_q95",
]


def _mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def _quantile(xs: Sequence[float], q: float) -> float:
    if not xs:
        return float("nan")
    ordered = sorted(xs)
    if len(ordered) == 1:
        return ordered[0]
    idx = q * (len(ordered) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(ordered) - 1)
    frac = idx - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac


def _col(draws: dict[str, Any], name: str) -> list[float]:
    """Extract a 1-d parameter column from cmdstanpy stan_variable dict/array."""
    if name not in draws:
        return []
    arr = draws[name]
    try:
        import numpy as np

        a = np.asarray(arr)
        return [float(x) for x in a.reshape(-1)]
    except Exception:
        if isinstance(arr, (list, tuple)):
            flat: list[float] = []
            for item in arr:
                if isinstance(item, (list, tuple)):
                    flat.extend(float(x) for x in item)
                else:
                    flat.append(float(item))
            return flat
        return [float(arr)]


def _matrix_param(draws: dict[str, Any], name: str) -> Any:
    return draws.get(name)


def _as_draw_matrix(arr: Any) -> Any:
    """Reshape a Stan variable to ``(draws, n)``."""
    import numpy as np

    a = np.asarray(arr)
    if a.ndim == 1:
        a = a.reshape(1, -1)
    return a


def _rounded_mean_quantiles(xs: Sequence[float]) -> dict[str, float]:
    return {
        "mean": round(_mean(xs), 6),
        "q05": round(_quantile(xs, 0.05), 6),
        "q50": round(_quantile(xs, 0.50), 6),
        "q95": round(_quantile(xs, 0.95), 6),
    }


def _summary_ctx(
    *,
    fit: Any,
    meta: dict[str, Any],
    out_dir: str,
    run_summary_rows: list[dict[str, Any]] | None,
) -> SimpleNamespace:
    out = ensure_out_dir(out_dir)
    post = ensure_out_dir(os.path.join(out, "posterior"))
    try:
        draws = fit.stan_variables()
    except Exception:
        draws = {}
    return SimpleNamespace(
        post=post,
        artifacts={},
        draws=draws,
        meta=meta,
        platforms=list(meta.get("platforms") or []),
        surveillances=list(meta.get("surveillances") or []),
        d0=float(meta.get("d0", 10.6)),
        run_summary_rows=run_summary_rows,
    )


def _dose_window_probability(beta: Sequence[float], d0: float) -> float:
    # Map implied compatible dose window around d0 via beta uncertainty.
    # Report P(dose in [10.4, 10.8]) under a normal approx centered at d0
    # with scale 1/mean(beta) when identifiable; else report beta summary.
    # Monte Carlo over posterior beta: treat calibration mass as N(d0, 1/beta)
    in_window = 0.0
    n_mc = min(len(beta), 2000)
    for b in beta[:n_mc]:
        s = 1.0 / b if b > 1e-6 else 1.0
        # probability mass of N(d0,s) on [10.4, 10.8] via erf
        lo = (10.4 - d0) / (s * math.sqrt(2))
        hi = (10.8 - d0) / (s * math.sqrt(2))
        p = 0.5 * (math.erf(hi) - math.erf(lo))
        in_window += p
    return in_window / max(n_mc, 1)


def _write_dose_adj_calibration(
    ctx: SimpleNamespace, dose_rows: list[dict[str, Any]]
) -> None:
    path = os.path.join(ctx.post, "dose_adj_calibration.csv")
    write_csv(path, dose_rows, _DOSE_ADJ_COLUMNS)
    ctx.artifacts["dose_adj_calibration"] = "posterior/dose_adj_calibration.csv"


def _write_dose_calibration_trajectory(ctx: SimpleNamespace) -> None:
    beta = _col(ctx.draws, "beta_d")
    dose_rows: list[dict[str, Any]] = []
    if beta:
        qs = _rounded_mean_quantiles(beta)
        dose_rows.append(
            {
                "parameter": "beta_d",
                "mean": qs["mean"],
                "q05": qs["q05"],
                "q50": qs["q50"],
                "q95": qs["q95"],
                "d0": ctx.d0,
                DOSE_PROBABILITY_WINDOW_KEY: round(
                    _dose_window_probability(beta, ctx.d0), 6
                ),
                "note": "Weakly identified from incidence slope; interpret with PPC",
            }
        )
    _write_dose_adj_calibration(ctx, dose_rows)


def _write_dose_calibration_outbreak(ctx: SimpleNamespace) -> None:
    beta = _col(ctx.draws, "beta_d")
    dose_rows: list[dict[str, Any]] = []
    if beta:
        qs = _rounded_mean_quantiles(beta)
        dose_rows.append(
            {
                "parameter": "beta_d",
                "mean": qs["mean"],
                "q05": qs["q05"],
                "q50": qs["q50"],
                "q95": qs["q95"],
                "d0": ctx.d0,
                DOSE_PROBABILITY_WINDOW_KEY: "",
                "note": "Stage A logit slope on (d0 - dose_adj); P(outbreak)",
            }
        )
    _write_dose_adj_calibration(ctx, dose_rows)


def _platform_named_rows(a: Any, r: Any, platforms: list[str]) -> list[dict[str, Any]]:
    plat_rows: list[dict[str, Any]] = []
    for i, name in enumerate(platforms):
        if i >= a.shape[1]:
            break
        col_a = [float(x) for x in a[:, i]]
        col_r = [float(x) for x in r[:, i]]
        plat_rows.append(
            {
                "platform": name,
                "alpha_mean": round(_mean(col_a), 6),
                "alpha_q05": round(_quantile(col_a, 0.05), 6),
                "alpha_q95": round(_quantile(col_a, 0.95), 6),
                "risk_mean": round(_mean(col_r), 6),
                "risk_q05": round(_quantile(col_r, 0.05), 6),
                "risk_q95": round(_quantile(col_r, 0.95), 6),
            }
        )
    return plat_rows


def _append_expedition_over_mega_ratio(
    plat_rows: list[dict[str, Any]], platforms: list[str], r: Any
) -> None:
    mega_idx = next((i for i, n in enumerate(platforms) if "mega" in n), None)
    exp_idx = next((i for i, n in enumerate(platforms) if "expedition" in n), None)
    if mega_idx is not None and exp_idx is not None and r.shape[1] > max(mega_idx, exp_idx):
        ratios = [
            float(r[d, exp_idx] / r[d, mega_idx])
            for d in range(r.shape[0])
            if r[d, mega_idx] > 0
        ]
        plat_rows.append(
            {
                "platform": "expedition_over_mega_ratio",
                "alpha_mean": "",
                "alpha_q05": "",
                "alpha_q95": "",
                "risk_mean": round(_mean(ratios), 6),
                "risk_q05": round(_quantile(ratios, 0.05), 6),
                "risk_q95": round(_quantile(ratios, 0.95), 6),
            }
        )


def _risk_from_exp_alpha(a: Any) -> Any:
    import numpy as np

    return np.exp(a)


def _risk_from_logit_alpha(a: Any) -> Any:
    import numpy as np

    return 1.0 / (1.0 + np.exp(-a))


def _build_platform_rows(
    draws: dict[str, Any],
    platforms: list[str],
    *,
    default_risk: Callable[[Any], Any],
    include_expedition_ratio: bool,
) -> list[dict[str, Any]]:
    import numpy as np

    alpha = draws.get("alpha_platform")
    risk = draws.get("platform_risk")
    plat_rows: list[dict[str, Any]] = []
    if alpha is None:
        return plat_rows
    a = _as_draw_matrix(alpha)
    r = np.asarray(risk) if risk is not None else default_risk(a)
    if r.ndim == 1:
        r = r.reshape(1, -1)
    plat_rows = _platform_named_rows(a, r, platforms)
    if include_expedition_ratio:
        _append_expedition_over_mega_ratio(plat_rows, platforms, r)
    return plat_rows


def _write_platform_effects(
    ctx: SimpleNamespace,
    *,
    default_risk: Callable[[Any], Any],
    include_expedition_ratio: bool,
) -> None:
    plat_rows = _build_platform_rows(
        ctx.draws,
        ctx.platforms,
        default_risk=default_risk,
        include_expedition_ratio=include_expedition_ratio,
    )
    write_csv(os.path.join(ctx.post, "platform_effects.csv"), plat_rows, _PLATFORM_COLUMNS)
    ctx.artifacts["platform_effects"] = "posterior/platform_effects.csv"


def _write_surveillance_effects(ctx: SimpleNamespace) -> None:
    delta = ctx.draws.get("delta_surveillance")
    surv_rows: list[dict[str, Any]] = []
    if delta is not None:
        d = _as_draw_matrix(delta)
        for i, name in enumerate(ctx.surveillances):
            if i >= d.shape[1]:
                break
            col = [float(x) for x in d[:, i]]
            qs = _rounded_mean_quantiles(col)
            surv_rows.append(
                {
                    "surveillance": name,
                    "delta_mean": qs["mean"],
                    "delta_q05": qs["q05"],
                    "delta_q50": qs["q50"],
                    "delta_q95": qs["q95"],
                }
            )
    write_csv(
        os.path.join(ctx.post, "surveillance_effects.csv"),
        surv_rows,
        _SURVEILLANCE_COLUMNS,
    )
    ctx.artifacts["surveillance_effects"] = "posterior/surveillance_effects.csv"


def _write_vsp_threshold_effect(ctx: SimpleNamespace) -> list[float]:
    eta = _col(ctx.draws, "eta_vsp")
    comp = _col(ctx.draws, "vsp_compression")
    vsp_rows: list[dict[str, Any]] = []
    if eta:
        qs = _rounded_mean_quantiles(eta)
        vsp_rows.append(
            {
                "parameter": "eta_vsp",
                "mean": qs["mean"],
                "q05": qs["q05"],
                "q50": qs["q50"],
                "q95": qs["q95"],
                "compression_mean": round(_mean(comp), 6) if comp else "",
                "compression_q05": round(_quantile(comp, 0.05), 6) if comp else "",
                "compression_q95": round(_quantile(comp, 0.95), 6) if comp else "",
            }
        )
    write_csv(
        os.path.join(ctx.post, "vsp_threshold_effect.csv"),
        vsp_rows,
        _VSP_COLUMNS,
    )
    ctx.artifacts["vsp_threshold_effect"] = "posterior/vsp_threshold_effect.csv"
    return eta


def _write_trigger_hazard(ctx: SimpleNamespace) -> None:
    write_csv(
        os.path.join(ctx.post, "trigger_hazard.csv"),
        [
            {
                "model": "observed_triggers",
                "note": "Phase 1 treats trigger epochs as known; latent hazard deferred",
            }
        ],
        ["model", "note"],
    )
    ctx.artifacts["trigger_hazard"] = "posterior/trigger_hazard.csv"


def _write_posterior_predictive_ar(ctx: SimpleNamespace) -> list[dict[str, Any]]:
    pred_ar = ctx.draws.get("pred_attack_rate")
    ppc_ar_rows: list[dict[str, Any]] = []
    if pred_ar is not None:
        pa = _as_draw_matrix(pred_ar)
        n_runs = pa.shape[1]
        for r in range(n_runs):
            col = [float(x) for x in pa[:, r]]
            obs = None
            if ctx.run_summary_rows and r < len(ctx.run_summary_rows):
                obs = ctx.run_summary_rows[r].get("attack_rate")
            qs = _rounded_mean_quantiles(col)
            ppc_ar_rows.append(
                {
                    "run_index": r + 1,
                    "run_id": (
                        ctx.run_summary_rows[r].get("run_id")
                        if ctx.run_summary_rows and r < len(ctx.run_summary_rows)
                        else ""
                    ),
                    "obs_attack_rate": obs,
                    "pred_mean": qs["mean"],
                    "pred_q05": qs["q05"],
                    "pred_q50": qs["q50"],
                    "pred_q95": qs["q95"],
                }
            )
    write_csv(
        os.path.join(ctx.post, "posterior_predictive_ar.csv"),
        ppc_ar_rows,
        _PPC_AR_COLUMNS,
    )
    ctx.artifacts["posterior_predictive_ar"] = "posterior/posterior_predictive_ar.csv"
    return ppc_ar_rows


def _vsp_factor_for_threshold(thr: float | None, eta: Sequence[float], meta: dict[str, Any]) -> list[float]:
    if thr is None:
        return [math.exp(e) for e in eta]
    ref = float(meta.get("vsp_ref", 0.05))
    strength = max(0.0, (ref - thr) / ref) if ref > 0 else 0.0
    return [math.exp(-e * (1 + strength)) for e in eta]


def _build_ppc_curve_rows(
    ppc_ar_rows: list[dict[str, Any]],
    eta: Sequence[float],
    meta: dict[str, Any],
) -> list[dict[str, Any]]:
    ppc_curve_rows: list[dict[str, Any]] = []
    if not (ppc_ar_rows and eta):
        return ppc_curve_rows
    base_mean = _mean(
        [float(r["pred_mean"]) for r in ppc_ar_rows if r.get("pred_mean") is not None]
    )
    for thr in VSP_SWEEP:
        label = "off" if thr is None else str(thr)
        factors = _vsp_factor_for_threshold(thr, eta, meta)
        adj = [base_mean * f for f in factors]
        qs = _rounded_mean_quantiles(adj)
        ppc_curve_rows.append(
            {
                "vsp_threshold": label,
                "pred_ar_mean": qs["mean"],
                "pred_ar_q05": qs["q05"],
                "pred_ar_q50": qs["q50"],
                "pred_ar_q95": qs["q95"],
            }
        )
    return ppc_curve_rows


def _epoch_ppc_from_mean(ppc_mean: Any) -> list[dict[str, Any]]:
    epoch_ppc: list[dict[str, Any]] = []
    pm = _as_draw_matrix(ppc_mean)
    t_len = pm.shape[1]
    for t in range(t_len):
        col = [float(x) for x in pm[:, t]]
        epoch_ppc.append(
            {
                "run_index": 0,
                "epoch": t,
                "y_rep_mean": round(_mean(col), 6),
                "y_rep_q05": round(_quantile(col, 0.05), 6),
                "y_rep_q95": round(_quantile(col, 0.95), 6),
            }
        )
    return epoch_ppc


def _epoch_ppc_from_y_rep(y_rep: Any) -> list[dict[str, Any]]:
    import numpy as np

    epoch_ppc: list[dict[str, Any]] = []
    yr = np.asarray(y_rep)
    if yr.ndim == 2:
        yr = yr.reshape(1, yr.shape[0], yr.shape[1])
    if yr.ndim != 3:
        return epoch_ppc
    _n_draws, n_runs, t_len = yr.shape
    for r in range(min(n_runs, 20)):
        for t in range(t_len):
            col = [float(x) for x in yr[:, r, t]]
            epoch_ppc.append(
                {
                    "run_index": r + 1,
                    "epoch": t,
                    "y_rep_mean": round(_mean(col), 6),
                    "y_rep_q05": round(_quantile(col, 0.05), 6),
                    "y_rep_q95": round(_quantile(col, 0.95), 6),
                }
            )
    return epoch_ppc


def _build_epoch_ppc(draws: dict[str, Any]) -> list[dict[str, Any]]:
    ppc_mean = draws.get("ppc_new_inf_mean")
    if ppc_mean is not None:
        return _epoch_ppc_from_mean(ppc_mean)
    y_rep = draws.get("y_rep")
    if y_rep is not None:
        return _epoch_ppc_from_y_rep(y_rep)
    return []


def _publish_epoch_ppc_curves(
    ctx: SimpleNamespace, epoch_ppc: list[dict[str, Any]]
) -> None:
    name = write_timeseries_table(
        ctx.post,
        epoch_ppc,
        ["run_index", "epoch", "y_rep_mean", "y_rep_q05", "y_rep_q95"],
    )
    src = os.path.join(ctx.post, name)
    dest = os.path.join(ctx.post, name.replace("epoch_timeseries", "ppc_curves"))
    if src != dest and os.path.isfile(src):
        with validated_open(src, "rb", allowed_roots=allowed_roots()) as rf:
            blob = rf.read()
        with validated_open(dest, "wb", allowed_roots=allowed_roots()) as wf:
            wf.write(blob)
        ctx.artifacts["ppc_curves"] = f"posterior/{os.path.basename(dest)}"
    else:
        ctx.artifacts["ppc_curves"] = f"posterior/{name}"


def _write_ppc_curves(
    ctx: SimpleNamespace,
    ppc_ar_rows: list[dict[str, Any]],
    eta: Sequence[float],
) -> None:
    ppc_curve_rows = _build_ppc_curve_rows(ppc_ar_rows, eta, ctx.meta)
    epoch_ppc = _build_epoch_ppc(ctx.draws)
    if epoch_ppc:
        _publish_epoch_ppc_curves(ctx, epoch_ppc)
    else:
        write_csv(
            os.path.join(ctx.post, "ppc_curves.csv"),
            ppc_curve_rows,
            _PPC_CURVE_COLUMNS,
        )
        ctx.artifacts["ppc_curves"] = "posterior/ppc_curves.csv"
    write_csv(
        os.path.join(ctx.post, "vsp_threshold_ppc_sweep.csv"),
        ppc_curve_rows,
        _PPC_CURVE_COLUMNS,
    )


def _write_posterior_predictive_outbreak(ctx: SimpleNamespace) -> None:
    pred = ctx.draws.get("pred_outbreak_prob")
    ppc_rows: list[dict[str, Any]] = []
    if pred is not None:
        pa = _as_draw_matrix(pred)
        for r in range(pa.shape[1]):
            col = [float(x) for x in pa[:, r]]
            obs = None
            rid = ""
            if ctx.run_summary_rows and r < len(ctx.run_summary_rows):
                obs = ctx.run_summary_rows[r].get("outbreak_occurred")
                rid = str(ctx.run_summary_rows[r].get("run_id") or "")
            qs = _rounded_mean_quantiles(col)
            ppc_rows.append(
                {
                    "run_index": r + 1,
                    "run_id": rid,
                    "obs_outbreak": obs,
                    "pred_mean": qs["mean"],
                    "pred_q05": qs["q05"],
                    "pred_q50": qs["q50"],
                    "pred_q95": qs["q95"],
                }
            )
    write_csv(
        os.path.join(ctx.post, "posterior_predictive_outbreak.csv"),
        ppc_rows,
        _PPC_OUTBREAK_COLUMNS,
    )
    ctx.artifacts["posterior_predictive_outbreak"] = (
        "posterior/posterior_predictive_outbreak.csv"
    )


def _write_stage_note(ctx: SimpleNamespace) -> None:
    write_csv(
        os.path.join(ctx.post, "stage_note.csv"),
        [
            {
                "stage": "outbreak",
                "n_runs": ctx.meta.get("N_runs"),
                "n_outbreaks": ctx.meta.get("n_outbreaks"),
                "outbreak_rate": ctx.meta.get("outbreak_rate"),
                "note": "Bernoulli-logit P(outbreak); trajectory is Stage B",
            }
        ],
        ["stage", "n_runs", "n_outbreaks", "outbreak_rate", "note"],
    )
    ctx.artifacts["stage_note"] = "posterior/stage_note.csv"


def summarize_fit(
    *,
    fit: Any,
    meta: dict[str, Any],
    out_dir: str,
    run_summary_rows: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    """Write posterior/*.csv (+ ppc curves) under ``out_dir``.

    ``meta`` must include ``platforms``, ``surveillances``, ``d0``, ``vsp_ref``.
    """
    ctx = _summary_ctx(
        fit=fit, meta=meta, out_dir=out_dir, run_summary_rows=run_summary_rows
    )
    _write_dose_calibration_trajectory(ctx)
    _write_platform_effects(
        ctx,
        default_risk=_risk_from_exp_alpha,
        include_expedition_ratio=True,
    )
    _write_surveillance_effects(ctx)
    eta = _write_vsp_threshold_effect(ctx)
    _write_trigger_hazard(ctx)
    ppc_ar_rows = _write_posterior_predictive_ar(ctx)
    _write_ppc_curves(ctx, ppc_ar_rows, eta)
    return ctx.artifacts


def summarize_outbreak_fit(
    *,
    fit: Any,
    meta: dict[str, Any],
    out_dir: str,
    run_summary_rows: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    """Write Stage-A outbreak posterior tables under ``out_dir/posterior``."""
    ctx = _summary_ctx(
        fit=fit, meta=meta, out_dir=out_dir, run_summary_rows=run_summary_rows
    )
    _write_dose_calibration_outbreak(ctx)
    _write_platform_effects(
        ctx,
        default_risk=_risk_from_logit_alpha,
        include_expedition_ratio=False,
    )
    _write_surveillance_effects(ctx)
    _write_vsp_threshold_effect(ctx)
    _write_posterior_predictive_outbreak(ctx)
    _write_stage_note(ctx)
    return ctx.artifacts


def write_summaries_from_csv_draws(
    draws_csv: str,
    meta: dict[str, Any],
    out_dir: str,
) -> dict[str, str]:
    """Fallback summarizer when given a flat draws CSV (tests / no cmdstan)."""

    class _FakeFit:
        def __init__(self, path: str) -> None:
            self._path = path

        def stan_variables(self) -> dict[str, Any]:
            with validated_open(
                self._path, allowed_roots=allowed_roots(), encoding="utf-8", newline=""
            ) as fh:
                reader = csv.DictReader(fh)
                cols: dict[str, list[float]] = {}
                for row in reader:
                    for k, v in row.items():
                        if k is None:
                            continue
                        try:
                            cols.setdefault(k, []).append(float(v))
                        except ValueError:
                            continue
            return cols

    return summarize_fit(fit=_FakeFit(draws_csv), meta=meta, out_dir=out_dir)
