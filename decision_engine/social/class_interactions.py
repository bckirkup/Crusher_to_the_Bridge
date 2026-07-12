"""Weighted class-pair interaction rules for social/contact hooks."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from simulation_utils.paths import validated_open

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class ClassInteractionMatrix:
    pairs: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_json(cls, path: str) -> ClassInteractionMatrix:
        with validated_open(path, allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
            data = json.load(fh)
        return cls(pairs=data.get("pairs", []))

    @classmethod
    def default_path(cls, repo_root: str) -> str:
        return os.path.join(
            repo_root,
            "presidio",
            "data",
            "social",
            "class_interactions_default.json",
        )

    def interaction_weight(
        self,
        from_class: str,
        to_class: str,
        zone: str,
    ) -> float:
        best = 0.0
        for pair in self.pairs:
            if pair.get("from_class") != from_class:
                continue
            if pair.get("to_class") != to_class:
                continue
            zones = pair.get("context_zones", [])
            if zones and zone not in zones:
                continue
            best = max(best, float(pair.get("weight", 0.0)))
        return best

    def validate_zones(self, zone_ids: set[str], report_errors: list[str]) -> None:
        for i, pair in enumerate(self.pairs):
            for z in pair.get("context_zones", []):
                if z not in zone_ids:
                    report_errors.append(
                        f"pairs[{i}].context_zones: unknown zone {z!r}",
                    )
