"""Per-class, per-era VSP scoring targets.

Locks the derivation behind A4's targets, which replaced the unprovenanced
``VSP_TARGETS`` triples in ``score_anchors.py``.  The regression locks here are
labelled change-detectors: they exist so a target cannot move without the diff
that moved it saying so.  Design and provenance:
`telemetry_buffer/observation_model/incidence_and_attack_rate_scoring_spec.md`.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path
from types import ModuleType

import pytest

from telemetry_buffer.observation_model import score_anchors

HARNESS = (
    Path(__file__).resolve().parents[1]
    / "telemetry_buffer"
    / "observation_model"
    / "vsp_class_era_scoring.py"
)

SERIES_HEADER = (
    "year,cruise_line,ship,voyage_dates_raw,voyage_end,causative_agent,"
    "pax_ill,pax_total,pax_pct_page,crew_ill,crew_total,crew_pct_page,era,"
    "counts_published,source_url,retrieved"
)

# Postings per (hull, era) in the shipped series, at the extraction recorded in
# `vsp_outbreak_series_extraction_log.md`. Change-detector: a move means the
# series was re-extracted, and every A4 target moved with it.
EXPECTED_COUNTS = {
    ("expedition_cruise_450", "pre"): 34,
    ("expedition_cruise_450", "post"): 18,
    ("classic_cruise_1900", "pre"): 174,
    ("classic_cruise_1900", "post"): 32,
    ("spirit_cruise_3000", "pre"): 50,
    ("spirit_cruise_3000", "post"): 13,
    ("mega_cruise_5000", "pre"): 4,
    ("mega_cruise_5000", "post"): 3,
}

# The one hull-era cell whose quantiles are pinned outright: the classic pre
# arm carries 174 postings, so it is the least noise-sensitive of the eight.
CLASSIC_PRE_Q1 = 0.0418
CLASSIC_PRE_MEDIAN = 0.0546
CLASSIC_PRE_Q3 = 0.0770
QUANTILE_TOLERANCE = 5e-5


def _load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("vsp_class_era_scoring", HARNESS)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # `NamedTuple` resolves annotations through `sys.modules`, so the module
    # has to be registered before its body runs.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


scoring = _load_harness()


def _row(
    *,
    year: int = 2015,
    era: str = "pre",
    pax_ill: str = "10",
    pax_total: str = "1000",
    crew_ill: str = "2",
    crew_total: str = "400",
) -> str:
    return (
        f"{year},Line,Ship,dates,{year}-01-01,norovirus,{pax_ill},{pax_total},"
        f"1.0,{crew_ill},{crew_total},0.5,{era},full,https://example.invalid,"
        "2026-08-30"
    )


def _series(tmp_path: Path, rows: list[str]) -> Path:
    path = tmp_path / "series.csv"
    path.write_text("\n".join([SERIES_HEADER, *rows]) + "\n", encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("pax_total", "expected"),
    [
        (924.0, "expedition_cruise_450"),
        (925.0, "classic_cruise_1900"),
        (2386.0, "classic_cruise_1900"),
        (2387.0, "spirit_cruise_3000"),
        (3872.0, "spirit_cruise_3000"),
        (3873.0, "mega_cruise_5000"),
        (6364.0, "mega_cruise_5000"),
    ],
)
def test_capacity_band_edges(pax_total: float, expected: str) -> None:
    """Each band edge is closed below and open above, with no gap at the top."""
    assert scoring._capacity_band(pax_total) == expected


def test_load_postings_drops_rows_without_a_passenger_denominator(
    tmp_path: Path,
) -> None:
    """A posting with no usable passenger denominator cannot carry a rate."""
    path = _series(
        tmp_path,
        [
            _row(pax_total=""),
            _row(pax_ill=""),
            _row(pax_total="0"),
            _row(pax_ill="50", pax_total="1000"),
        ],
    )

    postings = scoring.load_postings(path)

    assert len(postings) == 1
    assert postings[0].pax_rate == pytest.approx(0.05)


@pytest.mark.parametrize("crew_total", ["", "0"])
def test_load_postings_crew_rate_is_none_without_a_crew_denominator(
    tmp_path: Path,
    crew_total: str,
) -> None:
    """A missing or zero crew complement yields no crew rate, not a zero one."""
    path = _series(tmp_path, [_row(crew_total=crew_total)])

    assert scoring.load_postings(path)[0].crew_rate is None


def test_load_postings_crew_rate_present_with_a_denominator(tmp_path: Path) -> None:
    """A crew denominator gives the crew rate its own value."""
    path = _series(tmp_path, [_row(crew_ill="20", crew_total="400")])

    assert scoring.load_postings(path)[0].crew_rate == pytest.approx(0.05)


@pytest.mark.parametrize("count", [0, 1, 2, 3])
def test_quantiles_declines_fewer_than_four_values(count: int) -> None:
    """Three points cannot bracket an interquartile range."""
    assert scoring.quantiles([1.0] * count) is None


def test_quantiles_interpolate_linearly() -> None:
    """Quartiles interpolate between order statistics, as numpy's default does."""
    result = scoring.quantiles([1.0, 2.0, 3.0, 4.0])

    assert result is not None
    assert result["q1"] == pytest.approx(1.75)
    assert result["median"] == pytest.approx(2.5)
    assert result["q3"] == pytest.approx(3.25)


def test_quantiles_are_monotone_in_the_input() -> None:
    """Shifting every value up shifts every quantile up by the same amount."""
    base = scoring.quantiles([1.0, 2.0, 3.0, 4.0, 9.0])
    shifted = scoring.quantiles([3.0, 4.0, 5.0, 6.0, 11.0])

    assert base is not None
    assert shifted is not None
    for key in ("q1", "median", "q3"):
        assert shifted[key] == pytest.approx(base[key] + 2.0)


def test_era_year_spans_counts_inclusive_calendar_years(tmp_path: Path) -> None:
    """The span is read from the series, so a re-extraction cannot go stale."""
    path = _series(
        tmp_path,
        [
            _row(year=2006, era="pre"),
            _row(year=2019, era="pre"),
            _row(year=2012, era="pre"),
            _row(year=2022, era="post"),
            _row(year=2024, era="post"),
        ],
    )

    spans = scoring.era_year_spans(scoring.load_postings(path))

    assert spans["pre"] == 14
    assert spans["post"] == 3


@pytest.mark.parametrize(("key", "expected"), sorted(EXPECTED_COUNTS.items()))
def test_shipped_series_posting_counts(key: tuple[str, str], expected: int) -> None:
    """Change-detector on the postings behind every A4 target."""
    cells = scoring.targets_by_class_era(scoring.load_postings())

    assert cells[key]["n"] == expected


def test_shipped_series_classic_pre_quantiles() -> None:
    """Change-detector on the one cell whose target values are pinned."""
    cell = scoring.targets_by_class_era(scoring.load_postings())[
        ("classic_cruise_1900", "pre")
    ]

    assert cell["q1"] == pytest.approx(CLASSIC_PRE_Q1, abs=QUANTILE_TOLERANCE)
    assert cell["median"] == pytest.approx(
        CLASSIC_PRE_MEDIAN,
        abs=QUANTILE_TOLERANCE,
    )
    assert cell["q3"] == pytest.approx(CLASSIC_PRE_Q3, abs=QUANTILE_TOLERANCE)


def test_targets_withheld_for_the_mega_hull() -> None:
    """Four postings are not an anchor, in either era."""
    assert scoring.vsp_attack_rate_targets("pre")["mega_cruise_5000"] is None
    assert scoring.vsp_attack_rate_targets("post")["mega_cruise_5000"] is None


@pytest.mark.parametrize(
    "hull",
    ["expedition_cruise_450", "classic_cruise_1900", "spirit_cruise_3000"],
)
def test_targets_are_ordered_quantiles_with_their_postings(hull: str) -> None:
    """Every issued target is a real IQR and carries the n behind it."""
    target = scoring.vsp_attack_rate_targets("pre")[hull]

    assert target is not None
    assert target["q1"] < target["median"] < target["q3"]
    assert target["n"] == EXPECTED_COUNTS[(hull, "pre")]


def test_targets_reject_an_unknown_era() -> None:
    """An era outside the series' own vocabulary is a caller error."""
    with pytest.raises(ValueError, match="unknown era"):
        scoring.vsp_attack_rate_targets("during_covid")


def test_targets_cover_every_hull_class() -> None:
    """Every scored hull gets a key, present or explicitly withheld."""
    targets = scoring.vsp_attack_rate_targets("pre")

    assert set(targets) == set(scoring.HULL_CAPACITY)


def test_cli_paths_are_confined_to_their_declared_roots(tmp_path: Path) -> None:
    """Series and output CLI paths accept in-tree files and reject escapes."""
    assert (
        scoring._validated_cli_path(scoring.SERIES, scoring.SERIES.parent)
        == scoring.SERIES.resolve()
    )
    assert (
        scoring._validated_cli_path(Path("tests/report.md"), scoring.REPO_ROOT)
        == (scoring.REPO_ROOT / "tests/report.md").resolve()
    )

    with pytest.raises(ValueError, match="escapes"):
        scoring._validated_cli_path(tmp_path / "series.csv", scoring.SERIES.parent)
    with pytest.raises(ValueError, match="escapes"):
        scoring._validated_cli_path(Path("../outside.csv"), scoring.SERIES.parent)
    with pytest.raises(ValueError, match="escapes"):
        scoring._validated_cli_path(tmp_path / "report.md", scoring.REPO_ROOT)
    with pytest.raises(ValueError, match="escapes"):
        scoring._validated_cli_path(Path("../outside.md"), scoring.REPO_ROOT)


def test_vsp_cli_writes_a_report_inside_the_repository_root(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The direct CLI derives targets and writes only to an allowed root."""
    with tempfile.TemporaryDirectory(dir=scoring.REPO_ROOT) as directory:
        output = Path(directory) / "vsp_report.md"
        monkeypatch.setattr(
            sys,
            "argv",
            ["vsp_class_era_scoring.py", "--out", str(output)],
        )

        scoring.main()

        assert output.is_file()
        assert "VSP posted-outbreak targets" in output.read_text(encoding="utf-8")
    assert "VSP posted-outbreak targets" in capsys.readouterr().out


def test_anchor_report_identifies_era_and_target_sample_sizes() -> None:
    """A rendered report carries enough context to interpret its A4 verdicts."""
    targets = scoring.vsp_attack_rate_targets("pre")

    report = score_anchors.render({}, "pre", targets)

    assert "`pre` era" in report
    assert "| classic_cruise_1900 | 0.0418-0.0770 (median 0.0546) | 174 |" in report
    assert "| mega_cruise_5000 | none — n/a (insufficient VSP postings) | - |" in report


def _cell(reported: float) -> dict[str, float]:
    return {"reported_case_attack_rate_passenger": reported}


def test_verdict_reports_the_mega_hull_as_unanchored() -> None:
    """A mega-hull A4 result must never read as a pass or a plain n/a."""
    targets = scoring.vsp_attack_rate_targets("pre")

    verdict = score_anchors.verdicts("mega_cruise_5000", _cell(0.05), targets)

    assert verdict["A4_vsp_iqr"] == "n/a (insufficient VSP postings)"


@pytest.mark.parametrize(
    ("reported", "expected"),
    [
        (0.0300, "FAIL"),
        (0.0450, "PASS"),
        (0.0546, "PASS"),
        (0.0750, "PASS"),
        (0.1200, "FAIL"),
    ],
)
def test_verdict_scores_against_the_classic_pre_iqr(
    reported: float,
    expected: str,
) -> None:
    """A4 passes inside the derived IQR and fails on either side of it."""
    targets = scoring.vsp_attack_rate_targets("pre")

    verdict = score_anchors.verdicts("classic_cruise_1900", _cell(reported), targets)

    assert verdict["A4_vsp_iqr"] == expected
