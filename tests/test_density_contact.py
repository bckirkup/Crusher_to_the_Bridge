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
