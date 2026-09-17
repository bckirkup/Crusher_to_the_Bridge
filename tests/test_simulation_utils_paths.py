"""Tests for simulation_utils.paths security helpers."""

from __future__ import annotations

import json
import os

import pytest

from simulation_utils.paths import (
    SchemaValidationError,
    is_path_under_base,
    load_validated_json,
    prepare_output_directory,
    resolve_child_path,
    resolve_repo_path,
    validate_json_document,
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


def test_load_validated_json_returns_a_document_that_meets_its_schema(tmp_path) -> None:
    path = tmp_path / "protocols.json"
    path.write_text(json.dumps({"protocols": []}), encoding="utf-8")
    loaded = load_validated_json(str(path), "protocols.schema.json", allowed_roots=(str(tmp_path),))
    assert loaded == {"protocols": []}


def test_load_validated_json_names_the_file_schema_and_location_on_violation(tmp_path) -> None:
    path = tmp_path / "protocols.json"
    path.write_text(json.dumps({"protocols": "not-a-list"}), encoding="utf-8")
    with pytest.raises(SchemaValidationError, match=r"protocols\.json violates schemas/protocols\.schema\.json at protocols"):
        load_validated_json(str(path), "protocols.schema.json", allowed_roots=(str(tmp_path),))


def test_schema_violation_is_a_value_error_so_existing_fallbacks_still_catch_it() -> None:
    with pytest.raises(ValueError):
        validate_json_document({"protocols": 3}, "protocols.schema.json")


def test_load_validated_json_still_refuses_paths_outside_the_allowed_roots(tmp_path) -> None:
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    inside = tmp_path / "inside"
    inside.mkdir()
    with pytest.raises(ValueError):
        load_validated_json(str(outside), "protocols.schema.json", allowed_roots=(str(inside),))


def test_unknown_schema_names_are_rejected_before_any_file_is_read() -> None:
    with pytest.raises(ValueError):
        validate_json_document({}, "../pyproject.toml")


def test_reloading_the_same_bytes_returns_a_fresh_document_without_a_second_schema_walk(
    tmp_path, monkeypatch,
) -> None:
    from simulation_utils import paths as paths_module

    path = tmp_path / "protocols.json"
    path.write_text(json.dumps({"protocols": []}), encoding="utf-8")
    calls: list[str] = []
    real_validate = paths_module.validate_json_document

    def counting_validate(document, schema_name, *, source="<document>"):
        calls.append(source)
        return real_validate(document, schema_name, source=source)

    monkeypatch.setattr(paths_module, "validate_json_document", counting_validate)
    paths_module._validated_texts.clear()
    first = load_validated_json(str(path), "protocols.schema.json", allowed_roots=(str(tmp_path),))
    second = load_validated_json(str(path), "protocols.schema.json", allowed_roots=(str(tmp_path),))
    assert first == second == {"protocols": []}
    assert first is not second
    assert len(calls) == 1


def test_an_edited_file_is_validated_again_and_a_violation_is_still_reported(tmp_path) -> None:
    path = tmp_path / "protocols.json"
    path.write_text(json.dumps({"protocols": []}), encoding="utf-8")
    load_validated_json(str(path), "protocols.schema.json", allowed_roots=(str(tmp_path),))
    path.write_text(json.dumps({"protocols": "not-a-list"}), encoding="utf-8")
    with pytest.raises(SchemaValidationError):
        load_validated_json(str(path), "protocols.schema.json", allowed_roots=(str(tmp_path),))


def test_the_same_bytes_under_a_different_schema_are_validated_on_their_own(tmp_path) -> None:
    path = tmp_path / "doc.json"
    path.write_text(json.dumps({"protocols": []}), encoding="utf-8")
    load_validated_json(str(path), "protocols.schema.json", allowed_roots=(str(tmp_path),))
    with pytest.raises(SchemaValidationError):
        load_validated_json(str(path), "class_interactions.schema.json", allowed_roots=(str(tmp_path),))
