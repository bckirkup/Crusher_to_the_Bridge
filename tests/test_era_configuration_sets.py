"""The pre/post-2020 configuration sets (#10).

What these tests are for: the module's whole job is to make the post-2020 arm
constructible *without* anyone choosing a value, so the tests that matter are
the ones asserting a coordinate cannot be defaulted, that the arms of the
buffet prompt stay four separate levers, and that no reduction appears when
the unsourced part of a hygiene arm is at zero.  A handful of change
detectors pin the two sourced spans.
"""

from __future__ import annotations

import math

import pytest

from engines.non_pharmaceutical_interventions import resolve_npi
from telemetry_buffer.observation_model.era_configuration_sets import (
    ERAS,
    POST_LEVERS,
    PRE_LEVERS,
    SWEPT_KINDS,
    UNREPRESENTED,
    era_config_patch,
    hygiene_multiplier,
    levers,
    markdown_table,
    resolve,
    swept_lever_names,
)

_HYGIENE_ARMS = (
    "buffet_entry_handwash_prompt",
    "buffet_entry_sanitizer_prompt",
)


def _corner(era: str, position: float) -> dict[str, float]:
    return dict.fromkeys(swept_lever_names(era), position)


def _post_patch(**overrides: float) -> dict:
    coordinates = _corner("post", 0.5) | overrides
    return era_config_patch("post", coordinates)


# --- no lever has a value ------------------------------------------------


def test_every_swept_lever_needs_a_coordinate() -> None:
    with pytest.raises(ValueError, match="no coordinate for"):
        era_config_patch("post", {})


def test_a_partial_coordinate_set_is_refused() -> None:
    coordinates = _corner("post", 0.5)
    del coordinates["npi.buffet_entry_handwash_prompt.hand_share"]
    with pytest.raises(ValueError, match="hand_share"):
        era_config_patch("post", coordinates)


def test_an_unknown_coordinate_is_refused() -> None:
    with pytest.raises(ValueError, match="unknown lever"):
        era_config_patch("post", _corner("post", 0.5) | {"invented": 0.5})


@pytest.mark.parametrize("position", [-0.01, 1.01, math.inf, math.nan])
def test_a_coordinate_outside_the_unit_interval_is_refused(
    position: float,
) -> None:
    with pytest.raises(ValueError, match="must lie in"):
        resolve("pre", {"hvac.filter_efficiency": position})


def test_a_boolean_coordinate_is_refused() -> None:
    with pytest.raises(ValueError, match="must be a number"):
        resolve("pre", {"hvac.filter_efficiency": True})


def test_an_unknown_era_is_refused() -> None:
    with pytest.raises(ValueError, match="unknown era"):
        levers("during")


def test_no_swept_lever_carries_a_value() -> None:
    for era in ERAS:
        for lever in levers(era):
            if lever.kind in SWEPT_KINDS:
                assert lever.value is None, lever.name


def test_every_lever_carries_a_source_and_reasoning() -> None:
    for era in ERAS:
        for lever in levers(era):
            assert lever.source, lever.name
            assert lever.note, lever.name


# --- graded sensitivity: a few coordinates, a few different outputs ------


@pytest.mark.parametrize("era", ERAS)
def test_filter_efficiency_moves_monotonically_with_its_coordinate(
    era: str,
) -> None:
    seen = [
        era_config_patch(era, _corner(era, position))["hvac"][
            "filter_efficiency"
        ]
        for position in (0.0, 0.25, 0.5, 0.75, 1.0)
    ]
    assert len(set(seen)) == len(seen)
    assert seen == sorted(seen)


def test_the_immunity_axis_rises_towards_the_pre_2020_level() -> None:
    seen = [
        _post_patch(**{"ship_graph.immune_fraction": position})[
            "ship_graph"
        ]["immune_fraction"]
        for position in (0.0, 0.5, 1.0)
    ]
    assert seen[0] < seen[1]
    assert seen[1] < seen[2]


@pytest.mark.parametrize("arm", _HYGIENE_ARMS)
def test_the_hand_share_axis_grades_the_route_multiplier(arm: str) -> None:
    key = f"npi.{arm}.hand_share"
    seen = [
        _post_patch(**{key: position})[
            "non_pharmaceutical_interventions"
        ][arm]["reference_multipliers"]["fomite"]
        for position in (0.0, 0.25, 0.5, 0.75, 1.0)
    ]
    assert len(set(seen)) == len(seen)
    assert seen == sorted(seen, reverse=True)


def test_a_wider_removal_reduces_more_at_the_same_hand_share() -> None:
    weak = hygiene_multiplier(1.0, 0.5)
    strong = hygiene_multiplier(3.0, 0.5)
    assert strong < weak


# --- the unsourced part cannot manufacture a reduction ------------------


@pytest.mark.parametrize("arm", _HYGIENE_ARMS)
def test_a_zero_hand_share_leaves_the_route_untouched(arm: str) -> None:
    measure = _post_patch(**{f"npi.{arm}.hand_share": 0.0})[
        "non_pharmaceutical_interventions"
    ][arm]
    for route, multiplier in measure["reference_multipliers"].items():
        assert multiplier == pytest.approx(1.0), route


def test_hygiene_multiplier_is_identity_at_zero_share() -> None:
    assert hygiene_multiplier(6.0, 0.0) == pytest.approx(1.0)


def test_hygiene_multiplier_is_the_survival_at_full_share() -> None:
    assert hygiene_multiplier(2.0, 1.0) == pytest.approx(0.01)


@pytest.mark.parametrize("share", [-0.1, 1.1])
def test_hygiene_multiplier_refuses_a_share_outside_the_unit_interval(
    share: float,
) -> None:
    with pytest.raises(ValueError, match="hand_share"):
        hygiene_multiplier(3.0, share)


def test_hygiene_multiplier_refuses_a_negative_removal() -> None:
    with pytest.raises(ValueError, match="removal_log10"):
        hygiene_multiplier(-1.0, 0.5)


# --- bounds and invariants ----------------------------------------------


@pytest.mark.parametrize("position", [0.0, 0.5, 1.0])
def test_every_route_multiplier_is_a_surviving_fraction(
    position: float,
) -> None:
    measures = era_config_patch("post", _corner("post", position))[
        "non_pharmaceutical_interventions"
    ]
    for arm, measure in measures.items():
        for route, multiplier in measure["reference_multipliers"].items():
            assert math.isfinite(multiplier), (arm, route)
            assert 0.0 <= multiplier <= 1.0, (arm, route)


@pytest.mark.parametrize("position", [0.0, 0.5, 1.0])
def test_the_post_patch_is_accepted_by_the_npi_interface(
    position: float,
) -> None:
    patch = era_config_patch("post", _corner("post", position))
    measures = resolve_npi(patch)
    assert sorted(measures) == sorted(_HYGIENE_ARMS)


@pytest.mark.parametrize("era", ERAS)
def test_filter_efficiency_stays_a_fraction(era: str) -> None:
    for position in (0.0, 1.0):
        eta = era_config_patch(era, _corner(era, position))["hvac"][
            "filter_efficiency"
        ]
        assert 0.0 <= eta <= 1.0


# --- the two arms stay separate ----------------------------------------


def test_the_prompt_has_four_levers_per_arm() -> None:
    for arm in _HYGIENE_ARMS:
        names = [
            lever.name for lever in POST_LEVERS
            if lever.name.startswith(f"npi.{arm}.")
        ]
        assert len(names) == 4, names


def test_coverage_and_compliance_are_not_the_route_multiplier() -> None:
    patch = _post_patch(
        **{
            "npi.buffet_entry_handwash_prompt.coverage_passenger": 0.0,
            "npi.buffet_entry_handwash_prompt.compliance": 0.0,
        },
    )
    measure = patch["non_pharmaceutical_interventions"][
        "buffet_entry_handwash_prompt"
    ]
    assert measure["coverage_by_role"]["passenger"] == pytest.approx(0.0)
    assert measure["compliance"] == pytest.approx(0.0)
    assert measure["reference_multipliers"]["fomite"] < 1.0


def test_the_two_arms_have_different_removal_spans() -> None:
    spans = {
        lever.name.split(".")[1]: lever.span
        for lever in POST_LEVERS
        if lever.name.endswith("removal_log10")
    }
    assert spans["buffet_entry_handwash_prompt"] != spans[
        "buffet_entry_sanitizer_prompt"
    ]


def test_crew_coverage_is_zero_by_construction() -> None:
    measures = _post_patch()["non_pharmaceutical_interventions"]
    for arm, measure in measures.items():
        assert measure["coverage_by_role"]["crew"] == pytest.approx(0.0), arm


# --- the pre arm carries no intervention -------------------------------


def test_the_pre_arm_has_no_npi_block_at_all() -> None:
    patch = era_config_patch("pre", _corner("pre", 0.5))
    assert "non_pharmaceutical_interventions" not in patch


def test_the_pre_arm_keeps_the_inherited_immune_fraction() -> None:
    patch = era_config_patch("pre", _corner("pre", 0.5))
    assert patch["ship_graph"]["immune_fraction"] == pytest.approx(0.2)


def test_the_immunity_axis_cannot_exceed_the_pre_level() -> None:
    pre = era_config_patch("pre", _corner("pre", 0.0))["ship_graph"][
        "immune_fraction"
    ]
    post = _post_patch(**{"ship_graph.immune_fraction": 0.0})[
        "ship_graph"
    ]["immune_fraction"]
    assert post <= pre


def test_the_pre_arm_sweeps_only_the_filter() -> None:
    assert swept_lever_names("pre") == ("hvac.filter_efficiency",)


# --- what is deliberately absent stays on the record ------------------


def test_the_unrepresented_mechanisms_are_declared_not_dropped() -> None:
    absent = {
        lever.name for lever in POST_LEVERS
        if lever.kind == UNREPRESENTED
    }
    assert "hvac.air_changes_per_hour" in absent
    assert "buffet.staff_assisted_service" in absent
    assert "embarkation.preboarding_screening" in absent
    assert "transmission.surface_cleaning" in absent


def test_an_unrepresented_lever_writes_nothing_into_the_patch() -> None:
    patch = _post_patch()
    assert "air_changes_per_hour" not in patch.get("hvac", {})
    assert "surface_cleaning" not in patch.get("transmission", {})


def test_the_pre_arm_declares_its_npi_identity_explicitly() -> None:
    kinds = {lever.name: lever.kind for lever in PRE_LEVERS}
    assert kinds["non_pharmaceutical_interventions"] == "identity"


# --- change detectors: the sourced spans -------------------------------


def test_the_sourced_filter_spans_are_the_healthy_sail_panel_figures() -> None:
    spans = {
        "pre": levers("pre")[0].span,
        "post": levers("post")[0].span,
    }
    # MERV 8 at 30% (coarsest band, so a ceiling) and MERV 13 at 90%
    # (finest band, so a floor).  Moving either needs a new source.
    assert spans["pre"] == (0.0, 0.30)
    assert spans["post"] == (0.90, 0.99)


def test_the_shipped_filter_efficiency_belongs_to_neither_era() -> None:
    shipped = 0.50
    pre = levers("pre")[0].span
    post = levers("post")[0].span
    assert shipped > pre[1]
    assert shipped < post[0]


def test_the_removal_spans_are_tuladhars_infectious_titre_figures() -> None:
    spans = {
        lever.name.split(".")[1]: lever.span
        for lever in POST_LEVERS
        if lever.name.endswith("removal_log10")
    }
    assert spans["buffet_entry_handwash_prompt"] == (2.6, 3.4)
    assert spans["buffet_entry_sanitizer_prompt"] == (1.3, 4.3)


def test_the_arms_overlap_on_infectious_titre() -> None:
    soap = (2.6, 3.4)
    rub = (1.3, 4.3)
    assert rub[1] > soap[0]


@pytest.mark.parametrize("era", ERAS)
def test_the_markdown_table_lists_every_lever(era: str) -> None:
    rows = markdown_table(era)
    for lever in levers(era):
        assert any(f"`{lever.name}`" in row for row in rows), lever.name
