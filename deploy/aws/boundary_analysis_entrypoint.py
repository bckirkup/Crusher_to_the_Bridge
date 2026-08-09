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
import subprocess
import sys
from pathlib import Path
from typing import Sequence
from urllib.parse import urlparse


def _parse_s3(uri: str) -> tuple[str, str]:
    p = urlparse(uri if "://" in uri else f"s3://{uri}")
    if p.scheme != "s3" or not p.netloc:
        raise SystemExit(f"Expected s3://bucket/prefix, got {uri!r}")
    key = p.path.lstrip("/")
    return p.netloc, key


def _s3_sync(src: str, dst: str, *, exclude: Sequence[str] | None = None) -> None:
    cmd = ["aws", "s3", "sync", src, dst]
    for pat in exclude or ():
        cmd.extend(["--exclude", pat])
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd)


def _s3_cp_recursive(src: str, dst: str) -> None:
    cmd = ["aws", "s3", "cp", src, dst, "--recursive"]
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd)


def run_bundle(*, work: Path, results: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "picard_framework.analysis.campaign_bundle",
        str(results),
        "--out",
        str(out),
    ]
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=str(work))


def run_surface(*, work: Path, results: Path, out: Path, pathogen: str | None) -> None:
    out.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "picard_framework.analysis.boundary.export_outbreak_surface",
        str(results),
        "--out",
        str(out / "outbreak_surface.csv"),
    ]
    if pathogen:
        cmd.extend(["--pathogen", pathogen])
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=str(work))


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
    out.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "picard_framework.analysis.stan.fit_boundary_hurdle",
        str(analysis_dir),
        "--out",
        str(out),
        "--pathogen",
        pathogen,
        "--chains",
        str(chains),
        "--iter-warmup",
        str(warmup),
        "--iter-sampling",
        str(sampling),
        "--seed",
        str(seed),
    ]
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=str(work))


def run_mc(*, work: Path, stan_fit: Path, out: Path, n_mc: int, seed: int) -> None:
    out.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "picard_framework.analysis.boundary.run_decision_model",
        "--stan-fit",
        str(stan_fit),
        "--lookup",
        "auto",
        "--n-mc",
        str(n_mc),
        "--seed",
        str(seed),
        "--out",
        str(out),
        "--resume",
    ]
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=str(work))


def run_report(*, work: Path, mc_out: Path) -> None:
    # Decision model already writes report.md; no-op if present.
    report = mc_out / "report.md"
    if report.is_file():
        print(f"report already present: {report}", flush=True)
        return
    print("No report.md; re-run mc phase to regenerate.", flush=True)


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
    p.add_argument("--workdir", default="/tmp/boundary_work")
    p.add_argument("--chains", type=int, default=4)
    p.add_argument("--iter-warmup", type=int, default=1000)
    p.add_argument("--iter-sampling", type=int, default=1000)
    p.add_argument("--seed", type=int, default=1701)
    p.add_argument("--n-mc", type=int, default=2000)
    args = p.parse_args(argv)

    if not args.s3_campaign or not args.s3_analysis:
        raise SystemExit("--s3-campaign and --s3-analysis (or env) are required")

    work = Path(args.workdir)
    work.mkdir(parents=True, exist_ok=True)
    results = work / "results"
    analysis = work / "analysis"
    results.mkdir(exist_ok=True)
    analysis.mkdir(exist_ok=True)

    # Download inputs as needed
    if args.phase == "bundle":
        _s3_sync(
            args.s3_campaign.rstrip("/") + "/",
            str(results) + "/",
            exclude=("analysis/*", "_resume/*", "_ops/*"),
        )
        out = analysis / "bundles" / "all"
        run_bundle(work=work, results=results, out=out)
        _s3_cp_recursive(
            str(out) + "/",
            args.s3_analysis.rstrip("/") + "/bundles/all/",
        )
    elif args.phase == "surface":
        _s3_sync(
            args.s3_campaign.rstrip("/") + "/",
            str(results) + "/",
            exclude=("analysis/*", "_resume/*", "_ops/*"),
        )
        out = analysis / "surfaces"
        run_surface(
            work=work,
            results=results,
            out=out,
            pathogen=args.pathogen or None,
        )
        _s3_cp_recursive(str(out) + "/", args.s3_analysis.rstrip("/") + "/surfaces/")
    elif args.phase == "stan":
        if not args.pathogen:
            raise SystemExit("--pathogen required for stan phase")
        # Prefer combined bundle; fall back to per-pathogen prefix if present.
        _s3_sync(
            args.s3_analysis.rstrip("/") + "/bundles/all/",
            str(analysis / "all") + "/",
        )
        bundle_dir = analysis / "all"
        if not (bundle_dir / "run_summary.csv").is_file():
            _s3_sync(
                args.s3_analysis.rstrip("/") + f"/bundles/{args.pathogen}/",
                str(analysis / args.pathogen) + "/",
            )
            bundle_dir = analysis / args.pathogen
        out = analysis / "stan" / args.pathogen
        run_stan(
            work=work,
            analysis_dir=bundle_dir,
            out=out,
            pathogen=args.pathogen,
            chains=args.chains,
            warmup=args.iter_warmup,
            sampling=args.iter_sampling,
            seed=args.seed,
        )
        # Also stage surface next to fit for MC --lookup auto
        surf_src = args.s3_analysis.rstrip("/") + "/surfaces/"
        _s3_sync(surf_src, str(out) + "/")
        _s3_cp_recursive(
            str(out) + "/",
            args.s3_analysis.rstrip("/") + f"/stan/{args.pathogen}/",
        )
    elif args.phase == "mc":
        pathogen = args.pathogen or "norovirus"
        fit_uri = args.s3_analysis.rstrip("/") + f"/stan/{pathogen}/"
        local_fit = analysis / "stan" / pathogen
        _s3_sync(fit_uri, str(local_fit) + "/")
        # Prefer empirical surface if Stan dir lacks outbreak_surface
        if not (local_fit / "outbreak_surface.json").is_file() and not (
            local_fit / "outbreak_surface.csv"
        ).is_file():
            _s3_sync(
                args.s3_analysis.rstrip("/") + "/surfaces/",
                str(local_fit) + "/",
            )
        out = analysis / "mc" / pathogen
        run_mc(
            work=work,
            stan_fit=local_fit,
            out=out,
            n_mc=args.n_mc,
            seed=args.seed,
        )
        _s3_cp_recursive(
            str(out) + "/",
            args.s3_analysis.rstrip("/") + f"/mc/{pathogen}/",
        )
    else:
        pathogen = args.pathogen or "norovirus"
        mc_uri = args.s3_analysis.rstrip("/") + f"/mc/{pathogen}/"
        local_mc = analysis / "mc" / pathogen
        _s3_sync(mc_uri, str(local_mc) + "/")
        run_report(work=work, mc_out=local_mc)
        _s3_cp_recursive(
            str(local_mc) + "/",
            args.s3_analysis.rstrip("/") + f"/mc/{pathogen}/",
        )

    print(f"phase={args.phase} done", flush=True)
    return 0


if __name__ == "__main__":
    # Allow import without tempfile unused
    raise SystemExit(main())
