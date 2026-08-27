"""
crusher_labs.modalities.syndromic
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Syndromic surveillance – models sick-call reporting with:
- A parameterizable probability that truly symptomatic agents report.
- Optional detection_delay_hours gate after symptom onset.
- Optional proactive crew screening on a fixed interval.
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

from engines.sim_clock import SimClock
from simulation_utils.numeric import default_simulation_rng


def _agent_is_crew(agent: dict[str, Any]) -> bool:
    role = str(agent.get("role") or "").lower()
    if role == "crew":
        return True
    if role == "passenger":
        return False
    a_class = str(agent.get("agent_class") or "").lower()
    return a_class.startswith("crew")


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
        reluctant_fraction: float = 0.75,
        reluctant_delay_epochs: int = 48,
        compliance_by_class: dict[str, float] | None = None,
        detection_delay_epochs: int = 0,
        crew_screening_interval_epochs: int | None = None,
        reluctant_delay_hours: float | None = None,
        compliance_delay_hours: float | None = None,
        detection_delay_hours: float | None = None,
        crew_screening_interval_hours: float | None = None,
        clock: SimClock | None = None,
        rng: np.random.Generator | None = None,
    ) -> None:
        self.sick_call_probability = sick_call_probability
        self.clock = clock or SimClock()
        self.background_noise_rate = background_noise_rate
        self.quarantine_compliance = quarantine_compliance
        # Deprecated: forced post-delay compliance removed. Kept for config compat.
        self.compliance_delay_epochs = (
            self.clock.epochs_for_hours(compliance_delay_hours)
            if compliance_delay_hours is not None
            else compliance_delay_epochs
        )
        self.reluctant_fraction = float(reluctant_fraction)
        self.reluctant_delay_epochs = (
            self.clock.epochs_for_hours(reluctant_delay_hours)
            if reluctant_delay_hours is not None
            else int(reluctant_delay_epochs)
        )
        self.compliance_by_class = dict(compliance_by_class or {})
        self.detection_delay_epochs = (
            self.clock.epochs_for_hours(detection_delay_hours)
            if detection_delay_hours is not None
            else max(0, int(detection_delay_epochs))
        )
        if crew_screening_interval_hours is not None:
            crew_screening_interval_epochs = self.clock.epochs_for_hours(
                crew_screening_interval_hours,
            )
        if crew_screening_interval_epochs is None:
            self.crew_screening_interval_epochs: int | None = None
        else:
            interval = int(crew_screening_interval_epochs)
            self.crew_screening_interval_epochs = interval if interval > 0 else None
        self.rng = rng if rng is not None else default_simulation_rng()
        # Sticky per-agent compliance class for the cruise (compliant/reluctant/defiant)
        self._compliance_class: dict[int, str] = {}
        # First epoch agent observed symptomatic (for detection_delay_hours)
        self._symptom_onset_epoch: dict[int, int] = {}

        # None → built-in defaults; explicit [] disables background noise categories.
        if noise_categories is None:
            self.noise_categories = [
                {"reason": "seasickness",  "probability_per_day": 0.0042},
                {"reason": "fatigue",      "probability_per_day": 0.0030},
                {"reason": "minor_injury", "probability_per_day": 0.0020},
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
        epoch: int,
        overrides: dict[int, str],
        beliefs: dict[int, dict[str, float]],
        chronic_mods: dict[int, dict[str, float]],
        sick_call_ids: list[int],
        true_positive_ids: list[int],
    ) -> None:
        if aid not in self._symptom_onset_epoch:
            self._symptom_onset_epoch[aid] = int(epoch)
        override = overrides.get(aid, "")
        if override == "hide_symptoms":
            return
        if override == "report_sick_call":
            sick_call_ids.append(aid)
            true_positive_ids.append(aid)
            return
        onset = self._symptom_onset_epoch[aid]
        if (int(epoch) - onset) < self.detection_delay_epochs:
            return
        if self.sick_call_probability <= 0.0:
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
        prob = self.clock.probability_per_epoch(prob)
        if self.rng.random() < prob:
            sick_call_ids.append(aid)
            true_positive_ids.append(aid)

    def _apply_crew_screening(
        self,
        agents: list[dict[str, Any]],
        epoch: int,
        sick_call_ids: list[int],
        crew_screening_ids: list[int],
    ) -> None:
        interval = self.crew_screening_interval_epochs
        if interval is None or interval <= 0:
            return
        if int(epoch) % interval != 0:
            return
        from telemetry_buffer.agent_axes import agent_is_isolated

        already = set(sick_call_ids)
        for agent in agents:
            aid = int(agent["agent_id"])
            if aid in already:
                continue
            if agent_is_isolated(agent):
                continue
            if not _agent_is_crew(agent):
                continue
            sick_call_ids.append(aid)
            crew_screening_ids.append(aid)
            already.add(aid)

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
        - ``crew_screening_ids``: crew added via proactive screening.
        - ``total_agents``: total agent count.
        """
        agents = json_data.get("agents", [])
        epoch = json_data.get("epoch", 0)

        sick_call_ids: list[int] = []
        true_positive_ids: list[int] = []
        noise_ids: list[int] = []
        noise_reasons: list[dict[str, Any]] = []
        crew_screening_ids: list[int] = []

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
                    aid, epoch, overrides, beliefs, chronic_mods,
                    sick_call_ids, true_positive_ids,
                )
            else:
                reported, reason = self._check_background_noise(aid)
                if reported:
                    sick_call_ids.append(aid)
                    noise_ids.append(aid)
                    noise_reasons.append({"agent_id": aid, "reason": reason})

        self._apply_crew_screening(
            agents, epoch, sick_call_ids, crew_screening_ids,
        )

        return {
            "modality": self.name,
            "epoch": epoch,
            "sick_call_agents": sick_call_ids,
            "true_positive_ids": true_positive_ids,
            "noise_ids": noise_ids,
            "noise_reasons": noise_reasons,
            "crew_screening_ids": crew_screening_ids,
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
            probability = self.clock.probability_per_epoch(float(
                cat.get("probability_per_day", cat.get("probability", 0.0)),
            ))
            if self.rng.random() < probability:
                return True, cat["reason"]
        return False, None

    def _resolve_base_compliance(
        self,
        agent_class: str | None,
        chronic_compliance_boost: float,
    ) -> float:
        """Population (or class-specific) compliance fraction, chronic-boosted."""
        base = self.quarantine_compliance
        if agent_class and self.compliance_by_class:
            a_class = str(agent_class)
            if a_class in self.compliance_by_class:
                base = float(self.compliance_by_class[a_class])
            else:
                # role_group keys: "crew" / "passenger" match class_id prefixes
                for key, val in self.compliance_by_class.items():
                    if a_class.startswith(f"{key}_") or a_class == key:
                        base = float(val)
                        break
                else:
                    # passenger_young → non-elderly passenger classes
                    if "passenger_young" in self.compliance_by_class and (
                        a_class.startswith("passenger_")
                        and a_class != "passenger_elderly"
                    ):
                        base = float(self.compliance_by_class["passenger_young"])
        return min(1.0, max(0.0, base + chronic_compliance_boost))

    def assign_compliance_class(
        self,
        agent_id: int,
        *,
        agent_class: str | None = None,
        chronic_compliance_boost: float = 0.0,
        behavioral_override: str | None = None,
    ) -> str:
        """Assign sticky compliance class at first quarantine order (idempotent)."""
        if agent_id in self._compliance_class:
            return self._compliance_class[agent_id]

        if behavioral_override == "refuse_quarantine":
            cls = "defiant"
        else:
            effective = self._resolve_base_compliance(
                agent_class, chronic_compliance_boost,
            )
            draw = float(self.rng.random())
            if draw < effective:
                cls = "compliant"
            elif draw < effective + (1.0 - effective) * self.reluctant_fraction:
                cls = "reluctant"
            else:
                cls = "defiant"
        self._compliance_class[agent_id] = cls
        return cls

    def check_quarantine_compliance(
        self,
        agent_id: int,
        epochs_since_order: int,
        behavioral_override: str | None = None,
        chronic_compliance_boost: float = 0.0,
        agent_class: str | None = None,
        is_symptomatic: bool = False,
    ) -> bool:
        """Bimodal quarantine compliance (compliant / reluctant / defiant).

        Compliance class is drawn once per agent at first order and sticky.
        - compliant: follows immediately
        - reluctant: complies after ``reluctant_delay_hours`` or if symptomatic
        - defiant: never complies (unless override cleared)

        The legacy ``compliance_delay_hours`` forced-compliance path is removed.
        """
        if behavioral_override == "refuse_quarantine":
            self._compliance_class[agent_id] = "defiant"
            return False

        cls = self.assign_compliance_class(
            agent_id,
            agent_class=agent_class,
            chronic_compliance_boost=chronic_compliance_boost,
            behavioral_override=behavioral_override,
        )
        if cls == "compliant":
            return True
        if cls == "defiant":
            return False
        # reluctant
        if is_symptomatic:
            return True
        return epochs_since_order >= self.reluctant_delay_epochs
