"""Coverage for the HTML and Markdown analysis report builder."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from picard_framework.analysis import report


def test_read_csv_rows_round_trips_a_small_csv(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "rows.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["run_id", "value"])
        writer.writeheader()
        writer.writerow({"run_id": "a", "value": "0.2"})

    rows = report._read_csv_rows(str(path))

    assert rows == [{"run_id": "a", "value": "0.2"}]


def test_table_html_honours_limit_and_column_subset() -> None:
    rows = [
        {"run_id": "a", "value": "one", "ignored": "x"},
        {"run_id": "b", "value": "two", "ignored": "y"},
    ]

    html = report._table_html(rows, columns=["run_id", "value"], limit=1)

    assert "<th>run_id</th>" in html
    assert "<th>value</th>" in html
    assert "ignored" not in html
    assert "<td>a</td>" in html
    assert "<td>b</td>" not in html
    assert "Showing 1 of 2 rows." in html


def test_img_tag_only_references_existing_images(tmp_path: Path) -> None:
    image = tmp_path / "figures" / "dose_response.png"
    image.parent.mkdir()
    image.write_bytes(b"png")

    found = report._img_tag(str(tmp_path), "figures/dose_response.png")
    missing = report._img_tag(str(tmp_path), "figures/missing.png")

    assert found == '<img src="figures/dose_response.png" alt="figures/dose_response.png" />'
    assert missing == ""


def test_build_report_references_tables_and_images(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    analysis = tmp_path / "analysis"
    figures = analysis / "figures"
    figures.mkdir(parents=True)
    (analysis / "aggregate_metrics.json").write_text(
        json.dumps({"n_runs": 2, "mean_attack_rate": 0.3, "outbreak_rate": 0.5}),
        encoding="utf-8",
    )
    (analysis / "run_summary.csv").write_text(
        "run_id,platform_id,pathogen,attack_rate\n"
        "a,mega_cruise_5000,norovirus,0.2\n"
        "b,expedition_cruise_450,norovirus,0.4\n",
        encoding="utf-8",
    )
    (analysis / "pairwise_deltas.csv").write_text(
        "run_id,delta\n"
        "a,0.1\n",
        encoding="utf-8",
    )
    (figures / "dose_response.png").write_bytes(b"png")

    output = report.build_report(str(analysis), out_path=str(tmp_path / "report.html"))

    assert output == str(tmp_path / "report.html")
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    markdown = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "Campaign Analysis Report" in html
    assert "mega_cruise_5000" in html
    assert "figures/dose_response.png" in html
    assert "Pairwise deltas" in html
    assert "Runs: 2" in markdown
