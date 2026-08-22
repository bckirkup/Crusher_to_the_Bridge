"""Port detection latency derived from existing surveillance capabilities.

The incubation kernel is always projected from the active pathogen profile via
``profile_delays``.  Reporting delay is read from the bundled
``PortSurveillanceCapability``; ports are not re-specified in this package.
The crossing is measured on the uncontrolled trajectory.  This is exact, not
circular, because the controlled and uncontrolled arms are identical at every
epoch strictly before the port's own detection.

The active profile identifiers and the surveillance catalog's public-health
labels are not guaranteed to be identical.  The small translation below
matches catalog labels against the canonical profile name; it is a vocabulary
adapter, not a new surveillance parameter.  Callers still select the port
capability from the existing catalog.
"""

from __future__ import annotations

import math
from typing import Mapping, Sequence

import numpy as np

from picard_framework.analysis.sentinel.incubation import expected_onsets
from picard_framework.analysis.sentinel.port_health import PortSurveillanceCapability
from picard_framework.analysis.sentinel.port_profiles import capability_for
from picard_framework.analysis.sentinel.profile_delays import (
    active_profiles,
    incubation_delay_for_profile,
)


def _capability(
    port_id: str,
    supplied: PortSurveillanceCapability | None,
) -> PortSurveillanceCapability:
    """Use a supplied test capability or the merged bundled catalog."""
    return supplied if supplied is not None else capability_for(port_id)


def _ascertains(
    capability: PortSurveillanceCapability,
    pathogen_id: str,
    profile: Mapping[str, object],
) -> bool:
    """Whether this port's syndromic programme reports these cases at all."""
    profile_name = str(profile.get("name", "")).casefold()
    label = next(
        (
            candidate
            for candidate in capability.syndromic_pathogens
            if candidate.casefold() in profile_name
        ),
        pathogen_id,
    )
    return capability.reports_syndromic(label)


def _reporting_delay_epochs(
    capability: PortSurveillanceCapability,
    *,
    epoch_hours: float,
) -> int:
    """Convert profile reporting days to a conservative whole-epoch delay."""
    days = float(capability.syndromic_delay_days)
    if capability.lab_confirmation:
        days += float(capability.lab_turnaround_days)
    return int(math.ceil(days * 24.0 / float(epoch_hours)))


def port_detection_epoch(
    incidence: Sequence[float] | np.ndarray,
    *,
    port_id: str,
    pathogen_id: str,
    epoch_hours: float,
    case_threshold: float,
    capability: PortSurveillanceCapability | None = None,
    profiles: Mapping[str, Mapping[str, object]] | None = None,
) -> int | None:
    """Return first reported-threshold epoch, or ``None`` if never crossed."""
    if epoch_hours <= 0.0:
        raise ValueError("epoch_hours must be positive")
    if case_threshold < 0.0 or not math.isfinite(float(case_threshold)):
        raise ValueError("case_threshold must be finite and non-negative")
    values = np.asarray(list(incidence), dtype=float)
    if values.size == 0:
        return None
    profile_map = profiles if profiles is not None else active_profiles()
    profile = profile_map.get(pathogen_id)
    if profile is None:
        raise KeyError(f"no active pathogen profile for {pathogen_id!r}")
    delay = incubation_delay_for_profile(profile, epoch_hours=epoch_hours)
    onsets = np.asarray(expected_onsets(values, delay), dtype=float)
    selected = _capability(port_id, capability)
    ascertained = (
        onsets * selected.syndromic_coverage
        if _ascertains(selected, pathogen_id, profile)
        else np.zeros_like(onsets)
    )
    crossed = np.flatnonzero(np.cumsum(ascertained) >= case_threshold)
    if crossed.size == 0:
        return None
    return int(crossed[0]) + _reporting_delay_epochs(selected, epoch_hours=epoch_hours)


def detect_port(
    incidence: Sequence[float] | np.ndarray,
    *,
    port_id: str,
    pathogen_id: str,
    epoch_hours: float,
    case_threshold: float,
    capability: PortSurveillanceCapability | None = None,
    profiles: Mapping[str, Mapping[str, object]] | None = None,
) -> int | None:
    """Descriptive alias for :func:`port_detection_epoch`."""
    return port_detection_epoch(
        incidence,
        port_id=port_id,
        pathogen_id=pathogen_id,
        epoch_hours=epoch_hours,
        case_threshold=case_threshold,
        capability=capability,
        profiles=profiles,
    )
