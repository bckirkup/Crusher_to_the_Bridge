"""Onset back-dating: a host symptomatic before its first observation keeps
its true onset, not the observation epoch, in both stamp sites.
"""
from __future__ import annotations

import os
import sys

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from crusher_labs.modalities.syndromic import SyndromicSurveillance
from engines.infection_dynamics_bridge import IllnessStatus, KorkinAgent
from engines.sim_clock import HOURS, SimClock
from telemetry_buffer.agent_axes import (
    COMPLIANCE_COMPLIANT,
    INFECTION_INFECTED,
    PRESENTATION_SYMPTOMATIC,
)

PATHOGEN = "norwalk_gi"
HOURLY = SimClock(epoch_duration_hours=1.0, mode=HOURS)


def _agent(aid: int, elapsed: int | None) -> dict:
    infection = {
        "illness": "SYMPTOMATIC",
        "symptom_severity": "moderate",
    }
    if elapsed is not None:
        infection["epochs_since_symptom_onset"] = elapsed
    return {
        "agent_id": aid,
        "infection_state": INFECTION_INFECTED,
        "symptom_presentation": PRESENTATION_SYMPTOMATIC,
        "compliance_status": COMPLIANCE_COMPLIANT,
        "pathogen_infections": {PATHOGEN: infection},
    }


def _modality(**kwargs) -> SyndromicSurveillance:
    return SyndromicSurveillance(
        sick_call_probability=0.0,
        background_noise_rate=0.0,
        noise_categories=[],
        rng=np.random.default_rng(0),
        **kwargs,
    )


class TestBackDatedStamps:
    """Graded: elapsed onset values produce ordered back-dated onsets."""

    def test_both_stamp_sites_back_date_by_the_same_elapsed(self) -> None:
        modality = _modality()
        agents = [
            _agent(1, 0), _agent(2, 5), _agent(3, 48),
        ]
        modality.query_ground_truth({"epoch": 10, "agents": agents})
        for aid, expected in ((1, 10), (2, 5), (3, -38)):
            assert modality._symptom_onset_epoch[aid] == expected
            assert modality._presentation_onset_epoch[aid] == expected

    def test_zero_elapsed_stamps_the_first_seen_epoch(self) -> None:
        """Inertness: no onset age is exactly today's behaviour."""
        modality = _modality()
        modality.query_ground_truth(
            {"epoch": 10, "agents": [_agent(1, 0), _agent(9, None)]},
        )
        assert modality._symptom_onset_epoch[1] == 10
        assert modality._presentation_onset_epoch[1] == 10
        assert modality._symptom_onset_epoch[9] == 10


class TestDetectionDelayGate:
    def test_a_pre_observation_onset_does_not_restart_the_delay(self) -> None:
        modality = SyndromicSurveillance(
            sick_call_probability=1.0,
            background_noise_rate=0.0,
            noise_categories=[],
            detection_delay_epochs=24,
            rng=np.random.default_rng(0),
        )
        seen = modality.query_ground_truth(
            {"epoch": 0, "agents": [_agent(1, 48)]},
        )
        assert 1 in seen["true_positive_ids"]

    def test_a_fresh_onset_still_waits_out_the_delay(self) -> None:
        modality = SyndromicSurveillance(
            sick_call_probability=1.0,
            background_noise_rate=0.0,
            noise_categories=[],
            detection_delay_epochs=24,
            rng=np.random.default_rng(0),
        )
        agent = _agent(1, 0)
        for epoch in range(24):
            seen = modality.query_ground_truth(
                {"epoch": epoch, "agents": [agent]},
            )
            assert seen["true_positive_ids"] == []
        seen = modality.query_ground_truth(
            {"epoch": 24, "agents": [agent]},
        )
        assert 1 in seen["true_positive_ids"]


class TestOnsetObservation:
    def test_a_pre_boarding_onset_records_a_negative_day(self) -> None:
        modality = _modality(clock=HOURLY)
        aid = 7
        modality._lab_confirmed[(PATHOGEN, aid)] = 0
        result = modality.query_ground_truth(
            {"epoch": 10, "agents": [_agent(aid, 48)]},
        )
        (record,) = result["onset_observations"]
        assert record["onset_epoch"] == -38
        # 24 epochs per day: floor(-38 / 24) = -2, not day_index's clamp to 0.
        assert record["onset_day"] == -2


class TestEngineExport:
    def test_epochs_since_onset_matches_the_infection_record(self) -> None:
        agent = KorkinAgent(
            agent_id=0,
            role="passenger",
            immune=False,
            home_zone="Berthing",
            dining_zone="MainDining",
            work_zone="Bridge",
            free_zone="Lounge",
            schedule=["Berthing"],
        )
        agent.infect_with_pathogen(PATHOGEN, 1e4, 0, time_infected=96)
        infection = agent.infections[PATHOGEN]
        infection["onset_time_infected"] = 24
        infection["illness"] = IllnessStatus.SYMPTOMATIC
        exported = agent.to_schema_dict()["pathogen_infections"][PATHOGEN]
        assert exported["epochs_since_symptom_onset"] == 72
        # days_since_symptom_onset is unchanged: day_index(72) + 1 on the
        # legacy clock.
        assert exported["days_since_symptom_onset"] == 73

    def test_no_stamped_onset_exports_none(self) -> None:
        agent = KorkinAgent(
            agent_id=0,
            role="passenger",
            immune=False,
            home_zone="Berthing",
            dining_zone="MainDining",
            work_zone="Bridge",
            free_zone="Lounge",
            schedule=["Berthing"],
        )
        agent.infect_with_pathogen(PATHOGEN, 1e4, 0, time_infected=10)
        exported = agent.to_schema_dict()["pathogen_infections"][PATHOGEN]
        assert exported["epochs_since_symptom_onset"] is None
