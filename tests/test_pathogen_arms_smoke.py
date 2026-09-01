"""Fast smoke coverage for the campaign's isolated pathogen arms."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from picard_framework.runs.mega_cruise_campaign import campaign_runner


@pytest.mark.parametrize(
    ("arm", "expected_id", "removed_id"),
    [
        ("norovirus", "norwalk_gi", "sars_cov2_resp"),
        ("sarscov2", "sars_cov2_resp", "norwalk_gi"),
    ],
)
def test_pathogen_arm_writes_resolved_profile_artifacts(
    arm: str,
    expected_id: str,
    removed_id: str,
    tmp_path: Path,
) -> None:
    manifest = campaign_runner.load_manifest()
    runs = campaign_runner.generate_tier_runs(
        manifest, "t1_pathogen_baselines",
    )
    run_id, original_spec = next(
        (rid, spec)
        for rid, spec in runs
        if rid == f"t1_{arm}_s42"
    )
    spec = copy.deepcopy(original_spec)
    spec["catalog"]["platform_id"] = "expedition_cruise_450"
    spec["run"]["num_epochs"] = 24
    spec["config_overrides"]["ship_graph"] = {"num_agents": 30}

    assert campaign_runner.run_simulation(
        run_id,
        spec,
        full_telemetry=False,
        keep_workdir=True,
        output_root=tmp_path,
    ) is True

    run_dir = Path(
        campaign_runner._run_workdir(run_id, output_root=str(tmp_path)),
    )
    resolved_path = run_dir / "resolved_pathogen_profiles.json"
    summary_path = run_dir / "summary.json"
    timeseries_path = run_dir / "timeseries.json"
    assert resolved_path.exists()
    assert summary_path.exists()
    assert timeseries_path.exists()

    resolved = json.loads(resolved_path.read_text(encoding="utf-8"))
    assert resolved["pathogen_ids"] == [expected_id]
    assert list(resolved["profiles"]) == [expected_id]

    summary_text = summary_path.read_text(encoding="utf-8")
    timeseries_text = timeseries_path.read_text(encoding="utf-8")
    summary = json.loads(summary_text)
    assert summary["pathogen_ids"] == [expected_id]
    for key in (
        "cumulative_ever_infected_passenger",
        "cumulative_ever_infected_crew",
        "cumulative_reported_cases_passenger",
        "cumulative_reported_cases_crew",
        "passenger_complement",
        "crew_complement",
    ):
        assert key in summary["summary"]
    assert removed_id not in summary_text
    assert removed_id not in timeseries_text
