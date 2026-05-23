"""
crusher_labs.modalities.syndromic
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Syndromic surveillance – detects agents whose symptom status indicates
active illness.  This is the lowest-fidelity but fastest-cadence modality.
"""

from __future__ import annotations

from typing import Any


class SyndromicSurveillance:
    """Symptom-based screening modality."""

    name = "syndromic"

    def query_ground_truth(self, json_data: dict[str, Any]) -> dict[str, Any]:
        """Parse ground-truth state and return perceived syndromic data.

        Returns a dictionary with:
        - ``epoch``: the current simulation time-step.
        - ``flagged_agents``: list of agent IDs whose symptom status is
          anything other than ``"asymptomatic"``.
        - ``total_screened``: number of agents evaluated.
        """
        agents = json_data.get("agents", [])
        flagged = [
            a["agent_id"]
            for a in agents
            if a.get("symptom_status") != "asymptomatic"
        ]
        return {
            "modality": self.name,
            "epoch": json_data.get("epoch"),
            "flagged_agents": flagged,
            "total_screened": len(agents),
        }
