"""Hazard source model: emitters, standing/dynamic fields, and the
penetration-source adapter seam (``docs/ship_functions/ship_function_capacity_spec.md``
§8 companion; ENV-SOURCE-01).

A ``hazard_sources`` declaration block names *substances* (non-pathogen
profiles that ride the environmental reservoir machinery), *emitters*
(scheduled mass sources writing into ``env_contamination`` zone pools), and
*penetrations* (off-ship field couplings resolved into emitters by a named
adapter at load time).

Discipline, matching the modules it sits beside:

* Everything rides ``hazard_sources.enabled``: absent or disabled, nothing
  is parsed into the run, no substance profile registers, and every seeded
  voyage is bit-identical. Deposits themselves consume zero RNG draws — an
  armed model changes outcomes only through pool mass.
* Emitters write into ``env_contamination[substance_id][zone]`` — the same
  pools the scalar ``environmental_contamination`` arm reads — never beside
  them. Deposition happens once per epoch, before the reservoir growth and
  exposure pass, so pool semantics are identical to the standing arm.
* Declarations are transport-agnostic. A substance's pool is stepped through
  whichever transport is armed (native HVAC network or CONTAM) by
  ``ShipSimulation._transport_hazard_source_pools``; a substance may opt out
  with ``transport: "none"``.
* Every rate carries ``source`` + ``grade``; where no literature exists the
  declaration says so (``NULL-SOURCE``) rather than hiding the arm.
* Unit safety: rates are ``*_per_hour``, durations ``*_hours``, schedules
  resolve through ``SimClock`` — never ``*_epochs`` on a physical quantity.
* The dose ledger consumes pools as usual; substances carry
  ``dose_response: {model: exponential, k: 0.0}`` so the source arm is
  exercised end-to-end without inventing an effect arm (ENV-HAZARD-01's).

The penetration adapter contract is the seam an external plume solver feeds:
a resolver maps one ``PenetrationSpec`` to zero or more ``EmitterSpec``s at
model build. ``uniform_outdoor`` ships as the trivial analytic adapter — a
declared outdoor concentration rate times a declared penetration factor. A
QUIC (or other CFD) adapter would register under its own name and emit a
``series``-rate emitter per penetration zone read off the solver's output;
nothing downstream changes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from engines.sim_clock import SimClock
from engines.voyage_itinerary import deep_merge_dict

PLACEMENT_KINDS = frozenset({"point", "multipoint"})
FIELD_KINDS = frozenset({"standing", "dynamic"})
RATE_KINDS = frozenset({"constant", "series", "functional"})
FUNCTIONAL_FORMS = frozenset({"exponential_decay", "linear_ramp"})
TRANSPORT_MODES = frozenset({"armed", "none"})
OUTDOOR_FIELD_KINDS = frozenset({"uniform", "series"})

# Keys a substance may set on its environmental_contamination arm. ``enabled``
# and ``person_to_person`` are owned by the machinery (always on / always off)
# and are refused here so a substance can never become a shedding pathogen.
SUBSTANCE_ENV_KEYS = frozenset({
    "source_zones",
    "baseline_environmental_load",
    "base_emission_rate_per_day",
    "exposure_probability_per_day",
    "spore_decay_rate_per_day",
    "colonization_rate_per_day",
})
SUBSTANCE_ENV_FORBIDDEN = frozenset({"enabled", "person_to_person"})


def _require_mapping(raw: Any, what: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"hazard_sources: {what} must be a mapping")
    return raw


def _require_str(raw: Any, what: str) -> str:
    value = str(raw or "").strip()
    if not value:
        raise ValueError(f"hazard_sources: {what} requires a non-empty string")
    return value


def _require_number(raw: Any, what: str, *, minimum: float = 0.0) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"hazard_sources: {what} must be a number") from None
    if not math.isfinite(value) or value < minimum:
        raise ValueError(
            f"hazard_sources: {what} must be finite and >= {minimum}"
        )
    return value


def _require_provenance(entry: Mapping[str, Any], what: str) -> None:
    """Every rate carries source+grade; NULL-SOURCE is the declared arm."""
    for key in ("source", "grade"):
        if not str(entry.get(key) or "").strip():
            raise ValueError(
                f"hazard_sources: {what} requires {key!r} "
                "(use source 'NULL-SOURCE' for declared arms)"
            )


def _require_zones(
    raw: Any, what: str, known_zones: frozenset[str],
) -> tuple[str, ...]:
    if not isinstance(raw, (list, tuple)) or not raw:
        raise ValueError(f"hazard_sources: {what} requires a non-empty zones list")
    zones = tuple(str(z) for z in raw)
    unknown = [z for z in zones if z not in known_zones]
    if unknown:
        raise ValueError(
            f"hazard_sources: {what} names unknown zones {sorted(unknown)}"
        )
    return zones


@dataclass(frozen=True)
class ScheduleWindow:
    """``introduction_epoch``-style onset plus an optional duration.

    ``start_epoch`` is the first epoch the source is live; ``duration_hours``
    bounds the window on a physical clock, so the last covered epoch may be
    partial (its deposit is scaled to the covered hours).
    """

    start_epoch: int = 0
    duration_hours: float | None = None

    def epoch_bounds(self, epoch: int, hours_per_epoch: float) -> tuple[float, float] | None:
        """Return (h_start, h_end) of this epoch inside the window, or None."""
        if epoch < self.start_epoch:
            return None
        h0 = (epoch - self.start_epoch) * hours_per_epoch
        h1 = h0 + hours_per_epoch
        if self.duration_hours is not None:
            if h0 >= self.duration_hours:
                return None
            h1 = min(h1, self.duration_hours)
        return (h0, h1)


def _parse_schedule(raw: Any, what: str) -> ScheduleWindow:
    if raw is None:
        return ScheduleWindow()
    block = _require_mapping(raw, f"{what}.schedule")
    start = int(block.get("start_epoch", block.get("introduction_epoch", 0)))
    if start < 0:
        raise ValueError(
            f"hazard_sources: {what}.schedule.start_epoch must be >= 0"
        )
    duration = block.get("duration_hours")
    window = ScheduleWindow(
        start_epoch=start,
        duration_hours=(
            _require_number(duration, f"{what}.schedule.duration_hours")
            if duration is not None
            else None
        ),
    )
    if window.duration_hours is not None and window.duration_hours <= 0.0:
        raise ValueError(
            f"hazard_sources: {what}.schedule.duration_hours must be > 0"
        )
    return window


@dataclass(frozen=True)
class EmissionRate:
    """An emitter's declared rate schedule in declared units.

    ``kind`` is one of ``constant`` (standing fields), ``series`` (a
    per-epoch rate table indexed from the schedule onset), or ``functional``
    (a closed form integrated over each epoch — nothing compounds by hand).
    ``mass_per_hour`` is the constant/initial/plateau rate;
    ``decay_rate_per_hour`` parameterises ``exponential_decay`` and
    ``ramp_up_hours`` parameterises ``linear_ramp``.
    """

    kind: str
    mass_per_hour: float = 0.0
    series_per_hour: tuple[float, ...] = ()
    functional_form: str = ""
    decay_rate_per_hour: float = 0.0
    ramp_up_hours: float = 0.0
    source: str = ""
    grade: str = ""

    def epoch_mass(
        self,
        h0: float,
        h1: float,
        epoch_offset: int,
    ) -> float:
        """Mass emitted between h0 and h1 hours after the source's onset."""
        if h1 <= h0:
            return 0.0
        if self.kind == "constant":
            return self.mass_per_hour * (h1 - h0)
        if self.kind == "series":
            if 0 <= epoch_offset < len(self.series_per_hour):
                return self.series_per_hour[epoch_offset] * (h1 - h0)
            return 0.0
        if self.functional_form == "exponential_decay":
            return self._exponential_decay_mass(h0, h1)
        return self._linear_ramp_mass(h0, h1)

    def _exponential_decay_mass(self, h0: float, h1: float) -> float:
        if self.decay_rate_per_hour <= 0.0:
            return self.mass_per_hour * (h1 - h0)
        return (self.mass_per_hour / self.decay_rate_per_hour) * (
            math.exp(-self.decay_rate_per_hour * h0)
            - math.exp(-self.decay_rate_per_hour * h1)
        )

    def _linear_ramp_mass(self, h0: float, h1: float) -> float:
        ramp = self.ramp_up_hours
        if ramp <= 0.0:
            return self.mass_per_hour * (h1 - h0)
        lo = min(h0, ramp)
        hi = min(h1, ramp)
        ramped = self.mass_per_hour * (hi * hi - lo * lo) / (2.0 * ramp)
        plateau = self.mass_per_hour * max(0.0, h1 - max(h0, ramp))
        return ramped + plateau


def _parse_rate(raw: Any, what: str) -> EmissionRate:
    block = _require_mapping(raw, f"{what}.rate")
    kind = _require_str(block.get("kind"), f"{what}.rate.kind")
    if kind not in RATE_KINDS:
        raise ValueError(
            f"hazard_sources: {what}.rate.kind must be one of "
            f"{sorted(RATE_KINDS)}"
        )
    _require_provenance(block, f"{what}.rate")
    series = tuple(
        _require_number(v, f"{what}.rate.series_per_hour[]")
        for v in (block.get("series_per_hour") or ())
    )
    if kind == "series" and not series:
        raise ValueError(
            f"hazard_sources: {what}.rate.series_per_hour must be non-empty"
        )
    form = str(block.get("functional_form") or "")
    if kind == "functional" and form not in FUNCTIONAL_FORMS:
        raise ValueError(
            f"hazard_sources: {what}.rate.functional_form must be one of "
            f"{sorted(FUNCTIONAL_FORMS)}"
        )
    return EmissionRate(
        kind=kind,
        mass_per_hour=_require_number(
            block.get("mass_per_hour", 0.0), f"{what}.rate.mass_per_hour",
        ),
        series_per_hour=series,
        functional_form=form,
        decay_rate_per_hour=_require_number(
            block.get("decay_rate_per_hour", 0.0),
            f"{what}.rate.decay_rate_per_hour",
        ),
        ramp_up_hours=_require_number(
            block.get("ramp_up_hours", 0.0), f"{what}.rate.ramp_up_hours",
        ),
        source=str(block["source"]),
        grade=str(block["grade"]),
    )


@dataclass(frozen=True)
class EmitterSpec:
    """One resolved mass source writing into zone pools each epoch.

    ``origin`` records how the emitter arrived: ``declared`` for a direct
    emitter entry, or ``penetration:<id>`` for one produced by an adapter.
    A ``multipoint`` emitter deposits its full declared rate into every
    listed zone (replicated point emitters — the same semantics the scalar
    arm gives each of its ``source_zones``).
    """

    emitter_id: str
    substance_id: str
    placement: str
    field: str
    zones: tuple[str, ...]
    schedule: ScheduleWindow
    rate: EmissionRate
    origin: str = "declared"

    def epoch_deposit(self, epoch: int, hours_per_epoch: float) -> float:
        bounds = self.schedule.epoch_bounds(epoch, hours_per_epoch)
        if bounds is None:
            return 0.0
        h0, h1 = bounds
        return self.rate.epoch_mass(h0, h1, epoch - self.schedule.start_epoch)


@dataclass(frozen=True)
class SubstanceSpec:
    """A non-pathogen hazard riding the environmental reservoir machinery.

    The spec becomes a pathogen-shaped profile fragment (``hazard_substance``
    marker set, ``person_to_person`` off, exponential dose-response with
    k = 0 — dose is recorded, never converts to infection) so the whole
    environmental arm — reservoirs, decay, dose ledger, transport — carries
    it unchanged.
    """

    substance_id: str
    transport: str
    source_zones: tuple[str, ...]
    environmental: dict[str, Any]
    parameters_provenance: str

    def profile_fragment(self) -> dict[str, Any]:
        """The pathogen-profiles entry this substance registers as."""
        ec: dict[str, Any] = {
            "enabled": True,
            "person_to_person": False,
            "source_zones": list(self.source_zones),
            "baseline_environmental_load": 0.0,
            "base_emission_rate_per_day": 1.0,
            "exposure_probability_per_day": 1.0,
            "spore_decay_rate_per_day": 0.0,
            "colonization_rate_per_day": 0.0,
        }
        ec.update(self.environmental)
        return {
            "pathogen_id": self.substance_id,
            "hazard_substance": True,
            "initial_infected": None,
            "environmental_contamination": ec,
            "dose_response": {"model": "exponential", "k": 0.0},
            "parameters_provenance": self.parameters_provenance,
        }


@dataclass(frozen=True)
class OutdoorField:
    """The off-ship concentration a penetration adapter is handed."""

    kind: str  # "uniform" | "series"
    concentration_per_hour: float = 0.0
    series_per_hour: tuple[float, ...] = ()


@dataclass(frozen=True)
class PenetrationSpec:
    """An off-ship field coupled to the ship through declared zone points.

    ``adapter`` names the resolver; ``outdoor_field`` is the external field
    handed to it; ``penetration_factor`` is the declared transmission
    multiplier from outdoor concentration to indoor emission rate.
    """

    penetration_id: str
    substance_id: str
    adapter: str
    zones: tuple[str, ...]
    penetration_factor: float
    outdoor_field: OutdoorField
    schedule: ScheduleWindow
    source: str
    grade: str


def _resolve_uniform_outdoor(pen: PenetrationSpec) -> EmitterSpec:
    """Trivial analytic adapter: outdoor rate x declared penetration factor.

    ``uniform`` fields become ``standing`` emitters, ``series`` fields become
    ``dynamic`` emitters replaying the declared concentration series times
    the factor. A QUIC-backed adapter would register beside this one and emit
    the same shape — a ``series`` emitter per penetration zone read off the
    solver's output table.
    """
    rate = EmissionRate(
        kind="constant" if pen.outdoor_field.kind == "uniform" else "series",
        mass_per_hour=pen.outdoor_field.concentration_per_hour
        * pen.penetration_factor,
        series_per_hour=tuple(
            v * pen.penetration_factor
            for v in pen.outdoor_field.series_per_hour
        ),
        source=pen.source,
        grade=pen.grade,
    )
    return EmitterSpec(
        emitter_id=pen.penetration_id,
        substance_id=pen.substance_id,
        placement="multipoint",
        field="standing" if pen.outdoor_field.kind == "uniform" else "dynamic",
        zones=pen.zones,
        schedule=pen.schedule,
        rate=rate,
        origin=f"penetration:{pen.penetration_id}",
    )


# Penetration adapter registry: name -> resolver mapping one PenetrationSpec
# to one EmitterSpec. An external solver (QUIC etc.) registers a resolver
# returning a "series" emitter per penetration zone; the rest of the engine
# never sees the difference.
PENETRATION_ADAPTERS: dict[str, Callable[[PenetrationSpec], EmitterSpec]] = {
    "uniform_outdoor": _resolve_uniform_outdoor,
}


def _parse_substance(
    entry: Any, index: int, known_zones: frozenset[str],
) -> SubstanceSpec:
    what = f"hazard_sources.substances[{index}]"
    block = _require_mapping(entry, what)
    substance_id = _require_str(block.get("substance_id"), f"{what}.substance_id")
    transport = str(block.get("transport", "armed"))
    if transport not in TRANSPORT_MODES:
        raise ValueError(
            f"hazard_sources: {what}.transport must be one of "
            f"{sorted(TRANSPORT_MODES)}"
        )
    provenance = _require_str(
        block.get("parameters_provenance"), f"{what}.parameters_provenance",
    )
    env = _require_mapping(
        block.get("environmental_contamination") or {},
        f"{what}.environmental_contamination",
    )
    forbidden = sorted(set(env) & SUBSTANCE_ENV_FORBIDDEN)
    if forbidden:
        raise ValueError(
            f"hazard_sources: {what}.environmental_contamination must not set "
            f"{forbidden} — the source arm owns them"
        )
    unknown = sorted(set(env) - SUBSTANCE_ENV_KEYS)
    if unknown:
        raise ValueError(
            f"hazard_sources: {what}.environmental_contamination unknown keys "
            f"{unknown} (allowed: {sorted(SUBSTANCE_ENV_KEYS)})"
        )
    zones = tuple(str(z) for z in (env.get("source_zones") or ()))
    for z in zones:
        if z not in known_zones:
            raise ValueError(
                f"hazard_sources: {what}.environmental_contamination."
                f"source_zones names unknown zone {z!r}"
            )
    return SubstanceSpec(
        substance_id=substance_id,
        transport=transport,
        source_zones=zones,
        environmental={k: v for k, v in env.items() if k != "source_zones"},
        parameters_provenance=provenance,
    )


def _parse_emitter(
    entry: Any,
    index: int,
    known_zones: frozenset[str],
    known_substances: frozenset[str],
) -> EmitterSpec:
    what = f"hazard_sources.emitters[{index}]"
    block = _require_mapping(entry, what)
    emitter_id = _require_str(block.get("emitter_id"), f"{what}.emitter_id")
    substance_id = _require_str(
        block.get("substance_id"), f"{what}.substance_id",
    )
    if substance_id not in known_substances:
        raise ValueError(
            f"hazard_sources: {what}.substance_id {substance_id!r} names no "
            "declared substance or pathogen profile"
        )
    kind_block = _require_mapping(block.get("kind") or {}, f"{what}.kind")
    placement = str(kind_block.get("placement") or "")
    field_kind = str(kind_block.get("field") or "")
    if placement not in PLACEMENT_KINDS:
        raise ValueError(
            f"hazard_sources: {what}.kind.placement must be one of "
            f"{sorted(PLACEMENT_KINDS)}"
        )
    if field_kind not in FIELD_KINDS:
        raise ValueError(
            f"hazard_sources: {what}.kind.field must be one of "
            f"{sorted(FIELD_KINDS)}"
        )
    zones = _require_zones(block.get("zones"), what, known_zones)
    if placement == "point" and len(zones) != 1:
        raise ValueError(
            f"hazard_sources: {what} is 'point' but declares "
            f"{len(zones)} zones"
        )
    rate = _parse_rate(block.get("rate"), what)
    if field_kind == "standing" and rate.kind != "constant":
        raise ValueError(
            f"hazard_sources: {what} is 'standing' — rate.kind must be "
            "'constant'"
        )
    if field_kind == "dynamic" and rate.kind == "constant":
        raise ValueError(
            f"hazard_sources: {what} is 'dynamic' — rate.kind must be "
            "'series' or 'functional'"
        )
    return EmitterSpec(
        emitter_id=emitter_id,
        substance_id=substance_id,
        placement=placement,
        field=field_kind,
        zones=zones,
        schedule=_parse_schedule(block.get("schedule"), what),
        rate=rate,
    )


def _parse_penetration(
    entry: Any,
    index: int,
    known_zones: frozenset[str],
    known_substances: frozenset[str],
) -> PenetrationSpec:
    what = f"hazard_sources.penetrations[{index}]"
    block = _require_mapping(entry, what)
    penetration_id = _require_str(
        block.get("penetration_id"), f"{what}.penetration_id",
    )
    substance_id = _require_str(
        block.get("substance_id"), f"{what}.substance_id",
    )
    if substance_id not in known_substances:
        raise ValueError(
            f"hazard_sources: {what}.substance_id {substance_id!r} names no "
            "declared substance or pathogen profile"
        )
    adapter = _require_str(block.get("adapter"), f"{what}.adapter")
    if adapter not in PENETRATION_ADAPTERS:
        raise ValueError(
            f"hazard_sources: {what}.adapter {adapter!r} is not a registered "
            f"penetration adapter (have {sorted(PENETRATION_ADAPTERS)})"
        )
    _require_provenance(block, what)
    field_block = _require_mapping(
        block.get("outdoor_field"), f"{what}.outdoor_field",
    )
    field_kind = _require_str(
        field_block.get("kind"), f"{what}.outdoor_field.kind",
    )
    if field_kind not in OUTDOOR_FIELD_KINDS:
        raise ValueError(
            f"hazard_sources: {what}.outdoor_field.kind must be one of "
            f"{sorted(OUTDOOR_FIELD_KINDS)}"
        )
    series = tuple(
        _require_number(v, f"{what}.outdoor_field.series_per_hour[]")
        for v in (field_block.get("series_per_hour") or ())
    )
    if field_kind == "series" and not series:
        raise ValueError(
            f"hazard_sources: {what}.outdoor_field.series_per_hour must be "
            "non-empty"
        )
    return PenetrationSpec(
        penetration_id=penetration_id,
        substance_id=substance_id,
        adapter=adapter,
        zones=_require_zones(block.get("zones"), what, known_zones),
        penetration_factor=_require_number(
            block.get("penetration_factor"), f"{what}.penetration_factor",
        ),
        outdoor_field=OutdoorField(
            kind=field_kind,
            concentration_per_hour=_require_number(
                field_block.get("concentration_per_hour", 0.0),
                f"{what}.outdoor_field.concentration_per_hour",
            ),
            series_per_hour=series,
        ),
        schedule=_parse_schedule(block.get("schedule"), what),
        source=str(block["source"]),
        grade=str(block["grade"]),
    )


def merge_hazard_source_blocks(*blocks: Any) -> dict[str, Any]:
    """Merge declaration blocks (profiles file < voyage < cfg) by id.

    ``emitters``/``substances``/``penetrations`` lists merge by their id key
    (later layers override same-id entries key-by-key); every other key
    deep-merges. ``enabled`` therefore resolves to the last layer that
    declares it — a run can arm a platform's disabled example block from
    ``config_overrides`` alone.
    """
    merged: dict[str, Any] = {}
    for block in blocks:
        if not isinstance(block, dict) or not block:
            continue
        for key, value in block.items():
            if key in ("emitters", "substances", "penetrations") and isinstance(
                value, list,
            ):
                merged[key] = _merge_named_entries(merged.get(key), value, key)
            else:
                merged[key] = deep_merge_dict(
                    {key: merged.get(key)}, {key: value},
                )[key]
    return merged


def _merge_named_entries(
    base: Any, overlay: list[Any], key: str,
) -> list[Any]:
    id_key = {
        "emitters": "emitter_id",
        "substances": "substance_id",
        "penetrations": "penetration_id",
    }[key]
    out: list[Any] = list(base or [])
    index = {
        str(e.get(id_key) or ""): i
        for i, e in enumerate(out)
        if isinstance(e, dict)
    }
    for entry in overlay:
        if not isinstance(entry, dict):
            out.append(entry)
            continue
        entry_id = str(entry.get(id_key) or "")
        if entry_id and entry_id in index:
            out[index[entry_id]] = deep_merge_dict(out[index[entry_id]], entry)
        else:
            index[entry_id] = len(out)
            out.append(dict(entry))
    return out


@dataclass
class HazardSourceModel:
    """The resolved source model: substances, emitters, zone coverage.

    ``epoch_deposits`` recomputes every armed emitter's output for the epoch
    — declared time-series or functional schedules, never hand-compounded —
    into ``{substance_id: {zone: mass}}`` for ``env_contamination``.
    """

    clock: SimClock
    substances: dict[str, SubstanceSpec] = field(default_factory=dict)
    emitters: tuple[EmitterSpec, ...] = ()
    _emitter_zones: dict[str, frozenset[str]] = field(default_factory=dict)

    def is_substance(self, pid: str) -> bool:
        return pid in self.substances

    @property
    def substance_ids(self) -> frozenset[str]:
        return frozenset(self.substances)

    def emitter_zones_for(self, pid: str) -> frozenset[str]:
        return self._emitter_zones.get(pid, frozenset())

    def transport_armed(self, pid: str) -> bool:
        spec = self.substances.get(pid)
        return spec is not None and spec.transport == "armed"

    def profile_fragments(self) -> dict[str, dict[str, Any]]:
        return {
            sid: spec.profile_fragment()
            for sid, spec in self.substances.items()
        }

    def epoch_deposits(self, epoch: int) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}
        for emitter in self.emitters:
            mass = emitter.epoch_deposit(epoch, self.clock.hours_per_epoch)
            if mass <= 0.0:
                continue
            pool = out.setdefault(emitter.substance_id, {})
            for zone in emitter.zones:
                pool[zone] = pool.get(zone, 0.0) + mass
        return out


def _entry_disabled(entry: Any) -> bool:
    """Per-entry kill-switch: an overriding layer's ``enabled: false`` skips
    the entry entirely."""
    return isinstance(entry, dict) and entry.get("enabled") is False


def _parse_substance_list(
    raw: dict[str, Any],
    known_zones: frozenset[str],
    known_profile_ids: frozenset[str] | set[str],
) -> dict[str, SubstanceSpec]:
    substances: dict[str, SubstanceSpec] = {}
    for index, entry in enumerate(raw.get("substances") or []):
        if _entry_disabled(entry):
            continue
        spec = _parse_substance(entry, index, known_zones)
        if spec.substance_id in substances or spec.substance_id in known_profile_ids:
            raise ValueError(
                f"hazard_sources: duplicate substance_id "
                f"{spec.substance_id!r}"
            )
        substances[spec.substance_id] = spec
    return substances


def _parse_emitter_list(
    raw: dict[str, Any],
    known_zones: frozenset[str],
    known_ids: frozenset[str],
) -> list[EmitterSpec]:
    """Declared emitters plus each penetration's adapter-resolved emitter;
    both share one emitter_id namespace."""
    emitters: list[EmitterSpec] = []
    seen_ids: set[str] = set()
    for index, entry in enumerate(raw.get("emitters") or []):
        if _entry_disabled(entry):
            continue
        emitters.append(_parse_emitter(entry, index, known_zones, known_ids))
    for index, entry in enumerate(raw.get("penetrations") or []):
        if _entry_disabled(entry):
            continue
        pen = _parse_penetration(entry, index, known_zones, known_ids)
        emitters.append(PENETRATION_ADAPTERS[pen.adapter](pen))
    for emitter in emitters:
        if emitter.emitter_id in seen_ids:
            raise ValueError(
                f"hazard_sources: duplicate emitter_id {emitter.emitter_id!r}"
            )
        seen_ids.add(emitter.emitter_id)
    return emitters


def _emitter_zone_index(
    emitters: list[EmitterSpec],
) -> dict[str, frozenset[str]]:
    emitter_zones: dict[str, frozenset[str]] = {}
    for emitter in emitters:
        emitter_zones[emitter.substance_id] = (
            emitter_zones.get(emitter.substance_id, frozenset())
            | frozenset(emitter.zones)
        )
    return emitter_zones


def parse_hazard_sources(
    block: Any,
    *,
    zone_names: list[str] | tuple[str, ...] | frozenset[str],
    known_profile_ids: frozenset[str] | set[str],
    clock: SimClock,
) -> HazardSourceModel | None:
    """Validate a merged ``hazard_sources`` block into a model, or None.

    Structure and referential integrity are checked whenever a block is
    present — a malformed declaration is a load error, armed or not — but
    only an ``enabled: true`` block builds the model, so the identity arm
    never touches the run.
    """
    if block is None:
        return None
    raw = _require_mapping(block, "hazard_sources")
    known_zones = frozenset(zone_names)
    substances = _parse_substance_list(raw, known_zones, known_profile_ids)
    known_ids = frozenset(known_profile_ids) | frozenset(substances)
    emitters = _parse_emitter_list(raw, known_zones, known_ids)
    if not raw.get("enabled", False):
        return None
    return HazardSourceModel(
        clock=clock,
        substances=substances,
        emitters=tuple(emitters),
        _emitter_zones=_emitter_zone_index(emitters),
    )
