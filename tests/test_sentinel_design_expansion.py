"""
test_sentinel_design_expansion.py – design spec → sentinel campaign manifest
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The checked-in sentinel manifest is a generated artifact. These tests hold the
expansion deterministic, keep the manifest in sync with its design spec (drift
test), and check that the runner reads itinerary templates from configuration
rather than from code.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from picard_framework.runs.mega_cruise_campaign import expand_design, sentinel_recovery

REPO_ROOT = Path(__file__).resolve().parent.parent
CAMPAIGN = REPO_ROOT / "picard_framework" / "runs" / "mega_cruise_campaign"
DESIGN = CAMPAIGN / "sentinel_synthetic_recovery_v1_design.json"
MANIFEST = CAMPAIGN / "sentinel_synthetic_recovery_v1_manifest.json"


@pytest.fixture(name="design")
def design_fixture() -> dict[str, Any]:
    return json.loads(DESIGN.read_text(encoding="utf-8"))


def _port_days(days: list[dict[str, Any]]) -> list[tuple[int, str]]:
    return [
        (int(day["day"]), str(day["port_id"]))
        for day in days
        if day.get("type") == "port_day"
    ]


def test_checked_in_manifest_matches_design_expansion() -> None:
    """Drift test: the manifest must equal the expansion of its design spec."""
    expanded = expand_design.manifest_from_design_file(str(DESIGN))
    on_disk = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert expanded == on_disk


def test_expansion_is_deterministic() -> None:
    first = expand_design.manifest_from_design_file(str(DESIGN))
    second = expand_design.manifest_from_design_file(str(DESIGN))
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_tier_count_and_total_runs(design: dict[str, Any]) -> None:
    manifest = expand_design.build_manifest(design)
    n_hazard = len(design["hazard_profiles"])
    n_fleet = len(design["fleet_configs"])
    assert len(manifest["tiers"]) == n_hazard * n_fleet
    assert manifest["total_runs"] == 3360


def test_total_runs_scales_with_seed_count(design: dict[str, Any]) -> None:
    """Halving the seed block halves the campaign; doubling R doubles it."""
    base = expand_design.build_manifest(design)["total_runs"]
    fewer = copy.deepcopy(design)
    fewer["seeds"] = {"start": 300, "count": 10}
    more_r = copy.deepcopy(design)
    more_r["R_onboard_values"] = [*design["R_onboard_values"], 2.0]
    assert expand_design.build_manifest(fewer)["total_runs"] == base // 2
    assert expand_design.build_manifest(more_r)["total_runs"] == base * 5 // 4


def test_seeds_may_be_listed_explicitly(design: dict[str, Any]) -> None:
    explicit = copy.deepcopy(design)
    explicit["seeds"] = [7, 11, 13]
    manifest = expand_design.build_manifest(explicit)
    assert manifest["tiers"]["sr_null_single"]["seeds"] == [7, 11, 13]


def test_templates_expand_to_slots_with_sea_days(design: dict[str, Any]) -> None:
    templates = expand_design.build_itinerary_templates(design)
    standard = templates["standard"]
    assert [day["type"] for day in standard] == [
        "embarkation",
        "sea_day",
        "port_day",
        "port_day",
        "sea_day",
        "port_day",
        "disembarkation",
    ]
    assert _port_days(standard) == [(3, "MXCZM"), (4, "MXCTM"), (6, "KYGEC")]


def test_variant_templates_cross_order_and_timing(design: dict[str, Any]) -> None:
    """The three fleet_crossed itineraries differ in port order and in day slots."""
    templates = expand_design.build_itinerary_templates(design)
    assert _port_days(templates["reversed"]) == [
        (3, "KYGEC"),
        (4, "MXCTM"),
        (6, "MXCZM"),
    ]
    assert _port_days(templates["staggered"]) == [
        (2, "MXCZM"),
        (4, "MXCTM"),
        (5, "KYGEC"),
    ]


def test_port_slots_carry_exposure_metadata(design: dict[str, Any]) -> None:
    templates = expand_design.build_itinerary_templates(design)
    cozumel = next(
        day for day in templates["standard"] if day.get("port_id") == "MXCZM"
    )
    assert cozumel["disembark_fraction"] == pytest.approx(0.72)
    assert cozumel["crew_shore_leave_fraction"] == pytest.approx(0.15)
    assert cozumel["reembark_window_epochs"] == [12, 15]


def test_hazard_profiles_land_on_their_tiers(design: dict[str, Any]) -> None:
    manifest = expand_design.build_manifest(design)
    one_hot = manifest["tiers"]["sr_one_hot_fleet_crossed"]["shore_exposure"]
    assert one_hot["port_hazards"]["MXCZM"] == pytest.approx(0.01)
    assert one_hot["port_hazards"]["KYGEC"] == pytest.approx(0.001)
    null = manifest["tiers"]["sr_null_single"]["shore_exposure"]["port_hazards"]
    assert set(null.values()) == {0.0}


def test_fleet_config_drives_platforms_and_itineraries(design: dict[str, Any]) -> None:
    manifest = expand_design.build_manifest(design)
    crossed = manifest["tiers"]["sr_gradient_fleet_crossed"]
    single = manifest["tiers"]["sr_gradient_single"]
    assert crossed["itineraries"] == ["standard", "reversed", "staggered"]
    assert single["platforms"] == ["mega_cruise_5000"]


def test_unknown_port_in_template_is_rejected(design: dict[str, Any]) -> None:
    broken = copy.deepcopy(design)
    broken["itinerary_templates"]["standard"]["port_days"]["3"] = "XXXXX"
    with pytest.raises(ValueError, match="unknown port_id"):
        expand_design.build_manifest(broken)


def test_port_call_outside_voyage_bounds_is_rejected(design: dict[str, Any]) -> None:
    broken = copy.deepcopy(design)
    broken["itinerary_templates"]["standard"]["port_days"]["7"] = "MXCZM"
    with pytest.raises(ValueError, match="strictly between"):
        expand_design.build_manifest(broken)


def test_unknown_itinerary_in_fleet_config_is_rejected(design: dict[str, Any]) -> None:
    broken = copy.deepcopy(design)
    broken["fleet_configs"]["single"]["ships"][0]["itinerary"] = "atlantic"
    with pytest.raises(ValueError, match="unknown itinerary"):
        expand_design.build_manifest(broken)


def test_hazard_profile_for_unknown_port_is_rejected(design: dict[str, Any]) -> None:
    broken = copy.deepcopy(design)
    broken["hazard_profiles"]["null"]["port_hazards"]["ZZZZZ"] = 0.0
    with pytest.raises(ValueError, match="unknown ports"):
        expand_design.build_manifest(broken)


def test_missing_required_key_names_the_key(design: dict[str, Any]) -> None:
    broken = copy.deepcopy(design)
    del broken["R_onboard_values"]
    with pytest.raises(ValueError, match="R_onboard_values"):
        expand_design.build_manifest(broken)


def test_runner_reads_templates_from_the_manifest() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    days = sentinel_recovery.itinerary_days(manifest, "staggered")
    assert _port_days(days) == [(2, "MXCZM"), (4, "MXCTM"), (5, "KYGEC")]


def test_runner_returns_copies_not_manifest_state() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    days = sentinel_recovery.itinerary_days(manifest, "standard")
    days[0]["day"] = 99
    assert manifest["itinerary_templates"]["standard"][0]["day"] == 1


def test_missing_template_asks_for_expansion() -> None:
    with pytest.raises(ValueError, match="expand_design"):
        sentinel_recovery.itinerary_days({"itinerary_templates": {}}, "standard")


def test_cli_check_mode_passes_on_the_checked_in_pair() -> None:
    assert expand_design.main(["--design", str(DESIGN), "--check"]) == 0


def test_check_mode_exits_nonzero_on_drift() -> None:
    expected = expand_design.manifest_from_design_file(str(DESIGN))
    drifted = copy.deepcopy(expected)
    drifted["total_runs"] = 1
    assert expand_design.report_drift(expected, drifted) == 1


def test_manifest_is_written_where_asked(tmp_path: Path) -> None:
    """Writes stay inside the repository: an outside path is refused."""
    manifest = expand_design.manifest_from_design_file(str(DESIGN))
    with pytest.raises(ValueError, match="outside allowed roots"):
        expand_design.write_manifest(manifest, str(tmp_path / "manifest.json"))
