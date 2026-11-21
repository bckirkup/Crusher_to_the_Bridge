"""Exercise reviewed return integrity and the existing single-object caller."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import campaign_collect_exact as collect


@pytest.fixture
def s3(monkeypatch):
    state = SimpleNamespace(body=b"approved aggregate", gets=[])
    state.head = {"ContentLength": len(state.body), "ETag": '"etag"'}

    def get(cmd, **kwargs):
        state.gets.append(cmd)
        Path(cmd[-1]).write_bytes(state.body)

    monkeypatch.setattr(collect.subprocess, "check_output",
                        lambda *args, **kwargs: json.dumps(state.head).encode())
    monkeypatch.setattr(collect.subprocess, "run", get)
    return state


@pytest.mark.parametrize("version", [None, "version-1"])
def test_fetch_pins_head_and_checks_digest(s3, tmp_path, version):
    if version:
        s3.head["VersionId"] = version
    digest = hashlib.sha256(s3.body).hexdigest()
    assert collect.fetch("bucket", "campaign/reviewed.csv", len(s3.body),
                         digest, tmp_path) == digest
    cmd = s3.gets[0]
    pin = "--version-id" if version else "--if-match"
    assert cmd[cmd.index(pin) + 1] == (version or '"etag"')
    assert (tmp_path / "reviewed.csv").read_bytes() == s3.body


@pytest.mark.parametrize("change", ["oversize", "short", "archive", "corrupt", "truncated"])
def test_fetch_refuses_invalid_return(s3, tmp_path, change):
    digest = hashlib.sha256(s3.body).hexdigest()
    size = len(s3.body)
    if change == "oversize":
        s3.head["ContentLength"] += 1
    if change == "short":
        s3.head["ContentLength"] -= 1
    if change == "archive":
        s3.head["StorageClass"] = "DEEP_ARCHIVE"
    if change == "corrupt":
        s3.body = b"x" * size
    if change == "truncated":
        s3.body = s3.body[:-1]
    with pytest.raises(ValueError):
        collect.fetch("bucket", "campaign/reviewed.csv", size, digest, tmp_path)
    assert len(s3.gets) == (1 if change in {"corrupt", "truncated"} else 0)


@pytest.mark.parametrize("key", ["private/x", "campaign/../x", "campaign/"])
def test_fetch_refuses_out_of_scope_key(s3, tmp_path, key):
    with pytest.raises(ValueError):
        collect.fetch("bucket", key, 100, None, tmp_path)
    assert not s3.gets


@pytest.mark.parametrize("reviewed", [True, False])
def test_main_returns_requested_objects_with_legacy_ceiling(s3, monkeypatch, tmp_path, reviewed):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BUCKET", "bucket")
    monkeypatch.setenv("EXACT_KEY", "campaign/legacy.csv")
    monkeypatch.setenv("MAX_FETCH_BYTES", "100")
    monkeypatch.setenv("SOLVER_RETURN", str(reviewed).lower())
    digest = hashlib.sha256(s3.body).hexdigest()
    outputs = tuple((f"campaign/reviewed-{i}.csv", len(s3.body), digest) for i in range(2))
    monkeypatch.setattr(collect, "SOLVER_OUTPUTS", outputs)
    collect.main()
    lines = (tmp_path / "fetched/SHA256SUMS").read_text().splitlines()
    expected = [f"{digest}  reviewed-{i}.csv" for i in range(2)] if reviewed else [
        f"{digest}  campaign/legacy.csv"]
    assert lines == expected
    assert len(s3.gets) == len(expected)
