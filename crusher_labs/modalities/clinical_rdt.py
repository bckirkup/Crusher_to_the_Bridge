"""
crusher_labs.modalities.clinical_rdt
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Clinical Rapid Diagnostic Test (RDT) – antigen-based lateral-flow assay.
Returns a binary positive / negative per agent based on shedding rate.
"""

from __future__ import annotations

from typing import Any

# Placeholder LOD; will be loaded from config.yaml in Phase 2.
_DEFAULT_LOD = 100.0


class ClinicalRDT:
    """Rapid antigen test modality."""

    name = "clinical_rdt"

    def __init__(self, lod: float = _DEFAULT_LOD) -> None:
        self.lod = lod

    def query_ground_truth(self, json_data: dict[str, Any]) -> dict[str, Any]:
        """Parse ground-truth state and return perceived RDT results.

        Returns a dictionary with:
        - ``epoch``: the current simulation time-step.
        - ``results``: list of dicts, each containing ``agent_id`` and a
          boolean ``positive`` flag (True when shedding rate ≥ LOD).
        """
        agents = json_data.get("agents", [])
        results = [
            {
                "agent_id": a["agent_id"],
                "positive": a.get("shedding_rate", 0.0) >= self.lod,
            }
            for a in agents
        ]
        return {
            "modality": self.name,
            "epoch": json_data.get("epoch"),
            "results": results,
        }
