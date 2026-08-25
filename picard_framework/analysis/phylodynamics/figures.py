"""Phylodynamic figures, on axes labelled in physical hours (matplotlib optional).

Every x axis is voyage hours and says so in the label, and each title carries
the clock arm it was drawn under. That is the direct lesson of the epoch/day
bug: the error was in durations, so it was invisible in totals and obvious in
any correctly labelled time axis.
"""

from __future__ import annotations

import io
import os
from typing import Any, Sequence

from picard_framework.analysis._io import allowed_roots, ensure_out_dir
from picard_framework.analysis.phylodynamics.artifact import CensusArtifact
from picard_framework.analysis.phylodynamics.detection import DetectionRow
from picard_framework.analysis.phylodynamics.diversity import DiversityRow
from picard_framework.analysis.phylodynamics.information import InformationRow
from simulation_utils.paths import prepare_output_directory, validated_open

HOURS_AXIS_LABEL = "voyage hours (physical)"


def have_matplotlib() -> bool:
    """True when figures can be rendered in this environment."""
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        return False
    return True


def _savefig(path: str, fig: Any) -> None:
    parent = os.path.dirname(path)
    if parent:
        prepare_output_directory(parent, allowed_roots=allowed_roots())
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    with validated_open(path, "wb", allowed_roots=allowed_roots()) as fh:
        fh.write(buf.getvalue())


def clock_caption(census: CensusArtifact) -> str:
    """Arm identity for a figure title, so two arms cannot be confused."""
    return (
        f"clock={census.natural_history_clock}, "
        f"{census.epoch_duration_hours:g} h/epoch"
    )


def _plot(out_dir: str, name: str, draw: Any) -> str | None:
    """Render one figure through ``draw(ax)``; ``None`` without matplotlib."""
    if not have_matplotlib():
        return None
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    try:
        draw(ax)
        ax.set_xlabel(HOURS_AXIS_LABEL)
        path = os.path.join(ensure_out_dir(os.path.join(out_dir, "figures")), name)
        _savefig(path, fig)
    finally:
        plt.close(fig)
    return name


def plot_lineage_diversity(
    out_dir: str,
    census: CensusArtifact,
    rows: Sequence[DiversityRow],
) -> str | None:
    """Richness and effective-lineage trajectories against voyage hours."""
    if not rows:
        return None

    def draw(ax: Any) -> None:
        for pathogen_id in sorted({row.pathogen_id for row in rows}):
            series = [row for row in rows if row.pathogen_id == pathogen_id]
            hours = [row.voyage_hours for row in series]
            ax.plot(hours, [row.richness for row in series], label=f"{pathogen_id} richness")
            ax.plot(
                hours,
                [row.effective_lineages for row in series],
                linestyle="--",
                label=f"{pathogen_id} effective",
            )
        ax.set_ylabel("lineages")
        ax.set_title(f"Lineage diversity ({clock_caption(census)})")
        ax.legend(fontsize=7)

    return _plot(out_dir, "lineage_diversity_hours.png", draw)


def plot_dominance(
    out_dir: str,
    census: CensusArtifact,
    rows: Sequence[DiversityRow],
) -> str | None:
    """Dominant-lineage fraction and compositional turnover per hour."""
    if not rows:
        return None

    def draw(ax: Any) -> None:
        for pathogen_id in sorted({row.pathogen_id for row in rows}):
            series = [row for row in rows if row.pathogen_id == pathogen_id]
            hours = [row.voyage_hours for row in series]
            ax.plot(
                hours,
                [row.dominant_fraction for row in series],
                label=f"{pathogen_id} dominant fraction",
            )
            ax.plot(
                hours,
                [row.turnover for row in series],
                linestyle=":",
                label=f"{pathogen_id} turnover",
            )
        ax.set_ylim(0.0, 1.05)
        ax.set_ylabel("fraction / dissimilarity")
        ax.set_title(f"Dominance and turnover ({clock_caption(census)})")
        ax.legend(fontsize=7)

    return _plot(out_dir, "lineage_dominance_hours.png", draw)


def plot_detection_speed(
    out_dir: str,
    census: CensusArtifact,
    curve: Sequence[dict[str, float]],
) -> str | None:
    """Share of emerged genotypes already detected, against voyage hours."""
    if not curve:
        return None

    def draw(ax: Any) -> None:
        ax.plot(
            [point["voyage_hours"] for point in curve],
            [point["detected_fraction"] for point in curve],
            marker="",
        )
        ax.set_ylim(0.0, 1.05)
        ax.set_ylabel("detected fraction of emerged genotypes")
        ax.set_title(f"Detection speed ({clock_caption(census)})")

    return _plot(out_dir, "detection_speed_hours.png", draw)


def plot_detection_lags(
    out_dir: str,
    census: CensusArtifact,
    rows: Sequence[DetectionRow],
) -> str | None:
    """Per-genotype detection lag in hours; censored genotypes are annotated."""
    detected = [row for row in rows if row.first_detection_lag_hours is not None]
    if not detected:
        return None

    def draw(ax: Any) -> None:
        labels = [f"{row.pathogen_id}:{row.genotype}" for row in detected]
        lags = [row.first_detection_lag_hours or 0.0 for row in detected]
        ax.barh(labels, lags)
        censored = len(rows) - len(detected)
        ax.set_ylabel("genotype")
        ax.set_title(
            f"Detection lag, {censored} genotype(s) never typed "
            f"({clock_caption(census)})",
        )

    return _plot(out_dir, "detection_lag_hours.png", draw)


def plot_information_gain(
    out_dir: str,
    census: CensusArtifact,
    rows_by_channel: dict[str, Sequence[InformationRow]],
) -> str | None:
    """Bits each channel holds over a genotype-blind guess, against hours."""
    if not any(rows_by_channel.values()):
        return None

    def draw(ax: Any) -> None:
        for channel, rows in sorted(rows_by_channel.items()):
            if not rows:
                continue
            ax.plot(
                [row.voyage_hours for row in rows],
                [row.information_gain_bits for row in rows],
                label=channel,
            )
        ax.axhline(0.0, color="black", linewidth=0.6)
        ax.set_ylabel("information gain (bits vs uniform)")
        ax.set_title(f"Lineage information gain ({clock_caption(census)})")
        ax.legend(fontsize=7)

    return _plot(out_dir, "information_gain_hours.png", draw)
