"""Sentinel observation bundle: clinical line list + wastewater samples.

Validated against ``schemas/sentinel_observations.schema.json``. Referential
integrity against the itinerary (port ids, epoch ranges, hours ashore bounded
by dwell time) is checked here rather than in the schema, which cannot see the
voyage config.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from picard_framework.analysis._io import read_json
from picard_framework.analysis.sentinel.itinerary import (
    HOURS_FROM_WINDOWS,
    Voyage,
)
from picard_framework.analysis.sentinel.wastewater_assays import (
    ASSAY_METAGENOMIC,
    resolve_assay_mode,
)

REPORTING_CHANNELS = frozenset(
    {"sick_call", "screening", "cascade", "wearable", "unreported"},
)

_STRATA = frozenset({"passenger", "crew"})


@dataclass(frozen=True)
class ProvisioningSource:
    """Provisioned servings from one source, consumed per stratum per epoch.

    Two shapes are accepted, mirroring how ashore hours may be per-epoch or a
    total spread over the call window: explicit ``servings_per_epoch`` rows, or
    ``servings_total`` plus ``service_window_epochs`` which the data builder
    spreads uniformly. A ``source_id`` is a supply-chain entity from the
    PROVISIONED-SOURCE-01 mint ledger, not a port call — it never enters the
    itinerary's port list.
    """

    source_id: str
    servings_per_epoch: Mapping[str, tuple[float, ...]]
    servings_total: Mapping[str, float]
    service_window_epochs: tuple[int, int] | None

    @property
    def first_service_epoch(self) -> int | None:
        """First epoch the source serves, per whichever shape was given."""
        if self.servings_per_epoch:
            first = min(
                (i + 1 for row in self.servings_per_epoch.values()
                 for i, s in enumerate(row) if s > 0.0),
                default=None,
            )
            return first
        if self.service_window_epochs is not None:
            return self.service_window_epochs[0]
        return None


@dataclass(frozen=True)
class Embarkation:
    """The boarding pool: which market each stratum boarded from and how many.

    ``markets`` maps stratum -> market_id because a line's consumer market and
    its crew labour market are different pools. ``n_boarded`` defaults to the
    complement (``n_passengers``/``n_crew``) when absent; ``embark_epoch``
    defaults to the embarkation day's first epoch at fit time.
    """

    markets: Mapping[str, str]
    n_boarded: Mapping[str, float]
    embark_epoch: int | None


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
class LineageCall:
    """One lineage a wastewater library resolved, and how much of it it saw."""

    genotype: str
    reads: int
    fraction: float


@dataclass(frozen=True)
class WastewaterSample:
    """One wastewater observation, in whatever assay mode produced it.

    The read fields and the concentration fields are alternatives, not a pair: a
    qPCR row has no library and a shotgun row has no Ct. Both are carried on one
    dataclass because they are the same *sample* — the same tank, epoch, and tap
    — and the fit routes them to the channel their populated fields support
    (:mod:`wastewater_signal`).

    A non-detect keeps ``ct_value`` and ``concentration_copies_per_l`` at
    ``None`` and reports ``lod_copies_per_l``: that is a censored observation,
    which is evidence, and dropping it or filling it with a zero would bias the
    inferred prevalence in opposite directions.
    """

    sample_epoch: int
    collection_point: str
    pathogen: str
    pathogen_reads: int
    total_reads: int
    clr_anomaly_score: float
    concentration_copies_per_l: float | None
    assay_mode: str = ASSAY_METAGENOMIC
    ct_value: float | None = None
    detected: bool | None = None
    lod_copies_per_l: float | None = None
    turnaround_hours: float | None = None
    genotype: str | None = None
    lineage_status: str | None = None
    lineage_calls: tuple[LineageCall, ...] = ()
    lineage_unresolved_reads: int | None = None
    pathogen_id: str = ""

    @property
    def profile_key(self) -> str:
        """Key to join this row to ABM truth by.

        ``pathogen`` is the delay-catalog label the fit filters on, which is a
        different vocabulary from the profile id a lineage census is keyed on
        (``norovirus`` vs ``norwalk_gi``). Joining on the label drops every row
        silently, so the id is used whenever the run named one.
        """
        return self.pathogen_id or self.pathogen

    @property
    def resolved_lineage_fraction(self) -> float:
        """Share of the on-target reads a lineage call was made for.

        The honest measure of how much of the pool the assay typed: reads that
        fell below the reporting floor, or that came from untracked pool mass,
        are pathogen the library saw and could not name.
        """
        if self.pathogen_reads <= 0:
            return 0.0
        called = sum(call.reads for call in self.lineage_calls)
        return called / self.pathogen_reads

    @property
    def relative_abundance(self) -> float:
        """Pathogen read fraction (0.0 for an empty library)."""
        return self.pathogen_reads / self.total_reads if self.total_reads > 0 else 0.0

    @property
    def has_concentration_observation(self) -> bool:
        """True when the row carries a quantitative or censored concentration."""
        if self.lod_copies_per_l is None:
            return False
        return self.concentration_copies_per_l is not None or self.detected is False


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
    provisioning: tuple[ProvisioningSource, ...] = ()
    embarkation: Embarkation | None = None
    covariates: Mapping[str, float] = field(
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


def _optional_float(raw: dict[str, Any], key: str) -> float | None:
    value = raw.get(key)
    return None if value is None else float(value)


def _lineage_calls_from_raw(
    raw: dict[str, Any],
    *,
    pathogen_reads: int,
) -> tuple[LineageCall, ...]:
    """Lineage calls of one wastewater row, validated against its library.

    Called reads cannot exceed the on-target reads they were drawn from: a row
    claiming otherwise has had its composition renormalized somewhere upstream,
    which is exactly the error that makes a deconvolution look better than it is.
    """
    entries = raw.get("lineage_calls") or []
    if not isinstance(entries, list):
        raise ValueError("lineage_calls must be a list of lineage objects")
    calls = tuple(
        LineageCall(
            genotype=str(entry["genotype"]),
            reads=int(entry["reads"]),
            fraction=float(entry.get("fraction") or 0.0),
        )
        for entry in entries
    )
    called = sum(call.reads for call in calls)
    if called > pathogen_reads:
        raise ValueError(
            f"lineage reads ({called}) exceed pathogen_reads ({pathogen_reads}) "
            f"at epoch {raw.get('sample_epoch')}",
        )
    return calls


def _sample_from_dict(raw: dict[str, Any]) -> WastewaterSample:
    # Absent read fields mean "this mode does not sequence", not zero reads out of
    # zero: an empty library is dropped by the read channel either way, but the
    # distinction is what keeps a qPCR row from being scored as a failed shotgun.
    reads = int(raw.get("pathogen_reads") or 0)
    total = int(raw.get("total_reads") or 0)
    if reads > total:
        raise ValueError(
            f"pathogen_reads ({reads}) exceeds total_reads ({total}) "
            f"at epoch {raw.get('sample_epoch')}",
        )
    detected = raw.get("detected")
    mode = resolve_assay_mode(raw.get("assay_mode") or ASSAY_METAGENOMIC)
    conc = _optional_float(raw, "concentration_copies_per_l")
    lod = _optional_float(raw, "lod_copies_per_l")
    if conc is not None and detected is False:
        raise ValueError(
            "a sample below the limit of detection cannot report a "
            f"concentration at epoch {raw.get('sample_epoch')}",
        )
    if conc is not None and lod is None and mode != ASSAY_METAGENOMIC:
        raise ValueError(
            "a quantitative wastewater sample must report lod_copies_per_l "
            f"at epoch {raw.get('sample_epoch')}",
        )
    return WastewaterSample(
        sample_epoch=int(raw["sample_epoch"]),
        collection_point=str(raw["collection_point"]),
        pathogen=str(raw["pathogen"]),
        pathogen_id=str(raw.get("pathogen_id") or ""),
        pathogen_reads=reads,
        total_reads=total,
        clr_anomaly_score=float(raw.get("clr_anomaly_score") or 0.0),
        concentration_copies_per_l=conc,
        assay_mode=mode,
        ct_value=_optional_float(raw, "ct_value"),
        detected=None if detected is None else bool(detected),
        lod_copies_per_l=lod,
        turnaround_hours=_optional_float(raw, "turnaround_hours"),
        genotype=None if raw.get("genotype") is None else str(raw["genotype"]),
        lineage_status=(
            None if raw.get("lineage_status") is None else str(raw["lineage_status"])
        ),
        lineage_calls=_lineage_calls_from_raw(raw, pathogen_reads=reads),
        lineage_unresolved_reads=(
            None
            if raw.get("lineage_unresolved_reads") is None
            else int(raw["lineage_unresolved_reads"])
        ),
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


def _strata_check(source_id: str, stratum: object) -> str:
    if str(stratum) not in _STRATA:
        raise ValueError(
            f"provisioning[{source_id!r}]: unknown stratum {stratum!r}",
        )
    return str(stratum)


def _servings_per_epoch(
    source_id: str,
    raw: Mapping[str, Any],
) -> dict[str, tuple[float, ...]]:
    per_epoch_raw = raw.get("servings_per_epoch") or {}
    if not isinstance(per_epoch_raw, dict):
        raise ValueError(
            f"provisioning[{source_id!r}].servings_per_epoch must be an object "
            "keyed by stratum",
        )
    per_epoch: dict[str, tuple[float, ...]] = {}
    for stratum, row in per_epoch_raw.items():
        key = _strata_check(source_id, stratum)
        values = tuple(float(v) for v in (row or []))
        if any(v < 0.0 for v in values):
            raise ValueError(
                f"provisioning[{source_id!r}] has negative servings",
            )
        per_epoch[key] = values
    return per_epoch


def _servings_totals(
    source_id: str,
    raw: Mapping[str, Any],
) -> dict[str, float]:
    totals_raw = raw.get("servings_total") or {}
    if not isinstance(totals_raw, dict):
        raise ValueError(
            f"provisioning[{source_id!r}].servings_total must be an object "
            "keyed by stratum",
        )
    totals: dict[str, float] = {}
    for stratum, value in totals_raw.items():
        key = _strata_check(source_id, stratum)
        total = float(value)
        if total < 0.0:
            raise ValueError(
                f"provisioning[{source_id!r}] has negative servings",
            )
        totals[key] = total
    return totals


def _service_window(
    source_id: str,
    raw: Mapping[str, Any],
) -> tuple[int, int] | None:
    window_raw = raw.get("service_window_epochs")
    if window_raw is None:
        return None
    if not isinstance(window_raw, (list, tuple)) or len(window_raw) != 2:
        raise ValueError(
            f"provisioning[{source_id!r}].service_window_epochs must be "
            "[first_epoch, last_epoch]",
        )
    window = (int(window_raw[0]), int(window_raw[1]))
    if window[0] < 1 or window[1] < window[0]:
        raise ValueError(
            f"provisioning[{source_id!r}].service_window_epochs must be "
            "1-based and non-empty",
        )
    return window


def _provisioning_source_from_dict(
    source_id: str,
    raw: object,
) -> ProvisioningSource:
    if not isinstance(raw, dict):
        raise ValueError(f"provisioning[{source_id!r}] must be an object")
    per_epoch = _servings_per_epoch(source_id, raw)
    totals = _servings_totals(source_id, raw)
    window = _service_window(source_id, raw)
    if totals and window is None:
        raise ValueError(
            f"provisioning[{source_id!r}]: servings_total requires "
            "service_window_epochs",
        )
    if not per_epoch and not totals:
        raise ValueError(
            f"provisioning[{source_id!r}] names no servings "
            "(servings_per_epoch or servings_total)",
        )
    return ProvisioningSource(
        source_id=str(source_id),
        servings_per_epoch=MappingProxyType(per_epoch),
        servings_total=MappingProxyType(totals),
        service_window_epochs=window,
    )


def _provisioning_from_dict(raw: object) -> tuple[ProvisioningSource, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, dict):
        raise ValueError("provisioning must be an object keyed by source_id")
    return tuple(
        _provisioning_source_from_dict(str(source_id), cell)
        for source_id, cell in raw.items()
    )


def _embarkation_markets(raw: Mapping[str, Any]) -> dict[str, str]:
    markets_raw = raw.get("markets") or {}
    if not isinstance(markets_raw, dict) or not markets_raw:
        raise ValueError("embarkation.markets must map stratum to market_id")
    markets: dict[str, str] = {}
    for stratum, market_id in markets_raw.items():
        if str(stratum) not in _STRATA:
            raise ValueError(
                f"embarkation.markets: unknown stratum {stratum!r}",
            )
        markets[str(stratum)] = str(market_id)
    return markets


def _embarkation_boarded(raw: Mapping[str, Any]) -> dict[str, float]:
    boarded_raw = raw.get("n_boarded") or {}
    if not isinstance(boarded_raw, dict):
        raise ValueError("embarkation.n_boarded must be an object keyed by stratum")
    n_boarded: dict[str, float] = {}
    for stratum, value in boarded_raw.items():
        if str(stratum) not in _STRATA:
            raise ValueError(
                f"embarkation.n_boarded: unknown stratum {stratum!r}",
            )
        boarded = float(value)
        if boarded < 0.0:
            raise ValueError("embarkation.n_boarded must be non-negative")
        n_boarded[str(stratum)] = boarded
    return n_boarded


def _embarkation_from_dict(raw: object) -> Embarkation | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("embarkation must be an object")
    embark_epoch = raw.get("embark_epoch")
    return Embarkation(
        markets=MappingProxyType(_embarkation_markets(raw)),
        n_boarded=MappingProxyType(_embarkation_boarded(raw)),
        embark_epoch=None if embark_epoch is None else int(embark_epoch),
    )


def _covariates_from_dict(raw: object) -> Mapping[str, float]:
    if raw is None:
        return MappingProxyType({})
    if not isinstance(raw, dict):
        raise ValueError("covariates must be an object keyed by name")
    covariates: dict[str, float] = {}
    for name, value in raw.items():
        cov = float(value)
        if not math.isfinite(cov):
            raise ValueError(f"covariates[{name!r}] is not a finite number")
        covariates[str(name)] = cov
    return MappingProxyType(covariates)


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
        provisioning=_provisioning_from_dict(payload.get("provisioning")),
        embarkation=_embarkation_from_dict(payload.get("embarkation")),
        covariates=_covariates_from_dict(payload.get("covariates")),
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
        calls = voyage.port_calls_for(port_id)
        if not calls:
            problems.append(
                f"case {case.person_id}: hours_ashore references unknown port {port_id!r}",
            )
            continue
        # The home port is visited twice and a repositioning itinerary can
        # repeat a port, so the budget is the sum of the windowed visits.
        windowed = [c for c in calls if c.hours_ashore_source == HOURS_FROM_WINDOWS]
        if not windowed:
            continue
        dwell = voyage.epoch_duration_hours * sum(
            c.departure_epoch - c.arrival_epoch + 1 for c in windowed
        )
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
