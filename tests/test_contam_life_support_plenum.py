"""Offline tests for the fiction life-support plenum Contam boundary."""

from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.contam_hobbyist import load_hobbyist_overrides  # noqa: E402
from tools.contamw34_prj import _assemble_network  # noqa: E402

_HULLS = ("enterprise_constitution_tos", "enterprise_galaxy_tng")


def _load_platform(name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    base = REPO_ROOT / "data" / "platforms" / name
    spatial = json.loads((base / "spatial_layout.json").read_text())
    airflow = json.loads((base / "air_flow_paths.json").read_text())
    return spatial, airflow


def _overrides(name: str) -> dict[str, Any]:
    return load_hobbyist_overrides(str(REPO_ROOT / "data" / "platforms" / name))


def _net(
    name: str,
    lane: str = "design",
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    spatial, airflow = _load_platform(name)
    return _assemble_network(
        spatial,
        airflow,
        hobbyist=True,
        overrides=_overrides(name) if overrides is None else overrides,
        ahs_terminal_mode=lane,
    )


def _without_plenum(overrides: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(overrides)
    out.pop("life_support_plenum", None)
    return out


def _kind(path_map: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [entry for entry in path_map if entry.get("kind") == kind]


def _expected_relief_flow(
    spatial: dict[str, Any],
    airflow: dict[str, Any],
    lane: str,
) -> float:
    explicit_exhaust = sum(
        float(link.get("flow_rate_m3h", 0.0))
        for link in airflow.get("cross_zone_links", [])
        if str(link.get("to")) == "ambient"
    )
    if lane == "design":
        return explicit_exhaust
    volumes = {z["id"]: float(z.get("volume_m3") or 0.0) for z in spatial["zones"]}
    default_duty = float(airflow.get("hvac_duty", 1.0) or 0.0)
    exhaust_only = 0.0
    for hvac in airflow.get("hvac_zones", []):
        duty = hvac.get("hvac_duty")
        duty = default_duty if duty is None else float(duty)
        if duty <= 0.0:
            exhaust_only += float(hvac.get("ach", 0.0)) * sum(
                volumes.get(room, 0.0) for room in hvac.get("rooms", [])
            )
    return explicit_exhaust + exhaust_only


@pytest.mark.parametrize("hull", _HULLS)
def test_plenum_replaces_envelope_leaks_and_declared_openings(hull: str) -> None:
    spatial, _airflow = _load_platform(hull)
    baseline = _net(hull, overrides=_without_plenum(_overrides(hull)))
    plenum = _net(hull)

    envelope = _kind(baseline["path_map"], "envelope_leak")
    life_links = _kind(plenum["path_map"], "life_support_link")
    assert len(life_links) == len(spatial["zones"])
    assert len(life_links) == len(envelope)
    assert not _kind(plenum["path_map"], "envelope_leak")

    ambient = _kind(plenum["path_map"], "ambient_opening")
    assert ambient
    assert {entry["from_zone"] for entry in ambient} == {"LS_Plenum"}
    boundary = life_links + ambient
    assert all(entry["crusher_transfer"] is False for entry in boundary)
    assert all(entry["is_hvac_ducted"] is False for entry in life_links)


def test_disabled_plenum_keeps_envelope_leaks() -> None:
    overrides = _overrides("enterprise_galaxy_tng")
    overrides["life_support_plenum"]["enabled"] = False
    net = _net("enterprise_galaxy_tng", overrides=overrides)

    assert _kind(net["path_map"], "envelope_leak")
    assert not _kind(net["path_map"], "life_support_link")
    assert "life_support_plenum" not in net


def test_empty_plenum_config_uses_defaults() -> None:
    overrides = _overrides("enterprise_galaxy_tng")
    overrides["life_support_plenum"] = {}
    net = _net("enterprise_galaxy_tng", overrides=overrides)

    assert _kind(net["path_map"], "life_support_link")
    assert not _kind(net["path_map"], "envelope_leak")
    assert net["life_support_plenum"]["link_area_m2"] == pytest.approx(0.2)


@pytest.mark.parametrize("hull", _HULLS)
@pytest.mark.parametrize("lane", ("design", "commissioned"))
def test_relief_flow_matches_declared_ambient_balance(
    hull: str,
    lane: str,
) -> None:
    spatial, airflow = _load_platform(hull)
    net = _net(hull, lane=lane)
    summary = net["life_support_plenum"]
    expected = _expected_relief_flow(spatial, airflow, lane)

    assert summary["relief_flow_m3h"] == pytest.approx(expected, abs=1e-6)
    assert summary["relief_area_m2"] == pytest.approx(
        expected / 3600.0 / summary["relief_face_velocity_m_s"],
        rel=1e-9,
    )
    assert summary["relief_flow_m3h"] > 0.0
    assert math.isfinite(summary["relief_area_m2"])


def test_link_area_and_face_velocity_are_live_knobs() -> None:
    spatial, _airflow = _load_platform("enterprise_galaxy_tng")
    base = _overrides("enterprise_galaxy_tng")

    link_areas = []
    for area in (0.02, 0.2, 1.0):
        overrides = copy.deepcopy(base)
        overrides["life_support_plenum"]["link_area_m2"] = area
        net = _assemble_network(
            spatial,
            _airflow,
            hobbyist=True,
            overrides=overrides,
            ahs_terminal_mode="design",
        )
        element = next(
            element for element in net["elements"]
            if str(element.get("name", "")).startswith("LifeSup")
        )
        link_areas.append(float(element["area_m2"]))
    assert link_areas == pytest.approx([0.02, 0.2, 1.0])

    face_velocities = []
    relief_areas = []
    relief_flows = []
    for velocity in (1.0, 2.5, 5.0):
        overrides = copy.deepcopy(base)
        overrides["life_support_plenum"]["relief_face_velocity_m_s"] = velocity
        net = _assemble_network(
            spatial,
            _airflow,
            hobbyist=True,
            overrides=overrides,
            ahs_terminal_mode="design",
        )
        summary = net["life_support_plenum"]
        relief_flows.append(float(summary["relief_flow_m3h"]))
        relief_areas.append(float(summary["relief_area_m2"]))
        face_velocities.append(float(summary["relief_face_velocity_m_s"]))

    assert relief_flows[1] == pytest.approx(relief_flows[0])
    assert relief_flows[2] == pytest.approx(relief_flows[0])
    assert face_velocities == pytest.approx([1.0, 2.5, 5.0])
    assert relief_areas == pytest.approx(
        [relief_flows[0] / 3600.0 / v for v in face_velocities],
        rel=1e-9,
    )
    assert relief_areas == sorted(relief_areas, reverse=True)


def test_plenum_zone_id_collision_fails_loud() -> None:
    overrides = _overrides("enterprise_galaxy_tng")
    overrides["life_support_plenum"]["zone_id"] = "Bridge"
    spatial, airflow = _load_platform("enterprise_galaxy_tng")
    with pytest.raises(ValueError, match="already exists"):
        _assemble_network(
            spatial,
            airflow,
            hobbyist=True,
            overrides=overrides,
            ahs_terminal_mode="design",
        )
