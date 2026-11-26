"""COVID zero-inflated emitted-RNA source shape."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from engines.infection_dynamics_bridge import (
    InfectionStatus,
    KorkinAgent,
    draw_shedding_multiplier,
)
from engines.natural_history import advance_infections
from engines.sim_clock import HOURS, SimClock
from engines.strain_state import Phenotype

PATHOGEN = "sars_cov2_resp"
ZONE = "Cabin_A"


def _clock() -> SimClock:
    return SimClock(epoch_duration_hours=1.0, mode=HOURS)


def _agent(seed: int, profile: dict[str, Any]) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=seed,
        role="passenger",
        immune=False,
        home_zone=ZONE,
        dining_zone=ZONE,
        work_zone=ZONE,
        free_zone=ZONE,
        schedule=["Free"] * 24,
    )
    agent.clock = _clock()
    agent.infect_with_pathogen(
        PATHOGEN,
        1e4,
        0,
        rng=np.random.default_rng(seed),
        profile=profile,
        strain_id="s:index",
        strain_phenotype=Phenotype(),
    )
    return agent


def _shape_profile(probability: float, presymptomatic_days: float = 1.0) -> dict[str, Any]:
    return {
        "presymptomatic_shedding_days": presymptomatic_days,
        "emission_shape": {
            "model": "zero_inflated_daily",
            "axis": "days_since_first_symptom",
            "peak_positive_log10_copies_per_day": 7.0,
            "daily": [
                {
                    "day": -1,
                    "detection_probability": probability,
                    "conditional_positive_relative_shape": 0.5,
                },
                {
                    "day": 0,
                    "detection_probability": 1.0,
                    "conditional_positive_relative_shape": 1.0,
                },
            ],
        },
    }


def _set_age(agent: KorkinAgent, days: float) -> None:
    infection = agent.infections[PATHOGEN]
    infection["incubation_days"] = 1.0
    infection["time_infected"] = round(days * agent.clock.epochs_per_day)


class TestZeroInflatedDailyEmission:
    @pytest.mark.parametrize("probability", [0.0, 0.5, 1.0])
    def test_detection_probability_grades_positive_day_emission(
        self, probability: float,
    ) -> None:
        profile = _shape_profile(probability)
        emissions = []
        for seed in range(80):
            agent = _agent(seed, profile)
            _set_age(agent, 0.0)  # onset-relative day -1
            emissions.append(agent.get_pathogen_shedding(PATHOGEN, profile))

        positive_share = sum(value > 0.0 for value in emissions) / len(emissions)
        if probability == 0.0:
            assert positive_share == pytest.approx(0.0)
        elif probability == 1.0:
            assert positive_share == pytest.approx(1.0)
        else:
            assert 0.3 < positive_share < 0.7
        assert all(np.isfinite(value) for value in emissions)
        assert all(value >= 0.0 for value in emissions)

    def test_positive_conditional_mass_is_reproducible_within_a_day(self) -> None:
        profile = _shape_profile(1.0)
        agent = _agent(7, profile)
        _set_age(agent, 0.0)

        first = agent.get_pathogen_shedding(PATHOGEN, profile)
        second = agent.get_pathogen_shedding(PATHOGEN, profile)

        assert first > 0.0
        assert second == pytest.approx(first, rel=1e-12)
        expected = agent.clock.amount_per_epoch(10.0**7.0 * 0.5)
        assert first == pytest.approx(expected, rel=1e-9)

    def test_presymptomatic_gate_still_bounds_negative_onset_days(self) -> None:
        profile = _shape_profile(1.0, presymptomatic_days=0.5)
        agent = _agent(7, profile)
        _set_age(agent, 0.0)  # onset-relative day -1, outside the 0.5-day gate

        assert agent.get_pathogen_shedding(PATHOGEN, profile) == pytest.approx(0.0)

    def test_negative_onset_day_inside_gate_can_emit(self) -> None:
        profile = _shape_profile(1.0, presymptomatic_days=1.0)
        agent = _agent(7, profile)
        _set_age(agent, 0.0)

        assert agent.get_pathogen_shedding(PATHOGEN, profile) > 0.0


    def test_later_resident_strain_uses_the_declared_virtual_onset_default(self) -> None:
        profile = _shape_profile(1.0, presymptomatic_days=1.0)
        profile["incubation"] = {"median_days": 3.0}
        agent = _agent(7, profile)
        infection = agent.infections[PATHOGEN]
        infection["incubation_days"] = 1.0
        added = agent.superinfect_with_strain(
            PATHOGEN, "s:invader", 3000.0, 0,
            phenotype=Phenotype(),
        )
        assert added
        residents = agent.resident_strains(PATHOGEN)

        initial = agent._shape_resident_positive_masses(
            PATHOGEN, infection, residents,
            profile["emission_shape"], profile,
        )
        assert initial.get("s:index", 0.0) > 0.0
        assert initial.get("s:invader", 0.0) == pytest.approx(0.0)

        for resident in residents.values():
            resident.time_infected = round(2 * agent.clock.epochs_per_day)
        later = agent._shape_resident_positive_masses(
            PATHOGEN, infection, residents,
            profile["emission_shape"], profile,
        )
        assert later.get("s:index", 0.0) == pytest.approx(0.0)
        assert later.get("s:invader", 0.0) > 0.0

    def test_natural_history_keeps_a_promoted_later_strain_on_its_virtual_course(self) -> None:
        profile = {
            **_shape_profile(1.0),
            "incubation": {"median_days": 3.0},
            "recovery_day": 1.0,
            "shedding_duration_days": 1.0,
        }
        agent = _agent(7, profile)
        infection = agent.infections[PATHOGEN]
        infection["incubation_days"] = 1.0
        assert agent.superinfect_with_strain(
            PATHOGEN, "s:invader", 3000.0, 0,
            phenotype=Phenotype(),
        )
        rng = np.random.default_rng(7)

        for _ in range(round(2 * agent.clock.epochs_per_day)):
            advance_infections(agent, {PATHOGEN: profile}, rng)
        residents = agent.resident_strains(PATHOGEN)
        assert "s:index" not in residents
        assert "s:invader" in residents
        assert infection["status"] == InfectionStatus.INFECTED

        for _ in range(round(2 * agent.clock.epochs_per_day)):
            advance_infections(agent, {PATHOGEN: profile}, rng)
        assert agent.resident_strains(PATHOGEN) == {}
        assert infection["status"] == InfectionStatus.RECOVERED

    def test_within_host_replacement_inherits_the_primary_course_role(self) -> None:
        profile = _shape_profile(1.0, presymptomatic_days=1.0)
        profile["incubation"] = {"median_days": 3.0}
        agent = _agent(7, profile)
        infection = agent.infections[PATHOGEN]
        infection["incubation_days"] = 1.0
        assert agent.superinfect_with_strain(
            PATHOGEN, "s:invader", 3000.0, 0,
            phenotype=Phenotype(),
        )

        agent.replace_strain(
            PATHOGEN, "s:index", "s:child", phenotype=Phenotype(),
        )
        residents = agent.resident_strains(PATHOGEN)
        assert residents["s:child"].primary_course
        assert not residents["s:invader"].primary_course

        masses = agent._shape_resident_positive_masses(
            PATHOGEN, infection, residents,
            profile["emission_shape"], profile,
        )
        assert masses.get("s:child", 0.0) > 0.0
        assert masses.get("s:invader", 0.0) == pytest.approx(0.0)

    def test_later_strain_clearance_uses_its_own_virtual_course(self) -> None:
        profile = _shape_profile(1.0)
        agent = _agent(7, profile)
        assert agent.superinfect_with_strain(
            PATHOGEN, "s:invader", 3000.0, 0, phenotype=Phenotype(),
        )
        clearance = {"s:index": 1.0, "s:invader": 2.0}

        for _ in range(round(agent.clock.epochs_per_day)):
            agent.advance_resident_strains(
                PATHOGEN, 1.0,
                shedding_clearance_by_strain=clearance,
            )
        residents = agent.resident_strains(PATHOGEN)
        assert "s:index" not in residents
        assert "s:invader" in residents

    def test_strain_shares_use_the_same_inoculum_weighting_as_shape_emission(self) -> None:
        profile = _shape_profile(1.0)
        agent = _agent(7, profile)
        added = agent.superinfect_with_strain(
            PATHOGEN,
            "s:invader",
            3000.0,
            0,
            phenotype=Phenotype(shedding_multiplier=2.0),
        )
        assert added
        shares = agent.strain_shedding_shares(PATHOGEN, profile)

        index_weight = 10000.0
        invader_weight = 3000.0 * 2.0
        assert shares["s:index"] == pytest.approx(
            index_weight / (index_weight + invader_weight),
        )
        assert shares["s:invader"] == pytest.approx(
            invader_weight / (index_weight + invader_weight),
        )


class TestHighLowEmitterMixture:
    def test_mixture_is_mean_normalized_and_two_valued(self) -> None:
        profile = {
            "shedding_multiplier_mixture": {
                "high_emitter_fraction": 1.0 / 9.0,
                "high_to_low_ratio": 49.142857,
            },
        }
        rng = np.random.default_rng(11)
        draws = np.array([
            draw_shedding_multiplier(rng, profile) for _ in range(5000)
        ])
        unique = np.unique(draws)

        assert len(unique) == 2
        assert max(unique) / min(unique) == pytest.approx(49.142857, rel=1e-6)
        weighted_mean = (
            (1.0 / 9.0) * max(unique) + (8.0 / 9.0) * min(unique)
        )
        assert weighted_mean == pytest.approx(1.0, rel=1e-9)
        assert float(np.mean(draws == max(unique))) == pytest.approx(
            1.0 / 9.0, abs=0.02,
        )


class TestShippedCovidShape:
    def test_shape_preserves_zero_inflated_geometric_mass_contract(self) -> None:
        payload = json.loads(
            (Path(__file__).parent.parent / "data/pathogens/active_profiles.json").read_text(),
        )
        profile = next(
            entry for entry in payload["pathogens"]
            if entry["pathogen_id"] == PATHOGEN
        )
        rows = profile["emission_shape"]["daily"]
        expected_mass = [
            row["detection_probability"] * row["conditional_positive_relative_shape"]
            for row in rows
        ]
        presymptomatic = sum(
            mass for row, mass in zip(rows, expected_mass, strict=True)
            if row["day"] < 0
        )

        assert "shedding_variance_log10" not in profile
        assert "shedding_multiplier_mixture" in profile
        assert presymptomatic / sum(expected_mass) == pytest.approx(
            0.16803798, rel=1e-3,
        )
