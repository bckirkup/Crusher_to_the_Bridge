"""Phase 1b of the COVID first look: the boarding axis as a declared screen.

Diamond Princess is seeded with one passenger infected at embarkation
(``infection_age_days = 0``) because no retrieved source gives the index
case's infection age or how many introductions there were. Both are recorded
in the scenario as declared assumptions, not sourced values, and the fit spec
refuses to move them to make the onset curve come out right. This module
screens them instead: the same training hull, at the fitted Theta and its
half-decade neighbours, over a small grid of infection age and import count,
on matched seeds, and reports what the pre-quarantine onset count and the
first recorded onset do. It is a sensitivity surface. Nothing here selects a
scenario, and the fit itself stays at the declared age-0 / one-import cell,
which the grid includes so every contrast is paired within the screen.

The screen also declares ``transmission.sanitary_visit_mode``. The shared
heads landed default-off (#538: measure before default-on), so the replicated
fit ran with the zones present and unvisited; the screen runs them visited
and records the transmission core's execution witness in every cell so
"inert" and "never ran" cannot be confused (#540).
"""

from __future__ import annotations

import json
import math
import os
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import product
from typing import Any

import numpy as np

from engines.infection_dynamics_bridge import ever_presented
from engines.transmission_core import PATHWAY_EFFICIENCY_KEYS, TransmissionCore
from picard_framework.covid_fit_targets import load_fit_targets
from picard_framework.covid_hull_scenarios import REPO_ROOT, load_hull_scenarios
from picard_framework.covid_theta_fit import (
    PATHOGEN_ID,
    HullObservables,
    build_fit_run_spec,
    load_covid_profile,
    observables_from_modality,
    run_fit_spec,
)
from simulation_utils.paths import validated_open

DESIGN_REL = os.path.join(
    "picard_framework", "runs", "covid_boarding_screen_v1_design.json",
)
SANITARY_VISIT_MODES = ("none", "dwell_weighted")
# Attribution-design arm axes (covid_quarantine_attribution_v1). Every key a
# declared arm may override; anything else refuses at design load rather than
# drifting into a silently-ignored counterfactual.
ARM_OVERRIDE_KEYS = frozenset({
    "scheduled_protocol_id",
    "pathogen_pool_transport",
    "near_field_air_mode",
    "profile_route_efficiency_multipliers",
})
QUARANTINE_PROTOCOL_ID = "SOP-017"
NEAR_FIELD_AIR_MODES = ("two_box", "off")
ZONE_CLASSES = ("cabin", "corridor", "crew_mess", "galley", "other")
INTERVAL = (0.05, 0.95)
SPLIT_DAY = 17
TURN_DAY = 16

# Per-seed payload keys, written by the cell producers and read back by the
# merge-side criteria.
KEY_INDEX_ONSET_DAY = "index_onset_day"
KEY_INDEX_SHEDDING_AT_DAY0 = "index_shedding_at_day0"
KEY_INDEX_DEPARTED_EPOCH = "index_departed_epoch"
KEY_INFECTIONS_TOTAL = "infections_total"
KEY_ABOARD_TOTAL = "aboard_total"
KEY_ATTACK_RATE = "attack_rate"
KEY_VSP_MAX = "vsp_reported_case_fraction_max"

VSP_CROSSING_THRESHOLD = 0.03
INDEX_GEOMETRY_PASS_FRACTION_MIN = 0.80


# ── design ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BoardingScreenDesign:
    """The screen as declared before any cell ran."""

    design_id: str
    scenario_id: str
    thetas: tuple[float, ...]
    infection_age_days: tuple[float, ...]
    imports: tuple[int, ...]
    sanitary_visit_mode: str
    seed_base: int
    seeds: int
    takeoff_recorded_onsets: int
    points: tuple[tuple[float, float, int], ...] = ()
    parent_design: str | None = None
    arms: tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        if self.sanitary_visit_mode not in SANITARY_VISIT_MODES:
            raise ValueError(
                f"sanitary_visit_mode must be one of {SANITARY_VISIT_MODES}, "
                f"got {self.sanitary_visit_mode!r}",
            )
        if self.seeds < 1:
            raise ValueError("a screen needs at least one seed")
        if any(age < 0 for age in self.infection_age_days):
            raise ValueError("infection_age_days must be non-negative")
        if any(n < 1 for n in self.imports):
            raise ValueError("imports must be at least 1")
        if any(not math.isfinite(t) or t <= 0 for t in self.thetas):
            raise ValueError("thetas must be finite and positive")
        for theta, age, imports in self.points:
            if not math.isfinite(theta) or theta <= 0 or age < 0 or imports < 1:
                raise ValueError(f"malformed refinement point {(theta, age, imports)}")
        if len(set(self.points)) != len(self.points):
            raise ValueError("refinement points must be distinct")
        arm_ids = [a.get("arm_id") for a in self.arms]
        for arm_id in arm_ids:
            if not isinstance(arm_id, str) or not arm_id:
                raise ValueError("every arm needs a non-empty string arm_id")
        if len(set(arm_ids)) != len(arm_ids):
            raise ValueError("arm_ids must be distinct")
        if self.arms:
            baseline_overrides = self.arms[0].get("overrides") or {}
            if baseline_overrides:
                raise ValueError(
                    "the first arm is the declared baseline and must carry "
                    "empty overrides",
                )
            for arm in self.arms:
                unknown = set(arm.get("overrides") or {}) - ARM_OVERRIDE_KEYS
                if unknown:
                    raise ValueError(
                        f"arm {arm.get('arm_id')!r} declares unknown override "
                        f"keys {sorted(unknown)}; allowed: "
                        f"{sorted(ARM_OVERRIDE_KEYS)}",
                    )

    @property
    def arm_ids(self) -> tuple[str, ...]:
        return tuple(str(a["arm_id"]) for a in self.arms)

    @property
    def baseline_arm_id(self) -> str | None:
        return self.arm_ids[0] if self.arms else None

    def arm_overrides(self, arm_id: str) -> Mapping[str, Any]:
        """The override block one arm declares, KeyError on an unknown id."""
        for arm in self.arms:
            if arm.get("arm_id") == arm_id:
                return arm.get("overrides") or {}
        raise KeyError(f"unknown arm_id {arm_id!r}")

    @property
    def is_refinement(self) -> bool:
        """An explicit point list (stage 2) rather than a product grid."""
        return bool(self.points)

    @property
    def axis_points(self) -> tuple[tuple[float, float, int], ...]:
        """Every (Theta, age, imports) the design evaluates, in order."""
        if self.is_refinement:
            return self.points
        return tuple(
            (float(t), float(a), int(n))
            for t, a, n in product(self.thetas, self.infection_age_days, self.imports)
        )

    @property
    def seed_values(self) -> tuple[int, ...]:
        return tuple(self.seed_base + i for i in range(self.seeds))

    @property
    def baseline(self) -> tuple[float, int]:
        """The declared scenario's cell on the axis: age 0, one import."""
        return (0.0, 1)

    def as_dict(self) -> dict[str, Any]:
        return {
            "design_id": self.design_id,
            "scenario_id": self.scenario_id,
            "thetas": list(self.thetas),
            "infection_age_days": list(self.infection_age_days),
            "imports": list(self.imports),
            "sanitary_visit_mode": self.sanitary_visit_mode,
            "seed_base": self.seed_base,
            "seeds": self.seeds,
            "takeoff_recorded_onsets": self.takeoff_recorded_onsets,
            "points": [list(p) for p in self.points],
            "parent_design": self.parent_design,
            "arms": [dict(a) for a in self.arms],
        }


def design_path(repo_root: str = REPO_ROOT) -> str:
    return os.path.join(repo_root, DESIGN_REL)


def load_design(
    path: str | None = None,
    *,
    repo_root: str = REPO_ROOT,
) -> BoardingScreenDesign:
    resolved = path or design_path(repo_root)
    with validated_open(
        resolved, allowed_roots=(repo_root,), encoding="utf-8",
    ) as handle:
        raw = json.load(handle)
    design = BoardingScreenDesign(
        design_id=str(raw["design_id"]),
        scenario_id=str(raw["scenario_id"]),
        thetas=tuple(float(t) for t in raw["thetas"]),
        infection_age_days=tuple(float(a) for a in raw["infection_age_days"]),
        imports=tuple(int(n) for n in raw["imports"]),
        sanitary_visit_mode=str(raw["sanitary_visit_mode"]),
        seed_base=int(raw["seed_base"]),
        seeds=int(raw["seeds"]),
        takeoff_recorded_onsets=int(raw["takeoff_recorded_onsets"]),
        points=tuple(
            (float(t), float(a), int(n)) for t, a, n in raw.get("points", [])
        ),
        parent_design=raw.get("parent_design"),
        arms=tuple(dict(a) for a in raw.get("arms", [])),
    )
    load_hull_scenarios().assert_fit_target(design.scenario_id)
    if design.is_refinement:
        return design
    if design.arms:
        # An arm design pairs cells by arm, not by the boarding axis: its
        # axes do not have to include the declared scenario's cell.
        return design
    if design.baseline[0] not in design.infection_age_days or (
        design.baseline[1] not in design.imports
    ):
        raise ValueError(
            "the screen must include the declared scenario's cell "
            "(infection_age_days 0, imports 1) so contrasts are paired",
        )
    return design


# ── cells ─────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ScreenCell:
    """One (Theta, infection age, imports, seed) the array evaluates."""

    index: int
    scenario_id: str
    theta: float
    infection_age_days: float
    imports: int
    seed: int
    arm_id: str | None = None

    @property
    def axis(self) -> tuple[float, int]:
        return (self.infection_age_days, self.imports)

    @property
    def key(self) -> str:
        exponent = f"{math.log10(self.theta):.2f}".replace(".", "p")
        age = f"{self.infection_age_days:g}".replace(".", "p")
        stem = (
            f"screen_{self.scenario_id}_theta1e{exponent}_age{age}d"
            f"_imports{self.imports}_seed{self.seed}"
        )
        if self.arm_id is not None:
            stem += f"_arm{self.arm_id}"
        return f"{stem}.json"

    def as_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "scenario_id": self.scenario_id,
            "theta": self.theta,
            "infection_age_days": self.infection_age_days,
            "imports": self.imports,
            "seed": self.seed,
            "arm_id": self.arm_id,
            "key": self.key,
        }


def enumerate_cells(design: BoardingScreenDesign) -> tuple[ScreenCell, ...]:
    """Every cell in a fixed order: Theta, then age, then imports, then seed.

    A refinement design enumerates its explicit point list in the order the
    refinement ranked them, each over the same matched seeds.
    """
    cells: list[ScreenCell] = []
    # Axis point, then arm, then seed: one arm's seeds stay contiguous.
    arm_ids = design.arm_ids or (None,)
    for (theta, age, imports), arm_id, seed in product(
        design.axis_points, arm_ids, design.seed_values,
    ):
        cells.append(ScreenCell(
            index=len(cells),
            scenario_id=design.scenario_id,
            theta=float(theta),
            infection_age_days=float(age),
            imports=int(imports),
            seed=int(seed),
            arm_id=arm_id,
        ))
    return tuple(cells)


def apply_boarding_axis(
    raw: dict[str, Any],
    *,
    infection_age_days: float,
    imports: int,
    sanitary_visit_mode: str,
) -> dict[str, Any]:
    """Move the scenario's explicit seed along the axis, in place.

    The hull scenario declares exactly one explicit seed (the index case);
    the screen changes only its ``count`` and ``infection_age_days`` and the
    transmission block's sanitary visit mode. Everything else in the run
    spec is what the fit ran.
    """
    overrides = raw.setdefault("config_overrides", {})
    seeds = overrides.get("initiation", {}).get("explicit_seeds", [])
    if len(seeds) != 1:
        raise ValueError(
            f"the boarding screen expects one explicit seed, found {len(seeds)}",
        )
    seeds[0]["count"] = int(imports)
    seeds[0]["infection_age_days"] = float(infection_age_days)
    overrides.setdefault("transmission", {})["sanitary_visit_mode"] = (
        sanitary_visit_mode
    )
    return raw


def _swap_scheduled_protocol(raw: dict[str, Any], protocol_id: str) -> None:
    """Rename the scheduled SOP-017 entry to the arm's protocol, in place."""
    protocols = (
        raw.get("config_overrides", {})
        .get("scenario_schedule", {})
        .get("protocols", [])
    )
    found = False
    for entry in protocols:
        if entry.get("protocol_id") == QUARANTINE_PROTOCOL_ID:
            entry["protocol_id"] = str(protocol_id)
            found = True
    if not found:
        raise ValueError(
            f"the run spec's scenario_schedule schedules no "
            f"{QUARANTINE_PROTOCOL_ID} entry to rename",
        )


def _apply_route_efficiencies(
    raw: dict[str, Any],
    arm_values: Mapping[str, Any],
    profile: dict[str, Any],
) -> None:
    """Merge the arm's route multipliers onto the shipped profile mapping."""
    shipped = profile["route_efficiency_multipliers"]
    unknown = set(arm_values) - set(shipped)
    if unknown:
        raise ValueError(
            f"route_efficiency_multipliers keys {sorted(unknown)} are not in "
            f"the shipped profile {sorted(shipped)}",
        )
    for key, value in arm_values.items():
        if not math.isfinite(float(value)) or float(value) < 0.0:
            raise ValueError(
                f"route_efficiency_multipliers[{key!r}] must be finite and "
                f">= 0, got {value!r}",
            )
    merged = {**shipped, **{k: float(v) for k, v in arm_values.items()}}
    raw.setdefault("pathogen_overrides", {}).setdefault(
        PATHOGEN_ID, {},
    )["route_efficiency_multipliers"] = merged


def apply_arm_overrides(
    raw: dict[str, Any],
    overrides: Mapping[str, Any],
    *,
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Apply one arm's override block to a built run spec, in place.

    ``pathogen_pool_transport`` is not handled here: it is a build-time
    argument to ``build_fit_run_spec``. Every other declared key lands in the
    spec where the engine reads it; an undeclared key raises rather than
    being silently ignored.
    """
    for key in overrides:
        if key not in ARM_OVERRIDE_KEYS:
            raise ValueError(
                f"unknown arm override key {key!r}; allowed: "
                f"{sorted(ARM_OVERRIDE_KEYS)}",
            )
    if "scheduled_protocol_id" in overrides:
        _swap_scheduled_protocol(raw, str(overrides["scheduled_protocol_id"]))
    if "near_field_air_mode" in overrides:
        mode = str(overrides["near_field_air_mode"])
        if mode not in NEAR_FIELD_AIR_MODES:
            raise ValueError(
                f"near_field_air_mode must be one of {NEAR_FIELD_AIR_MODES}, "
                f"got {mode!r}",
            )
        raw["config_overrides"].setdefault("transmission", {}).setdefault(
            "near_field_air", {},
        )["mode"] = mode
    if "profile_route_efficiency_multipliers" in overrides:
        _apply_route_efficiencies(
            raw, overrides["profile_route_efficiency_multipliers"], profile,
        )
    return raw


class QuarantineAttributionLedger:
    """Per-epoch accumulator a screen cell attaches as the epoch observer.

    Reads the epoch's transmission events and the confinement in force while
    they fired — detail that ``history_retention = "compact"`` drops — into
    the smallest structure the payload needs. The observer only reads.
    """

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self._seen_targets: set[int] = set()
        self.activation_epoch: int | None = None
        self.exempt_classes: list[str] | None = None
        self.confined_at_activation: int | None = None
        self.protocol_ids: list[str] | None = None

    @property
    def activated(self) -> bool:
        return self.activation_epoch is not None

    @staticmethod
    def _event_pathway(ev: Any) -> str:
        """The dominant acquired-dose route, else the stripped pathway key."""
        ledger = ev.acquired_particles_by_route or {}
        if sum(ledger.values()) > 0.0:
            return max(ledger, key=ledger.get)
        pathway = str(ev.pathway or "")
        return pathway.split(":", 1)[0] or "unknown"

    def observe(self, sim: Any, work: Any) -> None:
        seeded = set(getattr(sim.engine, "explicit_seed_agent_ids", None) or ())
        quarantined = set(getattr(sim.engine, "quarantined_ids", None) or ())
        for ev in work.tx_events:
            target = ev.target_agent_id
            if target in self._seen_targets or target in seeded:
                continue
            self._seen_targets.add(target)
            self.events.append({
                "epoch": int(ev.epoch),
                "zone": TransmissionCore.compartment_parent(ev.zone),
                "pathway": self._event_pathway(ev),
                "target_agent_id": int(target),
                "confined": target in quarantined,
            })
        whole_body = [
            e for e in (work.active_mods or [])
            if e.get("modifiers", {}).get("confine_all_to_quarters")
        ]
        if self.activation_epoch is None and whole_body:
            self.activation_epoch = work.epoch
            exempt = [
                set(e.get("modifiers", {}).get("exempt_classes", []))
                for e in whole_body
            ]
            # An agent is exempt only if every whole-body order exempts it.
            self.exempt_classes = sorted(set.intersection(*exempt))
            self.confined_at_activation = len(work.state.quarantined_ids)
            self.protocol_ids = sorted(
                e.get("protocol_id") for e in whole_body
            )


def _index_host(engine: Any) -> Any | None:
    """The agent the explicit-seed channel infected at boarding."""
    seeded = set(getattr(engine, "explicit_seed_agent_ids", ()) or ())
    return next(
        (a for a in engine.agents if a.agent_id in seeded),
        None,
    )


def _index_geometry(
    engine: Any,
    cell: ScreenCell,
    profile: dict[str, Any],
) -> dict[str, Any]:
    """The seeded index host's own geometry, read off its infection record.

    The stamped ``onset_time_infected`` records when progression *noticed*
    the onset, so a host that boarded past incubation is not back-dated;
    the true onset is the drawn ``incubation_days`` against the declared
    boarding age, which is the record this screen means.
    """
    agent = _index_host(engine)
    if agent is None:
        return {
            KEY_INDEX_ONSET_DAY: None,
            KEY_INDEX_SHEDDING_AT_DAY0: None,
            KEY_INDEX_DEPARTED_EPOCH: None,
        }
    inf = agent.infections.get(PATHOGEN_ID, {})
    incubation = inf.get("incubation_days")
    onset_day: float | None = None
    if incubation is not None and ever_presented(inf):
        onset_day = (
            engine.clock.days_elapsed(int(inf.get("infection_epoch", 0)))
            + float(incubation)
            - cell.infection_age_days
        )
    shedding_day0 = False
    if incubation is not None:
        presymptomatic = float(profile.get("presymptomatic_shedding_days", 0.0))
        # The same gate _shedding_curve_point applies, evaluated at the
        # boarding age: in-window means the host emits at epoch 0.
        shedding_day0 = (
            cell.infection_age_days - float(incubation) >= -presymptomatic
        )
    return {
        KEY_INDEX_ONSET_DAY: onset_day,
        KEY_INDEX_SHEDDING_AT_DAY0: shedding_day0,
        KEY_INDEX_DEPARTED_EPOCH: agent.departure_epoch,
    }


def _truth_counts(engine: Any) -> dict[str, Any]:
    """Ever-infected host count excluding the seeded hosts, and the aboard."""
    seeded = set(getattr(engine, "explicit_seed_agent_ids", ()) or ())
    infected = sum(
        1 for a in engine.agents
        if PATHOGEN_ID in a.infections and a.agent_id not in seeded
    )
    aboard = len(engine.agents)
    return {
        KEY_INFECTIONS_TOTAL: infected,
        KEY_ABOARD_TOTAL: aboard,
        KEY_ATTACK_RATE: (infected / aboard) if aboard else None,
    }


def _first_onset_day(curve: dict[int, dict[str, int]]) -> int | None:
    days = [
        int(day) for day, roles in curve.items()
        if int(roles.get("passenger", 0)) + int(roles.get("crew", 0)) > 0
    ]
    return min(days) if days else None


def _quarantine_window(raw: dict[str, Any]) -> tuple[dict[str, Any], int, int | None]:
    """The scheduled quarantine entry and its inclusive day window."""
    protocols = (
        raw.get("config_overrides", {})
        .get("scenario_schedule", {})
        .get("protocols", [])
    )
    for entry in protocols:
        # SOP-017 or an arm's renamed copy of it (same window).
        if entry.get("protocol_id", "").startswith(QUARANTINE_PROTOCOL_ID):
            end = entry.get("end_day")
            return (
                entry,
                int(entry["start_day"]),
                None if end is None else int(end),
            )
    raise ValueError(
        "the run spec schedules no quarantine entry for the payload window",
    )


def _zone_class_lookup(sim: Any) -> dict[str, str]:
    """Zone id -> dining service type, from the platform's spatial layout."""
    from engines.infection_dynamics_bridge import resolve_dining_service_type
    from engines.py_contam_bridge import load_spatial_layout

    layout = load_spatial_layout(sim.repo_root, sim.cfg)
    return {
        str(z.get("id")): resolve_dining_service_type(z)
        for z in layout.get("zones", [])
        if z.get("type") == "Dining"
    }


def _truth_window_counts(sim: Any, start: int, end: int | None) -> dict[str, int]:
    """Ever-infected non-seeded hosts by infection day vs the window."""
    seeded = set(getattr(sim.engine, "explicit_seed_agent_ids", None) or ())
    counts = {"before": 0, "during": 0, "after": 0}
    for agent in sim.engine.agents:
        if agent.agent_id in seeded or PATHOGEN_ID not in agent.infections:
            continue
        day = sim.clock.day_index(int(agent.infections[PATHOGEN_ID]["infection_epoch"]))
        if day < start:
            counts["before"] += 1
        elif end is None or day <= end:
            counts["during"] += 1
        else:
            counts["after"] += 1
    return counts


def _during_zone_class(
    sim: Any,
    dining_types: Mapping[str, str],
    agents_by_id: Mapping[int, Any],
    ev: Mapping[str, Any],
) -> str:
    zone = ev["zone"]
    ztype = sim.zone_types.get(zone)
    if ztype == "Cabin_Corridor":
        target = agents_by_id.get(ev["target_agent_id"])
        if target is not None and zone == getattr(target, "home_zone", None):
            return "cabin"
        return "corridor"
    if ztype == "Dining":
        stype = dining_types.get(zone, "")
        if stype in ("crew_mess", "galley"):
            return stype
        return "other"
    return "other"


def _attribution_block(
    sim: Any,
    ledger: QuarantineAttributionLedger,
    raw: dict[str, Any],
) -> dict[str, Any]:
    """The cell_payload_additions fields of the attribution design."""
    schedule_entry, start, end = _quarantine_window(raw)
    window_counts = _truth_window_counts(sim, start, end)
    activated = ledger.activated
    agents_by_id = {a.agent_id: a for a in sim.engine.agents}
    dining_types = _zone_class_lookup(sim)

    def _in_window(ev: Mapping[str, Any]) -> bool:
        day = sim.clock.day_index(int(ev["epoch"]))
        return day >= start and (end is None or day <= end)

    during_events = [ev for ev in ledger.events if _in_window(ev)]
    by_role = {"passenger": 0, "crew": 0}
    by_zone = {c: 0 for c in ZONE_CLASSES}
    by_route = {
        **{k: 0 for k in PATHWAY_EFFICIENCY_KEYS},
        "unknown": 0,
    }
    confined_passengers = 0
    for ev in during_events:
        agent = agents_by_id.get(ev["target_agent_id"])
        role = getattr(agent, "role", None)
        if role in by_role:
            by_role[role] += 1
        by_zone[_during_zone_class(sim, dining_types, agents_by_id, ev)] += 1
        by_route[ev["pathway"] if ev["pathway"] in by_route else "unknown"] += 1
        if role == "passenger" and ev["confined"]:
            confined_passengers += 1

    witness = {
        "protocol_id": schedule_entry["protocol_id"],
        "protocol_ids": ledger.protocol_ids,
        "window_days": [start, end],
        "activated": activated,
        "activation_epoch": ledger.activation_epoch,
        "confined_at_activation": ledger.confined_at_activation,
        "exempt_classes": ledger.exempt_classes,
        "invalid_reason": None if activated else "quarantine_never_activated",
    }
    return {
        "infections_before_quarantine": window_counts["before"],
        "infections_during_quarantine": (
            window_counts["during"] if activated else None
        ),
        "infections_after_quarantine": window_counts["after"],
        "during_quarantine_by_role": by_role if activated else None,
        "during_quarantine_by_zone_class": by_zone if activated else None,
        "during_quarantine_by_route": by_route if activated else None,
        "confined_passenger_infections_during_quarantine": (
            confined_passengers if activated else None
        ),
        "quarantine_witness": witness,
    }


def prepare_cell_run_spec(
    design: BoardingScreenDesign,
    cell: ScreenCell,
    *,
    num_epochs: int | None = None,
    repo_root: str = REPO_ROOT,
) -> dict[str, Any]:
    """Build the run spec one cell executes, arm overrides included."""
    arm_overrides = (
        design.arm_overrides(cell.arm_id)
        if design.arms and cell.arm_id is not None else {}
    )
    raw = build_fit_run_spec(
        cell.scenario_id, cell.theta, cell.seed,
        num_epochs=num_epochs, repo_root=repo_root,
        pathogen_pool_transport=arm_overrides.get("pathogen_pool_transport"),
    )
    apply_boarding_axis(
        raw,
        infection_age_days=cell.infection_age_days,
        imports=cell.imports,
        sanitary_visit_mode=design.sanitary_visit_mode,
    )
    apply_arm_overrides(
        raw, arm_overrides, profile=load_covid_profile(repo_root),
    )
    return raw


def cell_payload(
    design: BoardingScreenDesign,
    cell: ScreenCell,
    sim: Any,
    ledger: QuarantineAttributionLedger,
    raw: dict[str, Any],
) -> dict[str, Any]:
    """Read one finished simulation into the cell's payload."""
    syndromic = sim.modalities["syndromic"]
    obs = observables_from_modality(
        syndromic,
        scenario_id=cell.scenario_id,
        theta=cell.theta,
        seed=cell.seed,
        split_day=SPLIT_DAY,
        turn_day=TURN_DAY,
    )
    curve = syndromic.onset_observation_curve(PATHOGEN_ID)
    payload = {
        "observables": obs.as_dict(),
        "onset_curve": {
            str(day): dict(roles) for day, roles in sorted(curve.items())
        },
        "first_onset_day": _first_onset_day(curve),
        "sanitary_activity": {
            k: float(v) for k, v in dict(sim.tx_core.sanitary_telemetry).items()
        },
        **_index_geometry(
            sim.engine, cell, sim.pathogen_profiles[PATHOGEN_ID],
        ),
        **_truth_counts(sim.engine),
        KEY_VSP_MAX: float(
            getattr(sim.engine, "vsp_reported_case_fraction_max", 0.0),
        ),
    }
    if design.arms:
        payload.update({
            "arm_id": cell.arm_id,
            **_attribution_block(sim, ledger, raw),
        })
    return payload


def simulate_screen_cell(
    design: BoardingScreenDesign,
    cell: ScreenCell,
    *,
    num_epochs: int | None = None,
    repo_root: str = REPO_ROOT,
) -> dict[str, Any]:
    """Run one cell and return its observables, onset curve and witness."""
    raw = prepare_cell_run_spec(
        design, cell, num_epochs=num_epochs, repo_root=repo_root,
    )
    ledger = QuarantineAttributionLedger()
    sim = run_fit_spec(raw, repo_root=repo_root, epoch_observer=ledger.observe)
    return cell_payload(design, cell, sim, ledger, raw)


ScreenRunner = Any


def run_cell(
    design: BoardingScreenDesign,
    cell: ScreenCell,
    *,
    runner: ScreenRunner = simulate_screen_cell,
) -> dict[str, Any]:
    """Run one cell and return the payload the array child uploads."""
    result = runner(design, cell)
    return {
        "design_id": design.design_id,
        "sanitary_visit_mode": design.sanitary_visit_mode,
        "cell": cell.as_dict(),
        **result,
    }


# ── merge: the surface ────────────────────────────────────────────────────

def _quantile(values: Sequence[float], q: float) -> float:
    return float(np.quantile(np.asarray(values, dtype=float), q))


def _summary(values: Sequence[float]) -> dict[str, float | int] | None:
    if not values:
        return None
    return {
        "n": len(values),
        "mean": float(np.mean(values)),
        "median": _quantile(values, 0.5),
        "q05": _quantile(values, INTERVAL[0]),
        "q95": _quantile(values, INTERVAL[1]),
    }


def _observables(payload: dict[str, Any]) -> HullObservables:
    raw = dict(payload["observables"])
    raw.pop("positive_share", None)
    raw.pop("asymptomatic_share", None)
    return HullObservables(**raw)


def _group(
    cells: Iterable[ScreenCell],
    payloads: dict[str, dict[str, Any]],
) -> dict[tuple[float, float, int, str | None], dict[int, dict[str, Any]]]:
    grouped: dict[
        tuple[float, float, int, str | None], dict[int, dict[str, Any]],
    ] = {}
    for cell in cells:
        payload = payloads.get(cell.key)
        if payload is None:
            continue
        grouped.setdefault(
            (cell.theta, cell.infection_age_days, cell.imports, cell.arm_id),
            {},
        )[cell.seed] = payload
    return grouped


def _witness(payloads: Iterable[dict[str, Any]], mode: str) -> dict[str, Any]:
    visits = [
        float(p.get("sanitary_activity", {}).get("visits", 0.0)) for p in payloads
    ]
    executed = sum(1 for v in visits if v > 0)
    return {
        "declared_mode": mode,
        "cells": len(visits),
        "cells_with_visits": executed,
        "consistent": (executed == len(visits)) if mode != "none" else (executed == 0),
    }


def _attack_quantiles(
    rates: Sequence[float],
) -> dict[str, float | None]:
    if not rates:
        return {
            f"q{int(q * 100):02d}": None
            for q in (0.10, 0.25, 0.50, 0.75, 0.90)
        }
    return {
        f"q{int(q * 100):02d}": _quantile(rates, q)
        for q in (0.10, 0.25, 0.50, 0.75, 0.90)
    }


def _index_geometry_criterion(
    by_seed: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Share of seeds whose index host was onset-before-boarding and shedding.

    Payloads written before the geometry fields existed carry no verdict at
    all, rather than reading a missing field as a failure.
    """
    has_geometry = any(KEY_INDEX_ONSET_DAY in p for p in by_seed.values())
    geometry_pass = [
        (p.get(KEY_INDEX_ONSET_DAY) is not None
         and float(p[KEY_INDEX_ONSET_DAY]) <= 0.0
         and bool(p.get(KEY_INDEX_SHEDDING_AT_DAY0)))
        for p in by_seed.values()
    ] if has_geometry else None
    pass_fraction = (
        float(np.mean(geometry_pass)) if geometry_pass else (0.0 if has_geometry else None)
    )
    return {
        "index_geometry_pass_fraction": pass_fraction,
        "index_geometry_ok": (
            None if pass_fraction is None
            else bool(pass_fraction >= INDEX_GEOMETRY_PASS_FRACTION_MIN)
        ),
    }


def _t1_criterion(
    obs: dict[int, HullObservables],
    t1: dict[str, Any],
) -> dict[str, Any]:
    """The covid.T1 onset-count and early-share admissibility criterion."""
    onsets = [o.recorded_onsets for o in obs.values()]
    before_share = [
        o.onsets_before_split_day / o.recorded_onsets
        for o in obs.values() if o.recorded_onsets > 0
    ]
    t1_onsets = float(t1["recorded_onsets"])
    t1_before_share = float(t1["onsets_before_day"]) / t1_onsets
    before_median = _quantile(before_share, 0.5) if before_share else None
    return {
        "recorded_onsets_p10": _quantile(onsets, 0.10),
        "recorded_onsets_p90": _quantile(onsets, 0.90),
        "before_share_median": before_median,
        "t1_ok": bool(
            _quantile(onsets, 0.10) <= t1_onsets <= _quantile(onsets, 0.90)
            and before_median is not None
            and abs(before_median - t1_before_share) <= 0.10
        ),
    }


def _t3_criterion(
    obs: dict[int, HullObservables],
    t3: dict[str, Any],
) -> dict[str, Any]:
    """The covid.T3 campaign positives and specimen-count criterion."""
    positives = [o.campaign_positives for o in obs.values()]
    specimens = [o.campaign_specimens for o in obs.values()]
    t3_positives = float(t3["cumulative_positives"])
    t3_tests = float(t3["cumulative_tests"])
    specimens_median = _quantile(specimens, 0.5) if specimens else None
    return {
        "campaign_positives_p10": _quantile(positives, 0.10),
        "campaign_positives_p90": _quantile(positives, 0.90),
        "campaign_specimens_median": specimens_median,
        "t3_ok": bool(
            _quantile(positives, 0.10) <= t3_positives <= _quantile(positives, 0.90)
            and specimens_median is not None
            and abs(specimens_median / t3_tests - 1.0) <= 0.15
        ),
    }


def _attack_rate_stats(
    by_seed: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Attack-rate quantiles and the declared tail probabilities."""
    rates = [
        float(p[KEY_ATTACK_RATE])
        for p in by_seed.values()
        if p.get(KEY_ATTACK_RATE) is not None
    ]
    return {
        "attack_rate_quantiles": _attack_quantiles(rates),
        "p_attack_ge_0p10": (
            float(np.mean([r >= 0.10 for r in rates])) if rates else None
        ),
        "p_attack_le_0p01": (
            float(np.mean([r <= 0.01 for r in rates])) if rates else None
        ),
    }


def _vsp_crossing_stats(
    by_seed: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Share of seeds crossing the VSP threshold, and their attack rates."""
    vsp_maxima = [
        float(p[KEY_VSP_MAX])
        for p in by_seed.values()
        if p.get(KEY_VSP_MAX) is not None
    ]
    crossing_ids = [
        seed for seed, p in by_seed.items()
        if p.get(KEY_VSP_MAX) is not None
        and float(p[KEY_VSP_MAX]) >= VSP_CROSSING_THRESHOLD
    ]
    crossing_rates = [
        float(by_seed[s][KEY_ATTACK_RATE]) for s in crossing_ids
        if by_seed[s].get(KEY_ATTACK_RATE) is not None
    ]
    return {
        "vsp_threshold_crossing_fraction": (
            float(np.mean([m >= VSP_CROSSING_THRESHOLD for m in vsp_maxima]))
            if vsp_maxima else None
        ),
        "attack_rate_quantiles_given_vsp_crossing": (
            _attack_quantiles(crossing_rates) if crossing_rates else None
        ),
    }


def _onset_mass_diagnostic(
    obs: dict[int, HullObservables],
    t1: dict[str, Any],
) -> dict[str, Any]:
    """Diagnostic only, v9's near-critical discriminator.

    The share of seeds whose ``recorded_onsets`` lands inside [0.5x, 2x] the
    covid.T1 target. Never enters t1_ok / t3_ok / index_geometry_ok.
    """
    t1_onsets = float(t1["recorded_onsets"])
    onsets_per_seed = [o.recorded_onsets for o in (obs[s] for s in sorted(obs))]
    bounds = [0.5 * t1_onsets, 2.0 * t1_onsets]
    return {
        "recorded_onsets_per_seed": onsets_per_seed,
        "onset_mass_near_target": (
            float(np.mean([
                bounds[0] <= x <= bounds[1] for x in onsets_per_seed
            ]))
            if onsets_per_seed else None
        ),
        "onset_mass_near_target_bounds": bounds,
    }


def _admissibility(
    by_seed: dict[int, dict[str, Any]],
    obs: dict[int, HullObservables],
    targets: Any,
) -> dict[str, Any]:
    """The v7 pre-declared criteria, evaluated per the design's own text.

    Each registered criterion is computed by its own helper; the onset-mass
    block is a diagnostic and feeds no gate.
    """
    t1 = targets.assert_fittable("covid.T1").values
    t3 = targets.assert_fittable("covid.T3").values
    t1_part = _t1_criterion(obs, t1)
    t3_part = _t3_criterion(obs, t3)
    return {
        **_index_geometry_criterion(by_seed),
        **{k: v for k, v in t1_part.items() if k != "t1_ok"},
        **{k: v for k, v in t3_part.items() if k != "t3_ok"},
        "t1_ok": t1_part["t1_ok"],
        "t3_ok": t3_part["t3_ok"],
        **_attack_rate_stats(by_seed),
        **_onset_mass_diagnostic(obs, t1),
        **_vsp_crossing_stats(by_seed),
    }


def _cell_summary(
    design: BoardingScreenDesign,
    by_seed: dict[int, dict[str, Any]],
    targets: Any | None = None,
) -> dict[str, Any]:
    obs = {seed: _observables(p) for seed, p in by_seed.items()}
    firsts = [
        int(p["first_onset_day"]) for p in by_seed.values()
        if p.get("first_onset_day") is not None
    ]
    asym = [
        o.asymptomatic_share for o in obs.values()
        if o.asymptomatic_share is not None
    ]
    early_share = [
        o.onsets_before_split_day / o.recorded_onsets
        for o in obs.values() if o.recorded_onsets > 0
    ]
    taken_off = [
        o for o in obs.values()
        if o.recorded_onsets >= design.takeoff_recorded_onsets
    ]
    return {
        "seeds": sorted(obs),
        "recorded_onsets": _summary([o.recorded_onsets for o in obs.values()]),
        "onsets_before_split_day": _summary(
            [o.onsets_before_split_day for o in obs.values()],
        ),
        "early_onset_share": _summary(early_share),
        "first_onset_day": _summary(firsts),
        "campaign_positives": _summary(
            [o.campaign_positives for o in obs.values()],
        ),
        "asymptomatic_share": _summary(asym),
        "takeoff_probability": float(np.mean([
            o.recorded_onsets >= design.takeoff_recorded_onsets
            for o in obs.values()
        ])),
        "conditional_on_takeoff": {
            "n": len(taken_off),
            "recorded_onsets": _summary([o.recorded_onsets for o in taken_off]),
            "onsets_before_split_day": _summary(
                [o.onsets_before_split_day for o in taken_off],
            ),
            "campaign_positives": _summary(
                [o.campaign_positives for o in taken_off],
            ),
        },
        "sanitary_witness": _witness(by_seed.values(), design.sanitary_visit_mode),
        **(_admissibility(
            by_seed, obs, targets or load_fit_targets(),
        )),
    }


def _paired_deltas(
    base: dict[int, dict[str, Any]],
    other: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Per-seed (other - baseline) on the two scored counts."""
    shared = sorted(set(base) & set(other))
    if not shared:
        return {"n": 0}
    b = {s: _observables(base[s]) for s in shared}
    o = {s: _observables(other[s]) for s in shared}
    onsets = [o[s].recorded_onsets - b[s].recorded_onsets for s in shared]
    early = [
        o[s].onsets_before_split_day - b[s].onsets_before_split_day
        for s in shared
    ]
    return {
        "n": len(shared),
        "recorded_onsets": _summary(onsets),
        "onsets_before_split_day": _summary(early),
        "seeds_with_more_early_onsets": sum(1 for d in early if d > 0),
    }


def merge_screen(
    design: BoardingScreenDesign,
    payloads: dict[str, dict[str, Any]],
    *,
    allow_partial: bool = False,
    targets: Any | None = None,
) -> dict[str, Any]:
    """Pool finished cells into the boarding surface."""
    cells = enumerate_cells(design)
    grouped = _group(cells, payloads)
    expected = len(cells)
    found = sum(len(v) for v in grouped.values())
    if found < expected and not allow_partial:
        raise ValueError(
            f"{found} of {expected} cells present; pass allow_partial to "
            "summarise an incomplete screen",
        )
    resolved_targets = targets or load_fit_targets()
    surface = []
    for theta, age, imports in design.axis_points:
        for arm_id in design.arm_ids or (None,):
            if design.arms:
                # Arm designs pair on the first arm at the same axis point.
                base = grouped.get(
                    (theta, age, imports, design.baseline_arm_id), {},
                )
                is_baseline = arm_id == design.baseline_arm_id
            else:
                base = grouped.get((theta, *design.baseline, None), {})
                is_baseline = (age, imports) == design.baseline
            by_seed = grouped.get((theta, age, imports, arm_id), {})
            if not by_seed:
                continue
            entry = {
                "theta": theta,
                "infection_age_days": age,
                "imports": imports,
                "arm_id": arm_id,
                "is_baseline": is_baseline,
                **_cell_summary(design, by_seed, resolved_targets),
                "delta_vs_baseline": _paired_deltas(base, by_seed),
            }
            surface.append(entry)
    return {
        "design": design.as_dict(),
        "coverage": {"expected": expected, "found": found, "partial": found < expected},
        "sanitary_witness": _witness(payloads.values(), design.sanitary_visit_mode),
        "surface": surface,
        "note": (
            "A screen, not a fit. Cells are paired by seed against the declared "
            "scenario (infection_age_days 0, imports 1) at the same Theta. "
            "No entry here may be used to move the scenario."
        ),
    }
