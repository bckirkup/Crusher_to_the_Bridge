"""
crusher_labs – Dr. Crusher's Bio-Diagnostic Suite
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Consumes ground-truth state from ``telemetry_buffer/ground_truth.json``
and returns modality-specific, noise-injected sensor telemetry.

Phase 2.5: Full human/clinical envelope with GRUMB seeding, FRED
behavioral compliance, and EMOD clinical progression phases.
"""

from __future__ import annotations

import os
import warnings
from typing import Any

import numpy as np
import yaml

from crusher_labs.clinical_correlation import (
    CLINICAL_TEST_KEYS,
    ClinicalTestCorrelation,
    clinical_diagnostics_params,
)
from crusher_labs.cost_ledger import CostLedger
from crusher_labs.lab_notebook import ArtificialLabNotebook
from crusher_labs.long_read_escalation import (
    collect_long_read_escalation_requests,
    is_long_read_enabled,
    long_read_config,
)
from crusher_labs.modalities.clinical_rdt import ClinicalRDT
from crusher_labs.modalities.long_read_sequencing import LongReadNanoporeSequencing
from crusher_labs.modalities.sequencing import MetagenomicSequencing
from crusher_labs.modalities.syndromic import SyndromicSurveillance
from crusher_labs.modalities.targeted_pcr import TargetedPCR
from crusher_labs.modalities.wearable import WearableDataStream
from crusher_labs.observation_core import (
    DEFAULT_WW_DIRICHLET_CONCENTRATION,
    DEFAULT_WW_PSEUDOCOUNT,
    DEFAULT_WW_READ_DEPTH,
    ClinicalMicrobiology,
    ClinicalQPCR,
    ClinicalRapidDiagnostic,
    ContinuousAirSniffer,
    InstrumentQC,
    TargetedSurfaceSwab,
    WastewaterSequencingGrid,
)
from crusher_labs.protocol_engine import ProtocolEngine
from engines.sim_clock import SimClock, config_epochs_for_hours
from simulation_utils.paths import resolve_repo_path, validated_open

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")


def _warn_legacy_syndromic_units(syndromic: dict[str, Any]) -> None:
    if "sick_call_probability" in syndromic:
        warnings.warn(
            "syndromic.sick_call_probability is deprecated; "
            "use sick_call_probability_per_day",
            DeprecationWarning,
            stacklevel=3,
        )


def _warn_legacy_noise_units(fred_behavior: dict[str, Any]) -> None:
    for category in fred_behavior.get("healthy_noise_categories", []):
        if isinstance(category, dict) and "probability" in category:
            warnings.warn(
                "fred_behavior healthy-noise probability is deprecated; "
                "use probability_per_day",
                DeprecationWarning,
                stacklevel=3,
            )


def _warn_legacy_density_units(transmission: dict[str, Any]) -> None:
    density = transmission.get("density_dependent", {}) or {}
    for key in ("base_contacts", "max_contacts"):
        if key in density:
            warnings.warn(
                f"transmission.density_dependent.{key} is deprecated",
                DeprecationWarning,
                stacklevel=3,
            )


def _warn_legacy_wearable_units(wearable: dict[str, Any]) -> None:
    stack = [wearable]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            if "prevalence" in current:
                warnings.warn(
                    "wearable confounder prevalence is deprecated; "
                    "use prevalence_per_day",
                    DeprecationWarning,
                    stacklevel=3,
                )
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)


def _warn_legacy_config_units(
    cfg: dict[str, Any],
    *,
    include_density: bool = True,
) -> None:
    """Warn once per configuration load for retired day-valued keys."""
    _warn_legacy_syndromic_units(cfg.get("syndromic", {}) or {})
    _warn_legacy_noise_units(cfg.get("fred_behavior", {}) or {})
    if include_density:
        _warn_legacy_density_units(cfg.get("transmission", {}) or {})
    _warn_legacy_wearable_units(cfg.get("wearable_monitoring", {}) or {})


def load_config(path: str = _CONFIG_PATH) -> dict[str, Any]:
    """Load and return the Crusher Labs YAML configuration."""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    resolved = resolve_repo_path(repo_root, path)
    with validated_open(resolved, allowed_roots=(repo_root,), encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    _warn_legacy_config_units(config)
    return config


def wastewater_sequencing_params(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Resolve ``wastewater_sequencing`` instrument parameters from *cfg*."""
    if cfg is None:
        cfg = load_config()
    ww_cfg = cfg.get("wastewater_sequencing", {})
    grumb_cfg = cfg.get("grumb_seeding", {})
    micro_cfg = cfg.get("microflora", {})
    return {
        "read_depth": int(ww_cfg.get("read_depth", DEFAULT_WW_READ_DEPTH)),
        "dirichlet_concentration": float(
            ww_cfg.get("dirichlet_concentration", DEFAULT_WW_DIRICHLET_CONCENTRATION),
        ),
        "pseudocount": float(
            ww_cfg.get("pseudocount", grumb_cfg.get("pseudocount", DEFAULT_WW_PSEUDOCOUNT)),
        ),
        "aitchison_anomaly_threshold": float(
            ww_cfg.get(
                "aitchison_anomaly_threshold",
                micro_cfg.get("aitchison_anomaly_threshold", 0.08),
            ),
        ),
    }


def metagenomic_sequencing_params(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Resolve ``sequencing`` modality parameters from *cfg*."""
    if cfg is None:
        cfg = load_config()
    seq_cfg = cfg.get("sequencing", {})
    micro_cfg = cfg.get("microflora", {})
    grumb_cfg = cfg.get("grumb_seeding", {})
    return {
        "read_depth": int(seq_cfg.get("read_depth", 100_000)),
        "pseudocount": float(
            seq_cfg.get("pseudocount", grumb_cfg.get("pseudocount", 1e-6)),
        ),
        "clr_shift_scale": float(
            seq_cfg.get("clr_shift_scale", micro_cfg.get("clr_shift_scale", 0.15)),
        ),
        "aitchison_anomaly_threshold": float(
            seq_cfg.get(
                "aitchison_anomaly_threshold",
                micro_cfg.get("aitchison_anomaly_threshold", 0.08),
            ),
        ),
    }


def build_modalities(
    cfg: dict[str, Any] | None = None,
    rng: np.random.Generator | None = None,
    total_epochs: int = 24,
    clock: SimClock | None = None,
    pathogen_profiles: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Instantiate all modalities from *cfg*, sharing *rng*.

    Returns a dict keyed by modality name for easy lookup.
    """
    if cfg is None:
        cfg = load_config()
    else:
        _warn_legacy_config_units(cfg, include_density=False)
    if rng is None:
        rng = np.random.default_rng(cfg.get("random_seed", 42))

    syn_cfg = cfg.get("syndromic", {})
    run_clock = clock or SimClock.from_config(cfg)
    rdt_cfg = cfg.get("clinical_rdt", {})
    pcr_cfg = cfg.get("targeted_pcr", {})
    fred_cfg = cfg.get("fred_behavior", {})
    emod_cfg = cfg.get("emod_progression", {})
    seq_params = metagenomic_sequencing_params(cfg)

    reluctant_delay = config_epochs_for_hours(
        fred_cfg, "reluctant_delay_hours", "reluctant_delay_epochs",
        run_clock, default=48,
    )
    compliance_delay = config_epochs_for_hours(
        fred_cfg, "compliance_delay_hours", "compliance_delay_epochs",
        run_clock, default=1,
    )
    detection_delay = config_epochs_for_hours(
        syn_cfg, "detection_delay_hours", "detection_delay_epochs",
        run_clock, default=0,
    )
    screening_interval = config_epochs_for_hours(
        syn_cfg, "crew_screening_interval_hours",
        "crew_screening_interval_epochs", run_clock, default=None,
    )
    return {
        "syndromic": SyndromicSurveillance(
            sick_call_probability=(
                syn_cfg["sick_call_probability"]
                if "sick_call_probability" in syn_cfg
                else syn_cfg.get("sick_call_probability_per_day", 0.70)
            ),
            background_noise_rate=syn_cfg.get("background_noise_rate", 0.015),
            noise_categories=fred_cfg.get("healthy_noise_categories"),
            quarantine_compliance=fred_cfg.get("quarantine_compliance", 0.85),
            compliance_delay_epochs=compliance_delay or 0,
            reluctant_fraction=fred_cfg.get("reluctant_fraction", 0.75),
            reluctant_delay_epochs=reluctant_delay or 0,
            compliance_by_class=fred_cfg.get("compliance_by_class"),
            detection_delay_epochs=detection_delay or 0,
            crew_screening_interval_epochs=screening_interval,
            sick_call_severity_mode=syn_cfg.get(
                "sick_call_severity_mode", "own_severity",
            ),
            symptom_severity_profiles=pathogen_profiles,
            clock=run_clock,
            rng=rng,
        ),
        "clinical_rdt": ClinicalRDT(
            base_sensitivity=rdt_cfg.get("base_sensitivity", 0.95),
            sigmoid_k=rdt_cfg.get("sigmoid_k", 0.08),
            sigmoid_midpoint=rdt_cfg.get("sigmoid_midpoint", 50.0),
            specificity=rdt_cfg.get("specificity", 0.97),
            shedding_phases=emod_cfg.get("shedding_phases"),
            rng=rng,
        ),
        "targeted_pcr": TargetedPCR(
            extraction_efficiency=pcr_cfg.get("extraction_efficiency", 0.35),
            ct_slope=pcr_cfg.get("ct_slope", -3.322),
            ct_intercept=pcr_cfg.get("ct_intercept", 40.0),
            lod_ct_threshold=pcr_cfg.get("lod_ct_threshold", 38.0),
        ),
        "sequencing": MetagenomicSequencing(
            read_depth=seq_params["read_depth"],
            pseudocount=seq_params["pseudocount"],
            clr_shift_scale=seq_params["clr_shift_scale"],
            aitchison_anomaly_threshold=seq_params["aitchison_anomaly_threshold"],
            total_epochs=total_epochs,
            rng=rng,
        ),
    }


ALL_MODALITIES = [
    SyndromicSurveillance,
    ClinicalRDT,
    TargetedPCR,
    MetagenomicSequencing,
    WearableDataStream,
]

ALL_INSTRUMENTS = [
    ContinuousAirSniffer,
    TargetedSurfaceSwab,
    WastewaterSequencingGrid,
    ClinicalRapidDiagnostic,
    ClinicalQPCR,
    ClinicalMicrobiology,
]

__all__ = [
    "SyndromicSurveillance",
    "ClinicalRDT",
    "TargetedPCR",
    "MetagenomicSequencing",
    "LongReadNanoporeSequencing",
    "ContinuousAirSniffer",
    "TargetedSurfaceSwab",
    "WastewaterSequencingGrid",
    "ClinicalRapidDiagnostic",
    "ClinicalQPCR",
    "ClinicalMicrobiology",
    "ClinicalTestCorrelation",
    "CLINICAL_TEST_KEYS",
    "clinical_diagnostics_params",
    "InstrumentQC",
    "ArtificialLabNotebook",
    "ProtocolEngine",
    "CostLedger",
    "WearableDataStream",
    "ALL_MODALITIES",
    "ALL_INSTRUMENTS",
    "build_modalities",
    "load_config",
    "wastewater_sequencing_params",
    "metagenomic_sequencing_params",
    "collect_long_read_escalation_requests",
    "is_long_read_enabled",
    "long_read_config",
    "DEFAULT_WW_READ_DEPTH",
    "DEFAULT_WW_DIRICHLET_CONCENTRATION",
    "DEFAULT_WW_PSEUDOCOUNT",
]
