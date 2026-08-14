"""Sentinel observation bundle: clinical line list + wastewater samples.

Validated against ``schemas/sentinel_observations.schema.json``. Referential
integrity against the itinerary (port ids, epoch ranges, hours ashore bounded
by dwell time) is checked here rather than in the schema, which cannot see the
voyage config.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from picard_framework.analysis._io import read_json
from picard_framework.analysis.sentinel.itinerary import (
    HOURS_FROM_WINDOWS,
    Voyage,
)

REPORTING_CHANNELS = frozenset(
    {"sick_call", "screening", "cascade", "wearable", "unreported"},
)


@dataclass(frozen=True)
class ClinicalCase:
    """One observed symptomatic case with its ashore exposure history."""

    person_id: str
    onset_epoch: int
    crew: bool
    pathogen: str | None
    genotype: str | None
    hours_ashore: Mapping[str, float]
    reported_via: str
    report_epoch: int | None

    @property
    def went_ashore(self) -> bool:
        """True when any positive ashore exposure is recorded."""
        return any(h > 0.0 for h in self.hours_ashore.values())


@dataclass(frozen=True)
class WastewaterSample:
    """One compositional wastewater observation (GRUMB read counts)."""

    sample_epoch: int
    collection_point: str
    pathogen: str
    pathogen_reads: int
    total_reads: int
    clr_anomaly_score: float
    concentration_copies_per_l: float | None

    @property
    def relative_abundance(self) -> float:
        """Pathogen read fraction (0.0 for an empty library)."""
        return self.pathogen_reads / self.total_reads if self.total_reads > 0 else 0.0


@dataclass(frozen=True)
class ObservationBundle:
    """All sentinel observations for one voyage."""

    voyage_id: str
    ship_id: str
    clinical_cases: tuple[ClinicalCase, ...]
    wastewater_samples: tuple[WastewaterSample, ...]
    n_passengers: int
    n_crew: int
    observation_end_epoch: int | None
    platform_class: str | None
    exposure_totals: Mapping[str, Mapping[str, float]] = field(
        default_factory=lambda: MappingProxyType({}),
    )


def _case_from_dict(raw: dict[str, Any]) -> ClinicalCase:
    channel = str(raw.get("reported_via") or "unreported")
    if channel not in REPORTING_CHANNELS:
        raise ValueError(f"Unknown reported_via: {channel!r}")
    hours_raw = raw.get("hours_ashore") or {}
    if not isinstance(hours_raw, dict):
        raise ValueError("hours_ashore must be an object keyed by port_id")
    hours: dict[str, float] = {}
    for port_id, value in hours_raw.items():
        hours_val = float(value)
        if hours_val < 0.0:
            raise ValueError(f"Negative hours_ashore for port {port_id!r}")
        hours[str(port_id)] = hours_val
    onset = int(raw["onset_epoch"])
    if onset < 1:
        raise ValueError("onset_epoch must be >= 1")
    report_epoch = raw.get("report_epoch")
    return ClinicalCase(
        person_id=str(raw["person_id"]),
        onset_epoch=onset,
        crew=bool(raw["crew"]),
        pathogen=None if raw.get("pathogen") is None else str(raw["pathogen"]),
        genotype=None if raw.get("genotype") is None else str(raw["genotype"]),
        hours_ashore=MappingProxyType(hours),
        reported_via=channel,
        report_epoch=None if report_epoch is None else int(report_epoch),
    )


def _sample_from_dict(raw: dict[str, Any]) -> WastewaterSample:
    reads = int(raw["pathogen_reads"])
    total = int(raw["total_reads"])
    if reads > total:
        raise ValueError(
            f"pathogen_reads ({reads}) exceeds total_reads ({total}) "
            f"at epoch {raw.get('sample_epoch')}",
        )
    conc = raw.get("concentration_copies_per_l")
    return WastewaterSample(
        sample_epoch=int(raw["sample_epoch"]),
        collection_point=str(raw["collection_point"]),
        pathogen=str(raw["pathogen"]),
        pathogen_reads=reads,
        total_reads=total,
        clr_anomaly_score=float(raw.get("clr_anomaly_score") or 0.0),
        concentration_copies_per_l=None if conc is None else float(conc),
    )


def _exposure_totals_from_dict(raw: object) -> Mapping[str, Mapping[str, float]]:
    if raw is None:
        return MappingProxyType({})
    if not isinstance(raw, dict):
        raise ValueError("exposure_totals must be an object keyed by port_id")
    totals: dict[str, Mapping[str, float]] = {}
    for port_id, cell in raw.items():
        if not isinstance(cell, dict):
            raise ValueError(f"exposure_totals[{port_id!r}] must be an object")
        values = {str(k): float(v) for k, v in cell.items()}
        negative = sorted(k for k, v in values.items() if v < 0.0)
        if negative:
            raise ValueError(
                f"exposure_totals[{port_id!r}] has negative values: {negative}",
            )
        totals[str(port_id)] = MappingProxyType(values)
    return MappingProxyType(totals)


def bundle_from_dict(payload: dict[str, Any]) -> ObservationBundle:
    """Build an ``ObservationBundle`` from a decoded observation document."""
    cases = [_case_from_dict(c) for c in payload.get("clinical_cases") or []]
    ids = [c.person_id for c in cases]
    duplicates = sorted({pid for pid in ids if ids.count(pid) > 1})
    if duplicates:
        raise ValueError(f"Duplicate person_id in clinical_cases: {duplicates}")
    end_epoch = payload.get("observation_end_epoch")
    return ObservationBundle(
        voyage_id=str(payload["voyage_id"]),
        ship_id=str(payload["ship_id"]),
        clinical_cases=tuple(sorted(cases, key=lambda c: (c.onset_epoch, c.person_id))),
        wastewater_samples=tuple(
            sorted(
                (_sample_from_dict(s) for s in payload.get("wastewater_samples") or []),
                key=lambda s: (s.sample_epoch, s.collection_point, s.pathogen),
            ),
        ),
        n_passengers=int(payload.get("n_passengers") or 0),
        n_crew=int(payload.get("n_crew") or 0),
        observation_end_epoch=None if end_epoch is None else int(end_epoch),
        platform_class=(
            None if payload.get("platform_class") is None
            else str(payload["platform_class"])
        ),
        exposure_totals=_exposure_totals_from_dict(payload.get("exposure_totals")),
    )


def load_observation_bundle(path: str) -> ObservationBundle:
    """Load an observation bundle from a JSON document on disk."""
    raw = read_json(path)
    if not isinstance(raw, dict):
        raise ValueError(f"sentinel observations must be an object: {path}")
    return bundle_from_dict(raw)


def _port_hours_problems(
    case: ClinicalCase,
    voyage: Voyage,
) -> list[str]:
    problems: list[str] = []
    for port_id, hours in case.hours_ashore.items():
        call = voyage.port_call(port_id)
        if call is None:
            problems.append(
                f"case {case.person_id}: hours_ashore references unknown port {port_id!r}",
            )
            continue
        if call.hours_ashore_source != HOURS_FROM_WINDOWS:
            continue
        dwell = (call.departure_epoch - call.arrival_epoch + 1) * voyage.epoch_duration_hours
        if hours > dwell:
            problems.append(
                f"case {case.person_id}: {hours:.1f} h ashore at {port_id} "
                f"exceeds the {dwell:.1f} h port dwell",
            )
    return problems


def validate_against_voyage(
    bundle: ObservationBundle,
    voyage: Voyage,
) -> list[str]:
    """Return human-readable referential-integrity problems (empty when clean).

    Kept as a report rather than an exception so a fleet run can drop or flag
    individual voyages instead of aborting.
    """
    problems: list[str] = []
    if bundle.voyage_id != voyage.voyage_id:
        problems.append(
            f"voyage_id mismatch: observations {bundle.voyage_id!r} "
            f"vs itinerary {voyage.voyage_id!r}",
        )
    if bundle.ship_id != voyage.ship_id:
        problems.append(
            f"ship_id mismatch: observations {bundle.ship_id!r} "
            f"vs itinerary {voyage.ship_id!r}",
        )
    end_epoch = bundle.observation_end_epoch or voyage.observation_end_epoch
    for case in bundle.clinical_cases:
        if case.onset_epoch > end_epoch:
            problems.append(
                f"case {case.person_id}: onset_epoch {case.onset_epoch} "
                f"is past observation_end_epoch {end_epoch}",
            )
        if case.report_epoch is not None and case.report_epoch < case.onset_epoch:
            problems.append(
                f"case {case.person_id}: report_epoch precedes onset_epoch",
            )
        problems.extend(_port_hours_problems(case, voyage))
    for sample in bundle.wastewater_samples:
        if sample.sample_epoch > end_epoch:
            problems.append(
                f"wastewater sample at epoch {sample.sample_epoch} "
                f"is past observation_end_epoch {end_epoch}",
            )
    return problems
