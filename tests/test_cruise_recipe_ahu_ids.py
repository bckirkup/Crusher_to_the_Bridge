"""Recipe-generated HVAC groups carry unique ids and cover each room once."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from cruise_platform_recipes import RECIPES  # noqa: E402
from generate_cruise_platform_layout import (  # noqa: E402
    build_air_flow_paths,
    build_spatial_layout,
)


@pytest.mark.parametrize("platform_id", sorted(RECIPES))
def test_generated_hvac_group_ids_are_unique(platform_id: str) -> None:
    recipe = RECIPES[platform_id]
    zone_ids = {zone["id"] for zone in build_spatial_layout(recipe)["zones"]}
    groups = build_air_flow_paths(recipe, zone_ids)["hvac_zones"]
    ids = Counter(group["id"] for group in groups)
    assert [gid for gid, n in ids.items() if n > 1] == []
    rooms = Counter(room for group in groups for room in group["rooms"])
    assert [room for room, n in rooms.items() if n > 1] == []


def test_extra_banks_sharing_a_deck_share_one_ahu() -> None:
    recipe = RECIPES["explorer_seas_06"]
    zone_ids = {zone["id"] for zone in build_spatial_layout(recipe)["zones"]}
    groups = {
        group["id"]: group["rooms"]
        for group in build_air_flow_paths(recipe, zone_ids)["hvac_zones"]
    }
    assert sorted(groups["AHU_PC_D2"]) == [
        "PC_D2_P_A", "PC_D2_P_F", "PC_D2_S_A", "PC_D2_S_F",
    ]
    assert sorted(groups["AHU_PC_D3"]) == [
        "PC_D3_P_F", "PC_D3_P_M", "PC_D3_S_F", "PC_D3_S_M",
    ]
