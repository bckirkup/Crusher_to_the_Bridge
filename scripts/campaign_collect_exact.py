"""Fetch the collector's requested object or the reviewed Edison solver return."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

SOLVER_OUTPUTS = (
    ("campaign/contam_fleet_workup_fleet_01/package/contam_fleet_workup_77_package_02.tar.gz",
     4_575_643, "3bc0e40f4d7a03082bbb6caf01ff76257163d7da8daee672f55a80c406f9684d"),
    ("campaign/covid_transport_fit_01/return/paired_01/seed_endpoints.csv",
     26_153, "0a990ce55e71776b054c1d403ef6dac01be5c83df1fde67ddd47a9f2723cd8c8"),
)


def fetch(bucket: str, key: str, ceiling: int, expected: str | None, folder: Path) -> str:
    if not key.startswith("campaign/") or ".." in key or key.endswith("/"):
        raise ValueError(f"malformed campaign key: {key!r}")
    args = ["--bucket", bucket, "--key", key]
    head = json.loads(subprocess.check_output(
        ["aws", "s3api", "head-object", *args, "--output", "json"]))
    storage = (head.get("StorageClass") or "STANDARD").upper()
    if "ARCHIVE" in storage or storage == "GLACIER":
        raise ValueError(f"archived object: {key}")
    if head["ContentLength"] > ceiling or (expected and head["ContentLength"] != ceiling):
        raise ValueError(f"unexpected size for {key}: {head['ContentLength']}")
    if head.get("VersionId"):
        args += ["--version-id", head["VersionId"]]
    else:
        args += ["--if-match", head["ETag"]]
    dest = folder / key.rsplit("/", 1)[-1]
    subprocess.run(["aws", "s3api", "get-object", *args, str(dest)],
                   check=True, stdout=subprocess.DEVNULL)
    if dest.stat().st_size != head["ContentLength"]:
        raise ValueError(f"size mismatch for {key}")
    with dest.open("rb") as fh:
        digest = hashlib.file_digest(fh, "sha256").hexdigest()
    if expected and digest != expected:
        raise ValueError(f"SHA-256 mismatch for {key}")
    return digest


def main() -> None:
    reviewed = os.environ.get("SOLVER_RETURN") == "true"
    outputs = SOLVER_OUTPUTS if reviewed else [
        (os.environ["EXACT_KEY"].strip(), int(os.environ.get("MAX_FETCH_BYTES") or 52_428_800), None)]
    folder = Path("fetched")
    folder.mkdir(exist_ok=True)
    with (folder / "SHA256SUMS").open("w", encoding="utf-8") as receipt:
        for key, ceiling, expected in outputs:
            digest = fetch(os.environ["BUCKET"], key, ceiling, expected, folder)
            label = key.rsplit("/", 1)[-1] if reviewed else key
            receipt.write(f"{digest}  {label}\n")
            print(f"fetched {key}, sha256 {digest}")


if __name__ == "__main__":
    main()
