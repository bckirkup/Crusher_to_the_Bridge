"""Timing probe for the covid_quarantine_attribution_v1 truth/ledger gap.

The A0 theta=1e9 seed 20200205 cell measured a contradiction: the syndromic
channel dates 2836 onsets before day 17 while truth counts only 2060
infections before day 16, and the attribution ledger's events cover ~68% of
the during-window truth infections. This tool reruns exactly one cell the way
``run_cell`` does — ``prepare_cell_run_spec`` + ``run_fit_spec`` with a
``QuarantineAttributionLedger`` observer — then dumps, per infected agent, the
truth stamp (``infection_epoch``), the syndromic onset stamps
(``_presentation_onset_epoch``, ``_onset_observations``) and whether a ledger
event exists, so the three candidate clocks can be differenced directly.

It proves, per agent, three separate questions:

* onset_day - infection_day should be the incubation period; a negative value
  means the syndromic onset is dated before the exposure that caused it;
* an infected agent with no ledger event reached ``infections[]`` through a
  path that never emits a ``tx_event`` (shore introductions, seeding
  channels, or any direct ``infect_with_pathogen`` call site);
* a ledger event *earlier* than the stamped ``infection_epoch`` means the
  record was overwritten by a later ``infect_with_pathogen`` (reinfection
  after recovery), so the truth window and the ledger disagree on when the
  agent was infected.

Usage:
    python3 tools/covid_attribution_timing_probe.py
        [--theta 1e9] [--seed 20200205] [--arm A0_declared]
        [--num-epochs N] [--out results/.../timing_probe.json]
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
    _quarantine_window,
    enumerate_cells,
    load_design,
    prepare_cell_run_spec,
)
from picard_framework.covid_theta_fit import PATHOGEN_ID, run_fit_spec

DESIGN_REL = os.path.join(
    "picard_framework", "runs", "covid_quarantine_attribution_v1_design.json",
)


def _find_cell(design, theta: float, seed: int, arm_id: str):
    """The design cell matching the requested axes."""
    matches = [
        c for c in enumerate_cells(design)
        if c.arm_id == arm_id and c.seed == seed and float(c.theta) == theta
    ]
    if not matches:
        raise SystemExit(
            f"no cell for theta={theta} seed={seed} arm={arm_id}",
        )
    return matches[0]


def _window_bucket(day: int, start: int, end: int | None) -> str:
    if day < start:
        return "before"
    if end is None or day <= end:
        return "during"
    return "after"


def _agent_row(
    sim, agent, inf, onset_obs, pres_epoch, ev,
) -> dict[str, Any]:
    """One agent's truth stamp, syndromic stamps and ledger event joined."""
    infection_epoch = int(inf.get("infection_epoch", 0))
    aid = int(agent.agent_id)
    return {
        "agent_id": aid,
        "role": getattr(agent, "role", None),
        "infection_epoch": infection_epoch,
        "infection_day": int(sim.clock.day_index(infection_epoch)),
        "time_infected": inf.get("time_infected"),
        "incubation_days": inf.get("incubation_days"),
        "illness": str(inf.get("illness")),
        "symptom_severity": inf.get("symptom_severity"),
        "onset_time_infected": inf.get("onset_time_infected"),
        "presentation_onset_epoch": (
            None if pres_epoch is None else int(pres_epoch)
        ),
        "onset_day": (
            None if onset_obs is None else int(onset_obs["onset_day"])
        ),
        "recorded": onset_obs is not None,
        "ledger_event_epoch": (
            None if ev is None else int(ev["epoch"])
        ),
        "ledger_event_day": (
            None if ev is None else int(sim.clock.day_index(ev["epoch"]))
        ),
        "ledger_pathway": None if ev is None else ev["pathway"],
    }


def _per_agent_rows(sim, ledger) -> list[dict[str, Any]]:
    """One row per non-seeded COVID-infected agent, all three clocks joined."""
    seeded = set(getattr(sim.engine, "explicit_seed_agent_ids", None) or ())
    syndromic = sim.modalities["syndromic"]
    presentation = getattr(syndromic, "_presentation_onset_epoch", {})
    observations = getattr(syndromic, "_onset_observations", {})
    events_by_target: dict[int, dict] = {}
    for ev in ledger.events:
        events_by_target.setdefault(int(ev["target_agent_id"]), ev)
    return [
        _agent_row(
            sim, agent, agent.infections[PATHOGEN_ID],
            observations.get((PATHOGEN_ID, int(agent.agent_id))),
            presentation.get(int(agent.agent_id)),
            events_by_target.get(int(agent.agent_id)),
        )
        for agent in sim.engine.agents
        if int(agent.agent_id) not in seeded
        and PATHOGEN_ID in agent.infections
    ]


def _summarise(sim, rows, start: int, end: int | None) -> dict[str, Any]:
    """The three readouts: onset-lag histogram, ledger misses, truth windows."""
    lags = [
        r["onset_day"] - r["infection_day"]
        for r in rows if r["onset_day"] is not None
    ]
    lag_hist = dict(sorted(Counter(lags).items()))
    no_event = [r for r in rows if r["ledger_event_epoch"] is None]
    miss_split = Counter(
        (r["role"], _window_bucket(r["infection_day"], start, end))
        for r in no_event
    )
    overwritten = [
        r for r in rows
        if r["ledger_event_epoch"] is not None
        and r["ledger_event_epoch"] < r["infection_epoch"]
    ]
    truth = Counter(
        _window_bucket(r["infection_day"], start, end) for r in rows
    )
    return {
        "n_infected": len(rows),
        "epochs_per_day": (
            sim.clock.epochs_for_days(1)
            if hasattr(sim.clock, "epochs_for_days") else None
        ),
        "onset_lag_hist_days": lag_hist,
        "onset_lag_negative": sum(1 for x in lags if x < 0),
        "infected_without_ledger_event": len(no_event),
        "no_event_by_role_window": {
            f"{role}/{bucket}": n
            for (role, bucket), n in sorted(
                miss_split.items(), key=lambda kv: (str(kv[0][0]), kv[0][1]),
            )
        },
        "ledger_epoch_before_infection_epoch": len(overwritten),
        "truth_windows": {
            "before": truth.get("before", 0),
            "during": truth.get("during", 0),
            "after": truth.get("after", 0),
        },
    }


def _write_dump(out_arg: str, summary: dict, rows: list[dict]) -> str:
    """Write the per-agent dump at the repo root; bare filenames only."""
    if os.path.basename(out_arg) != out_arg:
        raise SystemExit(f"--out {out_arg!r} must be a bare filename")
    repo_root = os.path.realpath(
        os.path.join(os.path.dirname(__file__), ".."),
    )
    path = os.path.join(repo_root, out_arg)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"summary": summary, "agents": rows}, fh, indent=1)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theta", type=float, default=1e9)
    parser.add_argument("--seed", type=int, default=20200205)
    parser.add_argument("--arm", default="A0_declared")
    parser.add_argument(
        "--num-epochs", type=int, default=None,
        help="truncate the horizon for a quick read (432 = 18 days)",
    )
    parser.add_argument("--design", default=DESIGN_REL)
    parser.add_argument(
        "--out", default=None,
        help="optional bare filename for the per-agent JSON dump "
        "(written at the repository root)",
    )
    args = parser.parse_args(argv)

    design = load_design(args.design)
    cell = _find_cell(design, args.theta, args.seed, args.arm)
    raw = prepare_cell_run_spec(
        design, cell, num_epochs=args.num_epochs,
    )
    _, start, end = _quarantine_window(raw)
    ledger = QuarantineAttributionLedger()
    sim = run_fit_spec(raw, epoch_observer=ledger.observe)
    rows = _per_agent_rows(sim, ledger)
    summary = _summarise(sim, rows, start, end)
    summary.update({
        "theta": cell.theta, "seed": cell.seed, "arm_id": cell.arm_id,
        "num_epochs": args.num_epochs,
        "quarantine_window_days": [start, end],
        "ledger_events": len(ledger.events),
    })
    print(json.dumps(summary, indent=2, sort_keys=True))
    if args.out:
        print(f"per-agent dump: {_write_dump(args.out, summary, rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
