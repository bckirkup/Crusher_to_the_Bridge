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

# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "0.1.0"

BUFFER_DIR = os.path.dirname(os.path.abspath(__file__))
GROUND_TRUTH_PATH = os.path.join(BUFFER_DIR, "ground_truth.json")


def make_agent(
    agent_id: int,
    symptom_status: str = "asymptomatic",
    shedding_rate: float = 0.0,
) -> dict[str, Any]:
    """Return a single agent state dictionary."""
    return {
        "agent_id": agent_id,
        "symptom_status": symptom_status,
        "shedding_rate": shedding_rate,
    }


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
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def read_ground_truth(path: str = GROUND_TRUTH_PATH) -> dict[str, Any]:
    """Deserialise and return the current ground-truth JSON file."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)
