"""The replicated COVID first look: one declared design, many seeds, one merge.

The single-seed fit in :mod:`picard_framework.covid_theta_fit` evaluates a
grid once. One index case on a 3,711-host hull either takes off or dies out,
so one seed per candidate gives a loss curve that is mostly that coin. This
module declares the same fit as a matrix of cells (hull x Theta x seed),
enumerates them deterministically so an AWS Batch array child can pick one by
index, and pools the finished cells into a replicated fit and a replicated
held-out report.

Discipline carried over from the single-seed fit and enforced here too:

- The fit reads training-hull cells only. Held-out cells are enumerated in the
  same array for economy, but the merge fixes Theta before it looks at them
  and scores them at that Theta.
- Theta stays a composite; nothing here attributes it to emission or beta.
- Seeds are matched across candidates so the comparison is paired.
- A cell is not a verdict; the merge refuses an incomplete training grid
  unless the caller declares that the result is partial.
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

from engines.transmission_core import CABIN_AIR_MODES, DEFAULT_CABIN_AIR_MODE
from picard_framework.covid_fit_targets import FitTargets, load_fit_targets
from picard_framework.covid_hull_scenarios import REPO_ROOT, load_hull_scenarios
from picard_framework.covid_theta_fit import (
    FIT_CONTRACT,
    HullObservables,
    HullRunner,
    ThetaObjective,
    _greg_mortimer_scores,
    candidate_grid,
    implied_per_copy_risk,
    simulate_hull,
)
from simulation_utils.paths import validated_open

DESIGN_REL = os.path.join(
    "picard_framework", "runs", "covid_first_look_v1_design.json",
)
FIT_PHASE = "fit"
HELD_OUT_PHASE = "held_out"
PHASES = (FIT_PHASE, HELD_OUT_PHASE)
INTERVAL = (0.05, 0.95)


# ── design ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PhaseDesign:
    """One hull's slice of the design: which scenario, how many seeds."""

    phase: str
    scenario_id: str
    split_role: str
    seed_base: int
    seeds: int

    def __post_init__(self) -> None:
        if self.phase not in PHASES:
            raise ValueError(f"unknown phase {self.phase!r}; known: {PHASES}")
        if self.seeds < 1:
            raise ValueError(f"{self.phase}: a phase needs at least one seed")

    @property
    def seed_values(self) -> tuple[int, ...]:
        return tuple(self.seed_base + i for i in range(self.seeds))


@dataclass(frozen=True)
class FirstLookDesign:
    """The whole design, as declared before any cell ran."""

    design_id: str
    grid: tuple[float, ...]
    fit: PhaseDesign
    held_out: PhaseDesign
    takeoff_recorded_onsets: int
    bootstrap_resamples: int
    bootstrap_seed: int
    cabin_air_mode: str = DEFAULT_CABIN_AIR_MODE

    def __post_init__(self) -> None:
        if self.cabin_air_mode not in CABIN_AIR_MODES:
            raise ValueError(
                "cabin_air_mode must be one of "
                f"{CABIN_AIR_MODES}, got {self.cabin_air_mode!r}",
            )

    def phase(self, name: str) -> PhaseDesign:
        if name == FIT_PHASE:
            return self.fit
        if name == HELD_OUT_PHASE:
            return self.held_out
        raise KeyError(name)

    def as_dict(self) -> dict[str, Any]:
        return {
            "design_id": self.design_id,
            "grid": list(self.grid),
            "fit": self.fit.__dict__,
            "held_out": self.held_out.__dict__,
            "takeoff_recorded_onsets": self.takeoff_recorded_onsets,
            "bootstrap_resamples": self.bootstrap_resamples,
            "bootstrap_seed": self.bootstrap_seed,
            "cabin_air_mode": self.cabin_air_mode,
        }


def design_path(repo_root: str = REPO_ROOT) -> str:
    return os.path.join(repo_root, DESIGN_REL)


def _phase_from_raw(name: str, raw: dict[str, Any]) -> PhaseDesign:
    return PhaseDesign(
        phase=name,
        scenario_id=str(raw["scenario_id"]),
        split_role=str(raw["split_role"]),
        seed_base=int(raw["seed_base"]),
        seeds=int(raw["seeds"]),
    )


def _assert_roles(design: FirstLookDesign) -> None:
    """The design's roles must be the fixed split's, not the other way round."""
    scenarios = load_hull_scenarios()
    scenarios.assert_fit_target(design.fit.scenario_id)
    held_out = scenarios[design.held_out.scenario_id]
    if held_out.is_training:
        raise ValueError(
            f"{design.held_out.scenario_id} is a training hull and cannot be "
            "the held-out phase",
        )
    for phase in (design.fit, design.held_out):
        declared = scenarios[phase.scenario_id].split_role
        if phase.split_role != declared:
            raise ValueError(
                f"{phase.phase}: design says {phase.split_role!r} but the "
                f"fixed split says {phase.scenario_id} is {declared!r}",
            )


def load_design(
    path: str | None = None,
    *,
    repo_root: str = REPO_ROOT,
) -> FirstLookDesign:
    resolved = path or design_path(repo_root)
    with validated_open(
        resolved, allowed_roots=(repo_root,), encoding="utf-8",
    ) as handle:
        raw = json.load(handle)
    grid_raw = raw["grid"]
    design = FirstLookDesign(
        design_id=str(raw["design_id"]),
        grid=candidate_grid(
            float(grid_raw["low"]), float(grid_raw["high"]), int(grid_raw["count"]),
        ),
        fit=_phase_from_raw(FIT_PHASE, raw["phases"][FIT_PHASE]),
        held_out=_phase_from_raw(HELD_OUT_PHASE, raw["phases"][HELD_OUT_PHASE]),
        takeoff_recorded_onsets=int(raw["takeoff_recorded_onsets"]),
        bootstrap_resamples=int(raw["bootstrap_resamples"]),
        bootstrap_seed=int(raw["bootstrap_seed"]),
        cabin_air_mode=str(raw.get("cabin_air_mode", DEFAULT_CABIN_AIR_MODE)),
    )
    _assert_roles(design)
    return design


# ── cells ─────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Cell:
    """One (phase, hull, Theta, seed) the array evaluates."""

    index: int
    phase: str
    scenario_id: str
    theta: float
    seed: int

    @property
    def key(self) -> str:
        exponent = f"{math.log10(self.theta):.2f}".replace(".", "p")
        return f"{self.phase}_{self.scenario_id}_theta1e{exponent}_seed{self.seed}.json"

    def as_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "phase": self.phase,
            "scenario_id": self.scenario_id,
            "theta": self.theta,
            "seed": self.seed,
            "key": self.key,
        }


def enumerate_cells(design: FirstLookDesign) -> tuple[Cell, ...]:
    """Every cell, in a fixed order: fit first, then held-out; Theta-major."""
    cells: list[Cell] = []
    for phase in (design.fit, design.held_out):
        for theta, seed in product(design.grid, phase.seed_values):
            cells.append(Cell(
                index=len(cells),
                phase=phase.phase,
                scenario_id=phase.scenario_id,
                theta=float(theta),
                seed=int(seed),
            ))
    return tuple(cells)


def run_cell(
    design: FirstLookDesign,
    cell: Cell,
    *,
    runner: HullRunner = simulate_hull,
) -> dict[str, Any]:
    """Run one cell and return the payload the array child uploads.

    The payload carries observables only. Loss terms are computed at merge
    time from the training anchors, so a worker never needs the targets and
    a held-out cell never has a loss attached to it.
    """
    obs = runner(
        cell.scenario_id, cell.theta, cell.seed,
        cabin_air_mode=design.cabin_air_mode,
    )
    return {
        "design_id": design.design_id,
        "cabin_air_mode": design.cabin_air_mode,
        "cell": cell.as_dict(),
        "observables": obs.as_dict(),
    }


def observables_from_payload(payload: dict[str, Any]) -> HullObservables:
    raw = dict(payload["observables"])
    raw.pop("positive_share", None)
    raw.pop("asymptomatic_share", None)
    return HullObservables(**raw)


# ── merge: the replicated fit ─────────────────────────────────────────────

def _quantile(values: Sequence[float], q: float) -> float:
    return float(np.quantile(np.asarray(values, dtype=float), q))


def _summary(values: Sequence[float]) -> dict[str, float | int]:
    return {
        "n": len(values),
        "mean": float(np.mean(values)),
        "median": _quantile(values, 0.5),
        "q05": _quantile(values, INTERVAL[0]),
        "q95": _quantile(values, INTERVAL[1]),
    }


@dataclass(frozen=True)
class CandidateSummary:
    """One Theta across its matched seeds."""

    theta: float
    seeds: tuple[int, ...]
    losses: tuple[float, ...]
    recorded_onsets: tuple[int, ...]
    campaign_positives: tuple[int, ...]
    takeoff_probability: float

    @property
    def mean_loss(self) -> float:
        return float(np.mean(self.losses))

    def as_dict(self) -> dict[str, Any]:
        return {
            "theta": self.theta,
            "seeds": list(self.seeds),
            "loss": _summary(self.losses),
            "recorded_onsets": _summary(self.recorded_onsets),
            "campaign_positives": _summary(self.campaign_positives),
            "takeoff_probability": self.takeoff_probability,
        }


def _group_by_theta(
    cells: Iterable[Cell],
    payloads: dict[str, dict[str, Any]],
    phase: str,
) -> dict[float, dict[int, HullObservables]]:
    grouped: dict[float, dict[int, HullObservables]] = {}
    for cell in cells:
        if cell.phase != phase or cell.key not in payloads:
            continue
        grouped.setdefault(cell.theta, {})[cell.seed] = observables_from_payload(
            payloads[cell.key],
        )
    return grouped


def _coverage(
    design: FirstLookDesign,
    grouped: dict[float, dict[int, HullObservables]],
    phase: PhaseDesign,
) -> dict[str, Any]:
    expected = len(design.grid) * phase.seeds
    present = sum(len(seeds) for seeds in grouped.values())
    missing = [
        {"theta": theta, "seed": seed}
        for theta in design.grid
        for seed in phase.seed_values
        if seed not in grouped.get(theta, {})
    ]
    return {"expected": expected, "present": present, "missing": missing}


def _summarise_candidate(
    objective: ThetaObjective,
    theta: float,
    by_seed: dict[int, HullObservables],
    takeoff_onsets: int,
) -> CandidateSummary:
    seeds = tuple(sorted(by_seed))
    obs = [by_seed[s] for s in seeds]
    losses = tuple(
        sum(term.residual for term in objective.terms(o)) for o in obs
    )
    onsets = tuple(o.recorded_onsets for o in obs)
    return CandidateSummary(
        theta=float(theta),
        seeds=seeds,
        losses=losses,
        recorded_onsets=onsets,
        campaign_positives=tuple(o.campaign_positives for o in obs),
        takeoff_probability=float(np.mean([n >= takeoff_onsets for n in onsets])),
    )


def _selection_frequency(
    candidates: Sequence[CandidateSummary],
    *,
    resamples: int,
    seed: int,
) -> dict[float, float]:
    """How often each Theta wins when the matched seed set is resampled.

    Paired bootstrap: the same seed indices are drawn for every candidate, so
    a resample is a plausible alternative campaign, not a shuffled one. A
    winner that wins 40% of resamples is a weaker result than one that wins
    95%, and this is where that is made visible.
    """
    # Pairing needs a seed every candidate has; on a partial grid that is
    # the intersection, and with no common seed there is no paired answer.
    common = sorted(set.intersection(*(set(c.seeds) for c in candidates))) if candidates else []
    if not common:
        return {}
    losses = np.asarray([
        [c.losses[c.seeds.index(seed)] for seed in common] for c in candidates
    ], dtype=float)
    thetas = np.asarray([c.theta for c in candidates])
    n_seeds = len(common)
    rng = np.random.default_rng(seed)
    wins = np.zeros(len(candidates), dtype=int)
    for _ in range(resamples):
        draw = rng.integers(0, n_seeds, size=n_seeds)
        means = losses[:, draw].mean(axis=1)
        # Ties break toward the smaller Theta, as in fit_theta.
        order = np.lexsort((thetas, means))
        wins[order[0]] += 1
    return {float(t): float(w / resamples) for t, w in zip(thetas, wins)}


@dataclass(frozen=True)
class ReplicatedFitResult:
    """The replicated fit: a winner, its interval, and how often it wins."""

    design_id: str
    theta: float
    mean_loss: float
    grid: tuple[float, ...]
    candidates: tuple[CandidateSummary, ...]
    selection_frequency: dict[float, float]
    boundary_pinned: bool
    coverage: dict[str, Any]
    partial: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "contract": FIT_CONTRACT,
            "design_id": self.design_id,
            "theta": self.theta,
            "mean_loss": self.mean_loss,
            "grid": list(self.grid),
            "boundary_pinned": self.boundary_pinned,
            "selection_frequency": [
                {"theta": theta, "frequency": freq}
                for theta, freq in sorted(self.selection_frequency.items())
            ],
            "implied_per_copy_risk_interval": list(implied_per_copy_risk(self.theta)),
            "candidates": [c.as_dict() for c in self.candidates],
            "coverage": self.coverage,
            "partial": self.partial,
        }


def _refuse_incomplete(coverage: dict[str, Any], phase: str, allow_partial: bool) -> None:
    if coverage["missing"] and not allow_partial:
        raise ValueError(
            f"{phase}: {len(coverage['missing'])} of {coverage['expected']} cells "
            "missing; a partial grid is not a fit unless declared partial",
        )
    if coverage["present"] == 0:
        raise ValueError(f"{phase}: no cells to merge")


def merge_fit(
    design: FirstLookDesign,
    payloads: dict[str, dict[str, Any]],
    *,
    targets: FitTargets | None = None,
    allow_partial: bool = False,
) -> ReplicatedFitResult:
    """Pool the training cells into the replicated fit.

    Only cells whose phase is ``fit`` are read. The objective is the one the
    single-seed fit used; what changes is that each candidate's loss is a
    distribution over matched seeds and the winner is the smallest mean.
    """
    cells = enumerate_cells(design)
    grouped = _group_by_theta(cells, payloads, FIT_PHASE)
    coverage = _coverage(design, grouped, design.fit)
    _refuse_incomplete(coverage, FIT_PHASE, allow_partial)
    objective = ThetaObjective(
        targets=targets or load_fit_targets(),
        runner=_unreachable_runner,
        scenario_id=design.fit.scenario_id,
    )
    candidates = tuple(
        _summarise_candidate(objective, theta, grouped[theta], design.takeoff_recorded_onsets)
        for theta in design.grid if theta in grouped
    )
    best = min(candidates, key=lambda c: (c.mean_loss, c.theta))
    return ReplicatedFitResult(
        design_id=design.design_id,
        theta=best.theta,
        mean_loss=best.mean_loss,
        grid=design.grid,
        candidates=candidates,
        selection_frequency=_selection_frequency(
            candidates,
            resamples=design.bootstrap_resamples,
            seed=design.bootstrap_seed,
        ),
        boundary_pinned=best.theta in (design.grid[0], design.grid[-1]),
        coverage=coverage,
        partial=bool(coverage["missing"]),
    )


def _unreachable_runner(scenario_id: str, theta: float, seed: int) -> HullObservables:
    raise RuntimeError(
        "the merge scores stored observables; it never runs a hull "
        f"({scenario_id}, {theta}, {seed})",
    )


# ── merge: the replicated held-out report ─────────────────────────────────

def _neighbours(grid: Sequence[float], theta: float) -> tuple[float, ...]:
    """The fitted Theta and the grid points either side of it."""
    index = list(grid).index(theta)
    return tuple(grid[i] for i in (index - 1, index, index + 1) if 0 <= i < len(grid))


def _verdict_frequencies(
    observables: Sequence[HullObservables],
    targets: FitTargets,
) -> list[dict[str, Any]]:
    """covid.H1 and covid.H2 per seed, pooled into verdict frequencies."""
    per_anchor: dict[str, dict[str, Any]] = {}
    for obs in observables:
        for score in _greg_mortimer_scores(obs, targets):
            entry = per_anchor.setdefault(score.anchor_id, {
                "anchor_id": score.anchor_id,
                "quantity": score.quantity,
                "target": score.target,
                "verdicts": {"hit": 0, "miss": 0, "undefined": 0},
                "observed": [],
            })
            entry["verdicts"][score.verdict] += 1
            if score.observed is not None:
                entry["observed"].append(float(score.observed))
    out = []
    for entry in per_anchor.values():
        observed = entry.pop("observed")
        entry["observed"] = _summary(observed) if observed else None
        out.append(entry)
    return out


def _placement_frequency(
    observables: Sequence[HullObservables],
    targets: FitTargets,
) -> dict[str, Any]:
    """covid.H3 as a frequency: how often the hull lands above the IQR."""
    anchor = targets.by_id("covid.H3")
    upper = float(anchor.values["iqr_attack_rate"][1])
    shares = [o.positive_share for o in observables]
    defined = [s for s in shares if s is not None]
    return {
        "anchor_id": anchor.anchor_id,
        "quantity": "share of seeds placing the hull above the cross-ship IQR",
        "target": upper,
        "n_defined": len(defined),
        "n_undefined": len(shares) - len(defined),
        "frequency_above_iqr": (
            float(np.mean([s > upper for s in defined])) if defined else None
        ),
    }


def _held_out_at_theta(
    theta: float,
    by_seed: dict[int, HullObservables],
    targets: FitTargets,
    takeoff_onsets: int,
) -> dict[str, Any]:
    obs = [by_seed[s] for s in sorted(by_seed)]
    positives = [o.campaign_positives for o in obs]
    return {
        "theta": theta,
        "seeds": sorted(by_seed),
        "probability_no_positives": float(np.mean([p == 0 for p in positives])),
        "takeoff_probability": float(
            np.mean([o.recorded_onsets >= takeoff_onsets for o in obs]),
        ),
        "campaign_positives": _summary(positives),
        "scores": _verdict_frequencies(obs, targets),
        "placement": _placement_frequency(obs, targets),
    }


def merge_held_out(
    design: FirstLookDesign,
    payloads: dict[str, dict[str, Any]],
    theta: float,
    *,
    targets: FitTargets | None = None,
    allow_partial: bool = False,
) -> dict[str, Any]:
    """Score the held-out hull at a Theta already fixed by :func:`merge_fit`.

    The fitted Theta is the scored point; its half-decade neighbours are
    reported as sensitivity. Cells at other grid points are counted in the
    coverage and otherwise left alone.
    """
    if theta not in design.grid:
        raise ValueError(f"Theta {theta!r} is not on the declared grid")
    resolved = targets or load_fit_targets()
    grouped = _group_by_theta(enumerate_cells(design), payloads, HELD_OUT_PHASE)
    coverage = _coverage(design, grouped, design.held_out)
    _refuse_incomplete(coverage, HELD_OUT_PHASE, allow_partial)
    reported = [
        _held_out_at_theta(t, grouped[t], resolved, design.takeoff_recorded_onsets)
        for t in _neighbours(design.grid, theta) if t in grouped
    ]
    return {
        "design_id": design.design_id,
        "theta": theta,
        "scenario_id": design.held_out.scenario_id,
        "scored": next((r for r in reported if r["theta"] == theta), None),
        "sensitivity": [r for r in reported if r["theta"] != theta],
        "unscorable": ["covid.H4"],
        "coverage": coverage,
        "partial": bool(coverage["missing"]),
        "split_preserved": True,
    }


__all__ = [
    "Cell",
    "FirstLookDesign",
    "PhaseDesign",
    "ReplicatedFitResult",
    "design_path",
    "enumerate_cells",
    "load_design",
    "merge_fit",
    "merge_held_out",
    "observables_from_payload",
    "run_cell",
]
