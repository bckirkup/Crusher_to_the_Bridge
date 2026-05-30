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
        assert totals["food"] == 2.5
        assert totals["hvac_airborne"] == 1.0

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
        assert totals["fomite"] == 3.0

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
