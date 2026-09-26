#!/usr/bin/env python3
"""AWS Batch worker for the initiation-probe matrix (COVID-SEED-GEOM-01 and
NORO-IMPORT-YIELD-01).

One array covers both readouts: array index maps to ``(family, seed)`` through
the fixed :data:`MATRIX` below, so the submitted experiment is this file and
nothing else. Each child runs one seed of one family, then uploads exactly the
per-seed artifact the driver wrote to the caller's S3 prefix under
``<family>/``. Pooling/readout aggregation runs locally after ``aws s3 sync``
— children deliberately do not upload the pooled ``*_readout.json`` the noro
driver writes, because each child's pool would be a one-seed pool overwriting
its siblings.

Same S3 conventions as ``dose_challenge_entrypoint.py``: a Spot reclaim
retries the child, cells are deterministic, so an existing artifact means the
cell is done rather than that it must be redone. The job role writes only
under ``campaign/*``.
"""
from __future__ import annotations

import argparse
import os
import subprocess  # noqa: S404 - fixed argv, no shell
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_BUCKET_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789.-")
_KEY_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._/-",
)

_COVID_DRIVER = "tools/covid_seed_ring_burn.py"
_NORO_DRIVER = "tools/noro_diag/import_yield_probe.py"
_OUT_ROOT = "init_probe_out"

_FRESH_INDEX_PATCH = (
    '{"onset_day": null, "departure_day": null, "infection_age_days": 0.0}'
)


def _covid_family(extra: list[str]) -> dict[str, Any]:
    return {
        "driver": _COVID_DRIVER,
        "extra": extra,
        "artifact": "{family}_seed{seed}.json",
        "out_is_file": True,
    }


def _noro_family(arm_args: list[str], tag: str) -> dict[str, Any]:
    return {
        "driver": _NORO_DRIVER,
        "extra": ["--platform", "spirit_cruise_3000", "--bundle", "norwalk_only",
                  "--pathogen-id", "norwalk_gi", "--epochs", "168", *arm_args],
        "artifact": f"import_yield_{tag}_seed{{seed}}.json.gz",
        "out_is_file": False,
    }


# (family, seeds, spec) — the full experiment, fixed before submission per the
# campaign-preflight gate. Seeds are contiguous ranges expanded at module load
# so the array index -> (family, seed) map is trivially auditable.
MATRIX: list[tuple[str, int, dict[str, Any]]] = [
    *[
        ("covid_base", seed, _covid_family(["--epochs", "168"]))
        for seed in range(20200205, 20200210)
    ],
    *[
        (
            "covid_agepair", seed,
            _covid_family(["--epochs", "48", "--age-pair", "6.8"]),
        )
        for seed in (20200205, 20200206)
    ],
    *[
        (
            "covid_depart0", seed,
            _covid_family(
                ["--epochs", "96", "--seed-patch", '{"departure_day": 0.0}'],
            ),
        )
        for seed in range(20200205, 20200210)
    ],
    *[
        (
            "covid_fresh", seed,
            _covid_family(["--epochs", "168", "--seed-patch", _FRESH_INDEX_PATCH]),
        )
        for seed in range(20200205, 20200210)
    ],
    *[
        ("noro_baseline", seed, _noro_family(["--arm", "baseline"], "baseline"))
        for seed in range(8000, 8020)
    ],
    *[
        (
            "noro_single_symptomatic", seed,
            _noro_family(
                ["--arm", "single", "--onset-day", "-1", "--age-days", "2.2"],
                "single_onset-1_age2.2",
            ),
        )
        for seed in range(8000, 8010)
    ],
    *[
        (
            "noro_single_presymptomatic", seed,
            _noro_family(
                ["--arm", "single", "--onset-day", "0.5", "--age-days", "0.4"],
                "single_onset0.5_age0.4",
            ),
        )
        for seed in range(8000, 8010)
    ],
    *[
        (
            "noro_single_convalescent", seed,
            _noro_family(
                ["--arm", "single", "--onset-day", "-4", "--age-days", "5.2"],
                "single_onset-4_age5.2",
            ),
        )
        for seed in range(8000, 8010)
    ],
]


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


def _array_index() -> int:
    raw = os.environ.get("AWS_BATCH_JOB_ARRAY_INDEX")
    if raw is None:
        raise SystemExit("AWS_BATCH_JOB_ARRAY_INDEX is required")
    try:
        return int(raw)
    except ValueError as exc:
        raise SystemExit("AWS_BATCH_JOB_ARRAY_INDEX must be an integer") from exc


def _already_uploaded(client: Any, bucket: str, key: str) -> bool:
    """Whether this cell's artifact is already in S3 (retry -> done)."""
    try:
        client.head_object(Bucket=bucket, Key=key)
    except Exception as exc:  # noqa: BLE001 - boto3 raises per-client classes
        response = getattr(exc, "response", {}) or {}
        status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status == 403:
            raise SystemExit(
                "S3 HeadObject returned 403: the prefix must be under "
                "the job role's campaign/* scope",
            ) from exc
        if status not in (404, None):
            raise
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--s3-prefix", required=True)
    parser.add_argument(
        "--index", type=int, default=None,
        help=(
            "matrix index override for non-array canary jobs — "
            "AWS_BATCH_* names are reserved, so a canary cannot set the "
            "array index through container environment overrides"
        ),
    )
    args = parser.parse_args()

    index = args.index if args.index is not None else _array_index()
    if not 0 <= index < len(MATRIX):
        raise SystemExit(f"Array index {index} outside 0..{len(MATRIX) - 1}")
    family, seed, spec = MATRIX[index]
    artifact = spec["artifact"].format(family=family, seed=seed)

    bucket, prefix = _s3_uri(args.s3_prefix)
    if prefix:
        prefix += "/"
    client = _s3_client()
    key = f"{prefix}{family}/{artifact}"
    if _already_uploaded(client, bucket, key):
        print(f"Already complete: s3://{bucket}/{key}", flush=True)
        return 0

    out_dir = _REPO_ROOT / _OUT_ROOT / family
    out_dir.mkdir(parents=True, exist_ok=True)
    if spec["out_is_file"]:
        out_arg = out_dir / artifact
    else:
        out_arg = out_dir
    command = [
        sys.executable, spec["driver"], "--seeds", str(seed),
        *spec["extra"], "--out", str(out_arg),
    ]
    print(" ".join(command), flush=True)
    subprocess.run(command, check=True, cwd=_REPO_ROOT)  # noqa: S603

    dump = out_dir / artifact
    if not dump.exists():
        raise SystemExit(f"driver finished but wrote no dump at {dump}")
    client.upload_file(str(dump), bucket, key)
    print(f"Uploaded s3://{bucket}/{key}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
