"""Tests for simulation_utils.paths security helpers."""

from __future__ import annotations

import os

import pytest

from simulation_utils.paths import (
    is_path_under_base,
    prepare_output_directory,
    resolve_child_path,
    resolve_repo_path,
    validate_path_component,
)


def test_resolve_repo_path_rejects_traversal(tmp_path) -> None:
    base = tmp_path / "repo"
    base.mkdir()
    with pytest.raises(ValueError, match="escapes repository root"):
        resolve_repo_path(str(base), "../outside.txt")


def test_resolve_child_path_rejects_nested_names(tmp_path) -> None:
    parent = tmp_path / "parent"
    parent.mkdir()
    with pytest.raises(ValueError, match="Invalid child path"):
        resolve_child_path(str(parent), "../escape")


def test_validate_path_component_accepts_platform_ids() -> None:
    assert validate_path_component("destroyer_baseline") == "destroyer_baseline"


def test_prepare_output_directory_creates_private_dir(tmp_path) -> None:
    out = tmp_path / "nested" / "output"
    created = prepare_output_directory(str(out), allowed_roots=(str(tmp_path),))
    assert os.path.isdir(created)
    assert oct(os.stat(created).st_mode & 0o777) == oct(0o700)


def test_is_path_under_base(tmp_path) -> None:
    base = tmp_path / "base"
    child = base / "child"
    sibling = tmp_path / "other"
    base.mkdir()
    child.mkdir()
    sibling.mkdir()
    assert is_path_under_base(str(base), str(child))
    assert not is_path_under_base(str(base), str(sibling))
