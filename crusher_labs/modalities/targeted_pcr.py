"""
crusher_labs.modalities.targeted_pcr
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Targeted PCR – RT-qPCR panel for environmental zone sampling.
Checks pathogen mass in each zone against the PCR limit of detection.
"""

from __future__ import annotations

from typing import Any

# Placeholder LOD; will be loaded from config.yaml in Phase 2.
_DEFAULT_LOD = 1.0


class TargetedPCR:
    """RT-qPCR environmental sampling modality."""

    name = "targeted_pcr"

    def __init__(self, lod: float = _DEFAULT_LOD) -> None:
        self.lod = lod

    def query_ground_truth(self, json_data: dict[str, Any]) -> dict[str, Any]:
        """Parse ground-truth state and return perceived PCR results.

        Returns a dictionary with:
        - ``epoch``: the current simulation time-step.
        - ``zone_results``: dict mapping zone IDs to a boolean ``detected``
          flag (True when pathogen mass ≥ LOD).
        """
        spaces = json_data.get("spaces", {})
        zone_results = {
            zone_id: {
                "detected": zone.get("pathogen_mass", 0.0) >= self.lod,
                "pathogen_mass_estimate": zone.get("pathogen_mass", 0.0),
            }
            for zone_id, zone in spaces.items()
        }
        return {
            "modality": self.name,
            "epoch": json_data.get("epoch"),
            "zone_results": zone_results,
        }
