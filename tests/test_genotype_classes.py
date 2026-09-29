"""Genotype-class machinery: NORO-GENO-01 and the class-structure ruling.

The class — not the genotype — is the unit of declared strain difference
(docs/proposals/pathogen_class_structure_decision.md). Classes draw at the
founder, carry the split secretor gate (Kambhampati OR 9.9 vs 2.2 → 0.10 vs
0.45) and the declared transmissibility axis, and era-resolved share
declarations replace the unsourced uniform placeholder. These tests pin the
machinery — never the declared constants.
"""

from __future__ import annotations

import copy
import json
import types
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
    EmissionMix,
    StrainDoseLedger,
    single_strain_mix,
)
from engines.strain_state import (  # noqa: E402
    Phenotype,
    StrainConfigError,
    StrainEvolutionConfig,
)
from engines.transmission_core import TransmissionCore  # noqa: E402
from orchestrator_init import _seed_host_susceptibility  # noqa: E402
from tests.test_strain_dose_ledger import _with_shipped_droplet  # noqa: E402

PATHOGEN = "norwalk_gi"
VARIANT_CFG = {"variant_surveillance": {"enabled": True}}
ZONES = ["Cabin_A", "MainDining_L"]

GII4_REL = 0.10
NON_GII4_REL = 0.45
FLAT_REL = 0.2


def _classes(gii4_t: float = 1.0, non_gii4_t: float = 1.0) -> dict:
    return {
        "gii4": {
            "genotypes": ["GII.4"],
            "secretor_negative_relative_susceptibility": GII4_REL,
            "transmissibility_multiplier": gii4_t,
        },
        "non_gii4": {
            "genotypes": ["GII.17", "GII.2"],
            "secretor_negative_relative_susceptibility": NON_GII4_REL,
            "transmissibility_multiplier": non_gii4_t,
        },
    }


def _evolution(**overrides) -> dict:
    block = {
        "genotypes": ["GII.4", "GII.17", "GII.2"],
        "prior_genotype_distribution_by_era": {
            "pre": {"GII.4": 0.6, "GII.17": 0.15, "GII.2": 0.25},
            "post_2020": {"GII.4": 0.15, "GII.17": 0.75, "GII.2": 0.1},
        },
        "genotype_share_era": "pre",
        "genotype_classes": _classes(),
    }
    block.update(overrides)
    return block


def _profile_with(**evolution_overrides) -> dict:
    return {
        "pathogen_id": PATHOGEN,
        "strain_evolution": _evolution(**evolution_overrides),
    }


def _shipped_norwalk() -> dict:
    data = json.loads(
        (REPO_ROOT / "data/pathogens/active_profiles.json").read_text(),
    )
    return copy.deepcopy(
        next(p for p in data["pathogens"] if p["pathogen_id"] == PATHOGEN),
    )


def _agent(aid: int, loc: str = "MainDining_L", *, infected: bool = False) -> KorkinAgent:
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
        agent.infect_with_pathogen(PATHOGEN, 1e4, 0, time_infected=2)
    return agent


def _core(
    *,
    profile: dict | None = None,
    cfg: dict | None = VARIANT_CFG,
    seed: int = 7,
) -> TransmissionCore:
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes=dict.fromkeys(ZONES, 60.0),
        pathogen_profiles={PATHOGEN: profile or _shipped_norwalk()},
        zone_types={"Cabin_A": "Cabin_Corridor", "MainDining_L": "Dining"},
        cfg=_with_shipped_droplet(cfg),
    )
    core.initialize_zones(ZONES)
    return core


# ── Config parsing and era resolution ───────────────────────────────────

class TestClassConfigParsing:
    def test_class_of_and_offsets(self) -> None:
        cfg = StrainEvolutionConfig.from_profile(
            _profile_with(genotype_classes=_classes(gii4_t=2.5)),
        )
        assert cfg.class_of("GII.4").name == "gii4"
        assert cfg.class_of("GII.2").name == "non_gii4"
        assert cfg.class_of("GI.1") is None
        assert cfg.has_class_secretor_gate
        assert cfg.class_secretor_rel("GII.4") == pytest.approx(GII4_REL)
        assert cfg.class_secretor_rel("GII.17") == pytest.approx(NON_GII4_REL)

    def test_class_phenotype_carries_only_the_declared_axis(self) -> None:
        cfg = StrainEvolutionConfig.from_profile(
            _profile_with(genotype_classes=_classes(gii4_t=3.0)),
        )
        ph = cfg.class_phenotype("GII.4")
        assert ph.transmissibility_multiplier == pytest.approx(3.0)
        assert ph.shedding_multiplier == pytest.approx(1.0)
        assert ph.immune_escape == pytest.approx(0.0)
        # An unclaimed genotype mints the neutral phenotype.
        other = StrainEvolutionConfig.from_profile(_profile_with(
            genotype_classes={"gii4": {"genotypes": ["GII.4"]}},
        ))
        assert other.class_phenotype("GII.2") == Phenotype()

    def test_era_resolves_prior_and_explicit_wins(self) -> None:
        cfg = StrainEvolutionConfig.from_profile(_profile_with())
        assert cfg.prior_genotype_distribution == pytest.approx(
            {"GII.4": 0.6, "GII.17": 0.15, "GII.2": 0.25},
        )
        post = StrainEvolutionConfig.from_profile(
            _profile_with(genotype_share_era="post_2020"),
        )
        assert post.prior_genotype_distribution["GII.17"] == pytest.approx(0.75)
        # The explicit map is the sweep/override path and wins over the era.
        mono = StrainEvolutionConfig.from_profile(_profile_with(
            prior_genotype_distribution={"GII.4": 1.0},
        ))
        assert mono.prior_genotype_distribution == {"GII.4": 1.0}

    def test_multi_era_requires_a_selector(self) -> None:
        profile = _profile_with(genotype_share_era=None)
        with pytest.raises(StrainConfigError, match="genotype_share_era"):
            StrainEvolutionConfig.from_profile(profile)

    def test_single_era_needs_no_selector(self) -> None:
        cfg = StrainEvolutionConfig.from_profile(_profile_with(
            prior_genotype_distribution_by_era={
                "only": {"GII.4": 0.5, "GII.17": 0.5},
            },
            genotype_share_era=None,
        ))
        assert cfg.prior_genotype_distribution == pytest.approx(
            {"GII.4": 0.5, "GII.17": 0.5},
        )

    def test_unknown_era_name_rejected(self) -> None:
        profile = _profile_with(genotype_share_era="bronze_age")
        with pytest.raises(StrainConfigError, match="genotype_share_era"):
            StrainEvolutionConfig.from_profile(profile)

    def test_class_boundaries_cannot_overlap(self) -> None:
        profile = _profile_with(
            genotype_classes={
                "a": {"genotypes": ["GII.4", "GII.2"]},
                "b": {"genotypes": ["GII.2"]},
            },
        )
        with pytest.raises(StrainConfigError, match="both"):
            StrainEvolutionConfig.from_profile(profile)

    def test_class_must_claim_declared_genotypes(self) -> None:
        profile = _profile_with(
            genotype_classes={"alien": {"genotypes": ["GIX.0"]}},
        )
        with pytest.raises(StrainConfigError, match="unknown genotype"):
            StrainEvolutionConfig.from_profile(profile)


# ── Founder minting carries the class phenotype ──────────────────────────

class TestFounderClassPhenotype:
    def _profile(self, *, gii4_t: float) -> dict:
        profile = _shipped_norwalk()
        se = profile["strain_evolution"]
        se["genotype_classes"]["gii4"]["transmissibility_multiplier"] = gii4_t
        # Pin the founder draw to GII.4 through the sweep override path.
        se["prior_genotype_distribution"] = {"GII.4": 1.0}
        return profile

    def test_resident_founder_mints_class_phenotype(self) -> None:
        core = _core(profile=self._profile(gii4_t=2.5))
        agent = _agent(1, infected=True)
        strain_id = core._resident_strain_id(agent, PATHOGEN)
        assert strain_id is not None
        founder = core.strain_registry.get(strain_id)
        assert founder.genotype == "GII.4"
        assert founder.transmissibility_multiplier == pytest.approx(2.5)
        # The host carries the founder's lineage and offset, not a copy.
        assert agent.infections[PATHOGEN]["strain_id"] == strain_id

    def test_environmental_founder_mints_class_phenotype(self) -> None:
        core = _core(profile=self._profile(gii4_t=2.5))
        strain_id = core._environmental_strain_id(PATHOGEN)
        founder = core.strain_registry.get(strain_id)
        assert founder.transmissibility_multiplier == pytest.approx(2.5)

    def test_unclassed_profile_mints_neutral(self) -> None:
        profile = _shipped_norwalk()
        profile["strain_evolution"].pop("genotype_classes")
        profile["strain_evolution"]["prior_genotype_distribution"] = {
            "GII.4": 1.0,
        }
        core = _core(profile=profile)
        strain_id = core._resident_strain_id(_agent(1, infected=True), PATHOGEN)
        founder = core.strain_registry.get(strain_id)
        assert founder.transmissibility_multiplier == pytest.approx(1.0)


# ── The split secretor gate ──────────────────────────────────────────────

class TestClassSecretorGate:
    def _gate_core(self, *, profile: dict | None = None) -> TransmissionCore:
        return _core(profile=profile or _shipped_norwalk())

    def _ledger_for(
        self,
        core: TransmissionCore,
        agent_id: int,
        mixes: list[tuple[EmissionMix, float]],
        pathway: str = "direct_contact",
    ) -> StrainDoseLedger:
        ledger = StrainDoseLedger()
        for mix, dose in mixes:
            ledger.add(agent_id, pathway, dose, mix)
        return ledger

    def test_secretor_negative_reads_the_challenging_class(self) -> None:
        core = self._gate_core()
        gii4 = core.strain_registry.mint(PATHOGEN, genotype="GII.4")
        gii2 = core.strain_registry.mint(PATHOGEN, genotype="GII.2")
        host = _agent(9)
        host.secretor_negative_by_pathogen[PATHOGEN] = True

        gii4_ledger = self._ledger_for(
            core, 9, [(single_strain_mix(gii4.strain_id), 5.0)],
        )
        gii2_ledger = self._ledger_for(
            core, 9, [(single_strain_mix(gii2.strain_id), 5.0)],
        )
        assert core._class_gate_rel(
            host, PATHOGEN, gii4_ledger, {},
        ) == pytest.approx(GII4_REL)
        assert core._class_gate_rel(
            host, PATHOGEN, gii2_ledger, {},
        ) == pytest.approx(NON_GII4_REL)

    def test_mixed_challenge_is_dose_share_weighted(self) -> None:
        core = self._gate_core()
        gii4 = core.strain_registry.mint(PATHOGEN, genotype="GII.4")
        gii2 = core.strain_registry.mint(PATHOGEN, genotype="GII.2")
        host = _agent(9)
        host.secretor_negative_by_pathogen[PATHOGEN] = True
        mix = EmissionMix(
            shares={(gii4.strain_id, 1): 0.75, (gii2.strain_id, 2): 0.25},
            emission_factor=1.0,
        )
        ledger = self._ledger_for(core, 9, [(mix, 8.0)])
        assert core._class_gate_rel(
            host, PATHOGEN, ledger, {},
        ) == pytest.approx(0.75 * GII4_REL + 0.25 * NON_GII4_REL)

    def test_unresolved_or_untracked_challenge_falls_back_to_flat(self) -> None:
        core = self._gate_core()
        host = _agent(9)
        host.secretor_negative_by_pathogen[PATHOGEN] = True
        ledger = StrainDoseLedger()
        ledger.add(
            9, "direct_contact", 5.0,
            single_strain_mix(UNRESOLVED_STRAIN),
        )
        assert core._class_gate_rel(
            host, PATHOGEN, ledger, {},
        ) == pytest.approx(FLAT_REL)
        # No resolvable mix at all → flat as well.
        assert core._class_gate_rel(
            host, PATHOGEN, StrainDoseLedger(), {},
        ) == pytest.approx(FLAT_REL)
        assert core._class_gate_rel(host, PATHOGEN, None, None) == pytest.approx(
            FLAT_REL,
        )

    def test_no_gate_when_profile_declares_none(self) -> None:
        profile = _shipped_norwalk()
        profile["strain_evolution"].pop("genotype_classes")
        core = self._gate_core(profile=profile)
        host = _agent(9)
        host.secretor_negative_by_pathogen[PATHOGEN] = True
        assert core._class_gate_rel(host, PATHOGEN, None, None) is None

    def test_secretor_positive_hosts_are_untouched(self) -> None:
        core = self._gate_core()
        host = _agent(9)
        host.secretor_negative_by_pathogen[PATHOGEN] = False
        assert core._class_gate_rel(host, PATHOGEN, None, None) is None


# ── Init-time bake vs challenge-time gate ────────────────────────────────

class TestInitTimeGateSplit:
    def _seed(self, profile: dict, n_agents: int = 200, seed: int = 3):
        agents = [_agent(i) for i in range(n_agents)]
        engine = types.SimpleNamespace(agents=agents)
        _seed_host_susceptibility(
            engine, {PATHOGEN: profile}, np.random.default_rng(seed),
        )
        return agents

    def test_class_gate_defers_rel_to_challenge_time(self) -> None:
        """With a gate declared, init leaves susceptibility un-baked.

        The flag still draws — FUT2 status is a host trait — but the rel is
        applied per-exposure by challenge class, so nothing is multiplied at
        init.
        """
        agents = self._seed(_shipped_norwalk())
        drawn = [
            a for a in agents
            if a.secretor_negative_by_pathogen[PATHOGEN]
        ]
        assert drawn, "expected some secretor-negative draws"
        assert all(
            a.susceptibility_multiplier[PATHOGEN] == pytest.approx(1.0)
            for a in drawn
        )

    def test_flat_bake_is_the_labelled_baseline(self) -> None:
        """A profile with no class gate keeps the legacy init-time bake."""
        profile = _shipped_norwalk()
        profile["strain_evolution"].pop("genotype_classes")
        agents = self._seed(profile)
        drawn = [
            a for a in agents
            if a.secretor_negative_by_pathogen[PATHOGEN]
        ]
        assert drawn
        assert all(
            a.susceptibility_multiplier[PATHOGEN] == pytest.approx(FLAT_REL)
            for a in drawn
        )

    def test_flag_draws_are_not_perturbed_by_the_gate(self) -> None:
        """Same seed, same flag draws whether or not the gate is declared —
        the gate moves where rel lands, not who is non-secretor."""
        gated = self._seed(_shipped_norwalk())
        flat_profile = _shipped_norwalk()
        flat_profile["strain_evolution"].pop("genotype_classes")
        ungated = self._seed(flat_profile)
        assert [
            a.secretor_negative_by_pathogen[PATHOGEN] for a in gated
        ] == [
            a.secretor_negative_by_pathogen[PATHOGEN] for a in ungated
        ]


# ── End-to-end: the challenge carries the class factor ───────────────────

class TestChallengeTimeFold:
    def test_secretor_negative_dose_scaled_by_challenging_class(self) -> None:
        """The merged dose a non-secretor host receives is scaled by the
        challenging class's rel, and the strain shadow reads identically."""
        core = _core()
        gii4 = core.strain_registry.mint(PATHOGEN, genotype="GII.4")
        host = _agent(9)
        host.secretor_negative_by_pathogen[PATHOGEN] = True
        host.susceptibility_multiplier[PATHOGEN] = 1.0  # gate skipped the bake

        ledger = StrainDoseLedger()
        ledger.add(
            9, "direct_contact", 5.0,
            single_strain_mix(gii4.strain_id, source_agent_id=1),
        )
        agent_doses: dict[int, float] = {}
        agent_pathogen_doses: dict[int, dict[str, float]] = {}
        susc = core._merge_pathogen_doses(
            [host], PATHOGEN, {9: 5.0}, agent_doses, agent_pathogen_doses,
            ledger=ledger, weights={}, npi=None,
        )
        assert susc[9] == pytest.approx(GII4_REL)
        assert agent_doses[9] == pytest.approx(5.0 * GII4_REL)

        core._fold_strain_doses(PATHOGEN, ledger, {}, susc)
        shadow = core._strain_doses[9][PATHOGEN]
        assert shadow[(gii4.strain_id, 1)] == pytest.approx(5.0 * GII4_REL)
