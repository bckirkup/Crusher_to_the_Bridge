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
``emesis_zonepool`` in-process semantic revert of the #604 filing via the
                    shipped emitter: ``_zone_floor_area_m2`` is patched to
                    answer the zone's fomite surface area (making the shipped
                    ``min(1, high_touch/max(floor, area))`` equal the
                    pre-change ``min(1, high_touch/area)``) and each
                    EmesisPatch filed is immediately re-filed into the zone
                    surface pool. Draw order inside the emitter is preserved;
                    downstream patch-pickup draws vanish with the patches, so
                    the arm is not bit-identical.
``report_scale``    ``pathogen_overrides.norwalk_gi.observation_model
                    .reporting_belief_scaling = "trust_medical"`` -- the
                    pre-NORO-CHANNEL-02 stacking, as a labelled baseline.
``pre_all``       joint pre-change baseline: all six candidates at their
                    labelled baseline simultaneously (config arms merged;
                    gate floor and emesis filing patched in-process). Added
                    before running, after the single-arm grid: the decisive
                    test for a collapse that is multiplicative across the
                    named set rather than carried by one change.
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
    resolve_repo_path,
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
    if arm == "pre_all":
        # Joint pre-change baseline: every candidate at its labelled
        # baseline/off state simultaneously. The in-process arms
        # (gate_off, emesis_zonepool) return empty patches here and apply
        # inside ``arm_patches``.
        config_patch: dict[str, Any] = {}
        pathogen_patch: dict[str, Any] = {}
        for sub in (
            "blackwater_off", "watch_off", "cabin_fomite_off", "report_scale",
        ):
            c_patch, p_patch = _arm_overrides(sub)
            config_patch = _deep_merge(config_patch, c_patch)
            pathogen_patch = _deep_merge(pathogen_patch, p_patch)
        return config_patch, pathogen_patch
    raise ValueError(f"unknown arm: {arm!r}")


ARMS = (
    "base",
    "blackwater_off",
    "watch_off",
    "gate_off",
    "emesis_zonepool",
    "report_scale",
    "cabin_fomite_off",
    "pre_all",
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


def _pool_mass(core: Any, pathogen_id: str, zone_name: str) -> float:
    """Current surface-pool mass for one (pathogen, zone) cell."""
    pools = core.surface_pools_by_pathogen.get(pathogen_id) or {}
    return float(pools.get(zone_name, 0.0))


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
        on_pathogen = pathogen_id == rec.pathogen_id
        before = _pool_mass(self, pathogen_id, zone_name) if on_pathogen else 0.0
        originals["_scale_surface_mass"](self, pathogen_id, zone_name, factor)
        if not on_pathogen:
            return
        removed = before - _pool_mass(self, pathogen_id, zone_name)
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
        _agent_census(rec, sim, core, pathogen_id, row)
        row.update(
            {key: float(value) for key, value in rec.epoch_acc.items()},
        )
        rec.epoch_rows.append(row)
        rec.epoch_acc.clear()

    return observe


def _agent_census(
    rec: Recorder,
    sim: Any,
    core: Any,
    pathogen_id: str,
    row: dict[str, Any],
) -> None:
    infected_now: set[int] = set()
    hand_positive = 0
    hand_max = 0.0
    confined = 0
    for agent in sim.engine.agents:
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


def _fomite_area_as_floor(self: Any, zone_name: str) -> float:
    """Pre-#604 touchable denominator, posed as the zone's floor area.

    Installed over ``_zone_floor_area_m2`` on the ``emesis_zonepool`` arm so
    the shipped emitter's ``min(1, high_touch / max(floor, area))`` reduces
    to the pre-change ``min(1, high_touch / area)`` — identical whether
    fomite area exceeds the bolus footprint (both saturate at 1) or not
    (both give fomite/area).
    """
    return float(self._fomite_surface_area(zone_name))


def _zonepool_emitter(saved_emit: Any) -> Any:
    """Wrap the shipped emitter with the pre-#604 zone-pool filing.

    The shipped emit body runs verbatim — same draws, same records — while
    the patched floor makes its touchable share the pre-change one; each
    ``EmesisPatch`` it files is re-filed into the zone surface pool via
    ``_deposit_surface_mass``, where pre-#604 ``_deposit_emesis`` put the
    gain. Call-site accounting records the deposit under this wrapper.
    """
    def emit_emesis_zonepool(
        self: Any,
        agent: Any,
        pathogen_id: str,
        profile: dict,
        zone_name: str,
        epoch: int,
    ) -> float:
        gained = saved_emit(
            self, agent, pathogen_id, profile, zone_name, epoch,
        )
        pools = self.emesis_patch_pools_by_pathogen.get(pathogen_id) or {}
        for patch in pools.pop(zone_name, []):
            if float(patch.mass) > 0.0:
                self._deposit_surface_mass(
                    pathogen_id, zone_name, float(patch.mass),
                )
        return gained
    return emit_emesis_zonepool


@contextmanager
def arm_patches(arm: str) -> Any:
    """In-process arms: gate floor at zero, pre-#604 emesis filing, both."""
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
        saved_floor = tc.TransmissionCore._zone_floor_area_m2
        tc.TransmissionCore._emit_emesis = _zonepool_emitter(saved_emit)
        tc.TransmissionCore._zone_floor_area_m2 = _fomite_area_as_floor
        try:
            yield
        finally:
            tc.TransmissionCore._emit_emesis = saved_emit
            tc.TransmissionCore._zone_floor_area_m2 = saved_floor
        return
    if arm == "pre_all":
        saved_gate = fomite_surfaces.SURFACE_PICKUP_MIN_GEC
        saved_emit = tc.TransmissionCore._emit_emesis
        saved_floor = tc.TransmissionCore._zone_floor_area_m2
        fomite_surfaces.SURFACE_PICKUP_MIN_GEC = 0.0
        tc.TransmissionCore._emit_emesis = _zonepool_emitter(saved_emit)
        tc.TransmissionCore._zone_floor_area_m2 = _fomite_area_as_floor
        try:
            yield
        finally:
            fomite_surfaces.SURFACE_PICKUP_MIN_GEC = saved_gate
            tc.TransmissionCore._emit_emesis = saved_emit
            tc.TransmissionCore._zone_floor_area_m2 = saved_floor
        return
    yield


def _tier_specs(
    manifest_path: Path, tier: str, epochs_override: int | None = None,
) -> dict[int, dict[str, Any]]:
    """seed -> verbatim campaign spec dict for the tier."""
    safe_manifest = Path(
        resolve_repo_path(str(REPO_ROOT), str(manifest_path)),
    )
    with validated_open(
        str(safe_manifest), "r", allowed_roots=(str(REPO_ROOT),), encoding="utf-8",
    ) as handle:
        manifest = json.load(handle)
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
