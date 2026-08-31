"""The lineage census artifact, and the clock every observable is read on.

A run's phylogenomic truth: the per-epoch carrier count of every lineage, plus
the strain metadata (genotype, generation, mutations, parents) needed to say
what a sequencing channel *should* have reported. Written by
``ShipSimulation._write_lineage_census``.

Epochs are the storage unit and physical hours are the reporting unit: the
artifact carries ``epoch_duration_hours`` so no consumer has to assume one,
which is the mistake ``docs/history/epoch_time_unit_audit.md`` documents.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

LINEAGE_CENSUS_SCHEMA_VERSION = "1.0.0"
DEFAULT_EPOCH_DURATION_HOURS = 1.0


class LineageCensusError(ValueError):
    """Raised when a lineage census artifact cannot be read as one."""


@dataclass(frozen=True)
class CensusEpoch:
    """One pathogen's lineage composition at one epoch."""

    epoch: int
    pathogen_id: str
    lineage_counts: Mapping[str, int]
    total_carriers: int
    num_lineages: int
    dominant_strain_id: str
    dominant_fraction: float


@dataclass(frozen=True)
class StrainMeta:
    """What a lineage is, for the observables that need more than its id."""

    strain_id: str
    pathogen_id: str
    genotype: str
    generation: int
    n_mutations: int
    origin: str
    recombinant: bool
    immune_escape: float


@dataclass(frozen=True)
class CensusArtifact:
    """A run's census series plus the strain metadata and the run's clock."""

    voyage_id: str
    ship_id: str
    epoch_duration_hours: float
    natural_history_clock: str
    epochs: tuple[CensusEpoch, ...]
    strains: Mapping[str, StrainMeta]
    founders: Mapping[str, tuple[str, ...]]

    def hours(self, epoch: int) -> float:
        """Voyage hours elapsed at ``epoch`` (the reporting axis)."""
        return float(epoch) * self.epoch_duration_hours

    def pathogen_ids(self) -> tuple[str, ...]:
        """Pathogens with at least one census row, in stable order."""
        return tuple(sorted({row.pathogen_id for row in self.epochs}))

    def series(self, pathogen_id: str) -> tuple[CensusEpoch, ...]:
        """Census rows for one pathogen, ordered by epoch."""
        rows = [row for row in self.epochs if row.pathogen_id == pathogen_id]
        return tuple(sorted(rows, key=lambda row: row.epoch))

    def genotype_of(self, strain_id: str) -> str:
        """Genotype of a lineage, or ``""`` when the registry forgot it.

        Extinct lineages with no living descendant are collected during the run
        (``StrainRegistry.collect``), so a census row can name an id the strain
        table no longer carries. That is expected, not corruption.
        """
        meta = self.strains.get(strain_id)
        return "" if meta is None else meta.genotype


def _require_float(raw: Mapping[str, Any], key: str, default: float) -> float:
    value = raw.get(key, default)
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise LineageCensusError(f"{key} must be a number, got {value!r}") from exc
    if out <= 0.0:
        raise LineageCensusError(f"{key} must be > 0, got {out}")
    return out


def _census_epoch(raw: Mapping[str, Any]) -> CensusEpoch:
    counts_raw = raw.get("lineage_counts") or {}
    if not isinstance(counts_raw, Mapping):
        raise LineageCensusError("lineage_counts must be an object")
    counts = {str(sid): int(n) for sid, n in counts_raw.items()}
    total = int(raw.get("total_carriers", sum(counts.values())))
    if total != sum(counts.values()):
        raise LineageCensusError(
            f"total_carriers {total} disagrees with lineage_counts "
            f"{sum(counts.values())} at epoch {raw.get('epoch')!r}",
        )
    return CensusEpoch(
        epoch=int(raw["epoch"]),
        pathogen_id=str(raw["pathogen_id"]),
        lineage_counts=counts,
        total_carriers=total,
        num_lineages=int(raw.get("num_lineages", len(counts))),
        dominant_strain_id=str(raw.get("dominant_strain_id") or ""),
        dominant_fraction=float(raw.get("dominant_fraction", 0.0)),
    )


def _strain_meta(raw: Mapping[str, Any]) -> StrainMeta:
    return StrainMeta(
        strain_id=str(raw["strain_id"]),
        pathogen_id=str(raw["pathogen_id"]),
        genotype=str(raw.get("genotype") or ""),
        generation=int(raw.get("generation", 0)),
        n_mutations=int(raw.get("n_mutations", 0)),
        origin=str(raw.get("origin") or ""),
        recombinant=bool(raw.get("recombinant", False)),
        immune_escape=float(raw.get("immune_escape", 0.0)),
    )


def census_from_dict(payload: Mapping[str, Any]) -> CensusArtifact:
    """Parse a ``lineage_census.json`` payload."""
    snapshots = payload.get("snapshots")
    if not isinstance(snapshots, Sequence) or isinstance(snapshots, (str, bytes)):
        raise LineageCensusError("lineage census payload needs a snapshots list")
    strains_raw = payload.get("strains") or []
    if not isinstance(strains_raw, Sequence):
        raise LineageCensusError("strains must be a list")
    strains = {}
    for entry in strains_raw:
        if not isinstance(entry, Mapping):
            raise LineageCensusError("each strain entry must be an object")
        meta = _strain_meta(entry)
        strains[meta.strain_id] = meta
    founders_raw = payload.get("founders") or {}
    if not isinstance(founders_raw, Mapping):
        raise LineageCensusError("founders must be an object")
    rows = []
    for entry in snapshots:
        if not isinstance(entry, Mapping):
            raise LineageCensusError("each snapshot must be an object")
        rows.append(_census_epoch(entry))
    return CensusArtifact(
        voyage_id=str(payload.get("voyage_id") or ""),
        ship_id=str(payload.get("ship_id") or ""),
        epoch_duration_hours=_require_float(
            payload, "epoch_duration_hours", DEFAULT_EPOCH_DURATION_HOURS,
        ),
        natural_history_clock=str(payload.get("natural_history_clock") or "hours"),
        epochs=tuple(rows),
        strains=strains,
        founders={
            str(pid): tuple(str(sid) for sid in sids)
            for pid, sids in founders_raw.items()
        },
    )
