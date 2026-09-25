"""Unit tests for the LAMBDA-CROSS-V1 preflight smoke's pure checks.

The sim drivers (``run_cell`` calls in ``main``) run a truncated declared
replay and are excluded from coverage; enumeration, theta spec-lands, and
the susceptibility-scale arithmetic are the parts a refactor could
silently break — and the checks that gate the Batch submission.
"""
from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from picard_framework.covid_boarding_screen import enumerate_cells, load_design
from picard_framework.covid_theta_fit import load_covid_profile
from tools.covid_assay_smoke import check_enumeration
from tools.covid_lambda_cross_smoke import (
    _cell_at,
    check_theta_spec_lands,
    engine_susceptibility_scale,
    expected_susceptibility_scale,
    spec_susceptibility_scale,
)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DESIGN_PATH = os.path.join(
    REPO_ROOT,
    "picard_framework",
    "runs",
    "covid_lambda_cross_v1_design.json",
)
CELLS = 140
SEEDS_PER_THETA = 20
DECLARED_THETA = 42200000000.0
DEEP_THETA = 42200000.0


@pytest.fixture(scope="module")
def design():
    return load_design(DESIGN_PATH)


class TestEnumeration:
    def test_declared_count_and_theta_blocks(self, design) -> None:
        blocks = check_enumeration(design, CELLS)
        assert len(blocks) == len(design.arms) == 1
        cells = enumerate_cells(design)
        thetas = sorted({c.theta for c in cells})
        assert len(thetas) == 7
        for i, theta in enumerate(design.axis_points):
            block = cells[i * SEEDS_PER_THETA:(i + 1) * SEEDS_PER_THETA]
            assert all(c.theta == theta[0] for c in block)
        # The canary row (deepest theta) sits at indices 120-139.
        assert cells[120].theta == DEEP_THETA
        assert cells[139].theta == DEEP_THETA

    def test_wrong_declared_count_fails(self, design) -> None:
        with pytest.raises(AssertionError):
            check_enumeration(design, CELLS + 1)


class TestThetaScaleArithmetic:
    def test_expected_scale_is_linear_in_theta(self) -> None:
        profile = load_covid_profile(REPO_ROOT)
        dr = profile["dose_response"]
        factor = (dr["alpha"] + dr["beta"]) / dr["alpha"]
        assert expected_susceptibility_scale(
            profile, DECLARED_THETA,
        ) == pytest.approx(DECLARED_THETA * factor)
        assert expected_susceptibility_scale(
            profile, DEEP_THETA,
        ) == pytest.approx(
            expected_susceptibility_scale(profile, DECLARED_THETA) * 0.001,
        )


class TestSpecLands:
    def test_every_theta_reaches_the_spec(self, design) -> None:
        landed = check_theta_spec_lands(design, REPO_ROOT)
        assert len(landed) == 7
        profile = load_covid_profile(REPO_ROOT)
        for theta, scale in landed.items():
            assert scale == pytest.approx(
                expected_susceptibility_scale(profile, theta),
            )

    def test_single_cell_spec_scale(self, design) -> None:
        cell = _cell_at(design, DEEP_THETA, design.seed_base)
        landed = spec_susceptibility_scale(design, cell, REPO_ROOT)
        profile = load_covid_profile(REPO_ROOT)
        assert landed == pytest.approx(
            expected_susceptibility_scale(profile, DEEP_THETA),
        )


class TestEngineReadback:
    def test_reads_scale_off_core(self) -> None:
        core = SimpleNamespace(
            pathogen_profiles={
                "sars_cov2_resp": {
                    "dose_response": {"susceptibility_scale": 123.5},
                },
            },
        )
        assert engine_susceptibility_scale(core, "sars_cov2_resp") == pytest.approx(123.5)
