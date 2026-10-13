#!/usr/bin/env python3
"""NORO-FOOD-SHAPES-01 fleet scan — one pass over campaign run zips.

Variant of ``food_score_01_scan.py`` carrying the extra census fields the
frozen design (``docs/norovirus/noro_food_shapes_01_sweep_design.md``)
scores: the minted-lot census (object rows, windows covered, titre draws
vs the implicated band), the per-window re-mint witness (distinct titres
per object_id), the declared-extent bookkeeping (per-window servings vs
the minted cap, ``extent_met`` placement), and the early shared-dose
rows of ``early_event_scan.py`` so the D3 conversion read needs no
second pass over the census member.

Summary-side fields are unchanged (posting flag, reported/infection
ARs, route shares, mechanism counters, the common_source override
echo); burst windows and the object-integrity tallies carry over
verbatim.

Reads only; no engine involvement. Resume-safe: ``--resume`` skips keys
already present in the JSONL output.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_source_readout import _cs_fields, _tail_fields  # noqa: E402
from early_event_scan import (  # noqa: E402
    _load_done,
    _load_key_filter,
    _object_rows,
    _v1_rows,
)
from food_score_01_scan import (  # noqa: E402
    _ARM_KEYS,
    _BUCKET_DEFAULT,
    _CENSUS_MEMBER,
    _SUMMARY_MEMBER,
    _acquisition_scan,
    _integrity,
    _list_keys,
    _object_spans,
)
from onset_curve_readout import _burst  # noqa: E402
from outbreak_anchor_readout import (  # noqa: E402
    _cell_label,
    _posted,
    _row_from_summary,
    _s3_client,
    _s3_member_blob,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from simulation_utils.paths import validated_open  # noqa: E402

# Same streaming plan as food_score_01_scan: `hosts[]` (acquisition
# records) is scanned incrementally; only a rolling tail window is
# retained for the trailing `common_source` witness block.
_PREFIX_DEFAULT = "campaign/noro_food_shapes_01/"
_EARLY_EPOCH_DEFAULT = 48
# Implicated census band from the frozen design (Lowther floor /
# Rexin ceiling) — the gate-2 audit bounds every emitted lot-titre
# draw on two_mode arms against it.
_IMPLICATED_BAND = (150.0, 5000.0)


def _lot_object_row(o: dict) -> dict:
    return {
        "oid": o.get("object_id"),
        "e": o.get("seeded_epoch"),
        "end": o.get("end_reason"),
        "w": o.get("windows_covered"),
        "pans": o.get("pans_emitted"),
        "srv": o.get("servings_served"),
        "lot_srv": o.get("lot_servings"),
        "dose": o.get("dose_credited"),
        "titre": o.get("lot_titre_gec_per_g"),
        "ext_mode": o.get("extent_mode"),
        "redraw": o.get("redraw"),
        "ext_win": o.get("extent_windows"),
        "zone": o.get("zone"),
        "item": o.get("item_label"),
    }


def _lot_windows(lot_events: list[dict], lot_obj_ids: set) -> dict:
    """Per-object window map: distinct pan titres + servings per
    (start_epoch, meal) window, restricted to provisioned_lot objects."""
    windows: dict[str, dict] = {}
    for e in lot_events:
        oid = e.get("object_id")
        if oid is None or oid not in lot_obj_ids:
            continue
        entry = windows.setdefault(oid, {"titres": set(), "win": {}})
        entry["titres"].add(round(float(e["lot_titre_gec_per_g"]), 4))
        wkey = (e.get("start_epoch"), e.get("meal"))
        entry["win"][wkey] = entry["win"].get(wkey, 0) + int(
            e.get("servings_taken", 0) or 0
        )
    return windows


def _remint_rows(lot_obj_ids: set, windows: dict) -> list[dict]:
    """Per provisioned_lot object: window count + distinct titre count
    (a constant titre across multi-window objects = re-mint absent)."""
    remint = []
    for oid in sorted(lot_obj_ids):
        entry = windows.get(oid)
        if entry is None:
            remint.append({"oid": oid, "win": 0, "titre_n": 0})
            continue
        remint.append(
            {
                "oid": oid,
                "win": len(entry["win"]),
                "titre_n": len(entry["titres"]),
                "titres": sorted(entry["titres"])[:64],
            }
        )
    return remint


def _extent_rows(objects: list[dict], windows: dict) -> list[dict]:
    """Declared-extent bookkeeping: per-window servings vs the minted
    cap ``lot_servings // extent_windows`` (cap binds every window but
    the last declared, which takes the leftover)."""
    extent = []
    for o in objects:
        if o.get("source_kind") != "provisioned_lot":
            continue
        ew = o.get("extent_windows")
        if ew is None:
            continue
        win_srv = [
            v for _, v in sorted(
                windows.get(o.get("object_id"), {"win": {}})["win"].items(),
                key=lambda kv: (kv[0][0], str(kv[0][1])),
            )
        ]
        cap = int(o.get("lot_servings") or 0) // max(1, int(ew))
        extent.append(
            {
                "oid": o.get("object_id"),
                "ext_win": int(ew),
                "cap": cap,
                "wins": win_srv,
                "cap_viol": sum(1 for s in win_srv[:-1] if cap > 0 and s > cap),
                "extent_met": o.get("end_reason") == "extent_met",
            }
        )
    return extent


def _lot_census(events: list[dict], objects: list[dict]) -> dict:
    """The SHAPES-01 §6/§7.4 census fields for provisioned_lot rows."""
    lot_events = [
        e for e in events if e.get("lot_titre_gec_per_g") is not None
    ]
    titres = [float(e["lot_titre_gec_per_g"]) for e in lot_events]
    lo, hi = _IMPLICATED_BAND
    lot_obj_ids = {
        o.get("object_id")
        for o in objects
        if o.get("source_kind") == "provisioned_lot"
    }
    windows = _lot_windows(lot_events, lot_obj_ids)
    return {
        "lot_objects": [
            _lot_object_row(o)
            for o in objects
            if o.get("source_kind") == "provisioned_lot"
        ],
        "lot_pans": {
            "n": len(lot_events),
            "n_draws": len(titres),
            "titre_min": min(titres) if titres else None,
            "titre_max": max(titres) if titres else None,
            "oob": sum(1 for t in titres if not (lo <= t <= hi)),
        },
        "remint": _remint_rows(lot_obj_ids, windows),
        "extent": _extent_rows(objects, windows),
        "n_obj_events": sum(
            1 for e in events if e.get("object_id") is not None
        ),
    }


def _event_tally(events: list[dict]) -> dict:
    tally = Counter(e.get("source_kind") for e in events)
    return {
        "arms": {k: tally.get(k, 0) for k in _ARM_KEYS},
        "takers_sum": sum(
            int(e.get("servings_taken", 0) or 0) for e in events
        ),
        "zero_dose_events": sum(
            e.get("per_serving_dose") in (None, 0) for e in events
        ),
    }


def _late_max_takers(events: list[dict], early_max: int) -> int:
    return max(
        (
            int(e.get("servings_taken", 0) or 0)
            for e in events
            if (e.get("start_epoch") or e.get("epoch") or 0) > early_max
            or (e.get("start_epoch") or e.get("epoch")) is None
        ),
        default=0,
    )


def _census_side(blob: bytes, num_epochs: int) -> dict:
    acq_all, cs_acq, tail, saw_marker = _acquisition_scan(blob)
    cs_fields = _tail_fields(tail)
    if saw_marker and not any(cs_fields.values()):
        cs_fields = _tail_fields(gzip.decompress(blob))
    telemetry, events, exposures, objects = _cs_fields(cs_fields)
    spans = _object_spans(objects, num_epochs - 1)
    in_span = len(
        [e for e in cs_acq if any(s <= e <= t for s, t in spans)]
    )
    object_ids = {o.get("object_id") for o in objects}
    early_obj, n_late_obj, _ = _object_rows(
        objects, events, _EARLY_EPOCH_DEFAULT
    )
    early_ev, n_late_ev = _v1_rows(
        events, object_ids, _EARLY_EPOCH_DEFAULT
    )
    out = {
        "n_events": len(events),
        **_event_tally(events),
        "n_exposures": len(exposures),
        "telemetry": telemetry,
        "n_objects": len(objects),
        "obj_arms": dict(
            Counter(o.get("source_kind") or "?" for o in objects)
        ),
        "end_reasons": dict(
            Counter(o.get("end_reason") or "?" for o in objects)
        ),
        "obj_pans_sum": sum(
            int(o.get("pans_emitted", 0) or 0) for o in objects
        ),
        "obj_windows_sum": sum(
            int(o.get("windows_covered", 0) or 0) for o in objects
        ),
        "lot_obj_voyage": any(
            o.get("source_kind") == "provisioned_lot" for o in objects
        ),
        "lot_event_voyage": any(
            e.get("lot_titre_gec_per_g") is not None
            and e.get("object_id") is None
            for e in events
        ),
        "integrity": _integrity(events, objects),
        "n_acq": len(acq_all),
        "cs_acq_n": len(cs_acq),
        "cs_acq_in_span": in_span,
        "saw_cs": saw_marker,
        "early": early_obj + early_ev,
        "n_early_obj": len(early_obj),
        "n_early_ev": len(early_ev),
        "n_late_obj": n_late_obj,
        "n_late_ev": n_late_ev,
        "max_early_takers": max(
            (r["t"] for r in early_obj + early_ev), default=0
        ),
        "max_late_ev_takers": _late_max_takers(
            events, _EARLY_EPOCH_DEFAULT
        ),
    }
    out.update(_lot_census(events, objects))
    for w in (48, 24, 12, 6):
        share, centre = _burst(acq_all, w)
        out[f"burst{w}"] = round(share, 4)
        if w == 48:
            out["burst48_centre"] = centre
    return out


def _fetch(client, bucket: str, key: str, census: bool) -> dict | None:
    try:
        blob = _s3_member_blob(client, bucket, key, _SUMMARY_MEMBER)
        if blob is None:
            return {"key": key, "error": "no summary member"}
        summary = json.loads(blob)
        base = _row_from_summary(summary, key.rsplit("/", 1)[-1])
    except Exception as exc:  # noqa: BLE001 — per-voyage isolation
        return {"key": key, "error": f"summary: {exc}"}
    params = summary.get("parameters", {})
    body = summary.get("summary", {})
    mech = summary.get("mechanisms", {})
    cs_echo = (
        (params.get("transmission") or {}).get("common_source")
        or params.get("common_source")
        or {}
    )
    anchor = base["anchor_row"]
    row = {
        "key": key,
        "seed": base["seed"],
        "cell": _cell_label(tuple(base["cell_key"])),
        "hull": anchor["hull"],
        "posted": _posted(anchor),
        "rep_pax_ar": anchor["reported_case_attack_rate_passenger"],
        "rep_crew_ar": anchor["reported_case_attack_rate_crew"],
        "inf_ar_pax": anchor["infection_attack_rate_passenger"],
        "inf_ar_crew": anchor["infection_attack_rate_crew"],
        "ever_ill_pax": anchor["A1_ever_ill_passenger"],
        "rep_pax_n": body.get("cumulative_reported_cases_passenger"),
        "rep_crew_n": body.get("cumulative_reported_cases_crew"),
        "pax_comp": anchor["passenger_complement"],
        "crew_comp": anchor["crew_complement"],
        "n_acquired": base["n_acquired"],
        "n_imports": base["n_imports"],
        "ignited": base["ignited"],
        "vsp_trigger": base["vsp_trigger_epoch"] is not None,
        "peak_prevalence": base["peak_prevalence"],
        "routes": body.get("infections_by_dominant_route") or {},
        "dose_share": body.get("infection_dose_share_by_route") or {},
        "cs_events_summary": int(mech.get("common_source_events", 0) or 0),
        "cs_takers_summary": int(mech.get("common_source_takers", 0) or 0),
        "cs_echo": cs_echo,
        "cs_sha_echo": params.get("engine_git_sha"),
        "num_epochs": int(params.get("num_epochs", 0) or 0),
    }
    if not census:
        row["census"] = None
        return row
    try:
        blob = _s3_member_blob(client, bucket, key, _CENSUS_MEMBER)
        if blob is None:
            row["census"] = {"error": "no census member"}
            return row
        row["census"] = _census_side(blob, row["num_epochs"])
    except Exception as exc:  # noqa: BLE001 — per-voyage isolation
        row["census"] = {"error": str(exc)}
    return row


def _run_prefix(
    client, bucket: str, prefix: str, args, done: set[str], fh
) -> tuple[int, int]:
    keys = [
        k
        for k in _list_keys(client, bucket, prefix)
        if k not in done
    ]
    if args.keys_set is not None:
        keys = [k for k in keys if k in args.keys_set]
    if not keys:
        return 0, 0
    n_rows = 0
    n_err = 0
    with ThreadPoolExecutor(args.workers) as pool:
        futs = {
            pool.submit(
                _fetch, client, bucket, k, not args.no_census
            ): k
            for k in keys
        }
        for i, fut in enumerate(as_completed(futs), 1):
            row = fut.result()
            if row is None:
                continue
            fh.write(json.dumps(row) + "\n")
            n_rows += 1
            if row.get("error") or (row.get("census") or {}).get("error"):
                n_err += 1
            if i % 200 == 0:
                fh.flush()
                print(
                    f"  {prefix}: {i}/{len(keys)} ({n_err} errors)",
                    file=sys.stderr,
                )
    fh.flush()
    return n_rows, n_err


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bucket", default=_BUCKET_DEFAULT)
    ap.add_argument(
        "--prefix", action="append", dest="prefixes",
        help="s3:// URI or bucket-relative prefix; repeatable",
    )
    ap.add_argument(
        "--keys", metavar="FILE",
        help="file of explicit S3 keys to scan (one per line)",
    )
    ap.add_argument("--no-census", action="store_true",
                    help="summary.json only — posting outcome, no census")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--out", required=True, help="JSONL rows output")
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    args.keys_set = _load_key_filter(args.keys)
    prefixes = [
        p[len("s3://") + len(args.bucket) + 1:] if p.startswith("s3://")
        else p
        for p in (args.prefixes or [_PREFIX_DEFAULT])
    ]
    client = _s3_client()
    out_path = Path(args.out)
    with validated_open(
        str(out_path),
        "a",
        encoding="utf-8",
        allowed_roots=(str(out_path.parent.resolve()),),
    ) as fh:
        done = _load_done(out_path, args.resume)
        for p in prefixes:
            tier_prefix = p.rstrip("/") + "/"
            rows, errs = _run_prefix(
                client, args.bucket, tier_prefix, args, done, fh
            )
            print(f"{tier_prefix}: {rows} rows, {errs} errors",
                  file=sys.stderr)


if __name__ == "__main__":
    main()
