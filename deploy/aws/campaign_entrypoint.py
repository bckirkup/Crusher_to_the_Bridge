#!/usr/bin/env python3
"""Generic AWS Batch worker for campaigns declared under ``campaigns/``.

One entrypoint for every campaign: the jobdef command names the campaign
directory (``--campaign noro/hand_occupancy``), the block, the seed list and
the S3 prefix; the campaign's ``campaign.json`` supplies workers, manifest,
epochs and artifact names. Per-campaign ``entry.py`` hooks override argv
construction when a worker takes non-standard arguments.

Child ``i`` runs ``seeds[i]`` and uploads exactly its own artifact under
``<s3_prefix>/<block>/``. A Spot reclaim retries the child and a cell is
deterministic, so an existing S3 artifact means the cell is done rather
than that it must be redone. ``--index`` overrides
``AWS_BATCH_JOB_ARRAY_INDEX`` for single-job canaries (the env var is
reserved on Batch).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess  # noqa: S404 - fixed argv, no shell
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(
    0, str(_REPO_ROOT / "picard_framework" / "runs" / "mega_cruise_campaign"),
)

_BUCKET_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789.-")
_KEY_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._/-",
)


def _s3_uri(raw: str) -> tuple[str, str]:
    parsed = urlparse(raw)
    bucket = parsed.netloc
    key = parsed.path.lstrip("/")
    bad_bucket = any(char not in _BUCKET_CHARS for char in bucket)
    if parsed.scheme != "s3" or not bucket or bad_bucket:
        raise SystemExit(f"Invalid S3 URI: {raw!r}")
    if any(char not in _KEY_CHARS for char in key):
        raise SystemExit(f"Invalid S3 key: {key!r}")
    return bucket, key.rstrip("/")


def _s3_client() -> Any:
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover - image always has boto3
        raise SystemExit("boto3 is required in the Batch image") from exc
    return boto3.client("s3")


def _array_index(explicit: int | None = None) -> int:
    """``--index`` (canary override) else the Batch array env var."""
    if explicit is not None:
        return int(explicit)
    raw = os.environ.get("AWS_BATCH_JOB_ARRAY_INDEX")
    if raw is None:
        raise SystemExit(
            "AWS_BATCH_JOB_ARRAY_INDEX is required (or pass --index)",
        )
    try:
        return int(raw)
    except ValueError as exc:
        raise SystemExit("AWS_BATCH_JOB_ARRAY_INDEX must be an integer") from exc


def _already_uploaded(client: Any, bucket: str, key: str) -> bool:
    """Whether this cell's dump is already in S3 (retry -> done, not redo)."""
    try:
        client.head_object(Bucket=bucket, Key=key)
    except Exception as exc:  # noqa: BLE001 - boto3 raises per-client classes
        response = getattr(exc, "response", {}) or {}
        status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status == 403:
            raise SystemExit(
                "S3 HeadObject returned 403: the block prefix must be under "
                "the job role's campaign/* scope",
            ) from exc
        if status not in (404, None):
            raise
        return False
    return True


def _campaign_dir(name: str) -> Path:
    directory = (_REPO_ROOT / "campaigns" / name).resolve()
    if not directory.is_dir():
        raise SystemExit(f"campaign directory not found: {directory}")
    if not directory.is_relative_to(_REPO_ROOT / "campaigns"):
        raise SystemExit(f"--campaign must stay under campaigns/: {name!r}")
    return directory


def _load_spec(directory: Path) -> dict[str, Any]:
    path = directory / "campaign.json"
    if not path.is_file():
        raise SystemExit(f"campaign spec not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_entry_hook(directory: Path) -> Any:
    """The campaign's ``entry.py`` argv builder, when it ships one."""
    path = directory / "entry.py"
    if not path.is_file():
        return None
    module_name = "campaign_entry_" + "_".join(directory.parts[-2:])
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, "build_argv", None)


def _seed_run_index(
    manifest_path: Path, tier: str, seed: int,
) -> tuple[int, str]:
    """The (index-in-tier, run_id) whose spec carries ``seed``."""
    from campaign_runner import generate_tier_runs

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for index, (run_id, spec) in enumerate(
        generate_tier_runs(manifest, tier),
    ):
        if int(spec["run"]["random_seed"]) == seed:
            return index, run_id
    raise SystemExit(f"seed {seed} not in tier {tier}")


def _default_argv(
    spec: dict[str, Any],
    block: dict[str, Any],
    seed: int,
    out_dir: Path,
    args: argparse.Namespace,
) -> tuple[list[str], Path]:
    """Argv for the two stock worker shapes.

    ``tier`` workers take (manifest, tier, index-in-tier); ``seeds``
    workers take (platform, epochs, seeds). Anything else needs the
    campaign's ``entry.py``.
    """
    worker = block["worker"]
    if block.get("tier"):
        index_in_tier, run_id = _seed_run_index(
            (_REPO_ROOT / args.manifest).resolve(), block["tier"], seed,
        )
        command = [
            sys.executable, worker,
            "--manifest", str(args.manifest),
            "--tier", block["tier"],
            "--index", str(index_in_tier),
            "--pathogen-id", args.pathogen_id,
            "--out", str(out_dir),
        ]
        artifact = out_dir / block["tier"] / f"{run_id}.zip"
    else:
        command = [
            sys.executable, worker,
            "--platform", args.platform,
            "--epochs", str(args.epochs),
            "--seeds", str(seed),
            "--pathogen-id", args.pathogen_id,
            "--out", str(out_dir),
        ]
        if args.bundle:
            command += ["--bundle", args.bundle]
        artifact = out_dir / block["artifact"].format(
            seed=seed, platform=args.platform,
        )
    for key, value in (block.get("args") or {}).items():
        command += [f"--{key.replace('_', '-')}", str(value)]
    return command, artifact


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True,
                        help="campaign dir under campaigns/, e.g. noro/hand_occupancy")
    parser.add_argument("--block", required=True)
    parser.add_argument("--s3-prefix", default=None,
                        help="required unless --local")
    parser.add_argument(
        "--seeds", required=True, type=str, nargs="+",
        help="seed list; accepts comma-joined tokens and/or bare tokens "
             "(--container-overrides splits commas into separate argv "
             "items, and jobdef Ref:: substitution joins them back)",
    )
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--pathogen-id", default=None)
    parser.add_argument("--platform", default="classic_cruise_1900")
    parser.add_argument("--bundle", default=None)
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--index", type=int, default=None)
    parser.add_argument("--local", action="store_true",
                        help="run the worker and verify the artifact locally; "
                             "no S3 upload (scripts/campaign run)")
    parser.add_argument("--out", default=None,
                        help="local output dir; defaults to out/<campaign>")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run this array child's cell and upload exactly its own artifact."""
    args = parse_args(argv)
    directory = _campaign_dir(args.campaign)
    spec = _load_spec(directory)
    block = spec["blocks"].get(args.block)
    if block is None:
        raise SystemExit(
            f"block {args.block!r} not in campaign.json "
            f"({', '.join(spec['blocks'])})",
        )
    args.manifest = args.manifest or spec.get("manifest")
    args.pathogen_id = args.pathogen_id or spec.get("pathogen_id")
    args.epochs = args.epochs or spec.get("epochs") or 288

    index = _array_index(args.index)
    seeds = [
        int(v) for item in args.seeds for v in item.split(",") if v.strip()
    ]
    if index >= len(seeds):
        raise SystemExit(f"array index {index} outside 0..{len(seeds) - 1}")
    seed = seeds[index]

    bucket, prefix = (None, "")
    client = None
    if not args.local:
        if not args.s3_prefix:
            raise SystemExit("--s3-prefix is required unless --local")
        bucket, prefix = _s3_uri(args.s3_prefix)
        if prefix:
            prefix += "/"
        client = _s3_client()

    out_dir = Path(args.out or f"out/{args.campaign}")
    out_dir.mkdir(parents=True, exist_ok=True)

    build = _load_entry_hook(directory)
    if build is not None:
        command, artifact = build(args, block, seed, out_dir)
    else:
        command, artifact = _default_argv(spec, block, seed, out_dir, args)

    print(f"RUN {' '.join(command)}")
    if args.local:
        subprocess.run(command, check=True)
        if not artifact.is_file():
            raise SystemExit(f"worker did not produce {artifact}")
        print(f"LOCAL {artifact}")
        return 0

    key = f"{prefix}{args.block}/{artifact.name}"
    if _already_uploaded(client, bucket, key):
        print(f"SKIP {key} already uploaded")
        return 0

    subprocess.run(command, check=True)
    if not artifact.is_file():
        raise SystemExit(f"worker did not produce {artifact}")
    client.upload_file(str(artifact), bucket, key)
    print(f"UPLOADED {artifact} -> s3://{bucket}/{key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
