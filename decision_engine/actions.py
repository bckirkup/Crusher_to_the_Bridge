"""Action types and per-epoch envelopes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

Action = dict[str, Any]


@dataclass
class ActionEnvelope:
    """Per-epoch actions keyed by actor identifier."""

    epoch: int = 0
    actions: dict[str, list[Action]] = field(default_factory=dict)

    def merge(self, other: ActionEnvelope) -> ActionEnvelope:
        merged = dict(self.actions)
        for actor_id, acts in other.actions.items():
            merged.setdefault(actor_id, []).extend(acts)
        return ActionEnvelope(epoch=self.epoch, actions=merged)
