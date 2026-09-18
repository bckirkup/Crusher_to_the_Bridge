"""The symptomatic boarding stream: partition, recurrence-time draw, seam.

The stream splits the renewal-derived import rate into an ill-at-embarkation
share p_sym = (I/1000)(E[T]/365.25) and the remainder p_asym; it is a
partition, so the total drawn RNA-positive cohort must not grow. Numbers
checked against the derivation of record in
docs/norovirus/symptomatic_boarding_stream.md; the labelled change-detectors
pin the derived values, not the mechanism.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np
import pytest

from engines.illness_duration import IllnessDurationModel
from engines.infection_dynamics_bridge import (
    IllnessStatus,
    KorkinAgent,
)
from engines.initiation import (
    STATE_CLEARED,
    STATE_SYMPTOMATIC,
    BoardingSpec,
    _board_one_symptomatic_host,
    draw_boarding_cohort,
    resolve_initiation_plan,
)
from engines.natural_history import advance_infections, severity_on_day
from engines.sim_clock import HOURS, SimClock

PATHOGEN = "norwalk_gi"
ZONE = "Cabin_A"
# O'Brien 2016 Table 1 case incidence (per 1000 person-years) and Atmar 2008
# detectable duration — the two sourced inputs the partition is an identity
# over.
INCIDENCE = {"passenger": 39.0, "crew": 39.0}
DETECTABLE_DAYS = 28.0
NEVER = 0.29
PRE_SHARE = 0.04

_HARRIS_SURVIVAL = [
    {"day": 0, "probability": 1.0},
    {"day": 1, "probability": 0.63},
    {"day": 2, "probability": 0.355},
    {"day": 3, "probability": 0.22},
    {"day": 4, "probability": 0.13},
    {"day": 5, "probability": 0.079},
    {"day": 6, "probability": 0.057},
    {"day": 7, "probability": 0.03},
    {"day": 8, "probability": 0.023},
    {"day": 9, "probability": 0.019},
    {"day": 13, "probability": 0.0},
]
_ILLNESS_BLOCK: dict[str, Any] = {
    "draw": "empirical_survival",
    "unit": "days",
    "survival": _HARRIS_SURVIVAL,
    "notes": "Harris 2019 Fig 4C fixture.",
}


def _clock() -> SimClock:
    return SimClock(epoch_duration_hours=1.0, mode=HOURS)


def _agent(agent_id: int, role: str = "passenger") -> KorkinAgent:
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


def _profile(**overrides: Any) -> dict[str, Any]:
    """A profile carrying everything a symptomatic boarder reads."""
    profile: dict[str, Any] = {
        "base_susceptibility": 1.0,
        "introduction_epoch": 0,
        "symptom_onset_day": 1.0,
        "recovery_day": 3,
        "shedding_duration_days": 15.0,
        "presymptomatic_shedding_days": 0.5,
        "illness_duration": dict(_ILLNESS_BLOCK),
        "severity_model": {
            "states": [
                "asymptomatic", "subclinical", "mild", "moderate",
                "severe_critical",
            ],
            "base_probabilities": [0.0, 0.0, 0.0, 0.0, 1.0],
            # The ladder drops the course two rungs per day, so day int(a)
            # reads off the peak visibly rather than coinciding with it.
            "trajectory_ladder_offsets_by_day": [0, 0, 1, 2, 2, 2],
        },
        "clinical_presentation": {
            "symptom_axis_probabilities": {
                "vomiting": 1.0,
                "diarrhoea_given_vomiting": 1.0,
            },
            "phases": [
                {
                    "name": "acute",
                    "features": ["vomiting"],
                    "dpi_min": 0,
                    "dpi_max": 2,
                },
            ],
        },
        "emesis_episodes_range": [2, 4],
        "emesis_titre_gec_per_ml_range": [1e5, 1e5],
        "emesis_censored_titre_gec_per_ml_range": [1e4, 1e4],
    }
    profile.update(overrides)
    return profile


def _cfg(
    symptomatic_stream: dict[str, Any] | None,
    **overrides: Any,
) -> dict[str, Any]:
    block: dict[str, Any] = {
        "rate_mode": "renewal",
        "renewal": {
            "case_incidence_per_1000_py": dict(
                overrides.pop("incidence", INCIDENCE),
            ),
            "detectable_duration_days": overrides.pop(
                "detectable", DETECTABLE_DAYS,
            ),
        },
        "state_split": {
            "never_symptomatic_fraction": overrides.pop("never", NEVER),
            "presymptomatic_share_of_presenting": overrides.pop(
                "pre", PRE_SHARE,
            ),
        },
    }
    block.update(overrides)
    if symptomatic_stream is not None:
        block["symptomatic_stream"] = symptomatic_stream
    else:
        # ATTRIBUTED MOVE (realism-default flip): an unstated stream under
        # renewal is now ON. These fixtures mean "off", so they state it.
        block["symptomatic_stream"] = {"enabled": False}
    if "preboarding_assessment" not in block:
        # Same flip: an unstated preboarding block under renewal resolves
        # to the reference crew clause; these fixtures mean "off".
        block["preboarding_assessment"] = {
            "crew": {"enabled": False},
            "passenger": {"enabled": False},
        }
    return {"initiation": {"boarding": {"enabled": True, PATHOGEN: block}}}


def _resolve(
    symptomatic_stream: dict[str, Any] | None,
    profile: dict[str, Any] | None = None,
    **overrides: Any,
) -> BoardingSpec:
    profiles = {PATHOGEN: profile or _profile()}
    plan = resolve_initiation_plan(_cfg(symptomatic_stream, **overrides), profiles)
    (spec,) = plan.boarding
    return spec


def _p_total(rate: float, never: float, detectable: float) -> float:
    return (rate / 1000.0) / (1.0 - never) * (detectable / 365.25)


def _p_sym(rate: float, mean_days: float) -> float:
    return (rate / 1000.0) * (mean_days / 365.25)


def _model() -> IllnessDurationModel:
    model = IllnessDurationModel.from_mapping(_ILLNESS_BLOCK)
    assert model is not None
    return model


def _sym_spec(
    sym_pax: float = 0.5,
    sym_crew: float = 0.0,
    asym: float = 0.0,
) -> BoardingSpec:
    return BoardingSpec(
        pathogen_id=PATHOGEN,
        passenger_prevalence=asym,
        crew_prevalence=asym,
        never_symptomatic_fraction=NEVER,
        presymptomatic_share_of_presenting=PRE_SHARE,
        rate_mode="renewal",
        symptomatic_stream=True,
        symptomatic_passenger_prevalence=sym_pax,
        symptomatic_crew_prevalence=sym_crew,
        mean_illness_duration_days=_model().mean_days(),
    )


def _boarded(profile: dict[str, Any], seed: int) -> tuple[KorkinAgent, str]:
    agent = _agent(seed)
    clock = _clock()
    spec = _sym_spec()
    state = _board_one_symptomatic_host(
        spec, agent, profile, clock, np.random.default_rng(seed),
    )
    assert state is not None
    return agent, state


class TestPartition:
    """p_sym + p_asym = p_total exactly; enabling the stream cannot grow
    the drawn cohort."""

    def test_partition_conserves_the_total(self) -> None:
        spec = _resolve({"enabled": True, "notes": "x"})
        total = _p_total(39.0, NEVER, DETECTABLE_DAYS)
        assert spec.symptomatic_passenger_prevalence + spec.passenger_prevalence == (
            pytest.approx(total, abs=1e-12)
        )
        assert spec.symptomatic_crew_prevalence + spec.crew_prevalence == (
            pytest.approx(total, abs=1e-12)
        )

    def test_derived_values_match_the_doc(self) -> None:
        """CHANGE DETECTOR: the derived numbers of the derivation of record."""
        spec = _resolve({"enabled": True, "notes": "x"})
        assert spec.symptomatic_passenger_prevalence == pytest.approx(
            0.02746e-2, abs=1e-7,
        )
        assert spec.passenger_prevalence == pytest.approx(0.3936e-2, abs=1e-6)
        share = (
            spec.symptomatic_passenger_prevalence
            / (spec.symptomatic_passenger_prevalence
               + spec.passenger_prevalence)
        )
        assert share == pytest.approx(0.0652, abs=1e-4)
        assert spec.mean_illness_duration_days == pytest.approx(
            2.5715, abs=1e-4,
        )

    def test_point_mode_uses_recovery_day_as_the_mean(self) -> None:
        spec = _resolve(
            {"enabled": True, "notes": "x"},
            profile=_profile(illness_duration=None),
        )
        assert spec.mean_illness_duration_days == pytest.approx(3.0)
        assert spec.symptomatic_passenger_prevalence == pytest.approx(
            0.03203e-2, abs=1e-7,
        )

    def test_the_drawn_cohort_does_not_grow(self) -> None:
        """Invariant: enabling the partition leaves the RNA-positive rate."""
        profile = _profile()
        # A large incidence keeps the Monte-Carlo comparison off the noise
        # floor; the claim is invariance of the total, not the level.
        arms = {
            "off": _resolve(None, incidence={"passenger": 1000.0, "crew": 0.0}),
            "on": _resolve(
                {"enabled": True, "notes": "x"},
                incidence={"passenger": 1000.0, "crew": 0.0},
            ),
        }
        drawn: dict[str, list[int]] = {arm: [] for arm in arms}
        for arm, spec in arms.items():
            for seed in range(25):
                agents = [_agent(i + seed * 1000) for i in range(600)]
                report = draw_boarding_cohort(
                    spec, agents, profile, _clock(),
                    np.random.default_rng(seed),
                )
                drawn[arm].append(sum(report.composition.values()))
        assert np.mean(drawn["on"]) == pytest.approx(
            np.mean(drawn["off"]), rel=0.10,
        )

    def test_introductions_equal_composition_minus_cleared(self) -> None:
        spec = _resolve({"enabled": True, "notes": "x"})
        for seed in range(10):
            agents = [_agent(i + seed * 600) for i in range(600)]
            report = draw_boarding_cohort(
                spec, agents, _profile(), _clock(),
                np.random.default_rng(seed),
            )
            assert sum(report.drawn_by_role.values()) == (
                sum(report.composition.values())
                - report.composition[STATE_CLEARED]
            )


class TestLengthBiasedDraw:
    def test_samples_reproduce_the_length_biased_mean(self) -> None:
        model = _model()
        pmf = {
            d: model.survival_at(d - 1) - model.survival_at(d)
            for d in range(1, 14)
        }
        expected = sum(d * d * p for d, p in pmf.items()) / model.mean_days()
        rng = np.random.default_rng(0)
        draws = [model.sample_length_biased_days(rng) for _ in range(20000)]
        assert np.mean(draws) == pytest.approx(expected, abs=0.1)
        assert np.mean(draws) > model.mean_days()

    def test_elapsed_time_covers_three_quarters_by_day_3(self) -> None:
        """P(a <= 3) = 0.772: VSP's three-day window has something to catch.

        Sampled as the renewal construction draws it: length-biased T, then
        a ~ U(0, T).
        """
        model = _model()
        rng = np.random.default_rng(1)
        covered = []
        for _ in range(20000):
            duration = model.sample_length_biased_days(rng)
            covered.append(float(rng.uniform(0.0, duration)) <= 3.0)
        assert np.mean(covered) == pytest.approx(0.7719, abs=0.02)

    def test_mean_days_is_the_exact_table_mean(self) -> None:
        model = _model()
        pmf = {
            d: model.survival_at(d - 1) - model.survival_at(d)
            for d in range(1, 14)
        }
        assert model.mean_days() == pytest.approx(
            sum(d * p for d, p in pmf.items()), abs=1e-12,
        )
        assert model.mean_days() == pytest.approx(2.5715, abs=1e-4)


class TestSymptomaticHost:
    def test_the_boarder_is_ill_at_embarkation(self) -> None:
        agent, state = _boarded(_profile(), 7)
        inf = agent.infections[PATHOGEN]
        assert state == STATE_SYMPTOMATIC
        assert inf["boarding_state"] == STATE_SYMPTOMATIC
        assert inf["illness"] == IllnessStatus.SYMPTOMATIC
        assert inf["presented"] is True
        assert inf["will_present"] is True
        assert agent.illness_status == IllnessStatus.SYMPTOMATIC
        duration = inf["recovery_day"]
        assert 0.0 <= inf["days_since_onset_at_boarding"] < duration
        assert inf["onset_time_infected"] == pytest.approx(
            round(_clock().epochs_for_days(inf["incubation_days"])),
        )
        # The host is already int(a) days into its course: the observer sees
        # that day of the ladder, not day 0 and not the peak.
        expected = severity_on_day(
            _profile(), inf["symptom_severity_peak"],
            int(inf["days_since_onset_at_boarding"]),
        )
        assert inf["symptom_severity"] == expected

    def test_the_illness_ends_t_minus_a_days_into_the_voyage(self) -> None:
        agent, _ = _boarded(_profile(), 11)
        profile = _profile()
        inf = agent.infections[PATHOGEN]
        elapsed = inf["days_since_onset_at_boarding"]
        duration = inf["recovery_day"]
        rng = np.random.default_rng(0)
        end_epoch = None
        for epoch in range(int(_clock().epochs_for_days(30))):
            advance_infections(
                agent, {PATHOGEN: profile}, rng, epoch=epoch,
            )
            if (
                inf["illness"] == IllnessStatus.RECOVERED
                and end_epoch is None
            ):
                end_epoch = epoch
        assert end_epoch is not None
        # Illness ends when days_infected reaches incubation + T; boarding is
        # incubation + a days in, so the voyage sees T - a days of illness.
        remaining_days = duration - elapsed
        assert _clock().days_elapsed(end_epoch) == pytest.approx(
            remaining_days, abs=1.0 / 24.0 + 0.5,
        )

    def test_point_mode_draws_the_same_three_day_illness(self) -> None:
        """Under the point duration the stream exists but disperses nothing."""
        profile = _profile(illness_duration=None)
        for seed in range(20):
            agent, state = _boarded(profile, seed + 100)
            if state == STATE_CLEARED:
                continue
            inf = agent.infections[PATHOGEN]
            assert inf["recovery_day"] == 3
            assert inf["days_since_onset_at_boarding"] < 3.0

    def test_beyond_shedding_is_cleared(self) -> None:
        """An elapsed age past the authored shedding window is the
        representability boundary, not a record."""
        profile = _profile(shedding_duration_days=1.0)
        cleared = sum(
            _boarded(profile, seed)[1] == STATE_CLEARED
            for seed in range(60)
        )
        assert cleared > 0

    def test_ashore_emesis_episodes_are_dropped(self) -> None:
        """Events at or before a happened ashore: they must never fire."""
        for seed in range(80):
            agent, state = _boarded(_profile(), seed + 400)
            if state != STATE_SYMPTOMATIC:
                continue
            inf = agent.infections[PATHOGEN]
            elapsed = inf["days_since_onset_at_boarding"]
            schedule = agent.emesis_episode_schedule_by_pathogen[PATHOGEN]
            # The onset axis the emitter reads is days since onset — at
            # boarding that is elapsed_days, so nothing due can fire.
            assert all(age > elapsed for age in schedule)

    def test_convalescent_boarders_carry_the_same_observable(self) -> None:
        spec = BoardingSpec(
            pathogen_id=PATHOGEN,
            passenger_prevalence=1.0,
            crew_prevalence=0.0,
            never_symptomatic_fraction=0.0,
            presymptomatic_share_of_presenting=0.0,
        )
        agents = [_agent(i) for i in range(80)]
        draw_boarding_cohort(
            spec, agents, _profile(), _clock(), np.random.default_rng(3),
        )
        convalescent = [
            a for a in agents
            if PATHOGEN in a.infections
            and a.infections[PATHOGEN]["boarding_state"] == "convalescent"
        ]
        assert convalescent
        for agent in convalescent:
            inf = agent.infections[PATHOGEN]
            assert inf["days_since_onset_at_boarding"] == pytest.approx(
                inf["time_infected"] / 24.0 - inf["incubation_days"],
                abs=0.5 / 24.0,  # age is rounded to whole epochs
            )


class TestRefusals:
    def test_screening_prevalence_refuses_the_stream(self) -> None:
        cfg = _cfg({"enabled": True, "notes": "x"})
        block = cfg["initiation"]["boarding"][PATHOGEN]
        block["rate_mode"] = "screening_prevalence"
        block["prevalence"] = {"passenger": 0.03, "crew": 0.02}
        with pytest.raises(ValueError, match="renewal"):
            resolve_initiation_plan(cfg, {PATHOGEN: _profile()})

    def test_party_mode_refuses_the_stream(self) -> None:
        cfg = _cfg({"enabled": True, "notes": "x"})
        block = cfg["initiation"]["boarding"][PATHOGEN]
        block.pop("rate_mode")
        block.pop("renewal")
        block["mode"] = "party"
        block["party"] = {"probability": 0.1, "size": 3}
        with pytest.raises(ValueError, match="party"):
            resolve_initiation_plan(cfg, {PATHOGEN: _profile()})

    def test_a_negative_partition_is_refused(self) -> None:
        # A mean illness longer than the detectable window empties p_asym.
        with pytest.raises(ValueError, match="partition"):
            _resolve(
                {"enabled": True, "notes": "x"},
                incidence={"passenger": 39.0, "crew": 39.0},
                detectable=1.0,
            )

    def test_unknown_stream_keys_are_refused(self) -> None:
        with pytest.raises(ValueError, match="unknown keys"):
            _resolve({"enabled": True, "notes": "x", "typo": 1})

    def test_a_non_mapping_stream_is_refused(self) -> None:
        cfg = _cfg({"enabled": True, "notes": "x"})
        cfg["initiation"]["boarding"][PATHOGEN]["symptomatic_stream"] = "on"
        with pytest.raises(ValueError, match="must be a mapping"):
            resolve_initiation_plan(cfg, {PATHOGEN: _profile()})

    def test_a_disabled_stream_reads_no_further_keys(self) -> None:
        spec = _resolve({"enabled": False, "notes": "x"})
        assert spec.symptomatic_stream is False
        assert spec.symptomatic_passenger_prevalence == 0.0
        assert spec.mean_illness_duration_days is None


class TestDefaultInertness:
    """The stream off is bit-for-bit the pre-arm draw.

    CHANGE DETECTOR: the fingerprint and RNG cursor pin the renewal draw
    captured with the arm disabled — which consumes no draw the pre-arm code
    did not make. If it moves, the arm is not inert: investigate, do not
    update the constants.
    """

    _INERTNESS_FINGERPRINT = (
        "044ff63110c7c58fbb84cf724b876278fcac32ca1ed0edd1820c3a3fe1e4d79c"
    )
    _INERTNESS_RNG_NEXT = 0.8120945066557737

    def _run(self) -> tuple[str, float]:
        # ATTRIBUTED MOVE (realism-default flip): the historical arm also
        # needs age_draw stated — unstated now means stationary.
        spec = _resolve(None, age_draw="engine_window")
        rng = np.random.default_rng(123)
        agents = [_agent(i) for i in range(200)] + [
            _agent(200 + i, "crew") for i in range(100)
        ]
        report = draw_boarding_cohort(
            spec, agents, _profile(), _clock(), rng,
        )
        records = sorted(
            (
                agent.agent_id,
                agent.infections[PATHOGEN]["boarding_state"],
                agent.infections[PATHOGEN]["time_infected"],
            )
            for agent in agents
            if PATHOGEN in agent.infections
        )
        payload = {
            "records": records,
            "drawn": report.drawn_by_role,
            "composition": {
                state: count
                for state, count in report.composition.items()
                if count
            },
        }
        fingerprint = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode(),
        ).hexdigest()
        return fingerprint, rng.random()

    def test_the_off_draw_is_the_pre_arm_draw(self) -> None:
        fingerprint, rng_next = self._run()
        assert fingerprint == self._INERTNESS_FINGERPRINT
        assert rng_next == pytest.approx(
            self._INERTNESS_RNG_NEXT, abs=1e-15,
        )
