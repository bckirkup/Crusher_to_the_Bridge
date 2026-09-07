"""Behavioral tests for the #37 admissible-region feasibility gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from simulation_utils.platform_complement import (
    declared_total,
    declaring_platforms,
)
from telemetry_buffer.observation_model import admissible_region as gate
from telemetry_buffer.observation_model import score_anchors
from telemetry_buffer.observation_model.bounded_screen import NOROVIRUS_FACTORS

TARGETS: dict[str, dict[str, float] | None] = {
    "mega_cruise_5000": {"q1": 0.035, "median": 0.05, "q3": 0.075, "n": 16.0},
    "spirit_cruise_3000": None,
}


def _cell(**overrides: Any) -> dict[str, Any]:
    cell = {
        "A1_ever_ill_passenger": 0.15,
        "A2_ill_per_infected__per_seed_median": 0.7,
        "A5_passenger_crew_ratio__per_seed_median": 3.0,
        "reported_case_attack_rate_passenger": 0.05,
        "A8_pax_incidence": 20.0,
        "A8_crew_incidence": 10.0,
        "A9_posting_probability": 0.005,
        "A9_eligible_runs": 200,
        "A9_posted_eligible": 1,
    }
    cell.update(overrides)
    return cell


def test_unit_cube_corners_map_to_the_declared_interval_endpoints() -> None:
    low = gate.factor_values(NOROVIRUS_FACTORS, [0.0] * len(NOROVIRUS_FACTORS))
    high = gate.factor_values(NOROVIRUS_FACTORS, [1.0] * len(NOROVIRUS_FACTORS))
    for factor in NOROVIRUS_FACTORS:
        assert low[factor.name] == pytest.approx(factor.low)
        assert high[factor.name] == pytest.approx(factor.high)


def test_log_scaled_factor_midpoint_is_geometric_not_arithmetic() -> None:
    units = [0.5] * len(NOROVIRUS_FACTORS)
    values = gate.factor_values(NOROVIRUS_FACTORS, units)
    emesis = next(f for f in NOROVIRUS_FACTORS if f.name == "emesis_total_shed_gec")
    assert values[emesis.name] == pytest.approx((emesis.low * emesis.high) ** 0.5)


def test_sobol_design_is_reproducible_and_inside_the_cube() -> None:
    first = gate.sobol_units(6, 4, seed=37)
    again = gate.sobol_units(6, 4, seed=37)
    other = gate.sobol_units(6, 4, seed=38)
    assert first == again
    assert first != other
    assert len(first) == 16
    assert all(0.0 <= value <= 1.0 for row in first for value in row)


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0.05, gate.BELOW), (0.15, gate.INSIDE), (0.9, gate.ABOVE), (None, gate.UNDETERMINED)],
)
def test_position_reports_which_side_of_the_interval_a_value_lands(
    value: float | None,
    expected: str,
) -> None:
    assert gate.position(value, (0.10, 0.22)) == expected


def test_position_is_undetermined_without_an_interval() -> None:
    assert gate.position(0.5, None) == gate.UNDETERMINED


def test_measurements_carry_the_direction_of_every_miss() -> None:
    measured = gate.measurements(
        "mega_cruise_5000",
        _cell(
            A1_ever_ill_passenger=0.01,
            reported_case_attack_rate_passenger=0.5,
            A8_pax_incidence=900.0,
        ),
        TARGETS,
        "pre",
    )
    assert measured["A1_ever_ill_passenger"]["position"] == gate.BELOW
    assert measured["A4_vsp_iqr"]["position"] == gate.ABOVE
    assert measured["A8"]["passenger"]["position"] == gate.ABOVE
    assert measured["A2_ill_per_infected"]["position"] == gate.INSIDE


def test_a4_has_no_interval_where_the_series_declares_no_target() -> None:
    measured = gate.measurements("spirit_cruise_3000", _cell(), TARGETS, "pre")
    assert measured["A4_vsp_iqr"]["interval"] is None
    assert measured["A4_vsp_iqr"]["position"] == gate.UNDETERMINED


def test_a9_is_unresolvable_by_a_small_cell_and_resolvable_by_the_named_one() -> None:
    small = gate.a9_design_resolution(5, "pre")
    assert not small["resolvable"]
    needed = small["min_runs_for_one_posting_inside"]
    assert isinstance(needed, int)
    assert gate.a9_design_resolution(needed, "pre")["resolvable"]
    low, high = small["interval"]
    assert low <= 1.0 / needed <= high


def test_a9_resolution_is_monotone_in_the_number_of_runs() -> None:
    resolvable = [
        n for n in (5, 20, 50, 100, 200, 400)
        if gate.a9_design_resolution(n, "pre")["resolvable"]
    ]
    assert resolvable == [200, 400]


def test_only_an_unresolvable_anchor_is_named_design_limited() -> None:
    limited = gate.design_limited_anchors(5, "pre")
    assert set(limited) == {"A9"}
    assert "0.2" in limited["A9"]
    assert gate.design_limited_anchors(200, "pre") == {}


def test_a4_and_a8_cannot_be_met_by_one_homogeneous_cell() -> None:
    conflict = gate.a4_a8_definitional_conflict("mega_cruise_5000", "pre", 7.0)
    assert conflict["comparable"]
    assert not conflict["overlaps"]
    assert conflict["separation_factor"] > 1.0
    implied_low, _implied_high = conflict["a4_implied_incidence_per_100k_travel_days"]
    assert implied_low > conflict["a8_passenger_band"][1]


def test_the_a4_a8_separation_scales_with_the_voyage_length() -> None:
    short = gate.a4_a8_definitional_conflict("mega_cruise_5000", "pre", 3.0)
    long_voyage = gate.a4_a8_definitional_conflict("mega_cruise_5000", "pre", 14.0)
    assert short["separation_factor"] > long_voyage["separation_factor"]


def test_the_a4_a8_conflict_is_not_asserted_without_both_targets() -> None:
    assert not gate.a4_a8_definitional_conflict("spirit_cruise_3000", "post", 7.0)[
        "comparable"
    ]
    assert not gate.a4_a8_definitional_conflict("mega_cruise_5000", "pre", None)[
        "comparable"
    ]


def test_voyage_length_is_recovered_from_the_cell_rather_than_assumed() -> None:
    points = [{"cell": _cell(reported_case_attack_rate_passenger=0.0, A8_pax_incidence=0.0)},
              {"cell": _cell(reported_case_attack_rate_passenger=0.07, A8_pax_incidence=1000.0)}]
    assert gate.observed_voyage_days(points) == pytest.approx(7.0)
    assert gate.observed_voyage_days(points[:1]) is None


def _verdicts(**overrides: str) -> dict[str, str]:
    out = dict.fromkeys(gate.REQUIRED_ANCHORS, "PASS")
    out.update(overrides)
    return out


def test_a_failing_anchor_makes_a_point_inadmissible_whatever_else_passes() -> None:
    result = gate.classify(_verdicts(A8="FAIL"), [])
    assert result["class"] == gate.INADMISSIBLE
    assert result["failed"] == ["A8"]


def test_a_missing_verdict_is_unscored_rather_than_admissible() -> None:
    result = gate.classify(_verdicts(A8="n/a (no reporting)"), [])
    assert result["class"] == gate.UNSCORED
    assert result["unresolved"] == {"A8": "n/a (no reporting)"}


def test_a_design_limited_anchor_withholds_admissibility_without_failing_it() -> None:
    result = gate.classify(_verdicts(A9="FAIL"), ["A9"])
    assert result["class"] == gate.ADMISSIBLE_PENDING
    assert result["failed"] == []
    assert result["design_limited"] == ["A9"]


def test_a_point_is_admissible_only_with_every_required_anchor_passing() -> None:
    assert gate.classify(_verdicts(), [])["class"] == gate.ADMISSIBLE


def test_a_failure_outranks_a_design_limit() -> None:
    result = gate.classify(_verdicts(A1_ever_ill_passenger="FAIL"), ["A9"])
    assert result["class"] == gate.INADMISSIBLE


def test_construction_bands_are_not_required_for_admissibility() -> None:
    assert "A3_reported_per_symptomatic" not in gate.REQUIRED_ANCHORS


def _point(verdicts: dict[str, str], factors: dict[str, float], **kwargs: Any) -> dict[str, Any]:
    point = {
        "verdicts": verdicts,
        "factors": factors,
        "measurements": gate.measurements(
            "mega_cruise_5000", _cell(**kwargs), TARGETS, "pre",
        ),
    }
    point["classification"] = gate.classify(verdicts, [])
    return point


def test_anchor_tally_counts_verdicts_and_the_side_each_failure_missed_on() -> None:
    points = [
        _point(_verdicts(A1_ever_ill_passenger="FAIL"), {"x": 1.0}, A1_ever_ill_passenger=0.01),
        _point(_verdicts(A1_ever_ill_passenger="FAIL"), {"x": 2.0}, A1_ever_ill_passenger=0.9),
        _point(_verdicts(), {"x": 3.0}),
    ]
    tally = gate.anchor_tally(points)
    assert tally["A1_ever_ill_passenger"]["FAIL"] == 2
    assert tally["A1_ever_ill_passenger"]["PASS"] == 1
    assert tally["A1_ever_ill_passenger"][gate.BELOW] == 1
    assert tally["A1_ever_ill_passenger"][gate.ABOVE] == 1


def test_anchor_tally_reads_both_roles_of_a_two_channel_anchor() -> None:
    points = [_point(_verdicts(A8="FAIL"), {"x": 1.0}, A8_pax_incidence=900.0, A8_crew_incidence=900.0)]
    assert gate.anchor_tally(points)["A8"][gate.ABOVE] == 2


def test_a_pair_never_passing_together_is_reported_as_zero_joint_passes() -> None:
    points = [
        _point(_verdicts(A8="FAIL"), {"x": 1.0}),
        _point(_verdicts(A1_ever_ill_passenger="FAIL"), {"x": 2.0}),
    ]
    pairs = gate.joint_pass_pairs(points)
    assert pairs["A1_ever_ill_passenger+A8"] == 0
    assert pairs["A2_ill_per_infected+A5_passenger_crew_ratio"] == 2


def test_marginal_ranges_bracket_the_selected_points_and_are_none_when_empty() -> None:
    points = [
        _point(_verdicts(), {"x": 1.0, "y": 5.0}),
        _point(_verdicts(), {"x": 3.0, "y": 4.0}),
        _point(_verdicts(A8="FAIL"), {"x": 99.0, "y": 99.0}),
    ]
    ranges = gate.marginal_ranges(points, [gate.ADMISSIBLE])
    assert ranges == {"x": [1.0, 3.0], "y": [4.0, 5.0]}
    assert gate.marginal_ranges(points, [gate.ADMISSIBLE_PENDING]) is None


def test_summary_fractions_partition_the_sampled_points() -> None:
    points = [
        _point(_verdicts(), {"x": 1.0}),
        _point(_verdicts(A8="FAIL"), {"x": 2.0}),
        _point(_verdicts(A8="n/a (no reporting)"), {"x": 3.0}),
        _point(_verdicts(A8="FAIL"), {"x": 4.0}),
    ]
    summary = gate.summarise_design(
        points, gate.Design(), list(range(500, 700)),
    )
    assert summary["n_points"] == 4
    assert sum(summary["class_counts"].values()) == 4
    assert summary["admissible_volume_fraction"] == pytest.approx(0.25)
    assert summary["unscored_fraction"] == pytest.approx(0.25)
    assert summary["design_limited_anchors"] == {}


def test_the_summary_declares_the_design_limit_it_ran_under() -> None:
    summary = gate.summarise_design([], gate.Design(), [500, 501])
    assert set(summary["design_limited_anchors"]) == {"A9"}
    assert not summary["a9_design_resolution"]["resolvable"]


def test_the_effective_reporting_hazard_is_read_and_never_defaulted() -> None:
    assert gate._effective_reporting_hazard(
        {"syndromic": {"sick_call_probability": 0.4}},
    ) == pytest.approx(0.4)
    with pytest.raises(RuntimeError, match="no syndromic sick-call hazard"):
        gate._effective_reporting_hazard({"syndromic": {}})


def test_a_gate_run_isolates_the_pathogen_through_initiation() -> None:
    spec = gate.build_run_spec(
        NOROVIRUS_FACTORS,
        [0.5] * len(NOROVIRUS_FACTORS),
        seed=500,
        description="gate_probe",
        **gate.Design().run_kwargs(),
    )
    boarding = spec["config_overrides"]["initiation"]["boarding"]
    assert boarding["enabled"] is True
    assert boarding["sars_cov2_resp"] == {"enabled": False}
    assert "norwalk_gi" not in boarding
    assert spec["pathogen_overrides"]["norwalk_gi"]


def test_an_unknown_hull_yields_no_a8_interval_and_no_a4_a8_comparison() -> None:
    a8 = gate._a8_measurements("nonesuch_hull", _cell(), "pre")
    assert a8["passenger"]["interval"] is None
    assert a8["passenger"]["position"] == gate.UNDETERMINED
    assert not gate.a4_a8_definitional_conflict("nonesuch_hull", "pre", 7.0)[
        "comparable"
    ]


def test_a9_is_declared_unresolvable_where_the_era_has_no_target() -> None:
    resolution = gate.a9_design_resolution(1_000, "post")
    assert not resolution["resolvable"]
    assert "post" in resolution["reason"]


def test_a_measurement_that_is_not_a_mapping_contributes_no_miss_side() -> None:
    assert gate._fail_sides(None) == []
    assert gate._fail_sides(0.5) == []


def _canonical_row(seed: int) -> dict[str, Any]:
    """One scorer row, built the way an archive row is built."""
    return score_anchors.row_from_summary(
        {
            "run_id": f"probe_s{seed}",
            "parameters": {
                "platform_id": "mega_cruise_5000",
                "surveillance": gate.SURVEILLANCE_LABEL,
                "seed": seed,
                "num_epochs": 168,
                "num_agents": 450,
                "natural_history_clock": "hours",
                "sick_call_probability_per_day": 1.0,
                "era": "pre",
            },
            "derived": {
                "peak_prevalence": 40,
                "passenger_complement": 321,
                "crew_complement": 129,
                "ever_ill_attack_rate_passenger": 0.15,
                "ever_ill_attack_rate_crew": 0.05,
                "infection_attack_rate_passenger": 0.21,
                "infection_attack_rate_crew": 0.07,
                "reported_case_attack_rate_passenger": 0.05,
                "reported_case_attack_rate_crew": 0.016,
                "vsp_trigger_epoch": 40,
            },
        },
        f"probe_s{seed}.zip",
    )


def test_a_point_is_one_cell_over_the_matched_seed_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[int] = []

    def fake_run_row(_factors, _units, *, seed, design, point_index):
        assert design.complement == declared_total(design.platform)
        assert point_index == 3
        seen.append(seed)
        return _canonical_row(seed)

    monkeypatch.setattr(gate, "run_row", fake_run_row)
    point = gate.evaluate_point(
        [0.5] * len(NOROVIRUS_FACTORS),
        point_index=3,
        seeds=[500, 501, 502],
        design=gate.Design(),
    )
    assert seen == [500, 501, 502]
    assert point["cell"]["n_seeds"] == 3
    assert set(point["verdicts"]) >= {"A1_ever_ill_passenger", "A8", "A9"}
    assert point["classification"]["design_limited"] == ["A9"]
    assert set(point["factors"]) == {factor.name for factor in NOROVIRUS_FACTORS}


def _stub_point(index: int) -> dict[str, Any]:
    point = _point(_verdicts(), {"x": float(index)})
    point["point_index"] = index
    point["cell"] = _cell()
    return point


def test_every_evaluated_point_is_streamed_and_completed_ones_are_not_rerun(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evaluated: list[int] = []

    def fake_evaluate_point(_units, *, point_index, seeds, design):
        assert len(seeds) == 2
        assert design.era == "pre"
        evaluated.append(point_index)
        return _stub_point(point_index)

    monkeypatch.setattr(gate, "evaluate_point", fake_evaluate_point)
    streamed: list[int] = []
    points = gate.evaluate_design(
        [[0.1] * len(NOROVIRUS_FACTORS)] * 4,
        seeds=[500, 501],
        design=gate.Design(),
        on_point=lambda point: streamed.append(point["point_index"]),
        start_index=2,
    )
    assert evaluated == [2, 3]
    assert streamed == [2, 3]
    assert [point["point_index"] for point in points] == [2, 3]


def test_the_command_line_declares_the_design_and_accepts_overrides() -> None:
    default = gate.parse_args(["--out", "report.json"])
    assert default.sobol_m == 7
    assert default.seeds == 5
    assert default.era == "pre"
    # Not a pinned hull: whatever the default is, its complement is the one
    # its own layout declares -- 450 agents on the 7,000-agent mega hull was
    # the defect, and it was constructible because these two were independent.
    assert default.platform in declaring_platforms()
    assert default.num_agents is None
    assert default.stream is None
    assert not default.resume
    overridden = gate.parse_args(
        [
            "--out", "report.json",
            "--stream", "points.jsonl",
            "--resume",
            "--era", "post",
            "--sobol-m", "2",
            "--seeds", "3",
            "--workers", "4",
            "--observation-scenario", "low_capture",
        ],
    )
    assert overridden.era == "post"
    assert overridden.sobol_m == 2
    assert overridden.workers == 4
    assert overridden.observation_scenario == "low_capture"
    assert overridden.resume


def test_the_gate_writes_its_report_and_resumes_from_its_own_stream(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(gate, "REPO_ROOT", tmp_path)
    evaluated: list[int] = []

    def fake_evaluate_point(_units, *, point_index, seeds, design):
        evaluated.append(point_index)
        return _stub_point(point_index)

    monkeypatch.setattr(gate, "evaluate_point", fake_evaluate_point)
    out = tmp_path / "report.json"
    stream = tmp_path / "points.jsonl"
    argv = [
        "--out", str(out),
        "--stream", str(stream),
        "--sobol-m", "1",
        "--seeds", "2",
    ]
    assert gate.main(argv) == 0
    assert evaluated == [0, 1]
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["mode"] == "feasibility_gate"
    assert payload["summary"]["n_points"] == 2
    assert payload["design"]["required_anchors"] == list(gate.REQUIRED_ANCHORS)
    assert [factor["name"] for factor in payload["factors"]] == [
        factor.name for factor in NOROVIRUS_FACTORS
    ]
    assert len(stream.read_text(encoding="utf-8").strip().splitlines()) == 2

    evaluated.clear()
    assert gate.main([*argv, "--resume"]) == 0
    assert evaluated == []
    resumed = json.loads(out.read_text(encoding="utf-8"))
    assert resumed["summary"]["n_points"] == 2


def test_a_missing_scoring_input_is_refused_before_any_voyage_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evaluated: list[int] = []

    def fake_evaluate_point(_units, *, point_index, seeds, design):
        evaluated.append(point_index)
        return _stub_point(point_index)

    def missing_series(_era):
        raise FileNotFoundError(2, "No such file", "vsp_outbreak_series.csv")

    monkeypatch.setattr(gate, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(gate, "evaluate_point", fake_evaluate_point)
    monkeypatch.setattr(gate, "vsp_attack_rate_targets", missing_series)
    with pytest.raises(SystemExit, match="vsp_outbreak_series.csv"):
        gate.main(["--out", str(tmp_path / "r.json"), "--sobol-m", "1", "--seeds", "1"])
    assert evaluated == []


def _quiet_row(seed: int, reported: float) -> dict[str, Any]:
    """One scorer row whose reported passenger rate is set by the caller."""
    row = _canonical_row(seed)
    row["reported_case_attack_rate_passenger"] = reported
    row["reported_case_attack_rate_crew"] = 0.0
    row["vsp_trigger_epoch"] = (
        40 if reported >= score_anchors.A9_POSTING_THRESHOLD else None
    )
    return row


def _rate(seed: int) -> float:
    """A voyage's reported rate: one seed in five posts, the rest are quiet."""
    return 0.09 if seed % 5 == 0 else 0.001 * (seed % 5)


def _point_with_rows(
    monkeypatch: pytest.MonkeyPatch,
    seeds: list[int],
) -> dict[str, Any]:
    monkeypatch.setattr(
        gate,
        "run_row",
        lambda _f, _u, *, seed, design, point_index: _quiet_row(seed, _rate(seed)),
    )
    return gate.evaluate_point(
        [0.5] * len(NOROVIRUS_FACTORS),
        point_index=7,
        seeds=seeds,
        design=gate.Design(),
    )


def test_a_point_keeps_one_run_vector_per_seed_beside_its_cell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seeds = list(range(500, 520))
    point = _point_with_rows(monkeypatch, seeds)
    runs = point["runs"]
    assert [run["seed"] for run in runs] == seeds
    assert set(runs[0]) == set(gate.RETAINED_RUN_FIELDS)
    posting = [
        run for run in runs
        if run["reported_case_attack_rate_passenger"]
        >= score_anchors.A9_POSTING_THRESHOLD
    ]
    assert len(posting) == point["cell"]["A9_posted_eligible"]
    # The retained vectors carry the within-point spread the cell hides.
    assert len({run["reported_case_attack_rate_passenger"] for run in runs}) > 1


def test_the_retained_vectors_track_the_cell_when_the_voyages_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    quiet = _point_with_rows(monkeypatch, list(range(501, 505)))
    mixed = _point_with_rows(monkeypatch, list(range(500, 520)))
    assert quiet["cell"]["A9_posted_eligible"] == 0
    assert mixed["cell"]["A9_posted_eligible"] > 0
    assert len(quiet["runs"]) == 4
    assert len(mixed["runs"]) == 20


@pytest.mark.parametrize("count", [1, 2, 3, 5])
def test_seed_blocks_partition_the_matched_set_exactly(count: int) -> None:
    seeds = list(range(500, 515))
    blocks = gate.seed_blocks(seeds, count)
    assert len(blocks) == count
    pooled = sorted(seed for block in blocks for seed in block)
    assert pooled == seeds


def test_more_blocks_than_seeds_is_refused_rather_than_left_empty() -> None:
    with pytest.raises(ValueError, match="empty"):
        gate.seed_blocks([500, 501], 3)


def test_a_selection_keeps_the_grid_indices_and_refuses_one_outside() -> None:
    grid = [[0.1], [0.2], [0.3], [0.4]]
    assert gate.selected_indices(grid) == [0, 1, 2, 3]
    assert gate.selected_indices(grid, [3, 1, 3]) == [1, 3]
    with pytest.raises(ValueError, match="outside the grid"):
        gate.selected_indices(grid, [1, 9])


def _write_blocks(
    tmp_path: Path,
    blocks: list[dict[str, Any]],
    name: str = "rows.jsonl",
) -> Path:
    stream = tmp_path / name
    with stream.open("w", encoding="utf-8") as handle:
        for block in blocks:
            handle.write(json.dumps(block) + "\n")
    return stream


def test_pooled_seed_blocks_score_the_cell_an_unsharded_point_would_score(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seeds = list(range(500, 512))
    unsharded = _point_with_rows(monkeypatch, seeds)
    blocks = [
        gate.evaluate_block(
            [0.5] * len(NOROVIRUS_FACTORS),
            point_index=7,
            block_index=index,
            seeds=block,
            design=gate.Design(),
        )
        for index, block in enumerate(gate.seed_blocks(seeds, 4))
    ]
    monkeypatch.setattr(gate, "REPO_ROOT", tmp_path)
    pooled = gate.pooled_row_points(
        [_write_blocks(tmp_path, blocks)],
        expected=[7],
        seeds=seeds,
        seed_shards=4,
        design=gate.Design(),
    )
    assert len(pooled) == 1
    assert pooled[0]["cell"] == unsharded["cell"]
    assert pooled[0]["verdicts"] == unsharded["verdicts"]
    assert sorted(run["seed"] for run in pooled[0]["runs"]) == seeds


def test_a_cell_missing_a_seed_block_is_refused_rather_than_scored_small(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seeds = list(range(500, 508))
    split = gate.seed_blocks(seeds, 2)
    monkeypatch.setattr(
        gate,
        "run_row",
        lambda _f, _u, *, seed, design, point_index: _quiet_row(seed, _rate(seed)),
    )
    first = gate.evaluate_block(
        [0.5] * len(NOROVIRUS_FACTORS),
        point_index=7,
        block_index=0,
        seeds=split[0],
        design=gate.Design(),
    )
    monkeypatch.setattr(gate, "REPO_ROOT", tmp_path)
    stream = _write_blocks(tmp_path, [first])
    with pytest.raises(SystemExit, match="missing seed block"):
        gate.pooled_row_points(
            [stream],
            expected=[7],
            seeds=seeds,
            seed_shards=2,
            design=gate.Design(),
        )
    with pytest.raises(SystemExit, match="design points are absent"):
        gate.pooled_row_points(
            [stream],
            expected=[7, 8],
            seeds=seeds,
            seed_shards=1,
            design=gate.Design(),
        )


def test_a_seed_block_pooled_twice_is_refused(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(gate, "REPO_ROOT", tmp_path)
    block = {
        "kind": gate.ROWS_RECORD,
        "point_index": 7,
        "block_index": 0,
        "units": [0.5],
        "seeds": [500],
        "rows": [_quiet_row(500, 0.001)],
    }
    stream = _write_blocks(tmp_path, [block, dict(block)])
    with pytest.raises(SystemExit, match="more than one shard stream"):
        gate.pooled_row_points(
            [stream],
            expected=[7],
            seeds=[500],
            seed_shards=1,
            design=gate.Design(),
        )


def test_pooling_a_different_seed_set_than_the_design_is_refused(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(gate, "REPO_ROOT", tmp_path)
    block = {
        "kind": gate.ROWS_RECORD,
        "point_index": 7,
        "block_index": 0,
        "units": [0.5],
        "seeds": [500],
        "rows": [_quiet_row(500, 0.001)],
    }
    stream = _write_blocks(tmp_path, [block])
    with pytest.raises(SystemExit, match="pools 1 seeds"):
        gate.pooled_row_points(
            [stream],
            expected=[7],
            seeds=[500, 501],
            seed_shards=1,
            design=gate.Design(),
        )


def test_block_shards_cover_every_point_and_block_exactly_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ran: list[tuple[int, int]] = []

    def fake_block(_units, *, point_index, block_index, seeds, design):
        ran.append((point_index, block_index))
        return {
            "kind": gate.ROWS_RECORD,
            "point_index": point_index,
            "block_index": block_index,
            "units": [0.5],
            "seeds": list(seeds),
            "rows": [],
        }

    monkeypatch.setattr(gate, "evaluate_block", fake_block)
    grid = [[0.1] * len(NOROVIRUS_FACTORS) for _ in range(4)]
    covered: list[tuple[int, int]] = []
    for shard in range(3):
        covered += [
            (record["point_index"], record["block_index"])
            for record in gate.evaluate_blocks(
                grid,
                seeds=list(range(500, 504)),
                design=gate.Design(),
                seed_shards=2,
                shard_count=3,
                shard_index=shard,
                only=[1, 2],
            )
        ]
    assert sorted(covered) == [(1, 0), (1, 1), (2, 0), (2, 1)]
    assert sorted(ran) == sorted(covered)


def test_a_named_subset_is_the_only_thing_a_subset_run_evaluates(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(gate, "REPO_ROOT", tmp_path)
    evaluated: list[int] = []

    def fake_evaluate_point(_units, *, point_index, seeds, design):
        evaluated.append(point_index)
        return _stub_point(point_index)

    monkeypatch.setattr(gate, "evaluate_point", fake_evaluate_point)
    out = tmp_path / "subset.json"
    assert gate.main([
        "--out", str(out),
        "--sobol-m", "2",
        "--seeds", "2",
        "--only-points", "1", "3",
    ]) == 0
    assert evaluated == [1, 3]
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["design"]["selected_points"] == [1, 3]
    assert payload["summary"]["n_points"] == 2


def test_a_seed_sharded_shard_reports_units_and_no_verdict(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(gate, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        gate,
        "run_row",
        lambda _f, _u, *, seed, design, point_index: _quiet_row(seed, _rate(seed)),
    )
    out = tmp_path / "block.json"
    stream = tmp_path / "block.jsonl"
    assert gate.main([
        "--out", str(out),
        "--stream", str(stream),
        "--sobol-m", "1",
        "--seeds", "4",
        "--seed-shards", "2",
        "--only-points", "0",
    ]) == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["mode"] == "feasibility_gate_rows_shard"
    assert "summary" not in payload
    assert payload["units"] == [
        {"point_index": 0, "block_index": 0, "n_rows": 2},
        {"point_index": 0, "block_index": 1, "n_rows": 2},
    ]
    merged = tmp_path / "merged.json"
    assert gate.main([
        "--out", str(merged),
        "--merge", str(stream),
        "--sobol-m", "1",
        "--seeds", "4",
        "--seed-shards", "2",
        "--only-points", "0",
    ]) == 0
    pooled = json.loads(merged.read_text(encoding="utf-8"))
    assert pooled["summary"]["n_points"] == 1
    assert pooled["points"][0]["cell"]["n_seeds"] == 4
    assert len(pooled["points"][0]["runs"]) == 4
