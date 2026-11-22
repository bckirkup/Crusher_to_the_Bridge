"""Calendar-driven protocol forcing for replayed historical events.

A reactive SOP fires when the ship's own surveillance trips its trigger. A
replayed event is different: the record says what the authority did and on
which day, and the run has to do the same thing on the same day whether or not
its simulated surveillance would have got there. This module carries that
calendar. It names existing protocols and the simulated days they were in
force; it invents no modifier of its own, so what a scheduled protocol does is
still whatever ``protocols.json`` says it does.

Days are simulated days as :class:`engines.sim_clock.SimClock` counts them, so
the same schedule means the same wall-clock window at any epoch length.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from engines.sim_clock import SimClock

CONFIG_KEY = "scenario_schedule"


@dataclass(frozen=True)
class ScheduledProtocol:
    """One protocol held active from ``start_day`` through ``end_day`` inclusive.

    ``end_day`` of ``None`` holds it to the end of the run. The optional
    hour fields move the boundary inside the boundary day: a historical
    order that took effect at 07:00 on its start day declares
    ``start_hour_of_day=7``, and one lifted mid-day declares
    ``end_hour_of_day``. ``None`` keeps the whole-day default.
    """

    protocol_id: str
    start_day: int
    end_day: int | None = None
    start_hour_of_day: int | None = None
    end_hour_of_day: int | None = None

    def __post_init__(self) -> None:
        if not self.protocol_id:
            raise ValueError("scheduled protocol needs a protocol_id")
        if self.start_day < 0:
            raise ValueError(
                f"{self.protocol_id}: start_day {self.start_day} is negative",
            )
        if self.end_day is not None and self.end_day < self.start_day:
            raise ValueError(
                f"{self.protocol_id}: end_day {self.end_day} precedes "
                f"start_day {self.start_day}",
            )
        for name, value in (
            ("start_hour_of_day", self.start_hour_of_day),
            ("end_hour_of_day", self.end_hour_of_day),
        ):
            if value is not None and not 0 <= value < 24:
                raise ValueError(
                    f"{self.protocol_id}: {name} {value} is not in [0, 24)",
                )

    def active_on(self, day_index: int, hour_of_day: int = 0) -> bool:
        if day_index < self.start_day:
            return False
        if (
            day_index == self.start_day
            and self.start_hour_of_day is not None
            and hour_of_day < self.start_hour_of_day
        ):
            return False
        if self.end_day is None:
            return True
        if day_index > self.end_day:
            return False
        if (
            day_index == self.end_day
            and self.end_hour_of_day is not None
            and hour_of_day >= self.end_hour_of_day
        ):
            return False
        return True


@dataclass(frozen=True)
class ScenarioSchedule:
    """Every scheduled protocol of one run, in declaration order."""

    entries: tuple[ScheduledProtocol, ...] = ()

    @property
    def protocol_ids(self) -> frozenset[str]:
        return frozenset(entry.protocol_id for entry in self.entries)

    def active_protocol_ids(
        self,
        day_index: int,
        hour_of_day: int = 0,
    ) -> set[str]:
        """Protocols the calendar holds active at this day-and-hour mark."""
        return {
            entry.protocol_id
            for entry in self.entries
            if entry.active_on(int(day_index), int(hour_of_day))
        }

    def protocol_ids_for_day(self, day_index: int) -> set[str]:
        """Protocols the calendar activates at ANY hour of this day.

        The dealing-day union DP-REPLAY-ENVIRON-01 needs: an order that
        opens at 07:00 belongs to the day it opens on, so the rhythm
        layer's first-epoch-of-day deal sees its variant even though the
        order's modifiers do not bind until the declared hour.
        """
        day = int(day_index)
        return {
            entry.protocol_id
            for entry in self.entries
            if entry.start_day <= day
            and (entry.end_day is None or day <= entry.end_day)
        }

    def apply(self, epoch: int, clock: SimClock, forced: set[str]) -> set[str]:
        """Reconcile ``forced`` with the calendar for this epoch, in place.

        Protocols the schedule names are added while their window is open and
        removed once it closes; protocols it does not name are left exactly as
        command actions set them, so a scheduled window and a live command
        decision coexist.
        """
        day = clock.day_index(int(epoch))
        active = self.active_protocol_ids(day, clock.hour_of_day(int(epoch)))
        forced.difference_update(self.protocol_ids - active)
        forced.update(active)
        return forced


def _parse_entry(index: int, raw: Any) -> ScheduledProtocol:
    if not isinstance(raw, Mapping):
        raise ValueError(f"{CONFIG_KEY}[{index}] must be a mapping")
    end = raw.get("end_day")
    start_hour = raw.get("start_hour_of_day")
    end_hour = raw.get("end_hour_of_day")
    return ScheduledProtocol(
        protocol_id=str(raw.get("protocol_id", "")),
        start_day=int(raw.get("start_day", 0)),
        end_day=None if end is None else int(end),
        start_hour_of_day=None if start_hour is None else int(start_hour),
        end_hour_of_day=None if end_hour is None else int(end_hour),
    )


def resolve_scenario_schedule(cfg: Mapping[str, Any] | None) -> ScenarioSchedule:
    """Read ``cfg['scenario_schedule']``; absent means no calendar at all."""
    raw = (cfg or {}).get(CONFIG_KEY)
    if raw is None:
        return ScenarioSchedule()
    if not isinstance(raw, Mapping):
        raise ValueError(f"{CONFIG_KEY} must be a mapping")
    protocols = raw.get("protocols") or ()
    if not isinstance(protocols, (list, tuple)):
        raise ValueError(f"{CONFIG_KEY}.protocols must be a list")
    return ScenarioSchedule(
        tuple(_parse_entry(i, entry) for i, entry in enumerate(protocols)),
    )
