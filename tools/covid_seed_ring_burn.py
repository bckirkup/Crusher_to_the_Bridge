#!/usr/bin/env python3
"""Day-0 ring-burn readout for a declared covid takeoff cell, for ledger
COVID-SEED-GEOM-01.

Purpose
-------
The Diamond Princess scenario boards one index case at voyage epoch 0 with
a declared ``onset_day`` (the seed is already mid-course when the voyage
starts) and a declared ``departure_day`` (the index leaves the ship mid-
voyage). While that one host is aboard it is the only infectious host —
every onboard acquisition before the first secondary could itself shed is
an index-attributable infection, so the voyage starts with not one seed
but a ring of effective co-primaries. This tool measures that ring:

    per seed: every non-seeded infection's acquisition epoch, dominant
    acquired-dose route, zone class and role, split into the window the
    index was aboard (epoch < departure_epoch) vs after it left.

Two side measurements ride the same cells:

* **Age-null verification.** Under a declared ``onset_day`` the seed's
  ``infection_age_days`` is claimed to cancel exactly (the shedding age is
  onset-anchored: ``days_since_onset = d - onset_day + seed_day``, and
  clearance is indexed the same way). ``--age-pair`` re-runs the same
  seeds with the seed's age rewritten and compares the full per-agent
  infection record — a bit-difference means the axis is live after all.
* **Secondary-shedding bound.** For every infected host the tool records
  ``infection_epoch + (onset - presymptomatic)`` — the earliest epoch it
  could emit — so acquisitions inside the aboard window that post-date the
  first possible secondary shed are flagged as possibly generation-2
  rather than index-attributed.

Method
------
Read-only instrumentation: the run spec is the design's declared cell
spec (``prepare_cell_run_spec``), observed through the same
``QuarantineAttributionLedger`` the boarding screen uses — one record per
non-seeded infection: acquisition epoch, dominant route (the engine's own
``acquired_particles_by_route`` argmax), zone, confinement flag. Nothing
draws from the engine's RNG; the cell is what a takeoff cell would have
run.

Inputs
------
``--design`` (default ``covid_sero_channel_v1``), ``--theta`` (default the
design's x1.0 = 4.22e10), ``--arm`` (default ``D0_declared``), ``--seeds``
(comma list of seed integers; the design's seeds are ``seed_base + i``),
``--epochs`` (truncate the voyage — the burn is visible by day ~8;
full length is 768), ``--age-pair FLOAT`` (re-run each seed with the
seed's ``infection_age_days`` rewritten and diff the outcomes), ``--out``.

Outputs
-------
Per seed: the index record (seeded age/onset/departure), the acquisition
table, the aboard-window count and route split, the secondary-shedding
bound split, recorded onsets at truncation. The readout pools per-seed
counts (median + IQR) for the ledger.

Nothing here fits or selects a parameter value; the readout describes the
mechanism the declared spec already runs.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from picard_framework.covid_boarding_screen import (  # noqa: E402
    PATHOGEN_ID,
    QuarantineAttributionLedger,
    enumerate_cells,
    prepare_cell_run_spec,
)
from picard_framework.covid_theta_fit import run_fit_spec  # noqa: E402
from tools.covid_assay_smoke import load_declared_cells, repo_root_of  # noqa: E402
from tools.covid_route_attribution import NearFieldShareLedger  # noqa: E402


def _quantiles(vals: list[float]) -> dict[str, Any]:
    if not vals:
        return {"n": 0}
    ordered = sorted(float(v) for v in vals)
    n = len(ordered)

    def q(p: float) -> float:
        k = (n - 1) * p
        lo = int(k)
        hi = min(lo + 1, n - 1)
        return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)

    return {
        "n": n,
        "min": ordered[0],
        "q25": q(0.25),
        "median": q(0.5),
        "q75": q(0.75),
        "max": ordered[-1],
        "mean": sum(ordered) / n,
    }


def _seed_spec(raw: dict[str, Any]) -> dict[str, Any]:
    seeds = (
        raw.get("config_overrides", {})
        .get("initiation", {}).get("explicit_seeds", [])
    )
    return seeds[0] if seeds else {}


def _infection_records(sim: Any, pathogen_id: str) -> dict[int, dict[str, Any]]:
    out = {}
    for agent in sim.engine.agents:
        inf = agent.infections.get(pathogen_id)
        if inf is None:
            continue
        out[int(agent.agent_id)] = inf
    return out


def _earliest_shed_epoch(
    inf: dict[str, Any], infection_epoch: int, presymptomatic_epochs: int,
    clock: Any,
) -> int | None:
    """First epoch this host could emit anything.

    Shedding opens ``presymptomatic_shedding_days`` before onset; a host
    that never presents sheds by the lazy incubation draw the same way.
    Clamped at the acquisition epoch — a host cannot emit before it is
    infected, however short its incubation draw sits inside the
    presymptomatic window.
    """
    onset = inf.get("onset_time_infected")
    incubation = inf.get("incubation_days")
    if onset is not None:
        start = int(infection_epoch) + int(onset) - presymptomatic_epochs
    elif incubation is not None:
        start = (
            int(infection_epoch)
            + int(round(clock.epochs_for_days(float(incubation))))
            - presymptomatic_epochs
        )
    else:
        return None
    return max(int(infection_epoch), start)


def analyse_seed(
    design: Any,
    cell: Any,
    *,
    num_epochs: int | None,
    repo_root: str,
    age_override: float | None = None,
    seed_patch: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run one cell and read off the day-0 burn."""
    raw = prepare_cell_run_spec(
        design, cell, num_epochs=num_epochs, repo_root=repo_root,
    )
    if age_override is not None:
        seed_spec = _seed_spec(raw)
        seed_spec["infection_age_days"] = float(age_override)
    if seed_patch:
        seed_spec = _seed_spec(raw)
        for key, value in seed_patch.items():
            if value is None:
                seed_spec.pop(key, None)
            else:
                seed_spec[key] = value
    seed_spec = _seed_spec(raw)
    departure_day = seed_spec.get("departure_day")
    ledger = QuarantineAttributionLedger()
    near = NearFieldShareLedger()

    def observer(sim: Any, work: Any) -> None:
        ledger.observe(sim, work)
        near.observe(sim, work)

    sim = run_fit_spec(raw, repo_root=repo_root, epoch_observer=observer)

    profile = sim.pathogen_profiles[PATHOGEN_ID]
    clock = sim.clock
    presymp_epochs = int(round(
        clock.epochs_for_days(
            float(profile.get("presymptomatic_shedding_days", 0.0)),
        ),
    ))
    seeded_ids = set(
        getattr(sim.engine, "explicit_seed_agent_ids", None) or (),
    )
    records = _infection_records(sim, PATHOGEN_ID)
    roles = {int(a.agent_id): str(getattr(a, "role", "")) for a in sim.engine.agents}

    # Earliest epoch at which any non-seed host could emit — the bound on
    # clean index attribution inside the aboard window.
    secondary_shed_epochs = [
        s for aid, inf in records.items()
        if aid not in seeded_ids
        for s in [
            _earliest_shed_epoch(
                inf, int(inf.get("infection_epoch") or 0), presymp_epochs,
                clock,
            )
        ]
        if s is not None
    ]
    first_secondary_shed = (
        min(secondary_shed_epochs) if secondary_shed_epochs else None
    )

    departure_epoch = (
        int(round(clock.epochs_for_days(float(departure_day))))
        if departure_day is not None else None
    )
    aboard_targets = {
        t for t, e in near.infection_epoch.items()
        if departure_epoch is None or e < departure_epoch
    }
    ring_share = [
        (near.near.get(t, 0.0) + near.addback.get(t, 0.0))
        / near.total.get(t, 1.0)
        for t in aboard_targets
        if near.total.get(t, 0.0) > 0.0
    ]
    events = ledger.events
    aboard = [
        e for e in events
        if departure_epoch is None or int(e["epoch"]) < departure_epoch
    ]
    aboard_clean = [
        e for e in aboard
        if first_secondary_shed is None
        or int(e["epoch"]) < first_secondary_shed
    ]

    def _route_split(rows: list[dict[str, Any]]) -> dict[str, int]:
        return dict(Counter(str(e["pathway"]) for e in rows))

    def _role_split(rows: list[dict[str, Any]]) -> dict[str, int]:
        return dict(Counter(roles.get(int(e["target_agent_id"]), "?") for e in rows))

    by_day = Counter(clock.day_index(int(e["epoch"])) for e in events)
    index_records = {
        aid: {
            "infection_epoch": int(records[aid].get("infection_epoch") or 0),
            "onset_time_infected": records[aid].get("onset_time_infected"),
            "incubation_days": records[aid].get("incubation_days"),
            "will_present": records[aid].get("will_present"),
        }
        for aid in sorted(seeded_ids)
        if aid in records
    }
    return {
        "cell": cell.as_dict(),
        "age_override": age_override,
        "index": {
            "seed": dict(seed_spec),
            "agents": index_records,
            "departure_epoch": departure_epoch,
            "first_secondary_shed_epoch": first_secondary_shed,
        },
        "acquisitions": {
            "total": len(events),
            "aboard_window": len(aboard),
            "aboard_window_clean": len(aboard_clean),
            "by_day": {str(k): by_day[k] for k in sorted(by_day)},
            "route_split_all": _route_split(events),
            "route_split_aboard": _route_split(aboard),
            "role_split_aboard": _role_split(aboard),
            "ring_share_aboard": _quantiles(ring_share),
        },
        "infected_total": sum(
            1 for aid in records if aid not in seeded_ids
        ),
        # Epoch-resolution infection map for the paired-age diff.
        "infections_by_epoch": {
            str(aid): int(records[aid].get("infection_epoch") or 0)
            for aid in sorted(records)
            if aid not in seeded_ids
        },
    }


def _diff_age_pair(base: dict[str, Any], other: dict[str, Any]) -> dict[str, Any]:
    """Bit-level outcome diff between two age arms on the same seed."""
    b = base["infections_by_epoch"]
    o = other["infections_by_epoch"]
    shared = set(b) & set(o)
    moved = {str(a): [b[a], o[a]] for a in shared if b[a] != o[a]}
    return {
        "infected_base": len(b),
        "infected_other": len(o),
        "only_base": sorted(set(b) - set(o)),
        "only_other": sorted(set(o) - set(b)),
        "epoch_moved": moved,
        "identical": not moved and set(b) == set(o),
    }


def main() -> None:  # pragma: no cover - CLI driver, exercised by hand
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--design",
        default="picard_framework/runs/covid_sero_channel_v1_design.json",
        help="design file path relative to the repo root",
    )
    parser.add_argument("--arm", default="D0_declared")
    parser.add_argument("--theta", type=float, default=4.22e10)
    parser.add_argument(
        "--seeds", default="20200205,20200206",
        help="comma-separated seed integers (design seeds are seed_base+i)",
    )
    parser.add_argument(
        "--epochs", type=int, default=288,
        help="voyage length; the burn is over by day ~8 (default 288 = 12 d)",
    )
    parser.add_argument(
        "--age-pair", type=float, default=None,
        help="re-run each seed with the seed's infection_age_days rewritten",
    )
    parser.add_argument(
        "--seed-patch", default=None,
        help=(
            "JSON object applied to the explicit seed before running "
            "(null values pop the key; e.g. "
            '\'{"departure_day": 0.0}\' removes the index at embarkation, '
            '\'{"onset_day": null, "departure_day": null, '
            '"infection_age_days": 0.0}\' is a just-infected index)'
        ),
    )
    parser.add_argument("--out", default=None, help="write JSON results here")
    args = parser.parse_args()

    repo_root = repo_root_of(__file__)
    design, _ = load_declared_cells(repo_root, args.design)
    seeds = {int(s) for s in args.seeds.split(",")}
    cells = [
        c for c in enumerate_cells(design)
        if c.arm_id == args.arm
        and c.seed in seeds
        and float(c.theta) == float(args.theta)
    ]
    if not cells:
        raise SystemExit(
            f"no cells match arm={args.arm} theta={args.theta} "
            f"seeds={sorted(seeds)}",
        )
    seed_patch = (
        json.loads(args.seed_patch) if args.seed_patch is not None else None
    )

    results = []
    for cell in cells:
        base = analyse_seed(
            design, cell, num_epochs=args.epochs, repo_root=repo_root,
            seed_patch=seed_patch,
        )
        entry = {"base": base}
        if args.age_pair is not None:
            other = analyse_seed(
                design, cell, num_epochs=args.epochs, repo_root=repo_root,
                age_override=args.age_pair,
            )
            entry["age_pair"] = {
                "age": float(args.age_pair),
                "diff": _diff_age_pair(base, other),
            }
        results.append(entry)

    aboard = [e["base"]["acquisitions"]["aboard_window"] for e in results]
    clean = [
        e["base"]["acquisitions"]["aboard_window_clean"] for e in results
    ]
    readout = {
        "design": args.design,
        "arm": args.arm,
        "theta": float(args.theta),
        "epochs": args.epochs,
        "aboard_window_acquisitions": _quantiles(aboard),
        "aboard_window_clean": _quantiles(clean),
        "cells": results,
    }
    text = json.dumps(readout, indent=1, default=str)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
    print(text)


if __name__ == "__main__":
    main()
