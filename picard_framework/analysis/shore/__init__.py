"""Deterministic shore-side post-processing for port-call importations.

This package is deliberately a renewal layer rather than a second agent-based
model.  It consumes infectious disembarkations and shipboard detection from a
single explicit ship interface, while incubation and port reporting latency
come from the existing canonical profile libraries.
"""

from __future__ import annotations

from picard_framework.analysis.shore.counterfactual import (
    CounterfactualResult,
    ShoreArmResult,
    evaluate_counterfactual,
)
from picard_framework.analysis.shore.detection import (
    detect_port,
    port_detection_epoch,
)
from picard_framework.analysis.shore.importation import PortCallImportation
from picard_framework.analysis.shore.renewal import (
    DEPLETION_FRACTION,
    ShoreRenewalParameters,
    ShoreRenewalResult,
    renewal_by_strain,
    renewal_result,
    renewal_trajectory,
)
from picard_framework.analysis.shore.sweep import benefit_surface

__all__ = [
    "CounterfactualResult",
    "DEPLETION_FRACTION",
    "PortCallImportation",
    "ShoreArmResult",
    "ShoreRenewalParameters",
    "ShoreRenewalResult",
    "benefit_surface",
    "detect_port",
    "evaluate_counterfactual",
    "port_detection_epoch",
    "renewal_by_strain",
    "renewal_result",
    "renewal_trajectory",
]
