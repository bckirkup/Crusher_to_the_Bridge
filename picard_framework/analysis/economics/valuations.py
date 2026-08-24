"""Named valuations and conversion rates, with their provenance attached.

None of these numbers are simulation outputs, and one of them (the labour
conversion rate) is the axis the willingness-to-pay answer is most sensitive
to.  They are therefore declared once, in one place, with a source string that
says plainly whether the value is anchored, a cited range with an author's
selection inside it, or an unanchored placeholder that exists only to be swept.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from picard_framework.analysis.economics.benefit import BenefitValuation
from picard_framework.analysis.economics.contributions import ContributionRates

_AFLOAT_CASE_SOURCE = (
    "Unanchored placeholder for the operator's cost of one shipboard case "
    "(medical care, isolation, itinerary and compensation effects). Cruise "
    "outbreak cost-per-case figures are not publicly itemised, so this value "
    "exists to be swept and no absolute dollar claim should rest on it."
)
_SHORE_CASE_SOURCE = (
    "Unanchored placeholder for the shore cost of one community norovirus "
    "case (productivity loss plus outpatient care). Published cost-of-illness "
    "estimates vary by an order of magnitude across settings and health "
    "systems, so the reportable quantity is the shore:afloat ratio and its "
    "sensitivity, not the level."
)
_OIS_SOURCE = (
    "Operational Impact Score is deliberately non-financial "
    "(crusher_labs/cost_ledger.py); it has no exchange rate to dollars. It "
    "defaults to zero here so that OIS is reported in its own units unless a "
    "caller supplies an explicit, defensible conversion."
)
_SYMPTOMATIC_HOUR_SOURCE = (
    "Zero by default: symptomatic person-hours already drive the case and OIS "
    "terms, and pricing them again would double-count the same illness."
)
_LABOUR_SOURCE = (
    "Unanchored: the monetary equivalent of one seconded port-health "
    "person-hour is a local labour-market quantity spanning roughly an order "
    "of magnitude across the itineraries CTB models. The central value is a "
    "round placeholder and the grid, not the point, is the deliverable."
)

VALUATION_PROVENANCE: Mapping[str, str] = MappingProxyType({
    "usd_per_case_afloat": _AFLOAT_CASE_SOURCE,
    "usd_per_case_ashore": _SHORE_CASE_SOURCE,
    "usd_per_operational_impact_point": _OIS_SOURCE,
    "usd_per_symptomatic_person_hour": _SYMPTOMATIC_HOUR_SOURCE,
})

LABOUR_RATE_SOURCE = _LABOUR_SOURCE

#: Equal per-case valuation ashore and afloat.  Under it the monetised
#: shore:afloat ratio equals the ratio in cases averted, which makes it the
#: reference arm for separating a valuation effect from a modelling one.
UNIT_VALUATION = BenefitValuation(
    usd_per_case_afloat=1.0,
    usd_per_case_ashore=1.0,
    provenance=VALUATION_PROVENANCE,
)

#: Placeholder central valuation.  Absolute dollar outputs computed with it
#: are not reportable claims; ratios and break-even thresholds are.
PLACEHOLDER_VALUATION = BenefitValuation(
    usd_per_case_afloat=1_200.0,
    usd_per_case_ashore=600.0,
    provenance=VALUATION_PROVENANCE,
)

#: Central labour conversion rate, in USD per person-hour.
PLACEHOLDER_USD_PER_LABOUR_HOUR = 45.0

#: Grid spanning roughly an order of magnitude around the central rate.
LABOUR_RATE_GRID: tuple[float, ...] = (10.0, 20.0, 45.0, 80.0, 120.0)

PLACEHOLDER_RATES = ContributionRates(
    usd_per_labour_hour=PLACEHOLDER_USD_PER_LABOUR_HOUR,
)
