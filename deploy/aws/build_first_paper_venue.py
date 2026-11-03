#!/usr/bin/env python3
"""Build the venue-pilot ``first_paper_scalar`` request + sources manifest.

Edison PHASE2_PILOT_SPEC counterfactual: 4 hulls x 2 venue-placement
arms x 4 seeds = 32 runs under the two campaign prefixes
``campaign/noro_provisioned_venue_01/`` (exp/cls/spr) and
``campaign/noro_provisioned_venue_01_mega/`` (meg). Scan rows all live
under the PARENT ``_scan_rows/`` prefix (mega rows are NOT under
``_mega/``) — same convention as the q-grid leg.

Reads the 8 scan-row files ``fl_{exp,cls,spr,meg}_12d_scr_q30_{crewv,paxv}``
and emits three pinned artifacts:

* ``red-fps02-venue-sources.json`` — cohort manifest (each scan row's
  ``key`` is the run zip's object key verbatim);
* ``red-fps02-venue-request.json`` — the ``crusher-reducer-spec/v1``
  worker request, extraction ``first_paper_scalar`` (contract
  ``first_paper_scalar/1.4.0`` — carries ``source_venue_arm``,
  ``actual_venues_used``, ``n_lots_placed``);
* ``red-fps02-venue-cohort.json`` — expected-vs-declared
  reconciliation the run report reconciles against measured coverage.

Canary cells are NOT in the cohort — the pilot's 32 cells are the
delivered set (canary seeds duplicate inside the arrays).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

BUCKET = "crusherbucket-994254241749-us-east-1-an"
CAMPAIGN = "noro_provisioned_venue_01"
SCAN_PREFIX = f"campaign/{CAMPAIGN}/_scan_rows"
ARMS = [
    f"fl_{hull}_12d_scr_q30_{arm}"
    for hull in ("exp", "cls", "spr", "meg")
    for arm in ("crewv", "paxv")
]
REDUCTION_ID = "red-fps02-venue"

# 32-run pilot: Phase-B measured actuals were ~92 KB compressed read per
# source (ranged summary.json member reads); the 45 MB zip bodies are
# referenced but never fetched whole. Ceilings carry >=5x headroom over
# the extrapolation; the $10 cap covers retries inside one attempt.
BUDGETS = {
    "max_list_pages": 40,
    "max_api_calls_total": 50000,
    "max_head_requests": 10000,
    "max_get_requests": 40000,
    "max_source_objects": 500,
    "max_source_object_bytes_referenced": 12000000000,
    "max_compressed_bytes_read": 1000000000,
    "max_uncompressed_bytes": 4000000000,
    "max_member_bytes": 8000000,
    "max_central_directory_bytes": 4000000,
    "max_output_bytes": 500000000,
    "max_spool_bytes": 2000000000,
    "max_wall_seconds": 7200,
    "max_queue_wait_seconds": 3600,
    "max_vcpu_seconds": 14400,
    "max_memory_mib_seconds": 36000000,
    "max_jobs": 1,
    "max_inflight_jobs": 1,
    "max_retries": 50,
    "max_cost_usd": 10.0,
    "checkpoint_reserve_bytes": 100000000,
    "checkpoint_reserve_seconds": 1800,
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
            "per-(hull,seed) arm pairs: crewv is the labelled baseline "
            "mirror of the delivered q30 allocation grammar pinned to "
            "crew-mess venues; paxv is the counterfactual. Pair on "
            "(hull_id, seed) — venue_venue_01 SEED_MANIFEST.json"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan-dir", required=True,
                    help="dir holding the 8 venue-pilot scan .jsonl files")
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
        "purpose": "Edison PHASE2_PILOT_SPEC venue-placement "
                   "counterfactual: first_paper_scalar/1.4.0 extraction "
                   "over the 32 provisioned-venue cells (4 hulls x "
                   "crew_venue/passenger_venue x 4 seeds); summary.json-"
                   "only member reads; budgets scaled from Phase-B "
                   "measured actuals with >=5x headroom; aggregate "
                   "$10 cap covers retries and the return leg",
        "reduction_id": REDUCTION_ID,
        "snapshot_id": f"snap-{REDUCTION_ID}",
        "source_root": f"s3://{args.bucket}/campaign/",
        "source_bucket": args.bucket,
        "utc": "2026-11-03T00:00:00Z",
        "shard_size": 8,
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
