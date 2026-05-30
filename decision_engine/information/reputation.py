"""Ship and class-level reputation tracking within a cruise."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ReputationTracker:
    trust_command: float = 0.7
    trust_medical: float = 0.75
    corporate_reputation_risk: float = 0.0
    class_trust_command: dict[str, float] = field(default_factory=dict)
    class_trust_medical: dict[str, float] = field(default_factory=dict)

    def apply_config(self, config: dict[str, Any]) -> None:
        self.trust_command = float(config.get("initial_trust_command", self.trust_command))
        self.trust_medical = float(config.get("initial_trust_medical", self.trust_medical))

    def on_confinement_spike(self, config: dict[str, Any], rate: float) -> None:
        delta = float(config.get("reputation_command_delta_on_confinement_spike", -0.02))
        self.trust_command = max(0.0, min(1.0, self.trust_command + delta * rate))
        self.corporate_reputation_risk = min(1.0, self.corporate_reputation_risk + 0.05 * rate)

    def on_surveillance_emphasis(self, config: dict[str, Any]) -> None:
        delta = float(config.get("reputation_medical_delta_on_test_cadence", 0.01))
        self.trust_medical = max(0.0, min(1.0, self.trust_medical + delta))

    def on_corporate_stance(self, stance: float) -> None:
        self.corporate_reputation_risk = max(0.0, min(1.0, stance))

    def update_class_slice(self, agent_class: str, command_trust: float, medical_trust: float) -> None:
        self.class_trust_command[agent_class] = command_trust
        self.class_trust_medical[agent_class] = medical_trust

    def to_dict(self) -> dict[str, Any]:
        return {
            "trust_command": round(self.trust_command, 4),
            "trust_medical": round(self.trust_medical, 4),
            "corporate_reputation_risk": round(self.corporate_reputation_risk, 4),
            "class_trust_command": {
                k: round(v, 4) for k, v in self.class_trust_command.items()
            },
            "class_trust_medical": {
                k: round(v, 4) for k, v in self.class_trust_medical.items()
            },
        }
