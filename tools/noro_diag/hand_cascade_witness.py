#!/usr/bin/env python3
"""NORO-HAND-CASCADE-01 witness: carrier redeposition and ordered fomite arms.

Runs the same paired seeds through the legacy, ``carriers``, ``ordered``,
and combined arms and records the mass that only the repaired gates can
move: non-shedder hand->surface/food/sanitary deposits, hand-strain
bookkeeping, and the downstream fomite delivery/dose books from
``fomite_mass_balance``.

The wrappers are read-only with respect to RNG: they classify deponents
and sum masses returned by the engine, and never draw from the engine
generator. ``_get_hand_depositors``/``_get_shedders`` are pure status
reads, so the extra classification calls do not perturb the stream.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines import transmission_core as tc  # noqa: E402
from simulation_utils.asset_defaults import DEFAULT_PATHOGEN_BUNDLE_ID  # noqa: E402
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_child_path,
)
from tools.diag.instrument_common import attr_patches, install_wrappers  # noqa: E402
from tools.diag.manifest_args import identifier  # noqa: E402
from tools.noro_diag import fomite_mass_balance as fmb  # noqa: E402

ARMS: dict[str, dict[str, Any]] = {
    "legacy": {},
    "carriers": {
        "transmission": {"hand_redeposit_mode": "carriers"},
    },
    "ordered": {
        "transmission": {"intra_epoch_causal_order": "ordered"},
    },
    "carriers_ordered": {
        "transmission": {
            "hand_redeposit_mode": "carriers",
            "intra_epoch_causal_order": "ordered",
        },
    },
}


class CascadeRecorder:
    """Carrier-only deposit and hand-strain witnesses for one voyage."""

    def __init__(self, pathogen_id: str) -> None:
        self.pathogen_id = pathogen_id
        self.surface_deposit_gec = 0.0
        self.surface_deposit_calls = 0
        self.food_deposit_gec = 0.0
        self.food_deposit_calls = 0
        self.sanitary_deposit_gec = 0.0
        self.sanitary_deposit_calls = 0
        self.surface_carrier_candidates = 0
        self.surface_carrier_hand_gec = 0.0
        self.surface_carrier_max_hand_gec = 0.0
        self.food_carrier_candidates = 0
        self.food_carrier_hand_gec = 0.0
        self.food_carrier_max_hand_gec = 0.0
        self.sanitary_carrier_candidates = 0
        self.sanitary_carrier_hand_gec = 0.0
        self.sanitary_carrier_max_hand_gec = 0.0
        self.mode_records = Counter()
        self.hand_strain_records = Counter()
        self.hand_strain_pathogens = Counter()

    def wrappers(self) -> dict[str, Any]:
        """Read-only wrappers installed on ``TransmissionCore``."""
        rec = self
        cls = tc.TransmissionCore
        orig_surface = cls._shedder_surface_deposits
        orig_food = cls._food_deposits
        orig_sanitary = cls._sanitary_venue_deposits
        orig_record_strain = cls._record_hand_strain

        def shedder_surface_deposits(
            self: Any, zone_name: str, shedders: list, epoch: int,
            pathogen_id: str, profile: dict | None,
        ) -> list:
            carrier_agents = (
                {
                    agent.agent_id: agent for agent, sv in shedders
                    if float(sv) <= 0.0
                }
                if pathogen_id == rec.pathogen_id else {}
            )
            carrier_ids = set(carrier_agents)
            if pathogen_id == rec.pathogen_id and carrier_ids:
                loads = [
                    float(agent.hand_load_by_pathogen.get(pathogen_id, 0.0))
                    for agent in carrier_agents.values()
                ]
                rec.surface_carrier_candidates += len(loads)
                rec.surface_carrier_hand_gec += sum(loads)
                rec.surface_carrier_max_hand_gec = max(
                    rec.surface_carrier_max_hand_gec, max(loads),
                )
            deposits = orig_surface(
                self, zone_name, shedders, epoch, pathogen_id, profile,
            )
            if carrier_ids:
                carrier_deposits = [
                    (agent, mass) for agent, mass in deposits
                    if agent.agent_id in carrier_ids
                ]
                rec.surface_deposit_gec += sum(
                    float(mass) for _agent, mass in carrier_deposits
                )
                rec.surface_deposit_calls += len(carrier_deposits)
            return deposits

        def food_deposits(
            self: Any, zone_name: str, occupants: list, pathogen_id: str,
            profile: dict | None, food_cfg: dict[str, Any], epoch: int,
        ) -> list:
            deponents = self._get_hand_depositors(
                occupants, pathogen_id, profile,
            )
            carrier_agents = (
                {
                    agent.agent_id: agent for agent, sv in deponents
                    if float(sv) <= 0.0
                }
                if pathogen_id == rec.pathogen_id else {}
            )
            carrier_ids = set(carrier_agents)
            if pathogen_id == rec.pathogen_id and carrier_ids:
                loads = [
                    float(agent.hand_load_by_pathogen.get(pathogen_id, 0.0))
                    for agent in carrier_agents.values()
                ]
                rec.food_carrier_candidates += len(loads)
                rec.food_carrier_hand_gec += sum(loads)
                rec.food_carrier_max_hand_gec = max(
                    rec.food_carrier_max_hand_gec, max(loads),
                )
            deposits = orig_food(
                self, zone_name, occupants, pathogen_id, profile,
                food_cfg, epoch,
            )
            if carrier_ids:
                carrier_deposits = [
                    (agent, mass) for agent, mass in deposits
                    if agent.agent_id in carrier_ids
                ]
                rec.food_deposit_gec += sum(
                    float(mass) for _agent, mass in carrier_deposits
                )
                rec.food_deposit_calls += len(carrier_deposits)
            return deposits

        def sanitary_venue_deposits(
            self: Any, records: dict, agents: dict, epoch: int,
            pathogen_id: str, profile: dict | None,
        ) -> None:
            carrier_ids: set[int] = set()
            hand_before: dict[int, float] = {}
            if pathogen_id == rec.pathogen_id:
                for aid in {key[0] for key in records}:
                    agent = agents.get(aid)
                    if agent is None:
                        continue
                    deponents = self._get_hand_depositors(
                        [agent], pathogen_id, profile,
                    )
                    if deponents and float(deponents[0][1]) <= 0.0:
                        carrier_ids.add(aid)
                        hand_before[aid] = float(
                            agent.hand_load_by_pathogen.get(pathogen_id, 0.0),
                        )
            if pathogen_id == rec.pathogen_id:
                loads = list(hand_before.values())
                rec.sanitary_carrier_candidates += len(loads)
                rec.sanitary_carrier_hand_gec += sum(loads)
                if loads:
                    rec.sanitary_carrier_max_hand_gec = max(
                        rec.sanitary_carrier_max_hand_gec, max(loads),
                    )
            orig_sanitary(self, records, agents, epoch, pathogen_id, profile)
            for aid in carrier_ids:
                agent = agents.get(aid)
                if agent is None:
                    continue
                after = float(
                    agent.hand_load_by_pathogen.get(pathogen_id, 0.0),
                )
                deposit = max(0.0, hand_before[aid] - after)
                rec.sanitary_deposit_gec += deposit
                if deposit > 0.0:
                    rec.sanitary_deposit_calls += 1

        def record_hand_strain(
            self: Any, target: Any, pathogen_id: str,
            surface_attribution: Any,
        ) -> None:
            rec.mode_records[
                (
                    getattr(self, "hand_redeposit_mode", ""),
                    getattr(self, "intra_epoch_order", ""),
                )
            ] += 1
            orig_record_strain(self, target, pathogen_id, surface_attribution)
            if (
                pathogen_id == rec.pathogen_id
                and getattr(self, "hand_redeposit_mode", "") == "carriers"
                and surface_attribution is not None
            ):
                strain_id = target.hand_strain_by_pathogen.get(pathogen_id)
                if strain_id:
                    rec.hand_strain_records[strain_id] += 1
                    rec.hand_strain_pathogens[pathogen_id] += 1

        return {
            "_shedder_surface_deposits": shedder_surface_deposits,
            "_food_deposits": food_deposits,
            "_sanitary_venue_deposits": sanitary_venue_deposits,
            "_record_hand_strain": record_hand_strain,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "surface_deposit_gec": self.surface_deposit_gec,
            "surface_deposit_calls": self.surface_deposit_calls,
            "food_deposit_gec": self.food_deposit_gec,
            "food_deposit_calls": self.food_deposit_calls,
            "sanitary_deposit_gec": self.sanitary_deposit_gec,
            "sanitary_deposit_calls": self.sanitary_deposit_calls,
            "surface_carrier_candidates": self.surface_carrier_candidates,
            "surface_carrier_hand_gec": self.surface_carrier_hand_gec,
            "surface_carrier_max_hand_gec": self.surface_carrier_max_hand_gec,
            "food_carrier_candidates": self.food_carrier_candidates,
            "food_carrier_hand_gec": self.food_carrier_hand_gec,
            "food_carrier_max_hand_gec": self.food_carrier_max_hand_gec,
            "sanitary_carrier_candidates": self.sanitary_carrier_candidates,
            "sanitary_carrier_hand_gec": self.sanitary_carrier_hand_gec,
            "sanitary_carrier_max_hand_gec": self.sanitary_carrier_max_hand_gec,
            "mode_records": {
                f"{reposit}|{order}": count
                for (reposit, order), count in self.mode_records.items()
            },
            "hand_strain_records": dict(self.hand_strain_records),
            "hand_strain_pathogens": dict(self.hand_strain_pathogens),
        }


def _row(summary: dict[str, Any], cascade: dict[str, Any]) -> dict[str, Any]:
    balance = summary["voyage_balance"]
    return {
        "seed": summary["seed"],
        "platform": summary["platform"],
        "epochs": summary["epochs"],
        "bundle": summary["bundle"],
        "num_agents": summary["num_agents"],
        "hosts_infected": summary["hosts_infected"],
        "hosts_symptomatic": summary["hosts_symptomatic"],
        "deposited_gec": balance["deposited_gec"],
        "removed_total_gec": balance["removed_total_gec"],
        "residual_gec": balance["residual_gec"],
        "delivered_all_paths_gec": balance["delivered_all_paths_gec"],
        "delivered_to_reservoir_gec": balance["delivered_to_reservoir_gec"],
        "offered_gec": balance["offered_gec"],
        "dose_gec": sum(
            float(zone.get("dose_gec", 0.0)) for zone in summary["zones"]
        ),
        "deposit_by_call_site_gec": balance["deposit_by_call_site_gec"],
        "delivered_by_call_site_gec": balance["delivered_by_call_site_gec"],
        "cascade": cascade,
    }


def _arm_spec(spec_dict: dict[str, Any], arm: str) -> dict[str, Any]:
    """Return a spec with this arm's transmission overrides merged in."""
    spec = copy.deepcopy(spec_dict)
    overrides = ARMS.get(arm) or {}
    cfg = spec.setdefault("config_overrides", {})
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(cfg.get(key), dict):
            merged = dict(cfg[key])
            merged.update(value)
            cfg[key] = merged
        else:
            cfg[key] = value
    return spec


def _run_spec_arm(
    *, arm: str, spec_dict: dict[str, Any], seed: int, pathogen_id: str,
) -> dict[str, Any]:
    """Run one instrumented voyage for an already-materialized spec."""
    spec = _arm_spec(spec_dict, arm)
    cfg = spec.get("config_overrides") or {}
    num_agents = int((cfg.get("ship_graph") or {}).get("num_agents") or 0)
    if num_agents <= 0:
        raise ValueError("spec has no ship_graph.num_agents")
    platform = str(spec["catalog"]["platform_id"])
    bundle = str(spec["catalog"]["pathogen_bundle_id"])
    epochs = int(spec["run"]["num_epochs"])
    rec = fmb.Recorder(pathogen_id=pathogen_id)
    cascade = CascadeRecorder(pathogen_id)
    with attr_patches() as patches:
        originals = install_wrappers(tc.TransmissionCore, cascade.wrappers())
        patches.note_all(tc.TransmissionCore, originals)
        result = fmb._run_voyage(spec, rec)
    summary = fmb.summarise(rec, seed, epochs)
    summary.pop("epoch_timeline", None)
    summary["voyage"] = fmb._voyage_fingerprint(spec, result, num_agents)
    summary["platform"] = platform
    summary["num_agents"] = num_agents
    summary["bundle"] = bundle
    summary["cascade"] = cascade.as_dict()
    row = _row(summary, summary["cascade"])
    row["arm"] = arm
    row["config_overrides"] = ARMS[arm]
    row["run_id"] = spec.get("description")
    return row


def run_seed_arm(
    *, arm: str, seed: int, platform: str, bundle: str, epochs: int,
    pathogen_id: str,
) -> dict[str, Any]:
    """Run one instrumented voyage for one arm."""
    num_agents = fmb.declared_total(platform)
    spec_dict = fmb.build_spec(
        seed=seed, platform=platform, bundle=bundle, epochs=epochs,
        num_agents=num_agents, config_overrides=ARMS[arm],
    )
    return _run_spec_arm(
        arm=arm, spec_dict=spec_dict, seed=seed, pathogen_id=pathogen_id,
    )


def tier_specs(
    manifest_path: Path, tier_id: str, seeds: list[int],
) -> dict[int, dict[str, Any]]:
    """Materialize the campaign specs for one tier and requested seeds."""
    from picard_framework.runs.mega_cruise_campaign import campaign_runner

    manifest = campaign_runner.load_manifest(str(manifest_path))
    wanted = {int(seed) for seed in seeds}
    found: dict[int, dict[str, Any]] = {}
    for _rid, spec in campaign_runner.generate_tier_runs(manifest, tier_id):
        seed = int(spec["run"]["random_seed"])
        if seed in wanted:
            found[seed] = spec
        if len(found) == len(wanted):
            break
    missing = sorted(wanted - set(found))
    if missing:
        raise ValueError(f"tier {tier_id} has no specs for seeds {missing}")
    return found


def _delta_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per-seed deltas against the legacy arm for the same seed."""
    legacy = {
        int(row["seed"]): row for row in rows if row["arm"] == "legacy"
    }
    out = []
    for row in rows:
        if row["arm"] == "legacy":
            continue
        base = legacy.get(int(row["seed"]))
        if base is None:
            continue
        delta = {"arm": row["arm"], "seed": row["seed"]}
        for key in (
            "deposited_gec", "delivered_all_paths_gec", "dose_gec",
            "hosts_infected", "hosts_symptomatic",
        ):
            delta[f"delta_{key}"] = float(row[key]) - float(base[key])
        for key in (
            "surface_deposit_gec", "food_deposit_gec", "sanitary_deposit_gec",
        ):
            delta[f"carrier_{key}"] = row["cascade"][key]
        out.append(delta)
    return out


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--platform", type=identifier, default="expedition_cruise_450")
    parser.add_argument(
        "--bundle", type=identifier, default=DEFAULT_PATHOGEN_BUNDLE_ID)
    parser.add_argument("--pathogen-id", type=identifier, default="norwalk_gi")
    parser.add_argument("--epochs", type=int, default=168)
    parser.add_argument("--seeds", type=int, nargs="+", default=[8001, 8106])
    parser.add_argument(
        "--arms", nargs="+", choices=sorted(ARMS),
        default=["legacy", "carriers", "ordered", "carriers_ordered"],
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--tier", type=str, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = Path(
        prepare_output_directory(str(args.out), allowed_roots=(str(REPO_ROOT),)),
    )
    rows: list[dict[str, Any]] = []
    specs_by_seed: dict[int, dict[str, Any]] | None = None
    if args.tier is not None:
        if args.manifest is None:
            raise SystemExit("--tier requires --manifest")
        specs_by_seed = tier_specs(args.manifest, args.tier, args.seeds)
    for arm in args.arms:
        for seed in args.seeds:
            if specs_by_seed is not None:
                row = _run_spec_arm(
                    arm=arm, spec_dict=specs_by_seed[int(seed)], seed=seed,
                    pathogen_id=args.pathogen_id,
                )
            else:
                row = run_seed_arm(
                    arm=arm, seed=seed, platform=args.platform,
                    bundle=args.bundle, epochs=args.epochs,
                    pathogen_id=args.pathogen_id,
                )
            rows.append(row)
            cascade = row["cascade"]
            print(
                f"{arm:18s} seed {seed}: "
                f"carrier surface {cascade['surface_deposit_gec']:.6g} GEC "
                f"({cascade['surface_deposit_calls']} calls), "
                f"food {cascade['food_deposit_gec']:.6g} GEC, "
                f"sanitary {cascade['sanitary_deposit_gec']:.6g} GEC, "
                f"delivered {row['delivered_all_paths_gec']:.6g} GEC, "
                f"dose {row['dose_gec']:.6g} GEC, "
                f"infected {row['hosts_infected']}",
            )
    payload = {
        "platform": args.platform,
        "bundle": args.bundle,
        "pathogen_id": args.pathogen_id,
        "epochs": args.epochs,
        "tier": args.tier,
        "manifest": str(args.manifest) if args.manifest else None,
        "rows": rows,
        "deltas_vs_legacy": _delta_rows(rows),
    }
    tag = args.tier or args.platform
    path = resolve_child_path(
        str(out_dir), f"hand_cascade_witness_{tag}.json.gz",
    )
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=1)
    print(f"written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
