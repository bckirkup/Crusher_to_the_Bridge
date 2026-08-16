#!/usr/bin/env python3
"""AWS Batch worker for one Sentinel Engine C NUTS ladder cell.

Each array child resolves its ``AWS_BATCH_JOB_ARRAY_INDEX`` against the
deterministic cell enumeration, runs one CmdStan fit, and writes one JSON
object under the caller-provided S3 prefix.  The container uses only its
ambient Batch job-role credentials.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from picard_framework.analysis._io import write_json  # noqa: E402
from picard_framework.analysis.sentinel.design_nuts import (  # noqa: E402
    enumerate_cells,
    load_ladder,
    run_cell,
)
from simulation_utils.paths import validate_path_component  # noqa: E402

_BUCKET_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789.-")
_KEY_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._/-")


def _s3_uri(raw: str) -> tuple[str, str]:
    parsed = urlparse(raw)
    bucket = parsed.netloc
    key = parsed.path.lstrip("/")
    if parsed.scheme != "s3" or not bucket or any(char not in _BUCKET_CHARS for char in bucket):
        raise SystemExit(f"Invalid S3 URI: {raw!r}")
    if any(char not in _KEY_CHARS for char in key):
        raise SystemExit(f"Invalid S3 key: {key!r}")
    return bucket, key.rstrip("/")


def _s3_client() -> Any:
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("boto3 is required in the Batch image") from exc
    return boto3.client("s3")


def _selected_cells(rung_ids: str | None) -> list[dict[str, Any]]:
    cells = enumerate_cells(load_ladder())
    if not rung_ids:
        return cells
    selected = {validate_path_component(value.strip(), label="rung") for value in rung_ids.split(",")}
    return [cell for cell in cells if cell["rung"] in selected]


def _cell_key(cell: dict[str, Any]) -> str:
    ratio = str(cell["ratio"]).replace(".", "p")
    return f"cell_{cell['rung']}_ratio_{ratio}_rep_{cell['replicate']}.json"


def _put_json(client: Any, bucket: str, key: str, payload: Any) -> None:
    with tempfile.TemporaryDirectory(prefix="sentinel-nuts-") as work:
        path = Path(work) / "payload.json"
        write_json(str(path), payload)
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=path.read_bytes(),
            ContentType="application/json",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rungs", default=None, help="Comma-separated rung ids to enumerate")
    parser.add_argument("--s3-prefix", required=True, help="s3://bucket/sentinel/nuts_ladder_v1/")
    args = parser.parse_args()

    cells = _selected_cells(args.rungs)
    index_raw = os.environ.get("AWS_BATCH_JOB_ARRAY_INDEX")
    if index_raw is None:
        raise SystemExit("AWS_BATCH_JOB_ARRAY_INDEX is required")
    try:
        index = int(index_raw)
    except ValueError as exc:
        raise SystemExit("AWS_BATCH_JOB_ARRAY_INDEX must be an integer") from exc
    if index < 0 or index >= len(cells):
        raise SystemExit(f"Array index {index} outside selected cell range 0..{len(cells) - 1}")

    bucket, prefix = _s3_uri(args.s3_prefix)
    if prefix:
        prefix += "/"
    client = _s3_client()
    cell = cells[index]
    key = f"{prefix}cells/{_cell_key(cell)}"
    manifest_key = f"{prefix}cells_manifest.json"
    missing = False
    try:
        client.head_object(Bucket=bucket, Key=key)
        print(f"Already complete: s3://{bucket}/{key}", flush=True)
        return 0
    except client.exceptions.NoSuchKey:
        # A missing object is the normal first-attempt path.
        missing = True
    except Exception as exc:
        if getattr(exc, "response", {}).get("ResponseMetadata", {}).get("HTTPStatusCode") != 404:
            raise
        missing = True
    if not missing:
        raise RuntimeError(f"Could not establish idempotence for s3://{bucket}/{key}")

    manifest = {
        "engine": "nuts_cell_manifest",
        "rung_ids": args.rungs.split(",") if args.rungs else None,
        "array_size": len(cells),
        "cells": cells,
    }
    _put_json(client, bucket, manifest_key, manifest)
    payload = run_cell(
        load_ladder(),
        rung_id=str(cell["rung"]),
        ratio=float(cell["ratio"]),
        replicate=int(cell["replicate"]),
        seed=int(cell["seed"]),
    )
    _put_json(client, bucket, key, payload)
    print(f"Uploaded s3://{bucket}/{key}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
