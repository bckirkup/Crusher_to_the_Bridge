"""Bounds and path-registration coverage for engines.engine_paths."""

from __future__ import annotations

import os
import sys

import pytest

import engines.engine_paths as engine_paths
from engines.engine_paths import get_engine_path, register_engine_paths


class TestUnknownAndLookup:
    def test_unknown_engine_returns_false(self) -> None:
        status = register_engine_paths(engines=["not-a-real-engine"])
        assert status == {"not-a-real-engine": False}

    def test_get_engine_path_abs_and_keyerror(self) -> None:
        path = get_engine_path("FRED")
        assert os.path.isabs(path)
        assert path.endswith("FRED")
        with pytest.raises(KeyError):
            get_engine_path("definitely-missing-engine")


class TestRegisterIdempotent:
    def test_tmp_py_path_prepended_once(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        repo = tmp_path / "fake-engine"
        py_dir = repo / "python"
        py_dir.mkdir(parents=True)
        abs_py = str(py_dir.resolve())
        abs_repo = str(repo.resolve())

        fake_entry = {
            "repo_dir": abs_repo,
            "py_paths": [abs_py],
            "language": "Python",
            "role": "unit-test stub",
        }
        monkeypatch.setitem(engine_paths.ENGINE_REGISTRY, "fake-engine", fake_entry)

        # Remove any prior insertion from a previous test run in-process.
        while abs_py in sys.path:
            sys.path.remove(abs_py)

        before = list(sys.path)
        status1 = register_engine_paths(engines=["fake-engine"])
        assert status1["fake-engine"] is True
        assert sys.path[0] == abs_py
        count_after_first = sys.path.count(abs_py)
        assert count_after_first == 1

        status2 = register_engine_paths(engines=["fake-engine"])
        assert status2["fake-engine"] is True
        assert sys.path.count(abs_py) == 1
        assert len(sys.path) == len(before) + 1


class TestFredEmptyPyPaths:
    def test_fred_empty_py_paths_does_not_grow_sys_path(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fred_repo = tmp_path / "FRED"
        fred_repo.mkdir()
        abs_repo = str(fred_repo.resolve())
        monkeypatch.setitem(
            engine_paths.ENGINE_REGISTRY,
            "FRED",
            {
                "repo_dir": abs_repo,
                "py_paths": [],
                "language": "C++ / R",
                "role": "compliance",
            },
        )
        before_len = len(sys.path)
        before_snapshot = list(sys.path)
        status = register_engine_paths(engines=["FRED"], verbose=True)
        assert status["FRED"] is True
        assert len(sys.path) == before_len
        assert sys.path == before_snapshot
