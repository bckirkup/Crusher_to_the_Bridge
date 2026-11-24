"""Bookkeeping tests for the DP-PARTICIPATION-01 day-of-acquisition readout."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location(
        "covid_dp_participation_diag",
        _ROOT / "tools" / "covid_dp_participation_diag.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _payload(seed: int, by_day: dict[str, int], shedding: bool) -> dict:
    return {
        "cell": {"theta": 1e9, "seed": seed},
        "index_shedding_at_day0": shedding,
        "seed_ring": {
            "aboard_window_acquisitions": sum(by_day.values()),
            "aboard_window_by_day": by_day,
            "aboard_window_by_route": {"droplet": sum(by_day.values())},
        },
    }


def test_day0_share_tracks_day0_acquisitions(mod):
    shares = []
    for day0 in (0, 5, 15):
        rows = [mod.cell_row(_payload(1, {"0": day0, "4": 15}, True))]
        shares.append(mod.summarize(rows)["day0_share"])
    assert shares == sorted(shares)
    assert shares[0] == 0.0
    assert shares[-1] == pytest.approx(0.5)


def test_founder_class_and_shedding_counts(mod):
    rows = [
        mod.cell_row(_payload(1, {"4": 12}, False)),
        mod.cell_row(_payload(2, {"3": 2}, True)),
        mod.cell_row(_payload(3, {}, False)),
    ]
    out = mod.summarize(rows)
    assert out["cells"] == 3
    assert out["founder_class_cells"] == 1
    assert out["index_shedding_at_day0_cells"] == 1
    assert out["founder_class_by_route"] == {"droplet": 12}
    assert sum(out["by_day"].values()) == out["acquisitions"] == 14


def test_empty_pool_has_no_share(mod):
    assert mod.summarize([mod.cell_row(_payload(1, {}, False))])["day0_share"] is None


def test_main_reads_cells_and_writes_readout(mod, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(mod, "_REPO_ROOT", tmp_path)
    block = tmp_path / "cells" / "block_a"
    block.mkdir(parents=True)
    (block / "cell_1.json").write_text(
        json.dumps(_payload(1, {"0": 3, "4": 9}, True)), encoding="utf-8",
    )
    (block / "cell_2.json").write_text(
        json.dumps(_payload(2, {"4": 1}, False)), encoding="utf-8",
    )
    assert mod.main(["--cells", "cells", "--out", "out.json"]) == 0
    written = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert written["pooled"]["acquisitions"] == 13
    assert written["pooled"]["day0_acquisitions"] == 3
    assert [row["seed"] for row in written["cells"]] == [1, 2]
    assert json.loads(capsys.readouterr().out)["pooled"]["cells"] == 2


def test_main_fails_on_empty_directory(mod, tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "_REPO_ROOT", tmp_path)
    (tmp_path / "cells").mkdir()
    assert mod.main(["--cells", "cells"]) == 1


def test_main_rejects_paths_outside_the_checkout(mod, tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "_REPO_ROOT", tmp_path / "repo")
    (tmp_path / "repo").mkdir()
    with pytest.raises(ValueError):
        mod.main(["--cells", str(tmp_path)])
