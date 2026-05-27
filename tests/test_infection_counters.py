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

from orchestrator_epoch import compute_infection_counters, confine_agents
from orchestrator_types import (
    SimulationState,
    SYMPTOM_ASYMPTOMATIC,
    SYMPTOM_ASYMPTOMATIC_SHEDDING,
    SYMPTOM_SYMPTOMATIC,
)


def _agent(
    agent_id: int,
    symptom_status: str,
    agent_class: str = "passenger_general",
) -> dict[str, Any]:
    return {
        "agent_id": agent_id,
        "symptom_status": symptom_status,
        "agent_class": agent_class,
        "shedding_rate": 0.0,
    }


class TestComputeInfectionCounters:
    def test_attack_rate_by_role_group(self) -> None:
        agents = [
            _agent(0, SYMPTOM_SYMPTOMATIC, "crew_general"),
            _agent(1, SYMPTOM_ASYMPTOMATIC, "crew_general"),
            _agent(2, SYMPTOM_SYMPTOMATIC, "passenger_general"),
            _agent(3, SYMPTOM_ASYMPTOMATIC, "passenger_general"),
        ]
        defs = [
            {
                "counter_id": "crew_attack_rate",
                "metric": "attack_rate",
                "filter": {"role_group": "crew"},
            },
        ]
        results = compute_infection_counters(agents, defs)
        assert results["crew_attack_rate"]["value"] == 0.5
        assert results["crew_attack_rate"]["population"] == 2

    def test_threshold_exceeded(self) -> None:
        agents = [
            _agent(0, SYMPTOM_SYMPTOMATIC),
            _agent(1, SYMPTOM_SYMPTOMATIC),
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

    def test_threshold_not_exceeded(self) -> None:
        agents = [
            _agent(0, SYMPTOM_SYMPTOMATIC),
            _agent(1, SYMPTOM_ASYMPTOMATIC),
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
            _agent(0, SYMPTOM_ASYMPTOMATIC_SHEDDING),
            _agent(1, SYMPTOM_ASYMPTOMATIC),
        ]
        defs = [{"counter_id": "n_infected", "metric": "infected_count", "filter": {}}]
        results = compute_infection_counters(agents, defs)
        assert results["n_infected"]["value"] == 1.0

    def test_class_filter(self) -> None:
        agents = [
            _agent(0, SYMPTOM_SYMPTOMATIC, "crew_medical"),
            _agent(1, SYMPTOM_SYMPTOMATIC, "passenger_general"),
        ]
        defs = [
            {
                "counter_id": "medical_attack",
                "metric": "attack_rate",
                "filter": {"classes": ["crew_medical"]},
            },
        ]
        results = compute_infection_counters(agents, defs)
        assert results["medical_attack"]["value"] == 1.0
        assert results["medical_attack"]["population"] == 1


class TestExemptClassesConfinement:
    def test_exempt_class_skipped(self) -> None:
        state = SimulationState()
        agents = [
            _agent(0, SYMPTOM_SYMPTOMATIC, "crew_medical"),
            _agent(1, SYMPTOM_SYMPTOMATIC, "passenger_general"),
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
