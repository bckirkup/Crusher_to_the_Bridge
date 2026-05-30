"""Policy interfaces and hierarchical decision rounds."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from decision_engine.actions import Action, ActionEnvelope
from decision_engine.experience import ExperienceStore
from decision_engine.observation import ObservationModel, ObservationView


class Policy(ABC):
    @abstractmethod
    def decide(self, obs: ObservationView, experience: ExperienceStore) -> list[Action]:
        ...


class RuleBasedPolicy(Policy):
    """Default no-op policy for scaffolding and tests."""

    def decide(self, obs: ObservationView, experience: ExperienceStore) -> list[Action]:
        return [{"kind": "noop"}]


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
