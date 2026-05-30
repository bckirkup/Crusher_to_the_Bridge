"""Partial observability views per actor role."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ObservationView:
    """Incomplete information snapshot for one actor at one epoch."""

    actor_id: str
    role: str
    epoch: int
    local: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    stoplights: dict[str, Any] = field(default_factory=dict)


class ObservationModel:
    """Build role-specific views from a host-provided public snapshot."""

    @staticmethod
    def build(
        public_snapshot: dict[str, Any],
        actor_id: str,
        role: str,
    ) -> ObservationView:
        epoch = int(public_snapshot.get("epoch", 0))
        agents = public_snapshot.get("agents", [])
        summary = public_snapshot.get("summary", {})
        stoplights = public_snapshot.get("stoplights", {})

        local: dict[str, Any] = {}
        if role == "crew_agent":
            try:
                aid = int(actor_id)
            except ValueError:
                aid = None
            if aid is not None:
                for ag in agents:
                    if ag.get("agent_id") == aid:
                        local = {
                            "location": ag.get("location"),
                            "infection_state": ag.get("infection_state"),
                            "symptom_presentation": ag.get("symptom_presentation"),
                        }
                        break
        elif role == "medical_officer":
            local = {
                "observation_engine": public_snapshot.get("observation_engine", {}),
                "trigger_status": public_snapshot.get("trigger_status"),
            }
        elif role == "commanding_officer":
            local = {
                "cost_accounting": public_snapshot.get("cost_accounting", {}),
                "trigger_status": public_snapshot.get("trigger_status"),
            }

        return ObservationView(
            actor_id=actor_id,
            role=role,
            epoch=epoch,
            local=local,
            summary=summary,
            stoplights=stoplights,
        )
