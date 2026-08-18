"""Assay modes for a shipboard wastewater sample: what the lab actually reports.

:mod:`wastewater_ops` decides *when* a sample is drawn and what has accumulated
in the holding tank. This module decides what a laboratory does with that
sample, and the four modes are not interchangeable views of one number:

* ``qpcr`` — RT-qPCR. Reports a Ct, and below the limit of detection reports
  nothing but the bound. This is the mode a cruise ship would actually run: it
  is quantitative over the prevalence range a ship reaches, where metagenomics
  is not (see below), and its output is a concentration the fit can put a
  censored likelihood on.
* ``amplicon`` — targeted amplicon sequencing. Detection is the same qPCR gate;
  the reads that follow are *on-target* reads, so their fraction saturates and
  carries far less quantitative information than the Ct does. It exists for
  typing, and the quantitative constraint still comes from the gate.
* ``metagenomic`` — the existing compositional read model, unchanged. It is
  blind at shipboard prevalence and this is arithmetic, not a defect: with an
  informative ceiling of 1e-4 of the library, a 0.3 % shedder prevalence has an
  expected 0.06 pathogen reads in a 250 000-read library. Kept as the
  comparison arm of the ops scan, not as a recommendation.
* ``long_read`` — Nanopore confirmation/typing. Same detection gate, plus the
  instrument turnaround that makes it a confirmatory rather than a routine
  cadence assay.

Every quantitative mode goes through one physical chain, so the modes stay
comparable::

    gc/L        = prevalence * gc_per_person_day / L_per_person_day
    copies/rxn  = gc/L * sample_volume * extraction_efficiency * reaction_fraction
    Ct          = ct_slope * log10(copies/rxn) + ct_intercept  (+ noise)
    detected    = Ct <= lod_ct_threshold

``concentration_factor`` is a *recovery* ratio on that chain, not free copies: a
100x volume reduction concentrates the copies already in the aliquot, it does
not create any, and modelling it as a multiplier on ``gc/L`` is the standard way
to overstate a wastewater assay's sensitivity by two orders of magnitude.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any, Mapping

import numpy as np

ASSAY_QPCR = "qpcr"
ASSAY_AMPLICON = "amplicon"
ASSAY_METAGENOMIC = "metagenomic"
ASSAY_LONG_READ = "long_read"
ASSAY_MODES: tuple[str, ...] = (
    ASSAY_QPCR,
    ASSAY_AMPLICON,
    ASSAY_METAGENOMIC,
    ASSAY_LONG_READ,
)
# The mode the channel had before the switch existed. Changing this default
# would silently reinterpret every campaign cell that predates it.
DEFAULT_ASSAY_MODE = ASSAY_METAGENOMIC

# Peak norovirus shedding is 1e9-1e11 gc/g of stool at ~150-250 g/day, so 1e10
# gc/person/day sits in the middle of that range rather than at its optimistic
# end. Blackwater, not total greywater: 30 L/person/day is the sewage stream the
# holding tank actually receives, and using the ~300 L/person/day total would
# dilute the signal tenfold.
DEFAULT_SHEDDING_GC_PER_PERSON_DAY = 1.0e10
DEFAULT_WASTEWATER_L_PER_PERSON_DAY = 30.0

DEFAULT_EXTRACTION_EFFICIENCY = 0.35
DEFAULT_CT_SLOPE = -3.322
DEFAULT_CT_INTERCEPT = 40.0
DEFAULT_LOD_CT_THRESHOLD = 38.0
DEFAULT_CT_NOISE_SD = 0.5
DEFAULT_SAMPLE_VOLUME_ML = 100.0
DEFAULT_CONCENTRATION_FACTOR = 1.0
# A 5 uL reaction off a 50 uL extract: the aliquot is a real, and usually
# unstated, factor of ten between "copies recovered" and "copies amplified".
DEFAULT_REACTION_FRACTION = 0.1

DEFAULT_AMPLICON_EFFICIENCY = 0.5
DEFAULT_AMPLICON_DEPTH = 50_000
# On-target fraction is half its ceiling at this input; above it the library is
# saturated and the read fraction stops tracking concentration.
DEFAULT_AMPLICON_HALF_SATURATION_COPIES = 1_000.0
DEFAULT_PRIMER_TARGETS: tuple[str, ...] = ("norovirus_capsid",)

DEFAULT_LONG_READ_DEPTH = 20_000
# Nanopore off an enriched library: a fifth of the reads are on target, and that
# fraction is a property of the preparation rather than of the concentration, so
# the read count in this mode types the pathogen and does not quantify it.
DEFAULT_LONG_READ_ON_TARGET_FRACTION = 0.2
# Consistent with the shipboard profiles in
# data/config/long_read_sequencing_params.json: a confirmation, not a cadence.
DEFAULT_LONG_READ_TURNAROUND_HOURS = 12.0

HOURS_PER_DAY = 24.0
ML_PER_L = 1000.0


def _require_positive(name: str, value: float) -> float:
    if value <= 0.0:
        raise ValueError(f"{name} must be positive: {value}")
    return float(value)


def _require_fraction(name: str, value: float) -> float:
    if not 0.0 < value <= 1.0:
        raise ValueError(f"{name} must be in (0, 1]: {value}")
    return float(value)


@dataclass(frozen=True)
class ShedLoadModel:
    """Prevalence to concentration: the one conversion every mode shares.

    Per *person*, so the concentration a tank reaches is a function of shedder
    prevalence rather than of ship size. A 7 000-berth ship and a 700-berth ship
    at the same prevalence present the same sample, which is what makes an ops
    scan across platforms readable.
    """

    gc_per_person_day: float = DEFAULT_SHEDDING_GC_PER_PERSON_DAY
    wastewater_l_per_person_day: float = DEFAULT_WASTEWATER_L_PER_PERSON_DAY

    def __post_init__(self) -> None:
        _require_positive("gc_per_person_day", self.gc_per_person_day)
        _require_positive(
            "wastewater_l_per_person_day", self.wastewater_l_per_person_day,
        )

    @property
    def gc_per_l_at_full_shedding(self) -> float:
        """Concentration if every person aboard were shedding."""
        return self.gc_per_person_day / self.wastewater_l_per_person_day

    def gc_per_l(self, shedder_prevalence: float) -> float:
        """Genome copies per litre at a given shedder prevalence."""
        share = max(float(shedder_prevalence), 0.0)
        return share * self.gc_per_l_at_full_shedding

    @classmethod
    def from_mapping(cls, block: Mapping[str, Any] | None) -> ShedLoadModel:
        """Build from a config block (or nothing)."""
        cfg = dict(block or {})
        return cls(
            gc_per_person_day=float(
                cfg.get("shedding_gc_per_person_day", DEFAULT_SHEDDING_GC_PER_PERSON_DAY),
            ),
            wastewater_l_per_person_day=float(
                cfg.get(
                    "wastewater_l_per_person_day", DEFAULT_WASTEWATER_L_PER_PERSON_DAY,
                ),
            ),
        )


@dataclass(frozen=True)
class QpcrAssayConfig:
    """RT-qPCR calibration: the standard curve, the aliquot, and the LOD."""

    extraction_efficiency: float = DEFAULT_EXTRACTION_EFFICIENCY
    ct_slope: float = DEFAULT_CT_SLOPE
    ct_intercept: float = DEFAULT_CT_INTERCEPT
    lod_ct_threshold: float = DEFAULT_LOD_CT_THRESHOLD
    ct_noise_sd: float = DEFAULT_CT_NOISE_SD
    sample_volume_ml: float = DEFAULT_SAMPLE_VOLUME_ML
    concentration_factor: float = DEFAULT_CONCENTRATION_FACTOR
    reaction_fraction: float = DEFAULT_REACTION_FRACTION

    def __post_init__(self) -> None:
        _require_fraction("extraction_efficiency", self.extraction_efficiency)
        _require_fraction("reaction_fraction", self.reaction_fraction)
        _require_positive("sample_volume_ml", self.sample_volume_ml)
        _require_positive("concentration_factor", self.concentration_factor)
        if self.ct_slope >= 0.0:
            raise ValueError(f"ct_slope must be negative: {self.ct_slope}")
        if self.ct_noise_sd < 0.0:
            raise ValueError(f"ct_noise_sd must be >= 0: {self.ct_noise_sd}")

    @property
    def copies_per_gc_per_l(self) -> float:
        """Copies reaching one reaction per gc/L in the tank."""
        return (
            self.sample_volume_ml
            / ML_PER_L
            * self.extraction_efficiency
            * self.concentration_factor
            * self.reaction_fraction
        )

    def copies_per_reaction(self, gc_per_l: float) -> float:
        """Template copies in one reaction, given the tank concentration."""
        return max(float(gc_per_l), 0.0) * self.copies_per_gc_per_l

    def ct_from_copies(self, copies: float) -> float | None:
        """Standard curve; ``None`` when nothing was recovered."""
        if copies <= 0.0:
            return None
        return self.ct_slope * math.log10(copies) + self.ct_intercept

    @property
    def lod_copies_per_reaction(self) -> float:
        """Template copies whose noiseless Ct sits exactly at the LOD."""
        exponent = (self.lod_ct_threshold - self.ct_intercept) / self.ct_slope
        return float(10.0**exponent)

    @property
    def lod_gc_per_l(self) -> float:
        """Tank concentration at the limit of detection — the censoring bound."""
        return self.lod_copies_per_reaction / self.copies_per_gc_per_l

    def gc_per_l_from_ct(self, ct_value: float) -> float:
        """Invert the curve: the concentration a reported Ct implies.

        The measurement, not the truth. Ct noise is what separates the two, and
        reporting the inverted noisy Ct is what a laboratory hands over.
        """
        exponent = (float(ct_value) - self.ct_intercept) / self.ct_slope
        return float(10.0**exponent) / self.copies_per_gc_per_l

    @classmethod
    def from_mapping(cls, block: Mapping[str, Any] | None) -> QpcrAssayConfig:
        """Build from a ``qpcr`` config block (or nothing)."""
        cfg = dict(block or {})
        return cls(
            extraction_efficiency=float(
                cfg.get("extraction_efficiency", DEFAULT_EXTRACTION_EFFICIENCY),
            ),
            ct_slope=float(cfg.get("ct_slope", DEFAULT_CT_SLOPE)),
            ct_intercept=float(cfg.get("ct_intercept", DEFAULT_CT_INTERCEPT)),
            lod_ct_threshold=float(
                cfg.get("lod_ct_threshold", DEFAULT_LOD_CT_THRESHOLD),
            ),
            ct_noise_sd=float(cfg.get("ct_noise_sd", DEFAULT_CT_NOISE_SD)),
            sample_volume_ml=float(
                cfg.get("sample_volume_mL", cfg.get("sample_volume_ml", DEFAULT_SAMPLE_VOLUME_ML)),
            ),
            concentration_factor=float(
                cfg.get("concentration_factor", DEFAULT_CONCENTRATION_FACTOR),
            ),
            reaction_fraction=float(
                cfg.get("reaction_fraction", DEFAULT_REACTION_FRACTION),
            ),
        )


@dataclass(frozen=True)
class AmpliconAssayConfig:
    """Targeted amplicon sequencing: a qPCR gate followed by on-target reads."""

    extraction_efficiency: float = DEFAULT_EXTRACTION_EFFICIENCY
    lod_ct_threshold: float = DEFAULT_LOD_CT_THRESHOLD
    amplification_efficiency: float = DEFAULT_AMPLICON_EFFICIENCY
    sequencing_depth: int = DEFAULT_AMPLICON_DEPTH
    half_saturation_copies: float = DEFAULT_AMPLICON_HALF_SATURATION_COPIES
    primer_targets: tuple[str, ...] = DEFAULT_PRIMER_TARGETS

    def __post_init__(self) -> None:
        _require_fraction("extraction_efficiency", self.extraction_efficiency)
        _require_fraction("amplification_efficiency", self.amplification_efficiency)
        _require_positive("half_saturation_copies", self.half_saturation_copies)
        if self.sequencing_depth < 1:
            raise ValueError(f"sequencing_depth must be >= 1: {self.sequencing_depth}")
        if not self.primer_targets:
            raise ValueError("primer_targets must name at least one target")

    def on_target_fraction(self, copies: float) -> float:
        """Fraction of the library that is target amplicon.

        Saturating in template: enrichment is a ceiling, so above the half
        saturation point more template buys reads but no more information about
        how much template there was. That plateau is the reason the quantitative
        constraint in this mode comes from the Ct gate, not from the reads.
        """
        template = max(float(copies), 0.0)
        return self.amplification_efficiency * template / (
            template + self.half_saturation_copies
        )

    @classmethod
    def from_mapping(cls, block: Mapping[str, Any] | None) -> AmpliconAssayConfig:
        """Build from an ``amplicon`` config block (or nothing)."""
        cfg = dict(block or {})
        targets = cfg.get("primer_targets")
        if targets is None:
            targets = list(DEFAULT_PRIMER_TARGETS)
        return cls(
            extraction_efficiency=float(
                cfg.get("extraction_efficiency", DEFAULT_EXTRACTION_EFFICIENCY),
            ),
            lod_ct_threshold=float(
                cfg.get("lod_ct_threshold", DEFAULT_LOD_CT_THRESHOLD),
            ),
            amplification_efficiency=float(
                cfg.get("amplification_efficiency", DEFAULT_AMPLICON_EFFICIENCY),
            ),
            sequencing_depth=int(cfg.get("sequencing_depth", DEFAULT_AMPLICON_DEPTH)),
            half_saturation_copies=float(
                cfg.get(
                    "half_saturation_copies", DEFAULT_AMPLICON_HALF_SATURATION_COPIES,
                ),
            ),
            primer_targets=tuple(str(t) for t in targets),
        )


@dataclass(frozen=True)
class LongReadAssayConfig:
    """Nanopore confirmation: same gate, fewer reads, an instrument delay."""

    extraction_efficiency: float = DEFAULT_EXTRACTION_EFFICIENCY
    lod_ct_threshold: float = DEFAULT_LOD_CT_THRESHOLD
    sequencing_depth: int = DEFAULT_LONG_READ_DEPTH
    on_target_fraction: float = DEFAULT_LONG_READ_ON_TARGET_FRACTION
    turnaround_hours: float = DEFAULT_LONG_READ_TURNAROUND_HOURS
    reference_genotype: str | None = None

    def __post_init__(self) -> None:
        _require_fraction("extraction_efficiency", self.extraction_efficiency)
        _require_fraction("on_target_fraction", self.on_target_fraction)
        if self.sequencing_depth < 1:
            raise ValueError(f"sequencing_depth must be >= 1: {self.sequencing_depth}")
        if self.turnaround_hours < 0.0:
            raise ValueError(f"turnaround_hours must be >= 0: {self.turnaround_hours}")

    @classmethod
    def from_mapping(cls, block: Mapping[str, Any] | None) -> LongReadAssayConfig:
        """Build from a ``long_read`` config block (or nothing)."""
        cfg = dict(block or {})
        genotype = cfg.get("reference_genotype")
        return cls(
            extraction_efficiency=float(
                cfg.get("extraction_efficiency", DEFAULT_EXTRACTION_EFFICIENCY),
            ),
            lod_ct_threshold=float(
                cfg.get("lod_ct_threshold", DEFAULT_LOD_CT_THRESHOLD),
            ),
            sequencing_depth=int(
                cfg.get("sequencing_depth", DEFAULT_LONG_READ_DEPTH),
            ),
            on_target_fraction=float(
                cfg.get("on_target_fraction", DEFAULT_LONG_READ_ON_TARGET_FRACTION),
            ),
            turnaround_hours=float(
                cfg.get("turnaround_hours", DEFAULT_LONG_READ_TURNAROUND_HOURS),
            ),
            reference_genotype=None if genotype is None else str(genotype),
        )


def gate_config(
    base: QpcrAssayConfig,
    *,
    extraction_efficiency: float,
    lod_ct_threshold: float,
) -> QpcrAssayConfig:
    """The qPCR chain a sequencing mode gates on, with its own recovery and LOD.

    Amplicon and long-read library preparation share the standard curve — the
    detection decision is a qPCR decision either way — but not necessarily the
    extraction recovery or the cutoff, so those two are substituted rather than
    duplicating the curve in each mode's config.
    """
    return replace(
        base,
        extraction_efficiency=float(extraction_efficiency),
        lod_ct_threshold=float(lod_ct_threshold),
    )


def resolve_assay_mode(mode: object) -> str:
    """Normalize and validate an ``assay_mode`` value."""
    resolved = str(mode or DEFAULT_ASSAY_MODE).strip().lower()
    if resolved not in ASSAY_MODES:
        raise ValueError(
            f"unknown wastewater assay_mode {resolved!r}; known: {list(ASSAY_MODES)}",
        )
    return resolved


@dataclass(frozen=True)
class QpcrReading:
    """One RT-qPCR result: a Ct, or the bound it fell below."""

    detected: bool
    ct_value: float | None
    concentration_copies_per_l: float | None
    lod_copies_per_l: float
    copies_per_reaction: float

    def as_row(self) -> dict[str, Any]:
        """Assay-specific fields of an observation row."""
        return {
            "detected": bool(self.detected),
            "ct_value": None if self.ct_value is None else round(self.ct_value, 2),
            "concentration_copies_per_l": (
                None
                if self.concentration_copies_per_l is None
                else float(self.concentration_copies_per_l)
            ),
            "lod_copies_per_l": float(self.lod_copies_per_l),
        }


def qpcr_reading(
    gc_per_l: float,
    *,
    config: QpcrAssayConfig,
    rng: np.random.Generator,
) -> QpcrReading:
    """Run the standard curve on a tank concentration and gate it at the LOD.

    A non-detect reports no Ct and no concentration — only that the sample sat
    below the bound. Reporting the noisy Ct of a negative well instead is how a
    censored observation gets silently promoted to a measurement.
    """
    threshold = config.lod_ct_threshold
    copies = config.copies_per_reaction(gc_per_l)
    ct_true = config.ct_from_copies(copies)
    lod_gc_per_l = config.lod_gc_per_l
    if ct_true is None:
        return QpcrReading(
            detected=False,
            ct_value=None,
            concentration_copies_per_l=None,
            lod_copies_per_l=lod_gc_per_l,
            copies_per_reaction=0.0,
        )
    noise = (
        float(rng.normal(0.0, config.ct_noise_sd)) if config.ct_noise_sd > 0.0 else 0.0
    )
    ct_observed = ct_true + noise
    if ct_observed > threshold:
        return QpcrReading(
            detected=False,
            ct_value=None,
            concentration_copies_per_l=None,
            lod_copies_per_l=lod_gc_per_l,
            copies_per_reaction=copies,
        )
    return QpcrReading(
        detected=True,
        ct_value=ct_observed,
        concentration_copies_per_l=config.gc_per_l_from_ct(ct_observed),
        lod_copies_per_l=lod_gc_per_l,
        copies_per_reaction=copies,
    )
