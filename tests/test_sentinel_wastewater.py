"""Wastewater as a correlated observation of the incidence curve (spec 1.3, 6).

The failure mode this suite exists to catch is not a wrong number, it is a *too
confident* one: greywater reads are correlated with the clinical line list by
construction (both are functions of the same latent incidence) and with each
other (replicate taps on one holding tank), so a naive per-sample binomial term
would let one deep library outvote the only observations that carry a port label.
Most of the tests are therefore about what the channel is not allowed to do —
inflate its own evidence, move a port hazard on its own, or report a signal from
reads that do not track the curve.

Sampling tests are deliberately few and short: the invariants are deterministic,
and only "does a real signal register at all" needs a posterior.
"""

from __future__ import annotations

import math
import os
import sys
from typing import Any, Sequence

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from picard_framework.analysis.sentinel.attribution import (
    CLINICAL_CHANNEL,
    WASTEWATER_CHANNEL,
    channel_loglik,
)
from picard_framework.analysis.sentinel.fleet import (
    FLEET_HAZARD_COLUMNS,
    fleet_hazard_rows,
    summarize_fleet_hazards,
    wastewater_summary,
)
from picard_framework.analysis.sentinel.incubation import load_delay_catalog
from picard_framework.analysis.sentinel.wastewater_signal import (
    DEFAULT_MAX_EFFECTIVE_READS,
    beta_binomial_logpmf,
    expected_read_fraction,
    pool_wastewater,
    shedding_kernel,
    wastewater_config,
)
from picard_framework.analysis.stan._data import cmdstan_available
from picard_framework.analysis.stan._sentinel_fleet_data import (
    FleetRates,
    WastewaterOptions,
    WastewaterParams,
    build_sentinel_fleet_data,
    expected_onsets_fleet,
    wastewater_loglik,
    wastewater_shares,
)
from picard_framework.analysis.stan._sentinel_fleet_reference import (
    fleet_reference_posterior,
)
from picard_framework.analysis.stan.fit_sentinel_fleet import stan_model_path
from tests.test_sentinel_attribution import GENERATION, INCUBATION
from tests.test_sentinel_fleet import fleet_voyage

EPOCHS = 96
# Deeper than the cap on purpose: a real metagenomic run is, and the cap is what
# the channel's honesty depends on.
DEPTH = 5_000_000
TRUE_BASE_LOGIT = -7.0
TRUE_SLOPE = 1.0
TRUE_CONC = 100_000.0
SAMPLE_EPOCHS = (24, 36, 48, 60, 72, 84)
VOYAGE_IDS = ("shipA-0", "shipB-0")
# Chains long enough that the ordering claims are properties, not seed luck (see
# the note on the same constants in tests/test_sentinel_fleet_validation.py); as
# there, the parity test is what lets the numpy walker stand in for Stan.
DRAWS = 400
WARMUP = 1600


def sample_dict(
    epoch: int,
    *,
    reads: int,
    total: int = DEPTH,
    collection_point: str = "aft_main_sewer",
    pathogen: str = "norovirus",
) -> dict[str, Any]:
    """One ``WastewaterSample`` payload."""
    return {
        "sample_epoch": epoch,
        "collection_point": collection_point,
        "pathogen": pathogen,
        "pathogen_reads": reads,
        "total_reads": total,
        "clr_anomaly_score": 0.0,
        "concentration_copies_per_l": None,
    }


def crossover_fleet(
    samples_by_voyage: dict[str, Sequence[dict[str, Any]]] | None = None,
) -> list[Any]:
    """Two ships, opposite port order, same week — the design the hazards need."""
    by_voyage = samples_by_voyage or {}
    voyages = []
    for voyage_id, ship, ports in (
        (VOYAGE_IDS[0], "shipA", ((2, "MXCZM"), (3, "KYGEC"))),
        (VOYAGE_IDS[1], "shipB", ((2, "KYGEC"), (3, "MXCZM"))),
    ):
        voyages.append(
            fleet_voyage(
                voyage_id=voyage_id,
                ship_id=ship,
                embarkation_date="2026-03-02",
                ports=ports,
                total_epochs=EPOCHS,
                wastewater_samples=list(by_voyage.get(voyage_id, ())),
            ),
        )
    return voyages


def fleet_data(
    voyages: Sequence[Any],
    **kwargs: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    return build_sentinel_fleet_data(
        voyages, INCUBATION, GENERATION, wastewater=WastewaterOptions(**kwargs),
    )


def truth_rates(data: dict[str, Any], hazard: float = 3.0e-3) -> FleetRates:
    return FleetRates(
        lambda_visit=[hazard] * int(data["NV"]),
        lambda_aboard=[1.0e-6] * int(data["S"]),
        r_onboard=[0.4] * int(data["S"]),
        crew_ratio=1.0,
        beta_repeat=0.0,
    )


def simulate_onsets(
    data: dict[str, Any],
    rates: FleetRates,
    *,
    seed: int = 7,
) -> dict[str, Any]:
    """Poisson onsets from known hazards, written back into the data block."""
    mu = expected_onsets_fleet(data, rates)
    rng = np.random.default_rng(seed)
    onsets = []
    for v, m in enumerate(mu):
        padded = np.zeros((m.shape[0], int(data["Tmax"])), dtype=int)
        padded[:, : int(data["T"][v])] = rng.poisson(m)
        onsets.append(padded.tolist())
    out = dict(data)
    out["onsets"] = onsets
    return out


def simulate_reads(
    data: dict[str, Any],
    rates: FleetRates,
    *,
    epochs: Sequence[int] = SAMPLE_EPOCHS,
    replicates: int = 1,
    depth: int = DEPTH,
    slope: float = TRUE_SLOPE,
    logit_base: float = TRUE_BASE_LOGIT,
    concentration: float = TRUE_CONC,
    seed: int = 19,
    scramble: bool = False,
) -> dict[str, list[dict[str, Any]]]:
    """Beta-binomial reads off the true shedder prevalence, per voyage.

    ``scramble=True`` draws each epoch's reads from *another* epoch's expected
    fraction: same marginal depth and roughly the same read totals, no alignment
    to the curve. That is the null the channel must fail to find a signal in.
    """
    shares = wastewater_shares(data, rates)
    rng = np.random.default_rng(seed)
    out: dict[str, list[dict[str, Any]]] = {}
    picked = list(epochs)
    source = list(reversed(picked)) if scramble else picked
    for v, voyage_id in enumerate(VOYAGE_IDS):
        fractions = expected_read_fraction(
            shares[v], logit_base=logit_base, slope=slope,
        )
        rows: list[dict[str, Any]] = []
        for epoch, from_epoch in zip(picked, source):
            p = float(fractions[from_epoch - 1])
            for r in range(replicates):
                q = float(rng.beta(p * concentration, (1.0 - p) * concentration))
                rows.append(
                    sample_dict(
                        epoch,
                        reads=int(rng.binomial(depth, q)),
                        total=depth,
                        collection_point=f"tap{r}",
                    ),
                )
        out[voyage_id] = rows
    return out


def fleet_with_reads(
    **kwargs: Any,
) -> tuple[dict[str, Any], dict[str, Any], FleetRates]:
    """Onsets and reads simulated from one truth, in one assembled data block."""
    bare, _ = fleet_data(crossover_fleet())
    rates = truth_rates(bare)
    simulated = simulate_onsets(bare, rates)
    reads = simulate_reads(simulated, rates, **kwargs)
    data, meta = fleet_data(crossover_fleet(reads))
    data = dict(data)
    data["onsets"] = simulated["onsets"]
    return data, meta, rates


def truth_params() -> WastewaterParams:
    return WastewaterParams(
        logit_base=TRUE_BASE_LOGIT,
        slope=TRUE_SLOPE,
        concentration=TRUE_CONC,
    )


# --- kernel ---------------------------------------------------------------


def test_shedding_kernel_is_a_lagged_survival_curve() -> None:
    """Zero through the holding time, 1.0 on arrival, non-increasing after."""
    kernel = shedding_kernel("norovirus", epoch_hours=1.0)
    weights = kernel.array
    lag = kernel.residence_lag_epochs
    assert lag == int(wastewater_config()["residence_lag_hours"])
    assert float(weights[:lag].sum()) == pytest.approx(0.0, abs=0.0)
    assert weights[lag] == pytest.approx(1.0)
    tail = weights[lag:]
    assert np.all(np.diff(tail) <= 1e-12), "survival curve is not non-increasing"
    assert 0.0 <= float(tail[-1]) < 0.05, "kernel has not decayed by max_hours"
    # A survival kernel integrates to a duration, not to 1: that integration is
    # what makes the channel informative between onsets.
    assert kernel.mean_shedding_hours > 100.0


def test_residence_lag_shifts_the_signal_without_reshaping_it() -> None:
    """A longer holding time delays arrival; shedding duration is unchanged."""
    prompt = shedding_kernel("norovirus", epoch_hours=1.0, residence_lag_hours=0.0)
    held = shedding_kernel("norovirus", epoch_hours=1.0, residence_lag_hours=24.0)
    assert held.residence_lag_epochs - prompt.residence_lag_epochs == 24
    assert held.mean_shedding_hours == pytest.approx(prompt.mean_shedding_hours)
    assert np.allclose(held.array[24:], prompt.array)


def test_kernel_falls_back_to_the_generation_interval() -> None:
    """No shedding block: an explicit approximation, not a silently dropped channel."""
    catalog = load_delay_catalog()
    entry = catalog["distributions"]["norovirus"]
    stripped = {
        "wastewater": catalog.get("wastewater"),
        "default_pathogen": catalog["default_pathogen"],
        "distributions": {
            "norovirus": {k: v for k, v in entry.items() if k != "shedding"},
        },
    }
    fallback = shedding_kernel("norovirus", epoch_hours=1.0, catalog=stripped)
    full = shedding_kernel("norovirus", epoch_hours=1.0)
    assert fallback.mean_shedding_hours < full.mean_shedding_hours
    assert fallback.array[fallback.residence_lag_epochs] == pytest.approx(1.0)


def test_unknown_pathogen_is_refused() -> None:
    with pytest.raises(KeyError):
        shedding_kernel("not_a_pathogen", epoch_hours=1.0)


# --- pooling and the depth cap -------------------------------------------


def one_voyage(samples: Sequence[dict[str, Any]]) -> Any:
    return fleet_voyage(
        voyage_id="A1",
        ship_id="shipA",
        embarkation_date="2026-03-02",
        ports=((2, "MXCZM"),),
        total_epochs=EPOCHS,
        wastewater_samples=list(samples),
    )


def test_replicate_taps_pool_into_one_trial() -> None:
    """Four collection points at one epoch are one observation, not four."""
    voyage = one_voyage(
        [
            sample_dict(48, reads=40, total=100_000, collection_point=f"tap{i}")
            for i in range(4)
        ],
    )
    pooled = pool_wastewater(
        voyage.bundle, pathogen="norovirus", observation_end_epoch=EPOCHS,
    )
    assert len(pooled) == 1
    only = pooled[0]
    assert only.n_collection_points == 4
    assert only.pathogen_reads == 160
    assert only.total_reads == 400_000
    assert only.read_fraction == pytest.approx(160 / 400_000)
    # The cap discards the claimed precision and keeps the observed fraction.
    assert only.effective_reads == 100_000, "replicates inflated the trial size"
    assert only.effective_pathogen_reads == pytest.approx(
        only.read_fraction * only.effective_reads, abs=1.0,
    )


def test_pooling_drops_off_pathogen_empty_and_censored_samples() -> None:
    """Only in-window, non-empty, on-pathogen reads reach the likelihood."""
    voyage = one_voyage(
        [
            sample_dict(24, reads=10),
            sample_dict(30, reads=3, pathogen="measles"),
            sample_dict(36, reads=0, total=0),
            sample_dict(90, reads=50),
        ],
    )
    pooled = pool_wastewater(
        voyage.bundle, pathogen="norovirus", observation_end_epoch=48,
    )
    assert [s.epoch for s in pooled] == [24]


def test_reads_beyond_the_library_are_refused() -> None:
    """``pathogen_reads <= total_reads`` is a contract, enforced before the model.

    The loader rejects it, so the beta-binomial can never be handed more
    successes than trials — and the pooling that follows cannot repair it either.
    """
    bad = [sample_dict(24, reads=101, total=100)]
    with pytest.raises(ValueError, match="exceeds total_reads"):
        one_voyage(bad)

    voyage = one_voyage([sample_dict(24, reads=10, total=100)])
    pooled = pool_wastewater(
        voyage.bundle, pathogen="norovirus", observation_end_epoch=EPOCHS,
    )
    assert pooled[0].effective_pathogen_reads <= pooled[0].effective_reads


# --- the likelihood itself ------------------------------------------------


def test_beta_binomial_is_a_pmf_and_reduces_to_the_binomial() -> None:
    """Sums to 1 over its support, and collapses onto the binomial as conc grows."""
    n = 12
    ks = np.arange(n + 1)
    mass = float(
        np.exp(beta_binomial_logpmf(ks, [n] * (n + 1), [0.3] * (n + 1), 40.0)).sum(),
    )
    assert mass == pytest.approx(1.0, abs=1e-9)

    binomial = (
        math.lgamma(n + 1)
        - math.lgamma(5.0)
        - math.lgamma(n - 4 + 1)
        + 4 * math.log(0.3)
        + (n - 4) * math.log(0.7)
    )
    tight = float(beta_binomial_logpmf([4], [n], [0.3], 1.0e8)[0])
    assert tight == pytest.approx(binomial, abs=1e-3)
    # Overdispersion has to cost the tail less than the binomial does, which is
    # the whole reason it is here.
    loose = float(beta_binomial_logpmf([n], [n], [0.3], 20.0)[0])
    assert loose > float(beta_binomial_logpmf([n], [n], [0.3], 1.0e8)[0])


def test_expected_read_fraction_is_bounded_and_monotone() -> None:
    """A probability for any prevalence, rising with it, finite at zero."""
    shares = np.array([0.0, 1e-6, 1e-4, 1e-2, 0.5, 1.0])
    p = expected_read_fraction(shares, logit_base=TRUE_BASE_LOGIT, slope=TRUE_SLOPE)
    assert np.all(np.isfinite(p))
    assert np.all(p > 0.0)
    assert np.all(p < 1.0)
    assert np.all(np.diff(p) >= 0.0)
    # slope = 0 is the "carries no information" hypothesis: a flat fraction.
    flat = expected_read_fraction(shares, logit_base=TRUE_BASE_LOGIT, slope=0.0)
    assert float(flat.std()) == pytest.approx(0.0, abs=1e-15)


# --- wiring into the fleet data block ------------------------------------


def test_data_block_carries_pooled_samples_and_prevalence_denominators() -> None:
    """The Stan arrays: one trial per voyage-epoch, headcount denominators."""
    data, meta, _ = fleet_with_reads()
    n_expected = len(SAMPLE_EPOCHS) * len(VOYAGE_IDS)
    assert data["NW"] == n_expected
    assert len(data["ww_voyage"]) == n_expected
    assert sorted(set(data["ww_voyage"])) == [1, 2]
    assert set(data["ww_epoch"]) == set(SAMPLE_EPOCHS)
    assert all(0 <= r <= t for r, t in zip(data["ww_reads"], data["ww_total"]))
    assert len(data["w_shed"]) == data["L_shed"] >= 1

    persons = np.asarray(data["ww_persons"][0], dtype=float)
    assert persons.size == int(data["Tmax"])
    # Everyone is aboard on a sea day; a port day moves people ashore but nobody
    # off the denominator's ship.
    assert persons.max() == pytest.approx(1400.0, rel=0.01)
    assert persons.min() >= 1.0

    block = meta["wastewater"]
    assert block["enabled"] is True
    assert block["n_pooled_samples"] == n_expected
    assert block["pathogen"] == "norovirus"
    assert block["residence_lag_epochs"] > 0


def test_disabling_the_channel_leaves_a_valid_clinical_only_block() -> None:
    """A disabled channel is the baseline the channel is measured against."""
    bare, _ = fleet_data(crossover_fleet())
    rates = truth_rates(bare)
    reads = simulate_reads(simulate_onsets(bare, rates), rates)
    data, meta = fleet_data(crossover_fleet(reads), enabled=False)
    assert data["NW"] == 0
    assert data["ww_voyage"] == []
    assert data["ww_reads"] == []
    # The kernel and denominators still exist: only the observations are absent.
    assert data["L_shed"] >= 1
    assert len(data["ww_persons"]) == int(data["V"])
    assert meta["wastewater"]["enabled"] is False
    assert wastewater_loglik(
        data, truth_rates(data), truth_params(),
    ) == pytest.approx(0.0, abs=0.0)


def test_a_fleet_with_no_samples_is_the_same_null_path() -> None:
    """Missing wastewater data is missing data, not zero prevalence."""
    data, meta = fleet_data(crossover_fleet())
    assert data["NW"] == 0
    assert meta["wastewater"]["enabled"] is True
    assert meta["wastewater"]["n_pooled_samples"] == 0
    assert wastewater_summary({}, meta)["enabled"] is False


# --- what the channel observes -------------------------------------------


def test_prevalence_lags_incidence_by_the_holding_time() -> None:
    """The signal cannot precede the shedding it integrates."""
    data, _, rates = fleet_with_reads()
    shares = wastewater_shares(data, rates)
    incidences = np.asarray(
        [np.asarray(o, dtype=float).sum(axis=0) for o in data["onsets"]],
    )
    lag = int(np.asarray(data["w_shed"], dtype=float).argmax())
    for v, share in enumerate(shares):
        assert float(share[:lag].sum()) == pytest.approx(0.0, abs=1e-15)
        assert np.all(share >= 0.0)
        assert float(share.max()) > 0.0
        # Prevalence integrates: its peak comes after the onsets it is built from.
        assert int(share.argmax()) >= int(incidences[v].argmax()) - lag


def test_reads_that_track_the_curve_beat_reads_that_do_not() -> None:
    """The likelihood prefers the aligned series — the signal is real, not depth."""
    aligned, _, rates = fleet_with_reads()
    scrambled, _, _ = fleet_with_reads(scramble=True)
    params = truth_params()
    assert wastewater_loglik(aligned, rates, params) > wastewater_loglik(
        scrambled, rates, params,
    )


def profile_slope(data: dict[str, Any], rates: FleetRates) -> float:
    """Best-fitting elasticity, maximising over the nuisance base at each slope.

    Profiling the base matters: a slope and a base that move the expected fraction
    the same way are not distinguishable at a single prevalence, so comparing
    slopes at one fixed base would compare intercepts instead.
    """
    best_slope, best_loglik = 0.0, -np.inf
    for slope in np.linspace(0.0, 2.0, 21):
        for base in np.linspace(-14.0, -2.0, 25):
            loglik = wastewater_loglik(
                data,
                rates,
                WastewaterParams(
                    logit_base=float(base),
                    slope=float(slope),
                    concentration=TRUE_CONC,
                ),
            )
            if loglik > best_loglik:
                best_slope, best_loglik = float(slope), loglik
    return best_slope


def test_the_recovered_elasticity_is_near_one_for_reads_that_track_the_curve() -> None:
    """A known elasticity is recovered; unaligned reads do not produce one.

    ``slope -> 0`` is the "this channel carries no information" hypothesis, and it
    has to be reachable: a channel that cannot report its own irrelevance would
    add spurious confidence to the incidence curve on every fit.
    """
    aligned, _, rates = fleet_with_reads()
    scrambled, _, _ = fleet_with_reads(scramble=True)
    recovered = profile_slope(aligned, rates)
    null = profile_slope(scrambled, rates)
    assert 0.6 <= recovered <= 1.5, f"true slope 1.0 profiled to {recovered}"
    assert null < recovered, f"scrambled reads profiled to slope {null}"


def test_correlated_replicates_do_not_multiply_the_evidence() -> None:
    """Six taps per epoch must not be six times the evidence of one.

    The depth cap plus pooling is what enforces this: without them the
    beta-binomial trial size grows with the number of taps the ship happened to
    sample, and the channel's weight against the clinical line list grows with it.
    """
    single, _, rates = fleet_with_reads(replicates=1)
    many, _, _ = fleet_with_reads(replicates=6)
    params = truth_params()
    assert many["NW"] == single["NW"], "replicates changed the number of trials"
    assert many["ww_total"] == single["ww_total"], "replicates changed the trial size"
    one_loglik = wastewater_loglik(single, rates, params)
    many_loglik = wastewater_loglik(many, rates, params)
    assert abs(many_loglik) < 2.0 * abs(one_loglik), (
        f"6 replicates moved the loglik from {one_loglik:.2f} to {many_loglik:.2f}"
    )


def test_deeper_libraries_do_not_buy_unbounded_confidence() -> None:
    """A 40x deeper library is capped, so its evidence barely moves."""
    capped, _, rates = fleet_with_reads(depth=DEFAULT_MAX_EFFECTIVE_READS)
    deep, _, _ = fleet_with_reads(depth=40 * DEFAULT_MAX_EFFECTIVE_READS)
    assert max(deep["ww_total"]) == max(capped["ww_total"])
    params = truth_params()
    ratio = wastewater_loglik(deep, rates, params) / wastewater_loglik(
        capped, rates, params,
    )
    assert 0.5 < ratio < 2.0, f"depth changed the evidence {ratio:.2f}x"


# --- posteriors ----------------------------------------------------------
#
# Three fits, cached, because each is a few tens of seconds: the aligned fleet,
# the same fleet with unaligned reads, and the clinical-only baseline.


@pytest.fixture(scope="module")
def aligned_fit() -> tuple[dict[str, Any], dict[str, Any], dict[str, list[float]]]:
    data, meta, _ = fleet_with_reads()
    return data, meta, fleet_reference_posterior(data, draws=DRAWS, warmup=WARMUP)


@pytest.fixture(scope="module")
def scrambled_fit() -> dict[str, list[float]]:
    data, _, _ = fleet_with_reads(scramble=True)
    return fleet_reference_posterior(data, draws=DRAWS, warmup=WARMUP)


@pytest.fixture(scope="module")
def clinical_only_fit() -> tuple[dict[str, Any], dict[str, list[float]]]:
    bare, _ = fleet_data(crossover_fleet())
    rates = truth_rates(bare)
    simulated = simulate_onsets(bare, rates)
    reads = simulate_reads(simulated, rates)
    data, meta = fleet_data(crossover_fleet(reads), enabled=False)
    data = dict(data)
    data["onsets"] = simulated["onsets"]
    return meta, fleet_reference_posterior(data, draws=DRAWS, warmup=WARMUP)


def test_the_posterior_recovers_the_shedding_signal(
    aligned_fit: tuple[dict[str, Any], dict[str, Any], dict[str, list[float]]],
) -> None:
    """Reads simulated at elasticity 1.0 give a positive, covering posterior."""
    _, _, posterior = aligned_fit
    slope = np.asarray(posterior["ww_slope"], dtype=float)
    lo, hi = float(np.quantile(slope, 0.05)), float(np.quantile(slope, 0.95))
    assert lo > 0.1, f"a real signal read as no signal: slope 90% [{lo:.2f}, {hi:.2f}]"
    covering = f"true slope {TRUE_SLOPE} far outside [{lo:.2f}, {hi:.2f}]"
    assert lo <= TRUE_SLOPE * 1.4, covering
    assert hi >= TRUE_SLOPE * 0.5, covering
    assert float(np.mean(posterior["loglik_wastewater"])) < 0.0
    assert np.all(np.isfinite(np.asarray(posterior["ww_conc"], dtype=float)))


def test_unaligned_reads_report_a_weaker_elasticity(
    aligned_fit: tuple[dict[str, Any], dict[str, Any], dict[str, list[float]]],
    scrambled_fit: dict[str, list[float]],
) -> None:
    """The channel has to be able to say the reads told it nothing."""
    _, _, aligned = aligned_fit
    tracked = float(np.mean(aligned["ww_slope"]))
    null = float(np.mean(scrambled_fit["ww_slope"]))
    assert null < tracked, f"unaligned reads gave slope {null:.2f} vs {tracked:.2f}"


def test_the_channel_does_not_move_the_port_hazards(
    aligned_fit: tuple[dict[str, Any], dict[str, Any], dict[str, list[float]]],
    clinical_only_fit: tuple[dict[str, Any], dict[str, list[float]]],
) -> None:
    """Adding wastewater must not relabel a port: it observes the curve, not a port.

    Same onsets, same design, reads added: the per-port hazards have to stay put.
    A shift here would mean the read counts had acquired a port label through the
    latent curve, which is the failure the design exists to prevent (spec 1.3).
    """
    _, meta, with_ww = aligned_fit
    _, clinical = clinical_only_fit
    for i in range(1, len(meta["ports"]) + 1):
        name = f"lambda_port[{i}]"
        combined = float(np.mean(with_ww[name]))
        alone = float(np.mean(clinical[name]))
        assert 0.33 < combined / alone < 3.0, (
            f"{name}: {alone:.3e} clinical-only vs {combined:.3e} with wastewater"
        )
    # The clinical-only fit reports no wastewater evidence at all, rather than a
    # flattering zero.
    assert "loglik_wastewater" not in clinical
    assert "ww_slope" not in clinical
    assert WASTEWATER_CHANNEL not in channel_loglik(clinical)
    assert WASTEWATER_CHANNEL in channel_loglik(with_ww)


@pytest.mark.skipif(not cmdstan_available(), reason="CmdStan toolchain not installed")
def test_stan_and_numpy_agree_on_the_wastewater_channel() -> None:
    """Why the numpy walker may stand in for Stan on this channel too.

    The fleet parity test covers the clinical density; this one covers the
    beta-binomial term and the link, which are the parts a Stan/numpy divergence
    would hide inside a plausible-looking slope.
    """
    from cmdstanpy import CmdStanModel

    data, _, rates = fleet_with_reads()
    model = CmdStanModel(stan_file=stan_model_path())
    fit_obj = model.sample(
        data=data,
        chains=2,
        iter_warmup=400,
        iter_sampling=400,
        seed=1701,
        show_progress=False,
    )
    draws = fit_obj.draws_pd()
    reference = fleet_reference_posterior(data, draws=DRAWS, warmup=WARMUP)

    stan_slope = float(draws["ww_slope"].to_numpy().mean())
    ref_slope = float(np.mean(reference["ww_slope"]))
    assert abs(stan_slope - ref_slope) < 0.5, (
        f"ww_slope {ref_slope:.2f} (numpy) vs {stan_slope:.2f} (stan)"
    )
    stan_loglik = float(draws["loglik_wastewater"].to_numpy().mean())
    ref_loglik = float(np.mean(reference["loglik_wastewater"]))
    assert abs(stan_loglik - ref_loglik) < 10.0, (
        f"loglik_wastewater {ref_loglik:.2f} (numpy) vs {stan_loglik:.2f} (stan)"
    )
    # Same term, evaluated by hand at Stan's own posterior mean parameters.
    by_hand = wastewater_loglik(
        data,
        rates,
        WastewaterParams(
            logit_base=float(draws["ww_logit_base"].to_numpy().mean()),
            slope=stan_slope,
            concentration=float(draws["ww_conc"].to_numpy().mean()),
        ),
    )
    assert abs(by_hand - stan_loglik) < 25.0, (
        f"hand-computed {by_hand:.2f} vs stan {stan_loglik:.2f}"
    )


# --- per-channel evidence and reporting ----------------------------------


def test_channels_are_reported_separately() -> None:
    """Two correlated observations, two keys — never one summed score."""
    posterior = {
        "loglik_clinical": [-60.0, -62.0],
        "loglik_wastewater": [-19.0, -21.0],
    }
    loglik = channel_loglik(posterior)
    assert loglik[CLINICAL_CHANNEL] == pytest.approx(-61.0)
    assert loglik[WASTEWATER_CHANNEL] == pytest.approx(-20.0)


def test_an_off_channel_reports_absence_not_zero_evidence() -> None:
    """A clinical-only fit must not look like a wastewater fit with a great score."""
    loglik = channel_loglik(
        {"loglik_clinical": [-60.0], "loglik_wastewater": [0.0]},
    )
    assert WASTEWATER_CHANNEL not in loglik
    assert CLINICAL_CHANNEL in loglik


def test_hazard_rows_expose_the_wastewater_column() -> None:
    """The per-port CSV carries both channels, so neither can hide in a total."""
    assert "loglik_wastewater" in FLEET_HAZARD_COLUMNS
    _, meta, _ = fleet_with_reads()
    n_ports = len(meta["ports"])
    posterior: dict[str, list[float]] = {
        "loglik_clinical": [-60.0, -61.0],
        "loglik_wastewater": [-19.0, -20.0],
        "total_incidence": [40.0, 41.0],
    }
    for i in range(1, n_ports + 1):
        posterior[f"lambda_port[{i}]"] = [1.0e-3, 1.1e-3]
        posterior[f"imported_cases[{i}]"] = [5.0, 6.0]
        posterior[f"attribution_share[{i}]"] = [0.2, 0.25]
    rows = fleet_hazard_rows(
        summarize_fleet_hazards(posterior, meta, pathogen="norovirus"),
    )
    assert rows
    assert all(r["loglik_wastewater"] == pytest.approx(-19.5) for r in rows)


def test_wastewater_summary_reports_the_collapsed_replication() -> None:
    """A reader must be able to see how many correlated samples became trials."""
    _, meta, _ = fleet_with_reads(replicates=4)
    posterior = {
        "ww_slope": [0.9, 1.1],
        "ww_conc": [250.0, 350.0],
        "loglik_clinical": [-60.0, -61.0],
        "loglik_wastewater": [-19.0, -20.0],
    }
    summary = wastewater_summary(posterior, meta)
    assert summary["enabled"] is True
    assert summary["fitted"] is True
    assert summary["n_pooled_samples"] == len(SAMPLE_EPOCHS) * len(VOYAGE_IDS)
    assert summary["n_raw_samples"] == 4 * summary["n_pooled_samples"]
    assert summary["slope_mean"] == pytest.approx(1.0)
    assert summary["loglik_wastewater"] == pytest.approx(-19.5)
    assert summary["loglik_clinical"] == pytest.approx(-60.5)
    assert summary["mean_shedding_hours"] > 0.0


def test_summary_of_a_clinical_only_posterior_reports_an_unfitted_channel() -> None:
    """Samples on file but no channel in the fit: say so, do not invent a slope."""
    _, meta, _ = fleet_with_reads()
    summary = wastewater_summary({"loglik_clinical": [-60.0, -61.0]}, meta)
    assert summary["enabled"] is True
    assert summary["fitted"] is False
    assert summary["n_pooled_samples"] > 0
    assert "slope_mean" not in summary
    assert "loglik_wastewater" not in summary
