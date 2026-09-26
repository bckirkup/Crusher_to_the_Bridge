"""Edge-path tests for epoch-step helpers extracted for readability.

Covers the guard branches of ``step_mid_cruise_introductions``,
``step_shore_introductions``, and ``_log_observation_epoch`` that the
integration tests do not reach.
"""

from types import SimpleNamespace
from typing import Any

import numpy as np

from engines.infection_dynamics_bridge import KorkinAgent
from orchestrator_epoch import (
    _log_observation_epoch,
    step_mid_cruise_introductions,
    step_shore_introductions,
)
from orchestrator_types import ObservationResults

PATHOGEN = "norwalk_gi"


def _agent(agent_id: int = 0, *, immune: bool = False) -> KorkinAgent:
    return KorkinAgent(
        agent_id=agent_id,
        role="passenger",
        immune=immune,
        home_zone="cabin_a",
        dining_zone="galley",
        work_zone="deck",
        free_zone="lounge",
        schedule=[],
    )


def _shore_state(
    probability: float = 1.0,
    pathogen: str | None = PATHOGEN,
) -> SimpleNamespace:
    return SimpleNamespace(
        shore_exposure_enabled=True,
        shore_infection_probability=probability,
        shore_pathogen=pathogen,
        port="Aruba",
    )


class TestMidCruiseIntroductions:
    def test_no_eligible_candidates_seeds_nothing(self) -> None:
        agent = _agent(0)
        agent.infect_with_pathogen(PATHOGEN, 1e4, 0)
        engine = SimpleNamespace(agents=[agent])
        profiles = {
            PATHOGEN: {"introduction_epoch": 3, "initial_infected": 1},
        }

        step_mid_cruise_introductions(
            3, engine, profiles, np.random.default_rng(1),
        )

        assert agent.infections[PATHOGEN]["time_infected"] == 0

    def test_all_immune_candidates_seeds_nothing(self) -> None:
        engine = SimpleNamespace(agents=[_agent(0, immune=True)])
        profiles = {
            PATHOGEN: {"introduction_epoch": 3, "initial_infected": 1},
        }

        step_mid_cruise_introductions(
            3, engine, profiles, np.random.default_rng(1),
        )

        assert not engine.agents[0].is_infected_with(PATHOGEN)


class TestShoreIntroductions:
    def test_zero_probability_returns_empty(self) -> None:
        agent = _agent(0)
        agent.ashore = True
        engine = SimpleNamespace(agents=[agent])

        out = step_shore_introductions(
            1, engine, {PATHOGEN: {}}, np.random.default_rng(1),
            _shore_state(probability=0.0),
        )

        assert out == []

    def test_unknown_shore_pathogen_returns_empty(self) -> None:
        agent = _agent(0)
        agent.ashore = True
        engine = SimpleNamespace(agents=[agent])

        out = step_shore_introductions(
            1, engine, {PATHOGEN: {}}, np.random.default_rng(1),
            _shore_state(pathogen="mystery_flu"),
        )

        assert out == []

    def test_departed_agents_are_not_exposed(self) -> None:
        agent = _agent(0)
        agent.ashore = True
        agent.current_location = "Departed"
        engine = SimpleNamespace(agents=[agent])

        out = step_shore_introductions(
            1, engine, {PATHOGEN: {}}, np.random.default_rng(1),
            _shore_state(probability=1.0),
        )

        assert out == []
        assert not agent.is_infected_with(PATHOGEN)

    def test_failed_draw_leaves_agent_uninfected(self) -> None:
        agent = _agent(0)
        agent.ashore = True
        engine = SimpleNamespace(agents=[agent])

        out = step_shore_introductions(
            1, engine, {PATHOGEN: {}}, np.random.default_rng(1),
            _shore_state(probability=1e-12),
        )

        assert out == []
        assert not agent.is_infected_with(PATHOGEN)


class _RecordingNotebook:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def log_air_sniffer(self, *args: Any) -> None:
        self.calls.append("log_air_sniffer")

    def log_surface_swab(self, *args: Any) -> None:
        self.calls.append("log_surface_swab")

    def log_wastewater_seq(self, *args: Any) -> None:
        self.calls.append("log_wastewater_seq")

    def log_clinical_rdt(self, *args: Any) -> None:
        self.calls.append("log_clinical_rdt")

    def log_clinical_qpcr(self, *args: Any) -> None:
        self.calls.append("log_clinical_qpcr")

    def log_clinical_microbiology(self, *args: Any) -> None:
        self.calls.append("log_clinical_microbiology")

    def log_agent_summary(self, *args: Any) -> None:
        self.calls.append("log_agent_summary")

    def log_long_read_verification(self, *args: Any) -> None:
        self.calls.append("log_long_read_verification")


class TestLogObservationEpoch:
    def test_long_read_results_are_recorded(self) -> None:
        notebook = _RecordingNotebook()
        obs = SimpleNamespace(lab_notebook_enabled=True, notebook=notebook)
        results = ObservationResults(long_read={"agent_1": {"confirmed": True}})

        _log_observation_epoch(obs, 5, results, [])

        assert "log_long_read_verification" in notebook.calls

    def test_no_long_read_skips_verification_log(self) -> None:
        notebook = _RecordingNotebook()
        obs = SimpleNamespace(lab_notebook_enabled=True, notebook=notebook)

        _log_observation_epoch(obs, 5, ObservationResults(), [])

        assert "log_long_read_verification" not in notebook.calls
        assert "log_air_sniffer" in notebook.calls
