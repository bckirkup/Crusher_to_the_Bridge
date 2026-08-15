"""Sentinel synthetic-recovery helpers (port-hazard × R_onboard × fleet).

Turns ``sentinel_synthetic_recovery_v1`` tiers into voyage overrides: known
``shore_infection_probability`` per UN-LOCODE, itinerary variants for fleet
crossover, and a contact-rate scale that stands in for known ``R_onboard``.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from simulation_utils.paths import validated_open

CAMPAIGN_DIR = Path(__file__).resolve().parent
REPO_ROOT = CAMPAIGN_DIR.parents[2]
_EXAMPLE_ITINERARY = (
    REPO_ROOT
    / "picard_framework"
    / "analysis"
    / "sentinel"
    / "data"
    / "example_itinerary.json"
)
_FLEET_SUFFIXES = ("fleet_crossed", "fleet_same", "single")
_PORT_FIELDS = (
    "port",
    "port_id",
    "region",
    "disembark_fraction",
    "crew_shore_leave_fraction",
    "disembark_window_epochs",
    "reembark_window_epochs",
    "shore_infection_probability",
    "shore_pathogen",
)
_NOMINAL_CONTACT = {
    "sea_day": 1.0,
    "port_day": 0.40,
    "embarkation": 1.2,
    "disembarkation": 0.2,
}
_EMBARKATION_DATE = "2026-01-10"


def is_sentinel_recovery_tier(tier: dict[str, Any]) -> bool:
    """True when the tier is a port-hazard recovery cell, not ridge sr*."""
    return "R_onboard_values" in tier or "shore_exposure" in tier


def tier_cartesian(tier: dict[str, Any]) -> int:
    """One run per platform × R_onboard × seed (itinerary is 1:1 with platform)."""
    plats = tier.get("platforms") or ([tier["platform"]] if "platform" in tier else [1])
    return len(plats) * len(tier["R_onboard_values"]) * len(tier["seeds"])


def r_onboard_tag(value: float) -> str:
    """Compact run-id fragment, e.g. 0.5 → R0p5."""
    return "R" + str(float(value)).replace(".", "p")


def parse_tier_labels(tier_id: str, tier: dict[str, Any]) -> tuple[str, str]:
    """Return (hazard_profile, fleet_config) from explicit keys or the tier id."""
    hazard = str(tier.get("hazard_profile") or "")
    fleet = str(tier.get("fleet_config") or "")
    if hazard and fleet:
        return hazard, fleet
    rest = tier_id[3:] if tier_id.startswith("sr_") else tier_id
    for suffix in _FLEET_SUFFIXES:
        token = "_" + suffix
        if rest.endswith(token):
            return rest[: -len(token)], suffix
    return rest, "single"


def initial_infected(hazards: dict[str, Any], r_onboard: float) -> int:
    """Shore-seeded when any λ_p > 0; one index case for onboard-only confound."""
    if any(float(v) > 0.0 for v in hazards.values()):
        return 0
    return 1 if float(r_onboard) > 0.0 else 0


def load_standard_itinerary() -> list[dict[str, Any]]:
    """Western Caribbean 7-day template (MXCZM / MXCTM / KYGEC)."""
    with validated_open(
        str(_EXAMPLE_ITINERARY),
        encoding="utf-8",
        allowed_roots=(str(REPO_ROOT),),
    ) as fh:
        raw = json.load(fh)
    days = list((raw.get("voyage") or {}).get("itinerary") or [])
    return [copy.deepcopy(day) for day in days]


def overlay_port(slot: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    """Copy port metadata onto a day slot, keeping the slot's day number."""
    out = dict(slot)
    for key in _PORT_FIELDS:
        if key in source:
            out[key] = copy.deepcopy(source[key])
        elif key in out:
            del out[key]
    return out


def apply_itinerary_variant(
    days: list[dict[str, Any]],
    variant: str,
) -> list[dict[str, Any]]:
    """standard = template; reversed = reverse port order; staggered = earlier ports."""
    name = str(variant or "standard")
    cloned = [copy.deepcopy(day) for day in days]
    if name == "standard":
        return cloned
    if name == "reversed":
        return _reverse_port_order(cloned)
    if name == "staggered":
        return _stagger_port_days(cloned)
    raise ValueError(f"unknown itinerary variant: {name}")


def stamp_port_hazards(
    days: list[dict[str, Any]],
    hazards: dict[str, Any],
) -> list[dict[str, Any]]:
    """Set ``shore_infection_probability`` from known λ_p keyed by port_id."""
    out: list[dict[str, Any]] = []
    for day in days:
        entry = copy.deepcopy(day)
        port_id = str(entry.get("port_id") or "")
        if port_id in hazards:
            entry["shore_infection_probability"] = float(hazards[port_id])
        out.append(entry)
    return out


def contact_defaults_for(r_onboard: float) -> dict[str, Any]:
    """Scale platform-class contact multipliers by known R_onboard (1.0 = nominal)."""
    scale = float(r_onboard)
    return {
        day_type: {"contact_rate_multiplier": nominal * scale}
        for day_type, nominal in _NOMINAL_CONTACT.items()
    }


def voyage_override(
    *,
    days: list[dict[str, Any]],
    r_onboard: float,
    epochs: int,
) -> dict[str, Any]:
    """Picard ``config_overrides.voyage`` for one sentinel recovery run."""
    return {
        "effects_enabled": True,
        "total_epochs": int(epochs),
        "epoch_duration_hours": 1,
        "embarkation_date": _EMBARKATION_DATE,
        "shore_exposure": {"enabled": True},
        "defaults": contact_defaults_for(r_onboard),
        "itinerary": days,
    }


def itinerary_for_platform(
    tier: dict[str, Any],
    platform_index: int,
) -> str:
    """Itinerary name aligned with ``platforms[i]``; default standard."""
    names = list(tier.get("itineraries") or ["standard"])
    if not names:
        return "standard"
    if platform_index < len(names):
        return str(names[platform_index])
    return str(names[-1])


def _reverse_port_order(days: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ports = [day for day in days if day.get("type") == "port_day"]
    ports.reverse()
    cursor = iter(ports)
    out: list[dict[str, Any]] = []
    for day in days:
        if day.get("type") == "port_day":
            out.append(overlay_port(day, next(cursor)))
        else:
            out.append(day)
    return out


def _stagger_port_days(days: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Shift ports one day earlier on the 7-day template: 3/4/6 → 2/4/5."""
    by_day = {int(day["day"]): day for day in days}
    ports = [
        by_day[day]
        for day in sorted(by_day)
        if by_day[day].get("type") == "port_day"
    ]
    sea = next(
        by_day[day] for day in sorted(by_day) if by_day[day].get("type") == "sea_day"
    )
    shifted = {2: ports[0], 3: sea, 4: ports[1], 5: ports[2], 6: sea}
    out: list[dict[str, Any]] = []
    for day in sorted(by_day):
        entry = copy.deepcopy(by_day[day])
        if day in shifted:
            source = shifted[day]
            entry["type"] = source["type"]
            entry["day"] = day
            if source["type"] == "port_day":
                entry = overlay_port(entry, source)
                entry["day"] = day
            else:
                for key in _PORT_FIELDS:
                    entry.pop(key, None)
        out.append(entry)
    return out
