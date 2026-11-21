#!/usr/bin/env python3
"""FLU-CONTAM-SOLVER-01 paired readout: ContamX vs. native influenza summary.

Reads per-seed cell JSON files under ``<root>/<block>/cell_<seed>.json``,
pairs ``contamx`` vs. ``native`` strictly on ``(platform, seed)``, verifies
solver resolution and index-case invariants, and writes:

- ``summary.json``: per-hull paired metrics, dynamics curves, route shifts,
  and wall/CPU/vCPU timing comparisons.
- ``paired_cells.csv``: one row per ``(platform, seed)`` pair for Edison
  downstream analysis.
- ``daily_dynamics.csv``: mean/median daily new and cumulative infections by
  ``(platform, solver, day)``.
- ``report.md``: concise human-readable readout table.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path
from typing import Any

_EXPECTED_ENGINES = {
    "contamx": "ContamXTransportEngine",
    "native": "ContamTransportEngine",
}


def _load_cells(root: Path) -> dict[tuple[str, str], dict[int, dict[str, Any]]]:
    """Load cell JSONs grouped by ``(platform, solver) -> {seed: payload}``."""
    grouped: dict[tuple[str, str], dict[int, dict[str, Any]]] = {}
    for path in sorted(root.glob("*/cell_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        platform = str(data["platform"])
        solver = str(data["solver"]["declared"])
        resolved = str(data["solver"]["resolved"])
        expected = _EXPECTED_ENGINES.get(solver)
        if resolved != expected:
            raise SystemExit(
                f"{path}: solver={solver!r} resolved={resolved!r} != {expected!r}",
            )
        if int(data["counts"]["index_cases"]) < 2:
            raise SystemExit(
                f"{path}: index_cases={data['counts']['index_cases']} < 2",
            )
        seed = int(data["seed"])
        grouped.setdefault((platform, solver), {})[seed] = data
    return grouped


def _mean_med(vals: list[float]) -> dict[str, float]:
    if not vals:
        return {"mean": 0.0, "median": 0.0, "min": 0.0, "max": 0.0}
    return {
        "mean": round(statistics.mean(vals), 4),
        "median": round(statistics.median(vals), 4),
        "min": round(min(vals), 4),
        "max": round(max(vals), 4),
    }


def _pair_row(
    platform: str,
    seed: int,
    nat: dict[str, Any],
    ctx: dict[str, Any],
) -> dict[str, Any]:
    nc, cc = nat["counts"], ctx["counts"]
    nt, ct = nat["timing"], ctx["timing"]
    nd, cd = nat["dynamics"], ctx["dynamics"]
    nr, cr = nat["routes"], ctx["routes"]
    total = int(nat["complement"]["total"])
    nat_air = float(
        nr["particles_by_route_sum"].get("hvac_airborne", 0.0)
        + nr["particles_by_route_sum"].get("airborne", 0.0)
    )
    ctx_air = float(
        cr["particles_by_route_sum"].get("hvac_airborne", 0.0)
        + cr["particles_by_route_sum"].get("airborne", 0.0)
    )
    return {
        "platform": platform,
        "seed": seed,
        "complement": total,
        "native_ever_infected": nc["ever_infected"],
        "contamx_ever_infected": cc["ever_infected"],
        "diff_ever_infected": cc["ever_infected"] - nc["ever_infected"],
        "native_onboard": nc["onboard_acquired"],
        "contamx_onboard": cc["onboard_acquired"],
        "diff_onboard": cc["onboard_acquired"] - nc["onboard_acquired"],
        "native_attack_pct": round(100.0 * nc["onboard_acquired"] / total, 4),
        "contamx_attack_pct": round(100.0 * cc["onboard_acquired"] / total, 4),
        "native_ever_ill": nc["ever_ill"],
        "contamx_ever_ill": cc["ever_ill"],
        "native_ever_reported": nc["ever_reported"],
        "contamx_ever_reported": cc["ever_reported"],
        "native_peak_day": nd["peak_day"],
        "contamx_peak_day": cd["peak_day"],
        "native_peak_daily": nd["peak_daily_new"],
        "contamx_peak_daily": cd["peak_daily_new"],
        "native_airborne_dom": nr["airborne_dominant_count"],
        "contamx_airborne_dom": cr["airborne_dominant_count"],
        "native_airborne_particles": round(nat_air, 4),
        "contamx_airborne_particles": round(ctx_air, 4),
        "native_init_wall_s": nt["init_wall_s"],
        "contamx_init_wall_s": ct["init_wall_s"],
        "native_run_wall_s": nt["run_wall_s"],
        "contamx_run_wall_s": ct["run_wall_s"],
        "native_total_wall_s": nt["total_wall_s"],
        "contamx_total_wall_s": ct["total_wall_s"],
        "native_total_cpu_s": nt["total_cpu_s"],
        "contamx_total_cpu_s": ct["total_cpu_s"],
        "contamx_child_cpu_s": ct["total_cpu_children_s"],
    }


def _daily_rows(
    platform: str,
    solver: str,
    cells: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not cells:
        return []
    n_days = max(int(c["dynamics"]["n_days"]) for c in cells)
    rows: list[dict[str, Any]] = []
    for day in range(n_days):
        new_vals = [
            int(c["dynamics"]["daily_new_infections"][day])
            for c in cells
            if day < len(c["dynamics"]["daily_new_infections"])
        ]
        cum_vals = [
            int(c["dynamics"]["daily_cumulative_infections"][day])
            for c in cells
            if day < len(c["dynamics"]["daily_cumulative_infections"])
        ]
        rows.append(
            {
                "platform": platform,
                "solver": solver,
                "day": day,
                "n_seeds": len(new_vals),
                "mean_new": round(statistics.mean(new_vals), 3),
                "median_new": round(statistics.median(new_vals), 3),
                "mean_cum": round(statistics.mean(cum_vals), 3),
                "median_cum": round(statistics.median(cum_vals), 3),
            }
        )
    return rows


def _summarize_platform(
    platform: str,
    pairs: list[dict[str, Any]],
) -> dict[str, Any]:
    nat_on = [p["native_onboard"] for p in pairs]
    ctx_on = [p["contamx_onboard"] for p in pairs]
    diff_on = [p["diff_onboard"] for p in pairs]
    nat_wall = [p["native_total_wall_s"] for p in pairs]
    ctx_wall = [p["contamx_total_wall_s"] for p in pairs]
    nat_cpu = [p["native_total_cpu_s"] for p in pairs]
    ctx_cpu = [p["contamx_total_cpu_s"] for p in pairs]
    ctx_child = [p["contamx_child_cpu_s"] for p in pairs]
    wall_ratio = (
        round(statistics.mean(ctx_wall) / statistics.mean(nat_wall), 3)
        if statistics.mean(nat_wall) > 0
        else 0.0
    )
    cpu_ratio = (
        round(statistics.mean(ctx_cpu) / statistics.mean(nat_cpu), 3)
        if statistics.mean(nat_cpu) > 0
        else 0.0
    )
    return {
        "platform": platform,
        "n_pairs": len(pairs),
        "complement": pairs[0]["complement"],
        "native_onboard": _mean_med(nat_on),
        "contamx_onboard": _mean_med(ctx_on),
        "diff_onboard_contamx_minus_native": _mean_med(diff_on),
        "native_airborne_dom_mean": round(
            statistics.mean(p["native_airborne_dom"] for p in pairs), 3,
        ),
        "contamx_airborne_dom_mean": round(
            statistics.mean(p["contamx_airborne_dom"] for p in pairs), 3,
        ),
        "native_total_wall_s": _mean_med(nat_wall),
        "contamx_total_wall_s": _mean_med(ctx_wall),
        "wall_ratio_contamx_over_native": wall_ratio,
        "native_total_cpu_s": _mean_med(nat_cpu),
        "contamx_total_cpu_s": _mean_med(ctx_cpu),
        "contamx_child_cpu_s": _mean_med(ctx_child),
        "cpu_ratio_contamx_over_native": cpu_ratio,
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _format_markdown(summaries: list[dict[str, Any]]) -> str:
    lines = [
        "# FLU-CONTAM-SOLVER-01 Readout",
        "",
        "| Platform | Pairs | Complement | Native Onboard (mean/med) | "
        "ContamX Onboard (mean/med) | Diff (Ctx-Nat) | Native Wall (s) | "
        "ContamX Wall (s) | Wall Ratio | CPU Ratio | ContamX Child CPU (s) |",
        "| --- | ---: | ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for s in summaries:
        lines.append(
            f"| {s['platform']} | {s['n_pairs']} | {s['complement']} | "
            f"{s['native_onboard']['mean']:.1f} / {s['native_onboard']['median']:.1f} | "
            f"{s['contamx_onboard']['mean']:.1f} / {s['contamx_onboard']['median']:.1f} | "
            f"{s['diff_onboard_contamx_minus_native']['mean']:+.1f} / "
            f"{s['diff_onboard_contamx_minus_native']['median']:+.1f} | "
            f"{s['native_total_wall_s']['mean']:.2f} | "
            f"{s['contamx_total_wall_s']['mean']:.2f} | "
            f"{s['wall_ratio_contamx_over_native']:.2f}x | "
            f"{s['cpu_ratio_contamx_over_native']:.2f}x | "
            f"{s['contamx_child_cpu_s']['mean']:.2f} |",
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="directory of <block>/cell_*.json")
    parser.add_argument("--out", required=True, help="output directory for readout artifacts")
    args = parser.parse_args(argv)

    root = Path(args.root)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    grouped = _load_cells(root)
    platforms = sorted({plat for plat, _ in grouped})
    all_pairs: list[dict[str, Any]] = []
    all_daily: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []

    for plat in platforms:
        nat_map = grouped.get((plat, "native"), {})
        ctx_map = grouped.get((plat, "contamx"), {})
        common_seeds = sorted(set(nat_map) & set(ctx_map))
        if not common_seeds:
            continue
        plat_pairs = [
            _pair_row(plat, seed, nat_map[seed], ctx_map[seed])
            for seed in common_seeds
        ]
        all_pairs.extend(plat_pairs)
        summaries.append(_summarize_platform(plat, plat_pairs))
        all_daily.extend(_daily_rows(plat, "native", [nat_map[s] for s in common_seeds]))
        all_daily.extend(_daily_rows(plat, "contamx", [ctx_map[s] for s in common_seeds]))

    (out / "summary.json").write_text(
        json.dumps({"platforms": summaries}, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_csv(out / "paired_cells.csv", all_pairs)
    _write_csv(out / "daily_dynamics.csv", all_daily)
    md = _format_markdown(summaries)
    (out / "report.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
