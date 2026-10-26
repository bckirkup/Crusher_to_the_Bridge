"""D1 record payloads — the reducer's pre-materialization row types.

These are the adapter outputs D2 materializes later. Every field that a
scan row, member, or decoded payload preserves lands here with its native
lexical token intact — ``0``, ``false`` and ``null`` stay distinct, and an
absent field stays absent rather than becoming a default.

``native_path`` is the JSON Pointer of the field in its source document;
``native_value_json`` is its serialized JSON token (e.g. ``"0"``,
``"false"``, ``"null"``); ``native_type`` is the JSON type name.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .pinned_reader import canonical_source_read_state


def json_pointer(*parts: str) -> str:
    """A JSON Pointer (RFC 6901) for a field path."""
    escaped = [
        p.replace("~", "~0").replace("/", "~1") for p in parts if p != ""
    ]
    return "/" + "/".join(escaped)


def native_token(value: Any) -> tuple[str, str]:
    """The canonical lexical JSON token and type name for a scalar value."""
    if value is None:
        return "null", "null"
    if value is True:
        return "true", "boolean"
    if value is False:
        return "false", "boolean"
    if isinstance(value, (int, float)):
        return json.dumps(value), "number"
    if isinstance(value, str):
        return json.dumps(value), "string"
    if isinstance(value, list):
        return json.dumps(value, sort_keys=True, separators=(",", ":")), "array"
    return json.dumps(value, sort_keys=True, separators=(",", ":")), "object"


@dataclass(frozen=True)
class AssetRecord:
    """An ``assets`` row: one readable unit inside or beside a source."""

    asset_id: str
    source_id: str
    asset_path: str
    read_state: str  # assets.read_state literal
    hash_scope: str  # assets.hash_scope literal
    sha256: str | None = None
    detail: str = ""

    def as_json(self) -> dict:
        return {
            "asset_id": self.asset_id,
            "source_id": self.source_id,
            "asset_path": self.asset_path,
            "read_state": self.read_state,
            "hash_scope": self.hash_scope,
            "sha256": self.sha256,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class ScalarRecord:
    """One scalar telemetry field preserved losslessly from a source row."""

    run_uid: str
    metric_id: str
    native_path: str
    native_value_json: str
    native_type: str
    value_status: str  # metrics.value_status literal
    value: float | int | bool | str | None = None
    asset_id: str | None = None

    def as_json(self) -> dict:
        return {
            "run_uid": self.run_uid,
            "metric_id": self.metric_id,
            "native_path": self.native_path,
            "native_value_json": self.native_value_json,
            "native_type": self.native_type,
            "value_status": self.value_status,
            "value": self.value,
            "asset_id": self.asset_id,
        }


@dataclass(frozen=True)
class RunRecord:
    """A ``runs`` row — identity is the reducer's, provenance is the scan's."""

    run_uid: str
    campaign_id: str
    selection_state: str  # runs.selection_state literal
    seed: int | None
    original_run_id: str | None
    hull_id: str | None = None
    cell_id: str | None = None
    engine_sha: str | None = None
    image_digest: str | None = None
    detail: str = ""

    def as_json(self) -> dict:
        return {
            "run_uid": self.run_uid,
            "campaign_id": self.campaign_id,
            "selection_state": self.selection_state,
            "seed": self.seed,
            "original_run_id": self.original_run_id,
            "hull_id": self.hull_id,
            "cell_id": self.cell_id,
            "engine_sha": self.engine_sha,
            "image_digest": self.image_digest,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class CapabilityRecord:
    """A ``capabilities`` row: what one family/axis can support."""

    family: str
    axis: str
    availability: str  # capabilities.availability literal
    telemetry_fields: list[str] = field(default_factory=list)
    evidence: str = ""

    def as_json(self) -> dict:
        return {
            "family": self.family,
            "axis": self.axis,
            "availability": self.availability,
            "telemetry_fields": list(self.telemetry_fields),
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class GapRecord:
    """A ``data_gaps`` row — a typed coverage hole with its reason."""

    gap_id: str
    source_id: str
    reason: str  # data_gaps.reason literal
    detail: str = ""
    member: str | None = None
    asset_id: str | None = None

    def as_json(self) -> dict:
        return {
            "gap_id": self.gap_id,
            "source_id": self.source_id,
            "reason": self.reason,
            "detail": self.detail,
            "member": self.member,
            "asset_id": self.asset_id,
        }


@dataclass(frozen=True)
class LinkRecord:
    """A ``source_objects`` row: HEAD pin evidence plus read outcome."""

    source_id: str
    uri: str
    read_state: str  # contract literal via canonical_source_read_state
    pin_kind: str
    version_id: str | None = None
    etag: str | None = None
    content_length: int | None = None
    storage_class: str | None = None
    last_modified: str | None = None
    sha256: str | None = None
    detail: str = ""
    internal_state: str = ""

    def as_json(self) -> dict:
        return {
            "source_id": self.source_id,
            "uri": self.uri,
            "read_state": self.read_state,
            "pin_kind": self.pin_kind,
            "version_id": self.version_id,
            "etag": self.etag,
            "content_length": self.content_length,
            "storage_class": self.storage_class,
            "last_modified": self.last_modified,
            "sha256": self.sha256,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class DecodedDoc:
    """One decoded document retained for long-table extraction (D2).

    ``member_path`` identifies the archive member (or ``None`` for a
    whole-object document); ``doc`` is the parsed JSON. Bounded by the
    same decoded-bytes budget the adapter already charges.
    """

    run_uid: str
    asset_id: str | None
    member_path: str | None
    doc: object


@dataclass
class AdapterResult:
    """Everything one family adapter produced from its source objects."""

    family: str
    links: list[LinkRecord] = field(default_factory=list)
    assets: list[AssetRecord] = field(default_factory=list)
    scalars: list[ScalarRecord] = field(default_factory=list)
    runs: list[RunRecord] = field(default_factory=list)
    gaps: list[GapRecord] = field(default_factory=list)
    docs: list[DecodedDoc] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        return {
            "links": len(self.links),
            "assets": len(self.assets),
            "scalars": len(self.scalars),
            "runs": len(self.runs),
            "gaps": len(self.gaps),
        }


def link_for(
    source_id: str,
    uri: str,
    obj,
    read_state: str,
    detail: str = "",
    sha256: str | None = None,
) -> LinkRecord:
    """A ``source_objects`` row from pin evidence + a read outcome.

    ``obj`` is the ``PinnedObject`` (or ``None`` when HEAD itself failed, in
    which case pin fields default to empty/unpinned evidence).
    """
    if obj is None:
        return LinkRecord(
            source_id=source_id,
            uri=uri,
            read_state=canonical_source_read_state(read_state),
            internal_state=read_state,
            pin_kind="unpinned_blocked",
            sha256=sha256,
            detail=detail,
        )
    return LinkRecord(
        source_id=source_id,
        uri=uri,
        read_state=canonical_source_read_state(read_state),
        internal_state=read_state,
        pin_kind=obj.pin.kind,
        version_id=obj.pin.version_id,
        etag=obj.pin.etag,
        content_length=obj.head.content_length,
        storage_class=obj.head.storage_class,
        last_modified=obj.head.last_modified,
        sha256=sha256,
        detail=detail,
    )
