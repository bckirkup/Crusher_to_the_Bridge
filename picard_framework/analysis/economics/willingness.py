"""Would a port rationally pay in, and up to what?

The decision rule is deliberately the weakest one that still answers the
question: a payer is willing to contribute while its share of the benefit
exceeds its share of the cost, so its break-even contribution is the monetary
equivalent of the benefit it receives.  Everything below that is a positive
net position; anything above it is a subsidy of another party.

Because the labour conversion rate is an unanchored input, a single answer
would be an artefact of whichever rate was picked.  The deliverable is
therefore the position *and* its sensitivity to that rate, in the same shape
the shore module reports its ``R_shore`` surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping, Sequence

from picard_framework.analysis.economics.benefit import (
    DEFAULT_COMMUNITY_WEIGHTS,
    PAYER_COMMUNITIES,
    BenefitSplit,
    payer_benefit_usd,
)
from picard_framework.analysis.economics.contributions import (
    MEDIUM_LABOUR_HOURS,
    PAYERS,
    ContributionLedger,
    ContributionRates,
)


@dataclass(frozen=True)
class PayerPosition:
    """One payer's cost, benefit, and break-even contribution."""

    payer: str
    community: str
    cost_usd: float
    benefit_usd: float
    cost_share: float
    benefit_share: float

    @property
    def net_usd(self) -> float:
        """Return benefit minus cost for this payer."""
        return float(self.benefit_usd - self.cost_usd)

    @property
    def break_even_cost_usd(self) -> float:
        """Return the largest contribution this payer would still accept."""
        return float(self.benefit_usd)

    @property
    def headroom_usd(self) -> float:
        """Return how much more this payer could pay and stay net-positive."""
        return max(0.0, self.net_usd)

    @property
    def rational_to_contribute(self) -> bool:
        """Whether this payer's benefit at least covers its own cost."""
        return self.benefit_usd >= self.cost_usd

    @property
    def benefit_to_cost_ratio(self) -> float | None:
        """Return benefit per unit cost, or ``None`` for a payer paying nothing.

        A payer contributing nothing has no ratio: every non-zero benefit
        would report an infinite one, which reads as a result and is not.
        """
        if abs(self.cost_usd) < 1e-15:
            return None
        return float(self.benefit_usd / self.cost_usd)

    def break_even_labour_hours(self, rates: ContributionRates) -> float | None:
        """Return the break-even contribution expressed as labour hours.

        This is the in-kind form of the same threshold, and it is undefined
        when labour has no declared monetary equivalent.
        """
        per_hour = rates.usd_per_unit(MEDIUM_LABOUR_HOURS)
        if per_hour <= 0.0:
            return None
        return float(self.break_even_cost_usd / per_hour)

    def to_dict(self, rates: ContributionRates) -> dict[str, Any]:
        """Flatten this position for tabular reporting."""
        return {
            "payer": self.payer,
            "community": self.community,
            "cost_usd": self.cost_usd,
            "benefit_usd": self.benefit_usd,
            "cost_share": self.cost_share,
            "benefit_share": self.benefit_share,
            "net_usd": self.net_usd,
            "break_even_cost_usd": self.break_even_cost_usd,
            "break_even_labour_hours": self.break_even_labour_hours(rates),
            "benefit_to_cost_ratio": self.benefit_to_cost_ratio,
            "rational_to_contribute": self.rational_to_contribute,
        }


def _shares(values: Mapping[str, float]) -> Mapping[str, float]:
    """Normalise payer values into shares, or zeros if there is nothing to share."""
    total = float(sum(values.values()))
    if total <= 0.0:
        return dict.fromkeys(PAYERS, 0.0)
    return {payer: float(value / total) for payer, value in values.items()}


def evaluate_payers(
    ledger: ContributionLedger,
    rates: ContributionRates,
    split: BenefitSplit,
    weights: Mapping[str, float] = DEFAULT_COMMUNITY_WEIGHTS,
) -> tuple[PayerPosition, ...]:
    """Return every payer's position under one valuation and one rate set."""
    costs = ledger.by_payer_usd(rates)
    benefits = payer_benefit_usd(split, weights)
    cost_shares = ledger.cost_shares(rates)
    benefit_shares = _shares(benefits)
    return tuple(
        PayerPosition(
            payer=payer,
            community=PAYER_COMMUNITIES[payer],
            cost_usd=float(costs[payer]),
            benefit_usd=float(benefits[payer]),
            cost_share=float(cost_shares[payer]),
            benefit_share=float(benefit_shares[payer]),
        )
        for payer in PAYERS
    )


def labour_rate_sensitivity(
    ledger: ContributionLedger,
    rates: ContributionRates,
    split: BenefitSplit,
    usd_per_labour_hour_grid: Sequence[float],
    weights: Mapping[str, float] = DEFAULT_COMMUNITY_WEIGHTS,
) -> tuple[dict[str, Any], ...]:
    """Re-evaluate every payer across the labour-rate grid.

    Only the conversion rate moves: the same contributions and the same
    benefit split are re-priced, so any change in a payer's position is
    attributable to the rate rather than to a different scenario.
    """
    grid = tuple(float(value) for value in usd_per_labour_hour_grid)
    if not grid:
        raise ValueError("usd_per_labour_hour_grid must be non-empty")
    if any(not isfinite(value) or value < 0.0 for value in grid):
        raise ValueError("usd_per_labour_hour_grid must be finite and non-negative")
    rows: list[dict[str, Any]] = []
    for rate_value in grid:
        priced = ContributionRates(
            usd_per_labour_hour=rate_value,
            usd_per_consumable_unit=rates.usd_per_consumable_unit,
            consumable_unit_costs=rates.consumable_unit_costs,
        )
        for position in evaluate_payers(ledger, priced, split, weights):
            row = position.to_dict(priced)
            row["usd_per_labour_hour"] = rate_value
            row["in_kind_fraction"] = ledger.in_kind_fraction(priced)
            rows.append(row)
    return tuple(rows)
