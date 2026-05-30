"""Shared per-epoch decision context for Stackelberg rounds."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EpochDecisionContext:
    epoch: int = 0
    command_directives: list[dict[str, Any]] = field(default_factory=list)
    authorized_sop_ids: list[str] | None = None
    corporate_communication_stance: float = 0.0
    medical_announcements: list[str] = field(default_factory=list)
    sop_announcements: list[str] = field(default_factory=list)
    sop_recommendations: list[str] = field(default_factory=list)

    def reset_ephemeral(self) -> None:
        """Clear per-epoch fields that must not accumulate across epochs."""
        self.command_directives.clear()
        self.medical_announcements.clear()
        self.sop_announcements.clear()
        self.sop_recommendations.clear()
        self.corporate_communication_stance = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "epoch": self.epoch,
            "command_directives": list(self.command_directives),
            "authorized_sop_ids": self.authorized_sop_ids,
            "corporate_communication_stance": self.corporate_communication_stance,
            "medical_announcements": list(self.medical_announcements),
            "sop_announcements": list(self.sop_announcements),
            "sop_recommendations": list(self.sop_recommendations),
        }
