"""The external bound on the cabin-localization fraction ``f`` (task #12).

``f`` is the fraction of a voyage's transmission events in which infector and
infectee shared a stateroom.  Nothing measures it: no study on any ship reports
the share of norovirus transmission occurring between cabinmates, and none
reports the cabin-level case distribution that would give it without a model
(tranche 17).  What can be stated without any epidemiology at all is a
**ceiling**, because the first case in any cabin was infected somewhere else by
construction.  In a berthing plan with ``c`` occupied cabins holding ``p``
people, at most ``p - c`` of the ``p`` infections can have happened in a cabin::

    f <= 1 - c / p

That is occupancy combinatorics.  It is not derived from an attack rate, so it
is admissible beside anchors A4/A8/A9 --- unlike the tighter ``f <= 0.18-0.45``
recorded in the register, which is derived from the same outbreak attack rates
those anchors score against and is barred while they score.

The register's headline ``f <= 0.5`` is the special case ``p = 2c``: every cabin
holding exactly two people.  Real ships do not sail that way, and cruise
operators publish the departure by construction of their own capacity measure.
Carnival's statistical notes define available lower berth days as assuming
"each cabin we offer for sale accommodates two passengers", and state that
occupancy "percentages in excess of 100% indicate that on average more than two
passengers occupied some cabins".  So published occupancy *is* ``p / 2c``, and
the ceiling follows from it as ``1 - 1 / (2 * occupancy)``.  Occupancy has run
above 100% every full year since the restart, so **0.5 is not the ceiling; it is
the floor of the ceiling**, and the register's bound was slightly too tight
rather than conservative.

The same arithmetic applies inside the repository, where the berthing plan is
declared rather than published: ``default_cabin_size`` in ``orchestrator_init``
puts passengers in doubles, crew in triples and officers in singles, so a hull's
ceiling is a property of its own layout and is not 0.5 either.

Grades, carried here because the values are: the occupancy and berth-census
inputs are **M** (audited operator filings and the operator's own fact sheet),
and the transmission-event ceiling they imply is **C**, because the step from a
berthing plan to a bound on transmission events is an argument rather than a
measurement.  Register row: "Cabin-localization fraction ``f``", §3.1.

Three things this module deliberately does not do.

* It states **no lower bound**.  ``f = 0`` is not excluded by anything, here or
  in the literature, and a ceiling is not an interval.
* It adopts **no central value**.  Every function here returns a bound.
* It does not bound the *other* quantity that used to share this one's name.
  The fraction of a symptomatic host's emesis episodes that occur in its own
  cabin (``park_surface_check.EMESIS_IN_OWN_CABIN_SWEEP``) is a location
  fraction for one behaviour, is swept between 0.50 and 1.00 in the Park
  harness, and is not this ``f``: nothing about occupancy combinatorics caps it
  at a half.  The two were both written "cabin-localization ``f``" and the
  screen spec's 0.80-0.99 interval for the emesis fraction sits entirely above
  this ``f``'s ceiling, which is how the collision was found.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Mapping
from typing import NamedTuple

# ``orchestrator_init.default_cabin_size``, injected rather than imported: that
# module pulls in the whole lab stack, and this one is read by the sourcing
# harnesses.
CabinSizeRule = Callable[[str, str, object], int | None]

# Occupancy index (passengers per lower berth) as published by the two largest
# operators in their own filings.  Both define the denominator as two per cabin,
# which is what makes the index convertible into people per cabin at all.
#
#   RCL 8-K, 2024 results (sec.gov/Archives/edgar/data/884887, filed
#     2025-01-28), "Occupancy" line: 108.5% FY2024, 105.6% FY2023
#   CCL 8-K, 4Q/FY2024 results (carnivalcorp.com), statistical information,
#     "Occupancy percentage" note (c): 105% FY2024, 100% FY2023
PUBLISHED_OCCUPANCY_INDEX: dict[tuple[str, int], float] = {
    ("RCL", 2023): 1.056,
    ("RCL", 2024): 1.085,
    ("CCL", 2023): 1.00,
    ("CCL", 2024): 1.05,
}

# Royal Caribbean's Symphony of the Seas fact sheet (2,759 staterooms, 5,518
# guests at double occupancy, 6,680 total).  The double-occupancy figure is
# exactly twice the stateroom count, which is the identity above; the total is
# the physical berth maximum, and it is the largest ceiling any single hull in
# the passenger fleet can reach.
SYMPHONY_STATEROOMS = 2759
SYMPHONY_GUESTS_DOUBLE = 5518
SYMPHONY_GUESTS_MAXIMUM = 6680


class BerthCeiling(NamedTuple):
    """A structural ceiling on ``f`` and the berthing plan it came from."""

    occupants: int
    cabins: int
    ceiling: float


def ceiling_from_berths(occupants: int, cabins: int) -> float:
    """Return ``1 - cabins / occupants``, the largest ``f`` the plan permits.

    Raises ``ValueError`` on a plan that cannot exist: no occupants, or more
    occupied cabins than people to occupy them.
    """
    if occupants <= 0:
        raise ValueError("a berthing plan with no occupants bounds nothing")
    if cabins <= 0:
        raise ValueError("occupants cannot be berthed in zero cabins")
    if cabins > occupants:
        raise ValueError(
            f"{cabins} occupied cabins cannot hold {occupants} occupants",
        )
    return 1.0 - cabins / occupants


def ceiling_from_cabin_sizes(sizes: Mapping[int, int]) -> BerthCeiling:
    """Ceiling for a plan given as ``{occupants per cabin: cabin count}``."""
    occupants = sum(size * count for size, count in sizes.items())
    cabins = sum(sizes.values())
    return BerthCeiling(occupants, cabins, ceiling_from_berths(occupants, cabins))


def ceiling_from_occupancy_index(occupancy_index: float) -> float:
    """Ceiling implied by a published occupancy index (1.0 = double occupancy).

    The index's denominator is two berths per cabin by definition, so people per
    cabin is ``2 * index`` and the ceiling is ``1 - 1 / (2 * index)``.  An index
    below 1.0 means some cabins sailed with a single occupant; the ceiling then
    falls below a half, because a solo occupant cannot have been infected by a
    cabinmate.
    """
    if occupancy_index <= 0.0:
        raise ValueError("occupancy index must be positive")
    return 1.0 - 1.0 / (2.0 * occupancy_index)


def published_ceiling_interval() -> tuple[float, float]:
    """Bracket the ceiling over every published operator-year on record.

    This is the external bound the register row asks for: it is read off
    capacity accounting, not off an outbreak, so it survives beside the scored
    attack-rate anchors.
    """
    ceilings = [
        ceiling_from_occupancy_index(index)
        for index in PUBLISHED_OCCUPANCY_INDEX.values()
    ]
    return min(ceilings), max(ceilings)


def symphony_ceilings() -> dict[str, float]:
    """Per-hull ceilings for the largest published berth census.

    ``double`` reproduces 0.5 exactly, which is the check that the identity
    ``occupancy index = occupants / 2 cabins`` is the operators' own; ``maximum``
    is what the same hull permits with every upper berth sold.
    """
    return {
        "double": ceiling_from_berths(SYMPHONY_GUESTS_DOUBLE, SYMPHONY_STATEROOMS),
        "maximum": ceiling_from_berths(SYMPHONY_GUESTS_MAXIMUM, SYMPHONY_STATEROOMS),
    }


def _cabin_zone_plan(
    zones: Iterable[Mapping[str, object]],
    cabin_size_of: CabinSizeRule,
) -> dict[str, tuple[int, int]]:
    """Collect ``{zone id: (occupants, cabins)}`` for cabin-corridor zones."""
    plan: dict[str, tuple[int, int]] = {}
    for zone in zones:
        if zone.get("type") != "Cabin_Corridor":
            continue
        zone_id = str(zone.get("id", ""))
        occupants = zone.get("max_occupancy")
        size = cabin_size_of(
            zone_id,
            str(zone.get("type", "")),
            zone.get("cabin_size"),
        )
        if not isinstance(occupants, int) or occupants <= 0:
            continue
        if not isinstance(size, int) or size < 1:
            continue
        plan[zone_id] = (occupants, math.ceil(occupants / size))
    return plan


def platform_ceiling(
    layout: Mapping[str, object],
    cabin_size_of: CabinSizeRule,
    zone_filter: Callable[[str], bool] | None = None,
) -> BerthCeiling:
    """Ceiling for one platform's declared berthing plan.

    ``cabin_size_of`` is ``orchestrator_init.default_cabin_size``, passed in so
    this module stays importable without the simulation package.  ``zone_filter``
    optionally restricts the population --- passenger cabins only, crew cabins
    only --- because ``f`` is defined over whichever transmission events are
    being counted, and the two populations are berthed differently.
    """
    zones = layout.get("zones", [])
    if not isinstance(zones, list):
        raise ValueError("layout has no zone list")
    plan = _cabin_zone_plan(zones, cabin_size_of)
    if zone_filter is not None:
        plan = {
            zone_id: value
            for zone_id, value in plan.items()
            if zone_filter(zone_id)
        }
    occupants = sum(value[0] for value in plan.values())
    cabins = sum(value[1] for value in plan.values())
    return BerthCeiling(occupants, cabins, ceiling_from_berths(occupants, cabins))


def is_crew_cabin_zone(zone_id: str) -> bool:
    """Crew and officer cabin-corridor prefixes, per ``default_cabin_size``."""
    return zone_id.startswith(("Crew_", "CC_", "OC_"))


def report() -> str:
    """Human-readable statement of the bound and of what stays unbounded."""
    lines = [
        "Cabin-localization fraction f: the ceiling, and only the ceiling",
        "=" * 70,
        "",
        "f = share of transmission events between cabinmates.",
        "Ceiling = 1 - cabins/occupants, because every cabin's first case was",
        "infected elsewhere.  No literature enters this line.",
        "",
        "Published capacity accounting (index = passengers per lower berth):",
    ]
    for (line, year), index in sorted(PUBLISHED_OCCUPANCY_INDEX.items()):
        lines.append(
            f"  {line} {year}  index {index:.3f}  ->  "
            f"f <= {ceiling_from_occupancy_index(index):.4f}",
        )
    low, high = published_ceiling_interval()
    lines += [
        f"  bracket over published operator-years: f <= {low:.4f} to {high:.4f}",
        "",
        "Single-hull berth census (Symphony of the Seas fact sheet):",
    ]
    for label, value in sorted(symphony_ceilings().items()):
        lines.append(f"  {label:>8} occupancy  ->  f <= {value:.4f}")
    lines += [
        "",
        "The register's 0.5 is the exact-double-occupancy case and is the",
        "floor of this ceiling, not the ceiling: published occupancy has been",
        "above 100% every full year since the restart.",
        "",
        "Not bounded here, and not bounded anywhere:",
        "  * any lower bound.  f = 0 is not excluded.",
        "  * any central value.  Nothing selects one.",
        "  * the emesis-in-own-cabin fraction, a different quantity that used",
        "    to share this one's name (park_surface_check).",
    ]
    return "\n".join(lines)


if __name__ == "__main__":  # pragma: no cover - manual harness
    print(report())
