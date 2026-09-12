"""The boarding posting readout's accounting, keying and spread measures.

The instrument's job is to separate imported infections from onward
transmission and to say how unevenly that transmission is spread across
voyages, so the tests here are about the accounting (an import is never
counted as transmission) and about graded response (a concentrated arm reads
as more concentrated than a spread arm carrying the same total), not about
golden numbers.
"""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from telemetry_buffer.observation_model.boarding_posting_readout import (
    _parse_arm,
    build_report,
    collect_rows,
    main,
    render_markdown,
)

PAX = 1000
CREW = 500


def _summary(
    run_id: str,
    infections_pax: int,
    *,
    reported_pax: int = 0,
    reported_crew: int = 0,
    prevalence: float = 0.0325,
    n_init: int | None = None,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "parameters": {
            "tier_id": "t",
            "platform_id": "classic_cruise_1900",
            "surveillance": "syndromic_comp65",
            "dose_adjustment": 4.0,
            "num_epochs": 168,
            "seed": 1,
            "boarding_passenger_prevalence": prevalence,
            "boarding_crew_prevalence": 0.0185,
            "presymptomatic_share_of_presenting": 0.04,
            "never_symptomatic_fraction": 0.29,
            "n_init": n_init,
        },
        "derived": {
            "reported_case_attack_rate_passenger": reported_pax / PAX,
            "reported_case_attack_rate_crew": reported_crew / CREW,
            "infection_attack_rate_passenger": infections_pax / PAX,
            "infection_attack_rate_crew": 0.0,
            "ever_ill_attack_rate_passenger": 0.0,
            "passenger_complement": PAX,
            "crew_complement": CREW,
            "peak_prevalence": infections_pax,
        },
    }


def _profile(drawn_pax: int, drawn_crew: int) -> dict[str, Any]:
    return {
        "initiation": {
            "mode": "boarding",
            "boarding": {
                "norwalk_gi": {
                    "drawn_by_role": {
                        "passenger": drawn_pax,
                        "crew": drawn_crew,
                    },
                    "composition": {
                        "never_symptomatic": drawn_pax,
                        "presymptomatic": drawn_crew,
                        "convalescent": 0,
                        "incubating": 0,
                    },
                },
            },
            "boarding_mode": {"norwalk_gi": "prevalence"},
        },
    }


def _archive(path: Path, runs: list[tuple[dict[str, Any], dict[str, Any] | None]]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for summary, profile in runs:
            prefix = summary["run_id"]
            archive.writestr(f"{prefix}/summary.json", json.dumps(summary))
            if profile is not None:
                archive.writestr(
                    f"{prefix}/resolved_pathogen_profiles.json",
                    json.dumps(profile),
                )


def _cells(tmp_path: Path, runs: list[Any], arm: str = "a") -> list[dict[str, Any]]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    _archive(tmp_path / "shard-0.zip", runs)
    rows = collect_rows(tmp_path, arm)
    return build_report(rows, "pre")["cells"]


def test_imports_are_not_counted_as_transmission(tmp_path: Path) -> None:
    """Secondary infections are infections net of the realised cohort."""
    runs = [(_summary("r0", 20), _profile(10, 2))]
    cell = _cells(tmp_path, runs)[0]
    assert cell["imports"]["mean_imported_total"] == 12
    assert cell["secondary_infection_spread"]["mean"] == 8


def test_fiat_arm_uses_the_declared_seed_count(tmp_path: Path) -> None:
    """With no boarding record the import count is the fiat n_init."""
    runs = [(_summary("r0", 20, n_init=1), None)]
    cell = _cells(tmp_path, runs)[0]
    assert cell["imports"]["mean_imported_total"] == 1
    assert cell["secondary_infection_spread"]["mean"] == 19


def test_boarding_coordinates_are_not_pooled(tmp_path: Path) -> None:
    """Two prevalence points are two cells, never one mixture."""
    runs = [
        (_summary("r0", 20, prevalence=0.025), _profile(8, 1)),
        (_summary("r1", 20, prevalence=0.040), _profile(14, 2)),
    ]
    cells = _cells(tmp_path, runs)
    assert len(cells) == 2
    assert {cell["boarding_passenger_prevalence"] for cell in cells} == {
        0.025, 0.040,
    }


def test_concentration_reads_higher_when_the_tail_carries_the_total(
    tmp_path: Path,
) -> None:
    """Same total transmission, graded response in every spread measure."""
    spread_runs = [
        (_summary(f"s{i}", 12, n_init=2), None) for i in range(10)
    ]
    tail_runs = [(_summary("t0", 102, n_init=2), None)] + [
        (_summary(f"t{i}", 2, n_init=2), None) for i in range(1, 10)
    ]
    spread_cell = _cells(tmp_path / "spread", spread_runs)[0]
    tail_cell = _cells(tmp_path / "tail", tail_runs)[0]
    assert spread_cell["secondary_infection_spread"]["mean"] == 10
    assert tail_cell["secondary_infection_spread"]["mean"] == 10
    tail = tail_cell["secondary_infection_spread"]
    even = spread_cell["secondary_infection_spread"]
    assert tail["top_10pct_share"] > even["top_10pct_share"]
    assert tail["variance_to_mean"] > even["variance_to_mean"]
    assert tail["fraction_zero"] > even["fraction_zero"]


def test_posting_channels_are_separated(tmp_path: Path) -> None:
    """A crew-only crossing posts on the or-rule but not on passengers."""
    runs = [
        (_summary("crew", 40, reported_crew=20), _profile(5, 1)),
        (_summary("pax", 40, reported_pax=40), _profile(5, 1)),
        (_summary("none", 40), _profile(5, 1)),
    ]
    cell = _cells(tmp_path, runs)[0]
    assert cell["n_posted"] == 2
    assert cell["n_posted_passenger_channel"] == 1
    assert cell["n_posted_crew_only"] == 1
    assert cell["posting_frequency"] == 2 / 3


def test_rates_and_shares_stay_in_bounds(tmp_path: Path) -> None:
    """Every reported rate, fraction and share is a proportion."""
    runs = [
        (_summary("r0", 40, reported_pax=35), _profile(6, 1)),
        (_summary("r1", 3), _profile(3, 0)),
        (_summary("r2", 0), _profile(0, 0)),
    ]
    cell = _cells(tmp_path, runs)[0]
    spread = cell["secondary_infection_spread"]
    low, high = cell["posting_frequency_ci95"]
    assert 0.0 <= low <= cell["posting_frequency"] <= high <= 1.0
    assert 0.0 <= spread["fraction_zero"] <= 1.0
    for fraction in (1, 10):
        share = spread[f"top_{fraction}pct_share"]
        assert share is None or 0.0 <= share <= 1.0
    assert spread["median"] <= spread["p90"] <= spread["p99"] <= spread["max"]


class TestRenderAndMain:
    """End-to-end: zips in, JSON report and markdown table out."""

    def test_render_markdown_emits_one_row_per_cell(
        self, tmp_path: Path,
    ) -> None:
        """Each cell becomes one table row under the report's own columns."""
        runs = [
            (_summary("quiet0", 3), _profile(3, 0)),
            (_summary("quiet1", 5), _profile(5, 0)),
        ]
        _archive(tmp_path / "shard-0.zip", runs)
        report = build_report(collect_rows(tmp_path, "boarding"), "pre")
        markdown = render_markdown(report)
        assert markdown.splitlines()[0] == (
            "# Introduction mechanism, posting frequency and "
            "between-voyage spread"
        )
        assert "| arm | platform | surv |" in markdown
        assert "median pax AR" in markdown
        rows = [
            line for line in markdown.splitlines()
            if line.startswith("| boarding |")
        ]
        assert len(rows) == 1
        assert "| classic_cruise_1900 |" in rows[0]
        # No voyage posted, so the posting-conditional median is n/a.
        assert "n/a" in rows[0]

    def test_main_writes_report_and_markdown(self, tmp_path: Path) -> None:
        """--arm name=root drives collection, writes JSON and markdown."""
        _archive(
            tmp_path / "shard-0.zip",
            [
                (_summary("r0", 40, reported_pax=35), _profile(6, 1)),
                (_summary("r1", 3), _profile(3, 0)),
            ],
        )
        out = Path("telemetry_buffer/_test_boarding_readout.json")
        md = Path("telemetry_buffer/_test_boarding_readout.md")
        try:
            assert main([
                f"--arm=boarding={tmp_path}",
                "--out", str(out), "--markdown", str(md),
            ]) == 0
            report = json.loads(
                (Path.cwd() / out).read_text(encoding="utf-8"),
            )
            assert report["n_cells"] == 1
            assert report["cells"][0]["arm"] == "boarding"
            assert report["cells"][0]["n_voyages"] == 2
            text = (Path.cwd() / md).read_text(encoding="utf-8")
            assert "median pax AR" in text
        finally:
            (Path.cwd() / out).unlink(missing_ok=True)
            (Path.cwd() / md).unlink(missing_ok=True)

    def test_main_errors_on_empty_results_root(self, tmp_path: Path) -> None:
        """An arm root with no run summaries is a CLI error, not a report."""
        with pytest.raises(SystemExit):
            main([
                f"--arm=boarding={tmp_path}",
                "--out", "telemetry_buffer/_never.json",
            ])

    def test_parse_arm_requires_a_name_equals_path(self) -> None:
        """`name=path` parses; anything else is an argument-type error."""
        name, path = _parse_arm("fiat=results/here")
        assert name == "fiat"
        assert path == Path("results/here")
        with pytest.raises(argparse.ArgumentTypeError):
            _parse_arm("no_separator_here")
