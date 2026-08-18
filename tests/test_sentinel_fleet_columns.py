"""Boundaries of the extracted fleet posterior column helpers."""

from __future__ import annotations

import math
import os
import sys
from types import SimpleNamespace

import numpy as np
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from picard_framework.analysis.stan._sentinel_fleet_reference import (  # noqa: E402
    _put_derived_columns,
    _put_indexed,
    _put_wastewater_columns,
)


def test_put_indexed_uses_one_based_stan_names() -> None:
    columns: dict[str, list[float]] = {}
    _put_indexed(columns, "lambda_port[{}]", 3, lambda p: [float(p + 1)])
    assert "lambda_port[0]" not in columns
    assert columns["lambda_port[1]"] == [1.0]
    assert columns["lambda_port[2]"] == [2.0]
    assert columns["lambda_port[3]"] == [3.0]


def test_derived_hazard_ratios_grade_with_log_crew_ratio() -> None:
    logs = [-0.5, 0.0, 0.5]
    per_draw = [
        {
            "u": {"log_crew_ratio": log_c, "beta_repeat": 0.0},
            "aboard_cases": 1.0,
            "total": 10.0,
            "imported_port": np.array([2.0]),
            "loglik": -1.0,
        }
        for log_c in logs
    ]
    columns: dict[str, list[float]] = {}
    _put_derived_columns(columns, per_draw)
    ratios = columns["crew_hazard_ratio"]
    assert ratios == [math.exp(v) for v in logs]
    assert ratios == sorted(ratios)
    assert ratios[-1] - ratios[0] > 0.5


def test_secondary_cases_never_go_negative_and_import_share_is_a_fraction() -> None:
    per_draw = [
        {
            "u": {"log_crew_ratio": 0.0, "beta_repeat": 0.0},
            "aboard_cases": aboard,
            "total": total,
            "imported_port": np.array([imported]),
            "loglik": 0.0,
        }
        for total, imported, aboard in (
            (10.0, 2.0, 3.0),
            (5.0, 4.0, 4.0),
            (1.0, 0.0, 0.0),
        )
    ]
    columns: dict[str, list[float]] = {}
    _put_derived_columns(columns, per_draw)
    assert all(sec >= 0.0 for sec in columns["secondary_cases"])
    assert columns["secondary_cases"][0] == pytest.approx(5.0)
    assert columns["secondary_cases"][1] == pytest.approx(0.0)
    for share in columns["import_share"]:
        assert 0.0 <= share <= 1.0
        assert math.isfinite(share)


def test_wastewater_columns_are_absent_without_the_channel() -> None:
    layout = SimpleNamespace(has_wastewater=False)
    columns: dict[str, list[float]] = {}
    _put_wastewater_columns(columns, [{"u": {}, "loglik_ww": -2.0}], layout)
    assert columns == {}


def test_wastewater_loglik_is_copied_when_the_channel_is_on() -> None:
    layout = SimpleNamespace(has_wastewater=True)
    per_draw = [
        {
            "u": {"ww_logit_base": 0.1, "ww_slope": 0.2, "ww_conc": 1.0},
            "loglik_ww": -3.0,
        },
        {
            "u": {"ww_logit_base": 0.2, "ww_slope": 0.4, "ww_conc": 2.0},
            "loglik_ww": -1.0,
        },
    ]
    columns: dict[str, list[float]] = {}
    _put_wastewater_columns(columns, per_draw, layout)
    assert columns["loglik_wastewater"] == [-3.0, -1.0]
    assert columns["ww_slope"] == [0.2, 0.4]
    assert columns["ww_slope"][1] > columns["ww_slope"][0]
