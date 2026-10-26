"""Offline reconciliation of the dated campaign coverage register.

``CAMPAIGN_COVERAGE.json`` is the canonical cold scope: 197 dated historical
prefixes plus 21 registered specs (218 records, 198 distinct prefix names).
``analysis plan`` recomputes every one of those counts from the register and
compares them against the expectations declared in
``CANONICAL_INTERFACE.json`` — nothing here is hardcoded, and any mismatch is
a reportable contract discrepancy, not something to silently patch.
"""
from __future__ import annotations

from collections import Counter
from typing import Any


def reconcile_scope(records: list[dict], scope_spec: dict) -> dict:
    """Recompute the coverage counts and compare with the declared scope.

    ``scope_spec`` is ``CANONICAL_INTERFACE.json["scope"]``. The returned
    report carries the dated (2026-10-19) register metadata as dated —
    never as a current/live inventory or run count.
    """
    kind_counts = Counter(str(record.get("record_kind")) for record in records)
    prefixes = sorted({record.get("prefix") for record in records if record.get("prefix")})
    group_counts = Counter(str(record.get("program_group")) for record in records)

    listed_objects = 0
    listed_bytes = 0
    for record in records:
        metadata = record.get("historical_object_metadata") or {}
        listed_objects += int(metadata.get("objects_listed") or 0)
        listed_bytes += int(metadata.get("bytes_listed") or 0)

    checks = [
        (
            "historical_prefix_records",
            kind_counts.get("historical_prefix", 0),
            scope_spec["prefix_families"],
        ),
        (
            "registered_campaign_records",
            kind_counts.get("registered_campaign", 0),
            scope_spec["registered_campaigns"],
        ),
        (
            "total_records",
            len(records),
            scope_spec["prefix_families"] + scope_spec["registered_campaigns"],
        ),
        (
            "distinct_prefix_names",
            len(prefixes),
            scope_spec["union_prefix_names_at_survey"],
        ),
    ]
    discrepancies = [
        {"metric": name, "actual": actual, "expected": expected}
        for name, actual, expected in checks
        if actual != expected
    ]

    return {
        "status": "scope_discrepancy" if discrepancies else "scope_reconciled",
        "reconciles": not discrepancies,
        "discrepancies": discrepancies,
        "inventory_as_of": scope_spec.get("inventory_as_of"),
        "counts_are_dated_not_current": True,
        "record_kind_counts": dict(sorted(kind_counts.items())),
        "total_records": len(records),
        "distinct_prefix_names": len(prefixes),
        "prefixes": prefixes,
        "program_group_record_counts": dict(sorted(group_counts.items())),
        "expected": {
            "prefix_families": scope_spec["prefix_families"],
            "registered_campaigns": scope_spec["registered_campaigns"],
            "union_prefix_names_at_survey": scope_spec["union_prefix_names_at_survey"],
        },
        "dated_object_listing": {
            "as_of": scope_spec.get("inventory_as_of"),
            "objects_listed": listed_objects,
            "bytes_listed": listed_bytes,
            "note": "Register metadata as of the dated inventory only; "
                    "not a current inventory and not a run/cell count.",
        },
    }


def scope_report(records: list[dict], canonical_scope: dict) -> dict[str, Any]:
    """Full plan-time scope report: reconciliation plus register summary."""
    report = reconcile_scope(records, canonical_scope)
    report["scope_register"] = "contracts/CAMPAIGN_COVERAGE.json"
    report["survey_source_sha"] = canonical_scope_source(records)
    return report


def canonical_scope_source(records: list[dict]) -> str | None:
    """The survey SHA the register records were written against."""
    shas = {record.get("survey_source_sha") for record in records}
    shas.discard(None)
    return sorted(shas)[0] if len(shas) == 1 else None
