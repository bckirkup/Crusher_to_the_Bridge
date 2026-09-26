"""Unit tests for the PARTNER-RATE-V1 preflight smoke's pure checks.

The sim drivers (``_run_cell``, ``_install_ring_recorder``, ``main``) run a
truncated declared replay and are excluded from coverage; enumeration,
spec-lands, engine-rate read-back and the binding assertions are the parts a
refactor could silently break — and the checks that gate the Batch submission.
"""
from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from picard_framework.covid_boarding_screen import enumerate_cells, load_design
from tools.covid_partner_rate_smoke import (
    RUNTIME_ARMS,
    SHIPPED_RATES,
    _check_binding,
    _check_enumeration,
    _check_spec_lands,
    _engine_rates,
)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DESIGN_PATH = os.path.join(
    REPO_ROOT,
    "picard_framework",
    "runs",
    "covid_partner_rate_assay_v1_design.json",
)
CELLS = 180
SEEDS_PER_ARM = 20
MULTIPLIERS = {
    "R1_rate_0p25": 0.25,
    "R2_rate_0p50": 0.50,
    "R3_rate_0p75": 0.75,
    "R4_rate_1p25": 1.25,
    "R5_rate_1p50": 1.50,
    "R6_rate_1p75": 1.75,
    "R7_rate_2p00": 2.00,
}


@pytest.fixture(scope="module")
def design():
    return load_design(DESIGN_PATH)


def _rates(mult: float) -> dict[str, dict[str, float]]:
    return {
        activity: {"passenger": rate * mult, "crew": rate * mult}
        for activity, rate in SHIPPED_RATES.items()
    }


def _run_entry(mult: float | None, draws: dict[str, list[int]]) -> dict:
    """A synthetic per-arm runtime record in _run_cell's shape."""
    return {
        "ring_calls": sum(len(v) for v in draws.values()),
        "ring_draws": draws,
        "engine_rates": _rates(mult) if mult is not None else {},
        "engine_droplet_split_mode": "partition" if mult is not None else "off",
        "recorded_onsets": 0,
    }


def _synthetic_runs(cut_ratio: float) -> dict[str, dict]:
    base_draws = {"leisure": [4] * SEEDS_PER_ARM, "dining_table": [8] * SEEDS_PER_ARM}
    cut_draws = {
        activity: [round(v * cut_ratio) for v in values]
        for activity, values in base_draws.items()
    }
    return {
        "R0_declared": _run_entry(1.0, base_draws),
        "R1_rate_0p25": _run_entry(0.25, cut_draws),
        "R8_pool_witness": _run_entry(None, {}),
    }


class TestEnumeration:
    def test_declared_count_and_arm_blocks(self, design) -> None:
        blocks = _check_enumeration(design, CELLS)
        assert len(blocks) == len(design.arms) == 9
        for arm_id, (lo, hi) in blocks.items():
            assert hi - lo + 1 == SEEDS_PER_ARM, arm_id
        assert blocks["R0_declared"] == [0, SEEDS_PER_ARM - 1]
        assert blocks["R1_rate_0p25"] == [SEEDS_PER_ARM, 2 * SEEDS_PER_ARM - 1]
        assert blocks["R8_pool_witness"] == [
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

    def test_baseline_arm_lands_no_activity_override(self, design) -> None:
        baseline = next(
            c for c in enumerate_cells(design) if c.arm_id == "R0_declared"
        )
        _check_spec_lands(design, baseline, REPO_ROOT)


class TestEngineRates:
    def test_reads_back_parsed_per_role_table(self) -> None:
        core = SimpleNamespace(
            activity_contacts={"leisure": {"passenger": 1.0, "crew": 1.0}},
        )
        assert _engine_rates(core) == {
            "leisure": {"passenger": 1.0, "crew": 1.0},
        }

    def test_none_reads_empty(self) -> None:
        core = SimpleNamespace(activity_contacts=None)
        assert _engine_rates(core) == {}


class TestBinding:
    def test_scaled_draws_pass(self) -> None:
        report: dict = {}
        _check_binding(None, _synthetic_runs(cut_ratio=0.25), report)
        assert report["ring_draw_mean_ratio"]["expected"] == pytest.approx(0.25)
        assert report["ring_draw_mean_ratio"]["pooled"] == pytest.approx(0.25)

    def test_inert_axis_fails(self) -> None:
        # Ratio 1.0 is the spec-lands-but-inert signature the prompt flags.
        runs = _synthetic_runs(cut_ratio=1.0)
        with pytest.raises(AssertionError, match="inert"):
            _check_binding(None, runs, {})

    def test_witness_that_draws_fails(self) -> None:
        runs = _synthetic_runs(cut_ratio=0.25)
        runs["R8_pool_witness"]["ring_calls"] = 3
        runs["R8_pool_witness"]["ring_draws"] = {"leisure": [1]}
        with pytest.raises(AssertionError, match="bit-identical"):
            _check_binding(None, runs, {})

    def test_wrong_engine_table_fails(self) -> None:
        runs = _synthetic_runs(cut_ratio=0.25)
        runs["R1_rate_0p25"]["engine_rates"]["leisure"]["passenger"] = 1.0
        with pytest.raises(AssertionError, match="engine rate"):
            _check_binding(None, runs, {})

    def test_no_ring_draws_fails(self) -> None:
        runs = _synthetic_runs(cut_ratio=0.25)
        runs["R0_declared"]["ring_draws"] = {}
        with pytest.raises(AssertionError, match="drew no partners"):
            _check_binding(None, runs, {})


def test_runtime_arms_cover_baseline_cut_and_witness() -> None:
    assert RUNTIME_ARMS == ("R0_declared", "R1_rate_0p25", "R8_pool_witness")
