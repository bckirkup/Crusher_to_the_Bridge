"""
Catalog registry for ship-level configuration libraries under ``data/``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlatformEntry:
    platform_id: str
    spatial_layout: str
    air_flow_paths: str


@dataclass
class CatalogRegistry:
    """Index of platforms, pathogen bundles, and shared config bundles."""

    repo_root: str
    platforms: dict[str, PlatformEntry] = field(default_factory=dict)
    pathogen_bundles: dict[str, str] = field(default_factory=dict)
    protocol_bundle: str = ""
    resource_costs: str = ""
    logging_profile: str = ""

    @classmethod
    def from_repo(cls, repo_root: str) -> CatalogRegistry:
        reg = cls(repo_root=repo_root)
        reg._scan_platforms()
        reg._scan_pathogens()
        reg._set_defaults()
        return reg

    def _scan_platforms(self) -> None:
        platforms_dir = os.path.join(self.repo_root, "data", "platforms")
        if not os.path.isdir(platforms_dir):
            return
        for name in sorted(os.listdir(platforms_dir)):
            pdir = os.path.join(platforms_dir, name)
            if not os.path.isdir(pdir):
                continue
            layout = os.path.join(pdir, "spatial_layout.json")
            airflow = os.path.join(pdir, "air_flow_paths.json")
            if os.path.isfile(layout) and os.path.isfile(airflow):
                self.platforms[name] = PlatformEntry(
                    platform_id=name,
                    spatial_layout=layout,
                    air_flow_paths=airflow,
                )

    def _scan_pathogens(self) -> None:
        pathogens_dir = os.path.join(self.repo_root, "data", "pathogens")
        if not os.path.isdir(pathogens_dir):
            return
        for fname in sorted(os.listdir(pathogens_dir)):
            if fname.endswith(".json"):
                bundle_id = fname.replace(".json", "")
                self.pathogen_bundles[bundle_id] = os.path.join(pathogens_dir, fname)

    def _set_defaults(self) -> None:
        config_dir = os.path.join(self.repo_root, "data", "config")
        self.protocol_bundle = os.path.join(config_dir, "protocols.json")
        self.resource_costs = os.path.join(config_dir, "resource_costs.json")
        self.logging_profile = os.path.join(config_dir, "logging_profile.json")

    def resolve_platform(self, platform_id: str) -> PlatformEntry:
        if platform_id not in self.platforms:
            raise KeyError(
                f"Unknown platform_id {platform_id!r}; "
                f"available: {sorted(self.platforms)}"
            )
        return self.platforms[platform_id]

    def resolve_pathogen_bundle(self, bundle_id: str) -> str:
        if bundle_id not in self.pathogen_bundles:
            raise KeyError(
                f"Unknown pathogen bundle {bundle_id!r}; "
                f"available: {sorted(self.pathogen_bundles)}"
            )
        return self.pathogen_bundles[bundle_id]

    def to_dict(self) -> dict[str, Any]:
        return {
            "platforms": sorted(self.platforms),
            "pathogen_bundles": sorted(self.pathogen_bundles),
            "protocol_bundle": self.protocol_bundle,
            "resource_costs": self.resource_costs,
            "logging_profile": self.logging_profile,
        }

    @classmethod
    def load_picard_catalog_index(cls, repo_root: str) -> dict[str, Any]:
        """Optional index file under picard_framework/data/catalog/libraries.json."""
        index_path = os.path.join(
            repo_root, "picard_framework", "data", "catalog", "libraries.json",
        )
        if os.path.isfile(index_path):
            with open(index_path, encoding="utf-8") as fh:
                return json.load(fh)
        return {}
