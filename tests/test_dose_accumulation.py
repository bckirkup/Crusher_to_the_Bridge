"""Behavioral tests for epoch-invariant dose-response accumulation."""

from __future__ import annotations

import math

import numpy as np
import pytest

from engines.infection_dynamics_bridge import (
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
    illness_probability,
)
from engines.natural_history import advance_infections
from engines.transmission_core import TransmissionCore

PATHOGEN = "dose_test_pathogen"
ZONE = "Dose_Test_Zone"
ALPHA = 0.111
BETA = 32.81


def _profile(model: str = "beta_poisson") -> dict:
    dose_response = (
        {"model": model, "k": 0.01}
        if model == "exponential"
        else {"model": model, "alpha": ALPHA, "beta": BETA}
    )
    return {
        "dose_response": dose_response,
        "shedding_curve_log10": [2.0] * 12,
        "asymptomatic_shedding_log10": [2.0] * 12,
    }


def _agent(agent_id: int) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=agent_id,
        role="passenger",
        immune=False,
        home_zone=ZONE,
        dining_zone=ZONE,
        work_zone=ZONE,
        free_zone=ZONE,
        schedule=["Free"] * 24,
    )
    agent.current_location = ZONE
    return agent


def _core(profile: dict, seed: int = 7) -> TransmissionCore:
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={ZONE: 100.0},
        zone_types={ZONE: "Free"},
        pathogen_profiles={PATHOGEN: profile},
    )
    core.initialize_zones([ZONE])
    return core


def _inject_fixed_dose(
    core: TransmissionCore,
    dose: float,
    route_doses: dict[str, float] | None = None,
) -> None:
    def inject(
        _epoch: int,
        agents: list[KorkinAgent],
        _zone_occupants: dict[str, list[KorkinAgent]],
        _zone_pathogen_mass: dict[str, float],
        _hvac_downstream_zones: dict[str, list[str]] | None,
        _multi_pathogen_mass: dict[str, dict[str, float]] | None,
        pathogen_id: str,
        _agent_doses: dict[int, float],
        _agent_pathway_doses: dict[int, dict[str, float]],
        agent_pathogen_doses: dict[int, dict[str, float]],
        _matrix: object,
        _events: list[object],
    ) -> None:
        for agent in agents:
            agent_pathogen_doses.setdefault(agent.agent_id, {})[pathogen_id] = dose
            if route_doses is not None:
                core._last_pathogen_route_doses[pathogen_id] = {
                    agent.agent_id: dict(route_doses),
                }

    core._execute_pathogen_pathways = inject


def _run_exposure(
    total_dose: float,
    epochs: int,
    *,
    population: int = 3000,
    profile: dict | None = None,
    seed: int = 7,
) -> list[KorkinAgent]:
    core = _core(profile or _profile(), seed=seed)
    agents = [_agent(agent_id) for agent_id in range(population)]
    _inject_fixed_dose(core, total_dose / epochs)
    for epoch in range(epochs):
        core.execute_transmission(
            epoch=epoch,
            agents=agents,
            zone_pathogen_mass={ZONE: 0.0},
        )
    return agents


def _outcome_rates(total_dose: float) -> tuple[float, float]:
    agents = _run_exposure(total_dose, 1, population=10000)
    infected = [
        agent for agent in agents
        if agent.infection_status == InfectionStatus.INFECTED
    ]
    illness_rng = np.random.default_rng(991)
    ill = sum(
        illness_rng.random()
        < illness_probability(agent.acquired_particles)
        for agent in infected
    )
    return len(infected) / len(agents), ill / max(len(infected), 1)


def test_fixed_window_refinement_is_epoch_invariant() -> None:
    rates = []
    for epochs in (24, 48):
        agents = _run_exposure(1000.0, epochs)
        infected = sum(
            agent.infection_status == InfectionStatus.INFECTED
            for agent in agents
        )
        rates.append(infected / len(agents))

    assert max(rates) - min(rates) < 0.04


@pytest.mark.parametrize("dose", [1.0, 100.0, 10_000.0])
def test_single_exposure_matches_beta_poisson_closed_form(dose: float) -> None:
    agents = _run_exposure(dose, 1, population=16000, seed=19)
    measured = sum(
        agent.infection_status == InfectionStatus.INFECTED for agent in agents
    ) / len(agents)
    expected = 1.0 - math.pow(1.0 + dose / BETA, -ALPHA)

    assert measured == pytest.approx(expected, abs=0.015)


def test_dose_response_susceptibility_is_persistent_and_host_specific() -> None:
    core = _core(_profile(), seed=23)
    first = _agent(1)
    second = _agent(2)

    assert PATHOGEN not in first.dose_response_susceptibility
    first_hazard = core._dose_response_hazard(first, PATHOGEN, 1.0)
    first_r = first.dose_response_susceptibility[PATHOGEN]
    second_hazard = core._dose_response_hazard(first, PATHOGEN, 2.0)
    other_hazard = core._dose_response_hazard(second, PATHOGEN, 1.0)

    assert first_hazard > 0.0
    assert second_hazard > first_hazard
    assert first.dose_response_susceptibility[PATHOGEN] == first_r
    assert other_hazard > 0.0
    assert second.dose_response_susceptibility[PATHOGEN] != first_r


class _SequenceRng:
    def __init__(self, values: list[float]) -> None:
        self.values = iter(values)

    def random(self) -> float:
        return next(self.values)


def test_cumulative_inoculum_is_passed_to_infection_and_resets() -> None:
    core = _core(_profile(), seed=1)
    core.rng = _SequenceRng([0.99, 0.0, 0.0])
    agent = _agent(1)
    agent.dose_response_susceptibility[PATHOGEN] = 1.0
    _inject_fixed_dose(
        core, 1.0, {"direct_contact": 0.4, "hvac_airborne": 0.6},
    )

    core.execute_transmission(0, [agent], {ZONE: 0.0})
    assert agent.cumulative_exposure[PATHOGEN] == pytest.approx(1.0)
    assert agent.cumulative_exposure_by_route[PATHOGEN] == pytest.approx({
        "direct_contact": 0.4,
        "hvac_airborne": 0.6,
    })
    core.execute_transmission(1, [agent], {ZONE: 0.0})

    assert agent.infections[PATHOGEN]["acquired_particles"] == pytest.approx(2.0)
    assert agent.infections[PATHOGEN]["acquired_particles_by_route"] == pytest.approx({
        "direct_contact": 0.8,
        "hvac_airborne": 1.2,
    })
    assert agent.cumulative_exposure[PATHOGEN] == pytest.approx(0.0)
    assert PATHOGEN not in agent.cumulative_exposure_by_route

    agent.infections[PATHOGEN]["status"] = InfectionStatus.RECOVERED
    agent.infection_status = InfectionStatus.RECOVERED
    agent.illness_status = IllnessStatus.RECOVERED
    core.execute_transmission(2, [agent], {ZONE: 0.0})

    assert agent.infections[PATHOGEN]["acquired_particles"] == pytest.approx(1.0)
    assert agent.cumulative_exposure[PATHOGEN] == pytest.approx(0.0)


def test_recovery_clears_exposure_but_preserves_susceptibility() -> None:
    agent = _agent(1)
    agent.infect_with_pathogen(PATHOGEN, 1.0, epoch=0)
    agent.infections[PATHOGEN]["incubation_days"] = 0.0
    agent.cumulative_exposure[PATHOGEN] = 0.25
    agent.cumulative_exposure_by_route[PATHOGEN] = {"fomite": 0.25}
    agent.dose_response_susceptibility[PATHOGEN] = 0.125

    advance_infections(
        agent,
        {PATHOGEN: {**_profile(), "recovery_day": 0}},
        np.random.default_rng(17),
    )

    assert agent.infections[PATHOGEN]["status"] == InfectionStatus.RECOVERED
    assert PATHOGEN not in agent.cumulative_exposure
    assert PATHOGEN not in agent.cumulative_exposure_by_route
    assert agent.dose_response_susceptibility[PATHOGEN] == pytest.approx(0.125)


def _run_route_establishment(
    route_doses: dict[str, float],
) -> tuple[KorkinAgent, object]:
    core = _core(_profile(), seed=31)
    core.rng = _SequenceRng([0.0])
    agent = _agent(1)
    agent.dose_response_susceptibility[PATHOGEN] = 1.0
    _inject_fixed_dose(core, sum(route_doses.values()), route_doses)
    _matrix, events = core.execute_transmission(0, [agent], {ZONE: 0.0})
    return agent, events[0]


def test_route_ledger_sums_to_pooled_dose_and_resets_on_establishment() -> None:
    agent, event = _run_route_establishment({
        "direct_contact": 2.0,
        "hvac_airborne": 3.0,
    })

    route_doses = event.acquired_particles_by_route
    assert sum(route_doses.values()) == pytest.approx(event.dose, abs=1e-9)
    assert event.dose == pytest.approx(5.0)
    assert agent.infections[PATHOGEN]["acquired_particles_by_route"] == pytest.approx(
        route_doses,
    )
    assert PATHOGEN not in agent.cumulative_exposure_by_route


def test_route_dose_cache_is_initialized_before_transmission() -> None:
    core = _core(_profile(), seed=37)

    assert core._effective_route_doses(1, PATHOGEN, 1.0) == {}


def test_route_ledger_is_invariant_to_route_insertion_order() -> None:
    first, first_event = _run_route_establishment({
        "direct_contact": 2.0,
        "hvac_airborne": 3.0,
    })
    second, second_event = _run_route_establishment({
        "hvac_airborne": 3.0,
        "direct_contact": 2.0,
    })

    assert first_event.dose == second_event.dose
    assert first_event.pathway == second_event.pathway
    assert first_event.acquired_particles_by_route == pytest.approx(
        second_event.acquired_particles_by_route,
    )
    assert first.infections[PATHOGEN]["acquired_particles_by_route"] == pytest.approx(
        second.infections[PATHOGEN]["acquired_particles_by_route"],
    )


def test_superinfection_keeps_pathogen_acquisition_and_records_strain_dose() -> None:
    core = _core(_profile(), seed=41)
    agent = _agent(1)
    initial_routes = {"direct_contact": 4.0, "hvac_airborne": 6.0}
    agent.infect_with_pathogen(
        PATHOGEN,
        10.0,
        epoch=0,
        strain_id="resident",
        acquired_particles_by_route=initial_routes,
    )

    established = core._establish(
        agent,
        PATHOGEN,
        "invader",
        3.0,
        4,
        resident=True,
        acquired_particles_by_route={
            "direct_contact": 1.0,
            "hvac_airborne": 2.0,
        },
    )

    assert established is True
    infection = agent.infections[PATHOGEN]
    assert infection["acquired_particles"] == pytest.approx(10.0)
    assert infection["acquired_particles_by_route"] == pytest.approx(initial_routes)
    invader = agent.resident_strains(PATHOGEN)["invader"]
    assert invader.acquired_particles == pytest.approx(3.0)
    assert sum(invader.acquired_particles_by_route.values()) == pytest.approx(3.0)
    assert invader.acquired_particles_by_route == pytest.approx({
        "direct_contact": 1.0,
        "hvac_airborne": 2.0,
    })


def test_exponential_model_keeps_its_closed_form_hazard() -> None:
    core = _core(_profile("exponential"), seed=29)
    agent = _agent(1)

    first = core._dose_response_hazard(agent, PATHOGEN, 0.3)
    second = core._dose_response_hazard(agent, PATHOGEN, 0.7)
    combined = 1.0 - (1.0 - first) * (1.0 - second)

    assert agent.dose_response_susceptibility[PATHOGEN] == pytest.approx(0.01)
    assert combined == pytest.approx(1.0 - math.exp(-0.01), rel=1e-12)


def test_more_total_dose_increases_infection_and_illness_rates() -> None:
    outcomes = [_outcome_rates(dose) for dose in (100.0, 1000.0, 10000.0)]
    infection_rates = [outcome[0] for outcome in outcomes]
    illness_rates = [outcome[1] for outcome in outcomes]

    assert infection_rates == sorted(infection_rates)
    assert illness_rates == sorted(illness_rates)
    assert infection_rates[-1] - infection_rates[0] > 0.15
    assert illness_rates[-1] - illness_rates[0] > 0.05
