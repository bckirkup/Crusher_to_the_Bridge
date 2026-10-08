"""Admissibility gates for FOOD-COMMON-SOURCE-02 leg 2.

``handler_mode: "object"`` and ``diner_mode: "object"`` — the shipped
defaults — replace the v1 per-window iid Bernoulli with persistent
contamination objects bound to an agent's contamination-relevant span:
one seeding draw per span/course, one pan per covered window while the
span holds, and a break in contiguity (exclusion, duty gap, station
change) ends the object so a later eligible span re-seeds on a fresh
draw. These tests pin the frozen spec's leg-2 invariants (gates
12–15); the v1 semantics under ``"independent"`` are pinned in
test_common_source_events.py.
"""

from __future__ import annotations

import numpy as np

import engines.transmission_core as tc
from engines.infection_dynamics_bridge import (
    InfectionStatus,
    KorkinAgent,
)
from engines.sim_clock import HOURS, SimClock
from engines.strain_state import StrainRegistry
from engines.transmission_core import (
    ContactTracingMatrix,
    TransmissionCore,
)
from tests.test_common_source_events import (
    MDR_ZONE,
    PATHOGEN,
    ZONE,
    _diner,
    _handler,
    _profile,
)

GALLEY_ZONE = "Main_Galley"     # name-typed galley service zone


def _leg2_cfg(**overrides: object) -> dict:
    """Armed cfg with both agent arms on the shipped object default.

    The lot arm stays on its v1 baseline spelling at rate 0 so leg-2
    reads isolate the handler/diner arms.
    """
    cs: dict[str, object] = {
        "mode": "on",
        "lot_mode": "independent",
        "lot_event_probability": 0.0,
        "handler_mode": "object",
        "diner_mode": "object",
        "handler_span_contamination_probability": 1.0,
        "diner_course_contamination_probability": 1.0,
    }
    cs.update(overrides)
    return cs


def _core_zones(
    zone_types: dict[str, str],
    cfg_cs: dict,
    seed: int = 7,
) -> TransmissionCore:
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={z: 50.0 for z in zone_types},
        pathogen_profiles={PATHOGEN: _profile()},
        zone_types=zone_types,
        cfg={"transmission": {"common_source": cfg_cs}},
        clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
    )
    core.initialize_zones(list(zone_types))
    core._quarantined_ids = set()
    return core


def _step_epochs(
    core: TransmissionCore,
    agents: list[KorkinAgent],
    occupants_by_zone: dict[str, list[KorkinAgent]],
    epochs: int,
    on_epoch=None,
) -> tuple[list[dict], list[dict]]:
    """Drive the pathway epoch by epoch; ``on_epoch(epoch)`` may mutate
    agents/quarantine before the epoch steps (mid-run span breaks)."""
    core._agents_by_id = {a.agent_id: a for a in agents}
    events: list[dict] = []
    objects: list[dict] = []
    matrix = ContactTracingMatrix(epoch=0)
    for epoch in range(epochs):
        if on_epoch is not None:
            on_epoch(epoch)
        matrix = ContactTracingMatrix(epoch=epoch)
        core._pathway_common_source(
            epoch, occupants_by_zone, {}, matrix, {},
            pathogen_id=PATHOGEN,
            profile=core.pathogen_profiles[PATHOGEN],
        )
        events.extend(matrix.common_source_events)
        objects.extend(matrix.common_source_objects)
    core._cs_close_voyage(epochs - 1, matrix)
    objects.extend(matrix.common_source_objects)
    return events, objects


# ── Gate 12a: a seeded handler object covers its span's windows ───────

def test_seeded_handler_object_emits_one_pan_per_covered_window() -> None:
    handler = _handler(1)
    agents = [handler] + [_diner(i) for i in range(2, 60)]
    core = _core_zones(
        {ZONE: "Dining"},
        _leg2_cfg(diner_course_contamination_probability=0.0),
    )
    events, objects = _step_epochs(
        core, agents, {ZONE: agents}, epochs=50,
    )
    objs = core._cs_objects[PATHOGEN]
    assert len(objs) == 1
    obj = objs[0]
    pans = [e for e in events if e["object_id"] == obj["object_id"]]
    # 50 epochs span three (zone, Lunch, day) windows — one pan each.
    assert len(pans) == 3
    assert all(e["source_kind"] == "ill_handler" for e in pans)
    assert all(e["source_agent_id"] == 1 for e in pans)
    assert all(e["zone"] == ZONE for e in pans)
    assert [e["pan_serial"] for e in pans] == [1, 2, 3]
    assert obj["pans_emitted"] == 3
    assert obj["windows_covered"] == 3
    row = [r for r in objects if r["object_id"] == obj["object_id"]]
    assert len(row) == 1
    assert row[0]["end_reason"] == "voyage_end"
    assert row[0]["source_agent_id"] == 1
    assert row[0]["item_label"] == ZONE


def test_one_seeding_draw_per_span_regardless_of_span_length() -> None:
    """Gate 15: a span consumes exactly one seeding draw — the draw is
    per (agent, span), never per window or per epoch."""
    handler = _handler(1)
    agents = [handler] + [_diner(i) for i in range(2, 60)]
    core = _core_zones(
        {ZONE: "Dining"},
        _leg2_cfg(diner_course_contamination_probability=0.0),
    )
    core._agents_by_id = {a.agent_id: a for a in agents}
    profile = core.pathogen_profiles[PATHOGEN]
    matrix = ContactTracingMatrix(epoch=0)

    class _CountingRng:
        def __init__(self, rng):
            self._rng = rng
            self.calls = 0

        def random(self, *args, **kwargs):
            self.calls += 1
            return self._rng.random(*args, **kwargs)

        def __getattr__(self, name):
            return getattr(self._rng, name)

    counting = _CountingRng(core._cs_rng)
    core._cs_rng = counting
    for epoch in range(20):
        core._cs_span_step(
            handler, "ill_handler", epoch, PATHOGEN, profile, matrix,
        )
    assert counting.calls == 1
    assert len(core._cs_objects[PATHOGEN]) == 1


# ── Gate 12b: contiguity — the span ends where eligibility breaks ─────

def test_duty_gap_terminates_the_span_and_a_later_span_reseeds() -> None:
    handler = _handler(1)
    agents = [handler] + [_diner(i) for i in range(2, 60)]
    core = _core_zones(
        {ZONE: "Dining"},
        _leg2_cfg(diner_course_contamination_probability=0.0),
    )

    def on_epoch(epoch: int) -> None:
        # Off-duty epochs 6-8; ``current_activity`` is the recorded
        # token ``_scheduled_activity`` reads first.
        handler.current_activity = "Rest" if 6 <= epoch <= 8 else "Work"

    events, objects = _step_epochs(
        core, agents, {ZONE: agents}, epochs=26, on_epoch=on_epoch,
    )
    objs = core._cs_objects[PATHOGEN]
    assert len(objs) == 2
    assert core.common_source_telemetry["objects_ill_handler"] == 2
    assert objects[0]["end_reason"] == "source_excluded"
    assert objects[0]["exhausted_epoch"] == 6
    assert objects[1]["end_reason"] == "voyage_end"
    first_obj_pans = [
        e for e in events
        if e["object_id"] == objects[0]["object_id"]
    ]
    assert all(e["start_epoch"] < 6 for e in first_obj_pans)


def test_station_change_terminates_one_span_and_starts_another() -> None:
    zone_types = {ZONE: "Dining", MDR_ZONE: "Dining"}
    core = _core_zones(
        zone_types,
        _leg2_cfg(diner_course_contamination_probability=0.0),
    )
    handler = _handler(1)     # work_zone ZONE, dining Crew_Mess
    agents = [handler] + [_diner(i) for i in range(2, 30)] + [
        _diner(i, dining_zone=MDR_ZONE) for i in range(30, 55)
    ]

    def on_epoch(epoch: int) -> None:
        if epoch == 10:
            handler.work_zone = MDR_ZONE
            handler.current_location = MDR_ZONE
        elif epoch == 18:
            handler.work_zone = ZONE
            handler.current_location = ZONE

    events, objects = _step_epochs(
        core, agents,
        {ZONE: agents, MDR_ZONE: agents},
        epochs=25, on_epoch=on_epoch,
    )
    objs = core._cs_objects[PATHOGEN]
    assert len(objs) == 3
    assert [o["zone"] for o in objs] == [ZONE, MDR_ZONE, ZONE]
    assert [r["end_reason"] for r in objects] == [
        "source_excluded", "source_excluded", "voyage_end",
    ]
    mdr_pans = [e for e in events if e["zone"] == MDR_ZONE]
    assert mdr_pans
    assert all(
        e["object_id"] == objs[1]["object_id"] for e in mdr_pans
    )


def test_quarantine_breaks_the_span_and_release_reseeds() -> None:
    handler = _handler(1)
    agents = [handler] + [_diner(i) for i in range(2, 60)]
    core = _core_zones(
        {ZONE: "Dining"},
        _leg2_cfg(diner_course_contamination_probability=0.0),
    )

    def on_epoch(epoch: int) -> None:
        if epoch == 8:
            core._quarantined_ids.add(1)
        elif epoch == 14:
            core._quarantined_ids.discard(1)

    events, objects = _step_epochs(
        core, agents, {ZONE: agents}, epochs=25, on_epoch=on_epoch,
    )
    assert len(core._cs_objects[PATHOGEN]) == 2
    assert objects[0]["end_reason"] == "source_excluded"
    assert objects[0]["exhausted_epoch"] == 8
    # No pan lands while the source agent is excluded.
    quarantined_pans = [
        e for e in events if 8 <= e["start_epoch"] < 14
    ]
    assert quarantined_pans == []


def test_reported_symptomatic_handler_never_seeds() -> None:
    handler = _handler(1)
    agents = [handler] + [_diner(i) for i in range(2, 60)]
    core = _core_zones(
        {ZONE: "Dining"},
        _leg2_cfg(diner_course_contamination_probability=0.0),
    )
    core._quarantined_ids = {1}
    events, objects = _step_epochs(
        core, agents, {ZONE: agents}, epochs=30,
    )
    assert events == []
    assert objects == []
    assert core.common_source_telemetry["objects_ill_handler"] == 0


def test_shedding_end_closes_the_object_as_shedding_ended() -> None:
    handler = _handler(1)
    agents = [handler] + [_diner(i) for i in range(2, 60)]
    core = _core_zones(
        {ZONE: "Dining"},
        _leg2_cfg(diner_course_contamination_probability=0.0),
    )

    def on_epoch(epoch: int) -> None:
        if epoch == 12:
            handler.infections[PATHOGEN]["status"] = (
                InfectionStatus.RECOVERED
            )

    events, objects = _step_epochs(
        core, agents, {ZONE: agents}, epochs=20, on_epoch=on_epoch,
    )
    assert len(objects) == 1
    assert objects[0]["end_reason"] == "shedding_ended"
    assert objects[0]["exhausted_epoch"] == 12
    pans = [e for e in events if e["source_kind"] == "ill_handler"]
    assert all(e["start_epoch"] < 12 for e in pans)


def test_galley_handler_emits_into_one_drawn_dining_zone() -> None:
    zone_types = {ZONE: "Dining", GALLEY_ZONE: "Galley"}
    core = _core_zones(
        zone_types,
        _leg2_cfg(diner_course_contamination_probability=0.0),
    )
    handler = _handler(1, work_zone=GALLEY_ZONE)
    agents = [handler] + [_diner(i) for i in range(2, 60)]
    events, _ = _step_epochs(
        core, agents, {ZONE: agents, GALLEY_ZONE: agents}, epochs=30,
    )
    objs = core._cs_objects[PATHOGEN]
    assert len(objs) == 1
    obj = objs[0]
    assert obj["station"] == GALLEY_ZONE
    # Declared simplification: one Dining zone drawn once per object.
    assert obj["zone"] == ZONE
    pans = [e for e in events if e["object_id"] == obj["object_id"]]
    assert pans
    assert all(e["zone"] == ZONE for e in pans)


# ── Gate 13: the diner object lives at its self-serve venue ───────────

def test_seeded_diner_object_emits_one_pan_per_infectious_pass() -> None:
    diner = _diner(1, infected=True)
    agents = [diner] + [_diner(i) for i in range(2, 60)]
    core = _core_zones(
        {ZONE: "Dining"},
        _leg2_cfg(handler_span_contamination_probability=0.0),
    )
    events, objects = _step_epochs(
        core, agents, {ZONE: agents}, epochs=50,
    )
    objs = core._cs_objects[PATHOGEN]
    assert len(objs) == 1
    pans = [
        e for e in events if e["object_id"] == objs[0]["object_id"]
    ]
    assert len(pans) == 3
    assert all(e["source_kind"] == "ill_diner" for e in pans)
    assert all(e["source_agent_id"] == 1 for e in pans)
    assert core.common_source_telemetry["objects_ill_diner"] == 1
    assert objects[0]["end_reason"] == "voyage_end"


def test_diner_never_seeds_at_a_plated_venue() -> None:
    agents = [
        _diner(i, dining_zone=MDR_ZONE, infected=(i == 1))
        for i in range(1, 60)
    ]
    core = _core_zones(
        {MDR_ZONE: "Dining"},
        _leg2_cfg(handler_span_contamination_probability=0.0),
    )
    events, objects = _step_epochs(
        core, agents, {MDR_ZONE: agents}, epochs=50,
    )
    assert events == []
    assert objects == []
    assert core.common_source_telemetry["objects_ill_diner"] == 0


def test_diner_course_breaks_on_exclusion_and_reseeds() -> None:
    diner = _diner(1, infected=True)
    agents = [diner] + [_diner(i) for i in range(2, 60)]
    core = _core_zones(
        {ZONE: "Dining"},
        _leg2_cfg(handler_span_contamination_probability=0.0),
    )

    def on_epoch(epoch: int) -> None:
        if epoch == 8:
            core._quarantined_ids.add(1)
        elif epoch == 14:
            core._quarantined_ids.discard(1)

    events, objects = _step_epochs(
        core, agents, {ZONE: agents}, epochs=25, on_epoch=on_epoch,
    )
    assert len(core._cs_objects[PATHOGEN]) == 2
    assert objects[0]["end_reason"] == "source_excluded"
    assert objects[1]["end_reason"] == "voyage_end"
    assert [
        e for e in events
        if e["source_kind"] == "ill_diner" and 8 <= e["start_epoch"] < 14
    ] == []


# ── Gate 14: several objects share a window — no first-fired wins ─────

def test_two_objects_emit_one_pan_each_into_the_same_window() -> None:
    h1, h2 = _handler(1), _handler(2)
    agents = [h1, h2] + [_diner(i) for i in range(3, 60)]
    core = _core_zones(
        {ZONE: "Dining"},
        _leg2_cfg(diner_course_contamination_probability=0.0),
    )
    events, _ = _step_epochs(core, agents, {ZONE: agents}, epochs=20)
    objs = core._cs_objects[PATHOGEN]
    assert len(objs) == 2
    day0_lunch = [
        e for e in events
        if e["zone"] == ZONE and e["meal"] == "Meal:Lunch"
        and e["start_epoch"] == 0
    ]
    assert len(day0_lunch) == 2
    assert {e["object_id"] for e in day0_lunch} == {
        o["object_id"] for o in objs
    }
    assert core.common_source_telemetry["multi_pan_windows"] >= 1


# ── Gate 15: one realized contamination state per object ──────────────

def test_strain_mix_is_minted_once_per_object(monkeypatch) -> None:
    """The object's strain is taken once at seeding; every pan carries
    the same realized mix — unlike the v1 path, which rebuilds it per
    event."""
    calls: list[int] = []
    orig = tc.build_emission_mix
    monkeypatch.setattr(
        tc, "build_emission_mix",
        lambda contributions: (calls.append(1), orig(contributions))[1],
    )
    handler = _handler(1)
    agents = [handler] + [_diner(i) for i in range(2, 60)]
    core = _core_zones(
        {ZONE: "Dining"},
        _leg2_cfg(diner_course_contamination_probability=0.0),
    )
    core.strain_registry = StrainRegistry()
    events, _ = _step_epochs(
        core, agents, {ZONE: agents}, epochs=50,
    )
    pans = [e for e in events if e["source_kind"] == "ill_handler"]
    assert len(pans) == 3
    assert len(calls) == 1
    # The object's one realized strain rides every pan it emits.
    obj = core._cs_objects[PATHOGEN][0]
    assert obj["mix"] is not None
    assert obj["strain_id"] is not None

    calls.clear()
    core_v1 = _core_zones(
        {ZONE: "Dining"},
        {
            "mode": "on",
            "lot_mode": "independent",
            "handler_mode": "independent",
            "diner_mode": "independent",
            "lot_event_probability": 0.0,
            "handler_event_probability": 1.0,
            "diner_event_probability": 0.0,
        },
    )
    core_v1.strain_registry = StrainRegistry()
    # Fresh agents — the first run minted the handler a strain id that
    # this registry doesn't know.
    agents_v1 = [_handler(1)] + [_diner(i) for i in range(2, 60)]
    v1_events, _ = _step_epochs(
        core_v1, agents_v1, {ZONE: agents_v1}, epochs=50,
    )
    v1_pans = [
        e for e in v1_events if e["source_kind"] == "ill_handler"
    ]
    assert len(v1_pans) >= 2
    assert len(calls) == len(v1_pans)


def test_intra_object_hand_load_depletes_across_pans() -> None:
    """The deposit composes exactly as v1 — contacts x transfer x hand
    load, depleting the hand — so dose decay inside the object is
    realized, not declared."""
    handler = _handler(1)
    agents = [handler] + [_diner(i) for i in range(2, 60)]
    core = _core_zones(
        {ZONE: "Dining"},
        _leg2_cfg(diner_course_contamination_probability=0.0),
    )
    loads: list[float] = []

    def on_epoch(epoch: int) -> None:
        loads.append(handler.hand_load_by_pathogen[PATHOGEN])

    events, _ = _step_epochs(
        core, agents, {ZONE: agents}, epochs=50, on_epoch=on_epoch,
    )
    pans = [e for e in events if e["source_kind"] == "ill_handler"]
    assert len(pans) >= 2
    assert all(b <= a for a, b in zip(loads, loads[1:]))
    assert loads[-1] < loads[0]
    assert sum(e["pan_mass"] for e in pans) <= loads[0] + 1e-6


# ── Mode hygiene: off / unarmed / independent stay strict no-ops ──────

def test_mode_off_and_unarmed_draw_nothing_under_object_defaults() -> None:
    agents = [_handler(1)] + [
        _diner(i, infected=(i == 3)) for i in range(2, 60)
    ]
    core_off = _core_zones(
        {ZONE: "Dining"}, _leg2_cfg(**{"mode": "off"}),
    )
    events, objects = _step_epochs(
        core_off, agents, {ZONE: agents}, epochs=30,
    )
    assert events == [] and objects == []
    assert core_off._cs_rng is None
    assert all(
        v == 0 for v in core_off.common_source_telemetry.values()
    )


def test_independent_spelling_holds_no_objects_and_v1_rate_names() -> None:
    agents = [_handler(1)] + [
        _diner(i, infected=(i == 3)) for i in range(2, 60)
    ]
    core = _core_zones(
        {ZONE: "Dining"},
        {
            "mode": "on",
            "lot_mode": "independent",
            "handler_mode": "independent",
            "diner_mode": "independent",
            "lot_event_probability": 0.0,
            "handler_event_probability": 1.0,
            "diner_event_probability": 0.0,
        },
    )
    # The all-independent composition draws the v1 rate triple verbatim.
    assert set(core._cs_rates[PATHOGEN]) == {
        "lot_event_probability",
        "handler_event_probability",
        "diner_event_probability",
    }
    events, objects = _step_epochs(
        core, agents, {ZONE: agents}, epochs=30,
    )
    assert objects == []
    assert core._cs_objects.get(PATHOGEN, []) == []
    handler_events = [
        e for e in events if e["source_kind"] == "ill_handler"
    ]
    assert handler_events
    assert all(e["object_id"] is None for e in handler_events)
    assert all(e["pan_serial"] is None for e in handler_events)


def test_object_modes_are_deterministic_per_seed() -> None:
    def run() -> tuple[list[dict], list[dict]]:
        handler = _handler(1)
        agents = [handler] + [_diner(i) for i in range(2, 60)]
        core = _core_zones(
            {ZONE: "Dining"},
            _leg2_cfg(diner_course_contamination_probability=0.0),
        )
        return _step_epochs(core, agents, {ZONE: agents}, epochs=40)

    first_events, first_objects = run()
    second_events, second_objects = run()
    assert first_events == second_events
    assert first_objects == second_objects
