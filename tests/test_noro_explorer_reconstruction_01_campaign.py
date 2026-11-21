"""Contract tests for campaigns/noro/explorer_reconstruction_01/.

Structural only, no voyage is stepped: the committed generated files equal
a rebuild from their sources, every tier carries the Paper-1 frozen block
verbatim, the blocks cover the design grid once, the worker composes the
declared introduction and complement without touching the frozen block,
and the readout's curve metrics recover the empirical target from itself.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN_DIR = REPO_ROOT / "campaigns" / "noro" / "explorer_reconstruction_01"


def _load(name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def build() -> types.ModuleType:
    return _load("explorer_recon_build", CAMPAIGN_DIR / "design" / "build.py")


@pytest.fixture(scope="module")
def cell() -> types.ModuleType:
    return _load("explorer_recon_cell", CAMPAIGN_DIR / "cell.py")


@pytest.fixture(scope="module")
def readout() -> types.ModuleType:
    return _load("explorer_recon_readout", CAMPAIGN_DIR / "readout.py")


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads((CAMPAIGN_DIR / "manifest.json").read_text("utf-8"))


@pytest.fixture(scope="module")
def target() -> dict:
    return json.loads(
        (CAMPAIGN_DIR / "empirical_target.json").read_text("utf-8"),
    )


def test_committed_files_equal_a_rebuild(build: types.ModuleType) -> None:
    for name, content in build.outputs().items():
        assert (CAMPAIGN_DIR / name).read_text("utf-8") == content, name


def test_every_tier_carries_the_frozen_block_verbatim(
    build: types.ModuleType, manifest: dict,
) -> None:
    block = build.frozen_block()
    assert manifest["tiers"]
    for tier in manifest["tiers"].values():
        assert tier["config_overrides"] == block
        assert tier["epoch_durations"] == [build.EPOCHS]


def test_blocks_cover_the_grid_once(manifest: dict) -> None:
    campaign = json.loads((CAMPAIGN_DIR / "campaign.json").read_text("utf-8"))
    tiers = [block["tier"] for block in campaign["blocks"].values()]
    assert sorted(tiers) == sorted(manifest["tiers"])
    for block in campaign["blocks"].values():
        assert block["seeds"] == manifest["tiers"][block["tier"]]["seeds"]
        assert len(set(block["seeds"])) == len(block["seeds"])
    assert campaign["canary"]["block"] in campaign["blocks"]


def test_target_is_internally_consistent(target: dict) -> None:
    for role in ("passenger", "crew"):
        daily = target["onsets_by_day"][role]
        assert len(daily) == len(target["day_labels"])
        assert sum(daily) == target["investigation_finals"][role]["cases"]
        assert daily[target["peak_day_index"][role]] == max(daily)
    assert target["crew_minus_passenger_peak_lag_days"] == (
        target["peak_day_index"]["crew"]
        - target["peak_day_index"]["passenger"]
    )


def test_complement_blocks_declare_their_role_counts(
    build: types.ModuleType, manifest: dict,
) -> None:
    exact = manifest["complement_blocks"]["explorer_investigation"]
    by_role: dict[str, int] = {}
    for cls in exact["agent_classes"]:
        by_role[cls["role_group"]] = by_role.get(cls["role_group"], 0) + cls["count"]
    assert by_role == exact["intended"]
    assert sum(c["fraction"] for c in exact["agent_classes"]) == pytest.approx(1.0)
    shipped = manifest["complement_blocks"]["archetype_shipped"]
    assert shipped["agent_classes"] is None
    for tier in manifest["tiers"].values():
        block = manifest["complement_blocks"][tier["complement"]]
        assert sum(block["intended"].values()) == tier["num_agents"]
        assert sum(block["class_counts"].values()) == tier["num_agents"]


def test_worker_composes_beside_the_frozen_block(
    cell: types.ModuleType, manifest: dict,
) -> None:
    for tier_id, tier in manifest["tiers"].items():
        boarding = {"boarding": {"enabled": True}}
        spec = {
            "config_overrides": {
                **copy.deepcopy(tier["config_overrides"]),
                "initiation": copy.deepcopy(boarding),
                "ship_graph": {"num_agents": tier["num_agents"]},
            },
        }
        name = cell.compose_introduction(spec, manifest, tier_id)
        complement, intended = cell.compose_complement(spec, manifest, tier_id)
        overrides = spec["config_overrides"]
        declared = manifest["introduction_blocks"][name]["explicit_seeds"]
        block = manifest["complement_blocks"][complement]
        assert overrides["initiation"]["boarding"] == boarding["boarding"]
        assert overrides["initiation"].get("explicit_seeds", []) == declared
        assert intended == block["intended"]
        assert ("agent_classes" in overrides["ship_graph"]) == (
            block["agent_classes"] is not None
        )
        count, missing = cell.block_mismatches(
            tier["config_overrides"], overrides,
        )
        assert count > 0 and missing == []


def test_block_mismatches_reports_a_moved_leaf(cell: types.ModuleType) -> None:
    block = {"a": {"b": 1, "c": [1, 2]}, "d": "x"}
    moved = {"a": {"b": 2, "c": [1, 2]}}
    count, missing = cell.block_mismatches(block, moved)
    assert count == 3
    assert sorted(m["key"] for m in missing) == ["a.b", "d"]


def _synthetic_cell(
    manifest: dict, tier_id: str, seed: int, onsets: dict[str, list[int]],
) -> dict:
    tier = manifest["tiers"][tier_id]
    declared = manifest["introduction_blocks"][tier["introduction"]]
    n_seeds = sum(s["count"] for s in declared["explicit_seeds"])
    complement = dict(
        manifest["complement_blocks"][tier["complement"]]["intended"],
    )
    cumulative = {
        role: [sum(values[: day + 1]) for day in range(len(values))]
        for role, values in onsets.items()
    }
    return {
        "tier": tier_id,
        "seed": seed,
        "num_epochs": tier["epoch_durations"][0],
        "engine_git_sha": "abc123",
        "platform": tier["platform"],
        "intended_complement": dict(complement),
        "effective_state": {
            "rhythm_catalog": True,
            "exposure_cap_requested": True,
            "exposure_cap_active": True,
            "rhythm_requested": True,
            "rhythm_layer_active": True,
        },
        "frozen_block_witness": {"pinned_leaves": 1, "mismatches": []},
        "introduction": {
            "declared_seed_roles": ["passenger"] * n_seeds,
            "preboarding_reportable": {"passenger": 0, "crew": 0},
            "complement": complement,
        },
        "onsets_by_day": {"all": onsets, "excluding_declared_seeds": onsets},
        "reporting_by_day": {
            "cumulative_end_of_day": cumulative,
            "epoch_zero_cumulative": {"passenger": 0, "crew": 0},
        },
        "protocols": {"first_active_epoch": {}},
    }


def test_readout_recovers_the_target_from_itself(
    readout: types.ModuleType, manifest: dict, target: dict,
) -> None:
    payloads = [
        _synthetic_cell(manifest, tier_id, seed, target["onsets_by_day"])
        for tier_id in manifest["tiers"]
        for seed in (1, 2)
    ]
    result = readout.build_readout(payloads, manifest, target)
    assert result["defects"] == []
    for tier_id, tier in manifest["tiers"].items():
        block = result["tiers"][tier_id]
        assert block["evaluable"] == block["cells"] == 2
        assert block["lag_days"]["p_equal_target"] == 1.0
        assert block["lag_days"]["target_in_central_90"] is True
        for role in ("passenger", "crew"):
            assert block[role]["peak_day"]["p_equal_target"] == 1.0
            assert block[role]["curve_total_variation"]["median"] == 0.0
            assert block[role]["peak_day"]["p_within_one_day"] == 1.0
            if tier["platform"] == manifest["platform"]:
                assert block[role]["onset_total"]["target_in_central_90"] is True
    assert "Empirical" in readout.build_markdown(result)


def test_readout_grades_peaks_and_small_curves(
    readout: types.ModuleType, manifest: dict,
) -> None:
    assert readout.peak_day([0, 3, 3, 1]) == 1
    assert readout.peak_tied([0, 3, 3, 1]) is True
    assert readout.peak_day([0, 0]) is None
    tier_id = next(iter(manifest["tiers"]))
    small = _synthetic_cell(
        manifest, tier_id, 1,
        {"passenger": [1, 2, 0, 0, 0, 0, 0, 0], "crew": [0] * 8},
    )
    metrics = readout.cell_metrics(small)
    assert metrics["evaluable"] is False and metrics["lag_days"] is None
    shifted = _synthetic_cell(
        manifest, tier_id, 1,
        {"passenger": [0, 30, 10, 0, 0, 0, 0, 0],
         "crew": [0, 0, 0, 0, 0, 2, 6, 0]},
    )
    assert readout.cell_metrics(shifted)["lag_days"] == 5


def test_readout_audit_flags_design_violations(
    readout: types.ModuleType, manifest: dict, target: dict,
) -> None:
    tier_id = next(
        t for t, tier in manifest["tiers"].items()
        if tier["platform"] == manifest["platform"]
        and tier["introduction"] == "declared_five"
    )
    good = _synthetic_cell(manifest, tier_id, 1, target["onsets_by_day"])
    assert readout.audit_cell(good, manifest, "abc") == []
    bad = copy.deepcopy(good)
    bad["frozen_block_witness"]["mismatches"] = [{"key": "x"}]
    bad["introduction"]["declared_seed_roles"] = ["passenger"]
    bad["introduction"]["complement"] = {"passenger": 3102, "crew": 1326}
    bad["num_epochs"] = 24
    bad["effective_state"]["exposure_cap_active"] = False
    assert len(readout.audit_cell(bad, manifest, "zzz")) == 6
