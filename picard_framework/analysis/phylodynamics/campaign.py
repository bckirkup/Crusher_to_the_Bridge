"""Campaign-level phylodynamic observables, one row per run and per arm.

Aggregation refuses to pool: a run's arm is its ``(clock, incubation, epoch
duration)`` triple, and every mean is reported inside one arm. Pooling an
hourly run with a ``legacy_epoch_day`` one would average two different
data-generating processes, which is the mistake the PR 12 run ids exist to
prevent.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from typing import Any

from picard_framework.analysis._io import iter_result_zips, write_csv, write_json
from picard_framework.analysis.phylodynamics.artifact import CensusArtifact
from picard_framework.analysis.phylodynamics.detection import (
    CHANNEL_CLINICAL,
    CHANNEL_WASTEWATER,
)
from picard_framework.analysis.phylodynamics.report import (
    MissingCensusError,
    build_report,
    load_bundle,
    load_census,
)

__all__ = [
    "ARM_UNKNOWN",
    "RUN_COLUMNS",
    "arm_key",
    "arm_summaries",
    "build_campaign_rows",
    "incubation_arm_of_run_id",
    "run_row",
    "write_campaign_tables",
]

ARM_UNKNOWN = "unknown"

# Tags the PR 12 run ids carry, so an arm can be recovered from a result zip
# whose manifest is no longer at hand.
_ARM_TAGS = {"dist": "distribution", "fixed": "fixed_onset"}

RUN_COLUMNS = (
    "run_id",
    "voyage_id",
    "ship_id",
    "natural_history_clock",
    "incubation_arm",
    "epoch_duration_hours",
    "observed",
    "pathogen_id",
    "peak_richness",
    "peak_richness_hours",
    "final_richness",
    "final_effective_lineages",
    "max_effective_lineages",
    "final_dominant_fraction",
    "cumulative_lineages",
    "mean_turnover",
    "final_mean_mutations",
    "final_recombinant_fraction",
    "genotypes_emerged",
    "genotypes_detected",
    "detected_fraction",
    "median_detection_lag_hours",
    "clinical_first_count",
    "wastewater_first_count",
    "clinical_mean_information_gain_bits",
    "wastewater_mean_information_gain_bits",
    "clinical_final_completeness",
    "wastewater_final_completeness",
)

_ARM_FIELDS = (
    "peak_richness",
    "final_effective_lineages",
    "cumulative_lineages",
    "detected_fraction",
    "median_detection_lag_hours",
    "clinical_mean_information_gain_bits",
    "wastewater_mean_information_gain_bits",
)


def incubation_arm_of_run_id(run_id: str) -> str:
    """Incubation arm named by a PR 12 run id, or ``unknown``."""
    for part in run_id.split("_"):
        arm = _ARM_TAGS.get(part)
        if arm is not None:
            return arm
    return ARM_UNKNOWN


def arm_key(row: Mapping[str, Any]) -> str:
    """The arm a run belongs to; rows may only be averaged within one."""
    return (
        f"clock={row['natural_history_clock']}"
        f",incubation={row['incubation_arm']}"
        f",epoch_hours={row['epoch_duration_hours']}"
    )


def _diversity_fields(summary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "peak_richness": summary["peak_richness"],
        "peak_richness_hours": summary["peak_richness_hours"],
        "final_richness": summary["final_richness"],
        "final_effective_lineages": summary["final_effective_lineages"],
        "max_effective_lineages": summary["max_effective_lineages"],
        "final_dominant_fraction": summary["final_dominant_fraction"],
        "cumulative_lineages": summary["final_cumulative_lineages"],
        "mean_turnover": summary["mean_turnover_per_hour"],
        "final_mean_mutations": summary["final_mean_mutations"],
        "final_recombinant_fraction": summary["final_recombinant_fraction"],
    }


def _information_fields(info: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for channel in (CHANNEL_CLINICAL, CHANNEL_WASTEWATER):
        summary = info[channel]
        out[f"{channel}_mean_information_gain_bits"] = summary[
            "mean_information_gain_bits"
        ]
        out[f"{channel}_final_completeness"] = summary["final_completeness"]
    return out


def run_row(
    run_id: str,
    census: CensusArtifact,
    report: Mapping[str, Any],
    pathogen_id: str,
) -> dict[str, Any]:
    """One flat campaign row for one pathogen of one run."""
    summary = report["summary"]
    detection = summary["detection"]
    row: dict[str, Any] = {
        "run_id": run_id,
        "voyage_id": census.voyage_id,
        "ship_id": census.ship_id,
        "natural_history_clock": census.natural_history_clock,
        "incubation_arm": incubation_arm_of_run_id(run_id),
        "epoch_duration_hours": census.epoch_duration_hours,
        "observed": report["arm"]["observed"],
        "pathogen_id": pathogen_id,
        "genotypes_emerged": detection["genotypes_emerged"],
        "genotypes_detected": detection["genotypes_detected"],
        "detected_fraction": detection["detected_fraction"],
        "median_detection_lag_hours": detection["median_detection_lag_hours"],
        "clinical_first_count": detection["clinical_first_count"],
        "wastewater_first_count": detection["wastewater_first_count"],
    }
    row.update(_diversity_fields(summary["diversity"][pathogen_id]))
    row.update(_information_fields(summary["information"]))
    return row


def _rows_for_source(source: str, run_id: str) -> list[dict[str, Any]]:
    census = load_census(source)
    report = build_report(census, load_bundle(source))
    return [
        run_row(run_id, census, report, pathogen_id)
        for pathogen_id in census.pathogen_ids()
    ]


def build_campaign_rows(results_dir: str) -> tuple[list[dict[str, Any]], int]:
    """Per-run phylodynamic rows for every armed run under ``results_dir``.

    Runs with no census are counted rather than raised on: a campaign mixes
    variant-surveillance arms with arms that track no lineages at all.
    """
    rows: list[dict[str, Any]] = []
    unarmed = 0
    for zip_path in iter_result_zips(results_dir):
        run_id = os.path.basename(zip_path)[: -len(".zip")]
        try:
            rows.extend(_rows_for_source(zip_path, run_id))
        except MissingCensusError:
            unarmed += 1
    return rows, unarmed


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def arm_summaries(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Per-arm means, keyed by arm, with the run count that produced them."""
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(arm_key(row), []).append(row)
    out: dict[str, Any] = {}
    for key, arm_rows in sorted(grouped.items()):
        summary: dict[str, Any] = {"n_rows": len(arm_rows)}
        for field in _ARM_FIELDS:
            values = [
                float(row[field]) for row in arm_rows if row.get(field) is not None
            ]
            summary[f"mean_{field}"] = _mean(values)
        out[key] = summary
    return out


def write_campaign_tables(out_dir: str, results_dir: str) -> dict[str, Any]:
    """Write the campaign phylodynamic table and per-arm summary, if any runs.

    Returns a manifest fragment; ``artifacts`` is empty when no run in the
    campaign was armed with a lineage census.
    """
    rows, unarmed = build_campaign_rows(results_dir)
    if not rows:
        return {"n_rows": 0, "unarmed_runs": unarmed, "artifacts": {}}
    write_csv(os.path.join(out_dir, "phylodynamic_runs.csv"), rows, RUN_COLUMNS)
    summaries = arm_summaries(rows)
    write_json(
        os.path.join(out_dir, "phylodynamic_arms.json"),
        {"arms": summaries, "unarmed_runs": unarmed},
    )
    return {
        "n_rows": len(rows),
        "n_arms": len(summaries),
        "unarmed_runs": unarmed,
        "artifacts": {
            "phylodynamic_runs": "phylodynamic_runs.csv",
            "phylodynamic_arms": "phylodynamic_arms.json",
        },
    }
