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
from engines.infection_dynamics_bridge import (
    IllnessStatus,
    InfectionStatus,
    KorkinShipEngine,
)
from engines.transmission_core import (
    SANITARY_DWELL_FEMALE_MULTIPLIER,
    SANITARY_DWELL_SECONDS,
    ContactTracingMatrix,
    TransmissionCore,
)
from engines.voyage_itinerary import LOCATION_ASHORE
from picard_framework.analysis import figures as figures_mod
from tests.test_diagnostic_cascade import (
    _default_tiers,
    _make_agent,
    _StubTestRunner,
)
from tests.test_shared_sanitary_zones import _agent as _sanitary_agent
from tests.test_shared_sanitary_zones import _make_core as _make_sanitary_core
from tools.sanity_checker import (
    Report,
    _check_ois_weights,
    _check_pathogen_shedding_curve,
    _check_pathogen_timing_bounds,
)

# --- figures helpers ---------------------------------------------------------


def test_heatmap_matrix_empty_and_populated() -> None:
    empty = figures_mod._heatmap_matrix({}, ["p1"], ["s1"])
    assert len(empty) == 1
    assert len(empty[0]) == 1
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
    assert not ok.errors
    assert not any(f.rule == "LOGIC_SHED" for f in ok.warnings)


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


# --- KorkinShipEngine native transmission helpers ----------------------------


def _native_engine_in_one_zone(
    initial_infected: int, *, seed: int = 3, zone_index: int = 0,
) -> tuple[KorkinShipEngine, str]:
    """Engine on the legacy path with every agent co-located and shedders past onset."""
    eng = KorkinShipEngine(
        num_passengers=200, num_crew=50, initial_infected=initial_infected, seed=seed,
    )
    for agent in eng.agents:
        if agent.is_infected:
            agent.time_infected = (agent.time_infected or 0) + 48
    zone = eng._all_zone_names[zone_index]
    for agent in eng.agents:
        agent.current_location = zone
    return eng, zone


def _count(eng: KorkinShipEngine, status: InfectionStatus) -> int:
    return sum(a.infection_status == status for a in eng.agents)


def test_native_transmission_grades_with_shedder_count() -> None:
    new_infections = []
    for n in (0, 2, 10, 40):
        eng, _ = _native_engine_in_one_zone(n)
        before = _count(eng, InfectionStatus.SUSCEPTIBLE)
        eng._native_transmission(LOCATION_ASHORE)
        new_infections.append(before - _count(eng, InfectionStatus.SUSCEPTIBLE))

    assert new_infections[0] == 0
    assert new_infections == sorted(new_infections)
    assert new_infections[-1] - new_infections[1] >= 10


def test_native_transmission_new_infections_are_fresh_and_dosed() -> None:
    eng, _ = _native_engine_in_one_zone(10)
    seeded = {a.agent_id for a in eng.agents if a.is_infected}
    immune_before = _count(eng, InfectionStatus.IMMUNE)
    eng._native_transmission(LOCATION_ASHORE)

    fresh = [a for a in eng.agents if a.is_infected and a.agent_id not in seeded]
    assert fresh
    for agent in fresh:
        assert agent.time_infected == 0
        assert agent.illness_status == IllnessStatus.NOT_ILL
        assert math.isfinite(agent.acquired_particles)
        assert agent.acquired_particles > 0
    assert _count(eng, InfectionStatus.IMMUNE) == immune_before


def test_native_transmission_skips_quarantine_and_ashore() -> None:
    for excluded in ("Isolated_In_Quarters", LOCATION_ASHORE):
        eng, _ = _native_engine_in_one_zone(10)
        for agent in eng.agents:
            agent.current_location = excluded
        before = _count(eng, InfectionStatus.SUSCEPTIBLE)
        eng._native_transmission(LOCATION_ASHORE)
        assert _count(eng, InfectionStatus.SUSCEPTIBLE) == before


def test_native_transmission_in_zone_needs_both_shedders_and_susceptible() -> None:
    eng, _ = _native_engine_in_one_zone(10)
    shedders = [a for a in eng.agents if a.current_shedding > 0]
    susceptible = [a for a in eng.agents if a.infection_status == InfectionStatus.SUSCEPTIBLE]
    assert shedders
    assert susceptible

    eng._native_transmission_in_zone(shedders)
    eng._native_transmission_in_zone(susceptible)
    assert all(a.infection_status == InfectionStatus.SUSCEPTIBLE for a in susceptible)

    eng._native_transmission_in_zone(shedders + susceptible)
    assert any(a.is_infected for a in susceptible)


# --- transmission_core pool-init helpers -------------------------------------


def test_initialize_food_pools_gated_and_zone_selective() -> None:
    core = _make_sanitary_core()
    core._initialize_food_pools("p", {"food_contamination": {"enabled": False}}, ["D1"])
    assert "p" not in core.food_pools

    core._initialize_food_pools("p", {"food_contamination": {"enabled": True}}, ["D1", "D2"])
    assert core.food_pools["p"] == {"D1": 0.0, "D2": 0.0}

    core._initialize_food_pools(
        "q", {"food_contamination": {"enabled": True, "food_zones": ["Galley"]}}, ["D1"],
    )
    assert core.food_pools["q"] == {"Galley": 0.0}


@pytest.mark.parametrize("baseline", [0.5, 2.0])
def test_initialize_environmental_load_seeds_matching_zones(baseline: float) -> None:
    core = _make_sanitary_core()
    zones = ["HD_5T_M", "HD_5T_F", "TheaterLng"]
    core._initialize_environmental_load("p", {"environmental_contamination": {"enabled": False}}, zones)
    assert "p" not in core.environmental_load

    profile = {"environmental_contamination": {
        "enabled": True, "baseline_environmental_load": baseline,
    }}
    core._initialize_environmental_load("p", profile, zones)
    assert core.environmental_load["p"] == pytest.approx(baseline)
    assert "p" not in core.env_contamination

    profile["environmental_contamination"]["source_zones"] = ["HD_5T_*"]
    core._initialize_environmental_load("p", profile, zones)
    assert set(core.env_contamination["p"]) == {"HD_5T_M", "HD_5T_F"}
    assert all(v == pytest.approx(baseline) for v in core.env_contamination["p"].values())


# --- transmission_core dose-response event seam -----------------------------


def test_record_transmission_event_dominant_and_breakdown_filter() -> None:
    matrix = ContactTracingMatrix(epoch=3)
    events: list = []
    agent = _sanitary_agent(7, "TheaterLng")
    pw = {"noro:fomite": 0.2, "noro:droplet": 0.7, "flu:droplet": 5.0}
    TransmissionCore._record_transmission_event(
        3, agent, "noro", 0.9, False, "", None, {"droplet": 0.9}, pw, matrix, events,
    )
    assert len(events) == 1
    assert len(matrix.transmission_events) == 1
    assert events[0].pathway == "flu:droplet"
    assert events[0].source_strain_id is None
    rec = matrix.transmission_events[0]
    assert set(rec["pathway_breakdown"]) == {"noro:fomite", "noro:droplet"}
    assert rec["total_dose"] == pytest.approx(0.9)

    TransmissionCore._record_transmission_event(
        3, agent, "noro", 0.1, True, "s1", 2, {}, {}, matrix, events,
    )
    assert events[1].pathway == "unknown"
    assert events[1].source_strain_id == "s1"
    assert matrix.transmission_events[1]["superinfection"] is True


# --- transmission_core sanitary-visit seam ----------------------------------


def test_sanitary_dwell_seconds_by_gender() -> None:
    male = TransmissionCore._sanitary_dwell_seconds(_sanitary_agent(1, "TheaterLng", "male"))
    female = TransmissionCore._sanitary_dwell_seconds(_sanitary_agent(2, "TheaterLng", "female"))
    assert male == pytest.approx(SANITARY_DWELL_SECONDS)
    assert female == pytest.approx(SANITARY_DWELL_SECONDS * SANITARY_DWELL_FEMALE_MULTIPLIER)
    assert female > male


def test_draw_agent_sanitary_visits_home_books_telemetry_only() -> None:
    core = _make_sanitary_core(seed=3)
    core._sanitary_visits = {}
    home = _sanitary_agent(1, "PC_D5_P_F")
    for _ in range(50):
        core._draw_agent_sanitary_visits("PC_D5_P_F", home)
    assert core._sanitary_visits == {}
    assert core.sanitary_telemetry["visits"] > 0
    assert core.sanitary_telemetry["person_seconds"] == pytest.approx(
        core.sanitary_telemetry["visits"] * SANITARY_DWELL_SECONDS,
    )

    away = _sanitary_agent(2, "TheaterLng")
    for _ in range(50):
        core._draw_agent_sanitary_visits("TheaterLng", away)
    assert set(core._sanitary_visits.get(2, [])) == {"HD_5T_M"}
    assert len(core._sanitary_visits[2]) > 0

    unserved = _sanitary_agent(3, "Casino")
    before = core.sanitary_telemetry["unresolved"]
    for _ in range(50):
        core._draw_agent_sanitary_visits("Casino", unserved)
    assert core.sanitary_telemetry["unresolved"] > before
    assert 3 not in core._sanitary_visits
