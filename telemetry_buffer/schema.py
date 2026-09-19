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

from simulation_utils.paths import is_path_under_base, resolve_repo_path
from telemetry_buffer.agent_axes import (
    COMPLIANCE_COMPLIANT,
    INFECTION_SUSCEPTIBLE,
    PRESENTATION_ASYMPTOMATIC,
    agent_axes_dict,
)
from telemetry_buffer.fields import (
    AGENT_CLASS,
    AGENT_GENDER,
    AGENT_ID,
    AGENT_LOCATION,
    AGENT_SHEDDING_RATE,
    RECORD_AGENTS,
    RECORD_EPOCH,
    RECORD_SPACES,
    ZONE_MICROBIOME_ID,
    ZONE_PATHOGEN_MASS,
)

# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "0.3.0"

BUFFER_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(BUFFER_DIR)
TELEMETRY_DIR_ENV = "CTTB_TELEMETRY_DIR"
TELEMETRY_BUFFER_DIRNAME = "telemetry_buffer"
GROUND_TRUTH_FILENAME = "ground_truth.json"
SIMULATION_HISTORY_FILENAME = "simulation_history.json"
LAB_NOTEBOOK_FILENAME = "artificial_lab_notebook.json"


def telemetry_dir(repo_root: str = REPO_ROOT) -> str:
    """Directory holding the default telemetry artifacts; CTTB_TELEMETRY_DIR overrides it."""
    override = os.environ.get(TELEMETRY_DIR_ENV)
    return os.path.realpath(override) if override else os.path.join(repo_root, TELEMETRY_BUFFER_DIRNAME)


def default_ground_truth_path(repo_root: str = REPO_ROOT) -> str:
    return os.path.join(telemetry_dir(repo_root), GROUND_TRUTH_FILENAME)


def default_simulation_history_path(repo_root: str = REPO_ROOT) -> str:
    return os.path.join(telemetry_dir(repo_root), SIMULATION_HISTORY_FILENAME)


def default_lab_notebook_path(repo_root: str = REPO_ROOT) -> str:
    return os.path.join(telemetry_dir(repo_root), LAB_NOTEBOOK_FILENAME)


def resolve_telemetry_path(path: str, repo_root: str = REPO_ROOT) -> str:
    """Resolve a configured telemetry artifact path.

    Relative paths under ``telemetry_buffer/`` follow :func:`telemetry_dir`;
    other relative paths resolve under *repo_root*; absolute paths are kept.
    """
    if os.path.isabs(path):
        return os.path.realpath(path)
    parts = os.path.normpath(path).split(os.sep)
    if parts[0] == TELEMETRY_BUFFER_DIRNAME:
        return os.path.realpath(os.path.join(telemetry_dir(repo_root), *parts[1:]))
    return resolve_repo_path(repo_root, path)


# Legacy import-time snapshot; prefer default_ground_truth_path(), which
# honours CTTB_TELEMETRY_DIR at call time.
GROUND_TRUTH_PATH = default_ground_truth_path()


def _validated_ground_truth_path(path: str) -> str:
    resolved = os.path.realpath(path)
    allowed_roots = (BUFFER_DIR, REPO_ROOT, telemetry_dir())
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
) -> dict[str, Any]:
    """Return a single agent state dictionary with orthogonal status axes."""
    d: dict[str, Any] = {
        AGENT_ID: agent_id,
        **agent_axes_dict(infection_state, symptom_presentation, compliance_status),
        AGENT_SHEDDING_RATE: shedding_rate,
    }
    if location is not None:
        d[AGENT_LOCATION] = location
    if agent_class is not None:
        d[AGENT_CLASS] = agent_class
    if gender is not None:
        d[AGENT_GENDER] = gender
    return d


def make_space(
    pathogen_mass: float = 0.0,
    microbiome_id: str = "baseline",
) -> dict[str, Any]:
    """Return a single space/zone state dictionary."""
    return {
        ZONE_PATHOGEN_MASS: pathogen_mass,
        ZONE_MICROBIOME_ID: microbiome_id,
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
        RECORD_EPOCH: epoch,
        RECORD_AGENTS: agents,
        RECORD_SPACES: spaces,
    }


# ---------------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------------

def write_ground_truth(payload: dict[str, Any], path: str | None = None) -> None:
    """Serialise *payload* to the ground-truth JSON file.

    Writes a per-process temp file and renames it into place: the default
    path is shared by every ShipSimulation in the checkout, so under
    parallel test workers a direct write can be read mid-serialisation.
    """
    safe_path = _validated_ground_truth_path(path or default_ground_truth_path())
    tmp_path = f"{safe_path}.tmp-{os.getpid()}"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    os.replace(tmp_path, safe_path)


def read_ground_truth(path: str | None = None) -> dict[str, Any]:
    """Deserialise and return the current ground-truth JSON file."""
    safe_path = _validated_ground_truth_path(path or default_ground_truth_path())
    with open(safe_path, "r", encoding="utf-8") as fh:
        return json.load(fh)
