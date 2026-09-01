"""Behavioral tests for unconditional A8/A9 anchor scoring."""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path
from typing import Any

import pytest

from telemetry_buffer.observation_model import score_anchors

TARGETS = {
    "classic_cruise_1900": {
        "q1": 0.0418,
        "median": 0.0546,
        "q3": 0.0770,
        "n": 174.0,
    },
    "mega_cruise_5000": None,
}


def _row(
    *,
    hull: str = "classic_cruise_1900",
    strategy: str = "syndromic",
    reported_pax: float = 0.04,
    reported_crew: float = 0.02,
    num_agents: int = 2_000,
    voyage_days: float = 7.0,
    trigger_epoch: int | None = 10,
    passenger_complement: int | None = None,
    sick_call_probability: float = 1.0,
) -> dict[str, Any]:
    passenger_complement = (
        score_anchors.HULL_CAPACITY[hull]
        if passenger_complement is None
        else passenger_complement
    )
    return {
        "hull": hull,
        "strategy": strategy,
        "sick_call_probability": sick_call_probability,
        "took_off": True,
        "A1_ever_ill_passenger": 0.1,
        "infection_attack_rate_passenger": 0.1,
        "infection_attack_rate_crew": 0.1,
        "ever_ill_attack_rate_crew": 0.1,
        "A2_ill_per_infected": 1.0,
        "A3_reported_per_symptomatic": reported_pax / 0.1,
        "A5_passenger_crew_ratio": (
            reported_pax / reported_crew if reported_crew else None
        ),
        "reported_case_attack_rate_passenger": reported_pax,
        "reported_case_attack_rate_crew": reported_crew,
        "passenger_complement": passenger_complement,
        "crew_complement": num_agents - passenger_complement,
        "voyage_days": voyage_days,
        "vsp_trigger_epoch": trigger_epoch,
    }


def _summary(
    *,
    hull: str = "classic_cruise_1900",
    num_epochs: int = 168,
    num_agents: int = 2_000,
    clock: str = "hours",
    strategy: str = "syndromic",
    reported_pax: float = 0.04,
    reported_crew: float = 0.02,
    sick_call_probability: float = 1.0,
) -> dict[str, Any]:
    return {
        "run_id": "test-run",
        "parameters": {
            "platform_id": hull,
            "surveillance": strategy,
            "dose_adjustment": 1.0,
            "seed": 1,
            "num_epochs": num_epochs,
            "num_agents": num_agents,
            "natural_history_clock": clock,
            "sick_call_probability": sick_call_probability,
        },
        "derived": {
            "peak_prevalence": 20,
            "ever_ill_attack_rate_passenger": 0.1,
            "infection_attack_rate_passenger": 0.1,
            "reported_case_attack_rate_passenger": reported_pax,
            "infection_attack_rate_crew": 0.1,
            "reported_case_attack_rate_crew": reported_crew,
            "ever_ill_attack_rate_crew": 0.1,
            "vsp_trigger_epoch": 10,
        },
        "summary": {
            "cumulative_ever_infected_passenger": 190,
            "infection_attack_rate_passenger": 0.1,
            "cumulative_ever_infected_crew": 10,
            "infection_attack_rate_crew": 0.1,
        },
    }


def _write_run(root: Path, summary: dict[str, Any], name: str = "run.zip") -> Path:
    path = root / name
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("summary.json", json.dumps(summary))
    return path


def _write_legacy_run(
    root: Path,
    name: str,
    *,
    peak_prevalence: int,
    reported_crew: float = 0.02,
) -> None:
    _write_run(
        root,
        _summary(
            num_epochs=168,
            reported_pax=0.06,
            reported_crew=reported_crew,
        )
        | {
            "run_id": name,
            "derived": _summary()["derived"]
            | {
                "peak_prevalence": peak_prevalence,
                "reported_case_attack_rate_passenger": 0.06,
                "reported_case_attack_rate_crew": reported_crew,
            },
        },
        f"{name}.zip",
    )


def test_read_rows_requires_parameters_and_resolves_legacy_days(tmp_path: Path) -> None:
    path = _write_run(
        tmp_path,
        _summary(num_epochs=168, clock="legacy_epoch_day"),
    )

    row = score_anchors.read_rows(tmp_path)[0]

    assert row["hours_per_epoch"] == pytest.approx(24.0)
    assert row["voyage_days"] == pytest.approx(168.0)
    assert row["passenger_complement"] == 1900
    assert row["crew_complement"] == 100
    assert path.name == "run.zip"
    cell = score_anchors.summarise_cell([row])
    assert cell["A9_eligible_runs"] == 0
    assert cell["A9_ineligible_runs"] == 1


def test_read_rows_rejects_missing_duration_parameters(tmp_path: Path) -> None:
    summary = _summary()
    del summary["parameters"]["num_epochs"]
    _write_run(tmp_path, summary)

    with pytest.raises(RuntimeError, match="run.zip.*num_epochs"):
        score_anchors.read_rows(tmp_path)


def test_a4_target_lines_include_target_and_insufficient_branches() -> None:
    lines = score_anchors._a4_target_lines("pre", TARGETS)
    header = "\n".join(lines)

    assert "`pre` era" in header
    assert "classic_cruise_1900" in header
    assert "174" in header
    assert "mega_cruise_5000" in header
    assert "n/a (insufficient VSP postings)" in header


def test_render_scores_targeted_and_withheld_hulls() -> None:
    cell = score_anchors.summarise_cell([_row()])
    report = score_anchors.render(
        {
            ("classic_cruise_1900", "syndromic", 1.0): cell,
            ("mega_cruise_5000", "syndromic", 1.0): cell,
        },
        "pre",
        TARGETS,
    )

    assert "`pre` era" in report
    assert "n/a (insufficient VSP postings)" in report
    assert "| classic_cruise_1900 | syndromic |" in report
    assert "| mega_cruise_5000 | syndromic |" in report


def test_read_rows_and_summarise_cell_preserve_run_and_ratio_metrics(
    tmp_path: Path,
) -> None:
    _write_legacy_run(tmp_path, "takeoff", peak_prevalence=10, reported_crew=0.0)
    _write_legacy_run(tmp_path, "no_takeoff", peak_prevalence=9)

    rows = score_anchors.read_rows(tmp_path)
    cell = score_anchors.summarise_cell(rows)

    assert len(rows) == 2
    assert cell["n_seeds"] == 2
    assert cell["n_takeoff"] == 1
    assert cell["takeoff_fraction"] == pytest.approx(0.5)
    assert cell["A1_ever_ill_passenger"] == pytest.approx(0.1)
    assert cell["A2_ill_per_infected__per_seed_median"] == pytest.approx(1.0)
    assert cell["A5_passenger_crew_ratio__n_undefined"] == 1


def test_main_reads_runs_and_writes_the_complete_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_legacy_run(tmp_path, "takeoff", peak_prevalence=10)
    output = tmp_path / "report.md"
    monkeypatch.setattr(
        sys,
        "argv",
        ["score_anchors.py", str(tmp_path), "--out", str(output)],
    )

    assert score_anchors.main() == 0

    report = output.read_text(encoding="utf-8")
    companion = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
    assert "Literature anchor scoring" in report
    assert "`pre` era" in report
    assert companion["rows"][0]["run_id"] == "takeoff"
    assert "Literature anchor scoring" in capsys.readouterr().out


def test_verdicts_score_numeric_unconditional_channels() -> None:
    cell = score_anchors.summarise_cell([_row()])
    verdict, ratios = score_anchors.verdicts(
        "classic_cruise_1900", cell, TARGETS
    )

    assert verdict["A8"] == "FAIL"
    assert verdict["A9"] == "FAIL"
    assert ratios["A8_pax_ratio_to_end_of_period"] > 1.0
    assert ratios["A9_ratio_to_investigated"] > 1.0
    assert "A8_pax_ratio_to_end_of_period" not in cell


def test_verdicts_report_unknown_hull_and_no_eligible_runs() -> None:
    no_eligible = score_anchors.summarise_cell(
        [_row(voyage_days=2.9, passenger_complement=1900)]
    )
    verdict, _ = score_anchors.verdicts(
        "classic_cruise_1900", no_eligible, TARGETS
    )
    assert verdict["A9"] == "n/a (no eligible runs)"

    unknown, _ = score_anchors.verdicts(
        "unknown_hull",
        no_eligible,
        TARGETS,
    )
    assert unknown["A8"] == "n/a (unknown hull)"


def test_a9_reports_passenger_trigger_disagreements() -> None:
    row = _row(reported_pax=0.02, trigger_epoch=10)

    cell = score_anchors.summarise_cell([row])

    assert cell["A9_flag_disagreements"] == 1
    assert score_anchors.summarise_cell(
        [_row(reported_pax=0.03, trigger_epoch=None)],
    )["A9_flag_disagreements"] == 1



def test_a8_uses_travel_day_weighting_for_heterogeneous_cell() -> None:
    first = _row(
        reported_pax=0.03,
        reported_crew=0.03,
        num_agents=2_000,
        voyage_days=3.0,
    )
    second = _row(
        reported_pax=0.12,
        reported_crew=0.12,
        num_agents=2_500,
        voyage_days=6.0,
    )

    cell = score_anchors.summarise_cell([first, second])

    expected_pax = 1e5 * (0.03 * 1900 + 0.12 * 1900) / (1900 * 3 + 1900 * 6)
    expected_crew = 1e5 * (0.03 * 100 + 0.12 * 600) / (100 * 3 + 600 * 6)
    assert cell["A8_pax_incidence"] == pytest.approx(expected_pax)
    assert cell["A8_crew_incidence"] == pytest.approx(expected_crew)
    unweighted_pax = (1e5 * 0.03 / 3.0 + 1e5 * 0.12 / 6.0) / 2
    assert cell["A8_pax_incidence"] != pytest.approx(unweighted_pax)


@pytest.mark.parametrize(
    ("reported_pax", "reported_crew", "expected_posted"),
    [(0.0299, 0.0, 0), (0.0300, 0.0, 1), (0.0, 0.0300, 1)],
)
def test_a9_posting_threshold_uses_passenger_or_crew(
    reported_pax: float,
    reported_crew: float,
    expected_posted: int,
) -> None:
    row = _row(
        reported_pax=reported_pax,
        reported_crew=reported_crew,
        voyage_days=3.0,
    )

    cell = score_anchors.summarise_cell([row])

    assert cell["A9_posted_eligible"] == expected_posted


@pytest.mark.parametrize(
    ("complement", "days", "eligible"),
    [
        (99, 3.0, False),
        (100, 3.0, True),
        (1900, 2.9, False),
        (1900, 3.0, True),
        (1900, 21.0, True),
        (1900, 21.1, False),
    ],
)
def test_a9_eligibility_boundaries(
    complement: int,
    days: float,
    eligible: bool,
) -> None:
    row = _row(
        hull="expedition_cruise_450",
        num_agents=450 + complement,
        passenger_complement=complement,
        voyage_days=days,
    )

    cell = score_anchors.summarise_cell([row])

    assert cell["A9_eligible_runs"] == int(eligible)
    assert cell["A9_ineligible_runs"] == int(not eligible)


def test_truth_only_arm_has_explicit_no_reporting_sentinel() -> None:
    row = _row(
        strategy="none_true",
        reported_pax=0.0,
        reported_crew=0.0,
        sick_call_probability=0.0,
    )

    cell = score_anchors.summarise_cell([row])

    assert cell["A8_pax_incidence"] == score_anchors.A8_A9_NO_REPORTING
    assert cell["A8_crew_incidence"] == score_anchors.A8_A9_NO_REPORTING
    assert cell["A9_posting_probability"] == score_anchors.A8_A9_NO_REPORTING
    verdict, _ = score_anchors.verdicts(
        "classic_cruise_1900",
        cell,
        score_anchors.vsp_attack_rate_targets("pre"),
    )
    assert verdict["A8"].startswith("n/a")
    assert "sick_call_probability = 0" in verdict["A8"]


@pytest.mark.parametrize("strategy", ["none", "none_env", "none_true"])
def test_no_reporting_sentinel_uses_sick_call_mechanism(
    strategy: str,
) -> None:
    cell = score_anchors.summarise_cell(
        [_row(
            strategy=strategy,
            reported_pax=0.0,
            reported_crew=0.0,
            sick_call_probability=0.0,
        )]
    )

    assert cell["A8_pax_incidence"] == score_anchors.A8_A9_NO_REPORTING


def test_reporting_cell_with_zero_outcomes_is_numeric_zero_and_fails() -> None:
    cell = score_anchors.summarise_cell(
        [_row(reported_pax=0.0, reported_crew=0.0)]
    )

    assert cell["A8_pax_incidence"] == pytest.approx(0.0)
    assert cell["A8_crew_incidence"] == pytest.approx(0.0)
    verdict, _ = score_anchors.verdicts(
        "classic_cruise_1900",
        cell,
        score_anchors.vsp_attack_rate_targets("pre"),
    )
    assert verdict["A8"] == "FAIL"
    assert verdict["A9"] == "FAIL"


def test_tiny_positive_reporting_probability_is_not_report_free() -> None:
    cell = score_anchors.summarise_cell(
        [_row(
            reported_pax=0.0,
            reported_crew=0.0,
            sick_call_probability=1e-9,
        )]
    )

    assert cell["A8_pax_incidence"] == pytest.approx(0.0)
    assert cell["A8_A9_no_reporting"] is False
    verdict, _ = score_anchors.verdicts(
        "classic_cruise_1900",
        cell,
        score_anchors.vsp_attack_rate_targets("pre"),
    )
    assert verdict["A8"] == "FAIL"


def test_negative_reporting_probability_is_rejected() -> None:
    row = _row(sick_call_probability=-1e-9)

    with pytest.raises(RuntimeError, match="negative sick_call_probability"):
        score_anchors.summarise_cell([row])


def test_mixed_reporting_mechanisms_are_rejected() -> None:
    rows = [
        _row(sick_call_probability=0.0),
        _row(sick_call_probability=1.0),
    ]
    with pytest.raises(RuntimeError, match="mixes report-free"):
        score_anchors.summarise_cell(rows)


def test_missing_sick_call_probability_names_archive() -> None:
    summary = _summary()
    del summary["parameters"]["sick_call_probability"]

    with pytest.raises(RuntimeError, match="missing.zip"):
        score_anchors._read_row(summary, "missing.zip")


def test_expedition_a8_plausibility_band_accepts_inverted_endpoints() -> None:
    target = score_anchors.a8_targets("expedition_cruise_450", "pre")
    assert target is not None
    assert target["passenger"] == {
        "end_of_period": 16.9,
        "pooled_band": 10.9,
    }
    cell = {
        "A8_A9_no_reporting": False,
        "A8_pax_incidence": 13.0,
        "A8_crew_incidence": 5.8,
        "A9_posting_probability": 0.0,
    }

    verdict, ratios = score_anchors.verdicts(
        "expedition_cruise_450",
        cell,
        score_anchors.vsp_attack_rate_targets("pre"),
    )

    assert verdict["A8"] == "PASS"
    assert ratios["A8_pax_ratio_to_end_of_period"] == pytest.approx(
        13.0 / 16.9
    )
    assert ratios["A8_pax_ratio_to_pooled_band"] == pytest.approx(
        13.0 / 10.9
    )
    assert "A8_pax_ratio_to_end_of_period" not in cell


def test_render_reports_unconditional_channels_and_post_arm() -> None:
    targets = score_anchors.vsp_attack_rate_targets("pre")
    cell = score_anchors.summarise_cell([_row()])

    report = score_anchors.render(
        {("classic_cruise_1900", "syndromic", 1.0): cell},
        "post",
        targets,
    )

    assert "A4 and A7 are conditional on posting" in report
    assert "post arm has no observation" in report
    assert "A8 pax/crew per 100k-days" in report


def test_write_report_writes_markdown_and_json(tmp_path: Path) -> None:
    output = tmp_path / "report.md"
    rows = [_row()]
    cells = {("classic_cruise_1900", "syndromic", 1.0): score_anchors.summarise_cell(rows)}

    score_anchors._write_report(output, "report\n", rows, cells, tmp_path)

    assert output.read_text(encoding="utf-8") == "report\n"
    assert output.with_suffix(".json").is_file()


def test_write_report_rejects_path_outside_root(tmp_path: Path) -> None:
    outside = tmp_path.parent / "report.md"

    with pytest.raises(ValueError, match="results_root"):
        score_anchors._write_report(outside, "report\n", [], {}, tmp_path)


def test_legacy_complement_recovery_accepts_six_digit_rate_rounding() -> None:
    summary = {
        "summary": {
            "cumulative_ever_infected_passenger": 1,
            "infection_attack_rate_passenger": 0.333333,
            "cumulative_ever_infected_crew": 1,
            "infection_attack_rate_crew": 0.5,
        },
    }

    assert score_anchors._resolve_complements(summary, 5, "legacy.zip") == (3, 2)


def test_legacy_complement_recovery_rejects_invalid_pairs() -> None:
    summary = {
        "summary": {
            "cumulative_ever_infected_passenger": 1,
            "infection_attack_rate_passenger": 0.333333,
            "cumulative_ever_infected_crew": 2,
            "infection_attack_rate_crew": 0.666667,
        },
    }

    with pytest.raises(RuntimeError, match="unrecoverable"):
        score_anchors._resolve_complements(summary, 4, "legacy.zip")
    with pytest.raises(RuntimeError, match="unrecoverable"):
        score_anchors._resolve_complements(
            {"summary": {
                "cumulative_ever_infected_passenger": 0,
                "infection_attack_rate_passenger": 0.0,
                "cumulative_ever_infected_crew": 0,
                "infection_attack_rate_crew": 0.0,
            }},
            3,
            "zero.zip",
        )


def test_explicit_complements_are_preferred_and_checked_against_recovery() -> None:
    summary = _summary() | {
        "derived": _summary()["derived"] | {
            "passenger_complement": 1900,
            "crew_complement": 100,
        },
    }

    assert score_anchors._resolve_complements(summary, 2000, "run.zip") == (
        1900,
        100,
    )
    summary["derived"]["passenger_complement"] = 1800
    summary["derived"]["crew_complement"] = 200
    with pytest.raises(RuntimeError, match="disagree"):
        score_anchors._resolve_complements(summary, 2000, "run.zip")
    summary["derived"]["crew_complement"] = 99
    with pytest.raises(RuntimeError, match="do not sum"):
        score_anchors._resolve_complements(summary, 2000, "run.zip")


def test_read_rows_collapses_nested_aggregate_duplicates(tmp_path: Path) -> None:
    first = _summary() | {"run_id": "first"}
    second = _summary() | {"run_id": "second"}
    per_run = tmp_path / "per_run"
    combined = tmp_path / "combined"
    per_run.mkdir()
    combined.mkdir()
    _write_run(per_run, first, "first.zip")
    _write_run(per_run, second, "second.zip")
    _write_run(combined, first, "first.zip")
    _write_run(combined, second, "second.zip")
    with zipfile.ZipFile(combined / "single.zip", "w") as archive:
        archive.writestr("first/summary.json", json.dumps(first))
        archive.writestr("second/summary.json", json.dumps(second))
    stats: dict[str, Any] = {}

    rows = score_anchors.read_rows(combined, stats)

    assert {row["run_id"] for row in rows} == {"first", "second"}
    assert stats == {
        "archives_read": 3,
        "duplicates_collapsed": 2,
        "runs_with_recovered_complements": 2,
        "runs_with_explicit_complements": 0,
        "skipped_archives": [],
        "runs_kept": 2,
    }
    assert score_anchors.summarise_cell(rows) == score_anchors.summarise_cell(
        score_anchors.read_rows(per_run),
    )


def test_read_rows_rejects_conflicting_duplicate_and_reports_skips(
    tmp_path: Path,
) -> None:
    first = _summary() | {"run_id": "first"}
    conflicting = first | {
        "derived": first["derived"] | {
            "reported_case_attack_rate_passenger": 0.07,
        },
    }
    _write_run(tmp_path, first, "first.zip")
    with zipfile.ZipFile(tmp_path / "aggregate.zip", "w") as archive:
        archive.writestr("first/summary.json", json.dumps(conflicting))
    with zipfile.ZipFile(tmp_path / "empty.zip", "w") as archive:
        archive.writestr("run_spec.json", "{}")

    with pytest.raises(RuntimeError, match="conflicting duplicate.*first"):
        score_anchors.read_rows(tmp_path)

    (tmp_path / "aggregate.zip").unlink()
    stats: dict[str, Any] = {}
    rows = score_anchors.read_rows(tmp_path, stats)
    assert len(rows) == 1
    assert stats["skipped_archives"] == [str(tmp_path / "empty.zip")]
