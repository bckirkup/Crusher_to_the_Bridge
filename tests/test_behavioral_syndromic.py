"""Tests for Layer-1 syndromic behavioral overrides."""

from __future__ import annotations

import os
import sys

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from crusher_labs.modalities.syndromic import SyndromicSurveillance
from telemetry_buffer.agent_axes import (
    COMPLIANCE_COMPLIANT,
    INFECTION_INFECTED,
    PRESENTATION_SYMPTOMATIC,
)


class TestBehavioralSyndromic:
    def test_hide_symptoms_suppresses_sick_call(self) -> None:
        syn = SyndromicSurveillance(sick_call_probability=1.0, rng=np.random.default_rng(0))
        truth = {
            "epoch": 1,
            "agents": [{
                "agent_id": 1,
                "infection_state": INFECTION_INFECTED,
                "symptom_presentation": PRESENTATION_SYMPTOMATIC,
                "compliance_status": COMPLIANCE_COMPLIANT,
            }],
        }
        result = syn.query_ground_truth(truth, behavioral_overrides={1: "hide_symptoms"})
        assert result["sick_call_agents"] == []

    def test_report_sick_call_forces_report(self) -> None:
        syn = SyndromicSurveillance(sick_call_probability=0.0, rng=np.random.default_rng(0))
        truth = {
            "epoch": 1,
            "agents": [{
                "agent_id": 2,
                "infection_state": INFECTION_INFECTED,
                "symptom_presentation": PRESENTATION_SYMPTOMATIC,
                "compliance_status": COMPLIANCE_COMPLIANT,
            }],
        }
        result = syn.query_ground_truth(truth, behavioral_overrides={2: "report_sick_call"})
        assert 2 in result["sick_call_agents"]

    def test_belief_scaled_probability(self) -> None:
        low = SyndromicSurveillance.effective_sick_call_probability(
            0.7, severity_belief=0.1, trust_medical=0.2,
        )
        high = SyndromicSurveillance.effective_sick_call_probability(
            0.7, severity_belief=0.9, trust_medical=0.9,
        )
        assert high > low

    def test_zero_background_noise_rate_suppresses_healthy_noise(self) -> None:
        """Config sensitivity: background_noise_rate=0 must silence noise categories."""
        from telemetry_buffer.agent_axes import (
            INFECTION_SUSCEPTIBLE,
            PRESENTATION_ASYMPTOMATIC,
        )

        categories = [
            {"reason": "seasickness", "probability": 1.0},
        ]
        truth = {
            "epoch": 1,
            "agents": [{
                "agent_id": 10,
                "infection_state": INFECTION_SUSCEPTIBLE,
                "symptom_presentation": PRESENTATION_ASYMPTOMATIC,
                "compliance_status": COMPLIANCE_COMPLIANT,
            }],
        }
        noisy = SyndromicSurveillance(
            sick_call_probability=0.0,
            background_noise_rate=0.015,
            noise_categories=categories,
            rng=np.random.default_rng(0),
        )
        silent = SyndromicSurveillance(
            sick_call_probability=0.0,
            background_noise_rate=0.0,
            noise_categories=categories,
            rng=np.random.default_rng(0),
        )
        assert 10 in noisy.query_ground_truth(truth)["sick_call_agents"]
        assert silent.query_ground_truth(truth)["sick_call_agents"] == []
        assert silent.query_ground_truth(truth)["noise_ids"] == []

    def test_empty_noise_categories_disables_background_noise(self) -> None:
        """Explicit [] must not fall back to built-in category defaults."""
        from telemetry_buffer.agent_axes import (
            INFECTION_SUSCEPTIBLE,
            PRESENTATION_ASYMPTOMATIC,
        )

        truth = {
            "epoch": 1,
            "agents": [{
                "agent_id": 11,
                "infection_state": INFECTION_SUSCEPTIBLE,
                "symptom_presentation": PRESENTATION_ASYMPTOMATIC,
                "compliance_status": COMPLIANCE_COMPLIANT,
            }],
        }
        syn = SyndromicSurveillance(
            sick_call_probability=0.0,
            background_noise_rate=1.0,
            noise_categories=[],
            rng=np.random.default_rng(0),
        )
        result = syn.query_ground_truth(truth)
        assert result["sick_call_agents"] == []
        assert syn.noise_categories == []

    def test_none_surveillance_overrides_yield_zero_sick_calls(self) -> None:
        """Campaign 'none' overrides → build_modalities produces silent syndromic."""
        from crusher_labs import build_modalities, load_config
        from picard_framework.run_spec import merge_config_overrides
        from picard_framework.runs.mega_cruise_campaign.campaign_runner import (
            load_manifest,
        )
        from telemetry_buffer.agent_axes import (
            INFECTION_INFECTED,
            INFECTION_SUSCEPTIBLE,
            PRESENTATION_ASYMPTOMATIC,
            PRESENTATION_SYMPTOMATIC,
        )

        manifest = load_manifest()
        none_cfg = merge_config_overrides(
            load_config(),
            manifest["surveillance_configs"]["none"],
        )
        syn_cfg = merge_config_overrides(
            load_config(),
            manifest["surveillance_configs"]["syndromic"],
        )
        none_mod = build_modalities(none_cfg, rng=np.random.default_rng(7))["syndromic"]
        syn_mod = build_modalities(syn_cfg, rng=np.random.default_rng(7))["syndromic"]

        assert none_mod.sick_call_probability == 0.0
        assert none_mod.background_noise_rate == 0.0
        assert none_mod.noise_categories == []
        assert syn_mod.sick_call_probability > 0.0
        assert syn_mod.noise_categories  # non-empty defaults / fred categories

        truth = {
            "epoch": 1,
            "agents": [
                {
                    "agent_id": 1,
                    "infection_state": INFECTION_INFECTED,
                    "symptom_presentation": PRESENTATION_SYMPTOMATIC,
                    "compliance_status": COMPLIANCE_COMPLIANT,
                },
                {
                    "agent_id": 2,
                    "infection_state": INFECTION_SUSCEPTIBLE,
                    "symptom_presentation": PRESENTATION_ASYMPTOMATIC,
                    "compliance_status": COMPLIANCE_COMPLIANT,
                },
            ],
        }
        # High beliefs so syndromic reports deterministically under default rate.
        beliefs = {
            1: {"severity_belief": 1.0, "trust_medical": 1.0},
        }
        none_result = none_mod.query_ground_truth(truth, information_beliefs=beliefs)
        syn_result = syn_mod.query_ground_truth(truth, information_beliefs=beliefs)
        assert none_result["sick_call_count"] == 0
        assert syn_result["sick_call_count"] > 0
        assert none_result["sick_call_agents"] != syn_result["sick_call_agents"]
