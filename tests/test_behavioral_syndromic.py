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
