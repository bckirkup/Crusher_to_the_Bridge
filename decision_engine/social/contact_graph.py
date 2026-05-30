"""Per-epoch contact graph from colocation and contact tracing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from decision_engine.social.class_interactions import ClassInteractionMatrix


@dataclass
class ContactGraphBuilder:
    """Build weighted adjacency for information diffusion."""

    agent_adjacency: dict[int, dict[int, float]] = field(default_factory=dict)
    zone_colocation: dict[str, list[int]] = field(default_factory=dict)

    def update(
        self,
        agents: list[dict[str, Any]],
        contact_tracing: dict[str, Any] | None,
        class_matrix: ClassInteractionMatrix | None = None,
        agent_classes: dict[int, str] | None = None,
    ) -> dict[int, dict[int, float]]:
        self.agent_adjacency = {}
        self.zone_colocation = {}
        classes = agent_classes or {
            int(a["agent_id"]): a.get("agent_class", "unknown") for a in agents
        }

        for ag in agents:
            aid = int(ag["agent_id"])
            loc = ag.get("location") or ""
            if loc:
                self.zone_colocation.setdefault(loc, []).append(aid)

        for loc, ids in self.zone_colocation.items():
            for i, a_id in enumerate(ids):
                for b_id in ids[i + 1:]:
                    w = 1.0
                    if class_matrix:
                        ca = classes.get(a_id, "unknown")
                        cb = classes.get(b_id, "unknown")
                        w = max(
                            class_matrix.interaction_weight(ca, cb, loc),
                            class_matrix.interaction_weight(cb, ca, loc),
                            0.1,
                        )
                    self._add_edge(a_id, b_id, w)

        if contact_tracing:
            for exp in contact_tracing.get("shared_room_exposures", []):
                target = exp.get("target_agent_id") or exp.get("agent_id")
                sources = exp.get("source_agent_ids", [])
                if target is None:
                    continue
                tid = int(target)
                for sid in sources:
                    self._add_edge(tid, int(sid), 1.5)

        return self.agent_adjacency

    def _add_edge(self, a: int, b: int, weight: float) -> None:
        if a == b:
            return
        self.agent_adjacency.setdefault(a, {})
        self.agent_adjacency.setdefault(b, {})
        self.agent_adjacency[a][b] = max(self.agent_adjacency[a].get(b, 0.0), weight)
        self.agent_adjacency[b][a] = max(self.agent_adjacency[b].get(a, 0.0), weight)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_adjacency": {
                str(k): {str(v): round(w, 4) for v, w in nbrs.items()}
                for k, nbrs in self.agent_adjacency.items()
            },
        }
