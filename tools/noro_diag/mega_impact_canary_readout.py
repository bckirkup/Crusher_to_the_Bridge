#!/usr/bin/env python3
"""MEGA-IMPACT-01 canary readout — the three frozen gates.

Reads the canary zips straight off S3 by ranged member GET (no full
downloads) and scores the design's admissibility criteria
(`docs/norovirus/noro_mega_impact_01_design.md`):

1. **Bit-identity gate** — for every seed in the a0id tier, the new
   zip's ``summary.json`` voyage fingerprint must reproduce the A0
   (NORO-MEGA-01) zip's fingerprint field-for-field. Compared blocks:
   ``parameters``, ``timeseries``, ``derived``, ``summary``,
   ``cost_accounting``, ``census``, ``initiation`` — every shared leaf
   must be identical. ``parameters.engine_git_sha`` is the declared
   image stamp and excluded; keys present only on one side (new schema
   fields such as ``mechanisms``/``rss_mb``) are reported separately as
   schema additions, not voyage diffs. Any other leaf diff voids
   per-seed pairing — the campaign redesigns on distributional arms.
2. **Exercise gate** — at least one A1 voyage must record
   ``mechanisms.common_source_events > 0`` (the mechanism fired).
   NOTE: on images before the witness fix that summary field reads
   the expiring ``_cs_windows`` list and undercounts to 0; the durable
   truth is ``growth_census.json.gz → common_source.telemetry``
   ``events_*`` counters, which this script also reads and reports.
3. **Peak-memory report** — ``rss_samples.json.peak_rss_mb`` plus the
   ``rss_mb.voyage``/``rss_mb.fold`` medians decide the fleet memory
   quote (design: if lean peak > ~10 GB keep 16 GB and cap concurrency
   at ~30).

Usage:
    python3 tools/noro_diag/mega_impact_canary_readout.py \
        --base-prefix s3://BUCKET/campaign/noro_mega_01/fl_mega_12d_scr \
        --canary-prefix s3://BUCKET/campaign/noro_mega_impact_01 \
        --seeds 8000:8019 --a0-seeds 8000:8009
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "tools" / "noro_diag"), str(REPO_ROOT / "tools" / "diag")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from botocore.exceptions import ClientError  # noqa: E402
from outbreak_anchor_readout import _s3_client, _s3_member_blob  # noqa: E402

BUCKET_DEFAULT = "crusherbucket-994254241749-us-east-1-an"
_RID = (
    "fl_norovirus_mega_cruise_5000_dose7p57_rung-shipped_nsf29_"
    "bp25c7_n7000_ep288_syndromic_comp65_s{seed}.zip"
)
_A0ID_TIER = "fl_mega_impact_a0id"
_A1_TIER = "fl_mega_impact_a1"

# Voyage-fingerprint blocks compared leaf-for-leaf between A0 and a0id.
_FINGERPRINT_BLOCKS = (
    "parameters", "timeseries", "derived", "summary",
    "cost_accounting", "census", "initiation",
)
# Declared non-voyage leaves: the image stamp and the tier label are
# expected to differ (a0id is the same voyage under a different tier
# name by construction).
_EXCLUDED_PATHS = {
    ("parameters", "engine_git_sha"),
    ("parameters", "tier_id"),
}


def _parse_seed_range(raw: str) -> list[int]:
    lo, _, hi = raw.partition(":")
    return list(range(int(lo), int(hi) + 1))


def _fetch_member_gz(client, bucket: str, key: str, member: str) -> dict | None:
    try:
        blob = _s3_member_blob(client, bucket, key, member)
    except ClientError:
        return None
    if blob is None:
        return None
    import gzip

    return json.loads(gzip.decompress(blob))


def _fetch_summary(client, bucket: str, key: str) -> dict | None:
    try:
        blob = _s3_member_blob(client, bucket, key, "summary.json")
    except ClientError:
        return None  # cell has not uploaded yet
    return json.loads(blob) if blob is not None else None


def _fetch_member_json(client, bucket: str, key: str, member: str) -> dict | None:
    try:
        blob = _s3_member_blob(client, bucket, key, member)
    except ClientError:
        return None
    return json.loads(blob) if blob is not None else None


def _leaf_diffs(
    a: Any, b: Any, path: tuple[str, ...] = ()
) -> tuple[list[tuple[tuple[str, ...], Any, Any]], list[tuple[str, ...]]]:
    """Return (value diffs on shared leaves, one-sided key paths)."""
    diffs: list[tuple[tuple[str, ...], Any, Any]] = []
    one_sided: list[tuple[str, ...]] = []
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) & set(b)):
            d, o = _leaf_diffs(a[key], b[key], path + (key,))
            diffs.extend(d)
            one_sided.extend(o)
        for key in sorted(set(a) ^ set(b)):
            one_sided.append(path + (key,))
        return diffs, one_sided
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            diffs.append((path + ("<len>",), len(a), len(b)))
            return diffs, one_sided
        for i, (x, y) in enumerate(zip(a, b)):
            d, o = _leaf_diffs(x, y, path + (str(i),))
            diffs.extend(d)
            one_sided.extend(o)
        return diffs, one_sided
    if a != b:
        diffs.append((path, a, b))
    return diffs, one_sided


def bit_identity_gate(client, bucket: str, args) -> bool:
    """Compare a0id vs A0 summary.json fingerprints per seed."""
    print("== Gate 1: bit-identity (a0id vs noro_mega_01) ==")
    all_clean = True
    for seed in args.a0_seeds:
        rid = _RID.format(seed=seed)
        a0 = _fetch_summary(client, bucket, f"{args.base_prefix}/{rid}")
        new = _fetch_summary(
            client, bucket, f"{args.canary_prefix}/{_A0ID_TIER}/{rid}"
        )
        if a0 is None or new is None:
            print(f"  s{seed}: MISSING (a0={a0 is not None} new={new is not None})")
            all_clean = False
            continue
        n_diffs = 0
        schema_adds: list[str] = []
        for block in _FINGERPRINT_BLOCKS:
            diffs, one_sided = _leaf_diffs(
                a0.get(block), new.get(block), (block,)
            )
            for path, va, vb in diffs:
                if path in _EXCLUDED_PATHS:
                    continue
                n_diffs += 1
                if n_diffs <= 5:
                    print(
                        f"  s{seed} DIFF {'.'.join(path)}: "
                        f"a0={va!r} new={vb!r}"
                    )
            schema_adds.extend(".".join(p) for p in one_sided)
        if n_diffs:
            print(f"  s{seed}: {n_diffs} voyage-fingerprint diffs")
            all_clean = False
        else:
            adds = f" (+{len(schema_adds)} schema keys)" if schema_adds else ""
            print(f"  s{seed}: identical{adds}")
        if schema_adds:
            top = sorted({p.split(".")[0] + "." + p.split(".")[1] for p in schema_adds})
            print(f"      one-sided keys: {', '.join(top[:8])}")
    print(f"  -> {'PASS' if all_clean else 'FAIL'}")
    return all_clean


def exercise_gate(client, bucket: str, args) -> bool:
    """A1 must record common_source_events > 0 on at least one voyage."""
    print("== Gate 2: exercise (a1 common_source fired) ==")
    fired = 0
    seen = 0
    for seed in args.a1_seeds:
        rid = _RID.format(seed=seed)
        s = _fetch_summary(
            client, bucket, f"{args.canary_prefix}/{_A1_TIER}/{rid}"
        )
        if s is None:
            continue  # pending cell
        seen += 1
        mech = s.get("mechanisms") or {}
        ev = int(mech.get("common_source_events") or 0)
        takers = int(mech.get("common_source_takers") or 0)
        cg = int(mech.get("caregiver_responses") or 0)
        # Ground truth on pre-witness-fix zips: census telemetry.
        cen = _fetch_member_gz(
            client, bucket, f"{args.canary_prefix}/{_A1_TIER}/{rid}",
            "growth_census.json.gz",
        )
        tel = ((cen or {}).get("common_source") or {}).get("telemetry") or {}
        tel_events = int(sum(
            v for k, v in tel.items() if k.startswith("events_")
        ))
        if tel_events > 0:
            fired += 1
            print(
                f"  s{seed}: telemetry_events={tel_events} "
                f"(by_kind={ {k: int(v) for k, v in tel.items() if k.startswith('events_')} }) "
                f"takers={takers} caregiver_responses={cg}"
            )
        elif ev > 0:
            fired += 1
            print(
                f"  s{seed}: summary_events={ev} takers={takers} "
                f"caregiver_responses={cg}"
            )
        else:
            print(f"  s{seed}: 0 events (takers={takers})")
    pending = len(args.a1_seeds) - seen
    ok = fired > 0
    suffix = f" (+{pending} pending)" if pending else ""
    print(f"  -> {fired}/{seen} voyages fired{suffix} — {'PASS' if ok else 'FAIL'}")
    return ok


def memory_report(client, bucket: str, args) -> None:
    """RSS curve medians from rss_samples.json + summary rss_mb."""
    print("== Gate 3: peak-memory report ==")
    peaks, voyages, folds = [], [], []
    tiers = (
        (_A0ID_TIER, args.a0_seeds),
        (_A1_TIER, args.a1_seeds),
    )
    for tier, seeds in tiers:
        for seed in seeds:
            rid = _RID.format(seed=seed)
            key = f"{args.canary_prefix}/{tier}/{rid}"
            rss = _fetch_member_json(client, bucket, key, "rss_samples.json")
            s = _fetch_summary(client, bucket, key)
            if rss is not None:
                peaks.append(rss["peak_rss_mb"])
            if s is not None:
                rmb = s.get("rss_mb") or {}
                if rmb.get("voyage"):
                    voyages.append(rmb["voyage"])
                if rmb.get("fold"):
                    folds.append(rmb["fold"])
    if not peaks:
        print("  no rss_samples.json members yet")
        return
    med = statistics.median
    print(
        f"  n={len(peaks)}  voyage_rss med={med(voyages):.0f} MB  "
        f"fold_rss med={med(folds):.0f} MB  "
        f"peak med={med(peaks):.0f} MB  p90={sorted(peaks)[int(0.9*len(peaks))-1]:.0f} MB  "
        f"max={max(peaks):.0f} MB"
    )
    q = med(peaks)
    if q > 10240:
        print("  -> fleet quote: keep 16384 MB, cap concurrency ~30")
    else:
        rec = int(q * 1.3 // 512) * 512 + 512
        print(f"  -> fleet quote: {rec} MB/child (~30% headroom on median peak)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", default=BUCKET_DEFAULT)
    parser.add_argument(
        "--base-prefix",
        default="campaign/noro_mega_01/fl_mega_12d_scr",
        help="A0 zip prefix (no s3:// scheme, no trailing slash)",
    )
    parser.add_argument(
        "--canary-prefix",
        default="campaign/noro_mega_impact_01",
        help="canary parent prefix; tiers appended",
    )
    parser.add_argument("--a0-seeds", type=_parse_seed_range, default="8000:8009")
    parser.add_argument("--a1-seeds", type=_parse_seed_range, default="8000:8019")
    args = parser.parse_args(argv)
    args.base_prefix = args.base_prefix.removeprefix("s3://" + args.bucket + "/").rstrip("/")
    args.canary_prefix = args.canary_prefix.removeprefix("s3://" + args.bucket + "/").rstrip("/")
    client = _s3_client()
    g1 = bit_identity_gate(client, args.bucket, args)
    g2 = exercise_gate(client, args.bucket, args)
    memory_report(client, args.bucket, args)
    return 0 if (g1 and g2) else 1


if __name__ == "__main__":
    raise SystemExit(main())
