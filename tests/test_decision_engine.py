"""decision_engine unit tests."""

from __future__ import annotations

import pytest

from decision_engine import ActionEnvelope, DecisionRound, ExperienceStore, ObservationModel
from decision_engine.policy import (
    CommandThresholdPolicy,
    RuleBasedPolicy,
    ThresholdBeliefPolicy,
    build_policies_from_config,
)
from decision_engine.stackelberg.round import StackelbergRound
from decision_engine.views import ObservationView
from telemetry_buffer.agent_axes import (
    COMPLIANCE_COMPLIANT,
    INFECTION_INFECTED,
    PRESENTATION_SYMPTOMATIC,
)


def test_observation_model_crew_local() -> None:
    snap = {
        "epoch": 1,
        "agents": [{"agent_id": 5, "location": "Bridge", "infection_state": "susceptible"}],
        "summary": {"infected": 2},
    }
    obs = ObservationModel.build(snap, "5", "crew_agent")
    assert obs.local.get("location") == "Bridge"


def test_observation_model_crew_information_state() -> None:
    snap = {
        "epoch": 1,
        "agents": [{
            "agent_id": 1,
            "infection_state": INFECTION_INFECTED,
            "symptom_presentation": PRESENTATION_SYMPTOMATIC,
            "compliance_status": COMPLIANCE_COMPLIANT,
        }],
        "information_state": {
            "agents": {
                "1": {"severity_belief": 0.2, "trust_medical": 0.3},
            },
        },
    }
    obs = ObservationModel.build(snap, "1", "crew_agent")
    assert obs.local["information_state"]["severity_belief"] == pytest.approx(0.2)


def test_observation_model_command_ois() -> None:
    snap = {
        "epoch": 2,
        "cost_accounting": {
            "operational_impact_cumulative": 12.5,
            "operational_impact_epoch": 3.0,
        },
    }
    obs = ObservationModel.build(snap, "command", "commanding_officer")
    assert obs.local["operational_impact_cumulative"] == pytest.approx(12.5)


def test_decision_round_noop_envelope(tmp_path) -> None:
    rnd = DecisionRound(
        actor_roster=[{"actor_id": "c1", "role": "commanding_officer"}],
        policies={"c1": RuleBasedPolicy()},
    )
    store = ExperienceStore(str(tmp_path / "unused_exp.json"))
    env = rnd.solve(0, {"epoch": 0, "summary": {}}, store)
    assert isinstance(env, ActionEnvelope)
    assert "c1" in env.actions


def test_experience_store_rolling_mean(tmp_path) -> None:
    store = ExperienceStore(str(tmp_path / "test_exp.json"))
    store.record_cruise(0, {"fleet": 10.0})
    store.record_cruise(1, {"fleet": 20.0})
    mean = store.get_param("rolling_mean:fleet")
    assert mean == pytest.approx(15.0)


def test_threshold_belief_policy_hide(tmp_path) -> None:
    policy = ThresholdBeliefPolicy()
    obs = ObservationView(
        actor_id="7",
        role="crew_agent",
        epoch=1,
        local={
            "symptom_presentation": PRESENTATION_SYMPTOMATIC,
            "infection_state": INFECTION_INFECTED,
            "compliance_status": COMPLIANCE_COMPLIANT,
            "information_state": {
                "severity_belief": 0.1,
                "trust_medical": 0.2,
            },
        },
    )
    acts = policy.decide(obs, ExperienceStore(str(tmp_path / "x.json")))
    assert acts[0]["kind"] == "hide_symptoms"
    assert acts[0]["agent_id"] == 7


def test_command_threshold_policy_authorize(tmp_path) -> None:
    policy = CommandThresholdPolicy(ois_escalation_threshold=5.0)
    obs = ObservationView(
        actor_id="command",
        role="commanding_officer",
        epoch=1,
        local={
            "operational_impact_cumulative": 10.0,
            "stoplight_eligible_sop_ids": ["SOP-001", "SOP-002"],
            "cost_accounting": {"operational_impact_cumulative": 10.0},
        },
        summary={"susceptible": 10, "infected": 0, "recovered": 0, "immune": 0},
    )
    acts = policy.decide(obs, ExperienceStore(str(tmp_path / "x.json")))
    kinds = {a["kind"] for a in acts}
    assert "authorize_sop_subset" in kinds


def test_build_policies_from_config() -> None:
    cmd, _med, pop = build_policies_from_config({
        "decision_engine": {
            "population_policy": "threshold_belief",
            "command_policy": "rule_based",
            "medical_policy": "threshold",
        },
    })
    assert isinstance(pop, ThresholdBeliefPolicy)
    assert isinstance(cmd, RuleBasedPolicy)


def test_stackelberg_split_solve_methods(tmp_path) -> None:
    rnd = StackelbergRound()
    snap = {
        "epoch": 1,
        "agents": [{
            "agent_id": 0,
            "infection_state": INFECTION_INFECTED,
            "symptom_presentation": PRESENTATION_SYMPTOMATIC,
            "compliance_status": COMPLIANCE_COMPLIANT,
            "role": "passenger",
        }],
        "summary": {"sick_call_count": 0},
    }
    info = {"agents": {"0": {"severity_belief": 0.5, "trust_medical": 0.8}}}
    store = ExperienceStore(str(tmp_path / "unused2.json"))
    pop_env = rnd.solve_population(1, snap, info, store)
    assert "population" in pop_env.actions or pop_env.actions == {}
