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
    introduction_epoch: int = 0
    initial_infected: int = 1
    shedding_profile: dict[str, Any] = {}

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


class ResourceCosts(BaseModel):
    description: str | None = None
    budgets: dict[str, BudgetEntry] = {}
    material_inventory: dict[str, MaterialItem] = {}
    baseline_surveillance_costs_per_epoch: dict[str, Any] = {}
    per_test_costs: dict[str, Any] = {}


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


# ── Main ─────────────────────────────────────────────────────────────────

def run_checks(
    config_dir: str,
    platform_dir: str,
    pathogen_dir: str,
) -> Report:
    """Run all sanity checks and return a report."""
    report = Report()

    print(f"\n{_CYAN}{_BOLD}  CRUSHER LABS SANITY CHECKER{_RESET}")
    print(f"  {'─' * 50}")
    print(f"  Config dir:   {config_dir}")
    print(f"  Platform dir: {platform_dir}")
    print(f"  Pathogen dir: {pathogen_dir}")
    print(f"  {'─' * 50}\n")

    # Load files
    spatial_data = _load_json(os.path.join(platform_dir, "spatial_layout.json"))
    airflow_data = _load_json(os.path.join(platform_dir, "air_flow_paths.json"))
    protocols_data = _load_json(os.path.join(config_dir, "protocols.json"))
    pathogen_data = _load_json(os.path.join(pathogen_dir, "active_profiles.json"))
    resource_data = _load_json(os.path.join(config_dir, "resource_costs.json"))

    files_found = {
        "spatial_layout.json": spatial_data is not None,
        "air_flow_paths.json": airflow_data is not None,
        "protocols.json": protocols_data is not None,
        "active_profiles.json": pathogen_data is not None,
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
    pathogens = _parse_model(PathogensFile, pathogen_data, "active_profiles.json", report)
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
        "--pathogen-dir",
        default=os.path.join(_REPO_ROOT, "data", "pathogens"),
        help="Path to pathogen profiles directory (default: data/pathogens/)",
    )
    args = parser.parse_args()

    report = run_checks(args.config_dir, args.platform_dir, args.pathogen_dir)
    print_report(report)

    sys.exit(0 if report.passed else 1)


if __name__ == "__main__":
    main()
