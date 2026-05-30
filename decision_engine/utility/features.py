"""Deterministic utility feature extraction (weights applied externally)."""

from __future__ import annotations

from typing import Any

from decision_engine.information.reputation import ReputationTracker
from decision_engine.lived_experience import AgentLivedExperienceStore


class UtilityFeatureExtractor:
    """Build feature dicts per role for external optimization."""

    def command_features(
        self,
        command_obs: dict[str, Any],
        reputation: ReputationTracker,
        incentives: dict[str, float],
    ) -> dict[str, float]:
        summary = command_obs.get("summary", {})
        cost = command_obs.get("cost_accounting", {})
        pop = max(
            1,
            int(summary.get("susceptible", 0))
            + int(summary.get("infected", 0))
            + int(summary.get("recovered", 0))
            + int(summary.get("immune", 0)),
        )
        infected_rate = float(summary.get("infected", 0)) / pop
        symptomatic_rate = float(summary.get("symptomatic", 0)) / pop
        return {
            "infected_rate": infected_rate,
            "symptomatic_rate": symptomatic_rate,
            "budget_spent_usd": float(cost.get("total_financial_usd", 0.0)),
            "operational_impact_epoch": float(cost.get("operational_impact_epoch", 0.0)),
            "operational_impact_cumulative": float(
                cost.get("operational_impact_cumulative", 0.0),
            ),
            "reputation_risk": reputation.corporate_reputation_risk,
            "trust_command": reputation.trust_command,
            "biodefense_weight": float(incentives.get("biodefense_weight", 1.0)),
            "budget_weight": float(incentives.get("budget_weight", 0.1)),
        }

    def medical_features(
        self,
        medical_obs: dict[str, Any],
        incentives: dict[str, float],
    ) -> dict[str, float]:
        summary = medical_obs.get("summary", {})
        gh = medical_obs.get("global_health", {})
        return {
            "sick_call_count": float(summary.get("sick_call_count", 0)),
            "symptomatic": float(summary.get("symptomatic", 0)),
            "global_alert_count": float(len(gh.get("alerts", []))),
            "active_sop_count": float(len(medical_obs.get("active_protocols", []))),
            "biodefense_weight": float(incentives.get("biodefense_weight", 1.0)),
        }

    def agent_features(
        self,
        agent_id: int,
        lived: AgentLivedExperienceStore,
        information_agents: dict[str, Any],
    ) -> dict[str, float]:
        exp = lived.experiences.get(agent_id)
        inf = information_agents.get(str(agent_id), {})
        if exp is None:
            return {"severity_belief": 0.0}
        return {
            "severity_belief": float(inf.get("severity_belief", 0.1)),
            "trust_command": float(inf.get("trust_command", 0.7)),
            "sick_call_count": float(len(exp.sick_call_epochs)),
            "confinement_count": float(len(exp.confinement_epochs)),
            "close_contact_count": float(len(exp.close_contact_ids)),
            "wearable_anomaly": float(exp.wearable_summary.get("anomaly_count", 0)),
        }

    def build_bundle(
        self,
        epoch: int,
        cruise_id: str,
        command_obs: dict[str, Any],
        medical_obs: dict[str, Any],
        reputation: ReputationTracker,
        lived: AgentLivedExperienceStore,
        information_state: dict[str, Any],
        incentives: dict[str, float],
        economics_weights: dict[str, Any],
        agent_granularity: str = "per_agent",
    ) -> dict[str, Any]:
        cmd_f = self.command_features(command_obs, reputation, incentives)
        med_f = self.medical_features(medical_obs, incentives)
        bundle: dict[str, Any] = {
            "schema_version": "1.0.0",
            "epoch": epoch,
            "cruise_id": cruise_id,
            "command": {
                "features": cmd_f,
                "eligible_sops": command_obs.get("stoplight_eligible_sop_ids", []),
                "observation_ref": "command_view",
            },
            "medical": {
                "features": med_f,
                "global_health": medical_obs.get("global_health", {}),
                "directives": medical_obs.get("command_directives", []),
                "observation_ref": "medical_view",
            },
            "economics_weights": economics_weights,
        }
        info_agents = information_state.get("agents", {})
        if agent_granularity == "per_agent":
            bundle["agents"] = {
                str(aid): {
                    "features": self.agent_features(aid, lived, info_agents),
                }
                for aid in lived.experiences
            }
        else:
            by_class: dict[str, list[dict[str, float]]] = {}
            for aid, exp in lived.experiences.items():
                cls = "unknown"
                by_class.setdefault(cls, []).append(
                    self.agent_features(aid, lived, info_agents),
                )
            bundle["agent_classes"] = {
                cls: {
                    "mean_severity_belief": sum(
                        f["severity_belief"] for f in feats
                    ) / max(len(feats), 1),
                }
                for cls, feats in by_class.items()
            }
        return bundle
