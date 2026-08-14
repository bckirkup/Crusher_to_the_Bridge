"""Exposure cells, offsets, and per-case port attribution weights.

The likelihood unit is one ``voyage x port-call x stratum`` cell whose Poisson
offset is ``log(person-hours ashore)`` — the denominator whose absence turns the
model into an attribution-share estimator (spec 1.4). Two corrections ride on
the same offset:

- **censoring** (1.6): a cell only ever shows the fraction of its infections
  whose incubation fits inside the observation window
- **ascertainment**: reporting x care-seeking x testing, the observation model
  folded in here rather than in a separate module (1.9)

Aboard persons are *not* emitted as one cell per port call. The same person
stays aboard at several ports, so per-port aboard cells would enter the
likelihood repeatedly with the same zero-hours exposure and double-count the
onboard baseline; the aboard denominator is a single voyage-level baseline cell
per stratum instead.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np

from picard_framework.analysis.sentinel.incubation import (
    DelayDistribution,
    observed_onset_fraction,
)
from picard_framework.analysis.sentinel.itinerary import (
    HOURS_FROM_WINDOWS,
    PortCall,
    Voyage,
    censoring_epochs_after,
)
from picard_framework.analysis.sentinel.observations import (
    ClinicalCase,
    ObservationBundle,
)

PAX_ASHORE = "pax_ashore"
PAX_ABOARD = "pax_aboard"
CREW_ASHORE = "crew_ashore"
CREW_ABOARD = "crew_aboard"
STRATA = (PAX_ASHORE, PAX_ABOARD, CREW_ASHORE, CREW_ABOARD)

# exposure_totals keys written by SentinelLedger.exposure_totals()
_HOURS_KEY = {PAX_ASHORE: "person_hours_passenger", CREW_ASHORE: "person_hours_crew"}
_COUNT_KEY = {PAX_ASHORE: "n_passengers_ashore", CREW_ASHORE: "n_crew_ashore"}


@dataclass(frozen=True)
class ExposureCell:
    """One voyage x port-call x ashore-stratum likelihood cell."""

    voyage_id: str
    ship_id: str
    port_id: str
    port_visit_key: str
    stratum: str
    n_calls: int
    n_persons: int
    person_hours_ashore: float
    cases: int
    expected_cases: float
    censor_epochs_remaining: int
    observed_fraction: float
    ascertainment: float

    @property
    def crew(self) -> bool:
        """Whether this cell is a crew stratum."""
        return self.stratum in (CREW_ASHORE, CREW_ABOARD)

    @property
    def effective_person_hours(self) -> float:
        """Exposure actually able to produce an *observed* case.

        ``person-hours x P(onset <= T_end) x ascertainment`` — the quantity that
        belongs in the Poisson offset, so the fitted hazard is per exposed
        person-hour rather than per observed person-hour.
        """
        return self.person_hours_ashore * self.observed_fraction * self.ascertainment

    @property
    def log_offset(self) -> float | None:
        """``log(effective_person_hours)``, or None when the cell is empty.

        None rather than ``-inf``: a cell with no exposure carries no hazard
        information and must be dropped, not driven to zero rate.
        """
        hours = self.effective_person_hours
        return math.log(hours) if hours > 0.0 else None

    @property
    def censoring_corrected(self) -> bool:
        """Whether censoring actually bites in this cell."""
        return self.observed_fraction < 1.0


@dataclass(frozen=True)
class BaselineCell:
    """Voyage-level onboard baseline for one crew/passenger stratum.

    Carries the person-hours *aboard* and the onsets with no ashore exposure at
    all: the cases the port hazards must not be allowed to explain.
    """

    voyage_id: str
    ship_id: str
    stratum: str
    n_persons: int
    person_hours_aboard: float
    cases: int


@dataclass(frozen=True)
class ExposureDesign:
    """Everything the attribution model needs from one voyage."""

    voyage_id: str
    ship_id: str
    observation_end_epoch: int
    epoch_duration_hours: float
    port_cells: tuple[ExposureCell, ...]
    baseline_cells: tuple[BaselineCell, ...]
    onsets_by_epoch: tuple[int, ...]
    ascertainment: float

    @property
    def usable_cells(self) -> tuple[ExposureCell, ...]:
        """Cells with a finite offset (positive effective exposure)."""
        return tuple(c for c in self.port_cells if c.log_offset is not None)

    def onset_counts(self) -> np.ndarray:
        """Onsets per observation epoch, index 0 = epoch 1."""
        return np.asarray(self.onsets_by_epoch, dtype=float)


def ascertainment_fraction(
    *,
    reporting: float = 1.0,
    care_seeking: float = 1.0,
    testing: float = 1.0,
) -> float:
    """Product of the observation-model channels, validated to ``(0, 1]``.

    Kept multiplicative and explicit because it scales every hazard by the same
    factor: a reviewer must be able to see what the reported rate is per.
    """
    factors = {"reporting": reporting, "care_seeking": care_seeking, "testing": testing}
    for name, value in factors.items():
        if not 0.0 < float(value) <= 1.0:
            raise ValueError(f"{name} must be in (0, 1]: {value}")
    return float(reporting) * float(care_seeking) * float(testing)


def ashore_epochs(voyage: Voyage, call: PortCall) -> tuple[int, ...]:
    """Epochs during which people could be ashore at this call."""
    del voyage  # signature symmetry with the other window helpers
    return tuple(range(call.arrival_epoch, call.departure_epoch + 1))


def min_inter_port_hours(voyage: Voyage) -> float:
    """Shortest gap between consecutive port arrivals, in hours (spec 1.8)."""
    calls = voyage.port_calls
    if len(calls) < 2:
        return math.inf
    gaps = [
        (b.arrival_epoch - a.arrival_epoch) * voyage.epoch_duration_hours
        for a, b in zip(calls, calls[1:])
    ]
    return float(min(gaps))


def import_attribution_weights(
    case: ClinicalCase,
    voyage: Voyage,
    incubation: DelayDistribution,
) -> dict[str, float]:
    """Per-port weights for one case, conditional on the case being imported.

    Weight is (hours ashore at the port) x (incubation mass linking that port's
    ashore epochs to the observed onset), normalized over ports. The
    imported-vs-onboard split is *not* decided here: that is what the renewal
    term and the sampled ``R_onboard`` are for (1.5). These weights are the
    conditional term, and a case with no ashore hours returns ``{}``.
    """
    by_port = _calls_by_port(voyage)
    raw: dict[str, float] = {}
    for port_id, hours in case.hours_ashore.items():
        if hours <= 0.0:
            continue
        mass = sum(
            incubation.weight_at(case.onset_epoch - epoch)
            for call in by_port.get(port_id, ())
            for epoch in ashore_epochs(voyage, call)
        )
        if mass > 0.0:
            raw[port_id] = float(hours) * mass
    total = sum(raw.values())
    if total <= 0.0:
        return {}
    return {port_id: value / total for port_id, value in sorted(raw.items())}


def derived_exposure_totals(
    voyage: Voyage,
) -> dict[str, dict[str, float]]:
    """Person-hour denominators from the itinerary, for field voyages.

    MIDRS carries no port-call attribution, so a retrospective voyage has no
    observed ashore ledger: the denominator is reconstructed as
    ``n_persons x ashore_fraction x mean_hours_ashore`` from the schedule, and
    the ashore fraction is a *prior* whose sensitivity has to be reported
    (spec 6). Synthetic runs should pass the simulated ledger instead.
    """
    totals: dict[str, dict[str, float]] = {}
    for call in voyage.port_calls:
        hours = call.mean_hours_ashore
        if call.hours_ashore_source != HOURS_FROM_WINDOWS or hours <= 0.0:
            continue
        n_pax = int(round(voyage.n_passengers * call.pax_ashore_fraction))
        n_crew = int(round(voyage.n_crew * call.crew_ashore_fraction))
        cell = totals.setdefault(
            call.port_id,
            {
                "person_hours_passenger": 0.0,
                "person_hours_crew": 0.0,
                "n_passengers_ashore": 0.0,
                "n_crew_ashore": 0.0,
            },
        )
        cell["person_hours_passenger"] += n_pax * hours
        cell["person_hours_crew"] += n_crew * hours
        cell["n_passengers_ashore"] += n_pax
        cell["n_crew_ashore"] += n_crew
    return totals


def _calls_by_port(voyage: Voyage) -> dict[str, list[PortCall]]:
    by_port: dict[str, list[PortCall]] = {}
    for call in voyage.port_calls:
        by_port.setdefault(call.port_id, []).append(call)
    return by_port


def onsets_per_epoch(
    cases: Sequence[ClinicalCase],
    observation_end_epoch: int,
) -> tuple[int, ...]:
    """Onset counts per epoch, index 0 = epoch 1 (the renewal input)."""
    counts = [0] * max(0, int(observation_end_epoch))
    for case in cases:
        idx = case.onset_epoch - 1
        if 0 <= idx < len(counts):
            counts[idx] += 1
    return tuple(counts)


def _stratum_cases(
    cases: Sequence[ClinicalCase],
    voyage: Voyage,
    incubation: DelayDistribution,
) -> tuple[dict[tuple[str, str], float], dict[tuple[str, str], int]]:
    """Fractional and modal case attribution keyed by ``(port_id, stratum)``."""
    expected: dict[tuple[str, str], float] = {}
    modal: dict[tuple[str, str], int] = {}
    for case in cases:
        weights = import_attribution_weights(case, voyage, incubation)
        if not weights:
            continue
        stratum = CREW_ASHORE if case.crew else PAX_ASHORE
        for port_id, weight in weights.items():
            key = (port_id, stratum)
            expected[key] = expected.get(key, 0.0) + weight
        best = max(weights.items(), key=lambda kv: (kv[1], kv[0]))[0]
        modal[(best, stratum)] = modal.get((best, stratum), 0) + 1
    return expected, modal


def _baseline_cells(
    voyage: Voyage,
    bundle: ObservationBundle,
    totals: Mapping[str, Mapping[str, float]],
) -> tuple[BaselineCell, ...]:
    voyage_hours = voyage.observation_end_epoch * voyage.epoch_duration_hours
    ashore_pax_hours = sum(
        float(cell.get("person_hours_passenger", 0.0)) for cell in totals.values()
    )
    ashore_crew_hours = sum(
        float(cell.get("person_hours_crew", 0.0)) for cell in totals.values()
    )
    aboard_cases = {PAX_ABOARD: 0, CREW_ABOARD: 0}
    for case in bundle.clinical_cases:
        if case.went_ashore:
            continue
        aboard_cases[CREW_ABOARD if case.crew else PAX_ABOARD] += 1
    n_pax = bundle.n_passengers or voyage.n_passengers
    n_crew = bundle.n_crew or voyage.n_crew
    return (
        BaselineCell(
            voyage_id=voyage.voyage_id,
            ship_id=voyage.ship_id,
            stratum=PAX_ABOARD,
            n_persons=int(n_pax),
            person_hours_aboard=max(0.0, n_pax * voyage_hours - ashore_pax_hours),
            cases=aboard_cases[PAX_ABOARD],
        ),
        BaselineCell(
            voyage_id=voyage.voyage_id,
            ship_id=voyage.ship_id,
            stratum=CREW_ABOARD,
            n_persons=int(n_crew),
            person_hours_aboard=max(0.0, n_crew * voyage_hours - ashore_crew_hours),
            cases=aboard_cases[CREW_ABOARD],
        ),
    )


def build_exposure_design(
    voyage: Voyage,
    bundle: ObservationBundle,
    incubation: DelayDistribution,
    *,
    ascertainment: float = 1.0,
) -> ExposureDesign:
    """Assemble the exposure cells, baselines, and onset curve for one voyage.

    Denominators come from ``bundle.exposure_totals`` when the run recorded them
    (synthetic voyages) and from the itinerary reconstruction otherwise.
    """
    if not 0.0 < float(ascertainment) <= 1.0:
        raise ValueError(f"ascertainment must be in (0, 1]: {ascertainment}")
    end_epoch = int(bundle.observation_end_epoch or voyage.observation_end_epoch)
    totals: Mapping[str, Mapping[str, float]] = (
        bundle.exposure_totals or derived_exposure_totals(voyage)
    )
    expected, modal = _stratum_cases(bundle.clinical_cases, voyage, incubation)

    cells: list[ExposureCell] = []
    for port_id, calls in _calls_by_port(voyage).items():
        cell_totals = totals.get(port_id) or {}
        # Hours are ledgered per port_id, so repeat calls within one voyage are
        # pooled; censoring follows the last of them, the exposure that is
        # hardest to observe. Repeat visits separate across voyages, by
        # port_visit_key, which is where the fleet hierarchy needs them.
        last_call = calls[-1]
        remaining = censoring_epochs_after(voyage, last_call)
        observed = observed_onset_fraction(remaining, incubation)
        for stratum in (PAX_ASHORE, CREW_ASHORE):
            hours = float(cell_totals.get(_HOURS_KEY[stratum], 0.0))
            n_persons = int(round(float(cell_totals.get(_COUNT_KEY[stratum], 0.0))))
            key = (port_id, stratum)
            cells.append(
                ExposureCell(
                    voyage_id=voyage.voyage_id,
                    ship_id=voyage.ship_id,
                    port_id=port_id,
                    port_visit_key=last_call.visit_key,
                    stratum=stratum,
                    n_calls=len(calls),
                    n_persons=n_persons,
                    person_hours_ashore=hours,
                    cases=modal.get(key, 0),
                    expected_cases=round(expected.get(key, 0.0), 6),
                    censor_epochs_remaining=remaining,
                    observed_fraction=observed,
                    ascertainment=float(ascertainment),
                ),
            )
    return ExposureDesign(
        voyage_id=voyage.voyage_id,
        ship_id=voyage.ship_id,
        observation_end_epoch=end_epoch,
        epoch_duration_hours=voyage.epoch_duration_hours,
        port_cells=tuple(cells),
        baseline_cells=_baseline_cells(voyage, bundle, totals),
        onsets_by_epoch=onsets_per_epoch(bundle.clinical_cases, end_epoch),
        ascertainment=float(ascertainment),
    )
