"""Initiation: a boarding prevalence, explicit seeds, and a legacy default.


Sensitivity and invariants rather than goldens: each configured coordinate is
asserted to move the one thing it owns and to leave the others where they
were, every drawn infection age is asserted to lie inside the window its state
defines, and the length-bias claim of the spec's §4 is asserted directly
against the chronic share of the population the cohort is drawn from.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from engines.infection_dynamics_bridge import (
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
)
from engines.initiation import (
    MODE_BOARDING,
    MODE_BOARDING_AND_SEEDS,
    MODE_LEGACY,
    MODE_SEEDS,
    STATE_CONVALESCENT,
    STATE_INCUBATING,
    STATE_NEVER_SYMPTOMATIC,
    STATE_PRESYMPTOMATIC,
    BoardingParty,
    BoardingSpec,
    build_initiation_manifest,
    draw_boarding_cohort,
    resolve_initiation_plan,
)
from engines.natural_history import (
    draw_symptom_onset,
)
from engines.sim_clock import HOURS, SimClock
from orchestrator_epoch import (
    step_mid_cruise_introductions,
)
from orchestrator_init import (
    _run_initiation,
    _seed_legacy_infections,
    init_multi_pathogen,
)

PATHOGEN = "norwalk_gi"
OTHER_PATHOGEN = "sars_cov2_resp"
ZONE = "Cabin_A"
ONSET_DAYS = 1.0
RECOVERY_DAYS = 3
SHEDDING_DAYS = 15.0
PRESYMPTOMATIC_DAYS = 0.5
CHRONIC_FRACTION = 0.228
IMMUNOCOMPROMISED_FRACTION = 0.05
CHRONIC_SPEC = {
    "median": 218.0, "min": 32.0, "max": 1164.0, "sigma_log": 1.09,
}
PASSENGERS = 200
CREW = 100
SEEDS = range(12)


def _clock() -> SimClock:
    return SimClock(epoch_duration_hours=6.0, mode=HOURS)


def _agent(agent_id: int, role: str) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=agent_id,
        role=role,
        immune=False,
        home_zone=ZONE,
        dining_zone=ZONE,
        work_zone=ZONE,
        free_zone=ZONE,
        schedule=["Free"] * 4,
    )
    agent.clock = _clock()
    agent.current_location = ZONE
    return agent


class _FakeEngine:
    """Minimal engine surface used by the initiation entry points."""

    def __init__(
        self, passengers: int = PASSENGERS, crew: int = CREW,
    ) -> None:
        self.agents = [_agent(index, "passenger") for index in range(passengers)]
        self.agents += [
            _agent(passengers + index, "crew") for index in range(crew)
        ]
        self.clock = _clock()
        self.initiation_manifest: dict[str, Any] = {"mode": MODE_LEGACY}

    def initialize_pathogen(self, _pid: str) -> None:
        return None


def _profile(**overrides: Any) -> dict[str, Any]:
    """A boarding-eligible profile: no fiat index case, full clocks."""
    profile: dict[str, Any] = {
        "base_susceptibility": 1.0,
        "introduction_epoch": 0,
        "symptom_onset_day": ONSET_DAYS,
        "recovery_day": RECOVERY_DAYS,
        "shedding_duration_days": SHEDDING_DAYS,
        "presymptomatic_shedding_days": PRESYMPTOMATIC_DAYS,
        "illness_probability": {"eta": 0.508, "gamma": 0.095},
        "severity_model": {
            "states": [
                "asymptomatic", "subclinical", "mild", "moderate",
                "severe_critical",
            ],
            "base_probabilities": [0.25, 0.55, 0.19, 0.009, 0.001],
        },
        "chronic_shedder_fraction": CHRONIC_FRACTION,
        "chronic_shedding_duration_days": dict(CHRONIC_SPEC),
    }
    profile.update(overrides)
    return profile


def _spec(
    passenger: float = 0.05,
    crew: float = 0.05,
    never: float = 0.20,
    pre_share: float = 0.04,
) -> BoardingSpec:
    return BoardingSpec(
        pathogen_id=PATHOGEN,
        passenger_prevalence=passenger,
        crew_prevalence=crew,
        never_symptomatic_fraction=never,
        presymptomatic_share_of_presenting=pre_share,
    )


def _cfg(**boarding: Any) -> dict[str, Any]:
    block: dict[str, Any] = {"enabled": True}
    block[PATHOGEN] = {
        "prevalence": {
            "passenger": boarding.get("passenger", 0.05),
            "crew": boarding.get("crew", 0.05),
        },
        "state_split": {
            "never_symptomatic_fraction": boarding.get("never", 0.2),
            "presymptomatic_share_of_presenting": boarding.get("pre", 0.04),
        },
    }
    return {
        "initiation": {"boarding": block},
        "multi_pathogen": {"immunocompromised_fraction": 0.05},
    }


def _draw(spec: BoardingSpec, seed: int, **profile_overrides: Any):
    engine = _FakeEngine()
    profile = _profile(**profile_overrides)
    report = draw_boarding_cohort(
        spec, engine.agents, profile, engine.clock,
        np.random.default_rng(seed),
    )
    return engine, profile, report


def _mean_counts(spec: BoardingSpec) -> dict[str, float]:
    totals = {"passenger": 0.0, "crew": 0.0}
    for seed in SEEDS:
        _, _, report = _draw(spec, seed)
        for role, count in report.drawn_by_role.items():
            totals[role] += count
    return {role: total / len(SEEDS) for role, total in totals.items()}


def _mean_composition(spec: BoardingSpec) -> dict[str, float]:
    totals: dict[str, float] = {}
    for seed in SEEDS:
        _, _, report = _draw(spec, seed)
        for state, count in report.composition.items():
            totals[state] = totals.get(state, 0.0) + count
    drawn = sum(totals.values())
    return {state: count / drawn for state, count in totals.items()}


def _stamp_chronic(engine: _FakeEngine, rng: np.random.Generator) -> int:
    """Emulate initialization: chronic durations on immunocompromised hosts.

    ``chronic_shedder_fraction`` is a share of immunocompromised hosts, so the
    population's chronic share is the product of the two fractions and not the
    profile field on its own.
    """
    stamped = 0
    for agent in engine.agents:
        immunocompromised = rng.random() < IMMUNOCOMPROMISED_FRACTION
        if immunocompromised and rng.random() < CHRONIC_FRACTION:
            agent.set_chronic_shedding_duration(
                PATHOGEN, float(CHRONIC_SPEC["median"]),
            )
            stamped += 1
    return stamped


def _infected_ids(engine: _FakeEngine) -> set[int]:
    return {
        agent.agent_id for agent in engine.agents
        if PATHOGEN in agent.infections
    }


class TestSensitivity:
    def test_passenger_prevalence_moves_the_passenger_count(self) -> None:
        means = [
            _mean_counts(_spec(passenger=prevalence))["passenger"]
            for prevalence in (0.02, 0.10, 0.30)
        ]
        assert means[0] < means[1] < means[2]
        # A factor-of-fifteen prevalence range must move the count by more
        # than sampling noise on 200 passengers.
        assert means[2] > 2.5 * means[1]
        assert means[1] > 3.0 * means[0]

    def test_passenger_prevalence_leaves_the_crew_count(self) -> None:
        # Negative control: the crew draw runs against its own pool at its own
        # rate, so 100 crew at 0.05 stay near five however many passengers
        # board infected.
        for prevalence in (0.02, 0.10, 0.30):
            crew_mean = _mean_counts(_spec(passenger=prevalence))["crew"]
            assert 2.5 < crew_mean < 7.5

    def test_crew_prevalence_moves_the_crew_count(self) -> None:
        means = [
            _mean_counts(_spec(crew=prevalence))["crew"]
            for prevalence in (0.02, 0.10, 0.30)
        ]
        assert means[0] < means[1] < means[2]
        assert means[2] > 2.5 * means[1]
        assert means[1] > 3.0 * means[0]

    def test_crew_prevalence_leaves_the_passenger_count(self) -> None:
        for prevalence in (0.02, 0.10, 0.30):
            passenger_mean = _mean_counts(_spec(crew=prevalence))["passenger"]
            assert 6.0 < passenger_mean < 14.0

    def test_never_symptomatic_fraction_moves_its_own_share(self) -> None:
        shares = [
            _mean_composition(
                _spec(passenger=0.4, crew=0.4, never=never),
            )[STATE_NEVER_SYMPTOMATIC]
            for never in (0.1, 0.4, 0.8)
        ]
        assert shares[0] < shares[1] < shares[2]
        assert shares[2] - shares[0] > 0.4

    def test_never_symptomatic_fraction_owns_only_that_share(self) -> None:
        # The presenting states shrink together: their split is the other
        # coordinate's business.
        ratios = []
        for never in (0.1, 0.4, 0.8):
            composition = _mean_composition(
                _spec(passenger=0.4, crew=0.4, never=never, pre_share=0.3),
            )
            presenting = (
                composition[STATE_PRESYMPTOMATIC]
                + composition[STATE_CONVALESCENT]
            )
            ratios.append(composition[STATE_PRESYMPTOMATIC] / presenting)
        assert max(ratios) - min(ratios) < 0.1

    def test_presymptomatic_share_moves_the_presymptomatic_share(self) -> None:
        shares = [
            _mean_composition(
                _spec(passenger=0.4, crew=0.4, pre_share=share),
            )[STATE_PRESYMPTOMATIC]
            for share in (0.05, 0.3, 0.7)
        ]
        assert shares[0] < shares[1] < shares[2]
        assert shares[2] - shares[0] > 0.3

    def test_presymptomatic_share_leaves_the_never_share(self) -> None:
        shares = [
            _mean_composition(
                _spec(passenger=0.4, crew=0.4, pre_share=share),
            )[STATE_NEVER_SYMPTOMATIC]
            for share in (0.05, 0.3, 0.7)
        ]
        assert max(shares) - min(shares) < 0.1


class TestLengthBias:
    def test_chronic_share_among_boarders_exceeds_the_population_share(
        self,
    ) -> None:
        """The §4 claim: a prevalent sample over-represents long episodes.

        The comparison is against the chronic share of the *population*,
        which is ``immunocompromised_fraction`` times
        ``chronic_shedder_fraction``, since the profile field is a share of
        immunocompromised hosts. A 218-day episode occupies about fifteen
        times as much of the prevalent pool as a 15-day one, so the share
        among boarders is higher; the band is broad because the prediction is
        a consequence of the weighting, not a golden.
        """
        chronic = 0
        boarders = 0
        population_chronic = 0
        population = 0
        for seed in range(60):
            engine = _FakeEngine()
            rng = np.random.default_rng(1000 + seed)
            population_chronic += _stamp_chronic(engine, rng)
            population += len(engine.agents)
            draw_boarding_cohort(
                _spec(passenger=0.02, crew=0.02), engine.agents,
                _profile(), engine.clock, rng,
            )
            for agent in engine.agents:
                infection = agent.infections.get(PATHOGEN)
                if infection is None:
                    continue
                boarders += 1
                if infection["shedding_duration_days"] > SHEDDING_DAYS:
                    chronic += 1
        population_share = population_chronic / population
        boarder_share = chronic / boarders
        assert boarders > 200
        assert boarder_share > population_share
        assert boarder_share > 0.05
        assert boarder_share < 0.35

    def test_no_boarding_host_is_given_a_re_drawn_duration(self) -> None:
        """Duration is a host property: unstamped hosts carry the profile's."""
        engine = _FakeEngine()
        rng = np.random.default_rng(77)
        stamped = {
            agent.agent_id for agent in engine.agents
            if agent.get_chronic_shedding_duration(PATHOGEN) is not None
        }
        assert stamped == set()
        draw_boarding_cohort(
            _spec(passenger=0.3, crew=0.3), engine.agents, _profile(),
            engine.clock, rng,
        )
        durations = [
            agent.infections[PATHOGEN]["shedding_duration_days"]
            for agent in engine.agents if PATHOGEN in agent.infections
        ]
        assert durations
        assert durations == pytest.approx([SHEDDING_DAYS] * len(durations))

    def test_a_profile_without_chronic_keys_boards_one_duration(self) -> None:
        engine, _, _ = _draw(
            _spec(passenger=0.5, crew=0.5), 3,
            chronic_shedder_fraction=None,
            chronic_shedding_duration_days=None,
        )
        durations = [
            agent.infections[PATHOGEN]["shedding_duration_days"]
            for agent in engine.agents
            if PATHOGEN in agent.infections
        ]
        assert durations
        assert durations == pytest.approx([SHEDDING_DAYS] * len(durations))


class TestInvariants:
    def test_every_age_lies_inside_its_state_window(self) -> None:
        clock = _clock()
        tolerance = 0.5 / clock.epochs_per_day
        checked = 0
        for seed in SEEDS:
            engine, profile, _ = _draw(_spec(passenger=0.4, crew=0.4), seed)
            for agent in engine.agents:
                infection = agent.infections.get(PATHOGEN)
                if infection is None:
                    continue
                checked += 1
                low, high = _expected_window(agent, infection, profile)
                age_days = (
                    infection["time_infected"] / clock.epochs_per_day
                )
                assert age_days >= low - tolerance
                assert age_days <= high + tolerance
        assert checked > 100

    def test_no_boarding_host_is_symptomatic_at_epoch_zero(self) -> None:
        for seed in SEEDS:
            engine, _, _ = _draw(_spec(passenger=0.4, crew=0.4), seed)
            for agent in engine.agents:
                assert agent.illness_status != IllnessStatus.SYMPTOMATIC
                infection = agent.infections.get(PATHOGEN)
                if infection is not None:
                    assert infection["illness"] != IllnessStatus.SYMPTOMATIC

    def test_boarding_hosts_carry_no_acquisition_dose(self) -> None:
        engine, _, _ = _draw(_spec(passenger=0.4, crew=0.4), 5)
        doses = [
            agent.infections[PATHOGEN]["acquired_particles"]
            for agent in engine.agents
            if PATHOGEN in agent.infections
        ]
        assert doses
        assert doses == pytest.approx([0.0] * len(doses))

    def test_realised_composition_sums_to_the_drawn_count(self) -> None:
        _, _, report = _draw(_spec(passenger=0.4, crew=0.4), 9)
        assert sum(report.composition.values()) == sum(
            report.drawn_by_role.values(),
        )

    def test_gate_off_consumes_no_draws_from_the_parent_stream(self) -> None:
        """A disabled gate takes exactly the draws the legacy path takes.

        The comparison is against a legacy run on the same seed rather than
        against an untouched stream: a disabled block owns no pathogen, and
        owning none is not a reason to drop the profile's own index case. So
        the parent stream has to land in the same place and the same hosts
        have to be seeded.
        """
        cfg = {"initiation": {"boarding": {"enabled": False}}}
        gated_engine = _FakeEngine()
        gated_rng = np.random.default_rng(7)
        _run_initiation(
            gated_engine, {PATHOGEN: _profile()}, cfg,
            resolve_initiation_plan(cfg, {PATHOGEN: _profile()}), gated_rng,
        )
        legacy_engine = _FakeEngine()
        legacy_rng = np.random.default_rng(7)
        _seed_legacy_infections(
            legacy_engine, {PATHOGEN: _profile()}, legacy_rng,
        )
        gated = _infected_ids(gated_engine)
        assert gated_rng.random() == pytest.approx(legacy_rng.random())
        assert gated == _infected_ids(legacy_engine)
        assert gated

    def test_enabling_boarding_leaves_the_earlier_streams_in_place(
        self,
    ) -> None:
        """The boarding stream is spawned third, so it rebases neither sibling."""
        legacy_engine, legacy_ids = _init_run({"multi_pathogen": {}})
        boarding_engine, boarding_ids = _init_run(_cfg())
        assert legacy_ids == boarding_ids
        assert [
            agent.secretor_negative_by_pathogen[PATHOGEN]
            for agent in legacy_engine.agents
        ] == [
            agent.secretor_negative_by_pathogen[PATHOGEN]
            for agent in boarding_engine.agents
        ]


def _expected_window(
    agent: KorkinAgent, infection: dict[str, Any], profile: dict[str, Any],
) -> tuple[float, float]:
    incubation = float(infection["incubation_days"])
    duration = float(infection["shedding_duration_days"])
    recovery = float(agent.get_chronic_recovery_day(
        PATHOGEN, int(profile["recovery_day"]),
    ))
    state = infection["boarding_state"]
    if state == STATE_PRESYMPTOMATIC:
        return max(0.0, incubation - PRESYMPTOMATIC_DAYS), incubation
    if state == STATE_CONVALESCENT:
        return incubation + recovery, incubation + duration
    return max(0.0, incubation - PRESYMPTOMATIC_DAYS), incubation + duration


def _init_run(cfg: dict[str, Any]) -> tuple[_FakeEngine, set[int]]:
    engine = _FakeEngine()
    profile = _profile(secretor_negative_fraction=0.2,
                       secretor_negative_relative_susceptibility=0.2)
    ids = init_multi_pathogen(
        engine, {PATHOGEN: profile}, cfg, np.random.default_rng(21),
    )
    return engine, ids


class TestEpochSeam:
    def test_a_presymptomatic_import_presents_without_a_dose(self) -> None:
        agent = _agent(1, "passenger")
        agent.infect_with_pathogen(PATHOGEN, 0.0, 0, time_infected=2)
        infection = agent.infections[PATHOGEN]
        infection["will_present"] = True
        draw_symptom_onset(
            agent, PATHOGEN, infection, _profile(), np.random.default_rng(1),
        )
        assert infection["illness"] == IllnessStatus.SYMPTOMATIC
        assert infection["presented"] is True

    def test_a_never_symptomatic_import_never_presents(self) -> None:
        agent = _agent(2, "passenger")
        agent.infect_with_pathogen(PATHOGEN, 0.0, 0, time_infected=2)
        infection = agent.infections[PATHOGEN]
        infection["will_present"] = False
        draw_symptom_onset(
            agent, PATHOGEN, infection, _profile(), np.random.default_rng(1),
        )
        assert infection["illness"] == IllnessStatus.NOT_ILL
        assert infection["symptom_severity"] == "asymptomatic"

    def test_an_acquired_infection_still_reads_its_dose(self) -> None:
        agent = _agent(3, "passenger")
        agent.infect_with_pathogen(PATHOGEN, 1e6, 0, time_infected=2)
        infection = agent.infections[PATHOGEN]
        draw_symptom_onset(
            agent, PATHOGEN, infection, _profile(), np.random.default_rng(0),
        )
        assert "will_present" not in infection


class TestExplicitSeeds:
    def test_a_dose_free_seed_presents_by_construction(self) -> None:
        engine, records = _seed_run(
            [{"pathogen": PATHOGEN, "count": 3, "role": None, "epoch": 0}],
        )
        assert records[0]["seeded"] == 3
        infected = [a for a in engine.agents if PATHOGEN in a.infections]
        assert len(infected) == 3
        for agent in infected:
            infection = agent.infections[PATHOGEN]
            assert infection["will_present"] is True
            assert infection["acquired_particles"] == pytest.approx(0.0)

    def test_a_stated_dose_leaves_presentation_to_the_dose(self) -> None:
        engine, _ = _seed_run(
            [{"pathogen": PATHOGEN, "count": 2, "dose": 1e5, "epoch": 0}],
        )
        for agent in engine.agents:
            infection = agent.infections.get(PATHOGEN)
            if infection is not None:
                assert "will_present" not in infection
                assert infection["acquired_particles"] == pytest.approx(1e5)

    def test_a_role_restricted_seed_only_touches_that_role(self) -> None:
        engine, _ = _seed_run(
            [{"pathogen": PATHOGEN, "count": 5, "role": "crew", "epoch": 0}],
        )
        roles = {
            agent.role for agent in engine.agents
            if PATHOGEN in agent.infections
        }
        assert roles == {"crew"}

    def test_a_later_epoch_seed_waits_for_its_epoch(self) -> None:
        engine, records = _seed_run(
            [{"pathogen": PATHOGEN, "count": 4, "epoch": 5}],
        )
        assert records == []
        assert not any(PATHOGEN in a.infections for a in engine.agents)

    def test_an_infection_age_lands_on_the_clock(self) -> None:
        engine, _ = _seed_run(
            [{
                "pathogen": PATHOGEN, "count": 1, "epoch": 0,
                "infection_age_days": 2.0,
            }],
        )
        ages = [
            agent.infections[PATHOGEN]["time_infected"]
            for agent in engine.agents if PATHOGEN in agent.infections
        ]
        assert ages == [int(round(_clock().epochs_for_days(2.0)))]


def _seed_run(
    seeds: list[dict[str, Any]],
) -> tuple[_FakeEngine, list[dict[str, Any]]]:
    from engines.initiation import apply_explicit_seeds

    engine = _FakeEngine()
    profiles = {PATHOGEN: _profile()}
    plan = resolve_initiation_plan({"initiation": {"explicit_seeds": seeds}},
                                   profiles)
    records = apply_explicit_seeds(
        plan, engine, 0, np.random.default_rng(4), profiles,
    )
    return engine, records


class TestPlanResolution:
    def test_no_initiation_key_is_the_legacy_plan(self) -> None:
        plan = resolve_initiation_plan({}, {PATHOGEN: _profile()})
        assert plan.legacy is True
        assert plan.boarding == ()
        assert plan.seeds == ()

    def test_a_disabled_gate_still_honours_explicit_seeds(self) -> None:
        plan = resolve_initiation_plan(
            {
                "initiation": {
                    "boarding": {"enabled": False},
                    "explicit_seeds": [{"pathogen": PATHOGEN, "count": 2}],
                },
            },
            {PATHOGEN: _profile()},
        )
        assert plan.legacy is False
        assert plan.boarding == ()
        assert len(plan.seeds) == 1

    def test_boarding_and_a_fiat_index_case_is_an_error(self) -> None:
        with pytest.raises(ValueError, match="initial_infected"):
            resolve_initiation_plan(
                _cfg(), {PATHOGEN: _profile(initial_infected=1)},
            )

    def test_a_seed_over_a_fiat_index_case_is_an_error(self) -> None:
        with pytest.raises(ValueError, match="initial_infected"):
            resolve_initiation_plan(
                {
                    "initiation": {
                        "explicit_seeds": [{"pathogen": PATHOGEN, "count": 2}],
                    },
                },
                {PATHOGEN: _profile(initial_infected=1)},
            )

    def test_a_seed_leaves_another_pathogens_index_case_alone(self) -> None:
        plan = resolve_initiation_plan(
            {
                "initiation": {
                    "explicit_seeds": [{"pathogen": PATHOGEN, "count": 2}],
                },
            },
            {
                PATHOGEN: _profile(),
                OTHER_PATHOGEN: _profile(initial_infected=3),
            },
        )
        assert len(plan.seeds) == 1

    def test_an_unset_never_symptomatic_fraction_is_an_error(self) -> None:
        cfg = _cfg()
        cfg["initiation"]["boarding"][PATHOGEN]["state_split"][
            "never_symptomatic_fraction"
        ] = None
        with pytest.raises(ValueError, match="never_symptomatic_fraction"):
            resolve_initiation_plan(cfg, {PATHOGEN: _profile()})

    def test_a_missing_state_split_is_an_error(self) -> None:
        cfg = _cfg()
        del cfg["initiation"]["boarding"][PATHOGEN]["state_split"]
        with pytest.raises(ValueError, match="never_symptomatic_fraction"):
            resolve_initiation_plan(cfg, {PATHOGEN: _profile()})

    @pytest.mark.parametrize("prevalence", [-0.1, 1.4])
    def test_a_prevalence_outside_the_unit_interval_is_an_error(
        self, prevalence: float,
    ) -> None:
        with pytest.raises(ValueError, match=r"outside \[0, 1\]"):
            resolve_initiation_plan(
                _cfg(passenger=prevalence), {PATHOGEN: _profile()},
            )

    @pytest.mark.parametrize("share", [-0.1, 1.4])
    def test_a_split_coordinate_outside_the_unit_interval_is_an_error(
        self, share: float,
    ) -> None:
        with pytest.raises(ValueError, match=r"outside \[0, 1\]"):
            resolve_initiation_plan(
                _cfg(pre=share), {PATHOGEN: _profile()},
            )

    def test_an_unknown_boarding_pathogen_is_an_error(self) -> None:
        with pytest.raises(ValueError, match="absent from the loaded profiles"):
            resolve_initiation_plan(_cfg(), {"other": _profile()})

    def test_an_unknown_seed_pathogen_is_an_error(self) -> None:
        with pytest.raises(ValueError, match="absent from the loaded profiles"):
            resolve_initiation_plan(
                {"initiation": {"explicit_seeds": [{"pathogen": "nope"}]}},
                {PATHOGEN: _profile()},
            )

    def test_a_negative_seed_count_is_an_error(self) -> None:
        with pytest.raises(ValueError, match="count"):
            resolve_initiation_plan(
                {
                    "initiation": {
                        "explicit_seeds": [
                            {"pathogen": PATHOGEN, "count": -2},
                        ],
                    },
                },
                {PATHOGEN: _profile()},
            )

    def test_a_negative_infection_age_is_an_error(self) -> None:
        with pytest.raises(ValueError, match="infection_age_days"):
            resolve_initiation_plan(
                {
                    "initiation": {
                        "explicit_seeds": [
                            {"pathogen": PATHOGEN, "infection_age_days": -1.0},
                        ],
                    },
                },
                {PATHOGEN: _profile()},
            )

    def test_an_unknown_seed_role_is_an_error(self) -> None:
        with pytest.raises(ValueError, match="role"):
            resolve_initiation_plan(
                {
                    "initiation": {
                        "explicit_seeds": [
                            {"pathogen": PATHOGEN, "role": "officer"},
                        ],
                    },
                },
                {PATHOGEN: _profile()},
            )


class TestManifest:
    def test_the_legacy_manifest_states_the_mode(self) -> None:
        plan = resolve_initiation_plan({}, {PATHOGEN: _profile()})
        assert build_initiation_manifest(plan, [], []) == {"mode": MODE_LEGACY}

    def test_the_mode_names_which_mechanisms_ran(self) -> None:
        profiles = {PATHOGEN: _profile()}
        boarding = resolve_initiation_plan(_cfg(), profiles)
        assert build_initiation_manifest(
            boarding, [], [],
        )["mode"] == MODE_BOARDING
        seeds_cfg = {
            "initiation": {
                "explicit_seeds": [{"pathogen": PATHOGEN, "count": 1}],
            },
        }
        seeds = resolve_initiation_plan(seeds_cfg, profiles)
        assert build_initiation_manifest(
            seeds, [], [],
        )["mode"] == MODE_SEEDS
        both_cfg = dict(_cfg())
        both_cfg["initiation"] = dict(both_cfg["initiation"])
        both_cfg["initiation"]["explicit_seeds"] = [
            {"pathogen": PATHOGEN, "count": 1},
        ]
        both = resolve_initiation_plan(both_cfg, profiles)
        assert build_initiation_manifest(
            both, [], [],
        )["mode"] == MODE_BOARDING_AND_SEEDS

    def test_the_manifest_records_the_configured_coordinates(self) -> None:
        profiles = {PATHOGEN: _profile()}
        plan = resolve_initiation_plan(_cfg(never=0.3, pre=0.1), profiles)
        _, _, report = _draw(_spec(passenger=0.4, crew=0.4), 11)
        manifest = build_initiation_manifest(plan, [report], [])
        split = manifest["state_split"][PATHOGEN]
        assert split["never_symptomatic_fraction"] == pytest.approx(0.3)
        assert split["presymptomatic_share_of_presenting"] == pytest.approx(0.1)
        drawn = manifest["boarding"][PATHOGEN]["drawn_by_role"]
        assert set(drawn) == {"passenger", "crew"}
        assert set(manifest["boarding"][PATHOGEN]["composition"]) == {
            STATE_NEVER_SYMPTOMATIC, STATE_PRESYMPTOMATIC, STATE_CONVALESCENT,
            STATE_INCUBATING,
        }
        assert manifest["boarding_mode"] == {PATHOGEN: "prevalence"}
        assert manifest["party"] == {}


class TestInitWiring:
    def test_an_unowned_pathogen_keeps_its_epoch_zero_index_case(self) -> None:
        engine = _FakeEngine()
        profiles = {
            PATHOGEN: _profile(),
            OTHER_PATHOGEN: _profile(
                introduction_epoch=0, initial_infected=2,
            ),
        }
        init_multi_pathogen(
            engine, profiles, _cfg(), np.random.default_rng(31),
        )
        seeded = [
            agent for agent in engine.agents
            if OTHER_PATHOGEN in agent.infections
        ]
        assert len(seeded) == 2

    def test_an_unowned_pathogen_still_introduces_mid_cruise(self) -> None:
        engine = _FakeEngine()
        profiles = {
            PATHOGEN: _profile(),
            OTHER_PATHOGEN: _profile(
                introduction_epoch=6, initial_infected=1,
            ),
        }
        init_multi_pathogen(
            engine, profiles, _cfg(), np.random.default_rng(32),
        )
        assert not any(
            OTHER_PATHOGEN in agent.infections for agent in engine.agents
        )
        step_mid_cruise_introductions(
            6, engine, profiles, np.random.default_rng(33),
        )
        introduced = [
            agent for agent in engine.agents
            if OTHER_PATHOGEN in agent.infections
        ]
        assert len(introduced) == 1

    def test_a_staged_pathogen_boards_at_its_port_call_once(self) -> None:
        engine = _FakeEngine()
        profiles = {PATHOGEN: _profile(introduction_epoch=6)}
        init_multi_pathogen(
            engine, profiles, _cfg(passenger=0.1, crew=0.1),
            np.random.default_rng(34),
        )
        assert engine.initiation_manifest["boarding_epoch"] == {PATHOGEN: 6}
        assert PATHOGEN not in engine.initiation_manifest["boarding"]
        assert not [a for a in engine.agents if PATHOGEN in a.infections]
        step_mid_cruise_introductions(
            5, engine, profiles, np.random.default_rng(35),
        )
        assert not [a for a in engine.agents if PATHOGEN in a.infections]
        step_mid_cruise_introductions(
            6, engine, profiles, np.random.default_rng(35),
        )
        boarded = sum(
            engine.initiation_manifest["boarding"][PATHOGEN][
                "drawn_by_role"
            ].values(),
        )
        infected = [
            agent for agent in engine.agents if PATHOGEN in agent.infections
        ]
        assert boarded > 0
        assert len(infected) == boarded

    def test_a_block_epoch_overrides_the_profile_schedule(self) -> None:
        cfg = _cfg(passenger=0.1, crew=0.1)
        cfg["initiation"]["boarding"][PATHOGEN]["epoch"] = 2
        plan = resolve_initiation_plan(
            cfg, {PATHOGEN: _profile(introduction_epoch=6)},
        )
        assert plan.boarding[0].epoch == 2

    def test_a_negative_epoch_is_refused(self) -> None:
        cfg = _cfg(passenger=0.1, crew=0.1)
        cfg["initiation"]["boarding"][PATHOGEN]["epoch"] = -1
        with pytest.raises(ValueError, match="epoch = -1"):
            resolve_initiation_plan(cfg, {PATHOGEN: _profile()})

    def test_a_boarding_run_leaves_no_fiat_index_case(self) -> None:
        engine, _ = _init_run(_cfg(passenger=0.2, crew=0.2))
        manifest = engine.initiation_manifest
        assert manifest["mode"] == MODE_BOARDING
        boarded = sum(
            manifest["boarding"][PATHOGEN]["drawn_by_role"].values(),
        )
        infected = [
            agent for agent in engine.agents
            if agent.infection_status == InfectionStatus.INFECTED
        ]
        assert boarded > 0
        assert len(infected) == boarded

    def test_a_legacy_run_keeps_the_profile_index_case(self) -> None:
        engine = _FakeEngine()
        profile = _profile(initial_infected=2, initial_time_infected=0)
        init_multi_pathogen(
            engine, {PATHOGEN: profile}, {"multi_pathogen": {}},
            np.random.default_rng(21),
        )
        infected = [
            agent for agent in engine.agents if PATHOGEN in agent.infections
        ]
        assert len(infected) == 2
        assert engine.initiation_manifest == {"mode": MODE_LEGACY}


# ── Party mode and profile-carried blocks ────────────────────────────────

_SPLIT = {
    "never_symptomatic_fraction": 0.2,
    "presymptomatic_share_of_presenting": 0.3,
}


def _party_spec(
    probability: float = 1.0, size: int = 3, role: str = "passenger",
    never: float = 0.2, pre_share: float = 0.3,
) -> BoardingSpec:
    return BoardingSpec(
        pathogen_id=PATHOGEN,
        passenger_prevalence=0.0,
        crew_prevalence=0.0,
        never_symptomatic_fraction=never,
        presymptomatic_share_of_presenting=pre_share,
        party=BoardingParty(probability=probability, size=size, role=role),
    )


def _party_block(**party: Any) -> dict[str, Any]:
    return {
        "mode": "party",
        "party": {"probability": 1.0, "size": 3, "role": "passenger", **party},
        "state_split": dict(_SPLIT),
    }


def _cabin(engine: _FakeEngine, ids: set[int]) -> None:
    for agent in engine.agents:
        if agent.agent_id in ids:
            agent.cabin_mate_ids = frozenset(ids - {agent.agent_id})


class TestPartyMode:
    def test_a_party_is_all_or_nothing(self) -> None:
        sizes = {
            sum(_draw(_party_spec(probability=0.5, size=4), seed)[2]
                .drawn_by_role.values())
            for seed in range(40)
        }
        assert sizes == {0, 4}

    def test_party_probability_moves_how_often_a_party_boards(self) -> None:
        def rate(probability: float) -> float:
            boarded = [
                sum(_draw(_party_spec(probability=probability), seed)[2]
                    .drawn_by_role.values()) > 0
                for seed in range(60)
            ]
            return sum(boarded) / len(boarded)

        assert rate(0.0) == 0.0
        assert rate(0.2) < rate(0.8)
        assert rate(1.0) == 1.0

    def test_party_size_is_the_drawn_count_when_one_boards(self) -> None:
        for size in (1, 2, 5):
            _, _, report = _draw(_party_spec(size=size), 3)
            assert sum(report.drawn_by_role.values()) == size

    def test_the_party_stays_in_its_role(self) -> None:
        _, _, report = _draw(_party_spec(role="crew", size=3), 5)
        assert report.drawn_by_role == {"passenger": 0, "crew": 3}

    def test_the_party_shares_a_cabin_when_one_holds_it(self) -> None:
        engine = _FakeEngine()
        cabins = [set(range(i, i + 4)) for i in range(0, PASSENGERS, 4)]
        for cabin in cabins:
            _cabin(engine, cabin)
        draw_boarding_cohort(
            _party_spec(size=3), engine.agents, _profile(), engine.clock,
            np.random.default_rng(11),
        )
        infected = _infected_ids(engine)
        assert len(infected) == 3
        assert any(infected <= cabin for cabin in cabins)

    def test_a_party_member_is_never_convalescent(self) -> None:
        composition: dict[str, int] = {}
        for seed in SEEDS:
            _, _, report = _draw(_party_spec(size=6), seed)
            for state, count in report.composition.items():
                composition[state] = composition.get(state, 0) + count
        assert composition[STATE_CONVALESCENT] == 0
        assert composition[STATE_INCUBATING] > 0

    def test_an_incubating_member_will_present_and_is_not_yet_ill(self) -> None:
        engine, _, _ = _draw(_party_spec(size=6, never=0.0, pre_share=0.0), 2)
        infections = [
            agent.infections[PATHOGEN] for agent in engine.agents
            if PATHOGEN in agent.infections
        ]
        assert infections
        for inf in infections:
            assert inf["will_present"] is True
            assert inf["illness"] == IllnessStatus.NOT_ILL
            assert inf["status"] == InfectionStatus.INFECTED

    def test_no_party_consumes_no_further_draws(self) -> None:
        rng = np.random.default_rng(4)
        engine = _FakeEngine()
        draw_boarding_cohort(
            _party_spec(probability=0.0), engine.agents, _profile(),
            engine.clock, rng,
        )
        assert rng.random() == np.random.default_rng(4).random(2)[1]


class TestPartyResolution:
    def test_a_party_block_resolves_to_party_mode(self) -> None:
        plan = resolve_initiation_plan(
            {"initiation": {"boarding": {"enabled": True, PATHOGEN: _party_block()}}},
            {PATHOGEN: _profile()},
        )
        (spec,) = plan.boarding
        assert spec.mode == "party"
        assert spec.party == BoardingParty(1.0, 3, "passenger")
        assert spec.passenger_prevalence == 0.0

    def test_a_party_alongside_a_prevalence_is_an_error(self) -> None:
        block = _party_block()
        block["prevalence"] = {"passenger": 0.1, "crew": 0.1}
        with pytest.raises(ValueError, match="also carries a prevalence"):
            resolve_initiation_plan(
                {"initiation": {"boarding": {"enabled": True, PATHOGEN: block}}},
                {PATHOGEN: _profile()},
            )

    @pytest.mark.parametrize(
        ("party", "match"),
        [
            ({"size": 0}, "party.size"),
            ({"role": "officer"}, "party.role"),
            ({"probability": 1.5}, "party.probability"),
            ({"probability": None}, "party.probability"),
        ],
    )
    def test_a_malformed_party_is_an_error(
        self, party: dict[str, Any], match: str,
    ) -> None:
        with pytest.raises(ValueError, match=match):
            resolve_initiation_plan(
                {"initiation": {"boarding": {
                    "enabled": True, PATHOGEN: _party_block(**party),
                }}},
                {PATHOGEN: _profile()},
            )

    def test_an_unknown_mode_is_an_error(self) -> None:
        block = _party_block()
        block["mode"] = "cluster"
        with pytest.raises(ValueError, match="mode"):
            resolve_initiation_plan(
                {"initiation": {"boarding": {"enabled": True, PATHOGEN: block}}},
                {PATHOGEN: _profile()},
            )

    def test_the_manifest_records_the_party(self) -> None:
        engine = _FakeEngine()
        plan = resolve_initiation_plan(
            {"initiation": {"boarding": {"enabled": True, PATHOGEN: _party_block()}}},
            {PATHOGEN: _profile()},
        )
        report = draw_boarding_cohort(
            plan.boarding[0], engine.agents, _profile(), engine.clock,
            np.random.default_rng(0),
        )
        manifest = build_initiation_manifest(plan, [report], [])
        assert manifest["boarding_mode"] == {PATHOGEN: "party"}
        assert manifest["party"][PATHOGEN] == {
            "probability": 1.0, "size": 3, "role": "passenger",
        }


class TestProfileCarriedBlocks:
    def _profiles(self) -> dict[str, dict[str, Any]]:
        return {
            PATHOGEN: _profile(boarding={
                "prevalence": {"passenger": 0.05, "crew": 0.02},
                "state_split": dict(_SPLIT),
            }),
            OTHER_PATHOGEN: _profile(boarding=_party_block()),
        }

    def test_every_loaded_profile_with_a_block_boards(self) -> None:
        plan = resolve_initiation_plan(
            {"initiation": {"boarding": {"enabled": True}}}, self._profiles(),
        )
        assert {s.pathogen_id: s.mode for s in plan.boarding} == {
            PATHOGEN: "prevalence", OTHER_PATHOGEN: "party",
        }

    def test_a_narrowed_run_inherits_no_stale_block(self) -> None:
        profiles = self._profiles()
        del profiles[PATHOGEN]
        plan = resolve_initiation_plan(
            {"initiation": {"boarding": {"enabled": True}}}, profiles,
        )
        assert [s.pathogen_id for s in plan.boarding] == [OTHER_PATHOGEN]

    def test_a_config_override_lands_on_one_coordinate(self) -> None:
        plan = resolve_initiation_plan(
            {"initiation": {"boarding": {
                "enabled": True,
                PATHOGEN: {"state_split": {"never_symptomatic_fraction": 0.6}},
            }}},
            self._profiles(),
        )
        spec = next(s for s in plan.boarding if s.pathogen_id == PATHOGEN)
        assert spec.never_symptomatic_fraction == pytest.approx(0.6)
        assert spec.passenger_prevalence == pytest.approx(0.05)
        assert spec.presymptomatic_share_of_presenting == pytest.approx(0.3)

    def test_a_per_pathogen_disable_is_the_fiat_opt_out(self) -> None:
        profiles = self._profiles()
        profiles[PATHOGEN]["initial_infected"] = 2
        plan = resolve_initiation_plan(
            {"initiation": {"boarding": {
                "enabled": True, PATHOGEN: {"enabled": False},
            }}},
            profiles,
        )
        assert [s.pathogen_id for s in plan.boarding] == [OTHER_PATHOGEN]

    def test_a_profile_block_over_a_fiat_index_case_is_an_error(self) -> None:
        profiles = self._profiles()
        profiles[PATHOGEN]["initial_infected"] = 2
        with pytest.raises(ValueError, match="initial_infected"):
            resolve_initiation_plan(
                {"initiation": {"boarding": {"enabled": True}}}, profiles,
            )

    def test_a_config_block_over_an_unloaded_pathogen_is_an_error(self) -> None:
        profiles = self._profiles()
        del profiles[OTHER_PATHOGEN]
        with pytest.raises(ValueError, match="absent from the loaded profiles"):
            resolve_initiation_plan(
                {"initiation": {"boarding": {
                    "enabled": True, OTHER_PATHOGEN: {"enabled": True},
                }}},
                profiles,
            )
