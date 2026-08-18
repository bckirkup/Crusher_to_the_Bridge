"""What a port's own public health system sees, independently of any ship.

The sentinel model infers a port hazard from ship data. Validating that number
needs a signal the ship did not produce, and a port authority is exactly that:
the same community prevalence that infects a passenger ashore also drives the
port's syndromic reports and its municipal wastewater. If the inferred hazard
tracks the port's signal the method is validated; where the port has no signal
at all, the ship is the only instrument there is.

**Every port generates every channel, always.** Capability is metadata, not a
generation switch (:func:`generate_port_signals` never returns ``None`` for a
signal). A port with no municipal WBE programme still gets a
``wbe_gc_per_l_observed``, because the sewage exists whether or not anyone is
sampling it, and the counterfactual is the whole point of the gap analysis:
"what would Cozumel have seen if it ran what Miami runs". Suppression happens at
fleet-analysis time through :func:`ablate_state` / :func:`ablate_series`, where
the ablation is a stated analysis choice rather than a hole burned into the data.

The chain from truth to signal::

    prevalence          = hazard_per_person_hour / hazard_per_prevalence_hour
    incidence/100k/day  = prevalence / infectious_days * 1e5
    ascertained cases   = Binomial(incidence, syndromic_coverage)   [delayed]
    gc/L                = prevalence * gc_per_person_day / l_per_person_day
    observed gc/L       = 10 ** (log10(gc/L) + N(0, log10_noise_sd))
    wbe detected        = observed gc/L >= lod_gc_per_l

The municipal denominator (~200 L/person/day) is an order of magnitude larger
than a ship's holding tank (30 L/person/day of blackwater, see
:mod:`wastewater_assays`), which is why a port needs a far lower LOD than a ship
to see the same prevalence.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

# --- reporting pathways and alert levels ---------------------------------

REPORT_CDC_VSP = "CDC_VSP"
REPORT_CARPHA = "CARPHA"
REPORT_ECDC = "ECDC"
REPORT_WHO_IHR = "WHO_IHR"
REPORT_LOCAL_ONLY = "local_only"
REPORTING_PATHWAYS: tuple[str, ...] = (
    REPORT_CDC_VSP,
    REPORT_CARPHA,
    REPORT_ECDC,
    REPORT_WHO_IHR,
    REPORT_LOCAL_ONLY,
)

ALERT_NORMAL = "normal"
ALERT_ELEVATED = "elevated"
ALERT_OUTBREAK = "outbreak"
# Not "normal": a port with every channel ablated knows nothing, and recording
# that as quiet is how a surveillance desert gets mistaken for a clean bill.
ALERT_UNKNOWN = "unknown"
ALERT_LEVELS: tuple[str, ...] = (
    ALERT_NORMAL,
    ALERT_ELEVATED,
    ALERT_OUTBREAK,
    ALERT_UNKNOWN,
)

CHANNEL_SYNDROMIC = "syndromic"
CHANNEL_WBE = "wbe"
CHANNEL_LAB = "lab"
CHANNEL_GENOTYPING = "genotyping"
CHANNELS: tuple[str, ...] = (
    CHANNEL_SYNDROMIC,
    CHANNEL_WBE,
    CHANNEL_LAB,
    CHANNEL_GENOTYPING,
)

# --- calibration defaults ------------------------------------------------

# Shared with the shipboard assay layer so a port and a ship at the same
# prevalence differ only by their dilution and their instrument.
DEFAULT_SHEDDING_GC_PER_PERSON_DAY = 1.0e10
DEFAULT_MUNICIPAL_L_PER_PERSON_DAY = 200.0
DEFAULT_WBE_LOD_GC_PER_L = 100.0
DEFAULT_WBE_LOG10_NOISE_SD = 0.5
DEFAULT_INFECTIOUS_DAYS = 2.0
# Hazard per person-hour ashore at 100% community prevalence: ~2 community
# contacts per hour ashore at ~5% transmission per contact. The sentinel
# estimator's λ_p is per person-hour, so this constant is the whole of the link
# between an inferred hazard and a community prevalence, and it is stated here
# rather than buried because every correlation against a port signal inherits
# it. At 0.1, the scan's hazard ladder (1e-4 … 0.015 per person-hour) maps to
# 0.1% … 15% community prevalence, i.e. background to frank outbreak.
DEFAULT_HAZARD_PER_PREVALENCE_HOUR = 0.1
DEFAULT_LAB_CONFIRMATION_FRACTION = 0.5
DEFAULT_SYNDROMIC_COVERAGE = 0.5
DEFAULT_SYNDROMIC_DELAY_DAYS = 3
DEFAULT_WBE_FREQUENCY_DAYS = 7.0
DEFAULT_LAB_TURNAROUND_DAYS = 2.0
PER_100K = 100_000.0


def _positive(name: str, value: float) -> float:
    if value <= 0.0:
        raise ValueError(f"{name} must be positive: {value}")
    return float(value)


def _fraction(name: str, value: float) -> float:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0, 1]: {value}")
    return float(value)


@dataclass(frozen=True)
class PrevalenceLink:
    """Truth-side conversions shared by the ship exposure and the port signals.

    One object because the whole validation argument rests on both sides being
    driven by the *same* latent prevalence: if the hazard-to-prevalence constant
    used to generate a port signal differed from the one used to interpret the
    sentinel posterior, the correlation would be an artefact of the mismatch.
    """

    hazard_per_prevalence_hour: float = DEFAULT_HAZARD_PER_PREVALENCE_HOUR
    infectious_days: float = DEFAULT_INFECTIOUS_DAYS
    gc_per_person_day: float = DEFAULT_SHEDDING_GC_PER_PERSON_DAY
    municipal_l_per_person_day: float = DEFAULT_MUNICIPAL_L_PER_PERSON_DAY

    def __post_init__(self) -> None:
        _positive("hazard_per_prevalence_hour", self.hazard_per_prevalence_hour)
        _positive("infectious_days", self.infectious_days)
        _positive("gc_per_person_day", self.gc_per_person_day)
        _positive("municipal_l_per_person_day", self.municipal_l_per_person_day)

    def prevalence_from_hazard(self, hazard_per_person_hour: float) -> float:
        """Community prevalence implied by a shore hazard (capped at 1)."""
        share = max(float(hazard_per_person_hour), 0.0) / self.hazard_per_prevalence_hour
        return min(share, 1.0)

    def hazard_from_prevalence(self, prevalence: float) -> float:
        """The inverse: what shore hazard a community prevalence produces."""
        return max(float(prevalence), 0.0) * self.hazard_per_prevalence_hour

    def incidence_per_100k_day(self, prevalence: float) -> float:
        """Daily incidence per 100 000, from prevalence and infectious duration."""
        return max(float(prevalence), 0.0) / self.infectious_days * PER_100K

    def gc_per_l(self, prevalence: float) -> float:
        """Municipal influent concentration at a community prevalence."""
        return (
            max(float(prevalence), 0.0)
            * self.gc_per_person_day
            / self.municipal_l_per_person_day
        )

    @classmethod
    def from_mapping(cls, block: Mapping[str, Any] | None) -> PrevalenceLink:
        cfg = dict(block or {})
        return cls(
            hazard_per_prevalence_hour=float(
                cfg.get(
                    "hazard_per_prevalence_hour", DEFAULT_HAZARD_PER_PREVALENCE_HOUR,
                ),
            ),
            infectious_days=float(cfg.get("infectious_days", DEFAULT_INFECTIOUS_DAYS)),
            gc_per_person_day=float(
                cfg.get("gc_per_person_day", DEFAULT_SHEDDING_GC_PER_PERSON_DAY),
            ),
            municipal_l_per_person_day=float(
                cfg.get(
                    "municipal_l_per_person_day", DEFAULT_MUNICIPAL_L_PER_PERSON_DAY,
                ),
            ),
        )


@dataclass(frozen=True)
class AlertThresholds:
    """Where a reported rate stops being background.

    Rates are *reported* per 100 000 per day, so a port with low ascertainment
    escalates later than a port with high ascertainment at the same true
    prevalence. That asymmetry is a finding, not a bug to normalize away.

    The defaults sit either side of the scan's background hazard: at 0.1%
    community prevalence and a 2-day infectious period the true incidence is
    50/100k/day, so a well-ascertaining port reads ~30 and stays ``normal``,
    while a decade above background reads in the hundreds and is an outbreak.
    """

    elevated_rate_per_100k: float = 50.0
    outbreak_rate_per_100k: float = 200.0
    # Municipal WBE escalates on *concentration*, not on detection: at the
    # municipal dilution a norovirus qPCR assay detects background prevalence
    # every single day, so "detected" carries no alerting information and only a
    # rise above this level does. 1e6 gc/L is ~2% community prevalence.
    wbe_elevated_gc_per_l: float = 1.0e6
    wbe_escalation_enabled: bool = True

    def __post_init__(self) -> None:
        if self.elevated_rate_per_100k <= 0.0:
            raise ValueError("elevated_rate_per_100k must be positive")
        if self.outbreak_rate_per_100k <= self.elevated_rate_per_100k:
            raise ValueError("outbreak_rate_per_100k must exceed elevated")
        if self.wbe_elevated_gc_per_l <= 0.0:
            raise ValueError("wbe_elevated_gc_per_l must be positive")

    @classmethod
    def from_mapping(cls, block: Mapping[str, Any] | None) -> AlertThresholds:
        cfg = dict(block or {})
        return cls(
            elevated_rate_per_100k=float(cfg.get("elevated_rate_per_100k", 50.0)),
            outbreak_rate_per_100k=float(cfg.get("outbreak_rate_per_100k", 200.0)),
            wbe_elevated_gc_per_l=float(cfg.get("wbe_elevated_gc_per_l", 1.0e6)),
            wbe_escalation_enabled=bool(cfg.get("wbe_escalation_enabled", True)),
        )


@dataclass(frozen=True)
class PortSurveillanceCapability:
    """What a port authority *would* report, and through which pathway.

    Every field here is metadata on the generated signals rather than a gate on
    generating them, so a capability profile can be edited (or ablated) without
    re-running any simulation.
    """

    port_id: str
    port_name: str
    region: str
    population: int
    syndromic_enabled: bool = True
    syndromic_delay_days: int = DEFAULT_SYNDROMIC_DELAY_DAYS
    syndromic_coverage: float = DEFAULT_SYNDROMIC_COVERAGE
    syndromic_pathogens: tuple[str, ...] = ()
    wbe_enabled: bool = False
    wbe_assay: str | None = None
    wbe_frequency_days: float = DEFAULT_WBE_FREQUENCY_DAYS
    wbe_pathogens: tuple[str, ...] = ()
    wbe_lod_gc_per_l: float = DEFAULT_WBE_LOD_GC_PER_L
    lab_confirmation: bool = False
    lab_turnaround_days: float = DEFAULT_LAB_TURNAROUND_DAYS
    lab_confirmation_fraction: float = DEFAULT_LAB_CONFIRMATION_FRACTION
    genotyping_available: bool = False
    reports_to: str = REPORT_LOCAL_ONLY
    reporting_threshold: str | None = None
    cruise_arrival_screening: bool = False
    departure_health_cert: bool = False
    wbe_log10_noise_sd: float = DEFAULT_WBE_LOG10_NOISE_SD
    thresholds: AlertThresholds = field(default_factory=AlertThresholds)

    def __post_init__(self) -> None:
        if not self.port_id:
            raise ValueError("port_id is required")
        if self.population < 1:
            raise ValueError(f"population must be >= 1: {self.population}")
        _fraction("syndromic_coverage", self.syndromic_coverage)
        _fraction("lab_confirmation_fraction", self.lab_confirmation_fraction)
        _positive("wbe_frequency_days", self.wbe_frequency_days)
        _positive("wbe_lod_gc_per_l", self.wbe_lod_gc_per_l)
        if self.syndromic_delay_days < 0:
            raise ValueError("syndromic_delay_days must be >= 0")
        if self.lab_turnaround_days < 0.0:
            raise ValueError("lab_turnaround_days must be >= 0")
        if self.wbe_log10_noise_sd < 0.0:
            raise ValueError("wbe_log10_noise_sd must be >= 0")
        if self.reports_to not in REPORTING_PATHWAYS:
            raise ValueError(
                f"unknown reports_to {self.reports_to!r}; "
                f"known: {list(REPORTING_PATHWAYS)}",
            )

    def reports_syndromic(self, pathogen: str) -> bool:
        """Would this authority report this pathogen's cases at all?

        An empty pathogen list means "everything reportable": a profile that
        omits the list is under-specified, not silently mute.
        """
        if not self.syndromic_enabled:
            return False
        return not self.syndromic_pathogens or pathogen in self.syndromic_pathogens

    def tests_wastewater(self, pathogen: str) -> bool:
        """Would this authority's WBE programme cover this pathogen?"""
        if not self.wbe_enabled:
            return False
        return not self.wbe_pathogens or pathogen in self.wbe_pathogens

    def samples_on_day(self, day_index: int) -> bool:
        """WBE cadence: which days a sample would have been drawn."""
        every = max(int(round(self.wbe_frequency_days)), 1)
        return int(day_index) % every == 0

    def supports(self, channel: str, pathogen: str) -> bool:
        """Whether an ablation that respects capability keeps ``channel``."""
        if channel == CHANNEL_SYNDROMIC:
            return self.reports_syndromic(pathogen)
        if channel == CHANNEL_WBE:
            return self.tests_wastewater(pathogen)
        if channel == CHANNEL_LAB:
            return bool(self.lab_confirmation)
        if channel == CHANNEL_GENOTYPING:
            return bool(self.genotyping_available)
        raise ValueError(f"unknown channel {channel!r}; known: {list(CHANNELS)}")

    def to_metadata(self) -> dict[str, Any]:
        """Flat capability record for a factorial analysis table."""
        return {
            "port_id": self.port_id,
            "port_name": self.port_name,
            "region": self.region,
            "population": int(self.population),
            "syndromic_enabled": bool(self.syndromic_enabled),
            "syndromic_delay_days": int(self.syndromic_delay_days),
            "syndromic_coverage": float(self.syndromic_coverage),
            "wbe_enabled": bool(self.wbe_enabled),
            "wbe_assay": self.wbe_assay,
            "wbe_frequency_days": float(self.wbe_frequency_days),
            "wbe_lod_gc_per_l": float(self.wbe_lod_gc_per_l),
            "lab_confirmation": bool(self.lab_confirmation),
            "lab_turnaround_days": float(self.lab_turnaround_days),
            "genotyping_available": bool(self.genotyping_available),
            "reports_to": self.reports_to,
            "reporting_threshold": self.reporting_threshold,
            "cruise_arrival_screening": bool(self.cruise_arrival_screening),
            "departure_health_cert": bool(self.departure_health_cert),
        }

    @classmethod
    def from_mapping(
        cls,
        block: Mapping[str, Any],
        *,
        port_id: str | None = None,
    ) -> PortSurveillanceCapability:
        """Build from a profile entry; missing keys fall back to the defaults."""
        cfg = dict(block)
        pid = str(port_id or cfg.get("port_id") or "")
        return cls(
            port_id=pid,
            port_name=str(cfg.get("port_name") or pid),
            region=str(cfg.get("region") or ""),
            population=int(cfg.get("population") or 1),
            syndromic_enabled=bool(cfg.get("syndromic_enabled", True)),
            syndromic_delay_days=int(
                cfg.get("syndromic_delay_days") or DEFAULT_SYNDROMIC_DELAY_DAYS,
            ),
            syndromic_coverage=float(
                cfg.get("syndromic_coverage", DEFAULT_SYNDROMIC_COVERAGE),
            ),
            syndromic_pathogens=tuple(
                str(p) for p in (cfg.get("syndromic_pathogens") or ())
            ),
            wbe_enabled=bool(cfg.get("wbe_enabled", False)),
            wbe_assay=(
                None if cfg.get("wbe_assay") is None else str(cfg["wbe_assay"])
            ),
            wbe_frequency_days=float(
                cfg.get("wbe_frequency_days") or DEFAULT_WBE_FREQUENCY_DAYS,
            ),
            wbe_pathogens=tuple(str(p) for p in (cfg.get("wbe_pathogens") or ())),
            wbe_lod_gc_per_l=float(
                cfg.get("wbe_lod_gc_per_L")
                or cfg.get("wbe_lod_gc_per_l")
                or DEFAULT_WBE_LOD_GC_PER_L,
            ),
            lab_confirmation=bool(cfg.get("lab_confirmation", False)),
            lab_turnaround_days=float(
                cfg.get("lab_turnaround_days") or DEFAULT_LAB_TURNAROUND_DAYS,
            ),
            lab_confirmation_fraction=float(
                cfg.get("lab_confirmation_fraction", DEFAULT_LAB_CONFIRMATION_FRACTION),
            ),
            genotyping_available=bool(cfg.get("genotyping_available", False)),
            reports_to=str(cfg.get("reports_to") or REPORT_LOCAL_ONLY),
            reporting_threshold=(
                None
                if cfg.get("reporting_threshold") is None
                else str(cfg["reporting_threshold"])
            ),
            cruise_arrival_screening=bool(cfg.get("cruise_arrival_screening", False)),
            departure_health_cert=bool(cfg.get("departure_health_cert", False)),
            wbe_log10_noise_sd=float(
                cfg.get("wbe_log10_noise_sd", DEFAULT_WBE_LOG10_NOISE_SD),
            ),
            thresholds=AlertThresholds.from_mapping(cfg.get("alert_thresholds")),
        )


@dataclass(frozen=True)
class PortEpidemiologicalState:
    """One port, one pathogen, one day: the truth and every observable signal.

    Signals are ``None`` only after :func:`ablate_state`. Straight out of
    generation they are all populated, including for ports that run no
    programme, because the counterfactual is what quantifies the gap.
    """

    port_id: str
    pathogen: str
    day_index: int
    observation_date: str
    true_community_prevalence: float
    true_incidence_per_100k_day: float
    true_ww_gc_per_l: float
    syndromic_cases_reported: int | None
    syndromic_rate_per_100k: float | None
    syndromic_report_date: str | None
    wbe_sampled: bool
    wbe_gc_per_l_observed: float | None
    wbe_detected: bool | None
    lab_confirmed_cases: int | None
    lab_result_date: str | None
    genotype: str | None
    alert_level: str
    reports_to: str
    reporting_threshold: str | None
    syndromic_capable: bool
    wbe_capable: bool
    lab_capable: bool
    genotyping_capable: bool

    def as_row(self) -> dict[str, Any]:
        """JSON-ready record (schema: ``schemas/port_surveillance.schema.json``)."""
        return {
            "port_id": self.port_id,
            "pathogen": self.pathogen,
            "day_index": int(self.day_index),
            "observation_date": self.observation_date,
            "true_community_prevalence": float(self.true_community_prevalence),
            "true_incidence_per_100k_day": float(self.true_incidence_per_100k_day),
            "true_ww_gc_per_l": float(self.true_ww_gc_per_l),
            "syndromic_cases_reported": self.syndromic_cases_reported,
            "syndromic_rate_per_100k": self.syndromic_rate_per_100k,
            "syndromic_report_date": self.syndromic_report_date,
            "wbe_sampled": bool(self.wbe_sampled),
            "wbe_gc_per_l_observed": self.wbe_gc_per_l_observed,
            "wbe_detected": self.wbe_detected,
            "lab_confirmed_cases": self.lab_confirmed_cases,
            "lab_result_date": self.lab_result_date,
            "genotype": self.genotype,
            "alert_level": self.alert_level,
            "reports_to": self.reports_to,
            "reporting_threshold": self.reporting_threshold,
            "syndromic_capable": bool(self.syndromic_capable),
            "wbe_capable": bool(self.wbe_capable),
            "lab_capable": bool(self.lab_capable),
            "genotyping_capable": bool(self.genotyping_capable),
        }


def _iso(start: date | None, day_index: int, offset_days: float = 0.0) -> str | None:
    if start is None:
        return None
    return (start + timedelta(days=int(day_index) + int(round(offset_days)))).isoformat()


def _syndromic_signal(
    capability: PortSurveillanceCapability,
    incidence_cases: float,
    rng: np.random.Generator,
) -> tuple[int, float]:
    """Ascertained cases and their reported rate per 100 000."""
    expected = max(incidence_cases, 0.0)
    # Poisson on the true count, then binomial ascertainment: the count itself
    # is random, and a fixed round() would suppress exactly the low-incidence
    # variance that decides whether a small port ever crosses a threshold.
    true_cases = int(rng.poisson(expected))
    observed = int(rng.binomial(true_cases, capability.syndromic_coverage))
    rate = observed / capability.population * PER_100K
    return observed, rate


def _wbe_signal(
    capability: PortSurveillanceCapability,
    true_gc_per_l: float,
    rng: np.random.Generator,
) -> tuple[float, bool]:
    """Lognormal measurement noise on the influent concentration, then the LOD."""
    floor = 1e-3
    log10_true = math.log10(max(true_gc_per_l, floor))
    noise = (
        float(rng.normal(0.0, capability.wbe_log10_noise_sd))
        if capability.wbe_log10_noise_sd > 0.0
        else 0.0
    )
    observed = float(10.0 ** (log10_true + noise))
    return observed, observed >= capability.wbe_lod_gc_per_l


def alert_level_for(
    capability: PortSurveillanceCapability,
    *,
    syndromic_rate_per_100k: float | None,
    wbe_gc_per_l: float | None,
) -> str:
    """Escalate on what the authority can actually see.

    With no channel left the level is ``unknown`` rather than ``normal``: an
    ablated port has no evidence of quiet, only an absence of evidence.
    """
    if syndromic_rate_per_100k is None and wbe_gc_per_l is None:
        return ALERT_UNKNOWN
    thresholds = capability.thresholds
    if syndromic_rate_per_100k is not None:
        if syndromic_rate_per_100k >= thresholds.outbreak_rate_per_100k:
            return ALERT_OUTBREAK
        if syndromic_rate_per_100k >= thresholds.elevated_rate_per_100k:
            return ALERT_ELEVATED
    escalates = (
        wbe_gc_per_l is not None
        and thresholds.wbe_escalation_enabled
        and wbe_gc_per_l >= thresholds.wbe_elevated_gc_per_l
    )
    return ALERT_ELEVATED if escalates else ALERT_NORMAL


def generate_port_signals(
    capability: PortSurveillanceCapability,
    *,
    pathogen: str,
    true_prevalence: float,
    day_index: int,
    rng: np.random.Generator,
    link: PrevalenceLink | None = None,
    start_date: date | None = None,
    genotype: str | None = None,
) -> PortEpidemiologicalState:
    """One day of signals for one port — all channels, capability aside.

    ``true_prevalence`` is the latent community prevalence that also drives the
    ship's shore exposure, so the ship-side and port-side observations are two
    views of one number rather than two independent draws.
    """
    model = link or PrevalenceLink()
    prevalence = min(max(float(true_prevalence), 0.0), 1.0)
    incidence_rate = model.incidence_per_100k_day(prevalence)
    incidence_cases = incidence_rate / PER_100K * capability.population
    cases, rate = _syndromic_signal(capability, incidence_cases, rng)
    true_gc = model.gc_per_l(prevalence)
    observed_gc, detected = _wbe_signal(capability, true_gc, rng)
    sampled = capability.samples_on_day(day_index)
    confirmed = int(rng.binomial(cases, capability.lab_confirmation_fraction))
    return PortEpidemiologicalState(
        port_id=capability.port_id,
        pathogen=str(pathogen),
        day_index=int(day_index),
        observation_date=_iso(start_date, day_index) or "",
        true_community_prevalence=prevalence,
        true_incidence_per_100k_day=incidence_rate,
        true_ww_gc_per_l=true_gc,
        syndromic_cases_reported=cases,
        syndromic_rate_per_100k=rate,
        syndromic_report_date=_iso(
            start_date, day_index, capability.syndromic_delay_days,
        ),
        wbe_sampled=sampled,
        wbe_gc_per_l_observed=observed_gc,
        wbe_detected=detected,
        lab_confirmed_cases=confirmed,
        lab_result_date=_iso(start_date, day_index, capability.lab_turnaround_days),
        genotype=genotype,
        # An authority escalates on assays it actually ran: off-cadence days
        # carry the counterfactual concentration but cannot raise an alert.
        alert_level=alert_level_for(
            capability,
            syndromic_rate_per_100k=rate,
            wbe_gc_per_l=observed_gc if sampled else None,
        ),
        reports_to=capability.reports_to,
        reporting_threshold=capability.reporting_threshold,
        syndromic_capable=capability.reports_syndromic(pathogen),
        wbe_capable=capability.tests_wastewater(pathogen),
        lab_capable=bool(capability.lab_confirmation),
        genotyping_capable=bool(capability.genotyping_available),
    )


def generate_port_series(
    capability: PortSurveillanceCapability,
    *,
    pathogen: str,
    prevalence_by_day: Sequence[float],
    rng: np.random.Generator,
    link: PrevalenceLink | None = None,
    start_date: date | None = None,
    genotype: str | None = None,
) -> tuple[PortEpidemiologicalState, ...]:
    """A port's whole time series, one state per day of the prevalence curve."""
    return tuple(
        generate_port_signals(
            capability,
            pathogen=pathogen,
            true_prevalence=prevalence,
            day_index=index,
            rng=rng,
            link=link,
            start_date=start_date,
            genotype=genotype,
        )
        for index, prevalence in enumerate(prevalence_by_day)
    )


# --- analysis-time ablation ----------------------------------------------

_SYNDROMIC_FIELDS = (
    "syndromic_cases_reported",
    "syndromic_rate_per_100k",
    "syndromic_report_date",
)
_WBE_FIELDS = ("wbe_gc_per_l_observed", "wbe_detected")
_LAB_FIELDS = ("lab_confirmed_cases", "lab_result_date")
_GENOTYPE_FIELDS = ("genotype",)

_CHANNEL_FIELDS: dict[str, tuple[str, ...]] = {
    CHANNEL_SYNDROMIC: _SYNDROMIC_FIELDS,
    CHANNEL_WBE: _WBE_FIELDS,
    CHANNEL_LAB: _LAB_FIELDS,
    CHANNEL_GENOTYPING: _GENOTYPE_FIELDS,
}


def resolve_channels(channels: Iterable[str] | None) -> tuple[str, ...]:
    """Normalize and validate a channel selection (``None`` keeps everything)."""
    if channels is None:
        return CHANNELS
    resolved = tuple(str(c).strip().lower() for c in channels)
    unknown = [c for c in resolved if c not in CHANNELS]
    if unknown:
        raise ValueError(f"unknown port channels {unknown}; known: {list(CHANNELS)}")
    return resolved


def ablate_state(
    state: PortEpidemiologicalState,
    capability: PortSurveillanceCapability,
    *,
    channels: Iterable[str] | None = None,
    respect_capability: bool = True,
) -> PortEpidemiologicalState:
    """Suppress the channels this analysis is not using, and re-derive the alert.

    Two independent switches, because they answer different questions.
    ``channels`` is the analyst's ablation ("what does the fleet fit look like
    without municipal WBE anywhere?"). ``respect_capability`` is the realism
    filter ("what do these ports actually run?"). Truth fields are never
    ablated — they are the ground truth the comparison is against, and they were
    never observable in the first place.
    """
    kept = resolve_channels(channels)
    updates: dict[str, Any] = {}
    for channel, fields in _CHANNEL_FIELDS.items():
        available = channel in kept and (
            not respect_capability or capability.supports(channel, state.pathogen)
        )
        if available:
            continue
        for name in fields:
            updates[name] = None
    masked = replace(state, **updates)
    return replace(
        masked,
        alert_level=alert_level_for(
            capability,
            syndromic_rate_per_100k=masked.syndromic_rate_per_100k,
            wbe_gc_per_l=(
                masked.wbe_gc_per_l_observed if masked.wbe_sampled else None
            ),
        ),
    )


def ablate_series(
    states: Sequence[PortEpidemiologicalState],
    capability: PortSurveillanceCapability,
    *,
    channels: Iterable[str] | None = None,
    respect_capability: bool = True,
) -> tuple[PortEpidemiologicalState, ...]:
    """:func:`ablate_state` over a port's series."""
    return tuple(
        ablate_state(
            state,
            capability,
            channels=channels,
            respect_capability=respect_capability,
        )
        for state in states
    )


def state_from_dict(raw: Mapping[str, Any]) -> PortEpidemiologicalState:
    """Rebuild a state from its row, for analysis of a written ledger."""
    row = dict(raw)
    return PortEpidemiologicalState(
        port_id=str(row["port_id"]),
        pathogen=str(row["pathogen"]),
        day_index=int(row["day_index"]),
        observation_date=str(row.get("observation_date") or ""),
        true_community_prevalence=float(row["true_community_prevalence"]),
        true_incidence_per_100k_day=float(row["true_incidence_per_100k_day"]),
        true_ww_gc_per_l=float(row["true_ww_gc_per_l"]),
        syndromic_cases_reported=_optional_int(row, "syndromic_cases_reported"),
        syndromic_rate_per_100k=_optional_float(row, "syndromic_rate_per_100k"),
        syndromic_report_date=_optional_str(row, "syndromic_report_date"),
        wbe_sampled=bool(row.get("wbe_sampled", False)),
        wbe_gc_per_l_observed=_optional_float(row, "wbe_gc_per_l_observed"),
        wbe_detected=(
            None if row.get("wbe_detected") is None else bool(row["wbe_detected"])
        ),
        lab_confirmed_cases=_optional_int(row, "lab_confirmed_cases"),
        lab_result_date=_optional_str(row, "lab_result_date"),
        genotype=_optional_str(row, "genotype"),
        alert_level=_resolve_alert_level(row.get("alert_level")),
        reports_to=str(row.get("reports_to") or REPORT_LOCAL_ONLY),
        reporting_threshold=_optional_str(row, "reporting_threshold"),
        syndromic_capable=bool(row.get("syndromic_capable", False)),
        wbe_capable=bool(row.get("wbe_capable", False)),
        lab_capable=bool(row.get("lab_capable", False)),
        genotyping_capable=bool(row.get("genotyping_capable", False)),
    )


def _optional_float(row: Mapping[str, Any], key: str) -> float | None:
    value = row.get(key)
    return None if value is None else float(value)


def _optional_int(row: Mapping[str, Any], key: str) -> int | None:
    value = row.get(key)
    return None if value is None else int(value)


def _optional_str(row: Mapping[str, Any], key: str) -> str | None:
    value = row.get(key)
    return None if value is None else str(value)


def _resolve_alert_level(value: object) -> str:
    level = str(value or ALERT_UNKNOWN).strip().lower()
    if level not in ALERT_LEVELS:
        raise ValueError(f"unknown alert_level {level!r}; known: {list(ALERT_LEVELS)}")
    return level
