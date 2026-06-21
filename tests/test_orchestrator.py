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
    INFECTION_SUSCEPTIBLE,
    INFECTION_INFECTED,
    PRESENTATION_ASYMPTOMATIC,
    PRESENTATION_SYMPTOMATIC,
    COMPLIANCE_COMPLIANT,
    COMPLIANCE_ISOLATED,
    COMPLIANCE_NON_COMPLIANT,
    SYMPTOM_ASYMPTOMATIC,
    SYMPTOM_SYMPTOMATIC,
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
from engines.wearable_monitor import (
    WearableDevice,
    WearableMonitor,
    AgentWearableState,
    build_wearable_device_from_config,
    build_wearable_monitor_from_config,
    DEFAULT_CHANNEL_BASELINES,
    DEFAULT_INFECTION_RESPONSES,
    DEFAULT_PHASE_BOUNDARIES,
    _get_infection_phase,
    _clamp_channel,
)
from crusher_labs.modalities.wearable import WearableDataStream
from engines.infection_dynamics_bridge import KorkinShipEngine


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

    def test_agent_classes_present(self) -> None:
        cfg = load_config()
        ship = _initialize_ship_graph(cfg)
        assert "agent_classes" in ship
        class_ids = [c["class_id"] for c in ship["agent_classes"]]
        assert "crew_medical" in class_ids
        assert "passenger_general" in class_ids

    def test_gender_distribution_present(self) -> None:
        cfg = load_config()
        ship = _initialize_ship_graph(cfg)
        assert "gender_distribution" in ship
        gd = ship["gender_distribution"]
        assert "male" in gd
        assert "female" in gd

    def test_agent_class_fractions_sum_to_one(self) -> None:
        cfg = load_config()
        ship = _initialize_ship_graph(cfg)
        classes = ship.get("agent_classes", [])
        total_frac = sum(c.get("fraction", 0) for c in classes)
        assert abs(total_frac - 1.0) < 0.01


# ── Agent class engine tests ────────────────────────────────────────────

class TestAgentClassEngine:
    def test_engine_creates_agents_with_classes(self) -> None:
        from engines.infection_dynamics_bridge import KorkinShipEngine
        engine = KorkinShipEngine(
            num_passengers=10, num_crew=10, initial_infected=1,
            agent_classes=[
                {"class_id": "passenger_general", "role_group": "passenger", "fraction": 0.50,
                 "home_zone_preference": "Berthing", "duty_zone": "", "free_zone_preference": ""},
                {"class_id": "crew_medical", "role_group": "crew", "fraction": 0.25,
                 "home_zone_preference": "Berthing", "duty_zone": "MedBay", "free_zone_preference": "MedBay"},
                {"class_id": "crew_general", "role_group": "crew", "fraction": 0.25,
                 "home_zone_preference": "Berthing", "duty_zone": "", "free_zone_preference": ""},
            ],
            seed=42,
        )
        assert len(engine.agents) == 20
        classes = {a.agent_class for a in engine.agents}
        assert "passenger_general" in classes
        assert "crew_medical" in classes
        assert "crew_general" in classes

    def test_engine_assigns_gender(self) -> None:
        from engines.infection_dynamics_bridge import KorkinShipEngine
        engine = KorkinShipEngine(
            num_passengers=50, num_crew=50, initial_infected=1,
            gender_distribution={"male": 0.50, "female": 0.50},
            seed=42,
        )
        genders = {a.gender for a in engine.agents}
        assert "male" in genders
        assert "female" in genders
        for a in engine.agents:
            assert a.gender in ("male", "female")

    def test_legacy_mode_still_works(self) -> None:
        from engines.infection_dynamics_bridge import KorkinShipEngine
        engine = KorkinShipEngine(
            num_passengers=10, num_crew=5, initial_infected=1,
            seed=42,
        )
        assert len(engine.agents) == 15
        roles = {a.role for a in engine.agents}
        assert "passenger" in roles
        assert "crew" in roles
        for a in engine.agents:
            assert a.agent_class in ("passenger_general", "crew_general")
            assert a.gender in ("male", "female", "unknown")

    def test_medical_crew_duty_zone(self) -> None:
        from engines.infection_dynamics_bridge import KorkinShipEngine
        engine = KorkinShipEngine(
            num_passengers=0, num_crew=20, initial_infected=0,
            agent_classes=[
                {"class_id": "crew_medical", "role_group": "crew", "fraction": 1.0,
                 "home_zone_preference": "Berthing", "duty_zone": "MedBay",
                 "free_zone_preference": "MedBay"},
            ],
            seed=42,
        )
        for a in engine.agents:
            assert a.agent_class == "crew_medical"
            assert "MedBay" in a.work_zone or "MedBay" == a.work_zone

    def test_gender_in_schema_export(self) -> None:
        from engines.infection_dynamics_bridge import KorkinShipEngine
        engine = KorkinShipEngine(
            num_passengers=5, num_crew=5, initial_infected=1,
            seed=42,
        )
        for a in engine.agents:
            d = a.to_schema_dict()
            assert "agent_class" in d
            assert "gender" in d
            assert d["gender"] in ("male", "female", "unknown")

    def test_summary_includes_class_and_gender(self) -> None:
        from engines.infection_dynamics_bridge import KorkinShipEngine
        engine = KorkinShipEngine(
            num_passengers=10, num_crew=10, initial_infected=1, seed=42,
        )
        summary = engine.get_summary()
        assert "agent_classes" in summary
        assert "gender_distribution" in summary
        assert sum(summary["agent_classes"].values()) == 20
        assert sum(summary["gender_distribution"].values()) == 20


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
        agents, spaces = _engine_payload_to_schema(engine_payload, set(), set(), set())
        assert len(agents) == 1
        assert agents[0]["agent_id"] == 0
        assert agents[0]["infection_state"] == INFECTION_SUSCEPTIBLE
        assert agents[0]["compliance_status"] == COMPLIANCE_COMPLIANT
        assert "Bridge" in spaces

    def test_isolated_agent(self) -> None:
        engine_payload = {
            "agents": [
                {
                    "agent_id": 5,
                    "infection_state": INFECTION_INFECTED,
                    "symptom_presentation": PRESENTATION_SYMPTOMATIC,
                    "compliance_status": COMPLIANCE_COMPLIANT,
                    "shedding_rate": 50.0,
                    "location": "MedBay",
                },
            ],
            "spaces": {},
        }
        agents, _ = _engine_payload_to_schema(engine_payload, {5}, set(), set())
        assert agents[0]["compliance_status"] == COMPLIANCE_ISOLATED
        assert agents[0]["infection_state"] == INFECTION_INFECTED
        assert agents[0]["symptom_presentation"] == PRESENTATION_SYMPTOMATIC
        assert agents[0]["location"] == LOCATION_ISOLATED
        assert agents[0]["shedding_rate"] == 0.0

    def test_non_compliant_agent(self) -> None:
        engine_payload = {
            "agents": [
                {
                    "agent_id": 3,
                    "infection_state": INFECTION_INFECTED,
                    "symptom_presentation": PRESENTATION_SYMPTOMATIC,
                    "compliance_status": COMPLIANCE_COMPLIANT,
                    "shedding_rate": 30.0,
                    "location": "Galley",
                },
            ],
            "spaces": {},
        }
        agents, _ = _engine_payload_to_schema(engine_payload, set(), set(), {3})
        assert agents[0]["compliance_status"] == COMPLIANCE_NON_COMPLIANT
        assert agents[0]["infection_state"] == INFECTION_INFECTED
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
        agents, _ = _engine_payload_to_schema(engine_payload, set(), set(), set())
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
        _, spaces = _engine_payload_to_schema(engine_payload, set(), set(), set())
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
        assert 0 in state.quarantined_ids

    def test_legacy_confirmed_fallback(self) -> None:
        state = SimulationState()
        agents = [{"agent_id": 1, "symptom_status": SYMPTOM_SYMPTOMATIC, "shedding_rate": 50.0}]
        merged = {}
        syndromic = self._make_syndromic_mock(compliance=True)

        _step_quarantine_confinement(5, agents, merged, STATUS_CONFIRMED, state, syndromic)
        assert 1 in state.quarantined_ids

    def test_no_confinement_at_baseline(self) -> None:
        state = SimulationState()
        agents = [{"agent_id": 2, "symptom_status": SYMPTOM_SYMPTOMATIC}]
        merged = {}
        syndromic = self._make_syndromic_mock(compliance=True)

        _step_quarantine_confinement(5, agents, merged, STATUS_BASELINE, state, syndromic)
        assert len(state.quarantined_ids) == 0

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

    def test_already_quarantined_skipped(self) -> None:
        state = SimulationState()
        state.quarantined_ids.add(0)
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
        assert 0 in state.quarantined_ids
        assert 1 in state.quarantined_ids

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
        assert 0 in state.quarantined_ids

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
        assert 0 not in state.quarantined_ids

    def test_empty_agent_list(self) -> None:
        state = SimulationState()
        syndromic = MagicMock()
        _step_quarantine_confinement(
            1, [], {"confine_symptomatic_to_quarters": True},
            STATUS_CONFIRMED, state, syndromic,
        )
        assert len(state.quarantined_ids) == 0
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


# ── Wearable monitoring tests ───────────────────────────────────────────

def _build_test_engine() -> KorkinShipEngine:
    """Build a minimal engine for wearable tests."""
    cfg = load_config()
    graph_cfg = cfg.get("ship_graph", {})
    num_agents = graph_cfg.get("num_agents", 20)
    roles_cfg = graph_cfg.get("agent_roles", {})
    pf = roles_cfg.get("passenger_fraction", 0.70)
    np_ = int(num_agents * pf)
    nc = num_agents - np_
    zones = graph_cfg.get("zones", [])
    engine_zones = [
        {"name": z["name"], "type": z["type"], "capacity": z.get("traffic", "medium")}
        for z in zones
    ]
    return KorkinShipEngine(
        num_passengers=np_,
        num_crew=nc,
        initial_infected=1,
        zones=engine_zones,
        seed=42,
        agent_classes=graph_cfg.get("agent_classes"),
        gender_distribution=graph_cfg.get("gender_distribution"),
    )


class TestWearableDevice:
    def test_device_creation(self) -> None:
        dev = WearableDevice(
            device_id="test_ring",
            channels=["heart_rate", "body_temp"],
        )
        assert dev.device_id == "test_ring"
        assert len(dev.channels) == 2

    def test_device_noise_defaults(self) -> None:
        dev = WearableDevice(device_id="x", channels=["heart_rate"])
        noise = dev.get_channel_noise("heart_rate")
        assert "sigma" in noise
        assert noise["sigma"] > 0

    def test_device_custom_noise(self) -> None:
        dev = WearableDevice(
            device_id="x",
            channels=["heart_rate"],
            noise={"heart_rate": {"sigma": 99.0, "drift_rate": 0.0, "dropout_prob": 0.0}},
        )
        assert dev.get_channel_noise("heart_rate")["sigma"] == 99.0

    def test_device_to_dict(self) -> None:
        dev = WearableDevice(device_id="ring", channels=["spo2", "hrv"])
        d = dev.to_dict()
        assert d["device_id"] == "ring"
        assert "spo2" in d["channels"]

    def test_build_from_config(self) -> None:
        cfg = {
            "device_id": "test_watch",
            "channels": ["heart_rate", "spo2"],
            "noise": [
                {"channel": "heart_rate", "sigma": 3.0, "drift_rate": 0.1, "dropout_prob": 0.01},
            ],
        }
        dev = build_wearable_device_from_config(cfg)
        assert dev.device_id == "test_watch"
        assert dev.get_channel_noise("heart_rate")["sigma"] == 3.0
        assert dev.channels == ["heart_rate", "spo2"]


class TestWearableMonitor:
    def test_monitor_from_config(self) -> None:
        cfg = load_config()
        rng = np.random.default_rng(42)
        monitor = build_wearable_monitor_from_config(cfg, rng, repo_root=REPO_ROOT)
        assert monitor is not None
        assert "oura_ring" in monitor.devices
        assert "apple_watch_s10" in monitor.devices

    def test_deployment_profile_crew_plus_byod(self) -> None:
        cfg = load_config()
        rng = np.random.default_rng(42)
        monitor = build_wearable_monitor_from_config(cfg, rng, repo_root=REPO_ROOT)
        assert monitor is not None
        crew_med = monitor.class_device_assignments.get("crew_medical", [])
        assert crew_med
        assert crew_med[0].device_id == "apple_watch_s10"

    def test_disabled_config(self) -> None:
        cfg = {"wearable_monitoring": {"enabled": False}}
        assert build_wearable_monitor_from_config(cfg) is None

    def test_absent_config(self) -> None:
        assert build_wearable_monitor_from_config({}) is None

    def test_initialize_agents(self) -> None:
        cfg = load_config()
        rng = np.random.default_rng(42)
        monitor = build_wearable_monitor_from_config(cfg, rng, repo_root=REPO_ROOT)
        assert monitor is not None
        engine = _build_test_engine()
        for agent in engine.agents:
            monitor.initialize_agent(agent)
        # crew_plus_byod: crew always monitored; passengers use probabilistic BYOD
        assert 0 < len(monitor.agent_states) < len(engine.agents)
        assert len(monitor.agent_states) == 13

    def test_agent_baselines_vary_by_class(self) -> None:
        cfg = load_config()
        rng = np.random.default_rng(42)
        monitor = build_wearable_monitor_from_config(cfg, rng, repo_root=REPO_ROOT)
        assert monitor is not None
        engine = _build_test_engine()
        for agent in engine.agents:
            monitor.initialize_agent(agent)

        baselines_by_class: dict[str, list[float]] = {}
        for states in monitor.agent_states.values():
            state = states[0]  # primary device
            hr = state.baselines.get("heart_rate", 0.0)
            cls = next(
                (a.agent_class for a in engine.agents if a.agent_id == state.agent_id),
                "unknown",
            )
            baselines_by_class.setdefault(cls, []).append(hr)
        assert len(baselines_by_class) > 1

    def test_generate_epoch_data(self) -> None:
        cfg = load_config()
        rng = np.random.default_rng(42)
        monitor = build_wearable_monitor_from_config(cfg, rng, repo_root=REPO_ROOT)
        assert monitor is not None
        engine = _build_test_engine()
        for agent in engine.agents:
            monitor.initialize_agent(agent)

        data = monitor.generate_epoch_data(engine.agents, {})
        assert len(data) == len(monitor.agent_states)
        for aid, epoch_data in data.items():
            assert "hourly" in epoch_data
            assert "summary" in epoch_data
            assert "device_id" in epoch_data
            assert "fever" in epoch_data
            assert "anomaly_count" in epoch_data
            for ch, readings in epoch_data["hourly"].items():
                assert len(readings) == 24

    def test_fleet_summary(self) -> None:
        cfg = load_config()
        rng = np.random.default_rng(42)
        monitor = build_wearable_monitor_from_config(cfg, rng, repo_root=REPO_ROOT)
        assert monitor is not None
        engine = _build_test_engine()
        for agent in engine.agents:
            monitor.initialize_agent(agent)

        summary = monitor.get_fleet_summary()
        assert summary["total_monitored"] == len(monitor.agent_states)
        assert "apple_watch_s10" in summary["devices"] or "garmin_venu3" in summary["devices"]

    def test_class_device_deployment(self) -> None:
        cfg = load_config()
        rng = np.random.default_rng(42)
        monitor = build_wearable_monitor_from_config(cfg, rng, repo_root=REPO_ROOT)
        assert monitor is not None
        engine = _build_test_engine()
        for agent in engine.agents:
            monitor.initialize_agent(agent)

        for agent in engine.agents:
            states = monitor.agent_states.get(agent.agent_id)
            if states is None:
                continue
            assert len(states) >= 1
            primary = states[0]
            if agent.agent_class == "crew_medical":
                assert primary.device.device_id == "apple_watch_s10"
            elif agent.agent_class in ("crew_engineering", "crew_general"):
                assert primary.device.device_id == "garmin_venu3"
            elif agent.agent_class == "crew_galley":
                assert primary.device.device_id == "apple_watch_s10"
        assert any(
            monitor.agent_states.get(a.agent_id) is not None
            for a in engine.agents
            if a.agent_class.startswith("crew_")
        )


class TestWearableDataStream:
    def test_query_ground_truth(self) -> None:
        rng = np.random.default_rng(42)
        modality = WearableDataStream(rng=rng)
        truth = {"epoch": 0, "agents": [], "spaces": {}}
        raw_data = {
            0: {
                "device_id": "oura_ring",
                "hourly": {"heart_rate": [70.0] * 24},
                "summary": {
                    "heart_rate": {
                        "mean": 70.0, "min": 65.0, "max": 75.0,
                        "readings_count": 24, "dropout_count": 0,
                        "z_score": 0.5, "anomaly": False,
                    },
                },
                "fever": False,
                "anomaly_channels": [],
                "anomaly_count": 0,
            },
        }
        result = modality.query_ground_truth(truth, raw_data)
        assert result["modality"] == "wearable"
        assert result["epoch"] == 0
        assert result["fleet_summary"]["total_monitored"] == 1
        assert 0 in result["agent_results"]

    def test_empty_wearable_data(self) -> None:
        modality = WearableDataStream()
        truth = {"epoch": 5}
        result = modality.query_ground_truth(truth, {})
        assert result["fleet_summary"]["total_monitored"] == 0
        assert result["fleet_summary"]["fever_count"] == 0


class TestWearableHelpers:
    def test_infection_phase_early(self) -> None:
        assert _get_infection_phase(0, DEFAULT_PHASE_BOUNDARIES) == "early"
        assert _get_infection_phase(2, DEFAULT_PHASE_BOUNDARIES) == "early"

    def test_infection_phase_peak(self) -> None:
        assert _get_infection_phase(3, DEFAULT_PHASE_BOUNDARIES) == "peak"
        assert _get_infection_phase(7, DEFAULT_PHASE_BOUNDARIES) == "peak"

    def test_infection_phase_late(self) -> None:
        assert _get_infection_phase(8, DEFAULT_PHASE_BOUNDARIES) == "late"
        assert _get_infection_phase(11, DEFAULT_PHASE_BOUNDARIES) == "late"

    def test_infection_phase_recovery(self) -> None:
        assert _get_infection_phase(12, DEFAULT_PHASE_BOUNDARIES) == "recovery"
        assert _get_infection_phase(20, DEFAULT_PHASE_BOUNDARIES) == "recovery"

    def test_clamp_heart_rate(self) -> None:
        assert _clamp_channel("heart_rate", 10.0) == 30.0
        assert _clamp_channel("heart_rate", 300.0) == 200.0
        assert _clamp_channel("heart_rate", 80.0) == 80.0

    def test_clamp_spo2(self) -> None:
        assert _clamp_channel("spo2", 50.0) == 70.0
        assert _clamp_channel("spo2", 105.0) == 100.0
        assert _clamp_channel("spo2", 97.0) == 97.0

    def test_clamp_body_temp(self) -> None:
        assert _clamp_channel("body_temp", 30.0) == 34.0
        assert _clamp_channel("body_temp", 45.0) == 42.0
