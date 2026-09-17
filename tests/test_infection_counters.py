"""
test_infection_counters.py – Configurable infection counter metrics (PR #45)
"""

from __future__ import annotations

import os
import sys
from typing import Any
from unittest.mock import MagicMock

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from crusher_labs import load_config
from orchestrator_epoch import (
    compute_infection_counters,
    confine_agents,
    step_counter_thresholds,
)
from orchestrator_init import build_engine
from orchestrator_types import SimulationState
from telemetry_buffer.agent_axes import (
    COMPLIANCE_COMPLIANT,
    INFECTION_INFECTED,
    INFECTION_SUSCEPTIBLE,
    PRESENTATION_ASYMPTOMATIC,
    PRESENTATION_SYMPTOMATIC,
    agent_axes_dict,
)


def _agent(
    agent_id: int,
    infection: str,
    presentation: str,
    agent_class: str = "passenger_general",
) -> dict[str, Any]:
    return {
        "agent_id": agent_id,
        **agent_axes_dict(infection, presentation, COMPLIANCE_COMPLIANT),
        "agent_class": agent_class,
        "shedding_rate": 0.0,
    }


def _susceptible(
    agent_id: int, agent_class: str = "passenger_general",
) -> dict[str, Any]:
    return _agent(
        agent_id, INFECTION_SUSCEPTIBLE, PRESENTATION_ASYMPTOMATIC, agent_class,
    )


def _symptomatic(
    agent_id: int, agent_class: str = "passenger_general",
) -> dict[str, Any]:
    return _agent(
        agent_id, INFECTION_INFECTED, PRESENTATION_SYMPTOMATIC, agent_class,
    )


def _asymptomatic_shedding(
    agent_id: int, agent_class: str = "passenger_general",
) -> dict[str, Any]:
    return _agent(
        agent_id, INFECTION_INFECTED, PRESENTATION_ASYMPTOMATIC, agent_class,
    )


class TestComputeInfectionCounters:
    def test_attack_rate_by_role_group(self) -> None:
        agents = [
            _symptomatic(0, "crew_general"),
            _susceptible(1, "crew_general"),
            _symptomatic(2, "passenger_general"),
            _susceptible(3, "passenger_general"),
        ]
        defs = [
            {
                "counter_id": "crew_attack_rate",
                "metric": "attack_rate",
                "filter": {"role_group": "crew"},
            },
        ]
        results = compute_infection_counters(agents, defs)
        assert results["crew_attack_rate"]["value"] == pytest.approx(0.5)
        assert results["crew_attack_rate"]["population"] == 2

    def test_threshold_exceeded(self) -> None:
        agents = [
            _symptomatic(0),
            _symptomatic(1),
        ]
        defs = [
            {
                "counter_id": "all_attack_rate",
                "metric": "attack_rate",
                "filter": {},
                "threshold": 0.5,
            },
        ]
        results = compute_infection_counters(agents, defs)
        assert results["all_attack_rate"]["exceeded"] is True

    def test_attack_rate_alias_matches_symptomatic_prevalence(self) -> None:
        agents = [
            _symptomatic(0),
            _susceptible(1),
        ]
        defs = [
            {"counter_id": "legacy", "metric": "attack_rate"},
            {"counter_id": "canonical", "metric": "symptomatic_prevalence"},
        ]
        results = compute_infection_counters(agents, defs)
        assert results["legacy"]["value"] == results["canonical"]["value"]
        assert results["legacy"]["value"] == pytest.approx(0.5)

    def test_threshold_not_exceeded(self) -> None:
        agents = [
            _symptomatic(0),
            _susceptible(1),
        ]
        defs = [
            {
                "counter_id": "all_attack_rate",
                "metric": "attack_rate",
                "filter": {},
                "threshold": 0.75,
            },
        ]
        results = compute_infection_counters(agents, defs)
        assert results["all_attack_rate"]["exceeded"] is False

    def test_infected_count_metric(self) -> None:
        agents = [
            _asymptomatic_shedding(0),
            _susceptible(1),
        ]
        defs = [{"counter_id": "n_infected", "metric": "infected_count", "filter": {}}]
        results = compute_infection_counters(agents, defs)
        assert results["n_infected"]["value"] == pytest.approx(1.0)

    def test_class_filter(self) -> None:
        agents = [
            _symptomatic(0, "crew_medical"),
            _symptomatic(1, "passenger_general"),
        ]
        defs = [
            {
                "counter_id": "medical_attack",
                "metric": "attack_rate",
                "filter": {"classes": ["crew_medical"]},
            },
        ]
        results = compute_infection_counters(agents, defs)
        assert results["medical_attack"]["value"] == pytest.approx(1.0)
        assert results["medical_attack"]["population"] == 1

    def test_reported_case_rate_uses_unique_ids_and_handles_empty_groups(self) -> None:
        agents = [
            _susceptible(0, "passenger_general"),
            _susceptible(1, "passenger_general"),
            _susceptible(2, "crew_general"),
            _susceptible(3, "crew_general"),
        ]
        defs = [
            {
                "counter_id": "passenger_reported_case_rate",
                "metric": "reported_case_rate",
                "filter": {"role_group": "passenger"},
            },
            {
                "counter_id": "crew_reported_case_rate",
                "metric": "reported_case_rate",
                "filter": {"role_group": "crew"},
            },
            {
                "counter_id": "empty_reported_case_rate",
                "metric": "reported_case_rate",
                "filter": {"classes": ["missing_class"]},
            },
        ]
        results = compute_infection_counters(
            agents,
            defs,
            ever_reported_ids={0, 2},
        )
        assert results["passenger_reported_case_rate"]["value"] == pytest.approx(0.5)
        assert results["crew_reported_case_rate"]["value"] == pytest.approx(0.5)
        assert results["empty_reported_case_rate"]["value"] == 0.0

        omitted = compute_infection_counters(agents, defs)
        assert omitted["passenger_reported_case_rate"]["value"] == 0.0

    def test_reported_case_rate_uses_zero_for_empty_population(self) -> None:
        defs = [{
            "counter_id": "reported_case_rate",
            "metric": "reported_case_rate",
            "filter": {"classes": ["missing_class"]},
        }]
        results = compute_infection_counters(
            [_susceptible(0)],
            defs,
            ever_reported_ids={0},
        )
        assert results["reported_case_rate"]["population"] == 0
        assert results["reported_case_rate"]["value"] == 0.0


class TestExemptClassesConfinement:
    def test_exempt_class_skipped(self) -> None:
        state = SimulationState()
        agents = [
            _symptomatic(0, "crew_medical"),
            _symptomatic(1, "passenger_general"),
        ]
        syndromic = MagicMock()
        syndromic.check_quarantine_compliance.return_value = True
        confine_agents(
            1, agents, state, syndromic,
            include_shedding=False,
            exempt_classes={"crew_medical"},
        )
        assert 0 not in state.quarantined_ids
        assert 1 in state.quarantined_ids


class TestCounterConfinementEnabled:
    def test_step_counter_thresholds_confines_when_exceeded(self) -> None:
        state = SimulationState()
        agents = [
            _symptomatic(0),
            _symptomatic(1),
        ]
        defs = [{
            "counter_id": "all_attack_rate",
            "metric": "attack_rate",
            "filter": {},
            "threshold": 0.03,
            "on_exceed": "confine_symptomatic",
        }]
        results = compute_infection_counters(agents, defs)
        assert results["all_attack_rate"]["exceeded"] is True
        syndromic = MagicMock()
        syndromic.check_quarantine_compliance.return_value = True
        step_counter_thresholds(1, agents, results, defs, state, syndromic)
        assert 0 in state.quarantined_ids
        assert 1 in state.quarantined_ids

    def test_counter_confinement_disabled_leaves_agents_free(self) -> None:
        """Config sensitivity: confinement_enabled=False skips confine actions."""
        state = SimulationState()
        agents = [
            _symptomatic(0),
            _symptomatic(1),
        ]
        defs = [{
            "counter_id": "all_attack_rate",
            "metric": "attack_rate",
            "filter": {},
            "threshold": 0.03,
            "on_exceed": "confine_symptomatic",
        }]
        results = compute_infection_counters(agents, defs)
        syndromic = MagicMock()
        syndromic.check_quarantine_compliance.return_value = True
        step_counter_thresholds(
            1, agents, results, defs, state, syndromic,
            confinement_enabled=False,
        )
        assert state.quarantined_ids == set()
        assert results["all_attack_rate"]["exceeded"] is True
        assert results["all_attack_rate"]["newly_confined"] == 0

    def test_reported_case_threshold_replaces_prevalence_trigger(self) -> None:
        state = SimulationState()
        agents = [
            _symptomatic(0, "passenger_general"),
            _symptomatic(1, "passenger_general"),
        ]
        defs = [{
            "counter_id": "passenger_reported_case_rate",
            "metric": "reported_case_rate",
            "filter": {"role_group": "passenger"},
            "threshold": 0.03,
            "on_exceed": "confine_symptomatic",
        }]
        syndromic = MagicMock()
        syndromic.check_quarantine_compliance.return_value = True

        prevalence_only = compute_infection_counters(agents, defs)
        step_counter_thresholds(
            1, agents, prevalence_only, defs, state, syndromic,
        )
        assert prevalence_only["passenger_reported_case_rate"]["value"] == 0.0
        assert state.quarantined_ids == set()

        reported = compute_infection_counters(
            agents, defs, ever_reported_ids={0},
        )
        step_counter_thresholds(
            2, agents, reported, defs, state, syndromic,
        )
        assert reported["passenger_reported_case_rate"]["value"] == 0.5
        assert reported["passenger_reported_case_rate"]["newly_confined"] == 2
        assert state.quarantined_ids == {0, 1}

    def test_counter_confinement_reports_only_newly_confined_agents(self) -> None:
        state = SimulationState(quarantined_ids={0})
        agents = [
            _symptomatic(0),
            _symptomatic(1),
        ]
        defs = [{
            "counter_id": "passenger_reported_case_rate",
            "metric": "reported_case_rate",
            "filter": {"role_group": "passenger"},
            "threshold": 0.03,
            "on_exceed": "confine_symptomatic",
        }]
        results = compute_infection_counters(
            agents, defs, ever_reported_ids={0, 1},
        )
        syndromic = MagicMock()
        syndromic.check_quarantine_compliance.return_value = True

        step_counter_thresholds(1, agents, results, defs, state, syndromic)

        assert results["passenger_reported_case_rate"]["newly_confined"] == 1
        assert state.quarantined_ids == {0, 1}


class TestVSPCounterConfiguration:
    def test_build_engine_keeps_internal_vsp_disabled(self) -> None:
        engine = build_engine(load_config(), seed=42)
        assert engine.vsp_isolation is False

    def test_shipped_config_uses_reported_case_vsp_counter(self) -> None:
        counters = load_config()["ship_graph"]["infection_counters"]
        by_id = {counter["counter_id"]: counter for counter in counters}
        assert "on_exceed" not in by_id["all_attack_rate"]
        assert by_id["passenger_reported_case_rate"]["threshold"] == 0.03
        assert (
            by_id["passenger_reported_case_rate"]["on_exceed"]
            == "confine_symptomatic"
        )
        assert by_id["crew_reported_case_rate"]["metric"] == "reported_case_rate"
        assert by_id["all_reported_case_rate"]["metric"] == "reported_case_rate"
        assert "threshold" not in by_id["crew_reported_case_rate"]
        assert "threshold" not in by_id["all_reported_case_rate"]
