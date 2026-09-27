"""COVID-TAKEOFF-ATTR-01: decompose the takeoff burn by route, ring, shedder.

The v12 stage-2 replay cells carry only aggregate counts (onset curve,
infections total) — no route, shedder, or epoch fields — so the burn
cannot be decomposed from the records on S3. This tool reruns one declared
cell of the clause surface with a read-only instrument stack on top of the
``QuarantineAttributionLedger`` and answers, per non-seeded infection on a
takeoff seed:

- which channel delivered the dose, resolved below the engine's "droplet"
  pathway into the declared rings: cabin-mate ring (addback + corridor
  plume + stateroom-compartment pool), dining / meal-table rings (same and
  adjacent tables), the sampled near-field plume (partner-bounded
  proximity set), the venue zone pool, HVAC airborne, and contact;
- which shedders that dose is attributable to (dose-share credit: pool by
  emitted share, near field by weight x emitted, addback by shedding x
  co-presence, contact/HVAC equally over the record's source ids); and
- the geometry of the burn: onsets per shedder, per epoch, per venue, plus
  the reach and footprint distributions that implicate the candidate
  missing mechanism — (a) per-epoch reach per shedder, (b) exposure-set
  footprints, (c) susceptibility heterogeneity / depletion.

Wrappers observe only: nothing draws on the engine's RNG — susceptibility
is read after the challenge resolves (the confined_challenge_trace.py
convention), and the near-field unit weight is recorded from the engine's
own return value.

Wrappers are installed as *instance* attributes on the TransmissionCore, so
they are invoked with the call-site arguments only — no ``self``.

Usage:
    python3 tools/covid_takeoff_attribution.py \
        --design picard_framework/runs/covid_theta_screen_v12_stage2_design.json \
        --theta 2.37e11 --seeds 20200205 [--epochs N] [--out out.json]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engines.transmission_core import (
    CABIN_COMPARTMENT_SEPARATOR,
    TransmissionCore,
)
from picard_framework.covid_boarding_screen import (
    PATHOGEN_ID,
    QuarantineAttributionLedger,
    cell_payload,
    enumerate_cells,
    load_design,
    prepare_cell_run_spec,
)
from picard_framework.covid_theta_fit import run_fit_spec
from simulation_utils.paths import resolve_repo_path, validated_open
from tools.covid_assay_smoke import repo_root_of
from tools.covid_route_attribution import _quantiles, _SusceptibilityResolver

# Channels the deliverable names, resolved below the engine's pathway keys.
CHANNELS = (
    "cabin_mate_ring",
    "dining_ring",
    "near_field_plume",
    "zone_pool",
    "hvac_airborne",
    "contact",
    "other",
)
# Droplet-pathway channels: the dose the pooled/plume droplet pathway
# carried; every other channel key comes straight from the pathway vector.
DROPLET_CHANNELS = (
    "cabin_mate_ring",
    "dining_ring",
    "near_field_plume",
    "zone_pool",
)
# Engine pathway key -> declared channel. "droplet" maps to None: it is
# resolved below pathway level into the droplet channels above.
PATHWAY_CHANNEL = {
    "droplet": None,
    "direct_contact": "contact",
    "contact": "contact",
    "hvac_airborne": "hvac_airborne",
    "fomite": "other",
    "food": "other",
    "emesis_aerosol": "other",
    "flush_aerosol": "other",
    "environmental": "other",
}


def _dose_shares(weights: dict[int, float]) -> dict[int, float]:
    """Normalise a shedder->weight map to dose shares ({} on empty)."""
    total = sum(weights.values())
    if total <= 0.0:
        return {}
    return {sid: w / total for sid, w in weights.items() if w > 0.0}


class TakeoffAttributionLedger:
    """Epoch observer: per-onset channel and shedder attribution.

    Buffers hold only the current epoch; on each ``observe`` the epoch's
    infected hosts get a full onset row and every challenged host feeds
    the susceptibility / reach aggregates before the buffers are dropped.
    """

    def __init__(self, pathogen_id: str = PATHOGEN_ID) -> None:
        self.pathogen_id = pathogen_id
        self._installed = False
        self._epoch = -1

        # Per-epoch buffers populated by the wrappers during
        # execute_transmission (droplet detail) and by observe itself
        # (non-droplet matrix records, challenges), all dropped post-flush.
        # Matrix records carry exposure-set membership and source ids only:
        # their ``dose`` field is rounded to 4 decimals, so channel dose for
        # non-droplet routes comes from the pathway vector on the challenge.
        self._droplet: dict[int, dict[str, Any]] = {}
        self._addback: dict[int, dict[str, Any]] = {}
        self._near: dict[int, dict[str, Any]] = {}
        self._other_src: dict[int, dict[str, Counter]] = {}
        self._challenges: dict[int, dict[str, Any]] = {}
        self._epoch_units: dict[str, dict[str, Any]] = {}
        self._reach_buf: dict[tuple[int, str], int] = {}
        self._near_ctx: tuple[int, int] | None = None
        self._near_weights: dict[int, tuple[float, str]] = {}

        # Results.
        self.onsets: list[dict[str, Any]] = []
        self.challenged_susc: dict[int, float] = {}
        self.reach_by_channel: dict[str, list[int]] = {
            c: [] for c in CHANNELS
        }
        # (epoch, channel) -> susceptibles with positive measured channel
        # dose this epoch (droplet channels from the wrappers' naive doses,
        # other channels from the post-efficiency pathway vector).
        self.footprint_counts: Counter = Counter()
        # (epoch, channel) -> hosts holding a matrix exposure-set record.
        self.offered_counts: Counter = Counter()
        self.unit_sizes: Counter = Counter()
        self.lifetime_sub: dict[int, Counter] = {}
        self.dosed_targets_epoch: Counter = Counter()
        self.droplet_unattributed = 0
        self.susceptibles_aboard: list[int] = []
        self._seen_infected: set[int] = set()

    # ── wrappers ────────────────────────────────────────────────────

    def _install(self, tx_core: Any) -> None:
        orig_record = tx_core._record_droplet_exposure
        orig_addback = tx_core._cabin_mate_droplet_addback
        orig_near = tx_core._near_field_droplet_dose
        orig_unit = tx_core._near_field_unit
        orig_resolve = tx_core._resolve_pathogen_challenge
        ledger = self
        pid = self.pathogen_id

        def record_wrapped(st: Any, matrix: Any, target: Any,
                           dose: float, near_dose: float) -> None:
            orig_record(st, matrix, target, dose, near_dose)
            tid = int(target.agent_id)
            slot = ledger._droplet.setdefault(tid, {
                "dose": 0.0, "near": 0.0, "unit": st.unit_name,
                "zone": st.zone_name, "src": {},
            })
            slot["dose"] += float(dose)
            slot["near"] += float(near_dose)
            slot["src"].update(
                {int(s.agent_id): float(em) for s, em in st.emitted_shedders}
            )
            unit = ledger._epoch_units.setdefault(
                st.unit_name, {"zone": st.zone_name, "targets": 0, "src": {}},
            )
            unit["targets"] += 1
            unit["src"].update(
                {int(s.agent_id): float(em) for s, em in st.emitted_shedders}
            )

        def addback_wrapped(target: Any, shedders: list, volume: Any,
                            vent_factor: Any, target_factor: float,
                            emission_fraction: Any, epoch: int,
                            residence_factor: Any) -> float:
            dose = orig_addback(
                target, shedders, volume, vent_factor, target_factor,
                emission_fraction, epoch, residence_factor,
            )
            if dose > 0.0:
                weights = {}
                for shedder, sv in shedders:
                    if shedder.agent_id not in target.cabin_mate_ids:
                        continue
                    factor = tx_core.confinement_emission_factor(shedder)
                    copresence = tx_core._cabin_pair_copresence(
                        shedder, target, epoch,
                    )
                    # Per-shedder addback contribution, engine form.
                    weights[shedder.agent_id] = (
                        sv * copresence * (1.0 - factor * target_factor)
                    )
                ledger._addback[int(target.agent_id)] = {
                    "dose": float(dose),
                    "src": weights,
                }
            return dose

        def near_wrapped(zone_name: str, target: Any, emitted: list,
                         volume: Any, target_factor: float,
                         emission_fraction: Any, epoch: int,
                         **kw: Any) -> float:
            ledger._near_ctx = (int(epoch), int(target.agent_id))
            ledger._near_weights = {}
            try:
                dose = orig_near(
                    zone_name, target, emitted, volume, target_factor,
                    emission_fraction, epoch, **kw,
                )
            finally:
                weights = dict(ledger._near_weights)
                ledger._near_weights = {}
                ledger._near_ctx = None
            if dose <= 0.0 or not weights:
                return dose
            emitted_of = {s.agent_id: em for s, em in emitted}
            shedder_of = {s.agent_id: s for s, _ in emitted}
            shares: dict[int, float] = {}
            ring_doses: Counter = Counter()
            for sid, (w, ring) in weights.items():
                em = emitted_of.get(sid, 0.0)
                if em <= 0.0:
                    continue
                shedder = shedder_of[sid]
                if sid in target.cabin_mate_ids:
                    factor = tx_core.confinement_emission_factor(shedder)
                    contribution = w * (em / factor if factor > 0 else em)
                else:
                    contribution = w * em * target_factor
                shares[sid] = contribution
            shares = _dose_shares(shares)
            for sid, share in shares.items():
                ring_doses[weights[sid][1]] += dose * share
            ledger._near[int(target.agent_id)] = {
                "dose": float(dose),
                "weights": {s: w for s, (w, _r) in weights.items()},
                "ring_doses": dict(ring_doses),
                "src": shares,
            }
            return dose

        def unit_wrapped(zone_name: str, target: Any, shedder: Any,
                         epoch: int, proximity_ids: Any = None) -> Any:
            weight = orig_unit(
                zone_name, target, shedder, epoch, proximity_ids,
            )
            ctx = ledger._near_ctx
            if (
                ctx is not None
                and ctx[0] == int(epoch)
                and ctx[1] == target.agent_id
                and weight is not None
                and weight > 0.0
            ):
                ledger._near_weights[int(shedder.agent_id)] = (
                    float(weight),
                    _near_ring(tx_core, zone_name, target, shedder,
                               epoch, proximity_ids),
                )
            return weight

        def resolve_wrapped(epoch: int, agent: Any, pathogen_id: str,
                            apd: Any, apw: Any, matrix: Any,
                            events: list) -> None:
            watched = (
                pathogen_id == pid and not agent.is_infected_with(pid)
            )
            p_dose = 0.0
            pw: dict[str, float] = {}
            protection = 0.0
            if watched:
                p_dose = float(apd.get(agent.agent_id, {}).get(pid, 0.0))
                watched = p_dose > 0.0
            if watched:
                protection = tx_core._challenge_protection(agent, pid, epoch)
                pw = {
                    name.rsplit(":", 1)[0]: float(dose)
                    for name, dose in apw.get(agent.agent_id, {}).items()
                    if name.endswith(f":{pid}")
                }
            orig_resolve(
                epoch, agent, pathogen_id, apd, apw, matrix, events,
            )
            if watched:
                ledger._challenges[int(agent.agent_id)] = {
                    "epoch": int(epoch),
                    "p_dose": p_dose,
                    "protection": float(protection),
                    "pathways": pw,
                    "susceptibility": (
                        agent.dose_response_susceptibility.get(pid)
                    ),
                    "infected": pid in agent.infections,
                    "location": agent.current_location,
                }

        tx_core._record_droplet_exposure = record_wrapped
        tx_core._cabin_mate_droplet_addback = addback_wrapped
        tx_core._near_field_droplet_dose = near_wrapped
        tx_core._near_field_unit = unit_wrapped
        tx_core._resolve_pathogen_challenge = resolve_wrapped
        self._installed = True

    # ── per-epoch helpers ───────────────────────────────────────────

    def _reach_add(self, sid: int, channel: str, n: int = 1) -> None:
        key = (sid, channel)
        self._reach_buf[key] = self._reach_buf.get(key, 0) + n

    def _tally_matrix(self, epoch: int, matrix: Any) -> None:
        records = (
            (getattr(matrix, "shared_room_exposures", []), "contact",
             ("source_ids", "source_agent_ids")),
            (getattr(matrix, "hvac_downstream_exposures", []),
             "hvac_airborne", ("source_agent_ids", "source_ids")),
            (getattr(matrix, "emesis_aerosol_exposures", []), "other",
             ("source_agent_ids", "source_ids")),
            (getattr(matrix, "flush_aerosol_exposures", []), "other",
             ("source_agent_ids", "source_ids")),
            (getattr(matrix, "fomite_trailing_exposures", []), "other",
             ("prev_shedder_ids", "source_ids")),
        )
        for rows, channel, source_keys in records:
            for rec in rows:
                tid = int(rec["target_id"])
                self.offered_counts[(epoch, channel)] += 1
                sources: list[int] = []
                for key in source_keys:
                    if rec.get(key):
                        sources = [int(s) for s in rec[key]]
                        break
                if sources:
                    slot = self._other_src.setdefault(tid, {})
                    cur = slot.setdefault(channel, Counter())
                    for sid in sources:
                        cur[sid] += 1
                        self._reach_add(sid, channel)

    def _channel_parts(self, tid: int) -> Counter:
        """This epoch's naive droplet dose split into the named rings."""
        parts: Counter = Counter()
        droplet = self._droplet.get(tid)
        if droplet is None:
            return parts
        near = self._near.get(tid, {})
        addback = self._addback.get(tid, {})
        near_dose = float(near.get("dose", droplet["near"]))
        pool = droplet["dose"] - near_dose - addback.get("dose", 0.0)
        if CABIN_COMPARTMENT_SEPARATOR in str(droplet["unit"]):
            parts["cabin_mate_ring"] += max(pool, 0.0)
        else:
            parts["zone_pool"] += max(pool, 0.0)
        parts["cabin_mate_ring"] += addback.get("dose", 0.0)
        ring_doses = near.get("ring_doses")
        if ring_doses:
            for ring, rdose in ring_doses.items():
                parts[ring] += rdose
        elif near_dose > 0.0:
            parts["near_field_plume"] += near_dose
        return parts

    # ── observer ────────────────────────────────────────────────────

    def observe(self, sim: Any, work: Any) -> None:
        if not self._installed:
            self._install(sim.tx_core)
        epoch = int(work.epoch)
        self._epoch = epoch
        matrix = work.tracing_matrix
        if matrix is not None:
            self._tally_matrix(epoch, matrix)

        seeded = set(getattr(sim.engine, "explicit_seed_agent_ids", None) or ())
        quarantined = set(
            getattr(sim.engine, "quarantined_ids", None) or ()
        )
        susceptible = 0
        for agent in sim.engine.agents:
            if agent.agent_id in seeded:
                continue
            if (
                self.pathogen_id not in agent.infections
                and not agent.has_departed(epoch)
            ):
                susceptible += 1
        self.susceptibles_aboard.append(susceptible)

        # This epoch's per-target droplet-channel parts (naive basis).
        all_parts: dict[int, Counter] = {}
        for tid in self._droplet:
            all_parts[tid] = self._channel_parts(tid)

        for tid, parts in all_parts.items():
            lt = self.lifetime_sub.setdefault(tid, Counter())
            for channel, dose in parts.items():
                lt[channel] += dose

        # Dosed footprint: droplet channels from the measured parts, every
        # other channel from the challenged host's pathway vector.
        dosed_tids: dict[str, set[int]] = {c: set() for c in CHANNELS}
        for tid, parts in all_parts.items():
            for channel, dose in parts.items():
                if dose > 0.0:
                    dosed_tids.setdefault(channel, set()).add(tid)
        for tid, challenge in self._challenges.items():
            pw = challenge["pathways"]
            droplet_pw = pw.get("droplet", 0.0)
            if droplet_pw > 0.0 and not any(
                all_parts.get(tid, {}).get(c, 0.0) > 0.0
                for c in DROPLET_CHANNELS
            ):
                self.droplet_unattributed += 1
            for name, dose in pw.items():
                channel = PATHWAY_CHANNEL.get(name, "other")
                if channel is not None and dose > 0.0:
                    dosed_tids[channel].add(tid)
            if challenge["p_dose"] > 0.0:
                self.dosed_targets_epoch[epoch] += 1
        for tid, parts in all_parts.items():
            if tid not in self._challenges and any(parts.values()):
                self.dosed_targets_epoch[epoch] += 1
        for channel, tids in dosed_tids.items():
            if tids:
                self.footprint_counts[(epoch, channel)] = len(tids)

        # Footprint + reach aggregates.
        for unit, info in self._epoch_units.items():
            self.unit_sizes[unit] = max(
                self.unit_sizes.get(unit, 0), info["targets"],
            )
            for sid, em in info["src"].items():
                if em > 0.0:
                    self._reach_add(sid, "zone_pool", n=info["targets"])
        for tid, near in self._near.items():
            for sid, share in near["src"].items():
                if share > 0.0:
                    self._reach_add(sid, "near_field_plume")
        for tid, addback in self._addback.items():
            for sid, w in addback["src"].items():
                if w > 0.0:
                    self._reach_add(sid, "cabin_mate_ring")
        for (sid, channel), n in self._reach_buf.items():
            self.reach_by_channel.setdefault(channel, []).append(n)
        # Onset rows for hosts infected this epoch.
        for ev in work.tx_events:
            tid = int(ev.target_agent_id)
            if tid in seeded or tid in self._seen_infected:
                continue
            challenge = self._challenges.get(tid)
            if challenge is None or not challenge["infected"]:
                continue
            self._seen_infected.add(tid)
            self.onsets.append(self._onset_row(
                sim, ev, tid, epoch, quarantined,
                all_parts.get(tid, Counter()),
            ))

        # Susceptibility bookkeeping for every challenged host.
        for tid, challenge in self._challenges.items():
            if tid not in self._seen_infected:
                susc = challenge["susceptibility"]
                if susc is not None:
                    self.challenged_susc[tid] = float(susc)

        self._droplet, self._addback, self._near = {}, {}, {}
        self._other_src, self._challenges = {}, {}
        self._epoch_units, self._reach_buf = {}, {}

    def _onset_row(
        self, sim: Any, ev: Any, tid: int, epoch: int,
        quarantined: set[int], parts: Counter,
    ) -> dict[str, Any]:
        challenge = self._challenges[tid]
        # Post-efficiency channel doses: droplet sub-channels split the
        # pathway's post-efficiency dose by their naive shares; every other
        # pathway maps straight onto its channel.
        pw = challenge["pathways"]
        droplet_post = pw.get("droplet", 0.0)
        droplet_naive = sum(parts.get(c, 0.0) for c in DROPLET_CHANNELS)
        chan_post: Counter = Counter()
        if droplet_naive > 0.0:
            for channel in DROPLET_CHANNELS:
                chan_post[channel] += (
                    droplet_post * parts.get(channel, 0.0) / droplet_naive
                )
        elif droplet_post > 0.0:
            chan_post["droplet_unattributed"] += droplet_post
        for name, dose in pw.items():
            channel = PATHWAY_CHANNEL.get(name)
            if channel is None:
                continue
            chan_post[channel] += dose
        post_total = sum(chan_post.values())
        shares = (
            {c: chan_post.get(c, 0.0) / post_total for c in CHANNELS}
            if post_total > 0 else {}
        )
        susc = float(challenge["susceptibility"] or 0.0)
        effective = challenge["p_dose"] * (1.0 - challenge["protection"])

        # Shedder credit on post-efficiency dose: pool by emitted share,
        # addback by the engine's per-shedder weight, near field by the
        # weight x emitted share, other channels by record appearance share
        # (the matrix records carry the offer set, not per-source doses).
        credit: Counter = Counter()
        droplet = self._droplet.get(tid, {})
        near = self._near.get(tid, {})
        addback = self._addback.get(tid, {})
        other_src = self._other_src.get(tid, {})
        pool_naive = (
            droplet.get("dose", 0.0)
            - float(near.get("dose", droplet.get("near", 0.0)))
            - addback.get("dose", 0.0)
        )
        emitted_total = sum(droplet.get("src", {}).values())
        if droplet_naive > 0.0 and emitted_total > 0.0:
            pool_post = droplet_post * max(pool_naive, 0.0) / droplet_naive
            for sid, em in droplet["src"].items():
                credit[sid] += pool_post * em / emitted_total
        addback_total = sum(addback.get("src", {}).values())
        if droplet_naive > 0.0 and addback_total > 0.0:
            addback_post = (
                droplet_post * addback.get("dose", 0.0) / droplet_naive
            )
            for sid, w in addback["src"].items():
                credit[sid] += addback_post * w / addback_total
        if droplet_naive > 0.0:
            near_post = (
                droplet_post * near.get("dose", 0.0) / droplet_naive
            )
            for sid, share in near.get("src", {}).items():
                credit[sid] += near_post * share
        for channel in ("contact", "hvac_airborne", "other"):
            src = other_src.get(channel)
            post = chan_post.get(channel, 0.0)
            if not src or post <= 0.0:
                continue
            src_total = sum(src.values())
            for sid, appearances in src.items():
                credit[sid] += post * appearances / src_total
        credit_total = sum(credit.values())

        dominant = (
            max(chan_post, key=chan_post.get) if post_total > 0 else "none"
        )
        return {
            "agent_id": tid,
            "epoch": epoch,
            "day": int(sim.clock.day_index(epoch)),
            "zone": ev.zone,
            "venue": TransmissionCore.compartment_parent(str(ev.zone)),
            "unit": droplet.get("unit"),
            "confined": tid in quarantined,
            "susceptibility": susc,
            "lambda_infecting": susc * effective,
            "p_dose": challenge["p_dose"],
            "protection": challenge["protection"],
            "dominant_channel": dominant,
            "channel_shares": {c: shares.get(c, 0.0) for c in CHANNELS},
            "channel_dose_post": dict(chan_post),
            "lifetime_route": dict(ev.acquired_particles_by_route or {}),
            "lifetime_sub": dict(self.lifetime_sub.get(tid, {})),
            "shedder_credit": (
                {
                    str(sid): share / credit_total
                    for sid, share in credit.items()
                    if share > 0
                }
                if credit_total > 0 else {}
            ),
        }


def _near_ring(tx_core: Any, zone_name: str, target: Any, shedder: Any,
               epoch: int, proximity_ids: Any) -> str:
    """Which declared ring delivered one near-field contribution.

    Fixed rings claim their own dose: a cabin mate in a Cabin_Corridor and
    same-table diners carry the weight regardless of the sampled proximity
    set. The proximity set claims a shedder only when no fixed ring already
    admits the pair — an adjacent-table mate lifted from rho to 1.0 and an
    unrelated partner both stand in the breathing zone because the sample
    drew them.
    """
    sid = int(shedder.agent_id)
    mate_pair = sid in target.cabin_mate_ids
    if mate_pair:
        if tx_core.zone_types.get(zone_name) == "Cabin_Corridor":
            return "cabin_mate_ring"
        return "near_field_plume"  # reachable only via the proximity set
    table = tx_core._table_party(zone_name, target, epoch)
    if table is not None and sid in table[0]:
        return "dining_ring"
    in_proximity = proximity_ids is not None and sid in proximity_ids
    if in_proximity:
        return "near_field_plume"
    if tx_core._adjacent_table(target, shedder, epoch):
        return "dining_ring"
    return "near_field_plume_unclassified"


def _channel_quantiles(vals: dict[str, list[int]],
                       channel: str) -> dict[str, Any]:
    series = vals.get(channel, [])
    return {
        "n": len(series),
        "quantiles": _quantiles([float(v) for v in series]),
    }


def summarise(sim: Any, ledger: TakeoffAttributionLedger,
              payload: dict[str, Any], takeoff_min: int) -> dict[str, Any]:
    """Aggregate one finished cell into the readout structure."""
    seeded = set(getattr(sim.engine, "explicit_seed_agent_ids", None) or ())
    profiles = getattr(sim.tx_core, "pathogen_profiles", {})
    resolver = _SusceptibilityResolver(
        seed=int(getattr(sim.run_spec, "random_seed", 0) or 0),
        profiles=profiles,
    )
    pid = PATHOGEN_ID
    agents = {a.agent_id: a for a in sim.engine.agents}
    infected = ledger.onsets
    recorded = int(payload.get("observables", {}).get("recorded_onsets") or 0)

    # Susceptibility: infected vs challenged-uninfected vs never challenged.
    infected_ids = {r["agent_id"] for r in infected}
    susc_infected = [
        r["susceptibility"] for r in infected
        if r["susceptibility"] is not None
    ]
    susc_challenged = [
        v for k, v in ledger.challenged_susc.items()
        if k not in infected_ids
    ]
    challenged_ids = set(ledger.challenged_susc) | infected_ids
    susc_never = [
        resolver.susceptibility(a, pid)[0]
        for aid, a in agents.items()
        if aid not in challenged_ids and aid not in seeded
        and a.infections.get(pid) is None
    ]

    # Shedder geometry: dominant-shedder onsets plus share-weighted credit.
    credit_totals: Counter = Counter()
    dominant_counts: Counter = Counter()
    for row in infected:
        shares = row["shedder_credit"]
        if not shares:
            continue
        top = max(shares.items(), key=lambda kv: kv[1])
        dominant_counts[int(top[0])] += 1
        for sid, share in shares.items():
            credit_totals[int(sid)] += float(share)
    sorted_credits = sorted(credit_totals.values(), reverse=True)
    sorted_dominant = sorted(dominant_counts.values(), reverse=True)
    n_infected = max(len(infected), 1)

    epoch_hist = Counter(r["epoch"] for r in infected)
    day_hist = Counter(r["day"] for r in infected)
    venue_hist = Counter(str(r["venue"]) for r in infected)
    confined_n = sum(1 for r in infected if r["confined"])
    chan_dom = Counter(r["dominant_channel"] for r in infected)
    chan_dose: Counter = Counter()
    chan_lifetime: Counter = Counter()
    for row in infected:
        for channel, dose in row["channel_dose_post"].items():
            chan_dose[channel] += dose
        lt = row["lifetime_route"]
        sub = row["lifetime_sub"]
        sub_droplet = sum(
            sub.get(c, 0.0) for c in DROPLET_CHANNELS
        )
        for route, dose in lt.items():
            route = route.split(":", 1)[0]
            if route == "droplet" and sub_droplet > 0:
                for channel in DROPLET_CHANNELS:
                    chan_lifetime[channel] += (
                        dose * sub.get(channel, 0.0) / sub_droplet
                    )
            elif route in ("contact", "direct_contact"):
                chan_lifetime["contact"] += dose
            elif route == "hvac_airborne":
                chan_lifetime["hvac_airborne"] += dose
            else:
                chan_lifetime["other"] += dose
    total_dose = sum(chan_dose.values())
    total_lt = sum(chan_lifetime.values())
    chan_share = Counter()
    for row in infected:
        for channel, share in row["channel_shares"].items():
            chan_share[channel] += share
    lam = [r["lambda_infecting"] for r in infected]
    footprint = {
        channel: {
            "epochs_with_dosed_targets": sum(
                1 for (_e, c) in ledger.footprint_counts if c == channel
            ),
            "targets_per_epoch_quantiles": _quantiles(
                [float(v) for (e, c), v in ledger.footprint_counts.items()
                 if c == channel],
            ),
        }
        for channel in CHANNELS
    }
    offered = {
        channel: {
            "epochs_with_records": sum(
                1 for (_e, c) in ledger.offered_counts if c == channel
            ),
            "targets_per_epoch_quantiles": _quantiles(
                [float(v) for (e, c), v in ledger.offered_counts.items()
                 if c == channel],
            ),
        }
        for channel in CHANNELS
    }
    return {
        "infections_total": len(infected),
        "recorded_onsets": recorded,
        "takeoff": recorded >= takeoff_min,
        "seeded_count": len(seeded),
        "confined_onsets": confined_n,
        "route_split": {
            "by_infecting_epoch_dose": {
                c: (chan_dose.get(c, 0.0) / total_dose
                    if total_dose else None)
                for c in CHANNELS
            },
            "by_onset_share": {
                c: chan_share.get(c, 0.0) / n_infected
                for c in CHANNELS
            },
            "by_dominant_channel": dict(chan_dom),
            "by_lifetime_dose": {
                c: (chan_lifetime.get(c, 0.0) / total_lt
                    if total_lt else None)
                for c in CHANNELS
            },
        },
        "geometry": {
            "onsets_per_shedder_credit": {
                "n_shedders_credited": len(sorted_credits),
                "top1": sorted_credits[0] if sorted_credits else None,
                "top5_share": (
                    sum(sorted_credits[:5]) / n_infected
                    if sorted_credits else None
                ),
                "quantiles": _quantiles(sorted_credits),
            },
            "onsets_per_shedder_dominant": {
                "n_shedders": len(sorted_dominant),
                "top1": sorted_dominant[0] if sorted_dominant else None,
                "top5_share": (
                    sum(sorted_dominant[:5]) / n_infected
                    if sorted_dominant else None
                ),
                "quantiles": _quantiles(
                    [float(v) for v in sorted_dominant],
                ),
            },
            "onsets_per_epoch": {
                "n_epochs_with_onsets": len(epoch_hist),
                "top5_share": (
                    sum(sorted(epoch_hist.values(), reverse=True)[:5])
                    / n_infected
                ),
                "quantiles": _quantiles(
                    [float(v) for v in epoch_hist.values()],
                ),
            },
            "onsets_per_day": {
                str(d): n for d, n in sorted(day_hist.items())
            },
            "onsets_per_venue": dict(venue_hist.most_common(16)),
        },
        "mechanism": {
            "reach_per_shedder_epoch": {
                c: _channel_quantiles(ledger.reach_by_channel, c)
                for c in CHANNELS
            },
            "footprint_targets_per_epoch": footprint,
            "offered_targets_per_epoch": offered,
            "dosed_targets_per_epoch": _quantiles(
                [float(v) for v in ledger.dosed_targets_epoch.values()],
            ),
            "droplet_unattributed_onsets": ledger.droplet_unattributed,
            "susceptibles_aboard": _quantiles(
                [float(v) for v in ledger.susceptibles_aboard],
            ),
            "susceptibility": {
                "infected": _quantiles(susc_infected),
                "challenged_uninfected": _quantiles(susc_challenged),
                "never_challenged_counterfactual": _quantiles(susc_never),
                "challenged_hosts": len(challenged_ids),
                "challenged_share_of_aboard": (
                    len(challenged_ids) / max(len(agents) - len(seeded), 1)
                ),
            },
            "lambda_infecting": _quantiles(lam),
        },
    }


def analyse_cell(design: Any, cell: Any, *,
                 num_epochs: int | None, repo_root: str) -> dict[str, Any]:
    """Run one instrumented declared-replay cell."""
    raw = prepare_cell_run_spec(
        design, cell, num_epochs=num_epochs, repo_root=repo_root,
    )
    quarantine_ledger = QuarantineAttributionLedger()
    ledger = TakeoffAttributionLedger()

    def observer(sim: Any, work: Any) -> None:
        quarantine_ledger.observe(sim, work)
        ledger.observe(sim, work)

    sim = run_fit_spec(raw, repo_root=repo_root, epoch_observer=observer)
    payload = cell_payload(design, cell, sim, quarantine_ledger, raw)
    return {
        "cell": cell.as_dict(),
        "summary": summarise(
            sim, ledger, payload, design.takeoff_recorded_onsets,
        ),
        "payload_observables": payload.get("observables"),
        "payload_onset_curve": payload.get("onset_curve"),
        "payload_sanitary_activity": payload.get("sanitary_activity"),
        "payload_recorded_onsets": payload.get(
            "observables", {},
        ).get("recorded_onsets"),
        "infections_total": payload.get("infections_total"),
        "aboard_total": payload.get("aboard_total"),
        "first_onset_day": payload.get("first_onset_day"),
        "index_onset_day": payload.get("index_onset_day"),
        "index_departed_epoch": payload.get("index_departed_epoch"),
        "attack_rate": payload.get("attack_rate"),
        "lab_confirmed_total": payload.get("lab_confirmed_total"),
        "vsp_reported_case_fraction_max": payload.get(
            "vsp_reported_case_fraction_max",
        ),
        "onsets": ledger.onsets,
    }


def main() -> None:  # pragma: no cover - CLI driver
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--design",
        default="picard_framework/runs/"
                "covid_theta_screen_v12_stage2_design.json",
    )
    parser.add_argument("--theta", type=float, required=True)
    parser.add_argument("--seeds", default="20200205")
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    repo_root = repo_root_of(__file__)
    design = load_design(os.path.join(repo_root, args.design))
    seeds = {int(s) for s in args.seeds.split(",")}
    cells = [
        c for c in enumerate_cells(design)
        if c.seed in seeds and abs(c.theta - args.theta) < args.theta * 0.001
    ]
    if not cells:
        raise SystemExit(
            f"no cells match theta={args.theta} seeds={sorted(seeds)}",
        )
    results = [
        analyse_cell(design, c, num_epochs=args.epochs, repo_root=repo_root)
        for c in cells
    ]
    text = json.dumps(results, indent=1, default=str)
    if args.out:
        resolved = resolve_repo_path(repo_root, args.out)
        with validated_open(
            resolved, "w", allowed_roots=(repo_root,), encoding="utf-8",
        ) as handle:
            handle.write(text)
        print(f"wrote {resolved}")
    else:
        print(text)


if __name__ == "__main__":
    main()
