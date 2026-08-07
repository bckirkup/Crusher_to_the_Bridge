"""Shared Sonar-safe CLI path I/O for Contam campaign manifest builders."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from simulation_utils.paths import (
    prepare_output_directory,
    resolve_repo_path,
    validated_open,
)


def resolve_repo_cli_path(repo_root: str | Path, path: Path | str) -> str:
    """Confine a CLI path under the repository root (Sonar S8707)."""
    return resolve_repo_path(str(repo_root), str(path))


def load_source_manifest(repo_root: str | Path, source_arg: Path | str) -> dict[str, Any]:
    """Read a JSON source manifest after confining the CLI path under *repo_root*."""
    root = str(repo_root)
    source_path = resolve_repo_cli_path(root, source_arg)
    with validated_open(source_path, allowed_roots=(root,), encoding="utf-8") as fh:
        return json.load(fh)


def write_manifest(
    repo_root: str | Path,
    out_arg: Path | str,
    manifest: dict[str, Any],
) -> str:
    """Write a JSON manifest after confining the CLI path under *repo_root*."""
    root = str(repo_root)
    out_path = resolve_repo_cli_path(root, out_arg)
    prepare_output_directory(os.path.dirname(out_path), allowed_roots=(root,))
    with validated_open(out_path, "w", allowed_roots=(root,), encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return out_path


def require_repo_file(repo_root: str | Path, path_arg: Path | str) -> str:
    """Resolve *path_arg* under *repo_root* and require that it exists as a file."""
    resolved = resolve_repo_cli_path(repo_root, path_arg)
    if not Path(resolved).is_file():
        raise SystemExit(f"Source manifest not found: {path_arg}")
    return resolved
