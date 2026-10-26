"""Internal worker transport for the campaign reducer (ticket D2).

This is the argv surface named by
``CANONICAL_INTERFACE.json["worker_transport"]``::

    python -m picard_framework.analysis.campaign_reducer.worker \
        --phase <phase> --request-uri <uri> --request-sha256 <sha> \
        --shard-index <n> [--out-uri <uri>]

The worker is the AWS-side projection/filter path's transport shim: on
Batch it will fetch the request from an immutable S3 URI and write to
the derived S3 namespace. Implemented and proven offline here —
``--request-uri`` accepts a local path (or ``file://``) and ``--out-uri``
a local directory (or ``dir://``); the same code paths run against
``MemoryDerivedStore`` in tests. No network, no boto3.

Exit codes follow the contract's table: 0 completed, 2 invalid contract,
3 access/resource blocked, 4 admission required/exceeded, 5 budget
stopped (checkpointed), 6 source changed, 7 schema/corruption
quarantine, 8 partial coverage, 9 return path blocked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .derived_store import DerivedStoreError, LocalDirStore, MemoryDerivedStore
from .ledger import BudgetBlocked, BudgetLedger, parse_ceilings
from .materialize import MaterializeSpec, run_materialization
from .pinned_reader import (
    GetResponse,
    HeadInfo,
    TransportError,
)
from .query_engine import QueryError, run_query
from .rows import ReductionContext, SourceSpec


class LocalTransport:
    """ObjectTransport over the local filesystem (offline worker path).

    Keys are paths confined under ``root`` (the request's
    ``source_root``, default the request file's own directory) — the
    offline shim never reads outside the declared fixture root. HEAD
    resolves existence/size/etag (sha256 of the body — deterministic,
    offline) and GET honors byte ranges, mirroring the test fakes.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / key.lstrip("/")).resolve()
        if path != self.root and self.root not in path.parents:
            raise TransportError("access_denied", key)
        if not path.is_file():
            raise TransportError("not_found", key)
        return path

    @staticmethod
    def _etag(body: bytes) -> str:
        return '"' + hashlib.sha256(body).hexdigest() + '"'

    def head(self, key: str) -> HeadInfo:
        body = self._path(key).read_bytes()
        return HeadInfo(
            content_length=len(body),
            etag=self._etag(body),
            version_id=None,
            storage_class="LOCAL",
            last_modified=None,
        )

    def get(
        self,
        key: str,
        *,
        start: int | None = None,
        end: int | None = None,
        version_id: str | None = None,
        if_match: str | None = None,
    ) -> GetResponse:
        body = self._path(key).read_bytes()
        etag = self._etag(body)
        if if_match is not None and if_match != etag:
            raise TransportError("precondition_failed", key, status=412)
        if start is None:
            return GetResponse(200, body, etag=etag)
        last = min(end, len(body) - 1)
        chunk = body[start : last + 1]
        return GetResponse(
            206, chunk,
            content_range=f"bytes {start}-{last}/{len(body)}", etag=etag,
        )

EXIT_COMPLETE = 0
EXIT_INVALID_CONTRACT = 2
EXIT_BLOCKED = 3
EXIT_ADMISSION = 4
EXIT_BUDGET_STOPPED = 5
EXIT_SOURCE_CHANGED = 6
EXIT_QUARANTINE = 7
EXIT_PARTIAL = 8
EXIT_RETURN_BLOCKED = 9


def _request_path(uri: str) -> Path:
    """Resolve the request URI to an existing regular file."""
    raw = uri[len("file://"):] if uri.startswith("file://") else uri
    path = Path(raw).resolve()
    if not path.is_file():
        raise QueryError("invalid_contract", f"request uri unreadable: {uri}")
    return path


def _fetch_request(uri: str) -> tuple[dict, Path]:
    """Read and parse the offline request document."""
    path = _request_path(uri)
    try:
        return json.loads(path.read_text()), path
    except (OSError, json.JSONDecodeError) as exc:
        raise QueryError("invalid_contract", f"request uri unreadable: {exc}")


def _open_store(out_uri: str | None):
    if not out_uri:
        return MemoryDerivedStore()
    if out_uri.startswith("dir://"):
        return LocalDirStore(out_uri[len("dir://"):])
    return LocalDirStore(out_uri)


def _verify_sha(doc: dict, expected: str) -> None:
    body = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
    actual = hashlib.sha256(body).hexdigest()
    if expected and actual != expected:
        raise QueryError(
            "invalid_contract",
            f"request sha256 {actual} != declared {expected}",
        )


def _ctx(request: dict, shard_index: int) -> ReductionContext:
    return ReductionContext(
        reduction_id=request.get("reduction_id") or "red-unknown",
        snapshot_id=request.get("snapshot_id") or "snap-unspecified",
        request_sha256=request.get("request_sha256") or "",
        inventory_sha256=request.get("inventory_sha256"),
        implementation_sha=request.get("implementation_sha") or "",
        adapter_registry_sha256=request.get("adapter_registry_sha256") or "",
        image_digest=request.get("image_digest") or "",
        phase=request.get("phase") or "materialize",
        admission_id=request.get("admission_id"),
        parent_reduction_id=request.get("parent_reduction_id"),
        discovery_root=request.get("discovery_root") or "",
        listing_start_utc=request.get("listing_start_utc") or "",
        listing_end_utc=request.get("listing_end_utc") or "",
        fingerprint=request.get("fingerprint") or "",
    )


def _sources(request: dict) -> list[SourceSpec]:
    return [
        SourceSpec(
            uri=s["uri"],
            family=s["family"],
            source_id=s.get("source_id") or f"src-{i}",
            campaign_id=s.get("campaign_id") or request.get("campaign_id", ""),
            seed=s.get("seed"),
            original_run_id=s.get("original_run_id"),
            hull_id=s.get("hull_id"),
            cell_id=s.get("cell_id"),
            engine_sha=s.get("engine_sha"),
            image_digest=s.get("image_digest"),
            attempt_id=s.get("attempt_id"),
            stage_id=s.get("stage_id"),
            attempt_kind=s.get("attempt_kind") or "unknown",
            scope_id=s.get("scope_id"),
            scope_delta=s.get("scope_delta") or "in_scope",
            declared_runs=s.get("declared_runs"),
        )
        for i, s in enumerate(request.get("sources") or [])
    ]


def _status_exit(status: str) -> int:
    return {
        "completed": EXIT_COMPLETE,
        "budget_stopped": EXIT_BUDGET_STOPPED,
        "source_changed": EXIT_SOURCE_CHANGED,
        "quarantined": EXIT_QUARANTINE,
        "partial": EXIT_PARTIAL,
        "blocked": EXIT_BLOCKED,
        "failed": EXIT_BLOCKED,
    }.get(status, EXIT_PARTIAL)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="campaign_reducer.worker")
    parser.add_argument("--phase", required=True,
                        choices=["materialize", "finalize", "query"])
    parser.add_argument("--request-uri", required=True)
    parser.add_argument("--request-sha256", default="")
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--out-uri", default="")
    parser.add_argument("--commit-uri", default="")
    args = parser.parse_args(argv)

    try:
        request, request_path = _fetch_request(args.request_uri)
        _verify_sha(request, args.request_sha256)
        ceilings = parse_ceilings(request.get("budgets"))
    except (QueryError, BudgetBlocked) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}))
        return EXIT_INVALID_CONTRACT if isinstance(exc, QueryError) else EXIT_ADMISSION
    store = _open_store(args.out_uri or None)
    ledger = BudgetLedger(ceilings)
    ctx = _ctx(request, args.shard_index)

    if args.phase in ("materialize", "finalize"):
        spec = MaterializeSpec(
            sources=_sources(request),
            ctx=ctx,
            shard_size=int(request.get("shard_size") or 64),
            requested_tables=tuple(request.get("requested_tables") or ()),
            metric_bindings=dict(request.get("metric_bindings") or {}),
            declared_source_count=request.get("declared_source_count"),
            partition_format=request.get("partition_format") or "jsonl",
            utc=request.get("utc") or "",
        )
        try:
            result = run_materialization(
                spec,
                LocalTransport(
                    request.get("source_root") or request_path.parent
                ),
                store, ledger,
            )
        except (DerivedStoreError, BudgetBlocked) as exc:
            print(json.dumps({"status": "blocked", "error": str(exc)}))
            return EXIT_BLOCKED
        print(json.dumps({"status": result.status,
                          "snapshot_id": result.snapshot_id}))
        return _status_exit(result.status)

    try:
        outcome = run_query(
            request.get("query") or request,
            store,
            ledger,
            commit_key=args.commit_uri or request.get("commit_uri") or "",
            reduction_id=ctx.reduction_id,
        )
    except QueryError as exc:
        print(json.dumps({"status": "blocked", "error": exc.detail}))
        return EXIT_INVALID_CONTRACT
    print(json.dumps({"status": outcome.status, "pages": len(outcome.pages)}))
    return _status_exit(outcome.status)


if __name__ == "__main__":
    sys.exit(main())
