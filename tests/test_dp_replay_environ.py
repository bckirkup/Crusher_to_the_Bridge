"""
test_dp_replay_environ.py — DP-REPLAY-ENVIRON-01 machinery invariants
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Diamond Princess replay environs (diamond rhythm catalog, real 2020
itinerary, confinement variant at epoch 391, staggered exercise outings)
rest on five mechanisms. These tests hold their invariants:

* the ``diamond`` catalog covers ``diamond_princess`` and deals a sea day;
* a scheduled protocol with ``start_hour_of_day`` binds from its declared
  hour, not from the day boundary — the epoch-391 witness;
* ``protocol_ids_for_day`` unions protocols activating later the same day
  so the dealing sees the confinement variant on day 16;
* the confinement variant deals exercise outings only for the rolled-out
  cohorts, alternate-day, group-capped;
* ``outing_zone_for`` returns the authorized destination a confined agent
  may occupy ahead of the home-zone override;
* the passenger-disposition block claims uncommitted Free/Meal epochs at
  the declared shares.
"""

from __future__ import annotations

import json
import os
import sys
from types import SimpleNamespace

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from engines.rhythm_layer import RhythmLayer  # noqa: E402
from engines.scenario_schedule import (  # noqa: E402
    ScenarioSchedule,
    ScheduledProtocol,
)
from engines.sim_clock import HOURS, SimClock  # noqa: E402

CONFINEMENT_SOP = "Diamond Princess Cabin Quarantine (2020-02-05)"


def _load_zones() -> list[dict]:
    path = os.path.join(
        REPO_ROOT, "data", "platforms", "diamond_princess",
        "spatial_layout.json",
    )
    zones = json.load(open(path, encoding="utf-8"))["zones"]
    for zone in zones:
        zone["name"] = zone.pop("id")
    return zones


def _agent(agent_id: int, *, home: str, role: str = "passenger",
           party: int | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        agent_id=agent_id,
        role=role,
        agent_class="passenger_general" if role == "passenger" else "crew_general",
        meal_seating=0,
        dining_zone="HorizonCourt",
        work_zone="MainGalley",
        free_zone="NeptunePool",
        home_zone=home,
        party_id=party if party is not None else agent_id,
        ashore=False,
        schedule=["Sleep"] * 8 + ["Free"] * 12 + ["Meal"] * 4,
    )


def _layer(**cfg) -> RhythmLayer:
    layer = RhythmLayer.from_platform(
        "diamond_princess",
        _load_zones(),
        seed=42,
        clock=SimClock(mode=HOURS),
        config={"enabled": True, "catalog": "diamond", **cfg},
    )
    assert layer is not None
    return layer


def test_diamond_catalog_builds_and_deals() -> None:
    _load_zones()
    layer = _layer()
    agents = [_agent(i, home="PC_D8_P_M") for i in range(30)]
    layer.deal_day(agents, "sea_day", set(), 1)
    placed = {
        layer.location_for(a, h, "Free")
        for a in agents
        for h in (10, 15, 20)
    }
    assert any(p is not None for p in placed)


def test_hour_level_schedule_activation() -> None:
    sched = ScenarioSchedule(
        entries=(
            ScheduledProtocol(
                protocol_id="SOP-017-DEDICATED",
                start_day=16,
                end_day=30,
                start_hour_of_day=7,
            ),
        ),
    )
    entry = sched.entries[0]
    assert not entry.active_on(16, 6)
    assert entry.active_on(16, 7)
    assert entry.active_on(17, 0)
    assert not entry.active_on(15, 23)
    clock = SimClock(mode=HOURS)
    forced: set[str] = set()
    sched.apply(390, clock, forced)
    assert forced == set()
    sched.apply(391, clock, forced)
    assert forced == {"SOP-017-DEDICATED"}


def test_dealing_day_union() -> None:
    sched = ScenarioSchedule(
        entries=(
            ScheduledProtocol(
                protocol_id="SOP-017-DEDICATED",
                start_day=16,
                end_day=30,
                start_hour_of_day=7,
            ),
        ),
    )
    assert sched.protocol_ids_for_day(15) == set()
    assert sched.protocol_ids_for_day(16) == {"SOP-017-DEDICATED"}
    assert sched.protocol_ids_for_day(31) == set()


def _confined_agents() -> list[SimpleNamespace]:
    """Interior + exterior cohort passengers and a couple of crew."""
    zones = _load_zones()
    by_vent = {}
    for z in zones:
        vent = z.get("cabin_ventilation_type")
        if vent:
            by_vent.setdefault(vent, z["name"])
    interior = by_vent["interior_hvac"]
    exterior = by_vent["balcony_partial"]
    agents = [
        _agent(i, home=interior, party=i // 2) for i in range(60)
    ] + [
        _agent(100 + i, home=exterior, party=100 + i // 2) for i in range(60)
    ] + [
        _agent(200 + i, home="CC_D1_F", role="crew") for i in range(10)
    ]
    return agents


def test_exercise_rollout_cohorts_and_caps() -> None:
    layer = _layer()
    agents = _confined_agents()
    sops = {CONFINEMENT_SOP}
    # Day offset 0: interior cohort only; offset 1: interior parity flips;
    # offset 2: exterior joins.
    layer.deal_day(agents, "sea_day", sops, 16)
    day0 = layer.exercise_telemetry["days"][-1]
    assert day0["cohorts"]["exterior"] == 0
    assert day0["cohorts"]["interior"] > 0
    assert 0 < day0["attended"] <= day0["willing"]
    assert day0["group_size_max"] <= 125
    layer.deal_day(agents, "sea_day", sops, 17)
    layer.deal_day(agents, "sea_day", sops, 18)
    day2 = layer.exercise_telemetry["days"][-1]
    assert day2["cohorts"]["exterior"] > 0
    # Outings land in the declared exterior destinations.
    outings = [
        c
        for entries in layer._commitments.values()
        for c in entries
        if c.event_class == "exercise_outing"
    ]
    assert outings
    assert {c.zone for c in outings} <= {
        "OceanFront", "TerracePool", "OpenAirCinema", "NeptunePool",
    }


def test_no_exercise_without_confinement_sop() -> None:
    layer = _layer()
    agents = _confined_agents()
    layer.deal_day(agents, "sea_day", set(), 16)
    assert layer.exercise_telemetry["days"] == []
    assert layer.exercise_telemetry["invitations"] == 0


def test_outing_zone_for_and_transit() -> None:
    layer = _layer()
    agents = _confined_agents()
    layer.deal_day(agents, "sea_day", {CONFINEMENT_SOP}, 16)
    seen = set()
    for a in agents:
        for h in range(24):
            zone = layer.outing_zone_for(a, h)
            if zone is not None:
                seen.add(zone)
    # Exercise outings claim at least one declared exterior destination;
    # corridors and service zones appear too (transit and crew routes).
    assert seen & {
        "OceanFront", "TerracePool", "OpenAirCinema", "NeptunePool",
    }


def test_disposition_claims_free_and_meal() -> None:
    layer = _layer()
    zones = _load_zones()
    interior = next(
        z["name"] for z in zones
        if z.get("cabin_ventilation_type") == "interior_hvac"
    )
    agents = [_agent(i, home=interior, party=i // 2) for i in range(200)]
    layer.deal_day(agents, "sea_day", set(), 1)
    free_hits = [
        layer.location_for(a, 10, "Free") for a in agents
    ]
    home_share = sum(1 for z in free_hits if z == interior) / len(free_hits)
    # Declared 0.75 cabin-preferring share on UNCOMMITTED Free epochs —
    # committed morning events claim part of the cohort first, so the
    # realized share over ~100 parties sits below the declared share.
    assert 0.3 < home_share < 0.95
    meal_hits = [
        layer.location_for(a, 12, "Meal") for a in agents
    ]
    meal_home = sum(1 for z in meal_hits if z == interior) / len(meal_hits)
    assert meal_home > 0.2


def test_arm_grammar_keys_apply() -> None:
    """protocols_path + rhythm_overrides arm keys reach the run spec."""
    from picard_framework.covid_boarding_screen import (
        _apply_protocols_path,
        _apply_rhythm_overrides,
    )
    raw: dict = {"catalog": {}, "config_overrides": {}}
    _apply_protocols_path(raw, "data/config/protocols_covid_dp_dedicated.json")
    assert raw["catalog"]["protocols_path"].endswith(
        "protocols_covid_dp_dedicated.json",
    )
    _apply_rhythm_overrides(raw, {"port_day_onboard_midday_residual": 0.5})
    assert raw["config_overrides"]["rhythm"] == {
        "port_day_onboard_midday_residual": 0.5,
    }
