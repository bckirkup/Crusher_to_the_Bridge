"""Behaviour tests for the expedition posting readout.

Synthetic run archives written to ``tmp_path`` in the real layout
(``<run_id>/summary.json`` inside a ``*.zip`` under the results root) —
no simulator runs. Assertions are on the posting rule's OR structure, the
posting-conditioned distributions, the report-free branch, the Jeffreys
interval, cell keying, and zip flattening. No goldens: every expected
number is derived in the test.
"""

from __future__ import annotations

import json
import statistics
import zipfile
from pathlib import Path

import pytest

from telemetry_buffer.observation_model.expedition_posting_readout import (
    POSTING_THRESHOLD,
    build_report,
    collect_rows,
    jeffreys_interval,
    main,
    render_markdown,
    summarise_cell,
)


def _summary(
    run_id: str,
    *,
    pax_ar: float,
    crew_ar: float,
    sick_call: float = 0.1,
    dose: float = -4.0,
    epochs: int = 240,
    platform: str = "expedition_test",
    surveillance: str = "sentinel",
    vsp_epoch: int | None = None,
    peak_prevalence: float = 0.0,
) -> dict:
    return {
        "run_id": run_id,
        "parameters": {
            "tier_id": "t0",
            "platform_id": platform,
            "surveillance": surveillance,
            "dose_adjustment": dose,
            "num_epochs": epochs,
            "seed": 1,
            "sick_call_probability_per_day": sick_call,
        },
        "derived": {
            "peak_prevalence": peak_prevalence,
            "vsp_trigger_epoch": vsp_epoch,
            "reported_case_attack_rate_passenger": pax_ar,
            "reported_case_attack_rate_crew": crew_ar,
            "infection_attack_rate_passenger": pax_ar + 0.01,
            "ever_ill_attack_rate_passenger": pax_ar + 0.005,
        },
    }


def _write_zip(root: Path, name: str, summaries: list[dict]) -> Path:
    archive = root / name
    with zipfile.ZipFile(archive, "w") as zf:
        for summary in summaries:
            zf.writestr(
                f"{summary['run_id']}/summary.json",
                json.dumps(summary),
            )
    return archive


def _row(
    *,
    pax_ar: float,
    crew_ar: float,
    sick_call: float = 0.1,
    dose: float = -4.0,
    epochs: int = 240,
    platform: str = "expedition_test",
    surveillance: str = "sentinel",
    vsp_epoch: int | None = None,
    peak_prevalence: float = 0.0,
) -> dict:
    """One readout row, mirroring collect_rows output without a zip."""
    return {
        "run_id": "synthetic",
        "tier_id": "t0",
        "platform_id": platform,
        "surveillance": surveillance,
        "dose_adjustment": dose,
        "num_epochs": epochs,
        "seed": 1,
        "sick_call_probability_per_day": sick_call,
        "peak_prevalence": peak_prevalence,
        "vsp_trigger_epoch": vsp_epoch,
        "reported_case_attack_rate_passenger": pax_ar,
        "reported_case_attack_rate_crew": crew_ar,
        "infection_attack_rate_passenger": pax_ar + 0.01,
        "ever_ill_attack_rate_passenger": pax_ar + 0.005,
        "posted_passenger": pax_ar >= POSTING_THRESHOLD,
        "posted": (
            pax_ar >= POSTING_THRESHOLD or crew_ar >= POSTING_THRESHOLD
        ),
    }


class TestPostingRule:
    """The posting rule is an OR over the passenger and crew channels."""

    def test_crew_only_crossing_posts_but_not_on_the_passenger_channel(
        self, tmp_path: Path,
    ) -> None:
        _write_zip(
            tmp_path, "runs.zip",
            [_summary("r1", pax_ar=0.02, crew_ar=0.05)],
        )
        (row,) = collect_rows(tmp_path)
        assert row["posted"] is True
        assert row["posted_passenger"] is False

    def test_passenger_crossing_posts_on_both(self, tmp_path: Path) -> None:
        _write_zip(
            tmp_path, "runs.zip",
            [_summary("r1", pax_ar=0.031, crew_ar=0.0)],
        )
        (row,) = collect_rows(tmp_path)
        assert row["posted"] is True
        assert row["posted_passenger"] is True

    def test_threshold_is_inclusive(self, tmp_path: Path) -> None:
        _write_zip(
            tmp_path, "runs.zip",
            [_summary("r1", pax_ar=POSTING_THRESHOLD, crew_ar=0.0)],
        )
        (row,) = collect_rows(tmp_path)
        assert row["posted"] is True

    def test_just_below_threshold_on_both_channels_does_not_post(
        self, tmp_path: Path,
    ) -> None:
        _write_zip(
            tmp_path, "runs.zip",
            [_summary("r1", pax_ar=0.029, crew_ar=0.029)],
        )
        (row,) = collect_rows(tmp_path)
        assert row["posted"] is False


class TestConditionalDistribution:
    def test_conditioning_selects_the_posted_subset_only(self) -> None:
        posted_ars = [0.05, 0.07, 0.11]
        rows = [
            _row(pax_ar=ar, crew_ar=0.0) for ar in posted_ars
        ]
        rows += [
            _row(pax_ar=0.001, crew_ar=0.001),
            _row(pax_ar=0.002, crew_ar=0.002),
        ]
        cell = summarise_cell(rows)
        conditional = cell["conditional_on_posting"][
            "reported_case_attack_rate_passenger"
        ]
        assert cell["n_posted"] == 3
        assert conditional["n"] == 3
        assert conditional["median"] == pytest.approx(
            statistics.median(posted_ars),
        )
        # Crew-channel-only postings also enter the conditional set.
        rows_with_crew_post = rows + [
            _row(pax_ar=0.01, crew_ar=0.06),
        ]
        cell2 = summarise_cell(rows_with_crew_post)
        assert cell2["n_posted"] == 4
        assert cell2["conditional_on_posting"][
            "reported_case_attack_rate_passenger"
        ]["median"] == pytest.approx(statistics.median([*posted_ars, 0.01]))


class TestReportFreeBranch:
    def test_report_free_rows_emit_no_posting_frequency(self) -> None:
        rows = [
            _row(pax_ar=0.05, crew_ar=0.05, sick_call=0.0),
            _row(pax_ar=0.0, crew_ar=0.0, sick_call=0.0),
        ]
        cell = summarise_cell(rows)
        assert cell["report_free_branch"] is True
        assert cell["posting_frequency"] is None
        assert cell["posting_frequency_ci95"] is None
        conditional = cell["conditional_on_posting"][
            "reported_case_attack_rate_passenger"
        ]
        assert conditional["n"] == 1
        assert conditional["median"] == pytest.approx(0.05)


class TestJeffreysInterval:
    def test_zero_successes_bounds_are_small_and_valid(self) -> None:
        interval = jeffreys_interval(0, 100)
        assert interval is not None
        lo, hi = interval
        assert 0.0 <= lo < hi < 1.0
        assert hi < 0.1

    def test_half_of_trials_brackets_the_point_estimate(self) -> None:
        lo, hi = jeffreys_interval(50, 100)
        assert lo < 0.5 < hi
        assert hi - lo < 0.3


class TestCellKeying:
    def test_cells_never_pool_across_the_release_scale(self) -> None:
        rows = [
            _row(pax_ar=0.05, crew_ar=0.0, dose=-3.0),
            _row(pax_ar=0.05, crew_ar=0.0, dose=-4.0),
        ]
        report = build_report(rows, era="pre")
        assert report["n_cells"] == 2
        doses = sorted(
            cell["environmental_faecal_release_log10_g_per_epoch"]
            for cell in report["cells"]
        )
        assert doses == [-4.0, -3.0]
        for cell in report["cells"]:
            assert cell["n_voyages"] == 1
            assert cell["voyage_days"] == pytest.approx(10.0)


class TestCollectRows:
    def test_nested_run_summaries_are_flattened_from_zips(
        self, tmp_path: Path,
    ) -> None:
        _write_zip(
            tmp_path, "shard_a.zip",
            [_summary("run_a1", pax_ar=0.05, crew_ar=0.0)],
        )
        nested = tmp_path / "nested"
        nested.mkdir()
        _write_zip(
            nested, "shard_b.zip",
            [
                _summary("run_b1", pax_ar=0.0, crew_ar=0.0),
                _summary("run_b2", pax_ar=0.04, crew_ar=0.0),
            ],
        )
        rows = collect_rows(tmp_path)
        assert sorted(row["run_id"] for row in rows) == [
            "run_a1", "run_b1", "run_b2",
        ]


class TestRenderAndMain:
    """End-to-end: zips in, JSON report and markdown table out."""

    def test_render_markdown_emits_one_row_per_cell(self) -> None:
        report = build_report(
            [
                _row(pax_ar=0.05, crew_ar=0.0),
                _row(pax_ar=0.0, crew_ar=0.0),
            ],
            era="pre",
        )
        markdown = render_markdown(report)
        assert "| surveillance | release | days |" in markdown
        assert "| sentinel | -4.0 | 10.0 | 2 | 1 |" in markdown
        assert "P(post)" in markdown

    def test_render_markdown_carries_platform_per_row(self) -> None:
        report = build_report(
            [
                _row(pax_ar=0.05, crew_ar=0.0, platform="hull_a"),
                _row(pax_ar=0.05, crew_ar=0.0, platform="hull_b"),
            ],
            era="pre",
        )
        markdown = render_markdown(report)
        assert markdown.splitlines()[0] == (
            "# Posting frequency and posting-conditional attack rate"
        )
        assert "| platform | surveillance | release | days |" in markdown
        rows = [l for l in markdown.splitlines() if l.startswith("| hull_")]
        assert len(rows) == 2
        by_platform = {r.split("|")[1].strip(): r for r in rows}
        assert set(by_platform) == {"hull_a", "hull_b"}
        for platform, row in by_platform.items():
            assert row.startswith(f"| {platform} |")

    def test_main_writes_report_and_markdown(self, tmp_path: Path) -> None:
        _write_zip(
            tmp_path, "runs.zip",
            [
                _summary("r1", pax_ar=0.05, crew_ar=0.0),
                _summary("r2", pax_ar=0.01, crew_ar=0.0),
            ],
        )
        out = Path("telemetry_buffer/_test_expedition_readout.json")
        md = Path("telemetry_buffer/_test_expedition_readout.md")
        try:
            assert main([
                str(tmp_path), "--out", str(out), "--markdown", str(md),
            ]) == 0
            report = json.loads(
                (Path.cwd() / out).read_text(encoding="utf-8"),
            )
            assert report["n_cells"] == 1
            assert report["cells"][0]["posting_frequency"] == pytest.approx(0.5)
            text = (Path.cwd() / md).read_text(encoding="utf-8")
            assert "median pax AR" in text
        finally:
            (Path.cwd() / out).unlink(missing_ok=True)
            (Path.cwd() / md).unlink(missing_ok=True)
