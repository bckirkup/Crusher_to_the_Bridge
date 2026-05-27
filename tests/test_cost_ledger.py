"""
test_cost_ledger.py – Unit tests for the cost accounting module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

from __future__ import annotations

import json
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from crusher_labs.cost_ledger import (
    CostLedger,
    build_ledger_from_config,
    load_resource_costs,
    CATEGORY_SURVEILLANCE,
    CATEGORY_INTERVENTION,
)


class TestCostLedger:
    def test_default_ledger(self) -> None:
        ledger = CostLedger()
        assert ledger.financial_balance >= 0

    def test_debit_reduces_balance(self) -> None:
        ledger = CostLedger(starting_financial_usd=1000.0)
        ledger.debit_baseline_surveillance(0, {"financial_usd": 50.0})
        assert ledger.financial_balance < 1000.0

    def test_get_epoch_summary(self) -> None:
        ledger = CostLedger(starting_financial_usd=500.0)
        ledger.debit_baseline_surveillance(0, {"financial_usd": 10.0, "materials": {"rdt_kits": 2}})
        summary = ledger.get_epoch_summary(0)
        assert isinstance(summary, dict)
        assert summary["epoch"] == 0
        assert summary["entries_count"] >= 1
        assert "materials_consumed" in summary
        assert summary["materials_consumed"]["rdt_kits"] == 2
        assert "by_category" in summary
        assert summary["by_category"][CATEGORY_SURVEILLANCE]["financial_usd"] >= 0.0

    def test_generate_financial_audit(self) -> None:
        ledger = CostLedger(starting_financial_usd=500.0)
        audit = ledger.generate_financial_audit()
        assert "summary" in audit
        assert "material_inventory" in audit
        summary = audit["summary"]
        assert "starting_financial_budget_usd" in summary
        assert "total_expenditure_usd" in summary
        assert "remaining_balance_usd" in summary


class TestBuildLedgerFromConfig:
    def test_loads_default_config(self) -> None:
        path = os.path.join(REPO_ROOT, "data", "config", "resource_costs.json")
        ledger = build_ledger_from_config(path)
        assert isinstance(ledger, CostLedger)
        assert ledger.starting_financial_usd > 0


class TestLoadResourceCosts:
    def test_loads_default_resource_costs(self) -> None:
        path = os.path.join(REPO_ROOT, "data", "config", "resource_costs.json")
        costs = load_resource_costs(path)
        assert isinstance(costs, dict)

    def test_has_expected_keys(self) -> None:
        path = os.path.join(REPO_ROOT, "data", "config", "resource_costs.json")
        costs = load_resource_costs(path)
        assert "baseline_surveillance_costs_per_epoch" in costs or "per_test_costs" in costs
