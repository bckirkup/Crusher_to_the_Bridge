"""The external voyage denominator (#13): what it covers and what it refuses."""

from __future__ import annotations

import pytest

from telemetry_buffer.observation_model import vsp_voyage_denominator as vd


def test_freeland_table_totals_match_the_published_sums() -> None:
    assert sum(vd.FREELAND_VOYAGES_REQUIRING_REPORT.values()) == 32_084
    assert sum(vd.FREELAND_VOYAGES_ANALYSED.values()) == 29_107
    assert sum(vd.FREELAND_PASSENGER_OUTBREAKS_INVESTIGATED.values()) == 132
    for year, analysed in vd.FREELAND_VOYAGES_ANALYSED.items():
        assert analysed < vd.FREELAND_VOYAGES_REQUIRING_REPORT[year]


def test_the_two_cdc_voyage_units_do_not_reconcile() -> None:
    """Freeland's seven years leave too few voyages for Jenkins's other seven.

    2006-2019 traffic grew, so 29,107 of 37,258 in the middle seven years is
    not a partition of one unit.  The check exists so that a later reader
    cannot quietly treat the two counts as the same quantity.
    """
    remainder = vd.JENKINS_VOYAGE_REPORTS_2006_2019 - 29_107
    assert remainder == 8_151
    assert remainder < 29_107 / 2


def test_published_rates_are_not_reproducible_from_the_published_counts() -> None:
    """One year reproduces to one decimal; four sit outside the unit bracket.

    Three of those four (2012, 2013, 2014) miss the nearer edge by 0.02-0.12
    per 1,000, which is rounding-scale; the width is graded separately below.
    """
    check = vd.published_rate_check()
    reproduced = {
        year: unit
        for year, row in check.items()
        for unit in ("over_required", "over_analysed")
        if round(row[unit], 1) == row["published"]
    }
    outside = {
        year
        for year, row in check.items()
        if not row["over_required"] <= row["published"] <= row["over_analysed"]
    }

    assert reproduced == {2012: "over_analysed"}
    assert outside == {2010, 2012, 2013, 2014}


def test_the_published_rates_miss_the_required_column_by_single_percents() -> None:
    """The disagreement is bounded: <=8.5% everywhere except the flagged year."""
    residuals = vd.published_rate_residuals()
    graded = {
        year: abs(row["relative_over_required"])
        for year, row in residuals.items()
        if year not in vd.FREELAND_INCONSISTENT_YEARS
    }

    assert max(graded.values()) < 0.09
    assert sum(graded.values()) / len(graded) < 0.05
    # The residual changes sign across years, so it is scatter rather than a
    # systematic offset that some third voyage unit would remove.
    signs = {row["residual_over_required"] > 0 for row in residuals.values()}
    assert signs == {True, False}


def test_only_2010_needs_more_voyages_than_either_column_publishes() -> None:
    """2014 also overshoots, but by 4%; only 2010 overshoots beyond rounding."""
    overshoot = {
        year: row["implied_denominator"] / vd.FREELAND_VOYAGES_REQUIRING_REPORT[year]
        for year, row in vd.published_rate_residuals().items()
        if row["implied_denominator"] > vd.FREELAND_VOYAGES_REQUIRING_REPORT[year]
    }

    assert set(overshoot) == {2010, 2014}
    assert overshoot[2014] < 1.05
    assert {year for year, ratio in overshoot.items() if ratio > 1.1} == set(
        vd.FREELAND_INCONSISTENT_YEARS
    )
    assert vd.published_rate_residuals()[2010]["implied_denominator"] == pytest.approx(
        5_526, abs=1
    )


@pytest.mark.parametrize("year", [2008, 2011, 2014])
def test_covered_years_carry_an_interval_over_both_units(year: int) -> None:
    low, high = vd.posting_rate_interval(year, 10)
    denominator = vd.annual_denominator(year)

    assert denominator is not None
    assert low < high
    assert low == pytest.approx(10_000 / denominator.voyages_requiring_report)
    assert high == pytest.approx(10_000 / denominator.voyages_analysed)
    assert vd.missing_denominator_reason(year) is None


@pytest.mark.parametrize("year", [2004, 2007, 2015, 2019])
def test_uncovered_pre_covid_years_are_null_not_estimated(year: int) -> None:
    assert vd.annual_denominator(year) is None
    assert vd.posting_rate_interval(year, 10) is None
    assert vd.missing_denominator_reason(year) == vd.NO_ANNUAL_DENOMINATOR


@pytest.mark.parametrize("year", [2020, 2021, 2022])
def test_the_inspection_pause_years_stay_null(year: int) -> None:
    """The census measures the programme, not the fleet, while sailing stopped."""
    assert vd.post_covid_denominator_interval(year) is None
    assert vd.posting_rate_interval(year, 10) is None
    assert vd.missing_denominator_reason(year) == vd.NO_PAUSE_ERA_DENOMINATOR


def test_an_incomplete_year_has_no_census_and_so_no_bracket() -> None:
    assert vd.post_covid_denominator_interval(2026) is None
    assert vd.posting_rate_interval(2026, 10) is None
    assert vd.missing_denominator_reason(2026) == vd.NO_CENSUS_DENOMINATOR


def test_the_public_pages_supply_the_post_2020_numerator_only() -> None:
    """Postings come from the outbreak pages; the fleet comes from inspections."""
    postings = vd.postings_by_year()

    for year in (2020, 2021, 2022, 2023, 2024, 2025, 2026):
        assert postings.get(year, 0) > 0
        assert vd.annual_denominator_interval(year) is None


def test_the_inspection_census_tracks_the_fleet_it_is_scaling() -> None:
    census = vd.ships_inspected_by_year()

    for year in vd.CENSUS_YEARS_PRE_COVID + vd.CENSUS_YEARS_POST_COVID:
        assert census[year]["ships"] > 100
        assert census[year]["inspections"] >= census[year]["ships"]
    for year in (2020, 2022):
        assert census[year]["ships"] < 40
    assert 2021 not in census


def test_the_fleet_ratio_grows_with_the_post_pause_census() -> None:
    ratios = [vd.fleet_ratio(year) for year in vd.CENSUS_YEARS_POST_COVID]

    assert ratios[0] < ratios[1] < ratios[2]
    assert ratios == pytest.approx([1.171, 1.283, 1.541], abs=0.001)
    assert vd.fleet_ratio(2016) is None
    assert vd.fleet_ratio(2021) is None


def test_the_post_covid_bracket_is_the_envelope_scaled_by_the_census() -> None:
    """Wide by construction: a ship census times a declared voyages-per-ship."""
    envelope = vd.stationarity_denominator_interval()

    for year in vd.CENSUS_YEARS_POST_COVID:
        low, high = vd.post_covid_denominator_interval(year)
        ratio = vd.fleet_ratio(year)
        assert low == pytest.approx(envelope[0] * ratio, abs=1)
        assert high == pytest.approx(envelope[1] * ratio, abs=1)
        assert high > low > envelope[0]
    assert vd.post_covid_denominator_interval(2024) == (5_084, 7_090)
    assert "declared, not sourced" in vd.FLEET_RATIO_ASSUMPTION
    assert "floor" in vd.CENSUS_COVERAGE_CAVEAT


def test_the_post_covid_posting_rate_spans_the_grade_c_bracket() -> None:
    low, high = vd.posting_rate_interval(2024, 18)
    bracket = vd.post_covid_denominator_interval(2024)

    assert low == pytest.approx(18_000 / bracket[1])
    assert high == pytest.approx(18_000 / bracket[0])
    assert high / low > 1.3


def test_posting_rate_moves_with_the_numerator() -> None:
    rates = [vd.posting_rate_interval(2012, n)[1] for n in (5, 10, 20)]

    assert rates[0] < rates[1] < rates[2]
    assert rates[2] == pytest.approx(4 * rates[0])


def test_series_diagnostic_pools_only_the_measured_window() -> None:
    observed = vd.observed_posting_rates()

    assert observed["covered_years"] == (
        vd.DENOMINATOR_YEARS + vd.CENSUS_YEARS_POST_COVID
    )
    assert observed["pooled"]["postings"] == 91
    low, high = observed["pooled"]["per_1000_voyages"]
    assert (low, high) == pytest.approx((2.836, 3.126), abs=0.001)
    for year in (2004, 2020, 2026):
        assert observed["per_year"][year]["per_1000_voyages"] is None
        assert observed["per_year"][year]["no_denominator_reason"]


def test_the_posting_numerator_is_wider_than_the_investigated_one() -> None:
    """Our 91 postings and CDC's 132 investigations are different quantities.

    They point opposite ways to the 2006-2019 pair (208 posted against 156
    investigated), which is why neither ratio may be used to convert one
    definition into the other.
    """
    observed = vd.observed_posting_rates()
    posted = observed["pooled"]["postings"]
    investigated = sum(vd.FREELAND_PASSENGER_OUTBREAKS_INVESTIGATED.values())

    assert posted < investigated


def test_annual_bracket_spans_both_columns_and_the_implied_count() -> None:
    """One rule for all seven years; it widens only where the table disagrees."""
    for year in vd.DENOMINATOR_YEARS:
        low, high = vd.annual_denominator_interval(year)
        assert low <= vd.FREELAND_VOYAGES_ANALYSED[year]
        assert high >= vd.FREELAND_VOYAGES_REQUIRING_REPORT[year]
        assert low <= vd.implied_denominator(year) <= high

    assert vd.annual_denominator_interval(2008) == (4_098, 4_694)
    assert vd.annual_denominator_interval(2010) == (4_155, 5_527)
    assert vd.annual_denominator_interval(2014) == (4_387, 5_000)
    assert vd.annual_denominator_interval(2007) is None
    assert vd.annual_denominator_interval(2022) is None


def test_stationarity_bracket_is_the_union_and_is_declared_not_measured() -> None:
    low, high = vd.stationarity_denominator_interval()

    assert (low, high) == (3_964, 5_527)
    assert high / low > 1.3
    assert "declared, not sourced" in vd.STATIONARITY_ASSUMPTION
    for year in vd.JENKINS_ONLY_YEARS:
        assert year not in vd.DENOMINATOR_YEARS
        assert vd.JENKINS_WINDOW[0] <= year <= vd.JENKINS_WINDOW[1]
    assert vd.missing_denominator_reason(2022) == vd.NO_PAUSE_ERA_DENOMINATOR


def test_jenkins_unit_is_a_fraction_of_a_required_report_voyage() -> None:
    """37,258 over fourteen years of the declared bracket is ~half a voyage each."""
    low, high = vd.jenkins_unit_ratio_interval()

    assert (low, high) == pytest.approx((0.4815, 0.6714), abs=0.0005)
    assert high < 1.0


def test_posting_step_is_bounded_by_the_observed_floor_and_the_ceiling() -> None:
    step = vd.posted_to_investigated()

    assert set(step["by_year"]) == set(vd.DENOMINATOR_YEARS)
    assert min(step["by_year"].values()) == pytest.approx(9 / 17)
    assert max(step["by_year"].values()) == pytest.approx(14 / 15)
    assert step["interval"] == (pytest.approx(9 / 17), 1.0)
    assert step["observed_mean"] == pytest.approx(0.701, abs=0.001)
    assert step["jenkins_ratio"] == pytest.approx(208 / 156)
    assert step["jenkins_ratio"] > vd.POSTED_TO_INVESTIGATED_CEILING
