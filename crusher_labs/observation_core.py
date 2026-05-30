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
from typing import Any

import numpy as np

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
        self.rng = rng if rng is not None else np.random.default_rng()
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
        self.rng = rng if rng is not None else np.random.default_rng()
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
        self.rng = rng if rng is not None else np.random.default_rng()
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
        rng: np.random.Generator | None = None,
    ) -> None:
        self.read_depth = read_depth
        self.dirichlet_concentration = dirichlet_concentration
        self.pseudocount = pseudocount
        self.rng = rng if rng is not None else np.random.default_rng()
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

    def sample_zone(
        self,
        zone_name: str,
        pathogen_mass: float = 0.0,
        microflora_shifts: dict[str, float] | None = None,
        pathogen_mass_by_id: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        microflora_shifts = microflora_shifts or {}

        composition = self._baseline_arr.copy()

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

            for kingdom in set(self._kingdoms):
                indices = [i for i, k in enumerate(self._kingdoms) if k == kingdom]
                if indices:
                    orig_k = float(np.mean(clr_vec[indices]))
                    new_k = float(np.mean(shifted_clr[indices]))
                    kingdom_clr_deltas[kingdom] = round(new_k - orig_k, 6)

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

        anomaly_detected = any(abs(d) > 0.05 for d in kingdom_clr_deltas.values())

        result: dict[str, Any] = {
            "instrument": self.name,
            "zone": zone_name,
            "read_depth": self.read_depth,
            "total_pathogen_reads": read_dict.get("Pathogen_target", 0),
            "read_counts": read_dict,
            "raw_read_counts_prenorm": raw_read_dict,
            "kingdom_reads": kingdom_reads,
            "kingdom_clr_deltas": kingdom_clr_deltas,
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
    ) -> None:
        self.sensitivity = sensitivity
        self.specificity = specificity
        self.rng = rng if rng is not None else np.random.default_rng()
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
    ) -> dict[str, Any]:
        """Run a rapid antigen test on a single agent."""
        # Shedding-dependent effective sensitivity (sigmoid)
        if shedding_rate > 0:
            eff_sens = self.sensitivity * min(
                1.0, shedding_rate / (shedding_rate + 1000.0),
            )
        else:
            eff_sens = 0.0

        _, carryover = self.qc.process_sample(shedding_rate * 0.001)

        if is_infected:
            positive = self.rng.random() < eff_sens
        else:
            positive = self.rng.random() > self.specificity  # false positive

        # Raw control line intensity (simulated)
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
            )
        return results


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
    ) -> None:
        self.extraction_efficiency = extraction_efficiency
        self.ct_slope = ct_slope
        self.ct_intercept = ct_intercept
        self.lod_ct = lod_ct
        self.rng = rng if rng is not None else np.random.default_rng()
        self.qc = InstrumentQC(cross_contamination_rate, control_intensity, self.rng)

    def test_agent(
        self,
        agent_id: int,
        shedding_rate: float,
        infection_state: str,
        symptom_presentation: str,
        compliance_status: str,
        location: str,
    ) -> dict[str, Any]:
        """Run clinical qPCR on a patient specimen."""
        specimen_mass = shedding_rate * self.extraction_efficiency
        noise_mult = self.rng.lognormal(0, 0.04)
        specimen_mass *= noise_mult

        effective_mass, carryover = self.qc.process_sample(specimen_mass)

        ct = self._compute_ct(effective_mass)
        detected = ct is not None and ct <= self.lod_ct

        viral_load_copies_ml = round(effective_mass * 100, 2) if effective_mass > 0 else 0.0

        raw_amplification = self._simulate_amplification_curve(effective_mass)

        result: dict[str, Any] = {
            "instrument": self.name,
            "agent_id": agent_id,
            "location": location,
            **agent_axes_dict(infection_state, symptom_presentation, compliance_status),
            "ct_value": ct,
            "detected": detected,
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
    ) -> None:
        self.culture_sensitivity = culture_sensitivity
        self.rng = rng if rng is not None else np.random.default_rng()
        self.qc = InstrumentQC(cross_contamination_rate, control_intensity, self.rng)

    def test_agent(
        self,
        agent_id: int,
        microflora_disruption: float,
        infection_state: str,
        symptom_presentation: str,
        compliance_status: str,
        location: str,
        pathogen_infections: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run clinical microbiology on a patient specimen."""
        pathogen_infections = pathogen_infections or {}

        _, carryover = self.qc.process_sample(microflora_disruption * 10)

        # Determine disruption site from active infections
        disruption_site = "skin"  # default
        for pid, inf in pathogen_infections.items():
            if "gi" in pid.lower() or "enteric" in pid.lower() or "norwalk" in pid.lower():
                disruption_site = "gastrointestinal"
                break
            elif "resp" in pid.lower() or "cov" in pid.lower() or "flu" in pid.lower():
                disruption_site = "respiratory"
                break

        # Simulate culture results
        normal_profile = NORMAL_FLORA.get(disruption_site, NORMAL_FLORA["skin"])
        culture_results: dict[str, str] = {}
        gram_stain = "mixed_normal"

        if microflora_disruption > 0.3:
            # Disrupted flora: some commensals reduced, abnormal markers appear
            for organism in normal_profile:
                if self.rng.random() < 0.7:
                    culture_results[organism] = "reduced"
                else:
                    culture_results[organism] = "normal"

            abnormal_list = ABNORMAL_MARKERS.get(disruption_site, [])
            for marker in abnormal_list:
                if self.rng.random() < microflora_disruption * self.culture_sensitivity:
                    culture_results[marker] = "detected"

            gram_stain = "abnormal_shift"
        else:
            for organism in normal_profile:
                culture_results[organism] = "normal"

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

        self.modality = modality or LongReadNanoporeSequencing(enabled=True)
        self.rng = rng if rng is not None else np.random.default_rng()
        self.qc = InstrumentQC(cross_contamination_rate, control_intensity, self.rng)

    def run_requests(
        self,
        requests: list[Any],
    ) -> dict[str, dict[str, Any]]:
        """Execute queued verification runs; keys are ``request_id``."""
        results: dict[str, dict[str, Any]] = {}
        for req in requests:
            out = self.modality.verify(req)
            if self.qc.should_run_control():
                out["qc_control"] = self.qc.run_negative_control()
            results[req.request_id] = out
        return results
