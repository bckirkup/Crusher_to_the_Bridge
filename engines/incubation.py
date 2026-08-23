"""Incubation periods drawn from a distribution, not scheduled on a fixed day.

A pathogen's incubation period is a distribution with a literature median and
dispersion, shortened by a larger inoculum and lengthened by host biology. A
single onset day per pathogen collapses all three, which makes every host
present on the same day and leaves the faster half of a variant's incubation
phenotype with nowhere to move.

Everything here is host and pathogen biology. The assay side of detection
timing (turnaround, sampling cadence) belongs to the observation modalities.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np

DISTRIBUTION_LOGNORMAL = "lognormal"
DISTRIBUTION_GAMMA = "gamma"
SUPPORTED_DISTRIBUTIONS = (DISTRIBUTION_LOGNORMAL, DISTRIBUTION_GAMMA)

DEFAULT_DISPERSION = 1.5
DEFAULT_MIN_DAYS = 0.5
DEFAULT_MAX_DAYS = 30.0
DEFAULT_DOSE_REFERENCE_LOG10 = 4.0

# A dose term is a modest shift of the median, not a licence to abolish the
# incubation period: bounds keep an extreme inoculum (or a near-threshold one)
# from producing same-day onset or a month-long silent period. The lower bound
# is the spec's per-pathogen ``dose_floor``; this is its default.
MIN_DOSE_FACTOR = 0.4
MAX_DOSE_FACTOR = 2.5

_DOSE_FLOOR = 1e-9

_INCUBATION_KEYS = frozenset({
    "distribution", "median_days", "dispersion", "min_days", "max_days",
    "dose_reference_log10", "dose_log10_shortening", "dose_floor",
    "host_factors", "notes",
})
_HOST_FACTOR_KEYS = frozenset({
    "immunocompromised", "prior_immunity", "age_bands",
})


def _reject_unknown_keys(
    where: str,
    cfg: Mapping[str, Any],
    allowed: frozenset[str],
) -> None:
    """Refuse config keys this model does not read.

    A misspelled parameter would otherwise fall back to a default and shift
    onset timing invisibly, which is the one failure mode a profile author
    cannot see in the output.
    """
    unknown = sorted(set(cfg) - allowed)
    if unknown:
        raise ValueError(f"{where} has unknown keys: {unknown}")


@dataclass(frozen=True)
class HostIncubationState:
    """The host attributes an incubation draw is conditioned on.

    Deliberately small: these are the three host axes the ship population
    actually carries. An attribute the simulator cannot supply is left at its
    neutral value rather than invented, so an unpopulated axis is inert instead
    of quietly biasing onset.
    """

    age_band: str = ""
    immunocompromised: bool = False
    prior_immunity: bool = False


@dataclass(frozen=True)
class HostIncubationFactors:
    """Multipliers on the incubation median, per host axis.

    Values above one lengthen the incubation period. Immunosuppression and
    partial immunity both delay recognisable illness rather than accelerating
    it, which matters for surveillance: those hosts shed while still
    presenting as well.
    """

    immunocompromised: float = 1.0
    prior_immunity: float = 1.0
    age_bands: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_positive("host_factors.immunocompromised", self.immunocompromised)
        _require_positive("host_factors.prior_immunity", self.prior_immunity)
        for band, value in self.age_bands.items():
            _require_positive(f"host_factors.age_bands.{band}", value)

    @classmethod
    def from_mapping(cls, block: Mapping[str, Any] | None) -> HostIncubationFactors:
        """Build from a ``host_factors`` config block (or nothing)."""
        cfg = dict(block or {})
        _reject_unknown_keys("host_factors", cfg, _HOST_FACTOR_KEYS)
        bands = {
            str(band): float(value)
            for band, value in dict(cfg.get("age_bands", {})).items()
        }
        return cls(
            immunocompromised=float(cfg.get("immunocompromised", 1.0)),
            prior_immunity=float(cfg.get("prior_immunity", 1.0)),
            age_bands=bands,
        )

    def multiplier(self, host: HostIncubationState) -> float:
        """Combined host multiplier on the incubation median."""
        factor = self.age_bands.get(host.age_band, 1.0)
        if host.immunocompromised:
            factor *= self.immunocompromised
        if host.prior_immunity:
            factor *= self.prior_immunity
        return factor


def _require_positive(name: str, value: float) -> None:
    """Reject a non-positive value for a strictly positive parameter."""
    if value <= 0.0:
        raise ValueError(f"{name} must be > 0: {value}")


@dataclass(frozen=True)
class IncubationModel:
    """Per-pathogen incubation distribution with dose and host conditioning.

    ``median_days`` and ``dispersion`` are the literature anchor; the dose and
    host terms move the median of an individual draw. ``dispersion`` is the
    geometric standard deviation for a lognormal and the coefficient of
    variation for a gamma, so both are read as "how wide", not "how long".
    """

    median_days: float
    distribution: str = DISTRIBUTION_LOGNORMAL
    dispersion: float = DEFAULT_DISPERSION
    min_days: float = DEFAULT_MIN_DAYS
    max_days: float = DEFAULT_MAX_DAYS
    dose_reference_log10: float = DEFAULT_DOSE_REFERENCE_LOG10
    dose_log10_shortening: float = 0.0
    dose_floor: float = MIN_DOSE_FACTOR
    host_factors: HostIncubationFactors = field(default_factory=HostIncubationFactors)

    def __post_init__(self) -> None:
        if self.distribution not in SUPPORTED_DISTRIBUTIONS:
            raise ValueError(
                f"incubation.distribution must be one of {SUPPORTED_DISTRIBUTIONS}: "
                f"{self.distribution}",
            )
        _require_positive("incubation.median_days", self.median_days)
        if self.dispersion <= 1.0 and self.distribution == DISTRIBUTION_LOGNORMAL:
            raise ValueError(
                f"incubation.dispersion must be > 1 for a lognormal (geometric "
                f"standard deviation): {self.dispersion}",
            )
        if self.distribution == DISTRIBUTION_GAMMA:
            _require_positive("incubation.dispersion", self.dispersion)
        if self.min_days < 0.0:
            raise ValueError(f"incubation.min_days must be >= 0: {self.min_days}")
        if self.max_days <= self.min_days:
            raise ValueError(
                f"incubation.max_days ({self.max_days}) must exceed min_days "
                f"({self.min_days})",
            )
        if not self.min_days < self.median_days < self.max_days:
            raise ValueError(
                f"incubation.median_days ({self.median_days}) must lie strictly "
                f"inside the truncation window "
                f"({self.min_days}, {self.max_days}): the typical host would "
                f"otherwise present at a bound rather than at the median",
            )
        if self.dose_log10_shortening < 0.0:
            raise ValueError(
                f"incubation.dose_log10_shortening must be >= 0: "
                f"{self.dose_log10_shortening}",
            )
        if not 0.0 < self.dose_floor <= 1.0:
            raise ValueError(
                f"incubation.dose_floor must be in (0, 1]: {self.dose_floor}",
            )

    @classmethod
    def from_mapping(cls, block: Mapping[str, Any] | None) -> IncubationModel | None:
        """Build from an ``incubation`` profile block, or ``None`` when absent.

        ``None`` is the legacy path: a pathogen without a distribution keeps
        the fixed onset day it had, so profiles are converted deliberately
        rather than all at once.
        """
        if not block:
            return None
        cfg = dict(block)
        _reject_unknown_keys("incubation", cfg, _INCUBATION_KEYS)
        median = cfg.get("median_days")
        if median is None:
            raise ValueError("incubation block requires median_days")
        return cls(
            median_days=float(median),
            distribution=str(cfg.get("distribution", DISTRIBUTION_LOGNORMAL)),
            dispersion=float(cfg.get("dispersion", DEFAULT_DISPERSION)),
            min_days=float(cfg.get("min_days", DEFAULT_MIN_DAYS)),
            max_days=float(cfg.get("max_days", DEFAULT_MAX_DAYS)),
            dose_reference_log10=float(
                cfg.get("dose_reference_log10", DEFAULT_DOSE_REFERENCE_LOG10),
            ),
            dose_log10_shortening=float(cfg.get("dose_log10_shortening", 0.0)),
            dose_floor=float(cfg.get("dose_floor", MIN_DOSE_FACTOR)),
            host_factors=HostIncubationFactors.from_mapping(cfg.get("host_factors")),
        )

    def dose_factor(self, dose: float) -> float:
        """Multiplier on the median from the size of the inoculum.

        Anchored at ``dose_reference_log10``, so the profile's median is the
        median at a typical exposure rather than at an arbitrary one, and a
        light exposure lengthens onset by as much as a heavy one shortens it.
        """
        if self.dose_log10_shortening <= 0.0:
            return 1.0
        exponent = math.log10(max(float(dose), _DOSE_FLOOR))
        excess = exponent - self.dose_reference_log10
        factor = 1.0 - self.dose_log10_shortening * excess
        return min(max(factor, self.dose_floor), MAX_DOSE_FACTOR)

    def conditional_median(self, dose: float, host: HostIncubationState) -> float:
        """Median incubation for this exposure in this host, before the draw."""
        median = self.median_days * self.dose_factor(dose)
        return median * self.host_factors.multiplier(host)

    def sample_days(
        self,
        *,
        dose: float,
        host: HostIncubationState,
        rng: np.random.Generator,
    ) -> float:
        """Draw one host's incubation period, in days.

        Clamped to the profile's plausible window: a distribution fitted to
        observed onsets has no business emitting a twelve-hour norovirus
        incubation just because its tail reaches there.
        """
        median = self.conditional_median(dose, host)
        drawn = self._draw(median, rng)
        return min(max(drawn, self.min_days), self.max_days)

    def _draw(self, median: float, rng: np.random.Generator) -> float:
        """Untruncated draw around a conditioned median."""
        if self.distribution == DISTRIBUTION_GAMMA:
            shape = 1.0 / (self.dispersion * self.dispersion)
            return float(rng.gamma(shape, median / shape))
        return float(rng.lognormal(math.log(median), math.log(self.dispersion)))


class IncubationHost(Protocol):
    """The agent surface an incubation draw reads.

    Narrow on purpose: it names exactly the three host facts the distribution
    is conditioned on, so a population builder that cannot supply one is a type
    error rather than a silently neutral host.
    """

    age_band: str
    immunocompromised: bool

    def immune_genotypes(self, pathogen_id: str) -> tuple[str, ...]:
        """Genotypes of this pathogen the host has immune memory of."""
        ...


def host_incubation_state(
    agent: IncubationHost,
    pathogen_id: str,
) -> HostIncubationState:
    """Read one agent's incubation-relevant biology.

    Prior immunity is any recorded memory of this pathogen, of any genotype:
    partial immunity blunts and delays presentation whether or not it protects
    against the lineage now arriving, which is exactly the case a cross-immunity
    study cares about.
    """
    return HostIncubationState(
        age_band=agent.age_band,
        immunocompromised=bool(agent.immunocompromised),
        prior_immunity=bool(agent.immune_genotypes(pathogen_id)),
    )
