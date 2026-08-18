"""Fleet posterior draws -> pooled port hazards, visit hazards, fleet-time.

Separate from ``attribution`` for the same reason that module is separate from the
Stan runner: the summary path must work from draws on disk, with no CmdStan.

What the fleet model adds to the single-ship summary:

- **attribution_share.** Imported cases at a port as a share of all fleet
  incidence — the quantity ``PortHazardEstimate.attribution_share`` returns
  ``None`` for, because one voyage cannot support it.
- **per-visit hazards** under a pooled port mean, so a single bad week is visible
  as a visit deviation instead of being averaged into the port.
- **a wastewater channel summary.** Reported separately from the port hazards,
  because the channel observes the incidence curve and never a port (spec 1.3);
  its evidence stays in its own ``evidence_loglik`` key rather than being summed
  into a single score with the correlated clinical term.
- **a structural identifiability flag.** A port whose every visit falls in a week
  when no other port was called at is not separable from the fleet-time effect
  for that week (spec 3). That is a property of the itinerary, not of the draws,
  so it is reported from the design rather than inferred from interval width —
  a wide interval has many causes, but this one is checkable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from picard_framework.analysis.sentinel.attribution import (
    CLINICAL_CHANNEL,
    WASTEWATER_CHANNEL,
    channel_loglik,
    parameter_draws,
)


@dataclass(frozen=True)
class FleetPortHazard:
    """Pooled posterior summary for one port across the fleet."""

    port_id: str
    pathogen: str
    hazard_mean: float
    hazard_q05: float
    hazard_q95: float
    n_attributed_cases: float
    attribution_share: float
    n_visits: int
    person_hours_ashore: float
    evidence_loglik: Mapping[str, float]
    fleet_time_confounded: bool
    port_resolution_adequate: bool


@dataclass(frozen=True)
class VisitHazard:
    """Posterior summary for one port visit (port x calendar week)."""

    visit_key: str
    port_id: str
    week: str
    hazard_mean: float
    hazard_q05: float
    hazard_q95: float
    n_attributed_cases: float
    person_hours_ashore: float


def fleet_time_confounded_ports(meta: Mapping[str, Any]) -> frozenset[str]:
    """Ports not separable from the fleet-time effect, from the design alone.

    A week in which only one port was called at contributes that port's hazard
    and that week's fleet-time effect to exactly the same observations: only
    their sum is identified. A port whose *every* visit is in such a week has no
    week where the two come apart, so its hazard rests entirely on the priors.
    Reporting it as a number without this flag is the over-confidence the spec
    review objected to (1.5, 3).
    """
    visits = meta.get("visits") or []
    ports_by_week: dict[str, set[str]] = {}
    for visit in visits:
        ports_by_week.setdefault(str(visit["week"]), set()).add(str(visit["port_id"]))
    weeks_by_port: dict[str, list[str]] = {}
    for visit in visits:
        weeks_by_port.setdefault(str(visit["port_id"]), []).append(str(visit["week"]))
    return frozenset(
        port_id
        for port_id, weeks in weeks_by_port.items()
        if all(len(ports_by_week[w]) == 1 for w in weeks)
    )


def summarize_fleet_hazards(
    posterior: Mapping[str, Sequence[float]],
    meta: Mapping[str, Any],
    *,
    pathogen: str,
) -> tuple[FleetPortHazard, ...]:
    """Pooled per-port summaries in ``meta['ports']`` order.

    ``hazard_mean`` is the port level *net of* the fleet-time effect, which is not
    centered: only ``lambda_port x exp(fleet_time)`` is identified, so a pooled
    port hazard is comparable across ports but not directly to the per-visit
    hazards, which carry their week's effect. Report the visit hazards when a
    number is needed for a particular call, and the pooled level when ranking
    ports. Centering the weeks would make the two scales line up by asserting the
    fleet-wide level is zero, which is the assumption the fleet-time effect exists
    to avoid (spec 3).
    """
    ports = [str(p) for p in meta.get("ports") or []]
    if not ports:
        raise ValueError("meta carries no port order; posterior indices are meaningless")
    visits = meta.get("visits") or []
    loglik = channel_loglik(posterior)
    confounded = fleet_time_confounded_ports(meta)
    resolved = bool(meta.get("port_resolution_adequate"))

    estimates: list[FleetPortHazard] = []
    for i, port_id in enumerate(ports, start=1):
        hazard = parameter_draws(posterior, f"lambda_port[{i}]")
        cases = parameter_draws(posterior, f"imported_cases[{i}]")
        share = parameter_draws(posterior, f"attribution_share[{i}]")
        port_visits = [v for v in visits if str(v["port_id"]) == port_id]
        estimates.append(
            FleetPortHazard(
                port_id=port_id,
                pathogen=pathogen,
                hazard_mean=float(hazard.mean()),
                hazard_q05=float(np.quantile(hazard, 0.05)),
                hazard_q95=float(np.quantile(hazard, 0.95)),
                n_attributed_cases=float(cases.mean()),
                attribution_share=float(share.mean()),
                n_visits=len(port_visits),
                person_hours_ashore=float(
                    sum(float(v["person_hours_ashore"]) for v in port_visits),
                ),
                evidence_loglik=loglik,
                fleet_time_confounded=port_id in confounded,
                port_resolution_adequate=resolved,
            ),
        )
    return tuple(estimates)


def summarize_visit_hazards(
    posterior: Mapping[str, Sequence[float]],
    meta: Mapping[str, Any],
) -> tuple[VisitHazard, ...]:
    """Per-visit summaries in ``meta['visits']`` order."""
    visits = meta.get("visits") or []
    if not visits:
        raise ValueError("meta carries no visit order; posterior indices are meaningless")
    out: list[VisitHazard] = []
    for i, visit in enumerate(visits, start=1):
        hazard = parameter_draws(posterior, f"lambda_visit[{i}]")
        cases = parameter_draws(posterior, f"imported_cases_visit[{i}]")
        out.append(
            VisitHazard(
                visit_key=str(visit["visit_key"]),
                port_id=str(visit["port_id"]),
                week=str(visit["week"]),
                hazard_mean=float(hazard.mean()),
                hazard_q05=float(np.quantile(hazard, 0.05)),
                hazard_q95=float(np.quantile(hazard, 0.95)),
                n_attributed_cases=float(cases.mean()),
                person_hours_ashore=float(visit["person_hours_ashore"]),
            ),
        )
    return tuple(out)


def fleet_time_summary(
    posterior: Mapping[str, Sequence[float]],
    meta: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Per-week fleet-time effects, on the log-hazard scale.

    A week whose interval excludes 0 is a fleet-wide shift the ports do not
    explain — the alternative hypothesis to "that port is dangerous".
    """
    weeks = [str(w) for w in meta.get("weeks") or []]
    rows: list[dict[str, Any]] = []
    for i, week in enumerate(weeks, start=1):
        effect = parameter_draws(posterior, f"fleet_time[{i}]")
        rows.append(
            {
                "week": week,
                "log_effect_mean": float(effect.mean()),
                "log_effect_q05": float(np.quantile(effect, 0.05)),
                "log_effect_q95": float(np.quantile(effect, 0.95)),
                "hazard_multiplier_mean": float(np.exp(effect).mean()),
            },
        )
    return rows


def fleet_onboard_summary(
    posterior: Mapping[str, Sequence[float]],
    meta: Mapping[str, Any],
) -> dict[str, Any]:
    """Per-ship onboard baseline and ``R_onboard``, plus the fleet import share.

    Both are partially pooled across ships, so a ship with three cases borrows
    the fleet's R rather than estimating its own — and a ship with an outbreak
    cannot push its onboard cases onto the ports it happened to call at.
    """
    ships = [str(s) for s in meta.get("ships") or []]
    share = parameter_draws(posterior, "import_share")
    out: dict[str, Any] = {
        "import_share_mean": float(share.mean()),
        "import_share_q05": float(np.quantile(share, 0.05)),
        "import_share_q95": float(np.quantile(share, 0.95)),
        "aboard_cases_mean": float(parameter_draws(posterior, "aboard_cases").mean()),
        "secondary_cases_mean": float(parameter_draws(posterior, "secondary_cases").mean()),
        "ships": [],
    }
    for i, ship_id in enumerate(ships, start=1):
        r = parameter_draws(posterior, f"R_onboard[{i}]")
        baseline = parameter_draws(posterior, f"lambda_aboard[{i}]")
        out["ships"].append(
            {
                "ship_id": ship_id,
                "r_onboard_mean": float(r.mean()),
                "r_onboard_q05": float(np.quantile(r, 0.05)),
                "r_onboard_q95": float(np.quantile(r, 0.95)),
                "lambda_aboard_mean": float(baseline.mean()),
            },
        )
    return out


def crew_exposure_summary(
    posterior: Mapping[str, Sequence[float]],
) -> dict[str, float]:
    """Crew ashore hazard ratio and the per-earlier-call repeat ratio.

    ``repeat_hazard_ratio`` below 1 is depletion or acquired protection across a
    ship's repeated calls at one port. It is identified only by the repeats
    inside the supplied fleet: a crew member's calls before the first voyage in
    the data are unobserved, so this is the effect of the repeats we can see.
    """
    ratio = parameter_draws(posterior, "crew_hazard_ratio")
    repeat = parameter_draws(posterior, "repeat_hazard_ratio")
    return {
        "crew_hazard_ratio_mean": float(ratio.mean()),
        "crew_hazard_ratio_q05": float(np.quantile(ratio, 0.05)),
        "crew_hazard_ratio_q95": float(np.quantile(ratio, 0.95)),
        "repeat_hazard_ratio_mean": float(repeat.mean()),
        "repeat_hazard_ratio_q05": float(np.quantile(repeat, 0.05)),
        "repeat_hazard_ratio_q95": float(np.quantile(repeat, 0.95)),
    }


def wastewater_summary(
    posterior: Mapping[str, Sequence[float]],
    meta: Mapping[str, Any],
) -> dict[str, Any]:
    """What the wastewater channel contributed, or why it contributed nothing.

    ``slope`` is the elasticity of the read fraction in shedder prevalence: an
    interval that includes 0 says this ship's greywater did not track the
    clinical curve, which is a reportable finding rather than a failure. There is
    deliberately no port attribution here — a composite sample cannot carry one
    (spec 1.3), and the pooled/raw sample counts are reported side by side so a
    reader can see how much correlated replication was collapsed. ``fitted`` is
    false when the samples exist but the posterior did not estimate the channel,
    so a clinical-only fit reports the absence rather than an invented slope.

    The two arms are reported separately because the assay decides which one
    exists: ``fitted`` is the read arm (metagenomic or amplicon libraries) and
    ``concentration_fitted`` the qPCR arm, and a qPCR-only fit has evidence in
    the channel with no ``ww_slope`` to quote at all.
    """
    block = dict((meta.get("wastewater") or {}))
    n_pooled = int(block.get("n_pooled_samples") or 0)
    n_conc = int(block.get("n_concentration_samples") or 0)
    enabled = bool(block.get("enabled")) and (n_pooled > 0 or n_conc > 0)
    fitted = bool(block.get("enabled")) and n_pooled > 0 and "ww_slope" in posterior
    out: dict[str, Any] = {
        "enabled": enabled,
        "fitted": fitted,
        "pathogen": block.get("pathogen"),
        "n_pooled_samples": int(block.get("n_pooled_samples") or 0),
        "n_raw_samples": int(block.get("n_raw_samples") or 0),
        "max_effective_reads": block.get("max_effective_reads"),
        "residence_lag_epochs": block.get("residence_lag_epochs"),
        "mean_shedding_hours": block.get("mean_shedding_hours"),
        "n_concentration_samples": int(block.get("n_concentration_samples") or 0),
        "n_concentration_censored": int(block.get("n_concentration_censored") or 0),
    }
    out.update(_concentration_summary(posterior, out["n_concentration_samples"]))
    if not fitted:
        return out
    slope = parameter_draws(posterior, "ww_slope")
    conc = parameter_draws(posterior, "ww_conc")
    loglik = channel_loglik(posterior)
    out.update(
        {
            "slope_mean": float(slope.mean()),
            "slope_q05": float(np.quantile(slope, 0.05)),
            "slope_q95": float(np.quantile(slope, 0.95)),
            "concentration_mean": float(conc.mean()),
            "loglik_wastewater": loglik.get(WASTEWATER_CHANNEL),
            "loglik_clinical": loglik.get(CLINICAL_CHANNEL),
        },
    )
    return out


def _concentration_summary(
    posterior: Mapping[str, Sequence[float]],
    n_concentration: int,
) -> dict[str, Any]:
    """The qPCR arm of the channel, reported apart from the read arm.

    A concentration slope near 0 says the Ct series did not track the clinical
    curve. ``concentration_fitted`` is false when no quantitative sample was
    pooled, so a metagenomic-only or clinical-only fit reports the absence
    rather than a slope estimated from the prior alone.
    """
    fitted = n_concentration > 0 and "conc_slope" in posterior
    out: dict[str, Any] = {"concentration_fitted": fitted}
    if not fitted:
        return out
    slope = parameter_draws(posterior, "conc_slope")
    intercept = parameter_draws(posterior, "conc_intercept")
    sigma = parameter_draws(posterior, "conc_sigma")
    out.update(
        {
            "conc_slope_mean": float(slope.mean()),
            "conc_slope_q05": float(np.quantile(slope, 0.05)),
            "conc_slope_q95": float(np.quantile(slope, 0.95)),
            "conc_intercept_mean": float(intercept.mean()),
            "conc_sigma_mean": float(sigma.mean()),
        },
    )
    if "loglik_concentration" in posterior:
        out["loglik_concentration"] = float(
            parameter_draws(posterior, "loglik_concentration").mean(),
        )
    return out


def fleet_hazard_rows(estimates: Sequence[FleetPortHazard]) -> list[dict[str, Any]]:
    """Flatten pooled port estimates for CSV output."""
    return [
        {
            "port_id": e.port_id,
            "pathogen": e.pathogen,
            "hazard_mean": e.hazard_mean,
            "hazard_q05": e.hazard_q05,
            "hazard_q95": e.hazard_q95,
            "n_attributed_cases": e.n_attributed_cases,
            "attribution_share": e.attribution_share,
            "n_visits": e.n_visits,
            "person_hours_ashore": e.person_hours_ashore,
            "fleet_time_confounded": e.fleet_time_confounded,
            "port_resolution_adequate": e.port_resolution_adequate,
            "loglik_clinical": e.evidence_loglik.get(CLINICAL_CHANNEL, ""),
            "loglik_wastewater": e.evidence_loglik.get(WASTEWATER_CHANNEL, ""),
        }
        for e in estimates
    ]


def visit_hazard_rows(estimates: Sequence[VisitHazard]) -> list[dict[str, Any]]:
    """Flatten per-visit estimates for CSV output."""
    return [
        {
            "visit_key": e.visit_key,
            "port_id": e.port_id,
            "week": e.week,
            "hazard_mean": e.hazard_mean,
            "hazard_q05": e.hazard_q05,
            "hazard_q95": e.hazard_q95,
            "n_attributed_cases": e.n_attributed_cases,
            "person_hours_ashore": e.person_hours_ashore,
        }
        for e in estimates
    ]


FLEET_HAZARD_COLUMNS = (
    "port_id",
    "pathogen",
    "hazard_mean",
    "hazard_q05",
    "hazard_q95",
    "n_attributed_cases",
    "attribution_share",
    "n_visits",
    "person_hours_ashore",
    "fleet_time_confounded",
    "port_resolution_adequate",
    "loglik_clinical",
    "loglik_wastewater",
)

VISIT_HAZARD_COLUMNS = (
    "visit_key",
    "port_id",
    "week",
    "hazard_mean",
    "hazard_q05",
    "hazard_q95",
    "n_attributed_cases",
    "person_hours_ashore",
)
