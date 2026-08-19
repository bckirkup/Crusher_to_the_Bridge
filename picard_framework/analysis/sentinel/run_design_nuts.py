"""CLI for Engine C Sentinel CmdStan NUTS ladder cells and aggregation."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from picard_framework.analysis._io import ensure_out_dir, safe_path, write_csv, write_json
from picard_framework.analysis.sentinel.design_nuts import (
    aggregate_cells,
    load_ladder,
    run_cell,
)

_NUTS_RUNG_FIELDS = [
    "rung",
    "n_cells",
    "n_clean",
    "clean_fraction",
    "coverage_ratio",
    "calibration_factor_r",
    "reliable",
    "coverage_gate",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ladder", default=None)
    parser.add_argument("--rung")
    parser.add_argument("--ratio", type=float)
    parser.add_argument("--replicate", type=int, default=0)
    parser.add_argument("--aggregate")
    parser.add_argument("--out", default="tmp_nuts_out")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--chains", type=int)
    parser.add_argument("--warmup", type=int)
    parser.add_argument("--sampling", type=int)
    parser.add_argument("--adapt-delta", type=float)
    parser.add_argument("--max-treedepth", type=int)
    parser.add_argument("--seed", type=int)
    return parser


def _cell_path(out: str, payload: dict[str, Any]) -> str:
    name = f"cell_{payload['rung']}_ratio_{payload['true_hot_ratio']:g}_rep_{payload['replicate']}.json"
    return os.path.join(out, name)


def _dump_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _write_aggregate(out: str, directory: str, ladder: dict[str, Any]) -> None:
    payload = aggregate_cells(directory, ladder)
    write_json(os.path.join(out, "nuts_aggregate.json"), payload)
    write_csv(os.path.join(out, "nuts_rungs.csv"), payload["rungs"], _NUTS_RUNG_FIELDS)
    _dump_json(payload)


def _write_cell(out: str, args: argparse.Namespace, ladder: dict[str, Any]) -> None:
    payload = run_cell(
        ladder,
        rung_id=args.rung,
        ratio=args.ratio,
        replicate=args.replicate,
        chains=args.chains,
        iter_warmup=args.warmup,
        iter_sampling=args.sampling,
        adapt_delta=args.adapt_delta,
        max_treedepth=args.max_treedepth,
        seed=args.seed,
        smoke=args.smoke,
    )
    write_json(_cell_path(out, payload), payload)
    _dump_json(payload)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = ensure_out_dir(args.out)
    ladder = load_ladder(safe_path(args.ladder) if args.ladder else None)
    if not args.aggregate:
        if args.smoke and not args.rung:
            args.rung = "C1"
            args.ratio = 2.0
        if not args.rung or args.ratio is None:
            print(
                "--rung and --ratio are required unless --aggregate is used",
                file=sys.stderr,
            )
            return 2
        _write_cell(out, args, ladder)
    else:
        _write_aggregate(out, safe_path(args.aggregate), ladder)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
