"""Internal worker transport for the campaign reducer (ticket D2).

This is the argv surface named by
``CANONICAL_INTERFACE.json["worker_transport"]``::

    python -m picard_framework.analysis.campaign_reducer.worker \
        --phase <phase> --request-uri <uri> --request-sha256 <sha> \
        --shard-index <n> [--out-uri <uri>]

The worker is the AWS-side projection/filter path's transport shim: on
Batch it fetches the request from an immutable S3 URI, reads sources
through the pinned boto3 transport, and writes to the derived S3
namespace. ``--request-uri`` accepts ``s3://bucket/key``, a local path,
or ``file://``; ``--out-uri`` accepts ``s3://bucket/prefix`` (create-only
``S3DerivedStore``), a local directory, or ``dir://``; the same code
paths run against ``MemoryDerivedStore``/stubbed client objects in
tests. boto3 imports stay lazy inside ``_s3_client`` so offline runs
never touch the SDK.

Exit codes follow the contract's table: 0 completed, 2 invalid contract,
3 access/resource blocked, 4 admission required/exceeded, 5 budget
stopped (checkpointed), 6 source changed, 7 schema/corruption
quarantine, 8 partial coverage, 9 return path blocked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

from simulation_utils.paths import confine_to_base

from .._io import cwd_root
from .derived_store import DerivedStoreError, LocalDirStore, MemoryDerivedStore
from .ledger import (
    BudgetBlocked,
    BudgetExceeded,
    BudgetLedger,
    parse_ceilings,
)
from .materialize import DERIVED_ROOT, MaterializeSpec, run_materialization
from .pinned_reader import (
    STATE_AVAILABLE,
    GetResponse,
    HeadInfo,
    ReadBudget,
    TransportError,
    boto3_transport,
    parse_s3_uri,
    read_object,
)
from .query_engine import QueryError, run_query
from .rows import ReductionContext, SourceSpec
from .s3_store import S3DerivedStore

# CANONICAL_INTERFACE readback cap for the request manifest itself.
_REQUEST_MANIFEST_MAX_BYTES = 1048576

# Cap on the pinned ``sources_uri`` cohort manifest the request may
# point at (the request itself stays under the 1 MiB readback cap).
_SOURCES_MANIFEST_MAX_BYTES = 16 * 1024 * 1024


class LocalTransport:
    """ObjectTransport over the local filesystem (offline worker path).

    Keys are paths confined under ``root`` (the request's
    ``source_root``, default the request file's own directory) — the
    offline shim never reads outside the declared fixture root. HEAD
    resolves existence/size/etag (sha256 of the body — deterministic,
    offline) and GET honors byte ranges, mirroring the test fakes.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()

    def _path(self, key: str) -> Path:
        key_path = Path(key.lstrip("/"))
        if key_path.is_absolute() or ".." in key_path.parts:
            raise TransportError("access_denied", key)
        path = (self.root / key_path).resolve()
        try:
            path.relative_to(self.root)
        except ValueError:
            raise TransportError("access_denied", key) from None
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


def _s3_client():
    """Build the S3 client; lazy boto3 import keeps offline runs clean.

    Tests substitute a stubbed client object by monkeypatching this
    factory — no moto, no network.
    """
    import boto3  # noqa: PLC0415

    return boto3.client("s3")


def _request_path(uri: str) -> Path:
    """Resolve the request URI to a file confined to the working root.

    Canonicalize-then-validate (S8707/S6549): an escape is denied
    before any filesystem access, and the read itself reports
    "unreadable" through the caller's OSError wrap.
    """
    raw = uri[len("file://"):] if uri.startswith("file://") else uri
    try:
        return Path(confine_to_base(cwd_root(), raw))
    except ValueError as exc:
        raise QueryError("access_denied", str(exc)) from exc


def _fetch_request_s3(uri: str) -> dict:
    """Read the request document through the pinned boto3 transport.

    Bounded by the canonical request-manifest readback cap (1 MiB) and
    pinned to the VersionId/ETag HEAD reports — the immutable-URI rule.
    """
    bucket, key = parse_s3_uri(uri)
    if not key:
        raise QueryError("invalid_contract", f"request uri has no key: {uri}")
    transport = boto3_transport(_s3_client(), bucket)
    budget = ReadBudget(
        max_total_bytes=_REQUEST_MANIFEST_MAX_BYTES,
        max_object_bytes=_REQUEST_MANIFEST_MAX_BYTES,
    )
    outcome = read_object(transport, bucket, key, budget)
    if outcome.state != STATE_AVAILABLE or outcome.body is None:
        raise QueryError(
            "access_denied",
            f"request fetch blocked: {outcome.state} {outcome.detail}",
        )
    try:
        return json.loads(outcome.body)
    except json.JSONDecodeError as exc:
        raise QueryError("invalid_contract", f"request uri unreadable: {exc}")


def _fetch_request(uri: str) -> tuple[dict, Path | None]:
    """Read and parse the request document (local or immutable S3 URI)."""
    if uri.startswith("s3://"):
        return _fetch_request_s3(uri), None
    path = _request_path(uri)
    try:
        return json.loads(path.read_text()), path
    except (OSError, json.JSONDecodeError) as exc:
        raise QueryError("invalid_contract", f"request uri unreadable: {exc}")


def _source_transport(request: dict, request_path: Path | None):
    """Pick the ObjectTransport for the request's declared sources.

    Every ``s3://`` source URI and the optional ``source_bucket`` field
    must name one bucket — the request schema declares a single
    ``source_bucket``, so a mixed-bucket request is invalid contract.
    Non-``s3://`` URIs under an S3 request resolve as plain object keys
    in that bucket (the transport is bucket-bound at construction).
    """
    uris = [request.get("source_root")]
    uris += [s.get("uri") for s in request.get("sources") or []]
    buckets = {
        parse_s3_uri(u)[0]
        for u in uris
        if isinstance(u, str) and u.startswith("s3://")
    }
    if request.get("source_bucket"):
        buckets.add(request["source_bucket"])
    if not buckets:
        root = request.get("source_root") or (
            request_path.parent if request_path else None
        )
        if root is None:
            raise QueryError(
                "invalid_contract", "no source_root or local request path"
            )
        return LocalTransport(root)
    if len(buckets) != 1:
        raise QueryError(
            "invalid_contract",
            f"source bucket ambiguity: {sorted(buckets)}",
        )
    return boto3_transport(_s3_client(), next(iter(buckets)))


def _open_store(out_uri: str | None):
    if not out_uri:
        return MemoryDerivedStore()
    if out_uri.startswith("s3://"):
        bucket, prefix = parse_s3_uri(out_uri)
        if not bucket:
            raise QueryError("invalid_contract", f"out uri has no bucket: {out_uri}")
        return S3DerivedStore(_s3_client(), bucket, prefix)
    raw = out_uri[len("dir://"):] if out_uri.startswith("dir://") else out_uri
    try:
        # The derived-root CLI argument is confined to the working
        # directory before any filesystem access (canonicalize-then-
        # validate, the repo's S8707 pattern).
        return LocalDirStore(confine_to_base(cwd_root(), raw))
    except ValueError as exc:
        raise QueryError("access_denied", str(exc)) from exc


def _verify_sha(doc: dict, expected: str) -> None:
    body = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
    actual = hashlib.sha256(body).hexdigest()
    if expected and actual != expected:
        raise QueryError(
            "invalid_contract",
            f"request sha256 {actual} != declared {expected}",
        )


def _fetch_sources_manifest(uri: str, ledger: BudgetLedger) -> dict:
    """Bounded read of the ``sources_uri`` cohort manifest.

    Same pinned-transport + canonical-sha contract as the request
    itself: an ``s3://`` URI is read through the pinned boto3 transport
    and charged to the shared ledger like every source read; a local
    path serves the offline shim. ``sources_sha256`` on the request
    binds the canonicalized manifest body exactly like
    ``--request-sha256`` binds the request.
    """
    if uri.startswith("s3://"):
        bucket, key = parse_s3_uri(uri)
        if not key:
            raise QueryError(
                "invalid_contract", f"sources uri has no key: {uri}"
            )
        transport = boto3_transport(_s3_client(), bucket)
        budget = ReadBudget(
            max_total_bytes=_SOURCES_MANIFEST_MAX_BYTES,
            max_object_bytes=_SOURCES_MANIFEST_MAX_BYTES,
        )
        outcome = read_object(transport, bucket, key, budget)
        if outcome.state != STATE_AVAILABLE or outcome.body is None:
            raise QueryError(
                "access_denied",
                f"sources manifest fetch blocked: "
                f"{outcome.state} {outcome.detail}",
            )
        body = outcome.body
        ledger.charge("max_api_calls_total", 1, uri)
        ledger.charge("max_get_requests", 1, uri)
        ledger.charge("max_compressed_bytes_read", len(body), uri)
    else:
        try:
            body = _request_path(uri).read_bytes()
        except OSError as exc:
            raise QueryError(
                "invalid_contract", f"sources uri unreadable: {exc}"
            )
        if len(body) > _SOURCES_MANIFEST_MAX_BYTES:
            raise QueryError(
                "invalid_contract",
                "sources manifest exceeds the byte cap",
            )
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise QueryError(
            "invalid_contract", f"sources manifest unreadable: {exc}"
        )


def _resolve_sources(request: dict, ledger: BudgetLedger) -> list:
    """The request's ``sources`` list plus any ``sources_uri`` cohort.

    ``sources_uri`` names a JSON document ``{"sources": [...]}`` staged
    beside the request — it keeps a cohort larger than the 1 MiB
    request cap explicit, immutable and sha-pinned instead of
    runtime-enumerated. Entries merge after inline ``sources``; the
    manifest's sha is verified when ``sources_sha256`` is declared.
    """
    sources = list(request.get("sources") or [])
    uri = request.get("sources_uri")
    if not uri:
        return sources
    doc = _fetch_sources_manifest(str(uri), ledger)
    expected = request.get("sources_sha256") or ""
    canonical = json.dumps(doc, sort_keys=True, separators=(",", ":"))
    if expected:
        actual = hashlib.sha256(canonical.encode()).hexdigest()
        if actual != expected:
            raise QueryError(
                "invalid_contract",
                f"sources sha256 {actual} != declared {expected}",
            )
    extra = doc.get("sources") if isinstance(doc, dict) else doc
    if not isinstance(extra, list) or not all(
        isinstance(s, dict) for s in extra
    ):
        raise QueryError(
            "invalid_contract",
            "sources manifest must carry a list of source objects",
        )
    return sources + extra


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


def _profile_defaults(request: dict) -> dict:
    """Extraction-profile defaults (first_paper_scalar et al.)."""
    from . import first_paper  # noqa: PLC0415

    if request.get("extraction_profile") == first_paper.PROFILE_ID:
        return first_paper.defaults()
    return {}


def _sources(request: dict) -> list[SourceSpec]:
    defaults = _profile_defaults(request)
    req_allow = request.get("member_allowlist")
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
            member_allowlist=(
                tuple(s["member_allowlist"])
                if s.get("member_allowlist") is not None
                else (
                    tuple(req_allow) if req_allow is not None
                    else defaults.get("member_allowlist")
                )
            ),
            emit_scalars=bool(
                s.get("emit_scalars",
                      defaults.get("emit_scalars", True))
            ),
            source_role=s.get("source_role"),
        )
        for i, s in enumerate(request.get("sources") or [])
    ]


def _default_out_uri(request: dict) -> str | None:
    """Derived store root when ``--out-uri`` is absent (ticket D4).

    All reducer store keys are full repository-relative paths
    (``campaign/_derived/reducer/v1/...``), so the store roots at the
    request's ``source_bucket`` itself — a prefixed store would
    double-prefix. Without this fallback the canonical worker argv
    (which carries no ``--out-uri``) would discard every derived write
    into a MemoryDerivedStore and the return leg could never poll a
    durable receipt.
    """
    bucket = request.get("source_bucket")
    return f"s3://{bucket}/" if isinstance(bucket, str) and bucket else None


def _attempt_receipt(
    request: dict,
    ctx: ReductionContext,
    phase: str,
    status: str,
    *,
    ledger: BudgetLedger | None = None,
    detail: str = "",
    snapshot_id: str | None = None,
    checkpoint_uri: str | None = None,
    counts: dict | None = None,
) -> dict:
    """Durable attempt receipt (CANONICAL ``attempt_receipt_fields``).

    The return leg polls ``attempts/{reduction_id}/RECEIPT.json`` — its
    absence is the detectable "job produced no receipt" state; a typed
    status here must never read as success.
    """
    rid = ctx.reduction_id
    prefix = f"{DERIVED_ROOT}/attempts/{rid}"
    job_id = os.environ.get("AWS_BATCH_JOB_ID", "")
    return {
        "schema": "crusher-reducer-attempt-receipt/v1",
        "reduction_id": rid,
        "fingerprint": ctx.fingerprint,
        "request_sha256": request.get("request_sha256") or "",
        "admission_id": ctx.admission_id,
        "github_run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "github_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        "phase": phase,
        "status": status,
        "batch_job_ids": [job_id] if job_id else [],
        "jobdef_revision_arn": (
            (request.get("job_binding") or {}).get(
                "job_definition_revision_arn", ""
            )
        ),
        "image_digest": (
            request.get("reducer_image_digest")
            or request.get("image_digest")
            or ""
        ),
        "catalog_uri": f"{prefix}/COMMIT.json",
        "catalog_hash": snapshot_id or "",
        "summary_key": f"{prefix}/MANIFEST.json",
        "files_manifest_key": f"{prefix}/MANIFEST.json",
        "pages_manifest_key": (
            f"{prefix}/pages/first_paper_vectors.pages_manifest.json"
        ),
        "status_key": f"{prefix}/status.json",
        "asset_index_key": f"{prefix}/asset_index.json",
        "checkpoint_uri": checkpoint_uri,
        "continuation": None,
        "output_counts": counts or {},
        "errors": [detail] if detail else [],
        "budget_spent": ledger.snapshot() if ledger is not None else {},
        "budget_remaining": (
            {f: ledger.headroom(f) for f in ledger.ceilings}
            if ledger is not None
            else {}
        ),
        "start_utc": request.get("utc") or "",
        "end_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def _write_attempt_receipt(store, doc: dict) -> None:
    """Create-only attempt receipt — the first job attempt's record wins."""
    key = f"{DERIVED_ROOT}/attempts/{doc['reduction_id']}/RECEIPT.json"
    try:
        store.put_if_absent(
            key, json.dumps(doc, sort_keys=True, indent=2).encode(),
        )
    except (DerivedStoreError, Exception):  # noqa: BLE001 — best-effort
        pass


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


class _MeteredTransport:
    """Counting ``ObjectTransport`` wrapper for the bounded pilot (D6).

    Records per-key head/get request counts, compressed bytes and wall
    seconds so the pilot evidence document carries measured per-source
    costs with specimen pins — the quote op's ``pilot_receipt`` input.
    """

    def __init__(self, inner) -> None:
        self._inner = inner
        self.per_key: dict[str, dict] = {}
        self.wall_seconds = 0.0

    def _bump(self, key: str, field: str, n: float) -> dict:
        row = self.per_key.setdefault(key, {
            "key": key, "head_requests": 0, "get_requests": 0,
            "bytes": 0, "wall_seconds": 0.0,
        })
        row[field] += n
        return row

    def head(self, key: str) -> HeadInfo:
        self._bump(key, "head_requests", 1)
        return self._inner.head(key)

    def get(self, key: str, **kwargs) -> GetResponse:
        start = time.monotonic()
        resp = self._inner.get(key, **kwargs)
        elapsed = time.monotonic() - start
        row = self._bump(key, "get_requests", 1)
        row["bytes"] += len(resp.body or b"")
        row["wall_seconds"] += elapsed
        self.wall_seconds += elapsed
        return resp


def _peak_memory_mib() -> float | None:
    """Peak RSS of the worker process in MiB, where the OS reports it."""
    try:
        import resource  # noqa: PLC0415

        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    except (ImportError, ValueError, OSError):
        return None


def _write_pilot_evidence(
    store, request: dict, ctx, transport, result, ledger,
) -> None:
    """Measured pilot evidence -> ``attempts/{rid}/pilot_evidence.json``.

    Per-source metering plus ledger spend and manifest byte totals — the
    ``pilot_receipt`` evidence document ``analysis quote`` extrapolates.
    Specimen pins travel on the request's ``sources`` entries verbatim.
    """
    per_source = []
    for src in request.get("sources") or []:
        uri = src.get("uri") or ""
        key = (
            parse_s3_uri(uri)[1] if str(uri).startswith("s3://")
            else uri
        )
        meter = dict(transport.per_key.get(key, {}))
        meter["source_id"] = src.get("source_id")
        meter["family"] = src.get("family")
        meter["specimen_class"] = src.get("specimen_class")
        meter["version_id"] = src.get("version_id")
        meter["etag"] = src.get("etag")
        per_source.append(meter)
    out_bytes = sum(
        int(e.get("bytes_stored") or 0) for e in result.manifest
    )
    doc = {
        "schema": "crusher-reducer-pilot-evidence/v1",
        "kind": "pilot_receipt",
        "reduction_id": ctx.reduction_id,
        "fingerprint": ctx.fingerprint,
        "request_sha256": request.get("request_sha256") or "",
        "inventory_sha256": ctx.inventory_sha256,
        "admission_id": ctx.admission_id,
        "utc": request.get("utc") or "",
        "status": result.status,
        "per_source": per_source,
        "measured": {
            "objects": len(request.get("sources") or []),
            "compressed_bytes_read": sum(
                m.get("bytes") or 0 for m in per_source
            ),
            "head_requests": sum(
                m.get("head_requests") or 0 for m in per_source
            ),
            "get_requests": sum(
                m.get("get_requests") or 0 for m in per_source
            ),
            "wall_seconds": transport.wall_seconds,
            "peak_memory_mib": _peak_memory_mib(),
            "output_bytes": out_bytes,
            "retries": ledger.retries,
            "budget_spent": ledger.snapshot(),
        },
    }
    key = (
        f"{DERIVED_ROOT}/attempts/{ctx.reduction_id}/pilot_evidence.json"
    )
    try:
        store.put_idempotent(
            key, json.dumps(doc, sort_keys=True, indent=2).encode(),
        )
    except DerivedStoreError:
        pass  # evidence is best-effort beside the attempt receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="campaign_reducer.worker")
    parser.add_argument("--phase", required=True,
                        choices=["materialize", "finalize", "query",
                                 "return_canary", "pilot"])
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
        ledger = BudgetLedger(ceilings)
        request["sources"] = _resolve_sources(request, ledger)
        transport = (
            _source_transport(request, request_path)
            if args.phase in ("materialize", "finalize",
                              "return_canary", "pilot")
            else None
        )
    except BudgetExceeded as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}))
        return EXIT_BUDGET_STOPPED
    except (QueryError, BudgetBlocked) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}))
        if isinstance(exc, BudgetBlocked):
            return EXIT_ADMISSION
        return (
            EXIT_BLOCKED
            if exc.kind == "access_denied"
            else EXIT_INVALID_CONTRACT
        )
    try:
        store = _open_store(args.out_uri or _default_out_uri(request))
    except QueryError as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}))
        return EXIT_BLOCKED
    ctx = _ctx(request, args.shard_index)

    if args.phase in ("materialize", "finalize", "return_canary",
                      "pilot"):
        if args.phase == "pilot":
            transport = _MeteredTransport(transport)
        spec = MaterializeSpec(
            sources=_sources(request),
            ctx=ctx,
            shard_size=int(request.get("shard_size") or 64),
            requested_tables=tuple(request.get("requested_tables") or ()),
            metric_bindings=dict(request.get("metric_bindings") or {}),
            declared_source_count=request.get("declared_source_count"),
            partition_format=request.get("partition_format") or "jsonl",
            utc=request.get("utc") or "",
            extraction_profile=request.get("extraction_profile"),
            suppress_tables=frozenset(
                request.get("suppress_tables") or ()),
        )
        try:
            result = run_materialization(spec, transport, store, ledger)
        except (DerivedStoreError, BudgetBlocked) as exc:
            _write_attempt_receipt(store, _attempt_receipt(
                request, ctx, args.phase, "failed", ledger=ledger,
                detail=str(exc),
            ))
            print(json.dumps({"status": "blocked", "error": str(exc)}))
            return EXIT_BLOCKED
        if args.phase == "pilot":
            _write_pilot_evidence(
                store, request, ctx, transport, result, ledger,
            )
        _write_attempt_receipt(store, _attempt_receipt(
            request, ctx, args.phase, result.status, ledger=ledger,
            snapshot_id=result.snapshot_id,
            checkpoint_uri=result.checkpoint_uri,
            detail="; ".join(
                str(e.get("detail") or e) for e in result.errors[:4]
            ) or None,
        ))
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
        _write_attempt_receipt(store, _attempt_receipt(
            request, ctx, args.phase, "failed", ledger=ledger,
            detail=exc.detail,
        ))
        print(json.dumps({"status": "blocked", "error": exc.detail}))
        return EXIT_INVALID_CONTRACT
    _write_attempt_receipt(store, _attempt_receipt(
        request, ctx, args.phase, outcome.status, ledger=ledger,
        counts={"pages": len(outcome.pages)},
    ))
    print(json.dumps({"status": outcome.status, "pages": len(outcome.pages)}))
    return _status_exit(outcome.status)


if __name__ == "__main__":
    sys.exit(main())
