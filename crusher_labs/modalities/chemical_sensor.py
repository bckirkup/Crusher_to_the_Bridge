"""Chemical-sensor instruments (ship_function_capacity_spec §8b).

The chemical arm of the observation surface: a fixed continuous detector
(a PID or electrochemical cell) reads substance concentration where the
air and surface pools carry it and answers ``detected`` against a
declared limit of detection. There is no assay machinery here by
design — no Ct, no amplification curve, no QC carryover, no turnaround:
a chemical sensor is a continuous monitor, not a lab test. Wastewater
sequencing stays pathogen-only and gains no hook.

Mass units are the substance's own declared units — the environmental
reservoir emits them and the LOD reads the same units, so the sensor
never needs to know what the substance is.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from simulation_utils.numeric import default_simulation_rng

DEFAULT_NOISE_SIGMA_LOG = 0.1


class ChemicalAirSensor:
    """Continuous point-monitor reading airborne concentration vs LOD."""

    name = "chemical_air_sensor"

    def __init__(
        self,
        lod_mass_per_m3: float,
        noise_sigma_log: float = DEFAULT_NOISE_SIGMA_LOG,
        rng: np.random.Generator | None = None,
    ) -> None:
        if not math.isfinite(lod_mass_per_m3) or lod_mass_per_m3 <= 0:
            raise ValueError(
                f"chemical air sensor lod_mass_per_m3 must be finite and "
                f"positive, got {lod_mass_per_m3!r}",
            )
        if noise_sigma_log < 0:
            raise ValueError(
                f"noise_sigma_log must be non-negative, got {noise_sigma_log}",
            )
        self.lod_mass_per_m3 = float(lod_mass_per_m3)
        self.noise_sigma_log = float(noise_sigma_log)
        self.rng = rng if rng is not None else default_simulation_rng()

    def sample(
        self,
        zone_name: str,
        airborne_mass: float,
        zone_volume_m3: float,
    ) -> dict[str, Any]:
        concentration = airborne_mass / max(float(zone_volume_m3), 1e-9)
        measured = concentration * (
            math.exp(self.rng.normal(0.0, self.noise_sigma_log))
            if self.noise_sigma_log > 0.0
            else 1.0
        )
        return {
            "instrument": self.name,
            "zone": zone_name,
            "airborne_mass": round(airborne_mass, 6),
            "concentration_per_m3": round(concentration, 8),
            "measured_concentration_per_m3": round(measured, 8),
            "lod_mass_per_m3": self.lod_mass_per_m3,
            "detected": measured >= self.lod_mass_per_m3,
        }

    def sample_all_zones(
        self,
        zone_masses: dict[str, float],
        zone_volumes: dict[str, float],
    ) -> dict[str, dict[str, Any]]:
        """Sample every zone the transport carries mass in."""
        return {
            zone: self.sample(
                zone, mass, float(zone_volumes.get(zone, 1.0)),
            )
            for zone, mass in zone_masses.items()
        }


class ChemicalSurfaceSensor:
    """Surface mass-density monitor reading mass per cm² vs LOD."""

    name = "chemical_surface_sensor"

    def __init__(
        self,
        lod_mass_per_cm2: float,
        noise_sigma_log: float = DEFAULT_NOISE_SIGMA_LOG,
        rng: np.random.Generator | None = None,
    ) -> None:
        if not math.isfinite(lod_mass_per_cm2) or lod_mass_per_cm2 <= 0:
            raise ValueError(
                f"chemical surface sensor lod_mass_per_cm2 must be finite "
                f"and positive, got {lod_mass_per_cm2!r}",
            )
        if noise_sigma_log < 0:
            raise ValueError(
                f"noise_sigma_log must be non-negative, got {noise_sigma_log}",
            )
        self.lod_mass_per_cm2 = float(lod_mass_per_cm2)
        self.noise_sigma_log = float(noise_sigma_log)
        self.rng = rng if rng is not None else default_simulation_rng()

    def sample(
        self,
        zone_name: str,
        density_mass_per_cm2: float,
    ) -> dict[str, Any]:
        measured = density_mass_per_cm2 * (
            math.exp(self.rng.normal(0.0, self.noise_sigma_log))
            if self.noise_sigma_log > 0.0
            else 1.0
        )
        return {
            "instrument": self.name,
            "zone": zone_name,
            "surface_density_mass_per_cm2": round(density_mass_per_cm2, 8),
            "measured_density_mass_per_cm2": round(measured, 8),
            "lod_mass_per_cm2": self.lod_mass_per_cm2,
            "detected": measured >= self.lod_mass_per_cm2,
        }

    def sample_all_zones(
        self,
        zone_densities: dict[str, float],
    ) -> dict[str, dict[str, Any]]:
        """Sample every zone the surface pool carries mass in."""
        return {
            zone: self.sample(zone, density)
            for zone, density in zone_densities.items()
        }


def build_chemical_sensors(
    pathogen_profiles: dict[str, dict[str, Any]] | None,
    *,
    seed: int,
) -> dict[str, dict[str, Any]]:
    """Build declared chemical sensors from the merged profile registry.

    Only ``category: "chemical"`` profiles with
    ``chemical_sensor.enabled: true`` produce instruments. Each declared
    modality gets its own seeded stream so an enabled sensor draws
    nothing it would not draw with another sensor disabled.
    """
    sensors: dict[str, dict[str, Any]] = {}
    for index, (pid, profile) in enumerate(
        sorted((pathogen_profiles or {}).items()),
    ):
        if profile.get("category") != "chemical":
            continue
        declaration = profile.get("chemical_sensor") or {}
        if not declaration.get("enabled", False):
            continue
        entry: dict[str, Any] = {}
        air = declaration.get("air")
        if isinstance(air, dict):
            entry["air"] = ChemicalAirSensor(
                lod_mass_per_m3=float(air.get("lod_mass_per_m3", 0.0)),
                noise_sigma_log=float(air.get("noise_sigma_log", 0.0)),
                rng=np.random.default_rng(seed + index * 2),
            )
        surface = declaration.get("surface")
        if isinstance(surface, dict):
            entry["surface"] = ChemicalSurfaceSensor(
                lod_mass_per_cm2=float(surface.get("lod_mass_per_cm2", 0.0)),
                noise_sigma_log=float(
                    surface.get("noise_sigma_log", 0.0),
                ),
                rng=np.random.default_rng(seed + index * 2 + 1),
            )
        if entry:
            sensors[pid] = entry
    return sensors
