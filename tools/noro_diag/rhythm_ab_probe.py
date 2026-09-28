#!/usr/bin/env python3
"""NORO-RHYTHM-01 probe: one campaign cell under the rhythm-layer A/B.

Purpose
-------
The schedule-conditioned rhythm layer (``engines/rhythm_layer.py``,
spec ``docs/rhythm/rhythm_spec.md`` section 5) claims to fix four measured
norovirus failure modes: secondary vomits landing in immune cabins
(NORO-GROWTH-01), emesis timing uncoupled from meal endings, port-heavy hulls
missing ashore/queue structure, and zero take-off on expedition hulls
(NORO-REBASE-01 0/2000). This driver replays one manifest-generated spec per
invocation under one of two arms -- ``off`` injects
``config_overrides.rhythm.enabled = false`` (the labelled baseline claiming
byte-identical behaviour and zero extra RNG draws) and ``on`` injects
``true``. Everything else in the spec is verbatim, so a paired cell differs
only by the flag.

Method
------
The engine is not modified. All observations are read-only wrappers plus the
ship-level epoch observer:

* ``RhythmLayer.deal_day`` -- the wiring witness: per dealt day, the day type,
  the active SOP names, and every committed event's class, zone, occupancy
  window and synchronized-egress minute (the clock-correlation input).
* ``TransmissionCore._epoch_zone_occupants`` -- the engine's own zone map is
  cached on the recorder each epoch so the emesis wrapper can score landing
  occupancy against the same map the dose machinery used.
* ``TransmissionCore._emit_emesis`` -- per emitted bolus: zone, zone type,
  the occupants present (total / susceptible / already infected), depositor
  generation and class (import vs acquired), the post-prandial sentinel the
  placement pass stamped, and the deposited loads. Call counters split by the
  sentinel's three states also count *deferred* emits (a call with a
  non-empty schedule that produced no deposition record under
  ``post_prandial is False``), so the modulation claim is measured in both
  directions.
* ``TransmissionCore._resolve_pathogen_challenge`` -- acquisition pedigree:
  each newly infected host gets source agent, resolved generation (source
  pedigree first, strain home second), the dose the challenge read, and
  whether the host was ashore when dosed (the ashore-dosing defect witness).
* ``ShipSimulation.epoch_observer`` -- per epoch, the full zone-occupancy
  count map, ashore/confined headcounts, infected counts, and a chained
  per-epoch canonical state digest (agent id, location, activity, ashore,
  symptomatic, infected-pathogen set) whose voyage digest is the
  byte-identity witness for the ``off`` arm against the pre-rhythm tree.

Wrappers only read engine state; none consumes an engine RNG draw.

Inputs
------
``--manifest``/``--tier``/``--index`` pick the campaign cell; ``--arm`` is one
of ``off``/``on`` and injects the flag. ``--spec-json`` runs an arbitrary spec
file verbatim (byte-identity mode: the pre-rhythm tree has no flag to inject,
so the same spec file is replayed on both trees and the flag-free ``--arm``
default leaves ``config_overrides`` untouched). ``--epochs-override`` caps
``run.num_epochs`` for short witness cells.

Outputs
-------
One ``<arm>/<tier>/<run_id>.zip`` per run carrying ``summary.json`` in the
campaign layout (parameters / timeseries / derived / summary /
cost_accounting, so ``score_anchors`` ingests it directly) plus
``rhythm.json.gz`` with the tables above and the wiring witnesses.

Nothing here fits or selects a parameter value; dose_adjustment comes from
the manifest tier verbatim.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import re
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
_CAMPAIGN_DIR = REPO_ROOT / "picard_framework" / "runs" / "mega_cruise_campaign"
if str(_CAMPAIGN_DIR) not in sys.path:
    sys.path.insert(0, str(_CAMPAIGN_DIR))

from campaign_runner import generate_tier_runs  # noqa: E402

from engines import transmission_core as tc  # noqa: E402
from picard_framework.run_spec import PicardRunSpec  # noqa: E402
from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_child_path,
    resolve_repo_path,
    validated_open,
)
from tools.noro_diag.growth_chain_census import (  # noqa: E402
    GEN_UNRESOLVED,
    _acquired_gen,
)
from tools.noro_diag.per_host_dose_challenge import (  # noqa: E402
    _attach_voyage_blocks,
)

try:  # the pre-rhythm tree has no module; the off arm must still run there
    from engines.rhythm_layer import RhythmLayer
except ImportError:  # pragma: no cover - exercised on the pre-rhythm tree
    RhythmLayer = None  # type: ignore[assignment,misc]

MINUTES_PER_DAY = 1440  # clock-exempt: minutes-of-day, not a unit conversion

_ASHORE_LOCATION = "Ashore"
_ISOLATED_LOCATION = "Isolated_In_Quarters"
_DEPARTED_LOCATION = "Departed"


# ── Recorder ──────────────────────────────────────────────────────────


@dataclass
class RhythmRecorder:
    """Every observation taken from one instrumented voyage."""

    pathogen_id: str
    # host -> generation (0 = import); filled lazily as hosts appear.
    host_gen: dict[int, int] = field(default_factory=dict)
    strain_home: dict[str, int] = field(default_factory=dict)
    acquired_ids: set[int] = field(default_factory=set)
    import_ids: set[int] = field(default_factory=set)
    epoch0_done: bool = False
    # Latest engine zone map (epoch the core is processing).
    zone_occupants: dict[str, list[Any]] = field(default_factory=dict)
    compartment_occupants: dict[str, list[Any]] = field(default_factory=dict)
    # Row tables.
    emesis_rows: list[dict[str, Any]] = field(default_factory=list)
    acquisition_rows: list[dict[str, Any]] = field(default_factory=list)
    dealt_days: list[dict[str, Any]] = field(default_factory=list)
    epoch_rows: list[dict[str, Any]] = field(default_factory=list)
    epoch_state_digests: list[str] = field(default_factory=list)
    ashore_dosed_rows: list[dict[str, Any]] = field(default_factory=list)
    # Emit-call counters split by the post-prandial sentinel state.
    emit_calls: dict[str, int] = field(
        default_factory=lambda: defaultdict(int),
    )
    emits_deferred: dict[str, int] = field(
        default_factory=lambda: defaultdict(int),
    )
    ashore_dosed_epochs: int = 0
    commitments_total: int = 0
    rhythm_attached: bool = False
    ignited: bool = False

    def gen_of(self, agent_id: Any) -> int:
        if agent_id is None:
            return GEN_UNRESOLVED
        return self.host_gen.get(int(agent_id), GEN_UNRESOLVED)

    def gen_class_of(self, agent_id: Any) -> str:
        if agent_id is None:
            return "unknown"
        aid = int(agent_id)
        if aid in self.acquired_ids:
            return "acquired"
        if aid in self.import_ids:
            return "import"
        return "unknown"


# ── Wrappers ──────────────────────────────────────────────────────────


def _wrap_cabin_compartments(core_cls: type, rec: RhythmRecorder) -> Any:
    """Cache the post-split compartment map (``zone::cabinNNN`` -> occupants)
    that ``_pathway_fomite`` feeds ``_fomite_hand_deposits`` — emesis lands in
    these per-stateroom keys, which never appear in the parent zone map."""
    original = core_cls._cabin_compartments

    def wrapper(self: Any, zone_occupants: dict) -> dict:
        out = original(self, zone_occupants)
        rec.compartment_occupants = out
        return out

    return wrapper


def _wrap_zone_occupants(core_cls: type, rec: RhythmRecorder) -> Any:
    """Cache the engine's own zone -> occupants map for the emit wrapper."""
    original = core_cls._epoch_zone_occupants

    def wrapper(self: Any, agents: list, epoch: int) -> Any:
        out = original(self, agents, epoch)
        rec.zone_occupants = out
        return out

    return wrapper


def _pp_state(agent: Any) -> str:
    flag = getattr(agent, "_rhythm_post_prandial", None)
    if flag is None:
        return "off"
    return "post_prandial" if flag else "outside_window"


def _occupancy_snapshot(
    rec: RhythmRecorder, core: Any, zone_name: str,
) -> dict[str, int]:
    occupants = (
        rec.compartment_occupants.get(zone_name)
        or rec.zone_occupants.get(zone_name)
        or []
    )
    susceptible = sum(
        1 for a in occupants if not a.is_infected_with(rec.pathogen_id)
    )
    return {
        "n_occupants": len(occupants),
        "n_susceptible": int(susceptible),
        "n_infected": len(occupants) - int(susceptible),
    }


def _wrap_emit_emesis(core_cls: type, rec: RhythmRecorder) -> Any:
    """Per-bolus landing record: zone, occupants, depositor, sentinel."""
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
        schedule_len = len(
            agent.emesis_episode_schedule_by_pathogen.get(
                pathogen_id, [],
            ),
        )
        pool_gain = original(
            self, agent, pathogen_id, profile, zone_name, epoch,
        )
        if pathogen_id != rec.pathogen_id:
            return pool_gain
        state = _pp_state(agent)
        rec.emit_calls[state] += 1
        records = agent.emesis_deposition_records_by_pathogen.get(
            pathogen_id, [],
        )[before:]
        if not records:
            if schedule_len:
                rec.emits_deferred[state] += 1
            return pool_gain
        if pool_gain > 0:
            rec.ignited = True
        aid = int(agent.agent_id)
        occupancy = _occupancy_snapshot(rec, self, zone_name)
        for record in records:
            rec.emesis_rows.append({
                "epoch": int(epoch),
                "agent_id": aid,
                "gen": rec.gen_of(aid),
                "gen_class": rec.gen_class_of(aid),
                "zone": zone_name,
                "zone_type": str(self.zone_types.get(zone_name) or ""),
                "post_prandial": getattr(
                    agent, "_rhythm_post_prandial", None,
                ),
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


def _record_acquisition(
    rec: RhythmRecorder,
    agent: Any,
    epoch: int,
    p_dose: float,
    new_events: list,
) -> None:
    aid = int(agent.agent_id)
    acquired_strain = (
        (agent.infections.get(rec.pathogen_id) or {}).get("strain_id")
    )
    row: dict[str, Any] = {
        "epoch": int(epoch),
        "agent_id": aid,
        "dose_read": float(p_dose),
        "location": str(agent.current_location),
        "ashore": bool(getattr(agent, "ashore", False)),
        "source_agent_id": None,
        "dominant_pathway": None,
    }
    if new_events:
        event = new_events[-1]
        row["source_agent_id"] = getattr(event, "source_agent_id", None)
        row["dominant_pathway"] = getattr(event, "pathway", None)
        parent_strain = getattr(event, "source_strain_id", None)
    else:
        parent_strain = None
    gen = _acquired_gen(
        rec, row["source_agent_id"], parent_strain, acquired_strain,
    )
    row["gen"] = gen if 0 <= gen < GEN_UNRESOLVED else "unresolved"
    rec.host_gen[aid] = gen
    rec.acquired_ids.add(aid)
    if acquired_strain:
        rec.strain_home.setdefault(str(acquired_strain), aid)
    rec.acquisition_rows.append(row)


def _wrap_challenge(core_cls: type, rec: RhythmRecorder) -> Any:
    """Acquisition pedigree + the ashore-dosing defect witness."""
    original = core_cls._resolve_pathogen_challenge

    def wrapper(
        self: Any, epoch: int, agent: Any, pathogen_id: str,
        agent_pathogen_doses: dict, agent_pathway_doses: Any,
        matrix: Any, events: list,
    ) -> None:
        if pathogen_id != rec.pathogen_id:
            original(
                self, epoch, agent, pathogen_id, agent_pathogen_doses,
                agent_pathway_doses, matrix, events,
            )
            return
        aid = int(agent.agent_id)
        p_dose = float(
            agent_pathogen_doses.get(aid, {}).get(pathogen_id, 0.0),
        )
        if p_dose > 0 and (
            getattr(agent, "ashore", False)
            or agent.current_location == _ASHORE_LOCATION
        ):
            rec.ashore_dosed_epochs += 1
            if len(rec.ashore_dosed_rows) < 64:
                rec.ashore_dosed_rows.append({
                    "epoch": int(epoch), "agent_id": aid,
                    "dose_read": p_dose,
                })
        was_infected = bool(agent.is_infected_with(pathogen_id))
        n_events = len(events)
        original(
            self, epoch, agent, pathogen_id, agent_pathogen_doses,
            agent_pathway_doses, matrix, events,
        )
        if not was_infected and agent.is_infected_with(pathogen_id):
            _record_acquisition(
                rec, agent, epoch, p_dose, events[n_events:],
            )
        elif was_infected and aid not in rec.acquired_ids:
            rec.import_ids.add(aid)
            rec.host_gen.setdefault(aid, 0)

    return wrapper


def _commitment_rows(rhythm: Any) -> list[dict[str, Any]]:
    """Per (event, zone, window) participation table for one dealt day."""
    grouped: dict[tuple, int] = defaultdict(int)
    for agent_commitments in rhythm._commitments.values():
        for c in agent_commitments:
            key = (
                c.event_id, c.event_class, c.zone,
                c.start_min, c.end_min, c.egress_min, c.is_meal,
            )
            grouped[key] += 1
    return [
        {
            "event_id": key[0],
            "event_class": key[1],
            "zone": key[2],
            "start_min": key[3],
            "end_min": key[4],
            "egress_min": key[5],
            "is_meal": key[6],
            "participants": n,
        }
        for key, n in sorted(grouped.items(), key=lambda kv: str(kv[0]))
    ]


def _wrap_deal_day(rec: RhythmRecorder) -> Any:
    """The wiring witness: committed events per dealt day."""
    original = RhythmLayer.deal_day

    def wrapper(
        self: Any, agents: list, day_type: str,
        sop_names: set, voyage_day: int,
    ) -> Any:
        result = original(self, agents, day_type, sop_names, voyage_day)
        events = _commitment_rows(self)
        rec.commitments_total += sum(e["participants"] for e in events)
        rec.dealt_days.append({
            "voyage_day": int(voyage_day),
            "day_type": str(day_type),
            "sop_names": sorted(str(s) for s in sop_names),
            "meals_to_cabin": bool(self.meals_to_cabin),
            "embarkation_covered": bool(self.embarkation_covered),
            "events": events,
        })
        return result

    return wrapper


@contextmanager
def instrumented(rec: RhythmRecorder) -> Any:
    """Install every wrapper for the duration of one run."""
    core_cls = tc.TransmissionCore
    saved = {
        "_epoch_zone_occupants": core_cls._epoch_zone_occupants,
        "_emit_emesis": core_cls._emit_emesis,
        "_resolve_pathogen_challenge": core_cls._resolve_pathogen_challenge,
        "_cabin_compartments": core_cls._cabin_compartments,
    }
    core_cls._epoch_zone_occupants = _wrap_zone_occupants(core_cls, rec)
    core_cls._emit_emesis = _wrap_emit_emesis(core_cls, rec)
    core_cls._resolve_pathogen_challenge = _wrap_challenge(core_cls, rec)
    core_cls._cabin_compartments = _wrap_cabin_compartments(core_cls, rec)
    deal_day_saved = None
    if RhythmLayer is not None:
        deal_day_saved = RhythmLayer.deal_day
        RhythmLayer.deal_day = _wrap_deal_day(rec)
    try:
        yield
    finally:
        for name, fn in saved.items():
            setattr(core_cls, name, fn)
        if deal_day_saved is not None:
            RhythmLayer.deal_day = deal_day_saved


# ── Epoch observer ────────────────────────────────────────────────────


def _agent_state_row(agent: Any, pathogen_id: str) -> str:
    infections = getattr(agent, "infections", {}) or {}
    infected = ",".join(sorted(str(p) for p in infections))
    symptomatic = bool(
        getattr(agent, "is_symptomatic", False)
    )
    return "|".join((
        str(agent.agent_id),
        str(agent.current_location),
        str(getattr(agent, "current_activity", "")),
        "1" if getattr(agent, "ashore", False) else "0",
        "1" if symptomatic else "0",
        infected,
    ))


def _epoch_observer(rec: RhythmRecorder) -> Any:
    def observe(sim: Any, work: Any) -> None:
        epoch = int(work.epoch)
        hours_per_epoch = float(
            getattr(sim.clock, "hours_per_epoch", 1.0),
        )
        engine = sim.engine
        if getattr(engine, "_rhythm", None) is not None:
            rec.rhythm_attached = True
        zones: dict[str, int] = defaultdict(int)
        ashore = confined = infected = 0
        hasher = hashlib.sha256()
        for agent in sorted(engine.agents, key=lambda a: a.agent_id):
            hasher.update(
                _agent_state_row(agent, rec.pathogen_id).encode(),
            )
            if getattr(agent, "ashore", False):
                ashore += 1
            elif agent.current_location == _ISOLATED_LOCATION:
                confined += 1
            if agent.is_infected_with(rec.pathogen_id):
                infected += 1
            zones[str(agent.current_location)] += 1
        rec.epoch_state_digests.append(hasher.hexdigest())
        rec.epoch_rows.append({
            "epoch": epoch,
            "minute_of_day": int(
                epoch * hours_per_epoch * 60 % MINUTES_PER_DAY,
            ),
            "ashore": ashore,
            "confined": confined,
            "infected": infected,
            "zones": dict(zones),
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


# ── Run driver ────────────────────────────────────────────────────────


def _inject_arm(spec_dict: dict[str, Any], arm: str | None) -> None:
    """Set ``config_overrides.rhythm.enabled`` for the chosen arm."""
    if arm is None:
        return
    if arm not in ("off", "on"):
        raise ValueError(f"unknown arm {arm!r}")
    overrides = spec_dict.setdefault("config_overrides", {})
    rhythm = dict(overrides.get("rhythm") or {})
    rhythm["enabled"] = arm == "on"
    overrides["rhythm"] = rhythm


def _rhythm_payload(
    rec: RhythmRecorder,
    spec_dict: dict[str, Any],
    arm: str | None,
    engine: Any,
) -> dict[str, Any]:
    rhythm_cfg = (spec_dict.get("config_overrides") or {}).get("rhythm") or {}
    attached = getattr(engine, "_rhythm", None) is not None
    requested = rhythm_cfg.get("enabled")
    if arm == "on" and not attached:
        raise RuntimeError(
            "rhythm.enabled=true did not attach a layer "
            "(platform uncatalogued or non-hourly clock?)",
        )
    if arm == "off" and attached:
        raise RuntimeError("rhythm.enabled=false still attached a layer")
    voyage_digest = hashlib.sha256(
        "".join(rec.epoch_state_digests).encode(),
    ).hexdigest()
    return {
        "arm": arm,
        "rhythm_requested": requested,
        "rhythm_attached": attached,
        "commitments_total": rec.commitments_total,
        "dealt_days": rec.dealt_days,
        "ignited": rec.ignited,
        "emit_calls": dict(rec.emit_calls),
        "emits_deferred": dict(rec.emits_deferred),
        "ashore_dosed_epochs": rec.ashore_dosed_epochs,
        "ashore_dosed_rows": rec.ashore_dosed_rows,
        "n_acquired": len(rec.acquired_ids),
        "n_imports": len(rec.import_ids),
        "n_emesis_emitted": len(rec.emesis_rows),
        "emesis_rows": rec.emesis_rows,
        "acquisition_rows": rec.acquisition_rows,
        "epoch_rows": rec.epoch_rows,
        "epoch_state_digests": rec.epoch_state_digests,
        "telemetry_sha256": voyage_digest,
    }


@contextmanager
def _sim_for_spec(spec: dict[str, Any]) -> Any:
    """Materialise one spec dict into a loaded (unrun) ShipSimulation."""
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
        spec_path = resolve_child_path(tmp, "run_spec.json")
        with validated_open(
            spec_path, "w", allowed_roots=(tmp,), encoding="utf-8",
        ) as handle:
            handle.write(json.dumps(spec))
        picard_spec = PicardRunSpec.from_picard_json(
            str(REPO_ROOT), spec_path,
        )
        yield ShipSimulation(picard_spec, display=False)


def run_spec(
    spec_dict: dict[str, Any],
    *,
    arm: str | None,
    pathogen_id: str,
    natural_history_clock: str | None = None,
) -> dict[str, Any]:
    """Run one spec under the wrappers; return the run payload."""
    spec = copy.deepcopy(spec_dict)
    _inject_arm(spec, arm)
    num_agents = int(
        (spec.get("config_overrides") or {})
        .get("ship_graph", {})
        .get("num_agents", 0),
    )
    rec = RhythmRecorder(pathogen_id=pathogen_id)
    started_total = time.perf_counter()
    with instrumented(rec), _sim_for_spec(spec) as sim:
        sim.epoch_observer = _epoch_observer(rec)
        started_run = time.perf_counter()
        result = sim.run()
        wall_clock_run = time.perf_counter() - started_run
    summary: dict[str, Any] = {
        "run_id": str(spec.get("description", "")),
        "seed": int(spec["run"]["random_seed"]),
        "num_epochs": int(spec["run"]["num_epochs"]),
        "num_agents": num_agents,
        "platform": str(spec["catalog"]["platform_id"]),
        "wall_clock_seconds_run": wall_clock_run,
        "wall_clock_seconds_total": time.perf_counter() - started_total,
    }
    _attach_voyage_blocks(
        summary, spec, result, num_agents, natural_history_clock,
    )
    summary["rhythm"] = _rhythm_payload(rec, spec, arm, sim.engine)
    return summary


# ── CLI / campaign-cell plumbing ──────────────────────────────────────


def _identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise argparse.ArgumentTypeError(f"invalid identifier: {value!r}")
    return value


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
        "--arm", choices=("off", "on"), default=None,
        help="rhythm.enabled arm; required with --manifest, optional "
             "with --spec-json (unset leaves the spec's own rhythm block)",
    )
    parser.add_argument(
        "--spec-json", type=Path, default=None,
        help="run an arbitrary spec file verbatim (byte-identity cells)",
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
    if args.manifest is not None:
        if args.tier is None or args.arm is None:
            parser.error("--manifest requires --tier and --arm")
        if args.spec_json is not None:
            parser.error("--manifest and --spec-json are exclusive")
    elif args.tier is not None or args.index is not None:
        parser.error("--tier/--index require --manifest")
    if args.index is not None and args.index < 0:
        parser.error("--index must be non-negative")
    if args.epochs_override is not None and args.epochs_override <= 0:
        parser.error("--epochs-override must be positive")
    return args


def _load_manifest(manifest_path: Path) -> dict[str, Any]:
    safe_manifest = Path(
        resolve_repo_path(str(REPO_ROOT), str(manifest_path)),
    )
    with validated_open(
        safe_manifest, "r", allowed_roots=(str(REPO_ROOT),), encoding="utf-8",
    ) as handle:
        return json.load(handle)


def _write_run_zip(
    out_dir: Path, tier: str, run_id: str, payload: dict[str, Any],
) -> Path:
    """``summary.json`` (campaign layout) + ``rhythm.json.gz`` payload."""
    cell_dir = Path(resolve_child_path(str(out_dir), tier))
    cell_dir.mkdir(parents=True, exist_ok=True)
    zip_path = Path(resolve_child_path(str(cell_dir), f"{run_id}.zip"))
    anchor = {
        "run_id": run_id,
        "parameters": payload["parameters"],
        "num_epochs": payload["num_epochs"],
        "trigger_status": payload.get("trigger_status"),
        "summary": payload["summary"],
        "cost_accounting": payload["cost_accounting"],
        "derived": payload["derived"],
    }
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("summary.json", json.dumps(anchor))
        archive.writestr(
            "rhythm.json.gz",
            gzip.compress(json.dumps(payload["rhythm"]).encode()),
        )
    return zip_path


def _main_manifest(args: argparse.Namespace) -> None:
    manifest = _load_manifest(args.manifest)
    manifest_clock = manifest.get("natural_history_clock")
    runs = list(generate_tier_runs(manifest, args.tier))
    if args.index is not None:
        if args.index >= len(runs):
            raise SystemExit(
                f"--index {args.index} outside tier {args.tier} "
                f"({len(runs)} runs)",
            )
        runs = [runs[args.index]]
    out_dir = Path(
        prepare_output_directory(str(args.out), allowed_roots=(str(REPO_ROOT),)),
    )
    for run_id, spec in runs:
        payload = run_spec(
            spec, arm=args.arm, pathogen_id=args.pathogen_id,
            natural_history_clock=manifest_clock,
        )
        zip_path = _write_run_zip(out_dir, args.tier, run_id, payload)
        print(
            f"{args.arm} {args.tier} {run_id}: "
            f"attached={payload['rhythm']['rhythm_attached']} "
            f"ignited={payload['rhythm']['ignited']} "
            f"acquired={payload['rhythm']['n_acquired']} "
            f"emits={payload['rhythm']['n_emesis_emitted']} "
            f"telemetry={payload['rhythm']['telemetry_sha256'][:12]} "
            f"-> {zip_path}",
            flush=True,
        )


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
    payload = run_spec(
        spec, arm=args.arm, pathogen_id=args.pathogen_id,
        natural_history_clock=spec.get("natural_history_clock"),
    )
    tier = args.tier or "spec"
    run_id = args.out_name or str(spec.get("description", "spec"))
    out_dir = Path(
        prepare_output_directory(str(args.out), allowed_roots=(str(REPO_ROOT),)),
    )
    zip_path = _write_run_zip(out_dir, tier, run_id, payload)
    print(
        f"spec-json {run_id}: "
        f"attached={payload['rhythm']['rhythm_attached']} "
        f"telemetry={payload['rhythm']['telemetry_sha256']} "
        f"acquired={payload['rhythm']['n_acquired']} "
        f"emits={payload['rhythm']['n_emesis_emitted']} "
        f"-> {zip_path}",
        flush=True,
    )


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.manifest is not None:
        _main_manifest(args)
    else:
        _main_spec_json(args)


if __name__ == "__main__":
    main()
