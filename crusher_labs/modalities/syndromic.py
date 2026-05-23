"""
crusher_labs.modalities.syndromic
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Syndromic surveillance – models sick-call reporting with:
- A parameterizable probability that truly symptomatic agents report.
- FRED-style categorized background noise (seasickness, fatigue,
  minor injury) so healthy agents generate realistic false-signal
  clutter with specific complaint reasons.
- Quarantine compliance tracking: when isolation is ordered, agents
  may stochastically refuse or delay compliance (FRED behavioral
  failure pattern from ``FRED/src/Person.h`` vaccine refusal logic).
"""

from __future__ import annotations

from typing import Any

import numpy as np


class SyndromicSurveillance:
    """Symptom-based screening modality with FRED-style behavioral noise."""

    name = "syndromic"

    def __init__(
        self,
        sick_call_probability: float = 0.70,
        background_noise_rate: float = 0.015,
        noise_categories: list[dict[str, Any]] | None = None,
        quarantine_compliance: float = 0.85,
        compliance_delay_epochs: int = 1,
        rng: np.random.Generator | None = None,
    ) -> None:
        self.sick_call_probability = sick_call_probability
        self.background_noise_rate = background_noise_rate
        self.quarantine_compliance = quarantine_compliance
        self.compliance_delay_epochs = compliance_delay_epochs
        self.rng = rng if rng is not None else np.random.default_rng()

        self.noise_categories = noise_categories or [
            {"reason": "seasickness",  "probability": 0.008},
            {"reason": "fatigue",      "probability": 0.005},
            {"reason": "minor_injury", "probability": 0.002},
        ]

    def query_ground_truth(self, json_data: dict[str, Any]) -> dict[str, Any]:
        """Parse ground-truth agent states and return sick-call roster.

        Returns:
        - ``sick_call_agents``: IDs that reported to sick-call this epoch.
        - ``true_positive_ids``: subset that are genuinely symptomatic.
        - ``noise_ids``: subset that are healthy but reported (background).
        - ``noise_reasons``: complaint reasons for noise reporters.
        - ``total_agents``: total agent count.
        """
        agents = json_data.get("agents", [])
        epoch = json_data.get("epoch", 0)

        sick_call_ids: list[int] = []
        true_positive_ids: list[int] = []
        noise_ids: list[int] = []
        noise_reasons: list[dict[str, Any]] = []

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
                reported, reason = self._check_background_noise(aid)
                if reported:
                    sick_call_ids.append(aid)
                    noise_ids.append(aid)
                    noise_reasons.append({"agent_id": aid, "reason": reason})

        return {
            "modality": self.name,
            "epoch": epoch,
            "sick_call_agents": sick_call_ids,
            "true_positive_ids": true_positive_ids,
            "noise_ids": noise_ids,
            "noise_reasons": noise_reasons,
            "sick_call_count": len(sick_call_ids),
            "total_agents": len(agents),
        }

    def _check_background_noise(self, aid: int) -> tuple[bool, str | None]:
        """FRED-style categorized background noise check.

        Each noise category has its own independent probability
        (ref: FRED ``Household.vaccination_probability`` pattern).
        """
        for cat in self.noise_categories:
            if self.rng.random() < cat["probability"]:
                return True, cat["reason"]
        return False, None

    def check_quarantine_compliance(
        self,
        agent_id: int,
        epochs_since_order: int,
    ) -> bool:
        """FRED-style quarantine compliance check.

        Returns ``True`` if the agent complies with isolation this epoch.
        Non-compliant agents eventually comply after a delay period
        (ref: FRED ``refuses_vaccines`` behavioral failure pattern).
        """
        if self.rng.random() < self.quarantine_compliance:
            return True
        if epochs_since_order >= self.compliance_delay_epochs:
            return True
        return False
