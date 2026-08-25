"""The lineage census artifact: written from a real run, and carrying its clock.

The truth channel for every phylodynamic observable, so what matters here is
that a real run emits it, that an unarmed run still emits nothing, and that the
clock arm travels with the data rather than being assumed downstream.
"""

from __future__ import annotations

import copy
import json
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from picard_framework.analysis.phylodynamics import census_from_dict, load_census

REPO_ROOT = Path(__file__).resolve().parents[1]
SMOKE_SPEC = REPO_ROOT / "picard_framework" / "runs" / "smoke_2epoch.json"


def _raw_spec(
    *,
    census_path: Path | None,
    epoch_duration_hours: int = 1,
    clock: str = "hours",
    num_epochs: int = 4,
    seed: int = 11,
) -> dict[str, Any]:
    raw = copy.deepcopy(json.loads(SMOKE_SPEC.read_text(encoding="utf-8")))
    raw["run"]["num_epochs"] = num_epochs
    raw["run"]["random_seed"] = seed
    if census_path is not None:
        raw["run"]["lineage_census"] = str(census_path)
    overrides = raw.setdefault("config_overrides", {})
    overrides["variant_surveillance"] = {"enabled": True}
    overrides["natural_history_clock"] = clock
    overrides["epoch_duration_hours"] = epoch_duration_hours
    return raw


@pytest.fixture
def run_root() -> Iterator[Path]:
    """A repo-root-relative scratch directory (telemetry writers are confined)."""
    root = REPO_ROOT / "telemetry_buffer" / "_tmp_pr13_census"
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _run(tmp_path: Path, raw: dict[str, Any]) -> None:
    from picard_framework import PicardRunSpec, ShipSimulation

    spec_path = tmp_path / "run_spec.json"
    spec_path.write_text(json.dumps(raw), encoding="utf-8")
    spec = PicardRunSpec.from_picard_json(str(REPO_ROOT), str(spec_path))
    sim = ShipSimulation(spec, display=False)
    sim.run(n_epochs=int(raw["run"]["num_epochs"]))


@pytest.fixture
def census_dir(tmp_path: Path, run_root: Path) -> Path:
    """A run directory holding one real run's lineage census."""
    out = run_root / "run"
    out.mkdir()
    _run(tmp_path, _raw_spec(census_path=out / "lineage_census.json"))
    return out


def test_armed_run_writes_a_parseable_census(census_dir: Path) -> None:
    """A real variant-surveillance run emits a census the analysis can read."""
    census = load_census(str(census_dir))
    assert census.epochs, "an armed run must record at least one census epoch"


def test_census_names_the_pathogens_it_tracked(census_dir: Path) -> None:
    """Census rows are keyed by tracked pathogen, not by an anonymous index."""
    census = load_census(str(census_dir))
    assert all(row.pathogen_id for row in census.epochs)


def test_census_carries_the_clock_arm_not_an_assumption(census_dir: Path) -> None:
    """Downstream must not have to guess the clock: the artifact declares it."""
    census = load_census(str(census_dir))
    assert census.natural_history_clock == "hours"


def test_census_carries_the_epoch_duration(census_dir: Path) -> None:
    """One epoch is one hour on this arm, and the artifact says so."""
    census = load_census(str(census_dir))
    assert census.epoch_duration_hours == pytest.approx(1.0)


def test_census_founders_are_recorded(census_dir: Path) -> None:
    """The founder set is what a diversity trajectory starts from."""
    census = load_census(str(census_dir))
    assert census.founders, "seeded infections should register founder lineages"


def test_unarmed_run_writes_no_census(tmp_path: Path, run_root: Path) -> None:
    """Off by default: a run that did not ask for the census pays nothing."""
    out = run_root / "unarmed"
    out.mkdir()
    _run(tmp_path, _raw_spec(census_path=None))
    assert not (out / "lineage_census.json").exists()


def test_legacy_clock_arm_is_labelled_differently(
    tmp_path: Path,
    run_root: Path,
) -> None:
    """The legacy-epoch-day control must be distinguishable from the hourly arm."""
    out = run_root / "legacy"
    out.mkdir()
    _run(
        tmp_path,
        _raw_spec(
            census_path=out / "lineage_census.json",
            clock="legacy_epoch_day",
        ),
    )
    census = load_census(str(out))
    assert census.natural_history_clock == "legacy_epoch_day"


def test_epoch_duration_reaches_the_reporting_axis(
    tmp_path: Path,
    run_root: Path,
) -> None:
    """A six-hour epoch reports six voyage hours per epoch, not one."""
    out = run_root / "sixhour"
    out.mkdir()
    _run(
        tmp_path,
        _raw_spec(
            census_path=out / "lineage_census.json",
            epoch_duration_hours=6,
        ),
    )
    census = load_census(str(out))
    assert census.hours(3) == pytest.approx(18.0)


def test_census_totals_agree_with_their_lineage_counts(census_dir: Path) -> None:
    """Conservation, enforced at parse time: carriers are the sum of lineages."""
    census = load_census(str(census_dir))
    for row in census.epochs:
        assert row.total_carriers == sum(row.lineage_counts.values())


def test_parse_rejects_a_census_whose_total_disagrees() -> None:
    """A census that does not conserve carriers is corruption, not data."""
    payload = {
        "epoch_duration_hours": 1.0,
        "snapshots": [
            {
                "epoch": 0,
                "pathogen_id": "norwalk_gi",
                "lineage_counts": {"norwalk_gi:0": 2},
                "total_carriers": 5,
            },
        ],
    }
    with pytest.raises(ValueError, match="disagrees"):
        census_from_dict(payload)


def test_campaign_runner_arms_the_census_for_variant_runs() -> None:
    """A Paper 3 campaign run collects truth without being told run by run."""
    from picard_framework.runs.mega_cruise_campaign.campaign_runner import (
        _arm_lineage_census,
    )

    spec: dict[str, Any] = {
        "run": {},
        "config_overrides": {"variant_surveillance": {"enabled": True}},
    }
    _arm_lineage_census(spec, "/tmp/run7")
    assert spec["run"]["lineage_census"].endswith("lineage_census.json")


def test_campaign_runner_arms_observations_for_variant_runs() -> None:
    """Truth without observations scores nothing: a variant run needs both."""
    from picard_framework.runs.mega_cruise_campaign.campaign_runner import (
        _arm_sentinel_line_list,
    )

    spec: dict[str, Any] = {
        "run": {},
        "config_overrides": {"variant_surveillance": {"enabled": True}},
    }
    _arm_sentinel_line_list(spec, "/tmp/run9")
    assert spec["run"]["sentinel_line_list"].endswith("sentinel_line_list.json")


def test_campaign_runner_still_arms_observations_for_shore_runs() -> None:
    """The importation fit's reason for the ledger is unchanged."""
    from picard_framework.runs.mega_cruise_campaign.campaign_runner import (
        _arm_sentinel_line_list,
    )

    spec: dict[str, Any] = {
        "run": {},
        "config_overrides": {"voyage": {"shore_exposure": {"enabled": True}}},
    }
    _arm_sentinel_line_list(spec, "/tmp/run10")
    assert spec["run"]["sentinel_line_list"].endswith("sentinel_line_list.json")


def test_campaign_runner_leaves_unobserved_runs_alone() -> None:
    """Neither channel asked for: no ledger, and no compact-mode cost."""
    from picard_framework.runs.mega_cruise_campaign.campaign_runner import (
        _arm_sentinel_line_list,
    )

    spec: dict[str, Any] = {"run": {}, "config_overrides": {}}
    _arm_sentinel_line_list(spec, "/tmp/run11")
    assert "sentinel_line_list" not in spec["run"]


def test_campaign_runner_leaves_untracked_runs_alone() -> None:
    """No strain tracking, no census: the artifact would be empty anyway."""
    from picard_framework.runs.mega_cruise_campaign.campaign_runner import (
        _arm_lineage_census,
    )

    spec: dict[str, Any] = {"run": {}, "config_overrides": {}}
    _arm_lineage_census(spec, "/tmp/run8")
    assert "lineage_census" not in spec["run"]
