"""test_sanity_checker.py – sanity checker vs orchestrator config paths."""
from __future__ import annotations
import copy
import os, sys
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
from tools.sanity_checker import (
    Report, paths_from_run_config, run_checks,
    _check_config_yaml, _check_agent_classes, _check_gender_distribution,
    _check_wearable_monitoring, _check_modality_params, _check_hvac_params,
    _check_emod_progression, _check_escalation_params, _check_fred_behavior,
    _check_multi_pathogen_params, _check_microflora_params,
)


def _assert_passed(report: Report) -> None:
    msgs = [f"[{f.rule}] {f.file}: {f.message}" for f in report.errors]
    assert report.passed, f"{len(report.errors)} error(s):\n" + "\n".join(msgs)


def _load_current_cfg() -> dict:
    from crusher_labs import load_config
    return load_config()


def test_default_destroyer_and_active_profiles() -> None:
    report = run_checks(
        os.path.join(REPO_ROOT, "data", "config"),
        os.path.join(REPO_ROOT, "data", "platforms", "destroyer_baseline"),
        pathogen_file=os.path.join(REPO_ROOT, "data", "pathogens", "active_profiles.json"),
    )
    _assert_passed(report)


def test_from_config_yaml_matches_orchestrator() -> None:
    paths = paths_from_run_config(REPO_ROOT)
    report = run_checks(
        paths["config_dir"], paths["platform_dir"],
        pathogen_file=paths["pathogen_file"], cfg=paths["cfg"],
    )
    _assert_passed(report)


# ── config.yaml validation: current config passes ───────────────────────

def test_current_config_yaml_passes() -> None:
    """The shipped config.yaml must pass all config validation checks."""
    cfg = _load_current_cfg()
    report = Report()
    _check_config_yaml(cfg, report)
    _assert_passed(report)


# ── Agent class fraction checks ──────────────────────────────────────────

class TestAgentClassChecks:
    def test_fractions_sum_to_one(self) -> None:
        cfg = _load_current_cfg()
        report = Report()
        _check_agent_classes(cfg, report)
        _assert_passed(report)

    def test_fractions_not_summing_to_one_errors(self) -> None:
        cfg = {"ship_graph": {"agent_classes": [
            {"class_id": "a", "role_group": "passenger", "fraction": 0.3},
            {"class_id": "b", "role_group": "crew", "fraction": 0.3},
        ]}}
        report = Report()
        _check_agent_classes(cfg, report)
        assert not report.passed
        assert any("fractions sum to" in f.message for f in report.errors)

    def test_invalid_role_group_errors(self) -> None:
        cfg = {"ship_graph": {"agent_classes": [
            {"class_id": "a", "role_group": "civilian", "fraction": 1.0},
        ]}}
        report = Report()
        _check_agent_classes(cfg, report)
        assert not report.passed

    def test_negative_fraction_errors(self) -> None:
        cfg = {"ship_graph": {"agent_classes": [
            {"class_id": "a", "role_group": "passenger", "fraction": -0.5},
            {"class_id": "b", "role_group": "crew", "fraction": 1.5},
        ]}}
        report = Report()
        _check_agent_classes(cfg, report)
        assert not report.passed

    def test_duplicate_class_id_errors(self) -> None:
        cfg = {"ship_graph": {"agent_classes": [
            {"class_id": "dup", "role_group": "passenger", "fraction": 0.5},
            {"class_id": "dup", "role_group": "crew", "fraction": 0.5},
        ]}}
        report = Report()
        _check_agent_classes(cfg, report)
        assert any("Duplicate class_id" in f.message for f in report.errors)

    def test_zone_cross_reference_warns(self) -> None:
        cfg = {"ship_graph": {"agent_classes": [
            {"class_id": "med", "role_group": "crew", "fraction": 1.0,
             "duty_zone": "NonExistentZone"},
        ]}}
        report = Report()
        _check_agent_classes(cfg, report, zone_ids={"Bridge", "MedBay"})
        assert any("NonExistentZone" in f.message for f in report.warnings)


# ── Gender distribution checks ───────────────────────────────────────────

class TestGenderDistribution:
    def test_valid_distribution(self) -> None:
        cfg = {"ship_graph": {"gender_distribution": {"male": 0.5, "female": 0.5}}}
        report = Report()
        _check_gender_distribution(cfg, report)
        _assert_passed(report)

    def test_not_summing_to_one(self) -> None:
        cfg = {"ship_graph": {"gender_distribution": {"male": 0.3, "female": 0.3}}}
        report = Report()
        _check_gender_distribution(cfg, report)
        assert any("gender_distribution" in f.message for f in report.errors)

    def test_negative_value(self) -> None:
        cfg = {"ship_graph": {"gender_distribution": {"male": -0.1, "female": 1.1}}}
        report = Report()
        _check_gender_distribution(cfg, report)
        assert any("negative" in f.message for f in report.errors)


# ── Wearable monitoring checks ───────────────────────────────────────────

class TestWearableMonitoringChecks:
    def test_current_config_passes(self) -> None:
        cfg = _load_current_cfg()
        report = Report()
        _check_wearable_monitoring(cfg, report)
        _assert_passed(report)

    def test_duplicate_device_id(self) -> None:
        cfg = {"wearable_monitoring": {"enabled": True, "devices": [
            {"device_id": "dup", "channels": ["heart_rate"]},
            {"device_id": "dup", "channels": ["spo2"]},
        ]}}
        report = Report()
        _check_wearable_monitoring(cfg, report)
        assert any("Duplicate device_id" in f.message for f in report.errors)

    def test_noise_references_invalid_channel(self) -> None:
        cfg = {"wearable_monitoring": {"enabled": True, "devices": [
            {"device_id": "test", "channels": ["heart_rate"],
             "noise": [{"channel": "nonexistent", "sigma": 1.0}]},
        ]}}
        report = Report()
        _check_wearable_monitoring(cfg, report)
        assert any("nonexistent" in f.message for f in report.errors)

    def test_class_device_map_invalid_device(self) -> None:
        cfg = {"wearable_monitoring": {"enabled": True,
            "devices": [{"device_id": "real_device", "channels": ["hr"]}],
            "class_device_map": [{"agent_class": "default", "device_id": "ghost"}],
        }}
        report = Report()
        _check_wearable_monitoring(cfg, report)
        assert any("ghost" in f.message for f in report.errors)

    def test_negative_observation_sigma(self) -> None:
        cfg = {"wearable_monitoring": {"enabled": True, "devices": [],
            "observation_noise_sigma": -1.0}}
        report = Report()
        _check_wearable_monitoring(cfg, report)
        assert any("observation_noise_sigma" in f.message for f in report.errors)

    def test_dropout_out_of_range(self) -> None:
        cfg = {"wearable_monitoring": {"enabled": True, "devices": [],
            "sync_dropout_prob": 1.5}}
        report = Report()
        _check_wearable_monitoring(cfg, report)
        assert any("sync_dropout_prob" in f.message for f in report.errors)

    def test_negative_anomaly_threshold(self) -> None:
        cfg = {"wearable_monitoring": {"enabled": True, "devices": [],
            "anomaly_z_threshold": -2.0}}
        report = Report()
        _check_wearable_monitoring(cfg, report)
        assert any("anomaly_z_threshold" in f.message for f in report.errors)

    def test_infection_response_invalid_channel(self) -> None:
        cfg = {"wearable_monitoring": {"enabled": True, "devices": [
            {"device_id": "d1", "channels": ["heart_rate"],
             "infection_responses": [{"pathogen_category": "viral",
                "channel_responses": [{"channel": "bogus", "peak": 5.0}]}]},
        ]}}
        report = Report()
        _check_wearable_monitoring(cfg, report)
        assert any("bogus" in f.message for f in report.errors)

    def test_negative_noise_sigma(self) -> None:
        cfg = {"wearable_monitoring": {"enabled": True, "devices": [
            {"device_id": "d1", "channels": ["hr"],
             "noise": [{"channel": "hr", "sigma": -1.0}]},
        ]}}
        report = Report()
        _check_wearable_monitoring(cfg, report)
        assert not report.passed


# ── Modality parameter checks ────────────────────────────────────────────

class TestModalityParams:
    def test_current_config_passes(self) -> None:
        cfg = _load_current_cfg()
        report = Report()
        _check_modality_params(cfg, report)
        _assert_passed(report)

    def test_probability_out_of_range(self) -> None:
        cfg = {"syndromic": {"sick_call_probability": 1.5}}
        report = Report()
        _check_modality_params(cfg, report)
        assert any("sick_call_probability" in f.message for f in report.errors)

    def test_negative_cadence(self) -> None:
        cfg = {"targeted_pcr": {"cadence": -1}}
        report = Report()
        _check_modality_params(cfg, report)
        assert any("cadence" in f.message for f in report.errors)

    def test_rdt_specificity_out_of_range(self) -> None:
        cfg = {"clinical_rdt": {"specificity": 2.0}}
        report = Report()
        _check_modality_params(cfg, report)
        assert not report.passed


# ── HVAC parameter checks ────────────────────────────────────────────────

class TestHVACParams:
    def test_filter_efficiency_out_of_range(self) -> None:
        cfg = {"hvac": {"filter_efficiency": 1.5}}
        report = Report()
        _check_hvac_params(cfg, report)
        assert any("filter_efficiency" in f.message for f in report.errors)

    def test_negative_decay_rate(self) -> None:
        cfg = {"hvac": {"natural_decay_rate": -0.1}}
        report = Report()
        _check_hvac_params(cfg, report)
        assert any("natural_decay_rate" in f.message for f in report.errors)


# ── EMOD progression checks ──────────────────────────────────────────────

class TestEmodProgression:
    def test_current_config_passes(self) -> None:
        cfg = _load_current_cfg()
        report = Report()
        _check_emod_progression(cfg, report)
        _assert_passed(report)

    def test_phase_duration_count_mismatch(self) -> None:
        cfg = {"emod_progression": {
            "shedding_phases": [
                {"name": "early", "max_rate": 20.0, "sensitivity_cap": 0.3},
                {"name": "peak", "max_rate": 80.0, "sensitivity_cap": 0.95},
            ],
            "phase_durations": [3, 5, 4],
        }}
        report = Report()
        _check_emod_progression(cfg, report)
        assert any("counts must match" in f.message for f in report.errors)

    def test_negative_incubation(self) -> None:
        cfg = {"emod_progression": {"incubation_epochs": -1}}
        report = Report()
        _check_emod_progression(cfg, report)
        assert not report.passed

    def test_non_positive_duration(self) -> None:
        cfg = {"emod_progression": {
            "shedding_phases": [{"name": "a", "max_rate": 1.0, "sensitivity_cap": 0.5}],
            "phase_durations": [0],
        }}
        report = Report()
        _check_emod_progression(cfg, report)
        assert any("must be positive" in f.message for f in report.errors)


# ── Escalation parameter checks ──────────────────────────────────────────

class TestEscalationParams:
    def test_negative_threshold(self) -> None:
        cfg = {"escalation": {"syndromic_suspect_threshold": -1}}
        report = Report()
        _check_escalation_params(cfg, report)
        assert not report.passed

    def test_non_positive_ct(self) -> None:
        cfg = {"escalation": {"pcr_confirm_ct_threshold": 0}}
        report = Report()
        _check_escalation_params(cfg, report)
        assert not report.passed


# ── FRED behavior checks ─────────────────────────────────────────────────

class TestFredBehavior:
    def test_compliance_out_of_range(self) -> None:
        cfg = {"fred_behavior": {"quarantine_compliance": 1.5}}
        report = Report()
        _check_fred_behavior(cfg, report)
        assert not report.passed

    def test_noise_probability_out_of_range(self) -> None:
        cfg = {"fred_behavior": {"healthy_noise_categories": [
            {"reason": "test", "probability": 2.0},
        ]}}
        report = Report()
        _check_fred_behavior(cfg, report)
        assert not report.passed


# ── Multi-pathogen checks ────────────────────────────────────────────────

class TestMultiPathogenParams:
    def test_immunocompromised_fraction_out_of_range(self) -> None:
        cfg = {"multi_pathogen": {"immunocompromised_fraction": 1.5}}
        report = Report()
        _check_multi_pathogen_params(cfg, report)
        assert not report.passed

    def test_negative_multiplier(self) -> None:
        cfg = {"multi_pathogen": {"immunocompromised_multiplier": -1}}
        report = Report()
        _check_multi_pathogen_params(cfg, report)
        assert not report.passed


# ── Microflora checks ────────────────────────────────────────────────────

class TestMicrofloraParams:
    def test_negative_shed_mass(self) -> None:
        cfg = {"microflora": {"disrupted_shed_mass": -10}}
        report = Report()
        _check_microflora_params(cfg, report)
        assert not report.passed

    def test_graywater_zone_cross_reference(self) -> None:
        cfg = {"microflora": {"graywater_zones": ["Nonexistent_Zone"]}}
        report = Report()
        _check_microflora_params(cfg, report, zone_ids={"Bridge", "MedBay"})
        assert any("Nonexistent_Zone" in f.message for f in report.warnings)


# ── Integration: --from-config now validates config.yaml ─────────────────

def test_from_config_includes_config_yaml_validation() -> None:
    """Verify that paths_from_run_config returns cfg and run_checks uses it."""
    paths = paths_from_run_config(REPO_ROOT)
    assert "cfg" in paths, "paths_from_run_config must return 'cfg' key"
    assert isinstance(paths["cfg"], dict)
    report = run_checks(
        paths["config_dir"], paths["platform_dir"],
        pathogen_file=paths["pathogen_file"], cfg=paths["cfg"],
    )
    _assert_passed(report)
