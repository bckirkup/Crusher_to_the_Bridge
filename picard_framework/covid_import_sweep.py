"""Adaptive-density refinement of the COVID imports x Theta sweep.

Stage 1 of the sweep is an ordinary boarding screen (a product grid over
import count and Theta on matched seeds, ``covid_boarding_screen``). Later
stages do not run the grid again at finer pitch: each reads the union of
every surface run so far and inserts a geometric midpoint only between
neighbouring cells where the response moves fast, or where it crosses the
observed Diamond Princess counts. Neighbours are taken along each row and
column *as populated*, so a stage-2 midpoint becomes a stage-3 neighbour and
the pitch closes only where earlier stages found the response moving. The
refined points are written as a screen design with an explicit ``points``
list, so the Batch worker, merge and pairing are the stage-1 code paths
unchanged. Tolerances are declared per stage and are expected to tighten as
the pitch closes; the refined design records them.

Responses read off each cell, all on the same matched seeds:

* ``takeoff_probability`` -- the fraction of seeds that ignite;
* conditional on takeoff, the median onsets before the split day and the
  median total recorded onsets (log scale).

A neighbouring pair is a candidate when any response changes by more than
its tolerance across the pair, or when a conditional median crosses the
observed count. Candidates are ranked by their largest normalised change
and the top ``budget`` midpoints are kept. Nothing here fits: the observed
counts only decide *where* to look, never which cell is preferred.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

# Diamond Princess retrospective counts the fit spec scores (onsets before
# 6 Feb and total recorded onsets); used to locate crossings only.
OBSERVED_EARLY_ONSETS = 34
OBSERVED_TOTAL_ONSETS = 197


@dataclass(frozen=True)
class RefinementRule:
    """Tolerances that make a neighbouring pair worth a midpoint."""

    takeoff_tolerance: float = 0.25
    log_ratio_tolerance: float = math.log(2.0)
    budget: int = 12
    observed_early: int = OBSERVED_EARLY_ONSETS
    observed_total: int = OBSERVED_TOTAL_ONSETS

    def __post_init__(self) -> None:
        if not 0.0 < self.takeoff_tolerance <= 1.0:
            raise ValueError("takeoff_tolerance must lie in (0, 1]")
        if self.log_ratio_tolerance <= 0.0:
            raise ValueError("log_ratio_tolerance must be positive")
        if self.budget < 1:
            raise ValueError("budget must be at least 1")

    def as_dict(self) -> dict[str, Any]:
        return {
            "takeoff_tolerance": self.takeoff_tolerance,
            "log_ratio_tolerance": self.log_ratio_tolerance,
            "budget": self.budget,
            "observed_early": self.observed_early,
            "observed_total": self.observed_total,
        }


@dataclass(frozen=True)
class CellResponse:
    theta: float
    imports: int
    takeoff: float
    early_median: float | None
    total_median: float | None


def _conditional_median(entry: dict[str, Any], field: str) -> float | None:
    block = entry.get("conditional_on_takeoff", {}).get(field)
    if block is None:
        return None
    return float(block["median"])


def responses_from_surface(
    surface: dict[str, Any], *, infection_age_days: float = 0.0,
) -> dict[tuple[float, int], CellResponse]:
    """Index one merged surface by (Theta, imports) at one infection age."""
    return responses_from_surfaces([surface], infection_age_days=infection_age_days)


def responses_from_surfaces(
    surfaces: Sequence[dict[str, Any]], *, infection_age_days: float = 0.0,
) -> dict[tuple[float, int], CellResponse]:
    """Union of every stage's cells; a (Theta, imports) may appear only once."""
    out: dict[tuple[float, int], CellResponse] = {}
    for entry in (e for s in surfaces for e in s["surface"]):
        if float(entry["infection_age_days"]) != infection_age_days:
            continue
        key = (float(entry["theta"]), int(entry["imports"]))
        if key in out:
            raise ValueError(f"cell {key} appears in more than one surface")
        out[key] = CellResponse(
            theta=key[0],
            imports=key[1],
            takeoff=float(entry["takeoff_probability"]),
            early_median=_conditional_median(entry, "onsets_before_split_day"),
            total_median=_conditional_median(entry, "recorded_onsets"),
        )
    return out


def _log_change(a: float | None, b: float | None) -> float:
    if a is None or b is None:
        return 0.0
    return abs(math.log1p(b) - math.log1p(a))


def _crosses(a: float | None, b: float | None, observed: int) -> bool:
    if a is None or b is None:
        return False
    return (a - observed) * (b - observed) < 0.0


def pair_score(a: CellResponse, b: CellResponse, rule: RefinementRule) -> dict[str, Any]:
    """Largest normalised response change across a neighbouring pair.

    A crossing of an observed count scores at least 1.0 (the threshold), so
    a pair that brackets the record is refined even when the medians on
    either side are close.
    """
    takeoff = abs(b.takeoff - a.takeoff) / rule.takeoff_tolerance
    early = _log_change(a.early_median, b.early_median) / rule.log_ratio_tolerance
    total = _log_change(a.total_median, b.total_median) / rule.log_ratio_tolerance
    crosses_early = _crosses(a.early_median, b.early_median, rule.observed_early)
    crosses_total = _crosses(a.total_median, b.total_median, rule.observed_total)
    score = max(takeoff, early, total)
    if crosses_early or crosses_total:
        score = max(score, 1.0)
    return {
        "score": score,
        "takeoff_change": takeoff * rule.takeoff_tolerance,
        "early_log_change": early * rule.log_ratio_tolerance,
        "total_log_change": total * rule.log_ratio_tolerance,
        "crosses_observed_early": crosses_early,
        "crosses_observed_total": crosses_total,
    }


def _midpoint(a: CellResponse, b: CellResponse) -> tuple[float, int] | None:
    theta = math.sqrt(a.theta * b.theta)
    imports = int(round(math.sqrt(a.imports * b.imports)))
    if imports in (a.imports, b.imports) and math.isclose(a.theta, b.theta):
        return None
    return (theta, imports)


def _neighbour_pairs(
    responses: dict[tuple[float, int], CellResponse],
) -> list[tuple[CellResponse, CellResponse, str]]:
    """Adjacent cells along each populated row (imports) and column (Theta).

    Adjacency is taken within the row or column as it is actually populated,
    so after refinement a midpoint pairs with the cells on either side of it
    rather than leaving a gap in a global lattice.
    """
    rows: dict[float, list[int]] = {}
    cols: dict[int, list[float]] = {}
    for theta, n in responses:
        rows.setdefault(theta, []).append(n)
        cols.setdefault(n, []).append(theta)
    pairs: list[tuple[CellResponse, CellResponse, str]] = []
    for theta, ns in sorted(rows.items()):
        ns.sort()
        for lo, hi in zip(ns, ns[1:]):
            pairs.append((responses[(theta, lo)], responses[(theta, hi)], "imports"))
    for n, ts in sorted(cols.items()):
        ts.sort()
        for lo, hi in zip(ts, ts[1:]):
            pairs.append((responses[(lo, n)], responses[(hi, n)], "theta"))
    return pairs


def refine_points(
    responses: dict[tuple[float, int], CellResponse],
    rule: RefinementRule,
) -> list[dict[str, Any]]:
    """Ranked midpoints for the pairs whose response moves fastest."""
    candidates: list[dict[str, Any]] = []
    for a, b, axis in _neighbour_pairs(responses):
        scored = pair_score(a, b, rule)
        if scored["score"] < 1.0:
            continue
        mid = _midpoint(a, b)
        if mid is None or mid in responses:
            continue
        candidates.append({
            "theta": mid[0],
            "imports": mid[1],
            "axis": axis,
            "between": [[a.theta, a.imports], [b.theta, b.imports]],
            **scored,
        })
    candidates.sort(key=lambda c: (-c["score"], c["theta"], c["imports"]))
    chosen: list[dict[str, Any]] = []
    seen: set[tuple[float, int]] = set()
    for cand in candidates:
        key = (round(cand["theta"], 6), cand["imports"])
        if key in seen:
            continue
        seen.add(key)
        chosen.append(cand)
        if len(chosen) >= rule.budget:
            break
    return chosen


def refined_design(
    parent: dict[str, Any],
    surface: dict[str, Any] | Sequence[dict[str, Any]],
    *,
    design_id: str,
    rule: RefinementRule,
    infection_age_days: float = 0.0,
    stage: int = 2,
) -> dict[str, Any]:
    """Next-stage screen design: the root grid's axes, an explicit point list.

    ``parent`` is the stage-1 (root) design whose axes, seeds and takeoff
    threshold every stage shares; ``surface`` is every merged surface run so
    far (stage 1 alone for stage 2; stages 1 and 2 for stage 3, ...).
    """
    surfaces = [surface] if isinstance(surface, dict) else list(surface)
    responses = responses_from_surfaces(surfaces, infection_age_days=infection_age_days)
    if not responses:
        raise ValueError("no surface cells at the requested infection age")
    if stage < 2:
        raise ValueError("refinement stages start at 2")
    chosen = refine_points(responses, rule)
    design = {
        k: parent[k] for k in (
            "scenario_id", "thetas", "infection_age_days", "imports",
            "sanitary_visit_mode", "seed_base", "seeds", "takeoff_recorded_onsets",
        )
    }
    design.update({
        "design_id": design_id,
        "parent_design": str(parent["design_id"]),
        "points": [[c["theta"], infection_age_days, c["imports"]] for c in chosen],
        "refinement": {
            "stage": stage,
            "rule": rule.as_dict(),
            "surfaces_read": [str(s["design"]["design_id"]) for s in surfaces],
            "cells_read": len(responses),
            "chosen": chosen,
        },
        "note": (
            f"Stage {stage} of the adaptive-density import sweep: geometric "
            "midpoints inserted only where the response over every earlier "
            "stage moved faster than the declared tolerances or crossed the "
            "observed counts. Same matched seeds as the root grid; pair by "
            "(Theta, imports, seed)."
        ),
    })
    return design
