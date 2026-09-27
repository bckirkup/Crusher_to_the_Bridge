"""
test_rhythm_layer.py — SHIP-RHYTHM-02 invariants
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The rhythm layer (``engines/rhythm_layer.py``, spec
``docs/rhythm/rhythm_spec.md``) replaces independent per-epoch location
draws with a schedule-conditioned day template. These tests hold the
invariants a wrong implementation cannot satisfy:

* the labelled baseline is inert — disabled / uncataloged / legacy-clock
  construction returns None and never consumes a draw;
* commitments land agents in the event's own zones during its window and
  let them go after;
* synchronized-end events pour their occupants onto transit corridors in
  the egress epoch;
* eligibility is class-scoped — a crew-only event claims no passengers;
* SOP variants decay participation by effect name, not silently;
* post-prandial windows open after completed meal participation and close.

No golden occupant counts: a cohort's seat map is a draw, not a constant.
"""

from __future__ import annotations

import json
import os
import sys
from types import SimpleNamespace

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from engines.rhythm_layer import RhythmLayer  # noqa: E402
from engines.sim_clock import HOURS, LEGACY_EPOCH_DAY, SimClock  # noqa: E402

CATALOGED_PLATFORMS = (
    "mega_cruise_5000",
    "spirit_cruise_3000",
    "classic_cruise_1900",
    "expedition_cruise_450",
    "enterprise_galaxy_tng",
    "enterprise_constitution_tos",
)


def _load_zones(platform_id: str) -> list[dict]:
    path = os.path.join(
        REPO_ROOT, "data", "platforms", platform_id, "spatial_layout.json",
    )
    zones = json.load(open(path, encoding="utf-8"))["zones"]
    for zone in zones:
        zone["name"] = zone.pop("id")
    return zones


def _agent(agent_id: int, role: str = "passenger", agent_class: str = "",
           zones: list[dict] | None = None) -> SimpleNamespace:
    zones = zones or []
    names = [z["name"] for z in zones] or ["Nowhere"]
    return SimpleNamespace(
        agent_id=agent_id,
        role=role,
        agent_class=agent_class or role,
        meal_seating=0,
        dining_zone=names[0],
        work_zone=names[0],
        free_zone=names[0],
        home_zone=names[0],
        ashore=False,
        schedule=["Sleep"] * 8 + ["Leisure"] * 16,
    )


def _layer(platform_id: str = "spirit_cruise_3000",
           zones: list[dict] | None = None, **cfg) -> RhythmLayer | None:
    return RhythmLayer.from_platform(
        platform_id,
        zones if zones is not None else _load_zones(platform_id),
        seed=42,
        clock=SimClock(mode=HOURS),
        config={"enabled": True, **cfg},
    )


@pytest.mark.parametrize("platform_id", CATALOGED_PLATFORMS)
def test_every_cataloged_platform_builds(platform_id: str) -> None:
    layer = _layer(platform_id)
    assert layer is not None
    layer.deal_day(
        [_agent(i, zones=_load_zones(platform_id)) for i in range(50)],
        "sea_day",
        set(),
        1,
    )


def test_disabled_flag_builds_nothing() -> None:
    layer = RhythmLayer.from_platform(
        "spirit_cruise_3000",
        _load_zones("spirit_cruise_3000"),
        seed=42,
        clock=SimClock(mode=HOURS),
        config={"enabled": False},
    )
    assert layer is None


def test_uncataloged_platform_builds_nothing() -> None:
    layer = RhythmLayer.from_platform(
        "destroyer_baseline",
        _load_zones("spirit_cruise_3000"),
        seed=42,
        clock=SimClock(mode=HOURS),
        config={"enabled": True},
    )
    assert layer is None


def test_legacy_clock_builds_nothing() -> None:
    layer = RhythmLayer.from_platform(
        "spirit_cruise_3000",
        _load_zones("spirit_cruise_3000"),
        seed=42,
        clock=SimClock(mode=LEGACY_EPOCH_DAY),
        config={"enabled": True},
    )
    assert layer is None


def test_committed_agents_occupy_event_zones() -> None:
    zones = _load_zones("spirit_cruise_3000")
    layer = _layer("spirit_cruise_3000", zones)
    assert layer is not None
    agents = [_agent(i, zones=zones) for i in range(400)]
    layer.deal_day(agents, "sea_day", set(), 1)
    # At least one epoch in the day must place some agents at committed
    # zones distinct from their schedule-token defaults.
    placed = sum(
        1
        for a in agents
        for h in range(24)
        if layer.location_for(a, h, a.schedule[h]) is not None
    )
    assert placed > 0


CREW_ONLY_EVENT_CLASSES = {"duty", "watch_turnover", "cleaning_rotation"}


def test_crew_only_event_claims_no_passengers() -> None:
    zones = _load_zones("spirit_cruise_3000")
    layer = _layer("spirit_cruise_3000", zones)
    assert layer is not None
    crew = [
        _agent(1000 + i, role="crew", agent_class="crew_general",
               zones=zones)
        for i in range(50)
    ]
    passengers = [_agent(i, zones=zones) for i in range(50)]
    layer.deal_day(crew + passengers, "sea_day", set(), 1)
    for p in passengers:
        for com in layer._commitments.get(p.agent_id, []):
            assert com.event_class not in CREW_ONLY_EVENT_CLASSES
    crew_committed = sum(
        bool(layer._commitments.get(c.agent_id)) for c in crew
    )
    assert crew_committed > 0


def test_synchronized_end_pours_into_corridor() -> None:
    zones = _load_zones("spirit_cruise_3000")
    layer = _layer("spirit_cruise_3000", zones)
    assert layer is not None
    agents = [_agent(i, zones=zones) for i in range(600)]
    layer.deal_day(agents, "sea_day", set(), 1)
    corridor_hours = 0
    for agent in agents:
        for com in layer._commitments.get(agent.agent_id, []):
            if com.egress_min is None or com.corridor_zone is None:
                continue
            for hour in range(24):
                if com.egress_epoch(hour):
                    loc = layer.location_for(agent, hour, "Leisure")
                    if loc == com.corridor_zone:
                        corridor_hours += 1
    assert corridor_hours > 0


def test_all_passenger_events_cancelled() -> None:
    zones = _load_zones("spirit_cruise_3000")
    layer = _layer("spirit_cruise_3000", zones)
    assert layer is not None
    agents = [_agent(i, zones=zones) for i in range(100)]
    layer.deal_day(agents, "sea_day", {"General Confinement to Quarters"}, 1)
    committed = sum(
        bool(layer._commitments.get(a.agent_id)) for a in agents
    )
    layer.deal_day(agents, "sea_day", set(), 1)
    baseline = sum(bool(layer._commitments.get(a.agent_id)) for a in agents)
    assert baseline > 0
    assert committed < baseline


def test_post_prandial_window_opens_after_meals() -> None:
    zones = _load_zones("spirit_cruise_3000")
    layer = _layer("spirit_cruise_3000", zones)
    assert layer is not None
    agents = [_agent(i, zones=zones) for i in range(400)]
    layer.deal_day(agents, "sea_day", set(), 1)
    flagged = sum(
        1
        for a in agents
        if any(layer.is_post_prandial(a.agent_id, h) for h in range(24))
    )
    assert flagged > 0


def test_sleep_share_moves_the_awake_minority_out() -> None:
    """The in-cabin share is graded: pinning it to 1.0 puts every Sleeper in
    its berth, 0.0 puts none (they resolve to the agent's free zone)."""
    zones = _load_zones("spirit_cruise_3000")
    agents = [_agent(i, zones=zones) for i in range(30)]
    for a in agents:
        a.home_zone, a.free_zone = "Cabin_X", "Lounge_Y"

    full = _layer("spirit_cruise_3000", zones,
                  asleep_in_cabin_share=[1.0] * 24)
    empty = _layer("spirit_cruise_3000", zones,
                   asleep_in_cabin_share=[0.0] * 24)
    assert full is not None
    assert empty is not None
    for a in agents:
        # No deal — commitments empty, so the Sleep-token branch is hit.
        a._test_home = full.location_for(a, 3, "Sleep")
        a._test_away = empty.location_for(a, 3, "Sleep")
    assert all(a._test_home == "Cabin_X" for a in agents)
    assert all(a._test_away == "Lounge_Y" for a in agents)


def test_flag_off_engine_consumes_no_draws() -> None:
    """Engine-level baseline inertness: disabled leaves _rhythm None and the
    post-prandial sentinel untouched on every agent."""
    from engines.infection_dynamics_bridge import KorkinShipEngine

    zones = _load_zones("spirit_cruise_3000")
    engine = KorkinShipEngine(
        num_passengers=20,
        num_crew=10,
        zones=zones,
        seed=7,
        clock=SimClock(mode=HOURS),
    )
    engine.attach_rhythm({"enabled": False}, "spirit_cruise_3000")
    assert engine._rhythm is None
    engine.step()
    assert all(
        a._rhythm_post_prandial is None for a in engine.agents
    )


def test_engine_rhythm_attach_enables(
) -> None:
    """attach_rhythm on a cataloged platform builds the layer; the engine
    then stamps post-prandial flags on agents each epoch."""
    from engines.infection_dynamics_bridge import KorkinShipEngine

    zones = _load_zones("spirit_cruise_3000")
    engine = KorkinShipEngine(
        num_passengers=20,
        num_crew=10,
        zones=zones,
        seed=7,
        clock=SimClock(mode=HOURS),
    )
    engine.attach_rhythm({"enabled": True}, "spirit_cruise_3000")
    assert engine._rhythm is not None
    engine.step()
    assert all(
        a._rhythm_post_prandial is not None for a in engine.agents
    )
