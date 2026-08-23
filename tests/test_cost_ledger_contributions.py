"""Behavioural tests for payer-attributed contribution accounting."""

from __future__ import annotations

import json
import math

import pytest

from crusher_labs.cost_ledger import (
    CATEGORY_INTERVENTION,
    CATEGORY_SURVEILLANCE,
    CONTRIBUTION_MEDIA,
    CONTRIBUTION_PAYERS,
    ContributionRecord,
    CostLedger,
    compute_operational_impact,
)


def contribution(
    *,
    payer: str = "port_authority",
    medium: str = "labour_hours",
    quantity: float = 4.0,
    rate: float = 50.0,
) -> ContributionRecord:
    return ContributionRecord(
        epoch=2,
        payer=payer,
        medium=medium,
        quantity=quantity,
        conversion_rate_usd_per_unit=rate,
        category=CATEGORY_SURVEILLANCE,
        source="port_health",
        description="Seconded laboratory technician",
    )


def test_contribution_validates_vocabularies_and_amounts() -> None:
    with pytest.raises(ValueError, match="unknown contribution payer"):
        contribution(payer="port")
    with pytest.raises(ValueError, match="unknown contribution medium"):
        contribution(medium="staff")
    with pytest.raises(ValueError, match="cash.*exactly 1.0"):
        contribution(medium="cash", rate=2.0)
    with pytest.raises(ValueError, match="quantity"):
        contribution(quantity=-1.0)
    with pytest.raises(ValueError, match="quantity"):
        contribution(quantity=math.inf)
    with pytest.raises(ValueError, match="conversion rate"):
        contribution(rate=-1.0)
    with pytest.raises(ValueError, match="conversion rate"):
        contribution(rate=math.nan)
    with pytest.raises(ValueError, match="category"):
        ContributionRecord(2, "port_authority", "cash", 1.0, 1.0, "other", "x")
    with pytest.raises(ValueError, match="epoch"):
        ContributionRecord(-1, "port_authority", "cash", 1.0, 1.0, CATEGORY_SURVEILLANCE, "x")


def test_contribution_monetary_equivalent_scales_with_quantity_and_rate() -> None:
    base = contribution(quantity=2.0, rate=25.0)
    doubled_quantity = contribution(quantity=4.0, rate=25.0)
    doubled_rate = contribution(quantity=2.0, rate=50.0)
    assert base.monetary_equivalent_usd == pytest.approx(50.0)
    assert doubled_quantity.monetary_equivalent_usd == pytest.approx(
        2 * base.monetary_equivalent_usd,
    )
    assert doubled_rate.monetary_equivalent_usd == pytest.approx(
        2 * base.monetary_equivalent_usd,
    )
    assert base.to_dict()["monetary_equivalent_usd"] == pytest.approx(50.0)


def test_recording_contribution_does_not_change_spend_or_balances() -> None:
    ledger = CostLedger(starting_financial_usd=1000.0, starting_labor_hours=100.0)
    ledger.debit(
        epoch=1,
        source="test",
        category=CATEGORY_INTERVENTION,
        financial_usd=100.0,
        labor_hours=3.0,
    )
    state_before = (
        ledger.financial_balance,
        ledger.labor_remaining,
        ledger._total_surveillance_usd,
        ledger._total_intervention_usd,
        ledger.generate_financial_audit(),
    )
    recorded = ledger.record_contribution(contribution())
    assert recorded is ledger.contributions[0]
    assert ledger.financial_balance == state_before[0]
    assert ledger.labor_remaining == state_before[1]
    assert ledger._total_surveillance_usd == state_before[2]
    assert ledger._total_intervention_usd == state_before[3]
    assert ledger.generate_financial_audit()["summary"] == state_before[4]["summary"]
    assert ledger.generate_financial_audit()["contributions"]["entries"]


def test_record_contribution_requires_a_contribution_record() -> None:
    with pytest.raises(TypeError, match="ContributionRecord"):
        CostLedger().record_contribution(object())  # type: ignore[arg-type]


def test_no_contribution_audit_remains_byte_identical() -> None:
    first = CostLedger(starting_financial_usd=1000.0)
    second = CostLedger(starting_financial_usd=1000.0)
    for ledger in (first, second):
        ledger.debit(
            epoch=1,
            source="test",
            category=CATEGORY_SURVEILLANCE,
            financial_usd=12.34,
            description="Routine check",
        )
    first_bytes = json.dumps(
        first.generate_financial_audit(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    second_bytes = json.dumps(
        second.generate_financial_audit(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    assert first_bytes == second_bytes
    assert "contributions" not in first.generate_financial_audit()


def test_contribution_summary_reports_payers_and_positive_shares() -> None:
    ledger = CostLedger()
    ledger.record_contribution(contribution(payer="ship_operator", medium="cash", quantity=100.0, rate=1.0))
    ledger.record_contribution(contribution(payer="port_authority", medium="labour_hours"))
    ledger.record_contribution(contribution(payer="port_authority", medium="consumables", quantity=2.0, rate=10.0))

    summary = ledger.contribution_summary()
    assert set(summary) == set(CONTRIBUTION_PAYERS)
    assert summary["ship_operator"]["cash_usd"] == pytest.approx(100.0)
    assert summary["port_authority"]["in_kind_usd"]["labour_hours"] == pytest.approx(200.0)
    assert summary["port_authority"]["in_kind_usd"]["consumables"] == pytest.approx(20.0)
    assert sum(item["share_of_total"] for item in summary.values()) == pytest.approx(1.0)
    assert summary["port_authority"]["total_usd"] == pytest.approx(220.0)


def test_zero_contribution_total_has_zero_shares() -> None:
    summary = CostLedger().contribution_summary()
    assert set(summary) == set(CONTRIBUTION_PAYERS)
    assert all(item["share_of_total"] == 0.0 for item in summary.values())
    assert all(item["total_usd"] == 0.0 for item in summary.values())


def test_conversion_override_changes_only_in_kind_values() -> None:
    ledger = CostLedger()
    ledger.record_contribution(contribution(payer="ship_operator", medium="cash", quantity=100.0, rate=1.0))
    ledger.record_contribution(contribution(payer="port_authority", quantity=4.0, rate=25.0))
    baseline = ledger.contribution_summary()
    overridden = ledger.contribution_summary({"labour_hours": 100.0})
    assert overridden["port_authority"]["total_usd"] > baseline["port_authority"]["total_usd"]
    assert overridden["port_authority"]["share_of_total"] > baseline["port_authority"]["share_of_total"]
    assert overridden["ship_operator"]["total_usd"] == pytest.approx(
        baseline["ship_operator"]["total_usd"],
    )
    assert overridden["ship_operator"]["cash_usd"] == pytest.approx(100.0)


def test_conversion_override_validation() -> None:
    ledger = CostLedger()
    for overrides, message in (
        ({"unknown": 1.0}, "unknown contribution media"),
        ({"labour_hours": -1.0}, "finite and non-negative"),
        ({"consumables": math.inf}, "finite and non-negative"),
        ({"cash": 2.0}, "cash.*exactly 1.0"),
    ):
        with pytest.raises(ValueError, match=message):
            ledger.contribution_summary(overrides)


def test_reconciliation_exposes_unallocated_expenditure() -> None:
    ledger = CostLedger()
    ledger.debit(0, "routine", CATEGORY_SURVEILLANCE, financial_usd=100.0)
    ledger.record_contribution(contribution(medium="cash", quantity=40.0, rate=1.0))
    reconciliation = ledger.contribution_reconciliation()
    assert reconciliation["contribution_total_usd"] == pytest.approx(40.0)
    assert reconciliation["ledger_total_expenditure_usd"] == pytest.approx(100.0)
    assert reconciliation["gap_usd"] == pytest.approx(-60.0)
    assert reconciliation["unallocated_expenditure_usd"] == pytest.approx(60.0)


def test_contribution_media_constant_contains_expected_vocabulary() -> None:
    assert CONTRIBUTION_MEDIA == ("cash", "labour_hours", "consumables")


def test_existing_cost_paths_remain_covered() -> None:
    ledger = CostLedger(
        starting_inventory={"swabs": 2},
        material_unit_costs={"swabs": 3.0},
    )
    ledger.accumulate_operational_impact(0, 0.0)
    ledger.accumulate_operational_impact(0, -1.0, {"manual": 1.0})
    assert ledger.operational_impact_cumulative == pytest.approx(0.0)
    ledger.debit_per_test(0, "missing", 1, {})
    ledger.debit_per_test(0, "clinical_rdt", 0, {"clinical_rdt": {}})
    ledger.debit_per_test(
        0,
        "clinical_rdt",
        2,
        {"clinical_rdt": {"financial_usd": 4.0, "materials": {"swabs": 1}}},
    )
    ledger.debit_protocol(
        1,
        "SOP-1",
        "Response",
        {"financial_usd": 2.0},
        is_activation=True,
    )
    ledger.debit_protocol(2, "SOP-1", "Response", {"financial_usd": 1.0})
    assert ledger.is_material_depleted("unknown")
    audit = ledger.generate_financial_audit()
    assert audit["material_inventory"]["swabs"]["total_cost_usd"] == pytest.approx(6.0)
    total, breakdown = compute_operational_impact(
        agents=[
            {"agent_id": 1, "role": "passenger", "agent_class": "passenger_general"},
        ],
        quarantined_ids=set(),
        isolated_ids={1},
        merged_modifiers={
            "close_zones": ["galley-1"],
            "ppe_transmission_reduction": 0.2,
        },
        active_protocol_ids=[],
        ois_weights={},
        zone_type_by_id={"galley-1": "galley"},
    )
    assert total > 0
    assert breakdown["passenger_isolation"] > 0
    assert breakdown["closed_galley_zones"] > 0
    assert breakdown["fleet_ppe"] > 0
