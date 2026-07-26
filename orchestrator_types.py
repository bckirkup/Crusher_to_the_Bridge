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
    WastewaterSequencingGrid,
)
from crusher_labs.protocol_engine import ProtocolEngine

# ── Trigger status constants ─────────────────────────────────────────────
STATUS_BASELINE = "BASELINE"
STATUS_SUSPECTED = "SUSPECTED"
STATUS_CONFIRMED = "CONFIRMED"

# ── Agent orthogonal status axes (telemetry_buffer.agent_axes) ───────────
from telemetry_buffer.agent_axes import (  # noqa: E402,F401
    INFECTION_SUSCEPTIBLE,
    INFECTION_INFECTED,
    INFECTION_RECOVERED,
    INFECTION_IMMUNE,
    PRESENTATION_ASYMPTOMATIC,
    PRESENTATION_MILD,
    PRESENTATION_SYMPTOMATIC,
    PRESENTATION_SEVERE,
    COMPLIANCE_COMPLIANT,
    COMPLIANCE_NON_COMPLIANT,
    COMPLIANCE_ISOLATED,
    COMPLIANCE_QUARANTINED,
    PRESENTATION_SYMPTOMATIC_LEVELS,
)

# Deprecated aliases — legacy combined ``symptom_status`` string values
SYMPTOM_ASYMPTOMATIC = PRESENTATION_ASYMPTOMATIC
SYMPTOM_SYMPTOMATIC = PRESENTATION_SYMPTOMATIC
SYMPTOM_ISOLATED = COMPLIANCE_ISOLATED
SYMPTOM_QUARANTINED = COMPLIANCE_QUARANTINED
SYMPTOM_NON_COMPLIANT = COMPLIANCE_NON_COMPLIANT
SYMPTOM_ASYMPTOMATIC_SHEDDING = "asymptomatic_shedding"

# ── Synthetic locations for confined agents ──────────────────────────────
LOCATION_ISOLATED = "Isolated_In_Quarters"
LOCATION_QUARANTINED = "Quarantined_In_Quarters"

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
    clinical_instrument_params: dict | None = None
    pathogen_profiles: dict | None = None
    outbreak_aware: bool = False


# ── Protocol engine bundle ───────────────────────────────────────────────

@dataclass
class ProtocolContext:
    """Bundle of the reactive protocol engine and cost ledger."""

    protocol_engine: ProtocolEngine
    cost_ledger: CostLedger
    resource_costs_cfg: dict[str, Any]
    standing_protocols: list[Any]
    original_filter_eff: float
