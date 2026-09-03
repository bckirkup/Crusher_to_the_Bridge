"""The simulated cost ledger acquires a payer, and only surveillance lines.

Intervention spend is deliberately excluded: pooling it with surveillance makes
the capability look more expensive the worse it performed, which inverts the
question the economics layer exists to answer.
"""

from __future__ import annotations

from typing import Any

import pytest

from crusher_labs.cost_ledger import CostLedger
from picard_framework.analysis.economics import (
    MEDIUM_CASH,
    MEDIUM_CONSUMABLES,
    MEDIUM_LABOUR_HOURS,
    PAYER_PORT_AUTHORITY,
    PAYER_PUBLIC_HEALTH_AGENCY,
    PAYER_SHIP_OPERATOR,
    ContributionRates,
    contributions_from_financial_audit,
)

RATES = ContributionRates(
    usd_per_labour_hour=40.0,
    usd_per_consumable_unit=1.0,
    consumable_unit_costs={"pcr_kits": 30.0},
)


def _audit(**overrides: Any) -> dict[str, Any]:
    """Build a FINANCIAL_AUDIT-shaped block."""
    audit: dict[str, Any] = {
        "summary": {
            "surveillance_cost_usd": 1_000.0,
            "surveillance_labor_hours": 20.0,
            "intervention_cost_usd": 9_000.0,
            "intervention_labor_hours": 500.0,
        },
        "itemized_entries": [
            {
                "category": "surveillance",
                "materials": {"pcr_kits": 3},
            },
            {
                "category": "intervention",
                "materials": {"pcr_kits": 100, "isolation_kits": 40},
            },
        ],
    }
    audit.update(overrides)
    return audit


class TestSurveillanceOnly:
    """Only the price of watching is charged to the capability."""

    def test_cash_and_labour_come_from_the_surveillance_summary(self) -> None:
        ledger = contributions_from_financial_audit(_audit())
        media = ledger.by_medium_usd(RATES)
        assert media[MEDIUM_CASH] == pytest.approx(1_000.0)
        assert media[MEDIUM_LABOUR_HOURS] == pytest.approx(800.0)

    def test_intervention_materials_are_not_charged(self) -> None:
        ledger = contributions_from_financial_audit(_audit())
        assert ledger.by_medium_usd(RATES)[MEDIUM_CONSUMABLES] == pytest.approx(90.0)

    def test_intervention_spend_never_reaches_the_total(self) -> None:
        ledger = contributions_from_financial_audit(_audit())
        assert ledger.total_usd(RATES) == pytest.approx(1_890.0)

    def test_repeated_surveillance_entries_accumulate_per_item(self) -> None:
        audit = _audit(itemized_entries=[
            {"category": "surveillance", "materials": {"pcr_kits": 3}},
            {"category": "surveillance", "materials": {"pcr_kits": 2, "swabs": 5}},
        ])
        ledger = contributions_from_financial_audit(audit)
        quantities = {
            item.item: item.quantity for item in ledger.contributions if item.item
        }
        assert quantities == {"pcr_kits": 5.0, "swabs": 5.0}

    def test_an_entry_without_materials_is_tolerated(self) -> None:
        audit = _audit(itemized_entries=[{"category": "surveillance"}])
        ledger = contributions_from_financial_audit(audit)
        assert ledger.by_medium_usd(RATES)[MEDIUM_CONSUMABLES] == pytest.approx(0.0)

    def test_a_run_without_retained_entries_contributes_no_consumables(self) -> None:
        audit = _audit()
        audit.pop("itemized_entries")
        ledger = contributions_from_financial_audit(audit)
        assert ledger.by_medium_usd(RATES)[MEDIUM_CONSUMABLES] == pytest.approx(0.0)

    def test_an_empty_audit_yields_an_empty_ledger(self) -> None:
        ledger = contributions_from_financial_audit({})
        assert ledger.contributions == ()
        assert ledger.total_usd(RATES) == pytest.approx(0.0)

    def test_zero_valued_lines_are_dropped_rather_than_recorded(self) -> None:
        audit = _audit(
            summary={"surveillance_cost_usd": 0.0, "surveillance_labor_hours": 20.0},
            itemized_entries=[
                {"category": "surveillance", "materials": {"pcr_kits": 0}},
            ],
        )
        ledger = contributions_from_financial_audit(audit)
        assert [item.medium for item in ledger.contributions] == [MEDIUM_LABOUR_HOURS]

    def test_lines_are_labelled_for_the_reader(self) -> None:
        ledger = contributions_from_financial_audit(_audit(), label="port berth watch")
        assert all(
            item.description.startswith("port berth watch")
            for item in ledger.contributions
        )


class TestAttribution:
    """The same simulated capability, re-costed under a different arrangement."""

    def test_the_operator_pays_for_everything_by_default(self) -> None:
        ledger = contributions_from_financial_audit(_audit())
        assert ledger.cost_shares(RATES)[PAYER_SHIP_OPERATOR] == pytest.approx(1.0)

    def test_seconded_labour_moves_cost_to_the_port_without_changing_the_total(
        self,
    ) -> None:
        operator = contributions_from_financial_audit(_audit())
        seconded = contributions_from_financial_audit(
            _audit(), attribution={MEDIUM_LABOUR_HOURS: PAYER_PORT_AUTHORITY},
        )
        assert seconded.total_usd(RATES) == pytest.approx(operator.total_usd(RATES))
        assert seconded.by_payer_usd(RATES)[PAYER_PORT_AUTHORITY] == pytest.approx(
            800.0,
        )
        assert operator.by_payer_usd(RATES)[PAYER_PORT_AUTHORITY] == pytest.approx(0.0)

    def test_every_medium_can_be_attributed_separately(self) -> None:
        ledger = contributions_from_financial_audit(
            _audit(),
            attribution={
                MEDIUM_CASH: PAYER_SHIP_OPERATOR,
                MEDIUM_LABOUR_HOURS: PAYER_PORT_AUTHORITY,
                MEDIUM_CONSUMABLES: PAYER_PUBLIC_HEALTH_AGENCY,
            },
        )
        by_payer = ledger.by_payer_usd(RATES)
        assert by_payer[PAYER_SHIP_OPERATOR] == pytest.approx(1_000.0)
        assert by_payer[PAYER_PORT_AUTHORITY] == pytest.approx(800.0)
        assert by_payer[PAYER_PUBLIC_HEALTH_AGENCY] == pytest.approx(90.0)

    def test_an_unknown_medium_is_refused(self) -> None:
        audit = _audit()
        attribution = {"goodwill": PAYER_PORT_AUTHORITY}
        with pytest.raises(ValueError, match="unknown medium"):
            contributions_from_financial_audit(audit, attribution=attribution)

    def test_an_unknown_payer_is_refused(self) -> None:
        audit = _audit()
        attribution = {MEDIUM_CASH: "harbourmaster"}
        with pytest.raises(ValueError, match="unknown payer"):
            contributions_from_financial_audit(audit, attribution=attribution)


class TestAgainstTheRealLedger:
    """The bridge reads what `CostLedger` actually emits, not a hand-written shape."""

    @staticmethod
    def _audit_from_a_run() -> dict[str, Any]:
        ledger = CostLedger(
            starting_financial_usd=100_000.0,
            starting_inventory={"pcr_kits": 100, "isolation_kits": 50},
        )
        ledger.debit(
            epoch=1,
            source="sentinel",
            category="surveillance",
            financial_usd=500.0,
            labor_hours=8.0,
            materials={"pcr_kits": 4},
            description="daily syndromic screening",
        )
        ledger.debit(
            epoch=2,
            source="medical",
            category="intervention",
            financial_usd=2_000.0,
            labor_hours=40.0,
            materials={"isolation_kits": 10},
            description="isolation of a confirmed case",
        )
        return ledger.generate_financial_audit()

    def test_surveillance_lines_are_recovered_from_a_real_audit(self) -> None:
        ledger = contributions_from_financial_audit(self._audit_from_a_run())
        media = ledger.by_medium_usd(RATES)
        assert media[MEDIUM_CASH] == pytest.approx(500.0)
        assert media[MEDIUM_LABOUR_HOURS] == pytest.approx(320.0)
        assert media[MEDIUM_CONSUMABLES] == pytest.approx(120.0)

    def test_the_intervention_line_is_absent_from_a_real_audit(self) -> None:
        ledger = contributions_from_financial_audit(self._audit_from_a_run())
        assert all(item.item != "isolation_kits" for item in ledger.contributions)
