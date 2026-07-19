"""Tests for mega_cruise_campaign runner (generation + smoke)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from picard_framework.runs.mega_cruise_campaign.campaign_runner import (  # noqa: E402
    compute_derived_metrics,
    extract_timeseries,
    generate_tier_runs,
    load_manifest,
    main,
    make_picard_spec,
    resolve_tier_ids,
)

CAMPAIGN = REPO_ROOT / "picard_framework" / "runs" / "mega_cruise_campaign"

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


def test_manifest_loads_and_has_ten_tiers() -> None:
    manifest = load_manifest(CAMPAIGN / "campaign_manifest.json")
    assert manifest["campaign"] == "mega_cruise_9k"
    assert len(manifest["tiers"]) == 10
    assert "norovirus" in manifest["pathogen_configs"]
    assert manifest["pathogen_configs"]["norovirus"]["pathogen_id"] == "norwalk_gi"


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


def test_make_picard_spec_optional_telemetry_paths() -> None:
    spec = make_picard_spec(
        "x",
        platform="destroyer_baseline",
        bundle="active_profiles",
        pathogen_overrides={"remove": ["sars_cov2_resp"]},
        config_overrides=None,
        seed=42,
        epochs=2,
        num_agents=20,
        telemetry_dir=Path("/tmp/ctb_run"),
    )
    assert spec["run"]["simulation_history"].endswith("simulation_history.json")


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
    assert extract_timeseries([]) == []


def test_compute_derived_metrics() -> None:
    ts = extract_timeseries(_sample_history())
    derived = compute_derived_metrics(ts, num_agents=1000)
    assert derived["peak_prevalence"] == 3
    assert derived["peak_epoch"] == 1
    assert derived["outbreak_occurred"] is True
    assert derived["detection_epoch"] == 1
    assert derived["confirmation_epoch"] == 2
    assert derived["attack_rate"] == pytest.approx(0.004)
    assert derived["total_quarantine_person_epochs"] == 3
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
