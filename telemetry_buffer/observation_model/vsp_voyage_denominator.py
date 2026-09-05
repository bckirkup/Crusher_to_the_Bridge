"""The external voyage denominator for VSP posting rates (task #13).

The posting series in ``vsp_outbreak_series.csv`` is a numerator only: it
counts voyages CDC *posted*, and says nothing about how many voyages sailed.
Any rate built on it needs a count of qualifying voyages from outside the
repository, and this module is the only place that count is allowed to enter.

Two published counts exist, they are in different units, and neither covers
the series:

* **Freeland 2016** (MMWR 65(1), DOI 10.15585/mmwr.mm6501a1) publishes voyages
  by year for 2008-2014, twice: voyages required to submit a VSP report, and
  the subset of 3-21 days carrying >100 passengers that the paper analysed.
* **Jenkins 2021** (MMWR SS 70(6), DOI 10.15585/mmwr.ss7006a1) publishes one
  total of unduplicated voyage reports for 2006-2019, not resolved by year.

The two do not reconcile as the same unit: Freeland's seven years hold 29,107
of Jenkins's 37,258, which would leave ~8,151 voyages for the remaining seven
years of a period whose traffic grew.  Which of "voyage", "voyage report" and
"arrival" each number counts is not stated in either paper, so this module
carries both and refuses to pick one.

How far apart the two Freeland columns are is small and measured, not open:
the analysed subset is 5.4-12.7% below the required-report count year by year,
and ``published_rate_residuals`` shows the paper's own printed rates sit on the
required-report column to within 4.8% on average (worst 8.5%) in six of the
seven years.  Only 2010 disagrees materially: its printed 3.8 per 1,000 needs
~5,526 voyages, more than either column publishes, so one of that year's three
cells is misprinted.  The denominator therefore enters as a ~10%-wide interval
with one flagged year, which is a bounded uncertainty rather than an unknown.

Where the sources disagree with each other, the disagreement is carried as an
interval rather than left as a blank: ``annual_denominator_interval`` brackets
both published columns and the count each printed rate implies,
``stationarity_denominator_interval`` states what the years outside Freeland's
table can be bounded to and on what assumption, ``posted_to_investigated``
bounds the posting step, and ``jenkins_unit_ratio_interval`` says how much
smaller an "unduplicated voyage report" must be than a required-report voyage
for the two papers to be describing the same fleet.  Post-2020 stays empty:
nothing has been published that could bound it, and an interval invented for it
would be a number with no source.

CDC's own outbreak pages do not close the post-2020 gap, and it is worth being
precise about why, because they visibly *do* cover those years.  What they cover
is the numerator: they list the voyages CDC posted (4 in 2020, 1 in 2021, 4 in
2022, then 14, 18, 23 and 9 so far), and they have never published a count of
voyages sailed in any era --- both counts this module carries came from MMWR,
which stops at 2019.  The only fleet quantity derivable from the pages is the
number of distinct ships they name, 1-19 per year against hundreds under
jurisdiction, which bounds the fleet from below by a factor that makes it
useless as a denominator.  So the post arm compares postings to postings and
never a rate to a rate.

Nothing here is fitted and nothing here is a target.  ``a9_targets`` in
``midrs_incidence_targets.py`` continues to score against the Jenkins
denominator it has always used; the Freeland-window rates below are a
diagnostic that says what the same numerator would give under the other
published count.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any, NamedTuple

from simulation_utils.paths import validated_open
from telemetry_buffer.observation_model.midrs_incidence_targets import (
    MIDRS_PASSENGER_OUTBREAKS_INVESTIGATED,
)

SERIES_PATH = Path(__file__).resolve().parent / "vsp_outbreak_series.csv"

# Freeland A, Vaughan GH Jr, Banerjee E, et al. Acute gastroenteritis on cruise
# ships - United States, 2008-2014. MMWR 2016;65(1):1-5.  Grade A (direct count
# of the population the posting series is drawn from).  Origin: R (Results
# body: "a total of 32,084 voyages required submission of a VSP report, ranging
# annually from 4,404 in 2012 to 4,808 in 2014 (Table); among these, 29,107
# (90.7%) were voyages of 3-21 days and included >100 passengers").
FREELAND_VOYAGES_REQUIRING_REPORT: dict[int, int] = {
    2008: 4_694,
    2009: 4_506,
    2010: 4_627,
    2011: 4_621,
    2012: 4_404,
    2013: 4_424,
    2014: 4_808,
}

# The same table's analysed subset: 3-21 days and >100 passengers, which are
# also the eligibility filters the scorer applies to model voyages.
FREELAND_VOYAGES_ANALYSED: dict[int, int] = {
    2008: 4_098,
    2009: 3_964,
    2010: 4_155,
    2011: 4_189,
    2012: 4_168,
    2013: 4_146,
    2014: 4_387,
}

# Passenger AGE outbreaks CDC *investigated*, by year, from the same table.
# Not our numerator: the series counts postings, a wider definition.
FREELAND_PASSENGER_OUTBREAKS_INVESTIGATED: dict[int, int] = {
    2008: 20,
    2009: 17,
    2010: 21,
    2011: 15,
    2012: 27,
    2013: 17,
    2014: 15,
}

# The rates the paper prints per 1,000 voyages, kept so that the arithmetic
# below can be checked against them rather than assumed to agree.
FREELAND_PUBLISHED_RATE_PER_1000: dict[int, float] = {
    2008: 4.4,
    2009: 4.0,
    2010: 3.8,
    2011: 3.3,
    2012: 6.5,
    2013: 4.2,
    2014: 3.0,
}

# Jenkins KA, Vaughan GH Jr, Rodriguez LO, Freeland A.  MMWR Surveill Summ
# 2021;70(6).  Grade A, Origin: T1 (Table 1, "No. voyage reports
# (unduplicated) 37,258").  One total for 2006-2019; no annual resolution.
JENKINS_VOYAGE_REPORTS_2006_2019 = 37_258
JENKINS_WINDOW = (2006, 2019)

# The one year whose three published cells (rate, outbreaks, both voyage
# counts) cannot be made consistent with each other: 3.8 per 1,000 on 21
# outbreaks implies ~5,526 voyages, above the 4,627 required-report count.
FREELAND_INCONSISTENT_YEARS = (2010,)

FREELAND_UNIT_REQUIRED = "voyages required to submit a VSP report"
FREELAND_UNIT_ANALYSED = "voyages of 3-21 d carrying >100 passengers"
JENKINS_UNIT = "unduplicated voyage reports"

# Why the years outside Freeland's table have no denominator at all.  Each is
# a null result, not an unfinished search: the evidence review is recorded in
# docs/literature/consensus_tranche_18_voyage_denominator.md.
NO_ANNUAL_DENOMINATOR = (
    "no published annual count of VSP-jurisdiction voyages for this year; "
    "MARAD/BTS departures and CLIA/BREA embarkations count a different "
    "population and are excluded (tranche 18 SS4-5)"
)
NO_POST_COVID_DENOMINATOR = (
    "no VSP voyage count of any kind has been published for the post-2020 "
    "era, so the post arm has no posting-rate denominator; CDC's outbreak "
    "pages supply postings only (a numerator), and the 1-19 distinct ships "
    "they name per year are a floor on the fleet, not a count of its voyages"
)

DENOMINATOR_YEARS = tuple(sorted(FREELAND_VOYAGES_ANALYSED))

# The public posting criterion, quoted from CDC's own outbreak-update pages
# (https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/index.html,
# retrieved 2026-09-05).  Grade A for what CDC says it does *now*; Origin: Tr
# (transcribed from a program web page, not a journal).  It is not evidence
# that the same criterion held in earlier years, which is one of the questions
# docs/proposals/vsp_midrs_extract_request.md asks.
POSTING_CRITERION = (
    "ship under VSP jurisdiction (voyage includes both US and foreign ports); "
    "3% or more of passengers OR crew reporting GI illness to the ship's "
    "medical staff; CDC may also post other outbreaks of public health "
    "significance"
)

# Years Jenkins's window covers that Freeland's table does not.  These are the
# years the pooled total has to accommodate and no annual source describes.
JENKINS_ONLY_YEARS = (2006, 2007, 2015, 2016, 2017, 2018, 2019)

# The structural ceiling on the posting step: a voyage cannot be posted without
# having been investigated, so posted/investigated <= 1 whatever the counts say.
# It is combinatorial, not epidemiological, and holds for every year.
POSTED_TO_INVESTIGATED_CEILING = 1.0

STATIONARITY_ASSUMPTION = (
    "annual VSP-jurisdiction voyage counts outside 2008-2014 lie within the "
    "envelope Freeland's seven years span; declared, not sourced, because no "
    "annual count is published for those years and the excluded MARAD/CLIA "
    "series count a different population (tranche 18 SS4-5)"
)


class AnnualDenominator(NamedTuple):
    """The two published voyage counts for one year, kept side by side."""

    year: int
    voyages_requiring_report: int
    voyages_analysed: int
    source: str = "Freeland 2016 (MMWR 65(1)), Table"


def annual_denominator(year: int) -> AnnualDenominator | None:
    """Published voyage counts for ``year``, or ``None`` where none exist."""
    if year not in FREELAND_VOYAGES_ANALYSED:
        return None
    return AnnualDenominator(
        year=year,
        voyages_requiring_report=FREELAND_VOYAGES_REQUIRING_REPORT[year],
        voyages_analysed=FREELAND_VOYAGES_ANALYSED[year],
    )


def missing_denominator_reason(year: int) -> str | None:
    """Why ``year`` has no denominator, or ``None`` when it has one."""
    if year in FREELAND_VOYAGES_ANALYSED:
        return None
    if year > JENKINS_WINDOW[1]:
        return NO_POST_COVID_DENOMINATOR
    return NO_ANNUAL_DENOMINATOR


def postings_by_year(path: Path = SERIES_PATH) -> dict[int, int]:
    """Count posted outbreaks per year in the VSP posting series."""
    counts: dict[int, int] = {}
    with validated_open(
        str(path),
        "r",
        allowed_roots=(str(path.parent),),
        encoding="utf-8",
        newline="",
    ) as handle:
        for row in csv.DictReader(handle):
            year = int(row["year"])
            counts[year] = counts.get(year, 0) + 1
    return counts


def posting_rate_interval(
    year: int,
    postings: int,
) -> tuple[float, float] | None:
    """Posted outbreaks per 1,000 voyages, as an interval over the two units.

    The interval spans the two published voyage counts because CDC does not
    say which unit its rates use, and choosing one would assert a resolution
    the sources do not support.  It is a *posting* rate: the numerator counts
    voyages CDC posted publicly, not the outbreaks it investigated, and the
    two differ by about a third (``midrs_observed_targets.md`` conflict 3).
    """
    denominator = annual_denominator(year)
    if denominator is None:
        return None
    high = 1_000 * postings / denominator.voyages_analysed
    low = 1_000 * postings / denominator.voyages_requiring_report
    return (low, high)


def published_rate_check() -> dict[int, dict[str, float]]:
    """Recompute Freeland's own published rates from its own table.

    The paper prints an investigated-outbreak rate per 1,000 voyages; dividing
    its outbreak counts by either voyage count reproduces the printed rate to
    its single decimal in only one year (2012, over the analysed subset), but
    the misses are small and one-sided rather than arbitrary --- see
    ``published_rate_residuals`` for how small.  The exact pairing between the
    printed rate and the printed counts is not recoverable, which is why the
    denominator enters as an interval; the interval is narrow.
    """
    return {
        year: {
            "published": FREELAND_PUBLISHED_RATE_PER_1000[year],
            "over_required": (
                1_000
                * FREELAND_PASSENGER_OUTBREAKS_INVESTIGATED[year]
                / FREELAND_VOYAGES_REQUIRING_REPORT[year]
            ),
            "over_analysed": (
                1_000
                * FREELAND_PASSENGER_OUTBREAKS_INVESTIGATED[year]
                / FREELAND_VOYAGES_ANALYSED[year]
            ),
        }
        for year in DENOMINATOR_YEARS
    }


def published_rate_residuals() -> dict[int, dict[str, float]]:
    """How far each printed Freeland rate sits from each published column.

    This is the quantified version of the disagreement above.  Against the
    required-report column the printed rates are off by 0.21 per 1,000 on
    average (4.8%, worst 8.5%) once 2010 is set aside, which is the scale of
    one-decimal rounding plus a plausible mid-year revision, not a unit error;
    against the analysed subset the average is 0.27 (7.2%, worst 14.0%).  So
    the printed rates behave like the required-report column, the interval this
    module carries spans the residual, and 2010 is separately flagged.

    ``implied_denominator`` is the voyage count each printed rate would need at
    the printed outbreak count: it lands between the two columns in three
    years, within 4% of the nearer column in three more, and 19% above the
    larger column only in 2010.
    """
    return {
        year: {
            "implied_denominator": (
                1_000
                * FREELAND_PASSENGER_OUTBREAKS_INVESTIGATED[year]
                / FREELAND_PUBLISHED_RATE_PER_1000[year]
            ),
            **{
                f"residual_{column}": values[column] - values["published"]
                for column in ("over_required", "over_analysed")
            },
            **{
                f"relative_{column}": (
                    (values[column] - values["published"]) / values["published"]
                )
                for column in ("over_required", "over_analysed")
            },
        }
        for year, values in published_rate_check().items()
    }


def observed_posting_rates(path: Path = SERIES_PATH) -> dict[str, Any]:
    """Observed posting-rate diagnostic for every year of the posting series.

    Years with a denominator carry an interval; every other year carries the
    reason it has none.  This is a diagnostic and no anchor scores against it:
    it covers 7 of the series' 23 denominator-bearing years, in a unit CDC
    does not resolve, against a numerator CDC does not publish.
    """
    postings = postings_by_year(path)
    per_year: dict[int, dict[str, Any]] = {}
    for year in sorted(postings):
        interval = posting_rate_interval(year, postings[year])
        per_year[year] = {
            "postings": postings[year],
            "per_1000_voyages": interval,
            "no_denominator_reason": missing_denominator_reason(year),
        }
    covered = [year for year in per_year if per_year[year]["per_1000_voyages"]]
    pooled_postings = sum(postings[year] for year in covered)
    return {
        "per_year": per_year,
        "covered_years": tuple(covered),
        "pooled": {
            "postings": pooled_postings,
            "per_1000_voyages": (
                1_000
                * pooled_postings
                / sum(FREELAND_VOYAGES_REQUIRING_REPORT.values()),
                1_000
                * pooled_postings
                / sum(FREELAND_VOYAGES_ANALYSED.values()),
            ),
            "units": (FREELAND_UNIT_REQUIRED, FREELAND_UNIT_ANALYSED),
        },
    }


def implied_denominator(year: int) -> float:
    """Voyages the printed rate needs at the printed outbreak count."""
    return (
        1_000
        * FREELAND_PASSENGER_OUTBREAKS_INVESTIGATED[year]
        / FREELAND_PUBLISHED_RATE_PER_1000[year]
    )


def annual_denominator_interval(year: int) -> tuple[int, int] | None:
    """Bracket every voyage count Freeland's own table supports for ``year``.

    One rule, applied to all seven years without exception: the low end is the
    smaller of the analysed subset and the count the printed rate implies, the
    high end is the larger of the required-report column and that same implied
    count.  It therefore spans the two published units *and* the internal
    inconsistency, so 2010 widens to ~[4155, 5527] instead of being dropped and
    2014 to [4387, 5000], without anyone deciding which of the three
    disagreeing cells is the misprint.

    Grade **M**: the endpoints are published counts or arithmetic on published
    counts, but which one is the quantity is unresolved.  Origin: T1.
    """
    if year not in FREELAND_VOYAGES_ANALYSED:
        return None
    implied = implied_denominator(year)
    low = min(FREELAND_VOYAGES_ANALYSED[year], math.floor(implied))
    high = max(FREELAND_VOYAGES_REQUIRING_REPORT[year], math.ceil(implied))
    return (low, high)


def stationarity_denominator_interval() -> tuple[int, int]:
    """The declared bracket for years Freeland's table does not cover.

    The union of the seven annual brackets: any year whose count sits inside
    the envelope 2008-2014 spans falls in here.  This is a **Grade C declared
    assumption** (``STATIONARITY_ASSUMPTION``), not a measurement, and it is
    deliberately wide, [3964, 5527] -- 2009's analysed subset sets the floor
    and 2010's misprint the ceiling.  It applies to ``JENKINS_ONLY_YEARS``
    only; post-2020 gets nothing, because assuming a fleet that stopped sailing
    was unchanged is not conservatism, it is invention.
    """
    brackets = [annual_denominator_interval(year) for year in DENOMINATOR_YEARS]
    return (
        min(bracket[0] for bracket in brackets if bracket),
        max(bracket[1] for bracket in brackets if bracket),
    )


def jenkins_unit_ratio_interval() -> tuple[float, float]:
    """How small an "unduplicated voyage report" must be to fit Jenkins's total.

    Under ``STATIONARITY_ASSUMPTION`` the fourteen years of Jenkins's window
    hold 14 x the declared bracket of voyages, so Jenkins's single published
    37,258 corresponds to ~0.48-0.67 of a required-report voyage each.  A ratio
    that far below 1 is the quantitative form of the units not matching: it is
    reported so the mismatch has a size, and it is **not** a conversion factor
    to multiply anything by.
    """
    low_year, high_year = stationarity_denominator_interval()
    span = JENKINS_WINDOW[1] - JENKINS_WINDOW[0] + 1
    return (
        JENKINS_VOYAGE_REPORTS_2006_2019 / (span * high_year),
        JENKINS_VOYAGE_REPORTS_2006_2019 / (span * low_year),
    )


def posted_to_investigated(path: Path = SERIES_PATH) -> dict[str, Any]:
    """Bound the posting step: posted voyages per outbreak investigated.

    Only 2008-2014 carries both counts annually, and there the ratio runs
    0.53-0.93 with no trend, so the *interval* is that observed floor up to the
    structural ceiling of 1.0 -- the mean 0.70 is reported and deliberately not
    adopted, because a central value here would be the fitted conversion this
    row exists to refuse.

    The Jenkins window is excluded from the interval on a structural ground
    rather than a convenient one: 208 postings against 156 investigated
    outbreaks is a ratio above 1, which the ceiling forbids, so that pair
    cannot be two counts of the same event class.  ``jenkins_ratio`` is
    returned anyway so the contradiction stays visible.
    """
    postings = postings_by_year(path)
    by_year = {
        year: postings.get(year, 0)
        / FREELAND_PASSENGER_OUTBREAKS_INVESTIGATED[year]
        for year in DENOMINATOR_YEARS
    }
    ratios = list(by_year.values())
    return {
        "by_year": by_year,
        "interval": (min(ratios), POSTED_TO_INVESTIGATED_CEILING),
        "observed_mean": sum(ratios) / len(ratios),
        "jenkins_ratio": (
            sum(
                count
                for year, count in postings.items()
                if JENKINS_WINDOW[0] <= year <= JENKINS_WINDOW[1]
            )
            / MIDRS_PASSENGER_OUTBREAKS_INVESTIGATED
        ),
        "ceiling_basis": (
            "a posting presupposes an investigation, so the ratio cannot "
            "exceed 1 for any year"
        ),
    }
