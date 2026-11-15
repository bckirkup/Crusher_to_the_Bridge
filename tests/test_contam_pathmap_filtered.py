"""PATHMAP-FILTERED carry-through and fail-loud endpoint tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

jsonschema = pytest.importorskip("jsonschema")

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.contamx_transport import ContamXTransportEngine  # noqa: E402
from engines.py_contam_bridge import ContamTransportEngine  # noqa: E402
from tools.contam_prj_bridge import export_prj_with_path_map  # noqa: E402

_EXPECTED = {
    "legend_class_nsc": {"medical_exhaust": 1},
    "mega_cruise_5000": {"Dining_to_Galley_Transfer": 10},
    "messy_cruise_500": {"Dining_to_Galley_Transfer": 10},
    "san_antonio_class_lpd": {
        "galley_exhaust_to_mess": 1,
        "medical_exhaust": 1,
    },
}
_SCHEMA_PATH = REPO_ROOT / "schemas" / "contam_path_map.schema.json"


def _load_platform(name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    base = REPO_ROOT / "data" / "platforms" / name
    spatial = json.loads((base / "spatial_layout.json").read_text())
    airflow = json.loads((base / "air_flow_paths.json").read_text())
    return spatial, airflow


def _filtered_entries(path_map: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [entry for entry in path_map if "filtered" in entry]


def _lane_paths(
    spatial: dict[str, Any],
    path_map: list[dict[str, Any]],
    entries: list[dict[str, Any]],
) -> list[Any]:
    flows = {int(entry["path_nr"]): 100.0 for entry in entries}
    engine = ContamXTransportEngine(
        spatial,
        path_map,
        flows,
        filter_efficiency=0.5,
        natural_decay_rate=0.0,
        path_map_entries=path_map,
    )
    target_nrs = {int(entry["path_nr"]) for entry in entries}
    return [
        path for path in engine.airflow_paths
        if path.path_type == "contamx_path"
        and int(path.path_id.split("_")[1]) in target_nrs
    ]


def _native_paths(
    spatial: dict[str, Any],
    airflow: dict[str, Any],
    kinds: set[str],
) -> list[Any]:
    engine = ContamTransportEngine(
        spatial,
        airflow,
        filter_efficiency=0.5,
        natural_decay_rate=0.0,
    )
    return [
        path for path in engine.airflow_paths
        if path.path_type == "cross_zone"
        and any(path.path_id.startswith(f"xzone_{kind}_") for kind in kinds)
    ]


@pytest.mark.parametrize("hobbyist", [False, True])
def test_path_map_carries_filtered_only_on_divergent_links(
    hobbyist: bool,
) -> None:
    for platform, expected in _EXPECTED.items():
        spatial, airflow = _load_platform(platform)
        _text, path_map = export_prj_with_path_map(
            spatial, airflow, hobbyist=hobbyist,
        )
        filtered_entries = _filtered_entries(path_map)
        assert len(filtered_entries) == sum(expected.values())
        for entry in filtered_entries:
            assert entry["filtered"] is False
            assert entry["is_hvac_ducted"] is True
        for kind, count in expected.items():
            rows = [
                entry for entry in filtered_entries if entry["kind"] == kind
            ]
            assert len(rows) == count

        round_tripped = json.loads(json.dumps(path_map))
        lane_paths = _lane_paths(spatial, round_tripped, filtered_entries)
        assert len(lane_paths) == len(filtered_entries)
        for path in lane_paths:
            assert path.filtered is False
            assert path.is_hvac_ducted is True

        native_paths = _native_paths(spatial, airflow, set(expected))
        assert len(native_paths) == len(filtered_entries)
        native_by_pair = {
            (path.from_zone, path.to_zone): path.filtered
            for path in native_paths
        }
        lane_by_pair = {
            (path.from_zone, path.to_zone): path.filtered
            for path in lane_paths
        }
        assert lane_by_pair == native_by_pair
        assert set(lane_by_pair.values()) == {False}


def test_path_map_filtered_absent_resolves_to_ducted_alias() -> None:
    spatial, airflow = _load_platform("legend_class_nsc")
    _text, path_map = export_prj_with_path_map(spatial, airflow)
    legacy_entries = [
        {key: value for key, value in entry.items() if key != "filtered"}
        for entry in path_map
    ]
    targets = [
        entry for entry in legacy_entries if entry["kind"] == "galley_supply"
    ]
    assert targets
    lane_paths = _lane_paths(spatial, legacy_entries, targets)
    assert len(lane_paths) == len(targets)
    for path in lane_paths:
        assert path.filtered is True


def test_path_map_schema_contract() -> None:
    schema = json.loads(_SCHEMA_PATH.read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    base = {
        "path_nr": 1,
        "from_zone": "A",
        "to_zone": "ambient",
        "is_hvac_ducted": False,
        "kind": "cross_zone",
        "crusher_transfer": True,
        "ahs_nr": 0,
    }
    jsonschema.validate([base], schema)
    jsonschema.validate(
        [{
            **base,
            "filtered": False,
            "sink": True,
            "declared_flow_m3h": 0.0,
        }],
        schema,
    )
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            [{key: value for key, value in base.items() if key != "path_nr"}],
            schema,
        )


@pytest.mark.parametrize("endpoint", ["from", "to"])
def test_exporter_raises_on_unresolved_cross_zone_endpoint(
    endpoint: str,
) -> None:
    spatial, airflow = _load_platform("destroyer_baseline")
    airflow = json.loads(json.dumps(airflow))
    link = {
        "from": "MedBay",
        "to": "Mess_Hall",
        "flow_rate_m3h": 10.0,
        "path": "unresolved_endpoint_test",
    }
    link[endpoint] = "Missing_Zone"
    airflow["cross_zone_links"] = [link]
    with pytest.raises(
        ValueError,
        match="cross_zone_links endpoint 'Missing_Zone'",
    ):
        export_prj_with_path_map(spatial, airflow)
