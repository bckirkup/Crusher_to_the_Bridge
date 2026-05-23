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
"""

from __future__ import annotations

from typing import Any

import numpy as np


# ── Mock background profiles (relative abundance vectors) ────────────
# Keys are pseudo-taxa; values are relative abundances that sum to ~1.
# These represent distinct ecological baselines for the two regimes.

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
    ) -> None:
        self.read_depth = read_depth
        self.pseudocount = pseudocount
        self.total_epochs = total_epochs
        self.rng = rng if rng is not None else np.random.default_rng()

    def query_ground_truth(self, json_data: dict[str, Any]) -> dict[str, Any]:
        """Consume ground-truth spaces and produce sequencing telemetry.

        For each zone:
        1. Build the time-dependent drifting baseline.
        2. Inject the pathogen as an additional taxon proportional to
           ``pathogen_mass`` using GRUMB CLR-space blending.
        3. Draw observed reads via ``numpy.random.multinomial``.
        """
        epoch = json_data.get("epoch", 0)
        spaces = json_data.get("spaces", {})

        zone_results: dict[str, dict[str, Any]] = {}

        for zone_id, zone in spaces.items():
            pathogen_mass = zone.get("pathogen_mass", 0.0)

            baseline, taxa = _get_drifted_baseline(
                epoch, self.total_epochs, self.rng
            )

            taxa_with_pathogen = taxa + [PATHOGEN_TAXON]
            pathogen_frac = pathogen_mass / (pathogen_mass + 100.0)
            env_frac = 1.0 - pathogen_frac
            full_profile = np.append(baseline * env_frac, pathogen_frac)
            full_profile = full_profile / full_profile.sum()

            reads = self.rng.multinomial(self.read_depth, full_profile)
            read_dict = {
                t: int(c) for t, c in zip(taxa_with_pathogen, reads) if c > 0
            }

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
            }

        return {
            "modality": self.name,
            "epoch": epoch,
            "zone_results": zone_results,
        }
