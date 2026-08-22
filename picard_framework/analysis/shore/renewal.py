"""Linear shore-side renewal dynamics.

``R_shore`` and the shore generation interval are unanchored caller-supplied
quantities and must be swept explicitly; this module supplies no defaults for
them.  The outstanding author item is a literature citation for norovirus
community transmission.  The generation interval is genuinely shore-side and
has no profile counterpart: it must not be inferred from incubation.

The renewal is deliberately linear and therefore appropriate only while cases
remain small relative to the port population.  It does not model susceptible
depletion or shore-side evolution.  Strain labels from the ship are retained
as separate trajectories under one shared shore parameter set; a future
per-strain parameter set would attach at :func:`renewal_by_strain`.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping, Sequence

import numpy as np

from picard_framework.analysis.sentinel.incubation import (
    DelayDistribution,
    lognormal_delay,
    renewal_incidence,
)
from picard_framework.analysis.shore.importation import PortCallImportation

DEPLETION_FRACTION = 0.05


@dataclass(frozen=True)
class ShoreRenewalParameters:
    """Caller-supplied shore dynamics; no epidemiological defaults are hidden."""

    r_shore: float
    generation_median_hours: float
    generation_sigma: float
    generation_max_hours: float
    population: int

    def __post_init__(self) -> None:
        values = (
            self.r_shore,
            self.generation_median_hours,
            self.generation_sigma,
            self.generation_max_hours,
        )
        if any(not isfinite(float(value)) for value in values):
            raise ValueError("shore renewal parameters must be finite")
        if self.r_shore < 0.0:
            raise ValueError("r_shore must be non-negative")
        if self.generation_median_hours <= 0.0:
            raise ValueError("generation_median_hours must be positive")
        if self.generation_sigma <= 0.0:
            raise ValueError("generation_sigma must be positive")
        if self.generation_max_hours <= 0.0:
            raise ValueError("generation_max_hours must be positive")
        if self.population < 1:
            raise ValueError("population must be >= 1")

    def generation_distribution(self, epoch_hours: float) -> DelayDistribution:
        """Build the caller-supplied shore generation pmf on this grid."""
        return lognormal_delay(
            name="shore.generation",
            median_hours=self.generation_median_hours,
            sigma=self.generation_sigma,
            epoch_hours=epoch_hours,
            max_hours=self.generation_max_hours,
        )


@dataclass(frozen=True)
class ShoreRenewalResult:
    """Combined shore incidence and validity diagnostics."""

    trajectory: np.ndarray
    by_strain: Mapping[str, np.ndarray]
    total_cases: float
    total_by_strain: Mapping[str, float]
    attack_fraction: float
    depletion_regime: bool
    unbounded_growth: bool


def renewal_trajectory(
    imports: Sequence[float] | np.ndarray,
    parameters: ShoreRenewalParameters,
    *,
    epoch_hours: float,
) -> np.ndarray:
    """Propagate one importation vector through the linear renewal."""
    generation = parameters.generation_distribution(epoch_hours)
    return renewal_incidence(imports, parameters.r_shore, generation)


def renewal_by_strain(
    importation: PortCallImportation,
    parameters: ShoreRenewalParameters,
) -> dict[str, np.ndarray]:
    """Propagate each exported strain with one shared shore parameter set."""
    return {
        label: renewal_trajectory(values, parameters, epoch_hours=importation.epoch_hours)
        for label, values in importation.strain_importations.items()
    }


def _result_from_trajectories(
    trajectories: Mapping[str, np.ndarray],
    parameters: ShoreRenewalParameters,
) -> ShoreRenewalResult:
    """Combine per-strain trajectories and derive population diagnostics."""
    horizon = max((len(values) for values in trajectories.values()), default=0)
    combined = np.zeros(horizon, dtype=float)
    totals: dict[str, float] = {}
    for label, values in trajectories.items():
        combined += values
        totals[label] = float(values.sum())
    total = float(combined.sum())
    attack_fraction = total / parameters.population
    return ShoreRenewalResult(
        trajectory=combined,
        by_strain=dict(trajectories),
        total_cases=total,
        total_by_strain=totals,
        attack_fraction=attack_fraction,
        depletion_regime=attack_fraction > DEPLETION_FRACTION,
        unbounded_growth=parameters.r_shore >= 1.0,
    )


def renewal_result(
    importation: PortCallImportation,
    parameters: ShoreRenewalParameters,
) -> ShoreRenewalResult:
    """Propagate a port call and report boundedness/depletion diagnostics."""
    return _result_from_trajectories(renewal_by_strain(importation, parameters), parameters)
