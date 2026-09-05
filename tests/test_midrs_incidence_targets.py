"""MIDRS source-record constants and target API contracts."""

from __future__ import annotations

import pytest

from telemetry_buffer.observation_model import midrs_incidence_targets as targets


def test_midrs_voyage_count_tables_cover_the_source_total() -> None:
    assert sum(targets.MIDRS_VOYAGE_COUNTS_BY_GRT_BAND.values()) == 37_258
    assert sum(targets.MIDRS_VOYAGE_COUNTS_BY_VOYAGE_LENGTH.values()) == 37_258


def test_midrs_rates_and_outbreak_counts_match_recorded_values() -> None:
    assert targets.MIDRS_PASSENGER_RATES_BY_GRT_BAND[
        "60,001-120,000"
    ] == pytest.approx(23.0)
    assert targets.MIDRS_CREW_RATES_BY_GRT_BAND[">=140,001"] == pytest.approx(
        16.0
    )
    assert targets.MIDRS_PASSENGER_RATES_BY_VOYAGE_LENGTH["15-21"] == (
        pytest.approx(40.0)
    )
    assert targets.MIDRS_CREW_RATES_BY_VOYAGE_LENGTH["3-5"] == pytest.approx(
        17.5
    )
    assert sum(targets.MIDRS_PASSENGER_OUTBREAKS_BY_VOYAGE_LENGTH.values()) == 156
    assert sum(targets.MIDRS_CREW_OUTBREAKS_BY_VOYAGE_LENGTH.values()) == 16


def test_a8_returns_named_endpoint_plausibility_bands() -> None:
    result = targets.a8_targets("classic_cruise_1900", "pre")

    assert result is not None
    assert result["passenger"] == {
        "end_of_period": 16.9,
        "pooled_band": (23.0, 23.7),
    }
    assert result["crew"] == {
        "end_of_period": 5.2,
        "pooled_band": (16.7, 19.8),
    }
    assert result["grt_bands"] == ("30,001-60,000", "60,001-120,000")


def test_grt_bands_come_from_passenger_complements_not_totals() -> None:
    complements = {
        hull: capacity
        for hull, capacity in targets.HULL_PASSENGER_CAPACITY.items()
    }

    assert targets.HULL_TO_GRT_BANDS == {
        "expedition_cruise_450": ("<=30,000",),
        "classic_cruise_1900": ("30,001-60,000", "60,001-120,000"),
        "spirit_cruise_3000": ("60,001-120,000",),
        "mega_cruise_5000": (">=140,001",),
    }
    # The platform ids and the passenger-plus-crew totals both exceed the
    # complements for three hulls, and both put the classic and spirit hulls in
    # a higher band than their complements admit.
    assert complements["classic_cruise_1900"] == 1_350
    assert targets.grt_bands_for_complement(1_910) == ("60,001-120,000",)
    assert complements["spirit_cruise_3000"] == 2_100
    assert targets.grt_bands_for_complement(3_000) == (
        "120,001-140,000",
        ">=140,001",
    )


def test_larger_complements_never_map_to_smaller_bands() -> None:
    order = list(targets.GRT_BAND_LIMITS)
    highest = [
        order.index(targets.grt_bands_for_complement(pax)[-1])
        for pax in range(200, 6_000, 200)
    ]

    assert highest == sorted(highest)
    assert targets.grt_bands_for_complement(1) == ("<=30,000",)
    assert targets.grt_bands_for_complement(100_000) == (">=140,001",)


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
    assert targets.UNMAPPED_GRT_BANDS == ("120,001-140,000",)
    assert result["passenger_by_voyage_length"]["3-5"] == pytest.approx(0.51, abs=0.01)
    assert targets.a9_targets("post") is None


def test_a9_rejects_invalid_era() -> None:
    with pytest.raises(ValueError, match="unknown MIDRS era"):
        targets.a9_targets("future")
