"""
test_data_contracts.py – Validate JSON data files against their schemas
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Ensures all configuration files conform to their JSON Schema definitions
and that cross-file referential integrity is maintained.
"""

from __future__ import annotations

import json
import os
from typing import Any

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(REPO_ROOT, "data")
SCHEMA_DIR = os.path.join(REPO_ROOT, "schemas")


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


# ── Schema structure tests ────────────────────────────────────────────


class TestPathogenProfiles:
    """Validate data/pathogens/active_profiles.json."""

    @pytest.fixture
    def profiles(self) -> dict:
        return _load_json(os.path.join(DATA_DIR, "pathogens", "active_profiles.json"))

    def test_has_pathogens_key(self, profiles: dict) -> None:
        assert "pathogens" in profiles
        assert isinstance(profiles["pathogens"], list)
        assert len(profiles["pathogens"]) >= 1

    def test_each_pathogen_has_required_fields(self, profiles: dict) -> None:
        required = {"pathogen_id", "name", "transmission_routes"}
        for p in profiles["pathogens"]:
            missing = required - set(p.keys())
            assert not missing, f"Pathogen '{p.get('name', '?')}' missing: {missing}"

    def test_pathogen_ids_unique(self, profiles: dict) -> None:
        ids = [p["pathogen_id"] for p in profiles["pathogens"]]
        assert len(ids) == len(set(ids)), f"Duplicate pathogen_id found: {ids}"

    def test_dose_response_valid(self, profiles: dict) -> None:
        for p in profiles["pathogens"]:
            if "dose_response" in p:
                dr = p["dose_response"]
                assert dr.get("alpha", 0) > 0, f"{p['pathogen_id']}: alpha must be > 0"
                assert dr.get("beta", 0) > 0, f"{p['pathogen_id']}: beta must be > 0"

    def test_shedding_curve_length(self, profiles: dict) -> None:
        for p in profiles["pathogens"]:
            if "shedding_curve_log10" in p:
                curve = p["shedding_curve_log10"]
                assert len(curve) >= 1, f"{p['pathogen_id']}: empty shedding curve"
                assert all(isinstance(v, (int, float)) for v in curve)

    def test_transmission_routes_valid(self, profiles: dict) -> None:
        valid_routes = {"direct_contact", "fomite", "droplet", "hvac_airborne"}
        for p in profiles["pathogens"]:
            routes = set(p["transmission_routes"])
            invalid = routes - valid_routes
            assert not invalid, f"{p['pathogen_id']}: invalid routes {invalid}"


class TestSpatialLayout:
    """Validate data/platforms/destroyer_baseline/spatial_layout.json."""

    @pytest.fixture
    def layout(self) -> dict:
        return _load_json(
            os.path.join(DATA_DIR, "platforms", "destroyer_baseline", "spatial_layout.json")
        )

    def test_has_zones(self, layout: dict) -> None:
        assert "zones" in layout
        assert len(layout["zones"]) >= 1

    def test_zone_ids_unique(self, layout: dict) -> None:
        ids = [z["id"] for z in layout["zones"]]
        assert len(ids) == len(set(ids)), f"Duplicate zone ids: {ids}"

    def test_zones_have_positive_volume(self, layout: dict) -> None:
        for z in layout["zones"]:
            assert z.get("volume_m3", 0) > 0, f"Zone '{z['id']}' has non-positive volume"

    def test_zones_have_display_coords(self, layout: dict) -> None:
        for z in layout["zones"]:
            assert "display" in z, f"Zone '{z['id']}' missing display coordinates"
            assert "x" in z["display"] and "y" in z["display"]


class TestAirFlowPaths:
    """Validate data/platforms/destroyer_baseline/air_flow_paths.json."""

    @pytest.fixture
    def paths(self) -> dict:
        return _load_json(
            os.path.join(DATA_DIR, "platforms", "destroyer_baseline", "air_flow_paths.json")
        )

    @pytest.fixture
    def zone_ids(self) -> set[str]:
        layout = _load_json(
            os.path.join(DATA_DIR, "platforms", "destroyer_baseline", "spatial_layout.json")
        )
        return {z["id"] for z in layout["zones"]}

    @pytest.fixture
    def hvac_zone_ids(self) -> set[str]:
        paths = _load_json(
            os.path.join(DATA_DIR, "platforms", "destroyer_baseline", "air_flow_paths.json")
        )
        return {hz["id"] for hz in paths.get("hvac_zones", [])}

    def test_hvac_zone_rooms_exist(self, paths: dict, zone_ids: set[str]) -> None:
        for hz in paths.get("hvac_zones", []):
            for room in hz["rooms"]:
                assert room in zone_ids, (
                    f"HVAC zone '{hz['id']}' references non-existent room '{room}'"
                )

    def test_cross_zone_links_reference_valid_hvac_zones(
        self, paths: dict, hvac_zone_ids: set[str]
    ) -> None:
        for link in paths.get("cross_zone_links", []):
            assert link["from"] in hvac_zone_ids, (
                f"Cross-zone link references non-existent HVAC zone '{link['from']}'"
            )
            assert link["to"] in hvac_zone_ids, (
                f"Cross-zone link references non-existent HVAC zone '{link['to']}'"
            )

    def test_adjacency_references_valid_zones(
        self, paths: dict, zone_ids: set[str]
    ) -> None:
        for edge in paths.get("adjacency", []):
            assert edge["from"] in zone_ids, (
                f"Adjacency edge references non-existent zone '{edge['from']}'"
            )
            assert edge["to"] in zone_ids, (
                f"Adjacency edge references non-existent zone '{edge['to']}'"
            )

    def test_flow_rates_non_negative(self, paths: dict) -> None:
        for link in paths.get("cross_zone_links", []):
            assert link.get("flow_rate_m3h", 0) >= 0, (
                f"Negative flow rate in link {link['from']} -> {link['to']}"
            )


class TestProtocols:
    """Validate data/config/protocols.json."""

    @pytest.fixture
    def protocols(self) -> dict:
        return _load_json(os.path.join(DATA_DIR, "config", "protocols.json"))

    def test_has_protocols_key(self, protocols: dict) -> None:
        assert "protocols" in protocols
        assert isinstance(protocols["protocols"], list)
        assert len(protocols["protocols"]) >= 1

    def test_protocol_ids_unique(self, protocols: dict) -> None:
        ids = [p["protocol_id"] for p in protocols["protocols"]]
        assert len(ids) == len(set(ids)), f"Duplicate protocol_id: {ids}"

    def test_trigger_stoplights_valid(self, protocols: dict) -> None:
        valid_levels = {"GREEN", "AMBER", "RED"}
        for p in protocols["protocols"]:
            trigger = p.get("trigger", {})
            level = trigger.get("stoplight_level", "").upper()
            assert level in valid_levels, (
                f"Protocol '{p['protocol_id']}' has invalid stoplight: '{level}'"
            )


class TestResourceCosts:
    """Validate data/config/resource_costs.json."""

    @pytest.fixture
    def costs(self) -> dict:
        return _load_json(os.path.join(DATA_DIR, "config", "resource_costs.json"))

    def test_budget_positive(self, costs: dict) -> None:
        budget = costs.get("budgets", {}).get("financial_usd", {}).get("starting_balance", 0)
        assert budget > 0, "Starting financial balance must be positive"

    def test_labor_capacity_positive(self, costs: dict) -> None:
        labor = costs.get("budgets", {}).get("labor_person_hours", {}).get("starting_capacity", 0)
        assert labor > 0, "Starting labor capacity must be positive"

    def test_material_inventory_has_items(self, costs: dict) -> None:
        inventory = costs.get("material_inventory", {})
        assert len(inventory) >= 1, "Material inventory must have at least one item"

    def test_material_costs_non_negative(self, costs: dict) -> None:
        for item, data in costs.get("material_inventory", {}).items():
            assert data.get("unit_cost_usd", 0) >= 0, (
                f"Material '{item}' has negative unit cost"
            )
            assert data.get("starting_count", 0) >= 0, (
                f"Material '{item}' has negative starting count"
            )
