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
REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schemas/publication_campaign_provenance.schema.json"


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


def _read_text_under(root: Path, path: Path) -> str:
    """Read UTF-8 text after confining *path* under *root*."""
    base = os.path.realpath(root)
    resolved = confine_to_base(base, str(path))
    with validated_open(resolved, allowed_roots=(base,), encoding="utf-8") as handle:
        return handle.read()


def confined_manifest_path(path: Path, root: Path | None = None) -> Path:
    """Resolve *path* and require it to remain under the working directory."""
    boundary = (root or Path.cwd()).resolve()
    try:
        resolved = Path(confine_to_base(str(boundary), str(path)))
    except ValueError as exc:
        raise SystemExit(f"manifest must remain under {boundary}: {path}") from exc
    if not resolved.is_file():
        raise SystemExit(f"manifest is not a file: {resolved}")
    return resolved


def validate(manifest: dict[str, Any]) -> None:
    """Validate *manifest* against the repository-owned provenance schema."""
    try:
        import jsonschema
    except ImportError as exc:
        raise SystemExit("jsonschema is required for --validate") from exc
    schema = json.loads(_read_text_under(REPO_ROOT, SCHEMA_PATH))
    jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    ).validate(manifest)


def main(argv: list[str] | None = None) -> int:
    """CLI entry: fingerprint a provenance envelope, optionally validating it."""
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="require run_fingerprint to match",
    )
    args = parser.parse_args(argv)
    manifest_path = confined_manifest_path(args.manifest)
    manifest = json.loads(_read_text_under(Path.cwd(), manifest_path))
    if args.validate:
        validate(manifest)
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
