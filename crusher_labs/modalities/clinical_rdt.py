"""
crusher_labs.modalities.clinical_rdt
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Clinical Rapid Diagnostic Test (RDT) – antigen-based lateral-flow assay.

Applies an EMOD-style state-dependent sensitivity curve based on the
agent's current shedding rate:

    S(r) = S_max / (1 + exp(-k * (r - r_mid)))

Early shedders (low rate) have a high false-negative rate; sensitivity
peaks only as shedding intensifies.  Reference: EMOD-Generic
``Base_Sensitivity`` diagnostic pattern.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np


def _sigmoid_sensitivity(
    shedding_rate: float,
    s_max: float,
    k: float,
    midpoint: float,
) -> float:
    """EMOD-style sigmoid sensitivity as a function of shedding rate."""
    exponent = -k * (shedding_rate - midpoint)
    exponent = max(min(exponent, 500.0), -500.0)
    return s_max / (1.0 + math.exp(exponent))


class ClinicalRDT:
    """Rapid antigen test modality with shedding-dependent sensitivity."""

    name = "clinical_rdt"

    def __init__(
        self,
        base_sensitivity: float = 0.95,
        sigmoid_k: float = 0.08,
        sigmoid_midpoint: float = 50.0,
        specificity: float = 0.97,
        rng: np.random.Generator | None = None,
    ) -> None:
        self.base_sensitivity = base_sensitivity
        self.sigmoid_k = sigmoid_k
        self.sigmoid_midpoint = sigmoid_midpoint
        self.specificity = specificity
        self.rng = rng if rng is not None else np.random.default_rng()

    def query_ground_truth(
        self,
        json_data: dict[str, Any],
        sick_call_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """Test agents who reported to sick-call via RDT.

        Parameters
        ----------
        json_data:
            Full ground-truth payload.
        sick_call_ids:
            Agent IDs that reported to sick-call.  If ``None``, all agents
            are tested (fallback for standalone invocation).
        """
        agents = json_data.get("agents", [])
        epoch = json_data.get("epoch", 0)

        agent_map = {a["agent_id"]: a for a in agents}
        test_ids = sick_call_ids if sick_call_ids is not None else list(agent_map.keys())

        results: list[dict[str, Any]] = []

        for aid in test_ids:
            agent = agent_map.get(aid)
            if agent is None:
                continue

            shedding = agent.get("shedding_rate", 0.0)
            is_truly_infected = shedding > 0.0

            if is_truly_infected:
                sensitivity = _sigmoid_sensitivity(
                    shedding,
                    self.base_sensitivity,
                    self.sigmoid_k,
                    self.sigmoid_midpoint,
                )
                positive = self.rng.random() < sensitivity
            else:
                positive = self.rng.random() > self.specificity

            results.append({
                "agent_id": aid,
                "positive": bool(positive),
                "shedding_rate": shedding,
                "effective_sensitivity": round(
                    _sigmoid_sensitivity(
                        shedding,
                        self.base_sensitivity,
                        self.sigmoid_k,
                        self.sigmoid_midpoint,
                    ),
                    4,
                )
                if is_truly_infected
                else None,
            })

        return {
            "modality": self.name,
            "epoch": epoch,
            "results": results,
            "tested_count": len(results),
        }
