"""COVID-RHYTHM-01: the four-class rhythm A/B cell machinery.

The rhythm layer (docs/rhythm/rhythm_spec.md, PRs #741/#742) is the
exposure-set partitioning mechanism the sars_cov2 takeoff failure is
measured against: TAKEOFF-ATTR-01 found every admissible-Theta takeoff cell
dosing ~705 hosts per epoch with challenged_share_of_aboard = 1.0 — the
ship-wide pool behaviour the layer exists to remove.

This module declares the paired A/B — the same takeoff-conditioned cells
with ``rhythm.enabled`` false vs true — across the four real cruise
classes the event catalogs cover:

- ``mega_cruise`` and ``expedition_cruise`` legs are the declared replays
  (diamond_princess_2020, greg_mortimer_2020) — the conditioning is the
  record, identical to TAKEOFF-ATTR-01.
- ``contemporary_cruise`` and ``classic_cruise`` legs are *generic takeoff
  cells*: the covid arm has no event record for those hulls, so the cell
  carries the TAKEOFF-ATTR-01 index geometry verbatim (one import,
  infection_age 6.8 d, onset day −1.0, departs day 5.0, dwell_weighted
  sanitary visits, SOP-017 days 16–30, 768 hourly epochs) on the
  platform's own complement. ``classic_cruise`` books all 1332 passenger
  berths + 560 crew (the layout's capacity); ``contemporary_cruise`` its
  nominal 2100 + 900.

Cells are leg-major, then arm (off before on), then seed, so the canary is
index 0 (mega/off/seed 20200205) with its on-arm pair at index 20.

The A/B flag is written into every cell spec explicitly —
``config_overrides.rhythm.enabled`` — so the spec alone records which arm
ran; the off arm is the labelled baseline the rhythm spec claims is
byte-identical to pre-layer draws.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from typing import Any

from engines.py_contam_bridge import load_spatial_layout
from engines.rhythm_layer import _CORRIDOR_ROLES
from picard_framework.covid_boarding_screen import (
    PATHOGEN_ID,
    QUARANTINE_PROTOCOL_ID,
    SANITARY_VISIT_MODES,
    VOYAGE_MODE_DECLARED,
    VOYAGE_MODES,
    _generic_age_stream,
    apply_boarding_axis,
)
from picard_framework.covid_hull_scenarios import (
    BUNDLE_ID,
)
from picard_framework.covid_theta_fit import (
    build_fit_run_spec,
    load_covid_profile,
    theta_profile_overrides,
)
from picard_framework.pathogen_overrides import isolate_arm_overrides
from simulation_utils.paths import load_validated_json, validated_open

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

# The TAKEOFF-ATTR-01 / v12 stage-2 conditioning, verbatim. The generic
# legs carry exactly this index geometry; the scenario legs inherit it
# from the hull records.
DECLARED_INFECTION_AGE_DAYS = 6.8
DECLARED_ONSET_DAY = -1.0
DECLARED_DEPARTURE_DAY = 5.0
DECLARED_IMPORTS = 1
SOP017_WINDOW = (16, 30)
MOLECULAR_ASCERTAINMENT_START_DAY = 14
EPOCHS_PER_DAY = 24


@dataclass(frozen=True)
class RhythmLeg:
    """One cruise class's cell recipe inside the A/B."""

    class_id: str
    platform_id: str
    kind: str                       # "scenario" | "generic"
    seed_base: int
    seeds: int
    scenario_id: str | None = None
    passengers: int = 0
    crew: int = 0
    duration_days: int = 32
    sop017_window: tuple[int, int] = SOP017_WINDOW
    voyage_mode: str = VOYAGE_MODE_DECLARED

    @property
    def seed_values(self) -> tuple[int, ...]:
        return tuple(self.seed_base + i for i in range(self.seeds))

    @property
    def label(self) -> str:
        """The cell's scenario label: the record id or the class id."""
        return self.scenario_id or self.class_id


@dataclass(frozen=True)
class RhythmABDesign:
    """The A/B as declared before any cell ran."""

    design_id: str
    theta: float
    infection_age_days: float
    imports: int
    sanitary_visit_mode: str
    takeoff_recorded_onsets: int
    arms: tuple[dict[str, Any], ...]
    legs: tuple[RhythmLeg, ...]
    seed_ring_readout: bool = False

    def __post_init__(self) -> None:
        if not math.isfinite(self.theta) or self.theta <= 0:
            raise ValueError(f"theta must be finite and positive, got {self.theta!r}")
        if self.sanitary_visit_mode not in SANITARY_VISIT_MODES:
            raise ValueError(
                f"sanitary_visit_mode must be one of {SANITARY_VISIT_MODES}, "
                f"got {self.sanitary_visit_mode!r}",
            )
        arm_ids = [a.get("arm_id") for a in self.arms]
        if len(arm_ids) != 2 or len(set(arm_ids)) != 2:
            raise ValueError("the rhythm A/B declares exactly two distinct arms")
        for arm in self.arms:
            overrides = set((arm.get("overrides") or {}).keys())
            if overrides != {"rhythm"}:
                raise ValueError(
                    f"arm {arm.get('arm_id')!r} may override 'rhythm' only, "
                    f"got {sorted(overrides)}",
                )
            enabled = (arm.get("overrides") or {}).get("rhythm", {}).get("enabled")
            if not isinstance(enabled, bool):
                raise ValueError(
                    f"arm {arm.get('arm_id')!r} must set rhythm.enabled to a "
                    f"boolean, got {enabled!r}",
                )
        class_ids = [leg.class_id for leg in self.legs]
        if len(set(class_ids)) != len(class_ids):
            raise ValueError("leg class_ids must be distinct")
        for leg in self.legs:
            if leg.voyage_mode not in VOYAGE_MODES:
                raise ValueError(
                    f"leg {leg.class_id!r} voyage_mode must be one of "
                    f"{VOYAGE_MODES}, got {leg.voyage_mode!r}",
                )
            if leg.kind not in ("scenario", "generic"):
                raise ValueError(
                    f"leg {leg.class_id!r} kind must be 'scenario' or "
                    f"'generic', got {leg.kind!r}",
                )
            if leg.kind == "scenario" and not leg.scenario_id:
                raise ValueError(
                    f"scenario leg {leg.class_id!r} needs a scenario_id",
                )
            if leg.kind == "generic" and leg.passengers < 1:
                raise ValueError(
                    f"generic leg {leg.class_id!r} needs a passenger count",
                )

    def leg(self, class_id: str) -> RhythmLeg:
        for leg in self.legs:
            if leg.class_id == class_id:
                return leg
        raise KeyError(f"unknown class_id {class_id!r}")

    def arm_enabled(self, arm_id: str) -> bool:
        """The rhythm flag one arm writes into every cell spec."""
        for arm in self.arms:
            if arm.get("arm_id") == arm_id:
                return bool((arm.get("overrides") or {})["rhythm"]["enabled"])
        raise KeyError(f"unknown arm_id {arm_id!r}")


@dataclass(frozen=True)
class RhythmCell:
    """One (class, arm, seed) the array evaluates."""

    index: int
    class_id: str
    platform_id: str
    scenario_id: str            # record id or class label
    theta: float
    infection_age_days: float
    imports: int
    seed: int
    arm_id: str

    @property
    def key(self) -> str:
        exponent = f"{math.log10(self.theta):.2f}".replace(".", "p")
        age = f"{self.infection_age_days:g}".replace(".", "p")
        return (
            f"rhythm_{self.class_id}_theta1e{exponent}_age{age}d"
            f"_imports{self.imports}_seed{self.seed}_arm{self.arm_id}.json"
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "class_id": self.class_id,
            "platform_id": self.platform_id,
            "scenario_id": self.scenario_id,
            "theta": self.theta,
            "infection_age_days": self.infection_age_days,
            "imports": self.imports,
            "seed": self.seed,
            "arm_id": self.arm_id,
            "key": self.key,
        }


def enumerate_rhythm_cells(design: RhythmABDesign) -> tuple[RhythmCell, ...]:
    """Every cell in a fixed order: leg, then arm, then seed."""
    cells: list[RhythmCell] = []
    for leg in design.legs:
        for arm in design.arms:
            for seed in leg.seed_values:
                cells.append(RhythmCell(
                    index=len(cells),
                    class_id=leg.class_id,
                    platform_id=leg.platform_id,
                    scenario_id=leg.label,
                    theta=float(design.theta),
                    infection_age_days=float(design.infection_age_days),
                    imports=int(design.imports),
                    seed=int(seed),
                    arm_id=str(arm["arm_id"]),
                ))
    return tuple(cells)


def _generic_leg_spec(
    design: RhythmABDesign,
    leg: RhythmLeg,
    cell: RhythmCell,
    *,
    repo_root: str,
) -> dict[str, Any]:
    """The takeoff-conditioned run spec for a class without an event record.

    Mirrors the declared replay's spec shape — the DP conditioning
    verbatim, population at the platform's own complement — so the cells
    differ from the record legs only in hull geometry and aboard count.
    """
    epochs = int(leg.duration_days) * EPOCHS_PER_DAY
    pax, crew = int(leg.passengers), int(leg.crew)
    total = pax + crew
    overrides: dict[str, Any] = {
        "num_epochs": epochs,
        "epoch_duration_hours": 1.0,
        "natural_history_clock": "hours",
        "random_seed": int(cell.seed),
        "voyage": {
            "epoch_duration_hours": 1.0,
            "total_epochs": epochs,
        },
        "ship_graph": {
            "num_agents": total,
            "immune_fraction": 0.0,
            "agent_roles": {
                "passenger_fraction": pax / total,
                "crew_fraction": crew / total,
            },
            "agent_classes": [
                {
                    "class_id": "passenger_general",
                    "role_group": "passenger",
                    "count": pax,
                    "fraction": pax / total,
                    "home_zone_preference": "PC_",
                },
                {
                    "class_id": "crew_general",
                    "role_group": "crew",
                    "count": crew,
                    "fraction": crew / total,
                    "home_zone_preference": "CC_",
                },
            ],
        },
        "initiation": {
            "explicit_seeds": [
                {
                    "pathogen": PATHOGEN_ID,
                    "count": int(design.imports),
                    "role": "passenger",
                    "epoch": 0,
                    "infection_age_days": float(design.infection_age_days),
                    "departure_day": DECLARED_DEPARTURE_DAY,
                    "onset_day": DECLARED_ONSET_DAY,
                },
            ],
            "boarding": {PATHOGEN_ID: {"enabled": False}},
        },
        "scenario_schedule": {
            "protocols": [
                {
                    "protocol_id": QUARANTINE_PROTOCOL_ID,
                    "start_day": int(leg.sop017_window[0]),
                    "end_day": int(leg.sop017_window[1]),
                },
            ],
        },
        "syndromic": {
            "molecular_ascertainment_start_day": (
                MOLECULAR_ASCERTAINMENT_START_DAY
            ),
            "retest_negatives_on_indication": True,
        },
        "transmission": {
            "sanitary_visit_mode": design.sanitary_visit_mode,
        },
        "wearable_monitoring": {"enabled": False},
        "diagnostic_cascade": {"enabled": False},
    }
    profile = load_covid_profile(repo_root)
    pathogen_overrides = isolate_arm_overrides(
        BUNDLE_ID, PATHOGEN_ID, {PATHOGEN_ID: {"initial_infected": None}},
    ) or {}
    pathogen_overrides.setdefault(PATHOGEN_ID, {}).update(
        theta_profile_overrides(profile, design.theta),
    )
    return {
        "schema_version": "1.0.0",
        "catalog": {
            "platform_id": leg.platform_id,
            "pathogen_bundle_id": BUNDLE_ID,
        },
        "run": {
            "random_seed": int(cell.seed),
            "num_epochs": epochs,
            "write_ground_truth": False,
            "history_retention": "compact",
        },
        "config_overrides": overrides,
        "pathogen_overrides": pathogen_overrides,
    }


def _scenario_leg_spec(
    design: RhythmABDesign,
    leg: RhythmLeg,
    cell: RhythmCell,
    *,
    repo_root: str,
) -> dict[str, Any]:
    """The TAKEOFF-ATTR-01 replay spec for a record hull.

    ``voyage_mode`` on the leg selects the boarding axis: ``declared`` for
    the Diamond Princess (the takeoff conditioning verbatim) and
    ``generic`` for the Greg Mortimer — the held-out hull's seed declares
    no onset day, so the v12 stage-3 convention draws its incubation and
    drops the ascertainment gate (the record's dates are DP particulars).
    """
    raw = build_fit_run_spec(
        leg.scenario_id or "", cell.theta, cell.seed,
        repo_root=repo_root,
    )
    profile = load_covid_profile(repo_root)
    apply_boarding_axis(
        raw,
        infection_age_days=cell.infection_age_days,
        imports=cell.imports,
        sanitary_visit_mode=design.sanitary_visit_mode,
        voyage_mode=leg.voyage_mode,
        incubation_profile=profile,
        age_stream=(
            _generic_age_stream(cell.seed)
            if leg.voyage_mode == "generic" else None
        ),
    )
    return raw


def prepare_rhythm_cell_spec(
    design: RhythmABDesign,
    cell: RhythmCell,
    *,
    repo_root: str = REPO_ROOT,
) -> dict[str, Any]:
    """Build the run spec one cell executes, arm flag written explicitly."""
    leg = design.leg(cell.class_id)
    if leg.kind == "scenario":
        raw = _scenario_leg_spec(design, leg, cell, repo_root=repo_root)
    else:
        raw = _generic_leg_spec(design, leg, cell, repo_root=repo_root)
    raw.setdefault("config_overrides", {})["rhythm"] = {
        "enabled": design.arm_enabled(cell.arm_id),
    }
    return raw


def load_rhythm_design(path: str) -> RhythmABDesign:
    """Parse the A/B design file; every criterion must already be in it."""
    with validated_open(
        path, allowed_roots=(os.path.dirname(path) or ".",), encoding="utf-8",
    ) as handle:
        raw = json.load(handle)
    legs = tuple(
        RhythmLeg(
            class_id=str(leg["class_id"]),
            platform_id=str(leg["platform_id"]),
            kind=str(leg["kind"]),
            seed_base=int(leg["seed_base"]),
            seeds=int(leg["seeds"]),
            scenario_id=leg.get("scenario_id"),
            passengers=int(leg.get("passengers") or 0),
            crew=int(leg.get("crew") or 0),
            duration_days=int(leg.get("duration_days") or 32),
            sop017_window=tuple(
                leg.get("sop017_window") or SOP017_WINDOW
            ),
            voyage_mode=str(leg.get("voyage_mode") or VOYAGE_MODE_DECLARED),
        )
        for leg in raw["legs"]
    )
    return RhythmABDesign(
        design_id=str(raw["design_id"]),
        theta=float(raw["theta"]),
        infection_age_days=float(raw["infection_age_days"]),
        imports=int(raw["imports"]),
        sanitary_visit_mode=str(raw["sanitary_visit_mode"]),
        takeoff_recorded_onsets=int(raw["takeoff_recorded_onsets"]),
        arms=tuple(raw["arms"]),
        legs=legs,
    )


# ── zone-class helpers for the instruments ─────────────────────────────

_CREW_ZONE_MARKERS = (
    "crew", "galley", "engine", "engcontrol", "bridge",
    "laundry", "stores", "wastetreat",
)


def crew_zone_names(platform_id: str, *, repo_root: str = REPO_ROOT) -> frozenset[str]:
    """Zones passengers must never occupy: crew-flagged by name or venue."""
    layout = load_spatial_layout(repo_root, _platform_cfg(platform_id))
    return frozenset(
        str(z["id"])
        for z in layout.get("zones", [])
        if any(m in str(z["id"]).lower() for m in _CREW_ZONE_MARKERS)
    )


def _catalog_for(platform_id: str, *, repo_root: str = REPO_ROOT) -> dict[str, Any] | None:
    """The rhythm event catalog covering *platform_id*, else None."""
    path = os.path.join(repo_root, "data", "rhythm", "event_catalogs.json")
    if not os.path.isfile(path):
        return None
    doc = load_validated_json(
        path, "rhythm_event_catalogs.schema.json",
        allowed_roots=(repo_root,),
    )
    for catalog in (doc.get("ship_class_catalogs") or {}).values():
        if platform_id in (catalog.get("platforms") or []):
            return catalog
    return None


def transit_zone_names(platform_id: str, *, repo_root: str = REPO_ROOT) -> frozenset[str]:
    """Where synchronized-end fronts land — mirrors _resolve_corridor_zones.

    The engine's corridor pick draws from the catalog's corridor-role
    venues first, then every Cabin_Corridor-typed zone the layout carries;
    the occupancy tally must cover the same set or the fronts are missed.
    """
    layout = load_spatial_layout(repo_root, _platform_cfg(platform_id))
    zones: set[str] = set()
    catalog = _catalog_for(platform_id, repo_root=repo_root)
    if catalog is not None:
        known = {str(z["id"]) for z in layout.get("zones", [])}
        venue_map = catalog.get("venue_map", {})
        for role in _CORRIDOR_ROLES:
            for name in venue_map.get(role, []) or []:
                if str(name) in known:
                    zones.add(str(name))
    for z in layout.get("zones", []):
        if str(z.get("type")) == "Cabin_Corridor":
            zones.add(str(z["id"]))
    return frozenset(zones)


def _platform_cfg(platform_id: str) -> dict[str, Any]:
    """Minimal cfg shape load_spatial_layout reads for the platform path."""
    return {
        "ship_graph": {
            "spatial_layout": f"data/platforms/{platform_id}/spatial_layout.json",
        },
    }


def sync_end_epoch_mask(
    platform_id: str,
    total_epochs: int,
    *,
    repo_root: str = REPO_ROOT,
    sop_window: tuple[int, int] | None = None,
) -> list[bool]:
    """Epochs containing a passenger synchronized-end window's egress.

    Computed statically from the sea-day event catalog — the same mask on
    both arms, so the corridor-occupancy correlation is arm-symmetric: off
    is the no-program-clock null, on is the claimed effect. Events are
    filtered to passenger-eligible ones, and days inside *sop_window*
    (SOP-017 confinement, which cancels all passenger events) are masked
    out — the fronts the claim predicts only exist while the program runs.
    """
    mask = [False] * int(total_epochs)
    catalog = _catalog_for(platform_id, repo_root=repo_root)
    if catalog is None:
        return mask
    template = (catalog.get("baseline_day_templates") or {}).get("sea_day") or {}
    end_minutes: list[int] = []
    for event in template.get("events", []):
        role_groups = set(
            (event.get("eligible") or {}).get("role_groups") or []
        )
        if role_groups and "passenger" not in role_groups:
            continue
        if str(event.get("egress_mode")) != "synchronized_end":
            continue
        window = event.get("window") or []
        try:
            start = _hhmm_to_min(str(window[0]))
            end = _hhmm_to_min(str(window[1]))
        except (IndexError, TypeError, ValueError):
            continue
        if end <= start:
            # Window wraps midnight (e.g. a 22:00-01:00 lounge set).
            end += 24 * 60  # clock-exempt: minutes-per-day wrap, not a unit conversion
        seatings = 1
        if str(event.get("event_class")) == "meal_seating":
            seatings = _max_meal_seatings(
                event, catalog, platform_id, repo_root=repo_root,
            )
        # The engine deals one occurrence per event absent a SOP frequency
        # multiplier; multi-seating events pour out once per seat turn.
        turn = max((end - start) // seatings, 1)
        for seat in range(seatings):
            end_minutes.append(
                (start + (seat + 1) * turn) % (24 * 60),  # clock-exempt: minute-of-day wrap
            )
    if not end_minutes:
        return mask
    for epoch in range(int(total_epochs)):
        day = epoch // 24  # clock-exempt: epoch->day on the hourly clock
        if sop_window and sop_window[0] <= day <= sop_window[1]:
            continue
        hour = epoch % 24  # clock-exempt: hour-of-day arithmetic
        lo, hi = hour * 60, (hour + 1) * 60
        if any(lo < m <= hi for m in end_minutes):
            mask[epoch] = True
    return mask


def _hhmm_to_min(hhmm: str) -> int:
    hh, mm = hhmm.split(":")
    return int(hh) * 60 + int(mm)


def _max_meal_seatings(
    event: dict[str, Any],
    catalog: dict[str, Any],
    platform_id: str,
    *,
    repo_root: str,
) -> int:
    """The venue's declared sittings, matching the layer's own resolution."""
    layout = load_spatial_layout(repo_root, _platform_cfg(platform_id))
    zones = {
        str(z["id"]): z for z in layout.get("zones", [])
    }
    names: set[str] = set()
    venue_map = catalog.get("venue_map", {})
    for role in event.get("venue_roles", []) or []:
        for name in venue_map.get(role, []) or []:
            names.add(str(name))
    best = 1
    for name in names:
        zone = zones.get(name)
        if zone is None:
            continue
        try:
            best = max(best, int(zone.get("meal_seatings") or 1))
        except (TypeError, ValueError):
            continue
    return best
