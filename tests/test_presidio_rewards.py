"""In-process unit tests for presidio_runner._compute_rewards (no subprocess)."""

from __future__ import annotations

import pytest

from presidio_runner import _compute_rewards


def _history(
    *,
    infected: int = 0,
    symptomatic: int = 0,
    recovered: int = 0,
    financial: float = 0.0,
    ois: float = 0.0,
) -> list[dict]:
    return [
        {
            "summary": {
                "infected": infected,
                "symptomatic": symptomatic,
                "recovered": recovered,
            },
            "cost_accounting": {
                "total_financial_usd": financial,
                "operational_impact_cumulative": ois,
            },
        }
    ]


DEFAULT_INCENTIVES = {
    "biodefense_weight": 1.0,
    "budget_weight": 0.1,
    "recovery_weight": 0.05,
    "ois_weight": 0.02,
}


class TestEmptyHistory:
    def test_empty_history_returns_zero_fleet(self) -> None:
        out = _compute_rewards([], DEFAULT_INCENTIVES)
        assert out == {"fleet": 0.0}
        assert "commanding_officer" not in out


class TestInfectedMonotone:
    def test_infected_sweep_reward_decreases(self) -> None:
        rewards = [
            _compute_rewards(_history(infected=n), DEFAULT_INCENTIVES)["fleet"]
            for n in (0, 5, 20)
        ]
        assert rewards == sorted(rewards, reverse=True)
        span = rewards[0] - rewards[-1]
        assert span > 10.0  # live biodefense knob
        assert all(isinstance(r, float) for r in rewards)


class TestFinancialPenalty:
    def test_financial_increase_lowers_reward(self) -> None:
        rewards = [
            _compute_rewards(_history(financial=f), DEFAULT_INCENTIVES)["fleet"]
            for f in (0.0, 10_000.0, 100_000.0)
        ]
        assert rewards == sorted(rewards, reverse=True)
        assert rewards[0] - rewards[-1] > 1.0


class TestRecoveryBonus:
    def test_recovered_increase_raises_reward(self) -> None:
        rewards = [
            _compute_rewards(_history(recovered=n), DEFAULT_INCENTIVES)["fleet"]
            for n in (0, 10, 50)
        ]
        assert rewards == sorted(rewards)
        assert rewards[-1] - rewards[0] > 1.0


class TestCommandingOfficer:
    def test_officer_is_half_fleet(self) -> None:
        out = _compute_rewards(
            _history(infected=4, recovered=2, financial=500.0),
            DEFAULT_INCENTIVES,
        )
        assert out["commanding_officer"] == pytest.approx(0.5 * out["fleet"])


class TestOisWeightLiveKnob:
    def test_ois_weight_grades_penalty(self) -> None:
        hist = _history(ois=100.0)
        weights = (0.0, 0.02, 0.5)
        rewards = [
            _compute_rewards(
                hist,
                {
                    **DEFAULT_INCENTIVES,
                    "ois_weight": w,
                },
            )["fleet"]
            for w in weights
        ]
        # Higher ois_weight → larger |penalty| → lower reward.
        assert rewards == sorted(rewards, reverse=True)
        assert rewards[0] - rewards[-1] > 20.0  # live knob
        # Negative control: unrelated recovered=0 fixed; only ois_weight moves.
        assert all(isinstance(r, float) and r == r for r in rewards)  # finite
