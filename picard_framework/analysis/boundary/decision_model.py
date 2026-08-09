"""Monte Carlo pre-boarding decision model (one scenario → summary)."""

from __future__ import annotations

from typing import Any

import numpy as np

from picard_framework.analysis.boundary.costs import (
    CostParams,
    compute_voyage_costs,
    cost_params_from_mapping,
    false_positives_per_true_positive,
    value_of_information_per_pax,
)
from picard_framework.analysis.boundary.posterior_lookup import OutbreakSurface
from picard_framework.analysis.boundary.prevalence import (
    draw_introductions,
    scenario_prevalence_params,
)
from picard_framework.analysis.boundary.screening import (
    run_screening,
    screening_params_from_scenario,
)


def simulate_one_voyage(
    scenario: dict[str, Any],
    surface: OutbreakSurface,
    rng: np.random.Generator,
    costs: CostParams,
) -> dict[str, float]:
    """Single voyage realization → scalar outcomes."""
    prev = scenario_prevalence_params(scenario)
    intro = draw_introductions(rng=rng, **prev)
    scr_params = screening_params_from_scenario(scenario)
    screening = run_screening(
        z=intro.z,
        is_crew=intro.is_crew,
        rng=rng,
        **scr_params,
    )

    point = surface.lookup(
        platform_class=str(scenario["platform_class"]),
        pathogen=str(scenario["pathogen"]),
        baseline_response=str(scenario.get("baseline_response", "vsp")),
        k=float(screening.k_board),
    )

    n_total = int(prev["n_pax"]) + int(prev["n_crew"])
    # Boarded population approx: deny removes passengers/crew from ship.
    n_denied = int(screening.denied.sum())
    n_boarded = max(n_total - n_denied, 0)

    policy = str(scenario["policy"])
    # P0/P1: no operational screening charges (P1 advisory-only).
    if policy in ("P0", "P1"):
        n_adopted_cost = 0
        n_secondary_cost = 0
    else:
        n_adopted_cost = int(screening.adopted.sum())
        n_secondary_cost = int(screening.n_secondary)

    voyage_costs = compute_voyage_costs(
        params=costs,
        n_total=n_total,
        n_adopted=n_adopted_cost,
        n_secondary=n_secondary_cost,
        n_fp=screening.n_fp,
        n_tp=screening.n_tp,
        k_missed=screening.k_board,  # infectious who boarded
        p_trigger=point.P_trigger,
        e_ar=point.E_AR,
        n_pax_boarded=n_boarded,
    )

    return {
        "K_intro": float(intro.k_intro),
        "K_board": float(screening.k_board),
        "intercepted": float(screening.intercepted),
        "n_fp": float(screening.n_fp),
        "n_tp": float(screening.n_tp),
        "n_adopted": float(screening.adopted.sum()),
        "n_secondary": float(screening.n_secondary),
        "P_trigger": float(point.P_trigger),
        "P_accel": float(point.P_accel),
        "attack_rate": float(point.E_AR),
        "screening_cost": float(voyage_costs.screening + voyage_costs.secondary),
        "false_positive_cost": float(voyage_costs.false_positive),
        "true_positive_cost": float(voyage_costs.true_positive),
        "onboard_cost": float(voyage_costs.onboard),
        "reputational_cost": float(voyage_costs.reputational),
        "total_cost": float(voyage_costs.total),
    }


def _mean(xs: list[float]) -> float:
    return float(sum(xs) / len(xs)) if xs else float("nan")


def run_monte_carlo(
    scenario: dict[str, Any],
    surface: OutbreakSurface,
    *,
    n_mc: int,
    seed: int,
    baseline_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Aggregate ``n_mc`` voyage draws into a decision summary."""
    costs = cost_params_from_mapping(scenario.get("costs"))
    rng = np.random.default_rng(int(seed))
    buckets: dict[str, list[float]] = {
        "K_intro": [],
        "K_board": [],
        "intercepted": [],
        "n_fp": [],
        "n_tp": [],
        "P_trigger": [],
        "P_accel": [],
        "attack_rate": [],
        "screening_cost": [],
        "false_positive_cost": [],
        "true_positive_cost": [],
        "onboard_cost": [],
        "reputational_cost": [],
        "total_cost": [],
    }
    for _ in range(int(n_mc)):
        row = simulate_one_voyage(scenario, surface, rng, costs)
        for key in buckets:
            buckets[key].append(row[key])

    mean_fp = _mean(buckets["n_fp"])
    mean_tp = _mean(buckets["n_tp"])
    summary: dict[str, Any] = {
        "schema_version": "1.0",
        "scenario_id": scenario["scenario_id"],
        "policy": scenario["policy"],
        "platform_class": scenario.get("platform_class"),
        "pathogen": scenario.get("pathogen"),
        "pi_inf": float(scenario["pi_inf"]),
        "n_mc": int(n_mc),
        "seed": int(seed),
        "expected_intercepted": _mean(buckets["intercepted"]),
        "expected_K_intro": _mean(buckets["K_intro"]),
        "expected_K_board": _mean(buckets["K_board"]),
        "expected_P_trigger": _mean(buckets["P_trigger"]),
        "expected_P_accel": _mean(buckets["P_accel"]),
        "expected_attack_rate": _mean(buckets["attack_rate"]),
        "expected_total_cost": _mean(buckets["total_cost"]),
        "expected_screening_cost": _mean(buckets["screening_cost"]),
        "expected_false_positive_cost": _mean(buckets["false_positive_cost"]),
        "expected_true_positive_cost": _mean(buckets["true_positive_cost"]),
        "expected_onboard_cost": _mean(buckets["onboard_cost"]),
        "expected_reputational_cost": _mean(buckets["reputational_cost"]),
        "false_positives_per_true_positive": false_positives_per_true_positive(
            mean_fp, mean_tp
        ),
        "false_positives_per_vsp_avoided": None,
        "cost_per_vsp_avoided": None,
        "break_even_prevalence": None,
        "value_of_information_per_pax": None,
        "parameters": {
            "N_pax": scenario.get("N_pax"),
            "N_crew": scenario.get("N_crew"),
            "Se_w": scenario.get("Se_w"),
            "Sp_w": scenario.get("Sp_w"),
            "adoption_pax": scenario.get("adoption_pax"),
            "adoption_crew": scenario.get("adoption_crew"),
            "cost_scenario": scenario.get("cost_scenario"),
            "baseline_response": scenario.get("baseline_response", "vsp"),
            "surface_source": surface.source,
        },
    }

    if baseline_summary is not None:
        n_pax = int(scenario.get("N_pax") or 0)
        summary["value_of_information_per_pax"] = value_of_information_per_pax(
            cost_baseline=float(baseline_summary["expected_total_cost"]),
            cost_policy=float(summary["expected_total_cost"]),
            n_pax=n_pax,
        )
        p0 = float(baseline_summary["expected_P_trigger"])
        p1 = float(summary["expected_P_trigger"])
        avoided = p0 - p1
        if avoided > 1e-12:
            summary["false_positives_per_vsp_avoided"] = mean_fp / avoided
            summary["cost_per_vsp_avoided"] = (
                float(summary["expected_total_cost"])
                - float(baseline_summary["expected_total_cost"])
            ) / avoided

    return summary
