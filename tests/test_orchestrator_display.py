"""Bounds and branch coverage for orchestrator_display helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from orchestrator_display import (
    _executive_counter_rows,
    _executive_epidemiology_rows,
    _print_pathogen_profile,
    print_contam_engine,
    print_executive_summary,
    print_initialization,
    print_korkin_engine,
    print_multi_pathogen,
    print_observation_engine,
    print_progress,
    print_protocol_engine,
    print_transmission_core,
    print_wearable_monitoring,
)


def _row(text: str = "") -> str:
    return text


class TestProgressAndIcons:
    """Progress bar fill grades with epoch; status icons are distinct."""

    def test_progress_fill_grades_with_epoch(self, capsys: pytest.CaptureFixture[str]) -> None:
        fills: list[int] = []
        for epoch in (0, 5, 11):
            print_progress(
                epoch=epoch,
                num_epochs=12,
                trigger_status="BASELINE",
                n_active_sops=0,
                total_spent=0.0,
                prev_status="BASELINE",
            )
            out = capsys.readouterr().out
            fills.append(out.count("█"))
        assert fills == sorted(fills)
        assert fills[-1] > fills[0]
        assert fills[0] >= 0

    def test_status_icons_are_distinct(self, capsys: pytest.CaptureFixture[str]) -> None:
        statuses = ("BASELINE", "ALERT", "SUSPECTED", "CONFIRMED", "LOCKDOWN")
        icons: list[str] = []
        for status in statuses:
            print_progress(0, 2, status, 0, 0.0, "BASELINE")
            out = capsys.readouterr().out
            # Icon sits just before the status token.
            idx = out.find(status)
            assert idx > 0
            icons.append(out[idx - 2 : idx].strip())
        assert len(set(icons)) == len(statuses)
        print_progress(0, 2, "UNKNOWN_STATUS", 0, 0.0, "BASELINE")
        assert "?" in capsys.readouterr().out

    def test_status_transition_announced(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_progress(1, 4, "ALERT", 1, 100.0, "BASELINE")
        out = capsys.readouterr().out
        assert "BASELINE → ALERT" in out


def test_initialization_displays_noise_probability_per_day(capsys: pytest.CaptureFixture[str]) -> None:
    print_initialization(
        ship={
            "num_agents": 2,
            "agent_roles": {1: "passenger", 2: "crew"},
            "zone_names": ["Bridge"],
            "high_traffic_zones": [],
        },
        seeds={},
        cfg={
            "fred_behavior": {
                "healthy_noise_categories": [
                    {"reason": "fatigue", "probability_per_day": 0.2},
                ],
            },
        },
    )
    output = capsys.readouterr().out
    assert "Noise: fatigue          P/day=0.200" in output


def test_initialization_optional_sections(capsys: pytest.CaptureFixture[str]) -> None:
    print_initialization(
        ship={
            "num_agents": 4,
            "agent_roles": {1: "passenger", 2: "passenger", 3: "crew", 4: "crew"},
            "agent_classes": [
                {"class_id": "passenger_adult", "fraction": 0.5},
                {"class_id": "crew_hotel", "fraction": 0.5},
            ],
            "gender_distribution": {"female": 0.55, "male": 0.45},
            "zone_names": ["Bridge", "Dining"],
            "high_traffic_zones": ["Dining"],
        },
        seeds={
            "Bridge": {
                "zone_type": "Work",
                "kingdom_fractions": {"bacteria": 0.7, "virus": 0.3},
            },
        },
        cfg={
            "ship_graph": {
                "infection_counters": [
                    {
                        "counter_id": "attack_rate",
                        "label": "Attack rate",
                        "metric": "attack_rate",
                        "threshold": 0.05,
                        "on_exceed": "escalate",
                    },
                    {
                        "counter_id": "case_count",
                        "metric": "cases",
                    },
                ],
            },
            "fred_behavior": {
                "quarantine_compliance": 0.9,
                "reluctant_fraction": 0.5,
                "reluctant_delay_hours": 24,
                "healthy_noise_categories": [
                    {"reason": "seasick", "probability": 0.1},
                ],
            },
            "emod_progression": {
                "incubation_days": 1,
                "shedding_phases": [
                    {"name": "peak", "max_rate": 10.0, "sensitivity_cap": 0.95},
                ],
            },
        },
    )
    out = capsys.readouterr().out
    assert "Agent classes:" in out
    assert "passenger_adult" in out
    assert "Gender distribution:" in out
    assert "Infection counters: 2 configured" in out
    assert "threshold=0.05" in out
    assert "Noise: seasick" in out
    assert "Phase peak" in out
    assert "2 passengers, 2 crew" in out


class TestEngineBanners:
    """print_* initialization banners via SimpleNamespace stubs."""

    def test_korkin_engine_banner(self, capsys: pytest.CaptureFixture[str]) -> None:
        engine = SimpleNamespace(
            num_passengers=10,
            num_crew=5,
            zones=[{"name": "Bridge"}, {"name": "Galley"}],
            get_summary=lambda: {
                "total": 15,
                "immune": 2,
                "infected": 1,
                "agent_classes": {"passenger": 10, "crew": 5},
                "gender_distribution": {"female": 8, "male": 7},
            },
        )
        print_korkin_engine(engine)  # type: ignore[arg-type]
        out = capsys.readouterr().out
        assert "KORKIN LAB ENGINE" in out
        assert "Population: 15 agents" in out
        assert "Agent classes:" in out
        assert "Gender:" in out
        assert "Bridge, Galley" in out

    def test_wearable_monitoring_enabled_and_disabled(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        print_wearable_monitoring(None)
        assert "disabled" in capsys.readouterr().out

        monitor = SimpleNamespace(
            get_fleet_summary=lambda: {
                "total_monitored": 12,
                "total_device_instances": 14,
                "devices": {
                    "band_v1": {"channels": ["hr", "temp"]},
                },
                "device_deployment_counts": {"band_v1": 12},
                "visibility_breakdown": {"full": 10, "partial": 2, "none": 0},
            }
        )
        print_wearable_monitoring(monitor)
        out = capsys.readouterr().out
        assert "WEARABLE MONITORING" in out
        assert "Monitored agents: 12" in out
        assert "band_v1" in out
        assert "Visibility: full=10, partial=2" in out

    def test_contam_engine_present_and_absent(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        engine = SimpleNamespace(zone_pathogen_mass={})
        print_contam_engine(None, engine, {})  # type: ignore[arg-type]
        assert "not available" in capsys.readouterr().out

        contam = SimpleNamespace(
            filter_efficiency=0.85,
            natural_decay_rate=0.1,
            zone_nodes={"A": 1, "B": 2},
            get_transport_summary=lambda _mass: {
                "total_hvac_paths": 3,
                "total_passive_paths": 1,
            },
        )
        print_contam_engine(contam, engine, {"hvac": {"filter_type": "HEPA"}})  # type: ignore[arg-type]
        out = capsys.readouterr().out
        assert "CONTAM TRANSPORT ENGINE" in out
        assert "Filter type:        HEPA" in out
        assert "HVAC-ducted paths:  3" in out

    def test_pathogen_profile_and_multi_pathogen(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        prof = {
            "name": "Norovirus GII",
            "category": "enteric",
            "transmission_routes": ["fomite", "airborne"],
            "introduction_epoch": 2,
            "food_contamination": {
                "enabled": True,
                "growth_rate_per_day": 0.1,
                "decay_rate_per_day": 0.05,
            },
            "environmental_contamination": {
                "enabled": True,
                "source_type": "sewage",
                "baseline_environmental_load": 1.5,
                "person_to_person": False,
            },
            "microflora_disruption": {
                "causes_disruption": True,
                "disruption_type": "dysbiosis",
                "disruption_magnitude": 0.4,
            },
            "chronic_shedder_fraction": 0.1,
            "chronic_shedding_duration_days": {"median": 28, "min": 14, "max": 56},
        }
        _print_pathogen_profile("norovirus", prof)
        profile_out = capsys.readouterr().out
        assert "Norovirus GII" in profile_out
        assert "Food contam:" in profile_out
        assert "Env contam:" in profile_out
        assert "Microflora disruption:" in profile_out

        engine = SimpleNamespace(agents={1: {}, 2: {}, 3: {}})
        print_multi_pathogen({"norovirus": prof}, {1}, engine, True)  # type: ignore[arg-type]
        out = capsys.readouterr().out
        assert "MULTI-PATHOGEN ENGINE" in out
        assert "Immunocompromised agents: 1/3" in out
        assert "Chronic shedders (norovirus)" in out
        assert "Dual-signal shedding: enabled" in out

        # Skip chronic-shedder lines when fraction/spec absent.
        thin_prof = {
            "name": "Influenza A",
            "transmission_routes": ["airborne"],
            "chronic_shedder_fraction": None,
        }
        print_multi_pathogen({"influenza": thin_prof}, set(), engine, False)  # type: ignore[arg-type]
        thin_out = capsys.readouterr().out
        assert "Chronic shedders" not in thin_out
        assert "Dual-signal shedding: disabled" in thin_out

        print_multi_pathogen({}, set(), engine, False)  # type: ignore[arg-type]
        assert capsys.readouterr().out == ""

    def test_transmission_observation_protocol_banners(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        print_transmission_core(
            {"A": ["B", "C"], "B": ["C"]},
            {"norovirus": {}, "influenza": {}},
        )
        tx = capsys.readouterr().out
        assert "TRANSMISSION CORE" in tx
        assert "HVAC downstream links: 3" in tx
        assert "norovirus, influenza" in tx

        print_observation_engine("HIGH", 0.001, "strict", True)
        obs = capsys.readouterr().out
        assert "OBSERVATION ENGINE" in obs
        assert "Logging fidelity:   HIGH" in obs
        assert "Lab notebook: enabled" in obs

        print_observation_engine("LOW", 0.0, "none", False)
        assert "Lab notebook: disabled" in capsys.readouterr().out

        proto = SimpleNamespace(
            protocol_id="SOP-001",
            name="Isolate",
            trigger={"instrument_class": "clinical_rdt", "stoplight_level": "yellow"},
            modifiers={"exempt_classes": ["crew_medical"]},
        )
        ledger = SimpleNamespace(
            financial_balance=5000.0,
            labor_remaining=40.0,
            inventory={"swabs": 10, "gloves": 20},
        )
        print_protocol_engine([proto], ledger)  # type: ignore[arg-type]
        proto_out = capsys.readouterr().out
        assert "REACTIVE PROTOCOL ENGINE" in proto_out
        assert "SOP-001" in proto_out
        assert "Exempt:  crew_medical" in proto_out
        assert "Starting allocation: $5,000.00" in proto_out


class TestExecutiveCounterRows:
    """Rate counters percent-format; count counters integer; exceeded flag."""

    def test_rate_vs_count_formatting(self) -> None:
        counters = {
            "infection_rate": {
                "label": "Infection rate",
                "value": 0.25,
                "population": 20,
                "threshold": 0.1,
                "exceeded": True,
            },
            "case_count": {
                "label": "Case count",
                "value": 5.0,
                "population": 20,
                "threshold": 10,
                "exceeded": False,
            },
        }
        lines = _executive_counter_rows(_row, "---", counters)
        joined = "\n".join(lines)
        assert "25.0%" in joined
        assert "EXCEEDED" in joined
        assert "5" in joined
        assert "ok" in joined
        assert "INFECTION COUNTERS" in joined

    def test_no_threshold_omits_thr_marker(self) -> None:
        counters = {
            "case_count": {"label": "Cases", "value": 3.0, "population": 10},
        }
        lines = _executive_counter_rows(_row, "---", counters)
        joined = "\n".join(lines)
        assert "thr=" not in joined
        assert "(n=10)" in joined


class TestEpidemiologyRows:
    """Epidemiology block lists required fields; totals stay non-negative."""

    def test_epidemiology_row_invariants(self) -> None:
        summary = {
            "infected": 3,
            "recovered": 2,
            "isolated": 1,
            "quarantined": 4,
            "immune": 0,
            "symptomatic": 2,
        }
        lines = _executive_epidemiology_rows(
            _row,
            "---",
            num_agents=20,
            engine_summary=summary,
            trigger_status="SUSPECTED",
        )
        joined = "\n".join(lines)
        assert "EPIDEMIOLOGICAL METRICS" in joined
        assert "Total crew:          20" in joined
        assert "Currently infected: 3" in joined
        assert "Recovered:          2" in joined
        assert "Final status:        SUSPECTED" in joined
        total_ever = summary["infected"] + summary["recovered"] + summary["isolated"]
        assert f"Total infected:      {total_ever}" in joined
        assert total_ever >= 0
        assert all(v >= 0 for v in summary.values())


class TestPrintExecutiveSummary:
    """Branch coverage for optional sections via SimpleNamespace stubs."""

    def _audit(self) -> dict:
        return {
            "summary": {
                "total_labor_consumed_hours": 1.5,
                "starting_labor_capacity_hours": 10.0,
                "starting_financial_budget_usd": 1000.0,
                "total_expenditure_usd": 100.0,
                "surveillance_cost_usd": 40.0,
                "intervention_cost_usd": 60.0,
                "remaining_balance_usd": 900.0,
                "surveillance_labor_hours": 0.5,
                "intervention_labor_hours": 1.0,
            },
            "material_inventory": {
                "swabs": {"remaining": 0, "consumed": 5, "starting": 5, "total_cost_usd": 12.0},
                "gloves": {"remaining": 2, "consumed": 1, "starting": 3, "total_cost_usd": 1.0},
            },
        }

    def _proto(self, *, with_activations: bool) -> dict:
        events = []
        if with_activations:
            events = [
                {"event": "ACTIVATED", "protocol_id": "SOP-001", "name": "Isolate", "epoch": 2},
                {"event": "ACTIVATED", "protocol_id": "SOP-001", "name": "Isolate", "epoch": 3},
            ]
        return {
            "event_log": events,
            "protocols_still_active": ["SOP-001"] if with_activations else [],
            "total_activations": len(events),
            "total_deactivations": 0,
        }

    def test_minimal_summary_no_optional_sections(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        print_executive_summary(
            num_agents=20,
            num_epochs=4,
            engine_summary={
                "infected": 0,
                "recovered": 0,
                "isolated": 0,
                "immune": 0,
                "symptomatic": 0,
            },
            audit=self._audit(),
            proto_summary=self._proto(with_activations=False),
            escalation_log=[],
            compliance_log=[],
            trigger_status="BASELINE",
            isolated_count=0,
            pathogen_profiles=None,
            infection_counters=None,
        )
        out = capsys.readouterr().out
        assert "EXECUTIVE SUMMARY" in out
        assert "(no protocols activated)" in out
        assert "4 epochs completed" in out

    def test_full_optional_branches(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_executive_summary(
            num_agents=20,
            num_epochs=6,
            engine_summary={
                "infected": 2,
                "recovered": 1,
                "isolated": 1,
                "quarantined": 2,
                "immune": 0,
                "symptomatic": 1,
            },
            audit=self._audit(),
            proto_summary=self._proto(with_activations=True),
            escalation_log=[{"epoch": 2, "from": "BASELINE", "to": "ALERT"}],
            compliance_log=[
                {"action": "immediate_compliance"},
                {"action": "refused_quarantine"},
            ],
            trigger_status="ALERT",
            isolated_count=1,
            quarantined_count=2,
            refuser_count=1,
            pathogen_profiles={"norovirus": {}, "influenza": {}},
            infection_counters={
                "attack_rate": {
                    "label": "Attack rate",
                    "value": 0.15,
                    "population": 20,
                    "threshold": 0.1,
                    "exceeded": True,
                },
            },
        )
        out = capsys.readouterr().out
        assert "Pathogen count:      2" in out
        assert "Escalation timeline:" in out
        assert "1 immediate, 1 refused" in out
        assert "DEPLETED SUPPLIES" in out
        assert "SOP-001" in out
        assert "Still active at end" in out
        assert "EXCEEDED" in out


def test_executive_summary_truncates_overlong_row(
    capsys: pytest.CaptureFixture[str],
) -> None:
    long_id = "pathogen_" + ("Z" * 120)
    print_executive_summary(
        num_agents=5,
        num_epochs=2,
        engine_summary={
            "infected": 0,
            "recovered": 0,
            "isolated": 0,
            "immune": 0,
            "symptomatic": 0,
        },
        audit={
            "summary": {
                "total_labor_consumed_hours": 0.0,
                "starting_labor_capacity_hours": 1.0,
                "starting_financial_budget_usd": 1.0,
                "total_expenditure_usd": 0.0,
                "surveillance_cost_usd": 0.0,
                "intervention_cost_usd": 0.0,
                "remaining_balance_usd": 1.0,
                "surveillance_labor_hours": 0.0,
                "intervention_labor_hours": 0.0,
            },
            "material_inventory": {},
        },
        proto_summary={
            "event_log": [],
            "protocols_still_active": [],
            "total_activations": 0,
            "total_deactivations": 0,
        },
        escalation_log=[],
        compliance_log=[],
        trigger_status="BASELINE",
        isolated_count=0,
        pathogen_profiles={"norovirus": {}, long_id: {}},
    )
    out = capsys.readouterr().out
    # Row width is fixed at 80; overlong pathogen ids are truncated in-place.
    assert long_id not in out
    assert "Pathogen count:      2" in out
