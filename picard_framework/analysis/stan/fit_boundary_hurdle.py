"""Fit boundary-pipeline two-stage hurdle (Bernoulli + Beta-AR).

Usage::

    python3 -m picard_framework.analysis.stan.fit_boundary_hurdle analysis/ \\
      --out analysis/stan/norovirus --pathogen norovirus
"""
from __future__ import annotations

import argparse
import io
import os
import sys
from typing import Any

from picard_framework.analysis._io import (
    allowed_roots,
    ensure_out_dir,
    safe_path,
    write_csv,
    write_json,
)
from picard_framework.analysis.stan._boundary_data import (
    DEFAULT_D0,
    build_boundary_ar_stan_data,
    build_boundary_outbreak_stan_data,
    cmdstan_available,
    read_csv,
)
from simulation_utils.paths import validated_open

_FIT_STATUS_JSON = "fit_status.json"


def _write_draws(fit: Any, path: str) -> None:
    try:
        buf = io.StringIO()
        fit.draws_pd().to_csv(buf, index=False)
        with validated_open(
            path, "w", allowed_roots=allowed_roots(), encoding="utf-8"
        ) as fh:
            fh.write(buf.getvalue())
    except Exception as exc:
        print(f"warn: could not write draws: {exc}", file=sys.stderr)


def _platform_effects(fit: Any, meta: dict[str, Any], out_csv: str) -> None:
    try:
        draws = fit.draws_pd()
    except Exception:
        return
    rows: list[dict[str, Any]] = []
    for i, name in enumerate(meta.get("platforms") or []):
        col = f"alpha_platform[{i + 1}]"
        if col not in draws.columns:
            continue
        series = draws[col]
        rows.append(
            {
                "platform": name,
                "mean": float(series.mean()),
                "q05": float(series.quantile(0.05)),
                "q50": float(series.quantile(0.50)),
                "q95": float(series.quantile(0.95)),
            }
        )
    if rows:
        write_csv(
            out_csv,
            rows,
            ["platform", "mean", "q05", "q50", "q95"],
        )


def _fit_stage(
    *,
    stan_file: str,
    data: dict[str, Any],
    meta: dict[str, Any],
    out_dir: str,
    chains: int,
    iter_warmup: int,
    iter_sampling: int,
    seed: int,
    show_progress: bool,
    stage_name: str,
) -> dict[str, Any]:
    stage_out = ensure_out_dir(os.path.join(out_dir, stage_name))
    write_json(os.path.join(stage_out, "stan_data_meta.json"), meta)
    if not cmdstan_available():
        status = {
            "status": "skipped",
            "reason": "cmdstanpy/CmdStan not installed",
            "meta": meta,
        }
        write_json(os.path.join(stage_out, _FIT_STATUS_JSON), status)
        return status

    from cmdstanpy import CmdStanModel

    try:
        model = CmdStanModel(stan_file=stan_file)
        print(
            f"[{stage_name}] Sampling chains={chains} "
            f"warmup={iter_warmup} sampling={iter_sampling} …",
            flush=True,
        )
        fit = model.sample(
            data=data,
            chains=chains,
            parallel_chains=chains,
            iter_sampling=iter_sampling,
            iter_warmup=iter_warmup,
            seed=seed,
            show_progress=show_progress,
        )
    except Exception as exc:
        status = {"status": "error", "reason": str(exc), "meta": meta}
        write_json(os.path.join(stage_out, _FIT_STATUS_JSON), status)
        print(f"[{stage_name}] fit failed: {exc}", file=sys.stderr)
        return status

    _write_draws(fit, os.path.join(stage_out, "draws.csv"))
    _platform_effects(
        fit, meta, os.path.join(stage_out, "platform_effects.csv"),
    )
    status = {"status": "ok", "meta": meta}
    write_json(os.path.join(stage_out, _FIT_STATUS_JSON), status)
    return status


def fit_boundary_hurdle(
    analysis_dir: str,
    out_dir: str,
    *,
    pathogen: str,
    chains: int = 4,
    iter_sampling: int = 1000,
    iter_warmup: int = 1000,
    seed: int = 1701,
    d0: float = DEFAULT_D0,
    show_progress: bool = True,
) -> dict[str, Any]:
    analysis_dir = safe_path(analysis_dir)
    out = ensure_out_dir(out_dir)
    run_rows = read_csv(os.path.join(analysis_dir, "run_summary.csv"))

    stan_dir = os.path.dirname(__file__)
    outbreak_data, outbreak_meta = build_boundary_outbreak_stan_data(
        run_rows, pathogen=pathogen, d0=d0,
    )
    a_status = _fit_stage(
        stan_file=os.path.join(stan_dir, "boundary_outbreak.stan"),
        data=outbreak_data,
        meta=outbreak_meta,
        out_dir=out,
        chains=chains,
        iter_warmup=iter_warmup,
        iter_sampling=iter_sampling,
        seed=seed,
        show_progress=show_progress,
        stage_name="outbreak",
    )

    ar_data, ar_meta = build_boundary_ar_stan_data(
        run_rows, pathogen=pathogen, d0=d0, outbreaks_only=True,
    )
    b_status = _fit_stage(
        stan_file=os.path.join(stan_dir, "boundary_ar.stan"),
        data=ar_data,
        meta=ar_meta,
        out_dir=out,
        chains=chains,
        iter_warmup=iter_warmup,
        iter_sampling=iter_sampling,
        seed=seed + 1,
        show_progress=show_progress,
        stage_name="ar",
    )

    summary = {
        "status": "ok"
        if a_status.get("status") == "ok" and b_status.get("status") == "ok"
        else "partial",
        "pathogen": pathogen,
        "outbreak": a_status,
        "ar": b_status,
    }
    write_json(os.path.join(out, _FIT_STATUS_JSON), summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Boundary hurdle: Bernoulli outbreak + Beta-AR | outbreak",
    )
    parser.add_argument("analysis_dir")
    parser.add_argument("--out", default="boundary_hurdle_fit")
    parser.add_argument(
        "--pathogen",
        required=True,
        help="norovirus | sarscov2 | influenza | measles",
    )
    parser.add_argument("--chains", type=int, default=4)
    parser.add_argument("--iter-sampling", type=int, default=1000)
    parser.add_argument("--iter-warmup", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1701)
    parser.add_argument("--d0", type=float, default=DEFAULT_D0)
    parser.add_argument(
        "--show-progress",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    args = parser.parse_args(argv)
    status = fit_boundary_hurdle(
        args.analysis_dir,
        args.out,
        pathogen=args.pathogen,
        chains=args.chains,
        iter_sampling=args.iter_sampling,
        iter_warmup=args.iter_warmup,
        seed=args.seed,
        d0=args.d0,
        show_progress=args.show_progress,
    )
    print(status.get("status"), flush=True)
    return 0 if status.get("status") in {"ok", "skipped", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
