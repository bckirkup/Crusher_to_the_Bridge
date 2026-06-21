"""Tests for Picard_Framework run specs and ship simulation."""

from __future__ import annotations

import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from picard_framework import PicardRunSpec, ShipSimulation
from picard_framework.catalog.registry import CatalogRegistry


def test_catalog_registry_lists_destroyer() -> None:
    reg = CatalogRegistry.from_repo(REPO_ROOT)
    assert "destroyer_baseline" in reg.platforms
    assert "active_profiles" in reg.pathogen_bundles


def test_from_legacy_yaml_matches_paths() -> None:
    spec = PicardRunSpec.from_legacy_yaml(REPO_ROOT, num_epochs=2)
    assert spec.num_epochs == 2
    assert os.path.isfile(spec.spatial_layout)
    assert os.path.isfile(spec.pathogen_profiles_path)


def test_ship_simulation_two_epoch_smoke() -> None:
    spec = PicardRunSpec.from_legacy_yaml(REPO_ROOT, num_epochs=2)
    sim = ShipSimulation(spec, display=False, repo_root=REPO_ROOT)
    result = sim.run(n_epochs=2)
    assert len(result.history) == 2
    assert result.history[-1]["epoch"] == 1


def test_from_picard_json_applies_config_overrides() -> None:
    spec_path = os.path.join(REPO_ROOT, "picard_framework/runs/smoke_cascade_6epoch.json")
    spec = PicardRunSpec.from_picard_json(REPO_ROOT, spec_path)
    assert spec.num_epochs == 6
    assert spec.legacy_cfg["diagnostic_cascade"]["enabled"] is True
    assert spec.legacy_cfg["diagnostic_cascade"]["config_path"] == (
        "data/config/diagnostic_cascade.json"
    )
