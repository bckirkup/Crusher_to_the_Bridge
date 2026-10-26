"""``analysis plan`` — deterministic offline scope/blocking-input report.

Writes three artifacts into ``--out DIR``:

- ``scope.json`` — reconciliation of the dated coverage register against the
  counts declared in ``CANONICAL_INTERFACE.json``.
- ``blocking_inputs.json`` — the resource/access/dependency checklist of
  what is still missing before any admitted (paid) operation.
- ``request_template.json`` — a null-valued request skeleton seeded from
  ``REQUEST.schema.json``'s required fields (``const`` leaves filled).

``plan`` performs zero network, cloud or simulation calls.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from simulation_utils.paths import validated_open

from .._io import allowed_roots, ensure_out_dir, write_json
from . import contracts
from .scope import scope_report

_BLOCKING_EXTERNAL_INPUTS = [
    "live queue/job-definition-revision/job-role/execution-role ARNs "
    "(job_binding.*) — resolved at deployment stage D3, never fabricated",
    "digest-pinned verified reducer image "
    "(reducer_image_digest + job_binding.image_digest)",
    "frozen inventory snapshot (inventory_snapshot.id/sha256) "
    "from an admitted D5 inventory",
    "approved admission (approval.*) binding scope_hash/quote_id/expiry",
    "pinned quote (quote.*) with timestamped verified regional prices and "
    "measured pilot evidence (D6); cold-register counts extrapolate as dated",
    "worker identity fields: implementation_sha (the SHA this code runs at), "
    "adapter_registry_sha256, scope_register_sha256",
    "source_prefix_allowlist + derived_root "
    "(campaign/_derived/reducer/v1/ is write-only-to-self; sources immutable)",
]

_DEPENDENCY_LOCK = {
    "python": ">=3.11",
    "locked": ["boto3>=1.34", "pyarrow>=14.0", "jsonschema>=4.17"],
    "not_required_on_reduction_path": ["cmdstanpy", "CmdStan"],
}


def seed_request_template(schema: dict) -> dict:
    """Null-valued request skeleton from a schema's required fields."""
    return {name: _seed(schema["properties"][name]) for name in schema["required"]}


def _seed(node: dict) -> Any:
    if "const" in node:
        return node["const"]
    if node.get("type") == "object":
        properties = node.get("properties", {})
        return {
            name: _seed(properties[name])
            for name in node.get("required", [])
            if name in properties
        }
    return None


def _null_paths(doc: Any, prefix: str = "") -> list[str]:
    """Dotted paths of every ``None`` leaf in a request document."""
    paths: list[str] = []
    if isinstance(doc, dict):
        for key, value in doc.items():
            path = f"{prefix}{key}"
            if value is None:
                paths.append(path)
            elif isinstance(value, dict):
                paths.extend(_null_paths(value, f"{path}."))
    return paths


def build_blocking_inputs(canonical: dict, provided: dict | None) -> dict:
    """Checklist of unset required fields plus external blocking inputs."""
    request_schema = contracts.load(contracts.REQUEST_SCHEMA)
    template = seed_request_template(request_schema)
    doc = template if provided is None else provided
    unset_required = [
        field for field in canonical["request_required_fields"] if doc.get(field) is None
    ]
    budgets = doc.get("budgets") or {}
    unset_budgets = [
        field for field in canonical["budgets_required"] if budgets.get(field) is None
    ]
    return {
        "status": "BLOCKED_ON_INPUTS",
        "request_kind": "execution",
        "request_schema": "contracts/REQUEST.schema.json",
        "request_required_fields": canonical["request_required_fields"],
        "unset_required_fields": unset_required,
        "budgets_required": canonical["budgets_required"],
        "unset_budget_fields": unset_budgets,
        "null_leaves": _null_paths(doc),
        "external_inputs": list(_BLOCKING_EXTERNAL_INPUTS),
        "dependency_lock": dict(_DEPENDENCY_LOCK),
        "source_provided": provided is not None,
        "note": "None is never unlimited; every budgets_required field must "
                "be explicit and finite before admission.",
    }


def _load_optional_request(path: Path | None) -> dict | None:
    if path is None:
        return None
    try:
        with validated_open(
            str(path), allowed_roots=allowed_roots(), encoding="utf-8",
        ) as fh:
            doc = json.load(fh)
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return doc if isinstance(doc, dict) else None


def run_plan(request_path: Path | None, out_dir: Path) -> int:
    """Emit the offline plan artifacts; nonzero on scope discrepancy."""
    canonical = contracts.load(contracts.CANONICAL_INTERFACE)
    records = contracts.load(contracts.CAMPAIGN_COVERAGE)
    report = scope_report(records, canonical["scope"])
    template = seed_request_template(contracts.load(contracts.REQUEST_SCHEMA))
    blocking = build_blocking_inputs(canonical, _load_optional_request(request_path))

    try:
        out_root = ensure_out_dir(str(out_dir))
    except SystemExit as exc:
        print(json.dumps({
            "status": "INVALID_CONTRACT",
            "operation": "plan",
            "error": str(exc),
        }))
        return contracts.EXIT_INVALID_CONTRACT
    write_json(os.path.join(out_root, "scope.json"), report)
    write_json(os.path.join(out_root, "blocking_inputs.json"), blocking)
    write_json(os.path.join(out_root, "request_template.json"), template)

    print(json.dumps({
        "status": report["status"],
        "operation": "plan",
        "total_records": report["total_records"],
        "distinct_prefix_names": report["distinct_prefix_names"],
        "reconciles": report["reconciles"],
        "discrepancies": report["discrepancies"],
        "out": str(out_dir),
    }))
    return contracts.EXIT_COMPLETE if report["reconciles"] else contracts.EXIT_INVALID_CONTRACT
