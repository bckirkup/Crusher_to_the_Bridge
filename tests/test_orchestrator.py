"""
test_orchestrator.py – Unit tests for the refactored orchestrator module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tests each segregated function in orchestrator.py independently.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from orchestrator_types import (
    STATUS_BASELINE,
    STATUS_SUSPECTED,
    STATUS_CONFIRMED,
    SYMPTOM_ASYMPTOMATIC,
    SYMPTOM_SYMPTOMATIC,
    SYMPTOM_ISOLATED,
    SYMPTOM_NON_COMPLIANT,
    LOCATION_ISOLATED,
    DEFAULT_AIRBORNE_FRACTION,
    DEFAULT_SURFACE_FRACTION,
    DEFAULT_GREYWATER_FRACTION,
    DEFAULT_GRAYWATER_PROPAGATION_FACTOR,
    SimulationState,
)
from orchestrator_init import (
    load_spatial_layout as _load_spatial_layout,
    initialize_ship_graph as _initialize_ship_graph,
    check_escalation as _check_escalation,
    load_pathogen_profiles as _load_pathogen_profiles,
    engine_payload_to_schema as _engine_payload_to_schema,
)
from orchestrator_epoch import (
    step_quarantine_confinement as _step_quarantine_confinement,
    confine_agents as _confine_agents,
    confine_all_agents as _confine_all_agents,
    step_cost_accounting as _step_cost_accounting,
)
from crusher_labs import load_config
from telemetry_buffer.schema import make_agent


# ── SimulationState tests ────────────────────────────────────────────────

class TestSimulationState:
    def test_default_state(self) -> None:
        state = SimulationState()
        assert state.trigger_status == STATUS_BASELINE
        assert len(state.isolated_ids) == 0
        assert len(state.quarantine_refusers) == 0
        assert len(state.escalation_log) == 0
        assert len(state.compliance_log) == 0
        assert len(state.simulation_history) == 0

    def test_mutable_state(self) -> None:
        state = SimulationState()
        state.isolated_ids.add(5)
        state.quarantine_refusers.add(10)
        state.trigger_status = STATUS_CONFIRMED
        assert 5 in state.isolated_ids
        assert 10 in state.quarantine_refusers
        assert state.trigger_status == STATUS_CONFIRMED


# ── Spatial layout tests ─────────────────────────────────────────────────

class TestLoadSpatialLayout:
    def test_loads_from_config(self) -> None:
        cfg = load_config()
        zones = _load_spatial_layout(cfg)
        assert zones is not None
        assert len(zones) >= 1
        for z in zones:
            assert "name" in z
            assert "type" in z
            assert "volume_m3" in z

    def test_returns_none_if_no_path(self) -> None:
        cfg = {"ship_graph": {}}
        assert _load_spatial_layout(cfg) is None

    def test_returns_none_if_file_missing(self) -> None:
        cfg = {"ship_graph": {"spatial_layout": "nonexistent_path.json"}}
        assert _load_spatial_layout(cfg) is None


class TestInitializeShipGraph:
    def test_basic_structure(self) -> None:
        cfg = load_config()
        ship = _initialize_ship_graph(cfg)
        assert "zones" in ship
        assert "zone_names" in ship
        assert "high_traffic_zones" in ship
        assert "num_agents" in ship
        assert "agent_roles" in ship

    def test_zone_names_match_zones(self) -> None:
        cfg = load_config()
        ship = _initialize_ship_graph(cfg)
        names = [z["name"] for z in ship["zones"]]
        assert ship["zone_names"] == names

    def test_agent_roles_assigned(self) -> None:
        cfg = load_config()
        ship = _initialize_ship_graph(cfg)
        for aid in range(ship["num_agents"]):
            assert aid in ship["agent_roles"]
            assert ship["agent_roles"][aid] in ("passenger", "crew")

    def test_passenger_crew_ratio(self) -> None:
        cfg = load_config()
        ship = _initialize_ship_graph(cfg)
        passengers = sum(1 for r in ship["agent_roles"].values() if r == "passenger")
        crew = sum(1 for r in ship["agent_roles"].values() if r == "crew")
        assert passengers + crew == ship["num_agents"]
        assert passengers >= crew

    def test_high_traffic_subset_of_zones(self) -> None:
        cfg = load_config()
        ship = _initialize_ship_graph(cfg)
        for ht in ship["high_traffic_zones"]:
            assert ht in ship["zone_names"]


# ── Escalation tests ────────────────────────────────────────────────────

class TestCheckEscalation:
    def test_baseline_stays_baseline(self) -> None:
        cfg = {"escalation": {"syndromic_suspect_threshold": 3}}
        syn_result = {"sick_call_count": 1}
        assert _check_escalation(STATUS_BASELINE, syn_result, None, cfg) == STATUS_BASELINE

    def test_baseline_to_suspected(self) -> None:
        cfg = {"escalation": {"syndromic_suspect_threshold": 3}}
        syn_result = {"sick_call_count": 5}
        assert _check_escalation(STATUS_BASELINE, syn_result, None, cfg) == STATUS_SUSPECTED

    def test_suspected_stays_suspected_no_pcr(self) -> None:
        cfg = {"escalation": {"pcr_confirm_ct_threshold": 35.0}}
        syn_result = {"sick_call_count": 5}
        assert _check_escalation(STATUS_SUSPECTED, syn_result, None, cfg) == STATUS_SUSPECTED

    def test_suspected_to_confirmed(self) -> None:
        cfg = {"escalation": {"pcr_confirm_ct_threshold": 35.0}}
        syn_result = {"sick_call_count": 5}
        pcr_result = {"zone_results": {"MedBay": {"ct_value": 30.0}}}
        assert _check_escalation(STATUS_SUSPECTED, syn_result, pcr_result, cfg) == STATUS_CONFIRMED

    def test_suspected_stays_if_ct_too_high(self) -> None:
        cfg = {"escalation": {"pcr_confirm_ct_threshold": 35.0}}
        syn_result = {"sick_call_count": 5}
        pcr_result = {"zone_results": {"MedBay": {"ct_value": 38.0}}}
        assert _check_escalation(STATUS_SUSPECTED, syn_result, pcr_result, cfg) == STATUS_SUSPECTED

    def test_confirmed_stays_confirmed(self) -> None:
        cfg = {"escalation": {}}
        syn_result = {"sick_call_count": 0}
        assert _check_escalation(STATUS_CONFIRMED, syn_result, None, cfg) == STATUS_CONFIRMED

    def test_default_thresholds(self) -> None:
        cfg = {}
        syn_result = {"sick_call_count": 3}
        assert _check_escalation(STATUS_BASELINE, syn_result, None, cfg) == STATUS_SUSPECTED


# ── Pathogen profile loading tests ────────────────────────────────────────

class TestLoadPathogenProfiles:
    def test_loads_default_profiles(self) -> None:
        cfg = load_config()
        profiles = _load_pathogen_profiles(cfg)
        assert len(profiles) >= 1
        for pid, prof in profiles.items():
            assert "pathogen_id" in prof
            assert "name" in prof
            assert "transmission_routes" in prof

    def test_returns_empty_if_no_file(self) -> None:
        cfg = {"multi_pathogen": {"profiles_path": "nonexistent.json"}}
        profiles = _load_pathogen_profiles(cfg)
        assert profiles == {}


# ── Engine payload conversion tests ──────────────────────────────────────

class TestEnginePayloadToSchema:
    def test_normal_agent(self) -> None:
        engine_payload = {
            "agents": [
                {"agent_id": 0, "symptom_status": SYMPTOM_ASYMPTOMATIC,
                 "shedding_rate": 0.0, "location": "Bridge"},
            ],
            "spaces": {
                "Bridge": {"pathogen_mass": 10.0},
            },
        }
        agents, spaces = _engine_payload_to_schema(engine_payload, set(), set())
        assert len(agents) == 1
        assert agents[0]["agent_id"] == 0
        assert agents[0]["symptom_status"] == SYMPTOM_ASYMPTOMATIC
        assert "Bridge" in spaces

    def test_isolated_agent(self) -> None:
        engine_payload = {
            "agents": [
                {"agent_id": 5, "symptom_status": SYMPTOM_SYMPTOMATIC,
                 "shedding_rate": 50.0, "location": "MedBay"},
            ],
            "spaces": {},
        }
        agents, _ = _engine_payload_to_schema(engine_payload, {5}, set())
        assert agents[0]["symptom_status"] == SYMPTOM_ISOLATED
        assert agents[0]["location"] == LOCATION_ISOLATED
        assert agents[0]["shedding_rate"] == 0.0

    def test_non_compliant_agent(self) -> None:
        engine_payload = {
            "agents": [
                {"agent_id": 3, "symptom_status": SYMPTOM_SYMPTOMATIC,
                 "shedding_rate": 30.0, "location": "Galley"},
            ],
            "spaces": {},
        }
        agents, _ = _engine_payload_to_schema(engine_payload, set(), {3})
        assert agents[0]["symptom_status"] == SYMPTOM_NON_COMPLIANT
        assert agents[0]["shedding_rate"] == 30.0

    def test_pathogen_metadata_preserved(self) -> None:
        engine_payload = {
            "agents": [
                {"agent_id": 0, "symptom_status": SYMPTOM_ASYMPTOMATIC,
                 "pathogen_infections": {"norovirus": {}},
                 "susceptibility_multiplier": {"norovirus": 1.0},
                 "microflora_disruption": 0.5},
            ],
            "spaces": {},
        }
        agents, _ = _engine_payload_to_schema(engine_payload, set(), set())
        assert "pathogen_infections" in agents[0]
        assert "susceptibility_multiplier" in agents[0]
        assert agents[0]["microflora_disruption"] == 0.5

    def test_space_with_pathogen_mass_by_id(self) -> None:
        engine_payload = {
            "agents": [],
            "spaces": {
                "Bridge": {
                    "pathogen_mass": 10.0,
                    "pathogen_mass_by_id": {"norovirus": 8.0, "sars_cov_2": 2.0},
                },
            },
        }
        _, spaces = _engine_payload_to_schema(engine_payload, set(), set())
        assert spaces["Bridge"]["pathogen_mass_by_id"]["norovirus"] == 8.0


# ── Quarantine confinement tests ─────────────────────────────────────────

class TestStepQuarantineConfinement:
    def _make_syndromic_mock(self, compliance: bool = True) -> MagicMock:
        mock = MagicMock()
        mock.check_quarantine_compliance.return_value = compliance
        return mock

    def test_protocol_driven_confinement(self) -> None:
        state = SimulationState()
        agents = [{"agent_id": 0, "symptom_status": SYMPTOM_SYMPTOMATIC, "shedding_rate": 50.0}]
        merged = {"confine_symptomatic_to_quarters": True}
        syndromic = self._make_syndromic_mock(compliance=True)

        _step_quarantine_confinement(5, agents, merged, STATUS_CONFIRMED, state, syndromic)
        assert 0 in state.isolated_ids

    def test_legacy_confirmed_fallback(self) -> None:
        state = SimulationState()
        agents = [{"agent_id": 1, "symptom_status": SYMPTOM_SYMPTOMATIC, "shedding_rate": 50.0}]
        merged = {}
        syndromic = self._make_syndromic_mock(compliance=True)

        _step_quarantine_confinement(5, agents, merged, STATUS_CONFIRMED, state, syndromic)
        assert 1 in state.isolated_ids

    def test_no_confinement_at_baseline(self) -> None:
        state = SimulationState()
        agents = [{"agent_id": 2, "symptom_status": SYMPTOM_SYMPTOMATIC}]
        merged = {}
        syndromic = self._make_syndromic_mock(compliance=True)

        _step_quarantine_confinement(5, agents, merged, STATUS_BASELINE, state, syndromic)
        assert len(state.isolated_ids) == 0

    def test_refusal_tracked(self) -> None:
        state = SimulationState()
        agents = [{"agent_id": 7, "symptom_status": SYMPTOM_SYMPTOMATIC}]
        merged = {"confine_symptomatic_to_quarters": True}
        syndromic = self._make_syndromic_mock(compliance=False)

        _step_quarantine_confinement(3, agents, merged, STATUS_CONFIRMED, state, syndromic)
        assert 7 in state.quarantine_refusers
        assert state.quarantine_order_epoch[7] == 3

    def test_already_isolated_skipped(self) -> None:
        state = SimulationState()
        state.isolated_ids.add(0)
        agents = [{"agent_id": 0, "symptom_status": SYMPTOM_SYMPTOMATIC}]
        merged = {"confine_symptomatic_to_quarters": True}
        syndromic = self._make_syndromic_mock(compliance=True)

        _step_quarantine_confinement(5, agents, merged, STATUS_CONFIRMED, state, syndromic)
        assert len(state.compliance_log) == 0


# ── SOP-009: General confinement tests ───────────────────────────────────

class TestSOP009GeneralConfinement:
    def _make_syndromic_mock(self, compliance: bool = True) -> MagicMock:
        mock = MagicMock()
        mock.check_quarantine_compliance.return_value = compliance
        return mock

    def test_confine_all_confines_asymptomatic_agents(self) -> None:
        state = SimulationState()
        agents = [
            {"agent_id": 0, "symptom_status": SYMPTOM_ASYMPTOMATIC},
            {"agent_id": 1, "symptom_status": SYMPTOM_SYMPTOMATIC},
        ]
        merged = {"confine_all_to_quarters": True}
        syndromic = self._make_syndromic_mock(compliance=True)
        _step_quarantine_confinement(5, agents, merged, STATUS_CONFIRMED, state, syndromic)
        assert 0 in state.isolated_ids
        assert 1 in state.isolated_ids

    def test_confine_all_takes_priority_over_symptomatic_only(self) -> None:
        state = SimulationState()
        agents = [
            {"agent_id": 0, "symptom_status": SYMPTOM_ASYMPTOMATIC},
        ]
        merged = {
            "confine_all_to_quarters": True,
            "confine_symptomatic_to_quarters": True,
        }
        syndromic = self._make_syndromic_mock(compliance=True)
        _step_quarantine_confinement(5, agents, merged, STATUS_CONFIRMED, state, syndromic)
        assert 0 in state.isolated_ids

    def test_confine_all_skips_already_isolated(self) -> None:
        state = SimulationState()
        state.isolated_ids.add(0)
        agents = [
            {"agent_id": 0, "symptom_status": SYMPTOM_SYMPTOMATIC},
            {"agent_id": 1, "symptom_status": SYMPTOM_ASYMPTOMATIC},
        ]
        syndromic = self._make_syndromic_mock(compliance=True)
        _confine_all_agents(5, agents, state, syndromic)
        general_entries = [c for c in state.compliance_log if c["action"] == "general_confinement"]
        assert len(general_entries) == 1
        assert general_entries[0]["agent_id"] == 1

    def test_confine_all_refusal_tracked(self) -> None:
        state = SimulationState()
        agents = [{"agent_id": 4, "symptom_status": SYMPTOM_ASYMPTOMATIC}]
        syndromic = self._make_syndromic_mock(compliance=False)
        _confine_all_agents(5, agents, state, syndromic)
        assert 4 in state.quarantine_refusers
        refusal_entries = [c for c in state.compliance_log
                          if c["action"] == "refused_general_confinement"]
        assert len(refusal_entries) == 1


# ── SOP-010: Surface decontamination & VSP threshold tests ──────────────

class TestSOP010Modifiers:
    def test_surface_decontamination_reduces_mass(self) -> None:
        from orchestrator_epoch import apply_surface_decontamination
        cfg = load_config()
        from orchestrator_init import build_engine
        engine = build_engine(cfg, seed=42)
        engine.zone_pathogen_mass["Bridge"] = 100.0
        apply_surface_decontamination(engine, 0.60)
        assert abs(engine.zone_pathogen_mass["Bridge"] - 40.0) < 1e-9

    def test_surface_decontamination_factor_clamped(self) -> None:
        from orchestrator_epoch import apply_surface_decontamination
        cfg = load_config()
        from orchestrator_init import build_engine
        engine = build_engine(cfg, seed=42)
        engine.zone_pathogen_mass["Bridge"] = 100.0
        apply_surface_decontamination(engine, 1.5)
        assert engine.zone_pathogen_mass["Bridge"] == 0.0

    def test_vsp_threshold_overridable(self) -> None:
        from engines.infection_dynamics_bridge import VSP_THRESHOLD_FRACTION
        cfg = load_config()
        from orchestrator_init import build_engine
        engine = build_engine(cfg, seed=42)
        assert engine.vsp_threshold_fraction == VSP_THRESHOLD_FRACTION
        engine.vsp_threshold_fraction = 0.05
        assert engine.vsp_threshold_fraction == 0.05


# ── Zone closure tests ──────────────────────────────────────────────────

class TestZoneClosures:
    def test_agents_relocated_from_closed_zones(self) -> None:
        from orchestrator_epoch import apply_zone_closures
        cfg = load_config()
        from orchestrator_init import build_engine
        engine = build_engine(cfg, seed=42)
        galley_agents = [a for a in engine.agents if a.current_location == "Galley"]
        if galley_agents:
            home = galley_agents[0].home_zone
            apply_zone_closures(engine, ["Galley"])
            for a in engine.agents:
                assert a.current_location != "Galley"

    def test_empty_close_list_is_noop(self) -> None:
        from orchestrator_epoch import apply_zone_closures
        cfg = load_config()
        from orchestrator_init import build_engine
        engine = build_engine(cfg, seed=42)
        locations_before = [a.current_location for a in engine.agents]
        apply_zone_closures(engine, [])
        locations_after = [a.current_location for a in engine.agents]
        assert locations_before == locations_after


# ── Edge-case tests ─────────────────────────────────────────────────────

class TestEdgeCaseBoundaries:
    def test_zero_shedding_agent_not_confined_by_shedding(self) -> None:
        state = SimulationState()
        agents = [{"agent_id": 0, "symptom_status": SYMPTOM_ASYMPTOMATIC, "shedding_rate": 0.0}]
        merged = {}
        syndromic = MagicMock()
        syndromic.check_quarantine_compliance.return_value = True
        _step_quarantine_confinement(1, agents, merged, STATUS_CONFIRMED, state, syndromic)
        assert 0 not in state.isolated_ids

    def test_empty_agent_list(self) -> None:
        state = SimulationState()
        syndromic = MagicMock()
        _step_quarantine_confinement(
            1, [], {"confine_symptomatic_to_quarters": True},
            STATUS_CONFIRMED, state, syndromic,
        )
        assert len(state.isolated_ids) == 0
        assert len(state.compliance_log) == 0

    def test_all_agents_already_isolated(self) -> None:
        state = SimulationState()
        state.isolated_ids = {0, 1, 2}
        agents = [
            {"agent_id": i, "symptom_status": SYMPTOM_SYMPTOMATIC}
            for i in range(3)
        ]
        syndromic = MagicMock()
        syndromic.check_quarantine_compliance.return_value = True
        _step_quarantine_confinement(
            5, agents, {"confine_all_to_quarters": True},
            STATUS_CONFIRMED, state, syndromic,
        )
        assert len(state.compliance_log) == 0


# ── Defaults / Law compliance tests ─────────────────────────────────────

class TestDefaultConstants:
    def test_airborne_surface_sum_to_one(self) -> None:
        assert abs(DEFAULT_AIRBORNE_FRACTION + DEFAULT_SURFACE_FRACTION - 1.0) < 1e-9

    def test_fractions_in_range(self) -> None:
        assert 0.0 < DEFAULT_AIRBORNE_FRACTION < 1.0
        assert 0.0 < DEFAULT_SURFACE_FRACTION < 1.0
        assert 0.0 < DEFAULT_GREYWATER_FRACTION < 1.0
        assert 0.0 < DEFAULT_GRAYWATER_PROPAGATION_FACTOR < 1.0
