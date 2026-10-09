"""DATING-RES diagnostic: decompose confirmed cases by specimen timing.

Dated onsets follow the record's own bookkeeping: a case is datable iff
its true symptom onset preceded the confirming specimen (the gate the
onset_recording channel enforces), times a recall draw. The measured
residual (dated share ~0.42 vs the record's 0.277 under the armed
channel) therefore collapses to one number: the share of confirmed cases
whose first positive specimen landed before symptom onset. The record
put that share at ~0.49 (Mizumoto 2020); the boxed hull reads ~0.24.

This probe decomposes that share by where the confirming specimen came
from and how it sat against the infection's course:

  * every confirmed case's specimen day vs infection day vs onset day
    (dpi at specimen, catch class: campaign/passive x pre-onset/post-onset);
  * whether the host was a cabin contact of an earlier-confirmed case at
    specimen time (the enriched pool the record's ladder reaches first);
  * the catchable pool: infected hosts and the share whose specimen fell
    inside their pre-onset window, plus its counterfactual if every
    contact-of-a-confirmed had been swabbed the day after the index
    confirmation;

so the residual names its own seam: thin contact enrichment, cadence
inside the pre-onset window, or structural volume.

    python3 tools/covid_specimen_timing_probe.py \
        --design picard_framework/runs/covid_crew_reach_01_design.json \
        --theta 7.9e6 --arm boxed_s1s2 \
        --seed 20200218 --seed 20200223 --seed 20200210 \
        --out reports/specimen_timing/s1s2.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from picard_framework.covid_boarding_screen import (  # noqa: E402
    load_design,
    prepare_cell_run_spec,
)
from picard_framework.covid_theta_fit import run_fit_spec  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    resolve_repo_path,
    validated_open,
)
from tools.covid_asym_conf_attribution import (  # noqa: E402
    _host_pools,
)
from tools.covid_funnel_attribution import _match_cell  # noqa: E402

ROLES = ("crew", "passenger")


def _contact_of_confirmed(
    sim: Any,
    pools: dict[str, Any],
) -> dict[int, int]:
    """First day each host became a cabin contact of a confirmed case."""
    confirmed = pools["confirmed"]
    day_of = pools["day_of"]
    first: dict[int, int] = {}
    for agent in sim.engine.agents:
        aid = int(agent.agent_id)
        mates = [int(m) for m in (getattr(agent, "cabin_mate_ids", None) or ())]
        hits = [
            day_of(confirmed[m]) for m in mates
            if m in confirmed and confirmed[m] is not None
        ]
        if hits:
            first[aid] = min(hits)
    return first


def _catch_class(
    *,
    campaign_days: set[int],
    spec_day: int,
    onset_day: int | None,
) -> str:
    channel = "campaign" if spec_day in campaign_days else "passive"
    pre = "pre_onset" if onset_day is None or spec_day < onset_day else "post_onset"
    return f"{channel}_{pre}"


def decompose_cell(
    design: object, theta: float, arm_id: str, seed: int,
) -> dict[str, Any]:
    """Re-run one cell and decompose its confirmed-case specimen timing."""
    cell = _match_cell(design, theta, arm_id, seed)
    raw = prepare_cell_run_spec(design, cell, repo_root=str(_REPO_ROOT))
    sim = run_fit_spec(raw, repo_root=str(_REPO_ROOT))
    pools = _host_pools(sim)
    day_of = pools["day_of"]
    confirmed = pools["confirmed"]
    onset = pools["onset"]
    infection = pools["infection_epoch"]
    role_of = pools["role_of"]

    campaign_days_of: dict[int, set[int]] = defaultdict(set)
    campaign_specimens_of: dict[int, list[int]] = defaultdict(list)
    for entry in pools["campaign_log"]:
        aid = int(entry["agent_id"])
        campaign_days_of[aid].add(int(entry["day"]))
        campaign_specimens_of[aid].append(int(entry["day"]))
    first_contact_day = _contact_of_confirmed(sim, pools)

    cases: list[dict[str, Any]] = []
    for aid, spec_ep in confirmed.items():
        spec_day = day_of(spec_ep)
        inf_day = day_of(infection[aid]) if aid in infection else None
        onset_day = day_of(onset[aid]) if aid in onset else None
        cases.append({
            "agent_id": aid,
            "role": role_of.get(aid, "passenger"),
            "infection_day": inf_day,
            "specimen_day": spec_day,
            "onset_day": onset_day,
            "dpi_at_specimen": (
                spec_day - inf_day if inf_day is not None else None
            ),
            "window_days": (
                (onset_day - inf_day)
                if (inf_day is not None and onset_day is not None)
                else None
            ),
            "class": _catch_class(
                campaign_days=campaign_days_of.get(aid, set()),
                spec_day=spec_day,
                onset_day=onset_day,
            ),
            "contact_of_confirmed_at_specimen": (
                aid in first_contact_day
                and first_contact_day[aid] <= spec_day
            ),
            "days_after_contact_eligibility": (
                spec_day - first_contact_day[aid]
                if aid in first_contact_day else None
            ),
        })

    # Catchable-pool coverage: infected hosts and whether any specimen
    # (campaign or passive) fell inside [infection, onset) — the window a
    # pre-onset confirmation requires.
    sampled = pools["sampled"]
    windowed: dict[str, dict[str, int]] = {
        k: {r: 0 for r in ROLES}
        for k in (
            "swabbed_in_window",
            "swabbed_only_outside_window",
            "never_swabbed",
        )
    }
    window_days_hist: list[int] = []
    for aid, inf_ep in infection.items():
        inf_day = day_of(inf_ep)
        onset_day = day_of(onset[aid]) if aid in onset else None
        role = role_of.get(aid, "passenger")
        if onset_day is not None:
            window_days_hist.append(onset_day - inf_day)
        spec_day = day_of(sampled[aid]) if aid in sampled else None
        if spec_day is None:
            windowed["never_swabbed"][role] += 1
        elif onset_day is None or inf_day <= spec_day < onset_day:
            windowed["swabbed_in_window"][role] += 1
        else:
            windowed["swabbed_only_outside_window"][role] += 1

    # Counterfactual: contacts of confirmeds swabbed the day after the
    # index confirmation. How many infected contacts were still pre-onset
    # that day, i.e. would have been pre-onset catches (weighted by
    # sensitivity at their dpi that day)?
    sensitivity = pools["sensitivity"]

    def sens_at(dpi: int) -> float:
        if dpi < 0:
            return 0.0
        return float(sensitivity[min(dpi, len(sensitivity) - 1)])

    cf_catches: dict[str, float] = {r: 0.0 for r in ROLES}
    cf_hosts: dict[str, int] = {r: 0 for r in ROLES}
    for aid, contact_day in first_contact_day.items():
        if aid in confirmed or aid not in infection:
            continue
        inf_day = day_of(infection[aid])
        onset_day = day_of(onset[aid]) if aid in onset else None
        spec_day = contact_day + 1
        if spec_day < inf_day:
            continue
        if onset_day is None or spec_day < onset_day:
            role = role_of.get(aid, "passenger")
            cf_hosts[role] += 1
            cf_catches[role] += sens_at(spec_day - inf_day)

    def _classes() -> dict[str, dict[str, int]]:
        out: dict[str, dict[str, int]] = {}
        for case in cases:
            out.setdefault(case["class"], {r: 0 for r in ROLES})
            out[case["class"]][case["role"]] += 1
        return out

    def _stat(values: list[int]) -> dict[str, float | None]:
        if not values:
            return {"median": None, "mean": None}
        vs = sorted(values)
        return {
            "median": vs[len(vs) // 2],
            "mean": round(sum(vs) / len(vs), 2),
        }

    return {
        "seed": seed,
        "arm_id": arm_id,
        "infections_total": len(infection),
        "lab_confirmed_total": len(cases),
        "catch_classes": _classes(),
        "pre_onset_share_of_confirmed": (
            sum(
                1 for c in cases if c["class"].endswith("_pre_onset")
            ) / len(cases)
            if cases else None
        ),
        "dpi_at_specimen": _stat(
            [c["dpi_at_specimen"] for c in cases
             if c["dpi_at_specimen"] is not None]
        ),
        "preonset_window_days": _stat(window_days_hist),
        "contact_of_confirmed_confirmed": sum(
            1 for c in cases if c["contact_of_confirmed_at_specimen"]
        ),
        "window_coverage": windowed,
        "counterfactual_next_day_contact_swab": {
            "pre_onset_hosts": cf_hosts,
            "expected_positives": {k: round(v, 1) for k, v in cf_catches.items()},
        },
        "cases": cases,
    }


def _pool_cells(cells: list[dict[str, Any]]) -> dict[str, Any]:
    classes: dict[str, dict[str, int]] = {}
    windowed: dict[str, dict[str, int]] = {}
    total = 0
    pre = 0
    for cell in cells:
        total += cell["lab_confirmed_total"]
        for key, roles in cell["catch_classes"].items():
            classes.setdefault(key, {r: 0 for r in ROLES})
            for role, n in roles.items():
                classes[key][role] += n
                if key.endswith("_pre_onset"):
                    pre += n
        for key, roles in cell["window_coverage"].items():
            windowed.setdefault(key, {r: 0 for r in ROLES})
            for role, n in roles.items():
                windowed[key][role] += n
    return {
        "lab_confirmed_total": total,
        "pre_onset_share_of_confirmed": (pre / total if total else None),
        "catch_classes": classes,
        "window_coverage": windowed,
    }


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
    print(json.dumps(out["pooled"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
