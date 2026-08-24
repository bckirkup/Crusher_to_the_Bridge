"""Would each payer contribute, and up to what — in cash or in hours.

The tests hold the scenario fixed and move only the conversion rate, so any
change in a payer's position is attributable to the price of a labour hour and
not to a different simulated voyage.  That is the whole reason the rate is an
input rather than a constant.
"""

from __future__ import annotations

import pytest

from picard_framework.analysis.economics import (
    COMMUNITY_AFLOAT,
    COMMUNITY_SHORE,
    LABOUR_RATE_GRID,
    MEDIUM_CASH,
    MEDIUM_LABOUR_HOURS,
    PAYER_PORT_AUTHORITY,
    PAYER_PUBLIC_HEALTH_AGENCY,
    PAYER_SHIP_OPERATOR,
    PAYERS,
    UNIT_VALUATION,
    AfloatBenefit,
    Contribution,
    ContributionLedger,
    ContributionRates,
    PayerPosition,
    ShoreBenefit,
    benefit_split,
    evaluate_payers,
    labour_rate_sensitivity,
)

RATES = ContributionRates(usd_per_labour_hour=50.0)

#: 100 afloat cases and 400 shore cases averted, valued equally, so every
#: monetary figure below is also a case count.
SPLIT = benefit_split(
    AfloatBenefit(cases_averted=100.0),
    ShoreBenefit(cases_averted=400.0),
    UNIT_VALUATION,
)

LEDGER = ContributionLedger.of([
    Contribution(
        payer=PAYER_SHIP_OPERATOR, medium=MEDIUM_CASH, quantity=300.0,
    ),
    Contribution(
        payer=PAYER_PORT_AUTHORITY, medium=MEDIUM_LABOUR_HOURS, quantity=4.0,
    ),
])


def _positions(rates: ContributionRates = RATES) -> dict[str, PayerPosition]:
    """Index the evaluated positions by payer."""
    return {
        position.payer: position
        for position in evaluate_payers(LEDGER, rates, SPLIT)
    }


class TestPayerPositions:
    """Cost, benefit, and the gap between them, per payer."""

    def test_every_payer_is_reported(self) -> None:
        assert set(_positions()) == set(PAYERS)

    def test_communities_are_assigned_not_inferred(self) -> None:
        positions = _positions()
        assert positions[PAYER_SHIP_OPERATOR].community == COMMUNITY_AFLOAT
        assert positions[PAYER_PORT_AUTHORITY].community == COMMUNITY_SHORE
        assert positions[PAYER_PUBLIC_HEALTH_AGENCY].community == COMMUNITY_SHORE

    def test_cost_comes_from_the_ledger_at_the_declared_rate(self) -> None:
        positions = _positions()
        assert positions[PAYER_SHIP_OPERATOR].cost_usd == pytest.approx(300.0)
        assert positions[PAYER_PORT_AUTHORITY].cost_usd == pytest.approx(200.0)
        assert positions[PAYER_PUBLIC_HEALTH_AGENCY].cost_usd == pytest.approx(0.0)

    def test_benefit_comes_from_the_split_at_the_declared_weights(self) -> None:
        positions = _positions()
        assert positions[PAYER_SHIP_OPERATOR].benefit_usd == pytest.approx(100.0)
        assert positions[PAYER_PORT_AUTHORITY].benefit_usd == pytest.approx(200.0)

    def test_net_position_is_benefit_minus_cost(self) -> None:
        positions = _positions()
        assert positions[PAYER_SHIP_OPERATOR].net_usd == pytest.approx(-200.0)
        assert positions[PAYER_PORT_AUTHORITY].net_usd == pytest.approx(0.0)

    def test_break_even_contribution_is_the_benefit_received(self) -> None:
        position = _positions()[PAYER_PORT_AUTHORITY]
        assert position.break_even_cost_usd == pytest.approx(position.benefit_usd)

    def test_break_even_labour_hours_is_the_in_kind_form_of_that_threshold(
        self,
    ) -> None:
        position = _positions()[PAYER_PORT_AUTHORITY]
        assert position.break_even_labour_hours(RATES) == pytest.approx(4.0)

    def test_a_cheaper_hour_buys_more_break_even_hours(self) -> None:
        position = _positions()[PAYER_PORT_AUTHORITY]
        cheap = ContributionRates(usd_per_labour_hour=10.0)
        assert position.break_even_labour_hours(cheap) > position.break_even_labour_hours(
            RATES,
        )

    def test_unpriced_labour_has_no_break_even_in_hours(self) -> None:
        free = ContributionRates(usd_per_labour_hour=0.0)
        assert _positions(free)[PAYER_PORT_AUTHORITY].break_even_labour_hours(
            free,
        ) is None

    def test_a_payer_underwater_is_not_rational_to_contribute(self) -> None:
        assert _positions()[PAYER_SHIP_OPERATOR].rational_to_contribute is False

    def test_a_payer_exactly_at_break_even_is_still_rational(self) -> None:
        assert _positions()[PAYER_PORT_AUTHORITY].rational_to_contribute is True

    def test_headroom_never_reports_a_negative_capacity(self) -> None:
        assert _positions()[PAYER_SHIP_OPERATOR].headroom_usd == pytest.approx(0.0)

    def test_headroom_is_the_net_position_when_positive(self) -> None:
        position = _positions()[PAYER_PUBLIC_HEALTH_AGENCY]
        assert position.headroom_usd == pytest.approx(position.net_usd)

    def test_benefit_to_cost_ratio_is_undefined_for_a_payer_paying_nothing(
        self,
    ) -> None:
        assert _positions()[PAYER_PUBLIC_HEALTH_AGENCY].benefit_to_cost_ratio is None

    def test_benefit_to_cost_ratio_reports_value_per_dollar_spent(self) -> None:
        assert _positions()[PAYER_SHIP_OPERATOR].benefit_to_cost_ratio == pytest.approx(
            100.0 / 300.0,
        )

    def test_shares_sum_to_one_across_payers(self) -> None:
        positions = evaluate_payers(LEDGER, RATES, SPLIT)
        assert sum(item.cost_share for item in positions) == pytest.approx(1.0)
        assert sum(item.benefit_share for item in positions) == pytest.approx(1.0)

    def test_cost_share_can_exceed_benefit_share(self) -> None:
        position = _positions()[PAYER_SHIP_OPERATOR]
        assert position.cost_share > position.benefit_share

    def test_flattened_row_carries_every_reported_quantity(self) -> None:
        row = _positions()[PAYER_PORT_AUTHORITY].to_dict(RATES)
        assert set(row) == {
            "payer",
            "community",
            "cost_usd",
            "benefit_usd",
            "cost_share",
            "benefit_share",
            "net_usd",
            "break_even_cost_usd",
            "break_even_labour_hours",
            "benefit_to_cost_ratio",
            "rational_to_contribute",
        }


class TestDifferentialAttribution:
    """Who pays changes the answer; what is paid in does not change the total."""

    def test_moving_labour_to_another_payer_moves_the_net_position(self) -> None:
        agency_seconds = ContributionLedger.of([
            Contribution(
                payer=PAYER_PUBLIC_HEALTH_AGENCY,
                medium=MEDIUM_LABOUR_HOURS,
                quantity=4.0,
            ),
        ])
        port_seconds = ContributionLedger.of([
            Contribution(
                payer=PAYER_PORT_AUTHORITY,
                medium=MEDIUM_LABOUR_HOURS,
                quantity=4.0,
            ),
        ])
        agency = {p.payer: p for p in evaluate_payers(agency_seconds, RATES, SPLIT)}
        port = {p.payer: p for p in evaluate_payers(port_seconds, RATES, SPLIT)}
        assert agency[PAYER_PUBLIC_HEALTH_AGENCY].cost_usd == pytest.approx(200.0)
        assert port[PAYER_PUBLIC_HEALTH_AGENCY].cost_usd == pytest.approx(0.0)
        assert agency[PAYER_PUBLIC_HEALTH_AGENCY].net_usd < port[
            PAYER_PUBLIC_HEALTH_AGENCY
        ].net_usd

    def test_cash_and_equivalent_labour_produce_the_same_position(self) -> None:
        cash = ContributionLedger.of([
            Contribution(
                payer=PAYER_PORT_AUTHORITY, medium=MEDIUM_CASH, quantity=200.0,
            ),
        ])
        labour = ContributionLedger.of([
            Contribution(
                payer=PAYER_PORT_AUTHORITY,
                medium=MEDIUM_LABOUR_HOURS,
                quantity=4.0,
            ),
        ])
        by_cash = {p.payer: p for p in evaluate_payers(cash, RATES, SPLIT)}
        by_labour = {p.payer: p for p in evaluate_payers(labour, RATES, SPLIT)}
        assert by_cash[PAYER_PORT_AUTHORITY].net_usd == pytest.approx(
            by_labour[PAYER_PORT_AUTHORITY].net_usd,
        )

    def test_a_larger_shore_benefit_makes_a_port_more_willing(self) -> None:
        small = benefit_split(
            AfloatBenefit(cases_averted=100.0),
            ShoreBenefit(cases_averted=10.0),
            UNIT_VALUATION,
        )
        lean = {p.payer: p for p in evaluate_payers(LEDGER, RATES, small)}
        rich = _positions()
        assert lean[PAYER_PORT_AUTHORITY].rational_to_contribute is False
        assert rich[PAYER_PORT_AUTHORITY].rational_to_contribute is True


class TestDegenerateScenarios:
    """No benefit and no cost are reported as such, not as failures."""

    def test_no_benefit_leaves_every_payer_unwilling_to_pay_anything(self) -> None:
        nothing = benefit_split(AfloatBenefit(), ShoreBenefit(), UNIT_VALUATION)
        for position in evaluate_payers(LEDGER, RATES, nothing):
            assert position.benefit_usd == pytest.approx(0.0)
            assert position.break_even_cost_usd == pytest.approx(0.0)
            assert position.benefit_share == pytest.approx(0.0)
        rational = {
            position.payer: position.rational_to_contribute
            for position in evaluate_payers(LEDGER, RATES, nothing)
        }
        assert rational[PAYER_SHIP_OPERATOR] is False
        assert rational[PAYER_PUBLIC_HEALTH_AGENCY] is True

    def test_a_free_capability_is_rational_for_everyone(self) -> None:
        positions = evaluate_payers(ContributionLedger(), RATES, SPLIT)
        for position in positions:
            assert position.cost_usd == pytest.approx(0.0)
            assert position.cost_share == pytest.approx(0.0)
            assert position.benefit_to_cost_ratio is None
            assert position.rational_to_contribute is True

    def test_a_negative_afloat_difference_survives_into_the_position(self) -> None:
        harmful = benefit_split(
            AfloatBenefit(cases_averted=-50.0),
            ShoreBenefit(cases_averted=400.0),
            UNIT_VALUATION,
        )
        positions = {p.payer: p for p in evaluate_payers(LEDGER, RATES, harmful)}
        assert positions[PAYER_SHIP_OPERATOR].benefit_usd == pytest.approx(-50.0)
        assert positions[PAYER_SHIP_OPERATOR].rational_to_contribute is False


class TestLabourRateSensitivity:
    """The deliverable is the surface, not the point."""

    def test_grid_is_swept_for_every_payer(self) -> None:
        rows = labour_rate_sensitivity(LEDGER, RATES, SPLIT, LABOUR_RATE_GRID)
        assert len(rows) == len(LABOUR_RATE_GRID) * len(PAYERS)
        assert {row["usd_per_labour_hour"] for row in rows} == set(LABOUR_RATE_GRID)

    def test_only_the_seconding_payer_moves_with_the_rate(self) -> None:
        rows = labour_rate_sensitivity(LEDGER, RATES, SPLIT, (10.0, 120.0))
        operator = {
            row["usd_per_labour_hour"]: row["cost_usd"]
            for row in rows
            if row["payer"] == PAYER_SHIP_OPERATOR
        }
        port = {
            row["usd_per_labour_hour"]: row["cost_usd"]
            for row in rows
            if row["payer"] == PAYER_PORT_AUTHORITY
        }
        assert operator[10.0] == pytest.approx(operator[120.0])
        assert port[120.0] > port[10.0]

    def test_a_port_flips_from_willing_to_unwilling_across_the_grid(self) -> None:
        rows = labour_rate_sensitivity(LEDGER, RATES, SPLIT, (10.0, 120.0))
        verdicts = {
            row["usd_per_labour_hour"]: row["rational_to_contribute"]
            for row in rows
            if row["payer"] == PAYER_PORT_AUTHORITY
        }
        assert verdicts[10.0] is True
        assert verdicts[120.0] is False

    def test_benefit_never_moves_with_the_labour_rate(self) -> None:
        rows = labour_rate_sensitivity(LEDGER, RATES, SPLIT, LABOUR_RATE_GRID)
        benefits = {
            (row["payer"], row["benefit_usd"]) for row in rows
        }
        assert len(benefits) == len(PAYERS)

    def test_in_kind_fraction_rises_with_the_rate(self) -> None:
        rows = labour_rate_sensitivity(LEDGER, RATES, SPLIT, (10.0, 120.0))
        fractions = {
            row["usd_per_labour_hour"]: row["in_kind_fraction"] for row in rows
        }
        assert fractions[120.0] > fractions[10.0]

    def test_consumable_rates_are_carried_through_the_sweep(self) -> None:
        rates = ContributionRates(
            usd_per_labour_hour=1.0,
            usd_per_consumable_unit=7.0,
            consumable_unit_costs={"pcr_kit": 25.0},
        )
        ledger = ContributionLedger.of([
            Contribution(
                payer=PAYER_PORT_AUTHORITY,
                medium="consumables",
                quantity=2.0,
                item="pcr_kit",
            ),
        ])
        rows = labour_rate_sensitivity(ledger, rates, SPLIT, (5.0,))
        port = next(row for row in rows if row["payer"] == PAYER_PORT_AUTHORITY)
        assert port["cost_usd"] == pytest.approx(50.0)

    def test_an_empty_grid_is_refused(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            labour_rate_sensitivity(LEDGER, RATES, SPLIT, ())

    @pytest.mark.parametrize("bad", [-1.0, float("nan")])
    def test_an_unusable_grid_value_is_refused(self, bad: float) -> None:
        with pytest.raises(ValueError, match="finite and non-negative"):
            labour_rate_sensitivity(LEDGER, RATES, SPLIT, (10.0, bad))
