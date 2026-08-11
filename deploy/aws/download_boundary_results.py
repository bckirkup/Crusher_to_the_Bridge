#!/usr/bin/env python3
"""Download boundary_surface_v1 results: pack run zips into tars, sync analysis.

The campaign prefix has ~17.6k tiny ``*.zip`` objects. Syncing them one-by-one
is slow on Windows; this streams each object into ``b1_run_zips.tar`` /
``b2_run_zips.tar`` (no gzip — payloads are already zip-compressed), then
``aws s3 sync``-equivalent download of ``analysis/``.

Example::

    python deploy/aws/download_boundary_results.py \\
      --bucket crusherbucket-994254241749-us-east-1-an \\
      --prefix campaign/boundary_surface_v1/ \\
      --out results/boundary_surface_v1/ \\
      --profile picard
"""

from __future__ import annotations

import argparse
import io
import sys
import tarfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import boto3
from botocore.config import Config

from deploy.aws.path_safety import safe_path
from simulation_utils.paths import validate_path_component


def _client(profile: str, region: str):
    session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    return session.client(
        "s3",
        region_name=region,
        config=Config(max_pool_connections=32, retries={"max_attempts": 10}),
    )


def _list_keys(s3, bucket: str, prefix: str) -> list[dict]:
    keys: list[dict] = []
    token = None
    while True:
        kwargs = {"Bucket": bucket, "Prefix": prefix, "MaxKeys": 1000}
        if token:
            kwargs["ContinuationToken"] = token
        resp = s3.list_objects_v2(**kwargs)
        for obj in resp.get("Contents") or []:
            keys.append({"Key": obj["Key"], "Size": int(obj["Size"])})
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextContinuationToken")
    return keys


def _fetch(s3, bucket: str, key: str) -> bytes:
    return s3.get_object(Bucket=bucket, Key=key)["Body"].read()


def _safe_key_parts(key: str, prefix: str) -> list[str] | None:
    """Return validated relative path segments for an S3 object key, or None."""
    if key.endswith("/"):
        return None
    rel = key[len(prefix) :] if prefix and key.startswith(prefix) else key
    raw_parts = [p for p in rel.split("/") if p]
    if not raw_parts:
        return None
    if any(p in {".", ".."} for p in raw_parts):
        raise ValueError(f"Invalid s3 object path segment in {key!r}")
    for part in raw_parts:
        validate_path_component(part, label="s3 object path segment")
    return raw_parts


def _is_run_zip_key(key: str) -> bool:
    return (
        key.endswith(".zip")
        and "/analysis/" not in key
        and "/_resume/" not in key
        and "/_ops/" not in key
    )


def _partition_run_zips(zips: list[dict]) -> list[tuple[str, list[dict]]]:
    """Group zip objects into tar output names (boundary b1/b2 or single tar)."""
    b1 = [o for o in zips if Path(o["Key"]).name.startswith("b1_")]
    b2 = [o for o in zips if Path(o["Key"]).name.startswith("b2_")]
    other = [
        o
        for o in zips
        if not Path(o["Key"]).name.startswith(("b1_", "b2_"))
    ]
    if b1 or b2:
        return [
            ("b1_run_zips.tar", b1),
            ("b2_run_zips.tar", b2),
            ("other_run_zips.tar", other),
        ]
    return [("run_zips.tar", zips)]


def pack_zips_to_tar(
    *,
    s3,
    bucket: str,
    keys: list[dict],
    tar_path: Path,
    workers: int,
) -> tuple[int, int]:
    """Download zip objects concurrently and write a single uncompressed tar."""
    tar_path.parent.mkdir(parents=True, exist_ok=True)
    if tar_path.exists():
        tar_path.unlink()

    # Prefetch in flight, write tar sequentially (tarfile is not thread-safe).
    total_bytes = 0
    n = 0
    t0 = time.time()
    with tarfile.open(tar_path, mode="w") as tar:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(_fetch, s3, bucket, item["Key"]): item for item in keys
            }
            done = 0
            for fut in as_completed(futures):
                item = futures[fut]
                data = fut.result()
                name = Path(item["Key"]).name
                validate_path_component(name, label="s3 object basename")
                info = tarfile.TarInfo(name=name)
                info.size = len(data)
                info.mtime = int(time.time())
                tar.addfile(info, io.BytesIO(data))
                total_bytes += len(data)
                n += 1
                done += 1
                if done % 500 == 0 or done == len(keys):
                    elapsed = max(time.time() - t0, 1e-6)
                    print(
                        f"  {tar_path.name}: {done}/{len(keys)} "
                        f"({total_bytes / 1e6:.1f} MB, {done / elapsed:.0f} obj/s)",
                        flush=True,
                    )
    return n, total_bytes


def _download_one_analysis_object(
    *,
    s3,
    bucket: str,
    item: dict,
    analysis_prefix: str,
    out_dir: Path,
) -> int:
    key = item["Key"]
    parts = _safe_key_parts(key, analysis_prefix)
    if parts is None:
        return 0
    dest = out_dir.joinpath(*parts)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(_fetch(s3, bucket, key))
    return int(item["Size"])


def download_analysis(*, s3, bucket: str, prefix: str, out_dir: Path, workers: int) -> int:
    """Download every object under analysis/ preserving relative paths."""
    analysis_prefix = prefix.rstrip("/") + "/analysis/"
    objs = _list_keys(s3, bucket, analysis_prefix)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Downloading analysis/ ({len(objs)} objects) -> {out_dir}", flush=True)

    written = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(
                _download_one_analysis_object,
                s3=s3,
                bucket=bucket,
                item=item,
                analysis_prefix=analysis_prefix,
                out_dir=out_dir,
            )
            for item in objs
        ]
        for i, fut in enumerate(as_completed(futures), 1):
            written += fut.result()
            if i % 100 == 0 or i == len(futures):
                print(
                    f"  analysis: {i}/{len(objs)} ({written / 1e6:.1f} MB)",
                    flush=True,
                )
    print(f"  analysis done in {time.time() - t0:.1f}s", flush=True)
    return len(objs)


def _pack_zip_groups(*, s3, bucket: str, prefix: str, out: Path, workers: int) -> None:
    print(f"Listing objects under s3://{bucket}/{prefix} ...", flush=True)
    all_objs = _list_keys(s3, bucket, prefix)
    zips = [o for o in all_objs if _is_run_zip_key(o["Key"])]
    groups = _partition_run_zips(zips)
    b1_n = next((len(g) for name, g in groups if name.startswith("b1_")), 0)
    b2_n = next((len(g) for name, g in groups if name.startswith("b2_")), 0)
    other_n = next((len(g) for name, g in groups if "other" in name or name == "run_zips.tar"), 0)
    print(
        f"Found {len(zips)} run zips "
        f"(b1={b1_n}, b2={b2_n}, other={other_n})",
        flush=True,
    )
    for name, group in groups:
        if not group:
            continue
        tar_path = out / name
        print(f"Packing {tar_path} ({len(group)} zips)...", flush=True)
        n, nbytes = pack_zips_to_tar(
            s3=s3,
            bucket=bucket,
            keys=group,
            tar_path=tar_path,
            workers=workers,
        )
        print(
            f"  wrote {tar_path} ({n} members, {nbytes / 1e6:.1f} MB)",
            flush=True,
        )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bucket", required=True)
    p.add_argument("--prefix", default="campaign/boundary_surface_v1/")
    p.add_argument("--out", type=Path, default=Path("results/boundary_surface_v1"))
    p.add_argument("--profile", default="picard")
    p.add_argument("--region", default="us-east-1")
    p.add_argument("--workers", type=int, default=16)
    p.add_argument("--skip-zips", action="store_true")
    p.add_argument("--skip-analysis", action="store_true")
    args = p.parse_args(argv)

    s3 = _client(args.profile, args.region)
    prefix = args.prefix if args.prefix.endswith("/") else args.prefix + "/"
    out = Path(safe_path(args.out))
    out.mkdir(parents=True, exist_ok=True)

    if not args.skip_zips:
        _pack_zip_groups(
            s3=s3,
            bucket=args.bucket,
            prefix=prefix,
            out=out,
            workers=args.workers,
        )

    if not args.skip_analysis:
        download_analysis(
            s3=s3,
            bucket=args.bucket,
            prefix=prefix,
            out_dir=out / "analysis",
            workers=args.workers,
        )

    print(f"Done. Output under {out.resolve()}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
