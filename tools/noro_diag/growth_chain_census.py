#!/usr/bin/env python3
"""Link-by-link census of the norovirus propagation chain, for NORO-GROWTH-01.

Purpose
-------
NORO-DOSE-REFIT-01 showed emesis ignition works (per-voyage P(ignite) ~0.37 on
the spirit cell) and converts to ~0.9 secondaries per ignited voyage, but
growth never compounds. This instrument measures which link in

    secondary case -> sheds -> deposits -> picked up -> tertiary infection

carries ~zero on ignited ``fl_spr_12d`` voyages. For every infected host it
records generation (import vs challenge-acquired, recursively from the
transmission-event pedigree), its emit/deposit record (emesis schedule and
emits, stool events, shedding-curve emission, deposits by destination), and
for every susceptible the delivered mass reaching its hand split by channel
(zone pool / emesis patch / sanitary venue / hand contact / food) and by the
*source generation* of the mass -- via a proportional per-unit composition
ledger maintained beside the engine's pools.

Method
------
Read-only wrappers on ``TransmissionCore`` for the duration of one run, the
same pattern as ``per_host_dose_challenge``:

* ``draw_emesis_schedule`` (all three module references) and ``_emit_emesis``
  -- per-host emesis schedule and emit records, plus patch ownership: each
  ``EmesisPatch`` gets a ``_growth_depositor`` attribute at filing so its
  delivered mass attributes to the emitting host's generation.
* ``_route_stool_event_venue`` -- one row per defecation event (agent, venue).
* ``_deposit_surface_mass`` / ``_add_food_deposits`` -- depositor recovery by
  bounded frame walk (the caller's ``agent`` local), then a ``unit_mix``
  ledger: each unit's standing mass is apportioned over
  {import, acquired, unknown} source generations, updated on every deposit
  and scaled proportionally on every removal.
* ``_scale_surface_mass`` / ``_roll_up_per_surface_zone`` /
  ``_scale_emesis_patch`` / ``_grow_food_pool`` / ``_consume_surface_mass`` --
  removal bookkeeping by call-site (pickup consume vs routine cleaning vs
  outbreak disinfection vs per-epoch survival decay), so a zero link
  distinguishes "gate deleted the mass" from "declared constants attenuated
  it".
* ``pickup_gate_open`` (module-level) -- every gate decision with the calling
  site and the pool mass it saw, so a sub-``SURFACE_PICKUP_MIN_GEC`` pool
  reads as a measured gate closure rather than an absence of calls.
* ``_fomite_zone_pickup`` -- per call, the unit's mass, its composition, the
  occupant and susceptible counts, and the gate state: the presence/timing
  half of link 3.
* ``_emesis_patch_pickup_one`` -- patch context (depositor gen, footprint
  share, susceptible count, requester count via
  ``_fomite_pickup_request_for_area`` calls made inside it).
* ``_deliver_one_pickup`` -- per-target delivered mass and hand->mouth dose
  for the zone-pool, patch, and sanitary by-class paths, attributed to
  source generations through the unit mix or the patch owner.
* ``_deliver_sanitary_pooled_requests`` -- the same join for the pooled
  sanitary path, which inlines the delivery rather than calling
  ``_deliver_one_pickup``.
* ``_per_partner_contact_dose`` -- the interpersonal hand->hand channel,
  with the donor list it moved mass from.
* ``_food_ingestion`` -- the food channel's per-susceptible dose.
* ``_dose_response_hazard`` and ``_resolve_pathogen_challenge`` -- evaluated
  hazard per challenge (susceptibility x effective dose) and the resulting
  acquisition pedigree (``TransmissionEvent.source_agent_id`` /
  ``source_strain_id``), so generation is measured from the engine's own
  source draw, not inferred from timing.

Wrappers only read; the per-unit composition ledger is observer-side
bookkeeping that follows the engine's own proportional scaling convention.
Nothing here draws from the engine's RNG streams.

Inputs
------
``--manifest``/``--tier``/``--index``/``--seeds`` run the verbatim campaign
mode: one spec generated from the manifest tier exactly as Batch would run
it (NORO-DOSE-REFIT-01's ``fl_spr_12d`` cell is the canary target). Ignition
is *measured*, not assumed -- the output rows let the readout condition on
the emesis emit record rather than the seed.

Outputs
-------
One ``<run_id>.zip`` per run in campaign layout: ``summary.json`` (small)
and ``growth_census.json.gz`` (the full per-link payload, gzipped because
the per-epoch tables carry keys the repository's unit-safety guard reads as
undeclared time units in plain ``.json``).

Nothing here fits or selects a parameter value.
"""

from __future__ import annotations

import argparse
import gzip
import inspect
import json
import sys
import tempfile
import time
import zipfile
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines import initiation as initiation_module  # noqa: E402
from engines import natural_history as natural_history_module  # noqa: E402
from engines import transmission_core as tc  # noqa: E402
from picard_framework.run_spec import PicardRunSpec  # noqa: E402
from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_child_path,
    resolve_repo_path,
    validated_open,
)

_CAMPAIGN_DIR = (
    REPO_ROOT / "picard_framework" / "runs" / "mega_cruise_campaign"
)
if str(_CAMPAIGN_DIR) not in sys.path:
    sys.path.insert(0, str(_CAMPAIGN_DIR))

from campaign_runner import generate_tier_runs  # noqa: E402

# Source-generation classes. ``import`` covers explicit seeds and boarding
# (resident-at-epoch-0) infections; ``acquired`` covers anything established
# by a challenge draw, with ``generation`` from the source pedigree.
GEN_IMPORT = "import"
GEN_ACQUIRED = "acquired"
GEN_UNKNOWN = "unknown"

# Generation for an acquired host whose parent could not be resolved.
GEN_UNRESOLVED = 99_999

# Depositor recovery: how far above ``_deposit_surface_mass`` an ``agent``
# local is allowed to sit before the deposit is classed unknown.
_FRAME_WALK_LIMIT = 8

_DEPOSIT_CALLSITES = (
    "_shedder_surface_deposits",
    "_sanitary_venue_deposits",
    "_legacy_fomite_deposits",
)
_REMOVAL_CALLSITES = {
    "_consume_surface_mass": "pickup_consume",
    "_routine_cleaning_event": "routine_cleaning",
    "_disinfect_zone_pools": "outbreak_disinfection",
    "_disinfect_zone": "outbreak_disinfection",
    "_update_surface_pools": "survival_decay",
    "_roll_up_per_surface_zone": "per_surface_rollup",
    "_consume_surface_mass_by_class": "pickup_consume",
}
_PATCH_REMOVAL_CALLSITES = {
    "_routine_cleaning_event": "routine_cleaning",
    "_disinfect_zone": "outbreak_disinfection",
    "_update_surface_pools": "survival_decay",
}
_GATE_CALLERS = (
    "_fomite_zone_pickup",
    "_sanitary_pickup_pooled",
    "_sanitary_pickup_by_class",
    "_pathway_fomite_legacy_default",
)


def _gen_class(gen: int | None) -> str:
    if gen is None or gen < 0 or gen >= GEN_UNRESOLVED:
        return GEN_UNKNOWN
    return GEN_IMPORT if gen == 0 else GEN_ACQUIRED


@dataclass
class CensusRecorder:
    """Every observation taken from one instrumented voyage."""

    pathogen_id: str
    profile: dict[str, Any] = field(default_factory=dict)
    # host -> generation (0 = import); filled lazily as hosts appear.
    host_gen: dict[int, int] = field(default_factory=dict)
    # strain_id -> first host carrying it; resolves source-less pedigrees.
    strain_home: dict[str, int] = field(default_factory=dict)
    seed_ids: set[int] = field(default_factory=set)
    import_ids: set[int] = field(default_factory=set)
    acquired_ids: set[int] = field(default_factory=set)
    epoch0_snapshotted: bool = False
    # Per-host census (infected hosts only).
    hosts: dict[int, dict[str, Any]] = field(default_factory=dict)
    # Live per-unit source-generation composition (observer-side mirrors of
    # ``surface_pools_by_pathogen`` / ``food_pools``).
    unit_mix: dict[str, dict[str, float]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(float)),
    )
    food_mix: dict[str, dict[str, float]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(float)),
    )
    # Delivery context stacks for the pickup-channel tag.
    channel_stack: list[tuple[str, str]] = field(default_factory=list)
    sanitary_ctx: dict[int, tuple[float, str]] = field(default_factory=dict)
    patch_ctx: dict[str, Any] | None = None
    # Row tables.
    deposit_rows: list[dict[str, Any]] = field(default_factory=list)
    emit_rows: list[dict[str, Any]] = field(default_factory=list)
    stool_rows: list[dict[str, Any]] = field(default_factory=list)
    gate_rows: list[dict[str, Any]] = field(default_factory=list)
    gate_open_by_caller: dict[str, int] = field(
        default_factory=lambda: defaultdict(int),
    )
    unit_epoch_rows: list[dict[str, Any]] = field(default_factory=list)
    pickup_rows: list[dict[str, Any]] = field(default_factory=list)
    dose_rows: list[dict[str, Any]] = field(default_factory=list)
    hazard_rows: list[dict[str, Any]] = field(default_factory=list)
    acquisition_rows: list[dict[str, Any]] = field(default_factory=list)
    contact_rows: list[dict[str, Any]] = field(default_factory=list)
    food_rows: list[dict[str, Any]] = field(default_factory=list)
    patch_rows: list[dict[str, Any]] = field(default_factory=list)
    patch_sweep_rows: list[dict[str, Any]] = field(default_factory=list)
    removal_totals: dict[str, dict[str, float]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(float)),
    )
    census_rows: list[dict[str, Any]] = field(default_factory=list)
    hazard_witness: tuple[int, str, float, float, float] | None = None

    def gen_of(self, agent_id: int | None) -> int:
        if agent_id is None:
            return -1
        return self.host_gen.get(int(agent_id), -1)

    def gen_class_of(self, agent_id: int | None) -> str:
        """import/acquired/unknown by membership -- immune to strain
        pedigree gaps (an unresolved draw still mints an acquired host)."""
        if agent_id is None:
            return GEN_UNKNOWN
        aid = int(agent_id)
        if aid in self.acquired_ids:
            return GEN_ACQUIRED
        if aid in self.import_ids:
            return GEN_IMPORT
        return GEN_UNKNOWN

    def host_row(self, agent: Any) -> dict[str, Any]:
        aid = int(agent.agent_id)
        row = self.hosts.get(aid)
        if row is None:
            row = {
                "agent_id": aid,
                "gen": self.gen_of(aid),
                "infected_epochs": 0,
                "symptomatic_epochs": 0,
                "confined_epochs": 0,
                "shedding_gec": 0.0,
                "shedding_epochs": 0,
                "hand_peak_gec": 0.0,
                "emesis_scheduled": 0,
                "emesis_emitted": 0,
                "emesis_surface_gec": 0.0,
                "emesis_patch_gec": 0.0,
                "emesis_aerosol_gec": 0.0,
                "emesis_censored": False,
                "vomiting_axis": False,
                "stool_events": 0,
                "deposit_gec": 0.0,
            }
            self.hosts[aid] = row
        return row


def _frame_probe(depth_limit: int = _FRAME_WALK_LIMIT) -> dict[str, Any]:
    """Nearest enclosing ``agent`` local / epoch / recognised callsite.

    One bounded walk recovers what the wrapped callee's signature does not
    carry: who deposited the mass, which epoch it is, and which engine
    function made the call (for removal cause attribution).
    """
    out: dict[str, Any] = {
        "agent": None, "epoch": None, "callsite": "other", "unit": None,
    }
    frame = inspect.currentframe()
    try:
        frame = frame.f_back if frame is not None else None
        depth = 0
        while frame is not None and depth < depth_limit:
            frame = frame.f_back
            depth += 1
            if frame is None:
                break
            if out["agent"] is None:
                agent = frame.f_locals.get("agent")
                if hasattr(agent, "agent_id"):
                    out["agent"] = agent
            if out["epoch"] is None:
                epoch = frame.f_locals.get("epoch")
                if isinstance(epoch, int):
                    out["epoch"] = int(epoch)
            if out["unit"] is None:
                for key in ("zone_name", "unit_name", "venue"):
                    unit = frame.f_locals.get(key)
                    if isinstance(unit, str):
                        out["unit"] = unit
                        break
            name = frame.f_code.co_name
            if name in _DEPOSIT_CALLSITES or name in _REMOVAL_CALLSITES or (
                name in _PATCH_REMOVAL_CALLSITES or name in _GATE_CALLERS
            ):
                if out["callsite"] == "other":
                    out["callsite"] = name
        return out
    finally:
        del frame


def _mix_add(
    mix: dict[str, dict[str, float]], unit: str, gen_class: str, mass: float,
) -> None:
    mix[unit][gen_class] = mix[unit].get(gen_class, 0.0) + mass


def _mix_scale(
    mix: dict[str, dict[str, float]], unit: str, factor: float,
) -> dict[str, float]:
    """Scale a unit's composition; return per-class removed mass."""
    state = mix.get(unit)
    if not state:
        return {}
    factor = max(0.0, min(1.0, factor))
    removed: dict[str, float] = {}
    for gen_class, mass in list(state.items()):
        kept = mass * factor
        removed[gen_class] = mass - kept
        state[gen_class] = kept
    return removed


def _mix_fractions(
    mix: dict[str, dict[str, float]], unit: str,
) -> dict[str, float]:
    state = mix.get(unit) or {}
    total = sum(state.values())
    if total <= 0.0:
        return {}
    return {gen_class: mass / total for gen_class, mass in state.items()}


def _scale_mix(
    rec: CensusRecorder,
    mix: dict[str, dict[str, float]],
    unit: str,
    factor: float,
    cause: str,
) -> None:
    for gen_class, removed in _mix_scale(mix, unit, factor).items():
        if removed > 0.0:
            rec.removal_totals[cause][gen_class] += removed


def _wrap_schedule_module(module: Any, rec: CensusRecorder) -> Any:
    original = module.draw_emesis_schedule

    def wrapper(agent: Any, pathogen_id: str, *args: Any, **kwargs: Any) -> Any:
        result = original(agent, pathogen_id, *args, **kwargs)
        if pathogen_id == rec.pathogen_id:
            schedule = getattr(
                agent, "emesis_episode_schedule_by_pathogen", {},
            ).get(pathogen_id, [])
            row = rec.host_row(agent)
            row["emesis_scheduled"] += len(schedule)
            infection = (getattr(agent, "infections", {}) or {}).get(
                pathogen_id,
            ) or {}
            row["vomiting_axis"] = bool(
                tc.has_symptom_axis(infection, tc.VOMITING_AXIS),
            )
            row["emesis_censored"] = bool(
                getattr(
                    agent, "emesis_censored_below_lod_by_pathogen", {},
                ).get(pathogen_id, False),
            )
        return result

    return wrapper


def _tag_new_patches(
    core: Any, pathogen_id: str, zone_name: str, before: int, agent: Any,
) -> None:
    patches = (
        core.emesis_patch_pools_by_pathogen.get(pathogen_id, {})
        .get(zone_name, [])
    )
    for patch in patches[before:]:
        patch._growth_depositor = int(agent.agent_id)


def _wrap_emit_emesis(core_cls: type, rec: CensusRecorder) -> Any:
    original = core_cls._emit_emesis

    def wrapper(
        self: Any, agent: Any, pathogen_id: str, profile: dict,
        zone_name: str, epoch: int,
    ) -> float:
        # NB: the engine creates this list via setdefault *inside* the call,
        # so it must be re-fetched afterwards — a pre-call .get() misses the
        # host's first emit entirely.
        before = len(
            agent.emesis_deposition_records_by_pathogen.get(
                pathogen_id, [],
            ),
        )
        patch_before = len(
            self.emesis_patch_pools_by_pathogen.get(pathogen_id, {})
            .get(zone_name, []),
        )
        pool_gain = original(
            self, agent, pathogen_id, profile, zone_name, epoch,
        )
        _tag_new_patches(self, pathogen_id, zone_name, patch_before, agent)
        if pathogen_id != rec.pathogen_id:
            return pool_gain
        row = rec.host_row(agent)
        for record in agent.emesis_deposition_records_by_pathogen.get(
            pathogen_id, [],
        )[before:]:
            row["emesis_emitted"] += 1
            row["emesis_surface_gec"] += float(record.get("surface_load", 0.0))
            row["emesis_aerosol_gec"] += float(record.get("aerosol_load", 0.0))
            rec.emit_rows.append({
                "epoch": int(epoch),
                "agent_id": int(agent.agent_id),
                "gen": rec.gen_of(int(agent.agent_id)),
                "gen_class": rec.gen_class_of(int(agent.agent_id)),
                "zone": zone_name,
                "episode_load": float(record.get("episode_load", 0.0)),
                "surface_load": float(record.get("surface_load", 0.0)),
                "aerosol_load": float(record.get("aerosol_load", 0.0)),
                "pool_gain": float(record.get("pool_gain", 0.0)),
                "non_touchable": float(record.get("non_touchable", 0.0)),
                "censored_below_lod": bool(
                    record.get("censored_below_lod", False),
                ),
            })
        row["emesis_patch_gec"] += float(pool_gain)
        return pool_gain

    return wrapper


def _patch_gen(rec: CensusRecorder, patch: Any) -> str:
    return rec.gen_class_of(getattr(patch, "_growth_depositor", None))


def _wrap_deposit_surface_mass(core_cls: type, rec: CensusRecorder) -> Any:
    original = core_cls._deposit_surface_mass

    def wrapper(
        self: Any, pathogen_id: str, zone_name: str, mass: float,
    ) -> None:
        original(self, pathogen_id, zone_name, mass)
        if pathogen_id != rec.pathogen_id or mass <= 0.0:
            return
        probe = _frame_probe()
        agent = probe["agent"]
        gen_class = rec.gen_class_of(
            int(agent.agent_id) if agent is not None else None,
        )
        _mix_add(rec.unit_mix, zone_name, gen_class, mass)
        if agent is not None:
            rec.host_row(agent)["deposit_gec"] += float(mass)
        rec.deposit_rows.append({
            "epoch": probe["epoch"],
            "unit": zone_name,
            "depositor": (
                int(agent.agent_id) if agent is not None else None
            ),
            "gen_class": gen_class,
            "callsite": probe["callsite"],
            "mass": float(mass),
        })

    return wrapper


def _wrap_scale_surface_mass(core_cls: type, rec: CensusRecorder) -> Any:
    original = core_cls._scale_surface_mass

    def wrapper(
        self: Any, pathogen_id: str, zone_name: str, factor: float,
    ) -> None:
        if pathogen_id == rec.pathogen_id:
            probe = _frame_probe()
            caller = probe["callsite"]
            _scale_mix(
                rec, rec.unit_mix, zone_name, factor,
                _REMOVAL_CALLSITES.get(caller, caller),
            )
        original(self, pathogen_id, zone_name, factor)

    return wrapper


def _wrap_roll_up(core_cls: type, rec: CensusRecorder) -> Any:
    original = core_cls._roll_up_per_surface_zone

    def wrapper(
        self: Any, pathogen_id: str, zone_name: str,
        previous_total: float, retention: float, **kwargs: Any,
    ) -> float:
        if pathogen_id == rec.pathogen_id:
            _scale_mix(
                rec, rec.unit_mix, zone_name, retention, "per_surface_rollup",
            )
        return original(
            self, pathogen_id, zone_name, previous_total, retention, **kwargs,
        )

    return wrapper


def _wrap_scale_emesis_patch(core_cls: type, rec: CensusRecorder) -> Any:
    original = core_cls._scale_emesis_patch

    def wrapper(self: Any, patch: Any, factor: float) -> float:
        before = float(patch.mass)
        kept = original(self, patch, factor)
        removed = before - float(kept)
        if removed > 0.0:
            probe = _frame_probe()
            caller = probe["callsite"]
            cause = _PATCH_REMOVAL_CALLSITES.get(caller, "survival_decay")
            rec.removal_totals[f"patch_{cause}"][_patch_gen(rec, patch)] += (
                removed
            )
        return kept

    return wrapper


def _wrap_stool_venue(core_cls: type, rec: CensusRecorder) -> Any:
    original = core_cls._route_stool_event_venue

    def wrapper(
        self: Any, agent: Any, pathogen_id: str, profile: Any,
        zone_name: str | None,
    ) -> None:
        original(self, agent, pathogen_id, profile, zone_name)
        if pathogen_id != rec.pathogen_id:
            return
        venue = (
            self._sanitary_venue(zone_name, agent)
            if zone_name is not None
            else None
        )
        rec.host_row(agent)["stool_events"] += 1
        rec.stool_rows.append({
            "epoch": _frame_probe()["epoch"],
            "agent_id": int(agent.agent_id),
            "gen": rec.gen_of(int(agent.agent_id)),
            "gen_class": rec.gen_class_of(int(agent.agent_id)),
            "zone": zone_name,
            "venue": venue,
        })

    return wrapper


def _wrap_pickup_gate(rec: CensusRecorder) -> Any:
    original = tc.pickup_gate_open

    def wrapper(surface_mass: float) -> bool:
        open_ = original(surface_mass)
        # Opens are the common case -- count them. Closes are the
        # mechanism evidence: which unit held how much sub-gate mass.
        if open_:
            probe = _frame_probe(depth_limit=6)
            rec.gate_open_by_caller[probe["callsite"]] += 1
            return open_
        probe = _frame_probe(depth_limit=6)
        rec.gate_rows.append({
            "epoch": probe["epoch"],
            "caller": probe["callsite"],
            "unit": probe["unit"],
            "mass": float(surface_mass),
        })
        return open_

    return wrapper


def _current_channel(rec: CensusRecorder) -> tuple[str, str]:
    return rec.channel_stack[-1] if rec.channel_stack else ("other", "")


def _record_pickup(
    rec: CensusRecorder, target: Any, delivered: float, unit: str,
    dose: float,
) -> None:
    channel, _ = _current_channel(rec)
    if channel == "patch" and rec.patch_ctx:
        source_share = {_patch_gen(rec, rec.patch_ctx["patch"]): 1.0}
    else:
        source_share = _mix_fractions(rec.unit_mix, unit)
    rec.pickup_rows.append({
        "epoch": _frame_probe()["epoch"],
        "target": int(target.agent_id),
        "unit": unit,
        "channel": channel,
        "delivered": float(delivered),
        "dose": float(dose),
        "source_acquired_share": source_share.get(GEN_ACQUIRED, 0.0),
        "source_import_share": source_share.get(GEN_IMPORT, 0.0),
    })


def _wrap_fomite_zone_pickup(core_cls: type, rec: CensusRecorder) -> Any:
    original = core_cls._fomite_zone_pickup

    def wrapper(
        self: Any, zone_name: str, occupants: list, epoch: int,
        agent_doses: dict, matrix: Any, agent_pathway_doses: Any,
        pathogen_id: str, ledger: Any,
    ) -> None:
        if pathogen_id != rec.pathogen_id:
            return original(
                self, zone_name, occupants, epoch, agent_doses, matrix,
                agent_pathway_doses, pathogen_id, ledger,
            )
        path_pools = self.surface_pools_by_pathogen.get(pathogen_id)
        surface_mass = (
            path_pools.get(zone_name, 0.0)
            if path_pools is not None
            else self.surface_pools.get(zone_name, 0.0)
        )
        if surface_mass > 0.0:
            susceptible = self._get_susceptible(occupants, pathogen_id)
            rec.unit_epoch_rows.append({
                "epoch": int(epoch),
                "unit": zone_name,
                "surface_mass": float(surface_mass),
                "mass_acquired": rec.unit_mix.get(
                    zone_name, {},
                ).get(GEN_ACQUIRED, 0.0),
                "occupants": len(occupants),
                "susceptible": len(susceptible),
            })
        rec.channel_stack.append(("zone_pool", zone_name))
        try:
            original(
                self, zone_name, occupants, epoch, agent_doses, matrix,
                agent_pathway_doses, pathogen_id, ledger,
            )
        finally:
            rec.channel_stack.pop()

    return wrapper


def _wrap_patch_sweep(core_cls: type, rec: CensusRecorder) -> Any:
    """Per-patch-unit census at each sweep -- counts the case the pickup
    row stream cannot see: patches sitting in units with zero susceptible
    occupants (the early-continue path)."""
    original = core_cls._emesis_patch_pickup

    def wrapper(
        self: Any, epoch: int, pickup_units: dict, pathogen_id: str,
        *args: Any, **kwargs: Any,
    ) -> None:
        if pathogen_id == rec.pathogen_id:
            patches_by_unit = self.emesis_patch_pools_by_pathogen.get(
                pathogen_id, {},
            )
            for unit_name, occupants in pickup_units.items():
                patches = patches_by_unit.get(unit_name)
                if not patches:
                    continue
                susceptible = self._get_susceptible(
                    occupants, pathogen_id,
                )
                rec.patch_sweep_rows.append({
                    "epoch": int(epoch),
                    "unit": unit_name,
                    "n_patches": len(patches),
                    "patch_mass_gec": sum(
                        float(p.mass) for p in patches
                    ),
                    "depositor_gens": [
                        rec.gen_class_of(
                            getattr(p, "_growth_depositor", None),
                        )
                        for p in patches
                    ],
                    "occupants": len(occupants),
                    "susceptible": len(susceptible),
                })
        return original(self, epoch, pickup_units, pathogen_id, *args, **kwargs)

    return wrapper


def _wrap_patch_pickup_one(core_cls: type, rec: CensusRecorder) -> Any:
    original = core_cls._emesis_patch_pickup_one

    def wrapper(
        self: Any, patch: Any, susceptible: list, unit_name: str,
        epoch: int, prev_occupant_ids: set, prev_shedders: list,
        agent_doses: dict, matrix: Any, agent_pathway_doses: Any,
        pathogen_id: str, surface_attribution: Any,
    ) -> float:
        if pathogen_id != rec.pathogen_id:
            return original(
                self, patch, susceptible, unit_name, epoch,
                prev_occupant_ids, prev_shedders, agent_doses, matrix,
                agent_pathway_doses, pathogen_id, surface_attribution,
            )
        rec.patch_ctx = {
            "patch": patch,
            "depositor": getattr(patch, "_growth_depositor", None),
            "occupant_share": float(patch.occupant_share),
            "mass_before": float(patch.mass),
            "n_susceptible": len(susceptible),
            "n_requests": 0,
        }
        rec.channel_stack.append(("patch", unit_name))
        try:
            delivered = original(
                self, patch, susceptible, unit_name, epoch,
                prev_occupant_ids, prev_shedders, agent_doses, matrix,
                agent_pathway_doses, pathogen_id, surface_attribution,
            )
        finally:
            rec.channel_stack.pop()
        rec.removal_totals["patch_pickup"][_patch_gen(rec, patch)] += float(
            delivered,
        )
        rec.patch_rows.append({
            "epoch": int(epoch),
            "unit": unit_name,
            "depositor": rec.patch_ctx["depositor"],
            "depositor_gen": rec.gen_of(rec.patch_ctx["depositor"]),
            "occupant_share": rec.patch_ctx["occupant_share"],
            "mass_before": rec.patch_ctx["mass_before"],
            "n_susceptible": rec.patch_ctx["n_susceptible"],
            "n_requests": rec.patch_ctx["n_requests"],
            "delivered": float(delivered),
        })
        rec.patch_ctx = None
        return delivered

    return wrapper


def _wrap_pickup_request_for_area(core_cls: type, rec: CensusRecorder) -> Any:
    original = core_cls._fomite_pickup_request_for_area

    def wrapper(*args: Any, **kwargs: Any) -> float:
        request = original(*args, **kwargs)
        if rec.patch_ctx is not None:
            rec.patch_ctx["n_requests"] += 1
        return request

    return wrapper


def _wrap_deliver_one_pickup(core_cls: type, rec: CensusRecorder) -> Any:
    original = core_cls._deliver_one_pickup

    def wrapper(
        self: Any, target: Any, delivered: float, zone_name: str,
        *args: Any, **kwargs: Any,
    ) -> float:
        dose = original(self, target, delivered, zone_name, *args, **kwargs)
        if delivered > 0.0:
            _record_pickup(rec, target, delivered, zone_name, dose)
        return dose

    return wrapper


def _wrap_deliver_sanitary_pooled(core_cls: type, rec: CensusRecorder) -> Any:
    original = core_cls._deliver_sanitary_pooled_requests

    def wrapper(
        self: Any, requests: list, venue: str, surface_mass: float,
        scale: float, epoch: int, agent_doses: dict, matrix: Any,
        agent_pathway_doses: Any, pathogen_id: str,
        surface_attribution: Any,
    ) -> float:
        if pathogen_id == rec.pathogen_id:
            for agent, requested in requests:
                delivered = float(requested) * scale
                if delivered > 0.0:
                    rec.sanitary_ctx[int(agent.agent_id)] = (
                        delivered, venue,
                    )
            rec.channel_stack.append(("sanitary", venue))
        try:
            return original(
                self, requests, venue, surface_mass, scale, epoch,
                agent_doses, matrix, agent_pathway_doses, pathogen_id,
                surface_attribution,
            )
        finally:
            if pathogen_id == rec.pathogen_id:
                rec.channel_stack.pop()
                rec.sanitary_ctx.clear()

    return wrapper


def _wrap_hand_to_mouth(core_cls: type, rec: CensusRecorder) -> Any:
    original = core_cls._hand_to_mouth_dose

    def wrapper(
        self: Any, target: Any, epoch: int, hand_load: float,
        rng: Any = None,
    ) -> float:
        dose = original(self, target, epoch, hand_load, rng)
        channel, _ = _current_channel(rec)
        row = {
            "epoch": int(epoch),
            "target": int(target.agent_id),
            "channel": channel,
            "hand_load": float(hand_load),
            "dose": float(dose),
        }
        if channel == "sanitary":
            delivered, venue = rec.sanitary_ctx.get(
                int(target.agent_id), (0.0, ""),
            )
            row["delivered"] = delivered
            row["unit"] = venue
            row["source_acquired_share"] = _mix_fractions(
                rec.unit_mix, venue,
            ).get(GEN_ACQUIRED, 0.0)
        rec.dose_rows.append(row)
        return dose

    return wrapper


def _wrap_partner_contact(core_cls: type, rec: CensusRecorder) -> Any:
    original = core_cls._per_partner_contact_dose

    def wrapper(
        self: Any, target: Any, sampled_shedders: list,
        cabin_confinement: bool, pathogen_id: str, epoch: int,
    ) -> tuple[float, list]:
        rec.channel_stack.append(("hand_contact", ""))
        try:
            dose, moved = original(
                self, target, sampled_shedders, cabin_confinement,
                pathogen_id, epoch,
            )
        finally:
            rec.channel_stack.pop()
        if pathogen_id == rec.pathogen_id and moved:
            for donor, amount in moved:
                rec.contact_rows.append({
                    "epoch": int(epoch),
                    "target": int(target.agent_id),
                    "donor": int(donor.agent_id),
                    "donor_gen": rec.gen_of(int(donor.agent_id)),
                    "amount": float(amount),
                    "dose": float(dose),
                })
        return dose, moved

    return wrapper


def _wrap_food_deposits(core_cls: type, rec: CensusRecorder) -> Any:
    original = core_cls._food_deposits

    def wrapper(
        self: Any, zone_name: str, *args: Any, **kwargs: Any,
    ) -> list:
        deposits = original(self, zone_name, *args, **kwargs)
        for agent, mass in deposits:
            if mass > 0.0:
                _mix_add(
                    rec.food_mix, zone_name,
                    rec.gen_class_of(int(agent.agent_id)), float(mass),
                )
        return deposits

    return wrapper


def _wrap_food_ingestion(core_cls: type, rec: CensusRecorder) -> Any:
    original = core_cls._food_ingestion

    def wrapper(
        self: Any, zone_name: str, occupants: list, food_zones: dict,
        fc: dict, agent_doses: dict, matrix: Any,
        agent_pathway_doses: Any, pathogen_id: str, ledger: Any,
    ) -> None:
        if pathogen_id != rec.pathogen_id:
            return original(
                self, zone_name, occupants, food_zones, fc, agent_doses,
                matrix, agent_pathway_doses, pathogen_id, ledger,
            )
        pool_before = float(food_zones.get(zone_name, 0.0))
        susceptible = self._get_susceptible(occupants, pathogen_id)
        fractions = _mix_fractions(rec.food_mix, zone_name)
        if pool_before > 0.0 and susceptible:
            rec.food_rows.append({
                "epoch": int(_frame_probe()["epoch"] or 0),
                "zone": zone_name,
                "pool_before": pool_before,
                "susceptible": len(susceptible),
                "source_acquired_share": fractions.get(GEN_ACQUIRED, 0.0),
            })
        original(
            self, zone_name, occupants, food_zones, fc, agent_doses,
            matrix, agent_pathway_doses, pathogen_id, ledger,
        )
        remaining = float(food_zones.get(zone_name, 0.0))
        if pool_before > 0.0:
            _scale_mix(
                rec, rec.food_mix, zone_name,
                remaining / pool_before, "food_eaten",
            )

    return wrapper


def _wrap_grow_food_pool(core_cls: type, rec: CensusRecorder) -> Any:
    original = core_cls._grow_food_pool

    def wrapper(
        self: Any, food_zones: dict, zone_name: str,
        growth_factor: float, decay_factor: float, pathogen_id: str,
    ) -> None:
        if pathogen_id == rec.pathogen_id:
            _scale_mix(
                rec, rec.food_mix, zone_name,
                growth_factor * decay_factor, "food_growth_decay",
            )
        original(
            self, food_zones, zone_name, growth_factor, decay_factor,
            pathogen_id,
        )

    return wrapper


def _wrap_hazard(core_cls: type, rec: CensusRecorder) -> Any:
    original = core_cls._dose_response_hazard

    def wrapper(
        self: Any, agent: Any, pathogen_id: str, effective_dose: float,
    ) -> float:
        hazard = original(self, agent, pathogen_id, effective_dose)
        frailty = float(
            agent.dose_response_susceptibility.get(pathogen_id, 0.0),
        )
        rec.hazard_witness = (
            int(agent.agent_id), str(pathogen_id),
            float(effective_dose), frailty, float(hazard),
        )
        if pathogen_id == rec.pathogen_id:
            rec.hazard_rows.append({
                "epoch": _frame_probe()["epoch"],
                "agent_id": int(agent.agent_id),
                "effective_dose": float(effective_dose),
                "frailty": frailty,
                "hazard": float(hazard),
                "target_gen": rec.gen_of(int(agent.agent_id)),
            })
        return hazard

    return wrapper


def _record_acquisition(
    rec: CensusRecorder, agent: Any, epoch: int, p_dose: float,
    witness: Any, new_events: list,
) -> None:
    event = new_events[-1] if new_events else None
    source_id = getattr(event, "source_agent_id", None) if event else None
    parent_strain = (
        getattr(event, "source_strain_id", None) if event else None
    )
    acquired_strain = (
        (agent.infections.get(rec.pathogen_id) or {}).get("strain_id")
    )
    if source_id is not None:
        gen = rec.gen_of(int(source_id)) + 1
    elif parent_strain and parent_strain in rec.strain_home:
        gen = rec.gen_of(rec.strain_home[parent_strain]) + 1
    elif acquired_strain and str(acquired_strain) in rec.strain_home:
        # Norwalk runs a single strain -- the acquired strain's home host
        # is the source lineage.
        gen = rec.gen_of(rec.strain_home[str(acquired_strain)]) + 1
    else:
        gen = GEN_UNRESOLVED
    aid = int(agent.agent_id)
    rec.host_gen[aid] = gen
    rec.acquired_ids.add(aid)
    if acquired_strain:
        rec.strain_home.setdefault(str(acquired_strain), aid)
    row = rec.host_row(agent)
    row["gen"] = gen
    row["epoch_acquired"] = int(epoch)
    row["source_agent_id"] = source_id
    row["dominant_pathway"] = getattr(event, "pathway", None) if event else None
    # Dose provenance: which source generation's mass the converting dose
    # drew from, summed over this epoch's recorded deliveries to `aid`.
    src = {GEN_IMPORT: 0.0, GEN_ACQUIRED: 0.0, GEN_UNKNOWN: 0.0}
    for pr in rec.pickup_rows:
        if pr["target"] != aid or pr["epoch"] != int(epoch):
            continue
        share_a = pr["source_acquired_share"]
        share_i = pr["source_import_share"]
        share_u = max(0.0, 1.0 - share_a - share_i)
        src[GEN_ACQUIRED] += pr["delivered"] * share_a
        src[GEN_IMPORT] += pr["delivered"] * share_i
        src[GEN_UNKNOWN] += pr["delivered"] * share_u
    rec.acquisition_rows.append({
        "epoch": int(epoch),
        "agent_id": aid,
        "gen": gen if gen != GEN_UNRESOLVED else "unresolved",
        "source_agent_id": source_id,
        "parent_strain_id": parent_strain,
        "dose_read": float(p_dose),
        "effective_dose": witness[2] if witness else None,
        "frailty": witness[3] if witness else None,
        "hazard": witness[4] if witness else None,
        "dominant_pathway": row["dominant_pathway"],
        "delivered_src_import_gec": src[GEN_IMPORT],
        "delivered_src_acquired_gec": src[GEN_ACQUIRED],
        "delivered_src_unknown_gec": src[GEN_UNKNOWN],
    })


def _wrap_challenge(core_cls: type, rec: CensusRecorder) -> Any:
    original = core_cls._resolve_pathogen_challenge

    def wrapper(
        self: Any, epoch: int, agent: Any, pathogen_id: str,
        agent_pathogen_doses: dict, agent_pathway_doses: Any,
        matrix: Any, events: list,
    ) -> None:
        if pathogen_id != rec.pathogen_id:
            return original(
                self, epoch, agent, pathogen_id, agent_pathogen_doses,
                agent_pathway_doses, matrix, events,
            )
        aid = int(agent.agent_id)
        was_infected = bool(agent.is_infected_with(pathogen_id))
        p_dose = float(
            agent_pathogen_doses.get(aid, {}).get(pathogen_id, 0.0),
        )
        n_events = len(events)
        rec.hazard_witness = None
        original(
            self, epoch, agent, pathogen_id, agent_pathogen_doses,
            agent_pathway_doses, matrix, events,
        )
        witness = rec.hazard_witness
        if (
            witness is not None
            and (witness[0] != aid or witness[1] != pathogen_id)
        ):
            witness = None
        if not was_infected and agent.is_infected_with(pathogen_id):
            _record_acquisition(
                rec, agent, epoch, p_dose, witness, events[n_events:],
            )
        elif was_infected and aid not in rec.acquired_ids:
            rec.import_ids.add(aid)
            rec.host_gen.setdefault(aid, 0)

    return wrapper


def _epoch_snapshot(
    rec: CensusRecorder, sim: Any, work: Any, pathogen_id: str,
) -> dict[str, Any]:
    core = sim.tx_core
    counts = {
        "infected": 0, "infected_import": 0, "infected_acquired": 0,
        "symptomatic": 0, "confined": 0, "hand_positive_susceptible": 0,
    }
    for agent in sim.engine.agents:
        aid = int(agent.agent_id)
        inf = (getattr(agent, "infections", {}) or {}).get(pathogen_id)
        if inf is None:
            if (
                not getattr(agent, "immune", False)
                and agent.hand_load_by_pathogen.get(pathogen_id, 0.0) > 0.0
            ):
                counts["hand_positive_susceptible"] += 1
            continue
        if not rec.epoch0_snapshotted and aid not in rec.acquired_ids:
            rec.host_gen.setdefault(aid, 0)
            rec.import_ids.add(aid)
            strain = inf.get("strain_id")
            if strain:
                rec.strain_home.setdefault(str(strain), aid)
        if not agent.is_infected_with(pathogen_id):
            continue
        counts["infected"] += 1
        if aid in rec.acquired_ids:
            counts["infected_acquired"] += 1
        elif aid in rec.import_ids:
            counts["infected_import"] += 1
        else:
            counts["infected_unattributed"] = (
                counts.get("infected_unattributed", 0) + 1
            )
        _observe_host_row(rec, agent, inf, core, counts)
    rec.epoch0_snapshotted = True
    epoch = int(getattr(work, "epoch", 0) or 0)
    patches = core.emesis_patch_pools_by_pathogen.get(pathogen_id, {})
    return {
        "epoch": epoch,
        **counts,
        "pool_import_gec": sum(
            m.get(GEN_IMPORT, 0.0) for m in rec.unit_mix.values()
        ),
        "pool_acquired_gec": sum(
            m.get(GEN_ACQUIRED, 0.0) for m in rec.unit_mix.values()
        ),
        "patches_live": sum(len(p) for p in patches.values()),
        "patch_mass_acquired_gec": sum(
            float(patch.mass)
            for plist in patches.values()
            for patch in plist
            if _patch_gen(rec, patch) == GEN_ACQUIRED
        ),
    }


def _observe_host_row(
    rec: CensusRecorder, agent: Any, inf: dict, core: Any,
    counts: dict[str, int],
) -> None:
    row = rec.host_row(agent)
    row["gen"] = rec.gen_of(int(agent.agent_id))
    row["infected_epochs"] += 1
    shedding = float(agent.get_pathogen_shedding(
        rec.pathogen_id, rec.profile,
    ))
    row["shedding_gec"] += shedding
    if shedding > 0.0:
        row["shedding_epochs"] += 1
    hand = float(agent.hand_load_by_pathogen.get(rec.pathogen_id, 0.0))
    row["hand_peak_gec"] = max(row["hand_peak_gec"], hand)
    if inf.get("illness") == tc.IllnessStatus.SYMPTOMATIC:
        counts["symptomatic"] += 1
        row["symptomatic_epochs"] += 1
    if core._cabin_confinement_active(agent):
        counts["confined"] += 1
        row["confined_epochs"] += 1


def _census_observer(rec: CensusRecorder, pathogen_id: str) -> Any:
    """Per-epoch census: infected/shedding/confined counts by generation."""

    def observe(sim: Any, work: Any) -> None:
        rec.census_rows.append(
            _epoch_snapshot(rec, sim, work, pathogen_id),
        )

    return observe


_WRAPPED_METHODS = (
    "_emit_emesis",
    "_deposit_surface_mass",
    "_scale_surface_mass",
    "_roll_up_per_surface_zone",
    "_scale_emesis_patch",
    "_route_stool_event_venue",
    "_fomite_zone_pickup",
    "_emesis_patch_pickup",
    "_emesis_patch_pickup_one",
    "_fomite_pickup_request_for_area",
    "_deliver_one_pickup",
    "_deliver_sanitary_pooled_requests",
    "_hand_to_mouth_dose",
    "_per_partner_contact_dose",
    "_food_deposits",
    "_food_ingestion",
    "_grow_food_pool",
    "_dose_response_hazard",
    "_resolve_pathogen_challenge",
)


def _install_wrappers(core_cls: type, rec: CensusRecorder) -> dict[str, Any]:
    return {
        "_emit_emesis": _wrap_emit_emesis(core_cls, rec),
        "_deposit_surface_mass": _wrap_deposit_surface_mass(core_cls, rec),
        "_scale_surface_mass": _wrap_scale_surface_mass(core_cls, rec),
        "_roll_up_per_surface_zone": _wrap_roll_up(core_cls, rec),
        "_scale_emesis_patch": _wrap_scale_emesis_patch(core_cls, rec),
        "_route_stool_event_venue": _wrap_stool_venue(core_cls, rec),
        "_fomite_zone_pickup": _wrap_fomite_zone_pickup(core_cls, rec),
        "_emesis_patch_pickup": _wrap_patch_sweep(core_cls, rec),
        "_emesis_patch_pickup_one": _wrap_patch_pickup_one(core_cls, rec),
        "_fomite_pickup_request_for_area": _wrap_pickup_request_for_area(
            core_cls, rec,
        ),
        "_deliver_one_pickup": _wrap_deliver_one_pickup(core_cls, rec),
        "_deliver_sanitary_pooled_requests": _wrap_deliver_sanitary_pooled(
            core_cls, rec,
        ),
        "_hand_to_mouth_dose": _wrap_hand_to_mouth(core_cls, rec),
        "_per_partner_contact_dose": _wrap_partner_contact(core_cls, rec),
        "_food_deposits": _wrap_food_deposits(core_cls, rec),
        "_food_ingestion": _wrap_food_ingestion(core_cls, rec),
        "_grow_food_pool": _wrap_grow_food_pool(core_cls, rec),
        "_dose_response_hazard": _wrap_hazard(core_cls, rec),
        "_resolve_pathogen_challenge": _wrap_challenge(core_cls, rec),
    }


@contextmanager
def instrumented(rec: CensusRecorder) -> Any:
    """Install the read-only census wrappers for one run."""
    core_cls = tc.TransmissionCore
    saved = {name: getattr(core_cls, name) for name in _WRAPPED_METHODS}
    saved_gate = tc.pickup_gate_open
    schedule_saved = (
        tc.draw_emesis_schedule,
        initiation_module.draw_emesis_schedule,
        natural_history_module.draw_emesis_schedule,
    )
    for name, wrapped in _install_wrappers(core_cls, rec).items():
        setattr(core_cls, name, wrapped)
    tc.pickup_gate_open = _wrap_pickup_gate(rec)
    tc.draw_emesis_schedule = _wrap_schedule_module(tc, rec)
    initiation_module.draw_emesis_schedule = _wrap_schedule_module(
        initiation_module, rec,
    )
    natural_history_module.draw_emesis_schedule = _wrap_schedule_module(
        natural_history_module, rec,
    )
    try:
        yield
    finally:
        for name, method in saved.items():
            setattr(core_cls, name, method)
        tc.pickup_gate_open = saved_gate
        (
            tc.draw_emesis_schedule,
            initiation_module.draw_emesis_schedule,
            natural_history_module.draw_emesis_schedule,
        ) = schedule_saved


def _count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[str(row.get(key))] += 1
    return dict(counts)


def _unit_classes(core: Any) -> dict[str, str]:
    """zone name -> venue class for every unit the census touched."""
    classes: dict[str, str] = {}
    for zone_name, zone_type in (core.zone_types or {}).items():
        classes[zone_name] = zone_type
    return classes


def _classify_unit(classes: dict[str, str], unit: str) -> str:
    if tc._is_cabin_compartment(unit):
        return "cabin_fittings"
    if classes.get(unit) == "Sanitary":
        return "shared_head"
    return "other_zone"


def _summarise_run(
    rec: CensusRecorder, spec_dict: dict[str, Any],
    wall_clock_s: float, core: Any,
) -> dict[str, Any]:
    """Fold one voyage's rows into the per-link census summary."""
    rec.import_ids |= rec.seed_ids
    for aid in rec.import_ids:
        rec.host_gen.setdefault(aid, 0)
    host_rows = sorted(
        (
            row for row in rec.hosts.values()
            if (
                row["infected_epochs"] > 0 or row["deposit_gec"] > 0.0
                or row["stool_events"] > 0 or row["emesis_emitted"] > 0
                or row["emesis_scheduled"] > 0
            )
        ),
        key=lambda row: row["agent_id"],
    )
    classes = _unit_classes(core)
    for row in host_rows:
        row["gen"] = rec.gen_of(row["agent_id"])
    emit_hosts = {row["agent_id"] for row in rec.emit_rows}
    return {
        "ignited": bool(rec.emit_rows),
        "emitting_hosts": sorted(emit_hosts),
        "emitting_imports": sorted(
            aid for aid in emit_hosts if rec.gen_of(aid) == 0
        ),
        "n_imports": len(rec.import_ids),
        "n_acquired": len(rec.acquired_ids),
        "acquisitions_by_gen": _count_by(rec.acquisition_rows, "gen"),
        "hosts": host_rows,
        "emits": rec.emit_rows,
        "deposits": rec.deposit_rows,
        "stool_events": rec.stool_rows,
        "gate_closed": rec.gate_rows,
        "gate_open_by_caller": dict(rec.gate_open_by_caller),
        "unit_epochs": rec.unit_epoch_rows,
        "pickups": rec.pickup_rows,
        "doses": rec.dose_rows,
        "hazards": rec.hazard_rows,
        "acquisitions": rec.acquisition_rows,
        "hand_contacts": rec.contact_rows,
        "food_venues": rec.food_rows,
        "patch_pickups": rec.patch_rows,
        "patch_sweeps": rec.patch_sweep_rows,
        "removal_totals": {
            cause: dict(by_gen)
            for cause, by_gen in rec.removal_totals.items()
        },
        "census_epochs": rec.census_rows,
        "meta": {
            "zone_classes": classes,
            "seed": int(spec_dict["run"]["random_seed"]),
            "num_agents": int(
                spec_dict["campaign_parameters"]["num_agents"],
            ),
            "epochs": int(spec_dict["run"]["num_epochs"]),
            "platform": spec_dict["catalog"]["platform_id"],
            "pathogen_id": rec.pathogen_id,
            "wall_clock_s": round(wall_clock_s, 1),
        },
    }


def _load_manifest(manifest_path: Path) -> dict[str, Any]:
    safe_manifest = Path(
        resolve_repo_path(str(REPO_ROOT), str(manifest_path)),
    )
    with validated_open(
        safe_manifest, "r", allowed_roots=(str(REPO_ROOT),), encoding="utf-8",
    ) as handle:
        return json.load(handle)


def run_seed(
    *, seed: int, pathogen_id: str, spec_dict: dict[str, Any],
) -> dict[str, Any]:
    """Run one voyage under the census wrappers and fold the summary."""
    rec = CensusRecorder(pathogen_id=pathogen_id)
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
        spec_path = resolve_child_path(tmp, "run_spec.json")
        with validated_open(
            spec_path, "w", allowed_roots=(tmp,), encoding="utf-8",
        ) as handle:
            handle.write(json.dumps(spec_dict))
        picard_spec = PicardRunSpec.from_picard_json(
            str(REPO_ROOT), spec_path,
        )
        rec.profile = dict(
            picard_spec.pathogen_profiles.get(pathogen_id) or {},
        )
        with instrumented(rec):
            sim = ShipSimulation(picard_spec, display=False)
            sim.initialize()
            # Priming pass: everything infected before epoch 0 is an
            # import, so epoch-0 emits/deposits attribute correctly
            # (the observer only snapshots at end-of-epoch).
            for agent in sim.engine.agents:
                inf = (
                    getattr(agent, "infections", {}) or {}
                ).get(pathogen_id)
                if inf is None:
                    continue
                aid = int(agent.agent_id)
                rec.host_gen.setdefault(aid, 0)
                rec.import_ids.add(aid)
                strain = inf.get("strain_id")
                if strain:
                    rec.strain_home.setdefault(str(strain), aid)
                rec.host_row(agent)
            sim.epoch_observer = _census_observer(rec, pathogen_id)
            started = time.perf_counter()
            sim.run()
            wall_clock_s = time.perf_counter() - started
        rec.seed_ids = set(
            getattr(sim.engine, "explicit_seed_agent_ids", None) or (),
        )
        core = sim.tx_core
    return _summarise_run(rec, spec_dict, wall_clock_s, core)


def _write_run_zip(
    out_dir: Path, tier: str, run_id: str, payload: dict[str, Any],
) -> Path:
    cell_dir = Path(resolve_child_path(str(out_dir), tier))
    cell_dir.mkdir(parents=True, exist_ok=True)
    zip_path = Path(resolve_child_path(str(cell_dir), f"{run_id}.zip"))
    anchor = {
        "run_id": run_id,
        "parameters": payload["meta"],
        "summary": {
            "ignited": payload["ignited"],
            "n_imports": payload["n_imports"],
            "n_acquired": payload["n_acquired"],
            "acquisitions_by_gen": payload["acquisitions_by_gen"],
        },
    }
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("summary.json", json.dumps(anchor))
        archive.writestr(
            "growth_census.json.gz",
            gzip.compress(json.dumps(payload).encode("utf-8")),
        )
    return zip_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--tier", type=str, required=True)
    parser.add_argument("--index", type=int, default=None)
    parser.add_argument(
        "--seeds", type=int, nargs="*", default=None,
        help="restrict to these seeds after any --index slice",
    )
    parser.add_argument(
        "--pathogen-id", type=str, default="norwalk_gi",
    )
    parser.add_argument(
        "--epochs-override", type=int, default=None,
        help="smoke-only: override the tier's epoch count",
    )
    parser.add_argument(
        "--num-agents-override", type=int, default=None,
        help="smoke-only: override the declared complement",
    )
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = _load_manifest(args.manifest)
    clock = manifest.get("natural_history_clock")
    runs = list(generate_tier_runs(
        manifest, args.tier,
        epochs_override=args.epochs_override,
        num_agents_override=args.num_agents_override,
        natural_history_clock=str(clock) if clock is not None else None,
    ))
    if args.index is not None:
        if args.index >= len(runs):
            raise SystemExit(
                f"--index {args.index} outside tier {args.tier} "
                f"({len(runs)} runs)",
            )
        runs = [runs[args.index]]
    if args.seeds:
        wanted = set(args.seeds)
        runs = [
            pair for pair in runs
            if int(pair[1]["run"]["random_seed"]) in wanted
        ]
    out_dir = Path(
        prepare_output_directory(str(args.out), allowed_roots=(str(REPO_ROOT),)),
    )
    for run_id, spec in runs:
        seed = int(spec["run"]["random_seed"])
        payload = run_seed(
            seed=seed, pathogen_id=args.pathogen_id, spec_dict=spec,
        )
        payload["run_id"] = run_id
        zip_path = _write_run_zip(out_dir, args.tier, run_id, payload)
        print(
            f"seed {seed}: ignited={payload['ignited']} "
            f"imports={payload['n_imports']} "
            f"acquired={payload['n_acquired']} "
            f"by_gen={payload['acquisitions_by_gen']} "
            f"-> {zip_path}", flush=True,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
