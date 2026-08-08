"""Fit the Phase-1b norovirus outbreak-probability Stan model (Stage A).

Usage::

    python3 -m picard_framework.analysis.stan.fit_norovirus_outbreak analysis/ --out stan_fit_outbreak/
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
    build_outbreak_stan_data,
    cmdstan_available,
    filter_norovirus_runs,
    read_csv,
)
from picard_framework.analysis.stan.posterior_summaries import summarize_outbreak_fit
from simulation_utils.paths import validated_open


def fit_model(
    analysis_dir: str,
    out_dir: str,
    *,
    chains: int = 4,
    iter_sampling: int = 1000,
    iter_warmup: int = 1000,
    seed: int = 1701,
    d0: float = DEFAULT_D0,
    vsp_ref: float = DEFAULT_VSP_REF,
    show_progress: bool = True,
) -> dict[str, Any]:
    """Compile/fit outbreak Bernoulli model and write posterior summaries."""
    analysis_dir = safe_path(analysis_dir)
    out = ensure_out_dir(out_dir)

    run_rows = read_csv(os.path.join(analysis_dir, "run_summary.csv"))
    data, meta = build_outbreak_stan_data(run_rows, d0=d0, vsp_ref=vsp_ref)

    write_json(os.path.join(out, "stan_data_meta.json"), meta)
    write_json(
        os.path.join(out, "stan_data_shapes.json"),
        {
            "N_runs": data["N_runs"],
            "P": data["P"],
            "S": data["S"],
            "n_outbreaks": meta["n_outbreaks"],
            "outbreak_rate": meta["outbreak_rate"],
            "platforms": meta["platforms"],
            "surveillances": meta["surveillances"],
        },
    )
    print(
        f"[outbreak] Stan data: N_runs={data['N_runs']} "
        f"outbreaks={meta['n_outbreaks']} rate={meta['outbreak_rate']} "
        f"P={data['P']} S={data['S']}",
        flush=True,
    )

    if not cmdstan_available():
        write_json(
            os.path.join(out, "fit_status.json"),
            {
                "status": "skipped",
                "reason": "cmdstanpy/CmdStan not installed",
            },
        )
        print("CmdStan not available; wrote metadata only.", file=sys.stderr)
        return {"status": "skipped", "meta": meta}

    from cmdstanpy import CmdStanModel

    stan_file = os.path.join(os.path.dirname(__file__), "norovirus_outbreak.stan")
    try:
        model = CmdStanModel(stan_file=stan_file)
        print(
            f"[outbreak] Sampling: chains={chains} warmup={iter_warmup} "
            f"sampling={iter_sampling} seed={seed} …",
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
        write_json(
            os.path.join(out, "fit_status.json"),
            {"status": "error", "reason": str(exc), "meta": meta},
        )
        print(f"[outbreak] fit failed: {exc}", file=sys.stderr)
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
        pass

    artifacts = summarize_outbreak_fit(
        fit=fit,
        meta=meta,
        out_dir=out,
        run_summary_rows=filter_norovirus_runs(run_rows),
    )
    status = {"status": "ok", "artifacts": artifacts, "meta": meta}
    write_json(os.path.join(out, "fit_status.json"), status)
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fit norovirus_outbreak.stan (Stage A / P(outbreak))",
    )
    parser.add_argument("analysis_dir")
    parser.add_argument("--out", default="stan_fit_outbreak")
    parser.add_argument("--chains", type=int, default=4)
    parser.add_argument("--iter-sampling", type=int, default=1000)
    parser.add_argument("--iter-warmup", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1701)
    parser.add_argument("--d0", type=float, default=DEFAULT_D0)
    parser.add_argument("--vsp-ref", type=float, default=DEFAULT_VSP_REF)
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
    )
    print(json.dumps({"status": result.get("status"), "out": args.out}))
    return 0 if result.get("status") in {"ok", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
