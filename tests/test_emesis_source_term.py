"""Invariant checks for the emesis source term against Kirby et al. 2016.

The retired source term drew a per-subject cumulative shed and partitioned
it equally over a uniform episode count, inverting Fig 1's measured
count/cumulative relation and capping every subject below the paper's own
measured means. The shipped structure is host titre x per-episode volume
with a below-LOD censored arm. These tests check the measured invariants of
that structure, not pinned totals -- the per-subject cumulative is a
validated output, not an input.
"""

from __future__ import annotations

import numpy as np
import pytest

from engines.infection_dynamics_bridge import IllnessStatus, KorkinAgent
from engines.sim_clock import HOURS, SimClock
from engines.transmission_core import (
    EMESIS_CENSORED_TITRE_GEC_PER_ML_RANGE,
    EMESIS_EPISODES_RANGE,
    EMESIS_SINGLE_EPISODE_FRACTION,
    EMESIS_TITRE_GEC_PER_ML_RANGE,
    TransmissionCore,
    draw_emesis_schedule,
    emesis_episode_weights,
)

PATHOGEN = "norwalk_gi"
ZONE = "Cabin_A"
ILLNESSES = 4000


def _profile(**overrides: object) -> dict:
    profile: dict[str, object] = {
        "symptom_onset_day": 0.0,
        "recovery_day": 5,
        "clinical_presentation": {
            "phases": [
                {
                    "name": "acute",
                    "dpi_min": 0,
                    "dpi_max": 2,
                    "features": ["vomiting"],
                },
                {
                    "name": "resolving",
                    "dpi_min": 3,
                    "dpi_max": None,
                    "features": ["watery_diarrhea"],
                },
            ],
        },
        "shedding_curve_log10": [11.0] * 12,
        "asymptomatic_shedding_log10": [11.0] * 12,
        "dose_response": {"model": "exponential", "k": 0.01},
    }
    profile.update(overrides)
    return profile


def _agent() -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=1,
        role="passenger",
        immune=False,
        home_zone=ZONE,
        dining_zone=ZONE,
        work_zone=ZONE,
        free_zone=ZONE,
        schedule=["Free"] * 24,
    )
    agent.current_location = ZONE
    agent.infect_with_pathogen(PATHOGEN, 1.0, 0, time_infected=0)
    agent.infections[PATHOGEN]["onset_time_infected"] = 0
    agent.infections[PATHOGEN]["illness"] = IllnessStatus.SYMPTOMATIC
    agent.infections[PATHOGEN]["symptom_axes"] = {
        "vomiting": True, "diarrhoea": True,
    }
    return agent


def _core(seed: int = 11, **kwargs: object) -> TransmissionCore:
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={ZONE: 50.0},
        pathogen_profiles={PATHOGEN: _profile()},
        zone_types={ZONE: "Cabin_Corridor"},
        clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
        **kwargs,
    )
    core.initialize_zones([ZONE])
    return core


def _drawn_illness(
    rng: np.random.Generator, profile: dict,
) -> tuple[KorkinAgent, int, float]:
    """One drawn illness: agent, episode count, host titre."""
    agent = _agent()
    draw_emesis_schedule(agent, PATHOGEN, profile, rng)
    count = len(agent.emesis_episode_schedule_by_pathogen[PATHOGEN])
    titre = agent.emesis_titre_gec_per_ml_by_pathogen[PATHOGEN]
    return agent, count, titre


def _emit_all(
    core: TransmissionCore, agent: KorkinAgent, profile: dict,
) -> list[dict]:
    """Fire every scheduled episode and return the deposition records."""
    agent.clock = core.clock
    for epoch in range(round(3.0 * core.clock.epochs_per_day) + 1):
        agent.infections[PATHOGEN]["time_infected"] = epoch
        core._deposit_emesis(agent, PATHOGEN, ZONE, epoch, profile)
    return agent.emesis_deposition_records_by_pathogen.get(PATHOGEN, [])


class TestEpisodeCountDistribution:
    """The count is a truncated geometric solved to the measured 32% mode."""

    def test_weights_solve_the_measured_single_episode_fraction(self) -> None:
        weights = emesis_episode_weights(*EMESIS_EPISODES_RANGE)
        assert weights[0] == pytest.approx(
            EMESIS_SINGLE_EPISODE_FRACTION, abs=1e-6,
        )
        assert len(weights) == EMESIS_EPISODES_RANGE[1]
        assert weights == tuple(sorted(weights, reverse=True))
        assert sum(weights) == pytest.approx(1.0)

    def test_drawn_counts_match_the_measured_share(self) -> None:
        rng = np.random.default_rng(5)
        profile = _profile()
        counts = [
            _drawn_illness(rng, profile)[1] for _ in range(ILLNESSES)
        ]
        low, high = EMESIS_EPISODES_RANGE
        assert min(counts) >= low
        assert max(counts) <= high
        singles = counts.count(1) / len(counts)
        # ~4 binomial SE at n=4000
        assert singles == pytest.approx(0.32, abs=0.03)
        modes = [counts.count(k) for k in range(low, high + 1)]
        assert modes[0] == max(modes)


class TestFigOneDirection:
    """Cumulative shed rises with episode count -- the old code inverted it."""

    def test_cumulative_shed_is_non_decreasing_in_episode_count(self) -> None:
        rng = np.random.default_rng(13)
        profile = _profile()
        volumes: dict[int, list[float]] = {k: [] for k in range(1, 8)}
        for _ in range(ILLNESSES):
            agent, count, titre = _drawn_illness(rng, profile)
            # E[cumulative | K] = titre x K x E[volume]; record the drawn
            # titre-weighted count so volume noise is not simulated twice.
            volumes[count].append(titre * count)
        means = [
            float(np.mean(volumes[k])) for k in sorted(volumes) if volumes[k]
        ]
        assert means == sorted(means)
        assert means[-1] > means[0] * 2.0


_KIRBY_SIMULATION: tuple[float, float] | None = None


def _kirby_simulation(illnesses: int = 1500) -> tuple[float, float]:
    """One simulated sample shared by both SEM-bracket assertions."""
    global _KIRBY_SIMULATION
    if _KIRBY_SIMULATION is not None:
        return _KIRBY_SIMULATION
    rng = np.random.default_rng(97)
    profile = _profile()
    totals: list[float] = []
    volume_totals: list[float] = []
    for i in range(illnesses):
        # Fresh core seed per subject so the per-episode volume draws
        # are independent across the sample.
        core = _core(seed=3000 + i)
        agent, _, _ = _drawn_illness(rng, profile)
        records = _emit_all(core, agent, profile)
        totals.append(sum(r["episode_load"] for r in records))
        volume_totals.append(sum(r["volume_ml"] for r in records))
    _KIRBY_SIMULATION = (
        float(np.mean(totals)), float(np.mean(volume_totals)),
    )
    return _KIRBY_SIMULATION


class TestKirbyMeasuredMeans:
    """The generated distribution lands inside Kirby's own SEM brackets."""

    def test_per_subject_cumulative_shed_within_two_sem(self) -> None:
        mean_total, _ = _kirby_simulation()
        # Overall 1.8e8 +/- 7.8e7 and All GI 2.3e8 +/- 1.0e8, 2 SEM each.
        assert 2.4e7 <= mean_total <= 3.4e8
        assert 3.0e7 <= mean_total <= 4.3e8

    def test_per_subject_total_volume_within_two_sem(self) -> None:
        _, mean_volume = _kirby_simulation()
        # All GI 658.7 +/- 111.9 mL and GII.2 845.0 +/- 226.7 mL, 2 SEM each.
        assert 434.9 <= mean_volume <= 882.5
        assert 391.6 <= mean_volume <= 1298.4


class TestCensoring:
    """Below-LOD illnesses emit real, bounded mass -- never a zero."""

    def _illness_at_count(self, count: int) -> tuple[dict, dict]:
        rng = np.random.default_rng(29)
        profile = _profile()
        while True:
            agent, drawn, _ = _drawn_illness(rng, profile)
            if drawn == count:
                break
        records = _emit_all(_core(), agent, profile)
        # An episode drawn in the tail of the emetic window can outlive the
        # phase and legitimately never emit; require the bulk through.
        assert 0 < len(records) <= count
        return records[0], {
            "titre": agent.emesis_titre_gec_per_ml_by_pathogen[PATHOGEN],
            "censored": agent.emesis_censored_below_lod_by_pathogen[PATHOGEN],
        }

    def test_single_episode_host_is_censored_but_positive(self) -> None:
        record, illness = self._illness_at_count(1)
        assert illness["censored"] is True
        assert record["censored_below_lod"] is True
        lo, hi = EMESIS_CENSORED_TITRE_GEC_PER_ML_RANGE
        assert lo <= record["titre_gec_per_ml"] <= hi
        # Below Ge et al. 2023's stated 1.5e4 GEC/g challenge-study LOD.
        assert record["titre_gec_per_ml"] <= 1.5e4
        assert record["episode_load"] > 0.0

    def test_many_episode_host_is_detectable(self) -> None:
        record, illness = self._illness_at_count(5)
        assert illness["censored"] is False
        assert record["censored_below_lod"] is False
        lo, hi = EMESIS_TITRE_GEC_PER_ML_RANGE
        assert lo <= record["titre_gec_per_ml"] <= hi


class TestConservationAndBounds:
    def test_episode_mass_conserves_and_sums_over_an_illness(self) -> None:
        rng = np.random.default_rng(53)
        profile = _profile()
        while True:
            agent, count, _ = _drawn_illness(rng, profile)
            if count >= 3:
                break
        records = _emit_all(_core(), agent, profile)
        assert 0 < len(records) <= count
        for record in records:
            parts = (
                record["pool_gain"]
                + record["non_touchable"]
                + record["aerosol_load"]
            )
            assert parts == pytest.approx(record["episode_load"], rel=1e-12)
            assert record["episode_load"] == pytest.approx(
                record["volume_ml"] * record["titre_gec_per_ml"], rel=1e-12,
            )

    def test_interval_endpoints_stay_finite_and_non_negative(self) -> None:
        rng = np.random.default_rng(61)
        for titre_range, censored_range in (
            (EMESIS_TITRE_GEC_PER_ML_RANGE, EMESIS_CENSORED_TITRE_GEC_PER_ML_RANGE),
            ((EMESIS_TITRE_GEC_PER_ML_RANGE[0],) * 2,
             (EMESIS_CENSORED_TITRE_GEC_PER_ML_RANGE[0],) * 2),
            ((EMESIS_TITRE_GEC_PER_ML_RANGE[1],) * 2,
             (EMESIS_CENSORED_TITRE_GEC_PER_ML_RANGE[1],) * 2),
        ):
            profile = _profile(
                emesis_titre_gec_per_ml_range=list(titre_range),
                emesis_censored_titre_gec_per_ml_range=list(censored_range),
            )
            for _ in range(60):
                agent, count, _ = _drawn_illness(rng, profile)
                records = _emit_all(_core(), agent, profile)
                assert len(records) <= count
                for record in records:
                    for value in record.values():
                        if isinstance(value, float):
                            assert np.isfinite(value)
                            assert value >= 0.0


class TestGradedSensitivity:
    """Different titre/volume intervals produce correspondingly different
    deposits, swab readings, and tank concentrations."""

    def _deposit_with(
        self, rng_seed: int, titre: float, **profile_overrides: object,
    ) -> dict:
        profile = _profile(
            emesis_titre_gec_per_ml_range=[titre, titre],
            emesis_censored_titre_gec_per_ml_range=[titre, titre],
            **profile_overrides,
        )
        rng = np.random.default_rng(rng_seed)
        while True:
            agent, count, _ = _drawn_illness(rng, profile)
            if count >= 1:
                break
        records = _emit_all(_core(seed=rng_seed), agent, profile)
        assert records
        return records[0]

    def test_titre_interval_grades_the_deposit(self) -> None:
        low = self._deposit_with(71, 1e4)
        high = self._deposit_with(71, 1e7)
        ratio = high["episode_load"] / low["episode_load"]
        assert ratio == pytest.approx(1e3, rel=0.05)
        assert high["pool_gain"] > low["pool_gain"] * 100.0

    def test_volume_interval_grades_the_deposit(self) -> None:
        small = self._deposit_with(
            73, 1e6, emesis_volume_ml_range=[50.0, 50.0],
        )
        large = self._deposit_with(
            73, 1e6, emesis_volume_ml_range=[800.0, 800.0],
        )
        assert large["episode_load"] / small["episode_load"] == pytest.approx(
            16.0, rel=0.05,
        )

    def test_deposit_reaches_the_swab_and_tank_channels(self) -> None:
        # Higher titre must move the observables the deposit feeds: the
        # surface pool a swab reads and the blackwater tank the assay reads.
        concentrations: dict[float, float] = {}
        for titre in (1e4, 1e6):
            profile = _profile(
                emesis_titre_gec_per_ml_range=[titre, titre],
                emesis_censored_titre_gec_per_ml_range=[titre, titre],
            )
            core = _core(
                seed=81,
                cfg={"transmission": {"blackwater_plumbing": True}},
            )
            agent = _agent()
            agent.emesis_episode_schedule_by_pathogen[PATHOGEN] = [0.0]
            agent.emesis_titre_gec_per_ml_by_pathogen[PATHOGEN] = titre
            agent.emesis_censored_below_lod_by_pathogen[PATHOGEN] = False
            agent.clock = core.clock
            agent.infections[PATHOGEN]["time_infected"] = 0
            core._deposit_emesis(agent, PATHOGEN, ZONE, 0, profile)
            pool = core.zone_surface_mass(ZONE, PATHOGEN)
            assert pool > 0.0
            tank = core.blackwater_tank
            assert tank is not None
            concentrations[titre] = (
                tank.copies_by_pathogen[PATHOGEN] + pool
            )
        assert concentrations[1e6] > concentrations[1e4] * 50.0
