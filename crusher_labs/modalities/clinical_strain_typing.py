"""
crusher_labs.modalities.clinical_strain_typing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Amplicon strain typing of a clinical specimen (variant surveillance, Paper 3
PR 6).

The assay is deliberately split into a biological part the simulation owns and
a design part the operator chooses:

* biology — which lineages a host is carrying and in what proportion, read
  from the strain state via :func:`specimen_genotype_mixture`;
* design — read depth, the read floor a genotype must clear to be reported,
  and the amplicon/accuracy/Ct/cost of the assay itself, which are sweepable
  parameters rather than fixed facts.

Detection is gated on the Ct standard curve already used by targeted PCR
(:func:`crusher_labs.modalities.targeted_pcr.ct_from_mass`) so there is one
Ct/LOD implementation in the repository, not two.

Accuracy below 100% miscalls *reads*, and enough miscalled reads miscall the
specimen: a typed result can therefore name the wrong genotype, not merely
fail. That is what keeps a detection-speed or lineage-attribution result
honest — a wrong lineage is a different epidemiological error from a missing
one, and the paper has to be able to report both.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np

from crusher_labs.modalities.targeted_pcr import (
    DEFAULT_CT_INTERCEPT,
    DEFAULT_CT_SLOPE,
    ct_from_mass,
)
from simulation_utils.numeric import default_simulation_rng

INSTRUMENT_NAME = "clinical_strain_typing"

STATUS_TYPED = "typed"
STATUS_NO_TEMPLATE = "no_template"
STATUS_ABOVE_CT_THRESHOLD = "above_ct_threshold"
STATUS_NO_STRAIN_STATE = "no_strain_state"
STATUS_BELOW_READ_FLOOR = "below_read_floor"
STATUS_NOT_OFFERED = "not_offered"

CLINICAL_EXTRACTION_EFFICIENCY = 0.7


class AssayConfigError(ValueError):
    """Raised when a pathogen's ``sequencing_assay`` block is unusable."""


def _require_fraction(name: str, value: Any) -> float:
    val = float(value)
    if val <= 0.0 or val > 1.0:
        raise AssayConfigError(f"{name} must be in (0,1], got {val}")
    return val


@dataclass(frozen=True)
class SequencingAssay:
    """One pathogen's clinical amplicon assay (spec §2.1).

    ``read_accuracy`` is the probability that a single read is assigned to the
    lineage it actually came from; the complement is spread over the pathogen's
    other declared genotypes, which is why a miscall produces a plausible wrong
    answer rather than a null one.

    ``read_depth`` and ``min_reads_for_genotype`` are the design dials: depth
    sets how much of a mixture is visible at all, and the floor sets how much
    evidence a minor lineage needs before it is reported.
    """

    pathogen_id: str
    amplicon_target: str
    read_accuracy: float
    ct_threshold: float
    genotypes: tuple[str, ...] = ()
    cost_usd: float = 0.0
    read_depth: int = 5000
    min_reads_for_genotype: int = 10

    @classmethod
    def from_profile(cls, profile: Mapping[str, Any]) -> SequencingAssay | None:
        """Parse a pathogen profile's ``sequencing_assay`` block, or ``None``.

        Genotype labels come from ``strain_evolution`` rather than being
        declared twice: the assay reports the lineages the biology can produce.
        """
        raw = profile.get("sequencing_assay")
        if not raw:
            return None
        if not isinstance(raw, Mapping):
            raise AssayConfigError("sequencing_assay must be an object")
        pathogen_id = str(profile.get("pathogen_id", ""))
        if not pathogen_id:
            raise AssayConfigError("sequencing_assay requires a pathogen_id")
        target = str(raw.get("amplicon_target", "")).strip()
        if not target:
            raise AssayConfigError(
                f"{pathogen_id}.sequencing_assay.amplicon_target must be non-empty",
            )
        evolution = profile.get("strain_evolution") or {}
        depth = int(raw.get("read_depth", 5000))
        floor = int(raw.get("min_reads_for_genotype", 10))
        if depth <= 0:
            raise AssayConfigError(f"{pathogen_id} read_depth must be positive")
        if floor < 1:
            raise AssayConfigError(
                f"{pathogen_id} min_reads_for_genotype must be at least 1",
            )
        return cls(
            pathogen_id=pathogen_id,
            amplicon_target=target,
            read_accuracy=_require_fraction(
                f"{pathogen_id}.read_accuracy", raw.get("read_accuracy", 1.0),
            ),
            ct_threshold=float(raw.get("ct_threshold", 40.0)),
            genotypes=tuple(str(g) for g in evolution.get("genotypes") or ()),
            cost_usd=max(0.0, float(raw.get("cost_usd", 0.0))),
            read_depth=depth,
            min_reads_for_genotype=floor,
        )

    @classmethod
    def load_profiles(
        cls,
        pathogen_profiles: Mapping[str, Mapping[str, Any]],
    ) -> dict[str, SequencingAssay]:
        """Assays for every profile that declares one, keyed by pathogen id."""
        assays: dict[str, SequencingAssay] = {}
        for pid, profile in pathogen_profiles.items():
            assay = cls.from_profile(profile)
            if assay is not None:
                assays[str(pid)] = assay
        return assays


def specimen_genotype_mixture(
    agent: Any,
    pathogen_id: str,
    profile: Mapping[str, Any],
    registry: Any,
) -> dict[str, float]:
    """Genotype composition of what this host is currently shedding.

    Empty when the host carries no tracked lineage for the pathogen, which is
    how an untyped legacy infection stays distinguishable from a typed one.
    Co-resident lineages of the same genotype are summed, since an amplicon
    cannot separate them.
    """
    residents = agent.resident_strains(pathogen_id)
    if not residents:
        return {}
    shares = agent.strain_shedding_shares(pathogen_id, dict(profile))
    if not shares:
        shares = {sid: 1.0 / len(residents) for sid in residents}
    mixture: dict[str, float] = {}
    for strain_id, share in shares.items():
        if share <= 0.0 or strain_id not in registry:
            continue
        genotype = registry.get(strain_id).genotype
        mixture[genotype] = mixture.get(genotype, 0.0) + float(share)
    total = sum(mixture.values())
    if total <= 0.0:
        return {}
    return {g: w / total for g, w in mixture.items()}


class ClinicalStrainTyping:
    """Amplicon sequencing of a clinical specimen into genotype calls."""

    name = INSTRUMENT_NAME

    def __init__(
        self,
        assays: Mapping[str, SequencingAssay] | None = None,
        *,
        extraction_efficiency: float = CLINICAL_EXTRACTION_EFFICIENCY,
        ct_slope: float = DEFAULT_CT_SLOPE,
        ct_intercept: float = DEFAULT_CT_INTERCEPT,
        rng: np.random.Generator | None = None,
    ) -> None:
        self.assays: dict[str, SequencingAssay] = dict(assays or {})
        self.extraction_efficiency = extraction_efficiency
        self.ct_slope = ct_slope
        self.ct_intercept = ct_intercept
        self.rng = rng if rng is not None else default_simulation_rng()

    def type_specimen(
        self,
        agent_id: int,
        pathogen_id: str,
        specimen_mass: float,
        genotype_mixture: Mapping[str, float],
        *,
        epoch: int = 0,
        read_depth: int | None = None,
        min_reads_for_genotype: int | None = None,
    ) -> dict[str, Any]:
        """Type one specimen, returning a call payload with its own status.

        ``genotype_mixture`` is the ground truth (see
        :func:`specimen_genotype_mixture`); ``read_depth`` and
        ``min_reads_for_genotype`` override the configured design for a sweep.
        """
        assay = self.assays.get(pathogen_id)
        if assay is None:
            return self._result(agent_id, pathogen_id, epoch, STATUS_NOT_OFFERED)
        depth = int(read_depth) if read_depth is not None else assay.read_depth
        floor = (
            int(min_reads_for_genotype)
            if min_reads_for_genotype is not None
            else assay.min_reads_for_genotype
        )
        ct = ct_from_mass(
            specimen_mass, self.extraction_efficiency, self.ct_slope, self.ct_intercept,
        )
        gate = self._gate_status(ct, assay, genotype_mixture, depth)
        if gate is not None:
            return self._result(
                agent_id, pathogen_id, epoch, gate, assay=assay, ct=ct, depth=depth,
            )
        truth = _normalized(genotype_mixture)
        reads = self._sequence(assay, truth, depth)
        calls = _calls_from_reads(reads, depth, floor)
        status = STATUS_TYPED if calls else STATUS_BELOW_READ_FLOOR
        return self._result(
            agent_id, pathogen_id, epoch, status,
            assay=assay, ct=ct, depth=depth,
            reads=reads, calls=calls, truth=truth,
        )

    def _gate_status(
        self,
        ct: float | None,
        assay: SequencingAssay,
        genotype_mixture: Mapping[str, float],
        depth: int,
    ) -> str | None:
        """The reason this specimen cannot be typed, or ``None`` if it can."""
        if ct is None:
            return STATUS_NO_TEMPLATE
        if ct > assay.ct_threshold:
            return STATUS_ABOVE_CT_THRESHOLD
        if not _normalized(genotype_mixture):
            return STATUS_NO_STRAIN_STATE
        if depth <= 0:
            return STATUS_BELOW_READ_FLOOR
        return None

    def _sequence(
        self,
        assay: SequencingAssay,
        truth: Mapping[str, float],
        depth: int,
    ) -> dict[str, int]:
        """Allocate reads over genotypes, then miscall a share of them.

        Miscalled reads are redistributed uniformly over the pathogen's other
        declared genotypes, so accuracy erodes a call toward a *wrong* lineage
        rather than toward nothing.
        """
        labels = _label_space(assay, truth)
        weights = np.array([truth.get(label, 0.0) for label in labels], dtype=float)
        drawn = self.rng.multinomial(depth, weights / weights.sum())
        reads = dict(zip(labels, (int(n) for n in drawn), strict=True))
        if assay.read_accuracy >= 1.0 or len(labels) < 2:
            return {label: count for label, count in reads.items() if count}
        error_rate = 1.0 - assay.read_accuracy
        final = dict.fromkeys(labels, 0)
        for idx, label in enumerate(labels):
            count = reads[label]
            if count <= 0:
                continue
            miscalled = int(self.rng.binomial(count, error_rate))
            final[label] += count - miscalled
            if miscalled <= 0:
                continue
            others = [other for j, other in enumerate(labels) if j != idx]
            spread = self.rng.multinomial(
                miscalled, np.full(len(others), 1.0 / len(others)),
            )
            for other, extra in zip(others, spread, strict=True):
                final[other] += int(extra)
        return {label: count for label, count in final.items() if count}

    def _result(
        self,
        agent_id: int,
        pathogen_id: str,
        epoch: int,
        status: str,
        *,
        assay: SequencingAssay | None = None,
        ct: float | None = None,
        depth: int = 0,
        reads: Mapping[str, int] | None = None,
        calls: list[dict[str, Any]] | None = None,
        truth: Mapping[str, float] | None = None,
    ) -> dict[str, Any]:
        """Assemble one typing payload; only a typed result carries calls."""
        call_list = list(calls or [])
        consensus = next((call["genotype"] for call in call_list), None)
        true_genotypes = sorted(truth or {})
        return {
            "instrument": self.name,
            "agent_id": agent_id,
            "pathogen_id": pathogen_id,
            "epoch": epoch,
            "status": status,
            "informative": status not in (STATUS_NOT_OFFERED, STATUS_NO_STRAIN_STATE),
            "amplicon_target": assay.amplicon_target if assay else "",
            "read_accuracy": assay.read_accuracy if assay else None,
            "ct_value": ct,
            "ct_threshold": assay.ct_threshold if assay else None,
            "read_depth": depth,
            "classified_reads": sum((reads or {}).values()),
            "read_counts": dict(reads or {}),
            "genotype_calls": call_list,
            "consensus_genotype": consensus,
            "mixed_genotype_flag": len(call_list) > 1,
            "true_genotypes": true_genotypes,
            "correct_consensus": (
                None if consensus is None
                else consensus == max(truth or {}, key=lambda g: (truth or {})[g])
            ),
            "cost_usd": assay.cost_usd if assay else 0.0,
        }


def _label_space(
    assay: SequencingAssay,
    truth: Mapping[str, float],
) -> list[str]:
    """Genotypes a read can be assigned to: declared labels plus any observed."""
    labels = list(assay.genotypes)
    labels.extend(g for g in truth if g not in labels)
    return labels


def _normalized(mixture: Mapping[str, float]) -> dict[str, float]:
    """Positive-weight entries of a mixture, renormalized to sum to one."""
    positive = {str(g): float(w) for g, w in mixture.items() if float(w) > 0.0}
    total = sum(positive.values())
    if total <= 0.0:
        return {}
    return {g: w / total for g, w in positive.items()}


def _calls_from_reads(
    reads: Mapping[str, int],
    depth: int,
    min_reads: int,
) -> list[dict[str, Any]]:
    """Genotypes clearing the read floor, most abundant first."""
    total = sum(reads.values()) or depth
    calls = [
        {
            "genotype": genotype,
            "reads": int(count),
            "fraction": round(count / total, 6) if total else 0.0,
        }
        for genotype, count in reads.items()
        if count >= min_reads
    ]
    calls.sort(key=lambda call: (-call["reads"], call["genotype"]))
    return calls
