"""The shared default-asset table resolves to real files and the registry agrees with it."""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from engines.py_contam_bridge import load_air_flow_paths, load_spatial_layout
from picard_framework.catalog.registry import CatalogRegistry
from simulation_utils import asset_defaults
from tools.sanity_checker import paths_from_run_config


def test_every_default_asset_exists_on_disk() -> None:
    for rel in (
        asset_defaults.DEFAULT_SPATIAL_LAYOUT,
        asset_defaults.DEFAULT_AIR_FLOW_PATHS,
        asset_defaults.DEFAULT_PATHOGEN_PROFILES,
        asset_defaults.PROTOCOLS_CONFIG,
        asset_defaults.RESOURCE_COSTS_CONFIG,
        asset_defaults.LOGGING_PROFILE_CONFIG,
        asset_defaults.INSTRUMENT_TURNAROUND_CONFIG,
        asset_defaults.LONG_READ_SEQUENCING_PARAMS_CONFIG,
    ):
        assert os.path.isfile(os.path.join(REPO_ROOT, rel)), rel


def test_registry_defaults_match_shared_table() -> None:
    reg = CatalogRegistry.from_repo(REPO_ROOT)
    platform = reg.default_platform()
    assert platform.platform_id == asset_defaults.DEFAULT_PLATFORM_ID
    assert os.path.samefile(
        platform.spatial_layout,
        os.path.join(REPO_ROOT, asset_defaults.DEFAULT_SPATIAL_LAYOUT),
    )
    assert os.path.samefile(
        platform.air_flow_paths,
        os.path.join(REPO_ROOT, asset_defaults.DEFAULT_AIR_FLOW_PATHS),
    )
    assert os.path.samefile(
        reg.default_pathogen_bundle(),
        os.path.join(REPO_ROOT, asset_defaults.DEFAULT_PATHOGEN_PROFILES),
    )
    assert os.path.samefile(
        reg.logging_profile,
        os.path.join(REPO_ROOT, asset_defaults.LOGGING_PROFILE_CONFIG),
    )


def test_loader_and_checker_fall_back_to_the_same_platform() -> None:
    """With ship_graph omitted, the engine loader and the validator resolve one platform."""
    layout = load_spatial_layout(REPO_ROOT, {})
    airflow = load_air_flow_paths(REPO_ROOT, {})
    assert layout["platform"] == asset_defaults.DEFAULT_PLATFORM_ID
    assert airflow

    # load_config only opens files under the repo root, so the bare config lives there briefly.
    cfg_yaml = os.path.join(REPO_ROOT, "_test_asset_defaults_bare_config.yaml")
    with open(cfg_yaml, "w", encoding="utf-8") as fh:
        fh.write("ship_graph: {}\nmulti_pathogen: {}\n")
    try:
        checker_paths = paths_from_run_config(REPO_ROOT, cfg_yaml)
    finally:
        os.unlink(cfg_yaml)
    assert os.path.basename(checker_paths["platform_dir"]) == asset_defaults.DEFAULT_PLATFORM_ID
    assert os.path.samefile(
        checker_paths["pathogen_file"],
        os.path.join(REPO_ROOT, asset_defaults.DEFAULT_PATHOGEN_PROFILES),
    )
