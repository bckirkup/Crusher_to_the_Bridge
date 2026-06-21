"""
test_scripts_tools.py – Tests for scripts/ and tools/gis_spatial_bridge.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Covers:
- blueprint_shapes hull and compartment generation
- gis_spatial_bridge column resolution, HVAC grouping, polygon-to-zone helpers
- Script import smoke tests

Closes #91.
"""

from __future__ import annotations

import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, SCRIPTS_DIR)


# ── blueprint_shapes tests ──────────────────────────────────────────────

class TestBlueprintShapes:
    def test_hull_outline_returns_closed_ring(self) -> None:
        from blueprint_shapes import hull_outline

        ring = hull_outline("naval_surface_combatant", 100.0, 20.0)
        assert ring[0] == ring[-1], "Hull ring must be closed"
        assert len(ring) >= 4

    def test_hull_outline_all_families(self) -> None:
        from blueprint_shapes import hull_outline, HULL_FAMILY

        for platform, family in HULL_FAMILY.items():
            ring = hull_outline(family, 150.0, 30.0)
            assert len(ring) >= 4, f"Family {family} (platform {platform})"
            assert ring[0] == ring[-1], f"Ring not closed for {family}"

    def test_blueprint_compartment(self) -> None:
        from blueprint_shapes import blueprint_compartment

        ring = blueprint_compartment(
            cx=50.0, cy=15.0, volume_m3=100.0, zone_type="Free",
        )
        assert len(ring) >= 4
        assert ring[0] == ring[-1]

    def test_blueprint_compartment_different_type(self) -> None:
        from blueprint_shapes import blueprint_compartment

        ring = blueprint_compartment(
            cx=50.0, cy=15.0, volume_m3=200.0, zone_type="Room",
        )
        assert len(ring) >= 4
        assert ring[0] == ring[-1]


# ── gis_spatial_bridge tests ────────────────────────────────────────────

class TestResolveColumn:
    def test_override_exact_match(self) -> None:
        from tools.gis_spatial_bridge import _resolve_column

        cols = ["Name", "ID", "Type"]
        assert _resolve_column(cols, ["NAME"], override="ID") == "ID"

    def test_override_case_insensitive(self) -> None:
        from tools.gis_spatial_bridge import _resolve_column

        cols = ["room_name", "room_type"]
        assert _resolve_column(cols, [], override="ROOM_NAME") == "room_name"

    def test_candidate_auto_resolve(self) -> None:
        from tools.gis_spatial_bridge import _resolve_column

        cols = ["VOLUME_M3", "TYPE", "NAME"]
        assert _resolve_column(cols, ["ROOM_NAME", "NAME"], None) == "NAME"

    def test_no_match(self) -> None:
        from tools.gis_spatial_bridge import _resolve_column

        cols = ["FOO", "BAR"]
        assert _resolve_column(cols, ["NAME", "ID"], None) is None


class TestGroupHvacZones:
    def test_groups_by_deck(self) -> None:
        from tools.gis_spatial_bridge import _group_hvac_zones

        zones = [
            {"id": "R1", "deck": "main", "base_ach": 6.0},
            {"id": "R2", "deck": "main"},
            {"id": "R3", "deck": "upper", "base_ach": 12.0},
        ]
        result = _group_hvac_zones(zones)
        assert len(result) == 2
        deck_ids = {h["id"] for h in result}
        assert "zone_main" in deck_ids
        assert "zone_upper" in deck_ids

    def test_max_ach_per_deck(self) -> None:
        from tools.gis_spatial_bridge import _group_hvac_zones

        zones = [
            {"id": "R1", "deck": "lower", "base_ach": 3.0},
            {"id": "R2", "deck": "lower", "base_ach": 10.0},
        ]
        result = _group_hvac_zones(zones)
        assert result[0]["ach"] == 10.0


# ── Script import smoke tests ───────────────────────────────────────────

class TestScriptImports:
    def test_import_blueprint_shapes(self) -> None:
        import blueprint_shapes

        assert hasattr(blueprint_shapes, "hull_outline")
        assert hasattr(blueprint_shapes, "blueprint_compartment")
        assert hasattr(blueprint_shapes, "HULL_FAMILY")

    def test_import_gis_spatial_bridge(self) -> None:
        from tools import gis_spatial_bridge

        assert hasattr(gis_spatial_bridge, "convert")
        assert hasattr(gis_spatial_bridge, "emit_deck_graphics")

    def test_import_deck_footprint_builder(self) -> None:
        import deck_footprint_builder  # noqa: F401

    def test_import_deck_photo_plate(self) -> None:
        import deck_photo_plate  # noqa: F401
