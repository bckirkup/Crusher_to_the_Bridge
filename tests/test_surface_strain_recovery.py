"""Surface strain recovery keeps swab mass honest.

Without an explicit recovery channel, a surface swab could report a genotype
that never deposited on the swabbed surface, or silently discard failed and
below-floor abundance. These tests keep the channel feature-gated, conserved,
and tied to the PR-4 surface composition rather than a second pool.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from crusher_labs.modalities.surface_strain_recovery import (
    DEFAULT_RECOVERY_BY_SURFACE_TYPE,
    STATUS_NO_COMPOSITION,
    STATUS_NO_DEPOSITION,
    STATUS_NOT_CONFIGURED,
    STATUS_RECOVERED,
    SURFACE_TYPE_RECOVERY_ORDER,
    SurfaceLineageMixture,
    SurfaceRecoveryConfig,
    recover_surface_mixture,
    recovery_probability,
    surface_persistence,
)
from engines.infection_dynamics_bridge import InfectionStatus, KorkinAgent
from engines.strain_dose_ledger import ReservoirComposition
from engines.transmission_core import (
    DEFAULT_SURFACE_DECAY_PER_DAY,
    SURFACE_RESERVOIR,
    ContactTracingMatrix,
    TransmissionCore,
)
from picard_framework import PicardRunSpec, ShipSimulation

REPO_ROOT = Path(__file__).resolve().parent.parent
PATHOGEN = "norwalk_gi"
ZONE = "MainDining_L"
ZONES = [ZONE]
ZONE_TYPES = {ZONE: "Dining"}


def _profile() -> dict:
    profiles = json.loads(
        (REPO_ROOT / "data/pathogens/active_profiles.json").read_text(),
    )
    profile = copy.deepcopy(
        next(item for item in profiles["pathogens"] if item["pathogen_id"] == PATHOGEN),
    )
    profile.setdefault("strain_evolution", {})
    profile["strain_evolution"]["min_strain_fraction"] = 0.0
    return profile


def _agent(agent_id: int, strain_id: str) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=agent_id,
        role="passenger",
        immune=False,
        home_zone=ZONE,
        dining_zone=ZONE,
        work_zone=ZONE,
        free_zone=ZONE,
        schedule=["Free"] * 24,
    )
    agent.current_location = ZONE
    agent.infection_status = InfectionStatus.INFECTED
    agent.time_infected = 2
    agent.infect_with_pathogen(PATHOGEN, 1e4, 0, time_infected=2)
    agent.infections[PATHOGEN]["illness"] = "symptomatic"
    agent.assign_strain(PATHOGEN, strain_id)
    return agent


def _config(**overrides: object) -> SurfaceRecoveryConfig:
    values: dict[str, object] = {"enabled": True}
    values.update(overrides)
    return SurfaceRecoveryConfig.from_mapping(values)


class TestSurfaceRecoveryConfig:
    def test_defaults_follow_declared_surface_order(self) -> None:
        values = [
            DEFAULT_RECOVERY_BY_SURFACE_TYPE[surface_type]
            for surface_type in SURFACE_TYPE_RECOVERY_ORDER
        ]
        assert values == sorted(values)

    @pytest.mark.parametrize(
        "field,value",
        [
            ("default_recovery", 1.1),
            ("default_recovery", -0.1),
            ("recovery_by_surface_type", ["Dining"]),
            ("recovery_by_surface_type", {"Dining": -0.1}),
            ("min_lineage_abundance", -1.0),
            ("min_lineage_fraction", -0.1),
        ],
    )
    def test_invalid_probability_or_floor_is_rejected(
        self,
        field: str,
        value: object,
    ) -> None:
        with pytest.raises(ValueError):
            SurfaceRecoveryConfig.from_mapping({field: value})


class TestSurfaceRecoveryFunctions:
    def test_persistence_reuses_surface_decay_factor(self) -> None:
        assert surface_persistence(0) == pytest.approx(1.0)
        expected_survival = 1.0 - DEFAULT_SURFACE_DECAY_PER_DAY
        assert surface_persistence(3) == pytest.approx(expected_survival**3)

    def test_recovery_probability_is_monotone_by_surface_type(self) -> None:
        probabilities = [
            recovery_probability(surface_type, 0, config=_config())
            for surface_type in SURFACE_TYPE_RECOVERY_ORDER
        ]
        assert probabilities == sorted(probabilities)

    def test_recovery_probability_strictly_decreases_with_age(self) -> None:
        probabilities = [
            recovery_probability("Dining", age, config=_config())
            for age in range(4)
        ]
        assert len(set(probabilities)) == 4
        assert probabilities == sorted(probabilities, reverse=True)

    def test_unknown_surface_type_uses_default_recovery(self) -> None:
        assert recovery_probability("Unknown", 0, config=_config()) == pytest.approx(
            _config().default_recovery,
        )


class TestSurfaceLineageMixture:
    def test_empty_calls_have_no_consensus_and_zero_fractions(self) -> None:
        result = SurfaceLineageMixture(
            STATUS_NO_COMPOSITION,
            "Dining",
            0.5,
            0,
            0.0,
        )

        assert result.consensus_genotype is None
        assert result.as_row()["lineage_calls"] == []

    def test_row_reports_fractions_without_renormalizing_abundance(self) -> None:
        result = SurfaceLineageMixture(
            STATUS_RECOVERED,
            "Dining",
            0.75,
            1,
            4.0,
            calls=(("GII.4", 2.0),),
            unresolved_abundance=2.0,
        )

        row = result.as_row()
        assert row["lineage_calls"] == [{
            "genotype": "GII.4",
            "abundance": 2.0,
            "fraction": 0.5,
        }]
        assert row["lineage_unresolved_abundance"] == 2.0

    def test_zero_deposition_has_no_recovered_lineages(self) -> None:
        result = recover_surface_mixture(
            0.0,
            {"GII.4": 1.0},
            surface_type="Dining",
            epochs_since_deposition=0,
            config=_config(),
            rng=np.random.default_rng(1),
        )
        assert result.status == STATUS_NO_DEPOSITION
        assert result.calls == ()
        assert result.unresolved_abundance == 0.0

    def test_empty_composition_moves_sample_to_unresolved(self) -> None:
        result = recover_surface_mixture(
            4.0,
            {},
            surface_type="Dining",
            epochs_since_deposition=0,
            config=_config(),
            rng=np.random.default_rng(1),
        )
        assert result.status == STATUS_NO_COMPOSITION
        assert result.unresolved_abundance == pytest.approx(4.0)
        assert result.resolved_abundance == 0.0

    def test_disabled_config_recovers_nothing(self) -> None:
        result = recover_surface_mixture(
            4.0,
            {"GII.4": 1.0},
            surface_type="Dining",
            epochs_since_deposition=0,
            config=SurfaceRecoveryConfig(),
            rng=np.random.default_rng(1),
        )
        assert result.status == STATUS_NOT_CONFIGURED
        assert result.calls == ()
        assert result.unresolved_abundance == pytest.approx(4.0)

    def test_single_lineage_pool_reports_only_that_lineage(self) -> None:
        result = recover_surface_mixture(
            4.0,
            {"GII.4": 10.0},
            surface_type="Medical",
            epochs_since_deposition=0,
            config=_config(recovery_by_surface_type={"Medical": 1.0}),
            rng=np.random.default_rng(1),
        )
        assert result.status == STATUS_RECOVERED
        assert result.calls == (("GII.4", 4.0),)

    def test_sub_floor_lineage_becomes_unresolved(self) -> None:
        result = recover_surface_mixture(
            10.0,
            {"GII.4": 99.0, "GII.17": 1.0},
            surface_type="Medical",
            epochs_since_deposition=0,
            config=_config(
                recovery_by_surface_type={"Medical": 1.0},
                min_lineage_fraction=0.2,
            ),
            rng=np.random.default_rng(1),
        )
        assert result.calls == (("GII.4", 9.9),)
        assert result.unresolved_abundance == pytest.approx(0.1)
        assert "GII.17" not in dict(result.calls)

    def test_raise_floor_moves_abundance_to_unresolved(self) -> None:
        composition = {"GII.4": 3.0, "GII.17": 1.0}
        low_floor = recover_surface_mixture(
            4.0,
            composition,
            surface_type="Dining",
            epochs_since_deposition=0,
            config=_config(
                recovery_by_surface_type={"Dining": 1.0},
                min_lineage_fraction=0.0,
            ),
            rng=np.random.default_rng(1),
        )
        high_floor = recover_surface_mixture(
            4.0,
            composition,
            surface_type="Dining",
            epochs_since_deposition=0,
            config=_config(
                recovery_by_surface_type={"Dining": 1.0},
                min_lineage_fraction=0.3,
            ),
            rng=np.random.default_rng(1),
        )
        assert high_floor.unresolved_abundance > low_floor.unresolved_abundance
        assert high_floor.resolved_abundance + high_floor.unresolved_abundance == pytest.approx(4.0)

    def test_unreportable_genotype_is_always_unresolved(self) -> None:
        result = recover_surface_mixture(
            2.0,
            {"GII.4": 1.0, "unresolved": 1.0, "": 1.0},
            surface_type="Medical",
            epochs_since_deposition=0,
            config=_config(recovery_by_surface_type={"Medical": 1.0}),
            rng=np.random.default_rng(1),
        )
        assert dict(result.calls) == {"GII.4": pytest.approx(2.0 / 3.0)}
        assert result.unresolved_abundance == pytest.approx(4.0 / 3.0)

    def test_unreportable_genotypes_do_not_consume_recovery_draws(self) -> None:
        with_unreportable = recover_surface_mixture(
            2.0,
            {"": 1.0, "GII.4": 1.0},
            surface_type="Medical",
            epochs_since_deposition=0,
            config=_config(
                recovery_by_surface_type={"Medical": 0.7},
                min_lineage_fraction=0.0,
            ),
            rng=np.random.default_rng(7),
        )
        reportable_only = recover_surface_mixture(
            1.0,
            {"GII.4": 1.0},
            surface_type="Medical",
            epochs_since_deposition=0,
            config=_config(
                recovery_by_surface_type={"Medical": 0.7},
                min_lineage_fraction=0.0,
            ),
            rng=np.random.default_rng(7),
        )
        assert with_unreportable.calls == reportable_only.calls == (
            ("GII.4", 1.0),
        )

    @pytest.mark.parametrize("seed", range(20))
    def test_abundance_is_conserved_for_random_draws(self, seed: int) -> None:
        result = recover_surface_mixture(
            12.5,
            {"GII.4": 4.0, "GII.17": 3.0, "unresolved": 1.0},
            surface_type="Dining",
            epochs_since_deposition=seed % 4,
            config=_config(),
            rng=np.random.default_rng(seed),
        )
        assert result.resolved_abundance + result.unresolved_abundance == pytest.approx(12.5)


class TestSurfaceReservoirIntegration:
    def test_three_way_surface_composition_round_trips_through_pr4(self) -> None:
        profile = _profile()
        core = TransmissionCore(
            rng=np.random.default_rng(2),
            zone_volumes={ZONE: 60.0},
            pathogen_profiles={PATHOGEN: profile},
            zone_types=ZONE_TYPES,
            cfg={"variant_surveillance": {"enabled": True}},
        )
        core.initialize_zones(ZONES)
        assert core.strain_registry is not None
        registry = core.strain_registry
        strains = [
            registry.mint(PATHOGEN, genotype=genotype)
            for genotype in ("GII.4", "GII.17", "GII.2")
        ]
        occupants = {
            ZONE: [
                _agent(index, strain.strain_id)
                for index, strain in enumerate(strains, start=1)
            ],
        }
        core._pathway_fomite(
            0,
            occupants,
            {},
            ContactTracingMatrix(epoch=0),
            [],
            pathogen_id=PATHOGEN,
            profile=profile,
        )
        composition = core.surface_lineage_masses(PATHOGEN, ZONE)
        result = recover_surface_mixture(
            10.0,
            composition,
            surface_type="Dining",
            epochs_since_deposition=core.surface_epochs_since_deposition(
                PATHOGEN, ZONE, 0,
            ) or 0,
            config=_config(recovery_by_surface_type={"Dining": 1.0}),
            rng=np.random.default_rng(3),
        )
        assert set(composition) == {"GII.4", "GII.17", "GII.2"}
        assert {genotype for genotype, _ in result.calls} == set(composition)
        assert result.resolved_abundance == pytest.approx(10.0)

    def test_untracked_core_accessors_are_empty(self) -> None:
        core = TransmissionCore(
            rng=np.random.default_rng(1),
            zone_volumes={ZONE: 60.0},
            pathogen_profiles={PATHOGEN: _profile()},
            zone_types=ZONE_TYPES,
            cfg={"variant_surveillance": {"enabled": False}},
        )
        assert core.surface_lineage_masses(PATHOGEN, ZONE) == {}
        assert core.surface_epochs_since_deposition(PATHOGEN, ZONE, 0) is None

    def test_surface_accessor_groups_registry_contributors_by_genotype(self) -> None:
        core = TransmissionCore(
            rng=np.random.default_rng(1),
            zone_volumes={ZONE: 60.0},
            pathogen_profiles={PATHOGEN: _profile()},
            zone_types=ZONE_TYPES,
            cfg={"variant_surveillance": {"enabled": True}},
        )
        assert core.strain_registry is not None
        first = core.strain_registry.mint(PATHOGEN, genotype="GII.4")
        second = core.strain_registry.mint(PATHOGEN, genotype="GII.4")
        key = ReservoirComposition.key(SURFACE_RESERVOIR, PATHOGEN, ZONE)
        core._reservoir.deposit(key, (first.strain_id, None), 2.0)
        core._reservoir.deposit(key, (second.strain_id, None), 3.0)
        core._reservoir.deposit(key, ("unresolved", None), 1.0)
        assert core.surface_lineage_masses(PATHOGEN, ZONE) == {
            "GII.4": 5.0,
            "unresolved": 1.0,
        }

    def test_feature_off_swabs_match_when_surface_block_is_absent(self) -> None:
        disabled_spec = PicardRunSpec.from_legacy_yaml(str(REPO_ROOT), num_epochs=1)
        absent_spec = PicardRunSpec.from_legacy_yaml(str(REPO_ROOT), num_epochs=1)
        variant_cfg = copy.deepcopy(absent_spec.legacy_cfg["variant_surveillance"])
        variant_cfg.pop("surface_sampling", None)
        absent_spec.legacy_cfg["variant_surveillance"] = variant_cfg

        disabled = ShipSimulation(
            disabled_spec, display=False, repo_root=str(REPO_ROOT),
        ).run(n_epochs=1)
        absent = ShipSimulation(
            absent_spec, display=False, repo_root=str(REPO_ROOT),
        ).run(n_epochs=1)
        disabled_swabs = disabled.history[0]["observation_engine"]["surface_swab"]
        absent_swabs = absent.history[0]["observation_engine"]["surface_swab"]

        assert disabled_swabs == absent_swabs
        assert all(
            "strain_recovery" not in swab for swab in disabled_swabs.values()
        )

    def test_armed_recovery_adds_conserved_payload_without_changing_swab_fields(
        self,
    ) -> None:
        # Deposition needs a shedding host, and under the hours clock a host is
        # not one epoch (one hour) past infection when it starts: the run has to
        # cover a biological day for surfaces to carry a lineage at all.
        # Rebaselined for the dose-pathway dimensional fix: corrected
        # per-epoch shedding is 24x smaller, so the run must supply enough
        # biological time and seeded hosts to clear the 1e-4 swab quantisation.
        epochs = 48
        enabled_spec = PicardRunSpec.from_legacy_yaml(
            str(REPO_ROOT), num_epochs=epochs,
        )
        enabled_spec.legacy_cfg["initial_infected"] = 10
        variant_cfg = copy.deepcopy(
            enabled_spec.legacy_cfg["variant_surveillance"],
        )
        variant_cfg["enabled"] = True
        variant_cfg["surface_sampling"] = {
            "enabled": True,
            "recovery_by_surface_type": {
                surface_type: 1.0 for surface_type in SURFACE_TYPE_RECOVERY_ORDER
            },
            "default_recovery": 1.0,
            "min_lineage_abundance": 0.0,
            "min_lineage_fraction": 0.0,
        }
        enabled_spec.legacy_cfg["variant_surveillance"] = variant_cfg

        baseline_spec = copy.deepcopy(enabled_spec)
        baseline_variant_cfg = copy.deepcopy(variant_cfg)
        baseline_variant_cfg["surface_sampling"]["enabled"] = False
        baseline_spec.legacy_cfg["variant_surveillance"] = baseline_variant_cfg

        armed_sim = ShipSimulation(
            enabled_spec, display=False, repo_root=str(REPO_ROOT),
        )
        armed = armed_sim.run(n_epochs=epochs)
        baseline = ShipSimulation(
            baseline_spec, display=False, repo_root=str(REPO_ROOT),
        ).run(n_epochs=epochs)
        armed_swabs = armed.history[-1]["observation_engine"]["surface_swab"]
        baseline_swabs = baseline.history[-1]["observation_engine"]["surface_swab"]

        payload_rows = [
            (zone_name, swab["strain_recovery"])
            for zone_name, swab in armed_swabs.items()
            if "strain_recovery" in swab
        ]
        assert payload_rows
        assert set(armed_swabs) == set(baseline_swabs)
        assert armed_sim.tx_core is not None
        for zone_name, swab in armed_swabs.items():
            preexisting = {
                key: value
                for key, value in swab.items()
                if key != "strain_recovery"
            }
            assert preexisting == baseline_swabs[zone_name]

            for pathogen_id, payload in swab.get(
                "strain_recovery", {},
            ).items():
                composition = armed_sim.tx_core.surface_lineage_masses(
                    pathogen_id, zone_name,
                )
                calls = payload["lineage_calls"]
                assert sum(
                    call["abundance"] for call in calls
                ) + payload["lineage_unresolved_abundance"] == pytest.approx(
                    payload["sampled_abundance"],
                )
                assert {
                    call["genotype"] for call in calls
                } <= set(composition)

    @pytest.mark.parametrize(
        "swab,aggregate,deposit",
        [
            ({"recovered_mass": 0.0}, 1.0, False),
            ({"recovered_mass": 1.0}, 0.0, False),
            ({"recovered_mass": 1.0}, 1.0, False),
            ({"recovered_mass": 1.0}, 1.0, True),
        ],
    )
    def test_armed_recovery_skips_empty_sampling_inputs(
        self,
        swab: dict[str, float],
        aggregate: float,
        deposit: bool,
    ) -> None:
        spec = PicardRunSpec.from_legacy_yaml(str(REPO_ROOT), num_epochs=1)
        spec.legacy_cfg["variant_surveillance"]["enabled"] = True
        spec.legacy_cfg["variant_surveillance"]["surface_sampling"] = {
            "enabled": True,
            "recovery_by_surface_type": {"Dining": 1.0},
            "default_recovery": 1.0,
            "min_lineage_fraction": 0.0,
        }
        sim = ShipSimulation(spec, display=False, repo_root=str(REPO_ROOT))
        sim.initialize()
        assert sim.tx_core is not None
        zone_name = sim.zone_names[0]
        sim.tx_core.surface_pools[zone_name] = aggregate
        if deposit:
            assert sim.tx_core.strain_registry is not None
            strain = sim.tx_core.strain_registry.mint(
                PATHOGEN, genotype="GII.4",
            )
            key = ReservoirComposition.key(
                SURFACE_RESERVOIR, PATHOGEN, zone_name,
            )
            sim.tx_core._reservoir.deposit(key, (strain.strain_id, None), 1.0)
        work = SimpleNamespace(
            swab_results={zone_name: dict(swab)},
            epoch=0,
        )
        sim._attach_surface_strain_recovery(work)
        assert "strain_recovery" not in work.swab_results[zone_name]
