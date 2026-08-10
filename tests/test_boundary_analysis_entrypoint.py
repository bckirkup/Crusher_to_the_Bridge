"""Unit tests for boundary analysis Batch entrypoint validators."""

from __future__ import annotations

import pytest

from deploy.aws.boundary_analysis_entrypoint import (
    _require_pathogen,
    _require_s3_uri,
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
