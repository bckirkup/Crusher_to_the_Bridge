"""D4 synthetic fixtures — bootstrap/execution requests, receipts,
checkpoints, acks and a tiny materialized catalog.

All offline-rigged: built in memory or under the repo scratch dir, never
against AWS. The live values needed at canary time (queue/jobdef ARNs,
image digest) are placeholders here — the deploy runbook substitutes the
verified live binding recorded on issue #1086.
"""
from __future__ import annotations

import hashlib
import json

from zip_builders import build_zip, member

from picard_framework.analysis.campaign_reducer.ledger import (
    BUDGET_FIELDS,
    BudgetLedger,
    parse_ceilings,
)
from picard_framework.analysis.campaign_reducer.materialize import (
    DERIVED_ROOT,
    MaterializeSpec,
    run_materialization,
)
from picard_framework.analysis.campaign_reducer.pinned_reader import (
    MemoryTransport,
)
from picard_framework.analysis.campaign_reducer.rows import (
    ReductionContext,
    SourceSpec,
)

BUCKET = "crusherbucket-994254241749-us-east-1-an"
BOOTSTRAP_BUDGET_FIELDS = (
    "max_api_calls_total",
    "max_list_pages",
    "max_head_requests",
    "max_source_objects",
    "max_return_bytes",
    "max_wall_seconds",
    "max_cost_usd",
)


def sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def bootstrap_request(
    request_id: str = "req-d4", operation: str = "collect",
) -> dict:
    return {
        "schema_version": "crusher-campaign-distributions/1.0-proposed",
        "request_id": request_id,
        "operation": operation,
        "source_bucket": BUCKET,
        "source_roots_allowlist": ["campaign/"],
        "derived_exclude_prefixes": [f"{DERIVED_ROOT}/"],
        "scope_register_sha256": "a" * 64,
        "budgets": {f: 1000.0 for f in BOOTSTRAP_BUDGET_FIELDS},
        "admission": {
            "admission_id": "adm-d4",
            "approved_scope_hash": "b" * 64,
            "approved_cost_usd": 10.0,
            "expires_utc": "2030-01-01T00:00:00Z",
        },
        "price_snapshot": {
            "id": "price-1",
            "as_of_utc": "2026-01-01T00:00:00Z",
            "unit_prices_json": {"api_call_usd": 0.004},
        },
    }


def _budgets() -> dict:
    doc = dict.fromkeys(BUDGET_FIELDS, 1_000_000_000.0)
    doc["safety_factor"] = 1.5
    doc["max_retries"] = 4.0
    doc["max_inflight_jobs"] = 8.0
    return doc


def _readback() -> dict:
    return {
        "receipt_bytes": 262144,
        "summary_bytes": 1048576,
        "index_page_bytes": 1048576,
        "export_object_bytes": 5242880,
        "request_manifest_bytes": 1048576,
        "files_per_collect": 20,
        "total_bytes_per_collect": 52428800,
        "max_query_rows_per_page": 10000,
        "issue_envelope_bytes": 32768,
    }


def execution_request(
    reduction_id: str = "red-canary", phase: str = "query",
) -> dict:
    return {
        "schema_version": "crusher-campaign-distributions/1.0-proposed",
        "reduction_id": reduction_id,
        "parent_reduction_id": None,
        "purpose": "synthetic return canary",
        "implementation_sha": "c" * 64,
        "reducer_image_digest": "sha256:" + "d" * 64,
        "adapter_registry_sha256": "e" * 64,
        "scope_register_sha256": "f" * 64,
        "source_bucket": BUCKET,
        "derived_root": f"s3://{BUCKET}/{DERIVED_ROOT}/",
        "source_prefix_allowlist": ["campaign/camp1/"],
        "source_exclude_prefixes": [f"{DERIVED_ROOT}/"],
        "inventory_snapshot": {"id": "inv-1", "sha256": "0" * 64},
        "job_binding": {
            "queue_arn": "arn:aws:batch:us-east-1:994254241749:"
                         "job-queue/picard-analysis-queue",
            "job_definition_revision_arn":
                "arn:aws:batch:us-east-1:994254241749:"
                "job-definition/picard-reducer:1",
            "job_role_arn": "arn:aws:iam::994254241749:"
                            "role/picard-reducer-job-role",
            "execution_role_arn": "arn:aws:iam::994254241749:"
                                  "role/picard-campaign-execution-role",
            "image_digest": "sha256:" + "d" * 64,
            "platform": "EC2",
            "vcpu": 2,
            "memory_mib": 8192,
            "timeout_seconds": 3600,
        },
        "budgets": _budgets(),
        "readback": _readback(),
        "approval": {
            "admission_id": "adm-d4",
            "scope_hash": "b" * 64,
            "quote_id": "quote-1",
            "approved_cost_usd": 10.0,
            "expires_utc": "2030-01-01T00:00:00Z",
        },
        "phase": phase,
        "request_id": "req-exec-d4",
        "survey_source_sha": "496a919ca3af4563da34b958db37e737b58bab4b",
        "quote": {
            "quote_id": "quote-1",
            "uri": f"s3://{BUCKET}/campaign/_derived/reducer/v1/"
                  "quotes/quote-1.json",
            "sha256": "2" * 64,
            "price_snapshot_id": "price-1",
            "price_as_of_utc": "2026-01-01T00:00:00Z",
            "input_inventory_sha256": "0" * 64,
            "scope_hash": "b" * 64,
            "valid_until_utc": "2030-01-01T00:00:00Z",
            "estimates_json": {"total_usd": 0.01},
            "resource_bindings_json": {"queue": "picard-analysis-queue"},
        },
    }


def ceilings():
    return parse_ceilings(_budgets())


def attempt_receipt(
    reduction_id: str = "red-ok", status: str = "completed",
) -> dict:
    prefix = f"{DERIVED_ROOT}/attempts/{reduction_id}"
    return {
        "schema": "crusher-reducer-attempt-receipt/v1",
        "reduction_id": reduction_id,
        "fingerprint": "fp-1",
        "request_sha256": "3" * 64,
        "admission_id": "adm-d4",
        "github_run_id": "100",
        "github_attempt": "1",
        "phase": "materialize",
        "status": status,
        "batch_job_ids": ["job-1"],
        "jobdef_revision_arn": "arn:aws:batch:us-east-1:994254241749:"
                               "job-definition/picard-reducer:1",
        "image_digest": "sha256:" + "d" * 64,
        "catalog_uri": f"{prefix}/COMMIT.json",
        "catalog_hash": "snap-1",
        "summary_key": f"{prefix}/MANIFEST.json",
        "files_manifest_key": f"{prefix}/MANIFEST.json",
        "checkpoint_uri": None,
        "continuation": None,
        "output_counts": {"partitions": 1},
        "errors": [],
        "budget_spent": {},
        "budget_remaining": {},
        "start_utc": "2026-01-01T00:00:00Z",
        "end_utc": "2026-01-01T00:05:00Z",
    }


def manifest_entry(key: str, body: bytes) -> dict:
    return {
        "uri": f"s3://{BUCKET}/{key}",
        "sha256": sha(body),
        "bytes_stored": len(body),
    }


def files_manifest(entries: list[dict]) -> bytes:
    return json.dumps(
        {"manifest_id": "manifest-d4", "entries": entries}, indent=2,
    ).encode()


def checkpoint_doc(reduction_id: str = "red-canary", shard: int = 0) -> dict:
    return {
        "reduction_id": reduction_id,
        "shard": shard,
        "shard_count": None,
        "manifest_delta": [{"uri": "s3://x/y", "sha256": "4" * 64,
                            "bytes_stored": 10, "table_name": "t",
                            "rows": 1}],
        "ledger_spent": {"max_api_calls_total": 3.0},
        "table_counts_delta": {"t": 1},
        "utc": "2026-01-01T00:00:00Z",
    }


def ack_doc(**over) -> dict:
    doc = {
        "schema": "crusher-reducer-ack/v1",
        "receipt_id": "red-ok",
        "reduction_id": "red-ok",
        "project_asset_ids": ["asset-1"],
        "accepted_page_ids": [f"{DERIVED_ROOT}/attempts/red-ok/RECEIPT.json"],
        "artifact_sha256s": {},
    }
    doc.update(over)
    return doc


def query_doc(**over) -> dict:
    doc = {
        "contract_id": "crusher-campaign-distributions/1.0-proposed",
        "catalog_snapshot_id": "",
        "operation": "query",
        "analysis_version": "d4-test",
        "source_table": "run_scalars",
        "metric_ids": [],
        "filters": {"ne": ["row_id", "__never__"]},
        "group_by": [],
        "statistic": "exact_rows",
        "weight_set_id": "w-equal",
        "missing_policy": "report_separately",
        "max_export_rows": 100000,
        "max_export_bytes": 5 * 1024 * 1024,
        "page_rows": 10000,
        "allow_raw_agent_export": False,
        "scan_budget": {
            "max_scan_bytes": 10**9,
            "max_wall_seconds": 600,
            "max_cost_usd": 10.0,
        },
        "grain": "run",
        "joins": [],
        "order_by": ["native_path"],
        "continuation_token": None,
    }
    doc.update(over)
    return doc


def fused_zip() -> bytes:
    return build_zip([
        member("run_1/summary.json",
               json.dumps({"attack_rate": 0.5, "final_size": 12}).encode()),
        member("run_2/summary.json",
               json.dumps({"attack_rate": 0.25, "final_size": 7}).encode()),
        member("run_3/summary.json",
               json.dumps({"attack_rate": 0.1, "final_size": 3}).encode()),
    ])


def build_catalog(
    store, reduction_id: str = "red-canary", snapshot_id: str = "snap-canary",
):
    """Materialize a tiny fused zip into ``store``; returns the outcome."""
    transport = MemoryTransport()
    transport.put("fused.zip", fused_zip())
    ctx = ReductionContext(
        reduction_id=reduction_id, snapshot_id=snapshot_id,
    )
    spec = MaterializeSpec(
        sources=[SourceSpec(
            uri="fused.zip", family="campaign_summary_zip",
            source_id="fused.zip", campaign_id="camp1",
        )],
        ctx=ctx,
        utc="2026-01-01T00:00:00Z",
    )
    result = run_materialization(
        spec, transport, store, BudgetLedger(ceilings()),
    )
    assert result.status == "completed"
    return result
