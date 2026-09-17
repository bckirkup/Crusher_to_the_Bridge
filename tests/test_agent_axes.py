"""
test_agent_axes.py – Orthogonal agent status axes
"""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from telemetry_buffer.agent_axes import (
    COMPLIANCE_ISOLATED,
    COMPLIANCE_NON_COMPLIANT,
    INFECTION_INFECTED,
    INFECTION_SUSCEPTIBLE,
    PRESENTATION_ASYMPTOMATIC,
    PRESENTATION_SYMPTOMATIC,
    agent_axes_dict,
    agent_is_infected,
    agent_requires_confinement,
    clinical_axes_for_notebook,
    resolve_agent_axes,
)


class TestResolveAgentAxes:
    def test_missing_axes_default_to_susceptible(self) -> None:
        assert resolve_agent_axes({"agent_id": 1}) == (
            INFECTION_SUSCEPTIBLE,
            PRESENTATION_ASYMPTOMATIC,
            "compliant",
        )

    def test_legacy_symptom_status_is_ignored(self) -> None:
        agent = {"agent_id": 1, "symptom_status": "symptomatic"}
        assert not agent_is_infected(agent)
        assert clinical_axes_for_notebook(agent) == agent_axes_dict(
            INFECTION_SUSCEPTIBLE,
            PRESENTATION_ASYMPTOMATIC,
            "compliant",
        )

    def test_orthogonal_fields_preferred(self) -> None:
        agent = {
            "agent_id": 1,
            **agent_axes_dict(
                INFECTION_INFECTED,
                PRESENTATION_SYMPTOMATIC,
                COMPLIANCE_ISOLATED,
            ),
        }
        assert resolve_agent_axes(agent) == (
            INFECTION_INFECTED,
            PRESENTATION_SYMPTOMATIC,
            COMPLIANCE_ISOLATED,
        )

    def test_agent_helpers(self) -> None:
        agent = agent_axes_dict(
            INFECTION_INFECTED,
            PRESENTATION_SYMPTOMATIC,
            COMPLIANCE_NON_COMPLIANT,
        )
        agent["agent_id"] = 0
        assert agent_is_infected(agent)
        assert agent_requires_confinement(agent)
