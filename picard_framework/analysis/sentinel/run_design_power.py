"""CLI for sentinel design-stage power and precision projections."""

from __future__ import annotations

import argparse
import os
from typing import Any

from picard_framework.analysis._io import ensure_out_dir, safe_path, write_csv, write_json
from picard_framework.analysis.sentinel.design_power import (
    DEFAULT_ALPHA,
    DEFAULT_DRAWS,
    DEFAULT_POWER,
    DEFAULT_REPLICATES,
    DEFAULT_WARMUP,
    SMOKE_DRAWS,
    SMOKE_REPLICATES,
    SMOKE_WARMUP,
    ceiling_projection,
    fit_projection,
    load_design,
    scaling_sweep,
)

SWEEP_VALUES = {"weeks": (4, 12, 26, 52), "calls": (2, 3, 4, 5)}
CSV_COLUMNS = (
    "design", "dimension", "value", "sd_log_lambda_hot", "width90_log_lambda",
    "sd_log_ratio", "mdhr", "provenance",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", default="caribbean")
    parser.add_argument("--presets-file", default=None)
    parser.add_argument("--engine", choices=("ceiling", "fit", "both"), default="both")
    parser.add_argument("--sweep", default="ships,weeks,calls")
    parser.add_argument("--out", default="tmp_design_power_out")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--alpha", type=float, default=DEFAULT_ALPHA)
    parser.add_argument("--power", type=float, default=DEFAULT_POWER)
    parser.add_argument("--replicates", type=int, default=DEFAULT_REPLICATES)
    parser.add_argument("--draws", type=int, default=DEFAULT_DRAWS)
    parser.add_argument("--warmup", type=int, default=DEFAULT_WARMUP)
    parser.add_argument("--seed", type=int, default=1701)
    return parser


def _run(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    design = load_design(args.preset, safe_path(args.presets_file) if args.presets_file else None)
    draws = SMOKE_DRAWS if args.smoke else args.draws
    warmup = SMOKE_WARMUP if args.smoke else args.warmup
    replicates = SMOKE_REPLICATES if args.smoke else args.replicates
    payload: dict[str, Any] = {"preset": design.name, "caveats": []}
    if args.engine in ("ceiling", "both"):
        payload["ceiling"] = ceiling_projection(design, alpha=args.alpha, power=args.power)
    if args.engine in ("fit", "both"):
        payload["fit"] = fit_projection(
            design,
            draws=draws,
            warmup=warmup,
            replicates=replicates,
            seed=args.seed,
            alpha=args.alpha,
            power=args.power,
        )
    payload["caveats"] = (
        payload.get("ceiling", {}).get("caveats")
        or payload.get("fit", {}).get("caveats")
        or []
    )
    sweeps = {}
    for dimension in (part.strip() for part in args.sweep.split(",") if part.strip()):
        values = SWEEP_VALUES.get(dimension)
        if dimension == "ships":
            values = tuple(
                max(1, round(design.n_ships * multiplier))
                for multiplier in (0.125, 0.25, 0.5, 1.0, 2.0)
            )
        if values is None:
            raise ValueError(f"unknown sweep dimension: {dimension}")
        sweeps[dimension] = scaling_sweep(
            design,
            dimension,
            values,
            alpha=args.alpha,
            power=args.power,
        )
    return payload, sweeps


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = ensure_out_dir(args.out)
    payload, sweeps = _run(args)
    write_json(os.path.join(out, "design_power.json"), payload)
    for dimension, rows in sweeps.items():
        write_csv(os.path.join(out, f"scaling_{dimension}.csv"), rows, CSV_COLUMNS)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
