"""
telemetry_buffer.schema
~~~~~~~~~~~~~~~~~~~~~~~

Canonical JSON exchange schema for the Crusher-to-the-Bridge data broker.

The simulation engine ("The Bridge") writes one of these payloads per epoch
into ``ground_truth.json``.  Crusher Labs reads the same file to produce
noisy, modality-specific sensor telemetry.
"""

from __future__ import annotations

import json
import os
from typing import Any

from simulation_utils.paths import is_path_under_base
from telemetry_buffer.agent_axes import (
    COMPLIANCE_COMPLIANT,
    INFECTION_SUSCEPTIBLE,
    PRESENTATION_ASYMPTOMATIC,
    agent_axes_dict,
)

# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "0.3.0"

BUFFER_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(BUFFER_DIR)
GROUND_TRUTH_PATH = os.path.join(BUFFER_DIR, "ground_truth.json")


def _validated_ground_truth_path(path: str) -> str:
    resolved = os.path.realpath(path)
    allowed_roots = (BUFFER_DIR, REPO_ROOT)
    if not any(is_path_under_base(root, resolved) for root in allowed_roots):
        raise ValueError(
            f"Ground-truth path must stay under repository or telemetry_buffer: {path!r}",
        )
    return resolved


def make_agent(
    agent_id: int,
    infection_state: str = INFECTION_SUSCEPTIBLE,
    symptom_presentation: str = PRESENTATION_ASYMPTOMATIC,
    compliance_status: str = COMPLIANCE_COMPLIANT,
    shedding_rate: float = 0.0,
    location: str | None = None,
    agent_class: str | None = None,
    gender: str | None = None,
    *,
    symptom_status: str | None = None,
) -> dict[str, Any]:
    """Return a single agent state dictionary with orthogonal status axes.

    ``symptom_status`` is accepted only for backward-compatible call sites
    and is not written to the output dict.
    """
    if symptom_status is not None:
        from telemetry_buffer.agent_axes import axes_from_legacy_symptom_status

        infection_state, symptom_presentation, compliance_status = (
            axes_from_legacy_symptom_status(symptom_status)
        )

    d: dict[str, Any] = {
        "agent_id": agent_id,
        **agent_axes_dict(infection_state, symptom_presentation, compliance_status),
        "shedding_rate": shedding_rate,
    }
    if location is not None:
        d["location"] = location
    if agent_class is not None:
        d["agent_class"] = agent_class
    if gender is not None:
        d["gender"] = gender
    return d


def make_space(
    pathogen_mass: float = 0.0,
    microbiome_id: str = "baseline",
) -> dict[str, Any]:
    """Return a single space/zone state dictionary."""
    return {
        "pathogen_mass": pathogen_mass,
        "microbiome_id": microbiome_id,
    }


def make_ground_truth(
    epoch: int,
    agents: list[dict[str, Any]],
    spaces: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build a full ground-truth payload for one simulation step.

    Parameters
    ----------
    epoch:
        The current simulation time-step (0-indexed).
    agents:
        A list of agent state dicts (see :func:`make_agent`).
    spaces:
        A mapping of zone/room IDs to space state dicts (see
        :func:`make_space`).

    Returns
    -------
    dict
        The canonical ground-truth dictionary ready for JSON serialisation.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "epoch": epoch,
        "agents": agents,
        "spaces": spaces,
    }


# ---------------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------------

def write_ground_truth(payload: dict[str, Any], path: str = GROUND_TRUTH_PATH) -> None:
    """Serialise *payload* to the ground-truth JSON file."""
    safe_path = _validated_ground_truth_path(path)
    with open(safe_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def read_ground_truth(path: str = GROUND_TRUTH_PATH) -> dict[str, Any]:
    """Deserialise and return the current ground-truth JSON file."""
    safe_path = _validated_ground_truth_path(path)
    with open(safe_path, "r", encoding="utf-8") as fh:
        return json.load(fh)
