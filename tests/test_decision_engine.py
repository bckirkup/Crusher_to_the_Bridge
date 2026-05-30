"""decision_engine unit tests."""

from __future__ import annotations

import pytest

from decision_engine import ActionEnvelope, DecisionRound, ExperienceStore, ObservationModel
from decision_engine.policy import RuleBasedPolicy


def test_observation_model_crew_local() -> None:
    snap = {
        "epoch": 1,
        "agents": [{"agent_id": 5, "location": "Bridge", "infection_state": "susceptible"}],
        "summary": {"infected": 2},
    }
    obs = ObservationModel.build(snap, "5", "crew_agent")
    assert obs.local.get("location") == "Bridge"


def test_decision_round_noop_envelope() -> None:
    rnd = DecisionRound(
        actor_roster=[{"actor_id": "c1", "role": "commanding_officer"}],
        policies={"c1": RuleBasedPolicy()},
    )
    store = ExperienceStore("/tmp/unused_exp.json")
    env = rnd.solve(0, {"epoch": 0, "summary": {}}, store)
    assert isinstance(env, ActionEnvelope)
    assert "c1" in env.actions


def test_experience_store_rolling_mean(tmp_path) -> None:
    store = ExperienceStore(str(tmp_path / "test_exp.json"))
    store.record_cruise(0, {"fleet": 10.0})
    store.record_cruise(1, {"fleet": 20.0})
    mean = store.get_param("rolling_mean:fleet")
    assert mean == pytest.approx(15.0)
