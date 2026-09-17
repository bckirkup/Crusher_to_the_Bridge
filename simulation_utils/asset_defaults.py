"""Canonical default locations of the shared data assets under ``data/``.

Every module that falls back to an on-disk asset when its config omits the
key reads that fallback from here, and ``CatalogRegistry`` scans the same
directories, so the repository layout is declared exactly once. Paths are
relative to the repository root; resolve them with
:func:`simulation_utils.paths.resolve_repo_path` (or ``os.path.join``).

The canonical default platform is ``mega_cruise_5000``: it is the platform
``crusher_labs/config.yaml`` ships with and the one the dashboard and the
sanity checker already default to. Picard JSON run specs declare their own
``catalog.platform_id`` and are not covered by this fallback.
"""

from __future__ import annotations

import os

DATA_DIR = "data"
PLATFORMS_DIR = os.path.join(DATA_DIR, "platforms")
PATHOGENS_DIR = os.path.join(DATA_DIR, "pathogens")
CONFIG_DIR = os.path.join(DATA_DIR, "config")

SPATIAL_LAYOUT_FILENAME = "spatial_layout.json"
AIR_FLOW_PATHS_FILENAME = "air_flow_paths.json"

DEFAULT_PLATFORM_ID = "mega_cruise_5000"
DEFAULT_PATHOGEN_BUNDLE_ID = "active_profiles"


def platform_dir_rel(platform_id: str = DEFAULT_PLATFORM_ID) -> str:
    return os.path.join(PLATFORMS_DIR, platform_id)


def platform_spatial_layout_rel(platform_id: str = DEFAULT_PLATFORM_ID) -> str:
    return os.path.join(platform_dir_rel(platform_id), SPATIAL_LAYOUT_FILENAME)


def platform_air_flow_paths_rel(platform_id: str = DEFAULT_PLATFORM_ID) -> str:
    return os.path.join(platform_dir_rel(platform_id), AIR_FLOW_PATHS_FILENAME)


def pathogen_bundle_rel(bundle_id: str = DEFAULT_PATHOGEN_BUNDLE_ID) -> str:
    return os.path.join(PATHOGENS_DIR, f"{bundle_id}.json")


def config_file_rel(filename: str) -> str:
    return os.path.join(CONFIG_DIR, filename)


DEFAULT_SPATIAL_LAYOUT = platform_spatial_layout_rel()
DEFAULT_AIR_FLOW_PATHS = platform_air_flow_paths_rel()
DEFAULT_PATHOGEN_PROFILES = pathogen_bundle_rel()

PROTOCOLS_CONFIG = config_file_rel("protocols.json")
RESOURCE_COSTS_CONFIG = config_file_rel("resource_costs.json")
LOGGING_PROFILE_CONFIG = config_file_rel("logging_profile.json")
INSTRUMENT_TURNAROUND_CONFIG = config_file_rel("instrument_turnaround.json")
LONG_READ_SEQUENCING_PARAMS_CONFIG = config_file_rel("long_read_sequencing_params.json")
