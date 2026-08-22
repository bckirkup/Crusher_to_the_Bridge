"""Unit tests for the paired-arm incubation sensitivity harness.

The harness itself runs whole voyages, so these tests exercise the parts that
decide whether the experiment is valid: that exactly one thing differs between
arms, that the extract layout the fleet fitter consumes is well formed, and
that the comparison arithmetic responds to its inputs.
"""
from __future__ import annotations

import json
import math
import os

import pytest

from picard_framework.analysis import incubation_arms as ia
from picard_framework.pathogen_overrides import apply_pathogen_overrides

MANIFEST = {
    "platform": "classic_cruise_1900",
    "default_epochs": 168,
    "embarkation_date": "2026-01-10",
    "defaults": {"dose_adjustment": 10.6, "density_exponent": 0.75},
    "surveillance_configs": {"syndromic": {"diagnostic_cascade": {"enabled": False}}},
    "pathogen_configs": {
        "norovirus": {
            "bundle": "active_profiles",
            "pathogen_id": "norwalk_gi",
            "overrides": {"remove": ["sars_cov2_resp"]},
        },
    },
    "tiers": {
        "sr_uniform_high_fleet_crossed": {
            "hazard_profile": "uniform_high",
            "fleet_config": "fleet_crossed",
            "shore_exposure": {
                "port_hazards": {"MXCZM": 0.001, "MXCTM": 0.001, "KYGEC": 0.001},
            },
        },
        "sr_one_hot_single": {
            "hazard_profile": "one_hot",
            "fleet_config": "single",
            "shore_exposure": {
                "port_hazards": {"MXCZM": 0.001, "MXCTM": 0.0001, "KYGEC": 0.0001},
            },
        },
    },
    "itinerary_templates": {
        "standard": [
            {"day": 1, "type": "embarkation", "port_id": "USMIA"},
            {"day": 2, "type": "port_day", "port_id": "MXCZM"},
            {"day": 3, "type": "disembarkation", "port_id": "USMIA"},
        ],
    },
}

PROFILES = {
    "norwalk_gi": {
        "pathogen_id": "norwalk_gi",
        "dose_adjustment": 1.0,
        "incubation": {"median_days": 1.2, "dispersion": 1.56},
    },
    "sars_cov2_resp": {"pathogen_id": "sars_cov2_resp"},
}


def _observations(pairs, *, epoch_hours=1.0):
    cases = [
        {"person_id": pid, "onset_epoch": onset, "hours_ashore": {}}
        for pid, _exposure, onset in pairs
    ]
    intro = [
        {"person_id": pid, "epoch": exposure, "port_id": "MXCZM"}
        for pid, exposure, _onset in pairs
    ]
    return {
        "epoch_duration_hours": epoch_hours,
        "clinical_cases": cases,
        "truth_introductions": intro,
    }


def _recovery_row(**kwargs):
    row = {
        "cell_id": "uniform_high__fleet_crossed__R1p0",
        "port_id": "MXCZM",
        "lambda_true": "0.001",
        "lambda_mean": "0.001",
        "lambda_q05": "0.0005",
        "lambda_q95": "0.0015",
        "lambda_covered": "True",
    }
    row.update({k: str(v) for k, v in kwargs.items()})
    return row


class TestArmSwitch:
    """The two arms must differ in the incubation block and nothing else."""

    def test_fixed_arm_strips_the_incubation_block(self):
        over = ia.arm_pathogen_overrides(
            arm=ia.ARM_FIXED,
            profiles=PROFILES,
            pathogen_id="norwalk_gi",
            base_overrides={"remove": ["sars_cov2_resp"]},
            dose_adjustment=10.6,
            n_init=0,
        )
        resolved = apply_pathogen_overrides(PROFILES, over)
        assert "incubation" not in resolved["norwalk_gi"]

    def test_distribution_arm_keeps_the_incubation_block(self):
        over = ia.arm_pathogen_overrides(
            arm=ia.ARM_DISTRIBUTION,
            profiles=PROFILES,
            pathogen_id="norwalk_gi",
            base_overrides={"remove": ["sars_cov2_resp"]},
            dose_adjustment=10.6,
            n_init=0,
        )
        resolved = apply_pathogen_overrides(PROFILES, over)
        assert resolved["norwalk_gi"]["incubation"]["median_days"] == pytest.approx(1.2)

    def test_arms_differ_only_in_incubation(self):
        kwargs = {
            "profiles": PROFILES,
            "pathogen_id": "norwalk_gi",
            "base_overrides": {"remove": ["sars_cov2_resp"]},
            "dose_adjustment": 10.6,
            "n_init": 0,
        }
        dist = apply_pathogen_overrides(
            PROFILES, ia.arm_pathogen_overrides(arm=ia.ARM_DISTRIBUTION, **kwargs),
        )["norwalk_gi"]
        fixed = apply_pathogen_overrides(
            PROFILES, ia.arm_pathogen_overrides(arm=ia.ARM_FIXED, **kwargs),
        )["norwalk_gi"]
        assert set(dist) - set(fixed) == {"incubation"}
        assert {k: v for k, v in dist.items() if k != "incubation"} == fixed

    def test_both_arms_carry_the_same_dose_and_seeding(self):
        kwargs = {
            "profiles": PROFILES,
            "pathogen_id": "norwalk_gi",
            "base_overrides": None,
            "dose_adjustment": 10.6,
            "n_init": 3,
        }
        for arm in ia.ARMS:
            resolved = apply_pathogen_overrides(
                PROFILES, ia.arm_pathogen_overrides(arm=arm, **kwargs),
            )["norwalk_gi"]
            assert resolved["dose_adjustment"] == pytest.approx(10.6)
            assert resolved["initial_infected"] == 3

    def test_fixed_arm_rejects_a_profile_without_incubation(self):
        with pytest.raises(SystemExit, match="no-op"):
            ia.arm_pathogen_overrides(
                arm=ia.ARM_FIXED,
                profiles={"p": {"pathogen_id": "p"}},
                pathogen_id="p",
                base_overrides=None,
                dose_adjustment=1.0,
                n_init=0,
            )

    def test_unknown_arm_is_rejected(self):
        with pytest.raises(SystemExit, match="unknown arm"):
            ia.arm_pathogen_overrides(
                arm="whatever",
                profiles=PROFILES,
                pathogen_id="norwalk_gi",
                base_overrides=None,
                dose_adjustment=1.0,
                n_init=0,
            )

    def test_base_overrides_are_not_mutated(self):
        base = {"remove": ["sars_cov2_resp"]}
        ia.arm_pathogen_overrides(
            arm=ia.ARM_FIXED,
            profiles=PROFILES,
            pathogen_id="norwalk_gi",
            base_overrides=base,
            dose_adjustment=1.0,
            n_init=0,
        )
        assert base == {"remove": ["sars_cov2_resp"]}

    def test_strip_incubation_leaves_the_source_untouched(self):
        profile = dict(PROFILES["norwalk_gi"])
        stripped = ia.strip_incubation(profile)
        assert "incubation" in profile
        assert "incubation" not in stripped


class TestDesignResolution:
    """Held factors come from the campaign manifest, not from code."""

    def test_hazards_come_from_the_named_profile(self):
        assert ia.hazards_for_profile(MANIFEST, "one_hot") == {
            "MXCZM": 0.001,
            "MXCTM": 0.0001,
            "KYGEC": 0.0001,
        }

    def test_different_hazard_profiles_give_different_hazards(self):
        assert ia.hazards_for_profile(MANIFEST, "uniform_high") != (
            ia.hazards_for_profile(MANIFEST, "one_hot")
        )

    def test_unknown_hazard_profile_is_rejected(self):
        with pytest.raises(SystemExit, match="hazard profile"):
            ia.hazards_for_profile(MANIFEST, "not_a_profile")

    def test_unknown_pathogen_config_is_rejected(self):
        with pytest.raises(SystemExit, match="pathogen config"):
            ia._pathogen_config(MANIFEST, "influenza")

    def test_pathogen_config_normalizes_a_list_of_removals(self):
        manifest = {
            "pathogen_configs": {
                "norovirus": {"pathogen_id": "norwalk_gi", "overrides": ["x"]},
            },
        }
        bundle, pid, over = ia._pathogen_config(manifest, "norovirus")
        assert (bundle, pid) == ("active_profiles", "norwalk_gi")
        assert over == {"remove": ["x"]}

    def test_run_ids_are_unique_per_arm_itinerary_and_seed(self):
        ids = {
            ia.voyage_run_id(arm, variant, seed)
            for arm in ia.ARMS
            for variant in ("standard", "reversed")
            for seed in (300, 301)
        }
        assert len(ids) == 8

    def test_run_spec_holds_the_design_and_names_the_arm(self):
        design = ia.ArmsDesign(seeds=(300,), itineraries=("standard",))
        spec = ia.run_spec_payload(
            design,
            manifest=MANIFEST,
            arm=ia.ARM_FIXED,
            variant="standard",
            seed=300,
            run_id="fixed_onset__standard__s300",
            voyage={"total_epochs": 168},
            pathogen_overrides={"remove": []},
            bundle="active_profiles",
            line_list_path="out/line_list.json",
        )
        assert spec["catalog"]["platform_id"] == design.platform
        assert spec["config_overrides"]["ship_graph"]["num_agents"] == design.num_agents
        assert spec["config_overrides"]["diagnostic_cascade"] == {"enabled": False}
        assert spec["run"]["random_seed"] == 300
        assert ia.ARM_FIXED in spec["notes"]

    def test_run_spec_carries_the_manifest_density_exponent(self):
        spec = ia.run_spec_payload(
            ia.ArmsDesign(),
            manifest=MANIFEST,
            arm=ia.ARM_DISTRIBUTION,
            variant="standard",
            seed=300,
            run_id="rid",
            voyage={},
            pathogen_overrides={},
            bundle="active_profiles",
            line_list_path="line_list.json",
        )
        exponent = spec["config_overrides"]["transmission"]["density_dependent"]
        assert exponent["exponent"] == pytest.approx(0.75)

    def test_missing_surveillance_config_is_rejected(self):
        with pytest.raises(SystemExit, match="surveillance config"):
            ia.run_spec_payload(
                ia.ArmsDesign(surveillance="wearable"),
                manifest=MANIFEST,
                arm=ia.ARM_DISTRIBUTION,
                variant="standard",
                seed=300,
                run_id="rid",
                voyage={},
                pathogen_overrides={},
                bundle="active_profiles",
                line_list_path="line_list.json",
            )

    def test_meta_records_the_cell_the_fitter_scores_against(self):
        params = ia.voyage_params(
            ia.ArmsDesign(),
            arm=ia.ARM_DISTRIBUTION,
            variant="reversed",
            seed=307,
            run_id="rid",
            hazards={"MXCZM": 0.001},
            dose_adjustment=10.6,
            n_init=0,
        )
        assert params["hazard_profile"] == ia.DEFAULT_HAZARD_PROFILE
        assert params["fleet_config"] == ia.DEFAULT_FLEET_CONFIG
        assert params["port_hazards"] == {"MXCZM": 0.001}
        assert params["R_onboard"] == pytest.approx(1.0)
        assert params["arm"] == ia.ARM_DISTRIBUTION


class TestRealizedOnset:
    """Realized incubation is the arm's observable signature."""

    def test_onset_minus_exposure_in_hours(self):
        rows = ia.realized_incubations(_observations([("1", 50, 74)]))
        assert rows[0]["incubation_hours"] == pytest.approx(24.0)
        assert rows[0]["port_id"] == "MXCZM"

    def test_epoch_duration_scales_the_span(self):
        rows = ia.realized_incubations(
            _observations([("1", 50, 74)], epoch_hours=2.0),
        )
        assert rows[0]["incubation_hours"] == pytest.approx(48.0)

    def test_cases_without_a_known_introduction_are_dropped(self):
        obs = _observations([("1", 50, 74)])
        obs["clinical_cases"].append({"person_id": "9", "onset_epoch": 80})
        assert len(ia.realized_incubations(obs)) == 1

    def test_non_positive_spans_are_dropped(self):
        assert ia.realized_incubations(_observations([("1", 50, 50)])) == []

    def test_summary_reports_median_and_iqr(self):
        rows = [{"incubation_hours": h} for h in (12, 20, 28, 36, 44)]
        summary = ia.onset_summary(rows)
        assert summary["n"] == 5
        assert summary["median_hours"] == pytest.approx(28.0)
        assert summary["iqr_hours"] == pytest.approx(16.0)

    def test_a_tighter_spread_yields_a_smaller_iqr(self):
        wide = ia.onset_summary([{"incubation_hours": h} for h in (4, 16, 28, 40, 52)])
        tight = ia.onset_summary([{"incubation_hours": h} for h in (26, 27, 28, 29, 30)])
        assert tight["iqr_hours"] < wide["iqr_hours"]
        assert tight["median_hours"] == pytest.approx(wide["median_hours"])

    def test_empty_summary_is_not_an_error(self):
        summary = ia.onset_summary([])
        assert summary["n"] == 0
        assert math.isnan(summary["median_hours"])

    def test_too_few_points_for_an_iqr(self):
        summary = ia.onset_summary([{"incubation_hours": 24.0}])
        assert summary["median_hours"] == pytest.approx(24.0)
        assert math.isnan(summary["iqr_hours"])


class TestComparison:
    """The comparison differences the two arms rather than judging one."""

    def test_rows_are_joined_on_cell_and_port(self):
        dist = [_recovery_row(port_id="MXCZM"), _recovery_row(port_id="KYGEC")]
        fixed = [_recovery_row(port_id="MXCZM")]
        rows = ia.compare_rows(dist, fixed)
        assert [r["port_id"] for r in rows] == ["MXCZM"]

    def test_relative_bias_is_signed_and_scaled_by_truth(self):
        rows = ia.compare_rows(
            [_recovery_row(lambda_mean=0.0012)],
            [_recovery_row(lambda_mean=0.0008)],
        )
        assert rows[0]["rel_bias_distribution"] == pytest.approx(0.2)
        assert rows[0]["rel_bias_fixed_onset"] == pytest.approx(-0.2)

    def test_width_ratio_below_one_means_the_new_arm_is_tighter(self):
        rows = ia.compare_rows(
            [_recovery_row(lambda_q05=0.0009, lambda_q95=0.0011)],
            [_recovery_row(lambda_q05=0.0005, lambda_q95=0.0015)],
        )
        assert rows[0]["width_ratio"] == pytest.approx(0.2)

    def test_width_ratio_is_one_when_both_arms_agree(self):
        rows = ia.compare_rows([_recovery_row()], [_recovery_row()])
        assert rows[0]["width_ratio"] == pytest.approx(1.0)

    def test_coverage_is_read_per_arm(self):
        rows = ia.compare_rows(
            [_recovery_row(lambda_covered="True")],
            [_recovery_row(lambda_covered="False")],
        )
        counts = ia.coverage_counts(rows)
        assert counts == {
            "n": 1,
            "covered_distribution": 1,
            "covered_fixed_onset": 0,
        }

    def test_zero_truth_gives_no_relative_bias(self):
        rows = ia.compare_rows(
            [_recovery_row(port_id="USMIA", lambda_true=0.0)],
            [_recovery_row(port_id="USMIA", lambda_true=0.0)],
        )
        assert math.isnan(rows[0]["rel_bias_distribution"])

    def test_report_names_both_arms_and_their_onsets(self):
        rows = ia.compare_rows([_recovery_row()], [_recovery_row()])
        lines = ia._report_lines(
            rows,
            {
                ia.ARM_DISTRIBUTION: {"n": 40, "median_hours": 28.0, "iqr_hours": 12.0},
                ia.ARM_FIXED: {"n": 40, "median_hours": 24.0, "iqr_hours": 0.0},
            },
        )
        text = "\n".join(lines)
        assert "| distribution | 40 | 28.0 | 12.0 |" in text
        assert "| fixed_onset | 40 | 24.0 | 0.0 |" in text
        assert "λ_p covered (fixed onset): 1/1" in text


class TestExtractLayout:
    """The per-arm output must be readable by the existing fleet fitter."""

    def _record(self, run_id="distribution__standard__s300"):
        return {
            "run_id": run_id,
            "params": ia.voyage_params(
                ia.ArmsDesign(),
                arm=ia.ARM_DISTRIBUTION,
                variant="standard",
                seed=300,
                run_id=run_id,
                hazards={"MXCZM": 0.001},
                dose_adjustment=10.6,
                n_init=0,
            ),
            "itinerary": {"schema_version": "1.0", "voyage": {"itinerary": []}},
            "observations": _observations([("1", 50, 74)]),
        }

    def test_voyage_files_are_written_where_cells_from_out_looks(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        arm_dir = ia.ensure_out_dir(os.path.join("out", ia.ARM_DISTRIBUTION))
        record = self._record()
        ia.write_voyage_record(arm_dir, record)
        ia._write_arm_index(
            arm_dir,
            ia.ArmsDesign(),
            [ia._voyage_entry(record)],
            list(ia.realized_incubations(record["observations"])),
        )
        cells = ia.cells_from_out(arm_dir)
        assert len(cells) == 1
        assert cells[0]["port_hazards"] == {"MXCZM": 0.001}
        assert cells[0]["n_voyages"] == 1
        assert os.path.isfile(cells[0]["manifest"])

    def test_onset_summary_is_written_next_to_the_cells(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        arm_dir = ia.ensure_out_dir(os.path.join("out", ia.ARM_DISTRIBUTION))
        record = self._record()
        ia.write_voyage_record(arm_dir, record)
        ia._write_arm_index(
            arm_dir,
            ia.ArmsDesign(),
            [ia._voyage_entry(record)],
            [{"arm": ia.ARM_DISTRIBUTION, "run_id": "r", "incubation_hours": 24.0}],
        )
        with open(os.path.join(arm_dir, "onset_summary.json"), encoding="utf-8") as fh:
            summary = json.load(fh)
        assert summary["n"] == 1
        assert summary["hazard_profile"] == ia.DEFAULT_HAZARD_PROFILE
        assert summary["n_voyages"] == 1

    def test_two_itineraries_group_into_one_fitted_cell(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        arm_dir = ia.ensure_out_dir(os.path.join("out", ia.ARM_DISTRIBUTION))
        records = [
            self._record("distribution__standard__s300"),
            self._record("distribution__reversed__s300"),
        ]
        for record in records:
            ia.write_voyage_record(arm_dir, record)
        ia._write_arm_index(
            arm_dir,
            ia.ArmsDesign(),
            [ia._voyage_entry(r) for r in records],
            [],
        )
        cells = ia.cells_from_out(arm_dir)
        assert len(cells) == 1
        assert cells[0]["n_voyages"] == 2


class _FakeSim:
    """Stand-in for ShipSimulation that emits a line list and nothing else."""

    line_list_path = ""
    cases = 1

    def __init__(self, run, display=False):
        self.run_spec = run
        self.display = display

    def run(self):
        payload = {
            "schema_version": "1.0.0",
            "voyage_id": "ignored",
            "ship_id": "ignored",
            "epoch_duration_hours": 1.0,
            "clinical_cases": [
                {
                    "person_id": str(i),
                    "onset_epoch": 70 + i,
                    "hours_ashore": {"MXCZM": 8.0, "miami": 2.0},
                }
                for i in range(type(self).cases)
            ],
            "exposure_totals": {"MXCZM": {"person_hours_passenger": 900.0}},
            "truth_introductions": [
                {"person_id": str(i), "epoch": 50, "port_id": "MXCZM"}
                for i in range(type(self).cases)
            ],
        }
        with open(type(self).line_list_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)

    def finalize(self, display=False):
        self.finalized = True


class _FakeRunSpec:
    @staticmethod
    def from_picard_json(root, path):
        with open(path, encoding="utf-8") as fh:
            spec = json.load(fh)
        _FakeSim.line_list_path = spec["run"]["sentinel_line_list"]
        return spec


@pytest.fixture
def stub_simulator(monkeypatch):
    """Replace the ABM with a stub so the harness itself can be tested."""
    monkeypatch.setattr(ia, "PicardRunSpec", _FakeRunSpec)
    monkeypatch.setattr(ia, "ShipSimulation", _FakeSim)
    return _FakeSim


class TestSimulateArm:
    """Driving one arm end to end, with the ABM stubbed out."""

    def _arm(self, tmp_path, monkeypatch, **kwargs):
        monkeypatch.chdir(tmp_path)
        design = ia.ArmsDesign(itineraries=("standard",), seeds=(300,), epochs=24)
        return ia.simulate_arm(design, ia.ARM_DISTRIBUTION, "out", **kwargs)

    def test_one_voyage_produces_a_fittable_cell(
        self, tmp_path, monkeypatch, stub_simulator,
    ):
        arm_dir = self._arm(tmp_path, monkeypatch)
        cells = ia.cells_from_out(arm_dir)
        assert [c["n_voyages"] for c in cells] == [1]
        assert cells[0]["port_hazards"] == {
            "MXCZM": 0.001, "MXCTM": 0.001, "KYGEC": 0.001,
        }

    def test_home_port_hours_are_filtered_out_of_the_observations(
        self, tmp_path, monkeypatch, stub_simulator,
    ):
        arm_dir = self._arm(tmp_path, monkeypatch)
        run_id = ia.voyage_run_id(ia.ARM_DISTRIBUTION, "standard", 300)
        obs = ia.read_json(
            os.path.join(arm_dir, "voyages", run_id, "observations.json"),
        )
        assert set(obs["clinical_cases"][0]["hours_ashore"]) == {"MXCZM"}
        assert obs["voyage_id"] == run_id

    def test_realized_onsets_are_recorded_for_the_arm(
        self, tmp_path, monkeypatch, stub_simulator,
    ):
        arm_dir = self._arm(tmp_path, monkeypatch)
        summary = ia.read_json(os.path.join(arm_dir, "onset_summary.json"))
        assert summary["n"] == 1
        assert summary["median_hours"] == pytest.approx(20.0)

    def test_cached_voyages_are_reused_instead_of_resimulated(
        self, tmp_path, monkeypatch, stub_simulator,
    ):
        arm_dir = self._arm(tmp_path, monkeypatch)
        calls = []
        monkeypatch.setattr(
            ia,
            "simulate_voyage",
            lambda *a, **k: calls.append(k) or pytest.fail("resimulated"),
        )
        design = ia.ArmsDesign(itineraries=("standard",), seeds=(300,), epochs=24)
        again = ia.simulate_arm(design, ia.ARM_DISTRIBUTION, "out")
        assert again == arm_dir
        assert calls == []

    def test_rerun_ignores_the_cache(self, tmp_path, monkeypatch, stub_simulator):
        self._arm(tmp_path, monkeypatch)
        stub_simulator.cases = 3
        try:
            arm_dir = self._arm(tmp_path, monkeypatch, skip_existing=False)
            summary = ia.read_json(os.path.join(arm_dir, "onset_summary.json"))
        finally:
            stub_simulator.cases = 1
        assert summary["n"] == 3

    def test_the_spec_written_for_the_fixed_arm_strips_incubation(
        self, tmp_path, monkeypatch, stub_simulator,
    ):
        monkeypatch.chdir(tmp_path)
        design = ia.ArmsDesign(itineraries=("standard",), seeds=(300,), epochs=24)
        arm_dir = ia.simulate_arm(design, ia.ARM_FIXED, "out")
        run_id = ia.voyage_run_id(ia.ARM_FIXED, "standard", 300)
        spec = ia.read_json(os.path.join(arm_dir, "voyages", run_id, "run_spec.json"))
        added = spec["pathogen_overrides"]["add"]
        assert [entry["pathogen_id"] for entry in added] == ["norwalk_gi"]
        assert "incubation" not in added[0]


class TestFitAndCompareStages:
    """Fitting and differencing, with the sampler stubbed out."""

    def _arm_with_cell(self, tmp_path, arm):
        arm_dir = ia.ensure_out_dir(os.path.join("out", arm))
        record = {
            "run_id": f"{arm}__standard__s300",
            "params": ia.voyage_params(
                ia.ArmsDesign(),
                arm=arm,
                variant="standard",
                seed=300,
                run_id=f"{arm}__standard__s300",
                hazards={"MXCZM": 0.001},
                dose_adjustment=10.6,
                n_init=0,
            ),
            "itinerary": {"schema_version": "1.0", "voyage": {"itinerary": []}},
            "observations": _observations([("1", 50, 74)]),
        }
        ia.write_voyage_record(arm_dir, record)
        ia._write_arm_index(arm_dir, ia.ArmsDesign(), [ia._voyage_entry(record)], [])
        return arm_dir

    def test_fit_arm_writes_a_recovery_table(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        arm_dir = self._arm_with_cell(tmp_path, ia.ARM_DISTRIBUTION)
        monkeypatch.setattr(ia, "fit_cell", lambda cell, **kw: {"status": "ok"})
        rows = ia.fit_arm(
            arm_dir,
            engine="numpy",
            sampler=ia.SamplerOptions(chains=1, iter_sampling=1, iter_warmup=1),
        )
        assert [r["port_id"] for r in rows] == ["MXCZM"]
        assert ia.read_recovery(arm_dir)[0]["lambda_true"] == "0.001"

    def test_compare_stage_differences_both_arms(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        for arm in ia.ARMS:
            arm_dir = self._arm_with_cell(tmp_path, arm)
            monkeypatch.setattr(ia, "fit_cell", lambda cell, **kw: {"status": "ok"})
            ia.fit_arm(
                arm_dir,
                engine="numpy",
                sampler=ia.SamplerOptions(chains=1, iter_sampling=1, iter_warmup=1),
            )
        assert ia.main(["--out", "out", "compare"]) == 0
        report = os.path.join("out", "arms_report.md")
        assert os.path.isfile(report)
        assert os.path.isfile(os.path.join("out", "arms_comparison.csv"))

    def test_main_dispatches_the_simulate_stage(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        seen: list[str] = []
        monkeypatch.setattr(
            ia,
            "simulate_arm",
            lambda design, arm, out, **kw: seen.append(arm) or out,
        )
        code = ia.main(
            ["--out", "out", "simulate", "--itinerary", "standard", "--seed", "300"],
        )
        assert code == 0
        assert seen == list(ia.ARMS)

    def test_main_dispatches_the_fit_stage_per_arm(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        seen: list[str] = []
        monkeypatch.setattr(
            ia,
            "fit_arm",
            lambda arm_dir, **kw: seen.append(os.path.basename(arm_dir)) or [],
        )
        assert ia.main(["--out", "out", "fit", "--engine", "numpy"]) == 0
        assert seen == list(ia.ARMS)


class TestCatalogInputs:
    """The harness reads the shipped manifest and bundle, not private copies."""

    def test_manifest_declares_the_default_cell(self):
        manifest = ia.load_manifest()
        assert ia.hazards_for_profile(manifest, ia.DEFAULT_HAZARD_PROFILE)
        bundle, pathogen_id, _over = ia._pathogen_config(manifest, "norovirus")
        assert (bundle, pathogen_id) == ("active_profiles", "norwalk_gi")

    def test_shipped_profile_carries_the_incubation_block(self):
        profiles = ia.bundle_profiles("active_profiles")
        assert "incubation" in profiles["norwalk_gi"]


class TestDefensiveEdges:
    """Malformed inputs are rejected or dropped, never silently coerced."""

    def test_a_bundle_without_the_pathogen_is_rejected(self):
        with pytest.raises(SystemExit):
            ia.arm_pathogen_overrides(
                arm=ia.ARM_FIXED,
                profiles={"other": {"pathogen_id": "other"}},
                pathogen_id="norwalk_gi",
                base_overrides=None,
                dose_adjustment=10.6,
                n_init=0,
            )

    def test_non_dict_clinical_cases_are_dropped(self):
        obs = _observations([("1", 50, 74)])
        obs["clinical_cases"].append("not a case")
        assert len(ia.realized_incubations(obs)) == 1

    def test_unparseable_recovery_fields_become_nan(self):
        rows = ia.compare_rows(
            [_recovery_row(lambda_true="not a number")],
            [_recovery_row()],
        )
        assert math.isnan(rows[0]["lambda_true"])

    def test_auto_engine_falls_back_when_cmdstan_is_absent(self, monkeypatch):
        monkeypatch.setattr(ia, "cmdstan_available", lambda: False)
        args = ia.build_parser().parse_args(["--out", "out", "fit"])
        engine, sampler = ia._sampler_from_args(args)
        assert engine == "numpy"
        assert sampler.iter_warmup == 1600


class TestCli:
    """Stage selection and sampler defaults."""

    def test_simulate_accepts_repeatable_design_axes(self):
        args = ia.build_parser().parse_args(
            [
                "--out", "out",
                "simulate",
                "--arm", ia.ARM_FIXED,
                "--itinerary", "standard",
                "--itinerary", "reversed",
                "--seed", "300",
                "--seed", "301",
            ],
        )
        design = ia._design_from_args(args)
        assert args.arm == [ia.ARM_FIXED]
        assert design.itineraries == ("standard", "reversed")
        assert design.seeds == (300, 301)

    def test_design_falls_back_to_the_documented_defaults(self):
        args = ia.build_parser().parse_args(["simulate"])
        design = ia._design_from_args(args)
        assert design.itineraries == ia.DEFAULT_ITINERARIES
        assert design.seeds == ia.DEFAULT_SEEDS

    def test_fit_defaults_to_the_long_chains(self):
        args = ia.build_parser().parse_args(["fit"])
        _engine, sampler = ia._sampler_from_args(args)
        assert sampler.iter_sampling == 400
        assert sampler.iter_warmup == 1600

    def test_an_unknown_arm_is_rejected_by_the_cli(self):
        with pytest.raises(SystemExit):
            ia.build_parser().parse_args(["simulate", "--arm", "nope"])
