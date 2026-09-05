"""The composite Theta fit and the held-out scoring (#34).

Everything a full-length hull run would cost is kept out of these tests by
injecting a runner: the fit machinery takes a callable that returns one hull's
observables, so the tests can hand it a stub whose observables are a known
function of Theta. What is then tested is the discipline rather than the
epidemiology — that the split is enforced in both directions, that the fit is
one-dimensional and reproducible, that a boundary winner is reported as pinned,
that held-out anchors cannot reach the objective, that the composite is never
attributed to either of its factors, and that the scored quantities come from
observation logs rather than from the truth channel.
"""

from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from picard_framework.covid_fit_targets import (
    HELD_OUT,
    TRAINING,
    load_fit_targets,
    targets_path,
)
from picard_framework.covid_theta_fit import (
    DECLARED_ASSUMPTIONS,
    EMISSION_BRACKET_COPIES_PER_EPOCH,
    FIT_CONTRACT,
    PER_COPY_RISK,
    HullObservables,
    ThetaObjective,
    build_fit_run_spec,
    candidate_grid,
    fit_theta,
    implied_per_copy_risk,
    load_covid_profile,
    observables_from_modality,
    score_held_out,
    theta_profile_overrides,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DIAMOND = "diamond_princess_2020"
MORTIMER = "greg_mortimer_2020"
TRUE_THETA = 1e9
# The stub reproduces the training anchors exactly at TRUE_THETA and overshoots
# them as it saturates, so the objective has an interior minimum to find.
SATURATION = 1.0 - math.exp(-1.0)


@pytest.fixture(scope="module")
def targets():
    return load_fit_targets()


@pytest.fixture(scope="module")
def profile():
    return load_covid_profile()


# ── the split, in both directions ─────────────────────────────────────────

def test_split_declares_the_hulls_and_anchors_it_was_fixed_with(targets):
    assert targets.split["fixed_before_implementation"] is True
    assert [a.anchor_id for a in targets.training()] == [
        "covid.T1", "covid.T2", "covid.T3", "covid.T4",
    ]
    assert [a.anchor_id for a in targets.held_out()] == [
        "covid.H1", "covid.H2", "covid.H3", "covid.H4",
    ]
    assert targets.objective_anchor_ids == ("covid.T1", "covid.T3")


@pytest.mark.parametrize("anchor_id", ["covid.H1", "covid.H2", "covid.H3", "covid.H4"])
def test_a_held_out_anchor_cannot_be_reached_from_a_fit(targets, anchor_id):
    with pytest.raises(ValueError, match="held_out"):
        targets.assert_fittable(anchor_id)


@pytest.mark.parametrize("anchor_id", ["covid.T2", "covid.T4"])
def test_a_training_diagnostic_is_not_an_objective_term(targets, anchor_id):
    with pytest.raises(ValueError, match="diagnostic"):
        targets.assert_fittable(anchor_id)


def test_every_anchor_carries_its_source_and_grade(targets):
    for anchor in targets.anchors:
        assert anchor.source.strip()
        assert anchor.evidence_grade.strip()
        assert anchor.channel.strip()


def test_no_anchor_scores_a_truth_channel(targets):
    """Truth-channel names are what an anchor may never be scored against."""
    forbidden = {
        "cumulative_ever_infected", "cumulative_ever_ill", "truth",
        "infection_attack_rate_passenger", "true_positive_ids",
    }
    for anchor in targets.anchors:
        assert anchor.channel not in forbidden


def test_the_objective_refuses_a_held_out_hull(targets):
    with pytest.raises(ValueError, match="held out|held_out|Diamond"):
        ThetaObjective(
            targets=targets, runner=_stub_runner, scenario_id=MORTIMER,
        )


# ── the fitted quantity is one composite ──────────────────────────────────

def test_the_contract_fits_one_composite_and_no_beta():
    assert FIT_CONTRACT["fitted_dimension"] == 1
    assert FIT_CONTRACT["beta"] is None
    assert FIT_CONTRACT["per_copy_risk"] is None
    assert FIT_CONTRACT["attribution_to_either_factor"] is None
    assert PER_COPY_RISK is None
    assert FIT_CONTRACT["emission_bracket_copies_per_epoch"] == [4.2e3, 5.8e7]


def test_every_declared_assumption_says_where_it_came_from():
    assert DECLARED_ASSUMPTIONS
    for assumption in DECLARED_ASSUMPTIONS:
        assert assumption.value.strip()
        assert assumption.evidence_grade.strip()
        assert len(assumption.source.strip()) > 20


def test_the_implied_per_copy_risk_is_an_interval_not_a_value():
    low, high = implied_per_copy_risk(1e7)
    assert low < high
    assert math.isclose(low, 1e7 / EMISSION_BRACKET_COPIES_PER_EPOCH[1])
    assert math.isclose(high, 1e7 / EMISSION_BRACKET_COPIES_PER_EPOCH[0])
    # The interval spans the bracket's four orders of magnitude, which is the
    # reason it is reported rather than adopted.
    assert high / low > 1e3


# ── Theta enters on one axis ──────────────────────────────────────────────

def test_theta_is_the_only_scale_the_overrides_move(profile):
    low = theta_profile_overrides(profile, 1e6)
    high = theta_profile_overrides(profile, 1e9)
    assert low["shedding_curve_log10"] == high["shedding_curve_log10"]
    assert low["dose_adjustment"] == pytest.approx(0.0)
    assert high["dose_adjustment"] == pytest.approx(0.0)
    assert low["dose_response"]["k"] < high["dose_response"]["k"]
    assert low["dose_response"]["model"] == "exponential"


def test_the_shedding_curve_keeps_its_shape_and_its_measured_offset(profile):
    overrides = theta_profile_overrides(profile, 1e8)
    curve = overrides["shedding_curve_log10"]
    source = [float(v) for v in profile["shedding_curve_log10"]]
    assert max(curve) == pytest.approx(0.0)
    # Shape preserved: every day sits the same distance below the peak.
    peak = max(source)
    assert curve == pytest.approx([round(v - peak, 6) for v in source])
    # Both curves shift by the same amount, so the measured symptomatic /
    # asymptomatic separation survives the normalisation.
    asymptomatic = overrides["asymptomatic_shedding_log10"]
    source_asym = [float(v) for v in profile["asymptomatic_shedding_log10"]]
    assert [
        round(a - b, 6) for a, b in zip(asymptomatic, curve, strict=True)
    ] == pytest.approx([
        round(a - b, 6) for a, b in zip(source_asym, source, strict=True)
    ])


@pytest.mark.parametrize("theta", [0.0, -1.0, float("nan"), float("inf")])
def test_a_non_positive_or_non_finite_theta_is_refused(profile, theta):
    with pytest.raises(ValueError):
        theta_profile_overrides(profile, theta)


def test_the_run_spec_carries_the_declared_assumptions():
    raw = build_fit_run_spec(DIAMOND, 1e8, 7, num_epochs=24)
    overrides = raw["config_overrides"]
    assert overrides["wearable_monitoring"]["enabled"] is False
    assert overrides["diagnostic_cascade"]["enabled"] is False
    assert overrides["ship_graph"]["immune_fraction"] == pytest.approx(0.0)
    assert raw["run"]["history_retention"] == "compact"
    dose = raw["pathogen_overrides"]["sars_cov2_resp"]["dose_response"]
    assert dose == {"model": "exponential", "k": 1e8}


# ── the grid ──────────────────────────────────────────────────────────────

def test_the_grid_is_log_spaced_and_spans_its_bounds():
    grid = candidate_grid(1e6, 1e10, 5)
    assert len(grid) == 5
    assert grid[0] == pytest.approx(1e6)
    assert grid[-1] == pytest.approx(1e10)
    ratios = [b / a for a, b in zip(grid[:-1], grid[1:], strict=True)]
    assert ratios == pytest.approx([ratios[0]] * len(ratios))
    assert all(math.isfinite(t) for t in grid)
    assert all(t > 0 for t in grid)


@pytest.mark.parametrize(
    ("low", "high", "count"),
    [(1e6, 1e10, 1), (0.0, 1e10, 3), (1e10, 1e6, 3), (-1.0, 1.0, 3)],
)
def test_a_degenerate_grid_is_refused(low, high, count):
    with pytest.raises(ValueError):
        candidate_grid(low, high, count)


# ── the fit, on a stub whose response is known ────────────────────────────
#
# The stub is a monotone, saturating response of the scored channels to Theta,
# which is the qualitative shape a dose-response hazard has. It is not a model
# of the hulls and no epidemiological claim is made from it: it exists so the
# selection rule can be tested without a 32-day voyage per candidate.

def _stub_observables(scenario_id: str, theta: float, seed: int) -> HullObservables:
    reach = (1.0 - math.exp(-float(theta) / TRUE_THETA)) / SATURATION
    onsets = round(197 * reach)
    positives = round(634 * reach)
    return HullObservables(
        scenario_id=scenario_id,
        theta=float(theta),
        seed=int(seed),
        recorded_onsets=onsets,
        onsets_before_split_day=round(onsets * 34 / 197),
        onsets_on_or_after_split_day=onsets - round(onsets * 34 / 197),
        passenger_onsets_before=round(onsets * 0.4),
        passenger_onsets_after=round(onsets * 0.1),
        crew_onsets_before=round(onsets * 0.05),
        crew_onsets_after=round(onsets * 0.05),
        campaign_specimens=3063 if scenario_id == DIAMOND else 217,
        campaign_positives=positives if scenario_id == DIAMOND else round(
            128 * reach,
        ),
        campaign_asymptomatic_positives=round(
            (positives if scenario_id == DIAMOND else 128 * reach)
            * (0.5 if scenario_id == DIAMOND else 0.81),
        ),
    )


def _stub_runner(scenario_id: str, theta: float, seed: int) -> HullObservables:
    return _stub_observables(scenario_id, theta, seed)


@pytest.fixture()
def objective(targets):
    return ThetaObjective(targets=targets, runner=_stub_runner)


def test_the_objective_sums_only_its_declared_anchors(objective):
    evaluation = objective.evaluate(TRUE_THETA, seed=7)
    assert {term.anchor_id for term in evaluation.terms} == {
        "covid.T1", "covid.T3",
    }
    assert all(math.isfinite(term.residual) for term in evaluation.terms)
    assert evaluation.loss == pytest.approx(
        sum(term.residual for term in evaluation.terms),
    )


def test_a_better_candidate_scores_a_lower_loss(objective):
    near = objective.evaluate(TRUE_THETA, seed=7).loss
    far_low = objective.evaluate(TRUE_THETA / 1e3, seed=7).loss
    far_high = objective.evaluate(TRUE_THETA * 1e3, seed=7).loss
    assert near < far_low
    assert near <= far_high


def test_the_fit_recovers_the_stub_scale_it_was_given(objective):
    grid = candidate_grid(TRUE_THETA / 1e3, TRUE_THETA * 1e3, 7)
    result = fit_theta(objective, grid, seed=11)
    assert result.theta == pytest.approx(TRUE_THETA, rel=0.5)
    assert not result.boundary_pinned
    assert len(result.evaluations) == len(grid)


def test_the_fit_is_reproducible_and_one_dimensional(objective):
    grid = candidate_grid(1e6, 1e12, 5)
    first = fit_theta(objective, grid, seed=11)
    second = fit_theta(objective, grid, seed=11)
    assert first.theta == second.theta
    assert first.loss == pytest.approx(second.loss)
    payload = first.as_dict()
    assert payload["contract"]["fitted_dimension"] == 1
    assert isinstance(payload["theta"], float)
    assert payload["contract"]["beta"] is None


def test_a_winner_at_the_grid_edge_is_reported_as_pinned(objective):
    grid = candidate_grid(TRUE_THETA * 1e3, TRUE_THETA * 1e6, 4)
    result = fit_theta(objective, grid, seed=11)
    assert result.boundary_pinned is True


def test_the_fit_result_serialises_with_its_grid_and_assumptions(objective):
    result = fit_theta(objective, candidate_grid(1e8, 1e10, 3), seed=11)
    payload = json.loads(json.dumps(result.as_dict()))
    assert len(payload["grid"]) == 3
    assert len(payload["evaluations"]) == 3
    assert payload["declared_assumptions"]
    assert payload["implied_per_copy_risk_interval"][0] < (
        payload["implied_per_copy_risk_interval"][1]
    )


# ── held-out scoring ──────────────────────────────────────────────────────

def test_held_out_scoring_runs_the_hull_the_fit_never_saw(targets):
    seen: list[str] = []

    def runner(scenario_id: str, theta: float, seed: int) -> HullObservables:
        seen.append(scenario_id)
        return _stub_observables(scenario_id, theta, seed)

    report = score_held_out(TRUE_THETA, runner, targets=targets)
    assert seen == [MORTIMER]
    verdicts = {score.anchor_id: score.verdict for score in report.scores}
    assert verdicts["covid.H1"] in {"hit", "miss"}
    assert verdicts["covid.H2"] in {"hit", "miss"}
    assert verdicts["covid.H4"] == "unscorable"


def test_held_out_scoring_is_reproducible(targets):
    first = score_held_out(TRUE_THETA, _stub_runner, targets=targets)
    second = score_held_out(TRUE_THETA, _stub_runner, targets=targets)
    assert first.as_dict() == second.as_dict()


def test_an_empty_campaign_is_undefined_and_never_a_hit(targets):
    def silent(scenario_id: str, theta: float, seed: int) -> HullObservables:
        return HullObservables(
            scenario_id=scenario_id, theta=theta, seed=seed,
            recorded_onsets=0, onsets_before_split_day=0,
            onsets_on_or_after_split_day=0, passenger_onsets_before=0,
            passenger_onsets_after=0, crew_onsets_before=0,
            crew_onsets_after=0, campaign_specimens=0, campaign_positives=0,
            campaign_asymptomatic_positives=0,
        )

    report = score_held_out(TRUE_THETA, silent, targets=targets)
    verdicts = {score.anchor_id: score.verdict for score in report.scores}
    assert verdicts["covid.H1"] == "undefined"
    assert verdicts["covid.H2"] == "undefined"
    assert verdicts["covid.H3"] == "undefined"


def test_a_held_out_miss_is_recorded_rather_than_absorbed(targets):
    def weak(scenario_id: str, theta: float, seed: int) -> HullObservables:
        return replace(
            _stub_observables(scenario_id, theta, seed),
            campaign_positives=4,
            campaign_asymptomatic_positives=2,
        )

    report = score_held_out(TRUE_THETA, weak, targets=targets)
    verdicts = {score.anchor_id: score.verdict for score in report.scores}
    assert verdicts["covid.H1"] == "miss"
    assert report.as_dict()["split_preserved"] is True


# ── the observables come from the observation logs ────────────────────────

class _StubSyndromic:
    """A stand-in for the observation modality's two COVID channels."""

    def __init__(self, curve, specimens):
        self._curve = curve
        self._specimens = specimens

    def onset_observation_curve(self, pathogen_id: str):
        return self._curve

    def campaign_specimen_log(self, pathogen_id: str):
        return self._specimens


def test_observables_read_the_onset_curve_and_the_specimen_log():
    curve = {
        14: {"passenger": 3, "crew": 1},
        17: {"passenger": 5, "crew": 2},
        20: {"passenger": 1, "crew": 4},
    }
    specimens = [
        {"positive": True, "symptomatic_at_specimen": False},
        {"positive": True, "symptomatic_at_specimen": True},
        {"positive": False, "symptomatic_at_specimen": False},
    ]
    obs = observables_from_modality(
        _StubSyndromic(curve, specimens),
        scenario_id=DIAMOND, theta=1e8, seed=3,
        split_day=17, turn_day=17, window_days=7,
    )
    assert obs.recorded_onsets == 16
    assert obs.onsets_before_split_day == 4
    assert obs.onsets_on_or_after_split_day == 12
    assert obs.passenger_onsets_before == 3
    assert obs.passenger_onsets_after == 6
    assert obs.crew_onsets_before == 1
    assert obs.crew_onsets_after == 6
    assert obs.campaign_specimens == 3
    assert obs.campaign_positives == 2
    assert obs.campaign_asymptomatic_positives == 1
    assert obs.positive_share == pytest.approx(2 / 3)
    assert obs.asymptomatic_share == pytest.approx(0.5)


def test_shares_are_undefined_rather_than_zero_without_specimens():
    obs = observables_from_modality(
        _StubSyndromic({}, []),
        scenario_id=DIAMOND, theta=1e8, seed=3, split_day=17, turn_day=16,
    )
    assert obs.positive_share is None
    assert obs.asymptomatic_share is None
    assert obs.recorded_onsets == 0


# ── the data file ─────────────────────────────────────────────────────────

def test_the_target_file_and_the_loaded_split_agree():
    payload: dict[str, Any] = json.loads(
        Path(targets_path(str(REPO_ROOT))).read_text(encoding="utf-8"),
    )
    roles = {row["anchor_id"]: row["split_role"] for row in payload["anchors"]}
    assert roles["covid.T1"] == TRAINING
    assert roles["covid.H1"] == HELD_OUT
    assert payload["split"]["fitted_against"] == ["covid.T1", "covid.T3"]
    assert payload["split"]["fixed_before_implementation"] is True
