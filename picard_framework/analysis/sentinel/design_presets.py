"""Regional fleet geometries -> ship x port x week visit tables.

The separability diagnostic needs *candidate designs*, and a candidate design is
a fleet geometry: a handful of itinerary rotations, how many ships fly each, how
their sail days are staggered across the calendar, and how much ashore exposure a
call generates. Those live in ``data/separability_presets.json`` rather than in a
function body so a reviewer can see and change the geometry being compared
without touching the diagnostic, and so the numbers behind a published
Alaska-vs-Caribbean claim are a committed artefact.

Expansion is deterministic. Ship ``i`` on a rotation is placed by index
arithmetic, not sampling:

- rotation: ``i % len(pattern)`` over a pattern that repeats each rotation
  ``n_ships_share`` times,
- sail-day offset: ``(i // len(pattern)) % sail_day_stagger`` days,
- call day of cycle ``c``: ``offset + c * itinerary_days + call_day``, dropped
  once it passes the horizon,
- port of the ``j``-th call: ``pool[(j + i * port_step + c * cycle_shift) %
  len(pool)]``, so ``port_step = 0`` means every ship on the rotation calls at the
  same port on the same cycle day (total itinerary overlap) and a positive step
  spreads the fleet across the pool in the same week (partial overlap).

The only stochastic element is the per-call ashore person-hours jitter, drawn
from a seeded generator in a fixed ship/cycle/call order, so a preset expands to
the same table every time.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from importlib import resources
from typing import Any, Mapping, Sequence

import numpy as np

from picard_framework.analysis.sentinel.visit_table import PortVisit
from simulation_utils.paths import validated_open

_PACKAGE = "picard_framework.analysis.sentinel"
_PRESET_FILE = "separability_presets.json"
DAYS_PER_WEEK = 7

# Overridable geometry knobs. Restricted on purpose: a sweep should vary the
# design, not silently redefine what a preset is.
OVERRIDABLE = frozenset(
    {
        "n_weeks",
        "n_ships",
        "sail_day_stagger",
        "seed",
        "hours_ashore_per_call",
        "passengers_ashore_per_call",
        "hours_jitter_fraction",
    },
)
ROTATION_OVERRIDABLE = frozenset({"port_step", "cycle_shift", "call_days"})


@dataclass(frozen=True)
class Rotation:
    """One itinerary template flown by part of the fleet."""

    name: str
    itinerary_days: int
    call_days: tuple[int, ...]
    port_pool: tuple[int, int]
    port_step: int
    cycle_shift: int
    n_ships_share: int


@dataclass(frozen=True)
class FleetGeometry:
    """A candidate regional deployment: ports, ships, rotations, exposure."""

    name: str
    label: str
    n_weeks: int
    port_prefix: str
    n_ports: int
    n_ships: int
    sail_day_stagger: int
    passengers_ashore_per_call: float
    hours_ashore_per_call: float
    hours_jitter_fraction: float
    seed: int
    rotations: tuple[Rotation, ...]
    port_exposure_scale: Mapping[int, float]

    @property
    def ports(self) -> tuple[str, ...]:
        """Stable port ids for the region."""
        return tuple(f"{self.port_prefix}{i:03d}" for i in range(self.n_ports))


def _load_document() -> dict[str, Any]:
    with resources.as_file(resources.files(_PACKAGE) / "data") as data_dir:
        root = str(data_dir)
        with validated_open(
            os.path.join(root, _PRESET_FILE),
            allowed_roots=(root,),
            encoding="utf-8",
        ) as fh:
            payload = json.load(fh)
    if not isinstance(payload, dict) or not isinstance(payload.get("presets"), dict):
        raise ValueError(f"{_PRESET_FILE} must hold a 'presets' object")
    return payload


def preset_names() -> tuple[str, ...]:
    """Names of the bundled geometries, in file order."""
    return tuple(_load_document()["presets"].keys())


def _rotation_from_dict(raw: Mapping[str, Any], overrides: Mapping[str, Any]) -> Rotation:
    merged = dict(raw)
    merged.update({k: v for k, v in overrides.items() if k in ROTATION_OVERRIDABLE})
    pool = [int(x) for x in merged["port_pool"]]
    if len(pool) != 2 or pool[0] >= pool[1]:
        raise ValueError(f"port_pool must be [start, end) with start < end: {pool}")
    return Rotation(
        name=str(merged["name"]),
        itinerary_days=int(merged["itinerary_days"]),
        call_days=tuple(int(d) for d in merged["call_days"]),
        port_pool=(pool[0], pool[1]),
        port_step=int(merged.get("port_step") or 0),
        cycle_shift=int(merged.get("cycle_shift") or 0),
        n_ships_share=int(merged.get("n_ships_share") or 1),
    )


def geometry(name: str, overrides: Mapping[str, Any] | None = None) -> FleetGeometry:
    """Load one preset, applying an allow-listed set of sweep overrides."""
    presets = _load_document()["presets"]
    if name not in presets:
        raise KeyError(f"unknown separability preset {name!r}; have {sorted(presets)}")
    over = dict(overrides or {})
    unknown = sorted(set(over) - OVERRIDABLE - ROTATION_OVERRIDABLE)
    if unknown:
        raise ValueError(f"cannot override {unknown} on a geometry preset")
    raw = dict(presets[name])
    raw.update({k: v for k, v in over.items() if k in OVERRIDABLE})
    scale = {
        int(k): float(v) for k, v in (raw.get("port_exposure_scale") or {}).items()
    }
    geo = FleetGeometry(
        name=name,
        label=str(raw.get("label") or name),
        n_weeks=int(raw["n_weeks"]),
        port_prefix=str(raw["port_prefix"]),
        n_ports=int(raw["n_ports"]),
        n_ships=int(raw["n_ships"]),
        sail_day_stagger=max(1, int(raw["sail_day_stagger"])),
        passengers_ashore_per_call=float(raw["passengers_ashore_per_call"]),
        hours_ashore_per_call=float(raw["hours_ashore_per_call"]),
        hours_jitter_fraction=float(raw.get("hours_jitter_fraction") or 0.0),
        seed=int(raw["seed"]),
        rotations=tuple(_rotation_from_dict(r, over) for r in raw["rotations"]),
        port_exposure_scale=scale,
    )
    _validate(geo)
    return geo


def _validate(geo: FleetGeometry) -> None:
    if geo.n_ports < 1 or geo.n_ships < 1 or geo.n_weeks < 1:
        raise ValueError(f"{geo.name}: ports, ships and weeks must all be positive")
    for rotation in geo.rotations:
        if rotation.port_pool[1] > geo.n_ports:
            raise ValueError(
                f"{geo.name}/{rotation.name}: port_pool exceeds n_ports",
            )
        if rotation.itinerary_days < 1:
            raise ValueError(f"{geo.name}/{rotation.name}: itinerary_days must be >= 1")
        if any(d < 0 or d >= rotation.itinerary_days for d in rotation.call_days):
            raise ValueError(
                f"{geo.name}/{rotation.name}: call_days must fall inside the cycle",
            )


def rotation_pattern(geo: FleetGeometry) -> tuple[Rotation, ...]:
    """Ship-to-rotation assignment pattern, repeated over the fleet."""
    pattern: list[Rotation] = []
    for rotation in geo.rotations:
        pattern.extend([rotation] * max(1, rotation.n_ships_share))
    return tuple(pattern)


def _ship_visits(
    geo: FleetGeometry,
    ship_index: int,
    rotation: Rotation,
    sail_offset: int,
    rng: np.random.Generator,
) -> list[PortVisit]:
    ports = geo.ports
    pool = list(range(*rotation.port_pool))
    horizon_days = geo.n_weeks * DAYS_PER_WEEK
    base_hours = geo.passengers_ashore_per_call * geo.hours_ashore_per_call
    out: list[PortVisit] = []
    cycle = 0
    while sail_offset + cycle * rotation.itinerary_days < horizon_days:
        start = sail_offset + cycle * rotation.itinerary_days
        for j, call_day in enumerate(rotation.call_days):
            day = start + call_day
            jitter = 1.0 + geo.hours_jitter_fraction * (2.0 * rng.random() - 1.0)
            if day >= horizon_days:
                continue
            offset = j + ship_index * rotation.port_step + cycle * rotation.cycle_shift
            port_index = pool[offset % len(pool)]
            hours = base_hours * jitter * geo.port_exposure_scale.get(port_index, 1.0)
            out.append(
                PortVisit(
                    ship_id=f"SHIP{ship_index:03d}",
                    port_id=ports[port_index],
                    week=f"W{day // DAYS_PER_WEEK:02d}",
                    person_hours_ashore=hours,
                ),
            )
        cycle += 1
    return out


def expand_geometry(geo: FleetGeometry) -> tuple[PortVisit, ...]:
    """Expand a geometry into its deterministic ship x port x week visit table.

    The jitter draw happens for every scheduled call, including calls dropped at
    the horizon, so shortening the horizon cannot change the exposure of the
    calls that remain.
    """
    pattern = rotation_pattern(geo)
    rng = np.random.default_rng(geo.seed)
    visits: list[PortVisit] = []
    for ship_index in range(geo.n_ships):
        rotation = pattern[ship_index % len(pattern)]
        sail_offset = (ship_index // len(pattern)) % geo.sail_day_stagger
        visits.extend(_ship_visits(geo, ship_index, rotation, sail_offset, rng))
    if not visits:
        raise ValueError(f"{geo.name}: geometry produced no port visits")
    return tuple(visits)


def expand_preset(
    name: str,
    overrides: Mapping[str, Any] | None = None,
) -> tuple[PortVisit, ...]:
    """Load a preset and expand it into a visit table."""
    return expand_geometry(geometry(name, overrides))


def calls_per_ship_week(visits: Sequence[PortVisit]) -> float:
    """Mean port calls per ship-week, the density figure the presets quote."""
    ships = {v.ship_id for v in visits}
    weeks = {v.week for v in visits}
    if not ships or not weeks:
        return 0.0
    return len(visits) / (len(ships) * len(weeks))
