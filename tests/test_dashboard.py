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


class TestMechanismAggregators:
    def test_pathway_label_covers_new_routes(self) -> None:
        from dashboard.mechanisms import pathway_label

        assert pathway_label("flush_aerosol") == "Flush Aerosol"
        assert pathway_label("common_source_food") == "Common-Source Food"
        assert pathway_label("environmental_source") == "Environmental Source"
        assert pathway_label("droplet") == "Droplet"

    def test_aggregate_exposure_counts(self) -> None:
        from dashboard.mechanisms import aggregate_exposure_counts

        history = [
            {
                "contact_tracing": {
                    "droplet_exposures": [{"a": 1}, {"b": 2}],
                    "flush_aerosol_exposures": [{"c": 3}],
                    "common_source_exposures": [],
                },
            },
            {
                "contact_tracing": {
                    "droplet_exposures": [{"d": 4}],
                },
            },
        ]
        counts = aggregate_exposure_counts(history)
        assert counts["Droplet"] == 3
        assert counts["Flush Aerosol"] == 1
        assert "Common-Source Food" not in counts

    def test_collect_common_source_events(self) -> None:
        from dashboard.mechanisms import collect_common_source_events

        history = [
            {
                "epoch": 4,
                "contact_tracing": {
                    "common_source_events": [
                        {
                            "event_id": "cs-norwalk_gi-1",
                            "pathogen_id": "norwalk_gi",
                            "zone": "Galley",
                            "meal": "dinner",
                            "source_kind": "provisioned_lot",
                            "food_safety_posture": 0.9,
                            "start_epoch": 4,
                            "end_epoch": 6,
                            "cohort_size": 12,
                            "servings_taken": 7,
                            "per_serving_dose": 1.5,
                        },
                    ],
                },
            },
        ]
        rows = collect_common_source_events(history)
        assert len(rows) == 1
        assert rows[0]["epoch"] == 4
        assert rows[0]["servings"] == 7
        assert rows[0]["window"] == "4–6"

    def test_route_attribution_latest_non_empty(self) -> None:
        from dashboard.mechanisms import route_attribution

        history = [
            {"summary": {"infections_by_dominant_route": {"droplet": 2}}},
            {"summary": {
                "infections_by_dominant_route": {"droplet": 3, "fomite": 1},
                "infection_dose_share_by_route": {"droplet": 0.6},
            }},
        ]
        counts, share = route_attribution(history)
        assert counts == {"droplet": 3, "fomite": 1}
        assert share == {"droplet": 0.6}
        assert route_attribution([{"summary": {}}]) == ({}, {})

    def test_passenger_crew_rates(self) -> None:
        from dashboard.mechanisms import passenger_crew_rates

        summary = {
            "passenger_complement": 14,
            "crew_complement": 6,
            "cumulative_ever_infected_passenger": 4,
            "cumulative_ever_infected_crew": 1,
            "infection_attack_rate_passenger": 0.286,
            "reported_case_rate_crew": 0.167,
        }
        rows = passenger_crew_rates(summary)
        assert [r["Group"] for r in rows] == ["Passengers", "Crew"]
        assert rows[0]["Ever infected"] == 4
        assert rows[0]["Attack rate"] == "28.6%"
        assert rows[1]["Illness rate"] == "—"
        assert passenger_crew_rates({}) == []

    def test_sanitary_activity_totals(self) -> None:
        from dashboard.mechanisms import sanitary_activity_totals

        empty = {"summary": {"sanitary_activity": {"visits": 0}}}
        used = {"summary": {"sanitary_activity": {"visits": 5, "flush_events": 1}}}
        assert sanitary_activity_totals([empty, used])["visits"] == 5
        assert sanitary_activity_totals([empty]) == {}

    def test_age_band_stats(self) -> None:
        from dashboard.mechanisms import aggregate_age_band_stats

        agents = [
            {
                "agent_id": 1, "age_band": "senior",
                "infection_state": "infected",
                "symptom_presentation": "symptomatic",
                "compliance_status": "compliant",
            },
            {
                "agent_id": 2, "age_band": "adult",
                "infection_state": "susceptible",
                "symptom_presentation": "asymptomatic",
                "compliance_status": "compliant",
            },
            {"agent_id": 3, "infection_state": "susceptible"},
        ]
        stats = aggregate_age_band_stats(agents)
        assert stats["senior"]["infected"] == 1
        assert stats["adult"]["total"] == 1
        assert len(stats) == 2

    def test_information_series(self) -> None:
        from dashboard.mechanisms import information_series

        history = [
            {
                "epoch": 0,
                "information_state": {
                    "reputation": {
                        "trust_command": 0.7,
                        "trust_medical": 0.8,
                        "corporate_reputation_risk": 0.0,
                    },
                    "agents": {
                        "0": {"rumor_exposure": 0.2, "severity_belief": 0.4},
                        "1": {"rumor_exposure": 0.6, "severity_belief": 0.2},
                    },
                    "public_messages": [],
                },
            },
        ]
        df = information_series(history)
        assert len(df) == 1
        assert df.iloc[0]["trust_command"] == pytest.approx(0.7)
        assert df.iloc[0]["mean_rumor_exposure"] == pytest.approx(0.4)
        assert df.iloc[0]["max_rumor_exposure"] == pytest.approx(0.6)

    def test_collect_decision_rows_skips_noop(self) -> None:
        from dashboard.mechanisms import collect_decision_rows

        history = [
            {
                "epoch": 2,
                "decisions": {
                    "by_actor": {
                        "command": ["noop", "increase_cleaning"],
                        "medical": ["open_ward"],
                    },
                },
            },
        ]
        rows = collect_decision_rows(history)
        assert len(rows) == 2
        assert rows[0]["action"] == "increase_cleaning"
        assert rows[1]["actor"] == "medical"

    def test_collect_sop_events(self) -> None:
        from dashboard.mechanisms import collect_sop_events

        history = [
            {
                "epoch": 0,
                "reactive_protocols": {
                    "sop_events": [
                        {
                            "epoch": 0,
                            "protocol_id": "SOP-014",
                            "name": "Wearable Fleet Outbreak Response",
                            "event": "ACTIVATED",
                            "modifiers": {"ppe_transmission_reduction": 0.5},
                        },
                    ],
                },
            },
        ]
        rows = collect_sop_events(history)
        assert len(rows) == 1
        assert rows[0]["protocol"] == "SOP-014"
        assert rows[0]["modifiers"] == "ppe_transmission_reduction"


class TestShipSpecOverrides:
    def test_mechanism_overrides_merge(self) -> None:
        from dashboard.run_console import _build_ship_spec

        spec = _build_ship_spec(
            platform_id="destroyer_baseline",
            num_epochs=2,
            seed=1,
            cascade=False,
            voyage_effects=False,
            preset_path=None,
            config_overrides={
                "rhythm": {"enabled": False},
                "transmission": {
                    "sanitary_visit_mode": "dwell_weighted",
                    "common_source": {"mode": "off"},
                },
            },
            pathogen_overrides={
                "norwalk_gi": {"common_source_events": {"enabled": False}},
            },
            history_retention="compact",
        )
        overrides = spec["config_overrides"]
        assert overrides["rhythm"]["enabled"] is False
        assert overrides["transmission"]["sanitary_visit_mode"] == "dwell_weighted"
        assert overrides["transmission"]["common_source"]["mode"] == "off"
        assert spec["pathogen_overrides"]["norwalk_gi"][
            "common_source_events"]["enabled"] is False
        assert spec["run"]["history_retention"] == "compact"

    def test_preset_overrides_preserved(self) -> None:
        import json
        import tempfile

        from dashboard.run_console import _build_ship_spec

        preset = {
            "catalog": {"platform_id": "destroyer_baseline"},
            "run": {"num_epochs": 1},
            "config_overrides": {
                "transmission": {"contact_mode": "density"},
            },
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, dir=REPO_ROOT,
        ) as fh:
            json.dump(preset, fh)
            path = fh.name
        try:
            spec = _build_ship_spec(
                platform_id="destroyer_baseline",
                num_epochs=2,
                seed=1,
                cascade=True,
                voyage_effects=False,
                preset_path=path,
                config_overrides={
                    "transmission": {"sanitary_visit_mode": "dwell_weighted"},
                },
            )
        finally:
            os.unlink(path)
        tx = spec["config_overrides"]["transmission"]
        assert tx["contact_mode"] == "density"
        assert tx["sanitary_visit_mode"] == "dwell_weighted"
        assert spec["config_overrides"]["diagnostic_cascade"]["enabled"] is True
