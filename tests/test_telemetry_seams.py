"""
test_telemetry_seams.py – Verify data integrity at module boundaries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tests that data passes correctly between the segregated orchestrator
modules: types are preserved, no implicit casts, no dropped fields,
and VSP isolation state stays synchronized.
"""

from __future__ import annotations

import os
import sys
from typing import Any
from unittest.mock import MagicMock

import pytest
import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from orchestrator_types import (
    STATUS_BASELINE,
    STATUS_SUSPECTED,
    STATUS_CONFIRMED,
    COMPLIANCE_NON_COMPLIANT,
    INFECTION_SUSCEPTIBLE,
    INFECTION_INFECTED,
    PRESENTATION_SYMPTOMATIC,
    SYMPTOM_ASYMPTOMATIC,
    SYMPTOM_SYMPTOMATIC,
    LOCATION_ISOLATED,
    SimulationState,
)
from orchestrator_init import (
    engine_payload_to_schema,
    build_engine,
    check_escalation,
)
from orchestrator_epoch import (
    sync_vsp_isolation,
    step_quarantine_confinement,
    confine_agents,
    compute_zone_microflora_shifts,
    run_observation_sampling,
)
from orchestrator_record import record_epoch
from engines.infection_dynamics_bridge import (
    KorkinShipEngine,
    InfectionStatus,
    IllnessStatus,
)
from crusher_labs import load_config


# ── VSP sync tests ───────────────────────────────────────────────────────

class TestSyncVspIsolation:
    """Verify the engine → SimulationState VSP isolation sync."""

    def _build_engine_with_vsp(self) -> KorkinShipEngine:
        cfg = load_config()
        engine = build_engine(cfg, seed=42)
        return engine

    def test_vsp_ids_flow_back_to_state(self) -> None:
        engine = self._build_engine_with_vsp()
        state = SimulationState()
        engine.quarantined_ids = {3, 7}
        sync_vsp_isolation(epoch=5, engine=engine, state=state)
        assert 3 in state.quarantined_ids
        assert 7 in state.quarantined_ids

    def test_no_duplicates_on_repeated_sync(self) -> None:
        engine = self._build_engine_with_vsp()
        state = SimulationState()
        state.quarantined_ids = {3}
        engine.quarantined_ids = {3, 7}
        sync_vsp_isolation(epoch=5, engine=engine, state=state)
        assert state.quarantined_ids == {3, 7}
        vsp_entries = [c for c in state.compliance_log if c["action"] == "vsp_quarantine"]
        assert len(vsp_entries) == 1
        assert vsp_entries[0]["agent_id"] == 7

    def test_noop_when_no_new_vsp(self) -> None:
        engine = self._build_engine_with_vsp()
        state = SimulationState()
        state.quarantined_ids = {3, 7}
        engine.quarantined_ids = {3, 7}
        sync_vsp_isolation(epoch=5, engine=engine, state=state)
        assert len(state.compliance_log) == 0

    def test_compliance_log_records_epoch(self) -> None:
        engine = self._build_engine_with_vsp()
        state = SimulationState()
        engine.quarantined_ids = {2}
        sync_vsp_isolation(epoch=10, engine=engine, state=state)
        assert state.compliance_log[0]["epoch"] == 10
        assert state.compliance_log[0]["action"] == "vsp_quarantine"
        assert state.compliance_log[0]["agent_id"] == 2


# ── engine_payload_to_schema boundary tests ──────────────────────────────

class TestEnginePayloadBoundary:
    """Type guards and coercion at the engine → schema boundary."""

    def test_missing_agents_raises(self) -> None:
        with pytest.raises(ValueError, match="missing 'agents'"):
            engine_payload_to_schema({"spaces": {}}, set(), set(), set())

    def test_missing_spaces_raises(self) -> None:
        with pytest.raises(ValueError, match="missing 'spaces'"):
            engine_payload_to_schema({"agents": []}, set(), set(), set())

    def test_shedding_rate_always_float(self) -> None:
        payload = {
            "agents": [
                {"agent_id": 0, "symptom_status": SYMPTOM_ASYMPTOMATIC,
                 "shedding_rate": 5, "location": "Bridge"},
            ],
            "spaces": {"Bridge": {"pathogen_mass": 10}},
        }
        agents, spaces = engine_payload_to_schema(payload, set(), set(), set())
        assert isinstance(agents[0]["shedding_rate"], float)
        assert isinstance(spaces["Bridge"]["pathogen_mass"], float)

    def test_shedding_rate_zero_for_isolated(self) -> None:
        payload = {
            "agents": [
                {"agent_id": 1, "symptom_status": SYMPTOM_SYMPTOMATIC,
                 "shedding_rate": 999.0, "location": "MedBay"},
            ],
            "spaces": {},
        }
        agents, _ = engine_payload_to_schema(payload, {1}, set(), set())
        assert agents[0]["shedding_rate"] == pytest.approx(0.0)
        assert agents[0]["location"] == LOCATION_ISOLATED

    def test_pathogen_mass_coerced_to_float(self) -> None:
        payload = {
            "agents": [],
            "spaces": {"Bridge": {"pathogen_mass": 42}},
        }
        _, spaces = engine_payload_to_schema(payload, set(), set(), set())
        assert isinstance(spaces["Bridge"]["pathogen_mass"], float)

    def test_pathogen_mass_by_id_preserved(self) -> None:
        payload = {
            "agents": [],
            "spaces": {
                "Bridge": {
                    "pathogen_mass": 10.0,
                    "pathogen_mass_by_id": {"noro": 6.0, "sars": 4.0},
                },
            },
        }
        _, spaces = engine_payload_to_schema(payload, set(), set(), set())
        assert spaces["Bridge"]["pathogen_mass_by_id"]["noro"] == pytest.approx(6.0)
        assert spaces["Bridge"]["pathogen_mass_by_id"]["sars"] == pytest.approx(4.0)

    def test_non_compliant_preserves_shedding(self) -> None:
        payload = {
            "agents": [
                {"agent_id": 3, "symptom_status": SYMPTOM_SYMPTOMATIC,
                 "shedding_rate": 42.5, "location": "Galley"},
            ],
            "spaces": {},
        }
        agents, _ = engine_payload_to_schema(payload, set(), set(), {3})
        assert agents[0]["compliance_status"] == COMPLIANCE_NON_COMPLIANT
        assert agents[0]["infection_state"] == INFECTION_INFECTED
        assert agents[0]["shedding_rate"] == pytest.approx(42.5)

    def test_microflora_disruption_field_preserved(self) -> None:
        payload = {
            "agents": [
                {"agent_id": 0, "symptom_status": SYMPTOM_ASYMPTOMATIC,
                 "microflora_disruption": 0.75},
            ],
            "spaces": {},
        }
        agents, _ = engine_payload_to_schema(payload, set(), set(), set())
        assert agents[0]["microflora_disruption"] == pytest.approx(0.75)


# ── record_epoch boundary guards ────────────────────────────────────────

class TestRecordEpochBoundary:
    """Type guards in record_epoch reject malformed inputs."""

    def test_agents_must_be_list(self) -> None:
        kwargs: dict[str, Any] = {
            "epoch": 0,
            "trigger_status": STATUS_BASELINE,
            "agents": "not_a_list",
            "spaces": {},
            "engine": MagicMock(),
            "contam_engine": None,
            "pathogen_profiles": {},
            "zone_names": [],
            "zone_microflora_shifts": {},
            "syn_result": {"sick_call_count": 0},
            "rdt_result": {"results": [], "tested_count": 0},
            "pcr_result": None,
            "seq_result": None,
            "tracing_matrix": MagicMock(to_dict=lambda: {}),
            "state": SimulationState(),
            "obs": MagicMock(fidelity_name="HIGH"),
            "active_mods": [],
            "merged_mods": {},
            "stoplights": {},
            "epoch_cost": {},
            "cfg": {},
            "air_results": {},
            "swab_results": {},
            "ww_results": {},
            "clin_rdt_results": {},
            "clin_qpcr_results": {},
            "clin_microbio_results": {},
        }
        with pytest.raises(TypeError, match="agents must be list"):
            record_epoch(**kwargs)

    def test_spaces_must_be_dict(self) -> None:
        kwargs: dict[str, Any] = {
            "epoch": 0,
            "trigger_status": STATUS_BASELINE,
            "agents": [],
            "spaces": [],
            "engine": MagicMock(),
            "contam_engine": None,
            "pathogen_profiles": {},
            "zone_names": [],
            "zone_microflora_shifts": {},
            "syn_result": {"sick_call_count": 0},
            "rdt_result": {"results": [], "tested_count": 0},
            "pcr_result": None,
            "seq_result": None,
            "tracing_matrix": MagicMock(to_dict=lambda: {}),
            "state": SimulationState(),
            "obs": MagicMock(fidelity_name="HIGH"),
            "active_mods": [],
            "merged_mods": {},
            "stoplights": {},
            "epoch_cost": {},
            "cfg": {},
            "air_results": {},
            "swab_results": {},
            "ww_results": {},
            "clin_rdt_results": {},
            "clin_qpcr_results": {},
            "clin_microbio_results": {},
        }
        with pytest.raises(TypeError, match="spaces must be dict"):
            record_epoch(**kwargs)

    def test_stoplights_must_be_dict(self) -> None:
        kwargs: dict[str, Any] = {
            "epoch": 0,
            "trigger_status": STATUS_BASELINE,
            "agents": [],
            "spaces": {},
            "engine": MagicMock(),
            "contam_engine": None,
            "pathogen_profiles": {},
            "zone_names": [],
            "zone_microflora_shifts": {},
            "syn_result": {"sick_call_count": 0},
            "rdt_result": {"results": [], "tested_count": 0},
            "pcr_result": None,
            "seq_result": None,
            "tracing_matrix": MagicMock(to_dict=lambda: {}),
            "state": SimulationState(),
            "obs": MagicMock(fidelity_name="HIGH"),
            "active_mods": [],
            "merged_mods": {},
            "stoplights": "not_a_dict",
            "epoch_cost": {},
            "cfg": {},
            "air_results": {},
            "swab_results": {},
            "ww_results": {},
            "clin_rdt_results": {},
            "clin_qpcr_results": {},
            "clin_microbio_results": {},
        }
        with pytest.raises(TypeError, match="stoplights must be dict"):
            record_epoch(**kwargs)

    def test_compact_omits_heavy_keys(self) -> None:
        engine = MagicMock()
        engine.agents = []
        kwargs: dict[str, Any] = {
            "epoch": 0,
            "trigger_status": STATUS_BASELINE,
            "agents": [
                {
                    "agent_id": 1,
                    "infection_state": "susceptible",
                    "symptom_presentation": "none",
                    "compliance_status": "compliant",
                    "shedding_rate": 0.0,
                    "location": "Bridge",
                    "agent_class": "crew",
                    "gender": "female",
                },
            ],
            "spaces": {"Bridge": {"pathogen_mass": 1.5}},
            "engine": engine,
            "contam_engine": None,
            "pathogen_profiles": {},
            "zone_names": ["Bridge"],
            "zone_microflora_shifts": {},
            "syn_result": {"sick_call_count": 0},
            "rdt_result": {"results": [], "tested_count": 0},
            "pcr_result": None,
            "seq_result": None,
            "tracing_matrix": MagicMock(to_dict=lambda: {"shared_room_exposures": [{"x": 1}]}),
            "state": SimulationState(),
            "obs": MagicMock(fidelity_name="HIGH"),
            "active_mods": [],
            "merged_mods": {"foo": 1},
            "stoplights": {"air": {"Bridge": "GREEN"}},
            "epoch_cost": {"total_financial_usd": 0.0},
            "cfg": {},
            "air_results": {"Bridge": {"ct": 40}},
            "swab_results": {},
            "ww_results": {},
            "clin_rdt_results": {},
            "clin_qpcr_results": {},
            "clin_microbio_results": {},
            "history_retention": "compact",
        }
        rec = record_epoch(**kwargs)
        assert "agents" not in rec
        assert "contact_tracing" not in rec
        assert "observation_engine" not in rec
        assert "summary" in rec
        assert "spaces" in rec
        assert "cost_accounting" in rec
        assert rec["spaces"]["Bridge"]["pathogen_mass"] == 1.5
        # Compact still supports campaign timeseries extraction.
        from picard_framework.runs.mega_cruise_campaign.campaign_runner import (
            extract_timeseries,
        )
        ts = extract_timeseries([rec])
        assert len(ts) == 1
        assert ts[0]["infected"] == rec["summary"]["infected"]


# ── Cross-module data flow tests ────────────────────────────────────────

class TestCrossModuleDataFlow:
    """Ensure data flows cleanly through the full init→schema pipeline."""

    def test_engine_export_matches_schema_expectations(self) -> None:
        cfg = load_config()
        engine = build_engine(cfg, seed=42)
        engine.enable_external_transmission()
        engine.enable_external_transport()
        engine.step()
        payload = engine._export_payload()

        assert "agents" in payload
        assert "spaces" in payload
        assert isinstance(payload["agents"], list)
        assert isinstance(payload["spaces"], dict)

        for a in payload["agents"]:
            assert "agent_id" in a
            assert "infection_state" in a
            assert "symptom_presentation" in a
            assert "compliance_status" in a
            assert isinstance(a["shedding_rate"], (int, float))

        for zname, zdata in payload["spaces"].items():
            assert isinstance(zname, str)
            assert "pathogen_mass" in zdata
            assert isinstance(zdata["pathogen_mass"], (int, float))

    def test_schema_conversion_round_trip(self) -> None:
        cfg = load_config()
        engine = build_engine(cfg, seed=42)
        engine.enable_external_transmission()
        engine.enable_external_transport()
        engine.step()
        payload = engine._export_payload()

        agents, spaces = engine_payload_to_schema(payload, set(), set(), set())

        assert len(agents) == len(payload["agents"])
        assert set(spaces.keys()) == set(payload["spaces"].keys())

        for a in agents:
            assert isinstance(a["shedding_rate"], float)

        for zdata in spaces.values():
            assert isinstance(zdata["pathogen_mass"], float)

    def test_escalation_status_type_consistency(self) -> None:
        cfg = load_config()
        for status in (STATUS_BASELINE, STATUS_SUSPECTED, STATUS_CONFIRMED):
            assert isinstance(status, str)

        result = check_escalation(
            STATUS_BASELINE,
            {"sick_call_count": 10},
            None,
            cfg,
        )
        assert isinstance(result, str)
        assert result in (STATUS_BASELINE, STATUS_SUSPECTED, STATUS_CONFIRMED)


# ── Microflora disruption boundary tests ────────────────────────────────

class TestMicrofloraDisruptionBoundary:
    """Ensure compute_zone_microflora_shifts handles edge cases."""

    def _make_agent(self, disruption: float = 0.0, location: str = "Bridge",
                    active_ids: list[str] | None = None) -> MagicMock:
        mock = MagicMock()
        mock.microflora_disruption_status = disruption
        mock.current_location = location
        mock.active_pathogen_ids = active_ids or []
        return mock

    def test_no_agents_returns_empty(self) -> None:
        result = compute_zone_microflora_shifts([], {}, {})
        assert result == {}

    def test_zero_disruption_excluded(self) -> None:
        agent = self._make_agent(disruption=0.0, active_ids=["noro"])
        result = compute_zone_microflora_shifts([agent], {"noro": {}}, {})
        assert result == {}

    def test_isolated_agents_excluded(self) -> None:
        agent = self._make_agent(
            disruption=0.5, location="Isolated_In_Quarters",
            active_ids=["noro"],
        )
        profiles = {"noro": {"microflora_disruption": {
            "causes_disruption": True, "disruption_type": "gastrointestinal",
        }}}
        result = compute_zone_microflora_shifts([agent], profiles, {})
        assert result == {}

    def test_disruption_accumulates_per_zone(self) -> None:
        a1 = self._make_agent(disruption=0.8, location="MedBay", active_ids=["noro"])
        a2 = self._make_agent(disruption=0.6, location="MedBay", active_ids=["noro"])
        profiles = {"noro": {"microflora_disruption": {
            "causes_disruption": True,
            "disruption_type": "gastrointestinal",
            "disruption_magnitude": 0.8,
        }}}
        cfg = {"microflora": {"disrupted_shed_mass": 100.0}}
        result = compute_zone_microflora_shifts([a1, a2], profiles, cfg)
        assert "MedBay" in result
        assert result["MedBay"]["gastrointestinal"] > 0
