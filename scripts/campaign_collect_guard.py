#!/usr/bin/env python3
"""Key allowlist + byte ceilings for the campaign_collect workflow.

Shared by the workflow's fetch steps and the offline regression tests so
the enforced contract lives in one place:

- legacy ``exact_key`` fetches stay confined to ``campaign/`` (any key),
  unchanged behavior.
- ``derived_key``/``derived_manifest`` fetch only under
  ``campaign/_derived/reducer/v1/`` with per-kind ceilings from
  CANONICAL_INTERFACE.readback: pages 5 MiB, indexes/manifests 1 MiB,
  receipts 256 KiB, issue envelopes 32 KiB. A collect pass fetches at
  most 20 objects / 50 MiB total.
"""
from __future__ import annotations

import json
import sys

DERIVED_ROOT = "campaign/_derived/reducer/v1/"
LEGACY_ROOT = "campaign/"

CEILING_PAGE = 5 * 1024 * 1024
CEILING_INDEX = 1024 * 1024
CEILING_RECEIPT = 256 * 1024
CEILING_ENVELOPE = 32 * 1024
MAX_COLLECT_OBJECTS = 20
MAX_COLLECT_BYTES = 50 * 1024 * 1024


def _clean(key: str) -> str:
    key = key.strip()
    if ".." in key.split("/") or key.endswith("/") or not key:
        raise ValueError(f"malformed key: {key!r}")
    return key


def validate_legacy_key(key: str) -> None:
    """Legacy exact_key rule: any single object under ``campaign/``."""
    key = _clean(key)
    if not key.startswith(LEGACY_ROOT):
        raise ValueError(f"key outside {LEGACY_ROOT}: {key!r}")


def classify_derived_key(key: str) -> tuple[str, int]:
    """``(kind, ceiling_bytes)`` for an allowlisted derived object."""
    key = _clean(key)
    if not key.startswith(DERIVED_ROOT):
        raise ValueError(f"key outside {DERIVED_ROOT}: {key!r}")
    leaf = key.rsplit("/", 1)[-1]
    if "envelope" in leaf:
        return "issue_envelope", CEILING_ENVELOPE
    if leaf.startswith("COMMIT") or "receipt" in leaf:
        return "receipt", CEILING_RECEIPT
    if "/pages/" in key or leaf.startswith("page-"):
        return "page", CEILING_PAGE
    return "index", CEILING_INDEX


def validate_manifest_key(key: str) -> None:
    """A derived manifest/index document (1 MiB ceiling)."""
    kind, _ = classify_derived_key(key)
    if kind == "page":
        raise ValueError(f"manifest key points at a page object: {key!r}")


def iter_manifest_keys(doc: dict) -> list[str]:
    """Derived object keys listed by a manifest document.

    Accepts ``entries[].uri``/``key`` and ``pages[].uri``/``key``; every
    listed key must resolve under the derived root or the pass refuses.
    """
    keys: list[str] = []
    for entry in (doc.get("entries") or []) + (doc.get("pages") or []):
        uri = entry.get("uri") or entry.get("key") or ""
        key = uri.split("/", 3)[-1] if uri.startswith("s3://") else uri
        classify_derived_key(key)  # raises unless allowlisted
        keys.append(key)
    return keys


def main(argv: list[str]) -> int:
    cmd = argv[0]
    if cmd == "legacy":
        validate_legacy_key(argv[1])
        return 0
    if cmd == "derived-ceiling":
        kind, ceiling = classify_derived_key(argv[1])
        print(f"{kind} {ceiling}")
        return 0
    if cmd == "manifest-keys":
        doc = json.loads(open(argv[1], encoding="utf-8").read())
        for key in iter_manifest_keys(doc):
            print(key)
        return 0
    raise SystemExit(f"unknown guard op {cmd!r}")


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except ValueError as exc:
        raise SystemExit(f"guard refused: {exc}")
