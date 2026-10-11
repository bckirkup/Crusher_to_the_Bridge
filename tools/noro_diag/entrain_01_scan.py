#!/usr/bin/env python3
"""NORO-ENTRAIN-01 fleet scan — one pass over campaign run zips.

Emits one JSONL row per voyage with everything the ENTRAIN-01 readout
(design doc ``docs/norovirus/noro_entrain_01_sweep_design.md`` §6/§11)
needs:

- summary-level fields on every key (posting flag + stream, reported
  and infection ARs, reported case counts vs the emitted-complement
  wires, dominant-route tallies, mechanism counters, the common_source
  override echo, and the boarding-witness block
  ``initiation.manifest.boarding.norwalk_gi.{drawn_by_role,composition}``
  plus the embarkation-immune tally) — cheap ranged reads on
  ``summary.json``;
- census-level fields when the census member is scanned: acquisition
  epochs for burst48/burst12, the import roll (``hosts[].gen == 0``),
  per-object witness rows for the serving-shape and arriving-shedder
  tables (``source_agent_id`` joined to the import roll), early
  shared-dose event rows (the §4.1 discriminator measure), emesis
  emitters, and the object-integrity tallies of design §6.3.

Per-key read depth follows the SCORE-01 scan pattern: keys listed in
the ``--full-keys`` file get the whole census member streamed once;
keys in ``--head-keys`` get the head-only pass (burst vectors plus the
``hosts[]`` import roll); anything else is summary.json only. All reads
are read-only S3 gets with ranged fetches — nothing touches the engine.
``--resume`` makes a re-run skip keys already written to the JSONL out.
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
from common_source_readout import _cs_fields, _list_keys, _tail_fields  # noqa: E402
from food_score_01_scan import _acq_epochs, _integrity  # noqa: E402
from onset_curve_readout import _burst, _census_prefix  # noqa: E402
from outbreak_anchor_readout import _posted, _row_from_summary, _s3_client, _s3_member_blob  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from simulation_utils.paths import validated_open  # noqa: E402
from telemetry_buffer.observation_model.score_anchors import (  # noqa: E402
    A9_POSTING_THRESHOLD,
)

_TAIL_WINDOW = 48 << 20
_CHUNK = 4 << 20
_ACQ_OVERLAP = 4096
_EARLY_EPOCH = 48

_BUCKET_DEFAULT = "crusherbucket-994254241749-us-east-1-an"
_PREFIX_DEFAULT = "campaign/noro_entrain_01/"
_SUMMARY_MEMBER = "summary.json"
_CENSUS_MEMBER = "growth_census.json.gz"

# Host rows emit {"agent_id": N, "gen": G, "infected_epochs": ...} with the
# three keys adjacent; the loose ``agent_id+gen`` pattern also matches emit
# and patch records, so the import roll anchors on the host-row triple.
_IMPORT_HOST_RE = re.compile(
    rb'"agent_id":\s*(\d+),\s*"gen":\s*0,\s*"infected_epochs"'
)
_EMESIS_EMITTED_RE = re.compile(rb'"emesis_emitted":\s*([1-9]\d*)')


def _tier_arm(tier: str) -> tuple[str, str]:
    """``fl_<hull>_<len>d_<rung>_<arm>`` -> (hull, arm)."""
    parts = tier.split("_")
    hull = parts[1] if len(parts) > 1 else "?"
    arm = parts[-1] if parts else "?"
    return hull, arm


def _boarding(summary: dict) -> dict:
    boarding = (
        ((summary.get("initiation") or {}).get("manifest") or {})
        .get("boarding") or {}
    ).get("norwalk_gi") or {}
    drawn = boarding.get("drawn_by_role") or {}
    comp = boarding.get("composition") or {}
    pba = boarding.get("preboarding_assessment") or {}
    screened = sum(
        int((pba.get(role) or {}).get("screened_out") or 0)
        for role in ("passenger", "crew")
    )
    return {
        "drawn_pax": int(drawn.get("passenger") or 0),
        "drawn_crew": int(drawn.get("crew") or 0),
        "composition": {k: int(v) for k, v in comp.items()},
        "screened_out": screened,
    }


def _object_rows(
    objects: list[dict], events: list[dict], import_ids: set[int],
) -> tuple[list[dict], list[dict], dict]:
    """Per-object rows + per-early-event rows + import-source tallies.

    Object rows carry the fields the serving-shape and integrity tables
    need; event rows carry the §4 route-decomposition columns. ``src`` is
    ``"import"`` when the source agent is on the gen-0 import roll,
    ``"acq"`` for an onboard-acquired source, ``"?"`` when unresolvable.
    """
    by_object: dict[str, list[dict]] = {}
    for e in events:
        oid = e.get("object_id")
        if oid is not None:
            by_object.setdefault(oid, []).append(e)
    obj_rows = []
    early_rows = []
    tallies = {"obj_src_import": 0, "obj_src_acq": 0, "obj_src_none": 0,
               "early_obj_src_import": 0, "n_late_obj": 0}
    for o in objects:
        oid = o.get("object_id")
        linked = by_object.get(oid, [])
        pw_list = [
            int(e.get("servings_taken", 0) or 0) for e in linked
        ]
        src_id = o.get("source_agent_id")
        if src_id is None:
            src = "none"
        elif int(src_id) in import_ids:
            src = "import"
        else:
            src = "acq"
        tallies["obj_src_" + ("import" if src == "import"
                              else "acq" if src == "acq" else "none")] += 1
        epoch = o.get("seeded_epoch")
        row = {
            "k": o.get("source_kind"),
            "e": epoch,
            "w": o.get("windows_covered"),
            "t": int(o.get("servings_served") or 0) or sum(pw_list),
            "pans": o.get("pans_emitted"),
            "end": o.get("end_reason"),
            "lot_srv": o.get("lot_servings"),
            "pw_max": max(pw_list, default=0),
            "pw": pw_list,
            "src": src,
            "zone": o.get("zone"),
        }
        obj_rows.append(row)
        if epoch is not None and int(epoch) <= _EARLY_EPOCH:
            early_rows.append({"f": "obj", **row})
            if src == "import":
                tallies["early_obj_src_import"] += 1
        else:
            tallies["n_late_obj"] += 1
    return obj_rows, early_rows, tallies


def _event_rows(
    events: list[dict], object_ids: set, import_ids: set[int],
) -> list[dict]:
    """Early v1 pan-window event rows (``ind`` cells; no object linkage)."""
    rows = []
    for e in events:
        oid = e.get("object_id")
        if oid is not None and oid in object_ids:
            continue  # accounted under its object row
        epoch = e.get("start_epoch")
        if epoch is None:
            epoch = e.get("epoch")
        if epoch is None or int(epoch) > _EARLY_EPOCH:
            continue
        src_id = e.get("source_agent_id")
        rows.append({
            "f": "ev",
            "k": e.get("source_kind"),
            "e": epoch,
            "t": int(e.get("servings_taken", 0) or 0),
            "src": (
                "import" if src_id is not None and int(src_id) in import_ids
                else "acq" if src_id is not None else "none"
            ),
            "zone": e.get("zone"),
        })
    return rows


def _census_side(blob: bytes, num_epochs: int) -> dict:
    """Stream-decompress the census member once.

    Returns the acquisition/burst counters, the gen-0 import roll, the
    common-source witness (objects + events aggregated in-worker), early
    shared-dose rows, and the §6.3 integrity tallies.
    """
    dec = zlib.decompressobj(16 + zlib.MAX_WBITS)
    acq_all: list[int] = []
    cs_acq: list[int] = []
    import_ids: set[int] = set()
    n_emesis = 0
    prev = b""
    tail = b""
    saw_marker = False
    marker = b'"common_source":'
    for i in range(0, len(blob), _CHUNK):
        part = dec.decompress(blob[i : i + _CHUNK])
        buf = prev + part
        saw_marker = saw_marker or marker in buf
        _acq_epochs(buf, acq_all, cs_acq)
        import_ids.update(int(m.group(1)) for m in _IMPORT_HOST_RE.finditer(buf))
        n_emesis += len(_EMESIS_EMITTED_RE.findall(buf))
        prev = buf[-_ACQ_OVERLAP:]
        tail = (tail + part)[-_TAIL_WINDOW:]
    tail = (tail + dec.flush())[-_TAIL_WINDOW:]
    cs_fields = _tail_fields(tail)
    if saw_marker and not any(cs_fields.values()):
        # Block start fell outside the tail window — full-decode fallback.
        cs_fields = _tail_fields(gzip.decompress(blob))
    telemetry, events, exposures, objects = _cs_fields(cs_fields)
    obj_rows, early_obj, tallies = _object_rows(objects, events, import_ids)
    early_ev = _event_rows(
        events, {o.get("object_id") for o in objects}, import_ids,
    )
    spans = [
        (int(o["seeded_epoch"]), int(o.get("exhausted_epoch") or num_epochs - 1))
        for o in objects if o.get("seeded_epoch") is not None
    ]
    out = {
        "saw_cs": saw_marker,
        "n_events": len(events),
        "n_exposures": len(exposures),
        "telemetry": telemetry,
        "n_objects": len(objects),
        "obj_rows": obj_rows,
        "early": early_obj + early_ev,
        "max_early_takers": max(
            (r["t"] for r in early_obj + early_ev), default=0,
        ),
        "integrity": _integrity(events, objects),
        "n_acq": len(acq_all),
        "cs_acq_n": len(cs_acq),
        "cs_acq_in_span": sum(
            1 for e in cs_acq if any(s <= e <= t for s, t in spans)
        ),
        "n_import_hosts": len(import_ids),
        "n_emesis_emitters": n_emesis,
    }
    out.update(tallies)
    for w in (48, 24, 12, 6):
        share, centre = _burst(acq_all, w)
        out[f"burst{w}"] = round(share, 4)
        if w == 48:
            out["burst48_centre"] = centre
    return out


def _head_side(client, bucket: str, key: str) -> dict:
    """Head-only census: bursts + the import roll from ``hosts[]``."""
    text = _census_prefix(client, bucket, key)
    if not text:
        return {"head_only": True, "error": "no census head"}
    blob = text.encode("utf-8")
    acq_all: list[int] = []
    cs_acq: list[int] = []
    _acq_epochs(blob, acq_all, cs_acq)
    import_ids = {int(m.group(1)) for m in _IMPORT_HOST_RE.finditer(blob)}
    bursts = {}
    for w in (48, 24, 12, 6):
        share, centre = _burst(acq_all, w)
        bursts[f"burst{w}"] = round(share, 4)
        if w == 48:
            bursts["burst48_centre"] = centre
    return {
        "head_only": True,
        "n_acq": len(acq_all),
        "cs_acq_n": len(cs_acq),
        "n_import_hosts": len(import_ids),
        "n_emesis_emitters": len(_EMESIS_EMITTED_RE.findall(blob)),
        **bursts,
    }


def _summary_side(summary: dict, key: str, tier: str) -> dict:
    base = _row_from_summary(summary, key.rsplit("/", 1)[-1])
    params = summary.get("parameters", {})
    body = summary.get("summary", {})
    mech = summary.get("mechanisms", {})
    anchor = base["anchor_row"]
    rep_pax_ar = anchor["reported_case_attack_rate_passenger"]
    rep_crew_ar = anchor["reported_case_attack_rate_crew"]
    hull, arm = _tier_arm(tier)
    cs_echo = params.get("common_source") or {}
    ts = summary.get("timeseries") or []
    row = {
        "key": key,
        "tier": tier,
        "hull": hull,
        "arm": arm,
        "seed": base["seed"],
        "posted": _posted(anchor),
        "posted_stream": (
            ("pax" if rep_pax_ar >= A9_POSTING_THRESHOLD else "")
            + ("crew" if rep_crew_ar >= A9_POSTING_THRESHOLD else "")
        ),
        "rep_pax_ar": rep_pax_ar,
        "rep_crew_ar": rep_crew_ar,
        "rep_pax_n": body.get("cumulative_reported_cases_passenger"),
        "rep_crew_n": body.get("cumulative_reported_cases_crew"),
        "pax_comp": anchor["passenger_complement"],
        "crew_comp": anchor["crew_complement"],
        "reach": round(
            max(rep_pax_ar, rep_crew_ar) / A9_POSTING_THRESHOLD, 4,
        ),
        "inf_ar_pax": anchor["infection_attack_rate_passenger"],
        "inf_ar_crew": anchor["infection_attack_rate_crew"],
        "n_acquired": base["n_acquired"],
        "n_imports": base["n_imports"],
        "ignited": base["ignited"],
        "vsp_trigger": base["vsp_trigger_epoch"] is not None,
        "peak_prevalence": base["peak_prevalence"],
        "onset_epoch": base["onset_epoch"],
        "peak_epoch": base["peak_epoch"],
        "detection_epoch": base["detection_epoch"],
        "routes": body.get("infections_by_dominant_route") or {},
        "dose_share": body.get("infection_dose_share_by_route") or {},
        "cs_events_summary": int(mech.get("common_source_events", 0) or 0),
        "cs_takers_summary": int(mech.get("common_source_takers", 0) or 0),
        "cs_echo": cs_echo,
        "immune": body.get("immune"),
        "immune_init": (ts[0].get("immune") if ts else None),
        "num_epochs": int(params.get("num_epochs", 0) or 0),
        "engine_sha": params.get("engine_git_sha"),
    }
    row.update(_boarding(summary))
    return row


def _fetch(client, bucket: str, key: str, mode: str) -> dict:
    tier = key.rsplit("/", 2)[-2]
    try:
        blob = _s3_member_blob(client, bucket, key, _SUMMARY_MEMBER)
        if blob is None:
            return {"key": key, "tier": tier, "error": "no summary member"}
        row = _summary_side(json.loads(blob), key, tier)
    except Exception as exc:  # noqa: BLE001 — per-voyage isolation
        return {"key": key, "tier": tier, "error": f"summary: {exc}"}
    if mode == "none":
        row["census"] = None
    elif mode == "head":
        row["census"] = _try(lambda: _head_side(client, bucket, key))
    else:
        blob = _try(
            lambda: _s3_member_blob(client, bucket, key, _CENSUS_MEMBER)
        )
        row["census"] = (
            blob if isinstance(blob, dict)
            else _try(lambda: _census_side(blob, row["num_epochs"]))
            if blob is not None
            else {"error": "no census member"}
        )
    return row


def _try(fn):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 — per-voyage isolation
        return {"error": str(exc)}


def _key_set_file(flag: str | None) -> set[str] | None:
    """A ``--*-keys`` file -> the set of zip keys it names."""
    if not flag:
        return None
    root = str(Path(flag).resolve().parent)
    with validated_open(str(flag), encoding="utf-8",
                        allowed_roots=(root,)) as fh:
        return {t for ln in fh if (t := ln.strip()).endswith(".zip")}


def _already_scanned(out_path: Path, resume: bool) -> set[str]:
    """Keys with a row already in the JSONL out (``--resume``)."""
    if not (resume and out_path.exists()):
        return set()
    root = str(out_path.parent.resolve())
    with validated_open(str(out_path), encoding="utf-8",
                        allowed_roots=(root,)) as fh:
        return {
            row["key"]
            for ln in fh
            if (row := _parse_row(ln)) is not None and "key" in row
        }


def _parse_row(line: str) -> dict | None:
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def _run_prefix(
    client, bucket: str, prefix: str, args, done: set[str], fh,
) -> tuple[int, int]:
    keys = [k for k in _list_keys(client, bucket, prefix) if k not in done]
    if args.full_set is not None or args.head_set is not None:
        wanted = (args.full_set or set()) | (args.head_set or set())
        keys = [k for k in keys if k in wanted]
    if not keys:
        return 0, 0

    def mode(k: str) -> str:
        if args.full_set is not None and k in args.full_set:
            return "full"
        if args.head_set is not None and k in args.head_set:
            return "head"
        return "none" if (args.full_set or args.head_set) else (
            "none" if args.no_census else "full"
        )

    n_rows, n_err, done_i = 0, 0, 0
    with ThreadPoolExecutor(args.workers) as pool:
        futs = [
            pool.submit(_fetch, client, bucket, k, mode(k)) for k in keys
        ]
        for fut in as_completed(futs):
            done_i += 1
            row = fut.result()
            if row is None:
                continue
            fh.write(json.dumps(row) + "\n")
            n_rows += 1
            n_err += bool(row.get("error"))
            if done_i % 200 == 0:
                fh.flush()
                print(f"  {prefix}: {done_i}/{len(keys)} ({n_err} errors)",
                      file=sys.stderr)
    fh.flush()
    return n_rows, n_err


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, help="JSONL rows output")
    ap.add_argument("--prefix", action="append", dest="prefixes",
                    help="s3:// URI or bucket-relative prefix; repeatable")
    ap.add_argument("--bucket", default=_BUCKET_DEFAULT)
    ap.add_argument("--full-keys", metavar="FILE",
                    help="file of keys to full-census (witness + bursts)")
    ap.add_argument("--head-keys", metavar="FILE",
                    help="file of keys to head-census (bursts + import roll)")
    ap.add_argument("--no-census", action="store_true",
                    help="summary.json only — no census member reads")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()
    args.head_set = _key_set_file(args.head_keys)
    args.full_set = _key_set_file(args.full_keys)
    prefixes = [
        p.split("/", 3)[-1] if p.startswith("s3://") else p
        for p in (args.prefixes or [_PREFIX_DEFAULT])
    ]
    done = _already_scanned(Path(args.out), args.resume)
    client = _s3_client()
    out_root = str(Path(args.out).parent.resolve())
    with validated_open(
        str(args.out), "a", allowed_roots=(out_root,), encoding="utf-8",
    ) as fh:
        for p in prefixes:
            tier = p.rstrip("/") + "/"
            n, e = _run_prefix(client, args.bucket, tier, args, done, fh)
            print(f"{tier}: {n} rows, {e} errors", file=sys.stderr)


if __name__ == "__main__":
    main()
