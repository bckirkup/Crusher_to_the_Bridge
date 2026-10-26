"""tests/analysis/campaign_reducer/test_plan.py — offline ``analysis plan``.

Closes ticket D0 acceptance: the dated register reconciles against
CANONICAL_INTERFACE counts programmatically (never hardcoded), the blocking
checklist and request template are emitted, and nothing is fabricated as a
current key or run count.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from picard_framework.analysis.campaign_reducer import cli, contracts
from picard_framework.analysis.campaign_reducer.scope import reconcile_scope

CONTRACTS = contracts.CONTRACTS_DIR
BLOCKED_REQUEST = CONTRACTS / "BLOCKED_REQUEST.template.json"


def _run_plan(tmp_path: Path) -> int:
    return cli.main([
        "plan", "--request", str(BLOCKED_REQUEST), "--out", str(tmp_path),
    ])


def test_plan_reconciles_dated_register(tmp_path: Path) -> None:
    assert _run_plan(tmp_path) == 0
    scope = json.loads((tmp_path / "scope.json").read_text(encoding="utf-8"))
    canonical = contracts.load(contracts.CANONICAL_INTERFACE)

    assert scope["status"] == "scope_reconciled"
    assert scope["reconciles"] is True
    assert scope["discrepancies"] == []
    assert scope["record_kind_counts"]["historical_prefix"] == (
        canonical["scope"]["prefix_families"]
    )
    assert scope["record_kind_counts"]["registered_campaign"] == (
        canonical["scope"]["registered_campaigns"]
    )
    assert scope["total_records"] == (
        canonical["scope"]["prefix_families"]
        + canonical["scope"]["registered_campaigns"]
    )
    assert scope["distinct_prefix_names"] == (
        canonical["scope"]["union_prefix_names_at_survey"]
    )


def test_plan_scope_is_dated_not_current(tmp_path: Path) -> None:
    assert _run_plan(tmp_path) == 0
    scope = json.loads((tmp_path / "scope.json").read_text(encoding="utf-8"))
    canonical = contracts.load(contracts.CANONICAL_INTERFACE)

    assert scope["counts_are_dated_not_current"] is True
    assert scope["inventory_as_of"] == canonical["scope"]["inventory_as_of"]
    listing = scope["dated_object_listing"]
    assert listing["as_of"] == canonical["scope"]["inventory_as_of"]
    assert listing["objects_listed"] > 0
    assert listing["bytes_listed"] > 0


def test_plan_emits_request_template_from_schema_required(tmp_path: Path) -> None:
    assert _run_plan(tmp_path) == 0
    template = json.loads((tmp_path / "request_template.json").read_text(encoding="utf-8"))
    schema = contracts.load(contracts.REQUEST_SCHEMA)

    assert set(template) == set(schema["required"])
    assert template["schema_version"] == schema["properties"]["schema_version"]["const"]
    assert template["survey_source_sha"] == (
        schema["properties"]["survey_source_sha"]["const"]
    )
    job_binding = template["job_binding"]
    assert set(job_binding) == set(schema["properties"]["job_binding"]["required"])
    budgets = template["budgets"]
    assert set(budgets) == set(schema["properties"]["budgets"]["required"])
    assert all(value is None for value in budgets.values())


def test_plan_emits_blocking_inputs_checklist(tmp_path: Path) -> None:
    assert _run_plan(tmp_path) == 0
    blocking = json.loads((tmp_path / "blocking_inputs.json").read_text(encoding="utf-8"))
    canonical = contracts.load(contracts.CANONICAL_INTERFACE)

    assert blocking["request_required_fields"] == canonical["request_required_fields"]
    assert blocking["budgets_required"] == canonical["budgets_required"]
    assert len(blocking["budgets_required"]) == 23
    # The blocked template leaves every budget unset — the checklist must say so.
    assert blocking["unset_budget_fields"] == canonical["budgets_required"]
    assert "budgets.max_list_pages" in blocking["null_leaves"]
    assert blocking["external_inputs"]
    assert blocking["dependency_lock"]["python"] == ">=3.11"
    assert "cmdstanpy" in blocking["dependency_lock"]["not_required_on_reduction_path"]


def test_reconcile_scope_flags_tampered_register() -> None:
    canonical = contracts.load(contracts.CANONICAL_INTERFACE)
    records = contracts.load(contracts.CAMPAIGN_COVERAGE)
    report = reconcile_scope(records[:-1], canonical["scope"])
    assert report["reconciles"] is False
    assert report["status"] == "scope_discrepancy"
    metrics = {d["metric"] for d in report["discrepancies"]}
    assert "total_records" in metrics


def test_plan_missing_request_file_is_invalid(tmp_path: Path) -> None:
    exit_code = cli.main([
        "plan", "--request", str(tmp_path / "missing.json"),
        "--out", str(tmp_path / "out"),
    ])
    assert exit_code == contracts.EXIT_INVALID_CONTRACT
