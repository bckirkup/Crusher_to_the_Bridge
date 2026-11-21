"""Coverage tests for tools/covid_early_growth_readout.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from covid_early_growth_readout import _cum, _ignition_day, _row, main


def _cell(seed, daily, founders=5, onsets=10, before=1):
    return {
        "cell": {"seed": seed, "theta": 1.0},
        "acquisition_curve": {"total_by_day": {str(d): v for d, v in daily.items()}},
        "observables": {"recorded_onsets": onsets,
                        "onsets_before_split_day": before},
        "seed_ring": {"aboard_window_acquisitions": founders},
    }


def test_cum_and_ignition():
    acq = {"total_by_day": {"0": 10, "5": 20, "8": 30}}
    assert _cum(acq, 4) == 10
    assert _cum(acq, 5) == 30
    assert _cum(acq, 8) == 60
    assert _ignition_day({"acquisition_curve": acq}) == 8  # reaches 50 at day 8
    assert _ignition_day({"acquisition_curve": {"total_by_day": {"0": 5}}}) is None


def test_row_records_landmarks(tmp_path):
    daily = {d: 2 for d in range(35)}
    daily[8] = 100  # crosses 50 at day 8 -> record-timed
    f = tmp_path / "cell_1.json"
    f.write_text(json.dumps(_cell(1, daily)))
    r = _row(f)
    assert r["record_timed"] is True
    assert r["cum"][34] == sum(daily.values())


def test_main_reports_and_empty_dir(tmp_path, capsys):
    cells = tmp_path / "cells"
    cells.mkdir()
    (cells / "cell_1.json").write_text(json.dumps(
        _cell(1, {d: 2 for d in range(35)})))  # crosses 50 at day 25 -> late
    early = {d: 3 for d in range(35)}
    early[6] = 200  # crosses 50 at day 6 -> record-timed
    (cells / "cell_2.json").write_text(json.dumps(_cell(2, early)))
    sys.argv = ["x", "--dir", str(cells)]
    main()
    out = capsys.readouterr().out
    assert "record-timed cells (ign<=9): n=1" in out
    assert "late/non-igniting nonzero cells: n=1" in out

    empty = tmp_path / "empty"
    empty.mkdir()
    sys.argv = ["x", "--dir", str(empty)]
    with pytest.raises(SystemExit):
        main()
    sys.argv = ["x", "--dir", str(tmp_path / "missing")]
    with pytest.raises(SystemExit):
        main()
