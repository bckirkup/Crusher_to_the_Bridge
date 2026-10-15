#!/usr/bin/env python3
"""NORO-HULL-SCALE-01 posting-chain census scan.

Emits one JSONL row per voyage carrying the full common-source posting
chain the decomposition needs:

    object minted -> pans served / diners covered -> cases generated
    -> reported -> posted (3% A9 wire).

The summary side is a ranged S3 read of summary.json (~30 KB); the census
side streams growth_census.json.gz through the rolling-tail decode from
early_event_scan (never materialises the ~400-800 MB full document).

Distinct-diner coverage is measurable because each event row carries
``taker_ids`` — the served agent ids for that pan. Distinct diners per
object = len(union of taker_ids over the object's events); the same
diner taking from several pans of one lot counts once.

Usage::

    python3 tools/noro_diag/hull_scale_01_scan.py \
        --prefix fl_spr_12d_scr_mint --prefix fl_spr_12d_scr_ind \
        --limit 400 --workers 8 --out rows.jsonl --resume
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common_source_readout import (  # noqa: E402
    _BUCKET_DEFAULT,
    _cs_fields,
    _list_keys,
    _tail_fields,
)
from early_event_scan import _tail_decompress  # noqa: E402
from outbreak_anchor_readout import (  # noqa: E402
    A9_POSTING_THRESHOLD,
    _posted,
    _row_from_summary,
    _s3_client,
    _s3_member_blob,
)

_PREFIX_ROOT = "campaign/noro_food_shapes_01/"
_SUMMARY_MEMBER = "summary.json"
_CENSUS_MEMBER = "growth_census.json.gz"


def _load_done(out_path: Path) -> set[str]:
    done: set[str] = set()
    if out_path.exists():
        with open(out_path) as f:  # NOSONAR -- operator-specified resume path in a local diagnostic tool
            for line in f:
                try:
                    done.add(json.loads(line)["key"])
                except Exception:
                    # skip truncated/partial resume lines
                    pass
    return done


def _object_rows_all(objects: list[dict],
                     events: list[dict]) -> list[dict]:
    """One row per cs object (all arms), with linked pans/diners."""
    diners: dict[str, set] = {}
    pan_takers: dict[str, list[int]] = {}
    take_fracs: dict[str, list[float]] = {}
    doses: dict[str, list[float]] = {}
    for e in events:
        oid = e.get("object_id")
        if oid is not None:
            taken = int(e.get("servings_taken", 0) or 0)
            pan_takers.setdefault(oid, []).append(taken)
            diners.setdefault(oid, set()).update(
                e.get("taker_ids") or ())
            cohort = int(e.get("cohort_size", 0) or 0)
            if cohort:
                take_fracs.setdefault(oid, []).append(taken / cohort)
            dose = e.get("per_serving_dose")
            if dose is not None:
                doses.setdefault(oid, []).append(float(dose))
    rows = []
    for o in objects:
        oid = o.get("object_id")
        linked = pan_takers.get(oid, [])
        rows.append({
            "oid": oid,
            "arm": o.get("source_kind"),
            "seeded_epoch": o.get("seeded_epoch"),
            "end_reason": o.get("end_reason"),
            "zone": o.get("zone"),
            "item": o.get("item_label"),
            "servings_served": int(o.get("servings_served") or 0),
            "dose_credited": o.get("dose_credited"),
            "windows_covered": o.get("windows_covered"),
            "n_pans": len(linked),
            "takers": sum(linked),
            "diners": len(diners.get(oid, set())),
            "pw_max": max(linked, default=0),
            "take_frac_med": (
                sorted(take_fracs[oid])[len(take_fracs[oid]) // 2]
                if take_fracs.get(oid) else None),
            "dose_per_serving": (
                max(doses[oid]) if doses.get(oid) else None),
            "lot_servings": o.get("lot_servings"),
            "lot_titre": o.get("lot_titre_gec_per_g"),
        })
    return rows


def _fetch(client, bucket: str, key: str) -> dict:
    row: dict = {"key": key}
    blob = _s3_member_blob(client, bucket, key, _SUMMARY_MEMBER)
    if blob is None:
        row["error"] = "no_summary"
        return row
    summary = json.loads(blob)
    base = _row_from_summary(summary, key.rsplit("/", 1)[-1])
    anchor = base["anchor_row"]
    body = summary.get("summary", {})
    mech = summary.get("mechanisms", {})
    routes = body.get("infections_by_dominant_route") or {}
    row.update({
        "seed": base["seed"],
        "hull": anchor["hull"],
        "num_epochs": int(summary.get("parameters", {}).get("num_epochs") or 0),
        "posted": _posted(anchor),
        "rep_pax_ar": anchor["reported_case_attack_rate_passenger"],
        "rep_crew_ar": anchor["reported_case_attack_rate_crew"],
        "rep_pax_n": body.get("cumulative_reported_cases_passenger"),
        "rep_crew_n": body.get("cumulative_reported_cases_crew"),
        "pax_comp": anchor["passenger_complement"],
        "crew_comp": anchor["crew_complement"],
        "reach": round(
            max(anchor["reported_case_attack_rate_passenger"],
                anchor["reported_case_attack_rate_crew"])
            / A9_POSTING_THRESHOLD, 4),
        "inf_ar_pax": anchor["infection_attack_rate_passenger"],
        "ever_ill_pax": body.get("cumulative_ever_ill_passenger"),
        "ever_ill_crew": body.get("cumulative_ever_ill_crew"),
        "n_acquired": base["n_acquired"],
        "n_imports": base["n_imports"],
        "cs_food_inf": int(routes.get("common_source_food", 0) or 0),
        "cs_events_summary": int(mech.get("common_source_events", 0) or 0),
        "cs_takers_summary": int(mech.get("common_source_takers", 0) or 0),
    })
    blob = _s3_member_blob(client, bucket, key, _CENSUS_MEMBER)
    if blob is None:
        row["census_error"] = "no_census"
        return row
    tail, saw_cs, _saw_em, _n_emit = _tail_decompress(blob)
    cs_fields = _tail_fields(tail)
    if saw_cs and "common_source" not in cs_fields:
        cs_fields = _tail_fields(gzip.decompress(blob))
    _tel, events, _exposures, objects = _cs_fields(cs_fields)
    objs = _object_rows_all(objects, events)
    lot = [o for o in objs if o["arm"] == "provisioned_lot"]
    v1 = [e for e in events if e.get("object_id") is None]
    all_diners: set = set()
    for e in events:
        all_diners.update(e.get("taker_ids") or ())
    row.update({
        "minted": bool(lot),
        "n_objects": len(objects),
        "lot_objects": lot,
        "obj_arms": {a: sum(1 for o in objs if o["arm"] == a)
                     for a in ("provisioned_lot", "ill_handler", "ill_diner")},
        "n_events": len(events),
        "n_v1_events": len(v1),
        "ev_takers_sum": sum(int(e.get("servings_taken", 0) or 0)
                             for e in events),
        "v1_takers_sum": sum(int(e.get("servings_taken", 0) or 0)
                             for e in v1),
        "max_ev_takers": max((int(e.get("servings_taken", 0) or 0)
                              for e in events), default=0),
        "distinct_diners": len(all_diners),
        "v1_diners": len({t for e in v1
                          for t in (e.get("taker_ids") or ())}),
        "lot_diners": sum(o["diners"] for o in lot),
        "census_error": None,
    })
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bucket", default=_BUCKET_DEFAULT)
    ap.add_argument("--prefix", action="append", dest="prefixes",
                    required=True)
    ap.add_argument("--limit", type=int, default=0,
                    help="first N keys per prefix (0 = all)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", required=True)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    out = Path(args.out)
    done = _load_done(out) if args.resume else set()
    client = _s3_client()
    keys: list[str] = []
    for p in args.prefixes:
        pref = p if p.startswith(_PREFIX_ROOT) else _PREFIX_ROOT + p.rstrip("/") + "/"
        ks = _list_keys(client, args.bucket, pref)
        if args.limit:
            ks = ks[: args.limit]
        keys.extend(k for k in ks if k not in done)
    print(f"{len(keys)} cells to scan", flush=True)
    n = 0
    with open(out, "a") as fh, ThreadPoolExecutor(  # NOSONAR -- operator-specified output path in a local diagnostic tool
            max_workers=args.workers) as ex:
        futs = {ex.submit(_fetch, client, args.bucket, k): k for k in keys}
        for fut in as_completed(futs):
            r = fut.result()
            fh.write(json.dumps(r, default=str) + "\n")
            fh.flush()
            n += 1
            if n % 50 == 0:
                print(f"{n}/{len(keys)}", flush=True)
    print("done", n, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
