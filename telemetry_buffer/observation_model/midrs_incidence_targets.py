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

import math
from fractions import Fraction
from typing import Any, NamedTuple

from telemetry_buffer.observation_model.vsp_class_era_scoring import (
    HULL_PASSENGER_CAPACITY,
)

# The A9 denominator, declared rather than assumed (#13).  It is Jenkins's
# count of *unduplicated voyage reports* pooled over 2006-2019, not a count of
# voyages per year and not the unit Freeland 2016 publishes annually; see
# ``vsp_voyage_denominator.py`` for the two counts side by side and for what
# the same numerator gives under the other one.
MIDRS_TOTAL_VOYAGES = 37_258
MIDRS_DENOMINATOR_UNIT = "unduplicated voyage reports, pooled 2006-2019"
MIDRS_DENOMINATOR_WINDOW = (2006, 2019)
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

# Numeric limits of the MMWR Table 2 tonnage strata, in gross tons.  The
# labels partition the integers, so 120,000 is the extra-large band and
# 120,001 the mega one.
GRT_BAND_LIMITS: dict[str, tuple[int, float]] = {
    GRT_BAND_LE_30000: (0, 30_000),
    GRT_BAND_30001_60000: (30_001, 60_000),
    GRT_BAND_60001_120000: (60_001, 120_000),
    GRT_BAND_120001_140000: (120_001, 140_000),
    GRT_BAND_GE_140001: (140_001, math.inf),
}


class SpaceRatioAnchor(NamedTuple):
    """A real ship whose tonnage and lower-berth capacity are both published."""

    ship: str
    gross_tonnage: int
    passengers: int

    @property
    def gt_per_passenger(self) -> Fraction:
        """Space ratio, exact so that a band edge is not a rounding artefact."""
        return Fraction(self.gross_tonnage, self.passengers)


# MMWR strata are gross registered tonnage while the project's hulls are
# passenger complements, so the mapping needs a space ratio.  These four ships
# publish both figures.  None of them *is* a hull, and no hull is anchored to
# one of them: a single representative ship is what put the classic and spirit
# hulls one band too high, because the ship was chosen against the hull's
# passenger-plus-crew total.  Grade C, origin Tr (operator specifications).
SPACE_RATIO_ANCHORS: tuple[SpaceRatioAnchor, ...] = (
    SpaceRatioAnchor("Silver Wind", 16_800, 294),
    SpaceRatioAnchor("Coral Princess", 91_627, 1_970),
    SpaceRatioAnchor("Voyager class", 138_000, 3_114),
    SpaceRatioAnchor("Oasis class", 225_282, 5_400),
)

# 41.7-57.1 GT/pax across those four.  The ratio tightens with ship size, but
# that is an observation of four ships rather than a sourced relation, so the
# whole span applies at every complement; narrowing it per hull would be a
# choice, and the choice would decide band membership.
SPACE_RATIO_SPAN: tuple[Fraction, Fraction] = (
    min(anchor.gt_per_passenger for anchor in SPACE_RATIO_ANCHORS),
    max(anchor.gt_per_passenger for anchor in SPACE_RATIO_ANCHORS),
)


def grt_bands_for_complement(passengers: int) -> tuple[str, ...]:
    """Every tonnage band a hull of this passenger complement can occupy.

    The complement is converted to a tonnage *interval* by the published space
    ratios, and every band that interval meets is returned.  An interval
    straddling a band edge therefore returns two bands instead of the one its
    midpoint would land in: which side of the edge such a ship sits on is not
    determined by anything in the record, and a midpoint would decide it.
    """
    low = passengers * SPACE_RATIO_SPAN[0]
    high = passengers * SPACE_RATIO_SPAN[1]
    return tuple(
        band
        for band, (band_low, band_high) in GRT_BAND_LIMITS.items()
        if low <= band_high and high >= band_low
    )


# Derived from each hull's declared passenger complement (#29), never from its
# platform id and never from its passenger-plus-crew total.  The spirit hull is
# a soft edge: 2,100 passengers at Silver Wind's 400/7 GT/pax is exactly
# 120,000 GT, the top of the extra-large band, so one more ton of space ratio
# would add the mega band to it.
HULL_TO_GRT_BANDS: dict[str, tuple[str, ...]] = {
    hull: grt_bands_for_complement(passengers)
    for hull, passengers in HULL_PASSENGER_CAPACITY.items()
}

# Bands no hull can occupy.  Their observed rates are transcribed above and
# nothing is scored against them.
UNMAPPED_GRT_BANDS: tuple[str, ...] = tuple(
    band
    for band in GRT_BAND_LIMITS
    if all(band not in bands for bands in HULL_TO_GRT_BANDS.values())
)
_VALID_ERAS = ("pre", "post")
_NO_HULL_A9_REASON = "per-hull outbreak numerator unpublished"


def _pooled_span(
    bands: tuple[str, ...],
    rates: dict[str, float],
) -> tuple[float, float]:
    """Envelope of the pooled rates of every band a hull's interval meets."""
    values = [rates[band] for band in bands]
    return (min(values), max(values))


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

    ``pooled_band`` is a ``(low, high)`` envelope over every tonnage band the
    hull's complement admits, so a hull whose tonnage interval straddles a band
    edge is scored against both bands rather than against whichever one a
    representative ship happened to fall in.  A hull inside a single band gets
    that band's rate as both ends.  ``end_of_period`` is fleet-wide and does
    not depend on the band.
    """
    if era not in _VALID_ERAS:
        raise ValueError(f"unknown MIDRS era: {era!r}")
    if hull not in HULL_TO_GRT_BANDS:
        raise ValueError(f"unknown hull: {hull!r}")
    if era == "post":
        return None
    bands = HULL_TO_GRT_BANDS[hull]
    return {
        "grt_bands": bands,
        "passenger": {
            "end_of_period": MIDRS_PASSENGER_CALENDAR_ENDPOINTS[1],
            "pooled_band": _pooled_span(
                bands, MIDRS_PASSENGER_RATES_BY_GRT_BAND,
            ),
        },
        "crew": {
            "end_of_period": MIDRS_CREW_CALENDAR_ENDPOINTS[1],
            "pooled_band": _pooled_span(bands, MIDRS_CREW_RATES_BY_GRT_BAND),
        },
    }


def a9_targets(era: str) -> dict[str, Any] | None:
    """Return fleet and voyage-length A9 targets for the selected era.

    The fleet interval spans 156 MMWR-investigated outbreaks and 208 postings
    in the project's series, both divided by the same 37,258 voyage reports.
    Table 3 supplies no GRT-band outbreak numerator, so per-hull targets are
    explicitly unavailable rather than inferred.

    The denominator is declared in the returned ``fleet`` block: it is one
    pooled 2006-2019 count in Jenkins's own unit, so the target is a
    period average and no year of it is separable.  The post arm keeps no
    target because no voyage count has been published for that era at all.
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
            "denominator": {
                "voyages": MIDRS_TOTAL_VOYAGES,
                "unit": MIDRS_DENOMINATOR_UNIT,
                "window": MIDRS_DENOMINATOR_WINDOW,
                "source": "Jenkins 2021 (MMWR SS 70(6)), Table 1",
            },
        },
        "per_hull": {
            hull: {"target": None, "reason": _NO_HULL_A9_REASON}
            for hull in HULL_TO_GRT_BANDS
        },
        "passenger_by_voyage_length": by_length,
        "per_length": by_length,
    }
