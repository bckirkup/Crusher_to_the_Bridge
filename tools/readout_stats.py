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
