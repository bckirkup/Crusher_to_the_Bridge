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


def download_analysis(*, s3, bucket: str, prefix: str, out_dir: Path, workers: int) -> int:
    """Download every object under analysis/ preserving relative paths."""
    analysis_prefix = prefix.rstrip("/") + "/analysis/"
    objs = _list_keys(s3, bucket, analysis_prefix)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Downloading analysis/ ({len(objs)} objects) -> {out_dir}", flush=True)

    def _one(item: dict) -> int:
        key = item["Key"]
        rel = key[len(analysis_prefix) :]
        if not rel or key.endswith("/"):
            return 0
        dest = out_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(_fetch(s3, bucket, key))
        return item["Size"]

    written = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_one, item) for item in objs]
        for i, fut in enumerate(as_completed(futures), 1):
            written += fut.result()
            if i % 100 == 0 or i == len(futures):
                print(
                    f"  analysis: {i}/{len(objs)} ({written / 1e6:.1f} MB)",
                    flush=True,
                )
    print(f"  analysis done in {time.time() - t0:.1f}s", flush=True)
    return len(objs)


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
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)

    if not args.skip_zips:
        print(f"Listing objects under s3://{args.bucket}/{prefix} ...", flush=True)
        all_objs = _list_keys(s3, args.bucket, prefix)
        zips = [
            o
            for o in all_objs
            if o["Key"].endswith(".zip")
            and "/analysis/" not in o["Key"]
            and "/_resume/" not in o["Key"]
            and "/_ops/" not in o["Key"]
        ]
        b1 = [o for o in zips if Path(o["Key"]).name.startswith("b1_")]
        b2 = [o for o in zips if Path(o["Key"]).name.startswith("b2_")]
        other = [
            o
            for o in zips
            if not Path(o["Key"]).name.startswith(("b1_", "b2_"))
        ]
        print(
            f"Found {len(zips)} run zips "
            f"(b1={len(b1)}, b2={len(b2)}, other={len(other)})",
            flush=True,
        )
        # Boundary campaigns keep b1/b2 split; others (sr_/vd_/…) → one tar.
        if b1 or b2:
            groups = (("b1_run_zips.tar", b1), ("b2_run_zips.tar", b2), ("other_run_zips.tar", other))
        else:
            groups = (("run_zips.tar", zips),)
        for name, group in groups:
            if not group:
                continue
            tar_path = out / name
            print(f"Packing {tar_path} ({len(group)} zips)...", flush=True)
            n, nbytes = pack_zips_to_tar(
                s3=s3,
                bucket=args.bucket,
                keys=group,
                tar_path=tar_path,
                workers=args.workers,
            )
            print(
                f"  wrote {tar_path} ({n} members, {nbytes / 1e6:.1f} MB)",
                flush=True,
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
