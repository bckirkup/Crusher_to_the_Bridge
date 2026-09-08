"""FOOD-ROLE-01: the food-handler channel is a duty state, not a room.

The transmission core's food-handler exposure (the staff shared-surface rate
and the food-handler contact multiplier) and the VSP duty exclusion's 48-hour
food-employee clause read one definition of "food employee": crew whose work
zone is a service zone. On top of that, the exposure is only taken while the
employee is on shift in that zone. Every crew member eats three times a day in
a Dining zone, so a role-and-location test would make the whole crew food
handlers at every meal; these tests hold the channel to the shift.

None of these tests asserts an epidemiological outcome.
"""

from __future__ import annotations

import numpy as np

from crusher_labs import load_config
from engines.crew_duty_exclusion import food_employee_ids, is_food_employee
from engines.infection_dynamics_bridge import KorkinAgent, KorkinShipEngine
from engines.sim_clock import HOURS, SimClock
from engines.transmission_core import TransmissionCore

GALLEY = "Main_Galley"
MESS = "CrewMess"
ENGINE = "Engine"
ZONE_TYPES = {GALLEY: "Galley", MESS: "Dining", ENGINE: "Engine"}


def _core() -> TransmissionCore:
    return TransmissionCore(
        rng=np.random.default_rng(3),
        zone_types=ZONE_TYPES,
        clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
    )


def _crew(work_zone: str, schedule: list[str]) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=1,
        role="crew",
        immune=False,
        home_zone="CC_1",
        dining_zone=MESS,
        work_zone=work_zone,
        free_zone="Lounge",
        schedule=schedule,
    )
    return agent


class TestOneDefinitionOfFoodEmployee:
    def test_the_set_and_the_predicate_agree_on_every_agent(self) -> None:
        roster = [
            _crew(GALLEY, ["Work"] * 24),
            _crew(ENGINE, ["Work"] * 24),
            _crew(MESS, ["Work"] * 24),
        ]
        for i, agent in enumerate(roster):
            agent.agent_id = i
        zones = _core().service_zones
        ids = food_employee_ids(roster, zones)
        for agent in roster:
            assert (agent.agent_id in ids) == is_food_employee(agent, zones)

    def test_a_passenger_is_never_a_food_employee(self) -> None:
        passenger = _crew(GALLEY, ["Work"] * 24)
        passenger.role = "passenger"
        assert not is_food_employee(passenger, _core().service_zones)


class TestTheChannelIsTheShift:
    def test_a_galley_worker_on_shift_in_the_galley_is_on_duty(self) -> None:
        core = _core()
        agent = _crew(GALLEY, ["Work"] * 24)
        assert core._on_service_duty(agent, GALLEY, 0)

    def test_the_same_worker_at_a_meal_is_a_diner(self) -> None:
        core = _core()
        agent = _crew(GALLEY, ["MealLunch"] * 24)
        assert not core._on_service_duty(agent, MESS, 0)
        assert not core._on_service_duty(agent, GALLEY, 0)

    def test_the_same_worker_off_watch_in_the_galley_is_not_on_duty(self) -> None:
        core = _core()
        for activity in ("Free", "Sleep"):
            agent = _crew(GALLEY, [activity] * 24)
            assert not core._on_service_duty(agent, GALLEY, 0)

    def test_an_engineer_is_never_on_service_duty(self) -> None:
        core = _core()
        agent = _crew(ENGINE, ["Work"] * 24)
        for zone in (GALLEY, MESS, ENGINE):
            assert not core._on_service_duty(agent, zone, 0)

    def test_a_service_worker_in_another_service_zone_is_not_on_duty(
        self,
    ) -> None:
        core = _core()
        agent = _crew(GALLEY, ["Work"] * 24)
        assert not core._on_service_duty(agent, MESS, 0)

    def test_duty_follows_the_schedule_hour_by_hour(self) -> None:
        core = _core()
        schedule = ["Work"] * 12 + ["Free"] * 12
        agent = _crew(GALLEY, schedule)
        on_duty = [core._on_service_duty(agent, GALLEY, e) for e in range(24)]
        assert on_duty == [True] * 12 + [False] * 12


class TestTheShippedRoster:
    """The food-employee population on a real hull is the service-duty crew."""

    def test_only_crew_working_a_service_zone_are_food_employees(self) -> None:
        cfg = load_config()
        graph = cfg["ship_graph"]
        zones = [
            {"name": z["name"], "type": z["type"], "capacity": "medium"}
            for z in graph["zones"]
        ]
        engine = KorkinShipEngine(
            num_passengers=140,
            num_crew=60,
            initial_infected=0,
            zones=zones,
            seed=5,
            agent_classes=graph.get("agent_classes"),
            gender_distribution=graph.get("gender_distribution"),
        )
        core = TransmissionCore(
            rng=np.random.default_rng(5),
            zone_types={z["name"]: z["type"] for z in zones},
        )
        service = core.service_zones
        food = food_employee_ids(engine.agents, service)
        by_id = {a.agent_id: a for a in engine.agents}

        assert food, "a real roster carries some food employees"
        for agent_id in food:
            agent = by_id[agent_id]
            assert agent.role == "crew"
            assert agent.work_zone in service
        for agent in engine.agents:
            if agent.agent_class == "crew_galley":
                assert agent.agent_id in food
            if agent.role != "crew" or agent.work_zone not in service:
                assert agent.agent_id not in food
        crew = [a for a in engine.agents if a.role == "crew"]
        assert len(food) < len(crew)
