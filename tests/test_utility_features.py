"""Graded sensitivity and bounds for UtilityFeatureExtractor."""

from __future__ import annotations

import pytest

from decision_engine.information.reputation import ReputationTracker
from decision_engine.lived_experience import AgentLivedExperience, AgentLivedExperienceStore
from decision_engine.utility.features import UtilityFeatureExtractor


def _pop_summary(*, infected: int, symptomatic: int = 0) -> dict:
    # Keep population fixed so infected_rate grades purely with infected count.
    susceptible = 20 - infected
    return {
        "susceptible": susceptible,
        "infected": infected,
        "recovered": 0,
        "immune": 0,
        "symptomatic": symptomatic,
    }


class TestInfectedRateSensitivity:
    def test_infected_rate_monotone_for_sweep(self) -> None:
        ext = UtilityFeatureExtractor()
        rep = ReputationTracker()
        rates: list[float] = []
        for infected in (0, 2, 10):
            cmd = {
                "summary": _pop_summary(infected=infected),
                "cost_accounting": {},
            }
            feats = ext.command_features(cmd, rep, {})
            rates.append(feats["infected_rate"])
        assert rates == sorted(rates)
        assert rates[0] == pytest.approx(0.0)
        assert rates[-1] - rates[0] > 0.4  # live knob across {0,10}/20
        assert all(0.0 <= r <= 1.0 for r in rates)


class TestMedicalFeatures:
    def test_alert_and_protocol_counts(self) -> None:
        ext = UtilityFeatureExtractor()
        empty = ext.medical_features({"summary": {}, "global_health": {}}, {})
        assert empty["global_alert_count"] == pytest.approx(0.0)
        assert empty["active_sop_count"] == pytest.approx(0.0)

        rich = ext.medical_features(
            {
                "summary": {"sick_call_count": 3, "symptomatic": 2},
                "global_health": {"alerts": ["a", "b", "c"]},
                "active_protocols": ["SOP-1", "SOP-2"],
            },
            {"biodefense_weight": 2.0},
        )
        assert rich["global_alert_count"] == pytest.approx(3.0)
        assert rich["active_sop_count"] == pytest.approx(2.0)
        assert rich["sick_call_count"] == pytest.approx(3.0)
        assert rich["biodefense_weight"] == pytest.approx(2.0)
        assert rich["global_alert_count"] > empty["global_alert_count"]
        assert rich["active_sop_count"] > empty["active_sop_count"]


class TestAgentFeatures:
    def test_missing_vs_present_lived_experience(self) -> None:
        ext = UtilityFeatureExtractor()
        lived = AgentLivedExperienceStore()
        missing = ext.agent_features(99, lived, {})
        assert missing == {"severity_belief": 0.0}

        lived.experiences[1] = AgentLivedExperience(
            agent_id=1,
            sick_call_epochs=[1, 2],
            confinement_epochs=[3],
            close_contact_ids=[4, 5, 6],
            wearable_summary={"anomaly_count": 7},
        )
        info = {"1": {"severity_belief": 0.4, "trust_command": 0.8}}
        present = ext.agent_features(1, lived, info)
        assert present["severity_belief"] == pytest.approx(0.4)
        assert present["trust_command"] == pytest.approx(0.8)
        assert present["sick_call_count"] == pytest.approx(2.0)
        assert present["confinement_count"] == pytest.approx(1.0)
        assert present["close_contact_count"] == pytest.approx(3.0)
        assert present["wearable_anomaly"] == pytest.approx(7.0)
        assert present["severity_belief"] > missing["severity_belief"]
        assert all(v >= 0.0 for v in present.values())


class TestBuildBundle:
    def test_per_agent_vs_agent_classes(self) -> None:
        ext = UtilityFeatureExtractor()
        rep = ReputationTracker()
        lived = AgentLivedExperienceStore()
        lived.experiences[1] = AgentLivedExperience(agent_id=1)
        lived.experiences[2] = AgentLivedExperience(agent_id=2)
        cmd = {
            "summary": _pop_summary(infected=1),
            "cost_accounting": {},
            "stoplight_eligible_sop_ids": ["SOP-A"],
        }
        med = {"summary": {}, "global_health": {}, "active_protocols": []}
        info_state = {"agents": {"1": {"severity_belief": 0.2}, "2": {"severity_belief": 0.6}}}

        per_agent = ext.build_bundle(
            epoch=1,
            cruise_id="c0",
            command_obs=cmd,
            medical_obs=med,
            reputation=rep,
            lived=lived,
            information_state=info_state,
            incentives={},
            economics_weights={"k": 1},
            agent_granularity="per_agent",
        )
        assert "agents" in per_agent
        assert "agent_classes" not in per_agent
        assert set(per_agent["agents"]) == {"1", "2"}
        assert per_agent["epoch"] == 1
        assert 0.0 <= per_agent["command"]["features"]["infected_rate"] <= 1.0

        by_class = ext.build_bundle(
            epoch=1,
            cruise_id="c0",
            command_obs=cmd,
            medical_obs=med,
            reputation=rep,
            lived=lived,
            information_state=info_state,
            incentives={},
            economics_weights={"k": 1},
            agent_granularity="agent_classes",
        )
        assert "agent_classes" in by_class
        assert "agents" not in by_class
        mean_belief = by_class["agent_classes"]["unknown"]["mean_severity_belief"]
        assert 0.0 <= mean_belief <= 1.0
        assert mean_belief == pytest.approx(0.4)  # (0.2 + 0.6) / 2
