"""Weighted class-pair interaction rules for social/contact hooks."""

from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from simulation_utils.paths import REPO_ROOT, load_validated_json


@dataclass
class ClassInteractionMatrix:
    """Class-pair interaction weights, indexed by the pair they apply to.

    ``pairs`` is the document order as loaded; the index and the resolved
    weight cache are built from it at construction, so a matrix is read-only
    once built.
    """

    pairs: list[dict[str, Any]] = field(default_factory=list)
    _by_class_pair: dict[tuple[Any, Any], tuple[tuple[frozenset[str] | None, float], ...]] = field(
        init=False, repr=False, compare=False, default_factory=dict,
    )
    _weight_cache: dict[tuple[str, str, str], float] = field(
        init=False, repr=False, compare=False, default_factory=dict,
    )

    def __post_init__(self) -> None:
        grouped: dict[tuple[Any, Any], list[tuple[frozenset[str] | None, float]]] = defaultdict(list)
        for pair in self.pairs:
            zones = pair.get("context_zones", [])
            grouped[(pair.get("from_class"), pair.get("to_class"))].append(
                (frozenset(zones) if zones else None, float(pair.get("weight", 0.0))),
            )
        self._by_class_pair = {key: tuple(rules) for key, rules in grouped.items()}
        self._weight_cache = {}

    @classmethod
    def from_json(cls, path: str) -> ClassInteractionMatrix:
        data = load_validated_json(path, "class_interactions.schema.json", allowed_roots=(REPO_ROOT,))
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
        key = (from_class, to_class, zone)
        cached = self._weight_cache.get(key)
        if cached is not None:
            return cached
        best = 0.0
        for zones, weight in self._by_class_pair.get((from_class, to_class), ()):
            if zones is not None and zone not in zones:
                continue
            best = max(best, weight)
        self._weight_cache[key] = best
        return best

    def validate_zones(self, zone_ids: set[str], report_errors: list[str]) -> None:
        for i, pair in enumerate(self.pairs):
            for z in pair.get("context_zones", []):
                if z not in zone_ids:
                    report_errors.append(
                        f"pairs[{i}].context_zones: unknown zone {z!r}",
                    )
