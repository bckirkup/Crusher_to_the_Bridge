"""Numpy reference sampler for the sentinel attribution posterior.

Not the inferential engine — ``sentinel_attribution.stan`` is. This is a
random-walk Metropolis over *the same* log density, for two jobs Stan cannot do
in this repo's CI:

- generate the committed fixture posterior the ``--smoke`` path summarizes;
- let the recovery/null/confounded suites assert on a real posterior on a box
  with no CmdStan toolchain (the ``[analysis]`` extra is optional).

Because it shares the density with the Stan model, a disagreement between them
is a bug in one of the two rather than a modelling choice. Chains are short and
the proposal is crude, so treat the intervals as indicative: the tests assert
ordering and monotonicity, never a calibrated interval width.

The sampler itself lives in ``_metropolis``; this module is only the density and
the generated quantities.
"""

from __future__ import annotations

import math
from typing import Any, Mapping

import numpy as np

from picard_framework.analysis.stan._metropolis import adaptive_metropolis
from picard_framework.analysis.stan._sentinel_data import (
    expected_onsets_from_data,
    forward_incidence,
)


def _log_density(
    theta: np.ndarray,
    data: Mapping[str, Any],
    onsets: np.ndarray,
) -> float:
    n_ports = int(data["P"])
    mu_log = float(theta[0])
    log_sigma = float(theta[1])
    z_port = theta[2 : 2 + n_ports]
    log_lambda_aboard = float(theta[2 + n_ports])
    r_onboard = float(theta[3 + n_ports])
    if r_onboard < 0.0:
        return -math.inf
    # A rate above 1 per person-hour is not a hazard any more; rejecting keeps
    # the random walk out of the region where exp() overflows.
    if mu_log > 0.0 or log_lambda_aboard > 0.0 or log_sigma > 3.0:
        return -math.inf

    sigma = math.exp(log_sigma)
    log_rates = mu_log + sigma * z_port
    if float(log_rates.max()) > 0.0:
        return -math.inf
    lambda_port = np.exp(log_rates)
    mu_onset = expected_onsets_from_data(
        data,
        lambda_port=lambda_port,
        lambda_aboard=math.exp(log_lambda_aboard),
        r_onboard=r_onboard,
    )
    mu_onset = np.clip(mu_onset, 1e-12, None)
    loglik = float((onsets * np.log(mu_onset) - mu_onset).sum())

    hazard_m = float(data["hazard_log_prior_mean"])
    hazard_s = float(data["hazard_log_prior_sd"])
    base_m = float(data["baseline_log_prior_mean"])
    base_s = float(data["baseline_log_prior_sd"])
    port_scale = float(data["port_sd_prior_scale"])
    r_m = float(data["r_prior_mean"])
    r_s = float(data["r_prior_sd"])

    lp = loglik
    lp += -0.5 * ((mu_log - hazard_m) / hazard_s) ** 2
    lp += -0.5 * ((log_lambda_aboard - base_m) / base_s) ** 2
    lp += -0.5 * ((r_onboard - r_m) / r_s) ** 2
    lp += -0.5 * float((z_port**2).sum())
    # half-normal on sigma, plus the log-scale Jacobian
    lp += -0.5 * (sigma / port_scale) ** 2 + log_sigma
    return lp


def _poisson_loglik(onsets: np.ndarray, mu_onset: np.ndarray) -> float:
    mu = np.clip(mu_onset, 1e-12, None)
    lgamma = np.vectorize(math.lgamma)(onsets + 1.0)
    return float((onsets * np.log(mu) - mu - lgamma).sum())


def reference_posterior(
    data: Mapping[str, Any],
    *,
    draws: int = 400,
    warmup: int = 800,
    thin: int = 1,
    step: float = 0.4,
    seed: int = 1701,
) -> dict[str, list[float]]:
    """Metropolis draws in Stan's parameter names and generated quantities."""
    onsets = np.asarray(data["onsets"], dtype=float)
    ashore = np.asarray(data["ashore_hours"], dtype=float)
    aboard = np.asarray(data["aboard_hours"], dtype=float)
    n_ports = int(data["P"])
    port_hours = ashore.sum(axis=(0, 1))
    aboard_hours_total = float(aboard.sum())

    theta = np.concatenate(
        [
            [float(data["hazard_log_prior_mean"]), math.log(0.3)],
            np.zeros(n_ports),
            [float(data["baseline_log_prior_mean"]), float(data["r_prior_mean"])],
        ],
    )
    scale = np.full(theta.size, float(step))
    # R_onboard is the only parameter on the natural scale, so it needs a step
    # sized in its own units rather than in log-rate units.
    scale[-1] = max(0.05, 0.25 * float(data["r_prior_sd"]))

    return _to_stan_columns(
        adaptive_metropolis(
            lambda vec: _log_density(vec, data, onsets),
            theta,
            draws=draws,
            warmup=warmup,
            thin=thin,
            scale=scale,
            seed=seed,
        ),
        data=data,
        onsets=onsets,
        port_hours=port_hours,
        aboard_hours_total=aboard_hours_total,
    )


def _to_stan_columns(
    samples: np.ndarray,
    *,
    data: Mapping[str, Any],
    onsets: np.ndarray,
    port_hours: np.ndarray,
    aboard_hours_total: float,
) -> dict[str, list[float]]:
    n_ports = int(data["P"])
    columns: dict[str, list[float]] = {
        f"lambda_port[{p + 1}]": [] for p in range(n_ports)
    }
    columns.update({f"imported_cases[{p + 1}]": [] for p in range(n_ports)})
    for name in ("R_onboard", "lambda_aboard", "aboard_cases", "import_share",
                 "loglik_clinical", "secondary_cases"):
        columns[name] = []

    for theta in samples:
        sigma = math.exp(float(theta[1]))
        lambda_port = np.exp(float(theta[0]) + sigma * theta[2 : 2 + n_ports])
        lambda_aboard = math.exp(float(theta[2 + n_ports]))
        r_onboard = float(theta[3 + n_ports])
        incidence, mu_onset = forward_incidence(
            data,
            lambda_port=lambda_port,
            lambda_aboard=lambda_aboard,
            r_onboard=r_onboard,
        )
        imported = lambda_port * port_hours
        aboard_cases = lambda_aboard * aboard_hours_total
        total = float(incidence.sum())
        for p in range(n_ports):
            columns[f"lambda_port[{p + 1}]"].append(float(lambda_port[p]))
            columns[f"imported_cases[{p + 1}]"].append(float(imported[p]))
        columns["R_onboard"].append(r_onboard)
        columns["lambda_aboard"].append(lambda_aboard)
        columns["aboard_cases"].append(float(aboard_cases))
        columns["secondary_cases"].append(
            max(0.0, total - float(imported.sum()) - float(aboard_cases)),
        )
        columns["import_share"].append(float(imported.sum()) / max(total, 1e-12))
        columns["loglik_clinical"].append(_poisson_loglik(onsets, mu_onset))
    return columns
