"""``analysis submit`` — paid, explicit phase submission (D6: pilot leg).

The admitted execution envelope (``--request``, schema kind
``execution``) is validated, its phase admission checked (the envelope's
``phase`` must equal ``--phase``, the admission must be unexpired), and
for ``--phase pilot`` the pilot specimens document (``--specimens``)
renders the bounded worker request: it is staged create-only under
``campaign/_derived/reducer/v1/requests/`` on the dispatcher role, then
one Batch job is submitted on the proven ``picard-reducer`` jobdef with
the canonical worker argv. A durable dispatch receipt lands under
``--out``.

Other declared phases remain a typed stop in this change — the ticket
wires the pilot leg; ``materialize``/``finalize``/``return_canary``
submits keep landing through their own phased tickets.
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Any

from .._io import write_json
from . import contracts
from .derived_store import DerivedConflict, DerivedStoreError
from .identity import sha256_hex
from .materialize import DERIVED_ROOT
from .return_path import (
    ReturnFailure,
    _load_json_path,
    _out_root,
    _request_doc,
)
from .rows import canonical_json

OPTIONAL_FLAGS = ("--specimens",)

_WORKER_MODULE = "picard_framework.analysis.campaign_reducer.worker"
_REQUESTS_PREFIX = f"{DERIVED_ROOT}/requests"


def _s3_client():
    import boto3  # noqa: PLC0415

    return boto3.client("s3")


def _batch_client():
    import boto3  # noqa: PLC0415

    return boto3.client("batch")


def _now_utc() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _emit(out_root: str, name: str, doc: Any) -> None:
    write_json(str(Path(out_root) / name), doc)


def _finish(out_root: str, status: str, rc: int, **extra) -> int:
    doc = {"status": status, "operation": "submit"}
    doc.update(extra)
    _emit(out_root, "status.json", doc)
    print(json.dumps(doc))
    return rc


def _admission_live(request: dict) -> str | None:
    """None when the admission is live; an expiry detail otherwise."""
    expiry = (
        (request.get("approval") or {}).get("expires_utc")
        or (request.get("admission") or {}).get("expires_utc")
    )
    if not expiry:
        return None
    try:
        exp = _dt.datetime.fromisoformat(str(expiry).replace("Z", "+00:00"))
    except ValueError:
        return f"unparseable admission expiry {expiry!r}"
    if exp <= _now_utc():
        return f"admission expired {expiry}"
    return None


def _specimen_source(spec: dict, bucket: str) -> dict:
    """One specimen -> a worker ``sources[]`` entry carrying its pin."""
    uri = spec.get("uri") or spec.get("key") or ""
    if not uri.startswith("s3://"):
        uri = f"s3://{bucket}/{uri.lstrip('/')}"
    pin = spec.get("pin") or {}
    out = {
        "uri": uri,
        "family": spec.get("family") or "unknown_legacy",
        "source_id": spec.get("source_id") or uri.rsplit("/", 1)[-1],
        "campaign_id": spec.get("record_id") or "",
        "specimen_class": spec.get("class"),
        "version_id": pin.get("version_id"),
        "etag": pin.get("etag"),
        "pin_kind": pin.get("pin_kind"),
    }
    return {k: v for k, v in out.items() if v is not None}


def _worker_request(request: dict, specimens_doc: dict) -> dict:
    """Render the admitted envelope + specimens into the bounded worker
    request doc (the doc Batch is pinned to by sha256)."""
    bucket = request["source_bucket"]
    snap = request.get("inventory_snapshot") or {}
    approval = request.get("approval") or {}
    specs = [
        s for s in (specimens_doc.get("specimens") or [])
        if s.get("key")
    ]
    sources = [_specimen_source(s, bucket) for s in specs]
    return {
        "reduction_id": request["reduction_id"],
        "phase": "pilot",
        "snapshot_id": snap.get("id") or "snap-unspecified",
        "request_sha256": sha256_hex(canonical_json(request).encode()),
        "inventory_sha256": snap.get("sha256"),
        "implementation_sha": request.get("implementation_sha") or "",
        "adapter_registry_sha256":
            request.get("adapter_registry_sha256") or "",
        "image_digest": request.get("reducer_image_digest") or "",
        "admission_id": approval.get("admission_id"),
        "parent_reduction_id": request.get("parent_reduction_id"),
        "budgets": request.get("budgets") or {},
        "source_bucket": bucket,
        "source_root": f"s3://{bucket}/campaign/",
        "sources": sources,
        "shard_size": max(1, len(sources)),
        "declared_source_count": len(sources),
        "utc": approval.get("expires_utc") or "",
    }


def _stage_request(store, key: str, body: bytes) -> None:
    store.put_idempotent(key, body)


def _submit_job(client, request: dict, argv: list[str]) -> dict:
    binding = request["job_binding"]
    resp = client.submit_job(
        jobName=f"crusher-reducer-{request['reduction_id']}-pilot"[:128],
        jobQueue=binding["queue_arn"],
        jobDefinition=binding["job_definition_revision_arn"],
        containerOverrides={"command": argv},
    )
    job_arn = resp.get("jobArn")
    tags = {
        "reduction_id": request["reduction_id"],
        "phase": "pilot",
        "admission_id": str(
            (request.get("approval") or {}).get("admission_id") or ""
        ),
        "quote_id": str(
            (request.get("quote") or {}).get("quote_id") or ""
        ),
    }
    if job_arn:
        client.tag_resource(resourceArn=job_arn, tags=tags)
    return resp


def _pilot(request: dict, args, out_root: str) -> int:
    spec_flag = getattr(args, "specimens", "") or ""
    if not spec_flag:
        return _finish(out_root, "invalid_contract",
                       contracts.EXIT_INVALID_CONTRACT, error={
                           "kind": "missing_required_input",
                           "detail": "--phase pilot requires --specimens "
                                     "<pilot_specimens.json>",
                       })
    try:
        specimens = _load_json_path(spec_flag)
    except ReturnFailure as exc:
        return _finish(out_root, "invalid_contract",
                       contracts.EXIT_INVALID_CONTRACT,
                       error={"kind": exc.kind, "detail": exc.detail})
    if not isinstance(specimens, dict) or not specimens.get("specimens"):
        return _finish(out_root, "invalid_contract",
                       contracts.EXIT_INVALID_CONTRACT, error={
                           "kind": "malformed_specimens",
                           "detail": "specimens doc must carry a "
                                     "non-empty specimens list",
                       })
    worker_doc = _worker_request(request, specimens)
    if not worker_doc["sources"]:
        return _finish(out_root, "blocked",
                       contracts.EXIT_ACCESS_OR_RESOURCE_BLOCKED, error={
                           "kind": "no_payload_specimens",
                           "detail": "every selected specimen is a "
                                     "missing witness — nothing to run",
                       })
    body = canonical_json(worker_doc).encode()
    sha = sha256_hex(body)
    bucket = request["source_bucket"]
    key = f"{_REQUESTS_PREFIX}/{request['reduction_id']}-pilot.json"
    from .s3_store import S3DerivedStore  # noqa: PLC0415

    store = S3DerivedStore(_s3_client(), bucket)
    try:
        _stage_request(store, key, body)
    except DerivedConflict as exc:
        return _finish(out_root, "blocked",
                       contracts.EXIT_SOURCE_CHANGED, error={
                           "kind": "request_conflict",
                           "detail": str(exc),
                       })
    except DerivedStoreError as exc:
        return _finish(out_root, "blocked",
                       contracts.EXIT_ACCESS_OR_RESOURCE_BLOCKED, error={
                           "kind": exc.kind, "detail": exc.detail,
                       })
    uri = f"s3://{bucket}/{key}"
    argv = [
        "-m", _WORKER_MODULE,
        "--phase", "pilot",
        "--request-uri", uri,
        "--request-sha256", sha,
        "--shard-index", "0",
    ]
    try:
        resp = _submit_job(_batch_client(), request, argv)
    except Exception as exc:  # dispatcher grant/API failure -> blocked
        return _finish(out_root, "blocked",
                       contracts.EXIT_ACCESS_OR_RESOURCE_BLOCKED, error={
                           "kind": "batch_submit_failed",
                           "detail": str(exc),
                       })
    receipt = {
        "schema": "crusher-reducer-dispatch-receipt/v1",
        "operation": "submit",
        "phase": "pilot",
        "reduction_id": request["reduction_id"],
        "admission_id": (request.get("approval") or {}).get(
            "admission_id"),
        "quote_id": (request.get("quote") or {}).get("quote_id"),
        "request_uri": uri,
        "request_sha256": sha,
        "worker_argv": argv,
        "batch_job_id": resp.get("jobId"),
        "batch_job_arn": resp.get("jobArn"),
        "job_queue": request["job_binding"]["queue_arn"],
        "job_definition":
            request["job_binding"]["job_definition_revision_arn"],
        "specimen_count": len(worker_doc["sources"]),
    }
    _emit(out_root, "durable_attempt_receipt.json", receipt)
    return _finish(out_root, "submitted", contracts.EXIT_COMPLETE,
                   batch_job_id=resp.get("jobId"), request_uri=uri)


def run(args) -> int:
    """Entry for ``analysis submit``."""
    out_root = _out_root(args.out, "submit")
    if out_root is None:
        return contracts.EXIT_INVALID_CONTRACT
    try:
        request = _request_doc(args, "execution")
    except ReturnFailure as exc:
        return _finish(out_root, "invalid_contract",
                       contracts.EXIT_INVALID_CONTRACT,
                       error={"kind": exc.kind, "detail": exc.detail})
    phase = getattr(args, "phase", "")
    if request.get("phase") != phase:
        return _finish(out_root, "invalid_contract",
                       contracts.EXIT_INVALID_CONTRACT, error={
                           "kind": "phase_mismatch",
                           "detail": f"admitted phase "
                                     f"{request.get('phase')!r} != "
                                     f"--phase {phase!r}",
                       })
    expired = _admission_live(request)
    if expired:
        return _finish(out_root, "blocked",
                       contracts.EXIT_ADMISSION_REQUIRED_OR_EXCEEDED,
                       error={"kind": "admission_expired",
                              "detail": expired})
    if phase != "pilot":
        return _finish(out_root, "blocked",
                       contracts.EXIT_ACCESS_OR_RESOURCE_BLOCKED, error={
                           "kind": "phase_not_wired",
                           "detail": f"submit --phase {phase} is not "
                                     "wired in this change — only "
                                     "--phase pilot",
                       })
    return _pilot(request, args, out_root)
