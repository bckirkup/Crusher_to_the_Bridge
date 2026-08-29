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
    def test_five_state_severity_is_drawn_once_per_episode(self) -> None:
        class Host:
            illness_status = IllnessStatus.NOT_ILL

            @staticmethod
            def get_chronic_illness_boost(_pid: str) -> float:
                return 0.0

        profile = {
            "illness_probability": {"eta": 1.0, "gamma": 1.0},
            "severity_model": {
                "states": [
                    "asymptomatic", "subclinical", "mild", "moderate",
                    "severe_critical",
                ],
                "base_probabilities": [0.0, 0.0, 1.0, 0.0, 0.0],
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
            "severity_model": {
                "states": [
                    "asymptomatic", "subclinical", "mild", "moderate",
                    "severe_critical",
                ],
                "base_probabilities": [0.0, 0.0, 0.0, 0.0, 1.0],
            },
        }, rng)
        assert infection["symptom_severity"] == first == "mild"

    def test_five_state_symptomatic_prior_is_renormalized(self) -> None:
        profile = {
            "severity_model": {
                "states": [
                    "asymptomatic", "subclinical", "mild", "moderate",
                    "severe_critical",
                ],
                "base_probabilities": [0.25, 0.55, 0.19, 0.009, 0.001],
            },
        }
        rng = np.random.default_rng(11)
        states = ("subclinical", "mild", "moderate", "severe_critical")
        counts = {name: 0 for name in states}
        for _ in range(20000):
            counts[_draw_symptom_severity(profile, rng)] += 1
        total = sum(counts.values())
        symptomatic = np.array([0.55, 0.19, 0.009, 0.001])
        symptomatic /= symptomatic.sum()
        for state, expected in zip(states, symptomatic):
            assert counts[state] / total == pytest.approx(expected, abs=0.02)

    def test_five_state_own_severity_hazard_is_ordered(self) -> None:
        profile = {
            "norwalk_gi": {
                "severity_model": {
                    "states": [
                        "asymptomatic", "subclinical", "mild", "moderate",
                        "severe_critical",
                    ],
                    "base_probabilities": [0.25, 0.55, 0.19, 0.009, 0.001],
                },
                "observation_model": {
                    "syndrome_case_eligibility_by_severity": [0, 0.55, 0.98, 1, 1],
                    "reporting_probability_by_severity_pre_recognition": [
                        0, 0.45, 0.70, 0.94, 1,
                    ],
                    "reporting_probability_by_severity_post_recognition": [
                        0, 0.50, 0.76, 0.96, 1,
                    ],
                    "episode_reporting_window_days": 2.0,
                },
            },
        }
        counts = {}
        for severity in ("subclinical", "mild", "moderate", "severe_critical"):
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
        assert counts["severe_critical"] > counts["moderate"] > counts["mild"]
        assert counts["mild"] > counts["subclinical"]

    def test_five_state_analytic_cross_checks(self) -> None:
        base = np.array([0.25, 0.55, 0.19, 0.009, 0.001])
        eligibility = np.array([0, 0.55, 0.98, 1, 1])
        reporting = np.array([0, 0.50, 0.76, 0.96, 1])
        eligible = float(np.dot(base, eligibility))
        reported = float(np.dot(base, eligibility * reporting))
        symptomatic = float(base[1:].sum())
        assert eligible == pytest.approx(0.498700, abs=1e-6)
        assert reported == pytest.approx(0.302402, abs=1e-6)
        assert reported / eligible == pytest.approx(0.606381, abs=1e-6)
        assert reported / symptomatic == pytest.approx(0.403203, abs=1e-6)

    def test_recognition_increases_five_state_reporting_hazard(self) -> None:
        profile = {
            "norwalk_gi": {
                "severity_model": {
                    "states": [
                        "asymptomatic", "subclinical", "mild", "moderate",
                        "severe_critical",
                    ],
                    "base_probabilities": [0.25, 0.55, 0.19, 0.009, 0.001],
                },
                "observation_model": {
                    "syndrome_case_eligibility_by_severity": [0, 0.55, 0.98, 1, 1],
                    "reporting_probability_by_severity_pre_recognition": [
                        0, 0.45, 0.70, 0.94, 1,
                    ],
                    "reporting_probability_by_severity_post_recognition": [
                        0, 0.50, 0.76, 0.96, 1,
                    ],
                    "episode_reporting_window_days": 2.0,
                },
            },
        }
        agent = {
            "agent_id": 5,
            "infection_state": INFECTION_INFECTED,
            "symptom_presentation": PRESENTATION_SYMPTOMATIC,
            "compliance_status": COMPLIANCE_COMPLIANT,
            "pathogen_infections": {
                "norwalk_gi": {
                    "pathogen_id": "norwalk_gi",
                    "illness": "SYMPTOMATIC",
                    "symptom_severity": "mild",
                },
            },
        }
        syn = SyndromicSurveillance(
            sick_call_probability=1.0,
            background_noise_rate=0.0,
            symptom_severity_profiles=profile,
            rng=np.random.default_rng(2),
        )
        pre = syn._severity_hazard(agent, outbreak_recognized=False)
        post = syn._severity_hazard(agent, outbreak_recognized=True)
        assert post > pre

    def test_lab_sampling_vector_is_validated_but_unused(self) -> None:
        profile = {
            "norwalk_gi": {
                "severity_model": {
                    "states": [
                        "asymptomatic", "subclinical", "mild", "moderate",
                        "severe_critical",
                    ],
                    "base_probabilities": [0.25, 0.55, 0.19, 0.009, 0.001],
                },
                "observation_model": {
                    "syndrome_case_eligibility_by_severity": [0, 0.55, 0.98, 1, 1],
                    "reporting_probability_by_severity_pre_recognition": [
                        0, 0.45, 0.70, 0.94, 1,
                    ],
                    "reporting_probability_by_severity_post_recognition": [
                        0, 0.50, 0.76, 0.96, 1,
                    ],
                    "lab_sampling_probability_by_severity": [0, 0.9, 0.9, 0.9, 0.9],
                    "episode_reporting_window_days": 2.0,
                },
            },
        }
        agent = {
            "agent_id": 6,
            "infection_state": INFECTION_INFECTED,
            "symptom_presentation": PRESENTATION_SYMPTOMATIC,
            "compliance_status": COMPLIANCE_COMPLIANT,
            "pathogen_infections": {
                "norwalk_gi": {
                    "pathogen_id": "norwalk_gi",
                    "illness": "SYMPTOMATIC",
                    "symptom_severity": "moderate",
                },
            },
        }
        syn = SyndromicSurveillance(
            sick_call_probability=1.0,
            background_noise_rate=0.0,
            symptom_severity_profiles=profile,
            rng=np.random.default_rng(3),
        )
        assert syn._severity_hazard(agent) == pytest.approx(
            1.0 - (1.0 - 1.0 * 0.94) ** 0.5,
        )

    def test_unknown_state_raises_but_legacy_profile_uses_base_hazard(self) -> None:
        profile = {
            "norwalk_gi": {
                "severity_model": {
                    "states": [
                        "asymptomatic", "subclinical", "mild", "moderate",
                        "severe_critical",
                    ],
                },
                "observation_model": {},
            },
        }
        agent = {
            "agent_id": 7,
            "symptom_presentation": PRESENTATION_SYMPTOMATIC,
            "pathogen_infections": {
                "norwalk_gi": {
                    "illness": "SYMPTOMATIC",
                    "symptom_severity": "unrecognised",
                },
            },
        }
        syn = SyndromicSurveillance(
            sick_call_probability=0.7,
            symptom_severity_profiles=profile,
        )
        with pytest.raises(ValueError, match="norwalk_gi.*unrecognised"):
            syn._severity_hazard(agent)

        legacy = SyndromicSurveillance(
            sick_call_probability=0.37,
            symptom_severity_profiles={"norwalk_gi": {}},
        )
        assert legacy._severity_hazard(agent) == pytest.approx(0.37)

    def test_asymptomatic_host_never_makes_true_sick_call(self) -> None:
        agent = {
            "agent_id": 7,
            "infection_state": INFECTION_INFECTED,
            "symptom_presentation": PRESENTATION_SYMPTOMATIC,
            "compliance_status": COMPLIANCE_COMPLIANT,
            "pathogen_infections": {
                "norwalk_gi": {
                    "pathogen_id": "norwalk_gi",
                    "illness": "SYMPTOMATIC",
                    "symptom_severity": "asymptomatic",
                },
            },
        }
        five_state_profile = {
            "norwalk_gi": {
                "severity_model": {
                    "states": [
                        "asymptomatic", "subclinical", "mild", "moderate",
                        "severe_critical",
                    ],
                },
                "observation_model": {},
            },
        }
        for profiles in (None, five_state_profile):
            syn = SyndromicSurveillance(
                sick_call_probability=1.0,
                background_noise_rate=0.0,
                noise_categories=[],
                symptom_severity_profiles=profiles,
                rng=np.random.default_rng(4),
            )
            result = syn.query_ground_truth({"epoch": 0, "agents": [agent]})
            assert result["true_positive_ids"] == []
            assert result["sick_call_agents"] == []

    def test_asymptomatic_label_is_recorded_and_replaced_once_on_symptom_onset(
        self,
    ) -> None:
        class Host:
            illness_status = IllnessStatus.NOT_ILL

            @staticmethod
            def get_chronic_illness_boost(_pid: str) -> float:
                return 0.0

        profile = {
            "illness_probability": {"eta": 0.0, "gamma": 1.0},
            "severity_model": {
                "states": [
                    "asymptomatic", "subclinical", "mild", "moderate",
                    "severe_critical",
                ],
                "base_probabilities": [0.0, 0.0, 1.0, 0.0, 0.0],
            },
        }
        infection = {
            "acquired_particles": 1e9,
            "time_infected": 0,
            "illness": IllnessStatus.NOT_ILL,
        }
        host = Host()
        rng = np.random.default_rng(8)
        _draw_symptom_onset(host, "norwalk_gi", infection, profile, rng)
        assert infection["symptom_severity"] == "asymptomatic"
        assert infection["illness"] == IllnessStatus.NOT_ILL

        symptomatic_profile = {
            **profile,
            "illness_probability": {"eta": 1.0, "gamma": 1.0},
        }
        _draw_symptom_onset(
            host,
            "norwalk_gi",
            infection,
            symptomatic_profile,
            rng,
        )
        assert infection["illness"] == IllnessStatus.SYMPTOMATIC
        assert infection["symptom_severity"] == "mild"

        replacement_profile = {
            **symptomatic_profile,
            "severity_model": {
                "states": [
                    "asymptomatic", "subclinical", "mild", "moderate",
                    "severe_critical",
                ],
                "base_probabilities": [0.0, 0.0, 0.0, 0.0, 1.0],
            },
        }
        _draw_symptom_onset(
            host,
            "norwalk_gi",
            infection,
            replacement_profile,
            rng,
        )
        assert infection["symptom_severity"] == "mild"

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
                    "severity_model": {
                        "states": [
                            "asymptomatic", "subclinical", "mild", "moderate",
                            "severe_critical",
                        ],
                        "base_probabilities": [0.25, 0.55, 0.19, 0.009, 0.001],
                    },
                    "observation_model": {
                        "syndrome_case_eligibility_by_severity": [0, 0.55, 0.98, 1, 1],
                        "reporting_probability_by_severity_pre_recognition": [
                            0, 0.45, 0.70, 0.94, 1,
                        ],
                        "reporting_probability_by_severity_post_recognition": [
                            0, 0.50, 0.76, 0.96, 1,
                        ],
                        "episode_reporting_window_days": 2.0,
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
                    "severity_model": {
                        "states": [
                            "asymptomatic", "subclinical", "mild", "moderate",
                            "severe_critical",
                        ],
                        "base_probabilities": [0.25, 0.55, 0.19, 0.009, 0.001],
                    },
                    "observation_model": {
                        "syndrome_case_eligibility_by_severity": [0, 0.55, 0.98, 1, 1],
                        "reporting_probability_by_severity_pre_recognition": [
                            0, 0.45, 0.70, 0.94, 1,
                        ],
                        "reporting_probability_by_severity_post_recognition": [
                            0, 0.50, 0.76, 0.96, 1,
                        ],
                        "episode_reporting_window_days": 2.0,
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
                    "symptom_severity": "severe_critical",
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
