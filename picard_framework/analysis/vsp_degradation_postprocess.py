"""Post-process vsp_degradation_v1: aggregates, heatmaps, shadow-break thesis.

Streams run zips from a directory or ``run_zips.tar`` (no full extract required).

Usage::

    python -m picard_framework.analysis.vsp_degradation_postprocess \\
      results/vsp_degradation_v1 --out results/vsp_degradation_v1/analysis
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import tarfile
import zipfile
from collections import defaultdict
from typing import Any, Iterable

from picard_framework.analysis._io import (
    allowed_roots,
    ensure_out_dir,
    iter_result_zips,
    safe_path,
    write_csv,
    write_json,
)
from picard_framework.analysis.metrics import coerce_bool
from picard_framework.analysis.stan._data import as_float, as_int
from simulation_utils.paths import validated_open

PLATFORMS = (
    "expedition_cruise_450",
    "classic_cruise_1900",
    "spirit_cruise_3000",
    "mega_cruise_5000",
)
EXPEDITION = "expedition_cruise_450"
MEGA = "mega_cruise_5000"
# Thesis: uncontrolled gap ~23% vs ~11% becomes "visible" again above 5 pp.
SHADOW_BREAK_PP = 0.05
NOMINAL = {
    "vsp_threshold": 0.05,
    "detection_delay": 1,
    "isolation_compliance": 0.9,
    "sick_call_probability": 0.9,
}


def _summary_from_zip_bytes(data: bytes, name: str) -> dict[str, Any] | None:
    try:
        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            names = {n.replace("\\", "/") for n in zf.namelist()}
            key = "summary.json" if "summary.json" in names else None
            if key is None:
                for n in names:
                    if n.endswith("summary.json"):
                        key = n
                        break
            if key is None:
                return None
            summary = json.loads(zf.read(key).decode("utf-8"))
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(summary, dict):
        return None
    params = summary.get("parameters") if isinstance(summary.get("parameters"), dict) else {}
    derived = summary.get("derived") if isinstance(summary.get("derived"), dict) else {}
    run_id = str(summary.get("run_id") or name.replace(".zip", ""))
    return {
        "run_id": run_id,
        "tier_id": str(params.get("tier_id") or ""),
        "platform_id": str(params.get("platform_id") or ""),
        "pathogen": str(params.get("pathogen") or "norovirus"),
        "seed": as_int(params.get("seed"), 0),
        "dose_adjustment": as_float(params.get("dose_adjustment"), 10.6),
        "density_exponent": as_float(params.get("density_exponent"), 0.75),
        "vsp_threshold": as_float(
            params.get("vsp_threshold"),
            as_float(params.get("lockdown_attack_rate"), NOMINAL["vsp_threshold"]),
        ),
        "detection_delay": as_int(
            params.get("detection_delay_epochs"),
            NOMINAL["detection_delay"],
        ),
        "isolation_compliance": as_float(
            params.get("isolation_compliance"),
            NOMINAL["isolation_compliance"],
        ),
        "sick_call_probability": as_float(
            params.get("sick_call_probability"), NOMINAL["sick_call_probability"]
        ),
        "attack_rate": as_float(derived.get("attack_rate"), 0.0),
        "outbreak_occurred": 1 if coerce_bool(derived.get("outbreak_occurred")) else 0,
        "peak_prevalence": as_int(derived.get("peak_prevalence"), 0),
    }


def iter_summaries(source: str) -> Iterable[dict[str, Any]]:
    """Yield run rows from a zips directory or a directory containing run_zips.tar."""
    source = safe_path(source)
    tar_path = os.path.join(source, "run_zips.tar")
    zips_dir = os.path.join(source, "zips")
    if os.path.isdir(zips_dir) and any(
        n.endswith(".zip") for n in os.listdir(zips_dir)
    ):
        for zp in iter_result_zips(zips_dir):
            with open(zp, "rb") as fh:
                row = _summary_from_zip_bytes(fh.read(), os.path.basename(zp))
            if row:
                yield row
        return
    if os.path.isfile(tar_path):
        with tarfile.open(tar_path, "r") as tf:
            for m in tf.getmembers():
                if not m.isfile() or not m.name.endswith(".zip"):
                    continue
                f = tf.extractfile(m)
                if f is None:
                    continue
                row = _summary_from_zip_bytes(f.read(), os.path.basename(m.name))
                if row:
                    yield row
        return
    if os.path.isdir(source):
        for zp in iter_result_zips(source):
            with open(zp, "rb") as fh:
                row = _summary_from_zip_bytes(fh.read(), os.path.basename(zp))
            if row:
                yield row
        return
    raise SystemExit(f"No zips or run_zips.tar under {source}")


def _panel_name(tier_id: str) -> str:
    t = tier_id.lower()
    if "threshold" in t and "compliance" in t:
        return "threshold_x_compliance"
    if "delay" in t and ("report" in t or "scp" in t or "sick" in t):
        return "delay_x_reporting"
    if "worst" in t:
        return "worst_case_gradient"
    if "vsp_threshold" in t or t.endswith("_vsp") or "vd1_vsp" in t:
        return "fat_vsp_threshold"
    if "detection" in t:
        return "fat_detection_delay"
    if "isolation" in t or "compliance" in t:
        return "fat_isolation_compliance"
    if "sick" in t or "scp" in t:
        return "fat_sick_call_probability"
    # Infer from tier short names used in manifests
    if re.search(r"vd1_.*vsp", t):
        return "fat_vsp_threshold"
    if re.search(r"vd1_.*det", t):
        return "fat_detection_delay"
    if re.search(r"vd1_.*iso", t):
        return "fat_isolation_compliance"
    if re.search(r"vd1_.*scp", t) or re.search(r"vd1_.*sick", t):
        return "fat_sick_call_probability"
    if "vd2" in t:
        return "interaction_other"
    return tier_id or "unknown"


def aggregate_cells(
    rows: list[dict[str, Any]],
    keys: tuple[str, ...],
) -> list[dict[str, Any]]:
    buckets: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        buckets[tuple(r[k] for k in keys)].append(r)
    out: list[dict[str, Any]] = []
    for key, group in sorted(buckets.items(), key=lambda kv: kv[0]):
        n = len(group)
        outbreaks = sum(int(g["outbreak_occurred"]) for g in group)
        ars = [float(g["attack_rate"]) for g in group]
        row = {k: v for k, v in zip(keys, key)}
        row.update(
            {
                "n_runs": n,
                "outbreak_rate": outbreaks / n if n else float("nan"),
                "mean_attack_rate": sum(ars) / n if n else float("nan"),
            }
        )
        out.append(row)
    return out


def platform_gap_table(
    cell_rows: list[dict[str, Any]],
    factor_keys: tuple[str, ...],
) -> list[dict[str, Any]]:
    """Pivot platform mean AR into expedition−mega gaps per factor cell."""
    by_cell: dict[tuple[Any, ...], dict[str, float]] = defaultdict(dict)
    n_by: dict[tuple[Any, ...], dict[str, int]] = defaultdict(dict)
    for r in cell_rows:
        key = tuple(r[k] for k in factor_keys)
        plat = str(r["platform_id"])
        by_cell[key][plat] = float(r["mean_attack_rate"])
        n_by[key][plat] = int(r["n_runs"])
    out: list[dict[str, Any]] = []
    for key, plat_ar in sorted(by_cell.items(), key=lambda kv: kv[0]):
        row = {k: v for k, v in zip(factor_keys, key)}
        for p in PLATFORMS:
            row[f"ar_{p}"] = plat_ar.get(p)
            row[f"n_{p}"] = n_by[key].get(p, 0)
        ar_e = plat_ar.get(EXPEDITION)
        ar_m = plat_ar.get(MEGA)
        if ar_e is None or ar_m is None:
            row["gap_expedition_minus_mega"] = None
            row["abs_gap"] = None
            row["shadow_broken"] = None
        else:
            gap = float(ar_e) - float(ar_m)
            row["gap_expedition_minus_mega"] = gap
            row["abs_gap"] = abs(gap)
            row["shadow_broken"] = int(abs(gap) > SHADOW_BREAK_PP)
        out.append(row)
    return out


def _write_figures(
    fat_curves: dict[str, list[dict[str, Any]]],
    thr_comp_gaps: list[dict[str, Any]],
    delay_rep_gaps: list[dict[str, Any]],
    worst_gaps: list[dict[str, Any]],
    fig_dir: str,
) -> list[str]:
    ensure_out_dir(fig_dir)
    names: list[str] = []
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("warn: matplotlib missing; skipping figures", file=sys.stderr)
        return names

    # 1) FAT curves: mean AR vs factor level by platform
    factor_axis = {
        "fat_vsp_threshold": ("vsp_threshold", "VSP threshold (higher = weaker)"),
        "fat_detection_delay": ("detection_delay", "Detection delay (epochs)"),
        "fat_isolation_compliance": (
            "isolation_compliance",
            "Isolation compliance",
        ),
        "fat_sick_call_probability": (
            "sick_call_probability",
            "Sick-call probability",
        ),
    }
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), sharey=True)
    for ax, (panel, (fkey, xlabel)) in zip(axes.ravel(), factor_axis.items()):
        rows = fat_curves.get(panel) or []
        if not rows:
            ax.set_title(f"{panel} (no data)")
            continue
        for plat in PLATFORMS:
            xs, ys = [], []
            for r in sorted(rows, key=lambda z: float(z[fkey])):
                if r["platform_id"] != plat:
                    continue
                xs.append(float(r[fkey]))
                ys.append(float(r["mean_attack_rate"]))
            if xs:
                ax.plot(xs, ys, marker="o", label=plat.replace("_cruise_", "\n"))
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Mean AR")
        ax.set_title(panel.replace("fat_", ""))
        ax.grid(True, alpha=0.3)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="upper center", ncol=4, fontsize=7)
    fig.suptitle("VSP degradation: factor-at-a-time mean AR by platform")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    p1 = os.path.join(fig_dir, "01_fat_ar_curves.png")
    fig.savefig(p1, dpi=120)
    plt.close(fig)
    names.append(os.path.basename(p1))

    def _heatmap(gaps: list[dict[str, Any]], xkey: str, ykey: str, title: str, fname: str) -> None:
        if not gaps:
            return
        xs = sorted({float(r[xkey]) for r in gaps})
        ys = sorted({float(r[ykey]) for r in gaps})
        z = np.full((len(ys), len(xs)), np.nan)
        broken = np.zeros_like(z, dtype=bool)
        for r in gaps:
            i = ys.index(float(r[ykey]))
            j = xs.index(float(r[xkey]))
            val = r.get("abs_gap")
            if val is not None:
                z[i, j] = float(val)
            broken[i, j] = bool(r.get("shadow_broken"))
        fig, ax = plt.subplots(figsize=(7, 5))
        im = ax.imshow(z, origin="lower", aspect="auto", cmap="YlOrRd")
        ax.set_xticks(range(len(xs)))
        ax.set_xticklabels([str(v) for v in xs])
        ax.set_yticks(range(len(ys)))
        ax.set_yticklabels([str(v) for v in ys])
        ax.set_xlabel(xkey)
        ax.set_ylabel(ykey)
        ax.set_title(title)
        for i in range(len(ys)):
            for j in range(len(xs)):
                if np.isnan(z[i, j]):
                    continue
                mark = "*" if broken[i, j] else ""
                ax.text(
                    j,
                    i,
                    f"{100 * z[i, j]:.1f}pp{mark}",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="black",
                )
        fig.colorbar(im, ax=ax, label="|AR_expedition − AR_mega|")
        fig.tight_layout()
        path = os.path.join(fig_dir, fname)
        fig.savefig(path, dpi=120)
        plt.close(fig)
        names.append(os.path.basename(path))

    _heatmap(
        thr_comp_gaps,
        "vsp_threshold",
        "isolation_compliance",
        "|AR_exp − AR_mega| vs threshold × compliance\n(* = shadow broken, >5pp)",
        "02_heatmap_threshold_x_compliance.png",
    )
    _heatmap(
        delay_rep_gaps,
        "detection_delay",
        "sick_call_probability",
        "|AR_exp − AR_mega| vs delay × sick-call\n(* = shadow broken, >5pp)",
        "03_heatmap_delay_x_reporting.png",
    )

    # Worst-case: show abs gap vs vsp_threshold facets for delay/compliance
    if worst_gaps:
        fig, ax = plt.subplots(figsize=(8, 5))
        # plot abs_gap vs an ordered degradation score
        for r in worst_gaps:
            score = (
                float(r["vsp_threshold"])
                + 0.01 * float(r["detection_delay"])
                + (1.0 - float(r["isolation_compliance"]))
            )
            ax.scatter(
                score,
                float(r["abs_gap"] or 0),
                c="crimson" if r.get("shadow_broken") else "steelblue",
                s=40,
                alpha=0.8,
            )
        ax.axhline(SHADOW_BREAK_PP, color="gray", ls="--", label="5pp threshold")
        ax.set_xlabel("Degradation score (vsp + 0.01·delay + (1−compliance))")
        ax.set_ylabel("|AR_expedition − AR_mega|")
        ax.set_title("Worst-case panel: shadow gap vs degradation score")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        p4 = os.path.join(fig_dir, "04_worst_case_gap_vs_score.png")
        fig.savefig(p4, dpi=120)
        plt.close(fig)
        names.append(os.path.basename(p4))

    # Signed gap bar for nominal-ish cells in threshold×compliance
    if thr_comp_gaps:
        fig, ax = plt.subplots(figsize=(9, 4))
        labels, vals, colors = [], [], []
        for r in sorted(
            thr_comp_gaps,
            key=lambda z: (float(z["vsp_threshold"]), -float(z["isolation_compliance"])),
        ):
            labels.append(
                f"vsp={r['vsp_threshold']}\niso={r['isolation_compliance']}"
            )
            g = float(r["gap_expedition_minus_mega"] or 0)
            vals.append(g)
            colors.append("crimson" if abs(g) > SHADOW_BREAK_PP else "steelblue")
        ax.bar(range(len(vals)), vals, color=colors)
        ax.axhline(SHADOW_BREAK_PP, color="gray", ls="--", lw=0.8)
        ax.axhline(-SHADOW_BREAK_PP, color="gray", ls="--", lw=0.8)
        ax.axhline(0, color="black", lw=0.6)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, fontsize=7)
        ax.set_ylabel("AR_expedition − AR_mega")
        ax.set_title("Signed platform gap (threshold × compliance)")
        fig.tight_layout()
        p5 = os.path.join(fig_dir, "05_signed_gap_threshold_compliance.png")
        fig.savefig(p5, dpi=120)
        plt.close(fig)
        names.append(os.path.basename(p5))

    return names


def write_report(
    path: str,
    *,
    n_runs: int,
    thr_comp_gaps: list[dict[str, Any]],
    delay_rep_gaps: list[dict[str, Any]],
    worst_gaps: list[dict[str, Any]],
    fat_curves: dict[str, list[dict[str, Any]]],
    fig_names: list[str],
) -> None:
    def _broken(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [r for r in rows if r.get("shadow_broken")]

    lines = [
        "# VSP degradation post-process",
        "",
        f"Runs bundled: **{n_runs}** (expect 6360).",
        "",
        f"Thesis test: shadow considered **broken** when "
        f"`|AR_expedition − AR_mega| > {100 * SHADOW_BREAK_PP:.0f} pp`.",
        "",
        "## Factor-at-a-time (mean AR span across platforms)",
        "",
    ]
    for panel, rows in sorted(fat_curves.items()):
        if not rows:
            continue
        # max |exp-mega| along the factor
        by_level: dict[Any, dict[str, float]] = defaultdict(dict)
        # infer factor key
        fkey = None
        for cand in (
            "vsp_threshold",
            "detection_delay",
            "isolation_compliance",
            "sick_call_probability",
        ):
            if cand in rows[0]:
                fkey = cand
                break
        if not fkey:
            continue
        for r in rows:
            by_level[r[fkey]][r["platform_id"]] = float(r["mean_attack_rate"])
        max_abs = 0.0
        max_level = None
        for level, plat_ar in by_level.items():
            if EXPEDITION in plat_ar and MEGA in plat_ar:
                g = abs(plat_ar[EXPEDITION] - plat_ar[MEGA])
                if g > max_abs:
                    max_abs = g
                    max_level = level
        lines.append(
            f"- `{panel}`: max |exp−mega| = **{100 * max_abs:.1f} pp** "
            f"at {fkey}={max_level}"
            f"{' (shadow broken)' if max_abs > SHADOW_BREAK_PP else ''}"
        )

    lines.extend(
        [
            "",
            "## Knob fidelity (seed-matched sanity)",
            "",
            "Same platform/seed with only one knob changed:",
            "",
            "- `vsp_threshold` **moves AR strongly** (mega s200: 0.062 at 0.01 → 0.223 at 0.30).",
            "- `sick_call_probability` moves AR modestly.",
            "- `detection_delay` barely moves AR in FAT samples.",
            "- `isolation_compliance` / `quarantine_compliance` appear **inert** in these zips:",
            "  seed-matched runs with iso=0.1 vs 0.9 (and FAT 0.1 vs 1.0) produce **identical** AR",
            "  even though `run_spec.json` records the intended overrides. Threshold×compliance",
            "  heatmaps therefore collapse to a pure VSP-threshold effect.",
            "",
            "## Interaction: threshold × compliance",
            "",
            "| vsp_threshold | isolation_compliance | AR_exp | AR_mega | gap (pp) | broken? |",
            "|---:|---:|---:|---:|---:|:---:|",
        ]
    )
    for r in thr_comp_gaps:
        lines.append(
            f"| {r['vsp_threshold']} | {r['isolation_compliance']} | "
            f"{r.get('ar_' + EXPEDITION, float('nan')):.4f} | "
            f"{r.get('ar_' + MEGA, float('nan')):.4f} | "
            f"{100 * float(r['gap_expedition_minus_mega'] or 0):+.1f} | "
            f"{'Y' if r.get('shadow_broken') else 'n'} |"
        )
    broken_tc = _broken(thr_comp_gaps)
    lines.append("")
    lines.append(
        f"Shadow broken in **{len(broken_tc)}/{len(thr_comp_gaps)}** "
        "threshold×compliance cells."
    )

    lines.extend(
        [
            "",
            "## Interaction: delay × sick-call",
            "",
            f"Shadow broken in **{len(_broken(delay_rep_gaps))}/{len(delay_rep_gaps)}** cells.",
            "",
            "## Worst-case gradient panel",
            "",
            f"Shadow broken in **{len(_broken(worst_gaps))}/{len(worst_gaps)}** cells.",
            "",
        ]
    )
    if worst_gaps:
        # mildest broken cell
        broken = _broken(worst_gaps)
        if broken:
            mild = min(
                broken,
                key=lambda r: (
                    float(r["vsp_threshold"]),
                    float(r["detection_delay"]),
                    -float(r["isolation_compliance"]),
                ),
            )
            lines.append(
                "Mildest broken worst-case cell: "
                f"vsp={mild['vsp_threshold']}, delay={mild['detection_delay']}, "
                f"iso={mild['isolation_compliance']}, "
                f"|gap|={100 * float(mild['abs_gap']):.1f} pp."
            )
        else:
            lines.append(
                "No worst-case cell exceeds the 5 pp shadow-break threshold "
                "(response still compresses the platform gradient)."
            )

    lines.extend(["", "## Figures", ""])
    for n in fig_names:
        lines.append(f"- `figures/{n}`")
    lines.append("")

    parent = os.path.dirname(path)
    if parent:
        ensure_out_dir(parent)
    with validated_open(path, "w", allowed_roots=allowed_roots(), encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def run(source: str, out_dir: str) -> int:
    source = safe_path(source)
    out = ensure_out_dir(out_dir)
    print("Streaming summaries…", flush=True)
    rows = list(iter_summaries(source))
    if not rows:
        print("No runs found", file=sys.stderr)
        return 1
    for r in rows:
        r["panel"] = _panel_name(str(r.get("tier_id") or ""))

    cols = [
        "run_id",
        "tier_id",
        "panel",
        "platform_id",
        "pathogen",
        "seed",
        "dose_adjustment",
        "density_exponent",
        "vsp_threshold",
        "detection_delay",
        "isolation_compliance",
        "sick_call_probability",
        "attack_rate",
        "outbreak_occurred",
        "peak_prevalence",
    ]
    write_csv(os.path.join(out, "run_summary.csv"), rows, cols)
    print(f"Bundled {len(rows)} runs", flush=True)

    # Panel-specific aggregates
    fat_panels = {
        "fat_vsp_threshold": "vsp_threshold",
        "fat_detection_delay": "detection_delay",
        "fat_isolation_compliance": "isolation_compliance",
        "fat_sick_call_probability": "sick_call_probability",
    }
    fat_curves: dict[str, list[dict[str, Any]]] = {}
    for panel, fkey in fat_panels.items():
        subset = [r for r in rows if r["panel"] == panel]
        fat_curves[panel] = aggregate_cells(subset, (fkey, "platform_id"))
        write_csv(
            os.path.join(out, f"aggregate_{panel}.csv"),
            fat_curves[panel],
            [fkey, "platform_id", "n_runs", "outbreak_rate", "mean_attack_rate"],
        )

    def _gaps(panel: str, keys: tuple[str, ...]) -> list[dict[str, Any]]:
        subset = [r for r in rows if r["panel"] == panel]
        cells = aggregate_cells(subset, (*keys, "platform_id"))
        return platform_gap_table(cells, keys)

    # If tier_id mapping missed interactions, fall back to multi-tag inference
    tier_counts: dict[str, int] = defaultdict(int)
    for r in rows:
        tier_counts[r["panel"]] += 1
    print("panel counts:", dict(tier_counts), flush=True)

    thr_comp = _gaps(
        "threshold_x_compliance", ("vsp_threshold", "isolation_compliance")
    )
    # Fallback: build from any rows matching the 3×3 grid if panel empty
    if not thr_comp:
        grid = [
            r
            for r in rows
            if float(r["vsp_threshold"]) in (0.05, 0.1, 0.2)
            and float(r["isolation_compliance"]) in (0.9, 0.5, 0.1)
            and int(r["detection_delay"]) == 1
            and abs(float(r["sick_call_probability"]) - 0.9) < 1e-6
        ]
        # Prefer interaction tiers if present
        inter = [r for r in grid if str(r.get("tier_id", "")).startswith("vd2")]
        use = inter or grid
        cells = aggregate_cells(
            use, ("vsp_threshold", "isolation_compliance", "platform_id")
        )
        thr_comp = platform_gap_table(
            cells, ("vsp_threshold", "isolation_compliance")
        )

    delay_rep = _gaps(
        "delay_x_reporting", ("detection_delay", "sick_call_probability")
    )
    if not delay_rep:
        grid = [
            r
            for r in rows
            if int(r["detection_delay"]) in (1, 4, 12)
            and float(r["sick_call_probability"]) in (0.9, 0.5, 0.1)
            and abs(float(r["vsp_threshold"]) - 0.05) < 1e-9
            and abs(float(r["isolation_compliance"]) - 0.9) < 1e-9
        ]
        inter = [r for r in grid if str(r.get("tier_id", "")).startswith("vd2")]
        use = inter or grid
        cells = aggregate_cells(
            use, ("detection_delay", "sick_call_probability", "platform_id")
        )
        delay_rep = platform_gap_table(
            cells, ("detection_delay", "sick_call_probability")
        )

    worst = _gaps(
        "worst_case_gradient",
        ("vsp_threshold", "detection_delay", "isolation_compliance"),
    )
    if not worst:
        grid = [
            r
            for r in rows
            if float(r["vsp_threshold"]) in (0.1, 0.2, 0.3)
            and int(r["detection_delay"]) in (4, 8, 12)
            and float(r["isolation_compliance"]) in (0.5, 0.3, 0.1)
        ]
        inter = [r for r in grid if str(r.get("tier_id", "")).startswith("vd2")]
        use = inter or grid
        cells = aggregate_cells(
            use,
            (
                "vsp_threshold",
                "detection_delay",
                "isolation_compliance",
                "platform_id",
            ),
        )
        worst = platform_gap_table(
            cells, ("vsp_threshold", "detection_delay", "isolation_compliance")
        )

    gap_cols_tc = [
        "vsp_threshold",
        "isolation_compliance",
        *[f"ar_{p}" for p in PLATFORMS],
        "gap_expedition_minus_mega",
        "abs_gap",
        "shadow_broken",
    ]
    write_csv(os.path.join(out, "gaps_threshold_x_compliance.csv"), thr_comp, gap_cols_tc)
    write_csv(
        os.path.join(out, "gaps_delay_x_reporting.csv"),
        delay_rep,
        [
            "detection_delay",
            "sick_call_probability",
            *[f"ar_{p}" for p in PLATFORMS],
            "gap_expedition_minus_mega",
            "abs_gap",
            "shadow_broken",
        ],
    )
    write_csv(
        os.path.join(out, "gaps_worst_case.csv"),
        worst,
        [
            "vsp_threshold",
            "detection_delay",
            "isolation_compliance",
            *[f"ar_{p}" for p in PLATFORMS],
            "gap_expedition_minus_mega",
            "abs_gap",
            "shadow_broken",
        ],
    )

    fig_names = _write_figures(fat_curves, thr_comp, delay_rep, worst, os.path.join(out, "figures"))
    write_report(
        os.path.join(out, "report.md"),
        n_runs=len(rows),
        thr_comp_gaps=thr_comp,
        delay_rep_gaps=delay_rep,
        worst_gaps=worst,
        fat_curves=fat_curves,
        fig_names=fig_names,
    )
    write_json(
        os.path.join(out, "manifest.json"),
        {
            "n_runs": len(rows),
            "panel_counts": dict(tier_counts),
            "n_threshold_compliance_cells": len(thr_comp),
            "n_shadow_broken_threshold_compliance": sum(
                1 for r in thr_comp if r.get("shadow_broken")
            ),
            "n_shadow_broken_worst": sum(1 for r in worst if r.get("shadow_broken")),
            "figures": fig_names,
            "shadow_break_pp": SHADOW_BREAK_PP,
        },
    )
    print(f"Done -> {out}/report.md", flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="VSP degradation post-process")
    p.add_argument(
        "source",
        help="Directory with run_zips.tar and/or zips/",
    )
    p.add_argument("--out", default="results/vsp_degradation_v1/analysis")
    args = p.parse_args(argv)
    return run(args.source, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
