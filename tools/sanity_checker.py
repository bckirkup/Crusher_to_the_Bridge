#!/usr/bin/env python3
"""
sanity_checker.py – Configuration Sanity Gatekeeper
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Scans Crusher Labs configuration files prior to an orchestrator run and
throws explicit errors if the data contains logical or physical
contradictions.  Uses pydantic models for strict structural validation.

Checks:
  1. Mathematical bound violations (probabilities, volumes, non-negative constraints)
  2. Graph referential integrity (orphan edges, ghost destinations)
  3. Logical contradictions (transmission routes, material references)

Usage::

    python tools/sanity_checker.py
    python tools/sanity_checker.py --config-dir data/config \\
                                    --platform-dir data/platforms/destroyer_baseline \\
                                    --pathogen-dir data/pathogens
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import warnings
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

from pydantic import (  # noqa: E402  (imported after the sys.path insert above)
    BaseModel,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from crusher_labs.modalities.clinical_strain_typing import (  # noqa: E402
    AssayConfigError,
    SequencingAssay,
)
from engines.incubation import IncubationModel  # noqa: E402
from engines.strain_state import (  # noqa: E402
    StrainConfigError,
    StrainEvolutionConfig,
)
from engines.transmission_core import HIGH_TOUCH_AREA_M2  # noqa: E402
from simulation_utils.paths import validated_open  # noqa: E402


def _config_value_with_retired_alias(
    section: dict[str, Any],
    canonical_key: str,
    retired_key: str,
    default: Any = None,
) -> Any:
    """Read a canonical config value while warning on its retired alias."""
    if canonical_key in section:
        return section[canonical_key]
    if retired_key in section:
        warnings.warn(
            f"{retired_key} is deprecated; use {canonical_key}",
            DeprecationWarning,
            stacklevel=3,
        )
        return section[retired_key]
    return default

# ── ANSI colour codes ────────────────────────────────────────────────────

_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_RED = "\033[91m"
_CYAN = "\033[96m"
_BOLD = "\033[1m"
_RESET = "\033[0m"

_PROTOCOLS_JSON = "protocols.json"
_ACTIVE_PROFILES_JSON = "active_profiles.json"
_SPATIAL_LAYOUT_JSON = "spatial_layout.json"
_AIR_FLOW_PATHS_JSON = "air_flow_paths.json"
_RESOURCE_COSTS_JSON = "resource_costs.json"
_CONFIG_YAML = "config.yaml"

# Sourced interval for immunosuppression prevalence in adults: Harpaz 2016
# (NHIS 2013, 2.7%), Martinson 2024 (6.6% in 2021, 7.4% in 2022),
# Lopez-Gigosos 2020 (24 of 1,196 international travellers, 2.0%). Grade B; the
# width is era and population, not uncertainty. Advisory, not a bound.
_IMM_FRACTION_LOW = 0.02
_IMM_FRACTION_HIGH = 0.074


class Severity(str, Enum):
    ERROR = "ERROR"
    WARN = "WARN"


@dataclass
class Finding:
    severity: Severity
    file: str
    rule: str
    message: str


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)

    def error(self, file: str, rule: str, msg: str) -> None:
        self.findings.append(Finding(Severity.ERROR, file, rule, msg))

    def warn(self, file: str, rule: str, msg: str) -> None:
        self.findings.append(Finding(Severity.WARN, file, rule, msg))

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == Severity.WARN]

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0


# ── Pydantic models ─────────────────────────────────────────────────────

class ZoneDisplay(BaseModel):
    x: float
    y: float


class SpatialZone(BaseModel):
    id: str
    type: str
    traffic: str = "medium"
    volume_m3: float = 100.0
    floor_area_m2: float | None = None
    ceiling_height_m: float | None = None
    elevation_m: float | None = None
    deck: str = "main"
    display: ZoneDisplay
    description: str | None = None
    base_ach: float | None = None

    @field_validator("volume_m3")
    @classmethod
    def volume_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"volume_m3 must be positive, got {v}")
        return v

    @field_validator("floor_area_m2")
    @classmethod
    def floor_area_positive(cls, v: float | None) -> float | None:
        if v is not None and v <= 0:
            raise ValueError(f"floor_area_m2 must be positive, got {v}")
        return v

    @field_validator("ceiling_height_m")
    @classmethod
    def ceiling_height_positive(cls, v: float | None) -> float | None:
        if v is not None and v <= 0:
            raise ValueError(f"ceiling_height_m must be positive, got {v}")
        return v


class SpatialLayout(BaseModel):
    platform: str
    zones: list[SpatialZone]
    description: str | None = None
    deck_dimensions: dict[str, Any] | None = None
    graywater_zones: list[str] | None = None


class HVACZone(BaseModel):
    id: str
    rooms: list[str]
    ach: float = 6.0
    description: str | None = None

    @field_validator("ach")
    @classmethod
    def ach_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError(f"ach must be non-negative, got {v}")
        return v


class CrossZoneLink(BaseModel):
    from_zone: str = Field(alias="from")
    to_zone: str = Field(alias="to")
    flow_rate_m3h: float = 50.0
    is_hvac_ducted: bool = False
    path: str | None = None
    description: str | None = None

    model_config = {"populate_by_name": True}

    @field_validator("flow_rate_m3h")
    @classmethod
    def flow_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError(f"flow_rate_m3h must be non-negative, got {v}")
        return v


class AdjacencyEdge(BaseModel):
    from_zone: str = Field(alias="from")
    to_zone: str = Field(alias="to")
    type: str = "passageway"

    model_config = {"populate_by_name": True}


class AirFlowPaths(BaseModel):
    platform: str
    hvac_zones: list[HVACZone] = []
    cross_zone_links: list[CrossZoneLink] = []
    adjacency: list[AdjacencyEdge] = []
    description: str | None = None


class ProtocolTrigger(BaseModel):
    instrument_class: str
    stoplight_level: str
    min_zones_affected: int = 1
    min_agents_affected: int | None = None
    min_modes_affected: int | None = None

    @field_validator("stoplight_level")
    @classmethod
    def valid_stoplight(cls, v: str) -> str:
        valid = {"GREEN", "AMBER", "RED"}
        if v.upper() not in valid:
            raise ValueError(f"stoplight_level must be one of {valid}, got '{v}'")
        return v.upper()


class ProtocolCosts(BaseModel):
    financial_usd: float = 0.0
    materials: dict[str, int] = {}
    labor_person_hours: float = 0.0

    @field_validator("financial_usd")
    @classmethod
    def cost_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError(f"financial_usd must be non-negative, got {v}")
        return v

    @field_validator("labor_person_hours")
    @classmethod
    def labor_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError(f"labor_person_hours must be non-negative, got {v}")
        return v


class StandingProtocol(BaseModel):
    protocol_id: str
    name: str
    description: str | None = None
    trigger: ProtocolTrigger
    modifiers: dict[str, Any] = {}
    costs_per_epoch: ProtocolCosts = ProtocolCosts()
    activation_costs: ProtocolCosts = ProtocolCosts()
    category: str = "intervention"


class ProtocolsConfig(BaseModel):
    protocols: list[StandingProtocol]
    description: str | None = None


class DoseResponse(BaseModel):
    model: str = "beta_poisson"
    alpha: float | None = None
    beta: float | None = None
    k: float | None = None

    @model_validator(mode="after")
    def check_model_params(self) -> "DoseResponse":
        if self.model == "beta_poisson":
            if self.alpha is None:
                raise ValueError("beta_poisson model requires 'alpha' parameter")
            if self.beta is None:
                raise ValueError("beta_poisson model requires 'beta' parameter")
            if self.alpha <= 0:
                raise ValueError(f"alpha must be positive, got {self.alpha}")
            if self.beta <= 0:
                raise ValueError(f"beta must be positive, got {self.beta}")
        elif self.model == "exponential":
            if self.k is None:
                raise ValueError("exponential model requires 'k' parameter")
            if self.k <= 0:
                raise ValueError(f"k must be positive, got {self.k}")
        else:
            raise ValueError(f"Unknown dose-response model: {self.model}")
        return self


class SeverityModel(BaseModel):
    states: list[str]
    base_probabilities: list[float]
    prior: dict[str, Any] = {}
    fatality_probability_by_severity: Any | None = None
    evidence_grade: str = ""

    @model_validator(mode="after")
    def validate_shape(self) -> "SeverityModel":
        expected = [
            "asymptomatic", "subclinical", "mild", "moderate", "severe_critical",
        ]
        if self.states != expected:
            raise ValueError("severity_model.states must use canonical five-state order")
        if len(self.base_probabilities) != 5:
            raise ValueError("severity_model.base_probabilities must have length 5")
        if any(
            not math.isfinite(value) or not 0.0 <= value <= 1.0
            for value in self.base_probabilities
        ):
            raise ValueError("severity_model.base_probabilities must be finite and bounded")
        if not math.isclose(sum(self.base_probabilities), 1.0):
            raise ValueError("severity_model.base_probabilities must sum to 1.0")
        if self.base_probabilities[0] >= 1.0:
            raise ValueError("severity_model.base_probabilities[0] must be < 1")
        if self.fatality_probability_by_severity is not None:
            raise NotImplementedError(
                "severity-conditioned fatality is not implemented",
            )
        return self


class ObservationModel(BaseModel):
    system: str
    syndrome_case_eligibility_by_severity: list[float]
    reporting_probability_by_severity_pre_recognition: list[float]
    reporting_probability_by_severity_post_recognition: list[float]
    active_screening: dict[str, Any] | None = None
    lab_sampling_probability_by_severity: list[float] = []
    assay_sensitivity_by_time_since_infection: Any | None = None
    episode_reporting_window_days: float

    @model_validator(mode="after")
    def validate_vectors(self) -> "ObservationModel":
        vectors = (
            self.syndrome_case_eligibility_by_severity,
            self.reporting_probability_by_severity_pre_recognition,
            self.reporting_probability_by_severity_post_recognition,
            self.lab_sampling_probability_by_severity,
        )
        for vector in vectors:
            if len(vector) != 5 or any(
                not math.isfinite(value) or not 0.0 <= value <= 1.0
                for value in vector
            ):
                raise ValueError("observation severity vectors must have five bounded values")
            if vector[0] != 0.0 or any(
                left > right for left, right in zip(vector, vector[1:])
            ):
                raise ValueError(
                    "observation severity vectors must start at zero and be non-decreasing",
                )
        if self.episode_reporting_window_days <= 0:
            raise ValueError("episode_reporting_window_days must be positive")
        if self.assay_sensitivity_by_time_since_infection is not None:
            raise NotImplementedError(
                "time-varying assay sensitivity is not implemented",
            )
        return self


class PathogenProfile(BaseModel):
    pathogen_id: str
    name: str
    category: str = ""
    transmission_routes: list[str] = []
    shedding_curve_log10: list[float] = []
    asymptomatic_shedding_log10: list[float] = []
    dose_adjustment: float = 1.0
    dose_response: DoseResponse | None = None
    illness_probability: dict[str, float] = {}
    severity_model: SeverityModel | None = None
    observation_model: ObservationModel | None = None
    recovery_day: int = 3
    shedding_duration_days: float | None = None
    chronic_shedder_fraction: float | None = None
    chronic_shedding_duration_days: dict[str, float] | None = None
    surface_deposition_fraction: float = 0.0001
    airborne_emission_fraction: float | None = None
    surface_decay_log10_per_day: float | None = None
    hand_to_surface_drying_multiplier: float | None = None
    emesis_total_shed_gec_range: list[float] | None = None
    base_susceptibility: float = 1.0
    microflora_disruption: dict[str, Any] = {}
    food_contamination: dict[str, Any] = {}
    environmental_contamination: dict[str, Any] = {}
    route_efficiency_multipliers: dict[str, float] = {}
    transmission_route_weights: dict[str, float] = {}
    innate_nonsusceptible_fraction: float = 0.0
    secretor_negative_fraction: float | None = None
    secretor_negative_relative_susceptibility: float | None = None
    nonsusceptible_mechanism: str = "none"
    introduction_epoch: int = 0
    initial_infected: int = 1
    initial_time_infected: int = 0
    shedding_profile: dict[str, Any] = {}
    incubation: dict[str, Any] = {}
    symptom_onset_day: float | None = None
    strain_evolution: dict[str, Any] = {}
    sequencing_assay: dict[str, Any] = {}
    symptom_severity: dict[str, Any] | None = None

    @model_validator(mode="after")
    def reject_retired_severity_model(self) -> "PathogenProfile":
        if self.symptom_severity is not None:
            raise ValueError("symptom_severity is retired; use severity_model")
        if self.severity_model is None and self.observation_model is None:
            return self
        if self.severity_model is None or self.observation_model is None:
            raise ValueError("severity_model and observation_model must be paired")
        return self

    @field_validator("initial_time_infected")
    @classmethod
    def initial_time_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"initial_time_infected must be non-negative, got {v}")
        return v

    @field_validator("innate_nonsusceptible_fraction")
    @classmethod
    def nonsus_frac_bounded(cls, v: float) -> float:
        if v < 0 or v > 1:
            raise ValueError(
                f"innate_nonsusceptible_fraction must be in [0,1], got {v}"
            )
        return v

    @field_validator(
        "route_efficiency_multipliers", "transmission_route_weights",
    )
    @classmethod
    def route_weights_non_negative(
        cls, v: dict[str, float], info: ValidationInfo,
    ) -> dict[str, float]:
        for k, val in v.items():
            if float(val) < 0:
                raise ValueError(
                    f"{info.field_name}[{k}] must be non-negative, got {val}"
                )
        return v

    @field_validator("surface_deposition_fraction")
    @classmethod
    def deposition_bounded(cls, v: float) -> float:
        if v < 0 or v > 1:
            raise ValueError(
                f"surface_deposition_fraction must be in [0,1], got {v}"
            )
        return v

    @field_validator("airborne_emission_fraction")
    @classmethod
    def airborne_emission_bounded(cls, v: float | None) -> float | None:
        # surface_deposition_fraction is the deprecated alias for this key.
        if v is not None and (v < 0 or v > 1):
            raise ValueError(
                f"airborne_emission_fraction must be in [0,1], got {v}"
            )
        return v

    @field_validator("surface_decay_log10_per_day")
    @classmethod
    def surface_decay_log10_non_negative(cls, v: float | None) -> float | None:
        # surface_decay_per_day is the deprecated fraction-valued alias.
        if v is not None and v < 0:
            raise ValueError(
                f"surface_decay_log10_per_day must be >= 0, got {v}"
            )
        return v

    @field_validator("hand_to_surface_drying_multiplier")
    @classmethod
    def drying_multiplier_bounded(cls, v: float | None) -> float | None:
        if v is not None and (v < 0 or v > 1):
            raise ValueError(
                "hand_to_surface_drying_multiplier must be in [0,1], "
                f"got {v}"
            )
        return v

    @field_validator("emesis_total_shed_gec_range")
    @classmethod
    def emesis_total_shed_ordered(
        cls, v: list[float] | None,
    ) -> list[float] | None:
        if v is None:
            return v
        if len(v) != 2:
            raise ValueError(
                f"emesis_total_shed_gec_range must be [low, high], got {v}"
            )
        low, high = v
        if low <= 0:
            raise ValueError(
                f"emesis_total_shed_gec_range low must be > 0, got {low}"
            )
        if low >= high:
            raise ValueError(
                f"emesis_total_shed_gec_range low must be < high, got {v}"
            )
        return v

    @field_validator("secretor_negative_fraction")
    @classmethod
    def secretor_fraction_bounded(cls, v: float | None) -> float | None:
        if v is not None and (v < 0 or v > 1):
            raise ValueError(
                f"secretor_negative_fraction must be in [0,1], got {v}"
            )
        return v

    @field_validator("secretor_negative_relative_susceptibility")
    @classmethod
    def secretor_relative_bounded(cls, v: float | None) -> float | None:
        if v is not None and (v < 0 or v > 1):
            raise ValueError(
                "secretor_negative_relative_susceptibility must be in [0,1], "
                f"got {v}"
            )
        return v

    @field_validator("base_susceptibility")
    @classmethod
    def susceptibility_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError(f"base_susceptibility must be non-negative, got {v}")
        return v


class PathogensFile(BaseModel):
    meta: dict[str, Any] = {}
    pathogens: list[PathogenProfile]


class BudgetEntry(BaseModel):
    starting_balance: float | None = None
    starting_capacity: float | None = None
    description: str | None = None

    @model_validator(mode="after")
    def budget_non_negative(self) -> "BudgetEntry":
        if self.starting_balance is not None and self.starting_balance < 0:
            raise ValueError(
                f"starting_balance must be non-negative, got {self.starting_balance}"
            )
        if self.starting_capacity is not None and self.starting_capacity < 0:
            raise ValueError(
                f"starting_capacity must be non-negative, got {self.starting_capacity}"
            )
        return self


class MaterialItem(BaseModel):
    starting_count: int = 0
    unit_cost_usd: float = 0.0
    description: str | None = None

    @field_validator("starting_count")
    @classmethod
    def count_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"starting_count must be non-negative, got {v}")
        return v

    @field_validator("unit_cost_usd")
    @classmethod
    def unit_cost_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError(f"unit_cost_usd must be non-negative, got {v}")
        return v


class OperationalImpactWeights(BaseModel):
    per_passenger_quarantined: float = 1.0
    per_essential_crew_quarantined: float = 3.0
    per_passenger_isolated: float = 0.5
    per_closed_galley_zone: float = 2.0
    per_fleet_ppe_active: float = 0.1
    essential_crew_classes: list[str] = []
    galley_zone_types: list[str] = []


class ResourceCosts(BaseModel):
    description: str | None = None
    budgets: dict[str, BudgetEntry] = {}
    material_inventory: dict[str, MaterialItem] = {}
    baseline_surveillance_costs_per_epoch: dict[str, Any] = {}
    per_test_costs: dict[str, Any] = {}
    operational_impact_weights: OperationalImpactWeights | None = None


# ── Validation checks ───────────────────────────────────────────────────

_PROBABILITY_MODIFIER_KEYS = {
    "hvac_filter_efficiency_override",
    "ppe_transmission_reduction",
    "direct_contact_scalar",
    "droplet_scalar",
    "hvac_airborne_scalar",
    "fomite_scalar",
    "vsp_isolation_threshold_fraction",
}

_VALID_TRANSMISSION_ROUTES = {
    "direct_contact",
    "fomite",
    "droplet",
    "hvac_airborne",
    "water_aerosol",
    "food",
    "water",
    "bodily_fluids",
}


def _check_mathematical_bounds(
    protocols: ProtocolsConfig | None,
    pathogens: PathogensFile | None,
    report: Report,
) -> None:
    """Check probability/scalar values are in [0, 1]."""

    if protocols:
        for proto in protocols.protocols:
            for key, val in proto.modifiers.items():
                if key in _PROBABILITY_MODIFIER_KEYS and isinstance(val, (int, float)):
                    if val < 0.0 or val > 1.0:
                        report.error(
                            _PROTOCOLS_JSON,
                            "MATH_BOUND",
                            f"{proto.protocol_id}.modifiers.{key} = {val} "
                            f"is outside [0.0, 1.0]",
                        )

    if pathogens:
        for p in pathogens.pathogens:
            illness = p.illness_probability
            for key, val in illness.items():
                if isinstance(val, (int, float)) and (val < 0 or val > 1):
                    report.error(
                        _ACTIVE_PROFILES_JSON,
                        "MATH_BOUND",
                        f"{p.pathogen_id}.illness_probability.{key} = {val} "
                        f"is outside [0.0, 1.0]",
                    )


def _check_strain_evolution(
    pathogens: PathogensFile | None,
    report: Report,
) -> None:
    """Validate optional strain_evolution blocks (variant surveillance).

    Parsing is delegated to ``StrainEvolutionConfig.from_profile`` so the
    checker and the engine cannot disagree about what a valid block is.
    """
    if pathogens is None:
        return
    for p in pathogens.pathogens:
        if not p.strain_evolution:
            continue
        try:
            StrainEvolutionConfig.from_profile(p.model_dump())
        except StrainConfigError as exc:
            report.error(
                _ACTIVE_PROFILES_JSON,
                "STRAIN_CONFIG",
                f"{p.pathogen_id}.strain_evolution invalid: {exc}",
            )
            continue
        _warn_unreachable_strain_rates(p, report)
        _warn_cross_immunity_shape(p, report)
        _check_sequencing_assay(p, report)


def _check_incubation_models(
    pathogens: PathogensFile | None,
    report: Report,
) -> None:
    """Validate optional incubation distributions.

    Parsing is delegated to ``IncubationModel.from_mapping`` so the checker and
    the progression seam cannot disagree about what a valid distribution is.
    """
    if pathogens is None:
        return
    for p in pathogens.pathogens:
        if not p.incubation:
            continue
        try:
            model = IncubationModel.from_mapping(p.incubation)
        except ValueError as exc:
            report.error(
                _ACTIVE_PROFILES_JSON,
                "INCUBATION_CONFIG",
                f"{p.pathogen_id}.incubation invalid: {exc}",
            )
            continue
        if model is not None:
            _check_incubation_shape(p, model, report)


def _check_incubation_shape(
    profile: PathogenProfile,
    model: IncubationModel,
    report: Report,
) -> None:
    """Flag distributions that cannot produce observable illness.

    A median past the recovery day means the typical host clears before it
    presents, which reads as a mild pathogen but is really a mis-specified
    incubation period; and a leftover ``symptom_onset_day`` alongside a
    distribution is dead configuration that will mislead the next reader.
    """
    if not str(profile.incubation.get("notes", "")).strip():
        report.error(
            _ACTIVE_PROFILES_JSON,
            "INCUBATION_CONFIG",
            f"{profile.pathogen_id}.incubation has no notes: an incubation "
            f"period with no provenance sets detection timing for every result",
        )
    if model.median_days >= float(profile.recovery_day):
        report.warn(
            _ACTIVE_PROFILES_JSON,
            "INCUBATION_CONFIG",
            f"{profile.pathogen_id}.incubation.median_days "
            f"({model.median_days}) is at or past recovery_day "
            f"({profile.recovery_day}): most hosts recover before presenting",
        )
    if profile.symptom_onset_day is not None:
        report.warn(
            _ACTIVE_PROFILES_JSON,
            "INCUBATION_CONFIG",
            f"{profile.pathogen_id} has both incubation and symptom_onset_day: "
            f"the distribution wins and symptom_onset_day is never read",
        )


def _check_sequencing_assay(profile: PathogenProfile, report: Report) -> None:
    """Validate the optional clinical typing assay for a strain-tracked pathogen.

    Parsing is delegated to ``SequencingAssay.from_profile`` so the checker and
    the modality cannot disagree. A strain-tracked pathogen with no assay is
    worth a warning rather than an error: the biology diversifies, but no
    clinical specimen can ever say which lineage it was.
    """
    if not profile.sequencing_assay:
        report.warn(
            _ACTIVE_PROFILES_JSON,
            "STRAIN_CONFIG",
            f"{profile.pathogen_id} tracks strains but has no sequencing_assay: "
            f"lineages exist and cannot be typed clinically",
        )
        return
    try:
        SequencingAssay.from_profile(profile.model_dump())
    except AssayConfigError as exc:
        report.error(
            _ACTIVE_PROFILES_JSON,
            "STRAIN_CONFIG",
            f"{profile.pathogen_id}.sequencing_assay invalid: {exc}",
        )


def _warn_unreachable_strain_rates(profile: PathogenProfile, report: Report) -> None:
    """Flag rate combinations that can never produce a phenotype variant."""
    block = profile.strain_evolution
    mutation = float(block.get("mutation_rate", 0.0) or 0.0)
    within_host = float(block.get("within_host_mutation_rate", 0.0) or 0.0)
    phenotype = float(block.get("phenotype_mutation_fraction", 0.0) or 0.0)
    if mutation <= 0.0 and within_host <= 0.0:
        report.warn(
            _ACTIVE_PROFILES_JSON,
            "STRAIN_CONFIG",
            f"{profile.pathogen_id}.strain_evolution has both mutation rates at "
            f"0: strains are inherited but never diversify",
        )
    elif phenotype <= 0.0:
        report.warn(
            _ACTIVE_PROFILES_JSON,
            "STRAIN_CONFIG",
            f"{profile.pathogen_id}.strain_evolution mutates but "
            f"phenotype_mutation_fraction is 0: labels drift, phenotype cannot",
        )
    if float(block.get("recombination_rate", 0.0) or 0.0) > 0.0 and \
            float(block.get("superinfection_susceptibility", 0.0) or 0.0) <= 0.0:
        report.warn(
            _ACTIVE_PROFILES_JSON,
            "STRAIN_CONFIG",
            f"{profile.pathogen_id}.strain_evolution has recombination_rate > 0 "
            f"but superinfection_susceptibility 0: co-infection can never occur, "
            f"so no recombination is reachable",
        )


def _warn_cross_immunity_shape(profile: PathogenProfile, report: Report) -> None:
    """Flag a cross-immunity matrix whose rows cannot mean what they say.

    Two shapes are almost always mistakes rather than models: a genotype with no
    row, which silently makes every host that resolved it fully susceptible to
    everything, and a row whose homologous entry is not its maximum, which says
    a host is better protected against a genotype it has never met.
    """
    block = profile.strain_evolution
    matrix = block.get("cross_immunity") or {}
    if not matrix:
        return
    for genotype in block.get("genotypes", []) or []:
        row = matrix.get(genotype)
        if not row:
            report.warn(
                _ACTIVE_PROFILES_JSON,
                "STRAIN_CONFIG",
                f"{profile.pathogen_id}.strain_evolution.cross_immunity has no "
                f"row for genotype {genotype}: prior infection with it confers "
                f"no protection at all",
            )
            continue
        homologous = float(row.get(genotype, 0.0))
        if homologous < max(float(v) for v in row.values()):
            report.warn(
                _ACTIVE_PROFILES_JSON,
                "STRAIN_CONFIG",
                f"{profile.pathogen_id}.strain_evolution.cross_immunity"
                f"[{genotype}] protects better against another genotype than "
                f"against itself",
            )


def _check_graph_integrity(
    layout: SpatialLayout | None,
    airflow: AirFlowPaths | None,
    protocols: ProtocolsConfig | None,
    report: Report,
) -> None:
    """Ensure all references point to existing zone IDs."""

    if layout is None:
        return

    valid_zones = {z.id for z in layout.zones}

    if layout.graywater_zones:
        for gz in layout.graywater_zones:
            if gz not in valid_zones:
                report.error(
                    _SPATIAL_LAYOUT_JSON,
                    "GRAPH_REF",
                    f"graywater_zones entry '{gz}' not found in spatial_layout zones",
                )
    else:
        report.error(
            _SPATIAL_LAYOUT_JSON,
            "GRAPH_REF",
            "graywater_zones must list downstream wastewater collection zone(s)",
        )

    if airflow:
        # Check HVAC zone room references
        for hz in airflow.hvac_zones:
            for room in hz.rooms:
                if room not in valid_zones:
                    report.error(
                        _AIR_FLOW_PATHS_JSON,
                        "GRAPH_REF",
                        f"HVAC zone '{hz.id}' references room '{room}' "
                        f"not found in spatial_layout.json zones: {valid_zones}",
                    )

        # Check cross-zone link endpoints
        hvac_zone_ids = {hz.id for hz in airflow.hvac_zones}
        for link in airflow.cross_zone_links:
            for endpoint_name, endpoint_val in [("from", link.from_zone), ("to", link.to_zone)]:
                if endpoint_val not in valid_zones and endpoint_val not in hvac_zone_ids:
                    report.error(
                        _AIR_FLOW_PATHS_JSON,
                        "GRAPH_REF",
                        f"Cross-zone link '{link.from_zone}' -> '{link.to_zone}' "
                        f"has '{endpoint_name}' = '{endpoint_val}' not found in "
                        f"zones or HVAC zone IDs",
                    )

        # Check adjacency edges
        for adj in airflow.adjacency:
            for endpoint_name, endpoint_val in [("from", adj.from_zone), ("to", adj.to_zone)]:
                if endpoint_val not in valid_zones:
                    report.error(
                        _AIR_FLOW_PATHS_JSON,
                        "GRAPH_REF",
                        f"Adjacency edge '{adj.from_zone}' -> '{adj.to_zone}' "
                        f"has '{endpoint_name}' = '{endpoint_val}' not found in "
                        f"spatial_layout.json zones: {valid_zones}",
                    )

    if protocols:
        for proto in protocols.protocols:
            close_zones = proto.modifiers.get("close_zones", [])
            if isinstance(close_zones, list):
                for zone in close_zones:
                    if zone not in valid_zones:
                        # Shared protocols.json follows the config.yaml default
                        # platform; other platforms may omit these zone IDs.
                        report.warn(
                            _PROTOCOLS_JSON,
                            "GRAPH_REF",
                            f"{proto.protocol_id}.modifiers.close_zones references "
                            f"'{zone}' not found in spatial_layout.json zones: "
                            f"{valid_zones}",
                        )


def _check_zone_geometry(
    layout: SpatialLayout | None,
    report: Report,
    *,
    rel_tolerance: float = 0.01,
) -> None:
    """Validate optional CONTAM geometry fields on spatial zones.

    Warns when ``volume_m3`` disagrees with ``floor_area_m2 *
    ceiling_height_m`` by more than ``rel_tolerance`` (default 1%).
    ``floor_area_m2`` and ``ceiling_height_m`` positivity (Law 3) is
    enforced by the pydantic model; this check covers the cross-field
    consistency the schema documents.
    """
    if layout is None:
        return

    for zone in layout.zones:
        area = zone.floor_area_m2
        height = zone.ceiling_height_m
        if area is None or height is None:
            continue
        derived = area * height
        if derived <= 0:
            continue
        rel_err = abs(zone.volume_m3 - derived) / derived
        if rel_err > rel_tolerance:
            report.warn(
                _SPATIAL_LAYOUT_JSON,
                "GEOMETRY",
                f"zone '{zone.id}': volume_m3 = {zone.volume_m3} disagrees "
                f"with floor_area_m2 * ceiling_height_m = "
                f"{area} * {height} = {derived:.4g} "
                f"(relative error {rel_err:.1%} > {rel_tolerance:.0%}).",
            )


def _check_logical_contradictions(
    protocols: ProtocolsConfig | None,
    resource_costs: ResourceCosts | None,
    pathogens: PathogensFile | None,
    report: Report,
) -> None:
    """Check for logical contradictions between config files."""

    # Note: Budget/labor values are tracked for reporting, not enforced
    # as limits.  No warnings are emitted for costs exceeding starting
    # allocations — the ledger is a spend tracker, not a constraint.

    # Validate pathogen transmission route names
    if pathogens:
        for p in pathogens.pathogens:
            for route in p.transmission_routes:
                if route not in _VALID_TRANSMISSION_ROUTES:
                    report.warn(
                        _ACTIVE_PROFILES_JSON,
                        "LOGIC_ROUTE",
                        f"{p.pathogen_id} has unknown transmission route "
                        f"'{route}'. Valid routes: {_VALID_TRANSMISSION_ROUTES}",
                    )

            # Route efficiencies are independent per-route dose multipliers,
            # unbounded above; there is deliberately no sum rule. Non-negativity
            # is enforced by the field validator on both key spellings.
            if p.route_efficiency_multipliers:
                field = "route_efficiency_multipliers"
                efficiencies = p.route_efficiency_multipliers
            else:
                field = "transmission_route_weights"
                efficiencies = p.transmission_route_weights or {}
            if efficiencies:
                allowed = {
                    "direct_contact", "droplet", "hvac_airborne",
                    "fomite", "food_contamination", "environmental_source",
                }
                unknown = set(efficiencies) - allowed
                if unknown:
                    report.warn(
                        _ACTIVE_PROFILES_JSON,
                        "LOGIC_ROUTE",
                        f"{p.pathogen_id} {field} has "
                        f"unknown keys {sorted(unknown)}",
                    )

            # Check that shedding curves have reasonable lengths
            if p.shedding_curve_log10:
                curve_len = len(p.shedding_curve_log10)
                if curve_len < 2:
                    report.warn(
                        _ACTIVE_PROFILES_JSON,
                        "LOGIC_SHED",
                        f"{p.pathogen_id} shedding_curve_log10 has only "
                        f"{curve_len} entries (expected >= 2 for a time-series).",
                    )
                for i, val in enumerate(p.shedding_curve_log10):
                    if val < 0:
                        report.error(
                            _ACTIVE_PROFILES_JSON,
                            "MATH_BOUND",
                            f"{p.pathogen_id}.shedding_curve_log10[{i}] = {val} "
                            f"is negative (log10 shedding rate cannot be negative "
                            f"in this model).",
                        )

            # Verify recovery_day is non-negative
            if p.recovery_day < 0:
                report.error(
                    _ACTIVE_PROFILES_JSON,
                    "MATH_BOUND",
                    f"{p.pathogen_id}.recovery_day = {p.recovery_day} is negative.",
                )

            # The shedding duration is the infectious period from onset, and a
            # host cannot stop being infectious before it stops being ill.
            if p.shedding_duration_days is not None:
                if p.shedding_duration_days < 0:
                    report.error(
                        _ACTIVE_PROFILES_JSON,
                        "MATH_BOUND",
                        f"{p.pathogen_id}.shedding_duration_days = "
                        f"{p.shedding_duration_days} is negative.",
                    )
                elif p.shedding_duration_days < p.recovery_day:
                    report.error(
                        _ACTIVE_PROFILES_JSON,
                        "MATH_BOUND",
                        f"{p.pathogen_id}.shedding_duration_days = "
                        f"{p.shedding_duration_days} is shorter than "
                        f"recovery_day = {p.recovery_day}: shedding cannot "
                        f"end before illness does.",
                    )

            # Verify introduction_epoch is non-negative
            if p.introduction_epoch < 0:
                report.error(
                    _ACTIVE_PROFILES_JSON,
                    "MATH_BOUND",
                    f"{p.pathogen_id}.introduction_epoch = {p.introduction_epoch} "
                    f"is negative.",
                )

            if p.initial_time_infected < 0:
                report.error(
                    _ACTIVE_PROFILES_JSON,
                    "MATH_BOUND",
                    f"{p.pathogen_id}.initial_time_infected = "
                    f"{p.initial_time_infected} is negative.",
                )
            curve_len = len(p.shedding_curve_log10)
            if curve_len and p.initial_time_infected >= curve_len:
                report.warn(
                    _ACTIVE_PROFILES_JSON,
                    "LOGIC",
                    f"{p.pathogen_id}.initial_time_infected = "
                    f"{p.initial_time_infected} is beyond shedding_curve_log10 "
                    f"length ({curve_len}); shedding will clamp to final day.",
                )

            # Validate food_contamination config
            fc = p.food_contamination
            if fc.get("enabled", False):
                gr = fc.get("growth_rate_per_epoch", 0.0)
                dr = fc.get("decay_rate_per_epoch", 0.0)
                if gr < 0:
                    report.error(
                        _ACTIVE_PROFILES_JSON,
                        "MATH_BOUND",
                        f"{p.pathogen_id}.food_contamination."
                        f"growth_rate_per_epoch = {gr} is negative.",
                    )
                if dr < 0 or dr > 1:
                    report.warn(
                        _ACTIVE_PROFILES_JSON,
                        "MATH_BOUND",
                        f"{p.pathogen_id}.food_contamination."
                        f"decay_rate_per_epoch = {dr} outside [0, 1].",
                    )
                if "food" not in p.transmission_routes:
                    report.warn(
                        _ACTIVE_PROFILES_JSON,
                        "LOGIC_ROUTE",
                        f"{p.pathogen_id} has food_contamination enabled "
                        f"but 'food' not in transmission_routes.",
                    )

            # Validate environmental_contamination config
            ecc = p.environmental_contamination
            if ecc.get("enabled", False):
                bl = ecc.get("baseline_environmental_load", 0.0)
                cr = ecc.get("colonization_rate_per_epoch", 0.0)
                if bl < 0:
                    report.error(
                        _ACTIVE_PROFILES_JSON,
                        "MATH_BOUND",
                        f"{p.pathogen_id}.environmental_contamination."
                        f"baseline_environmental_load = {bl} is negative.",
                    )
                if cr < 0:
                    report.error(
                        _ACTIVE_PROFILES_JSON,
                        "MATH_BOUND",
                        f"{p.pathogen_id}.environmental_contamination."
                        f"colonization_rate_per_epoch = {cr} is negative.",
                    )

    # Material references in protocol costs
    if protocols and resource_costs:
        known_materials = set(resource_costs.material_inventory.keys())
        for proto in protocols.protocols:
            for cost_block_name in ("costs_per_epoch", "activation_costs"):
                cost_block = getattr(proto, cost_block_name)
                for mat_name in cost_block.materials:
                    if mat_name not in known_materials:
                        report.warn(
                            _PROTOCOLS_JSON,
                            "LOGIC_MATERIAL",
                            f"{proto.protocol_id}.{cost_block_name} references "
                            f"material '{mat_name}' not found in "
                            f"resource_costs.json material_inventory: "
                            f"{known_materials}",
                        )

    # Validate exempt_classes references in protocols
    if protocols:
        for proto in protocols.protocols:
            ec = proto.modifiers.get("exempt_classes", [])
            if ec and not isinstance(ec, list):
                report.error(
                    _PROTOCOLS_JSON,
                    "SCHEMA",
                    f"{proto.protocol_id}.modifiers.exempt_classes must be "
                    f"a list of agent class IDs, got {type(ec).__name__}",
                )
            elif ec:
                has_confinement = (
                    proto.modifiers.get("confine_symptomatic_to_quarters", False)
                    or proto.modifiers.get("confine_all_to_quarters", False)
                )
                if not has_confinement:
                    report.warn(
                        _PROTOCOLS_JSON,
                        "LOGIC_EXEMPT",
                        f"{proto.protocol_id} has exempt_classes but no "
                        f"confinement modifier (confine_symptomatic_to_quarters "
                        f"or confine_all_to_quarters).",
                    )

    # Material references in per_test_costs
    if resource_costs:
        known_materials = set(resource_costs.material_inventory.keys())
        per_test = resource_costs.per_test_costs
        for test_type, cost_data in per_test.items():
            if isinstance(cost_data, dict):
                for mat_name in cost_data.get("materials", {}):
                    if mat_name not in known_materials:
                        report.warn(
                            _RESOURCE_COSTS_JSON,
                            "LOGIC_MATERIAL",
                            f"per_test_costs.{test_type} references "
                            f"material '{mat_name}' not found in "
                            f"material_inventory: {known_materials}",
                        )

        ois = resource_costs.operational_impact_weights
        if ois is not None:
            for field_name in (
                "per_passenger_quarantined",
                "per_essential_crew_quarantined",
                "per_passenger_isolated",
                "per_closed_galley_zone",
                "per_fleet_ppe_active",
            ):
                val = getattr(ois, field_name, 0.0)
                if val < 0:
                    report.error(
                        _RESOURCE_COSTS_JSON,
                        "BOUNDS_OIS",
                        f"operational_impact_weights.{field_name} = {val} must be non-negative",
                    )


# ── File loading + pydantic parse ────────────────────────────────────────

def _load_json(path: str) -> dict[str, Any] | None:
    if not os.path.isfile(path):
        return None
    with validated_open(path, allowed_roots=(_REPO_ROOT,), encoding="utf-8") as fh:
        return json.load(fh)


def _parse_model(
    model_cls: type[BaseModel],
    data: dict[str, Any] | None,
    filename: str,
    report: Report,
) -> BaseModel | None:
    if data is None:
        return None
    try:
        return model_cls.model_validate(data)
    except Exception as e:
        report.error(filename, "SCHEMA", str(e))
        return None



# ── Pydantic models for config.yaml sections ─────────────────────────────

class AgentClassEntry(BaseModel):
    class_id: str
    role_group: str
    fraction: float
    home_zone_preference: str = ""
    free_zone_preference: str = ""
    duty_zone: str = ""

    @field_validator("fraction")
    @classmethod
    def fraction_bounded(cls, v: float) -> float:
        if v < 0 or v > 1:
            raise ValueError(f"fraction must be in [0,1], got {v}")
        return v

    @field_validator("role_group")
    @classmethod
    def valid_role_group(cls, v: str) -> str:
        if v not in ("passenger", "crew"):
            raise ValueError(f"role_group must be 'passenger' or 'crew', got '{v}'")
        return v


class WearableNoiseEntry(BaseModel):
    channel: str
    sigma: float = 0.0
    drift_rate: float = 0.0
    dropout_prob: float = 0.0

    @field_validator("sigma")
    @classmethod
    def sigma_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError(f"sigma must be non-negative, got {v}")
        return v

    @field_validator("drift_rate")
    @classmethod
    def drift_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError(f"drift_rate must be non-negative, got {v}")
        return v

    @field_validator("dropout_prob")
    @classmethod
    def dropout_bounded(cls, v: float) -> float:
        if v < 0 or v > 1:
            raise ValueError(f"dropout_prob must be in [0,1], got {v}")
        return v


class WearableChannelResponse(BaseModel):
    channel: str
    early: float = 0.0
    peak: float = 0.0
    late: float = 0.0
    recovery: float = 0.0


class WearableInfectionResponse(BaseModel):
    pathogen_category: str
    channel_responses: list[WearableChannelResponse] = []


class WearablePhaseBoundary(BaseModel):
    day: int
    phase: str

    @field_validator("day")
    @classmethod
    def day_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"day must be non-negative, got {v}")
        return v


class WearableDetectionProfile(BaseModel):
    sensitivity: float = 1.0
    specificity: float = 1.0
    alert_latency_hours: float = 0.0
    fever_sensitivity: float = 1.0
    fever_specificity: float = 1.0

    @field_validator("sensitivity", "specificity", "fever_sensitivity", "fever_specificity")
    @classmethod
    def probability_bounded(cls, v: float) -> float:
        if v < 0 or v > 1:
            raise ValueError(f"probability must be in [0,1], got {v}")
        return v

    @field_validator("alert_latency_hours")
    @classmethod
    def latency_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError(f"alert_latency_hours must be non-negative, got {v}")
        return v


class WearableDeviceEntry(BaseModel):
    model_config = {"extra": "allow"}
    device_id: str
    channels: list[str]
    noise: list[WearableNoiseEntry] = []
    infection_responses: list[WearableInfectionResponse] = []
    phase_boundaries: list[WearablePhaseBoundary] = []
    detection_profile: WearableDetectionProfile | None = None
    confounders: list[dict[str, Any]] = []
    channel_baselines: list[dict[str, Any]] = []


class ClassDeviceMapDeviceEntry(BaseModel):
    device_id: str
    coverage: float = 1.0
    visibility: str = "medical_staff"

    @field_validator("coverage")
    @classmethod
    def coverage_bounded(cls, v: float) -> float:
        if v < 0 or v > 1:
            raise ValueError(f"coverage must be in [0,1], got {v}")
        return v

    @field_validator("visibility")
    @classmethod
    def visibility_valid(cls, v: str) -> str:
        valid = {"medical_staff", "wearer_only", "both"}
        if v not in valid:
            raise ValueError(f"visibility must be one of {valid}, got '{v}'")
        return v


class ClassDeviceMapEntry(BaseModel):
    model_config = {"extra": "allow"}
    agent_class: str
    device_id: str | None = None
    devices: list[ClassDeviceMapDeviceEntry] | None = None
    coverage: float = 1.0
    visibility: str = "medical_staff"


class ChronicDiseaseDeviceMapEntry(BaseModel):
    disease_id: str
    device_id: str
    coverage: float = 1.0
    visibility: str = "medical_staff"

    @field_validator("coverage")
    @classmethod
    def coverage_bounded(cls, v: float) -> float:
        if v < 0 or v > 1:
            raise ValueError(f"coverage must be in [0,1], got {v}")
        return v


class EmodPhase(BaseModel):
    name: str
    max_rate: float = 0.0
    sensitivity_cap: float = 0.0

    @field_validator("max_rate")
    @classmethod
    def rate_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError(f"max_rate must be non-negative, got {v}")
        return v

    @field_validator("sensitivity_cap")
    @classmethod
    def cap_bounded(cls, v: float) -> float:
        if v < 0 or v > 1:
            raise ValueError(f"sensitivity_cap must be in [0,1], got {v}")
        return v


# ── config.yaml validation checks ────────────────────────────────────────

def _check_config_yaml(
    cfg: dict[str, Any],
    report: Report,
    zone_ids: set[str] | None = None,
) -> None:
    """Validate config.yaml values: bounds, fractions, cross-references."""
    _check_agent_classes(cfg, report, zone_ids)
    _check_gender_distribution(cfg, report)
    _check_infection_counters(cfg, report)
    _check_wearable_monitoring(cfg, report)
    _check_modality_params(cfg, report)
    _check_wastewater_surveillance(cfg, report)
    _check_clinical_diagnostics(cfg, report)
    _check_hvac_params(cfg, report)
    _check_emod_progression(cfg, report)
    _check_escalation_params(cfg, report)
    _check_fred_behavior(cfg, report)
    _check_multi_pathogen_params(cfg, report)
    _check_chronic_disease(cfg, report)
    _check_microflora_params(cfg, report, zone_ids)
    _check_long_read_sequencing(cfg, report)
    _check_instrument_turnaround(cfg, report)
    _check_variant_surveillance(cfg, report)
    _check_surface_cleaning(cfg, report)


def _check_surface_cleaning(cfg: dict[str, Any], report: Report) -> None:
    """Validate routine and outbreak surface-cleaning settings."""
    cleaning = (cfg.get("transmission", {}) or {}).get(
        "surface_cleaning", {},
    )
    if not isinstance(cleaning, dict):
        report.error(_CONFIG_YAML, "CONFIG",
                     "transmission.surface_cleaning must be a mapping")
        return
    routine = cleaning.get("routine", {})
    if routine is None:
        routine = {}
    outbreak = cleaning.get("outbreak_response", {})
    if outbreak is None:
        outbreak = {}
    if not isinstance(routine, dict):
        report.error(
            _CONFIG_YAML, "CONFIG",
            "surface_cleaning.routine must be a mapping",
        )
        routine = {}
    if not isinstance(outbreak, dict):
        report.error(
            _CONFIG_YAML, "CONFIG",
            "surface_cleaning.outbreak_response must be a mapping",
        )
        outbreak = {}
    blocks = (
        ("routine", routine),
        ("outbreak_response", outbreak),
    )
    for name, block in blocks:
        if not isinstance(block, dict):
            report.error(_CONFIG_YAML, "CONFIG",
                         f"surface_cleaning.{name} must be a mapping")
            continue
        coverage = block.get("coverage")
        if isinstance(coverage, (int, float)) and not 0 <= coverage <= 1:
            report.error(
                _CONFIG_YAML, "MATH_BOUND",
                f"surface_cleaning.{name}.coverage must be in [0,1]",
            )
        reduction = block.get("log10_reduction")
        if isinstance(reduction, (int, float)) and reduction < 0:
            report.error(
                _CONFIG_YAML, "MATH_BOUND",
                f"surface_cleaning.{name}.log10_reduction must be >= 0",
            )
    events = routine.get("events_per_day")
    if isinstance(events, (int, float)) and events < 0:
        report.error(
            _CONFIG_YAML, "MATH_BOUND",
            "surface_cleaning.routine.events_per_day must be >= 0",
        )
    by_zone_class = routine.get("by_zone_class", {})
    if by_zone_class is None:
        by_zone_class = {}
    if not isinstance(by_zone_class, dict):
        report.error(
            _CONFIG_YAML, "CONFIG",
            "surface_cleaning.routine.by_zone_class must be a mapping",
        )
        return
    for zone_class, values in by_zone_class.items():
        if zone_class not in HIGH_TOUCH_AREA_M2:
            report.error(
                _CONFIG_YAML, "CONFIG",
                f"unknown surface-cleaning zone class: {zone_class}",
            )
            continue
        if not isinstance(values, dict):
            report.error(
                _CONFIG_YAML, "CONFIG",
                f"surface_cleaning.routine.by_zone_class.{zone_class} "
                "must be a mapping",
            )
            continue
        unknown_fields = set(values) - {"coverage", "events_per_day"}
        if unknown_fields:
            report.error(
                _CONFIG_YAML, "CONFIG",
                f"unknown fields in surface-cleaning zone class "
                f"{zone_class}: {sorted(unknown_fields)}",
            )
        coverage = values.get("coverage")
        if isinstance(coverage, (int, float)) and not 0 <= coverage <= 1:
            report.error(
                _CONFIG_YAML, "MATH_BOUND",
                f"surface_cleaning.routine.by_zone_class.{zone_class}."
                "coverage must be in [0,1]",
            )
        events = values.get("events_per_day")
        if isinstance(events, (int, float)) and events < 0:
            report.error(
                _CONFIG_YAML, "MATH_BOUND",
                f"surface_cleaning.routine.by_zone_class.{zone_class}."
                "events_per_day must be >= 0",
            )


def _check_variant_surveillance(cfg: dict[str, Any], report: Report) -> None:
    """Validate the variant_surveillance block (strain tracking gate)."""
    vs = cfg.get("variant_surveillance", {})
    if not isinstance(vs, dict):
        report.error(_CONFIG_YAML, "CONFIG",
                     "variant_surveillance must be a mapping")
        return
    founders = vs.get("founder_strains_per_pathogen")
    if isinstance(founders, (int, float)) and founders < 1:
        report.error(_CONFIG_YAML, "MATH_BOUND",
                     f"variant_surveillance.founder_strains_per_pathogen = "
                     f"{founders} must be >= 1")
    interval = _config_value_with_retired_alias(
        vs, "census_interval_hours", "census_interval_epochs",
    )
    if isinstance(interval, (int, float)) and interval < 1:
        report.error(_CONFIG_YAML, "MATH_BOUND",
                     f"variant_surveillance.census_interval_hours = {interval} "
                     f"must be >= 1")


def _check_instrument_turnaround(cfg: dict[str, Any], report: Report) -> None:
    """Validate instrument TAT config file and instrument keys."""
    tat_cfg = cfg.get("instrument_turnaround", {})
    config_path = tat_cfg.get("config_path")
    if not config_path:
        return
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    full = config_path if os.path.isabs(config_path) else os.path.join(_root, config_path)
    if not os.path.isfile(full):
        report.error(
            _CONFIG_YAML, "TAT",
            f"instrument_turnaround.config_path not found: {config_path}",
        )
        return
    try:
        with open(full, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        report.error(config_path, "TAT", f"instrument_turnaround JSON invalid: {exc}")
        return
    instruments = data.get("instruments", {})
    if not isinstance(instruments, dict):
        report.error(config_path, "TAT", "instruments must be an object")
        return
    known = {
        "continuous_air_sampler",
        "targeted_surface_swab",
        "clinical_rdt",
        "clinical_qpcr",
        "clinical_microbiology",
        "wastewater_sequencing",
        "long_read_verification",
        "clinical_strain_typing",
    }
    for key, block in instruments.items():
        if key not in known:
            report.warn(
                config_path, "TAT",
                f"unknown instrument key in turnaround config: {key}",
            )
        if not isinstance(block, dict):
            continue
        if "delay_epochs" in block and int(block["delay_epochs"]) < 0:
            report.error(
                config_path, "TAT",
                f"{key}.delay_epochs must be non-negative",
            )


def _check_long_read_sequencing(cfg: dict[str, Any], report: Report) -> None:
    """Validate long-read Nanopore escalation framework config."""
    lr = cfg.get("long_read_sequencing")
    if not lr:
        return
    valid_sources = {
        "wastewater_metagenomics",
        "clinical_specimen",
        "clinical_culture",
        "surveillance_swab",
    }
    sources = lr.get("specimen_sources", [])
    if isinstance(sources, list):
        for i, src in enumerate(sources):
            if src not in valid_sources:
                report.error(
                    _CONFIG_YAML, "LONG_READ",
                    f"long_read_sequencing.specimen_sources[{i}] invalid: {src}",
                )
    params_path = lr.get("params_path")
    if params_path:
        _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full = params_path if os.path.isabs(params_path) else os.path.join(_root, params_path)
        if not os.path.isfile(full):
            report.error(
                _CONFIG_YAML, "LONG_READ",
                f"long_read_sequencing.params_path not found: {params_path}",
            )
        else:
            try:
                with open(full, "r", encoding="utf-8") as fh:
                    params = json.load(fh)
                profile = lr.get(
                    "default_profile",
                    params.get("simulation_parameters", {}).get("default_profile"),
                )
                profiles = params.get("deployment_profiles", {})
                if profile and profile not in profiles:
                    report.error(
                        _CONFIG_YAML, "LONG_READ",
                        f"long_read_sequencing.default_profile unknown: {profile}",
                    )
            except json.JSONDecodeError as exc:
                report.error(
                    params_path, "LONG_READ",
                    f"long_read_sequencing.params_path invalid JSON: {exc}",
                )


def _check_agent_classes(
    cfg: dict[str, Any],
    report: Report,
    zone_ids: set[str] | None = None,
) -> None:
    """Validate agent_classes fractions, role_groups, and zone references."""
    graph_cfg = cfg.get("ship_graph", {})
    classes = graph_cfg.get("agent_classes")
    if not classes:
        return

    parsed: list[AgentClassEntry] = []
    for i, entry in enumerate(classes):
        try:
            parsed.append(AgentClassEntry.model_validate(entry))
        except Exception as e:
            report.error(_CONFIG_YAML, "SCHEMA",
                         f"agent_classes[{i}]: {e}")

    if parsed:
        total = sum(c.fraction for c in parsed)
        if abs(total - 1.0) > 0.01:
            report.error(_CONFIG_YAML, "MATH_BOUND",
                         f"agent_classes fractions sum to {total:.4f}, "
                         f"expected ~1.0 (tolerance 0.01)")

        ids = [c.class_id for c in parsed]
        if len(ids) != len(set(ids)):
            report.error(_CONFIG_YAML, "LOGIC_DUP",
                         f"Duplicate class_id values in agent_classes: {ids}")

    if zone_ids and parsed:
        for c in parsed:
            for field_name in ("home_zone_preference", "free_zone_preference", "duty_zone"):
                val = getattr(c, field_name)
                if val and not any(val in zid for zid in zone_ids):
                    report.warn(_CONFIG_YAML, "GRAPH_REF",
                                f"agent_classes.{c.class_id}.{field_name} = '{val}' "
                                f"does not match any zone in spatial_layout")


def _check_gender_distribution(cfg: dict[str, Any], report: Report) -> None:
    """Validate gender_distribution values sum to ~1.0 and are non-negative."""
    graph_cfg = cfg.get("ship_graph", {})
    gender = graph_cfg.get("gender_distribution")
    if not gender:
        return

    for k, v in gender.items():
        if not isinstance(v, (int, float)):
            continue
        if v < 0:
            report.error(_CONFIG_YAML, "MATH_BOUND",
                         f"gender_distribution.{k} = {v} is negative")

    total = sum(v for v in gender.values() if isinstance(v, (int, float)))
    if abs(total - 1.0) > 0.01:
        report.error(_CONFIG_YAML, "MATH_BOUND",
                     f"gender_distribution values sum to {total:.4f}, "
                     f"expected ~1.0 (tolerance 0.01)")


_VALID_COUNTER_METRICS = {
    "attack_rate", "reported_case_rate", "infected_count", "symptomatic_count",
    "recovered_count", "susceptible_count",
}

_VALID_ON_EXCEED = {"log_only", "confine_symptomatic"}


def _check_infection_counters(cfg: dict[str, Any], report: Report) -> None:
    """Validate infection_counters definitions in config.yaml."""
    graph_cfg = cfg.get("ship_graph", {})
    counters = graph_cfg.get("infection_counters")
    if not counters:
        return

    class_ids: set[str] = set()
    classes = graph_cfg.get("agent_classes", [])
    for cls in classes:
        cid = cls.get("class_id")
        if cid:
            class_ids.add(cid)

    counter_ids: list[str] = []
    for i, cdef in enumerate(counters):
        cid = cdef.get("counter_id")
        if not cid:
            report.error(_CONFIG_YAML, "SCHEMA",
                         f"infection_counters[{i}] missing counter_id")
            continue
        counter_ids.append(cid)

        metric = cdef.get("metric")
        if metric not in _VALID_COUNTER_METRICS:
            report.error(_CONFIG_YAML, "SCHEMA",
                         f"infection_counters.{cid}.metric = '{metric}' "
                         f"not in {_VALID_COUNTER_METRICS}")

        on_exceed = cdef.get("on_exceed", "log_only")
        if on_exceed not in _VALID_ON_EXCEED:
            report.error(_CONFIG_YAML, "SCHEMA",
                         f"infection_counters.{cid}.on_exceed = '{on_exceed}' "
                         f"not in {_VALID_ON_EXCEED}")

        threshold = cdef.get("threshold")
        if threshold is not None:
            if not isinstance(threshold, (int, float)) or threshold < 0:
                report.error(_CONFIG_YAML, "MATH_BOUND",
                             f"infection_counters.{cid}.threshold = {threshold} "
                             f"must be a non-negative number")

        cfilter = cdef.get("filter", {})
        rg = cfilter.get("role_group")
        if rg and rg not in ("crew", "passenger"):
            report.error(_CONFIG_YAML, "SCHEMA",
                         f"infection_counters.{cid}.filter.role_group = '{rg}' "
                         f"must be 'crew' or 'passenger'")

        filter_classes = cfilter.get("classes", [])
        if class_ids and filter_classes:
            for fc in filter_classes:
                if fc not in class_ids:
                    report.warn(_CONFIG_YAML, "GRAPH_REF",
                                f"infection_counters.{cid}.filter.classes "
                                f"references '{fc}' not in agent_classes")

        exempt = cdef.get("exempt_classes", [])
        if class_ids and exempt:
            for ec in exempt:
                if ec not in class_ids:
                    report.warn(_CONFIG_YAML, "GRAPH_REF",
                                f"infection_counters.{cid}.exempt_classes "
                                f"references '{ec}' not in agent_classes")

    if len(counter_ids) != len(set(counter_ids)):
        report.error(_CONFIG_YAML, "LOGIC_DUP",
                     f"Duplicate counter_id values: {counter_ids}")


def _check_wearable_monitoring(cfg: dict[str, Any], report: Report) -> None:
    """Validate wearable monitoring devices, noise, and deployment map."""
    wm = cfg.get("wearable_monitoring")
    if not wm or not wm.get("enabled", False):
        return

    devices = wm.get("devices", [])
    device_ids: set[str] = set()
    device_channels: dict[str, set[str]] = {}

    for i, dev_raw in enumerate(devices):
        try:
            dev = WearableDeviceEntry.model_validate(dev_raw)
        except Exception as e:
            report.error(_CONFIG_YAML, "SCHEMA",
                         f"wearable_monitoring.devices[{i}]: {e}")
            continue

        if dev.device_id in device_ids:
            report.error(_CONFIG_YAML, "LOGIC_DUP",
                         f"Duplicate device_id '{dev.device_id}' in wearable_monitoring.devices")
        device_ids.add(dev.device_id)
        device_channels[dev.device_id] = set(dev.channels)

        ch_set = set(dev.channels)
        for noise in dev.noise:
            if noise.channel not in ch_set:
                report.error(_CONFIG_YAML, "GRAPH_REF",
                             f"Device '{dev.device_id}' noise references channel "
                             f"'{noise.channel}' not in device channels: {ch_set}")

        for ir in dev.infection_responses:
            for cr in ir.channel_responses:
                if cr.channel not in ch_set:
                    report.error(_CONFIG_YAML, "GRAPH_REF",
                                 f"Device '{dev.device_id}' infection_response for "
                                 f"'{ir.pathogen_category}' references channel "
                                 f"'{cr.channel}' not in device channels: {ch_set}")

        # Validate confounder channel references
        for ci, conf in enumerate(dev.confounders):
            affected = conf.get("affected_channels", {})
            for conf_ch in affected:
                if conf_ch not in ch_set:
                    cid = conf.get("confounder_id", f"index {ci}")
                    report.error(_CONFIG_YAML, "GRAPH_REF",
                                 f"Device '{dev.device_id}' confounder '{cid}' "
                                 f"references channel '{conf_ch}' not in device "
                                 f"channels: {ch_set}")

    cdm = wm.get("class_device_map", [])
    for entry_raw in cdm:
        try:
            entry = ClassDeviceMapEntry.model_validate(entry_raw)
        except Exception as e:
            report.error(_CONFIG_YAML, "SCHEMA",
                         f"wearable_monitoring.class_device_map: {e}")
            continue
        # Validate device references for both old and new formats
        if entry.devices:
            for dev_entry in entry.devices:
                if dev_entry.device_id not in device_ids:
                    report.error(_CONFIG_YAML, "GRAPH_REF",
                                 f"class_device_map assigns '{entry.agent_class}' → "
                                 f"'{dev_entry.device_id}' which is not in devices: {device_ids}")
        elif entry.device_id and entry.device_id not in device_ids:
            report.error(_CONFIG_YAML, "GRAPH_REF",
                         f"class_device_map assigns '{entry.agent_class}' → "
                         f"'{entry.device_id}' which is not in devices: {device_ids}")

    # Validate chronic disease device map
    cddm = wm.get("chronic_disease_device_map", [])
    for cd_entry_raw in cddm:
        try:
            cd_entry = ChronicDiseaseDeviceMapEntry.model_validate(cd_entry_raw)
        except Exception as e:
            report.error(_CONFIG_YAML, "SCHEMA",
                         f"wearable_monitoring.chronic_disease_device_map: {e}")
            continue
        if cd_entry.device_id not in device_ids:
            report.error(_CONFIG_YAML, "GRAPH_REF",
                         f"chronic_disease_device_map assigns '{cd_entry.disease_id}' → "
                         f"'{cd_entry.device_id}' which is not in devices: {device_ids}")

    obs_sigma = wm.get("observation_noise_sigma", 0.5)
    if isinstance(obs_sigma, (int, float)) and obs_sigma < 0:
        report.error(_CONFIG_YAML, "MATH_BOUND",
                     f"wearable_monitoring.observation_noise_sigma = {obs_sigma} is negative")

    dropout = wm.get("sync_dropout_prob", 0.02)
    if isinstance(dropout, (int, float)) and (dropout < 0 or dropout > 1):
        report.error(_CONFIG_YAML, "MATH_BOUND",
                     f"wearable_monitoring.sync_dropout_prob = {dropout} outside [0,1]")

    z_thresh = wm.get("anomaly_z_threshold", 2.0)
    if isinstance(z_thresh, (int, float)) and z_thresh <= 0:
        report.error(_CONFIG_YAML, "MATH_BOUND",
                     f"wearable_monitoring.anomaly_z_threshold = {z_thresh} must be positive")

    ad_cfg = wm.get("anomaly_detection")
    if ad_cfg and ad_cfg.get("enabled", True):
        ad_z = ad_cfg.get("anomaly_z_threshold", z_thresh)
        if isinstance(ad_z, (int, float)) and ad_z <= 0:
            report.error(_CONFIG_YAML, "MATH_BOUND",
                         f"wearable_monitoring.anomaly_detection.anomaly_z_threshold "
                         f"= {ad_z} must be positive")
        for key in ("fleet_anomaly_floor", "fleet_anomaly_downweight",
                    "confounder_match_threshold"):
            val = ad_cfg.get(key)
            if val is not None and isinstance(val, (int, float)):
                if val < 0 or val > 1:
                    report.error(_CONFIG_YAML, "MATH_BOUND",
                                 f"wearable_monitoring.anomaly_detection.{key} "
                                 f"= {val} outside [0,1]")
        inf_thresh = ad_cfg.get("infection_score_threshold", 1.5)
        if isinstance(inf_thresh, (int, float)) and inf_thresh <= 0:
            report.error(_CONFIG_YAML, "MATH_BOUND",
                         f"wearable_monitoring.anomaly_detection.infection_score_threshold "
                         f"= {inf_thresh} must be positive")
        weights = ad_cfg.get("channel_infection_weights", {})
        if isinstance(weights, dict):
            for ch, w in weights.items():
                if isinstance(w, (int, float)) and (w < 0 or w > 1):
                    report.error(_CONFIG_YAML, "MATH_BOUND",
                                 f"wearable_monitoring.anomaly_detection."
                                 f"channel_infection_weights.{ch} = {w} outside [0,1]")


def _check_crew_screening_interval(cfg: dict[str, Any], report: Report) -> None:
    crew_screen = _config_value_with_retired_alias(
        cfg.get("syndromic", {}),
        "crew_screening_interval_hours",
        "crew_screening_interval_epochs",
    )
    if crew_screen is None or not isinstance(crew_screen, (int, float)):
        return
    if crew_screen >= 1:
        return
    report.error(
        _CONFIG_YAML, "MATH_BOUND",
        f"syndromic.crew_screening_interval_hours = {crew_screen} "
        f"must be null or >= 1",
    )


def _check_modality_params(cfg: dict[str, Any], report: Report) -> None:
    """Validate probability/scalar parameters for syndromic, RDT, PCR, sequencing."""
    _prob_fields = [
        ("syndromic", "sick_call_probability"),
        ("syndromic", "background_noise_rate"),
        ("clinical_rdt", "base_sensitivity"),
        ("clinical_rdt", "specificity"),
    ]
    for section, key in _prob_fields:
        val = cfg.get(section, {}).get(key)
        if val is not None and isinstance(val, (int, float)):
            if val < 0 or val > 1:
                report.error(_CONFIG_YAML, "MATH_BOUND",
                             f"{section}.{key} = {val} outside [0,1]")

    _non_neg_fields = [
        ("syndromic", "cadence"),
        ("syndromic", "activation_delay_hours"),
        ("syndromic", "detection_delay_hours"),
        ("diagnostic_cascade", "activation_delay_hours"),
        ("clinical_rdt", "cadence"),
        ("targeted_pcr", "cadence"),
        ("targeted_pcr", "extraction_efficiency"),
        ("targeted_pcr", "lod_ct_threshold"),
        ("sequencing", "cadence"),
        ("sequencing", "read_depth"),
        ("wastewater_sequencing", "read_depth"),
        ("wastewater_sequencing", "dirichlet_concentration"),
    ]
    for section, key in _non_neg_fields:
        val = cfg.get(section, {}).get(key)
        if val is not None and isinstance(val, (int, float)) and val < 0:
            report.error(_CONFIG_YAML, "MATH_BOUND",
                         f"{section}.{key} = {val} is negative")

    _check_crew_screening_interval(cfg, report)


def _check_wastewater_surveillance(cfg: dict[str, Any], report: Report) -> None:
    """Validate the sentinel wastewater sampling policy against its own dataclass.

    The dataclass is the single source of truth for what a runnable operating
    point is, so the config check asks it rather than re-deriving the bounds and
    drifting from the simulator.
    """
    block = cfg.get("wastewater_surveillance")
    if not isinstance(block, dict):
        return
    from picard_framework.analysis.sentinel.wastewater_ops import WastewaterOpsConfig

    try:
        WastewaterOpsConfig.from_mapping(block)
    except (TypeError, ValueError) as exc:
        report.error(_CONFIG_YAML, "MATH_BOUND", f"wastewater_surveillance: {exc}")


def _check_clinical_diagnostics(cfg: dict[str, Any], report: Report) -> None:
    """Validate clinical test autocorrelation matrix."""
    block = cfg.get("clinical_diagnostics", {})
    if not block:
        return
    raw = block.get("autocorrelation_matrix")
    if raw is None:
        return
    try:
        from crusher_labs.clinical_correlation import (
            CLINICAL_TEST_KEYS,
            parse_autocorrelation_matrix,
            validate_autocorrelation_matrix,
        )

        matrix = parse_autocorrelation_matrix(raw, test_order=CLINICAL_TEST_KEYS)
        validate_autocorrelation_matrix(matrix)
        if matrix.shape[0] != len(CLINICAL_TEST_KEYS):
            report.error(
                _CONFIG_YAML,
                "SCHEMA",
                "clinical_diagnostics.autocorrelation_matrix size must match test_order",
            )
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                val = float(matrix[i, j])
                if val < -1.0 or val > 1.0:
                    report.error(
                        _CONFIG_YAML,
                        "MATH_BOUND",
                        f"clinical_diagnostics.autocorrelation_matrix[{i}][{j}] "
                        f"= {val} outside [-1,1]",
                    )
    except ValueError as exc:
        report.error(_CONFIG_YAML, "SCHEMA", str(exc))


def _check_hvac_params(cfg: dict[str, Any], report: Report) -> None:
    """Validate HVAC filter efficiency and decay rate."""
    hvac = cfg.get("hvac", {})
    eff = hvac.get("filter_efficiency")
    if eff is not None and isinstance(eff, (int, float)) and (eff < 0 or eff > 1):
        report.error(_CONFIG_YAML, "MATH_BOUND",
                     f"hvac.filter_efficiency = {eff} outside [0,1]")
    decay = hvac.get("natural_decay_rate")
    if decay is not None and isinstance(decay, (int, float)) and decay < 0:
        report.error(_CONFIG_YAML, "MATH_BOUND",
                     f"hvac.natural_decay_rate = {decay} is negative")


def _check_emod_progression(cfg: dict[str, Any], report: Report) -> None:
    """Validate EMOD progression phases and durations."""
    emod = cfg.get("emod_progression", {})
    incub = _config_value_with_retired_alias(
        emod, "incubation_days", "incubation_epochs",
    )
    if incub is not None and isinstance(incub, (int, float)) and incub < 0:
        report.error(_CONFIG_YAML, "MATH_BOUND",
                     f"emod_progression.incubation_days = {incub} is negative")

    phases_raw = emod.get("shedding_phases", [])
    durations = _config_value_with_retired_alias(
        emod, "phase_durations_days", "phase_durations", [],
    )

    for i, p in enumerate(phases_raw):
        try:
            EmodPhase.model_validate(p)
        except Exception as e:
            report.error(_CONFIG_YAML, "SCHEMA",
                         f"emod_progression.shedding_phases[{i}]: {e}")

    if phases_raw and durations:
        if len(phases_raw) != len(durations):
            report.error(_CONFIG_YAML, "LOGIC_MISMATCH",
                         f"emod_progression has {len(phases_raw)} shedding_phases "
                         f"but {len(durations)} phase_durations_days — counts must match")
        for i, d in enumerate(durations):
            if isinstance(d, (int, float)) and d <= 0:
                report.error(_CONFIG_YAML, "MATH_BOUND",
                             f"emod_progression.phase_durations_days[{i}] = {d} must be positive")


def _check_escalation_params(cfg: dict[str, Any], report: Report) -> None:
    """Validate escalation thresholds and decision latency."""
    esc = cfg.get("escalation", {})
    for key in (
        "syndromic_suspect_threshold",
        "alert_sick_call_threshold",
    ):
        val = esc.get(key)
        if val is not None and isinstance(val, (int, float)) and val < 0:
            report.error(_CONFIG_YAML, "MATH_BOUND",
                         f"escalation.{key} = {val} is negative")
    for key in ("suspect_attack_rate", "confirm_attack_rate"):
        val = esc.get(key)
        if val is not None and isinstance(val, (int, float)) and (val < 0 or val > 1):
            report.error(_CONFIG_YAML, "MATH_BOUND",
                         f"escalation.{key} = {val} outside [0,1]")
    lockdown = esc.get("lockdown_attack_rate")
    if lockdown is not None and lockdown != "never":
        if isinstance(lockdown, (int, float)) and (lockdown < 0 or lockdown > 1):
            report.error(_CONFIG_YAML, "MATH_BOUND",
                         f"escalation.lockdown_attack_rate = {lockdown} outside [0,1]")
    pct = esc.get("pcr_confirm_ct_threshold")
    if pct is not None and isinstance(pct, (int, float)) and pct <= 0:
        report.error(_CONFIG_YAML, "MATH_BOUND",
                     f"escalation.pcr_confirm_ct_threshold = {pct} must be positive")
    latency = esc.get("decision_latency") or {}
    for key in (
        "alert_delay_epochs",
        "suspected_delay_epochs",
        "confirmed_delay_epochs",
        "lockdown_delay_epochs",
    ):
        val = latency.get(key)
        if val is not None and isinstance(val, (int, float)) and val < 0:
            report.error(_CONFIG_YAML, "MATH_BOUND",
                         f"escalation.decision_latency.{key} = {val} is negative")
    resp = esc.get("respiratory_overrides") or {}
    ac = resp.get("alert_confirmed_cases")
    if ac is not None and isinstance(ac, (int, float)) and ac < 0:
        report.error(_CONFIG_YAML, "MATH_BOUND",
                     f"escalation.respiratory_overrides.alert_confirmed_cases "
                     f"= {ac} is negative")
    sar = resp.get("suspect_attack_rate")
    if sar is not None and isinstance(sar, (int, float)) and (sar < 0 or sar > 1):
        report.error(_CONFIG_YAML, "MATH_BOUND",
                     f"escalation.respiratory_overrides.suspect_attack_rate "
                     f"= {sar} outside [0,1]")


def _check_fred_behavior(cfg: dict[str, Any], report: Report) -> None:
    """Validate FRED behavioral compliance parameters."""
    fred = cfg.get("fred_behavior", {})
    qc = fred.get("quarantine_compliance")
    if qc is not None and isinstance(qc, (int, float)) and (qc < 0 or qc > 1):
        report.error(_CONFIG_YAML, "MATH_BOUND",
                     f"fred_behavior.quarantine_compliance = {qc} outside [0,1]")
    delay = _config_value_with_retired_alias(
        fred, "compliance_delay_hours", "compliance_delay_epochs",
    )
    if delay is not None and isinstance(delay, (int, float)) and delay < 0:
        report.error(_CONFIG_YAML, "MATH_BOUND",
                     f"fred_behavior.compliance_delay_hours = {delay} is negative")
    rf = fred.get("reluctant_fraction")
    if rf is not None and isinstance(rf, (int, float)) and (rf < 0 or rf > 1):
        report.error(_CONFIG_YAML, "MATH_BOUND",
                     f"fred_behavior.reluctant_fraction = {rf} outside [0,1]")
    rd = _config_value_with_retired_alias(
        fred, "reluctant_delay_hours", "reluctant_delay_epochs",
    )
    if rd is not None and isinstance(rd, (int, float)) and rd < 0:
        report.error(_CONFIG_YAML, "MATH_BOUND",
                     f"fred_behavior.reluctant_delay_hours = {rd} is negative")
    for key, val in (fred.get("compliance_by_class") or {}).items():
        if isinstance(val, (int, float)) and (val < 0 or val > 1):
            report.error(_CONFIG_YAML, "MATH_BOUND",
                         f"fred_behavior.compliance_by_class[{key}] = {val} "
                         f"outside [0,1]")

    for i, cat in enumerate(fred.get("healthy_noise_categories", [])):
        prob = cat.get("probability")
        if prob is not None and isinstance(prob, (int, float)):
            if prob < 0 or prob > 1:
                report.error(_CONFIG_YAML, "MATH_BOUND",
                             f"fred_behavior.healthy_noise_categories[{i}].probability "
                             f"= {prob} outside [0,1]")


def _check_multi_pathogen_params(cfg: dict[str, Any], report: Report) -> None:
    """Validate multi-pathogen config parameters."""
    mp = cfg.get("multi_pathogen", {})
    imm_frac = mp.get("immunocompromised_fraction")
    if imm_frac is not None and isinstance(imm_frac, (int, float)):
        if imm_frac < 0 or imm_frac > 1:
            report.error(_CONFIG_YAML, "MATH_BOUND",
                         f"multi_pathogen.immunocompromised_fraction = {imm_frac} "
                         f"outside [0,1]")
        elif not (_IMM_FRACTION_LOW <= imm_frac <= _IMM_FRACTION_HIGH):
            report.warn(_CONFIG_YAML, "PROVENANCE",
                        f"multi_pathogen.immunocompromised_fraction = {imm_frac} "
                        f"outside the sourced interval "
                        f"[{_IMM_FRACTION_LOW}, {_IMM_FRACTION_HIGH}] "
                        f"(Harpaz 2016, Martinson 2024, Lopez-Gigosos 2020); see "
                        f"docs/parameter_provenance_register.md")
    if "immunocompromised_multiplier" in mp:
        report.warn(_CONFIG_YAML, "PROVENANCE",
                    "multi_pathogen.immunocompromised_multiplier is set but "
                    "refuted and ignored: it was a susceptibility multiplier on "
                    "acquisition, the one quantity no source measures. "
                    "Immunocompromise acts on shedding duration through the "
                    "pathogen profile's chronic_shedder_fraction and "
                    "chronic_shedding_duration_days; see "
                    "docs/parameter_provenance_register.md")


def _check_chronic_disease(cfg: dict[str, Any], report: Report) -> None:
    """Validate chronic disease config block and JSON file."""
    cd = cfg.get("chronic_disease", {})
    if not cd.get("enabled", False):
        return

    config_path = cd.get("config_path", "")
    if not config_path:
        report.warn(_CONFIG_YAML, "CONFIG",
                     "chronic_disease.enabled but no config_path specified")
        return

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    full_path = os.path.join(repo_root, config_path)
    if not os.path.isfile(full_path):
        report.error(_CONFIG_YAML, "FILE",
                      f"chronic_disease.config_path '{config_path}' not found")
        return

    try:
        with open(full_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        report.error(config_path, "FILE", f"Cannot parse: {exc}")
        return

    diseases = data.get("diseases", [])
    if not diseases:
        report.warn(config_path, "CONFIG", "No diseases defined")
        return

    for i, d in enumerate(diseases):
        did = d.get("disease_id", "")
        if not did:
            report.error(config_path, "SCHEMA",
                          f"diseases[{i}] missing disease_id")
            continue

        prev_map = d.get("prevalence_by_class", {})
        for cls_name, prev in prev_map.items():
            if isinstance(prev, (int, float)) and (prev < 0 or prev > 1):
                report.error(config_path, "MATH_BOUND",
                              f"{did}.prevalence_by_class.{cls_name} = {prev} "
                              f"outside [0,1]")

        pmods = d.get("pathogen_modifiers", {})
        for pid, mods in pmods.items():
            susc = mods.get("susceptibility_multiplier")
            if susc is not None and isinstance(susc, (int, float)) and susc < 0:
                report.error(config_path, "MATH_BOUND",
                              f"{did}.pathogen_modifiers.{pid}."
                              f"susceptibility_multiplier = {susc} is negative")
            sev = mods.get("severity_multiplier")
            if sev is not None and isinstance(sev, (int, float)) and sev < 0:
                report.error(config_path, "MATH_BOUND",
                              f"{did}.pathogen_modifiers.{pid}."
                              f"severity_multiplier = {sev} is negative")
            rec = mods.get("recovery_day_extension")
            if rec is not None and isinstance(rec, (int, float)) and rec < 0:
                report.error(config_path, "MATH_BOUND",
                              f"{did}.pathogen_modifiers.{pid}."
                              f"recovery_day_extension = {rec} is negative")
            boost = mods.get("illness_probability_boost")
            if boost is not None and isinstance(boost, (int, float)):
                if boost < 0 or boost > 1:
                    report.error(config_path, "MATH_BOUND",
                                  f"{did}.pathogen_modifiers.{pid}."
                                  f"illness_probability_boost = {boost} "
                                  f"outside [0,1]")

        wscale = d.get("wearable_infection_response_scale")
        if wscale is not None and isinstance(wscale, (int, float)) and wscale < 0:
            report.error(config_path, "MATH_BOUND",
                          f"{did}.wearable_infection_response_scale = {wscale} "
                          f"is negative")

    max_comorbid = cd.get("max_comorbid")
    if max_comorbid is not None and isinstance(max_comorbid, int) and max_comorbid < 1:
        report.error(_CONFIG_YAML, "MATH_BOUND",
                      f"chronic_disease.max_comorbid = {max_comorbid} must be >= 1")


def _check_microflora_params(
    cfg: dict[str, Any],
    report: Report,
    zone_ids: set[str] | None = None,
) -> None:
    """Validate microflora config and cross-reference graywater zones."""
    mf = cfg.get("microflora", {})
    shed = mf.get("disrupted_shed_mass")
    if shed is not None and isinstance(shed, (int, float)) and shed < 0:
        report.error(_CONFIG_YAML, "MATH_BOUND",
                     f"microflora.disrupted_shed_mass = {shed} is negative")
    scale = mf.get("clr_shift_scale")
    if scale is not None and isinstance(scale, (int, float)) and scale < 0:
        report.error(_CONFIG_YAML, "MATH_BOUND",
                     f"microflora.clr_shift_scale = {scale} is negative")

    if zone_ids:
        explicit = mf.get("graywater_zones")
        if explicit:
            for gz in explicit:
                if gz not in zone_ids:
                    report.warn(_CONFIG_YAML, "GRAPH_REF",
                                f"microflora.graywater_zones override references '{gz}' "
                                f"not found in spatial_layout zones")


# ── Path resolution (orchestrator-aligned) ───────────────────────────────

def paths_from_run_config(repo_root: str, config_yaml: str | None = None) -> dict[str, Any]:
    """Resolve platform + pathogen paths from crusher_labs/config.yaml.

    Returns a dict with ``config_dir``, ``platform_dir``, ``pathogen_file``,
    and ``cfg`` (the raw parsed config dict for downstream validation).
    """
    if config_yaml is None:
        config_yaml = os.path.join(repo_root, "crusher_labs", _CONFIG_YAML)
    sys.path.insert(0, repo_root)
    from crusher_labs import load_config
    cfg = load_config(config_yaml)
    layout_rel = cfg.get("ship_graph", {}).get(
        "spatial_layout", "data/platforms/mega_cruise_5000/spatial_layout.json")
    platform_dir = os.path.dirname(os.path.join(repo_root, layout_rel))
    profiles_rel = cfg.get("multi_pathogen", {}).get(
        "profiles_path", "data/pathogens/active_profiles.json")
    return {
        "config_dir": os.path.join(repo_root, "data", "config"),
        "platform_dir": platform_dir,
        "pathogen_file": os.path.join(repo_root, profiles_rel),
        "cfg": cfg,
    }

# ── Main ─────────────────────────────────────────────────────────────────

def run_checks(
    config_dir: str,
    platform_dir: str,
    pathogen_dir: str | None = None,
    *,
    pathogen_file: str | None = None,
    cfg: dict[str, Any] | None = None,
) -> Report:
    """Run all sanity checks.

    Uses pathogen_file or {pathogen_dir}/active_profiles.json.
    When *cfg* is provided (the parsed config.yaml dict), also validates
    config.yaml values: bounds, fractions, cross-references.
    """
    if pathogen_file is None:
        base = pathogen_dir or os.path.join(config_dir, "..", "pathogens")
        pathogen_file = os.path.join(base, _ACTIVE_PROFILES_JSON)
    pathogen_label = os.path.basename(pathogen_file)
    report = Report()

    print(f"\n{_CYAN}{_BOLD}  CRUSHER LABS SANITY CHECKER{_RESET}")
    print(f"  {'─' * 50}")
    print(f"  Config dir:     {config_dir}")
    print(f"  Platform dir:   {platform_dir}")
    print(f"  Pathogen file:  {pathogen_file}")
    print(f"  {'─' * 50}\n")

    # Load files
    spatial_data = _load_json(os.path.join(platform_dir, _SPATIAL_LAYOUT_JSON))
    airflow_data = _load_json(os.path.join(platform_dir, _AIR_FLOW_PATHS_JSON))
    protocols_data = _load_json(os.path.join(config_dir, _PROTOCOLS_JSON))
    pathogen_data = _load_json(pathogen_file)
    resource_data = _load_json(os.path.join(config_dir, _RESOURCE_COSTS_JSON))

    files_found = {
        _SPATIAL_LAYOUT_JSON: spatial_data is not None,
        _AIR_FLOW_PATHS_JSON: airflow_data is not None,
        _PROTOCOLS_JSON: protocols_data is not None,
        pathogen_label: pathogen_data is not None,
        _RESOURCE_COSTS_JSON: resource_data is not None,
    }

    for fname, found in files_found.items():
        icon = f"{_GREEN}OK{_RESET}" if found else f"{_YELLOW}MISSING{_RESET}"
        print(f"  [{icon}] {fname}")
    print()

    if not any(files_found.values()):
        report.error("(all)", "FILE", "No configuration files found.")
        return report

    # Parse with pydantic
    print(f"  {_CYAN}Parsing schemas...{_RESET}")
    layout = _parse_model(SpatialLayout, spatial_data, _SPATIAL_LAYOUT_JSON, report)
    airflow = _parse_model(AirFlowPaths, airflow_data, _AIR_FLOW_PATHS_JSON, report)
    protocols = _parse_model(ProtocolsConfig, protocols_data, _PROTOCOLS_JSON, report)
    pathogens = _parse_model(PathogensFile, pathogen_data, pathogen_label, report)
    resource_costs = _parse_model(ResourceCosts, resource_data, _RESOURCE_COSTS_JSON, report)

    schema_errors = len(report.errors)
    if schema_errors:
        print(f"  {_RED}Schema validation found {schema_errors} error(s){_RESET}")
    else:
        print(f"  {_GREEN}All schemas valid{_RESET}")
    print()

    # Run checks
    print(f"  {_CYAN}Running mathematical bound checks...{_RESET}")
    pre = len(report.findings)
    _check_mathematical_bounds(protocols, pathogens, report)
    added = len(report.findings) - pre
    if added:
        print(f"  {_RED}Found {added} issue(s){_RESET}")
    else:
        print(f"  {_GREEN}All bounds valid{_RESET}")

    print(f"  {_CYAN}Running graph referential integrity checks...{_RESET}")
    pre = len(report.findings)
    _check_graph_integrity(layout, airflow, protocols, report)
    added = len(report.findings) - pre
    if added:
        print(f"  {_RED}Found {added} issue(s){_RESET}")
    else:
        print(f"  {_GREEN}All references resolved{_RESET}")

    print(f"  {_CYAN}Running zone geometry checks...{_RESET}")
    pre = len(report.findings)
    _check_zone_geometry(layout, report)
    added = len(report.findings) - pre
    if added:
        print(f"  {_YELLOW}Found {added} issue(s){_RESET}")
    else:
        print(f"  {_GREEN}All zone geometry consistent{_RESET}")

    print(f"  {_CYAN}Running logical contradiction checks...{_RESET}")
    pre = len(report.findings)
    _check_logical_contradictions(protocols, resource_costs, pathogens, report)
    added = len(report.findings) - pre
    if added:
        print(f"  {_YELLOW}Found {added} issue(s){_RESET}")
    else:
        print(f"  {_GREEN}No contradictions detected{_RESET}")

    print(f"  {_CYAN}Running incubation distribution checks...{_RESET}")
    pre = len(report.findings)
    _check_incubation_models(pathogens, report)
    added = len(report.findings) - pre
    if added:
        print(f"  {_YELLOW}Found {added} issue(s){_RESET}")
    else:
        print(f"  {_GREEN}Incubation distributions valid{_RESET}")

    print(f"  {_CYAN}Running strain evolution checks...{_RESET}")
    pre = len(report.findings)
    _check_strain_evolution(pathogens, report)
    added = len(report.findings) - pre
    if added:
        print(f"  {_YELLOW}Found {added} issue(s){_RESET}")
    else:
        print(f"  {_GREEN}Strain parameters valid{_RESET}")

    if cfg is not None:
        zone_ids = {z.id for z in layout.zones} if layout else None
        print(f"\n  {_CYAN}Running config.yaml validation checks...{_RESET}")
        pre = len(report.findings)
        _check_config_yaml(cfg, report, zone_ids)
        added = len(report.findings) - pre
        if added:
            errs = sum(1 for f in report.findings[pre:] if f.severity == Severity.ERROR)
            warns = added - errs
            parts = []
            if errs:
                parts.append(f"{errs} error(s)")
            if warns:
                parts.append(f"{warns} warning(s)")
            color = _RED if errs else _YELLOW
            print(f"  {color}Found {', '.join(parts)}{_RESET}")
        else:
            print(f"  {_GREEN}All config.yaml values valid{_RESET}")

    return report


def print_report(report: Report) -> None:
    """Print the final pass/fail report with colour coding."""
    print(f"\n  {'═' * 60}")

    if report.findings:
        for f in report.findings:
            if f.severity == Severity.ERROR:
                icon = f"{_RED}{_BOLD}ERROR{_RESET}"
            else:
                icon = f"{_YELLOW}{_BOLD} WARN{_RESET}"
            print(f"  [{icon}] [{f.rule}] {f.file}")
            print(f"         {f.message}")
        print(f"\n  {'─' * 60}")

    n_err = len(report.errors)
    n_warn = len(report.warnings)

    if report.passed:
        if n_warn:
            print(
                f"\n  {_GREEN}{_BOLD}VALIDATION PASSED{_RESET} "
                f"with {_YELLOW}{n_warn} warning(s){_RESET}\n"
            )
        else:
            print(
                f"\n  {_GREEN}{_BOLD}VALIDATION PASSED{_RESET} — "
                f"all configuration files are structurally sound.\n"
            )
    else:
        print(
            f"\n  {_RED}{_BOLD}VALIDATION FAILED{_RESET} — "
            f"{n_err} error(s), {n_warn} warning(s)\n"
            f"  Fix the errors above before running the orchestrator.\n"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate Crusher Labs configuration files for structural "
                    "and logical correctness.",
    )
    parser.add_argument(
        "--config-dir",
        default=os.path.join(_REPO_ROOT, "data", "config"),
        help="Path to config directory (default: data/config/)",
    )
    parser.add_argument(
        "--platform-dir",
        default=os.path.join(_REPO_ROOT, "data", "platforms", "mega_cruise_5000"),
        help="Path to platform directory (default: data/platforms/mega_cruise_5000/)",
    )
    parser.add_argument(
        "--from-config",
        action="store_true",
        help="Use platform and pathogen paths from crusher_labs/config.yaml.",
    )
    parser.add_argument(
        "--config-yaml",
        default=os.path.join(_REPO_ROOT, "crusher_labs", _CONFIG_YAML),
    )
    parser.add_argument(
        "--pathogen-dir",
        default=os.path.join(_REPO_ROOT, "data", "pathogens"),
        help="Directory for active_profiles.json when --pathogen-file omitted",
    )
    parser.add_argument(
        "--pathogen-file",
        default=None,
        help="Pathogen profiles JSON (multi_pathogen.profiles_path)",
    )
    args = parser.parse_args()
    if args.from_config:
        r = paths_from_run_config(_REPO_ROOT, args.config_yaml)
        print(f"  Paths from {args.config_yaml}\n")
        report = run_checks(
            r["config_dir"], r["platform_dir"],
            pathogen_file=r["pathogen_file"], cfg=r["cfg"],
        )
    else:
        pf = args.pathogen_file or os.path.join(args.pathogen_dir, _ACTIVE_PROFILES_JSON)
        report = run_checks(args.config_dir, args.platform_dir, pathogen_file=pf)
    print_report(report)

    sys.exit(0 if report.passed else 1)


if __name__ == "__main__":
    main()
