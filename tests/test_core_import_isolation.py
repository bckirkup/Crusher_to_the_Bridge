"""Core-sim entrypoints must not load offline analysis/observation packages.

``picard_framework.analysis`` and ``telemetry_buffer.observation_model`` are
offline post-processing. Their heavy optional deps (the ``analysis`` extra in
``pyproject.toml``: pandas, pyarrow, matplotlib, cmdstanpy, scipy) must stay
off the core-simulation import path.

Observation-model tools may import core (offline -> core is fine); the reverse
edge is not. This module freezes that quarantine with a subprocess import under
an import hook that refuses the analysis extra.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# Modules an operator / orchestrator loads for a live ship step. Importing any
# of these must not pull offline analysis or observation_model packages.
CORE_ENTRYPOINTS = (
    "orchestrator",
    "orchestrator_init",
    "orchestrator_epoch",
    "orchestrator_types",
    "orchestrator_record",
    "engines.transmission_core",
    "picard_framework",
    "picard_framework.run_spec",
    "picard_framework.simulation.ship_simulation",
)

# Source files scanned for forbidden top-level analysis/observation imports.
CORE_SOURCE_FILES = (
    "orchestrator.py",
    "orchestrator_init.py",
    "orchestrator_epoch.py",
    "orchestrator_types.py",
    "orchestrator_record.py",
    "engines/transmission_core.py",
    "picard_framework/__init__.py",
    "picard_framework/run_spec.py",
    "picard_framework/simulation/ship_simulation.py",
)

_FORBIDDEN_PREFIXES = (
    "picard_framework.analysis",
    "telemetry_buffer.observation_model",
)

_BLOCKED_EXTRAS = (
    "pandas",
    "pyarrow",
    "matplotlib",
    "cmdstanpy",
    "scipy",
)


def _top_level_import_names(path: Path) -> list[str]:
    """Return dotted module names imported at module scope (not inside defs)."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
        elif isinstance(node, ast.If):
            # Skip TYPE_CHECKING / similar guarded import blocks.
            continue
    return names


@pytest.mark.parametrize("rel", CORE_SOURCE_FILES)
def test_core_sources_have_no_toplevel_analysis_imports(rel: str) -> None:
    path = REPO_ROOT / rel
    assert path.is_file(), f"missing core source {rel}"
    for name in _top_level_import_names(path):
        for prefix in _FORBIDDEN_PREFIXES:
            assert name != prefix and not name.startswith(prefix + "."), (
                f"{rel} top-level import {name!r} pulls offline package "
                f"{prefix!r}; move it inside the function that needs it"
            )


def test_core_entrypoints_import_without_analysis_extra() -> None:
    """Subprocess: block analysis extras, import core, assert quarantine."""
    script = textwrap.dedent(
        f"""
        import importlib
        import sys

        blocked = {list(_BLOCKED_EXTRAS)!r}
        forbidden_prefixes = {list(_FORBIDDEN_PREFIXES)!r}
        entrypoints = {list(CORE_ENTRYPOINTS)!r}

        class _BlockAnalysisExtra:
            def find_spec(self, fullname, path, target=None):
                root = fullname.split(".", 1)[0]
                if root in blocked:
                    raise ImportError(
                        f"analysis extra blocked during core-sim import: {{fullname}}"
                    )
                return None

        sys.meta_path.insert(0, _BlockAnalysisExtra())

        for name in entrypoints:
            importlib.import_module(name)

        offenders = sorted(
            mod
            for mod in sys.modules
            if any(
                mod == prefix or mod.startswith(prefix + ".")
                for prefix in forbidden_prefixes
            )
        )
        if offenders:
            raise SystemExit(
                "core-sim import pulled offline packages: " + ", ".join(offenders)
            )
        print("core_import_isolation_ok")
        """
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(REPO_ROOT), env.get("PYTHONPATH", "")],
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "core-sim import isolation failed\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "core_import_isolation_ok" in result.stdout
