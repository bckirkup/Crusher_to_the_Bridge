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
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import product
from typing import Any

import numpy as np

from picard_framework.covid_hull_scenarios import REPO_ROOT, load_hull_scenarios
from picard_framework.covid_theta_fit import (
    PATHOGEN_ID,
    HullObservables,
    build_fit_run_spec,
    observables_from_modality,
    run_fit_spec,
)
from simulation_utils.paths import validated_open

DESIGN_REL = os.path.join(
    "picard_framework", "runs", "covid_boarding_screen_v1_design.json",
)
SANITARY_VISIT_MODES = ("none", "dwell_weighted")
INTERVAL = (0.05, 0.95)
SPLIT_DAY = 17
TURN_DAY = 16


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
    )
    load_hull_scenarios().assert_fit_target(design.scenario_id)
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

    @property
    def axis(self) -> tuple[float, int]:
        return (self.infection_age_days, self.imports)

    @property
    def key(self) -> str:
        exponent = f"{math.log10(self.theta):.2f}".replace(".", "p")
        age = f"{self.infection_age_days:g}".replace(".", "p")
        return (
            f"screen_{self.scenario_id}_theta1e{exponent}_age{age}d"
            f"_imports{self.imports}_seed{self.seed}.json"
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "scenario_id": self.scenario_id,
            "theta": self.theta,
            "infection_age_days": self.infection_age_days,
            "imports": self.imports,
            "seed": self.seed,
            "key": self.key,
        }


def enumerate_cells(design: BoardingScreenDesign) -> tuple[ScreenCell, ...]:
    """Every cell in a fixed order: Theta, then age, then imports, then seed."""
    cells: list[ScreenCell] = []
    for theta, age, imports, seed in product(
        design.thetas, design.infection_age_days, design.imports,
        design.seed_values,
    ):
        cells.append(ScreenCell(
            index=len(cells),
            scenario_id=design.scenario_id,
            theta=float(theta),
            infection_age_days=float(age),
            imports=int(imports),
            seed=int(seed),
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


def _first_onset_day(curve: dict[int, dict[str, int]]) -> int | None:
    days = [
        int(day) for day, roles in curve.items()
        if int(roles.get("passenger", 0)) + int(roles.get("crew", 0)) > 0
    ]
    return min(days) if days else None


def simulate_screen_cell(
    design: BoardingScreenDesign,
    cell: ScreenCell,
    *,
    num_epochs: int | None = None,
    repo_root: str = REPO_ROOT,
) -> dict[str, Any]:
    """Run one cell and return its observables, onset curve and witness."""
    raw = build_fit_run_spec(
        cell.scenario_id, cell.theta, cell.seed,
        num_epochs=num_epochs, repo_root=repo_root,
    )
    apply_boarding_axis(
        raw,
        infection_age_days=cell.infection_age_days,
        imports=cell.imports,
        sanitary_visit_mode=design.sanitary_visit_mode,
    )
    sim = run_fit_spec(raw, repo_root=repo_root)
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
    return {
        "observables": obs.as_dict(),
        "onset_curve": {
            str(day): dict(roles) for day, roles in sorted(curve.items())
        },
        "first_onset_day": _first_onset_day(curve),
        "sanitary_activity": {
            k: float(v) for k, v in dict(sim.tx_core.sanitary_telemetry).items()
        },
    }


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
) -> dict[tuple[float, float, int], dict[int, dict[str, Any]]]:
    grouped: dict[tuple[float, float, int], dict[int, dict[str, Any]]] = {}
    for cell in cells:
        payload = payloads.get(cell.key)
        if payload is None:
            continue
        grouped.setdefault(
            (cell.theta, cell.infection_age_days, cell.imports), {},
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


def _cell_summary(
    design: BoardingScreenDesign,
    by_seed: dict[int, dict[str, Any]],
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
        "sanitary_witness": _witness(by_seed.values(), design.sanitary_visit_mode),
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
    surface = []
    for theta in design.thetas:
        base = grouped.get((theta, *design.baseline), {})
        for age, imports in product(design.infection_age_days, design.imports):
            by_seed = grouped.get((theta, age, imports), {})
            if not by_seed:
                continue
            entry = {
                "theta": theta,
                "infection_age_days": age,
                "imports": imports,
                "is_baseline": (age, imports) == design.baseline,
                **_cell_summary(design, by_seed),
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
