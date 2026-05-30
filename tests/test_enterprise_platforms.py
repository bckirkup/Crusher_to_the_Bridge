"""Referential integrity for Star Trek Enterprise example platforms."""

from __future__ import annotations

import json
import os

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO_ROOT, "data")

ENTERPRISE_PLATFORMS = (
    "enterprise_constitution_tos",
    "enterprise_galaxy_tng",
)


def _load(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.mark.parametrize("platform", ENTERPRISE_PLATFORMS)
def test_enterprise_platform_hvac_references(platform: str) -> None:
    base = os.path.join(DATA, "platforms", platform)
    layout = _load(os.path.join(base, "spatial_layout.json"))
    paths = _load(os.path.join(base, "air_flow_paths.json"))
    zone_ids = {z["id"] for z in layout["zones"]}
    assert "Mess_Hall" in zone_ids
    for hz in paths["hvac_zones"]:
        for room in hz["rooms"]:
            assert room in zone_ids, f"{platform}: HVAC room {room!r} missing from layout"
    hvac_ids = {hz["id"] for hz in paths["hvac_zones"]}
    for link in paths.get("cross_zone_links", []):
        assert link["from"] in hvac_ids
        assert link["to"] in hvac_ids


@pytest.mark.parametrize("profile_file", ("enterprise_tos_profiles.json", "enterprise_tng_profiles.json"))
def test_enterprise_pathogen_profiles(profile_file: str) -> None:
    data = _load(os.path.join(DATA, "pathogens", profile_file))
    assert len(data["pathogens"]) >= 2
    for p in data["pathogens"]:
        assert len(p["shedding_curve_log10"]) == 15
        assert len(p["asymptomatic_shedding_log10"]) == 15


def test_enterprise_template_fractions_sum() -> None:
    for name in ("enterprise_constitution_tos.json", "enterprise_galaxy_tng.json"):
        tmpl = _load(os.path.join(DATA, "templates", name))
        total = sum(c["fraction"] for c in tmpl["agent_classes"])
        assert abs(total - 1.0) < 0.01, f"{name} agent_classes sum to {total}"
