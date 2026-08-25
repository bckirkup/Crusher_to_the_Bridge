"""CLI: write one run's phylodynamic report.

``python3 -m picard_framework.analysis.phylodynamics RUN_DIR_OR_ZIP --out DIR``
"""

from __future__ import annotations

import argparse
import json
import sys

from picard_framework.analysis.phylodynamics.report import (
    DEFAULT_CURVE_POINTS,
    MissingCensusError,
    write_report,
)


def main(argv: list[str] | None = None) -> int:
    """Entry point; ``2`` when the run carries no lineage census."""
    parser = argparse.ArgumentParser(prog="phylodynamics")
    parser.add_argument("source", help="run directory or campaign result zip")
    parser.add_argument("--out", required=True, help="output directory")
    parser.add_argument(
        "--curve-points",
        type=int,
        default=DEFAULT_CURVE_POINTS,
        help="points on the detection-speed hour grid",
    )
    args = parser.parse_args(argv)
    try:
        result = write_report(
            args.source, args.out, curve_points=args.curve_points,
        )
    except MissingCensusError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI shim
    raise SystemExit(main())
