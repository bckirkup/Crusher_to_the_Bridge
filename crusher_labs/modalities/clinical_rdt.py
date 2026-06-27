"""
crusher_labs.modalities.clinical_rdt
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Clinical Rapid Diagnostic Test (RDT) – antigen-based lateral-flow assay.

Applies an EMOD-style state-dependent sensitivity curve based on the
agent's current shedding rate:

    S(r) = S_max / (1 + exp(-k * (r - r_mid)))

The sensitivity cap is further modulated by the agent's clinical
progression phase (early / peak / late) as defined in the EMOD-style
``emod_progression`` config block.  Early shedders have a hard cap on
achievable sensitivity, simulating the biological reality that antigen
tests miss low-titer infections.

Reference: EMOD-Generic ``Base_Sensitivity`` diagnostic pattern +
``Treatment_Fraction`` phase gating.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np


# ── EMOD clinical phase resolution ──────────────────────────────────

from simulation_utils.numeric import default_simulation_rng


def _resolve_shedding_phase(
    shedding_rate: float,
    phases: list[dict[str, Any]],
) -> dict[str, Any]:
    """Determine the EMOD shedding phase for a given rate.

    Phases are ordered ``[early, peak, late]`` with ascending
    ``max_rate`` thresholds.  Returns the matching phase dict.
    """
    for phase in phases:
        if shedding_rate <= phase["max_rate"]:
            return phase
    return phases[-1]


def _sigmoid_sensitivity(
    shedding_rate: float,
    s_max: float,
    k: float,
    midpoint: float,
    sensitivity_cap: float = 1.0,
) -> float:
    """EMOD-style sigmoid sensitivity with phase-dependent cap.

    The raw sigmoid ``S(r)`` is clamped to ``sensitivity_cap`` so that
    early-phase agents can never exceed a low detection ceiling.
    """
    exponent = -k * (shedding_rate - midpoint)
    exponent = max(min(exponent, 500.0), -500.0)
    raw = s_max / (1.0 + math.exp(exponent))
    return min(raw, sensitivity_cap)


class ClinicalRDT:
    """Rapid antigen test modality with EMOD-style state-dependent sensitivity."""

    name = "clinical_rdt"

    # Default shedding phases from EMOD progression config
    DEFAULT_PHASES = [
        {"name": "early", "max_rate": 20.0, "sensitivity_cap": 0.30},
        {"name": "peak",  "max_rate": 80.0, "sensitivity_cap": 0.95},
        {"name": "late",  "max_rate": 40.0, "sensitivity_cap": 0.80},
    ]

    def __init__(
        self,
        base_sensitivity: float = 0.95,
        sigmoid_k: float = 0.08,
        sigmoid_midpoint: float = 50.0,
        specificity: float = 0.97,
        shedding_phases: list[dict[str, Any]] | None = None,
        rng: np.random.Generator | None = None,
    ) -> None:
        self.base_sensitivity = base_sensitivity
        self.sigmoid_k = sigmoid_k
        self.sigmoid_midpoint = sigmoid_midpoint
        self.specificity = specificity
        self.shedding_phases = shedding_phases or self.DEFAULT_PHASES
        self.rng = rng if rng is not None else default_simulation_rng()

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
                phase = _resolve_shedding_phase(shedding, self.shedding_phases)
                sensitivity = _sigmoid_sensitivity(
                    shedding,
                    self.base_sensitivity,
                    self.sigmoid_k,
                    self.sigmoid_midpoint,
                    sensitivity_cap=phase["sensitivity_cap"],
                )
                positive = self.rng.random() < sensitivity
            else:
                phase = None
                positive = self.rng.random() > self.specificity

            results.append({
                "agent_id": aid,
                "positive": bool(positive),
                "shedding_rate": shedding,
                "clinical_phase": phase["name"] if phase else None,
                "effective_sensitivity": round(
                    _sigmoid_sensitivity(
                        shedding,
                        self.base_sensitivity,
                        self.sigmoid_k,
                        self.sigmoid_midpoint,
                        sensitivity_cap=phase["sensitivity_cap"],
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
