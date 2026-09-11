"""Hand-carriage intermittency: between-host propensity, drawn once.

Liu's 71 hand rinses reject a common per-event contamination rate, so a
host's defecation events are Bernoulli-thinned by a per-host-per-infection
beta-binomial propensity before they reach the hand. The defecation rate
itself stays a physical, declared quantity: ``_stool_event_rate_per_day``
still returns the profile's arm unthinned.
"""

from __future__ import annotations

import numpy as np
import pytest

import engines.transmission_core as transmission_core
from engines.infection_dynamics_bridge import (
    IllnessStatus,
    KorkinAgent,
)
from engines.sim_clock import HOURS, SimClock
from engines.transmission_core import (
    DIARRHOEA_AXIS,
    DIARRHOEAL_STOOL_EVENTS_PER_DAY,
    VOMITING_AXIS,
    TransmissionCore,
)

PATHOGEN = "test_pathogen"
ZONE = "Public_Lounge"
# Any carried copies on the hand count as detectable carriage.
DETECTION_LOAD = 1.0

PHASES = [
    {"name": "acute", "dpi_min": 0, "dpi_max": 2,
     "features": ["vomiting", "watery_diarrhea"]},
    {"name": "resolving", "dpi_min": 3, "dpi_max": None,
     "features": ["watery_diarrhea"]},
]


def _profile(**overrides: object) -> dict:
    profile: dict[str, object] = {
        "shedding_curve_log10": [11.0] * 12,
        "asymptomatic_shedding_log10": [10.5] * 12,
        "symptom_onset_day": 0.0,
        "recovery_day": 3,
        "dose_response": {"model": "exponential", "k": 0.01},
        "hand_inactivation_rate_per_hour": 0.61,
        "hand_hygiene_rate_per_hour": 0.0,
        "clinical_presentation": {"phases": PHASES},
        "stool_events_per_day": {
            "baseline": 1.0,
            "diarrhoeal": DIARRHOEAL_STOOL_EVENTS_PER_DAY,
        },
    }
    profile.update(overrides)
    return profile


def _agent(agent_id: int = 1) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=agent_id,
        role="passenger",
        immune=False,
        home_zone=ZONE,
        dining_zone=ZONE,
        work_zone=ZONE,
        free_zone=ZONE,
        schedule=["Free"] * 24,
    )
    agent.current_location = ZONE
    agent.infect_with_pathogen(PATHOGEN, 1.0, 0, time_infected=24)
    inf = agent.infections[PATHOGEN]
    inf["illness"] = IllnessStatus.SYMPTOMATIC
    inf["presented"] = True
    inf["symptom_axes"] = {VOMITING_AXIS: True, DIARRHOEA_AXIS: True}
    return agent


def _core(
    *,
    profile: dict | None = None,
    seed: int = 7,
) -> TransmissionCore:
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={ZONE: 50.0},
        pathogen_profiles={PATHOGEN: profile or _profile()},
        zone_types={ZONE: "Free"},
        clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
    )
    core.initialize_zones([ZONE])
    return core


def _beta_with_mean(mean: float, total: float = 4.4) -> tuple[float, float]:
    """(a, b) with the shipped concentration and a moved mean."""
    return mean * total, (1.0 - mean) * total


def _occupancy(core: TransmissionCore, agent: KorkinAgent, days: float = 3.0) -> float:
    """Fraction of epochs the host's hand carries a detectable load."""
    epochs = int(days * 24)
    hits = 0
    for _ in range(epochs):
        core._replenish_hand(agent, PATHOGEN, core.pathogen_profiles[PATHOGEN])
        if agent.hand_load_by_pathogen.get(PATHOGEN, 0.0) > DETECTION_LOAD:
            hits += 1
    return hits / epochs


class TestSensitivity:
    """The propensity's mean is a live knob on mean hand load."""

    def test_mean_hand_load_tracks_the_beta_mean(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        means = []
        for target_mean in (0.05, 0.207, 0.8):
            monkeypatch.setattr(
                transmission_core, "HAND_CARRIAGE_PROPENSITY_BETA",
                _beta_with_mean(target_mean),
            )
            loads = []
            for host_id in range(150):
                core = _core(seed=1000 + host_id)
                agent = _agent()
                series = []
                for _ in range(72):
                    core._replenish_hand(
                        agent, PATHOGEN, core.pathogen_profiles[PATHOGEN],
                    )
                    series.append(agent.hand_load_by_pathogen[PATHOGEN])
                loads.append(float(np.mean(series)))
            means.append(float(np.mean(loads)))
        assert means == sorted(means)
        assert means[2] > 3.0 * means[0]


class TestHeterogeneity:
    """Per-host propensity produces dispersion a common rate cannot."""

    def test_between_host_variance_exceeds_the_binomial_floor(self) -> None:
        core = _core(seed=2024)
        occupancies = [
            _occupancy(core, _agent(host_id)) for host_id in range(300)
        ]
        between = float(np.var(occupancies))
        # Under a common per-event rate every host shares one occupancy
        # probability; the between-host variance is then binomial noise in
        # the finite window, of order p(1-p)/epochs.
        binomial_floor = 0.25 / 72.0
        assert between > 5.0 * binomial_floor

    def test_a_band_of_hosts_never_carries(self) -> None:
        core = _core(seed=777)
        never = 0
        for host_id in range(300):
            if _occupancy(core, _agent(host_id)) == 0.0:
                never += 1
        fraction = never / 300
        # Liu: 2/6 infected hosts never hand-positive; the fitted beta gives
        # ~10-33% effectively never carrying. A band, not a point.
        assert 0.05 < fraction < 0.50


class TestPersistence:
    """The draw is once per host per infection."""

    def test_propensity_is_drawn_once_and_cached(self) -> None:
        core = _core(seed=11)
        agent = _agent()
        first = core._hand_carriage_propensity(agent, PATHOGEN)
        again = core._hand_carriage_propensity(agent, PATHOGEN)
        assert again == pytest.approx(first, rel=0.0, abs=0.0)
        assert agent.hand_carriage_propensity_by_pathogen[PATHOGEN] == first

    def test_a_fresh_infection_redraws(self) -> None:
        core = _core(seed=11)
        agent = _agent()
        core._hand_carriage_propensity(agent, PATHOGEN)
        assert PATHOGEN in agent.hand_carriage_propensity_by_pathogen
        agent.infect_with_pathogen(PATHOGEN, 1.0, 0, time_infected=0)
        # The cache is cleared on reinfection; the next call draws anew.
        assert PATHOGEN not in agent.hand_carriage_propensity_by_pathogen
        redrawn = core._hand_carriage_propensity(agent, PATHOGEN)
        assert agent.hand_carriage_propensity_by_pathogen[PATHOGEN] == redrawn

    def test_the_accessor_still_reports_the_declared_defecation_rate(
        self,
    ) -> None:
        """The stool-event accessor's contract is preserved by construction:
        it returns defecation frequency, and the carriage propensity never
        enters it."""
        core = _core(seed=3)
        agent = _agent()
        # Prime the propensity cache, then ask for the rate.
        core._hand_carriage_propensity(agent, PATHOGEN)
        assert core._stool_event_rate_per_day(agent, PATHOGEN, _profile()) == (
            DIARRHOEAL_STOOL_EVENTS_PER_DAY
        )


class TestBounds:
    def test_propensity_lies_in_the_unit_interval_and_thins_down(self) -> None:
        core = _core(seed=41)
        declared = DIARRHOEAL_STOOL_EVENTS_PER_DAY
        for host_id in range(200):
            agent = _agent(host_id)
            propensity = core._hand_carriage_propensity(agent, PATHOGEN)
            assert np.isfinite(propensity)
            assert 0.0 < propensity < 1.0
            thinned = declared * propensity
            assert 0.0 <= thinned <= declared


class TestControls:
    """The continuous-relaxation arm does not touch the new mechanism."""

    def test_continuous_arm_is_bit_identical(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        profile = _profile()
        del profile["stool_events_per_day"]
        agent_a = _agent()
        agent_b = _agent()
        core_a = _core(profile=profile, seed=97)
        core_b = _core(profile=profile, seed=97)
        # A degenerate beta would draw ~1.0 every time; the continuous arm
        # must never consult it, so the trajectory cannot differ.
        monkeypatch.setattr(
            transmission_core, "HAND_CARRIAGE_PROPENSITY_BETA", (1.0e9, 1.0e-9),
        )
        for _ in range(48):
            core_a._replenish_hand(agent_a, PATHOGEN, profile)
        monkeypatch.undo()
        for _ in range(48):
            core_b._replenish_hand(agent_b, PATHOGEN, profile)
        assert agent_b.hand_load_by_pathogen[PATHOGEN] == (
            agent_a.hand_load_by_pathogen[PATHOGEN]
        )
        assert PATHOGEN not in agent_a.hand_carriage_propensity_by_pathogen
        assert PATHOGEN not in agent_b.hand_carriage_propensity_by_pathogen

    def test_propensity_near_zero_means_a_decaying_never_carrying_hand(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            transmission_core, "HAND_CARRIAGE_PROPENSITY_BETA",
            (1.0e-6, 1.0e6),
        )
        core = _core(seed=5)
        agent = _agent()
        agent.hand_load_by_pathogen[PATHOGEN] = 1.0e3
        loads = []
        for _ in range(72):
            core._replenish_hand(
                agent, PATHOGEN, core.pathogen_profiles[PATHOGEN],
            )
            loads.append(agent.hand_load_by_pathogen[PATHOGEN])
        # Never recontaminates: monotone decay toward zero.
        assert all(b <= a for a, b in zip(loads, loads[1:], strict=False))
        assert loads[-1] < 1.0e-6
