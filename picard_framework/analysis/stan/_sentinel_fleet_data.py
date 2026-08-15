"""Stan data assembly for the fleet sentinel model (many voyages, shared ports).

The single-ship builder (``_sentinel_data``) keeps its conventions here — raw
rather than censoring-discounted hours, strata collapsed to person groups, the
onset convolution truncated at the horizon — and this module adds the three
grouping levels the hierarchy needs:

- **port visit.** ``port_id`` x ISO calendar week, the public-health unit (spec
  2). Two ships calling at the same port the same week share a visit; the same
  port a month later is a different visit. Visits are the level a port hazard
  actually varies at, so pooling voyages without this level would average a
  cluster week into a quiet one.
- **calendar week.** The fleet-time effect index. A port that every ship calls at
  in one week is confounded with a fleet-wide shock, and the model needs the
  shock in it for that to surface as a wide interval instead of a confident
  number (spec 3).
- **ship.** Onboard baseline and ``R_onboard`` partially pool across ships, so a
  ship with an outbreak cannot push its onboard cases onto the ports it called
  at, and a voyage with three cases is not asked to estimate its own R.

Crew repeat exposure is a *covariate*, not a level: ``crew_repeat[v, p]`` counts
the earlier calls that ship made at that port inside the supplied fleet, and its
coefficient is the only within-person contrast available (spec 3).

Wastewater enters as pooled read counts against the *same* latent incidence curve
(spec 1.3) — one beta-binomial trial per voyage-epoch, never a port-labelled
hazard. ``WastewaterOptions(enabled=False)`` drops the channel entirely, which is
how its marginal value is measured against the clinical-only baseline.

Voyages are padded to the longest horizon; every Stan loop stops at ``T[v]`` so
padded epochs never enter the likelihood.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping, Sequence

import numpy as np

from picard_framework.analysis.sentinel.exposure import (
    ExposureDesign,
    min_inter_port_hours,
)
from picard_framework.analysis.sentinel.incubation import (
    DelayDistribution,
    default_pathogen,
    port_resolution_adequate,
)
from picard_framework.analysis.sentinel.itinerary import Voyage
from picard_framework.analysis.sentinel.observations import ObservationBundle
from picard_framework.analysis.sentinel.wastewater_signal import (
    DEFAULT_BASE_LOGIT_PRIOR_MEAN,
    DEFAULT_BASE_LOGIT_PRIOR_SD,
    DEFAULT_CONCENTRATION_PRIOR_LOG_SD,
    DEFAULT_CONCENTRATION_PRIOR_MEDIAN,
    DEFAULT_SLOPE_PRIOR_MEAN,
    DEFAULT_SLOPE_PRIOR_SD,
    SHARE_FLOOR,
    PooledSample,
    beta_binomial_logpmf,
    expected_read_fraction,
    pool_wastewater,
    shedder_prevalence,
    shedding_kernel,
    wastewater_config,
)
from picard_framework.analysis.stan._sentinel_data import (
    CREW,
    DEFAULT_BASELINE_PRIOR_MEDIAN,
    DEFAULT_HAZARD_PRIOR_MEDIAN,
    DEFAULT_PORT_SD_PRIOR_SCALE,
    DEFAULT_PRIOR_LOG_SD,
    GROUPS,
    aboard_hours_by_epoch,
    ashore_hours_by_epoch,
    attribution_ports,
    group_onsets,
)

# Half-normal scales for the hierarchy. All are on the log-hazard scale, where
# 0.5 is a factor of ~1.6: ports are allowed to differ more than repeat visits
# to one port, and the fleet-time shock is given as much room as the between-port
# spread on purpose — shrinking it would quietly resolve the confounding in
# favour of the ports (spec 3).
DEFAULT_VISIT_SD_PRIOR_SCALE = 0.5
DEFAULT_TIME_SD_PRIOR_SCALE = 0.75
DEFAULT_SHIP_SD_PRIOR_SCALE = 0.5
DEFAULT_R_SD_PRIOR_SCALE = 0.4
# R_onboard is lognormal at the fleet level here (it is a positive multiplier
# pooled across ships), unlike the single-ship model's normal prior on R itself.
DEFAULT_R_LOG_PRIOR_MEDIAN = 0.6
DEFAULT_R_LOG_PRIOR_SD = 0.6
DEFAULT_CREW_RATIO_PRIOR_SD = 0.5
DEFAULT_REPEAT_PRIOR_SD = 0.3


@dataclass(frozen=True)
class FleetPriors:
    """Priors on the fleet hierarchy, travelling as one argument.

    Grouped rather than passed individually because they are one modelling
    decision: the between-port spread, the fleet-time spread, and the visit
    spread are only interpretable relative to each other (spec 3).
    """

    hazard_prior_median: float = DEFAULT_HAZARD_PRIOR_MEDIAN
    baseline_prior_median: float = DEFAULT_BASELINE_PRIOR_MEDIAN
    prior_log_sd: float = DEFAULT_PRIOR_LOG_SD
    port_sd_prior_scale: float = DEFAULT_PORT_SD_PRIOR_SCALE
    visit_sd_prior_scale: float = DEFAULT_VISIT_SD_PRIOR_SCALE
    time_sd_prior_scale: float = DEFAULT_TIME_SD_PRIOR_SCALE
    ship_sd_prior_scale: float = DEFAULT_SHIP_SD_PRIOR_SCALE
    r_sd_prior_scale: float = DEFAULT_R_SD_PRIOR_SCALE
    r_prior_median: float = DEFAULT_R_LOG_PRIOR_MEDIAN
    r_prior_log_sd: float = DEFAULT_R_LOG_PRIOR_SD
    crew_ratio_prior_sd: float = DEFAULT_CREW_RATIO_PRIOR_SD
    repeat_prior_sd: float = DEFAULT_REPEAT_PRIOR_SD

    def __post_init__(self) -> None:
        medians = (
            self.hazard_prior_median,
            self.baseline_prior_median,
            self.r_prior_median,
        )
        if any(m <= 0.0 for m in medians):
            raise ValueError("prior medians must be positive")

    def stan_fields(self) -> dict[str, float]:
        """The prior block of the Stan data dictionary."""
        return {
            "hazard_log_prior_mean": math.log(float(self.hazard_prior_median)),
            "hazard_log_prior_sd": float(self.prior_log_sd),
            "baseline_log_prior_mean": math.log(float(self.baseline_prior_median)),
            "baseline_log_prior_sd": float(self.prior_log_sd),
            "r_log_prior_mean": math.log(float(self.r_prior_median)),
            "r_log_prior_sd": float(self.r_prior_log_sd),
            "port_sd_prior_scale": float(self.port_sd_prior_scale),
            "visit_sd_prior_scale": float(self.visit_sd_prior_scale),
            "time_sd_prior_scale": float(self.time_sd_prior_scale),
            "ship_sd_prior_scale": float(self.ship_sd_prior_scale),
            "r_sd_prior_scale": float(self.r_sd_prior_scale),
            "crew_ratio_prior_sd": float(self.crew_ratio_prior_sd),
            "repeat_prior_sd": float(self.repeat_prior_sd),
        }


@dataclass(frozen=True)
class WastewaterOptions:
    """Wastewater channel switches.

    ``enabled=False`` is the clinical-only baseline the channel's marginal value
    is measured against (spec 6), so it belongs with the channel's other knobs
    rather than as a lone boolean beside the priors.
    """

    enabled: bool = True
    pathogen: str | None = None
    residence_lag_hours: float | None = None
    max_effective_reads: int | None = None


@dataclass(frozen=True)
class FleetVoyage:
    """One voyage's exposure design with the itinerary and observations it came from."""

    design: ExposureDesign
    voyage: Voyage
    bundle: ObservationBundle

    @property
    def ship_id(self) -> str:
        """Ship the voyage was sailed by."""
        return self.design.ship_id

    @property
    def voyage_id(self) -> str:
        """Voyage identifier."""
        return self.design.voyage_id


def fleet_visit_key(port_id: str, voyage: Voyage, port_call_day: int) -> str:
    """``port_id@ISO-week`` when dated, else ``port_id@voyage/day``.

    The week is the unit a port hazard is reported at, so two ships calling in
    the same week must land on the same key. An undated itinerary cannot be
    aligned to another ship's calendar at all, so it falls back to a key unique
    to that voyage — pooling it with anyone else would be an invented
    coincidence.
    """
    call = next(
        (c for c in voyage.port_calls if c.port_id == port_id and c.voyage_day == port_call_day),
        None,
    )
    if call is not None and call.calendar_date is not None:
        iso = call.calendar_date.isocalendar()
        return f"{port_id}@{iso.year}-W{iso.week:02d}"
    return f"{port_id}@{voyage.voyage_id}/d{port_call_day}"


def _first_call_day(voyage: Voyage, port_id: str) -> int:
    call = voyage.port_call(port_id)
    return call.voyage_day if call is not None else 1


def _week_key(voyage: Voyage, port_id: str) -> str:
    """Calendar week the visit falls in — the fleet-time index."""
    call = voyage.port_call(port_id)
    if call is not None and call.calendar_date is not None:
        iso = call.calendar_date.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    return f"{voyage.voyage_id}/unscheduled"


def _visit_layout(
    voyages: Sequence[FleetVoyage],
    ports: Sequence[str],
) -> tuple[list[str], list[str], dict[str, int], dict[str, int]]:
    """``(visit_keys, week_keys, visit_index, week_index)`` in stable order."""
    visit_keys: list[str] = []
    week_keys: list[str] = []
    for fv in voyages:
        for port_id in attribution_ports(fv.design):
            if port_id not in ports:
                continue
            key = fleet_visit_key(port_id, fv.voyage, _first_call_day(fv.voyage, port_id))
            if key not in visit_keys:
                visit_keys.append(key)
            week = _week_key(fv.voyage, port_id)
            if week not in week_keys:
                week_keys.append(week)
    visit_keys.sort()
    week_keys.sort()
    return (
        visit_keys,
        week_keys,
        {k: i + 1 for i, k in enumerate(visit_keys)},
        {k: i + 1 for i, k in enumerate(week_keys)},
    )


def _crew_repeat_counts(
    voyages: Sequence[FleetVoyage],
    ports: Sequence[str],
) -> np.ndarray:
    """``(voyage, port)`` count of earlier calls by the same ship at that port.

    Ordered by embarkation date where known, else by the order supplied. Only
    calls inside this fleet are counted: a crew member's exposure history before
    the first voyage in the data is unobserved, so the covariate is a lower bound
    and ``beta_repeat`` is the effect of the repeats we can see.
    """
    counts = np.zeros((len(voyages), len(ports)), dtype=float)
    order = sorted(
        range(len(voyages)),
        key=lambda i: (
            voyages[i].voyage.embarkation_date or date.min,
            voyages[i].voyage_id,
        ),
    )
    seen: dict[tuple[str, str], int] = {}
    for i in order:
        fv = voyages[i]
        for p, port_id in enumerate(ports):
            if port_id not in attribution_ports(fv.design):
                continue
            key = (fv.ship_id, port_id)
            counts[i, p] = float(seen.get(key, 0))
            seen[key] = seen.get(key, 0) + 1
    return counts


def build_sentinel_fleet_data(
    voyages: Sequence[FleetVoyage],
    incubation: DelayDistribution,
    generation: DelayDistribution,
    *,
    priors: FleetPriors | None = None,
    wastewater: WastewaterOptions | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """``(stan_data, meta)`` for a fleet of voyages sharing an epoch grid.

    ``meta`` carries the port, visit, week, and ship orders the posterior indices
    refer to — a fleet posterior is unreadable without them — plus the per-voyage
    port-resolution verdicts (spec 1.8).
    """
    resolved_priors = priors or FleetPriors()
    ww_options = wastewater or WastewaterOptions()
    if not voyages:
        raise ValueError("a fleet model needs at least one voyage")
    epoch_hours = {round(float(fv.voyage.epoch_duration_hours), 6) for fv in voyages}
    if len(epoch_hours) > 1:
        raise ValueError(
            "voyages must share an epoch duration; the delay pmfs are on that "
            f"grid: {sorted(epoch_hours)}",
        )
    ports = sorted({p for fv in voyages for p in attribution_ports(fv.design)})
    if not ports:
        raise ValueError("no voyage has a port with positive ashore exposure")

    visit_keys, week_keys, visit_index, week_index = _visit_layout(voyages, ports)
    crew_repeat = _crew_repeat_counts(voyages, ports)
    ships = sorted({fv.ship_id for fv in voyages})
    horizons = [int(fv.design.observation_end_epoch) for fv in voyages]
    t_max = max(horizons)

    onsets: list[list[list[int]]] = []
    ashore_all: list[list[list[list[float]]]] = []
    aboard_all: list[list[list[float]]] = []
    shares: list[list[float]] = []
    visit_idx: list[list[int]] = []
    visit_port: list[int] = [0] * len(visit_keys)
    visit_week: list[int] = [0] * len(visit_keys)
    hours_by_visit: dict[str, float] = dict.fromkeys(visit_keys, 0.0)

    for i, fv in enumerate(voyages):
        ashore = ashore_hours_by_epoch(fv.design, fv.voyage, ports)
        aboard = aboard_hours_by_epoch(fv.voyage, fv.bundle, ashore)
        counts = group_onsets(fv.bundle, fv.design.observation_end_epoch)
        # (epoch, port) per group, which is Stan's matrix[Tmax, P].
        ashore_all.append(
            [_pad_rows(ashore[g], t_max) for g in range(len(GROUPS))],
        )
        aboard_all.append(_pad_cols(aboard, t_max))
        onsets.append(_pad_cols(counts, t_max, dtype=int))
        share = aboard.sum(axis=1)
        if share.sum() <= 0.0:
            share = np.ones(len(GROUPS), dtype=float)
        shares.append([float(x) for x in share])

        row = [0] * len(ports)
        voyage_ports = attribution_ports(fv.design)
        for p, port_id in enumerate(ports):
            if port_id not in voyage_ports:
                continue
            key = fleet_visit_key(
                port_id, fv.voyage, _first_call_day(fv.voyage, port_id),
            )
            idx = visit_index[key]
            row[p] = idx
            visit_port[idx - 1] = p + 1
            visit_week[idx - 1] = week_index[_week_key(fv.voyage, port_id)]
            hours_by_visit[key] += float(ashore[:, :, p].sum())
        visit_idx.append(row)

    lagged = generation.strictly_lagged().weights[1:]
    ww = _wastewater_block(
        voyages,
        options=ww_options,
        t_max=t_max,
        aboard_all=aboard_all,
        epoch_hours=float(voyages[0].voyage.epoch_duration_hours),
    )
    data = {
        "V": len(voyages),
        "S": len(ships),
        "P": len(ports),
        "G": len(GROUPS),
        "NV": len(visit_keys),
        "W": len(week_keys),
        "Tmax": int(t_max),
        "T": horizons,
        "ship": [ships.index(fv.ship_id) + 1 for fv in voyages],
        "is_crew": [1 if g == CREW else 0 for g in GROUPS],
        "visit_idx": visit_idx,
        "visit_port": visit_port,
        "visit_week": visit_week,
        "crew_repeat": crew_repeat.tolist(),
        "L_inc": int(incubation.weights.size),
        "L_gen": int(lagged.size),
        "f_inc_raw": incubation.weights.tolist(),
        "w_gen_raw": lagged.tolist(),
        "onsets": onsets,
        "ashore_hours": ashore_all,
        "aboard_hours": aboard_all,
        "secondary_share_raw": shares,
        "ascertainment": [float(fv.design.ascertainment) for fv in voyages],
        **resolved_priors.stan_fields(),
        **ww["data"],
    }
    meta = _fleet_meta(
        voyages,
        ports=ports,
        visit_keys=visit_keys,
        week_keys=week_keys,
        ships=ships,
        visit_port=visit_port,
        visit_week=visit_week,
        hours_by_visit=hours_by_visit,
        crew_repeat=crew_repeat,
        incubation=incubation,
    )
    meta["wastewater"] = ww["meta"]
    return data, meta


def _fleet_meta(
    voyages: Sequence[FleetVoyage],
    *,
    ports: Sequence[str],
    visit_keys: Sequence[str],
    week_keys: Sequence[str],
    ships: Sequence[str],
    visit_port: Sequence[int],
    visit_week: Sequence[int],
    hours_by_visit: Mapping[str, float],
    crew_repeat: np.ndarray,
    incubation: DelayDistribution,
) -> dict[str, Any]:
    resolutions = {
        fv.voyage_id: port_resolution_adequate(
            incubation, min_inter_port_hours(fv.voyage),
        )
        for fv in voyages
    }
    return {
        "model": "sentinel_fleet",
        "ports": list(ports),
        "visits": [
            {
                "visit_key": key,
                "port_id": ports[visit_port[i] - 1],
                "week": week_keys[visit_week[i] - 1],
                "person_hours_ashore": round(float(hours_by_visit[key]), 6),
            }
            for i, key in enumerate(visit_keys)
        ],
        "weeks": list(week_keys),
        "ships": list(ships),
        "groups": list(GROUPS),
        "voyages": [
            {
                "voyage_id": fv.voyage_id,
                "ship_id": fv.ship_id,
                "observation_end_epoch": int(fv.design.observation_end_epoch),
                "ports": list(attribution_ports(fv.design)),
                "n_cases": len(fv.bundle.clinical_cases),
                "ascertainment": float(fv.design.ascertainment),
                "crew_repeat": {
                    port_id: float(crew_repeat[i, p])
                    for p, port_id in enumerate(ports)
                    if crew_repeat[i, p] > 0.0
                },
                "port_resolution_adequate": resolutions[fv.voyage_id],
            }
            for i, fv in enumerate(voyages)
        ],
        "epoch_duration_hours": float(voyages[0].voyage.epoch_duration_hours),
        "person_hours_ashore": {
            key: round(float(hours), 6) for key, hours in hours_by_visit.items()
        },
        "censoring_corrected": any(
            c.censoring_corrected for fv in voyages for c in fv.design.port_cells
        ),
        "incubation_iqr_hours": round(incubation.iqr_hours, 3),
        "port_resolution_adequate": all(resolutions.values()),
        "n_cases": sum(len(fv.bundle.clinical_cases) for fv in voyages),
    }


def _wastewater_block(
    voyages: Sequence[FleetVoyage],
    *,
    options: WastewaterOptions,
    t_max: int,
    aboard_all: Sequence[Sequence[Sequence[float]]],
    epoch_hours: float,
) -> dict[str, Any]:
    """``{'data': ..., 'meta': ...}`` for the wastewater channel.

    ``enabled=False`` still emits the arrays, at length 0: Stan needs the block to
    exist, and a zero-length observation array is how "no wastewater evidence"
    is stated without a second copy of the model. The parameters remain in the
    posterior and are then prior-only, which is deliberately visible — a report
    that quotes ``ww_slope`` off a clinical-only fit should be caught.

    The denominator is persons aboard per epoch, reconstructed from the aboard
    person-hours already assembled, so the read fraction is linked to a
    *prevalence* rather than a headcount that would scale with ship size.
    """
    resolved = options.pathogen or default_pathogen()
    kernel = shedding_kernel(
        resolved,
        epoch_hours=epoch_hours,
        residence_lag_hours=options.residence_lag_hours,
    )
    config = wastewater_config()
    cap = int(
        options.max_effective_reads
        if options.max_effective_reads is not None
        else config["max_effective_reads"],
    )

    persons: list[list[float]] = []
    for v in range(len(voyages)):
        aboard = np.asarray(aboard_all[v], dtype=float)
        # Person-hours over the epoch length is the headcount aboard that epoch.
        head = aboard.sum(axis=0) / float(epoch_hours or 1.0)
        persons.append([float(max(x, 1.0)) for x in head])

    pooled: list[PooledSample] = []
    voyage_of: list[int] = []
    if options.enabled:
        for i, fv in enumerate(voyages):
            samples = pool_wastewater(
                fv.bundle,
                pathogen=resolved,
                observation_end_epoch=int(fv.design.observation_end_epoch),
                max_effective_reads=cap,
            )
            pooled.extend(samples)
            voyage_of.extend([i + 1] * len(samples))

    data = {
        "NW": len(pooled),
        "ww_voyage": voyage_of,
        "ww_epoch": [int(s.epoch) for s in pooled],
        "ww_reads": [int(s.effective_pathogen_reads) for s in pooled],
        "ww_total": [int(s.effective_reads) for s in pooled],
        "L_shed": int(kernel.array.size),
        "w_shed": [float(x) for x in kernel.array],
        "ww_persons": persons,
        "ww_share_floor": float(SHARE_FLOOR),
        "ww_base_prior_mean": float(DEFAULT_BASE_LOGIT_PRIOR_MEAN),
        "ww_base_prior_sd": float(DEFAULT_BASE_LOGIT_PRIOR_SD),
        "ww_slope_prior_mean": float(DEFAULT_SLOPE_PRIOR_MEAN),
        "ww_slope_prior_sd": float(DEFAULT_SLOPE_PRIOR_SD),
        "ww_conc_prior_log_mean": math.log(float(DEFAULT_CONCENTRATION_PRIOR_MEDIAN)),
        "ww_conc_prior_log_sd": float(DEFAULT_CONCENTRATION_PRIOR_LOG_SD),
    }
    meta = {
        "enabled": bool(options.enabled),
        "pathogen": resolved,
        "n_pooled_samples": len(pooled),
        "n_raw_samples": sum(s.n_collection_points for s in pooled),
        "max_effective_reads": cap,
        "residence_lag_epochs": kernel.residence_lag_epochs,
        "mean_shedding_hours": round(kernel.mean_shedding_hours, 3),
        "samples": [
            {
                "voyage_id": s.voyage_id,
                "epoch": s.epoch,
                "pathogen_reads": s.pathogen_reads,
                "total_reads": s.total_reads,
                "effective_reads": s.effective_reads,
                "n_collection_points": s.n_collection_points,
                "read_fraction": round(s.read_fraction, 9),
            }
            for s in pooled
        ],
    }
    if t_max and persons and len(persons[0]) != t_max:
        raise ValueError(
            "aboard hours were not padded to Tmax before the wastewater "
            f"denominators were built: {len(persons[0])} vs {t_max}",
        )
    return {"data": data, "meta": meta}


@dataclass(frozen=True)
class WastewaterParams:
    """The wastewater link parameters, separated from the hierarchy like ``FleetRates``."""

    logit_base: float = DEFAULT_BASE_LOGIT_PRIOR_MEAN
    slope: float = DEFAULT_SLOPE_PRIOR_MEAN
    concentration: float = DEFAULT_CONCENTRATION_PRIOR_MEDIAN


@dataclass(frozen=True)
class FleetRates:
    """The rates the fleet forward model needs, already off the hierarchy.

    Separating this from the hierarchy is what lets the validation suites simulate
    from *known* per-visit hazards without also having to invent the z-scores that
    would produce them.
    """

    lambda_visit: Sequence[float]     # per port visit
    lambda_aboard: Sequence[float]    # per ship
    r_onboard: Sequence[float]        # per ship
    crew_ratio: float = 1.0
    beta_repeat: float = 0.0


def fleet_forward_incidence(
    data: Mapping[str, Any],
    rates: FleetRates,
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """``(incidence, mu_onset)`` per voyage, mirroring ``sentinel_fleet.stan``.

    Same recursion, same truncation, same crew multiplier. A divergence between
    this and the Stan model is a bug in one of them, not a modelling choice —
    which is the only reason the numpy reference sampler is allowed to stand in
    for Stan in CI.
    """
    f_inc = np.asarray(data["f_inc_raw"], dtype=float)
    f_inc = f_inc / f_inc.sum()
    w_gen = np.asarray(data["w_gen_raw"], dtype=float)
    w_gen = w_gen / w_gen.sum()
    lambda_visit = np.asarray(list(rates.lambda_visit), dtype=float)
    lambda_aboard = np.asarray(list(rates.lambda_aboard), dtype=float)
    r_onboard = np.asarray(list(rates.r_onboard), dtype=float)
    is_crew = np.asarray(data["is_crew"], dtype=float)
    crew_repeat = np.asarray(data["crew_repeat"], dtype=float)
    visit_idx = np.asarray(data["visit_idx"], dtype=int)
    ascertainment = list(data["ascertainment"])

    incidences: list[np.ndarray] = []
    onset_means: list[np.ndarray] = []
    for v in range(int(data["V"])):
        horizon = int(data["T"][v])
        ashore = np.asarray(data["ashore_hours"][v], dtype=float)[:, :horizon, :]
        aboard = np.asarray(data["aboard_hours"][v], dtype=float)[:, :horizon]
        share = np.asarray(data["secondary_share_raw"][v], dtype=float)
        share = share / share.sum()
        s = int(data["ship"][v]) - 1

        # (group, port) rate: crew carry the ratio and the repeat slope.
        crew_mult = float(rates.crew_ratio) * np.exp(
            rates.beta_repeat * crew_repeat[v],
        )
        rate = np.where(
            is_crew[:, None] > 0.0, crew_mult[None, :], 1.0,
        ) * np.where(
            visit_idx[v][None, :] > 0,
            lambda_visit[np.clip(visit_idx[v] - 1, 0, None)][None, :],
            0.0,
        )

        # Everything but the renewal term is a function of the epoch alone, so
        # only the secondary lag sum has to stay in a python loop.
        primary = (
            np.einsum("gtp,gp->gt", ashore, rate) + float(lambda_aboard[s]) * aboard
        )
        primary_total = primary.sum(axis=0)
        incidence = primary.copy()
        total = np.zeros(horizon, dtype=float)
        for t in range(horizon):
            lags = min(t, w_gen.size)
            secondary = 0.0
            if lags:
                secondary = float(r_onboard[s]) * float(
                    w_gen[:lags] @ total[t - lags : t][::-1],
                )
            if secondary:
                incidence[:, t] += secondary * share
            total[t] = primary_total[t] + secondary

        mu = np.zeros_like(incidence)
        for g in range(len(GROUPS)):
            mu[g] = np.convolve(incidence[g], f_inc)[:horizon]
        incidences.append(incidence)
        onset_means.append(float(ascertainment[v]) * mu)
    return incidences, onset_means


def expected_onsets_fleet(
    data: Mapping[str, Any],
    rates: FleetRates,
) -> list[np.ndarray]:
    """``mu_onset`` per voyage: onsets expected inside each voyage's window."""
    _, mu = fleet_forward_incidence(data, rates)
    return mu


def visit_hours(data: Mapping[str, Any]) -> np.ndarray:
    """Person-hours ashore per port visit — the hazard denominators."""
    hours = np.zeros(int(data["NV"]), dtype=float)
    visit_idx = np.asarray(data["visit_idx"], dtype=int)
    for v in range(int(data["V"])):
        horizon = int(data["T"][v])
        ashore = np.asarray(data["ashore_hours"][v], dtype=float)[:, :horizon, :]
        for p, idx in enumerate(visit_idx[v]):
            if idx > 0:
                hours[idx - 1] += float(ashore[:, :, p].sum())
    return hours


def wastewater_shares(
    data: Mapping[str, Any],
    rates: FleetRates,
) -> list[np.ndarray]:
    """Shedder prevalence per voyage-epoch, as a share of the people aboard.

    The quantity the wastewater channel observes: it is a function of the
    incidence curve only, so a port hazard and an onboard secondary that produce
    the same curve are indistinguishable here. That is the point — the channel
    constrains the curve and leaves the attribution to the clinical data (1.3).
    """
    incidences, _ = fleet_forward_incidence(data, rates)
    kernel = np.asarray(data["w_shed"], dtype=float)
    shares: list[np.ndarray] = []
    for v, incidence in enumerate(incidences):
        horizon = int(data["T"][v])
        persons = np.asarray(data["ww_persons"][v], dtype=float)[:horizon]
        shedders = shedder_prevalence(incidence.sum(axis=0), kernel)
        shares.append(shedders / np.clip(persons, 1.0, None))
    return shares


def wastewater_expected_fractions(
    data: Mapping[str, Any],
    rates: FleetRates,
    params: WastewaterParams,
) -> np.ndarray:
    """Expected read fraction at each pooled sample, in sample order."""
    n_samples = int(data["NW"])
    if n_samples == 0:
        return np.zeros(0, dtype=float)
    shares = wastewater_shares(data, rates)
    voyage = np.asarray(data["ww_voyage"], dtype=int) - 1
    epoch = np.asarray(data["ww_epoch"], dtype=int) - 1
    at_sample = np.asarray(
        [shares[voyage[i]][epoch[i]] for i in range(n_samples)], dtype=float,
    )
    return expected_read_fraction(
        at_sample, logit_base=params.logit_base, slope=params.slope,
    )


def wastewater_loglik(
    data: Mapping[str, Any],
    rates: FleetRates,
    params: WastewaterParams,
) -> float:
    """Beta-binomial log likelihood of the pooled reads; 0.0 with no samples."""
    if int(data["NW"]) == 0:
        return 0.0
    mean = wastewater_expected_fractions(data, rates, params)
    return float(
        beta_binomial_logpmf(
            np.asarray(data["ww_reads"], dtype=int),
            np.asarray(data["ww_total"], dtype=int),
            mean,
            params.concentration,
        ).sum(),
    )


def aboard_hours_by_ship(data: Mapping[str, Any]) -> np.ndarray:
    """Person-hours aboard per ship, summed over that ship's voyages."""
    hours = np.zeros(int(data["S"]), dtype=float)
    for v in range(int(data["V"])):
        horizon = int(data["T"][v])
        aboard = np.asarray(data["aboard_hours"][v], dtype=float)[:, :horizon]
        hours[int(data["ship"][v]) - 1] += float(aboard.sum())
    return hours


def _pad_cols(array: np.ndarray, width: int, *, dtype: type = float) -> list[list[Any]]:
    """Pad a ``(group, epoch)`` array out to ``width`` epochs with zeros."""
    padded = np.zeros((array.shape[0], width), dtype=dtype)
    padded[:, : array.shape[1]] = array
    return padded.tolist()


def _pad_rows(array: np.ndarray, height: int) -> list[list[float]]:
    """Pad an ``(epoch, port)`` array out to ``height`` epochs with zeros."""
    padded = np.zeros((height, array.shape[1]), dtype=float)
    padded[: array.shape[0], :] = array
    return padded.tolist()
