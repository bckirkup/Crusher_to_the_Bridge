"""Pair the census truth with what each channel had reported, epoch by epoch.

Observation is cumulative and truth is instantaneous, deliberately: a
surveillance programme at hour *t* knows every call returned up to *t*, and is
asked what is circulating now. Clinical calls are weighted by case count,
wastewater calls by reads, because that is the evidence each channel carries.
"""

from __future__ import annotations

from typing import Any, Mapping

from picard_framework.analysis.phylodynamics.artifact import CensusArtifact
from picard_framework.analysis.phylodynamics.detection import (
    CHANNEL_CLINICAL,
    CHANNEL_WASTEWATER,
    CHANNELS,
)
from picard_framework.analysis.phylodynamics.information import (
    InformationRow,
    information_row,
)
from picard_framework.analysis.sentinel.observations import ObservationBundle


def truth_composition(
    census: CensusArtifact,
    pathogen_id: str,
    epoch: int,
) -> dict[str, float]:
    """Genotype carrier counts for one pathogen at one epoch."""
    out: dict[str, float] = {}
    for row in census.series(pathogen_id):
        if row.epoch != epoch:
            continue
        for strain_id, count in row.lineage_counts.items():
            genotype = census.genotype_of(strain_id)
            if not genotype or count <= 0:
                continue
            out[genotype] = out.get(genotype, 0.0) + float(count)
    return out


def _clinical_observed(
    bundle: ObservationBundle,
    pathogen_id: str,
    epoch: int,
) -> dict[str, float]:
    out: dict[str, float] = {}
    for case in bundle.clinical_cases:
        if not case.genotype or (case.pathogen or pathogen_id) != pathogen_id:
            continue
        seen = case.report_epoch if case.report_epoch is not None else case.onset_epoch
        if seen > epoch:
            continue
        out[case.genotype] = out.get(case.genotype, 0.0) + 1.0
    return out


def _wastewater_observed(
    bundle: ObservationBundle,
    pathogen_id: str,
    epoch: int,
    hours_per_epoch: float,
) -> dict[str, float]:
    out: dict[str, float] = {}
    horizon = float(epoch) * hours_per_epoch
    for sample in bundle.wastewater_samples:
        if sample.profile_key != pathogen_id:
            continue
        available = float(sample.sample_epoch) * hours_per_epoch + float(
            sample.turnaround_hours or 0.0,
        )
        if available > horizon:
            continue
        for call in sample.lineage_calls:
            if call.reads <= 0 or not call.genotype:
                continue
            out[call.genotype] = out.get(call.genotype, 0.0) + float(call.reads)
    return out


def observed_composition(
    bundle: ObservationBundle | None,
    pathogen_id: str,
    epoch: int,
    hours_per_epoch: float,
    channel: str,
) -> dict[str, float]:
    """Cumulative genotype evidence one channel holds at ``epoch``."""
    if channel not in CHANNELS:
        raise ValueError(f"unknown detection channel: {channel!r}")
    if bundle is None:
        return {}
    if channel == CHANNEL_CLINICAL:
        return _clinical_observed(bundle, pathogen_id, epoch)
    return _wastewater_observed(bundle, pathogen_id, epoch, hours_per_epoch)


def information_rows(
    census: CensusArtifact,
    bundle: ObservationBundle | None,
    channel: str,
) -> tuple[InformationRow, ...]:
    """Information-gain trajectory of one channel over all pathogens."""
    rows: list[InformationRow] = []
    for pathogen_id in census.pathogen_ids():
        for entry in census.series(pathogen_id):
            rows.append(
                information_row(
                    pathogen_id=pathogen_id,
                    epoch=entry.epoch,
                    voyage_hours=census.hours(entry.epoch),
                    truth=truth_composition(census, pathogen_id, entry.epoch),
                    observed=observed_composition(
                        bundle,
                        pathogen_id,
                        entry.epoch,
                        census.epoch_duration_hours,
                        channel,
                    ),
                ),
            )
    return tuple(rows)


def channel_information_summary(
    rows: tuple[InformationRow, ...],
) -> dict[str, Any]:
    """Voyage-level information summary of one channel's trajectory."""
    informative = [row for row in rows if row.truth_genotypes > 0]
    if not informative:
        return {
            "epochs_with_truth": 0,
            "mean_information_gain_bits": 0.0,
            "final_information_gain_bits": 0.0,
            "mean_js_distance": 1.0,
            "final_completeness": 0.0,
        }
    return {
        "epochs_with_truth": len(informative),
        "mean_information_gain_bits": sum(
            row.information_gain_bits for row in informative
        )
        / len(informative),
        "final_information_gain_bits": informative[-1].information_gain_bits,
        "mean_js_distance": sum(row.js_distance for row in informative)
        / len(informative),
        "final_completeness": informative[-1].completeness,
    }


def channel_summaries(
    census: CensusArtifact,
    bundle: ObservationBundle | None,
) -> dict[str, Mapping[str, Any]]:
    """Information summary per channel, keyed by channel name."""
    return {
        channel: channel_information_summary(
            information_rows(census, bundle, channel),
        )
        for channel in (CHANNEL_CLINICAL, CHANNEL_WASTEWATER)
    }
