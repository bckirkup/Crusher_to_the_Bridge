"""Policy interfaces and hierarchical decision rounds."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from decision_engine.actions import Action, ActionEnvelope
from decision_engine.experience import ExperienceStore
from decision_engine.views import ObservationModel, ObservationView
from telemetry_buffer.agent_axes import (
    agent_has_symptomatic_presentation,
    agent_is_isolated,
)


class Policy(ABC):
    @abstractmethod
    def decide(self, obs: ObservationView, experience: ExperienceStore) -> list[Action]:
        ...


class RuleBasedPolicy(Policy):
    """Default no-op policy for scaffolding and tests."""

    def decide(self, obs: ObservationView, experience: ExperienceStore) -> list[Action]:
        return [{"kind": "noop"}]


class ThresholdBeliefPolicy(Policy):
    """Per-agent sick-call / concealment from beliefs and symptom presentation."""

    def __init__(
        self,
        severity_report_threshold: float = 0.35,
        trust_report_floor: float = 0.4,
        hide_trust_ceiling: float = 0.35,
        hide_severity_ceiling: float = 0.25,
    ) -> None:
        self.severity_report_threshold = severity_report_threshold
        self.trust_report_floor = trust_report_floor
        self.hide_trust_ceiling = hide_trust_ceiling
        self.hide_severity_ceiling = hide_severity_ceiling

    def decide(self, obs: ObservationView, experience: ExperienceStore) -> list[Action]:
        local = obs.local
        inf = local.get("information_state", {})
        severity = float(inf.get("severity_belief", 0.1))
        trust_medical = float(inf.get("trust_medical", 0.75))
        presentation = local.get("symptom_presentation", "")
        infection = local.get("infection_state", "")

        if agent_is_isolated({"compliance_status": local.get("compliance_status", "")}):
            return [{"kind": "noop"}]

        symptomatic = (
            agent_has_symptomatic_presentation({"symptom_presentation": presentation})
            or presentation in ("mild", "symptomatic", "severe")
        )
        if not symptomatic and infection not in ("infected",):
            return [{"kind": "noop"}]

        try:
            aid = int(obs.actor_id)
        except ValueError:
            return [{"kind": "noop"}]

        if trust_medical <= self.hide_trust_ceiling and severity <= self.hide_severity_ceiling:
            return [{"kind": "hide_symptoms", "agent_id": aid}]
        if severity >= self.severity_report_threshold and trust_medical >= self.trust_report_floor:
            return [{"kind": "report_sick_call", "agent_id": aid}]
        return [{"kind": "noop"}]


class CommandThresholdPolicy(Policy):
    """Command escalation from OIS, infection rates, and eligible SOPs."""

    def __init__(
        self,
        ois_escalation_threshold: float = 15.0,
        infected_rate_threshold: float = 0.05,
        max_authorized_sops: int = 5,
    ) -> None:
        self.ois_escalation_threshold = ois_escalation_threshold
        self.infected_rate_threshold = infected_rate_threshold
        self.max_authorized_sops = max_authorized_sops

    def decide(self, obs: ObservationView, experience: ExperienceStore) -> list[Action]:
        local = obs.local
        cost = local.get("cost_accounting", {})
        summary = obs.summary
        ois_cum = float(local.get("operational_impact_cumulative", cost.get(
            "operational_impact_cumulative", 0.0,
        )))
        pop = max(
            1,
            int(summary.get("susceptible", 0))
            + int(summary.get("infected", 0))
            + int(summary.get("recovered", 0))
            + int(summary.get("immune", 0)),
        )
        infected_rate = float(summary.get("infected", 0)) / pop
        eligible = local.get("stoplight_eligible_sop_ids", [])
        actions: list[Action] = []

        if ois_cum >= self.ois_escalation_threshold or infected_rate >= self.infected_rate_threshold:
            if eligible:
                actions.append({
                    "kind": "authorize_sop_subset",
                    "protocol_ids": eligible[: self.max_authorized_sops],
                })
            actions.append({"kind": "set_surveillance_cadence", "pcr_cadence": 2})
        if not actions:
            actions.append({"kind": "noop"})
        return actions


class MedicalThresholdPolicy(Policy):
    """Medical officer recommends verification when syndromic signal is elevated."""

    def __init__(self, sick_call_threshold: int = 3) -> None:
        self.sick_call_threshold = sick_call_threshold

    def decide(self, obs: ObservationView, experience: ExperienceStore) -> list[Action]:
        summary = obs.summary
        sick = int(summary.get("sick_call_count", 0))
        if sick >= self.sick_call_threshold:
            zones = obs.local.get("high_traffic_zones", [])
            if zones:
                return [{"kind": "order_verification_test", "zone": zones[0]}]
            return [{"kind": "request_sop_activation", "protocol_id": "SOP-002"}]
        return [{"kind": "noop"}]


def build_policies_from_config(cfg: dict[str, Any]) -> tuple[Policy, Policy, Policy]:
    """Construct command, medical, and population policies from config."""
    de_cfg = cfg.get("decision_engine", {})
    pop_kind = str(de_cfg.get("population_policy", "threshold_belief"))
    cmd_kind = str(de_cfg.get("command_policy", "threshold"))
    med_kind = str(de_cfg.get("medical_policy", "threshold"))

    def _pop() -> Policy:
        if pop_kind in ("noop", "rule_based"):
            return RuleBasedPolicy()
        params = de_cfg.get("threshold_belief", {})
        return ThresholdBeliefPolicy(**{k: v for k, v in params.items() if k in (
            "severity_report_threshold", "trust_report_floor",
            "hide_trust_ceiling", "hide_severity_ceiling",
        )})

    def _cmd() -> Policy:
        if cmd_kind in ("noop", "rule_based"):
            return RuleBasedPolicy()
        params = de_cfg.get("command_threshold", {})
        return CommandThresholdPolicy(**{k: v for k, v in params.items() if k in (
            "ois_escalation_threshold", "infected_rate_threshold", "max_authorized_sops",
        )})

    def _med() -> Policy:
        if med_kind in ("noop", "rule_based"):
            return RuleBasedPolicy()
        params = de_cfg.get("medical_threshold", {})
        return MedicalThresholdPolicy(**{k: v for k, v in params.items() if k in (
            "sick_call_threshold",
        )})

    return _cmd(), _med(), _pop()


class DecisionRound:
    """Stackelberg-ordered decision pass: command → medical → crew sample."""

    def __init__(
        self,
        actor_roster: list[dict[str, Any]],
        policies: dict[str, Policy] | None = None,
    ) -> None:
        self.actor_roster = actor_roster
        self.policies = policies or {}
        self._order = ("commanding_officer", "medical_officer", "crew_agent")

    def solve(
        self,
        epoch: int,
        public_snapshot: dict[str, Any],
        experience: ExperienceStore,
    ) -> ActionEnvelope:
        envelope = ActionEnvelope(epoch=epoch)
        roster_sorted = sorted(
            self.actor_roster,
            key=lambda a: self._order.index(a.get("role", "crew_agent"))
            if a.get("role", "crew_agent") in self._order
            else 99,
        )
        for actor in roster_sorted:
            actor_id = str(actor.get("actor_id", actor.get("id", "unknown")))
            role = str(actor.get("role", "crew_agent"))
            obs = ObservationModel.build(public_snapshot, actor_id, role)
            policy = self.policies.get(actor_id) or self.policies.get(role)
            if policy is None:
                policy = RuleBasedPolicy()
            acts = policy.decide(obs, experience)
            if acts:
                envelope.actions[actor_id] = acts
        return envelope
