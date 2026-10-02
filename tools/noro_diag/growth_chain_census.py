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
import time
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
from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_child_path,
)
from tools.diag.instrument_common import (  # noqa: E402
    attr_patches,
    emesis_records,
    materialized_picard_spec,
    wrap_emit_emesis,
)
from tools.diag.json_io import validated_json_load  # noqa: E402
from tools.diag.manifest_args import (  # noqa: E402
    add_manifest_args,
    filter_runs_by_seeds,
    index_run,
)
from tools.diag.readout_common import write_run_zip  # noqa: E402

_CAMPAIGN_DIR = (
    REPO_ROOT / "picard_framework" / "runs" / "mega_cruise_campaign"
)
if str(_CAMPAIGN_DIR) not in sys.path:
    sys.path.insert(0, str(_CAMPAIGN_DIR))

from campaign_runner import generate_tier_runs  # noqa: E402

from tools.noro_diag import hand_occupancy  # noqa: E402


def _voyage_blocks(
    spec_dict: dict[str, Any],
    result: Any,
    num_agents: int,
    natural_history_clock: str | None,
) -> dict[str, Any]:
    """The campaign-layout blocks a verbatim campaign spec produces.

    Deferred import: ``per_host_dose_challenge`` already imports this
    module for ``GEN_UNRESOLVED``/``_acquired_gen``, so a top-level import
    of it here would cycle.
    """
    from tools.noro_diag.per_host_dose_challenge import (  # noqa: E402
        _attach_voyage_blocks,
    )

    summary: dict[str, Any] = {}
    _attach_voyage_blocks(
        summary,
        spec_dict,
        result,
        num_agents,
        natural_history_clock=natural_history_clock,
    )
    return summary


def _initiation_witness(
    sim: Any, pathogen_id: str, profile: dict[str, Any],
) -> dict[str, Any]:
    """The consumed import configuration: resolved boarding spec + manifest.

    A renewal-mode arm proves the symptomatic partition was exercised by
    the resolved ``symptomatic_*_prevalence`` fields plus the manifest's
    realised ``composition`` counter, not by trusting the tier label.
    """
    plan = getattr(sim.engine, "initiation_plan", None)
    manifest = getattr(sim.engine, "initiation_manifest", None) or {}
    resolved: dict[str, Any] = {}
    if plan is not None and not plan.legacy:
        for spec in plan.boarding:
            if spec.pathogen_id != pathogen_id:
                continue
            resolved = {
                "rate_mode": spec.rate_mode,
                "symptomatic_stream": bool(spec.symptomatic_stream),
                "symptomatic_passenger_prevalence": (
                    spec.symptomatic_passenger_prevalence
                ),
                "symptomatic_crew_prevalence": (
                    spec.symptomatic_crew_prevalence
                ),
                "passenger_prevalence": spec.passenger_prevalence,
                "crew_prevalence": spec.crew_prevalence,
                "never_symptomatic_fraction": spec.never_symptomatic_fraction,
                "presymptomatic_share_of_presenting": (
                    spec.presymptomatic_share_of_presenting
                ),
            }
    return {
        "resolved": resolved,
        "dose_response": dict(profile.get("dose_response") or {}),
        "manifest": manifest,
    }

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
_KNOWN_CALLSITES = frozenset(
    set(_DEPOSIT_CALLSITES)
    | set(_REMOVAL_CALLSITES)
    | set(_PATCH_REMOVAL_CALLSITES)
    | set(_GATE_CALLERS)
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
    # NORO-HAND-STATIONARY-01: per host-epoch hand-load occupancy rows.
    occupancy: hand_occupancy.OccupancyRecorder | None = None

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


def _frame_agent(frame: Any, out: dict[str, Any]) -> None:
    if out["agent"] is not None:
        return
    agent = frame.f_locals.get("agent")
    if hasattr(agent, "agent_id"):
        out["agent"] = agent


def _frame_epoch(frame: Any, out: dict[str, Any]) -> None:
    if out["epoch"] is not None:
        return
    epoch = frame.f_locals.get("epoch")
    if isinstance(epoch, int):
        out["epoch"] = int(epoch)


def _frame_unit(frame: Any, out: dict[str, Any]) -> None:
    if out["unit"] is not None:
        return
    for key in ("zone_name", "unit_name", "venue"):
        unit = frame.f_locals.get(key)
        if isinstance(unit, str):
            out["unit"] = unit
            break


def _frame_callsite(frame: Any, out: dict[str, Any]) -> None:
    name = frame.f_code.co_name
    if out["callsite"] == "other" and name in _KNOWN_CALLSITES:
        out["callsite"] = name


def _frame_facts(frame: Any, out: dict[str, Any]) -> None:
    _frame_agent(frame, out)
    _frame_epoch(frame, out)
    _frame_unit(frame, out)
    _frame_callsite(frame, out)


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
            if frame is not None:
                _frame_facts(frame, out)
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
    for gen_class, mass in state.items():
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
    def _pre(
        self: Any, agent: Any, pathogen_id: str,
        zone_name: str, epoch: int,
    ) -> int:
        return len(
            self.emesis_patch_pools_by_pathogen.get(pathogen_id, {})
            .get(zone_name, []),
        )

    def _on_emit(
        self: Any, agent: Any, pathogen_id: str, zone_name: str,
        epoch: int, pool_gain: float, before: int, ctx: int,
    ) -> None:
        _tag_new_patches(self, pathogen_id, zone_name, ctx, agent)
        if pathogen_id != rec.pathogen_id:
            return
        row = rec.host_row(agent)
        for record in emesis_records(agent, pathogen_id)[before:]:
            row["emesis_emitted"] += 1
            row["emesis_surface_gec"] += float(record.get("surface_load", 0.0))
            row["emesis_aerosol_gec"] += float(record.get("aerosol_load", 0.0))
            rec.emit_rows.append({
                "epoch": int(epoch),
                "agent_id": int(agent.agent_id),
                "gen": rec.gen_of(int(agent.agent_id)),
                "gen_class": rec.gen_class_of(int(agent.agent_id)),
                "zone": zone_name,
                "zone_type": getattr(self, "zone_types", {}).get(
                    zone_name, "shared",
                ),
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

    return wrap_emit_emesis(core_cls, _on_emit, pre=_pre)


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
        probe = _frame_probe(depth_limit=6)
        if open_:
            rec.gate_open_by_caller[probe["callsite"]] += 1
        else:
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
    dose: float, challengeable: bool,
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
        "challengeable": bool(challengeable),
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
            # Under wash_reuptake this arg carries the widened requester
            # set; the field keeps its challengeable meaning in both arms.
            "n_susceptible": len(
                self._get_susceptible(susceptible, pathogen_id),
            ),
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
            # NORO-HAND-RESERVOIR-01: under wash_reuptake non-challengeable
            # occupants also draw pool mass -- tag whether this delivery
            # could challenge (dose-booked) or went to the reservoir.
            pathogen_id = kwargs.get("pathogen_id")
            if pathogen_id is None and len(args) >= 2:
                pathogen_id = args[-2]
            challengeable = (
                pathogen_id is not None
                and target in self._get_susceptible([target], pathogen_id)
            )
            _record_pickup(
                rec, target, delivered, zone_name, dose, challengeable,
            )
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
            # Under wash_reuptake a non-challengeable hand also swallows
            # mass; tag it so the reservoir share of the sanitary path is
            # measurable too.
            "challengeable": bool(
                target in self._get_susceptible(
                    [target], rec.pathogen_id,
                )
            ),
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


def _acquired_gen(
    rec: CensusRecorder, source_id: Any, parent_strain: Any,
    acquired_strain: Any,
) -> int:
    if source_id is not None:
        return rec.gen_of(int(source_id)) + 1
    if parent_strain and parent_strain in rec.strain_home:
        return rec.gen_of(rec.strain_home[parent_strain]) + 1
    if acquired_strain and str(acquired_strain) in rec.strain_home:
        # Norwalk runs a single strain -- the acquired strain's home host
        # is the source lineage.
        return rec.gen_of(rec.strain_home[str(acquired_strain)]) + 1
    return GEN_UNRESOLVED


def _dose_provenance(
    rec: CensusRecorder, aid: int, epoch: int,
) -> dict[str, float]:
    """Source generation of the mass the converting dose drew from."""
    src = {GEN_IMPORT: 0.0, GEN_ACQUIRED: 0.0, GEN_UNKNOWN: 0.0}
    for pr in rec.pickup_rows:
        if pr["target"] != aid or pr["epoch"] != int(epoch):
            continue
        share_a = pr["source_acquired_share"]
        share_i = pr["source_import_share"]
        src[GEN_ACQUIRED] += pr["delivered"] * share_a
        src[GEN_IMPORT] += pr["delivered"] * share_i
        src[GEN_UNKNOWN] += pr["delivered"] * max(
            0.0, 1.0 - share_a - share_i,
        )
    return src


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
    gen = _acquired_gen(rec, source_id, parent_strain, acquired_strain)
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
    src = _dose_provenance(rec, aid, epoch)
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
        matrix: Any, events: list, *args: Any, **kwargs: Any,
    ) -> None:
        if pathogen_id != rec.pathogen_id:
            return original(
                self, epoch, agent, pathogen_id, agent_pathogen_doses,
                agent_pathway_doses, matrix, events, *args, **kwargs,
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
            agent_pathway_doses, matrix, events, *args, **kwargs,
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


def _epoch_prime_imports(
    rec: CensusRecorder, inf: dict, aid: int,
) -> None:
    """Epoch-0 priming: pre-run infections are imports."""
    if rec.epoch0_snapshotted or aid in rec.acquired_ids:
        return
    rec.host_gen.setdefault(aid, 0)
    rec.import_ids.add(aid)
    strain = inf.get("strain_id")
    if strain:
        rec.strain_home.setdefault(str(strain), aid)


def _class_infected(
    rec: CensusRecorder, aid: int, counts: dict[str, int],
) -> None:
    if aid in rec.acquired_ids:
        counts["infected_acquired"] += 1
    elif aid in rec.import_ids:
        counts["infected_import"] += 1
    else:
        counts["infected_unattributed"] = (
            counts.get("infected_unattributed", 0) + 1
        )


def _epoch_agent(
    rec: CensusRecorder, agent: Any, pathogen_id: str, core: Any,
    counts: dict[str, int],
) -> None:
    aid = int(agent.agent_id)
    inf = (getattr(agent, "infections", {}) or {}).get(pathogen_id)
    if inf is None:
        if (
            not getattr(agent, "immune", False)
            and agent.hand_load_by_pathogen.get(pathogen_id, 0.0) > 0.0
        ):
            counts["hand_positive_susceptible"] += 1
        return
    _epoch_prime_imports(rec, inf, aid)
    if not agent.is_infected_with(pathogen_id):
        return
    counts["infected"] += 1
    _class_infected(rec, aid, counts)
    _observe_host_row(rec, agent, inf, core, counts)


def _epoch_snapshot(
    rec: CensusRecorder, sim: Any, work: Any, pathogen_id: str,
) -> dict[str, Any]:
    core = sim.tx_core
    counts = {
        "infected": 0, "infected_import": 0, "infected_acquired": 0,
        "symptomatic": 0, "confined": 0, "hand_positive_susceptible": 0,
    }
    for agent in sim.engine.agents:
        _epoch_agent(rec, agent, pathogen_id, core, counts)
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
    with attr_patches() as patches:
        for name, wrapped in _install_wrappers(core_cls, rec).items():
            patches.swap(core_cls, name, wrapped)
        if rec.occupancy is not None:
            # Installed last so the occupancy wrappers call the census
            # wrappers on shared methods; every census counter still sees
            # every call.
            patches.note(
                core_cls,
                hand_occupancy.install(core_cls, rec.occupancy),
            )
        patches.swap(tc, "pickup_gate_open", _wrap_pickup_gate(rec))
        patches.swap(
            tc, "draw_emesis_schedule", _wrap_schedule_module(tc, rec),
        )
        patches.swap(
            initiation_module, "draw_emesis_schedule",
            _wrap_schedule_module(initiation_module, rec),
        )
        patches.swap(
            natural_history_module, "draw_emesis_schedule",
            _wrap_schedule_module(natural_history_module, rec),
        )
        yield


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
        "hand_occupancy": (
            hand_occupancy.summarise(rec.occupancy)
            if rec.occupancy is not None else None
        ),
        "hand_occupancy_rows": (
            rec.occupancy.rows if rec.occupancy is not None else []
        ),
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
    return validated_json_load(REPO_ROOT, manifest_path)


def run_seed(
    *, pathogen_id: str, spec_dict: dict[str, Any],
    natural_history_clock: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Run one voyage under the census wrappers; fold summary + voyage
    blocks + the initiation witness."""
    rec = CensusRecorder(pathogen_id=pathogen_id)
    rec.occupancy = hand_occupancy.OccupancyRecorder(pathogen_id)
    with materialized_picard_spec(spec_dict, REPO_ROOT) as picard_spec:
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
            result = sim.run()
            wall_clock_s = time.perf_counter() - started
        rec.seed_ids = set(
            getattr(sim.engine, "explicit_seed_agent_ids", None) or (),
        )
        core = sim.tx_core
        initiation = _initiation_witness(sim, pathogen_id, rec.profile)
    num_agents = int(
        (spec_dict.get("config_overrides") or {})
        .get("ship_graph", {})
        .get("num_agents", 0),
    )
    voyage = _voyage_blocks(
        spec_dict, result, num_agents, natural_history_clock,
    )
    return (
        _summarise_run(rec, spec_dict, wall_clock_s, core),
        voyage,
        initiation,
    )


def _control_voyage(
    spec_dict: dict[str, Any], natural_history_clock: str | None,
) -> dict[str, Any]:
    """The same spec run with no wrappers -- the draw-neutrality control."""
    with materialized_picard_spec(spec_dict, REPO_ROOT) as picard_spec:
        result = ShipSimulation(picard_spec, display=False).run()
    num_agents = int(
        (spec_dict.get("config_overrides") or {})
        .get("ship_graph", {})
        .get("num_agents", 0),
    )
    return _voyage_blocks(spec_dict, result, num_agents, natural_history_clock)


def verify_draws(
    *, pathogen_id: str, spec_dict: dict[str, Any],
    natural_history_clock: str | None,
) -> dict[str, Any]:
    """Instrumented vs control voyage on the identical spec.

    The census and occupancy wrappers consume no RNG by construction; the
    ledger requires the claim measured, so the two runs must produce a
    byte-identical voyage fingerprint.
    """
    _payload, voyage, _initiation = run_seed(
        pathogen_id=pathogen_id, spec_dict=spec_dict,
        natural_history_clock=natural_history_clock,
    )
    control = _control_voyage(spec_dict, natural_history_clock)
    equal = (
        json.dumps(voyage, sort_keys=True, default=str)
        == json.dumps(control, sort_keys=True, default=str)
    )
    return {
        "seed": int(spec_dict["run"]["random_seed"]),
        "platform": spec_dict["catalog"]["platform_id"],
        "instrument": "growth_chain_census+hand_occupancy",
        "fingerprint_keys": sorted(voyage),
        "voyage_fingerprint_equal": equal,
        "verdict": "PASS" if equal else "FAIL",
    }


def _write_run_zip(
    out_dir: Path, tier: str, run_id: str, payload: dict[str, Any],
    voyage: dict[str, Any], initiation: dict[str, Any],
) -> Path:
    """``summary.json`` (campaign layout + census + initiation witness)
    plus the ``growth_census.json.gz`` link payload."""
    anchor = {
        "run_id": run_id,
        "parameters": voyage["parameters"],
        "num_epochs": payload["meta"]["epochs"],
        "trigger_status": voyage.get("trigger_status"),
        "summary": voyage["summary"],
        "cost_accounting": voyage["cost_accounting"],
        "derived": voyage["derived"],
        "timeseries": voyage["timeseries"],
        "census": {
            "ignited": payload["ignited"],
            "n_imports": payload["n_imports"],
            "n_acquired": payload["n_acquired"],
            "acquisitions_by_gen": payload["acquisitions_by_gen"],
        },
        "initiation": initiation,
    }
    return write_run_zip(out_dir, tier, run_id, anchor, {
        "growth_census.json.gz": gzip.compress(
            json.dumps(payload).encode("utf-8"),
        ),
    })


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    add_manifest_args(parser, required=True)
    parser.add_argument(
        "--seeds", type=int, nargs="*", default=None,
        help="restrict to these seeds after any --index slice",
    )
    parser.add_argument(
        "--pathogen-id", type=str, default="norwalk_gi",
    )
    parser.add_argument(
        "--exposure-cap", choices=("on", "off"), default=None,
        help="EXPO-CAP-01 arm: inject transmission.exposure_cap.enabled "
             "into each spec's config_overrides (unset leaves the tier "
             "spec's own transmission block)",
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
    parser.add_argument(
        "--verify-draws", action="store_true",
        help="run each selected seed twice (instrumented vs control) and "
             "report whether the voyage fingerprints are identical; writes "
             "verify_draws_<tier>.json and no cell zips",
    )
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
    runs = index_run(runs, args.index, args.tier)
    runs = filter_runs_by_seeds(runs, args.seeds or None)
    if args.exposure_cap is not None:
        enabled = args.exposure_cap == "on"
        for _run_id, spec in runs:
            tx = spec.setdefault("config_overrides", {}).setdefault(
                "transmission", {},
            )
            tx["exposure_cap"] = {"enabled": enabled}
    out_dir = Path(
        prepare_output_directory(str(args.out), allowed_roots=(str(REPO_ROOT),)),
    )
    if args.verify_draws:
        checks = [
            verify_draws(
                pathogen_id=args.pathogen_id, spec_dict=spec,
                natural_history_clock=clock,
            )
            for _run_id, spec in runs
        ]
        path = resolve_child_path(
            str(out_dir), f"verify_draws_{args.tier}.json",
        )
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"checks": checks}, handle, indent=1)
        ok = all(check["voyage_fingerprint_equal"] for check in checks)
        print(json.dumps({"checks": checks}, indent=1))
        print(f"written: {path}")
        return 0 if ok else 1
    for run_id, spec in runs:
        seed = int(spec["run"]["random_seed"])
        payload, voyage, initiation = run_seed(
            pathogen_id=args.pathogen_id, spec_dict=spec,
            natural_history_clock=clock,
        )
        payload["run_id"] = run_id
        zip_path = _write_run_zip(
            out_dir, args.tier, run_id, payload, voyage, initiation,
        )
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
