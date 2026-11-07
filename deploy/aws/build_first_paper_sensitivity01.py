#!/usr/bin/env python3
"""Build the SENSITIVITY-01 ``first_paper_scalar`` request + sources manifest.

Paper-1 sensitivity screen (Child B): 16 Res-V profiles x 4 hulls x 3
venue arms = 192 cells under ``campaign/noro_provisioned_sensitivity_01/``
(exp/cls/spr) and ``…_01_mega/`` (meg). Each cell has a nested scout
block ``scout_<tier>`` (first 8 seeds) and a main block ``<tier>``.
Scan rows live under the PARENT ``_scan_rows/`` prefix as
``<block>.jsonl`` (mega rows are NOT under ``_mega/``), one file per
block of the requested wave.

Emits the same three pinned artifacts as ``build_first_paper_venue02.py``
(sources manifest, ``crusher-reducer-spec/v1`` request with extraction
``first_paper_scalar`` — contract 1.5.0 carries the role-checkpoint
columns — and the expected-vs-declared cohort), for either wave:

* ``--wave scout``: the 192 ``scout_<tier>`` blocks (8 seeds each).
* ``--wave main``: the 192 ``<tier>`` blocks (n-8 seeds each).

Canary children are not in the cohort (their zips sit under the same
``scout_<tier>/`` prefix at a seed the array also wrote; the scan rows
dedupe on key so a canary duplicate is never counted twice).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from campaigns.noro.provisioned_sensitivity_01.design.build import (  # noqa: E402
    ARMS,
    HULLS,
    PROFILES,
    tier_id,
)

BUCKET = "crusherbucket-994254241749-us-east-1-an"
CAMPAIGN = "noro_provisioned_sensitivity_01"
SCAN_PREFIX = f"campaign/{CAMPAIGN}/_scan_rows"
TIERS = [
    tier_id(hull, row["profile_id"], arm)
    for hull in HULLS for row in PROFILES for arm in ARMS
]

# Budgets scale from the venue-02 12k-source leg (measured 60k GETs,
# 12k HEADs, 1.09 GB compressed read, 586 MB output, 146 MB shard-0
# checkpoint): ~5 GETs + 1 HEAD + ~92 KB compressed per source.
BUDGETS_BY_WAVE = {
    "scout": {
        "max_source_objects": 2000, "max_api_calls_total": 30000,
        "max_head_requests": 5000, "max_get_requests": 25000,
        "max_compressed_bytes_read": 600_000_000,
        "max_uncompressed_bytes": 4_000_000_000,
        "max_output_bytes": 300_000_000, "max_cost_usd": 20.0,
    },
    "main": {
        "max_source_objects": 12000, "max_api_calls_total": 120000,
        "max_head_requests": 30000, "max_get_requests": 100000,
        "max_compressed_bytes_read": 2_000_000_000,
        "max_uncompressed_bytes": 16_000_000_000,
        "max_output_bytes": 1_000_000_000, "max_cost_usd": 100.0,
    },
}
BUDGETS_COMMON = {
    "max_list_pages": 200,
    "max_source_object_bytes_referenced": 1_500_000_000_000,
    "max_member_bytes": 8_000_000,
    "max_central_directory_bytes": 4_000_000,
    "max_spool_bytes": 16_000_000_000,
    "max_wall_seconds": 7200,
    "max_queue_wait_seconds": 7200,
    "max_vcpu_seconds": 28800,
    "max_memory_mib_seconds": 117964800,
    "max_jobs": 1,
    "max_inflight_jobs": 1,
    "max_retries": 500,
    "checkpoint_reserve_bytes": 300_000_000,
    "checkpoint_reserve_seconds": 3600,
    "safety_factor": 2.0,
}


def _canonical_sha(doc: dict) -> str:
    body = json.dumps(doc, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode()).hexdigest()


def blocks_for(wave: str) -> list[str]:
    prefix = "scout_" if wave == "scout" else ""
    return [f"{prefix}{tid}" for tid in TIERS]


def _scan_source(block: str, rows: int) -> dict:
    key = f"{SCAN_PREFIX}/{block}.jsonl"
    return {
        "uri": f"s3://{BUCKET}/{key}",
        "family": "observation_jsonl",
        "source_id": key,
        "campaign_id": CAMPAIGN,
        "cell_id": block,
        "declared_runs": rows,
        "source_role": "scan_rows",
    }


def _run_source(row: dict, block: str) -> dict:
    key = row["key"]
    return {
        "uri": f"s3://{BUCKET}/{key}",
        "family": "campaign_summary_zip",
        "source_id": key,
        "campaign_id": CAMPAIGN,
        "hull_id": row.get("hull"),
        "cell_id": block,
        "seed": row.get("seed"),
        "attempt_kind": "production",
        "declared_runs": 1,
    }


def _cohort(rows_by_block: dict[str, list[dict]]) -> dict:
    per_block = {}
    seen: dict[str, str] = {}
    duplicates = []
    for block, rows in rows_by_block.items():
        seeds = sorted(
            r["seed"] for r in rows if isinstance(r.get("seed"), int)
        )
        per_block[block] = {
            "declared": len(rows), "scanned": len(rows),
            "seed_min": seeds[0] if seeds else None,
            "seed_max": seeds[-1] if seeds else None,
        }
        for row in rows:
            key = row["key"]
            if key in seen:
                duplicates.append({"key": key, "kept_block": seen[key],
                                   "dup_block": block})
            else:
                seen[key] = block
    return {
        "expected_runs": sum(p["declared"] for p in per_block.values()),
        "per_block": per_block,
        "unique_keys": len(seen),
        "duplicate_keys": duplicates,
        "pairing": (
            "per-(hull, seed) across the 16 profiles x 3 arms of one hull; "
            "seed-paired to NORO-PROVISIONED-VENUE-02 (same ascending "
            "seed prefix per hull). Profile signs: "
            "campaigns/noro/provisioned_sensitivity_01/PROFILE_TABLE.md"
        ),
    }


def _read_rows(scan_dir: Path, block: str) -> list[dict]:
    path = scan_dir / f"{block}.jsonl"
    if not path.is_file():
        raise SystemExit(f"missing scan file {path}")
    rows = [json.loads(line) for line in
            path.read_text().splitlines() if line.strip()]
    bad = [r for r in rows if not str(r.get("key", "")).endswith(".zip")]
    if bad:
        raise SystemExit(f"{block}: {len(bad)} rows without a zip key — "
                         "aborting rather than silently excluding")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wave", choices=("scout", "main"), required=True)
    ap.add_argument("--reduction-id", required=True)
    ap.add_argument("--scan-dir", required=True,
                    help="dir holding one <block>.jsonl per block")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--utc", required=True, help="request timestamp")
    ap.add_argument("--bucket", default=BUCKET)
    args = ap.parse_args()

    scan_dir = Path(args.scan_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    blocks = blocks_for(args.wave)
    rows_by_block = {b: _read_rows(scan_dir, b) for b in blocks}

    manifest = {
        "schema": "crusher-reducer-sources/v1",
        "reduction_id": args.reduction_id,
        "sources": (
            [_scan_source(b, len(rows_by_block[b])) for b in blocks]
            + [_run_source(r, b) for b in blocks for r in rows_by_block[b]]
        ),
    }
    manifest_sha = _canonical_sha(manifest)
    (out_dir / f"{args.reduction_id}-sources.json").write_text(
        json.dumps(manifest, indent=1) + "\n", encoding="utf-8")

    n_runs = sum(len(v) for v in rows_by_block.values())
    request = {
        "schema": "crusher-reducer-spec/v1",
        "purpose": (
            f"Paper-1 sensitivity screen SENSITIVITY-01 {args.wave} wave: "
            f"first_paper_scalar/1.5.0 extraction over {n_runs} cells "
            "(16 Res-V profiles x 4 hulls x 3 venue arms, seed-paired to "
            "venue-02); summary.json-only member reads; raw per-cell "
            "vectors only, no effect analysis"),
        "reduction_id": args.reduction_id,
        "snapshot_id": f"snap-{args.reduction_id}",
        "source_root": f"s3://{args.bucket}/campaign/",
        "source_bucket": args.bucket,
        "utc": args.utc,
        "shard_size": 64,
        "declared_source_count": len(manifest["sources"]),
        "extraction_profile": "first_paper_scalar",
        "sources_uri": (
            f"s3://{args.bucket}/campaign/_derived/reducer/v1/"
            f"requests/{args.reduction_id}-sources.json"),
        "sources_sha256": manifest_sha,
        "budgets": {**BUDGETS_COMMON, **BUDGETS_BY_WAVE[args.wave]},
        "sources": [],
    }
    request_sha = _canonical_sha(request)
    (out_dir / f"{args.reduction_id}-request.json").write_text(
        json.dumps(request, indent=1) + "\n", encoding="utf-8")

    cohort = _cohort(rows_by_block)
    cohort["wave"] = args.wave
    cohort["sources_manifest_sha256"] = manifest_sha
    cohort["request_sha256"] = request_sha
    (out_dir / f"{args.reduction_id}-cohort.json").write_text(
        json.dumps(cohort, indent=1) + "\n", encoding="utf-8")
    print(f"{args.wave}: {len(blocks)} blocks, {n_runs} runs, "
          f"{len(manifest['sources'])} sources; request sha {request_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
