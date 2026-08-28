"""Tests for cabin-corridor confinement and ventilation in TransmissionCore."""
from __future__ import annotations

import numpy as np
import pytest

from engines.infection_dynamics_bridge import (
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
)
from engines.sim_clock import SimClock
from engines.transmission_core import TransmissionCore


def _agent(aid: int, loc: str, infected: bool = False) -> KorkinAgent:
    a = KorkinAgent(
        agent_id=aid,
        role="passenger",
        immune=False,
        home_zone=loc,
        dining_zone="MainDining_L",
        work_zone="Main_Pool_Deck",
        free_zone="Main_Pool_Deck",
        schedule=["home"] * 24,
    )
    if infected:
        a.infection_status = InfectionStatus.INFECTED
        a.illness_status = IllnessStatus.SYMPTOMATIC
        a.time_infected = 1
    a.current_location = loc
    return a


def _droplet_doses(
    volume: float,
    susceptible_count: int = 1,
    clock: SimClock | None = None,
) -> list[float]:
    zone = "Droplet_Test"
    shedder = _agent(1, zone, infected=True)
    targets = [_agent(aid, zone) for aid in range(2, 2 + susceptible_count)]
    core = TransmissionCore(
        rng=np.random.default_rng(42),
        zone_volumes={zone: volume},
        clock=clock,
    )
    core.initialize_zones([zone])
    matrix, _ = core.execute_transmission(
        epoch=1,
        agents=[shedder, *targets],
        zone_pathogen_mass={zone: 0.0},
    )
    return [exposure["dose"] for exposure in matrix.droplet_exposures]


class TestCabinCorridorTransmission:
    def test_droplet_dose_halves_when_zone_volume_doubles(self) -> None:
        dose_small = _droplet_doses(20.0)[0]
        dose_large = _droplet_doses(40.0)[0]

        assert dose_large == pytest.approx(dose_small / 2.0, abs=1e-4)

    def test_droplet_dose_does_not_depend_on_susceptible_count(self) -> None:
        one_target = _droplet_doses(20.0, susceptible_count=1)[0]
        two_targets = _droplet_doses(20.0, susceptible_count=2)

        assert two_targets[0] == pytest.approx(one_target)
        assert two_targets[1] == pytest.approx(one_target)

    def test_droplet_dose_scales_with_clock_epoch_duration(self) -> None:
        one_hour = _droplet_doses(
            20.0,
            clock=SimClock(epoch_duration_hours=1.0, mode="hours"),
        )[0]
        two_hours = _droplet_doses(
            20.0,
            clock=SimClock(epoch_duration_hours=2.0, mode="hours"),
        )[0]

        assert two_hours == pytest.approx(one_hour * 2.0)

    def test_quarantined_agent_receives_reduced_direct_contact(self) -> None:
        zone = "PC_D6_P_F"
        shedder = _agent(1, zone, infected=True)
        free_target = _agent(2, zone)
        confined_target = _agent(3, zone)
        # Non-cabin-mates: confined agent should get minimal hallway contact
        confined_target.cabin_mate_ids = frozenset({99})
        core = TransmissionCore(
            rng=np.random.default_rng(42),
            zone_volumes={zone: 1200.0},
            zone_types={zone: "Cabin_Corridor"},
            corridor_direct_contact_factor=0.15,
            cfg={"transmission": {"contact_mode": "density_dependent"}},
        )
        core.initialize_zones([zone])
        free_dose = 0.0
        confined_dose = 0.0
        for epoch in range(24):
            matrix_free, _ = core.execute_transmission(
                epoch=epoch,
                agents=[shedder, free_target],
                zone_pathogen_mass={zone: 0.0},
                quarantined_ids=set(),
            )
            matrix_confined, _ = core.execute_transmission(
                epoch=epoch,
                agents=[shedder, confined_target],
                zone_pathogen_mass={zone: 0.0},
                quarantined_ids={3},
            )
            free_dose += sum(
                exposure["dose"]
                for exposure in matrix_free.shared_room_exposures
            )
            confined_dose += sum(
                exposure["dose"]
                for exposure in matrix_confined.shared_room_exposures
            )
        assert confined_dose < free_dose * 0.2

    def test_quarantine_in_non_cabin_zone_unchanged(self) -> None:
        zone = "Berthing"
        shedder = _agent(1, zone, infected=True)
        confined = _agent(2, zone)
        core = TransmissionCore(
            rng=np.random.default_rng(5),
            zone_volumes={zone: 200.0},
            zone_types={zone: "Room"},
            confinement_isolation_factor=0.05,
            # Legacy AVG_R_POOL always draws ≥1; density Poisson can be 0 at n=2.
            cfg={"transmission": {"contact_mode": "legacy"}},
        )
        core.initialize_zones([zone])
        dose = 0.0
        for epoch in range(24):
            matrix, _ = core.execute_transmission(
                epoch=epoch,
                agents=[shedder, confined],
                zone_pathogen_mass={zone: 0.0},
                quarantined_ids={2},
            )
            dose += sum(
                exposure["dose"]
                for exposure in matrix.shared_room_exposures
            )
        assert dose > 0

    def test_quarantined_agent_skips_fomite_pickup(self) -> None:
        zone = "PC_D6_P_M"
        shedder = _agent(1, zone, infected=True)
        confined = _agent(2, zone)
        core = TransmissionCore(
            rng=np.random.default_rng(0),
            zone_volumes={zone: 1200.0},
            zone_types={zone: "Cabin_Corridor"},
        )
        core.initialize_zones([zone])
        core.surface_pools[zone] = 1000.0
        core._prev_zone_shedders[zone] = [1]  # noqa: SLF001
        core._prev_zone_occupants[zone] = {1}  # noqa: SLF001
        matrix, _ = core.execute_transmission(
            epoch=1,
            agents=[shedder, confined],
            zone_pathogen_mass={zone: 0.0},
            quarantined_ids={2},
        )
        assert matrix.fomite_trailing_exposures == []

    def test_balcony_ventilation_reduces_droplet_dose(self) -> None:
        zone = "PC_D7_S_A"
        shedder = _agent(1, zone, infected=True)
        target = _agent(2, zone)
        core_interior = TransmissionCore(
            rng=np.random.default_rng(7),
            zone_volumes={zone: 1200.0},
            zone_types={zone: "Cabin_Corridor"},
            zone_ventilation={zone: "interior_hvac"},
        )
        core_balcony = TransmissionCore(
            rng=np.random.default_rng(7),
            zone_volumes={zone: 1200.0},
            zone_types={zone: "Cabin_Corridor"},
            zone_ventilation={zone: "balcony_partial"},
        )
        for c in (core_interior, core_balcony):
            c.initialize_zones([zone])
        m_int, _ = core_interior.execute_transmission(
            epoch=1, agents=[shedder, target], zone_pathogen_mass={zone: 0.0},
        )
        m_bal, _ = core_balcony.execute_transmission(
            epoch=1, agents=[shedder, target], zone_pathogen_mass={zone: 0.0},
        )
        assert m_bal.droplet_exposures[0]["dose"] < m_int.droplet_exposures[0]["dose"]

    def test_quarantined_agent_hvac_dose_not_reduced_by_confinement(self) -> None:
        source = "PC_D6_P_F"
        target_zone = "PC_D6_P_M"
        volumes = {source: 1200.0, target_zone: 1200.0}
        types = {source: "Cabin_Corridor", target_zone: "Cabin_Corridor"}
        downstream = {source: [target_zone]}
        mass = {target_zone: 5000.0}
        core_free = TransmissionCore(
            rng=np.random.default_rng(11),
            zone_volumes=volumes,
            zone_types=types,
            confinement_isolation_factor=0.05,
        )
        core_confined = TransmissionCore(
            rng=np.random.default_rng(11),
            zone_volumes=volumes,
            zone_types=types,
            confinement_isolation_factor=0.05,
        )
        for c in (core_free, core_confined):
            c.initialize_zones(list(volumes))
        m_free, _ = core_free.execute_transmission(
            epoch=1,
            agents=[_agent(1, source, infected=True), _agent(2, target_zone)],
            zone_pathogen_mass=mass,
            hvac_downstream_zones=downstream,
            quarantined_ids=set(),
        )
        m_conf, _ = core_confined.execute_transmission(
            epoch=1,
            agents=[_agent(1, source, infected=True), _agent(2, target_zone)],
            zone_pathogen_mass=mass,
            hvac_downstream_zones=downstream,
            quarantined_ids={2},
        )
        assert m_free.hvac_downstream_exposures[0]["dose"] == m_conf.hvac_downstream_exposures[0]["dose"]
