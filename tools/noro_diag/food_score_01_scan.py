#!/usr/bin/env python3
"""NORO-FOOD-SCORE-01 fleet scan — one pass over campaign run zips.

Emits one JSONL row per voyage with everything the scored readout needs:

- summary-level fields (posting flag, reported/infection ARs, route
  shares, mechanism counters, the common_source override echo) — cheap
  ranged reads on ``summary.json``;
- census-level fields when the census member is scanned (object witness:
  objects/events/takers/zero-dose/end_reason mix, object spans for the
  window-aligned acquisition share, per-voyage acquisition epochs for
  burst48/burst12, and the object-integrity tallies the design freezes).

``--census-limit N`` scans the census member on only the first N sorted
keys per tier (zero-witness spot checks on ``off``/``ind`` blocks);
``0`` scans every key. ``--summary-only`` skips the census entirely.

Reads only; no engine involvement. Resume-safe: ``--resume`` skips keys
already present in the JSONL output.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
import zlib
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_source_readout import _cs_fields, _tail_fields  # noqa: E402
from onset_curve_readout import _burst, _census_prefix  # noqa: E402
from outbreak_anchor_readout import (  # noqa: E402
    _cell_label,
    _posted,
    _row_from_summary,
    _s3_client,
    _s3_member_blob,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from simulation_utils.paths import validated_open  # noqa: E402

# Stream the gzip member: `hosts[]` (acquisition records) is scanned
# incrementally so the full decompressed text never materialises; only a
# rolling tail window is retained for the trailing `common_source` block.
# Big-hull zips decompress to ~0.8 GB — a whole-document decode OOM-killed
# multi-worker scans on small boxes.
_TAIL_WINDOW = 32 << 20
_CHUNK = 4 << 20
_ACQ_OVERLAP = 4096

_BUCKET_DEFAULT = "crusherbucket-994254241749-us-east-1-an"
_PREFIX_DEFAULT = "campaign/noro_food_score_01/"
_SUMMARY_MEMBER = "summary.json"
_CENSUS_MEMBER = "growth_census.json.gz"
_CS_PATHWAY_PREFIX = "common_source_food"
# Two-phase acquisition scan: find the epoch, then bound the pathway
# search at the record's closing `}` — the same "same-object" semantics as
# a `[^}]*` bridge but with no lazy-bridge backtracking (Sonar S8786).
_ACQ_EPOCH_RE = re.compile(rb'"epoch_acquired":\s*(-?\d+)')
_ACQ_PATH_RE = re.compile(rb'"dominant_pathway":\s*"([^"]+)"')


def _acq_epochs(buf: bytes, acq_all: list[int], cs_acq: list[int]) -> None:
    for m in _ACQ_EPOCH_RE.finditer(buf):
        epoch = int(m.group(1))
        if epoch <= 0:
            continue
        end = buf.find(b"}", m.end())
        window = buf[m.end() : end if end > 0 else len(buf)]
        pm = _ACQ_PATH_RE.search(window)
        acq_all.append(epoch)
        if pm and pm.group(1).startswith(_CS_PATHWAY_PREFIX.encode()):
            cs_acq.append(epoch)


_ARM_KEYS = ("provisioned_lot", "ill_handler", "ill_diner")


def _list_keys(client, bucket: str, prefix: str) -> list[str]:
    keys: list[str] = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(".zip"):
                keys.append(obj["Key"])
    return sorted(keys)


def _object_spans(objects: list[dict], last_epoch: int) -> list[list[int]]:
    spans = []
    for o in objects:
        start = o.get("seeded_epoch")
        if start is None:
            continue
        end = o.get("exhausted_epoch")
        spans.append([int(start), int(end) if end is not None else last_epoch])
    return spans


def _integrity(events: list[dict], objects: list[dict]) -> dict:
    ids = {o.get("object_id") for o in objects}
    unresolved = sum(
        1
        for e in events
        if e.get("object_id") is not None and e.get("object_id") not in ids
    )
    missing_oid = sum(1 for e in events if e.get("object_id") is None)
    missing_serial = sum(1 for e in events if e.get("pan_serial") is None)
    open_objects = sum(
        1
        for o in objects
        if o.get("end_reason") is None
        or o.get("pans_emitted") is None
        or o.get("windows_covered") is None
    )
    srv_exceed = sum(
        1
        for o in objects
        if o.get("lot_servings") is not None
        and int(o.get("servings_served") or 0)
        > int(o["lot_servings"])
    )
    non_noro = sum(
        1 for o in objects if o.get("pathogen_id") != "norwalk_gi"
    )
    return {
        "ev_rows": len(events),
        "ev_missing_oid": missing_oid,
        "ev_missing_serial": missing_serial,
        "ev_unresolved_oid": unresolved,
        "obj_open": open_objects,
        "lot_srv_exceeds": srv_exceed,
        "non_noro_objects": non_noro,
    }


def _acquisition_scan(
    blob: bytes,
) -> tuple[list[int], list[int], bytes, bool]:
    """Stream-decompress the census member once.

    Returns (all onboard acquisition epochs, cs-route acquisition epochs,
    rolling tail window, saw-cs-marker) — the acquisition regex runs per
    chunk on a small overlap, and the tail window keeps the trailing
    `common_source` block for the tail-decode. Baseline arms emit no
    `common_source` block at all, so the marker flag is what tells a
    legitimately empty witness from a window that ran short.
    """
    dec = zlib.decompressobj(16 + zlib.MAX_WBITS)
    acq_all: list[int] = []
    cs_acq: list[int] = []
    prev = b""
    tail = b""
    saw_marker = False
    # exact key with colon — `common_source_food` pathway strings inside
    # host rows must not trip this (ind arms have cs acquisitions but the
    # witness block itself may be absent)
    marker = b'"common_source":'
    for i in range(0, len(blob), _CHUNK):
        part = dec.decompress(blob[i : i + _CHUNK])
        buf = prev + part
        saw_marker = saw_marker or marker in buf
        _acq_epochs(buf, acq_all, cs_acq)
        prev = buf[-_ACQ_OVERLAP:]
        tail = (tail + part)[-_TAIL_WINDOW:]
    tail = (tail + dec.flush())[-_TAIL_WINDOW:]
    return acq_all, cs_acq, tail, saw_marker


def _head_side(client, bucket: str, key: str) -> dict:
    """Head-only census: acquisition epochs + bursts from the `hosts[]`
    prefix of the census member (~6 MB ranged read vs an 84 MB member).
    No witness block — objects/events live in the member tail.
    """
    text = _census_prefix(client, bucket, key)
    if not text:
        return {"head_only": True, "error": "no census head"}
    text = text.encode("utf-8")
    acq_all: list[int] = []
    cs_acq: list[int] = []
    _acq_epochs(text, acq_all, cs_acq)
    out = {
        "head_only": True,
        "n_acq": len(acq_all),
        "cs_acq_n": len(cs_acq),
    }
    for w in (48, 24, 12, 6):
        share, centre = _burst(acq_all, w)
        out[f"burst{w}"] = round(share, 4)
        if w == 48:
            out["burst48_centre"] = centre
    return out


def _census_side(blob: bytes, num_epochs: int) -> dict:
    acq_all, cs_acq, tail, saw_marker = _acquisition_scan(blob)
    cs_fields = _tail_fields(tail)
    if saw_marker and not any(cs_fields.values()):
        # Marker seen but the block's start fell outside the tail window
        # (huge exposure lists) — full-decode fallback for this zip.
        cs_fields = _tail_fields(gzip.decompress(blob))
    telemetry, events, exposures, objects = _cs_fields(cs_fields)
    arms = dict.fromkeys(_ARM_KEYS, 0)
    takers_sum = 0
    zero_dose = 0
    for e in events:
        kind = e.get("source_kind")
        if kind in arms:
            arms[kind] += 1
        takers_sum += int(e.get("servings_taken", 0) or 0)
        if not e.get("per_serving_dose"):
            zero_dose += 1
    spans = _object_spans(objects, num_epochs - 1)
    in_span = sum(
        1
        for e in cs_acq
        if any(s <= e <= t for s, t in spans)
    )
    out = {
        "n_events": len(events),
        "arms": arms,
        "takers_sum": takers_sum,
        "zero_dose_events": zero_dose,
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
        "integrity": _integrity(events, objects),
        "n_acq": len(acq_all),
        "cs_acq_n": len(cs_acq),
        "cs_acq_in_span": in_span,
    }
    for w in (48, 24, 12, 6):
        share, centre = _burst(acq_all, w)
        out[f"burst{w}"] = round(share, 4)
        if w == 48:
            out["burst48_centre"] = centre
    return out


def _fetch(client, bucket: str, key: str, census: str) -> dict | None:
    try:
        blob = _s3_member_blob(client, bucket, key, _SUMMARY_MEMBER)
        if blob is None:
            return {"key": key, "error": "no summary member"}
        summary = json.loads(blob)
    except Exception as exc:  # noqa: BLE001 — per-voyage isolation
        return {"key": key, "error": f"summary: {exc}"}
    base = _row_from_summary(summary, key.rsplit("/", 1)[-1])
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
        "num_epochs": int(params.get("num_epochs", 0) or 0),
    }
    if census == "none":
        row["census"] = None
        return row
    if census == "head":
        try:
            row["census"] = _head_side(client, bucket, key)
        except Exception as exc:  # noqa: BLE001 — per-voyage isolation
            row["census"] = {"error": str(exc)}
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


def _tier_keys(
    client, bucket: str, prefix: str, args, done: set[str],
) -> list[str]:
    keys = _list_keys(client, bucket, prefix)
    if args.keys_set is not None:
        keys = [k for k in keys if k in args.keys_set]
    return [k for k in keys if k not in done]


def _mode_fn(args, census_keys: set[str]):
    def _mode(k: str) -> str:
        if args.head_set is not None or args.full_set is not None:
            if args.full_set and k in args.full_set:
                return "full"
            if args.head_set and k in args.head_set:
                return "head"
            return "none"
        return "full" if k in census_keys else "none"
    return _mode


def _run_tier(
    client, bucket: str, prefix: str, args, done: set[str], fh,
) -> tuple[int, int]:
    keys = _tier_keys(client, bucket, prefix, args, done)
    if not keys:
        return 0, 0
    if args.no_census:
        census_keys: set[str] = set()
    else:
        n_census = len(keys) if args.census_limit <= 0 else min(
            args.census_limit, len(keys)
        )
        census_keys = set(keys[:n_census])
    mode = _mode_fn(args, census_keys)
    n_rows = 0
    n_err = 0

    with ThreadPoolExecutor(args.workers) as pool:
        futs = {
            pool.submit(_fetch, client, bucket, k, mode(k)): k
            for k in keys
        }
        for i, fut in enumerate(as_completed(futs), 1):
            row = fut.result()
            if row is None:
                continue
            fh.write(json.dumps(row) + "\n")
            n_rows += 1
            if row.get("error"):
                n_err += 1
            if i % 200 == 0:
                fh.flush()
                print(
                    f"  {prefix}: {i}/{len(keys)} "
                    f"({n_err} errors)",
                    file=sys.stderr,
                )
    fh.flush()
    return n_rows, n_err


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bucket", default=_BUCKET_DEFAULT)
    ap.add_argument("--prefix", action="append", dest="prefixes",
                    help="s3:// URI or bucket-relative prefix; repeatable")
    ap.add_argument("--census-limit", type=int, default=0,
                    help="census-scan first N keys per tier; 0 = all")
    ap.add_argument("--no-census", action="store_true",
                    help="summary.json only — no census member reads")
    ap.add_argument("--keys", metavar="FILE",
                    help="file of explicit S3 keys to scan (one per line)")
    ap.add_argument("--head-keys", metavar="FILE",
                    help="file of keys to head-census (bursts only)")
    ap.add_argument("--full-keys", metavar="FILE",
                    help="file of keys to full-census (witness + bursts)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", required=True, help="JSONL rows output")
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    prefixes = [
        p[len("s3://") + len(args.bucket) + 1:] if p.startswith("s3://")
        else p
        for p in (args.prefixes or [_PREFIX_DEFAULT])
    ]
    client = _s3_client()
    bucket = args.bucket
    for attr, flag in (
        ("keys_set", args.keys),
        ("head_set", args.head_keys),
        ("full_set", args.full_keys),
    ):
        setattr(args, attr, None)
        if flag:
            with validated_open(
                str(flag), encoding="utf-8",
                allowed_roots=(str(Path(flag).resolve().parent),),
            ) as kf:
                setattr(args, attr, {
                    ln.strip() for ln in kf if ln.strip().endswith(".zip")
                })
    done: set[str] = set()
    out_path = Path(args.out)
    if args.resume and out_path.exists():
        with validated_open(
            str(out_path), encoding="utf-8",
            allowed_roots=(str(out_path.parent.resolve()),),
        ) as fh:
            for line in fh:
                try:
                    done.add(json.loads(line)["key"])
                except (json.JSONDecodeError, KeyError):
                    continue
    with validated_open(
        str(out_path), "a",
        allowed_roots=(str(out_path.parent.resolve()),),
        encoding="utf-8",
    ) as fh:
        for p in prefixes:
            tier_prefix = p.rstrip("/") + "/"
            rows, errs = _run_tier(client, bucket, tier_prefix, args, done, fh)
            print(
                f"{tier_prefix}: {rows} rows, {errs} errors",
                file=sys.stderr,
            )


if __name__ == "__main__":
    main()
