"""
crusher_labs.modalities.sequencing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Metagenomic shotgun sequencing of environmental samples.
Produces a simulated read-count distribution per zone.
"""

from __future__ import annotations

from typing import Any

# Placeholder LOD; will be loaded from config.yaml in Phase 2.
_DEFAULT_LOD = 0.1
_DEFAULT_READ_DEPTH = 100_000


class MetagenomicSequencing:
    """Environmental metagenomic sequencing modality."""

    name = "sequencing"

    def __init__(
        self,
        lod: float = _DEFAULT_LOD,
        read_depth: int = _DEFAULT_READ_DEPTH,
    ) -> None:
        self.lod = lod
        self.read_depth = read_depth

    def query_ground_truth(self, json_data: dict[str, Any]) -> dict[str, Any]:
        """Parse ground-truth state and return perceived sequencing results.

        Returns a dictionary with:
        - ``epoch``: the current simulation time-step.
        - ``zone_results``: dict mapping zone IDs to a dict with
          ``microbiome_id``, ``pathogen_detected`` flag, and a placeholder
          ``simulated_read_count``.
        """
        spaces = json_data.get("spaces", {})
        zone_results = {}
        for zone_id, zone in spaces.items():
            mass = zone.get("pathogen_mass", 0.0)
            detected = mass >= self.lod
            zone_results[zone_id] = {
                "microbiome_id": zone.get("microbiome_id", "unknown"),
                "pathogen_detected": detected,
                "simulated_read_count": int(mass * 10) if detected else 0,
            }
        return {
            "modality": self.name,
            "epoch": json_data.get("epoch"),
            "zone_results": zone_results,
        }
