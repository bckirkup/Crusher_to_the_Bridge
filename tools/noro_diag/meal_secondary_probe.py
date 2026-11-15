#!/usr/bin/env python3
"""Same-span secondary-transmission probe for provisioned-lot common-source pans.

Runs posted ``carriers_ordered`` cells under ``growth_chain_census`` with the
full payload and buckets secondary (non-``common_source_food``) acquisitions plus
acquired-source exposure proxies by whether they occur before quarantine,
after quarantine but still inside the provisioned-lot span, or after that span.

The payload profile is fixed to ``full`` because ``lean`` drops the pickup,
hazard, contact, food and unit-epoch row streams this probe reads.
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
BUCKETS = ("before_cs", "cs_span_pre_q", "cs_span_post_q", "after_cs")


def _f(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _pathway(row: dict[str, Any]) -> str:
    return str(row.get("dominant_pathway") or row.get("pathway") or "").split(":", 1)[0]


def _first_epochs(voyage: dict[str, Any] | None) -> tuple[int | None, int | None]:
    series = (voyage or {}).get("timeseries") or []
    first_sym = next(
        (int(r.get("epoch")) for r in series if _f(r.get("symptomatic")) > 0.0),
        None,
    )
    first_q = next(
        (int(r.get("epoch")) for r in series if _f(r.get("quarantined")) > 0.0),
        None,
    )
    return first_sym, first_q


def _bucket(
    epoch: int | None,
    cs_start: int | None,
    cs_end: int | None,
    first_q: int | None,
) -> str:
    if epoch is None or cs_start is None or cs_end is None:
        return "unknown"
    if epoch < cs_start:
        return "before_cs"
    if epoch > cs_end:
        return "after_cs"
    quarantine_epoch = first_q if first_q is not None else cs_end + 1
    return "cs_span_pre_q" if epoch < quarantine_epoch else "cs_span_post_q"


def _hazard_summary(
    payload: dict[str, Any],
    acq_by_ep_agent: dict[tuple[int, int], list[str]],
    bucket_of: Any,
) -> dict[str, Any]:
    hz: Counter = Counter()
    hz_dose: Counter = Counter()
    hz_haz: Counter = Counter()
    for row in payload.get("hazards") or []:
        epoch = row.get("epoch")
        epoch = int(epoch) if epoch is not None else None
        bucket = bucket_of(epoch)
        agent_id = int(row.get("agent_id") or -1)
        paths = acq_by_ep_agent.get((epoch, agent_id), []) if epoch is not None else []
        if CS_PATHWAY in paths:
            cls = "cs_conversion"
        elif paths:
            cls = "secondary_conversion"
        else:
            cls = "exposed_no_acq"
        key = (bucket, cls)
        hz[key] += 1
        hz_dose[key] += _f(row.get("effective_dose"))
        hz_haz[key] += _f(row.get("hazard"))
    return {
        f"{bucket}|{cls}": {
            "n": hz[(bucket, cls)],
            "dose": hz_dose[(bucket, cls)],
            "haz": hz_haz[(bucket, cls)],
        }
        for bucket, cls in hz
    }


def _pickup_summary(payload: dict[str, Any], bucket_of: Any) -> tuple[dict[str, Any], dict[str, float]]:
    pk: Counter = Counter()
    pk_dose: Counter = Counter()
    pk_delivered: Counter = Counter()
    pk_targets: dict[tuple[str, str], set[int]] = defaultdict(set)
    pk_acquired_dose: Counter = Counter()
    for row in payload.get("pickups") or []:
        if not row.get("challengeable"):
            continue
        epoch = int(row.get("epoch") or 0)
        bucket = bucket_of(epoch)
        kind = "acquired" if _f(row.get("source_acquired_share")) > 0.0 else "other"
        key = (bucket, kind)
        target = int(row.get("target") or row.get("agent_id") or -1)
        pk[key] += 1
        pk_dose[key] += _f(row.get("dose"))
        pk_delivered[key] += _f(row.get("delivered"))
        pk_targets[key].add(target)
        if kind == "acquired":
            pk_acquired_dose[bucket] += _f(row.get("dose"))
    pickups = {
        f"{bucket}|{kind}": {
            "n": pk[(bucket, kind)],
            "dose": pk_dose[(bucket, kind)],
            "delivered": pk_delivered[(bucket, kind)],
            "targets": len(pk_targets[(bucket, kind)]),
        }
        for bucket, kind in pk
    }
    acquired = {
        bucket: pk_acquired_dose.get(bucket, 0.0)
        for bucket in sorted({bucket for bucket, _kind in pk})
    }
    return pickups, acquired


def _contact_summary(payload: dict[str, Any], first_cs_epoch: dict[int, int], bucket_of: Any) -> dict[str, Any]:
    ct: Counter = Counter()
    ct_dose: Counter = Counter()
    ct_targets: dict[str, set[int]] = defaultdict(set)
    ct_donor_cs: Counter = Counter()
    for row in payload.get("hand_contacts") or []:
        epoch = int(row.get("epoch") or 0)
        bucket = bucket_of(epoch)
        donor = int(row.get("donor") or -1)
        target = int(row.get("target") or -1)
        ct[bucket] += 1
        ct_dose[bucket] += _f(row.get("dose"))
        ct_targets[bucket].add(target)
        if donor in first_cs_epoch and first_cs_epoch[donor] < epoch:
            ct_donor_cs[bucket] += 1
    return {
        bucket: {
            "n": ct[bucket],
            "dose": ct_dose[bucket],
            "targets": len(ct_targets[bucket]),
            "donor_cs_earlier": ct_donor_cs[bucket],
        }
        for bucket in ct
    }


def _unit_food_summary(payload: dict[str, Any], bucket_of: Any) -> tuple[dict[str, Any], dict[str, int]]:
    ue_mass: Counter = Counter()
    ue_units: dict[str, set[str]] = defaultdict(set)
    food_rows: Counter = Counter()
    for row in payload.get("unit_epochs") or []:
        mass = _f(row.get("mass_acquired"))
        if mass <= 0.0:
            continue
        bucket = bucket_of(int(row.get("epoch") or 0))
        ue_mass[bucket] += mass
        ue_units[bucket].add(str(row.get("unit")))
    for row in payload.get("food_venues") or []:
        if _f(row.get("source_acquired_share")) > 0.0:
            food_rows[bucket_of(int(row.get("epoch") or 0))] += 1
    unit_mass = {
        bucket: {"mass": ue_mass[bucket], "units": len(ue_units[bucket])}
        for bucket in ue_mass
    }
    return unit_mass, dict(food_rows)


def _secondary_acquisitions(
    acquisitions: list[dict[str, Any]],
    bucket_of: Any,
) -> dict[str, int]:
    counts: Counter = Counter()
    for row in acquisitions:
        pathway = _pathway(row)
        if not pathway or pathway == CS_PATHWAY:
            continue
        epoch = row.get("epoch")
        if epoch is None:
            continue
        counts[f"{bucket_of(int(epoch))}|{pathway}"] += 1
    return dict(counts)


def summarise_meal_secondary(payload: dict[str, Any], voyage: dict[str, Any]) -> dict[str, Any]:
    """Compact per-seed row for the same-span secondary-transmission read."""
    cs = payload.get("common_source") or {}
    events = cs.get("events") or []
    prov = [e for e in events if e.get("source_kind") == "provisioned_lot"]
    cs_start = min((int(e.get("start_epoch") or 0) for e in prov), default=None)
    cs_end = max((int(e.get("end_epoch") or 0) for e in prov), default=None)
    first_sym, first_q = _first_epochs(voyage)

    def bucket_of(epoch: int | None) -> str:
        return _bucket(epoch, cs_start, cs_end, first_q)

    acquisitions = payload.get("acquisitions") or []
    acq_by_ep_agent: dict[tuple[int, int], list[str]] = defaultdict(list)
    first_cs_epoch: dict[int, int] = {}
    for row in acquisitions:
        epoch = row.get("epoch")
        agent_id = row.get("agent_id")
        if epoch is None or agent_id is None:
            continue
        epoch_i = int(epoch)
        agent_i = int(agent_id)
        pathway = _pathway(row)
        acq_by_ep_agent[(epoch_i, agent_i)].append(pathway)
        if pathway == CS_PATHWAY:
            first_cs_epoch[agent_i] = min(first_cs_epoch.get(agent_i, 10**9), epoch_i)

    pickups, pickup_acquired_dose = _pickup_summary(payload, bucket_of)
    contacts = _contact_summary(payload, first_cs_epoch, bucket_of)
    unit_mass, food_rows = _unit_food_summary(payload, bucket_of)
    return {
        "cs_start": cs_start,
        "cs_end": cs_end,
        "first_sym": first_sym,
        "first_q": first_q,
        "n_events": len(events),
        "n_prov_events": len(prov),
        "n_acquisitions": len(acquisitions),
        "n_hazards": len(payload.get("hazards") or []),
        "n_pickups": len(payload.get("pickups") or []),
        "n_contacts": len(payload.get("hand_contacts") or []),
        "n_unit_epochs": len(payload.get("unit_epochs") or []),
        "n_food_venues": len(payload.get("food_venues") or []),
        "hazard": _hazard_summary(payload, acq_by_ep_agent, bucket_of),
        "pickups": pickups,
        "pickup_acquired_dose": pickup_acquired_dose,
        "contacts": contacts,
        "secondary_acquisitions": _secondary_acquisitions(acquisitions, bucket_of),
        "unit_acquired_mass": unit_mass,
        "food_acquired_rows": food_rows,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--tier", type=str, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--arm", type=str, default=ARM, choices=sorted(witness.ARMS))
    parser.add_argument("--pathogen-id", type=identifier, default="norwalk_gi")
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
        payload, voyage, _initiation = gcc.run_seed(
            pathogen_id=args.pathogen_id,
            spec_dict=spec,
            natural_history_clock=nhc,
            payload_profile="full",
        )
        row = summarise_meal_secondary(payload, voyage)
        row["seed"] = int(seed)
        row["arm"] = args.arm
        row["payload_profile"] = "full"
        rows.append(row)
        sec = row["secondary_acquisitions"]
        print(
            f"meal-secondary seed {seed}: cs {row['cs_start']}-{row['cs_end']}, "
            f"secondary acquisitions {sec}",
        )
    payload_out = {
        "tier": args.tier,
        "manifest": str(args.manifest),
        "pathogen_id": args.pathogen_id,
        "arm": args.arm,
        "payload_profile": "full",
        "rows": rows,
    }
    path = resolve_child_path(str(out_dir), f"meal_secondary_{args.tier}.json.gz")
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(payload_out, handle, indent=1, default=str)
    print(f"written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
