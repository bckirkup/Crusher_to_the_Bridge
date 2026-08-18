"""Boundaries of the extracted ShipSimulation epoch helpers."""

from __future__ import annotations

import math
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from picard_framework.simulation.ship_simulation import (  # noqa: E402
    _beliefs_from_information,
    _merge_applied,
)


class TestMergeApplied:
    def test_empty_extra_returns_current(self) -> None:
        current = {"by_actor": {"command": ["activate:SOP-1"]}}
        assert _merge_applied(current, {}) is current

    def test_empty_current_takes_extra(self) -> None:
        extra = {"by_actor": {"medical": ["noop"]}}
        assert _merge_applied({}, extra) == extra

    def test_later_envelope_overlays_keys(self) -> None:
        merged = _merge_applied(
            {"by_actor": {"command": ["a"]}, "keep": 1},
            {"by_actor": {"medical": ["b"]}, "added": 2},
        )
        assert merged["keep"] == 1
        assert merged["added"] == 2
        assert merged["by_actor"] == {"medical": ["b"]}


class TestBeliefsFromInformation:
    def test_severity_belief_grades_across_agents(self) -> None:
        severities = [0.1, 0.5, 0.9]
        info = {
            "agents": {
                str(i): {"severity_belief": sev, "trust_medical": 0.75}
                for i, sev in enumerate(severities)
            },
        }
        beliefs = _beliefs_from_information(info)
        seen = [beliefs[i]["severity_belief"] for i in range(len(severities))]
        assert seen == severities
        assert seen == sorted(seen)
        assert seen[-1] - seen[0] >= 0.7

    def test_beliefs_stay_finite_and_in_unit_interval(self) -> None:
        info = {
            "agents": {
                "3": {"severity_belief": 0.2, "trust_medical": 0.8},
                "9": {"severity_belief": 0.0, "trust_medical": 1.0},
            },
        }
        beliefs = _beliefs_from_information(info)
        for row in beliefs.values():
            assert math.isfinite(row["severity_belief"])
            assert math.isfinite(row["trust_medical"])
            assert 0.0 <= row["severity_belief"] <= 1.0
            assert 0.0 <= row["trust_medical"] <= 1.0

    def test_malformed_agent_keys_are_dropped(self) -> None:
        beliefs = _beliefs_from_information(
            {
                "agents": {
                    "not-an-id": {"severity_belief": 0.4},
                    "4": "not-a-dict",
                    "5": {"severity_belief": 0.3, "trust_medical": 0.6},
                },
            },
        )
        assert set(beliefs) == {5}

    def test_non_dict_information_yields_no_beliefs(self) -> None:
        assert _beliefs_from_information({"agents": ["x"]}) == {}
