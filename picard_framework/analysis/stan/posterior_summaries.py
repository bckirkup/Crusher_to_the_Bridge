"""Summarize Stan posterior draws into campaign calibration tables."""

from __future__ import annotations

import csv
import math
import os
from typing import Any, Sequence

from picard_framework.analysis._io import (
    allowed_roots,
    ensure_out_dir,
    write_csv,
    write_timeseries_table,
)
from simulation_utils.paths import validated_open

VSP_SWEEP = (0.01, 0.03, 0.05, None)  # None = off


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
    out = ensure_out_dir(out_dir)
    post = ensure_out_dir(os.path.join(out, "posterior"))
    artifacts: dict[str, str] = {}

    try:
        draws = fit.stan_variables()
    except Exception:
        draws = {}

    platforms: list[str] = list(meta.get("platforms") or [])
    surveillances: list[str] = list(meta.get("surveillances") or [])
    d0 = float(meta.get("d0", 10.6))

    # --- dose_adj calibration ---
    beta = _col(draws, "beta_d")
    dose_rows = []
    if beta:
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
        dose_rows.append(
            {
                "parameter": "beta_d",
                "mean": round(_mean(beta), 6),
                "q05": round(_quantile(beta, 0.05), 6),
                "q50": round(_quantile(beta, 0.50), 6),
                "q95": round(_quantile(beta, 0.95), 6),
                "d0": d0,
                "p_dose_in_10.4_10.8": round(in_window / max(n_mc, 1), 6),
                "note": "Weakly identified from incidence slope; interpret with PPC",
            }
        )
    path = os.path.join(post, "dose_adj_calibration.csv")
    write_csv(
        path,
        dose_rows,
        [
            "parameter",
            "mean",
            "q05",
            "q50",
            "q95",
            "d0",
            "p_dose_in_10.4_10.8",
            "note",
        ],
    )
    artifacts["dose_adj_calibration"] = "posterior/dose_adj_calibration.csv"

    # --- platform effects ---
    alpha = draws.get("alpha_platform")
    risk = draws.get("platform_risk")
    plat_rows: list[dict[str, Any]] = []
    if alpha is not None:
        import numpy as np

        a = np.asarray(alpha)
        # shape (draws, P) or (P,)
        if a.ndim == 1:
            a = a.reshape(1, -1)
        r = np.asarray(risk) if risk is not None else np.exp(a)
        if r.ndim == 1:
            r = r.reshape(1, -1)
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
        # Risk ratios vs mega if present
        mega_idx = next((i for i, n in enumerate(platforms) if "mega" in n), None)
        exp_idx = next((i for i, n in enumerate(platforms) if "expedition" in n), None)
        if mega_idx is not None and exp_idx is not None and r.shape[1] > max(mega_idx, exp_idx):
            ratios = [float(r[d, exp_idx] / r[d, mega_idx]) for d in range(r.shape[0]) if r[d, mega_idx] > 0]
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
    write_csv(
        os.path.join(post, "platform_effects.csv"),
        plat_rows,
        [
            "platform",
            "alpha_mean",
            "alpha_q05",
            "alpha_q95",
            "risk_mean",
            "risk_q05",
            "risk_q95",
        ],
    )
    artifacts["platform_effects"] = "posterior/platform_effects.csv"

    # --- surveillance effects ---
    delta = draws.get("delta_surveillance")
    surv_rows: list[dict[str, Any]] = []
    if delta is not None:
        import numpy as np

        d = np.asarray(delta)
        if d.ndim == 1:
            d = d.reshape(1, -1)
        for i, name in enumerate(surveillances):
            if i >= d.shape[1]:
                break
            col = [float(x) for x in d[:, i]]
            surv_rows.append(
                {
                    "surveillance": name,
                    "delta_mean": round(_mean(col), 6),
                    "delta_q05": round(_quantile(col, 0.05), 6),
                    "delta_q50": round(_quantile(col, 0.50), 6),
                    "delta_q95": round(_quantile(col, 0.95), 6),
                }
            )
    write_csv(
        os.path.join(post, "surveillance_effects.csv"),
        surv_rows,
        ["surveillance", "delta_mean", "delta_q05", "delta_q50", "delta_q95"],
    )
    artifacts["surveillance_effects"] = "posterior/surveillance_effects.csv"

    # --- VSP threshold effect ---
    eta = _col(draws, "eta_vsp")
    comp = _col(draws, "vsp_compression")
    vsp_rows = []
    if eta:
        vsp_rows.append(
            {
                "parameter": "eta_vsp",
                "mean": round(_mean(eta), 6),
                "q05": round(_quantile(eta, 0.05), 6),
                "q50": round(_quantile(eta, 0.50), 6),
                "q95": round(_quantile(eta, 0.95), 6),
                "compression_mean": round(_mean(comp), 6) if comp else "",
                "compression_q05": round(_quantile(comp, 0.05), 6) if comp else "",
                "compression_q95": round(_quantile(comp, 0.95), 6) if comp else "",
            }
        )
    write_csv(
        os.path.join(post, "vsp_threshold_effect.csv"),
        vsp_rows,
        [
            "parameter",
            "mean",
            "q05",
            "q50",
            "q95",
            "compression_mean",
            "compression_q05",
            "compression_q95",
        ],
    )
    artifacts["vsp_threshold_effect"] = "posterior/vsp_threshold_effect.csv"

    # trigger_hazard stub (observed triggers in v1)
    write_csv(
        os.path.join(post, "trigger_hazard.csv"),
        [
            {
                "model": "observed_triggers",
                "note": "Phase 1 treats trigger epochs as known; latent hazard deferred",
            }
        ],
        ["model", "note"],
    )
    artifacts["trigger_hazard"] = "posterior/trigger_hazard.csv"

    # --- posterior predictive AR ---
    pred_ar = draws.get("pred_attack_rate")
    ppc_ar_rows: list[dict[str, Any]] = []
    if pred_ar is not None:
        import numpy as np

        pa = np.asarray(pred_ar)
        if pa.ndim == 1:
            pa = pa.reshape(1, -1)
        n_runs = pa.shape[1]
        for r in range(n_runs):
            col = [float(x) for x in pa[:, r]]
            obs = None
            if run_summary_rows and r < len(run_summary_rows):
                obs = run_summary_rows[r].get("attack_rate")
            ppc_ar_rows.append(
                {
                    "run_index": r + 1,
                    "run_id": (
                        run_summary_rows[r].get("run_id")
                        if run_summary_rows and r < len(run_summary_rows)
                        else ""
                    ),
                    "obs_attack_rate": obs,
                    "pred_mean": round(_mean(col), 6),
                    "pred_q05": round(_quantile(col, 0.05), 6),
                    "pred_q50": round(_quantile(col, 0.50), 6),
                    "pred_q95": round(_quantile(col, 0.95), 6),
                }
            )
    write_csv(
        os.path.join(post, "posterior_predictive_ar.csv"),
        ppc_ar_rows,
        [
            "run_index",
            "run_id",
            "obs_attack_rate",
            "pred_mean",
            "pred_q05",
            "pred_q50",
            "pred_q95",
        ],
    )
    artifacts["posterior_predictive_ar"] = "posterior/posterior_predictive_ar.csv"

    # --- PPC curves under alternative VSP thresholds (summary table) ---
    ppc_curve_rows: list[dict[str, Any]] = []
    if ppc_ar_rows and eta:
        base_mean = _mean([float(r["pred_mean"]) for r in ppc_ar_rows if r.get("pred_mean") is not None])
        for thr in VSP_SWEEP:
            label = "off" if thr is None else str(thr)
            if thr is None:
                factors = [math.exp(e) for e in eta]
            else:
                ref = float(meta.get("vsp_ref", 0.05))
                strength = max(0.0, (ref - thr) / ref) if ref > 0 else 0.0
                factors = [math.exp(-e * (1 + strength)) for e in eta]
            adj = [base_mean * f for f in factors]
            ppc_curve_rows.append(
                {
                    "vsp_threshold": label,
                    "pred_ar_mean": round(_mean(adj), 6),
                    "pred_ar_q05": round(_quantile(adj, 0.05), 6),
                    "pred_ar_q50": round(_quantile(adj, 0.50), 6),
                    "pred_ar_q95": round(_quantile(adj, 0.95), 6),
                }
            )

    # Slim epoch PPC from ppc_new_inf_mean (preferred) or legacy y_rep
    epoch_ppc: list[dict[str, Any]] = []
    ppc_mean = draws.get("ppc_new_inf_mean")
    if ppc_mean is not None:
        import numpy as np

        pm = np.asarray(ppc_mean)
        if pm.ndim == 1:
            pm = pm.reshape(1, -1)
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
    else:
        y_rep = draws.get("y_rep")
        if y_rep is not None:
            import numpy as np

            yr = np.asarray(y_rep)
            if yr.ndim == 2:
                yr = yr.reshape(1, yr.shape[0], yr.shape[1])
            if yr.ndim == 3:
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

    if epoch_ppc:
        name = write_timeseries_table(post, epoch_ppc, [
            "run_index", "epoch", "y_rep_mean", "y_rep_q05", "y_rep_q95",
        ])
        src = os.path.join(post, name)
        dest = os.path.join(post, name.replace("epoch_timeseries", "ppc_curves"))
        if src != dest and os.path.isfile(src):
            with validated_open(src, "rb", allowed_roots=allowed_roots()) as rf:
                blob = rf.read()
            with validated_open(dest, "wb", allowed_roots=allowed_roots()) as wf:
                wf.write(blob)
            artifacts["ppc_curves"] = f"posterior/{os.path.basename(dest)}"
        else:
            artifacts["ppc_curves"] = f"posterior/{name}"
    else:
        write_csv(
            os.path.join(post, "ppc_curves.csv"),
            ppc_curve_rows,
            ["vsp_threshold", "pred_ar_mean", "pred_ar_q05", "pred_ar_q50", "pred_ar_q95"],
        )
        artifacts["ppc_curves"] = "posterior/ppc_curves.csv"

    write_csv(
        os.path.join(post, "vsp_threshold_ppc_sweep.csv"),
        ppc_curve_rows,
        ["vsp_threshold", "pred_ar_mean", "pred_ar_q05", "pred_ar_q50", "pred_ar_q95"],
    )

    return artifacts


def summarize_outbreak_fit(
    *,
    fit: Any,
    meta: dict[str, Any],
    out_dir: str,
    run_summary_rows: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    """Write Stage-A outbreak posterior tables under ``out_dir/posterior``."""
    out = ensure_out_dir(out_dir)
    post = ensure_out_dir(os.path.join(out, "posterior"))
    artifacts: dict[str, str] = {}

    try:
        draws = fit.stan_variables()
    except Exception:
        draws = {}

    platforms: list[str] = list(meta.get("platforms") or [])
    surveillances: list[str] = list(meta.get("surveillances") or [])
    d0 = float(meta.get("d0", 10.6))

    beta = _col(draws, "beta_d")
    dose_rows = []
    if beta:
        dose_rows.append(
            {
                "parameter": "beta_d",
                "mean": round(_mean(beta), 6),
                "q05": round(_quantile(beta, 0.05), 6),
                "q50": round(_quantile(beta, 0.50), 6),
                "q95": round(_quantile(beta, 0.95), 6),
                "d0": d0,
                "p_dose_in_10.4_10.8": "",
                "note": "Stage A logit slope on (d0 - dose_adj); P(outbreak)",
            }
        )
    write_csv(
        os.path.join(post, "dose_adj_calibration.csv"),
        dose_rows,
        [
            "parameter",
            "mean",
            "q05",
            "q50",
            "q95",
            "d0",
            "p_dose_in_10.4_10.8",
            "note",
        ],
    )
    artifacts["dose_adj_calibration"] = "posterior/dose_adj_calibration.csv"

    alpha = draws.get("alpha_platform")
    risk = draws.get("platform_risk")
    plat_rows: list[dict[str, Any]] = []
    if alpha is not None:
        import numpy as np

        a = np.asarray(alpha)
        if a.ndim == 1:
            a = a.reshape(1, -1)
        r = np.asarray(risk) if risk is not None else 1.0 / (1.0 + np.exp(-a))
        if r.ndim == 1:
            r = r.reshape(1, -1)
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
    write_csv(
        os.path.join(post, "platform_effects.csv"),
        plat_rows,
        [
            "platform",
            "alpha_mean",
            "alpha_q05",
            "alpha_q95",
            "risk_mean",
            "risk_q05",
            "risk_q95",
        ],
    )
    artifacts["platform_effects"] = "posterior/platform_effects.csv"

    delta = draws.get("delta_surveillance")
    surv_rows: list[dict[str, Any]] = []
    if delta is not None:
        import numpy as np

        d = np.asarray(delta)
        if d.ndim == 1:
            d = d.reshape(1, -1)
        for i, name in enumerate(surveillances):
            if i >= d.shape[1]:
                break
            col = [float(x) for x in d[:, i]]
            surv_rows.append(
                {
                    "surveillance": name,
                    "delta_mean": round(_mean(col), 6),
                    "delta_q05": round(_quantile(col, 0.05), 6),
                    "delta_q50": round(_quantile(col, 0.50), 6),
                    "delta_q95": round(_quantile(col, 0.95), 6),
                }
            )
    write_csv(
        os.path.join(post, "surveillance_effects.csv"),
        surv_rows,
        ["surveillance", "delta_mean", "delta_q05", "delta_q50", "delta_q95"],
    )
    artifacts["surveillance_effects"] = "posterior/surveillance_effects.csv"

    eta = _col(draws, "eta_vsp")
    comp = _col(draws, "vsp_compression")
    vsp_rows = []
    if eta:
        vsp_rows.append(
            {
                "parameter": "eta_vsp",
                "mean": round(_mean(eta), 6),
                "q05": round(_quantile(eta, 0.05), 6),
                "q50": round(_quantile(eta, 0.50), 6),
                "q95": round(_quantile(eta, 0.95), 6),
                "compression_mean": round(_mean(comp), 6) if comp else "",
                "compression_q05": round(_quantile(comp, 0.05), 6) if comp else "",
                "compression_q95": round(_quantile(comp, 0.95), 6) if comp else "",
            }
        )
    write_csv(
        os.path.join(post, "vsp_threshold_effect.csv"),
        vsp_rows,
        [
            "parameter",
            "mean",
            "q05",
            "q50",
            "q95",
            "compression_mean",
            "compression_q05",
            "compression_q95",
        ],
    )
    artifacts["vsp_threshold_effect"] = "posterior/vsp_threshold_effect.csv"

    pred = draws.get("pred_outbreak_prob")
    ppc_rows: list[dict[str, Any]] = []
    if pred is not None:
        import numpy as np

        pa = np.asarray(pred)
        if pa.ndim == 1:
            pa = pa.reshape(1, -1)
        for r in range(pa.shape[1]):
            col = [float(x) for x in pa[:, r]]
            obs = None
            rid = ""
            if run_summary_rows and r < len(run_summary_rows):
                obs = run_summary_rows[r].get("outbreak_occurred")
                rid = str(run_summary_rows[r].get("run_id") or "")
            ppc_rows.append(
                {
                    "run_index": r + 1,
                    "run_id": rid,
                    "obs_outbreak": obs,
                    "pred_mean": round(_mean(col), 6),
                    "pred_q05": round(_quantile(col, 0.05), 6),
                    "pred_q50": round(_quantile(col, 0.50), 6),
                    "pred_q95": round(_quantile(col, 0.95), 6),
                }
            )
    write_csv(
        os.path.join(post, "posterior_predictive_outbreak.csv"),
        ppc_rows,
        [
            "run_index",
            "run_id",
            "obs_outbreak",
            "pred_mean",
            "pred_q05",
            "pred_q50",
            "pred_q95",
        ],
    )
    artifacts["posterior_predictive_outbreak"] = (
        "posterior/posterior_predictive_outbreak.csv"
    )

    write_csv(
        os.path.join(post, "stage_note.csv"),
        [
            {
                "stage": "outbreak",
                "n_runs": meta.get("N_runs"),
                "n_outbreaks": meta.get("n_outbreaks"),
                "outbreak_rate": meta.get("outbreak_rate"),
                "note": "Bernoulli-logit P(outbreak); trajectory is Stage B",
            }
        ],
        ["stage", "n_runs", "n_outbreaks", "outbreak_rate", "note"],
    )
    artifacts["stage_note"] = "posterior/stage_note.csv"
    return artifacts


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
