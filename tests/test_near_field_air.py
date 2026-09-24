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
    CONTACT_ACTIVITIES,
    DEFAULT_DROPLET_FIELD_SPLIT_MODE,
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
    split: str = "partition",
    far_share: float = 0.175,
    zone: str = DINING,
    zone_type: str = "Dining",
    seed: int = 7,
    extra_tx: dict | None = None,
) -> TransmissionCore:
    tx = {
        "cabin_air_mode": "zone_pool",
        "near_field_air": {
            "mode": mode,
            "interzonal_airflow_m3_per_hour": beta,
            "neighbour_table_ratio": rho,
        },
        "droplet_field_split": {
            "mode": split,
            "far_field_share": far_share,
        },
    }
    tx.update(extra_tx or {})
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={zone: volume},
        zone_types={zone: zone_type},
        cfg={"transmission": tx},
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
                # The excess-form sensitivity lives on the declared off
                # baseline; under the partition the near term is the plume
                # share, still 1/beta but on a different scale.
                _core(volume=5000.0, beta=beta, split="off"),
                _dining_agents(),
                DINING,
            )
            values.append(_near(rows, 2))
        assert values[0] > values[1] > values[2] >= 0.0

    def test_ring_ordering_and_ratio(self) -> None:
        rows = _exposures(
            # Same/adjacent/remote ring weights are the pre-partition rings;
            # the partition's proximity ring is a draw, so a remote table can
            # be sampled near. The declared rings stay pinned on the baseline.
            _core(volume=5000.0, rho=0.43, split="off"),
            _dining_agents(),
            DINING,
        )
        same = _near(rows, 2)
        adjacent = _near(rows, 3)
        remote = _near(rows, 5)
        assert same > adjacent > remote
        assert adjacent / same == pytest.approx(0.43, abs=1e-3)
        assert remote == pytest.approx(0.0)

    def test_far_field_and_pools_are_conserved(self) -> None:
        active_agents = _dining_agents()
        off_agents = _dining_agents()
        # Near-field on vs off on the off baseline: the partition is what
        # partitions the pool, so with it off the near field adds dose and
        # the pool is unchanged — the invariant this test was written for.
        active = _core(volume=5000.0, split="off")
        off = _core(volume=5000.0, mode="off", split="off")
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
            # The excess form's gain is 1/flushed - 1/volume and vanishes;
            # the partition's plume share does not depend on room volume.
            _core(
                zone=CABIN,
                zone_type="Cabin_Corridor",
                volume=100.0,
                beta=204.0,
                split="off",
            ),
            _cabin_agents(),
            CABIN,
        )
        assert _near(rows, 2) == pytest.approx(0.0)


class TestFieldSplit:
    """AERO-SPLIT-01: the emission partition and its partner bound."""

    @staticmethod
    def _partner_rates(per_hour: float) -> dict:
        rates = {
            activity: {"passenger": 0.0, "crew": 0.0}
            for activity in CONTACT_ACTIVITIES
        }
        rates["dining_table"] = {
            "passenger": per_hour,
            "crew": per_hour,
        }
        return rates

    def test_defaults_are_partition_and_sourced(self) -> None:
        core = TransmissionCore(rng=np.random.default_rng(1))
        split = core.droplet_field_split
        assert DEFAULT_DROPLET_FIELD_SPLIT_MODE == "partition"
        assert split.active
        assert split.far_field_share == pytest.approx(0.175)
        assert split.near_field_share == pytest.approx(1.0 - 0.175)

    @pytest.mark.parametrize(
        "block",
        [
            {"mode": "foo"},
            {"far_field_share": -0.1},
            {"far_field_share": 1.1},
            {"settled_share": float("nan")},
            {"far_field_share": 0.8, "settled_share": 0.4},
        ],
    )
    def test_declaration_bounds_are_refused(self, block: dict) -> None:
        with pytest.raises(ValueError):
            TransmissionCore(
                rng=np.random.default_rng(1),
                cfg={"transmission": {"droplet_field_split": block}},
            )

    def test_off_keeps_the_full_share_in_the_pool(self) -> None:
        # The off baseline's meaning is that the pool carries the whole
        # continuous share — identical to partition at far_field_share 1.
        off = _core(volume=5000.0, split="off")
        full = _core(volume=5000.0, split="partition", far_share=1.0)
        _exposures(off, _dining_agents(), DINING)
        _exposures(full, _dining_agents(), DINING)
        assert off.aerosol_pools == pytest.approx(full.aerosol_pools)

    def test_off_draws_no_proximity_ring(self) -> None:
        # Remote tables are unreachable under the declared rings; only the
        # partition's proximity draw could dose them near-field, so under
        # off they never carry any.
        for seed in range(5):
            rows = _exposures(
                _core(volume=5000.0, split="off", seed=seed),
                _dining_agents(),
                DINING,
            )
            for aid in (5, 6):
                assert _near(rows, aid) == pytest.approx(0.0)

    def test_partition_pool_carries_only_the_far_share(self) -> None:
        on = _core(volume=5000.0, split="partition", far_share=0.2)
        off = _core(volume=5000.0, split="off")
        _exposures(on, _dining_agents(), DINING)
        _exposures(off, _dining_agents(), DINING)
        assert on.aerosol_pools[DINING] == pytest.approx(
            0.2 * off.aerosol_pools[DINING],
        )

    def test_non_partner_far_dose_scales_with_the_share(self) -> None:
        off_rows = _exposures(
            _core(volume=5000.0, split="off"), _dining_agents(), DINING,
        )
        on_rows = _exposures(
            _core(volume=5000.0, split="partition", far_share=0.2),
            _dining_agents(),
            DINING,
        )
        checked = 0
        for row in on_rows:
            if row.get("near_field_dose"):
                continue
            off_dose = _dose(off_rows, row["target_id"])
            # doses are recorded rounded to 4 decimals
            assert row["dose"] == pytest.approx(0.2 * off_dose, abs=1e-4)
            checked += 1
        assert checked > 0

    def test_proximity_partners_take_the_plume_dose(self) -> None:
        # A saturated contact draw makes every co-occupant a near partner, so
        # every susceptible must see the near share at plume concentration.
        core = _core(
            volume=5000.0,
            split="partition",
            far_share=0.2,
            extra_tx={
                "contact_mode": "per_partner_contact",
                "activity_contacts": {
                    "enabled": True,
                    "rates_per_hour": self._partner_rates(30.0),
                },
            },
        )
        rows = _exposures(core, _dining_agents(), DINING)
        for row in rows:
            assert row.get("near_field_dose", 0.0) > 0.0

    def test_partition_needs_the_near_field(self) -> None:
        # Without near_field_air there is no near share destination: an off
        # near field keeps the whole pool, partition or not.
        near_off = _core(
            volume=5000.0, mode="off", split="partition", far_share=0.2,
        )
        both_off = _core(volume=5000.0, mode="off", split="off")
        _exposures(near_off, _dining_agents(), DINING)
        _exposures(both_off, _dining_agents(), DINING)
        assert near_off.aerosol_pools == both_off.aerosol_pools


class TestMealTables:
    def _buffet_core(self, seed: int = 17) -> TransmissionCore:
        return _core(zone=BUFFET, volume=5000.0, seed=seed)

    def _crew_core(self, seed: int = 17) -> TransmissionCore:
        return _core(zone="CrewMess", volume=5000.0, seed=seed)

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

    def _department_diners(self, venue: str) -> list[KorkinAgent]:
        agents = []
        for department in range(4):
            for offset in range(12):
                agent = _agent(
                    department * 12 + offset,
                    venue,
                    role="crew",
                )
                agent.work_zone = f"Department-{department}"
                agent.schedule = ["Meal:Dinner"] * 24
                agents.append(agent)
        return agents

    @staticmethod
    def _table_departments(
        core: TransmissionCore,
        venue: str,
        agents: list[KorkinAgent],
        epoch: int,
    ) -> list[set[str]]:
        core._deal_meal_tables(venue, agents, epoch)
        by_id = {agent.agent_id: agent for agent in agents}
        tables: dict[int, set[str]] = {}
        for agent_id, (table_index, party_ids) in core._meal_tables[(venue, epoch)].items():
            tables.setdefault(table_index, set()).add(
                by_id[agent_id].work_zone,
            )
            tables[table_index].update(
                by_id[party_id].work_zone for party_id in party_ids
            )
        return list(tables.values())

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

    def test_crew_mess_tables_are_dealt_within_department(self) -> None:
        core = self._crew_core()
        agents = self._department_diners("CrewMess")
        tables = self._table_departments(core, "CrewMess", agents, 1)
        assert sum(len(departments) > 1 for departments in tables) <= 3

    def test_buffet_tables_still_mix_departments(self) -> None:
        core = self._buffet_core()
        agents = self._department_diners(BUFFET)
        tables = self._table_departments(core, BUFFET, agents, 1)
        assert any(len(departments) > 1 for departments in tables)

    def test_department_dealing_repeats_table_mates_more_than_a_room_deal(self) -> None:
        crew = self._department_diners("CrewMess")
        buffet = self._department_diners(BUFFET)
        crew_core = self._crew_core(seed=23)
        buffet_core = self._buffet_core(seed=23)
        crew_mates: set[int] = set()
        buffet_mates: set[int] = set()
        for epoch in range(1, 21):
            crew_core._deal_meal_tables("CrewMess", crew, epoch)
            buffet_core._deal_meal_tables(BUFFET, buffet, epoch)
            crew_mates.update(
                crew_core._meal_tables[("CrewMess", epoch)][0][1]
            )
            buffet_mates.update(
                buffet_core._meal_tables[(BUFFET, epoch)][0][1]
            )
        assert len(crew_mates) < len(buffet_mates)

    def test_department_deal_keeps_cabin_groups_together(self) -> None:
        core = self._crew_core()
        agents = self._department_diners("CrewMess")
        agents[0].cabin_mate_ids = frozenset({1})
        agents[1].cabin_mate_ids = frozenset({0})
        core._deal_meal_tables("CrewMess", agents, 1)
        dealt = core._meal_tables[("CrewMess", 1)]
        assert dealt[agents[0].agent_id][0] == dealt[agents[1].agent_id][0]

    def test_department_deal_is_deterministic(self) -> None:
        first = self._crew_core(seed=31)
        second = self._crew_core(seed=31)
        first_agents = self._department_diners("CrewMess")
        second_agents = self._department_diners("CrewMess")
        first._deal_meal_tables("CrewMess", first_agents, 1)
        second._deal_meal_tables("CrewMess", second_agents, 1)
        assert first._meal_tables[("CrewMess", 1)] == second._meal_tables[("CrewMess", 1)]

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
