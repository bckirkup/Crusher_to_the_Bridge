"""NORO-FOOD-01 — common-source mechanism telemetry readout.

Aggregates the FOOD-COMMON-SOURCE-01 witness rows the census driver
harvests into ``growth_census.json.gz`` (``common_source_events`` /
``common_source_exposures`` / ``common_source_telemetry``) across the
run zips of a campaign prefix, plus the route-attribution fields in
``summary.json`` (``infections_by_dominant_route`` /
``infection_dose_share_by_route`` — ``common_source_food`` is the
mechanism's delivery route). Per cell it reports: fraction of voyages
with >=1 event, events/voyage distribution, source-arm mix,
takers/event, and dose credited via the pathway.

Reads only; no engine involvement. Output is a markdown table suitable
for the committed campaign readout.
"""

from __future__ import annotations

import argparse
import gzip
import json
import statistics as stats
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from outbreak_anchor_readout import (  # noqa: E402
    _cell_key,
    _cell_label,
    _s3_client,
    _s3_member_blob,
    seed_from_params,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from simulation_utils.paths import validated_open  # noqa: E402

_BUCKET_DEFAULT = "crusherbucket-994254241749-us-east-1-an"
_PREFIX_DEFAULT = "campaign/noro_food_01/"
_SUMMARY_MEMBER = "summary.json"
_CENSUS_MEMBER = "growth_census.json.gz"

_ARM_ORDER = ("provisioned_lot", "ill_handler", "ill_diner")


def _list_keys(client, bucket: str, prefix: str) -> list[str]:
    keys: list[str] = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(".zip"):
                keys.append(obj["Key"])
    return keys


def _tier_of(key: str, prefix: str) -> str:
    rest = key[len(prefix):]
    return rest.split("/", 1)[0]


def _fetch_voyage(client, bucket: str, key: str, prefix: str) -> dict | None:
    raw = _s3_member_blob(client, bucket, key, _CENSUS_MEMBER)
    if raw is None:
        return {"key": key, "error": "no census member"}
    census = json.loads(gzip.decompress(raw))
    sraw = _s3_member_blob(client, bucket, key, _SUMMARY_MEMBER)
    summary = json.loads(sraw) if sraw else {}
    params = summary.get("parameters", {})
    body = summary.get("summary", {})
    routes = body.get("infections_by_dominant_route") or {}
    shares = body.get("infection_dose_share_by_route") or {}
    telemetry = census.get("common_source_telemetry") or {}
    events = census.get("common_source_events") or []
    exposures = census.get("common_source_exposures") or []
    return {
        "key": key,
        "tier": _tier_of(key, prefix),
        "cell_key": _cell_key(params),
        "seed": seed_from_params(params),
        "n_events": len(events),
        "events": events,
        "n_exposures": len(exposures),
        "exposure_dose_sum": sum(
            float(e.get("dose", 0.0) or 0.0) for e in exposures
        ),
        "telemetry": telemetry,
        "cs_infections": int(routes.get("common_source_food", 0) or 0),
        "cs_dose_share": float(shares.get("common_source_food", 0.0) or 0.0),
        "routes": routes,
    }


def _pct(n: int, d: int) -> str:
    return f"{100.0 * n / d:.1f}" if d else "-"


def _median_or(xs: list[float], default: float = 0.0) -> float:
    return stats.median(xs) if xs else default


def _aggregate_cell(rows: list[dict]) -> dict:
    n = len(rows)
    event_counts = [r["n_events"] for r in rows]
    arm = Counter()
    takers = []
    dose_events = 0
    servings_dosed = 0
    for r in rows:
        for ev in r["events"]:
            arm[str(ev.get("source_kind") or "?")] += 1
            tk = int(ev.get("servings_taken", 0) or 0)
            takers.append(tk)
            if float(ev.get("per_serving_dose", 0.0) or 0.0) > 0.0:
                dose_events += 1
                servings_dosed += tk
    cs_inf = sum(r["cs_infections"] for r in rows)
    dose_credited = sum(
        float(r["telemetry"].get("dose_credited", 0.0) or 0.0)
        for r in rows
    )
    return {
        "voyages": n,
        "with_event": sum(1 for c in event_counts if c > 0),
        "events_total": sum(event_counts),
        "events_median": _median_or([float(c) for c in event_counts]),
        "events_p90": (
            sorted(event_counts)[int(0.9 * (n - 1))] if n else 0
        ),
        "events_max": max(event_counts, default=0),
        "arm": dict(arm),
        "takers_mean": (sum(takers) / len(takers)) if takers else 0.0,
        "zero_dose_events": sum(arm.values()) - dose_events,
        "servings_dosed": servings_dosed,
        "cs_infections": cs_inf,
        "dose_credited": dose_credited,
        "voyages_with_cs_infection": sum(
            1 for r in rows if r["cs_infections"] > 0
        ),
    }


def _arm_cell(arm: dict) -> str:
    total = sum(arm.values())
    if not total:
        return "-"
    parts = [
        f"{name.split('_', 1)[-1][0].upper()}{_pct(arm.get(name, 0), total)}"
        for name in _ARM_ORDER
    ]
    return "/".join(parts)


def render(cells: dict[tuple, dict]) -> str:
    lines = [
        "| cell | voyages | w/event | ev/voy med (p90,max) | arm L/H/D % |"
        " takers/ev | zero-dose ev | cs_food inf | dose credited |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for key in sorted(cells):
        c = cells[key]
        label = _cell_label(key)
        lines.append(
            f"| {label} | {c['voyages']} | {c['with_event']}"
            f" ({_pct(c['with_event'], c['voyages'])}%)"
            f" | {c['events_median']:g} ({c['events_p90']},{c['events_max']})"
            f" | {_arm_cell(c['arm'])}"
            f" | {c['takers_mean']:.1f}"
            f" | {c['zero_dose_events']}"
            f" | {c['cs_infections']}"
            f" ({c['voyages_with_cs_infection']} voy)"
            f" | {c['dose_credited']:.3g} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bucket", default=_BUCKET_DEFAULT)
    ap.add_argument("--prefix", action="append", dest="prefixes",
                    help="s3:// URI or bucket-relative prefix; repeatable")
    ap.add_argument("--limit", type=int, default=0,
                    help="cap zips read per tier (smoke)")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--out", help="Write the markdown table to this path")
    ap.add_argument("--json-out", help="Dump per-voyage rows JSON")
    args = ap.parse_args()

    prefixes = [
        p[len("s3://") + len(args.bucket) + 1:] if p.startswith("s3://")
        else p
        for p in (args.prefixes or [_PREFIX_DEFAULT])
    ]
    prefixes = [p.rstrip("/") + "/" for p in prefixes]

    client = _s3_client()
    rows: list[dict] = []
    errors = 0
    for prefix in prefixes:
        keys = _list_keys(client, args.bucket, prefix)
        if args.limit:
            by_tier: dict[str, list[str]] = defaultdict(list)
            for k in keys:
                by_tier[_tier_of(k, prefix)].append(k)
            keys = sorted(
                k for tier_keys in by_tier.values()
                for k in tier_keys[: args.limit]
            )
        print(f"{prefix}: {len(keys)} zips", file=sys.stderr)
        with ThreadPoolExecutor(args.workers) as pool:
            futs = [
                pool.submit(_fetch_voyage, client, args.bucket, k, prefix)
                for k in keys
            ]
            for i, fut in enumerate(as_completed(futs), 1):
                row = fut.result()
                if row and "error" not in row:
                    rows.append(row)
                else:
                    errors += 1
                if i % 500 == 0:
                    print(f"  {i}/{len(keys)} ({errors} errors)",
                          file=sys.stderr)
    print(f"read {len(rows)} voyages, {errors} errors", file=sys.stderr)

    cells: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        cells[tuple(r["cell_key"])].append(r)
    cell_agg = {k: _aggregate_cell(v) for k, v in cells.items()}
    md = render(cell_agg)
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
        dump = [{k: v for k, v in r.items() if k != "events"} for r in rows]
        with validated_open(
            str(args.json_out), "w",
            allowed_roots=(str(Path(args.json_out).parent.resolve()),),
            encoding="utf-8",
        ) as fh:
            json.dump(dump, fh, indent=1)
        print(f"wrote {args.json_out}", file=sys.stderr)


if __name__ == "__main__":
    main()
