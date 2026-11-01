"""D3 deployability tests — S3 store/transport wiring, jobdef binding,
collector guard, and workflow structure.

Everything runs offline: the S3 client is a stub object (no moto, no
network, real ``botocore.exceptions.ClientError`` codes so the
transport/store error mapping is exercised), and the jobdef renderer is
diffed as data. The ``boto3`` import stays forbidden — the stub bypasses
it entirely; ``botocore`` remains importable because the stub raises its
real ``ClientError`` type.
"""
from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
import io
import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from botocore.exceptions import ClientError
from zip_builders import build_zip, member

from picard_framework.analysis.campaign_reducer import worker as worker_mod
from picard_framework.analysis.campaign_reducer.derived_store import (
    DerivedConflict,
    DerivedStoreError,
)
from picard_framework.analysis.campaign_reducer.ledger import BUDGET_FIELDS
from picard_framework.analysis.campaign_reducer.s3_store import S3DerivedStore
from picard_framework.analysis.campaign_reducer.worker import (
    EXIT_BLOCKED,
    EXIT_COMPLETE,
    EXIT_INVALID_CONTRACT,
    main,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import campaign_collect_guard as guard  # noqa: E402

_DERIVED = "campaign/_derived/reducer/v1/"


@pytest.fixture(autouse=True)
def _forbid_external(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*a, **k):
        raise AssertionError("network/subprocess forbidden in offline tests")

    monkeypatch.setattr(socket, "create_connection", _raise)
    monkeypatch.setattr(socket.socket, "connect", _raise)
    monkeypatch.setattr(subprocess, "run", _raise)
    monkeypatch.setattr(subprocess, "Popen", _raise)
    monkeypatch.setitem(sys.modules, "boto3", None)


def _load_launcher() -> object:
    """Import the extensionless scripts/campaign file as a module."""
    loader = importlib.machinery.SourceFileLoader(
        "campaign_launcher", str(REPO_ROOT / "scripts" / "campaign"),
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class _StubS3Client:
    """Minimal boto3-s3 stand-in raising real ClientError codes."""

    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}
        self.put_calls: list[tuple[str, str, str | None]] = []

    @staticmethod
    def _err(code: str, op: str, status: int | None = None) -> ClientError:
        resp: dict = {"Error": {"Code": code}}
        if status is not None:
            resp["ResponseMetadata"] = {"HTTPStatusCode": status}
        return ClientError(resp, op)

    @staticmethod
    def _etag(body: bytes) -> str:
        return '"' + hashlib.sha256(body).hexdigest() + '"'

    def head_object(self, Bucket: str, Key: str, **_kw):
        body = self.objects.get((Bucket, Key))
        if body is None:
            raise self._err("404", "HeadObject", 404)
        return {
            "ContentLength": len(body),
            "ETag": self._etag(body),
            "VersionId": "v1",
            "StorageClass": "STANDARD",
        }

    def get_object(self, Bucket: str, Key: str, **kw):
        body = self.objects.get((Bucket, Key))
        if body is None:
            raise self._err("NoSuchKey", "GetObject", 404)
        etag = self._etag(body)
        if kw.get("IfMatch") and kw["IfMatch"] != etag:
            raise self._err("PreconditionFailed", "GetObject", 412)
        if kw.get("VersionId") and kw["VersionId"] != "v1":
            raise self._err("NoSuchVersion", "GetObject", 404)
        status = 200
        content_range = None
        if kw.get("Range"):
            rng = kw["Range"][len("bytes="):]
            start_s, _, end_s = rng.partition("-")
            start, end = int(start_s), int(end_s)
            last = min(end, len(body) - 1)
            content_range = f"bytes {start}-{last}/{len(body)}"
            body = body[start:last + 1]
            status = 206
        return {
            "Body": io.BytesIO(body),
            "ETag": etag,
            "VersionId": "v1",
            "ContentRange": content_range,
            "ResponseMetadata": {"HTTPStatusCode": status},
        }

    def put_object(self, Bucket: str, Key: str, Body: bytes, **kw):
        self.put_calls.append((Bucket, Key, kw.get("IfNoneMatch")))
        if kw.get("IfNoneMatch") == "*" and (Bucket, Key) in self.objects:
            raise self._err("PreconditionFailed", "PutObject", 412)
        self.objects[(Bucket, Key)] = Body
        return {"ETag": self._etag(Body)}

    def list_objects_v2(self, Bucket: str, Prefix: str, **kw):
        keys = sorted(k for b, k in self.objects
                      if b == Bucket and k.startswith(Prefix))
        return {"Contents": [{"Key": k} for k in keys]}


# ---------------------------------------------------------------------
# S3DerivedStore
# ---------------------------------------------------------------------


def test_s3_store_create_only_and_idempotent_resume() -> None:
    client = _StubS3Client()
    store = S3DerivedStore(client, "bkt", _DERIVED)
    assert store.put_if_absent("attempts/r1/A.json", b"{}") == hashlib.sha256(
        b"{}"
    ).hexdigest()
    # Every put carried the If-None-Match:* create-only condition.
    assert all(cond == "*" for _, _, cond in client.put_calls)
    # Identical re-derivation is a resume, not a conflict.
    assert store.put_idempotent("attempts/r1/A.json", b"{}") is False
    assert store.put_idempotent("attempts/r1/B.json", b"1") is True
    with pytest.raises(DerivedConflict):
        store.put_if_absent("attempts/r1/A.json", b"different")


def test_s3_store_get_head_list_and_denials() -> None:
    client = _StubS3Client()
    store = S3DerivedStore(client, "bkt", _DERIVED)
    store.put_if_absent("attempts/r1/COMMIT.json", b'{"status":"completed"}')
    assert store.get("attempts/r1/COMMIT.json") == b'{"status":"completed"}'
    assert store.head("attempts/r1/COMMIT.json")["bytes"] == 22
    assert store.head("attempts/r1/absent") is None
    assert store.list("attempts/") == ["attempts/r1/COMMIT.json"]
    with pytest.raises(DerivedStoreError):
        store.get("attempts/r1/absent")
    with pytest.raises(DerivedStoreError):
        store.put_if_absent("../escape", b"x")


# ---------------------------------------------------------------------
# worker s3:// wiring (stubbed client — no moto, no network)
# ---------------------------------------------------------------------


def _s3_request() -> tuple[dict, bytes]:
    fused = build_zip([
        member("run_1/summary.json",
               json.dumps({"attack_rate": 0.5}).encode()),
        member("run_2/summary.json",
               json.dumps({"attack_rate": 0.25}).encode()),
    ])
    request = {
        "reduction_id": "red-s3",
        "snapshot_id": "snap-s3",
        "budgets": dict.fromkeys(BUDGET_FIELDS, 1_000_000_000.0)
                   | {"safety_factor": 1.5},
        "source_root": "s3://bkt/campaign/camp1/",
        "shard_size": 1,
        "utc": "2026-01-01T00:00:00Z",
        "sources": [{
            "uri": "s3://bkt/campaign/camp1/fused.zip",
            "family": "campaign_summary_zip",
            "source_id": "fused.zip",
            "campaign_id": "camp1",
        }],
    }
    return request, fused


def test_worker_s3_materialize_end_to_end(
    capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _StubS3Client()
    monkeypatch.setattr(worker_mod, "_s3_client", lambda *a, **k: client)
    request, fused = _s3_request()
    client.objects[("bkt", "campaign/camp1/fused.zip")] = fused
    req_key = _DERIVED + "requests/red-s3.json"
    client.objects[("bkt", req_key)] = json.dumps(request).encode()

    rc = main([
        "--phase", "materialize",
        "--request-uri", f"s3://bkt/{req_key}",
        "--out-uri", f"s3://bkt/{_DERIVED}",
    ])
    assert rc == EXIT_COMPLETE
    assert json.loads(capsys.readouterr().out)["status"] == "completed"
    commit = [
        k for b, k in client.objects if k.endswith("COMMIT.json")
    ]
    assert commit
    # Derived writes stayed inside the derived namespace.
    written = {k for b, k in client.objects} - {
        "campaign/camp1/fused.zip", req_key,
    }
    assert all(k.startswith(_DERIVED) for k in written)


def test_worker_s3_sha_pin_and_mixed_bucket_rejection(
    capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _StubS3Client()
    monkeypatch.setattr(worker_mod, "_s3_client", lambda *a, **k: client)
    request, fused = _s3_request()
    req_key = _DERIVED + "requests/red-s3.json"
    client.objects[("bkt", req_key)] = json.dumps(request).encode()
    # Bad sha -> invalid contract before any source read.
    rc = main([
        "--phase", "materialize",
        "--request-uri", f"s3://bkt/{req_key}",
        "--request-sha256", "0" * 64,
    ])
    assert rc == EXIT_INVALID_CONTRACT
    client.objects[("bkt", "campaign/camp1/fused.zip")] = fused
    request["sources"] = [
        request["sources"][0],
        dict(request["sources"][0],
             uri="s3://other-bucket/campaign/camp1/fused.zip",
             source_id="other"),
    ]
    client.objects[("bkt", req_key)] = json.dumps(request).encode()
    rc = main([
        "--phase", "materialize",
        "--request-uri", f"s3://bkt/{req_key}",
        "--out-uri", f"s3://bkt/{_DERIVED}",
    ])
    assert rc == EXIT_INVALID_CONTRACT


def test_worker_s3_missing_request_blocks(
    capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _StubS3Client()
    monkeypatch.setattr(worker_mod, "_s3_client", lambda *a, **k: client)
    rc = main([
        "--phase", "materialize",
        "--request-uri", f"s3://bkt/{_DERIVED}requests/absent.json",
    ])
    assert rc == EXIT_BLOCKED


# ---------------------------------------------------------------------
# analysis jobdef binding (rendered-diff only)
# ---------------------------------------------------------------------

_BINDING = {
    "name": "reducer",
    "image_repo": "picard-boundary-analysis",
    "image_digest": "sha256:" + "a" * 64,
    "job_role_name": "picard-reducer-job-role",
    "execution_role_name": "picard-campaign-execution-role",
    "vcpu": 2,
    "memory_mib": 8192,
    "timeout_seconds": 3600,
    "retry_attempts": 3,
    "log_group": "/aws/batch/picard-boundary-analysis",
}


def test_analysis_jobdef_renders_reducer_binding() -> None:
    launcher = _load_launcher()
    jobdef = launcher._render_analysis_jobdef(
        _BINDING, "994254241749", "us-east-1",
    )
    cp = jobdef["containerProperties"]
    assert jobdef["jobDefinitionName"] == "picard-reducer"
    assert cp["command"] == [
        "-m", "picard_framework.analysis.campaign_reducer.worker",
        "--phase", "<phase>",
        "--request-uri", "<immutable_s3_uri>",
        "--request-sha256", "<sha256>",
        "--shard-index", "<index>",
    ]
    assert cp["image"].endswith(
        f"picard-boundary-analysis@sha256:{'a' * 64}"
    )
    assert cp["jobRoleArn"].endswith(":role/picard-reducer-job-role")
    assert cp["executionRoleArn"].endswith(
        ":role/picard-campaign-execution-role",
    )
    assert jobdef["timeout"] == {"attemptDurationSeconds": 3600}
    assert jobdef["retryStrategy"]["attempts"] == 3
    assert (
        cp["logConfiguration"]["options"]["awslogs-group"]
        == "/aws/batch/picard-boundary-analysis"
    )


def test_analysis_jobdef_blocks_unsupported_and_incomplete() -> None:
    launcher = _load_launcher()
    account = "994254241749"
    region = "us-east-1"
    escaped = _BINDING | {"shell_escape": "; rm -rf /"}
    with pytest.raises(SystemExit, match="unsupported"):
        launcher._render_analysis_jobdef(escaped, account, region)
    incomplete = {k: v for k, v in _BINDING.items() if k != "job_role_name"}
    with pytest.raises(SystemExit, match="missing"):
        launcher._render_analysis_jobdef(incomplete, account, region)
    bad_digest = _BINDING | {"image_digest": "sha256:not-hex"}
    with pytest.raises(SystemExit, match="sha256"):
        launcher._render_analysis_jobdef(bad_digest, account, region)


def test_analysis_jobdef_tagged_image_form() -> None:
    launcher = _load_launcher()
    binding = {k: v for k, v in _BINDING.items() if k != "image_digest"}
    binding["image_tag"] = "reducer-v1"
    jobdef = launcher._render_analysis_jobdef(
        binding, "994254241749", "us-east-1",
    )
    assert jobdef["containerProperties"]["image"].endswith(
        "picard-boundary-analysis:reducer-v1"
    )


def test_campaign_jobdef_render_unchanged() -> None:
    """The shared template still renders the campaign binding verbatim."""
    launcher = _load_launcher()
    spec = {
        "name": "noro_probe",
        "image_tag": "campaign-x",
        "resources": {"vcpu": "4", "memory": "16384"},
    }
    jobdef = launcher._render_jobdef(spec, "994254241749", "us-east-1")
    cp = jobdef["containerProperties"]
    assert jobdef["jobDefinitionName"] == "picard-noro-probe"
    assert cp["command"][0] == "deploy/aws/campaign_entrypoint.py"
    assert cp["jobRoleArn"].endswith(":role/picard-campaign-job-role")


def test_analysis_spec_dry_run_writes_rendered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = _load_launcher()
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(_BINDING))
    monkeypatch.setattr(launcher, "_REPO_ROOT", tmp_path)
    rc = launcher.main([
        "submit", "--analysis-spec", str(spec_path),
        "--account", "994254241749", "--profile", "", "--dry-run",
    ])
    assert rc == 0
    rendered = tmp_path / "deploy" / "aws" / "jobdef_picard-reducer.rendered.json"
    jobdef = json.loads(rendered.read_text())
    assert (
        jobdef["containerProperties"]["command"][1]
        == "picard_framework.analysis.campaign_reducer.worker"
    )


# ---------------------------------------------------------------------
# collector guard + workflow structure regression
# ---------------------------------------------------------------------


def test_guard_legacy_key_rules_unchanged() -> None:
    guard.validate_legacy_key("campaign/foo/manifest.json")
    for bad in ("campaign/../x", "not-campaign/x", "campaign/",
                "campaign/a/../../b"):
        with pytest.raises(ValueError):
            guard.validate_legacy_key(bad)


def test_guard_derived_kind_ceilings() -> None:
    root = guard.DERIVED_ROOT
    assert guard.classify_derived_key(
        root + "queries/q1/pages/page-0001.jsonl",
    ) == ("page", guard.CEILING_PAGE)
    assert guard.classify_derived_key(
        root + "attempts/r1/COMMIT.json",
    ) == ("receipt", guard.CEILING_RECEIPT)
    assert guard.classify_derived_key(
        root + "issues/i1/envelope.json",
    ) == ("issue_envelope", guard.CEILING_ENVELOPE)
    assert guard.classify_derived_key(
        root + "attempts/r1/manifest.json",
    ) == ("index", guard.CEILING_INDEX)


def test_guard_derived_allowlist_and_manifest_caps() -> None:
    with pytest.raises(ValueError):
        guard.classify_derived_key("campaign/foo/run.zip")
    with pytest.raises(ValueError):
        guard.classify_derived_key("campaign/_derived/reducer/v1/../x")
    doc = {"entries": [
        {"uri": f"s3://bkt/{guard.DERIVED_ROOT}queries/q/pages/p.jsonl"},
        {"key": f"{guard.DERIVED_ROOT}attempts/r/manifest.json"},
    ]}
    keys = guard.iter_manifest_keys(doc)
    assert len(keys) == 2
    assert all(k.startswith(guard.DERIVED_ROOT) for k in keys)
    doc["entries"].append({"uri": "campaign/not-derived/x"})
    with pytest.raises(ValueError):
        guard.iter_manifest_keys(doc)


def test_collect_workflow_legacy_shape_retained() -> None:
    doc = yaml.safe_load(
        (REPO_ROOT / ".github/workflows/campaign_collect.yml").read_text()
    )
    inputs = doc[True]["workflow_dispatch"]["inputs"]
    assert inputs["exact_key"]["default"] == ""
    assert inputs["max_fetch_bytes"]["default"] == "52428800"
    for new in ("derived_key", "derived_manifest", "derived_prefix"):
        assert new in inputs
    job = doc["jobs"]["collect"]
    assert job["environment"] == "aws-campaign"
    names = [s.get("name", "") for s in job["steps"]]
    assert any("exact-object fetch" in n for n in names)
    assert any("denied" in n for n in names) or any(
        "Denial probe" in n for n in names
    )


def test_reduction_workflow_gated_and_validated() -> None:
    doc = yaml.safe_load(
        (REPO_ROOT / ".github/workflows/campaign_reduction.yml").read_text()
    )
    inputs = doc[True]["workflow_dispatch"]["inputs"]
    assert inputs["phase"]["type"] == "choice"
    assert inputs["dry_run"]["default"] is True
    job = doc["jobs"]["dispatch"]
    assert job["environment"] == "aws-campaign"
    names = [s.get("name", "") for s in job["steps"]]
    assert any("Validate inputs" in n for n in names)
    submit = next(s for s in job["steps"] if "Submit reducer job" in s.get("name", ""))
    assert "dry_run == false" in submit["if"]
