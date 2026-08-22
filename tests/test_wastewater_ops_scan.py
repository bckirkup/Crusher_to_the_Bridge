"""Behavioral tests for the shipboard wastewater sampling ops layer.

The scan asks which operating point is worth paying for, so the tests assert the
*shape* of each knob's response rather than pinned draws: cadence sets how many
samples exist, residence time smears them, depth buys precision with saturating
returns, and extra taps are correlated replicates rather than extra evidence.
"""

from __future__ import annotations

import copy
import json
import math
import statistics
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from picard_framework.analysis.sentinel.observations import bundle_from_dict
from picard_framework.analysis.sentinel.wastewater_ops import (
    WastewaterOpsConfig,
    WastewaterOpsSampler,
    assign_collection_points,
)
from picard_framework.analysis.sentinel.wastewater_signal import pool_wastewater
from picard_framework.runs.mega_cruise_campaign import campaign_runner, expand_design

REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN_DIR = REPO_ROOT / "picard_framework" / "runs" / "mega_cruise_campaign"
WW_DESIGN = CAMPAIGN_DIR / "sentinel_ww_ops_scan_v1_design.json"
WW_MANIFEST = CAMPAIGN_DIR / "sentinel_ww_ops_scan_v1_manifest.json"
LEGACY_DESIGN = CAMPAIGN_DIR / "sentinel_synthetic_recovery_v1_design.json"

EXPECTED_TOTAL_RUNS = 9000


def _config(**over: Any) -> WastewaterOpsConfig:
    base: dict[str, Any] = {
        "enabled": True,
        "sampling_interval_epochs": 1,
        "holding_tank_residence_hours": 4.0,
        "collection_points": ["aft_main"],
        "sequencing_depth": 250_000,
        "pathogen": "norovirus",
    }
    base.update(over)
    return WastewaterOpsConfig.from_mapping(base)


def _sampler(seed: int = 17, **over: Any) -> WastewaterOpsSampler:
    return WastewaterOpsSampler(
        _config(**over),
        epoch_duration_hours=1.0,
        rng=np.random.default_rng(seed),
    )


def _run_constant(
    sampler: WastewaterOpsSampler,
    *,
    epochs: int,
    prevalence: float,
    aboard: float = 2000.0,
) -> tuple[dict[str, Any], ...]:
    """Hold shedder prevalence flat so only the sampler's own knobs vary."""
    points = sampler.config.collection_points
    for epoch in range(epochs):
        sampler.observe_epoch(
            epoch,
            shedders_by_point={p: prevalence * aboard for p in points},
            population_by_point={p: aboard for p in points},
        )
    return sampler.samples()


def _impulse_tank(residence_hours: float, *, epochs: int = 24) -> list[float]:
    """Tank trace for one epoch of shedding, i.e. the residence response."""
    sampler = _sampler(holding_tank_residence_hours=residence_hours)
    trace: list[float] = []
    for epoch in range(epochs):
        shedders = 100.0 if epoch == 1 else 0.0
        sampler.observe_epoch(
            epoch,
            shedders_by_point={"aft_main": shedders},
            population_by_point={"aft_main": 1000.0},
        )
        trace.append(sampler.tank_state()["aft_main"])
    return trace


class TestConfigValidation:
    """A misconfigured operating point must fail loudly, not sample silently."""

    @pytest.mark.parametrize(
        "bad",
        [
            {"sampling_interval_epochs": 0},
            {"holding_tank_residence_hours": -1.0},
            {"sequencing_depth": 0},
            {"collection_points": []},
            {"collection_points": ["aft_main", "aft_main"]},
            {"background_read_fraction": 1.0},
            {"background_read_fraction": -0.1},
            {"pathogen_shedding_to_reads_scale": 0.0},
            {"pathogen": ""},
        ],
    )
    def test_invalid_operating_points_are_rejected(self, bad: dict[str, Any]) -> None:
        with pytest.raises(ValueError):
            _config(**bad)

    def test_defaults_are_disabled_so_existing_runs_are_unchanged(self) -> None:
        assert WastewaterOpsConfig.from_mapping(None).enabled is False
        assert WastewaterOpsConfig.from_mapping({}).enabled is False

    def test_metadata_reports_the_operating_point(self) -> None:
        meta = _config(
            sampling_interval_epochs=6,
            holding_tank_residence_hours=8.0,
            collection_points=["aft_main", "midship", "forward"],
            sequencing_depth=1_000_000,
        ).to_metadata()
        assert meta == {
            "wastewater_enabled": True,
            "ww_assay_mode": "metagenomic",
            "ww_sampling_interval_epochs": 6,
            "ww_residence_hours": 8.0,
            "ww_sequencing_depth": 1_000_000,
            "ww_collection_points": 3,
            "ww_strain_deconvolution": False,
        }


class TestSensitivity:
    """Graded response: a few different values in -> a few different values out."""

    def test_cadence_grades_the_number_of_samples(self) -> None:
        epochs = 168
        counts = [
            len(
                _run_constant(
                    _sampler(sampling_interval_epochs=interval),
                    epochs=epochs,
                    prevalence=0.02,
                ),
            )
            for interval in (1, 3, 6, 12, 24)
        ]
        assert counts == sorted(counts, reverse=True)
        assert counts == [167, 55, 27, 13, 6]
        # A 24-epoch composite must still resolve the ~daily port structure.
        assert counts[-1] >= 6

    def test_residence_time_smears_a_shedding_impulse(self) -> None:
        traces = {tau: _impulse_tank(tau) for tau in (0.5, 2.0, 4.0, 8.0, 12.0)}
        peaks = [max(traces[tau]) for tau in (0.5, 2.0, 4.0, 8.0, 12.0)]
        # What a sample drawn 12 epochs later still sees: half the ~24 h
        # inter-port interval, i.e. the scale attribution has to resolve.
        tails = [traces[tau][13] for tau in (0.5, 2.0, 4.0, 8.0, 12.0)]

        assert peaks == sorted(peaks, reverse=True), "longer residence must blunt the peak"
        assert tails == sorted(tails), "longer residence must lengthen the memory"
        assert peaks[0] / max(peaks[-1], 1e-12) > 5.0, "residence knob looks dead"
        # The regime the scan exists to find: at 12 h a spike still carries a
        # third of its peak into the next port call, so calls overlap.
        assert tails[-1] / max(peaks[-1], 1e-12) > 0.3
        assert tails[0] / max(peaks[0], 1e-12) < 0.05

    def test_zero_residence_is_a_direct_line_tap(self) -> None:
        sampler = _sampler(holding_tank_residence_hours=0.0)
        sampler.observe_epoch(
            1,
            shedders_by_point={"aft_main": 40.0},
            population_by_point={"aft_main": 1000.0},
        )
        assert sampler.retention_weight == pytest.approx(0.0)
        assert sampler.tank_state()["aft_main"] == pytest.approx(0.04)

    def test_prevalence_grades_the_read_fraction(self) -> None:
        fractions = []
        for prevalence in (0.0, 0.01, 0.05, 0.25):
            samples = _run_constant(
                _sampler(seed=3, holding_tank_residence_hours=0.5),
                epochs=48,
                prevalence=prevalence,
            )
            fractions.append(
                statistics.fmean(s["pathogen_reads"] / s["total_reads"] for s in samples),
            )
        assert fractions == sorted(fractions)
        assert fractions[0] == pytest.approx(0.0, abs=1e-7)
        assert fractions[-1] > 5.0 * max(fractions[1], 1e-12)

    def test_depth_buys_precision_with_saturating_returns(self) -> None:
        cvs = []
        for depth in (50_000, 250_000, 1_000_000):
            samples = _run_constant(
                _sampler(seed=11, sequencing_depth=depth, holding_tank_residence_hours=0.5),
                epochs=400,
                prevalence=0.2,
            )
            observed = [s["pathogen_reads"] / s["total_reads"] for s in samples]
            cvs.append(statistics.stdev(observed) / statistics.fmean(observed))

        assert cvs == sorted(cvs, reverse=True), f"deeper libraries must not be noisier: {cvs}"
        assert cvs[0] - cvs[1] > cvs[1] - cvs[2], (
            f"depth returns must saturate once extraction noise dominates: {cvs}"
        )

    def test_depth_moves_precision_not_the_observed_fraction(self) -> None:
        """Negative control: depth is a cost knob, not a bias knob."""
        means = []
        for depth in (50_000, 250_000, 1_000_000):
            samples = _run_constant(
                _sampler(seed=29, sequencing_depth=depth, holding_tank_residence_hours=0.5),
                epochs=500,
                prevalence=1.0,
            )
            means.append(statistics.fmean(s["pathogen_reads"] / s["total_reads"] for s in samples))
        # Tolerance is the ~5% standard error of 500 draws at this dispersion,
        # doubled: the estimator is unbiased in depth, not noiseless.
        assert means[0] == pytest.approx(means[-1], rel=0.1)

    def test_depth_does_not_disturb_the_tank(self) -> None:
        """Negative control: sequencing is downstream of the plumbing."""
        tanks = []
        for depth in (50_000, 1_000_000):
            sampler = _sampler(sequencing_depth=depth)
            _run_constant(sampler, epochs=24, prevalence=0.1)
            tanks.append(sampler.tank_state()["aft_main"])
        assert tanks[0] == pytest.approx(tanks[1], rel=1e-12)

    def test_collection_points_add_replicates_not_epochs(self) -> None:
        rows = {}
        for points in (["aft_main"], ["aft_main", "midship", "forward"]):
            samples = _run_constant(
                _sampler(collection_points=points, sampling_interval_epochs=6),
                epochs=48,
                prevalence=0.05,
            )
            rows[len(points)] = samples

        assert len(rows[3]) == 3 * len(rows[1])
        assert {s["collection_point"] for s in rows[3]} == {"aft_main", "midship", "forward"}
        # Same epochs sampled: extra taps are replicates of one tank draw.
        assert {s["sample_epoch"] for s in rows[3]} == {s["sample_epoch"] for s in rows[1]}


class TestInvariants:
    """Ranges, finiteness and the count contract the fit's likelihood needs."""

    def test_counts_stay_schema_valid_over_a_long_voyage(self) -> None:
        samples = _run_constant(
            _sampler(collection_points=["aft_main", "midship", "forward"]),
            epochs=336,
            prevalence=0.3,
        )
        assert samples
        for row in samples:
            assert isinstance(row["pathogen_reads"], int)
            assert isinstance(row["total_reads"], int)
            assert row["total_reads"] == 250_000
            assert 0 <= row["pathogen_reads"] <= row["total_reads"]
            assert row["sample_epoch"] >= 1
            assert math.isfinite(row["pathogen_reads"] / row["total_reads"])

    def test_an_outbreak_free_ship_yields_a_near_empty_library(self) -> None:
        samples = _run_constant(_sampler(seed=5), epochs=168, prevalence=0.0)
        assert max(row["pathogen_reads"] for row in samples) == 0

    def test_a_fully_shedding_ship_tops_out_at_the_informative_fraction(self) -> None:
        cfg = _config(holding_tank_residence_hours=0.5)
        samples = _run_constant(_sampler(seed=5, holding_tank_residence_hours=0.5), epochs=96, prevalence=1.0)
        observed = statistics.fmean(s["pathogen_reads"] / s["total_reads"] for s in samples)
        assert observed == pytest.approx(cfg.informative_read_fraction, rel=0.3)

    def test_same_seed_reproduces_the_same_draws(self) -> None:
        first = _run_constant(_sampler(seed=101), epochs=24, prevalence=0.1)
        second = _run_constant(_sampler(seed=101), epochs=24, prevalence=0.1)
        assert first == second

    def test_every_zone_routes_to_a_configured_tap(self) -> None:
        zones = [f"zone_{i}" for i in range(11)]
        single = assign_collection_points(zones, ["aft_main"])
        assert set(single.values()) == {"aft_main"}
        assert len(single) == len(zones)

        triple = assign_collection_points(zones, ["aft_main", "midship", "forward"])
        assert set(triple) == set(zones)
        loads = [list(triple.values()).count(p) for p in ("aft_main", "midship", "forward")]
        assert min(loads) >= 1
        assert max(loads) - min(loads) <= 1, f"taps should drain comparable shares: {loads}"

    def test_empty_zone_list_routes_nothing(self) -> None:
        assert assign_collection_points([], ["aft_main"]) == {}

    def test_replicate_taps_pool_into_one_capped_trial_per_epoch(self) -> None:
        samples = _run_constant(
            _sampler(collection_points=["aft_main", "midship", "forward"], sampling_interval_epochs=6),
            epochs=48,
            prevalence=0.2,
        )
        bundle = bundle_from_dict(
            {
                "voyage_id": "ww_pool",
                "ship_id": "test",
                "clinical_cases": [],
                "wastewater_samples": [dict(s) for s in samples],
            },
        )
        pooled = pool_wastewater(
            bundle,
            pathogen="norovirus",
            observation_end_epoch=48,
            max_effective_reads=200_000,
        )
        assert len(pooled) == len({s["sample_epoch"] for s in samples})
        for trial in pooled:
            assert trial.n_collection_points == 3
            assert trial.effective_reads <= 200_000
            assert 0 <= trial.effective_pathogen_reads <= trial.effective_reads


class TestCampaignDesign:
    """The scan's cells, run count and per-run overrides."""

    def test_design_expands_to_the_documented_cell_blocks(self) -> None:
        design = json.loads(WW_DESIGN.read_text(encoding="utf-8"))
        cells = expand_design.build_wastewater_cells(design)
        blocks: dict[str, int] = {}
        for cell in cells:
            blocks[cell["block"]] = blocks.get(cell["block"], 0) + 1
        assert blocks == {
            "core": 25,
            "depth": 6,
            "collection": 2,
            "assay": 3,
            "control": 1,
        }
        assert len({c["cell_id"] for c in cells}) == len(cells)

    def test_control_cell_is_the_clinical_only_baseline(self) -> None:
        design = json.loads(WW_DESIGN.read_text(encoding="utf-8"))
        control = [
            c for c in expand_design.build_wastewater_cells(design) if c["block"] == "control"
        ]
        assert len(control) == 1
        assert control[0]["wastewater_surveillance"]["enabled"] is False

    def test_cells_cover_every_cadence_and_residence_level(self) -> None:
        design = json.loads(WW_DESIGN.read_text(encoding="utf-8"))
        core = [c for c in expand_design.build_wastewater_cells(design) if c["block"] == "core"]
        scan = design["wastewater_scan"]
        settings = [c["wastewater_surveillance"] for c in core]
        assert {s["sampling_interval_epochs"] for s in settings} == set(
            scan["sampling_interval_epochs"],
        )
        assert {s["holding_tank_residence_hours"] for s in settings} == set(
            scan["holding_tank_residence_hours"],
        )

    def test_checked_in_manifest_matches_the_design(self) -> None:
        design = json.loads(WW_DESIGN.read_text(encoding="utf-8"))
        expected = expand_design.manifest_from_design_file(str(WW_DESIGN))
        stored = json.loads(WW_MANIFEST.read_text(encoding="utf-8"))
        assert stored == expected, "regenerate sentinel_ww_ops_scan_v1_manifest.json"
        assert stored["total_runs"] == EXPECTED_TOTAL_RUNS

    def test_legacy_design_gains_no_wastewater_cells(self) -> None:
        """Negative control: the synthetic-recovery family is untouched."""
        design = json.loads(LEGACY_DESIGN.read_text(encoding="utf-8"))
        assert expand_design.build_wastewater_cells(design) == []
        manifest = expand_design.build_manifest(design)
        assert all(
            "wastewater_cells" not in tier for tier in manifest["tiers"].values()
        )


class TestCampaignRuns:
    """Generated run specs carry the operating point they were drawn from."""

    @staticmethod
    def _runs() -> list[tuple[str, dict[str, Any]]]:
        manifest = json.loads(WW_MANIFEST.read_text(encoding="utf-8"))
        tier_id = sorted(manifest["tiers"])[0]
        return list(campaign_runner.generate_tier_runs(manifest, tier_id))

    def test_run_ids_are_unique_and_name_their_cell(self) -> None:
        runs = self._runs()
        ids = [rid for rid, _ in runs]
        assert len(set(ids)) == len(ids)
        assert len(ids) == EXPECTED_TOTAL_RUNS // 3
        assert any("_core_f1_r0p5_" in rid for rid in ids)
        assert any("_control_clinical_only_" in rid for rid in ids)

    def test_each_run_carries_its_wastewater_override_and_labels(self) -> None:
        for _rid, spec in self._runs():
            block = spec["config_overrides"]["wastewater_surveillance"]
            params = spec["campaign_parameters"]
            assert params["wastewater_enabled"] == block["enabled"]
            # The clinical-only arm names no cadence, and labels it as 0.
            assert params["ww_sampling_interval_epochs"] == block.get(
                "sampling_interval_epochs", 0,
            )
            assert params["ww_residence_hours"] == block.get(
                "holding_tank_residence_hours", 0.0,
            )
            assert params["ww_sequencing_depth"] == block["sequencing_depth"]
            assert params["ww_collection_points"] == len(block["collection_points"])

    def test_labels_span_the_scan_grid(self) -> None:
        runs = self._runs()
        params = [spec["campaign_parameters"] for _rid, spec in runs]
        assert {p["ww_sampling_interval_epochs"] for p in params} >= {1, 3, 6, 12, 24}
        assert {p["ww_sequencing_depth"] for p in params} >= {50_000, 250_000, 1_000_000}
        assert {p["ww_collection_points"] for p in params} == {1, 3}
        assert {p["wastewater_enabled"] for p in params} == {True, False}


class TestSimulationIntegration:
    """End-to-end: the simulator writes cadence-respecting rows into the bundle."""

    @staticmethod
    def _line_list(
        *,
        enabled: bool,
        interval: int,
        tag: str,
        epochs: int = 8,
    ) -> dict[str, Any]:
        from picard_framework import PicardRunSpec, ShipSimulation

        raw = copy.deepcopy(
            json.loads(
                (REPO_ROOT / "picard_framework" / "runs" / "smoke_2epoch.json").read_text(),
            ),
        )
        out = REPO_ROOT / "telemetry_buffer" / f"_tmp_ww_ops_{tag}.json"
        raw["run"]["num_epochs"] = epochs
        raw["run"]["random_seed"] = 7
        raw["run"]["sentinel_line_list"] = str(out)
        cfg = raw.setdefault("config_overrides", {})
        cfg["voyage"] = {
            "effects_enabled": True,
            "epoch_duration_hours": 1,
            "shore_exposure": {"enabled": True},
            "itinerary": [
                {
                    "day": 1,
                    "type": "port_day",
                    "port": "Cozumel",
                    "port_id": "MXCZM",
                    "disembark_fraction": 0.5,
                    "disembark_window_epochs": [0, 5],
                    "reembark_window_epochs": [6, 6],
                    "crew_shore_leave_fraction": 1.0,
                    "shore_infection_probability": 1.0,
                },
            ],
        }
        cfg["wastewater_surveillance"] = {
            "enabled": enabled,
            "sampling_interval_epochs": interval,
            "holding_tank_residence_hours": 2.0,
            "collection_points": ["aft_main", "midship", "forward"],
            "sequencing_depth": 250_000,
            "pathogen": "norovirus",
            "pathogen_id": "norwalk_gi",
        }
        spec_path = REPO_ROOT / "telemetry_buffer" / f"_tmp_ww_spec_{tag}.json"
        spec_path.write_text(json.dumps(raw), encoding="utf-8")
        try:
            spec = PicardRunSpec.from_picard_json(str(REPO_ROOT), str(spec_path))
            sim = ShipSimulation(spec, display=False)
            sim.run(n_epochs=epochs)
            sim.finalize()
            return json.loads(out.read_text(encoding="utf-8"))
        finally:
            spec_path.unlink(missing_ok=True)
            out.unlink(missing_ok=True)

    def test_cadence_controls_how_many_rows_reach_the_bundle(self) -> None:
        dense = self._line_list(enabled=True, interval=1, tag="dense")
        sparse = self._line_list(enabled=True, interval=3, tag="sparse")
        dense_epochs = sorted({s["sample_epoch"] for s in dense["wastewater_samples"]})
        sparse_epochs = sorted({s["sample_epoch"] for s in sparse["wastewater_samples"]})
        assert dense_epochs == [1, 2, 3, 4, 5, 6, 7]
        assert sparse_epochs == [3, 6]
        assert len(dense["wastewater_samples"]) == 3 * len(dense_epochs)

    def test_disabled_channel_still_yields_the_clinical_bundle(self) -> None:
        """Negative control: the 135-run clinical-only arm must stay usable."""
        payload = self._line_list(enabled=False, interval=1, tag="off")
        assert payload["wastewater_samples"] == []
        assert "clinical_cases" in payload
        assert payload["exposure_totals"]
