"""Explicit adapter registry keyed to SOURCE_FAMILIES.json (ticket D1).

One adapter per contract ``schema_family`` — registration is verified
programmatically against the contract (set equality, never a hardcoded
count), so a family added upstream without an adapter fails loudly at
``verify_registry()`` rather than silently reducing to nothing.

Adapters are strictly offline: they take an :class:`ObjectTransport` and
read through the pinned bounded readers. Every decoded scan row is
preserved losslessly — unknown fields are kept with their JSON Pointer,
native JSON token and native type; ``0``/``false``/``null`` stay distinct;
missing denominators stay null (``readout_helpers``), never a confident
zero.

Capability rows derive from each family's ``AR/timing/mechanism/role``
blocks: ``known_saved`` → ``recoverable_unread``,
``documented_unverified`` → ``partial``, ``unknown`` → ``unknown``.
"""
from __future__ import annotations

import gzip
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .contracts import SOURCE_FAMILIES, load
from .identity import member_asset_id, object_id, run_uid, sha256_hex
from .payloads import (
    AdapterResult,
    AssetRecord,
    CapabilityRecord,
    DecodedDoc,
    GapRecord,
    LinkRecord,
    RunRecord,
    ScalarRecord,
    json_pointer,
    link_for,
    native_token,
)
from .pinned_reader import (
    STATE_AVAILABLE,
    STATE_UNSUPPORTED_SCHEMA,
    MemoryTransport,
    ObjectTransport,
    ReadBudget,
    ReadOutcome,
    SourceReadError,
    open_pinned,
)
from .zip_members import open_zip

_SUMMARY_JSON = "summary.json"

_CAPABILITY_BY_STATUS = {
    "known_saved": "recoverable_unread",
    "documented_unverified": "partial",
    "unknown": "unknown",
}

_CAPABILITY_AXES = ("AR", "timing", "mechanism", "role")

_GAP_REASON_BY_STATE = {
    "missing_member": "member_missing",
    "missing_object": "unreachable",
    "access_denied": "unreachable",
    "archived_unrestored": "unreachable",
    "corrupt_archive": "malformed",
    "crc_failure": "malformed",
    "decode_failure": "malformed",
    "source_changed": "identity_unresolved",
    "unsupported_schema": "unknown_schema",
    "unknown_schema": "unknown_schema",
    "unsupported_compression": "unknown_schema",
    "resource_limit": "unreachable",
    "duplicate_members": "malformed",
    "unpinned_blocked": "identity_unresolved",
    "transport_error": "unreachable",
    "not_yet_read": "unreachable",
}


@dataclass(frozen=True)
class SourceRef:
    """One source object an adapter is asked to read."""

    source_id: str
    uri: str
    campaign_id: str
    seed: int | None = None
    original_run_id: str | None = None
    hull_id: str | None = None
    cell_id: str | None = None
    engine_sha: str | None = None
    image_digest: str | None = None

    def run_id(self) -> str:
        """Attempt-scoped run identity — same seed in a different
        hull/cell/engine attempt never collides."""
        return run_uid(
            campaign_id=self.campaign_id,
            attempt_id=self.source_id,
            vessel_id=self.hull_id or "",
            case_id=self.cell_id or "",
            engine_sha=self.engine_sha or "",
            image_digest=self.image_digest or "",
            seed=self.seed,
            original_run_id=self.original_run_id or "",
        )


def _gap(source: SourceRef, state: str, detail: str, member: str | None = None,
         asset_id: str | None = None) -> GapRecord:
    return GapRecord(
        gap_id=f"gap-{source.source_id}-{state}",
        source_id=source.source_id,
        reason=_GAP_REASON_BY_STATE.get(state, "malformed"),
        detail=detail,
        member=member,
        asset_id=asset_id,
    )


def _open(ref: SourceRef, transport: ObjectTransport, budget: ReadBudget):
    """HEAD-pin a source ref; returns (PinnedObject|None, LinkRecord|None)."""
    try:
        from .pinned_reader import parse_s3_uri

        bucket, key = parse_s3_uri(ref.uri)
    except ValueError:
        bucket, key = ref.campaign_id, ref.uri
    try:
        return open_pinned(transport, bucket, key, budget), None
    except SourceReadError as exc:
        return None, link_for(ref.source_id, ref.uri, None, exc.state, exc.detail)


def _scalars_from_doc(run_id: str, doc: Any, prefix: str, metric_prefix: str,
                      asset_id: str | None = None) -> list[ScalarRecord]:
    """Losslessly flatten one decoded JSON document into scalar rows.

    Every leaf — including fields the reducer does not know — becomes a
    ScalarRecord with its JSON Pointer and verbatim token.
    """
    out: list[ScalarRecord] = []

    def walk(node: Any, path: list[str]) -> None:
        if isinstance(node, dict):
            for key in sorted(node):
                walk(node[key], [*path, str(key)])
            return
        if isinstance(node, list):
            for idx, item in enumerate(node):
                walk(item, [*path, str(idx)])
            return
        token, ntype = native_token(node)
        out.append(
            ScalarRecord(
                run_uid=run_id,
                metric_id=f"{metric_prefix}.{'.'.join(path)}",
                native_path=json_pointer(prefix, *path),
                native_value_json=token,
                native_type=ntype,
                value_status="exact_emitted",
                value=node if ntype in ("number", "boolean", "string") else None,
                asset_id=asset_id,
            ),
        )

    walk(doc, [])
    return out


def _run_record(ref: SourceRef) -> RunRecord:
    return RunRecord(
        run_uid=ref.run_id(),
        campaign_id=ref.campaign_id,
        selection_state="selected",
        seed=ref.seed,
        original_run_id=ref.original_run_id,
        hull_id=ref.hull_id,
        cell_id=ref.cell_id,
        engine_sha=ref.engine_sha,
        image_digest=ref.image_digest,
    )


def _asset_id(obj, ref: SourceRef, member: str | None) -> str:
    """The assets.asset_id for one member (or the whole object)."""
    if member:
        return member_asset_id(
            object_id(ref.campaign_id, ref.uri, obj.pin.version_id, obj.pin.etag),
            member,
        )
    return object_id(ref.campaign_id, ref.uri, obj.pin.version_id, obj.pin.etag)


def _asset(obj, ref: SourceRef, member: str | None, read_state: str,
           scope: str, sha: str | None, detail: str = "") -> AssetRecord:
    path = member or ref.uri
    aid = _asset_id(obj, ref, member)
    return AssetRecord(
        asset_id=aid,
        source_id=ref.source_id,
        asset_path=path,
        read_state=read_state,
        hash_scope=scope,
        sha256=sha,
        detail=detail,
    )


def _object_read_state_for_failures(ref: SourceRef, failure: LinkRecord, result: AdapterResult) -> None:
    result.links.append(failure)
    result.gaps.append(_gap(ref, failure.internal_state, failure.detail))


def _read_or_fail(obj, ref: SourceRef, result: AdapterResult, reader) -> bytes | None:
    """A bounded read with the link+gap failure pair recorded; None on fail."""
    try:
        return reader()
    except SourceReadError as exc:
        result.links.append(link_for(ref.source_id, ref.uri, obj, exc.state, exc.detail))
        result.gaps.append(_gap(ref, exc.state, exc.detail))
        return None


def _adapter_zip_scan_rows(
    member_names: tuple[str, ...], metric_prefix: str,
) -> Callable[[SourceRef, ObjectTransport, ReadBudget], AdapterResult]:
    """Adapter factory for ZIP families carrying summary/timeseries members.

    Indexes the archive, then reads every member whose *basename* is one of
    ``member_names`` — per-run archives match at top level, fused shard
    archives match once per nested run folder (``run_7/summary.json``), and
    each folder produces its own ``RunRecord`` so fused runs never collapse
    into the first summary found. Decoded rows are flattened losslessly and
    member-level assets carry ``uncompressed_member`` hashes — a distinct
    role from the ``container_bytes`` object hash.
    """

    def adapter(ref: SourceRef, transport: ObjectTransport, budget: ReadBudget) -> AdapterResult:
        result = AdapterResult(family=metric_prefix)
        obj, failure = _open(ref, transport, budget)
        if obj is None:
            _object_read_state_for_failures(ref, failure, result)
            return result
        index, err = open_zip(obj)
        if index is None:
            result.links.append(link_for(ref.source_id, ref.uri, obj, err.state, err.detail))
            result.gaps.append(_gap(ref, err.state, err.detail))
            return result
        result.links.append(link_for(ref.source_id, ref.uri, obj, STATE_AVAILABLE))
        for name in index.duplicates:
            result.gaps.append(
                _gap(ref, "duplicate_members",
                     f"{len(index.duplicates[name])} members named {name!r}", member=name),
            )
        _read_zip_groups(obj, index, ref, member_names, metric_prefix, result)
        return result

    return adapter


def _read_zip_groups(obj, index, ref: SourceRef, member_names: tuple[str, ...],
                     metric_prefix: str, result: AdapterResult) -> None:
    """Read every declared member basename, grouped by run folder."""
    groups: dict[str, list] = {}
    for entry in index.entries:
        if entry.name.rsplit("/", 1)[-1] in member_names:
            folder = entry.name.rsplit("/", 1)[0] if "/" in entry.name else ""
            groups.setdefault(folder, []).append(entry)
    for folder in sorted(groups):
        group_ref = _folder_ref(ref, folder)
        result.runs.append(_run_record(group_ref))
        for entry in sorted(groups[folder], key=lambda e: e.name):
            _read_scan_member(obj, entry, group_ref, metric_prefix, result)
    if not result.runs:
        result.runs.append(_run_record(ref))
        result.gaps.append(
            _gap(ref, "member_missing",
                 f"no member named {member_names} at any folder level"),
        )


def _folder_ref(ref: SourceRef, folder: str) -> SourceRef:
    """The run identity for one folder inside a (possibly fused) archive."""
    if not folder:
        return ref
    return SourceRef(
        source_id=f"{ref.source_id}:{folder}",
        uri=f"{ref.uri}#{folder}",
        campaign_id=ref.campaign_id,
        seed=ref.seed,
        original_run_id=ref.original_run_id,
        hull_id=ref.hull_id,
        cell_id=ref.cell_id,
        engine_sha=ref.engine_sha,
        image_digest=ref.image_digest,
    )


def _read_scan_member(obj, entry, ref: SourceRef,
                      metric_prefix: str, result: AdapterResult) -> None:
    """One declared scan member: bounded read → decode → lossless scalars."""
    from .zip_members import read_member as _read

    try:
        body = _read(obj, entry)
        state, detail = "available", ""
    except SourceReadError as exc:
        body, state, detail = None, exc.state, exc.detail
    aid = _asset_id(obj, ref, entry.name)
    result.assets.append(
        _asset(obj, ref, entry.name, _asset_state(state),
               "uncompressed_member",
               sha256_hex(body) if body is not None else None, detail),
    )
    if body is None:
        result.gaps.append(_gap(ref, state, detail, member=entry.name, asset_id=aid))
        return
    payload = body
    if entry.name.endswith(".gz"):
        try:
            payload = gzip.decompress(payload)
        except (gzip.BadGzipFile, EOFError) as exc:
            result.gaps.append(
                _gap(ref, "decode_failure",
                     f"member {entry.name!r} gzip stream invalid: {exc}",
                     member=entry.name, asset_id=aid),
            )
            return
    try:
        doc = json.loads(payload)
    except json.JSONDecodeError:
        result.gaps.append(
            _gap(ref, "malformed", f"member {entry.name!r} is not JSON",
                 member=entry.name, asset_id=aid),
        )
        return
    result.scalars.extend(
        _scalars_from_doc(ref.run_id(), doc, "", metric_prefix, asset_id=aid),
    )
    result.docs.append(
        DecodedDoc(run_uid=ref.run_id(), asset_id=aid,
                   member_path=entry.name, doc=doc),
    )


def _asset_state(read_state: str) -> str:
    """assets.read_state for a member/container read outcome."""
    return {
        "available": "read",
        "missing_member": "missing",
        "unsupported_compression": "malformed",
        "unsupported_schema": "malformed",
        "crc_failure": "malformed",
        "decode_failure": "malformed",
        "corrupt_archive": "malformed",
        "duplicate_members": "malformed",
        "resource_limit": "unreachable",
        "source_changed": "unreachable",
        "missing_object": "unreachable",
        "access_denied": "unreachable",
        "archived_unrestored": "unreachable",
        "unpinned_blocked": "unreachable",
        "transport_error": "unreachable",
        "not_yet_read": "not_requested",
    }.get(read_state, "malformed")


def _adapter_json(metric_prefix: str) -> Callable:
    """Whole-object JSON adapter (cell/screen/perturbation/NUTS families)."""

    def adapter(ref: SourceRef, transport: ObjectTransport, budget: ReadBudget) -> AdapterResult:
        result = AdapterResult(family=metric_prefix)
        obj, failure = _open(ref, transport, budget)
        if obj is None:
            _object_read_state_for_failures(ref, failure, result)
            return result
        body = _read_or_fail(obj, ref, result, obj.read_whole)
        if body is None:
            return result
        _emit_json_doc(obj, ref, result, body, metric_prefix, "container_bytes",
                       "object body is not valid JSON")
        return result

    return adapter


def _emit_json_doc(obj, ref: SourceRef, result: AdapterResult, body: bytes,
                   metric_prefix: str, hash_scope: str, not_json_detail: str) -> None:
    """Decode + flatten a JSON body into link/asset/run/scalar rows."""
    try:
        doc = json.loads(body)
    except json.JSONDecodeError:
        result.links.append(link_for(ref.source_id, ref.uri, obj,
                                     STATE_UNSUPPORTED_SCHEMA, not_json_detail))
        result.gaps.append(_gap(ref, "unsupported_schema", not_json_detail))
        return
    sha = sha256_hex(body)
    result.links.append(link_for(ref.source_id, ref.uri, obj, STATE_AVAILABLE, sha256=sha))
    result.assets.append(_asset(obj, ref, None, "read", hash_scope, sha))
    result.runs.append(_run_record(ref))
    aid = _asset_id(obj, ref, None)
    result.scalars.extend(_scalars_from_doc(ref.run_id(), doc, "", metric_prefix,
                                          asset_id=aid))
    result.docs.append(
        DecodedDoc(run_uid=ref.run_id(), asset_id=aid, member_path=None, doc=doc),
    )


def _adapter_jsonl(metric_prefix: str) -> Callable:
    """JSONL adapter — each row preserved losslessly, per-row schema typed."""

    def adapter(ref: SourceRef, transport: ObjectTransport, budget: ReadBudget) -> AdapterResult:
        result = AdapterResult(family=metric_prefix)
        obj, failure = _open(ref, transport, budget)
        if obj is None:
            _object_read_state_for_failures(ref, failure, result)
            return result
        body = _read_or_fail(obj, ref, result, obj.read_whole)
        if body is None:
            return result
        sha = sha256_hex(body)
        result.links.append(link_for(ref.source_id, ref.uri, obj, STATE_AVAILABLE, sha256=sha))
        result.assets.append(_asset(obj, ref, None, "read", "container_bytes", sha))
        result.runs.append(_run_record(ref))
        for lineno, raw in enumerate(body.decode("utf-8", "replace").splitlines()):
            if not raw.strip():
                continue
            try:
                doc = json.loads(raw)
            except json.JSONDecodeError:
                result.gaps.append(
                    _gap(ref, "malformed", f"JSONL line {lineno + 1} is not JSON"),
                )
                continue
            aid = _asset_id(obj, ref, None)
            result.scalars.extend(
                _scalars_from_doc(ref.run_id(), doc, str(lineno), metric_prefix,
                                  asset_id=aid),
            )
            result.docs.append(
                DecodedDoc(run_uid=ref.run_id(), asset_id=aid,
                           member_path=f"line:{lineno}", doc=doc),
            )
        return result

    return adapter


def _adapter_gzip_json(metric_prefix: str) -> Callable:
    """Gzip-wrapped JSON adapter (fomite diagnostic family)."""

    def adapter(ref: SourceRef, transport: ObjectTransport, budget: ReadBudget) -> AdapterResult:
        result = AdapterResult(family=metric_prefix)
        obj, failure = _open(ref, transport, budget)
        if obj is None:
            _object_read_state_for_failures(ref, failure, result)
            return result
        blob = _read_or_fail(obj, ref, result, obj.read_whole)
        if blob is None:
            return result
        try:
            body = gzip.decompress(blob)
        except (gzip.BadGzipFile, EOFError) as exc:
            result.links.append(link_for(ref.source_id, ref.uri, obj, "decode_failure", str(exc)))
            result.gaps.append(_gap(ref, "decode_failure", str(exc)))
            return result
        _emit_json_doc(obj, ref, result, body, metric_prefix, "file_bytes",
                       "gunzipped body is not JSON")
        return result

    return adapter


def _adapter_unknown(metric_prefix: str) -> Callable:
    """Unknown-legacy adapter: inventory only, never fabricated schema."""

    def adapter(ref: SourceRef, transport: ObjectTransport, budget: ReadBudget) -> AdapterResult:
        result = AdapterResult(family=metric_prefix)
        obj, failure = _open(ref, transport, budget)
        if obj is None:
            _object_read_state_for_failures(ref, failure, result)
            return result
        result.links.append(
            link_for(ref.source_id, ref.uri, obj, STATE_AVAILABLE,
                     "inventory only: family is unknown_legacy"),
        )
        result.assets.append(
            _asset(obj, ref, None, "listed", "not_computed", None,
                   "format unknown; not fabricated from naming"),
        )
        result.gaps.append(
            _gap(ref, "unknown_schema", "family unknown_legacy: format not declared"),
        )
        return result

    return adapter


def _adapter_parquet(metric_prefix: str) -> Callable:
    """Parquet sidecar adapter (bounded-region merged shards).

    Parquet decoding is D2 materialization territory; D1 reads the object
    pinned, verifies the ``PAR1`` magic envelope, and preserves the bytes —
    decoded rows arrive when the materializer lands.
    """

    def adapter(ref: SourceRef, transport: ObjectTransport, budget: ReadBudget) -> AdapterResult:
        result = AdapterResult(family=metric_prefix)
        obj, failure = _open(ref, transport, budget)
        if obj is None:
            _object_read_state_for_failures(ref, failure, result)
            return result
        head = _read_or_fail(obj, ref, result, lambda: obj.read_range(0, 3))
        if head is None:
            return result
        if head != b"PAR1":
            result.links.append(link_for(ref.source_id, ref.uri, obj, STATE_UNSUPPORTED_SCHEMA,
                                         "not a PAR1 parquet object"))
            result.gaps.append(_gap(ref, "unsupported_schema", "missing PAR1 magic"))
            return result
        result.links.append(link_for(ref.source_id, ref.uri, obj, STATE_AVAILABLE))
        result.assets.append(
            _asset(obj, ref, None, "indexed", "container_bytes", None,
                   "PAR1 envelope verified; decode is D2 materialization"),
        )
        return result

    return adapter


# Registry keys are the contract schema_family literals exactly.
ADAPTER_REGISTRY: dict[str, Callable[[SourceRef, ObjectTransport, ReadBudget], AdapterResult]] = {
    "growth_census_zip": _adapter_zip_scan_rows(
        (_SUMMARY_JSON, "growth_census.json.gz", "rss_samples.json"),
        "growth_census_zip",
    ),
    "campaign_summary_zip": _adapter_zip_scan_rows(
        (_SUMMARY_JSON, "timeseries.json", "ground_truth.json"),
        "campaign_summary_zip",
    ),
    "covid_screen_json": _adapter_json("covid_screen_json"),
    "flu_cell_json": _adapter_json("flu_cell_json"),
    "bounded_region_jsonl": _adapter_jsonl("bounded_region_jsonl"),
    "perturbation_json": _adapter_json("perturbation_json"),
    "stan_nuts_json": _adapter_json("stan_nuts_json"),
    "fomite_diagnostic_gzip": _adapter_gzip_json("fomite_diagnostic_gzip"),
    "unknown_legacy": _adapter_unknown("unknown_legacy"),
    "wastewater_campaign_zip": _adapter_zip_scan_rows(
        (_SUMMARY_JSON, "timeseries.json", "wastewater.json", "ground_truth.json"),
        "wastewater_campaign_zip",
    ),
    "observation_jsonl": _adapter_jsonl("observation_jsonl"),
}

# Parquet objects inside a family's expected formats use this sidecar
# adapter; the family adapters above route through it when a ref's URI
# ends in .parquet.
PARQUET_ADAPTER = _adapter_parquet("parquet_sidecar")


def contract_families() -> list[str]:
    """The schema_family keys declared by SOURCE_FAMILIES.json."""
    return [entry["schema_family"] for entry in load(SOURCE_FAMILIES)]


def verify_registry() -> dict[str, Any]:
    """Programmatic registry↔contract reconciliation.

    Returns a report; ``ok`` is true only when the registered adapter keys
    exactly equal the contract's schema_family set — count derived, never
    hardcoded.
    """
    families = set(contract_families())
    registered = set(ADAPTER_REGISTRY)
    return {
        "ok": families == registered,
        "families": sorted(families),
        "registered": sorted(registered),
        "missing_adapters": sorted(families - registered),
        "extra_adapters": sorted(registered - families),
        "family_count": len(families),
    }


def family_capabilities() -> list[CapabilityRecord]:
    """One CapabilityRecord per family×axis, status-mapped from the contract."""
    caps: list[CapabilityRecord] = []
    for fam in load(SOURCE_FAMILIES):
        for axis in _CAPABILITY_AXES:
            block = fam.get(axis) or {}
            caps.append(
                CapabilityRecord(
                    family=fam["schema_family"],
                    axis=axis,
                    availability=_CAPABILITY_BY_STATUS.get(
                        block.get("status", "unknown"), "unknown",
                    ),
                    telemetry_fields=list(block.get("telemetry_fields") or []),
                    evidence=(block.get("limitation") or ""),
                ),
            )
    return caps


def reduce_source(
    family: str,
    ref: SourceRef,
    transport: ObjectTransport | None = None,
    budget: ReadBudget | None = None,
) -> AdapterResult:
    """Dispatch one source to its family adapter with a fresh default budget."""
    transport = transport if transport is not None else MemoryTransport()
    budget = budget if budget is not None else ReadBudget()
    if ref.uri.endswith(".parquet"):
        return PARQUET_ADAPTER(ref, transport, budget)
    return adapter_for(family)(ref, transport, budget)


def adapter_for(family: str) -> Callable[[SourceRef, ObjectTransport, ReadBudget], AdapterResult]:
    """The adapter registered for a contract schema_family."""
    return ADAPTER_REGISTRY[family]


def read_outcome_for(ref: SourceRef, transport: ObjectTransport,
                     budget: ReadBudget | None = None) -> ReadOutcome:
    """HEAD+pin outcome for one ref without running its adapter (inventory)."""
    try:
        from .pinned_reader import parse_s3_uri

        bucket, key = parse_s3_uri(ref.uri)
    except ValueError:
        bucket, key = ref.campaign_id, ref.uri
    try:
        open_pinned(transport, bucket, key, budget or ReadBudget())
    except SourceReadError as exc:
        return ReadOutcome(exc.state, exc.detail)
    return ReadOutcome(STATE_AVAILABLE)
