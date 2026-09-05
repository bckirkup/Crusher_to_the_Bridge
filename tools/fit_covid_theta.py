#!/usr/bin/env python3
"""Fit Theta on Diamond Princess, then score the held-out hulls.

Two phases, in this order and no other:

    python3 tools/fit_covid_theta.py fit --grid-low 1e4 --grid-high 1e9 --grid-count 6
    python3 tools/fit_covid_theta.py score --theta <the fitted value>

``fit`` runs the training hull once per candidate and writes the whole grid,
losses included. ``score`` takes a Theta that is already fixed and runs the
held-out hull, writing whatever came out. The phases are separate commands on
purpose: there is no path from a held-out score back into candidate selection.

Each hull is a full voyage of a few thousand hosts, so a candidate costs tens
of minutes. The grid is small and declared for that reason.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from picard_framework.covid_fit_targets import load_fit_targets  # noqa: E402
from picard_framework.covid_theta_fit import (  # noqa: E402
    ThetaObjective,
    candidate_grid,
    fit_theta,
    score_held_out,
    simulate_hull,
)

DEFAULT_SEED = 20200205


def _runner(scenario_id: str, theta: float, seed: int):
    started = time.time()
    obs = simulate_hull(scenario_id, theta, seed)
    print(
        f"  {scenario_id} theta={theta:.4g} "
        f"onsets={obs.recorded_onsets} "
        f"specimens={obs.campaign_specimens} "
        f"positives={obs.campaign_positives} "
        f"({(time.time() - started) / 60:.1f} min)",
        flush=True,
    )
    return obs


def _write(payload: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(f"wrote {path}", flush=True)


def _fit(args: argparse.Namespace) -> int:
    grid = candidate_grid(args.grid_low, args.grid_high, args.grid_count)
    objective = ThetaObjective(targets=load_fit_targets(), runner=_runner)
    print(f"grid: {[f'{t:.4g}' for t in grid]}", flush=True)
    result = fit_theta(objective, grid, seed=args.seed)
    _write(result.as_dict(), args.out)
    print(
        f"Theta = {result.theta:.6g} (loss {result.loss:.4f}"
        f"{', BOUNDARY-PINNED' if result.boundary_pinned else ''})",
        flush=True,
    )
    return 0


def _score(args: argparse.Namespace) -> int:
    report = score_held_out(
        args.theta, _runner, targets=load_fit_targets(), seed=args.seed,
    )
    _write(report.as_dict(), args.out)
    for score in report.scores:
        print(
            f"{score.anchor_id}: {score.verdict} "
            f"observed={score.observed} target={score.target}",
            flush=True,
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    sub = parser.add_subparsers(dest="phase", required=True)

    fit_parser = sub.add_parser("fit", help="fit Theta on the training hull")
    fit_parser.add_argument("--grid-low", type=float, required=True)
    fit_parser.add_argument("--grid-high", type=float, required=True)
    fit_parser.add_argument("--grid-count", type=int, default=5)
    fit_parser.add_argument(
        "--out", default="telemetry_buffer/covid_theta_fit.json",
    )
    fit_parser.set_defaults(func=_fit)

    score_parser = sub.add_parser("score", help="score the held-out hulls")
    score_parser.add_argument("--theta", type=float, required=True)
    score_parser.add_argument(
        "--out", default="telemetry_buffer/covid_theta_held_out.json",
    )
    score_parser.set_defaults(func=_score)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
