"""ROOM-AIR-PAIRED-VALIDATION-01 blocker B3: whole-hull encounter witness.

Synthetic fixtures only: no voyage is stepped here. The witness is shown to
be bookkeeping -- it cannot move a dose or a draw -- and to respond to the
occupancy it is meant to count. Only whole-hull scalars are exposed.
Empirical paired-voyage values are unmeasured.
"""
from __future__ import annotations

import math
from types import SimpleNamespace

import numpy as np
import pytest

from engines.infection_dynamics_bridge import (
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
)
from engines.sim_clock import SimClock
from engines.transmission_core import (
    TransmissionCore,
    build_zone_air_exchange_map,
    room_air_changed_zones,
)
from orchestrator_record import _summary_counts
from orchestrator_types import SimulationState

OPEN, CLOSED = "Open_Deck_Test", "Closed_Room_Test"
VOLUMES = {OPEN: 40.0, CLOSED: 40.0}


def _airflow(exchange_m3h: float = 80.0) -> dict:
    return {
        "hvac_zones": [{"ach": 2.0, "rooms": [OPEN, CLOSED]}],
        "ambient_openings": [
            {
                "zone": OPEN,
                "type": "open_deck",
                "area_m2": 10.0,
                "exchange_m3h": exchange_m3h,
                "azimuth_deg": 180.0,
                "wind_speed_m_s": 5.0,
            },
        ],
    }


def _agent(aid: int, zone: str, infected: bool = False) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=aid,
        role="passenger",
        immune=False,
        home_zone=zone,
        dining_zone="MainDining_L",
        work_zone="Main_Pool_Deck",
        free_zone="Main_Pool_Deck",
        schedule=["home"] * 24,
    )
    if infected:
        agent.infection_status = InfectionStatus.INFECTED
        agent.illness_status = IllnessStatus.SYMPTOMATIC
        agent.time_infected = 1
    agent.current_location = zone
    return agent


def _hull(n_open: int, n_closed: int = 2) -> list[KorkinAgent]:
    """One shedder per room plus the stated susceptibles."""
    agents = [_agent(1, OPEN, infected=True), _agent(2, CLOSED, infected=True)]
    agents += [_agent(10 + i, OPEN) for i in range(n_open)]
    agents += [_agent(100 + i, CLOSED) for i in range(n_closed)]
    return agents


def _run(
    n_open: int = 3,
    *,
    mode: str = "first_order",
    witness: bool = True,
    epochs: int = 1,
    hours: float = 1.0,
    exchange_m3h: float = 80.0,
) -> tuple[TransmissionCore, list]:
    core = TransmissionCore(
        rng=np.random.default_rng(42),
        zone_volumes=dict(VOLUMES),
        clock=SimClock(epoch_duration_hours=hours, mode="hours"),
        cfg={
            "transmission": {
                "cabin_air_mode": "zone_pool",
                "near_field_air": {"mode": "off"},
                "room_air_removal": mode,
            },
        },
    )
    airflow = _airflow(exchange_m3h)
    core.zone_air_exchange_per_hour = build_zone_air_exchange_map(
        airflow, zone_volumes=VOLUMES, ambient_exchange_m3h={},
    )
    if witness:
        core.room_air_changed_zones = room_air_changed_zones(
            airflow, zone_volumes=VOLUMES, ambient_exchange_m3h={},
        )
    core.initialize_zones([OPEN, CLOSED])
    agents = _hull(n_open)
    records = []
    for epoch in range(1, epochs + 1):
        matrix, events = core.execute_transmission(
            epoch=epoch, agents=agents,
            zone_pathogen_mass={OPEN: 0.0, CLOSED: 0.0},
        )
        records.append((matrix.droplet_exposures, len(events)))
    return core, records


def test_changed_zones_are_where_the_two_maps_differ() -> None:
    airflow = _airflow()
    on = build_zone_air_exchange_map(
        airflow, zone_volumes=VOLUMES, ambient_exchange_m3h={},
    )
    hvac_only = build_zone_air_exchange_map({"hvac_zones": airflow["hvac_zones"]})
    differing = {z for z in on if on[z] != hvac_only.get(z, 0.0)}
    assert room_air_changed_zones(airflow, VOLUMES, {}) == differing == {OPEN}


@pytest.mark.parametrize("exchange", [0.0, 1.0, 500.0])
def test_changed_zone_count_tracks_positive_exchange(exchange: float) -> None:
    core, _ = _run(exchange_m3h=exchange)
    assert core.room_air_witness()["changed_zone_count"] == (exchange > 0.0)


def test_witness_exposes_whole_hull_scalars_only() -> None:
    core, _ = _run()
    witness = core.room_air_witness()
    assert set(witness) == {
        "changed_zone_count", "susceptible_person_hours_changed_zones",
    }
    for value in witness.values():
        assert isinstance(value, (int, float)) and math.isfinite(value)
        assert value >= 0.0
    assert OPEN not in repr(witness) and CLOSED not in repr(witness)


def test_person_hours_count_susceptibles_in_changed_zones_only() -> None:
    hours = [
        _run(n)[0].room_air_witness()["susceptible_person_hours_changed_zones"]
        for n in (0, 1, 3, 6)
    ]
    # Shedders and the closed room's susceptibles never count.
    assert hours == [0.0, 1.0, 3.0, 6.0]


def test_person_hours_scale_with_epoch_length_and_accumulate() -> None:
    key = "susceptible_person_hours_changed_zones"
    one = _run(3)[0].room_air_witness()[key]
    half = _run(3, hours=0.5)[0].room_air_witness()[key]
    assert half == pytest.approx(one / 2.0)
    two = _run(3, epochs=2)[0].room_air_witness()[key]
    assert one < two <= 2.0 * one


def test_no_changed_zone_means_no_encounter() -> None:
    core, _ = _run(exchange_m3h=0.0)
    assert core.room_air_witness() == {
        "changed_zone_count": 0,
        "susceptible_person_hours_changed_zones": 0.0,
    }


@pytest.mark.parametrize("mode", ["first_order", "sealed"])
def test_witness_cannot_move_a_dose_or_a_draw(mode: str) -> None:
    """Same seed with and without the witness: identical records and RNG."""
    with_core, with_records = _run(mode=mode, epochs=3)
    without_core, without_records = _run(mode=mode, epochs=3, witness=False)
    assert with_records == without_records
    assert with_records[0][0]
    assert with_core.rng.random() == without_core.rng.random()
    assert without_core.room_air_witness()[
        "susceptible_person_hours_changed_zones"
    ] == 0.0


def test_witness_repeats_on_the_same_seed_and_ignores_sealed_mode() -> None:
    first = _run(epochs=2)[0].room_air_witness()
    assert first == _run(epochs=2)[0].room_air_witness()
    # Occupancy is read before any dose, so the first epoch's person-hours
    # do not depend on the removal mode.
    assert (
        _run(mode="sealed")[0].room_air_witness()
        == _run(mode="first_order")[0].room_air_witness()
    )


def test_run_summary_carries_the_witness_scalars() -> None:
    core, _ = _run()
    agents = [
        {
            "agent_id": 1,
            "agent_class": "passenger",
            "infection_state": "susceptible",
        },
    ]
    engine = SimpleNamespace(
        agents=[SimpleNamespace(microflora_disruption_status=0)],
    )
    summary = _summary_counts(
        agents, engine,
        SimulationState(room_air_witness=core.room_air_witness()),
        {"sick_call_count": 0},
    )
    assert summary["room_air_witness"] == {
        "changed_zone_count": 1,
        "susceptible_person_hours_changed_zones": 3.0,
    }
    assert _summary_counts(
        agents, engine, SimulationState(), {"sick_call_count": 0},
    )["room_air_witness"] == {}
