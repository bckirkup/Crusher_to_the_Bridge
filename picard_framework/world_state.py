"""
WorldState — mutable ship simulation state bundle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from orchestrator_types import ObservationEngine, ProtocolContext, SimulationState


@dataclass
class WorldState:
    """Live objects and epoch-carried state for one ship simulation."""

    simulation: SimulationState
    observation: ObservationEngine | None = None
    protocol: ProtocolContext | None = None
    decisions_log: list[dict[str, Any]] = field(default_factory=list)

    @property
    def trigger_status(self) -> str:
        return self.simulation.trigger_status

    @property
    def simulation_history(self) -> list[dict[str, Any]]:
        return self.simulation.simulation_history
