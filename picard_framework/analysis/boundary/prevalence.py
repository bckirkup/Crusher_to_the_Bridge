"""Embarkation prevalence / infectious introduction draws."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class IntroductionDraw:
    """Per-voyage infectious status before screening."""

    z: np.ndarray  # bool/int, length N_total; 1 = infectious
    is_crew: np.ndarray  # bool, length N_total
    k_intro: int


def _beta_binomial_k(
    n: int,
    alpha: float,
    beta: float,
    rng: np.random.Generator,
) -> int:
    """Draw K ~ BetaBinomial(n, alpha, beta) via hierarchical Bernoulli."""
    if n <= 0:
        return 0
    pi = float(rng.beta(alpha, beta))
    return int(rng.binomial(n, pi))


def draw_introductions(
    *,
    n_pax: int,
    n_crew: int,
    pi_inf: float,
    rng: np.random.Generator,
    mode: str = "bernoulli",
    alpha_pi: float | None = None,
    beta_pi: float | None = None,
    rho_cluster: float = 1.0,
) -> IntroductionDraw:
    """Draw infectious status for passengers then crew.

    ``rho_cluster > 1`` increases overdispersion via Beta-Binomial when
    ``mode == "beta_binomial"`` (or when rho forces that path). Alpha/beta
    are derived from ``pi_inf`` and ``rho_cluster`` when not supplied.
    """
    n_total = int(n_pax) + int(n_crew)
    if n_total <= 0:
        empty = np.zeros(0, dtype=np.int8)
        return IntroductionDraw(z=empty, is_crew=empty.astype(bool), k_intro=0)

    use_bb = mode == "beta_binomial" or float(rho_cluster) > 1.0
    z = np.zeros(n_total, dtype=np.int8)
    is_crew = np.zeros(n_total, dtype=bool)
    if n_crew > 0:
        is_crew[n_pax:] = True

    if use_bb:
        if alpha_pi is None or beta_pi is None:
            # Method of moments: mean=pi, overdispersion via rho.
            # Effective sample size kappa = (1 / (rho-1)) roughly; clamp.
            rho = max(float(rho_cluster), 1.01)
            kappa = max(2.0, 1.0 / (rho - 1.0))
            pi = min(max(float(pi_inf), 1e-12), 1.0 - 1e-12)
            alpha = pi * kappa
            beta = (1.0 - pi) * kappa
        else:
            alpha = float(alpha_pi)
            beta = float(beta_pi)
        k = _beta_binomial_k(n_total, alpha, beta, rng)
        if k > 0:
            idx = rng.choice(n_total, size=k, replace=False)
            z[idx] = 1
    else:
        pi = min(max(float(pi_inf), 0.0), 1.0)
        z = rng.binomial(1, pi, size=n_total).astype(np.int8)

    return IntroductionDraw(z=z, is_crew=is_crew, k_intro=int(z.sum()))


def scenario_prevalence_params(scenario: dict[str, Any]) -> dict[str, Any]:
    """Extract prevalence kwargs from a scenario dict."""
    return {
        "n_pax": int(scenario.get("N_pax", 0)),
        "n_crew": int(scenario.get("N_crew", 0)),
        "pi_inf": float(scenario["pi_inf"]),
        "mode": str(scenario.get("prevalence_mode", "bernoulli")),
        "alpha_pi": scenario.get("alpha_pi"),
        "beta_pi": scenario.get("beta_pi"),
        "rho_cluster": float(scenario.get("rho_cluster", 1.0)),
    }
