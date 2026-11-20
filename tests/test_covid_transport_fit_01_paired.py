"""TRANSPORT-FIT-01 paired readout: statistics contract on synthetic rows."""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import pytest

MODULE = (
    Path(__file__).resolve().parents[1]
    / "campaigns" / "covid" / "transport_fit_01" / "paired_readout.py"
)


@pytest.fixture(scope="module")
def pr():
    spec = importlib.util.spec_from_file_location("tf01_paired_readout", MODULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_paired_counts_signs_and_keeps_the_tail(pr):
    nat = {s: 0 for s in range(20)}
    cx = dict(nat)
    nat[3], cx[3] = 454, 493
    nat[4], cx[4] = 20, 11
    out = pr._paired(nat, cx)
    assert (out["positive"], out["negative"], out["tied"]) == (1, 1, 18)
    assert (out["delta"]["min"], out["delta"]["max"]) == (-9, 39)
    assert out["delta"]["mean"] == pytest.approx(1.5)
    lo, hi = out["delta"]["mean_ci95_paired_t"]
    assert lo < 0 < hi
    assert out["delta"]["leave_one_seed_out_mean_range"][0] == pytest.approx(-9 / 19)
    assert out["delta"]["largest_abs_delta_share_of_sum_abs"] == pytest.approx(39 / 48)


def test_source_quantile_is_not_the_range(pr):
    vals = [0] * 19 + [454]
    assert pr._nearest_rank(vals, 0.95) == 0
    assert max(vals) == 454


def test_undefined_share_is_dropped_not_zero(pr):
    nat = {1: None, 2: 0.5, 3: 0.25}
    cx = {1: None, 2: 0.75, 3: 0.25}
    out = pr._paired(nat, cx)
    assert out["pairs_declared"] == 3
    assert out["pairs_defined"] == 2
    assert out["native_undefined"] == 1
    assert out["delta"]["mean"] == pytest.approx(0.125)
    assert pr._share(3, 0) is None
    assert pr._fmt(None) == ""


def test_takeoff_reports_both_discordance_directions(pr):
    nat = {1: 1, 2: 1, 3: 0, 4: 0, 5: 1}
    cx = {1: 1, 2: 0, 3: 0, 4: 1, 5: 1}
    out = pr._takeoff(nat, cx)
    assert out["both_takeoff"] == 2
    assert out["neither_takeoff"] == 1
    assert out["discordant_native_to_no_takeoff"] == [1, 3]
    assert out["discordant_no_takeoff_to_takeoff"] == [1, 2]


def test_t_critical_values(pr):
    assert math.isclose(pr.T975[20], 2.0930, abs_tol=1e-4)
    assert math.isclose(pr.T975[50], 2.0096, abs_tol=1e-4)
    assert math.isclose(pr.T975[16], 2.1314, abs_tol=1e-4)
