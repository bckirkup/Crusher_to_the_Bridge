"""Ship systems health and repair labor (``docs/ship_functions/ship_function_capacity_spec.md`` §5).

A small registry of named systems with a health state, beside
``crew_duty_exclusion.py`` in ownership style: data and transitions, no
epidemiological content. Each system's ``health ∈ [0,1]`` degrades at a
declared rate per day while the voyage runs and is repaired by watch-hours
drawn from the crew class the entry names — the same pool the function
capacity read (§4) scores, so a depleted engineering watch falls behind on
repairs and every function depending on that system degrades with it.

Discipline, matching the tracker it sits beside:

* Every rate is a declared operational parameter. Initial health,
  degradation rates, and repair rates carry a provenance declaration on the
  config entry; where no maritime source exists they ship as null-sourced
  weak ranges and may never be tuned against an anchor.
* Repair labor is *residual* watch capacity: crew standing a declared
  function watch are not also turning wrenches. The repair pool for a
  class is the watch-hours it delivers beyond the summed
  ``required_on_watch`` of every function instance drawing it.
* An absent or disabled block means no state and no draws: a platform
  without ``ship_systems`` runs bit-identical.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass(frozen=True)
class ShipSystemSpec:
    """One system as configured: degradation, repair channel, effects."""

    system_id: str
    health_start: float = 1.0
    degradation_rate_per_day: float = 0.0
    repair_labor_class: str = ""
    repair_rate_per_person_hour: float = 0.0
    failure_threshold: float = 0.0
    effects: dict[str, dict[str, float]] = field(default_factory=dict)
    repair_priority: int = 0

    @classmethod
    def from_config(cls, entry: dict[str, Any], index: int) -> "ShipSystemSpec":
        """Build the spec from one ``ship_systems`` list element."""
        if not isinstance(entry, dict):
            raise ValueError(f"ship_systems[{index}] must be a mapping")
        system_id = str(entry.get("system_id") or "")
        if not system_id:
            raise ValueError(f"ship_systems[{index}] requires system_id")
        degradation = dict(entry.get("degradation") or {})
        repair = dict(entry.get("repair") or {})
        spec = cls(
            system_id=system_id,
            health_start=float(entry.get("health_start", 1.0)),
            degradation_rate_per_day=float(degradation.get("rate_per_day", 0.0)),
            repair_labor_class=str(repair.get("labor_class", "") or ""),
            repair_rate_per_person_hour=float(
                repair.get("rate_per_person_hour", 0.0),
            ),
            failure_threshold=float(entry.get("failure_threshold", 0.0)),
            effects={
                str(fid): dict(effect)
                for fid, effect in dict(entry.get("effects") or {}).items()
            },
            repair_priority=int(
                entry.get("repair_priority", index),
            ),
        )
        spec.validate(index)
        return spec

    def validate(self, index: int) -> None:
        """Refuse out-of-range values rather than simulate them silently."""
        for name, value in (
            ("health_start", self.health_start),
            ("failure_threshold", self.failure_threshold),
        ):
            if not np.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"ship_systems[{index}].{name} must lie in [0, 1]: {value!r}",
                )
        # health_start may sit below failure_threshold: a voyage can depart
        # with a failed system.
        for name, value in (
            ("degradation.rate_per_day", self.degradation_rate_per_day),
            ("repair.rate_per_person_hour", self.repair_rate_per_person_hour),
        ):
            if not np.isfinite(value) or value < 0.0:
                raise ValueError(
                    f"ship_systems[{index}].{name} must be finite and "
                    f"non-negative: {value!r}",
                )
        for fid, effect in self.effects.items():
            mult = float((effect or {}).get("capacity_multiplier_at_failure", 0.0))
            if not np.isfinite(mult):
                raise ValueError(
                    f"ship_systems[{index}].effects.{fid}."
                    f"capacity_multiplier_at_failure must be finite: {mult!r}",
                )

    def capacity_multiplier(self, function_id: str) -> float:
        """What this failed system multiplies the named function's capacity by."""
        effect = self.effects.get(function_id) or {}
        return float(effect.get("capacity_multiplier_at_failure", 1.0))


class ShipSystemsState:
    """Live health registry for one voyage's declared systems."""

    def __init__(self, specs: list[ShipSystemSpec]) -> None:
        self._specs = sorted(specs, key=lambda spec: spec.repair_priority)
        self.health: dict[str, float] = {
            spec.system_id: spec.health_start for spec in specs
        }

    @property
    def specs(self) -> tuple[ShipSystemSpec, ...]:
        return tuple(self._specs)

    @property
    def system_ids(self) -> list[str]:
        return [spec.system_id for spec in self._specs]

    def is_failed(self, system_id: str) -> bool:
        spec = self._spec(system_id)
        return spec is not None and self.health[system_id] < spec.failure_threshold

    def capacity_multiplier(self, function_id: str) -> float:
        """Product of the failed systems' declared multipliers on *function_id*."""
        multiplier = 1.0
        for spec in self._specs:
            if self.is_failed(spec.system_id):
                multiplier *= spec.capacity_multiplier(function_id)
        return multiplier

    def step(
        self,
        day_fraction_per_epoch: float,
        repair_hours_by_class: dict[str, float],
    ) -> None:
        """Degrade everything, then spend repair labor in priority order.

        ``repair_hours_by_class`` is the residual on-watch person-hours each
        crew class has beyond declared watch demand — the hours it can spend
        below decks instead of standing a function watch.
        """
        for spec in self._specs:
            self.health[spec.system_id] = max(
                0.0,
                self.health[spec.system_id]
                - spec.degradation_rate_per_day * day_fraction_per_epoch,
            )
        pools = dict(repair_hours_by_class)
        for spec in self._specs:
            if not spec.repair_labor_class or spec.repair_rate_per_person_hour <= 0.0:
                continue
            deficit = 1.0 - self.health[spec.system_id]
            if deficit <= 0.0:
                continue
            available = pools.get(spec.repair_labor_class, 0.0)
            if available <= 0.0:
                continue
            hours_needed = deficit / spec.repair_rate_per_person_hour
            spent = min(available, hours_needed)
            self.health[spec.system_id] = min(
                1.0,
                self.health[spec.system_id]
                + spent * spec.repair_rate_per_person_hour,
            )
            pools[spec.repair_labor_class] = available - spent

    def snapshot(self) -> dict[str, dict[str, float | bool]]:
        """Per-system telemetry: health and whether the failure threshold is crossed."""
        return {
            spec.system_id: {
                "health": self.health[spec.system_id],
                "failed": self.is_failed(spec.system_id),
            }
            for spec in self._specs
        }

    def _spec(self, system_id: str) -> ShipSystemSpec | None:
        for spec in self._specs:
            if spec.system_id == system_id:
                return spec
        return None


def build_ship_systems(
    block: Any,
) -> ShipSystemsState | None:
    """Assemble the systems registry from a ``ship_systems`` config list.

    Returns None for an absent/empty block — a platform without declared
    systems has no state at all.
    """
    if not block:
        return None
    if not isinstance(block, list):
        raise ValueError("ship_systems must be a list of system entries")
    specs = [
        ShipSystemSpec.from_config(entry, index)
        for index, entry in enumerate(block)
    ]
    seen: set[str] = set()
    for spec in specs:
        if spec.system_id in seen:
            raise ValueError(f"ship_systems: duplicate system_id {spec.system_id!r}")
        seen.add(spec.system_id)
    return ShipSystemsState(specs)
