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
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from picard_framework.analysis.stan._metropolis import adaptive_metropolis
from picard_framework.analysis.stan._sentinel_fleet_data import (
    FleetRates,
    WastewaterParams,
    aboard_hours_by_ship,
    concentration_loglik,
    expected_onsets_fleet,
    fleet_forward_incidence,
    wastewater_loglik,
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
        # Wastewater link, only when there is wastewater to explain. With no
        # samples these would be prior-only dimensions: nothing to learn, and a
        # clinical-only fit would walk a wider space than the model it is.
        self.has_wastewater = int(data.get("NW", 0)) > 0
        if self.has_wastewater:
            self.ww_logit_base = take(1)
            self.log_ww_slope = take(1)
            self.log_ww_conc = take(1)
        # The qPCR link is dimensioned independently of the read link: a fit may
        # carry either channel, both, or neither, and an unused link would be a
        # prior-only dimension the walk pays for.
        self.has_concentration = int(data.get("NC", 0)) > 0
        if self.has_concentration:
            self.conc_intercept = take(1)
            self.log_conc_slope = take(1)
            self.log_conc_sigma = take(1)
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
    unpacked: dict[str, Any] = {
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
    if layout.has_wastewater:
        unpacked["ww_logit_base"] = float(theta[layout.ww_logit_base][0])
        unpacked["ww_slope"] = math.exp(float(theta[layout.log_ww_slope][0]))
        unpacked["ww_conc"] = math.exp(float(theta[layout.log_ww_conc][0]))
    if layout.has_concentration:
        unpacked["conc_intercept"] = float(theta[layout.conc_intercept][0])
        unpacked["conc_slope"] = math.exp(float(theta[layout.log_conc_slope][0]))
        unpacked["conc_sigma"] = math.exp(float(theta[layout.log_conc_sigma][0]))
    return unpacked


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


def wastewater_params(theta: np.ndarray, data: Mapping[str, Any]) -> WastewaterParams:
    """The wastewater link parameters a parameter vector implies.

    Links the fit does not carry keep their prior means, so callers can read the
    object without first asking which channels the bundle had.
    """
    unpacked = _unpack(np.asarray(theta, dtype=float), _Layout(data))
    defaults = WastewaterParams()
    return WastewaterParams(
        logit_base=unpacked.get("ww_logit_base", defaults.logit_base),
        slope=unpacked.get("ww_slope", defaults.slope),
        concentration=unpacked.get("ww_conc", defaults.concentration),
        conc_intercept=unpacked.get("conc_intercept", defaults.conc_intercept),
        conc_slope=unpacked.get("conc_slope", defaults.conc_slope),
        conc_sigma=unpacked.get("conc_sigma", defaults.conc_sigma),
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
    if layout.has_wastewater:
        lp += wastewater_loglik(
            data,
            rates,
            WastewaterParams(
                logit_base=u["ww_logit_base"],
                slope=u["ww_slope"],
                concentration=u["ww_conc"],
            ),
        )
    if layout.has_concentration:
        lp += concentration_loglik(
            data,
            rates,
            WastewaterParams(
                conc_intercept=u["conc_intercept"],
                conc_slope=u["conc_slope"],
                conc_sigma=u["conc_sigma"],
            ),
        )
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
    if layout.has_wastewater:
        lp += normal(
            u["ww_logit_base"],
            float(data["ww_base_prior_mean"]),
            float(data["ww_base_prior_sd"]),
        )
        # <lower=0> in Stan: the log-scale walk needs their Jacobians.
        lp += normal(
            u["ww_slope"],
            float(data["ww_slope_prior_mean"]),
            float(data["ww_slope_prior_sd"]),
        ) + math.log(u["ww_slope"])
        lp += _lognormal_log_scale(
            u["ww_conc"],
            float(data["ww_conc_prior_log_mean"]),
            float(data["ww_conc_prior_log_sd"]),
        )
    if layout.has_concentration:
        lp += normal(
            u["conc_intercept"],
            float(data["conc_intercept_prior_mean"]),
            float(data["conc_intercept_prior_sd"]),
        )
        # Both are <lower=0> in Stan, so the log-scale walk carries a Jacobian.
        lp += normal(
            u["conc_slope"],
            float(data["conc_slope_prior_mean"]),
            float(data["conc_slope_prior_sd"]),
        ) + math.log(u["conc_slope"])
        lp += normal(
            u["conc_sigma"], 0.0, float(data["conc_sigma_prior_scale"]),
        ) + math.log(u["conc_sigma"])
    for key in ("z_port", "z_visit", "z_time", "z_ship", "z_r"):
        block = theta[getattr(layout, key)]
        lp += -0.5 * float((block**2).sum())
    lp += half_normal_log_scale(u["sigma_port"], float(data["port_sd_prior_scale"]))
    lp += half_normal_log_scale(u["sigma_visit"], float(data["visit_sd_prior_scale"]))
    lp += half_normal_log_scale(u["sigma_time"], float(data["time_sd_prior_scale"]))
    lp += half_normal_log_scale(u["sigma_ship"], float(data["ship_sd_prior_scale"]))
    lp += half_normal_log_scale(u["sigma_r"], float(data["r_sd_prior_scale"]))
    return lp


def _lognormal_log_scale(value: float, log_mean: float, log_sd: float) -> float:
    """``lognormal_lpdf`` plus the log-scale Jacobian, up to a constant.

    The ``-log(value)`` in the lognormal density and the ``+log(value)`` Jacobian
    of the log-scale walk cancel, which is why only the quadratic term is left.
    """
    return -0.5 * ((math.log(value) - log_mean) / log_sd) ** 2


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
    if layout.has_wastewater:
        theta[layout.ww_logit_base] = float(data["ww_base_prior_mean"])
        theta[layout.log_ww_slope] = math.log(
            max(float(data["ww_slope_prior_mean"]), 0.1),
        )
        theta[layout.log_ww_conc] = float(data["ww_conc_prior_log_mean"])
    if layout.has_concentration:
        theta[layout.conc_intercept] = float(data["conc_intercept_prior_mean"])
        theta[layout.log_conc_slope] = math.log(
            max(float(data["conc_slope_prior_mean"]), 0.1),
        )
        theta[layout.log_conc_sigma] = math.log(
            max(float(data["conc_sigma_prior_scale"]), 0.05),
        )
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


def _wastewater_loglik_draw(
    data: Mapping[str, Any],
    rates: FleetRates,
    u: Mapping[str, Any],
    layout: _Layout,
) -> float:
    if not layout.has_wastewater:
        return 0.0
    return wastewater_loglik(
        data,
        rates,
        WastewaterParams(
            logit_base=u["ww_logit_base"],
            slope=u["ww_slope"],
            concentration=u["ww_conc"],
        ),
    )


def _concentration_loglik_draw(
    data: Mapping[str, Any],
    rates: FleetRates,
    u: Mapping[str, Any],
    layout: _Layout,
) -> float:
    if not layout.has_concentration:
        return 0.0
    return concentration_loglik(
        data,
        rates,
        WastewaterParams(
            conc_intercept=u["conc_intercept"],
            conc_slope=u["conc_slope"],
            conc_sigma=u["conc_sigma"],
        ),
    )


def _quantities_for_draw(
    row: np.ndarray,
    *,
    data: Mapping[str, Any],
    layout: _Layout,
    hours_aboard_ship: np.ndarray,
    visit_port: np.ndarray,
) -> dict[str, Any]:
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
    imported_visit = _imported_by_visit(data, rates)
    imported_port = np.zeros(layout.n_ports, dtype=float)
    for i, value in enumerate(imported_visit):
        imported_port[visit_port[i]] += value
    return {
        "u": u,
        "log_visit": log_visit,
        "imported_visit": imported_visit,
        "imported_port": imported_port,
        "aboard_cases": float((np.exp(u["log_lambda_aboard"]) * hours_aboard_ship).sum()),
        "total": float(sum(float(inc.sum()) for inc in incidence)),
        "loglik": _poisson_loglik(data, mu),
        "loglik_ww": _wastewater_loglik_draw(data, rates, u, layout),
        "loglik_conc": _concentration_loglik_draw(data, rates, u, layout),
    }


def _put_indexed(
    columns: dict[str, list[float]],
    template: str,
    count: int,
    values: Callable[[int], list[float]],
) -> None:
    for index in range(count):
        columns[template.format(index + 1)] = values(index)


def _put_wastewater_columns(
    columns: dict[str, list[float]],
    per_draw: Sequence[Mapping[str, Any]],
    layout: _Layout,
) -> None:
    if not layout.has_wastewater:
        return
    columns["ww_logit_base"] = [d["u"]["ww_logit_base"] for d in per_draw]
    columns["ww_slope"] = [d["u"]["ww_slope"] for d in per_draw]
    columns["ww_conc"] = [d["u"]["ww_conc"] for d in per_draw]
    columns["loglik_wastewater"] = [d["loglik_ww"] for d in per_draw]


def _put_concentration_columns(
    columns: dict[str, list[float]],
    per_draw: Sequence[Mapping[str, Any]],
    layout: _Layout,
) -> None:
    if not layout.has_concentration:
        return
    columns["conc_intercept"] = [d["u"]["conc_intercept"] for d in per_draw]
    columns["conc_slope"] = [d["u"]["conc_slope"] for d in per_draw]
    columns["conc_sigma"] = [d["u"]["conc_sigma"] for d in per_draw]
    columns["loglik_concentration"] = [d["loglik_conc"] for d in per_draw]


def _put_hierarchy_columns(
    columns: dict[str, list[float]],
    samples: np.ndarray,
    per_draw: Sequence[Mapping[str, Any]],
    layout: _Layout,
) -> None:
    columns["mu_log_hazard"] = [float(r[layout.mu_log_hazard][0]) for r in samples]
    columns["mu_log_aboard"] = [float(r[layout.mu_log_aboard][0]) for r in samples]
    columns["mu_log_r"] = [float(r[layout.mu_log_r][0]) for r in samples]
    columns["sigma_port"] = [d["u"]["sigma_port"] for d in per_draw]
    columns["sigma_visit"] = [d["u"]["sigma_visit"] for d in per_draw]
    columns["sigma_time"] = [d["u"]["sigma_time"] for d in per_draw]
    columns["sigma_ship"] = [d["u"]["sigma_ship"] for d in per_draw]
    columns["sigma_r"] = [d["u"]["sigma_r"] for d in per_draw]


def _put_derived_columns(
    columns: dict[str, list[float]],
    per_draw: Sequence[Mapping[str, Any]],
) -> None:
    columns["log_crew_ratio"] = [d["u"]["log_crew_ratio"] for d in per_draw]
    columns["crew_hazard_ratio"] = [math.exp(d["u"]["log_crew_ratio"]) for d in per_draw]
    columns["beta_repeat"] = [d["u"]["beta_repeat"] for d in per_draw]
    columns["repeat_hazard_ratio"] = [math.exp(d["u"]["beta_repeat"]) for d in per_draw]
    columns["aboard_cases"] = [d["aboard_cases"] for d in per_draw]
    columns["total_incidence"] = [d["total"] for d in per_draw]
    columns["secondary_cases"] = [
        max(0.0, d["total"] - float(d["imported_port"].sum()) - d["aboard_cases"])
        for d in per_draw
    ]
    columns["import_share"] = [
        float(d["imported_port"].sum() / max(d["total"], 1e-12)) for d in per_draw
    ]
    columns["loglik_clinical"] = [d["loglik"] for d in per_draw]


def _put_structure_columns(
    columns: dict[str, list[float]],
    per_draw: Sequence[Mapping[str, Any]],
    layout: _Layout,
) -> None:
    _put_indexed(
        columns,
        "lambda_port[{}]",
        layout.n_ports,
        lambda p: [float(math.exp(d["u"]["log_lambda_port"][p])) for d in per_draw],
    )
    _put_indexed(
        columns,
        "imported_cases[{}]",
        layout.n_ports,
        lambda p: [float(d["imported_port"][p]) for d in per_draw],
    )
    _put_indexed(
        columns,
        "attribution_share[{}]",
        layout.n_ports,
        lambda p: [
            float(d["imported_port"][p] / max(d["total"], 1e-12)) for d in per_draw
        ],
    )
    _put_indexed(
        columns,
        "lambda_visit[{}]",
        layout.n_visits,
        lambda i: [float(math.exp(d["log_visit"][i])) for d in per_draw],
    )
    _put_indexed(
        columns,
        "imported_cases_visit[{}]",
        layout.n_visits,
        lambda i: [float(d["imported_visit"][i]) for d in per_draw],
    )
    _put_indexed(
        columns,
        "fleet_time[{}]",
        layout.n_weeks,
        lambda w: [float(d["u"]["fleet_time"][w]) for d in per_draw],
    )
    _put_indexed(
        columns,
        "lambda_aboard[{}]",
        layout.n_ships,
        lambda s: [float(math.exp(d["u"]["log_lambda_aboard"][s])) for d in per_draw],
    )
    _put_indexed(
        columns,
        "R_onboard[{}]",
        layout.n_ships,
        lambda s: [float(math.exp(d["u"]["log_r"][s])) for d in per_draw],
    )


def _to_columns(
    samples: np.ndarray,
    *,
    data: Mapping[str, Any],
    layout: _Layout,
) -> dict[str, list[float]]:
    """Stan-named columns, including the generated quantities the report needs."""
    hours_aboard_ship = aboard_hours_by_ship(data)
    visit_port = np.asarray(data["visit_port"], dtype=int) - 1
    per_draw = [
        _quantities_for_draw(
            row,
            data=data,
            layout=layout,
            hours_aboard_ship=hours_aboard_ship,
            visit_port=visit_port,
        )
        for row in samples
    ]
    columns: dict[str, list[float]] = {}
    _put_hierarchy_columns(columns, samples, per_draw, layout)
    _put_derived_columns(columns, per_draw)
    _put_structure_columns(columns, per_draw, layout)
    _put_wastewater_columns(columns, per_draw, layout)
    _put_concentration_columns(columns, per_draw, layout)
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
