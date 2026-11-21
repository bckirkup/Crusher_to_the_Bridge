"""Unit tests for the H5 rescore readout's decomposition math.

The readout projects committed cell payloads onto the scored surface
(verbatim contract loss + takeoff gate + H5 band residual), so its
correctness is the band-residual and bookkeeping math; these pin it on
synthetic cells.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location(
        "covid_h5_rescore",
        _ROOT / "tools" / "covid_h5_rescore.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_h5_band_residual_zero_inside_band(mod):
    assert mod._h5_band_residual(712.0) == 0.0
    assert mod._h5_band_residual(836.0) == 0.0
    assert mod._h5_band_residual(960.0) == 0.0


def test_h5_band_residual_log_distance_outside(mod):
    # Under the floor: log(lo / inf).
    assert mod._h5_band_residual(356.0) == pytest.approx(math.log(2.0))
    # Over the top: log(inf / hi).
    assert mod._h5_band_residual(1920.0) == pytest.approx(math.log(2.0))
    # Degenerate counts floor at 1 rather than exploding.
    assert mod._h5_band_residual(0.0) == pytest.approx(math.log(712.0))


def _obs(
    scenario_id: str,
    theta: float,
    seed: int,
    recorded_onsets: int,
    campaign_positives: int,
) -> dict:
    return {
        "scenario_id": scenario_id,
        "theta": theta,
        "seed": seed,
        "recorded_onsets": recorded_onsets,
        "onsets_before_split_day": 0,
        "onsets_on_or_after_split_day": recorded_onsets,
        "passenger_onsets_before": 0,
        "passenger_onsets_after": recorded_onsets // 2,
        "crew_onsets_before": 0,
        "crew_onsets_after": recorded_onsets - recorded_onsets // 2,
        "campaign_specimens": 100,
        "campaign_positives": campaign_positives,
        "campaign_asymptomatic_positives": campaign_positives // 2,
    }


def test_decompose_cell_projects_payload(mod):
    payload = {
        "arm_id": "boxed_s1s2",
        "design_id": "covid_crew_reach_01",
        "observables": _obs("diamond_princess_2020", 1e9, 7, 20, 600),
        "infections_total": 800,
        "lab_confirmed_total": 700,
    }
    cell = mod._decompose_cell(payload, mod._objective())
    assert cell["scenario_id"] == "diamond_princess_2020"
    assert cell["theta"] == 1e9
    assert cell["seed"] == 7
    assert cell["recorded_onsets"] == 20
    assert cell["campaign_positives"] == 600
    assert cell["infections_total"] == 800
    assert cell["lab_confirmed_total"] == 700
    assert cell["h5_band_residual"] == 0.0
    assert cell["verbatim_loss"] >= 0.0


def _cell(
    scenario_id: str = "diamond_princess_2020",
    theta: float = 1e9,
    seed: int = 1,
    recorded_onsets: int = 20,
    campaign_positives: int = 600,
    infections_total: int | None = 800,
    lab_confirmed_total: int | None = 700,
) -> dict:
    return {
        "scenario_id": scenario_id,
        "theta": theta,
        "seed": seed,
        "arm_id": "boxed_s1s2",
        "design_id": "covid_crew_reach_01",
        "recorded_onsets": recorded_onsets,
        "campaign_positives": campaign_positives,
        "campaign_specimens": 100,
        "asymptomatic_share": 0.5,
        "infections_total": infections_total,
        "lab_confirmed_total": lab_confirmed_total,
        "verbatim_loss": 0.0,
        "h5_band_residual": 0.0,
    }


def test_dp_theta_block_gates_on_takeoff_and_band(mod):
    # Five takeoff seeds (>=10 onsets), one dead seed; infections chosen so
    # the takeoff median lands inside the band.
    cells = [
        _cell(seed=1, recorded_onsets=12, infections_total=800),
        _cell(seed=2, recorded_onsets=15, infections_total=720),
        _cell(seed=3, recorded_onsets=20, infections_total=900),
        _cell(seed=4, recorded_onsets=11, infections_total=840),
        _cell(seed=5, recorded_onsets=10, infections_total=700),
        _cell(seed=6, recorded_onsets=3, infections_total=10),  # no takeoff
    ]
    block = mod._dp_theta_block(1e9, cells, takeoff_onsets=10)
    assert block["seeds"] == 6
    assert block["takeoff_seeds"] == 5
    assert block["takeoff_fraction"] == pytest.approx(5 / 6)
    assert block["h5_scored"] is True
    assert block["infections_total_takeoff"]["n"] == 5
    assert block["infections_total_takeoff"]["median"] == 800
    # 700 is under the band floor, so 4 of 5 takeoff cells are in band.
    assert block["h5_in_band_fraction"] == pytest.approx(4 / 5)
    assert block["h5_median_in_band"] is True


def test_dp_theta_block_under_floor_is_unscored(mod):
    cells = [
        _cell(seed=s, recorded_onsets=20, infections_total=800)
        for s in range(4)
    ]
    block = mod._dp_theta_block(1e9, cells, takeoff_onsets=10)
    assert block["takeoff_seeds"] == 4 < mod.TAKEOFF_SEED_FLOOR
    assert block["h5_scored"] is False
    assert block["h5_band_residual_mean"] is None


def test_dp_theta_block_missing_infections_is_unscored(mod):
    cells = [
        _cell(seed=s, recorded_onsets=20, infections_total=None)
        for s in range(8)
    ]
    block = mod._dp_theta_block(1e9, cells, takeoff_onsets=10)
    assert block["infections_total_takeoff"]["n"] == 0
    assert block["h5_in_band_fraction"] is None
    assert block["h5_median_in_band"] is False


def test_selection_frequencies_tie_breaks_to_smaller_theta(mod):
    # Identical verbatim losses: the merge's tie rule picks the smaller
    # theta deterministically, so it must win 100% of resamples.
    seeded = {s: (1.0, True, 0.0) for s in range(10)}
    rows = [
        {
            "theta": t,
            "h5_scored": True,
            "h5_takeoff_mean": 0.0,
            "seeded": dict(seeded),
        }
        for t in (1e9, 1e10)
    ]
    verbatim, augmented = mod._selection_frequencies(rows)
    assert verbatim["1e+09"] == 1.0
    assert verbatim["1e+10"] == 0.0
    # Identical H5 residuals too -> same tie break on the augmented column.
    assert augmented["1e+09"] == 1.0


def test_selection_frequencies_h5_moves_winner(mod):
    # Row A wins verbatim but sits far outside the band on every seed;
    # row B loses verbatim slightly and sits in band. With the band
    # residual as a third term, B must win the augmented column while A
    # keeps the verbatim one.
    seeds = range(10)
    rows = [
        {
            "theta": 1e9,
            "h5_scored": True,
            "h5_takeoff_mean": 1.0,
            "seeded": {s: (1.0, True, 1.0) for s in seeds},
        },
        {
            "theta": 1e10,
            "h5_scored": True,
            "h5_takeoff_mean": 0.0,
            "seeded": {s: (1.5, True, 0.0) for s in seeds},
        },
    ]
    verbatim, augmented = mod._selection_frequencies(rows)
    assert verbatim["1e+09"] == 1.0
    assert augmented["1e+10"] == 1.0


def test_selection_frequencies_excludes_unscored_rows(mod):
    # A row under the takeoff-seed floor sits out the augmented column
    # but still competes verbatim.
    seeds = range(10)
    rows = [
        {
            "theta": 1e9,
            "h5_scored": False,  # under the floor
            "h5_takeoff_mean": 0.0,
            "seeded": {s: (1.0, True, 99.0) for s in seeds},
        },
        {
            "theta": 1e10,
            "h5_scored": True,
            "h5_takeoff_mean": 0.0,
            "seeded": {s: (2.0, True, 0.0) for s in seeds},
        },
    ]
    verbatim, augmented = mod._selection_frequencies(rows)
    assert verbatim["1e+09"] == 1.0
    assert augmented == {"1e+10": 1.0}


def test_quantiles_empty(mod):
    q = mod._quantiles([])
    assert q == {"n": 0, "q05": None, "median": None, "q95": None}
