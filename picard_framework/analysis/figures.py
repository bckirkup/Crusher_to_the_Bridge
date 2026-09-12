"""Standard campaign analysis figures (matplotlib optional)."""

from __future__ import annotations

import os
from collections import defaultdict
from typing import Any

from picard_framework.analysis._io import allowed_roots, ensure_out_dir
from simulation_utils.paths import prepare_output_directory, validated_open


def _have_matplotlib() -> bool:
    try:
        import matplotlib  # noqa: F401

        return True
    except ImportError:
        return False


def _savefig(path: str, fig: Any) -> None:
    parent = os.path.dirname(path)
    if parent:
        prepare_output_directory(parent, allowed_roots=allowed_roots())
    # Save to bytes then validated_open (path hardening).
    import io

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    with validated_open(path, "wb", allowed_roots=allowed_roots()) as fh:
        fh.write(buf.getvalue())


def _group_mean_curves(
    epoch_rows: list[dict[str, Any]],
    group_key: str,
    y_key: str = "infected",
) -> dict[Any, list[tuple[int, float]]]:
    buckets: dict[Any, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in epoch_rows:
        g = row.get(group_key)
        ep = row.get("epoch")
        if g is None or ep is None:
            continue
        try:
            buckets[g][int(ep)].append(float(row.get(y_key) or 0))
        except (TypeError, ValueError):
            continue
    out: dict[Any, list[tuple[int, float]]] = {}
    for g, by_ep in buckets.items():
        out[g] = sorted(
            (ep, sum(vals) / len(vals)) for ep, vals in by_ep.items() if vals
        )
    return out


def _fig_dose_response(fig_dir: str, run_rows: list[dict[str, Any]], plt: Any) -> str | None:
    dose_points = [
        (r.get("dose_adjustment"), r.get("attack_rate"))
        for r in run_rows
        if r.get("dose_adjustment") is not None and r.get("attack_rate") is not None
    ]
    if not dose_points:
        return None
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter([p[0] for p in dose_points], [p[1] for p in dose_points], alpha=0.7)
    ax.set_xlabel("dose_adjustment")
    ax.set_ylabel("attack_rate")
    ax.set_title("Dose–response (run-level)")
    path = os.path.join(fig_dir, "dose_response.png")
    _savefig(path, fig)
    plt.close(fig)
    return "figures/dose_response.png"


def _heatmap_matrix(
    heat: dict[tuple[str, str], list[float]],
    platforms: list[str],
    survs: list[str],
) -> list[list[float]]:
    mat: list[list[float]] = []
    for platform in platforms:
        row: list[float] = []
        for surv in survs:
            cells = heat.get((platform, surv))
            row.append(sum(cells) / len(cells) if cells else float("nan"))
        mat.append(row)
    return mat


def _fig_surveillance_heatmap(
    fig_dir: str, run_rows: list[dict[str, Any]], plt: Any,
) -> str | None:
    heat: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in run_rows:
        plat = row.get("platform_id")
        surv = row.get("surveillance_strategy")
        ar = row.get("attack_rate")
        if plat is None or surv is None or ar is None:
            continue
        heat[(str(plat), str(surv))].append(float(ar))
    if not heat:
        return None
    platforms = sorted({key[0] for key in heat})
    survs = sorted({key[1] for key in heat})
    mat = _heatmap_matrix(heat, platforms, survs)
    fig, ax = plt.subplots(figsize=(7, 4))
    image = ax.imshow(mat, aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(survs)), survs, rotation=30, ha="right")
    ax.set_yticks(range(len(platforms)), platforms)
    ax.set_title("Mean attack rate by platform × surveillance")
    fig.colorbar(image, ax=ax, fraction=0.046)
    path = os.path.join(fig_dir, "surveillance_heatmap.png")
    _savefig(path, fig)
    plt.close(fig)
    return "figures/surveillance_heatmap.png"


def _fig_vsp_threshold_sweep(
    fig_dir: str, run_rows: list[dict[str, Any]], plt: Any,
) -> str | None:
    vsp_points = [
        (r.get("vsp_lockdown_threshold"), r.get("attack_rate"))
        for r in run_rows
        if r.get("vsp_lockdown_threshold") not in (None, "never")
        and r.get("attack_rate") is not None
    ]
    if not vsp_points:
        return None
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter([p[0] for p in vsp_points], [p[1] for p in vsp_points], alpha=0.7)
    ax.set_xlabel("vsp_lockdown_threshold")
    ax.set_ylabel("attack_rate")
    ax.set_title("VSP threshold sweep")
    path = os.path.join(fig_dir, "vsp_threshold_sweep.png")
    _savefig(path, fig)
    plt.close(fig)
    return "figures/vsp_threshold_sweep.png"


def _fig_epidemic_curves(
    fig_dir: str, epoch_rows: list[dict[str, Any]], plt: Any,
) -> str | None:
    group_key = "pathogen" if any(r.get("pathogen") for r in epoch_rows) else "platform_id"
    curves = _group_mean_curves(epoch_rows, group_key, "infected")
    if not curves:
        return None
    fig, ax = plt.subplots(figsize=(7, 4))
    for label, series in sorted(curves.items(), key=lambda kv: str(kv[0])):
        if not series:
            continue
        ax.plot([p[0] for p in series], [p[1] for p in series], label=str(label))
    ax.set_xlabel("epoch")
    ax.set_ylabel("mean infected")
    ax.set_title(f"Epidemic curves by {group_key}")
    if len(curves) <= 12:
        ax.legend(fontsize=8)
    path = os.path.join(fig_dir, "epidemic_curves.png")
    _savefig(path, fig)
    plt.close(fig)
    return "figures/epidemic_curves.png"


def _boxplot_attack_rates(ax: Any, engines: dict[str, list[float]], labels: list[str]) -> None:
    try:
        ax.boxplot([engines[key] for key in labels], tick_labels=labels)
    except TypeError:
        # Matplotlib < 3.9 used labels=
        ax.boxplot([engines[key] for key in labels], labels=labels)


def _fig_pairwise_exact_match(
    fig_dir: str, run_rows: list[dict[str, Any]], plt: Any,
) -> str | None:
    engines: dict[str, list[float]] = defaultdict(list)
    for row in run_rows:
        eng = row.get("transport_engine")
        ar = row.get("attack_rate")
        if eng is None or ar is None:
            continue
        engines[str(eng)].append(float(ar))
    if len(engines) < 2:
        return None
    fig, ax = plt.subplots(figsize=(6, 4))
    labels = sorted(engines)
    _boxplot_attack_rates(ax, engines, labels)
    ax.set_ylabel("attack_rate")
    ax.set_title("Attack rate by transport engine")
    path = os.path.join(fig_dir, "pairwise_exact_match.png")
    _savefig(path, fig)
    plt.close(fig)
    return "figures/pairwise_exact_match.png"


def write_standard_figures(
    out_dir: str,
    run_rows: list[dict[str, Any]],
    epoch_rows: list[dict[str, Any]],
) -> list[str]:
    """Write standard PNG figures when matplotlib is available.

    Missing factor columns cause individual figures to be skipped.
    """
    if not _have_matplotlib():
        return []

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_dir = ensure_out_dir(os.path.join(out_dir, "figures"))
    written: list[str] = []
    for path in (
        _fig_dose_response(fig_dir, run_rows, plt),
        _fig_surveillance_heatmap(fig_dir, run_rows, plt),
        _fig_vsp_threshold_sweep(fig_dir, run_rows, plt),
        _fig_epidemic_curves(fig_dir, epoch_rows, plt),
        _fig_pairwise_exact_match(fig_dir, run_rows, plt),
    ):
        if path:
            written.append(path)
    return written
