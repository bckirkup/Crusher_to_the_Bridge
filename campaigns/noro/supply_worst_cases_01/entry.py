#!/usr/bin/env python3
"""Campaign argv hook: pin PYTHONHASHSEED and reuse the stock tier worker."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_AWS_DIR = _REPO_ROOT / "deploy" / "aws"
for _path in (str(_REPO_ROOT), str(_AWS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)


def build_argv(
    args: Any, block: dict[str, Any], seed: int, out_dir: Path,
) -> tuple[list[str], Path]:
    # campaign_entrypoint spawns the worker with this process environment.
    os.environ["PYTHONHASHSEED"] = "1"
    import campaign_entrypoint  # noqa: E402

    return campaign_entrypoint._default_argv({}, block, seed, out_dir, args)
