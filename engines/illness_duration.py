"""Illness duration drawn from a measured survival curve, not a point value.

``recovery_day`` is a single day count: under it every symptomatic host is ill
for exactly that long, so nobody is ill at day 3.1 and everybody is ill at day
2.9. An ``illness_duration`` profile block with ``draw: empirical_survival``
replaces the point with the discrete survival table the block carries — one
integer-day draw per infection, stamped on the record so the pharmaceutical
override shortens the host's drawn duration rather than the profile constant.

The shipped block for norwalk_gi is the Harris 2019 diarrhoea curve (BMC
Infect Dis 19:87, Fig 4C). Days between authored rows are linearly
interpolated; the table's gaps are measurement gaps (a legend overlying the
curve), not a statement that the survival function is discontinuous.
"""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np

DRAW_POINT = "point"
DRAW_EMPIRICAL_SURVIVAL = "empirical_survival"
SUPPORTED_DRAWS = (DRAW_POINT, DRAW_EMPIRICAL_SURVIVAL)

ILLNESS_DURATION_UNIT_DAYS = "days"

_ILLNESS_DURATION_KEYS = frozenset({"draw", "unit", "survival", "notes"})


def _reject_unknown_keys(where: str, cfg: Mapping[str, Any]) -> None:
    """Refuse config keys this model does not read.

    A misspelled key would otherwise fall back to a default and shift illness
    duration invisibly.
    """
    unknown = sorted(set(cfg) - _ILLNESS_DURATION_KEYS)
    if unknown:
        raise ValueError(f"{where} has unknown keys: {unknown}")


def _validate_survival_table(
    where: str, rows: list[Mapping[str, Any]],
) -> tuple[tuple[int, float], ...]:
    """Validate and normalize the authored survival table.

    The table is a survival function S(d) over integer days after onset: it
    must start at day 0 with S = 1.0, end at S = 0.0, have strictly increasing
    day values, and be monotone non-increasing in S. Rows are
    ``{"day": <int>, "probability": <float>}`` pairs.
    """
    if not isinstance(rows, list) or len(rows) < 2:
        raise ValueError(
            f"{where}.survival must list at least two day/probability rows",
        )
    points: list[tuple[int, float]] = []
    for row in rows:
        day = row.get("day")
        probability = row.get("probability")
        if not isinstance(day, int) or isinstance(day, bool):
            raise ValueError(
                f"{where}.survival day values must be integers: {day!r}",
            )
        if not isinstance(probability, (int, float)):
            raise ValueError(
                f"{where}.survival probability values must be numbers: "
                f"{probability!r}",
            )
        points.append((day, float(probability)))
    days = [day for day, _ in points]
    probs = [prob for _, prob in points]
    if days[0] != 0 or probs[0] != 1.0:
        raise ValueError(
            f"{where}.survival must start at day 0 with probability 1.0: "
            f"got ({days[0]}, {probs[0]})",
        )
    if probs[-1] != 0.0:
        raise ValueError(
            f"{where}.survival must end at probability 0.0: "
            f"got {probs[-1]}",
        )
    if any(b <= a for a, b in zip(days, days[1:])):
        raise ValueError(
            f"{where}.survival day values must be strictly increasing: {days}",
        )
    if any(b > a for a, b in zip(probs, probs[1:])):
        raise ValueError(
            f"{where}.survival must be non-increasing: {probs}",
        )
    if any(prob < 0.0 or prob > 1.0 for prob in probs):
        raise ValueError(
            f"{where}.survival probabilities must lie in [0, 1]: {probs}",
        )
    return tuple(points)


@dataclass(frozen=True)
class IllnessDurationModel:
    """How an infection's illness duration is drawn.

    ``point`` (the default when the block is absent) stamps nothing: the
    infection record keeps no ``recovery_day`` and every consumer reads the
    profile constant, bit-identical to the pre-distribution behaviour.
    ``empirical_survival`` draws an integer day count by inverting the
    authored survival table: ``T`` is the smallest integer day with
    S(T) <= u, u ~ Uniform(0, 1), so P(T = d) = S(d-1) - S(d). The draw is
    discrete because the underlying data are integer-day self-reports.
    """

    draw: str = DRAW_POINT
    unit: str = ILLNESS_DURATION_UNIT_DAYS
    survival: tuple[tuple[int, float], ...] = ()

    def __post_init__(self) -> None:
        if self.draw not in SUPPORTED_DRAWS:
            raise ValueError(
                f"illness_duration.draw must be one of {SUPPORTED_DRAWS}: "
                f"{self.draw!r}",
            )
        if self.unit != ILLNESS_DURATION_UNIT_DAYS:
            raise ValueError(
                f"illness_duration.unit must be "
                f"{ILLNESS_DURATION_UNIT_DAYS!r}: {self.unit!r}",
            )
        if self.draw == DRAW_EMPIRICAL_SURVIVAL and not self.survival:
            raise ValueError(
                "illness_duration.draw 'empirical_survival' requires a "
                "survival table",
            )

    @classmethod
    def from_mapping(
        cls, block: Mapping[str, Any] | None,
    ) -> IllnessDurationModel | None:
        """Build from an ``illness_duration`` profile block, or ``None``.

        ``None`` is the legacy path: a profile with no block keeps the point
        ``recovery_day`` it shipped with. A block's table is validated
        whenever one is present, even under ``draw: point`` — a malformed
        table shipped inertly would be an undetected data defect.
        """
        if not block:
            return None
        cfg = dict(block)
        _reject_unknown_keys("illness_duration", cfg)
        draw = str(cfg.get("draw", DRAW_POINT))
        unit = str(cfg.get("unit", ILLNESS_DURATION_UNIT_DAYS))
        table = cfg.get("survival")
        points: tuple[tuple[int, float], ...] = ()
        if table is not None:
            points = _validate_survival_table("illness_duration", table)
        return cls(draw=draw, unit=unit, survival=points)

    def survival_at(self, day: int) -> float:
        """S(day), interpolating linearly between authored rows."""
        days = [d for d, _ in self.survival]
        index = bisect_left(days, day)
        if index < len(days) and days[index] == day:
            return self.survival[index][1]
        if index == 0:
            return self.survival[0][1]
        if index == len(days):
            return self.survival[-1][1]
        day_lo, prob_lo = self.survival[index - 1]
        day_hi, prob_hi = self.survival[index]
        share = (day - day_lo) / (day_hi - day_lo)
        return prob_lo + share * (prob_hi - prob_lo)

    def sample_days(self, rng: np.random.Generator) -> int:
        """Draw this infection's illness duration in whole days."""
        u = float(rng.random())
        last_day = self.survival[-1][0]
        for day in range(1, last_day + 1):
            if self.survival_at(day) <= u:
                return day
        return last_day
