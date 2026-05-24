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
from typing import Any

import numpy as np
import yaml

from crusher_labs.modalities.syndromic import SyndromicSurveillance
from crusher_labs.modalities.clinical_rdt import ClinicalRDT
from crusher_labs.modalities.targeted_pcr import TargetedPCR
from crusher_labs.modalities.sequencing import MetagenomicSequencing
from crusher_labs.observation_core import (
    ContinuousAirSniffer,
    TargetedSurfaceSwab,
    WastewaterSequencingGrid,
)
from crusher_labs.lab_notebook import ArtificialLabNotebook

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")


def load_config(path: str = _CONFIG_PATH) -> dict[str, Any]:
    """Load and return the Crusher Labs YAML configuration."""
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def build_modalities(
    cfg: dict[str, Any] | None = None,
    rng: np.random.Generator | None = None,
    total_epochs: int = 24,
) -> dict[str, Any]:
    """Instantiate all modalities from *cfg*, sharing *rng*.

    Returns a dict keyed by modality name for easy lookup.
    """
    if cfg is None:
        cfg = load_config()
    if rng is None:
        rng = np.random.default_rng(cfg.get("random_seed", 42))

    syn_cfg = cfg.get("syndromic", {})
    rdt_cfg = cfg.get("clinical_rdt", {})
    pcr_cfg = cfg.get("targeted_pcr", {})
    seq_cfg = cfg.get("sequencing", {})
    fred_cfg = cfg.get("fred_behavior", {})
    emod_cfg = cfg.get("emod_progression", {})

    return {
        "syndromic": SyndromicSurveillance(
            sick_call_probability=syn_cfg.get("sick_call_probability", 0.70),
            background_noise_rate=syn_cfg.get("background_noise_rate", 0.015),
            noise_categories=fred_cfg.get("healthy_noise_categories"),
            quarantine_compliance=fred_cfg.get("quarantine_compliance", 0.85),
            compliance_delay_epochs=fred_cfg.get("compliance_delay_epochs", 1),
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
            read_depth=seq_cfg.get("read_depth", 100_000),
            pseudocount=seq_cfg.get("pseudocount", 1e-6),
            total_epochs=total_epochs,
            rng=rng,
        ),
    }


ALL_MODALITIES = [
    SyndromicSurveillance,
    ClinicalRDT,
    TargetedPCR,
    MetagenomicSequencing,
]

ALL_INSTRUMENTS = [
    ContinuousAirSniffer,
    TargetedSurfaceSwab,
    WastewaterSequencingGrid,
]

__all__ = [
    "SyndromicSurveillance",
    "ClinicalRDT",
    "TargetedPCR",
    "MetagenomicSequencing",
    "ContinuousAirSniffer",
    "TargetedSurfaceSwab",
    "WastewaterSequencingGrid",
    "ArtificialLabNotebook",
    "ALL_MODALITIES",
    "ALL_INSTRUMENTS",
    "build_modalities",
    "load_config",
]
