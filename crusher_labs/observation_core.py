"""
crusher_labs.observation_core
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Instrument-level sampling modules for the Crusher Labs Observation Engine.

**Environmental Instruments:**
1. ContinuousAirSniffer — real-time aerosol Ct from airborne mass pools
2. TargetedSurfaceSwab — fomite PCR with compliance-driven technique variance
3. WastewaterSequencingGrid — Dirichlet-multinomial metagenomic sampling

**Individual Patient Clinical Diagnostics (Sick Call):**
4. ClinicalRapidDiagnostic — lateral-flow antigen test (binary, fast, lower sensitivity)
5. ClinicalQPCR — high-sensitivity patient viral load Ct
6. ClinicalMicrobiology — culture/staining for host flora shifts and secondary infections

**Quality Control:**
All instruments track cross-contamination carryover and support automated
negative control runs that flag QC_FAILURE when contamination is detected.
"""

from __future__ import annotations

import math
import os
from typing import Any

import numpy as np

from simulation_utils.numeric import default_simulation_rng
from telemetry_buffer.agent_axes import (
    agent_axes_dict,
    agent_is_infected,
    resolve_agent_axes,
)

# ── Constants ────────────────────────────────────────────────────────────

DEFAULT_CT_SLOPE = -3.322
DEFAULT_CT_INTERCEPT = 40.0
DEFAULT_LOD_CT = 38.0

AIR_SNIFFER_VOLUME_FRACTION = 0.05
AIR_SNIFFER_FILTER_EFF = 0.85

SWAB_NOMINAL_EFF = 0.35
SWAB_GOOD_TECHNIQUE_VARIANCE = 0.05
SWAB_POOR_TECHNIQUE_VARIANCE = 0.20
SWAB_AREA_CM2 = 100.0

DEFAULT_WW_READ_DEPTH = 50_000
DEFAULT_WW_DIRICHLET_CONCENTRATION = 100.0
DEFAULT_WW_PSEUDOCOUNT = 1e-6

# Backward-compatible aliases (tests / imports)
WW_READ_DEPTH = DEFAULT_WW_READ_DEPTH
WW_DIRICHLET_CONCENTRATION = DEFAULT_WW_DIRICHLET_CONCENTRATION
WW_PSEUDOCOUNT = DEFAULT_WW_PSEUDOCOUNT

# Cross-contamination defaults
DEFAULT_CROSS_CONTAMINATION_RATE = 0.0001  # 0.01% mass carryover
DEFAULT_CONTROL_RUN_INTENSITY = "medium"   # low / medium / high

# Clinical diagnostic defaults
RDT_SENSITIVITY = 0.80
RDT_SPECIFICITY = 0.97
CLINICAL_PCR_EXTRACTION_EFF = 0.55
CLINICAL_PCR_LOD_CT = 40.0
MICROBIO_CULTURE_SENSITIVITY = 0.70


MULTI_KINGDOM_TAXA: dict[str, dict[str, float]] = {
    "Bacteria": {
        "Vibrio_spp": 0.10, "Pseudoalteromonas": 0.08,
        "Enterobacter": 0.06, "Acinetobacter": 0.05,
        "Shewanella": 0.04, "Bacillus_subtilis": 0.04,
        "Staphylococcus_epi": 0.03,
    },
    "Archaea": {
        "Nitrosopumilus": 0.03, "Halobacterium": 0.02,
        "Methanobrevibacter": 0.01,
    },
    "Fungi": {
        "Aspergillus_spp": 0.02, "Cladosporium": 0.02,
        "Candida_spp": 0.01,
    },
    "Virus": {
        "Phage_community": 0.04, "ssRNA_marine": 0.02,
    },
}


# ── QC: Cross-Contamination & Negative Control Engine ────────────────────

class InstrumentQC:
    """Tracks cross-contamination carryover and runs negative controls.

    After each sample, a fraction of the sample's mass is retained as
    carryover.  If a negative control is run, it measures only this
    carryover mass; if above detection threshold, QC_FAILURE is flagged.
    """

    def __init__(
        self,
        cross_contamination_rate: float = DEFAULT_CROSS_CONTAMINATION_RATE,
        control_intensity: str = DEFAULT_CONTROL_RUN_INTENSITY,
        rng: np.random.Generator | None = None,
    ) -> None:
        self.cross_contamination_rate = cross_contamination_rate
        self.control_intensity = control_intensity
        self.rng = rng if rng is not None else default_simulation_rng()
        self._carryover_mass: float = 0.0
        self._sample_count: int = 0
        self._last_sample_mass: float = 0.0

    @property
    def control_frequency(self) -> int:
        """How often to run negative controls (every N samples)."""
        return {"low": 12, "medium": 6, "high": 3}.get(
            self.control_intensity, 6,
        )

    def process_sample(self, input_mass: float) -> tuple[float, float]:
        """Process a sample through the instrument.

        Returns (effective_mass, carryover_added).
        Carryover from the previous sample bleeds into this one.
        """
        carryover_added = self._carryover_mass
        effective_mass = input_mass + carryover_added

        # Update carryover for next sample
        self._carryover_mass = effective_mass * self.cross_contamination_rate
        self._last_sample_mass = effective_mass
        self._sample_count += 1

        return effective_mass, round(carryover_added, 6)

    def should_run_control(self) -> bool:
        return self._sample_count > 0 and self._sample_count % self.control_frequency == 0

    def run_negative_control(self) -> dict[str, Any]:
        """Run a blank/negative control sample.

        Returns QC result with PASS or FAILURE status.
        """
        control_mass = self._carryover_mass
        # Add instrument baseline noise to the control
        noise = abs(self.rng.normal(0, 0.001))
        measured = control_mass + noise

        qc_pass = measured < 0.01  # threshold for "clean"

        # Reset carryover after control
        self._carryover_mass = 0.0

        return {
            "qc_type": "negative_control",
            "measured_mass": round(measured, 8),
            "carryover_detected": round(control_mass, 8),
            "instrument_noise": round(noise, 8),
            "qc_status": "QC_PASS" if qc_pass else "QC_FAILURE",
            "threshold": 0.01,
        }


# ── Instrument 1: Continuous Air Sniffer ─────────────────────────────────

class ContinuousAirSniffer:
    """Real-time aerosol detection via continuous air sampling."""

    name = "air_sniffer"

    def __init__(
        self,
        volume_fraction: float = AIR_SNIFFER_VOLUME_FRACTION,
        filter_efficiency: float = AIR_SNIFFER_FILTER_EFF,
        ct_slope: float = DEFAULT_CT_SLOPE,
        ct_intercept: float = DEFAULT_CT_INTERCEPT,
        lod_ct: float = DEFAULT_LOD_CT,
        cross_contamination_rate: float = DEFAULT_CROSS_CONTAMINATION_RATE,
        control_intensity: str = DEFAULT_CONTROL_RUN_INTENSITY,
        rng: np.random.Generator | None = None,
    ) -> None:
        self.volume_fraction = volume_fraction
        self.filter_efficiency = filter_efficiency
        self.ct_slope = ct_slope
        self.ct_intercept = ct_intercept
        self.lod_ct = lod_ct
        self.rng = rng if rng is not None else default_simulation_rng()
        self.qc = InstrumentQC(cross_contamination_rate, control_intensity, self.rng)

    def sample(
        self,
        zone_name: str,
        airborne_mass: float,
        zone_volume_m3: float = 100.0,
    ) -> dict[str, Any]:
        sampled_volume = zone_volume_m3 * self.volume_fraction
        concentration = airborne_mass / max(zone_volume_m3, 1.0)
        raw_captured = concentration * sampled_volume * self.filter_efficiency

        # Instrument noise
        noise_mult = self.rng.lognormal(0, 0.05)
        raw_captured *= noise_mult

        # Apply cross-contamination
        effective_mass, carryover = self.qc.process_sample(raw_captured)

        ct = self._compute_ct(effective_mass)
        detected = ct is not None and ct <= self.lod_ct

        # Raw amplification curve (simulated cycle-by-cycle fluorescence)
        raw_amplification = self._simulate_amplification_curve(effective_mass)

        result: dict[str, Any] = {
            "instrument": self.name,
            "zone": zone_name,
            "airborne_mass": round(airborne_mass, 4),
            "sampled_volume_m3": round(sampled_volume, 2),
            "concentration_per_m3": round(concentration, 6),
            "captured_mass": round(effective_mass, 4),
            "ct_value": ct,
            "detected": detected,
            "cross_contamination_carryover": carryover,
            "raw_amplification_curve": raw_amplification,
            "background_fluorescence": round(float(self.rng.normal(150, 20)), 1),
        }

        # QC negative control check
        if self.qc.should_run_control():
            result["qc_control"] = self.qc.run_negative_control()

        return result

    def sample_all_zones(
        self,
        zone_masses: dict[str, float],
        zone_volumes: dict[str, float],
    ) -> dict[str, dict[str, Any]]:
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

    def _simulate_amplification_curve(self, mass: float) -> list[float]:
        """Simulate a 40-cycle qPCR amplification curve."""
        if mass <= 0:
            return [round(float(self.rng.normal(150, 15)), 1) for _ in range(40)]
        ct_approx = self.ct_slope * math.log10(max(mass, 1e-10)) + self.ct_intercept
        curve = []
        for cycle in range(1, 41):
            if cycle < ct_approx - 3:
                val = self.rng.normal(150, 15)
            elif cycle < ct_approx + 5:
                progress = (cycle - (ct_approx - 3)) / 8.0
                val = 150 + 3850 * (1 / (1 + math.exp(-6 * (progress - 0.5))))
            else:
                val = self.rng.normal(4000, 50)
            curve.append(round(float(max(0, val)), 1))
        return curve


# ── Instrument 2: Targeted Surface Swab ──────────────────────────────────

class TargetedSurfaceSwab:
    """Surface PCR via targeted swab collection with compliance variance."""

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
        cross_contamination_rate: float = DEFAULT_CROSS_CONTAMINATION_RATE,
        control_intensity: str = DEFAULT_CONTROL_RUN_INTENSITY,
        rng: np.random.Generator | None = None,
    ) -> None:
        self.nominal_efficiency = nominal_efficiency
        self.good_variance = good_variance
        self.poor_variance = poor_variance
        self.swab_area_cm2 = swab_area_cm2
        self.ct_slope = ct_slope
        self.ct_intercept = ct_intercept
        self.lod_ct = lod_ct
        self.rng = rng if rng is not None else default_simulation_rng()
        self.qc = InstrumentQC(cross_contamination_rate, control_intensity, self.rng)

    def swab(
        self,
        zone_name: str,
        surface_mass: float,
        compliance_scalar: float = 0.85,
    ) -> dict[str, Any]:
        if compliance_scalar >= 0.8:
            variance = self.good_variance
            technique = "careful"
        else:
            variance = self.poor_variance
            technique = "rushed"

        actual_efficiency = self.rng.normal(self.nominal_efficiency, variance)
        actual_efficiency = float(np.clip(actual_efficiency, 0.05, 0.95))

        raw_recovered = surface_mass * actual_efficiency
        noise_mult = self.rng.lognormal(0, 0.03)
        raw_recovered *= noise_mult

        effective_mass, carryover = self.qc.process_sample(raw_recovered)

        ct = self._compute_ct(effective_mass)
        detected = ct is not None and ct <= self.lod_ct

        raw_amplification = self._simulate_amplification_curve(effective_mass)

        result: dict[str, Any] = {
            "instrument": self.name,
            "zone": zone_name,
            "surface_mass": round(surface_mass, 4),
            "compliance_scalar": round(compliance_scalar, 3),
            "technique_quality": technique,
            "actual_collection_efficiency": round(actual_efficiency, 4),
            "recovered_mass": round(effective_mass, 4),
            "ct_value": ct,
            "detected": detected,
            "cross_contamination_carryover": carryover,
            "raw_amplification_curve": raw_amplification,
            "background_fluorescence": round(float(self.rng.normal(140, 18)), 1),
        }

        if self.qc.should_run_control():
            result["qc_control"] = self.qc.run_negative_control()

        return result

    def swab_zones(
        self,
        zone_surface_masses: dict[str, float],
        compliance_scalar: float = 0.85,
        target_zones: list[str] | None = None,
    ) -> dict[str, dict[str, Any]]:
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

    def _simulate_amplification_curve(self, mass: float) -> list[float]:
        if mass <= 0:
            return [round(float(self.rng.normal(140, 12)), 1) for _ in range(40)]
        ct_approx = self.ct_slope * math.log10(max(mass, 1e-10)) + self.ct_intercept
        curve = []
        for cycle in range(1, 41):
            if cycle < ct_approx - 3:
                val = self.rng.normal(140, 12)
            elif cycle < ct_approx + 5:
                progress = (cycle - (ct_approx - 3)) / 8.0
                val = 140 + 3860 * (1 / (1 + math.exp(-6 * (progress - 0.5))))
            else:
                val = self.rng.normal(4000, 45)
            curve.append(round(float(max(0, val)), 1))
        return curve


# ── Instrument 3: Wastewater Sequencing Grid ─────────────────────────────

def _clr_transform(x: np.ndarray, pseudocount: float = 1e-6) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64) + pseudocount
    log_x = np.log(x)
    return log_x - log_x.mean()


def _inv_clr(clr_vec: np.ndarray) -> np.ndarray:
    exp_vec = np.exp(clr_vec)
    return exp_vec / exp_vec.sum()


class WastewaterSequencingGrid:
    """Pooled metagenomic sequencing from greywater/blackwater lines."""

    name = "wastewater_sequencing"

    def __init__(
        self,
        read_depth: int = WW_READ_DEPTH,
        dirichlet_concentration: float = WW_DIRICHLET_CONCENTRATION,
        pseudocount: float = WW_PSEUDOCOUNT,
        cross_contamination_rate: float = DEFAULT_CROSS_CONTAMINATION_RATE,
        control_intensity: str = DEFAULT_CONTROL_RUN_INTENSITY,
        aitchison_anomaly_threshold: float = 0.08,
        rng: np.random.Generator | None = None,
    ) -> None:
        self.read_depth = read_depth
        self.dirichlet_concentration = dirichlet_concentration
        self.pseudocount = pseudocount
        self.aitchison_anomaly_threshold = aitchison_anomaly_threshold
        self.rng = rng if rng is not None else default_simulation_rng()
        self.qc = InstrumentQC(cross_contamination_rate, control_intensity, self.rng)

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

    def _apply_microflora_shifts(
        self,
        composition: np.ndarray,
        microflora_shifts: dict[str, float],
    ) -> tuple[np.ndarray, float, dict[str, float]]:
        from crusher_labs.modalities.sequencing import (
            DISRUPTION_MARKERS,
            aitchison_distance,
        )

        pre_shift_composition = composition.copy()
        clr_vec = _clr_transform(composition, self.pseudocount)
        shift_vec = np.zeros_like(clr_vec)

        for d_type, magnitude in microflora_shifts.items():
            markers = DISRUPTION_MARKERS.get(d_type, {})
            for taxon, multiplier in markers.items():
                if taxon in self._taxa:
                    idx = self._taxa.index(taxon)
                    shift_vec[idx] += np.log(multiplier) * magnitude * 0.15

        shifted_clr = clr_vec + shift_vec
        composition = _inv_clr(shifted_clr)
        aitchison_dist = aitchison_distance(
            pre_shift_composition, composition, self.pseudocount,
        )

        kingdom_clr_deltas: dict[str, float] = {}
        for kingdom in set(self._kingdoms):
            indices = [i for i, k in enumerate(self._kingdoms) if k == kingdom]
            if indices:
                orig_k = float(np.mean(clr_vec[indices]))
                new_k = float(np.mean(shifted_clr[indices]))
                kingdom_clr_deltas[kingdom] = round(new_k - orig_k, 6)
        return composition, aitchison_dist, kingdom_clr_deltas

    def sample_zone(
        self,
        zone_name: str,
        pathogen_mass: float = 0.0,
        microflora_shifts: dict[str, float] | None = None,
        pathogen_mass_by_id: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        microflora_shifts = microflora_shifts or {}

        composition = self._baseline_arr.copy()
        aitchison_dist = 0.0
        kingdom_clr_deltas: dict[str, float] = {}
        if microflora_shifts:
            composition, aitchison_dist, kingdom_clr_deltas = (
                self._apply_microflora_shifts(composition, microflora_shifts)
            )

        pathogen_taxa = ["Pathogen_target"]
        pathogen_frac = pathogen_mass / (pathogen_mass + 1000.0)
        env_frac = 1.0 - pathogen_frac
        full_composition = np.append(composition * env_frac, pathogen_frac)
        full_composition /= full_composition.sum()
        all_taxa = self._taxa + pathogen_taxa

        if pathogen_mass_by_id and pathogen_mass > 0:
            for pid, pmass in pathogen_mass_by_id.items():
                if pmass > 0:
                    pf = pmass / (pathogen_mass + 1000.0)
                    all_taxa.append(f"Pathogen_{pid}")
                    full_composition = np.append(full_composition, pf)
            full_composition /= full_composition.sum()

        # Cross-contamination on total mass entering the sequencer
        total_input_mass = pathogen_mass + sum(microflora_shifts.values()) * 50.0
        _, carryover = self.qc.process_sample(total_input_mass)

        alpha = full_composition * self.dirichlet_concentration
        alpha = np.maximum(alpha, 1e-10)
        dirichlet_probs = self.rng.dirichlet(alpha)
        reads = self.rng.multinomial(self.read_depth, dirichlet_probs)

        # Raw pre-normalization read counts (before QC filter)
        raw_read_dict = {t: int(c) for t, c in zip(all_taxa, reads)}
        read_dict = {t: c for t, c in raw_read_dict.items() if c > 0}

        kingdom_reads: dict[str, int] = {}
        for i, kingdom in enumerate(self._kingdoms):
            kingdom_reads[kingdom] = kingdom_reads.get(kingdom, 0) + int(reads[i])

        anomaly_detected = aitchison_dist > self.aitchison_anomaly_threshold

        result: dict[str, Any] = {
            "instrument": self.name,
            "zone": zone_name,
            "read_depth": self.read_depth,
            "total_pathogen_reads": read_dict.get("Pathogen_target", 0),
            "read_counts": read_dict,
            "raw_read_counts_prenorm": raw_read_dict,
            "kingdom_reads": kingdom_reads,
            "kingdom_clr_deltas": kingdom_clr_deltas,
            "aitchison_distance_to_baseline": round(aitchison_dist, 6),
            "aitchison_anomaly_threshold": self.aitchison_anomaly_threshold,
            "anomaly_detected": anomaly_detected,
            "disruption_types": list(microflora_shifts.keys()),
            "pathogen_mass_input": round(pathogen_mass, 4),
            "dirichlet_concentration": self.dirichlet_concentration,
            "cross_contamination_carryover": carryover,
        }

        if self.qc.should_run_control():
            result["qc_control"] = self.qc.run_negative_control()

        return result

    def sample_all_zones(
        self,
        zone_pathogen_mass: dict[str, float],
        zone_microflora_shifts: dict[str, dict[str, float]],
        pathogen_mass_by_id: dict[str, dict[str, float]] | None = None,
        wastewater_zones: list[str] | None = None,
    ) -> dict[str, dict[str, Any]]:
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
            results[zone_name] = self.sample_zone(zone_name, pmass, mf, pid_mass)
        return results


def _uninformative_base_result(
    instrument: str,
    agent_id: int,
    location: str,
    infection_state: str,
    symptom_presentation: str,
    compliance_status: str,
    *,
    pathogen_id: str | None = None,
    panel_id: str | None = None,
) -> dict[str, Any]:
    """Assay ran but cannot speak to the agent's pathogen (not a true negative)."""
    result: dict[str, Any] = {
        "instrument": instrument,
        "agent_id": agent_id,
        "location": location,
        **agent_axes_dict(infection_state, symptom_presentation, compliance_status),
        "positive": False,
        "detected": False,
        "informative": False,
        "pathogen_id": pathogen_id,
    }
    if panel_id is not None:
        result["panel_id"] = panel_id
    return result


# ── Instrument 4: Clinical Rapid Diagnostic Test (Lateral Flow) ──────────

class ClinicalRapidDiagnostic:
    """Individual patient lateral-flow antigen test.

    High speed, lower sensitivity, binary output.
    Triggered when an agent reports to Sick Call.
    """

    name = "clinical_rdt"

    def __init__(
        self,
        sensitivity: float = RDT_SENSITIVITY,
        specificity: float = RDT_SPECIFICITY,
        cross_contamination_rate: float = DEFAULT_CROSS_CONTAMINATION_RATE,
        control_intensity: str = DEFAULT_CONTROL_RUN_INTENSITY,
        rng: np.random.Generator | None = None,
        instrument_params: dict[str, Any] | None = None,
    ) -> None:
        self.sensitivity = sensitivity
        self.specificity = specificity
        self.instrument_params = instrument_params
        self.rng = rng if rng is not None else default_simulation_rng()
        self.qc = InstrumentQC(cross_contamination_rate, control_intensity, self.rng)

    def test_agent(
        self,
        agent_id: int,
        shedding_rate: float,
        is_infected: bool,
        infection_state: str,
        symptom_presentation: str,
        compliance_status: str,
        location: str,
        *,
        uniform_draw: float | None = None,
        pathogen_id: str | None = None,
        pathogen_infections: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run a rapid antigen test on a single agent."""
        from crusher_labs.clinical_instrument_params import (
            active_pathogen_ids,
            rdt_phase_sensitivity,
            resolve_instrument_params,
        )

        if pathogen_id is None and pathogen_infections:
            ids = active_pathogen_ids({"pathogen_infections": pathogen_infections})
            pathogen_id = ids[0] if ids else None

        sens = self.sensitivity
        spec = self.specificity
        covers = True
        if self.instrument_params is not None and pathogen_id:
            resolved = resolve_instrument_params(
                self.instrument_params, self.name, pathogen_id,
            )
            covers = resolved.covers_pathogen
            if covers:
                sens = rdt_phase_sensitivity(resolved, shedding_rate)
                spec = resolved.specificity or spec
        elif self.instrument_params is not None and is_infected and not pathogen_id:
            covers = True

        if is_infected and pathogen_id and not covers:
            return _uninformative_base_result(
                self.name, agent_id, location,
                infection_state, symptom_presentation, compliance_status,
                pathogen_id=pathogen_id,
            )

        if shedding_rate > 0:
            eff_sens = sens * min(1.0, shedding_rate / (shedding_rate + 1000.0))
        else:
            eff_sens = 0.0

        _, carryover = self.qc.process_sample(shedding_rate * 0.001)

        draw = self.rng.random() if uniform_draw is None else uniform_draw
        if is_infected:
            positive = draw < eff_sens
        else:
            positive = draw > spec

        control_line = round(float(self.rng.normal(0.85, 0.05)), 3)
        test_line = 0.0
        if positive:
            test_line = round(float(self.rng.normal(0.6, 0.15)), 3)
        elif shedding_rate > 0:
            test_line = round(float(self.rng.normal(0.05, 0.02)), 3)

        result: dict[str, Any] = {
            "instrument": self.name,
            "agent_id": agent_id,
            "location": location,
            **agent_axes_dict(infection_state, symptom_presentation, compliance_status),
            "positive": positive,
            "informative": True,
            "pathogen_id": pathogen_id,
            "effective_sensitivity": round(eff_sens, 4),
            "shedding_rate": round(shedding_rate, 2),
            "control_line_intensity": control_line,
            "test_line_intensity": round(max(0, test_line), 3),
            "cross_contamination_carryover": carryover,
        }

        if self.qc.should_run_control():
            result["qc_control"] = self.qc.run_negative_control()

        return result

    def test_sick_call_agents(
        self,
        agents: list[dict[str, Any]],
    ) -> dict[int, dict[str, Any]]:
        """Run RDT on all agents reporting to sick call."""
        results: dict[int, dict[str, Any]] = {}
        for ag in agents:
            aid = ag["agent_id"]
            shedding = ag.get("shedding_rate", 0.0)
            infected = agent_is_infected(ag)
            infection, presentation, compliance = resolve_agent_axes(ag)
            results[aid] = self.test_agent(
                aid,
                shedding,
                infected,
                infection,
                presentation,
                compliance,
                ag.get("location", "unknown"),
                pathogen_infections=ag.get("pathogen_infections"),
            )
        return results


# ── Instrument 4b: Clinical Multiplex PCR Panel ─────────────────────────

class ClinicalMultiplexPanel:
    """Syndrome-selected multiplex PCR panel (GI / RP / pneumonia)."""

    name = "clinical_multiplex_panel"

    def __init__(
        self,
        instrument_params: dict[str, Any] | None = None,
        cross_contamination_rate: float = DEFAULT_CROSS_CONTAMINATION_RATE,
        control_intensity: str = DEFAULT_CONTROL_RUN_INTENSITY,
        rng: np.random.Generator | None = None,
    ) -> None:
        self.instrument_params = instrument_params or {}
        self.rng = rng if rng is not None else default_simulation_rng()
        self.qc = InstrumentQC(cross_contamination_rate, control_intensity, self.rng)

    def test_agent(
        self,
        agent_id: int,
        shedding_rate: float,
        is_infected: bool,
        infection_state: str,
        symptom_presentation: str,
        compliance_status: str,
        location: str,
        *,
        uniform_draw: float | None = None,
        pathogen_infections: dict[str, Any] | None = None,
        observed_syndromes: list[str] | None = None,
        panel_id: str | None = None,
    ) -> dict[str, Any]:
        from crusher_labs.clinical_instrument_params import (
            active_pathogen_ids,
            panels_for_syndromes,
            resolve_panel_params,
        )

        syndromes = list(observed_syndromes or [])
        panel_ids = [panel_id] if panel_id else panels_for_syndromes(
            self.instrument_params, syndromes,
        )
        active = active_pathogen_ids({"pathogen_infections": pathogen_infections or {}})

        if not panel_ids:
            return _uninformative_base_result(
                self.name, agent_id, location,
                infection_state, symptom_presentation, compliance_status,
                pathogen_id=active[0] if active else None,
            )

        _, carryover = self.qc.process_sample(shedding_rate * 0.001)
        draw = self.rng.random() if uniform_draw is None else uniform_draw

        target_results: dict[str, Any] = {}
        identified: str | None = None
        any_informative = False
        overall_positive = False

        for pid_panel in panel_ids:
            panel_cfg = (self.instrument_params.get("panels") or {}).get(pid_panel) or {}
            panel_pathogens = panel_cfg.get("pathogens") or {}
            for target_pid in panel_pathogens:
                resolved = resolve_panel_params(
                    self.instrument_params, pid_panel, target_pid,
                )
                if resolved is None:
                    continue
                any_informative = True
                infected_with_target = target_pid in active
                if shedding_rate > 0 and infected_with_target:
                    eff_sens = resolved.sensitivity * min(
                        1.0, shedding_rate / (shedding_rate + 1000.0),
                    )
                else:
                    eff_sens = 0.0
                if infected_with_target:
                    hit = draw < eff_sens
                else:
                    hit = draw > resolved.specificity
                target_results[target_pid] = {
                    "panel_id": pid_panel,
                    "positive": hit,
                    "effective_sensitivity": round(eff_sens, 4),
                }
                if hit:
                    overall_positive = True
                    if infected_with_target and identified is None:
                        identified = target_pid

        # Active pathogens not on any ordered panel → uninformative for them
        covered = set(target_results)
        uncovered_active = [p for p in active if p not in covered]
        informative = any_informative and (
            not active or any(p in covered for p in active)
        )
        # If agent is infected only with off-panel pathogens, entire result is
        # uninformative even though on-panel targets are negative.
        if active and not any(p in covered for p in active):
            informative = False
            overall_positive = False
            identified = None

        result: dict[str, Any] = {
            "instrument": self.name,
            "agent_id": agent_id,
            "location": location,
            **agent_axes_dict(infection_state, symptom_presentation, compliance_status),
            "positive": overall_positive if informative else False,
            "informative": informative,
            "panel_ids": panel_ids,
            "target_results": target_results,
            "identified_pathogen": identified if informative and overall_positive else None,
            "uncovered_active_pathogens": uncovered_active,
            "shedding_rate": round(shedding_rate, 2),
            "cross_contamination_carryover": carryover,
        }
        if self.qc.should_run_control():
            result["qc_control"] = self.qc.run_negative_control()
        return result


# ── Instrument 4c: Clinical Impression (bedside, no lab) ────────────────

class ClinicalImpression:
    """Time-dependent bedside clinical suspicion (not laboratory confirmation)."""

    name = "clinical_impression"

    def __init__(
        self,
        instrument_params: dict[str, Any] | None = None,
        rng: np.random.Generator | None = None,
    ) -> None:
        self.instrument_params = instrument_params or {}
        self.rng = rng if rng is not None else default_simulation_rng()

    def test_agent(
        self,
        agent_id: int,
        shedding_rate: float,
        is_infected: bool,
        infection_state: str,
        symptom_presentation: str,
        compliance_status: str,
        location: str,
        *,
        uniform_draw: float | None = None,
        pathogen_id: str | None = None,
        pathogen_infections: dict[str, Any] | None = None,
        days_since_symptom_onset: int = 0,
        outbreak_aware: bool = False,
        candidate_pathogens: list[str] | None = None,
    ) -> dict[str, Any]:
        from crusher_labs.clinical_instrument_params import (
            active_pathogen_ids,
            impression_sensitivity_for_day,
            resolve_instrument_params,
        )

        active = active_pathogen_ids({"pathogen_infections": pathogen_infections or {}})
        candidates = list(candidate_pathogens or [])
        if not candidates and pathogen_id:
            candidates = [pathogen_id]
        if not candidates:
            # Fall back to active pathogens with impression coverage
            for pid in active:
                resolved = resolve_instrument_params(
                    self.instrument_params, self.name, pid,
                )
                if resolved.covers_pathogen:
                    candidates.append(pid)

        if not candidates:
            return _uninformative_base_result(
                self.name, agent_id, location,
                infection_state, symptom_presentation, compliance_status,
                pathogen_id=active[0] if active else None,
            )

        draw = self.rng.random() if uniform_draw is None else uniform_draw
        suspected: str | None = None
        informative = False
        for pid in candidates:
            resolved = resolve_instrument_params(
                self.instrument_params, self.name, pid,
            )
            if not resolved.covers_pathogen:
                continue
            informative = True
            sens = impression_sensitivity_for_day(
                resolved,
                days_since_symptom_onset,
                outbreak_aware=outbreak_aware,
            )
            spec = resolved.specificity
            infected_with = pid in active
            if infected_with:
                hit = draw < sens
            else:
                hit = draw > spec
            if hit and suspected is None:
                suspected = pid

        if not informative:
            return _uninformative_base_result(
                self.name, agent_id, location,
                infection_state, symptom_presentation, compliance_status,
                pathogen_id=active[0] if active else None,
            )

        return {
            "instrument": self.name,
            "agent_id": agent_id,
            "location": location,
            **agent_axes_dict(infection_state, symptom_presentation, compliance_status),
            "positive": suspected is not None,
            "informative": True,
            "suspected_pathogen": suspected,
            "days_since_symptom_onset": int(days_since_symptom_onset),
            "outbreak_aware": bool(outbreak_aware),
            "confirmation": False,
            "shedding_rate": round(shedding_rate, 2),
        }


# ── Instrument 5: Clinical qPCR (Patient Viral Load) ────────────────────

class ClinicalQPCR:
    """High-sensitivity patient viral load qPCR.

    Returns exact Ct values for individual patient specimens.
    """

    name = "clinical_qpcr"

    def __init__(
        self,
        extraction_efficiency: float = CLINICAL_PCR_EXTRACTION_EFF,
        ct_slope: float = DEFAULT_CT_SLOPE,
        ct_intercept: float = DEFAULT_CT_INTERCEPT,
        lod_ct: float = CLINICAL_PCR_LOD_CT,
        cross_contamination_rate: float = DEFAULT_CROSS_CONTAMINATION_RATE,
        control_intensity: str = DEFAULT_CONTROL_RUN_INTENSITY,
        rng: np.random.Generator | None = None,
        instrument_params: dict[str, Any] | None = None,
    ) -> None:
        self.extraction_efficiency = extraction_efficiency
        self.ct_slope = ct_slope
        self.ct_intercept = ct_intercept
        self.lod_ct = lod_ct
        self.instrument_params = instrument_params
        self.rng = rng if rng is not None else default_simulation_rng()
        self.qc = InstrumentQC(cross_contamination_rate, control_intensity, self.rng)

    def test_agent(
        self,
        agent_id: int,
        shedding_rate: float,
        infection_state: str,
        symptom_presentation: str,
        compliance_status: str,
        location: str,
        *,
        uniform_draw: float | None = None,
        pathogen_id: str | None = None,
        pathogen_infections: dict[str, Any] | None = None,
        is_infected: bool | None = None,
    ) -> dict[str, Any]:
        """Run clinical qPCR on a patient specimen."""
        from crusher_labs.clinical_instrument_params import (
            active_pathogen_ids,
            resolve_instrument_params,
        )

        if pathogen_id is None and pathogen_infections:
            ids = active_pathogen_ids({"pathogen_infections": pathogen_infections})
            pathogen_id = ids[0] if ids else None
        if is_infected is None:
            is_infected = bool(pathogen_id) or shedding_rate > 0

        detect_sens = RDT_SENSITIVITY
        covers = True
        if self.instrument_params is not None and pathogen_id:
            resolved = resolve_instrument_params(
                self.instrument_params, self.name, pathogen_id,
            )
            covers = resolved.covers_pathogen
            if covers:
                detect_sens = resolved.sensitivity or detect_sens

        if is_infected and pathogen_id and not covers:
            return _uninformative_base_result(
                self.name, agent_id, location,
                infection_state, symptom_presentation, compliance_status,
                pathogen_id=pathogen_id,
            )

        specimen_mass = shedding_rate * self.extraction_efficiency
        if uniform_draw is None:
            noise_mult = self.rng.lognormal(0, 0.04)
        else:
            from crusher_labs.clinical_correlation import _normal_ppf

            noise_mult = math.exp(_normal_ppf(uniform_draw) * 0.04)
        specimen_mass *= noise_mult

        effective_mass, carryover = self.qc.process_sample(specimen_mass)

        ct = self._compute_ct(effective_mass)
        if uniform_draw is None:
            detected = ct is not None and ct <= self.lod_ct
        elif shedding_rate > 0:
            eff_detect = detect_sens * min(
                1.0, shedding_rate / (shedding_rate + 1000.0),
            )
            detected = uniform_draw < eff_detect
        else:
            detected = False

        viral_load_copies_ml = round(effective_mass * 100, 2) if effective_mass > 0 else 0.0

        raw_amplification = self._simulate_amplification_curve(effective_mass)

        result: dict[str, Any] = {
            "instrument": self.name,
            "agent_id": agent_id,
            "location": location,
            **agent_axes_dict(infection_state, symptom_presentation, compliance_status),
            "ct_value": ct,
            "detected": detected,
            "positive": detected,
            "informative": True,
            "pathogen_id": pathogen_id,
            "viral_load_copies_ml": viral_load_copies_ml,
            "specimen_mass": round(effective_mass, 6),
            "cross_contamination_carryover": carryover,
            "raw_amplification_curve": raw_amplification,
            "background_fluorescence": round(float(self.rng.normal(160, 18)), 1),
        }

        if self.qc.should_run_control():
            result["qc_control"] = self.qc.run_negative_control()

        return result

    def test_sick_call_agents(
        self,
        agents: list[dict[str, Any]],
    ) -> dict[int, dict[str, Any]]:
        """Run clinical qPCR on all sick-call agents."""
        results: dict[int, dict[str, Any]] = {}
        for ag in agents:
            aid = ag["agent_id"]
            infection, presentation, compliance = resolve_agent_axes(ag)
            results[aid] = self.test_agent(
                aid,
                ag.get("shedding_rate", 0.0),
                infection,
                presentation,
                compliance,
                ag.get("location", "unknown"),
                pathogen_infections=ag.get("pathogen_infections"),
                is_infected=agent_is_infected(ag),
            )
        return results

    def _compute_ct(self, mass: float) -> float | None:
        if mass <= 0:
            return None
        ct = self.ct_slope * math.log10(mass) + self.ct_intercept
        return round(ct, 2)

    def _simulate_amplification_curve(self, mass: float) -> list[float]:
        if mass <= 0:
            return [round(float(self.rng.normal(160, 15)), 1) for _ in range(40)]
        ct_approx = self.ct_slope * math.log10(max(mass, 1e-10)) + self.ct_intercept
        curve = []
        for cycle in range(1, 41):
            if cycle < ct_approx - 3:
                val = self.rng.normal(160, 15)
            elif cycle < ct_approx + 5:
                progress = (cycle - (ct_approx - 3)) / 8.0
                val = 160 + 3840 * (1 / (1 + math.exp(-6 * (progress - 0.5))))
            else:
                val = self.rng.normal(4000, 50)
            curve.append(round(float(max(0, val)), 1))
        return curve


# ── Instrument 6: Clinical Microbiology ──────────────────────────────────

# Normal host flora profiles by body site
NORMAL_FLORA: dict[str, dict[str, float]] = {
    "respiratory": {
        "Streptococcus_viridans": 0.30, "Neisseria_commensal": 0.15,
        "Haemophilus_spp": 0.10, "Moraxella_spp": 0.08,
        "Corynebacterium_spp": 0.12, "Staphylococcus_epi": 0.10,
    },
    "gastrointestinal": {
        "Bacteroides_spp": 0.25, "Lactobacillus_spp": 0.15,
        "Enterococcus_spp": 0.10, "E_coli_commensal": 0.12,
        "Bifidobacterium_spp": 0.10, "Clostridium_spp": 0.08,
    },
    "skin": {
        "Staphylococcus_epi": 0.30, "Propionibacterium_spp": 0.20,
        "Corynebacterium_spp": 0.15, "Malassezia_spp": 0.10,
        "Micrococcus_spp": 0.08,
    },
}

# Abnormal markers suggesting secondary infection or flora disruption
ABNORMAL_MARKERS: dict[str, list[str]] = {
    "gastrointestinal": ["Clostridioides_difficile", "Candida_overgrowth", "Enterobacter_bloom"],
    "respiratory": ["Pseudomonas_aeruginosa", "MRSA", "Aspergillus_fumigatus"],
    "skin": ["MRSA", "Strep_pyogenes", "Candida_skin"],
}


class ClinicalMicrobiology:
    """Clinical culture/staining for host flora shifts and secondary infections.

    Performs basic Gram stain and culture to detect:
    - Shifts in normal commensal flora composition
    - Presence of abnormal/pathogenic organisms indicating secondary infection
    - Microflora disruption severity (correlated with antibiotic use, disease)
    """

    name = "clinical_microbiology"

    def __init__(
        self,
        culture_sensitivity: float = MICROBIO_CULTURE_SENSITIVITY,
        cross_contamination_rate: float = DEFAULT_CROSS_CONTAMINATION_RATE,
        control_intensity: str = DEFAULT_CONTROL_RUN_INTENSITY,
        rng: np.random.Generator | None = None,
        instrument_params: dict[str, Any] | None = None,
        pathogen_profiles: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.culture_sensitivity = culture_sensitivity
        self.instrument_params = instrument_params
        self.pathogen_profiles = pathogen_profiles or {}
        self.rng = rng if rng is not None else default_simulation_rng()
        self.qc = InstrumentQC(cross_contamination_rate, control_intensity, self.rng)

    def _disruption_site(self, pathogen_infections: dict[str, Any]) -> str:
        from crusher_labs.clinical_instrument_params import active_pathogen_ids
        from crusher_labs.clinical_presentation import presentation_for_pathogen

        for pid in active_pathogen_ids({"pathogen_infections": pathogen_infections}):
            presentation = presentation_for_pathogen(pid, self.pathogen_profiles)
            syndromes = presentation.get("syndromes") or []
            if "gastrointestinal" in syndromes:
                return "gastrointestinal"
            if "respiratory" in syndromes:
                return "respiratory"
            sample_types = presentation.get("sample_types") or []
            if "stool" in sample_types:
                return "gastrointestinal"
            if "np_swab" in sample_types or "respiratory_specimen" in sample_types:
                return "respiratory"
            profile = self.pathogen_profiles.get(pid) or {}
            dtype = (profile.get("microflora_disruption") or {}).get("disruption_type", "")
            if "gastro" in str(dtype):
                return "gastrointestinal"
            if "resp" in str(dtype):
                return "respiratory"
        # Legacy substring fallback
        for pid in pathogen_infections:
            pid_lower = pid.lower()
            if "gi" in pid_lower or "enteric" in pid_lower or "norwalk" in pid_lower:
                return "gastrointestinal"
            if "resp" in pid_lower or "cov" in pid_lower or "flu" in pid_lower:
                return "respiratory"
        return "skin"

    def _culture_panel(
        self,
        disruption_site: str,
        microflora_disruption: float,
        *,
        uniform_draw: float | None,
        culture_sensitivity: float | None = None,
    ) -> tuple[dict[str, str], str]:
        sens = (
            self.culture_sensitivity
            if culture_sensitivity is None
            else culture_sensitivity
        )
        normal_profile = NORMAL_FLORA.get(disruption_site, NORMAL_FLORA["skin"])
        culture_results: dict[str, str] = {}
        culture_draw = self.rng.random() if uniform_draw is None else uniform_draw

        if microflora_disruption <= 0.3:
            for organism in normal_profile:
                culture_results[organism] = "normal"
            return culture_results, "mixed_normal"

        for organism in normal_profile:
            culture_results[organism] = (
                "reduced" if self.rng.random() < 0.7 else "normal"
            )

        abnormal_list = ABNORMAL_MARKERS.get(disruption_site, [])
        for marker in abnormal_list:
            if culture_draw < microflora_disruption * sens:
                culture_results[marker] = "detected"
            if uniform_draw is None:
                culture_draw = self.rng.random()

        return culture_results, "abnormal_shift"

    def test_agent(
        self,
        agent_id: int,
        microflora_disruption: float,
        infection_state: str,
        symptom_presentation: str,
        compliance_status: str,
        location: str,
        pathogen_infections: dict[str, Any] | None = None,
        *,
        uniform_draw: float | None = None,
        pathogen_id: str | None = None,
        is_infected: bool | None = None,
    ) -> dict[str, Any]:
        """Run clinical microbiology on a patient specimen."""
        from crusher_labs.clinical_instrument_params import (
            active_pathogen_ids,
            resolve_instrument_params,
        )

        pathogen_infections = pathogen_infections or {}
        if pathogen_id is None:
            ids = active_pathogen_ids({"pathogen_infections": pathogen_infections})
            pathogen_id = ids[0] if ids else None
        if is_infected is None:
            is_infected = pathogen_id is not None

        culture_sens = self.culture_sensitivity
        covers = True
        if self.instrument_params is not None and pathogen_id:
            resolved = resolve_instrument_params(
                self.instrument_params, self.name, pathogen_id,
            )
            covers = resolved.covers_pathogen
            if covers:
                culture_sens = resolved.sensitivity or culture_sens

        if is_infected and pathogen_id and not covers:
            result = _uninformative_base_result(
                self.name, agent_id, location,
                infection_state, symptom_presentation, compliance_status,
                pathogen_id=pathogen_id,
            )
            result["microflora_disruption_level"] = round(microflora_disruption, 4)
            result["flora_shift_detected"] = False
            result["secondary_infection_detected"] = False
            return result

        _, carryover = self.qc.process_sample(microflora_disruption * 10)

        disruption_site = self._disruption_site(pathogen_infections)
        culture_results, gram_stain = self._culture_panel(
            disruption_site,
            microflora_disruption,
            uniform_draw=uniform_draw,
            culture_sensitivity=culture_sens,
        )

        flora_shift_detected = microflora_disruption > 0.3
        secondary_infection = any(
            v == "detected" for v in culture_results.values()
        )

        result: dict[str, Any] = {
            "instrument": self.name,
            "agent_id": agent_id,
            "location": location,
            **agent_axes_dict(infection_state, symptom_presentation, compliance_status),
            "disruption_site": disruption_site,
            "microflora_disruption_level": round(microflora_disruption, 4),
            "gram_stain_result": gram_stain,
            "culture_results": culture_results,
            "flora_shift_detected": flora_shift_detected,
            "secondary_infection_detected": secondary_infection,
            "positive": secondary_infection or flora_shift_detected,
            "informative": True,
            "pathogen_id": pathogen_id,
            "cross_contamination_carryover": carryover,
        }

        if self.qc.should_run_control():
            result["qc_control"] = self.qc.run_negative_control()

        return result

    def test_sick_call_agents(
        self,
        agents: list[dict[str, Any]],
    ) -> dict[int, dict[str, Any]]:
        """Run clinical microbiology on all sick-call agents."""
        results: dict[int, dict[str, Any]] = {}
        for ag in agents:
            aid = ag["agent_id"]
            infection, presentation, compliance = resolve_agent_axes(ag)
            results[aid] = self.test_agent(
                aid,
                ag.get("microflora_disruption", 0.0),
                infection,
                presentation,
                compliance,
                ag.get("location", "unknown"),
                ag.get("pathogen_infections"),
                is_infected=agent_is_infected(ag),
            )
        return results


# ── Instrument 7: Long-read verification (Oxford Nanopore) ───────────────

class LongReadVerificationSequencing:
    """Escalation long-read sequencing for verification and pathogen typing.

    Consumes wastewater metagenomics, clinical specimens, clinical culture, or
    surveillance swab upstream results. Invoked only when escalation heuristics
    fire (see ``crusher_labs.long_read_escalation``).
    """

    name = "long_read_verification"

    def __init__(
        self,
        modality: Any | None = None,
        cross_contamination_rate: float = DEFAULT_CROSS_CONTAMINATION_RATE,
        control_intensity: str = DEFAULT_CONTROL_RUN_INTENSITY,
        rng: np.random.Generator | None = None,
    ) -> None:
        from crusher_labs.modalities.long_read_sequencing import LongReadNanoporeSequencing

        if modality is None:
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            modality = LongReadNanoporeSequencing.from_params_path(
                "data/config/long_read_sequencing_params.json",
                "flongle_rapid",
                enabled=True,
                rng=rng if rng is not None else default_simulation_rng(),
                repo_root=repo_root,
            )
        self.modality = modality
        self.rng = rng if rng is not None else default_simulation_rng()
        self.qc = InstrumentQC(cross_contamination_rate, control_intensity, self.rng)

    def run_requests(
        self,
        requests: list[Any],
        *,
        epoch: int = 0,
        spaces: dict[str, dict[str, Any]] | None = None,
        agents: list[dict[str, Any]] | None = None,
        pathogen_profiles: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Execute queued verification runs; keys are ``request_id``."""
        results: dict[str, dict[str, Any]] = {}
        for req in requests:
            out = self.modality.verify(
                req,
                epoch=epoch,
                spaces=spaces,
                agents=agents,
                pathogen_profiles=pathogen_profiles,
            )
            if self.qc.should_run_control():
                out["qc_control"] = self.qc.run_negative_control()
            results[req.request_id] = out
        return results
