"""Adaptive-density refinement of the COVID imports x Theta sweep.

Stage 1 of the sweep is an ordinary boarding screen (a product grid over
import count and Theta on matched seeds, ``covid_boarding_screen``). Stage 2
does not run the grid again at finer pitch: it reads the stage-1 surface and
inserts a geometric midpoint only between neighbouring grid cells where the
response moves fast, or where it crosses the observed Diamond Princess
counts. The refined points are written as a second screen design with an
explicit ``points`` list, so the Batch worker, merge and pairing are the
stage-1 code paths unchanged.

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
    """Index the stage-1 surface by (Theta, imports) at one infection age."""
    out: dict[tuple[float, int], CellResponse] = {}
    for entry in surface["surface"]:
        if float(entry["infection_age_days"]) != infection_age_days:
            continue
        key = (float(entry["theta"]), int(entry["imports"]))
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
    thetas = sorted({k[0] for k in responses})
    imports = sorted({k[1] for k in responses})
    pairs: list[tuple[CellResponse, CellResponse, str]] = []
    for theta in thetas:
        for lo, hi in zip(imports, imports[1:]):
            if (theta, lo) in responses and (theta, hi) in responses:
                pairs.append((responses[(theta, lo)], responses[(theta, hi)], "imports"))
    for n in imports:
        for lo, hi in zip(thetas, thetas[1:]):
            if (lo, n) in responses and (hi, n) in responses:
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
    surface: dict[str, Any],
    *,
    design_id: str,
    rule: RefinementRule,
    infection_age_days: float = 0.0,
) -> dict[str, Any]:
    """Stage-2 screen design: the parent's axes, an explicit point list."""
    responses = responses_from_surface(surface, infection_age_days=infection_age_days)
    if not responses:
        raise ValueError("the stage-1 surface has no cells at the requested infection age")
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
            "rule": rule.as_dict(),
            "stage1_cells_read": len(responses),
            "chosen": chosen,
        },
        "note": (
            "Stage 2 of the adaptive-density import sweep: geometric midpoints "
            "inserted only where the stage-1 response moved faster than the "
            "declared tolerances or crossed the observed counts. Same matched "
            "seeds as the parent; pair by (Theta, imports, seed)."
        ),
    })
    return design
