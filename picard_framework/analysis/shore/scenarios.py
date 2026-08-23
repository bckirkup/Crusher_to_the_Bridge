"""Named, cited shore-transmission scenarios.

This module records author-supplied norovirus shore parameters without making
them defaults for the shore renewal, counterfactual, or surface APIs.  The
central generation-interval estimate is attributed to Harris et al. 2014.
The eight-day truncation is a modelling choice applied to that distribution,
not a value attributed to Harris.  Community ``R_shore`` is a cited range with
an author-selected central value.  Residual importation and detection
threshold values are policy/scenario assumptions, not literature estimates.

Every numeric scenario field has a machine-readable :class:`ParameterProvenance`
record.  This keeps the distinction between anchored inputs, modelling choices,
and unanchored assumptions auditable without adding a JSON configuration file.
The central scenario is deliberately supercritical because ``r_shore = 1.6``;
its ``unbounded_growth`` flag is therefore expected, and its
``depletion_regime`` flag is expected on a sufficiently long horizon.  Results
are interpretable only while cumulative cases remain small relative to the port
population.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType
from typing import Literal, Mapping

from picard_framework.analysis.shore.renewal import ShoreRenewalParameters

AnchoringStatus = Literal[
    "anchored",
    "unanchored",
    "modelling_choice",
    "cited_range_author_selected",
]


@dataclass(frozen=True)
class ParameterProvenance:
    """Machine-readable provenance for one numeric scenario field."""

    source_text: str
    anchoring: AnchoringStatus
    semantics: Mapping[str, str] = MappingProxyType({})

    @property
    def anchored(self) -> bool:
        """Whether the field is anchored to the stated source."""
        return self.anchoring == "anchored"


_NUMERIC_FIELDS = (
    "r_shore",
    "r_shore_grid",
    "generation_median_hours",
    "generation_sigma",
    "generation_max_hours",
    "residual_importation_fraction",
    "residual_importation_fraction_grid",
    "case_threshold",
    "case_threshold_grid",
)


def _validate_grid(
    values: tuple[float, ...],
    *,
    field_name: str,
    central: float,
) -> None:
    """Validate one ordered, unique sweep grid containing its centre."""
    if not values:
        raise ValueError(f"{field_name} must be non-empty")
    if any(not isfinite(value) for value in values):
        raise ValueError(f"{field_name} must contain finite values")
    if tuple(sorted(set(values))) != values:
        raise ValueError(f"{field_name} must be sorted and unique")
    if central not in values:
        raise ValueError(f"{field_name} must contain its central value")


def _validate_provenance(
    provenance: Mapping[str, ParameterProvenance],
) -> Mapping[str, ParameterProvenance]:
    """Require one non-empty structured record for every numeric field."""
    records = dict(provenance)
    if set(records) != set(_NUMERIC_FIELDS):
        raise ValueError("provenance must cover exactly every numeric scenario field")
    if any(
        not record.source_text.strip()
        for record in records.values()
    ):
        raise ValueError("provenance source_text must be non-empty")
    if any(
        any(not key or not value.strip() for key, value in record.semantics.items())
        for record in records.values()
    ):
        raise ValueError("provenance semantics must have non-empty keys and values")
    return MappingProxyType(records)


@dataclass(frozen=True)
class ShoreTransmissionScenario:
    """Named shore parameter set with explicit central values and sweeps."""

    pathogen_id: str
    name: str
    r_shore: float
    r_shore_grid: tuple[float, ...]
    generation_median_hours: float
    generation_sigma: float
    generation_max_hours: float
    residual_importation_fraction: float
    residual_importation_fraction_grid: tuple[float, ...]
    case_threshold: float
    case_threshold_grid: tuple[float, ...]
    provenance: Mapping[str, ParameterProvenance]

    def __post_init__(self) -> None:
        values = (
            self.r_shore,
            self.generation_median_hours,
            self.generation_sigma,
            self.generation_max_hours,
            self.residual_importation_fraction,
            self.case_threshold,
        )
        if not self.pathogen_id or not self.name:
            raise ValueError("pathogen_id and name must be non-empty")
        if any(not isfinite(float(value)) for value in values):
            raise ValueError("scenario numeric fields must be finite")
        if self.r_shore < 0.0:
            raise ValueError("r_shore must be non-negative")
        if self.generation_median_hours <= 0.0:
            raise ValueError("generation_median_hours must be positive")
        if self.generation_sigma <= 0.0:
            raise ValueError("generation_sigma must be positive")
        if self.generation_max_hours <= 0.0:
            raise ValueError("generation_max_hours must be positive")
        if not 0.0 <= self.residual_importation_fraction <= 1.0:
            raise ValueError("residual_importation_fraction must be in [0, 1]")
        if self.case_threshold < 0.0:
            raise ValueError("case_threshold must be non-negative")
        _validate_grid(
            self.r_shore_grid,
            field_name="r_shore_grid",
            central=self.r_shore,
        )
        _validate_grid(
            self.residual_importation_fraction_grid,
            field_name="residual_importation_fraction_grid",
            central=self.residual_importation_fraction,
        )
        _validate_grid(
            self.case_threshold_grid,
            field_name="case_threshold_grid",
            central=self.case_threshold,
        )
        object.__setattr__(self, "provenance", _validate_provenance(self.provenance))

    def renewal_parameters(self, population: int) -> ShoreRenewalParameters:
        """Build central renewal parameters for a caller-supplied population."""
        return ShoreRenewalParameters(
            r_shore=self.r_shore,
            generation_median_hours=self.generation_median_hours,
            generation_sigma=self.generation_sigma,
            generation_max_hours=self.generation_max_hours,
            population=population,
        )


_HARRIS_GENERATION_SOURCE = (
    "Harris et al. 2014, 65 hospital norovirus outbreaks in England, "
    "doi:10.1136/bmjopen-2013-003060: direct serial interval measurement "
    "of 1.86 d (95% CI 1.6-2.2 d), not derived from incubation. "
    "The central value is chosen because port transmission is expected to "
    "be close-contact dominated, similar to the hospital setting."
)
_R_SHORE_SOURCE = (
    "Steele et al. 2020, 7,094 norovirus outbreaks from NORS 2009-2017, "
    "doi:10.3201/eid2608.191537: median R0 2.75 (IQR 2.38-3.65) and "
    "median Re 1.29 (IQR 1.12-1.74), broadly similar across settings "
    "except long-term care (3.35) and schools (2.92). Gaythorpe et al. "
    "2018 modelling review, doi:10.1017/S0950268817002692: community "
    "estimates cluster around R0 approximately 2, while outbreak-derived "
    "estimates run higher. Author judgement: 1.6 is deliberately above "
    "the NORS median Re because a port catchment receiving infectious "
    "disembarkations is a high-mixing environment, including tourists and "
    "food-service workers; the grid spans 1.1 to the outbreak-setting "
    "value 2.75. The central value is not itself a measured estimate."
)
_POLICY_SOURCE = "Author-supplied policy/scenario assumption; not literature."
_RESIDUAL_SEMANTICS = {
    "0.1": "aggressive response: isolation, delayed disembarkation, and screening",
    "0.3": (
        "moderate response: port-health notification, voluntary screening, "
        "and some infectious disembarkation"
    ),
    "0.5": "notification only",
    "0.8": "detection with no effective intervention",
}
_THRESHOLD_SEMANTICS = {
    "1": "single-case investigation in an aggressive or wearable-equipped scenario",
    "3": "standard cluster-detection response",
    "5": "moderate capacity",
    "10": "weak surveillance after substantial spread",
}
_RESIDUAL_CENTRAL_SEMANTIC = (
    "moderate response; central value justified by VSP notification "
    "requirements with incomplete enforcement and pre-symptomatic shedders"
)
_THRESHOLD_CENTRAL_SEMANTIC = "standard cluster threshold"
_POLICY_PROVENANCE = MappingProxyType(
    {
        "residual_importation_fraction": ParameterProvenance(
            _POLICY_SOURCE,
            "unanchored",
            semantics={"0.3": _RESIDUAL_CENTRAL_SEMANTIC},
        ),
        "residual_importation_fraction_grid": ParameterProvenance(
            _POLICY_SOURCE,
            "unanchored",
            semantics=_RESIDUAL_SEMANTICS,
        ),
        "case_threshold": ParameterProvenance(
            _POLICY_SOURCE,
            "unanchored",
            semantics={"3": _THRESHOLD_CENTRAL_SEMANTIC},
        ),
        "case_threshold_grid": ParameterProvenance(
            _POLICY_SOURCE,
            "unanchored",
            semantics=_THRESHOLD_SEMANTICS,
        ),
    }
)

NORWALK_GI_SHORE_SCENARIO = ShoreTransmissionScenario(
    pathogen_id="norwalk_gi",
    name="Norovirus shore transmission (Harris et al. 2014 generation interval)",
    r_shore=1.6,
    r_shore_grid=(1.1, 1.3, 1.6, 2.0, 2.75),
    generation_median_hours=44.6,
    generation_sigma=0.47,
    generation_max_hours=192.0,
    residual_importation_fraction=0.3,
    residual_importation_fraction_grid=(0.1, 0.3, 0.5, 0.8),
    case_threshold=3.0,
    case_threshold_grid=(1.0, 3.0, 5.0, 10.0),
    provenance={
        "r_shore": ParameterProvenance(
            _R_SHORE_SOURCE,
            "cited_range_author_selected",
        ),
        "r_shore_grid": ParameterProvenance(
            _R_SHORE_SOURCE,
            "cited_range_author_selected",
        ),
        "generation_median_hours": ParameterProvenance(
            _HARRIS_GENERATION_SOURCE,
            "anchored",
        ),
        "generation_sigma": ParameterProvenance(
            _HARRIS_GENERATION_SOURCE,
            "anchored",
        ),
        "generation_max_hours": ParameterProvenance(
            f"{_HARRIS_GENERATION_SOURCE}; eight-day truncation is a modelling "
            "choice, not attributed to Harris et al. 2014.",
            "modelling_choice",
        ),
        **_POLICY_PROVENANCE,
    },
)

NORWALK_GI_ENVIRONMENTAL_SHORE_SCENARIO = ShoreTransmissionScenario(
    pathogen_id="norwalk_gi",
    name="Norovirus environmental-dominated shore transmission (Heijne et al. 2009)",
    r_shore=NORWALK_GI_SHORE_SCENARIO.r_shore,
    r_shore_grid=NORWALK_GI_SHORE_SCENARIO.r_shore_grid,
    generation_median_hours=86.4,
    generation_sigma=0.47,
    generation_max_hours=192.0,
    residual_importation_fraction=0.3,
    residual_importation_fraction_grid=(0.1, 0.3, 0.5, 0.8),
    case_threshold=3.0,
    case_threshold_grid=(1.0, 3.0, 5.0, 10.0),
    provenance={
        "r_shore": ParameterProvenance(
            _R_SHORE_SOURCE,
            "cited_range_author_selected",
        ),
        "r_shore_grid": ParameterProvenance(
            _R_SHORE_SOURCE,
            "cited_range_author_selected",
        ),
        "generation_median_hours": ParameterProvenance(
            "Heijne et al. 2009, Netherlands scout-jamboree outbreak, "
            "doi:10.3201/eid1501.080299: mean generation time 3.6 d, "
            "gamma-fitted from Swedish outbreak data. This scenario "
            "approximates that mean as 86.4 h in the lognormal median field; "
            "it is not silently treated as a median.",
            "modelling_choice",
        ),
        "generation_sigma": ParameterProvenance(
            "Carried from the central Harris et al. 2014 scenario because "
            "Heijne et al. 2009 supplies no spread parameter; not estimated "
            "from the environmental outbreak.",
            "modelling_choice",
        ),
        "generation_max_hours": ParameterProvenance(
            "Eight-day truncation is a modelling choice in this scenario, "
            "not attributed to Harris et al. 2014 or Heijne et al. 2009.",
            "modelling_choice",
        ),
        **_POLICY_PROVENANCE,
    },
)

SHORE_SCENARIOS: Mapping[str, ShoreTransmissionScenario] = MappingProxyType(
    {
        "norwalk_gi": NORWALK_GI_SHORE_SCENARIO,
        "norwalk_gi_environmental": NORWALK_GI_ENVIRONMENTAL_SHORE_SCENARIO,
    }
)
