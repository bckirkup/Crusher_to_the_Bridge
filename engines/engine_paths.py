"""
engines.engine_paths
~~~~~~~~~~~~~~~~~~~~~

Path registry and sys.path integration for the five sibling simulation
repositories.  Calling :func:`register_engine_paths` adds the relevant
directories to ``sys.path`` so that Python-based engines can be imported
directly from the master ``crusher_to_the_bridge`` workspace.

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


def register_engine_paths(
    engines: list[str] | None = None,
    verbose: bool = False,
) -> dict[str, bool]:
    """Add Python-importable paths from sibling repos to ``sys.path``.

    Parameters
    ----------
    engines:
        Engine names to register.  ``None`` (default) registers all.
    verbose:
        If ``True``, print each path as it is added.

    Returns
    -------
    dict
        Mapping of engine name → bool indicating whether the repo
        directory exists on disk.
    """
    targets = engines if engines is not None else list(ENGINE_REGISTRY.keys())
    status: dict[str, bool] = {}

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

        for py_path in entry["py_paths"]:
            if os.path.isdir(py_path) and py_path not in sys.path:
                sys.path.insert(0, py_path)
                if verbose:
                    print(f"  [{name}] added    {py_path}")

        if verbose and not entry["py_paths"]:
            print(f"  [{name}] present  {entry['repo_dir']}  (no Python paths)")

    return status
