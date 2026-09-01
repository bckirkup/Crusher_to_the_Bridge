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
    update_ever_ill_ids,
    update_ever_infected_ids,
    update_ever_reported_ids,
)
from orchestrator_record import _summary_counts
from orchestrator_types import SimulationState
from picard_framework.runs.mega_cruise_campaign.campaign_runner import (
    compute_derived_metrics,
    extract_timeseries,
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
    agents = [
        {
            "agent_id": 1,
            "infection_state": "infected",
            "symptom_presentation": "symptomatic",
            "compliance_status": "compliant",
        },
        {
            "agent_id": 2,
            "infection_state": "infected",
            "symptom_presentation": "symptomatic",
            "compliance_status": "compliant",
        },
        {
            "agent_id": 3,
            "infection_state": "infected",
            "symptom_presentation": "symptomatic",
            "compliance_status": "compliant",
        },
    ]
    state = SimulationState()
    update_ever_reported_ids(
        agents,
        {"true_positive_ids": [1, 1, 2], "noise_ids": [9, 9]},
        state.ever_reported_ids,
        state.ever_reported_noise_ids,
    )
    update_ever_reported_ids(
        agents,
        {"true_positive_ids": [2, 3], "noise_ids": [9, 10]},
        state.ever_reported_ids,
        state.ever_reported_noise_ids,
    )
    assert state.ever_reported_ids == {1, 2, 3}
    assert state.ever_reported_noise_ids == {9, 10}


def test_ever_infected_ids_are_monotone_and_include_recovered_agents() -> None:
    agents = [
        {"agent_id": 1, "infection_state": "infected"},
        {"agent_id": 2, "infection_state": "susceptible"},
    ]
    ever_infected: set[int] = set()

    update_ever_infected_ids(agents, ever_infected)
    assert ever_infected == {1}

    agents[0]["infection_state"] = "recovered"
    agents[1]["infection_state"] = "infected"
    update_ever_infected_ids(agents, ever_infected)
    assert ever_infected == {1, 2}

    agents[1]["infection_state"] = "susceptible"
    update_ever_infected_ids(agents, ever_infected)
    assert ever_infected == {1, 2}


def test_epoch_rates_use_role_denominators_and_emit_crew_fields() -> None:
    from types import SimpleNamespace

    agents = [
        {
            "agent_id": 1,
            "agent_class": "passenger_general",
            "infection_state": "infected",
        },
        {
            "agent_id": 2,
            "agent_class": "passenger_general",
            "infection_state": "susceptible",
        },
        {
            "agent_id": 3,
            "agent_class": "crew_general",
            "infection_state": "infected",
        },
        {
            "agent_id": 4,
            "agent_class": "crew_general",
            "infection_state": "recovered",
        },
    ]
    state = SimulationState(
        ever_infected_ids={1, 3, 4},
        ever_ill_ids={1, 3},
        ever_reported_ids={1, 4},
    )
    engine = SimpleNamespace(
        agents=[
            SimpleNamespace(microflora_disruption_status=0)
            for _ in agents
        ],
    )
    summary = _summary_counts(
        agents, engine, state, {"sick_call_count": 0},
    )

    assert summary["infection_attack_rate_passenger"] == pytest.approx(0.5)
    assert summary["infection_attack_rate_crew"] == pytest.approx(1.0)
    assert summary["reported_case_rate_crew"] == pytest.approx(0.5)
    assert summary["ever_ill_rate_crew"] == pytest.approx(0.5)
    assert summary["passenger_complement"] == 2
    assert summary["crew_complement"] == 2
    assert summary["infection_attack_rate_passenger"] != pytest.approx(0.75)


def test_derived_anchor_fields_are_present_and_bounded() -> None:
    derived = compute_derived_metrics(
        [{
            "epoch": 0,
            "infected": 1,
            "recovered": 2,
            "susceptible": 7,
            "passenger_complement": 8,
            "crew_complement": 2,
            "infection_attack_rate_passenger": 0.4,
            "infection_attack_rate_crew": 0.8,
            "ever_ill_rate_crew": 0.6,
            "reported_case_rate_crew": 0.3,
        }],
        num_agents=10,
    )
    assert derived["attack_rate"] == pytest.approx(0.3)
    for field in (
        "infection_attack_rate_passenger",
        "infection_attack_rate_crew",
        "ever_ill_attack_rate_crew",
        "reported_case_attack_rate_crew",
    ):
        assert field in derived
        assert 0.0 <= derived[field] <= 1.0


def test_reported_ids_exclude_noncompliant_agents_without_symptoms() -> None:
    agents = [
        {
            "agent_id": 1,
            "infection_state": "susceptible",
            "symptom_presentation": "asymptomatic",
            "compliance_status": "non_compliant",
        },
        {
            "agent_id": 2,
            "infection_state": "infected",
            "symptom_presentation": "symptomatic",
            "compliance_status": "compliant",
        },
    ]
    state = SimulationState()
    update_ever_reported_ids(
        agents,
        {"true_positive_ids": [1, 2]},
        state.ever_reported_ids,
        state.ever_reported_noise_ids,
    )
    assert state.ever_reported_ids == {2}


def test_reported_cases_never_exceed_ever_ill_cases() -> None:
    agents = [
        {
            "agent_id": 1,
            "infection_state": "infected",
            "symptom_presentation": "symptomatic",
            "compliance_status": "compliant",
        },
        {
            "agent_id": 2,
            "infection_state": "susceptible",
            "symptom_presentation": "asymptomatic",
            "compliance_status": "non_compliant",
        },
    ]
    state = SimulationState()
    for reported_ids in ([1, 2], [1], [2], [1, 2]):
        update_ever_ill_ids(agents, state.ever_ill_ids)
        update_ever_reported_ids(
            agents,
            {"true_positive_ids": reported_ids},
            state.ever_reported_ids,
            state.ever_reported_noise_ids,
        )
        assert state.ever_reported_ids <= state.ever_ill_ids


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
            "passenger_complement": 8,
            "crew_complement": 2,
            "new_infections": 1,
            "trigger_status": "none",
            "reported_case_rate_passenger": 0.1,
            "cumulative_ever_ill_passenger": 1,
            "ever_ill_rate_passenger": 0.1,
            "vsp_triggered": False,
            "infection_counters": {
                "passenger_reported_case_rate": {
                    "value": 0.01,
                    "newly_confined": 0,
                    "exceeded": False,
                },
            },
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
            "infection_counters": {
                "passenger_reported_case_rate": {
                    "value": 0.03,
                    "newly_confined": 2,
                    "exceeded": True,
                },
            },
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
            "passenger_complement": 8,
            "crew_complement": 2,
            "vsp_triggered": True,
            "infection_counters": {
                "passenger_reported_case_rate": {
                    "value": 0.05,
                    "newly_confined": 0,
                    "exceeded": True,
                },
            },
        },
    ]
    derived = compute_derived_metrics(ts, num_agents=10)
    assert derived["reported_case_attack_rate_passenger"] == pytest.approx(0.3)
    assert derived["ever_ill_attack_rate_passenger"] == pytest.approx(0.3)
    assert derived["vsp_trigger_epoch"] == 1


def test_campaign_metrics_have_no_vsp_epoch_without_counter() -> None:
    ts = [
        {
            "epoch": 0,
            "infected": 1,
            "recovered": 0,
            "susceptible": 9,
            "passenger_complement": 8,
            "crew_complement": 2,
            "vsp_triggered": True,
        },
    ]
    assert compute_derived_metrics(ts, num_agents=10)["vsp_trigger_epoch"] is None


def test_timeseries_emits_reported_case_counter_fields() -> None:
    history = [{
        "summary": {
            "infected": 1,
            "recovered": 0,
            "susceptible": 9,
            "cumulative_ever_infected": 2,
            "cumulative_ever_infected_passenger": 1,
            "cumulative_ever_infected_crew": 1,
            "infection_attack_rate_passenger": 0.125,
            "infection_attack_rate_crew": 0.25,
            "ever_ill_rate_crew": 0.125,
            "reported_case_rate_crew": 0.0625,
        },
        "spaces": {},
        "cost_accounting": {},
        "infection_counters": {
            "passenger_reported_case_rate": {
                "value": 0.03125,
                "newly_confined": 3,
                "exceeded": True,
            },
        },
    }]
    series = extract_timeseries(history)
    assert series[0]["reported_case_rate_passenger"] == pytest.approx(0.03125)
    assert series[0]["passenger_reported_case_rate_newly_confined"] == 3
    assert series[0]["passenger_reported_case_rate_exceeded"] is True
    assert series[0]["cumulative_ever_infected"] == 2
    assert series[0]["cumulative_ever_infected_passenger"] == 1
    assert series[0]["cumulative_ever_infected_crew"] == 1
    assert series[0]["infection_attack_rate_passenger"] == pytest.approx(0.125)
    assert series[0]["infection_attack_rate_crew"] == pytest.approx(0.25)
    assert series[0]["ever_ill_rate_crew"] == pytest.approx(0.125)
    assert series[0]["reported_case_rate_crew"] == pytest.approx(0.0625)
    assert "vsp_triggered" not in series[0]
