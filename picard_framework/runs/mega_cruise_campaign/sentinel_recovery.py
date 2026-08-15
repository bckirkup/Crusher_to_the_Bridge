"""Sentinel synthetic-recovery helpers (port-hazard × R_onboard × fleet).

Turns ``sentinel_synthetic_recovery_v1`` tiers into voyage overrides: known
``shore_infection_probability`` per UN-LOCODE, the itinerary template named by
the tier, and a contact-rate scale that stands in for known ``R_onboard``.

Itinerary templates live in the manifest (expanded from the campaign design
spec by :mod:`expand_design`) rather than in this module, so running a
different region is a configuration change, not a code change.
"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

CAMPAIGN_DIR = Path(__file__).resolve().parent
REPO_ROOT = CAMPAIGN_DIR.parents[2]
_FLEET_SUFFIXES = ("fleet_crossed", "fleet_same", "single")
_DEFAULT_EMBARKATION_DATE = "2026-01-10"
_NOMINAL_CONTACT = {
    "sea_day": 1.0,
    "port_day": 0.40,
    "embarkation": 1.2,
    "disembarkation": 0.2,
}


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


def itinerary_days(manifest: dict[str, Any], variant: str) -> list[dict[str, Any]]:
    """Day slots for the named itinerary template declared in the manifest."""
    templates = manifest.get("itinerary_templates") or {}
    name = str(variant or "standard")
    if name not in templates:
        raise ValueError(
            f"manifest declares no itinerary template {name!r}; regenerate it "
            "from the campaign design spec with expand_design",
        )
    return [copy.deepcopy(day) for day in templates[name]]


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
    embarkation_date: str = _DEFAULT_EMBARKATION_DATE,
) -> dict[str, Any]:
    """Picard ``config_overrides.voyage`` for one sentinel recovery run."""
    return {
        "effects_enabled": True,
        "total_epochs": int(epochs),
        "epoch_duration_hours": 1,
        "embarkation_date": str(embarkation_date),
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
