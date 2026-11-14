#!/usr/bin/env python3
"""Secondary-transmission provenance probe for NORO-HAND-CASCADE-01.

Runs posted ``carriers_ordered`` M=1 cells under ``growth_chain_census`` and
classifies acquired infections by pathway provenance. The key join is
``common_source_food`` acquisitions to ``common_source.events``: provisioned
supply-chain pans are separated from aboard ``ill_handler``/``ill_diner``
sources, and fomite acquisitions keep their delivered source-generation mass.

The default payload profile is ``full`` because ``lean`` drops the pickup row
stream and therefore reports ``delivered_src_*`` as zero; the common-source
join still runs under ``lean``, but fomite acquired mass does not.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_child_path,
)
from tools.diag.manifest_args import identifier  # noqa: E402
from tools.noro_diag import growth_chain_census as gcc  # noqa: E402
from tools.noro_diag import hand_cascade_witness as witness  # noqa: E402

ARM = "carriers_ordered"
CS_PATHWAY = "common_source_food"
SUPPLY_KINDS = frozenset({"independent", "provisioned_lot"})
HOST_FIELDS = (
    "symptomatic_epochs",
    "infected_epochs",
    "shedding_gec",
    "deposit_gec",
    "emesis_emitted",
)


def _f(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _pathway(row: dict[str, Any]) -> str:
    return str(row.get("dominant_pathway") or "unknown").split(":", 1)[0]


def _host_index(hosts: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {
        int(host["agent_id"]): host
        for host in hosts
        if host.get("agent_id") is not None
    }


def _cs_windows(events: list[dict[str, Any]]) -> list[tuple[frozenset[int], int, int, dict[str, Any]]]:
    windows = []
    for event in events:
        takers = frozenset(int(t) for t in event.get("taker_ids") or ())
        windows.append((
            takers,
            int(event.get("start_epoch") or -(10**9)),
            int(event.get("end_epoch") or 10**9),
            event,
        ))
    return windows


def _cs_candidate(
    windows: list[tuple[frozenset[int], int, int, dict[str, Any]]],
    agent_id: int,
    epoch: int,
    dose: float,
) -> dict[str, Any] | None:
    best = None
    best_dist = None
    for takers, start, end, event in windows:
        if agent_id not in takers or not start <= epoch <= end:
            continue
        dist = abs(_f(event.get("per_serving_dose")) - dose)
        if best is None or dist < best_dist:
            best = event
            best_dist = dist
    return best


def _source_class(
    kind: str,
    source_agent_id: Any,
    host_by_id: dict[int, dict[str, Any]],
) -> str:
    if kind in SUPPLY_KINDS:
        return "supply_chain"
    if source_agent_id is None:
        return "unknown"
    gen = (host_by_id.get(int(source_agent_id)) or {}).get("gen")
    if gen == 0:
        return "import"
    if gen is not None and int(gen) >= 1:
        return "acquired"
    return "unknown"


def _path_stats() -> dict[str, float]:
    return {
        "acquisitions": 0.0,
        "dose_read_gec": 0.0,
        "delivered_src_import_gec": 0.0,
        "delivered_src_acquired_gec": 0.0,
        "delivered_src_unknown_gec": 0.0,
    }


def summarise_secondary_chain(payload: dict[str, Any]) -> dict[str, Any]:
    """Fold one census payload into pathway provenance and CS-source counts."""
    acqs = list(payload.get("acquisitions") or [])
    hosts = list(payload.get("hosts") or [])
    host_by_id = _host_index(hosts)
    cs = payload.get("common_source") or {}
    events = list(cs.get("events") or [])
    objects = list(cs.get("objects") or [])
    obj_by_id = {
        str(obj.get("object_id")): obj
        for obj in objects
        if obj.get("object_id") is not None
    }
    windows = _cs_windows(events)

    kind_counts: Counter[str] = Counter()
    class_counts: Counter[str] = Counter()
    unmatched = 0
    path_stats: dict[str, dict[str, float]] = defaultdict(_path_stats)
    sym_epochs_by_path: Counter[str] = Counter()
    sym_hosts_by_path: dict[str, set[int]] = defaultdict(set)

    for row in acqs:
        aid = int(row.get("agent_id"))
        epoch = int(row.get("epoch") or 0)
        dose = _f(row.get("dose_read"))
        host = host_by_id.get(aid) or {}
        for field in HOST_FIELDS:
            row[f"host_{field}"] = host.get(field)

        path = _pathway(row)
        stats = path_stats[path]
        stats["acquisitions"] += 1.0
        stats["dose_read_gec"] += dose
        stats["delivered_src_import_gec"] += _f(row.get("delivered_src_import_gec"))
        stats["delivered_src_acquired_gec"] += _f(row.get("delivered_src_acquired_gec"))
        stats["delivered_src_unknown_gec"] += _f(row.get("delivered_src_unknown_gec"))
        sym_epochs = _f(host.get("symptomatic_epochs"))
        if sym_epochs > 0.0:
            sym_epochs_by_path[path] += sym_epochs
            sym_hosts_by_path[path].add(aid)

        if not str(row.get("dominant_pathway") or "").startswith(CS_PATHWAY):
            continue
        event = _cs_candidate(windows, aid, epoch, dose)
        if event is None:
            row["cs_match"] = "none"
            unmatched += 1
            kind_counts["unmatched"] += 1
            continue

        kind = str(event.get("source_kind") or "unknown")
        source_agent_id = event.get("source_agent_id")
        source_class = _source_class(kind, source_agent_id, host_by_id)
        source_gen = None
        if source_agent_id is not None:
            source_gen = (host_by_id.get(int(source_agent_id)) or {}).get("gen")
        obj = obj_by_id.get(str(event.get("object_id"))) or {}
        row.update({
            "cs_match": "window",
            "cs_event_id": event.get("event_id"),
            "cs_source_kind": kind,
            "cs_source_class": source_class,
            "cs_object_id": event.get("object_id"),
            "cs_source_agent_id": source_agent_id,
            "cs_source_agent_gen": source_gen,
            "cs_per_serving_dose": event.get("per_serving_dose"),
            "cs_zone": event.get("zone"),
            "cs_meal": event.get("meal"),
            "cs_object_source_kind": obj.get("source_kind"),
            "cs_object_end_reason": obj.get("end_reason"),
        })
        kind_counts[kind] += 1
        class_counts[source_class] += 1

    return {
        "ignited": bool(payload.get("ignited")),
        "n_imports": payload.get("n_imports"),
        "n_acquired": payload.get("n_acquired"),
        "acquisitions_by_gen": payload.get("acquisitions_by_gen"),
        "emitting_hosts": len(payload.get("emitting_hosts") or []),
        "emitting_imports": len(payload.get("emitting_imports") or []),
        "hosts": len(hosts),
        "acquisitions": len(acqs),
        "host_gen_counts": dict(Counter(str(h.get("gen")) for h in hosts)),
        "acq_pathway_counts": dict(Counter(_pathway(row) for row in acqs)),
        "symptomatic_hosts_by_pathway": {
            path: len(sym_hosts_by_path[path])
            for path in sorted(sym_hosts_by_path)
        },
        "symptomatic_epochs_by_pathway": {
            path: sym_epochs_by_path[path]
            for path in sorted(sym_epochs_by_path)
        },
        "src_by_pathway": {
            path: dict(stats)
            for path, stats in sorted(path_stats.items())
        },
        "cs_acq_kind_counts": dict(sorted(kind_counts.items())),
        "cs_acq_source_class_counts": dict(sorted(class_counts.items())),
        "cs_acq_unmatched": unmatched,
        "common_source_events": len(events),
        "common_source_objects": len(objects),
        "acquisitions_detail": acqs,
        "wall_clock_s": (payload.get("meta") or {}).get("wall_clock_s"),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--tier", type=str, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--arm", type=str, default=ARM, choices=sorted(witness.ARMS))
    parser.add_argument("--pathogen-id", type=identifier, default="norwalk_gi")
    parser.add_argument(
        "--payload-profile", choices=("full", "lean"), default="full",
    )
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = Path(
        prepare_output_directory(str(args.out), allowed_roots=(str(REPO_ROOT),)),
    )
    manifest = gcc._load_manifest(args.manifest)
    clock = manifest.get("natural_history_clock")
    nhc = str(clock) if clock is not None else None
    specs = witness.tier_specs(args.manifest, args.tier, args.seeds)
    rows = []
    for seed in args.seeds:
        spec = witness._arm_spec(specs[int(seed)], args.arm)
        payload, _voyage, _initiation = gcc.run_seed(
            pathogen_id=args.pathogen_id,
            spec_dict=spec,
            natural_history_clock=nhc,
            payload_profile=args.payload_profile,
        )
        row = summarise_secondary_chain(payload)
        row["seed"] = int(seed)
        row["arm"] = args.arm
        row["payload_profile"] = args.payload_profile
        rows.append(row)
        print(
            f"secondary seed {seed}: acquired {row['n_acquired']}, "
            f"symptomatic pathways {row['symptomatic_hosts_by_pathway']}, "
            f"cs kinds {row['cs_acq_kind_counts']}, "
            f"cs unmatched {row['cs_acq_unmatched']}",
        )
    payload_out = {
        "tier": args.tier,
        "manifest": str(args.manifest),
        "pathogen_id": args.pathogen_id,
        "arm": args.arm,
        "payload_profile": args.payload_profile,
        "rows": rows,
    }
    path = resolve_child_path(
        str(out_dir), f"secondary_chain_{args.tier}.json.gz",
    )
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(payload_out, handle, indent=1, default=str)
    print(f"written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
