"""COVID-THETA-V15 stage-2 readout: the frozen-rule row audit, per-cell
replay contract, and clause scoring."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from tools import covid_theta_v15_stage2_readout as mod

REPO = Path(__file__).resolve().parents[1]
DESIGN_V15_S2 = (
    REPO / "picard_framework/runs/covid_theta_screen_v15_stage2_design.json"
)

LATTICE = [
    1e11, 1.33e11, 1.78e11, 2.37e11, 3.16e11, 4.22e11, 5.62e11, 7.5e11, 1e12,
]
ANCHOR = 1e9


def _payload(
    *,
    theta: float = 3.16e11,
    seed: int = 20200205,
    arm: str | None = "once_per_course",
    draw_mode: str | None = "once_per_course",
    hand_mode: str | None = "hygiene_cycle",
    rec: int = 200,
    before: int = 30,
    onset_day: float = -1.0,
    shedding: bool = True,
    infections: int | None = None,
) -> dict:
    return {
        "design_id": "covid_theta_screen_v15_stage2",
        "cell": {"theta": theta, "arm_id": arm, "seed": seed},
        "observables": {
            "recorded_onsets": rec,
            "onsets_before_split_day": before,
        },
        "infections_total": infections if infections is not None else rec,
        "index_onset_day": onset_day,
        "index_shedding_at_day0": shedding,
        "delivery": {
            "presentation_draw_mode": draw_mode,
            "hand_reservoir_mode": hand_mode,
        },
    }


def _surf_entry(theta, *, median, mean, ok=False, takeoff=0.5):
    return {
        "theta": theta,
        "arm_id": "once_per_course",
        "fleet_shape_ok": ok,
        "recorded_attack_rate": {"median": median, "mean": mean},
        "takeoff_probability": takeoff,
    }


def test_audit_cell_flags_replay_contract_breaks():
    assert mod._audit_cell(_payload(), "covid_theta_screen_v15_stage2") == []
    fails = mod._audit_cell(
        _payload(draw_mode="daily_hazard"), "covid_theta_screen_v15_stage2",
    )
    assert "presentation_draw_mode" in fails[0]
    fails = mod._audit_cell(
        _payload(onset_day=0.0), "covid_theta_screen_v15_stage2",
    )
    assert "index_onset_day" in fails[0]
    fails = mod._audit_cell(
        _payload(shedding=False), "covid_theta_screen_v15_stage2",
    )
    assert "index_shedding_at_day0" in fails[0]
    fails = mod._audit_cell(
        _payload(arm="hygiene_cycle"), "covid_theta_screen_v15_stage2",
    )
    assert "cell.arm_id" in fails[0]


def test_row_roles_rule_a_admissible_with_flanks():
    stage1 = {"admissible_thetas": [1.33e11, 1.78e11, 2.37e11, 3.16e11, 4.22e11]}
    roles, triggers = mod._row_roles(stage1, LATTICE, ANCHOR)
    assert triggers == []
    assert roles[ANCHOR] == "anchor"
    assert roles[1e11] == "flank"
    assert roles[5.62e11] == "flank"
    for t in stage1["admissible_thetas"]:
        assert roles[t] == "selected"
    assert len(roles) == 8


def test_row_roles_rule_b_straddling_pair():
    stage1 = {
        "admissible_thetas": [],
        "surface": [
            _surf_entry(1.33e11, median=0.0002, mean=0.01),   # floor
            _surf_entry(1.78e11, median=0.0002, mean=0.01),   # floor
            _surf_entry(2.37e11, median=0.03, mean=0.04),     # ceiling
            _surf_entry(3.16e11, median=0.03, mean=0.04),     # ceiling
        ],
    }
    roles, triggers = mod._row_roles(stage1, LATTICE, ANCHOR)
    assert roles[ANCHOR] == "anchor"
    assert roles[1.78e11] == "crossing"
    assert roles[2.37e11] == "crossing"
    assert roles[1.33e11] == "crossing_neighbour"
    assert roles[3.16e11] == "crossing_neighbour"
    assert triggers == []


def test_row_roles_illusory_runs_anchor_only():
    stage1 = {
        "admissible_thetas": [],
        "surface": [
            _surf_entry(t, median=0.03, mean=0.04) for t in LATTICE[1:-1]
        ],
    }
    roles, triggers = mod._row_roles(stage1, LATTICE, ANCHOR)
    assert roles == {ANCHOR: "anchor"}
    assert triggers == []


def test_clause_legs_verbatim():
    stats = {
        "takeoff_n": 10,
        "takeoff_recorded_onsets": {"median": 197.0, "q05": 180.0, "q95": 220.0},
        "takeoff_before_share": {"median": 0.17, "q05": 0.10, "q95": 0.25},
    }
    out = mod._clause(stats)
    assert out == {
        "scored": True, "count_leg": True, "timing_leg": True,
        "clause_ok": True,
    }
    stats["takeoff_recorded_onsets"]["q05"] = 200.0
    out = mod._clause(stats)
    assert out["count_leg"] is False
    assert out["clause_ok"] is False
    stats["takeoff_recorded_onsets"]["q05"] = 180.0
    stats["takeoff_before_share"]["median"] = 0.4
    out = mod._clause(stats)
    assert out["timing_leg"] is False
    assert out["clause_ok"] is False
    stats["takeoff_n"] = 4
    out = mod._clause(stats)
    assert out["scored"] is False
    assert out["clause_ok"] is False


def _write_cells(cells_dir: Path, payloads: list[dict]) -> None:
    cells_dir.mkdir(parents=True, exist_ok=True)
    for i, payload in enumerate(payloads):
        (cells_dir / f"cell_{i:04d}.json").write_text(json.dumps(payload))


def test_main_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "REPO_ROOT", str(tmp_path))
    design = tmp_path / "design.json"
    shutil.copy(DESIGN_V15_S2, design)

    # Rule (a) with a single admissible row: selected + two flanks + anchor.
    stage1 = tmp_path / "stage1.json"
    stage1.write_text(json.dumps({"admissible_thetas": [3.16e11]}))
    ruled = {ANCHOR, 2.37e11, 3.16e11, 4.22e11}
    seeds = list(range(20200205, 20200225))
    payloads = [
        _payload(theta=t, seed=s, rec=190 + (i % 5) * 8, before=30)
        for t in ruled for i, s in enumerate(seeds)
    ]
    cells_dir = tmp_path / "cells"
    _write_cells(cells_dir, payloads)

    out = tmp_path / "report.json"
    rc = mod.main([
        "--cells", str(cells_dir), "--design", str(design),
        "--stage1-report", str(stage1), "--out", str(out),
    ])
    assert rc == 0
    report = json.loads(out.read_text())
    assert report["cells_found"] == 80
    assert report["audit_failures"] == {}
    assert report["rule_missing_rows"] == []
    assert report["rule_extra_rows"] == []
    assert report["rule_rows"] == {
        "1e+09": "anchor", "2.37e+11": "flank",
        "3.16e+11": "selected", "4.22e+11": "flank",
    }
    row = report["rows"]["3.16e+11"]
    assert row["takeoff_n"] == 20
    assert row["clause"]["scored"] is True
    assert row["clause"]["clause_ok"] is True


def test_main_flags_unruled_and_missing_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "REPO_ROOT", str(tmp_path))
    design = tmp_path / "design.json"
    shutil.copy(DESIGN_V15_S2, design)
    stage1 = tmp_path / "stage1.json"
    stage1.write_text(json.dumps({"admissible_thetas": [3.16e11]}))
    seeds = list(range(20200205, 20200225))
    payloads = [
        # The anchor row plus one unruled row; the ruled rows are absent.
        *[_payload(theta=ANCHOR, seed=s) for s in seeds],
        *[_payload(theta=7.5e11, seed=s) for s in seeds],
    ]
    cells_dir = tmp_path / "cells"
    _write_cells(cells_dir, payloads)
    out = tmp_path / "report2.json"
    rc = mod.main([
        "--cells", str(cells_dir), "--design", str(design),
        "--stage1-report", str(stage1), "--out", str(out),
    ])
    assert rc == 0
    report = json.loads(out.read_text())
    assert sorted(report["rule_missing_rows"]) == [2.37e11, 3.16e11, 4.22e11]
    assert report["rule_extra_rows"] == [7.5e11]
    kinds = {t["trigger"] for t in report["report_immediately"]}
    assert "rule_row_missing" in kinds
    assert "unruled_row_submitted" in kinds
