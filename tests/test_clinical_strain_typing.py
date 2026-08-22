"""Clinical amplicon strain typing (variant surveillance, Paper 3 PR 6).

The assay is separated into biology (which lineages a host carries, and in what
proportion) and design (read depth, reporting floor, accuracy, Ct threshold).
These tests therefore check graded responses to the design dials rather than
golden read counts, plus the property that matters for the paper: an assay
below 100% accuracy can name the *wrong* lineage, not merely fail to name one.
"""

from __future__ import annotations

import os

import numpy as np
import pytest

from crusher_labs.instrument_turnaround import InstrumentTurnaroundRegistry
from crusher_labs.modalities.clinical_strain_typing import (
    INSTRUMENT_NAME,
    STATUS_ABOVE_CT_THRESHOLD,
    STATUS_BELOW_READ_FLOOR,
    STATUS_NO_STRAIN_STATE,
    STATUS_NO_TEMPLATE,
    STATUS_NOT_OFFERED,
    STATUS_TYPED,
    AssayConfigError,
    ClinicalStrainTyping,
    SequencingAssay,
    specimen_genotype_mixture,
)
from crusher_labs.modalities.long_read_sequencing import (
    SPECIMEN_CLINICAL,
    SPECIMEN_WASTEWATER_METAGENOMICS,
    LongReadNanoporeSequencing,
    LongReadVerificationRequest,
)
from crusher_labs.modalities.targeted_pcr import TargetedPCR, ct_from_mass
from engines.infection_dynamics_bridge import KorkinAgent
from engines.strain_state import StrainRegistry, StrainState
from orchestrator_init import _build_strain_typing

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PATHOGEN = "norwalk_gi"
GENOTYPES = ("GII.4", "GII.17", "GII.2")

PROFILE = {
    "pathogen_id": PATHOGEN,
    "recovery_day": 5,
    "shedding_curve_log10": [6.0, 7.0, 7.0, 6.0, 5.0],
    "asymptomatic_shedding_log10": [5.0, 5.0, 5.0, 4.0, 4.0],
    "dose_adjustment": 1.0,
    "strain_evolution": {"genotypes": list(GENOTYPES)},
    "sequencing_assay": {
        "amplicon_target": "Capsid (VP1)",
        "read_accuracy": 0.92,
        "ct_threshold": 30.0,
        "cost_usd": 150.0,
    },
}

# Mass that clears a Ct threshold of 30 at the clinical extraction efficiency.
AMPLE_MASS = 1e6
FAINT_MASS = 10.0


def assay(**overrides) -> SequencingAssay:
    profile = dict(PROFILE)
    profile["sequencing_assay"] = {**PROFILE["sequencing_assay"], **overrides}
    parsed = SequencingAssay.from_profile(profile)
    assert parsed is not None
    return parsed


def typer(seed: int = 7, **overrides) -> ClinicalStrainTyping:
    return ClinicalStrainTyping(
        {PATHOGEN: assay(**overrides)},
        rng=np.random.default_rng(seed),
    )


class TestAssayConfig:
    """The assay block is config, so it has to fail loudly when wrong."""

    def test_profile_block_parses_spec_values(self):
        parsed = assay()
        assert parsed.amplicon_target == "Capsid (VP1)"
        assert parsed.read_accuracy == pytest.approx(0.92)
        assert parsed.ct_threshold == pytest.approx(30.0)
        assert parsed.cost_usd == pytest.approx(150.0)

    def test_genotypes_come_from_strain_evolution_not_a_second_list(self):
        assert assay().genotypes == GENOTYPES

    def test_absent_block_is_none_not_a_default_assay(self):
        assert SequencingAssay.from_profile({"pathogen_id": PATHOGEN}) is None

    @pytest.mark.parametrize(
        "overrides",
        [
            {"read_accuracy": 0.0},
            {"read_accuracy": 1.5},
            {"amplicon_target": "  "},
            {"read_depth": 0},
            {"min_reads_for_genotype": 0},
        ],
    )
    def test_unusable_values_raise(self, overrides):
        with pytest.raises(AssayConfigError):
            assay(**overrides)

    def test_load_profiles_skips_untyped_pathogens(self):
        assays = SequencingAssay.load_profiles({
            PATHOGEN: PROFILE,
            "other": {"pathogen_id": "other"},
        })
        assert set(assays) == {PATHOGEN}


class TestCtGate:
    """Typing reuses the targeted-PCR standard curve, and is gated on it."""

    def test_ct_curve_is_the_targeted_pcr_curve(self):
        pcr = TargetedPCR(extraction_efficiency=0.5)
        assert pcr._compute_ct(1e5) == ct_from_mass(1e5, 0.5)

    def test_no_template_yields_no_call(self):
        result = typer().type_specimen(1, PATHOGEN, 0.0, {"GII.4": 1.0})
        assert result["status"] == STATUS_NO_TEMPLATE
        assert result["genotype_calls"] == []
        assert result["consensus_genotype"] is None

    def test_specimen_above_ct_threshold_is_not_typed(self):
        result = typer().type_specimen(1, PATHOGEN, FAINT_MASS, {"GII.4": 1.0})
        assert result["status"] == STATUS_ABOVE_CT_THRESHOLD
        assert result["ct_value"] > result["ct_threshold"]
        assert result["genotype_calls"] == []

    def test_a_looser_threshold_types_the_same_faint_specimen(self):
        loose = typer(ct_threshold=40.0)
        result = loose.type_specimen(1, PATHOGEN, FAINT_MASS, {"GII.4": 1.0})
        assert result["status"] == STATUS_TYPED
        assert result["consensus_genotype"] == "GII.4"

    def test_pathogen_without_an_assay_is_not_offered(self):
        result = typer().type_specimen(1, "sars_cov2_resp", AMPLE_MASS, {"BA.1": 1.0})
        assert result["status"] == STATUS_NOT_OFFERED
        assert result["informative"] is False

    def test_untracked_infection_cannot_be_typed(self):
        result = typer().type_specimen(1, PATHOGEN, AMPLE_MASS, {})
        assert result["status"] == STATUS_NO_STRAIN_STATE
        assert result["informative"] is False


class TestGenotypeCalls:
    """A typed specimen names the lineage the host is actually carrying."""

    def test_single_lineage_is_called_correctly_at_high_accuracy(self):
        result = typer(read_accuracy=1.0).type_specimen(
            3, PATHOGEN, AMPLE_MASS, {"GII.17": 1.0},
        )
        assert result["status"] == STATUS_TYPED
        assert result["consensus_genotype"] == "GII.17"
        assert result["correct_consensus"] is True
        assert result["mixed_genotype_flag"] is False
        assert result["amplicon_target"] == "Capsid (VP1)"
        assert result["cost_usd"] == pytest.approx(150.0)

    def test_reads_are_conserved_at_the_configured_depth(self):
        result = typer(read_accuracy=0.92).type_specimen(
            3, PATHOGEN, AMPLE_MASS, {"GII.4": 0.5, "GII.2": 0.5}, read_depth=4000,
        )
        assert sum(result["read_counts"].values()) == 4000
        assert result["read_depth"] == 4000

    def test_coinfection_is_reported_as_a_mixture(self):
        result = typer(read_accuracy=1.0).type_specimen(
            3, PATHOGEN, AMPLE_MASS, {"GII.4": 0.6, "GII.2": 0.4},
        )
        called = {call["genotype"] for call in result["genotype_calls"]}
        assert called == {"GII.4", "GII.2"}
        assert result["mixed_genotype_flag"] is True
        assert result["consensus_genotype"] == "GII.4"

    def test_calls_are_ordered_by_read_support(self):
        result = typer(read_accuracy=1.0).type_specimen(
            3, PATHOGEN, AMPLE_MASS, {"GII.4": 0.8, "GII.2": 0.2},
        )
        reads = [call["reads"] for call in result["genotype_calls"]]
        assert reads == sorted(reads, reverse=True)

    def test_fractions_sum_to_about_one_when_all_lineages_clear_the_floor(self):
        result = typer(read_accuracy=1.0).type_specimen(
            3, PATHOGEN, AMPLE_MASS, {"GII.4": 0.5, "GII.2": 0.5},
        )
        total = sum(call["fraction"] for call in result["genotype_calls"])
        assert total == pytest.approx(1.0, abs=1e-4)


class TestDesignDials:
    """Depth and the reporting floor are operator choices, and must bite."""

    def test_depth_raises_the_minor_lineage_read_count_monotonically(self):
        minor = []
        for depth in (200, 2000, 20000):
            result = typer(read_accuracy=1.0).type_specimen(
                4, PATHOGEN, AMPLE_MASS,
                {"GII.4": 0.97, "GII.2": 0.03},
                read_depth=depth,
            )
            minor.append(result["read_counts"].get("GII.2", 0))
        assert minor == sorted(minor)
        assert minor[-1] > minor[0]

    def test_shallow_depth_hides_a_minor_lineage_the_deep_run_reports(self):
        shallow = typer(read_accuracy=1.0).type_specimen(
            4, PATHOGEN, AMPLE_MASS, {"GII.4": 0.98, "GII.2": 0.02},
            read_depth=100, min_reads_for_genotype=20,
        )
        deep = typer(read_accuracy=1.0).type_specimen(
            4, PATHOGEN, AMPLE_MASS, {"GII.4": 0.98, "GII.2": 0.02},
            read_depth=20000, min_reads_for_genotype=20,
        )
        assert shallow["mixed_genotype_flag"] is False
        assert deep["mixed_genotype_flag"] is True

    def test_a_floor_above_the_whole_run_yields_no_call_at_all(self):
        result = typer().type_specimen(
            4, PATHOGEN, AMPLE_MASS, {"GII.4": 1.0},
            read_depth=50, min_reads_for_genotype=500,
        )
        assert result["status"] == STATUS_BELOW_READ_FLOOR
        assert result["genotype_calls"] == []

    def test_raising_the_floor_can_only_drop_calls(self):
        counts = []
        for floor in (5, 50, 500):
            result = typer(read_accuracy=1.0).type_specimen(
                4, PATHOGEN, AMPLE_MASS,
                {"GII.4": 0.9, "GII.2": 0.07, "GII.17": 0.03},
                read_depth=1000, min_reads_for_genotype=floor,
            )
            counts.append(len(result["genotype_calls"]))
        assert counts == sorted(counts, reverse=True)


class TestAccuracy:
    """Imperfect accuracy has to be able to produce a wrong genotype."""

    def _miscall_rate(self, accuracy: float, depth: int, trials: int = 120) -> float:
        wrong = 0
        for seed in range(trials):
            result = ClinicalStrainTyping(
                {PATHOGEN: assay(read_accuracy=accuracy)},
                rng=np.random.default_rng(seed),
            ).type_specimen(
                5, PATHOGEN, AMPLE_MASS, {"GII.4": 1.0},
                read_depth=depth, min_reads_for_genotype=1,
            )
            if result["consensus_genotype"] not in (None, "GII.4"):
                wrong += 1
        return wrong / trials

    def test_a_low_accuracy_assay_names_the_wrong_lineage_sometimes(self):
        assert self._miscall_rate(0.30, depth=5) > 0.0

    def test_miscall_rate_falls_as_accuracy_rises(self):
        low = self._miscall_rate(0.30, depth=5)
        mid = self._miscall_rate(0.60, depth=5)
        high = self._miscall_rate(0.92, depth=5)
        assert low > high
        assert low >= mid >= high

    def test_perfect_accuracy_never_miscalls(self):
        assert self._miscall_rate(1.0, depth=5) == pytest.approx(0.0)

    def test_error_reads_land_on_declared_genotypes_only(self):
        result = typer(read_accuracy=0.5).type_specimen(
            5, PATHOGEN, AMPLE_MASS, {"GII.4": 1.0}, read_depth=2000,
        )
        assert set(result["read_counts"]) <= set(GENOTYPES)

    def test_deeper_reads_recover_the_truth_a_shallow_run_can_miss(self):
        shallow = self._miscall_rate(0.55, depth=3)
        deep = self._miscall_rate(0.55, depth=999)
        assert deep < shallow

    def test_a_miscalled_consensus_is_flagged_as_incorrect(self):
        result = typer(read_accuracy=1.0).type_specimen(
            5, PATHOGEN, AMPLE_MASS, {"GII.4": 0.2, "GII.2": 0.8},
        )
        assert result["consensus_genotype"] == "GII.2"
        assert result["correct_consensus"] is True
        assert result["true_genotypes"] == ["GII.2", "GII.4"]


def _long_read(strain_typing: ClinicalStrainTyping | None) -> LongReadNanoporeSequencing:
    return LongReadNanoporeSequencing.from_params_path(
        os.path.join(REPO_ROOT, "data/config/long_read_sequencing_params.json"),
        "flongle_rapid",
        rng=np.random.default_rng(0),
        repo_root=REPO_ROOT,
        strain_typing=strain_typing,
    )


def _clinical_request() -> LongReadVerificationRequest:
    return LongReadVerificationRequest(
        request_id="lr_typing",
        specimen_source=SPECIMEN_CLINICAL,
        collection_key="3",
        trigger_reasons=["mixed_infection_suspected"],
    )


CLINICAL_AGENTS = [{
    "agent_id": 3,
    "shedding_rate": 5.0e6,
    "pathogen_infections": {PATHOGEN: {"status": "INFECTED"}},
}]


class TestLongReadIntegration:
    """Genotype calls ride along with the existing pathogen-level pass."""

    def test_pathogen_calls_are_unchanged_without_a_typing_assay(self):
        out = _long_read(None).verify(
            _clinical_request(), epoch=2,
            agents=CLINICAL_AGENTS, pathogen_profiles={PATHOGEN: PROFILE},
        )
        assert out["status"] == "complete"
        assert out["genotype_calls"] == []
        assert isinstance(out["pathogen_calls"], list)

    def test_clinical_specimen_gains_a_genotype_call(self):
        out = _long_read(typer(read_accuracy=1.0)).verify(
            _clinical_request(), epoch=2,
            agents=CLINICAL_AGENTS, pathogen_profiles={PATHOGEN: PROFILE},
            genotype_mixtures={PATHOGEN: {"GII.17": 1.0}},
        )
        call = out["genotype_calls"][0]
        assert call["status"] == STATUS_TYPED
        assert call["consensus_genotype"] == "GII.17"
        assert call["agent_id"] == 3
        assert call["epoch"] == 2

    def test_typing_depth_override_reaches_the_assay(self):
        out = _long_read(typer()).verify(
            _clinical_request(), epoch=0,
            agents=CLINICAL_AGENTS, pathogen_profiles={PATHOGEN: PROFILE},
            genotype_mixtures={PATHOGEN: {"GII.4": 1.0}},
            typing_read_depth=777,
        )
        assert out["genotype_calls"][0]["read_depth"] == 777

    def test_environmental_specimen_is_not_clinically_typed(self):
        request = LongReadVerificationRequest(
            request_id="lr_ww",
            specimen_source=SPECIMEN_WASTEWATER_METAGENOMICS,
            collection_key="Engine_Room",
        )
        out = _long_read(typer()).verify(
            request, epoch=0,
            spaces={"Engine_Room": {"pathogen_mass": 5000.0}},
            genotype_mixtures={PATHOGEN: {"GII.4": 1.0}},
        )
        assert out["genotype_calls"] == []

    def test_typing_engine_is_gated_on_variant_surveillance(self):
        assert _build_strain_typing(
            {"variant_surveillance": {"enabled": False}},
            {PATHOGEN: PROFILE}, seed=1,
        ) is None
        assert _build_strain_typing(
            {"variant_surveillance": {"enabled": True}}, {}, seed=1,
        ) is None
        engine = _build_strain_typing(
            {"variant_surveillance": {"enabled": True}},
            {PATHOGEN: PROFILE}, seed=1,
        )
        assert engine is not None
        assert set(engine.assays) == {PATHOGEN}

    def test_turnaround_config_carries_the_typing_instrument(self):
        registry = InstrumentTurnaroundRegistry.load(
            "data/config/instrument_turnaround.json", repo_root=REPO_ROOT,
        )
        assert registry.delay_epochs_for(INSTRUMENT_NAME) >= 1


def _agent(aid: int = 1) -> KorkinAgent:
    return KorkinAgent(
        agent_id=aid,
        role="passenger",
        immune=False,
        home_zone="MainDining_L",
        dining_zone="MainDining_L",
        work_zone="MainDining_L",
        free_zone="MainDining_L",
        schedule=["Free"] * 24,
    )


def _infected_agent(registry: StrainRegistry, genotypes: list[str]) -> KorkinAgent:
    agent = _agent()
    strains = []
    for idx, genotype in enumerate(genotypes):
        strain = StrainState(
            strain_id=f"s{idx}",
            pathogen_id=PATHOGEN,
            genotype=genotype,
        )
        registry.register(strain)
        strains.append(strain)
    agent.infect_with_pathogen(
        PATHOGEN, dose=100.0, epoch=0, strain_id=strains[0].strain_id,
    )
    for strain in strains[1:]:
        agent.superinfect_with_strain(
            PATHOGEN, strain.strain_id, dose=100.0, epoch=0,
        )
    return agent


class TestSpecimenTruthFromStrainState:
    """The mixture the assay sees comes from the host's resident lineages."""

    def test_single_infection_gives_its_genotype(self):
        registry = StrainRegistry()
        agent = _infected_agent(registry, ["GII.4"])
        assert specimen_genotype_mixture(agent, PATHOGEN, PROFILE, registry) == {
            "GII.4": 1.0,
        }

    def test_coinfection_gives_both_genotypes_summing_to_one(self):
        registry = StrainRegistry()
        agent = _infected_agent(registry, ["GII.4", "GII.2"])
        mixture = specimen_genotype_mixture(agent, PATHOGEN, PROFILE, registry)
        assert set(mixture) == {"GII.4", "GII.2"}
        assert sum(mixture.values()) == pytest.approx(1.0)

    def test_two_lineages_of_one_genotype_collapse(self):
        registry = StrainRegistry()
        agent = _infected_agent(registry, ["GII.4", "GII.4"])
        mixture = specimen_genotype_mixture(agent, PATHOGEN, PROFILE, registry)
        assert mixture == {"GII.4": pytest.approx(1.0)}

    def test_untracked_infection_gives_no_mixture(self):
        registry = StrainRegistry()
        agent = _agent(2)
        agent.infect_with_pathogen(PATHOGEN, dose=100.0, epoch=0)
        assert specimen_genotype_mixture(agent, PATHOGEN, PROFILE, registry) == {}

    def test_recovered_host_sheds_nothing_to_type(self):
        registry = StrainRegistry()
        agent = _infected_agent(registry, ["GII.4"])
        for _ in range(int(PROFILE["recovery_day"])):
            agent.advance_resident_strains(PATHOGEN, int(PROFILE["recovery_day"]))
        assert specimen_genotype_mixture(agent, PATHOGEN, PROFILE, registry) == {}
