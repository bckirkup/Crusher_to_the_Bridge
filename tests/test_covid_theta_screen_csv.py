"""Reporting-only flattening of a boarding-screen surface into the CSV of record."""
from __future__ import annotations

import csv
import json

import pytest

from tools import covid_theta_screen_csv as mod


@pytest.fixture(autouse=True)
def _cwd_is_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


def _surface(theta: float, *, onsets: list[int], takeoff: float) -> dict:
    return {
        "surface": [{
            "theta": theta,
            "infection_age_days": 3.3,
            "index_geometry_pass_fraction": 1.0,
            "recorded_onsets": {"median": float(onsets[len(onsets) // 2])},
            "recorded_onsets_per_seed": [float(x) for x in onsets],
            "attack_rate_quantiles": {"q10": 0.01, "q50": 0.3, "q90": 0.9},
            "takeoff_probability": takeoff,
            "index_geometry_ok": True,
            "t1_ok": True,
            "t3_ok": False,
        }],
    }


def _cell(theta: float, seed: int, total: int, onsets: int) -> dict:
    return {
        "cell": {"theta": theta, "infection_age_days": 3.3, "seed": seed},
        "infections_total": total,
        "attack_rate": total / 3712.0,
        "index_onset_day": -1.0,
        "index_shedding_at_day0": True,
        "invalid_reason": None,
        "observables": {"recorded_onsets": onsets},
    }


def _rows(path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class TestSurfaceCsv:
    def test_columns_match_the_surface_of_record(self, tmp_path) -> None:
        out = tmp_path / "surface.csv"
        mod.write_surface_csv(_surface(1e9, onsets=[0, 5, 3000], takeoff=0.6), str(out))
        assert tuple(_rows(out)[0]) == mod.SURFACE_COLUMNS

    def test_rows_sort_by_theta_then_age(self, tmp_path) -> None:
        surface = {"surface": [
            _surface(1e9, onsets=[1], takeoff=0.6)["surface"][0],
            _surface(1e4, onsets=[1], takeoff=0.1)["surface"][0],
        ]}
        out = tmp_path / "surface.csv"
        assert mod.write_surface_csv(surface, str(out)) == 2
        assert [r["theta"] for r in _rows(out)] == ["10000.0", "1000000000.0"]

    @pytest.mark.parametrize(
        ("onsets", "expected"),
        [([0, 0, 2], "0 0 2"), ([3000, 2, 0], "0 2 3000"), ([7], "7")],
    )
    def test_per_seed_onsets_are_sorted_integers(
        self, tmp_path, onsets, expected,
    ) -> None:
        out = tmp_path / "surface.csv"
        mod.write_surface_csv(_surface(1e9, onsets=onsets, takeoff=0.5), str(out))
        assert _rows(out)[0]["recorded_onsets_per_seed"] == expected

    @pytest.mark.parametrize("takeoff", [0.0, 0.6, 1.0])
    def test_takeoff_probability_passes_through(self, tmp_path, takeoff) -> None:
        out = tmp_path / "surface.csv"
        mod.write_surface_csv(_surface(1e9, onsets=[1], takeoff=takeoff), str(out))
        assert float(_rows(out)[0]["takeoff_probability"]) == takeoff

    def test_missing_fields_become_blank_not_an_error(self, tmp_path) -> None:
        out = tmp_path / "surface.csv"
        mod.write_surface_csv({"surface": [{"theta": 1.0, "infection_age_days": 3.3}]},
                              str(out))
        assert _rows(out)[0]["attack_q50"] == ""

    def test_empty_surface_writes_header_only(self, tmp_path) -> None:
        out = tmp_path / "surface.csv"
        assert mod.write_surface_csv({"surface": []}, str(out)) == 0
        assert _rows(out) == []


class TestPairsCsv:
    def _cells(self, tmp_path, name: str, cells: list[dict]):
        directory = tmp_path / name
        directory.mkdir()
        for i, payload in enumerate(cells):
            (directory / f"cell_{i}.json").write_text(json.dumps(payload))
        return directory

    def test_parent_values_pair_by_seed(self, tmp_path) -> None:
        cells = self._cells(tmp_path, "v10", [
            _cell(1e9, 20200205, 3458, 2879),
            _cell(1e9, 20200206, 2, 0),
        ])
        parent = self._cells(tmp_path, "v9", [_cell(1e9, 20200205, 3456, 3103)])
        out = tmp_path / "pairs.csv"
        assert mod.write_pairs_csv(str(cells), str(parent), str(out)) == 2
        rows = {int(r["seed"]): r for r in _rows(out)}
        assert rows[20200205]["parent_recorded_onsets"] == "3103"
        assert rows[20200206]["parent_recorded_onsets"] == ""

    def test_without_a_parent_every_parent_column_is_blank(self, tmp_path) -> None:
        cells = self._cells(tmp_path, "v10", [_cell(1e9, 20200205, 3458, 2879)])
        out = tmp_path / "pairs.csv"
        assert mod.write_pairs_csv(str(cells), None, str(out)) == 1
        row = _rows(out)[0]
        assert row["parent_infections_total"] == ""
        assert row["infections_total"] == "3458"

    def test_non_json_files_are_ignored(self, tmp_path) -> None:
        cells = self._cells(tmp_path, "v10", [_cell(1e9, 20200205, 3458, 2879)])
        (cells / "notes.txt").write_text("not a cell")
        out = tmp_path / "pairs.csv"
        assert mod.write_pairs_csv(str(cells), None, str(out)) == 1

    def test_rows_sort_by_theta_age_seed(self, tmp_path) -> None:
        cells = self._cells(tmp_path, "v10", [
            _cell(1e9, 20200206, 2, 0),
            _cell(1e4, 20200205, 1, 0),
            _cell(1e9, 20200205, 3458, 2879),
        ])
        out = tmp_path / "pairs.csv"
        mod.write_pairs_csv(str(cells), None, str(out))
        keys = [(float(r["theta"]), int(r["seed"])) for r in _rows(out)]
        assert keys == sorted(keys)


class TestPathContainment:
    def test_output_outside_the_allowed_roots_is_refused(self, tmp_path) -> None:
        surface = _surface(1e9, onsets=[1], takeoff=0.5)
        with pytest.raises(ValueError):
            mod.write_surface_csv(surface, "/etc/surface.csv")

    def test_traversal_in_a_cells_directory_is_refused(self, tmp_path) -> None:
        out = str(tmp_path / "pairs.csv")
        with pytest.raises(ValueError):
            mod.write_pairs_csv("../../etc", None, out)


class TestCli:
    def test_round_trip_writes_both_csvs(self, tmp_path, capsys) -> None:
        (tmp_path / "surface.json").write_text(
            json.dumps(_surface(1e9, onsets=[0, 2879], takeoff=0.6)),
        )
        cells = tmp_path / "cells"
        cells.mkdir()
        (cells / "a.json").write_text(json.dumps(_cell(1e9, 20200205, 3458, 2879)))

        code = mod.main([
            "surface.json", "--out", "surface.csv",
            "--cells", "cells", "--pairs-out", "pairs.csv",
        ])

        assert code == 0
        assert len(_rows(tmp_path / "surface.csv")) == 1
        assert len(_rows(tmp_path / "pairs.csv")) == 1
        assert "wrote 1 paired rows" in capsys.readouterr().out

    def test_pairs_out_requires_cells(self, tmp_path) -> None:
        (tmp_path / "surface.json").write_text(
            json.dumps(_surface(1e9, onsets=[1], takeoff=0.6)),
        )
        with pytest.raises(SystemExit):
            mod.main(["surface.json", "--out", "s.csv", "--pairs-out", "p.csv"])
