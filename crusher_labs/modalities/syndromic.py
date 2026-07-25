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


from simulation_utils.numeric import default_simulation_rng


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
        self.rng = rng if rng is not None else default_simulation_rng()

        # None → built-in defaults; explicit [] disables background noise categories.
        if noise_categories is None:
            self.noise_categories = [
                {"reason": "seasickness",  "probability": 0.008},
                {"reason": "fatigue",      "probability": 0.005},
                {"reason": "minor_injury", "probability": 0.002},
            ]
        else:
            self.noise_categories = list(noise_categories)

    @staticmethod
    def effective_sick_call_probability(
        base_probability: float,
        severity_belief: float = 0.5,
        trust_medical: float = 0.75,
    ) -> float:
        """Scale base sick-call rate by agent beliefs (Layer 1)."""
        sev = max(0.1, min(1.0, float(severity_belief)))
        trust = max(0.0, min(1.0, float(trust_medical)))
        return base_probability * sev * (0.5 + 0.5 * trust)

    def _process_symptomatic_agent(
        self,
        aid: int,
        overrides: dict[int, str],
        beliefs: dict[int, dict[str, float]],
        chronic_mods: dict[int, dict[str, float]],
        sick_call_ids: list[int],
        true_positive_ids: list[int],
    ) -> None:
        override = overrides.get(aid, "")
        if override == "hide_symptoms":
            return
        if override == "report_sick_call":
            sick_call_ids.append(aid)
            true_positive_ids.append(aid)
            return
        inf = beliefs.get(aid, {})
        prob = self.effective_sick_call_probability(
            self.sick_call_probability,
            severity_belief=inf.get("severity_belief", 0.5),
            trust_medical=inf.get("trust_medical", 0.75),
        )
        agent_chronic = chronic_mods.get(aid, {})
        prob = min(1.0, prob + agent_chronic.get(
            "sick_call_probability_boost", 0.0,
        ))
        if self.rng.random() < prob:
            sick_call_ids.append(aid)
            true_positive_ids.append(aid)

    def query_ground_truth(
        self,
        json_data: dict[str, Any],
        behavioral_overrides: dict[int, str] | None = None,
        information_beliefs: dict[int, dict[str, float]] | None = None,
        chronic_behavioral_mods: dict[int, dict[str, float]] | None = None,
    ) -> dict[str, Any]:
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

        from telemetry_buffer.agent_axes import (
            COMPLIANCE_NON_COMPLIANT,
            agent_has_symptomatic_presentation,
            agent_is_isolated,
            resolve_agent_axes,
        )

        overrides = behavioral_overrides or {}
        beliefs = information_beliefs or {}
        chronic_mods = chronic_behavioral_mods or {}

        for agent in agents:
            aid = agent["agent_id"]
            is_isolated = agent_is_isolated(agent)
            _, _, compliance = resolve_agent_axes(agent)
            is_symptomatic = (
                agent_has_symptomatic_presentation(agent)
                or compliance == COMPLIANCE_NON_COMPLIANT
            )

            if is_isolated:
                continue

            if is_symptomatic:
                self._process_symptomatic_agent(
                    aid, overrides, beliefs, chronic_mods,
                    sick_call_ids, true_positive_ids,
                )
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

    def _check_background_noise(self, _aid: int) -> tuple[bool, str | None]:
        """FRED-style categorized background noise check.

        ``background_noise_rate <= 0`` disables all background sick-call noise.
        Otherwise each noise category has its own independent probability
        (ref: FRED ``Household.vaccination_probability`` pattern).
        """
        if self.background_noise_rate <= 0.0:
            return False, None
        for cat in self.noise_categories:
            if self.rng.random() < cat["probability"]:
                return True, cat["reason"]
        return False, None

    def check_quarantine_compliance(
        self,
        _agent_id: int,
        epochs_since_order: int,
        behavioral_override: str | None = None,
        chronic_compliance_boost: float = 0.0,
    ) -> bool:
        """FRED-style quarantine compliance check.

        Returns ``True`` if the agent complies with isolation this epoch.
        Non-compliant agents eventually comply after a delay period
        (ref: FRED ``refuses_vaccines`` behavioral failure pattern).

        *chronic_compliance_boost* is an additive increase from chronic
        disease behavioral modifiers.
        """
        if behavioral_override == "refuse_quarantine":
            if epochs_since_order >= self.compliance_delay_epochs:
                return True
            return False
        effective_compliance = min(
            1.0, self.quarantine_compliance + chronic_compliance_boost,
        )
        if self.rng.random() < effective_compliance:
            return True
        if epochs_since_order >= self.compliance_delay_epochs:
            return True
        return False
