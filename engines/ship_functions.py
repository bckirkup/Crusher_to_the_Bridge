"""Ship-function capacity: the availability read, the registry, and the
feedback writers (``docs/proposals/ship_function_capacity_spec.md`` §3–§6).

A *function* is a declared ship capability — ``food_service``, ``housekeeping``,
``navigation``, ``fishing_ops`` — scored each epoch from state the sim already
carries: which crew are on watch, who is symptomatic at their station, who is
excluded/quarantined/isolated, which zones are closed, and how healthy the
declared ship systems are. ``(function_id, serves)`` is the instance key: a
cruise ship carries ``food_service`` for passengers *and* for its own crew,
and the two share a ``crew_galley`` pool, so capacity is scored against
summed demand across every instance a class staffs.

Discipline, matching the modules it sits beside:

* The read is hazard-agnostic by construction: symptomatic / absent /
  covered is all it ever sees — never a pathogen id.
* Feedback writers write *inputs* (a coverage scale, a dining-weight table,
  modifier entries merged into the protocol merge, a sustenance deficit on
  crew agents), never physics; engine physics and dose math are untouched.
* Everything rides ``ship_functions.enabled``: absent or disabled, nothing
  runs and every seeded voyage is bit-identical. Per-function ``feedback``
  may be switched off independently for readout-but-no-feedback arms.
* Every operational number in a config block is declared, graded, and never
  fitted to an anchor — ``symptomatic_effectiveness`` and the sustenance
  deficit rate ship as null-sourced declared arms, the
  ``crew_duty_exclusion.compliance_fraction`` precedent.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable

import numpy as np

from engines.ship_systems import ShipSystemsState

WORK_TOKEN = "Work"

SERVES_VALUES = frozenset({"passengers", "crew", "both", "mission"})
CAPACITY_MODELS = frozenset({"staffing_fraction", "bottleneck_min"})
FEEDBACK_KINDS = frozenset({
    "cleaning_coverage_scale",
    "dining_weights",
    "zone_modifiers",
    "route_scalar_scale",
    "readout_only",
})
# The only scalar keys ``apply_transmission_modifiers`` consumes; a
# route_scalar_scale writer may name exactly these.
ROUTE_SCALAR_KEYS = frozenset({
    "direct_contact_scalar",
    "droplet_scalar",
    "hvac_airborne_scalar",
    "fomite_scalar",
})

# Fraction of a watch a symptomatic-but-still-present crew member delivers.
# Sourced: ILI presenteeism literature measures 0.70–0.75 self-rated
# effectiveness; the declared arm sits mid-interval of the register's
# [0.55, 0.85] (docs/ship_functions/parameter_sources.md). A declared
# operational parameter, swept, never fitted.
DEFAULT_SYMPTOMATIC_EFFECTIVENESS = 0.7

# Sustenance deficit accrual per epoch of degraded crew service, and the
# per-epoch recovery multiplier while service is restored. Null-sourced
# operational arms; the parameter-sourcing register records what the
# literature does and does not cover.
DEFAULT_SUSTENANCE_DEFICIT_RATE = 1.0
DEFAULT_SUSTENANCE_RECOVERY = 0.0


class DutyState(Enum):
    """One crew member's relation to their watch this epoch."""

    ABSENT = "absent"       # excluded/quarantined/isolated, or not on watch
    IMPAIRED = "impaired"   # on watch but symptomatic — still at the station
    FIT = "fit"


def on_watch(agent: Any, hour: int) -> bool:
    """Whether the engine placed this agent on a Work token this epoch.

    Reads the recorded ``current_activity`` — the token the placement pass
    actually used — falling back to the raw schedule only for an agent
    nothing has placed yet (the ``_scheduled_activity`` precedent in
    transmission_core).
    """
    recorded = str(getattr(agent, "current_activity", "") or "")
    if recorded:
        return recorded == WORK_TOKEN
    schedule = getattr(agent, "schedule", None) or []
    if not schedule:
        return False
    return str(schedule[hour % len(schedule)]) == WORK_TOKEN


def available_for_duty(
    agent: Any,
    hour: int,
    *,
    symptomatic_ids: set[int],
    excluded_ids: Iterable[int],
    quarantined_ids: Iterable[int],
    isolated_ids: Iterable[int],
) -> DutyState:
    """Absent entirely vs. present-but-impaired vs. fit — spec §4."""
    aid = int(agent.agent_id)
    if (
        aid in excluded_ids
        or aid in quarantined_ids
        or aid in isolated_ids
        or not on_watch(agent, hour)
    ):
        return DutyState.ABSENT
    return DutyState.IMPAIRED if aid in symptomatic_ids else DutyState.FIT


@dataclass(frozen=True)
class StaffingEntry:
    """One staffing pool's watch demand inside a function instance."""

    pool_key: str
    required_on_watch: int
    minimum_on_watch: int = 0
    symptomatic_effectiveness: float = DEFAULT_SYMPTOMATIC_EFFECTIVENESS


@dataclass(frozen=True)
class ShipFunctionSpec:
    """One declared function instance, keyed by ``(function_id, serves)``."""

    function_id: str
    serves: str
    staffing: tuple[StaffingEntry, ...]
    required_zones: frozenset[str]
    required_systems: tuple[str, ...]
    capacity_model: str
    capacity_schedule: dict[int, float]
    feedback: dict[str, Any]
    crew_sustenance: bool

    @property
    def key(self) -> str:
        return f"{self.function_id}:{self.serves}"

    def demand_scale(self, hour: int) -> float:
        """Declared demand multiplier at this hour (galley peaks at meals)."""
        if not self.capacity_schedule:
            return 1.0
        return float(self.capacity_schedule.get(hour % 24, 1.0))


def _parse_staffing(
    entry: dict[str, Any],
    index: int,
) -> tuple[StaffingEntry, ...]:
    """Staffing by agent class, or by duty zone for legacy binary platforms."""
    by_class = entry.get("staffing")
    by_zone = entry.get("staffing_by_duty_zone")
    if by_class is not None and by_zone is not None:
        raise ValueError(
            f"ship_functions[{index}] ({entry.get('function_id')!r}): "
            "staffing and staffing_by_duty_zone are exclusive",
        )
    raw = by_class if by_class is not None else by_zone
    if not isinstance(raw, dict) or not raw:
        raise ValueError(
            f"ship_functions[{index}] ({entry.get('function_id')!r}): "
            "requires a non-empty staffing or staffing_by_duty_zone map",
        )
    out: list[StaffingEntry] = []
    for pool_name, demand in raw.items():
        demand = dict(demand or {})
        required = int(demand.get("required_on_watch", 0))
        minimum = int(demand.get("minimum_on_watch", 0))
        eff = float(demand.get(
            "symptomatic_effectiveness", DEFAULT_SYMPTOMATIC_EFFECTIVENESS,
        ))
        if required <= 0 and minimum <= 0:
            raise ValueError(
                f"ship_functions[{index}].staffing.{pool_name}: "
                "declares no watch demand",
            )
        if not 0.0 <= eff <= 1.0:
            raise ValueError(
                f"ship_functions[{index}].staffing.{pool_name}."
                f"symptomatic_effectiveness must lie in [0, 1]: {eff!r}",
            )
        pool_key = (
            str(pool_name) if by_class is not None else f"zone:{pool_name}"
        )
        out.append(StaffingEntry(
            pool_key=pool_key,
            required_on_watch=required,
            minimum_on_watch=minimum,
            symptomatic_effectiveness=eff,
        ))
    return tuple(out)


def _parse_capacity_schedule(raw: Any, index: int) -> dict[int, float]:
    """Hour-of-day demand multipliers; accepts int-string or int keys."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"ship_functions[{index}].capacity_schedule must be a mapping")
    out: dict[int, float] = {}
    for key, value in raw.items():
        hour = int(key)
        scale = float(value)
        if not 0 <= hour <= 23 or not np.isfinite(scale) or scale < 0.0:
            raise ValueError(
                f"ship_functions[{index}].capacity_schedule[{key!r}] invalid: "
                "hour must be 0-23 and scale finite non-negative",
            )
        out[hour] = scale
    return out


def parse_ship_functions(block: Any) -> tuple[bool, list[ShipFunctionSpec]]:
    """Validate a ``ship_functions`` config block into function specs.

    Returns ``(enabled, specs)``; an absent block means disabled with no
    specs — the identity arm. Referential integrity (classes, zones,
    systems) is checked by the caller, which owns the platform's sets.
    """
    if not block:
        return False, []
    if not isinstance(block, dict):
        raise ValueError("ship_functions must be a mapping")
    specs: list[ShipFunctionSpec] = []
    seen_keys: set[str] = set()
    for index, entry in enumerate(block.get("functions") or []):
        if not isinstance(entry, dict):
            raise ValueError(f"ship_functions.functions[{index}] must be a mapping")
        function_id = str(entry.get("function_id") or "")
        serves = str(entry.get("serves") or "")
        if not function_id or serves not in SERVES_VALUES:
            raise ValueError(
                f"ship_functions.functions[{index}]: function_id required and "
                f"serves must be one of {sorted(SERVES_VALUES)}: {entry!r}",
            )
        model = str(entry.get("capacity_model") or "staffing_fraction")
        if model not in CAPACITY_MODELS:
            raise ValueError(
                f"ship_functions.functions[{index}].capacity_model must be one "
                f"of {sorted(CAPACITY_MODELS)}: {model!r}",
            )
        feedback = dict(entry.get("feedback") or {})
        kind = str(feedback.get("kind") or "readout_only")
        if kind not in FEEDBACK_KINDS:
            raise ValueError(
                f"ship_functions.functions[{index}].feedback.kind must be one "
                f"of {sorted(FEEDBACK_KINDS)}: {kind!r}",
            )
        if kind == "route_scalar_scale":
            scalar_name = str(feedback.get("scalar_name") or "")
            if scalar_name not in ROUTE_SCALAR_KEYS:
                raise ValueError(
                    f"ship_functions.functions[{index}].feedback.scalar_name "
                    f"must be one of {sorted(ROUTE_SCALAR_KEYS)}: "
                    f"{scalar_name!r}",
                )
        spec = ShipFunctionSpec(
            function_id=function_id,
            serves=serves,
            staffing=_parse_staffing(entry, index),
            required_zones=frozenset(
                str(z) for z in (
                    list(entry.get("required_zone_ids") or [])
                    + list(entry.get("required_zone_types") or [])
                )
            ),
            required_systems=tuple(
                str(s) for s in (entry.get("required_systems") or [])
            ),
            capacity_model=model,
            capacity_schedule=_parse_capacity_schedule(
                entry.get("capacity_schedule"), index,
            ),
            feedback=feedback,
            crew_sustenance=bool(feedback.get("crew_sustenance", False)),
        )
        if spec.key in seen_keys:
            raise ValueError(f"ship_functions: duplicate instance {spec.key!r}")
        seen_keys.add(spec.key)
        specs.append(spec)
    return bool(block.get("enabled", False)), specs


def validate_ship_function_refs(
    specs: list[ShipFunctionSpec],
    *,
    class_ids: set[str],
    zone_names: set[str],
    zone_types: set[str],
    system_ids: set[str],
    staffing_pool_names: set[str] | None = None,
) -> None:
    """Referential integrity — an unresolved reference is a load error.

    Silent partial functions are how campaigns lie: every staffing class
    exists in the platform's ``agent_classes``, every zone name/type exists
    in the layout, every system in ``ship_systems``.
    """
    pools = class_ids | set(staffing_pool_names or set())
    for spec in specs:
        for staff in spec.staffing:
            name = staff.pool_key
            if name.startswith("zone:"):
                zone = name.split(":", 1)[1]
                if zone not in zone_names and zone not in zone_types:
                    raise ValueError(
                        f"ship_functions {spec.key!r}: unknown duty zone "
                        f"{zone!r}",
                    )
            elif name not in pools:
                raise ValueError(
                    f"ship_functions {spec.key!r}: staffing class {name!r} "
                    "not in the platform's agent_classes",
                )
        for zone in spec.required_zones:
            if zone not in zone_names and zone not in zone_types:
                raise ValueError(
                    f"ship_functions {spec.key!r}: unknown zone {zone!r}",
                )
        for system_id in spec.required_systems:
            if system_id not in system_ids:
                raise ValueError(
                    f"ship_functions {spec.key!r}: system {system_id!r} "
                    "not in ship_systems",
                )


class FunctionCapacityRunner:
    """Per-voyage capacity readout plus the declared feedback writers.

    Owns no physics. Computed once per epoch after confinement and duty
    exclusion settle; the modifier contributions it produces are merged
    into the *next* epoch's ``merged_mods`` before application, and its
    dining/cleaning writes land on slots the engine already reads.
    """

    def __init__(
        self,
        specs: list[ShipFunctionSpec],
        systems: ShipSystemsState | None,
        *,
        default_symptomatic_effectiveness: float = (
            DEFAULT_SYMPTOMATIC_EFFECTIVENESS
        ),
    ) -> None:
        self.specs = specs
        self.systems = systems
        self.default_effectiveness = float(default_symptomatic_effectiveness)
        # Per-instance count of consecutive epochs below the feedback
        # threshold — the sustained-state machine for thresholded writers.
        self._below_counts: dict[str, int] = {}
        # Modifier entries emitted for the next epoch's merge.
        self.pending_modifiers: dict[str, Any] = {}
        self._dining_baseline: dict[str, Any] | None = None

    # ── availability read ────────────────────────────────────────────

    def _pools(
        self,
        agents: list[Any],
        hour: int,
        symptomatic_ids: set[int],
        excluded_ids: Iterable[int],
        quarantined_ids: Iterable[int],
        isolated_ids: Iterable[int],
    ) -> tuple[
        dict[str, dict[str, int]],
        dict[str, list[tuple[Any, DutyState]]],
    ]:
        """fit/impaired counts (and members) per staffing pool key this epoch."""
        pools: dict[str, dict[str, int]] = {}
        members: dict[str, list[tuple[Any, DutyState]]] = {}
        for agent in agents:
            if str(getattr(agent, "role", "")) != "crew":
                continue
            state = available_for_duty(
                agent, hour,
                symptomatic_ids=symptomatic_ids,
                excluded_ids=excluded_ids,
                quarantined_ids=quarantined_ids,
                isolated_ids=isolated_ids,
            )
            if state is DutyState.ABSENT:
                continue
            keys = [str(getattr(agent, "agent_class", "") or "")]
            work_zone = getattr(agent, "work_zone", "") or ""
            if work_zone:
                keys.append(f"zone:{work_zone}")
            for key in keys:
                bucket = pools.setdefault(key, {"fit": 0, "impaired": 0})
                bucket["impaired" if state is DutyState.IMPAIRED else "fit"] += 1
                members.setdefault(key, []).append((agent, state))
        return pools, members

    def _demand_by_pool(self, hour: int) -> dict[str, float]:
        """Summed watch demand per pool across every instance drawing it."""
        demand: dict[str, float] = {}
        for spec in self.specs:
            scale = spec.demand_scale(hour)
            for staff in spec.staffing:
                demand[staff.pool_key] = (
                    demand.get(staff.pool_key, 0.0)
                    + staff.required_on_watch * scale
                )
        return demand

    # ── capacity math ────────────────────────────────────────────────

    def _staffing_share(
        self,
        staff: StaffingEntry,
        spec: ShipFunctionSpec,
        hour: int,
        pools: dict[str, dict[str, int]],
        demand: dict[str, float],
    ) -> tuple[float, dict[str, Any]]:
        """The fair-share fraction of this instance's demand the pool covers."""
        pool = pools.get(staff.pool_key) or {"fit": 0, "impaired": 0}
        delivered = pool["fit"] + pool["impaired"] * staff.symptomatic_effectiveness
        required_total = demand.get(staff.pool_key, 0.0)
        share = (
            1.0 if required_total <= 0.0
            else min(1.0, delivered / required_total)
        )
        own_demand = staff.required_on_watch * spec.demand_scale(hour)
        if (
            spec.capacity_model == "bottleneck_min"
            and staff.minimum_on_watch > 0
            and own_demand > 0
            and share * own_demand < staff.minimum_on_watch
        ):
            share = 0.0  # below the watch minimum the function does not run
        return share, {
            "fit": pool["fit"],
            "impaired": pool["impaired"],
            "delivered": delivered,
            "summed_demand": required_total,
            "share": share,
        }

    def _zone_share(
        self,
        spec: ShipFunctionSpec,
        closed_zones: set[str],
        zone_type_by_id: dict[str, str],
    ) -> float:
        """Fraction of required zones open; a type needs one open zone."""
        if not spec.required_zones:
            return 1.0
        open_count = 0
        for requirement in spec.required_zones:
            if requirement in zone_type_by_id:
                open_count += requirement not in closed_zones
                continue
            members = [
                name for name, ztype in zone_type_by_id.items()
                if ztype == requirement
            ]
            if members and any(name not in closed_zones for name in members):
                open_count += 1
            elif not members and requirement not in closed_zones:
                open_count += 1  # validated id not in the type map: open
        return open_count / len(spec.required_zones)

    def _instance_capacity(
        self,
        spec: ShipFunctionSpec,
        hour: int,
        pools: dict[str, dict[str, int]],
        demand: dict[str, float],
        closed_zones: set[str],
        zone_type_by_id: dict[str, str],
    ) -> tuple[float, str | None, dict[str, Any]]:
        """Score one instance; return (capacity, binding constraint, detail)."""
        weakest_share = 1.0
        weakest_class: str | None = None
        staffing_detail: dict[str, Any] = {}
        for staff in spec.staffing:
            share, detail = self._staffing_share(staff, spec, hour, pools, demand)
            staffing_detail[staff.pool_key] = detail
            if share < weakest_share:
                weakest_share, weakest_class = share, staff.pool_key
        zone_share = self._zone_share(spec, closed_zones, zone_type_by_id)
        system_mult = (
            self.systems.capacity_multiplier(spec.function_id)
            if self.systems is not None
            else 1.0
        )
        if spec.capacity_model == "bottleneck_min":
            capacity = min(weakest_share, zone_share, system_mult)
        else:  # staffing_fraction
            capacity = weakest_share * zone_share * system_mult
        binding: str | None = None
        if capacity < 1.0:
            binding, _ = min(
                {
                    f"staffing:{weakest_class}": weakest_share,
                    "zones": zone_share,
                    "systems": system_mult,
                }.items(),
                key=lambda kv: kv[1],
            )
        return capacity, binding, {
            "staffing": staffing_detail,
            "zone_share": zone_share,
            "system_multiplier": system_mult,
        }

    # ── epoch step ───────────────────────────────────────────────────

    def step(
        self,
        *,
        hour: int,
        agents: list[Any],
        symptomatic_ids: set[int],
        state: Any,
        tracker: Any,
        merged_mods: dict[str, Any] | None,
        engine: Any,
        tx_core: Any,
        clock: Any,
        zone_type_by_id: dict[str, str],
    ) -> dict[str, Any]:
        """Score every instance, run systems, and emit feedback writes."""
        closed = set((merged_mods or {}).get("close_zones") or [])
        closed.update(getattr(state, "info_suppression_closed_zones", ()) or ())
        excluded = getattr(tracker, "excluded_ids", frozenset()) if tracker else ()
        pools, members = self._pools(
            agents, hour, symptomatic_ids,
            excluded, state.quarantined_ids, state.isolated_ids,
        )
        demand = self._demand_by_pool(hour)

        self.pending_modifiers = {}
        cleaning_scale = 1.0
        dining_pick: dict[str, Any] | None = None
        dining_pick_capacity = 1.0
        functions: dict[str, Any] = {}

        for spec in self.specs:
            capacity, binding, detail = self._instance_capacity(
                spec, hour, pools, demand, closed, zone_type_by_id,
            )
            functions[spec.key] = {
                "capacity": capacity,
                "binding": binding,
                "available_on_watch": int(round(sum(
                    d["delivered"] for d in detail["staffing"].values()
                ))),
                "required_on_watch": sum(
                    staff.required_on_watch * spec.demand_scale(hour)
                    for staff in spec.staffing
                ),
                **detail,
            }
            self._tick_below(spec, capacity)
            if spec.feedback.get("enabled", True):
                cleaning_scale = self._fold_cleaning(spec, capacity, cleaning_scale)
                pick = self._dining_candidate(
                    spec, capacity, clock.hours_per_epoch,
                )
                if pick is not None and capacity < dining_pick_capacity:
                    dining_pick, dining_pick_capacity = pick, capacity
                self._write_modifiers(spec, capacity, clock.hours_per_epoch)
                self._write_sustenance(spec, capacity, agents)

        self._apply_dining(engine, dining_pick)
        if tx_core is not None:
            tx_core.cleaning_coverage_scale = cleaning_scale
        record: dict[str, Any] = {
            "functions": functions,
            "staffing_pools": {
                key: pools.get(key, {"fit": 0, "impaired": 0})
                for key in demand
                if demand[key] > 0
            },
        }
        if self.systems is not None:
            self._step_systems(clock, members, demand)
            record["ship_systems"] = self.systems.snapshot()
        return record

    # ── feedback writers ─────────────────────────────────────────────

    def _tick_below(self, spec: ShipFunctionSpec, capacity: float) -> None:
        """Advance the sustained-below counter for thresholded writers."""
        threshold = float(spec.feedback.get("threshold", 0.5))
        if capacity < threshold:
            self._below_counts[spec.key] = self._below_counts.get(spec.key, 0) + 1
        else:
            self._below_counts[spec.key] = 0

    def _sustained_below(
        self,
        spec: ShipFunctionSpec,
        hours_per_epoch: float,
    ) -> bool:
        """Sustained-below in wall-clock hours across epoch ticks."""
        sustained = float(spec.feedback.get("sustained_hours", 4.0))
        elapsed = self._below_counts.get(spec.key, 0) * hours_per_epoch
        return elapsed >= sustained

    def _write_modifiers(
        self,
        spec: ShipFunctionSpec,
        capacity: float,
        hours_per_epoch: float,
    ) -> None:
        """Thresholded zone closures and continuous route scalars."""
        kind = spec.feedback.get("kind")
        if kind == "zone_modifiers" and self._sustained_below(spec, hours_per_epoch):
            zones = [str(z) for z in spec.feedback.get("zone_close_on_loss", [])]
            if zones:
                current = self.pending_modifiers.get("close_zones", [])
                self.pending_modifiers["close_zones"] = sorted(
                    set(current) | set(zones),
                )
        elif kind == "route_scalar_scale" and capacity < 1.0:
            # Omitted at full capacity: reset_modifiers already restores 1.0.
            floor = float(spec.feedback.get("floor", 0.0))
            scalar = 1.0 - (1.0 - capacity) * (1.0 - floor)
            name = str(spec.feedback["scalar_name"])
            prev = self.pending_modifiers.get(name)
            # Most aggressive wins, matching the protocol merge's scalar rule.
            self.pending_modifiers[name] = (
                scalar if prev is None else min(prev, scalar)
            )

    def _fold_cleaning(
        self,
        spec: ShipFunctionSpec,
        capacity: float,
        current: float,
    ) -> float:
        """Continuous coverage scale; the most degraded declaration governs."""
        if spec.feedback.get("kind") != "cleaning_coverage_scale":
            return current
        floor = float(spec.feedback.get("floor", 0.0))
        return min(current, floor + (1.0 - floor) * capacity)

    def _dining_candidate(
        self,
        spec: ShipFunctionSpec,
        capacity: float,
        hours_per_epoch: float,
    ) -> dict[str, Any] | None:
        """Degraded meal weights when a declared dining writer is sustained-below."""
        if spec.feedback.get("kind") != "dining_weights":
            return None
        if not self._sustained_below(spec, hours_per_epoch):
            return None
        degraded = spec.feedback.get("degraded_weights")
        return dict(degraded) if degraded else None

    def _apply_dining(self, engine: Any, override: dict[str, Any] | None) -> None:
        """Swap or restore the engine's meal-weight table — inputs, not mechanics."""
        if engine is None:
            return
        behavior = engine.agent_behavior
        if self._dining_baseline is None:
            self._dining_baseline = {
                meal: dict(weights)
                for meal, weights in (
                    behavior.get("dining_meal_weights") or {}
                ).items()
            }
        baseline = self._dining_baseline
        if override is None:
            behavior["dining_meal_weights"] = {
                meal: dict(weights) for meal, weights in baseline.items()
            }
            return
        # Flat service-type weights apply to every meal; a per-meal mapping
        # overrides each meal's own row.
        per_meal = any(isinstance(v, dict) for v in override.values())
        new_weights: dict[str, dict[str, float]] = {}
        for meal, weights in baseline.items():
            row = dict(weights)
            overlay = override.get(meal) if per_meal else override
            if isinstance(overlay, dict):
                row.update({k: float(v) for k, v in overlay.items()})
            new_weights[meal] = row
        behavior["dining_meal_weights"] = new_weights

    def _write_sustenance(
        self,
        spec: ShipFunctionSpec,
        capacity: float,
        agents: list[Any],
    ) -> None:
        """Crew-served degradation lands on the crew — the second-order channel."""
        if not spec.crew_sustenance or spec.serves not in ("crew", "both"):
            return
        threshold = float(spec.feedback.get("sustenance_threshold", 1.0))
        rate = float(spec.feedback.get(
            "sustenance_deficit_rate", DEFAULT_SUSTENANCE_DEFICIT_RATE,
        ))
        recovery = float(spec.feedback.get(
            "sustenance_recovery", DEFAULT_SUSTENANCE_RECOVERY,
        ))
        if capacity >= threshold:
            if recovery <= 0.0:
                return
            for agent in agents:
                if str(getattr(agent, "role", "")) != "crew":
                    continue
                deficit = getattr(agent, "sustenance_deficit", 0.0)
                if deficit:
                    agent.sustenance_deficit = deficit * (1.0 - recovery)
            return
        increment = (threshold - capacity) * rate
        if increment <= 0.0:
            return
        for agent in agents:
            if str(getattr(agent, "role", "")) == "crew":
                agent.sustenance_deficit = (
                    getattr(agent, "sustenance_deficit", 0.0) + increment
                )

    def _step_systems(
        self,
        clock: Any,
        members: dict[str, list[tuple[Any, DutyState]]],
        demand: dict[str, float],
    ) -> None:
        """Degrade every system, then spend residual watch-hours on repair."""
        assert self.systems is not None
        residual_hours: dict[str, float] = {}
        labor_classes = {
            spec.repair_labor_class
            for spec in self.systems.specs
            if spec.repair_labor_class
        }
        for cls in labor_classes:
            # PPE dexterity impairment scales the watch-hours a worker can
            # still deliver to repair; the fatigue channel writes it,
            # presence-guarded so an unarmed run is untouched.
            delivered = sum(
                (
                    1.0 if state is DutyState.FIT
                    else self.default_effectiveness
                ) * (
                    1.0
                    - min(
                        1.0,
                        max(
                            0.0,
                            float(getattr(agent, "ppe_dexterity_impairment", 0.0) or 0.0),
                        ),
                    )
                )
                for agent, state in members.get(cls, [])
            )
            residual = max(0.0, delivered - demand.get(cls, 0.0))
            residual_hours[cls] = residual * clock.hours_per_epoch
        self.systems.step(clock.day_fraction_per_epoch, residual_hours)


def merge_capacity_modifiers(
    merged_mods: dict[str, Any],
    contribs: dict[str, Any],
    merge_value: Any,
) -> dict[str, Any]:
    """Fold capacity-writer contributions into the epoch's merged modifiers.

    Reuses the protocol engine's own merge rule (lists union, scalars keep
    the most aggressive value) so a capacity-driven zone close and an SOP
    zone close compose exactly the way two protocols' would.
    """
    if not contribs:
        return merged_mods
    out = dict(merged_mods or {})
    for key, value in contribs.items():
        if key in out:
            out[key] = merge_value(key, out[key], value)
        else:
            out[key] = value
    return out
