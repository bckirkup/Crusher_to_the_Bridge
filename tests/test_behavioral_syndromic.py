"""Tests for Layer-1 syndromic behavioral overrides."""

from __future__ import annotations

import os
import sys

import numpy as np
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from crusher_labs.modalities.syndromic import SyndromicSurveillance
from engines.infection_dynamics_bridge import IllnessStatus
from orchestrator_epoch import _draw_symptom_onset, _draw_symptom_severity
from telemetry_buffer.agent_axes import (
    COMPLIANCE_COMPLIANT,
    INFECTION_INFECTED,
    PRESENTATION_SYMPTOMATIC,
)


class TestBehavioralSyndromic:
    def test_symptom_severity_is_drawn_once_per_episode(self) -> None:
        class Host:
            illness_status = IllnessStatus.NOT_ILL

            @staticmethod
            def get_chronic_illness_boost(_pid: str) -> float:
                return 0.0

        profile = {
            "illness_probability": {"eta": 1.0, "gamma": 1.0},
            "symptom_severity": {
                "strata": [
                    {"name": "mild", "weight": 1.0,
                     "sick_call_probability_per_day": 0.2},
                ],
            },
        }
        infection = {
            "acquired_particles": 1e9,
            "time_infected": 0,
            "illness": IllnessStatus.NOT_ILL,
        }
        host = Host()
        rng = np.random.default_rng(4)
        _draw_symptom_onset(host, "norwalk_gi", infection, profile, rng)
        first = infection["symptom_severity"]
        _draw_symptom_onset(host, "norwalk_gi", infection, {
            **profile,
            "symptom_severity": {
                "strata": [{
                    "name": "severe", "weight": 1.0,
                    "sick_call_probability_per_day": 0.9,
                }],
            },
        }, rng)
        assert infection["symptom_severity"] == first == "mild"

    def test_symptom_severity_weights_are_respected(self) -> None:
        profile = {
            "symptom_severity": {
                "strata": [
                    {"name": "mild", "weight": 0.35,
                     "sick_call_probability_per_day": 0.2},
                    {"name": "moderate", "weight": 0.5,
                     "sick_call_probability_per_day": 0.4},
                    {"name": "severe", "weight": 0.15,
                     "sick_call_probability_per_day": 0.8},
                ],
            },
        }
        rng = np.random.default_rng(11)
        counts = {name: 0 for name in ("mild", "moderate", "severe")}
        for _ in range(20000):
            counts[_draw_symptom_severity(profile, rng)] += 1
        total = sum(counts.values())
        assert counts["mild"] / total == pytest.approx(0.35, abs=0.02)
        assert counts["moderate"] / total == pytest.approx(0.50, abs=0.02)
        assert counts["severe"] / total == pytest.approx(0.15, abs=0.02)

    def test_own_severity_hazard_is_ordered(self) -> None:
        profile = {
            "norwalk_gi": {
                "symptom_severity": {
                    "strata": [
                        {"name": "mild", "weight": 0.35,
                         "sick_call_probability_per_day": 0.1},
                        {"name": "moderate", "weight": 0.5,
                         "sick_call_probability_per_day": 0.3},
                        {"name": "severe", "weight": 0.15,
                         "sick_call_probability_per_day": 0.7},
                    ],
                },
            },
        }
        counts = {}
        for severity in ("mild", "moderate", "severe"):
            syn = SyndromicSurveillance(
                background_noise_rate=0.0,
                symptom_severity_profiles=profile,
                rng=np.random.default_rng(7),
            )
            agent = {
                "agent_id": 1,
                "infection_state": INFECTION_INFECTED,
                "symptom_presentation": PRESENTATION_SYMPTOMATIC,
                "compliance_status": COMPLIANCE_COMPLIANT,
                "pathogen_infections": {
                    "norwalk_gi": {
                        "pathogen_id": "norwalk_gi",
                        "illness": "SYMPTOMATIC",
                        "symptom_severity": severity,
                    },
                },
            }
            counts[severity] = sum(
                bool(syn.query_ground_truth({"epoch": epoch, "agents": [agent]})[
                    "sick_call_agents"
                ])
                for epoch in range(1000)
            )
        assert counts["severe"] > counts["moderate"] > counts["mild"]

    def test_information_belief_mode_keeps_legacy_formula(self) -> None:
        syn = SyndromicSurveillance(
            sick_call_probability=0.7,
            sick_call_severity_mode="information_belief",
            background_noise_rate=0.0,
            rng=np.random.default_rng(1),
        )
        truth = {
            "epoch": 1,
            "agents": [{
                "agent_id": 1,
                "infection_state": INFECTION_INFECTED,
                "symptom_presentation": PRESENTATION_SYMPTOMATIC,
                "compliance_status": COMPLIANCE_COMPLIANT,
            }],
        }
        beliefs = {1: {"severity_belief": 0.1, "trust_medical": 0.2}}
        expected = syn.clock.probability_per_epoch(
            syn.effective_sick_call_probability(
                0.7, severity_belief=0.1, trust_medical=0.2,
            ),
        )
        observed = 0
        for epoch in range(1, 10001):
            result = syn.query_ground_truth(
                {**truth, "epoch": epoch},
                information_beliefs=beliefs,
            )
            observed += int(bool(result["sick_call_agents"]))
        assert observed / 10000 == pytest.approx(expected, abs=0.015)

    def test_first_detection_event_persists_episode_metadata(self) -> None:
        syn = SyndromicSurveillance(
            sick_call_probability=0.0,
            background_noise_rate=0.0,
            symptom_severity_profiles={
                "norwalk_gi": {
                    "symptom_severity": {
                        "strata": [{
                            "name": "moderate",
                            "weight": 1.0,
                            "sick_call_probability_per_day": 0.0,
                        }],
                    },
                },
            },
            rng=np.random.default_rng(0),
        )
        agent = {
            "agent_id": 3,
            "infection_state": INFECTION_INFECTED,
            "symptom_presentation": PRESENTATION_SYMPTOMATIC,
            "compliance_status": COMPLIANCE_COMPLIANT,
            "pathogen_infections": {
                "norwalk_gi": {
                    "illness": "SYMPTOMATIC",
                    "symptom_severity": "moderate",
                },
            },
        }
        result = syn.query_ground_truth(
            {"epoch": 12, "agents": [agent]},
            behavioral_overrides={3: "report_sick_call"},
            include_episode_telemetry=True,
        )
        assert result["first_detection_events"] == [{
            "agent_id": 3,
            "symptom_onset_epoch": 12,
            "first_sick_call_epoch": 12,
            "symptom_severity": "moderate",
        }]
        assert result["episode_detection_telemetry"] == [{
            "agent_id": 3,
            "symptom_onset_epoch": 12,
            "first_sick_call_epoch": 12,
            "symptom_severity": "moderate",
        }]

    def test_zero_base_hazard_disables_own_severity_reporting(self) -> None:
        syn = SyndromicSurveillance(
            sick_call_probability=0.0,
            background_noise_rate=0.0,
            symptom_severity_profiles={
                "norwalk_gi": {
                    "symptom_severity": {
                        "strata": [{
                            "name": "severe",
                            "weight": 1.0,
                            "sick_call_probability_per_day": 1.0,
                        }],
                    },
                },
            },
            rng=np.random.default_rng(0),
        )
        agent = {
            "agent_id": 4,
            "infection_state": INFECTION_INFECTED,
            "symptom_presentation": PRESENTATION_SYMPTOMATIC,
            "compliance_status": COMPLIANCE_COMPLIANT,
            "pathogen_infections": {
                "norwalk_gi": {
                    "illness": "SYMPTOMATIC",
                    "symptom_severity": "severe",
                },
            },
        }
        result = syn.query_ground_truth({"epoch": 12, "agents": [agent]})
        assert result["sick_call_agents"] == []

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
        syn_results = [
            syn_mod.query_ground_truth(
                {**truth, "epoch": epoch},
                information_beliefs=beliefs,
            )
            for epoch in range(24)
        ]
        syn_result = {
            "sick_call_count": sum(
                result["sick_call_count"] for result in syn_results
            ),
            "sick_call_agents": [
                aid
                for result in syn_results
                for aid in result["sick_call_agents"]
            ],
        }
        assert none_result["sick_call_count"] == 0
        assert syn_result["sick_call_count"] > 0
        assert none_result["sick_call_agents"] != syn_result["sick_call_agents"]


class TestMedicalResponseSyndromicKnobs:
    def test_detection_delay_blocks_early_reports(self) -> None:
        """Config sensitivity: detection_delay_epochs gates Bernoulli until delay."""
        syn = SyndromicSurveillance(
            sick_call_probability=1.0,
            background_noise_rate=0.0,
            noise_categories=[],
            detection_delay_epochs=2,
            rng=np.random.default_rng(0),
        )
        agent = {
            "agent_id": 1,
            "infection_state": INFECTION_INFECTED,
            "symptom_presentation": PRESENTATION_SYMPTOMATIC,
            "compliance_status": COMPLIANCE_COMPLIANT,
        }
        beliefs = {1: {"severity_belief": 1.0, "trust_medical": 1.0}}
        early = syn.query_ground_truth(
            {"epoch": 0, "agents": [agent]}, information_beliefs=beliefs,
        )
        mid = syn.query_ground_truth(
            {"epoch": 1, "agents": [agent]}, information_beliefs=beliefs,
        )
        ready = syn.query_ground_truth(
            {"epoch": 2, "agents": [agent]}, information_beliefs=beliefs,
        )
        assert early["sick_call_agents"] == []
        assert mid["sick_call_agents"] == []
        assert 1 in ready["sick_call_agents"]

    def test_detection_delay_zero_matches_immediate(self) -> None:
        """Golden: delay=0 reports on first symptomatic epoch (stock behavior)."""
        syn = SyndromicSurveillance(
            sick_call_probability=1.0,
            background_noise_rate=0.0,
            noise_categories=[],
            detection_delay_epochs=0,
            rng=np.random.default_rng(0),
        )
        truth = {
            "epoch": 0,
            "agents": [{
                "agent_id": 3,
                "infection_state": INFECTION_INFECTED,
                "symptom_presentation": PRESENTATION_SYMPTOMATIC,
                "compliance_status": COMPLIANCE_COMPLIANT,
            }],
        }
        result = syn.query_ground_truth(
            truth,
            information_beliefs={3: {"severity_belief": 1.0, "trust_medical": 1.0}},
        )
        assert 3 in result["sick_call_agents"]

    def test_report_sick_call_bypasses_detection_delay(self) -> None:
        syn = SyndromicSurveillance(
            sick_call_probability=0.0,
            detection_delay_epochs=10,
            rng=np.random.default_rng(0),
        )
        truth = {
            "epoch": 0,
            "agents": [{
                "agent_id": 4,
                "infection_state": INFECTION_INFECTED,
                "symptom_presentation": PRESENTATION_SYMPTOMATIC,
                "compliance_status": COMPLIANCE_COMPLIANT,
            }],
        }
        result = syn.query_ground_truth(
            truth, behavioral_overrides={4: "report_sick_call"},
        )
        assert 4 in result["sick_call_agents"]

    def test_crew_screening_interval_adds_healthy_crew(self) -> None:
        """Config sensitivity: non-null interval adds crew on interval epochs."""
        from telemetry_buffer.agent_axes import (
            INFECTION_SUSCEPTIBLE,
            PRESENTATION_ASYMPTOMATIC,
        )

        syn = SyndromicSurveillance(
            sick_call_probability=0.0,
            background_noise_rate=0.0,
            noise_categories=[],
            crew_screening_interval_epochs=2,
            rng=np.random.default_rng(0),
        )
        agents = [
            {
                "agent_id": 10,
                "agent_class": "crew_services",
                "infection_state": INFECTION_SUSCEPTIBLE,
                "symptom_presentation": PRESENTATION_ASYMPTOMATIC,
                "compliance_status": COMPLIANCE_COMPLIANT,
            },
            {
                "agent_id": 11,
                "agent_class": "passenger_adult",
                "infection_state": INFECTION_SUSCEPTIBLE,
                "symptom_presentation": PRESENTATION_ASYMPTOMATIC,
                "compliance_status": COMPLIANCE_COMPLIANT,
            },
        ]
        on = syn.query_ground_truth({"epoch": 0, "agents": agents})
        off = syn.query_ground_truth({"epoch": 1, "agents": agents})
        on2 = syn.query_ground_truth({"epoch": 2, "agents": agents})
        assert 10 in on["sick_call_agents"]
        assert 10 in on["crew_screening_ids"]
        assert 11 not in on["sick_call_agents"]
        assert off["crew_screening_ids"] == []
        assert 10 not in off["sick_call_agents"]
        assert 10 in on2["crew_screening_ids"]

    def test_build_modalities_reads_new_syndromic_keys(self) -> None:
        from crusher_labs import build_modalities

        cfg = {
            "syndromic": {
                "sick_call_probability": 0.55,
                "detection_delay_epochs": 4,
                "crew_screening_interval_epochs": 12,
            },
            "fred_behavior": {"quarantine_compliance": 0.91},
        }
        syn = build_modalities(cfg, rng=np.random.default_rng(1))["syndromic"]
        assert syn.sick_call_probability == 0.55
        assert syn.detection_delay_epochs == 4
        assert syn.crew_screening_interval_epochs == 12
        assert syn.quarantine_compliance == 0.91
