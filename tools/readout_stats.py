"""Shared summary statistics for diagnostic probe readouts."""

from __future__ import annotations

from typing import Any


def quantiles(vals: list[float]) -> dict[str, Any]:
    """Linear-interpolated quantile summary for a list of numbers."""
    if not vals:
        return {"n": 0}
    ordered = sorted(float(v) for v in vals)
    n = len(ordered)

    def q(p: float) -> float:
        k = (n - 1) * p
        lo = int(k)
        hi = min(lo + 1, n - 1)
        return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)

    return {
        "n": n,
        "min": ordered[0],
        "q25": q(0.25),
        "median": q(0.5),
        "q75": q(0.75),
        "max": ordered[-1],
        "mean": sum(ordered) / n,
    }


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial fraction ``k/n``."""
    if n <= 0:
        return (0.0, 0.0)
    p = k / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    half = (z / denom) * ((p * (1 - p) + z2 / (4 * n)) / n) ** 0.5
    return (max(0.0, centre - half), min(1.0, centre + half))
