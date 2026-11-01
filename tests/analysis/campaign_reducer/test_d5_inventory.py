"""D5 cold-inventory tests — paginated listing, resumable caps,
denied-root completeness blocking, VersionId provenance, scope delta
vs the dated Oct-19 register, plus workflow/request wiring checks.

Everything offline-rigged: a stubbed S3 client object (no moto, no
network, no boto3 import) injected through ``inventory._s3_client``.
P06 (all-scope catalog: every register row represented with a fresh
observation — never an asserted-unique campaign) and P21 (restricted
roots block completeness explicitly rather than vanishing) are the
scientific fixtures this module answers to.
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from botocore.exceptions import ClientError
from conftest import rel
from d4_fixtures import BUCKET, bootstrap_request

from picard_framework.analysis.campaign_reducer import cli, contracts, inventory
from picard_framework.analysis.campaign_reducer.materialize import (
    DERIVED_ROOT,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
_REGISTER_SHA = contracts.sha256(contracts.CAMPAIGN_COVERAGE)


@pytest.fixture(autouse=True)
def _forbid_external(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*a, **k):
        raise AssertionError("network/subprocess forbidden in offline tests")

    monkeypatch.setattr(socket, "create_connection", _raise)
    monkeypatch.setattr(socket.socket, "connect", _raise)
    monkeypatch.setattr(subprocess, "run", _raise)
    monkeypatch.setattr(subprocess, "Popen", _raise)
    monkeypatch.setitem(sys.modules, "boto3", None)


def _write(path: Path, doc) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc))
    return path


def _request(**over) -> dict:
    doc = bootstrap_request(request_id="req-d5", operation="inventory")
    doc["scope_register_sha256"] = _REGISTER_SHA
    doc.update(over)
    return doc


class FakeS3:
    """Paginated fake for ListObjectsV2 / ListObjectVersions.

    ``objects`` maps key → (size, storage_class); ``versions`` maps key →
    [version_ids]. ``deny`` is a set of prefixes whose listing calls raise
    AccessDenied; ``deny_versions`` does the same for the versions pass.
    """

    def __init__(
        self, objects: dict, *, versions: dict | None = None,
        deny: tuple = (), deny_versions: tuple = (),
        top_level: tuple = ("campaign/",),
    ) -> None:
        self.objects = dict(sorted(objects.items()))
        self.versions = versions or {}
        self.deny = deny
        self.deny_versions = deny_versions
        self.top_level = top_level
        self.list_calls: list[dict] = []

    def _denied(self, prefix: str, deny: tuple, op: str) -> None:
        if any(prefix.startswith(p) or p.startswith(prefix) for p in deny):
            raise ClientError(
                {"Error": {"Code": "AccessDenied"},
                 "ResponseMetadata": {"HTTPStatusCode": 403}},
                op,
            )

    def list_objects_v2(self, **kw) -> dict:
        self.list_calls.append(dict(kw))
        prefix = kw.get("Prefix", "")
        if kw.get("Delimiter") == "/":
            return {"CommonPrefixes": [{"Prefix": p}
                                       for p in self.top_level],
                    "IsTruncated": False}
        self._denied(prefix, self.deny, "ListObjectsV2")
        keys = [k for k in self.objects if k.startswith(prefix)]
        max_keys = kw.get("MaxKeys", 1000)
        start = 0
        token = kw.get("ContinuationToken")
        if token:
            start = int(token)
        page = keys[start:start + max_keys]
        out = {
            "Contents": [
                {
                    "Key": k,
                    "Size": self.objects[k][0],
                    "StorageClass": self.objects[k][1],
                    "ETag": '"etag-%s"' % k[-8:],
                    "LastModified": "2026-10-20T00:00:00+00:00",
                }
                for k in page
            ],
            "KeyCount": len(page),
        }
        if start + max_keys < len(keys):
            out["NextContinuationToken"] = str(start + max_keys)
        return out

    def list_object_versions(self, **kw) -> dict:
        self.list_calls.append(dict(kw))
        prefix = kw.get("Prefix", "")
        self._denied(prefix, self.deny_versions, "ListObjectVersions")
        rows = [
            (k, v) for k in sorted(self.versions) if k.startswith(prefix)
            for v in self.versions[k]
        ]
        marker = int(kw.get("KeyMarker") or 0)
        page = rows[marker:marker + 2]
        out = {
            "Versions": [
                {
                    "Key": k,
                    "VersionId": v,
                    "IsLatest": True,
                    "Size": self.objects.get(k, (0, "STANDARD"))[0],
                    "StorageClass": self.objects.get(k, (0, "STANDARD"))[1],
                    "LastModified": "2026-10-20T00:00:00+00:00",
                }
                for k, v in page
            ],
            "DeleteMarkers": [],
        }
        if marker + 2 < len(rows):
            out["IsTruncated"] = True
            out["NextKeyMarker"] = str(marker + 2)
            out["NextVersionIdMarker"] = "v-marker"
        return out


def _invoke(scratch: Path, client: FakeS3, monkeypatch, request: dict,
            extra: list[str] | None = None) -> int:
    monkeypatch.setattr(inventory, "_s3_client", lambda *a, **k: client)
    req = _write(scratch / "inventory_request.json", request)
    argv = ["inventory", "--request", rel(req),
            "--out", rel(scratch / "out")]
    argv += extra or []
    return cli.main(argv)


def test_pages_truncate_with_continuation(
    scratch: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    objects = {
        f"campaign/camp_a/run_{i}/summary.zip": (100 + i, "STANDARD")
        for i in range(5)
    }
    objects[f"{DERIVED_ROOT}/attempts/x/RECEIPT.json"] = (10, "STANDARD")
    objects["campaign/camp_b/_scan_rows.json"] = (50, "STANDARD")
    client = FakeS3(
        objects,
        versions={
            "campaign/camp_a/run_0/summary.zip": ["v-aaa", "v-bbb"],
        },
    )
    rc = _invoke(scratch, client, monkeypatch, _request())
    assert rc == contracts.EXIT_COMPLETE
    inv = json.loads((scratch / "out" / "frozen_inventory.json").read_text())
    assert inv["status"] == "completed"
    root = inv["roots"][0]
    assert root["exhausted"] is True
    # Six listed objects; the derived receipt is excluded, never absent.
    assert root["objects"] == 6
    assert root["excluded_derived_objects"] == 1
    # Every listing row carries identity/size/class; versions live apart.
    page = scratch / "out" / root["manifest_pages"][0]["path"]
    rows = [json.loads(line) for line in page.read_text().splitlines()]
    scan_row = next(r for r in rows if r["key"].endswith("_scan_rows.json"))
    assert scan_row["is_scan_rows_key"] is True
    assert all("version_id" not in r for r in rows)
    vpages = inv["version_roots"][0]["manifest_pages"]
    vrows = [
        json.loads(line)
        for p in vpages
        for line in (scratch / "out" / p["path"]).read_text().splitlines()
    ]
    assert {r["version_id"] for r in vrows} == {"v-aaa", "v-bbb"}
    assert all(r["provenance"] == "list_object_versions" for r in vrows)


def test_resume_across_budget_cap(
    scratch: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    objects = {
        f"campaign/camp_a/run_{i}/s.zip": (10, "STANDARD")
        for i in range(2100)  # > one MaxKeys=1000 page
    }
    client = FakeS3(objects)
    request = _request()
    request["budgets"]["max_list_pages"] = 2  # discovery + ~1 page
    rc = _invoke(scratch, client, monkeypatch, request)
    assert rc == contracts.EXIT_BUDGET_STOPPED_CHECKPOINTED
    state = json.loads(
        (scratch / "out" / "inventory_state.json").read_text()
    )
    root_state = state["roots"]["campaign/"]
    assert root_state["exhausted"] is False
    assert root_state["next_token"]
    first_calls = len(client.list_calls)
    # Resume: completed pages are not restarted — the retained token
    # continues the same listing; a generous budget finishes it.
    state_src = scratch / "out" / "inventory_state.json"
    resume_req = _request()
    resume_req["budgets"]["max_list_pages"] = 100
    rc = _invoke(
        scratch, client, monkeypatch, resume_req,
        extra=["--resume-state", rel(state_src)],
    )
    # resume still hits the versions pass + probes within the same budget
    assert rc in (
        contracts.EXIT_COMPLETE,
        contracts.EXIT_PARTIAL_COVERAGE,
        contracts.EXIT_BUDGET_STOPPED_CHECKPOINTED,
    )
    state2 = json.loads(
        (scratch / "out" / "inventory_state.json").read_text()
    )
    resumed = state2["roots"]["campaign/"]
    assert resumed["pages_completed"] > root_state["pages_completed"]
    tokens = [
        c.get("ContinuationToken") for c in client.list_calls[first_calls:]
        if c.get("Prefix") == "campaign/"
    ]
    assert tokens
    assert tokens[0] == root_state["next_token"]


def test_denied_root_blocks_completeness_not_absent(
    scratch: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeS3(
        {"campaign/ok/s.zip": (5, "STANDARD")},
        deny=("restricted/",),
    )
    request = _request(
        source_roots_allowlist=["campaign/", "restricted/"],
    )
    rc = _invoke(scratch, client, monkeypatch, request)
    assert rc == contracts.EXIT_ACCESS_OR_RESOURCE_BLOCKED
    coverage = json.loads((scratch / "out" / "coverage.json").read_text())
    blocked = coverage["blocked_completeness"]
    kinds = {(b["scope"], b["kind"]) for b in blocked}
    assert ("root_listing", "access_denied") in kinds
    denied = next(b for b in blocked if b["root"] == "restricted/")
    assert denied["owner"] == "s3_listing"
    inv = json.loads((scratch / "out" / "frozen_inventory.json").read_text())
    restricted = next(r for r in inv["roots"] if r["root"] == "restricted/")
    assert restricted["exhausted"] is False
    assert restricted["objects"] == 0


def test_versions_denied_typed_blocked(
    scratch: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeS3(
        {"campaign/ok/s.zip": (5, "STANDARD")},
        deny_versions=("campaign/",),
    )
    rc = _invoke(scratch, client, monkeypatch, _request())
    assert rc == contracts.EXIT_ACCESS_OR_RESOURCE_BLOCKED
    coverage = json.loads((scratch / "out" / "coverage.json").read_text())
    scopes = {b["scope"] for b in coverage["blocked_completeness"]}
    assert "version_provenance" in scopes


def test_scope_delta_vs_dated_register(
    scratch: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    register = contracts.load(contracts.CAMPAIGN_COVERAGE)
    first = next(
        r for r in register if r["record_kind"] == "historical_prefix"
    )
    objects = {first["prefix"] + "obj.zip": (10, "STANDARD")}
    client = FakeS3(objects)
    rc = _invoke(scratch, client, monkeypatch, _request())
    assert rc in (
        contracts.EXIT_COMPLETE, contracts.EXIT_ACCESS_OR_RESOURCE_BLOCKED,
    )
    inv = json.loads((scratch / "out" / "frozen_inventory.json").read_text())
    rows = {r["record_id"]: r for r in inv["families"]}
    # All 218 register rows represented, each with a fresh observation —
    # never silently omitted (P06).
    assert len(inv["families"]) == 218
    observed = rows[first["record_id"]]
    assert observed["fresh_observation"] == "present"
    # Dated Oct-19 counts retained as dated — never overwritten by fresh.
    assert observed["dated_oct19"]["objects_listed"] == (
        first["historical_object_metadata"]["objects_listed"]
    )
    assert observed["dated_oct19"]["counts_are_dated_not_current"] is True
    mega = next(
        r for r in inv["families"]
        if r["prefix"] == "campaign/noro_age_food_01_mega/"
    )
    assert mega["fresh_observation"] in {"absent", "present", "blocked"}
    delta = json.loads((scratch / "out" / "scope_delta.json").read_text())
    assert delta["dated_register"]["records"] == 218
    assert delta["dated_register"]["counts_are_dated_not_current"] is True
    assert delta["derived_excluded"] is True
    mega_delta = next(
        r for r in delta["registered_absent_oct19_fresh_observation"]
        if r["prefix"] == "campaign/noro_age_food_01_mega/"
    )
    assert mega_delta["fresh_observation"] == mega["fresh_observation"]


def test_register_sha_mismatch_blocks(
    scratch: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeS3({})
    request = _request(scope_register_sha256="0" * 64)
    rc = _invoke(scratch, client, monkeypatch, request)
    assert rc == contracts.EXIT_ADMISSION_REQUIRED_OR_EXCEEDED
    doc = json.loads((scratch / "out" / "status.json").read_text())
    assert doc["error"]["kind"] == "scope_register_mismatch"
    assert not client.list_calls


def test_expired_admission_blocks(
    scratch: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeS3({})
    request = _request()
    request["admission"]["expires_utc"] = "2020-01-01T00:00:00Z"
    rc = _invoke(scratch, client, monkeypatch, request)
    assert rc == contracts.EXIT_ADMISSION_REQUIRED_OR_EXCEEDED
    assert not client.list_calls


def test_wrong_operation_rejected(
    scratch: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeS3({})
    request = _request()
    request["operation"] = "collect"
    monkeypatch.setattr(inventory, "_s3_client", lambda *a, **k: client)
    req = _write(scratch / "b.json", request)
    rc = cli.main([
        "inventory", "--request", rel(req), "--out", rel(scratch / "o"),
    ])
    assert rc == contracts.EXIT_INVALID_CONTRACT


# ----------------------------------------------------------------------
# Wiring: request doc + workflow
# ----------------------------------------------------------------------


def test_committed_request_doc_validates(tmp_path: Path) -> None:
    doc_path = (
        REPO_ROOT / "docs/campaign_reduction/canary/inventory_request.json"
    )
    doc = json.loads(doc_path.read_text())
    assert doc["operation"] == "inventory"
    assert doc["scope_register_sha256"] == _REGISTER_SHA
    assert doc["source_bucket"] == BUCKET
    assert "campaign/" in doc["source_roots_allowlist"]
    # The semantic gate must pass the committed doc (same rules as
    # ``analysis validate --request-kind bootstrap``).
    from picard_framework.analysis.campaign_reducer import validate as _v
    schema = contracts.load(contracts.BOOTSTRAP_REQUEST_SCHEMA)
    canonical = contracts.load(contracts.CANONICAL_INTERFACE)
    reasons = _v._semantic_reasons(doc, "bootstrap", schema, canonical)
    assert not reasons
    assert not _v._schema_errors(doc, schema)


def test_inventory_workflow_structure() -> None:
    wf = yaml.safe_load(
        (REPO_ROOT / ".github/workflows/campaign_inventory.yml").read_text()
    )
    assert wf.get(True) or wf.get("on")  # yaml parses 'on' as True
    dispatch = wf.get("on") or wf.get(True)
    inputs = dispatch["workflow_dispatch"]["inputs"]
    assert inputs["dry_run"]["default"] is True
    assert inputs["request_sha256"]["required"] is True
    job = wf["jobs"]["inventory"]
    assert job["environment"] == "aws-campaign"
    assert job["permissions"]["id-token"] == "write"
    steps = " ".join(
        str(step) for step in job["steps"]
    )
    assert "AWS_REDUCTION_COLLECTOR_ROLE_ARN" in steps
    assert "analysis inventory" in steps
