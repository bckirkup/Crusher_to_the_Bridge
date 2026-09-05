"""Sweep-resolution checks: an axis is only informative where it moves output."""

from __future__ import annotations

import pytest

from picard_framework.analysis import sweep_degeneracy

AXIS = "parameters.dose_adjustment"
OUT = "derived.infection_attack_rate_passenger"
GROUP = ("parameters.platform_id",)


def _rows(values: dict[float, dict[int, str]]) -> list[dict[str, str]]:
    """One row per (rung, seed) with a single hull and one output column."""
    return [
        {
            AXIS: str(rung),
            "parameters.seed": str(seed),
            "parameters.platform_id": "classic_cruise_1900",
            OUT: value,
        }
        for rung, per_seed in values.items()
        for seed, value in per_seed.items()
    ]


def test_ladder_inside_a_flat_region_is_reported_as_one_rung() -> None:
    rows = _rows({
        12.0: {760: "0.0032", 761: "0.0854"},
        13.0: {760: "0.0032", 761: "0.0854"},
        14.0: {760: "0.0032", 761: "0.0854"},
    })

    groups = sweep_degeneracy.degenerate_rung_groups(
        rows, axis=AXIS, outputs=(OUT,), group=GROUP,
    )

    assert groups == [["12.0", "13.0", "14.0"]]
    assert sweep_degeneracy.resolved_fraction(
        rows, axis=AXIS, outputs=(OUT,), group=GROUP,
    ) == pytest.approx(1 / 3)


def test_axis_that_moves_every_seed_is_fully_resolved() -> None:
    rows = _rows({
        4.0: {760: "0.0348", 761: "0.4177"},
        6.0: {760: "0.0201", 761: "0.2278"},
        8.0: {760: "0.0064", 761: "0.0791"},
    })

    assert sweep_degeneracy.degenerate_rung_groups(
        rows, axis=AXIS, outputs=(OUT,), group=GROUP,
    ) == []
    assert sweep_degeneracy.resolved_fraction(
        rows, axis=AXIS, outputs=(OUT,), group=GROUP,
    ) == pytest.approx(1.0)


def test_partial_collapse_names_only_the_flat_stretch() -> None:
    rows = _rows({
        4.0: {760: "0.0348"},
        6.0: {760: "0.0201"},
        12.0: {760: "0.0032"},
        14.0: {760: "0.0032"},
    })

    groups = sweep_degeneracy.degenerate_rung_groups(
        rows, axis=AXIS, outputs=(OUT,), group=GROUP,
    )

    assert groups == [["12.0", "14.0"]]
    assert sweep_degeneracy.resolved_fraction(
        rows, axis=AXIS, outputs=(OUT,), group=GROUP,
    ) == pytest.approx(3 / 4)


def test_a_rung_differing_on_one_seed_only_is_not_collapsed() -> None:
    rows = _rows({
        12.0: {760: "0.0032", 761: "0.0854"},
        13.0: {760: "0.0032", 761: "0.0855"},
    })

    assert sweep_degeneracy.degenerate_rung_groups(
        rows, axis=AXIS, outputs=(OUT,), group=GROUP,
    ) == []


def test_rungs_sharing_no_replicate_are_not_called_identical() -> None:
    """Disjoint seed sets carry no evidence either way about the axis."""
    rows = _rows({
        12.0: {760: "0.0032"},
        13.0: {761: "0.0032"},
    })

    assert sweep_degeneracy.degenerate_rung_groups(
        rows, axis=AXIS, outputs=(OUT,), group=GROUP,
    ) == []


def test_absent_column_is_an_error_rather_than_an_empty_verdict() -> None:
    rows = _rows({12.0: {760: "0.0032"}})

    with pytest.raises(sweep_degeneracy.SweepColumnError, match="absent"):
        sweep_degeneracy.degenerate_rung_groups(
            rows, axis=AXIS, outputs=("derived.not_recorded",), group=GROUP,
        )


def test_report_names_the_collapsed_rungs() -> None:
    rows = _rows({
        12.0: {760: "0.0032"},
        14.0: {760: "0.0032"},
    })

    report = sweep_degeneracy.format_report(
        rows, axis=AXIS, outputs=(OUT,), group=GROUP,
    )

    assert "Collapsed rungs" in report
    assert "12.0, 14.0" in report
    assert "resolved fraction: 0.500" in report
