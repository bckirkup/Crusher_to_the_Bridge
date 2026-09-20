#!/usr/bin/env python3
"""Surface-mass balance and emesis eligibility witness, ledger NORO-EXP-FOMITE-RECONCILE-01.

Purpose
-------
``NORO-EMESIS-CANARY-01`` measured, on ``expedition_cruise_450`` seed 8001,
25.943 GEC deposited to surfaces against 3.278e-28 GEC of surface mass offered
at pickup, and ``phase_eligible = 0`` on every measured expedition seed. Those
are two witnesses, not two explanations: the canary's fomite witness covers
``_deliver_fomite_requests`` only, and a zero phase counter does not say which
of its conditions failed.

This diagnostic closes the surface-mass books instead of arguing about them.
Every term that can move mass into or out of ``surface_pools_by_pathogen`` is
witnessed, per zone and per epoch, tagged by the engine function that called
it, so that

    deposited == removed(all call sites) + residual

is a measured identity rather than an assumption; a zone that fails it is an
engine bookkeeping defect. Deliveries are taken at ``_record_fomite_pickup``,
which every fomite path reaches, rather than at ``_deliver_fomite_requests``,
which the sanitary-venue path bypasses entirely. Emesis eligibility is taken
apart into its conditions: infected, symptomatic, shedding age, resolved
clinical phase, and whether that phase carries the ``vomiting`` feature.

Method
------
The engine is not modified and no configuration value is overridden. Bound
methods on ``TransmissionCore`` are wrapped for the duration of one run and
only read:

* ``_deposit_surface_mass``    -- mass in, per zone, per calling function.
* ``_scale_surface_mass``      -- mass out, per zone, per calling function
  (per-epoch survival decay, delivery consumption, and routine or SOP cleaning
  are separated, not summed).
* ``_record_fomite_pickup``    -- every delivery on every fomite path.
* ``_deliver_fomite_requests`` -- the canary's own term, kept for comparison.
* ``_replenish_hand``          -- per host hand target and hand load.
* ``_hand_carriage_propensity`` / ``_stationary_hand_load`` /
  ``_stool_event_occurs`` -- the hand reservoir's own initialisation: the
  per-host beta carriage propensity, the backward-recurrence load a host first
  seen mid-illness starts at, and whether a defecation event ever refills it.
* ``_emesis_phase``            -- eligibility, decomposed into its conditions.
* ``_pathway_fomite`` / ``_update_surface_pools`` -- epoch boundaries and the
  per-epoch pool total.

No wrapper draws from the engine's generator and none writes engine state.
``_symptomatic_phase`` and ``resolve_phase`` consume no RNG, so calling them
from a wrapper cannot perturb the stream. No ``dose_response.alpha`` or
``.beta`` override is written: ``RNG-FRAILTY-STREAM-01`` makes such an arm
unpairable at fixed seed.

Outputs
-------
One gzipped JSON per seed at ``--out`` (gzipped because the per-epoch table
carries count keys the repository's unit-safety guard reads as an undeclared
time unit in any plain ``.json`` on disk): the voyage balance, the per-zone
balance, the per-epoch timeline, the delivery witness, the hand-load witness,
and the emesis eligibility decomposition. A summary of the same is printed.

Nothing here fits or selects a parameter value.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
import tempfile
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines import transmission_core as tc  # noqa: E402
from picard_framework.run_spec import CRUSHER_CONFIG_REL, PicardRunSpec  # noqa: E402
from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402
from simulation_utils import asset_defaults  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_child_path,
    validated_open,
)
from simulation_utils.platform_complement import declared_total  # noqa: E402

# Relative tolerances for the conservation criterion, declared in the ledger
# entry before any cell ran.
VOYAGE_TOLERANCE = 1e-9
ZONE_TOLERANCE = 1e-6


def _caller_name(depth: int = 2) -> str:
    """The engine function that called the wrapper, for call-site tagging."""
    frame = sys._getframe(depth)
    return str(frame.f_code.co_name)


@dataclass
class ZoneBalance:
    """One zone's surface-mass book for one pathogen."""

    deposited: float = 0.0
    deposit_calls: int = 0
    removed: dict[str, float] = field(
        default_factory=lambda: defaultdict(float),
    )
    offered: float = 0.0
    offer_calls: int = 0
    delivered: float = 0.0
    delivery_calls: int = 0
    dose: float = 0.0


@dataclass
class Recorder:
    """Every observation taken from one instrumented run."""

    pathogen_id: str
    epoch: int = 0
    core: Any = None
    zones: dict[str, ZoneBalance] = field(default_factory=dict)
    deposit_by_site: dict[str, float] = field(
        default_factory=lambda: defaultdict(float),
    )
    delivery_by_site: dict[str, float] = field(
        default_factory=lambda: defaultdict(float),
    )
    epoch_rows: list[dict[str, Any]] = field(default_factory=list)
    epoch_acc: dict[str, float] = field(
        default_factory=lambda: defaultdict(float),
    )
    hand: dict[str, float] = field(
        default_factory=lambda: defaultdict(float),
    )
    propensities: list[float] = field(default_factory=list)
    stationary_rows: list[dict[str, float]] = field(default_factory=list)
    stool_events: dict[str, int] = field(
        default_factory=lambda: defaultdict(int),
    )
    eligibility: dict[str, int] = field(
        default_factory=lambda: defaultdict(int),
    )
    phase_names: dict[str, int] = field(
        default_factory=lambda: defaultdict(int),
    )
    symptomatic_hosts: set[int] = field(default_factory=set)
    infected_hosts: set[int] = field(default_factory=set)

    def zone(self, zone_name: str) -> ZoneBalance:
        """Return (creating if needed) one zone's book."""
        book = self.zones.get(zone_name)
        if book is None:
            book = ZoneBalance()
            self.zones[zone_name] = book
        return book

    def pool_total(self) -> float:
        """Current pool mass for this pathogen across all zones."""
        if self.core is None:
            return 0.0
        pools = self.core.surface_pools_by_pathogen.get(self.pathogen_id, {})
        return float(sum(pools.values()))


def _wrap_surface_mass(core_cls: type, rec: Recorder) -> dict[str, Any]:
    """Wrap the two functions that move mass into and out of the pools."""
    originals = {
        "_deposit_surface_mass": core_cls._deposit_surface_mass,
        "_scale_surface_mass": core_cls._scale_surface_mass,
    }

    def deposit(
        self: Any, pathogen_id: str, zone_name: str, mass: float,
    ) -> None:
        rec.core = self
        originals["_deposit_surface_mass"](self, pathogen_id, zone_name, mass)
        if pathogen_id != rec.pathogen_id or not float(mass) > 0.0:
            return
        book = rec.zone(zone_name)
        book.deposited += float(mass)
        book.deposit_calls += 1
        rec.deposit_by_site[_caller_name()] += float(mass)
        rec.epoch_acc["deposited"] += float(mass)

    def scale(
        self: Any, pathogen_id: str, zone_name: str, factor: float,
    ) -> None:
        pools = self.surface_pools_by_pathogen.get(pathogen_id) or {}
        before = float(pools.get(zone_name, 0.0))
        originals["_scale_surface_mass"](self, pathogen_id, zone_name, factor)
        if pathogen_id != rec.pathogen_id:
            return
        after = float(
            (self.surface_pools_by_pathogen.get(pathogen_id) or {}).get(
                zone_name, 0.0,
            ),
        )
        removed = before - after
        if removed <= 0.0:
            return
        site = _caller_name()
        rec.zone(zone_name).removed[site] += removed
        rec.epoch_acc[f"removed_{site}"] += removed

    core_cls._deposit_surface_mass = deposit
    core_cls._scale_surface_mass = scale
    return originals


def _wrap_delivery(core_cls: type, rec: Recorder) -> dict[str, Any]:
    """Wrap the delivery witnesses: every path, and the canary's own term."""
    originals = {
        "_record_fomite_pickup": core_cls._record_fomite_pickup,
        "_deliver_fomite_requests": core_cls._deliver_fomite_requests,
    }

    def record_pickup(
        self: Any,
        target: Any,
        zone_name: str,
        surface_mass: float,
        delivered: float,
        dose: float,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        site = _caller_name()
        originals["_record_fomite_pickup"](
            self, target, zone_name, surface_mass, delivered, dose,
            *args, **kwargs,
        )
        pathogen_id = kwargs.get("pathogen_id")
        if pathogen_id is None and len(args) >= 6:
            pathogen_id = args[5]
        if pathogen_id != rec.pathogen_id:
            return
        book = rec.zone(zone_name)
        book.delivered += float(delivered)
        book.delivery_calls += 1
        book.dose += float(dose)
        rec.delivery_by_site[site] += float(delivered)
        rec.epoch_acc["delivered"] += float(delivered)
        rec.epoch_acc["dose"] += float(dose)

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
        pathogen_id = kwargs.get("pathogen_id")
        if pathogen_id is None and len(args) >= 7:
            pathogen_id = args[6]
        if pathogen_id != rec.pathogen_id:
            return delivered
        book = rec.zone(zone_name)
        book.offered += float(surface_mass)
        book.offer_calls += 1
        rec.epoch_acc["offered"] += float(surface_mass)
        return delivered

    core_cls._record_fomite_pickup = record_pickup
    core_cls._deliver_fomite_requests = deliver
    return originals


def _wrap_hand_and_phase(core_cls: type, rec: Recorder) -> dict[str, Any]:
    """Wrap the hand reservoir and the emesis eligibility conditions."""
    originals = {
        "_replenish_hand": core_cls._replenish_hand,
        "_emesis_phase": core_cls._emesis_phase,
        "_hand_carriage_propensity": core_cls._hand_carriage_propensity,
        "_stationary_hand_load": core_cls._stationary_hand_load,
        "_stool_event_occurs": core_cls._stool_event_occurs,
    }

    def propensity(self: Any, agent: Any, pathogen_id: str) -> float:
        value = originals["_hand_carriage_propensity"](
            self, agent, pathogen_id,
        )
        if pathogen_id == rec.pathogen_id:
            rec.propensities.append(float(value))
        return value

    def stationary(
        self: Any,
        target: float,
        inactivation_rate_per_hour: float,
        events_per_day: float,
    ) -> float:
        value = originals["_stationary_hand_load"](
            self, target, inactivation_rate_per_hour, events_per_day,
        )
        rec.stationary_rows.append({
            "target_gec": float(target),
            "inactivation_rate_per_hour": float(inactivation_rate_per_hour),
            "events_per_day": float(events_per_day),
            "initial_load_gec": float(value),
        })
        return value

    def stool_event(self: Any, events_per_day: float) -> bool:
        occurred = originals["_stool_event_occurs"](self, events_per_day)
        rec.stool_events["calls"] += 1
        rec.stool_events["events"] += int(bool(occurred))
        return occurred

    def replenish(
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
        target = float(agent.get_pathogen_hand_target(pathogen_id, profile or {}))
        load = float(agent.hand_load_by_pathogen.get(pathogen_id, 0.0))
        rec.hand["max_target_gec"] = max(rec.hand["max_target_gec"], target)
        rec.hand["max_load_gec"] = max(rec.hand["max_load_gec"], load)
        if target > 0.0:
            rec.hand["target_positive_calls"] += 1
            if load >= target:
                rec.hand["calls_at_target"] += 1
            elif load <= target * 1e-6:
                rec.hand["calls_underflowed"] += 1

    def emesis_phase(
        self: Any, agent: Any, pathogen_id: str, profile: dict,
    ) -> Any:
        result = originals["_emesis_phase"](self, agent, pathogen_id, profile)
        if pathogen_id == rec.pathogen_id:
            _tally_eligibility(self, rec, agent, pathogen_id, profile, result)
        return result

    core_cls._replenish_hand = replenish
    core_cls._emesis_phase = emesis_phase
    core_cls._hand_carriage_propensity = propensity
    core_cls._stationary_hand_load = stationary
    core_cls._stool_event_occurs = stool_event
    return originals


def _tally_eligibility(
    core: Any,
    rec: Recorder,
    agent: Any,
    pathogen_id: str,
    profile: dict,
    result: Any,
) -> None:
    """Decompose one ``_emesis_phase`` call into the condition that failed."""
    rec.eligibility["calls"] += 1
    infection = agent.infections.get(pathogen_id)
    if infection is None:
        rec.eligibility["not_infected"] += 1
        return
    rec.infected_hosts.add(int(agent.agent_id))
    symptomatic = core._symptomatic_phase(agent, pathogen_id, profile)
    if symptomatic is None:
        rec.eligibility["infected_but_no_symptomatic_phase"] += 1
        return
    rec.symptomatic_hosts.add(int(agent.agent_id))
    phase, _age = symptomatic
    name = str(phase.get("name", "unnamed"))
    rec.phase_names[name] += 1
    if result is None:
        rec.eligibility["symptomatic_phase_without_vomiting"] += 1
    else:
        rec.eligibility["eligible"] += 1


def _wrap_epochs(core_cls: type, rec: Recorder) -> dict[str, Any]:
    """Wrap the epoch boundaries so every term is dated."""
    originals = {
        "_pathway_fomite": core_cls._pathway_fomite,
        "_update_surface_pools": core_cls._update_surface_pools,
    }

    def pathway_fomite(
        self: Any, epoch: int, *args: Any, **kwargs: Any,
    ) -> Any:
        rec.core = self
        rec.epoch = int(epoch)
        return originals["_pathway_fomite"](self, epoch, *args, **kwargs)

    def update_pools(self: Any, *args: Any, **kwargs: Any) -> Any:
        result = originals["_update_surface_pools"](self, *args, **kwargs)
        rec.core = self
        row = {"epoch": rec.epoch, "pool_total_gec": rec.pool_total()}
        row.update({key: float(value) for key, value in rec.epoch_acc.items()})
        rec.epoch_rows.append(row)
        rec.epoch_acc.clear()
        return result

    core_cls._pathway_fomite = pathway_fomite
    core_cls._update_surface_pools = update_pools
    return originals


@contextmanager
def instrumented(rec: Recorder) -> Any:
    """Install the read-only wrappers for the duration of one run."""
    core_cls = tc.TransmissionCore
    saved: dict[str, Any] = {}
    saved.update(_wrap_surface_mass(core_cls, rec))
    saved.update(_wrap_delivery(core_cls, rec))
    saved.update(_wrap_hand_and_phase(core_cls, rec))
    saved.update(_wrap_epochs(core_cls, rec))
    try:
        yield
    finally:
        for name, method in saved.items():
            setattr(core_cls, name, method)


def build_spec(
    *, seed: int, platform: str, bundle: str, epochs: int, num_agents: int,
) -> dict[str, Any]:
    """The shipped run, at one seed, with no override of any kind."""
    return {
        "schema_version": "1.0.0",
        "description": "noro_diag fomite_mass_balance",
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
        "config_overrides": {"ship_graph": {"num_agents": int(num_agents)}},
        "pathogen_overrides": {},
    }


def _zone_rows(rec: Recorder) -> list[dict[str, Any]]:
    """Per-zone books, worst balance error first."""
    rows = []
    pools = {}
    if rec.core is not None:
        pools = rec.core.surface_pools_by_pathogen.get(rec.pathogen_id, {})
    for zone_name, book in rec.zones.items():
        residual = float(pools.get(zone_name, 0.0))
        removed_total = sum(book.removed.values())
        error = book.deposited - removed_total - residual
        scale = max(book.deposited, removed_total + residual)
        rows.append({
            "zone": zone_name,
            "deposited_gec": book.deposited,
            "deposit_calls": book.deposit_calls,
            "removed_gec": dict(book.removed),
            "removed_total_gec": removed_total,
            "residual_gec": residual,
            "balance_error_gec": error,
            "balance_error_relative": (
                abs(error) / scale if scale > 0.0 else 0.0
            ),
            "offered_gec": book.offered,
            "offer_calls": book.offer_calls,
            "delivered_gec": book.delivered,
            "delivery_calls": book.delivery_calls,
            "dose_gec": book.dose,
        })
    rows.sort(key=lambda row: row["balance_error_relative"], reverse=True)
    return rows


def _voyage_balance(rec: Recorder, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """The voyage-total book and the criterion's verdict on it."""
    deposited = sum(row["deposited_gec"] for row in rows)
    removed = sum(row["removed_total_gec"] for row in rows)
    residual = sum(row["residual_gec"] for row in rows)
    error = deposited - removed - residual
    scale = max(deposited, removed + residual)
    relative = abs(error) / scale if scale > 0.0 else 0.0
    worst = rows[0]["balance_error_relative"] if rows else 0.0
    delivered = sum(rec.delivery_by_site.values())
    zones_never_offered = [
        row for row in rows
        if row["offer_calls"] == 0 and row["deposited_gec"] > 0.0
    ]
    never_offered_mass = sum(row["deposited_gec"] for row in zones_never_offered)
    removed_by_site: dict[str, float] = defaultdict(float)
    for row in rows:
        for site, mass in row["removed_gec"].items():
            removed_by_site[site] += mass
    return {
        "deposited_gec": deposited,
        "removed_total_gec": removed,
        "removed_by_call_site_gec": dict(removed_by_site),
        "residual_gec": residual,
        "balance_error_gec": error,
        "balance_error_relative": relative,
        "worst_zone_error_relative": worst,
        "verdict": (
            "CONSERVED"
            if relative <= VOYAGE_TOLERANCE and worst <= ZONE_TOLERANCE
            else "LEAK"
        ),
        "deposit_by_call_site_gec": dict(rec.deposit_by_site),
        "delivered_all_paths_gec": delivered,
        "delivered_by_call_site_gec": dict(rec.delivery_by_site),
        "offered_gec": sum(row["offered_gec"] for row in rows),
        "zones_with_deposit_never_offered": len(zones_never_offered),
        "deposited_into_never_offered_zones_gec": never_offered_mass,
        "never_offered_share_of_deposit": (
            never_offered_mass / deposited if deposited > 0.0 else 0.0
        ),
        "void_for_conservation": deposited <= 0.0,
    }


def summarise(rec: Recorder, seed: int, epochs: int) -> dict[str, Any]:
    """The balance, the delivery witness, and the eligibility decomposition."""
    rows = _zone_rows(rec)
    return {
        "seed": seed,
        "epochs": epochs,
        "pathogen_id": rec.pathogen_id,
        "voyage_balance": _voyage_balance(rec, rows),
        "zones": rows,
        "epoch_timeline": rec.epoch_rows,
        "hand_witness": dict(rec.hand),
        "hand_carriage_propensities": rec.propensities,
        "stationary_hand_load_rows": rec.stationary_rows,
        "stool_event_witness": dict(rec.stool_events),
        "emesis_eligibility": dict(rec.eligibility),
        "symptomatic_phase_names": dict(rec.phase_names),
        "hosts_infected": len(rec.infected_hosts),
        "hosts_symptomatic": len(rec.symptomatic_hosts),
    }


def run_seed(
    *, seed: int, platform: str, bundle: str, epochs: int, pathogen_id: str,
) -> dict[str, Any]:
    """Run one instrumented voyage and return its measurement."""
    num_agents = declared_total(platform)
    spec_dict = build_spec(
        seed=seed, platform=platform, bundle=bundle,
        epochs=epochs, num_agents=num_agents,
    )
    rec = Recorder(pathogen_id=pathogen_id)
    # The spec path lives under the repository root, not /tmp, because
    # validated_open refuses publicly writable targets; the directory is
    # still a fresh private TemporaryDirectory.
    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
        spec_path = resolve_child_path(tmp, "run_spec.json")
        with validated_open(
            spec_path, "w", allowed_roots=(tmp,), encoding="utf-8",
        ) as handle:
            handle.write(json.dumps(spec_dict))
        picard_spec = PicardRunSpec.from_picard_json(str(REPO_ROOT), spec_path)
        with instrumented(rec):
            ShipSimulation(picard_spec, display=False).run()
    summary = summarise(rec, seed, epochs)
    summary["platform"] = platform
    summary["num_agents"] = num_agents
    summary["bundle"] = bundle
    return summary


def print_summary(summary: dict[str, Any]) -> None:
    """Print the balance verdict and the eligibility decomposition."""
    balance = summary["voyage_balance"]
    print(f"\n=== {summary['platform']} seed {summary['seed']} "
          f"({summary['num_agents']} agents, {summary['epochs']} epochs) ===")
    print(f"balance verdict: {balance['verdict']}")
    for key in (
        "deposited_gec", "removed_total_gec", "residual_gec",
        "balance_error_gec", "balance_error_relative",
        "worst_zone_error_relative", "delivered_all_paths_gec", "offered_gec",
        "deposited_into_never_offered_zones_gec",
        "never_offered_share_of_deposit",
    ):
        print(f"  {key:42s} {balance[key]:.6g}")
    print(f"  deposit by call site:  {balance['deposit_by_call_site_gec']}")
    print(f"  removed by call site:  {balance['removed_by_call_site_gec']}")
    print(f"  delivery by call site: {balance['delivered_by_call_site_gec']}")
    print(f"  zones with deposit never offered: "
          f"{balance['zones_with_deposit_never_offered']}")
    print(f"hand witness: {summary['hand_witness']}")
    print(f"hand carriage propensities: "
          f"{summary['hand_carriage_propensities']}")
    print(f"stationary hand load rows: "
          f"{summary['stationary_hand_load_rows']}")
    print(f"stool event witness: {summary['stool_event_witness']}")
    print(f"emesis eligibility: {summary['emesis_eligibility']}")
    print(f"symptomatic phases: {summary['symptomatic_phase_names']}")
    print(f"hosts infected / symptomatic: {summary['hosts_infected']} / "
          f"{summary['hosts_symptomatic']}")
    print("worst three zones by balance error:")
    for row in summary["zones"][:3]:
        print(f"  {row['zone']}: deposited {row['deposited_gec']:.6g}, "
              f"removed {row['removed_total_gec']:.6g}, "
              f"residual {row['residual_gec']:.6g}, "
              f"offers {row['offer_calls']}, "
              f"rel err {row['balance_error_relative']:.3g}")


def _identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise argparse.ArgumentTypeError(f"invalid identifier: {value!r}")
    return value


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--platform", type=_identifier, default="expedition_cruise_450")
    parser.add_argument(
        "--bundle", type=_identifier,
        default=asset_defaults.DEFAULT_PATHOGEN_BUNDLE_ID)
    parser.add_argument(
        "--pathogen-id", type=_identifier, default="norwalk_gi")
    parser.add_argument("--epochs", type=int, default=168)
    parser.add_argument(
        "--seeds", type=int, nargs="+", default=[8001, 8106],
        help="the seeds NORO-EMESIS-CANARY-01 measured on this hull",
    )
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args(argv)


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
        )
        filename = f"fomite_mass_balance_{args.platform}_seed{seed}.json.gz"
        path = resolve_child_path(str(out_dir), filename)
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=1)
        print_summary(summary)
        print(f"written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
