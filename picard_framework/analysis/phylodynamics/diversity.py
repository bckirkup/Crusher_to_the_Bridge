"""Diversity observables over voyage hours (Paper 3 §7).

Every row is one pathogen at one epoch, reported at its physical hour: a
richness that rises with the mutation rate is only interpretable per hour, and
a curve plotted against a bare epoch index is how a 24x timing error survived
review (``docs/history/epoch_time_unit_audit.md``).

Richness counts lineages; ``effective_lineages`` is ``exp(H)``, the number of
equally-common lineages that would carry the same Shannon entropy, which is the
diversity a sequencing channel can actually hope to resolve.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from picard_framework.analysis.phylodynamics.artifact import CensusArtifact, CensusEpoch

DIVERSITY_COLUMNS = (
    "pathogen_id",
    "epoch",
    "voyage_hours",
    "carriers",
    "richness",
    "shannon_bits",
    "effective_lineages",
    "dominant_fraction",
    "cumulative_lineages",
    "turnover",
    "mean_generation",
    "mean_mutations",
    "recombinant_fraction",
)


@dataclass(frozen=True)
class DiversityRow:
    """One pathogen's diversity state at one voyage hour."""

    pathogen_id: str
    epoch: int
    voyage_hours: float
    carriers: int
    richness: int
    shannon_bits: float
    effective_lineages: float
    dominant_fraction: float
    cumulative_lineages: int
    turnover: float
    mean_generation: float
    mean_mutations: float
    recombinant_fraction: float

    def as_dict(self) -> dict[str, Any]:
        """Row form for CSV / JSON writers."""
        return asdict(self)


def frequencies(counts: Mapping[str, int]) -> dict[str, float]:
    """Carrier counts as a frequency distribution (empty for no carriers)."""
    total = sum(int(n) for n in counts.values())
    if total <= 0:
        return {}
    return {str(sid): int(n) / total for sid, n in counts.items() if int(n) > 0}


def shannon_bits(counts: Mapping[str, int]) -> float:
    """Shannon entropy of a lineage distribution, in bits."""
    freqs = frequencies(counts)
    return -sum(p * math.log2(p) for p in freqs.values() if p > 0.0)


def effective_lineages(counts: Mapping[str, int]) -> float:
    """``exp(H)`` in nats: equally-common lineages of the same entropy."""
    freqs = frequencies(counts)
    if not freqs:
        return 0.0
    entropy_nats = -sum(p * math.log(p) for p in freqs.values() if p > 0.0)
    return math.exp(entropy_nats)


def bray_curtis_turnover(
    previous: Mapping[str, int],
    current: Mapping[str, int],
) -> float:
    """Bray-Curtis dissimilarity between two lineage compositions.

    ``0.0`` for identical composition, ``1.0`` when the two epochs share no
    lineage at all; the per-hour rate of lineage replacement, which is what a
    detection channel has to keep up with.
    """
    prev_freq = frequencies(previous)
    cur_freq = frequencies(current)
    if not prev_freq and not cur_freq:
        return 0.0
    if not prev_freq or not cur_freq:
        return 1.0
    shared = sum(
        min(prev_freq.get(sid, 0.0), cur_freq.get(sid, 0.0))
        for sid in set(prev_freq) | set(cur_freq)
    )
    return max(0.0, 1.0 - shared)


def _weighted_lineage_traits(
    census: CensusArtifact,
    row: CensusEpoch,
) -> tuple[float, float, float]:
    """Carrier-weighted mean generation, mean mutations, recombinant share."""
    total = row.total_carriers
    if total <= 0:
        return (0.0, 0.0, 0.0)
    generations = 0.0
    mutations = 0.0
    recombinant = 0.0
    for strain_id, count in row.lineage_counts.items():
        meta = census.strains.get(strain_id)
        if meta is None:
            continue
        generations += meta.generation * count
        mutations += meta.n_mutations * count
        recombinant += count if meta.recombinant else 0
    return (generations / total, mutations / total, recombinant / total)


def diversity_rows(census: CensusArtifact, pathogen_id: str) -> tuple[DiversityRow, ...]:
    """Diversity trajectory for one pathogen, ordered by epoch."""
    seen: set[str] = set()
    previous: Mapping[str, int] = {}
    rows: list[DiversityRow] = []
    for entry in census.series(pathogen_id):
        seen |= set(entry.lineage_counts)
        generation, mutations, recombinant = _weighted_lineage_traits(census, entry)
        rows.append(
            DiversityRow(
                pathogen_id=pathogen_id,
                epoch=entry.epoch,
                voyage_hours=census.hours(entry.epoch),
                carriers=entry.total_carriers,
                richness=entry.num_lineages,
                shannon_bits=shannon_bits(entry.lineage_counts),
                effective_lineages=effective_lineages(entry.lineage_counts),
                dominant_fraction=entry.dominant_fraction,
                cumulative_lineages=len(seen),
                turnover=bray_curtis_turnover(previous, entry.lineage_counts),
                mean_generation=generation,
                mean_mutations=mutations,
                recombinant_fraction=recombinant,
            ),
        )
        previous = entry.lineage_counts
    return tuple(rows)


def all_diversity_rows(census: CensusArtifact) -> tuple[DiversityRow, ...]:
    """Diversity trajectories for every pathogen in the census."""
    out: list[DiversityRow] = []
    for pathogen_id in census.pathogen_ids():
        out.extend(diversity_rows(census, pathogen_id))
    return tuple(out)


def diversity_summary(rows: tuple[DiversityRow, ...]) -> dict[str, Any]:
    """Voyage-level diversity summary of one pathogen's trajectory."""
    if not rows:
        return {
            "peak_richness": 0,
            "peak_richness_hours": None,
            "final_cumulative_lineages": 0,
            "max_shannon_bits": 0.0,
            "mean_turnover_per_hour": 0.0,
            "final_recombinant_fraction": 0.0,
            "final_richness": 0,
            "final_effective_lineages": 0.0,
            "max_effective_lineages": 0.0,
            "final_dominant_fraction": 0.0,
            "final_mean_mutations": 0.0,
        }
    peak = max(rows, key=lambda row: row.richness)
    hours_span = max(rows[-1].voyage_hours, rows[0].voyage_hours) or 1.0
    return {
        "peak_richness": peak.richness,
        "peak_richness_hours": peak.voyage_hours,
        "final_cumulative_lineages": rows[-1].cumulative_lineages,
        "max_shannon_bits": max(row.shannon_bits for row in rows),
        "mean_turnover_per_hour": sum(row.turnover for row in rows) / hours_span,
        "final_recombinant_fraction": rows[-1].recombinant_fraction,
        "final_richness": rows[-1].richness,
        "final_effective_lineages": rows[-1].effective_lineages,
        "max_effective_lineages": max(row.effective_lineages for row in rows),
        "final_dominant_fraction": rows[-1].dominant_fraction,
        "final_mean_mutations": rows[-1].mean_mutations,
    }
