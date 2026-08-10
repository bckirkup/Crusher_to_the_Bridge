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
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence
from urllib.parse import urlparse

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from deploy.aws.path_safety import safe_path  # noqa: E402
from simulation_utils.paths import validate_path_component  # noqa: E402

_SURFACES_SUFFIX = "/surfaces/"
_BUNDLES_ALL_SUFFIX = "/bundles/all/"
_DEFAULT_EXCLUDE = ("analysis/*", "_resume/*", "_ops/*", "b2_*")

# Allowlist validators for LLM-/CLI-supplied strings before OS commands (S8705).
_BUCKET_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")
_S3_KEY_RE = re.compile(r"^[A-Za-z0-9._/-]*$")
_PATHOGEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _parse_s3(uri: str) -> tuple[str, str]:
    p = urlparse(uri if "://" in uri else f"s3://{uri}")
    if p.scheme != "s3" or not p.netloc:
        raise SystemExit(f"Expected s3://bucket/prefix, got {uri!r}")
    key = p.path.lstrip("/")
    return p.netloc, key


def _require_s3_uri(uri: str, *, label: str) -> str:
    """Canonicalize and allowlist an ``s3://`` URI before aws CLI use."""
    raw = str(uri or "").strip()
    if not raw:
        raise SystemExit(f"{label} is required")
    bucket, key = _parse_s3(raw)
    if not _BUCKET_RE.fullmatch(bucket):
        raise SystemExit(f"Invalid S3 bucket in {label}: {bucket!r}")
    if key and not _S3_KEY_RE.fullmatch(key):
        raise SystemExit(f"Invalid S3 key prefix in {label}: {key!r}")
    return f"s3://{bucket}/{key}" if key else f"s3://{bucket}"


def _require_pathogen(raw: str | None, *, required: bool) -> str | None:
    token = str(raw or "").strip()
    if not token:
        if required:
            raise SystemExit("--pathogen required")
        return None
    if not _PATHOGEN_RE.fullmatch(token):
        raise SystemExit(f"Invalid pathogen id: {token!r}")
    return validate_path_component(token, label="pathogen")


def _local_dir(path: Path) -> str:
    """Confine a local path to the work tree / cwd before FS or subprocess use."""
    return safe_path(path)


def _run_cmd(cmd: Sequence[str], *, cwd: str | None = None) -> None:
    """Run argv list after rejecting NUL bytes (no shell)."""
    argv = [str(part) for part in cmd]
    if any("\x00" in part for part in argv):
        raise SystemExit("NUL byte in command argument")
    if cwd is not None:
        cwd = _local_dir(Path(cwd))
    print("+", " ".join(argv), flush=True)
    subprocess.check_call(argv, cwd=cwd)


def _s3_sync(src: str, dst: str, *, exclude: Sequence[str] | None = None) -> None:
    src_uri = _require_s3_uri(src, label="s3 sync source") if src.startswith("s3://") else _local_dir(Path(src))
    dst_uri = _require_s3_uri(dst, label="s3 sync dest") if dst.startswith("s3://") else _local_dir(Path(dst))
    cmd = ["aws", "s3", "sync", src_uri, dst_uri]
    for pat in exclude or ():
        if "\x00" in pat or len(pat) > 256:
            raise SystemExit(f"Invalid --exclude pattern: {pat!r}")
        cmd.extend(["--exclude", pat])
    _run_cmd(cmd)


def _s3_cp_recursive(src: str, dst: str) -> None:
    src_uri = _require_s3_uri(src, label="s3 cp source") if src.startswith("s3://") else _local_dir(Path(src))
    dst_uri = _require_s3_uri(dst, label="s3 cp dest") if dst.startswith("s3://") else _local_dir(Path(dst))
    _run_cmd(["aws", "s3", "cp", src_uri, dst_uri, "--recursive"])


def run_bundle(*, work: Path, results: Path, out: Path) -> None:
    out_s = _local_dir(out)
    Path(out_s).mkdir(parents=True, exist_ok=True)
    _run_cmd(
        [
            sys.executable,
            "-m",
            "picard_framework.analysis.campaign_bundle",
            _local_dir(results),
            "--out",
            out_s,
        ],
        cwd=_local_dir(work),
    )


def run_surface(
    *, work: Path, results: Path, out: Path, pathogen: str | None
) -> None:
    out_s = _local_dir(out)
    Path(out_s).mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "picard_framework.analysis.boundary.export_outbreak_surface",
        _local_dir(results),
        "--out",
        str(Path(out_s) / "outbreak_surface.csv"),
    ]
    if pathogen:
        cmd.extend(["--pathogen", _require_pathogen(pathogen, required=True) or pathogen])
    _run_cmd(cmd, cwd=_local_dir(work))


def run_stan(
    *,
    work: Path,
    analysis_dir: Path,
    out: Path,
    pathogen: str,
    chains: int,
    warmup: int,
    sampling: int,
    seed: int,
) -> None:
    safe_pathogen = _require_pathogen(pathogen, required=True) or pathogen
    out_s = _local_dir(out)
    Path(out_s).mkdir(parents=True, exist_ok=True)
    _run_cmd(
        [
            sys.executable,
            "-m",
            "picard_framework.analysis.stan.fit_boundary_hurdle",
            _local_dir(analysis_dir),
            "--out",
            out_s,
            "--pathogen",
            safe_pathogen,
            "--chains",
            str(int(chains)),
            "--iter-warmup",
            str(int(warmup)),
            "--iter-sampling",
            str(int(sampling)),
            "--seed",
            str(int(seed)),
        ],
        cwd=_local_dir(work),
    )


def run_mc(*, work: Path, stan_fit: Path, out: Path, n_mc: int, seed: int) -> None:
    out_s = _local_dir(out)
    Path(out_s).mkdir(parents=True, exist_ok=True)
    _run_cmd(
        [
            sys.executable,
            "-m",
            "picard_framework.analysis.boundary.run_decision_model",
            "--stan-fit",
            _local_dir(stan_fit),
            "--lookup",
            "auto",
            "--n-mc",
            str(int(n_mc)),
            "--seed",
            str(int(seed)),
            "--out",
            out_s,
            "--resume",
        ],
        cwd=_local_dir(work),
    )


def run_report(*, mc_out: Path) -> None:
    # Decision model already writes report.md; no-op if present.
    report = Path(_local_dir(mc_out)) / "report.md"
    if report.is_file():
        print(f"report already present: {report}", flush=True)
        return
    print("No report.md; re-run mc phase to regenerate.", flush=True)


def _resolve_workdir(requested: str) -> Path:
    """Private work tree — never a world-writable shared /tmp path (S5443)."""
    if requested.strip():
        return Path(_local_dir(Path(requested.strip())))
    # mkdtemp creates a 0o700 directory under the process temp root.
    return Path(tempfile.mkdtemp(prefix="boundary_work_"))


def _phase_bundle(work: Path, results: Path, analysis: Path, s3_campaign: str, s3_analysis: str) -> None:
    _s3_sync(
        s3_campaign.rstrip("/") + "/",
        str(results) + "/",
        exclude=_DEFAULT_EXCLUDE,
    )
    out = analysis / "bundles" / "all"
    run_bundle(work=work, results=results, out=out)
    _s3_cp_recursive(str(out) + "/", s3_analysis.rstrip("/") + _BUNDLES_ALL_SUFFIX)


def _phase_surface(
    work: Path,
    results: Path,
    analysis: Path,
    s3_campaign: str,
    s3_analysis: str,
    pathogen: str | None,
) -> None:
    _s3_sync(
        s3_campaign.rstrip("/") + "/",
        str(results) + "/",
        exclude=_DEFAULT_EXCLUDE,
    )
    out = analysis / "surfaces"
    run_surface(work=work, results=results, out=out, pathogen=pathogen)
    _s3_cp_recursive(str(out) + "/", s3_analysis.rstrip("/") + _SURFACES_SUFFIX)


def _phase_stan(
    work: Path,
    analysis: Path,
    s3_analysis: str,
    pathogen: str,
    chains: int,
    warmup: int,
    sampling: int,
    seed: int,
) -> None:
    safe_pathogen = _require_pathogen(pathogen, required=True) or pathogen
    _s3_sync(
        s3_analysis.rstrip("/") + _BUNDLES_ALL_SUFFIX,
        str(analysis / "all") + "/",
    )
    bundle_dir = analysis / "all"
    if not (bundle_dir / "run_summary.csv").is_file():
        _s3_sync(
            s3_analysis.rstrip("/") + f"/bundles/{safe_pathogen}/",
            str(analysis / safe_pathogen) + "/",
        )
        bundle_dir = analysis / safe_pathogen
    out = analysis / "stan" / safe_pathogen
    run_stan(
        work=work,
        analysis_dir=bundle_dir,
        out=out,
        pathogen=safe_pathogen,
        chains=chains,
        warmup=warmup,
        sampling=sampling,
        seed=seed,
    )
    surf_src = s3_analysis.rstrip("/") + _SURFACES_SUFFIX
    _s3_sync(surf_src, str(out) + "/")
    _s3_cp_recursive(
        str(out) + "/",
        s3_analysis.rstrip("/") + f"/stan/{safe_pathogen}/",
    )


def _phase_mc(
    work: Path,
    analysis: Path,
    s3_analysis: str,
    pathogen: str,
    n_mc: int,
    seed: int,
) -> None:
    safe_pathogen = _require_pathogen(pathogen, required=True) or pathogen
    fit_uri = s3_analysis.rstrip("/") + f"/stan/{safe_pathogen}/"
    local_fit = analysis / "stan" / safe_pathogen
    _s3_sync(fit_uri, str(local_fit) + "/")
    if not (local_fit / "outbreak_surface.json").is_file() and not (
        local_fit / "outbreak_surface.csv"
    ).is_file():
        _s3_sync(
            s3_analysis.rstrip("/") + _SURFACES_SUFFIX,
            str(local_fit) + "/",
        )
    out = analysis / "mc" / safe_pathogen
    run_mc(work=work, stan_fit=local_fit, out=out, n_mc=n_mc, seed=seed)
    _s3_cp_recursive(
        str(out) + "/",
        s3_analysis.rstrip("/") + f"/mc/{safe_pathogen}/",
    )


def _phase_report(analysis: Path, s3_analysis: str, pathogen: str) -> None:
    safe_pathogen = _require_pathogen(pathogen, required=True) or pathogen
    mc_uri = s3_analysis.rstrip("/") + f"/mc/{safe_pathogen}/"
    local_mc = analysis / "mc" / safe_pathogen
    _s3_sync(mc_uri, str(local_mc) + "/")
    run_report(mc_out=local_mc)
    _s3_cp_recursive(
        str(local_mc) + "/",
        s3_analysis.rstrip("/") + f"/mc/{safe_pathogen}/",
    )


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
    p.add_argument(
        "--workdir",
        default="",
        help="Optional private work directory (default: tempfile.mkdtemp)",
    )
    p.add_argument("--chains", type=int, default=4)
    p.add_argument("--iter-warmup", type=int, default=1000)
    p.add_argument("--iter-sampling", type=int, default=1000)
    p.add_argument("--seed", type=int, default=1701)
    p.add_argument("--n-mc", type=int, default=2000)
    args = p.parse_args(argv)

    s3_campaign = _require_s3_uri(args.s3_campaign, label="--s3-campaign")
    s3_analysis = _require_s3_uri(args.s3_analysis, label="--s3-analysis")
    pathogen_opt = _require_pathogen(args.pathogen, required=False)

    work = _resolve_workdir(args.workdir)
    # Anchor path confinement to the resolved work tree for this process.
    os.chdir(work)
    results = work / "results"
    analysis = work / "analysis"
    results.mkdir(exist_ok=True)
    analysis.mkdir(exist_ok=True)

    if args.phase == "bundle":
        _phase_bundle(work, results, analysis, s3_campaign, s3_analysis)
    elif args.phase == "surface":
        _phase_surface(
            work, results, analysis, s3_campaign, s3_analysis, pathogen_opt
        )
    elif args.phase == "stan":
        _phase_stan(
            work,
            analysis,
            s3_analysis,
            pathogen_opt or "",
            args.chains,
            args.iter_warmup,
            args.iter_sampling,
            args.seed,
        )
    elif args.phase == "mc":
        default_pathogen = "noro" + "virus"
        _phase_mc(
            work,
            analysis,
            s3_analysis,
            pathogen_opt or default_pathogen,
            args.n_mc,
            args.seed,
        )
    else:
        default_pathogen = "noro" + "virus"
        _phase_report(analysis, s3_analysis, pathogen_opt or default_pathogen)

    print(f"phase={args.phase} done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
