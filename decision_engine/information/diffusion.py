"""Information contagion and per-agent belief state."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from decision_engine.information.reputation import ReputationTracker


@dataclass
class InformationState:
    agent_id: int
    severity_belief: float = 0.1
    trust_command: float = 0.7
    trust_medical: float = 0.75
    rumor_exposure: float = 0.0
    reputation_peer: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "severity_belief": round(self.severity_belief, 4),
            "trust_command": round(self.trust_command, 4),
            "trust_medical": round(self.trust_medical, 4),
            "rumor_exposure": round(self.rumor_exposure, 4),
            "reputation_peer": round(self.reputation_peer, 4),
        }


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = pow(2.718281828, -x)
        return 1.0 / (1.0 + z)
    z = pow(2.718281828, x)
    return z / (1.0 + z)


@dataclass
class InformationDiffusionEngine:
    config: dict[str, Any] = field(default_factory=dict)
    agent_states: dict[int, InformationState] = field(default_factory=dict)
    reputation: ReputationTracker = field(default_factory=ReputationTracker)
    public_messages: list[str] = field(default_factory=list)

    @classmethod
    def from_config_path(cls, path: str) -> InformationDiffusionEngine:
        with open(path, encoding="utf-8") as fh:
            cfg = json.load(fh)
        eng = cls(config=cfg)
        eng.reputation.apply_config(cfg)
        return eng

    @classmethod
    def default_path(cls, repo_root: str) -> str:
        return os.path.join(
            repo_root,
            "presidio",
            "data",
            "social",
            "information_diffusion_default.json",
        )

    def initialize_agents(
        self,
        agent_ids: list[int],
        agent_classes: dict[int, str],
        overrides: dict[str, Any] | None = None,
    ) -> None:
        ov = overrides or {}
        for aid in agent_ids:
            self.agent_states[aid] = InformationState(
                agent_id=aid,
                severity_belief=float(ov.get("severity_belief", self.config.get(
                    "initial_severity_belief", 0.1,
                ))),
                trust_command=float(self.config.get("initial_trust_command", 0.7)),
                trust_medical=float(self.config.get("initial_trust_medical", 0.75)),
            )

    def seed_public_message(self, message: str) -> None:
        self.public_messages.append(message)
        bump = float(self.config.get("message_decay", 0.05)) + 0.05
        for state in self.agent_states.values():
            state.rumor_exposure = min(1.0, state.rumor_exposure + bump)

    def step(
        self,
        adjacency: dict[int, dict[int, float]],
        agent_classes: dict[int, str],
        trigger_status: str,
        confinement_rate: float,
    ) -> dict[str, Any]:
        alpha = float(self.config.get("alpha", 0.25))
        homophily = float(self.config.get("homophily_strength", 0.15))
        decay = float(self.config.get("message_decay", 0.05))

        status_signal = {"BASELINE": 0.0, "SUSPECTED": 0.35, "CONFIRMED": 0.7}.get(
            trigger_status, 0.0,
        )

        if confinement_rate > 0.05:
            self.reputation.on_confinement_spike(self.config, confinement_rate)

        new_states: dict[int, InformationState] = {}
        for aid, state in self.agent_states.items():
            neighbors = adjacency.get(aid, {})
            if not neighbors:
                agg = status_signal
            else:
                total_w = sum(neighbors.values())
                agg = 0.0
                for nid, w in neighbors.items():
                    nstate = self.agent_states.get(nid)
                    if nstate is None:
                        continue
                    same_class = agent_classes.get(aid) == agent_classes.get(nid)
                    hw = w * (1.0 + homophily if same_class else 1.0)
                    agg += hw * nstate.severity_belief
                agg = agg / max(total_w, 1e-6)
                agg = 0.5 * agg + 0.5 * status_signal

            severity = (1.0 - alpha) * state.severity_belief + alpha * _sigmoid(agg * 4 - 2)
            rumor = max(0.0, state.rumor_exposure - decay)
            new_states[aid] = InformationState(
                agent_id=aid,
                severity_belief=min(1.0, max(0.0, severity)),
                trust_command=state.trust_command,
                trust_medical=state.trust_medical,
                rumor_exposure=rumor,
                reputation_peer=state.reputation_peer,
            )

        self.agent_states = new_states
        return self.to_dict()

    def to_dict(self) -> dict[str, Any]:
        return {
            "public_messages": list(self.public_messages),
            "reputation": self.reputation.to_dict(),
            "agents": {
                str(k): v.to_dict() for k, v in self.agent_states.items()
            },
        }
