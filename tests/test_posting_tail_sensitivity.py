"""The posting-tail readout: estimator behaviour, not fitted outcomes.

Sensitivity and bounds over the GPD/PWM tail fit, the paired-seed
contrasts, and McNemar — no goldens. The lead-authored module under test
is telemetry_buffer/observation_model/posting_tail_sensitivity.py.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pytest

from telemetry_buffer.observation_model.posting_tail_sensitivity import (
    COORD_KEYS,
    MARGIN_KEY,
    MIN_PAIRED_SEEDS,
    POSTING_THRESHOLD,
    _gpd_exceedance,
    _gpd_pwm,
    _mcnemar,
    _paired_diff,
    _tail_probability,
    build_report,
    render_markdown,
    tail_cell,
)

ANCHOR_FRACTION = 0.85  # 1 - ANCHOR_EXCEEDANCE


def _gpd_sample(xi: float, sigma: float, n: int, seed: int) -> np.ndarray:
    u = np.random.default_rng(seed).uniform(0.0, 1.0, n)
    if xi == 0.0:
        return -sigma * np.log1p(-u)
    return sigma / xi * ((1.0 - u) ** (-xi) - 1.0)


class TestGpdPwm:
    """The closed-form fit recovers the parameters it was simulated from."""

    @pytest.mark.parametrize("xi", (-0.2, 0.0, 0.3))
    def test_recovers_shape_and_scale(self, xi: float) -> None:
        sigma = 0.01
        sample = _gpd_sample(xi, sigma, 200_000, seed=11)
        fit = _gpd_pwm(list(sample))
        assert fit is not None
        xi_hat, sigma_hat = fit
        # PWM at n=200k carries a standard error of a few thousandths on
        # xi and a few percent on sigma; these bounds are loose against
        # that and tight enough to catch an inverted sign or a units bug.
        assert xi_hat == pytest.approx(xi, abs=0.02)
        assert sigma_hat == pytest.approx(sigma, rel=0.10)

    def test_too_few_exceedances_fits_nothing(self) -> None:
        assert _gpd_pwm(list(_gpd_sample(0.2, 0.01, 10, seed=3))) is None


class TestTailProbability:
    def test_matches_the_empirical_tail_on_a_lognormal(self) -> None:
        rng = np.random.default_rng(23)
        values = list(rng.lognormal(math.log(0.01), 0.8, 40_000))
        anchor = float(np.quantile(values, ANCHOR_FRACTION))
        modelled = _tail_probability(values, 0.03, anchor)
        empirical = float(np.mean([v >= 0.03 for v in values]))
        assert modelled is not None
        assert empirical > 0.0
        assert modelled == pytest.approx(empirical, rel=0.10)


class TestGpdExceedance:
    def test_xi_zero_limit_is_exponential(self) -> None:
        assert _gpd_exceedance(0.0, 0.01, 0.5) == pytest.approx(
            math.exp(-50.0), rel=1e-9,
        )
        assert _gpd_exceedance(1e-9, 0.01, 0.5) == pytest.approx(
            math.exp(-50.0), rel=1e-4,
        )

    def test_a_bounded_tail_past_its_endpoint_is_zero(self) -> None:
        # xi < 0 gives endpoint sigma/|xi| = 0.02 above the anchor.
        assert _gpd_exceedance(-0.5, 0.01, 0.05) == pytest.approx(0.0)

    def test_a_distance_at_or_below_zero_is_certain(self) -> None:
        assert _gpd_exceedance(0.3, 0.01, 0.0) == pytest.approx(1.0)
        assert _gpd_exceedance(0.3, 0.01, -0.01) == pytest.approx(1.0)


class TestTailCell:
    def test_everything_is_in_bounds(self) -> None:
        rng = np.random.default_rng(29)
        values = list(rng.lognormal(math.log(0.01), 0.8, 500))
        cell = tail_cell(values)
        for key in ("modelled", "modelled_at_check_level"):
            if cell.get(key) is not None:
                assert 0.0 <= cell[key] <= 1.0
        assert 0.0 <= cell["direct"]["probability"] <= 1.0
        assert 0.0 <= cell["direct_at_check_level"]["probability"] <= 1.0
        if cell.get("gpd_sigma") is not None:
            assert cell["gpd_sigma"] > 0.0

    def test_an_anchor_above_the_threshold_refuses_the_model(self) -> None:
        values = [0.05 + 0.001 * i for i in range(200)]
        cell = tail_cell(values)
        assert cell["modelled"] is None
        assert cell["modelled_reason"] == "anchor_above_threshold"

    def test_too_few_exceedances_leaves_modelled_none(self) -> None:
        values = [0.001 * (i + 1) for i in range(30)]
        cell = tail_cell(values)
        assert cell["modelled"] is None


def _row(seed: int, margin: float, **coords: Any) -> dict[str, Any]:
    """One synthetic run row carrying every coordinate the cell key reads."""
    row = dict.fromkeys(COORD_KEYS)
    row.update({
        "arm": "test",
        "platform_id": "classic_cruise_1900",
        "surveillance": "syndromic",
        "dose_adjustment": "dose4",
        "num_epochs": 168,
        "boarding_mechanism_rung": "reportable",
        "boarding_rate_mode": "renewal",
        "boarding_age_draw": "stationary_detectable",
        "illness_duration_draw": "empirical_survival",
        "symptomatic_stream": True,
    })
    row.update(coords)
    row.update({
        "seed": seed,
        "posted": margin >= POSTING_THRESHOLD,
        "reported_case_attack_rate_passenger": margin,
        "reported_case_attack_rate_crew": margin,
        "secondary_infections": 10.0 * margin,
        "imported": 4.0,
    })
    return row


def _cell_rows(
    margins: list[float], seeds: list[int] | None = None, **coords: Any,
) -> list[dict[str, Any]]:
    seeds = seeds if seeds is not None else list(range(len(margins)))
    return [_row(seed, margin, **coords) for seed, margin in zip(seeds, margins)]


def _margins(n: int, seed: int, centre: float = 0.01) -> list[float]:
    return list(np.random.default_rng(seed).lognormal(math.log(centre), 0.6, n))


class TestBuildReport:
    """Pairing rules: exactly one differing coordinate, enough shared seeds."""

    def test_pairs_only_form_on_a_single_coordinate(self) -> None:
        n = MIN_PAIRED_SEEDS + 10
        rows = (
            _cell_rows(_margins(n, 1), boarding_mechanism_rung="reportable")
            + _cell_rows(_margins(n, 2), boarding_mechanism_rung="symptomatic")
            # Two coordinates off "reportable": never paired with it.
            + _cell_rows(
                _margins(n, 3), boarding_mechanism_rung="renewal_stationary",
                symptomatic_stream=False,
            )
        )
        report = build_report(rows)
        assert report["n_cells"] == 3
        coords = {pair["coordinate"] for pair in report["pairs"]}
        assert coords == {"boarding_mechanism_rung"}
        (pair,) = report["pairs"]
        assert pair["n_shared_seeds"] == n

    def test_too_few_shared_seeds_forms_no_pair(self) -> None:
        n = MIN_PAIRED_SEEDS - 1
        rows = (
            _cell_rows(_margins(n, 1), boarding_mechanism_rung="reportable")
            + _cell_rows(_margins(n, 2), boarding_mechanism_rung="symptomatic")
        )
        assert build_report(rows)["pairs"] == []

    def test_a_duplicate_seed_inside_a_cell_forms_no_pair(self) -> None:
        n = MIN_PAIRED_SEEDS + 10
        left = _cell_rows(
            _margins(n, 1), boarding_mechanism_rung="reportable",
        )
        left.append(left[0].copy())  # seed 0 twice inside the cell
        right = _cell_rows(
            _margins(n, 2), boarding_mechanism_rung="symptomatic",
        )
        assert build_report(left + right)["pairs"] == []

    def test_identical_cells_diff_by_nothing(self) -> None:
        margins = _margins(MIN_PAIRED_SEEDS + 10, 1)
        rows = (
            _cell_rows(margins, boarding_mechanism_rung="reportable")
            + _cell_rows(margins, boarding_mechanism_rung="symptomatic")
        )
        (pair,) = build_report(rows)["pairs"]
        assert pair["identical_import_fraction"] == pytest.approx(1.0)
        margin = pair["differences"][MARGIN_KEY]
        assert margin["mean_difference"] == pytest.approx(0.0)
        assert pair["posting"]["n_gained"] == 0
        assert pair["posting"]["n_lost"] == 0
        assert pair["posting"]["exact_p_value"] is None

    def test_a_shifted_cell_gains_postings(self) -> None:
        n = MIN_PAIRED_SEEDS + 10
        rng = np.random.default_rng(5)
        base = 0.028 + rng.normal(0.0, 0.001, n)
        left = [float(v) for v in base]
        right = [v + 0.01 for v in left]  # 0.028 -> 0.038 crosses 0.03
        # "reportable" sorts before "symptomatic", so it is the pair's left
        # cell; the shifted cell is the right one.
        rows = (
            _cell_rows(left, boarding_mechanism_rung="reportable")
            + _cell_rows(right, boarding_mechanism_rung="symptomatic")
        )
        (pair,) = build_report(rows)["pairs"]
        margin = pair["differences"][MARGIN_KEY]
        assert margin["mean_difference"] == pytest.approx(0.01, abs=1e-9)
        lo, hi = margin["mean_difference_ci95"]
        assert lo > 0.0
        assert pair["posting"]["n_gained"] > pair["posting"]["n_lost"]
        assert 0.0 < pair["posting"]["exact_p_value"] <= 1.0

    def test_pairing_with_a_shared_component_cuts_variance(self) -> None:
        n = MIN_PAIRED_SEEDS + 10
        rng = np.random.default_rng(7)
        common = rng.lognormal(math.log(0.01), 0.6, n)
        left = list(common)
        right = list(common + rng.normal(0.0, 0.001, n))
        rows = (
            _cell_rows(left, boarding_mechanism_rung="symptomatic")
            + _cell_rows(right, boarding_mechanism_rung="reportable")
        )
        (pair,) = build_report(rows)["pairs"]
        assert pair["differences"][MARGIN_KEY]["variance_reduction"] > 1.0


class TestArchitectureCoordinates:
    """Complement and kernel sweep coordinates the pairing must respect."""

    def test_occupancy_is_its_own_coordinate(self) -> None:
        n = MIN_PAIRED_SEEDS + 10
        rows = (
            _cell_rows(_margins(n, 1), num_agents=478)
            + _cell_rows(_margins(n, 2), num_agents=955)
        )
        report = build_report(rows)
        assert report["n_cells"] == 2
        assert [pair["coordinate"] for pair in report["pairs"]] == [
            "num_agents",
        ]

    def test_occupancy_plus_kernel_refuses_to_pair(self) -> None:
        n = MIN_PAIRED_SEEDS + 10
        rows = (
            _cell_rows(
                _margins(n, 1), num_agents=478, contact_class_exponent=0.0,
            )
            + _cell_rows(
                _margins(n, 2), num_agents=955, contact_class_exponent=0.5,
            )
        )
        report = build_report(rows)
        assert report["n_cells"] == 2
        assert report["pairs"] == []

    def test_kernel_exponent_is_its_own_coordinate(self) -> None:
        n = MIN_PAIRED_SEEDS + 10
        rows = (
            _cell_rows(_margins(n, 1), contact_class_exponent=0.0)
            + _cell_rows(_margins(n, 2), contact_class_exponent=0.5)
            + _cell_rows(_margins(n, 3), contact_class_exponent=1.0)
        )
        report = build_report(rows)
        assert report["n_cells"] == 3
        assert {
            pair["coordinate"] for pair in report["pairs"]
        } == {"contact_class_exponent"}
        assert len(report["pairs"]) == 3


class TestPairedDiff:
    """n_identical uses a tolerance, not exact float equality."""

    def test_near_zero_diffs_count_as_identical(self) -> None:
        left = [{"imported": 4.0 + 1e-15} for _ in range(MIN_PAIRED_SEEDS)]
        right = [{"imported": 4.0} for _ in range(MIN_PAIRED_SEEDS)]
        out = _paired_diff(left, right, "imported")
        assert out["n_identical"] == MIN_PAIRED_SEEDS
        assert out["mean_difference"] == pytest.approx(0.0, abs=1e-12)

    def test_material_diffs_are_not_identical(self) -> None:
        left = [{"imported": 4.0} for _ in range(MIN_PAIRED_SEEDS)]
        right = [{"imported": 5.0} for _ in range(MIN_PAIRED_SEEDS)]
        out = _paired_diff(left, right, "imported")
        assert out["n_identical"] == 0
        assert out["mean_difference"] == pytest.approx(1.0)


class TestMcnemar:
    def _posted_rows(self, flags: list[bool]) -> list[dict[str, Any]]:
        return [{"posted": flag} for flag in flags]

    def test_no_discordant_pairs_gives_no_p_value(self) -> None:
        both = [True] * 10 + [False] * 10
        out = _mcnemar(self._posted_rows(both), self._posted_rows(both))
        assert out["n_gained"] == 0
        assert out["n_lost"] == 0
        assert out["exact_p_value"] is None

    def test_discordant_pairs_give_a_p_in_bounds(self) -> None:
        left = self._posted_rows([False] * 20)
        right = self._posted_rows([True] * 15 + [False] * 5)
        out = _mcnemar(left, right)
        assert out["n_gained"] == 15
        assert out["n_lost"] == 0
        assert 0.0 < out["exact_p_value"] <= 1.0


class TestRenderMarkdown:
    def test_both_tables_and_one_line_per_record(self) -> None:
        n = MIN_PAIRED_SEEDS + 10
        rows = (
            _cell_rows(_margins(n, 1), boarding_mechanism_rung="reportable")
            + _cell_rows(_margins(n, 2), boarding_mechanism_rung="symptomatic")
        )
        report = build_report(rows)
        text = render_markdown(report)
        assert "| arm | platform | days | rung |" in text
        assert "| coordinate | platform | days | seeds |" in text
        cell_lines = [
            line for line in text.splitlines()
            if line.startswith("| test |")
        ]
        assert len(cell_lines) == report["n_cells"]
        pair_lines = [
            line for line in text.splitlines()
            if line.startswith("| boarding_mechanism_rung |")
        ]
        assert len(pair_lines) == report["n_pairs"]
