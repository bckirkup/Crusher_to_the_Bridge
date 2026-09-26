"""AERO-CABIN-01: the short-range air route on staterooms, not on the block.

The pre-change route diluted a shedder's aerosol into the whole cabin
corridor, so a confined passenger breathed the air of every other cabin on
the block. ``cabin_air_mode: cabin_compartment`` runs the inhalation route
on the stateroom each occupant shares, with the block's declared volume
partitioned among its berths, and leaves the mass the drift route reads
credited to the ship zone.
"""
from __future__ import annotations

import numpy as np
import pytest

from engines.infection_dynamics_bridge import (
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
)
from engines.transmission_core import TransmissionCore

ZONE = "PC_D6_P_F"
BLOCK_VOLUME = 1200.0
COMPARTMENT_MODE = {
    "transmission": {
        "cabin_air_mode": "cabin_compartment",
        "near_field_air": {"mode": "off"},
        # ROOM-AIR-01 baseline: the berth-share arithmetic pinned below is
        # the partition's; the residence factor would rescale it.
        "room_air_removal": "sealed",
    },
}


def _agent(aid: int, infected: bool = False, mates: set[int] = frozenset()) -> KorkinAgent:
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
    agent.cabin_mate_ids = frozenset(mates)
    return agent


def _cabins(pairs: int, *, infected_first: bool = True) -> list[KorkinAgent]:
    """``pairs`` double cabins on one block, occupant 1 the shedder."""
    agents: list[KorkinAgent] = []
    for cabin in range(pairs):
        left, right = 2 * cabin + 1, 2 * cabin + 2
        agents.append(_agent(left, infected=infected_first and cabin == 0,
                             mates={right}))
        agents.append(_agent(right, mates={left}))
    return agents


def _run(
    agents: list[KorkinAgent],
    *,
    cfg: dict | None = None,
    quarantined_ids: set[int] | None = None,
    zone_volumes: dict[str, float] | None = None,
) -> tuple[TransmissionCore, list[dict]]:
    cfg = cfg or {
        "transmission": {
            "cabin_air_mode": "zone_pool",
            "near_field_air": {"mode": "off"},
        },
    }
    core = TransmissionCore(
        rng=np.random.default_rng(42),
        zone_volumes=zone_volumes or {ZONE: BLOCK_VOLUME},
        zone_types={ZONE: "Cabin_Corridor"},
        cfg=cfg,
    )
    core.initialize_zones([ZONE])
    core.register_cabin_berths(agents)
    matrix, _ = core.execute_transmission(
        epoch=1,
        agents=agents,
        zone_pathogen_mass={ZONE: 0.0},
        quarantined_ids=quarantined_ids or set(),
    )
    return core, matrix.droplet_exposures


def _doses(exposures: list[dict]) -> dict[int, float]:
    return {int(e["target_id"]): float(e["dose"]) for e in exposures}


class TestBerthRegistry:
    def test_partition_conserves_the_block_volume(self) -> None:
        agents = _cabins(6, infected_first=False)
        core, _ = _run(agents, cfg=COMPARTMENT_MODE)
        total = sum(
            core._air_unit_volume(key)  # noqa: SLF001
            for key in core._cabin_berths  # noqa: SLF001
        )
        assert total == pytest.approx(BLOCK_VOLUME)

    def test_a_cabin_of_four_takes_twice_the_air_of_a_cabin_of_two(self) -> None:
        quad = [_agent(aid, mates={1, 2, 3, 4} - {aid}) for aid in (1, 2, 3, 4)]
        double = [_agent(5, mates={6}), _agent(6, mates={5})]
        core, _ = _run([*quad, *double], cfg=COMPARTMENT_MODE)
        volumes = sorted(
            core._air_unit_volume(k)  # noqa: SLF001
            for k in core._cabin_berths  # noqa: SLF001
        )
        assert volumes[-1] == pytest.approx(volumes[0] * 2.0)

    def test_registry_ignores_who_is_aboard_the_zone_this_epoch(self) -> None:
        """Berths are the berthing plan, not this epoch's occupancy."""
        agents = _cabins(4, infected_first=False)
        core, _ = _run(agents, cfg=COMPARTMENT_MODE)
        before = dict(core._cabin_berths)  # noqa: SLF001
        for agent in agents[2:]:
            agent.current_location = "MainDining_L"
        core.register_cabin_berths(agents)
        assert core._cabin_berths == before  # noqa: SLF001

    def test_unregistered_block_falls_back_to_the_block_volume(self) -> None:
        agents = _cabins(3)
        core = TransmissionCore(
            rng=np.random.default_rng(42),
            zone_volumes={ZONE: BLOCK_VOLUME},
            zone_types={ZONE: "Cabin_Corridor"},
            cfg=COMPARTMENT_MODE,
        )
        core.initialize_zones([ZONE])
        matrix, _ = core.execute_transmission(
            epoch=1, agents=agents, zone_pathogen_mass={ZONE: 0.0},
        )
        _, pooled = _run(agents)
        doses = _doses(matrix.droplet_exposures)
        # Routing still splits; only the dilution volume falls back.
        assert doses[2] == pytest.approx(_doses(pooled)[2])


class TestCompartmentRouting:
    def test_non_mates_stop_sharing_the_shedder_air(self) -> None:
        agents = _cabins(6)
        _, pooled = _run(agents)
        _, split = _run(agents, cfg=COMPARTMENT_MODE)
        pooled_doses, split_doses = _doses(pooled), _doses(split)
        assert pooled_doses[8] > 0.0
        assert 8 not in split_doses

    def test_the_cabin_mate_still_breathes_the_shedder_air(self) -> None:
        agents = _cabins(6)
        _, split = _run(agents, cfg=COMPARTMENT_MODE)
        assert _doses(split)[2] > 0.0

    def test_the_mate_dose_rises_as_the_block_is_partitioned(self) -> None:
        """Same emission, a stateroom's worth of air instead of a block's."""
        agents = _cabins(6)
        _, pooled = _run(agents)
        _, split = _run(agents, cfg=COMPARTMENT_MODE)
        assert _doses(split)[2] > _doses(pooled)[2]

    def test_mate_dose_is_the_berth_share_of_the_pooled_dose(self) -> None:
        pairs = 6
        agents = _cabins(pairs)
        _, pooled = _run(agents)
        _, split = _run(agents, cfg=COMPARTMENT_MODE)
        # Payload doses are rounded to 4 dp.
        assert _doses(split)[2] == pytest.approx(
            _doses(pooled)[2] * pairs, abs=1e-3,
        )

    def test_a_bigger_block_dilutes_the_stateroom_the_same_way(self) -> None:
        agents = _cabins(6)
        _, small = _run(agents, cfg=COMPARTMENT_MODE)
        _, large = _run(
            agents, cfg=COMPARTMENT_MODE,
            zone_volumes={ZONE: BLOCK_VOLUME * 2},
        )
        assert _doses(large)[2] == pytest.approx(
            _doses(small)[2] / 2.0, abs=1e-3,
        )

    def test_the_exposure_names_the_zone_and_the_stateroom(self) -> None:
        agents = _cabins(6)
        _, split = _run(agents, cfg=COMPARTMENT_MODE)
        exposure = split[0]
        assert exposure["zone"] == ZONE
        assert exposure["air_unit"].startswith(ZONE)
        assert exposure["air_unit"] != ZONE

    def test_zone_pool_payload_is_the_pre_change_payload(self) -> None:
        agents = _cabins(6)
        _, pooled = _run(agents)
        assert all("air_unit" not in exposure for exposure in pooled)


class TestBlockAirAndOtherZones:
    def test_the_block_keeps_the_emitted_mass_for_the_drift_route(self) -> None:
        agents = _cabins(6)
        pooled_core, _ = _run(agents)
        split_core, _ = _run(agents, cfg=COMPARTMENT_MODE)
        assert split_core.aerosol_pools[ZONE] == pytest.approx(
            pooled_core.aerosol_pools[ZONE],
        )
        assert ZONE in split_core.aerosol_pools_by_pathogen["_default"]

    def test_confinement_no_longer_carries_the_block(self) -> None:
        """The mode, not the isolation factor, is what closes the block."""
        agents = _cabins(6)
        _, pooled = _run(agents, quarantined_ids={1})
        _, split = _run(agents, cfg=COMPARTMENT_MODE, quarantined_ids={1})
        assert _doses(pooled)[8] > 0.0
        assert 8 not in _doses(split)

    def test_a_non_cabin_zone_is_untouched_by_the_mode(self) -> None:
        zone = "Main_Pool_Deck"
        shedder = _agent(1, infected=True)
        target = _agent(2)
        for agent in (shedder, target):
            agent.current_location = zone
        # AERO-SPLIT-01: the shipped partition draws a proximity partner set
        # per target on the shared stream, so two configs no longer read the
        # same dose bit-for-bit; the baseline pin isolates the cabin mode.
        doses = []
        for cfg in (
            {"transmission": {"droplet_field_split": {"mode": "off"}}},
            COMPARTMENT_MODE,
        ):
            core = TransmissionCore(
                rng=np.random.default_rng(42),
                zone_volumes={zone: 4000.0},
                zone_types={zone: "Recreation"},
                cfg=cfg,
            )
            core.initialize_zones([zone])
            core.register_cabin_berths([shedder, target])
            matrix, _ = core.execute_transmission(
                epoch=1, agents=[shedder, target],
                zone_pathogen_mass={zone: 0.0},
            )
            doses.append(matrix.droplet_exposures[0]["dose"])
        assert doses[0] == pytest.approx(doses[1])


class TestModeDeclaration:
    def test_explicit_pre_change_pool_is_supported(self) -> None:
        core = TransmissionCore(
            rng=np.random.default_rng(0),
            cfg={"transmission": {"cabin_air_mode": "zone_pool"}},
        )
        assert core.cabin_air_mode == "zone_pool"

    def test_an_undeclared_mode_is_refused(self) -> None:
        with pytest.raises(ValueError, match="cabin_air_mode"):
            TransmissionCore(
                rng=np.random.default_rng(0),
                cfg={"transmission": {"cabin_air_mode": "per_deck"}},
            )
