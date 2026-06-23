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
import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

# ── ANSI colour codes ────────────────────────────────────────────────────

_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_RED = "\033[91m"
_CYAN = "\033[96m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


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


class SpatialLayout(BaseModel):
    platform: str
    zones: list[SpatialZone]
    description: str | None = None
    deck_dimensions: dict[str, Any] | None = None


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
    recovery_day: int = 3
    surface_deposition_fraction: float = 0.0001
    base_susceptibility: float = 1.0
    microflora_disruption: dict[str, Any] = {}
    food_contamination: dict[str, Any] = {}
    environmental_contamination: dict[str, Any] = {}
    introduction_epoch: int = 0
    initial_infected: int = 1
    initial_time_infected: int = 0
    shedding_profile: dict[str, Any] = {}

    @field_validator("initial_time_infected")
    @classmethod
    def initial_time_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"initial_time_infected must be non-negative, got {v}")
        return v

    @field_validator("surface_deposition_fraction")
    @classmethod
    def deposition_bounded(cls, v: float) -> float:
        if v < 0 or v > 1:
            raise ValueError(
                f"surface_deposition_fraction must be in [0,1], got {v}"
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
    "surface_decontamination_factor",
    "surface_decay_rate_override",
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
                            "protocols.json",
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
                        "active_profiles.json",
                        "MATH_BOUND",
                        f"{p.pathogen_id}.illness_probability.{key} = {val} "
                        f"is outside [0.0, 1.0]",
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

    if airflow:
        # Check HVAC zone room references
        for hz in airflow.hvac_zones:
            for room in hz.rooms:
                if room not in valid_zones:
                    report.error(
                        "air_flow_paths.json",
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
                        "air_flow_paths.json",
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
                        "air_flow_paths.json",
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
                        report.error(
                            "protocols.json",
                            "GRAPH_REF",
                            f"{proto.protocol_id}.modifiers.close_zones references "
                            f"'{zone}' not found in spatial_layout.json zones: "
                            f"{valid_zones}",
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
                        "active_profiles.json",
                        "LOGIC_ROUTE",
                        f"{p.pathogen_id} has unknown transmission route "
                        f"'{route}'. Valid routes: {_VALID_TRANSMISSION_ROUTES}",
                    )

            # Check that shedding curves have reasonable lengths
            if p.shedding_curve_log10:
                curve_len = len(p.shedding_curve_log10)
                if curve_len < 2:
                    report.warn(
                        "active_profiles.json",
                        "LOGIC_SHED",
                        f"{p.pathogen_id} shedding_curve_log10 has only "
                        f"{curve_len} entries (expected >= 2 for a time-series).",
                    )
                for i, val in enumerate(p.shedding_curve_log10):
                    if val < 0:
                        report.error(
                            "active_profiles.json",
                            "MATH_BOUND",
                            f"{p.pathogen_id}.shedding_curve_log10[{i}] = {val} "
                            f"is negative (log10 shedding rate cannot be negative "
                            f"in this model).",
                        )

            # Verify recovery_day is non-negative
            if p.recovery_day < 0:
                report.error(
                    "active_profiles.json",
                    "MATH_BOUND",
                    f"{p.pathogen_id}.recovery_day = {p.recovery_day} is negative.",
                )

            # Verify introduction_epoch is non-negative
            if p.introduction_epoch < 0:
                report.error(
                    "active_profiles.json",
                    "MATH_BOUND",
                    f"{p.pathogen_id}.introduction_epoch = {p.introduction_epoch} "
                    f"is negative.",
                )

            if p.initial_time_infected < 0:
                report.error(
                    "active_profiles.json",
                    "MATH_BOUND",
                    f"{p.pathogen_id}.initial_time_infected = "
                    f"{p.initial_time_infected} is negative.",
                )
            curve_len = len(p.shedding_curve_log10)
            if curve_len and p.initial_time_infected >= curve_len:
                report.warn(
                    "active_profiles.json",
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
                        "active_profiles.json",
                        "MATH_BOUND",
                        f"{p.pathogen_id}.food_contamination."
                        f"growth_rate_per_epoch = {gr} is negative.",
                    )
                if dr < 0 or dr > 1:
                    report.warn(
                        "active_profiles.json",
                        "MATH_BOUND",
                        f"{p.pathogen_id}.food_contamination."
                        f"decay_rate_per_epoch = {dr} outside [0, 1].",
                    )
                if "food" not in p.transmission_routes:
                    report.warn(
                        "active_profiles.json",
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
                        "active_profiles.json",
                        "MATH_BOUND",
                        f"{p.pathogen_id}.environmental_contamination."
                        f"baseline_environmental_load = {bl} is negative.",
                    )
                if cr < 0:
                    report.error(
                        "active_profiles.json",
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
                            "protocols.json",
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
                    "protocols.json",
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
                        "protocols.json",
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
                            "resource_costs.json",
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
                        "resource_costs.json",
                        "BOUNDS_OIS",
                        f"operational_impact_weights.{field_name} = {val} must be non-negative",
                    )


# ── File loading + pydantic parse ────────────────────────────────────────

def _load_json(path: str) -> dict[str, Any] | None:
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
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
            "config.yaml", "TAT",
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
                    "config.yaml", "LONG_READ",
                    f"long_read_sequencing.specimen_sources[{i}] invalid: {src}",
                )
    params_path = lr.get("params_path")
    if params_path:
        _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full = params_path if os.path.isabs(params_path) else os.path.join(_root, params_path)
        if not os.path.isfile(full):
            report.error(
                "config.yaml", "LONG_READ",
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
                        "config.yaml", "LONG_READ",
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
            report.error("config.yaml", "SCHEMA",
                         f"agent_classes[{i}]: {e}")

    if parsed:
        total = sum(c.fraction for c in parsed)
        if abs(total - 1.0) > 0.01:
            report.error("config.yaml", "MATH_BOUND",
                         f"agent_classes fractions sum to {total:.4f}, "
                         f"expected ~1.0 (tolerance 0.01)")

        ids = [c.class_id for c in parsed]
        if len(ids) != len(set(ids)):
            report.error("config.yaml", "LOGIC_DUP",
                         f"Duplicate class_id values in agent_classes: {ids}")

    if zone_ids and parsed:
        for c in parsed:
            for field_name in ("home_zone_preference", "free_zone_preference", "duty_zone"):
                val = getattr(c, field_name)
                if val and not any(val in zid for zid in zone_ids):
                    report.warn("config.yaml", "GRAPH_REF",
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
            report.error("config.yaml", "MATH_BOUND",
                         f"gender_distribution.{k} = {v} is negative")

    total = sum(v for v in gender.values() if isinstance(v, (int, float)))
    if abs(total - 1.0) > 0.01:
        report.error("config.yaml", "MATH_BOUND",
                     f"gender_distribution values sum to {total:.4f}, "
                     f"expected ~1.0 (tolerance 0.01)")


_VALID_COUNTER_METRICS = {
    "attack_rate", "infected_count", "symptomatic_count",
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
            report.error("config.yaml", "SCHEMA",
                         f"infection_counters[{i}] missing counter_id")
            continue
        counter_ids.append(cid)

        metric = cdef.get("metric")
        if metric not in _VALID_COUNTER_METRICS:
            report.error("config.yaml", "SCHEMA",
                         f"infection_counters.{cid}.metric = '{metric}' "
                         f"not in {_VALID_COUNTER_METRICS}")

        on_exceed = cdef.get("on_exceed", "log_only")
        if on_exceed not in _VALID_ON_EXCEED:
            report.error("config.yaml", "SCHEMA",
                         f"infection_counters.{cid}.on_exceed = '{on_exceed}' "
                         f"not in {_VALID_ON_EXCEED}")

        threshold = cdef.get("threshold")
        if threshold is not None:
            if not isinstance(threshold, (int, float)) or threshold < 0:
                report.error("config.yaml", "MATH_BOUND",
                             f"infection_counters.{cid}.threshold = {threshold} "
                             f"must be a non-negative number")

        cfilter = cdef.get("filter", {})
        rg = cfilter.get("role_group")
        if rg and rg not in ("crew", "passenger"):
            report.error("config.yaml", "SCHEMA",
                         f"infection_counters.{cid}.filter.role_group = '{rg}' "
                         f"must be 'crew' or 'passenger'")

        filter_classes = cfilter.get("classes", [])
        if class_ids and filter_classes:
            for fc in filter_classes:
                if fc not in class_ids:
                    report.warn("config.yaml", "GRAPH_REF",
                                f"infection_counters.{cid}.filter.classes "
                                f"references '{fc}' not in agent_classes")

        exempt = cdef.get("exempt_classes", [])
        if class_ids and exempt:
            for ec in exempt:
                if ec not in class_ids:
                    report.warn("config.yaml", "GRAPH_REF",
                                f"infection_counters.{cid}.exempt_classes "
                                f"references '{ec}' not in agent_classes")

    if len(counter_ids) != len(set(counter_ids)):
        report.error("config.yaml", "LOGIC_DUP",
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
            report.error("config.yaml", "SCHEMA",
                         f"wearable_monitoring.devices[{i}]: {e}")
            continue

        if dev.device_id in device_ids:
            report.error("config.yaml", "LOGIC_DUP",
                         f"Duplicate device_id '{dev.device_id}' in wearable_monitoring.devices")
        device_ids.add(dev.device_id)
        device_channels[dev.device_id] = set(dev.channels)

        ch_set = set(dev.channels)
        for noise in dev.noise:
            if noise.channel not in ch_set:
                report.error("config.yaml", "GRAPH_REF",
                             f"Device '{dev.device_id}' noise references channel "
                             f"'{noise.channel}' not in device channels: {ch_set}")

        for ir in dev.infection_responses:
            for cr in ir.channel_responses:
                if cr.channel not in ch_set:
                    report.error("config.yaml", "GRAPH_REF",
                                 f"Device '{dev.device_id}' infection_response for "
                                 f"'{ir.pathogen_category}' references channel "
                                 f"'{cr.channel}' not in device channels: {ch_set}")

        # Validate confounder channel references
        for ci, conf in enumerate(dev.confounders):
            affected = conf.get("affected_channels", {})
            for conf_ch in affected:
                if conf_ch not in ch_set:
                    cid = conf.get("confounder_id", f"index {ci}")
                    report.error("config.yaml", "GRAPH_REF",
                                 f"Device '{dev.device_id}' confounder '{cid}' "
                                 f"references channel '{conf_ch}' not in device "
                                 f"channels: {ch_set}")

    cdm = wm.get("class_device_map", [])
    for entry_raw in cdm:
        try:
            entry = ClassDeviceMapEntry.model_validate(entry_raw)
        except Exception as e:
            report.error("config.yaml", "SCHEMA",
                         f"wearable_monitoring.class_device_map: {e}")
            continue
        # Validate device references for both old and new formats
        if entry.devices:
            for dev_entry in entry.devices:
                if dev_entry.device_id not in device_ids:
                    report.error("config.yaml", "GRAPH_REF",
                                 f"class_device_map assigns '{entry.agent_class}' → "
                                 f"'{dev_entry.device_id}' which is not in devices: {device_ids}")
        elif entry.device_id and entry.device_id not in device_ids:
            report.error("config.yaml", "GRAPH_REF",
                         f"class_device_map assigns '{entry.agent_class}' → "
                         f"'{entry.device_id}' which is not in devices: {device_ids}")

    # Validate chronic disease device map
    cddm = wm.get("chronic_disease_device_map", [])
    for cd_entry_raw in cddm:
        try:
            cd_entry = ChronicDiseaseDeviceMapEntry.model_validate(cd_entry_raw)
        except Exception as e:
            report.error("config.yaml", "SCHEMA",
                         f"wearable_monitoring.chronic_disease_device_map: {e}")
            continue
        if cd_entry.device_id not in device_ids:
            report.error("config.yaml", "GRAPH_REF",
                         f"chronic_disease_device_map assigns '{cd_entry.disease_id}' → "
                         f"'{cd_entry.device_id}' which is not in devices: {device_ids}")

    obs_sigma = wm.get("observation_noise_sigma", 0.5)
    if isinstance(obs_sigma, (int, float)) and obs_sigma < 0:
        report.error("config.yaml", "MATH_BOUND",
                     f"wearable_monitoring.observation_noise_sigma = {obs_sigma} is negative")

    dropout = wm.get("sync_dropout_prob", 0.02)
    if isinstance(dropout, (int, float)) and (dropout < 0 or dropout > 1):
        report.error("config.yaml", "MATH_BOUND",
                     f"wearable_monitoring.sync_dropout_prob = {dropout} outside [0,1]")

    z_thresh = wm.get("anomaly_z_threshold", 2.0)
    if isinstance(z_thresh, (int, float)) and z_thresh <= 0:
        report.error("config.yaml", "MATH_BOUND",
                     f"wearable_monitoring.anomaly_z_threshold = {z_thresh} must be positive")

    ad_cfg = wm.get("anomaly_detection")
    if ad_cfg and ad_cfg.get("enabled", True):
        ad_z = ad_cfg.get("anomaly_z_threshold", z_thresh)
        if isinstance(ad_z, (int, float)) and ad_z <= 0:
            report.error("config.yaml", "MATH_BOUND",
                         f"wearable_monitoring.anomaly_detection.anomaly_z_threshold "
                         f"= {ad_z} must be positive")
        for key in ("fleet_anomaly_floor", "fleet_anomaly_downweight",
                    "confounder_match_threshold"):
            val = ad_cfg.get(key)
            if val is not None and isinstance(val, (int, float)):
                if val < 0 or val > 1:
                    report.error("config.yaml", "MATH_BOUND",
                                 f"wearable_monitoring.anomaly_detection.{key} "
                                 f"= {val} outside [0,1]")
        inf_thresh = ad_cfg.get("infection_score_threshold", 1.5)
        if isinstance(inf_thresh, (int, float)) and inf_thresh <= 0:
            report.error("config.yaml", "MATH_BOUND",
                         f"wearable_monitoring.anomaly_detection.infection_score_threshold "
                         f"= {inf_thresh} must be positive")
        weights = ad_cfg.get("channel_infection_weights", {})
        if isinstance(weights, dict):
            for ch, w in weights.items():
                if isinstance(w, (int, float)) and (w < 0 or w > 1):
                    report.error("config.yaml", "MATH_BOUND",
                                 f"wearable_monitoring.anomaly_detection."
                                 f"channel_infection_weights.{ch} = {w} outside [0,1]")


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
                report.error("config.yaml", "MATH_BOUND",
                             f"{section}.{key} = {val} outside [0,1]")

    _non_neg_fields = [
        ("syndromic", "cadence"),
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
        if val is not None and isinstance(val, (int, float)):
            if val < 0:
                report.error("config.yaml", "MATH_BOUND",
                             f"{section}.{key} = {val} is negative")


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
                "config.yaml",
                "SCHEMA",
                "clinical_diagnostics.autocorrelation_matrix size must match test_order",
            )
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                val = float(matrix[i, j])
                if val < -1.0 or val > 1.0:
                    report.error(
                        "config.yaml",
                        "MATH_BOUND",
                        f"clinical_diagnostics.autocorrelation_matrix[{i}][{j}] "
                        f"= {val} outside [-1,1]",
                    )
    except ValueError as exc:
        report.error("config.yaml", "SCHEMA", str(exc))


def _check_hvac_params(cfg: dict[str, Any], report: Report) -> None:
    """Validate HVAC filter efficiency and decay rate."""
    hvac = cfg.get("hvac", {})
    eff = hvac.get("filter_efficiency")
    if eff is not None and isinstance(eff, (int, float)):
        if eff < 0 or eff > 1:
            report.error("config.yaml", "MATH_BOUND",
                         f"hvac.filter_efficiency = {eff} outside [0,1]")
    decay = hvac.get("natural_decay_rate")
    if decay is not None and isinstance(decay, (int, float)):
        if decay < 0:
            report.error("config.yaml", "MATH_BOUND",
                         f"hvac.natural_decay_rate = {decay} is negative")


def _check_emod_progression(cfg: dict[str, Any], report: Report) -> None:
    """Validate EMOD progression phases and durations."""
    emod = cfg.get("emod_progression", {})
    incub = emod.get("incubation_epochs")
    if incub is not None and isinstance(incub, (int, float)) and incub < 0:
        report.error("config.yaml", "MATH_BOUND",
                     f"emod_progression.incubation_epochs = {incub} is negative")

    phases_raw = emod.get("shedding_phases", [])
    durations = emod.get("phase_durations", [])

    for i, p in enumerate(phases_raw):
        try:
            EmodPhase.model_validate(p)
        except Exception as e:
            report.error("config.yaml", "SCHEMA",
                         f"emod_progression.shedding_phases[{i}]: {e}")

    if phases_raw and durations:
        if len(phases_raw) != len(durations):
            report.error("config.yaml", "LOGIC_MISMATCH",
                         f"emod_progression has {len(phases_raw)} shedding_phases "
                         f"but {len(durations)} phase_durations — counts must match")
        for i, d in enumerate(durations):
            if isinstance(d, (int, float)) and d <= 0:
                report.error("config.yaml", "MATH_BOUND",
                             f"emod_progression.phase_durations[{i}] = {d} must be positive")


def _check_escalation_params(cfg: dict[str, Any], report: Report) -> None:
    """Validate escalation thresholds."""
    esc = cfg.get("escalation", {})
    sst = esc.get("syndromic_suspect_threshold")
    if sst is not None and isinstance(sst, (int, float)) and sst < 0:
        report.error("config.yaml", "MATH_BOUND",
                     f"escalation.syndromic_suspect_threshold = {sst} is negative")
    pct = esc.get("pcr_confirm_ct_threshold")
    if pct is not None and isinstance(pct, (int, float)) and pct <= 0:
        report.error("config.yaml", "MATH_BOUND",
                     f"escalation.pcr_confirm_ct_threshold = {pct} must be positive")


def _check_fred_behavior(cfg: dict[str, Any], report: Report) -> None:
    """Validate FRED behavioral compliance parameters."""
    fred = cfg.get("fred_behavior", {})
    qc = fred.get("quarantine_compliance")
    if qc is not None and isinstance(qc, (int, float)):
        if qc < 0 or qc > 1:
            report.error("config.yaml", "MATH_BOUND",
                         f"fred_behavior.quarantine_compliance = {qc} outside [0,1]")
    delay = fred.get("compliance_delay_epochs")
    if delay is not None and isinstance(delay, (int, float)) and delay < 0:
        report.error("config.yaml", "MATH_BOUND",
                     f"fred_behavior.compliance_delay_epochs = {delay} is negative")

    for i, cat in enumerate(fred.get("healthy_noise_categories", [])):
        prob = cat.get("probability")
        if prob is not None and isinstance(prob, (int, float)):
            if prob < 0 or prob > 1:
                report.error("config.yaml", "MATH_BOUND",
                             f"fred_behavior.healthy_noise_categories[{i}].probability "
                             f"= {prob} outside [0,1]")


def _check_multi_pathogen_params(cfg: dict[str, Any], report: Report) -> None:
    """Validate multi-pathogen config parameters."""
    mp = cfg.get("multi_pathogen", {})
    imm_frac = mp.get("immunocompromised_fraction")
    if imm_frac is not None and isinstance(imm_frac, (int, float)):
        if imm_frac < 0 or imm_frac > 1:
            report.error("config.yaml", "MATH_BOUND",
                         f"multi_pathogen.immunocompromised_fraction = {imm_frac} "
                         f"outside [0,1]")
    imm_mult = mp.get("immunocompromised_multiplier")
    if imm_mult is not None and isinstance(imm_mult, (int, float)):
        if imm_mult < 0:
            report.error("config.yaml", "MATH_BOUND",
                         f"multi_pathogen.immunocompromised_multiplier = {imm_mult} "
                         f"is negative")


def _check_chronic_disease(cfg: dict[str, Any], report: Report) -> None:
    """Validate chronic disease config block and JSON file."""
    cd = cfg.get("chronic_disease", {})
    if not cd.get("enabled", False):
        return

    config_path = cd.get("config_path", "")
    if not config_path:
        report.warn("config.yaml", "CONFIG",
                     "chronic_disease.enabled but no config_path specified")
        return

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    full_path = os.path.join(repo_root, config_path)
    if not os.path.isfile(full_path):
        report.error("config.yaml", "FILE",
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
        report.error("config.yaml", "MATH_BOUND",
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
        report.error("config.yaml", "MATH_BOUND",
                     f"microflora.disrupted_shed_mass = {shed} is negative")
    scale = mf.get("clr_shift_scale")
    if scale is not None and isinstance(scale, (int, float)) and scale < 0:
        report.error("config.yaml", "MATH_BOUND",
                     f"microflora.clr_shift_scale = {scale} is negative")

    if zone_ids:
        for gz in mf.get("graywater_zones", []):
            if gz not in zone_ids:
                report.warn("config.yaml", "GRAPH_REF",
                            f"microflora.graywater_zones references '{gz}' "
                            f"not found in spatial_layout zones")


# ── Path resolution (orchestrator-aligned) ───────────────────────────────

def paths_from_run_config(repo_root: str, config_yaml: str | None = None) -> dict[str, Any]:
    """Resolve platform + pathogen paths from crusher_labs/config.yaml.

    Returns a dict with ``config_dir``, ``platform_dir``, ``pathogen_file``,
    and ``cfg`` (the raw parsed config dict for downstream validation).
    """
    if config_yaml is None:
        config_yaml = os.path.join(repo_root, "crusher_labs", "config.yaml")
    sys.path.insert(0, repo_root)
    from crusher_labs import load_config
    cfg = load_config(config_yaml)
    layout_rel = cfg.get("ship_graph", {}).get(
        "spatial_layout", "data/platforms/destroyer_baseline/spatial_layout.json")
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
        pathogen_file = os.path.join(base, "active_profiles.json")
    pathogen_label = os.path.basename(pathogen_file)
    report = Report()

    print(f"\n{_CYAN}{_BOLD}  CRUSHER LABS SANITY CHECKER{_RESET}")
    print(f"  {'─' * 50}")
    print(f"  Config dir:     {config_dir}")
    print(f"  Platform dir:   {platform_dir}")
    print(f"  Pathogen file:  {pathogen_file}")
    print(f"  {'─' * 50}\n")

    # Load files
    spatial_data = _load_json(os.path.join(platform_dir, "spatial_layout.json"))
    airflow_data = _load_json(os.path.join(platform_dir, "air_flow_paths.json"))
    protocols_data = _load_json(os.path.join(config_dir, "protocols.json"))
    pathogen_data = _load_json(pathogen_file)
    resource_data = _load_json(os.path.join(config_dir, "resource_costs.json"))

    files_found = {
        "spatial_layout.json": spatial_data is not None,
        "air_flow_paths.json": airflow_data is not None,
        "protocols.json": protocols_data is not None,
        pathogen_label: pathogen_data is not None,
        "resource_costs.json": resource_data is not None,
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
    layout = _parse_model(SpatialLayout, spatial_data, "spatial_layout.json", report)
    airflow = _parse_model(AirFlowPaths, airflow_data, "air_flow_paths.json", report)
    protocols = _parse_model(ProtocolsConfig, protocols_data, "protocols.json", report)
    pathogens = _parse_model(PathogensFile, pathogen_data, pathogen_label, report)
    resource_costs = _parse_model(ResourceCosts, resource_data, "resource_costs.json", report)

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

    print(f"  {_CYAN}Running logical contradiction checks...{_RESET}")
    pre = len(report.findings)
    _check_logical_contradictions(protocols, resource_costs, pathogens, report)
    added = len(report.findings) - pre
    if added:
        print(f"  {_YELLOW}Found {added} issue(s){_RESET}")
    else:
        print(f"  {_GREEN}No contradictions detected{_RESET}")

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
    _REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
        default=os.path.join(_REPO_ROOT, "data", "platforms", "destroyer_baseline"),
        help="Path to platform directory (default: data/platforms/destroyer_baseline/)",
    )
    parser.add_argument(
        "--from-config",
        action="store_true",
        help="Use platform and pathogen paths from crusher_labs/config.yaml.",
    )
    parser.add_argument(
        "--config-yaml",
        default=os.path.join(_REPO_ROOT, "crusher_labs", "config.yaml"),
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
        pf = args.pathogen_file or os.path.join(args.pathogen_dir, "active_profiles.json")
        report = run_checks(args.config_dir, args.platform_dir, pathogen_file=pf)
    print_report(report)

    sys.exit(0 if report.passed else 1)


if __name__ == "__main__":
    main()
