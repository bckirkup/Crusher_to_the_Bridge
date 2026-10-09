#!/usr/bin/env python3
"""Early shared-dose event scan — joins seed size to posting outcome.

Emits one JSONL row per voyage. The summary side (always collected, cheap
ranged reads on ``summary.json``) carries the posting outcome: reported-case
attack rates, complements, and the 3%-wire reach fraction. The census side
(``--census``, one incremental gunzip of ``growth_census.json.gz`` with only
a rolling tail retained) decodes the trailing ``common_source`` witness block
and emits the voyage's *early* shared-dose events:

- object arms (``ol1``-``ol3``/``ship``): one row per contamination *object*
  whose ``seeded_epoch`` <= ``--early-epoch`` (default 48). Size =
  ``servings_served`` (takers across the object's windows); the row also
  carries ``dose_credited``, ``windows_covered`` and the largest single
  pan-window serving (``pw_max``) so object totals and per-window servings
  can be read separately.
- v1/independent arms (``ind``, mega A1/A3): one row per pan-window *event*
  with ``start_epoch`` <= ``--early-epoch``. Size = ``servings_taken``.

Everything else on the census side is aggregated to counts (late events,
total objects/events, telemetry) — raw event/object lists are never
retained. Arms with the mechanism off emit no ``common_source`` block at
all; ``saw_cs`` records the marker so a legitimately empty witness is
distinguishable from a truncated tail.

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
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_source_readout import (  # noqa: E402
    _cs_fields,
    _list_keys,
    _tail_fields,
)
from outbreak_anchor_readout import (  # noqa: E402
    _posted,
    _row_from_summary,
    _s3_client,
    _s3_member_blob,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from simulation_utils.paths import validated_open  # noqa: E402
from telemetry_buffer.observation_model.score_anchors import (  # noqa: E402
    A9_POSTING_THRESHOLD,
)

_BUCKET_DEFAULT = "crusherbucket-994254241749-us-east-1-an"
_PREFIX_DEFAULT = "campaign/noro_food_score_01/"
_SUMMARY_MEMBER = "summary.json"
_CENSUS_MEMBER = "growth_census.json.gz"

_TAIL_WINDOW = 48 << 20
_CHUNK = 4 << 20
_EARLY_EPOCH_DEFAULT = 48


def _tier_of(key: str, prefix: str) -> str:
    """The campaign tier = the directory the zip sits in."""
    return key.rsplit("/", 2)[-2] if "/" in key else prefix.rstrip("/")


_EMESIS_EMITTED_RE = re.compile(rb'"emesis_emitted":\s*([1-9]\d*)')
_ACQ_OVERLAP = 4096


def _tail_decompress(blob: bytes) -> tuple[bytes, bool, bool, int]:
    """Incremental gunzip keeping only the rolling tail window.

    Returns (tail, saw_cs_marker, saw_emesis, n_emesis_emitters). The
    ``common_source`` witness block is emitted near the end of the census
    document (before ``census_epochs``), so a ~48 MB tail decodes it without
    materialising the ~1 GB decompressed text. ``n_emesis_emitters`` counts
    host rows with ``emesis_emitted`` > 0 — the census carries per-host
    emesis tallies only, not per-episode venue rows.
    """
    dec = zlib.decompressobj(16 + zlib.MAX_WBITS)
    tail = b""
    prev = b""
    saw_cs = False
    saw_emesis = False
    n_emitters = 0
    for i in range(0, len(blob), _CHUNK):
        part = dec.decompress(blob[i : i + _CHUNK])
        buf = prev + part
        saw_cs = saw_cs or b'"common_source":' in buf
        n_emitters += len(_EMESIS_EMITTED_RE.findall(buf))
        saw_emesis = saw_emesis or b"emesis" in part
        prev = buf[-_ACQ_OVERLAP:]
        tail = (tail + part)[-_TAIL_WINDOW:]
    tail = (tail + dec.flush())[-_TAIL_WINDOW:]
    return tail, saw_cs, saw_emesis, n_emitters


def _object_rows(
    objects: list[dict], events: list[dict], early_max: int
) -> tuple[list[dict], int, int]:
    """Per-object early rows + (n_late_objects, n_linked_events)."""
    by_object: dict[str, list[dict]] = {}
    for e in events:
        oid = e.get("object_id")
        if oid is not None:
            by_object.setdefault(oid, []).append(e)
    rows = []
    n_late = 0
    for o in objects:
        linked = by_object.get(o.get("object_id"), [])
        takers = int(o.get("servings_served") or 0)
        if not takers and linked:
            takers = sum(int(e.get("servings_taken", 0) or 0) for e in linked)
        epoch = o.get("seeded_epoch")
        row = {
            "f": "obj",
            "k": o.get("source_kind"),
            "e": epoch,
            "t": takers,
            "d": o.get("dose_credited"),
            "z": o.get("zone"),
            "w": o.get("windows_covered"),
            "pw": max(
                (int(e.get("servings_taken", 0) or 0) for e in linked),
                default=0,
            ),
        }
        if epoch is not None and int(epoch) <= early_max:
            rows.append(row)
        else:
            n_late += 1
    return rows, n_late, len(events)


def _v1_rows(
    events: list[dict], object_ids: set, early_max: int
) -> tuple[list[dict], int]:
    """Per-event early rows for pan-window servings with no object."""
    rows = []
    n_late = 0
    for e in events:
        oid = e.get("object_id")
        if oid is not None and oid in object_ids:
            continue  # accounted under its object row
        epoch = e.get("start_epoch")
        if epoch is None:
            epoch = e.get("epoch")
        row = {
            "f": "ev",
            "k": e.get("source_kind"),
            "e": epoch,
            "t": int(e.get("servings_taken", 0) or 0),
            "d": (
                float(e["per_serving_dose"]) * int(e.get("servings_taken", 0))
                if e.get("per_serving_dose")
                else None
            ),
            "z": e.get("zone"),
            "coh": e.get("cohort_size"),
        }
        if epoch is not None and int(epoch) <= early_max:
            rows.append(row)
        else:
            n_late += 1
    return rows, n_late


def _census_side(blob: bytes, early_max: int) -> dict:
    tail, saw_cs, saw_emesis, n_emitters = _tail_decompress(blob)
    cs_fields = _tail_fields(tail)
    if saw_cs and "common_source" not in cs_fields:
        # Block start fell outside the tail window — full-decode fallback.
        cs_fields = _tail_fields(gzip.decompress(blob))
    telemetry, events, exposures, objects = _cs_fields(cs_fields)
    early_obj, n_late_obj, _ = _object_rows(objects, events, early_max)
    early_ev, n_late_ev = _v1_rows(
        events, {o.get("object_id") for o in objects}, early_max
    )
    # Largest single serving in a late (>early_max) pan-window event — kept
    # so "posting with only big LATE events" is distinguishable.
    max_late = max(
        [0]
        + [
            int(e.get("servings_taken", 0) or 0)
            for e in events
            if (e.get("start_epoch") or e.get("epoch") or 0) > early_max
            or (e.get("start_epoch") or e.get("epoch")) is None
        ]
    )
    return {
        "early": early_obj + early_ev,
        "n_early_obj": len(early_obj),
        "n_early_ev": len(early_ev),
        "n_late_obj": n_late_obj,
        "n_late_ev": n_late_ev,
        "n_objects": len(objects),
        "n_events": len(events),
        "n_exposures": len(exposures),
        "max_early_takers": max(
            (r["t"] for r in early_obj + early_ev), default=0
        ),
        "max_late_ev_takers": max_late,
        "telemetry": telemetry,
        "saw_cs": saw_cs,
        "saw_emesis": saw_emesis,
        "n_emesis_emitters": n_emitters,
    }


def _summary_side(summary: dict, key: str) -> dict:
    base = _row_from_summary(summary, key.rsplit("/", 1)[-1])
    params = summary.get("parameters", {})
    body = summary.get("summary", {})
    mech = summary.get("mechanisms", {})
    anchor = base["anchor_row"]
    rep_pax_ar = anchor["reported_case_attack_rate_passenger"]
    rep_crew_ar = anchor["reported_case_attack_rate_crew"]
    reach = max(rep_pax_ar, rep_crew_ar) / A9_POSTING_THRESHOLD
    routes = body.get("infections_by_dominant_route") or {}
    return {
        "seed": base["seed"],
        "hull": anchor["hull"],
        "num_epochs": int(params.get("num_epochs", 0) or 0),
        "posted": _posted(anchor),
        "posted_stream": (
            "pax" if rep_pax_ar >= A9_POSTING_THRESHOLD else ""
        )
        + ("crew" if rep_crew_ar >= A9_POSTING_THRESHOLD else ""),
        "rep_pax_ar": rep_pax_ar,
        "rep_crew_ar": rep_crew_ar,
        "rep_pax_n": body.get("cumulative_reported_cases_passenger"),
        "rep_crew_n": body.get("cumulative_reported_cases_crew"),
        "pax_comp": anchor["passenger_complement"],
        "crew_comp": anchor["crew_complement"],
        "reach": round(reach, 4),
        "inf_ar_pax": anchor["infection_attack_rate_passenger"],
        "inf_ar_crew": anchor["infection_attack_rate_crew"],
        "n_acquired": base["n_acquired"],
        "n_imports": base["n_imports"],
        "vsp_trigger": base["vsp_trigger_epoch"] is not None,
        "cs_events_summary": int(mech.get("common_source_events", 0) or 0),
        "cs_takers_summary": int(mech.get("common_source_takers", 0) or 0),
        "cs_food_inf": int(routes.get("common_source_food", 0) or 0),
    }


def _fetch(client, bucket: str, key: str, prefix: str, args) -> dict:
    row: dict = {"key": key, "tier": _tier_of(key, prefix)}
    try:
        blob = _s3_member_blob(client, bucket, key, _SUMMARY_MEMBER)
        if blob is None:
            return {**row, "error": "no summary member"}
        row.update(_summary_side(json.loads(blob), key))
    except Exception as exc:  # noqa: BLE001 — per-voyage isolation
        return {**row, "error": f"summary: {exc}"}
    if args.no_census:
        return row
    try:
        blob = _s3_member_blob(client, bucket, key, _CENSUS_MEMBER)
        if blob is None:
            row["census"] = {"error": "no census member"}
            return row
        row["census"] = _census_side(blob, args.early_epoch)
    except Exception as exc:  # noqa: BLE001 — per-voyage isolation
        row["census"] = {"error": str(exc)}
    return row


def _load_key_filter(flag: str | None) -> set[str] | None:
    if not flag:
        return None
    with validated_open(
        str(flag),
        encoding="utf-8",
        allowed_roots=(str(Path(flag).resolve().parent),),
    ) as fh:
        return {ln.strip() for ln in fh if ln.strip().endswith(".zip")}


def _load_done(out_path: Path, resume: bool) -> set[str]:
    done: set[str] = set()
    if resume and out_path.exists():
        with validated_open(
            str(out_path),
            encoding="utf-8",
            allowed_roots=(str(out_path.parent.resolve()),),
        ) as fh:
            for line in fh:
                try:
                    done.add(json.loads(line)["key"])
                except (json.JSONDecodeError, KeyError):
                    continue
    return done


def _run_prefix(
    client, bucket: str, prefix: str, args, done: set[str], fh
) -> tuple[int, int]:
    keys = _list_keys(client, bucket, prefix)
    keys_set = args.keys_set
    if keys_set is not None:
        keys = [k for k in keys if k in keys_set]
    keys = [k for k in keys if k not in done]
    if not keys:
        return 0, 0
    n_rows = 0
    n_err = 0
    with ThreadPoolExecutor(args.workers) as pool:
        futs = {
            pool.submit(_fetch, client, bucket, k, prefix, args): k
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
                    f"  {prefix}: {i}/{len(keys)} ({n_err} errors)",
                    file=sys.stderr,
                )
    fh.flush()
    return n_rows, n_err


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bucket", default=_BUCKET_DEFAULT)
    ap.add_argument(
        "--prefix",
        action="append",
        dest="prefixes",
        help="s3:// URI or bucket-relative prefix; repeatable",
    )
    ap.add_argument(
        "--keys",
        metavar="FILE",
        help="file of explicit S3 keys to scan (one per line); "
        "without it every zip under each --prefix is scanned",
    )
    ap.add_argument("--no-census", action="store_true",
                    help="summary.json only — posting outcome, no events")
    ap.add_argument("--early-epoch", type=int, default=_EARLY_EPOCH_DEFAULT,
                    help="seeded_epoch/start_epoch ceiling for 'early'")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", required=True, help="JSONL rows output")
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    args.keys_set = _load_key_filter(args.keys)
    prefixes = [
        p[len("s3://") + len(args.bucket) + 1:] if p.startswith("s3://")
        else p
        for p in (args.prefixes or [_PREFIX_DEFAULT])
    ]
    out_path = Path(args.out)
    done = _load_done(out_path, args.resume)
    client = _s3_client()
    with validated_open(
        str(out_path),
        "a",
        allowed_roots=(str(out_path.parent.resolve()),),
        encoding="utf-8",
    ) as fh:
        for p in prefixes:
            tier_prefix = p.rstrip("/") + "/"
            rows, errs = _run_prefix(
                client, args.bucket, tier_prefix, args, done, fh
            )
            print(f"{tier_prefix}: {rows} rows, {errs} errors",
                  file=sys.stderr)


if __name__ == "__main__":
    main()
