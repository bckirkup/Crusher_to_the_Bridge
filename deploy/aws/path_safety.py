"""Shared CWD-confined path helpers for AWS campaign CLI tools.

Keeps agent/CLI path arguments inside the process working directory
(Sonar S8707 / S2083). Prefer importing from here instead of redefining
``_cwd_root`` / ``safe_path`` in each script.
"""

from __future__ import annotations

import os
from pathlib import Path

from simulation_utils.paths import confine_to_base


def cwd_root() -> str:
    """Real path of the current working directory."""
    return os.path.realpath(os.getcwd())


def safe_path(path: Path | str) -> str:
    """Resolve ``path`` and confine it to the current working directory.

    Prevents a caller (e.g. an automated agent passing crafted CLI arguments)
    from reading or writing files outside the directory the tool was invoked
    from. Follows canonicalize-then-validate order (Sonar S8707).
    """
    try:
        return confine_to_base(cwd_root(), str(path))
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
