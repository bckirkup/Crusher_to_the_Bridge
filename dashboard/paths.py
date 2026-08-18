"""Repository paths for dashboard data loading."""
from __future__ import annotations

import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLATFORMS_DIR = os.path.join(REPO_ROOT, "data", "platforms")
CONFIG_YAML = os.path.join(REPO_ROOT, "crusher_labs", "config.yaml")
PATHOGEN_PATH = os.path.join(REPO_ROOT, "data", "pathogens", "active_profiles.json")
PROTOCOLS_PATH = os.path.join(REPO_ROOT, "data", "config", "protocols.json")
DEFAULT_FLEET_OUTPUT = os.path.join(
    REPO_ROOT, "presidio", "data", "experiences", "smoke_runs",
)
# Catalog default for the LCARS GUI when telemetry does not fingerprint a class.
DEFAULT_PLATFORM_ID = "mega_cruise_5000"
DEFAULT_PICARD_SPEC = os.path.join(
    REPO_ROOT, "picard_framework", "runs", "destroyer_baseline_default.json",
)

HISTORY_PATH = os.path.join(REPO_ROOT, "telemetry_buffer", "simulation_history.json")
NOTEBOOK_PATH = os.path.join(REPO_ROOT, "telemetry_buffer", "artificial_lab_notebook.json")

SPATIAL_LAYOUT_JSON = "spatial_layout.json"
ALL_DECKS_LABEL = "All Decks"
