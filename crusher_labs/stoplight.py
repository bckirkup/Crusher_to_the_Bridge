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


def stoplight_from_long_read_verification(result: dict[str, Any]) -> str:
    """Map long-read escalation output to stoplight (framework stub → AMBER)."""
    if result.get("pathogen_calls"):
        return "RED"
    if result.get("status") == "framework_stub":
        return "AMBER"
    if result.get("consensus_ready"):
        return "GREEN"
    return "AMBER"


def stoplight_from_wearable_agent(
    fever: bool,
    anomaly_count: int,
) -> str:
    """Derive per-agent stoplight from wearable physiological signals."""
    if fever or anomaly_count >= 2:
        return "RED"
    if anomaly_count >= 1:
        return "AMBER"
    return "GREEN"


def stoplight_from_wearable_fleet_rates(
    fever_rate: float,
    anomaly_rate: float,
    *,
    amber_fever_rate: float = 0.03,
    red_fever_rate: float = 0.08,
    amber_anomaly_rate: float = 0.05,
    red_anomaly_rate: float = 0.12,
) -> str:
    """Derive shipwide fleet stoplight from aggregate wearable rates."""
    if fever_rate >= red_fever_rate or anomaly_rate >= red_anomaly_rate:
        return "RED"
    if fever_rate >= amber_fever_rate or anomaly_rate >= amber_anomaly_rate:
        return "AMBER"
    return "GREEN"


def stoplight_from_sick_call_count(
    sick_call_count: int,
    *,
    amber_threshold: int = 2,
    red_threshold: int = 5,
) -> str:
    """Derive syndromic detection-mode stoplight from daily sick-call volume."""
    if sick_call_count >= red_threshold:
        return "RED"
    if sick_call_count >= amber_threshold:
        return "AMBER"
    return "GREEN"


def aggregate_stoplight_max(levels: list[str]) -> str:
    """Return the most severe stoplight in *levels* (GREEN if empty)."""
    if not levels:
        return "GREEN"
    return max(levels, key=lambda lvl: STOPLIGHT_ORDER.get(lvl, 0))


def meets_threshold(actual: str, required: str) -> bool:
    """Return True if *actual* stoplight level meets or exceeds *required*."""
    return STOPLIGHT_ORDER.get(actual, 0) >= STOPLIGHT_ORDER.get(required, 0)
