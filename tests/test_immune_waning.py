"""Per-pathogen immune waning, and the legacy fields as a record projection.

Protection used to be one number: the ``cross_immunity`` entry, applied as a
per-epoch susceptibility multiplier. A homologous 0.85 therefore left a recovered
host 15% susceptible *every hour* of continuous shipboard dose, so at the Paper 1
operating point every infected host was re-infected as fast as its previous
episode cleared (3 episodes for 318 of 368 hosts over 200 epochs, the physical
maximum). That reads a multi-year hazard ratio as an instantaneous rate — the
same category error as the epoch/day bug.

These tests hold the replacement to its contract: how *well matched* an exposure
is (``cross_immunity``) and how *fresh* it is (``immune_waning``) are separate,
the freshness term is per-pathogen and measured in days of natural history
through the run's clock, so a week-long voyage sees stiff protection and a
year-long deployment sees genuine loss of it.
"""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

from engines.infection_dynamics_bridge import (  # noqa: E402
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
)
from engines.sim_clock import HOURS, LEGACY_EPOCH_DAY, SimClock  # noqa: E402
from engines.strain_state import (  # noqa: E402
    IMMUNITY_AT_EMBARKATION,
    ImmuneRecord,
    ImmuneWaningConfig,
    Phenotype,
    StrainConfigError,
    StrainEvolutionConfig,
    StrainRegistry,
    StrainState,
)
from engines.strain_dose_ledger import UNRESOLVED_STRAIN  # noqa: E402
from engines.transmission_core import TransmissionCore  # noqa: E402
from orchestrator_epoch import (  # noqa: E402
    _advance_agent_pathogen_infections,
    _project_legacy_illness,
)

PATHOGEN = "norwalk_gi"
SARS = "sars_cov2_resp"
VARIANT_CFG = {"variant_surveillance": {"enabled": True}}
ZONES = ["Cabin_A", "MainDining_L"]
GENOTYPES = ("GII.4", "GII.17", "GII.2")
HOMOLOGOUS = 0.85
HETEROLOGOUS = 0.18
VOYAGE_DAYS = 8.0
YEAR_DAYS = 365.0


def _profile(pathogen_id: str = PATHOGEN, **overrides: object) -> dict:
    data = json.loads(
        (REPO_ROOT / "data/pathogens/active_profiles.json").read_text(),
    )
    profile = next(
        p for p in data["pathogens"] if p["pathogen_id"] == pathogen_id
    )
    return {**copy.deepcopy(profile), **overrides}


def _config(pathogen_id: str = PATHOGEN, **overrides: object) -> StrainEvolutionConfig:
    return StrainEvolutionConfig.from_profile(_profile(pathogen_id, **overrides))


def _strain(genotype: str, *, escape: float = 0.0) -> StrainState:
    return StrainState(
        strain_id="s1",
        pathogen_id=PATHOGEN,
        genotype=genotype,
        immune_escape=escape,
    )


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


def _core(
    *,
    profiles: dict[str, dict] | None = None,
    seed: int = 5,
    clock: SimClock | None = None,
) -> TransmissionCore:
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes=dict.fromkeys(ZONES, 60.0),
        pathogen_profiles=profiles or {PATHOGEN: _profile()},
        zone_types={"Cabin_A": "Cabin_Corridor", "MainDining_L": "Dining"},
        cfg=VARIANT_CFG,
        clock=clock or SimClock(epoch_duration_hours=1.0, mode=HOURS),
    )
    core.initialize_zones(ZONES)
    return core


def _recovered(
    agent: KorkinAgent, genotype: str, *, epoch: int = 0, escape: float = 0.0,
) -> None:
    """Give the host one resolved exposure to *genotype*, recorded at *epoch*."""
    agent.record_immunity(ImmuneRecord(
        pathogen_id=PATHOGEN,
        genotype=genotype,
        strain_id=f"resolved-{genotype}",
        epoch=epoch,
        immune_escape=escape,
    ))


def _challenge(
    core: TransmissionCore,
    agent: KorkinAgent,
    genotype: str,
    *,
    epoch: int,
    escape: float = 0.0,
) -> float:
    """Protection against one fresh strain of *genotype* at *epoch*."""
    registry = core.strain_registry
    assert registry is not None
    strain = registry.mint(
        PATHOGEN, genotype=genotype, phenotype=Phenotype(immune_escape=escape),
    )
    core._strain_doses = {
        agent.agent_id: {PATHOGEN: {(strain.strain_id, 0): 100.0}},
    }
    return core._challenge_protection(agent, PATHOGEN, epoch)


# ── The waning kernel ───────────────────────────────────────────────────

class TestWaningKernel:
    """``ImmuneWaningConfig.protection_at`` on its own, in days."""

    def test_absent_block_leaves_matched_protection_untouched(self) -> None:
        """The default is the pre-existing behaviour: no window, no decay."""
        waning = ImmuneWaningConfig()
        assert not waning.active
        for days in (0.0, 8.0, YEAR_DAYS, 10 * YEAR_DAYS):
            assert waning.protection_at(HOMOLOGOUS, days) == pytest.approx(
                HOMOLOGOUS,
            )

    def test_zero_elapsed_time_is_inside_the_window(self) -> None:
        """A host that recovered this epoch is protected, not re-challengeable."""
        waning = ImmuneWaningConfig(
            refractory_days=56.0, refractory_protection=0.98,
            half_life_days=1095.0,
        )
        assert waning.protection_at(HETEROLOGOUS, 0.0) == pytest.approx(0.98)

    def test_refractory_boundary_is_inclusive_and_continuous(self) -> None:
        """Protection at the window's edge equals the window, then decays."""
        waning = ImmuneWaningConfig(
            refractory_days=56.0, refractory_protection=0.98,
            half_life_days=100.0,
        )
        assert waning.protection_at(HOMOLOGOUS, 56.0) == pytest.approx(0.98)
        just_after = waning.protection_at(HOMOLOGOUS, 56.0 + 1e-9)
        assert just_after == pytest.approx(HOMOLOGOUS, abs=1e-6)
        assert just_after < 0.98

    def test_decay_is_monotone_over_five_ages(self) -> None:
        """More time since recovery is never more protection."""
        waning = ImmuneWaningConfig(
            refractory_days=56.0, refractory_protection=0.98,
            half_life_days=365.0,
        )
        ages = [56.0, 120.0, 365.0, 730.0, 3650.0]
        values = [waning.protection_at(HOMOLOGOUS, d) for d in ages]
        assert all(
            later < earlier for earlier, later in zip(values, values[1:])
        )
        assert values[0] > 0.9
        assert values[-1] < 0.05

    def test_half_life_halves_the_matched_protection(self) -> None:
        """The named parameter means what it says, measured from the window."""
        waning = ImmuneWaningConfig(refractory_days=10.0, half_life_days=100.0)
        assert waning.protection_at(0.8, 110.0) == pytest.approx(0.4)
        assert waning.protection_at(0.8, 210.0) == pytest.approx(0.2)

    def test_residual_protection_is_the_floor_and_never_exceeds_the_match(
        self,
    ) -> None:
        waning = ImmuneWaningConfig(
            half_life_days=30.0, residual_protection=0.2,
        )
        assert waning.protection_at(0.9, 10 * YEAR_DAYS) == pytest.approx(
            0.2, abs=1e-6,
        )
        # A poorly matched prior cannot be *raised* to the floor.
        assert waning.protection_at(0.05, 10 * YEAR_DAYS) == pytest.approx(
            0.05, abs=1e-6,
        )

    def test_escape_breaches_the_refractory_window_in_proportion(self) -> None:
        """A novel variant is not stopped by a window earned against another."""
        waning = ImmuneWaningConfig(
            refractory_days=56.0, refractory_protection=1.0,
        )
        full = waning.protection_at(0.0, 1.0, 0.0)
        half = waning.protection_at(0.0, 1.0, 0.5)
        none = waning.protection_at(0.0, 1.0, 1.0)
        assert full == pytest.approx(1.0)
        assert half == pytest.approx(0.5)
        assert none == pytest.approx(0.0)

    @pytest.mark.parametrize("days", [0.0, 1.0, 56.0, 400.0, 1e6])
    @pytest.mark.parametrize("matched", [0.0, 0.18, 0.85, 1.0])
    def test_output_is_a_finite_probability(
        self, matched: float, days: float,
    ) -> None:
        waning = ImmuneWaningConfig(
            refractory_days=56.0, refractory_protection=0.98,
            half_life_days=1095.0, residual_protection=0.05,
        )
        value = waning.protection_at(matched, days)
        assert math.isfinite(value)
        assert 0.0 <= value <= 1.0

    def test_negative_age_is_treated_as_the_present(self) -> None:
        waning = ImmuneWaningConfig(refractory_days=1.0, refractory_protection=1.0)
        assert waning.protection_at(0.1, -5.0) == pytest.approx(1.0)

    @pytest.mark.parametrize(
        "block",
        [
            {"refractory_days": -1.0},
            {"half_life_days": -0.5},
            {"refractory_days": float("nan")},
            {"half_life_days": float("inf")},
            {"refractory_protection": 1.5},
            {"residual_protection": -0.1},
        ],
    )
    def test_invalid_blocks_are_refused_at_load(self, block: dict) -> None:
        with pytest.raises(StrainConfigError):
            ImmuneWaningConfig.from_config(block)

    def test_non_object_block_is_refused(self) -> None:
        with pytest.raises(StrainConfigError):
            ImmuneWaningConfig.from_config([56.0])  # type: ignore[arg-type]

    def test_partial_block_keeps_the_defaults_for_the_rest(self) -> None:
        waning = ImmuneWaningConfig.from_config({"refractory_days": 14.0})
        assert waning.refractory_days == pytest.approx(14.0)
        assert waning.refractory_protection == pytest.approx(1.0)
        assert waning.half_life_days == pytest.approx(0.0)


# ── The profiles that carry it ──────────────────────────────────────────

class TestProfileContract:
    def test_shipped_profiles_declare_a_window_wider_than_a_voyage(self) -> None:
        """Every strain-structured pathogen has to answer the re-infection question."""
        data = json.loads(
            (REPO_ROOT / "data/pathogens/active_profiles.json").read_text(),
        )
        configs = [
            StrainEvolutionConfig.from_profile(p) for p in data["pathogens"]
        ]
        structured = [c for c in configs if c is not None]
        assert structured
        for cfg in structured:
            assert cfg.immune_waning.active, cfg.pathogen_id
            assert cfg.immune_waning.refractory_days > VOYAGE_DAYS

    def test_pathogens_wane_at_their_own_rates(self) -> None:
        """Not a global constant: norovirus outlasts SARS-CoV-2 by construction."""
        noro = _config().immune_waning
        sars = _config(SARS).immune_waning
        assert sars.refractory_days != noro.refractory_days
        at_a_year = (
            noro.protection_at(HOMOLOGOUS, YEAR_DAYS),
            sars.protection_at(0.8, YEAR_DAYS),
        )
        assert at_a_year[0] > at_a_year[1] + 0.2

    def test_a_year_costs_protection_that_a_voyage_does_not(self) -> None:
        """The requirement in one assertion, per pathogen."""
        for pathogen, matched in ((PATHOGEN, HOMOLOGOUS), (SARS, 0.8)):
            waning = _config(pathogen).immune_waning
            voyage = waning.protection_at(matched, VOYAGE_DAYS)
            year = waning.protection_at(matched, YEAR_DAYS)
            assert voyage > 0.9, pathogen
            assert year < voyage - 0.2, pathogen

    def test_waning_does_not_disturb_the_matched_value_it_ages(self) -> None:
        """Negative control: the cross-immunity matrix still sets the level."""
        cfg = _config()
        homologous = cfg.waned_protection(
            GENOTYPES[0], _strain(GENOTYPES[0]), YEAR_DAYS,
        )
        heterologous = cfg.waned_protection(
            GENOTYPES[0], _strain(GENOTYPES[1]), YEAR_DAYS,
        )
        assert homologous > heterologous

    def test_an_unrelated_parameter_does_not_move_protection(self) -> None:
        """Negative control: mutation rate is not an immunity dial."""
        base = _config()
        profile = _profile()
        profile["strain_evolution"] = {
            **profile["strain_evolution"], "mutation_rate": 0.5,
        }
        mutated = StrainEvolutionConfig.from_profile(profile)
        assert mutated is not None
        for days in (0.0, 30.0, YEAR_DAYS):
            assert mutated.waned_protection(
                GENOTYPES[0], _strain(GENOTYPES[0]), days,
            ) == pytest.approx(
                base.waned_protection(
                    GENOTYPES[0], _strain(GENOTYPES[0]), days,
                ),
            )


class TestMatchedProtectionAges:
    """``StrainEvolutionConfig.waned_protection`` — match and freshness together."""

    def test_a_resident_lineage_is_interference_not_memory(self) -> None:
        """``None`` age keeps the declared value, with no refractory window."""
        cfg = _config()
        assert cfg.waned_protection(
            GENOTYPES[0], _strain(GENOTYPES[1]), None,
        ) == pytest.approx(HETEROLOGOUS)

    def test_homologous_outlasts_heterologous_after_the_window(self) -> None:
        cfg = _config()
        age = cfg.immune_waning.refractory_days + 1.0
        homologous = cfg.waned_protection(GENOTYPES[0], _strain(GENOTYPES[0]), age)
        heterologous = cfg.waned_protection(GENOTYPES[0], _strain(GENOTYPES[1]), age)
        assert homologous == pytest.approx(HOMOLOGOUS, abs=1e-3)
        assert heterologous == pytest.approx(HETEROLOGOUS, abs=1e-3)

    def test_inside_the_window_the_two_are_deliberately_alike(self) -> None:
        """Short-term protection is non-specific; that is the point of it."""
        cfg = _config()
        homologous = cfg.waned_protection(GENOTYPES[0], _strain(GENOTYPES[0]), 1.0)
        heterologous = cfg.waned_protection(GENOTYPES[0], _strain(GENOTYPES[1]), 1.0)
        assert homologous == pytest.approx(heterologous)
        assert heterologous > HETEROLOGOUS + 0.5


# ── Ageing on the run's clock ───────────────────────────────────────────

class TestClockConversion:
    def test_a_voyage_of_epochs_is_days_through_the_clock(self) -> None:
        """168 hourly epochs is a week of immunity, not a season of it."""
        core = _core()
        agent = _agent()
        _recovered(agent, GENOTYPES[0], epoch=0)
        ages = core._resolved_exposure_ages(agent, PATHOGEN, 168)
        assert ages[GENOTYPES[0]] == pytest.approx(7.0)

    def test_the_legacy_arm_reads_the_same_epochs_as_days(self) -> None:
        """The control arm keeps its own clock, so the comparison stays paired."""
        core = _core(clock=SimClock(mode=LEGACY_EPOCH_DAY))
        agent = _agent()
        _recovered(agent, GENOTYPES[0], epoch=0)
        ages = core._resolved_exposure_ages(agent, PATHOGEN, 168)
        assert ages[GENOTYPES[0]] == pytest.approx(168.0)

    def test_the_most_recent_exposure_to_a_genotype_wins(self) -> None:
        core = _core()
        agent = _agent()
        _recovered(agent, GENOTYPES[0], epoch=24)
        _recovered(agent, GENOTYPES[0], epoch=240)
        ages = core._resolved_exposure_ages(agent, PATHOGEN, 480)
        assert ages[GENOTYPES[0]] == pytest.approx(10.0)

    def test_an_embarkation_prior_is_ageless_rather_than_freshly_recovered(
        self,
    ) -> None:
        """Standing immunity was raised before the voyage, so it gets no window."""
        core = _core()
        agent = _agent(immune=True)
        protection = _challenge(core, agent, GENOTYPES[0], epoch=1)
        assert core._resolved_exposure_ages(agent, PATHOGEN, 1) == {}
        assert [r.origin for r in agent.immune_history] == [
            IMMUNITY_AT_EMBARKATION,
        ]
        assert protection <= HOMOLOGOUS + 1e-9

    def test_a_recovered_host_is_protected_for_the_rest_of_the_voyage(self) -> None:
        """The behaviour that was wrong: protection at every hour of a week."""
        core = _core()
        agent = _agent()
        _recovered(agent, GENOTYPES[0], epoch=72)
        for epoch in (73, 100, 168, 200):
            assert _challenge(
                core, agent, GENOTYPES[1], epoch=epoch,
            ) > 0.9, epoch

    def test_the_same_host_is_challengeable_a_year_later(self) -> None:
        """Same parameters, longer deployment: immunity is genuinely lost."""
        core = _core()
        agent = _agent()
        _recovered(agent, GENOTYPES[0], epoch=0)
        voyage = _challenge(core, agent, GENOTYPES[1], epoch=8 * 24)
        year = _challenge(core, agent, GENOTYPES[1], epoch=int(YEAR_DAYS) * 24)
        assert voyage > 0.9
        assert year < 0.2
        assert voyage - year > 0.5

    def test_escape_gets_through_a_window_a_matched_strain_does_not(self) -> None:
        core = _core()
        agent = _agent()
        _recovered(agent, GENOTYPES[0], epoch=0)
        matched = _challenge(core, agent, GENOTYPES[0], epoch=24)
        escaping = _challenge(core, agent, GENOTYPES[0], epoch=24, escape=0.9)
        assert matched > 0.9
        assert escaping < 0.2


# ── A window that does not leak ─────────────────────────────────────────

class TestSterilizingWindow:
    """The window is a per-epoch hazard reduction, and every share pays it."""

    def test_unnamed_dose_inside_the_window_does_not_leak(self) -> None:
        """The window is genotype-blind, so it also covers dose it cannot name.

        Environmental pools report a sub-floor tail as ``unresolved``, and that
        share used to sit in the protection denominator at zero — dropping
        protection just under the short-circuit and leaving a hazard of a few
        parts in ten thousand *per epoch*, enough for homologous, zero-escape
        re-infections inside the refractory window at ship doses.
        """
        core = _core()
        registry = core.strain_registry
        assert registry is not None
        agent = _agent()
        _recovered(agent, GENOTYPES[0], epoch=0)
        named = registry.mint(PATHOGEN, genotype=GENOTYPES[0])
        core._strain_doses = {agent.agent_id: {PATHOGEN: {
            (named.strain_id, 0): 100.0,
            (UNRESOLVED_STRAIN, None): 3.0,
        }}}
        assert core._challenge_protection(agent, PATHOGEN, 24) == pytest.approx(1.0)

    def test_unnamed_dose_past_the_window_is_still_unprotected(self) -> None:
        """Only the window is non-specific: matched immunity needs a genotype."""
        core = _core()
        registry = core.strain_registry
        assert registry is not None
        agent = _agent()
        _recovered(agent, GENOTYPES[0], epoch=0)
        named = registry.mint(PATHOGEN, genotype=GENOTYPES[0])
        core._strain_doses = {agent.agent_id: {PATHOGEN: {
            (named.strain_id, 0): 90.0,
            (UNRESOLVED_STRAIN, None): 10.0,
        }}}
        aged = core._challenge_protection(agent, PATHOGEN, 24 * 4000)
        matched = _challenge(core, agent, GENOTYPES[0], epoch=24 * 4000)
        assert aged == pytest.approx(0.9 * matched)
        assert 0.0 < aged < matched

    def test_a_resident_only_prior_gives_unnamed_dose_nothing(self) -> None:
        """No resolution age, no window: interference is a separate mechanism."""
        core = _core()
        agent = _agent()
        agent.prior_genotypes[PATHOGEN] = GENOTYPES[0]
        core._strain_doses = {agent.agent_id: {PATHOGEN: {
            (UNRESOLVED_STRAIN, None): 10.0,
        }}}
        assert core._challenge_protection(agent, PATHOGEN, 24) == pytest.approx(0.0)

    def test_shipped_profiles_declare_a_sterilizing_window(self) -> None:
        """A per-epoch hazard reduction below 1.0 leaks every hour.

        ``TransmissionCore`` applies ``inf_prob *= 1 - protection`` once per
        epoch, so ``refractory_protection: 0.98`` is a 2% hourly hazard, i.e.
        a near-certain homologous re-infection over a voyage. Within-window
        breach is meant to be escape-driven, so every shipped bundle declares
        1.0 and the escape discount is the only way through.
        """
        bundles = sorted((REPO_ROOT / "data/pathogens").glob("*.json"))
        assert bundles
        seen = 0
        for bundle in bundles:
            for entry in json.loads(bundle.read_text())["pathogens"]:
                waning = (entry.get("strain_evolution") or {}).get(
                    "immune_waning",
                )
                if waning is None:
                    continue
                seen += 1
                assert waning["refractory_protection"] == pytest.approx(1.0), (
                    f"{bundle.name}:{entry['pathogen_id']} leaks "
                    f"{1 - waning['refractory_protection']:.3g} per epoch"
                )
        assert seen >= 2

    def test_an_escape_variant_still_breaches_a_sterilizing_window(self) -> None:
        """1.0 is not an absolute wall: escape grades straight through it."""
        waning = ImmuneWaningConfig(
            refractory_days=56.0, refractory_protection=1.0,
            half_life_days=1095.0,
        )
        graded = [
            waning.protection_at(HOMOLOGOUS, 1.0, escape)
            for escape in (0.0, 0.1, 0.3, 0.6)
        ]
        assert graded == sorted(graded, reverse=True)
        assert graded[0] == pytest.approx(1.0)
        assert graded[-1] < graded[0] - 0.1
        assert min(graded) >= HOMOLOGOUS - 1e-9


# ── Legacy fields as a projection of the records ────────────────────────

class TestLegacyProjection:
    def test_an_active_symptomatic_record_shows_at_the_agent_level(self) -> None:
        agent = _agent()
        agent.infect_with_pathogen(PATHOGEN, 1e4, 5, time_infected=5)
        agent.infections[PATHOGEN]["illness"] = IllnessStatus.SYMPTOMATIC
        agent.illness_status = IllnessStatus.NOT_ILL
        _project_legacy_illness(agent)
        assert agent.illness_status == IllnessStatus.SYMPTOMATIC
        assert agent.infection_status == InfectionStatus.INFECTED

    def test_the_projection_unlatches_a_host_whose_records_cleared(self) -> None:
        """The latch: SYMPTOMATIC forever once no transition was observed."""
        agent = _agent()
        agent.infect_with_pathogen(PATHOGEN, 1e4, 5)
        agent.illness_status = IllnessStatus.SYMPTOMATIC
        agent.infections[PATHOGEN]["status"] = InfectionStatus.RECOVERED
        agent.infections[PATHOGEN]["illness"] = IllnessStatus.RECOVERED
        _project_legacy_illness(agent)
        assert agent.infection_status == InfectionStatus.RECOVERED
        assert agent.illness_status == IllnessStatus.RECOVERED

    def test_an_asymptomatic_active_record_is_not_reported_ill(self) -> None:
        agent = _agent()
        agent.infect_with_pathogen(PATHOGEN, 1e4, 5)
        agent.illness_status = IllnessStatus.SYMPTOMATIC
        agent.infections[PATHOGEN]["illness"] = IllnessStatus.NOT_ILL
        _project_legacy_illness(agent)
        assert agent.illness_status == IllnessStatus.NOT_ILL

    def test_a_host_without_records_keeps_the_fallback_state(self) -> None:
        agent = _agent()
        agent.infection_status = InfectionStatus.INFECTED
        agent.illness_status = IllnessStatus.SYMPTOMATIC
        _project_legacy_illness(agent)
        assert agent.illness_status == IllnessStatus.SYMPTOMATIC

    def test_a_second_episode_reopens_the_legacy_fields(self) -> None:
        """The re-infection gap: episode two used to be invisible at agent level."""
        agent = _agent()
        registry = StrainRegistry()
        first = registry.mint(PATHOGEN, genotype=GENOTYPES[0])
        agent.infect_with_pathogen(
            PATHOGEN, 1e4, 0,
            strain_id=first.strain_id, strain_phenotype=Phenotype.of(first),
        )
        for _ in range(3):
            _advance_agent_pathogen_infections(
                agent, {PATHOGEN: _profile(recovery_day=1)},
                np.random.default_rng(1), registry, 96,
            )
        _project_legacy_illness(agent)
        assert agent.infection_status == InfectionStatus.RECOVERED

        second = registry.mint(PATHOGEN, genotype=GENOTYPES[1])
        agent.infect_with_pathogen(
            PATHOGEN, 2e4, 120,
            strain_id=second.strain_id, strain_phenotype=Phenotype.of(second),
        )
        assert agent.infection_status == InfectionStatus.INFECTED
        assert agent.illness_status == IllnessStatus.NOT_ILL
        assert agent.time_infected == 0

    def test_an_immune_host_breached_by_an_escape_variant_is_visible(self) -> None:
        """A breakthrough episode is an episode, not a host that stays IMMUNE."""
        agent = _agent(immune=True)
        assert agent.infection_status == InfectionStatus.IMMUNE
        agent.infect_with_pathogen(PATHOGEN, 1e4, 10)
        assert agent.infection_status == InfectionStatus.INFECTED
        assert agent.illness_status == IllnessStatus.NOT_ILL
