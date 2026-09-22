"""Aggregation-only readout for the NORO-FOMITE-DISAGG-01 identity block.

Synthetic cells, no engine run: the readout must call an exact copy an
identity, flag one seed's one statistic outside tolerance as a DEFECT,
compare host doses host by host, and place the runtime ratio against the
frozen envelope.
"""

from __future__ import annotations

import copy
import gzip
import json
from pathlib import Path

import pytest

from tools.noro_diag import fomite_disagg_identity_readout as ro

TOL = ro.RELATIVE_TOLERANCE


def _cell(seed: int, wall: float, arm: str) -> dict:
    return {
        "seed": seed,
        "epochs": 4,
        "platform": "classic_cruise_1900",
        "num_agents": 1910,
        "arm_tag": arm,
        "fomite_representation": arm,
        "fomite_representation_resolved": arm,
        "reconciliation": {
            "sum_credited_raw_gec": 1234.5 + seed,
            "sum_credited_scaled_gec": 1000.0 + seed,
            "sum_dose_read_at_challenge_gec": 900.0,
            "sum_effective_dose_evaluated_gec": 800.0,
            "sum_evaluated_hazard": 0.25,
        },
        "fomite_witness": {
            "surface_deposit_calls": 40,
            "surface_mass_deposited_gec": 5.0e6,
            "deliver_calls": 11,
            "mass_delivered_to_hands_gec": 933.0,
            "hand_to_mouth_calls": 30,
            "hand_load_seen_gec": 500.0,
            "hand_to_mouth_dose_gec": 20.0,
        },
        "joint": {"hosts_credited_any_dose": 3},
        "transmission": {"secondaries": 2, "imports": 5, "attack_rate": 0.1},
        "hosts": [
            {"agent_id": 1, "credited_scaled_gec": 600.0},
            {"agent_id": 2, "credited_scaled_gec": 300.0 + seed},
            {"agent_id": 3, "credited_scaled_gec": 100.0},
        ],
        "wall_clock_seconds_run": wall,
    }


def _write(directory: Path, tag: str, cells: list[dict]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for cell in cells:
        path = directory / f"per_host_dose_challenge_{tag}_seed{cell['seed']}.json.gz"
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            json.dump(cell, handle)


@pytest.fixture
def arms(tmp_path: Path) -> tuple[Path, list[dict], list[dict]]:
    base = [_cell(s, 10.0, "pooled") for s in (8000, 8001, 8002)]
    arm = [copy.deepcopy(c) for c in base]
    for cell in arm:
        cell["arm_tag"] = cell["fomite_representation"] = "per_surface_areal"
        cell["fomite_representation_resolved"] = "per_surface"
        cell["wall_clock_seconds_run"] = 25.0
    return tmp_path, base, arm


def test_exact_copy_is_an_identity_with_runtime_inside_envelope(arms):
    tmp, base, arm = arms
    _write(tmp / "base", "pooled", base)
    _write(tmp / "arm", "per_surface_areal", arm)
    result = ro.readout(tmp / "arm", "per_surface_areal", tmp / "base", "pooled")
    assert result["identity_verdict"] == "holds"
    assert result["seeds"] == [8000, 8001, 8002]
    assert all(c["verdict"] == "identity" for c in result["comparisons"])
    assert result["runtime"]["median_ratio"] == pytest.approx(2.5)
    assert result["runtime"]["verdict"] == "inside envelope"


@pytest.mark.parametrize(
    "bump, expect_defect",
    [(TOL / 10, False), (TOL * 10, True), (1e-3, True)],
)
def test_float_deviation_is_graded_against_the_frozen_tolerance(
    arms, bump, expect_defect,
):
    tmp, base, arm = arms
    arm[1]["reconciliation"]["sum_credited_raw_gec"] *= 1.0 + bump
    _write(tmp / "base", "pooled", base)
    _write(tmp / "arm", "per_surface_areal", arm)
    result = ro.readout(tmp / "arm", "per_surface_areal", tmp / "base", "pooled")
    row = next(
        c for c in result["comparisons"]
        if c["statistic"] == "reconciliation.sum_credited_raw_gec"
    )
    assert row["max_deviation_seed"] == 8001
    assert row["max_relative_deviation"] == pytest.approx(
        bump / (1.0 + bump), rel=1e-6,
    )
    assert (row["verdict"] == "DEFECT") is expect_defect
    assert (result["identity_verdict"] == "DEFECT") is expect_defect
    others = [
        c for c in result["comparisons"]
        if c["statistic"] != "reconciliation.sum_credited_raw_gec"
    ]
    assert all(c["verdict"] == "identity" for c in others)


def test_exact_count_off_by_one_is_a_defect_and_host_vector_is_checked(arms):
    tmp, base, arm = arms
    arm[0]["fomite_witness"]["deliver_calls"] += 1
    arm[2]["hosts"][1]["credited_scaled_gec"] += 1.0
    _write(tmp / "base", "pooled", base)
    _write(tmp / "arm", "per_surface_areal", arm)
    result = ro.readout(tmp / "arm", "per_surface_areal", tmp / "base", "pooled")
    assert set(result["statistics_outside_tolerance"]) == {
        "fomite_witness.deliver_calls", "hosts[].credited_scaled_gec",
    }
    hosts = result["comparisons"][-1]
    assert hosts["seeds_outside_tolerance"] == [8002]
    assert hosts["max_deviation_seed"] == 8002


def test_runtime_above_envelope_and_unshared_seeds_are_reported(arms):
    tmp, base, arm = arms
    for cell in arm:
        cell["wall_clock_seconds_run"] = 50.0
    arm.append(_cell(8003, 50.0, "per_surface_areal"))
    _write(tmp / "base", "pooled", base)
    _write(tmp / "arm", "per_surface_areal", arm)
    result = ro.readout(tmp / "arm", "per_surface_areal", tmp / "base", "pooled")
    assert result["seeds_only_in_arm"] == [8003]
    assert result["runtime"]["median_ratio"] == pytest.approx(5.0)
    assert result["runtime"]["verdict"] == "above envelope"
    assert result["identity_verdict"] == "holds"


def test_main_writes_the_json_and_exit_code_tracks_the_verdict(arms, monkeypatch):
    tmp, base, arm = arms
    _write(tmp / "base", "pooled", base)
    _write(tmp / "arm", "per_surface_areal", arm)
    out = ro.REPO_ROOT / "docs" / "norovirus" / "noro_fomite_disagg_01" / "_pytest_tmp"
    monkeypatch.setattr(
        ro, "prepare_output_directory", lambda path, allowed_roots: Path(path),
    )
    out.mkdir(parents=True, exist_ok=True)
    try:
        rc = ro.main([
            "--arm-dir", str(tmp / "arm"), "--base-dir", str(tmp / "base"),
            "--out", str(out),
        ])
        written = out / "fomite_disagg_identity_per_surface_areal.json"
        assert rc == 0
        assert json.loads(written.read_text())["identity_verdict"] == "holds"
    finally:
        for path in out.glob("*"):
            path.unlink()
        out.rmdir()


def test_no_shared_seeds_is_refused(tmp_path):
    _write(tmp_path / "base", "pooled", [_cell(1, 1.0, "pooled")])
    _write(tmp_path / "arm", "x", [_cell(2, 1.0, "x")])
    with pytest.raises(SystemExit):
        ro.readout(tmp_path / "arm", "x", tmp_path / "base", "pooled")
