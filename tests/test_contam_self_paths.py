"""CONTAM-OLYMPIA-SELFPATH-01: fleet guard against zone -> same-zone paths."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.py_contam_bridge import ContamTransportEngine  # noqa: E402
from tools.contam_hobbyist import load_hobbyist_overrides  # noqa: E402
from tools.contam_prj_bridge import export_prj_with_path_map  # noqa: E402

_PLATFORMS = REPO_ROOT / "data" / "platforms"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _platform_dirs() -> list[Path]:
    return sorted(
        path for path in _PLATFORMS.iterdir()
        if path.is_dir()
        and (path / "spatial_layout.json").is_file()
        and (path / "air_flow_paths.json").is_file()
    )


def _bundled_platform_dirs() -> list[Path]:
    return sorted(
        path for path in _platform_dirs()
        if (path / "contam" / "platform.prj").is_file()
        and (path / "contam" / "path_map.json").is_file()
    )


def _self_path_ids(entries: list[dict[str, Any]]) -> list[Any]:
    return [
        entry.get("path_nr", entry.get("path_id"))
        for entry in entries
        if entry.get("from_zone") == entry.get("to_zone")
    ]


def test_native_fleet_emits_no_self_paths() -> None:
    offenders = []
    for platform in _platform_dirs():
        spatial = _load_json(platform / "spatial_layout.json")
        airflow = _load_json(platform / "air_flow_paths.json")
        engine = ContamTransportEngine(spatial, airflow)
        bad = _self_path_ids([
            {
                "path_id": path.path_id,
                "from_zone": path.from_zone,
                "to_zone": path.to_zone,
            }
            for path in engine.airflow_paths
        ])
        if bad:
            offenders.append((platform.name, bad))
    assert offenders == []


def test_export_lane_fleet_emits_no_self_paths() -> None:
    offenders = []
    for platform in _bundled_platform_dirs():
        spatial = _load_json(platform / "spatial_layout.json")
        airflow = _load_json(platform / "air_flow_paths.json")
        _text, path_map = export_prj_with_path_map(
            spatial,
            airflow,
            hobbyist=True,
            overrides=load_hobbyist_overrides(str(platform)),
            ahs_terminal_mode="commissioned",
        )
        bad = _self_path_ids(path_map)
        if bad:
            offenders.append((platform.name, bad))
    assert offenders == []
