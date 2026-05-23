"""
crusher_labs.modalities.targeted_pcr
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Targeted PCR – RT-qPCR panel for environmental zone or surface wipe samples.

Applies:
1. An extraction efficiency (η) to the absolute pathogen mass.
2. A standard logarithmic curve mapping recovered mass to a simulated
   Cycle Threshold:  ``Ct = -k · log₁₀(M_recovered) + b``
3. LOD gate: if ``Ct > LOD_threshold``, result is binary Negative;
   otherwise returns the quantitative Ct value.
"""

from __future__ import annotations

import math
from typing import Any


class TargetedPCR:
    """RT-qPCR environmental / surface-wipe sampling modality."""

    name = "targeted_pcr"

    def __init__(
        self,
        extraction_efficiency: float = 0.35,
        ct_slope: float = -3.322,
        ct_intercept: float = 40.0,
        lod_ct_threshold: float = 38.0,
    ) -> None:
        self.extraction_efficiency = extraction_efficiency
        self.ct_slope = ct_slope
        self.ct_intercept = ct_intercept
        self.lod_ct_threshold = lod_ct_threshold

    def _compute_ct(self, pathogen_mass: float) -> float | None:
        """Map absolute pathogen mass → Ct value after extraction.

        Returns ``None`` when recovered mass is effectively zero.
        """
        recovered = pathogen_mass * self.extraction_efficiency
        if recovered <= 0.0:
            return None
        ct = self.ct_slope * math.log10(recovered) + self.ct_intercept
        return round(ct, 2)

    def query_ground_truth(
        self,
        json_data: dict[str, Any],
        surface_wipe_zones: list[str] | None = None,
    ) -> dict[str, Any]:
        """Parse ground-truth state and return PCR results per zone.

        Parameters
        ----------
        json_data:
            Full ground-truth payload.
        surface_wipe_zones:
            If provided (escalation mode), only these zones are sampled
            via targeted surface wipes.  Otherwise all zones are tested.

        Returns a dictionary with ``zone_results`` mapping zone IDs to:
        - ``ct_value``: quantitative Ct (or ``None`` if no mass)
        - ``detected``: True if ``Ct ≤ LOD_threshold``
        - ``recovered_mass``: mass after extraction efficiency applied
        """
        epoch = json_data.get("epoch", 0)
        spaces = json_data.get("spaces", {})

        target_zones = surface_wipe_zones if surface_wipe_zones else list(spaces.keys())

        zone_results: dict[str, dict[str, Any]] = {}
        for zone_id in target_zones:
            zone = spaces.get(zone_id)
            if zone is None:
                continue

            mass = zone.get("pathogen_mass", 0.0)
            recovered = round(mass * self.extraction_efficiency, 4)
            ct = self._compute_ct(mass)

            if ct is not None:
                detected = ct <= self.lod_ct_threshold
            else:
                detected = False

            zone_results[zone_id] = {
                "raw_mass": mass,
                "recovered_mass": recovered,
                "ct_value": ct,
                "detected": detected,
            }

        return {
            "modality": self.name,
            "epoch": epoch,
            "zone_results": zone_results,
            "surface_wipe_mode": surface_wipe_zones is not None,
        }
