#!/usr/bin/env python3
"""Epoch-lockstep RNG divergence probe, for ledger NORO-TOUCH-SHARE-02.

Purpose
-------
NORO-TOUCH-SHARE-01 measured the ``per_surface + areal`` (A) against the
``per_surface + declared`` (D) fomite arm over seeds 8000-8019 and left one
hypothesis open: the D-arm divergence is real reallocation dynamics, not an
RNG-stream disruption of the NORO-FOMITE-DISAGG-01 archetype (a ``<= 0``
gate taken differently on a floating-point residue). This probe steps both
arms of one seed in lockstep under a single process and, after every epoch,
compares the ordered draw sequence ``(context, method, arg-shape)`` of each
arm's ``TransmissionCore`` generator plus both generators' bit-states. At the
first divergence epoch ``e*`` it dumps a witness record and applies the
ledger's frozen mechanical classification.

Method
------
Both arms are ``ShipSimulation`` instances built from
``per_host_dose_challenge.build_spec`` -- A with
``fomite_representation=per_surface, fomite_touch_share=areal``, D with
``fomite_touch_share=declared`` and the shipped #666 table. Each arm's
``sim.rng`` and ``sim.tx_core.rng`` are replaced, after ``initialize()`` and
before the first ``step()``, by a ``TracingGenerator`` proxy that forwards
every call unchanged to the same underlying ``numpy.random.Generator``
(preserving its post-initialisation state) and appends
``(context, method, arg-shape)`` to the arm's current-epoch trace. The proxy
consumes no randomness and alters no argument or return value.

Engine context comes from read-only wrappers on the ``TransmissionCore``
fomite/contact/challenge seams and on ``PerSurfaceFomiteState``'s
``pickup_requests``/``consume``, dispatched to the arm currently stepping via
a module-level active-arm holder. Every context name carries the *actual*
``pathogen_id`` (``kind|pathogen|zone``; wrappers with no pathogen argument
derive it from the enclosing context), and every witness event records
``pathogen``, ``draw_start``/``draw_end`` (its trace-index range on the arm's
core stream) and ``phase`` (the enclosing context). Events are recorded for
every pathogen, not just norwalk -- the seed-8001 smoke showed the first
divergence was a SARS-CoV-2 PoolDeck zone gate, not a norovirus event.
Wrappers never draw and never alter a value.

Detailed trace comparison stops at ``e*`` (the tracer then drops recording);
both arms keep stepping to ``--epochs`` so the cumulative
``hand_to_mouth_calls`` trajectories (norwalk and all-pathogens) are complete
for the readout.

Deviations from the literal letter of the ledger text, none semantic:

* ``sim.rng`` cannot be replaced before ``initialize()``: ``initialize()``
  itself builds ``TransmissionCore`` with its own
  ``np.random.default_rng(self.seed)`` (``_init_transmission_core``), so the
  probe wraps *both* generators right after ``initialize()`` and before the
  first ``step()``. Initialization draws are therefore untraced but identical
  across arms (same seed, same code path).
* ``TransmissionCore.__init__`` spawns a dedicated sanitary-visit stream via
  ``self.rng.bit_generator.seed_seq.spawn(1)``; that child is a plain
  ``Generator`` and its draws are untraced. The spawn is deterministic and
  consumes no bit-generator state, so the stream pairs exactly across arms.

Outputs
-------
One deterministic JSON document at ``--out`` (rewritten after each seed so a
partial run is not lost): per seed the per-epoch draw counts, cumulative
per-pathogen event counters, both arms' ``hand_to_mouth_calls`` trajectories,
and the divergence record at ``e*`` -- trace window, differing-index entries,
the enclosing engine event per arm, the last aligned / first structurally
differing event pair, a ``zone_gate`` witness when a per-pathogen
``surface_mass <= 0`` zone gate was taken differently, start-of-epoch hand
loads for the named and differing agents, restricted mass diffs, ordering
witnesses (norwalk-only per the ledger, plus the first differing per-class
delivery for any pathogen), and the classification. ``measured_at`` = the
working-tree ``git rev-parse HEAD``.

Nothing here fits or selects a parameter value; no engine code changes.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines import transmission_core as tc  # noqa: E402
from engines.fomite_surfaces import (  # noqa: E402
    PerSurfaceFomiteState,
    load_declared_share_table,
)
from picard_framework.run_spec import PicardRunSpec  # noqa: E402
from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402
from simulation_utils import asset_defaults  # noqa: E402
from simulation_utils.paths import validated_open  # noqa: E402
from simulation_utils.platform_complement import declared_total  # noqa: E402
from tools.noro_diag.per_host_dose_challenge import build_spec  # noqa: E402

PATHOGEN_ID = "norwalk_gi"
RESIDUE_FLOOR_GEC = 1e-12
ORDERING_REL_TOL = 1e-9
TRACE_WINDOW = 10
EVENT_WINDOW = 400
HAND_DIFF_CAP = 200

# Frozen counter vocabulary (ledger NORO-TOUCH-SHARE-02 section 2); stored
# per pathogen as ``f"{key}|{pathogen}"``.
COUNTER_KEYS = (
    "deposit_calls",
    "replenish_calls",
    "pickup_requests",
    "pickup_by_class_calls",
    "pickup_by_class_zones",
    "deliveries",
    "deliver_one_pickups",
    "hand_to_mouth_calls",
    "hand_contact_calls",
    "sanitary_pickups",
    "challenge_calls",
    "consume_calls",
)

_CTX_IDS: dict[str, int] = {"": 0}


def _ctx_id(name: str) -> int:
    """Intern a context string so trace entries stay small and comparable."""
    ctx = _CTX_IDS.get(name)
    if ctx is None:
        ctx = len(_CTX_IDS)
        _CTX_IDS[name] = ctx
    return ctx


def _ctx_name(ctx: int) -> str:
    for name, value in _CTX_IDS.items():
        if value == ctx:
            return name
    return "?"


def _ctx_parts(ctx: int) -> list[str]:
    return _ctx_name(ctx).split("|")


def _ctx_zone(ctx: int) -> str | None:
    """Zone is the last segment of a ``kind|pathogen|zone`` context."""
    parts = _ctx_parts(ctx)
    return parts[2] if len(parts) >= 3 else None


def _ctx_pathogen(ctx: int) -> str:
    """Pathogen is the middle segment; ``kind|pathogen`` for zone-less ctx."""
    parts = _ctx_parts(ctx)
    return parts[1] if len(parts) >= 2 else "unknown"


def _shape_of(value: Any) -> Any:
    """A small hashable summary of one argument; never the value's identity."""
    if isinstance(value, np.ndarray):
        return ("nd", tuple(int(d) for d in value.shape))
    if isinstance(value, (list, tuple)):
        if all(np.isscalar(item) for item in value):
            return repr(tuple(value))
        return ("seq", len(value))
    if np.isscalar(value):
        return repr(value)
    return type(value).__name__


def _argshape(args: tuple, kwargs: dict) -> tuple:
    shaped = tuple(_shape_of(arg) for arg in args)
    if kwargs:
        shaped += (("kw", tuple(sorted(
            (key, _shape_of(val)) for key, val in kwargs.items()
        ))),)
    return shaped


class TracingGenerator:
    """Forwarding proxy that records ``(ctx, method, argshape)`` per call.

    Everything the sim asks of a ``numpy.random.Generator`` passes through
    untouched -- ``bit_generator`` and ``state`` included -- so bit-state
    comparison and ``seed_seq.spawn`` behave exactly as on a bare generator.
    """

    def __init__(self, generator: np.random.Generator) -> None:
        self._gen = generator
        self.trace: list[tuple[int, str, tuple]] = []
        self.draws = 0
        self.ctx = 0
        self.recording = True
        self._cache: dict[str, Any] = {}

    @property
    def bit_generator(self) -> Any:
        return self._gen.bit_generator

    @property
    def state(self) -> dict:
        return self._gen.bit_generator.state

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._gen, name)
        if not callable(attr):
            return attr
        wrapper = self._cache.get(name)
        if wrapper is None:
            def wrapper(*args: Any, __attr: Any = attr,
                        __name: str = name, **kwargs: Any) -> Any:
                if self.recording:
                    self.trace.append(
                        (self.ctx, __name, _argshape(args, kwargs)),
                    )
                self.draws += 1
                return __attr(*args, **kwargs)

            self._cache[name] = wrapper
        return wrapper


@dataclass
class Arm:
    """One instrumented arm: the sim, its two traced streams, witnesses."""

    name: str
    sim: ShipSimulation
    counts: dict[str, int] = field(
        default_factory=lambda: defaultdict(int),
    )
    events: list[dict[str, Any]] = field(default_factory=list)
    record_events: bool = True

    def __post_init__(self) -> None:
        self.root_rng = TracingGenerator(self.sim.rng)
        self.sim.rng = self.root_rng
        self.core_rng = TracingGenerator(self.sim.tx_core.rng)
        self.sim.tx_core.rng = self.core_rng

    def begin_epoch(self) -> None:
        for tracer in (self.root_rng, self.core_rng):
            tracer.trace.clear()
            tracer.draws = 0
            tracer.ctx = 0
        self.events.clear()


# The arm whose sim is currently inside step(); the class-level wrappers
# dispatch context, counters and events to it. ``None`` between epochs.
_ACTIVE: dict[str, Arm | None] = {"arm": None}


def _arm() -> Arm | None:
    return _ACTIVE["arm"]


def _kwarg(args: tuple, kwargs: dict, index: int, name: str) -> Any:
    """One argument whether the engine passed it positionally or by keyword."""
    if name in kwargs:
        return kwargs[name]
    return args[index] if len(args) > index else None


def _mark() -> tuple[Arm | None, int, str]:
    """(arm, draw_start, enclosing ctx name) at wrapper entry."""
    arm = _arm()
    if arm is None:
        return None, 0, ""
    return arm, len(arm.core_rng.trace), _ctx_name(arm.core_rng.ctx)


def _mark_pathogen() -> tuple[Arm | None, int, str, str]:
    """``_mark`` plus the pathogen parsed from the enclosing context."""
    arm, start, phase = _mark()
    parts = phase.split("|")
    pathogen = parts[1] if len(parts) >= 2 else "unknown"
    return arm, start, phase, pathogen


def _set_ctx(name: str) -> int:
    arm = _arm()
    if arm is None:
        return 0
    previous = arm.core_rng.ctx
    arm.core_rng.ctx = _ctx_id(name)
    return previous


def _restore_ctx(previous: int) -> None:
    arm = _arm()
    if arm is not None:
        arm.core_rng.ctx = previous


def _bump(key: str, pathogen: str) -> None:
    arm = _arm()
    if arm is not None:
        arm.counts[f"{key}|{pathogen}"] += 1


def _emit(
    arm: Arm | None, record: dict[str, Any], start: int, phase: str,
) -> None:
    """Stamp draw indices and append the witness event."""
    record["phase"] = phase
    record["draw_start"] = start
    record["draw_end"] = (
        len(arm.core_rng.trace) if arm is not None else start
    )
    if arm is not None and arm.record_events:
        arm.events.append(record)


def _class_masses(self: Any, zone_name: str, pathogen_id: str,
                  classes: Any) -> dict:
    per_surface = getattr(self, "_per_surface", None)
    if per_surface is None:
        return {}
    return {
        cls: float(per_surface.mass.get(
            (zone_name, pathogen_id, cls), 0.0,
        ))
        for cls in sorted(classes)
    }


def _wrap_fomite_chain(core_cls: type) -> dict[str, Any]:
    originals = {
        name: getattr(core_cls, name)
        for name in (
            "_deposit_surface_mass",
            "_replenish_hand",
            "_fomite_pickup_request_for_area",
            "_fomite_pickup_requests_by_class",
            "_fomite_pickup_by_class",
            "_deliver_fomite_requests",
            "_deliver_fomite_requests_by_class",
            "_deliver_one_pickup",
            "_hand_to_mouth_dose",
            "_consume_surface_mass",
            "_consume_surface_mass_by_class",
            "_resolve_pathogen_challenge",
            "_pathway_fomite",
            "_hand_contact_transfers",
            "_per_partner_contact_dose",
            "_sanitary_fomite_exposure",
            "_deliver_sanitary_requests_by_class",
        )
    }

    def deposit(
        self: Any, pathogen_id: str, zone_name: str, mass: float,
    ) -> None:
        arm, start, phase = _mark()
        prev = _set_ctx(f"fomite.deposit|{pathogen_id}|{zone_name}")
        try:
            originals["_deposit_surface_mass"](
                self, pathogen_id, zone_name, mass,
            )
        finally:
            _restore_ctx(prev)
        _bump("deposit_calls", pathogen_id)
        _emit(arm, {
            "kind": "deposit", "pathogen": pathogen_id, "zone": zone_name,
            "mass_gec": float(mass),
        }, start, phase)

    def replenish(
        self: Any, agent: Any, pathogen_id: str, profile: Any,
        zone_name: str | None = None,
    ) -> None:
        prev = _set_ctx(f"fomite.replenish_hand|{pathogen_id}|{zone_name}")
        try:
            originals["_replenish_hand"](
                self, agent, pathogen_id, profile, zone_name,
            )
        finally:
            _restore_ctx(prev)
        _bump("replenish_calls", pathogen_id)

    def pickup_request_for_area(
        self: Any, target: Any, zone_name: str, surface_mass: float,
        surface_area_m2: float, epoch: int,
    ) -> float:
        arm, start, phase, pathogen = _mark_pathogen()
        prev = _set_ctx(f"fomite.pickup_request|{pathogen}|{zone_name}")
        try:
            request = originals["_fomite_pickup_request_for_area"](
                self, target, zone_name, surface_mass, surface_area_m2, epoch,
            )
        finally:
            _restore_ctx(prev)
        _bump("pickup_requests", pathogen)
        _emit(arm, {
            "kind": "pickup_request", "pathogen": pathogen,
            "zone": zone_name,
            "agent_id": int(target.agent_id),
            "surface_mass_gec": float(surface_mass),
            "request_gec": float(request),
        }, start, phase)
        return request

    def pickup_requests_by_class(
        self: Any, target: Any, zone_name: str, epoch: int, pathogen_id: str,
    ) -> Any:
        prev = _set_ctx(
            f"fomite.pickup_requests_by_class|{pathogen_id}|{zone_name}",
        )
        try:
            request = originals["_fomite_pickup_requests_by_class"](
                self, target, zone_name, epoch, pathogen_id,
            )
        finally:
            _restore_ctx(prev)
        _bump("pickup_by_class_calls", pathogen_id)
        return request

    def pickup_by_class(
        self: Any, zone_name: str, susceptible: Any, surface_mass: float,
        epoch: int, *args: Any, **kwargs: Any,
    ) -> None:
        pathogen_id = _kwarg(args, kwargs, 5, "pathogen_id") or "unknown"
        arm, start, phase = _mark()
        prev = _set_ctx(f"fomite.pickup_by_class|{pathogen_id}|{zone_name}")
        try:
            originals["_fomite_pickup_by_class"](
                self, zone_name, susceptible, surface_mass, epoch,
                *args, **kwargs,
            )
        finally:
            _restore_ctx(prev)
        _bump("pickup_by_class_zones", pathogen_id)
        _emit(arm, {
            "kind": "pickup_by_class", "pathogen": pathogen_id,
            "zone": zone_name,
            "surface_mass_gec": float(surface_mass),
            "n_susceptible": len(susceptible),
        }, start, phase)

    def deliver(
        self: Any, requests: Any, zone_name: str, surface_mass: float,
        *args: Any, **kwargs: Any,
    ) -> float:
        pathogen_id = _kwarg(args, kwargs, 6, "pathogen_id") or "unknown"
        arm, start, phase = _mark()
        prev = _set_ctx(f"fomite.deliver|{pathogen_id}|{zone_name}")
        try:
            delivered = originals["_deliver_fomite_requests"](
                self, requests, zone_name, surface_mass, *args, **kwargs,
            )
        finally:
            _restore_ctx(prev)
        _bump("deliveries", pathogen_id)
        _emit(arm, {
            "kind": "deliver", "pathogen": pathogen_id, "zone": zone_name,
            "requested_gec": float(
                sum(mass for _, mass in requests)
            ),
            "surface_mass_gec": float(surface_mass),
            "delivered_gec": float(delivered),
        }, start, phase)
        return delivered

    def deliver_by_class(
        self: Any, requests: Any, zone_name: str, surface_mass: float,
        *args: Any, **kwargs: Any,
    ) -> dict:
        pathogen_id = _kwarg(args, kwargs, 6, "pathogen_id") or "unknown"
        classes = {c for _, req in requests for c in req}
        masses_before = _class_masses(self, zone_name, pathogen_id, classes)
        arm, start, phase = _mark()
        prev = _set_ctx(f"fomite.deliver_by_class|{pathogen_id}|{zone_name}")
        try:
            delivered = originals["_deliver_fomite_requests_by_class"](
                self, requests, zone_name, surface_mass, *args, **kwargs,
            )
        finally:
            _restore_ctx(prev)
        _bump("deliveries", pathogen_id)
        _emit(arm, {
            "kind": "deliver_by_class", "pathogen": pathogen_id,
            "zone": zone_name,
            "requested_by_class_gec": {
                cls: float(
                    sum(req.get(cls, 0.0) for _, req in requests)
                )
                for cls in sorted(classes)
            },
            "class_mass_before_gec": masses_before,
            "surface_mass_gec": float(surface_mass),
            "delivered_by_class_gec": {
                cls: float(m) for cls, m in delivered.items()
            },
        }, start, phase)
        return delivered

    def deliver_one(
        self: Any, target: Any, delivered: float, zone_name: str,
        surface_mass: float, epoch: int, *args: Any, **kwargs: Any,
    ) -> float:
        pathogen_id = _kwarg(args, kwargs, 5, "pathogen_id") or "unknown"
        arm, start, phase = _mark()
        prev = _set_ctx(f"fomite.deliver_one|{pathogen_id}|{zone_name}")
        hand_before = float(
            target.hand_load_by_pathogen.get(pathogen_id, 0.0),
        )
        try:
            dose = originals["_deliver_one_pickup"](
                self, target, delivered, zone_name, surface_mass, epoch,
                *args, **kwargs,
            )
        finally:
            _restore_ctx(prev)
        _bump("deliver_one_pickups", pathogen_id)
        _emit(arm, {
            "kind": "deliver_one", "pathogen": pathogen_id,
            "zone": zone_name,
            "agent_id": int(target.agent_id),
            "delivered_gec": float(delivered),
            "hand_load_before_gec": hand_before,
            "dose_gec": float(dose),
        }, start, phase)
        return dose

    def hand_to_mouth(
        self: Any, target: Any, epoch: int, hand_load: float,
    ) -> float:
        arm, start, phase, pathogen = _mark_pathogen()
        prev = _set_ctx(f"hand_to_mouth|{pathogen}")
        try:
            dose = originals["_hand_to_mouth_dose"](
                self, target, epoch, hand_load,
            )
        finally:
            _restore_ctx(prev)
        _bump("hand_to_mouth_calls", pathogen)
        _emit(arm, {
            "kind": "hand_to_mouth", "pathogen": pathogen,
            "agent_id": int(target.agent_id),
            "hand_load_gec": float(hand_load),
            "dose_gec": float(dose),
        }, start, phase)
        return dose

    def hand_contact_transfers(
        self: Any, target: Any, sampled_shedders: Any, pathogen_id: str,
        cabin_confinement: bool, epoch: int,
    ) -> Any:
        arm, start, phase = _mark()
        prev = _set_ctx(f"hand_contact|{pathogen_id}")
        donors = [
            (int(shedder.agent_id), float(
                shedder.hand_load_by_pathogen.get(pathogen_id, 0.0),
            ))
            for shedder, _ in sampled_shedders
        ]
        try:
            moved = originals["_hand_contact_transfers"](
                self, target, sampled_shedders, pathogen_id,
                cabin_confinement, epoch,
            )
        finally:
            _restore_ctx(prev)
        _bump("hand_contact_calls", pathogen_id)
        moved_by_id = {
            int(shedder.agent_id): float(amount)
            for shedder, amount in moved
        }
        _emit(arm, {
            "kind": "hand_contact", "pathogen": pathogen_id,
            "agent_id": int(target.agent_id),
            "donors": [
                {
                    "agent_id": donor_id,
                    "hand_load_gec": load,
                    "moved_gec": moved_by_id.get(donor_id, 0.0),
                }
                for donor_id, load in donors
            ],
        }, start, phase)
        return moved

    def per_partner_contact_dose(
        self: Any, target: Any, sampled_shedders: Any,
        cabin_confinement: bool, pathogen_id: str, epoch: int,
    ) -> Any:
        arm, start, phase = _mark()
        prev = _set_ctx(f"hand_contact.dose|{pathogen_id}")
        hand_before = float(
            target.hand_load_by_pathogen.get(pathogen_id, 0.0),
        )
        try:
            dose, moved = originals["_per_partner_contact_dose"](
                self, target, sampled_shedders, cabin_confinement,
                pathogen_id, epoch,
            )
        finally:
            _restore_ctx(prev)
        _emit(arm, {
            "kind": "hand_contact_dose", "pathogen": pathogen_id,
            "agent_id": int(target.agent_id),
            "acquired_gec": float(sum(m for _, m in moved)),
            "hand_load_before_gec": hand_before,
            "dose_gec": float(dose),
        }, start, phase)
        return dose, moved

    def consume(
        self: Any, pathogen_id: str, zone_name: str, delivered: float,
        previous_mass: float,
    ) -> None:
        arm, start, phase = _mark()
        prev = _set_ctx(f"fomite.consume|{pathogen_id}|{zone_name}")
        try:
            originals["_consume_surface_mass"](
                self, pathogen_id, zone_name, delivered, previous_mass,
            )
        finally:
            _restore_ctx(prev)
        _bump("consume_calls", pathogen_id)
        _emit(arm, {
            "kind": "consume", "pathogen": pathogen_id, "zone": zone_name,
            "delivered_gec": float(delivered),
            "previous_mass_gec": float(previous_mass),
        }, start, phase)

    def consume_by_class(
        self: Any, pathogen_id: str, zone_name: str,
        delivered_by_class: dict, previous_mass: float,
    ) -> None:
        arm, start, phase = _mark()
        prev = _set_ctx(f"fomite.consume_by_class|{pathogen_id}|{zone_name}")
        try:
            originals["_consume_surface_mass_by_class"](
                self, pathogen_id, zone_name, delivered_by_class,
                previous_mass,
            )
        finally:
            _restore_ctx(prev)
        _bump("consume_calls", pathogen_id)
        _emit(arm, {
            "kind": "consume_by_class", "pathogen": pathogen_id,
            "zone": zone_name,
            "delivered_by_class_gec": {
                cls: float(m)
                for cls, m in delivered_by_class.items()
            },
            "previous_mass_gec": float(previous_mass),
        }, start, phase)

    def sanitary_exposure(
        self: Any, epoch: int, zone_occupants: Any, *args: Any,
        **kwargs: Any,
    ) -> Any:
        pathogen_id = _kwarg(args, kwargs, 3, "pathogen_id") or "unknown"
        prev = _set_ctx(f"sanitary|{pathogen_id}")
        try:
            return originals["_sanitary_fomite_exposure"](
                self, epoch, zone_occupants, *args, **kwargs,
            )
        finally:
            _restore_ctx(prev)

    def sanitary_deliver_by_class(
        self: Any, requests: Any, venue: str, epoch: int, *args: Any,
        **kwargs: Any,
    ) -> Any:
        pathogen_id = _kwarg(args, kwargs, 3, "pathogen_id") or "unknown"
        classes = {c for _, req in requests for c in req}
        masses_before = _class_masses(self, venue, pathogen_id, classes)
        arm, start, phase = _mark()
        prev = _set_ctx(
            f"sanitary.deliver_by_class|{pathogen_id}|{venue}",
        )
        try:
            result = originals["_deliver_sanitary_requests_by_class"](
                self, requests, venue, epoch, *args, **kwargs,
            )
        finally:
            _restore_ctx(prev)
        _bump("sanitary_pickups", pathogen_id)
        _emit(arm, {
            "kind": "sanitary_deliver_by_class", "pathogen": pathogen_id,
            "zone": venue,
            "requested_by_class_gec": {
                cls: float(
                    sum(req.get(cls, 0.0) for _, req in requests)
                )
                for cls in sorted(classes)
            },
            "class_mass_before_gec": masses_before,
            "return": None if result is None else float(result),
        }, start, phase)
        return result

    def challenge(
        self: Any, epoch: int, agent: Any, pathogen_id: str,
        *args: Any, **kwargs: Any,
    ) -> Any:
        prev = _set_ctx(f"challenge|{pathogen_id}")
        try:
            result = originals["_resolve_pathogen_challenge"](
                self, epoch, agent, pathogen_id, *args, **kwargs,
            )
        finally:
            _restore_ctx(prev)
        _bump("challenge_calls", pathogen_id)
        return result

    def pathway_fomite(
        self: Any, epoch: int, zone_occupants: Any, *args: Any,
        **kwargs: Any,
    ) -> Any:
        pathogen_id = _kwarg(args, kwargs, 4, "pathogen_id") or "unknown"
        prev = _set_ctx(f"pathway_fomite|{pathogen_id}")
        try:
            return originals["_pathway_fomite"](
                self, epoch, zone_occupants, *args, **kwargs,
            )
        finally:
            _restore_ctx(prev)

    core_cls._deposit_surface_mass = deposit
    core_cls._replenish_hand = replenish
    core_cls._fomite_pickup_request_for_area = pickup_request_for_area
    core_cls._fomite_pickup_requests_by_class = pickup_requests_by_class
    core_cls._fomite_pickup_by_class = pickup_by_class
    core_cls._deliver_fomite_requests = deliver
    core_cls._deliver_fomite_requests_by_class = deliver_by_class
    core_cls._deliver_one_pickup = deliver_one
    core_cls._hand_to_mouth_dose = hand_to_mouth
    core_cls._consume_surface_mass = consume
    core_cls._consume_surface_mass_by_class = consume_by_class
    core_cls._resolve_pathogen_challenge = challenge
    core_cls._pathway_fomite = pathway_fomite
    core_cls._hand_contact_transfers = hand_contact_transfers
    core_cls._per_partner_contact_dose = per_partner_contact_dose
    core_cls._sanitary_fomite_exposure = sanitary_exposure
    core_cls._deliver_sanitary_requests_by_class = sanitary_deliver_by_class
    return originals


def _wrap_per_surface() -> dict[str, Any]:
    """Read-only wrappers on ``PerSurfaceFomiteState``'s two hot seams."""
    originals = {
        "pickup_requests": PerSurfaceFomiteState.pickup_requests,
        "consume": PerSurfaceFomiteState.consume,
    }

    def pickup_requests(
        self: Any, inv: Any, unit_key: str, pathogen_id: str,
        contacts: float, used_fraction: float, hand_area_m2: float,
        transfer_efficiency: float,
    ) -> dict[str, float]:
        arm, start, phase = _mark()
        prev = _set_ctx(f"pickup_requests|{pathogen_id}|{unit_key}")
        masses_before = {
            cls: float(self.mass.get((unit_key, pathogen_id, cls), 0.0))
            for cls in sorted(inv.counts)
        }
        try:
            request = originals["pickup_requests"](
                self, inv, unit_key, pathogen_id, contacts,
                used_fraction, hand_area_m2, transfer_efficiency,
            )
        finally:
            _restore_ctx(prev)
        _emit(arm, {
            "kind": "class_pickup_requests", "pathogen": pathogen_id,
            "zone": unit_key,
            "request_by_class_gec": {
                cls: float(v) for cls, v in request.items()
            },
            "class_mass_before_gec": masses_before,
            "contacts": float(contacts),
            "used_fraction": float(used_fraction),
            "hand_area_m2": float(hand_area_m2),
            "transfer_efficiency": float(transfer_efficiency),
        }, start, phase)
        return request

    def consume(
        self: Any, unit_key: str, pathogen_id: str,
        delivered_by_class: dict,
    ) -> None:
        arm, start, phase = _mark()
        prev = _set_ctx(f"ps.consume|{pathogen_id}|{unit_key}")
        masses_before = {
            cls: float(self.mass.get((unit_key, pathogen_id, cls), 0.0))
            for cls in sorted(delivered_by_class)
        }
        try:
            originals["consume"](
                self, unit_key, pathogen_id, delivered_by_class,
            )
        finally:
            _restore_ctx(prev)
        _emit(arm, {
            "kind": "ps_consume", "pathogen": pathogen_id,
            "zone": unit_key,
            "class_mass_before_gec": masses_before,
            "delivered_by_class_gec": {
                cls: float(m) for cls, m in delivered_by_class.items()
            },
        }, start, phase)

    PerSurfaceFomiteState.pickup_requests = pickup_requests
    PerSurfaceFomiteState.consume = consume
    return originals


@contextmanager
def lockstep_instrumented(active: dict[str, Arm | None]) -> Any:
    """Install the read-only context wrappers for the probe's duration."""
    core_cls = tc.TransmissionCore
    originals = _wrap_fomite_chain(core_cls)
    ps_originals = _wrap_per_surface()
    try:
        yield active
    finally:
        for name, method in originals.items():
            setattr(core_cls, name, method)
        for name, method in ps_originals.items():
            setattr(PerSurfaceFomiteState, name, method)
        active["arm"] = None


def _state_equal(a: dict, b: dict) -> bool:
    """Bit-generator ``state`` equality, numpy-array safe."""
    if set(a) != set(b):
        return False
    for key, va in a.items():
        vb = b[key]
        if isinstance(va, np.ndarray) or isinstance(vb, np.ndarray):
            if not np.array_equal(np.asarray(va), np.asarray(vb)):
                return False
        elif isinstance(va, dict):
            if not _state_equal(va, vb):
                return False
        elif va != vb:
            return False
    return True


def _snapshot_masses(core: Any) -> dict[str, dict]:
    """Start-of-epoch surface mass per pathogen+zone and per class."""
    zone = {
        f"{pid}|{z}": float(m)
        for pid, pools in core.surface_pools_by_pathogen.items()
        for z, m in pools.items()
    }
    by_class: dict[str, float] = {}
    per_surface = getattr(core, "_per_surface", None)
    if per_surface is not None:
        for (z, pid, cls), mass in per_surface.mass.items():
            by_class[f"{pid}|{z}|{cls}"] = float(mass)
    return {"zone_gec": zone, "zone_class_gec": by_class}


def _snapshot_hand_loads(sim: ShipSimulation) -> dict[int, float]:
    """Per-agent ``hand_load_by_pathogen`` at the epoch boundary, norwalk."""
    return {
        int(agent.agent_id): float(
            agent.hand_load_by_pathogen.get(PATHOGEN_ID, 0.0),
        )
        for agent in sim.engine.agents
    }


def _mass_diffs(
    snap_a: dict, snap_d: dict, zones: set[str] | None = None,
) -> dict[str, dict]:
    """Both arms' masses restricted to differing keys (optionally zoned)."""
    diffs: dict[str, dict] = {}
    for section in ("zone_gec", "zone_class_gec"):
        keys = set(snap_a[section]) | set(snap_d[section])
        rows = {}
        for key in sorted(keys):
            parts = key.split("|")
            zone_key = "|".join(parts[:2])
            if zones is not None and key not in zones and (
                zone_key not in zones
            ):
                continue
            va = snap_a[section].get(key, 0.0)
            vd = snap_d[section].get(key, 0.0)
            if va == vd:
                continue
            rows[key] = {
                "a": va,
                "d": vd,
                "abs_diff": abs(va - vd),
                "rel_diff": (
                    abs(va - vd) / max(abs(va), abs(vd), RESIDUE_FLOOR_GEC)
                ),
            }
        diffs[section] = rows
    return diffs


def _trace_diff(trace_a: list, trace_b: list) -> int | None:
    """First differing index across the two traces, or None if identical."""
    limit = min(len(trace_a), len(trace_b))
    for index in range(limit):
        if trace_a[index] != trace_b[index]:
            return index
    if len(trace_a) != len(trace_b):
        return limit
    return None


def _trace_json(entry: tuple[int, str, tuple]) -> dict[str, Any]:
    ctx, method, argshape = entry
    return {"ctx": _ctx_name(ctx), "method": method, "argshape": argshape}


def _trace_window(trace: list, index: int) -> list[dict]:
    low = max(0, index - TRACE_WINDOW)
    high = min(len(trace), index + TRACE_WINDOW + 1)
    return [_trace_json(trace[i]) for i in range(low, high)]


def _enclosing_event(events: list[dict], d_star: int) -> dict[str, Any]:
    """The innermost event containing ``d_star``, else its neighbours."""
    containing = [
        event for event in events
        if event.get("draw_start", -1) <= d_star < event.get("draw_end", -1)
    ]
    if containing:
        innermost = min(
            containing,
            key=lambda e: e["draw_end"] - e["draw_start"],
        )
        return {"containing": innermost}
    before = [
        event for event in events if event.get("draw_end", -1) <= d_star
    ]
    after = [
        event for event in events if event.get("draw_start", -1) > d_star
    ]
    return {
        "before": before[-1] if before else None,
        "after": after[0] if after else None,
    }


def _event_key(event: dict) -> tuple:
    return (
        event.get("kind"), event.get("zone"),
        event.get("agent_id"), event.get("pathogen"),
    )


def _structural_diff(
    events_a: list[dict], events_d: list[dict],
) -> tuple[int, dict[str, Any] | None]:
    """Last pairwise-aligned event index, and the first mismatching pair."""
    last_aligned = -1
    for index, (ea, ed) in enumerate(zip(events_a, events_d)):
        if _event_key(ea) != _event_key(ed):
            return last_aligned, {"index": index, "a": ea, "d": ed}
        last_aligned = index
    if len(events_a) != len(events_d):
        index = min(len(events_a), len(events_d))
        return last_aligned, {
            "index": index,
            "a": events_a[index] if index < len(events_a) else None,
            "d": events_d[index] if index < len(events_d) else None,
        }
    return last_aligned, None


def _event_agent_ids(event: dict | None) -> set[int]:
    ids = set()
    if not event:
        return ids
    for key in ("agent_id", "target"):
        if isinstance(event.get(key), int):
            ids.add(event[key])
    for donor in event.get("donors", ()):
        ids.add(donor["agent_id"])
    return ids


def _named_agents(*records: Any) -> set[int]:
    ids: set[int] = set()
    for record in records:
        if not isinstance(record, dict):
            continue
        for key in ("containing", "before", "after", "a", "d"):
            ids |= _event_agent_ids(record.get(key))
        ids |= _event_agent_ids(record)
    return ids


def _events_window(
    events: list[dict], d_star: int | None,
) -> dict[str, Any]:
    """Events within +-EVENT_WINDOW draws of d* plus per-kind counts."""
    counts = dict(Counter(e.get("kind") for e in events))
    if d_star is None:
        return {"events": events[:HAND_DIFF_CAP], "kind_counts": counts}
    lo, hi = d_star - EVENT_WINDOW, d_star + EVENT_WINDOW
    window = [
        e for e in events
        if e.get("draw_end", -1) >= lo and e.get("draw_start", -1) <= hi
    ]
    return {"events": window, "kind_counts": counts}


_ZONE_GATE_KINDS = (
    "pickup_by_class",
    "class_pickup_requests",
    "deliver_by_class",
    "sanitary_deliver_by_class",
)


def _zone_gate(
    enc_a: dict, enc_d: dict, snap_a: dict, snap_d: dict,
    events_a: list[dict], events_d: list[dict],
) -> dict[str, Any] | None:
    """Witness a ``surface_mass <= 0`` zone gate taken differently.

    Fires when an enclosing/neighbouring event at d* is a per-class pickup
    or delivery for (pathogen P, zone Z) whose start-of-epoch pooled mass
    differs between the arms.
    """
    candidates = []
    for enc in (enc_a, enc_d):
        for key in ("containing", "after", "before"):
            event = enc.get(key)
            if isinstance(event, dict) and event.get("kind") in (
                _ZONE_GATE_KINDS
            ):
                candidates.append(event)
    def gate_rows(event: dict) -> tuple[str, str, float, float] | None:
        pathogen = event.get("pathogen", "unknown")
        zone = event.get("zone")
        if zone is None:
            return None
        pz = f"{pathogen}|{zone}"
        return (
            pathogen, zone,
            snap_a["zone_gec"].get(pz, 0.0),
            snap_d["zone_gec"].get(pz, 0.0),
        )

    # The gate that diverged is the one where exactly one arm's pool is
    # an exact 0.0 (capped/consumed) versus residue — intentional exact test;
    # anything else is a downstream mass difference, not a gate.
    rows = [row for row in (gate_rows(e) for e in candidates) if row]
    zero_branch = [
        row for row in rows
        if (not row[2]) != (not row[3]) and max(row[2], row[3]) > 0.0
    ]
    pool_diff = [row for row in rows if row[2] != row[3]]
    for pathogen, zone, pool_a, pool_d in zero_branch + pool_diff:
        pz = f"{pathogen}|{zone}"
        prefix = f"{pz}|"
        deposits = {
            side: [
                {k: v for k, v in e.items() if k != "phase"}
                for e in events
                if e.get("kind") == "deposit"
                and e.get("pathogen") == pathogen
                and e.get("zone") == zone
            ]
            for side, events in (("a", events_a), ("d", events_d))
        }
        return {
            "gate": "_pathway_fomite surface_mass <= 0",
            "pathogen": pathogen,
            "is_norwalk_gi": pathogen == PATHOGEN_ID,
            "zone": zone,
            "pool_gec": {"a": pool_a, "d": pool_d},
            "by_class_gec": {
                "a": {
                    k[len(prefix):]: v
                    for k, v in snap_a["zone_class_gec"].items()
                    if k.startswith(prefix)
                },
                "d": {
                    k[len(prefix):]: v
                    for k, v in snap_d["zone_class_gec"].items()
                    if k.startswith(prefix)
                },
            },
            "deposits_this_epoch": deposits,
        }
    return None


def _gate_quantities_of(event: dict | None) -> dict[str, float]:
    """The mass/load that admits the draw for one event kind."""
    if not event:
        return {}
    kind = event.get("kind")
    pathogen = event.get("pathogen", "unknown")
    if kind == "hand_to_mouth":
        return {f"hand_load|{pathogen}": event["hand_load_gec"]}
    if kind == "hand_contact_dose":
        return {
            f"acquired|{pathogen}": event["acquired_gec"],
            f"hand_load|{pathogen}": event["hand_load_before_gec"],
        }
    if kind == "hand_contact":
        return {
            f"donor_hand|{pathogen}|{donor['agent_id']}": (
                donor["hand_load_gec"]
            )
            for donor in event.get("donors", ())
        }
    if kind == "deliver_one":
        return {
            f"delivered|{pathogen}": event["delivered_gec"],
            f"hand_load|{pathogen}": event["hand_load_before_gec"],
        }
    if kind in ("deliver", "deliver_by_class", "sanitary_deliver_by_class"):
        gates = {
            f"class_mass|{pathogen}|{event['zone']}|{cls}": mass
            for cls, mass in event.get(
                "class_mass_before_gec", {},
            ).items()
        }
        if "surface_mass_gec" in event:
            gates[f"surface_mass|{pathogen}|{event['zone']}"] = event[
                "surface_mass_gec"
            ]
        return gates
    if kind == "pickup_request":
        return {
            f"surface_mass|{pathogen}|{event['zone']}": (
                event["surface_mass_gec"]
            ),
        }
    if kind in ("class_pickup_requests", "ps_consume"):
        return {
            f"class_mass|{pathogen}|{event['zone']}|{cls}": mass
            for cls, mass in event.get(
                "class_mass_before_gec", {},
            ).items()
        }
    if kind in ("pickup_by_class", "consume", "consume_by_class"):
        key = (
            "surface_mass_gec" if kind == "pickup_by_class"
            else "previous_mass_gec"
        )
        return {f"surface_mass|{pathogen}|{event['zone']}": event[key]}
    if kind == "deposit":
        return {f"deposit|{pathogen}|{event['zone']}": event["mass_gec"]}
    return {}


def _merge_zone_gate_quantities(
    quantities: dict[str, dict[str, float]], zone_gate: dict,
) -> None:
    quantities["zone_pool_gec"] = {
        "a": float(zone_gate["pool_gec"]["a"]),
        "d": float(zone_gate["pool_gec"]["d"]),
    }
    classes = set(zone_gate["by_class_gec"]["a"]) | set(
        zone_gate["by_class_gec"]["d"],
    )
    for cls in sorted(classes):
        quantities[f"zone_class|{cls}"] = {
            "a": float(zone_gate["by_class_gec"]["a"].get(cls, 0.0)),
            "d": float(zone_gate["by_class_gec"]["d"].get(cls, 0.0)),
        }


def _merge_event_quantities(
    quantities: dict[str, dict[str, float]],
    enc_a: dict, enc_d: dict, first_diff: dict | None,
) -> None:
    event_a = (enc_a or {}).get("containing") or (
        (enc_a or {}).get("before")
    )
    event_d = (enc_d or {}).get("containing") or (
        (enc_d or {}).get("before")
    )
    qa, qd = _gate_quantities_of(event_a), _gate_quantities_of(event_d)
    for name in sorted(set(qa) | set(qd)):
        quantities[name] = {
            "a": float(qa.get(name, 0.0)),
            "d": float(qd.get(name, 0.0)),
        }
    if first_diff:
        for side, event in (("a", first_diff.get("a")),
                            ("d", first_diff.get("d"))):
            for name, value in _gate_quantities_of(event).items():
                quantities.setdefault(name, {"a": 0.0, "d": 0.0})
                quantities[name][side] = float(value)


def _merge_zone_snapshot_quantities(
    quantities: dict[str, dict[str, float]],
    snap_a: dict, snap_d: dict, zone_key: str | None,
) -> None:
    if zone_key is None:
        return
    quantities[f"surface_mass|{zone_key}"] = {
        "a": float(snap_a["zone_gec"].get(zone_key, 0.0)),
        "d": float(snap_d["zone_gec"].get(zone_key, 0.0)),
    }
    prefix = f"{zone_key}|"
    for key in sorted(set(snap_a["zone_class_gec"]) | set(
        snap_d["zone_class_gec"],
    )):
        if key.startswith(prefix):
            quantities[f"class_mass|{key}"] = {
                "a": float(snap_a["zone_class_gec"].get(key, 0.0)),
                "d": float(snap_d["zone_class_gec"].get(key, 0.0)),
            }


def _gate_quantities(
    enc_a: dict, enc_d: dict, first_diff: dict | None,
    snap_a: dict, snap_d: dict, zone_key: str | None,
    zone_gate: dict | None,
) -> dict[str, dict[str, float]]:
    """Paired gate quantities for the classifier, per the frozen rule."""
    quantities: dict[str, dict[str, float]] = {}
    if zone_gate is not None:
        _merge_zone_gate_quantities(quantities, zone_gate)
    _merge_event_quantities(quantities, enc_a, enc_d, first_diff)
    _merge_zone_snapshot_quantities(quantities, snap_a, snap_d, zone_key)
    return quantities


def _pair_verdict(va: float, vd: float) -> tuple[bool, bool, bool]:
    """One quantity pair -> (archetype_hit, differs, expected_ok)."""
    va, vd = float(va), float(vd)
    differs = va < vd or va > vd
    residue = 0.0 < abs(va) < RESIDUE_FLOOR_GEC or (
        0.0 < abs(vd) < RESIDUE_FLOOR_GEC
    )
    archetype = residue and (differs or min(va, vd) <= 0.0)
    both_real = (
        abs(va) >= RESIDUE_FLOOR_GEC and abs(vd) >= RESIDUE_FLOOR_GEC
    )
    # exact 0.0 (capped/consumed) vs residue — intentional exact test
    exact_zero = (not va) != (not vd)
    nonzero = max(abs(va), abs(vd)) >= RESIDUE_FLOOR_GEC
    return archetype, differs, (not differs) or (
        both_real or (exact_zero and nonzero)
    )


def classify_divergence(quantities: dict[str, dict[str, float]]) -> dict:
    """The frozen mechanical rule of ledger NORO-TOUCH-SHARE-02 section 1.

    ``quantities`` maps a gate-quantity name (the mass or hand load that
    admits the draw at d*) to ``{"a": value_A, "d": value_D}``.
    ``archetype`` fires when any quantity is a residue ``0 < |v| < 1e-12``
    in one arm while the other arm's is ``<= 0`` or the pair differs (the
    gate took the other branch); ``expected`` needs every differing pair to
    be either both >= 1e-12 or an exact 0.0 against >= 1e-12; anything else,
    and empty evidence, is ``other``.
    """
    if not quantities:
        return {
            "class": "other",
            "reason": "no gate quantities supplied",
            "quantities": {},
        }
    evidence = {
        name: {"a": float(pair["a"]), "d": float(pair["d"])}
        for name, pair in quantities.items()
    }
    archetype_hits = []
    differing: list[str] = []
    expected_ok = True
    for name, pair in evidence.items():
        archetype, differs, ok = _pair_verdict(pair["a"], pair["d"])
        if archetype:
            archetype_hits.append(name)
        if differs:
            differing.append(name)
            expected_ok = expected_ok and ok
    if archetype_hits:
        return {
            "class": "archetype",
            "gate_quantities": archetype_hits,
            "quantities": evidence,
        }
    if differing and expected_ok:
        return {
            "class": "expected",
            "differing_quantities": differing,
            "quantities": evidence,
        }
    return {
        "class": "other",
        "differing_quantities": differing,
        "quantities": evidence,
    }


def _ordering_witness(
    events_a: list[dict], events_d: list[dict], epoch: int,
    pathogen: str | None = None,
) -> dict[str, Any] | None:
    """First per-class delivery differing beyond the frozen tolerance."""
    by_a = [
        e for e in events_a
        if e["kind"] == "deliver_by_class"
        and (pathogen is None or e.get("pathogen") == pathogen)
    ]
    by_d = [
        e for e in events_d
        if e["kind"] == "deliver_by_class"
        and (pathogen is None or e.get("pathogen") == pathogen)
    ]
    for index, (ea, ed) in enumerate(zip(by_a, by_d)):
        classes = set(ea["delivered_by_class_gec"]) | set(
            ed["delivered_by_class_gec"],
        )
        for cls in sorted(classes):
            va = ea["delivered_by_class_gec"].get(cls, 0.0)
            vd = ed["delivered_by_class_gec"].get(cls, 0.0)
            if va < RESIDUE_FLOOR_GEC or vd < RESIDUE_FLOOR_GEC:
                continue
            if abs(va - vd) / max(va, vd) > ORDERING_REL_TOL:
                return {
                    "epoch": epoch,
                    "event_index": index,
                    "pathogen": ea.get("pathogen", "unknown"),
                    "zone": ea["zone"],
                    "item_class": cls,
                    "a_gec": va,
                    "d_gec": vd,
                }
    return None


def _build_sim(spec_dict: dict[str, Any]) -> ShipSimulation:
    """Build and initialize one arm's sim from a spec dict."""
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
        spec_path = Path(tmp) / "run_spec.json"
        with validated_open(
            str(spec_path), "w", allowed_roots=(tmp,), encoding="utf-8",
        ) as handle:
            handle.write(json.dumps(spec_dict))
        picard_spec = PicardRunSpec.from_picard_json(
            str(REPO_ROOT), str(spec_path),
        )
    sim = ShipSimulation(picard_spec, display=False)
    sim.initialize()
    return sim


def _arm_specs(
    seed: int, platform: str, bundle: str, epochs: int, num_agents: int,
    share_table: dict[str, Any],
) -> tuple[dict, dict]:
    """Arm A uses per_surface/areal/shipped; arm D declared shares (#666)."""
    common = {
        "seed": seed, "platform": platform, "bundle": bundle,
        "epochs": epochs, "num_agents": num_agents,
        "pathogen_id": PATHOGEN_ID, "alpha": None, "beta": 1.0,
        "fomite_representation": "per_surface",
    }
    spec_a = build_spec(**common, fomite_touch_share="areal")
    spec_d = build_spec(
        **common, fomite_touch_share="declared",
        fomite_touch_share_table=share_table,
    )
    return spec_a, spec_d


def _counts_snapshot(arm: Arm) -> dict[str, dict]:
    """Per-pathogen counter table plus an all-pathogens ``all`` block."""
    pathogens = sorted(
        {key.split("|", 1)[1] for key in arm.counts if "|" in key}
    )
    out = {
        pid: {
            key: int(arm.counts.get(f"{key}|{pid}", 0))
            for key in COUNTER_KEYS
        }
        for pid in pathogens
    }
    out["all"] = {
        key: int(sum(
            arm.counts.get(f"{key}|{pid}", 0) for pid in pathogens
        ))
        for key in COUNTER_KEYS
    }
    return out


def _hand_load_rows(
    hands_a: dict[int, float], hands_d: dict[int, float],
    named: set[int],
) -> dict[str, Any]:
    """Start-of-epoch loads for named agents and for all differing agents."""
    differing = [
        aid for aid in set(hands_a) | set(hands_d)
        if hands_a.get(aid, 0.0) != hands_d.get(aid, 0.0)
    ]
    differing.sort(
        key=lambda aid: -abs(
            hands_a.get(aid, 0.0) - hands_d.get(aid, 0.0),
        ),
    )
    emit = sorted(named | set(differing[:HAND_DIFF_CAP]))
    return {
        "differing_agent_count": len(differing),
        "agents": {
            str(aid): {
                "a": hands_a.get(aid, 0.0),
                "d": hands_d.get(aid, 0.0),
            }
            for aid in emit
        },
    }


def _record_zone_keys(
    enc_a: dict, enc_d: dict, first_diff: dict | None,
    trace_a: list, d_star: int | None,
) -> tuple[set[str], str | None]:
    """The (pathogen|zone) keys named by the enclosing/diff events + ctx."""
    zone_keys = {
        f"{ev.get('pathogen', 'unknown')}|{ev.get('zone')}"
        for ev in (
            enc_a.get("containing"), enc_a.get("before"),
            enc_d.get("containing"), enc_d.get("before"),
            (first_diff or {}).get("a"), (first_diff or {}).get("d"),
        )
        if isinstance(ev, dict) and ev.get("zone")
    }
    ctx_entry = trace_a[d_star] if (
        d_star is not None and d_star < len(trace_a)
    ) else None
    if ctx_entry is not None:
        czone, cpath = _ctx_zone(ctx_entry[0]), _ctx_pathogen(ctx_entry[0])
        if czone is not None:
            zone_keys.add(f"{cpath}|{czone}")
    return zone_keys, (min(zone_keys) if zone_keys else None)


def _divergence_record(
    epoch: int, gen: str, d_star: int | None,
    arm_a: Arm, arm_d: Arm, snap_a: dict, snap_d: dict,
    hands_a: dict, hands_d: dict,
    counts_start: dict[str, dict], ordering: dict | None,
    ordering_any: dict | None,
) -> dict[str, Any]:
    trace_a = getattr(arm_a, f"{gen}_rng").trace
    trace_d = getattr(arm_d, f"{gen}_rng").trace
    enc_a = enc_d = {"containing": None, "before": None, "after": None}
    if d_star is not None:
        enc_a = _enclosing_event(arm_a.events, d_star)
        enc_d = _enclosing_event(arm_d.events, d_star)
    last_aligned, first_diff = _structural_diff(
        arm_a.events, arm_d.events,
    )
    zone_gate = _zone_gate(
        enc_a, enc_d, snap_a, snap_d, arm_a.events, arm_d.events,
    )
    zone_keys, zone_key = _record_zone_keys(
        enc_a, enc_d, first_diff, trace_a, d_star,
    )
    quantities = _gate_quantities(
        enc_a, enc_d, first_diff, snap_a, snap_d, zone_key, zone_gate,
    )
    classification = classify_divergence(quantities)
    if zone_gate is not None:
        classification["zone_gate_fired"] = True
        classification["pathogen"] = zone_gate["pathogen"]
        classification["is_norwalk_gi"] = zone_gate["is_norwalk_gi"]
    named = _named_agents(enc_a, enc_d, first_diff or {})
    return {
        "epoch": epoch,
        "generator": gen,
        "d_star_index": d_star,
        "entry_a": (
            _trace_json(trace_a[d_star])
            if d_star is not None and d_star < len(trace_a) else None
        ),
        "entry_d": (
            _trace_json(trace_d[d_star])
            if d_star is not None and d_star < len(trace_d) else None
        ),
        "window_a": _trace_window(trace_a, d_star or 0),
        "window_d": _trace_window(trace_d, d_star or 0),
        "enclosing_event_a": enc_a,
        "enclosing_event_d": enc_d,
        "last_aligned_event_index": last_aligned,
        "first_structural_diff": first_diff,
        "zone_gate": zone_gate,
        "hand_loads_at_epoch_start": _hand_load_rows(
            hands_a, hands_d, named,
        ),
        "mass_diffs": _mass_diffs(snap_a, snap_d, zone_keys),
        "events_a": _events_window(arm_a.events, d_star),
        "events_d": _events_window(arm_d.events, d_star),
        "counts_at_epoch_start": counts_start,
        "counts_identical_before_divergence": (
            counts_start["a"] == counts_start["d"]
        ),
        "ordering_witness": ordering,
        "ordering_witness_any_pathogen": ordering_any,
        "classification": classification,
    }


def _compare_epoch(
    epoch: int, arm_a: Arm, arm_d: Arm, snap_a: dict, snap_d: dict,
    hands_a: dict, hands_d: dict,
    counts_start: dict[str, dict], ordering: dict | None,
    ordering_any: dict | None,
) -> tuple[dict | None, bool]:
    """Compare both traced streams; return (record, aligned) for the epoch."""
    states_equal = all(
        _state_equal(
            getattr(arm_a, f"{gen}_rng").bit_generator.state,
            getattr(arm_d, f"{gen}_rng").bit_generator.state,
        )
        for gen in ("core", "root")
    )
    for gen in ("core", "root"):
        d_star = _trace_diff(
            getattr(arm_a, f"{gen}_rng").trace,
            getattr(arm_d, f"{gen}_rng").trace,
        )
        if d_star is not None:
            return (
                _divergence_record(
                    epoch, gen, d_star, arm_a, arm_d,
                    snap_a, snap_d, hands_a, hands_d,
                    counts_start, ordering, ordering_any,
                ),
                False,
            )
    if not states_equal:
        return (
            _divergence_record(
                epoch, "core", None, arm_a, arm_d,
                snap_a, snap_d, hands_a, hands_d,
                counts_start, ordering, ordering_any,
            ),
            False,
        )
    return None, True


def _epoch_row(epoch: int, arm_a: Arm, arm_d: Arm) -> dict[str, Any]:
    def h2m(arm: Arm) -> tuple[int, int]:
        return (
            arm.counts.get(f"hand_to_mouth_calls|{PATHOGEN_ID}", 0),
            sum(
                v for k, v in arm.counts.items()
                if k.startswith("hand_to_mouth_calls|")
            ),
        )

    a_norwalk, a_all = h2m(arm_a)
    d_norwalk, d_all = h2m(arm_d)
    return {
        "epoch": epoch,
        "draws": {"a": arm_a.core_rng.draws, "d": arm_d.core_rng.draws},
        "hand_to_mouth_calls": {
            "a_norwalk": a_norwalk, "d_norwalk": d_norwalk,
            "a_all": a_all, "d_all": d_all,
        },
        "counts_a": _counts_snapshot(arm_a),
        "counts_d": _counts_snapshot(arm_d),
    }


def _freeze_after_divergence(arm_a: Arm, arm_d: Arm) -> None:
    for arm in (arm_a, arm_d):
        arm.root_rng.recording = False
        arm.core_rng.recording = False
        arm.record_events = False


def _step_epoch(
    epoch: int, arm_a: Arm, arm_d: Arm, state: dict[str, Any],
) -> dict | None:
    """Step both arms once; return the divergence record if one appears."""
    aligned = state["divergence"] is None
    snap_a = snap_d = counts_start = None
    if aligned:
        state["prev_hands"] = {"a": state["hands_a"], "d": state["hands_d"]}
        state["hands_a"] = _snapshot_hand_loads(arm_a.sim)
        state["hands_d"] = _snapshot_hand_loads(arm_d.sim)
        snap_a = _snapshot_masses(arm_a.sim.tx_core)
        snap_d = _snapshot_masses(arm_d.sim.tx_core)
        counts_start = {
            "a": _counts_snapshot(arm_a),
            "d": _counts_snapshot(arm_d),
        }
    for arm in (arm_a, arm_d):
        if aligned:
            arm.begin_epoch()
        _ACTIVE["arm"] = arm
        arm.sim.step()
    _ACTIVE["arm"] = None
    if not aligned:
        return None
    if state["ordering"] is None:
        state["ordering"] = _ordering_witness(
            arm_a.events, arm_d.events, epoch, PATHOGEN_ID,
        )
    if state["ordering_any"] is None:
        state["ordering_any"] = _ordering_witness(
            arm_a.events, arm_d.events, epoch,
        )
    divergence, still = _compare_epoch(
        epoch, arm_a, arm_d, snap_a, snap_d,
        state["hands_a"], state["hands_d"], counts_start,
        state["ordering"], state["ordering_any"],
    )
    if still:
        return None
    divergence["hand_loads_prev_epoch"] = (
        _hand_load_rows(
            state["prev_hands"]["a"], state["prev_hands"]["d"], set(),
        )
        if state["prev_hands"].get("a") else None
    )
    _freeze_after_divergence(arm_a, arm_d)
    state["divergence"] = divergence
    return divergence


def run_seed(
    seed: int, platform: str, bundle: str, epochs: int,
    num_agents: int, share_table_path: str,
) -> dict[str, Any]:
    """Step arms A and D in lockstep for one seed and emit the record."""
    share_table = load_declared_share_table(share_table_path)
    spec_a, spec_d = _arm_specs(
        seed, platform, bundle, epochs, num_agents, share_table,
    )
    arm_a = Arm("areal", _build_sim(spec_a))
    arm_d = Arm("declared", _build_sim(spec_d))
    state: dict[str, Any] = {
        "divergence": None, "ordering": None, "ordering_any": None,
        "hands_a": {}, "hands_d": {}, "prev_hands": {},
    }
    epoch_rows: list[dict] = []
    with lockstep_instrumented(_ACTIVE):
        for epoch in range(epochs):
            _step_epoch(epoch, arm_a, arm_d, state)
            epoch_rows.append(_epoch_row(epoch, arm_a, arm_d))
    return {
        "seed": seed,
        "platform": platform,
        "num_agents": num_agents,
        "epochs": epochs,
        "divergence": state["divergence"],
        "ordering_witness": state["ordering"],
        "ordering_witness_any_pathogen": state["ordering_any"],
        "epoch_rows": epoch_rows,
        "final_counts": {
            "a": _counts_snapshot(arm_a),
            "d": _counts_snapshot(arm_d),
        },
    }


def _safe_path(path: str) -> str:
    """Canonicalise a CLI target under the repo root or the user home."""
    resolved = os.path.realpath(path)
    roots = (
        os.path.realpath(str(REPO_ROOT)),
        os.path.realpath(os.path.expanduser("~")),
    )
    if not any(
        resolved == root or resolved.startswith(root + os.sep)
        for root in roots
    ):
        raise ValueError(f"path {path!r} is outside the allowed directories")
    return resolved


def _identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise argparse.ArgumentTypeError(f"invalid identifier: {value!r}")
    return value


def _git_sha() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--platform", type=_identifier, default="classic_cruise_1900")
    parser.add_argument(
        "--bundle", type=_identifier,
        default=asset_defaults.DEFAULT_PATHOGEN_BUNDLE_ID)
    parser.add_argument("--epochs", type=int, default=288)
    parser.add_argument(
        "--seeds", type=int, nargs="+", default=[8001, 8000],
        help="the two ledger seeds; 8001 aligned, 8000 diverged in -01",
    )
    parser.add_argument(
        "--num-agents", type=int, default=None,
        help="defaults to the platform's declared complement",
    )
    parser.add_argument(
        "--share-table", type=Path,
        default=REPO_ROOT / "data/config/fomite_touch_share_declared.json",
        help="the declared touch-share table JSON (the #666 table)",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    for name in ("share_table", "out"):
        try:
            setattr(args, name, _safe_path(str(getattr(args, name))))
        except ValueError as exc:
            parser.error(str(exc))
    return args


def _write(out_path: str, payload: dict[str, Any]) -> None:
    with validated_open(
        out_path, "w", allowed_roots=(
            str(REPO_ROOT), os.path.realpath(os.path.expanduser("~")),
        ),
        encoding="utf-8",
    ) as handle:
        json.dump(payload, handle, indent=1, sort_keys=True)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    num_agents = (
        args.num_agents
        if args.num_agents is not None
        else declared_total(args.platform)
    )
    payload: dict[str, Any] = {
        "probe": "NORO-TOUCH-SHARE-02",
        "measured_at": _git_sha(),
        "platform": args.platform,
        "num_agents": num_agents,
        "epochs": args.epochs,
        "seeds": {},
    }
    for seed in args.seeds:
        payload["seeds"][str(seed)] = run_seed(
            seed, args.platform, args.bundle, args.epochs,
            num_agents, args.share_table,
        )
        _write(args.out, payload)
        print(f"seed {seed}: written {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
