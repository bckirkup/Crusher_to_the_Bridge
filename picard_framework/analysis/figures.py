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

    # 1) dose_response.png — attack_rate vs dose_adjustment
    dose_points = [
        (r.get("dose_adjustment"), r.get("attack_rate"))
        for r in run_rows
        if r.get("dose_adjustment") is not None and r.get("attack_rate") is not None
    ]
    if dose_points:
        fig, ax = plt.subplots(figsize=(6, 4))
        xs = [p[0] for p in dose_points]
        ys = [p[1] for p in dose_points]
        ax.scatter(xs, ys, alpha=0.7)
        ax.set_xlabel("dose_adjustment")
        ax.set_ylabel("attack_rate")
        ax.set_title("Dose–response (run-level)")
        path = os.path.join(fig_dir, "dose_response.png")
        _savefig(path, fig)
        plt.close(fig)
        written.append("figures/dose_response.png")

    # 2) surveillance_heatmap.png — mean AR by platform × surveillance
    heat: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in run_rows:
        plat = r.get("platform_id")
        surv = r.get("surveillance_strategy")
        ar = r.get("attack_rate")
        if plat is None or surv is None or ar is None:
            continue
        heat[(str(plat), str(surv))].append(float(ar))
    if heat:
        platforms = sorted({k[0] for k in heat})
        survs = sorted({k[1] for k in heat})
        mat = []
        for p in platforms:
            mat.append(
                [
                    (sum(heat[(p, s)]) / len(heat[(p, s)]) if heat.get((p, s)) else float("nan"))
                    for s in survs
                ]
            )
        fig, ax = plt.subplots(figsize=(7, 4))
        im = ax.imshow(mat, aspect="auto", cmap="viridis")
        ax.set_xticks(range(len(survs)), survs, rotation=30, ha="right")
        ax.set_yticks(range(len(platforms)), platforms)
        ax.set_title("Mean attack rate by platform × surveillance")
        fig.colorbar(im, ax=ax, fraction=0.046)
        path = os.path.join(fig_dir, "surveillance_heatmap.png")
        _savefig(path, fig)
        plt.close(fig)
        written.append("figures/surveillance_heatmap.png")

    # 3) vsp_threshold_sweep.png — AR vs lockdown threshold
    vsp_points = [
        (r.get("vsp_lockdown_threshold"), r.get("attack_rate"))
        for r in run_rows
        if r.get("vsp_lockdown_threshold") not in (None, "never")
        and r.get("attack_rate") is not None
    ]
    if vsp_points:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.scatter([p[0] for p in vsp_points], [p[1] for p in vsp_points], alpha=0.7)
        ax.set_xlabel("vsp_lockdown_threshold")
        ax.set_ylabel("attack_rate")
        ax.set_title("VSP threshold sweep")
        path = os.path.join(fig_dir, "vsp_threshold_sweep.png")
        _savefig(path, fig)
        plt.close(fig)
        written.append("figures/vsp_threshold_sweep.png")

    # 4) epidemic_curves.png — mean infected by pathogen (or platform)
    group_key = "pathogen" if any(r.get("pathogen") for r in epoch_rows) else "platform_id"
    curves = _group_mean_curves(epoch_rows, group_key, "infected")
    if curves:
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
        written.append("figures/epidemic_curves.png")

    # 5) pairwise_exact_match.png — placeholder from run-level AR by engine
    engines = defaultdict(list)
    for r in run_rows:
        eng = r.get("transport_engine")
        ar = r.get("attack_rate")
        if eng is None or ar is None:
            continue
        engines[str(eng)].append(float(ar))
    if len(engines) >= 2:
        fig, ax = plt.subplots(figsize=(6, 4))
        labels = sorted(engines)
        try:
            ax.boxplot([engines[k] for k in labels], tick_labels=labels)
        except TypeError:
            # Matplotlib < 3.9 used labels=
            ax.boxplot([engines[k] for k in labels], labels=labels)
        ax.set_ylabel("attack_rate")
        ax.set_title("Attack rate by transport engine")
        path = os.path.join(fig_dir, "pairwise_exact_match.png")
        _savefig(path, fig)
        plt.close(fig)
        written.append("figures/pairwise_exact_match.png")

    return written
