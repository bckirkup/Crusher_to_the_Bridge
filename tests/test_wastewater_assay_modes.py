"""What each wastewater assay mode reports, and what it refuses to claim.

The switch's purpose is that the four modes are *not* interchangeable views of
one number, so the tests are mostly about the differences a report would be
wrong to ignore: qPCR is quantitative and censors below the LOD, amplicon reads
saturate and only exist behind that gate, metagenomics is arithmetically blind
at the prevalence a cruise reaches, and long-read is a delayed confirmation.

Graded sensitivity ("a few different prevalences produce a few different
outputs") and bounds ("reads never exceed the library, a non-detect never
reports a concentration") carry the suite; the one golden number is the
metagenomic blind regime, which is labelled as such because it is the finding
the assay arm of the ops scan exists to state.
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from picard_framework.analysis.sentinel.fleet import wastewater_summary
from picard_framework.analysis.sentinel.observations import bundle_from_dict
from picard_framework.analysis.sentinel.wastewater_assays import (
    ASSAY_AMPLICON,
    ASSAY_LONG_READ,
    ASSAY_METAGENOMIC,
    ASSAY_MODES,
    ASSAY_QPCR,
    DEFAULT_ASSAY_MODE,
    AmpliconAssayConfig,
    QpcrAssayConfig,
    ShedLoadModel,
    qpcr_reading,
    resolve_assay_mode,
)
from picard_framework.analysis.sentinel.wastewater_ops import (
    WastewaterOpsConfig,
    WastewaterOpsSampler,
)
from picard_framework.analysis.sentinel.wastewater_signal import (
    censored_normal_logpdf,
    pool_concentrations,
    pool_wastewater,
)
from picard_framework.analysis.stan._sentinel_fleet_data import wastewater_shares
from picard_framework.analysis.stan._sentinel_fleet_reference import (
    fleet_reference_posterior,
)
from tests.test_sentinel_wastewater import (
    SAMPLE_EPOCHS,
    VOYAGE_IDS,
    crossover_fleet,
    fleet_data,
    simulate_onsets,
    truth_rates,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
OBS_SCHEMA = REPO_ROOT / "schemas" / "sentinel_observations.schema.json"

PATHOGEN = "norovirus"
# Peak shedder prevalence of the full-scale cell that motivated the switch: 18
# shedders on a 7 000-berth ship.
CRUISE_PREVALENCE = 0.0026


def _config(**over: Any) -> WastewaterOpsConfig:
    base: dict[str, Any] = {
        "enabled": True,
        "sampling_interval_epochs": 6,
        "holding_tank_residence_hours": 4.0,
        "collection_points": ["aft_main"],
        "sequencing_depth": 250_000,
        "pathogen": PATHOGEN,
    }
    base.update(over)
    return WastewaterOpsConfig.from_mapping(base)


def _sampler(seed: int = 17, **over: Any) -> WastewaterOpsSampler:
    return WastewaterOpsSampler(
        _config(**over),
        epoch_duration_hours=1.0,
        rng=np.random.default_rng(seed),
    )


def _run(
    sampler: WastewaterOpsSampler,
    *,
    prevalence: float,
    epochs: int = 48,
    aboard: float = 3000.0,
) -> tuple[dict[str, Any], ...]:
    """Hold shedder prevalence flat, so only the assay varies."""
    points = sampler.config.collection_points
    for epoch in range(epochs):
        sampler.observe_epoch(
            epoch,
            shedders_by_point={p: prevalence * aboard for p in points},
            population_by_point={p: aboard for p in points},
        )
    return sampler.samples()


def _qpcr_rows(shares: np.ndarray, rng: np.random.Generator) -> list[dict[str, Any]]:
    """qPCR rows off known shedder prevalences, through the real assay chain."""
    cfg = QpcrAssayConfig()
    load = ShedLoadModel()
    rows: list[dict[str, Any]] = []
    for epoch in SAMPLE_EPOCHS:
        reading = qpcr_reading(
            load.gc_per_l(float(shares[epoch - 1])), config=cfg, rng=rng,
        )
        row: dict[str, Any] = {
            "sample_epoch": epoch,
            "collection_point": "aft_main",
            "pathogen": PATHOGEN,
            "assay_mode": ASSAY_QPCR,
            "clr_anomaly_score": 0.0,
        }
        row.update(reading.as_row())
        rows.append(row)
    return rows


def _fleet_with_qpcr(seed: int = 3) -> tuple[dict[str, Any], dict[str, Any]]:
    """Two crossed voyages whose qPCR series come from one known truth."""
    bare, _ = fleet_data(crossover_fleet())
    rates = truth_rates(bare)
    simulated = simulate_onsets(bare, rates)
    shares = wastewater_shares(simulated, rates)
    rng = np.random.default_rng(seed)
    rows = {
        voyage_id: _qpcr_rows(shares[v], rng)
        for v, voyage_id in enumerate(VOYAGE_IDS)
    }
    data, meta = fleet_data(crossover_fleet(rows))
    data = dict(data)
    data["onsets"] = simulated["onsets"]
    return data, meta


def _bundle(samples: tuple[dict[str, Any], ...], voyage_id: str = "assay") -> Any:
    return bundle_from_dict(
        {
            "voyage_id": voyage_id,
            "ship_id": "test",
            "clinical_cases": [],
            "wastewater_samples": [dict(s) for s in samples],
        },
    )


class TestModeSelection:
    """The switch itself: what a config may say, and what it means by default."""

    def test_absent_mode_keeps_the_pre_switch_behaviour(self) -> None:
        """Every campaign cell predating the switch must still mean metagenomic."""
        assert DEFAULT_ASSAY_MODE == ASSAY_METAGENOMIC
        assert _config().assay_mode == ASSAY_METAGENOMIC
        assert resolve_assay_mode(None) == ASSAY_METAGENOMIC

    @pytest.mark.parametrize("mode", ASSAY_MODES)
    def test_each_mode_is_selectable_and_labels_its_rows(self, mode: str) -> None:
        samples = _run(_sampler(assay_mode=mode), prevalence=0.2)
        assert samples
        assert {s["assay_mode"] for s in samples} == {mode}
        assert _config(assay_mode=mode).to_metadata()["ww_assay_mode"] == mode

    @pytest.mark.parametrize("raw", ["QPCR", " qpcr ", "Long_Read"])
    def test_case_and_padding_are_normalized(self, raw: str) -> None:
        assert resolve_assay_mode(raw) == raw.strip().lower()

    @pytest.mark.parametrize("bad", ["ddpcr", "sequencing", "qcpr", "16s"])
    def test_an_unknown_mode_is_refused_rather_than_defaulted(self, bad: str) -> None:
        with pytest.raises(ValueError, match="assay_mode"):
            _config(assay_mode=bad)

    def test_each_sequencing_mode_reports_its_own_library_depth(self) -> None:
        """qPCR sequences nothing; the other modes are not one shared depth."""
        depths = {m: _config(assay_mode=m).assay_depth for m in ASSAY_MODES}
        assert depths[ASSAY_QPCR] == 0
        assert depths[ASSAY_METAGENOMIC] == 250_000
        assert depths[ASSAY_AMPLICON] > 0
        assert depths[ASSAY_LONG_READ] > 0
        assert depths[ASSAY_LONG_READ] < depths[ASSAY_METAGENOMIC]


class TestQpcr:
    """A Ct that tracks the tank, and a bound when it does not clear the LOD."""

    def test_ct_falls_as_prevalence_rises(self) -> None:
        """Graded: more template, fewer cycles, over four decades of prevalence."""
        cfg = QpcrAssayConfig(ct_noise_sd=0.0)
        load = ShedLoadModel()
        rng = np.random.default_rng(0)
        cts = [
            qpcr_reading(load.gc_per_l(p), config=cfg, rng=rng).ct_value
            for p in (1e-4, 1e-3, 1e-2, 1e-1, 1.0)
        ]
        assert all(ct is not None for ct in cts)
        assert cts == sorted(cts, reverse=True)
        # A decade of template is one slope's worth of cycles (~3.32).
        gaps = [b - a for a, b in zip(cts[1:], cts[:-1])]
        assert all(3.0 < g < 3.7 for g in gaps), gaps

    def test_detection_rate_grades_across_the_limit_of_detection(self) -> None:
        cfg = _config(assay_mode=ASSAY_QPCR)
        lod_share = cfg.qpcr.lod_gc_per_l / cfg.load_model.gc_per_l_at_full_shedding
        rates = []
        for factor in (0.01, 0.3, 1.0, 3.0, 100.0):
            samples = _run(
                _sampler(seed=5, assay_mode=ASSAY_QPCR, sampling_interval_epochs=1),
                prevalence=lod_share * factor,
                epochs=60,
            )
            tail = samples[20:]
            rates.append(sum(1 for s in tail if s["detected"]) / len(tail))
        assert rates == sorted(rates)
        assert rates[0] == pytest.approx(0.0), "far below the LOD, nothing detects"
        assert rates[-1] == pytest.approx(1.0), "far above it, everything does"

    def test_a_detected_sample_reports_a_concentration_near_the_truth(self) -> None:
        samples = _run(_sampler(assay_mode=ASSAY_QPCR), prevalence=0.05)
        truth = ShedLoadModel().gc_per_l(0.05)
        detected = [s for s in samples if s["detected"]]
        assert detected == list(samples), "5 % shedders is far above the qPCR LOD"
        for row in detected:
            reported = row["concentration_copies_per_l"]
            assert row["ct_value"] is not None
            # Ct noise is what separates the report from the truth; 0.5 cycles is
            # ~1.4x in concentration, so a factor of 3 is a generous bound.
            assert 1 / 3 < reported / truth < 3, reported

    def test_a_non_detect_reports_the_bound_and_nothing_else(self) -> None:
        samples = _run(_sampler(assay_mode=ASSAY_QPCR), prevalence=0.0)
        assert samples
        for row in samples:
            assert row["detected"] is False
            assert row["ct_value"] is None
            assert row["concentration_copies_per_l"] is None
            assert row["lod_copies_per_l"] > 0.0

    def test_qpcr_rows_carry_no_library(self) -> None:
        """No sequencing keys at all, so the read channel cannot score them."""
        samples = _run(_sampler(assay_mode=ASSAY_QPCR), prevalence=0.05)
        for row in samples:
            assert "pathogen_reads" not in row
            assert "total_reads" not in row

    def test_the_same_seed_reproduces_the_ct_series(self) -> None:
        first = _run(_sampler(seed=99, assay_mode=ASSAY_QPCR), prevalence=0.02)
        again = _run(_sampler(seed=99, assay_mode=ASSAY_QPCR), prevalence=0.02)
        other = _run(_sampler(seed=100, assay_mode=ASSAY_QPCR), prevalence=0.02)
        assert first == again
        assert [r["ct_value"] for r in first] != [r["ct_value"] for r in other]


class TestAmplicon:
    """Reads only behind the gate, and a fraction that stops being quantitative."""

    def test_a_non_detect_sequences_nothing(self) -> None:
        samples = _run(_sampler(assay_mode=ASSAY_AMPLICON), prevalence=0.0)
        assert samples
        for row in samples:
            assert row["detected"] is False
            assert row["total_reads"] == 0
            assert row["pathogen_reads"] == 0

    def test_a_detected_sample_yields_bounded_on_target_reads(self) -> None:
        samples = _run(_sampler(assay_mode=ASSAY_AMPLICON), prevalence=0.05)
        depth = _config(assay_mode=ASSAY_AMPLICON).amplicon.sequencing_depth
        assert samples
        for row in samples:
            assert row["detected"] is True
            assert row["total_reads"] == depth
            assert 0 < row["pathogen_reads"] <= row["total_reads"]
            assert row["primer_target"]

    def test_the_on_target_fraction_saturates(self) -> None:
        """Graded then flat: above saturation, reads stop measuring template."""
        cfg = AmpliconAssayConfig()
        half = cfg.half_saturation_copies
        fractions = [cfg.on_target_fraction(half * f) for f in (0.01, 0.1, 1.0, 10.0, 1000.0)]
        assert fractions == sorted(fractions)
        assert all(0.0 <= f <= cfg.amplification_efficiency for f in fractions)
        assert math.isclose(fractions[2], cfg.amplification_efficiency / 2, rel_tol=1e-9)
        # Four more decades of template buy less than a factor of two of signal.
        assert fractions[-1] / fractions[2] < 2.0

    def test_read_counts_grade_with_prevalence_only_below_saturation(self) -> None:
        means = []
        for prevalence in (1e-3, 1e-2, 1e-1):
            samples = _run(
                _sampler(seed=3, assay_mode=ASSAY_AMPLICON, sampling_interval_epochs=1),
                prevalence=prevalence,
                epochs=40,
            )
            tail = [s["pathogen_reads"] for s in samples[20:]]
            means.append(sum(tail) / len(tail))
        assert means == sorted(means)
        assert means[0] < means[-1]


class TestMetagenomic:
    """Unchanged, and blind where it matters — the comparison arm of the scan."""

    def test_rows_keep_the_pre_switch_shape(self) -> None:
        samples = _run(_sampler(assay_mode=ASSAY_METAGENOMIC), prevalence=0.2)
        for row in samples:
            assert set(row) == {
                "sample_epoch",
                "collection_point",
                "pathogen",
                "assay_mode",
                "pathogen_reads",
                "total_reads",
            }
            assert 0 <= row["pathogen_reads"] <= row["total_reads"] == 250_000

    def test_the_default_mode_reproduces_the_recorded_read_series(self) -> None:
        """Change-detector: the compatibility default must not drift."""
        explicit = _run(_sampler(seed=17, assay_mode=ASSAY_METAGENOMIC), prevalence=0.2)
        implicit = _run(_sampler(seed=17), prevalence=0.2)
        assert [r["pathogen_reads"] for r in explicit] == [
            r["pathogen_reads"] for r in implicit
        ]

    def test_shotgun_is_blind_at_the_prevalence_a_cruise_reaches(self) -> None:
        """0.26 % shedders is ~0.06 expected reads in a 250 000-read library.

        Almost every composite therefore comes back empty, and the few that do
        not are single reads: a per-epoch read fraction that is 0 or 4e-6 cannot
        resolve a prevalence curve, which is the finding the assay arm states.
        """
        samples = _run(
            _sampler(seed=11, assay_mode=ASSAY_METAGENOMIC, sampling_interval_epochs=1),
            prevalence=CRUISE_PREVALENCE,
            epochs=120,
        )
        reads = [s["pathogen_reads"] for s in samples]
        empty = sum(1 for r in reads if r == 0)
        assert empty / len(reads) > 0.9, reads
        assert sum(reads) / len(reads) < 0.5, reads

    def test_qpcr_still_sees_what_shotgun_cannot(self) -> None:
        """The reason the scan's core cells run qPCR rather than metagenomics."""
        samples = _run(
            _sampler(seed=11, assay_mode=ASSAY_QPCR, sampling_interval_epochs=1),
            prevalence=CRUISE_PREVALENCE,
            epochs=120,
        )
        assert all(s["detected"] for s in samples[20:])


class TestLongRead:
    """Confirmation, not cadence: the same gate plus an instrument delay."""

    def test_a_detected_sample_reports_reads_and_a_turnaround(self) -> None:
        cfg = _config(assay_mode=ASSAY_LONG_READ)
        samples = _run(_sampler(assay_mode=ASSAY_LONG_READ), prevalence=0.05)
        assert samples
        for row in samples:
            assert row["total_reads"] == cfg.long_read.sequencing_depth
            assert 0 < row["pathogen_reads"] <= row["total_reads"]
            assert row["turnaround_hours"] == cfg.long_read.turnaround_hours
            assert row["turnaround_hours"] > 0.0, "a confirmation is not instantaneous"

    def test_a_non_detect_neither_sequences_nor_types(self) -> None:
        samples = _run(_sampler(assay_mode=ASSAY_LONG_READ), prevalence=0.0)
        assert samples
        for row in samples:
            assert row["total_reads"] == 0
            assert row["genotype"] is None

    def test_a_configured_reference_genotype_is_reported_when_detected(self) -> None:
        samples = _run(
            _sampler(
                assay_mode=ASSAY_LONG_READ,
                long_read={"reference_genotype": "GI.1"},
            ),
            prevalence=0.05,
        )
        assert {r["genotype"] for r in samples} == {"GI.1"}

    def test_the_read_count_does_not_pretend_to_quantify(self) -> None:
        """On-target fraction is a library property: a decade of template, same share."""
        shares = []
        for prevalence in (1e-2, 1e-1):
            samples = _run(
                _sampler(seed=7, assay_mode=ASSAY_LONG_READ, sampling_interval_epochs=1),
                prevalence=prevalence,
                epochs=40,
            )
            tail = samples[20:]
            shares.append(
                sum(s["pathogen_reads"] / s["total_reads"] for s in tail) / len(tail),
            )
        assert math.isclose(shares[0], shares[1], rel_tol=0.05)


class TestOperatingPolicyIsModeInvariant:
    """A mode comparison that also moved the plumbing would not be one."""

    @pytest.mark.parametrize("mode", ASSAY_MODES)
    def test_cadence_and_taps_are_identical_across_modes(self, mode: str) -> None:
        samples = _run(
            _sampler(
                assay_mode=mode,
                sampling_interval_epochs=6,
                collection_points=["aft_main", "midship", "forward"],
            ),
            prevalence=0.05,
            epochs=48,
        )
        epochs = sorted({s["sample_epoch"] for s in samples})
        assert epochs == [6, 12, 18, 24, 30, 36, 42]
        assert len(samples) == 3 * len(epochs)
        assert {s["collection_point"] for s in samples} == {
            "aft_main",
            "midship",
            "forward",
        }

    @pytest.mark.parametrize("mode", ASSAY_MODES)
    def test_the_tank_still_smears_across_epochs_in_every_mode(self, mode: str) -> None:
        sampler = _sampler(assay_mode=mode, holding_tank_residence_hours=8.0)
        sampler.observe_epoch(
            0,
            shedders_by_point={"aft_main": 100.0},
            population_by_point={"aft_main": 1000.0},
        )
        peak = sampler.tank_state()["aft_main"]
        for epoch in range(1, 6):
            sampler.observe_epoch(
                epoch,
                shedders_by_point={"aft_main": 0.0},
                population_by_point={"aft_main": 1000.0},
            )
        assert 0.0 < sampler.tank_state()["aft_main"] < peak

    def test_a_disabled_channel_samples_nothing_whatever_the_mode(self) -> None:
        cfg = WastewaterOpsConfig.from_mapping(
            {"enabled": False, "assay_mode": ASSAY_QPCR},
        )
        assert cfg.enabled is False
        assert cfg.assay_mode == ASSAY_QPCR


class TestBundleRoundTrip:
    """Heterogeneous rows have to survive the schema and the loader."""

    @pytest.mark.parametrize("mode", ASSAY_MODES)
    @pytest.mark.parametrize("prevalence", [0.0, 0.05])
    def test_rows_validate_and_load(self, mode: str, prevalence: float) -> None:
        jsonschema = pytest.importorskip("jsonschema")
        schema = json.loads(OBS_SCHEMA.read_text(encoding="utf-8"))
        samples = _run(_sampler(assay_mode=mode), prevalence=prevalence)
        payload = {
            "voyage_id": "assay_round_trip",
            "ship_id": "test",
            "clinical_cases": [],
            "wastewater_samples": [dict(s) for s in samples],
        }
        jsonschema.validate(payload, schema)
        bundle = bundle_from_dict(payload)
        assert len(bundle.wastewater_samples) == len(samples)
        assert {s.assay_mode for s in bundle.wastewater_samples} == {mode}

    def test_a_non_detect_reporting_a_concentration_is_refused(self) -> None:
        with pytest.raises(ValueError, match="below the limit of detection"):
            _bundle(
                (
                    {
                        "sample_epoch": 6,
                        "collection_point": "aft_main",
                        "pathogen": PATHOGEN,
                        "assay_mode": ASSAY_QPCR,
                        "detected": False,
                        "ct_value": None,
                        "concentration_copies_per_l": 1.0e6,
                        "lod_copies_per_l": 1.0e4,
                    },
                ),
            )

    def test_a_quantitative_row_without_a_bound_is_refused(self) -> None:
        with pytest.raises(ValueError, match="lod_copies_per_l"):
            _bundle(
                (
                    {
                        "sample_epoch": 6,
                        "collection_point": "aft_main",
                        "pathogen": PATHOGEN,
                        "assay_mode": ASSAY_QPCR,
                        "detected": True,
                        "ct_value": 30.0,
                        "concentration_copies_per_l": 1.0e6,
                    },
                ),
            )


class TestChannelRouting:
    """Which likelihood each mode's rows are allowed to reach."""

    def test_qpcr_rows_pool_into_concentrations_and_not_into_reads(self) -> None:
        samples = _run(
            _sampler(
                assay_mode=ASSAY_QPCR,
                collection_points=["aft_main", "midship", "forward"],
            ),
            prevalence=0.05,
        )
        bundle = _bundle(samples)
        assert pool_wastewater(bundle, pathogen=PATHOGEN, observation_end_epoch=48) == ()
        pooled = pool_concentrations(
            bundle, pathogen=PATHOGEN, observation_end_epoch=48,
        )
        assert len(pooled) == len({s["sample_epoch"] for s in samples})
        for obs in pooled:
            assert obs.n_collection_points == 3, "replicate taps are one observation"
            assert obs.n_detected == 3
            assert obs.censored is False
            assert math.isfinite(obs.log10_copies_per_l)

    def test_an_all_negative_epoch_pools_as_one_censored_observation(self) -> None:
        samples = _run(
            _sampler(assay_mode=ASSAY_QPCR, collection_points=["aft_main", "midship"]),
            prevalence=0.0,
        )
        pooled = pool_concentrations(
            _bundle(samples), pathogen=PATHOGEN, observation_end_epoch=48,
        )
        assert pooled
        for obs in pooled:
            assert obs.censored is True
            assert obs.n_detected == 0
            assert obs.n_collection_points == 2

    def test_shotgun_rows_pool_into_reads_and_not_into_concentrations(self) -> None:
        samples = _run(_sampler(assay_mode=ASSAY_METAGENOMIC), prevalence=0.2)
        bundle = _bundle(samples)
        assert pool_wastewater(bundle, pathogen=PATHOGEN, observation_end_epoch=48)
        assert pool_concentrations(
            bundle, pathogen=PATHOGEN, observation_end_epoch=48,
        ) == ()

    def test_amplicon_rows_reach_both_channels(self) -> None:
        """The gate is quantitative; the reads it opens are still reads."""
        samples = _run(_sampler(assay_mode=ASSAY_AMPLICON), prevalence=0.05)
        bundle = _bundle(samples)
        assert pool_wastewater(bundle, pathogen=PATHOGEN, observation_end_epoch=48)
        assert pool_concentrations(bundle, pathogen=PATHOGEN, observation_end_epoch=48)


class TestFleetChannels:
    """What the assembled fit data, and a posterior off it, may contain."""

    def test_qpcr_voyages_assemble_a_concentration_channel_only(self) -> None:
        data, meta = _fleet_with_qpcr()
        assert int(data["NW"]) == 0, "a qPCR row is not a sequencing library"
        assert int(data["NC"]) == len(SAMPLE_EPOCHS) * 2
        assert len(data["conc_log10"]) == int(data["NC"])
        assert set(data["conc_censored"]) <= {0, 1}
        assert meta["wastewater"]["n_concentration_samples"] == int(data["NC"])

    def test_a_clinical_only_fleet_assembles_both_channels_empty(self) -> None:
        """The ablation control: no reads, no concentrations, model unchanged."""
        data, _ = fleet_data(crossover_fleet(), enabled=False)
        assert int(data["NW"]) == 0
        assert int(data["NC"]) == 0
        assert data["conc_log10"] == []
        assert data["conc_epoch"] == []

    def test_the_reference_posterior_recovers_the_concentration_link(self) -> None:
        """The qPCR chain is linear in prevalence, so the true slope is 1."""
        data, meta = _fleet_with_qpcr()
        posterior = fleet_reference_posterior(data, draws=120, warmup=400, seed=5)
        summary = wastewater_summary(posterior, meta)
        assert summary["enabled"] is True
        assert summary["fitted"] is False, "there is no read arm to fit"
        assert summary["concentration_fitted"] is True
        assert summary["conc_slope_q05"] < 1.0 < summary["conc_slope_q95"]
        # log10(1e10 gc/person/day / 30 L/person/day) = 8.52 at full shedding.
        assert 7.5 < summary["conc_intercept_mean"] < 9.5
        assert math.isfinite(summary["loglik_concentration"])

    def test_a_clinical_only_posterior_quotes_no_assay_estimate(self) -> None:
        data, meta = fleet_data(crossover_fleet(), enabled=False)
        data = dict(data)
        data["onsets"] = simulate_onsets(data, truth_rates(data))["onsets"]
        posterior = fleet_reference_posterior(data, draws=40, warmup=120, seed=5)
        summary = wastewater_summary(posterior, meta)
        assert summary["enabled"] is False
        assert summary["fitted"] is False
        assert summary["concentration_fitted"] is False
        assert "conc_slope_mean" not in summary


class TestCensoredLikelihood:
    """A non-detect must be worth a bound, not a measurement and not nothing."""

    def test_a_censored_term_grades_with_the_bound(self) -> None:
        """A higher bound is weaker evidence, so it costs a low mean less."""
        bounds = [1.0, 2.0, 3.0, 4.0]
        values = [
            float(
                censored_normal_logpdf([b], [0.0], 1.0, [True])[0],
            )
            for b in bounds
        ]
        assert values == sorted(values)
        assert all(v <= 0.0 for v in values)
        assert all(math.isfinite(v) for v in values)

    def test_a_measured_value_is_scored_as_a_density(self) -> None:
        measured = float(censored_normal_logpdf([0.0], [0.0], 1.0, [False])[0])
        expected = -0.5 * math.log(2.0 * math.pi)
        assert math.isclose(measured, expected, rel_tol=1e-9)

    def test_a_bound_far_above_the_mean_stays_finite(self) -> None:
        far = float(censored_normal_logpdf([50.0], [0.0], 1.0, [True])[0])
        assert math.isfinite(far)
        assert far <= 0.0

    def test_zero_sigma_is_refused(self) -> None:
        with pytest.raises(ValueError, match="sigma"):
            censored_normal_logpdf([1.0], [0.0], 0.0, [True])
