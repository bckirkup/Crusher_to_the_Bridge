"""Paired-seed probe for the AERO-SPLIT-01 droplet emission partition.

Runs the declared Diamond Princess replay at Theta = 4.22e10 — the stage-2
cell shape from ``covid_theta_screen_v11_stage2`` — once per seed under the
shipped ``partition`` mode and once under the labelled ``off`` baseline
(``transmission_overrides.droplet_field_split.mode = off``, the pre-change
tree: the pool carries the whole continuous share and no proximity draw
exists). A ``QuarantineAttributionLedger`` epoch observer records every
transmission event's epoch, zone and dominant dose route, so the readout is
the prompt metric — total event count and the day-0-2 event share — on
paired seeds, plus the venue/route mix for the ledger entry.

Usage:
    python3 tools/covid_droplet_split_probe.py \
        [--theta 4.22e10] [--seeds 20200205 20200206] [--mode partition|off]
        [--out results/droplet_split_probe.json]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from picard_framework.covid_boarding_screen import (
    QuarantineAttributionLedger,
    enumerate_cells,
    load_design,
    prepare_cell_run_spec,
)
from picard_framework.covid_theta_fit import PATHOGEN_ID, run_fit_spec

DESIGN_REL = os.path.join(
    "picard_framework", "runs", "covid_theta_screen_v11_stage2_design.json",
)
DAY_EPOCHS = 24


def _design(repo_root: str):
    return load_design(os.path.join(repo_root, DESIGN_REL))


def _cell(design, theta: float, seed: int):
    matches = [
        c for c in enumerate_cells(design)
        if c.seed == seed and float(c.theta) == theta
    ]
    if not matches:
        raise SystemExit(f"no cell for theta={theta} seed={seed}")
    return matches[0]


def _event_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(events)
    early = sum(1 for e in events if e["epoch"] < 3 * DAY_EPOCHS)
    by_five = sum(1 for e in events if e["epoch"] < 5 * DAY_EPOCHS)
    zones = Counter(e["zone"] for e in events)
    pathways = Counter(e["pathway"] for e in events)
    confined = sum(1 for e in events if e["confined"])
    return {
        "events_total": total,
        "events_day0_2": early,
        "day0_2_share": early / total if total else 0.0,
        "events_day0_5": by_five,
        "day0_5_share": by_five / total if total else 0.0,
        "events_confined": confined,
        "zones": dict(zones.most_common()),
        "pathways": dict(pathways.most_common()),
    }


def run_one(
    design,
    theta: float,
    seed: int,
    mode: str,
    repo_root: str,
    num_epochs: int | None = None,
) -> dict[str, Any]:
    cell = _cell(design, theta, seed)
    raw = prepare_cell_run_spec(
        design, cell, num_epochs=num_epochs, repo_root=repo_root,
    )
    raw["config_overrides"].setdefault("transmission", {})[
        "droplet_field_split"
    ] = {"mode": mode}
    ledger = QuarantineAttributionLedger()
    sim = run_fit_spec(raw, repo_root=repo_root, epoch_observer=ledger.observe)
    seeded = set(getattr(sim.engine, "explicit_seed_agent_ids", ()) or ())
    secondaries = sum(
        1 for a in sim.engine.agents
        if PATHOGEN_ID in a.infections and a.agent_id not in seeded
    )
    return {
        "cell": cell.as_dict(),
        "mode": mode,
        "infections_total_truth": int(secondaries),
        **_event_summary(ledger.events),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--theta", type=float, default=4.22e10)
    parser.add_argument(
        "--seeds", type=int, nargs="+", default=[20200205, 20200206],
    )
    parser.add_argument(
        "--mode", choices=["partition", "off"], default=None,
        help="run one mode only; default runs both paired per seed",
    )
    parser.add_argument("--out", default=None)
    parser.add_argument(
        "--num-epochs", type=int, default=None,
        help="truncate the voyage (smoke only — not the declared replay)",
    )
    args = parser.parse_args()

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    design = _design(repo_root)
    modes = [args.mode] if args.mode else ["off", "partition"]
    results = []
    for seed in args.seeds:
        for mode in modes:
            print(f"running seed {seed} mode {mode} ...", flush=True)
            results.append(
                run_one(
                    design, args.theta, seed, mode, repo_root,
                    num_epochs=args.num_epochs,
                ),
            )
            print(
                f"  events={results[-1]['events_total']} "
                f"day0-2={results[-1]['day0_2_share']:.3f}",
                flush=True,
            )
    payload = {
        "design_id": design.design_id,
        "theta": args.theta,
        "cells": results,
    }
    text = json.dumps(payload, indent=2)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
