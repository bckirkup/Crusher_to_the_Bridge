"""The two replayed COVID hulls, as scenario records (#32).

A hull scenario is event geometry: how many people were aboard in which
roles, how long the event ran, which simulated days a protocol the record
names was in force, and which day the testing campaign's first recorded day
lands on. Nothing here is a biological parameter — both hulls share the one
``sars_cov2_resp`` profile — and nothing here is fitted, so the tests check
that the record survives translation into a run specification without a head
count, a calendar day or the fixed train/test split moving.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from engines.scenario_schedule import (
    ScenarioSchedule,
    ScheduledProtocol,
    resolve_scenario_schedule,
)
from engines.sim_clock import SimClock
from picard_framework.covid_hull_scenarios import (
    HullScenario,
    RoleClass,
    load_hull_scenarios,
    scenario_data_path,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
PATHOGEN = "sars_cov2_resp"
DIAMOND = "diamond_princess_2020"
MORTIMER = "greg_mortimer_2020"


@pytest.fixture(scope="module")
def scenarios():
    return load_hull_scenarios()


@pytest.fixture(scope="module")
def raw_records() -> dict[str, Any]:
    with open(scenario_data_path(), encoding="utf-8") as fh:
        return json.load(fh)


def _scenario(
    *,
    split_role: str = "training",
    duration_days: int = 10,
    epoch_duration_hours: float = 1.0,
    classes: tuple[tuple[str, str, int], ...] = (
        ("passenger_general", "passenger", 60),
        ("crew_general", "crew", 40),
    ),
    campaign_start_day: int = 2,
    scheduled: tuple[dict[str, Any], ...] = (),
) -> HullScenario:
    return HullScenario(
        scenario_id="unit_hull",
        hull_name="Unit Hull",
        split_role=split_role,
        pathogen_id=PATHOGEN,
        platform_id="cruise_ship",
        duration_days=duration_days,
        epoch_duration_hours=epoch_duration_hours,
        clock_mode="hours",
        population_total=sum(count for _, _, count in classes),
        role_classes=tuple(
            RoleClass(class_id=cid, role_group=grp, count=count)
            for cid, grp, count in classes
        ),
        campaign_id="unit_campaign",
        campaign_start_day=campaign_start_day,
        scheduled_protocols=scheduled,
    )


class TestFixedSplit:
    """The split the fit spec fixed in writing, carried as data."""

    def test_split_names_one_training_hull_and_the_held_out_hull(self, scenarios):
        assert scenarios.training_scenario_id == DIAMOND
        assert scenarios.held_out_scenario_ids == (MORTIMER,)

    def test_fit_target_is_the_training_hull_and_nothing_else(self, scenarios):
        assert scenarios.assert_fit_target(DIAMOND).scenario_id == DIAMOND
        with pytest.raises(ValueError, match="held_out"):
            scenarios.assert_fit_target(MORTIMER)

    def test_unknown_scenario_names_the_ones_that_exist(self, scenarios):
        with pytest.raises(KeyError, match=DIAMOND):
            scenarios["queen_elizabeth_2020"]

    def test_split_block_and_scenario_roles_must_agree(self, tmp_path, raw_records):
        record = json.loads(json.dumps(raw_records))
        record["split"]["training"] = [MORTIMER]
        record["split"]["held_out"] = [DIAMOND]
        path = tmp_path / "flipped.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        with pytest.raises(ValueError, match="split.training"):
            load_hull_scenarios(str(path), repo_root=str(tmp_path))

    def test_split_role_vocabulary_is_closed(self):
        with pytest.raises(ValueError, match="split_role"):
            _scenario(split_role="validation")

    def test_record_declares_the_document_that_fixed_the_split(
        self, scenarios, raw_records,
    ):
        assert "covid_trajectory_fit_spec" in scenarios.split_source
        assert raw_records["split"]["fixed_before_implementation"] is True
        assert raw_records["split"]["held_out_aggregates"]


class TestPopulationGeometry:
    """Head counts are counts, not fractions rounded back into counts."""

    def test_shipped_hulls_carry_their_published_complements(self, scenarios):
        diamond = scenarios[DIAMOND]
        mortimer = scenarios[MORTIMER]
        assert diamond.population_total == 3711
        assert {rc.class_id: rc.count for rc in diamond.role_classes} == {
            "passenger_general": 2666,
            "crew_general": 1045,
        }
        assert mortimer.population_total == 223
        assert sum(rc.count for rc in mortimer.role_classes) == 223

    def test_role_classes_must_sum_to_the_population(self):
        with pytest.raises(ValueError, match="role classes total"):
            HullScenario(
                scenario_id="mismatch",
                hull_name="Mismatch",
                split_role="training",
                pathogen_id=PATHOGEN,
                platform_id="cruise_ship",
                duration_days=10,
                epoch_duration_hours=1.0,
                clock_mode="hours",
                population_total=100,
                role_classes=(
                    RoleClass("passenger_general", "passenger", 60),
                    RoleClass("crew_general", "crew", 39),
                ),
                campaign_id="unit_campaign",
                campaign_start_day=0,
            )

    @pytest.mark.parametrize(
        ("passengers", "crew", "expected"),
        [(60, 40, 0.6), (2666, 1045, 2666 / 3711), (10, 90, 0.1)],
    )
    def test_role_fraction_tracks_the_declared_counts(
        self, passengers, crew, expected,
    ):
        scenario = _scenario(
            classes=(
                ("passenger_general", "passenger", passengers),
                ("crew_general", "crew", crew),
            ),
        )
        assert scenario.role_fraction("passenger") == pytest.approx(expected)
        assert scenario.role_fraction("passenger") + scenario.role_fraction(
            "crew",
        ) == pytest.approx(1.0)

    def test_agent_classes_emit_the_count_the_bridge_allocates_from(self, scenarios):
        classes = scenarios[DIAMOND].config_overrides()["ship_graph"][
            "agent_classes"
        ]
        assert [cls["count"] for cls in classes] == [2666, 1045]
        assert sum(cls["count"] for cls in classes) == 3711


class TestDurationAndClock:
    """Days are declared; epochs are derived through the clock."""

    @pytest.mark.parametrize(
        ("hours", "expected"), [(1.0, 240), (2.0, 120), (4.0, 60), (24.0, 10)],
    )
    def test_epoch_count_falls_as_the_epoch_lengthens(self, hours, expected):
        scenario = _scenario(duration_days=10, epoch_duration_hours=hours)
        assert scenario.num_epochs == expected

    def test_declared_duration_survives_the_round_trip_through_the_clock(
        self, scenarios,
    ):
        for scenario in (scenarios[DIAMOND], scenarios[MORTIMER]):
            clock = SimClock(
                epoch_duration_hours=scenario.epoch_duration_hours,
                mode=scenario.clock_mode,
            )
            assert clock.day_index(scenario.num_epochs - 1) == (
                scenario.duration_days - 1
            )

    def test_shipped_durations_are_the_recorded_events(self, scenarios):
        assert scenarios[DIAMOND].duration_days == 32
        assert scenarios[MORTIMER].duration_days == 28

    def test_non_positive_duration_and_epoch_length_are_refused(self):
        with pytest.raises(ValueError, match="duration_days"):
            _scenario(duration_days=0)
        with pytest.raises(ValueError, match="epoch_duration_hours"):
            _scenario(epoch_duration_hours=0.0)

    def test_config_declares_its_clock_units_to_the_run(self, scenarios):
        overrides = scenarios[MORTIMER].config_overrides()
        assert overrides["natural_history_clock"] == "hours"
        assert overrides["epoch_duration_hours"] == 1
        assert overrides["voyage"]["total_epochs"] == overrides["num_epochs"]


class TestScenarioSchedule:
    """A replayed protocol is held by the calendar, not by a trigger."""

    def test_window_opens_on_start_day_and_closes_after_end_day(self):
        entry = ScheduledProtocol("SOP-017", start_day=3, end_day=5)
        assert [entry.active_on(day) for day in range(7)] == [
            False, False, False, True, True, True, False,
        ]

    def test_open_ended_window_runs_to_the_end_of_the_event(self):
        entry = ScheduledProtocol("SOP-017", start_day=2)
        assert entry.active_on(2)
        assert entry.active_on(500)

    def test_malformed_windows_are_refused(self):
        with pytest.raises(ValueError, match="protocol_id"):
            ScheduledProtocol("", start_day=0)
        with pytest.raises(ValueError, match="negative"):
            ScheduledProtocol("SOP-017", start_day=-1)
        with pytest.raises(ValueError, match="precedes"):
            ScheduledProtocol("SOP-017", start_day=5, end_day=4)

    def test_apply_forces_inside_the_window_and_releases_outside_it(self):
        schedule = ScenarioSchedule((ScheduledProtocol("SOP-017", 1, 2),))
        clock = SimClock(epoch_duration_hours=12.0, mode="hours")
        forced: set[str] = set()
        seen = {}
        for epoch in range(8):
            schedule.apply(epoch, clock, forced)
            seen[clock.day_index(epoch)] = "SOP-017" in forced
        assert seen == {0: False, 1: True, 2: True, 3: False}

    def test_apply_leaves_protocols_the_calendar_does_not_name_alone(self):
        schedule = ScenarioSchedule((ScheduledProtocol("SOP-017", 5),))
        clock = SimClock(epoch_duration_hours=24.0, mode="hours")
        forced = {"SOP-009"}
        schedule.apply(0, clock, forced)
        assert forced == {"SOP-009"}

    def test_absent_config_is_an_empty_calendar(self):
        assert resolve_scenario_schedule(None).entries == ()
        assert resolve_scenario_schedule({}).protocol_ids == frozenset()

    def test_malformed_config_is_refused(self):
        with pytest.raises(ValueError, match="must be a mapping"):
            resolve_scenario_schedule({"scenario_schedule": ["SOP-017"]})
        with pytest.raises(ValueError, match="must be a list"):
            resolve_scenario_schedule({"scenario_schedule": {"protocols": 3}})

    def test_scenario_emits_its_calendar_as_config(self, scenarios):
        schedule = resolve_scenario_schedule(
            scenarios[DIAMOND].config_overrides(),
        )
        assert schedule.protocol_ids == frozenset({"SOP-017"})
        entry = schedule.entries[0]
        assert entry.start_day == 16
        assert entry.active_on(16)
        assert not entry.active_on(15)

    def test_scheduled_protocols_exist_in_the_protocol_catalogue(self, scenarios):
        with open(
            REPO_ROOT / "data" / "config" / "protocols.json", encoding="utf-8",
        ) as fh:
            catalogue = {p["protocol_id"] for p in json.load(fh)["protocols"]}
        for scenario in scenarios.scenarios.values():
            for entry in scenario.scheduled_protocols:
                assert entry["protocol_id"] in catalogue


class TestCampaignAlignment:
    """The campaign is aligned by day, and the alignment is all #32 sets."""

    def test_each_hull_points_at_its_own_campaign_record(self, scenarios):
        assert scenarios[DIAMOND].campaign_id == DIAMOND
        assert scenarios[MORTIMER].campaign_id == MORTIMER

    def test_campaign_block_carries_the_file_and_the_start_day(self, scenarios):
        block = scenarios[MORTIMER].config_overrides()["syndromic"][
            "testing_campaigns"
        ]
        assert block["campaign_file"].endswith("covid_testing_campaigns.json")
        assert block["campaigns"] == [
            {"campaign_id": MORTIMER, "start_day": 20},
        ]

    def test_campaign_ids_resolve_in_the_shipped_campaign_file(self, scenarios):
        with open(
            REPO_ROOT / "data" / "observation" / "covid_testing_campaigns.json",
            encoding="utf-8",
        ) as fh:
            known = {c["campaign_id"] for c in json.load(fh)["campaigns"]}
        for scenario in scenarios.scenarios.values():
            assert scenario.campaign_id in known

    def test_a_campaign_starting_after_the_event_is_refused(self):
        with pytest.raises(ValueError, match="campaign starts on day"):
            _scenario(duration_days=5, campaign_start_day=5)


class TestSharedBiology:
    """Both hulls run the same pathogen through the same machinery."""

    def test_both_hulls_name_the_one_covid_profile(self, scenarios):
        assert {s.pathogen_id for s in scenarios.scenarios.values()} == {PATHOGEN}

    def test_the_hull_arm_is_isolated_and_initiation_owns_the_index_case(
        self, scenarios,
    ):
        for scenario in scenarios.scenarios.values():
            overrides = scenario.pathogen_overrides()
            assert overrides["remove"]
            assert PATHOGEN not in overrides["remove"]
            assert overrides[PATHOGEN]["initial_infected"] is None
            seeds = scenario.config_overrides()["initiation"]["explicit_seeds"]
            assert [seed["pathogen"] for seed in seeds] == [PATHOGEN]

    def test_ground_truth_is_off_unless_a_caller_asks_for_it(self, scenarios):
        spec = scenarios[DIAMOND].to_run_spec_dict()
        assert spec["run"]["write_ground_truth"] is False
        assert spec["catalog"]["platform_id"] == scenarios[DIAMOND].platform_id

    @pytest.mark.parametrize("seed", [1, 42, 7919])
    def test_the_run_seed_is_pinned_by_the_caller(self, scenarios, seed):
        spec = scenarios[DIAMOND].to_run_spec_dict(random_seed=seed)
        assert spec["run"]["random_seed"] == seed
        assert spec["config_overrides"]["random_seed"] == seed

    def test_a_shortened_run_shortens_both_epoch_counts_together(self, scenarios):
        spec = scenarios[MORTIMER].to_run_spec_dict(num_epochs=12)
        assert spec["run"]["num_epochs"] == 12
        assert spec["config_overrides"]["num_epochs"] == 12
        assert spec["config_overrides"]["voyage"]["total_epochs"] == 12


class TestProvenanceAndRefusals:
    """Every scenario states where its numbers came from and what it will not do."""

    def test_each_hull_carries_graded_provenance(self, scenarios):
        for scenario in scenarios.scenarios.values():
            assert scenario.provenance
            for entry in scenario.provenance:
                assert entry["field"]
                assert entry["source"]
                assert entry["grade"] in {"A", "B", "C", "declared", "null"}

    def test_each_hull_carries_explicit_refusals(self, scenarios):
        for scenario in scenarios.scenarios.values():
            assert scenario.refusals

    def test_held_out_outcomes_are_recorded_as_observations_not_config(
        self, raw_records,
    ):
        mortimer = next(
            entry
            for entry in raw_records["scenarios"]
            if entry["scenario_id"] == MORTIMER
        )
        refusals = " ".join(mortimer["refusals"])
        assert "128/217" in refusals
        assert "81%" in refusals
        config_side = json.dumps(
            {
                key: value
                for key, value in mortimer.items()
                if key not in {"provenance", "refusals", "assumptions", "notes"}
            },
        )
        assert "217" not in config_side
        assert "0.81" not in config_side
        assert "81%" not in config_side


_ZONES = [
    {"name": "PC_Cabin", "type": "Room"},
    {"name": "CC_Berth", "type": "Room"},
    {"name": "Dining", "type": "Dining"},
    {"name": "Lounge", "type": "Free", "max_occupancy": 500},
]


def _engine(classes: list[dict[str, Any]], passengers: int, crew: int):
    from engines.infection_dynamics_bridge import KorkinShipEngine

    return KorkinShipEngine(
        num_passengers=passengers,
        num_crew=crew,
        initial_infected=0,
        zones=_ZONES,
        agent_classes=classes,
        seed=11,
    )


class TestExactClassCounts:
    """A declared head count is honoured to the person; fractions still round."""

    @pytest.mark.parametrize(
        ("passengers", "crew"), [(2666, 1045), (128, 95), (7, 3)],
    )
    def test_declared_counts_land_exactly(self, passengers, crew):
        engine = _engine(
            [
                {"class_id": "passenger_general", "role_group": "passenger",
                 "count": passengers, "home_zone_preference": "PC_"},
                {"class_id": "crew_general", "role_group": "crew",
                 "count": crew, "home_zone_preference": "CC_"},
            ],
            passengers, crew,
        )
        tally: dict[str, int] = {}
        for agent in engine.agents:
            tally[agent.agent_class] = tally.get(agent.agent_class, 0) + 1
        assert tally == {"passenger_general": passengers, "crew_general": crew}

    def test_fractions_still_allocate_by_proportion_with_remainder_first(self):
        engine = _engine(
            [
                {"class_id": "passenger_general", "role_group": "passenger",
                 "fraction": 0.5, "home_zone_preference": "PC_"},
                {"class_id": "crew_general", "role_group": "crew",
                 "fraction": 0.5, "home_zone_preference": "CC_"},
            ],
            6, 3,
        )
        tally: dict[str, int] = {}
        for agent in engine.agents:
            tally[agent.agent_class] = tally.get(agent.agent_class, 0) + 1
        # int(9 * 0.5) truncates to 4 twice; the odd person lands on the first class.
        assert tally == {"passenger_general": 5, "crew_general": 4}

    def test_counts_that_disagree_with_the_population_are_refused(self):
        with pytest.raises(ValueError, match="counts total"):
            _engine(
                [
                    {"class_id": "passenger_general", "role_group": "passenger",
                     "count": 60, "home_zone_preference": "PC_"},
                    {"class_id": "crew_general", "role_group": "crew",
                     "count": 30, "home_zone_preference": "CC_"},
                ],
                60, 40,
            )


class TestCampaignTelemetry:
    """Campaign specimens and onsets reach the epoch summary as counts."""

    @pytest.mark.parametrize("n_specimens", [0, 5, 217])
    def test_campaign_count_sums_across_pathogens(self, n_specimens):
        from orchestrator_record import _campaign_count

        result = {
            "campaign_specimens_by_pathogen": {
                PATHOGEN: list(range(n_specimens)),
                "other": [1, 2],
            },
        }
        assert _campaign_count(result, "campaign_specimens_by_pathogen") == (
            n_specimens + 2
        )
        assert _campaign_count({}, "campaign_specimens_by_pathogen") == 0


@pytest.fixture(scope="module")
def mortimer_steps():
    import contextlib
    import io

    from picard_framework.covid_hull_scenarios import build_run_spec_dict
    from picard_framework.run_spec import PicardRunSpec
    from picard_framework.simulation.ship_simulation import ShipSimulation

    raw = build_run_spec_dict(MORTIMER, num_epochs=30, random_seed=3)
    raw["config_overrides"]["scenario_schedule"]["protocols"][0]["start_day"] = 1
    spec = PicardRunSpec.from_picard_dict(str(REPO_ROOT), raw)
    sim = ShipSimulation(spec, display=False)
    results = []
    with contextlib.redirect_stdout(io.StringIO()):
        sim.initialize()
        for _ in range(30):
            results.append(sim.step())
    return sim, results


class TestScheduleInTheShip:
    """The calendar reaches the ship, and command cannot decline it."""

    def test_population_is_the_declared_complement(self, mortimer_steps):
        sim, _ = mortimer_steps
        tally: dict[str, int] = {}
        for agent in sim.engine.agents:
            tally[agent.agent_class] = tally.get(agent.agent_class, 0) + 1
        assert tally == {"passenger_general": 128, "crew_general": 95}
        assert sim.clock.hours_per_epoch == pytest.approx(1.0)

    def test_only_the_covid_arm_is_aboard(self, mortimer_steps):
        sim, _ = mortimer_steps
        assert set(sim.pathogen_profiles) == {PATHOGEN}

    def test_scheduled_protocol_holds_from_its_day_regardless_of_authorization(
        self, mortimer_steps,
    ):
        _, results = mortimer_steps
        active_by_epoch = [
            {m["protocol_id"] for m in res.active_protocols} for res in results
        ]
        assert all("SOP-017" not in ids for ids in active_by_epoch[:24])
        assert all("SOP-017" in ids for ids in active_by_epoch[24:])
        assert all(
            res.merged_modifiers.get("confine_all_to_quarters") is True
            for res in results[24:]
        )

    def test_confinement_reaches_passengers_and_spares_crew(self, mortimer_steps):
        sim, results = mortimer_steps
        before = results[23].epoch_record["summary"]["quarantined"]
        after = results[29].epoch_record["summary"]["quarantined"]
        assert before == 0 < after
        crew_ids = {
            a.agent_id for a in sim.engine.agents if a.agent_class == "crew_general"
        }
        assert not (sim.state.quarantined_ids & crew_ids)
        assert after + len(sim.state.quarantine_refusers) == 128
