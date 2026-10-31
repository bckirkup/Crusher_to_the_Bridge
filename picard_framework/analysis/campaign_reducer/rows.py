"""TABLE_ROWS emitters: adapter payloads -> contract-shaped row dicts.

D2 materialization turns each ``AdapterResult`` into rows for the
operational tables (``source_objects``, ``source_links``, ``assets``,
``runs``, ``run_scalars``, ``capabilities``, ``data_gaps``) and — through
``long_tables`` — the optional scientific long tables. Field names and
enum literals follow ``TABLE_ROWS.schema.json`` exactly; anything the
adapter did not observe stays ``None``, never a fabricated default.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .adapters import SourceRef
from .identity import case_id as _case_id
from .identity import object_id
from .payloads import AdapterResult
from .pinned_reader import parse_s3_uri

TABLE_VERSION = "1.0.0"


def canonical_json(doc: Any) -> str:
    """Deterministic serialization: sorted keys, tight separators."""
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), default=str)


def row_id(table: str, *parts: object) -> str:
    """Stable row id derived from the row's identifying tuple."""
    digest = hashlib.sha256(canonical_json([table, *parts]).encode()).hexdigest()
    return f"{table[:3]}-{digest[:16]}"


@dataclass(frozen=True)
class ReductionContext:
    """Reduction-level identity stamped onto every emitted row."""

    reduction_id: str
    snapshot_id: str
    request_sha256: str = ""
    inventory_sha256: str | None = None
    implementation_sha: str = ""
    adapter_registry_sha256: str = ""
    image_digest: str = ""
    phase: str = "materialize"
    admission_id: str | None = None
    parent_reduction_id: str | None = None
    discovery_root: str = ""
    listing_start_utc: str = ""
    listing_end_utc: str = ""
    fingerprint: str = ""


@dataclass(frozen=True)
class SourceSpec:
    """One inventory entry the materializer consumes.

    ``declared_runs`` is what the inventory said this source should
    contain; ``attempt_*`` carries attempt-aware selection metadata so
    canary/production/rerun conflicts stay visible.
    """

    uri: str
    family: str
    source_id: str
    campaign_id: str
    seed: int | None = None
    original_run_id: str | None = None
    hull_id: str | None = None
    cell_id: str | None = None
    engine_sha: str | None = None
    image_digest: str | None = None
    attempt_id: str | None = None
    stage_id: str | None = None
    attempt_kind: str = "unknown"
    scope_id: str | None = None
    scope_delta: str = "in_scope"
    declared_runs: int | None = None
    member_allowlist: tuple[str, ...] | None = None
    emit_scalars: bool = True
    source_role: str | None = None

    def to_ref(self) -> SourceRef:
        return SourceRef(
            source_id=self.source_id,
            uri=self.uri,
            campaign_id=self.campaign_id,
            seed=self.seed,
            original_run_id=self.original_run_id,
            hull_id=self.hull_id,
            cell_id=self.cell_id,
            engine_sha=self.engine_sha,
            image_digest=self.image_digest,
            member_allowlist=self.member_allowlist,
            emit_scalars=self.emit_scalars,
        )


def _bucket_key(uri: str) -> tuple[str, str]:
    try:
        return parse_s3_uri(uri)
    except ValueError:
        base = uri.split("#", 1)[0]
        return "", base


_GAP_RECOVERABILITY: dict[str, str] = {
    "not_saved": "irrecoverable_existing",
    "dropped_by_profile": "irrecoverable_existing",
    "member_missing": "read_existing",
    "not_applicable": "not_applicable",
    "unknown_schema": "irrecoverable_existing",
    "malformed": "irrecoverable_existing",
    "unreachable": "read_existing",
    "not_requested": "not_applicable",
    "identity_unresolved": "reconcile_identity",
    "incompatible_definition": "irrecoverable_existing",
    "denominator_zero": "not_applicable",
    "no_events": "not_applicable",
    "not_observed": "irrecoverable_existing",
    "not_identifiable": "irrecoverable_existing",
    "rounded_only": "irrecoverable_existing",
    "time_origin_unknown": "derive_existing",
    "partial_followup": "irrecoverable_existing",
    "unsupported_join": "not_applicable",
}


def emit_source_rows(
    result: AdapterResult,
    spec: SourceSpec,
    ctx: ReductionContext,
    suppress: frozenset[str] = frozenset(),
) -> dict[str, list[dict]]:
    """Emit contract rows for one source's adapter output.

    ``suppress`` names base tables the profile drops before rows are
    built — ``run_scalars`` suppression skips the per-leaf row
    materialization entirely (the cost driver measured in D6).
    """
    out: dict[str, list[dict]] = {
        t: []
        for t in (
            "source_objects",
            "source_links",
            "assets",
            "runs",
            "run_scalars",
            "capabilities",
            "data_gaps",
        )
    }
    obj_rows = _source_object_rows(result, spec, ctx)
    out["source_objects"] = obj_rows
    asset_rows = _asset_rows(result, spec, ctx, obj_rows)
    out["assets"] = asset_rows
    out["runs"] = _run_rows(result, spec, ctx)
    if "run_scalars" not in suppress:
        out["run_scalars"] = _scalar_rows(result, ctx)
    out["capabilities"] = _capability_rows(result, spec, ctx)
    out["data_gaps"] = _gap_rows(result, spec, ctx)
    out["source_links"] = _link_rows(obj_rows, asset_rows, result, ctx)
    return out


def _source_object_rows(
    result: AdapterResult, spec: SourceSpec, ctx: ReductionContext
) -> list[dict]:
    rows = []
    seen: dict[str, dict] = {}
    for link in result.links:
        bucket, key = _bucket_key(link.uri)
        oid = object_id(
            spec.campaign_id, link.uri, link.version_id, link.etag
        )
        row = {
            "row_id": row_id("so", oid, link.read_state),
            "reduction_id": ctx.reduction_id,
            "snapshot_id": ctx.snapshot_id,
            "object_id": oid,
            "bucket": bucket,
            "key": key,
            "prefix_family": spec.family,
            "version_id": link.version_id,
            "etag": link.etag,
            "pin_kind": link.pin_kind,
            "bytes_stored": link.content_length,
            "last_modified_utc": link.last_modified,
            "storage_class": link.storage_class,
            "listing_start_utc": ctx.listing_start_utc,
            "listing_end_utc": ctx.listing_end_utc,
            "discovery_root": ctx.discovery_root,
            "identity_evidence_json": {
                "pin_kind": link.pin_kind,
                "version_id": link.version_id,
                "etag": link.etag,
                "sha256": link.sha256,
                "detail": link.detail,
            },
            "read_state": link.read_state,
            "scope_delta": spec.scope_delta,
        }
        seen[oid] = row  # last link wins: final read state
    rows.extend(seen.values())
    if not rows:
        bucket, key = _bucket_key(spec.uri)
        oid = object_id(spec.campaign_id, spec.uri, None, None)
        rows.append(
            {
                "row_id": row_id("so", oid, "unread"),
                "reduction_id": ctx.reduction_id,
                "snapshot_id": ctx.snapshot_id,
                "object_id": oid,
                "bucket": bucket,
                "key": key,
                "prefix_family": spec.family,
                "version_id": None,
                "etag": None,
                "pin_kind": "unpinned_blocked",
                "bytes_stored": None,
                "last_modified_utc": None,
                "storage_class": None,
                "listing_start_utc": ctx.listing_start_utc,
                "listing_end_utc": ctx.listing_end_utc,
                "discovery_root": ctx.discovery_root,
                "identity_evidence_json": {},
                "read_state": "not_yet_read",
                "scope_delta": spec.scope_delta,
            }
        )
    return rows


def _asset_kind(spec: SourceSpec, member: str | None) -> str:
    if member:
        return "member"
    if spec.uri.endswith(".parquet"):
        return "parquet"
    if spec.uri.endswith(".zip"):
        return "container"
    return "container"


def _compression(member: str | None, uri: str) -> str:
    path = member or uri
    if path.endswith(".gz"):
        return "gzip"
    if uri.endswith(".zip"):
        return "deflate"
    return "none"


def _asset_rows(
    result: AdapterResult,
    spec: SourceSpec,
    ctx: ReductionContext,
    _obj_rows: list[dict],
) -> list[dict]:
    obj_asset = object_id(spec.campaign_id, spec.uri, None, None)
    rows = []
    for a in result.assets:
        member = a.asset_path if a.asset_path != spec.uri else None
        parent = obj_asset if member else None
        rows.append(
            {
                "row_id": row_id("a", a.asset_id),
                "reduction_id": ctx.reduction_id,
                "asset_id": a.asset_id,
                "asset_kind": _asset_kind(spec, member),
                "parent_asset_id": parent,
                "member_path": a.asset_path,
                "s3_uri": spec.uri,
                "object_version": None,
                "object_etag": None,
                "bytes_stored": None,
                "bytes_uncompressed": None,
                "compression": _compression(member, spec.uri),
                "content_sha256": a.sha256,
                "source_sha": a.sha256,
                "hash_scope": a.hash_scope,
                "read_state": a.read_state,
                "adapter_id": result.family,
                "attempt_id": spec.attempt_id,
                "campaign_id": spec.campaign_id,
                "run_uid": None,
            }
        )
    return rows


def _run_rows(
    result: AdapterResult, spec: SourceSpec, ctx: ReductionContext
) -> list[dict]:
    rows = []
    seen: set[str] = set()
    for r in result.runs:
        if r.run_uid in seen:
            continue
        seen.add(r.run_uid)
        rows.append(
            {
                "row_id": row_id("r", r.run_uid),
                "reduction_id": ctx.reduction_id,
                "run_uid": r.run_uid,
                "case_id": _case_id(r.campaign_id, r.cell_id),
                "execution_id": r.original_run_id or r.run_uid,
                "execution_state": "completed",
                "selection_state": r.selection_state,
                "selection_reason": r.detail,
                "seed": r.seed,
                "replicate_id": None,
                "arm_id": None,
                "vessel_id": r.hull_id,
                "stage_id": spec.stage_id,
                "attempt_id": spec.attempt_id,
                "campaign_id": r.campaign_id,
                "engine_sha": r.engine_sha,
                "image_digest": r.image_digest,
                "original_run_id": r.original_run_id,
                "clock_mode": None,
                "configured_epoch_hours": None,
                "effective_epoch_hours": None,
                "epoch_origin_hours": None,
                "epoch_origin_kind": None,
                "input_hash": None,
                "last_complete_epoch": None,
                "requested_duration_hours": None,
                "actual_followup_hours": None,
                "retention_profile": None,
                "rng_streams_json": None,
                "pathogen_ids": None,
                "voyage_start_utc": None,
                "metadata_json": {
                    "cell_id": r.cell_id,
                    "source_id": spec.source_id,
                    "attempt_kind": spec.attempt_kind,
                },
            }
        )
    return rows


def _scalar_rows(result: AdapterResult, ctx: ReductionContext) -> list[dict]:
    rows = []
    for s in result.scalars:
        rows.append(
            {
                "row_id": row_id("rs", s.run_uid, s.native_path),
                "reduction_id": ctx.reduction_id,
                "run_uid": s.run_uid,
                "source_asset_id": s.asset_id,
                "native_path": s.native_path,
                "native_value_json": s.native_value_json,
                "native_type": s.native_type,
                "canonical_metric_id": None,
                "unit": None,
                "mapping_state": "native_only",
            }
        )
    return rows


def _capability_rows(
    _result: AdapterResult, spec: SourceSpec, ctx: ReductionContext
) -> list[dict]:
    from .adapters import family_capabilities

    rows = []
    for c in family_capabilities():
        if c.family != spec.family:
            continue
        rows.append(
            {
                "row_id": row_id("cap", spec.source_id, c.axis),
                "reduction_id": ctx.reduction_id,
                "capability_id": f"cap-{spec.family}-{c.axis}",
                "scope_kind": "campaign",
                "scope_id": spec.scope_id or spec.campaign_id,
                "coverage_unit": "source_family",
                "row_coverage": c.availability,
                "availability": c.availability,
                "recoverability_action": (
                    "read_existing"
                    if c.availability in ("recoverable_unread",)
                    else "not_applicable"
                ),
                "required_members": list(c.telemetry_fields),
                "source_asset_id": None,
                "evidence_detail": c.evidence,
            }
        )
    return rows


def _gap_rows(
    result: AdapterResult, spec: SourceSpec, ctx: ReductionContext
) -> list[dict]:
    rows = []
    for g in result.gaps:
        rows.append(
            {
                "row_id": row_id("g", g.gap_id, g.member or ""),
                "reduction_id": ctx.reduction_id,
                "table_name": "assets" if g.member else "source_objects",
                "target_row_id": row_id("a", g.asset_id) if g.asset_id else None,
                "field_name": g.member,
                "selector_json": (
                    {"member": g.member} if g.member else {"uri": spec.uri}
                ),
                "reason": g.reason,
                "detail": g.detail,
                "recoverability": _GAP_RECOVERABILITY.get(
                    g.reason, "irrecoverable_existing"
                ),
                "source_asset_id": g.asset_id,
                "blocks_claim_ids": [],
            }
        )
    return rows


def _link_rows(
    obj_rows: list[dict],
    asset_rows: list[dict],
    _result: AdapterResult,
    ctx: ReductionContext,
) -> list[dict]:
    rows = []
    obj_row = obj_rows[0] if obj_rows else None
    if obj_row is None:
        return rows
    for a in asset_rows:
        lid = f"sl-{obj_row['object_id'][:12]}-{a['asset_id'][-12:]}"
        rows.append(
            {
                "row_id": row_id("sl", obj_row["object_id"], a["asset_id"]),
                "link_id": lid,
                "reduction_id": ctx.reduction_id,
                "from_table": "source_objects",
                "from_row_id": obj_row["row_id"],
                "to_table": "assets",
                "to_row_id": a["row_id"],
                "relation": (
                    "indexed_member"
                    if a["asset_kind"] == "member"
                    else "identified_object"
                ),
                "selection_effect": "in_scope",
                "confidence": "exact",
                "evidence_json": {"sha256": a["content_sha256"]},
            }
        )
    return rows


def coverage_cell_rows(
    cells: dict[tuple, dict], ctx: ReductionContext
) -> list[dict]:
    """Emit coverage_cells rows from per-cell tallies."""
    rows = []
    for key in sorted(cells):
        c = cells[key]
        scope_id, campaign_id, stage_id, attempt_id, cell_id = key
        status = _coverage_status(c)
        rows.append(
            {
                "row_id": row_id("cc", *key),
                "reduction_id": ctx.reduction_id,
                "scope_id": scope_id,
                "campaign_id": campaign_id,
                "stage_id": stage_id,
                "attempt_id": attempt_id,
                "cell_id": cell_id,
                "declared_runs": c["declared_runs"],
                "landed_physical_objects": c["landed"],
                "indexed_run_members": c["indexed"],
                "parsed_execution_rows": c["parsed"],
                "duplicate_copies": c["duplicates"],
                "conflicting_rows": c["conflicts"],
                "selected_unique_runs": c["selected"],
                "eligible_runs": None,
                "missing_or_unread_runs": c["missing"],
                "coverage_status": status,
                "metric_scope_json": None,
                "evidence_json": c["evidence"],
            }
        )
    return rows


def _coverage_status(c: dict) -> str:
    if c["unsupported"]:
        return "unsupported"
    if c["blocked"]:
        return "blocked"
    declared = c["declared_runs"]
    if c["parsed"] == 0 and c["selected"] == 0:
        return "absent" if declared is None or declared == 0 else "partial"
    if declared is not None and c["selected"] < declared:
        return "partial"
    if c["gaps"]:
        return "partial"
    return "complete"


def catalog_partition_row(
    entry: dict, ctx: ReductionContext, snapshot_id: str
) -> dict:
    """catalog_partitions row for one written shard partition."""
    return {
        "row_id": row_id("cp", entry["uri"]),
        "reduction_id": ctx.reduction_id,
        "partition_id": entry["partition_id"],
        "catalog_snapshot_id": snapshot_id,
        "table_name": entry["table_name"],
        "uri": entry["uri"],
        "sha256": entry["sha256"],
        "rows": entry["rows"],
        "bytes_stored": entry["bytes_stored"],
        "schema_version": TABLE_VERSION,
        "adapter_version": TABLE_VERSION,
        "min_key_json": entry.get("min_key"),
        "max_key_json": entry.get("max_key"),
        "statistics_json": entry.get("statistics"),
        "committed": True,
    }


def reduction_attempt_row(ctx: ReductionContext, status: str,
                          budget: dict, coverage: dict,
                          checkpoint_uri: str | None,
                          start_utc: str, end_utc: str) -> dict:
    return {
        "row_id": row_id("ra", ctx.reduction_id, ctx.phase),
        "reduction_id": ctx.reduction_id,
        "fingerprint": ctx.fingerprint,
        "parent_reduction_id": ctx.parent_reduction_id,
        "request_sha256": ctx.request_sha256,
        "inventory_sha256": ctx.inventory_sha256,
        "implementation_sha": ctx.implementation_sha,
        "image_digest": ctx.image_digest,
        "adapter_registry_sha256": ctx.adapter_registry_sha256,
        "phase": ctx.phase,
        "admission_id": ctx.admission_id,
        "status": status,
        "budget_json": budget,
        "checkpoint_uri": checkpoint_uri,
        "coverage_json": coverage,
        "start_utc": start_utc,
        "end_utc": end_utc,
    }


def weights_rows(run_uids: list[str], ctx: ReductionContext) -> list[dict]:
    """The always-emitted equal-run weight set ``w-equal``."""
    rows = []
    for uid in sorted(run_uids):
        rows.append(
            {
                "row_id": row_id("w", "w-equal", uid),
                "reduction_id": ctx.reduction_id,
                "weight_set_id": "w-equal",
                "target_id": uid,
                "unit_id": uid,
                "unit_kind": "run",
                "weight_kind": "equal_run",
                "weight": 1.0,
                "normalization_scope": "run",
                "validity_status": "complete",
                "provenance_json": {"kind": "equal_run", "note": "baseline"},
            }
        )
    return rows


def distribution_rows(
    metric_values: dict[str, dict[str, list[tuple[str, float | None]]]],
    _run_meta: dict[str, dict],
    ctx: ReductionContext,
    weight_lookup=None,
) -> list[dict]:
    """Base full-run ECDF distributions per (group, metric_id).

    ``metric_values`` maps ``(group_key, metric_id) -> [(run_uid, value)]``
    where ``value`` is ``None`` for a missing/non-numeric scalar. Support
    atoms are every observed value (exact ECDF semantics: F(x) is the mass
    at or below x); missingness is counted, never imputed. ``n_effective``
    is the Kish diagnostic — flagged, not a validity verdict.
    """
    rows = []
    for group_key, by_metric in sorted(metric_values.items()):
        for metric_id, entries in sorted(by_metric.items()):
            observed = [(u, v) for u, v in entries if v is not None]
            missing = [u for u, v in entries if v is None]
            n_eligible = len(entries)
            n_observed = len(observed)
            n_missing = len(missing)
            atoms: dict[float, dict] = {}
            weights = {
                u: (weight_lookup(u) if weight_lookup else 1.0)
                for u, _ in observed
            }
            total_w = sum(weights.values())
            for u, v in observed:
                a = atoms.setdefault(v, {"n": 0, "w": 0.0})
                a["n"] += 1
                a["w"] += weights[u]
            cum = 0.0
            n_eff = _kish(list(weights.values()))
            for i, v in enumerate(sorted(atoms)):
                a = atoms[v]
                cum += a["w"]
                rows.append(
                    {
                        "row_id": row_id("d", group_key, metric_id, i),
                        "reduction_id": ctx.reduction_id,
                        "distribution_id": f"dist-{group_key}-{metric_id}",
                        "metric_id": metric_id,
                        "group_json": {"group": group_key},
                        "support_id": f"{group_key}:{metric_id}:{i}",
                        "support_value": v,
                        "mass_count": a["n"],
                        "weight_sum": a["w"],
                        "cdf": (cum / total_w) if total_w else None,
                        "n_eligible": n_eligible,
                        "n_observed": n_observed,
                        "n_missing": n_missing,
                        "n_effective": n_eff,
                        "missing_reason_counts_json": (
                            {"not_identifiable": n_missing}
                            if n_missing
                            else {}
                        ),
                        "distribution_payload_json": None,
                        "query_id": None,
                    }
                )
    return rows


def _kish(weights: list[float]) -> float | None:
    if not weights:
        return None
    s = sum(weights)
    s2 = sum(w * w for w in weights)
    return (s * s / s2) if s2 else None


def group_key_for_run(run: dict, dims: tuple[str, ...]) -> str:
    return "|".join(str(run.get(d)) for d in dims)


def merge_tables(
    into: dict[str, list[dict]], extra: dict[str, list[dict]]
) -> None:
    for table, rows in extra.items():
        into.setdefault(table, []).extend(rows)
