"""Return-path operations for ``scripts/campaign analysis`` (ticket D4).

Implements the bounded metadata/return/control operations named by
``contracts/CANONICAL_INTERFACE.json``:

- ``status --attempt-id ID`` — bounded describe of an attempt's durable
  ``RECEIPT.json`` (or its checkpoint/partition subtree) → qualified
  receipt + continuation.
- ``resume --checkpoint URI`` — checkpoint-URI continuation → a new
  child request document + ``new_child_receipt`` (paid op).
- ``query --query QUERY.json`` — paged readback against the frozen
  catalog; the snapshot-pinned cursor from ``query_engine`` binds every
  page token to catalog + query + sort + PK (acceptance P20).
- ``collect --receipt URI`` — bounded, create-only-store fetch of an
  attempt's receipt + manifest + pages → verified artifacts + a
  durable ingestion request for the Edison leg.
- ``acknowledge --ack ACK.json`` — idempotent (attempt, query, page,
  hash) acknowledgment records create-only under
  ``requests/acks/`` (the dispatcher role's admitted write prefix).

Store keys throughout this module are full repository-relative paths
(``campaign/_derived/reducer/v1/...``) — the same convention
``materialize`` and ``query_engine`` write with — so the store always
roots at the bucket (or local root), never inside the derived prefix.

Every failure is typed: the status JSON carries ``status`` from
STATUS_NAMESPACES plus ``error.{kind,detail,owner}`` — a failure receipt
never looks successful, and no credential or signed URL is ever
emitted (acceptance P19: denied connectors report a structured blocked
status and an S3 pointer, never a secret prompt or file relay).
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from simulation_utils.paths import (
    confine_to_base,
    prepare_output_directory,
    validated_open,
)

from .._io import allowed_roots, cwd_root, write_json
from . import contracts
from . import validate as _validate_mod
from .catalog import CatalogError
from .derived_store import (
    DerivedConflict,
    DerivedStoreError,
    LocalDirStore,
)
from .ledger import BudgetBlocked, BudgetLedger, parse_ceilings
from .materialize import DERIVED_ROOT
from .pinned_reader import (
    STATE_AVAILABLE,
    ReadBudget,
    boto3_transport,
    parse_s3_uri,
    read_object,
)
from .query_engine import QueryError, run_query
from .s3_store import S3DerivedStore
from .worker import _status_exit

_CAPS = contracts.load(contracts.CANONICAL_INTERFACE)["readback"][
    "proposed_hard_caps"
]
_DERIVED = f"{DERIVED_ROOT}/"
_ACK_PREFIX = "requests/acks/"
_LISTING_BOUND = 1024

# Describe-only describe outcomes exit 0; every terminal attempt state maps
# to the canonical exit table (a failed attempt must fail the op too —
# a failure receipt never looks successful).
_ATTEMPT_EXIT = {
    "completed": contracts.EXIT_COMPLETE,
    "planned": contracts.EXIT_COMPLETE,
    "admitted": contracts.EXIT_COMPLETE,
    "queued": contracts.EXIT_COMPLETE,
    "running": contracts.EXIT_COMPLETE,
    "checkpointed": contracts.EXIT_COMPLETE,
    "partial": contracts.EXIT_PARTIAL_COVERAGE,
    "budget_stopped": contracts.EXIT_BUDGET_STOPPED_CHECKPOINTED,
    "source_changed": contracts.EXIT_SOURCE_CHANGED,
    "quarantined": contracts.EXIT_SCHEMA_OR_CORRUPTION_QUARANTINE,
    "return_blocked": contracts.EXIT_RETURN_PATH_BLOCKED,
}


def _s3_client():
    """Build the S3 client; lazy boto3 import keeps offline runs clean."""
    import boto3  # noqa: PLC0415

    return boto3.client("s3")


class ReturnFailure(Exception):
    """Typed return-path failure — status name + canonical exit code."""

    def __init__(
        self,
        kind: str,
        detail: str,
        *,
        status: str = "return_blocked",
        exit_code: int = contracts.EXIT_RETURN_PATH_BLOCKED,
        owner: str = "s3_return_path",
    ) -> None:
        super().__init__(f"{kind}: {detail}")
        self.kind = kind
        self.detail = detail
        self.status = status
        self.exit_code = exit_code
        self.owner = owner


def _invalid(detail: str) -> ReturnFailure:
    return ReturnFailure(
        "invalid_contract",
        detail,
        status="blocked",
        exit_code=contracts.EXIT_INVALID_CONTRACT,
        owner="request_file",
    )


def _out_root(out_dir, operation: str) -> str | None:
    """Confine ``--out`` to the invocation directory; None + print on escape."""
    try:
        safe = confine_to_base(cwd_root(), str(out_dir))
        return prepare_output_directory(safe, allowed_roots=(cwd_root(),))
    except ValueError as exc:
        print(json.dumps({
            "status": "blocked",
            "operation": operation,
            "error": {"kind": "invalid_contract", "detail": str(exc),
                      "owner": "request_file"},
        }))
        return None


def _emit(out_root: str, name: str, doc) -> None:
    write_json(os.path.join(out_root, name), doc)


def _run_ids() -> dict:
    return {
        "github_run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "github_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
    }


def _load_json_path(path) -> Any:
    """Read a JSON document from a path confined to the invocation CWD."""
    try:
        resolved = confine_to_base(cwd_root(), str(path))
    except ValueError as exc:
        raise _invalid(str(exc)) from exc
    try:
        with validated_open(
            resolved, allowed_roots=allowed_roots(), encoding="utf-8",
        ) as fh:
            return json.load(fh)
    except (OSError, ValueError) as exc:
        raise _invalid(f"{path}: {exc}") from exc


def _check_request(doc: Any, kind: str) -> dict:
    """Schema + semantic gate — identical rules to ``analysis validate``."""
    if not isinstance(doc, dict):
        raise _invalid("request document is not a JSON object")
    schema = contracts.load(contracts.REQUEST_KIND_SCHEMAS[kind])
    canonical = contracts.load(contracts.CANONICAL_INTERFACE)
    reasons = _validate_mod._semantic_reasons(doc, kind, schema, canonical)
    if reasons:
        admission = any(r["category"] == "admission" for r in reasons)
        raise ReturnFailure(
            "request_blocked",
            "; ".join(f"{r['path']}:{r['reason']}" for r in reasons[:8]),
            status="blocked",
            exit_code=(
                contracts.EXIT_ADMISSION_REQUIRED_OR_EXCEEDED
                if admission
                else contracts.EXIT_ACCESS_OR_RESOURCE_BLOCKED
            ),
            owner="request_file",
        )
    errors = _validate_mod._schema_errors(doc, schema)
    if errors:
        raise _invalid("; ".join(errors[:8]))
    return doc


def _request_doc(args, kind: str) -> dict:
    return _check_request(_load_json_path(args.request), kind)


def _store_for(args, request: dict):
    """Resolve the derived store — bucket-rooted, full-path keys."""
    uri = getattr(args, "store_uri", "") or ""
    if not uri:
        bucket = request.get("source_bucket")
        if isinstance(bucket, str) and bucket:
            uri = f"s3://{bucket}/"
        elif isinstance(request.get("derived_root"), str):
            uri = request["derived_root"]
        else:
            raise _invalid("request names neither source_bucket nor derived_root")
    if uri.startswith("s3://"):
        bucket, _ = parse_s3_uri(uri)
        if not bucket:
            raise _invalid(f"store uri has no bucket: {uri}")
        # Store keys already carry campaign/_derived/reducer/v1/… — the
        # store roots at the bucket itself to avoid double-prefixing.
        return S3DerivedStore(_s3_client(), bucket, "")
    raw = uri[len("dir://"):] if uri.startswith("dir://") else uri
    try:
        return LocalDirStore(confine_to_base(cwd_root(), raw))
    except ValueError as exc:
        raise ReturnFailure(
            "access_denied", str(exc), owner="store_root",
        ) from exc


def _resolve_store_key(ref: str) -> str:
    """Normalize an artifact reference to a derived-rooted store key."""
    if not isinstance(ref, str) or not ref:
        raise _invalid("empty artifact reference")
    key = parse_s3_uri(ref)[1] if ref.startswith("s3://") else ref
    key = key.lstrip("/")
    if not key.startswith(_DERIVED) or ".." in key.split("/"):
        raise ReturnFailure(
            "access_denied",
            f"key outside derived root: {ref}",
            owner="store_root",
        )
    return key


def _fetch_store(store, key: str, cap: int) -> bytes:
    """Bounded typed fetch: HEAD bounds, then GET — fail closed."""
    try:
        head = store.head(key)
    except DerivedStoreError as exc:
        raise ReturnFailure(
            exc.kind, f"{key}: {exc.detail}", owner="s3_return_path",
        ) from exc
    if head is None:
        raise ReturnFailure("missing_object", key, owner="s3_return_path")
    if head.get("bytes", 0) > cap:
        raise ReturnFailure(
            "budget_exceeded",
            f"{key}: {head['bytes']}B exceeds {cap}B cap",
            owner="s3_return_path",
        )
    try:
        return store.get(key)
    except DerivedStoreError as exc:
        raise ReturnFailure(
            exc.kind, f"{key}: {exc.detail}", owner="s3_return_path",
        ) from exc


def _fetch_uri(uri: str, max_bytes: int) -> bytes:
    """Bounded fetch of an external URI (s3://, file:// or local path)."""
    if uri.startswith("s3://"):
        bucket, key = parse_s3_uri(uri)
        if not key:
            raise _invalid(f"uri has no key: {uri}")
        transport = boto3_transport(_s3_client(), bucket)
        budget = ReadBudget(
            max_total_bytes=max_bytes, max_object_bytes=max_bytes,
        )
        outcome = read_object(transport, bucket, key, budget)
        if outcome.state != STATE_AVAILABLE or outcome.body is None:
            raise ReturnFailure(
                outcome.state, outcome.detail or uri, owner="s3_return_path",
            )
        return outcome.body
    raw = uri[len("file://"):] if uri.startswith("file://") else uri
    try:
        path = confine_to_base(cwd_root(), raw)
    except ValueError as exc:
        raise _invalid(str(exc)) from exc
    try:
        with validated_open(path, "rb", allowed_roots=allowed_roots()) as fh:
            body = fh.read()
    except OSError as exc:
        raise ReturnFailure("not_found", str(exc), owner="request_file") from exc
    if len(body) > max_bytes:
        raise ReturnFailure(
            "budget_exceeded",
            f"{uri}: {len(body)}B exceeds {max_bytes}B cap",
            owner="request_file",
        )
    return body


def _fetch_doc(uri: str, cap: int) -> dict:
    try:
        doc = json.loads(_fetch_uri(uri, cap))
    except ValueError as exc:
        raise _invalid(f"{uri}: unreadable JSON — {exc}") from exc
    if not isinstance(doc, dict):
        raise _invalid(f"{uri}: document is not a JSON object")
    return doc


def _kind_cap(key: str) -> int:
    """Per-kind readback cap for a derived store key."""
    name = key.rsplit("/", 1)[-1]
    if name.endswith("RECEIPT.json"):
        return _CAPS["receipt_bytes"]
    if name.endswith("MANIFEST.json") or name == "COMMIT.json":
        return _CAPS["request_manifest_bytes"]
    if name.startswith("summary"):
        return _CAPS["summary_bytes"]
    if name.endswith(".jsonl"):
        return _CAPS["index_page_bytes"]
    return _CAPS["export_object_bytes"]


def _write_collected(out_root: str, rel: str, body: bytes) -> str:
    target = os.path.join(out_root, "collected", rel)
    prepare_output_directory(
        os.path.dirname(target), allowed_roots=allowed_roots(),
    )
    with validated_open(target, "wb", allowed_roots=allowed_roots()) as fh:
        fh.write(body)
    return os.path.join("collected", rel)


def _sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


# ----------------------------------------------------------------------
# status — bounded describe of attempt receipt/subtree
# ----------------------------------------------------------------------


def _op_status(args, out_root: str) -> int:
    request = _request_doc(args, "bootstrap")
    store = _store_for(args, request)
    attempt = str(args.attempt_id)
    prefix = f"{_DERIVED}attempts/{attempt}/"
    try:
        keys = sorted(store.list(prefix))[:_LISTING_BOUND]
        receipt_meta = store.head(f"{prefix}RECEIPT.json")
    except DerivedStoreError as exc:
        raise ReturnFailure(exc.kind, exc.detail)
    receipt = None
    receipt_key = f"{prefix}RECEIPT.json"
    if receipt_meta is not None:
        receipt = json.loads(
            _fetch_store(store, receipt_key, _CAPS["receipt_bytes"])
        )
    checkpoints = [k for k in keys if "/checkpoints/" in k]
    if isinstance(receipt, dict) and receipt.get("status"):
        attempt_status = str(receipt["status"])
    elif checkpoints:
        attempt_status = "checkpointed"
    elif keys:
        attempt_status = "running"
    else:
        attempt_status = "planned"
    doc = {
        "status": attempt_status,
        "operation": "status",
        "request_id": request.get("request_id"),
        "attempt_id": attempt,
        "qualified_receipt": receipt,
        "objects": keys,
        "listing_bounded": len(keys) == _LISTING_BOUND,
        "continuation": checkpoints[-1] if checkpoints else None,
        **_run_ids(),
    }
    _emit(out_root, "status.json", doc)
    if receipt is not None:
        _emit(out_root, "qualified_receipt.json", receipt)
    print(json.dumps(doc))
    return _ATTEMPT_EXIT.get(
        attempt_status, contracts.EXIT_ACCESS_OR_RESOURCE_BLOCKED,
    )


# ----------------------------------------------------------------------
# resume — checkpoint URI continuation → new child request + receipt
# ----------------------------------------------------------------------


def _op_resume(args, out_root: str) -> int:
    request = _request_doc(args, "execution")
    checkpoint = _fetch_doc(args.checkpoint, _CAPS["request_manifest_bytes"])
    if "ledger_spent" not in checkpoint and "manifest_delta" not in checkpoint:
        raise _invalid(f"{args.checkpoint}: not a shard checkpoint doc")
    child = dict(request)
    parent = request.get("reduction_id") or checkpoint.get("reduction_id")
    child["parent_reduction_id"] = request.get("parent_reduction_id") or parent
    child_body = json.dumps(child, sort_keys=True, indent=2).encode()
    _emit(out_root, "new_child_request.json", child)
    new_child_receipt = {
        "kind": "new_child_receipt",
        "reduction_id": child.get("reduction_id"),
        "parent_reduction_id": child["parent_reduction_id"],
        "resumed_from_checkpoint": args.checkpoint,
        "checkpoint_reduction_id": checkpoint.get("reduction_id"),
        "ledger_spent_carried": checkpoint.get("ledger_spent") or {},
        "manifest_entries_carried": len(checkpoint.get("manifest_delta") or []),
        "request_sha256": _sha256(child_body),
        "resume_note": (
            "re-dispatch of the same reduction_id resumes the attempt "
            "subtree: completed shard checkpoints are skipped by the "
            "worker's _restore_state"
        ),
        **_run_ids(),
    }
    _emit(out_root, "new_child_receipt.json", new_child_receipt)
    doc = {
        "status": "completed",
        "operation": "resume",
        "request_id": request.get("request_id"),
        "new_child_receipt": new_child_receipt,
        **_run_ids(),
    }
    _emit(out_root, "status.json", doc)
    print(json.dumps(doc))
    return contracts.EXIT_COMPLETE


# ----------------------------------------------------------------------
# query — paged readback against the frozen catalog (P20 cursor binding)
# ----------------------------------------------------------------------


def _op_query(args, out_root: str) -> int:
    request = _request_doc(args, "execution")
    query_doc = _load_json_path(args.query)
    schema = contracts.load("QUERY.schema.json")
    errors = _validate_mod._schema_errors(query_doc, schema)
    if errors:
        raise _invalid("; ".join(errors[:8]))
    store = _store_for(args, request)
    try:
        ledger = BudgetLedger(parse_ceilings(request.get("budgets")))
    except BudgetBlocked as exc:
        raise ReturnFailure(
            "budget_blocked", str(exc), status="blocked",
            exit_code=contracts.EXIT_ADMISSION_REQUIRED_OR_EXCEEDED,
            owner="request_file",
        ) from exc
    commit = request.get("commit_uri") or (
        f"{_DERIVED}attempts/{request.get('reduction_id')}/COMMIT.json"
    )
    commit_key = _resolve_store_key(commit) if commit.startswith("s3://") else commit
    try:
        outcome = run_query(
            query_doc,
            store,
            ledger,
            commit_key=commit_key,
            reduction_id=str(request.get("reduction_id") or ""),
        )
    except QueryError as exc:
        code = (
            contracts.EXIT_SOURCE_CHANGED
            if exc.kind == "cursor_invalid"
            else contracts.EXIT_INVALID_CONTRACT
        )
        status = "source_changed" if exc.kind == "cursor_invalid" else "blocked"
        raise ReturnFailure(
            exc.kind, exc.detail, status=status, exit_code=code,
            owner="query_engine",
        ) from exc
    except CatalogError as exc:
        quarantine = exc.kind == "partition_corrupt"
        raise ReturnFailure(
            exc.kind, exc.detail,
            status="quarantined" if quarantine else "return_blocked",
            exit_code=(
                contracts.EXIT_SCHEMA_OR_CORRUPTION_QUARANTINE
                if quarantine
                else contracts.EXIT_RETURN_PATH_BLOCKED
            ),
            owner="catalog",
        ) from exc
    # A catalog version that changed behind a frozen cursor is typed
    # source_changed (the P20 surface), never a generic block or success.
    swappable = {
        e.get("kind") for e in outcome.errors if isinstance(e, dict)
    } & {"snapshot_mismatch", "cursor_invalid"}
    status = "source_changed" if swappable else outcome.status
    doc = {
        "status": status,
        "operation": "query",
        "request_id": request.get("request_id"),
        "query_id": outcome.query_id,
        "pages": len(outcome.pages),
        "bounded_query_pages": outcome.page_keys,
        "continuation": (
            outcome.next_cursor.get("token") if outcome.next_cursor else None
        ),
        **_run_ids(),
    }
    if swappable:
        doc["error"] = {
            "kind": sorted(swappable)[0],
            "detail": "catalog snapshot changed behind the frozen cursor",
            "owner": "query_engine",
        }
    elif outcome.errors:
        doc["errors"] = outcome.errors[:8]
    _emit(out_root, "status.json", doc)
    print(json.dumps(doc))
    if swappable:
        return contracts.EXIT_SOURCE_CHANGED
    return _status_exit(outcome.status)


# ----------------------------------------------------------------------
# collect — bounded fetch of receipt/manifest/pages → ingestion request
# ----------------------------------------------------------------------


def _manifest_entries(store, receipt: dict) -> list[dict]:
    key = receipt.get("files_manifest_key") or receipt.get("manifest_key")
    if not isinstance(key, str) or not key:
        return []
    doc = _fetch_doc_from_store(
        store, _resolve_store_key(key), _CAPS["request_manifest_bytes"],
    )
    entries = doc.get("entries") or doc.get("partitions") or []
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("uri"):
            raise _invalid(f"manifest entry missing uri: {entry!r}")
    return entries


def _fetch_doc_from_store(store, key: str, cap: int) -> dict:
    try:
        doc = json.loads(_fetch_store(store, key, cap))
    except ValueError as exc:
        raise _invalid(f"{key}: unreadable JSON — {exc}") from exc
    if not isinstance(doc, dict):
        raise _invalid(f"{key}: document is not a JSON object")
    return doc


def _op_collect(args, out_root: str) -> int:
    request = _request_doc(args, "bootstrap")
    store = _store_for(args, request)
    receipt_body = _fetch_uri(args.receipt, _CAPS["receipt_bytes"])
    receipt = _fetch_doc(args.receipt, _CAPS["receipt_bytes"])
    refs = [
        _resolve_store_key(ref)
        for ref in (receipt.get("summary_key"), receipt.get("catalog_uri"))
        if isinstance(ref, str) and ref
    ]
    entries = _manifest_entries(store, receipt)
    if len(entries) > _CAPS["files_per_collect"]:
        raise ReturnFailure(
            "budget_exceeded",
            f"{len(entries)} manifest entries exceeds "
            f"{_CAPS['files_per_collect']} files/collect cap",
            owner="s3_return_path",
        )
    refs += [_resolve_store_key(e["uri"]) for e in entries]
    declared = {_resolve_store_key(e["uri"]): e for e in entries}
    collected: list[dict] = []
    total = len(receipt_body)
    for key in refs:
        body = _fetch_store(store, key, _kind_cap(key))
        total += len(body)
        if total > _CAPS["total_bytes_per_collect"]:
            raise ReturnFailure(
                "budget_exceeded",
                f"collect exceeds {_CAPS['total_bytes_per_collect']}B "
                "total cap",
                owner="s3_return_path",
            )
        _verify_declared_sha(declared, key, body)
        rel = _write_collected(out_root, key.rsplit("/", 1)[-1], body)
        collected.append({
            "path": rel,
            "s3_key": key,
            "sha256": _sha256(body),
            "bytes": len(body),
            "kind": key.rsplit("/", 1)[-1].split(".")[-1],
        })
    rel = _write_collected(out_root, "RECEIPT.json", receipt_body)
    collected.insert(0, {
        "path": rel, "s3_key": "<receipt-uri>",
        "sha256": _sha256(receipt_body), "bytes": len(receipt_body),
        "kind": "receipt",
    })
    ingestion = {
        "schema": "crusher-reducer-ingestion/v1",
        "request_id": request.get("request_id"),
        "reduction_id": receipt.get("reduction_id"),
        "receipt_sha256": _sha256(receipt_body),
        "files": collected,
        "s3_pointer": args.receipt,
        **_run_ids(),
    }
    _emit(out_root, "durable_ingestion_request.json", ingestion)
    doc = {
        "status": "completed",
        "operation": "collect",
        "request_id": request.get("request_id"),
        "verified_artifacts": collected,
        "total_bytes": total,
        "durable_ingestion_request": "durable_ingestion_request.json",
        **_run_ids(),
    }
    _emit(out_root, "status.json", doc)
    print(json.dumps(doc))
    return contracts.EXIT_COMPLETE


def _verify_declared_sha(declared: dict, key: str, body: bytes) -> None:
    """Hash-pinned readback: a declared sha256 that mismatches quarantines."""
    entry = declared.get(key) or {}
    want = entry.get("sha256")
    if want and _sha256(body) != want:
        raise ReturnFailure(
            "hash_mismatch",
            f"{key}: sha256 {_sha256(body)} != declared {want}",
            status="quarantined",
            exit_code=contracts.EXIT_SCHEMA_OR_CORRUPTION_QUARANTINE,
            owner="s3_return_path",
        )


# ----------------------------------------------------------------------
# acknowledge — idempotent (attempt, query, page, hash) ack records
# ----------------------------------------------------------------------

_ACK_REQUIRED = ("receipt_id", "project_asset_ids", "accepted_page_ids")


def _op_acknowledge(args, out_root: str) -> int:
    request = _request_doc(args, "bootstrap")
    ack = _load_json_path(args.ack)
    missing = [f for f in _ACK_REQUIRED if f not in ack]
    if missing:
        raise _invalid(f"ack missing required fields: {missing}")
    ack = dict(ack)
    ack.setdefault("request_id", request.get("request_id"))
    ack_id = ack.get("ack_id") or (
        "ack-" + _sha256(json.dumps(
            ack, sort_keys=True, separators=(",", ":"),
        ).encode())[:16]
    )
    ack["ack_id"] = ack_id
    body = json.dumps(ack, sort_keys=True, indent=2).encode()
    # Run ids are provenance for the envelope/status only — the stored ack
    # must be byte-identical across idempotent reruns or every retry trips
    # derived_conflict on the same ack_id.
    ack.update(_run_ids())
    store = _store_for(args, request)
    key = f"{_DERIVED}{_ACK_PREFIX}{ack_id}.json"
    deduplicated = _write_ack(store, key, body)
    envelope = {
        "schema": "crusher-reducer-ack-envelope/v1",
        "ack_id": ack_id,
        "deduplicated": deduplicated,
        "receipt_id": ack.get("receipt_id"),
        "reduction_id": ack.get("reduction_id"),
        "accepted_page_ids": ack.get("accepted_page_ids"),
        "project_asset_ids": ack.get("project_asset_ids"),
        "s3_pointer": f"s3://{request.get('source_bucket')}/{key}",
        "request_id": request.get("request_id"),
        **_run_ids(),
    }
    if len(json.dumps(envelope).encode()) > _CAPS["issue_envelope_bytes"]:
        raise ReturnFailure(
            "budget_exceeded", "ack envelope exceeds 32KiB issue cap",
            owner="request_file",
        )
    _emit(out_root, "ack_envelope.json", envelope)
    doc = {
        "status": "completed",
        "operation": "acknowledge",
        "ack_id": ack_id,
        "deduplicated": deduplicated,
        "qualified_durable_ack": {
            "s3_key": key,
            "sha256": _sha256(body),
            "deduplicated": deduplicated,
        },
        "ack_envelope": "ack_envelope.json",
        **_run_ids(),
    }
    _emit(out_root, "status.json", doc)
    print(json.dumps(doc))
    return contracts.EXIT_COMPLETE


def _write_ack(store, key: str, body: bytes) -> bool:
    """Create-only ack write. Returns True when an identical record already
    existed (deduplicated notification); raises typed failures otherwise.

    Writes first, reads only on a collision: the ack prefix admits object
    writes but no ListBucket, and a GET on a missing key is denied as
    AccessDenied (existence-hiding), so a read-first dedupe can never
    succeed under the dispatcher role.
    """
    try:
        written = store.put_idempotent(key, body)
    except DerivedConflict as exc:
        raise ReturnFailure(
            "derived_conflict", f"{key}: {exc}", status="blocked",
            exit_code=contracts.EXIT_ACCESS_OR_RESOURCE_BLOCKED,
            owner="s3_return_path",
        ) from exc
    except DerivedStoreError as exc:
        raise ReturnFailure(
            exc.kind, f"{key}: {exc.detail}", owner="s3_return_path",
        ) from exc
    return not written


OPS = {
    "status": _op_status,
    "resume": _op_resume,
    "query": _op_query,
    "collect": _op_collect,
    "acknowledge": _op_acknowledge,
}

# Optional argv surface beyond the contract's required extra_argv: the
# store override lets offline runs (and tests) pin a local/dir:// store
# without inventing contract fields.
OPTIONAL_FLAGS = ("--store-uri",)


def run(args) -> int:
    """Dispatch a return-path operation; typed failures write status.json."""
    out_root = _out_root(args.out, args.operation)
    if out_root is None:
        return contracts.EXIT_INVALID_CONTRACT
    try:
        return OPS[args.operation](args, out_root)
    except ReturnFailure as exc:
        doc = {
            "status": exc.status,
            "operation": args.operation,
            "error": {
                "kind": exc.kind,
                "detail": exc.detail,
                "owner": exc.owner,
            },
            **_run_ids(),
        }
        _emit(out_root, "status.json", doc)
        print(json.dumps(doc))
        return exc.exit_code
