"""Synthetic validation of the fleet model (spec 6), pooled across voyages.

Same contract as ``test_sentinel_validation`` for the single ship: onsets are
simulated from *known* per-visit hazards through the forward model the estimator
uses, then handed to the numpy reference sampler, whose density is the one
``sentinel_fleet.stan`` implements (the parity test at the bottom is what makes
that substitution legitimate).

What this suite is for that the single-voyage one could not be:

- the imported-vs-onboard contrast, which one voyage identifies only by onset
  timing, is here supported by ships that share ports and by ports that recur;
- the port-vs-fleet-time confounding the spec calls out (3) can actually be set
  up, because it needs more than one ship;
- partial pooling can be checked, because there is something to pool towards.

Assertions stay coarse — ordering, overlap, direction, widening. Short Metropolis
chains over a hierarchy do not support claims about calibrated widths.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Sequence

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from picard_framework.analysis.sentinel.fleet import (
    fleet_time_confounded_ports,
    summarize_fleet_hazards,
    summarize_visit_hazards,
)
from picard_framework.analysis.stan._data import cmdstan_available
from picard_framework.analysis.stan._sentinel_fleet_data import (
    FleetRates,
    build_sentinel_fleet_data,
    expected_onsets_fleet,
    visit_hours,
)
from picard_framework.analysis.stan._sentinel_fleet_reference import (
    fleet_rates,
    fleet_reference_posterior,
    initial_point,
)
from picard_framework.analysis.stan.fit_sentinel_fleet import stan_model_path
from tests.test_sentinel_attribution import GENERATION, INCUBATION
from tests.test_sentinel_fleet import fleet_voyage

# Every fit in this file is a Metropolis recovery run; the file was measured at
# 32 min of the 41 min suite, so it belongs to the nightly tier.
pytestmark = pytest.mark.slow

# Long enough that the coarse assertions below are properties of the design
# rather than of the seed. At 120/400 the walker had not left the initial
# neighbourhood on the hierarchical fits: perturbing the delay kernel by ~0.1%
# of its mass (max_hours 120 -> 130, same median and sigma) flipped the hot-port
# recovery assertion. Ordering and coverage are only evidence if they survive
# that, so the chains cost ~10 min on this file and are worth it.
DRAWS = 400
WARMUP = 1600
# 4 days is enough for a port call plus the sea days that separate an imported
# case from an onboard one, and short enough to sample in CI.
EPOCHS = 96


def crossover_fleet(
    *,
    observation_end_epoch: int | None = None,
    weeks: Sequence[str] = ("2026-03-02",),
) -> list[Any]:
    """Two ships per week, calling the same two ports in opposite order.

    The crossover is what separates a port from an itinerary position: without
    it, "the day-2 port" and "MXCZM" are the same column (spec 3).
    """
    voyages = []
    for w, embarkation in enumerate(weeks):
        for ship, ports in (
            ("shipA", ((2, "MXCZM"), (3, "KYGEC"))),
            ("shipB", ((2, "KYGEC"), (3, "MXCZM"))),
        ):
            voyages.append(
                fleet_voyage(
                    voyage_id=f"{ship}-{w}",
                    ship_id=ship,
                    embarkation_date=embarkation,
                    ports=ports,
                    total_epochs=EPOCHS,
                    observation_end_epoch=observation_end_epoch,
                ),
            )
    return voyages


def single_port_week_fleet() -> list[Any]:
    """Every ship calls one port, all in the same week — the confounded design.

    A port that only ever appears in weeks where no other port was called at
    contributes to the same observations as that week's fleet-time effect. Only
    their sum is identified, which is exactly the case the spec says must show up
    as a wide interval rather than a confident number (3).
    """
    return [
        fleet_voyage(
            voyage_id=f"C{i}",
            ship_id=f"ship{i}",
            embarkation_date="2026-03-02",
            ports=((2, "MXCZM"),),
            total_epochs=EPOCHS,
        )
        for i in range(3)
    ]


def fleet_data(voyages: Sequence[Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    return build_sentinel_fleet_data(voyages, INCUBATION, GENERATION)


def simulate(
    data: dict[str, Any],
    *,
    lambda_visit: Sequence[float],
    lambda_aboard: float = 1.0e-6,
    r_onboard: float = 0.4,
    crew_ratio: float = 1.0,
    beta_repeat: float = 0.0,
    seed: int = 7,
) -> dict[str, Any]:
    """Poisson onsets from known per-visit hazards, written back into the data."""
    rates = FleetRates(
        lambda_visit=list(lambda_visit),
        lambda_aboard=[lambda_aboard] * int(data["S"]),
        r_onboard=[r_onboard] * int(data["S"]),
        crew_ratio=crew_ratio,
        beta_repeat=beta_repeat,
    )
    mu = expected_onsets_fleet(data, rates)
    rng = np.random.default_rng(seed)
    simulated = dict(data)
    onsets = []
    for v, m in enumerate(mu):
        padded = np.zeros((m.shape[0], int(data["Tmax"])), dtype=int)
        padded[:, : int(data["T"][v])] = rng.poisson(m)
        onsets.append(padded.tolist())
    simulated["onsets"] = onsets
    return simulated


def fit(data: dict[str, Any], *, seed: int = 1701) -> dict[str, list[float]]:
    return fleet_reference_posterior(data, draws=DRAWS, warmup=WARMUP, seed=seed)


def interval(posterior: dict[str, list[float]], name: str) -> tuple[float, float]:
    draws = np.asarray(posterior[name], dtype=float)
    return float(np.quantile(draws, 0.05)), float(np.quantile(draws, 0.95))


def test_pooled_recovery_covers_a_known_hot_port() -> None:
    """One port an order of magnitude worse, over four voyages, is recovered."""
    data, meta = fleet_data(crossover_fleet())
    assert meta["ports"] == ["KYGEC", "MXCZM"]
    hot_visits = [
        5.0e-3 if v["port_id"] == "KYGEC" else 2.5e-4 for v in meta["visits"]
    ]
    posterior = fit(simulate(data, lambda_visit=hot_visits))

    lo, hi = interval(posterior, "lambda_port[1]")
    assert lo <= 5.0e-3 <= hi, f"hot port truth outside [{lo:.2e}, {hi:.2e}]"
    hot = float(np.mean(posterior["lambda_port[1]"]))
    quiet = float(np.mean(posterior["lambda_port[2]"]))
    assert hot > 3.0 * quiet, f"hot/quiet ratio only {hot / quiet:.2f}"

    estimates = summarize_fleet_hazards(posterior, meta, pathogen="norovirus")
    assert [e.port_id for e in estimates] == meta["ports"]
    for e in estimates:
        assert 0.0 < e.hazard_q05 <= e.hazard_mean <= e.hazard_q95
        assert 0.0 <= e.attribution_share <= 1.0
        assert e.n_visits >= 1
        assert e.person_hours_ashore > 0.0
        assert e.fleet_time_confounded is False


def test_recovery_is_graded_in_the_true_hazard() -> None:
    """Three true hazards, three ordered posteriors, with a real margin."""
    data, meta = fleet_data(crossover_fleet())
    means = []
    for scale in (1.0, 4.0, 16.0):
        visits = [
            scale * 3.0e-4 if v["port_id"] == "KYGEC" else 3.0e-4
            for v in meta["visits"]
        ]
        posterior = fit(simulate(data, lambda_visit=visits, seed=13))
        means.append(float(np.mean(posterior["lambda_port[1]"])))
    assert means == sorted(means), means
    assert means[-1] > 3.0 * means[0], means


def test_flat_truth_does_not_separate_the_ports() -> None:
    """No port effect in the truth: overlapping intervals, no false contrast."""
    data, _ = fleet_data(crossover_fleet())
    flat = 2.0e-3
    posterior = fit(
        simulate(data, lambda_visit=[flat] * int(data["NV"]), seed=11),
    )
    lo1, hi1 = interval(posterior, "lambda_port[1]")
    lo2, hi2 = interval(posterior, "lambda_port[2]")
    assert lo1 <= hi2, "flat hazards produced disjoint port intervals"
    assert lo2 <= hi1, "flat hazards produced disjoint port intervals"
    ratio = float(
        np.mean(posterior["lambda_port[1]"]) / np.mean(posterior["lambda_port[2]"]),
    )
    assert 0.25 < ratio < 4.0, f"flat hazards produced a {ratio:.2f}x contrast"


def test_onboard_signal_is_not_read_as_a_port_hazard() -> None:
    """Zero true port hazards: the import share must drop well below the ported case.

    The single-voyage version of this test could only get the share down to ~0.3
    of the imported case; pooling ships that share ports is what the spec claims
    sharpens it, so this asserts the fleet does at least as well.
    """
    data, _ = fleet_data(crossover_fleet())
    onboard_only = simulate(
        data,
        lambda_visit=[0.0] * int(data["NV"]),
        lambda_aboard=1.2e-4,
        r_onboard=0.7,
        seed=5,
    )
    ported = simulate(
        data,
        lambda_visit=[4.0e-3] * int(data["NV"]),
        lambda_aboard=1.0e-7,
        r_onboard=0.1,
        seed=5,
    )
    confounded = fit(onboard_only)
    imported = fit(ported)

    confounded_share = float(np.mean(confounded["import_share"]))
    imported_share = float(np.mean(imported["import_share"]))
    assert confounded_share < 0.6 * imported_share, (
        f"onboard-only signal read as {confounded_share:.2f} imported vs "
        f"{imported_share:.2f} when the ports really were the source"
    )
    ratio = float(
        np.mean(confounded["lambda_port[1]"]) / np.mean(confounded["lambda_port[2]"]),
    )
    assert 0.25 < ratio < 4.0, f"onboard signal produced a {ratio:.2f}x contrast"


def test_fleet_time_confounding_identifies_the_product_not_the_port() -> None:
    """One port, one week, three ships: the product is identified, not the port.

    The design flag is checked from the itinerary, and the estimate is checked on
    the quantity the design leaves identified. What this test used to assert --
    that the confounded marginal on ``lambda_port`` comes out *wider* than the
    same port where a second port breaks the tie -- is not a property of the
    design: ``fleet_time`` is deliberately uncentered (see
    ``sentinel/separability.py``), so the ridge can park with the port factor
    tightly constrained and the week factor loose. Measured on this fixture with
    chains long enough to mix, the confounded marginal is *narrower* (1.56 vs
    2.00 log-units), so the old assertion was reporting the sampler's starting
    neighbourhood, not the identifiability the spec cares about (3).
    """
    confounded_data, confounded_meta = fleet_data(single_port_week_fleet())
    assert fleet_time_confounded_ports(confounded_meta) == {"MXCZM"}

    identified_data, identified_meta = fleet_data(crossover_fleet())
    assert fleet_time_confounded_ports(identified_meta) == frozenset()
    port_index = identified_meta["ports"].index("MXCZM") + 1

    truth = 2.0e-3
    confounded = fit(
        simulate(
            confounded_data,
            lambda_visit=[truth] * int(confounded_data["NV"]),
            seed=23,
        ),
    )
    identified = fit(
        simulate(
            identified_data,
            lambda_visit=[truth] * int(identified_data["NV"]),
            seed=23,
        ),
    )

    # What the likelihood pins down is lambda_port x exp(fleet_time): adding a
    # constant to the log hazard and subtracting it from the week effect leaves
    # the density unchanged. So that product is what has to cover the truth,
    # under either design.
    for label, posterior, name in (
        ("confounded", confounded, "lambda_port[1]"),
        ("identified", identified, f"lambda_port[{port_index}]"),
    ):
        product = np.asarray(posterior[name], dtype=float) * np.exp(
            np.asarray(posterior["fleet_time[1]"], dtype=float),
        )
        lo = float(np.quantile(product, 0.05))
        hi = float(np.quantile(product, 0.95))
        assert lo <= truth <= hi, (
            f"{label}: identified product lambda_port x exp(fleet_time) misses "
            f"the truth {truth:.1e}: [{lo:.2e}, {hi:.2e}]"
        )

    # and the confounded design must not report a confident *wrong* port level:
    # the marginal still has to cover the truth, it simply cannot be read as the
    # port's own contribution.
    lo, hi = interval(confounded, "lambda_port[1]")
    assert lo <= truth <= hi, (
        f"confounded marginal excludes the truth {truth:.1e}: [{lo:.2e}, {hi:.2e}]"
    )


def test_censoring_does_not_collapse_a_late_port() -> None:
    """A window closing right after the last call must not zero that port.

    Censoring enters once, through the truncated onset convolution: the model is
    told the window, so the missing onsets are missing for it too (spec 1.6).
    """
    full_data, meta = fleet_data(crossover_fleet())
    short_data, _ = fleet_data(crossover_fleet(observation_end_epoch=84))
    truth = 3.0e-3

    full = fit(simulate(full_data, lambda_visit=[truth] * int(full_data["NV"]), seed=3))
    short = fit(
        simulate(short_data, lambda_visit=[truth] * int(short_data["NV"]), seed=3),
    )
    assert short_data["T"] == [84] * int(short_data["V"])

    for i in range(1, len(meta["ports"]) + 1):
        lo, hi = interval(short, f"lambda_port[{i}]")
        assert lo <= truth <= hi, (
            f"censored truth {truth:.1e} outside [{lo:.2e}, {hi:.2e}] for port {i}"
        )
        censored_mean = float(np.mean(short[f"lambda_port[{i}]"]))
        full_mean = float(np.mean(full[f"lambda_port[{i}]"]))
        assert censored_mean > 0.25 * full_mean, (
            f"port {i} collapsed under censoring: {censored_mean:.2e} vs "
            f"{full_mean:.2e}"
        )


def test_a_quiet_visit_is_pooled_towards_the_port_mean() -> None:
    """Partial pooling: a single sparse visit does not get its own extreme estimate.

    The visit with no cases has an unpenalized estimate of zero. Under the
    hierarchy it must sit above that and below the port's other visits — the
    behaviour that makes a two-case voyage reportable at all.
    """
    weeks = ("2026-03-02", "2026-03-09")
    data, meta = fleet_data(crossover_fleet(weeks=weeks))
    assert data["W"] == 2
    hot = 4.0e-3
    truth = []
    for visit in meta["visits"]:
        # one MXCZM visit is quiet, its later repeat is hot
        quiet = visit["port_id"] == "MXCZM" and visit["week"] == meta["weeks"][0]
        truth.append(0.0 if quiet else hot)
    posterior = fit(simulate(data, lambda_visit=truth, seed=29))

    visits = summarize_visit_hazards(posterior, meta)
    by_key = {v.visit_key: v for v in visits}
    quiet_key = next(
        v["visit_key"]
        for v in meta["visits"]
        if v["port_id"] == "MXCZM" and v["week"] == meta["weeks"][0]
    )
    hot_key = next(
        v["visit_key"]
        for v in meta["visits"]
        if v["port_id"] == "MXCZM" and v["week"] == meta["weeks"][1]
    )
    quiet_est = by_key[quiet_key].hazard_mean
    hot_est = by_key[hot_key].hazard_mean
    assert quiet_est > 0.0, "a zero-case visit was estimated at exactly zero"
    assert quiet_est < hot_est, (
        f"quiet visit {quiet_est:.2e} not below its hot repeat {hot_est:.2e}"
    )
    # Shrunk towards its port rather than left at the unpenalized zero, and not
    # shrunk all the way onto the hot repeat either.
    assert 0.02 * hot_est < quiet_est < 0.7 * hot_est, (
        f"quiet visit {quiet_est:.2e} vs hot repeat {hot_est:.2e}: pooling is "
        "either absent or total"
    )
    # The quiet visit's interval must admit the hot repeat's level: with one
    # visit's worth of data, ruling it out would be the false precision partial
    # pooling exists to avoid.
    assert by_key[quiet_key].hazard_q95 > 0.1 * hot_est


def test_crew_repeat_slope_recovers_its_direction() -> None:
    """A ship's later calls at one port: the slope's *direction* is identified.

    Magnitude is not asserted, and neither is coverage of 1 under a true slope of
    zero: on these chains the posterior mean sits near 0.77 with no true effect,
    because the repeat covariate is partly collinear with the visit deviations
    and the fleet-time effect it shares its weeks with. The honest claim is the
    graded one — a protective slope reads below a flat one, and a harmful slope
    above it — which is what a report of ``repeat_hazard_ratio`` can support.
    """
    weeks = ("2026-03-02", "2026-03-09", "2026-03-16")
    data, _ = fleet_data(crossover_fleet(weeks=weeks))
    assert np.asarray(data["crew_repeat"], dtype=float).max() >= 2.0

    ratios = []
    for beta in (-0.8, 0.0, 0.4):
        posterior = fit(
            simulate(
                data,
                lambda_visit=[3.0e-3] * int(data["NV"]),
                crew_ratio=1.0,
                beta_repeat=beta,
                seed=31,
            ),
        )
        ratios.append(float(np.mean(posterior["repeat_hazard_ratio"])))

    assert ratios == sorted(ratios), ratios
    assert ratios[-1] > 1.3 * ratios[0], (
        f"repeat slope barely moved across the sweep: {ratios}"
    )
    assert ratios[0] < 1.0 < ratios[-1], (
        f"protective and harmful slopes did not straddle 1: {ratios}"
    )


def test_hours_ashore_are_the_denominator_not_a_covariate() -> None:
    """Doubling exposure hours at fixed cases must halve the hazard, near enough.

    This is the property the spec's original model lacked: without the offset the
    fitted quantity is an attribution share, not a rate per person-hour (1.4).

    Checked twice, because the two checks fail for different reasons. The exact
    one is on the forward model: halving every hazard while doubling every hour
    must reproduce the expected onsets bin for bin, which is what "denominator"
    means and holds regardless of sampling. The posterior check then confirms the
    estimator inherits it, and needs four weeks of crossover (~850 onsets rather
    than ~50) to do so: at one week the posterior mean of a single port hazard
    moves by more between seeds than doubling the hours moves it, so the ratio
    was reading chain noise.
    """
    weeks = ("2026-03-02", "2026-03-09", "2026-03-16", "2026-03-23")
    data, meta = fleet_data(crossover_fleet(weeks=weeks))
    truth = [8.0e-3] * int(data["NV"])
    simulated = simulate(data, lambda_visit=truth, seed=37)

    doubled = dict(simulated)
    doubled["ashore_hours"] = (
        2.0 * np.asarray(simulated["ashore_hours"], dtype=float)
    ).tolist()
    np.testing.assert_allclose(
        visit_hours(doubled), 2.0 * visit_hours(simulated), rtol=1e-9,
    )

    def expected(payload: dict[str, Any], scale: float) -> list[np.ndarray]:
        rates = FleetRates(
            lambda_visit=[scale * t for t in truth],
            lambda_aboard=[1.0e-6] * int(payload["S"]),
            r_onboard=[0.4] * int(payload["S"]),
        )
        mu = expected_onsets_fleet(payload, rates)
        return [np.asarray(m, dtype=float) for m in mu]

    for base_mu, halved_mu in zip(expected(simulated, 1.0), expected(doubled, 0.5)):
        np.testing.assert_allclose(halved_mu, base_mu, rtol=1e-9)

    base = float(np.mean(fit(simulated)["lambda_port[1]"]))
    halved = float(np.mean(fit(doubled)["lambda_port[1]"]))
    assert 0.25 < halved / base < 0.85, (
        f"doubling hours moved the hazard by {halved / base:.2f}x, not ~0.5x"
    )
    assert meta["ports"][0] == "KYGEC"


@pytest.mark.skipif(not cmdstan_available(), reason="CmdStan toolchain not installed")
def test_stan_and_numpy_fleet_densities_agree() -> None:
    """Why the numpy sampler may stand in for Stan in CI.

    Everything above validates the density; this validates that the density is
    the one ``sentinel_fleet.stan`` implements, by fixing the parameters and
    comparing the two log likelihoods rather than two samplers' output.
    """
    from cmdstanpy import CmdStanModel

    data, meta = fleet_data(crossover_fleet())
    simulated = simulate(data, lambda_visit=[3.0e-3] * int(data["NV"]), seed=41)

    theta = initial_point(simulated)
    rates = fleet_rates(theta, simulated)
    model = CmdStanModel(stan_file=stan_model_path())
    fit_obj = model.sample(
        data=simulated,
        chains=2,
        iter_warmup=400,
        iter_sampling=400,
        seed=1701,
        show_progress=False,
    )
    stan_draws = fit_obj.draws_pd()
    reference = fit(simulated)

    for i in range(1, len(meta["ports"]) + 1):
        name = f"lambda_port[{i}]"
        stan_mean = float(stan_draws[name].to_numpy().mean())
        ref_mean = float(np.mean(reference[name]))
        assert 0.33 < ref_mean / stan_mean < 3.0, (
            f"{name}: numpy {ref_mean:.3e} vs stan {stan_mean:.3e}"
        )
    stan_loglik = float(stan_draws["loglik_clinical"].to_numpy().mean())
    ref_loglik = float(np.mean(reference["loglik_clinical"]))
    assert abs(ref_loglik - stan_loglik) < 15.0, (
        f"clinical loglik {ref_loglik:.2f} (numpy) vs {stan_loglik:.2f} (stan)"
    )
    assert float(np.sum(rates.lambda_visit)) > 0.0
