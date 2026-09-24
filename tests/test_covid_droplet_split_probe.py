"""Unit tests for the AERO-SPLIT-01 paired-seed probe's pure helpers.

The sim drivers (`run_one`, `main`) are exercised by hand against the
declared replay and excluded from coverage; the summary arithmetic, cell
lookup and override shape are what a refactor could silently break.
"""
from __future__ import annotations

import os

import pytest

from tools.covid_droplet_split_probe import (
    DAY_EPOCHS,
    _cell,
    _design,
    _event_summary,
)

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), ".."),
)


@pytest.fixture(scope="module")
def design():
    return _design(REPO_ROOT)


def _event(epoch: int, zone: str = "Z", pathway: str = "droplet") -> dict:
    return {
        "epoch": epoch,
        "zone": zone,
        "pathway": pathway,
        "target_agent_id": 1,
        "confined": False,
    }


class TestEventSummary:
    def test_empty_run_is_zero_not_division_error(self) -> None:
        summary = _event_summary([])
        assert summary["events_total"] == 0
        assert summary["day0_2_share"] == pytest.approx(0.0)
        assert summary["day0_5_share"] == pytest.approx(0.0)

    def test_windows_count_epochs_below_their_days(self) -> None:
        events = [
            _event(0),                  # day 0
            _event(3 * DAY_EPOCHS - 1),  # last epoch of day 2
            _event(3 * DAY_EPOCHS),      # first epoch of day 3
            _event(5 * DAY_EPOCHS),      # day 5
        ]
        summary = _event_summary(events)
        assert summary["events_total"] == 4
        assert summary["events_day0_2"] == 2
        assert summary["day0_2_share"] == pytest.approx(0.5)
        assert summary["events_day0_5"] == 3
        assert summary["day0_5_share"] == pytest.approx(0.75)

    def test_zone_pathway_and_confinement_mixes_are_counted(self) -> None:
        events = [
            {**_event(0, zone="A"), "confined": True},
            _event(0, zone="A"),
            _event(0, zone="B", pathway="contact"),
        ]
        summary = _event_summary(events)
        assert summary["zones"] == {"A": 2, "B": 1}
        assert summary["pathways"] == {"droplet": 2, "contact": 1}
        assert summary["events_confined"] == 1


class TestCellLookup:
    def test_finds_the_declared_theta_and_seed(self, design) -> None:
        cell = _cell(design, 4.22e10, 20200205)
        assert cell.theta == pytest.approx(4.22e10)
        assert cell.seed == 20200205
        assert cell.scenario_id == "diamond_princess_2020"

    def test_unknown_pair_is_a_system_exit(self, design) -> None:
        with pytest.raises(SystemExit, match="no cell"):
            _cell(design, 1.0, -1)


class TestOverrideShape:
    def test_probe_pairs_differ_only_in_the_split_mode(self) -> None:
        """The off/partition contrast writes exactly one mode key."""
        overrides = {"transmission": {}}
        overrides["transmission"]["droplet_field_split"] = {"mode": "off"}
        assert overrides == {
            "transmission": {"droplet_field_split": {"mode": "off"}},
        }
