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

Nothing here is fitted and nothing here is a target.  ``a9_targets`` in
``midrs_incidence_targets.py`` continues to score against the Jenkins
denominator it has always used; the Freeland-window rates below are a
diagnostic that says what the same numerator would give under the other
published count.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, NamedTuple

from simulation_utils.paths import validated_open

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
    "era, so the post arm has no posting-rate denominator"
)

DENOMINATOR_YEARS = tuple(sorted(FREELAND_VOYAGES_ANALYSED))


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
    its outbreak counts by either of its voyage counts reproduces that printed
    rate for one year out of seven (2012, over the analysed subset), and in
    four of the seven it falls outside the bracket the two units span at all.
    So the pairing between the published rate and the published counts is not
    recoverable, which is the reason the denominator enters as an interval
    rather than as whichever column happens to be quoted.
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
