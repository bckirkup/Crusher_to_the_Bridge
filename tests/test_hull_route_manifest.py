"""Arm B-only route-attribution manifest contract."""
from __future__ import annotations

from scripts.build_hull_compounding_v1_manifest import build
from simulation_utils.platform_complement import declared_total


def test_arm_b_manifest_is_the_matched_1800_run_probe() -> None:
    manifest = build(arm_b_only=True)

    assert manifest["campaign"] == "hull_compounding_route_v1"
    assert "no posting" in manifest["description"]
    assert len(manifest["tiers"]) == 6
    assert sum(len(tier["seeds"]) for tier in manifest["tiers"].values()) == 1800

    expected_agents = {
        "rl_cls_occ25_7d": round(0.25 * declared_total("classic_cruise_1900")),
        "rl_cls_occ50_7d": round(0.50 * declared_total("classic_cruise_1900")),
        "rl_cls_occ100_7d": round(1.00 * declared_total("classic_cruise_1900")),
        "rl_spr_occ25_7d": round(0.25 * declared_total("spirit_cruise_3000")),
        "rl_spr_occ50_7d": round(0.50 * declared_total("spirit_cruise_3000")),
        "rl_spr_occ100_7d": round(1.00 * declared_total("spirit_cruise_3000")),
    }
    for tier_id, tier in manifest["tiers"].items():
        assert tier["platform"] in {
            "classic_cruise_1900",
            "spirit_cruise_3000",
        }
        assert tier["num_agents"] == expected_agents[tier_id]
        assert len(tier["seeds"]) == 300
        assert tier["epoch_durations"] == [168]
        assert "mechanism probe ONLY" in tier["description"]
        assert "config_overrides" not in tier
