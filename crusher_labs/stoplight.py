"""
crusher_labs.stoplight
~~~~~~~~~~~~~~~~~~~~~~

Canonical stoplight classification functions used by both the
Lab Notebook and the Reactive Protocol Engine.

Stoplight levels:
  GREEN — Clear / Baseline
  AMBER — Elevated Anomaly
  RED   — Critical Hazard / Isolate Immediately
"""

from __future__ import annotations


STOPLIGHT_ORDER: dict[str, int] = {"GREEN": 0, "AMBER": 1, "RED": 2}


def stoplight_from_ct(ct: float | None, detected: bool) -> str:
    """Derive stoplight from a Ct value and detection flag."""
    if not detected or ct is None:
        return "GREEN"
    if ct <= 30:
        return "RED"
    if ct <= 35:
        return "AMBER"
    return "GREEN"


def stoplight_from_anomaly(anomaly_score: float) -> str:
    """Derive stoplight from a metagenomic anomaly score."""
    if anomaly_score >= 0.7:
        return "RED"
    if anomaly_score >= 0.3:
        return "AMBER"
    return "GREEN"


def stoplight_from_rdt(positive: bool) -> str:
    """Derive stoplight from a rapid diagnostic test result."""
    return "RED" if positive else "GREEN"


def stoplight_from_disruption(level: float) -> str:
    """Derive stoplight from a microflora disruption level."""
    if level >= 0.6:
        return "RED"
    if level >= 0.3:
        return "AMBER"
    return "GREEN"


def meets_threshold(actual: str, required: str) -> bool:
    """Return True if *actual* stoplight level meets or exceeds *required*."""
    return STOPLIGHT_ORDER.get(actual, 0) >= STOPLIGHT_ORDER.get(required, 0)
