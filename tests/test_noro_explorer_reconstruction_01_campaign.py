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
            "rhythm_catalog": tier["platform"] == "mega_cruise_5000",
            **tier["expected_state"],
        },
        "frozen_block_witness": {"pinned_leaves": 1, "mismatches": []},
        "declared_arm": {
            "arm": tier.get("arm", "reference"), "mismatches": [],
        },
        "introduction": {
            "declared_seed_roles": ["passenger"] * n_seeds,
            "preboarding_reportable": {"passenger": 0, "crew": 0},
            "complement": complement,
        },
        "onsets_by_day": {
            "all": onsets,
            "excluding_declared_seeds": onsets,
            "incident": onsets,
        },
        "reporting_by_day": {
            "cumulative_end_of_day": cumulative,
            "epoch_zero_cumulative": {"passenger": 0, "crew": 0},
        },
        "protocols": {"first_active_epoch": {}},
    }


def _declared_seeds(manifest: dict, tier_id: str, n: int = 2) -> list[int]:
    return manifest["tiers"][tier_id]["seeds"][:n]


def test_readout_recovers_the_target_from_itself(
    readout: types.ModuleType, manifest: dict, target: dict,
) -> None:
    payloads = [
        _synthetic_cell(manifest, tier_id, seed, target["onsets_by_day"])
        for tier_id in manifest["tiers"]
        for seed in _declared_seeds(manifest, tier_id)
    ]
    result = readout.build_readout(payloads, manifest, target)
    assert result["defects"] == []
    assert result["status"] == "partial"
    assert all(
        cov["read"] == 2 and len(cov["missing"]) == 98
        for cov in result["coverage"].values()
    )
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
    seed = _declared_seeds(manifest, tier_id, 1)[0]
    small = _synthetic_cell(
        manifest, tier_id, seed,
        {"passenger": [1, 2, 0, 0, 0, 0, 0, 0], "crew": [0] * 8},
    )
    metrics = readout.cell_metrics(small)
    assert metrics["evaluable"] is False and metrics["lag_days"] is None
    shifted = _synthetic_cell(
        manifest, tier_id, seed,
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
    good = _synthetic_cell(
        manifest, tier_id, _declared_seeds(manifest, tier_id, 1)[0],
        target["onsets_by_day"],
    )
    assert readout.audit_cell(good, manifest, "abc") == []
    bad = copy.deepcopy(good)
    bad["frozen_block_witness"]["mismatches"] = [{"key": "x"}]
    bad["introduction"]["declared_seed_roles"] = ["passenger"]
    bad["introduction"]["complement"] = {"passenger": 3102, "crew": 1326}
    bad["num_epochs"] = 24
    bad["effective_state"]["exposure_cap_active"] = False
    problems = readout.audit_cell(bad, manifest, "zzz")
    assert len(problems) == 7
    stray = copy.deepcopy(good)
    stray["seed"] = 999999
    assert readout.audit_cell(stray, manifest, None) == [
        "seed 999999 is not in the tier's declared seeds",
    ]
    ghost = copy.deepcopy(good)
    ghost["tier"] = "fl_ghost"
    assert readout.audit_cell(ghost, manifest, None) == [
        "tier fl_ghost is not in the manifest",
    ]


def test_rhythm_off_arm_is_declared_on_both_hulls_with_paired_seeds(
    build: types.ModuleType, manifest: dict,
) -> None:
    arm = manifest["arm_blocks"]["rhythm_off"]
    assert arm["changed_paths"] == [
        {"path": "rhythm.enabled", "baseline": True, "arm": False},
    ]
    shipped = build.shipped_rhythm()
    assert arm["baseline_objects"]["rhythm"] == shipped
    assert arm["effective_objects"]["rhythm"] == {**shipped, "enabled": False}
    named_sources = [REPO_ROOT / arm["contract"]] + sorted(
        (REPO_ROOT / "docs" / "norovirus").glob(
            "paper1_freeze_declaration*.md"
        )
    )
    assert any(
        arm["named_commit"]["sha"] in p.read_text("utf-8")
        for p in named_sources
    )
    platforms = set()
    for arm_tier, reference_tier in arm["paired_with"].items():
        tier, reference = manifest["tiers"][arm_tier], manifest["tiers"][reference_tier]
        assert tier["arm"] == "rhythm_off" and "arm" not in reference
        assert tier["paired_with"] == reference_tier
        differing = {k for k in tier if tier[k] != reference.get(k)}
        assert differing == {
            "description", "arm", "paired_with", "expected_state",
        }
        assert tier["expected_state"]["rhythm_requested"] is False
        assert tier["seeds"] == reference["seeds"]
        platforms.add(tier["platform"])
    assert platforms == set(arm["hulls"]) and len(platforms) == 2
    armed = {t for t, tier in manifest["tiers"].items() if "arm" in tier}
    assert armed == set(arm["paired_with"])


def test_paired_cells_generate_the_same_run_apart_from_the_arm(
    cell: types.ModuleType, manifest: dict,
) -> None:
    arm = manifest["arm_blocks"]["rhythm_off"]
    for arm_tier, reference_tier in arm["paired_with"].items():
        sides = []
        for tier_id in (reference_tier, arm_tier):
            runs = [
                spec for _, spec in cell.generate_tier_runs(
                    manifest, tier_id, natural_history_clock="hours",
                )
            ]
            for spec in runs:
                cell.compose_introduction(spec, manifest, tier_id)
                cell.compose_complement(spec, manifest, tier_id)
                cell.compose_arm(spec, manifest, tier_id)
            sides.append(runs)
        reference_runs, arm_runs = sides
        assert len(reference_runs) == len(arm_runs) == len(
            manifest["tiers"][arm_tier]["seeds"],
        )
        for reference, armed in zip(reference_runs, arm_runs):
            assert "rhythm" not in reference["config_overrides"]
            rhythm = armed["config_overrides"].pop("rhythm")
            assert rhythm == arm["effective_objects"]["rhythm"]
            assert armed["campaign_parameters"].pop("tier_id") == arm_tier
            assert (
                reference["campaign_parameters"].pop("tier_id")
                == reference_tier
            )
            assert armed == reference


def test_arm_witness_requires_each_side_to_resolve_its_declared_value(
    cell: types.ModuleType, manifest: dict,
) -> None:
    arm = manifest["arm_blocks"]["rhythm_off"]
    off = {"rhythm": copy.deepcopy(arm["effective_objects"]["rhythm"])}
    on = {"rhythm": copy.deepcopy(arm["baseline_objects"]["rhythm"])}
    detached, attached = (
        {"rhythm_layer_active": False}, {"rhythm_layer_active": True},
    )
    good = cell.arm_witness(manifest, "rhythm_off", off, detached)
    assert good["mismatches"] == []
    assert good["resolved_objects"] == off
    assert good["changed_paths"][0]["resolved"] is False
    assert cell.arm_witness(manifest, "reference", on, attached)["mismatches"] == []
    # Explorer's reference cell: layer requested, not attached (section 2.8).
    assert cell.arm_witness(manifest, "reference", on, detached)["mismatches"] == []
    assert cell.arm_witness(manifest, "rhythm_off", on, detached)["mismatches"]
    assert cell.arm_witness(manifest, "rhythm_off", off, attached)["mismatches"]
    assert cell.arm_witness(manifest, "reference", off, detached)["mismatches"]
    drifted = copy.deepcopy(off)
    drifted["rhythm"]["post_prandial_window_minutes"] = 60
    assert cell.arm_witness(manifest, "rhythm_off", drifted, detached)["mismatches"]


def test_readout_measures_what_the_arm_removed(
    readout: types.ModuleType, manifest: dict, target: dict,
) -> None:
    arm = manifest["arm_blocks"]["rhythm_off"]
    base = target["onsets_by_day"]
    payloads = []
    for tier_id, tier in manifest["tiers"].items():
        for seed in _declared_seeds(manifest, tier_id):
            onsets = copy.deepcopy(base)
            if "arm" in tier:
                onsets["passenger"][2] -= (
                    10 * (seed - tier["seeds"][0] + 1)
                )
            payloads.append(_synthetic_cell(manifest, tier_id, seed, onsets))
    result = readout.build_readout(payloads, manifest, target)
    assert result["defects"] == []
    block = result["arms"]["rhythm_off"]
    assert set(block["reference_minus_arm"]) == set(arm["paired_with"])
    for row in block["reference_minus_arm"].values():
        assert row["pairs"] == 2 and row["pairs_identical_curves"] == 0
        daily = row["mean_daily_onset_diff"]
        assert daily["passenger"][2] == 15.0
        assert sum(daily["passenger"]) == 15.0 and not any(daily["crew"])
        assert row["mean_cumulative_reported_diff"]["passenger"][-1] == 15.0
        assert row["passenger"]["onset_attack_rate"]["median"] > 0
        assert row["crew"]["onset_attack_rate"]["median"] == 0
    assert set(block["explorer_minus_mega"]) == {"declared_five"}
    assert set(result["explorer_minus_mega"]) == set(
        manifest["introduction_blocks"],
    )
    assert "rhythm_off" in readout.build_markdown(result)
    wrong = copy.deepcopy(payloads[-1])
    wrong["declared_arm"]["arm"] = "reference"
    assert readout.audit_cell(wrong, manifest, None)
    del wrong["declared_arm"]
    assert readout.audit_cell(wrong, manifest, None)


def test_expected_state_distinguishes_the_hulls_and_arms(
    cell: types.ModuleType, manifest: dict,
) -> None:
    # The reference check Edison flagged: an absent layer passes
    # arm_witness on a mega reference cell; the tier's declared
    # expected_state is what rejects it.
    meg = "fl_meg_8d_recon_declared_five"
    exp = "fl_exp_8d_recon_declared_five"
    arm = "fl_meg_8d_recon_declared_five_rhythm_off"
    on = {
        "exposure_cap_requested": True, "exposure_cap_active": True,
        "rhythm_requested": True, "rhythm_layer_active": True,
    }
    detached = {**on, "rhythm_layer_active": False}
    off = {**detached, "rhythm_requested": False}
    assert cell.check_expected_state(manifest, meg, on) == []
    assert cell.check_expected_state(manifest, meg, detached)
    assert cell.check_expected_state(manifest, exp, detached) == []
    assert cell.check_expected_state(manifest, exp, on)
    assert cell.check_expected_state(manifest, arm, off) == []
    assert cell.check_expected_state(manifest, arm, detached)
    cap_missing = {**detached, "exposure_cap_active": False}
    assert cell.check_expected_state(manifest, exp, cap_missing)


def test_readout_enforces_coverage_before_a_complete_verdict(
    readout: types.ModuleType, manifest: dict, target: dict,
) -> None:
    tier_id = "fl_exp_8d_recon_declared_five"
    seed = _declared_seeds(manifest, tier_id, 1)[0]
    one = _synthetic_cell(manifest, tier_id, seed, target["onsets_by_day"])
    partial = readout.build_readout([one], manifest, target)
    assert partial["status"] == "partial"
    assert partial["defects"] == []
    assert partial["coverage"][tier_id]["missing"]
    # A duplicate archive is dropped before pairing and recorded.
    dup = readout.build_readout(
        [one, copy.deepcopy(one)], manifest, target,
    )
    assert partial["coverage"][tier_id]["read"] == 1
    assert any(
        "duplicate" in problem
        for defect in dup["defects"] for problem in defect["problems"]
    )
    assert dup["coverage"][tier_id]["read"] == 1
    # An unexpected seed is excluded and recorded, not paired.
    stray = copy.deepcopy(one)
    stray["seed"] = 999999
    out = readout.build_readout([stray], manifest, target)
    assert out["coverage"][tier_id]["unexpected"] == [999999]
    assert out["coverage"][tier_id]["read"] == 0
    assert out["defects"]
    # A cell for a tier outside the manifest is a defect, not a crash.
    ghost = copy.deepcopy(one)
    ghost["tier"] = "fl_ghost"
    out = readout.build_readout([ghost], manifest, target)
    assert out["defects"] and out["cells"] == 1
    # Empty input is a partial readout, not a clean verdict.
    empty = readout.build_readout([], manifest, target)
    assert empty["status"] == "partial" and empty["cells"] == 0
