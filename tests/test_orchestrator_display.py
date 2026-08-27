"""Bounds and branch coverage for orchestrator_display helpers."""

from __future__ import annotations

import pytest

from orchestrator_display import (
    _executive_counter_rows,
    _executive_epidemiology_rows,
    print_initialization,
    print_executive_summary,
    print_progress,
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
