"""Source/run identity helpers for the campaign reducer (ticket D1).

Identity rules from ``docs/campaign_reduction/SURVEY_AND_DEVIN_SPEC.md``:

- ``object_id`` pins (bucket, key, VersionId-or-ETag) — never a basename and
  never a listing row alone.
- Object-level bytes and member-level decoded bytes are **different hash
  scopes** (``assets.hash_scope``: ``container_bytes`` vs
  ``uncompressed_member``); a container hash is never presented as a member
  hash or vice versa.
- ``run_uid`` composes campaign/attempt/vessel/cell/engine/seed so the *same
  numeric seed* in different hulls, cells, engines or attempts can never
  collide; ``original_run_id`` is preserved unmodified alongside.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

_HASH_LEN = 40


def sha256_hex(data: bytes) -> str:
    """Full hex SHA-256 of ``data``."""
    return hashlib.sha256(data).hexdigest()


def _pin_digest(*parts: str) -> str:
    return sha256_hex("\x00".join(parts).encode("utf-8"))[:_HASH_LEN]


def object_id(
    bucket: str,
    key: str,
    version_id: str | None,
    etag: str | None,
) -> str:
    """Physical-object identity: hash of bucket/key and pin identity.

    ``version_id`` and ``etag`` are alternative pins; a non-null VersionId is
    the immutable pin, otherwise the opaque ETag identities the observed
    bytes. Literal ``"null"`` VersionIds are *not* treated as immutable.
    """
    version = "" if version_id in (None, "", "null") else str(version_id)
    return "obj-" + _pin_digest(
        str(bucket), str(key), version, str(etag or ""),
    )


def member_asset_id(object_identity: str, member_path: str) -> str:
    """Logical member identity inside one pinned container object."""
    return "mem-" + _pin_digest(object_identity, member_path)


def sidecar_asset_id(object_identity: str) -> str:
    """Identity for a non-ZIP standalone payload object."""
    return "asset-" + _pin_digest(object_identity, "whole-object")


def run_uid(
    *,
    campaign_id: str,
    attempt_id: str,
    vessel_id: str | None,
    case_id: str,
    engine_sha: str | None,
    image_digest: str | None,
    seed: int | str | None,
    original_run_id: str,
) -> str:
    """Globally unique execution identity.

    The composite keys on (campaign, attempt, vessel, cell, engine image,
    seed, emitted id): identical seeds under different hull/cell/engine/
    attempts produce different ``run_uid`` values, and two executions that
    merely share a filename stay distinct.
    """
    components = (
        str(campaign_id),
        str(attempt_id),
        str(vessel_id or "unresolved"),
        str(case_id),
        str(engine_sha or "unknown-engine"),
        str(image_digest or "unknown-image"),
        str(seed if seed is not None else "unknown-seed"),
        str(original_run_id),
    )
    return "run-" + _pin_digest(*components)


def case_id(*coordinates: Any) -> str:
    """Design-cell + replicate identity independent of retry packaging."""
    return "cell-" + _pin_digest(*(str(part) for part in coordinates))


@dataclass(frozen=True)
class HashEvidence:
    """A content hash with its declared scope (never conflated)."""

    sha256: str
    hash_scope: str  # "container_bytes" | "uncompressed_member" | "file_bytes"

    def as_json(self) -> dict[str, str]:
        return {"sha256": self.sha256, "hash_scope": self.hash_scope}
