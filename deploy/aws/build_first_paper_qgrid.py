#!/usr/bin/env python3
"""Build the q-grid ``first_paper_scalar`` request + sources manifest.

Reads the 38 q-grid scan-row files — ``fl_{exp,cls,spr}_12d_scr_
{q01,q02,q03,q05,q08,q15,q30,ind,ship,mint}`` (30) plus
``fl_meg_12d_scr_{q01,...,q30,ind}`` (8), all under the parent
``campaign/noro_provisioned_source_01/_scan_rows/`` prefix (mega scan
rows are NOT under ``_mega/``) — and emits three pinned artifacts:

* ``red-fps01-qgrid-sources.json`` — the cohort manifest the worker
  resolves through ``sources_uri``/``sources_sha256`` (each scan row's
  ``key`` is the run zip's object key verbatim, so the 38,000-source
  cohort stays explicit instead of runtime-enumerated);
* ``red-fps01-qgrid-request.json`` — the ``crusher-reducer-spec/v1``
  worker request carrying Phase-B-scaled budget ceilings;
* ``red-fps01-qgrid-cohort.json`` — the expected-vs-declared
  reconciliation (per-arm counts, duplicate keys, seed ranges) that the
  run report reconciles against measured coverage.

Unlike Phase B there is no within-hull arm pairing: off/ps_ship are
already accepted (red-fps01-b2) and the q-grid arms join scientific
groups only through ``tier_id``/``platform_id`` on each row — one
``reduction_id`` for all 38 arms, per the Edison-approved scope.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

BUCKET = "crusherbucket-994254241749-us-east-1-an"
CAMPAIGN = "noro_provisioned_source_01"
SCAN_PREFIX = f"campaign/{CAMPAIGN}/_scan_rows"
Q_ARMS = ["q01", "q02", "q03", "q05", "q08", "q15", "q30"]
ARMS = (
    [f"fl_{hull}_12d_scr_{arm}"
     for hull in ("exp", "cls", "spr")
     for arm in Q_ARMS + ["ind", "ship", "mint"]]
    + [f"fl_meg_12d_scr_{arm}" for arm in Q_ARMS + ["ind"]]
)
REDUCTION_ID = "red-fps01-qgrid"

# Phase-B measured actuals (8,008 sources): 738 MB compressed read,
# 663 MB output, 3.16 GB uncompressed, 40,017 GET + 8,008 HEAD,
# 88.4 vCPU-min single-job. The 38-arm cohort scales ~4.75x:
# ~3.5 GB read / ~15 GB uncompressed / ~3.2 GB output / ~7 vCPU-h.
# Ceilings below carry >=2x headroom over the extrapolation; the
# aggregate $100 covers the retry storm inside a single attempt.
BUDGETS = {
    "max_list_pages": 200,
    "max_api_calls_total": 600000,
    "max_head_requests": 120000,
    "max_get_requests": 500000,
    "max_source_objects": 50000,
    "max_source_object_bytes_referenced": 4000000000000,
    "max_compressed_bytes_read": 8000000000,
    "max_uncompressed_bytes": 40000000000,
    "max_member_bytes": 8000000,
    "max_central_directory_bytes": 4000000,
    "max_output_bytes": 6500000000,
    "max_spool_bytes": 40000000000,
    "max_wall_seconds": 21600,
    "max_queue_wait_seconds": 7200,
    "max_vcpu_seconds": 60000,
    "max_memory_mib_seconds": 176947200,
    "max_jobs": 1,
    "max_inflight_jobs": 1,
    "max_retries": 500,
    "max_cost_usd": 100.0,
    "checkpoint_reserve_bytes": 1000000000,
    "checkpoint_reserve_seconds": 7200,
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
    """Expected-vs-declared reconciliation: counts, dupes, seed spans."""
    per_arm = {}
    seen: dict[str, str] = {}
    duplicates = []
    for arm, rows in rows_by_arm.items():
        seeds = sorted(
            r["seed"] for r in rows if isinstance(r.get("seed"), int)
        )
        per_arm[arm] = {
            "declared": len(rows),
            "scanned": len(rows),
            "seed_min": seeds[0] if seeds else None,
            "seed_max": seeds[-1] if seeds else None,
        }
        for row in rows:
            key = row["key"]
            if key in seen:
                duplicates.append({"key": key,
                                   "kept_arm": seen[key],
                                   "dup_arm": arm})
            else:
                seen[key] = arm
    return {
        "expected_runs": sum(p["declared"] for p in per_arm.values()),
        "per_arm": per_arm,
        "unique_keys": len(seen),
        "duplicate_keys": duplicates,
        "pairing": (
            "none — q-grid arms join scientific groups via tier_id/"
            "platform_id on each row; off/ps_ship pairing lives in the "
            "accepted red-fps01-b2 tranche"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan-dir", required=True,
                    help="dir holding the 38 q-grid scan .jsonl files")
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
        "purpose": "Q-grid first_paper_scalar/1.3.0 extraction over the "
                   "38 provisioned-source arm-sets (38,000 declared); "
                   "summary.json-only member reads; observed-window "
                   "witness fields; budgets scaled from Phase-B "
                   "measured actuals with >=2x headroom; aggregate "
                   "$100 cap covers retries and the return leg",
        "reduction_id": REDUCTION_ID,
        "snapshot_id": f"snap-{REDUCTION_ID}",
        "source_root": f"s3://{args.bucket}/campaign/",
        "source_bucket": args.bucket,
        "utc": "2026-11-01T00:00:00Z",
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
        "unique_keys": cohort["unique_keys"],
        "duplicates": len(cohort["duplicate_keys"]),
        "arms": len(ARMS),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
