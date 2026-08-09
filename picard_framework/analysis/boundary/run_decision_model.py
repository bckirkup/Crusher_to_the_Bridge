"""CLI: run pre-boarding wearable decision model campaign."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from picard_framework.analysis._io import ensure_out_dir, read_json, safe_path
from picard_framework.analysis.boundary.campaign import (
    expand_scenarios,
    load_platform_defaults,
    load_scenario_matrix,
    run_campaign,
)
from picard_framework.analysis.boundary.decision_model import run_monte_carlo
from picard_framework.analysis.boundary.figures import write_boundary_figures
from picard_framework.analysis.boundary.posterior_lookup import load_outbreak_surface
from picard_framework.analysis.boundary.report import write_report


def _build_se_sp_grid(
    base_scenario: dict[str, Any],
    surface: Any,
    *,
    n_mc: int,
    seed: int,
) -> list[dict[str, Any]]:
    """Small Se×Sp grid for heatmap (plot 6) around the base scenario."""
    from copy import deepcopy

    ses = [0.45, 0.55, 0.65, 0.75]
    sps = [0.75, 0.85, 0.95]
    # Baseline P0 cost at same prevalence
    p0 = deepcopy(base_scenario)
    p0["policy"] = "P0"
    p0["scenario_id"] = base_scenario["scenario_id"] + "_heatmap_p0"
    base_summary = run_monte_carlo(p0, surface, n_mc=n_mc, seed=seed)
    base_cost = float(base_summary["expected_total_cost"])

    grid: list[dict[str, Any]] = []
    for se in ses:
        for sp in sps:
            sc = deepcopy(base_scenario)
            sc["policy"] = "P2"
            sc["Se_w"] = se
            sc["Sp_w"] = sp
            sc["scenario_id"] = f"{base_scenario['scenario_id']}_se{se}_sp{sp}"
            summary = run_monte_carlo(
                sc, surface, n_mc=n_mc, seed=seed, baseline_summary=base_summary
            )
            grid.append(
                {
                    "Se_w": se,
                    "Sp_w": sp,
                    "expected_net_benefit": base_cost
                    - float(summary["expected_total_cost"]),
                }
            )
    return grid


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python3 -m picard_framework.analysis.boundary.run_decision_model",
        description="Pre-boarding wearable decision model (boundary analysis)",
    )
    p.add_argument(
        "--scenarios",
        default=None,
        help="Scenario matrix JSON (default: package full or smoke matrix)",
    )
    p.add_argument(
        "--stan-fit",
        default=None,
        help="Stan fit directory containing outbreak_surface.{json,csv}",
    )
    p.add_argument(
        "--lookup",
        choices=("auto", "fixture", "stan"),
        default="auto",
        help="Outbreak surface source (default: auto)",
    )
    p.add_argument(
        "--fixture",
        default=None,
        help="Optional fixture outbreak_surface.json path (under CWD)",
    )
    p.add_argument("--n-mc", type=int, default=2000, help="Monte Carlo draws per scenario")
    p.add_argument("--seed", type=int, default=1701, help="RNG seed")
    p.add_argument("--out", default="boundary_analysis", help="Output directory under CWD")
    p.add_argument("--resume", action="store_true", help="Skip completed scenario_ids")
    p.add_argument(
        "--smoke",
        action="store_true",
        help="Tiny matrix, n_mc=50, fixture lookup",
    )
    p.add_argument(
        "--no-figures",
        action="store_true",
        help="Skip matplotlib figure generation",
    )
    p.add_argument(
        "--heatmap",
        action="store_true",
        help="Also compute Se×Sp net-benefit heatmap for first P2 scenario",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    smoke = bool(args.smoke)
    n_mc = 50 if smoke else int(args.n_mc)
    lookup = "fixture" if smoke and args.lookup == "auto" else args.lookup
    if smoke and args.n_mc == 2000:
        n_mc = 50

    matrix = load_scenario_matrix(args.scenarios, smoke=smoke)
    defaults = load_platform_defaults()
    scenarios = expand_scenarios(matrix, defaults)
    if not scenarios:
        print("No scenarios to run", file=sys.stderr)
        return 2

    stan_fit = safe_path(args.stan_fit) if args.stan_fit else None
    fixture = safe_path(args.fixture) if args.fixture else None
    surface = load_outbreak_surface(
        lookup=lookup,
        stan_fit_dir=stan_fit,
        fixture_path=fixture,
    )

    out_dir = ensure_out_dir(args.out)
    rows = run_campaign(
        scenarios,
        surface,
        out_dir=out_dir,
        n_mc=n_mc,
        seed=int(args.seed),
        resume=bool(args.resume),
    )

    se_sp_grid = None
    if args.heatmap or smoke:
        base = next((s for s in scenarios if s["policy"] == "P2"), None)
        if base is not None:
            se_sp_grid = _build_se_sp_grid(
                base, surface, n_mc=min(n_mc, 50), seed=int(args.seed)
            )

    figure_paths: list[str] = []
    if not args.no_figures:
        figure_paths = write_boundary_figures(
            out_dir, rows, se_sp_grid=se_sp_grid
        )

    meta_path = os.path.join(out_dir, "campaign_meta.json")
    meta = read_json(meta_path) if os.path.isfile(meta_path) else {}
    report_path = write_report(out_dir, rows, meta=meta, figure_paths=figure_paths)
    print(f"Wrote {len(rows)} scenarios → {out_dir}")
    print(f"Report: {report_path}")
    if figure_paths:
        print(f"Figures: {len(figure_paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
