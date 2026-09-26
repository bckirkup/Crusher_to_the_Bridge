"""Watch sections, the night-watch minority, phase jitter, and hot bunking.

Closes the schedule-fidelity gap of issue #104: the Java StrucCrew lottery
(~5% of crew on an inverted night watch) is implemented as
``night_watch_fraction``, agent classes may declare a ``schedule`` spec
(named template, inline 24 tokens, or ``watch_sections`` phase rotation),
every agent carries a persistent spawn-time ``phase_jitter`` (Java's
constructor ``randomness``, now active under the hourly clock via
``agent_behavior.schedule_jitter_hours``), and berthing can pool classes via
``berth_group`` with a zone's ``hot_bunk_ratio`` packing more occupants per
stateroom. Tests hold rotation invariants, graded sensitivity on the
night-watch draw, jitter bounds and persistence, and cabin-fill grouping —
no epidemiological outcome is asserted.
"""

from __future__ import annotations

import numpy as np
import pytest

from engines.infection_dynamics_bridge import (
    CLASS_SCHEDULES,
    CREW_NIGHT_WATCH_SCHEDULE,
    CREW_SCHEDULE,
    KorkinAgent,
    KorkinShipEngine,
    rotate_watch_schedule,
)
from orchestrator_init import assign_cabin_mates


def _engine(
    agent_classes: list[dict] | None,
    agent_behavior: dict | None = None,
    num_passengers: int = 300,
    num_crew: int = 150,
    seed: int = 42,
) -> KorkinShipEngine:
    return KorkinShipEngine(
        num_passengers=num_passengers,
        num_crew=num_crew,
        initial_infected=0,
        seed=seed,
        agent_classes=agent_classes,
        agent_behavior=agent_behavior,
    )


def _crew_class(class_id: str, fraction: float, schedule: object) -> dict:
    return {
        "class_id": class_id,
        "role_group": "crew",
        "fraction": fraction,
        "schedule": schedule,
    }


def _non_meal_positions(schedule: list[str]) -> list[int]:
    return [h for h, tok in enumerate(schedule) if not tok.startswith("Meal")]


def _agent(agent_id: int, home_zone: str, agent_class: str,
           berth_group: str = "") -> KorkinAgent:
    a = KorkinAgent(
        agent_id=agent_id, role="crew", immune=False,
        home_zone=home_zone, dining_zone="Mess",
        work_zone="Eng", free_zone="Rec",
        schedule=list(CREW_SCHEDULE), agent_class=agent_class,
        gender="male",
    )
    a.berth_group = berth_group
    return a


class TestWatchRotation:
    def test_single_section_is_the_template(self) -> None:
        for template in CLASS_SCHEDULES.values():
            assert rotate_watch_schedule(template, 0, 1) == template

    @pytest.mark.parametrize("template", list(CLASS_SCHEDULES.values()),
                             ids=list(CLASS_SCHEDULES))
    @pytest.mark.parametrize("sections", [2, 3, 4])
    def test_meals_pinned_and_activity_preserved(
        self, template: list[str], sections: int,
    ) -> None:
        for section in range(sections):
            rotated = rotate_watch_schedule(template, section, sections)
            assert len(rotated) == 24
            for h, tok in enumerate(template):
                if tok.startswith("Meal"):
                    assert rotated[h] == tok
            assert sorted(rotated) == sorted(template)

    def test_three_sections_cover_the_night_in_anti_phase(self) -> None:
        sections = [
            rotate_watch_schedule(CREW_SCHEDULE, k, 3) for k in range(3)
        ]
        sleep_sets = [
            {h for h, tok in enumerate(s) if tok == "Sleep"} for s in sections
        ]
        for i, s in enumerate(sleep_sets):
            for j, other in enumerate(sleep_sets):
                if i != j:
                    assert not s & other
        assert set().union(*sleep_sets) == set(_non_meal_positions(CREW_SCHEDULE))

    def test_sections_distinct(self) -> None:
        rotated = {
            tuple(rotate_watch_schedule(CREW_SCHEDULE, k, 3)) for k in range(3)
        }
        assert len(rotated) == 3


class TestNightWatch:
    NIGHT_SCHEDULE = {
        "class_id": "crew_deck",
        "role_group": "crew",
        "fraction": 1.0,
        "schedule": {"template": "crew_general", "night_watch_fraction": 0.5},
    }

    def test_fraction_zero_means_no_night_watch(self) -> None:
        cls = {**self.NIGHT_SCHEDULE,
               "schedule": {"template": "crew_general",
                            "night_watch_fraction": 0.0}}
        engine = _engine([cls], num_passengers=0, num_crew=120)
        assert not any(a.night_watch for a in engine.agents)

    def test_fraction_one_means_all_night_watch(self) -> None:
        cls = {**self.NIGHT_SCHEDULE,
               "schedule": {"template": "crew_general",
                            "night_watch_fraction": 1.0}}
        engine = _engine([cls], num_passengers=0, num_crew=120)
        assert all(a.night_watch for a in engine.agents)
        for agent in engine.agents:
            for h in (0, 20, 21, 22, 23):
                assert agent.schedule[h] == "Sleep"
            for h in range(2, 8):
                assert agent.schedule[h] == "Work"
            assert agent.schedule[8] == "Meal:Breakfast"

    def test_graded_share_of_crew(self) -> None:
        def night_count(frac: float) -> int:
            cls = {**self.NIGHT_SCHEDULE,
                   "schedule": {"template": "crew_general",
                                "night_watch_fraction": frac}}
            engine = _engine([cls], num_passengers=0, num_crew=200, seed=7)
            return sum(a.night_watch for a in engine.agents)

        low, mid, high = (night_count(f) for f in (0.05, 0.25, 0.6))
        assert 0 < low < mid < high <= 200

    def test_passengers_never_night_watch(self) -> None:
        cls = {
            "class_id": "pax_deck",
            "role_group": "passenger",
            "fraction": 1.0,
            "schedule": {"template": "passenger_general",
                         "night_watch_fraction": 1.0},
        }
        engine = _engine([cls], num_passengers=100, num_crew=0)
        assert not any(a.night_watch for a in engine.agents)

    def test_deepest_lottery_sleeps_hour_one(self) -> None:
        cls = {**self.NIGHT_SCHEDULE,
               "schedule": {"template": "crew_general",
                            "night_watch_fraction": 0.5}}
        engine = _engine([cls], num_passengers=0, num_crew=200, seed=3)
        hour1_sleepers = [
            a for a in engine.agents
            if a.night_watch and a.schedule[1] == "Sleep"
        ]
        # The workOrSleep == 0 extra is ~1 per class in expectation; the
        # rest of the watch still Works at hour 1.
        assert 1 <= len(hour1_sleepers) < sum(a.night_watch for a in engine.agents)


class TestLegacyNightWatchLottery:
    def test_minority_share_bounds(self) -> None:
        engine = _engine(None, num_passengers=200, num_crew=150, seed=11)
        night = [a for a in engine.agents if a.role == "crew" and a.night_watch]
        assert 1 <= len(night) <= 30  # Java lottery mean: 150*(8/150) = 8
        for agent in night:
            # The roll==0 member additionally sleeps hour 1.
            assert agent.schedule == CREW_NIGHT_WATCH_SCHEDULE or (
                agent.schedule[2:] == CREW_NIGHT_WATCH_SCHEDULE[2:]
                and agent.schedule[:2] == ["Sleep", "Sleep"]
            )
        day_crew = [
            a for a in engine.agents
            if a.role == "crew" and not a.night_watch
        ]
        assert all(a.schedule[1] == "Sleep" for a in day_crew)


class TestWatchSectionSpawning:
    SPEC = {
        "class_id": "crew_ops",
        "role_group": "crew",
        "fraction": 1.0,
        "schedule": {"template": "crew_general", "watch_sections": 3},
    }

    def test_sections_dealt_round_robin(self) -> None:
        engine = _engine([self.SPEC], num_passengers=0, num_crew=90)
        sections = sorted(a.watch_section for a in engine.agents)
        assert set(sections) == {0, 1, 2}
        counts = [sections.count(k) for k in (0, 1, 2)]
        assert all(c == 30 for c in counts)
        schedules = {
            a.watch_section: a.schedule for a in engine.agents
        }
        assert len({tuple(schedules[k]) for k in schedules}) == 3

    def test_meals_synchronized_across_sections(self) -> None:
        engine = _engine([self.SPEC], num_passengers=0, num_crew=90)
        for h in (8, 13, 19):
            assert all(
                a.schedule[h].startswith("Meal") for a in engine.agents
            )


class TestScheduleSpecForms:
    def test_bare_string_is_a_template_name(self) -> None:
        engine = _engine(
            [_crew_class("deck", 1.0, "crew_galley")],
            num_passengers=0, num_crew=50,
        )
        assert all(a.schedule == CLASS_SCHEDULES["crew_galley"]
                   for a in engine.agents)

    def test_inline_tokens(self) -> None:
        tokens = ["Work"] * 12 + ["Meal:Lunch"] + ["Free"] * 11
        engine = _engine(
            [_crew_class("deck", 1.0, tokens)],
            num_passengers=0, num_crew=50,
        )
        assert all(a.schedule == tokens for a in engine.agents)

    def test_unknown_class_id_falls_back_to_role_template(self) -> None:
        engine = _engine(
            [_crew_class("crew_unheard_of", 1.0, None)],
            num_passengers=0, num_crew=50,
        )
        # schedule: None is no spec at all; drop the key entirely.
        engine = _engine(
            [{"class_id": "crew_unheard_of", "role_group": "crew",
              "fraction": 1.0}],
            num_passengers=0, num_crew=50,
        )
        assert all(a.schedule == CREW_SCHEDULE for a in engine.agents)

    def test_builtin_class_id_needs_no_schedule_field(self) -> None:
        engine = _engine(
            [{"class_id": "crew_medical", "role_group": "crew",
              "fraction": 1.0}],
            num_passengers=0, num_crew=50,
        )
        assert all(a.schedule == CLASS_SCHEDULES["crew_medical"]
                   for a in engine.agents)


class TestPhaseJitter:
    def test_disabled_draw_is_zero(self) -> None:
        engine = _engine(
            [_crew_class("deck", 1.0, "crew_general")],
            agent_behavior={"schedule_jitter_hours": 0.0},
            num_passengers=0, num_crew=50,
        )
        assert all(
            a.phase_jitter == pytest.approx(0.0) for a in engine.agents
        )

    def test_scalar_bounds_and_spread(self) -> None:
        engine = _engine(
            [_crew_class("deck", 1.0, "crew_general")],
            agent_behavior={"schedule_jitter_hours": 1.0},
            num_passengers=0, num_crew=100,
        )
        jitters = np.array([a.phase_jitter for a in engine.agents])
        assert np.all(np.abs(jitters) <= 1.0)
        assert jitters.std() > 0.1

    def test_per_role_ranges(self) -> None:
        classes = [
            _crew_class("deck", 0.5, "crew_general"),
            {"class_id": "pax", "role_group": "passenger",
             "fraction": 0.5, "schedule": "passenger_general"},
        ]
        engine = _engine(
            classes,
            agent_behavior={"schedule_jitter_hours":
                            {"passenger": 2.0, "crew": 1.0}},
            num_passengers=200, num_crew=200,
        )
        crew = [a.phase_jitter for a in engine.agents if a.role == "crew"]
        pax = [a.phase_jitter for a in engine.agents
               if a.role == "passenger"]
        assert all(abs(j) <= 1.0 for j in crew)
        assert all(abs(j) <= 2.0 for j in pax)
        assert any(abs(j) > 1.0 for j in pax)  # the wider range is reached

    def test_jitter_is_persistent(self) -> None:
        engine = _engine(
            [_crew_class("deck", 1.0, "crew_general")],
            num_passengers=0, num_crew=50,
        )
        before = [a.phase_jitter for a in engine.agents]
        engine.step()
        assert [a.phase_jitter for a in engine.agents] == pytest.approx(before)

    def test_jitter_moves_the_scheduled_token(self) -> None:
        agent = _agent(0, "B", "deck")
        assert agent.scheduled_token(3, randomness=0.0) == "Sleep"
        assert agent.scheduled_token(3, randomness=-1.0) == "Sleep"
        assert agent.scheduled_token(3, randomness=5.0) == "Meal:Breakfast"


class TestHotBunking:
    ZONE = {"name": "EC_X", "type": "Cabin_Corridor", "cabin_size": 2}

    def _cabin_sizes(self, agents: list[KorkinAgent],
                     zones: list[dict]) -> list[int]:
        assign_cabin_mates(agents, zones)
        cabins: dict[int, set[int]] = {}
        for a in agents:
            cabins.setdefault(a.agent_id, {a.agent_id, *a.cabin_mate_ids})
        seen: set[frozenset[int]] = set()
        for members in cabins.values():
            seen.add(frozenset(members))
        return sorted(len(c) for c in seen)

    def test_ratio_packs_more_per_cabin(self) -> None:
        agents = [
            _agent(i, "EC_X", "crew_deck", berth_group="enlisted")
            for i in range(8)
        ]
        sizes = self._cabin_sizes(agents, [{**self.ZONE, "hot_bunk_ratio": 2}])
        assert sizes == [4, 4]

    def test_no_ratio_keeps_cabin_size(self) -> None:
        agents = [
            _agent(i, "EC_X", "crew_deck", berth_group="enlisted")
            for i in range(8)
        ]
        sizes = self._cabin_sizes(agents, [self.ZONE])
        assert sizes == [2, 2, 2, 2]

    def test_berth_group_mixes_classes(self) -> None:
        agents = [
            _agent(i, "EC_X", "crew_deck", berth_group="enlisted")
            for i in range(4)
        ] + [
            _agent(i + 4, "EC_X", "crew_eng", berth_group="enlisted")
            for i in range(4)
        ]
        assign_cabin_mates(agents, [self.ZONE])
        by_id = {a.agent_id: a for a in agents}
        mixed = [
            a for a in agents
            if {by_id[m].agent_class for m in a.cabin_mate_ids} != {a.agent_class}
        ]
        assert mixed

    def test_without_berth_group_classes_stay_separate(self) -> None:
        agents = [
            _agent(i, "EC_X", "crew_deck") for i in range(4)
        ] + [
            _agent(i + 4, "EC_X", "crew_eng") for i in range(4)
        ]
        assign_cabin_mates(agents, [self.ZONE])
        by_id = {a.agent_id: a for a in agents}
        for a in agents:
            assert {by_id[m].agent_class for m in a.cabin_mate_ids} == {
                a.agent_class
            }
