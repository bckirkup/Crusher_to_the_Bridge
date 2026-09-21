"""The per_host_dose_challenge sweep args reach only config_overrides.transmission."""

from __future__ import annotations

import pytest

from tools.noro_diag import per_host_dose_challenge as pdc


def _spec(**kwargs):
    return pdc.build_spec(
        seed=9000, platform="classic_cruise_1900",
        bundle="active_profiles", epochs=24, num_agents=1910,
        pathogen_id="norwalk_gi", alpha=None, beta=1.0, **kwargs,
    )


def test_spec_without_args_is_byte_identical():
    plain = _spec()
    with_nones = _spec(
        high_touch_area_scale=None,
        high_touch_area_scale_by_zone_class=None,
    )
    assert plain == with_nones
    assert "transmission" not in plain["config_overrides"]


def test_scalar_arm_writes_exactly_one_transmission_key():
    spec = _spec(high_touch_area_scale=0.25)
    assert spec["config_overrides"]["transmission"] == {
        "high_touch_area_scale": 0.25,
    }
    rest = _spec()
    assert spec["pathogen_overrides"] == rest["pathogen_overrides"]
    assert spec["config_overrides"]["ship_graph"] == (
        rest["config_overrides"]["ship_graph"]
    )


def test_class_map_arg_round_trips_through_the_json_parser():
    args = pdc.parse_args(
        [
            "--out", "x",
            "--high-touch-area-scale-by-zone-class",
            '{"cabin": 0.11, "dining": 3.5}',
        ],
    )
    assert args.high_touch_area_scale_by_zone_class == {
        "cabin": 0.11, "dining": 3.5,
    }
    spec = _spec(
        high_touch_area_scale_by_zone_class=(
            args.high_touch_area_scale_by_zone_class
        ),
    )
    assert spec["config_overrides"]["transmission"] == {
        "high_touch_area_scale_by_zone_class": {"cabin": 0.11, "dining": 3.5},
    }


def test_class_map_arg_rejects_non_object_json():
    with pytest.raises(SystemExit):
        pdc.parse_args(
            [
                "--out", "x",
                "--high-touch-area-scale-by-zone-class", "[1, 2]",
            ],
        )


def test_arm_tag_stamps_the_filename_pattern():
    # mirror main()'s filename precedence: tag wins over alpha and base.
    tag = "htaCabin"
    filename = f"per_host_dose_challenge_{tag}_seed9000.json.gz"
    assert filename == "per_host_dose_challenge_htaCabin_seed9000.json.gz"
    args = pdc.parse_args(
        ["--out", "x", "--arm-tag", tag, "--high-touch-area-scale", "0.25"],
    )
    assert args.arm_tag == tag
    assert args.high_touch_area_scale == pytest.approx(0.25, rel=0.0, abs=0.0)


def test_arm_tag_rejects_non_identifier_characters():
    with pytest.raises(SystemExit):
        pdc.parse_args(["--out", "x", "--arm-tag", "bad tag!"])
