"""Tests for GRUMB Aitchison beta diversity in sequencing bridge.

Closes #105.
"""

from __future__ import annotations

import numpy as np
import pytest

from crusher_labs.modalities.sequencing import (
    DISRUPTION_MARKERS,
    MetagenomicSequencing,
    _clr_transform,
    aitchison_distance,
    aitchison_distance_matrix,
)
from crusher_labs.observation_core import WastewaterSequencingGrid


def test_aitchison_distance_zero_for_identical_compositions() -> None:
    x = np.array([0.4, 0.35, 0.25])
    assert aitchison_distance(x, x) == pytest.approx(0.0, abs=1e-9)


def test_aitchison_distance_matches_clr_euclidean() -> None:
    x = np.array([0.5, 0.3, 0.2])
    y = np.array([0.2, 0.5, 0.3])
    clr_diff = _clr_transform(x) - _clr_transform(y)
    expected = float(np.linalg.norm(clr_diff))
    assert aitchison_distance(x, y) == pytest.approx(expected)


def test_aitchison_distance_matrix_symmetric_with_zero_diagonal() -> None:
    profiles = np.array(
        [
            [0.5, 0.3, 0.2],
            [0.2, 0.5, 0.3],
            [0.33, 0.33, 0.34],
        ],
    )
    dist = aitchison_distance_matrix(profiles)
    assert dist.shape == (3, 3)
    assert np.allclose(dist, dist.T)
    assert np.allclose(np.diag(dist), 0.0)


def test_apply_microflora_disruption_reports_aitchison_distance() -> None:
    seq = MetagenomicSequencing(rng=np.random.default_rng(42))
    taxa = ["Enterobacter", "Candida_spp", "Vibrio_spp"]
    baseline = np.array([0.4, 0.35, 0.25])
    shifted, deltas, beta_dist = seq.apply_microflora_disruption(
        baseline,
        taxa,
        {"gastrointestinal": DISRUPTION_MARKERS["gastrointestinal"]},
        total_disruption_magnitude=1.0,
    )
    assert beta_dist > 0.0
    assert shifted.sum() == pytest.approx(1.0, rel=1e-6)
    assert deltas


def test_detect_microflora_anomaly_uses_aitchison_threshold() -> None:
    seq = MetagenomicSequencing(aitchison_anomaly_threshold=0.08)
    report_low = seq.detect_microflora_anomaly({}, aitchison_distance_to_baseline=0.02)
    report_high = seq.detect_microflora_anomaly({}, aitchison_distance_to_baseline=0.12)
    assert report_low["anomaly_detected"] is False
    assert report_high["anomaly_detected"] is True
    assert report_high["aitchison_distance_to_baseline"] == 0.12


def test_wastewater_grid_uses_aitchison_anomaly_gate() -> None:
    grid = WastewaterSequencingGrid(
        rng=np.random.default_rng(42),
        aitchison_anomaly_threshold=0.08,
    )
    clean = grid.sample_zone("Z1", pathogen_mass=0.0, microflora_shifts={})
    shifted = grid.sample_zone(
        "Z1",
        pathogen_mass=0.0,
        microflora_shifts={"gastrointestinal": 1.0},
    )
    assert clean["aitchison_distance_to_baseline"] == 0.0
    assert clean["anomaly_detected"] is False
    assert shifted["aitchison_distance_to_baseline"] > 0.08
    assert shifted["anomaly_detected"] is True


def test_query_ground_truth_includes_beta_diversity_block() -> None:
    seq = MetagenomicSequencing(rng=np.random.default_rng(7))
    payload = {
        "epoch": 3,
        "spaces": {
            "Galley": {
                "pathogen_mass": 0.0,
                "microbiome_id": "coastal_port",
            },
        },
    }
    shifts = {"Galley": {"gastrointestinal": 1.0}}
    result = seq.query_ground_truth(payload, zone_microflora_shifts=shifts)
    zone = result["zone_results"]["Galley"]
    beta = zone["microflora_disruption"]["beta_diversity"]
    assert "aitchison_distance_to_baseline" in beta
    assert beta["aitchison_anomaly_threshold"] == pytest.approx(0.08)
