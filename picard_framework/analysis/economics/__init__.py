"""Surveillance economics: who pays, who benefits, and would a port pay in.

The layer is deliberately downstream of the simulation and free of it.  The
ABM prices surveillance in dollars, person-hours, and consumables; the shore
renewal layer converts earlier shipboard detection into shore cases averted.
This package attributes the cost to payers, splits the benefit between the
afloat and shore communities, and reports each payer's break-even
contribution — in cash and in the labour hours that could be given instead.
"""

from __future__ import annotations

from picard_framework.analysis.economics.benefit import (
    COMMUNITIES,
    COMMUNITY_AFLOAT,
    COMMUNITY_SHORE,
    DEFAULT_COMMUNITY_WEIGHTS,
    PAYER_COMMUNITIES,
    AfloatBenefit,
    BenefitSplit,
    BenefitValuation,
    ShoreBenefit,
    benefit_split,
    payer_benefit_usd,
)
from picard_framework.analysis.economics.contributions import (
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
from picard_framework.analysis.economics.ledger_bridge import (
    contributions_from_financial_audit,
)
from picard_framework.analysis.economics.valuations import (
    LABOUR_RATE_GRID,
    LABOUR_RATE_SOURCE,
    PLACEHOLDER_RATES,
    PLACEHOLDER_USD_PER_LABOUR_HOUR,
    PLACEHOLDER_VALUATION,
    UNIT_VALUATION,
    VALUATION_PROVENANCE,
)
from picard_framework.analysis.economics.willingness import (
    PayerPosition,
    evaluate_payers,
    labour_rate_sensitivity,
)

__all__ = [
    "COMMUNITIES",
    "COMMUNITY_AFLOAT",
    "COMMUNITY_SHORE",
    "DEFAULT_COMMUNITY_WEIGHTS",
    "LABOUR_RATE_GRID",
    "LABOUR_RATE_SOURCE",
    "MEDIA",
    "MEDIUM_CASH",
    "MEDIUM_CONSUMABLES",
    "MEDIUM_LABOUR_HOURS",
    "PAYERS",
    "PAYER_COMMUNITIES",
    "PAYER_PORT_AUTHORITY",
    "PAYER_PUBLIC_HEALTH_AGENCY",
    "PAYER_SHIP_OPERATOR",
    "PLACEHOLDER_RATES",
    "PLACEHOLDER_USD_PER_LABOUR_HOUR",
    "PLACEHOLDER_VALUATION",
    "UNIT_VALUATION",
    "VALUATION_PROVENANCE",
    "AfloatBenefit",
    "BenefitSplit",
    "BenefitValuation",
    "Contribution",
    "ContributionLedger",
    "ContributionRates",
    "PayerPosition",
    "ShoreBenefit",
    "benefit_split",
    "contributions_from_financial_audit",
    "evaluate_payers",
    "labour_rate_sensitivity",
    "payer_benefit_usd",
]
