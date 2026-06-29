"""Per-agent lived experience store for population-level decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from decision_engine.agent_profile import AgentProfile


@dataclass
class AgentLivedExperience:
    agent_id: int
    sick_call_epochs: list[int] = field(default_factory=list)
    confinement_epochs: list[int] = field(default_factory=list)
    perceived_sop_ids: list[str] = field(default_factory=list)
    close_contact_ids: list[int] = field(default_factory=list)
    wearable_summary: dict[str, Any] = field(default_factory=dict)
    symptom_presentation: str = "asymptomatic"
    infection_state: str = "susceptible"
    chronic_disease_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "sick_call_epochs": list(self.sick_call_epochs),
            "confinement_epochs": list(self.confinement_epochs),
            "perceived_sop_ids": list(self.perceived_sop_ids),
            "close_contact_ids": list(self.close_contact_ids),
            "wearable_summary": dict(self.wearable_summary),
            "symptom_presentation": self.symptom_presentation,
            "infection_state": self.infection_state,
            "chronic_disease_ids": list(self.chronic_disease_ids),
        }


@dataclass
class AgentLivedExperienceStore:
    experiences: dict[int, AgentLivedExperience] = field(default_factory=dict)
    sop_announcements: list[str] = field(default_factory=list)

    def ensure_agent(self, agent_id: int) -> AgentLivedExperience:
        if agent_id not in self.experiences:
            self.experiences[agent_id] = AgentLivedExperience(agent_id=agent_id)
        return self.experiences[agent_id]

    def _update_agent_experience(
        self,
        epoch: int,
        ag: dict[str, Any],
        sick_ids: set[int],
        sop_ids: list[str],
        quarantined_ids: set[int],
        isolated_ids: set[int],
        contact_adjacency: dict[int, dict[int, float]],
        agent_wearable: dict[Any, dict[str, Any]],
    ) -> None:
        aid = int(ag["agent_id"])
        exp = self.ensure_agent(aid)
        exp.symptom_presentation = ag.get("symptom_presentation", "asymptomatic")
        exp.infection_state = ag.get("infection_state", "susceptible")
        if "chronic_disease_ids" in ag and not exp.chronic_disease_ids:
            exp.chronic_disease_ids = list(ag["chronic_disease_ids"])
        if aid in sick_ids:
            exp.sick_call_epochs.append(epoch)
        if aid in quarantined_ids or aid in isolated_ids:
            exp.confinement_epochs.append(epoch)
        for sop_id in sop_ids:
            if sop_id and sop_id not in exp.perceived_sop_ids:
                exp.perceived_sop_ids.append(sop_id)
        nbrs = contact_adjacency.get(aid, {})
        exp.close_contact_ids = sorted(int(x) for x in nbrs.keys())
        wkey = str(aid)
        if wkey in agent_wearable:
            exp.wearable_summary = dict(agent_wearable[wkey].get("summary", {}))
            exp.wearable_summary["fever"] = agent_wearable[wkey].get("fever", False)
            exp.wearable_summary["anomaly_count"] = agent_wearable[wkey].get(
                "anomaly_count", 0,
            )
        elif aid in agent_wearable:
            exp.wearable_summary = dict(agent_wearable[aid].get("summary", {}))

    def update(
        self,
        epoch: int,
        agents: list[dict[str, Any]],
        syn_result: dict[str, Any] | None,
        active_protocols: list[dict[str, Any]],
        quarantined_ids: set[int],
        isolated_ids: set[int],
        contact_adjacency: dict[int, dict[int, float]],
        wearable_result: dict[str, Any] | None,
        _profiles: dict[int, AgentProfile] | None = None,
    ) -> None:
        sick_ids = set(syn_result.get("sick_call_agents", [])) if syn_result else set()
        sop_ids = [p.get("protocol_id", "") for p in active_protocols if p.get("protocol_id")]
        self.sop_announcements = [
            f"{p.get('protocol_id')}: {p.get('name', '')}" for p in active_protocols
        ]

        agent_wearable = (
            wearable_result.get("agent_results", {}) if wearable_result else {}
        )

        for ag in agents:
            self._update_agent_experience(
                epoch, ag, sick_ids, sop_ids,
                quarantined_ids, isolated_ids,
                contact_adjacency, agent_wearable,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "sop_announcements": list(self.sop_announcements),
            "agents": {
                str(k): v.to_dict() for k, v in self.experiences.items()
            },
        }
