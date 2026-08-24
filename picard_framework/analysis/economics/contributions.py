"""Who pays for shipboard surveillance, in what medium, and at what rate.

A port that seconds two environmental-health officers to a berthed ship has
contributed as surely as one that wires cash, and the paper's question is
whether ports would rationally do either.  So a contribution carries a payer,
a medium, a quantity in that medium's own unit, and a conversion rate to a
monetary equivalent that is an explicit, reportable input rather than a
constant buried in the arithmetic: a labour hour is worth what the local labour
market says it is worth, and that number moves the answer.

The output is net cost *per payer*.  A single total would answer a question
nobody is asking, since the whole point is that the payer bearing the cost and
the community receiving the benefit need not be the same party.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from types import MappingProxyType
from typing import Iterable, Mapping

PAYER_SHIP_OPERATOR = "ship_operator"
PAYER_PORT_AUTHORITY = "port_authority"
PAYER_PUBLIC_HEALTH_AGENCY = "public_health_agency"
PAYERS = (
    PAYER_SHIP_OPERATOR,
    PAYER_PORT_AUTHORITY,
    PAYER_PUBLIC_HEALTH_AGENCY,
)

MEDIUM_CASH = "cash"
MEDIUM_LABOUR_HOURS = "labour_hours"
MEDIUM_CONSUMABLES = "consumables"
MEDIA = (MEDIUM_CASH, MEDIUM_LABOUR_HOURS, MEDIUM_CONSUMABLES)


def _require_finite(name: str, value: float) -> float:
    """Validate one finite scalar."""
    number = float(value)
    if not isfinite(number):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return number


def _require_non_negative(name: str, value: float) -> float:
    """Validate one finite, non-negative scalar."""
    number = _require_finite(name, value)
    if number < 0.0:
        raise ValueError(f"{name} must be non-negative, got {value!r}")
    return number


@dataclass(frozen=True)
class ContributionRates:
    """Monetary equivalents for the non-cash contribution media.

    ``usd_per_consumable_unit`` is a fallback for consumables whose per-item
    cost the caller does not supply; ``consumable_unit_costs`` overrides it per
    item so the existing ``resource_costs.json`` unit costs can be used
    directly rather than re-declared.
    """

    usd_per_labour_hour: float
    usd_per_consumable_unit: float = 0.0
    consumable_unit_costs: Mapping[str, float] = field(
        default_factory=lambda: MappingProxyType({})
    )

    def __post_init__(self) -> None:
        _require_non_negative("usd_per_labour_hour", self.usd_per_labour_hour)
        _require_non_negative(
            "usd_per_consumable_unit", self.usd_per_consumable_unit,
        )
        costs = {
            str(item): _require_non_negative(f"consumable_unit_costs[{item}]", cost)
            for item, cost in self.consumable_unit_costs.items()
        }
        if any(not item for item in costs):
            raise ValueError("consumable item names must be non-empty")
        object.__setattr__(self, "consumable_unit_costs", MappingProxyType(costs))

    def usd_per_unit(self, medium: str, item: str | None = None) -> float:
        """Return the monetary equivalent of one unit of ``medium``."""
        if medium == MEDIUM_CASH:
            return 1.0
        if medium == MEDIUM_LABOUR_HOURS:
            return float(self.usd_per_labour_hour)
        if medium == MEDIUM_CONSUMABLES:
            if item is None:
                return float(self.usd_per_consumable_unit)
            return float(
                self.consumable_unit_costs.get(item, self.usd_per_consumable_unit)
            )
        raise ValueError(f"unknown medium {medium!r}")


@dataclass(frozen=True)
class Contribution:
    """One payer's contribution of one medium towards surveillance.

    ``quantity`` is in the medium's own unit: USD for cash, person-hours for
    labour, item counts for consumables.  ``item`` names the consumable so a
    per-item unit cost can be applied; it is meaningless for other media and
    must be omitted there.
    """

    payer: str
    medium: str
    quantity: float
    item: str | None = None
    description: str = ""

    def __post_init__(self) -> None:
        if self.payer not in PAYERS:
            raise ValueError(f"unknown payer {self.payer!r}, expected one of {PAYERS}")
        if self.medium not in MEDIA:
            raise ValueError(f"unknown medium {self.medium!r}, expected one of {MEDIA}")
        if self.item is not None:
            if self.medium != MEDIUM_CONSUMABLES:
                raise ValueError("item is only meaningful for consumables")
            if not str(self.item).strip():
                raise ValueError("item must be non-empty when supplied")
        _require_non_negative("quantity", self.quantity)

    def monetary_equivalent(self, rates: ContributionRates) -> float:
        """Convert this contribution to its monetary equivalent."""
        return float(self.quantity) * rates.usd_per_unit(self.medium, self.item)


@dataclass(frozen=True)
class ContributionLedger:
    """Every contribution to one scenario's surveillance capability."""

    contributions: tuple[Contribution, ...] = ()

    @classmethod
    def of(cls, contributions: Iterable[Contribution]) -> ContributionLedger:
        """Build a ledger from any iterable of contributions."""
        return cls(tuple(contributions))

    def total_usd(self, rates: ContributionRates) -> float:
        """Return the monetary-equivalent total across all payers."""
        return float(
            sum(item.monetary_equivalent(rates) for item in self.contributions)
        )

    def by_payer_usd(self, rates: ContributionRates) -> Mapping[str, float]:
        """Return the monetary-equivalent cost borne by each payer.

        Every payer appears, including those contributing nothing, so a share
        of zero is reported rather than silently absent.
        """
        totals = dict.fromkeys(PAYERS, 0.0)
        for item in self.contributions:
            totals[item.payer] += item.monetary_equivalent(rates)
        return MappingProxyType(totals)

    def by_medium_usd(self, rates: ContributionRates) -> Mapping[str, float]:
        """Return the monetary-equivalent cost supplied through each medium."""
        totals = dict.fromkeys(MEDIA, 0.0)
        for item in self.contributions:
            totals[item.medium] += item.monetary_equivalent(rates)
        return MappingProxyType(totals)

    def in_kind_fraction(self, rates: ContributionRates) -> float:
        """Return the non-cash share of the monetary-equivalent total.

        A ledger with no monetary equivalent at all has no meaningful in-kind
        share, and reports zero rather than dividing by zero.
        """
        total = self.total_usd(rates)
        if total <= 0.0:
            return 0.0
        cash = self.by_medium_usd(rates)[MEDIUM_CASH]
        return float((total - cash) / total)

    def cost_shares(self, rates: ContributionRates) -> Mapping[str, float]:
        """Return each payer's share of the monetary-equivalent total.

        With no cost to share, every share is zero: normalising nothing would
        otherwise invent a distribution.
        """
        totals = self.by_payer_usd(rates)
        total = self.total_usd(rates)
        if total <= 0.0:
            return MappingProxyType(dict.fromkeys(PAYERS, 0.0))
        return MappingProxyType(
            {payer: float(value / total) for payer, value in totals.items()}
        )
