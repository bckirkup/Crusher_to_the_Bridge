#!/usr/bin/env python3
"""Validate and fingerprint a publication campaign provenance envelope."""
from __future__ import annotations
import argparse, copy, hashlib, json
from pathlib import Path
from typing import Any
EXCLUDED_FROM_FINGERPRINT = {"outputs", "run_fingerprint"}
def canonical_fingerprint(manifest: dict[str, Any]) -> str:
    payload = {k: copy.deepcopy(v) for k, v in manifest.items() if k not in EXCLUDED_FROM_FINGERPRINT}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
def validate(manifest: dict[str, Any], schema_path: Path) -> None:
    try:
        import jsonschema
    except ImportError as exc:
        raise SystemExit("jsonschema is required for --validate") from exc
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(manifest)
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--schema", type=Path, default=Path("schemas/publication_campaign_provenance.schema.json"))
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--verify", action="store_true", help="require run_fingerprint to match")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if args.validate: validate(manifest, args.schema)
    fingerprint = canonical_fingerprint(manifest)
    if args.verify and manifest.get("run_fingerprint") != fingerprint:
        print(f"fingerprint mismatch: expected {fingerprint}, found {manifest.get('run_fingerprint')}")
        return 2
    print(fingerprint)
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
