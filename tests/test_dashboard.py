"""
test_dashboard.py – Dashboard module import and pure helpers (PR #46)
"""

from __future__ import annotations

import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


class TestDashboardImports:
    def test_dashboard_module_imports(self) -> None:
        import dashboard  # noqa: F401

    def test_lcars_constants_defined(self) -> None:
        import dashboard
        assert dashboard.LCARS_GOLD == "#FF9900"
        assert dashboard.HISTORY_PATH.endswith("simulation_history.json")

    def test_apply_lcars_layout_plot_bgcolor_override(self) -> None:
        import plotly.graph_objects as go

        from dashboard.theme import apply_lcars_layout

        fig = go.Figure(data=[go.Scatter(x=[1], y=[1])])
        apply_lcars_layout(fig, plot_bgcolor="rgba(0,0,0,0.85)", height=200)
        assert fig.layout.plot_bgcolor == "rgba(0,0,0,0.85)"
        assert fig.layout.height == 200


class TestAggregateTransmissionPathways:
    def test_pathway_breakdown_keys(self) -> None:
        from dashboard import aggregate_transmission_pathway_totals

        history = [
            {
                "contact_tracing": {
                    "transmission_events": [
                        {
                            "pathway_breakdown": {
                                "food:norwalk_gi": 2.5,
                                "hvac_airborne:sars_cov2_resp": 1.0,
                            },
                        },
                    ],
                },
            },
        ]
        totals = aggregate_transmission_pathway_totals(history)
        assert totals["food"] == pytest.approx(2.5)
        assert totals["hvac_airborne"] == pytest.approx(1.0)

    def test_dominant_pathway_fallback(self) -> None:
        from dashboard import aggregate_transmission_pathway_totals

        history = [
            {
                "contact_tracing": {
                    "transmission_events": [
                        {"dominant_pathway": "fomite", "total_dose": 3.0},
                    ],
                },
            },
        ]
        totals = aggregate_transmission_pathway_totals(history)
        assert totals["fomite"] == pytest.approx(3.0)

    def test_none_pathway_excluded(self) -> None:
        from dashboard import aggregate_transmission_pathway_totals

        history = [
            {
                "contact_tracing": {
                    "transmission_events": [
                        {"dominant_pathway": "none", "total_dose": 5.0},
                    ],
                },
            },
        ]
        totals = aggregate_transmission_pathway_totals(history)
        assert "none" not in totals
        assert totals == {}

    def test_load_history_returns_list_when_missing(
        self, tmp_path: str, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import dashboard
        missing = os.path.join(tmp_path, "no_history.json")
        monkeypatch.setattr(dashboard, "HISTORY_PATH", missing)
        dashboard.load_history.clear()
        assert dashboard.load_history() == []


class TestResolvePlatformId:
    def test_empty_history_defaults_to_mega_cruise(self) -> None:
        from dashboard.loaders import resolve_platform_id
        from dashboard.paths import DEFAULT_PLATFORM_ID

        assert DEFAULT_PLATFORM_ID == "mega_cruise_5000"
        pid, method = resolve_platform_id([])
        assert pid == "mega_cruise_5000"
        assert method == "default"

    def test_manual_override_wins(self) -> None:
        from dashboard.loaders import resolve_platform_id

        pid, method = resolve_platform_id([], override="spirit_cruise_3000")
        assert pid == "spirit_cruise_3000"
        assert method == "manual"

    def test_fingerprint_matches_destroyer_zones(self) -> None:
        import json

        from dashboard.loaders import resolve_platform_id
        from dashboard.paths import PLATFORMS_DIR, SPATIAL_LAYOUT_JSON

        layout_path = os.path.join(
            PLATFORMS_DIR, "destroyer_baseline", SPATIAL_LAYOUT_JSON,
        )
        with open(layout_path, encoding="utf-8") as fh:
            layout = json.load(fh)
        spaces = {z["id"]: {} for z in layout["zones"]}
        pid, method = resolve_platform_id([{"spaces": spaces}])
        assert pid == "destroyer_baseline"
        assert method == "exact"

    def test_unmatched_history_uses_config_before_default(self) -> None:
        from dashboard.loaders import resolve_platform_id

        pid, method = resolve_platform_id(
            [{"spaces": {"totally_fake_zone_xyz": {}}}],
        )
        # crusher_labs/config.yaml defaults to mega_cruise_5000
        assert pid == "mega_cruise_5000"
        assert method == "config"


class TestUnitsRegistry:
    def test_axis_persons(self) -> None:
        from dashboard.units import axis

        assert axis("persons").title == "Persons"

    def test_time_x_values_voyage_day(self) -> None:
        from dashboard.units import time_x_values, time_xaxis_title

        history = [
            {"epoch": 0, "voyage_epoch": {"voyage_day": 1}},
            {"epoch": 1, "voyage_epoch": {"voyage_day": 2}},
        ]
        assert time_x_values(history) == [1, 2]
        assert time_xaxis_title(history) == "Voyage day"


class TestAgentClassColors:
    def test_distinct_class_colors(self) -> None:
        from dashboard.spatial_viz import _colors_for_agents

        positions = [
            {"agent_class": "crew_medical", "infection_state": "infected"},
            {"agent_class": "passenger", "infection_state": "susceptible"},
            {"agent_class": "crew_medical", "infection_state": "susceptible"},
        ]
        colors = _colors_for_agents(positions, "agent_class")
        assert colors[0] == colors[2]
        assert colors[0] != colors[1]

    def test_infection_state_palette(self) -> None:
        from dashboard.spatial_viz import _AGENT_COLORS, _colors_for_agents

        positions = [{"infection_state": "infected", "agent_class": "x"}]
        assert _colors_for_agents(positions, "infection_state") == [_AGENT_COLORS["infected"]]


class TestEpidemicVlineAlignment:
    def test_status_vline_uses_voyage_day_x(self) -> None:
        from dashboard.charts import _build_epidemic_curve

        history = [
            {
                "epoch": 0,
                "trigger_status": "BASELINE",
                "voyage_epoch": {"voyage_day": 10},
                "summary": {
                    "susceptible": 10, "infected": 0, "symptomatic": 0,
                    "quarantined": 0, "isolated": 0, "recovered": 0,
                },
            },
            {
                "epoch": 1,
                "trigger_status": "CONFIRMED",
                "voyage_epoch": {"voyage_day": 11},
                "summary": {
                    "susceptible": 9, "infected": 1, "symptomatic": 0,
                    "quarantined": 0, "isolated": 0, "recovered": 0,
                },
            },
        ]
        fig = _build_epidemic_curve(history)
        shapes = fig.layout.shapes or ()
        vlines = [s for s in shapes if getattr(s, "type", None) == "line"]
        assert vlines
        assert float(vlines[0].x0) == 11.0


class TestRetentionDetection:
    def test_full_when_agents(self) -> None:
        from dashboard.loaders import detect_retention_mode

        history = [{"agents": [{"agent_id": 1}], "epoch": 0}]
        assert detect_retention_mode(history) == "full"

    def test_compact_without_agents(self) -> None:
        from dashboard.loaders import detect_retention_mode

        history = [{"summary": {}, "epoch": 0}]
        assert detect_retention_mode(history) == "compact"


class TestTransmissionTimeSeries:
    def test_per_epoch_pathways(self) -> None:
        from dashboard.transmission_viz import aggregate_pathway_time_series

        history = [
            {
                "epoch": 0,
                "contact_tracing": {
                    "transmission_events": [
                        {"pathway_breakdown": {"droplet:n1": 1.0}},
                    ],
                },
            },
            {
                "epoch": 1,
                "contact_tracing": {
                    "transmission_events": [
                        {"dominant_pathway": "fomite", "total_dose": 2.0},
                    ],
                },
            },
        ]
        epochs, series = aggregate_pathway_time_series(history)
        assert len(epochs) == 2
        assert series["droplet"][0] == pytest.approx(1.0)
        assert series["fomite"][1] == pytest.approx(2.0)
