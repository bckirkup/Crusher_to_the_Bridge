"""Strain composition in the environmental pools (Paper 3 PR 4).

The pools CTB doses from — zone aerosol, surfaces, food, environmental
reservoirs — carried a scalar mass and no lineage, so a pickup was attributed to
whoever happened to be shedding at pickup time. Here each pool carries a strain
mixture that ages with it, the mixture accounts for exactly the pool's mass (the
sub-floor tail included, held in :data:`UNRESOLVED_STRAIN` rather than dropped),
and lineages with no host and no pool remnant leave the registry.
"""

from __future__ import annotations

import copy
import json
import time
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

from engines.infection_dynamics_bridge import (  # noqa: E402
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
)
from engines.strain_dose_ledger import (  # noqa: E402
    UNRESOLVED_STRAIN,
    ReservoirComposition,
    StrainDoseLedger,
)
from engines.strain_state import Phenotype, StrainRegistry  # noqa: E402
from engines.transmission_core import (  # noqa: E402
    AIRBORNE_RESERVOIR,
    ENV_HOST_DEPOSITION_FRACTION,
    ENV_RESERVOIR,
    SURFACE_RESERVOIR,
    ContactTracingMatrix,
    TransmissionCore,
)

PATHOGEN = "norwalk_gi"
ENV_PATHOGEN = "cdiff_test"
VARIANT_CFG = {"variant_surveillance": {"enabled": True}}
ZONES = ["Cabin_A", "MainDining_L", "Medical_Bay"]
ZONE_TYPES = {
    "Cabin_A": "Cabin_Corridor",
    "MainDining_L": "Dining",
    "Medical_Bay": "Medical",
}


def _norwalk_profile(min_strain_fraction: float = 0.0) -> dict:
    data = json.loads(
        (REPO_ROOT / "data/pathogens/active_profiles.json").read_text(),
    )
    profile = copy.deepcopy(
        next(p for p in data["pathogens"] if p["pathogen_id"] == PATHOGEN),
    )
    profile.setdefault("strain_evolution", {})
    profile["strain_evolution"]["min_strain_fraction"] = min_strain_fraction
    return profile


def _env_profile() -> dict:
    """A zone-scoped spore reservoir with person-to-person shedding."""
    base = _norwalk_profile()
    base["environmental_contamination"] = {
        "enabled": True,
        "source_type": "spore_reservoir",
        "source_zones": ["*Medical*"],
        "base_emission_rate": 0.01,
        "exposure_probability_per_epoch": 1.0,
        "spore_decay_rate_per_epoch": 0.1,
        "colonization_rate_per_epoch": 0.0,
        "baseline_environmental_load": 100.0,
        "person_to_person": True,
    }
    return base


def _agent(
    aid: int,
    loc: str,
    *,
    pathogen_id: str = PATHOGEN,
    infected: bool = False,
) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=aid,
        role="passenger",
        immune=False,
        home_zone=loc,
        dining_zone=loc,
        work_zone=loc,
        free_zone=loc,
        schedule=["Free"] * 24,
    )
    agent.current_location = loc
    if infected:
        agent.infection_status = InfectionStatus.INFECTED
        agent.illness_status = IllnessStatus.SYMPTOMATIC
        agent.time_infected = 2
        agent.infect_with_pathogen(pathogen_id, 1e4, 0, time_infected=2)
        agent.infections[pathogen_id]["illness"] = IllnessStatus.SYMPTOMATIC
    return agent


def _core(
    *,
    cfg: dict | None = VARIANT_CFG,
    seed: int = 3,
    pathogen_id: str = PATHOGEN,
    profile: dict | None = None,
) -> TransmissionCore:
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes=dict.fromkeys(ZONES, 60.0),
        pathogen_profiles={pathogen_id: profile or _norwalk_profile()},
        zone_types=ZONE_TYPES,
        cfg=cfg,
    )
    core.initialize_zones(ZONES)
    return core


def _key(kind: str, zone: str, pathogen_id: str = PATHOGEN) -> str:
    return ReservoirComposition.key(kind, pathogen_id, zone)


# ── Composition arithmetic: mass, decay, floor ──────────────────────────

class TestCompositionMass:
    def test_decay_is_proportional_so_composition_is_unchanged(self) -> None:
        """Uniform decay ages a pool, it does not reshape it."""
        reservoir = ReservoirComposition()
        key = _key(SURFACE_RESERVOIR, "Cabin_A")
        reservoir.deposit(key, ("s:1", 1), 30.0)
        reservoir.deposit(key, ("s:2", 2), 10.0)
        before = reservoir.mix(key)
        reservoir.decay(0.25, key)
        after = reservoir.mix(key)
        assert before is not None
        assert after is not None
        assert after.shares == pytest.approx(dict(before.shares))
        assert reservoir.total_mass(key) == pytest.approx(10.0)

    def test_lumping_moves_the_tail_without_losing_mass(self) -> None:
        reservoir = ReservoirComposition()
        key = _key(SURFACE_RESERVOIR, "Cabin_A")
        reservoir.deposit(key, ("s:1", 1), 100.0)
        reservoir.deposit(key, ("s:2", 2), 0.5)
        reservoir.deposit(key, ("s:3", 3), 0.25)
        reservoir.lump(0.05, key)
        contributors = reservoir.contributors(key)
        assert reservoir.total_mass(key) == pytest.approx(100.75)
        assert contributors[(UNRESOLVED_STRAIN, None)] == pytest.approx(0.75)
        assert set(contributors) == {("s:1", 1), (UNRESOLVED_STRAIN, None)}

    def test_a_flat_pool_keeps_its_dominant_lineage(self) -> None:
        """A floor above every share must not erase the pool's identity."""
        reservoir = ReservoirComposition()
        key = _key(SURFACE_RESERVOIR, "Cabin_A")
        reservoir.deposit(key, ("s:1", 1), 2.0)
        reservoir.deposit(key, ("s:2", 2), 1.0)
        reservoir.lump(0.9, key)
        contributors = reservoir.contributors(key)
        # The lineage survives; its depositor, itself sub-floor, does not.
        assert contributors[("s:1", None)] == pytest.approx(2.0)
        assert reservoir.total_mass(key) == pytest.approx(3.0)

    def test_a_kept_lineage_loses_its_sub_floor_depositors_first(self) -> None:
        """The lineage survives a small deposit; whose deposit it was does not."""
        reservoir = ReservoirComposition()
        key = _key(SURFACE_RESERVOIR, "Cabin_A")
        reservoir.deposit(key, ("s:1", 1), 100.0)
        reservoir.deposit(key, ("s:1", 2), 1.0)
        reservoir.lump(0.05, key)
        contributors = reservoir.contributors(key)
        assert contributors[("s:1", 1)] == pytest.approx(100.0)
        assert contributors[("s:1", None)] == pytest.approx(1.0)
        assert reservoir.total_mass(key) == pytest.approx(101.0)

    def test_no_floor_leaves_the_composition_alone(self) -> None:
        reservoir = ReservoirComposition()
        key = _key(SURFACE_RESERVOIR, "Cabin_A")
        reservoir.deposit(key, ("s:1", 1), 100.0)
        reservoir.deposit(key, ("s:2", 2), 1e-6)
        reservoir.lump(0.0, key)
        assert set(reservoir.contributors(key)) == {("s:1", 1), ("s:2", 2)}

    def test_decayed_contributors_and_pools_are_forgotten(self) -> None:
        """State cannot grow forever with lineages nothing carries any more."""
        reservoir = ReservoirComposition()
        key = _key(SURFACE_RESERVOIR, "Cabin_A")
        reservoir.deposit(key, ("s:1", 1), 1.0)
        reservoir.decay(0.0, key)
        reservoir.drop_empty()
        assert reservoir.keys() == ()
        assert reservoir.strain_ids() == set()


# ── Registry collection ────────────────────────────────────────────────

class TestRegistryCollection:
    def test_ancestors_of_a_live_lineage_survive_their_own_extinction(self) -> None:
        registry = StrainRegistry()
        founder = registry.mint(PATHOGEN)
        child = registry.derive(founder, origin="transmission")
        grandchild = registry.derive(child, origin="transmission")
        dropped = registry.collect([grandchild.strain_id])
        assert dropped == ()
        assert founder.strain_id in registry
        assert child.strain_id in registry

    def test_a_recombinant_keeps_both_parents(self) -> None:
        registry = StrainRegistry()
        first = registry.mint(PATHOGEN, genotype="GII.4")
        second = registry.mint(PATHOGEN, genotype="GII.17")
        child = registry.recombine(first, second)
        registry.collect([child.strain_id])
        assert first.strain_id in registry
        assert second.strain_id in registry

    def test_a_lineage_with_no_host_and_no_pool_is_dropped(self) -> None:
        registry = StrainRegistry()
        live = registry.mint(PATHOGEN)
        extinct = registry.mint(PATHOGEN)
        dropped = registry.collect([live.strain_id])
        assert dropped == (extinct.strain_id,)
        assert extinct.strain_id not in registry
        assert [s.strain_id for s in registry.founders(PATHOGEN)] == [
            live.strain_id,
        ]

    def test_collected_ids_are_never_reused(self) -> None:
        registry = StrainRegistry()
        first = registry.mint(PATHOGEN)
        registry.collect([])
        assert registry.mint(PATHOGEN).strain_id != first.strain_id


class TestCoreCollection:
    def test_host_and_pool_references_both_keep_a_lineage(self) -> None:
        core = _core()
        registry = core.strain_registry
        assert registry is not None
        carried = registry.mint(PATHOGEN)
        pooled = registry.mint(PATHOGEN)
        orphan = registry.mint(PATHOGEN)
        host = _agent(1, "Cabin_A", infected=True)
        host.assign_strain(PATHOGEN, carried.strain_id)
        core._reservoir.deposit(
            _key(SURFACE_RESERVOIR, "Cabin_A"), (pooled.strain_id, 1), 5.0,
        )
        dropped = core.collect_extinct_strains([host])
        assert dropped == (orphan.strain_id,)
        assert carried.strain_id in registry
        assert pooled.strain_id in registry


# ── Pools attribute a pickup to what is in them ────────────────────────

class TestPoolAttribution:
    def test_hvac_pickup_follows_the_target_zone_air_not_the_shedder(self) -> None:
        """The mass inhaled downstream is older than this epoch's shedding."""
        core = _core()
        registry = core.strain_registry
        assert registry is not None
        resident = registry.mint(PATHOGEN, genotype="GII.4")
        upstream = registry.mint(PATHOGEN, genotype="GII.17")
        core._reservoir.deposit(
            _key(AIRBORNE_RESERVOIR, "MainDining_L"), (resident.strain_id, None), 50.0,
        )
        shedder = _agent(1, "Cabin_A", infected=True)
        shedder.assign_strain(PATHOGEN, upstream.strain_id)
        target = _agent(2, "MainDining_L")
        ledger = StrainDoseLedger()

        core._pathway_hvac_airborne(
            0,
            {"Cabin_A": [shedder], "MainDining_L": [target]},
            dict.fromkeys(ZONES, 1e3),
            {"Cabin_A": ["MainDining_L"]},
            {},
            ContactTracingMatrix(epoch=0),
            [],
            None,
            pathogen_id=PATHOGEN,
            ledger=ledger,
        )

        attributed = ledger.strain_doses(2)
        assert attributed, "downstream target should have been dosed"
        assert set(attributed) == {(resident.strain_id, None)}

    def test_this_epoch_shedding_enters_the_zone_air_for_later_epochs(self) -> None:
        core = _core()
        shedder = _agent(1, "Cabin_A", infected=True)
        core._airborne_composition(PATHOGEN, {"Cabin_A": [(shedder, 100.0)]})
        contributors = core._reservoir.contributors(
            _key(AIRBORNE_RESERVOIR, "Cabin_A"),
        )
        assert contributors, "shedding should leave a composition behind"
        assert all(agent_id == 1 for _, agent_id in contributors)

    def test_environmental_reservoir_composition_tracks_its_scalar_mass(self) -> None:
        """Founder plus host deposits account for exactly the pool's mass."""
        profile = _env_profile()
        core = _core(pathogen_id=PATHOGEN, profile=profile, seed=11)
        shedder = _agent(1, "Medical_Bay", infected=True)
        target = _agent(2, "Medical_Bay")
        occupants = {"Medical_Bay": [shedder, target]}

        for _ in range(3):
            core._pathway_environmental(
                occupants, {}, ContactTracingMatrix(epoch=0), {},
                pathogen_id=PATHOGEN, profile=profile,
                ledger=StrainDoseLedger(),
            )

        scalar = core.env_contamination[PATHOGEN]["Medical_Bay"]
        composed = core._reservoir.total_mass(_key(ENV_RESERVOIR, "Medical_Bay"))
        assert scalar > 0.0
        assert composed == pytest.approx(scalar, rel=1e-9)

    def test_a_shedding_host_joins_the_reservoir_it_contaminates(self) -> None:
        profile = _env_profile()
        core = _core(pathogen_id=PATHOGEN, profile=profile, seed=11)
        shedder = _agent(1, "Medical_Bay", infected=True)
        core._pathway_environmental(
            {"Medical_Bay": [shedder]}, {}, ContactTracingMatrix(epoch=0), {},
            pathogen_id=PATHOGEN, profile=profile, ledger=StrainDoseLedger(),
        )
        contributors = core._reservoir.contributors(
            _key(ENV_RESERVOIR, "Medical_Bay"),
        )
        assert (None in {aid for _, aid in contributors}), "founder lineage expected"
        assert 1 in {aid for _, aid in contributors}, "host deposit expected"
        assert ENV_HOST_DEPOSITION_FRACTION > 0.0

    def test_untracked_runs_keep_the_scalar_reservoir_untouched(self) -> None:
        """With the flag off no host input is added and no composition is kept."""
        profile = _env_profile()
        core = _core(cfg=None, pathogen_id=PATHOGEN, profile=profile, seed=11)
        shedder = _agent(1, "Medical_Bay", infected=True)
        core._pathway_environmental(
            {"Medical_Bay": [shedder]}, {}, ContactTracingMatrix(epoch=0), {},
            pathogen_id=PATHOGEN, profile=profile, ledger=None,
        )
        assert core.env_contamination[PATHOGEN]["Medical_Bay"] == pytest.approx(
            100.0 * 0.9,
        )
        assert core._reservoir.keys() == ()


class TestUnresolvedMass:
    def test_an_unresolved_draw_names_no_parent(self) -> None:
        """Sub-floor pool mass is real dose, but not an attributable lineage."""
        core = _core()
        core._strain_doses = {
            5: {PATHOGEN: {(UNRESOLVED_STRAIN, None): 8.0}},
        }
        assert core._draw_source(5, PATHOGEN) == ("", None)

    def test_unresolved_mass_still_carries_dose(self) -> None:
        core = _core()
        registry = core.strain_registry
        assert registry is not None
        key = _key(SURFACE_RESERVOIR, "Cabin_A")
        core._reservoir.deposit(key, (registry.mint(PATHOGEN).strain_id, 1), 100.0)
        core._reservoir.deposit(key, (registry.mint(PATHOGEN).strain_id, 2), 1.0)
        core._reservoir.lump(0.05, key)
        mix = core._reservoir_mix(SURFACE_RESERVOIR, PATHOGEN, "Cabin_A")
        assert mix is not None
        assert mix.shares[(UNRESOLVED_STRAIN, None)] == pytest.approx(1 / 101)

    def test_an_unresolved_lineage_needs_no_registry_entry(self) -> None:
        core = _core()
        assert core._transmissibility(UNRESOLVED_STRAIN) == pytest.approx(1.0)

    def test_an_unresolved_superinfection_founds_a_nameable_lineage(self) -> None:
        """A co-resident has to be in the registry: the census looks it up.

        An acquisition drawn from a pool's sub-floor bin names no parent, and
        installing that as a resident keyed on the empty string crashed the
        per-epoch lineage census with ``unknown strain ''``. It founds its own
        lineage instead, which is what an unattributable acquisition is.
        """
        core = _core()
        registry = core.strain_registry
        assert registry is not None
        host = _agent(1, "Cabin_A", infected=True)
        resident = registry.mint(PATHOGEN)
        host.assign_strain(PATHOGEN, resident.strain_id, Phenotype.of(resident))

        assert core._establish(host, PATHOGEN, "", 1e4, 5, resident=True)

        strain_ids = set(host.resident_strains(PATHOGEN))
        assert "" not in strain_ids
        founded = strain_ids - {resident.strain_id}
        assert len(founded) == 1
        assert all(sid in registry for sid in strain_ids)
        census = registry.census(
            5, PATHOGEN, {sid: 1 for sid in strain_ids},
        )
        assert set(census.lineage_counts) == strain_ids


# ── Bounded state ──────────────────────────────────────────────────────

class TestBoundedState:
    def test_a_floor_bounds_a_pool_at_one_entry_per_resolvable_lineage(self) -> None:
        core = _core(profile=_norwalk_profile(min_strain_fraction=0.05))
        registry = core.strain_registry
        assert registry is not None
        agents = [_agent(i, "Cabin_A", infected=True) for i in range(40)]
        for agent in agents:
            strain = registry.mint(PATHOGEN)
            agent.assign_strain(PATHOGEN, strain.strain_id, Phenotype.of(strain))
        for _ in range(5):
            core._deposit_reservoir_strains(
                SURFACE_RESERVOIR, PATHOGEN, "Cabin_A",
                [(agent, 1.0) for agent in agents],
            )
        contributors = core._reservoir.contributors(
            _key(SURFACE_RESERVOIR, "Cabin_A"),
        )
        assert len(contributors) <= int(1.0 / 0.05) + 1

    @pytest.mark.timeout(300)
    def test_two_thousand_agents_stay_within_a_step_budget(self) -> None:
        """The composition is per pool, not per agent pair, so it must scale."""
        core = _core(profile=_norwalk_profile(min_strain_fraction=0.01), seed=17)
        agents = [
            _agent(i, ZONES[i % len(ZONES)], infected=i < 40)
            for i in range(2000)
        ]
        started = time.perf_counter()
        for epoch in range(3):
            core.execute_transmission(
                epoch=epoch,
                agents=agents,
                zone_pathogen_mass=dict.fromkeys(ZONES, 1e3),
                multi_pathogen_mass={PATHOGEN: dict.fromkeys(ZONES, 1e3)},
            )
        elapsed = (time.perf_counter() - started) / 3.0
        entries = sum(
            len(core._reservoir.contributors(key))
            for key in core._reservoir.keys()
        )
        assert elapsed < 20.0, f"step took {elapsed:.1f}s"
        assert entries <= 4 * len(ZONES) * (int(1.0 / 0.01) + 1)
