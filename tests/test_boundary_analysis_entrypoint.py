"""Unit tests for boundary analysis Batch entrypoint validators."""

from __future__ import annotations

import pytest

from deploy.aws.boundary_analysis_entrypoint import (
    _excluded,
    _require_pathogen,
    _require_s3_uri,
    _safe_key_parts,
)


def test_require_s3_uri_accepts_canonical() -> None:
    assert (
        _require_s3_uri("s3://my-bucket/campaign/boundary_surface_v1/", label="t")
        == "s3://my-bucket/campaign/boundary_surface_v1/"
    )


def test_require_s3_uri_rejects_shell_metachar() -> None:
    with pytest.raises(SystemExit):
        _require_s3_uri("s3://bucket/$(touch /tmp/pwned)", label="t")


def test_require_pathogen_allowlist() -> None:
    assert _require_pathogen("norovirus", required=True) == "norovirus"
    with pytest.raises(SystemExit):
        _require_pathogen("../etc/passwd", required=True)
    with pytest.raises(SystemExit):
        _require_pathogen("", required=True)


def test_safe_key_parts_rejects_traversal() -> None:
    assert _safe_key_parts("pref/a/b.csv", "pref/") == ["a", "b.csv"]
    assert _safe_key_parts("pref/", "pref/") is None
    with pytest.raises(ValueError):
        _safe_key_parts("pref/../etc/passwd", "pref/")


def test_excluded_globs() -> None:
    assert _excluded("campaign/analysis/x.zip", "campaign/", ("analysis/*",))
    assert not _excluded("campaign/b1_run.zip", "campaign/", ("analysis/*", "b2_*"))
