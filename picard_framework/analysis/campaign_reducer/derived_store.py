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


class LocalDirStore:
    """Filesystem create-only store rooted at a local directory."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        rel = key.lstrip("/")
        path = (self.root / rel).resolve()
        if self.root.resolve() not in path.parents and path != self.root.resolve():
            raise DerivedStoreError("denied", f"{key} escapes store root")
        return path

    def put_if_absent(self, key: str, body: bytes) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        try:
            fd = os.open(path, flags, 0o644)
        except FileExistsError:
            raise DerivedConflict(
                key, _sha(path.read_bytes()), _sha(body)
            ) from None
        with os.fdopen(fd, "wb") as fh:
            fh.write(body)
        return _sha(body)

    def put_idempotent(self, key: str, body: bytes) -> bool:
        path = self._path(key)
        if path.exists():
            if _sha(path.read_bytes()) == _sha(body):
                return False
            raise DerivedConflict(key, _sha(path.read_bytes()), _sha(body))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        return True

    def get(self, key: str) -> bytes:
        path = self._path(key)
        if not path.exists():
            raise DerivedStoreError("not_found", key)
        return path.read_bytes()

    def head(self, key: str) -> dict | None:
        path = self._path(key)
        if not path.exists():
            return None
        body = path.read_bytes()
        return {"key": key, "bytes": len(body), "sha256": _sha(body)}

    def list(self, prefix: str = "") -> list[str]:
        base = self._path(prefix or ".")
        if not base.exists():
            return []
        out: list[str] = []
        for path in sorted(self.root.rglob("*")):
            if path.is_file():
                rel = path.relative_to(self.root).as_posix()
                if rel.startswith(prefix):
                    out.append(rel)
        return out


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
