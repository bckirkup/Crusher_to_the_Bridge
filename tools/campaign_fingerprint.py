#!/usr/bin/env python3
"""Validate and fingerprint a publication campaign provenance envelope."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from simulation_utils.paths import confine_to_base, validated_open

EXCLUDED_FROM_FINGERPRINT = {"outputs", "run_fingerprint"}


def canonical_fingerprint(manifest: dict[str, Any]) -> str:
    """Return the SHA-256 of the pre-run envelope, excluding outputs."""
    payload = {
        key: copy.deepcopy(value)
        for key, value in manifest.items()
        if key not in EXCLUDED_FROM_FINGERPRINT
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _safe_read_text(path: Path, *, base_dir: str | None = None) -> str:
    """Read UTF-8 text after confining *path* under *base_dir* (default: cwd)."""
    root = os.path.realpath(base_dir or os.getcwd())
    resolved = confine_to_base(root, str(path))
    with validated_open(resolved, allowed_roots=(root,), encoding="utf-8") as handle:
        return handle.read()


def validate(manifest: dict[str, Any], schema_path: Path) -> None:
    """Validate *manifest* against the JSON Schema at *schema_path*."""
    try:
        import jsonschema
    except ImportError as exc:
        raise SystemExit("jsonschema is required for --validate") from exc
    schema = json.loads(_safe_read_text(schema_path))
    jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    ).validate(manifest)


def main() -> int:
    """CLI entry: fingerprint a provenance envelope, optionally validating it."""
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("schemas/publication_campaign_provenance.schema.json"),
    )
    parser.add_argument("--validate", action="store_true")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="require run_fingerprint to match",
    )
    args = parser.parse_args()
    manifest = json.loads(_safe_read_text(args.manifest))
    if args.validate:
        validate(manifest, args.schema)
    fingerprint = canonical_fingerprint(manifest)
    if args.verify and manifest.get("run_fingerprint") != fingerprint:
        print(
            f"fingerprint mismatch: expected {fingerprint}, "
            f"found {manifest.get('run_fingerprint')}"
        )
        return 2
    print(fingerprint)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
