"""Unit tests for the onset-funnel readout's decomposition math.

The readout only restates committed payload echoes, so its correctness
is the bookkeeping on ``funnel_hosts`` + ``campaign_specimen_log``;
these pin it on synthetic cells.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location(
        "covid_onset_funnel_readout",
        _ROOT / "tools" / "covid_onset_funnel_readout.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _cell_payload(
    hosts: dict[int, dict[str, int]],
    log: list[dict],
    observables: dict | None = None,
) -> dict:
    return {
        "arm_id": "boxed_s1s2",
        "design_id": "covid_crew_reach_01",
        "observables": observables or {},
        "funnel_hosts": {str(k): v for k, v in hosts.items()},
        "campaign_specimen_log": log,
    }


def test_channel_split_campaign_vs_passive(mod):
    payload = _cell_payload(
        hosts={
            1: {"infection_day": 3, "presented_day": 9, "confirmed_day": 16},
            2: {"infection_day": 4, "presented_day": 10, "confirmed_day": 8},
        },
        log=[
            {"agent_id": 1, "day": 16, "positive": True},
            {"agent_id": 2, "day": 16, "positive": True},
        ],
    )
    cell = mod._decompose_cell(payload)
    # Host 1's confirming specimen is the day-16 campaign swab; host 2 was
    # confirmed on day 8 before that campaign day.
    assert cell["confirmed_channel"] == {"campaign": 1, "passive": 1}
    assert cell["confirmed_pre_onset_catch"] == 1
    assert cell["confirmed_never_presented"] == 0


def test_campaign_positive_hosts_split(mod):
    payload = _cell_payload(
        hosts={
            1: {"infection_day": 3, "presented_day": 9},
            2: {"infection_day": 4, "presented_day": 7},
            3: {"infection_day": 5},
        },
        log=[
            {"agent_id": 1, "day": 8, "positive": True},
            {"agent_id": 2, "day": 10, "positive": True},
            {"agent_id": 3, "day": 10, "positive": True},
        ],
    )
    cell = mod._decompose_cell(payload)
    assert cell["campaign_positive_hosts"] == {
        "never_presented": 1,
        "pre_onset": 1,
        "post_onset": 1,
    }


def test_unconfirmed_drain_modes(mod):
    payload = _cell_payload(
        hosts={
            1: {"infection_day": 3},  # never swabbed
            2: {"infection_day": 6, "specimen_day": 2},  # pre-infection swab
            3: {"infection_day": 4, "specimen_day": 9, "presented_day": 12},
            4: {"infection_day": 5, "specimen_day": 10},
        },
        log=[],
    )
    drains = mod._decompose_cell(payload)["unconfirmed_infected_drains"]
    assert drains == {
        "never_swabbed_never_presented": 1,
        "swabbed_only_pre_infection_never_presented": 1,
        "swabbed_while_infected_negative_presented": 1,
        "swabbed_while_infected_negative_never_presented": 1,
    }


def test_dated_share_and_pool_medians_skip_dead_cells(mod):
    live = mod._decompose_cell(
        _cell_payload(
            hosts={
                1: {"infection_day": 1, "presented_day": 2, "confirmed_day": 3},
                2: {"infection_day": 2},
            },
            log=[],
            observables={"recorded_onsets": 1, "seed": 7},
        )
    )
    dead = mod._decompose_cell(
        _cell_payload(hosts={}, log=[], observables={"recorded_onsets": 0})
    )
    assert live["dated_share_of_confirmed"] == pytest.approx(1.0)
    pooled = mod._pool([live, dead])
    assert pooled["cells"] == 2
    assert pooled["takeoff_cells"] == 1
    assert pooled["medians"]["infections_total"] == 2
    assert pooled["recorded_onsets"] == 1
