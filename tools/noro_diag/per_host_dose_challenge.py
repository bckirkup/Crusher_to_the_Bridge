#!/usr/bin/env python3
"""Per-host credited-dose / evaluated-challenge join, for ledger NORO-SUSCEPT-02.

Purpose
-------
NORO-SUSCEPT-01 leaves one open finding: a whole-run summed naive hazard of
0.197 against 394,281 GEC credited over 353,711 accumulate calls is an
ordinary draw only if the dose effectively reached one or two hosts, while the
recovered per-host maximum (49,572 GEC, 12.6% of the total) needs at least
eight. Credited dose and evaluated hazard therefore look like they are taken
over different host sets, or over different quantities. This diagnostic
measures the join instead of arguing about it: for one voyage it records, per
host, the dose the accumulator credited, the dose the challenge actually read,
and the hazard the engine actually evaluated.

Method
------
The engine is not modified and, unless ``--alpha`` is given, no configuration
value is overridden. Every
observation is taken by wrapping bound methods on ``TransmissionCore`` (and the
module-level ``draw_emesis_schedule``) for the duration of one run:

* ``_accumulate``            -- call count and credited dose, per pathway.
* ``_execute_pathogen_pathways`` -- which pathogen the accumulate calls belong
  to, and the raw per-agent dose map before route efficiency and NPI scaling.
* ``_merge_pathogen_doses``  -- per-agent dose entering the epoch's challenge
  map, before (raw) and after (scaled) ``susceptibility_multiplier``.
* ``_resolve_pathogen_challenge`` -- per-agent, per-epoch entry state: resident
  infection, immunity, secretor phenotype, protection, and the dose the
  challenge read.
* ``_dose_response_hazard``  -- the witness that a challenge was *evaluated*:
  the effective dose the hazard was computed on, the host's persistent
  frailty, and the hazard itself.
* ``draw_emesis_schedule`` / ``_emesis_phase`` / ``_emit_emesis`` /
  ``_emesis_patch_pickup`` / ``_emesis_patch_pickup_one`` -- the emesis chain's
  witness counters, from schedule draw to patch pickup.
* ``_deliver_fomite_requests`` / ``_hand_to_mouth_dose`` -- the fomite transfer
  chain's own reconciliation: surface mass offered, mass requested, mass
  delivered to hands, and dose ingested, so a dose that collapses between the
  surface pool and the accumulator is localised to a term rather than inferred.
* ``_fomite_pickup_request_for_area`` -- the per-touch surface->hand factor
  (ledger NORO-TRANSFER-PRODUCT-01): for every clean pickup call the witness
  records ``f_touch = (request / surface_mass) / contacts`` bucketed by
  source (zone pool vs emesis patch) and zone class, so the per-touch chain
  -- the layer literature transfer efficiencies are commensurable with -- is
  measured rather than inferred from whole-voyage bookkeeping ratios. The
  hand->mouth wrapper likewise records ``dose / hand_load`` per contact,
  split eating/non-eating, and the deliver wrapper records how often demand
  exceeded the pool (the ``_delivery_scale`` saturation path).

Wrappers only read. ``_challenge_protection`` and ``is_infected_with`` consume
no RNG, so calling them from a wrapper cannot perturb the stream; nothing here
draws from the engine's generator. The counterfactual frailties used for the
never-challenged hosts come from a separate, declared generator and are
labelled as such.

Inputs
------
``--platform`` (default ``classic_cruise_1900``) at its declared complement,
``--epochs``, ``--seed`` (repeat for paired seeds), the shipped ``--bundle``
pathogen bundle (both the run and the readout arithmetic). Without ``--alpha``
no pathogen or run override is written: an arm of this diagnostic differs from
a shipped run only by the wrappers, which are read-only. With ``--alpha`` (rejected
outside the frozen NORO-SUSCEPT-03 interval [0.072, 0.161]) the run carries
exactly one override, a ``pathogen_overrides`` patch on
``norwalk_gi.dose_response`` that sets ``alpha`` to the requested value and
pins ``beta`` at the profile value; everything else is unchanged.

Outputs
-------
One gzipped JSON per seed at ``--out`` (``*.json.gz``; gzipped because the
per-host table carries ``*_epochs`` count keys, which the repository's unit
safety guard reads as an undeclared time unit in any plain ``.json`` on disk):
the per-host table (credited dose, crediting epochs, frailty, challenge and
evaluation counts, state tallies), the
reconciliation chain from accumulated dose to summed evaluated hazard, the
dose-concentration curve (how many hosts hold 90% of the credited dose), and
the emesis witness counters. A summary of the same is printed.

Runtime
-------
About 25 min per seed at 1,910 agents x 288 epochs on one core.

Nothing here fits or selects a parameter value.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines import initiation as initiation_module  # noqa: E402
from engines import natural_history as natural_history_module  # noqa: E402
from engines import transmission_core as tc  # noqa: E402
from engines.fomite_surfaces import (  # noqa: E402
    load_declared_share_table,
)
from picard_framework.run_spec import CRUSHER_CONFIG_REL, PicardRunSpec  # noqa: E402
from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402
from simulation_utils import asset_defaults  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_child_path,
    validated_open,
)
from simulation_utils.platform_complement import declared_total  # noqa: E402
from tools.noro_diag.dose_response import load_dose_response  # noqa: E402

# Frailties for hosts the engine never challenged are not in the run: the
# engine draws one lazily at the first hazard evaluation. A counterfactual
# needs one per host, so it comes from this declared generator and is reported
# separately from anything the run measured.
COUNTERFACTUAL_SEED = 20260919

# Fixed bin spec for the per-touch transfer-factor histograms
# (``transfer_product_witness``). The edges are emitted in the summary so a
# readout never has to reconstruct them.
F_TOUCH_LOG_MIN = -12.0
F_TOUCH_LOG_MAX = 1.0
F_TOUCH_LOG_BIN = 0.25
F_TOUCH_BINS = round((F_TOUCH_LOG_MAX - F_TOUCH_LOG_MIN) / F_TOUCH_LOG_BIN)


def _log10_hist_index(value: float) -> int:
    """Bin index of a log10 ratio, clipped into the first/last bin."""
    index = int((value - F_TOUCH_LOG_MIN) / F_TOUCH_LOG_BIN)
    return min(F_TOUCH_BINS - 1, max(0, index))


def _touch_bucket() -> dict[str, Any]:
    """Accumulators for one (source, zone_class) surface->hand bucket."""
    return {
        "calls": 0,
        "calls_clean": 0,
        "calls_capped": 0,
        "calls_confined": 0,
        "calls_zero_mass": 0,
        "sum_request_gec": 0.0,
        "sum_surface_mass_gec": 0.0,
        "sum_contacts": 0.0,
        "sum_surface_area_m2": 0.0,
        "sum_log10_f_touch": 0.0,
        "sum_sq_log10_f_touch": 0.0,
        "min_log10_f_touch": math.inf,
        "max_log10_f_touch": -math.inf,
        "hist_log10_f_touch": [0] * F_TOUCH_BINS,
        "hist_underflow": 0,
        "hist_overflow": 0,
    }


def _mouth_bucket() -> dict[str, Any]:
    """Accumulators for one hand->mouth ``dose / hand_load`` bucket."""
    return {
        "calls": 0,
        "calls_capped": 0,
        "sum_log10_ratio": 0.0,
        "sum_sq_log10_ratio": 0.0,
        "min_log10_ratio": math.inf,
        "max_log10_ratio": -math.inf,
        "hist_log10_ratio": [0] * F_TOUCH_BINS,
        "hist_underflow": 0,
        "hist_overflow": 0,
    }


def _hist_add(bucket: dict[str, Any], hist_key: str, value: float) -> None:
    """File one log10 value into a bucket's fixed-bin histogram."""
    if value < F_TOUCH_LOG_MIN:
        bucket["hist_underflow"] += 1
    elif value >= F_TOUCH_LOG_MAX:
        bucket["hist_overflow"] += 1
    bucket[hist_key][_log10_hist_index(value)] += 1


def f_touch_bin_edges() -> list[float]:
    """The emitted histogram bin edges, explicit so readouts never guess."""
    return [
        F_TOUCH_LOG_MIN + index * F_TOUCH_LOG_BIN
        for index in range(F_TOUCH_BINS + 1)
    ]


@dataclass
class HostRecord:
    """One host's credited dose and challenge history for one pathogen."""

    credited_raw: float = 0.0
    credited_scaled: float = 0.0
    crediting_epochs: int = 0
    susceptibility_multiplier: float = 1.0
    frailty: float | None = None
    challenge_calls: int = 0
    challenge_dose_read: float = 0.0
    evaluated: int = 0
    evaluated_dose: float = 0.0
    hazard_sum: float = 0.0
    reasons: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    # State tallies over crediting epochs only, which is the join the ledger
    # question is about: what was true of the host at the epochs it was
    # credited dose.
    credited_epochs_infected: int = 0
    credited_epochs_immune: int = 0
    credited_epochs_secretor_negative: int = 0
    credited_epochs_challenge_evaluated: int = 0


@dataclass
class Recorder:
    """Every observation taken from one instrumented run."""

    pathogen_id: str
    epoch: int = 0
    current_pathogen: str | None = None
    accumulate_calls: dict[str, int] = field(
        default_factory=lambda: defaultdict(int),
    )
    accumulate_dose: dict[str, float] = field(
        default_factory=lambda: defaultdict(float),
    )
    pathway_dose: dict[str, float] = field(
        default_factory=lambda: defaultdict(float),
    )
    pathway_calls: dict[str, int] = field(
        default_factory=lambda: defaultdict(int),
    )
    hosts: dict[int, HostRecord] = field(default_factory=dict)
    emesis: dict[str, float] = field(
        default_factory=lambda: defaultdict(float),
    )
    fomite: dict[str, float] = field(
        default_factory=lambda: defaultdict(float),
    )
    emesis_units: dict[str, list[str]] = field(default_factory=dict)
    # Challenge-acquired infections: one row per susceptible->infected
    # transition seen across ``_resolve_pathogen_challenge``.
    acquisitions: list[dict[str, Any]] = field(default_factory=list)
    acquired_ids: set[int] = field(default_factory=set)
    import_ids: set[int] = field(default_factory=set)
    # Slot the hazard wrapper writes and the challenge wrapper reads, so that
    # "a challenge was evaluated this epoch" is a witnessed fact rather than a
    # re-derivation of the engine's early returns.
    hazard_witness: tuple[int, str, float, float, float] | None = None
    top_host_rows: list[dict[str, Any]] = field(default_factory=list)
    # Per-touch transfer witness (ledger NORO-TRANSFER-PRODUCT-01). Depth
    # counter, not a bool, so a nested call can never leave the flag set:
    # nonzero while ``_emesis_patch_pickup_one``'s original is on the stack,
    # which is how a ``_fomite_pickup_request_for_area`` call knows it was
    # made for a localised patch rather than the zone-wide pool.
    patch_depth: int = 0
    surface_touch: dict[str, dict[str, dict[str, Any]]] = field(
        default_factory=lambda: defaultdict(
            lambda: defaultdict(_touch_bucket),
        ),
    )
    mouth_touch: dict[str, dict[str, Any]] = field(
        default_factory=lambda: defaultdict(_mouth_bucket),
    )
    delivery_scale: dict[str, float] = field(
        default_factory=lambda: defaultdict(float),
    )
    # The fomite-representation arm the engine actually ran, captured off
    # the TransmissionCore by the deposit wrapper so a dropped override is
    # a witnessed fact rather than an assumption.
    fomite_representation_seen: str | None = None
    fomite_touch_share_seen: str | None = None
    # Per-item-class fomite witness (NORO-TOUCH-SHARE-01): pool-level
    # requested/delivered/calls/capped_calls per class, and per-host
    # delivered mass per class reconstructed in the delivery wrapper from
    # the engine's uniform per-class scale.
    fomite_by_class: dict[str, dict[str, float]] = field(
        default_factory=lambda: defaultdict(
            lambda: {
                "requested_gec": 0.0,
                "delivered_gec": 0.0,
                "calls": 0,
                "capped_calls": 0,
            },
        ),
    )
    fomite_host_class_gec: dict[int, dict[str, float]] = field(
        default_factory=lambda: defaultdict(
            lambda: defaultdict(float),
        ),
    )

    def host(self, agent_id: int) -> HostRecord:
        """Return (creating if needed) one host's record."""
        record = self.hosts.get(agent_id)
        if record is None:
            record = HostRecord()
            self.hosts[agent_id] = record
        return record


def _wrap_accumulate(core_cls: type, rec: Recorder) -> Any:
    original = core_cls._accumulate

    def wrapper(
        self: Any,
        target_id: int,
        pathway: str,
        dose: float,
        *args: Any,
        **kwargs: Any,
    ) -> float:
        credited = original(self, target_id, pathway, dose, *args, **kwargs)
        pathogen = rec.current_pathogen or "unknown"
        rec.accumulate_calls[pathogen] += 1
        rec.accumulate_dose[pathogen] += credited
        if pathogen == rec.pathogen_id:
            rec.pathway_calls[pathway] += 1
            rec.pathway_dose[pathway] += credited
        return credited

    return wrapper


def _wrap_execute_pathways(core_cls: type, rec: Recorder) -> Any:
    original = core_cls._execute_pathogen_pathways

    def wrapper(self: Any, epoch: int, *args: Any, **kwargs: Any) -> None:
        pathogen_id = kwargs.get("pathogen_id")
        if pathogen_id is None:
            # Positional call: after ``epoch`` the engine passes agents,
            # zone_occupants, zone_pathogen_mass, hvac_downstream_zones and
            # multi_pathogen_mass before pathogen_id.
            pathogen_id = args[5]
        previous = rec.current_pathogen
        rec.current_pathogen = pathogen_id
        rec.epoch = int(epoch)
        rec.fomite_representation_seen = self.fomite_representation
        if self._per_surface is not None:
            rec.fomite_touch_share_seen = self._per_surface.cfg.touch_share
        try:
            return original(self, epoch, *args, **kwargs)
        finally:
            rec.current_pathogen = previous

    return wrapper


def _wrap_merge(core_cls: type, rec: Recorder) -> Any:
    original = core_cls._merge_pathogen_doses

    def wrapper(
        self: Any,
        agents: list[Any],
        pathogen_id: str,
        p_agent_doses: dict[int, float],
        *args: Any,
        **kwargs: Any,
    ) -> dict[int, float]:
        susceptibility = original(
            self, agents, pathogen_id, p_agent_doses, *args, **kwargs,
        )
        if pathogen_id != rec.pathogen_id:
            return susceptibility
        by_id = {agent.agent_id: agent for agent in agents}
        for agent_id, dose in p_agent_doses.items():
            if dose <= 0.0:
                continue
            record = rec.host(agent_id)
            multiplier = float(susceptibility.get(agent_id, 1.0))
            record.credited_raw += float(dose)
            record.credited_scaled += float(dose) * multiplier
            record.crediting_epochs += 1
            record.susceptibility_multiplier = multiplier
            agent = by_id.get(agent_id)
            if agent is None:
                continue
            if agent.is_infected_with(pathogen_id):
                record.credited_epochs_infected += 1
            if bool(getattr(agent, "immune", False)):
                record.credited_epochs_immune += 1
            if bool(
                getattr(agent, "secretor_negative_by_pathogen", {}).get(
                    pathogen_id, False,
                ),
            ):
                record.credited_epochs_secretor_negative += 1
        return susceptibility

    return wrapper


def _wrap_hazard(core_cls: type, rec: Recorder) -> Any:
    original = core_cls._dose_response_hazard

    def wrapper(
        self: Any, agent: Any, pathogen_id: str, effective_dose: float,
    ) -> float:
        hazard = original(self, agent, pathogen_id, effective_dose)
        frailty = float(
            agent.dose_response_susceptibility.get(pathogen_id, 0.0),
        )
        rec.hazard_witness = (
            int(agent.agent_id), str(pathogen_id),
            float(effective_dose), frailty, float(hazard),
        )
        if pathogen_id == rec.pathogen_id:
            record = rec.host(agent.agent_id)
            record.evaluated += 1
            record.evaluated_dose += float(effective_dose)
            record.hazard_sum += float(hazard)
            record.frailty = frailty
        return hazard

    return wrapper


def _challenge_entry_state(
    core: Any, agent: Any, pathogen_id: str, epoch: int, dose_map: dict,
) -> dict[str, Any]:
    """Read the challenge's entry conditions without consuming RNG."""
    resident = bool(agent.is_infected_with(pathogen_id))
    p_dose = float(dose_map.get(agent.agent_id, {}).get(pathogen_id, 0.0))
    state = {
        "resident": resident,
        "p_dose": p_dose,
        "immune": bool(getattr(agent, "immune", False)),
        "secretor_negative": bool(
            getattr(agent, "secretor_negative_by_pathogen", {}).get(
                pathogen_id, False,
            ),
        ),
        "protection": None,
    }
    if resident and not core._superinfection_open(pathogen_id):
        state["reason"] = "resident_superinfection_closed"
        return state
    if p_dose <= 0.0:
        state["reason"] = "no_dose_this_epoch"
        return state
    protection = float(core._challenge_protection(agent, pathogen_id, epoch))
    state["protection"] = protection
    state["reason"] = "protection_absolute" if protection >= 1.0 else "pending"
    return state


def _wrap_challenge(core_cls: type, rec: Recorder, top_ids: set[int]) -> Any:
    original = core_cls._resolve_pathogen_challenge

    def wrapper(
        self: Any,
        epoch: int,
        agent: Any,
        pathogen_id: str,
        agent_pathogen_doses: dict[int, dict[str, float]],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        if pathogen_id != rec.pathogen_id:
            return original(
                self, epoch, agent, pathogen_id, agent_pathogen_doses,
                *args, **kwargs,
            )
        state = _challenge_entry_state(
            self, agent, pathogen_id, epoch, agent_pathogen_doses,
        )
        rec.hazard_witness = None
        result = original(
            self, epoch, agent, pathogen_id, agent_pathogen_doses,
            *args, **kwargs,
        )
        witness = rec.hazard_witness
        evaluated = (
            witness is not None
            and witness[0] == int(agent.agent_id)
            and witness[1] == pathogen_id
        )
        reason = state["reason"]
        if reason == "pending":
            reason = "evaluated" if evaluated else "effective_dose_zero"
        record = rec.host(agent.agent_id)
        record.challenge_calls += 1
        record.challenge_dose_read += state["p_dose"]
        record.reasons[reason] += 1
        if state["p_dose"] > 0.0 and evaluated:
            record.credited_epochs_challenge_evaluated += 1
        now_infected = bool(agent.is_infected_with(pathogen_id))
        if not state["resident"] and now_infected:
            rec.acquisitions.append({
                "agent_id": int(agent.agent_id),
                "epoch": int(epoch),
                "dose_read": state["p_dose"],
                "effective_dose": witness[2] if evaluated else None,
                "frailty": witness[3] if evaluated else None,
                "hazard": witness[4] if evaluated else None,
            })
            rec.acquired_ids.add(int(agent.agent_id))
        if state["resident"] and agent.agent_id not in rec.acquired_ids:
            rec.import_ids.add(int(agent.agent_id))
        if agent.agent_id in top_ids and state["p_dose"] > 0.0:
            rec.top_host_rows.append({
                "agent_id": int(agent.agent_id),
                "epoch": int(epoch),
                "dose_read": state["p_dose"],
                "resident_infected": state["resident"],
                "immune": state["immune"],
                "secretor_negative": state["secretor_negative"],
                "protection": state["protection"],
                "challenge_evaluated": bool(evaluated),
                "effective_dose": witness[2] if evaluated else None,
                "frailty": witness[3] if evaluated else None,
                "hazard": witness[4] if evaluated else None,
                "cumulative_exposure": float(
                    agent.cumulative_exposure.get(pathogen_id, 0.0),
                ),
            })
        return result

    return wrapper


def _wrap_fomite(core_cls: type, rec: Recorder) -> dict[str, Any]:
    """Wrap the fomite transfer chain's mass and dose terms."""
    originals = {
        "_deliver_fomite_requests": core_cls._deliver_fomite_requests,
        "_deliver_fomite_requests_by_class": (
            core_cls._deliver_fomite_requests_by_class
        ),
        "_fomite_pickup_requests_by_class": (
            core_cls._fomite_pickup_requests_by_class
        ),
        "_hand_to_mouth_dose": core_cls._hand_to_mouth_dose,
        "_deposit_surface_mass": core_cls._deposit_surface_mass,
        "_replenish_hand": core_cls._replenish_hand,
        "_fomite_pickup_request_for_area": (
            core_cls._fomite_pickup_request_for_area
        ),
        # RNG-free helpers, re-called from the witness below; kept in
        # ``originals`` so the restore loop covers them uniformly even though
        # nothing replaces them.
        "_fomite_surface_contacts": core_cls._fomite_surface_contacts,
    }

    def replenish_hand(
        self: Any,
        agent: Any,
        pathogen_id: str,
        profile: dict | None,
        zone_name: str | None = None,
    ) -> None:
        originals["_replenish_hand"](
            self, agent, pathogen_id, profile, zone_name,
        )
        if pathogen_id != rec.pathogen_id:
            return
        target = agent.get_pathogen_hand_target(pathogen_id, profile or {})
        load = agent.hand_load_by_pathogen.get(pathogen_id, 0.0)
        if target > 0.0:
            rec.fomite["hand_target_positive_calls"] += 1
            rec.fomite["max_hand_target_gec"] = max(
                rec.fomite["max_hand_target_gec"], float(target),
            )
        rec.fomite["max_hand_load_gec"] = max(
            rec.fomite["max_hand_load_gec"], float(load),
        )

    def deposit(
        self: Any, pathogen_id: str, zone_name: str, mass: float,
    ) -> None:
        rec.fomite_representation_seen = self.fomite_representation
        if self._per_surface is not None:
            rec.fomite_touch_share_seen = self._per_surface.cfg.touch_share
        if pathogen_id == rec.pathogen_id and float(mass) > 0.0:
            rec.fomite["surface_deposit_calls"] += 1
            rec.fomite["surface_mass_deposited_gec"] += float(mass)
        return originals["_deposit_surface_mass"](
            self, pathogen_id, zone_name, mass,
        )

    def deliver(
        self: Any,
        requests: list[tuple[Any, float]],
        zone_name: str,
        surface_mass: float,
        *args: Any,
        **kwargs: Any,
    ) -> float:
        delivered = originals["_deliver_fomite_requests"](
            self, requests, zone_name, surface_mass, *args, **kwargs,
        )
        if rec.current_pathogen == rec.pathogen_id:
            requested = float(sum(mass for _, mass in requests))
            rec.fomite["deliver_calls"] += 1
            rec.fomite["surface_mass_offered_gec"] += float(surface_mass)
            rec.fomite["mass_requested_gec"] += requested
            rec.fomite["mass_delivered_to_hands_gec"] += float(delivered)
            scale_witness = rec.delivery_scale
            scale_witness["deliver_calls"] += 1
            scale_witness["sum_requested_gec"] += requested
            scale_witness["sum_offered_gec"] += float(surface_mass)
            if requested > float(surface_mass) > 0.0:
                scale_witness["scaled_calls"] += 1
                log10_scale = math.log10(float(surface_mass) / requested)
                scale_witness["sum_log10_scale"] += log10_scale
                scale_witness["min_log10_scale"] = min(
                    scale_witness["min_log10_scale"], log10_scale,
                )
        return delivered

    def deliver_by_class(
        self: Any,
        requests: list[tuple[Any, dict[str, float]]],
        zone_name: str,
        surface_mass: float,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, float]:
        """Per-class analogue of ``deliver`` feeding the same counters.

        ``requests`` carries ``{item_class: mass}`` per target; the pooled
        aggregates are reconstructed exactly: requested is the sum over
        classes and targets, offered is ``surface_mass`` (the zone total),
        and delivered is the sum over the returned per-class dict.
        """
        delivered = originals["_deliver_fomite_requests_by_class"](
            self, requests, zone_name, surface_mass, *args, **kwargs,
        )
        if rec.current_pathogen == rec.pathogen_id:
            requested = float(
                sum(m for _, req in requests for m in req.values())
            )
            rec.fomite["deliver_calls"] += 1
            rec.fomite["surface_mass_offered_gec"] += float(surface_mass)
            rec.fomite["mass_requested_gec"] += requested
            rec.fomite["mass_delivered_to_hands_gec"] += float(
                sum(delivered.values())
            )
            zone_class = self._fomite_zone_class(zone_name)
            requested_by_class: dict[str, float] = defaultdict(float)
            for _, req in requests:
                for item_class, mass in req.items():
                    requested_by_class[item_class] += float(mass)
            for item_class, requested_c in requested_by_class.items():
                class_key = f"{zone_class}.{item_class}"
                bucket = rec.fomite_by_class[class_key]
                bucket["requested_gec"] += requested_c
                delivered_c = float(delivered.get(item_class, 0.0))
                bucket["delivered_gec"] += delivered_c
                if requested_c <= 0.0 or delivered_c <= 0.0:
                    continue
                scale_c = delivered_c / requested_c
                for target, req in requests:
                    share_c = float(req.get(item_class, 0.0))
                    if share_c > 0.0:
                        rec.fomite_host_class_gec[int(target.agent_id)][
                            class_key
                        ] += share_c * scale_c
            scale_witness = rec.delivery_scale
            scale_witness["deliver_calls"] += 1
            scale_witness["sum_requested_gec"] += requested
            scale_witness["sum_offered_gec"] += float(surface_mass)
            if requested > float(surface_mass) > 0.0:
                scale_witness["scaled_calls"] += 1
                log10_scale = math.log10(float(surface_mass) / requested)
                scale_witness["sum_log10_scale"] += log10_scale
                scale_witness["min_log10_scale"] = min(
                    scale_witness["min_log10_scale"], log10_scale,
                )
        return delivered

    def hand_to_mouth(
        self: Any, target: Any, epoch: int, hand_load: float,
    ) -> float:
        dose = originals["_hand_to_mouth_dose"](self, target, epoch, hand_load)
        if rec.current_pathogen == rec.pathogen_id:
            rec.fomite["hand_to_mouth_calls"] += 1
            rec.fomite["hand_load_seen_gec"] += float(hand_load)
            rec.fomite["hand_to_mouth_dose_gec"] += float(dose)
            if float(hand_load) > 0.0:
                # ``_fomite_is_eating`` only reads the schedule -- no draw --
                # so the eating/non-eating split is free.
                meal = (
                    "eating"
                    if self._fomite_is_eating(target, epoch)
                    else "non_eating"
                )
                bucket = rec.mouth_touch[meal]
                ratio = float(dose) / float(hand_load)
                bucket["calls"] += 1
                if dose >= hand_load:
                    bucket["calls_capped"] += 1
                if ratio > 0.0:
                    log10_ratio = math.log10(ratio)
                    bucket["sum_log10_ratio"] += log10_ratio
                    bucket["sum_sq_log10_ratio"] += log10_ratio**2
                    bucket["min_log10_ratio"] = min(
                        bucket["min_log10_ratio"], log10_ratio,
                    )
                    bucket["max_log10_ratio"] = max(
                        bucket["max_log10_ratio"], log10_ratio,
                    )
                    _hist_add(bucket, "hist_log10_ratio", log10_ratio)
                else:
                    bucket["hist_underflow"] += 1
        return dose

    def pickup_request_for_area(
        self: Any,
        target: Any,
        zone_name: str,
        surface_mass: float,
        surface_area_m2: float,
        epoch: int,
    ) -> float:
        """Witness the per-touch surface->hand factor without a draw.

        The original is called exactly once and both re-read helpers
        (``_fomite_surface_contacts``, ``_fomite_zone_class``) draw nothing,
        so this wrapper cannot perturb the RNG stream.
        """
        request = originals["_fomite_pickup_request_for_area"](
            self, target, zone_name, surface_mass, surface_area_m2, epoch,
        )
        if rec.current_pathogen != rec.pathogen_id:
            return request
        source = "patch" if rec.patch_depth > 0 else "pool"
        zone_class = self._fomite_zone_class(zone_name)
        contacts = originals["_fomite_surface_contacts"](
            self, zone_name, target, epoch,
        )
        bucket = rec.surface_touch[source][zone_class]
        bucket["calls"] += 1
        bucket["sum_request_gec"] += float(request)
        bucket["sum_surface_mass_gec"] += float(surface_mass)
        bucket["sum_contacts"] += float(contacts)
        bucket["sum_surface_area_m2"] += float(surface_area_m2)
        if self._cabin_confinement_active(target):
            bucket["calls_confined"] += 1
        elif surface_mass <= 0.0:
            bucket["calls_zero_mass"] += 1
        elif request >= surface_mass:
            # min(surface_mass, ...) bound bit: f_touch is right-censored.
            bucket["calls_capped"] += 1
        elif contacts > 0.0:
            bucket["calls_clean"] += 1
            f_touch = (float(request) / float(surface_mass)) / float(contacts)
            if f_touch > 0.0:
                log10_f = math.log10(f_touch)
                bucket["sum_log10_f_touch"] += log10_f
                bucket["sum_sq_log10_f_touch"] += log10_f**2
                bucket["min_log10_f_touch"] = min(
                    bucket["min_log10_f_touch"], log10_f,
                )
                bucket["max_log10_f_touch"] = max(
                    bucket["max_log10_f_touch"], log10_f,
                )
                _hist_add(bucket, "hist_log10_f_touch", log10_f)
            else:
                bucket["hist_underflow"] += 1
        return request

    def pickup_requests_by_class(
        self: Any,
        target: Any,
        zone_name: str,
        epoch: int,
        pathogen_id: str,
    ) -> Any:
        """Count per-class pickup calls and capped requests; reads only."""
        mass_before: dict[str, float] = {}
        if pathogen_id == rec.pathogen_id and self._per_surface is not None:
            inv = self._per_surface.inventory(zone_name)
            if inv is not None:
                for item_class in inv.counts:
                    mass_before[item_class] = self._per_surface.mass.get(
                        (zone_name, pathogen_id, item_class), 0.0,
                    )
        request = originals["_fomite_pickup_requests_by_class"](
            self, target, zone_name, epoch, pathogen_id,
        )
        if request is None or not mass_before:
            return request
        zone_class = self._fomite_zone_class(zone_name)
        for item_class, requested_c in request.items():
            bucket = rec.fomite_by_class[f"{zone_class}.{item_class}"]
            bucket["calls"] += 1
            mass_c = mass_before.get(item_class, 0.0)
            if mass_c > 0.0 and requested_c >= mass_c:
                bucket["capped_calls"] += 1
        return request

    core_cls._deliver_fomite_requests = deliver
    core_cls._deliver_fomite_requests_by_class = deliver_by_class
    core_cls._fomite_pickup_requests_by_class = pickup_requests_by_class
    core_cls._hand_to_mouth_dose = hand_to_mouth
    core_cls._deposit_surface_mass = deposit
    core_cls._replenish_hand = replenish_hand
    core_cls._fomite_pickup_request_for_area = pickup_request_for_area
    return originals


def _wrap_emesis(core_cls: type, rec: Recorder) -> dict[str, Any]:
    """Wrap the emesis chain's witness points; return the originals."""
    originals = {
        "draw_emesis_schedule": tc.draw_emesis_schedule,
        "_emesis_phase": core_cls._emesis_phase,
        "_emit_emesis": core_cls._emit_emesis,
        "_emesis_patch_pickup": core_cls._emesis_patch_pickup,
        "_emesis_patch_pickup_one": core_cls._emesis_patch_pickup_one,
    }

    def draw_schedule(
        agent: Any, pathogen_id: str, profile: dict, rng: Any,
    ) -> None:
        originals["draw_emesis_schedule"](agent, pathogen_id, profile, rng)
        if pathogen_id != rec.pathogen_id:
            return
        rec.emesis["schedule_draws"] += 1
        schedule = getattr(
            agent, "emesis_episode_schedule_by_pathogen", {},
        ).get(pathogen_id, [])
        rec.emesis["scheduled_episodes"] += len(schedule)
        if schedule:
            rec.emesis["hosts_with_schedule"] += 1
        else:
            rec.emesis["hosts_with_empty_schedule"] += 1

    def emesis_phase(
        self: Any, agent: Any, pathogen_id: str, profile: dict,
    ) -> Any:
        result = originals["_emesis_phase"](self, agent, pathogen_id, profile)
        if pathogen_id == rec.pathogen_id:
            key = "phase_eligible" if result is not None else "phase_blocked"
            rec.emesis[key] += 1
        return result

    def emit_emesis(
        self: Any,
        agent: Any,
        pathogen_id: str,
        profile: dict,
        zone_name: str,
        epoch: int,
    ) -> float:
        before = len(
            getattr(agent, "emesis_deposition_records_by_pathogen", {}).get(
                pathogen_id, [],
            ),
        )
        pool_gain = originals["_emit_emesis"](
            self, agent, pathogen_id, profile, zone_name, epoch,
        )
        if pathogen_id != rec.pathogen_id:
            return pool_gain
        rec.emesis["emit_calls"] += 1
        after = len(
            getattr(agent, "emesis_deposition_records_by_pathogen", {}).get(
                pathogen_id, [],
            ),
        )
        rec.emesis["emesis_events"] += after - before
        rec.emesis["patch_mass_gec"] += pool_gain
        if after > before:
            rec.emesis["emitting_hosts"] += 1
        return pool_gain

    def patch_pickup(
        self: Any,
        epoch: int,
        pickup_units: dict[str, list[Any]],
        pathogen_id: str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        if pathogen_id == rec.pathogen_id:
            pools = self.emesis_patch_pools_by_pathogen.get(pathogen_id) or {}
            filed = [unit for unit, patches in pools.items() if patches]
            rec.emesis["patch_pickup_sweeps"] += 1
            if filed:
                rec.emesis["sweeps_with_filed_patch"] += 1
                matched = [unit for unit in filed if unit in pickup_units]
                if matched:
                    rec.emesis["sweeps_with_matching_unit"] += 1
                    for unit in matched:
                        occupants = pickup_units.get(unit) or []
                        rec.emesis["matched_unit_occupants"] += len(occupants)
                        rec.emesis["matched_unit_susceptible"] += len(
                            self._get_susceptible(occupants, pathogen_id),
                        )
                if "filed_units" not in rec.emesis_units:
                    rec.emesis_units["filed_units"] = sorted(filed)[:10]
                    rec.emesis_units["pickup_units"] = sorted(pickup_units)[:10]
                    rec.emesis_units["matched_units"] = sorted(matched)[:10]
        return originals["_emesis_patch_pickup"](
            self, epoch, pickup_units, pathogen_id, *args, **kwargs,
        )

    def patch_pickup_one(self: Any, patch: Any, *args: Any, **kwargs: Any) -> float:
        rec.patch_depth += 1
        try:
            delivered = originals["_emesis_patch_pickup_one"](
                self, patch, *args, **kwargs,
            )
        finally:
            rec.patch_depth -= 1
        rec.emesis["patch_pickup_calls"] += 1
        rec.emesis["patch_pickup_dose_gec"] += float(delivered)
        if delivered > 0.0:
            rec.emesis["patch_pickups"] += 1
        return delivered

    tc.draw_emesis_schedule = draw_schedule
    initiation_module.draw_emesis_schedule = draw_schedule
    natural_history_module.draw_emesis_schedule = draw_schedule
    core_cls._emesis_phase = emesis_phase
    core_cls._emit_emesis = emit_emesis
    core_cls._emesis_patch_pickup = patch_pickup
    core_cls._emesis_patch_pickup_one = patch_pickup_one
    return originals


@contextmanager
def instrumented(rec: Recorder, top_ids: set[int]) -> Any:
    """Install the read-only wrappers for the duration of one run."""
    core_cls = tc.TransmissionCore
    saved = {
        "_accumulate": core_cls._accumulate,
        "_execute_pathogen_pathways": core_cls._execute_pathogen_pathways,
        "_merge_pathogen_doses": core_cls._merge_pathogen_doses,
        "_dose_response_hazard": core_cls._dose_response_hazard,
        "_resolve_pathogen_challenge": core_cls._resolve_pathogen_challenge,
    }
    core_cls._accumulate = _wrap_accumulate(core_cls, rec)
    core_cls._execute_pathogen_pathways = _wrap_execute_pathways(core_cls, rec)
    core_cls._merge_pathogen_doses = _wrap_merge(core_cls, rec)
    core_cls._dose_response_hazard = _wrap_hazard(core_cls, rec)
    core_cls._resolve_pathogen_challenge = _wrap_challenge(
        core_cls, rec, top_ids,
    )
    emesis_saved = _wrap_emesis(core_cls, rec)
    fomite_saved = _wrap_fomite(core_cls, rec)
    try:
        yield
    finally:
        for name, method in saved.items():
            setattr(core_cls, name, method)
        for name, method in fomite_saved.items():
            setattr(core_cls, name, method)
        core_cls._emesis_phase = emesis_saved["_emesis_phase"]
        core_cls._emit_emesis = emesis_saved["_emit_emesis"]
        core_cls._emesis_patch_pickup = emesis_saved["_emesis_patch_pickup"]
        core_cls._emesis_patch_pickup_one = emesis_saved[
            "_emesis_patch_pickup_one"
        ]
        tc.draw_emesis_schedule = emesis_saved["draw_emesis_schedule"]
        initiation_module.draw_emesis_schedule = emesis_saved[
            "draw_emesis_schedule"
        ]
        natural_history_module.draw_emesis_schedule = emesis_saved[
            "draw_emesis_schedule"
        ]


def build_spec(
    *, seed: int, platform: str, bundle: str, epochs: int, num_agents: int,
    pathogen_id: str, alpha: float | None, beta: float,
    high_touch_area_scale: float | None = None,
    high_touch_area_scale_by_zone_class: dict[str, Any] | None = None,
    fomite_representation: str | None = None,
    fomite_touch_share: str | None = None,
    fomite_touch_share_table: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The shipped run, at one seed.

    With ``alpha=None`` and no area-sweep arguments no pathogen or run
    override is written (byte-identical to the NORO-SUSCEPT-02 spec). With
    an alpha, exactly one override is written: a ``pathogen_overrides``
    patch on the pathogen's ``dose_response`` carrying the requested alpha
    and beta pinned explicitly. Each area-sweep argument, when given, adds
    its key under ``config_overrides.transmission`` -- the only block the
    sweep touches -- and nothing else.
    """
    overrides: dict[str, Any] = {}
    if alpha is not None:
        overrides = {
            pathogen_id: {
                "dose_response": {"alpha": float(alpha), "beta": float(beta)},
            },
        }
    tx_overrides: dict[str, Any] = {}
    if high_touch_area_scale is not None:
        tx_overrides["high_touch_area_scale"] = float(high_touch_area_scale)
    if high_touch_area_scale_by_zone_class is not None:
        tx_overrides["high_touch_area_scale_by_zone_class"] = dict(
            high_touch_area_scale_by_zone_class,
        )
    if fomite_representation is not None:
        tx_overrides["fomite_representation"] = str(fomite_representation)
    if fomite_touch_share is not None:
        tx_overrides["fomite_touch_share"] = str(fomite_touch_share)
    if fomite_touch_share_table is not None:
        tx_overrides["fomite_touch_share_table"] = dict(
            fomite_touch_share_table,
        )
    config_overrides: dict[str, Any] = {
        "ship_graph": {"num_agents": int(num_agents)},
    }
    if tx_overrides:
        config_overrides["transmission"] = tx_overrides
    return {
        "schema_version": "1.0.0",
        "description": "noro_diag per_host_dose_challenge",
        "catalog": {"platform_id": platform, "pathogen_bundle_id": bundle},
        "run": {
            "random_seed": int(seed),
            "num_epochs": int(epochs),
            "write_ground_truth": False,
            "history_retention": "compact",
        },
        "legacy_yaml": CRUSHER_CONFIG_REL,
        "actors": [],
        "incentives": {},
        "config_overrides": config_overrides,
        "pathogen_overrides": overrides,
    }


def concentration_curve(doses: list[float]) -> dict[str, Any]:
    """How much of the credited dose the top-k hosts hold."""
    ordered = sorted(doses, reverse=True)
    total = sum(ordered)
    cumulative = 0.0
    hosts_for = {}
    thresholds = [0.5, 0.9, 0.95, 0.99]
    remaining = list(thresholds)
    for index, dose in enumerate(ordered, start=1):
        cumulative += dose
        while remaining and total > 0.0 and cumulative / total >= remaining[0]:
            hosts_for[f"hosts_for_{int(remaining[0] * 100)}pct"] = index
            remaining.pop(0)
    return {
        "hosts_credited": len(ordered),
        "total_credited": total,
        "max_host": ordered[0] if ordered else 0.0,
        "max_host_share": (ordered[0] / total) if total > 0.0 else 0.0,
        **hosts_for,
    }


def _naive_hazard(
    records: list[HostRecord], generator: np.random.Generator,
    alpha: float, beta: float,
) -> dict[str, float]:
    """Voyage-total-dose hazard under each host's frailty.

    Hosts the engine never challenged have no drawn frailty -- the engine
    draws one lazily at the first hazard evaluation -- so a counterfactual
    over all credited hosts must supply one. Those come from ``generator``,
    not from the run, and are reported separately.
    """
    measured = 0.0
    counterfactual = 0.0
    drawn = 0
    for record in records:
        frailty = record.frailty
        if frailty is None:
            frailty = float(generator.beta(alpha, beta))
        else:
            drawn += 1
            measured += -math.expm1(-frailty * record.credited_scaled)
        counterfactual += -math.expm1(-frailty * record.credited_scaled)
    return {
        "hosts_with_engine_frailty": drawn,
        "naive_hazard_engine_frailty_hosts": measured,
        "naive_hazard_all_credited_hosts": counterfactual,
    }


def _finalise_bucket(bucket: dict[str, Any], prefix: str) -> dict[str, Any]:
    """Materialise one accumulator bucket for JSON, inf sentinels to None."""
    out = dict(bucket)
    for key in (f"min_{prefix}", f"max_{prefix}"):
        if not math.isfinite(out[key]):
            out[key] = None
    return out


def _transfer_product_summary(rec: Recorder) -> dict[str, Any]:
    """The per-touch transfer factors, split at the layers literature reads.

    ``surface_to_hand`` is bucketed by source (``pool`` zone-wide vs
    ``patch`` emesis footprint) and zone class; ``hand_to_mouth`` by whether
    the contact happened while the agent was eating. Only ``clean`` surface
    calls contribute to ``f_touch`` statistics -- capped, confined and
    zero-mass calls are counted but are not transfer-efficiency samples.
    """
    return {
        "hist_bin_edges": f_touch_bin_edges(),
        "hist_bin_width": F_TOUCH_LOG_BIN,
        "surface_to_hand": {
            source: {
                zone_class: _finalise_bucket(bucket, "log10_f_touch")
                for zone_class, bucket in sorted(zones.items())
            }
            for source, zones in sorted(rec.surface_touch.items())
        },
        "hand_to_mouth": {
            meal: _finalise_bucket(bucket, "log10_ratio")
            for meal, bucket in sorted(rec.mouth_touch.items())
        },
    }


def _delivery_scale_summary(rec: Recorder) -> dict[str, Any]:
    """How often demand exceeded the pool, and by how much it was scaled."""
    witness = dict(rec.delivery_scale)
    if not math.isfinite(witness.get("min_log10_scale", math.inf)):
        witness["min_log10_scale"] = None
    scaled = witness.get("scaled_calls", 0)
    witness["geometric_mean_scale"] = (
        10.0 ** (witness["sum_log10_scale"] / scaled) if scaled else None
    )
    return witness


def summarise(
    rec: Recorder, alpha: float, beta: float, seed: int, epochs: int,
) -> dict[str, Any]:
    """The reconciliation chain and the per-host joint distribution."""
    records = list(rec.hosts.values())
    credited = [r.credited_scaled for r in records if r.credited_scaled > 0.0]
    evaluated_hosts = [r for r in records if r.evaluated > 0]
    never_evaluated = [
        r for r in records if r.evaluated == 0 and r.credited_scaled > 0.0
    ]
    reasons: dict[str, int] = defaultdict(int)
    for record in records:
        for reason, count in record.reasons.items():
            reasons[reason] += count
    generator = np.random.default_rng(COUNTERFACTUAL_SEED)
    chain = {
        "accumulate_calls": dict(rec.accumulate_calls),
        "accumulate_dose_gec": dict(rec.accumulate_dose),
        "pathway_calls": dict(rec.pathway_calls),
        "pathway_dose_gec": dict(rec.pathway_dose),
        "sum_credited_raw_gec": sum(r.credited_raw for r in records),
        "sum_credited_scaled_gec": sum(r.credited_scaled for r in records),
        "sum_dose_read_at_challenge_gec": sum(
            r.challenge_dose_read for r in records
        ),
        "sum_effective_dose_evaluated_gec": sum(
            r.evaluated_dose for r in records
        ),
        "sum_evaluated_hazard": sum(r.hazard_sum for r in records),
    }
    joint = {
        "hosts_credited_any_dose": len(credited),
        "hosts_with_evaluated_challenge": len(evaluated_hosts),
        "hosts_credited_but_never_evaluated": len(never_evaluated),
        "dose_to_never_evaluated_hosts_gec": sum(
            r.credited_scaled for r in never_evaluated
        ),
        "crediting_epochs_total": sum(r.crediting_epochs for r in records),
        "crediting_epochs_host_infected": sum(
            r.credited_epochs_infected for r in records
        ),
        "crediting_epochs_host_immune": sum(
            r.credited_epochs_immune for r in records
        ),
        "crediting_epochs_host_secretor_negative": sum(
            r.credited_epochs_secretor_negative for r in records
        ),
        "crediting_epochs_challenge_evaluated": sum(
            r.credited_epochs_challenge_evaluated for r in records
        ),
        "challenge_exit_reasons": dict(reasons),
    }
    drawn = [r.frailty for r in records if r.frailty is not None]
    if drawn:
        frailty_drawn = {
            "n": len(drawn),
            "min": float(np.min(drawn)),
            "p25": float(np.percentile(drawn, 25)),
            "median": float(np.median(drawn)),
            "p75": float(np.percentile(drawn, 75)),
            "max": float(np.max(drawn)),
            "mean": float(np.mean(drawn)),
        }
    else:
        frailty_drawn = {"n": 0}
    transmission = {
        "secondaries": len(rec.acquired_ids),
        "imports": len(rec.import_ids),
        "ever_infected": len(rec.acquired_ids) + len(rec.import_ids),
        "acquisitions": rec.acquisitions,
    }
    return {
        "seed": seed,
        "epochs": epochs,
        "dose_response": {"alpha": alpha, "beta": beta},
        "reconciliation": chain,
        "joint": joint,
        "concentration": concentration_curve(credited),
        "naive_hazard": _naive_hazard(records, generator, alpha, beta),
        "frailty_drawn": frailty_drawn,
        "transmission": transmission,
        "emesis_witness": dict(rec.emesis),
        "emesis_unit_names": dict(rec.emesis_units),
        "fomite_witness": dict(rec.fomite),
        "transfer_product_witness": _transfer_product_summary(rec),
        "delivery_scale_witness": _delivery_scale_summary(rec),
        "fomite_by_class": _fomite_by_class_summary(rec),
        "fomite_delivered_by_host": {
            str(agent_id): float(mass)
            for agent_id, mass in sorted(
                (
                    (agent_id, sum(per_class.values()))
                    for agent_id, per_class in (
                        rec.fomite_host_class_gec.items()
                    )
                ),
                key=lambda item: item[0],
            )
            if mass > 0.0
        },
        "hosts": [
            {
                "agent_id": agent_id,
                "credited_raw_gec": r.credited_raw,
                "credited_scaled_gec": r.credited_scaled,
                "crediting_epochs": r.crediting_epochs,
                "susceptibility_multiplier": r.susceptibility_multiplier,
                "dose_response_susceptibility": r.frailty,
                "challenge_calls": r.challenge_calls,
                "dose_read_at_challenge_gec": r.challenge_dose_read,
                "challenges_evaluated": r.evaluated,
                "effective_dose_evaluated_gec": r.evaluated_dose,
                "hazard_sum": r.hazard_sum,
                "epochs_infected_when_credited": r.credited_epochs_infected,
                "epochs_immune_when_credited": r.credited_epochs_immune,
                "epochs_secretor_negative_when_credited": (
                    r.credited_epochs_secretor_negative
                ),
                "epochs_challenge_evaluated_when_credited": (
                    r.credited_epochs_challenge_evaluated
                ),
                "exit_reasons": dict(r.reasons),
                "fomite_delivered_gec": float(
                    sum(rec.fomite_host_class_gec.get(agent_id, {}).values()),
                ),
                "fomite_delivered_by_class": {
                    item_class: float(mass)
                    for item_class, mass in sorted(
                        rec.fomite_host_class_gec.get(agent_id, {}).items(),
                    )
                },
            }
            for agent_id, r in sorted(
                rec.hosts.items(),
                key=lambda item: item[1].credited_scaled,
                reverse=True,
            )
        ],
        "top_host_epoch_rows": rec.top_host_rows,
    }


def _fomite_by_class_summary(rec: Recorder) -> dict[str, Any]:
    """Pool-level per-class counters plus distinct credited hosts."""
    hosts_by_class: dict[str, int] = defaultdict(int)
    for per_class in rec.fomite_host_class_gec.values():
        for item_class, mass in per_class.items():
            if mass > 0.0:
                hosts_by_class[item_class] += 1
    return {
        item_class: {
            **bucket,
            "hosts_credited": hosts_by_class.get(item_class, 0),
        }
        for item_class, bucket in sorted(rec.fomite_by_class.items())
    }


def infection_tally(result: Any, pathogen_id: str) -> dict[str, Any]:
    """Whatever the run's own history reports about this pathogen's cases."""
    history = getattr(result, "history", None) or []
    final = history[-1] if history else {}
    keys = (
        "total_infected", "ever_infected", "active_infections",
        "cumulative_infections", "new_infections",
    )
    return {
        "pathogen_id": pathogen_id,
        "epochs_recorded": len(history),
        "final_epoch_fields": {
            key: final.get(key) for key in keys if isinstance(final, dict)
        },
    }


def run_seed(
    *,
    seed: int,
    platform: str,
    bundle: str,
    epochs: int,
    pathogen_id: str,
    top_hosts: int,
    alpha_override: float | None = None,
    high_touch_area_scale: float | None = None,
    high_touch_area_scale_by_zone_class: dict[str, Any] | None = None,
    fomite_representation: str | None = None,
    fomite_touch_share: str | None = None,
    fomite_touch_share_table: str | None = None,
    arm_tag: str | None = None,
) -> dict[str, Any]:
    """Run one instrumented voyage and return its measurement."""
    started_total = time.perf_counter()
    num_agents = declared_total(platform)
    alpha, beta = load_dose_response(pathogen_id, bundle)
    spec_dict = build_spec(
        seed=seed, platform=platform, bundle=bundle,
        epochs=epochs, num_agents=num_agents,
        pathogen_id=pathogen_id, alpha=alpha_override, beta=beta,
        high_touch_area_scale=high_touch_area_scale,
        high_touch_area_scale_by_zone_class=high_touch_area_scale_by_zone_class,
        fomite_representation=fomite_representation,
        fomite_touch_share=fomite_touch_share,
        fomite_touch_share_table=(
            load_declared_share_table(fomite_touch_share_table)
            if fomite_touch_share_table is not None
            else None
        ),
    )
    if alpha_override is not None:
        alpha = float(alpha_override)
    rec = Recorder(pathogen_id=pathogen_id)
    # The per-epoch witness rows are kept only for the hosts the first pass
    # cannot know yet, so the set is seeded by agent id order and pruned in
    # the summary: a full 1,910 x 288 row dump is not needed to show what one
    # heavily dosed host's epochs looked like.
    top_ids = set(range(top_hosts))
    # The spec path lives under the repository root, not /tmp, because
    # validated_open refuses publicly writable targets; the directory is
    # still a fresh private TemporaryDirectory.
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
        spec_path = resolve_child_path(tmp, "run_spec.json")
        with validated_open(
            spec_path, "w", allowed_roots=(tmp,), encoding="utf-8",
        ) as handle:
            handle.write(json.dumps(spec_dict))
        picard_spec = PicardRunSpec.from_picard_json(
            str(REPO_ROOT), spec_path,
        )
        resolved = picard_spec.pathogen_profiles[pathogen_id]["dose_response"]
        alpha_resolved = float(resolved["alpha"])
        if abs(alpha_resolved - alpha) > 1e-12:
            raise RuntimeError(
                f"dose-response override dropped: requested alpha={alpha}, "
                f"resolved alpha={alpha_resolved}",
            )
        with instrumented(rec, top_ids):
            started_run = time.perf_counter()
            result = ShipSimulation(picard_spec, display=False).run()
            wall_clock_run = time.perf_counter() - started_run
    if fomite_representation is not None and (
        rec.fomite_representation_seen != fomite_representation
    ):
        raise RuntimeError(
            "fomite_representation override dropped: requested "
            f"fomite_representation={fomite_representation}, resolved "
            f"{rec.fomite_representation_seen}",
        )
    if fomite_touch_share is not None and (
        rec.fomite_touch_share_seen != fomite_touch_share
    ):
        raise RuntimeError(
            "fomite_touch_share override dropped: requested "
            f"fomite_touch_share={fomite_touch_share}, resolved "
            f"{rec.fomite_touch_share_seen}",
        )
    summary = summarise(rec, alpha, beta, seed, epochs)
    summary["dose_response_resolved"] = {
        "alpha_requested": alpha,
        "alpha_resolved": alpha_resolved,
        "beta_resolved": float(resolved["beta"]),
        "source": "override" if alpha_override is not None else "active_profile",
    }
    summary["transmission"]["attack_rate"] = (
        len(rec.acquired_ids) / num_agents
    )
    summary["platform"] = platform
    summary["num_agents"] = num_agents
    summary["run_history"] = infection_tally(result, pathogen_id)
    if (
        arm_tag is not None
        or high_touch_area_scale is not None
        or high_touch_area_scale_by_zone_class is not None
        or fomite_representation is not None
        or fomite_touch_share is not None
        or fomite_touch_share_table is not None
    ):
        summary["arm_tag"] = arm_tag
        summary["high_touch_area_scale"] = high_touch_area_scale
        summary["high_touch_area_scale_by_zone_class"] = (
            high_touch_area_scale_by_zone_class
        )
        summary["fomite_representation"] = fomite_representation
        summary["fomite_touch_share"] = fomite_touch_share
        if fomite_touch_share_table is not None:
            resolved_table = _safe_path(fomite_touch_share_table)
            summary["fomite_touch_share_table"] = os.path.relpath(
                resolved_table, str(REPO_ROOT),
            )
            summary["fomite_touch_share_table_sha256"] = hashlib.sha256(
                Path(resolved_table).read_bytes(),
            ).hexdigest()
        else:
            summary["fomite_touch_share_table"] = None
    summary["fomite_representation_resolved"] = (
        rec.fomite_representation_seen
    )
    summary["fomite_touch_share_resolved"] = rec.fomite_touch_share_seen
    summary["wall_clock_seconds_run"] = wall_clock_run
    summary["wall_clock_seconds_total"] = time.perf_counter() - started_total
    return summary


def print_summary(summary: dict[str, Any]) -> None:
    """Print the reconciliation chain and the concentration answer."""
    chain = summary["reconciliation"]
    joint = summary["joint"]
    print(f"\n=== seed {summary['seed']} "
          f"({summary['num_agents']} agents, {summary['epochs']} epochs) ===")
    print("reconciliation, norovirus:")
    for key in (
        "sum_credited_raw_gec", "sum_credited_scaled_gec",
        "sum_dose_read_at_challenge_gec",
        "sum_effective_dose_evaluated_gec", "sum_evaluated_hazard",
    ):
        print(f"  {key:38s} {chain[key]:.6g}")
    print(f"  accumulate calls: {chain['accumulate_calls']}")
    print("per-host join:")
    for key, value in joint.items():
        if isinstance(value, dict):
            print(f"  {key}: {value}")
        else:
            print(f"  {key:44s} {value:.6g}")
    print(f"concentration: {summary['concentration']}")
    print(f"naive hazard: {summary['naive_hazard']}")
    print(f"emesis witness: {summary['emesis_witness']}")
    print(f"emesis units: {summary['emesis_unit_names']}")
    print(f"fomite witness: {summary['fomite_witness']}")


def _safe_path(path: str) -> str:
    """Canonicalise a CLI-derived target and refuse anything outside the repo."""
    resolved = os.path.realpath(path)
    base_dir = os.path.realpath(str(REPO_ROOT))
    if resolved != base_dir and not resolved.startswith(base_dir + os.sep):
        raise ValueError(f"path {path!r} is outside the allowed directory")
    return resolved


def _identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise argparse.ArgumentTypeError(f"invalid identifier: {value!r}")
    return value


def _json_object(value: str) -> dict[str, Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError(
            f"expected a JSON object, got {value!r}",
        )
    return parsed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--platform", type=_identifier, default="classic_cruise_1900")
    parser.add_argument(
        "--bundle", type=_identifier,
        default=asset_defaults.DEFAULT_PATHOGEN_BUNDLE_ID)
    parser.add_argument(
        "--pathogen-id", type=_identifier, default="norwalk_gi")
    parser.add_argument("--epochs", type=int, default=288)
    parser.add_argument(
        "--seeds", type=int, nargs="+", default=[8105, 8106],
        help="paired seeds; the norovirus pair is 8105 8106",
    )
    parser.add_argument(
        "--top-hosts", type=int, default=8,
        help="agent ids 0..N-1 get a per-epoch witness row dump",
    )
    parser.add_argument(
        "--alpha", type=float, default=None,
        help="dose-response alpha override for NORO-SUSCEPT-03; must lie in "
             "the frozen interval [0.072, 0.161]",
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--high-touch-area-scale", type=float, default=None,
        help="NORO-HIGH-TOUCH-AREA-01 sweep arm: global multiplier on the "
             "fomite areal denominator; the engine parser refuses bad arms",
    )
    parser.add_argument(
        "--high-touch-area-scale-by-zone-class", type=_json_object,
        default=None,
        help='JSON object of per-zone-class multipliers, e.g. '
             '\'{"cabin": 0.11, "dining": 3.5}\'',
    )
    parser.add_argument(
        "--fomite-representation",
        choices=("pooled", "per_surface"), default=None,
        help="NORO-FOMITE-DISAGG-01 arm: pooled (default-path identity) or "
             "per_surface (per-item-class fomite accounting); the run "
             "aborts if the engine resolves a different representation",
    )
    parser.add_argument(
        "--fomite-touch-share",
        choices=("areal", "declared"), default=None,
        help="NORO-TOUCH-SHARE-01 arm selector; requires "
             "--fomite-representation per_surface",
    )
    parser.add_argument(
        "--fomite-touch-share-table", type=Path, default=None,
        help="declared share table JSON under the repository root "
             "(required when --fomite-touch-share declared)",
    )
    parser.add_argument(
        "--arm-tag", type=_identifier, default=None,
        help="arm label stamped into the output filename and summary",
    )
    args = parser.parse_args(argv)
    if (
        args.fomite_touch_share is not None
        or args.fomite_touch_share_table is not None
    ) and args.fomite_representation != "per_surface":
        parser.error(
            "--fomite-touch-share/--fomite-touch-share-table require "
            "--fomite-representation per_surface",
        )
    if args.fomite_touch_share == "declared" and (
        args.fomite_touch_share_table is None
    ):
        parser.error(
            "--fomite-touch-share declared requires --fomite-touch-share-table",
        )
    if args.fomite_touch_share_table is not None:
        try:
            args.fomite_touch_share_table = _safe_path(
                str(args.fomite_touch_share_table),
            )
        except ValueError as exc:
            parser.error(str(exc))
    if args.alpha is not None and not 0.072 <= args.alpha <= 0.161:
        parser.error(
            f"--alpha {args.alpha} is outside the frozen interval "
            "[0.072, 0.161]",
        )
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = Path(
        prepare_output_directory(str(args.out), allowed_roots=(str(REPO_ROOT),)),
    )
    for seed in args.seeds:
        summary = run_seed(
            seed=seed,
            platform=args.platform,
            bundle=args.bundle,
            epochs=args.epochs,
            pathogen_id=args.pathogen_id,
            top_hosts=args.top_hosts,
            alpha_override=args.alpha,
            high_touch_area_scale=args.high_touch_area_scale,
            high_touch_area_scale_by_zone_class=(
                args.high_touch_area_scale_by_zone_class
            ),
            fomite_representation=args.fomite_representation,
            fomite_touch_share=args.fomite_touch_share,
            fomite_touch_share_table=(
                str(args.fomite_touch_share_table)
                if args.fomite_touch_share_table is not None
                else None
            ),
            arm_tag=args.arm_tag,
        )
        if args.arm_tag is not None:
            filename = (
                f"per_host_dose_challenge_{args.arm_tag}_seed{seed}.json.gz"
            )
        elif args.alpha is None:
            filename = f"per_host_dose_challenge_seed{seed}.json.gz"
        else:
            filename = (
                f"per_host_dose_challenge_a{args.alpha:.4f}_seed{seed}.json.gz"
            )
        path = resolve_child_path(str(out_dir), filename)
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=1)
        print_summary(summary)
        print(f"written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
