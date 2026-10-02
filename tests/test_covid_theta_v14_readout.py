"""COVID-THETA-V14 readout: selector scoring, audit, and pairing helpers."""
from __future__ import annotations

import csv
import io

import pytest

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
