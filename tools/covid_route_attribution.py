"""Whole-voyage route attribution + ascertainment funnel for a covid cell.

The boarding-screen cell payload only tallies routes for infections inside
the quarantine window — yet ~95% of the recorded mass lands before it. This
tool runs one declared cell end to end and reports, on the truth side, every
non-seeded infection's dominant acquired-dose route, zone class, role and
window (before / during / after the scheduled quarantine), and on the
recorded side the ascertainment funnel from infection to a dated onset:

    infected -> symptomatic -> eligible severity -> lab-confirmed -> dated

plus the per-severity histogram of dated onsets, and the per-challenge
Poisson rate lambda = susceptibility x epoch dose the engine drew against
(the quantity whose position vs 1 decides whether infection is
dose-limited or saturated). The funnel's last gap is
what the published investigation's dated-onset subset (covid.T1: 197 dated
of ~712 confirmed) cannot share — the model dates every confirmed,
symptomatic, eligible case while the record dated roughly a quarter of the
confirmed cases, so the funnel quantifies the channel's over-inclusion.

Usage:
    python3 tools/covid_route_attribution.py \
        --design picard_framework/runs/covid_plume_dose_assay_v1_design.json \
        --arm D0_declared --seeds 20200205,20200217 \
        [--epochs N] [--out out.json]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engines.infection_dynamics_bridge import IllnessStatus
from picard_framework.covid_boarding_screen import (
    PATHOGEN_ID,
    QuarantineAttributionLedger,
    _during_zone_class,
    _quarantine_window,
    _zone_class_lookup,
    cell_payload,
    enumerate_cells,
    prepare_cell_run_spec,
)
from picard_framework.covid_theta_fit import run_fit_spec
from tools.covid_assay_smoke import load_declared_cells, repo_root_of

WINDOWS = ("before", "during", "after")


class NearFieldShareLedger:
    """Per-target droplet dose split into ring / cabin-mate addback / pool.

    ``matrix.droplet_exposures`` rounds every dose to 4 decimals and the
    per-epoch droplet drip underflows to 0.0, so the split is tallied by
    wrapping the engine's unrounded dose functions on first ``observe``:

    - ``_near_field_droplet_dose`` → the near share's plume dose (fixed
      cabin/table pairs + the sampled proximity ring).
    - ``_cabin_mate_droplet_addback`` → the confinement channel inside a
      stateroom's pool.
    - ``_accumulate(…, "droplet", …)`` → the total credited droplet dose;
      the residual is the far-field pool.

    Infected agents leave ``_get_susceptible`` and stop accruing droplet
    dose, so lifetime tallies already end at the infection epoch.
    """

    def __init__(self) -> None:
        self.infection_epoch: dict[int, int] = {}
        self.total: Counter = Counter()
        self.near: Counter = Counter()
        self.addback: Counter = Counter()
        self._installed = False

    def _install(self, tx_core: Any) -> None:
        orig_near = tx_core._near_field_droplet_dose
        orig_addback = tx_core._cabin_mate_droplet_addback
        orig_accumulate = tx_core._accumulate
        near, addback, total = self.near, self.addback, self.total

        def near_wrapped(zone_name: str, target: Any, *a: Any, **kw: Any) -> float:
            d = orig_near(zone_name, target, *a, **kw)
            if d > 0.0:
                near[target.agent_id] += d
            return d

        def addback_wrapped(target: Any, *a: Any, **kw: Any) -> float:
            d = orig_addback(target, *a, **kw)
            if d > 0.0:
                addback[target.agent_id] += d
            return d

        def accumulate_wrapped(
            target_id: int, pathway: str, dose: float, *a: Any, **kw: Any
        ) -> float:
            if pathway == "droplet" and dose > 0.0:
                total[target_id] += dose
            return orig_accumulate(target_id, pathway, dose, *a, **kw)

        tx_core._near_field_droplet_dose = near_wrapped
        tx_core._cabin_mate_droplet_addback = addback_wrapped
        tx_core._accumulate = accumulate_wrapped
        self._installed = True

    def observe(self, sim: Any, work: Any) -> None:
        if not self._installed:
            self._install(sim.tx_core)
        for ev in work.tx_events:
            t = int(ev.target_agent_id)
            if t not in self.infection_epoch:
                self.infection_epoch[t] = int(ev.epoch)


class HazardRateLedger:
    """Per-challenge hazard rate lambda = susceptibility x epoch dose.

    The engine's single-hit hazard is ``p = 1 - exp(-susceptibility *
    effective_dose)``: lambda is the Poisson rate in that exponent, the
    expected hit count of one challenged host-epoch. ``_dose_response_hazard``
    is called exactly once per challenged host-epoch, so wrapping it tallies
    the lambda the engine drew against. An infected agent's last recorded
    lambda is the challenge that infected it — infected agents leave
    ``_get_susceptible`` and are never challenged again.
    """

    def __init__(self) -> None:
        self.lambdas: list[float] = []
        self.last: dict[int, float] = {}
        self.infecting: dict[int, float] = {}
        self._installed = False

    def _install(self, tx_core: Any) -> None:
        orig = tx_core._dose_response_hazard
        lambdas, last = self.lambdas, self.last

        def hazard_wrapped(
            agent: Any, pathogen_id: str, effective_dose: float,
            *a: Any, **kw: Any,
        ) -> float:
            p = orig(agent, pathogen_id, effective_dose, *a, **kw)
            susc = agent.dose_response_susceptibility.get(pathogen_id)
            lam = (susc if susc is not None else 0.0) * effective_dose
            lambdas.append(lam)
            last[agent.agent_id] = lam
            return p

        tx_core._dose_response_hazard = hazard_wrapped
        self._installed = True

    def observe(self, sim: Any, work: Any) -> None:
        if not self._installed:
            self._install(sim.tx_core)
        for ev in work.tx_events:
            t = int(ev.target_agent_id)
            if t not in self.infecting and t in self.last:
                self.infecting[t] = self.last[t]


def _quantiles(vals: list[float]) -> dict[str, Any]:
    n = len(vals)
    if not n:
        return {
            "n": 0, "mean": None, "q05": None, "q25": None,
            "median": None, "q75": None, "q95": None,
            "share_ge_1": None, "share_ge_0p1": None, "share_lt_0p01": None,
        }
    s = sorted(vals)

    def q(p: float) -> float:
        return s[min(int(p * n), n - 1)]

    return {
        "n": n,
        "mean": sum(s) / n,
        "q05": q(0.05),
        "q25": q(0.25),
        "median": q(0.5),
        "q75": q(0.75),
        "q95": q(0.95),
        "share_ge_1": sum(1 for v in s if v >= 1.0) / n,
        "share_ge_0p1": sum(1 for v in s if v >= 0.1) / n,
        "share_lt_0p01": sum(1 for v in s if v < 0.01) / n,
    }


def hazard_rate_table(ledger: HazardRateLedger) -> dict[str, Any]:
    """Lambda distribution over challenged host-epochs and infecting hits.

    ``lambda_all`` is the Poisson rate of every host-epoch the engine drew
    against; ``lambda_infecting`` the rate of the challenges that infected.
    Where the mass sits vs lambda = 1 (certain infection per challenge) is
    the saturation readout the flat dose/reach assays predicted.
    """
    return {
        "lambda_all": _quantiles(ledger.lambdas),
        "lambda_infecting": _quantiles(list(ledger.infecting.values())),
    }


def window_of(day: int, start: int, end: int | None) -> str:
    """Which quarantine window an infection day falls in."""
    if day < start:
        return "before"
    if end is None or day <= end:
        return "during"
    return "after"


def _agents_by_id(sim: Any) -> dict[int, Any]:
    return {a.agent_id: a for a in sim.engine.agents}


def _seeded_ids(sim: Any) -> set[int]:
    return set(getattr(sim.engine, "explicit_seed_agent_ids", None) or ())


def near_field_share_table(ledger: NearFieldShareLedger) -> dict[str, Any]:
    """Ring-vs-pool droplet dose decomposition among infected agents.

    ``ring_share`` = (near-field plume + cabin-mate addback) / total
    droplet dose; the residual is the far-field pool.
    """
    ring_share: dict[int, float] = {}
    for t in ledger.infection_epoch:
        tot = ledger.total.get(t, 0.0)
        if tot > 0.0:
            ring_share[t] = (
                ledger.near.get(t, 0.0) + ledger.addback.get(t, 0.0)
            ) / tot
    total_all = sum(ledger.total.get(t, 0.0) for t in ring_share)
    near_all = sum(ledger.near.get(t, 0.0) for t in ring_share)
    addback_all = sum(ledger.addback.get(t, 0.0) for t in ring_share)
    vals = sorted(ring_share.values())
    n = len(vals)
    return {
        "infected_with_droplet_dose": n,
        "dose_weighted_ring_share": (
            (near_all + addback_all) / total_all if total_all > 0.0 else None
        ),
        "dose_weighted_near_field_share": (
            near_all / total_all if total_all > 0.0 else None
        ),
        "dose_weighted_addback_share": (
            addback_all / total_all if total_all > 0.0 else None
        ),
        "ring_share_median": vals[n // 2] if n else None,
        "ring_share_q05": vals[int(0.05 * n)] if n else None,
        "ring_share_q95": vals[min(int(0.95 * n), n - 1)] if n else None,
        "share_majority_ring_dose": (
            sum(1 for v in vals if v > 0.5) / n if n else None
        ),
    }


def route_window_tables(
    sim: Any,
    ledger: QuarantineAttributionLedger,
    start: int,
    end: int | None,
) -> dict[str, Any]:
    """Every ledger event tallied route x window and zone-class x window."""
    dining_types = _zone_class_lookup(sim)
    agents_by_id = _agents_by_id(sim)
    route = {w: Counter() for w in WINDOWS}
    zone = {w: Counter() for w in WINDOWS}
    role = {w: Counter() for w in WINDOWS}
    for ev in ledger.events:
        w = window_of(sim.clock.day_index(int(ev["epoch"])), start, end)
        route[w][ev["pathway"]] += 1
        zone[w][_during_zone_class(sim, dining_types, agents_by_id, ev)] += 1
        agent = agents_by_id.get(ev["target_agent_id"])
        role[w][getattr(agent, "role", "unknown")] += 1
    return {
        "route_by_window": {w: dict(route[w]) for w in WINDOWS},
        "zone_by_window": {w: dict(zone[w]) for w in WINDOWS},
        "role_by_window": {w: dict(role[w]) for w in WINDOWS},
        "events": len(ledger.events),
    }


def ascertainment_funnel(sim: Any) -> dict[str, Any]:
    """Truth->recorded funnel for PATHOGEN_ID on one finished simulation.

    Counts every rung the observation channel must pass for a host to get a
    dated onset in ``_onset_observations``: infected (truth), illness
    SYMPTOMATIC, syndrome-eligible severity, lab-confirmed, onset dated.
    """
    syndromic = sim.modalities["syndromic"]
    seeded = _seeded_ids(sim)
    confirmed = {
        aid for (pid, aid) in syndromic._lab_confirmed if pid == PATHOGEN_ID
    }
    dated = {
        aid: rec
        for (pid, aid), rec in syndromic._onset_observations.items()
        if pid == PATHOGEN_ID
    }
    eligibility = (
        sim.pathogen_profiles[PATHOGEN_ID]
        .get("observation_model", {})
        .get("syndrome_case_eligibility_by_severity", [])
    )
    states = (
        sim.pathogen_profiles[PATHOGEN_ID]
        .get("severity_model", {})
        .get("states", [])
    )

    infected = symptomatic_now = eligible = 0
    severity_all: Counter = Counter()
    severity_eligible_course: Counter = Counter()
    confirmed_datable = 0
    for agent in sim.engine.agents:
        if agent.agent_id in seeded:
            continue
        inf = agent.infections.get(PATHOGEN_ID)
        if inf is None:
            continue
        infected += 1
        severity = str(inf.get("symptom_severity") or "none")
        severity_all[severity] += 1
        if inf.get("illness") == IllnessStatus.SYMPTOMATIC:
            symptomatic_now += 1
        # ``illness`` flips to RECOVERED by voyage end, so the datable-course
        # rung is read off severity instead: an eligibility>0 severity means
        # the host had a symptomatic course the channel could ever date.
        is_eligible = bool(
            eligibility
            and severity in states
            and eligibility[states.index(severity)] > 0.0
        ) or not eligibility
        if not is_eligible:
            continue
        eligible += 1
        severity_eligible_course[severity] += 1
        if agent.agent_id in confirmed:
            confirmed_datable += 1

    dated_severity = Counter(str(r["symptom_severity"]) for r in dated.values())
    return {
        "infected_truth": infected,
        "symptomatic_at_end": symptomatic_now,
        "severity_of_infected": dict(severity_all),
        "eligible_severity_course": eligible,
        "severity_of_datable_course": dict(severity_eligible_course),
        "lab_confirmed_total": len(confirmed),
        "confirmed_datable": confirmed_datable,
        "dated_onsets": len(dated),
        "dated_by_severity": dict(dated_severity),
        "dating_rate_confirmed": (
            len(dated) / len(confirmed) if confirmed else None
        ),
        "dating_rate_confirmed_datable": (
            len(dated) / confirmed_datable
            if confirmed_datable
            else None
        ),
        # The record dated 197 of ~712 confirmed cases (~0.28 of confirmed,
        # ~0.55 of symptomatic-confirmed) — the funnel's structural gap.
        "record_dating_rate_confirmed": 197.0 / 712.0,
    }


def analyse_cell(
    design: Any,
    cell: Any,
    *,
    num_epochs: int | None = None,
    repo_root: str,
) -> dict[str, Any]:
    """Run one cell and return payload + route tables + funnel."""
    raw = prepare_cell_run_spec(
        design, cell, num_epochs=num_epochs, repo_root=repo_root,
    )
    ledger = QuarantineAttributionLedger()
    near_ledger = NearFieldShareLedger()
    hazard_ledger = HazardRateLedger()

    def observer(sim: Any, work: Any) -> None:
        ledger.observe(sim, work)
        near_ledger.observe(sim, work)
        hazard_ledger.observe(sim, work)

    sim = run_fit_spec(raw, repo_root=repo_root, epoch_observer=observer)
    _, start, end = _quarantine_window(raw)
    return {
        "cell": cell.as_dict(),
        "quarantine_window_days": [start, end],
        "payload": cell_payload(design, cell, sim, ledger, raw),
        "route_attribution": route_window_tables(sim, ledger, start, end),
        "near_field": near_field_share_table(near_ledger),
        "hazard_rate": hazard_rate_table(hazard_ledger),
        "ascertainment": ascertainment_funnel(sim),
    }


def main() -> None:  # pragma: no cover - CLI driver, exercised by hand
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--design",
        default="picard_framework/runs/covid_plume_dose_assay_v1_design.json",
        help="design file path relative to the repo root",
    )
    parser.add_argument("--arm", default="D0_declared")
    parser.add_argument("--seeds", default="20200205")
    parser.add_argument(
        "--epochs", type=int, default=None,
        help="truncate the voyage for a smoke run",
    )
    parser.add_argument("--out", default=None, help="write JSON results here")
    args = parser.parse_args()

    repo_root = repo_root_of(__file__)
    design, _ = load_declared_cells(repo_root, args.design)
    seeds = {int(s) for s in args.seeds.split(",")}
    cells = [
        c for c in enumerate_cells(design)
        if c.arm_id == args.arm and c.seed in seeds
    ]
    if not cells:
        raise SystemExit(f"no cells match arm={args.arm} seeds={sorted(seeds)}")

    results = [
        analyse_cell(design, c, num_epochs=args.epochs, repo_root=repo_root)
        for c in cells
    ]
    text = json.dumps(results, indent=1, default=str)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
    print(text)


if __name__ == "__main__":
    main()
