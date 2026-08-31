"""MIDRS source-record constants and target API contracts."""

from __future__ import annotations

import pytest

from telemetry_buffer.observation_model import midrs_incidence_targets as targets


def test_midrs_voyage_count_tables_cover_the_source_total() -> None:
    assert sum(targets.MIDRS_VOYAGE_COUNTS_BY_GRT_BAND.values()) == 37_258
    assert sum(targets.MIDRS_VOYAGE_COUNTS_BY_VOYAGE_LENGTH.values()) == 37_258


def test_midrs_rates_and_outbreak_counts_match_recorded_values() -> None:
    assert targets.MIDRS_PASSENGER_RATES_BY_GRT_BAND["60,001-120,000"] == 23.0
    assert targets.MIDRS_CREW_RATES_BY_GRT_BAND[">=140,001"] == 16.0
    assert targets.MIDRS_PASSENGER_RATES_BY_VOYAGE_LENGTH["15-21"] == 40.0
    assert targets.MIDRS_CREW_RATES_BY_VOYAGE_LENGTH["3-5"] == 17.5
    assert sum(targets.MIDRS_PASSENGER_OUTBREAKS_BY_VOYAGE_LENGTH.values()) == 156
    assert sum(targets.MIDRS_CREW_OUTBREAKS_BY_VOYAGE_LENGTH.values()) == 16


def test_a8_returns_endpoint_to_pooled_intervals() -> None:
    result = targets.a8_targets("classic_cruise_1900", "pre")

    assert result is not None
    assert result["passenger"] == (16.9, 23.0)
    assert result["crew"] == (5.2, 19.8)
    assert result["grt_band"] == "60,001-120,000"


def test_a8_post_and_invalid_inputs_are_explicit() -> None:
    assert targets.a8_targets("classic_cruise_1900", "post") is None
    with pytest.raises(ValueError, match="unknown hull"):
        targets.a8_targets("unknown", "pre")
    with pytest.raises(ValueError, match="unknown MIDRS era"):
        targets.a8_targets("classic_cruise_1900", "future")


def test_a9_exposes_competing_fleet_definitions_and_unmapped_band() -> None:
    result = targets.a9_targets("pre")

    assert result is not None
    assert result["fleet"]["interval"] == pytest.approx((4.19, 5.58), abs=0.01)
    assert result["per_hull"]["classic_cruise_1900"]["target"] is None
    assert result["per_hull"]["classic_cruise_1900"]["reason"]
    assert targets.UNMAPPED_GRT_BANDS == ("30,001-60,000",)
    assert result["passenger_by_voyage_length"]["3-5"] == pytest.approx(0.51, abs=0.01)
    assert targets.a9_targets("post") is None


def test_a9_rejects_invalid_era() -> None:
    with pytest.raises(ValueError, match="unknown MIDRS era"):
        targets.a9_targets("future")
