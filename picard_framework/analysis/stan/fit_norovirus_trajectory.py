"""Fit the Phase-1b norovirus trajectory Stan model (Stage B | outbreak).

Usage::

    python3 -m picard_framework.analysis.stan.fit_norovirus_trajectory analysis/ --out stan_fit/
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from picard_framework.analysis._io import (
    allowed_roots,
    ensure_out_dir,
    safe_path,
    write_json,
)
from picard_framework.analysis.stan._data import (
    DEFAULT_D0,
    DEFAULT_VSP_REF,
    build_trajectory_stan_data,
    cmdstan_available,
    filter_norovirus_runs,
    filter_outbreak_runs,
    read_csv,
    read_epoch_table,
)
from picard_framework.analysis.stan.posterior_summaries import summarize_fit
from simulation_utils.paths import validated_open

FIT_STATUS_FILENAME = "fit_status.json"

# Back-compat for tests / external callers
build_stan_data = build_trajectory_stan_data



def fit_model(
    analysis_dir: str,
    out_dir: str,
    *,
    chains: int = 2,
    iter_sampling: int = 200,
    iter_warmup: int = 200,
    seed: int = 42,
    d0: float = DEFAULT_D0,
    vsp_ref: float = DEFAULT_VSP_REF,
    show_progress: bool = True,
    outbreaks_only: bool = True,
    threads_per_chain: int = 4,
    grainsize: int | None = None,
) -> dict[str, Any]:
    """Compile/fit trajectory model and write posterior summaries."""
    analysis_dir = safe_path(analysis_dir)
    out = ensure_out_dir(out_dir)

    run_rows = read_csv(os.path.join(analysis_dir, "run_summary.csv"))
    epoch_rows = read_epoch_table(analysis_dir)
    data, meta = build_trajectory_stan_data(
        run_rows,
        epoch_rows,
        d0=d0,
        vsp_ref=vsp_ref,
        outbreaks_only=outbreaks_only,
        grainsize=grainsize,
    )

    write_json(os.path.join(out, "stan_data_meta.json"), meta)
    write_json(
        os.path.join(out, "stan_data_shapes.json"),
        {
            "N_runs": data["N_runs"],
            "T": data["T"],
            "P": data["P"],
            "S": data["S"],
            "grainsize": data["grainsize"],
            "outbreaks_only": outbreaks_only,
            "platforms": meta["platforms"],
            "surveillances": meta["surveillances"],
        },
    )
    print(
        f"[trajectory] Stan data: N_runs={data['N_runs']} T={data['T']} "
        f"P={data['P']} S={data['S']} grainsize={data['grainsize']} "
        f"outbreaks_only={outbreaks_only}",
        flush=True,
    )

    if not cmdstan_available():
        write_json(
            os.path.join(out, FIT_STATUS_FILENAME),
            {
                "status": "skipped",
                "reason": "cmdstanpy/CmdStan not installed",
                "hint": "pip install 'crusher-to-the-bridge[analysis]' && "
                "python -c 'import cmdstanpy; cmdstanpy.install_cmdstan()'",
            },
        )
        print("CmdStan not available; wrote metadata only.", file=sys.stderr)
        return {"status": "skipped", "meta": meta}

    from cmdstanpy import CmdStanModel

    stan_file = os.path.join(os.path.dirname(__file__), "norovirus_trajectory.stan")
    try:
        model = CmdStanModel(stan_file=stan_file)
        print(
            f"[trajectory] Sampling: chains={chains} threads/chain={threads_per_chain} "
            f"warmup={iter_warmup} sampling={iter_sampling} seed={seed} …",
            flush=True,
        )
        fit = model.sample(
            data=data,
            chains=chains,
            parallel_chains=chains,
            threads_per_chain=threads_per_chain,
            iter_sampling=iter_sampling,
            iter_warmup=iter_warmup,
            seed=seed,
            show_progress=show_progress,
        )
    except Exception as exc:
        write_json(
            os.path.join(out, FIT_STATUS_FILENAME),
            {"status": "error", "reason": str(exc), "meta": meta},
        )
        print(f"[trajectory] fit failed: {exc}", file=sys.stderr)
        return {"status": "error", "meta": meta, "error": str(exc)}

    draws_path = os.path.join(out, "draws.csv")
    try:
        import io

        buf = io.StringIO()
        fit.draws_pd().to_csv(buf, index=False)
        with validated_open(
            draws_path, "w", allowed_roots=allowed_roots(), encoding="utf-8"
        ) as fh:
            fh.write(buf.getvalue())
    except Exception:
        # Continue when optional draw serialization cannot be written.
        pass

    noro = filter_norovirus_runs(run_rows)
    summary_rows = filter_outbreak_runs(noro) if outbreaks_only else noro
    artifacts = summarize_fit(
        fit=fit,
        meta=meta,
        out_dir=out,
        run_summary_rows=summary_rows,
    )
    status = {"status": "ok", "artifacts": artifacts, "meta": meta}
    write_json(os.path.join(out, FIT_STATUS_FILENAME), status)
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fit norovirus_trajectory.stan (Stage B | outbreak)",
    )
    parser.add_argument("analysis_dir", help="Bundle directory from campaign_bundle")
    parser.add_argument("--out", default="stan_fit_trajectory")
    parser.add_argument("--chains", type=int, default=2)
    parser.add_argument("--iter-sampling", type=int, default=200)
    parser.add_argument("--iter-warmup", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--d0", type=float, default=DEFAULT_D0)
    parser.add_argument("--vsp-ref", type=float, default=DEFAULT_VSP_REF)
    parser.add_argument("--threads-per-chain", type=int, default=4)
    parser.add_argument("--grainsize", type=int, default=None)
    parser.add_argument(
        "--outbreaks-only",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fit only outbreak_occurred runs (hurdle Stage B; default on)",
    )
    parser.add_argument(
        "--show-progress",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    args = parser.parse_args(argv)

    result = fit_model(
        args.analysis_dir,
        args.out,
        chains=args.chains,
        iter_sampling=args.iter_sampling,
        iter_warmup=args.iter_warmup,
        seed=args.seed,
        d0=args.d0,
        vsp_ref=args.vsp_ref,
        show_progress=args.show_progress,
        outbreaks_only=args.outbreaks_only,
        threads_per_chain=args.threads_per_chain,
        grainsize=args.grainsize,
    )
    print(json.dumps({"status": result.get("status"), "out": args.out}))
    return 0 if result.get("status") in {"ok", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
