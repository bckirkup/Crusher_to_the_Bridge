"""Tests for Issue #110: Chronic Disease agent feature."""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pytest

from engines.infection_dynamics_bridge import (
    InfectionStatus,
    IllnessStatus,
    KorkinAgent,
    KorkinShipEngine,
)

# ── Fixtures ─────────────────────────────────────────────────────────────

def _make_agent(agent_id: int = 0, agent_class: str = "passenger_general") -> KorkinAgent:
    a = KorkinAgent(
        agent_id=agent_id,
        role="passenger",
        agent_class=agent_class,
        gender="M",
        immune=False,
        home_zone="cabin_1",
        dining_zone="mess_hall",
        work_zone="lounge",
        free_zone="deck",
        schedule=["cabin_1", "mess_hall", "lounge", "deck"],
    )
    return a


SAMPLE_PATHOGEN_MODIFIERS: dict[str, dict[str, float]] = {
    "norwalk_gi": {
        "susceptibility_multiplier": 1.4,
        "severity_multiplier": 1.6,
        "recovery_day_extension": 2,
        "illness_probability_boost": 0.15,
    },
    "default": {
        "susceptibility_multiplier": 1.3,
        "severity_multiplier": 1.4,
        "recovery_day_extension": 1,
        "illness_probability_boost": 0.10,
    },
}

SAMPLE_CHRONIC_CONFIG: dict[str, dict[str, Any]] = {
    "type2_diabetes": {
        "disease_id": "type2_diabetes",
        "name": "Type 2 Diabetes Mellitus",
        "category": "metabolic",
        "prevalence_by_class": {
            "passenger_elderly": 0.25,
            "passenger_general": 0.08,
            "default": 0.07,
        },
        "pathogen_modifiers": SAMPLE_PATHOGEN_MODIFIERS,
        "wearable_baseline_offsets": {
            "heart_rate": 4.0,
            "hrv": -8.0,
        },
        "wearable_infection_response_scale": 1.3,
        "behavioral_modifiers": {
            "sick_call_probability_boost": 0.15,
            "quarantine_compliance_boost": 0.05,
        },
        "chronic_medications": ["metformin", "insulin_glargine"],
    },
    "hiv_controlled": {
        "disease_id": "hiv_controlled",
        "name": "HIV (Controlled on ART)",
        "category": "immunodeficiency",
        "prevalence_by_class": {
            "default": 0.02,
        },
        "pathogen_modifiers": {
            "default": {
                "susceptibility_multiplier": 2.0,
                "severity_multiplier": 1.8,
                "recovery_day_extension": 3,
                "illness_probability_boost": 0.20,
            },
        },
        "wearable_baseline_offsets": {
            "heart_rate": 3.0,
        },
        "wearable_infection_response_scale": 1.5,
        "behavioral_modifiers": {
            "sick_call_probability_boost": 0.20,
            "quarantine_compliance_boost": 0.10,
        },
        "chronic_medications": ["tenofovir_emtricitabine"],
    },
}


# ── KorkinAgent chronic disease methods ──────────────────────────────────

class TestKorkinAgentChronicDisease:
    def test_apply_chronic_disease_sets_ids(self) -> None:
        agent = _make_agent()
        agent.apply_chronic_disease("type2_diabetes", SAMPLE_PATHOGEN_MODIFIERS, 1.3)
        assert "type2_diabetes" in agent.chronic_disease_ids
        assert agent.has_chronic_disease is True

    def test_apply_chronic_disease_no_duplicate(self) -> None:
        agent = _make_agent()
        agent.apply_chronic_disease("type2_diabetes", SAMPLE_PATHOGEN_MODIFIERS, 1.3)
        agent.apply_chronic_disease("type2_diabetes", SAMPLE_PATHOGEN_MODIFIERS, 1.3)
        assert agent.chronic_disease_ids.count("type2_diabetes") == 1

    def test_get_chronic_recovery_day_extends(self) -> None:
        agent = _make_agent()
        agent.apply_chronic_disease("type2_diabetes", SAMPLE_PATHOGEN_MODIFIERS, 1.3)
        assert agent.get_chronic_recovery_day("norwalk_gi", 3) == 5
        assert agent.get_chronic_recovery_day("unknown", 3) == 4  # uses default

    def test_get_chronic_illness_boost(self) -> None:
        agent = _make_agent()
        agent.apply_chronic_disease("type2_diabetes", SAMPLE_PATHOGEN_MODIFIERS, 1.3)
        assert agent.get_chronic_illness_boost("norwalk_gi") == pytest.approx(0.15)
        assert agent.get_chronic_illness_boost("unknown") == pytest.approx(0.10)

    def test_get_chronic_severity_multiplier(self) -> None:
        agent = _make_agent()
        agent.apply_chronic_disease("type2_diabetes", SAMPLE_PATHOGEN_MODIFIERS, 1.3)
        assert agent.get_chronic_severity_multiplier("norwalk_gi") == pytest.approx(1.6)
        assert agent.get_chronic_severity_multiplier("unknown") == pytest.approx(1.4)

    def test_wearable_response_scale(self) -> None:
        agent = _make_agent()
        assert agent.chronic_wearable_response_scale == pytest.approx(1.0)
        agent.apply_chronic_disease("type2_diabetes", SAMPLE_PATHOGEN_MODIFIERS, 1.3)
        assert agent.chronic_wearable_response_scale == pytest.approx(1.3)

    def test_no_chronic_disease_defaults(self) -> None:
        agent = _make_agent()
        assert agent.has_chronic_disease is False
        assert agent.get_chronic_recovery_day("any", 5) == 5
        assert agent.get_chronic_illness_boost("any") == pytest.approx(0.0)
        assert agent.get_chronic_severity_multiplier("any") == pytest.approx(1.0)

    def test_comorbid_merging(self) -> None:
        agent = _make_agent()
        mods_a = {
            "norwalk_gi": {
                "susceptibility_multiplier": 1.4,
                "severity_multiplier": 1.6,
                "recovery_day_extension": 2,
                "illness_probability_boost": 0.15,
            },
        }
        mods_b = {
            "norwalk_gi": {
                "susceptibility_multiplier": 2.0,
                "severity_multiplier": 1.8,
                "recovery_day_extension": 3,
                "illness_probability_boost": 0.20,
            },
        }
        agent.apply_chronic_disease("disease_a", mods_a, 1.3)
        agent.apply_chronic_disease("disease_b", mods_b, 1.5)
        assert len(agent.chronic_disease_ids) == 2
        merged = agent.chronic_pathogen_mods["norwalk_gi"]
        # susceptibility: multiplicative composition
        assert merged["susceptibility_multiplier"] == pytest.approx(1.4 * 2.0)
        # severity: max
        assert merged["severity_multiplier"] == pytest.approx(1.8)
        # recovery: additive
        assert merged["recovery_day_extension"] == 5
        # illness boost: additive, capped at 0.5
        assert merged["illness_probability_boost"] == pytest.approx(0.35)
        # wearable scale: max
        assert agent.chronic_wearable_response_scale == pytest.approx(1.5)

    def test_to_schema_dict_includes_chronic_ids(self) -> None:
        agent = _make_agent()
        agent.apply_chronic_disease("type2_diabetes", SAMPLE_PATHOGEN_MODIFIERS, 1.3)
        d = agent.to_schema_dict()
        assert d["chronic_disease_ids"] == ["type2_diabetes"]

    def test_to_schema_dict_omits_chronic_when_empty(self) -> None:
        agent = _make_agent()
        d = agent.to_schema_dict()
        assert "chronic_disease_ids" not in d


# ── orchestrator_chronic module ──────────────────────────────────────────

class TestOrchestratorChronic:
    def test_load_disabled(self) -> None:
        from orchestrator_chronic import load_chronic_disease_config
        result = load_chronic_disease_config({"chronic_disease": {"enabled": False}})
        assert result == {}

    def test_load_missing_key(self) -> None:
        from orchestrator_chronic import load_chronic_disease_config
        result = load_chronic_disease_config({})
        assert result == {}

    def test_load_from_file(self) -> None:
        from orchestrator_chronic import load_chronic_disease_config
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cfg = {
            "chronic_disease": {
                "enabled": True,
                "config_path": "data/config/chronic_diseases.json",
            },
        }
        result = load_chronic_disease_config(cfg, repo_root=repo_root)
        assert "type2_diabetes" in result
        assert "hiv_controlled" in result

    def test_assign_chronic_diseases_respects_prevalence(self) -> None:
        from orchestrator_chronic import assign_chronic_diseases

        engine = MagicMock(spec=KorkinShipEngine)
        agents = []
        for i in range(100):
            a = _make_agent(agent_id=i, agent_class="passenger_elderly")
            agents.append(a)
        engine.agents = agents

        cfg = {
            "chronic_disease": {
                "enabled": True,
                "allow_comorbid": False,
                "max_comorbid": 1,
            },
        }
        high_prev_config = {
            "high_prev": {
                "disease_id": "high_prev",
                "prevalence_by_class": {"passenger_elderly": 1.0},
                "pathogen_modifiers": {"default": {"susceptibility_multiplier": 1.5}},
                "wearable_infection_response_scale": 1.0,
            },
        }
        rng = np.random.default_rng(42)
        assignments = assign_chronic_diseases(
            engine, high_prev_config, {"norwalk_gi": {}}, cfg, rng,
        )
        # With prevalence=1.0, all non-immune agents should be assigned
        assert len(assignments) == 100

    def test_assign_respects_max_comorbid(self) -> None:
        from orchestrator_chronic import assign_chronic_diseases

        engine = MagicMock(spec=KorkinShipEngine)
        agents = [_make_agent(agent_id=0)]
        engine.agents = agents

        cfg = {
            "chronic_disease": {
                "enabled": True,
                "allow_comorbid": True,
                "max_comorbid": 1,
            },
        }
        multi_config = {
            "d1": {
                "disease_id": "d1",
                "prevalence_by_class": {"default": 1.0},
                "pathogen_modifiers": {},
                "wearable_infection_response_scale": 1.0,
            },
            "d2": {
                "disease_id": "d2",
                "prevalence_by_class": {"default": 1.0},
                "pathogen_modifiers": {},
                "wearable_infection_response_scale": 1.0,
            },
        }
        rng = np.random.default_rng(42)
        assignments = assign_chronic_diseases(
            engine, multi_config, {}, cfg, rng,
        )
        assert len(assignments.get(0, [])) <= 1

    def test_assign_skips_immune_agents(self) -> None:
        from orchestrator_chronic import assign_chronic_diseases

        engine = MagicMock(spec=KorkinShipEngine)
        agent = _make_agent(agent_id=0)
        agent.immune = True
        engine.agents = [agent]

        cfg = {
            "chronic_disease": {"enabled": True, "allow_comorbid": True, "max_comorbid": 2},
        }
        all_config = {
            "d1": {
                "disease_id": "d1",
                "prevalence_by_class": {"default": 1.0},
                "pathogen_modifiers": {},
                "wearable_infection_response_scale": 1.0,
            },
        }
        rng = np.random.default_rng(42)
        assignments = assign_chronic_diseases(engine, all_config, {}, cfg, rng)
        assert 0 not in assignments

    def test_get_chronic_wearable_offsets(self) -> None:
        from orchestrator_chronic import get_chronic_wearable_offsets
        assignments = {0: ["type2_diabetes"]}
        offsets = get_chronic_wearable_offsets(SAMPLE_CHRONIC_CONFIG, assignments)
        assert offsets[0]["heart_rate"] == pytest.approx(4.0)
        assert offsets[0]["hrv"] == pytest.approx(-8.0)

    def test_get_chronic_medications(self) -> None:
        from orchestrator_chronic import get_chronic_medications
        assignments = {0: ["type2_diabetes"]}
        meds = get_chronic_medications(SAMPLE_CHRONIC_CONFIG, assignments)
        assert "metformin" in meds[0]
        assert "insulin_glargine" in meds[0]

    def test_get_chronic_behavioral_modifiers(self) -> None:
        from orchestrator_chronic import get_chronic_behavioral_modifiers
        assignments = {0: ["type2_diabetes"]}
        mods = get_chronic_behavioral_modifiers(SAMPLE_CHRONIC_CONFIG, assignments)
        assert mods[0]["sick_call_probability_boost"] == pytest.approx(0.15)
        assert mods[0]["quarantine_compliance_boost"] == pytest.approx(0.05)

    def test_behavioral_modifier_caps(self) -> None:
        from orchestrator_chronic import get_chronic_behavioral_modifiers
        assignments = {0: ["type2_diabetes", "hiv_controlled"]}
        mods = get_chronic_behavioral_modifiers(SAMPLE_CHRONIC_CONFIG, assignments)
        assert mods[0]["sick_call_probability_boost"] <= 0.30
        assert mods[0]["quarantine_compliance_boost"] <= 0.15


# ── AgentProfile chronic fields ──────────────────────────────────────────

class TestAgentProfileChronicFields:
    def test_profile_has_chronic_disease_ids(self) -> None:
        from decision_engine.agent_profile import AgentProfile
        profile = AgentProfile(
            profile_id="test",
            agent_id=0,
            agent_class="passenger_general",
            role_group="passenger",
            gender="M",
            chronic_disease_ids=["type2_diabetes"],
        )
        d = profile.to_dict()
        assert d["chronic_disease_ids"] == ["type2_diabetes"]

    def test_profile_default_empty(self) -> None:
        from decision_engine.agent_profile import AgentProfile
        profile = AgentProfile(
            profile_id="test",
            agent_id=0,
            agent_class="passenger_general",
            role_group="passenger",
            gender="M",
        )
        assert profile.chronic_disease_ids == []


# ── Lived experience chronic field ───────────────────────────────────────

class TestLivedExperienceChronicField:
    def test_chronic_disease_ids_in_experience(self) -> None:
        from decision_engine.lived_experience import AgentLivedExperience
        exp = AgentLivedExperience(
            agent_id=0,
            chronic_disease_ids=["type2_diabetes"],
        )
        d = exp.to_dict()
        assert d["chronic_disease_ids"] == ["type2_diabetes"]


# ── Syndromic surveillance chronic behavioral mods ───────────────────────

class TestSyndromicChronicMods:
    def test_sick_call_boost_increases_probability(self) -> None:
        from crusher_labs.modalities.syndromic import SyndromicSurveillance
        from telemetry_buffer.agent_axes import PRESENTATION_SYMPTOMATIC

        rng = np.random.default_rng(42)
        syn = SyndromicSurveillance(sick_call_probability=0.5, rng=rng)
        agents = [
            {
                "agent_id": 0,
                "infection_state": "infected",
                "symptom_presentation": PRESENTATION_SYMPTOMATIC,
                "compliance_status": "compliant",
                "shedding_rate": 1.0,
            },
        ]
        truth = {"epoch": 1, "agents": agents}

        # A nonzero base probability still receives the chronic boost.
        chronic_mods = {0: {"sick_call_probability_boost": 1.0}}
        result = syn.query_ground_truth(
            truth, chronic_behavioral_mods=chronic_mods,
        )
        assert 0 in result["sick_call_agents"]

    def test_zero_sick_call_base_blocks_chronic_boost(self) -> None:
        from crusher_labs.modalities.syndromic import SyndromicSurveillance
        from telemetry_buffer.agent_axes import PRESENTATION_SYMPTOMATIC

        syn = SyndromicSurveillance(sick_call_probability=0.0, rng=np.random.default_rng(42))
        truth = {
            "epoch": 1,
            "agents": [{
                "agent_id": 0,
                "infection_state": "infected",
                "symptom_presentation": PRESENTATION_SYMPTOMATIC,
                "compliance_status": "compliant",
            }],
        }
        result = syn.query_ground_truth(
            truth,
            chronic_behavioral_mods={0: {"sick_call_probability_boost": 1.0}},
        )
        assert result["sick_call_agents"] == []

    def test_quarantine_compliance_boost(self) -> None:
        from crusher_labs.modalities.syndromic import SyndromicSurveillance
        rng = np.random.default_rng(42)
        syn = SyndromicSurveillance(
            quarantine_compliance=0.0,
            reluctant_fraction=1.0,
            reluctant_delay_epochs=99,
            rng=rng,
        )

        # Without boost: compliance=0.0 → reluctant/defiant, fail at epoch 0
        results_no_boost = []
        for aid in range(50):
            results_no_boost.append(syn.check_quarantine_compliance(aid, 0))
        assert all(r is False for r in results_no_boost)

        # Fresh agent with boost=1.0: effective compliance=1.0 → compliant
        assert syn.check_quarantine_compliance(
            999, 0, chronic_compliance_boost=1.0,
        ) is True
        assert syn._compliance_class[999] == "compliant"


# ── Severity escalation ─────────────────────────────────────────────────

class TestSeverityEscalation:
    def test_escalation_applies_to_chronic_agents(self) -> None:
        from orchestrator_epoch import apply_chronic_severity_escalation
        from telemetry_buffer.agent_axes import (
            PRESENTATION_SYMPTOMATIC,
            PRESENTATION_SEVERE,
        )

        engine = MagicMock(spec=KorkinShipEngine)
        agent_obj = _make_agent(agent_id=0)
        agent_obj.apply_chronic_disease("test", {
            "pathogen_a": {
                "susceptibility_multiplier": 1.0,
                "severity_multiplier": 100.0,  # very high → guaranteed escalation
                "recovery_day_extension": 0,
                "illness_probability_boost": 0.0,
            },
        }, 1.0)
        agent_obj.infect_with_pathogen("pathogen_a", 1e4, 0)
        engine.agents = [agent_obj]

        agents = [{
            "agent_id": 0,
            "symptom_presentation": PRESENTATION_SYMPTOMATIC,
        }]
        rng = np.random.default_rng(42)
        apply_chronic_severity_escalation(agents, engine, rng)
        assert agents[0]["symptom_presentation"] == PRESENTATION_SEVERE

    def test_no_escalation_without_chronic_disease(self) -> None:
        from orchestrator_epoch import apply_chronic_severity_escalation
        from telemetry_buffer.agent_axes import PRESENTATION_SYMPTOMATIC

        engine = MagicMock(spec=KorkinShipEngine)
        agent_obj = _make_agent(agent_id=0)
        engine.agents = [agent_obj]

        agents = [{
            "agent_id": 0,
            "symptom_presentation": PRESENTATION_SYMPTOMATIC,
        }]
        rng = np.random.default_rng(42)
        apply_chronic_severity_escalation(agents, engine, rng)
        assert agents[0]["symptom_presentation"] == PRESENTATION_SYMPTOMATIC


# ── SimulationState chronic fields ───────────────────────────────────────

class TestSimulationStateChronicFields:
    def test_default_empty_chronic(self) -> None:
        from orchestrator_types import SimulationState
        state = SimulationState()
        assert state.chronic_assignments == {}
        assert state.chronic_behavioral_mods == {}

    def test_chronic_fields_set(self) -> None:
        from orchestrator_types import SimulationState
        state = SimulationState(
            chronic_assignments={0: ["type2_diabetes"]},
            chronic_behavioral_mods={0: {"sick_call_probability_boost": 0.15}},
        )
        assert state.chronic_assignments[0] == ["type2_diabetes"]
        assert state.chronic_behavioral_mods[0]["sick_call_probability_boost"] == pytest.approx(0.15)


# ── Sanity checker validation ────────────────────────────────────────────

class TestSanityCheckerChronic:
    def test_sanity_checker_validates_chronic_config(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        monkeypatch.syspath_prepend(os.path.join(repo_root, "tools"))
        monkeypatch.chdir(repo_root)
        from sanity_checker import Report, _check_chronic_disease
        cfg = {
            "chronic_disease": {
                "enabled": True,
                "config_path": "data/config/chronic_diseases.json",
            },
        }
        report = Report()
        _check_chronic_disease(cfg, report)
        assert report.passed, f"Sanity check failed: {[f.message for f in report.findings]}"

    def test_sanity_checker_disabled_skips(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        monkeypatch.syspath_prepend(os.path.join(repo_root, "tools"))
        from sanity_checker import Report, _check_chronic_disease
        cfg = {"chronic_disease": {"enabled": False}}
        report = Report()
        _check_chronic_disease(cfg, report)
        assert report.passed
