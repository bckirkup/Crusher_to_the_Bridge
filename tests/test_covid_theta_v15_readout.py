"""COVID-THETA-V15 stage-1 readout: the once_per_course arm and its audit
echoes on the generalized v14 engine, plus the thin wrapper's defaults."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tools import covid_theta_screen_csv
from tools import covid_theta_v14_readout as engine
from tools import covid_theta_v15_readout as mod

REPO = Path(__file__).resolve().parents[1]
DESIGN_FILES = {
    "v15": REPO / "picard_framework/runs/covid_theta_screen_v15_design.json",
    "v14": REPO / "picard_framework/runs/covid_theta_screen_v14_design.json",
}
THETAS = {
    1e11, 1.33e11, 1.78e11, 2.37e11, 3.16e11, 4.22e11, 5.62e11, 7.5e11, 1e12,
}
DESIGN_ID = "covid_theta_screen_v15"
ECHOES = {
    "presentation_draw_mode": "once_per_course",
    "hand_reservoir_mode": "hygiene_cycle",
}


def _payload(
    arm: str = "once_per_course",
    *,
    theta: float = 3.16e11,
    seed: int = 20201001,
    draw_mode: str | None = "once_per_course",
    hand_mode: str | None = "hygiene_cycle",
    rec: int = 20,
    before: int = 5,
) -> dict:
    return {
        "design_id": DESIGN_ID,
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
        "attack_rate": rec * 10 / 3711.0,
        "aboard_total": 3711,
        "index_onset_day": -1.0,
        "index_shedding_at_day0": True,
        "delivery": {
            "presentation_draw_mode": draw_mode,
            "hand_reservoir_mode": hand_mode,
        },
    }


def _entry(
    theta: float,
    *,
    median: float,
    mean: float,
    ok: bool,
    takeoff: float = 0.5,
    arm: str = "once_per_course",
) -> dict:
    return {
        "theta": theta,
        "arm_id": arm,
        "fleet_shape_ok": ok,
        "recorded_attack_rate": {"median": median, "mean": mean},
        "takeoff_probability": takeoff,
    }


def test_audit_cell_enforces_v15_delivery_echoes():
    assert engine._audit_cell(
        _payload(), "once_per_course", THETAS, DESIGN_ID,
        delivery_echoes=ECHOES,
    ) == []
    fails = engine._audit_cell(
        _payload(draw_mode="daily_hazard"),
        "once_per_course", THETAS, DESIGN_ID, delivery_echoes=ECHOES,
    )
    assert fails
    assert "presentation_draw_mode" in fails[0]
    fails = engine._audit_cell(
        _payload(draw_mode=None),
        "once_per_course", THETAS, DESIGN_ID, delivery_echoes=ECHOES,
    )
    assert fails
    assert "presentation_draw_mode" in fails[0]
    fails = engine._audit_cell(
        _payload(hand_mode="spike_decay"),
        "once_per_course", THETAS, DESIGN_ID, delivery_echoes=ECHOES,
    )
    assert fails
    assert "hand_reservoir_mode" in fails[0]


def test_evaluate_scores_the_single_screen_arm():
    thetas = [
        1e11, 1.33e11, 1.78e11, 2.37e11, 3.16e11,
        4.22e11, 5.62e11, 7.5e11, 1e12,
    ]
    interior, boundary = set(thetas[1:-1]), {thetas[0], thetas[-1]}
    rows = [
        _entry(1e11, median=0.00027, mean=0.014, ok=False),
        _entry(1.33e11, median=0.0028, mean=0.018, ok=True),
        _entry(1.78e11, median=0.0028, mean=0.018, ok=True),
        _entry(7.5e11, median=0.014, mean=0.045, ok=False),
        _entry(1e12, median=0.018, mean=0.052, ok=False),
        # An arm outside the screen is never part of the verdict.
        _entry(2.37e11, median=0.0028, mean=0.018, ok=True,
               arm="daily_hazard"),
    ]
    out = engine._evaluate(rows, interior, boundary, "once_per_course")
    assert out["admissible_thetas"] == [1.33e11, 1.78e11]
    assert not out["report_immediately"]


def test_wrapper_injects_v15_audit_echoes(monkeypatch):
    seen: dict[str, list] = {}

    def fake_main(argv=None):
        seen["argv"] = list(argv or [])
        return 0

    monkeypatch.setattr(engine, "main", fake_main)
    rc = mod.main(["--design", "x.json"])
    assert rc == 0
    argv = seen["argv"]
    echoes = [argv[i + 1] for i, a in enumerate(argv) if a == "--audit-echo"]
    assert echoes == [
        "presentation_draw_mode=once_per_course",
        "hand_reservoir_mode=hygiene_cycle",
    ]
    # A caller declaring its own audit echoes replaces the wrapper set.
    seen.clear()
    mod.main(["--audit-echo", "presentation_draw_mode=daily_hazard"])
    assert "hand_reservoir_mode=hygiene_cycle" not in seen["argv"]


def _lattice_cells(design_path, arm="once_per_course", n_seeds=20):
    design = engine.load_design(str(design_path), repo_root=engine.REPO_ROOT)
    cells = [
        c for c in engine.enumerate_cells(design)
        if c.arm_id == arm
    ]
    by_theta: dict[float, list] = {}
    for c in cells:
        by_theta.setdefault(c.theta, []).append(c)
    return [c for group in by_theta.values() for c in group[:n_seeds]]


def _screen_payload(cell, rec: int, *, parent: bool = False) -> dict:
    """A merge-compatible lattice payload for one enumerate_cells cell."""
    return {
        "design_id": (
            "covid_theta_screen_v14" if parent else DESIGN_ID
        ),
        "cell": {
            "theta": cell.theta,
            "arm_id": cell.arm_id,
            "seed": cell.seed,
            "infection_age_days": cell.infection_age_days,
            "imports": cell.imports,
            "index": cell.index,
            "key": cell.key,
            "scenario_id": cell.scenario_id,
        },
        "observables": {
            "scenario_id": cell.scenario_id,
            "theta": cell.theta,
            "seed": cell.seed,
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
        "delivery": dict(ECHOES) if not parent else {
            "hand_reservoir_mode": "hygiene_cycle",
        },
        "sanitary_activity": {"visits": 1.0},
    }


def test_main_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "REPO_ROOT", str(tmp_path))
    monkeypatch.setattr(covid_theta_screen_csv, "REPO_ROOT", str(tmp_path))
    v15 = tmp_path / "v15.json"
    v14 = tmp_path / "v14.json"
    shutil.copy(DESIGN_FILES["v15"], v15)
    shutil.copy(DESIGN_FILES["v14"], v14)

    cells = _lattice_cells(v15)
    payloads = {c.key: _screen_payload(c, rec=5) for c in cells}
    parents = {
        c.key: _screen_payload(c, rec=100, parent=True)
        for c in _lattice_cells(v14, arm="hygiene_cycle")
    }

    monkeypatch.setattr(engine, "_s3_client", lambda: object())

    def fake_stream(_client, _bucket, prefix):
        return dict(parents if "v14" in prefix else payloads)

    monkeypatch.setattr(engine, "stream_cells", fake_stream)

    out = tmp_path / "report.json"
    rc = mod.main([
        "--design", str(v15), "--s3-prefix", "s3://bkt/v15/",
        "--parent-design", str(v14), "--parent-s3-prefix", "s3://bkt/v14/",
        "--out", str(out), "--expected-cells", "1800",
        "--allow-partial",
    ])
    assert rc == 0
    report = json.loads(out.read_text())
    assert report["cells_found"] == 180
    assert report["audit_failures"] == {}
    assert report["admissible_thetas"] == pytest.approx([
        1.33e11, 1.78e11, 2.37e11, 3.16e11, 4.22e11, 5.62e11, 7.5e11,
    ])
    # The pairing key follows the declared parent's tag.
    assert "paired_vs_v14" in report
    assert "paired_vs_v13" not in report
    row = report["paired_vs_v14"]["316000000000.0"]
    assert row["n_paired"] == 20
    assert row["takeoff_class_flips"] == 20
