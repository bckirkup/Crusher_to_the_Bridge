"""COVID-VULN-01 analytic companion: the marginal susceptibility law.

For the shipped law — s ~ Beta(alpha, beta) * susceptibility_scale with
hazard -expm1(-s * D) — the marginal counterfactual infection probability
of a host that stood in an accrued effective dose field D~ has a closed
form: E_s[exp(-s * D~)] over X ~ Beta(alpha, beta), s = scale * X is the
confluent hypergeometric

    P(inf | D~; alpha) = 1 - 1F1(alpha; alpha + beta; -scale * D~)

with scale = Theta * (alpha + beta) / alpha so E[s] = Theta on every arm.
The alpha -> infinity limit is the exponential (homogeneous) law,
P = 1 - exp(-Theta * D~). This module:

1. emits the marginal curves P(D~; alpha) on a D~ grid for the arm
   endpoints, the shipped 0.18, and the exponential limit;
2. convolves them over each cell's emitted per-host dose field
   (mechanism.susceptibility.challenged_pairs -> accrued_dose) to predict
   the counterfactual infection mass under each alpha — the predicted
   tail-move the measured A/B is checked against;
3. scores prediction vs measurement per paired (class, seed): predicted
   residual mass under the counterfactual alpha on arm A's measured
   field against arm B's realized secondaries — the design's >2x
   disagreement trigger.

Usage:
    python3 tools/covid_vuln_analytic.py \
        --cells-dir /path/to/cells --out analytic.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scipy.special import hyp1f1, loggamma  # noqa: E402

from simulation_utils.paths import (  # noqa: E402
    resolve_repo_path,
    validated_open,
)
from tools.covid_rhythm_ab_readout import (  # noqa: E402
    _cell_summaries,
    _recorded,
)
from tools.covid_route_attribution import _quantiles  # noqa: E402

REPO_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))

BETA_FIXED = 58.0
THETA_FIXED = 2.37e11
# The grid the ledger table reports: endpoints, shipped, the graded
# interior band edges, and the homogeneous limit (None = exponential).
ALPHA_GRID: tuple[float | None, ...] = (
    0.05, 0.18, 0.5, 1.0, 1.5, 2.0, None,
)
ASYMPTOTIC_Z = -500.0


def susceptibility_scale(alpha: float, beta: float, theta: float) -> float:
    """scale = Theta * (alpha + beta) / alpha — E[s] = Theta on every arm."""
    return float(theta) * (float(alpha) + float(beta)) / float(alpha)


def marginal_p_infection(
    alpha: float | None,
    beta: float,
    theta: float,
    accrued_dose: float,
) -> float:
    """P(inf | D~) marginalized over the susceptibility draw.

    ``alpha=None`` is the homogeneous limit (a point mass at Theta):
    P = 1 - exp(-Theta * D~). For finite alpha the 1F1 evaluation falls
    back to the leading large-|z| asymptotic
    1F1(a, b, -x) ~ Gamma(b)/Gamma(b-a) * x^-a * (1 - a(1+a-b)/x)
    past |z| = 500, where the e^{-x} tail is negligible and scipy's
    direct evaluation loses precision.
    """
    d = float(accrued_dose)
    if d <= 0.0:
        return 0.0
    if alpha is None:
        return -math.expm1(-float(theta) * d)
    a = float(alpha)
    b = a + float(beta)
    z = -susceptibility_scale(a, beta, theta) * d
    if z > ASYMPTOTIC_Z:
        survival = float(hyp1f1(a, b, z))
    else:
        x = -z
        log_term = (
            float(loggamma(b)) - float(loggamma(b - a)) - a * math.log(x)
        )
        survival = math.exp(log_term) * (1.0 - a * (1.0 + a - b) / x)
    # Clamp into [0, 1] — the asymptotic series can overshoot slightly.
    return min(max(1.0 - survival, 0.0), 1.0)


def marginal_curve(
    alphas: tuple[float | None, ...],
    beta: float,
    theta: float,
    dose_grid: list[float],
) -> dict[str, list[float | None]]:
    """P(inf | D~; alpha) on a shared dose grid — the ledger table."""
    return {
        ("inf" if a is None else f"{a:g}"): [
            marginal_p_infection(a, beta, theta, d) for d in dose_grid
        ]
        for a in alphas
    }


def _pairs(cell: dict[str, Any]) -> list[dict[str, Any]]:
    susc = (
        cell.get("summary", {}).get("mechanism", {})
        .get("susceptibility", {})
    )
    return list(susc.get("challenged_pairs") or [])


def cell_prediction(
    cell: dict[str, Any],
    alphas: tuple[float | None, ...],
    beta: float,
    theta: float,
) -> dict[str, Any]:
    """Counterfactual infection mass per alpha over one cell's field.

    The basis is the cell's challenged-uninfected hosts' accrued dose
    rows: P~_i(alpha') = 1 - 1F1(alpha'; alpha'+beta; -scale' * D~_i),
    marginalized over a fresh counterfactual draw — so it applies to the
    dose field the host stood in on either arm. The own-law check uses
    the measured Lambda block: sum_i (1 - exp(-Lambda_i)) is the same
    quantity with the realized draw kept.
    """
    pairs = _pairs(cell)
    doses = [
        float(p["accrued_dose"]) for p in pairs
        if float(p.get("accrued_dose") or 0.0) > 0.0
    ]
    masses: dict[str, float] = {}
    share_ge_0p5: dict[str, float | None] = {}
    for a in alphas:
        probs = [
            marginal_p_infection(a, beta, theta, d) for d in doses
        ]
        key = "inf" if a is None else f"{a:g}"
        masses[key] = float(sum(probs))
        share_ge_0p5[key] = (
            sum(1 for p in probs if p >= 0.5) / len(probs)
            if probs else None
        )
    haz = [
        float(p["accrued_hazard"]) for p in pairs
        if float(p.get("accrued_hazard") or 0.0) > 0.0
    ]
    return {
        "index": cell["cell"]["index"],
        "class_id": cell["cell"]["class_id"],
        "arm_id": cell["cell"]["arm_id"],
        "seed": cell["cell"]["seed"],
        "alpha": cell["cell"].get("alpha"),
        "n_challenged_pairs": len(pairs),
        "n_dosed_hosts": len(doses),
        "own_law_residual_mass": float(
            sum(-math.expm1(-h) for h in haz)
        ),
        "recorded_onsets": _recorded(cell),
        "infections_total": float(
            cell.get("summary", {}).get("infections_total") or 0
        ),
        "seeded_count": float(
            cell.get("summary", {}).get("seeded_count") or 0
        ),
        "predicted_mass": masses,
        "predicted_share_p_ge_0p5": share_ge_0p5,
    }


def _cross_check(preds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Predicted tail-move vs measured tail-move per paired seed.

    The informative direction runs from the heavier-tail arm to the
    sharper one: the basis arm's challenged-uninfected survivors each
    carry an accrued dose field, and the counterfactual mass under the
    target alpha is the *predicted tail-move* — the extra conversions
    the sharper law would have produced on the same exposure
    trajectory. It is checked against the *measured tail-move*
    (mate secondaries - own secondaries), the same quantity the A/B
    reports. A ratio outside [0.5, 2.0] on an applicable pair is the
    design's instrument-defect trigger.

    A pair is applicable only when the basis arm's survivor field can
    stand in for the shared exposure trajectory: the basis arm must
    have ignited (secondaries > 0, dosed pairs present) and the two
    burns must be comparable (own >= 0.5 * mate). On extinct or weak
    basis cells the counterfactual field is structurally thin — the
    arms then differ by ignition, not by the marginal law on a shared
    field — so those pairs are reported as not applicable rather than
    as disagreement.
    """
    by_key = {
        (p["class_id"], p["seed"], p["arm_id"]): p for p in preds
    }
    checks = []
    for (class_id, seed, arm), p in sorted(by_key.items()):
        alpha = p["alpha"] if p["alpha"] is not None else math.inf
        for other, mate in by_key.items():
            if mate["class_id"] != class_id or mate["seed"] != seed:
                continue
            mate_alpha = (
                mate["alpha"] if mate["alpha"] is not None else math.inf
            )
            if not alpha < mate_alpha:
                continue
            key = "inf" if mate["alpha"] is None else f"{mate['alpha']:g}"
            predicted = p["predicted_mass"].get(key)
            if predicted is None:
                continue
            own = p["infections_total"] - p["seeded_count"]
            realized = mate["infections_total"] - mate["seeded_count"]
            delta = realized - own
            applicable = (
                own > 0.0
                and p["n_challenged_pairs"] > 0
                and own >= 0.5 * realized
                and delta > 0.0
            )
            ratio = (
                predicted / delta if applicable and predicted > 0.0
                else None
            )
            checks.append({
                "class_id": class_id,
                "seed": seed,
                "field_basis_arm": arm,
                "target_arm": mate["arm_id"],
                "predicted_tail_move": predicted,
                "measured_tail_move": delta,
                "own_secondaries": own,
                "mate_secondaries": realized,
                "applicable": applicable,
                "ratio": ratio,
                "exceeds_2x": bool(
                    applicable and ratio is not None
                    and (ratio > 2.0 or ratio < 0.5)
                ),
            })
    return checks


def pool_predictions(preds: list[dict[str, Any]]) -> dict[str, Any]:
    """Pool per-cell predictions by (class, field-basis arm, alpha')."""
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for p in preds:
        groups.setdefault((p["class_id"], p["arm_id"]), []).append(p)
    pooled: dict[str, Any] = {}
    for (class_id, arm), rows in sorted(groups.items()):
        alpha_keys = sorted(
            {k for r in rows for k in r["predicted_mass"]},
            key=lambda k: (k != "inf", float(k) if k != "inf" else 0.0),
        )
        pooled[f"{class_id}|{arm}"] = {
            "n_cells": len(rows),
            "predicted_mass_mean": {
                a: _quantiles([
                    r["predicted_mass"][a] for r in rows
                    if a in r["predicted_mass"]
                ])["mean"]
                for a in alpha_keys
            },
            "predicted_mass_median": {
                a: _quantiles([
                    r["predicted_mass"][a] for r in rows
                    if a in r["predicted_mass"]
                ])["median"]
                for a in alpha_keys
            },
            "own_law_residual_mass_mean": _quantiles([
                r["own_law_residual_mass"] for r in rows
            ])["mean"],
            "realized_secondaries": _quantiles([
                r["infections_total"] - r["seeded_count"] for r in rows
            ]),
            "recorded_onsets": _quantiles([
                r["recorded_onsets"] for r in rows
            ]),
        }
    return pooled


def pool(
    cells: list[dict[str, Any]],
    *,
    beta: float = BETA_FIXED,
    theta: float = THETA_FIXED,
    alphas: tuple[float | None, ...] = ALPHA_GRID,
) -> dict[str, Any]:
    preds = [
        cell_prediction(c, alphas, beta, theta) for c in cells
    ]
    checks = _cross_check(preds)
    return {
        "design": "covid_vuln_ab_v1",
        "beta": beta,
        "theta": theta,
        "alpha_grid": [
            ("inf" if a is None else a) for a in alphas
        ],
        "note": (
            "marginal curve P = 1 - 1F1(alpha; alpha+beta; -scale*D~), "
            "scale = theta*(alpha+beta)/alpha; alpha 'inf' is the "
            "exponential limit 1 - exp(-theta*D~). Predicted mass is "
            "over the cell's own measured challenged-uninfected dose "
            "field (accrued_dose); cross-check compares the predicted "
            "tail-move (counterfactual survivor conversions under the "
            "sharper arm) with the measured tail-move (paired arm "
            "difference), on pairs where the basis arm ignited and the "
            "two burns are comparable (own >= 0.5 * mate)."
        ),
        "marginal_curves": marginal_curve(
            alphas, beta, theta,
            [math.pow(10.0, e / 2.0) for e in range(-32, -6)],
        ),
        "cells": preds,
        "pooled": pool_predictions(preds),
        "cross_check": {
            "checks": checks,
            "n_exceeds_2x": sum(1 for c in checks if c["exceeds_2x"]),
            "ratio_quantiles": _quantiles([
                c["ratio"] for c in checks if c["ratio"] is not None
            ]),
        },
    }


def main() -> None:  # pragma: no cover - CLI driver
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cells-dir", required=True)
    parser.add_argument(
        "--design",
        default="picard_framework/runs/covid_vuln_ab_v1_design.json",
        help="Design JSON supplying beta and theta",
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
    cells = _cell_summaries(args.cells_dir)
    if not cells:
        raise SystemExit(f"no cell payloads under {args.cells_dir}")
    text = json.dumps(
        pool(
            cells,
            beta=float(design.beta),
            theta=float(design.theta),
        ),
        indent=1,
        default=str,
    )
    if args.out:
        out_path = resolve_repo_path(REPO_ROOT, args.out)
        with validated_open(
            out_path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8",
        ) as handle:
            handle.write(text)
        print(f"wrote {out_path}")
    else:
        print(text)


if __name__ == "__main__":
    main()
