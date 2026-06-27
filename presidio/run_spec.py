"""
PresidioRunSpec — fleet-level immutable configuration for multi-cruise runs.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from simulation_utils.paths import resolve_repo_path


@dataclass
class PresidioRunSpec:
    """Resolved fleet meta-run configuration."""

    repo_root: str
    num_cruises: int = 3
    picard_run_spec_path: str = ""
    picard_run_spec: dict[str, Any] = field(default_factory=dict)
    economics_path: str = ""
    experience_store_path: str = ""
    catalog_index_path: str = ""
    fleet_config_path: str = ""
    seed_base: int = 42
    actors: list[dict[str, Any]] = field(default_factory=list)
    incentives: dict[str, Any] = field(default_factory=dict)
    output_root: str = ""
    social_config: dict = field(default_factory=dict)

    @classmethod
    def from_fleet_json(cls, repo_root: str, fleet_config_path: str) -> PresidioRunSpec:
        fleet_config_path = resolve_repo_path(repo_root, fleet_config_path)
        with open(fleet_config_path, encoding="utf-8") as fh:
            raw = json.load(fh)
        fleet = raw.get("fleet", {})
        catalog = raw.get("catalog", {})
        run = raw.get("run", {})

        economics_rel = catalog.get(
            "economics_id", "presidio/data/economics/fleet_economics.json",
        )
        economics_path = resolve_repo_path(repo_root, economics_rel)

        experience_rel = run.get(
            "experience_store",
            "presidio/data/experiences/fleet_experience.json",
        )
        experience_path = resolve_repo_path(repo_root, experience_rel)

        picard_spec_rel = catalog.get(
            "picard_run_spec",
            "picard_framework/runs/destroyer_baseline_default.json",
        )
        picard_spec_path = resolve_repo_path(repo_root, picard_spec_rel)

        output_rel = run.get("output_root", "presidio/data/experiences/runs")
        output_root = resolve_repo_path(repo_root, output_rel)

        catalog_index = catalog.get(
            "libraries_index",
            "presidio/data/catalog/libraries.json",
        )
        catalog_index_path = resolve_repo_path(repo_root, catalog_index)

        return cls(
            repo_root=repo_root,
            num_cruises=int(fleet.get("num_cruises", 3)),
            picard_run_spec_path=picard_spec_path,
            picard_run_spec=raw.get("picard", {}),
            economics_path=economics_path,
            experience_store_path=experience_path,
            catalog_index_path=catalog_index_path,
            fleet_config_path=fleet_config_path,
            seed_base=int(run.get("seed_base", 42)),
            actors=raw.get("actors", []),
            incentives=raw.get("incentives", {}),
            output_root=output_root,
            social_config=raw.get("social", {}),
        )

    @classmethod
    def default(cls, repo_root: str) -> PresidioRunSpec:
        default_config = resolve_repo_path(
            repo_root, "presidio/data/config/default_fleet.json",
        )
        return cls.from_fleet_json(repo_root, default_config)
