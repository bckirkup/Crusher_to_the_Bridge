"""Filesystem path validation helpers for Sonar-safe I/O.

Inviolate rule for agents and CLI tools
---------------------------------------
Never pass attacker-/LLM-controlled path strings to ``open``, ``Path.open``,
``Path.read_text``, ``Path.write_text``, or ``os.remove`` directly.

Always canonicalize then contain via one of:

* :func:`validated_open` — preferred for all file reads/writes
* :func:`confine_to_base` / :func:`resolve_repo_path` — before other FS ops
* :func:`validate_path_component` / :func:`resolve_child_path` — for single
  path segments joined under a known parent (run ids, filenames)

Sonar rules ``pythonsecurity:S8707`` and ``pythonsecurity:S2083`` specifically
flag agent-supplied CLI paths that skip these helpers.
"""

from __future__ import annotations

import os
import re
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
    # Reject both forward and backward slashes on all platforms to prevent traversal bypass
    if "/" in name or "\\" in name or os.path.sep in name or (os.path.altsep and os.path.altsep in name):
        raise ValueError(f"Invalid {label}: {name!r}")
    if not _PATH_COMPONENT_RE.fullmatch(name):
        raise ValueError(f"Invalid {label}: {name!r}")
    return name


def confine_to_base(base_dir: str, path: str) -> str:
    """Resolve *path* (cwd-relative or absolute) and require it under *base_dir*.

    Use for CLI/agent arguments before any filesystem access (S8707/S2083).
    Relative paths resolve against the process cwd, then must still fall
    inside *base_dir*.
    """
    if not base_dir:
        raise ValueError("base_dir is required")
    base = _real(base_dir)
    resolved = _real(path)
    if not is_path_under_base(base, resolved):
        raise ValueError(f"Path {path!r} escapes allowed base {base_dir!r}")
    return resolved


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
    """Return True when an existing directory or any of its parents is world-writable."""
    if os.name == "nt":
        return False
    curr = _real(path)
    # Traverse up to the first directory that actually exists on the filesystem
    while curr and not os.path.isdir(curr):  # codeql[py/path-injection]
        parent = os.path.dirname(curr)  # codeql[py/path-injection]
        if parent == curr:  # reached root
            break
        curr = parent
    if not os.path.isdir(curr):  # codeql[py/path-injection]
        return False
    try:
        return bool(os.stat(curr).st_mode & 0o002)  # codeql[py/path-injection]
    except OSError:
        return False


def _check_containment(resolved: str, allowed_roots: tuple[str, ...]) -> None:
    """Helper to validate path absolute status and root containment."""
    if not os.path.isabs(resolved):
        raise ValueError(f"Resolved path must be absolute: {resolved!r}")
    if not any(is_path_under_base(root, resolved) for root in allowed_roots):
        raise ValueError(f"Path {resolved!r} is outside allowed roots")


def _get_target_dir(resolved: str) -> str:
    """Helper to find the target directory to check for write safety."""
    return resolved if os.path.isdir(resolved) else os.path.dirname(resolved) or resolved  # codeql[py/path-injection]


def prepare_output_directory(path: str, *, allowed_roots: tuple[str, ...]) -> str:
    """Create an output directory with restrictive permissions after validation."""
    resolved = _real(path)
    _check_containment(resolved, allowed_roots)
    target_dir = _get_target_dir(resolved)
    if is_publicly_writable(target_dir):
        raise ValueError(f"Refusing to write under publicly writable directory: {target_dir}")
    os.makedirs(resolved, mode=0o700, exist_ok=True)  # codeql[py/path-injection]  # NOSONAR
    return resolved


def safe_listdir(path: str, *, allowed_roots: tuple[str, ...]) -> list[str]:
    """List a directory after containment checks (CodeQL-safe directory probe)."""
    resolved = _real(path)
    _check_containment(resolved, allowed_roots)
    if not os.path.isdir(resolved):  # codeql[py/path-injection]
        return []
    return sorted(os.listdir(resolved))  # codeql[py/path-injection]


def _open_resolved(
    resolved: str,
    mode: str,
    *,
    encoding: str | None = None,
    newline: str | None = None,
    allowed_roots: tuple[str, ...],
) -> TextIO | BinaryIO:
    """Open a path that has already been validated and resolved."""
    _check_containment(resolved, allowed_roots)
    for_write = any(flag in mode for flag in ("w", "a", "+"))
    if for_write:
        target_dir = _get_target_dir(resolved)
        if is_publicly_writable(target_dir):
            raise ValueError(f"Refusing to write under publicly writable directory: {target_dir}")
    open_kwargs: dict[str, str | None] = {}
    if encoding is not None:
        open_kwargs["encoding"] = encoding
    if newline is not None:
        open_kwargs["newline"] = newline
    return open(resolved, mode, **open_kwargs)  # codeql[py/path-injection]  # NOSONAR


def validated_open(
    path: str,
    mode: str = "r",
    *,
    allowed_roots: tuple[str, ...],
    encoding: str | None = None,
    newline: str | None = None,
) -> TextIO | BinaryIO:
    """Open a file after containment checks.

    ``newline`` mirrors :func:`open` (needed for CSV writers that pass
    ``newline=""``). Binary modes must omit ``encoding`` / ``newline``.
    """
    resolved = _real(path)
    return _open_resolved(
        resolved,
        mode,
        encoding=encoding,
        newline=newline,
        allowed_roots=allowed_roots,
    )
