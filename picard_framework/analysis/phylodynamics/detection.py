"""Detection speed: when a genotype existed aboard versus when it was seen.

Truth comes from the lineage census (a genotype exists from the first epoch a
host carries a lineage of it), observation from the sentinel bundle: a clinical
amplicon call or a wastewater lineage call. The lag between them, in voyage
hours, is the observable Paper 3's "cruise ships as phylogenomic observatories"
claim rests on.

Reporting hours, not sampling hours: a wastewater library is evidence when it
comes back, so ``turnaround_hours`` is added where the sample carries it. A
genotype that is never typed gets ``None``, which is a censored observation and
is kept as one rather than dropped.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from picard_framework.analysis.phylodynamics.artifact import CensusArtifact
from picard_framework.analysis.sentinel.observations import ObservationBundle

CHANNEL_CLINICAL = "clinical"
CHANNEL_WASTEWATER = "wastewater"
CHANNELS = (CHANNEL_CLINICAL, CHANNEL_WASTEWATER)

DETECTION_COLUMNS = (
    "pathogen_id",
    "genotype",
    "emergence_hours",
    "clinical_detection_hours",
    "wastewater_detection_hours",
    "first_detection_hours",
    "clinical_lag_hours",
    "wastewater_lag_hours",
    "first_detection_lag_hours",
    "detected",
)


@dataclass(frozen=True)
class DetectionRow:
    """One genotype's truth emergence and per-channel first observation."""

    pathogen_id: str
    genotype: str
    emergence_hours: float
    clinical_detection_hours: float | None
    wastewater_detection_hours: float | None
    first_detection_hours: float | None
    clinical_lag_hours: float | None
    wastewater_lag_hours: float | None
    first_detection_lag_hours: float | None
    detected: bool

    def as_dict(self) -> dict[str, Any]:
        """Row form for CSV / JSON writers."""
        return asdict(self)


def genotype_emergence_hours(census: CensusArtifact) -> dict[tuple[str, str], float]:
    """First voyage hour each ``(pathogen, genotype)`` is carried by a host.

    Lineages the registry has collected are skipped rather than guessed at: an
    unknown genotype would otherwise become a spurious empty-string variant.
    """
    out: dict[tuple[str, str], float] = {}
    for row in sorted(census.epochs, key=lambda entry: entry.epoch):
        hours = census.hours(row.epoch)
        for strain_id, count in row.lineage_counts.items():
            if count <= 0:
                continue
            genotype = census.genotype_of(strain_id)
            if not genotype:
                continue
            out.setdefault((row.pathogen_id, genotype), hours)
    return out


def clinical_detection_hours(
    bundle: ObservationBundle,
    epoch_duration_hours: float,
) -> dict[tuple[str, str], float]:
    """First reporting hour each ``(pathogen, genotype)`` was typed clinically.

    Keyed by pathogen as well as genotype: two pathogens may name a lineage the
    same way, and crediting one's typing to the other would flatter detection.
    """
    out: dict[tuple[str, str], float] = {}
    for case in bundle.clinical_cases:
        if not case.genotype or not case.pathogen:
            continue
        epoch = case.report_epoch if case.report_epoch is not None else case.onset_epoch
        hours = float(epoch) * epoch_duration_hours
        key = (case.pathogen, case.genotype)
        current = out.get(key)
        if current is None or hours < current:
            out[key] = hours
    return out


def wastewater_detection_hours(
    bundle: ObservationBundle,
    epoch_duration_hours: float,
) -> dict[tuple[str, str], float]:
    """First reporting hour each ``(pathogen, genotype)`` was resolved in sewage."""
    out: dict[tuple[str, str], float] = {}
    for sample in bundle.wastewater_samples:
        if not sample.pathogen:
            continue
        available = float(sample.sample_epoch) * epoch_duration_hours + float(
            sample.turnaround_hours or 0.0,
        )
        for call in sample.lineage_calls:
            if call.reads <= 0 or not call.genotype:
                continue
            key = (sample.pathogen, call.genotype)
            current = out.get(key)
            if current is None or available < current:
                out[key] = available
    return out


def _lag(detection: float | None, emergence: float) -> float | None:
    return None if detection is None else max(0.0, detection - emergence)


def _earliest(values: Iterable[float | None]) -> float | None:
    seen = [v for v in values if v is not None]
    return min(seen) if seen else None


def detection_rows(
    census: CensusArtifact,
    bundle: ObservationBundle | None,
) -> tuple[DetectionRow, ...]:
    """Per-genotype detection table for one run.

    With no observation bundle every genotype is censored, which is the correct
    reading of an arm that sequenced nothing rather than an error.
    """
    hours_per_epoch = census.epoch_duration_hours
    clinical = {} if bundle is None else clinical_detection_hours(bundle, hours_per_epoch)
    wastewater = (
        {} if bundle is None else wastewater_detection_hours(bundle, hours_per_epoch)
    )
    rows: list[DetectionRow] = []
    for (pathogen_id, genotype), emergence in sorted(
        genotype_emergence_hours(census).items(),
    ):
        clin = clinical.get((pathogen_id, genotype))
        waste = wastewater.get((pathogen_id, genotype))
        first = _earliest((clin, waste))
        rows.append(
            DetectionRow(
                pathogen_id=pathogen_id,
                genotype=genotype,
                emergence_hours=emergence,
                clinical_detection_hours=clin,
                wastewater_detection_hours=waste,
                first_detection_hours=first,
                clinical_lag_hours=_lag(clin, emergence),
                wastewater_lag_hours=_lag(waste, emergence),
                first_detection_lag_hours=_lag(first, emergence),
                detected=first is not None,
            ),
        )
    return tuple(rows)


def detection_speed_curve(
    rows: tuple[DetectionRow, ...],
    hours_grid: Iterable[float],
) -> tuple[dict[str, float], ...]:
    """Fraction of emerged genotypes detected by each hour on ``hours_grid``.

    Denominator is the genotypes that had emerged by that hour, so the curve
    reads as "of what was aboard, how much had been seen" rather than being
    dragged down by variants that did not exist yet.
    """
    curve: list[dict[str, float]] = []
    for hours in hours_grid:
        emerged = [row for row in rows if row.emergence_hours <= hours]
        detected = [
            row
            for row in emerged
            if row.first_detection_hours is not None
            and row.first_detection_hours <= hours
        ]
        fraction = len(detected) / len(emerged) if emerged else 0.0
        curve.append(
            {
                "voyage_hours": float(hours),
                "genotypes_emerged": float(len(emerged)),
                "genotypes_detected": float(len(detected)),
                "detected_fraction": fraction,
            },
        )
    return tuple(curve)


def detection_summary(rows: tuple[DetectionRow, ...]) -> dict[str, Any]:
    """Voyage-level detection summary, censoring kept explicit."""
    lags = [
        row.first_detection_lag_hours
        for row in rows
        if row.first_detection_lag_hours is not None
    ]
    return {
        "genotypes_emerged": len(rows),
        "genotypes_detected": len(lags),
        "detected_fraction": (len(lags) / len(rows)) if rows else 0.0,
        "median_detection_lag_hours": _median(lags),
        "max_detection_lag_hours": max(lags) if lags else None,
        "clinical_first_count": sum(
            1 for row in rows if _channel_first(row) == CHANNEL_CLINICAL
        ),
        "wastewater_first_count": sum(
            1 for row in rows if _channel_first(row) == CHANNEL_WASTEWATER
        ),
    }


def _channel_first(row: DetectionRow) -> str | None:
    """Which channel saw a genotype first (``None`` when neither did)."""
    clin = row.clinical_detection_hours
    waste = row.wastewater_detection_hours
    if clin is None and waste is None:
        return None
    if waste is None or (clin is not None and clin <= waste):
        return CHANNEL_CLINICAL
    return CHANNEL_WASTEWATER


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[mid]
    return 0.5 * (ordered[mid - 1] + ordered[mid])
