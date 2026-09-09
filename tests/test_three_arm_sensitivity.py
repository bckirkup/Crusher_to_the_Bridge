"""The three expedition sensitivity arms: SURF-KO-01, boarding, IMMUNE-ROLE-01.

Three arms that share nothing but a campaign. SURF-KO-01 is a diagnostic
knockout of the staff surface-touch rate, off unless asked. Boarding prevalence
is two independently swept per-person probabilities. IMMUNE-ROLE-01 is a second
immune pool for crew, absent unless declared.

What is tested is the mechanism and its scope -- which agents, which zones,
which config paths, which arm reaches which block of a run spec -- and that the
unset arm is the shipped run host for host. No test here asserts an
epidemiological outcome, and none of these arms may be set from one.
"""

from __future__ import annotations

import numpy as np
import pytest

from engines.infection_dynamics_bridge import (
    IMMUNE_RATIO,
    KorkinAgent,
    KorkinShipEngine,
    _ImmunePool,
    _ImmunityAtEmbarkation,
)
from engines.sim_clock import HOURS, SimClock
from engines.transmission_core import (
    CREW_SERVICE_SURFACE_CONTACTS_PER_HOUR,
    SURFACE_CONTACTS_PER_HOUR,
    TransmissionCore,
)
from telemetry_buffer.observation_model.admissible_region import Design
from telemetry_buffer.observation_model.bounded_screen import (
    EXPEDITION_SENSITIVITY_FACTORS,
    FACTOR_SETS,
    NOROVIRUS_FACTORS,
    build_overrides,
    build_run_overrides,
    build_run_spec,
)

GALLEY = "Main_Galley"
MESS = "CrewMess"
ENGINE = "Engine"
ZONE_TYPES = {GALLEY: "Galley", MESS: "Dining", ENGINE: "Engine"}


def _core(*, knockout: bool = False) -> TransmissionCore:
    return TransmissionCore(
        rng=np.random.default_rng(3),
        zone_types=ZONE_TYPES,
        clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
        cfg={"service_surface_knockout": {"enabled": knockout}},
    )


def _crew(work_zone: str, schedule: list[str]) -> KorkinAgent:
    return KorkinAgent(
        agent_id=1,
        role="crew",
        immune=False,
        home_zone="CC_1",
        dining_zone=MESS,
        work_zone=work_zone,
        free_zone="Lounge",
        schedule=schedule,
    )


class TestServiceSurfaceKnockoutIsOffUnlessAsked:
    def test_the_default_core_keeps_the_staff_rate_on_shift(self) -> None:
        core = _core()
        agent = _crew(GALLEY, ["Work"] * 24)
        assert core._fomite_surface_contacts(
            GALLEY, agent, 0,
        ) == pytest.approx(CREW_SERVICE_SURFACE_CONTACTS_PER_HOUR)

    def test_an_absent_block_is_the_default(self) -> None:
        bare = TransmissionCore(
            rng=np.random.default_rng(3),
            zone_types=ZONE_TYPES,
            clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
        )
        assert bare.service_surface_knockout is False

    @pytest.mark.parametrize("block", [{"enabled": "yes"}, [], {"enabled": 1}])
    def test_a_non_boolean_arm_is_refused(self, block: object) -> None:
        with pytest.raises(ValueError, match="service_surface_knockout"):
            TransmissionCore(
                rng=np.random.default_rng(3),
                zone_types=ZONE_TYPES,
                clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
                cfg={"service_surface_knockout": block},
            )


class TestTheKnockoutSubstitutesTheDinerRate:
    def test_a_worker_on_shift_takes_the_diner_rate(self) -> None:
        core = _core(knockout=True)
        agent = _crew(GALLEY, ["Work"] * 24)
        assert core._fomite_surface_contacts(
            GALLEY, agent, 0,
        ) == pytest.approx(SURFACE_CONTACTS_PER_HOUR["dining"])

    def test_it_is_not_the_zone_class_rate_the_galley_would_give(self) -> None:
        # The knockout is a substitution, not a bypass: a galley worker whose
        # staff rate is removed must not fall back on the galley's own 545.4.
        assert SURFACE_CONTACTS_PER_HOUR["galley"] != pytest.approx(
            SURFACE_CONTACTS_PER_HOUR["dining"],
        )
        core = _core(knockout=True)
        agent = _crew(GALLEY, ["Work"] * 24)
        assert core._fomite_surface_contacts(GALLEY, agent, 0) < (
            SURFACE_CONTACTS_PER_HOUR["galley"]
        )

    def test_the_staff_constant_itself_is_untouched(self) -> None:
        _core(knockout=True)
        assert CREW_SERVICE_SURFACE_CONTACTS_PER_HOUR == pytest.approx(545.4)


class TestTheKnockoutScope:
    def test_the_same_worker_off_shift_is_unaffected(self) -> None:
        agent = _crew(GALLEY, ["MealLunch"] * 24)
        assert _core(knockout=True)._fomite_surface_contacts(
            MESS, agent, 0,
        ) == _core()._fomite_surface_contacts(MESS, agent, 0)

    def test_a_worker_in_an_unrelated_zone_is_unaffected(self) -> None:
        agent = _crew(ENGINE, ["Work"] * 24)
        assert _core(knockout=True)._fomite_surface_contacts(
            ENGINE, agent, 0,
        ) == _core()._fomite_surface_contacts(ENGINE, agent, 0)

    def test_an_occupantless_zone_touch_is_unaffected(self) -> None:
        assert _core(knockout=True)._fomite_surface_contacts(
            GALLEY, None, 0,
        ) == _core()._fomite_surface_contacts(GALLEY, None, 0)

    def test_the_duty_predicate_is_unchanged_by_the_arm(self) -> None:
        agent = _crew(GALLEY, ["Work"] * 24)
        assert _core(knockout=True)._on_service_duty(agent, GALLEY, 0)
        assert _core()._on_service_duty(agent, GALLEY, 0)


class TestImmunePoolDeliversItsShareExactly:
    @pytest.mark.parametrize("fraction", [0.0, 0.2, 0.5, 1.0])
    def test_the_count_drawn_is_the_declared_count(self, fraction: float) -> None:
        hosts = 200
        pool = _ImmunePool(int(hosts * fraction), hosts)
        rng = np.random.default_rng(11)
        drawn = sum(pool.draw(rng) for _ in range(hosts))
        assert drawn == int(hosts * fraction)

    def test_a_drained_pool_offers_nothing_further(self) -> None:
        pool = _ImmunePool(1, 1)
        rng = np.random.default_rng(2)
        assert pool.draw(rng) is True
        assert pool.draw(rng) is False


class TestImmunityIsRoleBlindUnlessCrewIsDeclared:
    def test_one_pool_serves_a_role_it_has_no_pool_for(self) -> None:
        immunity = _ImmunityAtEmbarkation.role_blind(10, 0.5)
        rng = np.random.default_rng(5)
        drawn = sum(immunity.draw("crew", rng) for _ in range(10))
        assert drawn == 5

    def test_a_role_stratified_immunity_refuses_an_unknown_role(self) -> None:
        immunity = _ImmunityAtEmbarkation.by_role(
            passengers=4, crew=4, passenger_fraction=0.5, crew_fraction=0.5,
        )
        with pytest.raises(ValueError, match="no pool for role"):
            immunity.draw("stowaway", np.random.default_rng(1))

    def test_each_role_gets_its_own_declared_share(self) -> None:
        immunity = _ImmunityAtEmbarkation.by_role(
            passengers=100, crew=50, passenger_fraction=0.1, crew_fraction=0.8,
        )
        rng = np.random.default_rng(7)
        assert sum(immunity.draw("passenger", rng) for _ in range(100)) == 10
        assert sum(immunity.draw("crew", rng) for _ in range(50)) == 40


def _engine(**kwargs: object) -> KorkinShipEngine:
    return KorkinShipEngine(
        num_passengers=60,
        num_crew=40,
        initial_infected=0,
        seed=42,
        **kwargs,
    )


def _immune_by_role(engine: KorkinShipEngine) -> dict[str, int]:
    counts = {"passenger": 0, "crew": 0}
    for agent in engine.agents:
        if agent.immune:
            counts[agent.role] += 1
    return counts


class TestCrewImmunityIsASensitivityAxis:
    def test_unset_leaves_the_shipped_role_blind_complement(self) -> None:
        engine = _engine()
        assert engine.crew_immune_ratio is None
        counts = _immune_by_role(engine)
        assert sum(counts.values()) == int(100 * IMMUNE_RATIO)

    def test_the_crew_share_moves_with_the_axis_and_passengers_do_not(
        self,
    ) -> None:
        seen = {}
        for fraction in (0.0, 0.25, 0.5, 1.0):
            counts = _immune_by_role(_engine(crew_immune_ratio=fraction))
            seen[fraction] = counts
            assert counts["crew"] == int(40 * fraction)
            assert counts["passenger"] == int(60 * IMMUNE_RATIO)
        crew = [seen[f]["crew"] for f in sorted(seen)]
        assert crew == sorted(crew)
        assert len(set(crew)) == len(crew)

    def test_the_same_declared_axis_replays_identically(self) -> None:
        first = _immune_by_role(_engine(crew_immune_ratio=0.3))
        second = _immune_by_role(_engine(crew_immune_ratio=0.3))
        assert first == second

    @pytest.mark.parametrize("bad", [-0.1, 1.5, float("nan"), float("inf")])
    def test_a_fraction_outside_zero_one_is_refused(self, bad: float) -> None:
        with pytest.raises(ValueError, match="crew_immune_ratio"):
            _engine(crew_immune_ratio=bad)


UNITS = tuple([0.5] * len(FACTOR_SETS["expedition_sensitivity"]))


def _factor(name: str):
    return next(
        factor
        for factor in FACTOR_SETS["expedition_sensitivity"]
        if factor.name == name
    )


class TestTheSensitivityBoxIsTheBiologyBoxPlusThreeAxes:
    def test_the_biology_box_is_a_prefix_of_the_sensitivity_box(self) -> None:
        wide = FACTOR_SETS["expedition_sensitivity"]
        assert wide[: len(NOROVIRUS_FACTORS)] == NOROVIRUS_FACTORS
        assert wide[len(NOROVIRUS_FACTORS):] == EXPEDITION_SENSITIVITY_FACTORS

    @pytest.mark.parametrize(
        ("name", "low", "high"),
        [
            ("boarding_prevalence_passenger", 0.025, 0.040),
            ("boarding_prevalence_crew", 0.007, 0.030),
            ("crew_immune_fraction", 0.0, 1.0),
        ],
    )
    def test_each_axis_spans_its_sourced_interval(
        self, name: str, low: float, high: float,
    ) -> None:
        factor = _factor(name)
        assert factor.value(0.0) == pytest.approx(low)
        assert factor.value(1.0) == pytest.approx(high)

    def test_the_two_boarding_axes_are_separate_probabilities(self) -> None:
        passenger = _factor("boarding_prevalence_passenger")
        crew = _factor("boarding_prevalence_crew")
        assert passenger.path != crew.path
        assert passenger.path[:2] == crew.path[:2] == ("boarding", "prevalence")

    def test_a_run_target_axis_stays_out_of_the_pathogen_profile(self) -> None:
        factors = FACTOR_SETS["expedition_sensitivity"]
        profile = build_overrides(factors, UNITS, "norwalk_gi")["norwalk_gi"]
        assert "crew_immune_fraction" not in str(profile)
        assert profile["boarding"]["prevalence"]["passenger"] > 0
        assert profile["boarding"]["prevalence"]["crew"] > 0

    def test_a_run_target_axis_lands_in_the_run_block(self) -> None:
        factors = FACTOR_SETS["expedition_sensitivity"]
        run = build_run_overrides(factors, UNITS)
        assert set(run) == {"ship_graph"}
        assert run["ship_graph"]["crew_immune_fraction"] == pytest.approx(0.5)

    def test_the_biology_box_writes_no_run_block_at_all(self) -> None:
        units = [0.5] * len(NOROVIRUS_FACTORS)
        assert build_run_overrides(NOROVIRUS_FACTORS, units) == {}


class TestTheRunSpecCarriesEachArmOnce:
    def _spec(self, **design_fields: object) -> dict:
        design = Design(
            factor_set="expedition_sensitivity",
            platform="expedition_cruise_450",
            **design_fields,
        )
        return build_run_spec(
            design.factors,
            UNITS,
            seed=1,
            description="three_arm_probe",
            **design.run_kwargs(),
        )

    def test_the_immunity_axis_does_not_displace_the_complement(self) -> None:
        graph = self._spec()["config_overrides"]["ship_graph"]
        assert graph["num_agents"] == Design(
            platform="expedition_cruise_450",
        ).complement
        assert graph["crew_immune_fraction"] == pytest.approx(0.5)

    def test_the_knockout_is_absent_unless_the_run_asks(self) -> None:
        assert "service_surface_knockout" not in self._spec()["config_overrides"]

    def test_the_knockout_is_written_as_an_enabled_block(self) -> None:
        spec = self._spec(service_surface_knockout=True)
        assert spec["config_overrides"]["service_surface_knockout"] == {
            "enabled": True,
        }


class TestADesignNamesItsOwnBox:
    def test_the_default_design_samples_the_biology_box(self) -> None:
        assert Design().factors == NOROVIRUS_FACTORS

    def test_a_sensitivity_design_samples_the_wider_box(self) -> None:
        design = Design(factor_set="expedition_sensitivity")
        assert design.factors == FACTOR_SETS["expedition_sensitivity"]

    def test_the_box_is_not_a_run_argument(self) -> None:
        # A shard resolves its factors from the design it was handed; the
        # factor set must not leak into the spec's run keyword arguments,
        # where build_run_spec would refuse it.
        assert "factor_set" not in Design(
            factor_set="expedition_sensitivity",
        ).run_kwargs()

    def test_both_diagnostic_arms_reach_the_run_keywords(self) -> None:
        kwargs = Design(
            service_surface_knockout=True, crew_duty_exclusion=True,
        ).run_kwargs()
        assert kwargs["service_surface_knockout"] is True
        assert kwargs["crew_duty_exclusion"] is True
