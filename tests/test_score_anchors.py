"""Tests for the VSP-aware report paths in ``score_anchors.py``."""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

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


def _cells() -> dict[tuple[str, str, float], dict[str, float]]:
    return {
        ("classic_cruise_1900", "syndromic", 1.0): {
            "n_takeoff": 1,
            "n_seeds": 1,
            "reported_case_attack_rate_passenger": 0.05,
        },
        ("mega_cruise_5000", "syndromic", 1.0): {
            "n_takeoff": 1,
            "n_seeds": 1,
            "reported_case_attack_rate_passenger": 0.05,
        },
    }


def _write_run(
    root: Path,
    name: str,
    *,
    peak_prevalence: int,
    reported_crew: float = 0.02,
) -> None:
    summary = {
        "run_id": name,
        "parameters": {
            "platform_id": "classic_cruise_1900",
            "surveillance": "syndromic",
            "dose_adjustment": 1.0,
            "seed": 1,
        },
        "derived": {
            "peak_prevalence": peak_prevalence,
            "ever_ill_attack_rate_passenger": 0.15,
            "infection_attack_rate_passenger": 0.2,
            "infection_attack_rate_crew": 0.05,
            "reported_case_attack_rate_passenger": 0.06,
            "reported_case_attack_rate_crew": reported_crew,
            "ever_ill_attack_rate_crew": 0.04,
        },
    }
    with zipfile.ZipFile(root / f"{name}.zip", "w") as archive:
        archive.writestr("summary.json", json.dumps(summary))


def test_a4_target_lines_include_target_and_insufficient_branches() -> None:
    """The header identifies era, sample size, and withheld mega target."""
    lines = score_anchors._a4_target_lines("pre", TARGETS)
    header = "\n".join(lines)

    assert "`pre` era" in header
    assert "| classic_cruise_1900 | 0.0418-0.0770 (median 0.0546) | 174 |" in header
    assert "mega_cruise_5000" in header
    assert "n/a (insufficient VSP postings)" in header


def test_render_scores_targeted_and_withheld_hulls() -> None:
    """Rendering exercises both A4 target branches and their verdict output."""
    report = score_anchors.render(_cells(), "pre", TARGETS)

    assert "`pre` era" in report
    assert "| classic_cruise_1900 | 0.0418-0.0770 (median 0.0546) | 174 |" in report
    assert "n/a (insufficient VSP postings)" in report
    assert "| classic_cruise_1900 | syndromic |" in report
    assert "| mega_cruise_5000 | syndromic |" in report


def test_read_rows_and_summarise_cell_preserve_run_and_ratio_metrics(
    tmp_path: Path,
) -> None:
    """Run ZIPs become one cell with takeoff and undefined-ratio counts."""
    _write_run(tmp_path, "takeoff", peak_prevalence=10, reported_crew=0.0)
    _write_run(tmp_path, "no_takeoff", peak_prevalence=9)

    rows = score_anchors.read_rows(tmp_path)
    cell = score_anchors.summarise_cell(rows)

    assert len(rows) == 2
    assert cell["n_seeds"] == 2
    assert cell["n_takeoff"] == 1
    assert cell["takeoff_fraction"] == pytest.approx(0.5)
    assert cell["A1_ever_ill_passenger"] == pytest.approx(0.15)
    assert cell["A2_ill_per_infected__per_seed_median"] == pytest.approx(0.75)
    assert cell["A5_passenger_crew_ratio__n_undefined"] == 1


def test_main_reads_runs_and_writes_the_complete_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI groups run ZIPs, renders verdicts, and writes both artifacts."""
    _write_run(tmp_path, "takeoff", peak_prevalence=10)
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


def test_write_report_writes_markdown_and_json_companions(tmp_path: Path) -> None:
    """Both report artifacts are written under the caller's validated root."""
    output = tmp_path / "report.md"

    score_anchors._write_report(
        output,
        "# report\n",
        [{"run_id": "one"}],
        {},
        tmp_path,
    )

    assert output.read_text(encoding="utf-8") == "# report\n"
    companion = output.with_suffix(".json")
    assert json.loads(companion.read_text(encoding="utf-8")) == {
        "rows": [{"run_id": "one"}],
        "cells": {},
    }


def test_write_report_rejects_output_outside_results_root(tmp_path: Path) -> None:
    """The write-site guard rejects a path that escapes the results root."""
    with pytest.raises(ValueError, match="report path must be inside results_root"):
        score_anchors._write_report(
            tmp_path.parent / "outside.md",
            "# report\n",
            [],
            {},
            tmp_path,
        )
