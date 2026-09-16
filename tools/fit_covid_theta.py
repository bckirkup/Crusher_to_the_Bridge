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

The replicated version of the same two phases runs on AWS Batch
(deploy/aws/submit_covid_first_look.sh) and pools here:

    aws s3 sync s3://<bucket>/campaign/covid_first_look_v1/cells/ <dir>
    python3 tools/fit_covid_theta.py merge --cells <dir>

``merge`` fixes Theta from the training cells first and only then reads the
held-out cells at that Theta, so the order the single-seed commands impose is
the order the merge takes internally.

The boarding-axis screen (Phase 1b, deploy/aws/submit_covid_boarding_screen.sh)
pools with ``screen``; it is a surface over declared assumptions, not a fit,
and writes no Theta.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from picard_framework import covid_boarding_screen, covid_import_sweep  # noqa: E402
from picard_framework.covid_first_look import (  # noqa: E402
    load_design,
    merge_fit,
    merge_held_out,
)
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


def _load_cells(directory: str) -> dict[str, dict]:
    payloads: dict[str, dict] = {}
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(directory, name), encoding="utf-8") as handle:
            payloads[name] = json.load(handle)
    return payloads


def _merge(args: argparse.Namespace) -> int:
    design = load_design(args.design)
    payloads = _load_cells(args.cells)
    targets = load_fit_targets()
    print(f"{len(payloads)} cells read from {args.cells}", flush=True)
    fit = merge_fit(
        design, payloads, targets=targets, allow_partial=args.allow_partial,
    )
    _write(fit.as_dict(), args.fit_out)
    for candidate in fit.candidates:
        print(
            f"  theta={candidate.theta:.4g} mean loss={candidate.mean_loss:.3f} "
            f"P(takeoff)={candidate.takeoff_probability:.2f} "
            f"wins={fit.selection_frequency.get(candidate.theta, 0.0):.2f}",
            flush=True,
        )
    print(
        f"Theta = {fit.theta:.6g} (mean loss {fit.mean_loss:.4f}"
        f"{', BOUNDARY-PINNED' if fit.boundary_pinned else ''}"
        f"{', PARTIAL' if fit.partial else ''})",
        flush=True,
    )
    held_out = merge_held_out(
        design, payloads, fit.theta,
        targets=targets, allow_partial=args.allow_partial,
    )
    _write(held_out, args.held_out_out)
    scored = held_out["scored"]
    if scored is None:
        print("held-out: no cells at the fitted Theta", flush=True)
        return 0
    for score in scored["scores"]:
        print(f"{score['anchor_id']}: {score['verdicts']}", flush=True)
    print(
        f"{scored['placement']['anchor_id']}: above IQR in "
        f"{scored['placement']['frequency_above_iqr']} of defined seeds",
        flush=True,
    )
    return 0


def _screen(args: argparse.Namespace) -> int:
    design = covid_boarding_screen.load_design(args.design)
    payloads = _load_cells(args.cells)
    print(f"{len(payloads)} cells read from {args.cells}", flush=True)
    surface = covid_boarding_screen.merge_screen(
        design, payloads, allow_partial=args.allow_partial,
    )
    _write(surface, args.out)
    witness = surface["sanitary_witness"]
    print(
        f"sanitary visits {witness['declared_mode']}: executed in "
        f"{witness['cells_with_visits']}/{witness['cells']} cells"
        f"{'' if witness['consistent'] else ' -- INCONSISTENT WITH DECLARED MODE'}",
        flush=True,
    )
    for entry in surface["surface"]:
        early = entry["onsets_before_split_day"]
        total = entry["recorded_onsets"]
        first = entry["first_onset_day"]
        first_text = "n/a" if first is None else f"{first['median']:.0f}"
        print(
            f"  theta={entry['theta']:.4g} age={entry['infection_age_days']:g}d "
            f"imports={entry['imports']}: early median={early['median']:.0f} "
            f"total median={total['median']:.0f} "
            f"first onset median={first_text} "
            f"P(takeoff)={entry['takeoff_probability']:.2f}",
            flush=True,
        )
    return 0


def _stage_tolerances(stage: int, takeoff: float | None, ratio: float | None) -> tuple[float, float]:
    """Per-stage defaults that tighten as the pitch closes: stage 2 (0.25, 2x), stage 3 (0.15, 1.5x), ..."""
    step = stage - 2
    if takeoff is None:
        takeoff = 0.25 * (0.6 ** step)
    if ratio is None:
        ratio = 1.0 + 1.0 * (0.5 ** step)
    return takeoff, ratio


def _refine(args: argparse.Namespace) -> int:
    parent = covid_boarding_screen.load_design(args.design)
    surfaces = []
    for path in args.surface:
        with open(path, encoding="utf-8") as handle:
            surfaces.append(json.load(handle))
    if surfaces[0]["design"]["design_id"] != parent.design_id:
        raise SystemExit(
            f"first surface is from {surfaces[0]['design']['design_id']}, "
            f"root design is {parent.design_id}",
        )
    takeoff, ratio = _stage_tolerances(
        args.stage, args.takeoff_tolerance, args.ratio_tolerance,
    )
    rule = covid_import_sweep.RefinementRule(
        takeoff_tolerance=takeoff,
        log_ratio_tolerance=math.log(ratio),
        budget=args.budget,
    )
    design = covid_import_sweep.refined_design(
        parent.as_dict(), surfaces, design_id=args.design_id, rule=rule,
        stage=args.stage,
    )
    print(
        f"stage {args.stage}: takeoff tolerance {takeoff:.3g}, "
        f"ratio tolerance {ratio:.3g}x, {len(surfaces)} surface(s) read",
        flush=True,
    )
    _write(design, args.out)
    for point in design["refinement"]["chosen"]:
        print(
            f"  theta={point['theta']:.4g} imports={point['imports']} "
            f"({point['axis']} midpoint, score {point['score']:.2f}"
            f"{', crosses early' if point['crosses_observed_early'] else ''}"
            f"{', crosses total' if point['crosses_observed_total'] else ''})",
            flush=True,
        )
    print(f"{len(design['points'])} refinement points -> {args.out}", flush=True)
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

    merge_parser = sub.add_parser(
        "merge", help="pool the replicated Batch cells into fit and held-out reports",
    )
    merge_parser.add_argument("--cells", required=True, help="directory of cell JSON files")
    merge_parser.add_argument("--design", default=None)
    merge_parser.add_argument("--allow-partial", action="store_true")
    merge_parser.add_argument(
        "--fit-out", default="telemetry_buffer/observation_model/covid_theta_fit_v2.json",
    )
    merge_parser.add_argument(
        "--held-out-out",
        default="telemetry_buffer/observation_model/covid_theta_held_out_v2.json",
    )
    merge_parser.set_defaults(func=_merge)

    screen_parser = sub.add_parser(
        "screen", help="pool the boarding-axis screen cells into a surface",
    )
    screen_parser.add_argument("--cells", required=True, help="directory of cell JSON files")
    screen_parser.add_argument("--design", default=None)
    screen_parser.add_argument("--allow-partial", action="store_true")
    screen_parser.add_argument(
        "--out",
        default="telemetry_buffer/observation_model/covid_boarding_screen_v1.json",
    )
    screen_parser.set_defaults(func=_screen)

    refine_parser = sub.add_parser(
        "refine",
        help="write the stage-2 point-list design from a stage-1 screen surface",
    )
    refine_parser.add_argument("--design", required=True, help="stage-1 (root) design JSON")
    refine_parser.add_argument(
        "--surface", required=True, nargs="+",
        help="every merged surface run so far, stage 1 first",
    )
    refine_parser.add_argument("--design-id", required=True)
    refine_parser.add_argument(
        "--stage", type=int, default=2,
        help="stage being designed (2, 3, ...); sets the default tolerances",
    )
    refine_parser.add_argument("--budget", type=int, default=12)
    refine_parser.add_argument(
        "--takeoff-tolerance", type=float, default=None,
        help="P(takeoff) change that triggers refinement (default per stage)",
    )
    refine_parser.add_argument(
        "--ratio-tolerance", type=float, default=None,
        help="fold change in a conditional onset median that triggers refinement (default per stage)",
    )
    refine_parser.add_argument("--out", required=True)
    refine_parser.set_defaults(func=_refine)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
