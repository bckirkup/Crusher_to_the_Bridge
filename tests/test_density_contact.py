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
    natural_history_clock: str | None = None,
) -> TransmissionCore:
    cfg: dict = {
        "transmission": {
            "contact_mode": contact_mode,
            "density_dependent": density or {},
        },
    }
    if natural_history_clock is not None:
        cfg["natural_history_clock"] = natural_history_clock
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
        core = _core(
            contact_mode="legacy",
            seed=123,
            natural_history_clock="legacy_epoch_day",
        )
        core.initialize_zones([zone])
        matrix, _ = core.execute_transmission(
            epoch=1,
            agents=[shedder, *targets],
            zone_pathogen_mass={zone: 0.0},
        )
        draws = [e["r0_draw"] for e in matrix.shared_room_exposures]
        assert draws
        assert all(d in AVG_R_POOL for d in draws)

        hourly = _core(contact_mode="legacy", seed=123)
        agent = _agent(1, zone, infected=True)
        expected_daily = sum(AVG_R_POOL) / len(AVG_R_POOL)
        daily_draws = [
            sum(hourly._draw_contact_multiplier(10, agent) for _ in range(24))
            for _ in range(8000)
        ]
        assert sum(daily_draws) / len(daily_draws) == pytest.approx(
            expected_daily, rel=0.08,
        )

    def test_density_dependent_contacts_scale(self) -> None:
        """At α=0.5, doubling occupancy increases mean contacts by ~√2 (~41%)."""
        dens = {
            "reference_occupancy": 50,
            "base_contacts_per_day": 1.33,
            "max_contacts_per_day": 100,
            "exponent": 0.5,
            "crew_contact_multiplier": 1.0,
        }
        hourly = _core(density=dens, seed=7)
        legacy = _core(
            density=dens,
            seed=7,
            natural_history_clock="legacy_epoch_day",
        )
        agent = _agent(1, "Lounge")
        n_samples = 8000
        draws_n = [
            sum(hourly._effective_contacts(50, agent) for _ in range(24))
            for _ in range(n_samples)
        ]
        draws_2n = [
            sum(hourly._effective_contacts(100, agent) for _ in range(24))
            for _ in range(n_samples)
        ]
        mean_n = sum(draws_n) / n_samples
        mean_2n = sum(draws_2n) / n_samples
        legacy_n = [
            legacy._effective_contacts(50, agent) for _ in range(n_samples)
        ]
        legacy_2n = [
            legacy._effective_contacts(100, agent) for _ in range(n_samples)
        ]
        assert mean_n == pytest.approx(1.33, rel=0.08)
        assert mean_n == pytest.approx(sum(legacy_n) / n_samples, rel=0.08)
        assert mean_2n == pytest.approx(sum(legacy_2n) / n_samples, rel=0.08)
        assert mean_2n / mean_n == pytest.approx(math.sqrt(2), rel=0.08)

    def test_density_dependent_alpha_zero_matches_legacy(self) -> None:
        """α=0 → mean ≈ base_contacts (1.33) regardless of occupancy."""
        dens = {
            "reference_occupancy": 50,
            "base_contacts_per_day": 1.33,
            "max_contacts_per_day": 100,
            "exponent": 0.0,
            "crew_contact_multiplier": 1.0,
        }
        hourly = _core(density=dens, seed=11)
        legacy = _core(
            density=dens,
            seed=11,
            natural_history_clock="legacy_epoch_day",
        )
        agent = _agent(1, "Lounge")
        n_samples = 6000
        for n_occ in (5, 50, 200):
            draws = [
                sum(hourly._effective_contacts(n_occ, agent) for _ in range(24))
                for _ in range(n_samples)
            ]
            legacy_draws = [
                legacy._effective_contacts(n_occ, agent)
                for _ in range(n_samples)
            ]
            assert sum(draws) / n_samples == pytest.approx(1.33, rel=0.08)
            assert sum(draws) / n_samples == pytest.approx(
                sum(legacy_draws) / n_samples, rel=0.08,
            )

    def test_crew_multiplier_applies_in_dining(self) -> None:
        """Crew in Dining get multiplied contacts; crew in cabins do not."""
        dens = {
            "reference_occupancy": 50,
            "base_contacts_per_day": 4.0,
            "max_contacts_per_day": 100,
            "exponent": 0.0,  # occupancy-independent for clean ratio
            "crew_contact_multiplier": 2.0,
        }
        hourly = _core(density=dens, seed=21)
        legacy = _core(
            density=dens,
            seed=21,
            natural_history_clock="legacy_epoch_day",
        )
        assert "MainDining" in hourly._service_zones
        assert "Main_Galley_Aft" in hourly._service_zones

        crew_dining = _agent(1, "MainDining", role="crew")
        crew_cabin = _agent(2, "CrewCabin", role="crew")
        pax_dining = _agent(3, "MainDining", role="passenger")

        n_samples = 5000
        def hourly_daily_mean(agent: KorkinAgent) -> float:
            return sum(
                sum(hourly._effective_contacts(50, agent) for _ in range(24))
                for _ in range(n_samples)
            ) / n_samples

        def legacy_mean(agent: KorkinAgent) -> float:
            return sum(
                legacy._effective_contacts(50, agent)
                for _ in range(n_samples)
            ) / n_samples

        mean_crew_dining = hourly_daily_mean(crew_dining)
        mean_crew_cabin = hourly_daily_mean(crew_cabin)
        mean_pax_dining = hourly_daily_mean(pax_dining)
        legacy_crew_dining = legacy_mean(crew_dining)
        legacy_crew_cabin = legacy_mean(crew_cabin)
        legacy_pax_dining = legacy_mean(pax_dining)
        assert mean_crew_dining == pytest.approx(8.0, rel=0.08)
        assert mean_crew_cabin == pytest.approx(4.0, rel=0.08)
        assert mean_pax_dining == pytest.approx(4.0, rel=0.08)
        assert mean_crew_dining == pytest.approx(legacy_crew_dining, rel=0.08)
        assert mean_crew_cabin == pytest.approx(legacy_crew_cabin, rel=0.08)
        assert mean_pax_dining == pytest.approx(legacy_pax_dining, rel=0.08)

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
        assert core.density_cfg["base_contacts_per_day"] == pytest.approx(13.4)
        assert core.density_cfg["max_contacts_per_day"] == pytest.approx(40.0)
        assert core.density_cfg["crew_contact_multiplier"] == pytest.approx(2.0)
        retired = _core(
            density={"base_contacts": 1.33, "max_contacts": 20.0},
        )
        assert retired.density_cfg["base_contacts_per_day"] == pytest.approx(1.33)
        assert retired.density_cfg["max_contacts_per_day"] == pytest.approx(20.0)


class TestHeterogeneousZoneDose:
    """Heterogeneous-zone contact mode remains explicitly selectable."""

    def test_default_mode_is_per_partner_contact(self) -> None:
        core = TransmissionCore(rng=np.random.default_rng(0))
        assert core.contact_mode == "per_partner_contact"

    def test_config_yaml_default_is_per_partner_contact(self) -> None:
        from crusher_labs import load_config

        cfg = load_config()
        assert cfg["transmission"]["contact_mode"] == "per_partner_contact"

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


class TestPerPartnerContact:
    """Distinct partner sampling changes variance without changing scale."""

    def test_mean_dose_matches_density_average(self) -> None:
        zone = "Lounge"
        shedders = [
            (_agent(1, zone, infected=True), 1.0),
            (_agent(2, zone, infected=True), 2.0),
            (_agent(3, zone, infected=True), 3.0),
            (_agent(4, zone, infected=True), 4.0),
        ]
        target = _agent(5, zone)
        partner = _core(contact_mode="per_partner_contact", seed=13)
        density = _core(contact_mode="density_dependent", seed=13)
        draws = [
            partner._direct_contact_dose(
                target, shedders, 10.0, 100, 4, False,
            )
            for _ in range(12000)
        ]
        expected = density._direct_contact_dose(
            target, shedders, 10.0, 100, 4, False,
        )
        assert sum(draws) / len(draws) == pytest.approx(expected, rel=0.03)

    def test_single_shedder_creates_contact_heterogeneity(self) -> None:
        zone = "Lounge"
        shedders = [(_agent(1, zone, infected=True), 4.0)]
        target = _agent(2, zone)
        partner = _core(contact_mode="per_partner_contact", seed=22)
        density = _core(contact_mode="density_dependent", seed=22)
        partner_doses = [
            partner._direct_contact_dose(
                target, shedders, 4.0, 100, 1, False,
            )
            for _ in range(6000)
        ]
        density_dose = density._direct_contact_dose(
            target, shedders, 4.0, 100, 1, False,
        )
        partner_variance = np.var(partner_doses)
        assert sum(dose > 0 for dose in partner_doses) < len(partner_doses) * 0.03
        assert partner_variance > np.var([density_dose] * len(partner_doses))

    def test_mean_dose_per_contact_is_occupancy_invariant(self) -> None:
        zone = "Lounge"
        target = _agent(999, zone)

        def _mean_per_contact(n_occupants: int, copies: int) -> float:
            shedders = [
                (_agent(i, zone, infected=True), float(i % 4 + 1))
                for i in range(copies)
            ]
            core = _core(contact_mode="per_partner_contact", seed=n_occupants)
            draws = [
                core._direct_contact_dose(
                    target, shedders, sum(v for _, v in shedders),
                    n_occupants, 1, False,
                )
                for _ in range(50000)
            ]
            return sum(draws) / len(draws)

        lower_occupancy = _mean_per_contact(20, 4)
        higher_occupancy = _mean_per_contact(200, 40)
        assert higher_occupancy >= lower_occupancy * 0.9

    def test_zero_contacts_and_no_shedders_are_zero(self) -> None:
        zone = "Lounge"
        target = _agent(1, zone)
        core = _core(contact_mode="per_partner_contact", seed=3)
        assert core._direct_contact_dose(
            target, [(_agent(2, zone, infected=True), 1.0)],
            1.0, 10, 0, False,
        ) == 0.0
        assert core._direct_contact_dose(
            target, [], 0.0, 10, 2, False,
        ) == 0.0
        assert core._sample_contact_partners(
            [(_agent(2, zone, infected=True), 1.0)], 1, 4,
        ) == ([], 0)

    def test_records_sampled_sources_and_contact_count(self) -> None:
        zone = "Lounge"
        shedder = _agent(1, zone, infected=True)
        targets = [_agent(i, zone) for i in range(2, 12)]
        core = _core(
            contact_mode="per_partner_contact",
            density={
                "base_contacts": 3.0,
                "max_contacts": 3.0,
                "exponent": 0.0,
                "crew_contact_multiplier": 1.0,
            },
            seed=8,
        )
        core.initialize_zones([zone])
        matrix, _ = core.execute_transmission(
            epoch=1,
            agents=[shedder, *targets],
            zone_pathogen_mass={zone: 0.0},
        )
        assert matrix.shared_room_exposures
        for exposure in matrix.shared_room_exposures:
            assert len(exposure["source_ids"]) <= exposure["n_contacts"]
            assert exposure["n_contacts"] == exposure["r0_draw"]
            assert set(exposure["source_ids"]) <= {1}
