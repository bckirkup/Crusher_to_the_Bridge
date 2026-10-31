"""COMMIT-bound catalog snapshot reader (ticket D2).

A ``Catalog`` is the frozen artifact a bounded query runs against: the
``COMMIT.json`` doc plus every partition it names, verified against the
manifest's recorded sha256 before a row is trusted. Paging cursors bind
to ``catalog_snapshot_id`` — a different commit is a different snapshot
and continuation fails closed.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from .derived_store import DerivedStoreError
from .identity import sha256_hex
from .materialize import decode_rows


class CatalogError(Exception):
    def __init__(self, kind: str, detail: str):
        super().__init__(f"{kind}: {detail}")
        self.kind = kind
        self.detail = detail


@dataclass
class Catalog:
    snapshot_id: str
    commit: dict
    partitions: list[dict]
    tables: dict[str, list[dict]] = field(default_factory=dict)

    def rows(self, table: str) -> list[dict]:
        return self.tables.get(table, [])


def _partition_format(uri: str) -> str:
    if uri.endswith(".parquet"):
        return "parquet"
    return "jsonl"


def load_catalog(store, commit_key: str) -> Catalog:
    """Read a COMMIT and all its partitions; verify every sha256."""
    try:
        commit = json.loads(store.get(commit_key))
    except DerivedStoreError as exc:
        raise CatalogError("commit_missing", commit_key) from exc
    partitions = commit.get("partitions") or []
    tables: dict[str, list[dict]] = {}
    for entry in partitions:
        uri = entry["uri"]
        try:
            body = store.get(uri)
        except DerivedStoreError as exc:
            raise CatalogError("partition_missing", uri) from exc
        if sha256_hex(body) != entry.get("sha256"):
            raise CatalogError("partition_corrupt", uri)
        fmt = _partition_format(uri)
        rows = decode_rows(body, fmt)
        tables.setdefault(entry["table_name"], []).extend(rows)
    return Catalog(
        snapshot_id=commit.get("catalog_snapshot_id", ""),
        commit=commit,
        partitions=partitions,
        tables=tables,
    )


def query_page_row(
    *, reduction_id: str, query_id: str, page_id: str, snapshot_id: str,
    query_sha256: str, uri: str, sha256: str, returned_rows: int,
    scanned: tuple[int, int], complete: bool,
    next_cursor, selection_counts: dict, oversized_rows: list,
) -> dict:
    """One ``query_pages`` row — written alongside every page artifact."""
    return {
        "row_id": f"qp-{page_id}",
        "reduction_id": reduction_id,
        "query_id": query_id,
        "page_id": page_id,
        "catalog_snapshot_id": snapshot_id,
        "query_sha256": query_sha256,
        "uri": uri,
        "sha256": sha256,
        "returned_rows": returned_rows,
        "scanned_rows": scanned[0],
        "scanned_bytes": scanned[1],
        "complete": complete,
        "next_cursor_json": next_cursor,
        "selection_counts_json": selection_counts,
        "oversized_rows_json": oversized_rows,
    }


def receipt_row(
    *, reduction_id: str, request_id: str, receipt_id: str, status: str,
    catalog_uri: str, catalog_sha256: str, budget: dict, error: dict | None,
    continuation: dict | None, created_utc: str, receipt_uri: str,
    receipt_sha256: str, batch_job_ids: list | None = None,
) -> dict:
    """One ``receipts`` row — the bounded return-path record."""
    return {
        "row_id": f"rc-{receipt_id}",
        "reduction_id": reduction_id,
        "receipt_id": receipt_id,
        "request_id": request_id,
        "status": status,
        "catalog_uri": catalog_uri,
        "catalog_sha256": catalog_sha256,
        "budget_json": budget,
        "error_json": error,
        "continuation_json": continuation,
        "created_utc": created_utc,
        "receipt_uri": receipt_uri,
        "receipt_sha256": receipt_sha256,
        "batch_job_ids_json": batch_job_ids or [],
        "github_run_id": None,
        "github_attempt": None,
    }
