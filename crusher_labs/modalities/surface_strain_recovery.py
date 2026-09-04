"""Strain recovery from targeted surface swabs.

This channel reports the part of a swab's recovered abundance that can be
attributed to the strain composition already held by the surface reservoir.
The recovery probabilities and reporting floors are operator dials with no
literature anchor: the defaults provide a sweepable spread and are not tuned
to a particular shipboard assay.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

import numpy as np

from engines.sim_clock import LEGACY_CLOCK, SimClock
from engines.strain_dose_ledger import UNREPORTABLE_GENOTYPES
from engines.transmission_core import (
    DEFAULT_SURFACE_DECAY_LOG10_PER_DAY,
    surface_fraction_per_day,
)

STATUS_NOT_CONFIGURED = "not_configured"
STATUS_NO_DEPOSITION = "no_deposition"
STATUS_NO_COMPOSITION = "no_composition"
STATUS_BELOW_REPORTING_FLOOR = "below_reporting_floor"
STATUS_RECOVERED = "recovered"

SURFACE_TYPE_RECOVERY_ORDER: tuple[str, ...] = (
    "Free",
    "Cabin_Corridor",
    "Room",
    "Engineering",
    "Dining",
    "Medical",
)
DEFAULT_RECOVERY_BY_SURFACE_TYPE: Mapping[str, float] = MappingProxyType({
    "Free": 0.25,
    "Cabin_Corridor": 0.40,
    "Room": 0.50,
    "Engineering": 0.60,
    "Dining": 0.75,
    "Medical": 0.85,
})
DEFAULT_SURFACE_RECOVERY = 0.25
DEFAULT_MIN_LINEAGE_ABUNDANCE = 0.0
DEFAULT_MIN_LINEAGE_FRACTION = 0.02


def _require_probability(name: str, value: float) -> float:
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0, 1]: {value}")
    return value


@dataclass(frozen=True)
class SurfaceRecoveryConfig:
    """Operator-controlled recovery and reporting settings."""

    enabled: bool = False
    recovery_by_surface_type: Mapping[str, float] = field(
        default_factory=lambda: DEFAULT_RECOVERY_BY_SURFACE_TYPE,
    )
    default_recovery: float = DEFAULT_SURFACE_RECOVERY
    min_lineage_abundance: float = DEFAULT_MIN_LINEAGE_ABUNDANCE
    min_lineage_fraction: float = DEFAULT_MIN_LINEAGE_FRACTION

    def __post_init__(self) -> None:
        _require_probability("default_recovery", float(self.default_recovery))
        for surface_type, probability in self.recovery_by_surface_type.items():
            _require_probability(
                f"recovery_by_surface_type[{surface_type!r}]",
                float(probability),
            )
        if self.min_lineage_abundance < 0.0:
            raise ValueError(
                "min_lineage_abundance must be >= 0: "
                f"{self.min_lineage_abundance}",
            )
        if self.min_lineage_fraction < 0.0:
            raise ValueError(
                "min_lineage_fraction must be >= 0: "
                f"{self.min_lineage_fraction}",
            )

    @classmethod
    def from_mapping(
        cls,
        block: Mapping[str, object] | None,
    ) -> "SurfaceRecoveryConfig":
        """Build from a ``surface_sampling`` config block (or nothing)."""
        cfg = dict(block or {})
        recovery_map = cfg.get("recovery_by_surface_type")
        if recovery_map is None:
            recovery_map = dict(DEFAULT_RECOVERY_BY_SURFACE_TYPE)
        if not isinstance(recovery_map, Mapping):
            raise ValueError("recovery_by_surface_type must be an object")
        return cls(
            enabled=bool(cfg.get("enabled", False)),
            recovery_by_surface_type={
                str(surface_type): float(probability)
                for surface_type, probability in recovery_map.items()
            },
            default_recovery=float(
                cfg.get("default_recovery", DEFAULT_SURFACE_RECOVERY),
            ),
            min_lineage_abundance=float(
                cfg.get(
                    "min_lineage_abundance",
                    DEFAULT_MIN_LINEAGE_ABUNDANCE,
                ),
            ),
            min_lineage_fraction=float(
                cfg.get("min_lineage_fraction", DEFAULT_MIN_LINEAGE_FRACTION),
            ),
        )

    def recovery_for_surface_type(self, surface_type: str) -> float:
        """Return the configured base recovery for one surface type."""
        return float(self.recovery_by_surface_type.get(
            surface_type, self.default_recovery,
        ))


def surface_persistence(
    epochs_since_deposition: int,
    *,
    clock: SimClock = LEGACY_CLOCK,
) -> float:
    """Surface mass retained after ``epochs_since_deposition`` epochs."""
    epochs = max(int(epochs_since_deposition), 0)
    survival = 1.0 - clock.decay_per_epoch(
        surface_fraction_per_day(DEFAULT_SURFACE_DECAY_LOG10_PER_DAY),
    )
    return float(survival ** epochs)


def recovery_probability(
    surface_type: str,
    epochs_since_deposition: int,
    *,
    config: SurfaceRecoveryConfig | None = None,
    clock: SimClock = LEGACY_CLOCK,
) -> float:
    """Base recovery attenuated by the repository's surface decay factor."""
    settings = config or SurfaceRecoveryConfig(enabled=True)
    probability = settings.recovery_for_surface_type(surface_type)
    return float(np.clip(
        probability * surface_persistence(
            epochs_since_deposition,
            clock=clock,
        ),
        0.0,
        1.0,
    ))


@dataclass(frozen=True)
class SurfaceLineageMixture:
    """Conserved strain composition recovered from one surface swab."""

    status: str
    surface_type: str
    recovery_probability: float
    epochs_since_deposition: int
    sampled_abundance: float
    calls: tuple[tuple[str, float], ...] = ()
    unresolved_abundance: float = 0.0

    @property
    def resolved_abundance(self) -> float:
        """Abundance attributed to reportable recovered lineages."""
        return sum(abundance for _genotype, abundance in self.calls)

    @property
    def consensus_genotype(self) -> str | None:
        """Most abundant reported genotype, or ``None``."""
        return next((genotype for genotype, _abundance in self.calls), None)

    def as_row(self) -> dict[str, object]:
        """Serialize the mixture for a surface-swab observation row."""
        total = float(self.sampled_abundance)
        return {
            "lineage_status": str(self.status),
            "surface_type": self.surface_type,
            "recovery_probability": float(self.recovery_probability),
            "epochs_since_deposition": int(self.epochs_since_deposition),
            "sampled_abundance": total,
            "lineage_calls": [
                {
                    "genotype": genotype,
                    "abundance": float(abundance),
                    "fraction": (abundance / total) if total > 0.0 else 0.0,
                }
                for genotype, abundance in self.calls
            ],
            "lineage_unresolved_abundance": float(self.unresolved_abundance),
        }


def _normalized_composition(
    composition: Mapping[str, float] | None,
) -> dict[str, float]:
    """Convert positive pool masses into proportions."""
    weights = {
        str(genotype): float(mass)
        for genotype, mass in (composition or {}).items()
        if float(mass) > 0.0
    }
    total = sum(weights.values())
    if total <= 0.0:
        return {}
    return {genotype: mass / total for genotype, mass in weights.items()}


def _recovered_calls(
    sampled_abundance: float,
    proportions: Mapping[str, float],
    *,
    probability: float,
    floor: float,
    rng: np.random.Generator,
) -> tuple[tuple[tuple[str, float], ...], float]:
    """Draw reportable lineages, floor, and conserve each abundance.

    Unreportable genotypes are routed to unresolved before the Bernoulli draw,
    so the recovery stream contains draws only for candidate reportable
    lineages.
    """
    calls: list[tuple[str, float]] = []
    unresolved = 0.0
    for genotype in sorted(proportions):
        abundance = sampled_abundance * proportions[genotype]
        reportable = genotype.strip().lower() not in UNREPORTABLE_GENOTYPES
        if not reportable:
            unresolved += abundance
            continue
        recovered = bool(rng.random() < probability)
        if recovered and reportable and abundance >= floor:
            calls.append((genotype, abundance))
        else:
            unresolved += abundance
    calls.sort(key=lambda item: (-item[1], item[0]))
    return tuple(calls), unresolved


def recover_surface_mixture(
    sampled_abundance: float,
    composition: Mapping[str, float] | None,
    *,
    surface_type: str,
    epochs_since_deposition: int,
    config: SurfaceRecoveryConfig,
    rng: np.random.Generator,
    clock: SimClock = LEGACY_CLOCK,
) -> SurfaceLineageMixture:
    """Recover a conserved lineage mixture from a sampled surface abundance."""
    sampled = max(float(sampled_abundance), 0.0)
    probability = recovery_probability(
        surface_type,
        epochs_since_deposition,
        config=config,
        clock=clock,
    )
    if not config.enabled:
        return SurfaceLineageMixture(
            STATUS_NOT_CONFIGURED,
            surface_type,
            0.0,
            max(int(epochs_since_deposition), 0),
            sampled,
            unresolved_abundance=sampled,
        )
    if sampled <= 0.0:
        return SurfaceLineageMixture(
            STATUS_NO_DEPOSITION,
            surface_type,
            probability,
            max(int(epochs_since_deposition), 0),
            0.0,
        )
    proportions = _normalized_composition(composition)
    if not proportions:
        return SurfaceLineageMixture(
            STATUS_NO_COMPOSITION,
            surface_type,
            probability,
            max(int(epochs_since_deposition), 0),
            sampled,
            unresolved_abundance=sampled,
        )
    floor = max(
        config.min_lineage_abundance,
        config.min_lineage_fraction * sampled,
    )
    calls, unresolved = _recovered_calls(
        sampled,
        proportions,
        probability=probability,
        floor=floor,
        rng=rng,
    )
    status = STATUS_RECOVERED if calls else STATUS_BELOW_REPORTING_FLOOR
    return SurfaceLineageMixture(
        status,
        surface_type,
        probability,
        max(int(epochs_since_deposition), 0),
        sampled,
        calls=calls,
        unresolved_abundance=unresolved,
    )
