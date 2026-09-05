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
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from picard_framework.runs.mega_cruise_campaign.boarding_axis import (
    IndexCaseAxis,
)

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


def embarks_clean(hazards: dict[str, Any], r_onboard: float) -> bool:
    """Whether the voyage starts with nobody infected aboard.

    Shore-seeded when any λ_p > 0, so the recovered port hazard is not
    confounded by importation; also clean when there is neither a hazard nor
    any onboard transmission to observe. Only the onboard-only confound arm
    (no hazard, R_onboard > 0) embarks with infection aboard.
    """
    if any(float(v) > 0.0 for v in hazards.values()):
        return True
    return float(r_onboard) <= 0.0


@dataclass(frozen=True)
class OnboardSeeding:
    """How one sentinel run starts: a profile patch and its parameter labels."""

    pathogen_patch: dict[str, Any]
    factors: dict[str, Any]


def onboard_seeding(
    hazards: dict[str, Any],
    r_onboard: float,
    pathogen_id: str,
    tier: dict[str, Any],
) -> OnboardSeeding:
    """The run's onboard seeding for this pathogen.

    A pathogen initiation owns embarks through the boarding channel: the
    confound arm boards at the tier's single coordinate point, and a clean
    embarkation is a zero boarding prevalence for both roles rather than a
    fiat count of zero. Any other pathogen keeps its one fiat index case for
    the confound arm and zero otherwise, as before.
    """
    axis = IndexCaseAxis.for_tier(tier, pathogen_id, legacy_default=1)
    if len(axis.points) != 1:
        raise ValueError(
            f"sentinel recovery tier sweeps {len(axis.points)} index-case "
            f"points for {pathogen_id}; its run ids are keyed by port hazard "
            "and R_onboard alone, so it takes exactly one",
        )
    clean = embarks_clean(hazards, r_onboard)
    point = axis.points[0]
    if not axis.boarding:
        n_init = 0 if clean else int(point)
        return OnboardSeeding({"initial_infected": n_init}, {"n_init": n_init})
    if clean:
        point = replace(point, passenger_prevalence=0.0, crew_prevalence=0.0)
    return OnboardSeeding({}, axis.factors(point))


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
