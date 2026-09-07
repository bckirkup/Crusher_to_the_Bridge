"""VSP's crew duty exclusion: who it removes, for how long, and who it spares.

The regulation (VSP 2018 Operations Manual 4.4.1.1.1) is the specification
under test: food employees off duty until symptom-free for a minimum of 48
hours with medical clearance, other crew 24 hours, passengers only advised
(4.4.2.1) and so untouched. These tests hold the durations to the manual and
the population to crew; none of them asserts an epidemiological outcome, so
none of them can be satisfied by moving a transmission constant.
"""

from __future__ import annotations

import numpy as np
import pytest

from engines.crew_duty_exclusion import (
    ACTION_EXCLUDED,
    ACTION_REFUSED,
    ACTION_RELEASED,
    FOOD_EMPLOYEE_SYMPTOM_FREE_HOURS,
    NONFOOD_CREW_SYMPTOM_FREE_HOURS,
    CrewDutyExclusionPolicy,
    CrewDutyExclusionTracker,
    build_tracker,
    crew_ids,
    food_employee_ids,
)
from engines.sim_clock import SimClock
from orchestrator_epoch import step_crew_duty_exclusion
from orchestrator_types import (
    STATUS_ALERT,
    STATUS_BASELINE,
    SimulationState,
)

# Explicit hourly grid: under the legacy mode an epoch *is* a day, and a
# 24-hour clause would then be one epoch, which tests nothing about duration.
CLOCK = SimClock(epoch_duration_hours=1.0, mode="hours")

FOOD_ID = 1
NONFOOD_ID = 2
PASSENGER_ID = 3


class _Agent:
    """The two roster attributes the classifier reads."""

    def __init__(self, agent_id: int, role: str, work_zone: str) -> None:
        self.agent_id = agent_id
        self.role = role
        self.work_zone = work_zone


ROSTER = [
    _Agent(FOOD_ID, "crew", "Galley_Main"),
    _Agent(NONFOOD_ID, "crew", "Engine_Room"),
    _Agent(PASSENGER_ID, "passenger", "Galley_Main"),
]
SERVICE_ZONES = frozenset({"Galley_Main", "Dining_Main"})


def _agent_row(agent_id: int, *, symptomatic: bool) -> dict[str, object]:
    return {
        "agent_id": agent_id,
        "infection_state": "infectious" if symptomatic else "susceptible",
        "symptom_presentation": "symptomatic" if symptomatic else "asymptomatic",
        "compliance_status": "compliant",
    }


def _enabled_tracker(**overrides: object) -> CrewDutyExclusionTracker:
    cfg: dict[str, object] = {"enabled": True}
    cfg.update(overrides)
    return build_tracker(cfg, ROSTER, SERVICE_ZONES, rng=np.random.default_rng(7))


def _state(*, reported: set[int], status: str = STATUS_BASELINE) -> SimulationState:
    state = SimulationState(trigger_status=status)
    state.ever_reported_ids.update(reported)
    return state


class TestRosterClassification:
    def test_food_employees_are_the_crew_working_service_zones(self) -> None:
        assert food_employee_ids(ROSTER, SERVICE_ZONES) == frozenset({FOOD_ID})

    def test_crew_ids_span_both_clauses_and_exclude_passengers(self) -> None:
        assert crew_ids(ROSTER) == frozenset({FOOD_ID, NONFOOD_ID})

    def test_a_passenger_in_a_galley_is_not_a_food_employee(self) -> None:
        assert PASSENGER_ID not in food_employee_ids(ROSTER, SERVICE_ZONES)


class TestPolicyDurations:
    def test_the_two_clauses_carry_the_manuals_hours(self) -> None:
        policy = CrewDutyExclusionPolicy()
        assert policy.symptom_free_hours(food_employee=True) == pytest.approx(48.0)
        assert policy.symptom_free_hours(food_employee=False) == pytest.approx(24.0)

    def test_the_food_clause_is_twice_the_other(self) -> None:
        assert (
            FOOD_EMPLOYEE_SYMPTOM_FREE_HOURS
            == 2.0 * NONFOOD_CREW_SYMPTOM_FREE_HOURS
        )

    @pytest.mark.parametrize("hours_per_epoch", [0.5, 1.0, 4.0, 6.0])
    def test_the_duration_is_a_duration_across_clock_grids(
        self, hours_per_epoch: float,
    ) -> None:
        """Epoch counts scale with the grid; the wall-clock hours do not."""
        clock = SimClock(
            epoch_duration_hours=hours_per_epoch, mode="hours",
        )
        tracker = _enabled_tracker()
        food = tracker.required_epochs(FOOD_ID, clock)
        nonfood = tracker.required_epochs(NONFOOD_ID, clock)
        assert food * hours_per_epoch == pytest.approx(48.0)
        assert nonfood * hours_per_epoch == pytest.approx(24.0)

    def test_clearance_review_lengthens_the_hold_and_defaults_to_nothing(
        self,
    ) -> None:
        base = _enabled_tracker()
        reviewed = _enabled_tracker(medical_clearance_delay_hours=12.0)
        assert base.required_epochs(NONFOOD_ID, CLOCK) == 24
        assert reviewed.required_epochs(NONFOOD_ID, CLOCK) == 36

    @pytest.mark.parametrize(
        "block",
        [
            {"food_employee_symptom_free_hours": -1.0},
            {"nonfood_crew_symptom_free_hours": float("nan")},
            {"compliance_fraction": 1.5},
            {"compliance_fraction": -0.1},
            {"medical_clearance_delay_hours": -4.0},
        ],
    )
    def test_an_impossible_policy_is_refused_not_clamped(
        self, block: dict[str, float],
    ) -> None:
        cfg = {"enabled": True, **block}
        with pytest.raises(ValueError):
            CrewDutyExclusionPolicy.from_config(cfg)


class TestExclusionStep:
    def test_disabled_is_the_baseline_and_touches_nothing(self) -> None:
        tracker = build_tracker(None, ROSTER, SERVICE_ZONES)
        state = _state(reported={FOOD_ID})
        step_crew_duty_exclusion(
            0, [_agent_row(FOOD_ID, symptomatic=True)], state, CLOCK, tracker,
        )
        assert not state.quarantined_ids
        assert not state.compliance_log

    def test_an_identified_symptomatic_crew_case_goes_off_duty(self) -> None:
        tracker = _enabled_tracker()
        state = _state(reported={FOOD_ID})
        step_crew_duty_exclusion(
            0, [_agent_row(FOOD_ID, symptomatic=True)], state, CLOCK, tracker,
        )
        assert FOOD_ID in tracker.excluded_ids
        assert FOOD_ID in state.quarantined_ids
        assert state.compliance_log[-1]["action"] == ACTION_EXCLUDED
        assert state.compliance_log[-1]["food_employee"] is True

    def test_it_fires_at_baseline_status_which_is_its_whole_difference(
        self,
    ) -> None:
        """SOP-008 is gated at ALERT; the regulation is not gated at all."""
        tracker = _enabled_tracker()
        state = _state(reported={NONFOOD_ID}, status=STATUS_BASELINE)
        step_crew_duty_exclusion(
            0, [_agent_row(NONFOOD_ID, symptomatic=True)], state, CLOCK, tracker,
        )
        assert NONFOOD_ID in state.quarantined_ids

    def test_an_unidentified_case_is_not_excluded(self) -> None:
        tracker = _enabled_tracker()
        state = _state(reported=set())
        step_crew_duty_exclusion(
            0, [_agent_row(FOOD_ID, symptomatic=True)], state, CLOCK, tracker,
        )
        assert not tracker.excluded_ids

    def test_an_asymptomatic_reported_crew_member_stays_on_duty(self) -> None:
        tracker = _enabled_tracker()
        state = _state(reported={FOOD_ID})
        step_crew_duty_exclusion(
            0, [_agent_row(FOOD_ID, symptomatic=False)], state, CLOCK, tracker,
        )
        assert not tracker.excluded_ids

    def test_a_symptomatic_reported_passenger_is_untouched(self) -> None:
        """4.4.2.1 only advises isolation of passengers."""
        tracker = _enabled_tracker()
        state = _state(reported={PASSENGER_ID})
        step_crew_duty_exclusion(
            0, [_agent_row(PASSENGER_ID, symptomatic=True)], state, CLOCK, tracker,
        )
        assert not tracker.excluded_ids
        assert PASSENGER_ID not in state.quarantined_ids


class TestReleaseTiming:
    def _hold(
        self,
        agent_id: int,
        *,
        symptom_epochs: int,
        status: str = STATUS_BASELINE,
    ) -> tuple[CrewDutyExclusionTracker, SimulationState]:
        tracker = _enabled_tracker()
        state = _state(reported={agent_id}, status=status)
        for epoch in range(symptom_epochs):
            step_crew_duty_exclusion(
                epoch, [_agent_row(agent_id, symptomatic=True)], state, CLOCK,
                tracker,
            )
        return tracker, state

    def _run_recovered(
        self,
        tracker: CrewDutyExclusionTracker,
        state: SimulationState,
        agent_id: int,
        *,
        start: int,
        epochs: int,
    ) -> None:
        for epoch in range(start, start + epochs):
            step_crew_duty_exclusion(
                epoch, [_agent_row(agent_id, symptomatic=False)], state, CLOCK,
                tracker,
            )

    @pytest.mark.parametrize(
        ("agent_id", "hold_hours"),
        [(FOOD_ID, 48), (NONFOOD_ID, 24)],
    )
    def test_release_lands_on_the_clause_for_that_role(
        self, agent_id: int, hold_hours: int,
    ) -> None:
        hold_epochs = int(hold_hours / CLOCK.hours_per_epoch)
        tracker, state = self._hold(agent_id, symptom_epochs=1)
        self._run_recovered(
            tracker, state, agent_id, start=1, epochs=hold_epochs - 1,
        )
        assert agent_id in tracker.excluded_ids, "released before the minimum"
        self._run_recovered(
            tracker, state, agent_id, start=hold_epochs, epochs=1,
        )
        assert agent_id not in tracker.excluded_ids
        assert agent_id not in state.quarantined_ids
        assert state.compliance_log[-1]["action"] == ACTION_RELEASED

    def test_a_relapse_restarts_the_symptom_free_clock(self) -> None:
        hold = int(NONFOOD_CREW_SYMPTOM_FREE_HOURS / CLOCK.hours_per_epoch)
        tracker, state = self._hold(NONFOOD_ID, symptom_epochs=1)
        self._run_recovered(tracker, state, NONFOOD_ID, start=1, epochs=hold - 4)
        relapse = hold - 3
        step_crew_duty_exclusion(
            relapse, [_agent_row(NONFOOD_ID, symptomatic=True)], state, CLOCK,
            tracker,
        )
        self._run_recovered(
            tracker, state, NONFOOD_ID, start=relapse + 1, epochs=hold - 1,
        )
        assert NONFOOD_ID in tracker.excluded_ids, "clock did not restart"
        self._run_recovered(
            tracker, state, NONFOOD_ID, start=relapse + hold, epochs=1,
        )
        assert NONFOOD_ID not in tracker.excluded_ids

    def test_release_does_not_lift_an_independent_confinement(self) -> None:
        """Under ALERT the outbreak response is holding them, not this rule."""
        tracker, state = self._hold(
            NONFOOD_ID, symptom_epochs=1, status=STATUS_ALERT,
        )
        self._run_recovered(tracker, state, NONFOOD_ID, start=1, epochs=40)
        assert NONFOOD_ID not in tracker.excluded_ids
        assert NONFOOD_ID in state.quarantined_ids


class TestComplianceArm:
    def test_the_default_arm_is_the_enforced_upper_bound(self) -> None:
        tracker = _enabled_tracker()
        assert tracker.policy.compliance_fraction == pytest.approx(1.0)
        assert tracker.complies(FOOD_ID)

    def test_zero_compliance_reproduces_the_baseline_exclusion_set(self) -> None:
        tracker = _enabled_tracker(compliance_fraction=0.0)
        state = _state(reported={FOOD_ID})
        step_crew_duty_exclusion(
            0, [_agent_row(FOOD_ID, symptomatic=True)], state, CLOCK, tracker,
        )
        assert not tracker.excluded_ids
        assert FOOD_ID not in state.quarantined_ids
        assert state.compliance_log[-1]["action"] == ACTION_REFUSED

    def test_a_refusal_is_sticky_rather_than_redrawn_each_epoch(self) -> None:
        tracker = _enabled_tracker(compliance_fraction=0.5)
        refusers = {
            aid for aid in range(200) if not tracker.complies(aid)
        }
        assert refusers, "a 0.5 arm that never refuses is not an arm"
        assert all(not tracker.complies(aid) for aid in refusers)

    @pytest.mark.parametrize("share", [0.25, 0.5, 0.75])
    def test_more_compliance_excludes_more_crew(self, share: float) -> None:
        tracker = _enabled_tracker(compliance_fraction=share)
        complied = sum(tracker.complies(aid) for aid in range(400))
        assert 0 < complied < 400
        assert complied == pytest.approx(400 * share, rel=0.25)
