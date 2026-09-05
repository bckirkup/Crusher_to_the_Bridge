"""The host natural-history module owns the course of an infection.

Ownership tests: the transitions live in ``engines.natural_history`` and
nowhere else, so a later change to the timeline (A2–A5 in
``docs/proposals/defect_resolution_plan.md``) lands in one module.
Invariant tests: the ordering of the timeline holds for any profile, without
pinning a golden value.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Any

import numpy as np
import pytest

import engines.initiation as initiation
import orchestrator_epoch
from engines import natural_history
from engines.infection_dynamics_bridge import (
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
)
from engines.natural_history import (
    advance_infections,
    clearance_days,
    incubation_days,
    onset_day,
    project_legacy_illness,
    severity_on_day,
)
from engines.sim_clock import HOURS, SimClock

REPO_ROOT = Path(__file__).resolve().parent.parent
PATHOGEN = "norwalk_gi"
ZONE = "Deck_1"

_OWNED = (
    "incubation_days",
    "onset_day",
    "presentation_probability",
    "draw_symptom_onset",
    "draw_symptom_severity",
    "clearance_days",
    "advance_infections",
    "project_legacy_illness",
    "record_cleared_immunity",
    "severity_on_day",
)

_STATES = [
    "asymptomatic", "subclinical", "mild", "moderate", "severe_critical",
]


def _defined_functions(module: object) -> set[str]:
    tree = ast.parse(Path(inspect.getfile(module)).read_text(encoding="utf-8"))
    return {
        node.name for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }


def _agent(clock: SimClock, dose: float = 1e4) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=1,
        role="passenger",
        immune=False,
        home_zone=ZONE,
        dining_zone=ZONE,
        work_zone=ZONE,
        free_zone=ZONE,
        schedule=["Free"] * 4,
    )
    agent.clock = clock
    agent.current_location = ZONE
    agent.infect_with_pathogen(PATHOGEN, dose, 0)
    return agent


def _profile(**overrides: Any) -> dict[str, Any]:
    profile: dict[str, Any] = {
        "recovery_day": 3,
        "shedding_duration_days": 6,
        "symptom_onset_day": 1.0,
        "symptomatic_fraction": 1.0,
    }
    profile.update(overrides)
    return profile


class TestOwnership:
    def test_every_transition_is_defined_on_the_owner(self) -> None:
        defined = _defined_functions(natural_history)
        assert set(_OWNED) <= defined
        assert set(natural_history.__all__) >= set(_OWNED)

    @pytest.mark.parametrize("module", [orchestrator_epoch, initiation])
    def test_former_writers_define_no_transition_of_their_own(
        self, module: object,
    ) -> None:
        legacy = set(_OWNED) | {f"_{name}" for name in _OWNED} | {
            "_advance_agent_pathogen_infections",
        }
        assert not (_defined_functions(module) & legacy)

    def test_no_module_reaches_into_orchestrator_epoch_for_the_timeline(
        self,
    ) -> None:
        offenders = []
        for path in (REPO_ROOT / "engines").rglob("*.py"):
            if "from orchestrator_epoch import" in path.read_text(encoding="utf-8"):
                offenders.append(path.name)
        assert offenders == []


class TestTimelineInvariants:
    @pytest.mark.parametrize("hours", [1.0, 6.0, 24.0])
    @pytest.mark.parametrize("recovery_day,shedding_days", [(3, 6), (5, 5), (7, 2)])
    def test_shedding_never_clears_before_illness(
        self, hours: float, recovery_day: int, shedding_days: int,
    ) -> None:
        clock = SimClock(epoch_duration_hours=hours, mode=HOURS)
        agent = _agent(clock)
        profile = _profile(
            recovery_day=recovery_day, shedding_duration_days=shedding_days,
        )
        inf = agent.infections[PATHOGEN]
        onset = onset_day(agent, PATHOGEN, inf, profile, np.random.default_rng(0))
        illness_end, shedding_end = clearance_days(
            agent, PATHOGEN, inf, profile, onset,
        )
        assert onset <= illness_end <= shedding_end
        assert illness_end == pytest.approx(onset + recovery_day)

    @pytest.mark.parametrize("hours", [1.0, 6.0, 24.0])
    def test_states_move_in_order_and_never_back(self, hours: float) -> None:
        clock = SimClock(epoch_duration_hours=hours, mode=HOURS)
        agent = _agent(clock)
        profile = _profile()
        rng = np.random.default_rng(3)
        order = {
            (InfectionStatus.INFECTED, IllnessStatus.NOT_ILL): 0,
            (InfectionStatus.INFECTED, IllnessStatus.SYMPTOMATIC): 1,
            (InfectionStatus.INFECTED, IllnessStatus.RECOVERED): 2,
            (InfectionStatus.RECOVERED, IllnessStatus.RECOVERED): 3,
        }
        seen = [0]
        for _ in range(int(clock.epochs_for_days(12))):
            advance_infections(agent, {PATHOGEN: profile}, rng)
            project_legacy_illness(agent)
            inf = agent.infections[PATHOGEN]
            rank = order[(inf["status"], inf["illness"])]
            assert rank >= seen[-1]
            seen.append(rank)
            assert agent.infection_status == inf["status"]
        assert seen[-1] == 3
        assert set(seen) == {0, 1, 2, 3}

    def test_incubation_is_drawn_once_per_infection(self) -> None:
        clock = SimClock(epoch_duration_hours=1.0, mode=HOURS)
        agent = _agent(clock)
        profile = _profile(
            incubation={"median_days": 1.2, "distribution": "lognormal"},
        )
        rng = np.random.default_rng(11)
        inf = agent.infections[PATHOGEN]
        first = incubation_days(agent, PATHOGEN, inf, profile, rng)
        assert inf["incubation_days"] == first
        for _ in range(4):
            assert incubation_days(agent, PATHOGEN, inf, profile, rng) == first

    def test_a_host_that_never_presents_still_clears(self) -> None:
        clock = SimClock(epoch_duration_hours=6.0, mode=HOURS)
        agent = _agent(clock)
        profile = _profile(symptomatic_fraction=0.0)
        rng = np.random.default_rng(5)
        for _ in range(int(clock.epochs_for_days(10))):
            advance_infections(agent, {PATHOGEN: profile}, rng)
        inf = agent.infections[PATHOGEN]
        assert inf["symptom_severity"] == "asymptomatic"
        assert inf.get("presented") is None
        assert inf["status"] == InfectionStatus.RECOVERED


def _severity_profile(offsets: list[int] | None = None, **overrides: Any) -> dict:
    severity: dict[str, Any] = {
        "states": _STATES,
        "base_probabilities": [0.0, 0.0, 0.0, 0.0, 1.0],
    }
    if offsets is not None:
        severity["trajectory_ladder_offsets_by_day"] = offsets
    return _profile(recovery_day=5, severity_model=severity, **overrides)


def _course(hours: float, profile: dict[str, Any]) -> list[tuple[int, str]]:
    """Visible severity on each illness day of one host's whole course."""
    clock = SimClock(epoch_duration_hours=hours, mode=HOURS)
    agent = _agent(clock)
    rng = np.random.default_rng(7)
    seen: list[tuple[int, str]] = []
    for _ in range(int(clock.epochs_for_days(10))):
        advance_infections(agent, {PATHOGEN: profile}, rng)
        inf = agent.infections[PATHOGEN]
        if inf["illness"] != IllnessStatus.SYMPTOMATIC:
            continue
        onset = int(inf["onset_time_infected"])
        day = clock.day_index(max(0, (inf["time_infected"] or 0) - onset))
        entry = (day, str(inf["symptom_severity"]))
        if entry not in seen:
            seen.append(entry)
    return seen


class TestSeverityTrajectory:
    """Severity is a course, not a single draw held for the whole illness."""

    @pytest.mark.parametrize("hours", [1.0, 6.0, 24.0])
    def test_a_profile_with_no_trajectory_holds_the_state_it_drew(
        self, hours: float,
    ) -> None:
        seen = _course(hours, _severity_profile())
        assert seen, "the host never became symptomatic"
        assert {severity for _, severity in seen} == {"severe_critical"}

    @pytest.mark.parametrize("hours", [1.0, 6.0, 24.0])
    def test_the_declared_ladder_is_what_an_observer_sees_day_by_day(
        self, hours: float,
    ) -> None:
        """One entry per illness day, read off the peak, last entry held.

        Timestep-invariant: the path is read from the peak and the day, so
        cutting time more finely does not move it.
        """
        profile = _severity_profile([0, 0, -1, -2])
        by_day = dict(_course(hours, profile))
        assert by_day[0] == "severe_critical"
        assert by_day[1] == "severe_critical"
        assert by_day[2] == "moderate"
        assert by_day[3] == "mild"
        assert by_day[max(by_day)] == "mild"

    @pytest.mark.parametrize(
        "offsets,expected",
        [
            ([0], "severe_critical"),
            ([-1], "moderate"),
            ([-2], "mild"),
            ([-3], "subclinical"),
            ([-9], "subclinical"),
        ],
    )
    def test_a_deeper_ladder_reads_a_milder_state_and_floors_at_subclinical(
        self, offsets: list[int], expected: str,
    ) -> None:
        """Graded: distinct depths give distinct states until the floor.

        The floor is subclinical, never asymptomatic: that rung means the host
        never presented, which the presentation draw owns and a day of the
        course cannot undo.
        """
        seen = _course(6.0, _severity_profile(offsets))
        assert {severity for _, severity in seen} == {expected}

    @pytest.mark.parametrize("peak", _STATES[1:])
    @pytest.mark.parametrize("offsets", [[0], [-1, -2], [0, -1, -4]])
    def test_no_day_of_any_course_exceeds_the_peak_or_leaves_the_ladder(
        self, peak: str, offsets: list[int],
    ) -> None:
        profile = _severity_profile(offsets)
        peak_index = _STATES.index(peak)
        for day in range(12):
            state = severity_on_day(profile, peak, day)
            assert state in _STATES[1:]
            assert 1 <= _STATES.index(state) <= peak_index

    def test_an_asymptomatic_host_is_not_moved_onto_the_ladder(self) -> None:
        profile = _severity_profile([0, -1], symptomatic_fraction=0.0)
        clock = SimClock(epoch_duration_hours=6.0, mode=HOURS)
        agent = _agent(clock)
        rng = np.random.default_rng(5)
        for _ in range(int(clock.epochs_for_days(10))):
            advance_infections(agent, {PATHOGEN: profile}, rng)
            inf = agent.infections[PATHOGEN]
            assert inf.get("symptom_severity", "asymptomatic") == "asymptomatic"
            assert "symptom_severity_peak" not in inf

    def test_a_record_written_before_the_seam_existed_still_resolves(self) -> None:
        """No peak on the record means no trajectory to read: hold the state."""
        profile = _severity_profile([0, -2])
        assert severity_on_day(profile, "moderate", 1) == "subclinical"
        legacy = _profile(severity_model={"states": _STATES})
        assert severity_on_day(legacy, "moderate", 5) == "moderate"
