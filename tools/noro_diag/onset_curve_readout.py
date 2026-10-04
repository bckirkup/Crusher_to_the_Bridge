"""NORO-ONSET-CURVE-01 — per-voyage acquisition/onset clustering readout.

Design: docs/norovirus/noro_onset_curve_01_design.md. Discriminates a
propagated-ramp outbreak (acquisitions dispersed across the voyage) from a
point-source-shaped one (acquisitions clustered inside ~one incubation
window), measured on the per-host ``epoch_acquired`` field inside each run
zip's ``growth_census.json.gz`` member. Sampling is bounded: a stride sample
of voyages per cell plus every posted voyage (VSP trigger non-null) — the
rare-excursion tail that decides whether clustered acquisition ever
materializes.

Reads only; no engine involvement. Outputs a committed-readout-style
markdown table.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics as stats
import struct
import sys
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from outbreak_anchor_readout import _s3_client, _s3_member_blob, _s3_parse_uri  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from simulation_utils.paths import validated_open  # noqa: E402

_BUCKET_DEFAULT = "crusherbucket-994254241749-us-east-1-an"
_PREFIXES_DEFAULT = [
    "campaign/noro_outbreak_02/",
    "campaign/noro_outbreak_03/",
    "campaign/noro_outbreak_04/",
    "campaign/noro_mega_01/",
]

# The rung/surveillance fields may carry underscores, so the old lazy-group
# key/host regexes were rewritten as plain string scans: linear, and free of
# the super-linear backtracking Sonar flags.
_AGENT_ID_RE = re.compile(r'"agent_id": \d+')
_SYMP_RE = re.compile(r'"symptomatic_epochs": (\d+)')
_ACQ_RE = re.compile(r'"epoch_acquired": (-?\d+)')
_IGN_RE = re.compile(r'"ignited": (true|false)')
_IMPORT_RE = re.compile(r'"n_imports": (\d+)')

_MIN_ACQUIRED = 10  # burst stats meaningless below this
_W_SHORT = 24  # ~one incubation window at 1-epoch hours
_W_LONG = 48
_W_SPIKE = 6  # single-meal common-source synchrony bound
_W_SPIKE2 = 12


def _list_zip_keys(client, bucket: str, prefix: str) -> list[str]:
    keys: list[str] = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(".zip"):
                keys.append(obj["Key"])
    return keys


def _leading_digits(text: str) -> str:
    """The digit run at the head of ``text`` (possibly empty)."""
    i = 0
    while i < len(text) and text[i].isdigit():
        i += 1
    return text[:i]


def _partition_tagged(
    text: str, tag: str, start: int = 0
) -> tuple[str, str] | None:
    """(before, after) at the first ``tag`` occurrence followed by a digit."""
    while True:
        idx = text.find(tag, start)
        if idx < 0:
            return None
        after = idx + len(tag)
        if after < len(text) and text[after].isdigit():
            return text[:idx], text[after:]
        start = after


def _tail_fields(rest: str) -> tuple | None:
    """``<nsf>[_bp<bp>]_n<n>_ep<e>_<surv>`` — fields after the ``_nsf`` tag."""
    nsf = _leading_digits(rest)
    if not nsf:
        return None
    rest = rest[len(nsf):]
    bp = None
    if rest.startswith("_bp"):
        pair = _partition_tagged(rest[len("_bp"):], "_n")
        if pair is None or not pair[0]:
            return None
        bp, rest = pair
        rest = "_n" + rest
    pair = _partition_tagged(rest, "_n")
    if pair is None or pair[0]:
        return None
    rest = pair[1]
    n_agents = _leading_digits(rest)
    if not n_agents:
        return None
    pair = _partition_tagged(rest[len(n_agents):], "_ep")
    if pair is None or pair[0]:
        return None
    rest = pair[1]
    n_ep = _leading_digits(rest)
    surv = rest[len(n_ep):]
    if not n_ep or not surv.startswith("_") or len(surv) < 2:
        return None
    return nsf, bp, n_agents, n_ep, surv[1:]


def _parse_key_fields(stem: str) -> tuple | None:
    """``<rung>_nsf<n>[_bp<bp>]_n<n>_ep<e>_<surv>_s<seed>`` — linear parse.

    A failed tail retries at the next ``_nsf`` boundary (lazy-group semantics),
    so a rung name may itself contain ``_nsf<digits>``.
    """
    head, sep, seed = stem.rpartition("_s")
    if not sep or not seed.isdigit():
        return None
    pos = 0
    while True:
        pair = _partition_tagged(head, "_nsf", pos)
        if pair is None:
            return None
        rung, rest = pair
        pos = len(rung) + len("_nsf")
        if not rung:
            continue
        tail = _tail_fields(rest)
        if tail is not None:
            return (rung,) + tail + (seed,)


def _parse_key(key: str) -> dict | None:
    """Parse a ``rung-`` run-zip key; first ``rung-`` whose tail parses wins."""
    if not key.endswith(".zip"):
        return None
    stem = key[:-len(".zip")]
    start = 0
    while True:
        idx = stem.find("rung-", start)
        if idx < 0:
            return None
        parsed = _parse_key_fields(stem[idx + len("rung-"):])
        if parsed is not None:
            break
        start = idx + 1
    rung, nsf, bp, n_agents, n_ep, surv, seed = parsed
    tier = key.split("/")[-2] if "/" in key else ""
    return {
        "key": key,
        "tier": tier,
        "cell": f"{tier}|{rung}|nsf{nsf}|bp{bp or 'none'}",
        "seed": int(seed),
        "num_epochs": int(n_ep),
        "num_agents": int(n_agents),
        "surveillance": surv,
    }


def _host_records(hosts: str) -> list[str]:
    """The ``{...}`` host records carrying an ``"agent_id": <int>`` field."""
    records = []
    for chunk in hosts.split("{"):
        rec, sep, _ = chunk.partition("}")
        if sep and _AGENT_ID_RE.search(rec):
            records.append("{" + rec + "}")
    return records


def _host_field(rec: str, rx: re.Pattern) -> int | None:
    m = rx.search(rec)
    return int(m.group(1)) if m else None


def _summary_posted(client, bucket: str, key: str) -> bool | None:
    blob = _s3_member_blob(client, bucket, key, "summary.json")
    if blob is None:
        return None
    try:
        return json.loads(blob).get("derived", {}).get("vsp_trigger_epoch") is not None
    except (json.JSONDecodeError, AttributeError):
        return None


def _census_prefix(client, bucket: str, key: str,
                   want_bytes: int = 6_000_000) -> str | None:
    """Range-read the head of `growth_census.json.gz` and inflate the prefix.

    The census JSON is `{...top-level..., "hosts": [...], ...per-event log}`:
    hosts[] is first and the event log makes the member hundreds of MB, so we
    only fetch enough of the compressed member to close hosts[] (a few MB).
    """
    size = client.head_object(Bucket=bucket, Key=key)["ContentLength"]
    tail_len = min(1 << 16, size)
    tail = client.get_object(
        Bucket=bucket, Key=key,
        Range=f"bytes={size - tail_len}-{size - 1}")["Body"].read()
    eocd_off = tail.rfind(b"PK\x05\x06")
    if eocd_off < 0:
        return None
    cd_size = struct.unpack_from("<I", tail, eocd_off + 12)[0]
    cd_off = struct.unpack_from("<I", tail, eocd_off + 16)[0]
    cd = client.get_object(
        Bucket=bucket, Key=key,
        Range=f"bytes={cd_off}-{cd_off + cd_size - 1}")["Body"].read()
    pos = 0
    while pos + 46 <= len(cd):
        if cd[pos : pos + 4] != b"PK\x01\x02":
            break
        name_len = struct.unpack_from("<H", cd, pos + 28)[0]
        extra_len = struct.unpack_from("<H", cd, pos + 30)[0]
        comment_len = struct.unpack_from("<H", cd, pos + 32)[0]
        lh_off = struct.unpack_from("<I", cd, pos + 42)[0]
        name = cd[pos + 46 : pos + 46 + name_len].decode("utf-8", "replace")
        if name == "growth_census.json.gz":
            lh = client.get_object(
                Bucket=bucket, Key=key,
                Range=f"bytes={lh_off}-{lh_off + 30}")["Body"].read()
            l_name_len = struct.unpack_from("<H", lh, 26)[0]
            l_extra_len = struct.unpack_from("<H", lh, 28)[0]
            data_start = lh_off + 30 + l_name_len + l_extra_len
            blob = client.get_object(
                Bucket=bucket, Key=key,
                Range=f"bytes={data_start}-{data_start + want_bytes - 1}"
            )["Body"].read()
            out = zlib.decompressobj(-15).decompress(blob)  # zip deflate
            inner = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(out)
            return inner.decode("utf-8", "replace")
        pos += 46 + name_len + extra_len + comment_len
    return None


def _census_epochs(client, bucket: str, key: str) -> dict | None:
    """Return per-voyage acquisition epochs, split all vs symptomatic cohort.

    Reads only the head of the census member: `hosts[]` sits before the huge
    per-event hand-reservoir log, so the read is a few MB, not hundreds.
    """
    text = _census_prefix(client, bucket, key)
    if text is None:
        return None
    hi = text.find('"hosts": [')
    if hi < 0:
        return None
    head = text[:hi]
    close = text.find("]", hi)
    hosts = text[hi:close + 1] if close > 0 else text[hi:]
    acquired_all: list[int] = []
    acquired_symp: list[int] = []
    n_records = 0
    for rec in _host_records(hosts):
        n_records += 1
        acq = _host_field(rec, _ACQ_RE)
        if acq is None:
            continue
        acquired_all.append(acq)
        symp = _host_field(rec, _SYMP_RE)
        if symp and symp > 0:
            acquired_symp.append(acq)
    ign = _IGN_RE.search(head) or _IGN_RE.search(text)
    imp = _IMPORT_RE.search(head) or _IMPORT_RE.search(text)
    return {
        "ignited": bool(ign and ign.group(1) == "true"),
        "n_imports": int(imp.group(1)) if imp else None,
        "n_host_records": n_records,
        "acquired": acquired_all,
        "acquired_symp": acquired_symp,
    }


def _burst(epochs: list[int], window: int) -> tuple[float, float | None]:
    """Max share of epochs inside any rolling `window`-epoch window.

    Returns (share, centre epoch of the densest window). Two-pointer over
    sorted epochs, O(n log n).
    """
    if not epochs:
        return 0.0, None
    ep = sorted(epochs)
    best, best_lo = 0, 0
    j = 0
    for i, e in enumerate(ep):
        while j < len(ep) and ep[j] <= e + window:
            j += 1
        if j - i > best:
            best, best_lo = j - i, i
    centre = (ep[best_lo] + ep[min(best_lo + best - 1, len(ep) - 1)]) / 2.0
    return best / len(ep), centre


def _voyage_metrics(epochs: dict, num_epochs: int) -> dict:
    onboard = [e for e in epochs["acquired"] if e > 0]
    onboard_symp = [e for e in epochs["acquired_symp"] if e > 0]
    out = {
        "ignited": epochs["ignited"],
        "n_imports": epochs["n_imports"],
        "n_acquired": len(onboard),
        "n_symp": len(onboard_symp),
    }
    for tag, eps in (("all", onboard), ("symp", onboard_symp)):
        if len(eps) < _MIN_ACQUIRED:
            continue
        b48, c48 = _burst(eps, _W_LONG)
        b24, _c24 = _burst(eps, _W_SHORT)
        b6, _c6 = _burst(eps, _W_SPIKE)
        b12, _c12 = _burst(eps, _W_SPIKE2)
        out[f"burst{_W_LONG}_{tag}"] = b48
        out[f"burst{_W_SHORT}_{tag}"] = b24
        out[f"burst{_W_SPIKE}_{tag}"] = b6
        out[f"burst{_W_SPIKE2}_{tag}"] = b12
        out[f"burst_centre_frac_{tag}"] = c48 / num_epochs if c48 else None
        out[f"med_acq_frac_{tag}"] = stats.median(eps) / num_epochs
    return out


def _iq(values: list[float]) -> tuple[float, float, float]:
    v = sorted(values)
    return v[len(v) // 2], v[len(v) // 4], v[min(3 * len(v) // 4, len(v) - 1)]


def _fmt_med_iqr(values: list[float], scale: float = 1.0) -> str:
    if not values:
        return "--"
    med, lo, hi = _iq(values)
    return f"{med * scale:.2f} [{lo * scale:.2f}-{hi * scale:.2f}]"


def _col(rows: list[dict], name: str) -> list[float]:
    return [r[name] for r in rows if r.get(name) is not None]


def _aggregate_cell(rows: list[dict]) -> dict:
    big = [r for r in rows if r["n_acquired"] >= _MIN_ACQUIRED]
    spiky = sum(1 for r in big if r.get(f"burst{_W_LONG}_all", 0) > 0.5)
    return {
        "n_voyages": len(rows),
        "n_meas": len(big),
        "med_acq": stats.median([r["n_acquired"] for r in big]) if big else 0,
        "burst48": _fmt_med_iqr(_col(big, f"burst{_W_LONG}_all")),
        "burst24": _fmt_med_iqr(_col(big, f"burst{_W_SHORT}_all")),
        "burst12": _fmt_med_iqr(_col(big, f"burst{_W_SPIKE2}_all")),
        "burst6": _fmt_med_iqr(_col(big, f"burst{_W_SPIKE}_all")),
        "centre": _fmt_med_iqr(_col(big, "burst_centre_frac_all")),
        "med_acq_frac": _fmt_med_iqr(_col(big, "med_acq_frac_all")),
        "symp_burst48": _fmt_med_iqr(_col(big, f"burst{_W_LONG}_symp")),
        "symp_centre": _fmt_med_iqr(_col(big, "burst_centre_frac_symp")),
        "spiky_share": spiky / len(big) if big else 0.0,
        "spike_share": sum(
            1 for r in big if r.get(f"burst{_W_SPIKE2}_all", 0) > 0.5
        ) / len(big) if big else 0.0,
    }


def render(cells: dict[str, dict], posted_rows: list[dict]) -> str:
    lines = [
        "# NORO-ONSET-CURVE-01 — acquisition/onset clustering readout",
        "",
        "Per-voyage `epoch_acquired` distributions from `growth_census` on a "
        "sample of voyages per cell plus every posted voyage. `burstW` is the "
        "max share of onboard acquisitions inside any rolling W-epoch window "
        "(48≈incubation tail, 12/6 = single-meal common-source synchrony); "
        "`centre` is the densest-48 window's position as a fraction of the "
        "voyage.",
        "",
        "| cell | measured | med acq | burst48 | burst24 | burst12 | burst6 | "
        "centre | med acq frac | symp burst48 | symp centre | "
        "share burst48>0.5 | share burst12>0.5 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for cell, agg in sorted(cells.items()):
        lines.append(
            f"| {cell} | {agg['n_meas']}/{agg['n_voyages']} | "
            f"{agg['med_acq']:.0f} | {agg['burst48']} | {agg['burst24']} | "
            f"{agg['burst12']} | {agg['burst6']} | "
            f"{agg['centre']} | {agg['med_acq_frac']} | {agg['symp_burst48']} | "
            f"{agg['symp_centre']} | {agg['spiky_share']:.2f} | "
            f"{agg['spike_share']:.2f} |"
        )
    if posted_rows:
        lines += [
            "",
            "## Posted voyages (all)",
            "",
            "| key | n_acq | burst48 | burst12 | burst6 | centre | symp n | symp burst48 | symp centre |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for r in sorted(posted_rows, key=lambda x: x["key"]):
            lines.append(
                f"| {r['key'].split('/')[-1]} | {r['n_acquired']} | "
                f"{r.get(f'burst{_W_LONG}_all', 0):.2f} | "
                f"{r.get(f'burst{_W_SPIKE2}_all', 0):.2f} | "
                f"{r.get(f'burst{_W_SPIKE}_all', 0):.2f} | "
                f"{r.get('burst_centre_frac_all') or 0:.2f} | {r['n_symp']} | "
                f"{r.get(f'burst{_W_LONG}_symp', 0):.2f} | "
                f"{r.get('burst_centre_frac_symp') or 0:.2f} |"
            )
    return "\n".join(lines) + "\n"


def _posted_keys(client, bucket: str, metas: list[dict],
                 substrs: list[str], workers: int) -> dict[str, bool]:
    """Summary-member sweep of the named cells; returns key -> posted."""
    targets = [m for m in metas if any(s in m["cell"] for s in substrs)]
    out: dict[str, bool] = {}
    print(f"posted sweep: {len(targets)} summaries", file=sys.stderr)
    with ThreadPoolExecutor(workers) as pool:
        futs = {pool.submit(_summary_posted, client, bucket, m["key"]): m["key"]
                for m in targets}
        for fut in as_completed(futs):
            out[futs[fut]] = bool(fut.result())
    return out


def _fetch_one(client, bucket: str, meta: dict, posted: dict[str, bool]) -> dict | None:
    try:
        epochs = _census_epochs(client, bucket, meta["key"])
    except Exception as exc:  # noqa: BLE001 — per-voyage isolation
        return {"key": meta["key"], "error": str(exc)}
    if epochs is None:
        return {"key": meta["key"], "error": "no census member"}
    row = {"key": meta["key"], "cell": meta["cell"], "seed": meta["seed"],
           "posted": posted.get(meta["key"], False),
           "acq_epochs": sorted(e for e in epochs["acquired"] if e > 0),
           "acq_epochs_symp": sorted(
               e for e in epochs["acquired_symp"] if e > 0)}
    row.update(_voyage_metrics(epochs, meta["num_epochs"]))
    return row


def _pick_sample(metas: list[dict], per_cell: int) -> list[dict]:
    by_cell: dict[str, list[dict]] = {}
    for m in metas:
        by_cell.setdefault(m["cell"], []).append(m)
    picked: list[dict] = []
    for cell in by_cell.values():
        cell.sort(key=lambda m: m["seed"])
        step = max(1, len(cell) // per_cell)
        picked.extend(cell[::step][:per_cell])
    return picked


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bucket", default=_BUCKET_DEFAULT)
    ap.add_argument("--prefix", action="append", dest="prefixes",
                    help="S3 campaign prefix; repeatable. Defaults to "
                    "noro_outbreak_02/03/04.")
    ap.add_argument("--sample-per-cell", type=int, default=200)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--also-seeds", action="append", default=[],
                    help="Extra seeds to include: 'tier_substr:seed,seed'")
    ap.add_argument("--posted-cell", action="append", default=[],
                    dest="posted_cells",
                    help="Cell substring; summaries are swept and every posted "
                    "voyage's census is added to the read set. Repeatable.")
    ap.add_argument("--out", help="Write the markdown readout to this path")
    ap.add_argument("--json-out", help="Dump per-voyage metrics JSON")
    ap.add_argument("--resume", action="store_true",
                    help="Skip keys already present in --json-out; "
                    "checkpoint every 500 rows so a crash can resume.")
    args = ap.parse_args()

    client = _s3_client()
    prefixes = args.prefixes or _PREFIXES_DEFAULT
    metas: list[dict] = []
    for prefix in prefixes:
        bucket, pfx = (args.bucket, prefix) if "://" not in prefix else (
            lambda t: (t[0], t[1]))(_s3_parse_uri(prefix))
        for key in _list_zip_keys(client, bucket, pfx):
            m = _parse_key(key)
            if m:
                metas.append(m)
    print(f"keys parsed: {len(metas)}", file=sys.stderr)

    posted: dict[str, bool] = {}
    if args.posted_cells:
        posted = _posted_keys(client, args.bucket, metas,
                              args.posted_cells, args.workers)

    picked = _pick_sample(metas, args.sample_per_cell)
    want = set()
    for spec in args.also_seeds:
        substr, _, seeds = spec.partition(":")
        want.update((substr, int(s)) for s in seeds.split(","))
    extra = [m for m in metas
             if (any(sub in m["tier"] and s == m["seed"] for sub, s in want)
                 or posted.get(m["key"]))
             and m not in picked]
    picked.extend(extra)
    print(f"voyages to read: {len(picked)} (+{len(extra)} posted/forced)",
          file=sys.stderr)

    json_allowed = (str(Path(args.json_out).parent.resolve()),) \
        if args.json_out else ()

    def _json_open(mode: str):
        return validated_open(
            str(args.json_out), mode, allowed_roots=json_allowed,
            encoding="utf-8")

    rows: list[dict] = []
    done_keys: set[str] = set()
    if args.resume and args.json_out and Path(args.json_out).exists():
        with _json_open("r") as fh:
            rows = json.load(fh)
        done_keys = {r["key"] for r in rows}
        print(f"resume: {len(rows)} rows already read", file=sys.stderr)
    picked = [m for m in picked if m["key"] not in done_keys]

    rows_new = 0
    errors = 0

    def _ckpt() -> None:
        if args.resume and args.json_out:
            with _json_open("w") as fh:
                json.dump(rows, fh, indent=1)

    with ThreadPoolExecutor(args.workers) as pool:
        futs = [pool.submit(_fetch_one, client, args.bucket, m, posted)
                for m in picked]
        for i, fut in enumerate(as_completed(futs), 1):
            row = fut.result()
            if row and "error" not in row:
                rows.append(row)
                rows_new += 1
                if rows_new % 500 == 0:
                    _ckpt()
            else:
                errors += 1
            if i % 200 == 0:
                print(f"  {i}/{len(picked)} ({errors} errors)", file=sys.stderr)
    _ckpt()

    cells: dict[str, list[dict]] = {}
    for r in rows:
        cells.setdefault(r["cell"], []).append(r)
    cell_agg = {c: _aggregate_cell(rs) for c, rs in cells.items()}
    posted = [r for r in rows if r.get("posted")]
    md = render(cell_agg, posted)
    if args.out:
        with validated_open(
            str(args.out), "w",
            allowed_roots=(str(Path(args.out).parent.resolve()),),
            encoding="utf-8",
        ) as fh:
            fh.write(md)
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(md)
    if args.json_out:
        with _json_open("w") as fh:
            json.dump(rows, fh, indent=1)
    print(f"done: {len(rows)} voyages, {errors} errors", file=sys.stderr)


if __name__ == "__main__":
    main()
