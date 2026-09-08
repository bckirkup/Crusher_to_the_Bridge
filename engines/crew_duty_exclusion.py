"""VSP crew duty exclusion: a regulated removal, not an epidemiological rate.

CDC's Vessel Sanitation Program *requires* a crew member meeting the acute
gastroenteritis case definition to be taken off duty and isolated — a food
employee "until symptom-free for a minimum of 48 hours" with documented
medical clearance before returning to work, other crew for a minimum of 24
hours (VSP 2018 Operations Manual section 4.4.1.1.1). The same manual only
*advises* isolation of passengers (section 4.4.2.1), so the rule here is
crew-only by construction and passenger behaviour is untouched.

Three things this module deliberately does not introduce:

* No epidemiological constant. The two durations are the regulation's own
  numbers, read from the manual and stated in hours; nothing here is chosen
  to move an anchor, and neither duration may be tuned against A9.
* No new ascertainment parameter. Exclusion fires on a case the ship has
  already *identified* — an agent in ``ever_reported_ids``, i.e. one that
  reached the existing sick-call/reporting ladder. VSP's mandatory-reporting
  requirement is represented by using that ladder, not by adding a second
  detection probability beside it.
* No sourced compliance share. The fraction of maritime crew who actually
  comply with an enforced duty exclusion is null in the literature
  (tranche 33). ``compliance_fraction`` therefore defaults to 1.0, which is
  the *upper bound* on what the structure can buy, and is declared as such:
  a run at 1.0 measures the most this mechanism can remove, not an estimate
  of what it does remove. Lower values are an explicit swept operational arm
  and may not be selected by which one reproduces an anchor.

Medical clearance is the manual's third requirement, and it enters as a
duration rather than a capability: the manual requires "follow-up with and
receive approval by designated medical personnel before returning crew to
work" but states no interval for it, and no maritime source quantifies how
long that review takes. It is therefore ``medical_clearance_delay_hours``,
null-sourced and defaulting to 0.0 h — release at the regulation's own stated
minimum — and is an exposed operational arm, never a fitted delay.

Food-employee status is positional in this model: the food-handler contact
multiplier applies to a crew member *while working in a service zone*, so a
crew agent is treated as a food employee here exactly when its work zone is
one of the transmission core's service zones. That is the same population the
48-hour clause covers, and it leaves the residual — a non-galley crew member
who touches food while passing through — on the 24-hour clause, which is the
conservative direction for this rule's effect.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from engines.sim_clock import SimClock

# VSP 2018 Operations Manual section 4.4.1.1.1, "Symptomatic and Meeting the
# Case Definition for Acute Gastroenteritis (AGE)". Grade A (regulation, read
# from the manual). Origin: CDC VSP; not an epidemiological measurement, and
# not fitted to anything.
FOOD_EMPLOYEE_SYMPTOM_FREE_HOURS = 48.0
NONFOOD_CREW_SYMPTOM_FREE_HOURS = 24.0

# Maritime compliance with the exclusion is null (tranche 33). 1.0 is the
# enforced-regulation upper bound, declared, not measured.
DEFAULT_EXCLUSION_COMPLIANCE = 1.0

# The manual requires medical approval before return to work but states no
# interval for it, and the maritime review delay is null. 0.0 h holds release
# at the regulation's stated minimum; a declared arm, not a measurement, and
# it may not be tuned against an anchor.
DEFAULT_MEDICAL_CLEARANCE_DELAY_HOURS = 0.0

ACTION_EXCLUDED = "crew_age_duty_exclusion"
ACTION_REFUSED = "refused_crew_age_duty_exclusion"
ACTION_RELEASED = "crew_age_duty_exclusion_release"

CREW_ROLE = "crew"


@dataclass(frozen=True)
class CrewDutyExclusionPolicy:
    """The regulation as configured: on/off, durations, compliance arm."""

    enabled: bool = False
    food_symptom_free_hours: float = FOOD_EMPLOYEE_SYMPTOM_FREE_HOURS
    nonfood_symptom_free_hours: float = NONFOOD_CREW_SYMPTOM_FREE_HOURS
    compliance_fraction: float = DEFAULT_EXCLUSION_COMPLIANCE
    medical_clearance_delay_hours: float = DEFAULT_MEDICAL_CLEARANCE_DELAY_HOURS

    @classmethod
    def from_config(cls, cfg: dict[str, Any] | None) -> CrewDutyExclusionPolicy:
        """Build the policy from a ``crew_duty_exclusion`` config block."""
        block = dict(cfg or {})
        policy = cls(
            enabled=bool(block.get("enabled", False)),
            food_symptom_free_hours=float(
                block.get(
                    "food_employee_symptom_free_hours",
                    FOOD_EMPLOYEE_SYMPTOM_FREE_HOURS,
                ),
            ),
            nonfood_symptom_free_hours=float(
                block.get(
                    "nonfood_crew_symptom_free_hours",
                    NONFOOD_CREW_SYMPTOM_FREE_HOURS,
                ),
            ),
            compliance_fraction=float(
                block.get("compliance_fraction", DEFAULT_EXCLUSION_COMPLIANCE),
            ),
            medical_clearance_delay_hours=float(
                block.get(
                    "medical_clearance_delay_hours",
                    DEFAULT_MEDICAL_CLEARANCE_DELAY_HOURS,
                ),
            ),
        )
        policy.validate()
        return policy

    def validate(self) -> None:
        """Refuse a negative duration or an out-of-range compliance share."""
        for name, hours in (
            ("food_employee_symptom_free_hours", self.food_symptom_free_hours),
            ("nonfood_crew_symptom_free_hours", self.nonfood_symptom_free_hours),
            ("medical_clearance_delay_hours", self.medical_clearance_delay_hours),
        ):
            if not np.isfinite(hours) or hours < 0.0:
                raise ValueError(f"{name} must be finite and non-negative: {hours!r}")
        share = self.compliance_fraction
        if not np.isfinite(share) or not 0.0 <= share <= 1.0:
            raise ValueError(
                f"compliance_fraction must lie in [0, 1]: {share!r}",
            )

    def symptom_free_hours(self, *, food_employee: bool) -> float:
        """The regulation's symptom-free duration for this crew member."""
        return (
            self.food_symptom_free_hours
            if food_employee
            else self.nonfood_symptom_free_hours
        )

    def return_to_work_hours(self, *, food_employee: bool) -> float:
        """Symptom-free minimum plus the declared clearance review."""
        return (
            self.symptom_free_hours(food_employee=food_employee)
            + self.medical_clearance_delay_hours
        )


@dataclass
class CrewDutyExclusionTracker:
    """Who is off duty, who counts as a food employee, and since when."""

    policy: CrewDutyExclusionPolicy
    food_employee_ids: frozenset[int] = frozenset()
    crew_ids: frozenset[int] = frozenset()
    excluded_ids: set[int] = field(default_factory=set)
    last_symptom_epoch: dict[int, int] = field(default_factory=dict)
    refusers: set[int] = field(default_factory=set)
    rng: Any = None

    @property
    def enabled(self) -> bool:
        return self.policy.enabled

    def required_epochs(self, agent_id: int, clock: SimClock) -> int:
        """Symptom-free epochs the regulation asks of this crew member."""
        hours = self.policy.return_to_work_hours(
            food_employee=agent_id in self.food_employee_ids,
        )
        return clock.epochs_for_hours(hours)

    def complies(self, agent_id: int) -> bool:
        """Sticky per-agent draw against the declared compliance arm.

        At the default 1.0 no draw happens at all, so the upper-bound arm is
        bit-identical whatever the RNG state.
        """
        share = self.policy.compliance_fraction
        if share >= 1.0:
            return True
        if agent_id in self.refusers:
            return False
        if share <= 0.0 or self.rng is None:
            self.refusers.add(agent_id)
            return False
        if float(self.rng.random()) < share:
            return True
        self.refusers.add(agent_id)
        return False

    def note_symptoms(self, epoch: int, agent_ids: Iterable[int]) -> None:
        """Record that these agents were still symptomatic at *epoch*."""
        for agent_id in agent_ids:
            self.last_symptom_epoch[agent_id] = epoch

    def due_for_release(self, epoch: int, clock: SimClock) -> set[int]:
        """Excluded crew who have now been symptom-free long enough."""
        return {
            agent_id
            for agent_id in self.excluded_ids
            if epoch - self.last_symptom_epoch.get(agent_id, epoch)
            >= self.required_epochs(agent_id, clock)
        }


def is_food_employee(agent: Any, service_zones: Iterable[str]) -> bool:
    """True when this agent is crew whose work zone is a service zone.

    The one definition of food-employee status in the model: the duty
    exclusion's 48-hour clause and the transmission core's food-handler
    exposure read it from here, so the two cannot disagree about who is a
    food employee.
    """
    return (
        getattr(agent, "role", "") == CREW_ROLE
        and getattr(agent, "work_zone", "") in set(service_zones)
    )


def food_employee_ids(
    agents: Iterable[Any],
    service_zones: Iterable[str],
) -> frozenset[int]:
    """Crew whose work zone is a service zone — the 48-hour population."""
    zones = set(service_zones)
    return frozenset(
        int(agent.agent_id)
        for agent in agents
        if is_food_employee(agent, zones)
    )


def crew_ids(agents: Iterable[Any]) -> frozenset[int]:
    """Every crew agent, food employee or not."""
    return frozenset(
        int(agent.agent_id)
        for agent in agents
        if getattr(agent, "role", "") == CREW_ROLE
    )


def build_tracker(
    cfg: dict[str, Any] | None,
    agents: Iterable[Any],
    service_zones: Iterable[str],
    rng: Any = None,
) -> CrewDutyExclusionTracker:
    """Assemble the tracker for one voyage's crew complement."""
    roster = list(agents)
    return CrewDutyExclusionTracker(
        policy=CrewDutyExclusionPolicy.from_config(cfg),
        food_employee_ids=food_employee_ids(roster, service_zones),
        crew_ids=crew_ids(roster),
        rng=rng,
    )
