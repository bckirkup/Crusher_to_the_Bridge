#!/usr/bin/env python3
"""CREW-MESS-01 berth attribution: decompose during-window crew acquisitions.

The Batch cell payloads carry zone-class tallies only — no infector ids —
so the co-berth question needs a local re-run of the same (arm, seed) cell
keeping the finished sim. For every during-window acquisition of a crew
target this script records:

* ``zone_class`` — the same cabin/corridor/crew_mess/galley/other split the
  campaign readout applies (``_during_zone_class``);
* ``confined`` — whether the target was quarantined at event time (the
  ledger's per-event flag, so confinement timing is exact);
* ``co_berth`` — whether at least one of the target's ``cabin_mate_ids``
  carried a strictly earlier infection epoch (a candidate berth-mate
  source existed; this is a *sufficient-cause* bound, not a proven
  infector — the run carries no strain tracking);
* ``at_work_zone`` — whether the acquisition zone equals the target's
  posted ``work_zone``;
* ``pathway`` — the dominant acquired-dose route.

Crew-in-cabin events split into ``co_berth`` (a cabin-mate had already
infected — household-style pair transmission, including confined mates
carried by working ones) and ``corridor_pool`` (no prior-infected mate —
the corridor-level dose: other berths' compartment share, zone pool,
fomites). Output is per-seed tallies plus pooled, written as JSON.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from picard_framework.covid_boarding_screen import (  # noqa: E402
    QuarantineAttributionLedger,
    _during_zone_class,
    _quarantine_window,
    _zone_class_lookup,
    enumerate_cells,
    load_design,
    prepare_cell_run_spec,
)
from picard_framework.covid_theta_fit import (  # noqa: E402
    PATHOGEN_ID,
    run_fit_spec,
)


def _match_cell(design: Any, theta: float, arm_id: str, seed: int) -> Any:
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


def run_seed(design: Any, theta: float, arm_id: str, seed: int) -> dict[str, Any]:
    """Re-run one cell and decompose its during-window crew events."""
    cell = _match_cell(design, theta, arm_id, seed)
    raw = prepare_cell_run_spec(design, cell, repo_root=str(_REPO_ROOT))
    ledger = QuarantineAttributionLedger()
    sim = run_fit_spec(
        raw, repo_root=str(_REPO_ROOT), epoch_observer=ledger.observe,
    )
    _entry, start, end = _quarantine_window(raw)

    agents_by_id = {a.agent_id: a for a in sim.engine.agents}
    infection_epoch = {
        a.agent_id: int(a.infections[PATHOGEN_ID]["infection_epoch"])
        for a in sim.engine.agents
        if PATHOGEN_ID in a.infections
    }
    dining_types = _zone_class_lookup(sim)

    events: list[dict[str, Any]] = []
    for ev in ledger.events:
        day = sim.clock.day_index(int(ev["epoch"]))
        if day < start or (end is not None and day > end):
            continue
        target = agents_by_id.get(ev["target_agent_id"])
        if target is None or getattr(target, "role", None) != "crew":
            continue
        mates = list(getattr(target, "cabin_mate_ids", None) or ())
        prior_mates = [
            m for m in mates
            if (m in infection_epoch
                and infection_epoch[m] < int(ev["epoch"]))
        ]
        mate_days = [
            sim.clock.day_index(infection_epoch[m]) for m in prior_mates
        ]
        events.append({
            "day": day,
            "zone": ev["zone"],
            "zone_class": _during_zone_class(
                sim, dining_types, agents_by_id, ev,
            ),
            "pathway": ev["pathway"],
            "target_agent_id": int(ev["target_agent_id"]),
            "confined": bool(ev["confined"]),
            "home_zone": getattr(target, "home_zone", None),
            "work_zone": getattr(target, "work_zone", None),
            "at_work_zone": ev["zone"] == getattr(target, "work_zone", None),
            "co_berth": bool(prior_mates),
            "prior_mates": prior_mates,
            "prior_mate_infection_days": sorted(mate_days),
            "mate_infected_before_window": any(d < start for d in mate_days),
        })

    tally = Counter(
        (
            e["zone_class"],
            "confined" if e["confined"] else "working",
            "co_berth" if e["co_berth"] else "no_prior_mate",
        )
        for e in events
    )
    by_route = Counter(e["pathway"] for e in events)
    return {
        "seed": seed,
        "arm_id": arm_id,
        "theta": theta,
        "window_days": [start, end],
        "activated": ledger.activated,
        "crew_during_events": len(events),
        "tally": {
            "|".join(key): n for key, n in sorted(tally.items())
        },
        "by_route": dict(sorted(by_route.items())),
        "events": events,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--design", required=True,
        help="repo-relative boarding-screen design JSON",
    )
    parser.add_argument("--theta", required=True, type=float)
    parser.add_argument("--arm", required=True, help="design arm_id")
    parser.add_argument(
        "--seed", required=True, type=int,
        help="one seed per invocation (run seeds as parallel processes)",
    )
    parser.add_argument("--out", required=True, help="output JSON path")
    args = parser.parse_args(argv)

    design = load_design(str(_REPO_ROOT / args.design))
    result = run_seed(design, args.theta, args.arm, args.seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8",
    )
    crew = result["crew_during_events"]
    print(
        f"seed {args.seed}: {crew} during-window crew events; "
        f"tally {result['tally']}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
