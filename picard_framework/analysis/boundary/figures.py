"""Key plots for the pre-boarding decision model."""

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


def write_boundary_figures(
    out_dir: str,
    rows: list[dict[str, Any]],
    *,
    se_sp_grid: list[dict[str, Any]] | None = None,
) -> list[str]:
    """Write spec plots 1,2,3,4,5,6,7,8 when matplotlib is available.

    ``se_sp_grid`` optional rows with Se_w, Sp_w, expected_net_benefit for plot 6.
    """
    if not _have_matplotlib() or not rows:
        return []

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_dir = ensure_out_dir(os.path.join(out_dir, "figures"))
    written: list[str] = []

    # 1) Expected total cost vs embarkation prevalence
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for (platform, policy), group in sorted(
        _group(rows, "platform_class", "policy").items()
    ):
        pts = sorted(
            (float(r["pi_inf"]), float(r["expected_total_cost"]))
            for r in group
            if r.get("pi_inf") is not None
        )
        if pts:
            ax.plot(
                [p[0] for p in pts],
                [p[1] for p in pts],
                marker="o",
                label=f"{platform}/{policy}",
            )
    ax.set_xlabel("Embarkation prevalence π_inf")
    ax.set_ylabel("Expected total cost")
    ax.set_title("Expected total cost vs prevalence")
    ax.legend(fontsize=7, ncol=2)
    path = os.path.join(fig_dir, "01_cost_vs_prevalence.png")
    _savefig(path, fig)
    plt.close(fig)
    written.append(path)

    # 2) P(VSP) vs prevalence
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for (platform, policy), group in sorted(
        _group(rows, "platform_class", "policy").items()
    ):
        pts = sorted(
            (float(r["pi_inf"]), float(r["expected_P_trigger"]))
            for r in group
            if r.get("pi_inf") is not None
        )
        if pts:
            ax.plot(
                [p[0] for p in pts],
                [p[1] for p in pts],
                marker="o",
                label=f"{platform}/{policy}",
            )
    ax.set_xlabel("Embarkation prevalence π_inf")
    ax.set_ylabel("P(VSP trigger)")
    ax.set_title("VSP trigger probability vs prevalence")
    ax.legend(fontsize=7, ncol=2)
    path = os.path.join(fig_dir, "02_vsp_vs_prevalence.png")
    _savefig(path, fig)
    plt.close(fig)
    written.append(path)

    # 3) Break-even prevalence by platform (cost(P2)-cost(P0) sign change marker)
    fig, ax = plt.subplots(figsize=(6, 4))
    platforms = sorted({r.get("platform_class") for r in rows if r.get("platform_class")})
    be_vals = []
    labels = []
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
        be = None
        for pi in sorted(set(p0) & set(p2)):
            if p2[pi] <= p0[pi]:
                be = pi
                break
        if be is not None:
            labels.append(str(platform))
            be_vals.append(be)
    if be_vals:
        ax.bar(labels, be_vals, color="#2a6f97")
    ax.set_ylabel("Break-even π_inf")
    ax.set_title("Break-even prevalence by platform (P2 vs P0)")
    path = os.path.join(fig_dir, "03_breakeven_by_platform.png")
    _savefig(path, fig)
    plt.close(fig)
    written.append(path)

    # 4) False positives per outbreak avoided (use false_positives_per_vsp_avoided)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for (platform, policy), group in sorted(
        _group(rows, "platform_class", "policy").items()
    ):
        if policy == "P0":
            continue
        pts = sorted(
            (
                float(r["pi_inf"]),
                float(r["false_positives_per_vsp_avoided"]),
            )
            for r in group
            if r.get("false_positives_per_vsp_avoided") is not None
        )
        if pts:
            ax.plot(
                [p[0] for p in pts],
                [p[1] for p in pts],
                marker="o",
                label=f"{platform}/{policy}",
            )
    ax.set_xlabel("Embarkation prevalence π_inf")
    ax.set_ylabel("FP per VSP avoided")
    ax.set_title("False positives per VSP event avoided")
    ax.legend(fontsize=7, ncol=2)
    path = os.path.join(fig_dir, "04_fp_per_vsp_avoided.png")
    _savefig(path, fig)
    plt.close(fig)
    written.append(path)

    # 5) Adoption threshold proxy: VoI per pax vs policy (at each prevalence)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for (platform, policy), group in sorted(
        _group(rows, "platform_class", "policy").items()
    ):
        if policy == "P0":
            continue
        pts = sorted(
            (
                float(r["pi_inf"]),
                float(r["value_of_information_per_pax"]),
            )
            for r in group
            if r.get("value_of_information_per_pax") is not None
        )
        if pts:
            ax.plot(
                [p[0] for p in pts],
                [p[1] for p in pts],
                marker="o",
                label=f"{platform}/{policy}",
            )
    ax.axhline(0.0, color="gray", lw=0.8)
    ax.set_xlabel("Embarkation prevalence π_inf")
    ax.set_ylabel("VoI per passenger")
    ax.set_title("Value of information per passenger (vs P0)")
    ax.legend(fontsize=7, ncol=2)
    path = os.path.join(fig_dir, "05_voi_vs_prevalence.png")
    _savefig(path, fig)
    plt.close(fig)
    written.append(path)

    # 6) Heatmap Se × Sp → net benefit (optional grid)
    if se_sp_grid:
        fig, ax = plt.subplots(figsize=(5.5, 4.5))
        ses = sorted({float(r["Se_w"]) for r in se_sp_grid})
        sps = sorted({float(r["Sp_w"]) for r in se_sp_grid})
        import numpy as np

        mat = np.full((len(sps), len(ses)), np.nan)
        lookup = {
            (float(r["Se_w"]), float(r["Sp_w"])): float(r["expected_net_benefit"])
            for r in se_sp_grid
        }
        for i, sp in enumerate(sps):
            for j, se in enumerate(ses):
                mat[i, j] = lookup.get((se, sp), np.nan)
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
        written.append(path)

    # 7) Platform comparison at shared prevalence
    fig, ax = plt.subplots(figsize=(7, 4.5))
    # pick median prevalence present
    pis = sorted({float(r["pi_inf"]) for r in rows if r.get("pi_inf") is not None})
    if pis:
        target_pi = pis[len(pis) // 2]
        subset = [
            r
            for r in rows
            if abs(float(r["pi_inf"]) - target_pi) < 1e-12 and r.get("policy") in ("P0", "P2")
        ]
        labels = []
        costs = []
        for r in sorted(subset, key=lambda x: (x.get("platform_class"), x.get("policy"))):
            labels.append(f"{r.get('platform_class')}/{r.get('policy')}")
            costs.append(float(r["expected_total_cost"]))
        if labels:
            ax.bar(labels, costs, color="#1b4965")
            ax.tick_params(axis="x", rotation=45)
        ax.set_title(f"Platform comparison at π_inf={target_pi}")
        ax.set_ylabel("Expected total cost")
    path = os.path.join(fig_dir, "07_platform_comparison.png")
    _savefig(path, fig)
    plt.close(fig)
    written.append(path)

    # 8) Policy frontier: cost vs VSP events avoided (1 - P_trigger relative to P0)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    p0_trigger = {}
    for r in rows:
        if r.get("policy") == "P0":
            p0_trigger[
                (r.get("platform_class"), float(r["pi_inf"]), r.get("pathogen"))
            ] = float(r["expected_P_trigger"])
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
    ax.set_ylabel("Expected total cost")
    ax.set_title("Policy frontier: cost vs VSP avoided")
    # de-duplicate legend
    handles, labels = ax.get_legend_handles_labels()
    uniq = dict(zip(labels, handles))
    ax.legend(uniq.values(), uniq.keys(), fontsize=7, ncol=2)
    path = os.path.join(fig_dir, "08_policy_frontier.png")
    _savefig(path, fig)
    plt.close(fig)
    written.append(path)

    return written
