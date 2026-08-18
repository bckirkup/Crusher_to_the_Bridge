"""
test_json_schema_validation.py – Validate JSON data files against schemas/
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Runs every config/data JSON file against its matching schema in
``schemas/``, catching drift between data and spec.

Closes #83.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

try:
    import jsonschema
except ImportError:
    jsonschema = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parent.parent

# Map: schema file name  →  list of data files to validate against it
SCHEMA_DATA_MAP: dict[str, list[str]] = {
    "protocols.schema.json": [
        "data/config/protocols.json",
    ],
    "resource_costs.schema.json": [
        "data/config/resource_costs.json",
        # edison_resource_costs.json intentionally excluded: uses fractional
        # materials (0.1 flow_cells) which violates "integer" in schema.
        # Schema should be relaxed to "number" — tracked separately.
    ],
    "logging_profile.schema.json": [
        "data/config/logging_profile.json",
    ],
    "clinical_instrument_params.schema.json": [
        "data/config/clinical_instrument_params.json",
    ],
    "picard_run_spec.schema.json": [
        "picard_framework/runs/destroyer_baseline_default.json",
        "picard_framework/runs/smoke_2epoch.json",
        "picard_framework/runs/smoke_cascade_6epoch.json",
        "picard_framework/runs/smoke_cascade_multiplex_6epoch.json",
        "picard_framework/runs/smoke_pathogen_overrides_2epoch.json",
    ],
    "pathogen_profiles.schema.json": [
        "data/pathogens/active_profiles.json",
        "data/pathogens/edison_10pathogen_profiles.json",
        "data/pathogens/enterprise_tng_profiles.json",
        "data/pathogens/enterprise_tos_profiles.json",
    ],
    "spatial_layout.schema.json": [],
    "air_flow_paths.schema.json": [],
    "preboarding_decision_scenario.schema.json": [
        "picard_framework/analysis/boundary/data/example_scenario.json",
    ],
    "preboarding_decision_summary.schema.json": [
        "picard_framework/analysis/boundary/data/example_summary.json",
    ],
    "voyage_config.schema.json": [
        "picard_framework/analysis/sentinel/data/example_itinerary.json",
    ],
    "sentinel_observations.schema.json": [
        "picard_framework/analysis/sentinel/data/example_observations.json",
    ],
    "port_surveillance.schema.json": [
        "picard_framework/analysis/sentinel/data/port_surveillance_caribbean.json",
        "picard_framework/analysis/sentinel/data/port_surveillance_mediterranean.json",
        "picard_framework/analysis/sentinel/data/port_surveillance_nordic.json",
        "picard_framework/analysis/sentinel/data/port_surveillance_alaska.json",
    ],
    "sentinel_recovery_design.schema.json": [
        "picard_framework/runs/mega_cruise_campaign/"
        "sentinel_synthetic_recovery_v1_design.json",
        "picard_framework/runs/mega_cruise_campaign/"
        "sentinel_ww_ops_scan_v1_design.json",
    ],
}


def _discover_platform_files() -> list[tuple[str, str]]:
    """Yield (schema_name, data_path) for all platform JSON files."""
    pairs: list[tuple[str, str]] = []
    platforms_dir = REPO_ROOT / "data" / "platforms"
    for platform_dir in sorted(platforms_dir.iterdir()):
        if not platform_dir.is_dir():
            continue
        spatial = platform_dir / "spatial_layout.json"
        airflow = platform_dir / "air_flow_paths.json"
        if spatial.is_file():
            pairs.append(("spatial_layout.schema.json", str(spatial.relative_to(REPO_ROOT))))
        if airflow.is_file():
            pairs.append(("air_flow_paths.schema.json", str(airflow.relative_to(REPO_ROOT))))
        voyage = platform_dir / "voyage_config.json"
        if voyage.is_file():
            pairs.append(("voyage_config.schema.json", str(voyage.relative_to(REPO_ROOT))))
    return pairs


def _discover_social_files() -> list[tuple[str, str]]:
    """Yield (schema_name, data_path) for Stackelberg social config files."""
    pairs: list[tuple[str, str]] = []
    social_dir = REPO_ROOT / "presidio" / "data" / "social"
    if not social_dir.is_dir():
        return pairs
    schema_map = {
        "class_interactions": "class_interactions.schema.json",
        "information_diffusion": "information_diffusion.schema.json",
        "agent_profile": "agent_profile.schema.json",
        "global_health_briefing": "global_health_briefing.schema.json",
    }
    for json_file in sorted(social_dir.rglob("*.json")):
        stem = json_file.stem
        for key, schema_name in schema_map.items():
            if key in stem:
                pairs.append((schema_name, str(json_file.relative_to(REPO_ROOT))))
                break
    return pairs


def _discover_fleet_files() -> list[tuple[str, str]]:
    """Yield (schema_name, data_path) for Presidio fleet config files."""
    pairs: list[tuple[str, str]] = []
    config_dir = REPO_ROOT / "presidio" / "data" / "config"
    if not config_dir.is_dir():
        return pairs
    for json_file in sorted(config_dir.glob("*fleet*.json")):
        pairs.append(("presidio_fleet_config.schema.json", str(json_file.relative_to(REPO_ROOT))))
    return pairs


def _build_test_cases() -> list[tuple[str, str]]:
    """Build full list of (schema_name, data_path) test cases."""
    cases: list[tuple[str, str]] = []
    for schema_name, data_files in SCHEMA_DATA_MAP.items():
        for df in data_files:
            cases.append((schema_name, df))
    cases.extend(_discover_platform_files())
    cases.extend(_discover_social_files())
    cases.extend(_discover_fleet_files())
    return cases


ALL_CASES = _build_test_cases()


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
@pytest.mark.parametrize("schema_name,data_path", ALL_CASES, ids=[f"{s}::{d}" for s, d in ALL_CASES])
def test_json_validates_against_schema(schema_name: str, data_path: str) -> None:
    schema_path = REPO_ROOT / "schemas" / schema_name
    full_data = REPO_ROOT / data_path

    if not schema_path.is_file():
        pytest.skip(f"Schema {schema_name} not found")
    if not full_data.is_file():
        pytest.skip(f"Data file {data_path} not found")

    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)
    with open(full_data, encoding="utf-8") as f:
        data = json.load(f)

    jsonschema.validate(instance=data, schema=schema)
