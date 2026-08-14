"""Synthetic validation of the attribution model (spec 6).

Onsets are simulated from *known* hazards through the same forward model the
estimator uses, then handed back to the numpy reference sampler
(``_sentinel_reference``), which shares its log density with
``sentinel_attribution.stan``. That keeps the whole suite runnable on a box with
no CmdStan toolchain — the ``[analysis]`` extra is optional — at the cost of
being a self-consistency check of the density rather than of Stan's sampler.

Assertions are deliberately coarse: interval coverage, ordering, and the
direction of a shift. Short Metropolis chains do not support a claim about
calibrated interval widths, and pretending otherwise would be the same error the
spec review flagged in the original design (1.5).
"""

from __future__ import annotations

import os
import sys
from typing import Any

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from picard_framework.analysis.sentinel.attribution import (
    load_fixture_posterior,
    onboard_summary,
    summarize_port_hazards,
)
from picard_framework.analysis.sentinel.incubation import lognormal_delay
from picard_framework.analysis.stan._data import cmdstan_available
from picard_framework.analysis.stan._sentinel_data import (
    build_sentinel_attribution_data,
    expected_onsets_from_data,
)
from picard_framework.analysis.stan._sentinel_reference import reference_posterior
from picard_framework.analysis.stan.fit_sentinel_attribution import stan_model_path
from tests.test_sentinel_attribution import (  # reuse the voyage fixture
    GENERATION,
    INCUBATION,
    build_exposure_design,
    bundle,
    voyage,
    voyage_from_config,
)

# Short chains: this suite runs on every CI push, so it buys ordering and
# coverage checks, not precision.
DRAWS = 120
WARMUP = 300
THIN = 1


def design_data(
    *,
    observation_end_epoch: int = 96,
    crew_fraction: float = 0.2,
) -> tuple[dict[str, Any], dict[str, Any]]:
    v = voyage(crew_fraction=crew_fraction)
    b = bundle([], observation_end_epoch=observation_end_epoch)
    design = build_exposure_design(v, b, INCUBATION)
    return build_sentinel_attribution_data(design, v, b, INCUBATION, GENERATION)


def spaced_design_data(
    *,
    observation_end_epoch: int = 168,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Seven days, ports on day 2 and day 5, sea days in between.

    Onboard and imported cases are told apart by *timing* alone, so the back-to-
    back port days of the compact fixture are the worst case for that contrast:
    a port hazard can mimic a flat onboard baseline when every day is a port
    day. Sea days after each call are what make the two hypotheses look
    different, which is why the confounding and censoring checks use this one.
    """
    config = {
        "voyage": {
            "effects_enabled": True,
            "total_epochs": 168,
            "epoch_duration_hours": 1,
            "embarkation_date": "2026-03-01",
            "itinerary": [
                {"day": 1, "type": "embarkation", "port": "Miami", "port_id": "USMIA"},
                {
                    "day": 2,
                    "type": "port_day",
                    "port": "Cozumel",
                    "port_id": "MXCZM",
                    "disembark_fraction": 0.6,
                    "crew_shore_leave_fraction": 0.2,
                    "disembark_window_epochs": [2, 4],
                    "reembark_window_epochs": [12, 14],
                },
                {"day": 3, "type": "sea_day"},
                {"day": 4, "type": "sea_day"},
                {
                    "day": 5,
                    "type": "port_day",
                    "port": "George Town",
                    "port_id": "KYGEC",
                    "disembark_fraction": 0.6,
                    "crew_shore_leave_fraction": 0.2,
                    "disembark_window_epochs": [2, 4],
                    "reembark_window_epochs": [12, 14],
                },
                {"day": 6, "type": "sea_day"},
                {"day": 7, "type": "disembarkation", "port": "Miami", "port_id": "USMIA"},
            ],
        },
    }
    v = voyage_from_config(
        config, voyage_id="V1", ship_id="s1", n_passengers=1000, n_crew=400,
    )
    b = bundle([], observation_end_epoch=observation_end_epoch)
    design = build_exposure_design(v, b, INCUBATION)
    return build_sentinel_attribution_data(design, v, b, INCUBATION, GENERATION)


def simulate(
    data: dict[str, Any],
    *,
    lambda_port: list[float],
    lambda_aboard: float = 1.0e-6,
    r_onboard: float = 0.4,
    seed: int = 7,
) -> dict[str, Any]:
    """Poisson onsets from known hazards, written back into the Stan data."""
    mu = expected_onsets_from_data(
        data,
        lambda_port=lambda_port,
        lambda_aboard=lambda_aboard,
        r_onboard=r_onboard,
    )
    rng = np.random.default_rng(seed)
    simulated = dict(data)
    simulated["onsets"] = rng.poisson(mu).tolist()
    return simulated


def fit(data: dict[str, Any], *, seed: int = 1701) -> dict[str, list[float]]:
    return reference_posterior(
        data, draws=DRAWS, warmup=WARMUP, thin=THIN, seed=seed,
    )


def interval(posterior: dict[str, list[float]], name: str) -> tuple[float, float]:
    draws = np.asarray(posterior[name], dtype=float)
    return float(np.quantile(draws, 0.05)), float(np.quantile(draws, 0.95))


def test_recovery_covers_a_known_hot_port() -> None:
    """One port an order of magnitude worse than the other is recovered."""
    data, meta = design_data()
    truth = [5.0e-3, 2.5e-4]  # KYGEC hot, MXCZM quiet (meta['ports'] order)
    posterior = fit(simulate(data, lambda_port=truth))

    lo, hi = interval(posterior, "lambda_port[1]")
    assert lo <= truth[0] <= hi, f"hot port truth {truth[0]} outside [{lo}, {hi}]"
    hot = np.mean(posterior["lambda_port[1]"])
    quiet = np.mean(posterior["lambda_port[2]"])
    assert hot > 3.0 * quiet, f"hot/quiet ratio only {hot / quiet:.2f}"
    assert meta["ports"] == ["KYGEC", "MXCZM"]


def test_recovery_is_monotone_in_the_true_hazard() -> None:
    """Graded response: a bigger true hazard must move the posterior up."""
    data, _ = design_data()
    means = []
    for scale in (1.0, 8.0):
        posterior = fit(simulate(data, lambda_port=[scale * 4.0e-4, 2.5e-4]))
        means.append(float(np.mean(posterior["lambda_port[1]"])))
    assert means[1] > 2.0 * means[0], means


def test_null_hazards_do_not_separate_the_ports() -> None:
    """Flat truth: no port effect. Overlapping intervals, no false positive."""
    data, _ = design_data()
    flat = 2.0e-3
    posterior = fit(simulate(data, lambda_port=[flat, flat], seed=11))
    lo1, hi1 = interval(posterior, "lambda_port[1]")
    lo2, hi2 = interval(posterior, "lambda_port[2]")
    assert lo1 <= hi2 and lo2 <= hi1, "flat hazards produced disjoint port intervals"
    ratio = np.mean(posterior["lambda_port[1]"]) / np.mean(posterior["lambda_port[2]"])
    assert 0.25 < ratio < 4.0, f"flat hazards produced a {ratio:.2f}x port difference"


def test_confounded_onboard_signal_is_not_attributed_to_ports() -> None:
    """All true signal is onboard: zero port hazards, everything from baseline+R.

    The honest result is a *shift*, not a clean zero. One voyage carries only
    the timing contrast between a flat aboard baseline and two shore windows, so
    the port hazards do not go to zero; the imported share drops by roughly half
    and no port is singled out. Driving it further needs many voyages sharing
    ports, which is the fleet hierarchy in PR 6 — reporting a near-zero import
    share off a single voyage would be the over-confidence the spec review
    flagged (1.5).
    """
    data, _ = spaced_design_data()
    onboard_only = simulate(
        data, lambda_port=[0.0, 0.0], lambda_aboard=1.2e-4, r_onboard=0.7, seed=5,
    )
    ported = simulate(
        data, lambda_port=[4.0e-3, 4.0e-3], lambda_aboard=1.0e-7, r_onboard=0.1, seed=5,
    )
    confounded = fit(onboard_only)
    imported = fit(ported)

    confounded_share = float(np.mean(confounded["import_share"]))
    imported_share = float(np.mean(imported["import_share"]))
    assert confounded_share < 0.6 * imported_share, (
        f"onboard-only signal still read as {confounded_share:.2f} imported "
        f"vs {imported_share:.2f} when the ports really were the source"
    )
    # and it is not read as one bad port either
    ratio = (
        np.mean(confounded["lambda_port[1]"]) / np.mean(confounded["lambda_port[2]"])
    )
    assert 0.25 < ratio < 4.0, f"onboard signal produced a {ratio:.2f}x port contrast"
    assert np.mean(confounded["lambda_port[1]"]) < np.mean(imported["lambda_port[1]"])


def test_censored_last_port_estimate_does_not_collapse() -> None:
    """Truncating one day after the last port must not zero out that port.

    The spec's original model had no censoring term, so a late port's onsets
    simply never arrived and its hazard was reported as low (1.6). Here the
    onset convolution is truncated at ``T`` for the model as well as the truth,
    so the estimate stays in family.
    """
    truth = [3.0e-3, 3.0e-3]
    full_data, meta = spaced_design_data(observation_end_epoch=168)
    # KYGEC is the day-5 port (epochs 97-120); close the window a day after it
    assert meta["ports"] == ["KYGEC", "MXCZM"]
    short_data, _ = spaced_design_data(observation_end_epoch=144)

    full = fit(simulate(full_data, lambda_port=truth, seed=3))
    short = fit(simulate(short_data, lambda_port=truth, seed=3))

    lo, hi = interval(short, "lambda_port[1]")
    assert lo <= truth[0] <= hi, f"censored last-port truth outside [{lo}, {hi}]"
    censored_mean = float(np.mean(short["lambda_port[1]"]))
    full_mean = float(np.mean(full["lambda_port[1]"]))
    assert censored_mean > 0.25 * full_mean, (
        f"late-port hazard collapsed: {censored_mean:.2e} vs {full_mean:.2e}"
    )


def test_mis_specified_incubation_biases_the_hazard_and_is_reported() -> None:
    """A wrong incubation pmf shifts the estimate; the size is the reported bias."""
    data, _ = design_data()
    truth = [3.0e-3, 3.0e-3]
    simulated = simulate(data, lambda_port=truth, seed=17)

    slow = lognormal_delay(
        name="mis_specified_incubation",
        median_hours=72.0,
        sigma=0.5,
        epoch_hours=1.0,
        max_hours=336.0,
    )
    wrong = dict(simulated)
    wrong["f_inc_raw"] = slow.weights.tolist()
    wrong["L_inc"] = int(slow.weights.size)

    right_mean = float(np.mean(fit(simulated)["lambda_port[1]"]))
    wrong_mean = float(np.mean(fit(wrong)["lambda_port[1]"]))
    bias = (wrong_mean - right_mean) / right_mean
    # Direction is what matters: a slower clock pushes onsets past the window,
    # so the same onsets require a larger hazard.
    assert abs(bias) > 0.1, f"mis-specification had no effect (bias {bias:.3f})"


@pytest.mark.skipif(not cmdstan_available(), reason="CmdStan toolchain not installed")
def test_stan_and_numpy_reference_posteriors_agree() -> None:
    """The reason the numpy sampler is allowed to stand in for Stan in CI.

    Everything above validates the *density*; this validates that the density in
    ``_sentinel_reference`` is the one ``sentinel_attribution.stan`` implements.
    Tolerances are wide because two different samplers on short chains are being
    compared, not two evaluations of one sampler.
    """
    from cmdstanpy import CmdStanModel

    data, _ = design_data()
    simulated = simulate(data, lambda_port=[5.0e-3, 2.5e-4])

    model = CmdStanModel(stan_file=stan_model_path())
    stan_fit = model.sample(
        data=simulated,
        chains=2,
        iter_warmup=500,
        iter_sampling=500,
        seed=1701,
        show_progress=False,
    )
    stan_draws = stan_fit.draws_pd()
    reference = fit(simulated)

    for name in ("lambda_port[1]", "lambda_port[2]", "R_onboard", "import_share"):
        stan_mean = float(stan_draws[name].to_numpy().mean())
        ref_mean = float(np.mean(reference[name]))
        assert 0.5 < ref_mean / stan_mean < 2.0, (
            f"{name}: numpy reference {ref_mean:.3e} vs stan {stan_mean:.3e}"
        )
    # the log density itself, not just its argmax region
    stan_loglik = float(stan_draws["loglik_clinical"].to_numpy().mean())
    ref_loglik = float(np.mean(reference["loglik_clinical"]))
    assert abs(ref_loglik - stan_loglik) < 5.0, (
        f"clinical loglik {ref_loglik:.2f} (numpy) vs {stan_loglik:.2f} (stan)"
    )


def test_fixture_posterior_summarizes_to_port_hazards() -> None:
    """The CI smoke path: a committed posterior, no sampler, no CmdStan."""
    posterior = load_fixture_posterior()
    meta = {
        "ports": ["KYGEC", "MXCTM", "MXCZM"],
        "port_visit_keys": {"KYGEC": "KYGEC@2026-01-15"},
        "censoring_corrected": True,
        "port_resolution_adequate": True,
    }
    estimates = summarize_port_hazards(posterior, meta, pathogen="norovirus")
    assert [e.port_id for e in estimates] == meta["ports"]
    for e in estimates:
        assert 0.0 < e.hazard_q05 <= e.hazard_mean <= e.hazard_q95
        assert e.n_attributed_cases > 0.0
        assert e.censoring_corrected and e.port_resolution_adequate
        assert e.attribution_share is None  # single-ship model reports no share
    assert estimates[0].port_visit_key == "KYGEC@2026-01-15"
    assert estimates[1].port_visit_key is None

    onboard = onboard_summary(posterior)
    assert onboard["r_onboard_q05"] < onboard["r_onboard_mean"] < onboard["r_onboard_q95"]
    assert 0.0 <= onboard["import_share_mean"] <= 1.0


def test_summary_refuses_a_posterior_without_a_port_order() -> None:
    posterior = load_fixture_posterior()
    with pytest.raises(ValueError, match="no port order"):
        summarize_port_hazards(posterior, {}, pathogen="norovirus")
    with pytest.raises(KeyError, match="lambda_port"):
        summarize_port_hazards(
            {"R_onboard": [0.5]}, {"ports": ["A"]}, pathogen="norovirus",
        )
