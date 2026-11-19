"""ROOM-AIR-PAIRED-VALIDATION-01 blocker B1: the room-air map arm key.

Synthetic fixtures only: no voyage is stepped here. These tests show the
software invariants of ``transmission.room_air_removal.map_arm`` -- the
default is the shipped map, ``ambient_off`` is the AHU-only baseline, and
under ``mode: sealed`` the arm cannot reach a dose. They are not the
design's K0/K1 paired-voyage controls, which stay unmeasured.
"""
from __future__ import annotations

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
    DEFAULT_ROOM_AIR_MAP_ARM,
    ROOM_AIR_MAP_ARMS,
    TransmissionCore,
    build_zone_air_exchange_map,
    parse_room_air_map_arm,
)
from orchestrator_record import _summary_counts
from orchestrator_types import SimulationState
from picard_framework.covid_theta_fit import (
    _declare_room_air_map_arm,
    build_fit_run_spec,
)

ZONE = "Droplet_Test"
VOLUMES = {"Cabin": 50.0, "Pool": 100.0, ZONE: 20.0}


def _airflow(exchange_m3h: float = 100.0) -> dict:
    return {
        "hvac_duty": 0.5,
        "hvac_zones": [
            {"ach": 4.0, "rooms": ["Cabin"]},
            {"ach": 6.0, "rooms": [ZONE]},
        ],
        "ambient_openings": [
            {
                "zone": zone,
                "type": "open_deck",
                "area_m2": 10.0,
                "exchange_m3h": exchange_m3h,
                "azimuth_deg": 180.0,
                "wind_speed_m_s": 5.0,
            }
            for zone in ("Pool", ZONE)
        ],
    }


def _map(arm: str | None = None, exchange_m3h: float = 100.0) -> dict:
    kwargs = {} if arm is None else {"map_arm": arm}
    return build_zone_air_exchange_map(
        _airflow(exchange_m3h),
        zone_volumes=VOLUMES,
        ambient_exchange_m3h={},
        **kwargs,
    )


def _agent(aid: int, infected: bool = False) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=aid,
        role="passenger",
        immune=False,
        home_zone=ZONE,
        dining_zone="MainDining_L",
        work_zone="Main_Pool_Deck",
        free_zone="Main_Pool_Deck",
        schedule=["home"] * 24,
    )
    if infected:
        agent.infection_status = InfectionStatus.INFECTED
        agent.illness_status = IllnessStatus.SYMPTOMATIC
        agent.time_infected = 1
    agent.current_location = ZONE
    return agent


def _exposures(arm: str | None, mode: str) -> list:
    """One synthetic two-agent transmission call on the arm's map."""
    removal: dict = {"mode": mode}
    if arm is not None:
        removal["map_arm"] = arm
    core = TransmissionCore(
        rng=np.random.default_rng(42),
        zone_volumes={ZONE: VOLUMES[ZONE]},
        clock=SimClock(epoch_duration_hours=1.0, mode="hours"),
        cfg={
            "transmission": {
                "cabin_air_mode": "zone_pool",
                "near_field_air": {"mode": "off"},
                "room_air_removal": removal,
            },
        },
    )
    core.zone_air_exchange_per_hour = _map(core.room_air_removal.map_arm)
    core.initialize_zones([ZONE])
    matrix, _ = core.execute_transmission(
        epoch=1,
        agents=[_agent(1, infected=True), _agent(2)],
        zone_pathogen_mass={ZONE: 0.0},
    )
    return matrix.droplet_exposures


def test_default_arm_is_the_shipped_map() -> None:
    assert DEFAULT_ROOM_AIR_MAP_ARM == "ambient_on"
    assert parse_room_air_map_arm(None) == "ambient_on"
    assert parse_room_air_map_arm({"room_air_removal": "sealed"}) == "ambient_on"
    assert _map() == _map("ambient_on")


def test_ambient_off_only_removes_opening_exchange() -> None:
    on, off = _map("ambient_on"), _map("ambient_off")
    assert off == {"Cabin": 2.0, ZONE: 3.0}
    assert set(off) <= set(on)
    assert all(on[zone] >= off[zone] for zone in off)
    assert on["Cabin"] == off["Cabin"]
    assert on[ZONE] - off[ZONE] == pytest.approx(100.0 / VOLUMES[ZONE])


def test_arm_difference_grows_with_opening_exchange() -> None:
    off = [_map("ambient_off", q) for q in (0.0, 50.0, 200.0)]
    on = [_map("ambient_on", q) for q in (0.0, 50.0, 200.0)]
    assert off[0] == off[1] == off[2]
    assert on[0] == off[0]
    gaps = [on_map[ZONE] - off[0][ZONE] for on_map in on]
    assert gaps == sorted(gaps) and gaps[0] == 0.0 and gaps[2] > gaps[1] > 0.0


def test_both_arms_reject_the_same_platform() -> None:
    for arm in ROOM_AIR_MAP_ARMS:
        with pytest.raises(ValueError):
            build_zone_air_exchange_map(
                _airflow(), zone_volumes={}, ambient_exchange_m3h={},
                map_arm=arm,
            )


def test_unknown_arm_is_rejected() -> None:
    with pytest.raises(ValueError, match="map_arm"):
        build_zone_air_exchange_map(_airflow(), map_arm="ambient_half")
    with pytest.raises(ValueError, match="map_arm"):
        parse_room_air_map_arm({"room_air_removal": {"map_arm": "off"}})
    with pytest.raises(ValueError, match="room_air_map_arm"):
        build_fit_run_spec(
            "diamond_princess_2020", 1e8, 7, num_epochs=1,
            room_air_map_arm="off",
        )


def test_default_arm_reproduces_itself_on_the_same_seed() -> None:
    """Undeclared, declared-default and a repeat give identical records."""
    undeclared = _exposures(None, "first_order")
    assert undeclared
    assert undeclared == _exposures(None, "first_order")
    assert undeclared == _exposures("ambient_on", "first_order")


def test_arm_reaches_the_dose_only_through_first_order_removal() -> None:
    on = _exposures("ambient_on", "first_order")[0]["dose"]
    off = _exposures("ambient_off", "first_order")[0]["dose"]
    assert 0.0 < on < off


def test_sealed_mode_makes_the_arm_toggle_inert() -> None:
    sealed_on = _exposures("ambient_on", "sealed")
    sealed_off = _exposures("ambient_off", "sealed")
    assert sealed_on and sealed_on == sealed_off
    assert sealed_on[0]["dose"] > _exposures("ambient_off", "first_order")[0]["dose"]


def test_fit_spec_declares_the_arm_only_when_asked() -> None:
    base = build_fit_run_spec("diamond_princess_2020", 1e8, 7, num_epochs=1)
    assert "transmission" not in base["config_overrides"]
    for arm in ROOM_AIR_MAP_ARMS:
        raw = build_fit_run_spec(
            "diamond_princess_2020", 1e8, 7, num_epochs=1,
            room_air_map_arm=arm,
        )
        # The arm key is the only thing the two specs differ by.
        assert raw["config_overrides"].pop("transmission") == {
            "room_air_removal": {"map_arm": arm},
        }
        assert raw == base


def test_declaring_the_arm_keeps_a_declared_sealed_mode() -> None:
    for declared in ("sealed", {"mode": "sealed"}):
        overrides = {"transmission": {"room_air_removal": declared}}
        _declare_room_air_map_arm(overrides, "ambient_off")
        assert overrides["transmission"]["room_air_removal"] == {
            "mode": "sealed", "map_arm": "ambient_off",
        }


@pytest.mark.parametrize("arm", ROOM_AIR_MAP_ARMS)
def test_run_summary_records_the_arm(arm: str) -> None:
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
        agents, engine, SimulationState(room_air_map_arm=arm),
        {"sick_call_count": 0},
    )
    assert summary["room_air_map_arm"] == arm


def test_run_summary_defaults_to_the_shipped_arm() -> None:
    assert SimulationState().room_air_map_arm == DEFAULT_ROOM_AIR_MAP_ARM
