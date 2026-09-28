"""COVID-VULN-01 readout: pool the alpha-endpoint A/B cells.

Reads the per-seed cell JSONs the Batch array wrote
(``tools/covid_vuln_ab.run_cell`` payloads — fetched from S3 or a local
directory) and pools them by (class_id, arm) into the numbers the
COVID-VULN-01 ledger reports:

1. the override-landing audit — ``summary.dose_response`` must echo the
   arm's declared alpha/beta/scale on every cell (an unexercised axis is
   not a measurement);
2. the drawn-vs-declared susceptibility check — measured never-challenged
   draw quantiles against the theoretical Beta(alpha, 58) * scale
   quantiles the arm declares;
3. takeoff burn (recorded-onset distribution, clause ratio vs ~197,
   before_share) per arm;
4. ignition share (recorded_onsets >= takeoff gate) with a Wilson 95%
   interval per arm;
5. exposure-set metrics (dosed-set size, challenged share, accrued-hazard
   block, route split);
6. the paired-seed A/B deltas (hi - lo) against the paired-seed spread.

Usage:
    python3 tools/covid_vuln_ab_readout.py \
        --cells-dir /path/to/cells --out readout.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from simulation_utils.paths import resolve_repo_path  # noqa: E402
from tools.covid_rhythm_ab_readout import (  # noqa: E402
    _cell_summaries,
    _emit_text,
    _exposure_pool,
    _group_cells,
    _p_infection_mean,
    _recorded,
    _t1_clause,
)
from tools.covid_route_attribution import _quantiles  # noqa: E402

REPO_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))

WILSON_Z = 1.959964  # 95%


def _wilson(k: int, n: int) -> dict[str, Any]:
    """Wilson 95% interval on a binomial share."""
    if n <= 0:
        return {"share": None, "lo": None, "hi": None, "n": 0, "k": 0}
    p = k / n
    denom = 1.0 + WILSON_Z * WILSON_Z / n
    centre = (p + WILSON_Z * WILSON_Z / (2.0 * n)) / denom
    half = (
        WILSON_Z
        * math.sqrt(p * (1.0 - p) / n + WILSON_Z * WILSON_Z / (4.0 * n * n))
        / denom
    )
    return {
        "share": p,
        "lo": max(0.0, centre - half),
        "hi": min(1.0, centre + half),
        "n": n,
        "k": k,
    }


def _infections(c: dict[str, Any]) -> float:
    return float(c["summary"].get("infections_total") or 0)


def _resolved_dose_response(c: dict[str, Any]) -> dict[str, Any]:
    return c["summary"].get("dose_response") or {}


def _landing_audit(
    cells: list[dict[str, Any]],
    declared_alpha: float | None,
    declared_scale: float | None,
) -> dict[str, Any]:
    """Every cell's consumed dose_response vs its declared arm values."""
    mismatched = []
    alphas = []
    for c in cells:
        dr = _resolved_dose_response(c)
        alpha = dr.get("alpha")
        scale = dr.get("susceptibility_scale")
        if alpha is not None:
            alphas.append(float(alpha))
        ok = (
            alpha is not None
            and scale is not None
            and declared_alpha is not None
            and declared_scale is not None
            and abs(float(alpha) - declared_alpha) <= 1e-9 * declared_alpha
            and abs(float(scale) - declared_scale) <= 1e-6 * declared_scale
            and dr.get("model") == "beta_poisson"
        )
        if not ok:
            mismatched.append(c.get("_file") or c["cell"].get("key"))
    return {
        "n_cells": len(cells),
        "declared_alpha": declared_alpha,
        "resolved_alpha_values": sorted(set(round(a, 9) for a in alphas)),
        "mismatched_cells": mismatched,
        "landed": not mismatched,
    }


def _draw_check(
    cells: list[dict[str, Any]],
    declared_alpha: float | None,
    declared_scale: float | None,
    beta: float,
) -> dict[str, Any]:
    """Measured susceptibility draws vs the declared Beta(alpha, beta).

    The never-challenged counterfactual quantiles are the cleanest draw
    sample the instrument emits; a small ratio-vs-theory spread is the
    NORO-FRAIL-01 (a) check carried on this axis.
    """
    if declared_alpha is None or declared_scale is None:
        return {"skipped": "no declared alpha"}
    try:
        from scipy.stats import beta as beta_dist
    except ImportError:
        return {"skipped": "scipy unavailable"}
    measured = _quantiles([
        float(v)
        for c in cells
        for v in (
            c["summary"].get("mechanism", {}).get("susceptibility", {})
            .get("never_challenged_counterfactual", {})
            .get(q)
            for q in ("median", "q05", "q95")
        )
        if v is not None
    ])
    dist = beta_dist(declared_alpha, beta)
    theory = {
        "q05": declared_scale * float(dist.ppf(0.05)),
        "median": declared_scale * float(dist.ppf(0.50)),
        "q95": declared_scale * float(dist.ppf(0.95)),
    }
    per_cell_median = []
    for c in cells:
        susc = (
            c["summary"].get("mechanism", {}).get("susceptibility", {})
            .get("never_challenged_counterfactual", {})
        )
        med = susc.get("median")
        if med is not None and theory["median"]:
            per_cell_median.append(float(med) / theory["median"])
    return {
        "theory_quantiles": theory,
        "measured_median_ratio_vs_theory": _quantiles(per_cell_median),
        "measured_pool": measured,
    }


def _paired_alpha_spread(
    lo: list[dict[str, Any]],
    hi: list[dict[str, Any]],
) -> dict[str, Any]:
    """Per-seed (hi - lo) deltas against the within-arm paired spread.

    The dose_response.alpha change re-phases the draw stream, so a seed
    pair is a legal paired realization rather than a bit-aligned one; the
    null band is the within-arm neighbouring-seed spread, per the
    declared attribution criterion.
    """
    by_seed_lo = {c["cell"]["seed"]: c for c in lo}
    by_seed_hi = {c["cell"]["seed"]: c for c in hi}
    paired = sorted(set(by_seed_lo) & set(by_seed_hi))
    d_onsets = [
        _recorded(by_seed_hi[s]) - _recorded(by_seed_lo[s]) for s in paired
    ]
    d_infect = [
        _infections(by_seed_hi[s]) - _infections(by_seed_lo[s])
        for s in paired
    ]
    lo_sorted = sorted(_recorded(by_seed_lo[s]) for s in paired)
    hi_sorted = sorted(_recorded(by_seed_hi[s]) for s in paired)
    spread = [
        abs(b - a)
        for a, b in zip(lo_sorted, lo_sorted[1:])
    ] + [
        abs(b - a)
        for a, b in zip(hi_sorted, hi_sorted[1:])
    ]
    return {
        "n_paired_seeds": len(paired),
        "recorded_onsets_delta_hi_minus_lo": _quantiles(d_onsets),
        "recorded_onsets_abs_delta": _quantiles([abs(d) for d in d_onsets]),
        "infections_delta_hi_minus_lo": _quantiles(d_infect),
        "within_arm_seed_spread_abs": _quantiles(spread),
        "effect_exceeds_spread": bool(
            d_onsets
            and _quantiles([abs(d) for d in d_onsets])["median"]
            > (_quantiles(spread)["median"] or 0.0)
        ),
        "identical_burns": bool(
            d_onsets and all(d == 0 for d in d_onsets)
            and all(d == 0 for d in d_infect)
        ),
        "p_infection_mean_lo_median": _quantiles([
            _p_infection_mean(c) for c in lo
            if _p_infection_mean(c) is not None
        ])["median"],
        "p_infection_mean_hi_median": _quantiles([
            _p_infection_mean(c) for c in hi
            if _p_infection_mean(c) is not None
        ])["median"],
    }


def _arm_pool(
    cells: list[dict[str, Any]],
    takeoff_min: int,
    declared_alpha: float | None,
    declared_scale: float | None,
    beta: float,
) -> dict[str, Any]:
    takeoff = _t1_clause(cells, takeoff_min)
    ignited = sum(1 for c in cells if _recorded(c) >= takeoff_min)
    return {
        "n_cells": len(cells),
        "landing_audit": _landing_audit(cells, declared_alpha, declared_scale),
        "draw_check": _draw_check(cells, declared_alpha, declared_scale, beta),
        "recorded_onsets": _quantiles([_recorded(c) for c in cells]),
        "infections_total": _quantiles([_infections(c) for c in cells]),
        "ignition_share_wilson": _wilson(ignited, len(cells)),
        "takeoff": takeoff,
        "exposure_set": _exposure_pool(cells),
    }


def pool(
    cells: list[dict[str, Any]],
    *,
    takeoff_min: int = 10,
    arm_alphas: dict[str, float] | None = None,
    arm_scales: dict[str, float] | None = None,
    beta: float = 58.0,
) -> dict[str, Any]:
    groups = _group_cells(cells)
    classes: dict[str, Any] = {}
    for class_id in sorted({k[0] for k in groups}):
        arms = {
            arm: _arm_pool(
                groups[(class_id, arm)], takeoff_min,
                (arm_alphas or {}).get(arm),
                (arm_scales or {}).get(arm),
                beta,
            )
            for arm in sorted(
                a for (cid, a) in groups if cid == class_id
            )
        }
        entry: dict[str, Any] = {"arms": arms}
        if "alpha_lo" in arms and "alpha_hi" in arms:
            entry["paired_ab"] = _paired_alpha_spread(
                groups[(class_id, "alpha_lo")],
                groups[(class_id, "alpha_hi")],
            )
        classes[class_id] = entry
    return {
        "design": "covid_vuln_ab_v1",
        "takeoff_recorded_onsets": takeoff_min,
        "n_cells": len(cells),
        "arm_alphas": arm_alphas or {},
        "arm_scales": arm_scales or {},
        "beta": beta,
        "classes": classes,
    }


def main() -> None:  # pragma: no cover - CLI driver
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cells-dir", required=True)
    parser.add_argument("--takeoff-min", type=int, default=10)
    parser.add_argument(
        "--design",
        default="picard_framework/runs/covid_vuln_ab_v1_design.json",
        help="Design JSON supplying the declared arm alphas",
    )
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    from picard_framework.covid_vuln_cells import load_vuln_design

    design_path = (
        args.design
        if os.path.isabs(args.design)
        else str(resolve_repo_path(REPO_ROOT, args.design))
    )
    design = load_vuln_design(design_path)
    arm_alphas = {
        str(a["arm_id"]): float(a["alpha"]) for a in design.arms
    }
    arm_scales = {
        str(a["arm_id"]): design.susceptibility_scale(str(a["arm_id"]))
        for a in design.arms
    }
    cells = _cell_summaries(args.cells_dir)
    if not cells:
        raise SystemExit(f"no cell payloads under {args.cells_dir}")
    text = json.dumps(
        pool(
            cells,
            takeoff_min=args.takeoff_min,
            arm_alphas=arm_alphas,
            arm_scales=arm_scales,
            beta=float(design.beta),
        ),
        indent=1,
        default=str,
    )
    _emit_text(text, args.out)


if __name__ == "__main__":
    main()
