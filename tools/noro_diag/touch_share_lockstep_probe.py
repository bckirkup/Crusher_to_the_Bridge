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
fomite/contact/challenge seams (``_deposit_surface_mass``,
``_replenish_hand``, ``_fomite_pickup_request_for_area``,
``_fomite_pickup_requests_by_class``, ``_fomite_pickup_by_class``,
``_deliver_fomite_requests``, ``_deliver_fomite_requests_by_class``,
``_deliver_one_pickup``, ``_hand_to_mouth_dose``, ``_consume_surface_mass``,
``_consume_surface_mass_by_class``, ``_resolve_pathogen_challenge``,
``_pathway_fomite``, plus the hand-contact and sanitary seams
``_hand_contact_transfers``, ``_per_partner_contact_dose``,
``_sanitary_fomite_exposure``, ``_deliver_sanitary_requests_by_class``) and on
``PerSurfaceFomiteState.pickup_requests`` / ``.consume`` in
``engines/fomite_surfaces.py``, dispatched to the arm currently stepping via
a module-level active-arm holder. Every witness event carries ``draw_start``
/ ``draw_end`` -- its enclosing trace-index range on the arm's core stream --
and ``phase``, the coarse enclosing context, so a trace index maps to its
enclosing engine event. Wrappers never draw and never alter a value.

Detailed trace comparison stops at ``e*`` (the tracer then drops recording);
both arms keep stepping to ``--epochs`` so the cumulative
``hand_to_mouth_calls`` trajectory is complete for the readout.

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
event counters, both arms' ``hand_to_mouth_calls`` trajectories, and the
divergence record at ``e*`` -- trace window, differing-index entries, the
enclosing engine event per arm, the last aligned / first structurally
differing event pair, start-of-epoch hand loads for the named and differing
agents, the restricted mass diffs, the ordering witness, and the
classification. ``measured_at`` = the working-tree ``git rev-parse HEAD``.

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
from collections import defaultdict
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
HAND_DIFF_CAP = 200

# Frozen counter vocabulary (ledger NORO-TOUCH-SHARE-02 section 2).
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
    pathogen_id: str = PATHOGEN_ID
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
    """(arm, draw_start, enclosing phase) at wrapper entry."""
    arm = _arm()
    if arm is None:
        return None, 0, ""
    return arm, len(arm.core_rng.trace), _ctx_name(arm.core_rng.ctx)


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


def _bump(key: str, active_pathogen: bool = True) -> None:
    arm = _arm()
    if arm is not None and active_pathogen:
        arm.counts[key] += 1


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
        active = pathogen_id == PATHOGEN_ID
        arm, start, phase = _mark()
        prev = _set_ctx(f"fomite.deposit|{zone_name}" if active else "other")
        try:
            originals["_deposit_surface_mass"](
                self, pathogen_id, zone_name, mass,
            )
        finally:
            _restore_ctx(prev)
        _bump("deposit_calls", active)
        if active:
            _emit(arm, {
                "kind": "deposit", "zone": zone_name,
                "mass_gec": float(mass),
            }, start, phase)

    def replenish(
        self: Any, agent: Any, pathogen_id: str, profile: Any,
        zone_name: str | None = None,
    ) -> None:
        active = pathogen_id == PATHOGEN_ID
        prev = _set_ctx(
            f"fomite.replenish_hand|{zone_name}" if active else "other",
        )
        try:
            originals["_replenish_hand"](
                self, agent, pathogen_id, profile, zone_name,
            )
        finally:
            _restore_ctx(prev)
        _bump("replenish_calls", active)

    def pickup_request_for_area(
        self: Any, target: Any, zone_name: str, surface_mass: float,
        surface_area_m2: float, epoch: int,
    ) -> float:
        arm, start, phase = _mark()
        prev = _set_ctx(f"fomite.pickup_request|{zone_name}")
        try:
            request = originals["_fomite_pickup_request_for_area"](
                self, target, zone_name, surface_mass, surface_area_m2, epoch,
            )
        finally:
            _restore_ctx(prev)
        _bump("pickup_requests")
        _emit(arm, {
            "kind": "pickup_request", "zone": zone_name,
            "agent_id": int(target.agent_id),
            "surface_mass_gec": float(surface_mass),
            "request_gec": float(request),
        }, start, phase)
        return request

    def pickup_requests_by_class(
        self: Any, target: Any, zone_name: str, epoch: int, pathogen_id: str,
    ) -> Any:
        active = pathogen_id == PATHOGEN_ID
        prev = _set_ctx(
            f"fomite.pickup_requests_by_class|{zone_name}"
            if active else "other",
        )
        try:
            request = originals["_fomite_pickup_requests_by_class"](
                self, target, zone_name, epoch, pathogen_id,
            )
        finally:
            _restore_ctx(prev)
        _bump("pickup_by_class_calls", active)
        return request

    def pickup_by_class(
        self: Any, zone_name: str, susceptible: Any, surface_mass: float,
        epoch: int, *args: Any, **kwargs: Any,
    ) -> None:
        prev = _set_ctx(f"fomite.pickup_by_class|{zone_name}")
        try:
            originals["_fomite_pickup_by_class"](
                self, zone_name, susceptible, surface_mass, epoch,
                *args, **kwargs,
            )
        finally:
            _restore_ctx(prev)
        _bump("pickup_by_class_zones")

    def deliver(
        self: Any, requests: Any, zone_name: str, surface_mass: float,
        *args: Any, **kwargs: Any,
    ) -> float:
        pathogen_id = _kwarg(args, kwargs, 6, "pathogen_id")
        active = pathogen_id == PATHOGEN_ID
        arm, start, phase = _mark()
        prev = _set_ctx(f"fomite.deliver|{zone_name}" if active else "other")
        try:
            delivered = originals["_deliver_fomite_requests"](
                self, requests, zone_name, surface_mass, *args, **kwargs,
            )
        finally:
            _restore_ctx(prev)
        _bump("deliveries", active)
        if active:
            _emit(arm, {
                "kind": "deliver", "zone": zone_name,
                "requested_gec": float(
                    sum(mass for _, mass in requests)
                ),
                "surface_mass_gec": float(surface_mass),
                "delivered_gec": float(delivered),
            }, start, phase)
        return delivered

    def _class_masses(self: Any, zone_name: str, classes: Any) -> dict:
        per_surface = getattr(self, "_per_surface", None)
        if per_surface is None:
            return {}
        return {
            cls: float(per_surface.mass.get(
                (zone_name, PATHOGEN_ID, cls), 0.0,
            ))
            for cls in sorted(classes)
        }

    def deliver_by_class(
        self: Any, requests: Any, zone_name: str, surface_mass: float,
        *args: Any, **kwargs: Any,
    ) -> dict:
        pathogen_id = _kwarg(args, kwargs, 6, "pathogen_id")
        active = pathogen_id == PATHOGEN_ID
        classes = {c for _, req in requests for c in req}
        masses_before = _class_masses(self, zone_name, classes) if (
            active
        ) else {}
        arm, start, phase = _mark()
        prev = _set_ctx(
            f"fomite.deliver_by_class|{zone_name}" if active else "other",
        )
        try:
            delivered = originals["_deliver_fomite_requests_by_class"](
                self, requests, zone_name, surface_mass, *args, **kwargs,
            )
        finally:
            _restore_ctx(prev)
        _bump("deliveries", active)
        if active:
            _emit(arm, {
                "kind": "deliver_by_class", "zone": zone_name,
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
        pathogen_id = _kwarg(args, kwargs, 5, "pathogen_id")
        active = pathogen_id == PATHOGEN_ID
        arm, start, phase = _mark()
        prev = _set_ctx(
            f"fomite.deliver_one|{zone_name}" if active else "other",
        )
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
        _bump("deliver_one_pickups", active)
        if active:
            _emit(arm, {
                "kind": "deliver_one", "zone": zone_name,
                "agent_id": int(target.agent_id),
                "delivered_gec": float(delivered),
                "hand_load_before_gec": hand_before,
                "dose_gec": float(dose),
            }, start, phase)
        return dose

    def hand_to_mouth(
        self: Any, target: Any, epoch: int, hand_load: float,
    ) -> float:
        arm, start, phase = _mark()
        prev = _set_ctx("hand_to_mouth")
        try:
            dose = originals["_hand_to_mouth_dose"](
                self, target, epoch, hand_load,
            )
        finally:
            _restore_ctx(prev)
        _bump("hand_to_mouth_calls")
        _emit(arm, {
            "kind": "hand_to_mouth",
            "agent_id": int(target.agent_id),
            "hand_load_gec": float(hand_load),
            "dose_gec": float(dose),
        }, start, phase)
        return dose

    def hand_contact_transfers(
        self: Any, target: Any, sampled_shedders: Any, pathogen_id: str,
        cabin_confinement: bool,
    ) -> Any:
        active = pathogen_id == PATHOGEN_ID
        arm, start, phase = _mark()
        prev = _set_ctx("hand_contact" if active else "other")
        donors = [
            (int(shedder.agent_id), float(
                shedder.hand_load_by_pathogen.get(pathogen_id, 0.0),
            ))
            for shedder, _ in sampled_shedders
        ] if active else []
        try:
            moved = originals["_hand_contact_transfers"](
                self, target, sampled_shedders, pathogen_id,
                cabin_confinement,
            )
        finally:
            _restore_ctx(prev)
        _bump("hand_contact_calls", active)
        if active:
            moved_by_id = {
                int(shedder.agent_id): float(amount)
                for shedder, amount in moved
            }
            _emit(arm, {
                "kind": "hand_contact",
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
        active = pathogen_id == PATHOGEN_ID
        arm, start, phase = _mark()
        prev = _set_ctx("hand_contact.dose" if active else "other")
        hand_before = (
            float(target.hand_load_by_pathogen.get(pathogen_id, 0.0))
            if active else 0.0
        )
        try:
            dose, moved = originals["_per_partner_contact_dose"](
                self, target, sampled_shedders, cabin_confinement,
                pathogen_id, epoch,
            )
        finally:
            _restore_ctx(prev)
        if active:
            _emit(arm, {
                "kind": "hand_contact_dose",
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
        active = pathogen_id == PATHOGEN_ID
        arm, start, phase = _mark()
        prev = _set_ctx(f"fomite.consume|{zone_name}" if active else "other")
        try:
            originals["_consume_surface_mass"](
                self, pathogen_id, zone_name, delivered, previous_mass,
            )
        finally:
            _restore_ctx(prev)
        _bump("consume_calls", active)
        if active:
            _emit(arm, {
                "kind": "consume", "zone": zone_name,
                "delivered_gec": float(delivered),
                "previous_mass_gec": float(previous_mass),
            }, start, phase)

    def consume_by_class(
        self: Any, pathogen_id: str, zone_name: str,
        delivered_by_class: dict, previous_mass: float,
    ) -> None:
        active = pathogen_id == PATHOGEN_ID
        arm, start, phase = _mark()
        prev = _set_ctx(
            f"fomite.consume_by_class|{zone_name}" if active else "other",
        )
        try:
            originals["_consume_surface_mass_by_class"](
                self, pathogen_id, zone_name, delivered_by_class,
                previous_mass,
            )
        finally:
            _restore_ctx(prev)
        _bump("consume_calls", active)
        if active:
            _emit(arm, {
                "kind": "consume_by_class", "zone": zone_name,
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
        pathogen_id = _kwarg(args, kwargs, 3, "pathogen_id")
        prev = _set_ctx(
            "sanitary" if pathogen_id == PATHOGEN_ID else "other",
        )
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
        pathogen_id = _kwarg(args, kwargs, 3, "pathogen_id")
        active = pathogen_id == PATHOGEN_ID
        classes = {c for _, req in requests for c in req}
        masses_before = _class_masses(self, venue, classes) if active else {}
        arm, start, phase = _mark()
        prev = _set_ctx(
            f"sanitary.deliver_by_class|{venue}" if active else "other",
        )
        try:
            result = originals["_deliver_sanitary_requests_by_class"](
                self, requests, venue, epoch, *args, **kwargs,
            )
        finally:
            _restore_ctx(prev)
        _bump("sanitary_pickups", active)
        if active:
            _emit(arm, {
                "kind": "sanitary_deliver_by_class", "zone": venue,
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
        active = pathogen_id == PATHOGEN_ID
        prev = _set_ctx("challenge" if active else "other")
        try:
            result = originals["_resolve_pathogen_challenge"](
                self, epoch, agent, pathogen_id, *args, **kwargs,
            )
        finally:
            _restore_ctx(prev)
        _bump("challenge_calls", active)
        return result

    def pathway_fomite(
        self: Any, epoch: int, zone_occupants: Any, *args: Any,
        **kwargs: Any,
    ) -> Any:
        pathogen_id = _kwarg(args, kwargs, 4, "pathogen_id")
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
        active = pathogen_id == PATHOGEN_ID
        arm, start, phase = _mark()
        prev = _set_ctx(
            f"pickup_requests|{unit_key}" if active else "other",
        )
        masses_before = {
            cls: float(self.mass.get((unit_key, pathogen_id, cls), 0.0))
            for cls in sorted(inv.counts)
        } if active else {}
        try:
            request = originals["pickup_requests"](
                self, inv, unit_key, pathogen_id, contacts,
                used_fraction, hand_area_m2, transfer_efficiency,
            )
        finally:
            _restore_ctx(prev)
        if active:
            _emit(arm, {
                "kind": "class_pickup_requests", "zone": unit_key,
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
        active = pathogen_id == PATHOGEN_ID
        arm, start, phase = _mark()
        prev = _set_ctx(f"ps.consume|{unit_key}" if active else "other")
        masses_before = {
            cls: float(self.mass.get((unit_key, pathogen_id, cls), 0.0))
            for cls in sorted(delivered_by_class)
        } if active else {}
        try:
            originals["consume"](
                self, unit_key, pathogen_id, delivered_by_class,
            )
        finally:
            _restore_ctx(prev)
        if active:
            _emit(arm, {
                "kind": "ps_consume", "zone": unit_key,
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


def _snapshot_masses(core: Any, pathogen_id: str) -> dict[str, dict]:
    """Start-of-epoch surface mass per zone and per (zone, item class)."""
    zone = {
        str(z): float(m)
        for z, m in core.surface_pools_by_pathogen.get(
            pathogen_id, {},
        ).items()
    }
    by_class: dict[str, float] = {}
    per_surface = getattr(core, "_per_surface", None)
    if per_surface is not None:
        for (z, pid, cls), mass in per_surface.mass.items():
            if pid == pathogen_id:
                by_class[f"{z}|{cls}"] = float(mass)
    return {"zone_gec": zone, "zone_class_gec": by_class}


def _snapshot_hand_loads(sim: ShipSimulation) -> dict[int, float]:
    """Per-agent ``hand_load_by_pathogen`` at the epoch boundary."""
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
            if zones is not None and key.rsplit("|", 1)[0] not in zones and (
                key not in zones
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
        event.get("kind"), event.get("zone"), event.get("agent_id"),
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


def _gate_quantities_of(event: dict | None) -> dict[str, float]:
    """The mass/load that admits the draw for one event kind."""
    if not event:
        return {}
    kind = event.get("kind")
    if kind == "hand_to_mouth":
        return {"hand_load_gec": event["hand_load_gec"]}
    if kind == "hand_contact_dose":
        return {
            "acquired_gec": event["acquired_gec"],
            "hand_load_gec": event["hand_load_before_gec"],
        }
    if kind == "hand_contact":
        return {
            f"donor_hand|{donor['agent_id']}": donor["hand_load_gec"]
            for donor in event.get("donors", ())
        }
    if kind == "deliver_one":
        return {
            "delivered_gec": event["delivered_gec"],
            "hand_load_gec": event["hand_load_before_gec"],
        }
    if kind in ("deliver", "deliver_by_class", "sanitary_deliver_by_class"):
        gates = {
            f"class_mass|{event['zone']}|{cls}": mass
            for cls, mass in event.get("class_mass_before_gec", {}).items()
        }
        if "surface_mass_gec" in event:
            gates["surface_mass_gec"] = event["surface_mass_gec"]
        return gates
    if kind in ("pickup_request",):
        return {"surface_mass_gec": event["surface_mass_gec"]}
    if kind in ("class_pickup_requests", "ps_consume"):
        return {
            f"class_mass|{event['zone']}|{cls}": mass
            for cls, mass in event.get("class_mass_before_gec", {}).items()
        }
    if kind in ("consume", "consume_by_class"):
        return {"previous_mass_gec": event["previous_mass_gec"]}
    if kind == "deposit":
        return {"mass_gec": event["mass_gec"]}
    return {}


def _gate_quantities(
    enc_a: dict, enc_d: dict, first_diff: dict | None,
    snap_a: dict, snap_d: dict, zone: str | None,
) -> dict[str, dict[str, float]]:
    """Paired gate quantities for the classifier, per the frozen rule."""
    quantities: dict[str, dict[str, float]] = {}

    def merge(name: str, va: float, vd: float) -> None:
        quantities[name] = {"a": float(va), "d": float(vd)}

    event_a = (enc_a or {}).get("containing") or (
        (enc_a or {}).get("before")
    )
    event_d = (enc_d or {}).get("containing") or (
        (enc_d or {}).get("before")
    )
    names = set(_gate_quantities_of(event_a)) | set(
        _gate_quantities_of(event_d),
    )
    for name in sorted(names):
        merge(
            name,
            _gate_quantities_of(event_a).get(name, 0.0),
            _gate_quantities_of(event_d).get(name, 0.0),
        )
    if first_diff:
        for side, event in (("a", first_diff.get("a")),
                            ("d", first_diff.get("d"))):
            for name, value in _gate_quantities_of(event).items():
                quantities.setdefault(name, {"a": 0.0, "d": 0.0})
                quantities[name][side] = float(value)
    if zone is not None:
        merge(
            f"surface_mass|{zone}",
            snap_a["zone_gec"].get(zone, 0.0),
            snap_d["zone_gec"].get(zone, 0.0),
        )
        for key in sorted(set(snap_a["zone_class_gec"]) | set(
            snap_d["zone_class_gec"],
        )):
            if key.rsplit("|", 1)[0] == zone:
                merge(
                    f"class_mass|{key}",
                    snap_a["zone_class_gec"].get(key, 0.0),
                    snap_d["zone_class_gec"].get(key, 0.0),
                )
    return quantities


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
        va, vd = pair["a"], pair["d"]
        residue = 0.0 < abs(va) < RESIDUE_FLOOR_GEC or (
            0.0 < abs(vd) < RESIDUE_FLOOR_GEC
        )
        if residue and (va != vd or min(va, vd) <= 0.0):
            archetype_hits.append(name)
        if va != vd:
            differing.append(name)
            both_real = (
                abs(va) >= RESIDUE_FLOOR_GEC
                and abs(vd) >= RESIDUE_FLOOR_GEC
            )
            exact_zero = (va == 0.0) != (vd == 0.0)
            nonzero = max(abs(va), abs(vd)) >= RESIDUE_FLOOR_GEC
            if not (both_real or (exact_zero and nonzero)):
                expected_ok = False
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


def _ctx_zone(ctx: int) -> str | None:
    name = _ctx_name(ctx)
    return name.rsplit("|", 1)[1] if "|" in name else None


def _ordering_witness(
    events_a: list[dict], events_d: list[dict], epoch: int,
) -> dict[str, Any] | None:
    """First per-class delivery differing beyond the frozen tolerance."""
    kind = "deliver_by_class"
    by_a = [e for e in events_a if e["kind"] == kind]
    by_d = [e for e in events_d if e["kind"] == kind]
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
    """A = per_surface + areal + shipped; D = + declared + the #666 table."""
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


def _counts_snapshot(arm: Arm) -> dict[str, int]:
    return {key: int(arm.counts.get(key, 0)) for key in COUNTER_KEYS}


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


def _divergence_record(
    epoch: int, gen: str, d_star: int | None,
    arm_a: Arm, arm_d: Arm, snap_a: dict, snap_d: dict,
    hands_a: dict, hands_d: dict,
    counts_start: dict[str, dict], ordering: dict | None,
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
    zones = {
        ev.get("zone")
        for ev in (
            enc_a.get("containing"), enc_a.get("before"),
            enc_d.get("containing"), enc_d.get("before"),
            (first_diff or {}).get("a"), (first_diff or {}).get("d"),
        )
        if isinstance(ev, dict) and ev.get("zone")
    }
    zone = sorted(zones)[0] if zones else None
    ctx_entry = trace_a[d_star] if (
        d_star is not None and d_star < len(trace_a)
    ) else None
    if ctx_entry is not None and _ctx_zone(ctx_entry[0]) is not None:
        zones.add(_ctx_zone(ctx_entry[0]))
    quantities = _gate_quantities(enc_a, enc_d, first_diff, snap_a, snap_d, zone)
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
        "hand_loads_at_epoch_start": _hand_load_rows(
            hands_a, hands_d, named,
        ),
        "mass_diffs": _mass_diffs(snap_a, snap_d, zones),
        "events_a": arm_a.events,
        "events_d": arm_d.events,
        "counts_at_epoch_start": counts_start,
        "counts_identical_before_divergence": (
            counts_start["a"] == counts_start["d"]
        ),
        "ordering_witness": ordering,
        "classification": classify_divergence(quantities),
    }


def _compare_epoch(
    epoch: int, arm_a: Arm, arm_d: Arm, snap_a: dict, snap_d: dict,
    hands_a: dict, hands_d: dict,
    counts_start: dict[str, dict], ordering: dict | None,
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
                    counts_start, ordering,
                ),
                False,
            )
    if not states_equal:
        return (
            _divergence_record(
                epoch, "core", None, arm_a, arm_d,
                snap_a, snap_d, hands_a, hands_d,
                counts_start, ordering,
            ),
            False,
        )
    return None, True


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
    epoch_rows: list[dict] = []
    divergence: dict | None = None
    ordering: dict | None = None
    hands_a: dict = {}
    hands_d: dict = {}
    prev_hands: dict = {}
    with lockstep_instrumented(_ACTIVE):
        for epoch in range(epochs):
            aligned = divergence is None
            snap_a = snap_d = counts_start = None
            if aligned:
                prev_hands = {"a": hands_a, "d": hands_d}
                hands_a = _snapshot_hand_loads(arm_a.sim)
                hands_d = _snapshot_hand_loads(arm_d.sim)
                snap_a = _snapshot_masses(arm_a.sim.tx_core, PATHOGEN_ID)
                snap_d = _snapshot_masses(arm_d.sim.tx_core, PATHOGEN_ID)
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
            if aligned:
                if ordering is None:
                    ordering = _ordering_witness(
                        arm_a.events, arm_d.events, epoch,
                    )
                divergence, still = _compare_epoch(
                    epoch, arm_a, arm_d, snap_a, snap_d,
                    hands_a, hands_d, counts_start, ordering,
                )
                if not still:
                    divergence["hand_loads_prev_epoch"] = _hand_load_rows(
                        prev_hands["a"], prev_hands["d"], set(),
                    ) if prev_hands.get("a") else None
                    for arm in (arm_a, arm_d):
                        arm.root_rng.recording = False
                        arm.core_rng.recording = False
                        arm.record_events = False
            epoch_rows.append({
                "epoch": epoch,
                "draws": {
                    "a": arm_a.core_rng.draws, "d": arm_d.core_rng.draws,
                },
                "counts_a": _counts_snapshot(arm_a),
                "counts_d": _counts_snapshot(arm_d),
            })
    return {
        "seed": seed,
        "platform": platform,
        "num_agents": num_agents,
        "epochs": epochs,
        "divergence": divergence,
        "ordering_witness": ordering,
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
