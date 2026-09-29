"""COVID-VULN-01 analytic companion (tools/covid_vuln_analytic.py).

Locks the closed-form marginal P(inf | D~; alpha) = 1 - 1F1(alpha;
alpha+beta; -scale*D~) against numerical integration of the realized
beta draw, the exponential limit, and the endpoint monotonicity the
ledger's predicted tail-move relies on — no simulation required.
"""

from __future__ import annotations

import math

import pytest
from scipy.integrate import quad
from scipy.stats import beta as beta_dist

from tools.covid_vuln_analytic import (
    _cross_check,
    marginal_p_infection,
    susceptibility_scale,
)

BETA = 58.0
THETA = 2.37e11


def _numerical(alpha: float, beta: float, theta: float, d: float) -> float:
    """E_s[1 - exp(-s*d)] with s = scale * X, X ~ Beta(alpha, beta)."""
    scale = susceptibility_scale(alpha, beta, theta)
    dist = beta_dist(alpha, beta)
    val, _ = quad(
        lambda x: -math.expm1(-scale * x * d) * dist.pdf(x),
        0.0,
        1.0,
        epsabs=0.0,
        epsrel=1e-10,
        limit=200,
    )
    return val


class TestMarginalClosedForm:
    @pytest.mark.parametrize(
        "alpha,d",
        [
            (0.05, 1e-12),
            (0.05, 1e-10),
            (0.18, 1e-12),
            (0.18, 1e-9),
            (0.5, 1e-11),
            (2.0, 1e-13),
            (2.0, 1e-10),
        ],
    )
    def test_matches_numerical_integration(
        self, alpha: float, d: float,
    ) -> None:
        closed = marginal_p_infection(alpha, BETA, THETA, d)
        numeric = _numerical(alpha, BETA, THETA, d)
        assert closed == pytest.approx(numeric, rel=0.02, abs=1e-6)

    def test_zero_dose_is_zero(self) -> None:
        for alpha in (0.05, 0.18, 2.0, None):
            assert marginal_p_infection(alpha, BETA, THETA, 0.0) == 0.0
            assert marginal_p_infection(alpha, BETA, THETA, -1.0) == 0.0

    def test_exponential_limit(self) -> None:
        # alpha -> infinity collapses to the point mass at Theta.
        d = 5e-14
        high_alpha = marginal_p_infection(500.0, BETA, THETA, d)
        limit = marginal_p_infection(None, BETA, THETA, d)
        assert high_alpha == pytest.approx(limit, rel=0.02)
        assert limit == pytest.approx(-math.expm1(-THETA * d))

    def test_monotone_in_dose(self) -> None:
        for alpha in (0.05, 0.18, 2.0, None):
            grid = [10.0 ** e for e in (-16, -14, -12, -10)]
            vals = [
                marginal_p_infection(alpha, BETA, THETA, d) for d in grid
            ]
            assert all(b >= a for a, b in zip(vals, vals[1:]))

    def test_homogeneous_dominates_at_high_dose(self) -> None:
        # For a shared dose field, heavier tails (smaller alpha) put more
        # mass at s ~ 0, so marginal escape is larger: P_lo <= P_hi at
        # any dose where both are interior.
        d = 3e-13
        p_lo = marginal_p_infection(0.05, BETA, THETA, d)
        p_hi = marginal_p_infection(2.0, BETA, THETA, d)
        p_inf = marginal_p_infection(None, BETA, THETA, d)
        assert p_lo <= p_hi <= p_inf


class TestScaleInvariance:
    def test_mean_susceptibility_is_theta(self) -> None:
        for alpha in (0.05, 0.18, 0.5, 2.0):
            scale = susceptibility_scale(alpha, BETA, THETA)
            mean_s = scale * alpha / (alpha + BETA)
            assert mean_s == pytest.approx(THETA, rel=1e-9)


def _pred(
    arm: str,
    alpha: float,
    infections: float,
    n_pairs: int,
    mass_2: float,
) -> dict:
    return {
        "class_id": "mega_cruise",
        "seed": 20200205,
        "arm_id": arm,
        "alpha": alpha,
        "n_challenged_pairs": n_pairs,
        "infections_total": infections,
        "seeded_count": 1.0,
        "predicted_mass": {"2": mass_2, "0.05": 0.0},
    }


class TestCrossCheck:
    """Predicted tail-move vs measured tail-move on paired arms.

    The check compares the lo arm's predicted survivor-conversions
    under the sharper alpha against the measured arm difference, only
    where the basis arm's field can stand in for the shared trajectory.
    """

    def test_applicable_pair_ratio_is_tail_move(self) -> None:
        lo = _pred("alpha_lo", 0.05, 1001.0, 100, 770.0)
        hi = _pred("alpha_hi", 2.0, 1773.0, 10, 0.0)
        (check,) = _cross_check([lo, hi])
        assert check["applicable"]
        assert check["predicted_tail_move"] == 770.0
        assert check["measured_tail_move"] == 772.0
        assert check["ratio"] == pytest.approx(770.0 / 772.0)
        assert not check["exceeds_2x"]

    def test_flags_only_genuine_disagreement(self) -> None:
        lo = _pred("alpha_lo", 0.05, 1001.0, 100, 100.0)
        hi = _pred("alpha_hi", 2.0, 1773.0, 10, 0.0)
        (check,) = _cross_check([lo, hi])
        assert check["applicable"]
        assert check["exceeds_2x"]

    def test_extinct_basis_is_not_applicable(self) -> None:
        lo = _pred("alpha_lo", 0.05, 1.0, 30, 1.0)
        hi = _pred("alpha_hi", 2.0, 3701.0, 10, 0.0)
        (check,) = _cross_check([lo, hi])
        assert not check["applicable"]
        assert not check["exceeds_2x"]

    def test_only_heavier_to_sharper_direction(self) -> None:
        lo = _pred("alpha_lo", 0.05, 1001.0, 100, 770.0)
        hi = _pred("alpha_hi", 2.0, 1773.0, 10, 0.0)
        checks = _cross_check([hi, lo])
        assert len(checks) == 1
        assert checks[0]["field_basis_arm"] == "alpha_lo"
