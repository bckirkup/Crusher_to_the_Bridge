"""
cost_ledger.py – Comprehensive Cost-Accounting Ledger
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tracks four resource dimensions across a simulation run:

1. **Financial Spend** ($USD) — cumulative surveillance and intervention costs.
2. **Material Inventory** — item counts (masks, test kits, sanitizers, etc.).
3. **Labor Hours** — crew person-hours consumed per epoch.
4. **Operational Impact Score (OIS)** — cumulative operational degradation from
   confinement, zone closures, and fleet-wide interventions (tracker only).

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

    DEFAULT_OIS_WEIGHTS: dict[str, Any] = {
        "per_passenger_quarantined": 1.0,
        "per_essential_crew_quarantined": 3.0,
        "per_passenger_isolated": 0.5,
        "per_closed_galley_zone": 2.0,
        "per_fleet_ppe_active": 0.1,
        "essential_crew_classes": [
            "crew_medical",
            "crew_engineering",
            "crew_galley",
            "crew_general",
        ],
        "galley_zone_types": ["galley", "mess"],
    }

    def __init__(
        self,
        starting_financial_usd: float = 50_000.0,
        starting_labor_hours: float = 480.0,
        starting_inventory: dict[str, int] | None = None,
        material_unit_costs: dict[str, float] | None = None,
        ois_weights: dict[str, Any] | None = None,
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

        self.ois_weights: dict[str, Any] = dict(self.DEFAULT_OIS_WEIGHTS)
        if ois_weights:
            self.ois_weights.update(ois_weights)
        self._cumulative_ois: float = 0.0
        self._epoch_ois: dict[int, float] = {}
        self._epoch_ois_breakdown: dict[int, dict[str, float]] = {}

    # ── Operational impact (tracker only) ─────────────────────────────

    def accumulate_operational_impact(
        self,
        epoch: int,
        ois_delta: float,
        source: str = "operational_state",
        breakdown: dict[str, float] | None = None,
    ) -> None:
        """Record operational degradation for an epoch (never blocks actions)."""
        if ois_delta <= 0 and not breakdown:
            return
        delta = max(0.0, float(ois_delta))
        self._cumulative_ois += delta
        self._epoch_ois[epoch] = self._epoch_ois.get(epoch, 0.0) + delta
        if breakdown:
            existing = self._epoch_ois_breakdown.setdefault(epoch, {})
            for key, val in breakdown.items():
                existing[key] = existing.get(key, 0.0) + float(val)

    def get_epoch_operational_impact(self, epoch: int) -> float:
        return self._epoch_ois.get(epoch, 0.0)

    def get_operational_impact_breakdown(self, epoch: int) -> dict[str, float]:
        return dict(self._epoch_ois_breakdown.get(epoch, {}))

    @property
    def operational_impact_cumulative(self) -> float:
        return self._cumulative_ois

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
        materials: dict[str, int] = {}
        for e in epoch_entries:
            for item_name, qty in (e.materials or {}).items():
                materials[item_name] = materials.get(item_name, 0) + qty

        by_category: dict[str, dict[str, Any]] = {
            CATEGORY_SURVEILLANCE: {"financial_usd": 0.0, "labor_hours": 0.0, "materials": {}},
            CATEGORY_INTERVENTION: {"financial_usd": 0.0, "labor_hours": 0.0, "materials": {}},
        }
        for e in epoch_entries:
            cat = CATEGORY_SURVEILLANCE if e.category == CATEGORY_SURVEILLANCE else CATEGORY_INTERVENTION
            by_category[cat]["financial_usd"] += e.financial_usd
            by_category[cat]["labor_hours"] += e.labor_hours
            mats = by_category[cat]["materials"]
            for item_name, qty in (e.materials or {}).items():
                mats[item_name] = mats.get(item_name, 0) + qty

        return {
            "epoch": epoch,
            "entries_count": len(epoch_entries),
            "total_financial_usd": round(total_usd, 2),
            "total_labor_hours": round(total_labor, 2),
            "materials_consumed": materials,
            "by_category": {
                CATEGORY_SURVEILLANCE: {
                    "financial_usd": round(by_category[CATEGORY_SURVEILLANCE]["financial_usd"], 2),
                    "labor_hours": round(by_category[CATEGORY_SURVEILLANCE]["labor_hours"], 2),
                    "materials": by_category[CATEGORY_SURVEILLANCE]["materials"],
                },
                CATEGORY_INTERVENTION: {
                    "financial_usd": round(by_category[CATEGORY_INTERVENTION]["financial_usd"], 2),
                    "labor_hours": round(by_category[CATEGORY_INTERVENTION]["labor_hours"], 2),
                    "materials": by_category[CATEGORY_INTERVENTION]["materials"],
                },
            },
            "financial_balance_remaining": round(self.financial_balance, 2),
            "labor_hours_remaining": round(self.labor_remaining, 2),
            "operational_impact_epoch": round(self.get_epoch_operational_impact(epoch), 3),
            "operational_impact_cumulative": round(self._cumulative_ois, 3),
            "operational_impact_breakdown": {
                k: round(v, 3)
                for k, v in self.get_operational_impact_breakdown(epoch).items()
            },
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
                "total_operational_impact_score": round(self._cumulative_ois, 3),
            },
            "material_inventory": inventory_status,
            "cost_by_epoch": per_epoch,
            "itemized_entries": [e.to_dict() for e in self.entries],
        }


# ── Operational impact computation ───────────────────────────────────────

def compute_operational_impact(
    agents: list[dict[str, Any]],
    quarantined_ids: set[int],
    isolated_ids: set[int],
    merged_modifiers: dict[str, Any],
    active_protocol_ids: list[str],
    ois_weights: dict[str, Any],
    zone_type_by_id: dict[str, str] | None = None,
) -> tuple[float, dict[str, float]]:
    """Compute epoch OIS delta and component breakdown from simulation state."""
    weights = {**CostLedger.DEFAULT_OIS_WEIGHTS, **(ois_weights or {})}
    essential_classes = set(weights.get("essential_crew_classes", []))
    galley_types = {t.lower() for t in weights.get("galley_zone_types", [])}
    zone_types = zone_type_by_id or {}

    breakdown: dict[str, float] = {}
    quarantined_set = set(quarantined_ids)
    isolated_set = set(isolated_ids)

    passenger_q = 0
    essential_q = 0
    passenger_iso = 0
    for agent in agents:
        aid = agent["agent_id"]
        agent_class = agent.get("agent_class", agent.get("role", ""))
        if aid in quarantined_set:
            if agent_class in essential_classes:
                essential_q += 1
            elif agent.get("role") == "passenger" or str(agent_class).startswith("passenger"):
                passenger_q += 1
        if aid in isolated_set:
            if agent.get("role") == "passenger" or str(agent_class).startswith("passenger"):
                passenger_iso += 1

    w_pq = float(weights.get("per_passenger_quarantined", 1.0))
    w_ec = float(weights.get("per_essential_crew_quarantined", 3.0))
    w_pi = float(weights.get("per_passenger_isolated", 0.5))
    if passenger_q:
        breakdown["passenger_quarantine"] = passenger_q * w_pq
    if essential_q:
        breakdown["essential_crew_quarantine"] = essential_q * w_ec
    if passenger_iso:
        breakdown["passenger_isolation"] = passenger_iso * w_pi

    closed = merged_modifiers.get("close_zones", [])
    galley_closed = 0
    for zone_id in closed:
        ztype = zone_types.get(zone_id, "").lower()
        if ztype in galley_types:
            galley_closed += 1
    w_galley = float(weights.get("per_closed_galley_zone", 2.0))
    if galley_closed:
        breakdown["closed_galley_zones"] = galley_closed * w_galley

    ppe_reduction = float(merged_modifiers.get("ppe_transmission_reduction", 0.0))
    w_ppe = float(weights.get("per_fleet_ppe_active", 0.1))
    if ppe_reduction > 0.0 or "SOP-004" in active_protocol_ids:
        breakdown["fleet_ppe"] = w_ppe

    total = sum(breakdown.values())
    return total, breakdown


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

    ois_weights = cfg.get("operational_impact_weights")

    return CostLedger(
        starting_financial_usd=starting_usd,
        starting_labor_hours=starting_labor,
        starting_inventory=starting_inv,
        material_unit_costs=unit_costs,
        ois_weights=ois_weights,
    )


def load_resource_costs(config_path: str) -> dict[str, Any]:
    """Load the raw resource costs config."""
    with open(config_path, "r", encoding="utf-8") as fh:
        return json.load(fh)
