"""Read-only sentinel view over ``voyage_config`` itineraries.

Port-visit exposure windows are derived from the same config the ship engine
consumes (``engines.voyage_itinerary``), so the sentinel model and the
simulation can never disagree about when people were ashore. Nothing here
mutates config or agents.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from engines.voyage_itinerary import (
    DEFAULT_DAY_DEFAULTS,
    normalize_voyage_config,
)
from picard_framework.analysis._io import read_json

PORT_DAY_TYPE = "port_day"
EMBARKATION_DAY_TYPE = "embarkation"
DISEMBARKATION_DAY_TYPE = "disembarkation"
HOME_PORT_DAY_TYPES = (EMBARKATION_DAY_TYPE, DISEMBARKATION_DAY_TYPE)

# Ashore window that puts people on the pier at the home port: boarding on the
# embarkation day, walking off on the disembarkation day.
_HOME_PORT_WINDOW_KEYS = {
    EMBARKATION_DAY_TYPE: "embarkation_window_epochs",
    DISEMBARKATION_DAY_TYPE: "disembark_window_epochs",
}

_SLUG_RE = re.compile(r"[^a-z0-9]+")

# Hours ashore are known only when both ashore windows are configured; the
# exposure model must supply a prior for the rest (spec §6).
HOURS_FROM_WINDOWS = "windows"
HOURS_UNSPECIFIED = "unspecified"


@dataclass(frozen=True)
class PortCall:
    """One port visit with its exposure window."""

    port_id: str
    port_name: str
    region: str
    voyage_day: int
    arrival_epoch: int
    departure_epoch: int
    calendar_date: date | None
    pax_ashore_fraction: float
    crew_ashore_fraction: float
    mean_hours_ashore: float
    hours_ashore_source: str
    is_home_port: bool = False

    @property
    def carries_ashore_exposure(self) -> bool:
        """Whether this call can contribute person-hours ashore.

        A call with no ashore window or nobody on the pier has no denominator,
        so it can carry neither a fitted hazard nor a separability claim.
        """
        return (
            self.hours_ashore_source == HOURS_FROM_WINDOWS
            and self.mean_hours_ashore > 0.0
            and max(self.pax_ashore_fraction, self.crew_ashore_fraction) > 0.0
        )

    @property
    def visit_key(self) -> str:
        """Fleet-unique key for this visit (port + date, else port + day)."""
        stamp = self.calendar_date.isoformat() if self.calendar_date else f"d{self.voyage_day}"
        return f"{self.port_id}@{stamp}"


@dataclass(frozen=True)
class Voyage:
    """Sentinel view of a single voyage."""

    voyage_id: str
    ship_id: str
    platform_class: str
    embarkation_date: date | None
    n_passengers: int
    n_crew: int
    port_calls: tuple[PortCall, ...]
    total_epochs: int
    epoch_duration_hours: float
    observation_end_epoch: int

    @property
    def epochs_per_day(self) -> int:
        """Epochs in one voyage day."""
        return epochs_per_day_for(self.epoch_duration_hours)

    def port_call(self, port_id: str) -> PortCall | None:
        """First visit to ``port_id``, or None."""
        for call in self.port_calls:
            if call.port_id == port_id:
                return call
        return None

    def port_calls_for(self, port_id: str) -> tuple[PortCall, ...]:
        """Every visit to ``port_id`` in itinerary order.

        The home port is called twice (embarkation and disembarkation) and a
        repositioning itinerary may repeat a port, so ashore hours have to be
        checked against the sum of the visits rather than the first one.
        """
        return tuple(call for call in self.port_calls if call.port_id == port_id)

    @property
    def port_ids(self) -> tuple[str, ...]:
        """Distinct port ids in itinerary order."""
        seen: list[str] = []
        for call in self.port_calls:
            if call.port_id not in seen:
                seen.append(call.port_id)
        return tuple(seen)


def slugify_port(name: str) -> str:
    """Fallback port id from a free-text port name."""
    slug = _SLUG_RE.sub("_", name.strip().lower()).strip("_")
    return slug or "unknown_port"


def epochs_per_day_for(epoch_duration_hours: float) -> int:
    """Epochs per day for an epoch duration, matching ``resolve_epoch_state``."""
    hours = float(epoch_duration_hours or 1.0)
    if hours <= 0:
        hours = 1.0
    return max(1, int(round(24.0 / hours)))


def _parse_date(raw: Any) -> date | None:
    if raw in (None, ""):
        return None
    return date.fromisoformat(str(raw))


def _window_bounds(raw: Any) -> tuple[int, int] | None:
    if not isinstance(raw, (list, tuple)) or len(raw) < 2:
        return None
    lo, hi = int(raw[0]), int(raw[1])
    return (lo, hi) if lo <= hi else (hi, lo)


def _ashore_hours(
    disembark: tuple[int, int] | None,
    reembark: tuple[int, int] | None,
    hours_per_epoch: float,
) -> tuple[float, str]:
    """Mean hours ashore from window midpoints (0.0 when windows are absent)."""
    if disembark is None or reembark is None:
        return 0.0, HOURS_UNSPECIFIED
    d_mid = (disembark[0] + disembark[1]) / 2.0
    r_mid = (reembark[0] + reembark[1]) / 2.0
    return max(0.0, (r_mid - d_mid) * hours_per_epoch), HOURS_FROM_WINDOWS


def _pax_ashore_fraction(day: dict[str, Any], defaults: dict[str, Any]) -> float:
    if "disembark_fraction" in day:
        return float(day.get("disembark_fraction") or 0.0)
    onboard = float(
        defaults.get(
            "onboard_passenger_fraction",
            DEFAULT_DAY_DEFAULTS[PORT_DAY_TYPE]["onboard_passenger_fraction"],
        ),
    )
    return max(0.0, 1.0 - onboard)


def _calendar_date(
    day: dict[str, Any],
    voyage_day: int,
    embark_date: date | None,
) -> date | None:
    """Explicit ``calendar_date``, else the date implied by embarkation."""
    cal_date = _parse_date(day.get("calendar_date"))
    if cal_date is None and embark_date is not None:
        cal_date = embark_date + timedelta(days=voyage_day - 1)
    return cal_date


def _home_port_ashore_hours(
    day_type: str,
    window: tuple[int, int] | None,
    *,
    per_day: int,
    hours: float,
) -> tuple[float, str]:
    """Mean hours on the pier at the home port for one boundary day.

    Embarkation counts the hours before boarding closes; disembarkation counts
    the hours from walking off until the voyage day ends.
    """
    if window is None:
        return 0.0, HOURS_UNSPECIFIED
    if day_type == EMBARKATION_DAY_TYPE:
        return _ashore_hours((0, 0), window, hours)
    return _ashore_hours(window, (per_day - 1, per_day - 1), hours)


def _home_port_ashore_fraction(day_type: str, day_defaults: dict[str, Any]) -> float:
    """Passenger fraction on the pier, from the day type's onboard fraction."""
    onboard = float(
        day_defaults.get(
            "onboard_passenger_fraction",
            DEFAULT_DAY_DEFAULTS[day_type]["onboard_passenger_fraction"],
        ),
    )
    return min(1.0, max(0.0, 1.0 - onboard))


def _home_port_call_from_day(
    day: dict[str, Any],
    *,
    per_day: int,
    hours: float,
    day_defaults: dict[str, Any],
    embark_date: date | None,
    total_epochs: int,
) -> PortCall:
    """An embarkation or disembarkation day as a home-port call.

    The voyage starts and ends at the pier, so the home port carries real
    ashore hours and has to be a port the observation bundle can name. The
    ashore window is the whole voyage day: the ship is alongside for all of it,
    and the incubation weighting decides which of those epochs can explain an
    onset.
    """
    day_type = str(day.get("type", ""))
    voyage_day = int(day.get("day", 1))
    day_start = (voyage_day - 1) * per_day + 1
    day_end = day_start + per_day - 1
    if total_epochs > 0:
        day_end = min(day_end, max(day_start, total_epochs))
    window = _window_bounds(day.get(_HOME_PORT_WINDOW_KEYS[day_type]))
    ashore_fraction = _home_port_ashore_fraction(day_type, day_defaults)
    mean_hours, source = _home_port_ashore_hours(
        day_type, window, per_day=per_day, hours=hours,
    )
    if ashore_fraction <= 0.0:
        mean_hours, source = 0.0, HOURS_UNSPECIFIED
    port_name = str(day.get("port") or "")
    return PortCall(
        port_id=str(day.get("port_id") or slugify_port(port_name)),
        port_name=port_name,
        region=str(day.get("region") or "unknown"),
        voyage_day=voyage_day,
        arrival_epoch=day_start,
        departure_epoch=day_end,
        calendar_date=_calendar_date(day, voyage_day, embark_date),
        pax_ashore_fraction=ashore_fraction,
        crew_ashore_fraction=float(day.get("crew_shore_leave_fraction") or 0.0),
        mean_hours_ashore=mean_hours,
        hours_ashore_source=source,
        is_home_port=True,
    )


def _port_call_from_day(
    day: dict[str, Any],
    *,
    per_day: int,
    hours: float,
    day_defaults: dict[str, Any],
    embark_date: date | None,
) -> PortCall:
    """One ``port_day`` entry as a ``PortCall``, dated off embarkation if needed."""
    voyage_day = int(day.get("day", 1))
    day_start = (voyage_day - 1) * per_day + 1
    disembark = _window_bounds(day.get("disembark_window_epochs"))
    reembark = _window_bounds(day.get("reembark_window_epochs"))
    mean_hours, source = _ashore_hours(disembark, reembark, hours)
    port_name = str(day.get("port") or "")
    return PortCall(
        port_id=str(day.get("port_id") or slugify_port(port_name)),
        port_name=port_name,
        region=str(day.get("region") or "unknown"),
        voyage_day=voyage_day,
        arrival_epoch=day_start + (disembark[0] if disembark else 0),
        departure_epoch=day_start + (reembark[1] if reembark else per_day - 1),
        calendar_date=_calendar_date(day, voyage_day, embark_date),
        pax_ashore_fraction=_pax_ashore_fraction(day, day_defaults),
        crew_ashore_fraction=float(day.get("crew_shore_leave_fraction") or 0.0),
        mean_hours_ashore=mean_hours,
        hours_ashore_source=source,
    )


def port_calls_from_config(
    config: dict[str, Any] | None,
    *,
    include_home_port: bool = True,
) -> tuple[PortCall, ...]:
    """Derive port calls from a (possibly raw) voyage config.

    ``port_day`` entries are shore excursions; the embarkation and
    disembarkation days are the home port, which is a port call too — the
    voyage begins and ends on that pier, so the ashore hours the ship engine
    records there have to resolve to a port the exposure model knows. Pass
    ``include_home_port=False`` for the excursion-only view.
    """
    cfg = normalize_voyage_config(config or {})
    voyage = cfg.get("voyage") or {}
    hours = float(voyage.get("epoch_duration_hours", 1) or 1)
    per_day = epochs_per_day_for(hours)
    defaults = voyage.get("defaults") or {}
    embark_date = _parse_date(voyage.get("embarkation_date"))
    total_epochs = int(voyage.get("total_epochs", 0) or 0)

    calls: list[PortCall] = []
    for day in voyage.get("itinerary") or []:
        day_type = str(day.get("type", ""))
        if day_type == PORT_DAY_TYPE:
            calls.append(
                _port_call_from_day(
                    day,
                    per_day=per_day,
                    hours=hours,
                    day_defaults=defaults.get(PORT_DAY_TYPE) or {},
                    embark_date=embark_date,
                ),
            )
        elif day_type in HOME_PORT_DAY_TYPES and include_home_port:
            calls.append(
                _home_port_call_from_day(
                    day,
                    per_day=per_day,
                    hours=hours,
                    day_defaults=defaults.get(day_type) or {},
                    embark_date=embark_date,
                    total_epochs=total_epochs,
                ),
            )
    return tuple(sorted(calls, key=lambda c: (c.voyage_day, c.arrival_epoch)))


def voyage_from_config(
    config: dict[str, Any] | None,
    *,
    voyage_id: str,
    ship_id: str,
    n_passengers: int = 0,
    n_crew: int = 0,
    platform_class: str | None = None,
    observation_end_epoch: int | None = None,
) -> Voyage:
    """Build the sentinel ``Voyage`` view from a voyage config document."""
    cfg = normalize_voyage_config(config or {})
    voyage = cfg.get("voyage") or {}
    total_epochs = int(voyage.get("total_epochs", 0) or 0)
    calls = port_calls_from_config(cfg)
    if total_epochs <= 0 and calls:
        total_epochs = max(c.departure_epoch for c in calls)
    end_epoch = int(observation_end_epoch or total_epochs)
    excursions = [c for c in calls if not c.is_home_port]
    if excursions and end_epoch < max(c.departure_epoch for c in excursions):
        raise ValueError(
            "observation_end_epoch precedes the last port departure; "
            "censoring would be misattributed",
        )
    return Voyage(
        voyage_id=voyage_id,
        ship_id=ship_id,
        platform_class=str(platform_class or cfg.get("platform_class") or "unknown"),
        embarkation_date=_parse_date(voyage.get("embarkation_date")),
        n_passengers=int(n_passengers),
        n_crew=int(n_crew),
        port_calls=calls,
        total_epochs=total_epochs,
        epoch_duration_hours=float(voyage.get("epoch_duration_hours", 1) or 1),
        observation_end_epoch=end_epoch,
    )


def load_voyage(
    path: str,
    *,
    voyage_id: str,
    ship_id: str,
    n_passengers: int = 0,
    n_crew: int = 0,
    platform_class: str | None = None,
    observation_end_epoch: int | None = None,
) -> Voyage:
    """Load a voyage config from disk and return its sentinel view."""
    raw = read_json(path)
    if not isinstance(raw, dict):
        raise ValueError(f"voyage_config must be an object: {path}")
    return voyage_from_config(
        raw,
        voyage_id=voyage_id,
        ship_id=ship_id,
        n_passengers=n_passengers,
        n_crew=n_crew,
        platform_class=platform_class,
        observation_end_epoch=observation_end_epoch,
    )


def censoring_epochs_after(voyage: Voyage, call: PortCall) -> int:
    """Observation epochs remaining after a port call departs.

    Cases incubating past ``observation_end_epoch`` are never seen; late ports
    are censored harder than early ones (spec §4).
    """
    return max(0, voyage.observation_end_epoch - call.departure_epoch)
