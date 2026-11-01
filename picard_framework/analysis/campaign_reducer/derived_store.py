"""Create-only derived-output store for the campaign reducer (ticket D2).

Derived outputs under ``campaign/_derived/reducer/v1/`` are immutable:
the publication rule in ``CANONICAL_INTERFACE.json`` is a create-if-absent
put, never an overwrite. ``put_idempotent`` therefore accepts two cases
only — the object was absent (created) or it already exists with byte-
identical content (a deterministic re-derivation after a kill/resume).
Any third case is a conflicting overwrite and raises
:class:`DerivedConflict` instead of silently replacing immutable bytes.

Two implementations are provided, both offline:

- :class:`MemoryDerivedStore` — dict-backed fake for unit tests, with
  injectable failures mirroring ``MemoryTransport``.
- :class:`LocalDirStore` — a directory on the local filesystem, so the
  CLI path and human inspection see real files; puts are create-only via
  ``O_EXCL``.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from simulation_utils.paths import exclusive_create, resolve_under_base, validated_open


def _sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


class DerivedConflict(Exception):
    """An output key already exists with different bytes."""

    def __init__(self, key: str, existing_sha: str, incoming_sha: str):
        super().__init__(
            f"{key}: existing {existing_sha[:16]} != incoming {incoming_sha[:16]}"
        )
        self.key = key
        self.existing_sha = existing_sha
        self.incoming_sha = incoming_sha


class DerivedStoreError(Exception):
    """Typed derived-store failure (denied / closed / injected)."""

    def __init__(self, kind: str, detail: str):
        super().__init__(f"{kind}: {detail}")
        self.kind = kind
        self.detail = detail


class MemoryDerivedStore:
    """In-memory create-only store; mirrors ``MemoryTransport`` style."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.writes: list[str] = []
        self.reads: list[str] = []
        self._fail_kinds: set[str] = set()
        self.closed = False

    # -- test fakes -----------------------------------------------------
    def fail(self, kind: str) -> None:
        """Inject a failure kind: ``denied`` or ``closed``."""
        self._fail_kinds.add(kind)

    def clear_failures(self) -> None:
        self._fail_kinds.clear()

    def _check(self) -> None:
        if self.closed or "closed" in self._fail_kinds:
            raise DerivedStoreError("closed", "store closed")
        if "denied" in self._fail_kinds:
            raise DerivedStoreError("denied", "access denied")

    # -- store protocol -------------------------------------------------
    def put_if_absent(self, key: str, body: bytes) -> str:
        """Create-only put; returns the body sha256."""
        self._check()
        existing = self.objects.get(key)
        if existing is not None:
            raise DerivedConflict(key, _sha(existing), _sha(body))
        self.objects[key] = body
        self.writes.append(key)
        return _sha(body)

    def put_idempotent(self, key: str, body: bytes) -> bool:
        """Create-only put tolerant of identical bytes.

        Returns True when the write happened, False when the key already
        held byte-identical content (a deterministic resume). A key with
        different content raises :class:`DerivedConflict` — a conflicting
        overwrite is never performed.
        """
        self._check()
        existing = self.objects.get(key)
        if existing is not None:
            if _sha(existing) == _sha(body):
                return False
            raise DerivedConflict(key, _sha(existing), _sha(body))
        self.objects[key] = body
        self.writes.append(key)
        return True

    def get(self, key: str) -> bytes:
        self._check()
        self.reads.append(key)
        body = self.objects.get(key)
        if body is None:
            raise DerivedStoreError("not_found", key)
        return body

    def head(self, key: str) -> dict | None:
        self._check()
        body = self.objects.get(key)
        if body is None:
            return None
        return {"key": key, "bytes": len(body), "sha256": _sha(body)}

    def list(self, prefix: str = "") -> list[str]:
        self._check()
        return sorted(k for k in self.objects if k.startswith(prefix))


def _files_under(root: str, prefix: str) -> list[str]:
    """Return slash-separated file keys under *root* that start with *prefix*."""
    out: list[str] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if rel.startswith(prefix):
                out.append(rel)
    return sorted(out)


class LocalDirStore:
    """Filesystem create-only store rooted at a local directory.

    Keys are relative paths. ``_path`` returns the canonical path
    :func:`resolve_under_base` already contained, and every read or
    write uses that string rather than the caller's key.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _roots(self) -> tuple[str, ...]:
        return (os.path.realpath(os.fspath(self.root)),)

    def _path(self, key: str) -> str:
        try:
            return resolve_under_base(os.fspath(self.root), key)
        except ValueError as exc:
            raise DerivedStoreError("denied", str(exc)) from exc

    def _read(self, path: str) -> bytes:
        with validated_open(path, "rb", allowed_roots=self._roots()) as fh:
            return fh.read()

    def _same_bytes_or_conflict(self, key: str, path: str, body: bytes) -> bool:
        """Return False when *path* already holds *body*; else raise."""
        existing = self._read(path)
        if _sha(existing) == _sha(body):
            return False
        raise DerivedConflict(key, _sha(existing), _sha(body))

    def put_if_absent(self, key: str, body: bytes) -> str:
        path = self._path(key)
        try:
            exclusive_create(path, body, allowed_roots=self._roots())
        except FileExistsError:
            raise DerivedConflict(
                key, _sha(self._read(path)), _sha(body)
            ) from None
        return _sha(body)

    def put_idempotent(self, key: str, body: bytes) -> bool:
        path = self._path(key)
        if os.path.exists(path):
            return self._same_bytes_or_conflict(key, path, body)
        try:
            exclusive_create(path, body, allowed_roots=self._roots())
        except FileExistsError:
            return self._same_bytes_or_conflict(key, path, body)
        return True

    def get(self, key: str) -> bytes:
        path = self._path(key)
        if not os.path.exists(path):
            raise DerivedStoreError("not_found", key)
        return self._read(path)

    def head(self, key: str) -> dict | None:
        path = self._path(key)
        if not os.path.exists(path):
            return None
        body = self._read(path)
        return {"key": key, "bytes": len(body), "sha256": _sha(body)}

    def list(self, prefix: str = "") -> list[str]:
        root = os.path.realpath(os.fspath(self.root))
        if prefix not in {"", "."} and not os.path.exists(self._path(prefix)):
            return []
        if not os.path.isdir(root):
            return []
        return _files_under(root, prefix)


def write_manifest(store, key: str, entries: list[dict]) -> dict:
    """Write a sha-manifest of immutable entries, excluding itself.

    The release-manifest invariant (P26): the manifest lists every
    partition/checkpoint artifact with its sha256 but never references
    itself. Returns the manifest doc written at ``key``.
    """
    import json

    doc = {
        "manifest_id": f"manifest-{hashlib.sha256(key.encode()).hexdigest()[:16]}",
        "entries": [
            {
                "uri": e["uri"],
                "sha256": e["sha256"],
                "bytes_stored": e["bytes_stored"],
            }
            for e in sorted(entries, key=lambda x: x["uri"])
        ],
    }
    store.put_idempotent(
        key, json.dumps(doc, sort_keys=True, indent=2).encode()
    )
    return doc
