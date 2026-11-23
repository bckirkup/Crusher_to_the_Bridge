"""DP-THETA-FIT-01: the declared matrix, the T3 mapping, and the selector."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CAMPAIGN = _REPO_ROOT / "campaigns/covid/dp_theta_fit_01"
_DESIGN = _REPO_ROOT / "picard_framework/runs/covid_dp_theta_fit_01_design.json"
_TARGET = {"cumulative_positives": 634, "through_day_index": 31}


def _load(name: str):
    spec = importlib.util.spec_from_file_location(
        f"dp_theta_fit_01_{name}", _CAMPAIGN / f"{name}.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _row(theta: float, positives: list[int], *, saturated: bool = False) -> dict:
    return {
        "theta": theta,
        "median_positives": sorted(positives)[len(positives) // 2],
        "side": "compatible",
        "dead": False,
        "saturated": saturated,
        "seeds_in_band": sum(1 for p in positives if 317 <= p <= 1268),
    }


def test_blocks_cover_the_declared_matrix_once():
    design = json.loads(_DESIGN.read_text(encoding="utf-8"))
    spec = json.loads((_CAMPAIGN / "campaign.json").read_text(encoding="utf-8"))
    cells = [
        (block["args"]["theta"], seed)
        for block in spec["blocks"].values() for seed in block["seeds"]
    ]
    expected = {
        (theta, design["seed_base"] + offset)
        for theta in design["thetas"] for offset in range(design["seeds"])
    }
    assert len(cells) == len(set(cells)) == 168
    assert set(cells) == expected
    assert all(
        block["args"]["arm_id"] == "replay_niid"
        and "num_epochs" not in block["args"]
        for block in spec["blocks"].values()
    )


def test_fit_arm_matches_the_frozen_pilot_arm():
    pilot = json.loads(
        (_REPO_ROOT / "picard_framework/runs/covid_dp_theta_pilot_01_design.json")
        .read_text(encoding="utf-8"),
    )
    design = json.loads(_DESIGN.read_text(encoding="utf-8"))
    arm = {a["arm_id"]: a["overrides"] for a in design["arms"]}
    pilot_arm = {a["arm_id"]: a["overrides"] for a in pilot["arms"]}
    assert arm["replay_niid"] == pilot_arm["replay_niid"]
    assert design["fit_target"]["cumulative_positives"] == 634


@pytest.mark.parametrize("cutoff, expected", [(31, 2), (33, 2), (34, 3), (15, 0)])
def test_t3_block_counts_positives_only_through_the_cutoff(cutoff, expected):
    cell = _load("cell")
    log = [
        {"day": 16, "positive": True},
        {"day": 16, "positive": False},
        {"day": 31, "positive": True},
        {"day": 34, "positive": True, "wave": "crew_wave"},
    ]
    block = cell.t3_block(log, cutoff)
    assert block["positives_through_day"] == expected
    assert block["positives_all"] == 3
    assert block["specimens_by_wave"] == {"crew_wave": 1}
    assert block["last_specimen_day"] == 34


def test_selector_brackets_and_interpolates_in_log_theta():
    readout = _load("readout")
    rows = [
        _row(1e8, [0] * 24),
        _row(1e9, [234] * 24),
        _row(1e10, [1034] * 24),
    ]
    selection = readout._selection(rows, _TARGET)
    assert selection["bracket"]["theta_lo"] == 1e9
    assert selection["bracket"]["theta_hi"] == 1e10
    assert selection["bracket"]["theta_star_interpolated"] == pytest.approx(10 ** 9.5)
    assert selection["monotone_medians"] is True


def test_selector_reports_no_bracket_and_skips_saturated_cells():
    readout = _load("readout")
    rows = [
        _row(1e9, [700] * 24),
        _row(1e10, [640] * 24, saturated=True),
    ]
    selection = readout._selection(rows, _TARGET)
    assert selection["bracket"] is None
    assert selection["selected_theta"] == 1e9
    assert selection["saturated_thetas"] == [1e10]


def test_selected_cell_is_flagged_when_no_seed_resembles_the_target():
    readout = _load("readout")
    bimodal = [0] * 11 + [640] + [1400] * 12
    selection = readout._selection([_row(1e9, bimodal)], _TARGET)
    assert selection["selected_theta"] == 1e9
    assert selection["selected_median_not_representative"] is True


def _cell(seed: int, infections: int, positives: int) -> dict:
    return {
        "infections_total": infections,
        "aboard_total": 3711,
        "attack_rate": infections / 3711,
        "lab_confirmed_total": positives,
        "infections_before_quarantine": infections,
        "observables": {"recorded_onsets": 0, "campaign_positives": positives},
        "dp_theta_fit": {"seed": seed, "t3": {
            "positives_through_day": positives,
            "specimens_through_day": 10,
            "last_specimen_day": 31,
            "specimens_by_wave": {},
            "by_day": {"16": {"specimens": 10, "positives": positives}},
        }},
    }


@pytest.mark.parametrize(
    "infections, extinct, saturated",
    [(0, 20, False), (3524, 0, False), (3525, 0, True)],
)
def test_secondaries_exclude_the_index_exactly_once(infections, extinct, saturated):
    readout = _load("readout")
    by_seed = {seed: _cell(seed, infections, 5) for seed in range(20)}
    row = readout._theta_row(1e9, by_seed, _TARGET, 24)
    assert row["reported_only"]["extinct_seeds"] == extinct
    assert row["reported_only"]["median_secondaries"] == infections
    assert row["saturated"] is saturated
    assert row["provisional"] is True
    assert row["reported_only"]["median_by_day"]["16"]["positives"] == 5
