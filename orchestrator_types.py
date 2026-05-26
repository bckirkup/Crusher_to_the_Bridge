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

from crusher_labs.observation_core import (
    ContinuousAirSniffer,
    TargetedSurfaceSwab,
    WastewaterSequencingGrid,
    ClinicalRapidDiagnostic,
    ClinicalQPCR,
    ClinicalMicrobiology,
)
from crusher_labs.lab_notebook import ArtificialLabNotebook
from crusher_labs.protocol_engine import ProtocolEngine
from crusher_labs.cost_ledger import CostLedger

# ── Trigger status constants ─────────────────────────────────────────────
STATUS_BASELINE = "BASELINE"
STATUS_SUSPECTED = "SUSPECTED"
STATUS_CONFIRMED = "CONFIRMED"

# ── Agent symptom-status constants (used in telemetry schema) ────────────
SYMPTOM_ASYMPTOMATIC = "asymptomatic"
SYMPTOM_SYMPTOMATIC = "symptomatic"
SYMPTOM_ISOLATED = "isolated"
SYMPTOM_QUARANTINED = "quarantined"
SYMPTOM_NON_COMPLIANT = "non_compliant"
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


# ── Observation engine bundle ────────────────────────────────────────────

@dataclass
class ObservationEngine:
    """Bundle of all six diagnostic instruments."""

    air_sniffer: ContinuousAirSniffer
    surface_swab: TargetedSurfaceSwab
    wastewater_seq: WastewaterSequencingGrid
    clin_rdt: ClinicalRapidDiagnostic
    clin_qpcr: ClinicalQPCR
    clin_microbio: ClinicalMicrobiology
    notebook: ArtificialLabNotebook
    fidelity_name: str
    lab_notebook_enabled: bool


# ── Protocol engine bundle ───────────────────────────────────────────────

@dataclass
class ProtocolContext:
    """Bundle of the reactive protocol engine and cost ledger."""

    protocol_engine: ProtocolEngine
    cost_ledger: CostLedger
    resource_costs_cfg: dict[str, Any]
    standing_protocols: list[Any]
    original_filter_eff: float
