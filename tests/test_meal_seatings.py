"""SEAT-01: a dining venue serves its declared number of successive seatings.

Before this change every agent on a hull entered its meal block at the same
hour, so a venue's hourly occupancy was its whole assigned complement — on the
classic and spirit hulls more diners than the venue declares seats. A Dining
zone now declares ``meal_seatings``; each diner is dealt a cohort at spawn and
each meal block is cut into seat-turns (a 2-hour block in two sittings is two
1-hour turns) so at any hour one cohort is in the room and the venue's service
window is unchanged. These tests hold the schedule transform's invariants,
the per-hour occupancy bound, the hull declarations against their complements,
and bit-identity where a venue declares a single sitting. No epidemiological
outcome is asserted.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from crusher_labs import load_config
from engines.infection_dynamics_bridge import (
    CLASS_SCHEDULES,
    CREW_SCHEDULE,
    PASSENGER_DINING_SERVICE_TYPES,
    PASSENGER_SCHEDULE,
    KorkinShipEngine,
    stagger_meal_seating,
)
from orchestrator_init import load_spatial_layout

REPO = Path(__file__).resolve().parents[1]
HULLS = [
    "expedition_cruise_450",
    "classic_cruise_1900",
    "spirit_cruise_3000",
    "mega_cruise_5000",
]


def _layout(hull: str) -> dict:
    return json.loads((REPO / "data" / "platforms" / hull / "spatial_layout.json").read_text())


def _hull_zones(hull: str) -> list[dict]:
    cfg = {"ship_graph": {"spatial_layout": f"data/platforms/{hull}/spatial_layout.json"}}
    zones = load_spatial_layout(cfg)
    assert zones is not None
    return zones


def _engine(zones: list[dict], seed: int, agent_classes: list[dict] | None,
            num_passengers: int = 300, num_crew: int = 150) -> KorkinShipEngine:
    return KorkinShipEngine(
        num_passengers=num_passengers, num_crew=num_crew, initial_infected=0,
        zones=zones, seed=seed, agent_classes=agent_classes,
    )


def _meal_hours(schedule: list[str]) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    for h, a in enumerate(schedule):
        if a.startswith("Meal"):
            out.setdefault(a, []).append(h)
    return out


class TestScheduleTransform:
    @pytest.mark.parametrize("template", list(CLASS_SCHEDULES.values()), ids=list(CLASS_SCHEDULES))
    def test_a_single_sitting_is_the_template(self, template: list[str]) -> None:
        assert stagger_meal_seating(template, 0, 1) == template

    @pytest.mark.parametrize("template", list(CLASS_SCHEDULES.values()), ids=list(CLASS_SCHEDULES))
    @pytest.mark.parametrize("seatings", [2, 3])
    def test_cohorts_partition_each_meal_into_disjoint_turns(
        self, template: list[str], seatings: int,
    ) -> None:
        base = _meal_hours(template)
        cohorts = [
            _meal_hours(stagger_meal_seating(template, k, seatings))
            for k in range(seatings)
        ]
        for meal, hours in base.items():
            turn = max(len(hours) // seatings, 1)
            seen: set[int] = set()
            for k, cohort in enumerate(cohorts):
                assert len(cohort[meal]) == turn
                assert cohort[meal][0] == (hours[0] + k * turn) % 24
                assert not seen & set(cohort[meal])
                seen |= set(cohort[meal])

    def test_two_sittings_of_a_two_hour_block_fill_the_template_window(self) -> None:
        base = _meal_hours(PASSENGER_SCHEDULE)
        early = _meal_hours(stagger_meal_seating(PASSENGER_SCHEDULE, 0, 2))
        late = _meal_hours(stagger_meal_seating(PASSENGER_SCHEDULE, 1, 2))
        for meal, hours in base.items():
            assert sorted(early[meal] + late[meal]) == hours

    def test_a_late_crew_sitting_swaps_its_meal_hour_with_the_displaced_work_hour(self) -> None:
        shifted = stagger_meal_seating(CREW_SCHEDULE, 1, 2)
        landed = {h for hs in _meal_hours(shifted).values() for h in hs}
        for h, a in enumerate(CREW_SCHEDULE):
            if a.startswith("Meal"):
                assert shifted[h] == CREW_SCHEDULE[(h + 1) % 24]
            elif h not in landed:
                assert shifted[h] == a
        assert sorted(shifted) == sorted(CREW_SCHEDULE)

    def test_a_late_passenger_sitting_frees_the_vacated_hour(self) -> None:
        shifted = stagger_meal_seating(PASSENGER_SCHEDULE, 1, 2)
        for meal, hours in _meal_hours(PASSENGER_SCHEDULE).items():
            assert shifted[hours[0]] == "Free"
            assert shifted[hours[1]] == meal


class TestDeclarationsAgainstComplements:
    @pytest.mark.parametrize("hull", HULLS)
    def test_passenger_venues_seat_the_complement_across_their_seatings(self, hull: str) -> None:
        doc = _layout(hull)
        pax = doc["nominal_complement"]["passengers"]
        seats = 0
        for z in doc["zones"]:
            if z["type"] == "Dining" and z.get("dining_service_type") in PASSENGER_DINING_SERVICE_TYPES:
                seats += z["max_occupancy"] * z.get("meal_seatings", 1)
        assert seats >= pax, f"{hull}: {seats} passenger seat-turns for {pax} passengers"

    @pytest.mark.parametrize("hull", HULLS)
    def test_every_crew_mess_declares_more_than_one_seating(self, hull: str) -> None:
        for z in _layout(hull)["zones"]:
            if z.get("dining_service_type") == "crew_mess":
                assert z.get("meal_seatings", 1) >= 2

    def test_expedition_passenger_venues_are_a_single_sitting(self) -> None:
        for z in _layout("expedition_cruise_450")["zones"]:
            if z.get("dining_service_type") in PASSENGER_DINING_SERVICE_TYPES:
                assert z.get("meal_seatings", 1) == 1


def _peak_hourly_diners(engine: KorkinShipEngine, venue: str) -> int:
    diners = [a for a in engine.agents if a.dining_zone == venue]
    peak = 0
    for hour in range(24):
        n = sum(1 for a in diners if a.schedule[hour].startswith("Meal"))
        peak = max(peak, n)
    return peak


class TestOccupancyPerHour:
    @pytest.mark.parametrize("hull", ["classic_cruise_1900", "spirit_cruise_3000"])
    def test_a_two_seating_venue_holds_about_half_its_diners_at_once(self, hull: str) -> None:
        graph = load_config()["ship_graph"]
        doc = _layout(hull)
        pax = doc["nominal_complement"]["passengers"]
        crew = doc["nominal_complement"]["crew"]
        engine = _engine(_hull_zones(hull), 5, graph["agent_classes"], pax, crew)
        for z in doc["zones"]:
            if z.get("dining_service_type") not in PASSENGER_DINING_SERVICE_TYPES:
                continue
            assigned = sum(1 for a in engine.agents if a.dining_zone == z["id"])
            peak = _peak_hourly_diners(engine, z["id"])
            assert peak <= 0.6 * assigned + 5
            assert peak >= 0.4 * assigned - 5
            seatings = {a.meal_seating for a in engine.agents if a.dining_zone == z["id"]}
            assert seatings == {0, 1}

    def test_more_seatings_lower_the_peak_monotonically(self) -> None:
        peaks = []
        for seatings in (1, 2, 3):
            zones = [
                {"name": "Berthing", "type": "Room"},
                {"name": "MDR", "type": "Dining", "dining_service_type": "mdr",
                 "max_occupancy": 100, "meal_seatings": seatings},
                {"name": "Mess", "type": "Dining", "dining_service_type": "crew_mess",
                 "max_occupancy": 40},
                {"name": "Deck", "type": "Free"},
            ]
            peaks.append(_peak_hourly_diners(_engine(zones, 11, None), "MDR"))
        assert peaks[0] > peaks[1] > peaks[2]
        assert peaks[0] == 300
        assert peaks[2] <= 300 / 3 + 20


class TestSingleSittingIsUnchanged:
    def test_a_venue_without_the_declaration_keeps_the_template_schedule(self) -> None:
        zones = [
            {"name": "Berthing", "type": "Room"},
            {"name": "MDR", "type": "Dining", "dining_service_type": "mdr"},
            {"name": "Mess", "type": "Dining", "dining_service_type": "crew_mess"},
            {"name": "Deck", "type": "Free"},
        ]
        engine = _engine(zones, 7, None)
        for a in engine.agents:
            assert a.meal_seating == 0
            template = PASSENGER_SCHEDULE if a.role == "passenger" else CREW_SCHEDULE
            assert a.schedule == template

    def test_expedition_passengers_all_eat_in_one_sitting(self) -> None:
        graph = load_config()["ship_graph"]
        engine = _engine(_hull_zones("expedition_cruise_450"), 3, graph["agent_classes"])
        assert all(a.meal_seating == 0 for a in engine.agents if a.role == "passenger")
        crew_seatings = {a.meal_seating for a in engine.agents if a.role == "crew"}
        assert crew_seatings == {0, 1}
