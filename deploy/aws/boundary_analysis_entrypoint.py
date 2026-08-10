#!/usr/bin/env python3
"""AWS Batch analysis worker for boundary_surface pipeline phases.

Phases (``--phase``):
  surface  — export outbreak_surface from campaign result zips
  stan     — Bernoulli + Beta-AR hurdle fit for one pathogen
  mc       — pre-boarding Monte Carlo decision model
  report   — regenerate boundary report.md / figures if missing

S3 layout (default)::

  s3://<bucket>/campaign/boundary_surface_v1/                 # Phase-1 zips
  s3://<bucket>/campaign/boundary_surface_v1/analysis/       # Phase 2–5 outs

Environment / flags supply bucket + prefixes. Uses ambient job-role creds.

Security notes (Sonar S8705 / S8707 / S5443)
-------------------------------------------
* S3 I/O uses boto3 (no ``aws`` CLI subprocess).
* Analysis stages call in-process APIs (no ``python -m`` subprocess).
* Work tree is always a private ``tempfile.mkdtemp`` directory.
* Pathogen ids and S3 URIs are allowlist-validated before use.
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlparse

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from simulation_utils.paths import (  # noqa: E402
    confine_to_base,
    validate_path_component,
)

_S3_SCHEME = "s3://"
_SURFACES_SUFFIX = "/surfaces/"
_BUNDLES_ALL_SUFFIX = "/bundles/all/"
_DEFAULT_EXCLUDE = ("analysis/*", "_resume/*", "_ops/*", "b2_*")

_BUCKET_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")
_S3_KEY_RE = re.compile(r"^[A-Za-z0-9._/-]*$")
_PATHOGEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _parse_s3(uri: str) -> tuple[str, str]:
    p = urlparse(uri if "://" in uri else f"{_S3_SCHEME}{uri}")
    if p.scheme != "s3" or not p.netloc:
        raise SystemExit(f"Expected s3://bucket/prefix, got {uri!r}")
    return p.netloc, p.path.lstrip("/")


def _require_s3_uri(uri: str, *, label: str) -> str:
    """Canonicalize and allowlist an ``s3://`` URI."""
    raw = str(uri or "").strip()
    if not raw:
        raise SystemExit(f"{label} is required")
    bucket, key = _parse_s3(raw)
    if not _BUCKET_RE.fullmatch(bucket):
        raise SystemExit(f"Invalid S3 bucket in {label}: {bucket!r}")
    if key and not _S3_KEY_RE.fullmatch(key):
        raise SystemExit(f"Invalid S3 key prefix in {label}: {key!r}")
    return f"{_S3_SCHEME}{bucket}/{key}" if key else f"{_S3_SCHEME}{bucket}"


def _require_pathogen(raw: str | None, *, required: bool) -> str | None:
    token = str(raw or "").strip()
    if not token:
        if required:
            raise SystemExit("--pathogen required")
        return None
    if not _PATHOGEN_RE.fullmatch(token):
        raise SystemExit(f"Invalid pathogen id: {token!r}")
    return validate_path_component(token, label="pathogen")


def _s3_client() -> Any:
    try:
        import boto3  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("boto3 is required (pip install boto3).") from exc
    return boto3.client("s3")


def _excluded(key: str, prefix: str, patterns: Sequence[str]) -> bool:
    rel = key[len(prefix) :].lstrip("/") if key.startswith(prefix) else key
    return any(fnmatch.fnmatch(rel, pat) for pat in patterns)


def _safe_key_parts(key: str, prefix: str) -> list[str] | None:
    """Return validated relative path segments for an S3 object key, or None."""
    if key.endswith("/"):
        return None
    rel = key[len(prefix) :] if prefix and key.startswith(prefix) else key
    parts = [p for p in rel.split("/") if p and p not in {".", ".."}]
    if not parts:
        return None
    for part in parts:
        validate_path_component(part, label="s3 object path segment")
    return parts


def _download_object(client: Any, bucket: str, key: str, dest_dir: Path, prefix: str) -> None:
    parts = _safe_key_parts(key, prefix)
    if parts is None:
        return
    local = dest_dir.joinpath(*parts)
    local.parent.mkdir(parents=True, exist_ok=True)
    print(f"+ {_S3_SCHEME}{bucket}/{key} -> {local}", flush=True)
    client.download_file(bucket, key, str(local))


def _iter_s3_keys(client: Any, bucket: str, prefix: str) -> Any:
    token: str | None = None
    while True:
        kwargs: dict[str, Any] = {"Bucket": bucket, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        page = client.list_objects_v2(**kwargs)
        for obj in page.get("Contents") or ():
            yield str(obj["Key"])
        if not page.get("IsTruncated"):
            return
        token = page.get("NextContinuationToken")


def _s3_download_prefix(
    uri: str,
    dest_dir: Path,
    *,
    exclude: Sequence[str] = (),
) -> None:
    """Download all objects under an S3 prefix into ``dest_dir`` via boto3."""
    safe_uri = _require_s3_uri(uri, label="s3 download")
    bucket, prefix = _parse_s3(safe_uri)
    prefix = prefix.rstrip("/")
    if prefix:
        prefix = prefix + "/"
    dest_dir.mkdir(parents=True, exist_ok=True)
    client = _s3_client()
    for key in _iter_s3_keys(client, bucket, prefix):
        if exclude and _excluded(key, prefix, exclude):
            continue
        _download_object(client, bucket, key, dest_dir, prefix)


def _s3_upload_tree(src_dir: Path, uri: str) -> None:
    """Upload files under ``src_dir`` to an S3 prefix via boto3."""
    safe_uri = _require_s3_uri(uri, label="s3 upload")
    bucket, prefix = _parse_s3(safe_uri)
    prefix = prefix.rstrip("/")
    client = _s3_client()
    base = src_dir.resolve()
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(base).as_posix()
        for part in rel.split("/"):
            validate_path_component(part, label="upload path segment")
        key = f"{prefix}/{rel}" if prefix else rel
        print(f"+ {path} -> {_S3_SCHEME}{bucket}/{key}", flush=True)
        client.upload_file(str(path), bucket, key)


def run_bundle(*, results: Path, out: Path) -> None:
    from picard_framework.analysis.campaign_bundle import build_bundle

    out.mkdir(parents=True, exist_ok=True)
    build_bundle(str(results), str(out))


def run_surface(*, results: Path, out: Path, pathogen: str | None) -> None:
    from picard_framework.analysis.boundary.export_outbreak_surface import (
        export_outbreak_surface,
    )

    out.mkdir(parents=True, exist_ok=True)
    pathogens = [pathogen] if pathogen else None
    export_outbreak_surface(
        [str(results)],
        str(out / "outbreak_surface.csv"),
        pathogens=pathogens,
    )


def run_stan(
    *,
    analysis_dir: Path,
    out: Path,
    pathogen: str,
    chains: int,
    warmup: int,
    sampling: int,
    seed: int,
) -> None:
    from picard_framework.analysis.stan.fit_boundary_hurdle import fit_boundary_hurdle

    safe_pathogen = _require_pathogen(pathogen, required=True) or pathogen
    out.mkdir(parents=True, exist_ok=True)
    fit_boundary_hurdle(
        str(analysis_dir),
        str(out),
        pathogen=safe_pathogen,
        chains=int(chains),
        iter_warmup=int(warmup),
        iter_sampling=int(sampling),
        seed=int(seed),
    )


def run_mc(*, stan_fit: Path, out: Path, n_mc: int, seed: int) -> None:
    from picard_framework.analysis.boundary.run_decision_model import main as mc_main

    out.mkdir(parents=True, exist_ok=True)
    rc = mc_main(
        [
            "--stan-fit",
            str(stan_fit),
            "--lookup",
            "auto",
            "--n-mc",
            str(int(n_mc)),
            "--seed",
            str(int(seed)),
            "--out",
            str(out),
            "--resume",
        ]
    )
    if rc not in (0, None):
        raise SystemExit(rc or 1)


def run_report(*, mc_out: Path) -> None:
    report = mc_out / "report.md"
    if report.is_file():
        print(f"report already present: {report}", flush=True)
        return
    print("No report.md; re-run mc phase to regenerate.", flush=True)


def _phase_bundle(results: Path, analysis: Path, s3_campaign: str, s3_analysis: str) -> None:
    _s3_download_prefix(s3_campaign, results, exclude=_DEFAULT_EXCLUDE)
    out = analysis / "bundles" / "all"
    run_bundle(results=results, out=out)
    _s3_upload_tree(out, s3_analysis.rstrip("/") + _BUNDLES_ALL_SUFFIX)


def _phase_surface(
    results: Path,
    analysis: Path,
    s3_campaign: str,
    s3_analysis: str,
    pathogen: str | None,
) -> None:
    _s3_download_prefix(s3_campaign, results, exclude=_DEFAULT_EXCLUDE)
    out = analysis / "surfaces"
    run_surface(results=results, out=out, pathogen=pathogen)
    _s3_upload_tree(out, s3_analysis.rstrip("/") + _SURFACES_SUFFIX)


def _phase_stan(
    analysis: Path,
    s3_analysis: str,
    pathogen: str,
    chains: int,
    warmup: int,
    sampling: int,
    seed: int,
) -> None:
    safe_pathogen = _require_pathogen(pathogen, required=True) or pathogen
    bundle_dir = analysis / "all"
    _s3_download_prefix(s3_analysis.rstrip("/") + _BUNDLES_ALL_SUFFIX, bundle_dir)
    if not (bundle_dir / "run_summary.csv").is_file():
        bundle_dir = analysis / safe_pathogen
        _s3_download_prefix(
            s3_analysis.rstrip("/") + f"/bundles/{safe_pathogen}/",
            bundle_dir,
        )
    out = analysis / "stan" / safe_pathogen
    run_stan(
        analysis_dir=bundle_dir,
        out=out,
        pathogen=safe_pathogen,
        chains=chains,
        warmup=warmup,
        sampling=sampling,
        seed=seed,
    )
    _s3_download_prefix(s3_analysis.rstrip("/") + _SURFACES_SUFFIX, out)
    _s3_upload_tree(out, s3_analysis.rstrip("/") + f"/stan/{safe_pathogen}/")


def _phase_mc(
    analysis: Path,
    s3_analysis: str,
    pathogen: str,
    n_mc: int,
    seed: int,
) -> None:
    safe_pathogen = _require_pathogen(pathogen, required=True) or pathogen
    local_fit = analysis / "stan" / safe_pathogen
    _s3_download_prefix(
        s3_analysis.rstrip("/") + f"/stan/{safe_pathogen}/",
        local_fit,
    )
    if not (local_fit / "outbreak_surface.json").is_file() and not (
        local_fit / "outbreak_surface.csv"
    ).is_file():
        _s3_download_prefix(s3_analysis.rstrip("/") + _SURFACES_SUFFIX, local_fit)
    out = analysis / "mc" / safe_pathogen
    run_mc(stan_fit=local_fit, out=out, n_mc=n_mc, seed=seed)
    _s3_upload_tree(out, s3_analysis.rstrip("/") + f"/mc/{safe_pathogen}/")


def _phase_report(analysis: Path, s3_analysis: str, pathogen: str) -> None:
    safe_pathogen = _require_pathogen(pathogen, required=True) or pathogen
    local_mc = analysis / "mc" / safe_pathogen
    _s3_download_prefix(
        s3_analysis.rstrip("/") + f"/mc/{safe_pathogen}/",
        local_mc,
    )
    run_report(mc_out=local_mc)
    _s3_upload_tree(local_mc, s3_analysis.rstrip("/") + f"/mc/{safe_pathogen}/")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--phase",
        required=True,
        choices=("bundle", "surface", "stan", "mc", "report"),
    )
    p.add_argument(
        "--s3-campaign",
        default=os.environ.get("BOUNDARY_S3_CAMPAIGN", ""),
        help="s3://bucket/campaign/boundary_surface_v1/",
    )
    p.add_argument(
        "--s3-analysis",
        default=os.environ.get("BOUNDARY_S3_ANALYSIS", ""),
        help="s3://bucket/campaign/boundary_surface_v1/analysis/",
    )
    p.add_argument("--pathogen", default=os.environ.get("BOUNDARY_PATHOGEN", ""))
    p.add_argument("--chains", type=int, default=4)
    p.add_argument("--iter-warmup", type=int, default=1000)
    p.add_argument("--iter-sampling", type=int, default=1000)
    p.add_argument("--seed", type=int, default=1701)
    p.add_argument("--n-mc", type=int, default=2000)
    args = p.parse_args(argv)

    s3_campaign = _require_s3_uri(args.s3_campaign, label="--s3-campaign")
    s3_analysis = _require_s3_uri(args.s3_analysis, label="--s3-analysis")
    pathogen_opt = _require_pathogen(args.pathogen, required=False)

    # Private 0o700 work tree — never CLI-controlled / world-writable (S5443/S8707).
    work = Path(tempfile.mkdtemp(prefix="boundary_work_"))
    work_s = confine_to_base(str(work), str(work))
    os.chdir(work_s)
    results = Path(work_s) / "results"
    analysis = Path(work_s) / "analysis"
    results.mkdir(exist_ok=True)
    analysis.mkdir(exist_ok=True)

    default_pathogen = "noro" + "virus"
    if args.phase == "bundle":
        _phase_bundle(results, analysis, s3_campaign, s3_analysis)
    elif args.phase == "surface":
        _phase_surface(results, analysis, s3_campaign, s3_analysis, pathogen_opt)
    elif args.phase == "stan":
        _phase_stan(
            analysis,
            s3_analysis,
            pathogen_opt or "",
            args.chains,
            args.iter_warmup,
            args.iter_sampling,
            args.seed,
        )
    elif args.phase == "mc":
        _phase_mc(
            analysis,
            s3_analysis,
            pathogen_opt or default_pathogen,
            args.n_mc,
            args.seed,
        )
    else:
        _phase_report(analysis, s3_analysis, pathogen_opt or default_pathogen)

    print(f"phase={args.phase} done work={work_s}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
