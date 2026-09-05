"""Tests for mega_cruise_campaign runner (generation + smoke)."""

from __future__ import annotations

import json
import shutil
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from typing import Any  # noqa: E402

from picard_framework.pathogen_overrides import (  # noqa: E402
    load_pathogen_bundle,
)
from picard_framework.runs.mega_cruise_campaign.campaign_runner import (  # noqa: E402
    ShardBundle,
    _campaign_parser,
    _ensure_clock_arm,
    clear_failed_artifacts,
    compute_derived_metrics,
    extract_timeseries,
    failed_runs,
    generate_tier_runs,
    load_manifest,
    main,
    make_picard_spec,
    mark_failed,
    parameters_from_spec,
    resolve_tier_ids,
    run_simulation_subprocess,
)

CAMPAIGN = REPO_ROOT / "picard_framework" / "runs" / "mega_cruise_campaign"
CALIBRATION_MANIFEST = CAMPAIGN / "calibration_manifest_v1.json"
CLOCK_ARM_C1_MANIFEST = CAMPAIGN / "clock_arm_c1_v1_manifest.json"
SINGLE_DOSE_HOURS_MANIFEST = CAMPAIGN / "c1_single_dose_hours_v1_manifest.json"
REPORTED_CASE_REFIT_MANIFEST = CAMPAIGN / "c1_reported_case_refit_v1_manifest.json"

STANDARD_TIERS = [
    "t1_pathogen_baselines",
    "t2_hvac_sweep",
    "t3_surveillance_sweep",
    "t4_full_factorial",
    "t5_multi_pathogen",
    "t6_dose_response",
    "t7_compliance",
    "t8_wearables",
    "t9_slow_pathogens",
]


def test_manifest_loads_and_has_expected_tiers() -> None:
    manifest = load_manifest(CAMPAIGN / "campaign_manifest.json")
    assert manifest["campaign"] == "mega_cruise_17780"
    # t1–t11 + t15/t16 (outbreak-response architecture sweeps); t12–t14 optional
    assert len(manifest["tiers"]) >= 13
    assert "t15_sop_threshold_sweep" in manifest["tiers"]
    assert "t16_reluctant_fraction_sweep" in manifest["tiers"]
    assert "norovirus" in manifest["pathogen_configs"]
    assert manifest["pathogen_configs"]["norovirus"]["pathogen_id"] == "norwalk_gi"


def test_none_and_syndromic_surveillance_configs_diverge() -> None:
    """Campaign 'none' must disable sick-call surveillance; 'syndromic' must not."""
    manifest = load_manifest()
    none_cfg = manifest["surveillance_configs"]["none"]
    syn_cfg = manifest["surveillance_configs"]["syndromic"]
    assert none_cfg != syn_cfg
    assert none_cfg["diagnostic_cascade"]["enabled"] is False
    assert syn_cfg["diagnostic_cascade"]["enabled"] is False
    assert none_cfg["syndromic"]["sick_call_probability"] == 0.0
    assert none_cfg["syndromic"]["background_noise_rate"] == 0.0
    assert none_cfg["fred_behavior"]["healthy_noise_categories"] == []
    # Soft none keeps observation / wearables / VSP confinement on (defaults).
    assert none_cfg.get("observation", {}).get("enabled", True) is True
    assert "wearable_monitoring" not in none_cfg
    assert "counter_confinement_enabled" not in none_cfg.get("ship_graph", {})
    assert "syndromic" not in syn_cfg

    runs = list(generate_tier_runs(manifest, "t3_surveillance_sweep"))
    none_spec = next(s for rid, s in runs if "_none_" in rid)
    syn_spec = next(s for rid, s in runs if "_syndromic_" in rid)
    none_over = none_spec["config_overrides"]
    syn_over = syn_spec["config_overrides"]
    assert none_over["syndromic"]["sick_call_probability"] == 0.0
    assert none_over["fred_behavior"]["healthy_noise_categories"] == []
    assert "sick_call_probability" not in syn_over.get("syndromic", {})
    assert none_over != syn_over


def test_none_preset_ladder_diverges() -> None:
    """none / none_env / none_true must differ on observation and confinement switches."""
    manifest = load_manifest()
    configs = manifest["surveillance_configs"]
    none = configs["none"]
    none_env = configs["none_env"]
    none_true = configs["none_true"]

    assert none != none_env != none_true
    assert none_env["observation"]["enabled"] is False
    assert none_env.get("wearable_monitoring", {}).get("enabled", True) is True
    assert none_env.get("ship_graph", {}).get("counter_confinement_enabled", True) is True

    assert none_true["observation"]["enabled"] is False
    assert none_true["wearable_monitoring"]["enabled"] is False
    assert none_true["ship_graph"]["counter_confinement_enabled"] is False

    # Soft none still only silences sick-call / cascade (legacy campaign shape).
    assert "observation" not in none or none["observation"].get("enabled", True) is True
    assert none["syndromic"]["sick_call_probability"] == 0.0
    assert none_env["syndromic"]["sick_call_probability"] == 0.0
    assert none_true["syndromic"]["sick_call_probability"] == 0.0


def test_resolve_tier_short_prefix() -> None:
    manifest = load_manifest()
    assert resolve_tier_ids(manifest, "t1") == ["t1_pathogen_baselines"]
    assert resolve_tier_ids(manifest, "t10") == ["t10_population_size"]


def test_dry_run_counts_match_readme_table() -> None:
    manifest = load_manifest()
    expected = {
        "t1_pathogen_baselines": 300,
        "t2_hvac_sweep": 4500,
        "t3_surveillance_sweep": 1200,
        "t4_full_factorial": 2880,
        "t5_multi_pathogen": 400,
        "t6_dose_response": 3600,
        "t7_compliance": 4000,
        "t8_wearables": 480,
        "t9_slow_pathogens": 320,
        "t10_population_size": 100,
    }
    total = 0
    for tier_id, n_exp in expected.items():
        runs = list(generate_tier_runs(manifest, tier_id))
        assert len(runs) == n_exp, f"{tier_id}: {len(runs)} != {n_exp}"
        total += len(runs)
    assert total == 17780


def test_default_num_agents_is_7000_across_standard_tiers() -> None:
    manifest = load_manifest()
    assert manifest["default_num_agents"] == 7000
    for tier_id in STANDARD_TIERS:
        _rid, spec = next(generate_tier_runs(manifest, tier_id))
        assert spec["config_overrides"]["ship_graph"]["num_agents"] == 7000, tier_id


def test_t2_sweeps_outdoor_air_fraction() -> None:
    manifest = load_manifest()
    runs = list(generate_tier_runs(manifest, "t2_hvac_sweep"))
    rid, spec = next((r, s) for r, s in runs if "oa30" in r)
    assert "oa30" in rid
    assert spec["config_overrides"]["hvac"]["oa_fraction"] == pytest.approx(0.30)
    # Every configured OA level appears in the generated run ids.
    oa_names = set(manifest["tiers"]["t2_hvac_sweep"]["oa_fractions"])
    seen = {name for name in oa_names if any(name in r for r, _ in runs)}
    assert seen == oa_names


def test_t6_sweeps_initial_infected_and_pre_immunity() -> None:
    manifest = load_manifest()
    runs = list(generate_tier_runs(manifest, "t6_dose_response"))
    # New top dose value and a non-zero immunity level are both generated.
    sample = next(
        s for rid, s in runs
        if "init50" in rid and "imm40" in rid and "norovirus" in rid
    )
    assert sample["pathogen_overrides"]["norwalk_gi"]["initial_infected"] == 50
    assert sample["config_overrides"]["ship_graph"]["immune_fraction"] == pytest.approx(0.4)


def test_t7_sweeps_pre_immunity_with_compliance() -> None:
    manifest = load_manifest()
    runs = list(generate_tier_runs(manifest, "t7_compliance"))
    sample = next(s for rid, s in runs if "comp80" in rid and "imm20" in rid)
    assert sample["config_overrides"]["fred_behavior"]["quarantine_compliance"] == pytest.approx(0.8)
    assert sample["config_overrides"]["ship_graph"]["immune_fraction"] == pytest.approx(0.2)


def test_t1_spec_shape_and_pathogen_override() -> None:
    manifest = load_manifest()
    rid, spec = next(generate_tier_runs(manifest, "t1_pathogen_baselines"))
    assert rid.startswith("t1_")
    assert spec["catalog"]["platform_id"] == "mega_cruise_5000"
    assert spec["run"]["num_epochs"] == 240
    assert spec["config_overrides"]["ship_graph"]["num_agents"] == 7000
    assert "pathogen_overrides" in spec


def test_natural_history_clock_flag_is_optional_and_recorded() -> None:
    manifest = load_manifest()
    assert _campaign_parser().parse_args([]).natural_history_clock is None
    _rid, default_spec = next(
        generate_tier_runs(manifest, "t1_pathogen_baselines"),
    )
    assert "natural_history_clock" not in default_spec.get("config_overrides", {})
    assert "natural_history_clock" not in default_spec["campaign_parameters"]

    _rid, arm_spec = next(
        generate_tier_runs(
            manifest,
            "t1_pathogen_baselines",
            natural_history_clock="legacy_epoch_day",
        ),
    )
    assert arm_spec["config_overrides"]["natural_history_clock"] == (
        "legacy_epoch_day"
    )
    assert arm_spec["campaign_parameters"]["natural_history_clock"] == (
        "legacy_epoch_day"
    )


def test_natural_history_clock_arm_mismatch_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    out = tmp_path / "clock_arm"
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.OUTPUT_ROOT",
        out,
    )
    assert _ensure_clock_arm("hours") is None
    with pytest.raises(SystemExit, match="hours.*legacy_epoch_day"):
        _ensure_clock_arm("legacy_epoch_day")


def test_natural_history_clock_arm_refuses_legacy_unmarked_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    out = tmp_path / "unmarked_clock_arm"
    out.mkdir()
    (out / "completed_runs.txt").write_text("existing_run\n", encoding="utf-8")
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.OUTPUT_ROOT",
        out,
    )
    with pytest.raises(SystemExit, match="hours.*legacy_epoch_day"):
        _ensure_clock_arm("legacy_epoch_day", explicit=True)
    assert (out / "natural_history_clock.txt").read_text(
        encoding="utf-8",
    ).strip() == "hours"


@pytest.mark.timeout(120)
def test_natural_history_clock_changes_single_run(
    tmp_path: Path,
) -> None:
    run_id = "clock_arm_probe"
    for clock in ("hours", "legacy_epoch_day"):
        spec = make_picard_spec(
            run_id,
            platform="destroyer_baseline",
            bundle="active_profiles",
            pathogen_overrides={
                "norwalk_gi": {
                    "dose_adjustment": 10.6,
                    "initial_infected": 1,
                },
                "remove": ["sars_cov2_resp"],
            },
            config_overrides={
                "natural_history_clock": clock,
                "ship_graph": {"num_agents": 20},
            },
            seed=200,
            epochs=24,
            num_agents=20,
        )
        out = tmp_path / clock
        out.mkdir()
        spec_path = out / f"{clock}.json"
        spec_path.write_text(json.dumps(spec), encoding="utf-8")
        assert main(["--single", str(spec_path), str(out)]) == 0

    summaries = {}
    for clock in ("hours", "legacy_epoch_day"):
        with zipfile.ZipFile(tmp_path / clock / f"{run_id}.zip") as zf:
            summaries[clock] = json.loads(zf.read("summary.json"))
    assert summaries["hours"]["parameters"]["natural_history_clock"] == "hours"
    assert summaries["legacy_epoch_day"]["parameters"][
        "natural_history_clock"
    ] == "legacy_epoch_day"
    assert summaries["hours"]["derived"] != summaries["legacy_epoch_day"]["derived"]


def test_t6_sets_initial_infected_on_pathogen_id() -> None:
    manifest = load_manifest()
    runs = list(generate_tier_runs(manifest, "t6_dose_response"))
    sample = next(s for rid, s in runs if "init5_" in rid and "norovirus" in rid)
    assert sample["pathogen_overrides"]["norwalk_gi"]["initial_infected"] == 5


def test_t7_sets_quarantine_compliance() -> None:
    manifest = load_manifest()
    runs = list(generate_tier_runs(manifest, "t7_compliance"))
    sample = next(s for rid, s in runs if "comp80" in rid)
    assert sample["config_overrides"]["fred_behavior"]["quarantine_compliance"] == pytest.approx(0.8)


def test_t8_sets_wearable_deployment_profile() -> None:
    manifest = load_manifest()
    runs = list(generate_tier_runs(manifest, "t8_wearables"))
    sample = next(s for rid, s in runs if "crew_only" in rid)
    assert sample["config_overrides"]["wearable_monitoring"]["deployment_profile"] == "crew_only"


def _v4_manifest_or_stub() -> dict[str, Any]:
    """Prefer the Downloads v4 manifest; fall back to a minimal stub for CI."""
    v4 = Path.home() / "Downloads" / "campaign_manifest_v4.json"
    if v4.is_file():
        # Outside campaign roots — load directly for local generator checks.
        with open(v4, encoding="utf-8") as fh:
            return json.load(fh)
    base = load_manifest()
    base["tiers"] = {
        **base.get("tiers", {}),
        "t11_intervention_timing": {
            "pathogens": ["norovirus"],
            "surveillance_delay_epochs": [0, 24],
            "surveillance_strategies": ["syndromic", "cascade"],
            "seeds": [200],
        },
        "t12_surveillance_sensitivity": {
            "pathogens": ["norovirus"],
            "sick_call_probabilities": [0.1, 0.7],
            "surveillance_strategies": ["syndromic"],
            "seeds": [200],
        },
        "t13_wearable_sensitivity": {
            "pathogens": ["norovirus"],
            "wearable_sensitivities": [0.3, 0.95],
            "surveillance_strategies": ["cascade"],
            "wearable_config": "crew_only",
            "seeds": [200],
        },
        "t14_immunity_threshold": {
            "pathogens": ["norovirus", "measles"],
            "pre_immunity_fractions": [0.0, 0.5],
            "surveillance": "syndromic",
            "seeds": [200],
        },
    }
    return base


def test_t11_sweeps_surveillance_activation_delay() -> None:
    manifest = _v4_manifest_or_stub()
    runs = list(generate_tier_runs(manifest, "t11_intervention_timing"))
    sample_rid, sample = next(
        (rid, s) for rid, s in runs if "delay24" in rid and "syndromic" in rid
    )
    assert "delay24" in sample_rid
    assert sample["config_overrides"]["syndromic"]["activation_delay_hours"] == 24
    assert sample["config_overrides"]["diagnostic_cascade"]["activation_delay_hours"] == 24
    assert sample["campaign_parameters"]["surveillance_delay_epochs"] == 24
    expected = (
        len(manifest["tiers"]["t11_intervention_timing"]["pathogens"])
        * len(manifest["tiers"]["t11_intervention_timing"]["surveillance_delay_epochs"])
        * len(manifest["tiers"]["t11_intervention_timing"]["surveillance_strategies"])
        * len(manifest["tiers"]["t11_intervention_timing"].get("compliance_levels") or [None])
        * len(manifest["tiers"]["t11_intervention_timing"]["seeds"])
    )
    assert len(runs) == expected


def test_t11_legacy_crosses_compliance_when_present() -> None:
    """v6-style T11: surveillance_delay_epochs × compliance_levels."""
    manifest = _v4_manifest_or_stub()
    tier = dict(manifest["tiers"]["t11_intervention_timing"])
    tier["compliance_levels"] = [0.2, 1.0]
    manifest = {**manifest, "tiers": {**manifest["tiers"], "t11_intervention_timing": tier}}
    runs = list(generate_tier_runs(manifest, "t11_intervention_timing"))
    sample_rid, sample = next(
        (rid, s) for rid, s in runs if "comp20" in rid and "delay24" in rid
    )
    assert "comp20" in sample_rid
    assert sample["config_overrides"]["fred_behavior"]["quarantine_compliance"] == pytest.approx(0.2)
    assert sample["campaign_parameters"]["compliance"] == pytest.approx(0.2)
    expected = (
        len(tier["pathogens"])
        * len(tier["surveillance_delay_epochs"])
        * len(tier["surveillance_strategies"])
        * len(tier["compliance_levels"])
        * len(tier["seeds"])
    )
    assert len(runs) == expected


def test_t12_sweeps_sick_call_probability() -> None:
    manifest = _v4_manifest_or_stub()
    runs = list(generate_tier_runs(manifest, "t12_surveillance_sensitivity"))
    sample = next(s for rid, s in runs if "scp10" in rid)
    assert sample["config_overrides"]["syndromic"]["sick_call_probability"] == pytest.approx(0.1)
    assert sample["campaign_parameters"]["sick_call_probability"] == pytest.approx(0.1)


def test_every_arm_records_the_hazard_it_will_report_at() -> None:
    """An arm that overrides nothing still reports, so the hazard is recorded.

    A summary that omits it cannot be scored against the reported-case anchors
    without assuming a value, which is how the C1 syndromic arm became
    unscorable.
    """
    manifest = load_manifest(REPORTED_CASE_REFIT_MANIFEST)
    runs = list(generate_tier_runs(manifest, "c1_expedition_cruise_450"))

    syndromic = next(s for rid, s in runs if "_syndromic_" in rid)
    silent = next(s for rid, s in runs if "_none_true_" in rid)

    assert "sick_call_probability" not in syndromic["config_overrides"].get(
        "syndromic", {},
    )
    assert syndromic["campaign_parameters"][
        "sick_call_probability_per_day"
    ] == pytest.approx(0.70)
    assert silent["campaign_parameters"][
        "sick_call_probability"
    ] == pytest.approx(0.0)


def test_an_explicit_hazard_override_is_not_overwritten_by_the_base() -> None:
    manifest = _v4_manifest_or_stub()
    runs = list(generate_tier_runs(manifest, "t12_surveillance_sensitivity"))
    sample = next(s for rid, s in runs if "scp10" in rid)

    params = sample["campaign_parameters"]
    assert params["sick_call_probability"] == pytest.approx(0.1)
    assert "sick_call_probability_per_day" not in params


def test_a_base_config_with_no_hazard_is_refused_not_defaulted(monkeypatch) -> None:
    """No silent fallback: an arm whose hazard is undeclared is an error."""
    from picard_framework.runs.mega_cruise_campaign import campaign_runner

    monkeypatch.setattr(
        campaign_runner,
        "_base_syndromic_config",
        lambda: {"background_noise_rate": 0.0},
    )

    with pytest.raises(ValueError, match="no syndromic sick-call hazard"):
        campaign_runner._record_reporting_hazard(
            {"platform_id": "expedition_cruise_450"},
        )


def test_t13_sweeps_wearable_detection_sensitivity() -> None:
    manifest = _v4_manifest_or_stub()
    runs = list(generate_tier_runs(manifest, "t13_wearable_sensitivity"))
    sample = next(s for rid, s in runs if "wsens30" in rid)
    wear = sample["config_overrides"]["wearable_monitoring"]
    assert wear["deployment_profile"] == "crew_only"
    assert wear["detection_sensitivity_scale"] == pytest.approx(0.3)
    assert sample["campaign_parameters"]["wearable_sensitivity"] == pytest.approx(0.3)


def test_t14_sweeps_pre_immunity_with_syndromic() -> None:
    manifest = _v4_manifest_or_stub()
    runs = list(generate_tier_runs(manifest, "t14_immunity_threshold"))
    sample = next(s for rid, s in runs if "imm50" in rid and "norovirus" in rid)
    assert sample["config_overrides"]["ship_graph"]["immune_fraction"] == pytest.approx(0.5)
    assert sample["config_overrides"]["diagnostic_cascade"]["enabled"] is False
    assert sample["campaign_parameters"]["immunity"] == pytest.approx(0.5)
    assert sample["campaign_parameters"]["surveillance"] == "syndromic"


def test_t1_honors_surveillance_strategies_when_present() -> None:
    """v4 t1 sweeps none_true vs syndromic; legacy single-surveillance ids stay unchanged."""
    legacy = load_manifest()
    legacy_runs = list(generate_tier_runs(legacy, "t1_pathogen_baselines"))
    assert all("_none_" not in rid and "_syndromic_" not in rid for rid, _ in legacy_runs)
    assert legacy_runs[0][0].startswith("t1_")
    assert legacy_runs[0][1]["campaign_parameters"]["surveillance"] == "none"

    manifest = _v4_manifest_or_stub()
    if "surveillance_strategies" not in manifest["tiers"]["t1_pathogen_baselines"]:
        manifest["tiers"]["t1_pathogen_baselines"]["surveillance_strategies"] = [
            "none_true", "syndromic",
        ]
        manifest["tiers"]["t1_pathogen_baselines"].pop("surveillance", None)
    runs = list(generate_tier_runs(manifest, "t1_pathogen_baselines"))
    none_true = next(s for rid, s in runs if "_none_true_" in rid)
    syn = next(s for rid, s in runs if "_syndromic_" in rid)
    assert none_true["config_overrides"]["syndromic"]["sick_call_probability"] == 0.0
    assert none_true["config_overrides"]["wearable_monitoring"]["enabled"] is False
    assert "sick_call_probability" not in syn["config_overrides"].get("syndromic", {})
    tier = manifest["tiers"]["t1_pathogen_baselines"]
    assert len(runs) == (
        len(tier["pathogens"])
        * len(tier["surveillance_strategies"])
        * len(tier["seeds"])
    )


def test_t10_honors_surveillance_strategies_when_present() -> None:
    """v4 t10 crosses population × surveillance; legacy omits surv tags/overrides."""
    legacy = load_manifest()
    legacy_runs = list(generate_tier_runs(legacy, "t10_population_size"))
    assert all(
        "_none_true_" not in rid and "_syndromic_" not in rid and "_cascade_" not in rid
        for rid, _ in legacy_runs
    )
    assert "surveillance" not in legacy_runs[0][1]["campaign_parameters"]

    manifest = _v4_manifest_or_stub()
    tier = manifest["tiers"].setdefault("t10_population_size", {
        "pathogens": ["norovirus"],
        "population_sizes": [1000, 2000],
        "surveillance_strategies": ["none_true", "cascade"],
        "seeds": [200],
    })
    if "surveillance_strategies" not in tier:
        tier["surveillance_strategies"] = ["none_true", "cascade"]
    runs = list(generate_tier_runs(manifest, "t10_population_size"))
    sample = next(s for rid, s in runs if "_cascade_" in rid and "_n" in rid)
    assert sample["config_overrides"]["diagnostic_cascade"]["enabled"] is True
    assert sample["campaign_parameters"]["surveillance"] == "cascade"
    assert len(runs) == (
        len(tier["pathogens"])
        * len(tier["population_sizes"])
        * len(tier["surveillance_strategies"])
        * len(tier["seeds"])
    )


def test_make_picard_spec_optional_telemetry_paths(tmp_path) -> None:
    telemetry = tmp_path / "ctb_run"
    telemetry.mkdir()
    spec = make_picard_spec(
        "x",
        platform="destroyer_baseline",
        bundle="active_profiles",
        pathogen_overrides={"remove": ["sars_cov2_resp"]},
        config_overrides=None,
        seed=42,
        epochs=2,
        num_agents=20,
        telemetry_dir=telemetry,
    )
    assert spec["run"]["simulation_history"].endswith("simulation_history.json")
    assert spec["run"]["history_retention"] == "compact"
    assert spec["campaign_parameters"]["seed"] == 42
    assert spec["campaign_parameters"]["num_agents"] == 20


def test_tier_specs_carry_compact_retention_and_parameters() -> None:
    manifest = load_manifest()
    rid, spec = next(generate_tier_runs(manifest, "t1_pathogen_baselines"))
    assert spec["run"]["history_retention"] == "compact"
    params = spec["campaign_parameters"]
    assert params["run_id"] == rid
    assert params["tier_id"] == "t1_pathogen_baselines"
    assert params["pathogen"]
    assert params["seed"] == spec["run"]["random_seed"]
    assert params["num_agents"] == spec["config_overrides"]["ship_graph"]["num_agents"]

    _rid2, spec2 = next(generate_tier_runs(manifest, "t2_hvac_sweep"))
    p2 = spec2["campaign_parameters"]
    assert "filter" in p2
    assert "oa" in p2
    assert "decay" in p2
    assert "filter_efficiency" in p2
    assert "outdoor_air_fraction" in p2


def test_parameters_from_spec_fallback_without_campaign_block() -> None:
    spec = {
        "description": "ad_hoc",
        "catalog": {"platform_id": "destroyer_baseline", "pathogen_bundle_id": "active_profiles"},
        "run": {"random_seed": 7, "num_epochs": 4, "history_retention": "full"},
        "config_overrides": {"ship_graph": {"num_agents": 50}, "hvac": {"filter_efficiency": 0.9}},
    }
    params = parameters_from_spec(spec)
    assert params["run_id"] == "ad_hoc"
    assert params["seed"] == 7
    assert params["num_agents"] == 50
    assert params["filter_efficiency"] == pytest.approx(0.9)
    assert params["history_retention"] == "full"


def _sample_history() -> list[dict]:
    return [
        {
            "epoch": 0, "trigger_status": "BASELINE",
            "summary": {"susceptible": 10, "infected": 1, "recovered": 0,
                        "quarantined": 0, "isolated": 0,
                        "passenger_complement": 900,
                        "crew_complement": 100},
            "cost_accounting": {"total_financial_usd": 5.0,
                                "operational_impact_cumulative": 1.0},
            "spaces": {"A": {"concentration_per_m3": 2.0, "pathogen_mass": 3.0}},
        },
        {
            "epoch": 1, "trigger_status": "SUSPECTED",
            "summary": {"susceptible": 8, "infected": 3, "recovered": 1,
                        "quarantined": 2, "isolated": 1,
                        "passenger_complement": 900,
                        "crew_complement": 100},
            "cost_accounting": {"total_financial_usd": 9.0,
                                "operational_impact_cumulative": 2.0},
            "spaces": {"A": {"concentration_per_m3": 0.5, "pathogen_mass": 1.0}},
        },
        {
            "epoch": 2, "trigger_status": "CONFIRMED",
            "summary": {"susceptible": 6, "infected": 1, "recovered": 4,
                        "quarantined": 1, "isolated": 0,
                        "passenger_complement": 900,
                        "crew_complement": 100},
            "cost_accounting": {"total_financial_usd": 12.0,
                                "operational_impact_cumulative": 3.0},
            "spaces": {"A": {"concentration_per_m3": 0.1, "pathogen_mass": 0.0}},
        },
    ]


def test_extract_timeseries_compact_fields() -> None:
    ts = extract_timeseries(_sample_history())
    assert len(ts) == 3
    assert ts[0]["epoch"] == 0
    assert ts[0]["n_zones_contaminated"] == 1  # conc 2.0 > 1.0
    assert ts[1]["n_zones_contaminated"] == 0  # conc 0.5 < 1.0
    assert ts[0]["max_conc_zone"] == "A"
    assert ts[2]["cumulative_cost_usd"] == pytest.approx(12.0)
    assert ts[2]["trigger_status"] == "CONFIRMED"
    assert ts[2]["passenger_complement"] == 900
    assert ts[2]["crew_complement"] == 100
    # Incidence = Δ(I+R): 1, then 3, then 1 — not the old ΔR+I formula.
    assert [e["new_infections"] for e in ts] == [1, 3, 1]
    assert extract_timeseries([]) == []


def test_compute_derived_metrics() -> None:
    ts = extract_timeseries(_sample_history())
    derived = compute_derived_metrics(ts, num_agents=1000)
    assert derived["peak_prevalence"] == 3
    assert derived["peak_epoch"] == 1
    # VSP at epoch 1 (too early for Δ²incidence) → fizzle under curvature rule.
    assert derived["outbreak_occurred"] is False
    assert derived["detection_epoch"] == 1
    assert derived["confirmation_epoch"] == 2
    # Attack rate uses (I+R)_final / N = 5/1000.
    assert derived["attack_rate"] == pytest.approx(0.005)
    assert derived["total_quarantine_person_epochs"] == 3
    assert derived["r_effective_at_peak"] == pytest.approx(3.0)
    assert derived["passenger_complement"] == 900
    assert derived["crew_complement"] == 100
    # Empty series must not raise (no max([])).
    assert compute_derived_metrics([], num_agents=1000) == {}


def test_compute_derived_metrics_omits_legacy_role_complements() -> None:
    point = {
        "epoch": 0,
        "infected": 1,
        "recovered": 0,
    }
    derived = compute_derived_metrics([point], num_agents=10)
    assert "passenger_complement" not in derived
    assert "crew_complement" not in derived


def test_compute_derived_metrics_rejects_half_populated_role_complements() -> None:
    point = {
        "epoch": 0,
        "infected": 1,
        "recovered": 0,
        "passenger_complement": 9,
    }
    with pytest.raises(ValueError, match="positive integers summing"):
        compute_derived_metrics([point], num_agents=10)


def test_compute_derived_metrics_rejects_invalid_role_complements() -> None:
    point = {
        "epoch": 0,
        "infected": 1,
        "recovered": 0,
        "passenger_complement": 900,
        "crew_complement": 99,
    }

    with pytest.raises(ValueError, match="positive integers summing"):
        compute_derived_metrics([point], num_agents=1000)


@pytest.mark.timeout(180)
def test_smoke_cli_one_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end subprocess path writes local and fused shard artifacts."""
    import zipfile

    out = tmp_path / "mega_cruise_campaign"
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.OUTPUT_ROOT",
        out,
    )
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.COMPLETED_LOG",
        out / "completed_runs.txt",
    )
    rc = main(["--smoke", "--keep-workdir"])
    assert rc == 0
    zips = {path.name: path for path in out.glob("*.zip")}
    assert len(zips) == 2
    assert "single.zip" in zips
    assert "single.manifest.json" in {path.name for path in out.glob("*.json")}
    completed = (out / "completed_runs.txt").read_text(encoding="utf-8").strip()
    assert completed
    # summary present in both the retained workdir and accumulation dir.
    work = out / completed
    assert (work / "summary.json").is_file()
    summary = json.loads((work / "summary.json").read_text(encoding="utf-8"))
    assert "summary" in summary
    assert "derived" in summary
    assert "parameters" in summary
    assert summary["parameters"]["seed"] is not None
    assert summary["parameters"].get("history_retention") == "compact"
    accumulated = out / "_shard_runs" / "single" / completed
    assert (accumulated / "summary.json").is_file()
    # timeseries.json is written and packed into the zip.
    assert (work / "timeseries.json").is_file()
    with zipfile.ZipFile(zips["single.zip"]) as zf:
        names = zf.namelist()
    assert any(n == f"{completed}/timeseries.json" for n in names)
    assert any(n == f"{completed}/summary.json" for n in names)
    manifest = json.loads((out / "single.manifest.json").read_text(encoding="utf-8"))
    assert manifest[0]["run_id"] == completed
    assert manifest[0]["parameters"] == summary["parameters"]


@pytest.mark.timeout(120)
def test_smoke_in_process(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--in-process runs one sim and writes local plus fused shard zips."""
    out = tmp_path / "mega_cruise_campaign"
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.OUTPUT_ROOT",
        out,
    )
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.COMPLETED_LOG",
        out / "completed_runs.txt",
    )
    rc = main(["--smoke", "--in-process", "--keep-workdir"])
    assert rc == 0
    assert "single.zip" in {path.name for path in out.glob("*.zip")}
    assert len(list(out.glob("*.zip"))) == 2


def _load_aggregator():
    import importlib.util

    path = REPO_ROOT / "deploy" / "aws" / "aggregate_results.py"
    spec = importlib.util.spec_from_file_location("aggregate_results", path)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_zip(path: Path, payload: dict, timeseries: list | None) -> None:
    import zipfile

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("summary.json", json.dumps(payload))
        if timeseries is not None:
            zf.writestr("timeseries.json", json.dumps(timeseries))


def test_aggregate_flattens_derived_and_timeseries_metadata(tmp_path: Path) -> None:
    agg = _load_aggregator()
    zip_path = tmp_path / "run_a.zip"
    _write_zip(
        zip_path,
        {
            "run_id": "run_a",
            "num_epochs": 3,
            "trigger_status": "CONFIRMED",
            "parameters": {"pathogen": "norovirus", "seed": 42, "filter": "hepa"},
            "summary": {"infected": 1, "recovered": 4},
            "cost_accounting": {"total_financial_usd": 12.0},
            "derived": {"attack_rate": 0.004, "peak_prevalence": 3},
        },
        timeseries=[{"epoch": 0}, {"epoch": 1}, {"epoch": 2}],
    )
    row = agg.summary_from_zip(zip_path)
    assert row is not None
    assert row["derived.attack_rate"] == pytest.approx(0.004)
    assert row["derived.peak_prevalence"] == 3
    assert row["summary.recovered"] == 4
    assert row["cost.total_financial_usd"] == pytest.approx(12.0)
    assert row["parameters.pathogen"] == "norovirus"
    assert row["parameters.seed"] == 42
    assert row["parameters.filter"] == "hepa"
    assert row["timeseries.present"] is True
    assert row["timeseries.n_epochs"] == 3


def test_aggregate_backward_compatible_without_derived(tmp_path: Path) -> None:
    agg = _load_aggregator()
    zip_path = tmp_path / "run_old.zip"
    _write_zip(
        zip_path,
        {
            "run_id": "run_old",
            "num_epochs": 240,
            "trigger_status": "BASELINE",
            "summary": {"infected": 0},
            "cost_accounting": {"total_financial_usd": 1.0},
        },
        timeseries=None,
    )
    row = agg.summary_from_zip(zip_path)
    assert row is not None
    assert row["summary.infected"] == 0
    assert row["timeseries.present"] is False
    assert row["timeseries.n_epochs"] is None
    assert not any(k.startswith("derived.") for k in row)
    assert not any(k.startswith("parameters.") for k in row)


def test_aggregate_deduplicates_local_run_and_shard_zips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    agg = _load_aggregator()
    results = tmp_path / "results"
    results.mkdir()
    payload = {
        "run_id": "run_a",
        "parameters": {"seed": 42},
        "summary": {"infected": 1},
    }
    _write_zip(results / "run_a.zip", payload, [{"epoch": 0}])
    with zipfile.ZipFile(results / "single.zip", "w") as zf:
        zf.writestr("run_a/summary.json", json.dumps(payload))
        zf.writestr("run_a/timeseries.json", json.dumps([{"epoch": 0}]))

    output_json = tmp_path / "aggregate.json"
    output_csv = tmp_path / "aggregate.csv"
    monkeypatch.chdir(tmp_path)
    assert agg.main([
        str(results),
        "--out-json", str(output_json),
        "--out-csv", str(output_csv),
    ]) == 0
    rows = json.loads(output_json.read_text(encoding="utf-8"))
    assert [row["run_id"] for row in rows] == ["run_a"]


def test_subprocess_timeout_writes_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Child timeout must leave stderr + failure sidecars and return False."""
    out = tmp_path / "mega_cruise_campaign"
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.OUTPUT_ROOT",
        out,
    )

    class _FakeProc:
        pid = 4242
        returncode = -9

        def poll(self):
            return None

        def kill(self):
            return None

        def communicate(self, timeout=None):  # noqa: ARG002
            return ("", "")

    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.subprocess.Popen",
        lambda *_a, **_k: _FakeProc(),
    )
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.time.monotonic",
        lambda: 1_000_000.0,
    )
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner._read_vmhwm_kb",
        lambda _pid: 1234,
    )
    ok = run_simulation_subprocess("timeout_run", {"description": "timeout_run"}, timeout=0)
    assert ok is False
    err = out / "timeout_run.subprocess_stderr.txt"
    assert err.is_file()
    assert "TimeoutExpired" in err.read_text(encoding="utf-8")
    failure = json.loads((out / "timeout_run.failure.json").read_text(encoding="utf-8"))
    assert failure["timed_out"] is True
    assert failure["failure_class"] == "timeout"
    assert failure["peak_rss_kb"] == 1234
    resource = json.loads((out / "timeout_run.resource.json").read_text(encoding="utf-8"))
    assert resource["ok"] is False


def test_looks_like_oom_and_classify_helpers() -> None:
    import importlib.util

    from picard_framework.runs.mega_cruise_campaign.campaign_runner import (
        _looks_like_oom,
    )

    clf_path = REPO_ROOT / "deploy" / "aws" / "classify_batch_failures.py"
    spec = importlib.util.spec_from_file_location("classify_batch_failures", clf_path)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    classify_attempt = mod.classify_attempt

    assert _looks_like_oom(137) is True
    assert _looks_like_oom(-9) is True
    assert _looks_like_oom(1) is False
    assert classify_attempt(
        status_reason="Host EC2 terminated",
        exit_code=1,
        container_reason=None,
    ) == "spot_reclaim"
    # Fargate Spot reclaim uses exit 137 + Spot statusReason — not OOM.
    assert classify_attempt(
        status_reason="Your Spot Task was interrupted.",
        exit_code=137,
        container_reason=None,
    ) == "spot_reclaim"
    assert classify_attempt(
        status_reason=None,
        exit_code=137,
        container_reason="OutOfMemoryError: container killed due to memory usage",
    ) == "oom"
    assert classify_attempt(
        status_reason=None,
        exit_code=137,
        container_reason=None,
    ) == "oom"
    assert classify_attempt(
        status_reason="Essential container in task exited",
        exit_code=1,
        container_reason="TimeoutExpired after 3600s",
    ) == "timeout"
    assert classify_attempt(
        status_reason=None,
        exit_code=0,
        container_reason=None,
    ) == "ok"


def test_failed_ledger_and_clear_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    out = tmp_path / "mega_cruise_campaign"
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.OUTPUT_ROOT",
        out,
    )
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.FAILED_LOG",
        out / "failed_runs.txt",
    )
    run_dir = out / "bad_run"
    run_dir.mkdir(parents=True)
    (run_dir / "error.txt").write_text("boom", encoding="utf-8")
    (out / "bad_run.subprocess_stderr.txt").write_text("err", encoding="utf-8")
    (out / "bad_run.failure.json").write_text("{}", encoding="utf-8")
    (out / "bad_run.resource.json").write_text("{}", encoding="utf-8")

    mark_failed("bad_run")
    assert "bad_run" in failed_runs()
    clear_failed_artifacts("bad_run")
    assert not run_dir.exists()
    assert not (out / "bad_run.subprocess_stderr.txt").exists()
    assert not (out / "bad_run.failure.json").exists()
    assert not (out / "bad_run.resource.json").exists()


def test_resume_downloads_s3_completed_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--resume with --s3-prefix must seed completed_runs.txt from S3."""
    out = tmp_path / "mega_cruise_campaign"
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.OUTPUT_ROOT",
        out,
    )
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.COMPLETED_LOG",
        out / "completed_runs.txt",
    )
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.FAILED_LOG",
        out / "failed_runs.txt",
    )

    class FakeUploader:
        def __init__(self, _prefix: str) -> None:
            pass

        def download_file(self, name: str, local_path: Path) -> bool:
            if not name.startswith("_resume/"):
                return False
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_text("already_done\n", encoding="utf-8")
            return True

        def object_exists(self, name: str) -> bool:
            return False

        def upload_file(self, local_path: Path, name: str) -> str:
            return f"s3://fake/{name}"

    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.S3Uploader",
        FakeUploader,
    )
    # dry-run still triggers resume download before generation completes.
    rc = main([
        "--dry-run", "--resume", "--tier", "t1",
        "--s3-prefix", "s3://fake-bucket/campaign/",
        "--shard-count", "2", "--shard-index", "0",
    ])
    assert rc == 0
    assert (out / "completed_runs.txt").read_text(encoding="utf-8").strip() == "already_done"


def test_native_oa_fraction_changes_supply_flow() -> None:
    """hvac.oa_fraction must change native recirculated supply (sensitivity)."""
    from engines.py_contam_bridge import (
        UNSOURCED_LEGACY_FILTER_EFFICIENCY,
        build_transport_engine,
    )

    base_cfg = {
        "ship_graph": {
            "spatial_layout": "data/platforms/mega_cruise_5000/spatial_layout.json",
            "air_flow_paths": "data/platforms/mega_cruise_5000/air_flow_paths.json",
        },
        # η stated rather than inherited; this test varies oa_fraction only.
        "hvac": {
            "transport_engine": "native",
            "oa_fraction": 0.2,
            "filter_efficiency": UNSOURCED_LEGACY_FILTER_EFFICIENCY,
        },
    }
    high_oa = {
        **base_cfg,
        "hvac": {
            "transport_engine": "native",
            "oa_fraction": 0.4,
            "filter_efficiency": UNSOURCED_LEGACY_FILTER_EFFICIENCY,
        },
    }
    from engines.py_contam_bridge import PATH_TYPE_HVAC_SUPPLY

    eng_lo = build_transport_engine(str(REPO_ROOT), base_cfg)
    eng_hi = build_transport_engine(str(REPO_ROOT), high_oa)
    assert eng_lo is not None
    assert eng_hi is not None
    supplies_lo = [
        p.flow_rate_m3h for p in eng_lo.airflow_paths
        if p.path_type == PATH_TYPE_HVAC_SUPPLY
    ]
    supplies_hi = [
        p.flow_rate_m3h for p in eng_hi.airflow_paths
        if p.path_type == PATH_TYPE_HVAC_SUPPLY
    ]
    assert supplies_lo
    assert supplies_hi
    # Higher OA → less recirculated supply.
    assert sum(supplies_hi) < sum(supplies_lo)


def test_contamx_build_applies_hvac_oa_fraction(monkeypatch: pytest.MonkeyPatch) -> None:
    """build_contamx_engine must re-apply hvac.oa_fraction after disk reload."""
    from engines import contamx_transport as cx
    from engines.py_contam_bridge import UNSOURCED_LEGACY_FILTER_EFFICIENCY

    captured: dict[str, Any] = {}

    class FakeSim:
        def path_volumetric_flow_m3h(self):
            return {1: 10.0}

    class FakeEngine:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            captured["oa_fraction"] = kwargs.get("oa_fraction")
            self._oa_fraction = kwargs["oa_fraction"]

    monkeypatch.setattr(cx, "find_contamx", lambda cfg: "/fake/contamx")
    monkeypatch.setattr(cx, "run_contamx", lambda *a, **k: "/fake/model.sim")
    monkeypatch.setattr(cx, "SimResults", lambda path, allowed_roots=None: FakeSim())
    monkeypatch.setattr(
        cx, "resolve_contam_prj_path",
        lambda *a, **k: str(REPO_ROOT / "data/platforms/destroyer_baseline/contam/model.prj"),
    )
    monkeypatch.setattr(
        cx, "_load_path_map_entries_beside_prj",
        lambda *a, **k: [{
            "path_nr": 1, "from_zone": "A", "to_zone": "B",
            "is_hvac_ducted": False, "kind": "adjacency", "ahs_nr": 0,
        }],
    )
    monkeypatch.setattr(cx, "ContamXTransportEngine", FakeEngine)

    # Disk default 0.2; campaign override 0.35 must win.
    monkeypatch.setattr(
        "engines.py_contam_bridge.load_spatial_layout",
        lambda *a, **k: {"zones": [{"id": "A", "volume_m3": 10.0}, {"id": "B", "volume_m3": 10.0}]},
    )
    monkeypatch.setattr(
        "engines.py_contam_bridge.load_air_flow_paths",
        lambda *a, **k: {"oa_fraction": 0.2},
    )

    cfg = {
        "hvac": {
            "oa_fraction": 0.35,
            "filter_efficiency": UNSOURCED_LEGACY_FILTER_EFFICIENCY,
        },
    }
    engine = cx.build_contamx_engine(str(REPO_ROOT), cfg)
    assert captured["oa_fraction"] == pytest.approx(0.35)
    assert engine._oa_fraction == pytest.approx(0.35)


def test_immune_fraction_changes_init_immune_count() -> None:
    """ship_graph.immune_fraction must flow to KorkinShipEngine.immune_ratio."""
    from orchestrator_init import build_engine

    base = {
        "ship_graph": {"num_agents": 100, "num_passengers": 80, "num_crew": 20},
        "initial_infected": 1,
    }
    eng_default = build_engine(base, seed=7)
    eng_high = build_engine(
        {**base, "ship_graph": {**base["ship_graph"], "immune_fraction": 0.5}},
        seed=7,
    )
    assert eng_default.immune_ratio == pytest.approx(0.2)
    assert eng_high.immune_ratio == pytest.approx(0.5)
    n_default = sum(1 for a in eng_default.agents if a.immune)
    n_high = sum(1 for a in eng_high.agents if a.immune)
    assert n_high > n_default


def test_analyze_campaign_curves_long_form(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Curve analyzer stacks timeseries.json into a long-form CSV."""
    import importlib.util
    import zipfile

    mod_path = REPO_ROOT / "deploy" / "aws" / "analyze_campaign_curves.py"
    spec = importlib.util.spec_from_file_location("analyze_campaign_curves", mod_path)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    zpath = tmp_path / "t2_noro_merv8_oa20_med_s42.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr(
            "summary.json",
            json.dumps({
                "run_id": "t2_noro_merv8_oa20_med_s42",
                "derived": {"attack_rate": 0.1, "peak_prevalence": 5},
            }),
        )
        zf.writestr(
            "timeseries.json",
            json.dumps([
                {"epoch": 0, "infected": 1, "recovered": 0},
                {"epoch": 1, "infected": 3, "recovered": 1},
            ]),
        )
    with zipfile.ZipFile(tmp_path / "single.zip", "w") as zf:
        zf.writestr(
            "run_a/summary.json",
            json.dumps({
                "run_id": "t2_noro_merv8_oa20_med_s42",
                "derived": {"attack_rate": 0.1, "peak_prevalence": 5},
            }),
        )
        zf.writestr(
            "run_a/timeseries.json",
            json.dumps([
                {"epoch": 0, "infected": 1, "recovered": 0},
                {"epoch": 1, "infected": 3, "recovered": 1},
            ]),
        )

    rows = list(mod.iter_curve_rows(tmp_path))
    assert len(rows) == 2
    assert rows[0]["run_id"] == "t2_noro_merv8_oa20_med_s42"
    assert rows[0]["oa"] == "oa20"
    assert rows[1]["infected"] == 3
    assert rows[0]["attack_rate"] == pytest.approx(0.1)

    out_csv = tmp_path / "curves.csv"
    frontiers = tmp_path / "frontiers.csv"
    monkeypatch.chdir(tmp_path)
    n = mod.write_outputs(tmp_path, str(out_csv), str(frontiers))
    assert n == 2
    assert out_csv.is_file()
    assert frontiers.is_file()
    frontier_text = frontiers.read_text(encoding="utf-8")
    assert "oa20" in frontier_text
    assert "attack_rate" in frontier_text


def test_shard_partitions_are_complete_and_disjoint() -> None:
    """shard-count/index must partition the flattened run list without gaps or overlap."""
    manifest = load_manifest()
    all_runs = list(generate_tier_runs(manifest, "t1_pathogen_baselines"))
    n = len(all_runs)
    assert n == 300

    shard_count = 7
    claimed: dict[int, int] = {}
    for shard_index in range(shard_count):
        for global_index in range(n):
            if global_index % shard_count == shard_index:
                assert global_index not in claimed
                claimed[global_index] = shard_index

    assert len(claimed) == n
    assert set(claimed) == set(range(n))
    # Each shard gets floor(n/k) or ceil(n/k) runs.
    sizes = [sum(1 for v in claimed.values() if v == i) for i in range(shard_count)]
    assert sum(sizes) == n
    assert max(sizes) - min(sizes) <= 1


def test_dry_run_shard_counts_sum_to_total(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """Dry-run with shards reports disjoint shard sizes that sum to the tier total."""
    out = tmp_path / "mega_cruise_campaign"
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.OUTPUT_ROOT",
        out,
    )
    shard_count = 4
    reported: list[int] = []
    for shard_index in range(shard_count):
        rc = main([
            "--dry-run", "--tier", "t1",
            "--shard-count", str(shard_count),
            "--shard-index", str(shard_index),
        ])
        assert rc == 0
        text = capsys.readouterr().out
        # "DRY RUN — N runs would run on shard i"
        match_line = next(
            line for line in text.splitlines()
            if "would run on shard" in line
        )
        count = int(match_line.split("—")[1].strip().split()[0])
        reported.append(count)
    assert sum(reported) == 300
    assert max(reported) - min(reported) <= 1


def test_smoke_s3_upload_failure_still_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """A failed zip upload must not flip a successful smoke run into failure."""
    out = tmp_path / "mega_cruise_campaign"
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.OUTPUT_ROOT",
        out,
    )
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.COMPLETED_LOG",
        out / "completed_runs.txt",
    )
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.FAILED_LOG",
        out / "failed_runs.txt",
    )

    class FailingUploader:
        def __init__(self, _prefix: str) -> None:
            self.uploads: list[str] = []

        def download_file(self, name: str, local_path: Path) -> bool:
            return False

        def object_exists(self, name: str) -> bool:
            return False

        def upload_file(self, local_path: Path, name: str) -> str:
            self.uploads.append(name)
            raise RuntimeError("simulated S3 outage")

    def fake_run(run_id: str, spec: dict, **kwargs: Any) -> bool:
        zip_path = out / f"{run_id}.zip"
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        zip_path.write_bytes(b"PK\x05\x06" + b"\x00" * 18)
        return True

    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.S3Uploader",
        FailingUploader,
    )
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.run_simulation_subprocess",
        fake_run,
    )
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.run_simulation",
        fake_run,
    )
    rc = main([
        "--smoke", "--in-process",
        "--s3-prefix", "s3://fake-bucket/campaign/",
    ])
    assert rc == 0
    out_text = capsys.readouterr().out
    assert "s3 upload failed" in out_text or "completed_runs.txt upload failed" in out_text
    zips = list(out.glob("*.zip"))
    assert len(zips) == 2
    assert (out / "completed_runs.txt").is_file()


def test_resume_skips_when_s3_manifest_contains_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On --resume, a downloaded shard manifest marks the run completed."""
    out = tmp_path / "mega_cruise_campaign"
    out.mkdir(parents=True)
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.OUTPUT_ROOT",
        out,
    )
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.COMPLETED_LOG",
        out / "completed_runs.txt",
    )
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.FAILED_LOG",
        out / "failed_runs.txt",
    )

    class ExistingZipUploader:
        def __init__(self, _prefix: str) -> None:
            pass

        def download_file(self, name: str, local_path: Path) -> bool:
            if name.endswith(".manifest.json"):
                candidate = list(generate_tier_runs(
                    load_manifest(),
                    "t1_pathogen_baselines",
                    platform="destroyer_baseline",
                    epochs_override=2,
                    num_agents_override=20,
                ))[0][0]
                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.write_text(
                    json.dumps([{
                        "run_id": candidate,
                        "parameters": {"seed": 1},
                        "derived": {},
                    }]),
                    encoding="utf-8",
                )
                return True
            return False

        def upload_file(self, local_path: Path, name: str) -> str:
            return f"s3://fake/{name}"

    called: list[str] = []

    def fake_run(run_id: str, spec: dict, **kwargs: Any) -> bool:
        called.append(run_id)
        return True

    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.S3Uploader",
        ExistingZipUploader,
    )
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.run_simulation_subprocess",
        fake_run,
    )
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.run_simulation",
        fake_run,
    )

    # Smoke selects t1/limit 1; with the candidate in the shard manifest
    # is skipped and marked completed without invoking the simulator.
    rc = main([
        "--smoke", "--resume",
        "--s3-prefix", "s3://fake-bucket/campaign/",
        "--in-process", "--shard-count", "300", "--shard-index", "0",
    ])
    assert rc == 0
    assert called == []
    completed = (out / "completed_runs.txt").read_text(encoding="utf-8").strip()
    assert completed  # at least the first smoke candidate was marked done
    assert [path.name for path in out.glob("*.zip")] == ["shard-0.zip"]


def test_periodic_shard_bundle_upload_and_resume_append(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Periodic bundle uploads are resumable and append later shard runs."""
    out = tmp_path / "mega_cruise_campaign"
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.OUTPUT_ROOT",
        out,
    )
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.COMPLETED_LOG",
        out / "completed_runs.txt",
    )
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.FAILED_LOG",
        out / "failed_runs.txt",
    )

    storage: dict[str, bytes] = {}
    upload_events: list[str] = []

    class MemoryUploader:
        def __init__(self, _prefix: str) -> None:
            self.uploads: list[str] = []

        def download_file(self, name: str, local_path: Path) -> bool:
            payload = storage.get(name)
            if payload is None:
                return False
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(payload)
            return True

        def upload_file(self, local_path: Path, name: str) -> str:
            self.uploads.append(name)
            upload_events.append(name)
            storage[name] = local_path.read_bytes()
            return f"s3://fake/{name}"

    calls: list[str] = []

    def fake_run(run_id: str, spec: dict, **kwargs: Any) -> bool:
        calls.append(run_id)
        suffix = kwargs.get("accumulation_suffix", "single")
        run_dir = out / "_shard_runs" / suffix / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        summary = {
            "run_id": run_id,
            "parameters": {"seed": spec["run"]["random_seed"]},
            "derived": {"attack_rate": 0.1},
        }
        (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
        (run_dir / "timeseries.json").write_text("[]", encoding="utf-8")
        (out / f"{run_id}.zip").write_bytes(b"local")
        return True

    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.S3Uploader",
        MemoryUploader,
    )
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.run_simulation",
        fake_run,
    )
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.run_simulation_subprocess",
        fake_run,
    )

    args = [
        "--tier", "t1", "--platform", "destroyer_baseline",
        "--epochs", "2", "--num-agents", "20", "--limit", "2",
        "--in-process", "--s3-log-every", "1",
        "--s3-prefix", "s3://fake-bucket/campaign/",
    ]
    assert main(args) == 0
    first_ids = calls[:2]
    assert "single.zip" in storage
    assert "single.manifest.json" in storage
    assert "_resume/completed_runs.single.txt" in storage
    first_manifest = json.loads(storage["single.manifest.json"])
    assert [entry["run_id"] for entry in first_manifest] == first_ids
    assert upload_events.count("single.zip") >= 2
    assert upload_events.count("single.manifest.json") >= 2
    with zipfile.ZipFile(out / "single.zip") as zf:
        assert all(f"{run_id}/summary.json" in zf.namelist() for run_id in first_ids)

    (out / "completed_runs.txt").unlink()
    (out / "single.zip").unlink()
    (out / "single.manifest.json").unlink()
    shutil.rmtree(out / "_shard_runs")
    args[args.index("--limit") + 1] = "1"
    assert main([*args, "--resume"]) == 0
    assert calls[2] not in first_ids
    final_manifest = json.loads(storage["single.manifest.json"])
    assert [entry["run_id"] for entry in final_manifest] == calls[:3]
    assert {"single.zip", "single.manifest.json"} <= set(
        name for name in storage if name.startswith("single")
    )


def test_shard_bundle_incremental_flush_and_corrupt_rebuild(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    out = tmp_path / "mega_cruise_campaign"
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.OUTPUT_ROOT",
        out,
    )
    bundle = ShardBundle(0, None)

    def add_run(run_id: str) -> None:
        run_dir = Path(bundle.accumulation_root) / run_id
        run_dir.mkdir(parents=True)
        (run_dir / "summary.json").write_text(
            json.dumps({"run_id": run_id, "parameters": {}, "derived": {}}),
            encoding="utf-8",
        )

    add_run("run_a")
    bundle.record_run("run_a")
    bundle.flush(None)
    with zipfile.ZipFile(bundle.zip_path) as zf:
        first_info = zf.getinfo("run_a/summary.json")

    full_rebuilds: list[list[tuple[str, str]]] = []
    original_pack_full = bundle._pack_full

    def track_full_rebuild(members: list[tuple[str, str]]) -> None:
        full_rebuilds.append(members)
        original_pack_full(members)

    monkeypatch.setattr(bundle, "_pack_full", track_full_rebuild)
    add_run("run_b")
    bundle.record_run("run_b")
    bundle.flush(None)
    assert full_rebuilds == []
    with zipfile.ZipFile(bundle.zip_path) as zf:
        assert zf.getinfo("run_a/summary.json").CRC == first_info.CRC
        assert "run_b/summary.json" in zf.namelist()

    Path(bundle.zip_path).write_bytes(b"not a zip")
    bundle.flush(None)
    assert len(full_rebuilds) == 1
    with zipfile.ZipFile(bundle.zip_path) as zf:
        assert {"run_a/summary.json", "run_b/summary.json"} <= set(zf.namelist())


def test_local_resume_preserves_manifest_entries_without_s3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    out = tmp_path / "mega_cruise_campaign"
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.OUTPUT_ROOT",
        out,
    )
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.COMPLETED_LOG",
        out / "completed_runs.txt",
    )
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.FAILED_LOG",
        out / "failed_runs.txt",
    )
    calls: list[str] = []

    def fake_run(run_id: str, spec: dict, **kwargs: Any) -> bool:
        calls.append(run_id)
        suffix = kwargs.get("accumulation_suffix", "single")
        run_dir = out / "_shard_runs" / suffix / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "summary.json").write_text(
            json.dumps({
                "run_id": run_id,
                "parameters": {"seed": spec["run"]["random_seed"]},
                "derived": {},
            }),
            encoding="utf-8",
        )
        (run_dir / "timeseries.json").write_text("[]", encoding="utf-8")
        (out / f"{run_id}.zip").write_bytes(b"local")
        return True

    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.run_simulation",
        fake_run,
    )
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.run_simulation_subprocess",
        fake_run,
    )
    args = [
        "--tier", "t1", "--platform", "destroyer_baseline",
        "--epochs", "2", "--num-agents", "20", "--limit", "2",
        "--in-process",
    ]
    assert main(args) == 0
    first_ids = calls[:2]
    args[args.index("--limit") + 1] = "1"
    assert main([*args, "--resume"]) == 0
    manifest = json.loads(
        (out / "single.manifest.json").read_text(encoding="utf-8"),
    )
    assert [entry["run_id"] for entry in manifest] == calls[:3]
    assert first_ids == calls[:2]


def test_shard_accumulation_isolated_by_shard_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    out = tmp_path / "mega_cruise_campaign"
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.OUTPUT_ROOT",
        out,
    )
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.COMPLETED_LOG",
        out / "completed_runs.txt",
    )
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.FAILED_LOG",
        out / "failed_runs.txt",
    )

    def fake_run(run_id: str, spec: dict, **kwargs: Any) -> bool:
        suffix = kwargs.get("accumulation_suffix", "single")
        run_dir = out / "_shard_runs" / suffix / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "summary.json").write_text(
            json.dumps({
                "run_id": run_id,
                "parameters": {},
                "derived": {},
            }),
            encoding="utf-8",
        )
        (run_dir / "timeseries.json").write_text("[]", encoding="utf-8")
        (out / f"{run_id}.zip").write_bytes(b"local")
        return True

    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.run_simulation",
        fake_run,
    )
    monkeypatch.setattr(
        "picard_framework.runs.mega_cruise_campaign.campaign_runner.run_simulation_subprocess",
        fake_run,
    )
    common = [
        "--tier", "t1", "--platform", "destroyer_baseline",
        "--epochs", "2", "--num-agents", "20", "--limit", "2",
        "--in-process", "--shard-count", "2",
    ]
    assert main([*common, "--shard-index", "0"]) == 0
    assert main([*common, "--shard-index", "1"]) == 0

    shard_runs: dict[str, set[str]] = {}
    for suffix in ("shard-0", "shard-1"):
        with zipfile.ZipFile(out / f"{suffix}.zip") as zf:
            shard_runs[suffix] = {
                name.split("/", 1)[0] for name in zf.namelist()
            }
        manifest = json.loads(
            (out / f"{suffix}.manifest.json").read_text(encoding="utf-8"),
        )
        assert {entry["run_id"] for entry in manifest} == shard_runs[suffix]
    assert shard_runs["shard-0"].isdisjoint(shard_runs["shard-1"])


# ---------------------------------------------------------------------------
# Multi-platform calibration (c1–c4) — calibration_manifest_v1.json
# ---------------------------------------------------------------------------

PLATFORM_AGENT_COUNTS = {
    "expedition_cruise_450": 450,
    "classic_cruise_1900": 1910,
    "spirit_cruise_3000": 3000,
    "mega_cruise_5000": 7000,
}


def _calibration_manifest() -> dict[str, Any]:
    return load_manifest(CALIBRATION_MANIFEST)


def _assert_isolates(spec: dict[str, Any], pathogen_id: str) -> None:
    """An arm removes every pathogen in its bundle except its own.

    Asserted as a set relation rather than a literal list because the
    removals are derived from the bundle, so adding a pathogen to the bundle
    extends the list without changing the arm's contract.
    """
    bundle = load_pathogen_bundle(
        str(REPO_ROOT / "data" / "pathogens" / "active_profiles.json"),
    )
    removed = set(spec["pathogen_overrides"]["remove"])
    assert pathogen_id not in removed
    assert set(bundle) - {pathogen_id} <= removed


def test_calibration_manifest_loads() -> None:
    manifest = _calibration_manifest()
    assert manifest["campaign"] == "multi_platform_calibration_v1"
    assert "c1_expedition_cruise_450" in manifest["tiers"]
    assert "c2_immunity_sweep" in manifest["tiers"]
    assert "c3_sarscov2_calibration" in manifest["tiers"]
    assert "c4_voyage_duration" in manifest["tiers"]
    assert "c5_density_calibration" in manifest["tiers"]
    assert "c6_heterogeneous_sensitivity" in manifest["tiers"]
    assert "none_true" in manifest["surveillance_configs"]


def test_resolve_calibration_tier_prefixes() -> None:
    manifest = _calibration_manifest()
    c1 = resolve_tier_ids(manifest, "c1")
    assert len(c1) == 4
    assert all(t.startswith("c1_") for t in c1)
    assert resolve_tier_ids(manifest, "c2") == ["c2_immunity_sweep"]
    assert resolve_tier_ids(manifest, "c4") == ["c4_voyage_duration"]
    assert resolve_tier_ids(manifest, "c5") == ["c5_density_calibration"]
    assert resolve_tier_ids(manifest, "c6") == ["c6_heterogeneous_sensitivity"]


def test_calibration_dry_run_counts() -> None:
    """Golden run counts from calibration_manifest_v1 factorials."""
    manifest = _calibration_manifest()
    expected = {
        # 11 doses × 2 init × 2 surv × 20 seeds
        "c1_expedition_cruise_450": 880,
        # 7 × 2 × 2 × 15
        "c1_classic_cruise_1900": 420,
        # 7 × 2 × 2 × 10
        "c1_spirit_cruise_3000": 280,
        # 6 × 2 × 2 × 10
        "c1_mega_cruise_5000": 240,
        # 4 platforms × 5 immunity × 2 surv × 10 seeds
        "c2_immunity_sweep": 400,
        # 2 platforms × 6 doses × 1 init × 2 surv × 15 seeds
        "c3_sarscov2_calibration": 360,
        # 3 epochs × 3 doses × 2 surv × 10 seeds
        "c4_voyage_duration": 180,
        # 4 plat × 3 dose × 5 α × 2 imm × 2 surv × 15 seeds
        "c5_density_calibration": 3600,
    }
    total = 0
    for tier_id, n_exp in expected.items():
        runs = list(generate_tier_runs(manifest, tier_id))
        assert len(runs) == n_exp, f"{tier_id}: {len(runs)} != {n_exp}"
        total += len(runs)
    assert total == 6360


def _clock_arm_c1_manifest() -> dict[str, Any]:
    return load_manifest(CLOCK_ARM_C1_MANIFEST)


def test_clock_arm_c1_manifest_loads() -> None:
    manifest = _clock_arm_c1_manifest()
    assert manifest["campaign"] == "clock_arm_c1_refit_v1"
    assert set(manifest["tiers"]) == {
        "c1_expedition_cruise_450",
        "c1_classic_cruise_1900",
        "c1_spirit_cruise_3000",
        "c1_mega_cruise_5000",
    }
    assert manifest["pathogen_configs"]["norovirus"]["pathogen_id"] == "norwalk_gi"


def test_clock_arm_c1_dry_run_counts() -> None:
    """Golden run counts from the focused C1 clock-arm factorials."""
    manifest = _clock_arm_c1_manifest()
    expected = {
        # 6 doses × 2 init × 2 surv × 20 seeds
        "c1_expedition_cruise_450": 480,
        # 8 × 2 × 2 × 20
        "c1_classic_cruise_1900": 640,
        # 8 × 2 × 2 × 20
        "c1_spirit_cruise_3000": 640,
        # 8 × 2 × 2 × 20
        "c1_mega_cruise_5000": 640,
    }
    total = 0
    for tier_id, n_exp in expected.items():
        runs = list(generate_tier_runs(manifest, tier_id))
        assert len(runs) == n_exp, f"{tier_id}: {len(runs)} != {n_exp}"
        total += len(runs)
    assert total == 2400


def _single_dose_hours_manifest() -> dict[str, Any]:
    return load_manifest(SINGLE_DOSE_HOURS_MANIFEST)


def test_single_dose_hours_manifest_loads() -> None:
    manifest = _single_dose_hours_manifest()
    assert manifest["campaign"] == "c1_single_dose_hours_v1"
    assert set(manifest["tiers"]) == {
        "c1_expedition_cruise_450",
        "c1_classic_cruise_1900",
        "c1_spirit_cruise_3000",
        "c1_mega_cruise_5000",
    }
    assert manifest["pathogen_configs"]["norovirus"]["pathogen_id"] == "norwalk_gi"


def test_single_dose_hours_dry_run_counts() -> None:
    """Golden run counts for the hourly single-dose C1 refit."""
    manifest = _single_dose_hours_manifest()
    expected = {
        # 7 doses × 1 init × 2 surv × 40 seeds
        "c1_expedition_cruise_450": 560,
        "c1_classic_cruise_1900": 560,
        "c1_spirit_cruise_3000": 560,
        "c1_mega_cruise_5000": 560,
    }
    total = 0
    for tier_id, n_exp in expected.items():
        runs = list(generate_tier_runs(manifest, tier_id))
        assert len(runs) == n_exp, f"{tier_id}: {len(runs)} != {n_exp}"
        total += len(runs)
    assert total == 2240


def _reported_case_refit_manifest() -> dict[str, Any]:
    return load_manifest(REPORTED_CASE_REFIT_MANIFEST)


def test_reported_case_refit_manifest_loads() -> None:
    manifest = _reported_case_refit_manifest()
    assert manifest["campaign"] == "c1_reported_case_refit_v1"
    assert set(manifest["tiers"]) == {
        "c1_expedition_cruise_450",
        "c1_classic_cruise_1900",
        "c1_spirit_cruise_3000",
        "c1_mega_cruise_5000",
    }
    assert manifest["pathogen_configs"]["norovirus"]["pathogen_id"] == "norwalk_gi"
    assert manifest["tiers"]["c1_expedition_cruise_450"]["epochs"] == 168


def test_reported_case_refit_dry_run_counts_and_specs() -> None:
    """Lock the corrected-model C1 factorial and hourly run wiring."""
    manifest = _reported_case_refit_manifest()
    expected_tiers = {
        "c1_expedition_cruise_450": 720,
        "c1_classic_cruise_1900": 720,
        "c1_spirit_cruise_3000": 720,
        "c1_mega_cruise_5000": 720,
    }
    total = 0
    for tier_id, expected in expected_tiers.items():
        runs = list(generate_tier_runs(manifest, tier_id, natural_history_clock="hours"))
        assert len(runs) == expected, f"{tier_id}: {len(runs)} != {expected}"
        for run_id, spec in runs:
            assert spec["config_overrides"]["natural_history_clock"] == "hours"
            assert spec["campaign_parameters"]["natural_history_clock"] == "hours"
            assert spec["campaign_parameters"]["dose_adjustment"] in (
                manifest["tiers"][tier_id]["dose_adjustments"]
            )
            assert spec["campaign_parameters"]["seed"] in range(760, 800)
            assert "legacy_epoch_day" not in repr(spec)
            assert run_id.startswith("c1_norovirus_")
        total += len(runs)
    assert total == 2880


def test_campaign_generator_c5() -> None:
    """c5 dry-run count and density exponent wiring."""
    manifest = _calibration_manifest()
    runs = list(generate_tier_runs(manifest, "c5_density_calibration"))
    assert len(runs) == 3600
    rid, spec = next(
        (r, s) for r, s in runs
        if "a050" in r and "dose15" in r and "mega_cruise_5000" in r
    )
    assert "imm0" in rid or "imm20" in rid
    tx = spec["config_overrides"]["transmission"]
    assert tx["contact_mode"] == "density_dependent"
    assert tx["density_dependent"]["exponent"] == pytest.approx(0.5)
    assert spec["campaign_parameters"]["density_exponent"] == pytest.approx(0.5)
    assert spec["pathogen_overrides"]["norwalk_gi"]["dose_adjustment"] == pytest.approx(15.0)
    assert spec["pathogen_overrides"]["norwalk_gi"]["initial_infected"] == 1


def test_c5_exponent_sensitivity_in_overrides() -> None:
    """Changing density exponent in the c5 sweep changes the config override."""
    manifest = _calibration_manifest()
    runs = list(generate_tier_runs(manifest, "c5_density_calibration"))
    a0 = next(s for r, s in runs if "_a000_" in r)
    a1 = next(s for r, s in runs if "_a100_" in r)
    assert a0["config_overrides"]["transmission"]["density_dependent"]["exponent"] == (
        pytest.approx(0.0)
    )
    assert a1["config_overrides"]["transmission"]["density_dependent"]["exponent"] == (
        pytest.approx(1.0)
    )
    assert (
        a0["config_overrides"]["transmission"]["density_dependent"]["exponent"]
        != a1["config_overrides"]["transmission"]["density_dependent"]["exponent"]
    )


def test_a2_reuses_calibration_generator_with_density_and_immunity() -> None:
    """sensitivity_a2_phase1 tiers share the c1–c6 generator (pinned alpha)."""
    a2 = Path.home() / "Downloads" / "sensitivity_a2_phase1_manifest.json"
    if not a2.is_file():
        pytest.skip("Downloads/sensitivity_a2_phase1_manifest.json not present")
    with open(a2, encoding="utf-8") as fh:
        manifest = json.load(fh)
    runs = list(generate_tier_runs(manifest, "a2_expedition_cruise_450"))
    # 9 doses × 1 alpha × 11 immunity × 1 init × 2 surv × 30 seeds
    assert len(runs) == 9 * 1 * 11 * 1 * 2 * 30
    rid, spec = next(
        (r, s) for r, s in runs
        if "dose15" in r and "a075" in r and "imm20" in r and "syndromic" in r
    )
    assert rid.startswith("a2_norovirus_expedition_cruise_450_")
    tx = spec["config_overrides"]["transmission"]
    assert tx["contact_mode"] == "density_dependent"
    assert tx["density_dependent"]["exponent"] == pytest.approx(0.75)
    assert spec["campaign_parameters"]["density_exponent"] == pytest.approx(0.75)
    assert spec["pathogen_overrides"]["norwalk_gi"]["dose_adjustment"] == pytest.approx(15.0)
    assert resolve_tier_ids(manifest, "a2") == [
        "a2_classic_cruise_1900",
        "a2_expedition_cruise_450",
        "a2_mega_cruise_5000",
        "a2_spirit_cruise_3000",
    ]


def test_campaign_generator_c6() -> None:
    """c6 dry-run: density vs heterogeneous contact_mode at pinned α/dose."""
    manifest = _calibration_manifest()
    assert manifest["tiers"]["c6_heterogeneous_sensitivity"].get("deferred") is True
    runs = list(generate_tier_runs(manifest, "c6_heterogeneous_sensitivity"))
    # 4 platforms × 1 dose × 1 α × 2 modes × 1 imm × 2 surv × 10 seeds
    assert len(runs) == 160
    dd = next(s for r, s in runs if "_dd_" in r and "mega_cruise_5000" in r)
    het = next(s for r, s in runs if "_het_" in r and "mega_cruise_5000" in r)
    assert dd["config_overrides"]["transmission"]["contact_mode"] == "density_dependent"
    assert het["config_overrides"]["transmission"]["contact_mode"] == (
        "heterogeneous_zone_dose"
    )
    assert dd["config_overrides"]["transmission"]["density_dependent"]["exponent"] == (
        pytest.approx(0.5)
    )
    assert het["campaign_parameters"]["contact_mode"] == "heterogeneous_zone_dose"
    assert dd["campaign_parameters"]["contact_mode"] == "density_dependent"


def test_c1_sets_platform_agents_dose_and_init() -> None:
    manifest = _calibration_manifest()
    runs = list(generate_tier_runs(manifest, "c1_expedition_cruise_450"))
    rid, spec = next(
        (r, s) for r, s in runs
        if "dose5" in r and "init1" in r and "none_true" in r
    )
    assert "expedition_cruise_450" in rid
    assert spec["catalog"]["platform_id"] == "expedition_cruise_450"
    assert spec["config_overrides"]["ship_graph"]["num_agents"] == 450
    assert spec["pathogen_overrides"]["norwalk_gi"]["dose_adjustment"] == pytest.approx(5.0)
    assert spec["pathogen_overrides"]["norwalk_gi"]["initial_infected"] == 1
    _assert_isolates(spec, "norwalk_gi")
    assert spec["run"]["num_epochs"] == 168
    assert spec["campaign_parameters"]["dose_adjustment"] == pytest.approx(5.0)
    assert spec["campaign_parameters"]["n_init"] == 1


def test_c1_platforms_use_canonical_agent_counts() -> None:
    manifest = _calibration_manifest()
    for tier_id, platform_id, n_agents in (
        ("c1_expedition_cruise_450", "expedition_cruise_450", 450),
        ("c1_classic_cruise_1900", "classic_cruise_1900", 1910),
        ("c1_spirit_cruise_3000", "spirit_cruise_3000", 3000),
        ("c1_mega_cruise_5000", "mega_cruise_5000", 7000),
    ):
        _rid, spec = next(generate_tier_runs(manifest, tier_id))
        assert spec["catalog"]["platform_id"] == platform_id
        assert spec["config_overrides"]["ship_graph"]["num_agents"] == n_agents


def test_c1_dose_adjustment_sensitivity() -> None:
    """Changing dose_adjustment in the sweep changes the pathogen override."""
    manifest = _calibration_manifest()
    runs = list(generate_tier_runs(manifest, "c1_mega_cruise_5000"))
    dose1 = next(s for r, s in runs if "dose1_" in r and "init1_" in r)
    dose15 = next(s for r, s in runs if "dose15_" in r and "init1_" in r)
    assert dose1["pathogen_overrides"]["norwalk_gi"]["dose_adjustment"] == pytest.approx(1.0)
    assert dose15["pathogen_overrides"]["norwalk_gi"]["dose_adjustment"] == pytest.approx(15.0)
    assert (
        dose1["pathogen_overrides"]["norwalk_gi"]["dose_adjustment"]
        != dose15["pathogen_overrides"]["norwalk_gi"]["dose_adjustment"]
    )


def test_c2_sweeps_immunity_across_platforms() -> None:
    manifest = _calibration_manifest()
    runs = list(generate_tier_runs(manifest, "c2_immunity_sweep"))
    platforms = {s["catalog"]["platform_id"] for _, s in runs}
    assert platforms == set(PLATFORM_AGENT_COUNTS)
    sample = next(s for r, s in runs if "imm20" in r and "classic_cruise_1900" in r)
    assert sample["config_overrides"]["ship_graph"]["immune_fraction"] == pytest.approx(0.2)
    assert sample["config_overrides"]["ship_graph"]["num_agents"] == 1910
    # No dose/init patch when tier omits those fields.
    assert "norwalk_gi" not in sample.get("pathogen_overrides", {})
    _assert_isolates(sample, "norwalk_gi")


def test_c2_accepts_singular_dose_adjustment_after_c1() -> None:
    """c2 note: pin best dose from C1 via singular dose_adjustment."""
    manifest = _calibration_manifest()
    tier = manifest["tiers"]["c2_immunity_sweep"]
    tier["dose_adjustment"] = 7.0
    runs = list(generate_tier_runs(manifest, "c2_immunity_sweep"))
    rid, spec = next(
        (r, s) for r, s in runs
        if "dose7" in r and "imm0_" in r and "mega_cruise_5000" in r
    )
    assert "dose7" in rid
    assert spec["pathogen_overrides"]["norwalk_gi"]["dose_adjustment"] == pytest.approx(7.0)


def test_c3_sarscov2_multi_platform_dose_sweep() -> None:
    manifest = _calibration_manifest()
    runs = list(generate_tier_runs(manifest, "c3_sarscov2_calibration"))
    platforms = {s["catalog"]["platform_id"] for _, s in runs}
    assert platforms == {"mega_cruise_5000", "expedition_cruise_450"}
    sample = next(
        s for r, s in runs
        if "dose10" in r and "expedition_cruise_450" in r and "init1" in r
    )
    assert sample["catalog"]["platform_id"] == "expedition_cruise_450"
    assert sample["config_overrides"]["ship_graph"]["num_agents"] == 450
    assert sample["pathogen_overrides"]["sars_cov2_resp"]["dose_adjustment"] == pytest.approx(10.0)
    assert sample["pathogen_overrides"]["sars_cov2_resp"]["initial_infected"] == 1
    _assert_isolates(sample, "sars_cov2_resp")
    assert sample["catalog"]["pathogen_bundle_id"] == "active_profiles"


def test_c4_varies_num_epochs_from_epoch_durations() -> None:
    manifest = _calibration_manifest()
    runs = list(generate_tier_runs(manifest, "c4_voyage_duration"))
    by_ep = {}
    for rid, spec in runs:
        if "dose7" in rid and "none_true" in rid and rid.endswith("_s500"):
            by_ep[spec["run"]["num_epochs"]] = rid
    assert set(by_ep) == {72, 168, 336}
    assert "ep72" in by_ep[72]
    assert "ep168" in by_ep[168]
    assert "ep336" in by_ep[336]
    # Platform + dose tagged; mega uses 7000 agents.
    sample = next(s for r, s in runs if "ep168" in r and "dose15" in r)
    assert sample["catalog"]["platform_id"] == "mega_cruise_5000"
    assert sample["config_overrides"]["ship_graph"]["num_agents"] == 7000
    assert sample["pathogen_overrides"]["norwalk_gi"]["dose_adjustment"] == pytest.approx(15.0)
    assert sample["campaign_parameters"]["num_epochs"] == 168


def test_calibration_num_agents_override() -> None:
    manifest = _calibration_manifest()
    _rid, spec = next(
        generate_tier_runs(
            manifest, "c1_expedition_cruise_450", num_agents_override=50,
        ),
    )
    assert spec["config_overrides"]["ship_graph"]["num_agents"] == 50


def test_c2_is_deferred_from_all_selection() -> None:
    manifest = _calibration_manifest()
    assert manifest["tiers"]["c2_immunity_sweep"].get("deferred") is True
    assert manifest["tiers"]["c6_heterogeneous_sensitivity"].get("deferred") is True
    all_tiers = resolve_tier_ids(manifest, "all")
    assert "c2_immunity_sweep" not in all_tiers
    assert "c6_heterogeneous_sensitivity" not in all_tiers
    assert "c1_mega_cruise_5000" in all_tiers
    assert "c3_sarscov2_calibration" in all_tiers
    assert "c4_voyage_duration" in all_tiers
    assert "c5_density_calibration" in all_tiers
    with_deferred = resolve_tier_ids(manifest, "all", include_deferred=True)
    assert "c2_immunity_sweep" in with_deferred
    assert "c6_heterogeneous_sensitivity" in with_deferred
    # Explicit prefix still selects deferred wave-2 tier.
    assert resolve_tier_ids(manifest, "c2") == ["c2_immunity_sweep"]
    assert resolve_tier_ids(manifest, "c6") == ["c6_heterogeneous_sensitivity"]


def test_calibration_wave1_dry_run_excludes_c2() -> None:
    """Wave-1 Batch submit uses --tier all → 5960 runs (no deferred c2/c6)."""
    manifest = _calibration_manifest()
    total = 0
    for tier_id in resolve_tier_ids(manifest, "all"):
        total += len(list(generate_tier_runs(manifest, tier_id)))
    assert total == 5960


BOUNDARY_MANIFEST = CAMPAIGN / "boundary_surface_v1_manifest.json"


def test_boundary_surface_manifest_cartesian_counts() -> None:
    """Light arithmetic check — do not expand Picard specs for all 17.6k."""
    from picard_framework.runs.mega_cruise_campaign.count_manifest_cartesian import (
        summarize,
        tier_cartesian,
    )

    manifest = load_manifest(BOUNDARY_MANIFEST)
    assert manifest["campaign"] == "boundary_surface_v1"
    assert "syndromic" in manifest["surveillance_configs"]
    assert all(k in manifest["pathogen_configs"] for k in (
        "norovirus", "sarscov2", "influenza", "measles",
    ))
    assert tier_cartesian(manifest, manifest["tiers"]["b1_norovirus"]) == 2400
    assert tier_cartesian(manifest, manifest["tiers"]["b1_measles"]) == 2800
    assert manifest["tiers"]["b2_sarscov2_sensitivity"].get("deferred") is True
    wave1, wave2 = summarize(manifest)
    assert wave1 == 10000
    assert wave2 == 7600


def test_boundary_b1_generator_smoke_one_run() -> None:
    """Single next() — proves b1 hits the c1/a2 generator without full expand."""
    manifest = load_manifest(BOUNDARY_MANIFEST)
    rid, spec = next(generate_tier_runs(manifest, "b1_norovirus"))
    assert rid.startswith("b1_norovirus_")
    assert "init" in rid
    assert spec["catalog"]["platform_id"] in {
        "expedition_cruise_450",
        "classic_cruise_1900",
        "spirit_cruise_3000",
        "mega_cruise_5000",
    }
    noro = spec["pathogen_overrides"]["norwalk_gi"]
    assert noro["dose_adjustment"] == pytest.approx(10.6)
    wave1 = resolve_tier_ids(manifest, "all")
    assert set(wave1) == {
        "b1_norovirus",
        "b1_sarscov2",
        "b1_influenza",
        "b1_measles",
    }
    deferred = resolve_tier_ids(manifest, "all", include_deferred=True)
    assert "b2_measles_sensitivity" in deferred


SR_MANIFEST = CAMPAIGN / "synthetic_recovery_v1_manifest.json"
VD_MANIFEST = CAMPAIGN / "vsp_degradation_v1_manifest.json"


def test_synthetic_recovery_cartesian_and_generator() -> None:
    from picard_framework.runs.mega_cruise_campaign.count_manifest_cartesian import (
        summarize,
        tier_cartesian,
    )

    manifest = load_manifest(SR_MANIFEST)
    assert manifest["campaign"] == "synthetic_recovery_v1"
    assert tier_cartesian(manifest, manifest["tiers"]["sr1_ridge"]) == 1200
    wave1, wave2 = summarize(manifest)
    assert wave1 == 1200
    assert wave2 == 0

    rid, spec = next(generate_tier_runs(manifest, "sr1_ridge"))
    assert rid.startswith("sr_norovirus_")
    assert "ridge_" in rid or "off_ridge" in rid
    noro = spec["pathogen_overrides"]["norwalk_gi"]
    assert "dose_adjustment" in noro
    assert noro["initial_infected"] == 3
    assert "innate_nonsusceptible_fraction" in noro
    tx = spec["config_overrides"]["transmission"]
    assert tx["contact_mode"] == "density_dependent"
    assert "exponent" in tx["density_dependent"]


def test_vsp_degradation_cartesian_and_generator() -> None:
    from picard_framework.runs.mega_cruise_campaign.count_manifest_cartesian import (
        summarize,
        tier_cartesian,
    )

    manifest = load_manifest(VD_MANIFEST)
    assert manifest["campaign"] == "vsp_degradation_v1"
    assert tier_cartesian(manifest, manifest["tiers"]["vd1_vsp_threshold"]) == 840
    assert tier_cartesian(manifest, manifest["tiers"]["vd1_detection_delay"]) == 720
    assert (
        tier_cartesian(manifest, manifest["tiers"]["vd1_isolation_compliance"]) == 600
    )
    assert (
        tier_cartesian(manifest, manifest["tiers"]["vd1_sick_call_probability"]) == 600
    )
    assert (
        tier_cartesian(manifest, manifest["tiers"]["vd2_threshold_x_compliance"])
        == 720
    )
    assert tier_cartesian(manifest, manifest["tiers"]["vd2_delay_x_reporting"]) == 720
    assert (
        tier_cartesian(manifest, manifest["tiers"]["vd2_worst_case_gradient"]) == 2160
    )
    wave1, wave2 = summarize(manifest)
    assert wave1 == 6360
    assert wave2 == 0

    rid, spec = next(generate_tier_runs(manifest, "vd1_vsp_threshold"))
    assert rid.startswith("vd_norovirus_")
    assert "vsp" in rid
    cfg = spec["config_overrides"]
    assert "lockdown_attack_rate" in cfg["escalation"]
    assert "detection_delay_hours" in cfg["medical_response"]
    assert "isolation_compliance" in cfg["medical_response"]
    params = spec["campaign_parameters"]
    assert params["dose_adjustment"] == pytest.approx(10.6)
    assert params["density_exponent"] == pytest.approx(0.75)


SENTINEL_MANIFEST = CAMPAIGN / "sentinel_synthetic_recovery_v1_manifest.json"


def test_sentinel_recovery_cartesian_and_generator() -> None:
    from picard_framework.runs.mega_cruise_campaign.count_manifest_cartesian import (
        summarize,
        tier_cartesian,
    )

    manifest = load_manifest(SENTINEL_MANIFEST)
    assert manifest["campaign"] == "sentinel_synthetic_recovery_v1"
    assert tier_cartesian(manifest, manifest["tiers"]["sr_uniform_low_single"]) == 80
    assert (
        tier_cartesian(manifest, manifest["tiers"]["sr_uniform_low_fleet_same"]) == 240
    )
    wave1, wave2 = summarize(manifest)
    assert wave1 == 3360
    assert wave2 == 0

    rid, spec = next(generate_tier_runs(manifest, "sr_uniform_low_single"))
    assert rid.startswith("sr_norovirus_mega_cruise_5000_uniform_low_single_")
    voyage = spec["config_overrides"]["voyage"]
    assert voyage["effects_enabled"] is True
    assert voyage["shore_exposure"]["enabled"] is True
    hazards = {
        day["port_id"]: day["shore_infection_probability"]
        for day in voyage["itinerary"]
        if day.get("type") == "port_day"
    }
    assert hazards == {"MXCZM": 0.0001, "MXCTM": 0.0001, "KYGEC": 0.0001}
    params = spec["campaign_parameters"]
    assert params["R_onboard"] == pytest.approx(0.0)
    assert params["n_init"] == 0
    assert spec["pathogen_overrides"]["norwalk_gi"]["initial_infected"] == 0
    sea = voyage["defaults"]["sea_day"]["contact_rate_multiplier"]
    assert sea == pytest.approx(0.0)


def test_sentinel_recovery_fleet_crossed_itineraries() -> None:
    manifest = load_manifest(SENTINEL_MANIFEST)
    runs = list(generate_tier_runs(manifest, "sr_one_hot_fleet_crossed"))
    assert len(runs) == 240
    by_plat: dict[str, dict[str, Any]] = {}
    for rid, spec in runs:
        if "_R0p0_s300" not in rid:
            continue
        plat = spec["campaign_parameters"]["platform_id"]
        by_plat[plat] = spec
    assert set(by_plat) == {
        "mega_cruise_5000",
        "spirit_cruise_3000",
        "classic_cruise_1900",
    }
    mega_days = [
        d for d in by_plat["mega_cruise_5000"]["config_overrides"]["voyage"]["itinerary"]
        if d.get("type") == "port_day"
    ]
    spirit_days = [
        d
        for d in by_plat["spirit_cruise_3000"]["config_overrides"]["voyage"]["itinerary"]
        if d.get("type") == "port_day"
    ]
    classic_days = [
        d
        for d in by_plat["classic_cruise_1900"]["config_overrides"]["voyage"]["itinerary"]
        if d.get("type") == "port_day"
    ]
    assert [d["port_id"] for d in mega_days] == ["MXCZM", "MXCTM", "KYGEC"]
    assert [d["day"] for d in mega_days] == [3, 4, 6]
    assert [d["port_id"] for d in spirit_days] == ["KYGEC", "MXCTM", "MXCZM"]
    assert [d["day"] for d in classic_days] == [2, 4, 5]
    assert classic_days[0]["port_id"] == "MXCZM"
    hot = by_plat["mega_cruise_5000"]["campaign_parameters"]["port_hazards"]
    assert hot["MXCZM"] == pytest.approx(0.001)


def test_sentinel_recovery_null_onboard_seed() -> None:
    manifest = load_manifest(SENTINEL_MANIFEST)
    seeded = [
        spec
        for rid, spec in generate_tier_runs(manifest, "sr_null_single")
        if spec["campaign_parameters"]["R_onboard"] == 1.0
    ]
    empty = [
        spec
        for rid, spec in generate_tier_runs(manifest, "sr_null_single")
        if spec["campaign_parameters"]["R_onboard"] == 0.0
    ]
    assert seeded[0]["pathogen_overrides"]["norwalk_gi"]["initial_infected"] == 1
    assert empty[0]["pathogen_overrides"]["norwalk_gi"]["initial_infected"] == 0
