#!/usr/bin/env python3
"""
generate_platform_contam_prj.py – FICTION BOOTSTRAP only
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Synthesize ContamW 3.4 ``contam/platform.prj`` + ``path_map.json`` from
platform JSON for **fiction ships that have no authentic Contam model**
(Mega Cruise, Enterprises, destroyer demos).

The primary Contam product loop is the opposite direction:

    authentic .prj  ──Path A──► ContamX airflow ──► Crusher mass balance
                └──Path B──► simplify → JSON (+ path_map) → native engine

Re-run this script only after editing fiction platform JSON, or when
 ContamW export grammar changes.

Usage::

    python3 scripts/generate_platform_contam_prj.py
    python3 scripts/generate_platform_contam_prj.py --platform destroyer_baseline
"""

from __future__ import annotations

import argparse
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.contam_prj_bridge import export_platform_to_prj  # noqa: E402

DEFAULT_PLATFORMS = (
    "destroyer_baseline",
    "mega_cruise_5000",
    "enterprise_constitution_tos",
    "enterprise_galaxy_tng",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "FICTION BOOTSTRAP: synthesize ContamW 3.4 platform.prj + "
            "path_map.json from JSON (not the primary Contam workflow)."
        ),
    )
    parser.add_argument(
        "--platform",
        action="append",
        dest="platforms",
        help="Platform id under data/platforms/ (repeatable). "
             f"Default: {', '.join(DEFAULT_PLATFORMS)}",
    )
    args = parser.parse_args(argv)
    platforms = args.platforms or list(DEFAULT_PLATFORMS)

    print("Fiction bootstrap (JSON→PRJ). Prefer authentic .prj + --simplify.")
    for name in platforms:
        platform_dir = os.path.join(REPO_ROOT, "data", "platforms", name)
        out = os.path.join(platform_dir, "contam", "platform.prj")
        if not os.path.isdir(platform_dir):
            print(f"  SKIP missing platform: {name}")
            continue
        written = export_platform_to_prj(platform_dir, out, write_path_map=True)
        print(f"  Wrote {written}")
        print(f"  Wrote {os.path.join(os.path.dirname(written), 'path_map.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
