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
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import product
from typing import Any

import numpy as np

from engines.incubation import HostIncubationState, IncubationModel
from engines.infection_dynamics_bridge import (
    earliest_shed_epoch,
    ever_presented,
)
from engines.sim_clock import SimClock
from engines.transmission_core import PATHWAY_EFFICIENCY_KEYS, TransmissionCore
from picard_framework.covid_fit_targets import load_fit_targets
from picard_framework.covid_hull_scenarios import REPO_ROOT, load_hull_scenarios
from picard_framework.covid_theta_fit import (
    PATHOGEN_ID,
    HullObservables,
    build_fit_run_spec,
    build_fit_sim,
    load_covid_profile,
    observables_from_modality,
    run_fit_spec,
)
from picard_framework.pathogen_overrides import deep_merge_dict
from simulation_utils.paths import validated_open

DESIGN_REL = os.path.join(
    "picard_framework", "runs", "covid_boarding_screen_v1_design.json",
)
SANITARY_VISIT_MODES = ("none", "dwell_weighted")
# A screen's voyage shape: the declared replay carries the record's onset
# and departure on its explicit seed; a generic voyage drops both, draws the
# import's infection age from the profile's incubation distribution, and
# runs a fixed-length cruise with no dated interventions.
VOYAGE_MODE_DECLARED = "declared"
VOYAGE_MODE_GENERIC = "generic"
VOYAGE_MODES = (VOYAGE_MODE_DECLARED, VOYAGE_MODE_GENERIC)
GENERIC_VOYAGE_DAYS = 7.0
# covid.H3's recorded attack-rate window (Willebrand 2022, 104 voyages on 79
# ships): the stage-1 selector of covid_theta_screen_v11. The numerator is
# the RECORDED channel — recorded_onsets / aboard_total per voyage — not the
# truth channel the attack-rate block pools.
FLEET_MEDIAN_WINDOW = (0.0005, 0.008)
FLEET_IQR_WINDOW = (0.0003, 0.015)
FLEET_MEAN_MAX = 0.06
# Attribution-design arm axes (covid_quarantine_attribution_v1). Every key a
# declared arm may override; anything else refuses at design load rather than
# drifting into a silently-ignored counterfactual.
ARM_OVERRIDE_KEYS = frozenset({
    "scheduled_protocol_id",
    "scheduled_protocol_window",
    "pathogen_pool_transport",
    "near_field_air_mode",
    "profile_route_efficiency_multipliers",
    "infection_counters",
    "transmission_overrides",
    "pathogen_overrides",
    "seed_patch",
    "ship_graph_overrides",
    "dose_response_frailty",
    "hazard_frailty",
})
# The embarkation-immunity structure an arm may write onto
# ``config_overrides.ship_graph``: the pooled depth (``immune_fraction``)
# and IMMUNE-ROLE-01's role split (``crew_immune_fraction``). A null
# crew fraction removes the field, returning the engine to the
# role-blind pool; ``immune_fraction`` may not be null because removing
# it would restore the ENGINE default (0.2), not the fit's pinned 0.0.
SHIP_GRAPH_OVERRIDE_KEYS = frozenset({
    "immune_fraction", "crew_immune_fraction",
})
# Fields a dose_response_frailty arm may declare. The arm writes the
# whole beta-Poisson block at the cell's theta so E[susceptibility] is
# preserved on every arm and only the draw's shape moves (the
# covid_vuln_cells convention).
DOSE_RESPONSE_FRAILTY_KEYS = frozenset({"alpha", "beta"})
# Fields a hazard_frailty arm may declare (FRAILTY-V1): the draw family
# and its coefficient of variation. The mean is pinned at 1.0 inside the
# engine so a corner declares dispersion only — never a refit of the
# cell's mean hazard. ``cv`` 0 is the degenerate inert corner (multiplier
# identically 1.0) kept for binding audits.
HAZARD_FRAILTY_ARM_KEYS = frozenset({"distribution", "cv"})
HAZARD_FRAILTY_ARM_DISTRIBUTIONS = ("gamma", "lognormal")
# Fields an arm may write onto the first explicit seed — the measured
# boarding-geometry axes: position in the shedding course at day 0
# (onset_day), departure day, seeded count, infection age, role. A null
# value removes the field, handing that degree of freedom back to the
# engine's draw.
SEED_PATCH_KEYS = frozenset({
    "count", "infection_age_days", "onset_day", "departure_day", "role",
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

def _validate_arms(arms: tuple[Mapping[str, Any], ...]) -> None:
    """The arm-axis validation the design performs at load."""
    arm_ids = [a.get("arm_id") for a in arms]
    for arm_id in arm_ids:
        if not isinstance(arm_id, str) or not arm_id:
            raise ValueError("every arm needs a non-empty string arm_id")
    if len(set(arm_ids)) != len(arm_ids):
        raise ValueError("arm_ids must be distinct")
    if arms:
        baseline_overrides = arms[0].get("overrides") or {}
        if baseline_overrides:
            raise ValueError(
                "the first arm is the declared baseline and must carry "
                "empty overrides",
            )
        for arm in arms:
            unknown = set(arm.get("overrides") or {}) - ARM_OVERRIDE_KEYS
            if unknown:
                raise ValueError(
                    f"arm {arm.get('arm_id')!r} declares unknown override "
                    f"keys {sorted(unknown)}; allowed: "
                    f"{sorted(ARM_OVERRIDE_KEYS)}",
                )


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
    voyage_mode: str = VOYAGE_MODE_DECLARED
    seed_ring_readout: bool = False

    def __post_init__(self) -> None:
        if self.voyage_mode not in VOYAGE_MODES:
            raise ValueError(
                f"voyage_mode must be one of {VOYAGE_MODES}, "
                f"got {self.voyage_mode!r}",
            )
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
        _validate_arms(self.arms)

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
            "voyage_mode": self.voyage_mode,
            "seed_ring_readout": self.seed_ring_readout,
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
        voyage_mode=str(raw.get("voyage_mode", VOYAGE_MODE_DECLARED)),
        seed_ring_readout=bool(raw.get("seed_ring_readout", False)),
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


def _generic_age_stream(seed: int) -> np.random.Generator:
    """The stream a generic voyage's introduction age is drawn on.

    Keyed on the cell seed and a fixed port tag so the same seed draws the
    same introduction at every Theta — the screen's pairing — on a stream
    disjoint from the simulation's own ``default_rng(seed)``, which the
    engine consumes.
    """
    digest = sum(
        (index + 1) * ord(ch)
        for index, ch in enumerate("generic_voyage_age")
    )
    return np.random.default_rng([int(seed), digest])


def _draw_introduction_age(
    incubation_profile: Mapping[str, Any] | None,
    rng: np.random.Generator | None,
) -> float:
    """One generic-voyage introduction's infection age at boarding.

    Drawn from the pathogen's incubation distribution: a typical voyage's
    index is not a dated case report, so its time-since-infection at
    boarding is the range of times an onset takes to appear, at the
    reference dose a declared index sits at and a neutral host.
    """
    model = IncubationModel.from_mapping(
        dict(incubation_profile or {}).get("incubation"),
    )
    if model is None:
        raise ValueError(
            "voyage_mode 'generic' draws the import's infection age from "
            "the pathogen's incubation distribution; the profile declares "
            "none",
        )
    if rng is None:
        raise ValueError(
            "voyage_mode 'generic' needs the per-seed introduction-age stream",
        )
    return float(model.sample_days(
        dose=None, host=HostIncubationState(), rng=rng,
    ))


def _generic_voyage_epochs(scenario_id: str, repo_root: str) -> int:
    """A generic voyage's length on the scenario's own clock."""
    scenario = load_hull_scenarios(repo_root=repo_root)[scenario_id]
    clock = SimClock(
        epoch_duration_hours=float(scenario.epoch_duration_hours),
        mode=scenario.clock_mode,
    )
    return int(round(clock.epochs_for_days(GENERIC_VOYAGE_DAYS)))


def apply_boarding_axis(
    raw: dict[str, Any],
    *,
    infection_age_days: float,
    imports: int,
    sanitary_visit_mode: str,
    voyage_mode: str = VOYAGE_MODE_DECLARED,
    incubation_profile: Mapping[str, Any] | None = None,
    age_stream: np.random.Generator | None = None,
) -> dict[str, Any]:
    """Move the scenario's explicit seed along the axis, in place.

    The hull scenario declares exactly one explicit seed (the index case);
    the screen changes only its ``count`` and ``infection_age_days`` and the
    transmission block's sanitary visit mode. Everything else in the run
    spec is what the fit ran.

    Under ``voyage_mode 'generic'`` the seed's declared ``onset_day`` and
    ``departure_day`` are dropped — a typical voyage's introduction is not a
    dated case report — and its infection age is a draw from the pathogen's
    incubation distribution, so the engine's lazy incubation channel applies
    and the index stays aboard for the whole voyage. The scenario's
    molecular-ascertainment start day is a Diamond Princess historical —
    onboard testing began mid-voyage there — while a generic voyage swabs
    sick-call presenters from embarkation, so the start-day gate is dropped
    and the recorded channel works for the whole voyage.
    """
    overrides = raw.setdefault("config_overrides", {})
    seeds = overrides.get("initiation", {}).get("explicit_seeds", [])
    if len(seeds) != 1:
        raise ValueError(
            f"the boarding screen expects one explicit seed, found {len(seeds)}",
        )
    seeds[0]["count"] = int(imports)
    if voyage_mode == VOYAGE_MODE_GENERIC:
        seeds[0].pop("onset_day", None)
        seeds[0].pop("departure_day", None)
        seeds[0]["infection_age_days"] = _draw_introduction_age(
            incubation_profile, age_stream,
        )
        overrides.get("syndromic", {}).pop(
            "molecular_ascertainment_start_day", None,
        )
    elif voyage_mode == VOYAGE_MODE_DECLARED:
        seeds[0]["infection_age_days"] = float(infection_age_days)
    else:
        raise ValueError(
            f"voyage_mode must be one of {VOYAGE_MODES}, got {voyage_mode!r}",
        )
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


def _retime_scheduled_protocol(
    raw: dict[str, Any],
    window: Mapping[str, Any],
) -> None:
    """Move one scheduled protocol's day window, in place.

    Counterfactual only: the declared replay's schedule is the record's
    calendar, so an arm that retimes it is a sensitivity probe (how much of
    the outbreak was committed before the order could bind), never a
    candidate configuration.
    """
    protocol_id = str(window.get("protocol_id", QUARANTINE_PROTOCOL_ID))
    protocols = (
        raw.get("config_overrides", {})
        .get("scenario_schedule", {})
        .get("protocols", [])
    )
    for entry in protocols:
        if entry.get("protocol_id") != protocol_id:
            continue
        if "start_day" in window:
            entry["start_day"] = int(window["start_day"])
        if "end_day" in window:
            entry["end_day"] = (
                None if window["end_day"] is None else int(window["end_day"])
            )
        return
    raise ValueError(
        f"the run spec's scenario_schedule schedules no {protocol_id} "
        "entry to retime",
    )


def _apply_scheduled_window(raw: dict[str, Any], window: Any) -> None:
    if not isinstance(window, Mapping):
        raise ValueError("scheduled_protocol_window must be a mapping")
    _retime_scheduled_protocol(raw, window)


def _apply_infection_counters(raw: dict[str, Any], counters: Any) -> None:
    if not isinstance(counters, list):
        raise ValueError("infection_counters must be a list of counter defs")
    raw.setdefault("config_overrides", {}).setdefault("ship_graph", {})[
        "infection_counters"
    ] = counters


def _apply_transmission_overrides(raw: dict[str, Any], tx: Any) -> None:
    if not isinstance(tx, Mapping):
        raise ValueError("transmission_overrides must be a mapping")
    raw.setdefault("config_overrides", {}).setdefault(
        "transmission", {},
    ).update(tx)


def _apply_pathogen_overrides(raw: dict[str, Any], patches: Any) -> None:
    """Deep-merge the arm's per-pathogen patches into pathogen_overrides.

    The mapping is {pathogen_id: patch} shaped exactly like the spec-level
    ``pathogen_overrides`` block; the same deep-merge the engine applies at
    profile load is applied here, per pathogen, onto whatever earlier arms'
    patches (e.g. route efficiencies) already wrote.
    """
    if not isinstance(patches, Mapping):
        raise ValueError("pathogen_overrides must be a mapping")
    reserved = {"remove", "add"}
    unknown = set(patches) - reserved
    if unknown - {PATHOGEN_ID}:
        raise ValueError(
            f"pathogen_overrides may only patch {PATHOGEN_ID!r} on this "
            f"screen, got {sorted(unknown - {PATHOGEN_ID})}",
        )
    for pid, patch in patches.items():
        if pid in reserved:
            raise ValueError(
                "pathogen_overrides arm patches may not use the reserved "
                f"{pid!r} form",
            )
        if not isinstance(patch, Mapping):
            raise ValueError(f"pathogen_overrides[{pid!r}] must be a mapping")
        overrides_map = raw.setdefault("pathogen_overrides", {})
        overrides_map[pid] = deep_merge_dict(
            overrides_map.get(pid, {}), dict(patch),
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


def _validate_seed_patch_value(key: str, value: Any) -> None:
    """Per-field validation a seed_patch arm performs at apply time."""
    if key == "role":
        if not isinstance(value, str):
            raise ValueError(
                f"seed_patch.role must be a string, got {value!r}",
            )
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"seed_patch.{key} must be numeric, got {value!r}")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"seed_patch.{key} must be finite, got {value!r}")
    if key == "count" and (number < 1 or number != int(number)):
        raise ValueError(
            f"seed_patch.count must be an integer >= 1, got {value!r}",
        )
    if key == "infection_age_days" and number < 0:
        raise ValueError(
            f"seed_patch.infection_age_days must be >= 0, got {value!r}",
        )


def _apply_seed_patch(raw: dict[str, Any], patch: Any) -> None:
    """Merge ``{key: value}`` onto the first explicit seed.

    Same semantics as ``tools/covid_seed_ring_burn.py``'s ``seed_patch``:
    a null value removes the field. Only SEED_PATCH_KEYS are accepted so an
    arm cannot silently drift into an undeclared counterfactual.
    """
    if not isinstance(patch, Mapping):
        raise ValueError("seed_patch must be a mapping")
    unknown = set(patch) - SEED_PATCH_KEYS
    if unknown:
        raise ValueError(
            f"seed_patch keys {sorted(unknown)} are not seed fields; "
            f"allowed: {sorted(SEED_PATCH_KEYS)}",
        )
    seeds = (
        raw.get("config_overrides", {})
        .get("initiation", {}).get("explicit_seeds")
    )
    if not seeds:
        raise ValueError("seed_patch needs an explicit_seeds entry to edit")
    seed = dict(seeds[0])
    for key, value in patch.items():
        if value is None:
            seed.pop(key, None)
            continue
        _validate_seed_patch_value(key, value)
        seed[key] = int(value) if key == "count" else value
    seeds[0] = seed


def _apply_ship_graph_overrides(raw: dict[str, Any], sg: Any) -> None:
    """Write the arm's embarkation-immunity structure onto ship_graph."""
    if not isinstance(sg, Mapping):
        raise ValueError("ship_graph_overrides must be a mapping")
    unknown = set(sg) - SHIP_GRAPH_OVERRIDE_KEYS
    if unknown:
        raise ValueError(
            f"ship_graph_overrides keys {sorted(unknown)} are not "
            f"immunity fields; allowed: {sorted(SHIP_GRAPH_OVERRIDE_KEYS)}",
        )
    graph = raw.setdefault("config_overrides", {}).setdefault(
        "ship_graph", {},
    )
    for key, value in sg.items():
        if value is None:
            if key == "immune_fraction":
                raise ValueError(
                    "ship_graph_overrides.immune_fraction may not be null: "
                    "removing it restores the engine default 0.2, not the "
                    "fit's pinned 0.0 — declare the fraction explicitly",
                )
            graph.pop(key, None)
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(
                f"ship_graph_overrides.{key} must be a fraction in [0, 1], "
                f"got {value!r}",
            )
        fraction = float(value)
        if not math.isfinite(fraction) or not 0.0 <= fraction <= 1.0:
            raise ValueError(
                f"ship_graph_overrides.{key} must be a fraction in [0, 1], "
                f"got {value!r}",
            )
        graph[key] = fraction


def _apply_dose_response_frailty(
    raw: dict[str, Any],
    spec: Any,
    theta: float,
    profile: dict[str, Any],
) -> None:
    """A beta-Poisson shape arm at preserved E[susceptibility] = theta.

    ``dose_response_frailty`` declares ``{"alpha": a}`` with ``beta``
    optional (default the profile's); it rewrites the resolved
    dose_response block so ``susceptibility_scale`` is recomputed as
    ``theta * (alpha + beta) / alpha`` — the covid_vuln_cells
    convention. Every arm therefore varies only the draw's dispersion
    (alpha < profile is a heavy near-immune tail; alpha > profile is
    near-homogeneous) while the mean challenge stays the cell's Theta.
    """
    if not isinstance(spec, Mapping):
        raise ValueError("dose_response_frailty must be a mapping")
    unknown = set(spec) - DOSE_RESPONSE_FRAILTY_KEYS
    if unknown:
        raise ValueError(
            f"dose_response_frailty keys {sorted(unknown)} are not "
            f"shape fields; allowed: {sorted(DOSE_RESPONSE_FRAILTY_KEYS)}",
        )
    shipped = profile["dose_response"]
    resolved = {"alpha": shipped["alpha"], "beta": shipped["beta"], **spec}
    alpha = resolved["alpha"]
    beta = resolved["beta"]
    for key, value in resolved.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(
                f"dose_response_frailty.{key} must be numeric, got {value!r}",
            )
        if not math.isfinite(float(value)) or float(value) <= 0.0:
            raise ValueError(
                f"dose_response_frailty.{key} must be finite and > 0, "
                f"got {value!r}",
            )
    if not math.isfinite(theta) or theta <= 0.0:
        raise ValueError(
            f"dose_response_frailty needs the cell's positive theta, "
            f"got {theta!r}",
        )
    raw.setdefault("pathogen_overrides", {}).setdefault(
        PATHOGEN_ID, {},
    )["dose_response"] = {
        "model": "beta_poisson",
        "alpha": float(alpha),
        "beta": float(beta),
        "susceptibility_scale": float(theta) * (float(alpha) + float(beta))
        / float(alpha),
    }


def _apply_hazard_frailty(raw: dict[str, Any], spec: Any) -> None:
    """A continuous per-host frailty draw on the infection hazard.

    ``hazard_frailty`` declares ``{"distribution": "gamma"|"lognormal",
    "cv": c}`` and writes ``dose_response.frailty`` onto the resolved
    block. Where ``dose_response_frailty`` reshapes the existing beta
    susceptibility draw, this arm multiplies a second, orthogonal mixing
    variable into the hazard — drawn per challenged host on a dedicated
    stream with mean pinned at 1.0, so E[susceptibility] and the cell's
    theta are untouched and only the burn's dispersion moves (the frail
    burn early; the surviving pool thins). ``cv`` 0 is the inert corner:
    every challenged host carries a recorded 1.0 so the payload echo
    proves the binding without moving the hazard.
    """
    if not isinstance(spec, Mapping):
        raise ValueError("hazard_frailty must be a mapping")
    unknown = set(spec) - HAZARD_FRAILTY_ARM_KEYS
    if unknown:
        raise ValueError(
            f"hazard_frailty keys {sorted(unknown)} are not frailty "
            f"fields; allowed: {sorted(HAZARD_FRAILTY_ARM_KEYS)}",
        )
    missing = HAZARD_FRAILTY_ARM_KEYS - set(spec)
    if missing:
        raise ValueError(
            f"hazard_frailty is missing {sorted(missing)}; both "
            "distribution and cv are declared together",
        )
    distribution = spec["distribution"]
    if distribution not in HAZARD_FRAILTY_ARM_DISTRIBUTIONS:
        raise ValueError(
            f"hazard_frailty.distribution must be one of "
            f"{HAZARD_FRAILTY_ARM_DISTRIBUTIONS}, got {distribution!r}",
        )
    cv = spec["cv"]
    if isinstance(cv, bool) or not isinstance(cv, (int, float)):
        raise ValueError(
            f"hazard_frailty.cv must be numeric, got {cv!r}",
        )
    if not math.isfinite(float(cv)) or float(cv) < 0.0:
        raise ValueError(
            f"hazard_frailty.cv must be finite and >= 0, got {cv!r}",
        )
    raw.setdefault("pathogen_overrides", {}).setdefault(
        PATHOGEN_ID, {},
    ).setdefault("dose_response", {})["frailty"] = {
        "enabled": True,
        "distribution": str(distribution),
        "cv": float(cv),
    }


def apply_arm_overrides(
    raw: dict[str, Any],
    overrides: Mapping[str, Any],
    *,
    profile: dict[str, Any],
    theta: float | None = None,
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
    # The window retime names the DECLARED protocol id; it must run before a
    # rename in the same arm.
    if "scheduled_protocol_window" in overrides:
        _apply_scheduled_window(raw, overrides["scheduled_protocol_window"])
    if "scheduled_protocol_id" in overrides:
        _swap_scheduled_protocol(raw, str(overrides["scheduled_protocol_id"]))
    if "infection_counters" in overrides:
        _apply_infection_counters(raw, overrides["infection_counters"])
    if "transmission_overrides" in overrides:
        _apply_transmission_overrides(raw, overrides["transmission_overrides"])
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
    if "pathogen_overrides" in overrides:
        _apply_pathogen_overrides(raw, overrides["pathogen_overrides"])
    if "ship_graph_overrides" in overrides:
        _apply_ship_graph_overrides(raw, overrides["ship_graph_overrides"])
    if "dose_response_frailty" in overrides:
        if theta is None:
            raise ValueError(
                "dose_response_frailty needs the cell's theta to hold "
                "E[susceptibility] constant",
            )
        _apply_dose_response_frailty(
            raw, overrides["dose_response_frailty"], float(theta), profile,
        )
    if "hazard_frailty" in overrides:
        # Runs after the block-rewriting arms above so the frailty
        # sub-key lands on whatever dose_response block they resolved.
        _apply_hazard_frailty(raw, overrides["hazard_frailty"])
    if "seed_patch" in overrides:
        _apply_seed_patch(raw, overrides["seed_patch"])
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
    *,
    infection_age_days: float | None = None,
) -> dict[str, Any]:
    """The seeded index host's own geometry, read off its infection record.

    The stamped ``onset_time_infected`` records when progression *noticed*
    the onset, so a host that boarded past incubation is not back-dated;
    the true onset is the drawn ``incubation_days`` against the boarding
    age, which is the record this screen means. ``infection_age_days`` is
    the age the host was actually seeded with — the cell axis under the
    declared mode, the drawn introduction age under a generic voyage.
    """
    age = (
        float(cell.infection_age_days) if infection_age_days is None
        else float(infection_age_days)
    )
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
            - age
        )
    shedding_day0 = False
    if incubation is not None:
        presymptomatic = float(profile.get("presymptomatic_shedding_days", 0.0))
        # The same gate _shedding_curve_point applies, evaluated at the
        # boarding age: in-window means the host emits at epoch 0.
        shedding_day0 = age - float(incubation) >= -presymptomatic
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
    """The scheduled quarantine entry and its inclusive day window.

    The screened scenarios carry a single scheduled-protocol slot, so the
    entry is found by the SOP-017 prefix first (SOP-017 or an arm's
    renamed copy of it) and otherwise by the run's only scheduled entry —
    an arm that swapped the slot to another protocol (SOP-009/011/007)
    still occupies the window these tallies are computed against.
    """
    protocols = (
        raw.get("config_overrides", {})
        .get("scenario_schedule", {})
        .get("protocols", [])
    )
    entry = next(
        (
            e for e in protocols
            if e.get("protocol_id", "").startswith(QUARANTINE_PROTOCOL_ID)
        ),
        protocols[0] if len(protocols) == 1 else None,
    )
    if entry is None:
        raise ValueError(
            "the run spec schedules no quarantine entry for the payload window",
        )
    end = entry.get("end_day")
    return (
        entry,
        int(entry["start_day"]),
        None if end is None else int(end),
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


def _tally_during_events(
    sim: Any,
    ledger_events: list[dict[str, Any]],
    agents_by_id: dict[int, Any],
    dining_types: Mapping[str, str],
    start: int,
    end: int | None,
) -> tuple[dict[str, int], dict[str, int], dict[str, int], int]:
    """Split the during-window ledger events by role, zone class and route."""
    by_role = {"passenger": 0, "crew": 0}
    by_zone = dict.fromkeys(ZONE_CLASSES, 0)
    by_route = {**dict.fromkeys(PATHWAY_EFFICIENCY_KEYS, 0), "unknown": 0}
    confined_passengers = 0
    for ev in ledger_events:
        day = sim.clock.day_index(int(ev["epoch"]))
        if day < start or (end is not None and day > end):
            continue
        agent = agents_by_id.get(ev["target_agent_id"])
        role = getattr(agent, "role", None)
        if role in by_role:
            by_role[role] += 1
        by_zone[_during_zone_class(sim, dining_types, agents_by_id, ev)] += 1
        by_route[ev["pathway"] if ev["pathway"] in by_route else "unknown"] += 1
        if role == "passenger" and ev["confined"]:
            confined_passengers += 1
    return by_role, by_zone, by_route, confined_passengers


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

    by_role, by_zone, by_route, confined_passengers = _tally_during_events(
        sim, ledger.events, agents_by_id, dining_types, start, end,
    )

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
        # Window tallies are unconditional: an arm whose scheduled slot
        # carries no whole-body confinement (symptomatic-only, venue
        # closure, never-binds) still needs its during-window mass and
        # zone/route mix for the suppression-shape discriminators.
        "infections_during_window": window_counts["during"],
        "during_window_by_role": by_role,
        "during_window_by_zone_class": by_zone,
        "during_window_by_route": by_route,
        "confined_passenger_infections_during_window": confined_passengers,
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


def _immune_block(raw: dict[str, Any], sim: Any) -> dict[str, Any]:
    """Declared + resolved + realized embarkation-immunity echo.

    The declared block is what the arm wrote onto
    ``config_overrides.ship_graph``; the resolved pair is what the
    engine built its pools from; the realized counts prove the draw
    delivered the declared share (the pool deals without replacement,
    so realized == declared share exactly).
    """
    graph = raw.get("config_overrides", {}).get("ship_graph", {})
    engine = sim.engine
    realized = Counter(
        str(getattr(a, "role", "unknown"))
        for a in engine.agents if getattr(a, "immune", False)
    )
    complement = Counter(str(getattr(a, "role", "unknown")) for a in engine.agents)
    return {
        "declared": {
            "immune_fraction": graph.get("immune_fraction"),
            "crew_immune_fraction": graph.get("crew_immune_fraction"),
        },
        "resolved": {
            "immune_ratio": getattr(engine, "immune_ratio", None),
            "crew_immune_ratio": getattr(engine, "crew_immune_ratio", None),
        },
        "realized": {
            "by_role": dict(realized),
            "complement_by_role": dict(complement),
        },
    }


def _acquisition_curve(
    sim: Any,
    ledger: QuarantineAttributionLedger,
) -> dict[str, Any]:
    """Truth-level daily incidence — the day-16 kink readout.

    Per-day counts of non-seeded acquisitions across the whole voyage,
    split by whether the target was confined at the event's epoch, so a
    suppression-shaped arm (incidence kinks at day 16 and concentrates
    in cabins/crew) separates from a structure-shaped arm (smooth
    attenuation of the same curve).
    """
    by_day: Counter[int] = Counter()
    confined_by_day: Counter[int] = Counter()
    for ev in ledger.events:
        day = sim.clock.day_index(int(ev["epoch"]))
        by_day[day] += 1
        if ev["confined"]:
            confined_by_day[day] += 1
    return {
        "total_by_day": {str(d): c for d, c in sorted(by_day.items())},
        "confined_by_day": {str(d): c for d, c in sorted(confined_by_day.items())},
    }


def _host_draw_stats(sim: Any, attribute: str) -> dict[str, Any]:
    """Quantiles of one lazy per-host draw over the challenged set.

    Both the beta susceptibility draw and the frailty multiplier are
    lazy: only hosts the engine actually challenged carry a value, so
    the quantiles describe the challenged set — the drawn-vs-declared
    check a dispersion arm needs, and on other arms a no-op echo.
    """
    draws = [
        float(getattr(a, attribute)[PATHOGEN_ID])
        for a in sim.engine.agents
        if PATHOGEN_ID in getattr(a, attribute, {})
    ]
    if not draws:
        return {"n": 0}
    return {
        "n": len(draws),
        "mean": float(np.mean(draws)),
        "q05": _quantile(draws, 0.05),
        "q25": _quantile(draws, 0.25),
        "q50": _quantile(draws, 0.5),
        "q75": _quantile(draws, 0.75),
        "q95": _quantile(draws, 0.95),
    }


def _susceptibility_draw_stats(sim: Any) -> dict[str, Any]:
    """Quantiles of the drawn per-host susceptibilities (landing proof)."""
    return _host_draw_stats(sim, "dose_response_susceptibility")


def _frailty_draw_stats(sim: Any) -> dict[str, Any]:
    """Quantiles of the drawn per-host frailty multipliers (landing proof).

    ``{"n": 0}`` on every arm that leaves the frailty surface unarmed —
    the off-arm stays bit-identical and this echo is what proves it.
    """
    return _host_draw_stats(sim, "frailty_multiplier")


def prepare_cell_run_spec(
    design: BoardingScreenDesign,
    cell: ScreenCell,
    *,
    num_epochs: int | None = None,
    repo_root: str = REPO_ROOT,
) -> dict[str, Any]:
    """Build the run spec one cell executes, arm overrides included.

    A generic-voyage design runs the fixed cruise length on the scenario's
    clock unless ``num_epochs`` is given (a smoke); a declared design keeps
    the scenario's full recorded event.
    """
    arm_overrides = (
        design.arm_overrides(cell.arm_id)
        if design.arms and cell.arm_id is not None else {}
    )
    if num_epochs is None and design.voyage_mode == VOYAGE_MODE_GENERIC:
        num_epochs = _generic_voyage_epochs(cell.scenario_id, repo_root)
    raw = build_fit_run_spec(
        cell.scenario_id, cell.theta, cell.seed,
        num_epochs=num_epochs, repo_root=repo_root,
        pathogen_pool_transport=arm_overrides.get("pathogen_pool_transport"),
    )
    profile = load_covid_profile(repo_root)
    apply_boarding_axis(
        raw,
        infection_age_days=cell.infection_age_days,
        imports=cell.imports,
        sanitary_visit_mode=design.sanitary_visit_mode,
        voyage_mode=design.voyage_mode,
        incubation_profile=profile,
        age_stream=(
            _generic_age_stream(cell.seed)
            if design.voyage_mode == VOYAGE_MODE_GENERIC else None
        ),
    )
    apply_arm_overrides(
        raw, arm_overrides, profile=profile, theta=cell.theta,
    )
    return raw


def _index_infection_age(raw: dict[str, Any], cell: ScreenCell) -> float:
    """The age the index host was seeded with, read back off the run spec.

    Identical to the cell axis under the declared mode; under a generic
    voyage it is the drawn introduction age stamped on the explicit seed —
    the index-geometry fields need the value the host boarded with, not the
    placeholder the cell key carries.
    """
    seeds = (
        raw.get("config_overrides", {})
        .get("initiation", {}).get("explicit_seeds", [])
    )
    if len(seeds) == 1 and seeds[0].get("infection_age_days") is not None:
        return float(seeds[0]["infection_age_days"])
    return float(cell.infection_age_days)


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
            infection_age_days=_index_infection_age(raw, cell),
        ),
        **_truth_counts(sim.engine),
        "lab_confirmed_total": syndromic.lab_confirmed_count(PATHOGEN_ID),
        # The resolved onset-recording channel, echoed back so a cell's
        # channel arm is auditable from the payload alone: the declared arm
        # carries null, a period arm carries its declared block.
        "onset_recording": syndromic.onset_recording_channel(PATHOGEN_ID),
        # The resolved syndrome-eligibility ladder and the dated mass's
        # severity split, echoed so a severity-scoped observation arm
        # (a mild-stratum corner) is auditable the same way.
        "onset_eligibility_by_severity": (
            sim.pathogen_profiles[PATHOGEN_ID].get("observation_model") or {}
        ).get("syndrome_case_eligibility_by_severity"),
        "recorded_onsets_by_severity": (
            syndromic.onset_observation_severity_counts(PATHOGEN_ID)
        ),
        KEY_VSP_MAX: float(
            getattr(sim.engine, "vsp_reported_case_fraction_max", 0.0),
        ),
    }
    if design.seed_ring_readout:
        payload["seed_ring"] = _seed_ring_block(sim, ledger, raw)
    if design.arms:
        payload.update({
            "arm_id": cell.arm_id,
            # The resolved dose_response after arm overrides, echoed so a
            # cell's declared law (model, n_star, carrier_loading, and the
            # swept susceptibility_scale composite) is auditable from the
            # payload alone.
            "dose_response": dict(
                sim.pathogen_profiles[PATHOGEN_ID].get("dose_response") or {}
            ),
            # The resolved exposure-cap ring-inclusion flag, echoed so a
            # fixed-ring-inclusion arm is auditable from the payload
            # alone (null on arms that do not declare the block).
            "exposure_cap_include_fixed_rings": (
                raw.get("config_overrides", {})
                .get("transmission", {})
                .get("exposure_cap", {})
                .get("include_fixed_rings")
            ),
            # The engine-resolved cap state, echoed so a cap arm's
            # declared switch is auditable against what actually ran
            # (the hull gates the feature on the platform).
            "exposure_cap_active": bool(
                getattr(sim.tx_core, "_exposure_cap_active", False)
            ),
            "ship_graph_immune": _immune_block(raw, sim),
            "acquisition_curve": _acquisition_curve(sim, ledger),
            "susceptibility_draw": _susceptibility_draw_stats(sim),
            # The realized frailty-multiplier draws, echoed so a
            # hazard_frailty arm's declared corner (distribution, cv)
            # is auditable against what actually landed on challenged
            # hosts — {"n": 0} on every unarmed arm.
            "frailty_draw": _frailty_draw_stats(sim),
            **_attribution_block(sim, ledger, raw),
            # The resolved pooled-route delivery constants, echoed so a
            # delivery-machinery arm's declared values are auditable from
            # the payload alone (HEAT-V1 lineage).
            "delivery": _delivery_block(sim, raw),
        })
    return payload


def _delivery_block(sim: Any, raw: Mapping[str, Any]) -> dict[str, Any]:
    """Resolved delivery-machinery constants for the audit echo.

    Reads the post-override profile fields the cell actually ran with
    (half-life, merged route-efficiency map), the build-time pool transport
    mode, the declared exposure_cap sub-block plus the engine-resolved
    active flag, and the resolved activity_contacts table (null when the
    arm leaves the POLYMOD draw shipped).
    """
    profile = sim.pathogen_profiles.get(PATHOGEN_ID) or {}
    tx_over = raw.get("config_overrides", {}).get("transmission", {})
    tx_core = getattr(sim, "tx_core", None)
    resolved_contacts = (
        getattr(tx_core, "activity_contacts", None) if tx_core is not None else None
    )
    return {
        "airborne_half_life_hours": profile.get("airborne_half_life_hours"),
        "route_efficiency_multipliers": dict(
            profile.get("route_efficiency_multipliers") or {}
        ),
        "pathogen_pool_transport": getattr(sim, "pathogen_pool_transport", None),
        "exposure_cap": dict(tx_over.get("exposure_cap") or {}),
        "exposure_cap_active": bool(
            getattr(tx_core, "_exposure_cap_active", False)
        ),
        # The engine-resolved hand-reservoir arm, echoed so a
        # transmission_overrides hand_reservoir_mode arm is auditable from
        # the payload alone (COVID-HAND-AB-01: None only on payloads
        # written before the reservoir machinery shipped).
        "hand_reservoir_mode": getattr(tx_core, "hand_reservoir_mode", None),
        "activity_contacts": resolved_contacts,
    }


def _first_secondary_shed_epoch(
    sim: Any, seeded: set[int], presymptomatic_epochs: int,
) -> int | None:
    """Earliest epoch any non-seeded host could emit — the bound on clean
    seed attribution inside the aboard window."""
    candidates = []
    for agent in sim.engine.agents:
        if agent.agent_id in seeded:
            continue
        inf = agent.infections.get(PATHOGEN_ID)
        if inf is None:
            continue
        epoch = earliest_shed_epoch(
            inf, int(inf.get("infection_epoch") or 0),
            presymptomatic_epochs, sim.clock,
        )
        if epoch is not None:
            candidates.append(epoch)
    return min(candidates) if candidates else None


def _seeded_host_rows(sim: Any, seeded: set[int]) -> list[dict[str, Any]]:
    """Realized placement of each seeded host — the placement-arm audit.

    ``seed_spec.role`` echoes the declared filter; the draw inside the
    role pool is stochastic, so the payload records which host class and
    ring memberships each seeded agent actually landed on.
    """
    return [
        {
            "agent_id": int(a.agent_id),
            "role": a.role,
            "agent_class": a.agent_class,
            "home_zone": a.home_zone,
            "dining_zone": a.dining_zone,
            "work_zone": a.work_zone,
            "cabin_ring_size": len(getattr(a, "cabin_mate_ids", None) or ()),
            "table_ring_size": len(getattr(a, "dining_party_ids", None) or ()),
        }
        for a in sim.engine.agents
        if a.agent_id in seeded
    ]


def _seed_ring_block(
    sim: Any, ledger: QuarantineAttributionLedger, raw: dict[str, Any],
) -> dict[str, Any]:
    """Secondary yield of the boarding seed(s) — the day-0 ring burn.

    Every non-seeded acquisition while at least one seeded host was still
    aboard, split by route and day, with the clean attribution bound
    (events before any secondary host could first emit) so ring-driven
    burn is separated from onboard amplification. ``seed_spec`` echoes the
    applied seed record so the arm's patched geometry is auditable from
    the payload alone; ``seeded_hosts`` echoes each seeded agent's
    realized role and ring memberships so placement arms are auditable.
    """
    seeds = (
        raw.get("config_overrides", {})
        .get("initiation", {}).get("explicit_seeds", [])
    )
    seed0 = dict(seeds[0]) if seeds else {}
    seeded = set(getattr(sim.engine, "explicit_seed_agent_ids", None) or ())
    departures = [
        int(a.departure_epoch) for a in sim.engine.agents
        if a.agent_id in seeded and a.departure_epoch is not None
    ]
    window_end = max(departures) if departures else None
    profile = sim.pathogen_profiles[PATHOGEN_ID]
    presymptomatic_epochs = int(round(
        sim.clock.epochs_for_days(
            float(profile.get("presymptomatic_shedding_days", 0.0)),
        ),
    ))
    first_shed = _first_secondary_shed_epoch(
        sim, seeded, presymptomatic_epochs,
    )
    aboard = [
        e for e in ledger.events
        if window_end is None or int(e["epoch"]) < window_end
    ]
    clean = [
        e for e in aboard
        if first_shed is None or int(e["epoch"]) < first_shed
    ]
    by_day = Counter(sim.clock.day_index(int(e["epoch"])) for e in aboard)
    return {
        "seeded_count": len(seeded),
        "seed_spec": {
            key: seed0[key] for key in SEED_PATCH_KEYS if key in seed0
        },
        "seeded_hosts": _seeded_host_rows(sim, seeded),
        "index_departure_epoch": window_end,
        "aboard_window_acquisitions": len(aboard),
        "aboard_window_clean_bound": len(clean),
        "first_secondary_shed_epoch": first_shed,
        "aboard_window_by_route": dict(
            Counter(e["pathway"] for e in aboard),
        ),
        "aboard_window_by_day": {
            str(day): count for day, count in sorted(by_day.items())
        },
        "yield_per_seeded_host": (
            len(aboard) / len(seeded) if seeded else None
        ),
    }


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


def echo_screen_cell(
    design: BoardingScreenDesign,
    cell: ScreenCell,
    *,
    repo_root: str = REPO_ROOT,
) -> dict[str, Any]:
    """Read one cell's payload at initialize(), without stepping a voyage.

    The resolved-config echoes a payload carries — dose_response, delivery,
    ship_graph_immune, the exposure-cap flags, the seed-ring spec and
    seeded-host placement rows — are fixed when the spec applies at
    initialize(), so asserting on them needs no voyage epochs. Epoch-accrual
    fields (the aboard-window attribution counts, acquisition_curve buckets,
    susceptibility draws) read their empty state; assertions on those still
    run a voyage.
    """
    raw = prepare_cell_run_spec(design, cell, repo_root=repo_root)
    ledger = QuarantineAttributionLedger()
    sim = build_fit_sim(
        raw, repo_root=repo_root, epoch_observer=ledger.observe,
    )
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
    if geometry_pass:
        pass_fraction = float(np.mean(geometry_pass))
    elif has_geometry:
        pass_fraction = 0.0
    else:
        pass_fraction = None
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


def _fleet_shape(
    by_seed: dict[int, dict[str, Any]],
    obs: dict[int, HullObservables],
) -> dict[str, Any]:
    """The across-voyage recorded attack-rate shape, scored against covid.H3.

    The numerator is the RECORDED channel — ``recorded_onsets`` over the
    aboard total — verbatim from the v10 stage-2 block, not the truth
    channel ``attack_rate`` pools. ``fleet_shape_ok`` is the v11 stage-1
    selector verbatim: the median in [0.0005, 0.008], the IQR overlapping
    [0.0003, 0.015], the mean not above 0.06. Emitted on every design as a
    diagnostic; only a generic-voyage screen selects on it.
    """
    rates = [
        o.recorded_onsets / float(by_seed[seed][KEY_ABOARD_TOTAL])
        for seed, o in obs.items()
        if by_seed[seed].get(KEY_ABOARD_TOTAL)
    ]
    if not rates:
        return {
            "recorded_attack_rate": None,
            "recorded_attack_rate_quantiles": _attack_quantiles(()),
            "p_recorded_ge_0p015": None,
            "p_recorded_ge_0p10": None,
            "p_recorded_le_0p01": None,
            "fleet_shape_ok": None,
        }
    median = _quantile(rates, 0.5)
    q25 = _quantile(rates, 0.25)
    q75 = _quantile(rates, 0.75)
    mean = float(np.mean(rates))
    iqr_overlaps = not (
        q75 < FLEET_IQR_WINDOW[0] or q25 > FLEET_IQR_WINDOW[1]
    )
    return {
        "recorded_attack_rate": {
            "median": median,
            "mean": mean,
            "q25": q25,
            "q75": q75,
        },
        "recorded_attack_rate_quantiles": _attack_quantiles(rates),
        "p_recorded_ge_0p015": float(np.mean([r >= 0.015 for r in rates])),
        "p_recorded_ge_0p10": float(np.mean([r >= 0.10 for r in rates])),
        "p_recorded_le_0p01": float(np.mean([r <= 0.01 for r in rates])),
        "fleet_shape_ok": bool(
            FLEET_MEDIAN_WINDOW[0] <= median <= FLEET_MEDIAN_WINDOW[1]
            and iqr_overlaps
            and mean <= FLEET_MEAN_MAX
        ),
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
        **_fleet_shape(by_seed, obs),
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
    taken_off_seeds = [
        seed for seed, o in obs.items()
        if o.recorded_onsets >= design.takeoff_recorded_onsets
    ]
    taken_off = [obs[seed] for seed in taken_off_seeds]
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
        **_seed_ring_summary(by_seed, taken_off_seeds),
        **(_admissibility(
            by_seed, obs, targets or load_fit_targets(),
        )),
    }


def _seed_ring_summary(
    by_seed: dict[int, dict[str, Any]],
    taken_off_seeds: list[int],
) -> dict[str, Any]:
    """Row-level aggregate of the per-seed ring block, when present.

    The takeoff-conditioned yield is the readout INDEX-GEOM-01 asked for:
    secondary yield per seeded host among the seeds that took off.
    """
    rings = {
        seed: p["seed_ring"] for seed, p in by_seed.items()
        if isinstance(p.get("seed_ring"), Mapping)
    }
    if not rings:
        return {}
    aboard = [float(r["aboard_window_acquisitions"]) for r in rings.values()]
    clean = [
        float(r["aboard_window_clean_bound"]) for r in rings.values()
        if r.get("aboard_window_clean_bound") is not None
    ]
    yields = [
        float(r["yield_per_seeded_host"]) for r in rings.values()
        if r.get("yield_per_seeded_host") is not None
    ]
    takeoff_yields = [
        float(rings[s]["yield_per_seeded_host"]) for s in taken_off_seeds
        if s in rings and rings[s].get("yield_per_seeded_host") is not None
    ]
    pooled_routes: Counter[str] = Counter()
    for ring in rings.values():
        pooled_routes.update(
            {
                str(route): int(count)
                for route, count in (
                    ring.get("aboard_window_by_route") or {}
                ).items()
            },
        )
    return {
        "seed_ring": {
            "n": len(rings),
            "aboard_window_acquisitions": _summary(aboard),
            "aboard_window_clean_bound": _summary(clean),
            "yield_per_seeded_host": _summary(yields),
            "yield_per_seeded_host_on_takeoff": _summary(takeoff_yields),
            "aboard_window_by_route_pooled": dict(pooled_routes),
        },
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
