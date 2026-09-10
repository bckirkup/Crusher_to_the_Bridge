"""The contact draw as a property of the activity, not of the day.

Behaviour and invariant tests for CONTACT-ARCH-01: when a run declares
``transmission.activity_contacts``, each susceptible's hourly contact draw comes
from the rate declared for the activity its schedule and the ship's
architecture put it in (cabin, corridor, service shift, other work, table,
venue, leisure, other). Absent, the uniform POLYMOD draw runs on its old code
path. No golden numbers: every expectation is a relation between runs, a
refusal, a conservation law or a bound.
"""
from __future__ import annotations

import numpy as np
import pytest

from engines.infection_dynamics_bridge import (
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
    KorkinShipEngine,
)
from engines.sim_clock import HOURS, SimClock
from engines.transmission_core import (
    CONTACT_ACTIVITIES,
    CONTACT_RATE_PER_HOUR_BOUNDS,
    TransmissionCore,
)
from engines.voyage_itinerary import LOCATION_ASHORE
from orchestrator_init import load_spatial_layout


LOUNGE = "Lounge"
DINING = "MainDining"
CORRIDOR = "PC_D6"
ZONE_TYPES = {LOUNGE: "Free", DINING: "Dining", CORRIDOR: "Cabin_Corridor"}
ZONE_VOLUMES = {LOUNGE: 3000.0, DINING: 1000.0, CORRIDOR: 600.0}

FLAT = {a: 2.0 for a in CONTACT_ACTIVITIES}


def _agent(
    aid: int,
    role: str,
    schedule: list[str],
    location: str,
    infected: bool = False,
    work_zone: str = LOUNGE,
) -> KorkinAgent:
    a = KorkinAgent(
        agent_id=aid, role=role, immune=False,
        home_zone=CORRIDOR, dining_zone=DINING,
        work_zone=work_zone, free_zone=LOUNGE,
        schedule=list(schedule),
    )
    if infected:
        a.infection_status = InfectionStatus.INFECTED
        a.illness_status = IllnessStatus.SYMPTOMATIC
        a.time_infected = 1
    a.current_location = location
    return a


def _block(rates: dict, enabled: bool = True) -> dict:
    return {"activity_contacts": {"enabled": enabled, "rates_per_hour": rates}}


def _core(tx: dict | None, seed: int = 5) -> TransmissionCore:
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes=dict(ZONE_VOLUMES),
        zone_types=dict(ZONE_TYPES),
        cfg={"transmission": dict(tx or {})},
    )
    core.initialize_zones(list(ZONE_TYPES))
    return core


def _room(location: str, token: str, n: int = 30, role: str = "passenger") -> list[KorkinAgent]:
    """Target 0 susceptible, everyone else shedding, all on one schedule token."""
    schedule = [token] * 24
    agents = [_agent(0, role, schedule, location)]
    agents += [_agent(i, role, schedule, location, infected=True) for i in range(1, n)]
    return agents


def _rows(core: TransmissionCore, agents: list[KorkinAgent], epochs: int) -> list[dict]:
    rows: list[dict] = []
    shedders = {a.agent_id for a in agents if a.is_infected}
    for epoch in range(1, epochs + 1):
        matrix, _ = core.execute_transmission(
            epoch=epoch, agents=agents,
            zone_pathogen_mass={z: 0.0 for z in ZONE_TYPES},
            quarantined_ids=set(),
        )
        rows.extend(matrix.shared_room_exposures)
        for a in agents:
            if a.agent_id not in shedders:
                a.infection_status = InfectionStatus.SUSCEPTIBLE
                a.illness_status = IllnessStatus.NOT_ILL
    return rows


def _draws(rows: list[dict], target: int = 0) -> list[int]:
    return [int(r["r0_draw"]) for r in rows if r["target_id"] == target]


class TestDeclaration:
    def test_absent_block_leaves_the_uniform_draw(self) -> None:
        assert _core(None).activity_contacts is None

    def test_disabled_block_leaves_the_uniform_draw(self) -> None:
        assert _core(_block(FLAT, enabled=False)).activity_contacts is None

    def test_an_enabled_block_reads_every_activity(self) -> None:
        core = _core(_block(FLAT))
        assert core.activity_contacts is not None
        assert set(core.activity_contacts) == set(CONTACT_ACTIVITIES)

    def test_a_bare_rate_applies_to_every_role(self) -> None:
        core = _core(_block(FLAT))
        assert core.activity_contacts is not None
        assert core.activity_contacts["leisure"] == {"passenger": 2.0, "crew": 2.0}

    def test_a_per_role_rate_is_read_per_role(self) -> None:
        rates = dict(FLAT, work_service={"passenger": 0.0, "crew": 4.0})
        core = _core(_block(rates))
        assert core.activity_contacts is not None
        assert core.activity_contacts["work_service"]["crew"] == pytest.approx(4.0)
        assert core.activity_contacts["work_service"]["passenger"] == pytest.approx(0.0)

    @pytest.mark.parametrize("dropped", list(CONTACT_ACTIVITIES))
    def test_a_missing_activity_is_refused(self, dropped: str) -> None:
        rates = {a: r for a, r in FLAT.items() if a != dropped}
        with pytest.raises(ValueError, match=dropped):
            _core(_block(rates))

    def test_an_unknown_activity_is_refused(self) -> None:
        with pytest.raises(ValueError, match="gym"):
            _core(_block(dict(FLAT, gym=1.0)))

    def test_a_per_role_rate_missing_a_role_is_refused(self) -> None:
        with pytest.raises(ValueError, match="crew"):
            _core(_block(dict(FLAT, leisure={"passenger": 1.0})))

    @pytest.mark.parametrize(
        "bad",
        [
            CONTACT_RATE_PER_HOUR_BOUNDS[0] - 0.1,
            CONTACT_RATE_PER_HOUR_BOUNDS[1] + 0.1,
            float("nan"),
            float("inf"),
            "many",
        ],
    )
    def test_a_rate_outside_the_band_is_refused(self, bad: object) -> None:
        with pytest.raises(ValueError):
            _core(_block(dict(FLAT, leisure=bad)))

    def test_the_block_requires_the_per_partner_mode(self) -> None:
        tx = dict(_block(FLAT), contact_mode="density_dependent")
        with pytest.raises(ValueError, match="per_partner_contact"):
            _core(tx)

    def test_no_rates_at_all_is_refused(self) -> None:
        with pytest.raises(ValueError, match="rates_per_hour"):
            _core({"activity_contacts": {"enabled": True}})


class TestControlIsUnchanged:
    def test_disabled_is_run_identical_to_absent(self) -> None:
        a = _rows(_core(None), _room(LOUNGE, "Free"), epochs=40)
        b = _rows(_core(_block(FLAT, enabled=False)), _room(LOUNGE, "Free"), epochs=40)
        assert a == b

    def test_the_uniform_control_still_draws_the_polymod_mean(self) -> None:
        rows = _rows(_core(None), _room(LOUNGE, "Free", n=200), epochs=240)
        draws = _draws(rows)
        assert np.mean(draws) == pytest.approx(13.4 / 24, rel=0.2)


class TestActivityResolution:
    """Resolution from state the engine already holds, one case per activity."""

    def _activity(self, core: TransmissionCore, agent: KorkinAgent, unit: str, zone: str, hallway: bool = False) -> str:
        return core._contact_activity(agent, unit, zone, hallway, epoch=1)

    def test_hallway_is_corridor(self) -> None:
        core = _core(_block(FLAT))
        a = _agent(1, "passenger", ["Sleep"] * 24, CORRIDOR)
        assert self._activity(core, a, CORRIDOR, CORRIDOR, hallway=True) == "corridor"

    def test_a_cabin_compartment_is_cabin(self) -> None:
        core = _core(_block(FLAT))
        a = _agent(1, "passenger", ["Sleep"] * 24, CORRIDOR)
        assert self._activity(core, a, CORRIDOR + "#cabin-1", CORRIDOR) == "cabin"

    def test_sleep_anywhere_is_cabin(self) -> None:
        core = _core(_block(FLAT))
        a = _agent(1, "crew", ["Sleep"] * 24, LOUNGE)
        assert self._activity(core, a, LOUNGE, LOUNGE) == "cabin"

    def test_free_is_leisure(self) -> None:
        core = _core(_block(FLAT))
        a = _agent(1, "passenger", ["Free"] * 24, LOUNGE)
        assert self._activity(core, a, LOUNGE, LOUNGE) == "leisure"

    def test_work_off_the_service_floor_is_work_other(self) -> None:
        core = _core(_block(FLAT))
        a = _agent(1, "crew", ["Work"] * 24, LOUNGE, work_zone=LOUNGE)
        assert self._activity(core, a, LOUNGE, LOUNGE) == "work_other"

    def test_a_food_employee_on_shift_is_work_service(self) -> None:
        core = _core(_block(FLAT))
        a = _agent(1, "crew", ["Work"] * 24, DINING, work_zone=DINING)
        assert self._activity(core, a, DINING, DINING) == "work_service"

    def test_a_food_employee_at_a_meal_is_a_diner(self) -> None:
        core = _core(_block(FLAT))
        a = _agent(1, "crew", ["Meal:Lunch"] * 24, DINING, work_zone=DINING)
        assert self._activity(core, a, DINING, DINING) == "dining_venue"

    def test_crew_working_in_a_dining_zone_off_food_duty_is_work_other(self) -> None:
        # The room is a Dining zone but this crew member is not a food employee
        # on shift there: the schedule says at work, so at work, not at a meal.
        core = _core(_block(FLAT))
        a = _agent(1, "crew", ["Work"] * 24, DINING, work_zone=LOUNGE)
        assert not core._on_service_duty(a, DINING, 1)
        assert self._activity(core, a, DINING, DINING) == "work_other"

    def test_the_same_work_token_resolves_by_duty_not_by_room(self) -> None:
        core = _core(_block(FLAT))
        on_duty = _agent(1, "crew", ["Work"] * 24, DINING, work_zone=DINING)
        off_duty = _agent(2, "crew", ["Work"] * 24, DINING, work_zone=LOUNGE)
        elsewhere = _agent(3, "crew", ["Work"] * 24, LOUNGE, work_zone=LOUNGE)
        assert self._activity(core, on_duty, DINING, DINING) == "work_service"
        assert self._activity(core, off_duty, DINING, DINING) == "work_other"
        assert self._activity(core, elsewhere, LOUNGE, LOUNGE) == "work_other"

    def test_the_recorded_placement_token_wins_over_the_epoch(self) -> None:
        # The engine records the token it placed the agent by; the core reads
        # that, not a token re-derived from its own epoch counter.
        core = _core(_block(FLAT))
        a = _agent(1, "passenger", ["Sleep"] * 24, DINING)
        a.current_activity = "Meal:Dinner"
        assert self._activity(core, a, DINING, DINING) == "dining_venue"
        a.current_activity = "Sleep"
        assert self._activity(core, a, DINING, DINING) == "cabin"

    def test_a_seated_party_is_dining_table(self) -> None:
        core = _core(_block(FLAT))
        a = _agent(1, "passenger", ["Meal:Lunch"] * 24, DINING)
        a.dining_party_ids = (2, 3, 4)
        assert self._activity(core, a, DINING, DINING) == "dining_table"

    def test_a_diner_without_a_party_is_dining_venue(self) -> None:
        core = _core(_block(FLAT))
        a = _agent(1, "passenger", ["Meal:Lunch"] * 24, DINING)
        assert self._activity(core, a, DINING, DINING) == "dining_venue"

    def test_a_meal_taken_outside_a_dining_zone_is_still_a_meal(self) -> None:
        core = _core(_block(FLAT))
        a = _agent(1, "passenger", ["Meal:Lunch"] * 24, LOUNGE)
        assert self._activity(core, a, LOUNGE, LOUNGE) == "dining_venue"

    def test_a_party_seated_away_from_its_venue_is_the_venue_not_the_table(self) -> None:
        core = _core(_block(FLAT))
        a = _agent(1, "passenger", ["Meal:Lunch"] * 24, LOUNGE)
        a.dining_party_ids = (2, 3, 4)
        assert self._activity(core, a, LOUNGE, LOUNGE) == "dining_venue"
        assert self._activity(core, a, DINING, DINING) == "dining_table"

    def test_an_unscheduled_hour_is_other(self) -> None:
        core = _core(_block(FLAT))
        a = _agent(1, "passenger", ["Transit"] * 24, LOUNGE)
        assert self._activity(core, a, LOUNGE, LOUNGE) == "other"

    def test_every_resolution_is_a_declared_activity(self) -> None:
        core = _core(_block(FLAT))
        cases = [
            (_agent(1, "passenger", ["Sleep"] * 24, CORRIDOR), CORRIDOR, CORRIDOR, True),
            (_agent(2, "crew", ["Work"] * 24, DINING, work_zone=DINING), DINING, DINING, False),
            (_agent(3, "passenger", ["Free"] * 24, LOUNGE), LOUNGE, LOUNGE, False),
            (_agent(4, "passenger", ["Meal:Dinner"] * 24, DINING), DINING, DINING, False),
        ]
        for agent, unit, zone, hallway in cases:
            assert self._activity(core, agent, unit, zone, hallway) in CONTACT_ACTIVITIES


class TestPlacementAndActivityAgree:
    """The token the engine places an agent by is the token the core reads.

    The core's epoch counter runs one behind the engine's, so re-deriving the
    hour from it would read the previous hour's token against this hour's
    location: a meal token in a lounge, a sleep token in the dining room.
    """

    def _engine(self) -> KorkinShipEngine:
        cfg = {"ship_graph": {
            "spatial_layout": "data/platforms/expedition_cruise_450/spatial_layout.json",
        }}
        zones = load_spatial_layout(cfg)
        assert zones is not None
        return KorkinShipEngine(
            num_passengers=60, num_crew=30, initial_infected=0,
            zones=zones, seed=11,
            clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
        )

    def test_the_recorded_token_is_the_one_that_placed_the_agent(self) -> None:
        engine = self._engine()
        dining = {z["name"] for z in engine.zones if z["type"] == "Dining"}
        core = TransmissionCore(
            rng=np.random.default_rng(0),
            zone_types={z["name"]: z["type"] for z in engine.zones},
            clock=engine.clock,
        )
        seen: set[str] = set()
        for epoch in range(48):
            engine.step()
            overridden = engine.isolated_ids | engine.quarantined_ids
            for a in engine.agents:
                if a.agent_id in overridden or a.current_location == LOCATION_ASHORE:
                    continue
                token = core._scheduled_activity(a, epoch)
                assert token == a.current_activity
                assert token in a.schedule
                seen.add(token.split(":", 1)[0])
                if token.startswith("Meal"):
                    assert a.current_location in dining
                elif token == "Work":
                    assert a.current_location == a.work_zone
                elif token == "Sleep":
                    assert a.current_location == a.home_zone
        assert {"Meal", "Work", "Sleep", "Free"} <= seen

    def test_an_unplaced_agent_falls_back_to_its_schedule(self) -> None:
        core = _core(_block(FLAT))
        a = _agent(1, "passenger", ["Sleep"] * 12 + ["Free"] * 12, LOUNGE)
        assert a.current_activity == ""
        assert core._scheduled_activity(a, 1) == "Sleep"
        assert core._scheduled_activity(a, 13) == "Free"


class TestGradedSensitivity:
    def test_the_leisure_rate_grades_the_leisure_draw(self) -> None:
        means = []
        for rate in (0.5, 2.0, 8.0):
            rows = _rows(_core(_block(dict(FLAT, leisure=rate))), _room(LOUNGE, "Free", n=100), epochs=120)
            means.append(np.mean(_draws(rows)))
        assert means == sorted(means)
        assert means[-1] > 2 * means[0]

    def test_the_declared_rate_is_the_hourly_mean(self) -> None:
        rows = _rows(_core(_block(dict(FLAT, leisure=3.0))), _room(LOUNGE, "Free", n=100), epochs=240)
        assert np.mean(_draws(rows)) == pytest.approx(3.0, rel=0.15)

    def test_a_rate_for_another_activity_does_not_reach_this_one(self) -> None:
        a = _rows(_core(_block(FLAT)), _room(LOUNGE, "Free", n=40), epochs=40)
        b = _rows(_core(_block(dict(FLAT, work_service=20.0))), _room(LOUNGE, "Free", n=40), epochs=40)
        assert a == b

    def test_a_zero_rate_draws_nothing(self) -> None:
        rates = dict(FLAT, leisure=0.0)
        rows = _rows(_core(_block(rates)), _room(LOUNGE, "Free", n=40), epochs=40)
        assert all(d == 0 for d in _draws(rows))
        assert all(r["n_contacts"] == 0 for r in rows if r["target_id"] == 0)

    def test_the_same_role_differs_by_activity(self) -> None:
        rates = dict(FLAT, leisure=6.0, cabin=0.5)
        awake = np.mean(_draws(_rows(_core(_block(rates)), _room(LOUNGE, "Free", n=60), epochs=120)))
        asleep = np.mean(_draws(_rows(_core(_block(rates)), _room(LOUNGE, "Sleep", n=60), epochs=120)))
        assert awake > asleep

    def test_roles_differ_only_where_declared(self) -> None:
        rates = dict(FLAT, leisure={"passenger": 1.0, "crew": 6.0})
        pax = np.mean(_draws(_rows(_core(_block(rates)), _room(LOUNGE, "Free", n=60, role="passenger"), epochs=120)))
        crew = np.mean(_draws(_rows(_core(_block(rates)), _room(LOUNGE, "Free", n=60, role="crew"), epochs=120)))
        assert crew > 3 * pax


class TestInvariants:
    def test_contacts_never_exceed_the_draw_or_the_pool(self) -> None:
        rows = _rows(_core(_block(dict(FLAT, leisure=12.0))), _room(LOUNGE, "Free", n=8), epochs=60)
        assert rows
        for r in rows:
            assert 0 <= r["n_contacts"] <= r["r0_draw"]
            assert r["n_contacts"] <= 7

    def test_partners_are_distinct_and_present(self) -> None:
        agents = _room(LOUNGE, "Free", n=40)
        present = {a.agent_id for a in agents}
        for r in _rows(_core(_block(FLAT)), agents, epochs=40):
            picked = r["source_ids"]
            assert len(picked) == len(set(picked))
            assert set(picked) <= present - {r["target_id"]}

    def test_doses_stay_finite_and_non_negative(self) -> None:
        rows = _rows(_core(_block(FLAT)), _room(LOUNGE, "Free", n=40), epochs=40)
        assert rows
        for r in rows:
            assert np.isfinite(r["dose"])
            assert r["dose"] >= 0.0

    def test_the_voyage_multiplier_still_scales_the_draw(self) -> None:
        base = _core(_block(FLAT))
        boosted = _core(_block(FLAT))
        boosted.voyage_contact_multiplier = 3.0
        lo = np.mean(_draws(_rows(base, _room(LOUNGE, "Free", n=100), epochs=120)))
        hi = np.mean(_draws(_rows(boosted, _room(LOUNGE, "Free", n=100), epochs=120)))
        assert hi > 2 * lo


ARM = ",".join(f"{a}={r}" for a, r in zip(
    CONTACT_ACTIVITIES, (0.3, 0.2, 3.5, 1.5, 3.0, 3.0, 2.0, 0.5), strict=True,
))


class TestTheActivityArmOfTheGate:
    """Sweep plumbing: a design carries the arm, and absent writes nothing."""

    def _design(self, text: str | None):
        from telemetry_buffer.observation_model.admissible_region import (
            Design,
            parse_activity_contacts,
        )
        return Design(
            factor_set="expedition_sensitivity",
            platform="expedition_cruise_450",
            activity_contacts=parse_activity_contacts(text),
        )

    def _spec(self, text: str | None) -> dict:
        from telemetry_buffer.observation_model.bounded_screen import (
            build_run_spec,
        )
        design = self._design(text)
        units = [0.5] * len(design.factors)
        return build_run_spec(
            design.factors, units, seed=3, description="arch_probe",
            **design.run_kwargs(),
        )

    def test_the_control_arm_is_the_pre_change_spec(self) -> None:
        assert "transmission" not in self._spec(None)["config_overrides"]
        assert "transmission" not in self._spec("")["config_overrides"]
        assert self._design(None).run_kwargs()["activity_contacts"] is None

    def test_the_arm_writes_a_complete_enabled_declaration_and_nothing_else(self) -> None:
        control = self._spec(None)
        arm = self._spec(ARM)
        overrides = dict(arm["config_overrides"])
        tx = overrides.pop("transmission")
        assert overrides == control["config_overrides"]
        assert tx["contact_mode"] == "per_partner_contact"
        assert tx["activity_contacts"]["enabled"] is True
        rates = tx["activity_contacts"]["rates_per_hour"]
        assert tuple(rates) == CONTACT_ACTIVITIES
        assert rates["work_service"] == pytest.approx(3.5)
        assert rates["other"] == pytest.approx(0.5)

    def test_the_arm_is_recorded_in_the_report_kwargs_as_json(self) -> None:
        import json
        kwargs = self._design(ARM).run_kwargs()
        assert json.loads(json.dumps(kwargs))["activity_contacts"] == dict(
            zip(CONTACT_ACTIVITIES, (0.3, 0.2, 3.5, 1.5, 3.0, 3.0, 2.0, 0.5), strict=True),
        )

    def test_distinct_arms_are_distinct_specs(self) -> None:
        arms = [
            self._spec(",".join(f"{a}={r}" for a in CONTACT_ACTIVITIES))
            for r in (0.5, 1.0, 2.0)
        ]
        assert len({repr(a["config_overrides"]) for a in arms}) == 3

    @pytest.mark.parametrize("bad", [
        "cabin=0.3",
        ARM + ",cabin=0.1",
        ARM.replace("leisure=2.0", "lounge=2.0"),
        ARM.replace("leisure=2.0", "leisure"),
        ARM.replace("leisure=2.0", "leisure=abc"),
    ])
    def test_a_partial_duplicated_or_malformed_arm_is_refused(self, bad: str) -> None:
        from telemetry_buffer.observation_model.admissible_region import (
            parse_activity_contacts,
        )
        with pytest.raises(ValueError):
            parse_activity_contacts(bad)

    def test_the_gate_cli_parses_the_arm_and_the_shard_passes_it(self) -> None:
        from pathlib import Path

        from deploy.aws.bounded_design_entrypoint import _region_argv, parse_args
        from telemetry_buffer.observation_model.admissible_region import (
            parse_args as gate_parse_args,
        )
        args = parse_args([
            "--design", "region", "--s3-prefix", "s3://b/p/",
            "--shard-count", "2", "--activity-contacts", ARM,
        ])
        argv = _region_argv(args, 0, Path("/tmp/o.json"), Path("/tmp/r.jsonl"))
        i = argv.index("--activity-contacts")
        assert argv[i + 1] == ARM
        gate = gate_parse_args(["--out", "o.json", "--activity-contacts", ARM])
        assert gate.activity_contacts == ARM

    def test_the_control_shard_sends_no_arm(self) -> None:
        from pathlib import Path

        from deploy.aws.bounded_design_entrypoint import _region_argv, parse_args
        for text in ([], ["--activity-contacts", "off"]):
            args = parse_args([
                "--design", "region", "--s3-prefix", "s3://b/p/",
                "--shard-count", "2", *text,
            ])
            argv = _region_argv(args, 0, Path("/tmp/o.json"), Path("/tmp/r.jsonl"))
            assert "--activity-contacts" not in argv

    def test_the_arm_reaches_the_engine_through_the_merged_config(self) -> None:
        from picard_framework.run_spec import merge_config_overrides
        merged = merge_config_overrides(
            {"transmission": {"contact_mode": "per_partner_contact"}},
            self._spec(ARM)["config_overrides"],
        )
        core = TransmissionCore(
            cfg={"transmission": merged["transmission"]},
            rng=np.random.default_rng(1),
        )
        assert core.activity_contacts is not None
        assert core.activity_contacts["work_service"] == {
            "passenger": pytest.approx(3.5), "crew": pytest.approx(3.5),
        }
