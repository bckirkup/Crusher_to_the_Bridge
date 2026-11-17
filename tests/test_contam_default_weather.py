"""CONTAM-DEFAULT-WEATHER-01: one declared relative wind per exported hull."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tools.contam_hobbyist import (
    DEFAULT_RELATIVE_WIND_DIRECTION_DEG,
    DEFAULT_RELATIVE_WIND_SPEED_M_S,
    load_hobbyist_overrides,
    resolve_relative_wind,
)
from tools.contam_prj_bridge import export_prj_with_path_map

REPO_ROOT = Path(__file__).resolve().parents[1]
PLATFORMS = REPO_ROOT / "data" / "platforms"
BUNDLED = sorted(p.parent.parent.name for p in PLATFORMS.glob("*/contam/platform.prj"))


def _steady_wind(text: str) -> tuple[float, float]:
    line = next(row for row in text.splitlines() if row.endswith("! steady simulation"))
    tokens = line.split()
    return float(tokens[2]), float(tokens[3])


def _path_rows(text: str) -> list[list[str]]:
    lines = text.splitlines()
    start = next(i for i, row in enumerate(lines) if row.endswith("! flow paths:"))
    rows = []
    for row in lines[start + 2:]:
        if row.startswith("-999"):
            break
        rows.append(row.split())
    return rows


def _load(name: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    root = PLATFORMS / name
    spatial = json.loads((root / "spatial_layout.json").read_text(encoding="utf-8"))
    airflow = json.loads((root / "air_flow_paths.json").read_text(encoding="utf-8"))
    return spatial, airflow, load_hobbyist_overrides(str(root))


def _export(name: str, **extra: Any) -> str:
    spatial, airflow, overrides = _load(name)
    text, _ = export_prj_with_path_map(
        spatial, airflow, hobbyist=True, overrides={**overrides, **extra},
        ahs_terminal_mode="commissioned",
    )
    return text


def test_default_is_the_declared_constant() -> None:
    assert resolve_relative_wind({}) == (
        DEFAULT_RELATIVE_WIND_SPEED_M_S, DEFAULT_RELATIVE_WIND_DIRECTION_DEG,
    )
    assert DEFAULT_RELATIVE_WIND_SPEED_M_S > 0.0


@pytest.mark.parametrize("bad", [
    {"relative_wind_speed_m_s": -1.0},
    {"relative_wind_direction_deg": 360.0},
    {"relative_wind_direction_deg": -5.0},
    {"relative_wind_speed_m_s": float("nan")},
    {"relative_wind_speed_m_s": float("inf")},
])
def test_invalid_override_is_rejected(bad: dict[str, float]) -> None:
    with pytest.raises(ValueError, match="relative_wind"):
        resolve_relative_wind(bad)


@pytest.mark.parametrize("speed,direction", [(1.0, 0.0), (3.5, 90.0), (10.0, 270.0)])
def test_override_sets_the_header_and_nothing_per_path(
    speed: float, direction: float,
) -> None:
    base = _export("destroyer_baseline")
    moved = _export(
        "destroyer_baseline", relative_wind_speed_m_s=speed,
        relative_wind_direction_deg=direction,
    )
    assert _steady_wind(moved) == (speed, direction)
    # One constant: the speed lives in the weather line only.
    assert _path_rows(moved) == _path_rows(base)


def test_calm_override_clears_every_wind_flag() -> None:
    calm = _export("destroyer_baseline", relative_wind_speed_m_s=0.0)
    assert _steady_wind(calm)[0] == pytest.approx(0.0)
    rows = _path_rows(calm)
    assert any(int(row[6]) > 0 for row in rows)
    assert all(int(row[1]) & 1 == 0 for row in rows)


def test_skeleton_export_carries_no_wind() -> None:
    spatial, airflow, _ = _load("destroyer_baseline")
    text, _ = export_prj_with_path_map(spatial, airflow, hobbyist=False)
    assert _steady_wind(text) == (0.0, 0.0)
    assert all(int(row[1]) & 1 == 0 for row in _path_rows(text))


@pytest.mark.parametrize("name", BUNDLED)
def test_committed_bundle_weather_is_internally_consistent(name: str) -> None:
    text = (PLATFORMS / name / "contam" / "platform.prj").read_text(encoding="utf-8")
    _, airflow, overrides = _load(name)
    speed, direction = resolve_relative_wind(overrides)
    assert _steady_wind(text) == (speed, direction)
    rows = _path_rows(text)
    profiled = [row for row in rows if int(row[6]) > 0]
    assert profiled, "every bundled hull has envelope leaks on a wind profile"
    # Profile-carrying paths keep the one modifier and no constant pressure;
    # the wind flag is set only when the hull's resolved speed is nonzero.
    assert {float(row[16]) for row in profiled} == {0.8}
    assert all(float(row[15]) == pytest.approx(0.0) for row in rows)
    expected_wind_flag = 1 if speed > 0.0 else 0
    assert all((int(row[1]) & 1) == expected_wind_flag for row in profiled)
    if speed > 0.0:
        assert all(int(row[6]) > 0 for row in rows if int(row[1]) & 1)
    # No per-record drift: a declared opening speed is the hull's speed.
    declared = {
        float(record["wind_speed_m_s"])
        for record in airflow.get("ambient_openings", [])
        if record.get("wind_speed_m_s")
    }
    assert declared <= {speed}
