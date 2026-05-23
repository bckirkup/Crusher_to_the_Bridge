"""
crusher_labs.modalities.syndromic
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Syndromic surveillance – models sick-call reporting with:
- A parameterizable probability that truly symptomatic agents report.
- A flat daily background noise rate (seasickness, fatigue, etc.) that
  causes healthy agents to report, creating realistic false-signal clutter.
"""

from __future__ import annotations

from typing import Any

import numpy as np


class SyndromicSurveillance:
    """Symptom-based screening modality with stochastic reporting."""

    name = "syndromic"

    def __init__(
        self,
        sick_call_probability: float = 0.70,
        background_noise_rate: float = 0.015,
        rng: np.random.Generator | None = None,
    ) -> None:
        self.sick_call_probability = sick_call_probability
        self.background_noise_rate = background_noise_rate
        self.rng = rng if rng is not None else np.random.default_rng()

    def query_ground_truth(self, json_data: dict[str, Any]) -> dict[str, Any]:
        """Parse ground-truth agent states and return sick-call roster.

        Returns:
        - ``sick_call_agents``: IDs that reported to sick-call this epoch.
        - ``true_positive_ids``: subset that are genuinely symptomatic.
        - ``noise_ids``: subset that are healthy but reported (background).
        - ``total_agents``: total agent count.
        """
        agents = json_data.get("agents", [])
        epoch = json_data.get("epoch", 0)

        sick_call_ids: list[int] = []
        true_positive_ids: list[int] = []
        noise_ids: list[int] = []

        for agent in agents:
            aid = agent["agent_id"]
            status = agent.get("symptom_status", "asymptomatic")
            is_isolated = status == "isolated"
            is_symptomatic = status not in ("asymptomatic", "isolated")

            if is_isolated:
                continue

            if is_symptomatic:
                if self.rng.random() < self.sick_call_probability:
                    sick_call_ids.append(aid)
                    true_positive_ids.append(aid)
            else:
                if self.rng.random() < self.background_noise_rate:
                    sick_call_ids.append(aid)
                    noise_ids.append(aid)

        return {
            "modality": self.name,
            "epoch": epoch,
            "sick_call_agents": sick_call_ids,
            "true_positive_ids": true_positive_ids,
            "noise_ids": noise_ids,
            "sick_call_count": len(sick_call_ids),
            "total_agents": len(agents),
        }
