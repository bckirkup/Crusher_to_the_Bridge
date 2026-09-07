"""The low-posting read-out counts voyages, and reports zero as a bound."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from telemetry_buffer.observation_model import gate37_lowposting as low
from telemetry_buffer.observation_model.score_anchors import A9_POSTING_THRESHOLD

ANALYSIS = (
    Path(__file__).resolve().parent.parent
    / "telemetry_buffer" / "observation_model"
    / "gate37_lowposting_v1_analysis.json"
)


def _row(infection=0.0, ill=0.0, reported=0.0, crew=0.0, took_off=True):
    return {
        "took_off": took_off,
        "infection_attack_rate_passenger": infection,
        "A1_ever_ill_passenger": ill,
        "reported_case_attack_rate_passenger": reported,
        "reported_case_attack_rate_crew": crew,
    }


def _point(index, rows):
    return {"point_index": index, "runs": rows}


LADDER = [
    _row(),
    _row(infection=0.05),
    _row(infection=0.05, ill=0.01),
    _row(infection=0.05, ill=0.01, reported=0.01),
    _row(infection=0.3, ill=0.2, reported=0.08),
    _row(infection=0.3, ill=0.2, reported=0.01, crew=0.04),
]


def test_posting_rule_matches_the_scorer_on_either_complement():
    assert not low.posted(_row(reported=A9_POSTING_THRESHOLD - 1e-9))
    assert low.posted(_row(reported=A9_POSTING_THRESHOLD))
    assert low.posted(_row(crew=A9_POSTING_THRESHOLD))


def test_each_voyage_lands_in_exactly_one_class():
    counts = low.voyage_classes(LADDER)
    assert counts == {
        "no_infection": 1,
        "infected_no_illness": 1,
        "ill_no_report": 1,
        "reported_below_threshold": 1,
        "posted": 2,
    }
    assert sum(counts.values()) == len(LADDER)


@pytest.mark.parametrize("k,n", [(0, 10), (1, 1440), (7, 180), (180, 180)])
def test_exact_binomial_interval_brackets_the_observed_frequency(k, n):
    lower, upper = low.exact_binomial_interval(k, n)
    assert 0.0 <= lower <= k / n <= upper <= 1.0
    if k == 0:
        assert lower == pytest.approx(0.0)
        assert upper > 0.0
    if k == n:
        assert upper == pytest.approx(1.0)


def test_zero_count_widens_as_the_cell_shrinks():
    _, wide = low.exact_binomial_interval(0, 180)
    _, narrow = low.exact_binomial_interval(0, 1440)
    assert narrow < wide
    # 1440 voyages resolve a ~0.1% frequency; 180 do not.
    assert narrow < 0.003 < wide


def test_rate_summary_reports_zero_mass_and_the_nonzero_tail():
    summary = low.rate_summary(LADDER, "reported_case_attack_rate_passenger")
    assert summary["zero_fraction"] == pytest.approx(0.5)
    assert summary["nonzero_quantiles"][0] == pytest.approx(0.01)
    assert summary["nonzero_quantiles"][-1] == pytest.approx(0.08)
    assert low.rate_summary([], "reported_case_attack_rate_passenger") == {
        "zero_fraction": None, "quantiles": [], "nonzero_quantiles": [],
    }


def test_point_summary_counts_postings_and_keeps_the_gate_count():
    reference = [{"point_index": 5, "cell": {"A9_posted_eligible": 9}}]
    analysis = low.analyse([_point(5, LADDER)], reference, groups={"g": (5, 99)})
    (summary,) = analysis["points"]
    assert summary["posted"] == 2
    assert summary["posting_frequency"] == pytest.approx(2 / 6)
    assert summary["gate_180_posted"] == 9
    assert summary["posted_reported_passenger"]["quantiles"][0] == pytest.approx(0.01)
    (group,) = analysis["groups"]
    assert group["points"] == [5]
    assert group["per_point_posted"] == [2]
    assert group["n_voyages"] == 6


def test_group_with_no_present_points_is_dropped_not_zeroed():
    analysis = low.analyse([_point(5, LADDER)], groups={"absent": (1, 2)})
    assert analysis["groups"] == []


def test_report_lines_carry_the_frequency_and_its_bounds():
    analysis = low.analyse([_point(5, LADDER)], groups={"g": (5,)})
    text = "\n".join(low.report(analysis))
    assert "point   5: posted 2/6 = 33.3333%" in text
    assert "group g (1 points, 6 voyages)" in text


def test_the_committed_analysis_keeps_the_run_it_describes():
    """Change detectors on the 16-point, 1,440-seed re-run of gate #37 v2."""
    record = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    assert record["n_points"] == 16
    assert record["n_voyages"] == 16 * 1440
    groups = {group["group"]: group for group in record["groups"]}
    assert groups["quietest"]["posted"] == 793
    assert groups["quietest"]["posting_frequency"] == pytest.approx(0.045891)
    assert groups["a1_band"]["posted"] == 2875
    # Every voyage established transmission or fizzled; none was uninfected.
    for group in record["groups"]:
        assert group["classes"]["no_infection"] == 0


def test_posting_channels_partition_the_posted_voyages():
    rows = [
        _row(reported=0.05, crew=0.0),
        _row(reported=0.0, crew=0.04),
        _row(reported=0.05, crew=0.04),
        _row(reported=0.01, crew=0.01),
    ]
    channels = low.posting_channels(rows)
    assert channels == {"passenger_only": 1, "crew_only": 1, "both": 1}
    assert sum(channels.values()) == sum(1 for row in rows if low.posted(row))


def test_the_crew_channel_carries_most_low_posting_postings():
    """Half the quiet region's postings never crossed the passenger threshold."""
    record = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    quietest = next(g for g in record["groups"] if g["group"] == "quietest")
    channels = quietest["posting_channels"]
    assert channels["crew_only"] == 408
    assert channels["crew_only"] > channels["passenger_only"] + channels["both"]


def test_no_point_reaches_the_anchor_and_none_is_reported_as_quiet():
    record = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    for summary in record["points"]:
        lower_bound = summary["posting_interval_95"][0]
        # A9's ceiling is 0.56%; a point clears it only if its interval does.
        assert lower_bound > 0.0056, summary["point_index"]


def test_load_points_refuses_paths_outside_the_repository(tmp_path):
    outside = tmp_path / "merged.json"
    outside.write_text('{"points": []}', encoding="utf-8")
    with pytest.raises(Exception):
        low.load_points(outside)
