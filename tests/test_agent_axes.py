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
    PRESENTATION_SYMPTOMATIC,
    agent_axes_dict,
    agent_is_infected,
    agent_requires_confinement,
    axes_from_legacy_symptom_status,
    resolve_agent_axes,
)


class TestLegacyMapping:
    def test_symptomatic_infected(self) -> None:
        assert axes_from_legacy_symptom_status("symptomatic") == (
            INFECTION_INFECTED,
            PRESENTATION_SYMPTOMATIC,
            "compliant",
        )

    def test_isolated_preserves_infection(self) -> None:
        inf, _pres, comp = axes_from_legacy_symptom_status("isolated")
        assert inf == INFECTION_INFECTED
        assert comp == COMPLIANCE_ISOLATED


class TestResolveAgentAxes:
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
