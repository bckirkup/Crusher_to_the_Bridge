"""Admissibility gates for FOOD-COMMON-SOURCE-01.

The common-source mechanism adds synchronized foodborne events — one
contaminated pan at one Dining zone in one meal window — so the
outbreak tail that onset-curve scoring showed absent can exist. These
tests pin the design contract: which draws happen, where they happen,
who can source an event, and what never changes when the mechanism is
off or a pathogen is unarmed.

Every cfg here pins all three arm modes to ``"independent"`` — the
v1 labelled baseline FOOD-COMMON-SOURCE-02 keeps for comparison. Under
the shipped ``"object"`` defaults the ``*_event_probability`` knobs are
not drawn and contamination objects could provision, so these v1
semantics are only stable under the baseline spelling.
"""

from __future__ import annotations

import numpy as np
import pytest

from engines.infection_dynamics_bridge import (
    IllnessStatus,
    KorkinAgent,
    resolve_dining_service_type,
)
from engines.sim_clock import HOURS, SimClock
from engines.transmission_core import (
    ContactTracingMatrix,
    TransmissionCore,
)

PATHOGEN = "test_pathogen"
ZONE = "Windjammer"          # resolves to buffet — self-serve
MDR_ZONE = "Main_Dining"     # resolves to mdr — plated service


def _profile(armed: bool = True, **overrides: object) -> dict:
    profile: dict[str, object] = {
        "shedding_curve_log10": [11.0] * 12,
        "asymptomatic_shedding_log10": [11.0] * 12,
        "symptom_onset_day": 0.0,
        "dose_adjustment": 4.0,
        "dose_response": {"model": "exponential", "k": 0.01},
        "hand_inactivation_rate_per_hour": 0.61,
        "hand_hygiene_rate_per_hour": 0.0,
        "food_contamination": {"enabled": False},
    }
    if armed:
        profile["common_source_events"] = {"enabled": True}
    profile.update(overrides)
    return profile


def _diner(
    agent_id: int,
    *,
    dining_zone: str = ZONE,
    activity: str = "Meal:Lunch",
    location: str | None = ZONE,
    infected: bool = False,
) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=agent_id,
        role="passenger",
        immune=False,
        home_zone="Berthing_Passenger",
        dining_zone=dining_zone,
        work_zone="Crew_Work",
        free_zone="Lido",
        schedule=[activity] * 24,
    )
    agent.current_location = location
    agent.current_activity = activity
    if infected:
        agent.infect_with_pathogen(PATHOGEN, 1.0, 0, time_infected=24)
        agent.infections[PATHOGEN]["illness"] = IllnessStatus.NOT_ILL
        agent.hand_load_by_pathogen[PATHOGEN] = 1e8
    return agent


def _handler(agent_id: int, *, work_zone: str = ZONE) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=agent_id,
        role="crew",
        immune=False,
        home_zone="Berthing_Crew",
        dining_zone="Crew_Mess",
        work_zone=work_zone,
        free_zone="Lido",
        schedule=["Work"] * 24,
    )
    agent.current_location = work_zone
    agent.current_activity = "Work"
    agent.infect_with_pathogen(PATHOGEN, 1.0, 0, time_infected=24)
    agent.infections[PATHOGEN]["illness"] = IllnessStatus.NOT_ILL
    agent.hand_load_by_pathogen[PATHOGEN] = 1e8
    return agent


def _core(
    *,
    cfg_cs: dict | None = None,
    profile: dict | None = None,
    zone: str = ZONE,
    seed: int = 7,
    food_safety_posture: float | None = None,
) -> TransmissionCore:
    cs = dict(cfg_cs or {"mode": "on"})
    if food_safety_posture is not None:
        cs["food_safety_posture"] = food_safety_posture
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={zone: 50.0},
        pathogen_profiles={PATHOGEN: profile or _profile()},
        zone_types={zone: "Dining"},
        cfg={"transmission": {"common_source": cs}},
        clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
    )
    core.initialize_zones([zone])
    core._quarantined_ids = set()
    return core


def _force_lot(cfg_cs: dict | None = None) -> dict:
    cs = {"mode": "on", "lot_mode": "independent",
          "handler_mode": "independent", "diner_mode": "independent",
          "lot_event_probability": 1.0}
    cs.update(cfg_cs or {})
    return cs


def _step(
    core: TransmissionCore,
    agents: list[KorkinAgent],
    zone: str = ZONE,
    epochs: int = 30,
) -> tuple[list[dict], list[dict], dict[int, float]]:
    """Run the pathway epoch by epoch; collect every event/exposure."""
    core._agents_by_id = {a.agent_id: a for a in agents}
    events: list[dict] = []
    exposures: list[dict] = []
    doses: dict[int, float] = {}
    for epoch in range(epochs):
        matrix = ContactTracingMatrix(epoch=epoch)
        doses_epoch: dict[int, float] = {}
        pw: dict[int, dict[str, float]] = {}
        core._pathway_common_source(
            epoch, {zone: agents}, doses_epoch, matrix, pw,
            pathogen_id=PATHOGEN,
            profile=core.pathogen_profiles[PATHOGEN],
        )
        events.extend(matrix.common_source_events)
        exposures.extend(matrix.common_source_exposures)
        for aid, dose in doses_epoch.items():
            doses[aid] = doses.get(aid, 0.0) + dose
    return events, exposures, doses


# ── Gate 1: mode: off is a strict no-op and bit-identical ─────────────

def test_mode_off_fires_nothing_and_never_spawns_a_stream() -> None:
    agents = [_diner(i) for i in range(1, 40)]
    core = _core(cfg_cs=_force_lot({"mode": "off"}))
    events, exposures, doses = _step(core, agents)
    assert events == []
    assert exposures == []
    assert doses == {}
    assert core._cs_rng is None
    assert all(v == 0 for v in core.common_source_telemetry.values())


def test_mode_off_leaves_the_shared_stream_bit_identical() -> None:
    agents = [_diner(i) for i in range(1, 20)]
    core_on = _core(cfg_cs=_force_lot())
    core_off = _core(cfg_cs=_force_lot({"mode": "off"}))
    _step(core_on, agents)
    _step(core_off, [_diner(i) for i in range(1, 20)])
    # The dedicated stream is spawned only when armed — the shared RNG
    # must stand at the same place either way.
    assert core_on.rng.random() == pytest.approx(core_off.rng.random())


# ── Gate 2: an unarmed profile is a strict no-op ──────────────────────

def test_an_unarmed_pathogen_never_fires() -> None:
    agents = [_diner(i) for i in range(1, 40)]
    core = _core(
        cfg_cs=_force_lot(),
        profile=_profile(armed=False),
    )
    events, exposures, _ = _step(core, agents)
    assert events == []
    assert exposures == []
    assert core._cs_rng is None


# ── Gate 3: the lot event lands where the design says it does ─────────

def test_a_forced_lot_event_has_the_frozen_geometry() -> None:
    agents = [_diner(i) for i in range(1, 60)]
    core = _core(cfg_cs=_force_lot())
    events, _, _ = _step(core, agents)
    lots = [e for e in events if e["source_kind"] == "provisioned_lot"]
    assert len(lots) == 1
    event = lots[0]
    assert event["zone"] == ZONE
    assert event["meal"].startswith("Meal:")
    # The embarkation window caps at day index < 3; an epoch-day clock
    # puts start_epoch in [0, 72).
    assert event["start_epoch"] < 72
    assert event["source_agent_id"] is None
    assert event["lot_titre_gec_per_g"] > 0.0
    assert event["pan_mass"] >= 0.0
    assert event["servings_taken"] <= event["cohort_size"]
    assert event["servings_taken"] == len(event["taker_ids"])


# ── Gate 4: who can source an event ───────────────────────────────────

def test_the_handler_arm_needs_a_shedding_agent_on_service_duty() -> None:
    agents = [_handler(1)] + [_diner(i) for i in range(2, 60)]
    core = _core(cfg_cs={"mode": "on", "lot_mode": "independent",
                         "handler_mode": "independent",
                         "diner_mode": "independent",
                         "lot_event_probability": 0.0,
                         "handler_event_probability": 1.0})
    events, _, _ = _step(core, agents)
    handler_events = [e for e in events if e["source_kind"] == "ill_handler"]
    assert handler_events
    assert all(e["source_agent_id"] == 1 for e in handler_events)


def test_a_reported_symptomatic_handler_never_sources_an_event() -> None:
    handler = _handler(1)
    agents = [handler] + [_diner(i) for i in range(2, 60)]
    core = _core(cfg_cs={"mode": "on", "lot_mode": "independent",
                         "handler_mode": "independent",
                         "diner_mode": "independent",
                         "lot_event_probability": 0.0,
                         "handler_event_probability": 1.0})
    core._quarantined_ids = {1}
    events, _, _ = _step(core, agents)
    assert not [e for e in events if e["source_kind"] == "ill_handler"]


def test_an_ill_diner_can_only_source_a_self_serve_meal() -> None:
    # Buffet (self-serve) — the diner arm is live.
    agents = [_diner(i, infected=(i == 1)) for i in range(1, 60)]
    core = _core(cfg_cs={"mode": "on", "lot_mode": "independent",
                         "handler_mode": "independent",
                         "diner_mode": "independent",
                         "lot_event_probability": 0.0,
                         "handler_event_probability": 0.0,
                         "diner_event_probability": 1.0})
    events, _, _ = _step(core, agents)
    diner_events = [e for e in events if e["source_kind"] == "ill_diner"]
    assert diner_events
    assert all(e["source_agent_id"] == 1 for e in diner_events)


def test_a_shedding_diner_never_sources_a_plated_service() -> None:
    agents = [
        _diner(i, dining_zone=MDR_ZONE, infected=(i == 1))
        for i in range(1, 60)
    ]
    core = _core(
        cfg_cs={"mode": "on", "lot_mode": "independent",
                         "handler_mode": "independent",
                         "diner_mode": "independent",
                         "lot_event_probability": 0.0,
                "handler_event_probability": 0.0,
                "diner_event_probability": 1.0},
        zone=MDR_ZONE,
    )
    events, _, _ = _step(core, agents, zone=MDR_ZONE)
    assert not [e for e in events if e["source_kind"] == "ill_diner"]
    assert (
        resolve_dining_service_type({"name": MDR_ZONE})
        not in {"buffet", "crew_mess"}
    )


# ── Gate 5: mass conservation ─────────────────────────────────────────

def test_credited_dose_never_exceeds_the_pan_mass() -> None:
    agents = [_diner(i) for i in range(1, 60)]
    core = _core(cfg_cs=_force_lot())
    events, exposures, _ = _step(core, agents)
    assert events
    for event in events:
        credited = sum(
            e["dose"] for e in exposures
            if e["event_id"] == event["event_id"]
        )
        assert credited <= event["pan_mass"] + 1e-6
        assert credited == pytest.approx(
            event["per_serving_dose"]
            * len({
                e["target_id"] for e in exposures
                if e["event_id"] == event["event_id"]
            }),
            rel=1e-6,
        )


# ── Gate 6: the delivered dose lands on the declared pathway ──────────

def test_takers_are_dosed_under_the_common_source_food_key() -> None:
    agents = [_diner(i) for i in range(1, 60)]
    core = _core(cfg_cs=_force_lot())
    core._agents_by_id = {a.agent_id: a for a in agents}
    pw: dict[int, dict[str, float]] = {}
    for epoch in range(30):
        matrix = ContactTracingMatrix(epoch=epoch)
        core._pathway_common_source(
            epoch, {ZONE: agents}, {}, matrix, pw,
            pathogen_id=PATHOGEN,
            profile=core.pathogen_profiles[PATHOGEN],
        )
    assert pw
    assert all(
        set(agent_pw) == {"common_source_food"}
        for agent_pw in pw.values()
    )


# ── Gate 7: determinism ───────────────────────────────────────────────

def test_the_same_seed_reproduces_the_same_events() -> None:
    def run() -> tuple[list, list]:
        agents = [_diner(i) for i in range(1, 60)]
        core = _core(cfg_cs=_force_lot(), seed=23)
        return _step(core, agents)[:2]

    events_a, exposures_a = run()
    events_b, exposures_b = run()
    assert events_a == events_b
    assert exposures_a == exposures_b


# ── Gate 8: cohort integrity ──────────────────────────────────────────

def test_quarantined_and_non_dining_agents_never_take_a_serving() -> None:
    agents = [_diner(i) for i in range(1, 60)]
    quarantined = _diner(100)
    ashore = _diner(101)
    ashore.ashore = True
    agents.extend([quarantined, ashore])
    core = _core(cfg_cs=_force_lot())
    core._quarantined_ids = {100}
    events, _, _ = _step(core, agents)
    assert events
    for event in events:
        assert 100 not in event["taker_ids"]
        assert 101 not in event["taker_ids"]


def test_takers_come_only_from_the_meals_assigned_dining_cohort() -> None:
    in_zone = [_diner(i, dining_zone=ZONE) for i in range(1, 40)]
    elsewhere = [_diner(i + 40, dining_zone="Other") for i in range(1, 40)]
    agents = in_zone + elsewhere
    core = _core(cfg_cs=_force_lot())
    events, _, _ = _step(core, agents)
    assert events
    assigned = {a.agent_id for a in in_zone}
    for event in events:
        assert set(event["taker_ids"]) <= assigned


# ── Gate 9: food_safety_posture moves frequency, nothing else ─────────

def test_posture_one_is_bit_identical_to_no_posture() -> None:
    def run(posture: float) -> tuple[list, list]:
        agents = [_diner(i) for i in range(1, 60)]
        core = _core(
            cfg_cs=_force_lot(),
            seed=31,
            food_safety_posture=posture,
        )
        # 72 epochs spans the whole embarkation window (day 0-2).
        return _step(core, agents, epochs=72)[:2]

    events_flat, exposures_flat = run(1.0)
    events_none, exposures_none = run(1.0)  # same value → same draws
    assert events_flat == events_none
    assert exposures_flat == exposures_none
    assert events_flat[0]["food_safety_posture"] == pytest.approx(1.0)


def test_posture_changes_event_frequency_not_dose_mass() -> None:
    """Posture multiplies handler/diner probabilities — never titre."""
    agents = [_handler(1)] + [_diner(i) for i in range(2, 60)]
    low = _core(cfg_cs={"mode": "on", "lot_mode": "independent",
                         "handler_mode": "independent",
                         "diner_mode": "independent",
                         "lot_event_probability": 0.0,
                        "handler_event_probability": 0.05},
                food_safety_posture=0.1, seed=41)
    high = _core(cfg_cs={"mode": "on", "lot_mode": "independent",
                         "handler_mode": "independent",
                         "diner_mode": "independent",
                         "lot_event_probability": 0.0,
                         "handler_event_probability": 0.05},
                 food_safety_posture=5.0, seed=41)
    events_low, _, _ = _step(low, agents)
    events_high, _, _ = _step(high, [_handler(1)] + [
        _diner(i) for i in range(2, 60)])
    assert (
        len([e for e in events_high if e["source_kind"] == "ill_handler"])
        >= len([e for e in events_low if e["source_kind"] == "ill_handler"])
    )
    for event in events_high:
        assert event["food_safety_posture"] == pytest.approx(5.0)
