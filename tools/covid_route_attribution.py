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
import math
import os
import sys
import zlib
from collections import Counter
from typing import Any

import numpy as np

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


def cabin_compartment_key(agent: Any) -> str | None:
    """The agent's stateroom air unit, keyed as the engine keys it.

    ``{home_zone}::cabin{min(member ids)}``; agents with no cabin mates
    share no stateroom and get none.
    """
    mates = getattr(agent, "cabin_mate_ids", None) or set()
    if not mates or not getattr(agent, "home_zone", None):
        return None
    label = min(set(mates) | {agent.agent_id})
    return f"{agent.home_zone}::cabin{label}"


class CabinPairChallengeLedger:
    """Per-pair cumulative challenge on cabin-mate pairs (CABIN-OCC-01).

    Tally the compartment-channel dose each cabin-mate pair exchanges —
    droplet pool/plume/addback, contact, HVAC delivery, emesis and flush
    aerosol — keyed by the pair's stateroom air unit. Per-pair lambda is
    exact: the hazard is linear in dose, so susceptibility x summed
    compartment dose is the lambda the engine drew against. The implied
    pair attack rate ``1 - exp(-lambda)`` sits beside the observed
    conversion flag; confined-cabinmate attack rates are the held-out
    check on this table, never a fitting target.
    """

    CHANNELS = ("pool", "plume", "contact", "hvac", "emesis", "flush")

    def __init__(self) -> None:
        # (member ids tuple, target id) -> {pathogen: {channel: dose}}
        self.directed_dose: dict[tuple[tuple[int, ...], int], dict[str, Counter]] = {}
        self.shared_epochs: Counter = Counter()
        self.confined_epochs: Counter = Counter()
        self.confined_first: dict[tuple[int, ...], int] = {}
        self.confined_last: dict[tuple[int, ...], int] = {}
        self._unit_members: dict[str, frozenset[int]] | None = None
        self._agent_unit: dict[int, str] | None = None

    def _pair_map(self, sim: Any) -> None:
        unit_members: dict[str, set[int]] = {}
        agent_unit: dict[int, str] = {}
        for agent in sim.engine.agents:
            key = cabin_compartment_key(agent)
            if key is None:
                continue
            unit_members.setdefault(key, set()).add(agent.agent_id)
            agent_unit[agent.agent_id] = key
        self._unit_members = {
            k: frozenset(v) for k, v in unit_members.items() if len(v) >= 2
        }
        self._agent_unit = agent_unit

    def observe(self, sim: Any, work: Any) -> None:
        if self._unit_members is None:
            self._pair_map(sim)
        unit_members = self._unit_members or {}
        quarantined = getattr(sim.tx_core, "_quarantined_ids", set())
        epoch = int(getattr(work, "epoch", getattr(sim, "_epoch", 0)))
        for members in unit_members.values():
            if members <= quarantined:
                key = tuple(sorted(members))
                self.confined_epochs[key] += 1
                self.confined_first.setdefault(key, epoch)
                self.confined_last[key] = epoch
        matrix = getattr(work, "tracing_matrix", None)
        if matrix is not None:
            self._tally_exposure_records(matrix, unit_members)

    def _tally_exposure_records(
        self,
        matrix: Any,
        unit_members: dict[str, frozenset[int]],
    ) -> None:
        records = (
            (matrix.droplet_exposures, "pool", "air_unit"),
            (matrix.shared_room_exposures, "contact", "compartment"),
            (matrix.hvac_downstream_exposures, "hvac", "air_unit"),
            (matrix.emesis_aerosol_exposures, "emesis", "target_zone"),
            (matrix.flush_aerosol_exposures, "flush", "target_zone"),
        )
        seen_shared: set[tuple[int, ...]] = set()
        for rows, channel, unit_field in records:
            for rec in rows:
                unit = rec.get(unit_field)
                members = unit_members.get(unit) if unit else None
                if members is None:
                    continue
                target = int(rec["target_id"])
                if target not in members:
                    continue
                dose = float(rec.get("dose") or 0.0)
                if dose <= 0.0:
                    continue
                key = tuple(sorted(members))
                by_pathogen = self.directed_dose.setdefault(
                    (key, target), {},
                ).setdefault(str(rec.get("pathogen_id") or ""), Counter())
                if channel == "pool":
                    plume = float(rec.get("near_field_dose") or 0.0)
                    by_pathogen["plume"] += plume
                    dose -= plume
                by_pathogen[channel] += dose
                seen_shared.add(key)
        for key in seen_shared:
            self.shared_epochs[key] += 1


def cabin_pair_challenge_table(
    ledger: CabinPairChallengeLedger,
    sim: Any,
) -> dict[str, Any]:
    """Per-pair lambda, implied SAR, and observed mate-case conversion.

    ``directed`` rows read target <- cabin: the target's summed
    compartment-channel dose x its persistent susceptibility draw is the
    hazard the engine drew against while it shared the stateroom.
    ``observed_mate_case_attack`` is the descriptive analogue of the
    confined-cabinmate attack rate — among pairs where a member was
    infected and cabin dose was exchanged, the share of the other
    members infected (any source). It is a held-out readout, not a fit.
    """
    agents = _agents_by_id(sim)
    profiles = getattr(sim.tx_core, "pathogen_profiles", {})
    resolver = _SusceptibilityResolver(
        seed=int(getattr(sim.run_spec, "random_seed", 0) or 0),
        profiles=profiles,
    )
    rows = _challenge_rows(ledger, agents, resolver)
    lambdas = [r["lambda"] for r in rows]
    mate = _mate_attack_counts(ledger, agents)
    confined_rows = [r for r in rows if r["confined_epochs"] > 0]
    # Observed cabinmate secondary attack among pairs where a member was
    # infected (index excluded). The confined slice is the held-out
    # analogue of Pluciński 2020 / Wikswo 2011 / Chimonas 2008.
    return {
        "pairs_observed": mate["pairs_observed"],
        "directed_rows": len(rows),
        "lambda_quantiles": _quantiles(lambdas),
        "lambda_confined_quantiles": _quantiles(
            [r["lambda"] for r in confined_rows],
        ),
        "implied_sar_confined_median": (
            _quantiles([r["implied_sar"] for r in confined_rows]).get("median")
        ),
        "observed_mate_case_attack": mate["observed_mate_case_attack"],
        "observed_mate_case_attack_confined": (
            mate["observed_mate_case_attack_confined"]
        ),
        "mate_index_pairs": mate["mate_index_pairs"],
        "mate_secondaries": mate["mate_secondaries"],
        "mate_slots": mate["mate_slots"],
        "confined_index_pairs": mate["confined_index_pairs"],
        "confined_secondaries": mate["confined_secondaries"],
        "confined_slots": mate["confined_slots"],
        "rows": rows,
    }


class _SusceptibilityResolver:
    """Persistent frailty lookup with counterfactual fallback draws.

    Counterfactual frailty for hosts whose engine challenge never fired
    (e.g. every dose sub-copy) is drawn on a labelled separate stream keyed
    by (run seed, agent, pathogen), never from the engine's generator —
    the per_host_dose_challenge convention for never-challenged hosts.
    """

    def __init__(self, seed: int, profiles: dict[str, Any]) -> None:
        self.seed = seed
        self.profiles = profiles
        self._draws: dict[tuple[int, str], float] = {}

    def susceptibility(self, agent: Any, pid: str) -> tuple[float, bool]:
        drawn = agent.dose_response_susceptibility.get(pid) if agent else None
        if drawn is not None:
            return float(drawn), True
        key = (int(agent.agent_id), pid)
        if key not in self._draws:
            self._draws[key] = self._counterfactual_draw(key)
        return self._draws[key], False

    def _counterfactual_draw(self, key: tuple[int, str]) -> float:
        dr = self.profiles.get(key[1], {}).get("dose_response", {})
        if dr.get("model", "beta_poisson") == "exponential":
            return float(dr.get("k", 0.01))
        gen = np.random.default_rng(
            (self.seed * 1_000_003 + key[0] * 977
             + zlib.crc32(key[1].encode())) & 0x7FFFFFFF
        )
        return float(
            gen.beta(float(dr.get("alpha", 1.0)),
                     float(dr.get("beta", 1.0)))
        ) * float(dr.get("susceptibility_scale", 1.0))


def _challenge_rows(
    ledger: CabinPairChallengeLedger,
    agents: dict[int, Any],
    resolver: _SusceptibilityResolver,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (members, target), by_pathogen in sorted(ledger.directed_dose.items()):
        agent = agents.get(target)
        for pid, channels in sorted(by_pathogen.items()):
            susc, drawn = resolver.susceptibility(agent, pid)
            lam = susc * sum(channels.values())
            rows.append({
                "cabin_members": list(members),
                "target_id": target,
                "pathogen_id": pid,
                "lambda": lam,
                "susceptibility": "engine_draw" if drawn else "counterfactual",
                "implied_sar": 1.0 - math.exp(-lam),
                "channel_dose": {
                    c: channels.get(c, 0.0)
                    for c in CabinPairChallengeLedger.CHANNELS
                    if channels.get(c, 0.0)
                },
                "confined_epochs": ledger.confined_epochs.get(members, 0),
                "infected": (
                    agent.infections.get(pid) is not None
                    if agent is not None
                    else None
                ),
            })
    return rows


def _pair_first_epochs(
    members: tuple[int, ...],
    pids: set[str],
    agents: dict[int, Any],
) -> dict[int, int]:
    return {
        aid: min(
            agents[aid].infections[pid].get(
                "first_infection_epoch",
                agents[aid].infections[pid]["infection_epoch"],
            )
            for pid in pids if pid in agents[aid].infections
        )
        for aid in members
        if (agents.get(aid) is not None
            and any(pid in agents[aid].infections for pid in pids))
    }


def _confined_window_counts(
    members: tuple[int, ...],
    first_epochs: dict[int, int],
    ledger: CabinPairChallengeLedger,
) -> tuple[int, int]:
    """Confined-window cabinmate attack: earliest member is the index; each
    other member exposed if it entered confinement uninfected, converting
    if its first infection epoch lands inside the confined window. Epoch
    granularity cannot separate an infection acquired on confinement day
    before the order fired."""
    first_confined = ledger.confined_first.get(members)
    if first_confined is None:
        return 0, 0
    last_confined = ledger.confined_last[members]
    index = min(first_epochs, key=first_epochs.get)
    slots = 0
    secondaries = 0
    for aid in members:
        if aid == index:
            continue
        ep = first_epochs.get(aid)
        if ep is not None and ep < first_confined:
            continue
        slots += 1
        if ep is not None and first_confined <= ep <= last_confined:
            secondaries += 1
    return slots, secondaries


def _mate_attack_counts(
    ledger: CabinPairChallengeLedger,
    agents: dict[int, Any],
) -> dict[str, Any]:
    """Household-SAR analogue: (infected - 1)/(members - 1) per pair with a
    member infected with a pair pathogen. A converted mate stays inside
    infected_ids, so members-minus-infected denominators read 0 — unused."""
    pairs_infected: dict[tuple[int, ...], set[int]] = {}
    pair_pathogens: dict[tuple[int, ...], set[str]] = {}
    for (members, _t), by_pathogen in ledger.directed_dose.items():
        pairs_infected.setdefault(members, set())
        pair_pathogens.setdefault(members, set()).update(by_pathogen)
    for members in pairs_infected:
        for aid in members:
            agent = agents.get(aid)
            if agent is not None and agent.infections:
                pairs_infected[members].add(aid)
    mate_index_pairs = mate_secondaries = mate_slots = 0
    confined_index_pairs = confined_secondaries = confined_slots = 0
    for members, infected_ids in pairs_infected.items():
        if not infected_ids:
            continue
        first_epochs = _pair_first_epochs(
            members, pair_pathogens.get(members, set()), agents,
        )
        if not first_epochs:
            continue
        mate_index_pairs += 1
        mate_secondaries += len(first_epochs) - 1
        mate_slots += len(members) - 1
        slots, secondaries = _confined_window_counts(
            members, first_epochs, ledger,
        )
        if slots or (members in ledger.confined_first):
            confined_index_pairs += 1
        confined_slots += slots
        confined_secondaries += secondaries
    return {
        "pairs_observed": len(pairs_infected),
        "mate_index_pairs": mate_index_pairs,
        "mate_secondaries": mate_secondaries,
        "mate_slots": mate_slots,
        "confined_index_pairs": confined_index_pairs,
        "confined_secondaries": confined_secondaries,
        "confined_slots": confined_slots,
        "observed_mate_case_attack": (
            mate_secondaries / mate_slots if mate_slots else None
        ),
        "observed_mate_case_attack_confined": (
            confined_secondaries / confined_slots if confined_slots else None
        ),
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


def _funnel_rung(
    agent: Any,
    pathogen_id: str,
    seeded: set[int],
    confirmed: set[int],
    eligibility: list[float],
    states: list[str],
) -> dict[str, Any] | None:
    """One host's place in the truth→recorded funnel, or None if uninfected."""
    if agent.agent_id in seeded:
        return None
    inf = agent.infections.get(pathogen_id)
    if inf is None:
        return None
    severity = str(inf.get("symptom_severity") or "none")
    # ``illness`` flips to RECOVERED by voyage end, so the datable-course
    # rung is read off severity instead: an eligibility>0 severity means
    # the host had a symptomatic course the channel could ever date.
    is_eligible = bool(
        eligibility
        and severity in states
        and eligibility[states.index(severity)] > 0.0
    ) or not eligibility
    return {
        "severity": severity,
        "symptomatic": inf.get("illness") == IllnessStatus.SYMPTOMATIC,
        "eligible": is_eligible,
        "confirmed": is_eligible and agent.agent_id in confirmed,
    }


def ascertainment_funnel(
    sim: Any,
    *,
    pathogen_id: str = PATHOGEN_ID,
    record_dating_rate_confirmed: float | None = None,
) -> dict[str, Any]:
    """Truth->recorded funnel for ``pathogen_id`` on one finished simulation.

    Counts every rung the observation channel must pass for a host to get a
    dated onset in ``_onset_observations``: infected (truth), illness
    SYMPTOMATIC, syndrome-eligible severity, lab-confirmed, onset dated.
    ``record_dating_rate_confirmed`` is the published investigation's dated
    share, carried beside the rung it is checked against; callers without a
    record leave it unset.
    """
    syndromic = sim.modalities["syndromic"]
    seeded = _seeded_ids(sim)
    confirmed = {
        aid for (pid, aid) in syndromic._lab_confirmed if pid == pathogen_id
    }
    dated = {
        aid: rec
        for (pid, aid), rec in syndromic._onset_observations.items()
        if pid == pathogen_id
    }
    eligibility = (
        sim.pathogen_profiles[pathogen_id]
        .get("observation_model", {})
        .get("syndrome_case_eligibility_by_severity", [])
    )
    states = (
        sim.pathogen_profiles[pathogen_id]
        .get("severity_model", {})
        .get("states", [])
    )

    infected, symptomatic_now, eligible, confirmed_datable = 0, 0, 0, 0
    severity_all: Counter = Counter()
    severity_eligible_course: Counter = Counter()
    for agent in sim.engine.agents:
        rung = _funnel_rung(
            agent, pathogen_id, seeded, confirmed, eligibility, states,
        )
        if rung is None:
            continue
        infected += 1
        severity_all[rung["severity"]] += 1
        symptomatic_now += int(rung["symptomatic"])
        if not rung["eligible"]:
            continue
        eligible += 1
        severity_eligible_course[rung["severity"]] += 1
        confirmed_datable += int(rung["confirmed"])

    dated_severity = Counter(str(r["symptom_severity"]) for r in dated.values())
    out = {
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
    }
    if record_dating_rate_confirmed is not None:
        # The record dated 197 of ~712 confirmed cases (~0.28 of confirmed,
        # ~0.55 of symptomatic-confirmed) — the funnel's structural gap.
        out["record_dating_rate_confirmed"] = float(record_dating_rate_confirmed)
    return out


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
    pair_ledger = CabinPairChallengeLedger()

    def observer(sim: Any, work: Any) -> None:
        ledger.observe(sim, work)
        near_ledger.observe(sim, work)
        hazard_ledger.observe(sim, work)
        pair_ledger.observe(sim, work)

    sim = run_fit_spec(raw, repo_root=repo_root, epoch_observer=observer)
    _, start, end = _quarantine_window(raw)
    return {
        "cell": cell.as_dict(),
        "quarantine_window_days": [start, end],
        "payload": cell_payload(design, cell, sim, ledger, raw),
        "route_attribution": route_window_tables(sim, ledger, start, end),
        "near_field": near_field_share_table(near_ledger),
        "hazard_rate": hazard_rate_table(hazard_ledger),
        "cabin_pairs": cabin_pair_challenge_table(pair_ledger, sim),
        "ascertainment": ascertainment_funnel(
            sim, record_dating_rate_confirmed=197.0 / 712.0,
        ),
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
        "--thetas", default=None,
        help="comma-separated theta filter; omitted runs every declared theta",
    )
    parser.add_argument(
        "--epochs", type=int, default=None,
        help="truncate the voyage for a smoke run",
    )
    parser.add_argument("--out", default=None, help="write JSON results here")
    args = parser.parse_args()

    repo_root = repo_root_of(__file__)
    design, _ = load_declared_cells(repo_root, args.design)
    seeds = {int(s) for s in args.seeds.split(",")}
    thetas = (
        {float(t) for t in args.thetas.split(",")}
        if args.thetas else None
    )
    cells = [
        c for c in enumerate_cells(design)
        if c.arm_id == args.arm and c.seed in seeds
        and (thetas is None or float(getattr(c, "theta", 0)) in thetas)
    ]
    if not cells:
        raise SystemExit(f"no cells match arm={args.arm} seeds={sorted(seeds)}")

    results = [
        analyse_cell(design, c, num_epochs=args.epochs, repo_root=repo_root)
        for c in cells
    ]
    text = json.dumps(results, indent=1, default=str)
    if args.out:
        out_path = args.out
        if not os.path.isabs(out_path):
            out_path = os.path.join(repo_root, out_path)
        out_path = os.path.realpath(out_path)
        root = os.path.realpath(repo_root) + os.sep
        if not out_path.startswith(root):
            raise SystemExit(f"--out must resolve under the repo root: {args.out}")
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(text)
    print(text)


if __name__ == "__main__":
    main()
