"""
cost_ledger.py – Comprehensive Cost-Accounting Ledger
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tracks three resource dimensions across a simulation run:

1. **Financial Spend** ($USD) — cumulative surveillance and intervention costs.
2. **Material Inventory** — item counts (masks, test kits, sanitizers, etc.).
3. **Labor Hours** — crew person-hours consumed per epoch.

The ledger is a **tracker**, not a limiter — spending is never blocked
by exhausting a balance.  Starting values are recorded for reporting
purposes (spend-to-date vs. initial allocation).

Produces a ``FINANCIAL_AUDIT`` block for inclusion in the Artificial Lab Notebook,
itemizing total expenditures split by *Surveillance Cost* vs *Intervention Cost*.
"""

from __future__ import annotations

import json
import os
from typing import Any


# ── Ledger entry categories ──────────────────────────────────────────────
CATEGORY_SURVEILLANCE = "surveillance"
CATEGORY_INTERVENTION = "intervention"


class LedgerEntry:
    """Single cost event recorded against the ledger."""

    __slots__ = (
        "epoch", "source", "category", "financial_usd",
        "materials", "labor_hours", "description",
    )

    def __init__(
        self,
        epoch: int,
        source: str,
        category: str,
        financial_usd: float = 0.0,
        materials: dict[str, int] | None = None,
        labor_hours: float = 0.0,
        description: str = "",
    ) -> None:
        self.epoch = epoch
        self.source = source
        self.category = category
        self.financial_usd = financial_usd
        self.materials = materials or {}
        self.labor_hours = labor_hours
        self.description = description

    def to_dict(self) -> dict[str, Any]:
        return {
            "epoch": self.epoch,
            "source": self.source,
            "category": self.category,
            "financial_usd": round(self.financial_usd, 2),
            "materials": dict(self.materials),
            "labor_person_hours": round(self.labor_hours, 2),
            "description": self.description,
        }


class CostLedger:
    """Tracks financial, material, and labor spend across a simulation.

    The ledger records all cost events but never blocks actions due to
    exhausted funds, labor, or materials.  Negative balances simply
    indicate overspend relative to the initial allocation.
    """

    def __init__(
        self,
        starting_financial_usd: float = 50_000.0,
        starting_labor_hours: float = 480.0,
        starting_inventory: dict[str, int] | None = None,
        material_unit_costs: dict[str, float] | None = None,
    ) -> None:
        self.starting_financial_usd = starting_financial_usd
        self.starting_labor_hours = starting_labor_hours
        self.starting_inventory = dict(starting_inventory or {})

        self.financial_balance = starting_financial_usd
        self.labor_remaining = starting_labor_hours
        self.inventory: dict[str, int] = dict(self.starting_inventory)
        self.material_unit_costs: dict[str, float] = dict(material_unit_costs or {})

        self.entries: list[LedgerEntry] = []

        self._total_surveillance_usd = 0.0
        self._total_intervention_usd = 0.0
        self._total_surveillance_labor = 0.0
        self._total_intervention_labor = 0.0
        self._materials_consumed: dict[str, dict[str, int]] = {
            CATEGORY_SURVEILLANCE: {},
            CATEGORY_INTERVENTION: {},
        }

    # ── Core debit method ────────────────────────────────────────────

    def debit(
        self,
        epoch: int,
        source: str,
        category: str,
        financial_usd: float = 0.0,
        materials: dict[str, int] | None = None,
        labor_hours: float = 0.0,
        description: str = "",
    ) -> LedgerEntry:
        """Record a cost event, updating all tracked spend totals."""
        materials = materials or {}

        self.financial_balance -= financial_usd
        self.labor_remaining -= labor_hours

        for item_name, qty in materials.items():
            current = self.inventory.get(item_name, 0)
            self.inventory[item_name] = max(0, current - qty)

        if category == CATEGORY_SURVEILLANCE:
            self._total_surveillance_usd += financial_usd
            self._total_surveillance_labor += labor_hours
            bucket = self._materials_consumed[CATEGORY_SURVEILLANCE]
        else:
            self._total_intervention_usd += financial_usd
            self._total_intervention_labor += labor_hours
            bucket = self._materials_consumed[CATEGORY_INTERVENTION]

        for item_name, qty in materials.items():
            bucket[item_name] = bucket.get(item_name, 0) + qty

        entry = LedgerEntry(
            epoch=epoch,
            source=source,
            category=category,
            financial_usd=financial_usd,
            materials=materials,
            labor_hours=labor_hours,
            description=description,
        )
        self.entries.append(entry)
        return entry

    # ── Convenience debiting methods ─────────────────────────────────

    def debit_baseline_surveillance(
        self,
        epoch: int,
        costs: dict[str, Any],
    ) -> None:
        """Debit fixed per-epoch surveillance costs."""
        self.debit(
            epoch=epoch,
            source="baseline_surveillance",
            category=CATEGORY_SURVEILLANCE,
            financial_usd=costs.get("financial_usd", 0.0),
            materials=costs.get("materials", {}),
            labor_hours=costs.get("labor_person_hours", 0.0),
            description="Fixed per-epoch environmental monitoring",
        )

    def debit_per_test(
        self,
        epoch: int,
        test_type: str,
        count: int,
        per_test_costs: dict[str, Any],
    ) -> None:
        """Debit costs for running *count* tests of a given type."""
        if count <= 0:
            return
        unit = per_test_costs.get(test_type, {})
        if not unit:
            return
        total_usd = unit.get("financial_usd", 0.0) * count
        total_labor = unit.get("labor_person_hours", 0.0) * count
        mats = {k: v * count for k, v in unit.get("materials", {}).items()}

        self.debit(
            epoch=epoch,
            source=f"test:{test_type}",
            category=CATEGORY_SURVEILLANCE,
            financial_usd=total_usd,
            materials=mats,
            labor_hours=total_labor,
            description=f"{count}x {test_type}",
        )

    def debit_protocol(
        self,
        epoch: int,
        protocol_id: str,
        protocol_name: str,
        costs: dict[str, Any],
        category: str = CATEGORY_INTERVENTION,
        is_activation: bool = False,
    ) -> None:
        """Debit costs for a protocol activation or per-epoch maintenance."""
        cost_type = "activation" if is_activation else "per-epoch"
        self.debit(
            epoch=epoch,
            source=f"protocol:{protocol_id}",
            category=category,
            financial_usd=costs.get("financial_usd", 0.0),
            materials=costs.get("materials", {}),
            labor_hours=costs.get("labor_person_hours", 0.0),
            description=f"{protocol_name} ({cost_type})",
        )

    # ── Spend status queries ─────────────────────────────────────────

    def is_material_depleted(self, item_name: str) -> bool:
        """Check if a material item has been fully consumed."""
        return self.inventory.get(item_name, 0) <= 0

    def get_epoch_summary(self, epoch: int) -> dict[str, Any]:
        """Return a summary of costs incurred during a specific epoch."""
        epoch_entries = [e for e in self.entries if e.epoch == epoch]
        total_usd = sum(e.financial_usd for e in epoch_entries)
        total_labor = sum(e.labor_hours for e in epoch_entries)
        return {
            "epoch": epoch,
            "entries_count": len(epoch_entries),
            "total_financial_usd": round(total_usd, 2),
            "total_labor_hours": round(total_labor, 2),
            "financial_balance_remaining": round(self.financial_balance, 2),
            "labor_hours_remaining": round(self.labor_remaining, 2),
        }

    # ── Financial Audit Report ───────────────────────────────────────

    def generate_financial_audit(self) -> dict[str, Any]:
        """Produce the FINANCIAL_AUDIT block for the Artificial Lab Notebook."""
        total_usd = self._total_surveillance_usd + self._total_intervention_usd
        total_labor = self._total_surveillance_labor + self._total_intervention_labor

        all_materials: dict[str, int] = {}
        for bucket in self._materials_consumed.values():
            for item, qty in bucket.items():
                all_materials[item] = all_materials.get(item, 0) + qty

        inventory_status: dict[str, dict[str, Any]] = {}
        for item_name, starting in self.starting_inventory.items():
            remaining = self.inventory.get(item_name, 0)
            consumed = starting - remaining
            unit_cost = self.material_unit_costs.get(item_name, 0.0)
            inventory_status[item_name] = {
                "starting": starting,
                "consumed": consumed,
                "remaining": remaining,
                "total_cost_usd": round(consumed * unit_cost, 2),
            }

        per_epoch: list[dict[str, Any]] = []
        epoch_set = sorted(set(e.epoch for e in self.entries))
        running_balance = self.starting_financial_usd
        for ep in epoch_set:
            ep_entries = [e for e in self.entries if e.epoch == ep]
            ep_surv = sum(e.financial_usd for e in ep_entries if e.category == CATEGORY_SURVEILLANCE)
            ep_intv = sum(e.financial_usd for e in ep_entries if e.category == CATEGORY_INTERVENTION)
            running_balance -= (ep_surv + ep_intv)
            per_epoch.append({
                "epoch": ep,
                "surveillance_usd": round(ep_surv, 2),
                "intervention_usd": round(ep_intv, 2),
                "cumulative_balance_usd": round(running_balance, 2),
            })

        return {
            "audit_type": "FINANCIAL_AUDIT",
            "summary": {
                "starting_financial_budget_usd": round(self.starting_financial_usd, 2),
                "total_expenditure_usd": round(total_usd, 2),
                "remaining_balance_usd": round(self.financial_balance, 2),
                "surveillance_cost_usd": round(self._total_surveillance_usd, 2),
                "intervention_cost_usd": round(self._total_intervention_usd, 2),
                "starting_labor_capacity_hours": round(self.starting_labor_hours, 2),
                "total_labor_consumed_hours": round(total_labor, 2),
                "remaining_labor_hours": round(self.labor_remaining, 2),
                "surveillance_labor_hours": round(self._total_surveillance_labor, 2),
                "intervention_labor_hours": round(self._total_intervention_labor, 2),
            },
            "material_inventory": inventory_status,
            "cost_by_epoch": per_epoch,
            "itemized_entries": [e.to_dict() for e in self.entries],
        }


# ── Factory ──────────────────────────────────────────────────────────────

def build_ledger_from_config(config_path: str) -> CostLedger:
    """Construct a CostLedger from ``resource_costs.json``."""
    with open(config_path, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)

    budgets = cfg.get("budgets", {})
    starting_usd = budgets.get("financial_usd", {}).get("starting_balance", 50_000.0)
    starting_labor = budgets.get("labor_person_hours", {}).get("starting_capacity", 480.0)

    inv_cfg = cfg.get("material_inventory", {})
    starting_inv: dict[str, int] = {}
    unit_costs: dict[str, float] = {}
    for item_name, item_data in inv_cfg.items():
        starting_inv[item_name] = item_data.get("starting_count", 0)
        unit_costs[item_name] = item_data.get("unit_cost_usd", 0.0)

    return CostLedger(
        starting_financial_usd=starting_usd,
        starting_labor_hours=starting_labor,
        starting_inventory=starting_inv,
        material_unit_costs=unit_costs,
    )


def load_resource_costs(config_path: str) -> dict[str, Any]:
    """Load the raw resource costs config."""
    with open(config_path, "r", encoding="utf-8") as fh:
        return json.load(fh)
