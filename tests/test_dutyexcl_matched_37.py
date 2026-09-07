"""The duty-exclusion read-out is paired, and refuses arms that are not."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from telemetry_buffer.observation_model import dutyexcl_matched_37 as matched
from telemetry_buffer.observation_model.score_anchors import A9_POSTING_THRESHOLD

ANALYSIS = (
    Path(__file__).resolve().parent.parent
    / "telemetry_buffer" / "observation_model"
    / "dutyexcl_matched_37_v1_analysis.json"
)


def _row(seed=0, reported=0.0, crew=0.0, **rest):
    row = {
        "seed": seed,
        "took_off": True,
        "infection_attack_rate_passenger": 0.0,
        "infection_attack_rate_crew": 0.0,
        "A1_ever_ill_passenger": 0.0,
        "ever_ill_attack_rate_crew": 0.0,
        "reported_case_attack_rate_passenger": reported,
        "reported_case_attack_rate_crew": crew,
        "peak_prevalence": 0.0,
    }
    row.update(rest)
    return row


def _point(index, rows):
    return {"point_index": index, "runs": rows}


def test_the_channel_rule_names_the_complement_that_carried_the_voyage():
    high = A9_POSTING_THRESHOLD
    low = A9_POSTING_THRESHOLD - 1e-9
    assert matched.channel(_row(reported=low, crew=low)) == "quiet"
    assert matched.channel(_row(reported=high, crew=low)) == "passenger_only"
    assert matched.channel(_row(reported=low, crew=high)) == "crew_only"
    assert matched.channel(_row(reported=high, crew=high)) == "both"


def test_pairing_refuses_arms_that_cover_different_grid_indices():
    with pytest.raises(ValueError, match="different grid indices"):
        matched.paired_points(
            [_point(1, [_row(seed=0)])],
            [_point(2, [_row(seed=0)])],
        )


def test_pairing_refuses_a_point_whose_arms_ran_different_seeds():
    with pytest.raises(ValueError, match="different seeds"):
        matched.paired_points(
            [_point(1, [_row(seed=0), _row(seed=1)])],
            [_point(1, [_row(seed=0), _row(seed=2)])],
        )


def test_pairing_keeps_the_grid_order_and_matches_every_seed():
    pairs = matched.paired_points(
        [_point(7, [_row(seed=3)]), _point(2, [_row(seed=1)])],
        [_point(2, [_row(seed=1)]), _point(7, [_row(seed=3)])],
    )
    assert [index for index, _base, _arm in pairs] == [2, 7]
    assert [sorted(base) for _index, base, _arm in pairs] == [[1], [3]]


def test_transitions_count_the_channel_each_matched_voyage_moved_to():
    base = {0: _row(crew=0.05), 1: _row(crew=0.05), 2: _row()}
    arm = {0: _row(), 1: _row(crew=0.05), 2: _row(reported=0.05)}
    assert matched.transitions(base, arm) == {
        "crew_only -> quiet": 1,
        "crew_only -> crew_only": 1,
        "quiet -> passenger_only": 1,
    }


def test_no_discordant_pair_leaves_the_p_value_null_rather_than_one():
    record = matched.mcnemar(0, 0)
    assert record["discordant"] == 0
    assert record["p_value"] is None


@pytest.mark.parametrize(
    ("gained", "lost", "resolves"),
    [(0, 6, True), (0, 5, False), (4, 5, False), (0, 30, True)],
)
def test_mcnemar_resolves_a_one_sided_split_and_not_a_balanced_one(
    gained: int, lost: int, resolves: bool,
) -> None:
    assert (matched.mcnemar(gained, lost)["p_value"] < 0.05) is resolves


def test_discordance_reads_the_posting_rule_on_matched_voyages():
    base = {0: _row(crew=0.05), 1: _row(), 2: _row(reported=0.05)}
    arm = {0: _row(), 1: _row(crew=0.05), 2: _row(reported=0.05)}
    record = matched.discordance(base, arm)
    assert (record["lost"], record["gained"], record["discordant"]) == (1, 1, 2)


def test_paired_deltas_report_the_mean_change_and_how_many_pairs_moved():
    base = {0: _row(reported=0.02), 1: _row(reported=0.04)}
    arm = {0: _row(reported=0.01), 1: _row(reported=0.04)}
    delta = matched.paired_deltas(base, arm)["reported_case_attack_rate_passenger"]
    assert delta["mean_change"] == pytest.approx(-0.005)
    assert delta["changed_pairs"] == 1
    assert delta["changed_fraction"] == pytest.approx(0.5)


def test_pooling_keeps_a_seed_matched_to_its_own_partner_across_points():
    pairs = matched.paired_points(
        [_point(1, [_row(seed=5, crew=0.05)]), _point(2, [_row(seed=5)])],
        [_point(1, [_row(seed=5, crew=0.05)]), _point(2, [_row(seed=5, crew=0.05)])],
    )
    base, arm = matched.pool(pairs)
    assert len(base) == len(arm) == 2
    assert matched.transitions(base, arm) == {
        "crew_only -> crew_only": 1,
        "quiet -> crew_only": 1,
    }


def test_a_cell_only_artifact_is_refused_because_it_has_no_voyages(tmp_path):
    artifact = (
        Path(matched.REPO_ROOT) / "telemetry_buffer" / "dutyexcl_cells_only.json"
    )
    artifact.write_text(json.dumps({"points": [{"point_index": 0, "cell": {}}]}))
    try:
        with pytest.raises(ValueError, match="keeps no voyage rows"):
            matched.load_points(artifact)
    finally:
        artifact.unlink()


def test_the_arms_of_the_analysed_campaign_are_the_same_size_and_paired():
    record = json.loads(ANALYSIS.read_text())
    pooled = record["pooled"]
    assert pooled["baseline"]["n_voyages"] == pooled["exclusion"]["n_voyages"] == 17280
    assert len(record["per_point"]) == 12
    assert all(point["baseline"]["n_voyages"] == 1440 for point in record["per_point"])


def test_the_measured_exclusion_arm_does_not_reach_a9s_posting_target():
    record = json.loads(ANALYSIS.read_text())
    ceiling = record["targets"]["A9_posting_frequency"][1]
    for arm in ("baseline", "exclusion"):
        assert record["pooled"][arm]["posting_interval_95"][0] > ceiling


def test_the_recorded_transitions_account_for_every_matched_voyage():
    record = json.loads(ANALYSIS.read_text())
    for cell in [record["pooled"], *record["per_point"]]:
        assert sum(cell["transitions"].values()) == cell["baseline"]["n_voyages"]
