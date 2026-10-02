"""PPE wear-fatigue channel (ship_function_capacity_spec §7).

Sustained PPE wear degrades the wearer three ways: a ``fatigue_score``
accumulator fed by per-type wear-hours, fatigue-driven refusal that drops the
host's NPI reductions, and type-keyed endogenous conditions that present
through the existing symptomatic path. This module holds the declarations and
the per-epoch mechanics; the compliance-log writes stay in
``orchestrator_epoch.step_ppe_fatigue``, mirroring the crew-duty-exclusion
split between policy and state.

Two boundaries matter:

- **Off means absent.** ``ppe_fatigue.enabled: false`` (or no ``ppe_types``
  registry) leaves the step a no-op: no draw is consumed, no field is written,
  so a run that never declares the channel is bit-identical to one that
  declares it and disables it.
- **Declared, not fitted.** Every number here is an operational declaration
  carrying a source or an explicit NULL-SOURCE note at its definition in
  ``crusher_labs/config.yaml``; none may be tuned against an anchor.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from engines.non_pharmaceutical_interventions import resolve_npi

# Non-numeric scalar bounds shared by the registry and the policy block.
_NONNEGATIVE = "must be finite and non-negative"
_UNIT_INTERVAL = "must lie in [0, 1]"


def _finite_nonnegative(value: object, name: str) -> float:
    """Coerce a declared non-negative scalar, refusing odd types."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} {_NONNEGATIVE}, got {value!r}")
    number = float(value)
    if not np.isfinite(number) or number < 0.0:
        raise ValueError(f"{name} {_NONNEGATIVE}, got {value!r}")
    return number


def _unit_interval(value: object, name: str) -> float:
    """Coerce a declared probability or fraction."""
    number = _finite_nonnegative(value, name)
    if number > 1.0:
        raise ValueError(f"{name} {_UNIT_INTERVAL}, got {value!r}")
    return number


@dataclass(frozen=True)
class FatigueCondition:
    """One endogenous sequelae a PPE type may induce (spec §7.4).

    ``rate_per_wear_hour`` is a per-wear-hour onset hazard; ``symptomatic``
    routes onset into the symptomatic-presentation path so sick-call, duty
    exclusion and the VSP counters see it with no new machinery.
    """

    condition_id: str
    rate_per_wear_hour: float
    symptomatic: bool = True

    @classmethod
    def from_config(cls, raw: Mapping[str, object], name: str) -> FatigueCondition:
        if not isinstance(raw, Mapping):
            raise ValueError(f"{name} must be a mapping, got {raw!r}")
        condition_id = str(raw.get("condition_id") or "").strip()
        if not condition_id:
            raise ValueError(f"{name}.condition_id is required")
        return cls(
            condition_id=condition_id,
            rate_per_wear_hour=_finite_nonnegative(
                raw.get("rate_per_wear_hour"), f"{name}.rate_per_wear_hour",
            ),
            symptomatic=bool(raw.get("symptomatic", True)),
        )


@dataclass(frozen=True)
class PpeType:
    """One entry in the ``ppe_types`` registry (spec §7.1).

    ``dexterity_impairment`` is the share of the wearer's effective watch
    hours lost to manual-work impairment — the §5 repair-labor hook reads it
    off the agent; ``heat_load`` is declared for completeness and is not yet
    consumed.
    """

    type_id: str
    fatigue_rate_per_epoch: float
    heat_load: float
    dexterity_impairment: float
    fatigue_conditions: tuple[FatigueCondition, ...] = ()

    @classmethod
    def from_config(cls, type_id: str, raw: object) -> PpeType:
        name = f"ppe_types.{type_id}"
        if not isinstance(raw, Mapping):
            raise ValueError(f"{name} must be a mapping, got {raw!r}")
        conditions_raw = raw.get("fatigue_conditions") or ()
        if not isinstance(conditions_raw, (list, tuple)):
            raise ValueError(f"{name}.fatigue_conditions must be a list")
        return cls(
            type_id=str(type_id),
            fatigue_rate_per_epoch=_finite_nonnegative(
                raw.get("fatigue_rate_per_epoch"),
                f"{name}.fatigue_rate_per_epoch",
            ),
            heat_load=_finite_nonnegative(
                raw.get("heat_load"), f"{name}.heat_load",
            ),
            dexterity_impairment=_unit_interval(
                raw.get("dexterity_impairment"),
                f"{name}.dexterity_impairment",
            ),
            fatigue_conditions=tuple(
                FatigueCondition.from_config(c, f"{name}.fatigue_conditions[{i}]")
                for i, c in enumerate(conditions_raw)
            ),
        )


def resolve_ppe_types(cfg: Mapping[str, object] | None) -> dict[str, PpeType]:
    """Read ``cfg['ppe_types']`` into the typed registry.

    Absent returns an empty mapping, which is the whole off-switch: no type
    can be worn, so the channel produces nothing.
    """
    raw = (cfg or {}).get("ppe_types")
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise ValueError("ppe_types must be a mapping of type_id to declaration")
    return {
        str(type_id): PpeType.from_config(str(type_id), block)
        for type_id, block in raw.items()
    }


# The stock issue when a measure does not type its coverage: SOP-004's
# standard deployment. NULL-SOURCE (operational declaration, Grade C): the
# mildest registry member is the conservative default; a platform may name
# another via ``ppe_fatigue.default_ppe_type``.
DEFAULT_PPE_TYPE = "surgical_mask"


@dataclass(frozen=True)
class PpeFatiguePolicy:
    """The channel's run-level switches (spec §7.3 names the two draws)."""

    enabled: bool = False
    default_ppe_type: str = DEFAULT_PPE_TYPE
    fatigue_refusal_threshold: float = 0.0
    fatigue_refusal_probability_per_epoch: float = 0.0

    @classmethod
    def from_config(cls, cfg: Mapping[str, object] | None) -> PpeFatiguePolicy:
        block = cfg or {}
        if not isinstance(block, Mapping):
            raise ValueError("ppe_fatigue must be a mapping")
        policy = cls(
            enabled=bool(block.get("enabled", False)),
            default_ppe_type=str(block.get("default_ppe_type") or DEFAULT_PPE_TYPE),
            fatigue_refusal_threshold=_finite_nonnegative(
                block.get("fatigue_refusal_threshold", 0.0),
                "ppe_fatigue.fatigue_refusal_threshold",
            ),
            fatigue_refusal_probability_per_epoch=_unit_interval(
                block.get("fatigue_refusal_probability_per_epoch", 0.0),
                "ppe_fatigue.fatigue_refusal_probability_per_epoch",
            ),
        )
        return policy


@dataclass
class PpeFatigueTracker:
    """Registry, policy and the sticky refuser set for one voyage.

    ``measures`` maps NPI measure name to its resolved per-role PPE types;
    it is the same ``resolve_npi`` output the dose machinery parsed, read
    here for the wear contract only.
    """

    policy: PpeFatiguePolicy
    ppe_types: Mapping[str, PpeType] = field(default_factory=dict)
    measure_types_by_role: Mapping[str, Mapping[str, tuple[str, ...]]] = (
        field(default_factory=dict)
    )
    refusers: set[int] = field(default_factory=set)
    rng: Any = None

    @property
    def active(self) -> bool:
        return self.policy.enabled and bool(self.ppe_types)

    def _worn_types(self, agent: Any) -> tuple[str, ...]:
        """The distinct registry types this host is covered by this epoch.

        Coverage is read, not assumed: the measure reached the host (it is in
        ``npi_measures``), and its coverage map names types for the host's
        role — falling back to agent_class for class-keyed coverage.
        """
        worn: list[str] = []
        seen: set[str] = set()
        for measure_name in getattr(agent, "npi_measures", ()) or ():
            by_role = self.measure_types_by_role.get(measure_name)
            if not by_role:
                continue
            declared = by_role.get(str(agent.role)) or by_role.get(
                str(getattr(agent, "agent_class", ""))
            )
            if not declared:
                continue
            for type_id in declared:
                if type_id in self.ppe_types and type_id not in seen:
                    seen.add(type_id)
                    worn.append(type_id)
        return tuple(worn)

    def _try_refusal(self, agent: Any) -> bool:
        """The §7.3 fatigue draw: sticky refusal once drawn."""
        if self.rng is None:
            return False
        probability = self.policy.fatigue_refusal_probability_per_epoch
        if probability <= 0.0:
            return False
        if float(self.rng.random()) >= probability:
            return False
        return True

    def _condition_draws(
        self, agent: Any, worn: tuple[str, ...], wear_hours: float,
    ) -> list[str]:
        """Draw per-type endogenous onset at the declared wear-hour hazard."""
        if self.rng is None:
            return []
        onsets: list[str] = []
        held = getattr(agent, "ppe_condition_ids", set())
        for type_id in worn:
            for condition in self.ppe_types[type_id].fatigue_conditions:
                if condition.condition_id in held:
                    continue
                if condition.rate_per_wear_hour <= 0.0:
                    continue
                hazard = 1.0 - float(
                    np.exp(-condition.rate_per_wear_hour * wear_hours)
                )
                if float(self.rng.random()) >= hazard:
                    continue
                held.add(condition.condition_id)
                onsets.append(condition.condition_id)
                if condition.symptomatic:
                    agent.ppe_symptomatic_active = True
        return onsets

    def step_epoch(
        self, epoch: int, agents: list[Any], hours_per_epoch: float,
    ) -> tuple[list[int], list[tuple[int, str]]]:
        """Accrue wear and fatigue, then draw refusal and onset per host.

        Returns ``(refused_ids, onsets)`` — the refusal ids so the caller can
        write them into the existing compliance log, and (agent_id,
        condition_id) onset pairs so the caller has the audit record.
        """
        if not self.active:
            return [], []
        refused: list[int] = []
        onsets: list[tuple[int, str]] = []
        hours = float(hours_per_epoch)
        for agent in agents:
            aid = int(agent.agent_id)
            # The crew-sustenance channel's declared input (§6.2), written by
            # a sibling arm as a per-epoch contribution; absent = 0.
            deficit = float(getattr(agent, "sustenance_deficit", 0.0) or 0.0)
            if aid in self.refusers or agent.has_departed(epoch):
                agent.fatigue_score += deficit
                agent.ppe_dexterity_impairment = 0.0
                continue
            worn = self._worn_types(agent)
            if not worn:
                agent.fatigue_score += deficit
                agent.ppe_dexterity_impairment = 0.0
                continue
            fatigue = 0.0
            dexterity = 0.0
            for type_id in worn:
                ppe = self.ppe_types[type_id]
                agent.ppe_wear_hours_by_type[type_id] = (
                    agent.ppe_wear_hours_by_type.get(type_id, 0.0) + hours
                )
                fatigue += hours * ppe.fatigue_rate_per_epoch
                dexterity += ppe.dexterity_impairment
            agent.fatigue_score += fatigue + deficit
            agent.ppe_dexterity_impairment = dexterity
            if (
                agent.fatigue_score >= self.policy.fatigue_refusal_threshold
                and self.policy.fatigue_refusal_threshold > 0.0
                and self._try_refusal(agent)
            ):
                self.refusers.add(aid)
                refused.append(aid)
                agent.ppe_fatigue_refused = True
                # A refuser's host-level NPI reductions drop out for the rest
                # of the voyage (spec §7.3).
                agent.dose_reduction_multipliers.clear()
                agent.ppe_dexterity_impairment = 0.0
                continue
            for condition_id in self._condition_draws(agent, worn, hours):
                onsets.append((aid, condition_id))
        return refused, onsets


def build_ppe_fatigue_tracker(
    cfg: Mapping[str, object] | None,
    rng: Any = None,
) -> PpeFatigueTracker:
    """Assemble the channel's tracker from a run config.

    Resolves the registry, the policy block and the NPI measures' typed
    coverage in one place so the epoch step never re-parses config. When the
    channel is enabled, every PPE type a coverage map names must resolve
    against the registry — an untyped run is inert, a mistyped one is a
    config error.
    """
    policy = PpeFatiguePolicy.from_config((cfg or {}).get("ppe_fatigue"))
    ppe_types = resolve_ppe_types(cfg)
    measure_types_by_role: dict[str, Mapping[str, tuple[str, ...]]] = {}
    for name, measure in resolve_npi(cfg).items():
        resolved: dict[str, tuple[str, ...]] = {}
        for role, declared in measure.ppe_types_by_role.items():
            resolved[role] = tuple(
                declared if declared else (policy.default_ppe_type,)
            )
        measure_types_by_role[name] = resolved
    if policy.enabled:
        unknown = sorted(
            {
                type_id
                for by_role in measure_types_by_role.values()
                for declared in by_role.values()
                for type_id in declared
            }
            - set(ppe_types)
        )
        if unknown:
            raise ValueError(
                "ppe_fatigue is enabled but NPI coverage names PPE types "
                f"absent from the ppe_types registry: {unknown}",
            )
    return PpeFatigueTracker(
        policy=policy,
        ppe_types=ppe_types,
        measure_types_by_role=measure_types_by_role,
        rng=rng,
    )
