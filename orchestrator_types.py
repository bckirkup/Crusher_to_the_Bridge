"""
orchestrator_types.py – Shared types, constants, and dataclasses
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Defines the simulation state container, instrument bundles,
protocol context, and shared constants used across all
orchestrator modules.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from crusher_labs.clinical_correlation import ClinicalTestCorrelation
from crusher_labs.cost_ledger import CostLedger
from crusher_labs.lab_notebook import ArtificialLabNotebook
from crusher_labs.observation_core import (
    ClinicalMicrobiology,
    ClinicalQPCR,
    ClinicalRapidDiagnostic,
    ContinuousAirSniffer,
    LongReadVerificationSequencing,
    TargetedSurfaceSwab,
    WastewaterHoldingTankAssay,
    WastewaterSequencingGrid,
)
from crusher_labs.protocol_engine import ProtocolEngine
from engines.sim_clock import SimClock

# ── Trigger status constants ─────────────────────────────────────────────
# Five-level escalation (Campaign v5 / outbreak response architecture):
#   0 BASELINE → 1 ALERT → 2 SUSPECTED → 3 CONFIRMED → 4 LOCKDOWN
STATUS_BASELINE = "BASELINE"
STATUS_ALERT = "ALERT"
STATUS_SUSPECTED = "SUSPECTED"
STATUS_CONFIRMED = "CONFIRMED"
STATUS_LOCKDOWN = "LOCKDOWN"

STATUS_RANK: dict[str, int] = {
    STATUS_BASELINE: 0,
    STATUS_ALERT: 1,
    STATUS_SUSPECTED: 2,
    STATUS_CONFIRMED: 3,
    STATUS_LOCKDOWN: 4,
}

# Compliance class labels (bimodal mixture; assigned at first quarantine order)
COMPLIANCE_CLASS_COMPLIANT = "compliant"
COMPLIANCE_CLASS_RELUCTANT = "reluctant"
COMPLIANCE_CLASS_DEFIANT = "defiant"

# ── Agent orthogonal status axes (telemetry_buffer.agent_axes) ───────────
from telemetry_buffer.agent_axes import (  # noqa: E402,F401
    COMPLIANCE_COMPLIANT,
    COMPLIANCE_ISOLATED,
    COMPLIANCE_NON_COMPLIANT,
    COMPLIANCE_QUARANTINED,
    INFECTION_IMMUNE,
    INFECTION_INFECTED,
    INFECTION_RECOVERED,
    INFECTION_SUSCEPTIBLE,
    PRESENTATION_ASYMPTOMATIC,
    PRESENTATION_MILD,
    PRESENTATION_SEVERE,
    PRESENTATION_SYMPTOMATIC,
    PRESENTATION_SYMPTOMATIC_LEVELS,
)

# ── Synthetic locations for confined agents ──────────────────────────────
LOCATION_ISOLATED = "Isolated_In_Quarters"
LOCATION_QUARANTINED = "Quarantined_In_Quarters"
LOCATION_ASHORE = "Ashore"

# ── Defaults for configurable fractions (Law 1: no hardcoded ops) ────────
DEFAULT_AIRBORNE_FRACTION = 0.6
DEFAULT_SURFACE_FRACTION = 0.4
DEFAULT_GREYWATER_FRACTION = 0.1
DEFAULT_GRAYWATER_PROPAGATION_FACTOR = 0.3

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


# ── Simulation state container ───────────────────────────────────────────

@dataclass
class SimulationState:
    """Mutable state carried across epochs."""

    trigger_status: str = STATUS_BASELINE
    isolated_ids: set[int] = field(default_factory=set)
    quarantined_ids: set[int] = field(default_factory=set)
    isolation_unit_capacity: int = 0
    quarantine_refusers: set[int] = field(default_factory=set)
    quarantine_order_epoch: dict[int, int] = field(default_factory=dict)
    escalation_log: list[dict[str, Any]] = field(default_factory=list)
    compliance_log: list[dict[str, Any]] = field(default_factory=list)
    simulation_history: list[dict[str, Any]] = field(default_factory=list)
    forced_protocol_ids: set[str] = field(default_factory=set)
    verification_test_queue: list[dict[str, Any]] = field(default_factory=list)
    agent_behavioral_overrides: dict[int, str] = field(default_factory=dict)
    cascade_engine: Any = None  # DiagnosticCascadeEngine | None
    chronic_assignments: dict[int, list[str]] = field(default_factory=dict)
    chronic_behavioral_mods: dict[int, dict[str, float]] = field(default_factory=dict)
    # Outbreak-response architecture (escalation + compliance)
    cumulative_confirmed_case_ids: set[int] = field(default_factory=set)
    ever_infected_ids: set[int] = field(default_factory=set)
    ever_ill_ids: set[int] = field(default_factory=set)
    ever_reported_ids: set[int] = field(default_factory=set)
    ever_reported_noise_ids: set[int] = field(default_factory=set)
    infections_by_dominant_route: dict[str, int] = field(default_factory=dict)
    infection_dose_share_by_route: dict[str, float] = field(default_factory=dict)
    # Cumulative sanitary-mechanism counters copied from
    # TransmissionCore.sanitary_telemetry each epoch (all zeros when
    # sanitary_visit_mode is "none" -- presence is the arm's witness).
    sanitary_activity: dict[str, float] = field(default_factory=dict)
    vsp_reported_case_fraction: float = 0.0
    # Pending escalation: {"to": status, "epoch_triggered": int} or None
    escalation_pending: dict[str, Any] | None = None
    # agent_id → compliant | reluctant | defiant (sticky for the cruise)
    compliance_class_by_agent: dict[int, str] = field(default_factory=dict)
    # Voyage itinerary layer (ship operations)
    voyage_config: dict[str, Any] = field(default_factory=dict)
    epoch_voyage: Any = None  # EpochState | None from engines.voyage_itinerary


# ── Observation engine bundle ────────────────────────────────────────────

@dataclass
class ObservationEngine:
    """Bundle of diagnostic instruments (routine clinical + optional long-read)."""

    air_sniffer: ContinuousAirSniffer
    surface_swab: TargetedSurfaceSwab
    wastewater_seq: WastewaterSequencingGrid
    clin_rdt: ClinicalRapidDiagnostic
    clin_qpcr: ClinicalQPCR
    clin_microbio: ClinicalMicrobiology
    clinical_correlation: ClinicalTestCorrelation
    notebook: ArtificialLabNotebook
    fidelity_name: str
    lab_notebook_enabled: bool
    clin_multiplex: Any = None  # ClinicalMultiplexPanel
    clin_impression: Any = None  # ClinicalImpression
    turnaround: Any = None  # InstrumentTurnaroundQueue
    long_read: LongReadVerificationSequencing | None = None
    wastewater_assay: WastewaterHoldingTankAssay | None = None
    clinical_instrument_params: dict | None = None
    pathogen_profiles: dict | None = None
    outbreak_aware: bool = False


@dataclass
class ObservationResults:
    """Delivered instrument results for one epoch (turnaround already applied)."""

    air: dict[str, dict[str, Any]] = field(default_factory=dict)
    swab: dict[str, dict[str, Any]] = field(default_factory=dict)
    ww: dict[str, dict[str, Any]] = field(default_factory=dict)
    clin_rdt: dict[int, dict[str, Any]] = field(default_factory=dict)
    clin_qpcr: dict[int, dict[str, Any]] = field(default_factory=dict)
    clin_microbio: dict[int, dict[str, Any]] = field(default_factory=dict)
    long_read: dict[str, dict[str, Any]] = field(default_factory=dict)
    long_read_ordered_count: int = 0
    wastewater_ht: dict[str, Any] | None = None
    cascade: dict[str, Any] | None = None


# ── Protocol engine bundle ───────────────────────────────────────────────

@dataclass
class ProtocolContext:
    """Bundle of the reactive protocol engine and cost ledger."""

    protocol_engine: ProtocolEngine
    cost_ledger: CostLedger
    resource_costs_cfg: dict[str, Any]
    standing_protocols: list[Any]
    original_filter_eff: float
    clock: SimClock = field(default_factory=SimClock)
