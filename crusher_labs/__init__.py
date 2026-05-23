"""
crusher_labs – Dr. Crusher's Bio-Diagnostic Suite
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Consumes ground-truth state from ``telemetry_buffer/ground_truth.json``
and returns modality-specific, noise-injected sensor telemetry.
"""

from crusher_labs.modalities.syndromic import SyndromicSurveillance
from crusher_labs.modalities.clinical_rdt import ClinicalRDT
from crusher_labs.modalities.targeted_pcr import TargetedPCR
from crusher_labs.modalities.sequencing import MetagenomicSequencing

ALL_MODALITIES = [
    SyndromicSurveillance,
    ClinicalRDT,
    TargetedPCR,
    MetagenomicSequencing,
]

__all__ = [
    "SyndromicSurveillance",
    "ClinicalRDT",
    "TargetedPCR",
    "MetagenomicSequencing",
    "ALL_MODALITIES",
]
