"""CONTAM-NATIVE-PATHID-DEDUPE-01: native diagnostic path ids are unique."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.py_contam_bridge import ContamTransportEngine  # noqa: E402

_PLATFORMS = REPO_ROOT / "data" / "platforms"


def _platform_dirs() -> list[Path]:
    return sorted(
        path for path in _PLATFORMS.iterdir()
        if path.is_dir()
        and (path / "spatial_layout.json").is_file()
        and (path / "air_flow_paths.json").is_file()
    )


def test_native_fleet_path_ids_are_unique() -> None:
    offenders = []
    for platform in _platform_dirs():
        spatial = json.loads(
            (platform / "spatial_layout.json").read_text(encoding="utf-8"),
        )
        airflow = json.loads(
            (platform / "air_flow_paths.json").read_text(encoding="utf-8"),
        )
        engine = ContamTransportEngine(spatial, airflow)
        ids = [path.path_id for path in engine.airflow_paths]
        counts = Counter(ids)
        duplicates = {
            path_id: count for path_id, count in counts.items() if count > 1
        }
        if duplicates:
            offenders.append((platform.name, duplicates))
    assert offenders == []
