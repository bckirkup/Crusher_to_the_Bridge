"""Turn a simulated cost ledger into attributed contributions.

``crusher_labs/cost_ledger.py`` already prices surveillance in three units —
dollars, person-hours, and consumed items — but it records only *what* was
spent, never *who* paid.  This bridge adds the payer, which is the whole
question the economics layer exists to answer, and it does so as an explicit
attribution map rather than a default buried in the arithmetic: a port that
staffs a berth-side sampling team is paying for the same line the operator
would otherwise have paid in cash.

Only surveillance lines are read.  Intervention spend is a consequence of an
outbreak rather than a price of watching for one, and pooling the two would
make the capability look more expensive the worse it performed.
"""

from __future__ import annotations

from typing import Any, Mapping

from picard_framework.analysis.economics.contributions import (
    MEDIUM_CASH,
    MEDIUM_CONSUMABLES,
    MEDIUM_LABOUR_HOURS,
    PAYER_SHIP_OPERATOR,
    PAYERS,
    Contribution,
    ContributionLedger,
)

_MEDIA_KEYS = (MEDIUM_CASH, MEDIUM_LABOUR_HOURS, MEDIUM_CONSUMABLES)


def _validate_attribution(
    attribution: Mapping[str, str] | None,
) -> Mapping[str, str]:
    """Validate a medium-to-payer attribution map, defaulting to the operator."""
    records = dict.fromkeys(_MEDIA_KEYS, PAYER_SHIP_OPERATOR)
    for medium, payer in (attribution or {}).items():
        if medium not in _MEDIA_KEYS:
            raise ValueError(f"unknown medium {medium!r}")
        if payer not in PAYERS:
            raise ValueError(f"unknown payer {payer!r}")
        records[medium] = payer
    return records


def _surveillance_totals(audit: Mapping[str, Any]) -> tuple[float, float]:
    """Read surveillance cash and labour out of a FINANCIAL_AUDIT block."""
    summary = audit.get("summary", {})
    return (
        float(summary.get("surveillance_cost_usd", 0.0)),
        float(summary.get("surveillance_labor_hours", 0.0)),
    )


def _surveillance_materials(audit: Mapping[str, Any]) -> dict[str, int]:
    """Sum consumables charged to surveillance entries, by item.

    The audit summary reports no per-category material split, so the itemised
    entries are the only faithful source; a run whose entries were not
    retained simply contributes no consumable lines.
    """
    materials: dict[str, int] = {}
    for entry in audit.get("itemized_entries", []):
        if entry.get("category") != "surveillance":
            continue
        for item, quantity in (entry.get("materials") or {}).items():
            materials[str(item)] = materials.get(str(item), 0) + int(quantity)
    return materials


def contributions_from_financial_audit(
    audit: Mapping[str, Any],
    *,
    attribution: Mapping[str, str] | None = None,
    label: str = "shipboard surveillance",
) -> ContributionLedger:
    """Build a contribution ledger from one run's ``FINANCIAL_AUDIT`` block.

    ``attribution`` maps each medium to the payer bearing it, so the same
    simulated capability can be re-costed under different funding
    arrangements without re-running the simulation.  Zero-valued lines are
    dropped rather than recorded as empty contributions.
    """
    payers = _validate_attribution(attribution)
    cash, labour = _surveillance_totals(audit)
    lines: list[Contribution] = []
    if cash > 0.0:
        lines.append(Contribution(
            payer=payers[MEDIUM_CASH],
            medium=MEDIUM_CASH,
            quantity=cash,
            description=f"{label}: financial spend",
        ))
    if labour > 0.0:
        lines.append(Contribution(
            payer=payers[MEDIUM_LABOUR_HOURS],
            medium=MEDIUM_LABOUR_HOURS,
            quantity=labour,
            description=f"{label}: crew person-hours",
        ))
    for item, quantity in sorted(_surveillance_materials(audit).items()):
        if quantity <= 0:
            continue
        lines.append(Contribution(
            payer=payers[MEDIUM_CONSUMABLES],
            medium=MEDIUM_CONSUMABLES,
            quantity=float(quantity),
            item=item,
            description=f"{label}: {item}",
        ))
    return ContributionLedger.of(lines)
