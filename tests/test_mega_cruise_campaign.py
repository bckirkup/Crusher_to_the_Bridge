"""Tests for mega_cruise_campaign runner (generation + smoke)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from picard_framework.runs.mega_cruise_campaign.campaign_runner import (  # noqa: E402
    generate_tier_runs,
    load_manifest,
    main,
    make_picard_spec,
    resolve_tier_ids,
)

CAMPAIGN = REPO_ROOT / "picard_framework" / "runs" / "mega_cruise_campaign"


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
        "t2_hvac_sweep": 2000,
        "t3_surveillance_sweep": 1200,
        "t4_full_factorial": 2880,
        "t5_multi_pathogen": 400,
        "t6_dose_response": 600,
        "t7_compliance": 800,
        "t8_wearables": 480,
        "t9_slow_pathogens": 320,
        "t10_population_size": 100,
    }
    total = 0
    for tier_id, n_exp in expected.items():
        runs = list(generate_tier_runs(manifest, tier_id))
        assert len(runs) == n_exp, f"{tier_id}: {len(runs)} != {n_exp}"
        total += len(runs)
    assert total == 9080


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
    sample = next(s for rid, s in runs if "init5" in rid and "norovirus" in rid)
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


@pytest.mark.timeout(120)
def test_smoke_cli_one_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end: --smoke executes one destroyer run and writes a zip."""
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
