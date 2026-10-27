"""D4 return-canary machinery tests — status/resume/query/collect/
acknowledge ops, Edison ingest leg, worker attempt receipts, typed
failure paths, P19/P20 acceptance fixtures, workflow structure.

Everything offline-rigged: MemoryDerivedStore/LocalDirStore, stubbed
S3 clients raising real ``ClientError`` codes, and a fake
``edison_client`` module — no moto, no network, no AWS spend. Nothing
here marks a production pass; the live canary is a post-merge
workflow_dispatch on ``aws-campaign``.
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
import types
from pathlib import Path

import pytest
import yaml
from botocore.exceptions import ClientError
from conftest import rel
from d4_fixtures import (
    BUCKET,
    _budgets,
    ack_doc,
    attempt_receipt,
    bootstrap_request,
    build_catalog,
    checkpoint_doc,
    execution_request,
    files_manifest,
    fused_zip,
    manifest_entry,
    query_doc,
    sha,
)

from picard_framework.analysis.campaign_reducer import (
    cli,
    edison_ingest,
    return_path,
    worker,
)
from picard_framework.analysis.campaign_reducer.contracts import (
    EXIT_ACCESS_OR_RESOURCE_BLOCKED,
    EXIT_COMPLETE,
    EXIT_INVALID_CONTRACT,
    EXIT_RETURN_PATH_BLOCKED,
    EXIT_SCHEMA_OR_CORRUPTION_QUARANTINE,
    EXIT_SOURCE_CHANGED,
)
from picard_framework.analysis.campaign_reducer.derived_store import (
    MemoryDerivedStore,
)
from picard_framework.analysis.campaign_reducer.materialize import DERIVED_ROOT

REPO_ROOT = Path(__file__).resolve().parents[3]
_D = f"{DERIVED_ROOT}/"


@pytest.fixture(autouse=True)
def _forbid_external(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*a, **k):
        raise AssertionError("network/subprocess forbidden in offline tests")

    monkeypatch.setattr(socket, "create_connection", _raise)
    monkeypatch.setattr(socket.socket, "connect", _raise)
    monkeypatch.setattr(subprocess, "run", _raise)
    monkeypatch.setattr(subprocess, "Popen", _raise)
    monkeypatch.setitem(sys.modules, "boto3", None)


def _run(argv: list[str]) -> int:
    return cli.main(argv)


def _write(path: Path, doc) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc))
    return path


def _seed_attempt(store: MemoryDerivedStore, rid: str, receipt: dict) -> None:
    store.put_if_absent(
        f"{_D}attempts/{rid}/RECEIPT.json", json.dumps(receipt).encode(),
    )


class _DeniedS3:
    """Connector stub — every call denied (the P19 surface)."""

    @staticmethod
    def _err(op: str) -> ClientError:
        return ClientError(
            {"Error": {"Code": "AccessDenied"},
             "ResponseMetadata": {"HTTPStatusCode": 403}},
            op,
        )

    def head_object(self, **_kw):
        raise self._err("HeadObject")

    def get_object(self, **_kw):
        raise self._err("GetObject")

    def put_object(self, **_kw):
        raise self._err("PutObject")

    def list_objects_v2(self, **_kw):
        raise self._err("ListObjectsV2")


def _denied_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(return_path, "_s3_client", lambda *a, **k: _DeniedS3())


# ----------------------------------------------------------------------
# status — bounded describe of attempt receipt/subtree
# ----------------------------------------------------------------------


def test_status_reads_qualified_receipt(
    scratch: Path, capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rid = "red-ok"
    store = MemoryDerivedStore()
    receipt = attempt_receipt(rid)
    _seed_attempt(store, rid, receipt)
    req = _write(scratch / "bootstrap.json",
                 bootstrap_request(operation="status"))
    monkeypatch.setattr(return_path, "_store_for", lambda *a, **k: store)
    rc = _run([
        "status", "--request", rel(req), "--out", rel(scratch / "out"),
        "--attempt-id", rid,
    ])
    assert rc == EXIT_COMPLETE
    doc = json.loads(capsys.readouterr().out)
    assert doc["status"] == "completed"
    assert doc["qualified_receipt"]["reduction_id"] == rid
    assert (scratch / "out" / "qualified_receipt.json").exists()


def test_status_checkpointed_and_planned(
    scratch: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = MemoryDerivedStore()
    store.put_if_absent(
        f"{_D}attempts/red-run/checkpoints/shard-00000.json",
        json.dumps(checkpoint_doc("red-run")).encode(),
    )
    store.put_if_absent(
        f"{_D}attempts/red-run/shards/shard-00000/part-0.jsonl", b"{}",
    )
    monkeypatch.setattr(return_path, "_store_for", lambda *a, **k: store)
    req = _write(scratch / "b.json", bootstrap_request(operation="status"))
    rc = _run([
        "status", "--request", rel(req), "--out", rel(scratch / "o1"),
        "--attempt-id", "red-run",
    ])
    assert rc == EXIT_COMPLETE
    doc = json.loads((scratch / "o1" / "status.json").read_text())
    assert doc["status"] == "checkpointed"
    assert doc["continuation"].endswith("shard-00000.json")
    rc = _run([
        "status", "--request", rel(req), "--out", rel(scratch / "o2"),
        "--attempt-id", "red-absent",
    ])
    assert rc == EXIT_COMPLETE
    assert json.loads(
        (scratch / "o2" / "status.json").read_text()
    )["status"] == "planned"


def test_status_failed_attempt_fails_closed(
    scratch: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = MemoryDerivedStore()
    _seed_attempt(store, "red-bad", attempt_receipt("red-bad", "failed"))
    monkeypatch.setattr(return_path, "_store_for", lambda *a, **k: store)
    req = _write(scratch / "b.json", bootstrap_request(operation="status"))
    rc = _run([
        "status", "--request", rel(req), "--out", rel(scratch / "o"),
        "--attempt-id", "red-bad",
    ])
    assert rc == EXIT_ACCESS_OR_RESOURCE_BLOCKED
    assert json.loads(
        (scratch / "o" / "status.json").read_text()
    )["status"] == "failed"


def test_status_denied_connector_p19(
    scratch: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    """P19: denied connector → structured blocked status + owner, never
    a secret prompt or file relay, and an S3 pointer survives."""
    _denied_store(monkeypatch)
    req = _write(scratch / "b.json", bootstrap_request(operation="status"))
    rc = _run([
        "status", "--request", rel(req), "--out", rel(scratch / "o"),
        "--attempt-id", "red-x",
        "--store-uri", f"s3://{BUCKET}/",
    ])
    assert rc == EXIT_RETURN_PATH_BLOCKED
    out = capsys.readouterr().out
    doc = json.loads(out)
    assert doc["status"] == "return_blocked"
    assert doc["error"]["owner"] == "s3_return_path"
    for leak in ("AKIA", "X-Amz-Signature", "EDISON_PLATFORM_API_KEY",
                 "presign", "BEGIN "):
        assert leak not in out


# ----------------------------------------------------------------------
# resume — checkpoint continuation
# ----------------------------------------------------------------------


def test_resume_emits_new_child_receipt(scratch: Path) -> None:
    req = _write(scratch / "exec.json", execution_request())
    ck = _write(scratch / "ck.json", checkpoint_doc())
    rc = _run([
        "resume", "--request", rel(req), "--out", rel(scratch / "o"),
        "--checkpoint", rel(ck),
    ])
    assert rc == EXIT_COMPLETE
    child = json.loads((scratch / "o" / "new_child_request.json").read_text())
    receipt = json.loads(
        (scratch / "o" / "new_child_receipt.json").read_text()
    )
    assert child["reduction_id"] == "red-canary"
    assert child["parent_reduction_id"] == "red-canary"
    assert receipt["resumed_from_checkpoint"].endswith("ck.json")
    assert receipt["ledger_spent_carried"]["max_api_calls_total"] == 3.0


def test_resume_rejects_non_checkpoint(scratch: Path) -> None:
    req = _write(scratch / "exec.json", execution_request())
    ck = _write(scratch / "ck.json", {"unrelated": True})
    rc = _run([
        "resume", "--request", rel(req), "--out", rel(scratch / "o"),
        "--checkpoint", rel(ck),
    ])
    assert rc == EXIT_INVALID_CONTRACT


# ----------------------------------------------------------------------
# query — paged readback + P20 snapshot-frozen continuation
# ----------------------------------------------------------------------


def _local_catalog(scratch: Path):
    store_root = scratch / "store"
    store = MemoryDerivedStore()
    result = build_catalog(store)
    # Persist the derived tree into a local dir store so the CLI path
    # (confined to CWD) resolves it via --store-uri.
    for key in store.list(""):
        target = store_root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(store.get(key))
    return store_root, result


def test_query_pages_with_retained_continuation(scratch: Path) -> None:
    store_root, result = _local_catalog(scratch)
    req = _write(scratch / "exec.json", execution_request())
    q1 = _write(
        scratch / "q1.json",
        query_doc(catalog_snapshot_id=result.snapshot_id, page_rows=2,
                  max_export_rows=2),
    )
    _run([
        "query", "--request", rel(req), "--out", rel(scratch / "o1"),
        "--query", rel(q1), "--store-uri", rel(store_root),
    ])
    # A capped first page reports partial coverage with a retained token.
    d1 = json.loads((scratch / "o1" / "status.json").read_text())
    assert d1["pages"] >= 1
    token = d1["continuation"]
    assert token, "page-1 continuation token must be retained"
    # Follow-up page through the frozen cursor — the doc must match the
    # token's bound query exactly (token frozen to catalog+query+sort+PK).
    q2 = _write(
        scratch / "q2.json",
        query_doc(catalog_snapshot_id=result.snapshot_id, page_rows=2,
                  max_export_rows=2, continuation_token=token),
    )
    _run([
        "query", "--request", rel(req), "--out", rel(scratch / "o2"),
        "--query", rel(q2), "--store-uri", rel(store_root),
    ])
    d2 = json.loads((scratch / "o2" / "status.json").read_text())
    # Gather all page rows — pages disjoint, no duplicates, coverage
    # continues past the first page's cap.
    rows = []
    for key in d1["bounded_query_pages"] + d2["bounded_query_pages"]:
        body = (store_root / key).read_text()
        rows.extend(
            json.loads(line) for line in body.splitlines() if line.strip()
        )
    ids = [r.get("row_id") or r.get("native_path") for r in rows]
    assert len(ids) == len(set(ids))
    assert len(ids) > 2, "resume must emit rows the first page never saw"


def test_query_p20_catalog_swap_frozen_token(
    scratch: Path,
) -> None:
    """P20: a new catalog version mid-paging must not leak missing or
    duplicate rows — the token is frozen to catalog+query+sort+PK and a
    mismatch errors instead of silently resuming."""
    store_root, result = _local_catalog(scratch)
    req = _write(scratch / "exec.json", execution_request())
    q1 = _write(
        scratch / "q1.json",
        query_doc(catalog_snapshot_id=result.snapshot_id, page_rows=2,
                  max_export_rows=2),
    )
    _run([
        "query", "--request", rel(req), "--out", rel(scratch / "o1"),
        "--query", rel(q1), "--store-uri", rel(store_root),
    ])
    token = json.loads(
        (scratch / "o1" / "status.json").read_text()
    )["continuation"]
    assert token
    # Swap the catalog under the frozen token: a new catalog version
    # lands at the same attempt COMMIT with a different snapshot.
    store2 = MemoryDerivedStore()
    build_catalog(store2, snapshot_id="snap-canary-2")
    for key in store2.list(""):
        target = store_root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(store2.get(key))
    # The resuming doc is byte-identical except for the token — the
    # catalog swap behind it is what the cursor must catch.
    q2 = _write(
        scratch / "q2.json",
        query_doc(catalog_snapshot_id=result.snapshot_id, page_rows=2,
                  max_export_rows=2, continuation_token=token),
    )
    rc = _run([
        "query", "--request", rel(req), "--out", rel(scratch / "o2"),
        "--query", rel(q2), "--store-uri", rel(store_root),
    ])
    assert rc == EXIT_SOURCE_CHANGED
    doc = json.loads((scratch / "o2" / "status.json").read_text())
    assert doc["status"] == "source_changed"
    assert doc["error"]["kind"] in {"cursor_invalid", "snapshot_mismatch"}


def test_query_invalid_query_doc(scratch: Path) -> None:
    store_root, _ = _local_catalog(scratch)
    req = _write(scratch / "exec.json", execution_request())
    bad = _write(scratch / "q.json", {"contract_id": "wrong"})
    rc = _run([
        "query", "--request", rel(req), "--out", rel(scratch / "o"),
        "--query", rel(bad), "--store-uri", rel(store_root),
    ])
    assert rc == EXIT_INVALID_CONTRACT


# ----------------------------------------------------------------------
# collect — bounded fetch + verified artifacts + ingestion request
# ----------------------------------------------------------------------


def _seed_commit(store: MemoryDerivedStore, rid: str = "red-ok") -> None:
    store.put_if_absent(
        f"{_D}attempts/{rid}/COMMIT.json",
        json.dumps({"snapshot_id": "snap-1", "reduction_id": rid}).encode(),
    )


def _seed_collect(store: MemoryDerivedStore, rid: str = "red-ok") -> dict:
    receipt = attempt_receipt(rid)
    page = b'{"row": 1}\n{"row": 2}\n'
    page_key = f"{_D}attempts/{rid}/pages/page-00001.jsonl"
    manifest_body = files_manifest([manifest_entry(page_key, page)])
    manifest_key = f"{_D}attempts/{rid}/MANIFEST.json"
    receipt["files_manifest_key"] = manifest_key
    store.put_if_absent(manifest_key, manifest_body)
    store.put_if_absent(page_key, page)
    _seed_commit(store, rid)
    return receipt


def test_collect_verifies_and_emits_ingestion_request(
    scratch: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = MemoryDerivedStore()
    receipt = _seed_collect(store)
    monkeypatch.setattr(return_path, "_store_for", lambda *a, **k: store)
    req = _write(scratch / "b.json", bootstrap_request())
    rec = _write(scratch / "receipt.json", receipt)
    rc = _run([
        "collect", "--request", rel(req), "--out", rel(scratch / "o"),
        "--receipt", rel(rec),
    ])
    assert rc == EXIT_COMPLETE
    doc = json.loads((scratch / "o" / "status.json").read_text())
    assert doc["status"] == "completed"
    ingestion = json.loads(
        (scratch / "o" / "durable_ingestion_request.json").read_text()
    )
    paths = {f["path"] for f in ingestion["files"]}
    assert "collected/page-00001.jsonl" in paths
    assert "collected/RECEIPT.json" in paths
    assert all(len(f["sha256"]) == 64 for f in ingestion["files"])
    assert (scratch / "o" / "collected" / "page-00001.jsonl").exists()


def test_collect_missing_member_fails_closed(
    scratch: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = MemoryDerivedStore()
    receipt = attempt_receipt()
    mkey = f"{_D}attempts/red-ok/MANIFEST.json"
    missing = f"{_D}attempts/red-ok/pages/page-absent.jsonl"
    store.put_if_absent(mkey, files_manifest([
        manifest_entry(missing, b"{}"),
    ]))
    receipt["files_manifest_key"] = mkey
    _seed_commit(store)
    monkeypatch.setattr(return_path, "_store_for", lambda *a, **k: store)
    req = _write(scratch / "b.json", bootstrap_request())
    rec = _write(scratch / "receipt.json", receipt)
    rc = _run([
        "collect", "--request", rel(req), "--out", rel(scratch / "o"),
        "--receipt", rel(rec),
    ])
    assert rc == EXIT_RETURN_PATH_BLOCKED
    doc = json.loads((scratch / "o" / "status.json").read_text())
    assert doc["error"]["kind"] == "missing_object"
    assert not (scratch / "o" / "durable_ingestion_request.json").exists()


def test_collect_hash_mismatch_quarantines(
    scratch: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = MemoryDerivedStore()
    receipt = attempt_receipt()
    mkey = f"{_D}attempts/red-ok/MANIFEST.json"
    pkey = f"{_D}attempts/red-ok/pages/page-00001.jsonl"
    entry = manifest_entry(pkey, b"real body")
    entry["sha256"] = "0" * 64  # corrupted declaration
    store.put_if_absent(mkey, files_manifest([entry]))
    store.put_if_absent(pkey, b"real body")
    receipt["files_manifest_key"] = mkey
    _seed_commit(store)
    monkeypatch.setattr(return_path, "_store_for", lambda *a, **k: store)
    req = _write(scratch / "b.json", bootstrap_request())
    rec = _write(scratch / "receipt.json", receipt)
    rc = _run([
        "collect", "--request", rel(req), "--out", rel(scratch / "o"),
        "--receipt", rel(rec),
    ])
    assert rc == EXIT_SCHEMA_OR_CORRUPTION_QUARANTINE
    doc = json.loads((scratch / "o" / "status.json").read_text())
    assert doc["status"] == "quarantined"
    assert doc["error"]["kind"] == "hash_mismatch"


def test_collect_denied_connector_p19(
    scratch: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    _denied_store(monkeypatch)
    req = _write(scratch / "b.json", bootstrap_request())
    rec = _write(scratch / "receipt.json", attempt_receipt())
    rc = _run([
        "collect", "--request", rel(req), "--out", rel(scratch / "o"),
        "--receipt", rel(rec), "--store-uri", f"s3://{BUCKET}/",
    ])
    assert rc == EXIT_RETURN_PATH_BLOCKED
    out = capsys.readouterr().out
    doc = json.loads(out)
    assert doc["status"] == "return_blocked"
    assert doc["error"]["owner"] == "s3_return_path"
    for leak in ("AKIA", "X-Amz-Signature", "presign", "BEGIN "):
        assert leak not in out


def test_collect_receipt_over_cap(
    scratch: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        return_path, "_store_for", lambda *a, **k: MemoryDerivedStore(),
    )
    req = _write(scratch / "b.json", bootstrap_request())
    big = scratch / "receipt.json"
    big.write_text(json.dumps({"pad": "x" * (262144 + 10)}))
    rc = _run([
        "collect", "--request", rel(req), "--out", rel(scratch / "o"),
        "--receipt", rel(big),
    ])
    assert rc == EXIT_RETURN_PATH_BLOCKED
    doc = json.loads((scratch / "o" / "status.json").read_text())
    assert doc["error"]["kind"] == "budget_exceeded"


# ----------------------------------------------------------------------
# acknowledge — idempotent (attempt, query, page, hash) records
# ----------------------------------------------------------------------


def test_acknowledge_create_dedup_conflict(
    scratch: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = MemoryDerivedStore()
    monkeypatch.setattr(return_path, "_store_for", lambda *a, **k: store)
    req = _write(scratch / "b.json",
                 bootstrap_request(operation="acknowledge"))
    ack = _write(scratch / "ack.json", ack_doc())
    argv = [
        "acknowledge", "--request", rel(req), "--out", rel(scratch / "o1"),
        "--ack", rel(ack),
    ]
    assert _run(argv) == EXIT_COMPLETE
    doc = json.loads((scratch / "o1" / "status.json").read_text())
    assert doc["status"] == "completed"
    assert doc["deduplicated"] is False
    ack_keys = [k for k in store.list("") if "/acks/" in k]
    assert len(ack_keys) == 1
    envelope = json.loads((scratch / "o1" / "ack_envelope.json").read_text())
    assert envelope["s3_pointer"].startswith(f"s3://{BUCKET}/")
    assert len(json.dumps(envelope).encode()) <= 32768
    # Identical re-ack: deduplicated, never a conflict.
    assert _run([
        "acknowledge", "--request", rel(req), "--out", rel(scratch / "o2"),
        "--ack", rel(ack),
    ]) == EXIT_COMPLETE
    assert json.loads(
        (scratch / "o2" / "status.json").read_text()
    )["deduplicated"] is True
    # Conflicting bytes at the same ack_id: typed conflict, not a fake success.
    changed = _write(scratch / "ack2.json", ack_doc(
        ack_id=json.loads(
            (scratch / "o1" / "status.json").read_text()
        )["ack_id"], project_asset_ids=["asset-other"],
    ))
    rc = _run([
        "acknowledge", "--request", rel(req), "--out", rel(scratch / "o3"),
        "--ack", rel(changed),
    ])
    assert rc == EXIT_ACCESS_OR_RESOURCE_BLOCKED
    assert json.loads(
        (scratch / "o3" / "status.json").read_text()
    )["error"]["kind"] == "derived_conflict"


def test_acknowledge_denied_write_p19(
    scratch: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _denied_store(monkeypatch)
    req = _write(scratch / "b.json",
                 bootstrap_request(operation="acknowledge"))
    ack = _write(scratch / "ack.json", ack_doc())
    rc = _run([
        "acknowledge", "--request", rel(req), "--out", rel(scratch / "o"),
        "--ack", rel(ack), "--store-uri", f"s3://{BUCKET}/",
    ])
    assert rc == EXIT_RETURN_PATH_BLOCKED
    doc = json.loads((scratch / "o" / "status.json").read_text())
    assert doc["status"] == "return_blocked"
    assert doc["error"]["owner"] == "s3_return_path"


def test_acknowledge_missing_fields(scratch: Path) -> None:
    req = _write(scratch / "b.json",
                 bootstrap_request(operation="acknowledge"))
    ack = _write(scratch / "ack.json", {"receipt_id": "x"})
    rc = _run([
        "acknowledge", "--request", rel(req), "--out", rel(scratch / "o"),
        "--ack", rel(ack),
    ])
    assert rc == EXIT_INVALID_CONTRACT


# ----------------------------------------------------------------------
# edison ingest — typed blocked without connector, stubbed success
# ----------------------------------------------------------------------


def _ingest_manifest(scratch: Path) -> Path:
    body = b'{"row": 1}\n'
    fdir = scratch / "run" / "collected"
    fdir.mkdir(parents=True, exist_ok=True)
    (fdir / "page-1.jsonl").write_bytes(body)
    manifest = {
        "schema": "crusher-reducer-ingestion/v1",
        "request_id": "req-d4",
        "reduction_id": "red-ok",
        "files": [{
            "path": "collected/page-1.jsonl",
            "s3_key": f"{_D}attempts/red-ok/pages/page-1.jsonl",
            "sha256": sha(body),
            "bytes": len(body),
            "kind": "jsonl",
        }],
        "s3_pointer": f"s3://{BUCKET}/{_D}attempts/red-ok/RECEIPT.json",
    }
    return _write(scratch / "run" / "durable_ingestion_request.json", manifest)


def test_ingest_missing_key_typed_blocked(
    scratch: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    manifest = _ingest_manifest(scratch)
    monkeypatch.delenv("EDISON_PLATFORM_API_KEY", raising=False)
    rc = edison_ingest.main([
        "--manifest", rel(manifest), "--out", rel(scratch / "ing"),
    ])
    assert rc == EXIT_RETURN_PATH_BLOCKED
    receipt = json.loads(
        (scratch / "ing" / "ingestion_receipt.json").read_text()
    )
    assert receipt["status"] == "return_blocked"
    assert receipt["error_owner"] == "edison_connector"
    assert receipt["s3_pointer"].startswith("s3://")
    out = capsys.readouterr().out
    for leak in ("AKIA", "X-Amz-Signature", "BEGIN "):
        assert leak not in out


def test_ingest_stubbed_connector_uploads(
    scratch: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _ingest_manifest(scratch)
    uploaded = []

    def _store(name, file_path, metadata):
        uploaded.append(
            {"name": name, "file_path": file_path, "metadata": metadata},
        )
        return types.SimpleNamespace(
            data_storage=types.SimpleNamespace(
                id=f"asset-{len(uploaded)}",
            ),
        )

    fake = types.SimpleNamespace(
        EdisonClient=lambda api_key: types.SimpleNamespace(
            store_file_content=_store,
        ),
    )
    monkeypatch.setenv("EDISON_PLATFORM_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "edison_client", fake)
    rc = edison_ingest.main([
        "--manifest", rel(manifest), "--out", rel(scratch / "ing"),
    ])
    assert rc == EXIT_COMPLETE
    receipt = json.loads(
        (scratch / "ing" / "ingestion_receipt.json").read_text()
    )
    assert receipt["project_asset_ids"] == ["asset-1"]
    assert uploaded[0]["metadata"]["sha256"] == sha(b'{"row": 1}\n')


def test_ingest_connector_crash_typed_blocked(
    scratch: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live-canary regression: a connector API mismatch (e.g. calling the
    module-level ``astore_file_content`` that edison-client 0.18.0 does
    not export) must surface as a typed ``return_blocked`` receipt with
    ``connector_error`` — never a bare traceback exit."""
    manifest = _ingest_manifest(scratch)

    def _boom(name, file_path, metadata):
        raise AttributeError(
            "module 'edison_client' has no attribute 'astore_file_content'",
        )

    fake = types.SimpleNamespace(
        EdisonClient=lambda api_key: types.SimpleNamespace(
            store_file_content=_boom,
        ),
    )
    monkeypatch.setenv("EDISON_PLATFORM_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "edison_client", fake)
    rc = edison_ingest.main([
        "--manifest", rel(manifest), "--out", rel(scratch / "ing"),
    ])
    assert rc == EXIT_RETURN_PATH_BLOCKED
    receipt = json.loads(
        (scratch / "ing" / "ingestion_receipt.json").read_text()
    )
    assert receipt["status"] == "return_blocked"
    assert receipt["error"]["kind"] == "connector_error"
    assert receipt["error"]["owner"] == "edison_connector"


def test_ingest_hash_mismatch_quarantines(
    scratch: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _ingest_manifest(scratch)
    (scratch / "run" / "collected" / "page-1.jsonl").write_bytes(b"mutated")
    monkeypatch.setenv("EDISON_PLATFORM_API_KEY", "test-key")
    rc = edison_ingest.main([
        "--manifest", rel(manifest), "--out", rel(scratch / "ing"),
    ])
    assert rc == EXIT_SCHEMA_OR_CORRUPTION_QUARANTINE
    receipt = json.loads(
        (scratch / "ing" / "ingestion_receipt.json").read_text()
    )
    assert receipt["status"] == "quarantined"


# ----------------------------------------------------------------------
# worker attempt receipt — the durable object the poll waits for
# ----------------------------------------------------------------------


def test_worker_writes_attempt_receipt(scratch: Path) -> None:
    src = scratch / "src"
    src.mkdir()
    (src / "fused.zip").write_bytes(fused_zip())
    request = {
        "reduction_id": "red-canary",
        "snapshot_id": "snap-1",
        "budgets": _budgets(),
        "source_root": str(src),
        "shard_size": 1,
        "utc": "2026-01-01T00:00:00Z",
        "sources": [{
            "uri": "fused.zip", "family": "campaign_summary_zip",
            "source_id": "fused.zip", "campaign_id": "camp1",
        }],
    }
    req = _write(scratch / "req.json", request)
    out_dir = scratch / "derived"
    rc = worker.main([
        "--phase", "materialize",
        "--request-uri", rel(req),
        "--out-uri", f"dir://{rel(out_dir)}",
    ])
    assert rc == worker.EXIT_COMPLETE
    receipt = json.loads(
        (out_dir / _D / "attempts/red-canary/RECEIPT.json").read_text()
    )
    assert receipt["status"] == "completed"
    assert receipt["files_manifest_key"].endswith("MANIFEST.json")


def test_worker_failed_attempt_receipt_not_successful(
    scratch: Path,
) -> None:
    """A failed attempt writes a typed receipt — never one that reads as
    success (the return leg must not collect a failure as completed)."""
    src = scratch / "src"
    src.mkdir()
    request = {
        "reduction_id": "red-fail",
        "snapshot_id": "snap-1",
        "budgets": _budgets(),
        "source_root": str(src),
        "shard_size": 1,
        "utc": "2026-01-01T00:00:00Z",
        "sources": [{
            "uri": "absent.zip", "family": "campaign_summary_zip",
            "source_id": "absent.zip", "campaign_id": "camp1",
        }],
    }
    req = _write(scratch / "req.json", request)
    out_dir = scratch / "derived"
    rc = worker.main([
        "--phase", "materialize",
        "--request-uri", rel(req),
        "--out-uri", f"dir://{rel(out_dir)}",
    ])
    assert rc != worker.EXIT_COMPLETE
    receipt = json.loads(
        (out_dir / _D / "attempts/red-fail/RECEIPT.json").read_text()
    )
    # The receipt must never read as a success: the typed status is the
    # failure evidence even when no error detail exists (zero processed
    # sources → partial coverage).
    assert receipt["status"] in (
        "failed", "partial", "blocked", "quarantined", "return_blocked",
    )


# ----------------------------------------------------------------------
# workflow structure — gating, literal argv, dedup, bounded poll
# ----------------------------------------------------------------------


def test_return_workflow_gated_validated_bounded() -> None:
    doc = yaml.safe_load(
        (REPO_ROOT / ".github/workflows/campaign_return.yml").read_text()
    )
    inputs = doc[True]["workflow_dispatch"]["inputs"]
    assert inputs["dry_run"]["default"] is True
    assert inputs["edison_ingest"]["default"] is True
    assert "campaign-return-${{ inputs.attempt_id }}" in (
        doc["concurrency"]["group"]
    )
    for job in doc["jobs"].values():
        assert job["environment"] == "aws-campaign"
        for step in job["steps"]:
            uses = step.get("uses", "")
            if uses:
                repo, _, ref = uses.partition("@")
                assert len(ref) == 40 and all(
                    c in "0123456789abcdef" for c in ref
                ), f"unpinned action: {uses}"
            run = step.get("run", "")
            assert "${{" not in run, "input injection surface in run:"
    steps = [s for j in doc["jobs"].values() for s in j["steps"]]
    names = " ".join(s.get("name", "") for s in steps)
    assert "Validate inputs" in names
    assert "Bounded poll" in names
    assert "deduplicated" in " ".join(s.get("run", "") for s in steps)
    # The ack write runs under the dispatch role; collect/ingest under collector.
    ack_job = doc["jobs"]["acknowledge"]
    roles = [
        s.get("with", {}).get("role-to-assume", "")
        for s in ack_job["steps"]
    ]
    assert any("DISPATCH_ROLE_ARN" in r for r in roles)


def test_dispatch_workflow_unchanged_shape() -> None:
    doc = yaml.safe_load(
        (REPO_ROOT / ".github/workflows/campaign_reduction.yml").read_text()
    )
    inputs = doc[True]["workflow_dispatch"]["inputs"]
    assert inputs["dry_run"]["default"] is True
    assert doc["jobs"]["dispatch"]["environment"] == "aws-campaign"


# ----------------------------------------------------------------------
# no credential leakage across emitted docs
# ----------------------------------------------------------------------


def test_no_credentials_or_signed_urls_in_emitted_docs(
    scratch: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = MemoryDerivedStore()
    receipt = _seed_collect(store)
    monkeypatch.setattr(return_path, "_store_for", lambda *a, **k: store)
    req = _write(scratch / "b.json", bootstrap_request())
    rec = _write(scratch / "receipt.json", receipt)
    ack = _write(scratch / "ack.json", ack_doc())
    assert _run([
        "collect", "--request", rel(req), "--out", rel(scratch / "c"),
        "--receipt", rel(rec),
    ]) == EXIT_COMPLETE
    assert _run([
        "acknowledge", "--request", rel(req), "--out", rel(scratch / "a"),
        "--ack", rel(ack),
    ]) == EXIT_COMPLETE
    emitted = "".join(
        p.read_text() for p in scratch.rglob("*.json") if "scratch" in str(p)
    )
    for leak in ("AKIA", "X-Amz-Signature", "X-Amz-Credential",
                 "EDISON_PLATFORM_API_KEY", "BEGIN PRIVATE"):
        assert leak not in emitted
