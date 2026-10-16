"""ENTRAIN-01 dose-position audit + unposted lot-mint census.

Implications doc (``docs/norovirus/noro_entrain_01_implications.md``)
ordered step 1/2: for every acquired infection, where does the delivered
dose sit relative to the ``illness_probability`` Hill, and on unposted
cells did a ``provisioned_lot``/ill-handler/diner object ever mint?

Per zip, one JSONL row:

- summary side: posted flag (A9 threshold), funnel counters
  (``cumulative_ever_infected_*`` / ``cumulative_ever_ill_*`` /
  ``cumulative_reported_cases_*``), ``n_imports`` / ``n_acquired``,
  boarding composition fields, complements.
- census side (``growth_census.json.gz``), streamed with a rolling buffer
  and decoded only at the ``hosts``/``hazards``/``acquisitions``/
  ``common_source`` keys (doc order verified on s8000):
    * ``acq``: per-acquisition rows ``{a, ep, dr, ed, cum, p, g, w, pr}``
      where ``cum`` is the reconstructed ``acquired_particles`` the Hill
      consumes (sum of ``hazards[].effective_dose`` for the agent since
      its previous acquisition epoch, matching
      ``transmission_core._resolve_pathogen_challenge`` accumulation) and
      ``p`` is the declared Hill value at ``cum``.
    * ``mint``: ``common_source`` object mint census — object rows by
      ``source_kind`` (total vs ``seeded_epoch``-minted), events, and the
      ``telemetry`` counters (``objects_provisioned_lot``,
      ``objects_ill_handler``, ``objects_ill_diner``, ``events_*``,
      ``takers_served``, ``dose_credited``).
    * ``hz``: hazard-row count (sanity for the reconstruction).

Usage::

    python3 tools/noro_diag/entrain_01_dose_audit.py \\
        --out <rows.jsonl> --keys <file-of-keys> [--workers 32] [--resume]
    python3 tools/noro_diag/entrain_01_dose_audit.py \\
        --out <rows.jsonl> --prefix campaign/noro_entrain_01/<tier>/ ...

``--keys`` takes a newline-delimited file of full S3 keys (one scan over
an explicit, usually stratified, key set); ``--prefix`` lists one tier.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zlib
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from common_source_readout import _list_keys
from outbreak_anchor_readout import (
    _posted,
    _row_from_summary,
    _s3_client,
    _s3_member_blob,
)

from simulation_utils.paths import validated_open

_BUCKET_DEFAULT = "crusherbucket-994254241749-us-east-1-an"
_PREFIX_DEFAULT = "campaign/noro_entrain_01/"
_SUMMARY_MEMBER = "summary.json"
_CENSUS_MEMBER = "growth_census.json.gz"
_CHUNK = 1 << 22
_TAIL_KEEP = 512
_DECODE_WINDOWS = (1 << 20, 1 << 23, 1 << 26)
_TARGETS = (b"hosts", b"hazards", b"acquisitions", b"common_source")
_ETA = 0.508  # illness_probability eta, data/pathogens/active_profiles.json
_GAMMA = 0.095  # illness_probability gamma, same profile

_SEED_RE = re.compile(r"_s(\d+)\.zip$")

_FUNNEL_FIELDS = (
    "cumulative_ever_infected_passenger",
    "cumulative_ever_infected_crew",
    "cumulative_ever_ill_passenger",
    "cumulative_ever_ill_crew",
    "cumulative_reported_cases_passenger",
    "cumulative_reported_cases_crew",
    "cumulative_reported_noise_cases",
    "passenger_complement",
    "crew_complement",
)
_BOARDING_FIELDS = (
    "boarding_infected_passengers",
    "boarding_infected_crew",
    "boarding_shedder_passengers",
    "boarding_shedder_crew",
)


def _hill_p(dose: float) -> float:
    """``illness_probability`` Hill at a delivered dose (η, γ profile)."""
    if dose <= 0.0:
        return 0.0
    return 1.0 - (1.0 + _ETA * dose) ** (-_GAMMA)


def _iter_decompressed(blob: bytes):
    dec = zlib.decompressobj(16 + zlib.MAX_WBITS)
    for i in range(0, len(blob), _CHUNK):
        part = dec.decompress(blob[i : i + _CHUNK])
        if part:
            yield part
    tail = dec.flush()
    if tail:
        yield tail


_STRUCT = re.compile(rb'["\\[\]{}]')
_STR_END = re.compile(rb'["\\]')
_HZ_ROW = re.compile(
    rb'"epoch": (\d+), "agent_id": (\d+),'
    rb' "effective_dose": ([\-\d.eE+]+)'
)


def _skip_string(buf: bytes, i: int, st: dict) -> int | None:
    """From just past an opening quote: index after the closing quote.
    Sets st['in_str'] when the buffer ends mid-string so the next chunk
    resumes inside the same string."""
    while True:
        m = _STR_END.search(buf, i)
        if m is None:
            st["pos"] = len(buf)
            st["in_str"] = True
            return None
        if buf[m.start()] == 0x22:
            st["in_str"] = False
            return m.start() + 1
        i = m.start() + 2  # backslash: skip it and the escaped char


def _value_end_step(buf: bytes, i: int, st: dict) -> int | None:
    """One struct token; ``0`` when the top-level value closed, else next index."""
    m = _STRUCT.search(buf, i)
    if m is None:
        st["pos"] = len(buf)
        return None
    c = buf[m.start()]
    if c == 0x22:
        nxt = _skip_string(buf, m.start() + 1, st)
        return nxt
    if c == 0x5C:
        return m.start() + 2
    if c in b"[{":
        st["depth"] += 1
        return m.start() + 1
    st["depth"] -= 1
    nxt = m.start() + 1
    if st["depth"] == 0:
        st["pos"] = nxt
        return 0
    return nxt


def _value_end(buf: bytes, _start: int, st: dict) -> int | None:
    """Incremental bracket/string scan; end index after the top-level
    value or None when the span is incomplete. State resumes where the
    last chunk left off, so each byte is scanned exactly once."""
    i = st["pos"]
    if st.get("in_str"):
        i = _skip_string(buf, i, st)
        if i is None:
            return None
    while True:
        step = _value_end_step(buf, i, st)
        if step is None:
            return None
        if step == 0:
            return st["pos"]
        i = step


def _hazard_fold(span: bytes) -> dict[int, list[tuple[int, float]]]:
    """Fold hazard rows to per-agent (epoch, effective_dose) lists
    without materializing the JSON array (hundreds of MB on spr)."""
    out: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for m in _HZ_ROW.finditer(span):
        out[int(m.group(2))].append(
            (int(m.group(1)), float(m.group(3)))
        )
    return out


def _store_target_value(
    out: dict[str, Any],
    name: bytes,
    span: bytes,
    decoder: json.JSONDecoder,
) -> None:
    if name == b"hazards":
        out["hazards"] = _hazard_fold(span)
    else:
        out[name.decode()] = decoder.raw_decode(
            span.decode("utf-8", "replace")
        )[0]


def _marker_value_start(buf: bytes, name: bytes) -> int | None:
    j = buf.find(b'"' + name + b'":')
    if j < 0:
        return None
    s = j + len(name) + 3
    while s < len(buf) and buf[s] in b" \t\r\n":
        s += 1
    if s >= len(buf):
        return -1
    return s


def _extract_census(blob: bytes) -> dict[str, Any]:
    """Decode only the four target keys; skip everything between them.

    The marker+value scanner visits each decompressed byte once: marker
    hits buffer until the bracket scanner reports the value complete;
    ``hazards`` is folded by regex instead of a full JSON parse."""
    out: dict[str, Any] = {}
    decoder = json.JSONDecoder()
    buf = b""
    ti = 0
    val_start: int | None = None
    st = {"pos": 0, "depth": 0}
    for part in _iter_decompressed(blob):
        buf += part
        while ti < len(_TARGETS):
            name = _TARGETS[ti]
            if val_start is None:
                s = _marker_value_start(buf, name)
                if s is None:
                    if len(buf) > _CHUNK:
                        buf = buf[-_TAIL_KEEP:]
                    break
                if s < 0:
                    break
                val_start = s
                st = {"pos": s, "depth": 0}
            end = _value_end(buf, val_start, st)
            if end is None:
                break
            span = buf[val_start:end]
            _store_target_value(out, name, span, decoder)
            buf = buf[end:]
            val_start = None
            ti += 1
        if ti >= len(_TARGETS):
            break
    return out


def _cell_from_key(key: str) -> tuple[str, str]:
    """(hull, arm) from the tier directory in the key."""
    m = re.search(r"fl_(exp|cls|spr)_12d_scr_([a-z0-9_]+)/", key)
    if not m:
        return ("?", "?")
    return m.group(1), m.group(2)


def _mint_block(cs: dict[str, Any]) -> dict[str, Any]:
    tele = cs.get("telemetry") or {}
    by_kind: Counter = Counter()
    by_kind_seeded: Counter = Counter()
    for obj in cs.get("objects") or []:
        kind = obj.get("source_kind") or "unknown"
        by_kind[kind] += 1
        if obj.get("seeded_epoch") is not None:
            by_kind_seeded[kind] += 1
    ev_by_kind: Counter = Counter()
    for e in cs.get("events") or []:
        ev_by_kind[e.get("source_kind") or "unknown"] += 1
    return {
        "objects_total": len(cs.get("objects") or []),
        "by_kind": dict(by_kind),
        "by_kind_seeded": dict(by_kind_seeded),
        "events_by_kind": dict(ev_by_kind),
        "telemetry": dict(tele),
    }


def _acq_rows(census: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    hz_by_agent = census.get("hazards") or {}
    acqs = census.get("acquisitions") or []
    hosts = census.get("hosts") or []
    for rows in hz_by_agent.values():
        rows.sort()
    presented = {
        int(h["agent_id"])
        for h in hosts
        if (h.get("symptomatic_epochs") or 0) > 0
    }
    acq_by_agent: dict[int, list[dict]] = defaultdict(list)
    for a in acqs:
        acq_by_agent[int(a["agent_id"])].append(a)
    out: list[dict[str, Any]] = []
    for aid, rows in acq_by_agent.items():
        rows.sort(key=lambda r: int(r["epoch"]))
        prev = -1
        for a in rows:
            ep = int(a["epoch"])
            cum = sum(
                d for e, d in hz_by_agent.get(aid, ()) if prev < e <= ep
            )
            out.append(
                {
                    "a": aid,
                    "ep": ep,
                    "dr": a.get("dose_read"),
                    "ed": a.get("effective_dose"),
                    "cum": round(cum, 4),
                    "p": round(_hill_p(cum), 6),
                    "g": a.get("gen"),
                    "w": a.get("dominant_pathway"),
                    "pr": aid in presented,
                }
            )
            prev = ep
    return out, sum(len(v) for v in hz_by_agent.values())


def _row(client, bucket: str, key: str, member: str) -> dict[str, Any]:
    hull, arm = _cell_from_key(key)
    row: dict[str, Any] = {"key": key, "hull": hull, "arm": arm}
    m = _SEED_RE.search(key)
    if m:
        row["seed"] = int(m.group(1))
    sblob = _s3_member_blob(client, bucket, key, _SUMMARY_MEMBER)
    if sblob is None:
        row["error"] = "no summary member"
        return row
    summary = json.loads(sblob)
    body = summary.get("summary") or {}
    for f in _FUNNEL_FIELDS:
        row[f] = body.get(f)
    params = summary.get("parameters", {})
    for f in _BOARDING_FIELDS:
        row[f] = params.get(f)
    try:
        run = _row_from_summary(summary, Path(key).stem)
        row["posted"] = _posted(run["anchor_row"])
        row["n_imports"] = run["n_imports"]
        row["n_acquired"] = run["n_acquired"]
        row["ignited"] = run["ignited"]
    except Exception as exc:  # noqa: BLE001 — per-voyage isolation
        row["posted_error"] = str(exc)
    if member == "summary":
        return row
    cblob = _s3_member_blob(client, bucket, key, _CENSUS_MEMBER)
    if cblob is None:
        row["census_error"] = "no census member"
        return row
    census = _extract_census(cblob)
    missing = [t.decode() for t in _TARGETS if t.decode() not in census]
    if missing:
        row["extract_missing"] = missing
    row["acq"], row["hz"] = _acq_rows(census)
    row["mint"] = _mint_block(census.get("common_source") or {})
    return row


def _fetch(client, bucket: str, key: str, member: str) -> dict[str, Any]:
    try:
        return _row(client, bucket, key, member)
    except Exception as exc:  # noqa: BLE001 — per-voyage isolation
        return {"key": key, "error": str(exc)}


def _already_scanned(out_path: Path, resume: bool) -> set[str]:
    if not (resume and out_path.exists()):
        return set()
    root = str(out_path.parent.resolve())
    done = set()
    with validated_open(
        str(out_path), encoding="utf-8", allowed_roots=(root,)
    ) as fh:
        for line in fh:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "key" in row:
                done.add(row["key"])
    return done


def _gather_keys(client, bucket: str, args) -> list[str]:
    if args.keys_file:
        with validated_open(
            args.keys_file, encoding="utf-8",
            allowed_roots=(str(Path(args.keys_file).parent.resolve()),),
        ) as fh:
            return [ln.strip() for ln in fh if ln.strip()]
    keys: list[str] = []
    for prefix in args.prefixes or [_PREFIX_DEFAULT]:
        tier = prefix.rstrip("/") + "/"
        keys.extend(_list_keys(client, bucket, tier))
    return keys


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, help="JSONL rows output")
    ap.add_argument(
        "--prefix", action="append", dest="prefixes",
        help="bucket-relative prefix or s3:// URI; repeatable",
    )
    ap.add_argument(
        "--keys", dest="keys_file", default=None,
        help="newline-delimited file of full S3 keys to scan",
    )
    ap.add_argument("--bucket", default=_BUCKET_DEFAULT)
    ap.add_argument(
        "--member", choices=("summary", "both"), default="both",
        help="summary = summary.json only (cheap posted/funnel pass)",
    )
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--workers", type=int, default=32)
    args = ap.parse_args()
    out_path = Path(args.out)
    done = _already_scanned(out_path, args.resume)
    client = _s3_client()
    prefixes = [
        p.split("/", 3)[-1] if p.startswith("s3://") else p
        for p in (args.prefixes or [])
    ]
    args.prefixes = prefixes
    keys = [k for k in _gather_keys(client, args.bucket, args)
            if k not in done]
    out_root = str(out_path.parent.resolve())
    n_rows = n_err = 0
    with validated_open(
        str(out_path), "a", allowed_roots=(out_root,), encoding="utf-8",
    ) as fh, ThreadPoolExecutor(args.workers) as pool:
        futs = [
            pool.submit(_fetch, client, args.bucket, k, args.member)
            for k in keys
        ]
        for i, fut in enumerate(as_completed(futs)):
            row = fut.result()
            fh.write(json.dumps(row) + "\n")
            n_rows += 1
            n_err += bool(row.get("error"))
            if (i + 1) % 200 == 0:
                fh.flush()
                print(f"  {i + 1}/{len(keys)}", file=sys.stderr)
        fh.flush()
    print(f"{n_rows} rows, {n_err} errors", file=sys.stderr)


if __name__ == "__main__":
    main()
