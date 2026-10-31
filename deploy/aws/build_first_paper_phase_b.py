#!/usr/bin/env python3
"""Build the Phase B ``first_paper_scalar`` request + sources manifest.

Reads the eight Phase-B scan-row files (``fl_{exp,cls,spr,meg}_12d_scr_
{off,ps_ship}.jsonl``) and emits three pinned artifacts:

* ``red-fps01-b-sources.json`` — the cohort manifest the worker resolves
  through ``sources_uri``/``sources_sha256`` (each scan row's ``key``
  is the run zip's object key verbatim, so the 8,000-source cohort
  stays explicit instead of runtime-enumerated);
* ``red-fps01-b-request.json`` — the ``crusher-reducer-spec/v1`` worker
  request carrying real Phase-B budget ceilings;
* ``red-fps01-b-cohort.json`` — the expected-vs-declared reconciliation
  (per-arm counts, duplicate keys, within-hull off/ps_ship seed pairs)
  that the run report reconciles against measured coverage.

Pairs are matched within hull by seed only (off arm joins ps_ship on
``(hull, seed)``) — never forced.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

BUCKET = "crusherbucket-994254241749-us-east-1-an"
CAMPAIGN = "noro_provisioned_source_01"
SCAN_PREFIX = f"campaign/{CAMPAIGN}/_scan_rows"
ARMS = [
    "fl_exp_12d_scr_off",
    "fl_exp_12d_scr_ps_ship",
    "fl_cls_12d_scr_off",
    "fl_cls_12d_scr_ps_ship",
    "fl_spr_12d_scr_off",
    "fl_spr_12d_scr_ps_ship",
    "fl_meg_12d_scr_off",
    "fl_meg_12d_scr_ps_ship",
]
REDUCTION_ID = "red-fps01-b"

BUDGETS = {
    # ~24k ranged GETs + 8k HEADs + ~150 PUTs measured-quoted; the
    # ceilings below carry ~2-4x headroom and stay finite per the
    # worker spec (no 1e9 placeholders).
    "max_list_pages": 200,
    "max_api_calls_total": 120000,
    "max_head_requests": 30000,
    "max_get_requests": 100000,
    "max_source_objects": 12000,
    "max_source_object_bytes_referenced": 1500000000000,
    "max_compressed_bytes_read": 2000000000,
    "max_uncompressed_bytes": 16000000000,
    "max_member_bytes": 8000000,
    "max_central_directory_bytes": 4000000,
    "max_output_bytes": 1000000000,
    "max_spool_bytes": 16000000000,
    "max_wall_seconds": 7200,
    "max_queue_wait_seconds": 7200,
    "max_vcpu_seconds": 28800,
    "max_memory_mib_seconds": 117964800,
    "max_jobs": 1,
    "max_inflight_jobs": 1,
    "max_retries": 500,
    "max_cost_usd": 100.0,
    "checkpoint_reserve_bytes": 200000000,
    "checkpoint_reserve_seconds": 3600,
    "safety_factor": 2.0,
}


def _canonical_sha(doc: dict) -> str:
    body = json.dumps(doc, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode()).hexdigest()


def _scan_source(arm: str, rows: int) -> dict:
    key = f"{SCAN_PREFIX}/{arm}.jsonl"
    return {
        "uri": f"s3://{BUCKET}/{key}",
        "family": "observation_jsonl",
        "source_id": key,
        "campaign_id": CAMPAIGN,
        "cell_id": arm,
        "declared_runs": rows,
        "source_role": "scan_rows",
    }


def _run_source(row: dict, arm: str) -> dict:
    key = row["key"]
    return {
        "uri": f"s3://{BUCKET}/{key}",
        "family": "campaign_summary_zip",
        "source_id": key,
        "campaign_id": CAMPAIGN,
        "hull_id": row.get("hull"),
        "cell_id": arm,
        "seed": row.get("seed"),
        "attempt_kind": "production",
        "declared_runs": 1,
    }


def _cohort(rows_by_arm: dict[str, list[dict]]) -> dict:
    """Expected-vs-declared reconciliation: counts, dupes, seed pairs."""
    per_arm = {}
    seen: dict[str, str] = {}
    duplicates = []
    pairs = {}
    for arm, rows in rows_by_arm.items():
        per_arm[arm] = {"declared": len(rows), "scanned": len(rows)}
        hull, _, arm_name = arm.partition("_12d_scr_")
        for row in rows:
            key = row["key"]
            if key in seen:
                duplicates.append({"key": key,
                                   "kept_arm": seen[key],
                                   "dup_arm": arm})
            else:
                seen[key] = arm
            if arm_name == "off":
                pair_key = (row.get("hull"), row.get("seed"))
                pairs.setdefault(pair_key, {"off": key})
            elif arm_name == "ps_ship":
                pair_key = (row.get("hull"), row.get("seed"))
                pairs.setdefault(pair_key, {})["ps_ship"] = key
    paired = sum(1 for p in pairs.values() if "off" in p and "ps_ship" in p)
    unpaired = {f"{h}:{s}": sorted(p) for (h, s), p in pairs.items()
                if len(p) != 2}
    return {
        "expected_runs": sum(p["declared"] for p in per_arm.values()),
        "per_arm": per_arm,
        "unique_keys": len(seen),
        "duplicate_keys": duplicates,
        "within_hull_seed_pairs_declared": len(pairs),
        "pairs_complete": paired,
        "pairs_incomplete": unpaired,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan-dir", required=True,
                    help="dir holding the 8 Phase-B scan .jsonl files")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--bucket", default=BUCKET)
    args = ap.parse_args()

    scan_dir = Path(args.scan_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows_by_arm: dict[str, list[dict]] = {}
    for arm in ARMS:
        path = scan_dir / f"{arm}.jsonl"
        if not path.is_file():
            raise SystemExit(f"missing scan file {path}")
        rows = [json.loads(line) for line in
                path.read_text().splitlines() if line.strip()]
        bad = [r for r in rows
               if not str(r.get("key", "")).endswith(".zip")]
        if bad:
            raise SystemExit(
                f"{arm}: {len(bad)} rows without a zip key — "
                "aborting rather than silently excluding")
        rows_by_arm[arm] = rows

    manifest = {
        "schema": "crusher-reducer-sources/v1",
        "reduction_id": REDUCTION_ID,
        "sources": (
            [_scan_source(arm, len(rows_by_arm[arm])) for arm in ARMS]
            + [src for arm in ARMS
               for src in (_run_source(r, arm)
                           for r in rows_by_arm[arm])]
        ),
    }
    manifest_sha = _canonical_sha(manifest)

    sources_path = out_dir / f"{REDUCTION_ID}-sources.json"
    sources_path.write_text(
        json.dumps(manifest, indent=1) + "\n", encoding="utf-8")

    request = {
        "schema": "crusher-reducer-spec/v1",
        "purpose": "Phase B first_paper_scalar extraction over the "
                   "four-hull off/ps_ship cohort (8,000 declared)",
        "reduction_id": REDUCTION_ID,
        "snapshot_id": f"snap-{REDUCTION_ID}",
        "source_root": f"s3://{args.bucket}/campaign/",
        "source_bucket": args.bucket,
        "utc": "2026-10-31T00:00:00Z",
        "shard_size": 64,
        "declared_source_count": len(manifest["sources"]),
        "extraction_profile": "first_paper_scalar",
        "sources_uri": (
            f"s3://{args.bucket}/campaign/_derived/reducer/v1/"
            f"requests/{REDUCTION_ID}-sources.json"),
        "sources_sha256": manifest_sha,
        "budgets": BUDGETS,
        "sources": [],
    }
    request_sha = _canonical_sha(request)
    request_path = out_dir / f"{REDUCTION_ID}-request.json"
    request_path.write_text(
        json.dumps(request, indent=1) + "\n", encoding="utf-8")

    cohort = _cohort(rows_by_arm)
    cohort["sources_manifest_sha256"] = manifest_sha
    cohort["request_sha256"] = request_sha
    (out_dir / f"{REDUCTION_ID}-cohort.json").write_text(
        json.dumps(cohort, indent=1) + "\n", encoding="utf-8")

    print(json.dumps({
        "sources": len(manifest["sources"]),
        "manifest_sha256": manifest_sha,
        "request_sha256": request_sha,
        "expected_runs": cohort["expected_runs"],
        "pairs_complete": cohort["pairs_complete"],
        "pairs_incomplete": len(cohort["pairs_incomplete"]),
        "duplicates": len(cohort["duplicate_keys"]),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
