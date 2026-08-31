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
) -> dict[str, Any]:
    passenger_complement = (
        score_anchors.HULL_CAPACITY[hull]
        if passenger_complement is None
        else passenger_complement
    )
    return {
        "hull": hull,
        "strategy": strategy,
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
    verdict = score_anchors.verdicts("classic_cruise_1900", cell, TARGETS)

    assert verdict["A8"] == "FAIL"
    assert verdict["A9"] == "FAIL"
    assert cell["A8_pax_ratio_to_end"] > 1.0
    assert cell["A9_ratio_to_investigated"] > 1.0


def test_verdicts_report_unknown_hull_and_no_eligible_runs() -> None:
    no_eligible = score_anchors.summarise_cell(
        [_row(voyage_days=2.9, passenger_complement=1900)]
    )
    verdict = score_anchors.verdicts("classic_cruise_1900", no_eligible, TARGETS)
    assert verdict["A9"] == "n/a (no eligible runs)"

    unknown = score_anchors.verdicts(
        "unknown_hull",
        no_eligible,
        TARGETS,
    )
    assert unknown["A8"] == "n/a (unknown hull)"


def test_a9_reports_passenger_trigger_disagreements() -> None:
    row = _row(reported_pax=0.02, trigger_epoch=10)

    cell = score_anchors.summarise_cell([row])

    assert cell["A9_flag_disagreements"] == 1



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
    )

    cell = score_anchors.summarise_cell([row])

    assert cell["A8_pax_incidence"] == score_anchors.A8_A9_NO_REPORTING
    assert cell["A8_crew_incidence"] == score_anchors.A8_A9_NO_REPORTING
    assert cell["A9_posting_probability"] == score_anchors.A8_A9_NO_REPORTING
    verdict = score_anchors.verdicts(
        "classic_cruise_1900",
        cell,
        score_anchors.vsp_attack_rate_targets("pre"),
    )
    assert verdict["A8"].startswith("n/a")
    assert "no reporting" in verdict["A8"]


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
