"""The complement a hull carries, read from the hull.

A run has two things that must agree: the platform whose spatial graph, zones
and air paths it walks, and the number of agents it puts in them.  Nothing in
the run spec couples them, so a complement can be stated that the hull does
not berth -- and one was: every bounded screen and feasibility gate ran 450
agents on ``mega_cruise_5000``, a 129-zone hull declaring 5,000 passengers and
2,000 crew.  That is the expedition class's complement in the mega class's
graph, so zone occupancy sat ~1/15 of nominal, the density kernel's
``reference_occupancy`` was never approached, and the VSP 3% rule was applied
to a 134-person crew denominator where it means five cases.

The complement is therefore not a free parameter of a run: it is a property of
the platform, declared in that platform's ``spatial_layout.json`` as
``nominal_complement``.  This module is the one place that reads it, so a
second table cannot drift from the first.  ``mega_cruise_5000``'s id names its
passengers alone; the other three name passengers plus crew; neither is
inferred from the id.
"""

from __future__ import annotations

import json
from pathlib import Path

from simulation_utils.paths import validated_open

REPO_ROOT = Path(__file__).resolve().parents[1]
PLATFORMS = REPO_ROOT / "data" / "platforms"


def declaring_platforms() -> tuple[str, ...]:
    """Platforms that declare a nominal complement, in id order.

    Only the cruise hulls carry a declaration; the naval and fictional
    platforms do not, and a caller that needs their complement must source it
    rather than default it.
    """
    return tuple(
        sorted(
            path.name
            for path in PLATFORMS.iterdir()
            if (path / "spatial_layout.json").is_file()
            and _declared_block(path.name) is not None
        ),
    )


def _declared_block(platform_id: str) -> dict[str, int] | None:
    """The platform's ``nominal_complement`` block, or ``None`` if absent."""
    layout = PLATFORMS / platform_id / "spatial_layout.json"
    if not layout.is_file():
        raise FileNotFoundError(
            f"{platform_id} has no spatial_layout.json under {PLATFORMS}: a "
            "run cannot walk a hull the repository does not carry",
        )
    with validated_open(
        str(layout),
        "r",
        allowed_roots=(str(PLATFORMS),),
        encoding="utf-8",
    ) as handle:
        complement = json.load(handle).get("nominal_complement")
    return complement if isinstance(complement, dict) else None


def _berths(platform_id: str, role: str, value: object) -> int:
    """A declared berth count, refusing anything that is not one.

    ``bool`` is an ``int`` in Python and a fraction of a person is not a
    complement, so both are refused rather than coerced: a hull that berths
    ``True`` passengers would otherwise sail with one.
    """
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RuntimeError(
            f"{platform_id} declares nominal_complement.{role} = {value!r}: a "
            "hull berths a positive whole number of people",
        )
    return value


def declared_complement(platform_id: str) -> tuple[int, int]:
    """The platform's declared ``(passengers, crew)`` complement."""
    complement = _declared_block(platform_id)
    if complement is None:
        raise RuntimeError(
            f"{platform_id} declares no nominal_complement: a run cannot state "
            "a complement its hull does not berth",
        )
    missing = {"passengers", "crew"} - set(complement)
    if missing:
        raise RuntimeError(
            f"{platform_id}'s nominal_complement omits {sorted(missing)}: the "
            "VSP rule scores passenger and crew denominators separately",
        )
    return (
        _berths(platform_id, "passengers", complement["passengers"]),
        _berths(platform_id, "crew", complement["crew"]),
    )


def declared_total(platform_id: str) -> int:
    """Agents the platform berths: passengers plus crew."""
    passengers, crew = declared_complement(platform_id)
    return passengers + crew


def require_declared_total(platform_id: str, num_agents: int) -> int:
    """The complement, refusing one that contradicts the hull's declaration.

    A run whose complement is not its hull's is not a run of that class, and
    any per-complement quantity read out of it -- attack rate, the 3% posting
    rule, zone occupancy -- belongs to no class at all.
    """
    declared = declared_total(platform_id)
    if int(num_agents) != declared:
        passengers, crew = declared_complement(platform_id)
        raise ValueError(
            f"{platform_id} berths {declared} agents "
            f"({passengers} passengers + {crew} crew), but the run states "
            f"{int(num_agents)}: a complement that is not the hull's makes "
            "every per-complement quantity classless",
        )
    return declared
