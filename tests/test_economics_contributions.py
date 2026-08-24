"""Contribution ledger: payer, medium, conversion rate, net cost per payer.

The property under test throughout is that a contribution's *medium* never
leaks into the arithmetic: two hundred person-hours and the cash they are worth
must produce the same total, the same payer, and a different in-kind fraction.
"""

from __future__ import annotations

import pytest

from picard_framework.analysis.economics import (
    MEDIA,
    MEDIUM_CASH,
    MEDIUM_CONSUMABLES,
    MEDIUM_LABOUR_HOURS,
    PAYER_PORT_AUTHORITY,
    PAYER_PUBLIC_HEALTH_AGENCY,
    PAYER_SHIP_OPERATOR,
    PAYERS,
    Contribution,
    ContributionLedger,
    ContributionRates,
)

RATES = ContributionRates(
    usd_per_labour_hour=50.0,
    usd_per_consumable_unit=2.0,
    consumable_unit_costs={"pcr_kit": 25.0},
)


def _cash(amount: float, payer: str = PAYER_SHIP_OPERATOR) -> Contribution:
    """Build one cash contribution."""
    return Contribution(payer=payer, medium=MEDIUM_CASH, quantity=amount)


def _labour(hours: float, payer: str = PAYER_PORT_AUTHORITY) -> Contribution:
    """Build one seconded-labour contribution."""
    return Contribution(payer=payer, medium=MEDIUM_LABOUR_HOURS, quantity=hours)


def _items(count: float, item: str, payer: str = PAYER_PUBLIC_HEALTH_AGENCY):
    """Build one consumable contribution."""
    return Contribution(
        payer=payer, medium=MEDIUM_CONSUMABLES, quantity=count, item=item,
    )


class TestContributionRates:
    """Conversion rates are explicit inputs, and cash is the identity."""

    def test_cash_converts_one_for_one(self) -> None:
        assert RATES.usd_per_unit(MEDIUM_CASH) == pytest.approx(1.0)

    def test_labour_uses_the_declared_hourly_rate(self) -> None:
        assert RATES.usd_per_unit(MEDIUM_LABOUR_HOURS) == pytest.approx(50.0)

    def test_named_consumable_overrides_the_default_unit_cost(self) -> None:
        assert RATES.usd_per_unit(MEDIUM_CONSUMABLES, "pcr_kit") == pytest.approx(
            25.0,
        )

    def test_unnamed_consumable_falls_back_to_the_default(self) -> None:
        assert RATES.usd_per_unit(MEDIUM_CONSUMABLES) == pytest.approx(2.0)

    def test_unknown_consumable_falls_back_to_the_default(self) -> None:
        assert RATES.usd_per_unit(MEDIUM_CONSUMABLES, "swab") == pytest.approx(2.0)

    def test_unknown_medium_is_refused_rather_than_priced_at_zero(self) -> None:
        with pytest.raises(ValueError, match="unknown medium"):
            RATES.usd_per_unit("goodwill")

    @pytest.mark.parametrize("bad", [-1.0, float("nan"), float("inf")])
    def test_labour_rate_must_be_finite_and_non_negative(self, bad: float) -> None:
        with pytest.raises(ValueError):
            ContributionRates(usd_per_labour_hour=bad)

    def test_consumable_default_must_be_non_negative(self) -> None:
        with pytest.raises(ValueError, match="usd_per_consumable_unit"):
            ContributionRates(usd_per_labour_hour=1.0, usd_per_consumable_unit=-1.0)

    def test_per_item_cost_must_be_non_negative(self) -> None:
        with pytest.raises(ValueError, match="consumable_unit_costs"):
            ContributionRates(
                usd_per_labour_hour=1.0, consumable_unit_costs={"kit": -3.0},
            )

    def test_item_names_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            ContributionRates(
                usd_per_labour_hour=1.0, consumable_unit_costs={"": 3.0},
            )

    def test_declared_costs_are_not_mutable_through_the_rates(self) -> None:
        costs = {"pcr_kit": 25.0}
        rates = ContributionRates(
            usd_per_labour_hour=1.0, consumable_unit_costs=costs,
        )
        costs["pcr_kit"] = 1.0
        assert rates.usd_per_unit(MEDIUM_CONSUMABLES, "pcr_kit") == pytest.approx(
            25.0,
        )


class TestContributionValidation:
    """A contribution that cannot name its payer or medium is not recorded."""

    def test_unknown_payer_is_refused(self) -> None:
        with pytest.raises(ValueError, match="unknown payer"):
            Contribution(payer="stowaway", medium=MEDIUM_CASH, quantity=1.0)

    def test_unknown_medium_is_refused(self) -> None:
        with pytest.raises(ValueError, match="unknown medium"):
            Contribution(
                payer=PAYER_SHIP_OPERATOR, medium="goodwill", quantity=1.0,
            )

    def test_negative_quantity_is_refused(self) -> None:
        with pytest.raises(ValueError, match="quantity"):
            _cash(-5.0)

    def test_non_finite_quantity_is_refused(self) -> None:
        with pytest.raises(ValueError, match="quantity"):
            _cash(float("inf"))

    def test_item_is_meaningless_outside_consumables(self) -> None:
        with pytest.raises(ValueError, match="only meaningful for consumables"):
            Contribution(
                payer=PAYER_SHIP_OPERATOR,
                medium=MEDIUM_CASH,
                quantity=1.0,
                item="pcr_kit",
            )

    def test_blank_item_is_refused(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            _items(1.0, "   ")


class TestMonetaryEquivalent:
    """Each medium converts through its own declared rate and no other."""

    def test_labour_hours_convert_at_the_hourly_rate(self) -> None:
        assert _labour(10.0).monetary_equivalent(RATES) == pytest.approx(500.0)

    def test_named_consumables_convert_at_the_item_cost(self) -> None:
        assert _items(4.0, "pcr_kit").monetary_equivalent(RATES) == pytest.approx(
            100.0,
        )

    def test_a_higher_labour_rate_raises_the_labour_equivalent(self) -> None:
        cheap = ContributionRates(usd_per_labour_hour=10.0)
        dear = ContributionRates(usd_per_labour_hour=100.0)
        contribution = _labour(10.0)
        assert contribution.monetary_equivalent(dear) > contribution.monetary_equivalent(
            cheap,
        )

    def test_labour_rate_does_not_touch_cash(self) -> None:
        cash = _cash(500.0)
        assert cash.monetary_equivalent(
            ContributionRates(usd_per_labour_hour=10.0),
        ) == pytest.approx(
            cash.monetary_equivalent(ContributionRates(usd_per_labour_hour=999.0)),
        )


class TestLedgerAggregation:
    """Totals, payer attribution, and the in-kind share."""

    @staticmethod
    def _ledger() -> ContributionLedger:
        return ContributionLedger.of([
            _cash(1_000.0),
            _labour(10.0),
            _items(4.0, "pcr_kit"),
        ])

    def test_total_is_the_sum_of_monetary_equivalents(self) -> None:
        assert self._ledger().total_usd(RATES) == pytest.approx(1_600.0)

    def test_every_payer_appears_even_when_paying_nothing(self) -> None:
        ledger = ContributionLedger.of([_cash(100.0)])
        by_payer = ledger.by_payer_usd(RATES)
        assert set(by_payer) == set(PAYERS)
        assert by_payer[PAYER_PORT_AUTHORITY] == pytest.approx(0.0)

    def test_payer_totals_reconcile_with_the_grand_total(self) -> None:
        ledger = self._ledger()
        assert sum(ledger.by_payer_usd(RATES).values()) == pytest.approx(
            ledger.total_usd(RATES),
        )

    def test_medium_totals_reconcile_with_the_grand_total(self) -> None:
        ledger = self._ledger()
        assert set(ledger.by_medium_usd(RATES)) == set(MEDIA)
        assert sum(ledger.by_medium_usd(RATES).values()) == pytest.approx(
            ledger.total_usd(RATES),
        )

    def test_cost_shares_sum_to_one_when_there_is_a_cost(self) -> None:
        assert sum(self._ledger().cost_shares(RATES).values()) == pytest.approx(1.0)

    def test_in_kind_fraction_is_the_non_cash_share(self) -> None:
        assert self._ledger().in_kind_fraction(RATES) == pytest.approx(600 / 1600)

    def test_an_all_cash_ledger_has_no_in_kind_share(self) -> None:
        assert ContributionLedger.of([_cash(100.0)]).in_kind_fraction(
            RATES,
        ) == pytest.approx(0.0)

    def test_an_all_labour_ledger_is_entirely_in_kind(self) -> None:
        assert ContributionLedger.of([_labour(3.0)]).in_kind_fraction(
            RATES,
        ) == pytest.approx(1.0)

    def test_reattributing_a_medium_moves_cost_between_payers(self) -> None:
        operator_pays = ContributionLedger.of([_labour(10.0, PAYER_SHIP_OPERATOR)])
        port_pays = ContributionLedger.of([_labour(10.0, PAYER_PORT_AUTHORITY)])
        assert operator_pays.total_usd(RATES) == pytest.approx(
            port_pays.total_usd(RATES),
        )
        assert operator_pays.cost_shares(RATES)[PAYER_SHIP_OPERATOR] == pytest.approx(
            1.0,
        )
        assert port_pays.cost_shares(RATES)[PAYER_SHIP_OPERATOR] == pytest.approx(0.0)

    def test_raising_the_labour_rate_raises_the_seconding_payer_share(self) -> None:
        ledger = self._ledger()
        cheap = ContributionRates(usd_per_labour_hour=1.0, usd_per_consumable_unit=2.0)
        dear = ContributionRates(usd_per_labour_hour=500.0, usd_per_consumable_unit=2.0)
        assert (
            ledger.cost_shares(dear)[PAYER_PORT_AUTHORITY]
            > ledger.cost_shares(cheap)[PAYER_PORT_AUTHORITY]
        )


class TestEmptyLedger:
    """Nothing spent is reported as nothing, not as a distribution."""

    def test_total_is_zero(self) -> None:
        assert ContributionLedger().total_usd(RATES) == pytest.approx(0.0)

    def test_shares_are_zero_rather_than_normalised(self) -> None:
        shares = ContributionLedger().cost_shares(RATES)
        assert set(shares) == set(PAYERS)
        assert sum(shares.values()) == pytest.approx(0.0)

    def test_in_kind_fraction_does_not_divide_by_zero(self) -> None:
        assert ContributionLedger().in_kind_fraction(RATES) == pytest.approx(0.0)

    def test_a_free_medium_leaves_the_total_at_zero(self) -> None:
        free = ContributionRates(usd_per_labour_hour=0.0)
        ledger = ContributionLedger.of([_labour(40.0)])
        assert ledger.total_usd(free) == pytest.approx(0.0)
        assert ledger.in_kind_fraction(free) == pytest.approx(0.0)
