#!/usr/bin/env python3
"""ISO-QUARTERS-01 local smoke: a confined host's emesis reaches service.

One verbatim defpair-style cell from the noro_age_food_01 manifest, run
three ways:

- default arm — the census-instrumented voyage, verbatim. Reads the
  confined (quarantined) hosts' emesis deposit zones and the steward
  ``service_deliveries``/``service_dose_credited`` telemetry: the real
  defpair-measured gap, where compartment-keyed patches existed but the
  parent-keyed service read never found them.
- ``--isolate-confined`` — an epoch observer mirrors
  ``state.quarantined_ids`` into ``state.isolated_ids`` after each
  epoch's record step, so every confined host is held under the
  ``Isolated_In_Quarters`` sentinel placement next epoch. The deposit
  pass then has to file the bolus into the quarters pool itself.
- ``--mode off`` — the labelled baseline arm: the cell replays the
  pre-change behaviour for paired-seed attribution.

``--fingerprint`` runs the uninstrumented voyage and dumps the voyage
blocks only — the cross-tree bit-identity witness: ``off`` at this SHA
must equal the parent tree's run on the same spec and seed.

Nothing here draws from the engine's RNG streams except the voyage
itself.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from picard_framework.runs.mega_cruise_campaign.campaign_runner import (  # noqa: E402
    generate_tier_runs,
)
from picard_framework.simulation.ship_simulation import ShipSimulation  # noqa: E402
from simulation_utils.paths import prepare_output_directory  # noqa: E402
from tools.diag.instrument_common import materialized_picard_spec  # noqa: E402
from tools.diag.manifest_args import (  # noqa: E402
    add_manifest_args,
    filter_runs_by_seeds,
    index_run,
)
from tools.noro_diag.growth_chain_census import (  # noqa: E402
    _control_voyage,
    _load_manifest,
    run_seed,
)


def _pick_spec(args: argparse.Namespace) -> tuple[dict[str, Any], Any]:
    manifest = _load_manifest(args.manifest)
    clock = manifest.get("natural_history_clock")
    runs = list(generate_tier_runs(
        manifest, args.tier,
        epochs_override=args.epochs_override,
        num_agents_override=args.num_agents_override,
        natural_history_clock=str(clock) if clock is not None else None,
    ))
    runs = index_run(runs, args.index, args.tier)
    runs = filter_runs_by_seeds(runs, args.seeds or None)
    if len(runs) != 1:
        raise SystemExit(
            f"smoke needs exactly one run; got {len(runs)}",
        )
    run_id, spec = runs[0]
    if args.mode is not None:
        spec.setdefault("config_overrides", {}).setdefault(
            "transmission", {},
        )["isolated_quarters_deposits"] = {"mode": args.mode}
    return spec, clock, run_id


def _confined_deposit_summary(sim: Any, pathogen_id: str) -> dict[str, Any]:
    """Where the confined population's emesis deposited, by pool key."""
    core = sim.tx_core
    engine = sim.engine
    confined = set(getattr(engine, "quarantined_ids", set())) | set(
        getattr(engine, "isolated_ids", set()),
    )
    deposit_zones: Counter[str] = Counter()
    confined_emitters: dict[int, dict[str, Any]] = {}
    for agent in engine.agents:
        records = (
            agent.emesis_deposition_records_by_pathogen.get(pathogen_id, [])
        )
        if not records:
            continue
        for rec in records:
            deposit_zones[rec["zone"]] += 1
        if agent.agent_id in confined or (
            agent.current_location == "Isolated_In_Quarters"
        ):
            confined_emitters[int(agent.agent_id)] = {
                "location": agent.current_location,
                "home_zone": agent.home_zone,
                "emits": len(records),
                "zones": sorted({r["zone"] for r in records}),
                "surface_gec": sum(r["surface_load"] for r in records),
            }
    patch_keys = {
        pid: sorted(pools)
        for pid, pools in core.emesis_patch_pools_by_pathogen.items()
    }
    return {
        "confined_emitters": confined_emitters,
        "deposit_zone_counts": dict(deposit_zones),
        "patch_pool_keys": patch_keys,
        "caregiver_telemetry": dict(
            getattr(core, "caregiver_telemetry", {}) or {},
        ),
    }


def _isolate_confined_observer(sim: Any, work: Any) -> None:
    """Hold every quarantined host under the isolation sentinel.

    Runs after the epoch's record step, so the mirrored set takes effect
    at next epoch's placement; releases from quarantine release the
    sentinel too.
    """
    work.state.isolated_ids = set(work.state.quarantined_ids)


def _isolated_voyage(
    spec: dict[str, Any], clock: Any, pathogen_id: str,
) -> dict[str, Any]:
    """The verbatim cell with confinement routed through the sentinel."""
    with materialized_picard_spec(spec, REPO_ROOT) as picard_spec:
        sim = ShipSimulation(picard_spec, display=False)
        sim.initialize()
        sim.epoch_observer = _isolate_confined_observer
        sim.run()
    out = _confined_deposit_summary(sim, pathogen_id)
    out["isolated_ids_final"] = sorted(
        getattr(sim.engine, "isolated_ids", set()),
    )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_manifest_args(parser, required=True)
    parser.add_argument("--seeds", type=int, nargs="*", default=None)
    parser.add_argument("--pathogen-id", type=str, default="norwalk_gi")
    parser.add_argument("--epochs-override", type=int, default=None)
    parser.add_argument("--num-agents-override", type=int, default=None)
    parser.add_argument(
        "--mode", choices=("deposits_only", "off"), default=None,
        help="inject transmission.isolated_quarters_deposits.mode "
             "(unset leaves the spec's own transmission block)",
    )
    parser.add_argument(
        "--isolate-confined", action="store_true",
        help="hold quarantined hosts under Isolated_In_Quarters",
    )
    parser.add_argument(
        "--fingerprint", action="store_true",
        help="uninstrumented voyage blocks only (cross-tree identity)",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    spec, clock, run_id = _pick_spec(args)
    out_dir = Path(prepare_output_directory(
        str(args.out), allowed_roots=(str(REPO_ROOT),),
    ))

    if args.fingerprint:
        voyage = _control_voyage(spec, clock)
        result = {
            "run_id": run_id,
            "seed": int(spec["run"]["random_seed"]),
            "mode": args.mode or "deposits_only",
            "voyage": voyage,
        }
    elif args.isolate_confined:
        result = {
            "run_id": run_id,
            "seed": int(spec["run"]["random_seed"]),
            "mode": args.mode or "deposits_only",
            "arm": "isolate_confined",
            **_isolated_voyage(spec, clock, args.pathogen_id),
        }
    else:
        payload, voyage, _initiation = run_seed(
            pathogen_id=args.pathogen_id, spec_dict=spec,
            natural_history_clock=clock, payload_profile="full",
        )
        emits_by_zone = Counter(
            str(row.get("zone")) for row in payload.get("emits", [])
        )
        result = {
            "run_id": run_id,
            "seed": int(spec["run"]["random_seed"]),
            "mode": args.mode or "deposits_only",
            "arm": "verbatim",
            "ignited": payload.get("ignited"),
            "emits_by_zone": dict(emits_by_zone),
            "caregiver_telemetry": payload.get("caregiver_telemetry"),
            "meta": {
                k: v for k, v in (payload.get("meta") or {}).items()
                if k not in {"row_stream_counts"}
            },
        }

    path = out_dir / f"iso_quarters_smoke_{args.tier}_{run_id}.json"
    path.write_text(json.dumps(result, indent=1, sort_keys=True, default=str))
    print(json.dumps(result, indent=1, sort_keys=True, default=str))
    print(f"written: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
