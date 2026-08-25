"""Assemble one run's phylodynamic report: tables, summary, and figures.

Reads the lineage census (truth) and, when present, the sentinel observation
bundle (what was seen) from a run directory or a campaign result zip. Nothing
here needs ``simulation_history.json``: the census is an aggregate that survives
``compact`` retention, which is what makes this affordable at campaign scale.
"""

from __future__ import annotations

import os
from typing import Any, Mapping, Sequence

from picard_framework.analysis._io import (
    ensure_out_dir,
    load_zip_json,
    read_json,
    safe_path,
    write_csv,
    write_json,
)
from picard_framework.analysis.phylodynamics.artifact import (
    CensusArtifact,
    census_from_dict,
)
from picard_framework.analysis.phylodynamics.compare import (
    channel_information_summary,
    information_rows,
)
from picard_framework.analysis.phylodynamics.detection import (
    CHANNEL_CLINICAL,
    CHANNEL_WASTEWATER,
    DETECTION_COLUMNS,
    detection_rows,
    detection_speed_curve,
    detection_summary,
)
from picard_framework.analysis.phylodynamics.diversity import (
    DIVERSITY_COLUMNS,
    all_diversity_rows,
    diversity_rows,
    diversity_summary,
)
from picard_framework.analysis.phylodynamics.figures import (
    plot_detection_lags,
    plot_detection_speed,
    plot_dominance,
    plot_information_gain,
    plot_lineage_diversity,
)
from picard_framework.analysis.phylodynamics.information import (
    INFORMATION_COLUMNS,
    InformationRow,
)
from picard_framework.analysis.sentinel.observations import (
    ObservationBundle,
    bundle_from_dict,
)

LINEAGE_CENSUS_FILENAME = "lineage_census.json"
SENTINEL_LINE_LIST_FILENAME = "sentinel_line_list.json"
DEFAULT_CURVE_POINTS = 25


class MissingCensusError(FileNotFoundError):
    """Raised when a run carries no lineage census to analyse."""


def _load_json_member(source: str, filename: str) -> Any | None:
    """Read ``filename`` from a run directory or a campaign result zip."""
    if source.endswith(".zip"):
        return load_zip_json(safe_path(source), filename)
    path = os.path.join(source, filename)
    if not os.path.exists(safe_path(path)):
        return None
    return read_json(safe_path(path))


def load_census(source: str) -> CensusArtifact:
    """Load the lineage census of a run directory or result zip."""
    payload = _load_json_member(source, LINEAGE_CENSUS_FILENAME)
    if not isinstance(payload, Mapping):
        raise MissingCensusError(
            f"no {LINEAGE_CENSUS_FILENAME} in {source!r}: the run was not armed "
            "with variant surveillance",
        )
    return census_from_dict(payload)


def load_bundle(source: str) -> ObservationBundle | None:
    """Load the sentinel observation bundle of a run, if it collected one."""
    payload = _load_json_member(source, SENTINEL_LINE_LIST_FILENAME)
    if not isinstance(payload, Mapping):
        return None
    return bundle_from_dict(dict(payload))


def hours_grid(census: CensusArtifact, points: int = DEFAULT_CURVE_POINTS) -> tuple[float, ...]:
    """Evenly spaced physical-hour grid spanning the census."""
    if not census.epochs or points < 1:
        return ()
    last = max(row.epoch for row in census.epochs)
    end = census.hours(last)
    if points == 1 or end <= 0.0:
        return (end,)
    step = end / (points - 1)
    return tuple(round(step * i, 6) for i in range(points))


def _diversity_summaries(census: CensusArtifact) -> dict[str, Any]:
    return {
        pathogen_id: diversity_summary(diversity_rows(census, pathogen_id))
        for pathogen_id in census.pathogen_ids()
    }


def build_report(
    census: CensusArtifact,
    bundle: ObservationBundle | None,
    *,
    curve_points: int = DEFAULT_CURVE_POINTS,
) -> dict[str, Any]:
    """Every phylodynamic table and summary for one run, in memory."""
    div_rows = all_diversity_rows(census)
    det_rows = detection_rows(census, bundle)
    grid = hours_grid(census, curve_points)
    info: dict[str, tuple[InformationRow, ...]] = {
        channel: information_rows(census, bundle, channel)
        for channel in (CHANNEL_CLINICAL, CHANNEL_WASTEWATER)
    }
    return {
        "arm": {
            "voyage_id": census.voyage_id,
            "ship_id": census.ship_id,
            "natural_history_clock": census.natural_history_clock,
            "epoch_duration_hours": census.epoch_duration_hours,
            "observed": bundle is not None,
        },
        "diversity_rows": div_rows,
        "detection_rows": det_rows,
        "detection_curve": detection_speed_curve(det_rows, grid),
        "information_rows": info,
        "summary": {
            "diversity": _diversity_summaries(census),
            "detection": detection_summary(det_rows),
            "information": {
                channel: channel_information_summary(rows)
                for channel, rows in info.items()
            },
        },
    }


def _write_tables(out: str, report: Mapping[str, Any]) -> list[str]:
    written: list[str] = []
    write_csv(
        os.path.join(out, "lineage_diversity.csv"),
        [row.as_dict() for row in report["diversity_rows"]],
        DIVERSITY_COLUMNS,
    )
    written.append("lineage_diversity.csv")
    write_csv(
        os.path.join(out, "genotype_detection.csv"),
        [row.as_dict() for row in report["detection_rows"]],
        DETECTION_COLUMNS,
    )
    written.append("genotype_detection.csv")
    for channel, rows in sorted(report["information_rows"].items()):
        name = f"information_gain_{channel}.csv"
        write_csv(
            os.path.join(out, name),
            [row.as_dict() for row in rows],
            INFORMATION_COLUMNS,
        )
        written.append(name)
    write_json(
        os.path.join(out, "phylodynamic_summary.json"),
        {
            "arm": report["arm"],
            "summary": report["summary"],
            "detection_curve": list(report["detection_curve"]),
        },
    )
    written.append("phylodynamic_summary.json")
    return written


def _write_figures(
    out: str,
    census: CensusArtifact,
    report: Mapping[str, Any],
) -> list[str]:
    div_rows: Sequence[Any] = report["diversity_rows"]
    candidates = [
        plot_lineage_diversity(out, census, div_rows),
        plot_dominance(out, census, div_rows),
        plot_detection_speed(out, census, report["detection_curve"]),
        plot_detection_lags(out, census, report["detection_rows"]),
        plot_information_gain(out, census, dict(report["information_rows"])),
    ]
    return [name for name in candidates if name]


def write_report(
    source: str,
    out_dir: str,
    *,
    curve_points: int = DEFAULT_CURVE_POINTS,
) -> dict[str, Any]:
    """Analyse one run and write its tables, summary, and figures."""
    census = load_census(source)
    bundle = load_bundle(source)
    report = build_report(census, bundle, curve_points=curve_points)
    out = ensure_out_dir(out_dir)
    names = _write_tables(out, report)
    figures = _write_figures(out, census, report)
    return {
        "out_dir": out,
        "arm": report["arm"],
        "tables": names,
        "figures": figures,
        "summary": report["summary"],
    }
