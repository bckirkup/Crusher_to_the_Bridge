"""Immunocompromise acts on shedding duration, never on acquisition.

The susceptibility multiplier is withdrawn; what remains is a per-host chronic
shedding duration drawn at initialization for immunocompromised hosts, on
profiles that carry the chronic keys.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np
import pytest

from engines.infection_dynamics_bridge import (
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
)
from engines.sim_clock import HOURS, SimClock
from orchestrator_epoch import _advance_agent_pathogen_infections
from orchestrator_init import _draw_chronic_duration, init_multi_pathogen
from tools.sanity_checker import Report, _check_multi_pathogen_params

REPO_ROOT = Path(__file__).resolve().parent.parent

PATHOGEN = "norwalk_gi"
ZONE = "Cabin_A"
ONSET_DAYS = 1.0
RECOVERY_DAYS = 3
SHEDDING_DAYS = 15.0
CHRONIC_MEDIAN = 218.0
CHRONIC_MIN = 32.0
CHRONIC_MAX = 1164.0
CHRONIC_SIGMA_LOG = 1.09
CHRONIC_FRACTION = 0.228
COHORT_SIZE = 200
SYMPTOMATIC_CURVE = [11.0 - 0.1 * index for index in range(15)]
ASYMPTOMATIC_CURVE = [7.0] * 15

CHRONIC_SPEC = {
    "median": CHRONIC_MEDIAN,
    "min": CHRONIC_MIN,
    "max": CHRONIC_MAX,
    "sigma_log": CHRONIC_SIGMA_LOG,
}


def _clock() -> SimClock:
    return SimClock(epoch_duration_hours=6.0, mode=HOURS)


def _new_agent(agent_id: int) -> KorkinAgent:
    return KorkinAgent(
        agent_id=agent_id,
        role="passenger",
        immune=False,
        home_zone=ZONE,
        dining_zone=ZONE,
        work_zone=ZONE,
        free_zone=ZONE,
        schedule=["Free"] * 4,
    )


class _FakeEngine:
    """Minimal engine surface used by ``init_multi_pathogen``."""

    def __init__(self, size: int = COHORT_SIZE) -> None:
        self.agents = [_new_agent(index) for index in range(size)]
        self.clock = _clock()

    def initialize_pathogen(self, _pid: str) -> None:
        return None


def _init_profile(**overrides: Any) -> dict[str, Any]:
    """A profile that skips seeding, so only the host draws are exercised."""
    profile: dict[str, Any] = {
        "base_susceptibility": 1.0,
        "secretor_negative_fraction": 0.20,
        "secretor_negative_relative_susceptibility": 0.20,
        "introduction_epoch": 1,
        "chronic_shedder_fraction": CHRONIC_FRACTION,
        "chronic_shedding_duration_days": dict(CHRONIC_SPEC),
    }
    profile.update(overrides)
    return profile


def _run_init(
    profile: dict[str, Any], *, seed: int = 11, imm_fraction: float = 1.0,
) -> tuple[_FakeEngine, set[int], np.random.Generator]:
    engine = _FakeEngine()
    cfg = {"multi_pathogen": {"immunocompromised_fraction": imm_fraction}}
    rng = np.random.default_rng(seed)
    ids = init_multi_pathogen(engine, {PATHOGEN: profile}, cfg, rng)
    return engine, ids, rng


def _chronic_durations(engine: _FakeEngine) -> dict[int, float]:
    return {
        agent.agent_id: duration
        for agent in engine.agents
        if (duration := agent.get_chronic_shedding_duration(PATHOGEN))
        is not None
    }


def _clearance_profile(**overrides: Any) -> dict[str, Any]:
    profile: dict[str, Any] = {
        "recovery_day": RECOVERY_DAYS,
        "shedding_duration_days": SHEDDING_DAYS,
        "symptom_onset_day": ONSET_DAYS,
        "shedding_curve_log10": list(SYMPTOMATIC_CURVE),
        "asymptomatic_shedding_log10": list(ASYMPTOMATIC_CURVE),
        "environmental_faecal_release_log10_g_per_epoch": 0.0,
        "presymptomatic_shedding_days": 0.5,
        "illness_probability": {"eta": 0.0, "gamma": 0.095},
    }
    profile.update(overrides)
    return profile


def _infected_host(*, chronic_days: float | None) -> KorkinAgent:
    agent = _new_agent(1)
    agent.clock = _clock()
    agent.current_location = ZONE
    agent.immunocompromised = True
    if chronic_days is not None:
        agent.set_chronic_shedding_duration(PATHOGEN, chronic_days)
    agent.infect_with_pathogen(PATHOGEN, 1e4, 0, time_infected=0)
    infection = agent.infections[PATHOGEN]
    infection["incubation_days"] = ONSET_DAYS
    infection["illness"] = IllnessStatus.SYMPTOMATIC
    infection["presented"] = True
    infection["onset_time_infected"] = round(
        ONSET_DAYS * agent.clock.epochs_per_day,
    )
    return agent


@dataclass(frozen=True)
class _Sample:
    days: float
    status: InfectionStatus
    illness: IllnessStatus
    shedding: float


def _run(
    agent: KorkinAgent, profile: dict[str, Any], horizon_days: float,
) -> list[_Sample]:
    """Step the real progression seam and sample state once per epoch."""
    rng = np.random.default_rng(7)
    clock = agent.clock
    trace: list[_Sample] = []
    for epoch in range(round(horizon_days * clock.epochs_per_day)):
        infection = agent.infections[PATHOGEN]
        trace.append(_Sample(
            days=clock.days_elapsed(infection["time_infected"] or 0),
            status=infection["status"],
            illness=infection["illness"],
            shedding=agent.get_pathogen_shedding(PATHOGEN, profile),
        ))
        _advance_agent_pathogen_infections(
            agent, {PATHOGEN: profile}, rng, epoch=epoch,
        )
    return trace


def _at_day(trace: list[_Sample], day: float) -> _Sample:
    matches = [sample for sample in trace if sample.days >= day]
    assert matches, f"trace never reached day {day}"
    return matches[0]


class TestWithdrawnMultiplier:
    def test_immunocompromise_does_not_scale_susceptibility(self) -> None:
        engine, ids, _ = _run_init(_init_profile(), imm_fraction=0.5)
        assert ids
        by_secretor: dict[bool, set[int]] = {True: set(), False: set()}
        for agent in engine.agents:
            secretor_negative = agent.secretor_negative_by_pathogen[PATHOGEN]
            by_secretor[bool(secretor_negative)].add(agent.agent_id)
        assert by_secretor[True]
        assert by_secretor[False]

        for secretor_negative, agent_ids in by_secretor.items():
            expected = 0.20 if secretor_negative else 1.0
            for agent_id in agent_ids:
                agent = engine.agents[agent_id]
                assert agent.susceptibility_multiplier[PATHOGEN] == (
                    pytest.approx(expected)
                )

    def test_immunocompromised_hosts_are_still_flagged(self) -> None:
        engine, ids, _ = _run_init(_init_profile(), imm_fraction=0.5)
        flagged = {a.agent_id for a in engine.agents if a.immunocompromised}
        assert flagged == ids


class TestSanityCheckerBranches:
    def test_setting_the_withdrawn_multiplier_warns(self) -> None:
        report = Report()
        _check_multi_pathogen_params(
            {"multi_pathogen": {"immunocompromised_multiplier": 2.0}}, report,
        )
        assert report.passed
        assert len(report.warnings) == 1
        assert "refuted" in report.warnings[0].message

    def test_fraction_outside_the_sourced_interval_is_advisory(self) -> None:
        report = Report()
        _check_multi_pathogen_params(
            {"multi_pathogen": {"immunocompromised_fraction": 0.10}}, report,
        )
        assert report.passed
        assert len(report.warnings) == 1

    def test_shipped_fraction_is_silent(self) -> None:
        report = Report()
        _check_multi_pathogen_params(
            {"multi_pathogen": {"immunocompromised_fraction": 0.05}}, report,
        )
        assert report.passed
        assert not report.warnings

    def test_fraction_out_of_bounds_still_errors(self) -> None:
        report = Report()
        _check_multi_pathogen_params(
            {"multi_pathogen": {"immunocompromised_fraction": 1.5}}, report,
        )
        assert not report.passed


class TestChronicAssignmentSensitivity:
    def test_chronic_fraction_grades_the_chronic_count(self) -> None:
        counts = []
        for fraction in (0.0, CHRONIC_FRACTION, 1.0):
            engine, ids, _ = _run_init(
                _init_profile(chronic_shedder_fraction=fraction),
            )
            assert len(ids) == COHORT_SIZE
            counts.append(len(_chronic_durations(engine)))

        assert counts[0] == 0
        assert counts[-1] == COHORT_SIZE
        assert counts == sorted(counts)
        assert counts[1] > 0
        assert counts[1] < COHORT_SIZE

    def test_profile_without_the_chronic_keys_assigns_nothing(self) -> None:
        with (REPO_ROOT / "data" / "pathogens" / "active_profiles.json").open(
            encoding="utf-8",
        ) as handle:
            profiles = json.load(handle)["pathogens"]
        shipped = next(
            profile for profile in profiles
            if profile["pathogen_id"] == "sars_cov2_resp"
        )
        assert "chronic_shedder_fraction" not in shipped
        assert "chronic_shedding_duration_days" not in shipped

        covid = dict(shipped)
        covid["introduction_epoch"] = 1
        engine = _FakeEngine()
        cfg = {"multi_pathogen": {"immunocompromised_fraction": 1.0}}
        init_multi_pathogen(
            engine, {"sars_cov2_resp": covid}, cfg, np.random.default_rng(3),
        )
        assert all(
            agent.get_chronic_shedding_duration("sars_cov2_resp") is None
            for agent in engine.agents
        )


class TestChronicDurationBounds:
    def test_draws_stay_inside_the_reported_range(self) -> None:
        rng = np.random.default_rng(5)
        draws = [_draw_chronic_duration(dict(CHRONIC_SPEC), rng)
                 for _ in range(400)]
        assert min(draws) >= CHRONIC_MIN
        assert max(draws) <= CHRONIC_MAX

    def test_sample_median_tracks_the_reported_median(self) -> None:
        rng = np.random.default_rng(5)
        draws = [_draw_chronic_duration(dict(CHRONIC_SPEC), rng)
                 for _ in range(400)]
        # Truncation to [32, 1164] pulls the sample median slightly in; a 25%
        # band is a consistency check on sigma_log, not a golden value.
        assert median(draws) == pytest.approx(CHRONIC_MEDIAN, rel=0.25)


class TestChronicClearance:
    def test_chronic_host_sheds_past_the_profile_duration(self) -> None:
        trace = _run(
            _infected_host(chronic_days=CHRONIC_MEDIAN),
            _clearance_profile(),
            104.0,
        )
        for day in (30.0, 100.0):
            sample = _at_day(trace, ONSET_DAYS + day)
            assert sample.shedding > 0.0
            assert sample.status == InfectionStatus.INFECTED

    def test_chronic_host_illness_still_clears_on_the_illness_clock(
        self,
    ) -> None:
        trace = _run(
            _infected_host(chronic_days=CHRONIC_MEDIAN),
            _clearance_profile(),
            10.0,
        )
        epoch_days = 1.0 / _clock().epochs_per_day
        recovered = [
            sample for sample in trace
            if sample.illness == IllnessStatus.RECOVERED
        ]
        assert recovered
        assert recovered[0].days >= ONSET_DAYS + RECOVERY_DAYS
        assert recovered[0].days < ONSET_DAYS + RECOVERY_DAYS + epoch_days

    def test_non_chronic_immunocompromised_host_clears_with_the_profile(
        self,
    ) -> None:
        immunocompromised = _run(
            _infected_host(chronic_days=None), _clearance_profile(), 20.0,
        )
        baseline_host = _infected_host(chronic_days=None)
        baseline_host.immunocompromised = False
        baseline = _run(baseline_host, _clearance_profile(), 20.0)

        def clearance_day(trace: list[_Sample]) -> float:
            recovered = [
                sample for sample in trace
                if sample.status == InfectionStatus.RECOVERED
            ]
            assert recovered
            return recovered[0].days

        assert clearance_day(immunocompromised) == pytest.approx(
            ONSET_DAYS + SHEDDING_DAYS, abs=0.3,
        )
        assert clearance_day(immunocompromised) == pytest.approx(
            clearance_day(baseline),
        )


class TestReproducibility:
    def test_same_seed_gives_the_same_chronic_assignment(self) -> None:
        first, _, _ = _run_init(_init_profile(), seed=29)
        second, _, _ = _run_init(_init_profile(), seed=29)
        assert _chronic_durations(first) == _chronic_durations(second)

    def test_chronic_draws_do_not_rebase_the_shared_stream(self) -> None:
        with_keys = _init_profile()
        without_keys = _init_profile()
        without_keys.pop("chronic_shedder_fraction")
        without_keys.pop("chronic_shedding_duration_days")

        engine_with, _, rng_with = _run_init(with_keys, seed=31)
        _, _, rng_without = _run_init(without_keys, seed=31)

        assert _chronic_durations(engine_with)
        assert float(rng_with.random()) == pytest.approx(
            float(rng_without.random()),
        )
