"""``analysis quote`` — offline phase quote from measured evidence (D6).

Reads the request being priced (``--request``, bootstrap- or
execution-shaped — quoted *for*, so missing fields become typed blocking
inputs rather than a schema rejection) and a measured-evidence document
(``--evidence``): a pilot receipt (``kind: pilot_receipt``) carrying
per-class measured costs with specimen pins, or a bootstrap estimate
(``kind: bootstrap_estimate``) carrying declared unit costs.

Emits under ``--out``:

- ``phase_quote.json`` — per-phase cost rows (bytes/requests/time/
  memory/spool/retries) priced in USD only where the request's
  ``price_snapshot`` declares a timestamped unit price;
- ``uncertainty.json`` — explicit bands per estimate, with cold-count
  extrapolation labeled dated;
- ``blocking_inputs.json`` — absent price/resource/measurement entries
  (a typed stop, never a guessed number);
- ``status.json``.

Zero network, zero clock dependence: every emitted number derives from
the two input documents so the quote is reproducible and pinnable.
"""
from __future__ import annotations

import json
import os
from typing import Any

from .._io import write_json
from . import contracts
from .identity import sha256_hex
from .return_path import _load_json_path, _out_root

OPTIONAL_FLAGS: tuple[str, ...] = ()

_STATUS_NAME = "status.json"
_QUOTE_SCHEMA = "crusher-reducer-phase-quote/v1"
_UNCERTAINTY_SCHEMA = "crusher-reducer-quote-uncertainty/v1"
_BLOCKING_SCHEMA = "crusher-reducer-blocking-inputs/v1"
_EVIDENCE_KINDS = {"pilot_receipt", "bootstrap_estimate"}

# Unit-price keys the cost model consumes from
# request.price_snapshot.unit_prices_json. An absent key is a typed
# blocking input; the affected cost component stays null — never a guess.
_PRICE_FOR = {
    "s3_list": "s3_list_per_1000_requests_usd",
    "s3_head": "s3_head_per_1000_requests_usd",
    "s3_get": "s3_get_per_1000_requests_usd",
    "s3_put": "s3_put_per_1000_requests_usd",
    "vcpu_hour": "batch_vcpu_hour_usd",
    "memory_gib_hour": "batch_memory_gib_hour_usd",
    "storage_gb_month": "s3_storage_gb_month_usd",
    "transfer_out_gb": "s3_data_transfer_out_gb_usd",
}

_PHASES = ("materialize", "finalize", "query", "return")

# Phase multiplier profiles: how each phase's resource draw scales with
# the per-family measured/declared units, as a declared shape (the pilot
# measures it; the bootstrap estimate declares it). Fractions of the
# materialize-phase measured draw.
_PHASE_SHAPE = {
    "materialize": {"api": 1.0, "bytes": 1.0, "time": 1.0,
                    "memory": 1.0, "spool": 1.0, "output": 1.0},
    "finalize": {"api": 0.10, "bytes": 0.10, "time": 0.10,
                 "memory": 0.25, "spool": 0.10, "output": 0.10},
    "query": {"api": 0.20, "bytes": 0.20, "time": 0.20,
              "memory": 0.20, "spool": 0.0, "output": 0.20},
    "return": {"api": 0.05, "bytes": 0.05, "time": 0.05,
               "memory": 0.05, "spool": 0.0, "output": 0.05},
}


def _emit(out_root: str, name: str, doc: Any) -> None:
    write_json(os.path.join(out_root, name), doc)


def _status_doc(status: str, **extra) -> dict:
    doc = {"status": status, "operation": "quote"}
    doc.update(extra)
    return doc


def _evidence_classes(evidence: dict) -> dict[str, dict]:
    """Per-family unit draws from the evidence: measured classes (pilot
    receipt) or declared estimates (bootstrap), keyed by schema family."""
    per_family: dict[str, dict] = {}
    for row in evidence.get("per_class") or []:
        fam = row.get("family") or row.get("schema_family")
        if not fam:
            continue
        cur = per_family.setdefault(fam, {
            "objects": 0.0, "compressed_bytes": 0.0,
            "uncompressed_bytes": 0.0, "member_bytes": 0.0,
            "api_list": 0.0, "api_head": 0.0, "api_get": 0.0,
            "api_put": 0.0, "wall_seconds": 0.0, "vcpu_seconds": 0.0,
            "memory_mib_seconds": 0.0, "peak_memory_mib": 0.0,
            "spool_bytes": 0.0, "output_bytes": 0.0, "retries": 0.0,
        })
        for field in cur:
            val = row.get(field)
            if isinstance(val, (int, float)):
                cur[field] += float(val)
    return per_family


def _scope_families(evidence: dict) -> tuple[list[dict], list[dict]]:
    """Scope counts the quote extrapolates over, with datedness kept."""
    scope = evidence.get("scope") or {}
    rows = []
    blocking = []
    for fam in scope.get("families") or []:
        rows.append({
            "family": fam.get("family") or fam.get("schema_family"),
            "objects": float(fam.get("objects") or 0),
            "bytes": float(fam.get("bytes") or 0),
            "counts_basis": fam.get("counts_basis")
            or scope.get("counts_basis") or "unspecified",
            "as_of": fam.get("as_of") or scope.get("as_of"),
        })
    if not rows:
        blocking.append({
            "kind": "resource_absent",
            "input": "evidence.scope.families",
            "needed_for": "phase_quote extrapolation",
            "detail": "evidence carries no scope counts to extrapolate "
                      "over — stop, do not guess coverage",
        })
    return rows, blocking


def _phase_row(phase: str, basis: str, units: dict) -> dict:
    shape = _PHASE_SHAPE[phase]
    return {
        "phase": phase,
        "basis": basis,
        "objects": units["objects"] * shape["bytes"],
        "compressed_bytes_read": units["compressed_bytes"]
        * shape["bytes"],
        "uncompressed_bytes": units["uncompressed_bytes"] * shape["bytes"],
        "member_bytes": units["member_bytes"] * shape["bytes"],
        "api_calls": {
            "list": units["api_list"] * shape["api"],
            "head": units["api_head"] * shape["api"],
            "get": units["api_get"] * shape["api"],
            "put": units["api_put"] * shape["api"],
        },
        "wall_seconds": units["wall_seconds"] * shape["time"],
        "vcpu_seconds": units["vcpu_seconds"] * shape["time"],
        "memory_mib_seconds": units["memory_mib_seconds"] * shape["memory"],
        "peak_memory_mib": units["peak_memory_mib"],
        "spool_bytes": units["spool_bytes"] * shape["spool"],
        "output_bytes": units["output_bytes"] * shape["output"],
        "retries": units["retries"],
    }


def _scale_units(
    scope_rows: list[dict], per_family: dict[str, dict],
) -> tuple[dict, list[dict], list[dict]]:
    """Extrapolate measured/declared units over the scope.

    Returns (total units, unmeasured family rows, uncertainty rows).
    An unmeasured family is never folded into the totals as a known
    cost — it lands as a typed uncertainty row instead (no inferred
    all-family compatibility from measured classes).
    """
    totals = dict.fromkeys((
        "objects", "compressed_bytes", "uncompressed_bytes",
        "member_bytes", "api_list", "api_head", "api_get", "api_put",
        "wall_seconds", "vcpu_seconds", "memory_mib_seconds",
        "peak_memory_mib", "spool_bytes", "output_bytes", "retries",
    ), 0.0)
    unmeasured: list[dict] = []
    bands: list[dict] = []
    for row in scope_rows:
        fam = row["family"]
        units = per_family.get(fam)
        dated = row["counts_basis"] != "fresh_inventory"
        if units is None or not units["objects"]:
            unmeasured.append(row)
            bands.append({
                "field": f"{fam}",
                "basis": "unmeasured_family",
                "low": None, "central": None, "high": None,
                "counts_basis": row["counts_basis"],
                "as_of": row["as_of"],
                "counts_are_dated_not_current": dated,
                "note": "family not covered by measured classes — no "
                        "compatibility inferred",
            })
            continue
        factor = row["objects"] / units["objects"]
        for field in totals:
            totals[field] += units[field] * factor
        bands.append({
            "field": fam,
            "basis": "measured" if not dated else "measured_dated_counts",
            "low": units["wall_seconds"] * factor * 0.5,
            "central": units["wall_seconds"] * factor,
            "high": units["wall_seconds"] * factor * 2.0,
            "counts_basis": row["counts_basis"],
            "as_of": row["as_of"],
            "counts_are_dated_not_current": dated,
            "note": ("extrapolated over dated register counts — "
                     "fresh listing may differ" if dated else
                     "extrapolated over fresh inventory counts"),
        })
    return totals, unmeasured, bands


def _cost_breakdown(
    row: dict, prices: dict,
) -> tuple[dict, list[str]]:
    """USD per component when the price snapshot declares the unit."""
    api = row["api_calls"]
    components = {
        "s3_list": api["list"] / 1000.0,
        "s3_head": api["head"] / 1000.0,
        "s3_get": api["get"] / 1000.0,
        "s3_put": api["put"] / 1000.0,
        "vcpu_hour": row["vcpu_seconds"] / 3600.0,
        "memory_gib_hour": row["memory_mib_seconds"] / 1024.0 / 3600.0,
        "storage_gb_month": row["output_bytes"] / (1024.0 ** 3),
        "transfer_out_gb": row["output_bytes"] / (1024.0 ** 3),
    }
    detail: dict[str, Any] = {}
    missing: list[str] = []
    for comp, qty in components.items():
        price_key = _PRICE_FOR[comp]
        unit = prices.get(price_key)
        if unit is None:
            detail[comp] = {"quantity": qty, "unit_price": None,
                            "usd": None, "price_key": price_key}
            missing.append(price_key)
        else:
            detail[comp] = {"quantity": qty, "unit_price": float(unit),
                            "usd": qty * float(unit),
                            "price_key": price_key}
    total = sum(c["usd"] for c in detail.values() if c["usd"] is not None)
    return {"components": detail, "total_usd": total,
            "fully_priced": not missing}, missing


def _prices_of(
    request: dict, evidence: dict,
) -> tuple[dict, dict | None, dict | None]:
    """The declared unit-price snapshot.

    Looked up on the request first (bootstrap requests carry
    ``price_snapshot``), then the evidence (an execution envelope
    cannot — schema-forbidden extra fields — so the pilot receipt or
    bootstrap estimate carries the timestamped snapshot instead), then
    the request's admitted quote block.
    """
    candidates = (
        (request.get("price_snapshot"), "request.price_snapshot"),
        (evidence.get("price_snapshot"), "evidence.price_snapshot"),
        (request.get("quote"), "request.quote"),
    )
    for carrier, owner in candidates:
        if not isinstance(carrier, dict):
            continue
        prices = carrier.get("unit_prices_json")
        if not isinstance(prices, dict):
            prices = carrier.get("unit_prices")
        if isinstance(prices, dict):
            return prices, {
                "id": carrier.get("id") or carrier.get(
                    "price_snapshot_id"),
                "as_of_utc": carrier.get("as_of_utc")
                or carrier.get("price_as_of_utc"),
                "owner": owner,
            }, None
    return {}, None, {
        "kind": "price_absent",
        "input": "price_snapshot.unit_prices_json",
        "needed_for": "phase_quote cost_usd",
        "detail": "no timestamped unit-price snapshot on the request "
                  "or the evidence — stop, do not guess prices",
    }


def run(args) -> int:
    """Entry for ``analysis quote``."""
    out_root = _out_root(args.out, "quote")
    if out_root is None:
        return contracts.EXIT_INVALID_CONTRACT
    try:
        request = _load_json_path(args.request)
        evidence = _load_json_path(getattr(args, "evidence", "") or "")
    except Exception as exc:  # confined-path or JSON failure -> invalid
        doc = _status_doc("invalid_contract", error={
            "kind": "unreadable_input", "detail": str(exc),
        })
        _emit(out_root, _STATUS_NAME, doc)
        print(json.dumps(doc))
        return contracts.EXIT_INVALID_CONTRACT
    if not isinstance(request, dict) or not isinstance(evidence, dict):
        doc = _status_doc("invalid_contract", error={
            "kind": "malformed_input",
            "detail": "request and evidence must be JSON objects",
        })
        _emit(out_root, _STATUS_NAME, doc)
        print(json.dumps(doc))
        return contracts.EXIT_INVALID_CONTRACT
    kind = evidence.get("kind")
    if kind not in _EVIDENCE_KINDS:
        doc = _status_doc("invalid_contract", error={
            "kind": "unknown_evidence_kind",
            "detail": f"evidence.kind must be one of "
                      f"{sorted(_EVIDENCE_KINDS)}, got {kind!r}",
        })
        _emit(out_root, _STATUS_NAME, doc)
        print(json.dumps(doc))
        return contracts.EXIT_INVALID_CONTRACT
    return _quote(request, evidence, kind, out_root)


def _price_gap_blocks(phase: str, missing) -> list[dict]:
    return [
        {
            "kind": "price_absent",
            "input": f"price_snapshot.unit_prices_json.{key}",
            "needed_for": f"phase_quote.{phase}.cost",
            "detail": "unit price not declared — stop, never guess",
        }
        for key in missing
    ]


def _quote_document(
    request, kind, price_snap, evidence, phase_rows, unmeasured, safety, totals,
) -> tuple[dict, str]:
    """The phase-quote document and its content-addressed id."""
    quote_body = {
        "request_id": request.get("request_id") or request.get("reduction_id"),
        "evidence_kind": kind,
        "price_snapshot": price_snap,
        "input_inventory_sha256": (
            (request.get("inventory_snapshot") or {}).get("sha256")
            or evidence.get("inventory_sha256")
        ),
        "scope_hash": (request.get("approval") or {}).get("scope_hash"),
        "phase_rows": phase_rows,
        "unmeasured_families": unmeasured,
        "safety_factor": safety,
        "reserves": {
            k: totals[k] * (safety - 1.0) for k in totals
        } if safety > 1.0 else dict.fromkeys(totals, 0.0),
        "valid_until_utc": (request.get("approval") or {}).get(
            "expires_utc"),
    }
    quote_id = "quote-" + sha256_hex(
        json.dumps(quote_body, sort_keys=True).encode()
    )[:16]
    quote_doc = {
        "schema": _QUOTE_SCHEMA,
        "quote_id": quote_id,
        **quote_body,
    }
    max_cost = float(
        (request.get("budgets") or {}).get("max_cost_usd") or 0.0
    )
    grand = sum(
        r["cost"]["total_usd"] for r in phase_rows
        if r["cost"]["total_usd"] is not None
    ) * safety
    quote_doc["totals"] = {
        "central_usd": grand,
        "exceeds_declared_envelope": bool(max_cost) and grand > max_cost,
    }
    return quote_doc, quote_id


def _quote_exit(blocking, unmeasured) -> tuple[str, int]:
    if blocking:
        return "blocked", contracts.EXIT_ACCESS_OR_RESOURCE_BLOCKED
    if unmeasured:
        return "partial", contracts.EXIT_PARTIAL_COVERAGE
    return "complete", contracts.EXIT_COMPLETE


def _quote(request: dict, evidence: dict, kind: str, out_root: str) -> int:
    blocking: list[dict] = []
    prices, price_snap, price_block = _prices_of(request, evidence)
    if price_block:
        blocking.append(price_block)
    scope_rows, scope_blocking = _scope_families(evidence)
    blocking += scope_blocking
    basis = "measured" if kind == "pilot_receipt" else "bootstrap_estimate"
    per_family = _evidence_classes(evidence)
    totals, unmeasured, bands = _scale_units(scope_rows, per_family)
    safety = float(
        (request.get("budgets") or {}).get("safety_factor") or 1.0
    )
    phase_rows = []
    for phase in _PHASES:
        row = _phase_row(phase, basis, totals)
        cost, missing = _cost_breakdown(row, prices)
        row["cost"] = cost
        blocking.extend(_price_gap_blocks(phase, missing))
        phase_rows.append(row)
    quote_doc, quote_id = _quote_document(
        request, kind, price_snap, evidence, phase_rows,
        unmeasured, safety, totals,
    )
    _emit(out_root, "phase_quote.json", quote_doc)
    _emit(out_root, "uncertainty.json", {
        "schema": _UNCERTAINTY_SCHEMA,
        "quote_id": quote_id,
        "bands": bands,
    })
    _emit(out_root, "blocking_inputs.json", {
        "schema": _BLOCKING_SCHEMA,
        "quote_id": quote_id,
        "blocking": blocking,
    })
    status, rc = _quote_exit(blocking, unmeasured)
    doc = _status_doc(
        status, quote_id=quote_id,
        blocking_count=len(blocking),
        unmeasured_families=len(unmeasured),
    )
    _emit(out_root, _STATUS_NAME, doc)
    print(json.dumps(doc))
    return rc
