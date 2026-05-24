"""
crusher_labs.observation_core
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Instrument-level sampling modules for the Crusher Labs Observation Engine.

Three physical diagnostic instruments simulate realistic, noisy telemetry
from the ship's environmental and biological monitoring infrastructure:

1. **ContinuousAirSniffer** — real-time aerosol Ct from room airborne
   mass pools, scaled by filter efficiency and volume sampled per epoch.

2. **TargetedSurfaceSwab** — surface PCR from fomite/surface mass pools,
   with stochastic collection-efficiency variance driven by FRED-style
   human compliance and technique quality.

3. **WastewaterSequencingGrid** — pooled metagenomic sampling of
   pathogen mass + disrupted microflora from greywater/blackwater lines.
   Uses Dirichlet-multinomial sampling to convert GRUMB log-ratio
   abundance arrays into simulated relative-abundance tables.

All instruments interface with the TransmissionCore surface/aerosol pools,
the py-contam HVAC transport layer, and the GRUMB compositional math.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np


# ── Constants ────────────────────────────────────────────────────────────

DEFAULT_CT_SLOPE = -3.322       # k in Ct = -k * log10(M) + b
DEFAULT_CT_INTERCEPT = 40.0     # b (Ct at 1 unit of recovered mass)
DEFAULT_LOD_CT = 38.0           # Ct > this => Negative

# Air sniffer default parameters
AIR_SNIFFER_VOLUME_FRACTION = 0.05   # fraction of room volume sampled/epoch
AIR_SNIFFER_FILTER_EFF = 0.85        # capture efficiency of the sniffer filter

# Surface swab default parameters
SWAB_NOMINAL_EFF = 0.35              # nominal collection efficiency
SWAB_GOOD_TECHNIQUE_VARIANCE = 0.05  # low variance for careful technique
SWAB_POOR_TECHNIQUE_VARIANCE = 0.20  # high variance for rushed technique
SWAB_AREA_CM2 = 100.0               # default swab area (10cm x 10cm)

# Wastewater sequencing defaults
WW_READ_DEPTH = 50_000              # sequencing reads per wastewater sample
WW_DIRICHLET_CONCENTRATION = 100.0  # Dirichlet concentration (overdispersion)
WW_PSEUDOCOUNT = 1e-6


# ── Multi-kingdom taxa for wastewater (shared with sequencing.py) ────────

MULTI_KINGDOM_TAXA: dict[str, dict[str, float]] = {
    "Bacteria": {
        "Vibrio_spp":           0.10,
        "Pseudoalteromonas":    0.08,
        "Enterobacter":         0.06,
        "Acinetobacter":        0.05,
        "Shewanella":           0.04,
        "Bacillus_subtilis":    0.04,
        "Staphylococcus_epi":   0.03,
    },
    "Archaea": {
        "Nitrosopumilus":       0.03,
        "Halobacterium":        0.02,
        "Methanobrevibacter":   0.01,
    },
    "Fungi": {
        "Aspergillus_spp":     0.02,
        "Cladosporium":        0.02,
        "Candida_spp":         0.01,
    },
    "Virus": {
        "Phage_community":     0.04,
        "ssRNA_marine":        0.02,
    },
}


# ── Instrument 1: Continuous Air Sniffer ─────────────────────────────────

class ContinuousAirSniffer:
    """Real-time aerosol detection via continuous air sampling.

    Draws a fraction of the room's airborne mass pool each epoch,
    applies an instrument filter-capture efficiency, then maps
    the captured mass to a Ct value using the standard logarithmic
    PCR curve.  Produces per-zone Ct readings at every epoch.
    """

    name = "air_sniffer"

    def __init__(
        self,
        volume_fraction: float = AIR_SNIFFER_VOLUME_FRACTION,
        filter_efficiency: float = AIR_SNIFFER_FILTER_EFF,
        ct_slope: float = DEFAULT_CT_SLOPE,
        ct_intercept: float = DEFAULT_CT_INTERCEPT,
        lod_ct: float = DEFAULT_LOD_CT,
        rng: np.random.Generator | None = None,
    ) -> None:
        self.volume_fraction = volume_fraction
        self.filter_efficiency = filter_efficiency
        self.ct_slope = ct_slope
        self.ct_intercept = ct_intercept
        self.lod_ct = lod_ct
        self.rng = rng if rng is not None else np.random.default_rng()

    def sample(
        self,
        zone_name: str,
        airborne_mass: float,
        zone_volume_m3: float = 100.0,
    ) -> dict[str, Any]:
        """Sample the airborne mass pool for one zone at one epoch.

        Parameters
        ----------
        zone_name : str
            Zone identifier.
        airborne_mass : float
            Total airborne pathogen mass in the room (copies).
        zone_volume_m3 : float
            Room volume in cubic meters.
        """
        sampled_volume = zone_volume_m3 * self.volume_fraction
        concentration = airborne_mass / max(zone_volume_m3, 1.0)

        captured_mass = concentration * sampled_volume * self.filter_efficiency

        # Add instrument noise (log-normal, ~5% CV)
        noise_mult = self.rng.lognormal(0, 0.05)
        captured_mass *= noise_mult

        ct = self._compute_ct(captured_mass)
        detected = ct is not None and ct <= self.lod_ct

        return {
            "instrument": self.name,
            "zone": zone_name,
            "airborne_mass": round(airborne_mass, 4),
            "sampled_volume_m3": round(sampled_volume, 2),
            "concentration_per_m3": round(concentration, 6),
            "captured_mass": round(captured_mass, 4),
            "ct_value": ct,
            "detected": detected,
        }

    def sample_all_zones(
        self,
        zone_masses: dict[str, float],
        zone_volumes: dict[str, float],
    ) -> dict[str, dict[str, Any]]:
        """Run continuous air sampling across all zones."""
        results: dict[str, dict[str, Any]] = {}
        for zone_name, mass in zone_masses.items():
            vol = zone_volumes.get(zone_name, 100.0)
            results[zone_name] = self.sample(zone_name, mass, vol)
        return results

    def _compute_ct(self, mass: float) -> float | None:
        if mass <= 0:
            return None
        ct = self.ct_slope * math.log10(mass) + self.ct_intercept
        return round(ct, 2)


# ── Instrument 2: Targeted Surface Swab ──────────────────────────────────

class TargetedSurfaceSwab:
    """Surface PCR via targeted swab collection.

    Reads from the room's fomite/surface mass pool.  The collection
    efficiency is stochastic: when human compliance is low or the
    technique is rushed, the variance widens to simulate poor
    swabbing technique.

    The FRED compliance scalar modulates the technique quality:
    - compliance >= 0.8: careful technique (low variance)
    - compliance < 0.8: rushed technique (high variance)
    """

    name = "surface_swab"

    def __init__(
        self,
        nominal_efficiency: float = SWAB_NOMINAL_EFF,
        good_variance: float = SWAB_GOOD_TECHNIQUE_VARIANCE,
        poor_variance: float = SWAB_POOR_TECHNIQUE_VARIANCE,
        swab_area_cm2: float = SWAB_AREA_CM2,
        ct_slope: float = DEFAULT_CT_SLOPE,
        ct_intercept: float = DEFAULT_CT_INTERCEPT,
        lod_ct: float = DEFAULT_LOD_CT,
        rng: np.random.Generator | None = None,
    ) -> None:
        self.nominal_efficiency = nominal_efficiency
        self.good_variance = good_variance
        self.poor_variance = poor_variance
        self.swab_area_cm2 = swab_area_cm2
        self.ct_slope = ct_slope
        self.ct_intercept = ct_intercept
        self.lod_ct = lod_ct
        self.rng = rng if rng is not None else np.random.default_rng()

    def swab(
        self,
        zone_name: str,
        surface_mass: float,
        compliance_scalar: float = 0.85,
    ) -> dict[str, Any]:
        """Perform a surface swab on a zone.

        Parameters
        ----------
        zone_name : str
            Zone identifier.
        surface_mass : float
            Total surface pathogen mass in the room (copies).
        compliance_scalar : float
            FRED compliance metric [0..1].  Controls technique quality.
        """
        # Select variance based on compliance
        if compliance_scalar >= 0.8:
            variance = self.good_variance
            technique = "careful"
        else:
            variance = self.poor_variance
            technique = "rushed"

        # Stochastic collection efficiency: clipped normal around nominal
        actual_efficiency = self.rng.normal(self.nominal_efficiency, variance)
        actual_efficiency = float(np.clip(actual_efficiency, 0.05, 0.95))

        recovered_mass = surface_mass * actual_efficiency

        # Add instrument noise
        noise_mult = self.rng.lognormal(0, 0.03)
        recovered_mass *= noise_mult

        ct = self._compute_ct(recovered_mass)
        detected = ct is not None and ct <= self.lod_ct

        return {
            "instrument": self.name,
            "zone": zone_name,
            "surface_mass": round(surface_mass, 4),
            "compliance_scalar": round(compliance_scalar, 3),
            "technique_quality": technique,
            "actual_collection_efficiency": round(actual_efficiency, 4),
            "recovered_mass": round(recovered_mass, 4),
            "ct_value": ct,
            "detected": detected,
        }

    def swab_zones(
        self,
        zone_surface_masses: dict[str, float],
        compliance_scalar: float = 0.85,
        target_zones: list[str] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Run surface swabs across targeted zones."""
        targets = target_zones if target_zones else list(zone_surface_masses.keys())
        results: dict[str, dict[str, Any]] = {}
        for zone_name in targets:
            mass = zone_surface_masses.get(zone_name, 0.0)
            results[zone_name] = self.swab(zone_name, mass, compliance_scalar)
        return results

    def _compute_ct(self, mass: float) -> float | None:
        if mass <= 0:
            return None
        ct = self.ct_slope * math.log10(mass) + self.ct_intercept
        return round(ct, 2)


# ── Instrument 3: Wastewater Sequencing Grid ─────────────────────────────

def _clr_transform(x: np.ndarray, pseudocount: float = 1e-6) -> np.ndarray:
    """Centered Log-Ratio transform (GRUMB Module 2 pattern)."""
    x = np.asarray(x, dtype=np.float64) + pseudocount
    log_x = np.log(x)
    return log_x - log_x.mean()


def _inv_clr(clr_vec: np.ndarray) -> np.ndarray:
    """Inverse CLR: map back to the simplex."""
    exp_vec = np.exp(clr_vec)
    return exp_vec / exp_vec.sum()


class WastewaterSequencingGrid:
    """Pooled metagenomic sequencing from greywater/blackwater lines.

    Samples the combined output of pathogen mass AND disrupted
    microflora mass from a zone's wastewater system.  Uses
    Dirichlet-multinomial sampling to convert GRUMB log-ratio
    abundance arrays into simulated relative-abundance tables,
    mimicking a real metagenomic sequencing run.

    The Dirichlet-multinomial model:
    1. Start with the GRUMB 4-kingdom CLR composition + microflora shifts
    2. Convert to simplex proportions via inverse-CLR
    3. Inject pathogen as an additional taxon proportional to mass
    4. Draw Dirichlet proportions: p ~ Dir(alpha * composition)
    5. Draw read counts: reads ~ Multinomial(read_depth, p)

    This produces realistically overdispersed metagenomic count data.
    """

    name = "wastewater_sequencing"

    def __init__(
        self,
        read_depth: int = WW_READ_DEPTH,
        dirichlet_concentration: float = WW_DIRICHLET_CONCENTRATION,
        pseudocount: float = WW_PSEUDOCOUNT,
        rng: np.random.Generator | None = None,
    ) -> None:
        self.read_depth = read_depth
        self.dirichlet_concentration = dirichlet_concentration
        self.pseudocount = pseudocount
        self.rng = rng if rng is not None else np.random.default_rng()

        # Build the base taxa list and baseline profile
        self._taxa: list[str] = []
        self._kingdoms: list[str] = []
        self._baseline: list[float] = []
        for kingdom, taxa_dict in MULTI_KINGDOM_TAXA.items():
            for taxon, abund in taxa_dict.items():
                self._taxa.append(taxon)
                self._kingdoms.append(kingdom)
                self._baseline.append(abund)
        self._baseline_arr = np.array(self._baseline, dtype=np.float64)
        self._baseline_arr /= self._baseline_arr.sum()

    def sample_zone(
        self,
        zone_name: str,
        pathogen_mass: float = 0.0,
        microflora_shifts: dict[str, float] | None = None,
        pathogen_mass_by_id: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Sample wastewater from a zone.

        Parameters
        ----------
        zone_name : str
            Zone identifier.
        pathogen_mass : float
            Total pathogen mass flowing into wastewater.
        microflora_shifts : dict, optional
            {disruption_type: magnitude} from dual-signal shedding.
        pathogen_mass_by_id : dict, optional
            Per-pathogen mass for multi-pathogen attribution.
        """
        microflora_shifts = microflora_shifts or {}

        # Start with baseline GRUMB composition
        composition = self._baseline_arr.copy()

        # Apply microflora disruption shifts via CLR perturbation
        kingdom_clr_deltas: dict[str, float] = {}
        if microflora_shifts:
            clr_vec = _clr_transform(composition, self.pseudocount)
            shift_vec = np.zeros_like(clr_vec)

            from crusher_labs.modalities.sequencing import DISRUPTION_MARKERS

            for d_type, magnitude in microflora_shifts.items():
                markers = DISRUPTION_MARKERS.get(d_type, {})
                for taxon, multiplier in markers.items():
                    if taxon in self._taxa:
                        idx = self._taxa.index(taxon)
                        shift_vec[idx] += np.log(multiplier) * magnitude * 0.15

            shifted_clr = clr_vec + shift_vec
            composition = _inv_clr(shifted_clr)

            # Compute kingdom-level CLR deltas
            for kingdom in set(self._kingdoms):
                indices = [
                    i for i, k in enumerate(self._kingdoms) if k == kingdom
                ]
                if indices:
                    orig_k = float(np.mean(clr_vec[indices]))
                    new_k = float(np.mean(shifted_clr[indices]))
                    kingdom_clr_deltas[kingdom] = round(new_k - orig_k, 6)

        # Add pathogen as additional taxon
        pathogen_taxa = ["Pathogen_target"]
        pathogen_frac = pathogen_mass / (pathogen_mass + 1000.0)
        env_frac = 1.0 - pathogen_frac
        full_composition = np.append(composition * env_frac, pathogen_frac)
        full_composition /= full_composition.sum()
        all_taxa = self._taxa + pathogen_taxa

        # Per-pathogen sub-fractions
        if pathogen_mass_by_id and pathogen_mass > 0:
            for pid, pmass in pathogen_mass_by_id.items():
                if pmass > 0:
                    pf = pmass / (pathogen_mass + 1000.0)
                    all_taxa.append(f"Pathogen_{pid}")
                    full_composition = np.append(full_composition, pf)
            full_composition /= full_composition.sum()

        # Dirichlet-multinomial draw
        alpha = full_composition * self.dirichlet_concentration
        alpha = np.maximum(alpha, 1e-10)  # prevent zero alpha
        dirichlet_probs = self.rng.dirichlet(alpha)
        reads = self.rng.multinomial(self.read_depth, dirichlet_probs)

        read_dict = {
            t: int(c) for t, c in zip(all_taxa, reads) if c > 0
        }

        # Kingdom-level read aggregation
        kingdom_reads: dict[str, int] = {}
        for i, kingdom in enumerate(self._kingdoms):
            kingdom_reads[kingdom] = kingdom_reads.get(kingdom, 0) + int(reads[i])

        # Anomaly scoring
        anomaly_detected = False
        for delta in kingdom_clr_deltas.values():
            if abs(delta) > 0.05:
                anomaly_detected = True
                break

        return {
            "instrument": self.name,
            "zone": zone_name,
            "read_depth": self.read_depth,
            "total_pathogen_reads": read_dict.get("Pathogen_target", 0),
            "read_counts": read_dict,
            "kingdom_reads": kingdom_reads,
            "kingdom_clr_deltas": kingdom_clr_deltas,
            "anomaly_detected": anomaly_detected,
            "disruption_types": list(microflora_shifts.keys()),
            "pathogen_mass_input": round(pathogen_mass, 4),
            "dirichlet_concentration": self.dirichlet_concentration,
        }

    def sample_all_zones(
        self,
        zone_pathogen_mass: dict[str, float],
        zone_microflora_shifts: dict[str, dict[str, float]],
        pathogen_mass_by_id: dict[str, dict[str, float]] | None = None,
        wastewater_zones: list[str] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Run wastewater sequencing across all (or specified) zones."""
        targets = wastewater_zones if wastewater_zones else list(zone_pathogen_mass.keys())
        results: dict[str, dict[str, Any]] = {}
        for zone_name in targets:
            pmass = zone_pathogen_mass.get(zone_name, 0.0)
            mf = zone_microflora_shifts.get(zone_name, {})
            pid_mass = {}
            if pathogen_mass_by_id:
                pid_mass = {
                    pid: masses.get(zone_name, 0.0)
                    for pid, masses in pathogen_mass_by_id.items()
                }
            results[zone_name] = self.sample_zone(
                zone_name, pmass, mf, pid_mass,
            )
        return results
