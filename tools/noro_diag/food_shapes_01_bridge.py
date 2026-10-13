#!/usr/bin/env python3
"""NORO-FOOD-SHAPES-01 bit-identity bridge check (design §7.4 gate 5).

The frozen bridges pair wave-1 cells with the ENTRAIN-01 grid at
``dbbd5395`` on identical seed lists:

- ``ind_bg`` vs ``campaign/noro_entrain_01/fl_exp_12d_scr_ind``
- ``bg``    vs ``campaign/noro_entrain_01/fl_exp_12d_scr_ship``
- ``off``   vs ``campaign/noro_entrain_01/fl_exp_12d_scr_off``

Per seed, ``summary.json`` is fetched (ranged read) from both campaigns
and compared as parsed JSON after dropping the declared field-level
exceptions — ``parameters.common_source`` (the arm's own override
echo), ``parameters.engine_git_sha``/``parameters.tier_id`` (image +
tier naming) and ``rss_mb`` (runtime memory). Every other key must be
identical; the voyage's ``summary``/``mechanisms``/``timeseries``/
``derived``/``initiation`` blocks are the output contract.

Optionally (``--census-sample N``), the census member of N evenly
spaced seeds is decompressed and compared after normalizing numeric
literals to 12 significant digits — the cross-image serializer can
drift a mass-balance accumulator by ~1 ULP; anything larger is a real
RNG/content divergence and reported.

Emits one JSONL row per seed pair + a summary table on stdout.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from outbreak_anchor_readout import _s3_client, _s3_member_blob  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from simulation_utils.paths import validated_open  # noqa: E402

_BUCKET_DEFAULT = "crusherbucket-994254241749-us-east-1-an"
_SUMMARY_MEMBER = "summary.json"
_CENSUS_MEMBER = "growth_census.json.gz"

# Declared exceptions: fields that legitimately differ between the two
# campaigns' zips even when the voyage is bit-identical.
_DROP_PARAM_KEYS = ("common_source", "engine_git_sha", "tier_id")
_DROP_TOP_KEYS = ("rss_mb",)

_BRIDGES = (
    ("ind_bg", "campaign/noro_food_shapes_01/fl_exp_12d_scr_ind_bg",
     "campaign/noro_entrain_01/fl_exp_12d_scr_ind"),
    ("bg", "campaign/noro_food_shapes_01/fl_exp_12d_scr_bg",
     "campaign/noro_entrain_01/fl_exp_12d_scr_ship"),
    ("off", "campaign/noro_food_shapes_01/fl_exp_12d_scr_off",
     "campaign/noro_entrain_01/fl_exp_12d_scr_off"),
)

# Census floats drift by ~1 ULP across the two engine images' serializers
# (mass-balance accumulators); the tolerant leaf compare below holds that
# same bar (~12 significant digits) without regex normalization.
_CENSUS_TOL = 1e-12


def _index_prefix(client, bucket: str, prefix: str) -> dict[int, str]:
    out: dict[int, str] = {}
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            k = obj["Key"]
            if not k.endswith(".zip"):
                continue
            m = re.search(r"_s(\d+)\.zip$", k)
            if m:
                out[int(m.group(1))] = k
    return out


def _summary_norm(summary: dict) -> dict:
    s = dict(summary)
    params = dict(s.get("parameters") or {})
    for k in _DROP_PARAM_KEYS:
        params.pop(k, None)
    s["parameters"] = params
    for k in _DROP_TOP_KEYS:
        s.pop(k, None)
    return s


def _is_num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _leaf_diff(a, b, path: str, diffs: list[str], tol: float) -> None:
    if _is_num(a) and _is_num(b):
        if a != b and not math.isclose(a, b, rel_tol=tol):
            diffs.append(f"{path or '<root>'} ({a} vs {b})")
    elif a != b:
        diffs.append(path or "<root>")


def _diff_key(a: dict, b: dict, k, path: str, diffs: list[str],
              tol: float, cap: int) -> None:
    if k not in a:
        diffs.append(f"{path}.{k} (only in B)")
    elif k not in b:
        diffs.append(f"{path}.{k} (only in A)")
    else:
        _diff_keys(a[k], b[k], f"{path}.{k}", diffs, tol, cap)


def _diff_keys(a, b, path: str = "", diffs: list[str] | None = None,
               tol: float = 0.0, cap: int = 40) -> list[str]:
    """Paths where the two parsed structures differ (capped first-
    divergence walk, not exhaustive). `tol` is the relative tolerance
    for numeric leaves (0 = exact)."""
    if diffs is None:
        diffs = []
    if len(diffs) >= cap:
        return diffs
    if type(a) is not type(b):
        diffs.append(path or "<root>")
    elif isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if len(diffs) >= cap:
                break
            _diff_key(a, b, k, path, diffs, tol, cap)
    elif isinstance(a, list):
        if len(a) != len(b):
            diffs.append(f"{path} (len {len(a)} vs {len(b)})")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                if len(diffs) >= cap:
                    break
                if x != y:
                    _diff_keys(x, y, f"{path}[{i}]", diffs, tol, cap)
    else:
        _leaf_diff(a, b, path, diffs, tol)
    return diffs


def _check_seed(
    client, bucket: str, key_a: str, key_b: str, do_census: bool,
) -> dict:
    row: dict = {"key_a": key_a, "key_b": key_b}
    blob_a = _s3_member_blob(client, bucket, key_a, _SUMMARY_MEMBER)
    blob_b = _s3_member_blob(client, bucket, key_b, _SUMMARY_MEMBER)
    if blob_a is None or blob_b is None:
        row["verdict"] = "missing_member"
        return row
    sa = _summary_norm(json.loads(blob_a))
    sb = _summary_norm(json.loads(blob_b))
    if sa == sb:
        row["verdict"] = "identical"
        row["diffs"] = []
    else:
        row["verdict"] = "diverged"
        row["diffs"] = _diff_keys(sa, sb)[:40]
    if do_census:
        ca = _s3_member_blob(client, bucket, key_a, _CENSUS_MEMBER)
        cb = _s3_member_blob(client, bucket, key_b, _CENSUS_MEMBER)
        if ca is None or cb is None:
            row["census"] = "missing_member"
        else:
            try:
                da = json.loads(gzip.decompress(ca))
                db = json.loads(gzip.decompress(cb))
            except (OSError, ValueError) as exc:
                row["census"] = f"parse: {exc}"
            else:
                cdiffs = _diff_keys(da, db, tol=_CENSUS_TOL)
                row["census"] = (
                    "identical" if not cdiffs else "diverged"
                )
                if cdiffs:
                    row["census_first_diff"] = cdiffs[:5]
    return row


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bucket", default=_BUCKET_DEFAULT)
    ap.add_argument("--out", required=True, help="JSONL rows output")
    ap.add_argument(
        "--census-sample", type=int, default=0,
        help="also compare decompressed census members on N seeds",
    )
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()
    client = _s3_client()
    rows: list[dict] = []
    for arm, p_w1, p_old in _BRIDGES:
        idx_w1 = _index_prefix(client, args.bucket, p_w1 + "/")
        idx_old = _index_prefix(client, args.bucket, p_old + "/")
        seeds = sorted(set(idx_w1) & set(idx_old))
        missing_w1 = sorted(set(idx_old) - set(idx_w1))
        missing_old = sorted(set(idx_w1) - set(idx_old))
        census_seeds = set()
        if args.census_sample:
            step = max(1, len(seeds) // args.census_sample)
            census_seeds = set(seeds[::step])
        with ThreadPoolExecutor(args.workers) as pool:
            futs = {
                pool.submit(
                    _check_seed, client, args.bucket,
                    idx_w1[s], idx_old[s], s in census_seeds,
                ): s
                for s in seeds
            }
            for fut in as_completed(futs):
                s = futs[fut]
                row = fut.result()
                row["arm"] = arm
                row["seed"] = s
                rows.append(row)
        n_div = sum(1 for r in rows if r["arm"] == arm
                    and r["verdict"] == "diverged")
        print(
            f"{arm}: {len(seeds)} paired seeds, {n_div} diverged "
            f"(missing w1:{len(missing_w1)} old:{len(missing_old)})",
            file=sys.stderr,
        )
        if missing_w1 or missing_old:
            rows.append({
                "arm": arm, "verdict": "key_missing",
                "missing_w1": missing_w1, "missing_old": missing_old,
            })
    out_path = Path(args.out)
    with validated_open(
        str(out_path),
        "w",
        encoding="utf-8",
        allowed_roots=(str(out_path.parent.resolve()),),
    ) as fh:
        for r in sorted(rows, key=lambda r: (r["arm"], r.get("seed", 0))):
            fh.write(json.dumps(r) + "\n")
    print("\n| arm | paired | identical | diverged | census n |"
          " census identical |")
    print("|---|---|---|---|---|---|")
    for arm, _, _ in _BRIDGES:
        ar = [r for r in rows if r["arm"] == arm and r.get("seed")]
        cen = [r for r in ar if r.get("census")]
        print(
            f"| {arm} | {len(ar)} |"
            f" {sum(1 for r in ar if r['verdict'] == 'identical')} |"
            f" {sum(1 for r in ar if r['verdict'] == 'diverged')} |"
            f" {len(cen)} |"
            f" {sum(1 for r in cen if r['census'] == 'identical')} |"
        )


if __name__ == "__main__":
    main()
