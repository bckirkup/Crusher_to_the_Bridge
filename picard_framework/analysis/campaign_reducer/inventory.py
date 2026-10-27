"""``analysis inventory`` — bounded metadata cold-inventory (ticket D5).

Runs the fresh enumeration the dated 2026-10-19 register cannot supply:
paginated ``ListObjectsV2`` over every root the admitted
``BOOTSTRAP_REQUEST`` names (``source_roots_allowlist`` — ``campaign/`` is
not assumed to be the only results root), a top-level delimiter discovery
probe for other authorized roots, a per-family present/absent probe for
all 218 register records, and a separate ``ListObjectVersions`` pass so
every candidate carries VersionId provenance distinct from the listing
row itself.

Outputs in ``--out`` (contract outputs ``frozen_inventory`` +
``scope_delta`` + ``coverage``):

- ``frozen_inventory.json`` — index over the exact-key manifest pages
  plus the per-family fresh observations (dated Oct-19 fields retained
  as dated, never overwritten).
- ``inventory/pages/<root-slug>/page-NNNNN.jsonl`` — paginated exact-key
  manifests; one row per object with key/etag/size/storage-class/
  last-modified plus candidate flags (manifest / ``_scan_rows`` mapping /
  schema-candidate-by-extension — documentary, not payload inspection).
- ``inventory/versions/<root-slug>/versions-NNNNN.jsonl`` — VersionId
  provenance pages, keyed to the same object identity.
- ``scope_delta.json`` — additions vs the dated register, derived-root
  exclusions, registered-but-October-absent names (e.g.
  ``campaign/noro_age_food_01_mega/``) with their fresh observation.
- ``coverage.json`` — per-root completeness including typed
  blocked-completeness records for denied/unlistable roots and the
  versions pass; a cap stop is explicit continuation state, never a
  silent truncation.
- ``inventory_state.json`` — the resume cursor document. Pass it back on
  a later run via ``--resume-state`` (a URI fetchable by the same bounded
  rules, or re-supplied as a workflow artifact): completed pages are not
  restarted.

Every failure is typed; boto3 stays lazy so offline runs never touch the
SDK — tests inject a stubbed client object, no moto, no network.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from simulation_utils.paths import prepare_output_directory, validated_open

from .._io import allowed_roots
from . import contracts
from .contracts import sha256 as _contract_sha
from .materialize import DERIVED_ROOT
from .return_path import (
    ReturnFailure,
    _emit,
    _fetch_uri,
    _invalid,
    _out_root,
    _request_doc,
    _run_ids,
)

_PAGE_KEYS = 1000
_STATE_NAME = "inventory_state.json"
_INVENTORY_CAP = 1 << 20  # resume-state fetch bound (1 MiB)

# Extra argv beyond the contract's required ``--request/--out`` — same
# convention as return_path.OPTIONAL_FLAGS (offline store pinning without
# inventing contract fields).
OPTIONAL_FLAGS = ("--store-uri", "--resume-state")

_STATUS_EXIT = {
    "completed": contracts.EXIT_COMPLETE,
    "budget_stopped": contracts.EXIT_BUDGET_STOPPED_CHECKPOINTED,
    "blocked": contracts.EXIT_ACCESS_OR_RESOURCE_BLOCKED,
    "partial": contracts.EXIT_PARTIAL_COVERAGE,
}


def _s3_client():
    """Lazy boto3 client — tests monkeypatch this factory with a stub."""
    import boto3  # noqa: PLC0415

    return boto3.client("s3")


class _BudgetStop(Exception):
    """A declared ceiling was reached mid-enumeration."""

    def __init__(self, field: str) -> None:
        super().__init__(field)
        self.field = field


class _Counters:
    """Spend against the bootstrap ceilings; None is never unlimited."""

    def __init__(self, budgets: dict) -> None:
        self.ceilings = {
            k: float(v) for k, v in (budgets or {}).items()
            if isinstance(v, (int, float)) and not isinstance(v, bool)
        }
        self.spent = dict.fromkeys(self.ceilings, 0.0)
        self.started = time.monotonic()

    def charge(self, field: str, amount: float = 1.0) -> None:
        ceiling = self.ceilings.get(field)
        if ceiling is None:
            return
        if self.spent.get(field, 0.0) + amount > ceiling:
            raise _BudgetStop(field)
        self.spent[field] = self.spent.get(field, 0.0) + amount

    def check_wall(self) -> None:
        limit = self.ceilings.get("max_wall_seconds")
        if limit is not None and time.monotonic() - self.started > limit:
            raise _BudgetStop("max_wall_seconds")


class InventoryFailure(ReturnFailure):
    """Typed inventory failure (same envelope shape as the return path)."""


def _list_call(client, bucket: str, **kwargs) -> dict:
    try:
        return client.list_objects_v2(**kwargs)
    except Exception as exc:  # noqa: BLE001 — botocore ClientError maps by code
        code = str(
            getattr(exc, "response", {}).get("Error", {}).get("Code", "")
            or type(exc).__name__
        )
        kind = {
            "AccessDenied": "access_denied",
            "403": "access_denied",
            "NoSuchBucket": "not_found",
            "SlowDown": "throttled",
        }.get(code, "transient")
        raise InventoryFailure(
            kind, f"list_objects_v2 {kwargs.get('Prefix', '')}: {code}",
            owner="s3_listing",
        ) from exc


def _versions_call(client, bucket: str, **kwargs) -> dict:
    try:
        return client.list_object_versions(**kwargs)
    except Exception as exc:  # noqa: BLE001
        code = str(
            getattr(exc, "response", {}).get("Error", {}).get("Code", "")
            or type(exc).__name__
        )
        kind = {
            "AccessDenied": "access_denied",
            "403": "access_denied",
            "NoSuchBucket": "not_found",
            "SlowDown": "throttled",
        }.get(code, "transient")
        raise InventoryFailure(
            kind, f"list_object_versions {kwargs.get('Prefix', '')}: {code}",
            owner="s3_versioning",
        ) from exc


def _excluded(key: str, excludes: list[str]) -> bool:
    return any(key.startswith(prefix) for prefix in excludes)


def _candidate_flags(key: str) -> dict:
    """Documentary candidate flags — never a payload or success claim."""
    name = key.rsplit("/", 1)[-1].lower()
    ext = name.rsplit(".", 1)[-1] if "." in name else ""
    family_hint = {
        "zip": "archive_zip_candidate",
        "jsonl": "jsonl_candidate",
        "json": "json_candidate",
        "gz": "gzip_candidate",
        "parquet": "parquet_candidate",
    }.get(ext, "unknown_candidate")
    return {
        "schema_candidate": family_hint,
        "is_manifest_key": "manifest" in name,
        "is_scan_rows_key": "_scan_rows" in name,
    }


def _listing_row(key: str, obj: dict, root: str) -> dict:
    row = {
        "key": key,
        "root": root,
        "etag": obj.get("ETag"),
        "bytes": obj.get("Size"),
        "storage_class": obj.get("StorageClass"),
        "last_modified": str(obj.get("LastModified", "")),
    }
    row.update(_candidate_flags(key))
    return row


def _write_page(out_root: str, root_slug: str, index: int, rows: list) -> dict:
    rel = os.path.join(
        "inventory", "pages", root_slug, f"page-{index:05d}.jsonl",
    )
    target = os.path.join(out_root, rel)
    prepare_output_directory(
        os.path.dirname(target), allowed_roots=allowed_roots(),
    )
    body = "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows).encode()
    with validated_open(target, "wb", allowed_roots=allowed_roots()) as fh:
        fh.write(body)
    return {
        "path": rel,
        "rows": len(rows),
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "first_key": rows[0]["key"] if rows else None,
        "last_key": rows[-1]["key"] if rows else None,
    }


def _write_version_page(
    out_root: str, root_slug: str, index: int, rows: list,
) -> dict:
    rel = os.path.join(
        "inventory", "versions", root_slug, f"versions-{index:05d}.jsonl",
    )
    target = os.path.join(out_root, rel)
    prepare_output_directory(
        os.path.dirname(target), allowed_roots=allowed_roots(),
    )
    body = "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows).encode()
    with validated_open(target, "wb", allowed_roots=allowed_roots()) as fh:
        fh.write(body)
    return {
        "path": rel,
        "rows": len(rows),
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
    }


def _root_slug(root: str) -> str:
    slug = root.strip("/").replace("/", "_") or "_bucket_root"
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in slug)


def _load_prior_state(args) -> dict | None:
    """Resume cursor doc from ``--resume-state`` or the request dir."""
    uri = getattr(args, "resume_state", "") or ""
    if uri:
        body = _fetch_uri(uri, _INVENTORY_CAP)
        try:
            doc = json.loads(body)
        except ValueError as exc:
            raise _invalid(f"{uri}: unreadable resume state — {exc}") from exc
    else:
        sibling = Path(args.request).resolve().parent / _STATE_NAME
        if not sibling.is_file():
            return None
        try:
            with validated_open(
                str(sibling), allowed_roots=allowed_roots(),
                encoding="utf-8",
            ) as fh:
                doc = json.load(fh)
        except (OSError, ValueError) as exc:
            raise _invalid(f"{sibling}: unreadable resume state — {exc}") from exc
    if not isinstance(doc, dict) or doc.get("schema") != (
        "crusher-reducer-inventory-state/v1"
    ):
        raise _invalid("resume document is not an inventory_state doc")
    return doc


def _admission_check(request: dict) -> None:
    """The in-envelope admission must exist and not be expired."""
    admission = request.get("admission") or {}
    expires = admission.get("expires_utc")
    if not isinstance(expires, str) or not expires:
        raise InventoryFailure(
            "admission_missing", "admission.expires_utc absent",
            status="blocked",
            exit_code=contracts.EXIT_ADMISSION_REQUIRED_OR_EXCEEDED,
            owner="request_file",
        )
    try:
        expiry = datetime.fromisoformat(expires.replace("Z", "+00:00"))
        expired = expiry <= datetime.now(timezone.utc)
    except (ValueError, OverflowError):
        expired = True
    if expired:
        raise InventoryFailure(
            "admission_expired", f"admission expired {expires}",
            status="blocked",
            exit_code=contracts.EXIT_ADMISSION_REQUIRED_OR_EXCEEDED,
            owner="request_file",
        )


def _register(request: dict) -> list[dict]:
    """The dated scope register — sha-bound to the declared request pin."""
    expected = request.get("scope_register_sha256")
    actual = _contract_sha(contracts.CAMPAIGN_COVERAGE)
    if isinstance(expected, str) and expected and expected != actual:
        raise InventoryFailure(
            "scope_register_mismatch",
            f"scope_register_sha256 {expected[:12]} != register {actual[:12]}",
            status="blocked",
            exit_code=contracts.EXIT_ADMISSION_REQUIRED_OR_EXCEEDED,
            owner="request_file",
        )
    return contracts.load(contracts.CAMPAIGN_COVERAGE)


def _probe_family(client, bucket: str, prefix: str, counters: _Counters) -> dict:
    """Fresh present/absent/blocked observation for one register prefix."""
    counters.charge("max_api_calls_total")
    try:
        page = _list_call(
            client, bucket, Bucket=bucket, Prefix=prefix, MaxKeys=1,
        )
    except InventoryFailure as exc:
        return {
            "fresh_observation": "blocked",
            "blocked_kind": exc.kind,
            "detail": exc.detail,
        }
    seen = int(page.get("KeyCount") or 0)
    return {
        "fresh_observation": "present" if seen else "absent",
        "probe_objects_seen": seen,
    }


def _enumerate_root(
    client, bucket: str, root: str, excludes: list[str],
    counters: _Counters, out_root: str, prior: dict | None,
) -> dict:
    """Paginated exact-key listing of one root; explicit continuation."""
    slug = _root_slug(root)
    state = dict(
        (prior or {}).get("roots", {}).get(root) or {},
    )
    token = state.get("next_token")
    index = int(state.get("pages_completed") or 0)
    objects = int(state.get("objects") or 0)
    excluded = int(state.get("excluded_derived_objects") or 0)
    pages = list(state.get("manifest_pages") or [])
    exhausted = bool(state.get("exhausted"))
    blocked = state.get("blocked")
    while not exhausted:
        try:
            counters.check_wall()
            counters.charge("max_api_calls_total")
            counters.charge("max_list_pages")
        except _BudgetStop as exc:
            blocked = {"kind": "budget_stopped", "detail": exc.field,
                       "owner": "budget_ledger"}
            break
        kwargs: dict = {
            "Bucket": bucket, "Prefix": root, "MaxKeys": _PAGE_KEYS,
        }
        if token:
            kwargs["ContinuationToken"] = token
        try:
            page = _list_call(client, bucket, **kwargs)
        except InventoryFailure as exc:
            blocked = {"kind": exc.kind, "detail": exc.detail,
                       "owner": exc.owner}
            break
        rows = []
        try:
            for obj in page.get("Contents") or []:
                key = obj["Key"]
                if _excluded(key, excludes):
                    excluded += 1
                    continue
                counters.charge("max_source_objects")
                objects += 1
                rows.append(_listing_row(key, obj, root))
        except _BudgetStop as exc:
            # A cap mid-page drops the unwritten page — the retained
            # token still points before it, so resume re-fetches it.
            blocked = {"kind": "budget_stopped", "detail": exc.field,
                       "owner": "budget_ledger"}
            break
        index += 1
        if rows:
            pages.append(_write_page(out_root, slug, index, rows))
        token = page.get("NextContinuationToken")
        exhausted = not token
    return {
        "root": root,
        "exhausted": exhausted,
        "next_token": token,
        "pages_completed": index,
        "objects": objects,
        "excluded_derived_objects": excluded,
        "manifest_pages": pages,
        "blocked": blocked,
    }


def _enumerate_versions(
    client, bucket: str, root: str, counters: _Counters,
    out_root: str, prior: dict | None,
) -> dict:
    """VersionId provenance pass — separate rows from the listing."""
    slug = _root_slug(root)
    state = dict(
        (prior or {}).get("version_roots", {}).get(root) or {},
    )
    key_marker = state.get("key_marker")
    version_marker = state.get("version_id_marker")
    index = int(state.get("pages_completed") or 0)
    objects = int(state.get("objects") or 0)
    pages = list(state.get("manifest_pages") or [])
    exhausted = bool(state.get("exhausted"))
    blocked = state.get("blocked")
    while not exhausted:
        try:
            counters.check_wall()
            counters.charge("max_api_calls_total")
            counters.charge("max_list_pages")
        except _BudgetStop as exc:
            blocked = {"kind": "budget_stopped", "detail": exc.field,
                       "owner": "budget_ledger"}
            break
        kwargs: dict = {"Bucket": bucket, "Prefix": root}
        if key_marker:
            kwargs["KeyMarker"] = key_marker
        if version_marker:
            kwargs["VersionIdMarker"] = version_marker
        try:
            page = _versions_call(client, bucket, **kwargs)
        except InventoryFailure as exc:
            blocked = {"kind": exc.kind, "detail": exc.detail,
                       "owner": exc.owner}
            break
        index += 1
        rows = []
        try:
            for obj in page.get("Versions") or []:
                counters.charge("max_source_objects")
                objects += 1
                rows.append({
                    "key": obj["Key"],
                    "version_id": obj.get("VersionId"),
                    "is_latest": obj.get("IsLatest"),
                    "bytes": obj.get("Size"),
                    "storage_class": obj.get("StorageClass"),
                    "last_modified": str(obj.get("LastModified", "")),
                    "provenance": "list_object_versions",
                })
        except _BudgetStop as exc:
            blocked = {"kind": "budget_stopped", "detail": exc.field,
                       "owner": "budget_ledger"}
            break
        for marker in page.get("DeleteMarkers") or []:
            rows.append({
                "key": marker["Key"],
                "version_id": marker.get("VersionId"),
                "is_latest": marker.get("IsLatest"),
                "bytes": None,
                "storage_class": "DELETE_MARKER",
                "last_modified": str(marker.get("LastModified", "")),
                "provenance": "list_object_versions",
            })
        if rows:
            pages.append(_write_version_page(out_root, slug, index, rows))
        key_marker = page.get("NextKeyMarker")
        version_marker = page.get("NextVersionIdMarker")
        exhausted = not page.get("IsTruncated")
    return {
        "root": root,
        "exhausted": exhausted,
        "key_marker": key_marker,
        "version_id_marker": version_marker,
        "pages_completed": index,
        "objects": objects,
        "manifest_pages": pages,
        "blocked": blocked,
    }


def _discover_roots(client, bucket: str, counters: _Counters) -> dict:
    """Stage-0 delimiter probe for other authorized bucket roots."""
    try:
        counters.charge("max_api_calls_total")
        page = _list_call(
            client, bucket, Bucket=bucket, Delimiter="/",
            # An omitted Prefix leaves s3:prefix absent from the request
            # context, so the collector's ``""`` grant cannot match and the
            # probe denies; sending it explicitly carries ``prefix=`` on
            # the wire (live-proven on the D5 inventory run).
            Prefix="", MaxKeys=_PAGE_KEYS,
        )
    except InventoryFailure as exc:
        return {
            "state": "blocked",
            "blocked": {"kind": exc.kind, "detail": exc.detail,
                        "owner": exc.owner},
            "discovered_top_level": [],
        }
    return {
        "state": "complete",
        "blocked": None,
        "discovered_top_level": sorted(
            p["Prefix"] for p in page.get("CommonPrefixes") or []
        ),
        "truncated": bool(page.get("IsTruncated")),
    }


def _family_rows(records: list[dict], probes: dict) -> list[dict]:
    """Per-record fresh observation joined to the dated register row."""
    rows = []
    for record in records:
        prefix = record.get("prefix")
        dated = record.get("historical_object_metadata") or {}
        row = {
            "record_id": record.get("record_id"),
            "record_kind": record.get("record_kind"),
            "prefix": prefix,
            "program_group": record.get("program_group"),
            "schema_family": record.get("schema_family"),
            "historical_prefix_observed_oct19": record.get(
                "historical_prefix_observed_oct19",
            ),
            "dated_oct19": {
                "objects_listed": dated.get("objects_listed"),
                "bytes_listed": dated.get("bytes_listed"),
                "truncated": dated.get("truncated"),
                "as_of": (dated.get("observation_window") or {}).get(
                    "targeted_index_generated_at",
                ),
                "counts_are_dated_not_current": True,
            },
        }
        row.update(probes.get(prefix) or {"fresh_observation": "unobserved"})
        rows.append(row)
    return rows


def _scope_delta(
    records: list[dict], family_rows: list[dict], discovery: dict,
    roots_seen: list[str],
) -> dict:
    """Additive delta vs the dated register — Oct-19 counts stay dated."""
    union_names = {
        record.get("prefix") for record in records if record.get("prefix")
    }
    listed_names = {
        row["prefix"] for row in family_rows
        if row.get("fresh_observation") == "present"
    }
    additions = sorted(
        prefix for prefix in listed_names if prefix not in union_names
    )
    discovered_roots = [
        root for root in discovery.get("discovered_top_level") or []
        if root not in roots_seen
    ]
    registered_absent_oct19 = [
        {
            "record_id": row["record_id"],
            "prefix": row["prefix"],
            "fresh_observation": row["fresh_observation"],
        }
        for row in family_rows
        if row.get("historical_prefix_observed_oct19") is False
    ]
    now_absent = [
        row["prefix"] for row in family_rows
        if row.get("fresh_observation") == "absent"
        and row.get("record_kind") == "historical_prefix"
    ]
    return {
        "schema": "crusher-reducer-scope-delta/v1",
        "dated_register": {
            "as_of": "2026-10-19",
            "records": len(records),
            "union_prefix_names": len(union_names),
            "counts_are_dated_not_current": True,
            "note": "Oct-19 counts are a dated snapshot retained as dated — "
                    "never overwritten, never represented as fresh.",
        },
        "fresh_additions": additions,
        "discovered_roots_outside_allowlist": discovered_roots,
        "registered_absent_oct19_fresh_observation": registered_absent_oct19,
        "oct19_rows_now_absent": sorted(now_absent),
        "derived_excluded": True,
    }


def _blocked_records(roots: list[dict], versions: list[dict], discovery: dict) -> list:
    """Typed blocked-completeness records — a denial is never an absence."""
    records = []
    for result in roots:
        if result.get("blocked"):
            records.append({
                "scope": "root_listing",
                "root": result["root"],
                **result["blocked"],
            })
    for result in versions:
        if result.get("blocked"):
            records.append({
                "scope": "version_provenance",
                "root": result["root"],
                **result["blocked"],
            })
    if discovery.get("blocked"):
        records.append({
            "scope": "root_discovery",
            "root": "",
            **discovery["blocked"],
        })
    return records


def run(args) -> int:
    """Dispatch the inventory op; typed failures still write coverage."""
    out_root = _out_root(args.out, "inventory")
    if out_root is None:
        return contracts.EXIT_INVALID_CONTRACT
    try:
        request = _request_doc(args, "bootstrap")
        if request.get("operation") != "inventory":
            raise _invalid(
                f"operation {request.get('operation')!r} is not inventory",
            )
        _admission_check(request)
        records = _register(request)
        prior = _load_prior_state(args)
        counters = _Counters(request.get("budgets") or {})
        bucket = request.get("source_bucket")
        if not isinstance(bucket, str) or not bucket:
            raise _invalid("request names no source_bucket")
        client = _s3_client()
        roots = [
            r if r.endswith("/") else f"{r}/"
            for r in request.get("source_roots_allowlist") or []
        ]
        excludes = [
            p if p.endswith("/") else f"{p}/"
            for p in request.get("derived_exclude_prefixes") or []
        ]
        if not excludes:
            excludes = [f"{DERIVED_ROOT}/"]
        started_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        stop_reason = None
        root_results = []
        version_results = []
        probes = {}
        discovery = {"state": "skipped", "blocked": None,
                     "discovered_top_level": []}
        try:
            discovery = _discover_roots(client, bucket, counters)
            for root in roots:
                root_results.append(_enumerate_root(
                    client, bucket, root, excludes, counters,
                    out_root, prior,
                ))
            for root in roots:
                version_results.append(_enumerate_versions(
                    client, bucket, root, counters, out_root, prior,
                ))
            for record in records:
                prefix = record.get("prefix")
                if not prefix or prefix in probes:
                    continue
                probes[prefix] = _probe_family(
                    client, bucket, prefix, counters,
                )
        except _BudgetStop as exc:
            stop_reason = f"budget_stopped:{exc.field}"
        ended_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        family_rows = _family_rows(records, probes)
        blocked = _blocked_records(root_results, version_results, discovery)
        if not stop_reason:
            stop_reason = next(
                (
                    f"budget_stopped:{b.get('detail')}"
                    for b in blocked
                    if b.get("kind") == "budget_stopped"
                ),
                None,
            )
        exhausted = all(r.get("exhausted") for r in root_results)
        status = (
            "budget_stopped" if stop_reason
            else "blocked" if blocked
            else "partial" if not exhausted
            else "completed"
        )
        inventory_doc = {
            "schema": "crusher-reducer-frozen-inventory/v1",
            "request_id": request.get("request_id"),
            "status": status,
            "source_bucket": bucket,
            "observation_window": {
                "listing_start_utc": started_utc,
                "listing_end_utc": ended_utc,
            },
            "families": family_rows,
            "roots": root_results,
            "version_roots": version_results,
            "stop_reason": stop_reason,
            **_run_ids(),
        }
        delta_doc = _scope_delta(records, family_rows, discovery, roots)
        coverage_doc = {
            "schema": "crusher-reducer-inventory-coverage/v1",
            "request_id": request.get("request_id"),
            "status": status,
            "complete": exhausted and not blocked and not stop_reason,
            "blocked_completeness": blocked,
            "continuation": {
                r["root"]: r.get("next_token")
                for r in root_results if not r.get("exhausted")
            },
            "budget_spent": counters.spent,
            "budget_ceilings": counters.ceilings,
            "stop_reason": stop_reason,
            **_run_ids(),
        }
        state_doc = {
            "schema": "crusher-reducer-inventory-state/v1",
            "request_id": request.get("request_id"),
            "roots": {r["root"]: r for r in root_results},
            "version_roots": {r["root"]: r for r in version_results},
        }
        _emit(out_root, "frozen_inventory.json", inventory_doc)
        _emit(out_root, "scope_delta.json", delta_doc)
        _emit(out_root, "coverage.json", coverage_doc)
        _emit(out_root, _STATE_NAME, state_doc)
        _emit(out_root, "status.json", {
            "status": status, "operation": "inventory",
            "request_id": request.get("request_id"),
            "stop_reason": stop_reason, **_run_ids(),
        })
        print(json.dumps({"status": status, "operation": "inventory",
                          "stop_reason": stop_reason}))
        return _STATUS_EXIT[status]
    except ReturnFailure as exc:
        doc = {
            "status": exc.status,
            "operation": "inventory",
            "error": {"kind": exc.kind, "detail": exc.detail,
                      "owner": exc.owner},
            **_run_ids(),
        }
        _emit(out_root, "status.json", doc)
        print(json.dumps(doc))
        return exc.exit_code
