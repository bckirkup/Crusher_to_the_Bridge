"""Unit tests for the ignition-timing readout's decomposition math.

The readout only restates committed payload echoes, so its correctness
is the bookkeeping on ``seed_ring`` + ``acquisition_curve`` plus the
funnel_hosts median-infection-day classification; these pin it on
synthetic cells.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location(
        "covid_ignition_readout",
        _ROOT / "tools" / "covid_ignition_readout.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _cell_payload(
    seed: int,
    daily: dict[int, int],
    n_ab: int,
    clean: int,
    routes: dict[str, int],
    day0: int,
    recorded_onsets: int,
    inf_days: list[int],
    before: int,
) -> dict:
    return {
        "cell": {"seed": seed, "theta": 3.162e8, "arm_id": "D0_declared",
                 "key": f"k{seed}"},
        "arm_id": "D0_declared",
        "observables": {"recorded_onsets": recorded_onsets},
        "infections_before_quarantine": before,
        "acquisition_curve": {
            "total_by_day": {str(d): n for d, n in daily.items()}},
        "seed_ring": {
            "seed_spec": {"count": 1, "departure_day": 5.0,
                          "infection_age_days": 6.8, "onset_day": -1.0,
                          "role": "passenger"},
            "seeded_hosts": [{
                "agent_id": 1, "role": "passenger",
                "agent_class": "passenger_general",
                "home_zone": "PC_D13_C_F", "dining_zone": "Windjammer",
                "work_zone": "Solarium",
                "cabin_ring_size": 1, "table_ring_size": 0}],
            "index_departure_epoch": 120,
            "aboard_window_acquisitions": n_ab,
            "aboard_window_clean_bound": clean,
            "first_secondary_shed_epoch": 24,
            "aboard_window_by_route": routes,
            "aboard_window_by_day": {"0": day0},
            "yield_per_seeded_host": float(n_ab),
        },
        "funnel_hosts": {
            str(i): {"infection_day": d, "confirmed_day": None}
            for i, d in enumerate(inf_days)
        },
    }


def test_cell_record_classifies_record_timed(mod, tmp_path):
    # Fast cell: founder burst, median infection day 14 -> record-timed
    daily = {0: 20, 1: 5, 2: 10, 3: 15, 4: 30, 5: 50}
    cell = _cell_payload(
        seed=1, daily=daily, n_ab=25, clean=20,
        routes={"droplet": 23, "caregiver": 2}, day0=20,
        recorded_onsets=200, inf_days=[10, 12, 14, 14, 16], before=500)
    (tmp_path / "cell_1.json").write_text(json.dumps(cell))
    records = [mod._cell_record(str(tmp_path / "cell_1.json"))]
    r = records[0]
    assert r["takeoff"] is True
    assert r["record_timed"] is True
    assert r["median_infection_day"] == 14
    assert r["cum5"] == 130
    assert r["ignition_day"] == 3  # cumulative reaches 50 at day 3
    assert r["aboard_window_acquisitions"] == 25


def test_late_cell_not_record_timed(mod, tmp_path):
    # Slow cell: small founder pool, median infection day 25 -> late
    daily = {0: 1, 10: 5, 15: 10}
    cell = _cell_payload(
        seed=2, daily=daily, n_ab=2, clean=1,
        routes={"caregiver": 2}, day0=1,
        recorded_onsets=100, inf_days=[20, 24, 25, 26, 30], before=56)
    (tmp_path / "cell_2.json").write_text(json.dumps(cell))
    r = mod._cell_record(str(tmp_path / "cell_2.json"))
    assert r["takeoff"] is True
    assert r["record_timed"] is False
    assert r["ignition_day"] is None  # never reaches 50
    assert r["median_infection_day"] == 25


def test_dead_cell_below_takeoff_gate(mod, tmp_path):
    cell = _cell_payload(
        seed=3, daily={0: 1}, n_ab=1, clean=1,
        routes={"caregiver": 1}, day0=1,
        recorded_onsets=5, inf_days=[10], before=1)
    (tmp_path / "cell_3.json").write_text(json.dumps(cell))
    r = mod._cell_record(str(tmp_path / "cell_3.json"))
    assert r["takeoff"] is False
    assert r["record_timed"] is False


def test_absent_epochs_stay_none(mod, tmp_path):
    cell = _cell_payload(
        seed=4, daily={0: 1}, n_ab=0, clean=0,
        routes={}, day0=0,
        recorded_onsets=0, inf_days=[], before=0)
    del cell["seed_ring"]["first_secondary_shed_epoch"]
    del cell["seed_ring"]["index_departure_epoch"]
    (tmp_path / "cell_4.json").write_text(json.dumps(cell))
    r = mod._cell_record(str(tmp_path / "cell_4.json"))
    assert r["first_secondary_shed_day"] is None
    assert r["index_departure_day"] is None


def test_summary_pools_routes_and_groups(mod, tmp_path):
    fast = _cell_payload(1, {0: 20, 5: 40}, 25, 20,
                         {"droplet": 25}, 20, 200, [14, 14, 14], 60)
    slow = _cell_payload(2, {10: 5, 15: 60}, 2, 1,
                         {"caregiver": 2}, 0, 100, [25, 26], 65)
    (tmp_path / "cell_1.json").write_text(json.dumps(fast))
    (tmp_path / "cell_2.json").write_text(json.dumps(slow))
    records = [mod._cell_record(str(p))
               for p in sorted(tmp_path.glob("cell_*.json"))]
    summary = mod._summarize(records)
    assert summary["n_cells"] == 2
    assert summary["n_record_timed"] == 1
    assert summary["n_late"] == 1
    assert summary["aboard_window_route_totals"] == {
        "droplet": 25, "caregiver": 2}
    assert summary["founder_yield"]["median"] == pytest.approx(13.5)
    assert summary["founder_yield_median_record_timed"] == 25
    # fast cell cum10=60, cum15=60 -> fold 1.0; slow cum10=5, cum15=65 -> 13
    assert summary["growth_fold_10_15_median"] == pytest.approx(7.0)


def test_main_writes_evidence_json(mod, tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "_REPO_ROOT", tmp_path)
    cells_dir = tmp_path / "cells"
    cells_dir.mkdir()
    cell = _cell_payload(1, {0: 20, 5: 40}, 25, 20,
                         {"droplet": 25}, 20, 200, [14, 14, 14], 60)
    (cells_dir / "cell_1.json").write_text(json.dumps(cell))
    out = tmp_path / "evidence.json"
    rc = mod.main(["--cells", str(cells_dir), "--out", str(out)])
    assert rc == 0
    evidence = json.loads(out.read_text())
    assert evidence["summary"]["n_cells"] == 1
    assert evidence["gates"]["ignition_mass"] == 50


def test_main_fails_without_cells(mod, tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "_REPO_ROOT", tmp_path)
    rc = mod.main(["--cells", str(tmp_path), "--out",
                   str(tmp_path / "e.json")])
    assert rc == 1
