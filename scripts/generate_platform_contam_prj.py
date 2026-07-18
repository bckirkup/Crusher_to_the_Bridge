#!/usr/bin/env python3
"""
generate_platform_contam_prj.py – regenerate ContamW 3.4 bundles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Writes ``contam/platform.prj`` + ``contam/path_map.json`` for the fiction
platforms used in Contam dual-path workflows (Mega Cruise + both
Enterprises). Re-run after editing platform JSON.

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
    "mega_cruise_5000",
    "enterprise_constitution_tos",
    "enterprise_galaxy_tng",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate ContamW 3.4 platform.prj + path_map.json bundles.",
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
