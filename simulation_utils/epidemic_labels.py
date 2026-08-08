"""Epidemic takeoff vs fizzle labels for campaign derived metrics / Stan Stage A.

**Takeoff** — the wave is still accelerating when VSP first fires
(``trigger_status`` enters SUSPECTED/CONFIRMED/LOCKDOWN). Suppression is then
attributable to the response, not a pre-threshold fade.

**Fizzle** — incidence never reaches a VSP trigger, or VSP fires only after the
incidence curve has already lost acceleration (discrete second derivative of
incidence ``< 0`` at onset). Even a late VSP trigger counts as fizzle when the
curve is already bending down.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

# Engine tokens that mean VSP / reactive escalation has kicked in.
_VSP_ACTIVE = frozenset(
    {
        "SUSPECTED",
        "SUSPECT",
        "CONFIRMED",
        "CONFIRM",
        "LOCKDOWN",
    }
)


def _status_token(raw: Any) -> str:
    return str(raw if raw is not None else "none").strip().upper()


def _incidence_series(timeseries: Sequence[Mapping[str, Any]]) -> list[int]:
    """Per-epoch new infections; prefer ``new_infections``, else Δ(I+R)."""
    inc: list[int] = []
    prev_ever = 0
    for point in timeseries:
        if "new_infections" in point and point.get("new_infections") is not None:
            inc.append(max(0, int(point.get("new_infections") or 0)))
            prev_ever = int(point.get("infected", 0) or 0) + int(
                point.get("recovered", 0) or 0
            )
            continue
        ever = int(point.get("infected", 0) or 0) + int(
            point.get("recovered", 0) or 0
        )
        inc.append(max(0, ever - prev_ever))
        prev_ever = ever
    return inc


def first_vsp_index(timeseries: Sequence[Mapping[str, Any]]) -> int | None:
    """Index of first epoch where VSP / reactive trigger is active."""
    for idx, point in enumerate(timeseries):
        if _status_token(point.get("trigger_status", "none")) in _VSP_ACTIVE:
            return idx
    return None


def incidence_second_difference(incidence: Sequence[int], index: int) -> int | None:
    """Discrete second derivative of incidence at ``index`` (needs ≥3 points)."""
    if index < 2 or index >= len(incidence):
        return None
    return int(incidence[index]) - 2 * int(incidence[index - 1]) + int(
        incidence[index - 2]
    )


def epidemic_took_off(timeseries: Sequence[Mapping[str, Any]]) -> bool:
    """True if the epidemic took off into VSP while still accelerating.

    Requires:
    1. VSP (or equivalent trigger) fires at some epoch ``t``, and
    2. at that epoch, ``Δ² incidence[t] >= 0`` (still accelerating / not yet
       bending down). If ``Δ² < 0``, the wave is already fizzling even if VSP
       has kicked in. No VSP → fizzle.
    """
    if not timeseries or len(timeseries) < 3:
        return False
    onset = first_vsp_index(timeseries)
    if onset is None:
        return False
    d2 = incidence_second_difference(_incidence_series(timeseries), onset)
    if d2 is None:
        # Trigger before we can form a second difference → treat as fizzle.
        return False
    return d2 >= 0


def seed_established(ever_infected: int) -> bool:
    """Legacy weak signal: more than the usual 1–2 index cases."""
    return ever_infected > 2
