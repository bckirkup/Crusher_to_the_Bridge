"""Unit tests for the PLUME-DOSE-V1 preflight smoke's pure checks.

The sim drivers (``_run_cell``, ``_install_ring_recorder``, ``main``) run a
truncated declared replay and are excluded from coverage; enumeration,
spec-lands, the stubbed dose-formula check, and the binding assertions are
the parts a refactor could silently break — and the checks that gate the
Batch submission.
"""
from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from picard_framework.covid_boarding_screen import enumerate_cells, load_design
from tools import covid_plume_dose_smoke as smoke
from tools.covid_plume_dose_smoke import (
    RUNTIME_ARMS,
    SHIPPED_BETA,
    _check_binding,
    _check_enumeration,
    _check_spec_lands,
    _engine_near_field,
    dose_scaling_ratio,
    plume_dose_at_beta,
)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DESIGN_PATH = os.path.join(
    REPO_ROOT,
    "picard_framework",
    "runs",
    "covid_plume_dose_assay_v1_design.json",
)
CELLS = 200
SEEDS_PER_ARM = 20
D1_BETA = 4080.0

BASE_RATES = {
    "cabin": {"passenger": 0.25, "crew": 0.25},
    "corridor": {"passenger": 0.25, "crew": 0.25},
    "work_service": {"passenger": 2.9, "crew": 2.9},
    "work_other": {"passenger": 0.5, "crew": 0.5},
    "dining_table": {"passenger": 2.0, "crew": 2.0},
    "dining_venue": {"passenger": 2.0, "crew": 2.0},
    "leisure": {"passenger": 1.0, "crew": 1.0},
    "other": {"passenger": 0.0, "crew": 0.0},
}


@pytest.fixture(scope="module")
def design():
    return load_design(DESIGN_PATH)


def _near_field(beta: float) -> dict[str, float]:
    return {
        "beta": beta,
        "flushed": beta * 0.5,
        "mode": "two_box",
    }


def _run_entry(
    beta: float | None, draws: dict[str, list[int]],
) -> dict:
    """A synthetic per-arm runtime record in _run_cell's shape."""
    return {
        "ring_calls": sum(len(v) for v in draws.values()),
        "ring_draws": draws,
        "engine_near_field": (
            _near_field(beta) if beta is not None else _near_field(SHIPPED_BETA)
        ),
        "engine_rates": dict(BASE_RATES),
        "engine_droplet_split_mode": "partition" if beta is not None else "off",
        "recorded_onsets": 0,
    }


def _synthetic_runs() -> dict[str, dict]:
    knockout_rates = dict(BASE_RATES)
    knockout_rates["dining_table"] = {"passenger": 0.0, "crew": 0.0}
    knockout_rates["dining_venue"] = {"passenger": 0.0, "crew": 0.0}
    entry = _run_entry(SHIPPED_BETA, {"leisure": [4, 4], "dining_table": [0, 0]})
    entry["engine_rates"] = knockout_rates
    return {
        "D0_declared": _run_entry(SHIPPED_BETA, {"leisure": [4, 4]}),
        "D1_dose_0p05": _run_entry(D1_BETA, {"leisure": [4, 4]}),
        "K1_dining_off": entry,
        "W_pool_witness": _run_entry(None, {}),
    }


class TestEnumeration:
    def test_declared_count_and_arm_blocks(self, design) -> None:
        blocks = _check_enumeration(design, CELLS)
        assert len(blocks) == len(design.arms) == 10
        for arm_id, (lo, hi) in blocks.items():
            assert hi - lo + 1 == SEEDS_PER_ARM, arm_id
        assert blocks["D0_declared"] == [0, SEEDS_PER_ARM - 1]
        assert blocks["D1_dose_0p05"] == [SEEDS_PER_ARM, 2 * SEEDS_PER_ARM - 1]
        assert blocks["W_pool_witness"] == [
            CELLS - SEEDS_PER_ARM, CELLS - 1,
        ]

    def test_wrong_declared_count_fails(self, design) -> None:
        with pytest.raises(AssertionError):
            _check_enumeration(design, CELLS + 1)


class TestSpecLands:
    def test_every_arm_override_reaches_the_spec(self, design) -> None:
        for cell in enumerate_cells(design):
            if cell.seed != design.seed_base:
                continue
            _check_spec_lands(design, cell, REPO_ROOT)

    def test_baseline_arm_lands_no_override(self, design) -> None:
        baseline = next(
            c for c in enumerate_cells(design) if c.arm_id == "D0_declared"
        )
        _check_spec_lands(design, baseline, REPO_ROOT)


class TestEngineNearField:
    def test_reads_back_beta_and_flushed(self) -> None:
        core = SimpleNamespace(
            near_field_air=SimpleNamespace(
                interzonal_airflow_m3_per_hour=816.0,
                mode="two_box",
            ),
            near_field_flushed_volume_m3_per_epoch=408.0,
        )
        assert _engine_near_field(core) == {
            "beta": 816.0,
            "flushed": 408.0,
            "mode": "two_box",
        }


class TestDoseFormula:
    def test_dose_scales_inverse_beta(self) -> None:
        ratio = dose_scaling_ratio(D1_BETA, SHIPPED_BETA)
        assert ratio == pytest.approx(SHIPPED_BETA / D1_BETA)

    def test_dose_is_positive_and_finite(self) -> None:
        assert plume_dose_at_beta(SHIPPED_BETA) > 0.0


class TestBinding:
    def test_declared_arms_pass(self, design) -> None:
        report: dict = {}
        _check_binding(design, _synthetic_runs(), report)
        assert report["plume_dose_scaling"]["expected"] == pytest.approx(0.05)

    def test_witness_that_draws_fails(self, design) -> None:
        runs = _synthetic_runs()
        runs["W_pool_witness"]["ring_calls"] = 3
        runs["W_pool_witness"]["ring_draws"] = {"leisure": [1]}
        with pytest.raises(AssertionError, match="bit-identical"):
            _check_binding(design, runs, {})

    def test_inert_beta_fails(self, design) -> None:
        runs = _synthetic_runs()
        runs["D1_dose_0p05"]["engine_near_field"] = _near_field(SHIPPED_BETA)
        with pytest.raises(AssertionError, match="engine beta"):
            _check_binding(design, runs, {})

    def test_untracked_flushed_fails(self, design) -> None:
        runs = _synthetic_runs()
        runs["D1_dose_0p05"]["engine_near_field"]["flushed"] = 102.0
        with pytest.raises(AssertionError, match="flushed"):
            _check_binding(design, runs, {})

    def test_inert_dose_formula_fails(self, design, monkeypatch) -> None:
        monkeypatch.setattr(
            smoke, "plume_dose_at_beta", lambda _beta: 1.0,
        )
        with pytest.raises(AssertionError, match="does not bind"):
            _check_binding(design, _synthetic_runs(), {})

    def test_knockout_rate_not_zero_fails(self, design) -> None:
        runs = _synthetic_runs()
        runs["K1_dining_off"]["engine_rates"]["dining_table"] = {
            "passenger": 2.0,
            "crew": 2.0,
        }
        with pytest.raises(AssertionError, match="engine rate"):
            _check_binding(design, runs, {})

    def test_knockout_draws_partners_fails(self, design) -> None:
        runs = _synthetic_runs()
        runs["K1_dining_off"]["ring_draws"]["dining_table"] = [1]
        with pytest.raises(AssertionError, match="knocked-out"):
            _check_binding(design, runs, {})


def test_runtime_arms_cover_baseline_dose_knockout_and_witness() -> None:
    assert RUNTIME_ARMS == (
        "D0_declared",
        "D1_dose_0p05",
        "K1_dining_off",
        "W_pool_witness",
    )
