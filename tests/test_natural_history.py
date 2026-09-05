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
)


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
