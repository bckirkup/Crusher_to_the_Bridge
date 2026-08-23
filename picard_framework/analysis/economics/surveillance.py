"""Deterministic cost and two-community benefit post-processing.

This layer does not simulate transmission or value a case in dollars.  It
consumes ship/shore outputs, contribution quantities, and explicit scenario
assumptions to report per-payer cost shares and the shore-versus-afloat share
of signed benefit.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from crusher_labs.cost_ledger import (
    CATEGORY_SURVEILLANCE,
    CONTRIBUTION_MEDIA,
    CONTRIBUTION_PAYERS,
    ContributionRecord,
    CostLedger,
)
from picard_framework.analysis.shore.counterfactual import CounterfactualResult
from simulation_utils.paths import resolve_repo_path, validated_open

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
COMMUNITIES = ("afloat", "shore")


def _finite_nonnegative(value: float, label: str) -> float:
    """Validate a non-negative finite numeric assumption."""
    numeric = float(value)
    if not isfinite(numeric) or numeric < 0.0:
        raise ValueError(f"{label} must be finite and non-negative")
    return numeric


@dataclass(frozen=True)
class CostAllocation:
    """One payer's medium-denominated contribution per voyage."""

    payer: str
    medium: str
    quantity_per_voyage: float
    provenance: str = ""

    def __post_init__(self) -> None:
        if self.payer not in CONTRIBUTION_PAYERS:
            raise ValueError(f"unknown contribution payer: {self.payer}")
        if self.medium not in CONTRIBUTION_MEDIA:
            raise ValueError(f"unknown contribution medium: {self.medium}")
        _finite_nonnegative(self.quantity_per_voyage, "allocation quantity")
        if not self.provenance:
            raise ValueError("allocation provenance is required")

    def as_contribution(
        self,
        *,
        epoch: int,
        labour_conversion_rate: float,
        consumables_conversion_rate: float,
    ) -> ContributionRecord:
        """Convert this medium quantity to a ledger attribution record."""
        rates = {
            "cash": 1.0,
            "labour_hours": labour_conversion_rate,
            "consumables": consumables_conversion_rate,
        }
        return ContributionRecord(
            epoch=epoch,
            payer=self.payer,
            medium=self.medium,
            quantity=self.quantity_per_voyage,
            conversion_rate_usd_per_unit=rates[self.medium],
            category=CATEGORY_SURVEILLANCE,
            source="surveillance_scenario",
            description=self.provenance,
        )


@dataclass(frozen=True)
class SurveillanceScenario:
    """Named §4 scenario with explicit amortisation and allocation inputs."""

    scenario_id: str
    label: str
    onboard_capability: str
    ashore_capability: str
    ships_covered: int
    annual_cost_usd: float
    voyages_per_year: float
    voyages_per_year_sweep: tuple[float, ...]
    allocations: tuple[CostAllocation, ...]
    provenance: Mapping[str, str]
    scope_note: str

    def __post_init__(self) -> None:
        if self.ships_covered < 1:
            raise ValueError("ships_covered must be >= 1")
        _finite_nonnegative(self.annual_cost_usd, "annual cost")
        if self.voyages_per_year <= 0.0:
            raise ValueError("voyages_per_year must be positive")
        sweep = tuple(_finite_nonnegative(v, "voyages per year sweep") for v in self.voyages_per_year_sweep)
        if not sweep or any(v <= 0.0 for v in sweep):
            raise ValueError("voyages_per_year_sweep must contain positive values")
        if not self.allocations:
            raise ValueError("at least one cost allocation is required")
        if not self.scope_note:
            raise ValueError("scope_note is required")
        required_provenance = {
            "ships_covered",
            "annual_cost_usd",
            "voyages_per_year",
            "voyages_per_year_sweep",
            "allocation_quantities_per_voyage",
        }
        if not required_provenance.issubset(self.provenance):
            raise ValueError("provenance is missing one or more numeric fields")

    @property
    def per_voyage_programme_cost_usd(self) -> float:
        """Return annual cost amortised over ships and voyages."""
        return self.annual_cost_usd / self.ships_covered / self.voyages_per_year


def _scenario_from_dict(raw: Mapping[str, Any]) -> SurveillanceScenario:
    """Build an immutable scenario from one validated JSON object."""
    allocations = tuple(
        CostAllocation(
            payer=item["payer"],
            medium=item["medium"],
            quantity_per_voyage=item["quantity_per_voyage"],
            provenance=item["provenance"],
        )
        for item in raw["allocations"]
    )
    return SurveillanceScenario(
        scenario_id=raw["scenario_id"],
        label=raw["label"],
        onboard_capability=raw["onboard_capability"],
        ashore_capability=raw["ashore_capability"],
        ships_covered=raw["ships_covered"],
        annual_cost_usd=raw["annual_cost_usd"],
        voyages_per_year=raw["voyages_per_year"],
        voyages_per_year_sweep=tuple(raw["voyages_per_year_sweep"]),
        allocations=allocations,
        provenance=MappingProxyType(dict(raw["provenance"])),
        scope_note=raw["scope_note"],
    )


def _load_json(path: str) -> dict[str, Any]:
    """Load an economics JSON file confined to the repository."""
    with validated_open(path, "r", allowed_roots=(REPO_ROOT,), encoding="utf-8") as fh:
        return json.load(fh)


def load_surveillance_scenarios(path: str) -> dict[str, SurveillanceScenario]:
    """Load all named surveillance scenarios keyed by scenario ID."""
    raw = _load_json(path)
    scenarios = {
        scenario.scenario_id: scenario
        for scenario in (_scenario_from_dict(item) for item in raw["scenarios"])
    }
    if len(scenarios) != len(raw["scenarios"]):
        raise ValueError("duplicate surveillance scenario ID")
    return scenarios


def load_surveillance_scenario(path: str, scenario_id: str) -> SurveillanceScenario:
    """Load one named scenario, raising for an unknown ID."""
    scenarios = load_surveillance_scenarios(path)
    try:
        return scenarios[scenario_id]
    except KeyError as exc:
        raise ValueError(f"unknown surveillance scenario: {scenario_id}") from exc


def load_scenario_from_fleet_config(
    fleet_config_path: str,
    *,
    repo_root: str = REPO_ROOT,
) -> SurveillanceScenario:
    """Resolve and load a scenario referenced by a Presidio fleet config."""
    fleet_path = resolve_repo_path(repo_root, fleet_config_path)
    raw = _load_json(fleet_path)
    catalog = raw.get("catalog", {})
    scenario_path = resolve_repo_path(
        repo_root,
        catalog["surveillance_economics_id"],
    )
    return load_surveillance_scenario(
        scenario_path,
        catalog["surveillance_scenario_id"],
    )


def cost_shares_for_scenario(
    scenario: SurveillanceScenario,
    *,
    labour_conversion_rate: float,
    consumables_conversion_rate: float,
) -> dict[str, dict[str, Any]]:
    """Attribute one representative voyage's allocation by payer."""
    ledger = CostLedger()
    for allocation in scenario.allocations:
        ledger.record_contribution(
            allocation.as_contribution(
                epoch=0,
                labour_conversion_rate=labour_conversion_rate,
                consumables_conversion_rate=consumables_conversion_rate,
            ),
        )
    return ledger.contribution_summary()


@dataclass(frozen=True)
class BenefitSplit:
    """Signed shore and afloat cases averted and their benefit shares."""

    shore_cases_averted: float
    afloat_cases_averted: float

    @classmethod
    def from_counterfactuals(
        cls,
        counterfactuals: Iterable[CounterfactualResult],
        *,
        afloat_cases_averted: float,
    ) -> BenefitSplit:
        """Build shore benefit by summing 11b counterfactual benefits."""
        shore = sum(float(result.benefit) for result in counterfactuals)
        return cls(shore_cases_averted=shore, afloat_cases_averted=afloat_cases_averted)

    @property
    def shore_afloat_ratio(self) -> float | None:
        """Return shore divided by afloat, or ``None`` for a non-positive denominator."""
        if self.afloat_cases_averted <= 0.0:
            return None
        return self.shore_cases_averted / self.afloat_cases_averted

    @property
    def total_cases_averted(self) -> float:
        """Return signed total cases averted across both communities."""
        return self.shore_cases_averted + self.afloat_cases_averted

    @property
    def shore_benefit_share(self) -> float | None:
        """Return shore's share when total benefit is positive."""
        total = self.total_cases_averted
        return None if total <= 0.0 else self.shore_cases_averted / total

    @property
    def afloat_benefit_share(self) -> float | None:
        """Return afloat's share when total benefit is positive."""
        total = self.total_cases_averted
        return None if total <= 0.0 else self.afloat_cases_averted / total


def _share_value(value: Any) -> float:
    """Read a share from a ledger report or an explicitly supplied scalar."""
    if isinstance(value, Mapping):
        if "share_of_total" not in value:
            raise ValueError("payer report must include share_of_total")
        return float(value["share_of_total"])
    if isinstance(value, (int, float)):
        return float(value)
    raise TypeError("payer cost must be a scalar share or ledger report")


def _validate_community_map(
    payer_community_map: Mapping[str, str],
    per_payer_costs: Mapping[str, Any],
    port_community: str,
) -> None:
    """Ensure all payer costs map to a known community."""
    expected = set(CONTRIBUTION_PAYERS)
    actual = set(payer_community_map)
    if actual != expected:
        raise ValueError("payer community map must cover exactly every payer")
    if any(community not in COMMUNITIES for community in payer_community_map.values()):
        raise ValueError("unknown payer community")
    if port_community not in COMMUNITIES:
        raise ValueError(f"unknown port community: {port_community}")
    if set(per_payer_costs) != expected:
        raise ValueError("per-payer costs must cover exactly every payer")


@dataclass(frozen=True)
class WillingnessToPayResult:
    """One port-community benefit-versus-cost share comparison."""

    benefit_share: float
    cost_share: float
    signed_difference: float
    pays_own_way: bool


def willingness_to_pay(
    per_payer_costs: Mapping[str, Any],
    payer_community_map: Mapping[str, str],
    benefit_split: BenefitSplit,
    *,
    port_community: str = "shore",
) -> WillingnessToPayResult:
    """Compare the port community's benefit share with its cost share."""
    _validate_community_map(payer_community_map, per_payer_costs, port_community)
    benefit_share = (
        benefit_split.shore_benefit_share
        if port_community == "shore"
        else benefit_split.afloat_benefit_share
    )
    if benefit_share is None:
        raise ValueError("benefit shares are unavailable when total benefit is non-positive")
    port_cost_share = sum(
        _share_value(per_payer_costs[payer])
        for payer, community in payer_community_map.items()
        if community == port_community
    )
    difference = benefit_share - port_cost_share
    return WillingnessToPayResult(
        benefit_share=benefit_share,
        cost_share=port_cost_share,
        signed_difference=difference,
        pays_own_way=difference >= 0.0,
    )


@dataclass(frozen=True)
class WillingnessToPaySweep:
    """Grid results and a non-interpolated cost-share crossing bracket."""

    labour_conversion_rates: tuple[float, ...]
    results: tuple[WillingnessToPayResult, ...]
    crossing_bracketing_rates: tuple[float, float] | None
    cost_share_monotone: bool


def sweep_willingness_to_pay(
    scenario: SurveillanceScenario,
    payer_community_map: Mapping[str, str],
    benefit_split: BenefitSplit,
    labour_conversion_rates: Iterable[float],
    *,
    consumables_conversion_rate: float,
    port_community: str = "shore",
) -> WillingnessToPaySweep:
    """Sweep labour rates and report grid crossings without interpolation."""
    rates = tuple(float(rate) for rate in labour_conversion_rates)
    results = tuple(
        willingness_to_pay(
            cost_shares_for_scenario(
                scenario,
                labour_conversion_rate=rate,
                consumables_conversion_rate=consumables_conversion_rate,
            ),
            payer_community_map,
            benefit_split,
            port_community=port_community,
        )
        for rate in rates
    )
    crossing = None
    for previous_rate, rate, previous, current in zip(
        rates,
        rates[1:],
        results,
        results[1:],
    ):
        if previous.cost_share <= previous.benefit_share and current.cost_share > current.benefit_share:
            crossing = (previous_rate, rate)
            break
    monotone = all(
        current.cost_share >= previous.cost_share
        for previous, current in zip(results, results[1:])
    )
    return WillingnessToPaySweep(
        labour_conversion_rates=rates,
        results=results,
        crossing_bracketing_rates=crossing,
        cost_share_monotone=monotone,
    )
