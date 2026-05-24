"""
crusher_labs.modalities.sequencing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Metagenomic shotgun sequencing of environmental samples.

Uses GRUMB-validated compositional math:
  1. Represent microbial profiles as relative-abundance vectors.
  2. Blend pathogen into the background using Centered Log-Ratio (CLR)
     linear arithmetic  (ref: GRUMB ``02_Quality_batch_subsetting``).
  3. Inverse-CLR back to simplex proportions.
  4. Draw observed read counts via ``numpy.random.multinomial``.

Implements ecological drift: the marine baseline shifts stochastically
from a Coastal Port profile to an Open Ocean profile and back over the
simulation timeline.

Phase 2.5: Multi-kingdom log-ratio seeding at t=0 — spatial nodes are
initialized with realistic multi-kingdom relative-abundance arrays
derived from the infection-dynamics ship graph zones.

Phase 4+: Microflora disruption detection — when hosts with disrupted
microbiomes shed altered native microbial signatures into the
environment, this modality detects the resulting kingdom-level
log-ratio shifts via GRUMB CLR-space anomaly scoring, independently
of direct pathogen identification.
"""

from __future__ import annotations

from typing import Any

import numpy as np


# ── Multi-Kingdom baseline profiles (GRUMB reference) ────────────────
# Each kingdom contributes taxa to a unified relative-abundance vector.
# Zone-specific modifiers adjust the balance (e.g. Galley has more Fungi
# from food-borne communities, Engine_Room has more Archaea from fuel
# contamination).

MULTI_KINGDOM_TAXA: dict[str, dict[str, float]] = {
    # Kingdom: {taxon: base_relative_abundance}
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

# Zone-type modifiers — scale kingdom abundances per zone type
# (infection-dynamics: Room, Dining, Free, Boarding)
ZONE_TYPE_MODIFIERS: dict[str, dict[str, float]] = {
    "Dining":  {"Bacteria": 1.3, "Archaea": 0.7, "Fungi": 1.6, "Virus": 1.0},
    "Room":    {"Bacteria": 1.1, "Archaea": 0.9, "Fungi": 1.0, "Virus": 1.2},
    "Free":    {"Bacteria": 1.0, "Archaea": 1.0, "Fungi": 0.8, "Virus": 0.9},
}

# Ecological drift profiles
COASTAL_PORT_PROFILE: dict[str, float] = {
    "Vibrio_spp":           0.18,
    "Pseudoalteromonas":    0.12,
    "Enterobacter":         0.10,
    "Acinetobacter":        0.08,
    "Shewanella":           0.07,
    "Bacillus_subtilis":    0.06,
    "Human_commensal_mix":  0.15,
    "Industrial_runoff":    0.09,
    "Phytoplankton_assoc":  0.08,
    "Other_coastal":        0.07,
}

OPEN_OCEAN_PROFILE: dict[str, float] = {
    "Vibrio_spp":           0.04,
    "Pseudoalteromonas":    0.06,
    "Enterobacter":         0.02,
    "Acinetobacter":        0.02,
    "Shewanella":           0.03,
    "Bacillus_subtilis":    0.03,
    "Human_commensal_mix":  0.05,
    "Industrial_runoff":    0.01,
    "Phytoplankton_assoc":  0.35,
    "Other_coastal":        0.39,
}

PATHOGEN_TAXON = "Pathogen_target"

# Microflora disruption markers — altered taxa signatures shed by
# hosts with disrupted microbiomes.  Keyed by disruption type.
DISRUPTION_MARKERS: dict[str, dict[str, float]] = {
    "gastrointestinal": {
        "Enterobacter":       3.5,   # bloom from GI dysbiosis
        "Candida_spp":        2.5,   # fungal opportunist
        "Vibrio_spp":         2.0,   # enteric pathobiont
        "Phage_community":    1.8,   # phage bloom tracks bacterial bloom
    },
    "respiratory": {
        "Pseudoalteromonas":  2.0,   # respiratory tract commensal shift
        "Staphylococcus_epi": 3.0,   # skin/nares dysbiosis
        "Aspergillus_spp":    2.2,   # fungal opportunist
        "ssRNA_marine":       1.5,   # viral community shift
    },
    "skin": {
        "Staphylococcus_epi": 2.5,
        "Candida_spp":        2.0,
        "Bacillus_subtilis":  1.5,
    },
}


# ── GRUMB compositional math helpers ─────────────────────────────────

def _clr_transform(x: np.ndarray, pseudocount: float = 1e-6) -> np.ndarray:
    """Centered Log-Ratio transform (GRUMB Module 2 pattern)."""
    x = np.asarray(x, dtype=np.float64)
    x = x + pseudocount
    log_x = np.log(x)
    return log_x - log_x.mean()


def _inv_clr(clr_vec: np.ndarray) -> np.ndarray:
    """Inverse CLR: map back to the simplex (positive, sums to 1)."""
    exp_vec = np.exp(clr_vec)
    return exp_vec / exp_vec.sum()


def _blend_clr(
    profile_a: np.ndarray,
    profile_b: np.ndarray,
    alpha: float,
    pseudocount: float = 1e-6,
) -> np.ndarray:
    """Blend two profiles via CLR-space linear interpolation (GRUMB pattern).

    ``blend = alpha * CLR(A) + (1 - alpha) * CLR(B)``
    then inverse-CLR to return a valid composition on the simplex.
    """
    clr_a = _clr_transform(profile_a, pseudocount)
    clr_b = _clr_transform(profile_b, pseudocount)
    blended_clr = alpha * clr_a + (1.0 - alpha) * clr_b
    return _inv_clr(blended_clr)


# ── Multi-kingdom seeding (GRUMB + infection-dynamics) ───────────────

def seed_zone_microbiome(
    zone_name: str,
    zone_type: str,
    rng: np.random.Generator,
    pseudocount: float = 1e-6,
) -> dict[str, Any]:
    """Seed a spatial node with a multi-kingdom log-ratio abundance array.

    Constructs a relative-abundance vector spanning all four kingdoms,
    applies zone-type modifiers (from infection-dynamics room categories),
    then normalises via CLR → inv-CLR to produce a valid simplex composition.

    Returns a dict with ``taxa``, ``abundances``, and ``kingdom_fractions``.
    """
    modifiers = ZONE_TYPE_MODIFIERS.get(zone_type, {})
    taxa_names: list[str] = []
    raw_abundances: list[float] = []
    kingdom_labels: list[str] = []

    for kingdom, taxa_dict in MULTI_KINGDOM_TAXA.items():
        mod = modifiers.get(kingdom, 1.0)
        for taxon, base_abund in taxa_dict.items():
            taxa_names.append(taxon)
            raw_abundances.append(base_abund * mod)
            kingdom_labels.append(kingdom)

    raw = np.array(raw_abundances, dtype=np.float64)
    noise = rng.normal(0, 0.005, size=len(raw))
    raw = np.clip(raw + noise, 1e-10, None)

    clr_vec = _clr_transform(raw, pseudocount)
    abundances = _inv_clr(clr_vec)

    kingdom_fracs: dict[str, float] = {}
    for k_label, abund in zip(kingdom_labels, abundances):
        kingdom_fracs[k_label] = kingdom_fracs.get(k_label, 0.0) + abund

    return {
        "zone": zone_name,
        "zone_type": zone_type,
        "taxa": taxa_names,
        "abundances": abundances.tolist(),
        "kingdom_fractions": {k: round(v, 4) for k, v in kingdom_fracs.items()},
    }


# ── Ecological drift ─────────────────────────────────────────────────

def _drift_alpha(epoch: int, total_epochs: int = 24) -> float:
    """Compute the Port↔Ocean blending factor for *epoch*.

    Returns a value in [0, 1] where 0 = pure Port, 1 = pure Open Ocean.
    The trajectory is: Port → Ocean → Port (sinusoidal half-cycle).
    """
    t = epoch / max(total_epochs - 1, 1)
    return float(np.sin(np.pi * t))


def _get_drifted_baseline(
    epoch: int,
    total_epochs: int,
    rng: np.random.Generator,
    noise_scale: float = 0.02,
) -> tuple[np.ndarray, list[str]]:
    """Return the time-dependent background profile and taxon order.

    Applies GRUMB CLR-space blending between Coastal Port and Open Ocean
    profiles, then adds small stochastic noise to simulate ecological
    variability.
    """
    taxa = sorted(
        set(COASTAL_PORT_PROFILE.keys()) | set(OPEN_OCEAN_PROFILE.keys())
    )
    port_vec = np.array([COASTAL_PORT_PROFILE.get(t, 0.0) for t in taxa])
    ocean_vec = np.array([OPEN_OCEAN_PROFILE.get(t, 0.0) for t in taxa])

    alpha = _drift_alpha(epoch, total_epochs)
    baseline = _blend_clr(port_vec, ocean_vec, alpha)

    noise = rng.normal(0, noise_scale, size=len(baseline))
    baseline = baseline + noise
    baseline = np.clip(baseline, 1e-10, None)
    baseline = baseline / baseline.sum()

    return baseline, taxa


# ── Public class ─────────────────────────────────────────────────────

class MetagenomicSequencing:
    """Environmental metagenomic sequencing modality."""

    name = "sequencing"

    def __init__(
        self,
        read_depth: int = 100_000,
        pseudocount: float = 1e-6,
        total_epochs: int = 24,
        rng: np.random.Generator | None = None,
        clr_shift_scale: float = 0.15,
    ) -> None:
        self.read_depth = read_depth
        self.pseudocount = pseudocount
        self.total_epochs = total_epochs
        self.rng = rng if rng is not None else np.random.default_rng()
        self.clr_shift_scale = clr_shift_scale
        self._zone_seeds: dict[str, dict[str, Any]] = {}

    def seed_zones(self, zone_configs: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
        """Seed all zones with multi-kingdom log-ratio abundance arrays at t=0.

        Parameters
        ----------
        zone_configs:
            List of dicts with ``name`` and ``type`` keys (from config.yaml
            ``ship_graph.zones``).

        Returns the seeded profiles keyed by zone name.
        """
        for zc in zone_configs:
            seed = seed_zone_microbiome(
                zc["name"], zc["type"], self.rng, self.pseudocount,
            )
            self._zone_seeds[zc["name"]] = seed
        return dict(self._zone_seeds)

    def apply_microflora_disruption(
        self,
        baseline: np.ndarray,
        taxa: list[str],
        disruption_shifts: dict[str, dict[str, float]],
        total_disruption_magnitude: float,
    ) -> tuple[np.ndarray, dict[str, float]]:
        """Apply microflora disruption shifts to a baseline profile via CLR.

        When hosts with disrupted microbiomes shed altered native microbial
        signatures, the local community composition shifts.  This uses
        GRUMB CLR-space perturbation to modify the baseline profile.

        Returns the shifted profile and a dict of kingdom-level CLR deltas.
        """
        if total_disruption_magnitude <= 0 or not disruption_shifts:
            return baseline, {}

        clr_baseline = _clr_transform(baseline, self.pseudocount)
        shift_vec = np.zeros(len(taxa), dtype=np.float64)

        for disruption_type, markers in disruption_shifts.items():
            for taxon, multiplier in markers.items():
                if taxon in taxa:
                    idx = taxa.index(taxon)
                    shift_vec[idx] += (
                        np.log(multiplier)
                        * total_disruption_magnitude
                        * self.clr_shift_scale
                    )

        shifted_clr = clr_baseline + shift_vec
        shifted_profile = _inv_clr(shifted_clr)

        # Compute kingdom-level CLR deltas for anomaly scoring
        kingdom_deltas: dict[str, float] = {}
        for kingdom, kingdom_taxa in MULTI_KINGDOM_TAXA.items():
            indices = [taxa.index(t) for t in kingdom_taxa if t in taxa]
            if indices:
                baseline_kingdom_clr = float(np.mean(clr_baseline[indices]))
                shifted_kingdom_clr = float(np.mean(shifted_clr[indices]))
                kingdom_deltas[kingdom] = round(
                    shifted_kingdom_clr - baseline_kingdom_clr, 6,
                )

        return shifted_profile, kingdom_deltas

    def detect_microflora_anomaly(
        self,
        kingdom_deltas: dict[str, float],
        threshold: float = 0.05,
    ) -> dict[str, Any]:
        """Score kingdom-level CLR shifts for anomaly detection."""
        anomalies = {}
        overall_shift = 0.0
        for kingdom, delta in kingdom_deltas.items():
            abs_delta = abs(delta)
            overall_shift += abs_delta
            if abs_delta > threshold:
                anomalies[kingdom] = {
                    "clr_delta": delta,
                    "direction": "elevated" if delta > 0 else "depleted",
                    "anomaly_detected": True,
                }
        return {
            "anomaly_detected": len(anomalies) > 0,
            "overall_shift_magnitude": round(overall_shift, 6),
            "kingdom_anomalies": anomalies,
        }

    def query_ground_truth(
        self,
        json_data: dict[str, Any],
        zone_microflora_shifts: dict[str, dict[str, float]] | None = None,
    ) -> dict[str, Any]:
        """Consume ground-truth spaces and produce sequencing telemetry.

        For each zone:
        1. Build the time-dependent drifting baseline.
        2. Apply microflora disruption shifts (if any) via GRUMB CLR.
        3. Inject the pathogen as an additional taxon proportional to
           ``pathogen_mass`` using GRUMB CLR-space blending.
        4. Draw observed reads via ``numpy.random.multinomial``.
        5. Score kingdom-level anomalies from microflora shifts.
        """
        epoch = json_data.get("epoch", 0)
        spaces = json_data.get("spaces", {})
        zone_microflora_shifts = zone_microflora_shifts or {}

        zone_results: dict[str, dict[str, Any]] = {}

        for zone_id, zone in spaces.items():
            pathogen_mass = zone.get("pathogen_mass", 0.0)

            baseline, taxa = _get_drifted_baseline(
                epoch, self.total_epochs, self.rng
            )

            # Apply microflora disruption shifts from dual-signal shedding
            mf_shifts = zone_microflora_shifts.get(zone_id, {})
            total_disruption = sum(mf_shifts.values()) if mf_shifts else 0.0
            kingdom_deltas: dict[str, float] = {}

            if total_disruption > 0:
                disruption_markers: dict[str, dict[str, float]] = {}
                for d_type in mf_shifts:
                    if d_type in DISRUPTION_MARKERS:
                        disruption_markers[d_type] = DISRUPTION_MARKERS[d_type]
                baseline, kingdom_deltas = self.apply_microflora_disruption(
                    baseline, taxa, disruption_markers, total_disruption,
                )

            anomaly_report = self.detect_microflora_anomaly(kingdom_deltas)

            taxa_with_pathogen = taxa + [PATHOGEN_TAXON]
            pathogen_frac = pathogen_mass / (pathogen_mass + 100.0)
            env_frac = 1.0 - pathogen_frac
            full_profile = np.append(baseline * env_frac, pathogen_frac)
            full_profile = full_profile / full_profile.sum()

            reads = self.rng.multinomial(self.read_depth, full_profile)
            read_dict = {
                t: int(c) for t, c in zip(taxa_with_pathogen, reads) if c > 0
            }

            seed_info = self._zone_seeds.get(zone_id)

            zone_results[zone_id] = {
                "microbiome_id": zone.get("microbiome_id", "unknown"),
                "drift_alpha": round(_drift_alpha(epoch, self.total_epochs), 4),
                "regime": (
                    "open_ocean"
                    if _drift_alpha(epoch, self.total_epochs) > 0.5
                    else "coastal_port"
                ),
                "total_reads": self.read_depth,
                "pathogen_reads": read_dict.get(PATHOGEN_TAXON, 0),
                "read_counts": read_dict,
                "seeded_kingdoms": (
                    seed_info["kingdom_fractions"] if seed_info else None
                ),
                "pathogen_mass_by_id": zone.get("pathogen_mass_by_id", {}),
                "microflora_disruption": {
                    "kingdom_clr_deltas": kingdom_deltas,
                    "anomaly_report": anomaly_report,
                    "disruption_types_present": list(mf_shifts.keys()),
                    "total_disruption_magnitude": round(total_disruption, 4),
                },
            }

        return {
            "modality": self.name,
            "epoch": epoch,
            "zone_results": zone_results,
        }
