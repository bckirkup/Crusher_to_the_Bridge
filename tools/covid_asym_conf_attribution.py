#!/usr/bin/env python3
"""ASYM-CONF-01: decompose confirmed cases by presentation status at specimen.

The record's ~0.49 is the share of confirmed positives that had NOT
presented symptoms when the specimen was taken (Mizumoto 2020). On the
boxed cells the funnel attribution measured a symptomatic-at-specimen
share of ~0.76 - the channel over-confirms presenters and under-confirms
non-presenters. This tool re-runs a campaign cell keeping the finished
sim (the same-realization rule from the funnel attribution: per-cell
tallies reproduce the Batch cells exactly) and decomposes, per role:

  * lab_confirmed cases by specimen channel (testing-campaign roster vs
    passive sick-call lab sampling) crossed with whether the host had
    presented on or before its specimen epoch;
  * the replicated campaign day-by-day: published capacity, roster size
    (a day whose roster comes in under capacity is a day the ladder ran
    out of eligible hosts, not a day capacity starved the roster),
    and the specimens' presentation state and result;
  * the unconfirmed infected pool: never swabbed, swabbed only before
    infection (the barred-negative drain), swabbed while infected but
    negative (the assay-timing drain), each split by whether the host
    ever presented - the three failure modes point at different
    declared observation structures;
  * days-post-infection at each campaign specimen of an infected host,
    read against the declared sensitivity curve (Kucirka 2020): a swab
    inside the low-sensitivity window is a specimen the record could not
    have expected to come back positive.

Usage:
    python3 tools/covid_asym_conf_attribution.py \
        --design <design.json> --theta 7.9e6 --arm <arm> \
        --seed 20200218 [--seed ...] --out <json>
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from picard_framework.covid_boarding_screen import (  # noqa: E402
    _quarantine_window,
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
from tools.covid_funnel_attribution import _match_cell  # noqa: E402

ROLES = ("crew", "passenger")


def _role_counts() -> dict[str, int]:
    return {role: 0 for role in ROLES}


def _bump(table: dict[str, dict[str, int]], key: str, role: str) -> None:
    table.setdefault(key, _role_counts())
    if role in table[key]:
        table[key][role] += 1


def _host_pools(sim: Any) -> dict[str, Any]:
    """Pull the modality's observation state for this pathogen."""
    syndromic = sim.modalities["syndromic"]
    confirmed = {
        aid: int(ep)
        for (pid, aid), ep in syndromic._lab_confirmed.items()
        if pid == PATHOGEN_ID
    }
    sampled = {
        aid: int(ep)
        for (pid, aid), ep in syndromic._lab_sampled.items()
        if pid == PATHOGEN_ID
    }
    onset = {
        int(aid): int(ep)
        for aid, ep in syndromic._presentation_onset_epoch.items()
    }
    campaign_log = syndromic.campaign_specimen_log(PATHOGEN_ID)
    campaign = syndromic.campaign_for(PATHOGEN_ID)
    models = syndromic._molecular_models()
    sensitivity = list(models[PATHOGEN_ID]["sensitivity_by_day"])
    return {
        "confirmed": confirmed,
        "sampled": sampled,
        "onset": onset,
        "campaign_log": campaign_log,
        "campaign": campaign,
        "sensitivity": sensitivity,
        "role_of": {
            a.agent_id: getattr(a, "role", None) or "passenger"
            for a in sim.engine.agents
        },
        "infection_epoch": {
            a.agent_id: int(a.infections[PATHOGEN_ID]["infection_epoch"])
            for a in sim.engine.agents
            if PATHOGEN_ID in a.infections
        },
        "day_of": lambda e: sim.clock.day_index(int(e)),
        "end_epoch": int(sim.num_epochs) - 1,
    }


def _confirmed_channels(pools: dict[str, Any]) -> dict[str, dict[str, int]]:
    """lab_confirmed cases by specimen channel x presentation at specimen."""
    campaign_positive_at: dict[int, set[int]] = {}
    for entry in pools["campaign_log"]:
        if entry["positive"]:
            campaign_positive_at.setdefault(
                int(entry["agent_id"]), set(),
            ).add(int(entry["epoch"]))
    out: dict[str, dict[str, int]] = {}
    onset = pools["onset"]
    for aid, epoch in pools["confirmed"].items():
        symptomatic = onset.get(aid) is not None and onset[aid] <= epoch
        channel = (
            "campaign"
            if epoch in campaign_positive_at.get(aid, set())
            else "passive"
        )
        key = f"{channel}_{'symptomatic' if symptomatic else 'asymptomatic'}"
        _bump(out, key, pools["role_of"].get(aid) or "passenger")
    for key in (
        "campaign_symptomatic",
        "campaign_asymptomatic",
        "passive_symptomatic",
        "passive_asymptomatic",
    ):
        out.setdefault(key, _role_counts())
    return out


def _campaign_days(pools: dict[str, Any]) -> list[dict[str, Any]]:
    """Per campaign day: capacity spent and who the roster swabbed."""
    infection_day = {
        aid: pools["day_of"](ep)
        for aid, ep in pools["infection_epoch"].items()
    }
    by_day: dict[int, dict[str, Any]] = {}
    for entry in pools["campaign_log"]:
        day = int(entry["day"])
        row = by_day.setdefault(day, {
            "day": day,
            "specimens": 0,
            "to_symptomatic": 0,
            "to_asymptomatic": 0,
            "positive_symptomatic": 0,
            "positive_asymptomatic": 0,
            "crew_specimens": 0,
            "infected_swabbed": 0,
            "infected_negative": 0,
            "negative_dpi_hist": Counter(),
        })
        row["specimens"] += 1
        aid = int(entry["agent_id"])
        symptomatic = bool(entry["symptomatic_at_specimen"])
        row["to_symptomatic" if symptomatic else "to_asymptomatic"] += 1
        if entry["positive"]:
            key = (
                "positive_symptomatic" if symptomatic
                else "positive_asymptomatic"
            )
            row[key] += 1
        if entry["role"] == "crew":
            row["crew_specimens"] += 1
        if aid in infection_day:
            row["infected_swabbed"] += 1
            if not entry["positive"]:
                row["infected_negative"] += 1
                dpi = day - infection_day[aid]
                row["negative_dpi_hist"][dpi] += 1
    campaign = pools["campaign"]
    days = []
    for day in sorted(by_day):
        row = by_day[day]
        row["capacity"] = (
            campaign.capacity_for_day(day) if campaign is not None else None
        )
        row["negative_dpi_hist"] = {
            str(k): v for k, v in sorted(row["negative_dpi_hist"].items())
        }
        days.append(row)
    return days


def _unconfirmed_infected(pools: dict[str, Any]) -> dict[str, dict[str, int]]:
    """Infected-but-unconfirmed hosts by the failure mode that held them."""
    out: dict[str, dict[str, int]] = {}
    onset = pools["onset"]
    day_of = pools["day_of"]
    for aid, infection_epoch in pools["infection_epoch"].items():
        if aid in pools["confirmed"]:
            continue
        role = pools["role_of"].get(aid) or "passenger"
        presented = aid in onset
        specimen_epoch = pools["sampled"].get(aid)
        if specimen_epoch is None:
            mode = "never_swabbed"
        elif day_of(specimen_epoch) < day_of(infection_epoch):
            mode = "swabbed_only_pre_infection"
        else:
            mode = "swabbed_while_infected_negative"
        key = f"{mode}_{'presented' if presented else 'never_presented'}"
        _bump(out, key, role)
    for mode in (
        "never_swabbed",
        "swabbed_only_pre_infection",
        "swabbed_while_infected_negative",
    ):
        for state in ("presented", "never_presented"):
            out.setdefault(f"{mode}_{state}", _role_counts())
    return out


def _sensitivity_at(pools: dict[str, Any], days_post: int) -> float:
    curve = pools["sensitivity"]
    if not curve:
        return 0.0
    return float(curve[min(max(int(days_post), 0), len(curve) - 1)])


def _counterfactual(pools: dict[str, Any]) -> dict[str, Any]:
    """Expected positives had each missed host been swabbed at voyage end.

    A bound, not a plan: sums the declared Kucirka sensitivity at the
    host's days-post-infection on the final simulated day over each
    failure bucket, split by whether the host ever presented. Nothing is
    fitted; it sizes the observable mass each candidate structure could
    in principle recover.
    """
    onset = pools["onset"]
    day_of = pools["day_of"]
    end_day = day_of(pools["end_epoch"])
    totals: dict[str, float] = {}
    counts: dict[str, int] = {}
    for aid, infection_epoch in pools["infection_epoch"].items():
        if aid in pools["confirmed"]:
            continue
        specimen_epoch = pools["sampled"].get(aid)
        if specimen_epoch is None:
            mode = "never_swabbed"
        elif day_of(specimen_epoch) < day_of(infection_epoch):
            mode = "swabbed_only_pre_infection"
        else:
            mode = "swabbed_while_infected_negative"
        state = "presented" if aid in onset else "never_presented"
        key = f"{mode}_{state}"
        dpi = max(end_day - day_of(infection_epoch), 0)
        totals[key] = totals.get(key, 0.0) + _sensitivity_at(pools, dpi)
        counts[key] = counts.get(key, 0) + 1
    return {
        "expected_positives": {k: round(v, 1) for k, v in totals.items()},
        "hosts": counts,
    }


def decompose_cell(
    design: object, theta: float, arm_id: str, seed: int,
) -> dict[str, Any]:
    """Re-run one boxed cell and decompose the confirmed-case pool."""
    cell = _match_cell(design, theta, arm_id, seed)
    raw = prepare_cell_run_spec(design, cell, repo_root=str(_REPO_ROOT))
    sim = run_fit_spec(raw, repo_root=str(_REPO_ROOT))
    _entry, start, end = _quarantine_window(raw)
    pools = _host_pools(sim)
    confirmed = _confirmed_channels(pools)
    campaign_days = _campaign_days(pools)
    unconfirmed = _unconfirmed_infected(pools)
    counterfactual = _counterfactual(pools)
    symptomatic = sum(sum(v.values()) for k, v in confirmed.items()
                      if k.endswith("_symptomatic"))
    total = sum(sum(v.values()) for v in confirmed.values())
    return {
        "seed": seed,
        "arm_id": arm_id,
        "window_days": [start, end],
        "infections_total": len(pools["infection_epoch"]),
        "lab_confirmed_total": total,
        "confirmed_by_channel_status": confirmed,
        "asymptomatic_share_of_confirmed": (
            (total - symptomatic) / total if total else None
        ),
        "campaign_days": campaign_days,
        "unconfirmed_infected": unconfirmed,
        "counterfactual_end_voyage": counterfactual,
    }


def _pool_cells(cells: list[dict[str, Any]]) -> dict[str, Any]:
    pooled_confirmed: dict[str, dict[str, int]] = {}
    pooled_unconfirmed: dict[str, dict[str, int]] = {}
    for cell in cells:
        for key, roles in cell["confirmed_by_channel_status"].items():
            for role, n in roles.items():
                _bump_series(pooled_confirmed, key, role, n)
        for key, roles in cell["unconfirmed_infected"].items():
            for role, n in roles.items():
                _bump_series(pooled_unconfirmed, key, role, n)
    total = sum(sum(v.values()) for v in pooled_confirmed.values())
    symptomatic = sum(
        sum(v.values()) for k, v in pooled_confirmed.items()
        if k.endswith("_symptomatic")
    )
    return {
        "lab_confirmed_total": total,
        "confirmed_by_channel_status": pooled_confirmed,
        "asymptomatic_share_of_confirmed": (
            (total - symptomatic) / total if total else None
        ),
        "unconfirmed_infected": pooled_unconfirmed,
    }


def _bump_series(
    table: dict[str, dict[str, int]], key: str, role: str, n: int,
) -> None:
    table.setdefault(key, _role_counts())
    if role in table[key]:
        table[key][role] += n


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", required=True)
    parser.add_argument("--theta", type=float, required=True)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--seed", type=int, action="append", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    design = load_design(resolve_repo_path(str(_REPO_ROOT), args.design))
    cells = [
        decompose_cell(design, args.theta, args.arm, s) for s in args.seed
    ]
    out = {"cells": cells, "pooled": _pool_cells(cells)}
    out_path = Path(resolve_repo_path(str(_REPO_ROOT), args.out))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with validated_open(
        str(out_path), "w", allowed_roots=(str(_REPO_ROOT),)
    ) as fh:
        fh.write(json.dumps(out, indent=1) + "\n")
    pooled = out["pooled"]
    print(json.dumps({
        "lab_confirmed_total": pooled["lab_confirmed_total"],
        "asymptomatic_share": pooled["asymptomatic_share_of_confirmed"],
        "confirmed_by_channel_status": pooled["confirmed_by_channel_status"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
