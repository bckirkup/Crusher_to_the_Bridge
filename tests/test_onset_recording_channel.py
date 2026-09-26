"""The period-faithful onset-recording channel on ``sars_cov2_resp``.

``observation_model.onset_recording`` is additive and default-off: a
profile that declares no block dates every confirmed symptomatic onset
(the shipped channel), and a profile that declares one dates an onset
only when the host had presented on or before the epoch of the specimen
that confirmed it, times a once-per-case recall draw on a dedicated RNG
stream. These tests pin the gate, the draw's memoization, the stream's
isolation, and the channel's reachability through the arm grammar.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from crusher_labs.modalities.syndromic import SyndromicSurveillance
from engines.sim_clock import HOURS, SimClock
from picard_framework.covid_boarding_screen import (
    enumerate_cells,
    load_design,
    prepare_cell_run_spec,
)
from picard_framework.covid_theta_fit import PATHOGEN_ID, load_covid_profile
from picard_framework.pathogen_overrides import apply_pathogen_overrides
from telemetry_buffer.agent_axes import (
    COMPLIANCE_COMPLIANT,
    INFECTION_INFECTED,
    PRESENTATION_SYMPTOMATIC,
)

HOURLY = SimClock(epoch_duration_hours=1.0, mode=HOURS)
DESIGN_REL = os.path.join(
    "picard_framework", "runs", "covid_sero_channel_v1_design.json",
)
PERIOD_BLOCK = {
    "symptomatic_at_confirmation_required": True,
    "report_probability": 0.56,
}


def _agent(aid: int, elapsed: int | None) -> dict:
    """A symptomatic confirmed-presenting host, onset ``elapsed`` ago."""
    infection = {
        "illness": "SYMPTOMATIC",
        "symptom_severity": "moderate",
        "pathogen_id": PATHOGEN_ID,
        "infection_epoch": 0,
    }
    if elapsed is not None:
        infection["epochs_since_symptom_onset"] = elapsed
    return {
        "agent_id": aid,
        "infection_state": INFECTION_INFECTED,
        "symptom_presentation": PRESENTATION_SYMPTOMATIC,
        "compliance_status": COMPLIANCE_COMPLIANT,
        "pathogen_infections": {PATHOGEN_ID: infection},
    }


def _modality(onset_recording: dict | None = None) -> SyndromicSurveillance:
    observation: dict = {}
    if onset_recording is not None:
        observation["onset_recording"] = dict(onset_recording)
    return SyndromicSurveillance(
        sick_call_probability=0.0,
        background_noise_rate=0.0,
        noise_categories=[],
        symptom_severity_profiles={
            PATHOGEN_ID: {"observation_model": observation},
        },
        clock=HOURLY,
        rng=np.random.default_rng(0),
    )


def _confirmed_at(
    modality: SyndromicSurveillance, aid: int, epoch: int,
) -> None:
    modality._lab_confirmed[(PATHOGEN_ID, aid)] = epoch


def _observe_at(
    modality: SyndromicSurveillance, aid: int, epoch: int, elapsed: int,
) -> list[dict]:
    result = modality.query_ground_truth(
        {"epoch": epoch, "agents": [_agent(aid, elapsed)]},
    )
    return result["onset_observations"]


class TestChannelDeclaration:
    def test_undeclared_block_is_off(self) -> None:
        modality = _modality()
        assert modality.onset_recording_channel(PATHOGEN_ID) is None

    def test_declared_block_reads_back_normalized(self) -> None:
        modality = _modality(
            {"symptomatic_at_confirmation_required": True,
             "report_probability": 0.56},
        )
        channel = modality.onset_recording_channel(PATHOGEN_ID)
        assert channel == {
            "symptomatic_at_confirmation_required": True,
            "report_probability": pytest.approx(0.56),
        }

    def test_no_observation_model_is_off(self) -> None:
        modality = SyndromicSurveillance(
            sick_call_probability=0.0,
            background_noise_rate=0.0,
            noise_categories=[],
            symptom_severity_profiles={PATHOGEN_ID: {}},
            rng=np.random.default_rng(0),
        )
        assert modality.onset_recording_channel(PATHOGEN_ID) is None


class TestDefaultOffIsUnchanged:
    def test_confirmed_symptomatic_onset_records_as_shipped(self) -> None:
        modality = _modality()
        _confirmed_at(modality, 1, epoch=20)
        records = _observe_at(modality, 1, epoch=30, elapsed=5)
        (record,) = records
        assert record["onset_epoch"] == 25
        assert record["confirmed_epoch"] == 20
        # An onset after the confirming specimen still dates, as shipped:
        # the channel change is the period arm's, not the baseline's.
        assert modality._onset_recording_decisions == {}


class TestSymptomaticAtConfirmationGate:
    def test_onset_at_or_before_confirmation_dates(self) -> None:
        modality = _modality(dict(PERIOD_BLOCK))
        _confirmed_at(modality, 1, epoch=20)
        modality._onset_recording_decisions[(PATHOGEN_ID, 1)] = True
        records = _observe_at(modality, 1, epoch=30, elapsed=25)
        (record,) = records
        assert record["onset_epoch"] == 5

    def test_onset_after_confirming_specimen_enters_undated(self) -> None:
        modality = _modality(dict(PERIOD_BLOCK))
        _confirmed_at(modality, 1, epoch=20)
        # Presentation onset at epoch 25 postdates the confirming specimen.
        assert _observe_at(modality, 1, epoch=30, elapsed=5) == []
        assert modality._onset_observations == {}

    def test_gate_off_dates_a_post_specimen_onset(self) -> None:
        """Recall-only fallback: no gate, so confirmation order is inert."""
        modality = _modality({
            "symptomatic_at_confirmation_required": False,
            "report_probability": 1.0,
        })
        _confirmed_at(modality, 1, epoch=20)
        records = _observe_at(modality, 1, epoch=30, elapsed=5)
        (record,) = records
        assert record["onset_epoch"] == 25


class TestRecallDraw:
    def test_zero_probability_never_records(self) -> None:
        modality = _modality({
            "symptomatic_at_confirmation_required": False,
            "report_probability": 0.0,
        })
        _confirmed_at(modality, 1, epoch=20)
        for epoch in (30, 31, 32):
            assert _observe_at(modality, 1, epoch, elapsed=10) == []
        assert modality._onset_observations == {}

    def test_one_probability_always_records(self) -> None:
        modality = _modality({
            "symptomatic_at_confirmation_required": False,
            "report_probability": 1.0,
        })
        _confirmed_at(modality, 1, epoch=20)
        (record,) = _observe_at(modality, 1, epoch=30, elapsed=10)
        assert record["onset_epoch"] == 20

    def test_the_draw_is_once_per_case(self) -> None:
        """A fresh draw per epoch would asymptotically admit every case."""
        modality = _modality({
            "symptomatic_at_confirmation_required": False,
            "report_probability": 0.56,
        })
        _confirmed_at(modality, 1, epoch=20)
        _observe_at(modality, 1, epoch=30, elapsed=10)
        key = (PATHOGEN_ID, 1)
        first = modality._onset_recording_decisions[key]
        for epoch in (31, 32, 33, 34):
            _observe_at(modality, 1, epoch, elapsed=10)
            assert modality._onset_recording_decisions[key] == first
        # One draw, not one per epoch: the memoized decision is sticky.
        assert len(modality._onset_recording_decisions) == 1

    def test_a_gated_case_spends_no_draw(self) -> None:
        """The specimen-epoch gate answers before the recall draw runs."""
        modality = _modality(dict(PERIOD_BLOCK))
        _confirmed_at(modality, 1, epoch=20)
        _observe_at(modality, 1, epoch=30, elapsed=5)
        assert modality._onset_recording_decisions == {}


class TestStreamIsolation:
    def test_onset_draws_leave_parent_and_molecular_streams(self) -> None:
        off = _modality()
        on = _modality(dict(PERIOD_BLOCK))
        for modality in (off, on):
            _confirmed_at(modality, 1, epoch=20)
            _observe_at(modality, 1, epoch=30, elapsed=25)
        # Deriving and drawing the onset stream consumed nothing upstream:
        # the parent's next draws are identical with or without the block,
        # and the molecular stream never moved.
        assert [off.rng.random() for _ in range(4)] == [
            on.rng.random() for _ in range(4)
        ]
        assert [off._molecular_rng.random() for _ in range(4)] == [
            on._molecular_rng.random() for _ in range(4)
        ]


class TestArmReachability:
    def test_design_enumerates_the_declared_1080_cells(self) -> None:
        design = load_design(os.path.join(REPO_ROOT, DESIGN_REL))
        cells = enumerate_cells(design)
        assert len(cells) == 1080
        # Canary row under the 60-seed revision: period channel at
        # theta x0.001, seeds 20200205-264 (first 20 unchanged).
        canary = cells[1020:1080]
        assert all(c.arm_id == "P1_period" for c in canary)
        assert [c.seed for c in canary] == list(range(20200205, 20200265))
        assert all(c.theta == pytest.approx(4.22e7) for c in canary)
        # The declared arm's matching row sits immediately before.
        declared = cells[960:1020]
        assert all(c.arm_id == "D0_declared" for c in declared)
        assert [c.seed for c in declared] == [c.seed for c in canary]

    def test_period_arm_block_reaches_the_run_spec(self) -> None:
        design = load_design(os.path.join(REPO_ROOT, DESIGN_REL))
        cells = enumerate_cells(design)
        period = next(c for c in cells if c.arm_id == "P1_period")
        raw = prepare_cell_run_spec(design, period, num_epochs=24)
        block = (
            raw["pathogen_overrides"][PATHOGEN_ID]
            .get("observation_model", {})
            .get("onset_recording")
        )
        assert block == PERIOD_BLOCK

    def test_declared_arm_spec_carries_no_block(self) -> None:
        design = load_design(os.path.join(REPO_ROOT, DESIGN_REL))
        cells = enumerate_cells(design)
        declared = next(c for c in cells if c.arm_id == "D0_declared")
        raw = prepare_cell_run_spec(design, declared, num_epochs=24)
        observation = (
            raw["pathogen_overrides"][PATHOGEN_ID].get("observation_model")
        )
        assert observation is None

    def test_block_resolves_onto_the_profile_and_modality(self) -> None:
        """The deep-merge the engine applies lands the channel readable."""
        profile = load_covid_profile(REPO_ROOT)
        resolved = apply_pathogen_overrides(
            {PATHOGEN_ID: profile},
            {PATHOGEN_ID: {
                "observation_model": {"onset_recording": dict(PERIOD_BLOCK)},
            }},
        )
        block = (
            resolved[PATHOGEN_ID]["observation_model"]["onset_recording"]
        )
        assert block == PERIOD_BLOCK
        modality = _modality(block)
        channel = modality.onset_recording_channel(PATHOGEN_ID)
        assert channel == {
            "symptomatic_at_confirmation_required": True,
            "report_probability": pytest.approx(0.56),
        }
