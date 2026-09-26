"""Tests for cabin-corridor confinement and ventilation in TransmissionCore."""
from __future__ import annotations

import numpy as np
import pytest

from engines import transmission_core as tc_mod
from engines.infection_dynamics_bridge import (
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
)
from engines.sim_clock import SimClock
from engines.stateroom_air import partition_block_air
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
        cfg={
            "transmission": {
                "cabin_air_mode": "zone_pool",
                "near_field_air": {"mode": "off"},
            },
        },
    )
    core.initialize_zones([zone])
    matrix, _ = core.execute_transmission(
        epoch=1,
        agents=[shedder, *targets],
        zone_pathogen_mass={zone: 0.0},
    )
    return [exposure["dose"] for exposure in matrix.droplet_exposures]


class TestCabinCorridorTransmission:
    def test_partition_conserves_transport_mass(self) -> None:
        pre = {
            "B::cabin::1": 17.0,
            "B::cabin::2": 29.0,
            "B::cabin::3": 43.0,
            "B": 0.0,
        }
        post = {"B": 88.0, "Public": 12.0}
        shares = {
            "B": {
                "B::cabin::1": 0.25,
                "B::cabin::2": 0.25,
                "B::cabin::3": 0.5,
            },
        }
        result = partition_block_air(pre, post, shares, {"B": 0.2}, 1.0)
        assert sum(result.values()) == pytest.approx(sum(post.values()), rel=1e-12)

    def test_stateroom_retention_and_share(self) -> None:
        pre = {
            "B::cabin::1": 100.0,
            "B::cabin::2": 0.0,
            "B::cabin::3": 0.0,
        }
        shares = {
            "B": {
                "B::cabin::1": 0.25,
                "B::cabin::2": 0.25,
                "B::cabin::3": 0.5,
            },
        }
        k = 0.2
        result = partition_block_air(
            pre, {"B": 100.0}, shares, {"B": k}, 1.0,
        )
        retained = np.exp(-k)
        assert result["B::cabin::1"] >= 100.0 * retained
        assert result["B::cabin::2"] / result["B::cabin::3"] == pytest.approx(0.5)

    @pytest.mark.parametrize("cabin_air_mode, expected_compartment", [
        ("cabin_compartment", True),
        ("zone_pool", False),
    ])
    def test_airborne_deposit_key(
        self,
        cabin_air_mode: str,
        expected_compartment: bool,
    ) -> None:
        block = "PC_D6_P_M"
        public = "MainDining_L"
        agent = _agent(1, block)
        core = TransmissionCore(
            rng=np.random.default_rng(12),
            zone_volumes={block: 1200.0, public: 100.0},
            zone_types={block: "Cabin_Corridor", public: "Dining"},
            cfg={"transmission": {"cabin_air_mode": cabin_air_mode}},
        )
        key = core.airborne_deposit_key(agent, block)
        assert (key != block) == expected_compartment
        assert core.airborne_deposit_key(agent, public) == public

    def test_cabin_compartment_hvac_targets_other_stateroom(self) -> None:
        block = "PC_D6_P_M"
        shedder = _agent(1, block, infected=True)
        target = _agent(2, block)
        shedder.cabin_mate_ids = frozenset()
        target.cabin_mate_ids = frozenset()
        core = TransmissionCore(
            rng=np.random.default_rng(13),
            zone_volumes={block: 1200.0},
            zone_types={block: "Cabin_Corridor"},
            cfg={"transmission": {"cabin_air_mode": "cabin_compartment"}},
        )
        core.initialize_zones([block])
        core.register_cabin_berths([shedder, target])
        shedder.cabin_mate_ids = frozenset()
        target.cabin_mate_ids = frozenset()
        shedder.current_location = block
        target.current_location = block
        shed_key = core._cabin_compartment_key(block, shedder)
        target_key = core._cabin_compartment_key(block, target)
        matrix, _ = core.execute_transmission(
            epoch=1,
            agents=[shedder, target],
            zone_pathogen_mass={shed_key: 0.0, target_key: 5000.0},
            hvac_downstream_zones={block: [block]},
        )
        assert len(matrix.hvac_downstream_exposures) == 1
        exposure = matrix.hvac_downstream_exposures[0]
        assert exposure["target_id"] == target.agent_id
        assert exposure["air_unit"] == target_key

    def test_cabin_compartment_hvac_is_graded_in_stateroom_mass(self) -> None:
        block = "PC_D6_P_M"
        shedder = _agent(1, block, infected=True)
        target = _agent(2, block)
        core = TransmissionCore(
            rng=np.random.default_rng(14),
            zone_volumes={block: 1200.0},
            zone_types={block: "Cabin_Corridor"},
            cfg={"transmission": {"cabin_air_mode": "cabin_compartment"}},
        )
        core.initialize_zones([block])
        core.register_cabin_berths([shedder, target])
        shed_key = core._cabin_compartment_key(block, shedder)
        target_key = core._cabin_compartment_key(block, target)
        doses: list[float] = []
        for mass in (0.0, 1000.0, 5000.0, 20000.0):
            matrix, _ = core.execute_transmission(
                epoch=1,
                agents=[shedder, target],
                zone_pathogen_mass={shed_key: 0.0, target_key: mass},
                hvac_downstream_zones={block: [block]},
            )
            exposures = matrix.hvac_downstream_exposures
            assert len(exposures) == (1 if mass > 0.0 else 0)
            if exposures:
                dose = exposures[0]["dose"]
                assert np.isfinite(dose)
                assert dose >= 0.0
                doses.append(dose)
        assert doses[0] < doses[1] < doses[2]

    def test_cabin_compartment_hvac_excludes_shedder_stateroom(self) -> None:
        block = "PC_D6_P_M"
        shedder = _agent(1, block, infected=True)
        target = _agent(2, block)
        core = TransmissionCore(
            rng=np.random.default_rng(15),
            zone_volumes={block: 1200.0},
            zone_types={block: "Cabin_Corridor"},
            cfg={"transmission": {"cabin_air_mode": "cabin_compartment"}},
        )
        core.initialize_zones([block])
        core.register_cabin_berths([shedder, target])
        shed_key = core._cabin_compartment_key(block, shedder)
        target_key = core._cabin_compartment_key(block, target)
        matrix, _ = core.execute_transmission(
            epoch=1,
            agents=[shedder, target],
            zone_pathogen_mass={shed_key: 5000.0, target_key: 5000.0},
            hvac_downstream_zones={block: [block]},
        )
        assert [
            exposure["air_unit"]
            for exposure in matrix.hvac_downstream_exposures
        ] == [target_key]

    @staticmethod
    def _droplet_case(
        *,
        quarantined_ids: set[int],
        cabin_mates: bool = False,
    ) -> tuple[float, float]:
        zone = "PC_D6_P_F"
        shedder = _agent(1, zone, infected=True)
        target = _agent(2, zone)
        if cabin_mates:
            shedder.cabin_mate_ids = frozenset({2})
            target.cabin_mate_ids = frozenset({1})
        core = TransmissionCore(
            rng=np.random.default_rng(42),
            zone_volumes={zone: 1200.0},
            zone_types={zone: "Cabin_Corridor"},
            cfg={
                "transmission": {
                    "cabin_air_mode": "zone_pool",
                    "near_field_air": {"mode": "off"},
                    # Pre-CABIN-OCC-01/ROOM-AIR-01 baseline: these cases pin
                    # the confinement factors, not the partition or the
                    # ventilation residence factor.
                    "cabin_cooccupancy": "off",
                    "room_air_removal": "sealed",
                },
            },
        )
        core.initialize_zones([zone])
        matrix, _ = core.execute_transmission(
            epoch=1,
            agents=[shedder, target],
            zone_pathogen_mass={zone: 0.0},
            quarantined_ids=quarantined_ids,
        )
        exposure = matrix.droplet_exposures[0]
        return exposure["dose"], core.aerosol_pools[zone]

    def test_confined_shedder_attenuates_shared_droplet_emission(self) -> None:
        baseline, _ = self._droplet_case(quarantined_ids=set())
        confined, _ = self._droplet_case(quarantined_ids={1})
        assert confined == pytest.approx(baseline * 0.05, abs=5e-5)

    def test_confined_shedder_preserves_cabin_mate_droplet_dose(self) -> None:
        baseline, _ = self._droplet_case(quarantined_ids=set(), cabin_mates=True)
        confined, _ = self._droplet_case(
            quarantined_ids={1},
            cabin_mates=True,
        )
        assert confined == pytest.approx(baseline)

    def test_confined_target_receipt_attenuation_is_preserved(self) -> None:
        baseline, _ = self._droplet_case(quarantined_ids=set())
        confined, _ = self._droplet_case(quarantined_ids={2})
        assert confined == pytest.approx(baseline * 0.05, abs=5e-5)

    def test_unconfined_shedder_and_confined_cabin_mate_share_full_dose(self) -> None:
        """Cabin mates share the cabin, so confinement does not separate them."""
        baseline, _ = self._droplet_case(
            quarantined_ids=set(),
            cabin_mates=True,
        )
        confined, _ = self._droplet_case(
            quarantined_ids={2},
            cabin_mates=True,
        )
        assert confined == pytest.approx(baseline)

    def test_confined_shedder_and_confined_cabin_mate_are_not_double_attenuated(
        self,
    ) -> None:
        baseline, _ = self._droplet_case(quarantined_ids=set(), cabin_mates=True)
        confined, _ = self._droplet_case(
            quarantined_ids={1, 2},
            cabin_mates=True,
        )
        assert confined == pytest.approx(baseline)

    def test_confined_shedder_and_non_mate_target_apply_both_factors(self) -> None:
        baseline, _ = self._droplet_case(quarantined_ids=set())
        confined, _ = self._droplet_case(quarantined_ids={1, 2})
        assert confined == pytest.approx(baseline * 0.05 * 0.05, abs=5e-5)

    def test_aerosol_pool_records_attenuated_shared_emission(self) -> None:
        _, baseline_pool = self._droplet_case(quarantined_ids=set())
        _, confined_pool = self._droplet_case(quarantined_ids={1})
        assert confined_pool == pytest.approx(baseline_pool * 0.05)

    def test_shared_droplet_dose_is_monotonic_in_isolation_factor(self) -> None:
        doses = []
        for factor in (0.0, 0.05, 0.5, 1.0):
            zone = "PC_D6_P_F"
            shedder = _agent(1, zone, infected=True)
            target = _agent(2, zone)
            core = TransmissionCore(
                rng=np.random.default_rng(42),
                zone_volumes={zone: 1200.0},
                zone_types={zone: "Cabin_Corridor"},
                confinement_isolation_factor=factor,
                cfg={"transmission": {"cabin_air_mode": "zone_pool"}},
            )
            core.initialize_zones([zone])
            matrix, _ = core.execute_transmission(
                epoch=1,
                agents=[shedder, target],
                zone_pathogen_mass={zone: 0.0},
                quarantined_ids={1},
            )
            doses.append(matrix.droplet_exposures[0]["dose"])
        assert doses == sorted(doses)

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
            cfg={"transmission": {
                "contact_mode": "density_dependent",
                "cabin_air_mode": "zone_pool",
            }},
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
            cfg={"transmission": {
                "contact_mode": "legacy",
                "cabin_air_mode": "zone_pool",
            }},
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
            cfg={"transmission": {"cabin_air_mode": "zone_pool"}},
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
            cfg={"transmission": {"cabin_air_mode": "zone_pool"}},
        )
        core_balcony = TransmissionCore(
            rng=np.random.default_rng(7),
            zone_volumes={zone: 1200.0},
            zone_types={zone: "Cabin_Corridor"},
            zone_ventilation={zone: "balcony_partial"},
            cfg={"transmission": {"cabin_air_mode": "zone_pool"}},
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

    @pytest.mark.parametrize(
        "cabin_air_mode",
        ("zone_pool", "cabin_compartment"),
    )
    def test_quarantined_agent_hvac_dose_is_reduced_by_confinement(
        self,
        cabin_air_mode: str,
    ) -> None:
        source = "PC_D6_P_F"
        target_zone = "PC_D6_P_M"
        volumes = {source: 1200.0, target_zone: 1200.0}
        types = {source: "Cabin_Corridor", target_zone: "Cabin_Corridor"}
        downstream = {source: [target_zone]}
        mass = {target_zone: 5000.0}
        core = TransmissionCore(
            rng=np.random.default_rng(11),
            zone_volumes=volumes,
            zone_types=types,
            confinement_isolation_factor=0.05,
            # Baseline modes: this case pins the confinement factor itself;
            # the co-occupancy presence share would attenuate it further.
            cfg={
                "transmission": {
                    "cabin_air_mode": cabin_air_mode,
                    "cabin_cooccupancy": "off",
                    "room_air_removal": "sealed",
                },
            },
        )
        core.initialize_zones(list(volumes))
        matrix, _ = core.execute_transmission(
            epoch=1,
            agents=[
                _agent(1, source, infected=True),
                _agent(2, target_zone),
                _agent(3, target_zone),
            ],
            zone_pathogen_mass=mass,
            hvac_downstream_zones=downstream,
            quarantined_ids={3},
        )
        doses = {
            exposure["target_id"]: exposure["dose"]
            for exposure in matrix.hvac_downstream_exposures
        }
        free_dose = doses[2]
        confined_dose = doses[3]
        assert confined_dose == pytest.approx(free_dose * 0.05, abs=5e-5)

    @pytest.mark.parametrize("cabin_air_mode", ("zone_pool", "cabin_compartment"))
    def test_quarantined_hvac_target_outside_cabin_zone_is_unaffected(
        self,
        cabin_air_mode: str,
    ) -> None:
        source = "PC_D6_P_F"
        target_zone = "MainDining_L"
        volumes = {source: 1200.0, target_zone: 1200.0}
        types = {source: "Cabin_Corridor", target_zone: "Dining"}
        downstream = {source: [target_zone]}
        mass = {target_zone: 5000.0}
        core = TransmissionCore(
            rng=np.random.default_rng(11),
            zone_volumes=volumes,
            zone_types=types,
            confinement_isolation_factor=0.05,
            cfg={"transmission": {"cabin_air_mode": cabin_air_mode}},
        )
        core.initialize_zones(list(volumes))
        matrix, _ = core.execute_transmission(
            epoch=1,
            agents=[
                _agent(1, source, infected=True),
                _agent(2, target_zone),
                _agent(3, target_zone),
            ],
            zone_pathogen_mass=mass,
            hvac_downstream_zones=downstream,
            quarantined_ids={3},
        )
        doses = {
            exposure["target_id"]: exposure["dose"]
            for exposure in matrix.hvac_downstream_exposures
        }
        assert doses[3] == pytest.approx(doses[2])

    def test_hvac_confinement_dose_is_finite_nonnegative_and_monotonic(
        self,
    ) -> None:
        source = "PC_D6_P_F"
        target_zone = "PC_D6_P_M"
        volumes = {source: 1200.0, target_zone: 1200.0}
        doses = []
        for confinement_factor in (0.0, 0.05, 0.5, 1.0):
            core = TransmissionCore(
                rng=np.random.default_rng(11),
                zone_volumes=volumes,
                zone_types={
                    source: "Cabin_Corridor",
                    target_zone: "Cabin_Corridor",
                },
                confinement_isolation_factor=confinement_factor,
                cfg={"transmission": {"cabin_air_mode": "zone_pool"}},
            )
            core.initialize_zones(list(volumes))
            matrix, _ = core.execute_transmission(
                epoch=1,
                agents=[_agent(1, source, infected=True), _agent(2, target_zone)],
                zone_pathogen_mass={target_zone: 5000.0},
                hvac_downstream_zones={source: [target_zone]},
                quarantined_ids={2},
            )
            dose = matrix.hvac_downstream_exposures[0]["dose"]
            assert np.isfinite(dose)
            assert dose >= 0.0
            doses.append(dose)
        assert doses == sorted(doses)

    @staticmethod
    def _hvac_multiplicity_case(upstream_count: int) -> tuple[float, int]:
        """One epoch of HVAC dosing with ``upstream_count`` shedding sources."""
        target_zone = "PC_D6_P_M"
        source_zones = [f"PC_D6_P_F_{index}" for index in range(upstream_count)]
        volumes = {zone: 1200.0 for zone in [*source_zones, target_zone]}
        core = TransmissionCore(
            rng=np.random.default_rng(11),
            zone_volumes=volumes,
            zone_types={zone: "Cabin_Corridor" for zone in volumes},
            cfg={"transmission": {"cabin_air_mode": "zone_pool"}},
        )
        core.initialize_zones(list(volumes))
        sources = [
            _agent(index + 1, zone, infected=True)
            for index, zone in enumerate(source_zones)
        ]
        matrix, _ = core.execute_transmission(
            epoch=1,
            agents=[*sources, _agent(100, target_zone)],
            zone_pathogen_mass={target_zone: 5000.0},
            hvac_downstream_zones={
                zone: [target_zone] for zone in source_zones
            },
        )
        exposures = matrix.hvac_downstream_exposures
        total = sum(exposure["dose"] for exposure in exposures)
        return total, len(exposures)

    @pytest.mark.parametrize("upstream_count", (1, 2, 4))
    def test_hvac_dose_is_invariant_to_upstream_source_multiplicity(
        self,
        upstream_count: int,
    ) -> None:
        one_dose, one_records = self._hvac_multiplicity_case(1)
        dose, records = self._hvac_multiplicity_case(upstream_count)

        assert records == 1
        assert one_records == 1
        assert dose == pytest.approx(one_dose)

    def test_hvac_dose_sensitivity_to_standing_mass(self) -> None:
        source_zones = ["PC_D6_P_F_0", "PC_D6_P_F_1"]
        target_zone = "PC_D6_P_M"
        volumes = {zone: 1200.0 for zone in [*source_zones, target_zone]}
        doses = []
        for mass in (0.0, 1000.0, 5000.0, 20000.0):
            core = TransmissionCore(
                rng=np.random.default_rng(11),
                zone_volumes=volumes,
                zone_types={zone: "Cabin_Corridor" for zone in volumes},
                cfg={"transmission": {"cabin_air_mode": "zone_pool"}},
            )
            core.initialize_zones(list(volumes))
            sources = [
                _agent(index + 1, zone, infected=True)
                for index, zone in enumerate(source_zones)
            ]
            matrix, _ = core.execute_transmission(
                epoch=1,
                agents=[*sources, _agent(100, target_zone)],
                zone_pathogen_mass={target_zone: mass},
                hvac_downstream_zones={
                    zone: [target_zone] for zone in source_zones
                },
            )
            assert len(matrix.hvac_downstream_exposures) == (mass > 0.0)
            doses.append(
                matrix.hvac_downstream_exposures[0]["dose"]
                if matrix.hvac_downstream_exposures
                else 0.0
            )
        assert doses[0] == 0.0
        assert doses[1] < doses[2] < doses[3]
        assert all(np.isfinite(dose) and dose >= 0.0 for dose in doses)

    def test_hvac_gate_requires_shedders_and_downstream_edge(self) -> None:
        source = "PC_D6_P_F"
        target_zone = "PC_D6_P_M"
        volumes = {source: 1200.0, target_zone: 1200.0}
        core = TransmissionCore(
            rng=np.random.default_rng(11),
            zone_volumes=volumes,
            zone_types={zone: "Cabin_Corridor" for zone in volumes},
            cfg={"transmission": {"cabin_air_mode": "zone_pool"}},
        )
        core.initialize_zones(list(volumes))
        target = _agent(2, target_zone)
        no_shedder, _ = core.execute_transmission(
            epoch=1,
            agents=[target],
            zone_pathogen_mass={target_zone: 5000.0},
            hvac_downstream_zones={source: [target_zone]},
        )
        assert no_shedder.hvac_downstream_exposures == []

        shedder = _agent(1, source, infected=True)
        no_edge, _ = core.execute_transmission(
            epoch=1,
            agents=[shedder, target],
            zone_pathogen_mass={target_zone: 5000.0},
            hvac_downstream_zones={source: []},
        )
        assert no_edge.hvac_downstream_exposures == []

    def test_hvac_exposure_attributes_all_upstream_sources(self) -> None:
        source_zones = ["PC_D6_P_F_1", "PC_D6_P_F_0"]
        target_zone = "PC_D6_P_M"
        volumes = {zone: 1200.0 for zone in [*source_zones, target_zone]}
        core = TransmissionCore(
            rng=np.random.default_rng(11),
            zone_volumes=volumes,
            zone_types={zone: "Cabin_Corridor" for zone in volumes},
            cfg={"transmission": {"cabin_air_mode": "zone_pool"}},
        )
        core.initialize_zones(list(volumes))
        sources = [
            _agent(20, source_zones[0], infected=True),
            _agent(10, source_zones[1], infected=True),
        ]
        matrix, _ = core.execute_transmission(
            epoch=1,
            agents=[*sources, _agent(100, target_zone)],
            zone_pathogen_mass={target_zone: 5000.0},
            hvac_downstream_zones={
                source_zones[0]: [target_zone],
                source_zones[1]: [target_zone],
            },
        )
        exposure = matrix.hvac_downstream_exposures[0]
        assert exposure["source_zones"] == sorted(source_zones)
        assert exposure["source_agent_ids"] == [10, 20]


class TestCabinCooccupancyPartition:
    """CABIN-OCC-01: time-partitioned co-occupancy on the mate channels."""

    @staticmethod
    def _mate_droplet_dose(
        *,
        quarantined_ids: set[int],
        mode: str = "time_partitioned",
        activity: str | None = None,
    ) -> float:
        zone = "PC_D6_P_F"
        shedder = _agent(1, zone, infected=True)
        target = _agent(2, zone)
        shedder.cabin_mate_ids = frozenset({2})
        target.cabin_mate_ids = frozenset({1})
        if activity is not None:
            shedder.current_activity = activity
            target.current_activity = activity
        core = TransmissionCore(
            rng=np.random.default_rng(42),
            zone_volumes={zone: 1200.0},
            zone_types={zone: "Cabin_Corridor"},
            cfg={
                "transmission": {
                    "cabin_air_mode": "zone_pool",
                    "near_field_air": {"mode": "off"},
                    "cabin_cooccupancy": mode,
                    "room_air_removal": "sealed",
                },
            },
        )
        core.initialize_zones([zone])
        matrix, _ = core.execute_transmission(
            epoch=1,
            agents=[shedder, target],
            zone_pathogen_mass={zone: 0.0},
            quarantined_ids=quarantined_ids,
        )
        return matrix.droplet_exposures[0]["dose"]

    def test_confined_awake_pair_dose_below_baseline(self) -> None:
        """Awake confined mates lose the absence share of co-presence."""
        off = self._mate_droplet_dose(quarantined_ids={1, 2}, mode="off")
        on = self._mate_droplet_dose(quarantined_ids={1, 2})
        assert 0.0 < on < off
        # Both confined, both on the 24-token "home" (non-Sleep) schedule:
        # each carries presence 1 - 1/24, so the copresence floor is ~0.917.
        assert on >= off * 0.8

    def test_asleep_confined_pair_recovers_full_copresence(self) -> None:
        """Both mates asleep are co-present for the whole epoch."""
        off = self._mate_droplet_dose(quarantined_ids={1, 2}, mode="off")
        on = self._mate_droplet_dose(
            quarantined_ids={1, 2}, activity="Sleep",
        )
        assert on == pytest.approx(off)

    def test_unconfined_pair_presence_is_unity(self) -> None:
        """Free agents' location is resolved per epoch — no absence shave."""
        off = self._mate_droplet_dose(quarantined_ids=set(), mode="off")
        on = self._mate_droplet_dose(quarantined_ids=set())
        assert on == pytest.approx(off)

    def test_asleep_pair_contact_factor_is_asleep_share(self) -> None:
        zone = "PC_D6_P_F"
        shedder = _agent(1, zone, infected=True)
        target = _agent(2, zone)
        shedder.cabin_mate_ids = frozenset({2})
        target.cabin_mate_ids = frozenset({1})
        shedder.current_activity = "Sleep"
        target.current_activity = "Sleep"
        core = TransmissionCore(
            rng=np.random.default_rng(42),
            zone_volumes={zone: 1200.0},
            zone_types={zone: "Cabin_Corridor"},
            cfg={"transmission": {"cabin_air_mode": "zone_pool"}},
        )
        core.initialize_zones([zone])
        core._quarantined_ids = {1, 2}
        factor = core._cabin_pair_contact_factor(shedder, target, 0)
        assert factor == pytest.approx(
            core.cabin_cooccupancy.asleep_contact_share
        )
        shedder.current_activity = "Free"
        awake = core._cabin_pair_contact_factor(shedder, target, 0)
        assert awake > factor
        assert awake <= 1.0


class TestRoomAirRemoval:
    """ROOM-AIR-01: first-order removal at the declared AHU rate."""

    @staticmethod
    def _dose_with_ach(ach: float, mode: str = "first_order") -> float:
        zone = "Droplet_Test"
        shedder = _agent(1, zone, infected=True)
        target = _agent(2, zone)
        core = TransmissionCore(
            rng=np.random.default_rng(42),
            zone_volumes={zone: 20.0},
            clock=SimClock(epoch_duration_hours=1.0, mode="hours"),
            cfg={
                "transmission": {
                    "cabin_air_mode": "zone_pool",
                    "near_field_air": {"mode": "off"},
                    "room_air_removal": mode,
                },
            },
        )
        core.zone_air_exchange_per_hour = {zone: ach}
        core.initialize_zones([zone])
        matrix, _ = core.execute_transmission(
            epoch=1,
            agents=[shedder, target],
            zone_pathogen_mass={zone: 0.0},
        )
        return matrix.droplet_exposures[0]["dose"]

    def test_declared_ach_scales_dose_by_residence_factor(self) -> None:
        sealed = self._dose_with_ach(3.0, mode="sealed")
        vented = self._dose_with_ach(3.0)
        expected = -np.expm1(-3.0) / 3.0
        # Exposure records round dose to 4 decimals.
        assert vented == pytest.approx(sealed * expected, abs=1e-3)

    def test_dose_decreases_monotonically_in_ach(self) -> None:
        doses = [self._dose_with_ach(a) for a in (0.0, 1.0, 3.0, 10.0)]
        assert doses[0] == pytest.approx(self._dose_with_ach(0.0, "sealed"))
        assert all(d > 0.0 and np.isfinite(d) for d in doses)
        assert doses == sorted(doses, reverse=True)

    def test_build_zone_air_exchange_map_conventions(self) -> None:
        """ach x duty for AHU branches; duty-0 100%-OA branches exhaust at ach."""
        paths = {
            "hvac_duty": 0.5,
            "oa_fraction": 0.2,
            "hvac_zones": [
                {"ach": 3.0, "rooms": ["Cabin_Deck"]},
                {"ach": 6.0, "hvac_duty": 1.0, "rooms": ["Dining"]},
                {
                    "ach": 19.2, "hvac_duty": 0.0, "oa_fraction": 1.0,
                    "rooms": ["Heads"],
                },
                {
                    "ach": 8.0, "hvac_duty": 0.0, "oa_fraction": 0.2,
                    "rooms": ["Idle"],
                },
            ],
        }
        rates = tc_mod.build_zone_air_exchange_map(paths)
        assert rates["Cabin_Deck"] == pytest.approx(1.5)
        assert rates["Dining"] == pytest.approx(6.0)
        # Exhaust-only sanitary branch: not on the AHU duty cycle.
        assert rates["Heads"] == pytest.approx(19.2)
        # Duty 0 with recirculated air is a genuinely idle branch.
        assert rates["Idle"] == pytest.approx(0.0)
        assert "Undeclared" not in rates

    def test_undeclared_zone_keeps_sealed_dose(self) -> None:
        """No declared ACH and first_order still sealed: baseline dose."""
        zone = "Droplet_Test"
        shedder = _agent(1, zone, infected=True)
        target = _agent(2, zone)
        core = TransmissionCore(
            rng=np.random.default_rng(42),
            zone_volumes={zone: 20.0},
            clock=SimClock(epoch_duration_hours=1.0, mode="hours"),
            cfg={
                "transmission": {
                    "cabin_air_mode": "zone_pool",
                    "near_field_air": {"mode": "off"},
                },
            },
        )
        core.initialize_zones([zone])
        matrix, _ = core.execute_transmission(
            epoch=1,
            agents=[shedder, target],
            zone_pathogen_mass={zone: 0.0},
        )
        assert matrix.droplet_exposures[0]["dose"] == pytest.approx(
            self._dose_with_ach(0.0, mode="sealed")
        )
