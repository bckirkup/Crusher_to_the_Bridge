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
    base_str = str(base)
    with pytest.raises(ValueError, match="escapes repository root"):
        resolve_repo_path(base_str, "../outside.txt")


def test_resolve_child_path_rejects_nested_names(tmp_path) -> None:
    parent = tmp_path / "parent"
    parent.mkdir()
    parent_str = str(parent)
    with pytest.raises(ValueError, match="Invalid child path"):
        resolve_child_path(parent_str, "../escape")


def test_validate_path_component_accepts_platform_ids() -> None:
    assert validate_path_component("destroyer_baseline") == "destroyer_baseline"


def test_prepare_output_directory_creates_private_dir(tmp_path) -> None:
    out = tmp_path / "nested" / "output"
    created = prepare_output_directory(str(out), allowed_roots=(str(tmp_path),))
    assert os.path.isdir(created)
    if os.name != "nt":
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


def test_confine_to_base_rejects_escape(tmp_path) -> None:
    from simulation_utils.paths import confine_to_base

    base = tmp_path / "base"
    base.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="escapes allowed base"):
        confine_to_base(str(base), str(outside))


def test_confine_to_base_accepts_child(tmp_path) -> None:
    from simulation_utils.paths import confine_to_base

    base = tmp_path / "base"
    child = base / "child.txt"
    base.mkdir()
    child.write_text("ok", encoding="utf-8")
    assert confine_to_base(str(base), str(child)) == os.path.realpath(child)


def test_validated_open_accepts_newline_for_csv(tmp_path) -> None:
    """python:S930 — CSV writers need newline='' on validated_open."""
    import csv

    from simulation_utils.paths import validated_open

    base = tmp_path / "out"
    base.mkdir()
    path = base / "rows.csv"
    with validated_open(
        str(path),
        "w",
        allowed_roots=(str(tmp_path),),
        encoding="utf-8",
        newline="",
    ) as fh:
        writer = csv.DictWriter(fh, fieldnames=["a", "b"])
        writer.writeheader()
        writer.writerow({"a": "1", "b": "2"})
    text = path.read_text(encoding="utf-8")
    assert text.splitlines() == ["a,b", "1,2"]


def test_is_publicly_writable_recursive(tmp_path) -> None:
    from simulation_utils.paths import is_publicly_writable
    if os.name == "nt":
        return
    # Create a world-writable directory
    writable_dir = tmp_path / "writable"
    writable_dir.mkdir()
    os.chmod(writable_dir, 0o777)  # NOSONAR
    
    # Check that a nonexistent subdirectory under it is detected as publicly writable
    nested_nonexistent = writable_dir / "sub1" / "sub2" / "file.txt"
    assert is_publicly_writable(str(nested_nonexistent)) is True


def test_safe_listdir_rejects_outside_root(tmp_path) -> None:
    from simulation_utils.paths import safe_listdir

    base = tmp_path / "repo"
    base.mkdir()
    (base / "cruise_000").mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    names = safe_listdir(str(base), allowed_roots=(str(base),))
    assert "cruise_000" in names
    try:
        safe_listdir(str(outside), allowed_roots=(str(base),))
        raised = False
    except ValueError:
        raised = True
    assert raised
