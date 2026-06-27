"""
test_protocol_engine.py – Unit tests for the reactive protocol engine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

from __future__ import annotations

import os
import sys
from typing import Any

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from crusher_labs.protocol_engine import (
    StandingProtocol,
    ProtocolEngine,
    compute_stoplights,
    compute_detection_escalation_stoplights,
    compute_wearable_stoplights,
    load_protocols,
    apply_hvac_modifiers,
    apply_transmission_modifiers,
    reset_modifiers,
    DETECTION_ESCALATION_INSTRUMENT,
)
from crusher_labs.cost_ledger import CostLedger


def _make_protocol(
    protocol_id: str = "SOP-TEST",
    name: str = "Test Protocol",
    instrument_class: str = "continuous_air_sampler",
    stoplight_level: str = "RED",
    min_zones_affected: int = 1,
    modifiers: dict | None = None,
) -> StandingProtocol:
    return StandingProtocol({
        "protocol_id": protocol_id,
        "name": name,
        "trigger": {
            "instrument_class": instrument_class,
            "stoplight_level": stoplight_level,
            "min_zones_affected": min_zones_affected,
        },
        "modifiers": modifiers or {},
        "costs_per_epoch": {},
        "activation_costs": {},
    })


class TestStandingProtocol:
    def test_is_triggered_when_matching(self) -> None:
        proto = _make_protocol(stoplight_level="RED")
        stoplights = {"continuous_air_sampler": {"Bridge": "RED"}}
        assert proto.is_triggered(stoplights) is True

    def test_not_triggered_when_below_level(self) -> None:
        proto = _make_protocol(stoplight_level="RED")
        stoplights = {"continuous_air_sampler": {"Bridge": "AMBER"}}
        assert proto.is_triggered(stoplights) is False

    def test_not_triggered_when_wrong_instrument(self) -> None:
        proto = _make_protocol(instrument_class="targeted_surface_swab")
        stoplights = {"continuous_air_sampler": {"Bridge": "RED"}}
        assert proto.is_triggered(stoplights) is False

    def test_not_triggered_when_empty_stoplights(self) -> None:
        proto = _make_protocol()
        assert proto.is_triggered({}) is False

    def test_min_zones_required(self) -> None:
        proto = _make_protocol(min_zones_affected=2)
        one_zone = {"continuous_air_sampler": {"Bridge": "RED"}}
        assert proto.is_triggered(one_zone) is False
        two_zones = {"continuous_air_sampler": {"Bridge": "RED", "MedBay": "RED"}}
        assert proto.is_triggered(two_zones) is True

    def test_amber_meets_amber_trigger(self) -> None:
        proto = _make_protocol(stoplight_level="AMBER")
        stoplights = {"continuous_air_sampler": {"Bridge": "AMBER"}}
        assert proto.is_triggered(stoplights) is True

    def test_red_meets_amber_trigger(self) -> None:
        proto = _make_protocol(stoplight_level="AMBER")
        stoplights = {"continuous_air_sampler": {"Bridge": "RED"}}
        assert proto.is_triggered(stoplights) is True


class TestProtocolEngine:
    def test_activation_and_deactivation(self) -> None:
        proto = _make_protocol(modifiers={"hvac_filter_efficiency_override": 0.95})
        ledger = CostLedger()
        engine = ProtocolEngine([proto], ledger)

        stoplights_on = {"continuous_air_sampler": {"Bridge": "RED"}}
        active = engine.evaluate_epoch(0, stoplights_on)
        assert len(active) == 1
        assert active[0]["newly_activated"] is True

        stoplights_off = {"continuous_air_sampler": {"Bridge": "GREEN"}}
        active = engine.evaluate_epoch(1, stoplights_off)
        assert len(active) == 0

    def test_stays_active(self) -> None:
        proto = _make_protocol()
        ledger = CostLedger()
        engine = ProtocolEngine([proto], ledger)

        stoplights = {"continuous_air_sampler": {"Bridge": "RED"}}
        engine.evaluate_epoch(0, stoplights)
        active = engine.evaluate_epoch(1, stoplights)
        assert len(active) == 1
        assert active[0]["newly_activated"] is False

    def test_get_active_protocols(self) -> None:
        proto = _make_protocol()
        ledger = CostLedger()
        engine = ProtocolEngine([proto], ledger)

        stoplights = {"continuous_air_sampler": {"Bridge": "RED"}}
        engine.evaluate_epoch(0, stoplights)
        assert "SOP-TEST" in engine.get_active_protocols()

    def test_merged_modifiers_scalar(self) -> None:
        p1 = _make_protocol("SOP-1", modifiers={"hvac_filter_efficiency_override": 0.90})
        p2 = _make_protocol(
            "SOP-2", modifiers={"hvac_filter_efficiency_override": 0.95},
            instrument_class="continuous_air_sampler",
        )
        ledger = CostLedger()
        engine = ProtocolEngine([p1, p2], ledger)
        stoplights = {"continuous_air_sampler": {"Bridge": "RED"}}
        active = engine.evaluate_epoch(0, stoplights)
        merged = engine.get_merged_modifiers(active)
        assert merged["hvac_filter_efficiency_override"] == pytest.approx(0.95)

    def test_merged_modifiers_list_union(self) -> None:
        p1 = _make_protocol("SOP-1", modifiers={"close_zones": ["Bridge"]})
        p2 = _make_protocol("SOP-2", modifiers={"close_zones": ["MedBay"]})
        ledger = CostLedger()
        engine = ProtocolEngine([p1, p2], ledger)
        stoplights = {"continuous_air_sampler": {"Bridge": "RED"}}
        active = engine.evaluate_epoch(0, stoplights)
        merged = engine.get_merged_modifiers(active)
        assert "Bridge" in merged["close_zones"]
        assert "MedBay" in merged["close_zones"]

    def test_generate_protocol_summary(self) -> None:
        proto = _make_protocol()
        ledger = CostLedger()
        engine = ProtocolEngine([proto], ledger)
        stoplights_on = {"continuous_air_sampler": {"Bridge": "RED"}}
        engine.evaluate_epoch(0, stoplights_on)
        summary = engine.generate_protocol_summary()
        assert summary["total_activations"] == 1

    def test_forced_protocol_without_stoplight(self) -> None:
        proto = _make_protocol("SOP-FORCED")
        ledger = CostLedger()
        engine = ProtocolEngine([proto], ledger)
        stoplights_off: dict = {"continuous_air_sampler": {}}
        active = engine.evaluate_epoch(
            0, stoplights_off, forced_protocol_ids={"SOP-FORCED"},
        )
        assert len(active) == 1
        assert active[0]["protocol_id"] == "SOP-FORCED"
        assert "SOP-FORCED" in engine.get_active_protocols()


class TestComputeStoplights:
    def test_air_results_to_stoplights(self) -> None:
        air = {"Bridge": {"ct_value": 28.0, "detected": True}}
        lights = compute_stoplights(air, {}, {}, {}, {}, {})
        assert lights["continuous_air_sampler"]["Bridge"] == "RED"

    def test_clinical_rdt_to_stoplights(self) -> None:
        rdt = {0: {"positive": True}}
        lights = compute_stoplights({}, {}, {}, rdt, {}, {})
        assert lights["clinical_rdt"]["0"] == "RED"

    def test_wastewater_anomaly_to_stoplights(self) -> None:
        ww = {"Engine_Room": {"anomaly_score": 0.5}}
        lights = compute_stoplights({}, {}, ww, {}, {}, {})
        assert lights["wastewater_sequencing_grid"]["Engine_Room"] == "AMBER"

    def test_all_green_when_empty(self) -> None:
        lights = compute_stoplights({}, {}, {}, {}, {}, {})
        for instrument, zones in lights.items():
            for zone, level in zones.items():
                assert level == "GREEN"

    def test_wearable_agent_stoplights(self) -> None:
        wearable = {
            "agent_results": {
                1: {"fever": True, "anomaly_count": 0},
                2: {"fever": False, "anomaly_count": 0},
            },
            "fleet_summary": {
                "fever_rate": 0.5,
                "anomaly_rate": 0.0,
            },
        }
        lights = compute_stoplights({}, {}, {}, {}, {}, {}, wearable_result=wearable)
        assert lights["wearable_physiological_monitor"]["1"] == "RED"
        assert lights["wearable_physiological_monitor"]["2"] == "GREEN"
        assert lights["wearable_fleet_monitor"]["fleet"] == "RED"

    def test_detection_escalation_integrates_modes(self) -> None:
        base = {
            "continuous_air_sampler": {"Z1": "RED"},
            "clinical_rdt": {},
        }
        syndromic = {"sick_call_count": 6}
        modes = compute_detection_escalation_stoplights(base, syndromic, None)
        assert modes["syndromic"] == "RED"
        assert modes["environmental"] == "RED"
        assert modes["clinical"] == "GREEN"


class TestDetectionEscalationProtocol:
    def _make_escalation_protocol(self, level: str = "AMBER", min_modes: int = 2) -> StandingProtocol:
        return StandingProtocol({
            "protocol_id": "SOP-ESC",
            "name": "Escalation Test",
            "trigger": {
                "instrument_class": DETECTION_ESCALATION_INSTRUMENT,
                "stoplight_level": level,
                "min_modes_affected": min_modes,
            },
            "modifiers": {},
            "costs_per_epoch": {},
            "activation_costs": {},
        })

    def test_triggers_when_min_modes_met(self) -> None:
        proto = self._make_escalation_protocol()
        stoplights = {
            DETECTION_ESCALATION_INSTRUMENT: {
                "syndromic": "AMBER",
                "wearable_individual": "GREEN",
                "wearable_fleet": "AMBER",
                "environmental": "GREEN",
                "clinical": "GREEN",
            },
        }
        assert proto.is_triggered(stoplights) is True

    def test_not_triggered_when_one_mode(self) -> None:
        proto = self._make_escalation_protocol()
        stoplights = {
            DETECTION_ESCALATION_INSTRUMENT: {
                "syndromic": "RED",
                "wearable_individual": "GREEN",
                "wearable_fleet": "GREEN",
                "environmental": "GREEN",
                "clinical": "GREEN",
            },
        }
        assert proto.is_triggered(stoplights) is False


class TestWearableStoplightsHelper:
    def test_compute_wearable_stoplights_empty(self) -> None:
        agents, fleet = compute_wearable_stoplights(None)
        assert agents == {}
        assert fleet == {}


class TestModifierHelpers:
    def test_apply_hvac_modifiers(self) -> None:
        mock_engine = type("E", (), {"filter_efficiency": 0.50})()
        apply_hvac_modifiers(mock_engine, {"hvac_filter_efficiency_override": 0.95})
        assert mock_engine.filter_efficiency == pytest.approx(0.95)

    def test_apply_hvac_none_engine(self) -> None:
        apply_hvac_modifiers(None, {"hvac_filter_efficiency_override": 0.95})

    def test_apply_transmission_modifiers(self) -> None:
        mock_core = type("TC", (), {
            "direct_contact_scalar": 1.0,
            "droplet_scalar": 1.0,
            "hvac_airborne_scalar": 1.0,
            "fomite_scalar": 1.0,
        })()
        mods = {"direct_contact_scalar": 0.5, "fomite_scalar": 0.3}
        apply_transmission_modifiers(mock_core, mods)
        assert mock_core.direct_contact_scalar == pytest.approx(0.5)
        assert mock_core.fomite_scalar == pytest.approx(0.3)
        assert mock_core.droplet_scalar == pytest.approx(1.0)

    def test_reset_modifiers(self) -> None:
        mock_engine = type("E", (), {"filter_efficiency": 0.95})()
        mock_core = type("TC", (), {
            "direct_contact_scalar": 0.5,
            "droplet_scalar": 0.5,
            "hvac_airborne_scalar": 0.5,
            "fomite_scalar": 0.5,
        })()
        reset_modifiers(mock_engine, mock_core, 0.50)
        assert mock_engine.filter_efficiency == pytest.approx(0.50)
        assert mock_core.direct_contact_scalar == pytest.approx(1.0)
        assert mock_core.fomite_scalar == pytest.approx(1.0)


class TestLoadProtocols:
    def test_loads_default_protocols(self) -> None:
        path = os.path.join(REPO_ROOT, "data", "config", "protocols.json")
        protocols = load_protocols(path)
        assert len(protocols) >= 1
        for p in protocols:
            assert hasattr(p, "protocol_id")
            assert hasattr(p, "trigger")
