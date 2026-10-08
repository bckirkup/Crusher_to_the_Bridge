#!/usr/bin/env python3
"""GM-RESCORE-02 readout: pool the campaign's block prefixes into the two
flat cell dirs the scoring readout expects, then run
``tools/covid_gm_rescore_readout.py`` for both designs.

Sources: ``--prefix s3://...`` (streams cell_*.json via boto3, default the
campaign prefix) or ``--dir`` (a local tree of block dirs, e.g. after
``aws s3 sync``). Scoring blocks — every block except ``imports3_hygiene``
— merge into the scoring dir (the anchor row pools its canary prefix and
the fleet continuation; payloads carry (theta, arm_id, seed) so the merge
is coordinate-safe); ``imports3_hygiene`` lands in the pair dir. Each
design then reads with the other as ``--pair-cells``.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools import covid_gm_rescore_readout as _rescore  # noqa: E402

_SCORING_DESIGN = "picard_framework/runs/covid_gm_rescore_v2_design.json"
_IMPORTS3_DESIGN = (
    "picard_framework/runs/covid_gm_rescore_v2_imports3_design.json"
)
_DEFAULT_PREFIX = (
    "s3://crusherbucket-994254241749-us-east-1-an/"
    "campaign/covid_gm_rescore_02/"
)
_IMPORTS3_BLOCK = "imports3_hygiene"


def _s3_client() -> Any:
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover - dev box has boto3
        raise SystemExit("boto3 is required for --prefix") from exc
    return boto3.client("s3")


def _split_s3(uri: str) -> tuple[str, str]:
    assert uri.startswith("s3://"), f"need s3:// uri, got {uri!r}"
    bucket, _, prefix = uri[5:].partition("/")
    return bucket, prefix.rstrip("/") + "/"


def _iter_s3(prefix: str) -> Iterable[tuple[str, dict[str, Any]]]:
    """(block_name, payload) for every cell_*.json under an s3 prefix."""
    bucket, key_prefix = _split_s3(prefix)
    client = _s3_client()
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=key_prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            rel = key[len(key_prefix):]
            if not rel.endswith(".json") or "/" not in rel:
                continue
            block = rel.split("/", 1)[0]
            body = client.get_object(Bucket=bucket, Key=key)["Body"].read()
            yield block, json.loads(body)


def _iter_dir(root: Path) -> Iterable[tuple[str, dict[str, Any]]]:
    """(block_name, payload) for every cell_*.json under a block tree."""
    for block_dir in sorted(root.iterdir()):
        if not block_dir.is_dir():
            continue
        for path in sorted(block_dir.glob("cell_*.json")):
            yield block_dir.name, json.loads(
                path.read_text(encoding="utf-8"),
            )


def _stage(
    staged: dict[str, Path], block: str, payloads: Iterable[dict],
    root: Path,
) -> dict[str, Path]:
    """Write payloads into per-side staging dirs, return the dir map."""
    for payload in payloads:
        key = (
            payload.get("cell") or {}
        ).get("key") or f"cell_{id(payload)}.json"
        side_dir = staged["pair"] if block == _IMPORTS3_BLOCK \
            else staged["scoring"]
        (side_dir / key).write_text(
            json.dumps(payload), encoding="utf-8",
        )
    return staged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--prefix", default=_DEFAULT_PREFIX)
    source.add_argument(
        "--dir", type=Path, default=None,
        help="local block tree (skips s3)",
    )
    parser.add_argument(
        "--stage", type=Path,
        default=_REPO_ROOT / "campaign_results/covid_gm_rescore_v2",
        help="staging root for the pooled cell dirs",
    )
    parser.add_argument(
        "--out", type=Path, default=None,
        help="report dir (default: <stage>/reports)",
    )
    parser.add_argument(
        "--allow-partial", action="store_true",
        help="read whatever cells exist (canary/incomplete arrays)",
    )
    args = parser.parse_args(argv)

    stage = args.stage
    staged = {
        "scoring": stage / "cells",
        "pair": stage / "cells_imports3",
    }
    for d in staged.values():
        d.mkdir(parents=True, exist_ok=True)
        for old in d.glob("cell_*.json"):
            old.unlink()

    source_iter = (
        _iter_dir(args.dir) if args.dir is not None
        else _iter_s3(args.prefix)
    )
    n = 0
    for block, payload in source_iter:
        _stage(staged, block, [payload], stage)
        n += 1
    print(f"staged {n} cell payloads under {stage}")

    out_dir = args.out or (stage / "reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    partial = ["--allow-partial"] if args.allow_partial else []
    rc = _rescore.main([
        "--cells", str(staged["scoring"]),
        "--design", _SCORING_DESIGN,
        "--out", str(out_dir / "covid_gm_rescore_v2_readout.json"),
        "--pair-cells", str(staged["pair"]),
        *partial,
    ])
    if rc:
        return rc
    return _rescore.main([
        "--cells", str(staged["pair"]),
        "--design", _IMPORTS3_DESIGN,
        "--out", str(out_dir / "covid_gm_rescore_v2_imports3_readout.json"),
        "--pair-cells", str(staged["scoring"]),
        "--pair-arm", "hygiene_cycle",
        *partial,
    ])


if __name__ == "__main__":
    raise SystemExit(main())
