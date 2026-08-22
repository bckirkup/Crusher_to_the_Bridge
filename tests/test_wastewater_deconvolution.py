"""What a wastewater library can and cannot say about the lineages in a tank.

The channel already answers "is the pathogen here"; deconvolution answers "which
lineages", and the point of these tests is that the second answer is much weaker
than the first. Reads are conserved rather than renormalized, so a composition
recovered off a shallow library reports how little of the pool it resolved
instead of restating the simulator's truth at full confidence; a minority lineage
below the reporting floor is unresolved reads, not an absence; and ``metagenomic``
stays blind by construction, as the negative control for the whole idea.

Graded sensitivity (deeper libraries resolve more, tighter floors report less)
and conservation bounds carry the suite rather than golden compositions, which
would only pin the RNG.
"""

from __future__ import annotations

import os
import sys
from typing import Any

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from picard_framework.analysis.sentinel.observations import bundle_from_dict
from picard_framework.analysis.sentinel.wastewater_assays import (
    ASSAY_AMPLICON,
    ASSAY_LONG_READ,
    ASSAY_METAGENOMIC,
    ASSAY_QPCR,
    LINEAGE_STATUS_BELOW_REPORTING_FLOOR,
    LINEAGE_STATUS_DECONVOLVED,
    LINEAGE_STATUS_INSUFFICIENT_READS,
    LINEAGE_STATUS_NO_COMPOSITION,
    LINEAGE_STATUS_NO_TEMPLATE,
    LINEAGE_STATUS_NOT_CONFIGURED,
    StrainDeconvolutionConfig,
    deconvolve_lineages,
)
from picard_framework.analysis.sentinel.wastewater_ops import (
    WastewaterOpsConfig,
    WastewaterOpsSampler,
)

PATHOGEN = "norovirus"
DOMINANT = "GII.4"
MINOR = "GII.17"
THIRD = "GII.2"


def _deconv(**over: Any) -> StrainDeconvolutionConfig:
    base: dict[str, Any] = {"enabled": True}
    base.update(over)
    return StrainDeconvolutionConfig.from_mapping(base)


def _config(**over: Any) -> WastewaterOpsConfig:
    base: dict[str, Any] = {
        "enabled": True,
        "sampling_interval_epochs": 6,
        "holding_tank_residence_hours": 4.0,
        "collection_points": ["aft_main"],
        "sequencing_depth": 250_000,
        "pathogen": PATHOGEN,
        "pathogen_id": "norwalk_gi",
    }
    base.update(over)
    return WastewaterOpsConfig.from_mapping(base)


def _sampler(seed: int = 11, **over: Any) -> WastewaterOpsSampler:
    return WastewaterOpsSampler(
        _config(**over),
        epoch_duration_hours=1.0,
        rng=np.random.default_rng(seed),
    )


def _run(
    sampler: WastewaterOpsSampler,
    *,
    prevalence: float,
    composition: dict[str, float] | None,
    epochs: int = 12,
    aboard: float = 3000.0,
) -> tuple[dict[str, Any], ...]:
    """Hold prevalence and shed composition flat, so only the assay varies."""
    points = sampler.config.collection_points
    for epoch in range(epochs):
        sampler.observe_epoch(
            epoch,
            shedders_by_point={p: prevalence * aboard for p in points},
            population_by_point={p: aboard for p in points},
            composition_by_point=None if composition is None else {p: composition for p in points},
        )
    return sampler.samples()


class TestDeconvolutionConfig:
    """The operator's dials, and the operating points that are not runnable."""

    def test_defaults_are_off_so_existing_runs_are_unchanged(self) -> None:
        cfg = StrainDeconvolutionConfig()
        assert cfg.enabled is False

    def test_mapping_round_trips_every_dial(self) -> None:
        cfg = _deconv(
            dirichlet_concentration=50.0,
            min_pathogen_reads=500,
            min_lineage_reads=5,
            min_lineage_fraction=0.1,
        )
        assert cfg.enabled is True
        assert cfg.dirichlet_concentration == pytest.approx(50.0)
        assert cfg.min_pathogen_reads == 500
        assert cfg.min_lineage_reads == 5
        assert cfg.min_lineage_fraction == pytest.approx(0.1)

    @pytest.mark.parametrize(
        "bad",
        [
            {"dirichlet_concentration": 0.0},
            {"min_pathogen_reads": 0},
            {"min_lineage_reads": 0},
            {"min_lineage_fraction": 1.0},
            {"min_lineage_fraction": -0.01},
        ],
    )
    def test_unrunnable_operating_points_are_rejected(self, bad: dict[str, Any]) -> None:
        with pytest.raises(ValueError):
            _deconv(**bad)

    def test_config_block_reaches_the_sampler_metadata(self) -> None:
        cfg = _config(assay_mode="amplicon", strain_deconvolution={"enabled": True})
        assert cfg.strain_deconvolution.enabled is True
        assert cfg.to_metadata()["ww_strain_deconvolution"] is True


class TestReadConservation:
    """Every on-target read is attributed or explicitly unresolved."""

    @pytest.mark.parametrize(
        "composition",
        [
            {DOMINANT: 1.0},
            {DOMINANT: 0.9, MINOR: 0.1},
            {DOMINANT: 0.6, MINOR: 0.3, THIRD: 0.1},
            {DOMINANT: 0.5, "unresolved": 0.5},
            {},
        ],
    )
    def test_resolved_plus_unresolved_equals_the_library(
        self,
        composition: dict[str, float],
    ) -> None:
        mixture = deconvolve_lineages(
            5_000,
            composition,
            config=_deconv(),
            rng=np.random.default_rng(3),
        )
        assert mixture.resolved_reads + mixture.unresolved_reads == mixture.pathogen_reads

    def test_untracked_pool_mass_consumes_reads_without_being_called(self) -> None:
        """PR 4's ``unresolved`` bin is pathogen the assay saw and cannot name."""
        mixture = deconvolve_lineages(
            20_000,
            {DOMINANT: 0.5, "unresolved": 0.5},
            config=_deconv(),
            rng=np.random.default_rng(5),
        )
        called = {genotype for genotype, _reads in mixture.calls}
        assert called == {DOMINANT}
        assert mixture.unresolved_reads > 0.4 * mixture.pathogen_reads


class TestWhatIsNotACall:
    """Statuses that are refusals, not compositions."""

    def test_unconfigured_assay_reports_nothing(self) -> None:
        mixture = deconvolve_lineages(
            10_000,
            {DOMINANT: 1.0},
            config=StrainDeconvolutionConfig(),
            rng=np.random.default_rng(1),
        )
        assert mixture.status == LINEAGE_STATUS_NOT_CONFIGURED
        assert mixture.calls == ()
        assert mixture.consensus_genotype is None

    def test_no_reads_is_no_template_rather_than_a_negative_lineage(self) -> None:
        mixture = deconvolve_lineages(
            0,
            {DOMINANT: 1.0},
            config=_deconv(),
            rng=np.random.default_rng(1),
        )
        assert mixture.status == LINEAGE_STATUS_NO_TEMPLATE
        assert mixture.pathogen_reads == 0

    def test_untyped_pool_is_distinguishable_from_an_untyped_assay(self) -> None:
        mixture = deconvolve_lineages(
            10_000,
            {},
            config=_deconv(),
            rng=np.random.default_rng(1),
        )
        assert mixture.status == LINEAGE_STATUS_NO_COMPOSITION
        assert mixture.unresolved_reads == 10_000

    def test_shallow_library_says_so_instead_of_reporting_the_truth(self) -> None:
        mixture = deconvolve_lineages(
            10,
            {DOMINANT: 0.9, MINOR: 0.1},
            config=_deconv(min_pathogen_reads=100),
            rng=np.random.default_rng(1),
        )
        assert mixture.status == LINEAGE_STATUS_INSUFFICIENT_READS
        assert mixture.calls == ()
        assert mixture.unresolved_reads == 10

    def test_a_library_whose_every_lineage_is_sub_floor_reports_none(self) -> None:
        mixture = deconvolve_lineages(
            200,
            {f"g{idx}": 1.0 for idx in range(20)},
            config=_deconv(min_lineage_reads=50, min_pathogen_reads=100),
            rng=np.random.default_rng(2),
        )
        assert mixture.status == LINEAGE_STATUS_BELOW_REPORTING_FLOOR
        assert mixture.consensus_genotype is None
        assert mixture.unresolved_reads == 200


class TestRecovery:
    """What a deep library gets right, and what depth costs."""

    def test_single_lineage_pool_recovers_that_lineage(self) -> None:
        mixture = deconvolve_lineages(
            10_000,
            {DOMINANT: 1.0},
            config=_deconv(),
            rng=np.random.default_rng(7),
        )
        assert mixture.status == LINEAGE_STATUS_DECONVOLVED
        assert mixture.consensus_genotype == DOMINANT
        assert mixture.resolved_reads == 10_000

    def test_deep_library_recovers_known_proportions(self) -> None:
        truth = {DOMINANT: 0.7, MINOR: 0.2, THIRD: 0.1}
        rng = np.random.default_rng(19)
        mixture = deconvolve_lineages(
            200_000,
            truth,
            config=_deconv(dirichlet_concentration=5_000.0),
            rng=rng,
        )
        recovered = {
            genotype: reads / mixture.pathogen_reads for genotype, reads in mixture.calls
        }
        assert set(recovered) == set(truth)
        for genotype, share in truth.items():
            assert recovered[genotype] == pytest.approx(share, abs=0.03)

    def test_dominance_ordering_is_preserved_across_seeds(self) -> None:
        truth = {DOMINANT: 0.6, MINOR: 0.3, THIRD: 0.1}
        for seed in range(12):
            mixture = deconvolve_lineages(
                50_000,
                truth,
                config=_deconv(),
                rng=np.random.default_rng(seed),
            )
            assert mixture.consensus_genotype == DOMINANT
            assert [g for g, _r in mixture.calls] == [DOMINANT, MINOR, THIRD]

    def test_depth_grades_how_many_lineages_are_resolvable(self) -> None:
        """A minority lineage is a function of the library, not just the pool."""
        truth = {DOMINANT: 0.97, MINOR: 0.03}
        found = {}
        for depth in (200, 2_000, 100_000):
            hits = 0
            for seed in range(20):
                mixture = deconvolve_lineages(
                    depth,
                    truth,
                    config=_deconv(min_lineage_reads=20, min_lineage_fraction=0.0),
                    rng=np.random.default_rng(seed),
                )
                hits += any(g == MINOR for g, _r in mixture.calls)
            found[depth] = hits
        assert found[200] < found[100_000]
        assert found[100_000] == 20

    def test_abundance_floor_grades_what_is_reportable(self) -> None:
        truth = {DOMINANT: 0.9, MINOR: 0.1}
        reported = []
        for floor in (0.01, 0.05, 0.2):
            mixture = deconvolve_lineages(
                100_000,
                truth,
                config=_deconv(min_lineage_fraction=floor),
                rng=np.random.default_rng(23),
            )
            reported.append(len(mixture.calls))
        assert reported == [2, 2, 1]

    def test_a_badly_reproducible_library_is_noisier_than_a_tight_one(self) -> None:
        """The Dirichlet layer is library bias, so it must widen the spread."""
        truth = {DOMINANT: 0.5, MINOR: 0.5}

        def spread(concentration: float) -> float:
            shares = []
            for seed in range(24):
                mixture = deconvolve_lineages(
                    50_000,
                    truth,
                    config=_deconv(dirichlet_concentration=concentration),
                    rng=np.random.default_rng(seed),
                )
                reads = dict(mixture.calls).get(DOMINANT, 0)
                shares.append(reads / mixture.pathogen_reads)
            return float(np.std(shares))

        assert spread(5.0) > spread(5_000.0)


class TestSamplerIntegration:
    """What reaches an observation row, per assay mode."""

    def test_amplicon_rows_carry_the_recovered_mixture(self) -> None:
        sampler = _sampler(
            assay_mode=ASSAY_AMPLICON,
            strain_deconvolution={"enabled": True},
        )
        rows = _run(sampler, prevalence=0.05, composition={DOMINANT: 0.8, MINOR: 0.2})
        typed = [r for r in rows if r["lineage_status"] == LINEAGE_STATUS_DECONVOLVED]
        assert typed, "a shedding ship at 5% should type its amplicon library"
        row = typed[-1]
        assert row["genotype"] == DOMINANT
        assert {c["genotype"] for c in row["lineage_calls"]} == {DOMINANT, MINOR}
        called = sum(c["reads"] for c in row["lineage_calls"])
        assert called + row["lineage_unresolved_reads"] == row["pathogen_reads"]

    def test_amplicon_without_deconvolution_keeps_its_legacy_row(self) -> None:
        sampler = _sampler(assay_mode=ASSAY_AMPLICON)
        rows = _run(sampler, prevalence=0.05, composition={DOMINANT: 1.0})
        assert rows
        for row in rows:
            assert row["genotype"] is None
            assert row["lineage_status"] == LINEAGE_STATUS_NOT_CONFIGURED
            assert row["lineage_calls"] == []

    def test_long_read_consensus_overrides_the_configured_reference(self) -> None:
        sampler = _sampler(
            assay_mode=ASSAY_LONG_READ,
            long_read={"reference_genotype": "reference_only"},
            strain_deconvolution={"enabled": True},
        )
        rows = _run(sampler, prevalence=0.08, composition={MINOR: 1.0})
        typed = [r for r in rows if r["lineage_status"] == LINEAGE_STATUS_DECONVOLVED]
        assert typed
        assert typed[-1]["genotype"] == MINOR

    @pytest.mark.parametrize("mode", [ASSAY_METAGENOMIC, ASSAY_QPCR])
    def test_blind_modes_report_no_lineage_at_all(self, mode: str) -> None:
        """Metagenomics is the negative control; qPCR has no library."""
        sampler = _sampler(assay_mode=mode, strain_deconvolution={"enabled": True})
        rows = _run(sampler, prevalence=0.05, composition={DOMINANT: 1.0})
        assert rows
        for row in rows:
            assert "lineage_status" not in row
            assert "lineage_calls" not in row

    def test_a_pool_with_no_tracked_lineage_still_detects_the_pathogen(self) -> None:
        sampler = _sampler(
            assay_mode=ASSAY_AMPLICON,
            strain_deconvolution={"enabled": True},
        )
        rows = _run(sampler, prevalence=0.05, composition=None)
        assert rows
        for row in rows:
            assert row["lineage_status"] in {
                LINEAGE_STATUS_NO_COMPOSITION,
                LINEAGE_STATUS_NO_TEMPLATE,
            }
            assert row["genotype"] is None

    def test_tank_composition_is_lagged_like_the_prevalence_it_rides_on(self) -> None:
        sampler = _sampler(
            assay_mode=ASSAY_AMPLICON,
            strain_deconvolution={"enabled": True},
        )
        points = sampler.config.collection_points
        for epoch in range(8):
            sampler.observe_epoch(
                epoch,
                shedders_by_point={p: 150.0 for p in points},
                population_by_point={p: 3000.0 for p in points},
                composition_by_point={p: {DOMINANT: 1.0} for p in points},
            )
        before = sampler.tank_composition()["aft_main"]
        assert set(before) == {DOMINANT}
        # A new lineage arrives; yesterday's mixture must still dilute it.
        sampler.observe_epoch(
            8,
            shedders_by_point={p: 150.0 for p in points},
            population_by_point={p: 3000.0 for p in points},
            composition_by_point={p: {MINOR: 1.0} for p in points},
        )
        mixed = sampler.tank_composition()["aft_main"]
        assert set(mixed) == {DOMINANT, MINOR}
        assert mixed[DOMINANT] > mixed[MINOR]
        assert mixed[DOMINANT] < before[DOMINANT]

    def test_composition_totals_track_the_scalar_tank(self) -> None:
        sampler = _sampler(
            assay_mode=ASSAY_AMPLICON,
            strain_deconvolution={"enabled": True},
        )
        _run(sampler, prevalence=0.05, composition={DOMINANT: 0.5, MINOR: 0.5})
        total = sum(sampler.tank_composition()["aft_main"].values())
        assert total == pytest.approx(sampler.tank_state()["aft_main"], rel=1e-9)


class TestBundlePlumbing:
    """The loader carries lineage fields, and refuses an impossible one."""

    @staticmethod
    def _payload(sample: dict[str, Any]) -> dict[str, Any]:
        return {
            "voyage_id": "v1",
            "ship_id": "s1",
            "clinical_cases": [],
            "wastewater_samples": [sample],
        }

    def test_lineage_fields_survive_the_loader(self) -> None:
        bundle = bundle_from_dict(
            self._payload(
                {
                    "sample_epoch": 6,
                    "collection_point": "aft_main",
                    "pathogen": PATHOGEN,
                    "assay_mode": ASSAY_AMPLICON,
                    "pathogen_reads": 1_000,
                    "total_reads": 10_000,
                    "genotype": DOMINANT,
                    "lineage_status": LINEAGE_STATUS_DECONVOLVED,
                    "lineage_calls": [
                        {"genotype": DOMINANT, "reads": 700, "fraction": 0.7},
                        {"genotype": MINOR, "reads": 200, "fraction": 0.2},
                    ],
                    "lineage_unresolved_reads": 100,
                },
            ),
        )
        sample = bundle.wastewater_samples[0]
        assert [c.genotype for c in sample.lineage_calls] == [DOMINANT, MINOR]
        assert sample.resolved_lineage_fraction == pytest.approx(0.9)

    def test_a_row_claiming_more_lineage_reads_than_it_sequenced_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="exceed pathogen_reads"):
            bundle_from_dict(
                self._payload(
                    {
                        "sample_epoch": 6,
                        "collection_point": "aft_main",
                        "pathogen": PATHOGEN,
                        "pathogen_reads": 100,
                        "total_reads": 1_000,
                        "lineage_calls": [{"genotype": DOMINANT, "reads": 900}],
                    },
                ),
            )

    def test_a_legacy_row_has_no_lineage_information(self) -> None:
        bundle = bundle_from_dict(
            self._payload(
                {
                    "sample_epoch": 6,
                    "collection_point": "aft_main",
                    "pathogen": PATHOGEN,
                    "pathogen_reads": 10,
                    "total_reads": 1_000,
                },
            ),
        )
        sample = bundle.wastewater_samples[0]
        assert sample.lineage_status is None
        assert sample.lineage_calls == ()
        assert sample.resolved_lineage_fraction == pytest.approx(0.0)
