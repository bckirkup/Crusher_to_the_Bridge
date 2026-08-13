"""Unit tests for deploy/aws/download_boundary_results helpers."""

from __future__ import annotations

import pytest

from deploy.aws.download_boundary_results import (
    _is_run_zip_key,
    _partition_run_zips,
    _resolve_parts,
    _safe_key_parts,
)


def test_safe_key_parts_accepts_nested() -> None:
    assert _safe_key_parts("pref/a/b.csv", "pref/") == ["a", "b.csv"]


def test_safe_key_parts_rejects_traversal() -> None:
    assert _safe_key_parts("pref/", "pref/") is None
    with pytest.raises(ValueError):
        _safe_key_parts("pref/../etc/passwd", "pref/")
    with pytest.raises(ValueError):
        _safe_key_parts("pref/./secret", "pref/")


def test_is_run_zip_key_filters() -> None:
    assert _is_run_zip_key("campaign/b1_x.zip")
    assert not _is_run_zip_key("campaign/analysis/x.zip")
    assert not _is_run_zip_key("campaign/_resume/x.zip")
    assert not _is_run_zip_key("campaign/note.txt")


def test_partition_run_zips_boundary_split() -> None:
    zips = [
        {"Key": "p/b1_a.zip", "Size": 1},
        {"Key": "p/b2_a.zip", "Size": 1},
        {"Key": "p/sr_a.zip", "Size": 1},
    ]
    groups = dict(_partition_run_zips(zips))
    assert len(groups["b1_run_zips.tar"]) == 1
    assert len(groups["b2_run_zips.tar"]) == 1
    assert len(groups["other_run_zips.tar"]) == 1


def test_partition_run_zips_single_tar() -> None:
    zips = [{"Key": "p/sr_a.zip", "Size": 1}, {"Key": "p/vd_a.zip", "Size": 1}]
    groups = _partition_run_zips(zips)
    assert groups == [("run_zips.tar", zips)]


def test_resolve_parts_rejects_traversal(tmp_path) -> None:
    base = tmp_path / "out"
    base.mkdir()
    assert _resolve_parts(str(base), ["stan", "norovirus.csv"]).endswith(
        "stan/norovirus.csv"
    )
    with pytest.raises(ValueError):
        _resolve_parts(str(base), ["..", "etc"])
