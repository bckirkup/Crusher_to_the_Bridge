#!/usr/bin/env python3
"""Funnel attribution: where the DP crew share sits at each observation stage.

The record's 0.29 is the crew share of *confirmed* cases (712 total).
The measurement to date scored acquisitions (0.683) and dated recorded
onsets (0.475). Neither is the right comparator: the funnel runs

    infection -> symptomatic -> specimen -> assay -> lab_confirmed
        -> [onset_recording channel] -> dated onset

and each stage can move the crew share. This tool re-runs a campaign
cell keeping the finished sim (same-realization rule from the berth
attribution: crew-event counts reproduce the Batch cells exactly) and
tallies, per role:

  * infections_total (all acquisitions, and the during-window subset)
  * lab_confirmed (any specimen channel: passive lab sampling + the
    replicated DP testing campaign, whose eligibility ladder tests
    crew last)
  * confirmed-and-ever-presented (a symptom onset exists at all —
    the datable pool)
  * the symptomatic-at-specimen counterfactual: confirmed cases whose
    presentation onset came on or before their specimen epoch — the
    share that survives SERO-CHANNEL-V1's specimen gate. The recall
    draw (report_probability) is flat per case and cannot move the
    share, so it is reported as count math only.

Usage:
    python3 tools/covid_funnel_attribution.py \
        --design <design.json> --theta 7.9e6 --arm <arm> \
        --seed 20200218 [--seed ...] --out <json>
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from picard_framework.covid_boarding_screen import (  # noqa: E402
    _quarantine_window,
    enumerate_cells,
    load_design,
    prepare_cell_run_spec,
)
from picard_framework.covid_theta_fit import (  # noqa: E402
    PATHOGEN_ID,
    run_fit_spec,
)
from simulation_utils.paths import (  # noqa: E402
    resolve_repo_path,
    validated_open,
)


def _match_cell(design: object, theta: float, arm_id: str, seed: int) -> object:
    matches = [
        cell for cell in enumerate_cells(design)
        if cell.arm_id == arm_id and cell.seed == seed
        and math.isclose(cell.theta, theta, rel_tol=1e-12)
    ]
    if len(matches) != 1:
        raise SystemExit(
            f"{len(matches)} cells match theta={theta} arm={arm_id} "
            f"seed={seed}; expected exactly 1",
        )
    return matches[0]


def funnel_seed(
    design: object, theta: float, arm_id: str, seed: int,
) -> dict[str, object]:
    """Re-run one cell and decompose the observation funnel by role."""
    cell = _match_cell(design, theta, arm_id, seed)
    raw = prepare_cell_run_spec(design, cell, repo_root=str(_REPO_ROOT))
    sim = run_fit_spec(raw, repo_root=str(_REPO_ROOT))
    _entry, start, end = _quarantine_window(raw)

    role_of = {
        a.agent_id: getattr(a, "role", None) or "passenger"
        for a in sim.engine.agents
    }
    syndromic = sim.modalities["syndromic"]

    # infection day per agent (all acquisitions; repeats collapse to first)
    infection_epoch = {
        a.agent_id: int(a.infections[PATHOGEN_ID]["infection_epoch"])
        for a in sim.engine.agents
        if PATHOGEN_ID in a.infections
    }
    day_of = lambda e: sim.clock.day_index(int(e))  # noqa: E731

    confirmed = {
        aid: int(ep)
        for (pid, aid), ep in syndromic._lab_confirmed.items()
        if pid == PATHOGEN_ID
    }
    onset_epoch = {
        int(aid): int(ep)
        for aid, ep in syndromic._presentation_onset_epoch.items()
    }

    def tally(pred) -> dict[str, int]:
        out = {"crew": 0, "passenger": 0, "other": 0}
        for aid in confirmed:
            if pred(aid):
                out[role_of.get(aid) or "other"] += 1
        return out

    infected = {
        "total": {"crew": 0, "passenger": 0},
        "during_window": {"crew": 0, "passenger": 0},
    }
    for aid, ep in infection_epoch.items():
        role = role_of.get(aid, "other")
        if role not in ("crew", "passenger"):
            continue
        infected["total"][role] += 1
        d = day_of(ep)
        if start <= d <= (end if end is not None else start):
            infected["during_window"][role] += 1

    presented = tally(lambda aid: aid in onset_epoch)
    gate_pass = tally(
        lambda aid: aid in onset_epoch
        and onset_epoch[aid] <= confirmed[aid]
    )

    confirmed_by_role = {"crew": 0, "passenger": 0, "other": 0}
    for aid in confirmed:
        confirmed_by_role[role_of.get(aid) or "other"] += 1

    recorded = {"crew": 0, "passenger": 0, "other": 0}
    for (pid, aid), rec in syndromic._onset_observations.items():
        if pid == PATHOGEN_ID:
            recorded[role_of.get(aid) or "other"] += 1

    return {
        "seed": seed,
        "arm_id": arm_id,
        "window_days": [start, end],
        "infected": infected,
        "lab_confirmed": confirmed_by_role,
        "confirmed_and_presented": presented,
        "gate_pass_symptomatic_at_specimen": gate_pass,
        "recorded_onsets": recorded,
        "lab_confirmed_total": syndromic.lab_confirmed_count(PATHOGEN_ID),
        "onset_recording_channel": syndromic.onset_recording_channel(
            PATHOGEN_ID
        ),
    }


def _share(role_counts: dict[str, int], role: str = "crew") -> float | None:
    total = sum(role_counts.values())
    if total == 0:
        return None
    return role_counts.get(role, 0) / total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", required=True)
    parser.add_argument("--theta", type=float, required=True)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--seed", type=int, action="append", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    design = load_design(
        resolve_repo_path(str(_REPO_ROOT), args.design)
    )

    cells = [
        funnel_seed(design, args.theta, args.arm, s) for s in args.seed
    ]
    pooled_keys = (
        "lab_confirmed",
        "confirmed_and_presented",
        "gate_pass_symptomatic_at_specimen",
        "recorded_onsets",
    )
    pooled = {k: {"crew": 0, "passenger": 0, "other": 0} for k in pooled_keys}
    pooled["infected_total"] = {"crew": 0, "passenger": 0}
    pooled["infected_during_window"] = {"crew": 0, "passenger": 0}
    for c in cells:
        for k in pooled_keys:
            for role, n in c[k].items():
                pooled[k][role] += n
        for role, n in c["infected"]["total"].items():
            pooled["infected_total"][role] += n
        for role, n in c["infected"]["during_window"].items():
            pooled["infected_during_window"][role] += n

    shares = {
        "infected_total_crew_share": _share(pooled["infected_total"]),
        "infected_during_crew_share": _share(
            pooled["infected_during_window"]
        ),
        "lab_confirmed_crew_share": _share(pooled["lab_confirmed"]),
        "presented_crew_share": _share(pooled["confirmed_and_presented"]),
        "gate_pass_crew_share": _share(
            pooled["gate_pass_symptomatic_at_specimen"]
        ),
        "recorded_onset_crew_share": _share(pooled["recorded_onsets"]),
        "dated_share_of_confirmed": (
            sum(pooled["recorded_onsets"].values())
            / sum(pooled["lab_confirmed"].values())
            if sum(pooled["lab_confirmed"].values())
            else None
        ),
        "gated_share_of_confirmed": (
            sum(pooled["gate_pass_symptomatic_at_specimen"].values())
            / sum(pooled["lab_confirmed"].values())
            if sum(pooled["lab_confirmed"].values())
            else None
        ),
    }

    out = {"cells": cells, "pooled": pooled, "shares": shares}
    out_path = Path(
        resolve_repo_path(str(_REPO_ROOT), args.out)
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with validated_open(
        str(out_path), "w", allowed_roots=(str(_REPO_ROOT),)
    ) as fh:
        fh.write(json.dumps(out, indent=1) + "\n")
    print(json.dumps(shares, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
