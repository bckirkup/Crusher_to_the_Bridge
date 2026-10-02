"""Environmental/chemical hazard arm (ship_function_capacity_spec §8).

A chemical hazard (VOC leak, spill) is declared as a pathogen-schema
profile carrying ``category: "chemical"`` and a ``dose_response.model`` of
``cumulative_toxicity``. Transport is the shipped machinery — the
``environmental_contamination`` zone reservoir, per-zone mass pools, and
surface deposition are substance-agnostic. What this module adds is:

- ``merge_environmental_hazard_profiles``: merges voyage-declared hazards
  into the profile registry. The merge is the *only* enablement gate —
  ``environmental_hazards.enabled: false`` (or absent) returns the
  registry untouched, so a declared-disabled run is bit-identical to a
  run that never declared the block.
- ``cumulative_toxicity_spec``: parses the declared Haber c·t threshold
  arm. The effect side (``TransmissionCore._resolve_toxicity_challenge``)
  is a deterministic threshold crossing on the agent's
  ``cumulative_exposure`` ledger — it draws nothing, creates no infection
  record, and sheds nothing. Onset flips ``hazard_symptomatic_active``,
  which lands on the §7 ``symptom_presentation`` seam, so sick-call,
  duty exclusion, OIS, and ``available_for_duty`` see a chemical
  incapacitation identically to an infectious one.
- Pool readers for the chemical-sensor modality surface (§8b): the
  sensor reads substance mass where the transport actually deposits it —
  the environmental reservoir, aerosol pools, multi-pathogen zone mass
  for air; the surface pool for surfaces. Concentration-vs-LOD, never a
  Ct or an amplification curve. Wastewater stays pathogen-only by
  construction: no hook is added there.

Declared, not fitted: every threshold, emission rate and LOD in a hazard
declaration carries a NULL-SOURCE provenance note in
``docs/ship_functions/parameter_sources.md`` unless the declaration cites
a measurement.
"""

from __future__ import annotations

import math
from typing import Any

CUMULATIVE_TOXICITY_MODEL = "cumulative_toxicity"

HAZARD_CATEGORY = "chemical"

# Keys a cumulative-toxicity declaration may carry. ``haber_ct_threshold``
# is the Haber c·t product in the simulation's dose-units accumulated over
# epochs — the quantity ``agent.cumulative_exposure`` books. ``symptomatic``
# (default true) says the crossing produces a symptomatic presentation.
_TOXICITY_KEYS = frozenset({"haber_ct_threshold", "symptomatic"})


def cumulative_toxicity_spec(profile: dict[str, Any]) -> dict[str, Any] | None:
    """Return the parsed cumulative-toxicity declaration, or ``None``.

    ``None`` means the profile does not declare the toxicity arm; a
    malformed declaration raises — silently ignoring a bad threshold
    would let a hazard run as an inert pool.
    """
    dr = profile.get("dose_response") or {}
    if dr.get("model") != CUMULATIVE_TOXICITY_MODEL:
        return None
    unknown = set(dr) - (_TOXICITY_KEYS | {"model"})
    if unknown:
        raise ValueError(
            f"{profile.get('pathogen_id')}: cumulative_toxicity does not "
            f"parameterise {sorted(unknown)}; the Haber arm declares "
            "haber_ct_threshold and symptomatic only",
        )
    threshold = dr.get("haber_ct_threshold")
    if (
        threshold is None
        or not math.isfinite(float(threshold))
        or float(threshold) <= 0.0
    ):
        raise ValueError(
            f"{profile.get('pathogen_id')}: cumulative_toxicity requires a "
            f"finite positive haber_ct_threshold, got {threshold!r}",
        )
    return {
        "haber_ct_threshold": float(threshold),
        "symptomatic": bool(dr.get("symptomatic", True)),
    }


def _validate_hazard_profile(hazard: dict[str, Any]) -> str:
    """Return the hazard id after checking the chemical-arm invariants."""
    pid = hazard.get("pathogen_id")
    if not pid:
        raise ValueError("environmental_hazards entry missing pathogen_id")
    category = hazard.get("category")
    if category != HAZARD_CATEGORY:
        raise ValueError(
            f"{pid}: an environmental_hazards entry must declare "
            f"category 'chemical', got {category!r}",
        )
    spec = cumulative_toxicity_spec(hazard)
    if spec is None:
        raise ValueError(
            f"{pid}: environmental_hazards entries must declare "
            "dose_response.model 'cumulative_toxicity'; chemical "
            "incapacitation does not run through an infection model",
        )
    if hazard.get("initial_infected"):
        raise ValueError(
            f"{pid}: a chemical hazard cannot seed an index case; "
            "initial_infected must be 0 or null",
        )
    if hazard.get("introduction_epoch"):
        raise ValueError(
            f"{pid}: a chemical hazard cannot fiat-introduction a case; "
            "introduction_epoch must be 0 or null (the environmental "
            "reservoir is the emission mechanism)",
        )
    return str(pid)


def merge_environmental_hazard_profiles(
    profiles: dict[str, dict[str, Any]],
    voyage_cfg: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    """Merge voyage-declared chemical hazards into the pathogen registry.

    ``environmental_hazards`` absent or ``enabled: false`` returns the
    registry untouched — the merge is the only enablement gate, so a
    declared-disabled run cannot draw, emit, or export anything a run
    without the block would not.
    """
    block = (voyage_cfg or {}).get("environmental_hazards") or {}
    if not block.get("enabled", False):
        return profiles
    hazards = block.get("hazards") or []
    merged = dict(profiles)
    for hazard in hazards:
        pid = _validate_hazard_profile(hazard)
        if not hazard.get("enabled", True):
            continue
        if pid in merged:
            raise ValueError(
                f"{pid}: an environmental hazard cannot shadow an "
                "existing pathogen profile",
            )
        merged[pid] = hazard
    return merged


def hazard_air_zone_masses(
    tx_core: Any,
    engine: Any,
    pathogen_id: str,
    zone_names: list[str],
) -> dict[str, float]:
    """Per-zone airborne mass of one hazard, summed across every pool.

    A chemical's airborne mass lives wherever transport put it: the
    environmental reservoir (``env_contamination``), the aerosol pools,
    and the multi-pathogen zone mass the HVAC and deposition machinery
    share. Reads only — no mass moves.
    """
    reservoir = tx_core.env_contamination.get(pathogen_id) or {}
    aerosol = tx_core.aerosol_pools_by_pathogen.get(pathogen_id) or {}
    multi = engine.get_pathogen_zone_mass(pathogen_id) or {}
    masses: dict[str, float] = {}
    for zone in zone_names:
        mass = (
            float(reservoir.get(zone, 0.0))
            + float(aerosol.get(zone, 0.0))
            + float(multi.get(zone, 0.0))
        )
        if mass > 0.0:
            masses[zone] = mass
    return masses


def hazard_surface_densities(
    tx_core: Any,
    pathogen_id: str,
    zone_names: list[str],
) -> dict[str, float]:
    """Per-zone surface mass per cm² of high-touch area for one hazard."""
    densities: dict[str, float] = {}
    for zone in zone_names:
        mass = float(tx_core.zone_surface_mass(zone, pathogen_id))
        area = float(tx_core.zone_high_touch_area_cm2(zone))
        if mass > 0.0 and area > 0.0:
            densities[zone] = mass / area
    return densities
