#!/usr/bin/env python3
"""NORO-VENUE-01 census probe: emesis placement vs the confinement clock.

Purpose
-------
The ignited-voyage line is subcritical (~0.1/gen, ~13-17 peak cases vs
~90 needed for a VSP posting) and ~85% of secondary-vomit cabin landings
find no susceptible -- structurally, because the cabin that receives the
deposit is the shedder's own stateroom. The open question this census
answers: does that placement happen because hosts are *flagged and
confined before they vomit* (the confinement clock is the named gap), or
does meaningful emesis mass still land pre-confinement / on never-confined
hosts in susceptible-rich shared venues (the barrier is downstream, in
pickup/conversion)?

Method
------
The engine is not modified. Read-only wrappers plus the ship-level epoch
observer:

* ``TransmissionCore._epoch_zone_occupants`` and ``_cabin_compartments``
  -- the engine's own occupancy maps, cached each epoch so an emit row's
  landing occupancy is scored against the same map the dose machinery
  used (emesis lands in ``zone::cabinNNN`` compartment keys, which never
  appear in the parent zone map).
* ``TransmissionCore._emit_emesis`` -- per emitted bolus: landing unit,
  zone type, occupants present (total / susceptible / infected), the
  depositor's generation and import/acquired class, whether the depositor
  was already confined (``core._quarantined_ids``, set at
  ``execute_transmission`` entry) or symptomatic at emit, and the
  deposited loads. Emit calls that produced no record are counted
  separately so the emitted-event denominator is honest.
* ``TransmissionCore._resolve_pathogen_challenge`` -- acquisition
  pedigree identical to ``growth_chain_census`` (generation from the
  source host's pedigree, falling back to the strain's home host).
* ``ShipSimulation.epoch_observer`` -- runs after ``_step_record``, so it
  sees the same epoch's confinement writes: per-epoch confined-set
  membership (``state.quarantined_ids`` | ``isolated_ids`` |
  ``engine.quarantined_ids`` -- the engine-side VSP set is unioned in
  because ``sync_vsp_isolation`` is never invoked outside tests), the
  ``compliance_log`` delta (order/admission/refusal/release events),
  ``escalation_log`` delta, ``ever_reported_ids`` additions, the
  trigger status, and per-host first-symptomatic epochs (agent-level and
  per-pathogen).

Join (post-run, ``_venue_payload``)
-----------------------------------
Each emit event is classified against its emitter's voyage timeline:

* ``post_confinement`` -- host was in the confined set at emit time.
* ``pre_confinement``  -- host was confined later in the voyage
  (``ordered_mobile``: an order was already logged at emit time but
  admission had not landed; ``pre_order``: the emit precedes the first
  order).
* ``never_confined``   -- host never enters the confined set
  (``ordered_refused``: refusal events but no admission;
  ``never_ordered``: no confinement event at all).

Landing units are classified own-stateroom / shared venue (passenger
dining, passenger toilet, leisure) / crew-only / medical / off-grid from
the zone records (type, deck, dining service type, non-leisure tokens).
Latency per host: first-symptomatic -> first report -> first order ->
first confined membership. Nothing here fits or selects a parameter
value; dose_adjustment comes from the spec verbatim.

Inputs
------
``--manifest``/``--tier``/``--index`` pick the campaign cell;
``--seeds`` restricts a manifest tier to a seed subset (ignited cells);
``--spec-json`` runs an arbitrary spec verbatim (classic/mega cells are
reached by post-mutating the tier spec's ``catalog.platform_id``);
``--epochs-override`` caps ``run.num_epochs`` for short witness cells.

Outputs
-------
One ``<tier>/<run_id>.zip`` per run carrying ``summary.json`` in the
campaign layout plus ``venue.json.gz`` with the classified emit rows,
per-host confinement timelines, confinement/escalation events, per-epoch
confinement membership, and the zone classification table.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import json
import sys
import time
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(
    0, str(REPO_ROOT / "picard_framework" / "runs" / "mega_cruise_campaign"),
)

from campaign_runner import generate_tier_runs  # noqa: E402

from engines import transmission_core as tc  # noqa: E402
from engines.infection_dynamics_bridge import (  # noqa: E402
    NON_LEISURE_ZONE_TOKENS,
    IllnessStatus,
    resolve_dining_service_type,
)
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_child_path,
    resolve_repo_path,
    validated_open,
)
from tools.noro_diag.per_host_dose_challenge import (  # noqa: E402
    _attach_voyage_blocks,
)

# The occupancy/pedigree plumbing is shared verbatim with the rhythm
# probe rather than re-typed: identical wrappers keep the two censuses'
# landing snapshots comparable cell-for-cell.
from tools.noro_diag.rhythm_ab_probe import (  # noqa: E402
    RhythmRecorder,
    _identifier,
    _load_manifest,
    _occupancy_snapshot,
    _sim_for_spec,
    _wrap_cabin_compartments,
    _wrap_challenge,
    _wrap_zone_occupants,
)

ASHORE_LOCATION = "Ashore"
ISOLATED_LOCATION = "Isolated_In_Quarters"
DEPARTED_LOCATION = "Departed"
OFF_GRID_LOCATIONS = frozenset(
    {ASHORE_LOCATION, ISOLATED_LOCATION, DEPARTED_LOCATION},
)

# compliance_log actions: an order attempt was written for the host.
ORDER_ACTIONS = frozenset({
    "immediate_compliance",
    "refused_quarantine",
    "vsp_quarantine",
    "refused_vsp_quarantine",
    "delayed_compliance",
    "enforced_confinement",
    "general_confinement",
    "refused_general_confinement",
    "crew_age_duty_exclusion",
    "refused_crew_age_duty_exclusion",
})
# actions under which the host physically enters the confined set.
ADMIT_ACTIONS = frozenset({
    "immediate_compliance",
    "vsp_quarantine",
    "delayed_compliance",
    "enforced_confinement",
    "general_confinement",
    "crew_age_duty_exclusion",
})
REFUSE_ACTIONS = frozenset({
    "refused_quarantine",
    "refused_vsp_quarantine",
    "refused_general_confinement",
    "refused_crew_age_duty_exclusion",
})
RELEASE_ACTIONS = frozenset({
    "crew_age_duty_exclusion_release",
})

CREW_DECK_TOKENS = ("crew", "engine", "bridge")


# ── Recorder ──────────────────────────────────────────────────────────


@dataclass
class VenueRecorder(RhythmRecorder):
    """Rhythm-census pedigree plus confinement-clock observations.

    Inheriting ``RhythmRecorder`` reuses its generation pedigree, epoch0
    import capture and the ashore-dosing witness fields (captured and
    ignored here) so the shared wrappers work unmodified on either
    recorder.
    """

    confined_membership: list[dict[str, Any]] = field(default_factory=list)
    confinement_events: list[dict[str, Any]] = field(default_factory=list)
    escalation_events: list[dict[str, Any]] = field(default_factory=list)
    # Per-host voyage timelines (observer-maintained).
    host_meta: dict[int, dict[str, Any]] = field(default_factory=dict)
    first_symptomatic: dict[int, int] = field(default_factory=dict)
    first_noro_symptomatic: dict[int, int] = field(default_factory=dict)
    ever_symptomatic: set[int] = field(default_factory=set)
    first_reported: dict[int, int] = field(default_factory=dict)
    # Emit-call accounting (invocations vs record-producing emits).
    emit_invocations: int = 0
    emit_idle_invocations: int = 0
    # Observer cursors.
    _compliance_seen: int = 0
    _escalation_seen: int = 0
    _reported_seen: set[int] = field(default_factory=set)


# ── Site classification (pure; exercised by unit tests) ──────────────


def _deck_is_crew(deck: Any) -> bool:
    text = str(deck or "").lower()
    return any(token in text for token in CREW_DECK_TOKENS)


def _zone_has_nonleisure_token(name: str) -> bool:
    lowered = name.lower()
    return any(token in lowered for token in NON_LEISURE_ZONE_TOKENS)


def classify_site(
    zone_name: str,
    zone_rec: dict[str, Any] | None,
) -> dict[str, str]:
    """Map one landing unit to (site_class, site_group, site_detail).

    ``site_class`` is the deliverable's taxonomy: own_stateroom /
    shared_venue / crew_only / medical / off_grid. ``site_group`` is the
    finer split used inside the 3xN table rows; ``site_detail`` keeps the
    raw evidence (zone type, dining service type, deck, parent zone).
    """
    if zone_name in OFF_GRID_LOCATIONS:
        detail = zone_name.lower()
        return {
            "site_class": "off_grid",
            "site_group": detail,
            "site_detail": detail,
        }
    if tc.CABIN_COMPARTMENT_SEPARATOR in zone_name:
        parent = zone_name.split(tc.CABIN_COMPARTMENT_SEPARATOR, 1)[0]
        group = (
            "stateroom_crew" if parent.upper().startswith("CC_")
            else "stateroom_pax"
        )
        return {
            "site_class": "own_stateroom",
            "site_group": group,
            "site_detail": parent,
        }
    rec = zone_rec or {}
    ztype = str(rec.get("type") or "")
    deck = str(rec.get("deck") or "")
    crew_deck = _deck_is_crew(deck)
    if ztype == "Dining":
        service = resolve_dining_service_type(rec)
        if service in ("crew_mess", "galley") or crew_deck:
            group = "dining_crew"
            site_class = "crew_only"
        else:
            group = "dining_pax"
            site_class = "shared_venue"
        return {
            "site_class": site_class,
            "site_group": group,
            "site_detail": f"dining:{service}:{deck}",
        }
    if ztype == "Sanitary":
        site_class = "crew_only" if crew_deck else "shared_venue"
        group = "toilet_crew" if crew_deck else "toilet_pax"
        return {
            "site_class": site_class,
            "site_group": group,
            "site_detail": f"sanitary:{deck}",
        }
    if ztype == "Medical":
        return {
            "site_class": "medical",
            "site_group": "medical",
            "site_detail": f"medical:{deck}",
        }
    if crew_deck or _zone_has_nonleisure_token(zone_name):
        return {
            "site_class": "crew_only",
            "site_group": "crew_zone",
            "site_detail": f"{ztype}:{deck}",
        }
    if ztype == "Cabin_Corridor":
        # A corridor key reaching an emit row means the compartment split
        # did not apply; classify by prefix as the block's cabins.
        group = (
            "stateroom_crew" if zone_name.upper().startswith("CC_")
            else "stateroom_pax"
        )
        return {
            "site_class": "own_stateroom",
            "site_group": group,
            "site_detail": f"corridor:{zone_name}",
        }
    return {
        "site_class": "shared_venue",
        "site_group": f"venue_{ztype.lower() or 'other'}",
        "site_detail": f"{ztype}:{deck}",
    }


def _zone_parent(zone_name: str) -> str:
    return zone_name.split(tc.CABIN_COMPARTMENT_SEPARATOR, 1)[0]


# ── Wrappers ──────────────────────────────────────────────────────────


def _wrap_emit_emesis(core_cls: type, rec: VenueRecorder) -> Any:
    """Per-bolus landing record plus the depositor's confinement state."""
    original = core_cls._emit_emesis

    def wrapper(
        self: Any, agent: Any, pathogen_id: str, profile: dict,
        zone_name: str, epoch: int,
    ) -> float:
        before = len(
            agent.emesis_deposition_records_by_pathogen.get(
                pathogen_id, [],
            ),
        )
        pool_gain = original(
            self, agent, pathogen_id, profile, zone_name, epoch,
        )
        if pathogen_id != rec.pathogen_id:
            return pool_gain
        rec.emit_invocations += 1
        records = agent.emesis_deposition_records_by_pathogen.get(
            pathogen_id, [],
        )[before:]
        if not records:
            rec.emit_idle_invocations += 1
            return pool_gain
        if pool_gain > 0:
            rec.ignited = True
        aid = int(agent.agent_id)
        occupancy = _occupancy_snapshot(rec, self, zone_name)
        inf = agent.infections.get(pathogen_id) or {}
        confined = aid in self._quarantined_ids
        for record in records:
            rec.emesis_rows.append({
                "epoch": int(epoch),
                "agent_id": aid,
                "role": str(getattr(agent, "role", "")),
                "gen": rec.gen_of(aid),
                "gen_class": rec.gen_class_of(aid),
                "zone": zone_name,
                "zone_type": str(self.zone_types.get(zone_name) or ""),
                "location": str(agent.current_location),
                "confined_at_emit": bool(confined),
                "symptomatic_at_emit": bool(agent.is_symptomatic),
                "noro_will_present": inf.get("will_present"),
                "episode_load": float(record.get("episode_load", 0.0)),
                "surface_load": float(record.get("surface_load", 0.0)),
                "aerosol_load": float(record.get("aerosol_load", 0.0)),
                "pool_gain": float(record.get("pool_gain", 0.0)),
                "censored_below_lod": bool(
                    record.get("censored_below_lod", False),
                ),
                **occupancy,
            })
        return pool_gain

    return wrapper


_WRAPPED_CORE_METHODS = (
    "_epoch_zone_occupants",
    "_emit_emesis",
    "_resolve_pathogen_challenge",
    "_cabin_compartments",
)


@contextmanager
def instrumented(rec: VenueRecorder) -> Any:
    """Install every wrapper for the duration of one run."""
    core_cls = tc.TransmissionCore
    saved = {
        name: getattr(core_cls, name) for name in _WRAPPED_CORE_METHODS
    }
    core_cls._epoch_zone_occupants = _wrap_zone_occupants(core_cls, rec)
    core_cls._emit_emesis = _wrap_emit_emesis(core_cls, rec)
    core_cls._resolve_pathogen_challenge = _wrap_challenge(core_cls, rec)
    core_cls._cabin_compartments = _wrap_cabin_compartments(core_cls, rec)
    try:
        yield
    finally:
        for name, fn in saved.items():
            setattr(core_cls, name, fn)


# ── Epoch observer ────────────────────────────────────────────────────


def _host_meta_for(rec: VenueRecorder, agent: Any) -> dict[str, Any]:
    aid = int(agent.agent_id)
    meta = rec.host_meta.get(aid)
    if meta is None:
        inf = agent.infections.get(rec.pathogen_id) or {}
        meta = {
            "role": str(getattr(agent, "role", "")),
            "agent_class": str(getattr(agent, "agent_class", "")),
            "home_zone": str(getattr(agent, "home_zone", "")),
            "will_present": inf.get("will_present"),
        }
        rec.host_meta[aid] = meta
    elif meta.get("will_present") is None:
        meta["will_present"] = (
            agent.infections.get(rec.pathogen_id) or {}
        ).get("will_present")
    return meta


def _capture_event_deltas(rec: VenueRecorder, epoch: int, state: Any) -> None:
    """Append new compliance/escalation/report rows for this epoch."""
    for entry in state.compliance_log[rec._compliance_seen:]:
        if entry.get("agent_id") is None:
            continue
        rec.confinement_events.append({
            "epoch": int(entry.get("epoch", epoch)),
            "agent_id": int(entry.get("agent_id")),
            "action": str(entry.get("action", "")),
            "compliance_class": entry.get("compliance_class"),
        })
    rec._compliance_seen = len(state.compliance_log)
    for entry in state.escalation_log[rec._escalation_seen:]:
        row = {"epoch": epoch}
        if isinstance(entry, dict):
            row.update(entry)
        else:
            row["entry"] = str(entry)
        rec.escalation_events.append(row)
    rec._escalation_seen = len(state.escalation_log)
    reported = {int(a) for a in state.ever_reported_ids}
    for aid in sorted(reported - rec._reported_seen):
        rec.first_reported.setdefault(aid, epoch)
    rec._reported_seen = reported


def _capture_agent_axes(rec: VenueRecorder, epoch: int, engine: Any) -> int:
    symptomatic = 0
    for agent in engine.agents:
        aid = int(agent.agent_id)
        _host_meta_for(rec, agent)
        inf = agent.infections.get(rec.pathogen_id) or {}
        if inf.get("illness") == IllnessStatus.SYMPTOMATIC:
            rec.first_noro_symptomatic.setdefault(aid, epoch)
        if agent.is_symptomatic:
            symptomatic += 1
            rec.ever_symptomatic.add(aid)
            rec.first_symptomatic.setdefault(aid, epoch)
    return symptomatic


def _epoch_observer(rec: VenueRecorder) -> Any:
    def observe(sim: Any, work: Any) -> None:
        epoch = int(work.epoch)
        state = work.state
        engine = sim.engine
        confined = (
            {int(a) for a in state.quarantined_ids}
            | {int(a) for a in state.isolated_ids}
            | {int(a) for a in getattr(engine, "quarantined_ids", ())}
            | {int(a) for a in getattr(engine, "isolated_ids", ())}
        )
        rec.confined_membership.append({
            "epoch": epoch,
            "ids": sorted(confined),
        })
        _capture_event_deltas(rec, epoch, state)
        symptomatic = _capture_agent_axes(rec, epoch, engine)
        sick_calls = 0
        if work.syn_result:
            sick_calls = int(work.syn_result.get("sick_call_count", 0))
        rec.epoch_rows.append({
            "epoch": epoch,
            "trigger_status": str(state.trigger_status),
            "n_confined": len(confined),
            "n_reported": len(state.ever_reported_ids),
            "n_ever_ill": len(state.ever_ill_ids),
            "n_symptomatic": symptomatic,
            "n_sick_calls": sick_calls,
            "n_infected": sum(
                1 for a in engine.agents
                if a.is_infected_with(rec.pathogen_id)
            ),
        })
        if not rec.epoch0_done:
            rec.epoch0_done = True
            for agent in engine.agents:
                if agent.is_infected_with(rec.pathogen_id):
                    aid = int(agent.agent_id)
                    if aid not in rec.acquired_ids:
                        rec.import_ids.add(aid)
                        rec.host_gen.setdefault(aid, 0)

    return observe


# ── Post-run join ─────────────────────────────────────────────────────


def _confined_epochs_index(
    rec: VenueRecorder,
) -> dict[int, list[int]]:
    """host id -> sorted epochs it appears in the confined set."""
    by_host: dict[int, list[int]] = {}
    for snap in rec.confined_membership:
        epoch = int(snap["epoch"])
        for aid in snap["ids"]:
            by_host.setdefault(int(aid), []).append(epoch)
    return by_host


def _host_timeline(rec: VenueRecorder, aid: int) -> dict[str, Any]:
    """One emitter/host's confinement timeline for the voyage."""
    events = [e for e in rec.confinement_events if e["agent_id"] == aid]
    orders = [e["epoch"] for e in events if e["action"] in ORDER_ACTIONS]
    admits = [e["epoch"] for e in events if e["action"] in ADMIT_ACTIONS]
    refusals = [e["epoch"] for e in events if e["action"] in REFUSE_ACTIONS]
    releases = [e["epoch"] for e in events if e["action"] in RELEASE_ACTIONS]
    return {
        "first_order_epoch": min(orders) if orders else None,
        "first_admit_event_epoch": min(admits) if admits else None,
        "refusal_epochs": refusals,
        "release_epochs": releases,
        "actions": [
            {"epoch": e["epoch"], "action": e["action"]} for e in events
        ],
    }


def _emit_confinement_class(
    row: dict[str, Any],
    timeline: dict[str, Any],
    confined_epochs: list[int] | None,
) -> tuple[str, str]:
    """Assign one emit event to a confinement class + order subclass."""
    if row["confined_at_emit"]:
        return "post_confinement", "confined"
    first_order = timeline["first_order_epoch"]
    if confined_epochs:
        first_confined = min(confined_epochs)
        if row["epoch"] < first_confined:
            if first_order is not None and first_order <= row["epoch"]:
                return "pre_confinement", "ordered_mobile"
            return "pre_confinement", "pre_order"
        # emit on/after the first confined epoch but not confined at emit:
        # released mid-voyage or an order that never admitted.
        if first_order is not None and first_order <= row["epoch"]:
            return "never_confined_at_emit", "ordered_not_admitted"
        return "never_confined_at_emit", "released_or_unordered"
    if timeline["refusal_epochs"]:
        return "never_confined", "ordered_refused"
    if first_order is not None:
        return "never_confined", "ordered_never_admitted"
    return "never_confined", "never_ordered"


def _emitter_class(rec: VenueRecorder, aid: int) -> str:
    if aid in rec.ever_symptomatic:
        return "symptomatic_onboard"
    meta = rec.host_meta.get(aid) or {}
    if meta.get("will_present") is False:
        return "never_symptomatic_course"
    return "never_symptomatic_onboard"


def _zones_meta(engine: Any) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for zrec in getattr(engine, "zones", []) or []:
        name = str(zrec.get("name") or zrec.get("id") or "")
        if not name:
            continue
        site = classify_site(name, zrec)
        out[name] = {
            "type": str(zrec.get("type") or ""),
            "deck": str(zrec.get("deck") or ""),
            **site,
        }
    return out


def _join_emits(
    rec: VenueRecorder,
    zones_meta: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    confined_index = _confined_epochs_index(rec)
    timelines: dict[int, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    unattributed = 0
    for row in rec.emesis_rows:
        aid = int(row["agent_id"])
        if aid not in rec.host_meta:
            unattributed += 1
        if aid not in timelines:
            timelines[aid] = _host_timeline(rec, aid)
        conf_class, order_sub = _emit_confinement_class(
            row, timelines[aid], confined_index.get(aid),
        )
        site = classify_site(
            row["zone"], zones_meta.get(_zone_parent(row["zone"])),
        )
        rows.append({
            **row,
            # pedigree is finalized post-run: epoch-0 emits predate the
            # observer's import capture, so re-resolve the class here.
            "gen": rec.gen_of(aid),
            "gen_class": rec.gen_class_of(aid),
            "confinement_class": conf_class,
            "order_subclass": order_sub,
            "emitter_class": _emitter_class(rec, aid),
            **site,
        })
    return rows, unattributed


def _host_rows(
    rec: VenueRecorder,
    confined_index: dict[int, list[int]],
) -> list[dict[str, Any]]:
    """Per-host latency timeline for every host the census cares about."""
    ids = (
        {int(r["agent_id"]) for r in rec.emesis_rows}
        | set(confined_index)
        | {int(e["agent_id"]) for e in rec.confinement_events}
        | set(rec.first_symptomatic)
        | set(rec.first_reported)
    )
    rows = []
    for aid in sorted(ids):
        timeline = _host_timeline(rec, aid)
        confined_epochs = confined_index.get(aid) or []
        meta = rec.host_meta.get(aid) or {}
        emit_epochs = [
            int(r["epoch"]) for r in rec.emesis_rows
            if int(r["agent_id"]) == aid
        ]
        rows.append({
            "agent_id": aid,
            "role": meta.get("role", ""),
            "home_zone": meta.get("home_zone", ""),
            "gen_class": rec.gen_class_of(aid),
            "will_present": meta.get("will_present"),
            "emitter_class": _emitter_class(rec, aid),
            "first_symptomatic_epoch": rec.first_symptomatic.get(aid),
            "first_noro_symptomatic_epoch": (
                rec.first_noro_symptomatic.get(aid)
            ),
            "first_reported_epoch": rec.first_reported.get(aid),
            "first_order_epoch": timeline["first_order_epoch"],
            "first_confined_epoch": (
                min(confined_epochs) if confined_epochs else None
            ),
            "n_confined_epochs": len(confined_epochs),
            "refusal_epochs": timeline["refusal_epochs"],
            "release_epochs": timeline["release_epochs"],
            "actions": timeline["actions"],
            "n_emesis_emits": len(emit_epochs),
            "first_emit_epoch": min(emit_epochs) if emit_epochs else None,
        })
    return rows


def _venue_payload(
    rec: VenueRecorder,
    spec_dict: dict[str, Any],
    sim: Any,
) -> dict[str, Any]:
    zones_meta = _zones_meta(sim.engine)
    emit_rows, unattributed = _join_emits(rec, zones_meta)
    confined_index = _confined_epochs_index(rec)
    return {
        "ignited": rec.ignited,
        "emit_calls": rec.emit_invocations,
        "emit_calls_no_records": rec.emit_idle_invocations,
        "n_emesis_emitted": len(rec.emesis_rows),
        "n_unattributed": unattributed,
        "n_acquired": len(rec.acquired_ids),
        "n_imports": len(rec.import_ids),
        "emit_rows": emit_rows,
        "host_rows": _host_rows(rec, confined_index),
        "acquisition_rows": rec.acquisition_rows,
        "confinement_events": rec.confinement_events,
        "escalation_events": rec.escalation_events,
        "confined_membership": rec.confined_membership,
        "epoch_rows": rec.epoch_rows,
        "zones_meta": zones_meta,
        "pathogen_id": rec.pathogen_id,
        "platform": str(spec_dict["catalog"]["platform_id"]),
        "seed": int(spec_dict["run"]["random_seed"]),
    }


# ── Run driver ────────────────────────────────────────────────────────


def _run_summary(
    spec: dict[str, Any],
    wall_clock_run: float,
    wall_clock_total: float,
) -> dict[str, Any]:
    overrides = spec.get("config_overrides") or {}
    return {
        "run_id": str(spec.get("description", "")),
        "seed": int(spec["run"]["random_seed"]),
        "num_epochs": int(spec["run"]["num_epochs"]),
        "num_agents": int(
            overrides.get("ship_graph", {}).get("num_agents", 0),
        ),
        "platform": str(spec["catalog"]["platform_id"]),
        "wall_clock_seconds_run": wall_clock_run,
        "wall_clock_seconds_total": wall_clock_total,
    }


def run_spec(
    spec_dict: dict[str, Any],
    *,
    pathogen_id: str,
    natural_history_clock: str | None = None,
) -> dict[str, Any]:
    """Run one spec under the wrappers; return the run payload."""
    spec = copy.deepcopy(spec_dict)
    rec = VenueRecorder(pathogen_id=pathogen_id)
    started_total = time.perf_counter()
    with instrumented(rec), _sim_for_spec(spec) as sim:
        sim.epoch_observer = _epoch_observer(rec)
        started_run = time.perf_counter()
        result = sim.run()
        wall_clock_run = time.perf_counter() - started_run
    summary = _run_summary(
        spec, wall_clock_run, time.perf_counter() - started_total,
    )
    _attach_voyage_blocks(
        summary, spec, result, summary["num_agents"], natural_history_clock,
    )
    summary["venue"] = _venue_payload(rec, spec, sim)
    return summary


# ── CLI / campaign-cell plumbing ──────────────────────────────────────


def _seed_list(value: str) -> list[int]:
    try:
        return [int(v) for v in value.split(",") if v.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid --seeds list: {value!r}",
        ) from exc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path, default=None,
        help="campaign manifest JSON (tier specs verbatim)",
    )
    parser.add_argument(
        "--tier", type=_identifier, default=None,
        help="tier inside --manifest; required with --manifest",
    )
    parser.add_argument(
        "--index", type=int, default=None,
        help="run only the tier's runs[index] (Batch array child / canary)",
    )
    parser.add_argument(
        "--seeds", type=_seed_list, default=None,
        help="restrict the manifest tier to these run.random_seed values",
    )
    parser.add_argument(
        "--platform-id", type=_identifier, default=None,
        help="override spec catalog.platform_id (classic/mega cells)",
    )
    parser.add_argument(
        "--num-agents", type=int, default=None,
        help="override spec ship_graph.num_agents for the platform swap",
    )
    parser.add_argument(
        "--spec-json", type=Path, default=None,
        help="run an arbitrary spec file verbatim",
    )
    parser.add_argument(
        "--epochs-override", type=int, default=None,
        help="cap run.num_epochs for short witness cells",
    )
    parser.add_argument(
        "--pathogen-id", type=_identifier, default="norwalk_gi",
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--out-name", type=_identifier, default=None,
        help="zip filename stem under <out>/<tier>/ (spec-json mode)",
    )
    args = parser.parse_args(argv)
    manifest_mode = args.manifest is not None
    if manifest_mode:
        for problem in (
            "--manifest requires --tier" if args.tier is None else None,
            "--manifest and --spec-json are exclusive"
            if args.spec_json is not None else None,
        ):
            if problem:
                parser.error(problem)
    elif args.tier is not None or args.index is not None:
        parser.error("--tier/--index require --manifest")
    for label, value, floor in (
        ("--index", args.index, 0),
        ("--epochs-override", args.epochs_override, 1),
    ):
        if value is not None and value < floor:
            parser.error(f"{label} must be >= {floor}")
    if args.seeds is not None and not manifest_mode:
        parser.error("--seeds requires --manifest")
    return args


def _apply_overrides(spec: dict[str, Any], args: argparse.Namespace) -> None:
    if args.platform_id is not None:
        spec.setdefault("catalog", {})["platform_id"] = args.platform_id
    if args.num_agents is not None:
        spec.setdefault("config_overrides", {}).setdefault(
            "ship_graph", {},
        )["num_agents"] = int(args.num_agents)


_ANCHOR_KEYS = (
    "parameters", "num_epochs", "trigger_status", "summary",
    "cost_accounting", "derived",
)


def _write_run_zip(
    out_dir: Path, tier: str, run_id: str, payload: dict[str, Any],
) -> Path:
    """``summary.json`` (campaign layout) + ``venue.json.gz`` payload."""
    cell_dir = Path(resolve_child_path(str(out_dir), tier))
    cell_dir.mkdir(parents=True, exist_ok=True)
    zip_path = Path(resolve_child_path(str(cell_dir), f"{run_id}.zip"))
    anchor = {"run_id": run_id}
    anchor.update({key: payload[key] for key in _ANCHOR_KEYS})
    census_blob = gzip.compress(
        json.dumps(payload["venue"]).encode(),
    )
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("summary.json", json.dumps(anchor))
        archive.writestr("venue.json.gz", census_blob)
    return zip_path


def _select_runs(
    manifest: dict[str, Any], tier: str, args: argparse.Namespace,
) -> list[tuple[str, dict[str, Any]]]:
    runs = list(generate_tier_runs(manifest, tier))
    if args.seeds is not None:
        wanted = set(args.seeds)
        runs = [
            pair for pair in runs
            if int(pair[1]["run"]["random_seed"]) in wanted
        ]
    if args.index is not None:
        if args.index >= len(runs):
            raise SystemExit(
                f"--index {args.index} outside tier {tier} "
                f"({len(runs)} runs)",
            )
        runs = [runs[args.index]]
    return runs


def _run_one(
    spec: dict[str, Any], args: argparse.Namespace,
    natural_history_clock: str | None,
) -> dict[str, Any]:
    _apply_overrides(spec, args)
    return run_spec(
        spec, pathogen_id=args.pathogen_id,
        natural_history_clock=natural_history_clock,
    )


def _report_zip(
    tag: str, tier: str, run_id: str, payload: dict[str, Any],
    zip_path: Path,
) -> None:
    venue = payload["venue"]
    print(
        f"{tag} {tier} {run_id}: ignited={venue['ignited']} "
        f"acquired={venue['n_acquired']} emits={venue['n_emesis_emitted']} "
        f"unattributed={venue['n_unattributed']} -> {zip_path}",
        flush=True,
    )


def _main_manifest(args: argparse.Namespace) -> None:
    manifest = _load_manifest(args.manifest)
    out_dir = Path(
        prepare_output_directory(str(args.out), allowed_roots=(str(REPO_ROOT),)),
    )
    clock = manifest.get("natural_history_clock")
    for run_id, spec in _select_runs(manifest, args.tier, args):
        payload = _run_one(spec, args, clock)
        zip_path = _write_run_zip(out_dir, args.tier, run_id, payload)
        _report_zip("cell", args.tier, run_id, payload, zip_path)


def _main_spec_json(args: argparse.Namespace) -> None:
    safe = Path(
        resolve_repo_path(str(REPO_ROOT), str(args.spec_json)),
    )
    with validated_open(
        safe, "r", allowed_roots=(str(REPO_ROOT),), encoding="utf-8",
    ) as handle:
        spec = json.load(handle)
    if args.epochs_override is not None:
        spec["run"]["num_epochs"] = int(args.epochs_override)
    _apply_overrides(spec, args)
    payload = run_spec(
        spec, pathogen_id=args.pathogen_id,
        natural_history_clock=spec.get("natural_history_clock"),
    )
    tier = args.tier or "spec"
    run_id = args.out_name or str(spec.get("description", "spec"))
    out_dir = Path(
        prepare_output_directory(str(args.out), allowed_roots=(str(REPO_ROOT),)),
    )
    zip_path = _write_run_zip(out_dir, tier, run_id, payload)
    _report_zip("spec-json", tier, run_id, payload, zip_path)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.manifest is None:
        _main_spec_json(args)
    else:
        _main_manifest(args)


if __name__ == "__main__":
    main()
