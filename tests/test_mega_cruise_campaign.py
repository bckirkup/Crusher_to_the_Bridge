"""Tests for mega_cruise_campaign runner (generation + smoke)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from typing import Any  # noqa: E402

from picard_framework.runs.mega_cruise_campaign.campaign_runner import (  # noqa: E402
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
    assert sample["config_overrides"]["syndromic"]["activation_delay_epochs"] == 24
    assert sample["config_overrides"]["diagnostic_cascade"]["activation_delay_epochs"] == 24
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
    assert "filter" in p2 and "oa" in p2 and "decay" in p2
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
                        "quarantined": 0, "isolated": 0},
            "cost_accounting": {"total_financial_usd": 5.0,
                                "operational_impact_cumulative": 1.0},
            "spaces": {"A": {"concentration_per_m3": 2.0, "pathogen_mass": 3.0}},
        },
        {
            "epoch": 1, "trigger_status": "SUSPECTED",
            "summary": {"susceptible": 8, "infected": 3, "recovered": 1,
                        "quarantined": 2, "isolated": 1},
            "cost_accounting": {"total_financial_usd": 9.0,
                                "operational_impact_cumulative": 2.0},
            "spaces": {"A": {"concentration_per_m3": 0.5, "pathogen_mass": 1.0}},
        },
        {
            "epoch": 2, "trigger_status": "CONFIRMED",
            "summary": {"susceptible": 6, "infected": 1, "recovered": 4,
                        "quarantined": 1, "isolated": 0},
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
    # Incidence = Δ(I+R): 1, then 3, then 1 — not the old ΔR+I formula.
    assert [e["new_infections"] for e in ts] == [1, 3, 1]
    assert extract_timeseries([]) == []


def test_compute_derived_metrics() -> None:
    ts = extract_timeseries(_sample_history())
    derived = compute_derived_metrics(ts, num_agents=1000)
    assert derived["peak_prevalence"] == 3
    assert derived["peak_epoch"] == 1
    assert derived["outbreak_occurred"] is True
    assert derived["detection_epoch"] == 1
    assert derived["confirmation_epoch"] == 2
    # Attack rate uses (I+R)_final / N = 5/1000.
    assert derived["attack_rate"] == pytest.approx(0.005)
    assert derived["total_quarantine_person_epochs"] == 3
    assert derived["r_effective_at_peak"] == pytest.approx(3.0)
    # Empty series must not raise (no max([])).
    assert compute_derived_metrics([], num_agents=1000) == {}


@pytest.mark.timeout(180)
def test_smoke_cli_one_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end via the default subprocess-isolated path: one run -> one zip."""
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
    zips = list(out.glob("*.zip"))
    assert len(zips) == 1
    completed = (out / "completed_runs.txt").read_text(encoding="utf-8").strip()
    assert completed
    # summary present in workdir when keep_workdir
    work = out / completed
    assert (work / "summary.json").is_file()
    summary = json.loads((work / "summary.json").read_text(encoding="utf-8"))
    assert "summary" in summary
    assert "derived" in summary
    assert "parameters" in summary
    assert summary["parameters"]["seed"] is not None
    assert summary["parameters"].get("history_retention") == "compact"
    # timeseries.json is written and packed into the zip.
    assert (work / "timeseries.json").is_file()
    with zipfile.ZipFile(zips[0]) as zf:
        names = zf.namelist()
    assert any(n.endswith("timeseries.json") for n in names)
    assert any(n.endswith("summary.json") for n in names)


@pytest.mark.timeout(120)
def test_smoke_in_process(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--in-process runs one sim in the parent and still writes the zip."""
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
    assert len(list(out.glob("*.zip"))) == 1


def _load_aggregator():
    import importlib.util

    path = REPO_ROOT / "deploy" / "aws" / "aggregate_results.py"
    spec = importlib.util.spec_from_file_location("aggregate_results", path)
    assert spec and spec.loader
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
    assert spec is not None and spec.loader is not None
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
            assert "_resume/completed_runs" in name
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
    from engines.py_contam_bridge import build_transport_engine

    base_cfg = {
        "ship_graph": {
            "spatial_layout": "data/platforms/mega_cruise_5000/spatial_layout.json",
            "air_flow_paths": "data/platforms/mega_cruise_5000/air_flow_paths.json",
        },
        "hvac": {"transport_engine": "native", "oa_fraction": 0.2},
    }
    high_oa = {
        **base_cfg,
        "hvac": {"transport_engine": "native", "oa_fraction": 0.4},
    }
    from engines.py_contam_bridge import PATH_TYPE_HVAC_SUPPLY

    eng_lo = build_transport_engine(str(REPO_ROOT), base_cfg)
    eng_hi = build_transport_engine(str(REPO_ROOT), high_oa)
    assert eng_lo is not None and eng_hi is not None
    supplies_lo = [
        p.flow_rate_m3h for p in eng_lo.airflow_paths
        if p.path_type == PATH_TYPE_HVAC_SUPPLY
    ]
    supplies_hi = [
        p.flow_rate_m3h for p in eng_hi.airflow_paths
        if p.path_type == PATH_TYPE_HVAC_SUPPLY
    ]
    assert supplies_lo and supplies_hi
    # Higher OA → less recirculated supply.
    assert sum(supplies_hi) < sum(supplies_lo)


def test_contamx_build_applies_hvac_oa_fraction(monkeypatch: pytest.MonkeyPatch) -> None:
    """build_contamx_engine must re-apply hvac.oa_fraction after disk reload."""
    from engines import contamx_transport as cx

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

    cfg = {"hvac": {"oa_fraction": 0.35}}
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
    assert spec and spec.loader
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
    assert len(zips) == 1
    assert (out / "completed_runs.txt").is_file()


def test_resume_skips_when_s3_zip_already_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On --resume, an existing S3 zip should mark the run completed and skip it."""
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
            return False

        def object_exists(self, name: str) -> bool:
            # Pretend every run zip already landed in S3.
            return name.endswith(".zip")

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

    # Smoke selects t1/limit 1; with all zips present in S3 the first candidate
    # is skipped and marked completed without invoking the simulator.
    rc = main([
        "--smoke", "--resume",
        "--s3-prefix", "s3://fake-bucket/campaign/",
        "--in-process",
    ])
    assert rc == 0
    assert called == []
    completed = (out / "completed_runs.txt").read_text(encoding="utf-8").strip()
    assert completed  # at least the first smoke candidate was marked done
    assert not list(out.glob("*.zip"))  # no local zip written when skipped


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


def test_calibration_manifest_loads() -> None:
    manifest = _calibration_manifest()
    assert manifest["campaign"] == "multi_platform_calibration_v1"
    assert "c1_expedition_cruise_450" in manifest["tiers"]
    assert "c2_immunity_sweep" in manifest["tiers"]
    assert "c3_sarscov2_calibration" in manifest["tiers"]
    assert "c4_voyage_duration" in manifest["tiers"]
    assert "none_true" in manifest["surveillance_configs"]


def test_resolve_calibration_tier_prefixes() -> None:
    manifest = _calibration_manifest()
    c1 = resolve_tier_ids(manifest, "c1")
    assert len(c1) == 4
    assert all(t.startswith("c1_") for t in c1)
    assert resolve_tier_ids(manifest, "c2") == ["c2_immunity_sweep"]
    assert resolve_tier_ids(manifest, "c4") == ["c4_voyage_duration"]


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
    }
    total = 0
    for tier_id, n_exp in expected.items():
        runs = list(generate_tier_runs(manifest, tier_id))
        assert len(runs) == n_exp, f"{tier_id}: {len(runs)} != {n_exp}"
        total += len(runs)
    assert total == 2760


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
    assert spec["pathogen_overrides"]["remove"] == ["sars_cov2_resp"]
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
    assert sample["pathogen_overrides"]["remove"] == ["sars_cov2_resp"]


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
    assert sample["pathogen_overrides"]["remove"] == ["norwalk_gi"]
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
