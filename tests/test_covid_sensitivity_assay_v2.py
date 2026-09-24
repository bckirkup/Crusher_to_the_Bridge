"""covid_sensitivity_assay_v2: the pathogen_overrides arm key and its design.

No hull runs here. The design loads and enumerates, the new arm key lands in
a real fit run-spec's pathogen_overrides block, and the patched profile is
proven to resolve through PicardRunSpec the way the engine reads it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from picard_framework.covid_boarding_screen import (
    PATHOGEN_ID,
    apply_arm_overrides,
    enumerate_cells,
    load_design,
)
from picard_framework.covid_theta_fit import (
    build_fit_run_spec,
    load_covid_profile,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DESIGN_PATH = (
    REPO_ROOT / "picard_framework/runs/covid_sensitivity_assay_v2_design.json"
)
THETA = 4.22e10


@pytest.fixture(scope="module")
def design():
    return load_design(str(DESIGN_PATH))


def _raw_spec():
    return build_fit_run_spec("diamond_princess_2020", THETA, 20200205)


# ── design + enumeration ──────────────────────────────────────────────────

def test_design_loads_the_declared_220_cells(design):
    cells = enumerate_cells(design)
    assert len(cells) == 220
    assert len({c.key for c in cells}) == 220
    assert all(c.theta == pytest.approx(THETA) for c in cells)
    assert design.arm_ids[0] == "B0_declared"
    assert design.arm_ids[-1] == "B10_mixed_floor"


def test_canary_rows_are_the_declared_index_ranges(design):
    cells = enumerate_cells(design)
    assert [c.index for c in cells if c.arm_id == "B0_declared"] == list(
        range(0, 20)
    )
    assert [c.index for c in cells if c.arm_id == "B10_mixed_floor"] == list(
        range(200, 220)
    )


def test_b0_is_the_empty_declared_baseline(design):
    assert design.arms[0].get("overrides") == {}


# ── the pathogen_overrides arm key ────────────────────────────────────────

def test_pathogen_overrides_deep_merge_into_the_spec():
    raw = _raw_spec()
    apply_arm_overrides(
        raw,
        {"pathogen_overrides": {
            PATHOGEN_ID: {
                "symptomatic_fraction": 0.4,
                "shedding_duration_days": 8,
            },
        }},
        profile=load_covid_profile(),
    )
    po = raw["pathogen_overrides"][PATHOGEN_ID]
    assert po["symptomatic_fraction"] == pytest.approx(0.4)
    assert po["shedding_duration_days"] == 8
    # Spec-level overrides written by build_fit_run_spec survive the merge.
    assert "dose_response" in po


def test_pathogen_overrides_nested_dicts_merge():
    raw = _raw_spec()
    apply_arm_overrides(
        raw,
        {
            "profile_route_efficiency_multipliers": {"direct_contact": 0.25},
            "pathogen_overrides": {
                PATHOGEN_ID: {"secretor_negative_fraction": 0.5},
            },
        },
        profile=load_covid_profile(),
    )
    po = raw["pathogen_overrides"][PATHOGEN_ID]
    assert po["secretor_negative_fraction"] == pytest.approx(0.5)
    assert (
        po["route_efficiency_multipliers"]["direct_contact"]
        == pytest.approx(0.25)
    )


def test_pathogen_overrides_rejects_other_pathogens():
    raw = _raw_spec()
    profile = load_covid_profile()
    with pytest.raises(ValueError, match="may only patch"):
        apply_arm_overrides(
            raw,
            {"pathogen_overrides": {"norwalk_gi": {"initial_infected": 2}}},
            profile=profile,
        )


@pytest.mark.parametrize("bad", [{"remove": [PATHOGEN_ID]}, {"add": {}}])
def test_pathogen_overrides_rejects_reserved_forms(bad):
    raw = _raw_spec()
    profile = load_covid_profile()
    with pytest.raises(ValueError, match="reserved"):
        apply_arm_overrides(
            raw, {"pathogen_overrides": bad}, profile=profile,
        )


def test_pathogen_overrides_rejects_non_mapping_patch():
    raw = _raw_spec()
    profile = load_covid_profile()
    with pytest.raises(ValueError, match="must be a mapping"):
        apply_arm_overrides(
            raw,
            {"pathogen_overrides": {PATHOGEN_ID: [1, 2]}},
            profile=profile,
        )


def test_mixed_floor_arm_lands_every_lever(design):
    from picard_framework.covid_boarding_screen import prepare_cell_run_spec

    cell = next(
        c for c in enumerate_cells(design) if c.arm_id == "B10_mixed_floor"
    )
    spec = prepare_cell_run_spec(design, cell)
    po = spec["pathogen_overrides"][PATHOGEN_ID]
    assert po["symptomatic_fraction"] == pytest.approx(0.4)
    assert po["shedding_duration_days"] == 8
    assert po["secretor_negative_fraction"] == pytest.approx(0.5)
    sm = po["severity_model"]
    assert len(sm["base_probabilities_by_age_band"]) == 17
    ac = spec["config_overrides"]["transmission"]["activity_contacts"]
    assert ac["saturation_hours"]["cabin"] == pytest.approx(8)


# ── the patched profile reaching the engine ───────────────────────────────

def test_patched_profile_resolves_through_run_spec():
    from picard_framework.run_spec import PicardRunSpec

    raw = _raw_spec()
    apply_arm_overrides(
        raw,
        {"pathogen_overrides": {
            PATHOGEN_ID: {
                "symptomatic_fraction": 0.4,
                "secretor_negative_fraction": 0.5,
            },
        }},
        profile=load_covid_profile(),
    )
    spec = PicardRunSpec.from_picard_dict(str(REPO_ROOT), raw)
    resolved = spec.pathogen_profiles[PATHOGEN_ID]
    assert resolved["symptomatic_fraction"] == pytest.approx(0.4)
    assert resolved["secretor_negative_fraction"] == pytest.approx(0.5)


def test_design_loads_cleanly_under_arm_key_validation():
    design = load_design(str(DESIGN_PATH))
    assert len(design.arms) == 11
