"""Immune history and genotype-specific protection (Paper 3 PR 5).

Before this, a host's prior exposure was whatever strain its *current* infection
record still named: one genotype, lost as soon as the registry collected the
lineage, and blind to a host that has resolved two of them. These tests hold the
history to what a serology or reinfection analysis would need — one record per
resolved lineage, self-contained, and protection scored against the best match —
plus the legacy behaviour with variant surveillance off.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

from engines.infection_dynamics_bridge import (  # noqa: E402
    InfectionStatus,
    KorkinAgent,
)
from engines.strain_state import (  # noqa: E402
    IMMUNITY_AT_EMBARKATION,
    IMMUNITY_FROM_INFECTION,
    ImmuneRecord,
    Phenotype,
    StrainConfigError,
    StrainRegistry,
)
from engines.transmission_core import TransmissionCore  # noqa: E402
from orchestrator_epoch import (  # noqa: E402
    _advance_agent_pathogen_infections,
)
from tools.sanity_checker import (  # noqa: E402
    PathogenProfile,
    Report,
    _warn_cross_immunity_shape,
)

PATHOGEN = "norwalk_gi"
VARIANT_CFG = {"variant_surveillance": {"enabled": True}}
ZONES = ["Cabin_A", "MainDining_L"]
GENOTYPES = ("GII.4", "GII.17", "GII.2")
# Hourly epochs past norovirus's 56-day refractory window, where protection is
# genotype-specific again rather than non-specifically fresh.
PAST_REFRACTORY = 24 * 60


def _norwalk_profile(**overrides: object) -> dict:
    data = json.loads(
        (REPO_ROOT / "data/pathogens/active_profiles.json").read_text(),
    )
    profile = next(
        p for p in data["pathogens"] if p["pathogen_id"] == PATHOGEN
    )
    return {**copy.deepcopy(profile), **overrides}


def _agent(aid: int = 1, *, immune: bool = False) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=aid,
        role="passenger",
        immune=immune,
        home_zone="MainDining_L",
        dining_zone="MainDining_L",
        work_zone="MainDining_L",
        free_zone="MainDining_L",
        schedule=["Free"] * 24,
    )
    agent.current_location = "MainDining_L"
    return agent


def _core(*, cfg: dict | None = VARIANT_CFG, seed: int = 5) -> TransmissionCore:
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes=dict.fromkeys(ZONES, 60.0),
        pathogen_profiles={PATHOGEN: _norwalk_profile()},
        zone_types={"Cabin_A": "Cabin_Corridor", "MainDining_L": "Dining"},
        cfg=cfg,
    )
    core.initialize_zones(ZONES)
    return core


def _registry(core: TransmissionCore) -> StrainRegistry:
    registry = core.strain_registry
    assert registry is not None
    return registry


def _resolve(
    agent: KorkinAgent,
    registry: StrainRegistry | None,
    *,
    epoch: int = 3,
    recovery_day: int = 1,
) -> None:
    """Run the progression seam far enough for every resident lineage to clear."""
    profile = _norwalk_profile(recovery_day=recovery_day)
    _advance_agent_pathogen_infections(
        agent, {PATHOGEN: profile}, np.random.default_rng(1), registry, epoch,
    )


def _infect(
    agent: KorkinAgent,
    registry: StrainRegistry,
    genotype: str,
    *,
    escape: float = 0.0,
) -> str:
    strain = registry.mint(
        PATHOGEN, genotype=genotype, phenotype=Phenotype(immune_escape=escape),
    )
    agent.infect_with_pathogen(
        PATHOGEN, 1e4, 0,
        strain_id=strain.strain_id,
        strain_phenotype=Phenotype.of(strain),
    )
    return strain.strain_id


def _challenge(
    core: TransmissionCore,
    agent: KorkinAgent,
    genotype: str,
    *,
    escape: float = 0.0,
    epoch: int = 0,
) -> float:
    """Protection against a single fresh strain of *genotype* at *epoch*.

    ``epoch`` matters because protection is now matched *and* aged: inside a
    pathogen's refractory window short-term protection is deliberately
    non-specific, so genotype specificity is read past that window
    (``PAST_REFRACTORY``). See ``tests/test_immune_waning.py``.
    """
    strain = _registry(core).mint(
        PATHOGEN, genotype=genotype, phenotype=Phenotype(immune_escape=escape),
    )
    core._strain_doses = {
        agent.agent_id: {PATHOGEN: {(strain.strain_id, 0): 100.0}},
    }
    return core._challenge_protection(agent, PATHOGEN, epoch)


# ── Recording at the recovery seam ──────────────────────────────────────

class TestRecordingImmunity:
    def test_resolved_infection_leaves_one_record(self) -> None:
        core = _core()
        registry = _registry(core)
        agent = _agent()
        strain_id = _infect(agent, registry, GENOTYPES[0], escape=0.2)
        _resolve(agent, registry, epoch=7)

        assert agent.infections[PATHOGEN]["status"] == InfectionStatus.RECOVERED
        assert len(agent.immune_history) == 1
        record = agent.immune_history[0]
        assert record.pathogen_id == PATHOGEN
        assert record.genotype == GENOTYPES[0]
        assert record.strain_id == strain_id
        assert record.epoch == 7
        assert record.immune_escape == pytest.approx(0.2)
        assert record.origin == IMMUNITY_FROM_INFECTION

    def test_coinfected_host_remembers_every_lineage(self) -> None:
        """Two co-resident genotypes resolve into two records, not one."""
        core = _core()
        registry = _registry(core)
        agent = _agent()
        _infect(agent, registry, GENOTYPES[0])
        second = registry.mint(PATHOGEN, genotype=GENOTYPES[1])
        agent.superinfect_with_strain(
            PATHOGEN, second.strain_id, 1e4, 0,
            phenotype=Phenotype.of(second),
        )
        _resolve(agent, registry)

        assert len(agent.immune_history) == 2
        assert set(agent.immune_genotypes(PATHOGEN)) == {
            GENOTYPES[0], GENOTYPES[1],
        }

    def test_lineages_clearing_on_different_days_record_separately(self) -> None:
        """A late superinfection is recorded when it clears, not with the first."""
        core = _core()
        registry = _registry(core)
        agent = _agent()
        _infect(agent, registry, GENOTYPES[0])
        late = registry.mint(PATHOGEN, genotype=GENOTYPES[1])
        agent.superinfect_with_strain(
            PATHOGEN, late.strain_id, 1e4, 0, phenotype=Phenotype.of(late),
        )
        agent.resident_strains(PATHOGEN)[late.strain_id].time_infected = -1

        _resolve(agent, registry, epoch=4, recovery_day=1)
        assert [r.genotype for r in agent.immune_history] == [GENOTYPES[0]]
        assert agent.infections[PATHOGEN]["status"] == InfectionStatus.INFECTED

        _resolve(agent, registry, epoch=9, recovery_day=1)
        assert [r.genotype for r in agent.immune_history] == [
            GENOTYPES[0], GENOTYPES[1],
        ]
        assert agent.immune_history[-1].epoch == 9

    def test_untracked_infection_records_nothing(self) -> None:
        """Flag off: the recovery seam is the legacy one, history stays empty."""
        agent = _agent()
        agent.infect_with_pathogen(PATHOGEN, 1e4, 0)
        _resolve(agent, None)
        assert agent.infections[PATHOGEN]["status"] == InfectionStatus.RECOVERED
        assert agent.immune_history == []

    def test_history_grows_only_with_resolved_exposures(self) -> None:
        """Repeated progression of one infection does not append per epoch."""
        core = _core()
        registry = _registry(core)
        agent = _agent()
        _infect(agent, registry, GENOTYPES[0])
        for epoch in range(6):
            _resolve(agent, registry, epoch=epoch, recovery_day=3)
        assert len(agent.immune_history) == 1

    def test_cleared_ids_are_reported_without_changing_the_count(self) -> None:
        core = _core()
        registry = _registry(core)
        agent = _agent()
        strain_id = _infect(agent, registry, GENOTYPES[0])
        cleared: list[str] = []
        left = agent.advance_resident_strains(PATHOGEN, 1, cleared)
        assert left == 0
        assert cleared == [strain_id]

    def test_repeat_exposure_appends_a_record_per_exposure(self) -> None:
        core = _core()
        registry = _registry(core)
        agent = _agent()
        _infect(agent, registry, GENOTYPES[0])
        _resolve(agent, registry, epoch=2)
        _infect(agent, registry, GENOTYPES[0])
        _resolve(agent, registry, epoch=8)
        assert len(agent.immune_history) == 2
        assert agent.immune_genotypes(PATHOGEN) == (GENOTYPES[0],)


# ── Protection at exposure ──────────────────────────────────────────────

class TestProtectionFromHistory:
    def test_homologous_rechallenge_is_more_protected_than_cross(self) -> None:
        core = _core()
        registry = _registry(core)
        agent = _agent()
        _infect(agent, registry, GENOTYPES[0])
        _resolve(agent, registry)

        homologous = _challenge(core, agent, GENOTYPES[0], epoch=PAST_REFRACTORY)
        heterologous = _challenge(core, agent, GENOTYPES[1], epoch=PAST_REFRACTORY)
        assert homologous > heterologous
        assert 0.0 < heterologous < homologous <= 1.0

    def test_history_survives_the_lineage_being_collected(self) -> None:
        """Protection outlives the strain, which is why records are snapshots."""
        core = _core()
        registry = _registry(core)
        agent = _agent()
        strain_id = _infect(agent, registry, GENOTYPES[0])
        _resolve(agent, registry)

        registry.collect([])
        assert strain_id not in registry
        assert core._prior_genotypes(agent, PATHOGEN) == (GENOTYPES[0],)
        assert _challenge(core, agent, GENOTYPES[0]) > 0.0

    def test_escape_grades_protection_down_monotonically(self) -> None:
        core = _core()
        registry = _registry(core)
        agent = _agent()
        _infect(agent, registry, GENOTYPES[0])
        _resolve(agent, registry)

        protections = [
            _challenge(core, agent, GENOTYPES[0], escape=escape)
            for escape in (0.0, 0.25, 0.5, 0.75, 1.0)
        ]
        assert protections == sorted(protections, reverse=True)
        assert protections[0] > protections[-1]
        assert protections[-1] == pytest.approx(0.0)
        assert all(0.0 <= p <= 1.0 for p in protections)

    def test_two_resolved_genotypes_are_scored_on_the_best_match(self) -> None:
        core = _core()
        registry = _registry(core)
        one = _agent(1)
        _infect(one, registry, GENOTYPES[1])
        _resolve(one, registry)
        both = _agent(2)
        _infect(both, registry, GENOTYPES[1])
        _resolve(both, registry)
        _infect(both, registry, GENOTYPES[0])
        _resolve(both, registry, epoch=9)

        cross_only = _challenge(core, one, GENOTYPES[0], epoch=PAST_REFRACTORY)
        matched = _challenge(core, both, GENOTYPES[0], epoch=PAST_REFRACTORY)
        homologous_only = _agent(3)
        _infect(homologous_only, registry, GENOTYPES[0])
        _resolve(homologous_only, registry)

        assert matched > cross_only
        assert matched == pytest.approx(
            _challenge(core, homologous_only, GENOTYPES[0], epoch=PAST_REFRACTORY),
            abs=1e-3,
        )

    def test_repeat_exposures_do_not_stack_protection(self) -> None:
        core = _core()
        registry = _registry(core)
        once = _agent(1)
        _infect(once, registry, GENOTYPES[0])
        _resolve(once, registry)
        twice = _agent(2)
        _infect(twice, registry, GENOTYPES[0])
        _resolve(twice, registry)
        _infect(twice, registry, GENOTYPES[0])
        _resolve(twice, registry, epoch=9)

        assert len(twice.immune_history) == 2
        assert _challenge(core, twice, GENOTYPES[1]) == pytest.approx(
            _challenge(core, once, GENOTYPES[1]),
        )

    def test_resident_lineage_still_counts_as_a_prior(self) -> None:
        """An ongoing infection interferes before it has cleared."""
        core = _core()
        registry = _registry(core)
        agent = _agent()
        _infect(agent, registry, GENOTYPES[0])
        assert core._prior_genotypes(agent, PATHOGEN) == (GENOTYPES[0],)

    def test_embarkation_immunity_is_recorded_as_such(self) -> None:
        core = _core()
        agent = _agent(11, immune=True)
        priors = core._prior_genotypes(agent, PATHOGEN)
        assert len(priors) == 1
        assert len(agent.immune_history) == 1
        record = agent.immune_history[0]
        assert record.origin == IMMUNITY_AT_EMBARKATION
        assert record.genotype == priors[0]
        assert record.epoch == 0
        assert core._prior_genotypes(agent, PATHOGEN) == priors
        assert len(agent.immune_history) == 1

    def test_naive_host_has_no_history_and_no_protection(self) -> None:
        core = _core()
        agent = _agent()
        assert core._prior_genotypes(agent, PATHOGEN) == ()
        assert _challenge(core, agent, GENOTYPES[0]) == pytest.approx(0.0)

    def test_flag_off_keeps_immunity_absolute_and_history_empty(self) -> None:
        core = _core(cfg=None)
        immune = _agent(3, immune=True)
        susceptible = _agent(4)
        assert core._prior_genotypes(immune, PATHOGEN) == ()
        assert core._challenge_protection(immune, PATHOGEN) == pytest.approx(1.0)
        assert core._challenge_protection(susceptible, PATHOGEN) == pytest.approx(
            0.0,
        )
        assert immune.immune_history == []


# ── Record semantics ────────────────────────────────────────────────────

class TestImmuneRecord:
    def test_distinct_genotypes_keep_first_seen_order(self) -> None:
        agent = _agent()
        for genotype in (GENOTYPES[1], GENOTYPES[0], GENOTYPES[1]):
            agent.record_immunity(
                ImmuneRecord(pathogen_id=PATHOGEN, genotype=genotype),
            )
        agent.record_immunity(ImmuneRecord(pathogen_id="other", genotype="x"))
        assert agent.immune_genotypes(PATHOGEN) == (GENOTYPES[1], GENOTYPES[0])
        assert agent.immune_genotypes("other") == ("x",)

    def test_unnamed_genotype_is_not_a_prior(self) -> None:
        """A lineage with no genotype gives nothing for a matrix to match on."""
        agent = _agent()
        agent.record_immunity(ImmuneRecord(pathogen_id=PATHOGEN, genotype=""))
        assert agent.immune_genotypes(PATHOGEN) == ()

    def test_telemetry_round_trips_the_fields(self) -> None:
        record = ImmuneRecord(
            pathogen_id=PATHOGEN, genotype=GENOTYPES[0], strain_id="s:1",
            epoch=12, immune_escape=0.3,
        )
        assert record.to_telemetry() == {
            "pathogen_id": PATHOGEN,
            "genotype": GENOTYPES[0],
            "strain_id": "s:1",
            "epoch": 12,
            "immune_escape": 0.3,
            "origin": IMMUNITY_FROM_INFECTION,
        }

    def test_invalid_records_are_rejected(self) -> None:
        with pytest.raises(StrainConfigError):
            ImmuneRecord(pathogen_id="", genotype=GENOTYPES[0])
        with pytest.raises(StrainConfigError):
            ImmuneRecord(
                pathogen_id=PATHOGEN, genotype=GENOTYPES[0], origin="wishful",
            )
        with pytest.raises(StrainConfigError):
            ImmuneRecord(
                pathogen_id=PATHOGEN, genotype=GENOTYPES[0], immune_escape=1.5,
            )


# ── Cross-immunity matrix validation ────────────────────────────────────

def _profile_with_matrix(matrix: dict[str, dict[str, float]]) -> PathogenProfile:
    profile = _norwalk_profile()
    profile["strain_evolution"] = {
        **profile["strain_evolution"], "cross_immunity": matrix,
    }
    return PathogenProfile(**profile)


class TestCrossImmunityShapeChecks:
    def test_shipped_matrix_is_clean(self) -> None:
        report = Report()
        _warn_cross_immunity_shape(
            PathogenProfile(**_norwalk_profile()), report,
        )
        assert report.warnings == []

    def test_missing_row_warns(self) -> None:
        report = Report()
        _warn_cross_immunity_shape(
            _profile_with_matrix({GENOTYPES[0]: {GENOTYPES[0]: 0.85}}), report,
        )
        assert len(report.warnings) == 2
        assert all("no row for genotype" in f.message for f in report.warnings)

    def test_row_protecting_others_better_than_itself_warns(self) -> None:
        report = Report()
        _warn_cross_immunity_shape(
            _profile_with_matrix({
                g: {other: 0.9 if other != g else 0.2 for other in GENOTYPES}
                for g in GENOTYPES
            }),
            report,
        )
        assert len(report.warnings) == len(GENOTYPES)
        assert all("against itself" in f.message for f in report.warnings)
