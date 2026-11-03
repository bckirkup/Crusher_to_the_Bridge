#!/usr/bin/env python3
"""Item #30 diagnostic: per-shedder airborne deposit under the sourced
exhaled-rate level, versus the measured bracket and the Theta regime.

Runs the two COVID hulls (Diamond Princess training, Greg Mortimer
held-out) on the shipped ``sars_cov2_resp`` profile with NO Theta
overrides - the arm's natural state after #30's level fix - and, each
epoch, reproduces the deposit line ``_deposit_agent_emission`` writes:
``sv * airborne_emission_fraction``, where ``sv`` is the agent's
per-epoch emission. Recorded per run: shedder-epoch counts, the deposit
distribution at the shipped fraction 5e-5, and the reference deposit at
the tranche-27-licensed fine share 0.85 (measurement only - the shipped
value is unchanged by this tool).

Comparison witnesses: the declared measured bracket
``EMISSION_BRACKET_COPIES_PER_EPOCH = [4.2e3, 5.8e7]`` per epoch, and the
Theta-fit regime's analytic deposit (the fit pins the release normaliser
to 0 on a peak-0 curve, so its sv is 10^0/24 = 0.0417 and its deposit
2.1e-6 copies/epoch - Theta carries the whole emission scale, which is
why the deposit comparison to witnesses is by regime, not by seed).
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from orchestrator_epoch import _airborne_emission_fraction  # noqa: E402
from picard_framework.covid_hull_scenarios import (  # noqa: E402
    load_hull_scenarios,
)
from picard_framework.covid_theta_fit import (  # noqa: E402
    EMISSION_BRACKET_COPIES_PER_EPOCH,
    PATHOGEN_ID,
)
from picard_framework.run_spec import PicardRunSpec  # noqa: E402
from picard_framework.simulation.ship_simulation import (  # noqa: E402
    ShipSimulation,
)

LICENSED_FINE_SHARE = 0.85  # Coleman 2021, inside [0.76, 0.92] - tranche 27


def observe_deposit(sim, work, out):
    """Sum this epoch's per-shedder sv and deposit into ``out``."""
    prof = sim.pathogen_profiles.get(PATHOGEN_ID)
    if prof is None:
        return
    dep_frac = _airborne_emission_fraction(prof)
    shedders = 0
    sv_sum = 0.0
    for agent in sim.engine.agents:
        sv = agent.get_pathogen_shedding(PATHOGEN_ID, prof)
        if sv <= 0:
            continue
        shedders += 1
        sv_sum += sv
        out["per_shedder_deposit"].append(sv * dep_frac)
    out["shedder_epochs"] += shedders
    out["sv_sum"] += sv_sum


def run_cell(scenario_id: str, seed: int, num_epochs: int | None) -> dict:
    scenarios = load_hull_scenarios(repo_root=REPO_ROOT)
    scenario = scenarios[scenario_id]
    raw = scenario.to_run_spec_dict(
        random_seed=int(seed), num_epochs=num_epochs,
    )
    raw["run"]["history_retention"] = "compact"
    spec = PicardRunSpec.from_picard_dict(REPO_ROOT, raw)
    out = {"shedder_epochs": 0, "sv_sum": 0.0, "per_shedder_deposit": []}
    with contextlib.redirect_stdout(io.StringIO()):
        sim = ShipSimulation(spec, display=False)
        sim.epoch_observer = lambda s, w: observe_deposit(s, w, out)
        sim.initialize()
        for _ in range(sim.num_epochs):
            sim.step()
    deps = out["per_shedder_deposit"]
    deps.sort()
    n = len(deps)
    return {
        "scenario_id": scenario_id,
        "seed": int(seed),
        "num_epochs": int(sim.num_epochs),
        "shedder_epochs": out["shedder_epochs"],
        "sv_sum_all_epochs": out["sv_sum"],
        "deposit_5e5": {
            "count": n,
            "median": deps[n // 2] if n else None,
            "max": deps[-1] if n else None,
            "total": sum(deps),
            "share_below_floor": (
                sum(1 for d in deps if d < EMISSION_BRACKET_COPIES_PER_EPOCH[0])
                / n if n else None
            ),
            "share_in_bracket": (
                sum(
                    1
                    for d in deps
                    if EMISSION_BRACKET_COPIES_PER_EPOCH[0]
                    <= d
                    <= EMISSION_BRACKET_COPIES_PER_EPOCH[1]
                )
                / n if n else None
            ),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[20201001, 20201002, 20201003, 20201004])
    ap.add_argument("--scenarios", nargs="+", default=["diamond_princess_2020", "greg_mortimer_2020"])
    ap.add_argument("--out", default=None)
    ap.add_argument("--only", default=None, help="scenario:seed single cell")
    ap.add_argument(
        "--num-epochs", type=int, default=None,
        help="window cap; the DP hull defaults to 480 (day 20) because a "
        "full 840-epoch DP voyage on 3,711 agents is a Batch-scale cell "
        "on this box. The window spans the index's whole shedding course, "
        "the pre-quarantine transmission mass and the day-16 order.",
    )
    args = ap.parse_args()
    cells = [
        (sid, seed)
        for sid in args.scenarios
        for seed in args.seeds
        if args.only is None or f"{sid}:{seed}" == args.only
    ]
    results = []
    for sid, seed in cells:
        res = run_cell(sid, seed, args.num_epochs)
        results.append(res)
        print(json.dumps(res["deposit_5e5"], indent=None), sid, seed, flush=True)
    low, high = EMISSION_BRACKET_COPIES_PER_EPOCH
    payload = {
        "bracket_per_epoch": [low, high],
        "theta_regime_deposit_per_epoch": (10**0 / 24) * 5e-5,  # clock-exempt: analytic Theta-regime deposit (sv 10^0 per day / 24 h), not a clock conversion the sim performs
        "licensed_fine_share": LICENSED_FINE_SHARE,
        "cells": results,
    }
    text = json.dumps(payload, indent=1)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text + "\n")
        print("wrote", args.out)
    else:
        print(text)


if __name__ == "__main__":
    main()
