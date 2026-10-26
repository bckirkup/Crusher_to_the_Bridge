"""Bounded Edison ingest leg for the return canary (ticket D4).

Reads a ``durable_ingestion_request.json`` produced by
``scripts/campaign analysis collect``, sha256-verifies every declared
file against the collected bytes, and uploads each with
``edison_client.astore_file_content`` — the bounded-file bridge Edison
Scientific reads on its own side (it never gets raw S3).

Typed failure, never a workaround: when the connector package or the
``EDISON_PLATFORM_API_KEY`` environment variable is absent this emits an
``ingestion_receipt.json`` whose status is ``return_blocked`` with
``error_owner: edison_connector``, a bounded-retry hint and the S3
pointer — it never prompts for a secret and never relays file bytes
through logs, issues or chat (acceptance P19).

CLI::

    python3 -m picard_framework.analysis.campaign_reducer.edison_ingest \
        --manifest <durable_ingestion_request.json> --out <dir>

Exit codes follow the canonical table: 0 complete, 2 invalid contract,
3 blocked, 7 hash quarantine, 9 return path blocked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from typing import Any

from simulation_utils.paths import (
    confine_to_base,
    prepare_output_directory,
    validated_open,
)

from .._io import allowed_roots, cwd_root, read_json, write_json
from . import contracts

_API_KEY_ENV = "EDISON_PLATFORM_API_KEY"


def _out_root(out_dir: str) -> str:
    safe = confine_to_base(cwd_root(), out_dir)
    return prepare_output_directory(safe, allowed_roots=(cwd_root(),))


def _connector():
    """Return (module, blocked_reason); the key itself never leaves env."""
    if not os.environ.get(_API_KEY_ENV):
        return None, "missing_api_key"
    try:
        import edison_client  # noqa: PLC0415
    except ImportError:
        return None, "connector_unavailable"
    return edison_client, None


def _upload(module, path: str, meta: dict) -> Any:
    """Upload seam — tests substitute a fake module; live code calls the
    edison-client bounded-file API."""
    return module.astore_file_content(path=path, metadata=meta)


def _asset_id(result: Any) -> str:
    if isinstance(result, dict):
        return str(result.get("asset_id") or result.get("id") or result)
    return str(result)


def _read_bounded(path: str, cap: int) -> bytes:
    try:
        resolved = confine_to_base(cwd_root(), path)
    except ValueError as exc:
        raise _Failure("invalid_contract", str(exc), 2) from exc
    try:
        with validated_open(resolved, "rb", allowed_roots=allowed_roots()) as fh:
            body = fh.read()
    except OSError as exc:
        raise _Failure("not_found", f"{path}: {exc}", 3) from exc
    if len(body) > cap:
        raise _Failure(
            "budget_exceeded", f"{path}: {len(body)}B exceeds {cap}B cap", 9,
        )
    return body


class _Failure(Exception):
    def __init__(self, kind: str, detail: str, exit_code: int) -> None:
        super().__init__(f"{kind}: {detail}")
        self.kind = kind
        self.detail = detail
        self.exit_code = exit_code
        self.status = (
            "quarantined" if kind == "hash_mismatch"
            else "blocked" if exit_code in (2, 3)
            else "return_blocked"
        )


def _verified_files(manifest: dict, base: str, cap: int) -> list[dict]:
    """Resolve + sha256-verify every declared file; quarantine on mismatch."""
    verified = []
    for entry in manifest.get("files") or []:
        path = entry.get("path")
        if not isinstance(path, str) or not path:
            raise _Failure("invalid_contract", f"file entry missing path: {entry!r}", 2)
        resolved = confine_to_base(cwd_root(), os.path.join(base, path))
        body = _read_bounded(resolved, cap)
        want = entry.get("sha256")
        got = hashlib.sha256(body).hexdigest()
        if want and want != got:
            raise _Failure(
                "hash_mismatch",
                f"{path}: sha256 {got} != declared {want}", 7,
            )
        verified.append({**entry, "resolved": resolved})
    return verified


def ingest(manifest_path: str, out_dir: str) -> int:
    """Run the ingest leg; write ``ingestion_receipt.json`` to out_dir."""
    out_root = _out_root(out_dir)
    try:
        manifest = read_json(manifest_path)
        if not isinstance(manifest, dict):
            raise _Failure("invalid_contract", "manifest is not a JSON object", 2)
        cap = int(
            manifest.get("max_file_bytes")
            or contracts.load(contracts.CANONICAL_INTERFACE)["readback"][
                "proposed_hard_caps"
            ]["total_bytes_per_collect"]
        )
        files = _verified_files(
            manifest, os.path.dirname(manifest_path) or ".", cap,
        )
        module, reason = _connector()
        if reason is not None:
            receipt = _blocked_receipt(manifest, reason, len(files))
            write_json(os.path.join(out_root, "ingestion_receipt.json"), receipt)
            print(json.dumps(receipt))
            return contracts.EXIT_RETURN_PATH_BLOCKED
        assets = []
        for entry in files:
            result = _upload(
                module,
                entry["resolved"],
                {
                    "request_id": manifest.get("request_id"),
                    "reduction_id": manifest.get("reduction_id"),
                    "kind": entry.get("kind"),
                    "sha256": entry.get("sha256"),
                },
            )
            assets.append(_asset_id(result))
        receipt = {
            "status": "completed",
            "project_asset_ids": assets,
            "files_uploaded": len(files),
            "request_id": manifest.get("request_id"),
            "reduction_id": manifest.get("reduction_id"),
            "s3_pointer": manifest.get("s3_pointer"),
        }
        write_json(os.path.join(out_root, "ingestion_receipt.json"), receipt)
        print(json.dumps(receipt))
        return contracts.EXIT_COMPLETE
    except _Failure as exc:
        receipt = {
            "status": exc.status,
            "error": {"kind": exc.kind, "detail": exc.detail,
                      "owner": "edison_connector"},
        }
        write_json(os.path.join(out_root, "ingestion_receipt.json"), receipt)
        print(json.dumps(receipt))
        return exc.exit_code


def _blocked_receipt(manifest: dict, reason: str, n_files: int) -> dict:
    return {
        "status": "return_blocked",
        "error_owner": "edison_connector",
        "reason": reason,
        "bounded_retry": {"max_retries": 3, "backoff": "cursor"},
        "s3_pointer": manifest.get("s3_pointer"),
        "files_pending": n_files,
        "request_id": manifest.get("request_id"),
        "note": (
            "typed blocked — no secret prompt, no file relay; the "
            "collected artifacts remain fetchable at s3_pointer"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="campaign_reducer.edison_ingest")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    return ingest(args.manifest, args.out)


if __name__ == "__main__":
    sys.exit(main())
