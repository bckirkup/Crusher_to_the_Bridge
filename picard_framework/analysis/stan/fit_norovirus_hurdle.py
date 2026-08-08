"""Fit the two-stage hurdle: P(outbreak) then trajectory | outbreak.

Usage::

    python3 -m picard_framework.analysis.stan.fit_norovirus_hurdle analysis/ \\
        --out-outbreak stan_fit_outbreak/ --out-trajectory stan_fit_trajectory/
"""

from __future__ import annotations

import argparse
import json
import os

from picard_framework.analysis._io import ensure_out_dir, safe_path, write_json
from picard_framework.analysis.stan._data import DEFAULT_D0, DEFAULT_VSP_REF
from picard_framework.analysis.stan.fit_norovirus_outbreak import (
    fit_model as fit_outbreak,
)
from picard_framework.analysis.stan.fit_norovirus_trajectory import (
    fit_model as fit_trajectory,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Two-stage norovirus hurdle: outbreak + trajectory|outbreak",
    )
    parser.add_argument("analysis_dir", help="Bundle with run_summary + epochs")
    parser.add_argument("--out-dir", default="analysis/hurdle_fit")
    parser.add_argument("--chains-outbreak", type=int, default=4)
    parser.add_argument("--chains-trajectory", type=int, default=4)
    parser.add_argument("--iter-sampling", type=int, default=1000)
    parser.add_argument("--iter-warmup", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1701)
    parser.add_argument("--d0", type=float, default=DEFAULT_D0)
    parser.add_argument("--vsp-ref", type=float, default=DEFAULT_VSP_REF)
    parser.add_argument("--threads-per-chain", type=int, default=4)
    parser.add_argument(
        "--show-progress",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    args = parser.parse_args(argv)

    analysis_dir = safe_path(args.analysis_dir)
    out_root = ensure_out_dir(safe_path(args.out_dir))
    out_a = os.path.join(out_root, "outbreak")
    out_b = os.path.join(out_root, "trajectory")

    print("=== Stage A: P(outbreak) ===", flush=True)
    status_a = fit_outbreak(
        analysis_dir,
        out_a,
        chains=args.chains_outbreak,
        iter_sampling=args.iter_sampling,
        iter_warmup=args.iter_warmup,
        seed=args.seed,
        d0=args.d0,
        vsp_ref=args.vsp_ref,
        show_progress=args.show_progress,
    )

    print("=== Stage B: trajectory | outbreak ===", flush=True)
    status_b = fit_trajectory(
        analysis_dir,
        out_b,
        chains=args.chains_trajectory,
        iter_sampling=args.iter_sampling,
        iter_warmup=args.iter_warmup,
        seed=args.seed + 1,
        d0=args.d0,
        vsp_ref=args.vsp_ref,
        show_progress=args.show_progress,
        outbreaks_only=True,
        threads_per_chain=args.threads_per_chain,
    )

    combined = {
        "status": "ok"
        if status_a.get("status") == "ok" and status_b.get("status") == "ok"
        else "partial",
        "outbreak": {"status": status_a.get("status"), "out": out_a},
        "trajectory": {"status": status_b.get("status"), "out": out_b},
    }
    if status_a.get("status") == "skipped" or status_b.get("status") == "skipped":
        combined["status"] = "skipped"
    write_json(os.path.join(out_root, "fit_status.json"), combined)
    print(json.dumps(combined, indent=2))
    return 0 if combined["status"] in {"ok", "skipped", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
