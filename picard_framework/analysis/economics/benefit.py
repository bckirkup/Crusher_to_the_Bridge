"""Two communities, two benefit streams, and one ratio between them.

Afloat benefit comes from the ABM as a paired difference: the same voyage with
and without the surveillance capability being priced.  Shore benefit cannot
come from the ABM at all — CTB simulates the ship, and ports enter only as a
hazard prior — so it is required to arrive from the shore counterfactual in
``picard_framework/analysis/shore/``, which converts earlier shipboard
detection into shore cases averted.  Nothing here invents a shore number.

Monetisation is kept separate from the natural units on purpose.  Case counts
and averted operational impact are what the simulation produces; dollars per
case are an external valuation whose provenance is recorded and whose effect is
swept.  The ratio a port cares about — its share of benefit against its share
of cost — survives in natural units when the two communities are valued at the
same rate, so it is reported both ways.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from types import MappingProxyType
from typing import TYPE_CHECKING, Mapping

from picard_framework.analysis.economics.contributions import (
    PAYER_PORT_AUTHORITY,
    PAYER_PUBLIC_HEALTH_AGENCY,
    PAYER_SHIP_OPERATOR,
    PAYERS,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from picard_framework.analysis.shore.counterfactual import CounterfactualResult

#: Every valuation rate a caller must document a source for.
VALUATION_RATE_FIELDS = (
    "usd_per_case_afloat",
    "usd_per_case_ashore",
    "usd_per_operational_impact_point",
    "usd_per_symptomatic_person_hour",
)

COMMUNITY_AFLOAT = "afloat"
COMMUNITY_SHORE = "shore"
COMMUNITIES = (COMMUNITY_AFLOAT, COMMUNITY_SHORE)

PAYER_COMMUNITIES: Mapping[str, str] = MappingProxyType({
    PAYER_SHIP_OPERATOR: COMMUNITY_AFLOAT,
    PAYER_PORT_AUTHORITY: COMMUNITY_SHORE,
    PAYER_PUBLIC_HEALTH_AGENCY: COMMUNITY_SHORE,
})


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
class AfloatBenefit:
    """Shipboard benefit as a paired difference between two voyage arms.

    Every field is *averted*: the surveillance-off arm minus the
    surveillance-on arm.  Negative values are legal and are not clamped — a
    capability that made an arm worse should report that it did, not silently
    show zero.
    """

    cases_averted: float = 0.0
    symptomatic_person_hours_averted: float = 0.0
    operational_impact_averted: float = 0.0
    intervention_usd_averted: float = 0.0

    def __post_init__(self) -> None:
        _require_finite("cases_averted", self.cases_averted)
        _require_finite(
            "symptomatic_person_hours_averted",
            self.symptomatic_person_hours_averted,
        )
        _require_finite(
            "operational_impact_averted", self.operational_impact_averted,
        )
        _require_finite(
            "intervention_usd_averted", self.intervention_usd_averted,
        )


@dataclass(frozen=True)
class ShoreBenefit:
    """Shore benefit, as produced by the shore counterfactual."""

    cases_averted: float = 0.0
    detection_lead_epochs: int | None = None
    epoch_hours: float = 1.0

    def __post_init__(self) -> None:
        _require_finite("cases_averted", self.cases_averted)
        if self.epoch_hours <= 0.0 or not isfinite(float(self.epoch_hours)):
            raise ValueError("epoch_hours must be positive and finite")
        if self.detection_lead_epochs is not None:
            object.__setattr__(
                self, "detection_lead_epochs", int(self.detection_lead_epochs),
            )

    @property
    def detection_lead_hours(self) -> float | None:
        """Return the shipboard detection lead in physical hours.

        The shore model counts epochs; the paper reports hours, and mixing the
        two is the class of error this repository has already paid for once.
        """
        if self.detection_lead_epochs is None:
            return None
        return float(self.detection_lead_epochs) * float(self.epoch_hours)

    @classmethod
    def from_counterfactual(
        cls, result: CounterfactualResult, *, epoch_hours: float,
    ) -> ShoreBenefit:
        """Adopt a shore counterfactual's benefit without re-deriving it."""
        return cls(
            cases_averted=float(result.benefit),
            detection_lead_epochs=result.detection_lead_epochs,
            epoch_hours=float(epoch_hours),
        )


@dataclass(frozen=True)
class BenefitValuation:
    """External monetary values for simulated outcomes.

    ``provenance`` must name a source for every rate, because none of these
    are simulation outputs and a reader has to be able to tell an anchored cost
    of illness from a placeholder.
    """

    usd_per_case_afloat: float
    usd_per_case_ashore: float
    usd_per_operational_impact_point: float = 0.0
    usd_per_symptomatic_person_hour: float = 0.0
    provenance: Mapping[str, str] = field(
        default_factory=lambda: MappingProxyType({})
    )

    def __post_init__(self) -> None:
        _require_non_negative("usd_per_case_afloat", self.usd_per_case_afloat)
        _require_non_negative("usd_per_case_ashore", self.usd_per_case_ashore)
        _require_non_negative(
            "usd_per_operational_impact_point",
            self.usd_per_operational_impact_point,
        )
        _require_non_negative(
            "usd_per_symptomatic_person_hour",
            self.usd_per_symptomatic_person_hour,
        )
        records = {str(key): str(value) for key, value in self.provenance.items()}
        if set(records) != set(VALUATION_RATE_FIELDS):
            raise ValueError("provenance must cover exactly every valuation rate")
        if any(not value.strip() for value in records.values()):
            raise ValueError("provenance entries must be non-empty")
        object.__setattr__(self, "provenance", MappingProxyType(records))

    def afloat_usd(self, benefit: AfloatBenefit) -> float:
        """Value one afloat benefit bundle."""
        return float(
            benefit.cases_averted * self.usd_per_case_afloat
            + benefit.symptomatic_person_hours_averted
            * self.usd_per_symptomatic_person_hour
            + benefit.operational_impact_averted
            * self.usd_per_operational_impact_point
            + benefit.intervention_usd_averted
        )

    def shore_usd(self, benefit: ShoreBenefit) -> float:
        """Value one shore benefit bundle."""
        return float(benefit.cases_averted * self.usd_per_case_ashore)


def _ratio(numerator: float, denominator: float) -> float | None:
    """Return a ratio, or ``None`` where the denominator cannot support one."""
    if denominator == 0.0:
        return None
    return float(numerator / denominator)


@dataclass(frozen=True)
class BenefitSplit:
    """Benefit accruing to each community, in cases and in dollars."""

    afloat_cases_averted: float
    shore_cases_averted: float
    afloat_usd: float
    shore_usd: float

    @property
    def total_usd(self) -> float:
        """Return the monetised benefit summed over communities."""
        return float(self.afloat_usd + self.shore_usd)

    @property
    def shore_to_afloat_case_ratio(self) -> float | None:
        """Return shore:afloat benefit in cases averted, valuation-free."""
        return _ratio(self.shore_cases_averted, self.afloat_cases_averted)

    @property
    def shore_to_afloat_usd_ratio(self) -> float | None:
        """Return shore:afloat benefit in monetary equivalent."""
        return _ratio(self.shore_usd, self.afloat_usd)

    def community_usd(self) -> Mapping[str, float]:
        """Return monetised benefit keyed by community."""
        return MappingProxyType({
            COMMUNITY_AFLOAT: float(self.afloat_usd),
            COMMUNITY_SHORE: float(self.shore_usd),
        })

    def benefit_shares(self) -> Mapping[str, float]:
        """Return each community's share of total monetised benefit.

        Shares are defined only when the total is positive; a zero or negative
        total reports zero shares rather than manufacturing a split.
        """
        total = self.total_usd
        if total <= 0.0:
            return MappingProxyType(dict.fromkeys(COMMUNITIES, 0.0))
        return MappingProxyType({
            COMMUNITY_AFLOAT: float(self.afloat_usd / total),
            COMMUNITY_SHORE: float(self.shore_usd / total),
        })


def benefit_split(
    afloat: AfloatBenefit,
    shore: ShoreBenefit,
    valuation: BenefitValuation,
) -> BenefitSplit:
    """Combine the two benefit streams under one valuation."""
    return BenefitSplit(
        afloat_cases_averted=float(afloat.cases_averted),
        shore_cases_averted=float(shore.cases_averted),
        afloat_usd=valuation.afloat_usd(afloat),
        shore_usd=valuation.shore_usd(shore),
    )


def _validate_weights(weights: Mapping[str, float]) -> Mapping[str, float]:
    """Validate within-community weights over the known payers."""
    records = {}
    for payer, weight in weights.items():
        if payer not in PAYERS:
            raise ValueError(f"unknown payer {payer!r}")
        records[payer] = _require_non_negative(f"weights[{payer}]", weight)
    if set(records) != set(PAYERS):
        raise ValueError("weights must cover exactly every payer")
    for community in COMMUNITIES:
        total = sum(
            weight
            for payer, weight in records.items()
            if PAYER_COMMUNITIES[payer] == community
        )
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"weights within {community} must sum to 1, got {total}")
    return MappingProxyType(records)


DEFAULT_COMMUNITY_WEIGHTS: Mapping[str, float] = MappingProxyType({
    PAYER_SHIP_OPERATOR: 1.0,
    PAYER_PORT_AUTHORITY: 0.5,
    PAYER_PUBLIC_HEALTH_AGENCY: 0.5,
})


def payer_benefit_usd(
    split: BenefitSplit,
    weights: Mapping[str, float] = DEFAULT_COMMUNITY_WEIGHTS,
) -> Mapping[str, float]:
    """Attribute community benefit to individual payers.

    The within-community split is an institutional assumption, not a
    simulation result: how a port authority and a public-health agency divide
    the value of averted shore cases is a matter of local arrangement.  It is
    therefore an explicit input, defaulting to an even shore split.
    """
    validated = _validate_weights(weights)
    community_usd = split.community_usd()
    return MappingProxyType({
        payer: float(community_usd[PAYER_COMMUNITIES[payer]] * validated[payer])
        for payer in PAYERS
    })
