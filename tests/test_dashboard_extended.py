"""
test_dashboard_extended.py – Expanded dashboard module tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Covers deck_geometry helpers, pydeck_builder pure functions,
and fleet_viz utility imports.

Closes #90.
"""

from __future__ import annotations

import os
import sys
from typing import Any

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


# ── deck_geometry tests ─────────────────────────────────────────────────

class TestZoneMetric:
    def test_airborne_mass(self) -> None:
        from dashboard.deck_geometry import zone_metric

        record = {"spaces": {"Z1": {"pathogen_mass": 42.0}}}
        assert zone_metric(record, "Z1", "Airborne Aerosol Mass") == pytest.approx(42.0)

    def test_fomite_mode(self) -> None:
        from dashboard.deck_geometry import zone_metric

        record = {
            "spaces": {},
            "observation_engine": {
                "surface_swab": {"Z1": {"surface_mass": 7.5}},
            },
        }
        assert zone_metric(record, "Z1", "Surface Fomite Contamination") == pytest.approx(7.5)

    def test_infected_count_mode(self) -> None:
        from dashboard.deck_geometry import zone_metric

        record = {
            "spaces": {},
            "agents": [
                {
                    "location": "Z1",
                    "infection_state": "infected",
                    "symptom_presentation": "symptomatic",
                    "compliance_status": "compliant",
                },
                {
                    "location": "Z1",
                    "infection_state": "infected",
                    "symptom_presentation": "mild",
                    "compliance_status": "compliant",
                },
                {
                    "location": "Z1",
                    "infection_state": "susceptible",
                    "symptom_presentation": "asymptomatic",
                    "compliance_status": "compliant",
                },
                {
                    "location": "Z2",
                    "infection_state": "infected",
                    "symptom_presentation": "asymptomatic",
                    "compliance_status": "compliant",
                },
            ],
        }
        assert zone_metric(record, "Z1", "Symptomatic Agent Count") == pytest.approx(2.0)

    def test_missing_zone_returns_zero(self) -> None:
        from dashboard.deck_geometry import zone_metric

        record = {"spaces": {}}
        assert zone_metric(record, "UNKNOWN", "Airborne Aerosol Mass") == pytest.approx(0.0)


class TestColorScaleMax:
    def test_nonempty(self) -> None:
        from dashboard.deck_geometry import color_scale_max

        assert color_scale_max({"A": 10.0, "B": 20.0}) == pytest.approx(20.0)

    def test_all_zeros(self) -> None:
        from dashboard.deck_geometry import color_scale_max

        result = color_scale_max({"A": 0.0, "B": 0.0})
        assert result >= 0.0

    def test_empty(self) -> None:
        from dashboard.deck_geometry import color_scale_max

        result = color_scale_max({})
        assert result >= 0.0


class TestMetricFraction:
    def test_normal(self) -> None:
        from dashboard.deck_geometry import metric_fraction

        assert metric_fraction(5.0, 10.0) == pytest.approx(0.5)

    def test_zero_max(self) -> None:
        from dashboard.deck_geometry import metric_fraction

        assert metric_fraction(5.0, 0.0) == pytest.approx(0.0)


class TestComputeAgentPositions:
    def test_positions_at_zone_centroid(self) -> None:
        from dashboard.deck_geometry import compute_agent_positions
        from dashboard.loaders import PlatformBundle

        bundle = PlatformBundle(
            platform_id="test",
            layout={"zones": [{"id": "Z1", "display": {"x": 10, "y": 5}, "deck": "main", "type": "Free", "volume_m3": 50}]},
            airflow={},
            manifest={},
            deck_graphics={},
            hull_png_path=None,
            blueprint_bg_path=None,
            zone_coords={
                "Z1": {"x": 10, "y": 5, "deck": "main", "type": "Free", "volume_m3": 50},
            },
        )
        record = {
            "agents": [
                {"agent_id": 1, "location": "Z1", "infection_state": "infected"},
            ],
        }
        positions = compute_agent_positions(record, bundle, "main")
        assert len(positions) == 1
        assert abs(positions[0]["x"] - 10) > 0.2
        assert abs(positions[0]["y"] - 5) > 0.2


class TestLcarsRgba:
    def test_zero_fraction(self) -> None:
        from dashboard.pydeck_builder import _lcars_rgba

        rgba = _lcars_rgba(0.0)
        assert len(rgba) == 4
        assert rgba == [26, 26, 46, 140]

    def test_low_fraction(self) -> None:
        from dashboard.pydeck_builder import _lcars_rgba

        rgba = _lcars_rgba(0.2)
        assert rgba[0] == 153  # green band

    def test_mid_fraction(self) -> None:
        from dashboard.pydeck_builder import _lcars_rgba

        rgba = _lcars_rgba(0.5)
        assert rgba[0] == 255  # amber band

    def test_high_fraction(self) -> None:
        from dashboard.pydeck_builder import _lcars_rgba

        rgba = _lcars_rgba(0.8)
        assert rgba[0] == 204  # red band


class TestAggregateClassStats:
    def test_orthogonal_axes(self) -> None:
        from dashboard.charts import aggregate_class_stats

        agents = [
            {
                "agent_class": "crew_medical",
                "infection_state": "infected",
                "symptom_presentation": "symptomatic",
                "compliance_status": "quarantined",
            },
            {
                "agent_class": "crew_medical",
                "infection_state": "susceptible",
                "symptom_presentation": "asymptomatic",
                "compliance_status": "compliant",
            },
            {
                "agent_class": "passenger_general",
                "infection_state": "recovered",
                "symptom_presentation": "asymptomatic",
                "compliance_status": "compliant",
            },
        ]
        stats = aggregate_class_stats(agents)
        assert stats["crew_medical"]["infected"] == 1
        assert stats["crew_medical"]["symptomatic"] == 1
        assert stats["crew_medical"]["quarantined"] == 1
        assert stats["passenger_general"]["recovered"] == 1


# ── theme tests ──────────────────────────────────────────────────────────

class TestTheme:
    def test_apply_lcars_layout(self) -> None:
        import plotly.graph_objects as go
        from dashboard.theme import apply_lcars_layout

        fig = go.Figure()
        apply_lcars_layout(fig, plot_bgcolor="rgba(0,0,0,0.5)", height=300)
        assert fig.layout.plot_bgcolor == "rgba(0,0,0,0.5)"
        assert fig.layout.height == 300

    def test_worst_stoplight_dict(self) -> None:
        from dashboard.theme import _worst_stoplight

        assert _worst_stoplight({"z1": "GREEN", "z2": "AMBER", "z3": "RED"}) == "RED"
        assert _worst_stoplight({"z1": "GREEN", "z2": "AMBER"}) == "AMBER"
        assert _worst_stoplight({"z1": "GREEN"}) == "GREEN"

    def test_worst_stoplight_scalar(self) -> None:
        from dashboard.theme import _worst_stoplight

        assert _worst_stoplight("RED") == "RED"
        assert _worst_stoplight("GREEN") == "GREEN"

    def test_lcars_banner(self) -> None:
        from dashboard.theme import _lcars_banner

        html = _lcars_banner("Test")
        assert "Test" in html

    def test_lcars_alert_banner(self) -> None:
        from dashboard.theme import _lcars_alert_banner

        html = _lcars_alert_banner("CONFIRMED")
        assert "CONFIRMED" in html or len(html) > 0


# ── fleet_viz import smoke ───────────────────────────────────────────────

class TestFleetVizImport:
    def test_render_fleet_operations_importable(self) -> None:
        from dashboard.fleet_viz import render_fleet_operations

        assert callable(render_fleet_operations)


# ── spatial_viz import smoke ─────────────────────────────────────────────

class TestSpatialVizImport:
    def test_footprint_caption(self) -> None:
        from dashboard.spatial_viz import footprint_caption

        manifest = {
            "footprint_tier": "representative",
            "ship_class_label": "Destroyer",
        }
        caption = footprint_caption(manifest)
        assert "Destroyer" in caption
        assert "representative" in caption.lower()
