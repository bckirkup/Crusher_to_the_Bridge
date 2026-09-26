#!/usr/bin/env python3
"""Per-change deposit-collapse attribution trace, ledger NORO-DEPOSIT-ATTR-01.

Purpose
-------
``NORO-REBASE-01`` measured a post-#724 collapse of surface-pool deposit mass
(~5 orders of magnitude) at the sanitary venues of the ``fl_spr_12d`` cell:
``sanitary_activity.dose_delivered`` fell from ~1.8e5/epoch (pre-fix archive,
seed 8105) to ~2-5/epoch, while pickup requests still fire. This probe replays
that exact cell on the post-724 base under one ablation arm at a time and
records the whole deposit path per epoch:

* which engine call site deposited mass, and into which venue class
  (shared head / cabin fittings / other zone),
* where stool events rerouted,
* how much emesis mass filed into patch pools vs zone pools,
* what the venue pools held at epoch end, split by venue class,
* shedder hand loads, confined counts, and new infections.

Arms (declared in the ledger before any run)
--------------------------------------------
``base``            the verbatim cell (local canary: dose ~2-5/epoch).
``blackwater_off``  ``transmission.blackwater_plumbing: false`` (labelled,
                    stream-neutral baseline).
``watch_off``       ``ship_graph.agent_classes`` without the ``schedule`` key
                    on crew classes + ``agent_behavior.schedule_jitter_hours``
                    zeroed -- the pre-#723 state. NOT stream-neutral: spawn
                    draws reorder (SCHED-WATCH-01 caveat).
``gate_off``        ``fomite_surfaces.SURFACE_PICKUP_MIN_GEC`` patched to 0.0
                    in-process for the run (equivalent to reverting the
                    constant; the gate consumes no RNG either way).
``emesis_zonepool`` in-process semantic revert of ``_emit_emesis`` /
                    ``_deposit_emesis`` to the pre-#604 filing: touchable
                    share ``min(1, high_touch/footprint)`` and zone-pool
                    deposit instead of EmesisPatch. Draw order inside the
                    emitter is preserved; downstream patch-pickup draws vanish
                    with the patches, so the arm is not bit-identical.
``report_scale``    ``pathogen_overrides.norwalk_gi.observation_model
                    .reporting_belief_scaling = "trust_medical"`` -- the
                    pre-NORO-CHANNEL-02 stacking, as a labelled baseline.
``cabin_fomite_off`` ``transmission.cabin_confined_fomite.mode: "off"`` --
                    labelled baseline for the in-window NORO-CABIN-01 pickup
                    path.

No wrapper draws from the engine's generator and none writes engine state,
except the two declared in-process patches which are the arm itself.

Outputs
-------
One gzipped JSON per (arm, seed) at ``--out`` with the per-epoch table and the
voyage summary; a compact summary is printed. ``--index`` selects a single
seed for Batch canaries.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import re
import sys
import tempfile
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
_CAMPAIGN_DIR = REPO_ROOT / "picard_framework" / "runs" / "mega_cruise_campaign"
if str(_CAMPAIGN_DIR) not in sys.path:
    sys.path.insert(0, str(_CAMPAIGN_DIR))

import yaml  # noqa: E402
from campaign_runner import generate_tier_runs  # noqa: E402

from engines import fomite_surfaces  # noqa: E402
from engines import transmission_core as tc  # noqa: E402
from picard_framework.run_spec import PicardRunSpec  # noqa: E402
from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_child_path,
    validated_open,
)

DEFAULT_MANIFEST = (
    _CAMPAIGN_DIR / "noro_rebase_01_manifest.json"
)
DEFAULT_TIER = "fl_spr_12d"
DEFAULT_SEEDS = (8105, 8106)
PATHOGEN_ID = "norwalk_gi"


def _caller_name(depth: int = 2) -> str:
    """The engine function that called the wrapper, for call-site tagging."""
    return str(sys._getframe(depth).f_code.co_name)


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """Recursive dict merge; non-dict values replace wholesale."""
    merged = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _pre723_agent_classes() -> list[dict[str, Any]]:
    """The config agent_classes list with every ``schedule`` key removed.

    Pre-#723 the crew classes carried no ``schedule`` block at all and
    inherited their role-group template; stripping the whole key (not just
    ``night_watch_fraction``) reproduces that state.
    """
    cfg = yaml.safe_load(
        (REPO_ROOT / "crusher_labs" / "config.yaml").read_text(
            encoding="utf-8",
        ),
    )
    classes = []
    for entry in cfg["ship_graph"]["agent_classes"]:
        entry = dict(entry)
        entry.pop("schedule", None)
        classes.append(entry)
    return classes


def _arm_overrides(arm: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """(config_overrides patch, pathogen_overrides patch) for one arm."""
    if arm == "base":
        return {}, {}
    if arm == "blackwater_off":
        return {"transmission": {"blackwater_plumbing": False}}, {}
    if arm == "watch_off":
        return {
            "ship_graph": {"agent_classes": _pre723_agent_classes()},
            "agent_behavior": {
                "schedule_jitter_hours": {"passenger": 0.0, "crew": 0.0},
            },
        }, {}
    if arm == "gate_off":
        return {}, {}
    if arm == "emesis_zonepool":
        return {}, {}
    if arm == "report_scale":
        return {}, {
            PATHOGEN_ID: {
                "observation_model": {
                    "reporting_belief_scaling": "trust_medical",
                },
            },
        }
    if arm == "cabin_fomite_off":
        return {"transmission": {"cabin_confined_fomite": {"mode": "off"}}}, {}
    raise ValueError(f"unknown arm: {arm!r}")


ARMS = (
    "base",
    "blackwater_off",
    "watch_off",
    "gate_off",
    "emesis_zonepool",
    "report_scale",
    "cabin_fomite_off",
)


def _venue_class(core: Any, venue: str) -> str:
    """Classify a deposit/pickup venue for the attribution split."""
    if core._is_cabin_compartment(venue):
        return "cabin_fittings"
    if core.zone_types.get(venue) == "Sanitary":
        return "shared_head"
    return "other_zone"


@dataclass
class Recorder:
    """Every observation taken from one instrumented arm run."""

    pathogen_id: str
    epoch: int = 0
    core: Any = None
    epoch_acc: dict[str, float] = field(
        default_factory=lambda: defaultdict(float),
    )
    epoch_rows: list[dict[str, Any]] = field(default_factory=list)
    stool_venues: dict[str, int] = field(
        default_factory=lambda: defaultdict(int),
    )
    emesis_zone_mass: dict[str, float] = field(
        default_factory=lambda: defaultdict(float),
    )
    totals: dict[str, float] = field(
        default_factory=lambda: defaultdict(float),
    )
    _seen_infected: set[int] = field(default_factory=set)
    _seed_ids: set[int] = field(default_factory=set)
    _prev_telemetry: dict[str, float] = field(default_factory=dict)

    def venue_pools(self) -> dict[str, float]:
        """Current pool mass for this pathogen, split by venue class."""
        split: dict[str, float] = defaultdict(float)
        if self.core is None:
            return dict(split)
        pools = self.core.surface_pools_by_pathogen.get(self.pathogen_id, {})
        for venue, mass in pools.items():
            split[_venue_class(self.core, str(venue))] += float(mass)
        return dict(split)

    def patch_pool_total(self) -> float:
        """Mass currently sitting in emesis patch pools."""
        if self.core is None:
            return 0.0
        patches = self.core.emesis_patch_pools_by_pathogen.get(
            self.pathogen_id, {},
        )
        return float(
            sum(p.mass for venues in patches.values() for p in venues)
        )


def _wrap_mass_books(core_cls: type, rec: Recorder) -> dict[str, Any]:
    """Wrap the functions moving mass into/out of the surface pools."""
    originals = {
        "_deposit_surface_mass": core_cls._deposit_surface_mass,
        "_scale_surface_mass": core_cls._scale_surface_mass,
        "_consume_surface_mass": core_cls._consume_surface_mass,
    }

    def deposit(
        self: Any, pathogen_id: str, zone_name: str, mass: float,
    ) -> None:
        rec.core = self
        originals["_deposit_surface_mass"](self, pathogen_id, zone_name, mass)
        if pathogen_id != rec.pathogen_id or float(mass) <= 0.0:
            return
        site = _caller_name()
        vclass = _venue_class(self, zone_name)
        rec.epoch_acc[f"deposit_{site}"] += float(mass)
        rec.epoch_acc[f"deposit_venue_{vclass}"] += float(mass)
        rec.epoch_acc["deposited"] += float(mass)
        rec.totals[f"deposit_{site}"] += float(mass)
        rec.totals[f"deposit_venue_{vclass}"] += float(mass)

    def scale(
        self: Any, pathogen_id: str, zone_name: str, factor: float,
    ) -> None:
        pools = self.surface_pools_by_pathogen.get(pathogen_id) or {}
        before = float(pools.get(zone_name, 0.0))
        originals["_scale_surface_mass"](self, pathogen_id, zone_name, factor)
        if pathogen_id != rec.pathogen_id:
            return
        after = float(
            (self.surface_pools_by_pathogen.get(pathogen_id) or {}).get(
                zone_name, 0.0,
            ),
        )
        removed = before - after
        if removed <= 0.0:
            return
        site = _caller_name()
        rec.epoch_acc[f"removed_{site}"] += removed
        rec.totals[f"removed_{site}"] += removed

    def consume(
        self: Any,
        pathogen_id: str,
        zone_name: str,
        delivered: float,
        previous_mass: float,
    ) -> None:
        originals["_consume_surface_mass"](
            self, pathogen_id, zone_name, delivered, previous_mass,
        )
        if pathogen_id == rec.pathogen_id and delivered > 0.0:
            vclass = _venue_class(self, zone_name)
            rec.epoch_acc[f"consumed_venue_{vclass}"] += float(delivered)

    core_cls._deposit_surface_mass = deposit
    core_cls._scale_surface_mass = scale
    core_cls._consume_surface_mass = consume
    return originals


def _wrap_events(core_cls: type, rec: Recorder) -> dict[str, Any]:
    """Wrap stool reroutes, emesis filing, and sanitary pickup requests."""
    originals = {
        "_route_stool_event_venue": core_cls._route_stool_event_venue,
        "_emit_emesis": core_cls._emit_emesis,
        "_fomite_pickup_request": core_cls._fomite_pickup_request,
        "_deliver_sanitary_pooled_requests": (
            core_cls._deliver_sanitary_pooled_requests
        ),
        "_deliver_sanitary_requests_by_class": (
            core_cls._deliver_sanitary_requests_by_class
        ),
    }

    def stool_route(
        self: Any, agent: Any, pathogen_id: str, profile: Any,
        zone_name: str | None,
    ) -> None:
        venue = (
            self._sanitary_venue(zone_name, agent)
            if zone_name is not None
            else None
        )
        originals["_route_stool_event_venue"](
            self, agent, pathogen_id, profile, zone_name,
        )
        if pathogen_id != rec.pathogen_id:
            return
        vclass = _venue_class(self, venue) if venue is not None else "none"
        rec.stool_venues[vclass] += 1
        rec.epoch_acc[f"stool_to_{vclass}"] += 1

    def emit_emesis(
        self: Any, agent: Any, pathogen_id: str, profile: dict,
        zone_name: str, epoch: int,
    ) -> float:
        gained = originals["_emit_emesis"](
            self, agent, pathogen_id, profile, zone_name, epoch,
        )
        if pathogen_id == rec.pathogen_id and gained > 0.0:
            vclass = _venue_class(self, zone_name)
            rec.emesis_zone_mass[vclass] += float(gained)
            rec.epoch_acc[f"emesis_{vclass}"] += float(gained)
        return gained

    def pickup_request(
        self: Any, target: Any, zone_name: str, surface_mass: float,
        epoch: int,
    ) -> float:
        site = _caller_name()
        request = originals["_fomite_pickup_request"](
            self, target, zone_name, surface_mass, epoch,
        )
        if site == "_sanitary_pickup_pooled":
            rec.epoch_acc["sanitary_requests"] += 1
            rec.epoch_acc["sanitary_request_mass"] += float(request)
            vclass = _venue_class(self, zone_name)
            rec.epoch_acc[f"request_poolmass_{vclass}"] += float(surface_mass)
        return request

    def deliver_pooled(
        self: Any, requests: list, venue: str, surface_mass: float,
        scale: float, epoch: int, *args: Any, **kwargs: Any,
    ) -> float:
        delivered = originals["_deliver_sanitary_pooled_requests"](
            self, requests, venue, surface_mass, scale, epoch,
            *args, **kwargs,
        )
        rec.epoch_acc["sanitary_delivered"] += float(delivered)
        rec.epoch_acc[f"delivered_venue_{_venue_class(self, venue)}"] += (
            float(delivered)
        )
        return delivered

    def deliver_by_class(
        self: Any, requests: list, venue: str, epoch: int,
        *args: Any, **kwargs: Any,
    ) -> None:
        originals["_deliver_sanitary_requests_by_class"](
            self, requests, venue, epoch, *args, **kwargs,
        )
        rec.epoch_acc["sanitary_delivered_by_class_calls"] += 1

    core_cls._route_stool_event_venue = stool_route
    core_cls._emit_emesis = emit_emesis
    core_cls._fomite_pickup_request = pickup_request
    core_cls._deliver_sanitary_pooled_requests = deliver_pooled
    core_cls._deliver_sanitary_requests_by_class = deliver_by_class
    return originals


def _wrap_epoch_marks(core_cls: type, rec: Recorder) -> dict[str, Any]:
    """Epoch boundary marks so every per-epoch accumulator is dated."""
    originals = {"_pathway_fomite": core_cls._pathway_fomite}

    def pathway_fomite(
        self: Any, epoch: int, *args: Any, **kwargs: Any,
    ) -> Any:
        rec.core = self
        rec.epoch = int(epoch)
        return originals["_pathway_fomite"](self, epoch, *args, **kwargs)

    core_cls._pathway_fomite = pathway_fomite
    return originals


def _epoch_observer(rec: Recorder, pathogen_id: str) -> Any:
    """Per-epoch census: telemetry deltas, pools, infections, confinement."""

    def observe(sim: Any, _work: Any) -> None:
        core = sim.tx_core
        rec.core = core
        rec._seed_ids = set(
            getattr(sim.engine, "explicit_seed_agent_ids", None) or [],
        )
        telemetry = dict(core.sanitary_telemetry)
        row: dict[str, Any] = {"epoch": int(getattr(sim, "epoch", rec.epoch))}
        for key, value in telemetry.items():
            delta = float(value) - float(rec._prev_telemetry.get(key, 0.0))
            row[f"tele_{key}"] = delta
        rec._prev_telemetry = telemetry
        pools = rec.venue_pools()
        for vclass, mass in pools.items():
            row[f"pool_{vclass}"] = mass
        row["pool_patches"] = rec.patch_pool_total()
        agents = sim.engine.agents
        infected_now: set[int] = set()
        hand_positive = 0
        hand_max = 0.0
        confined = 0
        for agent in agents:
            if agent.is_infected_with(pathogen_id):
                infected_now.add(int(agent.agent_id))
            if float(agent.hand_load_by_pathogen.get(pathogen_id, 0.0)) > 0.0:
                hand_positive += 1
                hand_max = max(
                    hand_max,
                    float(agent.hand_load_by_pathogen.get(pathogen_id, 0.0)),
                )
            if core._cabin_confinement_active(agent):
                confined += 1
        row["infected_total"] = len(infected_now)
        row["new_infections"] = len(
            (infected_now - rec._seen_infected) - rec._seed_ids,
        )
        rec._seen_infected |= infected_now
        row["hand_positive_agents"] = hand_positive
        row["hand_load_max"] = hand_max
        row["confined_agents"] = confined
        row.update(
            {key: float(value) for key, value in rec.epoch_acc.items()},
        )
        rec.epoch_rows.append(row)
        rec.epoch_acc.clear()

    return observe


@contextmanager
def instrumented(rec: Recorder) -> Any:
    """Install the read-only wrappers for the duration of one run."""
    core_cls = tc.TransmissionCore
    saved: dict[str, Any] = {}
    saved.update(_wrap_mass_books(core_cls, rec))
    saved.update(_wrap_events(core_cls, rec))
    saved.update(_wrap_epoch_marks(core_cls, rec))
    try:
        yield
    finally:
        for name, method in saved.items():
            setattr(core_cls, name, method)


def _emit_emesis_pre604(
    self: Any,
    agent: Any,
    pathogen_id: str,
    profile: dict,
    zone_name: str,
    epoch: int,
) -> float:
    """Pre-#604 emesis filing: footprint share, zone-pool deposit.

    Identical draw order to the shipped emitter (volume, then aerosol
    fraction, per due episode); only the filing target and the touchable
    share's denominator differ. ``_deposit_emesis_pre604`` adds the zone-pool
    deposit the shipped code moved into ``EmesisPatch``.
    """
    eligible = self._emesis_phase(agent, pathogen_id, profile)
    if eligible is None:
        return 0.0
    _, age = eligible
    schedule = agent.emesis_episode_schedule_by_pathogen.get(pathogen_id, [])
    due = [event_age for event_age in schedule if event_age <= age]
    if not due:
        return 0.0
    agent.emesis_episode_schedule_by_pathogen[pathogen_id] = [
        event_age for event_age in schedule if event_age > age
    ]
    volume_low, volume_high = self._emesis_range(
        profile, "emesis_volume_ml_range", tc.EMESIS_VOLUME_ML_RANGE,
    )
    aerosol_low, aerosol_high = self._emesis_range(
        profile,
        "emesis_aerosol_fraction_range",
        tc.EMESIS_AEROSOL_FRACTION_RANGE,
    )
    host_titre = self._emesis_host_titre(agent, pathogen_id, profile)
    censored = agent.emesis_censored_below_lod_by_pathogen.get(
        pathogen_id, False,
    )
    area = float(profile.get(
        "emesis_deposition_area_m2", tc.EMESIS_DEPOSITION_AREA_M2,
    ))
    touchable_fraction = min(
        1.0, self._fomite_surface_area(zone_name) / area,
    )
    records = agent.emesis_deposition_records_by_pathogen.setdefault(
        pathogen_id, [],
    )
    pool_gain_total = 0.0
    for _ in due:
        volume = math.exp(self.rng.uniform(
            math.log(volume_low), math.log(volume_high),
        ))
        aerosol_fraction = math.exp(self.rng.uniform(
            math.log(aerosol_low), math.log(aerosol_high),
        ))
        episode_load = volume * host_titre
        surface_load = episode_load * (1.0 - aerosol_fraction)
        aerosol_load = episode_load * aerosol_fraction
        pending = self.emesis_aerosol_pending_by_pathogen.setdefault(
            pathogen_id, {},
        )
        pending[zone_name] = pending.get(zone_name, 0.0) + aerosol_load
        emitted = self._emesis_aerosol_emitted_by_pathogen.setdefault(
            pathogen_id, {},
        )
        emitted.setdefault(zone_name, []).append((agent, aerosol_load))
        pool_gain = surface_load * touchable_fraction
        records.append({
            "epoch": int(epoch),
            "zone": zone_name,
            "volume_ml": volume,
            "titre_gec_per_ml": host_titre,
            "censored_below_lod": bool(censored),
            "episode_load": episode_load,
            "surface_load": surface_load,
            "aerosol_load": aerosol_load,
            "pool_gain": pool_gain,
            "non_touchable": surface_load - pool_gain,
            "touchable_fraction": touchable_fraction,
        })
        if pool_gain > 0.0:
            self._deposit_surface_mass(pathogen_id, zone_name, pool_gain)
        if self.blackwater_tank is not None:
            self.blackwater_tank.add_copies(
                pathogen_id,
                (surface_load - pool_gain)
                * self.blackwater_tank.emesis_drain_capture_fraction,
                "emesis",
            )
        pool_gain_total += pool_gain
    return pool_gain_total


def _deposit_emesis_pre604(
    self: Any,
    agent: Any,
    pathogen_id: str,
    zone_name: str,
    epoch: int,
    profile: dict,
) -> float:
    """Pre-#604 counterpart: pool deposit already filed inside the emitter."""
    return self._emit_emesis(
        agent, pathogen_id, profile, zone_name, epoch,
    )


@contextmanager
def arm_patches(arm: str) -> Any:
    """The in-process arms: gate floor at zero, pre-#604 emesis filing."""
    if arm == "gate_off":
        saved = fomite_surfaces.SURFACE_PICKUP_MIN_GEC
        fomite_surfaces.SURFACE_PICKUP_MIN_GEC = 0.0
        try:
            yield
        finally:
            fomite_surfaces.SURFACE_PICKUP_MIN_GEC = saved
        return
    if arm == "emesis_zonepool":
        saved_emit = tc.TransmissionCore._emit_emesis
        saved_deposit = tc.TransmissionCore._deposit_emesis
        tc.TransmissionCore._emit_emesis = _emit_emesis_pre604
        tc.TransmissionCore._deposit_emesis = _deposit_emesis_pre604
        try:
            yield
        finally:
            tc.TransmissionCore._emit_emesis = saved_emit
            tc.TransmissionCore._deposit_emesis = saved_deposit
        return
    yield


def _tier_specs(
    manifest_path: Path, tier: str, epochs_override: int | None = None,
) -> dict[int, dict[str, Any]]:
    """seed -> verbatim campaign spec dict for the tier."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    specs = {}
    for _rid, spec in generate_tier_runs(
        manifest, tier, epochs_override=epochs_override,
    ):
        specs[int(spec["run"]["random_seed"])] = spec
    return specs


def _apply_arm(spec: dict[str, Any], arm: str) -> dict[str, Any]:
    """Merge the arm's config/pathogen overrides into the verbatim spec."""
    spec = json.loads(json.dumps(spec))
    config_patch, pathogen_patch = _arm_overrides(arm)
    spec["config_overrides"] = _deep_merge(
        spec.get("config_overrides") or {}, config_patch,
    )
    spec["pathogen_overrides"] = _deep_merge(
        spec.get("pathogen_overrides") or {}, pathogen_patch,
    )
    return spec


def run_seed(
    *, spec_dict: dict[str, Any], arm: str, seed: int,
) -> dict[str, Any]:
    """Run one instrumented arm voyage and return its measurement."""
    rec = Recorder(pathogen_id=PATHOGEN_ID)
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
        spec_path = resolve_child_path(tmp, "run_spec.json")
        with validated_open(
            spec_path, "w", allowed_roots=(tmp,), encoding="utf-8",
        ) as handle:
            handle.write(json.dumps(spec_dict))
        picard_spec = PicardRunSpec.from_picard_json(str(REPO_ROOT), spec_path)
        # arm_patches first: the recording wrappers then capture the patched
        # functions as their originals, so the patched arms are still traced.
        with arm_patches(arm), instrumented(rec):
            sim = ShipSimulation(picard_spec, display=False)
            sim.epoch_observer = _epoch_observer(rec, PATHOGEN_ID)
            sim.run()
    return _summarise(rec, arm, seed)


def _summarise(rec: Recorder, arm: str, seed: int) -> dict[str, Any]:
    """Per-epoch table plus voyage summary for one (arm, seed) run."""
    rows = rec.epoch_rows
    peak_dose = max(
        (float(row.get("tele_dose_delivered", 0.0)) for row in rows),
        default=0.0,
    )
    total_dose = sum(
        float(row.get("tele_dose_delivered", 0.0)) for row in rows
    )
    total_new = sum(int(row.get("new_infections", 0)) for row in rows)
    shared_pool_peak = max(
        (float(row.get("pool_shared_head", 0.0)) for row in rows),
        default=0.0,
    )
    cabin_pool_peak = max(
        (float(row.get("pool_cabin_fittings", 0.0)) for row in rows),
        default=0.0,
    )
    deposit_sites = {
        key: value for key, value in rec.totals.items()
        if key.startswith("deposit_")
    }
    return {
        "arm": arm,
        "seed": seed,
        "pathogen_id": rec.pathogen_id,
        "summary": {
            "dose_delivered_total": total_dose,
            "dose_delivered_epoch_peak": peak_dose,
            "new_infections_total": total_new,
            "infected_total_final": (
                rows[-1]["infected_total"] if rows else 0
            ),
            "shared_head_pool_peak_gec": shared_pool_peak,
            "cabin_fittings_pool_peak_gec": cabin_pool_peak,
            "deposit_by_call_site_gec": {
                key.removeprefix("deposit_"): value
                for key, value in deposit_sites.items()
                if not key.startswith("deposit_venue_")
            },
            "deposit_by_venue_class_gec": {
                key.removeprefix("deposit_venue_"): value
                for key, value in deposit_sites.items()
                if key.startswith("deposit_venue_")
            },
            "stool_venue_destinations": dict(rec.stool_venues),
            "emesis_mass_by_venue_class_gec": dict(rec.emesis_zone_mass),
            "sanitary_requests_total": int(
                sum(row.get("sanitary_requests", 0) for row in rows)
            ),
        },
        "epoch_rows": rows,
    }


def _identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        raise argparse.ArgumentTypeError(f"invalid identifier: {value!r}")
    return value


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--tier", type=_identifier, default=DEFAULT_TIER)
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument(
        "--seeds", type=int, nargs="+", default=list(DEFAULT_SEEDS),
    )
    parser.add_argument(
        "--index", type=int, default=None,
        help="run only seeds[index] (Batch canary; AWS_BATCH_JOB_ARRAY_INDEX "
             "is reserved and cannot be overridden via env)",
    )
    parser.add_argument(
        "--epochs-override", type=int, default=None,
        help="smoke only: truncate the cell's epoch count; final numbers "
             "always run at the tier's own duration",
    )
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = Path(
        prepare_output_directory(str(args.out), allowed_roots=(str(REPO_ROOT),)),
    )
    specs = _tier_specs(args.manifest, args.tier, args.epochs_override)
    seeds = (
        [args.seeds[args.index]] if args.index is not None else args.seeds
    )
    for seed in seeds:
        spec = _apply_arm(specs[seed], args.arm)
        summary = run_seed(spec_dict=spec, arm=args.arm, seed=seed)
        filename = (
            f"deposit_attr_{args.tier}_{args.arm}_seed{seed}.json.gz"
        )
        path = resolve_child_path(str(out_dir), filename)
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=1)
        s = summary["summary"]
        print(
            f"[{args.arm} s{seed}] dose_total={s['dose_delivered_total']:.4g} "
            f"peak={s['dose_delivered_epoch_peak']:.4g} "
            f"new_inf={s['new_infections_total']} "
            f"pool_peak_shared={s['shared_head_pool_peak_gec']:.4g} "
            f"cabin={s['cabin_fittings_pool_peak_gec']:.4g} "
            f"requests={s['sanitary_requests_total']} "
            f"-> {path}",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
