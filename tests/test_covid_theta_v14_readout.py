"""COVID-THETA-V14 readout: selector scoring, audit, and pairing helpers."""
from __future__ import annotations

import csv
import io
import json
import shutil
from pathlib import Path

import pytest

from tools import covid_theta_screen_csv
from tools import covid_theta_v14_readout as mod


def _payload(
    arm: str = "hygiene_cycle",
    *,
    theta: float = 3.16e11,
    seed: int = 20201001,
    mode: str | None = "hygiene_cycle",
    rec: int = 20,
    before: int = 5,
    aboard: float = 3711.0,
    index_onset_day: float = -1.0,
    index_shedding: bool = True,
) -> dict:
    return {
        "design_id": "covid_theta_screen_v14",
        "cell": {
            "theta": theta,
            "arm_id": arm,
            "seed": seed,
            "infection_age_days": 0.0,
        },
        "observables": {
            "recorded_onsets": rec,
            "onsets_before_split_day": before,
        },
        "infections_total": rec * 10,
        "attack_rate": rec * 10 / aboard,
        "aboard_total": aboard,
        "index_onset_day": index_onset_day,
        "index_shedding_at_day0": index_shedding,
        "delivery": {"hand_reservoir_mode": mode},
    }


def _entry(
    theta: float,
    *,
    median: float,
    mean: float,
    ok: bool,
    takeoff: float = 0.5,
) -> dict:
    return {
        "theta": theta,
        "arm_id": "hygiene_cycle",
        "fleet_shape_ok": ok,
        "recorded_attack_rate": {"median": median, "mean": mean},
        "takeoff_probability": takeoff,
    }


def test_s3_uri_splits_bucket_and_prefix():
    bucket, prefix = mod._s3_uri("s3://bkt/campaign/x/1234/")
    assert bucket == "bkt"
    assert prefix == "campaign/x/1234/"


def test_row_side_classifies_floor_ceiling_iqr():
    assert mod._row_side(_entry(1e11, median=0.0002, mean=0.01, ok=False)) == "floor"
    assert mod._row_side(_entry(1e12, median=0.02, mean=0.04, ok=False)) == "ceiling"
    assert mod._row_side(_entry(5e11, median=0.002, mean=0.07, ok=False)) == "ceiling"
    assert mod._row_side(_entry(3e11, median=0.002, mean=0.01, ok=False)) == "iqr"
    assert mod._row_side(_entry(3e11, median=0.002, mean=0.01, ok=True)) is None


THETAS = {1e11, 1.33e11, 1.78e11, 2.37e11, 3.16e11, 4.22e11, 5.62e11, 7.5e11, 1e12}
DESIGN_ID = "covid_theta_screen_v14"


def test_audit_cell_flags_contract_breaks():
    assert mod._audit_cell(_payload(), "hygiene_cycle", THETAS, DESIGN_ID) == []
    fails = mod._audit_cell(
        _payload(mode="spike_decay"), "hygiene_cycle", THETAS, DESIGN_ID,
    )
    assert fails
    assert "hand_reservoir_mode" in fails[0]
    fails = mod._audit_cell(
        _payload(theta=9e99), "hygiene_cycle", THETAS, DESIGN_ID,
    )
    assert fails
    assert "theta" in fails[0]
    fails = mod._audit_cell(
        _payload(mode="hygiene_cycle", arm="spike_decay"),
        "hygiene_cycle", THETAS, DESIGN_ID,
    )
    assert fails
    assert "arm_id" in fails[0]


def test_evaluate_reads_interior_admissible_and_triggers():
    thetas = [1e11, 1.33e11, 1.78e11, 2.37e11, 3.16e11, 4.22e11, 5.62e11, 7.5e11, 1e12]
    interior, boundary = set(thetas[1:-1]), {thetas[0], thetas[-1]}
    rows = [
        _entry(1e11, median=0.00027, mean=0.014, ok=False),
        _entry(1.33e11, median=0.00027, mean=0.016, ok=False),
        _entry(1.78e11, median=0.0008, mean=0.018, ok=True),
        _entry(2.37e11, median=0.0028, mean=0.022, ok=True),
        _entry(7.5e11, median=0.014, mean=0.045, ok=False),
        _entry(1e12, median=0.018, mean=0.052, ok=False),
    ]
    out = mod._evaluate(rows, interior, boundary)
    assert out["admissible_thetas"] == [1.78e11, 2.37e11]
    assert not out["report_immediately"]

    # Window illusory: every interior row overshoots.
    rows = [
        _entry(t, median=0.02, mean=0.04, ok=False, takeoff=0.5)
        for t in thetas
    ]
    out = mod._evaluate(rows, interior, boundary)
    assert out["admissible_thetas"] == []
    triggers = {t["trigger"] for t in out["report_immediately"]}
    assert "window_illusory" in triggers

    # Boundary-only pass reports, never selects.
    rows = [
        _entry(1e11, median=0.002, mean=0.02, ok=True, takeoff=0.5),
        *(
            _entry(t, median=0.02, mean=0.04, ok=False, takeoff=0.5)
            for t in thetas[1:-1]
        ),
        _entry(1e12, median=0.02, mean=0.04, ok=False, takeoff=0.5),
    ]
    out = mod._evaluate(rows, interior, boundary)
    triggers = {t["trigger"] for t in out["report_immediately"]}
    assert "boundary_only_admissible" in triggers


def test_pair_row_stats_and_suppression_flag():
    cells = {
        "a.json": _payload(theta=3.16e11, seed=1, rec=10),
        "b.json": _payload(theta=3.16e11, seed=2, rec=30),
    }
    parent = {
        "pa.json": _payload(theta=3.16e11, seed=1, rec=100),
        "pb.json": _payload(theta=3.16e11, seed=2, rec=5),
        "pc.json": _payload(theta=2.37e11, seed=1, rec=50),
    }
    paired = mod._pairs(cells, parent)
    assert set(paired) == {(3.16e11, 1), (3.16e11, 2)}
    stats = mod._pair_row_stats(paired)
    row = stats[3.16e11]
    assert row["n_paired"] == 2
    # Nearest-rank median of per-pair deltas {-90, +25}.
    assert row["delta_recorded_onsets_median"] == pytest.approx(-90.0)
    assert row["delta_recorded_onsets_q95"] == pytest.approx(25.0)
    # Parent seed 2 sits below the takeoff floor; current does not.
    assert row["takeoff_class_flips"] == 1
    assert row["parent_takeoff_seeds"] == 1


def test_write_pairs_csv_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "REPO_ROOT", str(tmp_path))
    cells = {"a.json": _payload(seed=7)}
    parent = {"p.json": _payload(seed=7, rec=50)}
    paired = mod._pairs(cells, parent)
    out = tmp_path / "pairs.csv"
    n = mod._write_pairs_csv(paired, str(out))
    assert n == 1
    rows = list(csv.DictReader(io.StringIO(out.read_text())))
    assert rows[0]["seed"] == "7"
    assert rows[0]["parent_recorded_onsets"] == "50"


DESIGN_FILES = {
    "v14": Path(__file__).resolve().parents[1]
    / "picard_framework/runs/covid_theta_screen_v14_design.json",
    "v13": Path(__file__).resolve().parents[1]
    / "picard_framework/runs/covid_theta_screen_v13_design.json",
}


def _screen_payload(cell, rec: int, *, parent: bool = False) -> dict:
    """A merge-compatible lattice cell payload for one enumerate_cells cell."""
    theta, seed = cell.theta, cell.seed
    return {
        "design_id": "covid_theta_screen_v13" if parent else "covid_theta_screen_v14",
        "cell": {
            "theta": theta,
            "arm_id": cell.arm_id,
            "seed": seed,
            "infection_age_days": cell.infection_age_days,
            "imports": cell.imports,
            "index": cell.index,
            "key": cell.key,
            "scenario_id": cell.scenario_id,
        },
        "observables": {
            "scenario_id": cell.scenario_id,
            "theta": theta,
            "seed": seed,
            "recorded_onsets": rec,
            "onsets_before_split_day": 0,
            "onsets_on_or_after_split_day": rec,
            "passenger_onsets_before": 0,
            "passenger_onsets_after": rec,
            "crew_onsets_before": 0,
            "crew_onsets_after": 0,
            "campaign_specimens": 0,
            "campaign_positives": 0,
            "campaign_asymptomatic_positives": 0,
        },
        "infections_total": rec * 2,
        "attack_rate": (rec * 2) / 3711.0,
        "aboard_total": 3711,
        "first_onset_day": None,
        "index_onset_day": -1.0,
        "index_shedding_at_day0": True,
        "delivery": {"hand_reservoir_mode": "hygiene_cycle"},
        "sanitary_activity": {"visits": 1.0},
    }


class _FakePaginator:
    def __init__(self, keys):
        self._keys = keys

    def paginate(self, **_kwargs):
        return [{"Contents": [{"Key": k} for k in self._keys]}]


class _FakeS3Client:
    def __init__(self, objects):
        self._objects = objects

    def get_paginator(self, _name):
        return _FakePaginator(list(self._objects))

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(json.dumps(self._objects[Key]).encode())}


def _lattice_cells(design_path, n_seeds=20):
    design = mod.load_design(str(design_path), repo_root=mod.REPO_ROOT)
    # The v13 lattice predates arms; its cells carry arm_id=None.
    cells = [c for c in mod.enumerate_cells(design)
             if c.arm_id in (None, "hygiene_cycle")]
    by_theta: dict[float, list] = {}
    for c in cells:
        by_theta.setdefault(c.theta, []).append(c)
    return [c for group in by_theta.values() for c in group[:n_seeds]]


def test_stream_cells_lists_and_fetches_in_parallel():
    objects = {
        "pfx/cells/a.json": {"cell": {"theta": 1e11}},
        "pfx/cells/nested/b.json": {"cell": {"theta": 2e11}},
        "pfx/cells/not_a_cell.txt": None,
    }
    client = _FakeS3Client(objects)
    out = mod.stream_cells(client, "bkt", "pfx/cells/", workers=4)
    assert set(out) == {"a.json", "b.json"}
    assert out["a.json"]["cell"]["theta"] == pytest.approx(1e11)
    assert out["b.json"]["cell"]["theta"] == pytest.approx(2e11)


def test_main_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "REPO_ROOT", str(tmp_path))
    monkeypatch.setattr(covid_theta_screen_csv, "REPO_ROOT", str(tmp_path))
    v14 = tmp_path / "v14.json"
    v13 = tmp_path / "v13.json"
    shutil.copy(DESIGN_FILES["v14"], v14)
    shutil.copy(DESIGN_FILES["v13"], v13)

    cells = _lattice_cells(v14)
    payloads = {c.key: _screen_payload(c, rec=5) for c in cells}
    parents = {
        c.key: _screen_payload(c, rec=100, parent=True)
        for c in _lattice_cells(v13)
    }

    monkeypatch.setattr(mod, "_s3_client", lambda: object())

    def fake_stream(_client, _bucket, prefix):
        return dict(parents if "v13" in prefix else payloads)

    monkeypatch.setattr(mod, "stream_cells", fake_stream)

    out = tmp_path / "report.json"
    surface = tmp_path / "surface.csv"
    pairs = tmp_path / "pairs.csv"
    rc = mod.main([
        "--design", str(v14), "--s3-prefix", "s3://bkt/v14/",
        "--parent-design", str(v13), "--parent-s3-prefix", "s3://bkt/v13/",
        "--out", str(out), "--surface-out", str(surface),
        "--pairs-out", str(pairs), "--expected-cells", "1800",
        "--allow-partial",
    ])
    assert rc == 0
    report = json.loads(out.read_text())
    assert report["cells_found"] == 180
    assert report["audit_failures"] == {}
    assert report["admissible_thetas"] == pytest.approx([
        1.33e11, 1.78e11, 2.37e11, 3.16e11, 4.22e11, 5.62e11, 7.5e11,
    ])
    assert report["boundary_passing"] == pytest.approx([1e11, 1e12])
    triggers = {t["trigger"] for t in report["report_immediately"]}
    assert "takeoff_transition_outside_bracket" in triggers
    assert "suppression_shaped_delta" in triggers
    assert len(list(csv.DictReader(surface.open()))) == 9
    assert len(list(csv.DictReader(pairs.open()))) == 180
    row = report["paired_vs_v13"]["237000000000.0"]
    assert row["n_paired"] == 20
    assert row["takeoff_class_flips"] == 20
    assert row["suppression_candidate"] is True


def test_main_returns_2_when_cells_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "REPO_ROOT", str(tmp_path))
    v14 = tmp_path / "v14.json"
    shutil.copy(DESIGN_FILES["v14"], v14)
    monkeypatch.setattr(mod, "_s3_client", lambda: object())
    monkeypatch.setattr(mod, "stream_cells", lambda *_a, **_kw: {})
    rc = mod.main([
        "--design", str(v14), "--s3-prefix", "s3://bkt/v14/",
        "--expected-cells", "1800",
    ])
    assert rc == 2
