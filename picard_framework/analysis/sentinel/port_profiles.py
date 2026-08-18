"""Regional libraries of port surveillance capability profiles.

Profiles live in JSON (``data/port_surveillance_<region>.json``) so adding a
cruise region is a data change, not a code change, and so the capability of a
real port can be corrected against a citation without touching the model.

The regions are the four cruise theatres the sentinel scan uses: the Caribbean
(the surveillance desert the ship is meant to fill), the Mediterranean and the
Nordic ports (dense municipal WBE, so the validation correlation is computable),
and Alaska (US-flag reporting with sparse municipal infrastructure).
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any, Mapping

from picard_framework.analysis._io import read_json
from picard_framework.analysis.sentinel.port_health import PortSurveillanceCapability

REGION_CARIBBEAN = "caribbean"
REGION_MEDITERRANEAN = "mediterranean"
REGION_NORDIC = "nordic"
REGION_ALASKA = "alaska"
PROFILE_REGIONS: tuple[str, ...] = (
    REGION_CARIBBEAN,
    REGION_MEDITERRANEAN,
    REGION_NORDIC,
    REGION_ALASKA,
)

_PROFILE_KEY = "port_surveillance_profiles"


def _profile_filename(region: str) -> str:
    return f"port_surveillance_{region}.json"


def _packaged_profiles(region: str) -> dict[str, Any]:
    root = resources.files("picard_framework.analysis.sentinel")
    text = (root / "data" / _profile_filename(region)).read_text(encoding="utf-8")
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError(f"{_profile_filename(region)} must contain an object")
    return parsed


def _entries(raw: Mapping[str, Any], source: str) -> dict[str, Any]:
    block = raw.get(_PROFILE_KEY)
    if not isinstance(block, dict) or not block:
        raise ValueError(f"{source} declares no {_PROFILE_KEY!r}")
    return dict(block)


def load_region_profiles(
    region: str,
    *,
    path: str | None = None,
) -> dict[str, PortSurveillanceCapability]:
    """Capabilities for one region, keyed by UN-LOCODE."""
    key = str(region).strip().lower()
    if path is None and key not in PROFILE_REGIONS:
        raise ValueError(
            f"unknown port profile region {region!r}; known: {list(PROFILE_REGIONS)}",
        )
    raw = _packaged_profiles(key) if path is None else read_json(path)
    if not isinstance(raw, dict):
        raise ValueError(f"port profile source {path or key} must be an object")
    return {
        port_id: PortSurveillanceCapability.from_mapping(entry, port_id=port_id)
        for port_id, entry in _entries(raw, path or key).items()
    }


@lru_cache(maxsize=1)
def _catalog() -> dict[str, PortSurveillanceCapability]:
    merged: dict[str, PortSurveillanceCapability] = {}
    for region in PROFILE_REGIONS:
        for port_id, capability in load_region_profiles(region).items():
            if port_id in merged:
                raise ValueError(
                    f"port {port_id} is declared in more than one region profile",
                )
            merged[port_id] = capability
    return merged


def load_all_profiles() -> dict[str, PortSurveillanceCapability]:
    """Every bundled port, all regions, keyed by UN-LOCODE."""
    return dict(_catalog())


def capability_for(port_id: str) -> PortSurveillanceCapability:
    """Look a port up across all bundled regions."""
    key = str(port_id).strip().upper()
    catalog = _catalog()
    if key not in catalog:
        raise KeyError(
            f"no port surveillance profile for {port_id!r}; "
            "add it to a data/port_surveillance_<region>.json library",
        )
    return catalog[key]


def capability_or_default(
    port_id: str,
    *,
    population: int = 100_000,
    region: str = "",
) -> PortSurveillanceCapability:
    """A bundled profile, or a minimally-capable stand-in for an unlisted port.

    Every port must produce signals (the whole point is that the data exists
    even where the programme does not), so an itinerary that calls somewhere
    unprofiled gets a local-only authority rather than a hole in the ledger.
    """
    try:
        return capability_for(port_id)
    except KeyError:
        key = str(port_id).strip().upper()
        return PortSurveillanceCapability(
            port_id=key,
            port_name=key,
            region=str(region),
            population=int(population),
        )
