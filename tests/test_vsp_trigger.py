"""Regression tests for the selectable VSP trigger and reported-case telemetry."""

from __future__ import annotations

import pytest

from engines.infection_dynamics_bridge import (
    VSP_RULE_INSTANT_PREVALENCE,
    VSP_RULE_REPORTED_PASSENGER_CASES,
    IllnessStatus,
    KorkinShipEngine,
)
from orchestrator_init import (
    compute_group_rates_for_ids,
    load_vsp_trigger_rule,
    update_ever_reported_ids,
)
from orchestrator_types import SimulationState
from picard_framework.runs.mega_cruise_campaign.campaign_runner import (
    compute_derived_metrics,
)


def _engine(rule: str = VSP_RULE_REPORTED_PASSENGER_CASES) -> KorkinShipEngine:
    return KorkinShipEngine(
        num_passengers=10,
        num_crew=0,
        initial_infected=0,
        seed=7,
        vsp_trigger_rule=rule,
    )


def test_reported_rule_crosses_threshold_without_prevalence_trigger() -> None:
    engine = _engine()
    engine.vsp_threshold_fraction = 0.3
    for agent in engine.agents[:4]:
        agent.illness_status = IllnessStatus.SYMPTOMATIC

    engine._check_vsp_trigger()
    assert engine.vsp_triggered is False

    engine.vsp_reported_case_fraction = 0.29
    engine._check_vsp_trigger()
    assert engine.vsp_triggered is False

    engine.vsp_reported_case_fraction = 0.3
    engine._check_vsp_trigger()
    assert engine.vsp_triggered is True


def test_instant_prevalence_rule_preserves_old_trigger() -> None:
    cfg = {"escalation": {"vsp_trigger_rule": VSP_RULE_INSTANT_PREVALENCE}}
    engine = _engine(load_vsp_trigger_rule(cfg))
    engine.vsp_threshold_fraction = 0.3
    for agent in engine.agents[:3]:
        agent.illness_status = IllnessStatus.SYMPTOMATIC

    engine._check_vsp_trigger()
    assert engine.vsp_triggered is True


def test_reported_ids_are_unique_and_noise_is_separate() -> None:
    state = SimulationState()
    update_ever_reported_ids(
        {"true_positive_ids": [1, 1, 2], "noise_ids": [9, 9]},
        state.ever_reported_ids,
        state.ever_reported_noise_ids,
    )
    update_ever_reported_ids(
        {"true_positive_ids": [2, 3], "noise_ids": [9, 10]},
        state.ever_reported_ids,
        state.ever_reported_noise_ids,
    )
    assert state.ever_reported_ids == {1, 2, 3}
    assert state.ever_reported_noise_ids == {9, 10}


def test_reported_rates_split_roles_and_class_fallback() -> None:
    agents = [
        {"agent_id": 1, "role": "passenger", "agent_class": "passenger_general"},
        {"agent_id": 2, "role": "passenger", "agent_class": "passenger_family"},
        {"agent_id": 3, "role": "crew", "agent_class": "crew_medical"},
        {"agent_id": 4, "agent_class": "crew_engineering"},
    ]
    rates = compute_group_rates_for_ids(agents, {1, 3, 4})
    assert rates == {
        "overall": 0.75,
        "passenger": 0.5,
        "crew": 1.0,
        "max_group": 1.0,
    }


def test_unknown_vsp_rule_raises() -> None:
    with pytest.raises(ValueError, match="Unknown VSP trigger rule"):
        load_vsp_trigger_rule({"escalation": {"vsp_trigger_rule": "bogus"}})


def test_campaign_metrics_include_reported_case_and_vsp_fields() -> None:
    ts = [
        {
            "epoch": 0,
            "infected": 1,
            "recovered": 0,
            "susceptible": 9,
            "new_infections": 1,
            "trigger_status": "none",
            "reported_case_rate_passenger": 0.1,
            "cumulative_ever_ill_passenger": 1,
            "ever_ill_rate_passenger": 0.1,
            "vsp_triggered": False,
        },
        {
            "epoch": 1,
            "infected": 2,
            "recovered": 0,
            "susceptible": 8,
            "new_infections": 1,
            "trigger_status": "none",
            "reported_case_rate_passenger": 0.2,
            "cumulative_ever_ill_passenger": 2,
            "ever_ill_rate_passenger": 0.2,
            "vsp_triggered": False,
        },
        {
            "epoch": 2,
            "infected": 2,
            "recovered": 0,
            "susceptible": 8,
            "new_infections": 0,
            "trigger_status": "none",
            "reported_case_rate_passenger": 0.3,
            "cumulative_ever_ill_passenger": 3,
            "ever_ill_rate_passenger": 0.3,
            "vsp_triggered": True,
        },
    ]
    derived = compute_derived_metrics(ts, num_agents=10)
    assert derived["reported_case_attack_rate"] == pytest.approx(0.3)
    assert derived["ever_ill_attack_rate"] == pytest.approx(0.3)
    assert derived["vsp_trigger_epoch"] == 2
