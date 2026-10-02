#!/usr/bin/env python3
"""Validated JSON readers shared by the diagnostic tools.

``validated_json_load`` collapses the three-call
``resolve_repo_path`` + ``validated_open`` + ``json.load`` idiom every
manifest/spec reader used to repeat; ``gz_json_load`` is the
gzip-compressed cell reader the arm readouts share.
"""

from __future__ import annotations

import gzip
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ),
)

from simulation_utils.paths import (  # noqa: E402
    resolve_repo_path,
    validated_open,
)


def validated_json_load(repo_root: Any, path: Any) -> Any:
    """``json.load`` of *path* confined under *repo_root*.

    Resolves the CLI-supplied path against the repository root and reads
    it through ``validated_open`` so the file must sit inside the root.
    """
    safe = Path(resolve_repo_path(str(repo_root), str(path)))
    with validated_open(
        str(safe), "r",
        allowed_roots=(str(repo_root),), encoding="utf-8",
    ) as handle:
        return json.load(handle)


def gz_json_load(path: Any) -> Any:
    """``json.load`` of a gzip-compressed JSON file."""
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)
