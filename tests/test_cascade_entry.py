"""Tests for cascade entry routing and wearable fusion."""

from __future__ import annotations

import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from crusher_labs.cascade_entry import (
    CascadeEntryConfig,
    WearableAlertFusionConfig,
    WearableDeviceFusionConfig,
    evaluate_wearable_alert,
    fuse_device_results,
)
from crusher_labs.diagnostic_cascade import DiagnosticCascadeEngine, DiagnosticTier


def _default_tiers() -> list[DiagnosticTier]:
    return [
        DiagnosticTier(
            tier_id=0, name="Triage", tests=[],
            sensitivity=0.7, specificity=0.6,
            cost_per_agent={}, tat_epochs=0,
            regret_level="low",
            actions_on_positive=["advance_to_tier_1"],
            confinement_on_positive=False, sop_gate=None,
            implicit_positive=False,
        ),
        DiagnosticTier(
            tier_id=1, name="RDT Screen", tests=["clinical_rdt"],
            sensitivity=0.8, specificity=0.97,
            cost_per_agent={"financial_usd": 12},
            tat_epochs=0, regret_level="low",
            actions_on_positive=["advance_to_tier_2"],
            confinement_on_positive=False,
            sop_gate=["SOP-006"],
        ),
    ]


def test_sick_call_enters_tier1_wearable_enters_tier0() -> None:
    engine = DiagnosticCascadeEngine(_default_tiers())
    agent = {
        "agent_id": 1,
        "infection_state": "susceptible",
        "symptom_presentation": "asymptomatic",
        "compliance_status": "compliant",
        "shedding_rate": 0.0,
        "location": "MedBay",
        "microflora_disruption": 0.0,
        "agent_class": "crew_general",
    }

    sick_result = engine.evaluate_epoch(
        epoch=0,
        sick_call_ids=[1],
        wearable_red_ids=[],
        agents=[agent],
        test_runner=None,
    )
    assert sick_result.new_tier1_agents == [1]
    assert sick_result.new_tier0_agents == []
    assert engine.agent_states[1].current_tier == 1

    engine2 = DiagnosticCascadeEngine(_default_tiers())
    wearable_result = engine2.evaluate_epoch(
        epoch=0,
        sick_call_ids=[],
        wearable_red_ids=[2],
        agents=[{**agent, "agent_id": 2}],
        test_runner=None,
    )
    assert wearable_result.new_tier0_agents == [2]
    assert engine2.agent_states[2].current_tier == 0


def test_wearable_skipped_when_agent_already_at_sick_call_tier() -> None:
    engine = DiagnosticCascadeEngine(_default_tiers())
    agent = {
        "agent_id": 3,
        "infection_state": "susceptible",
        "symptom_presentation": "asymptomatic",
        "compliance_status": "compliant",
        "shedding_rate": 0.0,
        "location": "MedBay",
        "microflora_disruption": 0.0,
        "agent_class": "crew_general",
    }
    engine.evaluate_epoch(
        epoch=0, sick_call_ids=[3], wearable_red_ids=[], agents=[agent], test_runner=None,
    )
    result = engine.evaluate_epoch(
        epoch=1, sick_call_ids=[], wearable_red_ids=[3], agents=[agent], test_runner=None,
    )
    assert result.new_tier0_agents == []
    assert engine.agent_states[3].current_tier == 1


def test_evaluate_wearable_alert_default_rules() -> None:
    fusion = WearableAlertFusionConfig()
    assert evaluate_wearable_alert({"fever": True, "anomaly_count": 0}, fusion)
    assert evaluate_wearable_alert({"fever": False, "anomaly_count": 2}, fusion)
    assert not evaluate_wearable_alert({"fever": False, "anomaly_count": 1}, fusion)


def test_evaluate_wearable_alert_and_operator() -> None:
    fusion = WearableAlertFusionConfig(
        operator="and",
        rules=(
            {"signal": "fever", "equals": True},
            {"signal": "anomaly_count", "operator": ">=", "value": 2},
        ),
    )
    assert evaluate_wearable_alert({"fever": True, "anomaly_count": 2}, fusion)
    assert not evaluate_wearable_alert({"fever": True, "anomaly_count": 1}, fusion)


def test_fuse_device_results_intersection() -> None:
    fusion = WearableDeviceFusionConfig(fever="all", anomaly_channels="intersection")
    devices = [
        {"fever": True, "anomaly_channels": ["heart_rate", "hrv"], "device_id": "a"},
        {"fever": True, "anomaly_channels": ["heart_rate"], "device_id": "b"},
    ]
    fused = fuse_device_results(devices, fusion)
    assert fused["fever"] is True
    assert fused["anomaly_channels"] == ["heart_rate"]
    assert fused["anomaly_count"] == 1


def test_cascade_entry_config_runtime_override() -> None:
    cfg = CascadeEntryConfig.from_config(
        cascade_json={
            "cascade_entry": {
                "sick_call_tier": 1,
                "wearable_alert_fusion": {
                    "operator": "and",
                    "rules": [{"signal": "fever", "equals": True}],
                },
            },
        },
        runtime_cfg={
            "entry": {
                "wearable_alert_fusion": {
                    "operator": "or",
                    "rules": [{"signal": "anomaly_count", "operator": ">=", "value": 3}],
                },
            },
        },
    )
    assert cfg.sick_call_tier == 1
    assert cfg.wearable_alert_fusion.operator == "or"
    assert cfg.wearable_alert_fusion.rules[0]["value"] == 3
