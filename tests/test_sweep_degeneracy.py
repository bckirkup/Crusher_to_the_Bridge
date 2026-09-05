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


def test_report_on_a_resolved_axis_says_so_and_names_no_group() -> None:
    rows = _rows({
        4.0: {760: "0.0348"},
        6.0: {760: "0.0201"},
    })

    report = sweep_degeneracy.format_report(
        rows, axis=AXIS, outputs=(OUT,), group=GROUP,
    )

    assert "Every rung is distinguishable" in report
    assert "Collapsed rungs" not in report


def test_no_rows_is_an_error_rather_than_a_resolved_verdict() -> None:
    with pytest.raises(sweep_degeneracy.SweepColumnError, match="no rows"):
        sweep_degeneracy.degenerate_rung_groups([], axis=AXIS, outputs=(OUT,))


def test_non_numeric_rung_labels_still_group_and_report() -> None:
    """A categorical axis (a strategy name) is ordered by label, not by value."""
    rows = [
        {
            AXIS: rung,
            "parameters.seed": "760",
            "parameters.platform_id": "classic_cruise_1900",
            OUT: value,
        }
        for rung, value in (("none_true", "0.0032"), ("syndromic", "0.0032"))
    ]

    assert sweep_degeneracy.degenerate_rung_groups(
        rows, axis=AXIS, outputs=(OUT,), group=GROUP,
    ) == [["none_true", "syndromic"]]


def _write_summary(path, rows) -> None:
    header = (AXIS, "parameters.seed", "parameters.platform_id", OUT)
    lines = [",".join(header)]
    lines.extend(",".join(str(row[column]) for column in header) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_cli_writes_the_report_and_reads_the_rungs_back(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_summary(
        tmp_path / "summary.csv",
        _rows({12.0: {760: "0.0032"}, 14.0: {760: "0.0032"}}),
    )

    code = sweep_degeneracy.main([
        "summary.csv",
        "--axis", AXIS,
        "--outputs", OUT,
        "--group", "parameters.platform_id",
        "--out", "report.md",
    ])

    assert code == 0
    assert "12.0, 14.0" in (tmp_path / "report.md").read_text(encoding="utf-8")


def test_cli_prints_to_stdout_when_no_out_path_is_given(
    tmp_path, monkeypatch, capsys,
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_summary(
        tmp_path / "summary.csv",
        _rows({4.0: {760: "0.0348"}, 6.0: {760: "0.0201"}}),
    )

    code = sweep_degeneracy.main([
        "summary.csv", "--axis", AXIS, "--outputs", OUT,
    ])

    assert code == 0
    assert "Every rung is distinguishable" in capsys.readouterr().out


def test_cli_fails_the_submission_when_a_stretch_collapsed(
    tmp_path, monkeypatch,
) -> None:
    """The pre-submission gate: a degenerate ladder must not exit zero."""
    monkeypatch.chdir(tmp_path)
    collapsed = _rows({12.0: {760: "0.0032"}, 14.0: {760: "0.0032"}})
    resolved = _rows({4.0: {760: "0.0348"}, 6.0: {760: "0.0201"}})
    _write_summary(tmp_path / "collapsed.csv", collapsed)
    _write_summary(tmp_path / "resolved.csv", resolved)

    argv = ["--axis", AXIS, "--outputs", OUT, "--fail-on-degenerate"]

    assert sweep_degeneracy.main(["collapsed.csv", *argv]) == 1
    assert sweep_degeneracy.main(["resolved.csv", *argv]) == 0


def test_cli_refuses_a_summary_outside_the_working_directory(
    tmp_path, monkeypatch,
) -> None:
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    _write_summary(tmp_path / "outside.csv", _rows({12.0: {760: "0.0032"}}))

    with pytest.raises(SystemExit):
        sweep_degeneracy.main([
            "../outside.csv", "--axis", AXIS, "--outputs", OUT,
        ])
