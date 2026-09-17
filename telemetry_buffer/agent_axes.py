"""
telemetry_buffer.agent_axes
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Orthogonal agent state axes for ground-truth and simulation telemetry.

A single combined status string cannot represent infection biology,
clinical presentation, and FRED compliance confinement at once.  Agents
carry three independent fields instead; ``infection_state``,
``symptom_presentation`` and ``compliance_status`` are the only status
representation.
"""

from __future__ import annotations

from typing import Any

# ── Infection state (SIR / immune) ───────────────────────────────────────

INFECTION_SUSCEPTIBLE = "susceptible"
INFECTION_INFECTED = "infected"
INFECTION_RECOVERED = "recovered"
INFECTION_IMMUNE = "immune"

# ── Symptom presentation (clinical) ────────────────────────────────────

PRESENTATION_ASYMPTOMATIC = "asymptomatic"
PRESENTATION_MILD = "mild"
PRESENTATION_SYMPTOMATIC = "symptomatic"
PRESENTATION_SEVERE = "severe"

# ── Behavioral compliance (FRED confinement) ─────────────────────────────

COMPLIANCE_COMPLIANT = "compliant"
COMPLIANCE_NON_COMPLIANT = "non_compliant"
COMPLIANCE_ISOLATED = "isolated"
COMPLIANCE_QUARANTINED = "quarantined"

# Sets used by counters and syndromic logic
PRESENTATION_SYMPTOMATIC_LEVELS = frozenset({
    PRESENTATION_MILD,
    PRESENTATION_SYMPTOMATIC,
    PRESENTATION_SEVERE,
})


def resolve_agent_axes(raw: dict[str, Any]) -> tuple[str, str, str]:
    """Return (infection_state, symptom_presentation, compliance_status).

    Missing axes default to a susceptible, asymptomatic, compliant agent.
    """
    return (
        str(raw.get("infection_state", INFECTION_SUSCEPTIBLE)),
        str(raw.get("symptom_presentation", PRESENTATION_ASYMPTOMATIC)),
        str(raw.get("compliance_status", COMPLIANCE_COMPLIANT)),
    )


def agent_axes_dict(
    infection_state: str,
    symptom_presentation: str,
    compliance_status: str,
) -> dict[str, str]:
    return {
        "infection_state": infection_state,
        "symptom_presentation": symptom_presentation,
        "compliance_status": compliance_status,
    }


def agent_is_infected(agent: dict[str, Any]) -> bool:
    infection, _, _ = resolve_agent_axes(agent)
    return infection == INFECTION_INFECTED


def agent_has_symptomatic_presentation(agent: dict[str, Any]) -> bool:
    _, presentation, _ = resolve_agent_axes(agent)
    return presentation in PRESENTATION_SYMPTOMATIC_LEVELS


def agent_requires_confinement(agent: dict[str, Any]) -> bool:
    """True when agent is clinically symptomatic or refusing quarantine."""
    _, presentation, compliance = resolve_agent_axes(agent)
    if compliance == COMPLIANCE_NON_COMPLIANT:
        return True
    return presentation in PRESENTATION_SYMPTOMATIC_LEVELS


def agent_is_isolated(agent: dict[str, Any]) -> bool:
    _, _, compliance = resolve_agent_axes(agent)
    return compliance == COMPLIANCE_ISOLATED


def clinical_axes_for_notebook(data: dict[str, Any]) -> dict[str, str]:
    """Extract orthogonal axes for lab-notebook clinical records."""
    return agent_axes_dict(*resolve_agent_axes(data))
