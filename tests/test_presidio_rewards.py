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


class TestSymptomaticBiodefense:
    def test_symptomatic_increases_biodefense_penalty(self) -> None:
        rewards = [
            _compute_rewards(
                _history(infected=2, symptomatic=s),
                DEFAULT_INCENTIVES,
            )["fleet"]
            for s in (0, 5, 20)
        ]
        assert rewards == sorted(rewards, reverse=True)
        assert rewards[0] - rewards[-1] > 10.0


class TestMainCliWiring:
    """CLI flag wiring without invoking ShipSimulation."""

    def test_main_applies_cruises_and_utility_dirs(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        import presidio_runner as pr

        captured: dict = {}

        class FakeSpec:
            def __init__(self) -> None:
                self.num_cruises = 1
                self.social_config = {}
                self.repo_root = str(tmp_path)

            @classmethod
            def from_fleet_json(cls, repo_root, path):
                spec = cls()
                captured["fleet_path"] = path
                captured["repo_root"] = repo_root
                return spec

            @classmethod
            def default(cls, repo_root):
                return cls()

        def fake_run(spec, *, display=False):
            captured["spec"] = spec
            captured["display"] = display

        monkeypatch.setattr(pr, "PresidioRunSpec", FakeSpec)
        monkeypatch.setattr(pr, "run", fake_run)
        monkeypatch.setattr(
            pr.sys,
            "argv",
            [
                "presidio_runner.py",
                "--fleet-config",
                "presidio/data/config/smoke_fleet.json",
                "--cruises",
                "3",
                "--display",
                "--export-utility-dir",
                "out/utility",
                "--import-actions-dir",
                "out/actions",
            ],
        )
        pr.main()
        assert captured["display"] is True
        assert captured["spec"].num_cruises == 3
        social = captured["spec"].social_config
        assert "export_utility_dir" in social
        assert "import_actions_dir" in social
        assert social["export_utility_dir"].endswith("out/utility")
        assert social["import_actions_dir"].endswith("out/actions")

    def test_main_default_spec_without_fleet_config(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import presidio_runner as pr

        seen: dict = {}

        class FakeSpec:
            def __init__(self) -> None:
                self.num_cruises = 1
                self.social_config = None

            @classmethod
            def default(cls, repo_root):
                seen["default"] = repo_root
                return cls()

        monkeypatch.setattr(pr, "PresidioRunSpec", FakeSpec)
        monkeypatch.setattr(pr, "run", lambda spec, *, display=False: seen.update(ran=True))
        monkeypatch.setattr(pr.sys, "argv", ["presidio_runner.py"])
        pr.main()
        assert seen.get("ran") is True
        assert "default" in seen
