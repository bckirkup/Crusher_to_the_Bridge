"""Tests for boundary Stan data prep (no CmdStan required)."""

from __future__ import annotations

from picard_framework.analysis.stan._boundary_data import (
    build_boundary_ar_stan_data,
    build_boundary_outbreak_stan_data,
    filter_pathogen_runs,
    matches_pathogen,
)


def test_matches_pathogen_aliases() -> None:
    assert matches_pathogen("norovirus", "norovirus", "norwalk_gi")
    assert matches_pathogen("sarscov2", "sarscov2", "sars_cov2_resp")
    assert matches_pathogen("influenza", "influenza", "influenza_a")
    assert matches_pathogen("measles", "measles", "measles_virus")
    assert not matches_pathogen("influenza", "norovirus", "norwalk_gi")


def test_boundary_outbreak_and_ar_data_shapes() -> None:
    rows = [
        {
            "run_id": "b1_norovirus_mega_cruise_5000_dose10p6_init1_syndromic_s200",
            "pathogen": "norovirus",
            "pathogen_id": "norwalk_gi",
            "platform_id": "mega_cruise_5000",
            "surveillance_strategy": "syndromic",
            "dose_adjustment": 10.6,
            "initial_infected": 1,
            "outbreak_occurred": True,
            "attack_rate": 0.12,
        },
        {
            "run_id": "b1_norovirus_mega_cruise_5000_dose10p6_init2_syndromic_s201",
            "pathogen": "norovirus",
            "pathogen_id": "norwalk_gi",
            "platform_id": "expedition_cruise_450",
            "surveillance_strategy": "syndromic",
            "dose_adjustment": 10.6,
            "initial_infected": 2,
            "outbreak_occurred": False,
            "attack_rate": 0.01,
        },
        {
            "run_id": "b1_influenza_mega_cruise_5000_dose1p5_init1_syndromic_s200",
            "pathogen": "influenza",
            "pathogen_id": "influenza_a",
            "platform_id": "mega_cruise_5000",
            "surveillance_strategy": "syndromic",
            "dose_adjustment": 1.5,
            "initial_infected": 1,
            "outbreak_occurred": True,
            "attack_rate": 0.08,
        },
    ]
    noro = filter_pathogen_runs(rows, "norovirus")
    assert len(noro) == 2
    data, meta = build_boundary_outbreak_stan_data(rows, pathogen="norovirus")
    assert data["N_runs"] == 2
    assert meta["n_outbreaks"] == 1
    assert len(data["log_k"]) == 2
    ar_data, ar_meta = build_boundary_ar_stan_data(rows, pathogen="norovirus")
    assert ar_data["N_runs"] == 1
    assert ar_meta["pathogen"] == "norovirus"
    assert 0.0 < ar_data["ar"][0] < 1.0
