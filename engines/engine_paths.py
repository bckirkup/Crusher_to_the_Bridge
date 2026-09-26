"""
engines.engine_paths
~~~~~~~~~~~~~~~~~~~~~

Path registry for the five sibling simulation repositories.  Importing this
module has no side effects.  :func:`engine_import_paths` reports which of the
registered Python directories exist on disk; an entrypoint that wants them on
``sys.path`` opts in explicitly with :func:`register_engine_paths` (appends,
never prepends) or the scoped :func:`registered_engine_paths` context manager.

Layout assumption::

    repos/
    ├── Crusher_to_the_Bridge/   ← this repo (project root)
    ├── infection-dynamics/       ← Korkin Lab ABM (Java / R)
    ├── py-contam/                ← NIST CONTAM wrapper (Python)
    ├── EMOD-Generic/             ← IDM clinical diagnostics (C++ / Python)
    ├── FRED/                     ← CMU compliance model (C++ / R)
    └── GRUMB/                    ← Genome-resolved metagenomics (Python / R)

Non-Python engines (infection-dynamics, FRED) are registered for path
reference only — their primary interfaces are subprocess / JSON based.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

# ── Resolve workspace root (parent of this repo) ────────────────────────
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
_WORKSPACE_ROOT = os.path.dirname(_PROJECT_ROOT)

# ── Engine registry ─────────────────────────────────────────────────────
# Each entry maps an engine name to:
#   repo_dir  – absolute path to the repo root
#   py_paths  – subdirectories to add to sys.path (Python-importable)
#   language  – primary language (for reference)
#   role      – one-line description

ENGINE_REGISTRY: dict[str, dict[str, Any]] = {
    "infection-dynamics": {
        "repo_dir": os.path.join(_WORKSPACE_ROOT, "infection-dynamics"),
        "py_paths": [],
        "language": "Java / R",
        "role": "Korkin Lab agent-based outbreak model (Norwalk / COVID-19)",
    },
    "py-contam": {
        "repo_dir": os.path.join(_WORKSPACE_ROOT, "py-contam"),
        "py_paths": [
            os.path.join(_WORKSPACE_ROOT, "py-contam", "python"),
        ],
        "language": "Python",
        "role": "NIST CONTAM airflow automation wrapper",
    },
    "EMOD-Generic": {
        "repo_dir": os.path.join(_WORKSPACE_ROOT, "EMOD-Generic"),
        "py_paths": [
            os.path.join(_WORKSPACE_ROOT, "EMOD-Generic", "Scripts"),
            os.path.join(_WORKSPACE_ROOT, "EMOD-Generic", "Regression"),
        ],
        "language": "C++ / Python",
        "role": "IDM reference architecture for clinical diagnostics",
    },
    "FRED": {
        "repo_dir": os.path.join(_WORKSPACE_ROOT, "FRED"),
        "py_paths": [],
        "language": "C++ / R",
        "role": "CMU reference architecture for human compliance / behavioral rules",
    },
    "GRUMB": {
        "repo_dir": os.path.join(_WORKSPACE_ROOT, "GRUMB"),
        "py_paths": [
            os.path.join(_WORKSPACE_ROOT, "GRUMB"),
            os.path.join(_WORKSPACE_ROOT, "GRUMB", "04_Machine_Learning"),
            os.path.join(_WORKSPACE_ROOT, "GRUMB", "perspective_simulations"),
        ],
        "language": "Python / R",
        "role": "Genome-resolved metagenomics framework (CLR, blending, MDC)",
    },
}


def get_engine_path(engine_name: str) -> str:
    """Return the absolute repo directory for *engine_name*.

    Raises ``KeyError`` if the engine is not in the registry.
    """
    return ENGINE_REGISTRY[engine_name]["repo_dir"]


def engine_import_paths(
    engines: list[str] | None = None,
    verbose: bool = False,
) -> tuple[dict[str, bool], list[str]]:
    """Report sibling-repo presence and the Python directories they expose.

    Pure query: nothing is mutated.

    Parameters
    ----------
    engines:
        Engine names to inspect.  ``None`` (default) inspects all.
    verbose:
        If ``True``, print each engine's status.

    Returns
    -------
    tuple
        ``(status, paths)`` where ``status`` maps engine name → bool (repo
        directory exists on disk) and ``paths`` lists, in registry order,
        the existing Python-importable directories of the present engines.
    """
    targets = engines if engines is not None else list(ENGINE_REGISTRY.keys())
    status: dict[str, bool] = {}
    paths: list[str] = []

    for name in targets:
        entry = ENGINE_REGISTRY.get(name)
        if entry is None:
            status[name] = False
            continue

        repo_exists = os.path.isdir(entry["repo_dir"])
        status[name] = repo_exists

        if not repo_exists:
            if verbose:
                print(f"  [{name}] MISSING  {entry['repo_dir']}")
            continue

        _collect_engine_py_paths(name, entry, paths, verbose)

    return status, paths


def _collect_engine_py_paths(
    name: str,
    entry: dict[str, Any],
    paths: list[str],
    verbose: bool,
) -> None:
    """Append an engine's existing Python dirs to ``paths`` (deduplicated)."""
    for py_path in entry["py_paths"]:
        if os.path.isdir(py_path) and py_path not in paths:
            paths.append(py_path)
            if verbose:
                print(f"  [{name}] python   {py_path}")

    if verbose and not entry["py_paths"]:
        print(f"  [{name}] present  {entry['repo_dir']}  (no Python paths)")


def register_engine_paths(
    engines: list[str] | None = None,
    verbose: bool = False,
) -> dict[str, bool]:
    """Append sibling-repo Python directories to ``sys.path``.

    Explicit opt-in for an entrypoint; call it once from a CLI ``main``,
    not from a library module.  Paths are appended so first-party and
    standard-library modules are never shadowed, and a path already on
    ``sys.path`` is left where it is.

    Returns the engine presence mapping from :func:`engine_import_paths`.
    """
    status, paths = engine_import_paths(engines, verbose=verbose)
    for py_path in paths:
        if py_path not in sys.path:
            sys.path.append(py_path)
    return status


@contextmanager
def registered_engine_paths(
    engines: list[str] | None = None,
    verbose: bool = False,
) -> Iterator[dict[str, bool]]:
    """Scoped :func:`register_engine_paths`: ``sys.path`` is restored on exit."""
    saved = list(sys.path)
    try:
        yield register_engine_paths(engines, verbose=verbose)
    finally:
        sys.path[:] = saved
