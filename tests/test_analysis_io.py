"""Path-safe I/O helpers for picard_framework.analysis._io."""

from __future__ import annotations

import csv
import gzip
import json
import os
import zipfile
from pathlib import Path

import pytest

from picard_framework.analysis import _io as aio

COLUMNS = ("epoch", "infected", "label")


def _rows() -> list[dict]:
    return [
        {"epoch": 0, "infected": 1, "label": "a"},
        {"epoch": 1, "infected": 3, "label": "b"},
        {"epoch": 2, "infected": 2, "label": "c"},
    ]


class TestCsvRoundTrip:
    def test_write_csv_round_trip(self, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        path = str(tmp_path / "table.csv")
        rows = _rows()
        aio.write_csv(path, rows, COLUMNS)
        with open(path, encoding="utf-8", newline="") as fh:
            loaded = list(csv.DictReader(fh))
        assert len(loaded) == len(rows)
        assert [int(r["infected"]) for r in loaded] == [1, 3, 2]
        assert list(loaded[0].keys()) == list(COLUMNS)

    def test_write_csv_gz_round_trip(self, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        path = str(tmp_path / "table.csv.gz")
        rows = _rows()
        aio.write_csv_gz(path, rows, COLUMNS)
        with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
            loaded = list(csv.DictReader(fh))
        assert len(loaded) == len(rows)
        assert [r["label"] for r in loaded] == ["a", "b", "c"]


class TestTimeseriesTable:
    def test_write_timeseries_row_count(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        out_dir = str(tmp_path / "out")
        os.makedirs(out_dir)
        rows = _rows()
        basename = aio.write_timeseries_table(out_dir, rows, COLUMNS)
        assert basename in ("epoch_timeseries.parquet", "epoch_timeseries.csv.gz")
        written = os.path.join(out_dir, basename)
        assert os.path.isfile(written)
        if basename.endswith(".csv.gz"):
            with gzip.open(written, "rt", encoding="utf-8", newline="") as fh:
                n = sum(1 for _ in csv.DictReader(fh))
            assert n == len(rows)
        else:
            import pyarrow.parquet as pq

            table = pq.read_table(written)
            assert table.num_rows == len(rows)


class TestIterResultZips:
    def test_sorting_and_zip_only(self, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        root = tmp_path / "results"
        root.mkdir()
        (root / "b.zip").write_bytes(b"PK\x05\x06" + b"\x00" * 18)
        (root / "a.zip").write_bytes(b"PK\x05\x06" + b"\x00" * 18)
        (root / "notes.txt").write_text("skip me", encoding="utf-8")
        (root / "c.json").write_text("{}", encoding="utf-8")
        paths = list(aio.iter_result_zips(str(root)))
        names = [os.path.basename(p) for p in paths]
        assert names == ["a.zip", "b.zip"]
        assert all(p.endswith(".zip") for p in paths)


class TestLoadZipNoneOnBad:
    def test_load_zip_json_none_on_bad(self, tmp_path) -> None:
        bad = tmp_path / "bad.zip"
        bad.write_bytes(b"not-a-zip")
        assert aio.load_zip_json(str(bad), "summary.json") is None

        empty = tmp_path / "empty.zip"
        with zipfile.ZipFile(empty, "w") as zf:
            zf.writestr("readme.txt", "hello")
        assert aio.load_zip_json(str(empty), "summary.json") is None

    def test_load_run_zip_none_on_bad(self, tmp_path) -> None:
        bad = tmp_path / "bad.zip"
        bad.write_bytes(b"nope")
        assert aio.load_run_zip(str(bad)) is None

        # Valid zip but missing summary.json → None.
        no_summary = tmp_path / "nosum.zip"
        with zipfile.ZipFile(no_summary, "w") as zf:
            zf.writestr("other.json", json.dumps({"x": 1}))
        assert aio.load_run_zip(str(no_summary)) is None


class TestSafePath:
    def test_safe_path_outside_cwd_system_exit(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        outside = Path("/tmp") / "cursor-analysis-outside-cwd"
        with pytest.raises(SystemExit):
            aio.safe_path(str(outside))

    def test_safe_path_inside_cwd(self, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        inner = tmp_path / "ok"
        inner.mkdir()
        resolved = aio.safe_path(str(inner))
        assert os.path.isabs(resolved)
        assert resolved.startswith(os.path.realpath(str(tmp_path)))
