"""Filesystem path validation helpers for Sonar-safe I/O."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import BinaryIO, TextIO

_PATH_COMPONENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _real(path: str) -> str:
    return os.path.realpath(path)


def is_path_under_base(base_dir: str, candidate: str) -> bool:
    """Return True when *candidate* resolves inside *base_dir*."""
    base = _real(base_dir)
    resolved = _real(candidate)
    try:
        return os.path.commonpath([base, resolved]) == base
    except ValueError:
        return False


def validate_path_component(name: str, *, label: str = "path component") -> str:
    """Reject traversal or separator characters in a single path component."""
    if not name or name in {".", ".."}:
        raise ValueError(f"Invalid {label}: {name!r}")
    if os.path.sep in name or (os.path.altsep and os.path.altsep in name):
        raise ValueError(f"Invalid {label}: {name!r}")
    if "/" in name or "\\" in name:
        raise ValueError(f"Invalid {label}: {name!r}")
    if not _PATH_COMPONENT_RE.fullmatch(name):
        raise ValueError(f"Invalid {label}: {name!r}")
    return name


def resolve_repo_path(repo_root: str, path: str) -> str:
    """Resolve *path* under *repo_root* and reject traversal escapes."""
    if not repo_root:
        raise ValueError("repo_root is required")
    base = _real(repo_root)
    resolved = _real(path if os.path.isabs(path) else os.path.join(base, path))
    if not is_path_under_base(base, resolved):
        raise ValueError(f"Path {path!r} escapes repository root {repo_root!r}")
    return resolved


def resolve_child_path(parent_dir: str, child_name: str) -> str:
    """Join a single validated filename under *parent_dir*."""
    parent = _real(parent_dir)
    safe_name = validate_path_component(child_name, label="child path")
    resolved = _real(os.path.join(parent, safe_name))
    if not is_path_under_base(parent, resolved):
        raise ValueError(f"Child path {child_name!r} escapes parent directory")
    return resolved


def is_publicly_writable(path: str) -> bool:
    """Return True when an existing directory is world-writable."""
    directory = path
    if not os.path.isdir(directory):
        directory = os.path.dirname(_real(directory)) or "."
    if not os.path.isdir(directory):
        return False
    return bool(os.stat(directory).st_mode & 0o002)


def _ensure_safe_resolved_path(
    resolved: str,
    *,
    allowed_roots: tuple[str, ...] | None = None,
    for_write: bool = False,
) -> str:
    """Validate a realpath before filesystem access."""
    if not os.path.isabs(resolved):
        raise ValueError(f"Resolved path must be absolute: {resolved!r}")
    if allowed_roots and not any(is_path_under_base(root, resolved) for root in allowed_roots):
        raise ValueError(f"Path {resolved!r} is outside allowed roots")
    target_dir = resolved if os.path.isdir(resolved) else os.path.dirname(resolved) or resolved
    if for_write and is_publicly_writable(target_dir):
        raise ValueError(f"Refusing to write under publicly writable directory: {target_dir}")
    return resolved


def prepare_output_directory(path: str, *, allowed_roots: tuple[str, ...] | None = None) -> str:
    """Create an output directory with restrictive permissions after validation."""
    resolved = _ensure_safe_resolved_path(
        _real(path),
        allowed_roots=allowed_roots,
        for_write=True,
    )
    Path(resolved).mkdir(mode=0o700, parents=True, exist_ok=True)
    return resolved


def _open_resolved(
    resolved: str,
    mode: str,
    *,
    encoding: str | None = None,
    allowed_roots: tuple[str, ...] | None = None,
) -> TextIO | BinaryIO:
    """Open a path that has already been validated and resolved."""
    safe_path = _ensure_safe_resolved_path(
        resolved,
        allowed_roots=allowed_roots,
        for_write=any(flag in mode for flag in ("w", "a", "+")),
    )
    path_obj = Path(safe_path)
    if encoding is None:
        return path_obj.open(mode)
    return path_obj.open(mode, encoding=encoding)


def validated_open(
    path: str,
    mode: str = "r",
    *,
    allowed_roots: tuple[str, ...] | None = None,
    encoding: str | None = None,
) -> TextIO | BinaryIO:
    """Open a file after optional containment checks."""
    resolved = _real(path)
    if encoding is None:
        return _open_resolved(resolved, mode, allowed_roots=allowed_roots)
    return _open_resolved(resolved, mode, encoding=encoding, allowed_roots=allowed_roots)
