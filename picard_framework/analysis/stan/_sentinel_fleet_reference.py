"""Pure-numpy posterior for ``sentinel_fleet.stan``, for boxes without CmdStan.

Same role as ``_sentinel_reference`` for the single-ship model: the density here
is the fleet Stan model's density, evaluated through the same forward recursion
(``fleet_forward_incidence``), so the parity test compares two implementations of
one model rather than two models. The sampler is the shared coordinate-wise
Metropolis in ``_metropolis``.

Read the intervals as indicative. A crude random walk over a hierarchy this size
is not a substitute for NUTS — it exists so the recovery, null, confounded, and
censoring suites can run in CI, where CmdStan is an optional extra.
"""

from __future__ import annotations

import math
from typing import Any, Mapping

import numpy as np

from picard_framework.analysis.stan._metropolis import adaptive_metropolis
from picard_framework.analysis.stan._sentinel_fleet_data import (
    FleetRates,
    aboard_hours_by_ship,
    expected_onsets_fleet,
    fleet_forward_incidence,
)

# Log rates above 0 are more than one infection per person-hour: not a hazard,
# and the region where exp() overflows. Rejecting keeps the walk out of it.
_MAX_LOG_RATE = 0.0
_MAX_LOG_SIGMA = 3.0


class _Layout:
    """Where each parameter block sits in the flat vector the sampler walks."""

    def __init__(self, data: Mapping[str, Any]) -> None:
        n_ports = int(data["P"])
        n_visits = int(data["NV"])
        n_weeks = int(data["W"])
        n_ships = int(data["S"])
        self.n_ports = n_ports
        self.n_visits = n_visits
        self.n_weeks = n_weeks
        self.n_ships = n_ships
        cursor = 0

        def take(width: int) -> slice:
            nonlocal cursor
            out = slice(cursor, cursor + width)
            cursor += width
            return out

        self.mu_log_hazard = take(1)
        self.log_sigma_port = take(1)
        self.z_port = take(n_ports)
        self.log_sigma_visit = take(1)
        self.z_visit = take(n_visits)
        self.log_sigma_time = take(1)
        self.z_time = take(n_weeks)
        self.mu_log_aboard = take(1)
        self.log_sigma_ship = take(1)
        self.z_ship = take(n_ships)
        self.mu_log_r = take(1)
        self.log_sigma_r = take(1)
        self.z_r = take(n_ships)
        self.log_crew_ratio = take(1)
        self.beta_repeat = take(1)
        self.size = cursor


def _unpack(theta: np.ndarray, layout: _Layout) -> dict[str, Any]:
    sigma_port = math.exp(float(theta[layout.log_sigma_port][0]))
    sigma_visit = math.exp(float(theta[layout.log_sigma_visit][0]))
    sigma_time = math.exp(float(theta[layout.log_sigma_time][0]))
    sigma_ship = math.exp(float(theta[layout.log_sigma_ship][0]))
    sigma_r = math.exp(float(theta[layout.log_sigma_r][0]))
    log_lambda_port = (
        float(theta[layout.mu_log_hazard][0]) + sigma_port * theta[layout.z_port]
    )
    fleet_time = sigma_time * theta[layout.z_time]
    return {
        "sigma_port": sigma_port,
        "sigma_visit": sigma_visit,
        "sigma_time": sigma_time,
        "sigma_ship": sigma_ship,
        "sigma_r": sigma_r,
        "log_lambda_port": log_lambda_port,
        "fleet_time": fleet_time,
        "z_visit": theta[layout.z_visit],
        "log_lambda_aboard": (
            float(theta[layout.mu_log_aboard][0]) + sigma_ship * theta[layout.z_ship]
        ),
        "log_r": float(theta[layout.mu_log_r][0]) + sigma_r * theta[layout.z_r],
        "log_crew_ratio": float(theta[layout.log_crew_ratio][0]),
        "beta_repeat": float(theta[layout.beta_repeat][0]),
    }


def _log_lambda_visit(
    unpacked: Mapping[str, Any],
    data: Mapping[str, Any],
) -> np.ndarray:
    visit_port = np.asarray(data["visit_port"], dtype=int) - 1
    visit_week = np.asarray(data["visit_week"], dtype=int) - 1
    return (
        np.asarray(unpacked["log_lambda_port"])[visit_port]
        + unpacked["sigma_visit"] * np.asarray(unpacked["z_visit"])
        + np.asarray(unpacked["fleet_time"])[visit_week]
    )


def fleet_rates(theta: np.ndarray, data: Mapping[str, Any]) -> FleetRates:
    """The ``FleetRates`` a parameter vector implies — the hierarchy resolved."""
    unpacked = _unpack(np.asarray(theta, dtype=float), _Layout(data))
    return FleetRates(
        lambda_visit=np.exp(_log_lambda_visit(unpacked, data)),
        lambda_aboard=np.exp(unpacked["log_lambda_aboard"]),
        r_onboard=np.exp(unpacked["log_r"]),
        crew_ratio=math.exp(unpacked["log_crew_ratio"]),
        beta_repeat=unpacked["beta_repeat"],
    )


def _log_density(theta: np.ndarray, data: Mapping[str, Any], layout: _Layout) -> float:
    u = _unpack(theta, layout)
    if (
        max(u["sigma_port"], u["sigma_visit"], u["sigma_time"], u["sigma_ship"])
        > math.exp(_MAX_LOG_SIGMA)
    ):
        return -math.inf
    log_visit = _log_lambda_visit(u, data)
    if (
        float(log_visit.max(initial=-math.inf)) > _MAX_LOG_RATE
        or float(np.max(u["log_lambda_aboard"])) > _MAX_LOG_RATE
        or float(np.max(u["log_r"])) > 2.0
    ):
        return -math.inf

    rates = FleetRates(
        lambda_visit=np.exp(log_visit),
        lambda_aboard=np.exp(u["log_lambda_aboard"]),
        r_onboard=np.exp(u["log_r"]),
        crew_ratio=math.exp(u["log_crew_ratio"]),
        beta_repeat=u["beta_repeat"],
    )
    mu_onsets = expected_onsets_fleet(data, rates)

    lp = 0.0
    for v, mu in enumerate(mu_onsets):
        horizon = int(data["T"][v])
        counts = np.asarray(data["onsets"][v], dtype=float)[:, :horizon]
        m = np.clip(mu, 1e-12, None)
        lp += float((counts * np.log(m) - m).sum())
    if not math.isfinite(lp):
        return -math.inf

    lp += _log_prior(theta, data, layout, u)
    return lp


def _log_prior(
    theta: np.ndarray,
    data: Mapping[str, Any],
    layout: _Layout,
    u: Mapping[str, Any],
) -> float:
    def normal(x: float, mean: float, sd: float) -> float:
        return -0.5 * ((x - mean) / sd) ** 2

    def half_normal_log_scale(sigma: float, scale: float) -> float:
        # Half-normal on sigma with the log-scale Jacobian, matching Stan's
        # sigma ~ normal(0, scale) under a <lower=0> declaration.
        return -0.5 * (sigma / scale) ** 2 + math.log(sigma)

    lp = normal(
        float(theta[layout.mu_log_hazard][0]),
        float(data["hazard_log_prior_mean"]),
        float(data["hazard_log_prior_sd"]),
    )
    lp += normal(
        float(theta[layout.mu_log_aboard][0]),
        float(data["baseline_log_prior_mean"]),
        float(data["baseline_log_prior_sd"]),
    )
    lp += normal(
        float(theta[layout.mu_log_r][0]),
        float(data["r_log_prior_mean"]),
        float(data["r_log_prior_sd"]),
    )
    lp += normal(u["log_crew_ratio"], 0.0, float(data["crew_ratio_prior_sd"]))
    lp += normal(u["beta_repeat"], 0.0, float(data["repeat_prior_sd"]))
    for key in ("z_port", "z_visit", "z_time", "z_ship", "z_r"):
        block = theta[getattr(layout, key)]
        lp += -0.5 * float((block**2).sum())
    lp += half_normal_log_scale(u["sigma_port"], float(data["port_sd_prior_scale"]))
    lp += half_normal_log_scale(u["sigma_visit"], float(data["visit_sd_prior_scale"]))
    lp += half_normal_log_scale(u["sigma_time"], float(data["time_sd_prior_scale"]))
    lp += half_normal_log_scale(u["sigma_ship"], float(data["ship_sd_prior_scale"]))
    lp += half_normal_log_scale(u["sigma_r"], float(data["r_sd_prior_scale"]))
    return lp


def fleet_log_density(theta: np.ndarray, data: Mapping[str, Any]) -> float:
    """Log posterior density up to a constant — the parity test's left-hand side."""
    return _log_density(np.asarray(theta, dtype=float), data, _Layout(data))


def initial_point(data: Mapping[str, Any]) -> np.ndarray:
    """Prior-median start: every scale small, every random effect at zero."""
    layout = _Layout(data)
    theta = np.zeros(layout.size, dtype=float)
    theta[layout.mu_log_hazard] = float(data["hazard_log_prior_mean"])
    theta[layout.mu_log_aboard] = float(data["baseline_log_prior_mean"])
    theta[layout.mu_log_r] = float(data["r_log_prior_mean"])
    for key in (
        "log_sigma_port",
        "log_sigma_visit",
        "log_sigma_time",
        "log_sigma_ship",
        "log_sigma_r",
    ):
        theta[getattr(layout, key)] = math.log(0.25)
    return theta


def fleet_reference_posterior(
    data: Mapping[str, Any],
    *,
    draws: int = 400,
    warmup: int = 1200,
    thin: int = 1,
    step: float = 0.3,
    seed: int = 1701,
) -> dict[str, list[float]]:
    """Posterior draws under Stan's names, plus the fleet generated quantities.

    Warmup is longer than the single-ship default: the hierarchy adds a scale
    parameter per level, and each needs its own step size adapted.
    """
    layout = _Layout(data)
    theta = initial_point(data)
    samples = adaptive_metropolis(
        lambda vec: _log_density(vec, data, layout),
        theta,
        draws=draws,
        warmup=warmup,
        thin=thin,
        scale=step,
        seed=seed,
    )
    return _to_columns(samples, data=data, layout=layout)


def _to_columns(
    samples: np.ndarray,
    *,
    data: Mapping[str, Any],
    layout: _Layout,
) -> dict[str, list[float]]:
    """Stan-named columns, including the generated quantities the report needs."""
    hours_aboard_ship = aboard_hours_by_ship(data)
    visit_port = np.asarray(data["visit_port"], dtype=int) - 1

    columns: dict[str, list[float]] = {}

    def put(name: str, values: list[float]) -> None:
        columns[name] = values

    per_draw: list[dict[str, Any]] = []
    for row in samples:
        u = _unpack(row, layout)
        log_visit = _log_lambda_visit(u, data)
        rates = FleetRates(
            lambda_visit=np.exp(log_visit),
            lambda_aboard=np.exp(u["log_lambda_aboard"]),
            r_onboard=np.exp(u["log_r"]),
            crew_ratio=math.exp(u["log_crew_ratio"]),
            beta_repeat=u["beta_repeat"],
        )
        incidence, mu = fleet_forward_incidence(data, rates)
        total = float(sum(float(inc.sum()) for inc in incidence))
        imported_visit = _imported_by_visit(data, rates)
        imported_port = np.zeros(layout.n_ports, dtype=float)
        for i, value in enumerate(imported_visit):
            imported_port[visit_port[i]] += value
        aboard_cases = float(
            (np.exp(u["log_lambda_aboard"]) * hours_aboard_ship).sum(),
        )
        per_draw.append(
            {
                "u": u,
                "log_visit": log_visit,
                "imported_visit": imported_visit,
                "imported_port": imported_port,
                "aboard_cases": aboard_cases,
                "total": total,
                "loglik": _poisson_loglik(data, mu),
            },
        )

    put("mu_log_hazard", [float(r[layout.mu_log_hazard][0]) for r in samples])
    put("mu_log_aboard", [float(r[layout.mu_log_aboard][0]) for r in samples])
    put("mu_log_r", [float(r[layout.mu_log_r][0]) for r in samples])
    put("sigma_port", [d["u"]["sigma_port"] for d in per_draw])
    put("sigma_visit", [d["u"]["sigma_visit"] for d in per_draw])
    put("sigma_time", [d["u"]["sigma_time"] for d in per_draw])
    put("sigma_ship", [d["u"]["sigma_ship"] for d in per_draw])
    put("sigma_r", [d["u"]["sigma_r"] for d in per_draw])
    put("log_crew_ratio", [d["u"]["log_crew_ratio"] for d in per_draw])
    put("crew_hazard_ratio", [math.exp(d["u"]["log_crew_ratio"]) for d in per_draw])
    put("beta_repeat", [d["u"]["beta_repeat"] for d in per_draw])
    put("repeat_hazard_ratio", [math.exp(d["u"]["beta_repeat"]) for d in per_draw])
    for p in range(layout.n_ports):
        put(
            f"lambda_port[{p + 1}]",
            [float(math.exp(d["u"]["log_lambda_port"][p])) for d in per_draw],
        )
        put(f"imported_cases[{p + 1}]", [float(d["imported_port"][p]) for d in per_draw])
        put(
            f"attribution_share[{p + 1}]",
            [float(d["imported_port"][p] / max(d["total"], 1e-12)) for d in per_draw],
        )
    for i in range(layout.n_visits):
        put(
            f"lambda_visit[{i + 1}]",
            [float(math.exp(d["log_visit"][i])) for d in per_draw],
        )
        put(
            f"imported_cases_visit[{i + 1}]",
            [float(d["imported_visit"][i]) for d in per_draw],
        )
    for w in range(layout.n_weeks):
        put(f"fleet_time[{w + 1}]", [float(d["u"]["fleet_time"][w]) for d in per_draw])
    for s in range(layout.n_ships):
        put(
            f"lambda_aboard[{s + 1}]",
            [float(math.exp(d["u"]["log_lambda_aboard"][s])) for d in per_draw],
        )
        put(
            f"R_onboard[{s + 1}]",
            [float(math.exp(d["u"]["log_r"][s])) for d in per_draw],
        )
    put("aboard_cases", [d["aboard_cases"] for d in per_draw])
    put("total_incidence", [d["total"] for d in per_draw])
    put(
        "secondary_cases",
        [
            max(0.0, d["total"] - float(d["imported_port"].sum()) - d["aboard_cases"])
            for d in per_draw
        ],
    )
    put(
        "import_share",
        [
            float(d["imported_port"].sum() / max(d["total"], 1e-12))
            for d in per_draw
        ],
    )
    put("loglik_clinical", [d["loglik"] for d in per_draw])
    return columns


def _imported_by_visit(data: Mapping[str, Any], rates: FleetRates) -> np.ndarray:
    """Cases attributed to each visit, at the rate each group actually faced."""
    imported = np.zeros(int(data["NV"]), dtype=float)
    visit_idx = np.asarray(data["visit_idx"], dtype=int)
    crew_repeat = np.asarray(data["crew_repeat"], dtype=float)
    is_crew = np.asarray(data["is_crew"], dtype=float)
    lambda_visit = np.asarray(list(rates.lambda_visit), dtype=float)
    for v in range(int(data["V"])):
        horizon = int(data["T"][v])
        ashore = np.asarray(data["ashore_hours"][v], dtype=float)[:, :horizon, :]
        crew_mult = float(rates.crew_ratio) * np.exp(
            rates.beta_repeat * crew_repeat[v],
        )
        for p, idx in enumerate(visit_idx[v]):
            if idx <= 0:
                continue
            for g in range(ashore.shape[0]):
                mult = crew_mult[p] if is_crew[g] > 0.0 else 1.0
                imported[idx - 1] += (
                    lambda_visit[idx - 1] * mult * float(ashore[g, :, p].sum())
                )
    return imported


def _poisson_loglik(data: Mapping[str, Any], mu_onsets: list[np.ndarray]) -> float:
    total = 0.0
    for v, mu in enumerate(mu_onsets):
        horizon = int(data["T"][v])
        counts = np.asarray(data["onsets"][v], dtype=float)[:, :horizon]
        m = np.clip(mu, 1e-12, None)
        lgamma = np.vectorize(math.lgamma)(counts + 1.0)
        total += float((counts * np.log(m) - m - lgamma).sum())
    return total
