"""Observed MIDRS incidence targets from MMWR 2021;70(6):182-190.

The source record is transcribed in
``telemetry_buffer/observation_model/midrs_observed_targets.md``.  Table 2
reports rates per 100,000 travel-days pooled across 2006-2019; its passenger
calendar endpoints fell from 32.5 in 2006 to 16.9 in 2019, while crew rates
fell from 13.5 to 5.2.  A8 therefore returns an interval from the endpoint
rate to the pooled band rate rather than treating the pooled rate as a point.
"""

from __future__ import annotations

from typing import Any

MIDRS_TOTAL_VOYAGES = 37_258
MIDRS_PASSENGER_OUTBREAKS_INVESTIGATED = 156
MIDRS_PASSENGER_OUTBREAKS_POSTED = 208

MIDRS_VOYAGE_COUNTS_BY_GRT_BAND: dict[str, int] = {
    "<=30,000": 1_500,
    "30,001-60,000": 4_510,
    "60,001-120,000": 30_039,
    "120,001-140,000": 917,
    ">=140,001": 292,
}

MIDRS_VOYAGE_COUNTS_BY_VOYAGE_LENGTH: dict[str, int] = {
    "3-5": 13_772,
    "6-7": 6_031,
    "8-10": 12_239,
    "11-14": 3_111,
    "15-21": 2_105,
}

MIDRS_PASSENGER_RATES_BY_GRT_BAND: dict[str, float] = {
    "<=30,000": 10.9,
    "30,001-60,000": 23.7,
    "60,001-120,000": 23.0,
    "120,001-140,000": 26.7,
    ">=140,001": 29.2,
}

MIDRS_CREW_RATES_BY_GRT_BAND: dict[str, float] = {
    "<=30,000": 6.4,
    "30,001-60,000": 16.7,
    "60,001-120,000": 19.8,
    "120,001-140,000": 14.7,
    ">=140,001": 16.0,
}

MIDRS_TOTAL_RATES_BY_GRT_BAND: dict[str, float] = {
    "<=30,000": 9.06,
    "30,001-60,000": 21.4,
    "60,001-120,000": 22.1,
    "120,001-140,000": 22.9,
    ">=140,001": 24.4,
}

MIDRS_PASSENGER_RATES_BY_VOYAGE_LENGTH: dict[str, float] = {
    "3-5": 13.3,
    "6-7": 17.8,
    "8-10": 23.2,
    "11-14": 35.0,
    "15-21": 40.0,
}

MIDRS_CREW_RATES_BY_VOYAGE_LENGTH: dict[str, float] = {
    "3-5": 17.5,
    "6-7": 22.1,
    "8-10": 19.0,
    "11-14": 17.4,
    "15-21": 20.9,
}

MIDRS_TOTAL_RATES_BY_VOYAGE_LENGTH: dict[str, float] = {
    "3-5": 14.5,
    "6-7": 19.0,
    "8-10": 22.0,
    "11-14": 29.5,
    "15-21": 33.8,
}

MIDRS_PASSENGER_OUTBREAKS_BY_VOYAGE_LENGTH: dict[str, int] = {
    "3-5": 7,
    "6-7": 2,
    "8-10": 30,
    "11-14": 57,
    "15-21": 60,
}

MIDRS_CREW_OUTBREAKS_BY_VOYAGE_LENGTH: dict[str, int] = {
    "3-5": 6,
    "6-7": 4,
    "8-10": 3,
    "11-14": 2,
    "15-21": 1,
}

MIDRS_PASSENGER_CALENDAR_ENDPOINTS = (32.5, 16.9)
MIDRS_CREW_CALENDAR_ENDPOINTS = (13.5, 5.2)

HULL_TO_GRT_BAND: dict[str, str] = {
    # Silver Wind, 16,800 GT, 294 passengers.
    "expedition_cruise_450": "<=30,000",
    # Coral Princess, 91,627 GT, 1,970 passengers.
    "classic_cruise_1900": "60,001-120,000",
    # Voyager class, approximately 138,000 GT, 3,114 passengers.
    "spirit_cruise_3000": "120,001-140,000",
    # Oasis class, approximately 225,282 GT, 5,400 passengers.
    "mega_cruise_5000": ">=140,001",
}

UNMAPPED_GRT_BANDS = ("30,001-60,000",)
_VALID_ERAS = ("pre", "post")
_NO_HULL_A9_REASON = "per-hull outbreak numerator unpublished"

_PASSENGER_ENDPOINT_BY_BAND = {
    "<=30,000": MIDRS_PASSENGER_CALENDAR_ENDPOINTS[1],
    "60,001-120,000": MIDRS_PASSENGER_CALENDAR_ENDPOINTS[1],
    "120,001-140,000": MIDRS_PASSENGER_CALENDAR_ENDPOINTS[1],
    ">=140,001": MIDRS_PASSENGER_CALENDAR_ENDPOINTS[1],
}
_CREW_ENDPOINT_BY_BAND = {
    "<=30,000": MIDRS_CREW_CALENDAR_ENDPOINTS[1],
    "60,001-120,000": MIDRS_CREW_CALENDAR_ENDPOINTS[1],
    "120,001-140,000": MIDRS_CREW_CALENDAR_ENDPOINTS[1],
    ">=140,001": MIDRS_CREW_CALENDAR_ENDPOINTS[1],
}


def a8_targets(hull: str, era: str) -> dict[str, Any] | None:
    """Return pre-arm A8 intervals for a hull's MIDRS tonnage band.

    Each interval is ``(end_of_period_rate, pooled_band_rate)``.  The pooled
    Table 2 band rate averages 2006-2019, during which the passenger rate
    halved from 32.5 to 16.9.  Scoring a late-2010s configuration only against
    the pooled figure asks for about 1.4 times the last observed incidence.
    Both endpoints are reported; neither is used alone.  No post-2019 MIDRS
    analysis exists, so the post arm has no A8 target.
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
        "passenger": (
            _PASSENGER_ENDPOINT_BY_BAND[band],
            MIDRS_PASSENGER_RATES_BY_GRT_BAND[band],
        ),
        "crew": (
            _CREW_ENDPOINT_BY_BAND[band],
            MIDRS_CREW_RATES_BY_GRT_BAND[band],
        ),
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
