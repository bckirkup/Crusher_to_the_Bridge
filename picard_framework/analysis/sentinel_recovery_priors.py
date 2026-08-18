"""Informative fleet priors for sentinel synthetic-recovery Stan fits.

The recovery campaign reuses existing voyage zips; these priors implement the
``sentinel_stan_fix_spec`` adjustments so port hazards are not absorbed by a
broad onboard baseline and ``R_onboard`` prior.

``R_onboard`` medians come from the Crusher boundary Stage B norovirus hurdle
posterior (mega ≈ 0.06 on the natural scale). Spirit and classic values are
approximate until per-platform hurdle exports are wired in.
"""

from __future__ import annotations

import math

from picard_framework.analysis.stan._sentinel_fleet_data import FleetPriors

# CTB Stage B norovirus hurdle: natural-scale median and log-scale SD for
# mu_log_r ~ normal(log(median), log_sd) in sentinel_fleet.stan.
_CTB_R_ONBOARD: dict[str, tuple[float, float]] = {
    "mega_cruise_5000": (0.06, 0.35),
    "spirit_cruise_3000": (0.07, 0.35),
    "classic_cruise_1900": (0.08, 0.35),
}
_DEFAULT_FLEET_R = (0.06, 0.35)

# Fix 2 (alternative): aboard hours already net ashore time; tighten the
# onboard baseline prior so lambda_aboard cannot dominate port signal.
_RECOVERY_BASELINE_LOG_SD = 1.0


def fleet_config_from_cell_id(cell_id: str) -> str:
    """Parse ``{hazard}__{fleet}__R{tag}`` cell ids from recovery post-process."""
    parts = cell_id.split("__")
    if len(parts) >= 3:
        return parts[1]
    return "single"


def recovery_fleet_priors(*, fleet_config: str) -> FleetPriors:
    """Return spec-informed priors for one recovery grid cell."""
    if fleet_config == "single":
        median, log_sd = _CTB_R_ONBOARD["mega_cruise_5000"]
    else:
        median, log_sd = _DEFAULT_FLEET_R
    return FleetPriors(
        r_prior_median=median,
        r_prior_log_sd=log_sd,
        baseline_prior_log_sd=_RECOVERY_BASELINE_LOG_SD,
    )


def recovery_r_log_prior_fields(*, fleet_config: str) -> dict[str, float]:
    """Stan ``r_log_prior_*`` fields for tests and diagnostics."""
    priors = recovery_fleet_priors(fleet_config=fleet_config)
    fields = priors.stan_fields()
    return {
        "r_log_prior_mean": fields["r_log_prior_mean"],
        "r_log_prior_sd": fields["r_log_prior_sd"],
        "baseline_log_prior_sd": fields["baseline_log_prior_sd"],
        "r_prior_median": priors.r_prior_median,
    }


def ctb_r_prior_median(platform: str) -> float:
    """Natural-scale CTB reference median for one platform id."""
    median, _log_sd = _CTB_R_ONBOARD.get(platform, _DEFAULT_FLEET_R)
    return median


def ctb_r_log_prior_mean(platform: str) -> float:
    """Log-scale fleet mean passed to Stan for one platform id."""
    return math.log(ctb_r_prior_median(platform))
