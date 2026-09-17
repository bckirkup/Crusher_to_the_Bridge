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

Containment is written as canonicalize-then-``startswith``, and every helper
returns the value it checked rather than checking one variable and using
another. Taint analysis recognizes that shape as a containment check, so the
filesystem calls downstream of these helpers are provably guarded rather than
annotated as guarded.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import OrderedDict
from functools import lru_cache
from typing import Any, BinaryIO, TextIO

import jsonschema
from jsonschema.exceptions import best_match
from jsonschema.protocols import Validator
from jsonschema.validators import validator_for

_PATH_COMPONENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

_REPO_ROOT_MARKERS = ("pyproject.toml", ".git")


def repo_root() -> str:
    """Return the absolute path of the repository root.

    The root is the nearest ancestor of this module that carries a repository
    marker (``pyproject.toml`` or ``.git``); if no marker is found the
    package's parent directory is used. Modules should call this instead of
    counting ``os.path.dirname`` levels from their own ``__file__``.
    """
    package_dir = os.path.dirname(os.path.abspath(__file__))
    current = package_dir
    while True:
        if any(os.path.exists(os.path.join(current, m)) for m in _REPO_ROOT_MARKERS):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return os.path.dirname(package_dir)
        current = parent


REPO_ROOT = repo_root()

SCHEMA_DIR = os.path.join(REPO_ROOT, "schemas")


class SchemaValidationError(ValueError):
    """A JSON document violates the repository schema it is loaded under."""


def _real(path: str) -> str:
    return os.path.realpath(path)


def _prefix(base_real: str) -> str:
    """Return *base_real* with a trailing separator, so ``/a`` never covers ``/ab``."""
    return base_real if base_real.endswith(os.sep) else base_real + os.sep


def _contain(base_real: str, resolved: str, message: str) -> str:
    """Return *resolved* when it is *base_real* or lies beneath it, else raise.

    Both arguments must already be canonicalized. The base itself is returned
    as the base, not as the caller's string, so nothing downstream of this
    function reads an unchecked path.
    """
    if resolved == base_real:
        return base_real
    if not resolved.startswith(_prefix(base_real)):
        raise ValueError(message)
    return resolved


def is_path_under_base(base_dir: str, candidate: str) -> bool:
    """Return True when *candidate* resolves inside *base_dir*."""
    base = _real(base_dir)
    resolved = _real(candidate)
    return resolved == base or resolved.startswith(_prefix(base))


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
    return _contain(base, resolved, f"Path {path!r} escapes allowed base {base_dir!r}")


def resolve_repo_path(repo_root: str, path: str) -> str:
    """Resolve *path* under *repo_root* and reject traversal escapes."""
    if not repo_root:
        raise ValueError("repo_root is required")
    base = _real(repo_root)
    resolved = _real(path if os.path.isabs(path) else os.path.join(base, path))
    return _contain(base, resolved, f"Path {path!r} escapes repository root {repo_root!r}")


def resolve_child_path(parent_dir: str, child_name: str) -> str:
    """Join a single validated filename under *parent_dir*."""
    parent = _real(parent_dir)
    safe_name = validate_path_component(child_name, label="child path")
    resolved = _real(os.path.join(parent, safe_name))
    return _contain(
        parent, resolved, f"Child path {child_name!r} escapes parent directory"
    )


def is_publicly_writable(path: str) -> bool:
    """Return True when an existing directory or any of its parents is world-writable."""
    if os.name == "nt":
        return False
    curr = _real(path)
    # Traverse up to the first directory that actually exists on the filesystem
    while curr and not os.path.isdir(curr):
        parent = os.path.dirname(curr)
        if parent == curr:  # reached root
            break
        curr = parent
    if not os.path.isdir(curr):
        return False
    try:
        return bool(os.stat(curr).st_mode & 0o002)
    except OSError:
        return False


def _confine_to_roots(resolved: str, allowed_roots: tuple[str, ...]) -> str:
    """Return the canonical *resolved* path once one allowed root contains it."""
    if not os.path.isabs(resolved):
        raise ValueError(f"Resolved path must be absolute: {resolved!r}")
    for root in allowed_roots:
        base = _real(root)
        if resolved == base:
            return base
        if resolved.startswith(_prefix(base)):
            return resolved
    raise ValueError(f"Path {resolved!r} is outside allowed roots")


def _get_target_dir(resolved: str) -> str:
    """Helper to find the target directory to check for write safety."""
    return resolved if os.path.isdir(resolved) else os.path.dirname(resolved) or resolved


def _refuse_public_target(safe: str) -> None:
    target_dir = _get_target_dir(safe)
    if is_publicly_writable(target_dir):
        raise ValueError(f"Refusing to write under publicly writable directory: {target_dir}")


def prepare_output_directory(path: str, *, allowed_roots: tuple[str, ...]) -> str:
    """Create an output directory with restrictive permissions after validation."""
    safe = _confine_to_roots(_real(path), allowed_roots)
    _refuse_public_target(safe)
    os.makedirs(safe, mode=0o700, exist_ok=True)  # NOSONAR
    return safe


def safe_listdir(path: str, *, allowed_roots: tuple[str, ...]) -> list[str]:
    """List a directory after containment checks."""
    safe = _confine_to_roots(_real(path), allowed_roots)
    if not os.path.isdir(safe):
        return []
    return sorted(os.listdir(safe))


def _open_resolved(
    resolved: str,
    mode: str,
    *,
    encoding: str | None = None,
    newline: str | None = None,
    allowed_roots: tuple[str, ...],
) -> TextIO | BinaryIO:
    """Open a path that has already been validated and resolved."""
    safe = _confine_to_roots(resolved, allowed_roots)
    if any(flag in mode for flag in ("w", "a", "+")):
        _refuse_public_target(safe)
    open_kwargs: dict[str, str | None] = {}
    if encoding is not None:
        open_kwargs["encoding"] = encoding
    if newline is not None:
        open_kwargs["newline"] = newline
    return open(safe, mode, **open_kwargs)  # NOSONAR


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


@lru_cache(maxsize=None)
def load_schema(schema_name: str) -> dict[str, Any]:
    """Return the parsed ``schemas/<schema_name>`` document, cached per process."""
    schema_path = resolve_child_path(SCHEMA_DIR, schema_name)
    with validated_open(schema_path, "r", allowed_roots=(SCHEMA_DIR,), encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=None)
def _schema_validator(schema_name: str) -> Validator:
    """Return a validator for ``schemas/<schema_name>``, metaschema-checked once per process.

    ``jsonschema.validate`` re-runs the metaschema check on every call, and
    for the draft-2020-12 schemas in this repository that check dominates the
    cost of validating the instance itself.
    """
    schema = load_schema(schema_name)
    cls = validator_for(schema)
    cls.check_schema(schema)
    return cls(schema)


def _describe_violation(schema_name: str, source: str, error: jsonschema.ValidationError) -> str:
    location = "/".join(str(part) for part in error.absolute_path) or "<root>"
    return f"{source} violates schemas/{schema_name} at {location}: {error.message}"


def validate_json_document(
    document: Any,
    schema_name: str,
    *,
    source: str = "<document>",
) -> Any:
    """Validate *document* against ``schemas/<schema_name>`` and return it.

    Raises :class:`SchemaValidationError` (a ``ValueError``) naming the source,
    the schema, and the offending location so callers that already treat
    ``ValueError`` as "unusable input" keep their existing fallbacks.
    """
    error = best_match(_schema_validator(schema_name).iter_errors(document))
    if error is not None:
        raise SchemaValidationError(_describe_violation(schema_name, source, error)) from error
    return document


_VALIDATED_TEXT_CACHE_SIZE = 256
# (schema_name, sha256 of the file text) for documents that already passed validation.
_validated_texts: OrderedDict[tuple[str, str], None] = OrderedDict()


def _remember_validated_text(key: tuple[str, str]) -> None:
    _validated_texts[key] = None
    _validated_texts.move_to_end(key)
    while len(_validated_texts) > _VALIDATED_TEXT_CACHE_SIZE:
        _validated_texts.popitem(last=False)


def load_validated_json(
    path: str,
    schema_name: str,
    *,
    allowed_roots: tuple[str, ...],
) -> Any:
    """Open *path* under *allowed_roots*, parse it, and validate it against a schema.

    This is the one loader every runtime consumer of a schema-backed asset
    (platform layouts, pathogen bundles, run specs, protocol/cost/logging
    configs, ...) should use, so the contracts in ``schemas/`` are enforced on
    the path the simulation actually runs rather than only offline.

    Every call re-reads and re-parses the file, so callers always get a fresh
    document; only the schema walk is skipped when the exact same bytes have
    already been validated against the same schema in this process.
    """
    with validated_open(path, "r", allowed_roots=allowed_roots, encoding="utf-8") as fh:
        text = fh.read()
    document = json.loads(text)
    key = (schema_name, hashlib.sha256(text.encode("utf-8")).hexdigest())
    if key in _validated_texts:
        _validated_texts.move_to_end(key)
        return document
    validate_json_document(document, schema_name, source=path)
    _remember_validated_text(key)
    return document
