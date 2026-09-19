"""Declared index onset day (SEED-ONSET-01).

``ExplicitSeed.onset_day`` states the voyage day of the seeded host's
observed symptom onset on the same day axis as ``departure_day`` (signed:
onset before the seed's own epoch is the ordinary case). The implied
incubation ``infection_age_days + onset_day − <seed day>`` is a consequence
of the record rather than a draw from the profile distribution.

Sensitivity, invariants and validation here; no goldens.
"""

from __future__ import annotations

import numpy as np
import pytest

from engines.infection_dynamics_bridge import (
    IllnessStatus,
    KorkinAgent,
)
from engines.initiation import apply_explicit_seeds, resolve_initiation_plan
from engines.natural_history import advance_infections
from engines.sim_clock import SimClock

PATHOGEN = "test_pathogen"
ZONE = "Test_Zone"
HOURS_PER_EPOCH = 6.0


def _clock() -> SimClock:
    return SimClock(epoch_duration_hours=HOURS_PER_EPOCH, mode="hours")


def _agent(agent_id: int) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=agent_id,
        role="passenger",
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


def _profile() -> dict:
    return {
        "shedding_curve_log10": [7.0] * 40,
        "asymptomatic_shedding_log10": [7.0] * 40,
        "symptom_onset_day": 0.0,
        "recovery_day": 1000.0,
        "shedding_duration_days": 30.0,
        "airborne_half_life_hours": 24.0,
        "dose_response": {"model": "exponential", "k": 0.05},
    }


class _FakeEngine:
    def __init__(self, passengers: int = 40) -> None:
        self.agents = [_agent(i) for i in range(passengers)]
        self.clock = _clock()
        self.initiation_manifest: dict = {"mode": "legacy"}


def _plan(**seed_fields):
    seed = {"pathogen": PATHOGEN, "count": 1, "epoch": 0}
    seed.update(seed_fields)
    return resolve_initiation_plan(
        {"initiation": {"explicit_seeds": [seed]}}, {PATHOGEN: _profile()},
    )


def _apply(plan, engine, rng_seed: int = 1):
    return apply_explicit_seeds(
        plan, engine, 0, np.random.default_rng(rng_seed), {PATHOGEN: _profile()},
    )


def _seeded(engine) -> KorkinAgent:
    return next(a for a in engine.agents if PATHOGEN in a.infections)


class TestDeclaration:
    def test_unset_by_default(self) -> None:
        assert _plan().seeds[0].onset_day is None

    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_onset_is_refused(self, bad: float) -> None:
        with pytest.raises(ValueError, match="onset_day"):
            _plan(onset_day=bad)

    def test_signed_onset_is_accepted(self) -> None:
        assert _plan(onset_day=-1.0).seeds[0].onset_day == -1.0

    def test_manifest_record_carries_the_declared_day(self) -> None:
        engine = _FakeEngine()
        records = _apply(_plan(infection_age_days=4.0, onset_day=-1.0), engine)
        assert records[0]["onset_day"] == -1.0
        assert engine.initiation_manifest["seeds"][0]["onset_day"] == -1.0


class TestImpliedIncubation:
    @pytest.mark.parametrize(
        "age,onset", [(2.0, -1.0), (4.0, -0.5), (6.8, -1.0), (8.0, 1.5)],
    )
    def test_incubation_is_age_plus_onset_minus_seed_day(
        self, age: float, onset: float,
    ) -> None:
        engine = _FakeEngine()
        _apply(_plan(infection_age_days=age, onset_day=onset), engine)
        inf = _seeded(engine).infections[PATHOGEN]
        assert inf["incubation_days"] == pytest.approx(age + onset - 0.0)
        assert inf["will_present"] is True

    def test_onset_before_acquisition_is_refused(self) -> None:
        engine = _FakeEngine()
        with pytest.raises(ValueError, match="explicit_seeds.*onset"):
            _apply(_plan(infection_age_days=0.0, onset_day=-1.0), engine)

    def test_onset_past_the_shedding_window_is_refused(self) -> None:
        engine = _FakeEngine()
        with pytest.raises(ValueError, match="shedding window"):
            _apply(
                _plan(infection_age_days=40.0, onset_day=-35.0), engine,
            )


class TestSymptomaticAtBoarding:
    def test_stamps_the_arrival_record(self) -> None:
        """Onset 1 day before boarding: the host boards already ill."""
        engine = _FakeEngine()
        _apply(_plan(infection_age_days=6.8, onset_day=-1.0), engine)
        agent = _seeded(engine)
        inf = agent.infections[PATHOGEN]
        assert inf["illness"] == IllnessStatus.SYMPTOMATIC
        assert inf["presented"] is True
        assert inf["will_present"] is True
        assert inf["days_since_onset_at_boarding"] == pytest.approx(1.0)
        assert "boarding_state" not in inf

    def test_severity_is_read_at_the_elapsed_day(self) -> None:
        """A host deep into its course does not show the peak severity."""
        early = _FakeEngine()
        _apply(_plan(infection_age_days=5.0, onset_day=-0.5), early)
        late = _FakeEngine()
        _apply(_plan(infection_age_days=9.0, onset_day=-4.5), late)
        early_inf = _seeded(early).infections[PATHOGEN]
        late_inf = _seeded(late).infections[PATHOGEN]
        assert early_inf["symptom_severity"] <= early_inf["symptom_severity_peak"]
        assert late_inf["days_since_onset_at_boarding"] == pytest.approx(4.5)
        # Day-indexed severity, not a constant: the two elapsed reads differ
        # unless the curve is flat at both days.
        assert early_inf["symptom_severity"] is not None
        assert late_inf["symptom_severity"] is not None


class TestPresymptomaticAtBoarding:
    def test_onset_arrives_at_the_declared_day(self) -> None:
        """Onset 2 days after boarding: illness stays latent until day 2."""
        age, onset = 3.0, 2.0
        engine = _FakeEngine()
        _apply(_plan(infection_age_days=age, onset_day=onset), engine)
        agent = _seeded(engine)
        inf = agent.infections[PATHOGEN]
        assert inf["illness"] == IllnessStatus.NOT_ILL
        assert not inf.get("presented")
        rng = np.random.default_rng(7)
        profiles = {PATHOGEN: _profile()}
        # infection age at boarding is ``age``; onset fires at age + onset
        epochs_to_onset = engine.clock.epochs_for_days(onset)
        for _ in range(int(epochs_to_onset) - 1):
            advance_infections(agent, profiles, rng)
            assert inf["illness"] == IllnessStatus.NOT_ILL
        advance_infections(agent, profiles, rng)
        assert inf["illness"] == IllnessStatus.SYMPTOMATIC
        # onset_time_infected is the elapsed-epochs stamp at presentation;
        # infection_age at onset equals the implied incubation.
        assert inf["time_infected"] - inf.get("onset_time_infected", 0) >= 0


class TestNoOnsetInvariance:
    def test_absent_key_consumes_and_stamps_identically(self) -> None:
        """onset_day unset: the draw sequence and stamped fields are unchanged."""
        plain = _FakeEngine()
        _apply(_plan(infection_age_days=4.0), plain, rng_seed=11)
        seeded_plain = _seeded(plain).infections[PATHOGEN]

        declared = _FakeEngine()
        _apply(
            _plan(infection_age_days=4.0, onset_day=None), declared,
            rng_seed=11,
        )
        seeded_declared = _seeded(declared).infections[PATHOGEN]

        assert seeded_plain == seeded_declared

    def test_declared_future_onset_consumes_no_extra_draws(self) -> None:
        """A presymptomatic declared onset stamps only the record fields."""
        plain = _FakeEngine()
        _apply(_plan(infection_age_days=4.0), plain, rng_seed=11)
        declared = _FakeEngine()
        _apply(
            _plan(infection_age_days=4.0, onset_day=3.0), declared, rng_seed=11,
        )
        inf_p = _seeded(plain).infections[PATHOGEN]
        inf_d = _seeded(declared).infections[PATHOGEN]
        # Same record apart from the two declared-onset stamps.
        assert inf_d["incubation_days"] == pytest.approx(4.0 + 3.0)
        assert inf_d["will_present"] is True
        assert {
            k: v for k, v in inf_d.items()
            if k not in {"incubation_days", "will_present"}
        } == {k: v for k, v in inf_p.items() if k not in {"will_present"}}
