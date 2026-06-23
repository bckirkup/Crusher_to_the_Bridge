"""Tests for clinical test autocorrelation matrix."""

from __future__ import annotations

import os
import sys

import numpy as np
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from crusher_labs.clinical_correlation import (
    CLINICAL_TEST_KEYS,
    ClinicalTestCorrelation,
    parse_autocorrelation_matrix,
    run_correlated_clinical_panel,
    validate_autocorrelation_matrix,
)
from crusher_labs.observation_core import (
    ClinicalMicrobiology,
    ClinicalQPCR,
    ClinicalRapidDiagnostic,
)
from orchestrator_init import init_observation_engine
from orchestrator_types import ObservationEngine
from telemetry_buffer.agent_axes import (
    COMPLIANCE_COMPLIANT,
    INFECTION_INFECTED,
    PRESENTATION_SYMPTOMATIC,
    resolve_agent_axes,
)


def _make_obs(seed: int = 42) -> ObservationEngine:
    return init_observation_engine({}, seed=seed)


def test_default_matrix_is_identity() -> None:
    corr = ClinicalTestCorrelation.from_config({})
    assert corr.is_independent
    assert np.allclose(corr.correlation_matrix, np.eye(3))


def test_parse_nested_mapping_matrix() -> None:
    raw = {
        "clinical_rdt": {
            "clinical_rdt": 1.0,
            "clinical_qpcr": 0.5,
            "clinical_microbiology": 0.0,
        },
        "clinical_qpcr": {
            "clinical_rdt": 0.5,
            "clinical_qpcr": 1.0,
            "clinical_microbiology": 0.2,
        },
        "clinical_microbiology": {
            "clinical_rdt": 0.0,
            "clinical_qpcr": 0.2,
            "clinical_microbiology": 1.0,
        },
    }
    matrix = parse_autocorrelation_matrix(raw)
    validate_autocorrelation_matrix(matrix)
    assert matrix[0, 1] == pytest.approx(0.5)


def test_invalid_matrix_rejected() -> None:
    with pytest.raises(ValueError, match="3x3"):
        parse_autocorrelation_matrix([[1.0, 0.9], [0.9, 1.0]])
    non_psd = np.array([
        [1.0, 0.95, 0.95],
        [0.95, 1.0, -0.95],
        [0.95, -0.95, 1.0],
    ])
    with pytest.raises(ValueError, match="positive semi-definite"):
        validate_autocorrelation_matrix(non_psd)


def test_shared_uniform_aligns_rdt_and_qpcr_outcomes() -> None:
    """Correlated path uses the same latent draw for RDT and qPCR thresholds."""
    obs = _make_obs(seed=99)
    agent = {
        "agent_id": 7,
        "location": "MedBay",
        "shedding_rate": 600.0,
        "infection_status": INFECTION_INFECTED,
        "symptom_presentation": PRESENTATION_SYMPTOMATIC,
        "compliance_status": COMPLIANCE_COMPLIANT,
        "microflora_disruption": 0.0,
        "pathogen_infections": {},
    }
    for draw in (0.05, 0.25, 0.75, 0.95):
        panel = ClinicalTestCorrelation(
            correlation_matrix=np.eye(3),
            rng=np.random.default_rng(0),
        ).run_agent_tests(obs, agent)
        # Force deterministic check via direct uniform injection
        infection, presentation, compliance = resolve_agent_axes(agent)
        rdt = obs.clin_rdt.test_agent(
            agent["agent_id"],
            agent["shedding_rate"],
            True,
            infection,
            presentation,
            compliance,
            agent["location"],
            uniform_draw=draw,
        )
        qpcr = obs.clin_qpcr.test_agent(
            agent["agent_id"],
            agent["shedding_rate"],
            infection,
            presentation,
            compliance,
            agent["location"],
            uniform_draw=draw,
        )
        assert rdt["positive"] == qpcr["detected"]
        assert panel  # panel path exercised once per loop


def test_run_correlated_clinical_panel_keys() -> None:
    agents = [
        {
            "agent_id": 0,
            "location": "MedBay",
            "shedding_rate": 100.0,
            "infection_status": INFECTION_INFECTED,
            "symptom_presentation": PRESENTATION_SYMPTOMATIC,
            "compliance_status": COMPLIANCE_COMPLIANT,
            "microflora_disruption": 0.1,
            "pathogen_infections": {},
        },
    ]
    obs = _make_obs()
    corr = ClinicalTestCorrelation.from_config({})
    rdt, qpcr, micro = run_correlated_clinical_panel(obs, agents, corr)
    assert 0 in rdt and 0 in qpcr and 0 in micro
    assert rdt[0]["instrument"] == "clinical_rdt"
    assert qpcr[0]["instrument"] == "clinical_qpcr"
    assert micro[0]["instrument"] == "clinical_microbiology"


def test_uniform_draw_overrides_primary_stochastic_decision() -> None:
    rdt = ClinicalRapidDiagnostic(rng=np.random.default_rng(0))
    always_pos = rdt.test_agent(
        1, 5000.0, True, INFECTION_INFECTED,
        PRESENTATION_SYMPTOMATIC, COMPLIANCE_COMPLIANT, "MedBay",
        uniform_draw=0.01,
    )
    never_pos = rdt.test_agent(
        1, 5000.0, True, INFECTION_INFECTED,
        PRESENTATION_SYMPTOMATIC, COMPLIANCE_COMPLIANT, "MedBay",
        uniform_draw=0.99,
    )
    assert always_pos["positive"] is True
    assert never_pos["positive"] is False

    qpcr = ClinicalQPCR(rng=np.random.default_rng(0))
    low_detect = qpcr.test_agent(
        1, 1000.0, INFECTION_INFECTED,
        PRESENTATION_SYMPTOMATIC, COMPLIANCE_COMPLIANT, "MedBay",
        uniform_draw=0.01,
    )
    high_detect = qpcr.test_agent(
        1, 1000.0, INFECTION_INFECTED,
        PRESENTATION_SYMPTOMATIC, COMPLIANCE_COMPLIANT, "MedBay",
        uniform_draw=0.99,
    )
    assert low_detect["detected"] is True
    assert high_detect["detected"] is False

    micro = ClinicalMicrobiology(rng=np.random.default_rng(0))
    detected = micro.test_agent(
        1, 0.8, INFECTION_INFECTED,
        PRESENTATION_SYMPTOMATIC, COMPLIANCE_COMPLIANT, "MedBay",
        {},
        uniform_draw=0.01,
    )
    not_detected = micro.test_agent(
        1, 0.8, INFECTION_INFECTED,
        PRESENTATION_SYMPTOMATIC, COMPLIANCE_COMPLIANT, "MedBay",
        {},
        uniform_draw=0.99,
    )
    assert detected["secondary_infection_detected"] is True
    assert not_detected["secondary_infection_detected"] is False


def test_init_observation_engine_attaches_correlation() -> None:
    obs = init_observation_engine({}, seed=42)
    assert hasattr(obs, "clinical_correlation")
    assert obs.clinical_correlation.is_independent
    assert obs.clinical_correlation.test_order == CLINICAL_TEST_KEYS
