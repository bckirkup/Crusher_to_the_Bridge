"""``analysis validate`` — offline schema + semantic request validation.

``--request-kind`` selects the frozen contract schema the ``--request``
document is checked against: ``execution`` (REQUEST.schema.json),
``bootstrap`` (BOOTSTRAP_REQUEST.schema.json) or ``query``
(QUERY.schema.json — the document is a bounded query file).

Schema validation alone never admits a request. The semantic gate re-checks
that every required and ``budgets_required`` field is present, explicit and
finite — ``None`` is never unlimited — and that no resource, price or
admission value is an unresolved ``<PLACEHOLDER>``. Outcomes:

- ``VALID`` → exit 0
- ``BLOCKED`` (unset/non-finite budget, missing required field, unknown
  resource/price/admission) → exit 4 when admission-related, else 3
- ``INVALID_CONTRACT`` (unparseable, non-object, or schema violation with
  no semantic blockage) → exit 2

Zero network, cloud or simulation calls.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Iterator

import jsonschema

from . import contracts

_PLACEHOLDER = re.compile(r"^\s*<[^<>]+>\s*$")

# Root fields whose unset/unknown values block on admission (exit 4); every
# other root blocks as an unknown resource (exit 3). Both are the
# "blocked" lifecycle alias in STATUS_NAMESPACES.json.
_ADMISSION_ROOTS = {
    "budgets", "approval", "quote", "admission", "price_snapshot",
    "readback", "scan_budget",
}


def _category(path: str) -> str:
    root = path.split(".", 1)[0].split("[", 1)[0]
    return "admission" if root in _ADMISSION_ROOTS else "resource"


def _reason(path: str, reason: str) -> dict:
    return {"path": path, "reason": reason, "category": _category(path)}


def _allows_null(property_schema: dict) -> bool:
    prop_type = property_schema.get("type")
    return isinstance(prop_type, list) and "null" in prop_type


def _required_reasons(doc: dict, kind: str, schema: dict, canonical: dict) -> list[dict]:
    fields = set(schema.get("required", []))
    if kind == "execution":
        fields |= set(canonical["request_required_fields"])
    properties = schema.get("properties", {})
    reasons = []
    for field in sorted(fields):
        if field not in doc:
            reasons.append(_reason(field, "required_field_missing"))
        elif doc[field] is None and not _allows_null(properties.get(field, {})):
            reasons.append(_reason(field, "required_field_null"))
    return reasons


def _budget_specs(kind: str, schema: dict, canonical: dict) -> tuple[str, list[str]]:
    if kind == "execution":
        return "budgets", list(canonical["budgets_required"])
    properties = schema.get("properties", {})
    if kind == "query":
        return "scan_budget", list(properties.get("scan_budget", {}).get("required", []))
    return "budgets", list(properties.get("budgets", {}).get("required", []))


def _budget_reasons(doc: dict, kind: str, schema: dict, canonical: dict) -> list[dict]:
    parent, fields = _budget_specs(kind, schema, canonical)
    budgets = doc.get(parent)
    if not isinstance(budgets, dict):
        budgets = {}
    reasons = []
    for field in fields:
        path = f"{parent}.{field}"
        value = budgets.get(field)
        if value is None:
            reasons.append(_reason(path, "budget_unset_or_null"))
        elif isinstance(value, bool) or not isinstance(value, (int, float)):
            reasons.append(_reason(path, "budget_not_numeric"))
        elif not math.isfinite(value):
            reasons.append(_reason(path, "budget_not_finite"))
        elif (field == "max_retries" and value < 0) or (
            field != "max_retries" and value <= 0
        ):
            reasons.append(_reason(path, "budget_not_positive"))
    return reasons


def _walk_strings(doc: Any, path: str = "") -> Iterator[tuple[str, str]]:
    if isinstance(doc, dict):
        for key, value in doc.items():
            child = f"{path}.{key}" if path else str(key)
            yield from _walk_strings(value, child)
    elif isinstance(doc, list):
        for index, value in enumerate(doc):
            yield from _walk_strings(value, f"{path}[{index}]")
    elif isinstance(doc, str):
        yield path, doc


def _placeholder_reasons(doc: dict) -> list[dict]:
    return [
        _reason(path, "unresolved_placeholder")
        for path, value in _walk_strings(doc)
        if _PLACEHOLDER.match(value)
    ]


# SHA/digest roles are distinct identities: the engine/implementation SHA is
# never filled from the survey SHA or the reducer image digest.
_DISTINCT_SHA_PAIRS = (
    ("implementation_sha", "reducer_image_digest"),
    ("implementation_sha", "survey_source_sha"),
)


def _distinct_sha_reasons(doc: dict, kind: str) -> list[dict]:
    if kind != "execution":
        return []
    reasons = []
    for first, second in _DISTINCT_SHA_PAIRS:
        first_value = doc.get(first)
        second_value = doc.get(second)
        if (
            isinstance(first_value, str)
            and isinstance(second_value, str)
            and first_value == second_value
        ):
            reasons.append(_reason(first, f"sha_roles_conflated_with_{second}"))
    return reasons


def _semantic_reasons(doc: dict, kind: str, schema: dict, canonical: dict) -> list[dict]:
    reasons = _required_reasons(doc, kind, schema, canonical)
    reasons += _budget_reasons(doc, kind, schema, canonical)
    reasons += _placeholder_reasons(doc)
    reasons += _distinct_sha_reasons(doc, kind)
    return reasons


def _load_request(path: Path, errors: list[str]) -> dict | None:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path}: unreadable or invalid JSON — {exc}")
        return None
    if not isinstance(doc, dict):
        errors.append(f"{path}: request document is not a JSON object")
        return None
    return doc


def _schema_errors(doc: dict, schema: dict) -> list[str]:
    validator = jsonschema.Draft202012Validator(schema)
    return sorted(
        f"{'.'.join(str(part) for part in error.absolute_path) or '<root>'}: "
        f"{error.message}"
        for error in validator.iter_errors(doc)
    )


def run_validate(request_path: Path, kind: str, out_dir: Path) -> int:
    """Validate one request document; write ``validation.json`` to --out."""
    schema_name = contracts.REQUEST_KIND_SCHEMAS[kind]
    schema = contracts.load(schema_name)
    canonical = contracts.load(contracts.CANONICAL_INTERFACE)

    schema_errors: list[str] = []
    reasons: list[dict] = []
    doc = _load_request(request_path, schema_errors)
    if doc is not None:
        schema_errors.extend(_schema_errors(doc, schema))
        reasons = _semantic_reasons(doc, kind, schema, canonical)

    if reasons:
        exit_code = (
            contracts.EXIT_ADMISSION_REQUIRED_OR_EXCEEDED
            if any(reason["category"] == "admission" for reason in reasons)
            else contracts.EXIT_ACCESS_OR_RESOURCE_BLOCKED
        )
        status = "BLOCKED"
    elif schema_errors:
        exit_code = contracts.EXIT_INVALID_CONTRACT
        status = "INVALID_CONTRACT"
    else:
        exit_code = contracts.EXIT_COMPLETE
        status = "VALID"

    result = {
        "status": status,
        "operation": "validate",
        "request_kind": kind,
        "request_file": str(request_path),
        "schema": f"contracts/{schema_name}",
        "schema_valid": not schema_errors,
        "schema_errors": schema_errors,
        "blocked_reasons": reasons,
        "exit_code": exit_code,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "validation.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps(result))
    return exit_code
