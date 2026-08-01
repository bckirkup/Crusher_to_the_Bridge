"""Architectural ship graphics: packing, loaders, and spatial viz helpers."""
from __future__ import annotations

import json
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))


class TestCompartmentPacker:
    def test_port_stbd_hints_separate_laterally(self) -> None:
        from compartment_packer import pack_deck_compartments

        zones = [
            {
                "id": "PC_D10_P_F",
                "type": "Cabin_Corridor",
                "volume_m3": 400,
                "display": {"x": 295, "y": 32},
            },
            {
                "id": "PC_D10_S_F",
                "type": "Cabin_Corridor",
                "volume_m3": 400,
                "display": {"x": 295, "y": 35},
            },
            {
                "id": "PC_D10_C_F",
                "type": "Cabin_Corridor",
                "volume_m3": 400,
                "display": {"x": 295, "y": 33.5},
            },
        ]
        rings = pack_deck_compartments(zones, length_m=362, beam_m=64)
        assert set(rings) == {z["id"] for z in zones}
        centers = {
            zid: (
                sum(p[0] for p in ring[:-1]) / (len(ring) - 1),
                sum(p[1] for p in ring[:-1]) / (len(ring) - 1),
            )
            for zid, ring in rings.items()
        }
        assert centers["PC_D10_P_F"][1] < centers["PC_D10_C_F"][1]
        assert centers["PC_D10_C_F"][1] < centers["PC_D10_S_F"][1]

    def test_same_deck_pack_has_zero_overlaps_mega_cabin_deck(self) -> None:
        from compartment_packer import count_aabb_overlaps, pack_deck_compartments

        layout_path = os.path.join(
            REPO, "data", "platforms", "mega_cruise_5000", "spatial_layout.json",
        )
        with open(layout_path, encoding="utf-8") as fh:
            layout = json.load(fh)
        dims = layout["deck_dimensions"]
        zones = [z for z in layout["zones"] if z.get("deck") == "10_Cabins"]
        assert len(zones) >= 6
        rings = pack_deck_compartments(
            zones, float(dims["length_m"]), float(dims["beam_m"]),
        )
        assert count_aabb_overlaps(rings) == 0

    def test_packing_sensitive_to_beam(self) -> None:
        from compartment_packer import pack_deck_compartments

        zones = [
            {"id": "A_Port_Mid", "type": "Free", "volume_m3": 200, "display": {"x": 50, "y": 10}},
            {"id": "B_Stbd_Mid", "type": "Free", "volume_m3": 200, "display": {"x": 50, "y": 12}},
        ]
        narrow = pack_deck_compartments(zones, 100, 20)
        wide = pack_deck_compartments(zones, 100, 80)
        cy_n = [
            sum(p[1] for p in narrow[z][:-1]) / (len(narrow[z]) - 1)
            for z in ("A_Port_Mid", "B_Stbd_Mid")
        ]
        cy_w = [
            sum(p[1] for p in wide[z][:-1]) / (len(wide[z]) - 1)
            for z in ("A_Port_Mid", "B_Stbd_Mid")
        ]
        assert abs(cy_w[1] - cy_w[0]) > abs(cy_n[1] - cy_n[0])


class TestArchitecturalGraphicsLoader:
    @pytest.mark.parametrize(
        "platform_id",
        [
            "mega_cruise_5000",
            "enterprise_galaxy_tng",
            "enterprise_constitution_tos",
            "expedition_cruise_450",
        ],
    )
    def test_committed_plates_exist(self, platform_id: str) -> None:
        from dashboard.architectural_graphics import load_architectural_graphics

        pdir = os.path.join(REPO, "data", "platforms", platform_id)
        arch = load_architectural_graphics(pdir)
        assert arch.has_elevation
        assert arch.has_plan
        assert arch.elevation_path.endswith("elevation.jpg")
        assert arch.plan_overview_path.endswith("plan_overview.jpg")
        assert os.path.getsize(arch.elevation_path) > 1000
        assert os.path.getsize(arch.plan_overview_path) > 1000

    def test_bundle_prefers_plan_underlay(self) -> None:
        from dashboard.loaders import load_platform_bundle

        bundle = load_platform_bundle("mega_cruise_5000")
        assert bundle.architectural is not None
        assert bundle.architectural.has_plan
        assert bundle.blueprint_bg_path == bundle.architectural.plan_overview_path


class TestSpatialVizArchitectural:
    def test_footprint_caption_mentions_architectural(self) -> None:
        from dashboard.spatial_viz import footprint_caption

        caption = footprint_caption({
            "footprint_tier": "fiction_adapted",
            "ship_class_label": "Galaxy-class (fiction-adapted)",
            "architectural_graphics": {
                "elevation": {"credit": "elev credit"},
                "plan": {"credit": "plan credit"},
            },
        })
        assert "Galaxy-class" in caption
        assert "elev credit" in caption
        assert "not show artwork" in caption.lower() or "demonstration" in caption.lower()

    def test_build_plan_and_elevation_figures(self) -> None:
        from dashboard.loaders import load_platform_bundle
        from dashboard.spatial_viz import (
            _build_plotly_elevation,
            _build_plotly_plan_map,
        )
        from dashboard.architectural_graphics import ordered_decks

        bundle = load_platform_bundle("enterprise_constitution_tos")
        decks = ordered_decks(bundle.layout)
        record = {
            "epoch": 0,
            "spaces": {zid: {"pathogen_mass": 0.1} for zid in bundle.zone_coords},
            "observation_engine": {"surface_swab": {}},
            "agents": [],
            "trigger_status": "GREEN",
        }
        plan = _build_plotly_plan_map(
            record, bundle, "Airborne Aerosol Mass", decks[0],
        )
        elev = _build_plotly_elevation(
            record, bundle, "Airborne Aerosol Mass", decks, highlight_deck=decks[0],
        )
        assert len(plan.data) >= 1
        assert len(elev.data) == len(decks)

    def test_geojson_same_deck_no_overlaps_after_builder(self) -> None:
        from compartment_packer import count_aabb_overlaps
        from deck_footprint_builder import build_representative_geojson

        layout_path = os.path.join(
            REPO, "data", "platforms", "mega_cruise_5000", "spatial_layout.json",
        )
        airflow_path = os.path.join(
            REPO, "data", "platforms", "mega_cruise_5000", "air_flow_paths.json",
        )
        with open(layout_path, encoding="utf-8") as fh:
            layout = json.load(fh)
        with open(airflow_path, encoding="utf-8") as fh:
            airflow = json.load(fh)
        geo = build_representative_geojson("mega_cruise_5000", layout, airflow)
        by_deck: dict[str, dict[str, list]] = {}
        for feat in geo["features"]:
            props = feat.get("properties", {})
            if props.get("kind") != "compartment":
                continue
            deck = props["deck"]
            by_deck.setdefault(deck, {})[props["zone_id"]] = feat["geometry"]["coordinates"][0]
        worst = max(count_aabb_overlaps(rings) for rings in by_deck.values())
        assert worst == 0
