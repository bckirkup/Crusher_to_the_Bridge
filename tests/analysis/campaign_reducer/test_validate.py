"""tests/analysis/campaign_reducer/test_validate.py — offline ``analysis validate``.

Covers all three ``--request-kind`` schemas: every shipped BLOCKED fixture
must produce a blocked nonzero exit; a fully filled request passes; unset,
non-finite or conflated fields block. ``None`` is never unlimited.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from picard_framework.analysis.campaign_reducer import cli, contracts

CONTRACTS = contracts.CONTRACTS_DIR
BLOCKED_REQUEST = CONTRACTS / "BLOCKED_REQUEST.template.json"
BLOCKED_BOOTSTRAP = CONTRACTS / "BLOCKED_BOOTSTRAP.template.json"
BLOCKED_QUERY = CONTRACTS / "QUERY.blocked_example.json"

_FAKE_SHA = "a" * 64


def _validate(path: Path, kind: str, out: Path) -> tuple[int, dict]:
    exit_code = cli.main([
        "validate", "--request", str(path),
        "--request-kind", kind, "--out", str(out),
    ])
    report = json.loads((out / "validation.json").read_text(encoding="utf-8"))
    return exit_code, report


def valid_execution_request() -> dict:
    doc = json.loads(BLOCKED_REQUEST.read_text(encoding="utf-8"))
    doc.update({
        "purpose": "D6 bounded PS01 pilot",
        "reducer_image_digest": f"sha256:{_FAKE_SHA}",
        "adapter_registry_sha256": _FAKE_SHA,
        "scope_register_sha256": _FAKE_SHA,
        "source_bucket": "crusherbucket-994254241749-us-east-1-an",
        "derived_root": "campaign/_derived/reducer/v1/",
        "source_prefix_allowlist": ["campaign/"],
        "inventory_snapshot": {"id": "inv-2026-10-19", "sha256": _FAKE_SHA},
        "job_binding": {
            "queue_arn": "arn:aws:batch:us-east-1:994254241749:job-queue/picard-analysis",
            "job_definition_revision_arn":
                "arn:aws:batch:us-east-1:994254241749:job-definition/reducer:3",
            "job_role_arn": "arn:aws:iam::994254241749:role/reducer-app",
            "execution_role_arn": "arn:aws:iam::994254241749:role/reducer-exec",
            "image_digest": f"sha256:{_FAKE_SHA}",
            "platform": "LINUX",
            "vcpu": 2,
            "memory_mib": 8192,
            "timeout_seconds": 3600,
        },
        "budgets": {field: 1000 for field in doc["budgets"]},
        "approval": {
            "admission_id": "adm-1",
            "scope_hash": _FAKE_SHA,
            "quote_id": "q-1",
            "approved_cost_usd": 12.0,
            "expires_utc": "2026-12-31T00:00:00Z",
        },
        "phase": "pilot",
        "request_id": "req-1",
        "reduction_id": "red-1",
        "implementation_sha": "0" * 40,
        "quote": {
            "quote_id": "q-1",
            "uri": "s3://bucket/quotes/q-1.json",
            "sha256": _FAKE_SHA,
            "price_snapshot_id": "ps-1",
            "price_as_of_utc": "2026-10-26T00:00:00Z",
            "input_inventory_sha256": _FAKE_SHA,
            "scope_hash": _FAKE_SHA,
            "valid_until_utc": "2026-12-31T00:00:00Z",
            "estimates_json": {"p95_compressed_bytes": 1},
            "resource_bindings_json": {"job_definition_revision": "reducer:3"},
        },
    })
    doc["budgets"]["max_retries"] = 0
    doc["budgets"]["safety_factor"] = 1.5
    doc["budgets"]["max_cost_usd"] = 25.0
    doc["budgets"]["max_vcpu_seconds"] = 100.0
    doc["budgets"]["max_memory_mib_seconds"] = 100.0
    return doc


def valid_bootstrap_request() -> dict:
    return {
        "schema_version": "crusher-campaign-distributions/1.0-proposed",
        "request_id": "boot-1",
        "operation": "inventory",
        "source_bucket": "crusherbucket-994254241749-us-east-1-an",
        "source_roots_allowlist": ["campaign/"],
        "derived_exclude_prefixes": ["campaign/_derived/"],
        "scope_register_sha256": _FAKE_SHA,
        "budgets": {
            "max_api_calls_total": 500,
            "max_list_pages": 100,
            "max_head_requests": 1000,
            "max_source_objects": 500000,
            "max_return_bytes": 1048576,
            "max_wall_seconds": 3600,
            "max_cost_usd": 5.0,
        },
        "admission": {
            "admission_id": "adm-boot-1",
            "approved_scope_hash": _FAKE_SHA,
            "approved_cost_usd": 5.0,
            "expires_utc": "2026-12-31T00:00:00Z",
        },
        "price_snapshot": {
            "id": "ps-2026-10-26",
            "as_of_utc": "2026-10-26T00:00:00Z",
            "unit_prices_json": {"s3_list_per_1000": 0.005},
        },
    }


def valid_query() -> dict:
    doc = json.loads(BLOCKED_QUERY.read_text(encoding="utf-8"))
    doc["catalog_snapshot_id"] = "catalog-2026-10-26"
    doc["analysis_version"] = "0" * 40
    doc["weight_set_id"] = "equal_run_weights_v1"
    return doc


def _write(tmp_path: Path, doc: object, name: str = "request.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("fixture", "kind"),
    [
        (BLOCKED_REQUEST, "execution"),
        (BLOCKED_BOOTSTRAP, "bootstrap"),
        (BLOCKED_QUERY, "query"),
    ],
)
def test_shipped_blocked_fixtures_block(
    tmp_path: Path, fixture: Path, kind: str,
) -> None:
    out = tmp_path / "out"
    exit_code, report = _validate(fixture, kind, out)
    assert exit_code != 0
    assert report["status"] == "BLOCKED"
    assert exit_code in (
        contracts.EXIT_ACCESS_OR_RESOURCE_BLOCKED,
        contracts.EXIT_ADMISSION_REQUIRED_OR_EXCEEDED,
    )
    assert report["blocked_reasons"]


def test_query_blocked_example_is_schema_valid_but_semantically_blocked(
    tmp_path: Path,
) -> None:
    exit_code, report = _validate(BLOCKED_QUERY, "query", tmp_path / "out")
    assert report["schema_valid"] is True
    assert report["status"] == "BLOCKED"
    assert exit_code == contracts.EXIT_ACCESS_OR_RESOURCE_BLOCKED
    paths = {reason["path"] for reason in report["blocked_reasons"]}
    assert "catalog_snapshot_id" in paths
    assert "weight_set_id" in paths


@pytest.mark.parametrize(
    ("doc_fn", "kind"),
    [
        (valid_execution_request, "execution"),
        (valid_bootstrap_request, "bootstrap"),
        (valid_query, "query"),
    ],
)
def test_fully_filled_requests_pass(
    tmp_path: Path, doc_fn: object, kind: str,
) -> None:
    path = _write(tmp_path, doc_fn())
    exit_code, report = _validate(path, kind, tmp_path / "out")
    assert report["schema_valid"] is True
    assert report["status"] == "VALID"
    assert exit_code == 0


def test_unset_budget_field_blocks(tmp_path: Path) -> None:
    doc = valid_execution_request()
    doc["budgets"].pop("max_cost_usd")
    exit_code, report = _validate(
        _write(tmp_path, doc), "execution", tmp_path / "out",
    )
    assert exit_code == contracts.EXIT_ADMISSION_REQUIRED_OR_EXCEEDED
    assert any(
        reason["path"] == "budgets.max_cost_usd"
        for reason in report["blocked_reasons"]
    )


def test_null_budget_field_blocks_none_is_never_unlimited(tmp_path: Path) -> None:
    doc = valid_execution_request()
    doc["budgets"]["max_get_requests"] = None
    exit_code, report = _validate(
        _write(tmp_path, doc), "execution", tmp_path / "out",
    )
    assert exit_code == contracts.EXIT_ADMISSION_REQUIRED_OR_EXCEEDED


def test_non_finite_budget_blocks(tmp_path: Path) -> None:
    path = tmp_path / "request.json"
    raw = json.dumps(valid_execution_request()).replace(
        '"max_cost_usd": 25.0', '"max_cost_usd": 1e999',
    )
    path.write_text(raw, encoding="utf-8")
    exit_code, report = _validate(path, "execution", tmp_path / "out")
    assert exit_code == contracts.EXIT_ADMISSION_REQUIRED_OR_EXCEEDED
    assert any(
        reason["reason"] == "budget_not_finite"
        for reason in report["blocked_reasons"]
    )


def test_negative_budget_blocks(tmp_path: Path) -> None:
    doc = valid_execution_request()
    doc["budgets"]["max_wall_seconds"] = -1
    exit_code, report = _validate(
        _write(tmp_path, doc), "execution", tmp_path / "out",
    )
    assert exit_code == contracts.EXIT_ADMISSION_REQUIRED_OR_EXCEEDED


def test_zero_retries_is_admitted(tmp_path: Path) -> None:
    doc = valid_execution_request()
    doc["budgets"]["max_retries"] = 0
    exit_code, report = _validate(
        _write(tmp_path, doc), "execution", tmp_path / "out",
    )
    assert report["status"] == "VALID"
    assert exit_code == 0


def test_missing_required_field_blocks(tmp_path: Path) -> None:
    doc = valid_execution_request()
    doc.pop("approval")
    exit_code, report = _validate(
        _write(tmp_path, doc), "execution", tmp_path / "out",
    )
    assert exit_code != 0
    assert any(
        reason["path"] == "approval"
        for reason in report["blocked_reasons"]
    )


def test_placeholder_resource_blocks(tmp_path: Path) -> None:
    doc = valid_execution_request()
    doc["job_binding"]["queue_arn"] = "<LIVE_QUEUE_ARN_REQUIRED>"
    exit_code, report = _validate(
        _write(tmp_path, doc), "execution", tmp_path / "out",
    )
    assert exit_code == contracts.EXIT_ACCESS_OR_RESOURCE_BLOCKED
    assert any(
        reason["reason"] == "unresolved_placeholder"
        for reason in report["blocked_reasons"]
    )


def test_sha_role_conflation_blocks(tmp_path: Path) -> None:
    doc = valid_execution_request()
    doc["implementation_sha"] = doc["reducer_image_digest"]
    exit_code, report = _validate(
        _write(tmp_path, doc), "execution", tmp_path / "out",
    )
    assert exit_code != 0
    assert any(
        reason["reason"].startswith("sha_roles_conflated")
        for reason in report["blocked_reasons"]
    )


def test_survey_sha_as_implementation_sha_blocks(tmp_path: Path) -> None:
    doc = valid_execution_request()
    doc["implementation_sha"] = doc["survey_source_sha"]
    exit_code, report = _validate(
        _write(tmp_path, doc), "execution", tmp_path / "out",
    )
    assert exit_code != 0
    assert any(
        reason["reason"].startswith("sha_roles_conflated")
        for reason in report["blocked_reasons"]
    )


def test_schema_violation_without_blockage_is_invalid_contract(
    tmp_path: Path,
) -> None:
    doc = valid_execution_request()
    doc["schema_version"] = "wrong-version"
    exit_code, report = _validate(
        _write(tmp_path, doc), "execution", tmp_path / "out",
    )
    assert exit_code == contracts.EXIT_INVALID_CONTRACT
    assert report["schema_valid"] is False
    assert report["blocked_reasons"] == []


def test_non_object_request_is_invalid(tmp_path: Path) -> None:
    path = _write(tmp_path, [1, 2, 3])
    exit_code, report = _validate(path, "execution", tmp_path / "out")
    assert exit_code == contracts.EXIT_INVALID_CONTRACT


def test_missing_request_file_is_invalid(tmp_path: Path) -> None:
    exit_code, _report = _validate(
        tmp_path / "missing.json", "execution", tmp_path / "out",
    )
    assert exit_code == contracts.EXIT_INVALID_CONTRACT


def test_wrong_kind_schema_rejects(tmp_path: Path) -> None:
    # A bootstrap document is not a valid execution request.
    exit_code, report = _validate(
        _write(tmp_path, valid_bootstrap_request()),
        "execution", tmp_path / "out",
    )
    assert exit_code != 0
    assert report["status"] != "VALID"
