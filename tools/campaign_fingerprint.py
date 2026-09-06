#!/usr/bin/env python3
"""Validate and fingerprint a publication campaign provenance envelope."""
from __future__ import annotations
import argparse, copy, hashlib, json
from pathlib import Path
from typing import Any
EXCLUDED_FROM_FINGERPRINT = {"outputs", "run_fingerprint"}
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas/publication_campaign_provenance.schema.json"
def canonical_fingerprint(manifest: dict[str, Any]) -> str:
    payload = {k: copy.deepcopy(v) for k, v in manifest.items() if k not in EXCLUDED_FROM_FINGERPRINT}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
def confined_manifest_path(path: Path, root: Path | None = None) -> Path:
    boundary = (root or Path.cwd()).resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(boundary)
    except ValueError as exc:
        raise SystemExit(f"manifest must remain under {boundary}: {resolved}") from exc
    if not resolved.is_file():
        raise SystemExit(f"manifest is not a file: {resolved}")
    return resolved
def validate(manifest: dict[str, Any]) -> None:
    try:
        import jsonschema
    except ImportError as exc:
        raise SystemExit("jsonschema is required for --validate") from exc
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(manifest)
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--verify", action="store_true", help="require run_fingerprint to match")
    args = parser.parse_args(argv)
    manifest_path = confined_manifest_path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if args.validate: validate(manifest)
    fingerprint = canonical_fingerprint(manifest)
    if args.verify and manifest.get("run_fingerprint") != fingerprint:
        print(f"fingerprint mismatch: expected {fingerprint}, found {manifest.get('run_fingerprint')}")
        return 2
    print(fingerprint)
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
