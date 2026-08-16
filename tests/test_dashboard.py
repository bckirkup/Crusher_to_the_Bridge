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
        # crusher_labs/config.yaml still points at destroyer_baseline
        assert pid == "destroyer_baseline"
        assert method == "config"
