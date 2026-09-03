"""Observed MIDRS incidence targets from MMWR 2021;70(6):182-190.

The source record is transcribed in
``telemetry_buffer/observation_model/midrs_observed_targets.md``.  Table 2
reports rates per 100,000 travel-days pooled across 2006-2019; its passenger
calendar endpoints fell from 32.5 in 2006 to 16.9 in 2019, while crew rates
fell from 13.5 to 5.2.  A8 therefore returns named endpoint values from
different stratifications as a plausibility band, rather than treating the
pooled rate as a point or a confidence interval.
"""

from __future__ import annotations

from typing import Any

MIDRS_TOTAL_VOYAGES = 37_258
MIDRS_PASSENGER_OUTBREAKS_INVESTIGATED = 156
MIDRS_PASSENGER_OUTBREAKS_POSTED = 208

# GRT population bands (MMWR Table 2 column labels).
GRT_BAND_LE_30000 = "<=30,000"
GRT_BAND_30001_60000 = "30,001-60,000"
GRT_BAND_60001_120000 = "60,001-120,000"
GRT_BAND_120001_140000 = "120,001-140,000"
GRT_BAND_GE_140001 = ">=140,001"

# Voyage-length population bands (MMWR Table 2 / Table 3 column labels).
VOYAGE_LENGTH_3_5 = "3-5"
VOYAGE_LENGTH_6_7 = "6-7"
VOYAGE_LENGTH_8_10 = "8-10"
VOYAGE_LENGTH_11_14 = "11-14"
VOYAGE_LENGTH_15_21 = "15-21"

MIDRS_VOYAGE_COUNTS_BY_GRT_BAND: dict[str, int] = {
    GRT_BAND_LE_30000: 1_500,
    GRT_BAND_30001_60000: 4_510,
    GRT_BAND_60001_120000: 30_039,
    GRT_BAND_120001_140000: 917,
    GRT_BAND_GE_140001: 292,
}

MIDRS_VOYAGE_COUNTS_BY_VOYAGE_LENGTH: dict[str, int] = {
    VOYAGE_LENGTH_3_5: 13_772,
    VOYAGE_LENGTH_6_7: 6_031,
    VOYAGE_LENGTH_8_10: 12_239,
    VOYAGE_LENGTH_11_14: 3_111,
    VOYAGE_LENGTH_15_21: 2_105,
}

MIDRS_PASSENGER_RATES_BY_GRT_BAND: dict[str, float] = {
    GRT_BAND_LE_30000: 10.9,
    GRT_BAND_30001_60000: 23.7,
    GRT_BAND_60001_120000: 23.0,
    GRT_BAND_120001_140000: 26.7,
    GRT_BAND_GE_140001: 29.2,
}

MIDRS_CREW_RATES_BY_GRT_BAND: dict[str, float] = {
    GRT_BAND_LE_30000: 6.4,
    GRT_BAND_30001_60000: 16.7,
    GRT_BAND_60001_120000: 19.8,
    GRT_BAND_120001_140000: 14.7,
    GRT_BAND_GE_140001: 16.0,
}

MIDRS_TOTAL_RATES_BY_GRT_BAND: dict[str, float] = {
    GRT_BAND_LE_30000: 9.06,
    GRT_BAND_30001_60000: 21.4,
    GRT_BAND_60001_120000: 22.1,
    GRT_BAND_120001_140000: 22.9,
    GRT_BAND_GE_140001: 24.4,
}

MIDRS_PASSENGER_RATES_BY_VOYAGE_LENGTH: dict[str, float] = {
    VOYAGE_LENGTH_3_5: 13.3,
    VOYAGE_LENGTH_6_7: 17.8,
    VOYAGE_LENGTH_8_10: 23.2,
    VOYAGE_LENGTH_11_14: 35.0,
    VOYAGE_LENGTH_15_21: 40.0,
}

MIDRS_CREW_RATES_BY_VOYAGE_LENGTH: dict[str, float] = {
    VOYAGE_LENGTH_3_5: 17.5,
    VOYAGE_LENGTH_6_7: 22.1,
    VOYAGE_LENGTH_8_10: 19.0,
    VOYAGE_LENGTH_11_14: 17.4,
    VOYAGE_LENGTH_15_21: 20.9,
}

MIDRS_TOTAL_RATES_BY_VOYAGE_LENGTH: dict[str, float] = {
    VOYAGE_LENGTH_3_5: 14.5,
    VOYAGE_LENGTH_6_7: 19.0,
    VOYAGE_LENGTH_8_10: 22.0,
    VOYAGE_LENGTH_11_14: 29.5,
    VOYAGE_LENGTH_15_21: 33.8,
}

MIDRS_PASSENGER_OUTBREAKS_BY_VOYAGE_LENGTH: dict[str, int] = {
    VOYAGE_LENGTH_3_5: 7,
    VOYAGE_LENGTH_6_7: 2,
    VOYAGE_LENGTH_8_10: 30,
    VOYAGE_LENGTH_11_14: 57,
    VOYAGE_LENGTH_15_21: 60,
}

MIDRS_CREW_OUTBREAKS_BY_VOYAGE_LENGTH: dict[str, int] = {
    VOYAGE_LENGTH_3_5: 6,
    VOYAGE_LENGTH_6_7: 4,
    VOYAGE_LENGTH_8_10: 3,
    VOYAGE_LENGTH_11_14: 2,
    VOYAGE_LENGTH_15_21: 1,
}

MIDRS_PASSENGER_CALENDAR_ENDPOINTS = (32.5, 16.9)
MIDRS_CREW_CALENDAR_ENDPOINTS = (13.5, 5.2)

HULL_TO_GRT_BAND: dict[str, str] = {
    # Silver Wind, 16,800 GT, 294 passengers.
    "expedition_cruise_450": GRT_BAND_LE_30000,
    # Coral Princess, 91,627 GT, 1,970 passengers.
    "classic_cruise_1900": GRT_BAND_60001_120000,
    # Voyager class, approximately 138,000 GT, 3,114 passengers.
    "spirit_cruise_3000": GRT_BAND_120001_140000,
    # Oasis class, approximately 225,282 GT, 5,400 passengers.
    "mega_cruise_5000": GRT_BAND_GE_140001,
}

UNMAPPED_GRT_BANDS = (GRT_BAND_30001_60000,)
_VALID_ERAS = ("pre", "post")
_NO_HULL_A9_REASON = "per-hull outbreak numerator unpublished"

_PASSENGER_ENDPOINT_BY_BAND = {
    GRT_BAND_LE_30000: MIDRS_PASSENGER_CALENDAR_ENDPOINTS[1],
    GRT_BAND_60001_120000: MIDRS_PASSENGER_CALENDAR_ENDPOINTS[1],
    GRT_BAND_120001_140000: MIDRS_PASSENGER_CALENDAR_ENDPOINTS[1],
    GRT_BAND_GE_140001: MIDRS_PASSENGER_CALENDAR_ENDPOINTS[1],
}
_CREW_ENDPOINT_BY_BAND = {
    GRT_BAND_LE_30000: MIDRS_CREW_CALENDAR_ENDPOINTS[1],
    GRT_BAND_60001_120000: MIDRS_CREW_CALENDAR_ENDPOINTS[1],
    GRT_BAND_120001_140000: MIDRS_CREW_CALENDAR_ENDPOINTS[1],
    GRT_BAND_GE_140001: MIDRS_CREW_CALENDAR_ENDPOINTS[1],
}


def a8_targets(hull: str, era: str) -> dict[str, Any] | None:
    """Return pre-arm A8 plausibility bands for a hull's MIDRS tonnage band.

    Endpoints are returned by name as ``end_of_period`` and ``pooled_band``.
    They come from different stratifications: the first is the fleet-wide
    2019 calendar endpoint, while the second is the pooled Table 2 GRT-band
    rate.  They are therefore a plausibility band, not a confidence interval.
    For example, the expedition band is ``16.9`` fleet-wide endpoint versus
    ``10.9`` pooled <=30,000 GRT rate, so its returned pair is intentionally
    inverted.  The pooled rate averages 2006-2019, during which the passenger
    rate halved from 32.5 to 16.9.  No post-2019 MIDRS analysis exists, so the
    post arm has no A8 target.
    """
    if era not in _VALID_ERAS:
        raise ValueError(f"unknown MIDRS era: {era!r}")
    if hull not in HULL_TO_GRT_BAND:
        raise ValueError(f"unknown hull: {hull!r}")
    if era == "post":
        return None
    band = HULL_TO_GRT_BAND[hull]
    return {
        "grt_band": band,
        "passenger": {
            "end_of_period": _PASSENGER_ENDPOINT_BY_BAND[band],
            "pooled_band": MIDRS_PASSENGER_RATES_BY_GRT_BAND[band],
        },
        "crew": {
            "end_of_period": _CREW_ENDPOINT_BY_BAND[band],
            "pooled_band": MIDRS_CREW_RATES_BY_GRT_BAND[band],
        },
    }


def a9_targets(era: str) -> dict[str, Any] | None:
    """Return fleet and voyage-length A9 targets for the selected era.

    The fleet interval spans 156 MMWR-investigated outbreaks and 208 postings
    in the project's series, both divided by the same 37,258 voyage reports.
    Table 3 supplies no GRT-band outbreak numerator, so per-hull targets are
    explicitly unavailable rather than inferred.
    """
    if era not in _VALID_ERAS:
        raise ValueError(f"unknown MIDRS era: {era!r}")
    if era == "post":
        return None
    investigated = (
        1_000 * MIDRS_PASSENGER_OUTBREAKS_INVESTIGATED / MIDRS_TOTAL_VOYAGES
    )
    posted = 1_000 * MIDRS_PASSENGER_OUTBREAKS_POSTED / MIDRS_TOTAL_VOYAGES
    by_length = {
        length: 1_000 * count / MIDRS_VOYAGE_COUNTS_BY_VOYAGE_LENGTH[length]
        for length, count in MIDRS_PASSENGER_OUTBREAKS_BY_VOYAGE_LENGTH.items()
    }
    return {
        "fleet": {
            "investigated": investigated,
            "posted": posted,
            "interval": (investigated, posted),
            "definitions": {
                "investigated": "MMWR investigated passenger outbreaks",
                "posted": "project VSP posted series",
            },
        },
        "per_hull": {
            hull: {"target": None, "reason": _NO_HULL_A9_REASON}
            for hull in HULL_TO_GRT_BAND
        },
        "passenger_by_voyage_length": by_length,
        "per_length": by_length,
    }
