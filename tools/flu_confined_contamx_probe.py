#!/usr/bin/env python3
"""FLU-CONTAMX-01: transport-engine re-lane of the settled flu confined cell.

Re-runs the conditioned ``influenza_a`` confined-cabinmate cell — the
CABIN-FLOOR-03 scored anchor settled at FLU-SOCIAL-01 — under
``hvac.transport_engine: contamx`` with identical seeds, plus a native
parity lane at the same HEAD, local only. The only delta vs the settled
conditioned cell is the transport-engine override; the payload's
``transport_engine`` block proves which engine class actually ran, because
a ContamX request falls back to native silently and the warning never
reaches the payload.

Usage:
    python3 tools/flu_confined_contamx_probe.py \
        --transport-engine contamx --seeds 8105 8106 --out-dir DIR
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

REPO_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_repo_path,
    validated_open,
)
from tools.covid_route_attribution import CabinPairChallengeLedger  # noqa: E402
from tools.diag.conditioned_cell import (  # noqa: E402
    ACTIVE,
    conditioned_spec,
    party_size,
)
from tools.noro_diag.cabin_pair_challenge_probe import (  # noqa: E402
    instrumented_voyage,
)

PATHOGEN_ID = "influenza_a"


def _transport_engine_identity(
    sim: Any, spec_dict: dict[str, Any], requested: str | None,
) -> dict[str, Any]:
    """Which transport engine actually ran, proven from the live engine."""
    engine = sim.contam_engine
    flows = [
        float(getattr(p, "flow_rate_m3h", 0.0))
        for p in (getattr(engine, "airflow_paths", []) or [])
    ]
    hvac_override = spec_dict.get("config_overrides", {}).get("hvac", {})
    return {
        "requested": requested or "native",
        "config_transport_engine": hvac_override.get("transport_engine"),
        "engine_class": type(engine).__name__ if engine is not None else None,
        "n_airflow_paths": len(getattr(engine, "airflow_paths", []) or []),
        "total_flow_m3h": round(sum(flows), 3),
        "max_path_flow_m3h": round(max(flows), 3) if flows else 0.0,
    }


def _route_sums(sim: Any, pathogen_id: str) -> dict[str, float]:
    """Summed per-route acquired dose over non-seeded infection records."""
    seeded = set(getattr(sim.engine, "explicit_seed_agent_ids", None) or ())
    totals: dict[str, float] = {}
    for agent in sim.engine.agents:
        if agent.agent_id in seeded:
            continue
        inf = agent.infections.get(pathogen_id)
        if not inf:
            continue
        for route, dose in (inf.get("acquired_particles_by_route") or {}).items():
            totals[route] = totals.get(route, 0.0) + float(dose)
    return totals


def _infection_tallies(sim: Any, pathogen_id: str) -> dict[str, Any]:
    """Fleet infection counts split imported vs onboard-acquired, by dominant route."""
    seeded = set(getattr(sim.engine, "explicit_seed_agent_ids", None) or ())
    acquired = 0
    imported = 0
    dominant: dict[str, int] = {}
    for agent in sim.engine.agents:
        inf = agent.infections.get(pathogen_id)
        if not inf:
            continue
        routes = inf.get("acquired_particles_by_route") or {}
        if routes and agent.agent_id not in seeded:
            acquired += 1
            route = max(routes, key=routes.get)
            dominant[route] = dominant.get(route, 0) + 1
        else:
            imported += 1
    return {
        "infections_total": acquired + imported,
        "infections_imported": imported,
        "infections_acquired": acquired,
        "infections_by_dominant_route": dominant,
    }


def run_cell(
    *,
    bundle: str,
    pathogen_id: str,
    seed: int,
    platform: str,
    epochs: int,
    confinement: str,
    transport_engine: str | None,
) -> dict[str, Any]:
    """One conditioned voyage under the cabin-pair ledger, one engine lane."""
    spec_dict, profile = conditioned_spec(
        bundle=bundle, pathogen_id=pathogen_id, seed=seed,
        platform=platform, epochs=epochs, confinement=confinement,
    )
    if transport_engine is not None:
        spec_dict.setdefault("config_overrides", {}).setdefault(
            "hvac", {},
        )["transport_engine"] = transport_engine
    sim, table = instrumented_voyage(spec_dict)
    channel_totals = {
        channel: sum(
            row["channel_dose"].get(channel, 0.0)
            for row in table["rows"]
            if row["confined_epochs"] > 0
        )
        for channel in CabinPairChallengeLedger.CHANNELS
    }
    payload: dict[str, Any] = {
        "bundle": bundle,
        "pathogen_id": pathogen_id,
        "seed": seed,
        "platform": platform,
        "confinement": confinement,
        "num_epoch_steps": epochs,
        "explicit_seed_count": party_size(profile),
        "dose_response": profile.get("dose_response"),
        "pairs_observed": table["pairs_observed"],
        "mate_index_pairs": table["mate_index_pairs"],
        "mate_slots": table["mate_slots"],
        "mate_secondaries": table["mate_secondaries"],
        "observed_mate_case_attack": table["observed_mate_case_attack"],
        "confined_index_pairs": table["confined_index_pairs"],
        "confined_slots": table["confined_slots"],
        "confined_secondaries": table["confined_secondaries"],
        "observed_mate_case_attack_confined": (
            table["observed_mate_case_attack_confined"]
        ),
        "lambda_confined_median": table["lambda_confined_quantiles"]["median"],
        "implied_sar_confined_median": table["implied_sar_confined_median"],
        "confined_channel_dose_totals": channel_totals,
        "acquired_particles_sums": _route_sums(sim, pathogen_id),
        "transport_engine": _transport_engine_identity(
            sim, spec_dict, transport_engine,
        ),
    }
    payload.update(_infection_tallies(sim, pathogen_id))
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", default="classic_cruise_1900")
    parser.add_argument("--bundle", default=ACTIVE)
    parser.add_argument("--pathogen-id", default=PATHOGEN_ID)
    parser.add_argument("--epochs", type=int, default=288)
    parser.add_argument(
        "--seeds", type=int, nargs="+", default=[8105, 8106],
        help="paired seeds; this platform's conditioned pair is 8105 8106",
    )
    parser.add_argument(
        "--confinement", choices=("organic", "declared"), default="declared",
        help="the settled conditioned cell holds SOP-017 declared day 1→end",
    )
    parser.add_argument(
        "--transport-engine", choices=["native", "contamx", "auto"],
        default=None,
        help="inject hvac.transport_engine into the cell's config_overrides "
        "(the only delta vs the settled cell). The payload's "
        "transport_engine block records which engine class ran, because a "
        "contamx request falls back to native silently.",
    )
    parser.add_argument("--out-dir", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = resolve_repo_path(REPO_ROOT, args.out_dir)
    prepare_output_directory(out_dir, allowed_roots=(REPO_ROOT,))
    for seed in args.seeds:
        payload = run_cell(
            bundle=args.bundle, pathogen_id=args.pathogen_id, seed=seed,
            platform=args.platform, epochs=args.epochs,
            confinement=args.confinement,
            transport_engine=args.transport_engine,
        )
        path = os.path.join(out_dir, f"seed_{seed}.json")
        with validated_open(
            path, "w", allowed_roots=(REPO_ROOT,), encoding="utf-8",
        ) as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
        engine = payload["transport_engine"]
        print(
            f"seed {seed}: infected={payload['infections_total']} "
            f"confined_slots={payload['confined_slots']} "
            f"confined_SAR={payload['observed_mate_case_attack_confined']} "
            f"hvac_channel_copies="
            f"{payload['confined_channel_dose_totals'].get('hvac', 0.0):.1f} "
            f"engine={engine['engine_class']} ({engine['n_airflow_paths']} "
            f"paths)",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
