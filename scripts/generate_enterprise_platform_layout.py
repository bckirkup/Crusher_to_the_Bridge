#!/usr/bin/env python3
"""Generate Enterprise cabin-corridor layouts from enterprise_platform_recipes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from enterprise_platform_recipes import RECIPES  # noqa: E402
from generate_cruise_platform_layout import write_platform  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--platform",
        required=True,
        choices=sorted(RECIPES.keys()),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    write_platform(RECIPES[args.platform], dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
