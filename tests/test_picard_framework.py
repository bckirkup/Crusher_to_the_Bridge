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


def test_history_retention_compact_from_json(tmp_path) -> None:
    import json

    path = tmp_path / "compact_spec.json"
    path.write_text(
        json.dumps({
            "catalog": {
                "platform_id": "destroyer_baseline",
                "pathogen_bundle_id": "active_profiles",
            },
            "run": {
                "random_seed": 42,
                "num_epochs": 2,
                "write_ground_truth": False,
                "history_retention": "compact",
            },
            "legacy_yaml": "crusher_labs/config.yaml",
            "config_overrides": {"ship_graph": {"num_agents": 20}},
            "actors": [],
            "incentives": {},
        }),
        encoding="utf-8",
    )
    spec = PicardRunSpec.from_picard_json(REPO_ROOT, str(path))
    assert spec.history_retention == "compact"
    sim = ShipSimulation(spec, display=False, repo_root=REPO_ROOT)
    result = sim.run(n_epochs=2)
    assert len(result.history) == 2
    assert sim.obs is not None
    assert sim.obs.lab_notebook_enabled is False
    assert len(sim.obs.notebook.records) == 0
    for rec in result.history:
        assert "agents" not in rec
        assert "contact_tracing" not in rec
        assert "observation_engine" not in rec
        assert "summary" in rec
        assert "spaces" in rec
        assert "cost_accounting" in rec
    # Compact history stays small vs full agent dumps (JSON bytes, not RSS).
    compact_bytes = sum(len(json.dumps(r, default=str)) for r in result.history)
    assert compact_bytes < 200_000


def test_history_retention_defaults_to_full() -> None:
    spec = PicardRunSpec.from_legacy_yaml(REPO_ROOT, num_epochs=2)
    assert spec.history_retention == "full"
