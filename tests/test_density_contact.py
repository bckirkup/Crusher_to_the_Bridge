"""Density-dependent contact model (contact_mode) unit tests."""
from __future__ import annotations

import math

import numpy as np
import pytest

from engines.infection_dynamics_bridge import (
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
)
from engines.transmission_core import AVG_R_POOL, TransmissionCore


def _agent(
    aid: int,
    loc: str,
    *,
    role: str = "passenger",
    infected: bool = False,
) -> KorkinAgent:
    a = KorkinAgent(
        agent_id=aid,
        role=role,
        immune=False,
        home_zone=loc,
        dining_zone="MainDining",
        work_zone=loc,
        free_zone=loc,
        schedule=["home"] * 24,
    )
    if infected:
        a.infection_status = InfectionStatus.INFECTED
        a.illness_status = IllnessStatus.SYMPTOMATIC
        a.time_infected = 1
    a.current_location = loc
    return a


def _core(
    *,
    contact_mode: str = "density_dependent",
    density: dict | None = None,
    zone_types: dict[str, str] | None = None,
    seed: int = 0,
) -> TransmissionCore:
    cfg = {
        "transmission": {
            "contact_mode": contact_mode,
            "density_dependent": density or {},
        },
    }
    zt = zone_types or {
        "Lounge": "Free",
        "MainDining": "Dining",
        "CrewCabin": "Room",
        "Main_Galley_Aft": "Dining",
    }
    return TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={z: 200.0 for z in zt},
        zone_types=zt,
        cfg=cfg,
    )


class TestDensityContactMode:
    def test_legacy_contact_mode_unchanged(self) -> None:
        """With contact_mode=legacy, r0_draw comes only from AVG_R_POOL."""
        zone = "Lounge"
        shedder = _agent(1, zone, infected=True)
        targets = [_agent(i, zone) for i in range(2, 12)]
        core = _core(contact_mode="legacy", seed=123)
        core.initialize_zones([zone])
        matrix, _ = core.execute_transmission(
            epoch=1,
            agents=[shedder, *targets],
            zone_pathogen_mass={zone: 0.0},
        )
        draws = [e["r0_draw"] for e in matrix.shared_room_exposures]
        assert draws
        assert all(d in AVG_R_POOL for d in draws)

    def test_density_dependent_contacts_scale(self) -> None:
        """At α=0.5, doubling occupancy increases mean contacts by ~√2 (~41%)."""
        dens = {
            "reference_occupancy": 50,
            "base_contacts": 1.33,
            "max_contacts": 100,
            "exponent": 0.5,
            "crew_contact_multiplier": 1.0,
        }
        core = _core(density=dens, seed=7)
        agent = _agent(1, "Lounge")
        n_samples = 8000
        draws_n = [core._effective_contacts(50, agent) for _ in range(n_samples)]
        draws_2n = [core._effective_contacts(100, agent) for _ in range(n_samples)]
        mean_n = sum(draws_n) / n_samples
        mean_2n = sum(draws_2n) / n_samples
        # Expected: 1.33 and 1.33*√2 ≈ 1.881
        assert mean_n == pytest.approx(1.33, rel=0.08)
        assert mean_2n / mean_n == pytest.approx(math.sqrt(2), rel=0.08)

    def test_density_dependent_alpha_zero_matches_legacy(self) -> None:
        """α=0 → mean ≈ base_contacts (1.33) regardless of occupancy."""
        dens = {
            "reference_occupancy": 50,
            "base_contacts": 1.33,
            "max_contacts": 100,
            "exponent": 0.0,
            "crew_contact_multiplier": 1.0,
        }
        core = _core(density=dens, seed=11)
        agent = _agent(1, "Lounge")
        n_samples = 6000
        for n_occ in (5, 50, 200):
            draws = [core._effective_contacts(n_occ, agent) for _ in range(n_samples)]
            assert sum(draws) / n_samples == pytest.approx(1.33, rel=0.08)

    def test_crew_multiplier_applies_in_dining(self) -> None:
        """Crew in Dining get multiplied contacts; crew in cabins do not."""
        dens = {
            "reference_occupancy": 50,
            "base_contacts": 4.0,
            "max_contacts": 100,
            "exponent": 0.0,  # occupancy-independent for clean ratio
            "crew_contact_multiplier": 2.0,
        }
        core = _core(density=dens, seed=21)
        assert "MainDining" in core._service_zones
        assert "Main_Galley_Aft" in core._service_zones

        crew_dining = _agent(1, "MainDining", role="crew")
        crew_cabin = _agent(2, "CrewCabin", role="crew")
        pax_dining = _agent(3, "MainDining", role="passenger")

        n_samples = 5000
        mean_crew_dining = (
            sum(core._effective_contacts(50, crew_dining) for _ in range(n_samples))
            / n_samples
        )
        mean_crew_cabin = (
            sum(core._effective_contacts(50, crew_cabin) for _ in range(n_samples))
            / n_samples
        )
        mean_pax_dining = (
            sum(core._effective_contacts(50, pax_dining) for _ in range(n_samples))
            / n_samples
        )
        assert mean_crew_dining == pytest.approx(8.0, rel=0.08)
        assert mean_crew_cabin == pytest.approx(4.0, rel=0.08)
        assert mean_pax_dining == pytest.approx(4.0, rel=0.08)

    def test_max_contacts_cap(self) -> None:
        """Contacts never exceed max_contacts even at high occupancy."""
        dens = {
            "reference_occupancy": 10,
            "base_contacts": 5.0,
            "max_contacts": 7,
            "exponent": 1.0,
            "crew_contact_multiplier": 1.0,
        }
        core = _core(density=dens, seed=33)
        agent = _agent(1, "Lounge")
        for _ in range(2000):
            # raw = 5 * (10000/10)^1 = 5000 → capped at 7
            assert core._effective_contacts(10_000, agent) <= 7

    def test_exponent_sensitivity_changes_r0_draw(self) -> None:
        """Changing exponent changes r0_draw under fixed seed and occupancy."""
        zone = "Lounge"
        shedder = _agent(1, zone, infected=True)
        targets = [_agent(i, zone) for i in range(2, 22)]  # n=20
        agents = [shedder, *targets]

        def _draws(exponent: float) -> list[int]:
            core = _core(
                density={
                    "reference_occupancy": 50,
                    "base_contacts": 1.33,
                    "max_contacts": 50,
                    "exponent": exponent,
                    "crew_contact_multiplier": 1.0,
                },
                seed=99,
            )
            core.initialize_zones([zone])
            matrix, _ = core.execute_transmission(
                epoch=1,
                agents=agents,
                zone_pathogen_mass={zone: 0.0},
            )
            return [e["r0_draw"] for e in matrix.shared_room_exposures]

        assert _draws(0.0) != _draws(1.0)

    def test_partial_density_override_merges_defaults(self) -> None:
        """Shallow campaign patch {exponent: x} must keep other density defaults."""
        core = TransmissionCore(
            rng=np.random.default_rng(0),
            zone_types={"MainDining": "Dining"},
            cfg={
                "transmission": {
                    "contact_mode": "density_dependent",
                    "density_dependent": {"exponent": 0.25},
                },
            },
        )
        assert core.density_cfg["exponent"] == pytest.approx(0.25)
        assert core.density_cfg["reference_occupancy"] == pytest.approx(50.0)
        assert core.density_cfg["base_contacts"] == pytest.approx(1.33)
        assert core.density_cfg["max_contacts"] == pytest.approx(20.0)
        assert core.density_cfg["crew_contact_multiplier"] == pytest.approx(2.0)


class TestHeterogeneousZoneDose:
    """Optional second-stage contact_mode (not the default)."""

    def test_default_mode_remains_density_dependent(self) -> None:
        core = TransmissionCore(rng=np.random.default_rng(0))
        assert core.contact_mode == "density_dependent"

    def test_config_yaml_default_is_density_dependent(self) -> None:
        from crusher_labs import load_config

        cfg = load_config()
        assert cfg["transmission"]["contact_mode"] == "density_dependent"

    def test_zone_sigma_ordering(self) -> None:
        core = _core(
            contact_mode="heterogeneous_zone_dose",
            zone_types={
                "CabinA": "Cabin_Corridor",
                "Lounge": "Free",
                "MainDining": "Dining",
                "Main_Galley_Aft": "Dining",
            },
        )
        assert core._zone_exposure_sigma("CabinA") < core._zone_exposure_sigma("Lounge")
        assert core._zone_exposure_sigma("Lounge") < core._zone_exposure_sigma("MainDining")
        assert core._zone_exposure_sigma("MainDining") == pytest.approx(1.0)
        assert core._zone_exposure_sigma("Main_Galley_Aft") == pytest.approx(1.0)

    def test_exposure_factor_mean_near_one(self) -> None:
        """Mean-1 lognormal: E[factor] ≈ 1 for each zone class."""
        core = _core(
            contact_mode="heterogeneous_zone_dose",
            zone_types={
                "CabinA": "Cabin_Corridor",
                "Lounge": "Free",
                "MainDining": "Dining",
            },
            seed=42,
        )
        n = 12_000
        for zone in ("CabinA", "Lounge", "MainDining"):
            draws = [core._zone_exposure_factor(zone) for _ in range(n)]
            assert sum(draws) / n == pytest.approx(1.0, abs=0.05)

    def test_heterogeneous_records_exposure_factor(self) -> None:
        zone = "MainDining"
        shedder = _agent(1, zone, infected=True)
        targets = [_agent(i, zone) for i in range(2, 8)]
        dens = {
            "reference_occupancy": 50,
            "base_contacts": 5.0,
            "max_contacts": 50,
            "exponent": 0.0,
            "crew_contact_multiplier": 1.0,
        }
        core = _core(
            contact_mode="heterogeneous_zone_dose",
            density=dens,
            zone_types={zone: "Dining"},
            seed=7,
        )
        core.initialize_zones([zone])
        matrix, _ = core.execute_transmission(
            epoch=1,
            agents=[shedder, *targets],
            zone_pathogen_mass={zone: 0.0},
        )
        assert matrix.shared_room_exposures
        for rec in matrix.shared_room_exposures:
            assert "zone_exposure_factor" in rec
            assert rec["zone_exposure_factor"] > 0.0

    def test_density_mode_omits_exposure_factor(self) -> None:
        zone = "Lounge"
        shedder = _agent(1, zone, infected=True)
        target = _agent(2, zone)
        core = _core(contact_mode="density_dependent", seed=3)
        core.initialize_zones([zone])
        matrix, _ = core.execute_transmission(
            epoch=1,
            agents=[shedder, target],
            zone_pathogen_mass={zone: 0.0},
        )
        if matrix.shared_room_exposures:
            assert "zone_exposure_factor" not in matrix.shared_room_exposures[0]

    def test_heterogeneous_changes_doses_vs_density(self) -> None:
        """Sensitivity: heterogeneous_zone_dose changes recorded doses vs density."""
        zone = "MainDining"
        shedder = _agent(1, zone, infected=True)
        targets = [_agent(i, zone) for i in range(2, 22)]
        agents = [shedder, *targets]
        dens = {
            "reference_occupancy": 50,
            "base_contacts": 4.0,
            "max_contacts": 50,
            "exponent": 0.0,
            "crew_contact_multiplier": 1.0,
        }

        def _doses(mode: str) -> list[float]:
            core = _core(
                contact_mode=mode,
                density=dens,
                zone_types={zone: "Dining"},
                seed=99,
            )
            core.initialize_zones([zone])
            matrix, _ = core.execute_transmission(
                epoch=1,
                agents=agents,
                zone_pathogen_mass={zone: 0.0},
            )
            return [e["dose"] for e in matrix.shared_room_exposures]

        assert _doses("density_dependent") != _doses("heterogeneous_zone_dose")

    def test_sigma_override_sensitivity(self) -> None:
        """Changing Dining sigma changes exposure-factor variance (config wiring)."""
        zt = {"MainDining": "Dining"}

        def _var(sigma: float) -> float:
            core = TransmissionCore(
                rng=np.random.default_rng(0),
                zone_types=zt,
                cfg={
                    "transmission": {
                        "contact_mode": "heterogeneous_zone_dose",
                        "heterogeneous_zone_dose": {
                            "sigma_by_zone_type": {"Dining": sigma},
                        },
                    },
                },
            )
            draws = [core._zone_exposure_factor("MainDining") for _ in range(4000)]
            mean = sum(draws) / len(draws)
            return sum((x - mean) ** 2 for x in draws) / len(draws)

        assert _var(1.0) > _var(0.2) * 2.0
