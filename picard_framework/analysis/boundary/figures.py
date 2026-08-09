"""Key plots for the pre-boarding decision model."""

from __future__ import annotations

import os
from collections import defaultdict
from typing import Any, Callable

from picard_framework.analysis._io import allowed_roots, ensure_out_dir
from simulation_utils.paths import prepare_output_directory, validated_open

LABEL_EXPECTED_TOTAL_COST = "Expected total cost"
LABEL_PI_INF = "Embarkation prevalence π_inf"


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
    import io

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    with validated_open(path, "wb", allowed_roots=allowed_roots()) as fh:
        fh.write(buf.getvalue())


def _group(
    rows: list[dict[str, Any]], *keys: str
) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    out: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        out[tuple(row.get(k) for k in keys)].append(row)
    return out


def _series_by_platform_policy(
    rows: list[dict[str, Any]],
    y_key: str,
    *,
    skip_p0: bool = False,
    require_y: bool = False,
) -> list[tuple[str, list[tuple[float, float]]]]:
    series: list[tuple[str, list[tuple[float, float]]]] = []
    for (platform, policy), group in sorted(
        _group(rows, "platform_class", "policy").items()
    ):
        if skip_p0 and policy == "P0":
            continue
        pts = []
        for r in group:
            if r.get("pi_inf") is None:
                continue
            if require_y and r.get(y_key) is None:
                continue
            pts.append((float(r["pi_inf"]), float(r[y_key])))
        pts = sorted(pts)
        if pts:
            series.append((f"{platform}/{policy}", pts))
    return series


def _plot_line_series(
    fig_dir: str,
    filename: str,
    title: str,
    ylabel: str,
    series: list[tuple[str, list[tuple[float, float]]]],
    *,
    xlabel: str = LABEL_PI_INF,
    hline: float | None = None,
    figsize: tuple[float, float] = (7, 4.5),
) -> str:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=figsize)
    for label, pts in series:
        ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", label=label)
    if hline is not None:
        ax.axhline(hline, color="gray", lw=0.8)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(fontsize=7, ncol=2)
    path = os.path.join(fig_dir, filename)
    _savefig(path, fig)
    plt.close(fig)
    return path


def _breakeven_by_platform(rows: list[dict[str, Any]]) -> tuple[list[str], list[float]]:
    platforms = sorted(
        {r.get("platform_class") for r in rows if r.get("platform_class")}
    )
    labels: list[str] = []
    values: list[float] = []
    for platform in platforms:
        p0 = {
            float(r["pi_inf"]): float(r["expected_total_cost"])
            for r in rows
            if r.get("platform_class") == platform and r.get("policy") == "P0"
        }
        p2 = {
            float(r["pi_inf"]): float(r["expected_total_cost"])
            for r in rows
            if r.get("platform_class") == platform and r.get("policy") == "P2"
        }
        be = next((pi for pi in sorted(set(p0) & set(p2)) if p2[pi] <= p0[pi]), None)
        if be is not None:
            labels.append(str(platform))
            values.append(be)
    return labels, values


def _write_breakeven(fig_dir: str, rows: list[dict[str, Any]]) -> str:
    import matplotlib.pyplot as plt

    labels, values = _breakeven_by_platform(rows)
    fig, ax = plt.subplots(figsize=(6, 4))
    if values:
        ax.bar(labels, values, color="#2a6f97")
    ax.set_ylabel("Break-even π_inf")
    ax.set_title("Break-even prevalence by platform (P2 vs P0)")
    path = os.path.join(fig_dir, "03_breakeven_by_platform.png")
    _savefig(path, fig)
    plt.close(fig)
    return path


def _write_heatmap(fig_dir: str, se_sp_grid: list[dict[str, Any]]) -> str:
    import matplotlib.pyplot as plt
    import numpy as np

    ses = sorted({float(r["Se_w"]) for r in se_sp_grid})
    sps = sorted({float(r["Sp_w"]) for r in se_sp_grid})
    mat = np.full((len(sps), len(ses)), np.nan)
    lookup = {
        (float(r["Se_w"]), float(r["Sp_w"])): float(r["expected_net_benefit"])
        for r in se_sp_grid
    }
    for i, sp in enumerate(sps):
        for j, se in enumerate(ses):
            mat[i, j] = lookup.get((se, sp), np.nan)
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    im = ax.imshow(mat, origin="lower", aspect="auto", cmap="RdYlGn")
    ax.set_xticks(range(len(ses)))
    ax.set_xticklabels([f"{v:.2f}" for v in ses])
    ax.set_yticks(range(len(sps)))
    ax.set_yticklabels([f"{v:.2f}" for v in sps])
    ax.set_xlabel("Se_w")
    ax.set_ylabel("Sp_w")
    ax.set_title("Net benefit heatmap (Se × Sp)")
    fig.colorbar(im, ax=ax, fraction=0.046)
    path = os.path.join(fig_dir, "06_se_sp_heatmap.png")
    _savefig(path, fig)
    plt.close(fig)
    return path


def _write_platform_comparison(fig_dir: str, rows: list[dict[str, Any]]) -> str:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 4.5))
    pis = sorted({float(r["pi_inf"]) for r in rows if r.get("pi_inf") is not None})
    if pis:
        target_pi = pis[len(pis) // 2]
        subset = [
            r
            for r in rows
            if abs(float(r["pi_inf"]) - target_pi) < 1e-12
            and r.get("policy") in ("P0", "P2")
        ]
        labels = [
            f"{r.get('platform_class')}/{r.get('policy')}"
            for r in sorted(
                subset, key=lambda x: (x.get("platform_class"), x.get("policy"))
            )
        ]
        costs = [
            float(r["expected_total_cost"])
            for r in sorted(
                subset, key=lambda x: (x.get("platform_class"), x.get("policy"))
            )
        ]
        if labels:
            ax.bar(labels, costs, color="#1b4965")
            ax.tick_params(axis="x", rotation=45)
        ax.set_title(f"Platform comparison at π_inf={target_pi}")
        ax.set_ylabel(LABEL_EXPECTED_TOTAL_COST)
    path = os.path.join(fig_dir, "07_platform_comparison.png")
    _savefig(path, fig)
    plt.close(fig)
    return path


def _write_policy_frontier(fig_dir: str, rows: list[dict[str, Any]]) -> str:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 4.5))
    p0_trigger = {
        (r.get("platform_class"), float(r["pi_inf"]), r.get("pathogen")): float(
            r["expected_P_trigger"]
        )
        for r in rows
        if r.get("policy") == "P0"
    }
    for r in rows:
        if r.get("policy") == "P0":
            continue
        key = (r.get("platform_class"), float(r["pi_inf"]), r.get("pathogen"))
        if key not in p0_trigger:
            continue
        avoided = p0_trigger[key] - float(r["expected_P_trigger"])
        ax.scatter(
            avoided,
            float(r["expected_total_cost"]),
            label=f"{r.get('platform_class')}/{r.get('policy')}",
            alpha=0.8,
        )
    ax.set_xlabel("VSP events avoided (ΔP)")
    ax.set_ylabel(LABEL_EXPECTED_TOTAL_COST)
    ax.set_title("Policy frontier: cost vs VSP avoided")
    handles, labels = ax.get_legend_handles_labels()
    uniq = dict(zip(labels, handles))
    ax.legend(uniq.values(), uniq.keys(), fontsize=7, ncol=2)
    path = os.path.join(fig_dir, "08_policy_frontier.png")
    _savefig(path, fig)
    plt.close(fig)
    return path


def write_boundary_figures(
    out_dir: str,
    rows: list[dict[str, Any]],
    *,
    se_sp_grid: list[dict[str, Any]] | None = None,
) -> list[str]:
    """Write spec plots 1–8 when matplotlib is available."""
    if not _have_matplotlib() or not rows:
        return []

    import matplotlib

    matplotlib.use("Agg")

    fig_dir = ensure_out_dir(os.path.join(out_dir, "figures"))
    writers: list[Callable[[], str]] = [
        lambda: _plot_line_series(
            fig_dir,
            "01_cost_vs_prevalence.png",
            "Expected total cost vs prevalence",
            LABEL_EXPECTED_TOTAL_COST,
            _series_by_platform_policy(rows, "expected_total_cost"),
        ),
        lambda: _plot_line_series(
            fig_dir,
            "02_vsp_vs_prevalence.png",
            "VSP trigger probability vs prevalence",
            "P(VSP trigger)",
            _series_by_platform_policy(rows, "expected_P_trigger"),
        ),
        lambda: _write_breakeven(fig_dir, rows),
        lambda: _plot_line_series(
            fig_dir,
            "04_fp_per_vsp_avoided.png",
            "False positives per VSP event avoided",
            "FP per VSP avoided",
            _series_by_platform_policy(
                rows, "false_positives_per_vsp_avoided", skip_p0=True, require_y=True
            ),
        ),
        lambda: _plot_line_series(
            fig_dir,
            "05_voi_vs_prevalence.png",
            "Value of information per passenger (vs P0)",
            "VoI per passenger",
            _series_by_platform_policy(
                rows, "value_of_information_per_pax", skip_p0=True, require_y=True
            ),
            hline=0.0,
        ),
        lambda: _write_platform_comparison(fig_dir, rows),
        lambda: _write_policy_frontier(fig_dir, rows),
    ]
    written = [fn() for fn in writers]
    if se_sp_grid:
        written.insert(5, _write_heatmap(fig_dir, se_sp_grid))
    return written
