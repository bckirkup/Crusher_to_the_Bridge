"""Fit one composite quantity on Diamond Princess, then score hulls never seen.

The COVID arm fits exactly one number, and it is a composite. C2 was refused on
evidence (``docs/literature/consensus_tranche_25_covid_emission_beta_alias.md``):
the respiratory emission scale and the per-copy risk factor are not merely
non-identifiable from outbreak data, they are one axis, because the hazard reads
susceptibility times dose and nothing else. So the emission side stays a
bracket, the per-copy factor stays null, and what is fitted is their product::

    Theta = respiratory emission scale x per-copy risk

Theta enters the simulation through the one place that product can be
represented without splitting it: the shedding curves are reduced to their
measured *shape* (peak normalised to unity, the measured asymptomatic offset
preserved) and Theta becomes the exponential dose-response coefficient, so the
hazard is ``1 - exp(-Theta x shape-weighted dose)``. There is no second knob to
compensate with, which is the point.

What the fit is allowed to look at is enforced elsewhere:
:mod:`picard_framework.covid_fit_targets` will not hand a held-out anchor to an
objective, and :func:`picard_framework.covid_hull_scenarios.assert_fit_target`
will not hand it a held-out hull. This module runs the training hull over a
declared candidate grid, takes the best candidate, and only then calls
:func:`score_held_out`, which is the first line of code in the arm that reads
Greg Mortimer or Willebrand.

Every quantity scored is an observation channel: recorded symptom onsets and
campaign PCR results, drawn from the observation modality's own logs. Nothing
here reads the truth channel, which knows infections no shipboard record ever
held.
"""

from __future__ import annotations

import contextlib
import io
import json
import math
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from picard_framework.covid_fit_targets import FitTarget, FitTargets, load_fit_targets
from picard_framework.covid_hull_scenarios import (
    REPO_ROOT,
    build_run_spec_dict,
    load_hull_scenarios,
)
from picard_framework.run_spec import PicardRunSpec
from simulation_utils.paths import validated_open

PATHOGEN_ID = "sars_cov2_resp"
PROFILE_REL = os.path.join("data", "pathogens", "active_profiles.json")

# Emission side: a bracket, Grade B, and it stays a bracket. Attributing the
# fitted composite to this factor is exactly the move tranche 25 refused.
EMISSION_BRACKET_COPIES_PER_EPOCH: tuple[float, float] = (4.2e3, 5.8e7)
EMISSION_BRACKET_GRADE = "B"
EMISSION_BRACKET_SOURCE = (
    "docs/literature/consensus_tranche_25_covid_emission_beta_alias.md: "
    "respiratory emission of SARS-CoV-2 RNA copies per epoch, bracketed "
    "across measured exhaled-breath and aerosol studies."
)
# Per-copy risk: null. Not fitted here, not sourced here, not inferred from the
# composite. The register row that once prescribed an endpoint is inadmissible.
PER_COPY_RISK: None = None


@dataclass(frozen=True)
class DeclaredAssumption:
    """One thing the fit assumes rather than sources, said out loud."""

    name: str
    value: str
    evidence_grade: str
    source: str


# Degrees of freedom, in full. One fitted scalar; everything else below is an
# assumption of the run construction or the observation layer, declared here so
# that a reader can count the free quantities without reading the code.
DECLARED_ASSUMPTIONS: tuple[DeclaredAssumption, ...] = (
    DeclaredAssumption(
        name="shedding curve enters as shape only",
        value=(
            "shedding_curve_log10 shifted so the symptomatic peak is 0; the "
            "measured asymptomatic offset is preserved by shifting both "
            "curves by the same amount"
        ),
        evidence_grade="B for the shape, from the profile's own sourced curve",
        source=(
            "data/pathogens/active_profiles.json sars_cov2_resp "
            "shedding_curve_log10 / asymptomatic_shedding_log10"
        ),
    ),
    DeclaredAssumption(
        name="dose_adjustment folded into Theta",
        value="dose_adjustment = 0 while Theta is fitted",
        evidence_grade="declared, not sourced",
        source=(
            "The respiratory arm's inherited dose_adjustment is an "
            "emission-side scalar of the previous dose representation. "
            "Leaving it in place would put a second multiplier on the one "
            "axis Theta occupies, which would make the composite "
            "unidentifiable against itself."
        ),
    ),
    DeclaredAssumption(
        name="immunologically naive population",
        value="ship_graph.immune_fraction = 0.0",
        evidence_grade="A",
        source=(
            "SARS-CoV-2 in February 2020: no prior population immunity "
            "existed to a pathogen first reported eight weeks earlier. The "
            "engine's inherited default immune fraction is a cruise-era "
            "figure for endemic pathogens and is wrong for this event."
        ),
    ),
    DeclaredAssumption(
        name="instruments the hulls did not carry are off",
        value="wearable_monitoring and diagnostic_cascade disabled",
        evidence_grade="A",
        source=(
            "Neither 2020 hull carried wearable monitors or a tiered "
            "diagnostic cascade; the record is a testing campaign and a "
            "clinical log. Leaving them on would add case-finding no "
            "observer had."
        ),
    ),
    DeclaredAssumption(
        name="asymptomatic means asymptomatic at specimen",
        value=(
            "campaign specimens are scored asymptomatic when no symptom "
            "onset had been recorded for that host by the day of the swab"
        ),
        evidence_grade="A - matches how both sources define it",
        source=(
            "Mizumoto 2020 (320/634 at confirmation) and Ing 2020 "
            "(104/128 at the time of testing) both report shares at "
            "testing, not final outcome shares."
        ),
    ),
    DeclaredAssumption(
        name="onset denominator is the recorded-onset subset",
        value=(
            "the onset channel counts laboratory-confirmed hosts presenting "
            "a syndrome-eligible severity, not every confirmed case"
        ),
        evidence_grade="A",
        source=(
            "The published Diamond Princess curve dates 197 of the cases; "
            "the rest had onset imputed. covid_trajectory_fit_spec.md "
            "section 8 records the identification."
        ),
    ),
)

FIT_CONTRACT: dict[str, Any] = {
    "fitted_quantity": "Theta = respiratory emission scale x per-copy risk",
    "fitted_dimension": 1,
    "fitted_against_hull": "diamond_princess_2020",
    "attribution_to_either_factor": None,
    "emission_bracket_copies_per_epoch": list(EMISSION_BRACKET_COPIES_PER_EPOCH),
    "emission_bracket_evidence_grade": EMISSION_BRACKET_GRADE,
    "per_copy_risk": PER_COPY_RISK,
    "beta": PER_COPY_RISK,
    "refusals": (
        "The composite is never split into its factors, and no value of "
        "beta is reported: the two factors enter the hazard as a product, "
        "so outbreak data cannot separate them and this arm does not "
        "pretend to.",
    ),
}


def profile_path(repo_root: str = REPO_ROOT) -> str:
    return os.path.join(repo_root, PROFILE_REL)


def load_covid_profile(repo_root: str = REPO_ROOT) -> dict[str, Any]:
    """The sars_cov2_resp profile, as published in the active bundle."""
    with validated_open(
        profile_path(repo_root), allowed_roots=(repo_root,), encoding="utf-8",
    ) as handle:
        payload = json.load(handle)
    for entry in payload.get("pathogens") or ():
        if entry.get("pathogen_id") == PATHOGEN_ID:
            return dict(entry)
    raise KeyError(f"{PATHOGEN_ID} missing from {PROFILE_REL}")


def theta_profile_overrides(
    profile: dict[str, Any],
    theta: float,
) -> dict[str, Any]:
    """Profile overrides that put Theta on the one axis it occupies.

    The emission curves keep their measured shape and their measured
    symptomatic/asymptomatic separation; only their scale moves, and it moves
    as part of the composite rather than as an emission figure of its own.
    """
    theta = float(theta)
    if not math.isfinite(theta) or theta <= 0.0:
        raise ValueError(f"Theta must be finite and positive, got {theta!r}")
    symptomatic = [float(v) for v in profile["shedding_curve_log10"]]
    asymptomatic = [
        float(v) for v in profile.get(
            "asymptomatic_shedding_log10", symptomatic,
        )
    ]
    peak = max(symptomatic)
    return {
        "shedding_curve_log10": [round(v - peak, 6) for v in symptomatic],
        "asymptomatic_shedding_log10": [
            round(v - peak, 6) for v in asymptomatic
        ],
        "dose_adjustment": 0.0,
        "dose_response": {"model": "exponential", "k": theta},
    }


def implied_per_copy_risk(theta: float) -> tuple[float, float]:
    """The per-copy factor the emission bracket would imply, as an interval.

    Reported, never adopted: this is what the composite means *if* the
    emission side sits somewhere in its Grade B bracket, and it is an
    interval precisely because the composite cannot be attributed to either
    factor. It is not a fitted beta and must not be quoted as one.
    """
    low, high = EMISSION_BRACKET_COPIES_PER_EPOCH
    return (float(theta) / high, float(theta) / low)


# ── observables ───────────────────────────────────────────────────────────
#
# Everything below is read from the observation modality's own logs: the
# recorded-onset channel and the campaign specimen log. The truth channel is
# not consulted, so a host the campaign never swabbed and who never presented
# is invisible here, exactly as it was to the ships.

@dataclass(frozen=True)
class HullObservables:
    """What an observer of one simulated hull would have written down."""

    scenario_id: str
    theta: float
    seed: int
    recorded_onsets: int
    onsets_before_split_day: int
    onsets_on_or_after_split_day: int
    passenger_onsets_before: int
    passenger_onsets_after: int
    crew_onsets_before: int
    crew_onsets_after: int
    campaign_specimens: int
    campaign_positives: int
    campaign_asymptomatic_positives: int

    @property
    def positive_share(self) -> float | None:
        if self.campaign_specimens <= 0:
            return None
        return self.campaign_positives / self.campaign_specimens

    @property
    def asymptomatic_share(self) -> float | None:
        if self.campaign_positives <= 0:
            return None
        return self.campaign_asymptomatic_positives / self.campaign_positives

    def as_dict(self) -> dict[str, Any]:
        payload = {
            key: getattr(self, key) for key in (
                "scenario_id", "theta", "seed", "recorded_onsets",
                "onsets_before_split_day", "onsets_on_or_after_split_day",
                "passenger_onsets_before", "passenger_onsets_after",
                "crew_onsets_before", "crew_onsets_after",
                "campaign_specimens", "campaign_positives",
                "campaign_asymptomatic_positives",
            )
        }
        payload["positive_share"] = self.positive_share
        payload["asymptomatic_share"] = self.asymptomatic_share
        return payload


def _onset_window_counts(
    curve: dict[int, dict[str, int]],
    split_day: int,
    window_days: int,
) -> dict[str, int]:
    """Passenger/crew recorded onsets either side of a dated turn."""
    counts = {
        "passenger_before": 0, "passenger_after": 0,
        "crew_before": 0, "crew_after": 0,
    }
    for day, roles in curve.items():
        if split_day - window_days <= day < split_day:
            side = "before"
        elif split_day <= day < split_day + window_days:
            side = "after"
        else:
            continue
        counts[f"passenger_{side}"] += int(roles.get("passenger", 0))
        counts[f"crew_{side}"] += int(roles.get("crew", 0))
    return counts


def observables_from_modality(
    syndromic: Any,
    *,
    scenario_id: str,
    theta: float,
    seed: int,
    split_day: int,
    turn_day: int,
    window_days: int = 7,
    pathogen_id: str = PATHOGEN_ID,
) -> HullObservables:
    """Read one hull's observation logs into the scored quantities."""
    curve = syndromic.onset_observation_curve(pathogen_id)
    specimens = syndromic.campaign_specimen_log(pathogen_id)
    positives = [entry for entry in specimens if entry["positive"]]
    windows = _onset_window_counts(curve, turn_day, window_days)
    return HullObservables(
        scenario_id=str(scenario_id),
        theta=float(theta),
        seed=int(seed),
        recorded_onsets=sum(
            int(roles.get("passenger", 0)) + int(roles.get("crew", 0))
            for roles in curve.values()
        ),
        onsets_before_split_day=sum(
            int(roles.get("passenger", 0)) + int(roles.get("crew", 0))
            for day, roles in curve.items() if day < split_day
        ),
        onsets_on_or_after_split_day=sum(
            int(roles.get("passenger", 0)) + int(roles.get("crew", 0))
            for day, roles in curve.items() if day >= split_day
        ),
        passenger_onsets_before=windows["passenger_before"],
        passenger_onsets_after=windows["passenger_after"],
        crew_onsets_before=windows["crew_before"],
        crew_onsets_after=windows["crew_after"],
        campaign_specimens=len(specimens),
        campaign_positives=len(positives),
        campaign_asymptomatic_positives=sum(
            1 for entry in positives if not entry["symptomatic_at_specimen"]
        ),
    )


def build_fit_run_spec(
    scenario_id: str,
    theta: float,
    seed: int,
    *,
    num_epochs: int | None = None,
    repo_root: str = REPO_ROOT,
) -> dict[str, Any]:
    """The run spec one candidate is evaluated on, assumptions included."""
    raw = build_run_spec_dict(
        scenario_id, random_seed=int(seed), num_epochs=num_epochs,
    )
    run = raw.setdefault("run", {})
    # Compact retention keeps only the scalars: the scored channels are read
    # from the modality's logs, and a full per-epoch history of a 3,711-host
    # hull exhausts memory long before the voyage ends.
    run["history_retention"] = "compact"
    overrides = raw.setdefault("config_overrides", {})
    overrides["wearable_monitoring"] = {"enabled": False}
    overrides["diagnostic_cascade"] = {"enabled": False}
    overrides.setdefault("ship_graph", {})["immune_fraction"] = 0.0
    profile = load_covid_profile(repo_root)
    raw.setdefault("pathogen_overrides", {}).setdefault(
        PATHOGEN_ID, {},
    ).update(theta_profile_overrides(profile, theta))
    return raw


def simulate_hull(
    scenario_id: str,
    theta: float,
    seed: int,
    *,
    num_epochs: int | None = None,
    repo_root: str = REPO_ROOT,
    split_day: int = 17,
    turn_day: int = 16,
) -> HullObservables:
    """Run one hull at one candidate Theta and read its observation logs."""
    from picard_framework.simulation.ship_simulation import ShipSimulation

    raw = build_fit_run_spec(
        scenario_id, theta, seed,
        num_epochs=num_epochs, repo_root=repo_root,
    )
    spec = PicardRunSpec.from_picard_dict(repo_root, raw)
    with contextlib.redirect_stdout(io.StringIO()):
        sim = ShipSimulation(spec, display=False)
        sim.initialize()
        for _ in range(sim.num_epochs):
            sim.step()
    return observables_from_modality(
        sim.modalities["syndromic"],
        scenario_id=scenario_id,
        theta=theta,
        seed=seed,
        split_day=split_day,
        turn_day=turn_day,
    )


HullRunner = Callable[[str, float, int], HullObservables]


# ── the objective ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ObjectiveTerm:
    """One anchor's contribution, in the units it was published in."""

    anchor_id: str
    quantity: str
    observed: float
    target: float
    residual: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "anchor_id": self.anchor_id,
            "quantity": self.quantity,
            "observed": self.observed,
            "target": self.target,
            "residual": self.residual,
        }


def _log_residual(observed: float, target: float) -> float:
    """Squared log-ratio: a count half the target costs what double does."""
    obs = max(float(observed), 0.5)
    return (math.log(obs / float(target))) ** 2


@dataclass(frozen=True)
class ThetaEvaluation:
    """One candidate's loss, with the terms that produced it."""

    theta: float
    seed: int
    loss: float
    terms: tuple[ObjectiveTerm, ...]
    observables: HullObservables

    def as_dict(self) -> dict[str, Any]:
        return {
            "theta": self.theta,
            "seed": self.seed,
            "loss": self.loss,
            "terms": [term.as_dict() for term in self.terms],
            "observables": self.observables.as_dict(),
        }


@dataclass(frozen=True)
class ThetaObjective:
    """The training objective: two anchors, on one hull, and nothing else."""

    targets: FitTargets
    runner: HullRunner
    scenario_id: str = "diamond_princess_2020"

    def __post_init__(self) -> None:
        scenarios = load_hull_scenarios()
        scenarios.assert_fit_target(self.scenario_id)
        # Reading the objective rows through the split enforcer means an
        # attempt to fit a held-out anchor fails here, at construction.
        self.targets.objective_anchors()

    def _onset_terms(self, obs: HullObservables) -> list[ObjectiveTerm]:
        anchor = self.targets.assert_fittable("covid.T1")
        values = anchor.values
        return [
            ObjectiveTerm(
                anchor_id=anchor.anchor_id,
                quantity="recorded_onsets",
                observed=float(obs.recorded_onsets),
                target=float(values["recorded_onsets"]),
                residual=_log_residual(
                    obs.recorded_onsets, values["recorded_onsets"],
                ),
            ),
            ObjectiveTerm(
                anchor_id=anchor.anchor_id,
                quantity="onsets_on_or_after_split_day",
                observed=float(obs.onsets_on_or_after_split_day),
                target=float(values["onsets_on_or_after_day"]),
                residual=_log_residual(
                    obs.onsets_on_or_after_split_day,
                    values["onsets_on_or_after_day"],
                ),
            ),
        ]

    def _campaign_terms(self, obs: HullObservables) -> list[ObjectiveTerm]:
        anchor = self.targets.assert_fittable("covid.T3")
        target = float(anchor.values["cumulative_positives"])
        return [
            ObjectiveTerm(
                anchor_id=anchor.anchor_id,
                quantity="campaign_positives",
                observed=float(obs.campaign_positives),
                target=target,
                residual=_log_residual(obs.campaign_positives, target),
            ),
        ]

    def terms(self, obs: HullObservables) -> tuple[ObjectiveTerm, ...]:
        """The objective's terms: covid.T1 and covid.T3, equally weighted.

        Equal weights are a declared choice, not a tuned one. The onset
        channel carries two terms because its shape is what the fit spec
        calls load-bearing: a total alone can be met by a curve of the wrong
        timing.
        """
        return tuple(self._onset_terms(obs) + self._campaign_terms(obs))

    def evaluate(self, theta: float, seed: int) -> ThetaEvaluation:
        obs = self.runner(self.scenario_id, float(theta), int(seed))
        terms = self.terms(obs)
        return ThetaEvaluation(
            theta=float(theta),
            seed=int(seed),
            loss=sum(term.residual for term in terms),
            terms=terms,
            observables=obs,
        )


def candidate_grid(
    low: float,
    high: float,
    count: int,
) -> tuple[float, ...]:
    """A log-spaced candidate grid, declared before the fit runs.

    A grid rather than a search: it is reproducible, it is reportable in
    full, and it makes a value pinned at an endpoint visible as pinned
    instead of hiding it in an optimiser's last step.
    """
    if count < 2:
        raise ValueError(f"a grid needs at least two candidates, got {count}")
    if not 0.0 < float(low) < float(high):
        raise ValueError(f"grid bounds must satisfy 0 < low < high: {low}, {high}")
    lo, hi = math.log10(float(low)), math.log10(float(high))
    step = (hi - lo) / (count - 1)
    return tuple(10.0 ** (lo + step * i) for i in range(count))


@dataclass(frozen=True)
class ThetaFitResult:
    """The fitted composite, and every candidate that lost to it."""

    theta: float
    loss: float
    seed: int
    grid: tuple[float, ...]
    evaluations: tuple[ThetaEvaluation, ...]
    boundary_pinned: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "contract": FIT_CONTRACT,
            "theta": self.theta,
            "loss": self.loss,
            "seed": self.seed,
            "grid": list(self.grid),
            "boundary_pinned": self.boundary_pinned,
            "implied_per_copy_risk_interval": list(
                implied_per_copy_risk(self.theta),
            ),
            "declared_assumptions": [
                {
                    "name": a.name, "value": a.value,
                    "evidence_grade": a.evidence_grade, "source": a.source,
                }
                for a in DECLARED_ASSUMPTIONS
            ],
            "evaluations": [ev.as_dict() for ev in self.evaluations],
        }


def fit_theta(
    objective: ThetaObjective,
    grid: Sequence[float],
    *,
    seed: int = 20200205,
) -> ThetaFitResult:
    """Evaluate the declared grid on the training hull and take the best.

    Deterministic: one seed, one candidate list, ties broken by the smaller
    Theta. A winner at either end of the grid is reported as boundary-pinned
    rather than as a fit.
    """
    candidates = tuple(float(theta) for theta in grid)
    if not candidates:
        raise ValueError("fit_theta needs at least one candidate")
    evaluations = tuple(
        objective.evaluate(theta, seed) for theta in candidates
    )
    best = min(evaluations, key=lambda ev: (ev.loss, ev.theta))
    return ThetaFitResult(
        theta=best.theta,
        loss=best.loss,
        seed=int(seed),
        grid=candidates,
        evaluations=evaluations,
        boundary_pinned=best.theta in (candidates[0], candidates[-1]),
    )


# ── held-out scoring ──────────────────────────────────────────────────────
#
# Nothing below is reachable from the objective. It runs once, on a Theta
# already fixed, and its results do not feed back: a miss here is a result to
# record, not a reason to widen an interval or re-pick a hull.

@dataclass(frozen=True)
class HeldOutScore:
    """One held-out anchor, scored or explicitly refused."""

    anchor_id: str
    quantity: str
    observed: float | None
    target: float | None
    verdict: str
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "anchor_id": self.anchor_id,
            "quantity": self.quantity,
            "observed": self.observed,
            "target": self.target,
            "verdict": self.verdict,
            "note": self.note,
        }


def _share_verdict(
    observed: float | None,
    target: float,
    tolerance: float,
) -> str:
    if observed is None:
        return "undefined"
    return "hit" if abs(observed - target) <= tolerance else "miss"


def _greg_mortimer_scores(
    obs: HullObservables,
    targets: FitTargets,
    *,
    tolerance: float = 0.1,
) -> list[HeldOutScore]:
    """covid.H1 and covid.H2, on a hull the fit never ran on."""
    h1 = targets.by_id("covid.H1")
    h2 = targets.by_id("covid.H2")
    return [
        HeldOutScore(
            anchor_id=h1.anchor_id,
            quantity="campaign positive share",
            observed=obs.positive_share,
            target=float(h1.values["share"]),
            verdict=_share_verdict(
                obs.positive_share, float(h1.values["share"]), tolerance,
            ),
            note=(
                f"{obs.campaign_positives}/{obs.campaign_specimens} campaign "
                "specimens positive. Undefined when the campaign took no "
                "specimens: a hull with no epidemic still has a test day, "
                "and reporting 0/0 as a hit would be a scoring error."
            ),
        ),
        HeldOutScore(
            anchor_id=h2.anchor_id,
            quantity="asymptomatic share among positives",
            observed=obs.asymptomatic_share,
            target=float(h2.values["share"]),
            verdict=_share_verdict(
                obs.asymptomatic_share, float(h2.values["share"]), tolerance,
            ),
            note=(
                f"{obs.campaign_asymptomatic_positives}/"
                f"{obs.campaign_positives} positives asymptomatic at the "
                "swab. Paired with covid.T4: the same biology has to give "
                "about half asymptomatic under rolling symptom-led testing "
                "and four fifths under one-shot universal testing."
            ),
        ),
    ]


def _willebrand_score(
    hulls: Sequence[HullObservables],
    targets: FitTargets,
) -> HeldOutScore:
    """covid.H3, scored as a placement question and no more than that."""
    anchor = targets.by_id("covid.H3")
    upper_quartile = float(anchor.values["iqr_attack_rate"][1])
    shares = [h.positive_share for h in hulls]
    if any(share is None for share in shares):
        return HeldOutScore(
            anchor_id=anchor.anchor_id,
            quantity="placement of both hulls above the cross-ship IQR",
            observed=None,
            target=upper_quartile,
            verdict="undefined",
            note=(
                "A hull with no campaign specimens has no attack rate, and "
                "0/0 is not a placement."
            ),
        )
    worst = min(float(share) for share in shares if share is not None)
    return HeldOutScore(
        anchor_id=anchor.anchor_id,
        quantity="placement of both hulls above the cross-ship IQR",
        observed=worst,
        target=upper_quartile,
        verdict="hit" if worst > upper_quartile else "miss",
        note=(
            "Both replayed hulls are right-tail voyages of the 104 in the "
            "distribution, so what two hulls can test is placement in the "
            "tail. The 0.2% median needs the other 102 voyages' geometries, "
            "which this repository does not have; that channel is left "
            "unscored rather than approximated."
        ),
    )


def _unscorable_score(anchor: FitTarget) -> HeldOutScore:
    return HeldOutScore(
        anchor_id=anchor.anchor_id,
        quantity=anchor.observable,
        observed=None,
        target=None,
        verdict="unscorable",
        note=anchor.notes or (
            "No instrument in the observation model measures this channel."
        ),
    )


@dataclass(frozen=True)
class HeldOutReport:
    """The held-out result, as it came out."""

    theta: float
    seed: int
    scores: tuple[HeldOutScore, ...]
    observables: tuple[HullObservables, ...] = field(default=())

    def as_dict(self) -> dict[str, Any]:
        return {
            "theta": self.theta,
            "seed": self.seed,
            "scores": [score.as_dict() for score in self.scores],
            "observables": [obs.as_dict() for obs in self.observables],
            "split_preserved": True,
        }


def score_held_out(
    theta: float,
    runner: HullRunner,
    *,
    targets: FitTargets | None = None,
    seed: int = 20200205,
    training_observables: HullObservables | None = None,
) -> HeldOutReport:
    """Score the held-out hull and the held-out aggregate at a fixed Theta.

    Called after :func:`fit_theta` has returned, with the Theta it returned.
    The held-out results are reported and nothing is refitted from them.
    """
    resolved = targets or load_fit_targets()
    scenarios = load_hull_scenarios()
    held_out_ids = scenarios.held_out_scenario_ids
    hulls = [runner(scenario_id, float(theta), int(seed))
             for scenario_id in held_out_ids]
    scores: list[HeldOutScore] = []
    for obs in hulls:
        scores.extend(_greg_mortimer_scores(obs, resolved))
    placement = list(hulls)
    if training_observables is not None:
        placement.append(training_observables)
    scores.append(_willebrand_score(placement, resolved))
    scores.append(_unscorable_score(resolved.by_id("covid.H4")))
    return HeldOutReport(
        theta=float(theta),
        seed=int(seed),
        scores=tuple(scores),
        observables=tuple(hulls),
    )
