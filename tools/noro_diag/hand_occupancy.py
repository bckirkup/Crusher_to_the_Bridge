#!/usr/bin/env python3
"""Hand-reservoir occupancy census, ledger NORO-HAND-STATIONARY-01.

The question the ledger freezes: as shipped, does the hand reservoir occupy
the load the mechanism was built from — Liu 2013's infected-subject rinse
distribution (25.4% of rinse-days positive at LOD 2.15 log10) — or does the
spike-and-crash decay leave the hand at measurable load so rarely that the
mechanism under-occupies its own anchor?

One row per ``_replenish_hand`` call that touches the counted pathogen and
matters (the host is shedding, carried a load in, or already has a hand
record), so the row set is the shedding host-epoch census plus the decay tail.
Each row carries the entry load, the post-replenish load, the defecation-event
flag, the first-seen stationary initialisation, the per-host propensity and
inactivation rate, the symptomatic/confinement flags, and the call site
(fomite vs food path) -- and the end-of-epoch post-hygiene load appended by
the ``_apply_hand_hygiene`` wrapper, which is the point-in-time analogue of
Liu's rinse sample.

The instrument is read-only: wrappers call the originals first (through any
wrapper the host driver already installed) and only read engine state.
``get_pathogen_hand_target`` and ``_symptomatic_phase``-family reads consume
no RNG, so this module never perturbs the draw stream -- verified per cell by
the ``--verify-draws`` fingerprint check, not asserted.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any

from engines import transmission_core as tc

# Liu 2013 rinse LOD, log10 copies per hand (register tranche 40).
LIU_LOD_LOG10 = 2.15
LIU_LOD_GEC = 10.0 ** LIU_LOD_LOG10


@dataclass
class OccupancyRecorder:
    """Everything the hand-occupancy census collected on one voyage."""

    pathogen_id: str
    epoch: int = -1
    rows: list[dict[str, Any]] = field(default_factory=list)
    # (epoch, agent_id) -> index of the host's most recent row this epoch,
    # so the end-of-epoch hygiene load lands on the row it belongs to.
    row_index: dict[tuple[int, int], int] = field(default_factory=dict)
    # Transient state for the replenish call currently in flight; the
    # sub-wrappers fill these and the replenish wrapper files the row.
    _current: dict[str, Any] | None = None
    _stool_outcome: bool | None = None
    _events_per_day: float | None = None
    _stationary: float | None = None
    _propensity: float | None = None
    counters: dict[str, int] = field(
        default_factory=lambda: {
            "replenish_calls": 0,
            "continuous_path_calls": 0,
            "rows_recorded": 0,
            "stool_calls": 0,
            "stool_events": 0,
            "stationary_inits": 0,
            "propensity_draws": 0,
            "propensity_cache_hits": 0,
            "hygiene_calls": 0,
        },
    )


def _call_site() -> str:
    """The engine function that called the wrapped method."""
    frame = sys._getframe(1)
    return str(frame.f_code.co_name)


def _symptomatic(agent: Any, pathogen_id: str) -> bool:
    infection = (agent.infections or {}).get(pathogen_id)
    return bool(
        infection is not None
        and infection.get("illness") == tc.IllnessStatus.SYMPTOMATIC
    )


def _stamp_epoch(core_cls: type, rec: OccupancyRecorder) -> dict[str, Any]:
    """Epoch stamps only -- the pathways are the epoch boundaries."""
    originals = {
        "_pathway_fomite": core_cls._pathway_fomite,
        "_pathway_food_contamination": core_cls._pathway_food_contamination,
    }

    def pathway_fomite(
        self: Any, epoch: int, *args: Any, **kwargs: Any,
    ) -> Any:
        rec.epoch = int(epoch)
        return originals["_pathway_fomite"](self, epoch, *args, **kwargs)

    def pathway_food(
        self: Any, epoch: int, *args: Any, **kwargs: Any,
    ) -> Any:
        rec.epoch = int(epoch)
        return originals["_pathway_food_contamination"](
            self, epoch, *args, **kwargs,
        )

    core_cls._pathway_fomite = pathway_fomite
    core_cls._pathway_food_contamination = pathway_food
    return originals


def _wrap_replenish(core_cls: type, rec: OccupancyRecorder) -> dict[str, Any]:
    """One occupancy row per replenish call that involves the reservoir."""
    originals = {
        "_replenish_hand": core_cls._replenish_hand,
        "_stool_event_occurs": core_cls._stool_event_occurs,
        "_stationary_hand_load": core_cls._stationary_hand_load,
        "_hand_carriage_propensity": core_cls._hand_carriage_propensity,
        "_apply_hand_hygiene": core_cls._apply_hand_hygiene,
    }

    def stool_event(self: Any, events_per_day: float) -> bool:
        occurred = originals["_stool_event_occurs"](self, events_per_day)
        if rec._current is not None:
            rec.counters["stool_calls"] += 1
            rec.counters["stool_events"] += int(bool(occurred))
            rec._stool_outcome = bool(occurred)
            rec._events_per_day = float(events_per_day)
        return occurred

    def stationary(
        self: Any,
        target: float,
        inactivation_rate_per_hour: float,
        events_per_day: float,
    ) -> float:
        value = originals["_stationary_hand_load"](
            self, target, inactivation_rate_per_hour, events_per_day,
        )
        if rec._current is not None:
            rec.counters["stationary_inits"] += 1
            rec._stationary = float(value)
        return value

    def propensity(self: Any, agent: Any, pathogen_id: str) -> float:
        existed = pathogen_id in (
            agent.hand_carriage_propensity_by_pathogen or {}
        )
        value = originals["_hand_carriage_propensity"](
            self, agent, pathogen_id,
        )
        if rec._current is not None and pathogen_id == rec.pathogen_id:
            rec._propensity = float(value)
            key = "propensity_cache_hits" if existed else "propensity_draws"
            rec.counters[key] += 1
        return value

    def replenish(
        self: Any,
        agent: Any,
        pathogen_id: str,
        profile: dict | None,
        zone_name: str | None = None,
    ) -> None:
        if pathogen_id != rec.pathogen_id:
            originals["_replenish_hand"](
                self, agent, pathogen_id, profile, zone_name,
            )
            return
        rec.counters["replenish_calls"] += 1
        present = pathogen_id in (agent.hand_load_by_pathogen or {})
        load_entry = float(
            agent.hand_load_by_pathogen.get(pathogen_id, 0.0)
        )
        rec._current = {
            "agent_id": int(agent.agent_id),
            "epoch": rec.epoch,
            "call_site": _call_site(),
            "zone_name": zone_name,
            "first_seen": not present,
            "load_entry_gec": load_entry,
        }
        rec._stool_outcome = None
        rec._events_per_day = None
        rec._stationary = None
        rec._propensity = None
        try:
            originals["_replenish_hand"](
                self, agent, pathogen_id, profile, zone_name,
            )
        finally:
            row = rec._current
            rec._current = None
        if row is None:
            return
        target = float(
            agent.get_pathogen_hand_target(pathogen_id, profile or {})
        )
        load_post = float(
            agent.hand_load_by_pathogen.get(pathogen_id, 0.0)
        )
        # Keep the row only when the reservoir did work this call: the host
        # is shedding (target > 0), carried load in, or already had a record.
        if not (target > 0.0 or load_entry > 0.0 or present):
            return
        row.update({
            "target_gec": target,
            "shedding": target > 0.0,
            "symptomatic": _symptomatic(agent, pathogen_id),
            "confined": bool(self._cabin_confinement_active(agent)),
            "load_post_replenish_gec": load_post,
            "at_target": target > 0.0 and load_post >= target,
            "underflowed": target > 0.0 and load_post <= target * 1e-6,
            "stool_event": rec._stool_outcome,
            "events_per_day_thinned": rec._events_per_day,
            "event_path": rec._stool_outcome is not None,
            "stationary_init_gec": rec._stationary,
            "propensity": rec._propensity,
            "inactivation_rate_per_hour": (
                agent.hand_inactivation_rate_by_pathogen.get(pathogen_id)
            ),
            # NORO-HAND-PRACTICE-01 witness: the epoch's deposit-side
            # drying blend under hygiene_cycle (None on every other arm).
            "hand_wet_transfer": (
                agent.hand_wet_transfer_by_pathogen.get(pathogen_id)
            ),
            "hygiene_calls": 0,
            "load_end_epoch_gec": None,
        })
        key = (row["epoch"], row["agent_id"])
        rec.row_index[key] = len(rec.rows)
        rec.rows.append(row)
        rec.counters["rows_recorded"] += 1
        if rec._stool_outcome is None:
            rec.counters["continuous_path_calls"] += 1

    def apply_hygiene(
        self: Any, agent: Any, pathogen_id: str, profile: dict | None,
    ) -> None:
        originals["_apply_hand_hygiene"](self, agent, pathogen_id, profile)
        if pathogen_id != rec.pathogen_id:
            return
        index = rec.row_index.get((rec.epoch, int(agent.agent_id)))
        if index is None:
            return
        rec.counters["hygiene_calls"] += 1
        row = rec.rows[index]
        row["hygiene_calls"] += 1
        row["load_end_epoch_gec"] = float(
            agent.hand_load_by_pathogen.get(pathogen_id, 0.0)
        )

    core_cls._replenish_hand = replenish
    core_cls._stool_event_occurs = stool_event
    core_cls._stationary_hand_load = stationary
    core_cls._hand_carriage_propensity = propensity
    core_cls._apply_hand_hygiene = apply_hygiene
    return originals


def install(core_cls: type, rec: OccupancyRecorder) -> dict[str, Any]:
    """Wrap the hand-reservoir methods; returns originals for restore.

    Installed *inside* the host driver's ``instrumented()`` so a driver's own
    pre-existing wrappers (fomite_mass_balance's hand witness) stay in the
    call chain: these wrappers call whichever method was bound at install
    time, and the driver's counters still see every call.
    """
    originals = _stamp_epoch(core_cls, rec)
    originals.update(_wrap_replenish(core_cls, rec))
    return originals


def summarise(rec: OccupancyRecorder) -> dict[str, Any]:
    """The occupancy payload a dump carries."""
    shedding = [row for row in rec.rows if row["shedding"]]
    positive = [
        row for row in shedding
        if (row["load_end_epoch_gec"] or 0.0) >= LIU_LOD_GEC
    ]
    missing_end = [row for row in shedding if row["load_end_epoch_gec"] is None]
    return {
        "counters": dict(rec.counters),
        "shedding_rows": len(shedding),
        "end_load_missing_rows": len(missing_end),
        "positive_rows": len(positive),
        "positive_share": (
            len(positive) / len(shedding) if shedding else None
        ),
        "lod_log10": LIU_LOD_LOG10,
    }
