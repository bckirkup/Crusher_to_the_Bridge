"""
test_contam_outcome_compare.py – helpers extracted from _summarize.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.contam_outcome_compare import (  # noqa: E402
    _agent_outcomes,
    _hvac_exposure_events,
)


def test_agent_outcomes_counts_non_susceptible() -> None:
    agents = [
        SimpleNamespace(infection_status="infected"),
        SimpleNamespace(infection_status="susceptible"),
        SimpleNamespace(infection_status=None),
        SimpleNamespace(infection_status="RECOVERED"),
    ]
    out = _agent_outcomes(agents)
    assert out["n_agents"] == 4
    assert out["n_infected"] == 2
    assert out["attack_rate"] == pytest.approx(0.5)


def test_agent_outcomes_empty() -> None:
    assert _agent_outcomes([]) == {
        "n_agents": 0, "n_infected": 0, "attack_rate": 0.0,
    }


def test_hvac_exposure_events_scans_top_level_and_nested() -> None:
    history = [
        "not-a-dict",
        {"transmission_summary": {"hvac_downstream_exposures": [1, 2]}},
        {"transmission": {"hvac_downstream_exposures": [3]}},
        {"hvac_downstream_exposures": [4], "exposures": [5]},
        {},
    ]
    assert _hvac_exposure_events(history) == 5


def test_hvac_exposure_events_empty() -> None:
    assert _hvac_exposure_events(None) == 0
    assert _hvac_exposure_events([]) == 0
