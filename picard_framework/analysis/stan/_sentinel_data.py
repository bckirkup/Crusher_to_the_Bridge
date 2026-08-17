"""Stan data assembly for the single-ship sentinel attribution model.

Turns the pure-numpy exposure design (PR 4) into the epoch-by-group arrays
``sentinel_attribution.stan`` consumes. Two conventions matter and are easy to
get wrong:

- **hours are raw, not censoring-discounted.** ``ExposureCell.log_offset``
  folds ``P(onset <= T_end)`` into the offset for a cell-level Poisson fit; the
  Stan model instead truncates the onset convolution at ``T``, which is the same
  correction applied once. Passing effective hours here would apply it twice.
- **strata collapse to person groups.** The four exposure strata are two person
  groups (passenger, crew) crossed with ashore/aboard hours. Keeping them as
  groups and splitting the *hours* is what makes ``lambda_port`` a rate per
  person-hour ashore rather than a group fixed effect.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

import numpy as np

from picard_framework.analysis.sentinel.exposure import (
    CREW_ASHORE,
    PAX_ASHORE,
    ExposureDesign,
    ashore_epochs,
    min_inter_port_hours,
)
from picard_framework.analysis.sentinel.incubation import (
    DelayDistribution,
    port_resolution_adequate,
)
from picard_framework.analysis.sentinel.itinerary import Voyage
from picard_framework.analysis.sentinel.observations import ObservationBundle

PASSENGER = "passenger"
CREW = "crew"
GROUPS = (PASSENGER, CREW)

_GROUP_OF_STRATUM = {PAX_ASHORE: PASSENGER, CREW_ASHORE: CREW}

# Rates per person-hour, centred on "about one case": a port call is O(1e4)
# person-hours ashore and a voyage O(1e5-1e6) person-hours aboard, so these
# medians put a handful of imported and a handful of background cases on a
# voyage. The log sd is deliberately wide (a factor of ~50 either way inside
# 90%) because neither rate is known to an order of magnitude, and a prior
# median two orders below the truth would push the fit to explain onboard cases
# with port hazards instead.
DEFAULT_HAZARD_PRIOR_MEDIAN = 1.0e-4
DEFAULT_BASELINE_PRIOR_MEDIAN = 1.0e-5
DEFAULT_PRIOR_LOG_SD = 2.0
DEFAULT_PORT_SD_PRIOR_SCALE = 0.75
# CTB Stage B norovirus hurdle posterior (mega); see sentinel_stan_fix_spec.md.
DEFAULT_R_PRIOR_MEAN = 0.06
DEFAULT_R_PRIOR_SD = 0.02


def attribution_ports(design: ExposureDesign) -> tuple[str, ...]:
    """Ports with positive ashore exposure, in stable order."""
    hours: dict[str, float] = {}
    for cell in design.port_cells:
        hours[cell.port_id] = hours.get(cell.port_id, 0.0) + cell.person_hours_ashore
    return tuple(sorted(p for p, h in hours.items() if h > 0.0))


def ashore_hours_by_epoch(
    design: ExposureDesign,
    voyage: Voyage,
    ports: Sequence[str],
) -> np.ndarray:
    """``(group, epoch, port)`` person-hours ashore.

    A port's pooled hours are spread evenly across the ashore epochs of its
    calls: the ledger records hours per port, not per epoch, and a within-day
    exposure profile would be invented precision. Epoch resolution still
    matters because it is what links a port to an onset through the incubation
    pmf.
    """
    n_epochs = int(design.observation_end_epoch)
    index = {port_id: i for i, port_id in enumerate(ports)}
    epochs_of_port: dict[str, list[int]] = {}
    for call in voyage.port_calls:
        if call.port_id not in index:
            continue
        epochs_of_port.setdefault(call.port_id, []).extend(
            e for e in ashore_epochs(voyage, call) if 1 <= e <= n_epochs
        )
    hours = np.zeros((len(GROUPS), n_epochs, len(ports)), dtype=float)
    for cell in design.port_cells:
        group = _GROUP_OF_STRATUM.get(cell.stratum)
        if group is None or cell.port_id not in index:
            continue
        epochs = epochs_of_port.get(cell.port_id) or []
        if not epochs or cell.person_hours_ashore <= 0.0:
            continue
        per_epoch = cell.person_hours_ashore / len(epochs)
        g = GROUPS.index(group)
        p = index[cell.port_id]
        for epoch in epochs:
            hours[g, epoch - 1, p] += per_epoch
    return hours


def aboard_hours_by_epoch(
    voyage: Voyage,
    bundle: ObservationBundle,
    ashore: np.ndarray,
) -> np.ndarray:
    """``(group, epoch)`` person-hours aboard, net of the hours spent ashore."""
    n_epochs = ashore.shape[1]
    heads = (
        bundle.n_passengers or voyage.n_passengers,
        bundle.n_crew or voyage.n_crew,
    )
    per_epoch = np.array(heads, dtype=float) * float(voyage.epoch_duration_hours)
    aboard = np.repeat(per_epoch[:, None], n_epochs, axis=1)
    return np.clip(aboard - ashore.sum(axis=2), 0.0, None)


def group_onsets(bundle: ObservationBundle, observation_end_epoch: int) -> np.ndarray:
    """``(group, epoch)`` observed onset counts."""
    counts = np.zeros((len(GROUPS), int(observation_end_epoch)), dtype=int)
    for case in bundle.clinical_cases:
        idx = case.onset_epoch - 1
        if 0 <= idx < counts.shape[1]:
            counts[GROUPS.index(CREW if case.crew else PASSENGER), idx] += 1
    return counts


def build_sentinel_attribution_data(
    design: ExposureDesign,
    voyage: Voyage,
    bundle: ObservationBundle,
    incubation: DelayDistribution,
    generation: DelayDistribution,
    *,
    hazard_prior_median: float = DEFAULT_HAZARD_PRIOR_MEDIAN,
    baseline_prior_median: float = DEFAULT_BASELINE_PRIOR_MEDIAN,
    prior_log_sd: float = DEFAULT_PRIOR_LOG_SD,
    port_sd_prior_scale: float = DEFAULT_PORT_SD_PRIOR_SCALE,
    r_prior_mean: float = DEFAULT_R_PRIOR_MEAN,
    r_prior_sd: float = DEFAULT_R_PRIOR_SD,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """``(stan_data, meta)`` for one voyage.

    ``meta`` carries the port order the posterior indices refer to, plus the
    port-resolution verdict (spec 1.8): when the incubation IQR exceeds the
    shortest inter-port interval the per-port estimates are not separable and
    must be read as a port-window set.
    """
    if hazard_prior_median <= 0.0 or baseline_prior_median <= 0.0:
        raise ValueError("prior medians must be positive rates per person-hour")
    ports = attribution_ports(design)
    if not ports:
        raise ValueError(
            f"voyage {design.voyage_id}: no port has positive ashore exposure, "
            "so no port hazard is identified",
        )
    ashore = ashore_hours_by_epoch(design, voyage, ports)
    aboard = aboard_hours_by_epoch(voyage, bundle, ashore)
    onsets = group_onsets(bundle, design.observation_end_epoch)
    lagged = generation.strictly_lagged().weights[1:]
    share = aboard.sum(axis=1)
    if share.sum() <= 0.0:
        share = np.ones(len(GROUPS), dtype=float)

    data = {
        "T": int(design.observation_end_epoch),
        "P": len(ports),
        "G": len(GROUPS),
        "L_inc": int(incubation.weights.size),
        "L_gen": int(lagged.size),
        "onsets": onsets.tolist(),
        "ashore_hours": [ashore[g].tolist() for g in range(len(GROUPS))],
        "aboard_hours": aboard.tolist(),
        "f_inc_raw": incubation.weights.tolist(),
        "w_gen_raw": lagged.tolist(),
        "secondary_share_raw": share.tolist(),
        "ascertainment": float(design.ascertainment),
        "hazard_log_prior_mean": math.log(float(hazard_prior_median)),
        "hazard_log_prior_sd": float(prior_log_sd),
        "baseline_log_prior_mean": math.log(float(baseline_prior_median)),
        "baseline_log_prior_sd": float(prior_log_sd),
        "r_prior_mean": float(r_prior_mean),
        "r_prior_sd": float(r_prior_sd),
        "port_sd_prior_scale": float(port_sd_prior_scale),
    }
    min_gap = min_inter_port_hours(voyage)
    meta = {
        "model": "sentinel_attribution",
        "voyage_id": design.voyage_id,
        "ship_id": design.ship_id,
        "ports": list(ports),
        "port_visit_keys": _visit_keys(design, ports),
        "groups": list(GROUPS),
        "epoch_duration_hours": float(voyage.epoch_duration_hours),
        "observation_end_epoch": int(design.observation_end_epoch),
        "n_cases": int(onsets.sum()),
        "person_hours_ashore": {
            port_id: float(ashore[:, :, i].sum()) for i, port_id in enumerate(ports)
        },
        "person_hours_aboard": float(aboard.sum()),
        "ascertainment": float(design.ascertainment),
        "censoring_corrected": any(c.censoring_corrected for c in design.port_cells),
        "incubation_iqr_hours": round(incubation.iqr_hours, 3),
        "min_inter_port_hours": None if math.isinf(min_gap) else round(min_gap, 3),
        "port_resolution_adequate": port_resolution_adequate(incubation, min_gap),
    }
    return data, meta


def _visit_keys(design: ExposureDesign, ports: Sequence[str]) -> dict[str, str]:
    keys: dict[str, str] = {}
    for cell in design.port_cells:
        if cell.port_id in ports:
            keys[cell.port_id] = cell.port_visit_key
    return keys


def forward_incidence(
    data: Mapping[str, Any],
    *,
    lambda_port: Sequence[float],
    lambda_aboard: float,
    r_onboard: float,
) -> tuple[np.ndarray, np.ndarray]:
    """``(incidence, mu_onset)`` by group and epoch, mirroring the Stan model.

    Same recursion as ``sentinel_attribution.stan``: the test suite uses it to
    generate synthetic onsets from known hazards without a Stan toolchain, and
    a divergence between the two is a bug in one of them. The Stan model adds a
    1e-9 floor to ``mu_onset`` so an empty-exposure epoch cannot make a nonzero
    count impossible; that floor is left off here to keep a zero hazard exactly
    zero.
    """
    ashore = np.asarray(data["ashore_hours"], dtype=float)
    aboard = np.asarray(data["aboard_hours"], dtype=float)
    f_inc = np.asarray(data["f_inc_raw"], dtype=float)
    f_inc = f_inc / f_inc.sum()
    w_gen = np.asarray(data["w_gen_raw"], dtype=float)
    w_gen = w_gen / w_gen.sum()
    share = np.asarray(data["secondary_share_raw"], dtype=float)
    share = share / share.sum()
    rates = np.asarray(list(lambda_port), dtype=float)
    n_groups, n_epochs = aboard.shape

    incidence = np.zeros((n_groups, n_epochs), dtype=float)
    total = np.zeros(n_epochs, dtype=float)
    for t in range(n_epochs):
        lags = min(t, w_gen.size)
        secondary = 0.0
        if lags:
            secondary = float(r_onboard) * float(
                w_gen[:lags] @ total[t - lags : t][::-1],
            )
        imported = ashore[:, t, :] @ rates + float(lambda_aboard) * aboard[:, t]
        incidence[:, t] = imported + secondary * share
        total[t] = incidence[:, t].sum()

    mu = np.zeros_like(incidence)
    for g in range(n_groups):
        mu[g] = np.convolve(incidence[g], f_inc)[:n_epochs]
    return incidence, float(data["ascertainment"]) * mu


def expected_onsets_from_data(
    data: Mapping[str, Any],
    *,
    lambda_port: Sequence[float],
    lambda_aboard: float,
    r_onboard: float,
) -> np.ndarray:
    """``mu_onset`` by group and epoch: onsets expected inside the window."""
    _, mu = forward_incidence(
        data,
        lambda_port=lambda_port,
        lambda_aboard=lambda_aboard,
        r_onboard=r_onboard,
    )
    return mu
