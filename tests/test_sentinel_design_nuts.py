"""Pure-Python contract and aggregation tests for Engine C."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from picard_framework.analysis._io import write_json
from picard_framework.analysis.sentinel.design_nuts import (
    _clean,
    _interpolate_mdhr,
    _power_curve,
    aggregate_cells,
    enumerate_cells,
    load_ladder,
)
from picard_framework.analysis.stan._data import cmdstan_available

FIXTURE_DIR = Path("tmp_sentinel_nuts_test_cells")


@pytest.fixture(autouse=True)
def cleanup_fixture_dir():
    yield
    if FIXTURE_DIR.exists():
        shutil.rmtree(FIXTURE_DIR)


def _cell(
    rung: str,
    ratio: float,
    replicate: int,
    *,
    width: float = 2.0,
    coverage: bool = True,
    clean: bool = True,
    detected: bool = False,
    voyages: int = 48,
    prior_ratio: float = 0.4,
) -> dict[str, object]:
    return {
        "engine": "nuts",
        "rung": rung,
        "true_hot_ratio": ratio,
        "replicate": replicate,
        "clean": clean,
        "geometry": {"voyages": voyages},
        "ratio_width90_log": width,
        "hot_width90_log": width,
        "background_width90_log": width,
        "engine_a_ceiling_width90_log_ratio": 1.0,
        "ratio_coverage": coverage,
        "detected": detected,
        "posterior_to_prior_width_ratio_ratio": prior_ratio,
    }


def _write_cells(rows: list[dict[str, object]]) -> str:
    if FIXTURE_DIR.exists():
        shutil.rmtree(FIXTURE_DIR)
    FIXTURE_DIR.mkdir()
    for index, row in enumerate(rows):
        write_json(str(FIXTURE_DIR / f"cell_{index}.json"), row)
    return str(FIXTURE_DIR)


def test_cell_enumeration_is_reproducible_and_seeded() -> None:
    ladder = load_ladder()
    first = enumerate_cells(ladder)
    second = enumerate_cells(json.loads(json.dumps(ladder)))
    assert first == second
    assert len({cell["seed"] for cell in first}) == len(first)
    assert 1.0 in next(r for r in ladder["rungs"] if r["id"] == "C3")["sweep_ratios"]
    assert 1.0 in next(r for r in ladder["rungs"] if r["id"] == "C6")["sweep_ratios"]


def test_aggregation_widths_change_calibration_factor() -> None:
    narrow = aggregate_cells(
        _write_cells([_cell("C2", 2.0, i, width=1.5) for i in range(10)]),
    )["rungs"]
    wide = aggregate_cells(
        _write_cells([_cell("C2", 2.0, i, width=2.5) for i in range(10)]),
    )["rungs"]
    narrow_r = next(row for row in narrow if row["rung"] == "C2")["calibration_factor_r"]
    wide_r = next(row for row in wide if row["rung"] == "C2")["calibration_factor_r"]
    assert wide_r > narrow_r


def test_power_curve_and_interpolation_respond_to_signal() -> None:
    low = [
        _cell("C3", ratio, 0, detected=ratio >= 3.0)
        for ratio in (1.0, 1.25, 1.5, 2.0, 3.0)
    ]
    high = [
        _cell("C3", ratio, 0, detected=ratio >= 1.5)
        for ratio in (1.0, 1.25, 1.5, 2.0, 3.0)
    ]
    low_result = aggregate_cells(_write_cells(low))["power_curves"]["C3"]
    high_result = aggregate_cells(_write_cells(high))["power_curves"]["C3"]
    assert high_result["curve"][-1]["power"] >= low_result["curve"][-1]["power"]
    assert _interpolate_mdhr(high_result["curve"]) < _interpolate_mdhr(low_result["curve"])


def test_mixed_ratio_cells_do_not_contaminate_calibration_summary() -> None:
    rows = [
        _cell("C3", 2.0, i, width=1.5, coverage=True)
        for i in range(10)
    ] + [
        _cell("C3", 1.0, i, width=9.0, coverage=False)
        for i in range(20)
    ]
    summary = next(
        row for row in aggregate_cells(_write_cells(rows))["rungs"] if row["rung"] == "C3"
    )
    assert summary["n_cells"] == 30
    assert summary["n_calibration_cells"] == 10
    assert summary["coverage_ratio"] == pytest.approx(1.0)
    assert summary["calibration_factor_r"] == pytest.approx(1.5)


def test_sweep_power_curve_includes_calibration_arm() -> None:
    base = [
        _cell("C3", ratio, replicate, detected=ratio == 3.0)
        for ratio in (1.0, 1.5, 2.0, 3.0)
        for replicate in range(5)
    ]
    shifted = [
        _cell("C3", ratio, replicate, detected=ratio >= 2.0)
        for ratio in (1.0, 1.5, 2.0, 3.0)
        for replicate in range(5)
    ]
    low = aggregate_cells(_write_cells(base))["power_curves"]["C3"]
    high = aggregate_cells(_write_cells(shifted))["power_curves"]["C3"]
    assert [point["true_hot_ratio"] for point in low["curve"]] == [1.0, 1.5, 2.0, 3.0]
    assert high["mdhr_at_power_080"] < low["mdhr_at_power_080"]


def test_prior_learning_gate_is_graded() -> None:
    dominated = aggregate_cells(
        _write_cells([_cell("C2", 2.0, i, prior_ratio=0.99) for i in range(10)]),
    )
    learning = aggregate_cells(
        _write_cells([_cell("C2", 2.0, i, prior_ratio=0.4) for i in range(10)]),
    )
    dominated_summary = next(row for row in dominated["rungs"] if row["rung"] == "C2")
    learning_summary = next(row for row in learning["rungs"] if row["rung"] == "C2")
    assert dominated_summary["learning_gate"] is False
    assert dominated_summary["calibration_factor_usable"] is False
    assert learning_summary["learning_gate"] is True


def test_nonfinite_sampling_draws_are_not_clean() -> None:
    assert _clean(
        {
            "divergent_transitions": 0,
            "max_rhat": 1.0,
            "min_bulk_ess": 200.0,
            "finite_sampling_draws": False,
        },
    ) is False


def test_power_curve_reports_monotonicity() -> None:
    monotone = _power_curve(
        [_cell("C3", ratio, 0, detected=ratio >= 2.0) for ratio in (1.0, 1.5, 3.0)],
    )
    non_monotone = _power_curve(
        [
            _cell("C3", 1.0, 0, detected=False),
            _cell("C3", 1.5, 0, detected=True),
            _cell("C3", 3.0, 0, detected=False),
        ],
    )
    assert monotone["monotone"] is True
    assert non_monotone["monotone"] is False


def test_gates_void_bad_coverage_and_unreliable_clean_fraction() -> None:
    rows = [_cell("C2", 2.0, i, coverage=i == 0) for i in range(10)]
    result = aggregate_cells(_write_cells(rows))
    rung = next(row for row in result["rungs"] if row["rung"] == "C2")
    assert rung["coverage_gate"] is False
    assert rung["calibration_factor_usable"] is False

    rows = [_cell("C2", 2.0, i, clean=i < 8) for i in range(10)]
    rung = next(
        row for row in aggregate_cells(_write_cells(rows))["rungs"] if row["rung"] == "C2"
    )
    assert rung["clean_fraction"] == pytest.approx(0.8)
    assert rung["reliable"] is False


def test_r_below_one_is_inconsistent_and_extrapolation_never_lowers_mdhr() -> None:
    result = aggregate_cells(
        _write_cells([_cell("C2", 2.0, i, width=0.5) for i in range(10)]),
    )
    rung = next(row for row in result["rungs"] if row["rung"] == "C2")
    assert rung["r_below_one_inconsistent"] is True
    assert rung["calibration_factor_usable"] is False
    assert result["caribbean_extrapolation"]["status"] == "void"


def test_coverage_power_and_interpolation_invariants() -> None:
    rows = [
        _cell("C3", ratio, 0, detected=ratio >= 2.0)
        for ratio in (1.0, 1.25, 1.5, 2.0, 3.0)
    ]
    result = aggregate_cells(_write_cells(rows))
    curve = result["power_curves"]["C3"]
    for point in curve["curve"]:
        assert 0.0 <= point["power"] <= 1.0
        assert 0.0 <= point["ratio_coverage"] <= 1.0
    assert curve["mdhr_at_power_080"] > 1.0


@pytest.mark.skipif(not cmdstan_available(), reason="CmdStan toolchain not installed")
def test_cmdstan_cell_path_is_available() -> None:
    """The real fit path is exercised manually; CI skips without CmdStan."""
    assert cmdstan_available()
