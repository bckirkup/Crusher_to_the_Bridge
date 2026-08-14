"""Per-person sentinel line list and its exposure denominators.

The ABM's epoch history keeps aggregate counts (and, under ``compact``
retention, nothing per agent at all), so onset epochs and hours ashore do not
survive a run. ``SentinelLedger`` accumulates exactly the per-person fields the
attribution model needs — first symptom epoch, crew status, hours ashore per
port, detection channel — plus the person-hour denominators that make a hazard
a rate rather than a share (spec §2).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from telemetry_buffer.agent_axes import agent_has_symptomatic_presentation

# Ordered by evidentiary strength: the strongest channel a person ever hit is
# the one reported, since the observation model conditions on it.
CHANNEL_PRIORITY: tuple[str, ...] = ("sick_call", "screening", "cascade", "wearable")
UNREPORTED = "unreported"


@dataclass(frozen=True)
class LineListRecord:
    """One person's sentinel observation."""

    person_id: str
    onset_epoch: int
    crew: bool
    pathogen: str | None
    genotype: str | None
    hours_ashore: dict[str, float]
    reported_via: str
    report_epoch: int | None

    def to_dict(self) -> dict[str, Any]:
        """Schema-shaped clinical case record."""
        return {
            "person_id": self.person_id,
            "onset_epoch": self.onset_epoch,
            "crew": self.crew,
            "pathogen": self.pathogen,
            "genotype": self.genotype,
            "hours_ashore": dict(sorted(self.hours_ashore.items())),
            "reported_via": self.reported_via,
            "report_epoch": self.report_epoch,
        }


@dataclass
class _PortExposure:
    """Person-hours ashore at one port, split by stratum."""

    person_hours_passenger: float = 0.0
    person_hours_crew: float = 0.0
    passengers_ashore: set[int] = field(default_factory=set)
    crew_ashore: set[int] = field(default_factory=set)

    def to_dict(self) -> dict[str, Any]:
        """Schema-shaped exposure denominator."""
        return {
            "person_hours_passenger": round(self.person_hours_passenger, 4),
            "person_hours_crew": round(self.person_hours_crew, 4),
            "n_passengers_ashore": len(self.passengers_ashore),
            "n_crew_ashore": len(self.crew_ashore),
        }


def agent_is_crew(agent: Mapping[str, Any]) -> bool:
    """Crew/passenger split from whichever role field the record carries."""
    role = str(agent.get("role") or "")
    if role:
        return role == "crew"
    return str(agent.get("agent_class") or "").startswith("crew")


def active_pathogen(agent: Mapping[str, Any]) -> str | None:
    """Lowest-sorted pathogen id with an active infection, if any.

    Returns ``None`` for a single-pathogen run or a syndromic-only case, which
    the schema allows: the attribution model treats pathogen as observed-if-
    available rather than required.
    """
    infections = agent.get("pathogen_infections") or {}
    if not isinstance(infections, Mapping):
        return None
    active = [
        str(pid)
        for pid, info in infections.items()
        if isinstance(info, Mapping) and str(info.get("status", "")) == "INFECTED"
    ]
    return sorted(active)[0] if active else None


class SentinelLedger:
    """Accumulate per-person sentinel observations across epochs.

    Retention-independent: it reads the same per-epoch agent records the
    orchestrator already builds, and keeps only one row per person.
    """

    def __init__(self, *, epoch_duration_hours: float = 1.0) -> None:
        self.epoch_duration_hours = float(epoch_duration_hours or 1.0)
        self.last_epoch = 0
        self._onset: dict[int, int] = {}
        self._crew: dict[int, bool] = {}
        self._pathogen: dict[int, str | None] = {}
        self._hours: dict[int, dict[str, float]] = {}
        self._channel: dict[int, tuple[int, int]] = {}
        self._exposure: dict[str, _PortExposure] = {}

    def observe_epoch(
        self,
        epoch: int,
        agents: Sequence[Mapping[str, Any]],
        *,
        port_id: str = "",
        ashore_ids: Iterable[int] = (),
        detections: Mapping[str, Iterable[int]] | None = None,
    ) -> None:
        """Fold one epoch of agent records into the ledger.

        Epochs are clamped to >= 1 the same way ``resolve_epoch_state`` clamps
        them, so a run whose loop starts at 0 still lands on voyage day 1.
        """
        epoch = max(1, int(epoch))
        self.last_epoch = max(self.last_epoch, epoch)
        ashore = {int(a) for a in ashore_ids}
        crew_by_id: dict[int, bool] = {}
        for agent in agents:
            aid = int(agent["agent_id"])
            crew = agent_is_crew(agent)
            crew_by_id[aid] = crew
            self._crew[aid] = crew
            if aid not in self._onset and agent_has_symptomatic_presentation(dict(agent)):
                self._onset[aid] = int(epoch)
                self._pathogen[aid] = active_pathogen(agent)
        if port_id and ashore:
            self._accumulate_ashore(port_id, ashore, crew_by_id)
        self._record_detections(epoch, detections)

    def _accumulate_ashore(
        self,
        port_id: str,
        ashore: set[int],
        crew_by_id: Mapping[int, bool],
    ) -> None:
        cell = self._exposure.setdefault(port_id, _PortExposure())
        for aid in ashore:
            self._hours.setdefault(aid, {})
            self._hours[aid][port_id] = (
                self._hours[aid].get(port_id, 0.0) + self.epoch_duration_hours
            )
            if crew_by_id.get(aid, self._crew.get(aid, False)):
                cell.person_hours_crew += self.epoch_duration_hours
                cell.crew_ashore.add(aid)
            else:
                cell.person_hours_passenger += self.epoch_duration_hours
                cell.passengers_ashore.add(aid)

    def _record_detections(
        self,
        epoch: int,
        detections: Mapping[str, Iterable[int]] | None,
    ) -> None:
        if not detections:
            return
        for channel, ids in detections.items():
            if channel not in CHANNEL_PRIORITY:
                raise ValueError(f"Unknown detection channel: {channel!r}")
            rank = CHANNEL_PRIORITY.index(channel)
            for raw_id in ids:
                aid = int(raw_id)
                prior = self._channel.get(aid)
                if prior is None or rank < prior[0]:
                    self._channel[aid] = (rank, int(epoch))

    def records(self) -> tuple[LineListRecord, ...]:
        """Line-list rows for every person with an observed onset."""
        rows: list[LineListRecord] = []
        for aid, onset in self._onset.items():
            channel = self._channel.get(aid)
            reported_via = UNREPORTED if channel is None else CHANNEL_PRIORITY[channel[0]]
            report_epoch = None if channel is None else max(channel[1], onset)
            rows.append(
                LineListRecord(
                    person_id=str(aid),
                    onset_epoch=onset,
                    crew=self._crew.get(aid, False),
                    pathogen=self._pathogen.get(aid),
                    genotype=None,
                    hours_ashore=dict(self._hours.get(aid, {})),
                    reported_via=reported_via,
                    report_epoch=report_epoch,
                ),
            )
        return tuple(sorted(rows, key=lambda r: (r.onset_epoch, int(r.person_id))))

    def exposure_totals(self) -> dict[str, dict[str, Any]]:
        """Person-hours ashore per port (the hazard denominator)."""
        return {
            port_id: cell.to_dict()
            for port_id, cell in sorted(self._exposure.items())
        }

    def to_payload(
        self,
        *,
        voyage_id: str,
        ship_id: str,
        n_passengers: int = 0,
        n_crew: int = 0,
        platform_class: str | None = None,
        observation_end_epoch: int | None = None,
        wastewater_samples: Sequence[Mapping[str, Any]] = (),
    ) -> dict[str, Any]:
        """Build a ``sentinel_observations.schema.json`` document."""
        payload: dict[str, Any] = {
            "schema_version": "1.0.0",
            "voyage_id": voyage_id,
            "ship_id": ship_id,
            "n_passengers": int(n_passengers),
            "n_crew": int(n_crew),
            "epoch_duration_hours": self.epoch_duration_hours,
            "observation_end_epoch": int(observation_end_epoch or self.last_epoch or 1),
            "clinical_cases": [r.to_dict() for r in self.records()],
            "wastewater_samples": [dict(s) for s in wastewater_samples],
            "exposure_totals": self.exposure_totals(),
        }
        if platform_class:
            payload["platform_class"] = platform_class
        return payload
