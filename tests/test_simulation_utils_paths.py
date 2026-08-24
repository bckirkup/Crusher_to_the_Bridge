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


def test_a_sibling_sharing_a_name_prefix_is_not_contained(tmp_path) -> None:
    """``/base`` must not admit ``/base-evil``: containment is per component."""
    base = tmp_path / "base"
    sibling = tmp_path / "base-evil"
    base.mkdir()
    sibling.mkdir()
    assert not is_path_under_base(str(base), str(sibling))


def test_a_sibling_sharing_a_name_prefix_is_rejected_by_every_helper(tmp_path) -> None:
    from simulation_utils.paths import confine_to_base, safe_listdir, validated_open

    base = tmp_path / "base"
    sibling = tmp_path / "base-evil"
    base.mkdir()
    sibling.mkdir()
    victim = sibling / "secrets.txt"
    victim.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="escapes allowed base"):
        confine_to_base(str(base), str(victim))
    with pytest.raises(ValueError, match="outside allowed roots"):
        safe_listdir(str(sibling), allowed_roots=(str(base),))
    with pytest.raises(ValueError, match="outside allowed roots"):
        validated_open(str(victim), "r", allowed_roots=(str(base),), encoding="utf-8")


def test_the_base_itself_is_contained(tmp_path) -> None:
    """A helper that refused its own root would break every default output dir."""
    from simulation_utils.paths import confine_to_base

    base = tmp_path / "base"
    base.mkdir()
    base_str = str(base)
    assert is_path_under_base(base_str, base_str)
    assert confine_to_base(base_str, base_str) == os.path.realpath(base_str)
    assert resolve_repo_path(base_str, ".") == os.path.realpath(base_str)


def test_a_symlink_out_of_the_base_is_rejected(tmp_path) -> None:
    """Containment is decided after canonicalization, not on the literal string."""
    if os.name == "nt":
        return
    base = tmp_path / "base"
    base.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "loot.txt").write_text("x", encoding="utf-8")
    (base / "door").symlink_to(outside)
    base_path = str(base)
    target = os.path.join("door", "loot.txt")
    with pytest.raises(ValueError, match="escapes repository root"):
        resolve_repo_path(base_path, target)


def test_distinct_inputs_resolve_to_distinct_contained_paths(tmp_path) -> None:
    """Containment must not collapse different requests onto one path."""
    base = tmp_path / "repo"
    (base / "a").mkdir(parents=True)
    (base / "b").mkdir()
    first = resolve_repo_path(str(base), "a")
    second = resolve_repo_path(str(base), "b")
    assert first != second
    assert os.path.basename(first) == "a"
    assert os.path.basename(second) == "b"


def test_prepare_output_directory_returns_the_path_it_checked(tmp_path) -> None:
    """The created directory is the canonical one, so callers cannot re-point it."""
    if os.name == "nt":
        return
    root = tmp_path / "root"
    root.mkdir()
    (root / "link").symlink_to(root / "real", target_is_directory=True)
    (root / "real").mkdir()
    created = prepare_output_directory(str(root / "link" / "out"), allowed_roots=(str(root),))
    assert created == os.path.realpath(root / "real" / "out")
    assert os.path.isdir(created)
