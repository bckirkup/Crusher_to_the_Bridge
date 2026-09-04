"""Tests for Picard pathogen_overrides resolution."""

from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from picard_framework import PicardRunSpec, ShipSimulation
from picard_framework.pathogen_overrides import (
    apply_pathogen_overrides,
    load_pathogen_bundle,
)
from orchestrator_init import load_pathogen_profiles


def test_apply_pathogen_overrides_patches_and_removes() -> None:
    base = load_pathogen_bundle(
        os.path.join(REPO_ROOT, "data/pathogens/active_profiles.json"),
    )
    resolved = apply_pathogen_overrides(
        base,
        {
            "norwalk_gi": {"initial_infected": 5},
            "remove": ["sars_cov2_resp"],
        },
    )
    assert "sars_cov2_resp" not in resolved
    assert resolved["norwalk_gi"]["initial_infected"] == 5
    assert base["norwalk_gi"]["initial_infected"] == 1


def test_apply_pathogen_overrides_adds_profile() -> None:
    base = load_pathogen_bundle(
        os.path.join(REPO_ROOT, "data/pathogens/active_profiles.json"),
    )
    new_profile = {
        "pathogen_id": "test_pathogen",
        "name": "Test Pathogen",
        "category": "bacterial",
        "transmission_routes": ["direct_contact"],
        "shedding_curve_log10": [1.0],
        "asymptomatic_shedding_log10": [0.5],
        "dose_response": {"model": "exponential", "k": 0.1},
        "illness_probability": {"eta": 0.5, "gamma": 0.1},
        "recovery_day": 5,
        "surface_deposition_fraction": 0.1,
        "base_susceptibility": 1.0,
        "introduction_epoch": 0,
        "initial_infected": 1,
        "initial_time_infected": 0,
        "microflora_disruption": {"causes_disruption": False},
    }
    resolved = apply_pathogen_overrides(base, {"add": [new_profile]})
    assert "test_pathogen" in resolved
    assert resolved["test_pathogen"]["name"] == "Test Pathogen"


def test_from_picard_json_applies_pathogen_overrides() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_path = os.path.join(tmpdir, "experiment.json")
        with open(spec_path, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "catalog": {
                        "platform_id": "destroyer_baseline",
                        "pathogen_bundle_id": "active_profiles",
                    },
                    "run": {"random_seed": 7, "num_epochs": 1, "write_ground_truth": False},
                    "legacy_yaml": os.path.join(REPO_ROOT, "crusher_labs/config.yaml"),
                    "pathogen_overrides": {
                        "norwalk_gi": {"initial_infected": 4},
                        "remove": ["sars_cov2_resp"],
                    },
                },
                fh,
            )
        spec = PicardRunSpec.from_picard_json(REPO_ROOT, spec_path)
        assert spec.pathogen_profiles["norwalk_gi"]["initial_infected"] == 4
        assert "sars_cov2_resp" not in spec.pathogen_profiles
        injected = spec.inject_into_cfg()
        loaded = load_pathogen_profiles(injected)
        assert loaded["norwalk_gi"]["initial_infected"] == 4
        assert "sars_cov2_resp" not in loaded


def test_ship_simulation_uses_resolved_pathogen_profiles() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_path = os.path.join(tmpdir, "experiment.json")
        with open(spec_path, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "catalog": {
                        "platform_id": "destroyer_baseline",
                        "pathogen_bundle_id": "active_profiles",
                    },
                    "run": {"random_seed": 42, "num_epochs": 1, "write_ground_truth": False},
                    "legacy_yaml": os.path.join(REPO_ROOT, "crusher_labs/config.yaml"),
                    "pathogen_overrides": {
                        "remove": ["sars_cov2_resp", "influenza_a"],
                    },
                },
                fh,
            )
        spec = PicardRunSpec.from_picard_json(REPO_ROOT, spec_path)
        sim = ShipSimulation(spec, display=False, repo_root=REPO_ROOT)
        sim.initialize()
        assert set(sim.pathogen_profiles) == {"norwalk_gi"}


def test_unknown_pathogen_patch_raises() -> None:
    base = {"norwalk_gi": {"pathogen_id": "norwalk_gi", "initial_infected": 1}}
    with pytest.raises(ValueError, match="unknown pathogen_id"):
        apply_pathogen_overrides(base, {"missing_pid": {"initial_infected": 2}})
