"""Sensitivity and invariants for the AERO-NEAR-02 two-box route."""
from __future__ import annotations

import numpy as np
import pytest

from engines.infection_dynamics_bridge import (
    DEFAULT_DINING_TABLE_SIZE,
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
)
from engines.transmission_core import (
    DEFAULT_NEAR_FIELD_INTERZONAL_AIRFLOW_M3_PER_HOUR,
    DEFAULT_NEAR_FIELD_MODE,
    DEFAULT_NEAR_FIELD_NEIGHBOUR_TABLE_RATIO,
    TransmissionCore,
)
from orchestrator_init import assign_dining_parties

CABIN = "Cabin_A"
DINING = "MainDining"
BUFFET = "Windjammer"


def _agent(
    aid: int,
    location: str,
    *,
    infected: bool = False,
    role: str = "passenger",
) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=aid,
        role=role,
        immune=False,
        home_zone=CABIN,
        dining_zone=DINING,
        work_zone=BUFFET if role == "crew" else "Lounge",
        free_zone="Lounge",
        schedule=["Meal:Dinner"] * 24,
    )
    agent.current_location = location
    if infected:
        agent.infection_status = InfectionStatus.INFECTED
        agent.illness_status = IllnessStatus.SYMPTOMATIC
        agent.time_infected = 1
    return agent


def _core(
    *,
    volume: float = 1000.0,
    mode: str = "two_box",
    beta: float = DEFAULT_NEAR_FIELD_INTERZONAL_AIRFLOW_M3_PER_HOUR,
    rho: float = DEFAULT_NEAR_FIELD_NEIGHBOUR_TABLE_RATIO,
    zone: str = DINING,
    zone_type: str = "Dining",
    seed: int = 7,
) -> TransmissionCore:
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={zone: volume},
        zone_types={zone: zone_type},
        cfg={
            "transmission": {
                "cabin_air_mode": "zone_pool",
                "near_field_air": {
                    "mode": mode,
                    "interzonal_airflow_m3_per_hour": beta,
                    "neighbour_table_ratio": rho,
                },
            },
        },
    )
    core.initialize_zones([zone])
    return core


def _exposures(
    core: TransmissionCore,
    agents: list[KorkinAgent],
    zone: str,
) -> list[dict]:
    matrix, _ = core.execute_transmission(
        epoch=1,
        agents=agents,
        zone_pathogen_mass={zone: 0.0},
    )
    return matrix.droplet_exposures


def _dose(rows: list[dict], aid: int) -> float:
    return next(row["dose"] for row in rows if row["target_id"] == aid)


def _near(rows: list[dict], aid: int) -> float:
    row = next(row for row in rows if row["target_id"] == aid)
    return row.get("near_field_dose", 0.0)


def _dining_agents() -> list[KorkinAgent]:
    agents = [_agent(1, DINING, infected=True)]
    agents.extend(_agent(aid, DINING) for aid in range(2, 7))
    assign_dining_parties(
        agents,
        [{
            "name": DINING,
            "type": "Dining",
            "dining_service_type": "mdr",
            "dining_table_size": 2,
        }],
    )
    return agents


def _cabin_agents() -> list[KorkinAgent]:
    shedder = _agent(1, CABIN, infected=True)
    mate = _agent(2, CABIN)
    stranger = _agent(3, CABIN)
    shedder.cabin_mate_ids = frozenset({2})
    mate.cabin_mate_ids = frozenset({1})
    return [shedder, mate, stranger]


class TestDeclaration:
    def test_defaults_are_two_box_and_sourced(self) -> None:
        core = TransmissionCore(rng=np.random.default_rng(1))
        near = core.near_field_air
        assert DEFAULT_NEAR_FIELD_MODE == "two_box"
        assert DEFAULT_NEAR_FIELD_INTERZONAL_AIRFLOW_M3_PER_HOUR == pytest.approx(204.0)
        assert DEFAULT_NEAR_FIELD_NEIGHBOUR_TABLE_RATIO == pytest.approx(0.43)
        assert near.active
        assert near.interzonal_airflow_m3_per_hour == pytest.approx(204.0)

    @pytest.mark.parametrize(
        ("key", "value"),
        [
            ("retained_fraction", 0.5),
            ("table_seat_volume_m3", 1.0),
            ("cabin_berth_volume_m3", 10.0),
        ],
    )
    def test_retired_keys_are_refused(self, key: str, value: float) -> None:
        with pytest.raises(ValueError, match="interzonal_airflow_m3_per_hour"):
            TransmissionCore(
                rng=np.random.default_rng(1),
                cfg={"transmission": {"near_field_air": {key: value}}},
            )

    @pytest.mark.parametrize(
        "block",
        [
            {"mode": "foo"},
            {"interzonal_airflow_m3_per_hour": 0.0},
            {"interzonal_airflow_m3_per_hour": float("nan")},
            {"interzonal_airflow_m3_per_hour": float("inf")},
            {"neighbour_table_ratio": -0.1},
            {"neighbour_table_ratio": 1.1},
        ],
    )
    def test_declaration_bounds_are_refused(self, block: dict) -> None:
        with pytest.raises(ValueError):
            TransmissionCore(
                rng=np.random.default_rng(1),
                cfg={"transmission": {"near_field_air": block}},
            )


class TestTwoBoxRoute:
    def test_beta_sensitivity_is_monotone(self) -> None:
        values = []
        for beta in (60.0, 204.0, 1140.0):
            rows = _exposures(
                _core(volume=5000.0, beta=beta),
                _dining_agents(),
                DINING,
            )
            values.append(_near(rows, 2))
        assert values[0] > values[1] > values[2] >= 0.0

    def test_ring_ordering_and_ratio(self) -> None:
        rows = _exposures(_core(volume=5000.0, rho=0.43), _dining_agents(), DINING)
        same = _near(rows, 2)
        adjacent = _near(rows, 3)
        remote = _near(rows, 5)
        assert same > adjacent > remote
        assert adjacent / same == pytest.approx(0.43, abs=1e-3)
        assert remote == pytest.approx(0.0)

    def test_far_field_and_pools_are_conserved(self) -> None:
        active_agents = _dining_agents()
        off_agents = _dining_agents()
        active = _core(volume=5000.0)
        off = _core(volume=5000.0, mode="off")
        active_rows = _exposures(active, active_agents, DINING)
        off_rows = _exposures(off, off_agents, DINING)
        assert active.aerosol_pools == off.aerosol_pools
        assert active.aerosol_pools_by_pathogen == off.aerosol_pools_by_pathogen
        for row in active_rows + off_rows:
            assert np.isfinite(row["dose"])
            assert row["dose"] >= 0.0
        for aid in (5, 6):
            assert _dose(active_rows, aid) == pytest.approx(_dose(off_rows, aid))
        assert all("near_field_dose" not in row for row in off_rows)

    def test_gain_vanishes_when_cabin_is_smaller_than_flushed_volume(self) -> None:
        rows = _exposures(
            _core(
                zone=CABIN,
                zone_type="Cabin_Corridor",
                volume=100.0,
                beta=204.0,
            ),
            _cabin_agents(),
            CABIN,
        )
        assert _near(rows, 2) == pytest.approx(0.0)


class TestMealTables:
    def _buffet_core(self, seed: int = 17) -> TransmissionCore:
        return _core(zone=BUFFET, volume=5000.0, seed=seed)

    def _diners(self) -> list[KorkinAgent]:
        agents = [_agent(aid, BUFFET) for aid in range(20)]
        for left, right in ((0, 1), (2, 3), (4, 5)):
            agents[left].cabin_mate_ids = frozenset({right})
            agents[right].cabin_mate_ids = frozenset({left})
        for aid in (18, 19):
            agents[aid] = _agent(aid, BUFFET, role="crew")
            agents[aid].work_zone = BUFFET
            agents[aid].schedule = ["Work"] * 24
        return agents

    def test_per_meal_deal_keeps_bookings_and_excludes_staff(self) -> None:
        core = self._buffet_core()
        agents = self._diners()
        core._deal_meal_tables(BUFFET, agents, 1)
        dealt = core._meal_tables[(BUFFET, 1)]
        assert set(dealt) == set(range(18))
        assert all(
            len(party) + 1 <= DEFAULT_DINING_TABLE_SIZE
            for _, party in dealt.values()
        )
        for left, right in ((0, 1), (2, 3), (4, 5)):
            assert dealt[left][0] == dealt[right][0]

    def test_free_buffet_occupants_are_dealt_but_work_is_not(self) -> None:
        core = self._buffet_core()
        free = _agent(20, BUFFET)
        free.schedule = ["Free"] * 24
        worker = _agent(21, BUFFET, role="crew")
        worker.work_zone = BUFFET
        worker.schedule = ["Work"] * 24
        core._deal_meal_tables(BUFFET, [free, worker], 1)
        assert set(core._meal_tables[(BUFFET, 1)]) == {free.agent_id}

    def test_same_seed_repeats_and_next_epoch_redeals(self) -> None:
        first = self._buffet_core(seed=31)
        second = self._buffet_core(seed=31)
        diners = self._diners()
        first._deal_meal_tables(BUFFET, diners, 1)
        second._deal_meal_tables(BUFFET, self._diners(), 1)
        assert first._meal_tables[(BUFFET, 1)] == second._meal_tables[(BUFFET, 1)]
        first._deal_meal_tables(BUFFET, diners, 2)
        assert first._meal_tables[(BUFFET, 1)] != first._meal_tables[(BUFFET, 2)]

    def test_buffet_contact_activity_is_dining_table(self) -> None:
        core = self._buffet_core()
        diners = self._diners()
        core._deal_meal_tables(BUFFET, diners, 1)
        assert core._contact_activity(
            diners[0], BUFFET, BUFFET, False, 1,
        ) == "dining_table"
