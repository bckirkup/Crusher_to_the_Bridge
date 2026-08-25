"""
PicardRunSpec — immutable resolved configuration for one ship cruise.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Literal

from picard_framework.catalog.registry import CatalogRegistry
from picard_framework.pathogen_overrides import (
    apply_pathogen_overrides,
    load_pathogen_bundle,
)
from simulation_utils.paths import validated_open

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_CRUSHER_CONFIG_REL = os.path.join("crusher_labs", "config.yaml")

HistoryRetention = Literal["full", "compact"]
_VALID_HISTORY_RETENTION = frozenset({"full", "compact"})


def _parse_history_retention(value: Any) -> HistoryRetention:
    """Normalize run.history_retention; unknown values fall back to full."""
    text = str(value or "full").strip().lower()
    if text not in _VALID_HISTORY_RETENTION:
        return "full"
    return text  # type: ignore[return-value]


def _resolve_repo_path(
    repo_root: str,
    path_value: str | None,
    default: str,
) -> str:
    if path_value:
        return path_value if os.path.isabs(path_value) else os.path.join(repo_root, path_value)
    return default


def merge_config_overrides(
    cfg: dict[str, Any],
    overrides: dict[str, Any],
) -> dict[str, Any]:
    """Shallow-merge top-level override blocks into a loaded config dict."""
    merged = dict(cfg)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


@dataclass(frozen=True)
class TelemetryPaths:
    """Output paths for a single ship run."""

    repo_root: str
    ground_truth: str = ""
    simulation_history: str = ""
    lab_notebook: str = ""
    # Empty means no sentinel line list is collected (default off).
    sentinel_line_list: str = ""
    # Empty means the lineage census artifact is not written (default off).
    lineage_census: str = ""

    def __post_init__(self) -> None:
        if not self.ground_truth:
            object.__setattr__(
                self,
                "ground_truth",
                os.path.join(self.repo_root, "telemetry_buffer", "ground_truth.json"),
            )
        if not self.simulation_history:
            object.__setattr__(
                self,
                "simulation_history",
                os.path.join(
                    self.repo_root, "telemetry_buffer", "simulation_history.json",
                ),
            )
        if not self.lab_notebook:
            object.__setattr__(
                self,
                "lab_notebook",
                os.path.join(
                    self.repo_root,
                    "telemetry_buffer",
                    "artificial_lab_notebook.json",
                ),
            )


@dataclass
class PicardRunSpec:
    """Resolved ship-level run configuration."""

    repo_root: str
    random_seed: int = 42
    num_epochs: int = 24
    platform_id: str = "destroyer_baseline"
    spatial_layout: str = ""
    air_flow_paths: str = ""
    pathogen_bundle_id: str = "active_profiles"
    pathogen_profiles_path: str = ""
    pathogen_profiles: dict[str, dict[str, Any]] = field(default_factory=dict)
    protocols_path: str = ""
    resource_costs_path: str = ""
    logging_profile_path: str = ""
    legacy_yaml_path: str = ""
    legacy_cfg: dict[str, Any] = field(default_factory=dict)
    actors: list[dict[str, Any]] = field(default_factory=list)
    incentives: dict[str, Any] = field(default_factory=dict)
    social_config: dict[str, Any] = field(default_factory=dict)
    telemetry: TelemetryPaths | None = None
    write_ground_truth: bool = True
    history_retention: HistoryRetention = "full"

    @property
    def cfg(self) -> dict[str, Any]:
        """Merged runtime dict for legacy orchestrator_init helpers."""
        return self.legacy_cfg

    @classmethod
    def from_legacy_yaml(
        cls,
        repo_root: str,
        config_yaml: str | None = None,
        *,
        num_epochs: int | None = None,
        catalog: CatalogRegistry | None = None,
    ) -> PicardRunSpec:
        sys_path_insert = repo_root
        if sys_path_insert not in __import__("sys").path:
            __import__("sys").path.insert(0, sys_path_insert)
        from crusher_labs import load_config

        if config_yaml is None:
            config_yaml = os.path.join(repo_root, _CRUSHER_CONFIG_REL)
        cfg = load_config(config_yaml)
        reg = catalog or CatalogRegistry.from_repo(repo_root)

        ship_graph = cfg.get("ship_graph", {})
        layout_rel = ship_graph.get(
            "spatial_layout",
            "data/platforms/destroyer_baseline/spatial_layout.json",
        )
        airflow_rel = ship_graph.get(
            "air_flow_paths",
            "data/platforms/destroyer_baseline/air_flow_paths.json",
        )
        profiles_rel = cfg.get("multi_pathogen", {}).get(
            "profiles_path", "data/pathogens/active_profiles.json",
        )

        platform_id = "destroyer_baseline"
        for pid, entry in reg.platforms.items():
            if os.path.normpath(entry.spatial_layout) == os.path.normpath(
                os.path.join(repo_root, layout_rel),
            ):
                platform_id = pid
                break

        epochs = num_epochs if num_epochs is not None else cfg.get("num_epochs", 24)
        bundle_id = os.path.splitext(os.path.basename(profiles_rel))[0]
        pathogen_profiles = load_pathogen_bundle(
            os.path.join(repo_root, profiles_rel),
        )

        return cls(
            repo_root=repo_root,
            random_seed=int(cfg.get("random_seed", 42)),
            num_epochs=int(epochs),
            platform_id=platform_id,
            spatial_layout=os.path.join(repo_root, layout_rel),
            air_flow_paths=os.path.join(repo_root, airflow_rel),
            pathogen_bundle_id=bundle_id,
            pathogen_profiles_path=os.path.join(repo_root, profiles_rel),
            pathogen_profiles=pathogen_profiles,
            protocols_path=reg.protocol_bundle,
            resource_costs_path=reg.resource_costs,
            logging_profile_path=reg.logging_profile,
            legacy_yaml_path=config_yaml,
            legacy_cfg=cfg,
            telemetry=TelemetryPaths(repo_root=repo_root),
        )

    @classmethod
    def from_picard_json(cls, repo_root: str, spec_path: str) -> PicardRunSpec:
        root = repo_root or REPO_ROOT
        spec_dir = os.path.dirname(os.path.abspath(spec_path))
        with validated_open(spec_path, allowed_roots=(root, spec_dir), encoding="utf-8") as fh:
            raw = json.load(fh)
        return cls.from_picard_dict(repo_root, raw)

    @classmethod
    def from_picard_dict(cls, repo_root: str, raw: dict[str, Any]) -> PicardRunSpec:
        """Build a run spec from an in-memory Picard JSON mapping."""
        reg = CatalogRegistry.from_repo(repo_root)
        catalog = raw.get("catalog", {})
        run = raw.get("run", {})

        platform_id = catalog.get("platform_id", "destroyer_baseline")
        platform = reg.resolve_platform(platform_id)
        pathogen_id = catalog.get("pathogen_bundle_id", "active_profiles")
        pathogen_path = reg.resolve_pathogen_bundle(pathogen_id)

        protocols = catalog.get("protocols_path")
        protocols_path = _resolve_repo_path(repo_root, protocols, reg.protocol_bundle)

        resource = catalog.get("resource_costs_path")
        resource_path = _resolve_repo_path(repo_root, resource, reg.resource_costs)

        logging = catalog.get("logging_profile_path")
        logging_path = _resolve_repo_path(repo_root, logging, reg.logging_profile)

        legacy_yaml = raw.get("legacy_yaml")
        legacy_cfg: dict[str, Any] = {}
        if legacy_yaml:
            from crusher_labs import load_config
            yaml_path = (
                legacy_yaml if os.path.isabs(legacy_yaml)
                else os.path.join(repo_root, legacy_yaml)
            )
            legacy_cfg = load_config(yaml_path)
        elif os.path.isfile(os.path.join(repo_root, _CRUSHER_CONFIG_REL)):
            from crusher_labs import load_config
            legacy_cfg = load_config(
                os.path.join(repo_root, _CRUSHER_CONFIG_REL),
            )
            ship_graph = legacy_cfg.setdefault("ship_graph", {})
            ship_graph["spatial_layout"] = os.path.relpath(
                platform.spatial_layout, repo_root,
            )
            ship_graph["air_flow_paths"] = os.path.relpath(
                platform.air_flow_paths, repo_root,
            )
            mp = legacy_cfg.setdefault("multi_pathogen", {})
            mp["profiles_path"] = os.path.relpath(pathogen_path, repo_root)

        overrides = raw.get("config_overrides", {})
        if overrides:
            legacy_cfg = merge_config_overrides(legacy_cfg, overrides)

        base_profiles = load_pathogen_bundle(pathogen_path)
        pathogen_profiles = apply_pathogen_overrides(
            base_profiles,
            raw.get("pathogen_overrides"),
        )

        return cls(
            repo_root=repo_root,
            random_seed=int(run.get("random_seed", 42)),
            num_epochs=int(run.get("num_epochs", 24)),
            platform_id=platform_id,
            spatial_layout=platform.spatial_layout,
            air_flow_paths=platform.air_flow_paths,
            pathogen_bundle_id=pathogen_id,
            pathogen_profiles_path=pathogen_path,
            pathogen_profiles=pathogen_profiles,
            protocols_path=protocols_path,
            resource_costs_path=resource_path,
            logging_profile_path=logging_path,
            legacy_cfg=legacy_cfg,
            actors=raw.get("actors", []),
            incentives=raw.get("incentives", {}),
            social_config=raw.get("social", {}),
            telemetry=TelemetryPaths(
                repo_root=repo_root,
                ground_truth=run.get("ground_truth", ""),
                simulation_history=run.get("simulation_history", ""),
                lab_notebook=run.get("lab_notebook", ""),
                sentinel_line_list=run.get("sentinel_line_list", ""),
                lineage_census=run.get("lineage_census", ""),
            ),
            write_ground_truth=bool(run.get("write_ground_truth", True)),
            history_retention=_parse_history_retention(
                run.get("history_retention", "full"),
            ),
        )

    def inject_into_cfg(self) -> dict[str, Any]:
        """Return legacy_cfg with resolved paths for ship_graph and pathogens."""
        cfg = dict(self.legacy_cfg)
        sg = dict(cfg.get("ship_graph", {}))
        sg["spatial_layout"] = os.path.relpath(self.spatial_layout, self.repo_root)
        sg["air_flow_paths"] = os.path.relpath(self.air_flow_paths, self.repo_root)
        cfg["ship_graph"] = sg
        mp = dict(cfg.get("multi_pathogen", {}))
        mp["profiles_path"] = os.path.relpath(
            self.pathogen_profiles_path, self.repo_root,
        )
        if self.pathogen_profiles:
            mp["resolved_profiles"] = {
                pid: dict(prof) for pid, prof in self.pathogen_profiles.items()
            }
        cfg["multi_pathogen"] = mp
        cfg["random_seed"] = self.random_seed
        cfg["num_epochs"] = self.num_epochs
        return cfg
