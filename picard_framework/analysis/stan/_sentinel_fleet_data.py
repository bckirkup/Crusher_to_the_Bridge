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
    DEFAULT_CONC_INTERCEPT_PRIOR_MEAN,
    DEFAULT_CONC_INTERCEPT_PRIOR_SD,
    DEFAULT_CONC_SIGMA_PRIOR_SCALE,
    DEFAULT_CONC_SLOPE_PRIOR_MEAN,
    DEFAULT_CONC_SLOPE_PRIOR_SD,
    DEFAULT_CONCENTRATION_PRIOR_LOG_SD,
    DEFAULT_CONCENTRATION_PRIOR_MEDIAN,
    DEFAULT_SLOPE_PRIOR_MEAN,
    DEFAULT_SLOPE_PRIOR_SD,
    SHARE_FLOOR,
    PooledConcentration,
    PooledSample,
    beta_binomial_logpmf,
    censored_normal_logpdf,
    expected_log10_concentration,
    expected_read_fraction,
    pool_concentrations,
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
# Provisioning-source hazards get the port-hazard prior shape by default: a
# voyage serves O(1e3-1e4) provisioned servings, so the shared median puts a
# handful of food-channel cases on it. Source-level spread gets the week-level
# scale — supply-side shocks are absorbed by sigma_source, and no separate
# per-receiving level exists (docs/sentinel/sentinel_source_market_revision.md).
DEFAULT_PROV_SD_PRIOR_SCALE = 0.75
# Boarding prevalence is a probability, so its mean sits on the logit scale.
# 2e-3 central with logit-sd 1.5 spans roughly 4e-5 to 4e-2 at two sd —
# declared, not fit; a wide enough band to leave the data the deciding vote.
DEFAULT_MARKET_PRIOR_MEDIAN = 2e-3
DEFAULT_MARKET_LOGIT_PRIOR_SD = 1.5
DEFAULT_MARKET_SD_PRIOR_SCALE = 0.75
# Voyage covariates multiply per-exposure risk; 0.5 sd keeps a coefficient
# centred on no-effect with room for a ~2.7x fold change at 1 sd.
DEFAULT_X_PRIOR_SD = 0.5


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
    baseline_prior_log_sd: float | None = None
    port_sd_prior_scale: float = DEFAULT_PORT_SD_PRIOR_SCALE
    visit_sd_prior_scale: float = DEFAULT_VISIT_SD_PRIOR_SCALE
    time_sd_prior_scale: float = DEFAULT_TIME_SD_PRIOR_SCALE
    ship_sd_prior_scale: float = DEFAULT_SHIP_SD_PRIOR_SCALE
    r_sd_prior_scale: float = DEFAULT_R_SD_PRIOR_SCALE
    r_prior_median: float = DEFAULT_R_LOG_PRIOR_MEDIAN
    r_prior_log_sd: float = DEFAULT_R_LOG_PRIOR_SD
    crew_ratio_prior_sd: float = DEFAULT_CREW_RATIO_PRIOR_SD
    repeat_prior_sd: float = DEFAULT_REPEAT_PRIOR_SD
    prov_sd_prior_scale: float = DEFAULT_PROV_SD_PRIOR_SCALE
    market_prior_median: float = DEFAULT_MARKET_PRIOR_MEDIAN
    market_logit_prior_sd: float = DEFAULT_MARKET_LOGIT_PRIOR_SD
    market_sd_prior_scale: float = DEFAULT_MARKET_SD_PRIOR_SCALE
    x_prior_sd: float = DEFAULT_X_PRIOR_SD

    def __post_init__(self) -> None:
        medians = (
            self.hazard_prior_median,
            self.baseline_prior_median,
            self.r_prior_median,
        )
        if any(m <= 0.0 for m in medians):
            raise ValueError("prior medians must be positive")
        if not 0.0 < self.market_prior_median < 1.0:
            raise ValueError("market_prior_median is a probability, in (0, 1)")

    def stan_fields(self) -> dict[str, float]:
        """The prior block of the Stan data dictionary."""
        baseline_log_sd = (
            float(self.prior_log_sd)
            if self.baseline_prior_log_sd is None
            else float(self.baseline_prior_log_sd)
        )
        return {
            "hazard_log_prior_mean": math.log(float(self.hazard_prior_median)),
            "hazard_log_prior_sd": float(self.prior_log_sd),
            "baseline_log_prior_mean": math.log(float(self.baseline_prior_median)),
            "baseline_log_prior_sd": baseline_log_sd,
            "r_log_prior_mean": math.log(float(self.r_prior_median)),
            "r_log_prior_sd": float(self.r_prior_log_sd),
            "port_sd_prior_scale": float(self.port_sd_prior_scale),
            "visit_sd_prior_scale": float(self.visit_sd_prior_scale),
            "time_sd_prior_scale": float(self.time_sd_prior_scale),
            "ship_sd_prior_scale": float(self.ship_sd_prior_scale),
            "r_sd_prior_scale": float(self.r_sd_prior_scale),
            "crew_ratio_prior_sd": float(self.crew_ratio_prior_sd),
            "repeat_prior_sd": float(self.repeat_prior_sd),
            # The provisioning channel borrows the port-hazard log prior:
            # per-serving and per-person-hour hazards live on the same scale.
            "prov_log_prior_mean": math.log(float(self.hazard_prior_median)),
            "prov_log_prior_sd": float(self.prior_log_sd),
            "prov_sd_prior_scale": float(self.prov_sd_prior_scale),
            "market_logit_prior_mean": _logit(float(self.market_prior_median)),
            "market_logit_prior_sd": float(self.market_logit_prior_sd),
            "market_sd_prior_scale": float(self.market_sd_prior_scale),
            "x_prior_sd": float(self.x_prior_sd),
        }


def _logit(p: float) -> float:
    return math.log(p / (1.0 - p))


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


def _source_ids(voyages: Sequence[FleetVoyage]) -> list[str]:
    """Sorted provisioning-source ids declared across the fleet's bundles."""
    return sorted(
        {src.source_id for fv in voyages for src in fv.bundle.provisioning},
    )


def _market_ids(voyages: Sequence[FleetVoyage]) -> list[str]:
    """Sorted embarkation-market ids the fleet's boarding pools were drawn from."""
    return sorted(
        {
            market_id
            for fv in voyages
            if fv.bundle.embarkation is not None
            for market_id in fv.bundle.embarkation.markets.values()
        },
    )


def _covariate_names(voyages: Sequence[FleetVoyage]) -> list[str]:
    """Sorted voyage-covariate names; a missing key reads as 0, not absent."""
    return sorted({name for fv in voyages for name in fv.bundle.covariates})


def _prov_matrix(
    fv: FleetVoyage,
    source_index: Mapping[str, int],
    t_max: int,
) -> np.ndarray:
    """``(group, epoch, source)`` servings for one voyage.

    Per-epoch rows are taken as declared; a ``servings_total`` is spread
    uniformly over its service window, the same no-invented-profile rule the
    ashore-hours builder uses for call windows.
    """
    prov = np.zeros((len(GROUPS), t_max, len(source_index)), dtype=float)
    horizon = int(fv.design.observation_end_epoch)
    for src in fv.bundle.provisioning:
        s = source_index[src.source_id]
        if src.servings_per_epoch:
            for stratum, row in src.servings_per_epoch.items():
                g = GROUPS.index(stratum)
                n = min(len(row), horizon)
                prov[g, :n, s] += np.asarray(row[:n], dtype=float)
            continue
        if not src.servings_total or src.service_window_epochs is None:
            continue
        first, last = src.service_window_epochs
        start = max(first - 1, 0)
        end = min(last, horizon)
        span = end - start
        if span <= 0:
            continue
        for stratum, total in src.servings_total.items():
            g = GROUPS.index(stratum)
            prov[g, start:end, s] += float(total) / float(span)
    return prov


def _embark_row(
    fv: FleetVoyage,
    market_index: Mapping[str, int],
) -> tuple[list[int], list[float], int]:
    """``(market_idx[G], embark_persons[G], embark_epoch)`` for one voyage.

    ``embark_persons`` defaults to the complement the bundle declares
    (``n_passengers``/``n_crew``); ``embark_epoch`` defaults to the first
    home-port call's arrival — the embarkation day's first epoch.
    """
    market_row = [0] * len(GROUPS)
    persons_row = [0.0] * len(GROUPS)
    embark = fv.bundle.embarkation
    embark_epoch = _embark_epoch_default(fv)
    if embark is None:
        return market_row, persons_row, embark_epoch
    complements = {
        "passenger": float(fv.bundle.n_passengers),
        "crew": float(fv.bundle.n_crew),
    }
    for g, stratum in enumerate(GROUPS):
        market_id = embark.markets.get(stratum)
        if market_id is None:
            continue
        market_row[g] = market_index[market_id] + 1
        persons_row[g] = float(embark.n_boarded.get(stratum, complements[stratum]))
    if embark.embark_epoch is not None:
        embark_epoch = int(embark.embark_epoch)
    horizon = int(fv.design.observation_end_epoch)
    return market_row, persons_row, min(max(embark_epoch, 1), horizon)


def _embark_epoch_default(fv: FleetVoyage) -> int:
    """First epoch of the embarkation home-port call (day 1's start)."""
    home = [c for c in fv.voyage.port_calls if c.is_home_port]
    if not home:
        return 1
    return int(min(c.arrival_epoch for c in home))


def _embark_call(fv: FleetVoyage) -> Any:
    """The day-1 home-port call — the embarkation leg — or ``None``."""
    home = sorted(
        (c for c in fv.voyage.port_calls if c.is_home_port),
        key=lambda c: (c.voyage_day, c.arrival_epoch),
    )
    return home[0] if home else None


def _voyage_source(
    fv: FleetVoyage,
    source_id: str,
) -> Any:
    """The voyage's provisioning record for ``source_id``, or ``None``."""
    return next(
        (src for src in fv.bundle.provisioning if src.source_id == source_id),
        None,
    )


def _visit_index_row(
    fv: FleetVoyage,
    ports: Sequence[str],
    visit_index: Mapping[str, int],
    week_index: Mapping[str, int],
    hours_by_visit: dict[str, float],
    ashore: np.ndarray,
    visit_port: list[int],
    visit_week: list[int],
) -> list[int]:
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
    return row


def _fill_voyage_exposures(
    voyages: Sequence[FleetVoyage],
    *,
    ports: Sequence[str],
    visit_index: Mapping[str, int],
    week_index: Mapping[str, int],
    t_max: int,
    visit_port: list[int],
    visit_week: list[int],
    hours_by_visit: dict[str, float],
) -> tuple[
    list[list[list[int]]],
    list[list[list[list[float]]]],
    list[list[list[float]]],
    list[list[float]],
    list[list[int]],
]:
    onsets: list[list[list[int]]] = []
    ashore_all: list[list[list[list[float]]]] = []
    aboard_all: list[list[list[float]]] = []
    shares: list[list[float]] = []
    visit_idx: list[list[int]] = []
    for fv in voyages:
        ashore = ashore_hours_by_epoch(fv.design, fv.voyage, ports)
        aboard = aboard_hours_by_epoch(fv.voyage, fv.bundle, ashore)
        counts = group_onsets(fv.bundle, fv.design.observation_end_epoch)
        ashore_all.append(
            [_pad_rows(ashore[g], t_max) for g in range(len(GROUPS))],
        )
        aboard_all.append(_pad_cols(aboard, t_max))
        onsets.append(_pad_cols(counts, t_max, dtype=int))
        share = aboard.sum(axis=1)
        if share.sum() <= 0.0:
            share = np.ones(len(GROUPS), dtype=float)
        shares.append([float(x) for x in share])
        visit_idx.append(
            _visit_index_row(
                fv, ports, visit_index, week_index, hours_by_visit, ashore,
                visit_port, visit_week,
            ),
        )
    return onsets, ashore_all, aboard_all, shares, visit_idx


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
    sources = _source_ids(voyages)
    markets = _market_ids(voyages)
    covariate_names = _covariate_names(voyages)
    source_index = {s: i for i, s in enumerate(sources)}
    market_index = {m: i for i, m in enumerate(markets)}

    visit_keys, week_keys, visit_index, week_index = _visit_layout(voyages, ports)
    crew_repeat = _crew_repeat_counts(voyages, ports)
    ships = sorted({fv.ship_id for fv in voyages})
    horizons = [int(fv.design.observation_end_epoch) for fv in voyages]
    t_max = max(horizons)

    visit_port: list[int] = [0] * len(visit_keys)
    visit_week: list[int] = [0] * len(visit_keys)
    hours_by_visit: dict[str, float] = dict.fromkeys(visit_keys, 0.0)
    onsets, ashore_all, aboard_all, shares, visit_idx = _fill_voyage_exposures(
        voyages,
        ports=ports,
        visit_index=visit_index,
        week_index=week_index,
        t_max=t_max,
        visit_port=visit_port,
        visit_week=visit_week,
        hours_by_visit=hours_by_visit,
    )
    prov_all = [_prov_matrix(fv, source_index, t_max).tolist() for fv in voyages]
    market_rows: list[list[int]] = []
    embark_persons: list[list[float]] = []
    embark_epochs: list[int] = []
    for fv in voyages:
        market_row, persons_row, embark_epoch = _embark_row(fv, market_index)
        market_rows.append(market_row)
        embark_persons.append(persons_row)
        embark_epochs.append(embark_epoch)

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
        "NS": len(sources),
        "NM": len(markets),
        "K": len(covariate_names),
        "prov_servings": prov_all,
        "market_idx": market_rows,
        "embark_persons": embark_persons,
        "embark_epoch": embark_epochs,
        "X": [
            [float(fv.bundle.covariates.get(name, 0.0)) for name in covariate_names]
            for fv in voyages
        ],
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
        channels=_MetaChannels(
            sources=sources,
            markets=markets,
            covariate_names=covariate_names,
            prov_all=prov_all,
            embark_epochs=embark_epochs,
        ),
    )
    meta["wastewater"] = ww["meta"]
    return data, meta


@dataclass(frozen=True)
class _MetaChannels:
    """The optional reverse-inference channels a fleet may declare."""

    sources: Sequence[str] = ()
    markets: Sequence[str] = ()
    covariate_names: Sequence[str] = ()
    prov_all: Sequence[Any] = ()
    embark_epochs: Sequence[int] = ()


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
    channels: _MetaChannels = _MetaChannels(),
) -> dict[str, Any]:
    sources = channels.sources
    markets = channels.markets
    covariate_names = channels.covariate_names
    prov_all = channels.prov_all
    embark_epochs = channels.embark_epochs
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
                "home_port": (
                    None
                    if _embark_call(fv) is None
                    else str(_embark_call(fv).port_id)
                ),
                "embark_window": (
                    None
                    if _embark_call(fv) is None
                    else [
                        int(_embark_call(fv).arrival_epoch),
                        int(_embark_call(fv).departure_epoch),
                    ]
                ),
                "home_port_has_ashore": bool(
                    _embark_call(fv) is not None
                    and any(
                        c.carries_ashore_exposure
                        for c in fv.voyage.port_calls
                        if c.is_home_port
                    )
                ),
                "markets": (
                    dict(fv.bundle.embarkation.markets)
                    if fv.bundle.embarkation is not None
                    else {}
                ),
                "sources": [src.source_id for src in fv.bundle.provisioning],
                "embark_epoch": int(embark_epochs[i]) if i < len(embark_epochs) else 1,
            }
            for i, fv in enumerate(voyages)
        ],
        "sources": [
            {
                "source_id": source_id,
                "voyages": [
                    fv.voyage_id
                    for fv in voyages
                    if _voyage_source(fv, source_id) is not None
                ],
                "total_servings": round(
                    sum(
                        float(np.asarray(prov_all[i], dtype=float)[:, :, s].sum())
                        for i, fv in enumerate(voyages)
                        if i < len(prov_all)
                        and _voyage_source(fv, source_id) is not None
                    ),
                    6,
                ),
                "first_service_epoch": {
                    fv.voyage_id: _voyage_source(fv, source_id).first_service_epoch
                    for fv in voyages
                    if _voyage_source(fv, source_id) is not None
                },
            }
            for s, source_id in enumerate(sources)
        ],
        "markets": [
            {
                "market_id": market_id,
                "voyages": [
                    fv.voyage_id
                    for i, fv in enumerate(voyages)
                    if fv.bundle.embarkation is not None
                    and market_id in fv.bundle.embarkation.markets.values()
                ],
                "strata": sorted(
                    {
                        stratum
                        for fv in voyages
                        if fv.bundle.embarkation is not None
                        for stratum, market in fv.bundle.embarkation.markets.items()
                        if market == market_id
                    },
                ),
            }
            for market_id in markets
        ],
        "covariate_names": list(covariate_names),
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


def _pool_ww_observations(
    voyages: Sequence[FleetVoyage],
    *,
    resolved: Any,
    cap: int,
    enabled: bool,
) -> tuple[list[Any], list[int], list[Any], list[int]]:
    pooled: list[PooledSample] = []
    voyage_of: list[int] = []
    conc: list[PooledConcentration] = []
    conc_voyage_of: list[int] = []
    if not enabled:
        return pooled, voyage_of, conc, conc_voyage_of
    for i, fv in enumerate(voyages):
        samples = pool_wastewater(
            fv.bundle,
            pathogen=resolved,
            observation_end_epoch=int(fv.design.observation_end_epoch),
            max_effective_reads=cap,
        )
        pooled.extend(samples)
        voyage_of.extend([i + 1] * len(samples))
        readings = pool_concentrations(
            fv.bundle,
            pathogen=resolved,
            observation_end_epoch=int(fv.design.observation_end_epoch),
        )
        conc.extend(readings)
        conc_voyage_of.extend([i + 1] * len(readings))
    return pooled, voyage_of, conc, conc_voyage_of


def _ww_stan_data(
    *,
    pooled: Sequence[PooledSample],
    voyage_of: Sequence[int],
    conc: Sequence[PooledConcentration],
    conc_voyage_of: Sequence[int],
    kernel: Any,
    persons: Sequence[Sequence[float]],
) -> dict[str, Any]:
    return {
        "NW": len(pooled),
        "ww_voyage": list(voyage_of),
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
        "NC": len(conc),
        "conc_voyage": list(conc_voyage_of),
        "conc_epoch": [int(c.epoch) for c in conc],
        "conc_log10": [float(c.log10_copies_per_l) for c in conc],
        "conc_censored": [int(bool(c.censored)) for c in conc],
        "conc_intercept_prior_mean": float(DEFAULT_CONC_INTERCEPT_PRIOR_MEAN),
        "conc_intercept_prior_sd": float(DEFAULT_CONC_INTERCEPT_PRIOR_SD),
        "conc_slope_prior_mean": float(DEFAULT_CONC_SLOPE_PRIOR_MEAN),
        "conc_slope_prior_sd": float(DEFAULT_CONC_SLOPE_PRIOR_SD),
        "conc_sigma_prior_scale": float(DEFAULT_CONC_SIGMA_PRIOR_SCALE),
    }


def _ww_meta(
    *,
    options: WastewaterOptions,
    resolved: Any,
    pooled: Sequence[PooledSample],
    conc: Sequence[PooledConcentration],
    cap: int,
    kernel: Any,
) -> dict[str, Any]:
    return {
        "enabled": bool(options.enabled),
        "pathogen": resolved,
        "n_pooled_samples": len(pooled),
        "n_concentration_samples": len(conc),
        "n_concentration_censored": sum(1 for c in conc if c.censored),
        "concentrations": [
            {
                "voyage_id": c.voyage_id,
                "epoch": c.epoch,
                "log10_copies_per_l": round(c.log10_copies_per_l, 6),
                "censored": bool(c.censored),
                "n_collection_points": c.n_collection_points,
                "n_detected": c.n_detected,
            }
            for c in conc
        ],
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


def _wastewater_block(
    voyages: Sequence[FleetVoyage],
    *,
    options: WastewaterOptions,
    t_max: int,
    aboard_all: Sequence[Sequence[Sequence[float]]],
    epoch_hours: float,
) -> dict[str, Any]:
    """Stan wastewater arrays plus the meta a report needs to read them."""
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
        head = aboard.sum(axis=0) / float(epoch_hours or 1.0)
        persons.append([float(max(x, 1.0)) for x in head])
    pooled, voyage_of, conc, conc_voyage_of = _pool_ww_observations(
        voyages, resolved=resolved, cap=cap, enabled=bool(options.enabled),
    )
    data = _ww_stan_data(
        pooled=pooled,
        voyage_of=voyage_of,
        conc=conc,
        conc_voyage_of=conc_voyage_of,
        kernel=kernel,
        persons=persons,
    )
    meta = _ww_meta(
        options=options,
        resolved=resolved,
        pooled=pooled,
        conc=conc,
        cap=cap,
        kernel=kernel,
    )
    if t_max and persons and len(persons[0]) != t_max:
        raise ValueError(
            "aboard hours were not padded to Tmax before the wastewater "
            f"denominators were built: {len(persons[0])} vs {t_max}",
        )
    return {"data": data, "meta": meta}


@dataclass(frozen=True)
class WastewaterParams:
    """The wastewater link parameters, separated from the hierarchy like ``FleetRates``.

    Carries both channels' links. The read parameters and the qPCR parameters are
    never used on the same observation, but they are one object because they are
    one measurement model of one latent shedder prevalence.
    """

    logit_base: float = DEFAULT_BASE_LOGIT_PRIOR_MEAN
    slope: float = DEFAULT_SLOPE_PRIOR_MEAN
    concentration: float = DEFAULT_CONCENTRATION_PRIOR_MEDIAN
    conc_intercept: float = DEFAULT_CONC_INTERCEPT_PRIOR_MEAN
    conc_slope: float = DEFAULT_CONC_SLOPE_PRIOR_MEAN
    conc_sigma: float = DEFAULT_CONC_SIGMA_PRIOR_SCALE


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
    kappa: Sequence[float] = ()       # per provisioning source (per serving)
    epsilon: Sequence[float] = ()     # per embarkation market (per capita)
    susceptibility: Sequence[float] = ()  # per voyage multiplier, empty = 1.0


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
    kappa = np.asarray(list(rates.kappa), dtype=float)
    epsilon = np.asarray(list(rates.epsilon), dtype=float)
    n_voyages = int(data["V"])
    susceptibility = (
        np.asarray(list(rates.susceptibility), dtype=float)
        if len(rates.susceptibility) == n_voyages
        else np.ones(n_voyages, dtype=float)
    )
    is_crew = np.asarray(data["is_crew"], dtype=float)
    crew_repeat = np.asarray(data["crew_repeat"], dtype=float)
    visit_idx = np.asarray(data["visit_idx"], dtype=int)
    ascertainment = list(data["ascertainment"])

    incidences: list[np.ndarray] = []
    onset_means: list[np.ndarray] = []
    for v in range(int(data["V"])):
        incidence, mu = _voyage_forward_incidence(
            data,
            v,
            w_gen=w_gen,
            f_inc=f_inc,
            lambda_visit=lambda_visit,
            lambda_aboard=lambda_aboard,
            r_onboard=r_onboard,
            kappa=kappa,
            epsilon=epsilon,
            susceptibility=susceptibility,
            is_crew=is_crew,
            crew_repeat=crew_repeat,
            visit_idx=visit_idx,
            rates=rates,
        )
        incidences.append(incidence)
        onset_means.append(float(ascertainment[v]) * mu)
    return incidences, onset_means


def _voyage_import_injections(
    data: Mapping[str, Any],
    v: int,
    horizon: int,
    *,
    susc: float,
    kappa: np.ndarray,
    epsilon: np.ndarray,
) -> np.ndarray:
    """Provisioned-serving and embarkation-market injections for one voyage."""
    injected = np.zeros((int(data["G"]), horizon), dtype=float)
    if kappa.size and int(data.get("NS", 0)) > 0:
        prov = np.asarray(data["prov_servings"][v], dtype=float)[
            :, :horizon, :
        ]
        injected += susc * np.einsum("gts,s->gt", prov, kappa)
    if epsilon.size and int(data.get("NM", 0)) > 0:
        market_row = np.asarray(data["market_idx"][v], dtype=int) - 1
        persons_row = np.asarray(data["embark_persons"][v], dtype=float)
        embark_t = int(data["embark_epoch"][v]) - 1
        for g in range(int(data["G"])):
            m = int(market_row[g])
            if m >= 0 and 0 <= embark_t < horizon:
                injected[g, embark_t] += (
                    susc * float(epsilon[m]) * float(persons_row[g])
                )
    return injected


def _voyage_forward_incidence(
    data: Mapping[str, Any],
    v: int,
    *,
    w_gen: np.ndarray,
    f_inc: np.ndarray,
    lambda_visit: np.ndarray,
    lambda_aboard: np.ndarray,
    r_onboard: np.ndarray,
    kappa: np.ndarray,
    epsilon: np.ndarray,
    susceptibility: np.ndarray,
    is_crew: np.ndarray,
    crew_repeat: np.ndarray,
    visit_idx: np.ndarray,
    rates: FleetRates,
) -> tuple[np.ndarray, np.ndarray]:
    """``(incidence, mu_onset)`` for voyage ``v`` — the Stan recursion verbatim."""
    horizon = int(data["T"][v])
    ashore = np.asarray(data["ashore_hours"][v], dtype=float)[:, :horizon, :]
    aboard = np.asarray(data["aboard_hours"][v], dtype=float)[:, :horizon]
    share = np.asarray(data["secondary_share_raw"][v], dtype=float)
    share = share / share.sum()
    s = int(data["ship"][v]) - 1
    susc = float(susceptibility[v])

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
        susc * np.einsum("gtp,gp->gt", ashore, rate)
        + float(lambda_aboard[s]) * aboard
        + _voyage_import_injections(
            data, v, horizon, susc=susc, kappa=kappa, epsilon=epsilon,
        )
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
    return incidence, mu


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


def concentration_expected_log10(
    data: Mapping[str, Any],
    rates: FleetRates,
    params: WastewaterParams,
) -> np.ndarray:
    """Expected log10 copies/L at each pooled qPCR result, in result order."""
    n_conc = int(data.get("NC", 0))
    if n_conc == 0:
        return np.zeros(0, dtype=float)
    shares = wastewater_shares(data, rates)
    voyage = np.asarray(data["conc_voyage"], dtype=int) - 1
    epoch = np.asarray(data["conc_epoch"], dtype=int) - 1
    at_sample = np.asarray(
        [shares[voyage[i]][epoch[i]] for i in range(n_conc)], dtype=float,
    )
    return expected_log10_concentration(
        at_sample, intercept=params.conc_intercept, slope=params.conc_slope,
    )


def concentration_loglik(
    data: Mapping[str, Any],
    rates: FleetRates,
    params: WastewaterParams,
) -> float:
    """Tobit log likelihood of the pooled qPCR results; 0.0 with no results."""
    if int(data.get("NC", 0)) == 0:
        return 0.0
    mean = concentration_expected_log10(data, rates, params)
    return float(
        censored_normal_logpdf(
            np.asarray(data["conc_log10"], dtype=float),
            mean,
            params.conc_sigma,
            np.asarray(data["conc_censored"], dtype=int).astype(bool),
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
