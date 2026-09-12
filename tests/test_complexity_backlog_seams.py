"""Graded sensitivity / bounds tests at complexity-backlog extraction seams.

These lock helper boundaries introduced for Sonar S3776 / C901 reduction.
They are not golden-value locks of end-to-end campaign or cascade behavior —
existing suite files cover those.
"""

from __future__ import annotations

import math
from pathlib import Path
from types import SimpleNamespace

import pytest

from crusher_labs.diagnostic_cascade import DiagnosticCascadeEngine
from picard_framework.analysis import figures as figures_mod
from tests.test_diagnostic_cascade import (
    _StubTestRunner,
    _default_tiers,
    _make_agent,
)
from tools.sanity_checker import (
    Report,
    _check_ois_weights,
    _check_pathogen_shedding_curve,
    _check_pathogen_timing_bounds,
)


# --- figures helpers ---------------------------------------------------------


def test_heatmap_matrix_empty_and_populated() -> None:
    empty = figures_mod._heatmap_matrix({}, ["p1"], ["s1"])
    assert len(empty) == 1 and len(empty[0]) == 1
    assert math.isnan(empty[0][0])
    heat = {("p1", "s1"): [0.2, 0.4], ("p1", "s2"): [0.5]}
    mat = figures_mod._heatmap_matrix(heat, ["p1"], ["s1", "s2"])
    assert mat[0][0] == pytest.approx(0.3)
    assert mat[0][1] == pytest.approx(0.5)


def test_write_standard_figures_skips_without_matplotlib(
    monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    monkeypatch.setattr(figures_mod, "_have_matplotlib", lambda: False)
    assert figures_mod.write_standard_figures(str(tmp_path), [], []) == []


def test_write_standard_figures_emits_dose_and_epidemic_when_mpl_ok() -> None:
    pytest.importorskip("matplotlib")
    # analysis/_io confines outputs under the repo root.
    out_dir = Path("telemetry_buffer") / "_complexity_backlog_fig_test"
    if out_dir.exists():
        for child in out_dir.rglob("*"):
            if child.is_file():
                child.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)

    run_rows = [
        {
            "dose_adjustment": 1.0,
            "attack_rate": 0.1,
            "platform_id": "p1",
            "pathogen_id": "noro",
            "surveillance_strategy": "baseline",
            "seed": 1,
        }
    ]
    epoch_rows = [
        {"epoch": 0, "pathogen": "noro", "infected": 0.0, "platform_id": "p1"},
        {"epoch": 1, "pathogen": "noro", "infected": 2.0, "platform_id": "p1"},
        {"epoch": 2, "pathogen": "noro", "infected": 5.0, "platform_id": "p1"},
    ]
    try:
        out = figures_mod.write_standard_figures(str(out_dir), run_rows, epoch_rows)
        assert "figures/dose_response.png" in out
        assert "figures/epidemic_curves.png" in out
        assert (out_dir / "figures" / "dose_response.png").is_file()
    finally:
        for child in sorted(out_dir.rglob("*"), reverse=True):
            if child.is_file():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
        if out_dir.exists():
            out_dir.rmdir()


# --- diagnostic cascade evaluate_epoch helpers --------------------------------


def test_evaluate_epoch_entry_sensitivity_sick_vs_wearable() -> None:
    engine = DiagnosticCascadeEngine(_default_tiers())
    agents = [_make_agent(1), _make_agent(2)]
    runner = _StubTestRunner(positive_agents={1})

    sick_only = engine.evaluate_epoch(
        epoch=0,
        sick_call_ids=[1],
        wearable_red_ids=[],
        agents=agents,
        test_runner=runner,
    )
    assert 1 in sick_only.new_tier1_agents
    assert 1 not in sick_only.new_tier0_agents
    assert 2 not in sick_only.new_tier1_agents

    wear_only = engine.evaluate_epoch(
        epoch=1,
        sick_call_ids=[],
        wearable_red_ids=[2],
        agents=agents,
        test_runner=runner,
    )
    assert 2 in wear_only.new_tier0_agents


def test_evaluate_epoch_bounds_no_double_entry() -> None:
    engine = DiagnosticCascadeEngine(_default_tiers())
    agents = [_make_agent(1)]
    runner = _StubTestRunner(positive_agents={1})
    first = engine.evaluate_epoch(
        epoch=0,
        sick_call_ids=[1],
        wearable_red_ids=[1],
        agents=agents,
        test_runner=runner,
    )
    second = engine.evaluate_epoch(
        epoch=1,
        sick_call_ids=[1],
        wearable_red_ids=[1],
        agents=agents,
        test_runner=runner,
    )
    # Sick-call default entry is tier 1; wearable does not re-enter once active.
    assert first.new_tier1_agents.count(1) == 1
    assert 1 not in second.new_tier0_agents
    assert 1 not in second.new_tier1_agents


# --- sanity_checker logical contradiction helpers -----------------------------


def _pathogen(**kwargs):
    base = dict(
        pathogen_id="noro",
        recovery_day=3.0,
        shedding_duration_days=3.0,
        shedding_curve_log10=[1.0, 2.0, 1.0],
        introduction_epoch=0,
        initial_time_infected=0,
        transmission_routes=["airborne", "direct_contact"],
        route_efficiency_multipliers={"airborne": 1.0, "direct_contact": 1.0},
        transmission_route_weights={},
        food_contamination={"enabled": False},
        environmental_contamination={"enabled": False},
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_timing_bounds_sensitive_to_shedding_shorter_than_recovery() -> None:
    report = Report()
    _check_pathogen_timing_bounds(
        _pathogen(recovery_day=5.0, shedding_duration_days=2.0),
        report,
    )
    assert any(f.rule == "MATH_BOUND" for f in report.errors)

    ok = Report()
    _check_pathogen_timing_bounds(_pathogen(), ok)
    assert not any(f.rule == "MATH_BOUND" for f in ok.errors)


def test_shedding_curve_length_and_sign_bounds() -> None:
    short = Report()
    _check_pathogen_shedding_curve(
        _pathogen(shedding_curve_log10=[1.0]),
        short,
    )
    assert any(f.rule == "LOGIC_SHED" for f in short.warnings)

    negative = Report()
    _check_pathogen_shedding_curve(
        _pathogen(shedding_curve_log10=[1.0, -0.5]),
        negative,
    )
    assert any(f.rule == "MATH_BOUND" for f in negative.errors)

    ok = Report()
    _check_pathogen_shedding_curve(_pathogen(), ok)
    assert not ok.errors and not any(f.rule == "LOGIC_SHED" for f in ok.warnings)


def test_ois_weights_non_negative_bounds() -> None:
    costs = SimpleNamespace(
        operational_impact_weights=SimpleNamespace(
            per_passenger_quarantined=-1.0,
            per_essential_crew_quarantined=1.0,
            per_passenger_isolated=1.0,
            per_closed_galley_zone=1.0,
            per_fleet_ppe_active=1.0,
        )
    )
    report = Report()
    _check_ois_weights(costs, report)
    assert any(f.rule == "BOUNDS_OIS" for f in report.errors)

    costs.operational_impact_weights.per_passenger_quarantined = 0.0
    ok = Report()
    _check_ois_weights(costs, ok)
    assert not any(f.rule == "BOUNDS_OIS" for f in ok.errors)
