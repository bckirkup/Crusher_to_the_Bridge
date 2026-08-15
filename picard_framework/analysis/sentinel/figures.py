"""Plots for a sentinel fit: port hazards, visits, fleet-time, decomposition.

Every hazard plot draws the 90% interval, never the mean alone. A port ranking
without intervals is the specific over-claim the spec review objected to: with
one week of person-hours ashore the intervals overlap almost entirely, and a bar
chart of means would hide that.

matplotlib is an optional dependency here as it is for the boundary figures, so
each entry point returns the paths it actually wrote and an empty list is a valid
outcome rather than an error.
"""

from __future__ import annotations

import io
import os
from typing import Any, Sequence

from picard_framework.analysis._io import allowed_roots, ensure_out_dir
from picard_framework.analysis.sentinel.artifacts import (
    MODE_FLEET,
    SentinelArtifacts,
    as_bool,
    as_float,
)
from simulation_utils.paths import prepare_output_directory, validated_open

_HAZARD_LABEL = "Introduction hazard per person-hour ashore"
_FIG_DIR = "figures"


def have_matplotlib() -> bool:
    """Whether figures can be drawn at all in this environment."""
    try:
        import matplotlib  # noqa: F401

        return True
    except ImportError:
        return False


def _savefig(path: str, fig: Any) -> None:
    parent = os.path.dirname(path)
    if parent:
        prepare_output_directory(parent, allowed_roots=allowed_roots())
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    with validated_open(path, "wb", allowed_roots=allowed_roots()) as fh:
        fh.write(buf.getvalue())


def _close(fig: Any) -> None:
    import matplotlib.pyplot as plt

    plt.close(fig)


def _port_label(row: dict[str, Any]) -> str:
    """Port id, flagged when its hazard is not separable from fleet-time."""
    label = str(row.get("port_id") or "?")
    return f"{label} *" if as_bool(row.get("fleet_time_confounded")) else label


def _plot_port_hazards(fig_dir: str, rows: Sequence[dict[str, Any]]) -> str:
    """Ranked pooled hazards with 90% intervals, worst port at the top."""
    import matplotlib.pyplot as plt

    ordered = sorted(rows, key=lambda r: as_float(r.get("hazard_mean"), 0.0))
    means = [as_float(r.get("hazard_mean"), 0.0) for r in ordered]
    lo = [m - as_float(r.get("hazard_q05"), m) for m, r in zip(means, ordered)]
    hi = [as_float(r.get("hazard_q95"), m) - m for m, r in zip(means, ordered)]
    labels = [_port_label(r) for r in ordered]

    fig, ax = plt.subplots(figsize=(7, 0.5 * len(ordered) + 2))
    ax.errorbar(means, range(len(ordered)), xerr=[lo, hi], fmt="o", capsize=3)
    ax.set_yticks(range(len(ordered)))
    ax.set_yticklabels(labels)
    ax.set_xlabel(
        f"{_HAZARD_LABEL}\n(* not separable from that week's fleet-time effect)",
    )
    ax.set_title("Port introduction hazards (mean, 90% CrI)")
    ax.grid(axis="x", alpha=0.3)
    path = os.path.join(fig_dir, "port_hazards.png")
    _savefig(path, fig)
    _close(fig)
    return path


def _plot_visit_hazards(fig_dir: str, rows: Sequence[dict[str, Any]]) -> str:
    """Per-visit hazards by week, one series per port.

    This is the plot to read for a particular call: the per-visit hazard carries
    its own week's fleet-time effect, while the pooled port level does not.
    """
    import matplotlib.pyplot as plt

    weeks = sorted({str(r.get("week")) for r in rows})
    index = {w: i for i, w in enumerate(weeks)}
    by_port: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_port.setdefault(str(row.get("port_id")), []).append(row)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    for offset, (port_id, port_rows) in enumerate(sorted(by_port.items())):
        xs = [index[str(r.get("week"))] + 0.06 * offset for r in port_rows]
        means = [as_float(r.get("hazard_mean"), 0.0) for r in port_rows]
        lo = [m - as_float(r.get("hazard_q05"), m) for m, r in zip(means, port_rows)]
        hi = [as_float(r.get("hazard_q95"), m) - m for m, r in zip(means, port_rows)]
        ax.errorbar(xs, means, yerr=[lo, hi], fmt="o", capsize=3, label=port_id)
    ax.set_xticks(range(len(weeks)))
    ax.set_xticklabels(weeks, rotation=30, ha="right")
    ax.set_ylabel(_HAZARD_LABEL)
    ax.set_title("Per-visit hazards (mean, 90% CrI)")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    path = os.path.join(fig_dir, "visit_hazards.png")
    _savefig(path, fig)
    _close(fig)
    return path


def _plot_fleet_time(fig_dir: str, rows: Sequence[dict[str, Any]]) -> str:
    """Weekly fleet-wide hazard multiplier — the rival to "that port is bad"."""
    import matplotlib.pyplot as plt

    weeks = [str(r.get("week")) for r in rows]
    means = [as_float(r.get("log_effect_mean"), 0.0) for r in rows]
    lo = [m - as_float(r.get("log_effect_q05"), m) for m, r in zip(means, rows)]
    hi = [as_float(r.get("log_effect_q95"), m) - m for m, r in zip(means, rows)]

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.errorbar(range(len(weeks)), means, yerr=[lo, hi], fmt="o-", capsize=3)
    ax.axhline(0.0, color="grey", linewidth=1, linestyle="--")
    ax.set_xticks(range(len(weeks)))
    ax.set_xticklabels(weeks, rotation=30, ha="right")
    ax.set_ylabel("Fleet-time effect (log hazard)")
    ax.set_title("Fleet-wide weekly effect (0 = no fleet-wide shift)")
    ax.grid(axis="y", alpha=0.3)
    path = os.path.join(fig_dir, "fleet_time.png")
    _savefig(path, fig)
    _close(fig)
    return path


def _plot_decomposition(
    fig_dir: str,
    port_rows: Sequence[dict[str, Any]],
    onboard: dict[str, Any],
) -> str | None:
    """Imported vs aboard-baseline vs secondary expected cases.

    Imported cases are summed over ports rather than derived from
    ``import_share``: the share is a ratio of posterior means of different
    quantities, so multiplying it back out would not reproduce the counts.
    """
    import matplotlib.pyplot as plt

    aboard = onboard.get("aboard_cases_mean")
    secondary = onboard.get("secondary_cases_mean")
    if aboard is None or secondary is None:
        return None

    imported = sum(as_float(r.get("n_attributed_cases"), 0.0) for r in port_rows)
    aboard_cases = as_float(aboard, 0.0)
    secondary_cases = as_float(secondary, 0.0)
    share = as_float(onboard.get("import_share_mean"), float("nan"))

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(
        ["imported", "aboard baseline", "secondary"],
        [imported, aboard_cases, secondary_cases],
        color=["#c1462f", "#4a7ab5", "#6f9f4a"],
    )
    ax.set_ylabel("Expected cases (posterior mean)")
    ax.set_title(f"Incidence decomposition (import share {share:.2f})")
    ax.grid(axis="y", alpha=0.3)
    path = os.path.join(fig_dir, "incidence_decomposition.png")
    _savefig(path, fig)
    _close(fig)
    return path


def write_sentinel_figures(out_dir: str, artifacts: SentinelArtifacts) -> list[str]:
    """Draw every figure the artifacts support; empty list without matplotlib."""
    if not have_matplotlib():
        return []
    fig_dir = ensure_out_dir(os.path.join(out_dir, _FIG_DIR))
    paths: list[str] = []
    if artifacts.port_rows:
        paths.append(_plot_port_hazards(fig_dir, artifacts.port_rows))
    if artifacts.mode == MODE_FLEET and artifacts.visit_rows:
        paths.append(_plot_visit_hazards(fig_dir, artifacts.visit_rows))
    if artifacts.week_rows:
        paths.append(_plot_fleet_time(fig_dir, artifacts.week_rows))
    if artifacts.onboard:
        decomposition = _plot_decomposition(
            fig_dir, artifacts.port_rows, artifacts.onboard,
        )
        if decomposition:
            paths.append(decomposition)
    return paths
