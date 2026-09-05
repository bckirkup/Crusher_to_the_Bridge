"""Behavioural tests for the joint level/A7c scorer (task #11).

The properties under test are the ones that make A7c evidence rather than
decoration: the fit cannot see the post arm, the arms are selected by VSP's own
posting rule, A7c responds to the contrast in the right direction and by the
right magnitude, and an empty admissible region is reported rather than
repaired.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from telemetry_buffer.observation_model import era_joint_scoring as joint
from telemetry_buffer.observation_model.era_configuration_sets import (
    swept_lever_names,
)

PRE_COORDINATES = {"hvac.filter_efficiency": 0.5}
POST_COORDINATES = {name: 0.5 for name in swept_lever_names("post")}

# The one all-PASS pre-2020 cell used below: a single 3-day outbreak voyage in
# 200, whose reported rates satisfy A4, A5, A8 and A9 at once.  It is arranged
# by arithmetic, not fitted: A9 fixes the posted share, A8 then fixes the
# reported rates given the voyage length, and A4 and A5 are checked afterwards.
OUTBREAK_PAX_RATE = 0.095
OUTBREAK_CREW_RATE = 0.037
CELL_SEEDS = 200


def _row(
    *,
    era: str,
    dose: float = 1.0,
    hull: str = "expedition_cruise_450",
    coordinates: dict[str, float] | None = None,
    reported_pax: float = 0.0,
    reported_crew: float = 0.0,
    took_off: bool = False,
    voyage_days: float = 3.0,
    passenger_complement: int = 300,
    crew_complement: int = 150,
) -> dict[str, Any]:
    """One scorer row, in the shape ``score_anchors.read_rows`` produces."""
    ever_ill = 0.15 if took_off else 0.0
    infected = 0.20 if took_off else 0.0
    if coordinates is None:
        coordinates = PRE_COORDINATES if era == "pre" else POST_COORDINATES
    return {
        "run_id": f"{era}-{dose}-{reported_pax}-{took_off}-{voyage_days}",
        "hull": hull,
        "strategy": "syndromic",
        "era": era,
        "era_coordinates": dict(coordinates),
        "dose_adjustment": dose,
        "sick_call_probability": 1.0,
        "took_off": took_off,
        "voyage_days": voyage_days,
        "passenger_complement": passenger_complement,
        "crew_complement": crew_complement,
        "A1_ever_ill_passenger": ever_ill,
        "infection_attack_rate_passenger": infected,
        "infection_attack_rate_crew": infected,
        "ever_ill_attack_rate_crew": ever_ill,
        "A2_ill_per_infected": 0.75 if took_off else None,
        "A3_reported_per_symptomatic": (
            reported_pax / ever_ill if ever_ill else None
        ),
        "A5_passenger_crew_ratio": (
            reported_pax / reported_crew if reported_crew else None
        ),
        "reported_case_attack_rate_passenger": reported_pax,
        "reported_case_attack_rate_crew": reported_crew,
        "vsp_trigger_epoch": 10 if reported_pax >= 0.03 else None,
        "_source_path": f"{era}.zip",
    }


def _arm(
    era: str,
    *,
    dose: float = 1.0,
    pax_rate: float = OUTBREAK_PAX_RATE,
    crew_rate: float = OUTBREAK_CREW_RATE,
    coordinates: dict[str, float] | None = None,
    seeds: int = CELL_SEEDS,
) -> list[dict[str, Any]]:
    """One era arm: a single outbreak voyage among ``seeds`` quiet ones."""
    outbreak = _row(
        era=era,
        dose=dose,
        coordinates=coordinates,
        reported_pax=pax_rate,
        reported_crew=crew_rate,
        took_off=True,
    )
    quiet = [
        _row(era=era, dose=dose, coordinates=coordinates) | {"run_id": f"{era}-q{i}"}
        for i in range(seeds - 1)
    ]
    return [outbreak, *quiet]


def _fit_of(doses: tuple[float, ...]) -> joint.CommonDoseFit:
    return joint.CommonDoseFit(doses=doses, rejected={}, cell_verdicts={})


def test_the_fit_refuses_to_see_the_post_arm() -> None:
    rows = _arm("pre") + _arm("post")

    with pytest.raises(RuntimeError, match="expected only era 'pre'"):
        joint.fit_common_dose(rows)


def test_the_fit_refuses_an_unlabelled_arm() -> None:
    rows = [row | {"era": ""} for row in _arm("pre")]

    with pytest.raises(RuntimeError, match="expected only era 'pre'"):
        joint.fit_common_dose(rows)


def test_the_fit_refuses_a_run_that_does_not_state_its_sweep_position() -> None:
    rows = [row | {"era_coordinates": {}} for row in _arm("pre")]

    with pytest.raises(RuntimeError, match="does not state the pre sweep"):
        joint.fit_common_dose(rows)


def test_the_post_arm_must_state_every_swept_coordinate() -> None:
    partial = dict(POST_COORDINATES)
    partial.pop("ship_graph.immune_fraction")
    post = _arm("post", coordinates=partial, seeds=2)

    with pytest.raises(RuntimeError, match="ship_graph.immune_fraction"):
        joint.score_discontinuity(_fit_of((1.0,)), _arm("pre"), post)


def test_a_dose_the_pre_levels_admit_enters_the_fit() -> None:
    fit = joint.fit_common_dose(_arm("pre", dose=1.0))

    assert fit.doses == (1.0,)
    assert not fit.is_empty


def test_a_dose_whose_pre_levels_fail_is_rejected_and_the_reason_named() -> None:
    # Ten times the reported rate leaves A4, A8 and A9 all out of band.
    fit = joint.fit_common_dose(_arm("pre", pax_rate=0.95, crew_rate=0.37))

    assert fit.doses == ()
    assert fit.is_empty
    reasons = " ".join(fit.rejected[1.0])
    assert "A4_vsp_iqr" in reasons


def test_the_fit_admits_and_rejects_doses_independently() -> None:
    rows = _arm("pre", dose=1.0) + _arm(
        "pre", dose=2.0, pax_rate=0.95, crew_rate=0.37,
    )

    fit = joint.fit_common_dose(rows)

    assert fit.doses == (1.0,)
    assert 2.0 in fit.rejected


def test_the_posting_rule_keeps_only_voyages_vsp_would_have_posted() -> None:
    kept = joint.posted([
        _row(era="pre", reported_pax=0.04, took_off=True),
        _row(era="pre", reported_pax=0.02, reported_crew=0.05, took_off=True),
        _row(era="pre", reported_pax=0.02, reported_crew=0.01, took_off=True),
    ])

    assert len(kept) == 2


def test_the_posting_rule_excludes_small_and_out_of_window_voyages() -> None:
    rejected = [
        _row(
            era="pre",
            reported_pax=0.40,
            took_off=True,
            passenger_complement=80,
        ),
        _row(era="pre", reported_pax=0.40, took_off=True, voyage_days=2.0),
        _row(era="pre", reported_pax=0.40, took_off=True, voyage_days=30.0),
    ]

    assert joint.posted(rejected) == []


def test_a7c_is_one_when_both_roles_shift_together() -> None:
    pre = joint.posted(_arm("pre", pax_rate=0.10, crew_rate=0.05))
    post = joint.posted(_arm("post", pax_rate=0.05, crew_rate=0.025))

    assert joint.a7c(pre, post) == pytest.approx(1.0)


def test_a7c_falls_as_the_passenger_arm_falls_relative_to_crew() -> None:
    pre = joint.posted(_arm("pre", pax_rate=0.10, crew_rate=0.05))
    seen = [
        joint.a7c(
            pre,
            joint.posted(_arm("post", pax_rate=pax, crew_rate=0.05)),
        )
        for pax in (0.10, 0.08, 0.06)
    ]

    assert seen[0] == pytest.approx(1.0)
    assert seen[1] < seen[0]
    assert seen[2] < seen[1]


def test_a7c_is_undefined_when_the_crew_median_is_zero() -> None:
    pre = joint.posted(_arm("pre", pax_rate=0.10, crew_rate=0.0))
    post = joint.posted(_arm("post", pax_rate=0.05, crew_rate=0.0))

    assert joint.a7c(pre, post) is None


def test_a_post_point_inside_the_a7c_target_becomes_the_region() -> None:
    fit = joint.fit_common_dose(_arm("pre"))
    points = joint.score_discontinuity(
        fit,
        _arm("pre"),
        _arm("post", pax_rate=0.080, crew_rate=0.040),
    )

    assert [point.verdict for point in points] == [joint.PASS]
    assert points[0].value == pytest.approx(0.7789, abs=1e-3)
    assert len(joint.admissible_region(points)) == 1


def test_a_post_point_outside_the_a7c_target_leaves_the_region_empty() -> None:
    fit = joint.fit_common_dose(_arm("pre"))
    points = joint.score_discontinuity(
        fit,
        _arm("pre"),
        _arm("post", pax_rate=0.095, crew_rate=0.037),
    )

    assert points[0].value == pytest.approx(1.0)
    assert points[0].verdict == joint.FAIL
    assert joint.admissible_region(points) == ()


def test_an_empty_region_is_reported_as_a_result() -> None:
    fit = joint.fit_common_dose(_arm("pre"))
    points = joint.score_discontinuity(
        fit, _arm("pre"), _arm("post", pax_rate=0.095, crew_rate=0.037),
    )

    report = joint.render(fit, points)

    assert joint.EMPTY_REGION_NOTE in report


def test_a_post_point_at_a_rejected_dose_is_not_scored_at_all() -> None:
    pre = _arm("pre", pax_rate=0.95, crew_rate=0.37)
    fit = joint.fit_common_dose(pre)

    points = joint.score_discontinuity(
        fit, pre, _arm("post", pax_rate=0.08, crew_rate=0.04),
    )

    assert points[0].verdict == joint.UNSCORED_DOSE
    assert points[0].value is None
    assert joint.admissible_region(points) == ()


def test_a_post_arm_run_at_a_dose_the_pre_arm_never_ran_is_refused() -> None:
    with pytest.raises(RuntimeError, match="no pre-arm counterpart"):
        joint.score_discontinuity(
            _fit_of((1.0,)),
            _arm("pre", dose=1.0),
            _arm("post", dose=3.0, seeds=2),
        )


def test_a_fit_that_saw_more_than_the_pre_arm_cannot_score_a7c() -> None:
    tainted = joint.CommonDoseFit(
        doses=(1.0,),
        rejected={},
        cell_verdicts={},
        arms_seen=("pre", "post"),
    )

    with pytest.raises(RuntimeError, match="only evidence if the fit"):
        joint.score_discontinuity(tainted, _arm("pre"), _arm("post", seeds=2))


def test_a_post_arm_with_no_posted_voyage_scores_neither_pass_nor_fail() -> None:
    fit = joint.fit_common_dose(_arm("pre"))
    points = joint.score_discontinuity(
        fit, _arm("pre"), _arm("post", pax_rate=0.01, crew_rate=0.005),
    )

    assert points[0].n_post_posted == 0
    assert points[0].verdict == joint.NO_POSTINGS


def test_the_scored_target_is_a7c_and_contains_the_measured_value() -> None:
    low, high = joint.A7C_TARGET

    assert low <= joint.A7C_POINT_ESTIMATE <= high
    assert high < 1.0


def test_the_composition_controlled_interval_is_context_not_a_verdict() -> None:
    low, high = joint.A7C_COMPOSITION_INTERVAL

    assert low < 1.0 < high


def test_the_report_states_which_post_mechanisms_carried_no_number() -> None:
    fit = joint.fit_common_dose(_arm("pre"))
    points = joint.score_discontinuity(
        fit, _arm("pre"), _arm("post", pax_rate=0.08, crew_rate=0.04),
    )

    report = joint.render(fit, points)
    unrepresented = joint.unrepresented_mechanisms("post")

    assert unrepresented
    for name, _note in unrepresented:
        assert name in report


def test_coordinate_keys_are_order_independent() -> None:
    forward = joint.coordinate_key({"a": 0.25, "b": 0.5})
    reversed_order = joint.coordinate_key({"b": 0.5, "a": 0.25})

    assert forward == reversed_order


def _summary(era: str, coordinates: dict[str, float]) -> dict[str, Any]:
    return {
        "run_id": f"{era}-run",
        "parameters": {
            "platform_id": "expedition_cruise_450",
            "surveillance": "syndromic",
            "dose_adjustment": 1.0,
            "seed": 1,
            "num_epochs": 72,
            "num_agents": 450,
            "natural_history_clock": "hours",
            "sick_call_probability": 1.0,
            "era": era,
            "era_coordinates": coordinates,
        },
        "derived": {
            "peak_prevalence": 20,
            "passenger_complement": 300,
            "crew_complement": 150,
            "ever_ill_attack_rate_passenger": 0.15,
            "infection_attack_rate_passenger": 0.20,
            "reported_case_attack_rate_passenger": 0.095,
            "infection_attack_rate_crew": 0.20,
            "reported_case_attack_rate_crew": 0.037,
            "ever_ill_attack_rate_crew": 0.15,
            "vsp_trigger_epoch": 10,
        },
    }


def _write(root: Path, summary: dict[str, Any]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(root / "run.zip", "w") as archive:
        archive.writestr("summary.json", json.dumps(summary))


def test_score_reads_both_arms_from_disk_and_keeps_them_separate(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "pre", _summary("pre", PRE_COORDINATES))
    _write(tmp_path / "post", _summary("post", POST_COORDINATES))

    fit, points = joint.score(tmp_path / "pre", tmp_path / "post")

    assert fit.arms_seen == ("pre",)
    assert [point.coordinates for point in points] == [
        joint.coordinate_key(POST_COORDINATES),
    ]


def test_the_cli_exit_code_reports_an_empty_region(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(tmp_path / "pre", _summary("pre", PRE_COORDINATES))
    _write(tmp_path / "post", _summary("post", POST_COORDINATES))
    report = tmp_path / "report.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "era_joint_scoring",
            "--pre-root",
            str(tmp_path / "pre"),
            "--post-root",
            str(tmp_path / "post"),
            "--out",
            str(report),
        ],
    )

    assert joint.main() == 1
    assert joint.EMPTY_REGION_NOTE in report.read_text(encoding="utf-8")
