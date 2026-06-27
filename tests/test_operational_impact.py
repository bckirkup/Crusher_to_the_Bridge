"""Tests for operational impact score accounting."""

from __future__ import annotations

import os
import sys

import pytest
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from crusher_labs.cost_ledger import compute_operational_impact


class TestComputeOperationalImpact:
    def test_galley_closure_by_zone_type(self) -> None:
        total, breakdown = compute_operational_impact(
            agents=[],
            quarantined_ids=set(),
            isolated_ids=set(),
            merged_modifiers={"close_zones": ["Galley", "Bridge"]},
            active_protocol_ids=[],
            ois_weights={"per_closed_galley_zone": 2.0, "galley_zone_types": ["galley"]},
            zone_type_by_id={"Galley": "galley", "Bridge": "command"},
        )
        assert total == pytest.approx(2.0)
        assert breakdown["closed_galley_zones"] == pytest.approx(2.0)

    def test_fleet_ppe_from_modifier(self) -> None:
        total, breakdown = compute_operational_impact(
            agents=[],
            quarantined_ids=set(),
            isolated_ids=set(),
            merged_modifiers={"ppe_transmission_reduction": 0.4},
            active_protocol_ids=[],
            ois_weights={"per_fleet_ppe_active": 0.1},
        )
        assert total == pytest.approx(0.1)
        assert breakdown["fleet_ppe"] == pytest.approx(0.1)
