"""COVID-MECH-V2 fleet readout: per-arm audits, the covid.H3 surface
rows, lattice-notch trigger, and seed-paired deltas vs v15."""
from __future__ import annotations

import json
from pathlib import Path

from picard_framework.covid_boarding_screen import (
    enumerate_cells,
    load_design,
)
from tools import covid_mech_v2_fleet_readout as mod

REPO = Path(__file__).resolve().parents[1]
FLEET_DESIGN = (
    REPO / "picard_framework/runs/covid_susc_pool_v1_fleet_design.json"
)
V15_DESIGN = (
    REPO / "picard_framework/runs/covid_theta_screen_v15_design.json"
)


def _fleet_payload(
    *,
    cell,
    rec: int,
    aboard: int = 3711,
    secretor_fraction: float | None = None,
) -> dict:
    declared = {
        "secretor_negative_fraction": secretor_fraction,
        "secretor_negative_relative_susceptibility": (
            0.0 if secretor_fraction is not None else None
        ),
    }
    drawn = round((secretor_fraction or 0.0) * aboard)
    return {
        "design_id": "covid_susc_pool_v1_fleet",
        "cell": {
            "theta": cell.theta,
            "arm_id": cell.arm_id,
            "seed": cell.seed,
            "key": cell.key,
        },
        "observables": {
            "scenario_id": cell.scenario_id,
            "theta": cell.theta,
            "seed": cell.seed,
            "recorded_onsets": rec,
            "onsets_before_split_day": 0,
            "onsets_on_or_after_split_day": rec,
            "passenger_onsets_before": 0,
            "passenger_onsets_after": 0,
            "crew_onsets_before": 0,
            "crew_onsets_after": 0,
            "campaign_specimens": 0,
            "campaign_positives": 0,
            "campaign_asymptomatic_positives": 0,
            "asymptomatic_share": None,
        },
        "aboard_total": aboard,
        "infections_total": rec,
        "first_onset_day": None,
        "sanitary_activity": {"visits": 1.0},
        "delivery": {
            "presentation_draw_mode": "once_per_course",
            "hand_reservoir_mode": "hygiene_cycle",
        },
        "secretor_negative": {
            "declared": declared,
            "resolved": {
                "secretor_negative_fraction": secretor_fraction,
                "secretor_negative_relative_susceptibility": (
                    0.0 if secretor_fraction is not None else None
                ),
                "innate_nonsusceptible_fraction": 0.0,
            },
            "realized": {
                "agents": aboard,
                "secretor_negative_drawn": drawn,
                "drawn_fraction": drawn / aboard,
                "zero_susceptibility": drawn,
                "zero_susceptibility_fraction": drawn / aboard,
            },
        },
    }


def _parent_payload(*, cell, rec: int) -> dict:
    return {
        "design_id": "covid_theta_screen_v15",
        "cell": {
            "theta": cell.theta,
            "arm_id": cell.arm_id,
            "seed": cell.seed,
            "key": cell.key,
        },
        "observables": {
            "scenario_id": "diamond_princess_2020",
            "theta": cell.theta,
            "seed": cell.seed,
            "recorded_onsets": rec,
            "onsets_before_split_day": 0,
            "onsets_on_or_after_split_day": rec,
            "passenger_onsets_before": 0,
            "passenger_onsets_after": 0,
            "crew_onsets_before": 0,
            "crew_onsets_after": 0,
            "campaign_specimens": 0,
            "campaign_positives": 0,
            "campaign_asymptomatic_positives": 0,
            "asymptomatic_share": None,
        },
        "aboard_total": 3711,
        "infections_total": rec,
        "first_onset_day": None,
        "sanitary_activity": {"visits": 1.0},
        "delivery": {
            "presentation_draw_mode": "once_per_course",
            "hand_reservoir_mode": "hygiene_cycle",
        },
    }


def _write(cells_dir: Path, payloads: dict[str, dict]) -> None:
    cells_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in payloads.items():
        (cells_dir / name).write_text(json.dumps(payload))


def _synth(tmp_path: Path, *, arm_rec: dict[str, int]) -> Path:
    """One declared + one f050 cell at each of the five thetas."""
    design = load_design(str(FLEET_DESIGN))
    payloads: dict[str, dict] = {}
    for cell in enumerate_cells(design):
        if cell.arm_id not in ("declared", "f050") or cell.seed > 20201005:
            continue
        payloads[cell.key] = _fleet_payload(
            cell=cell,
            rec=arm_rec[cell.arm_id],
            secretor_fraction=0.5 if cell.arm_id == "f050" else None,
        )
    cells_dir = tmp_path / "cells"
    _write(cells_dir, payloads)
    return cells_dir


def test_lattice_offset_and_upward_trigger():
    thetas = [1.0, 10.0, 100.0]
    parent = {1.0: {"recorded_attack_rate": {"median": 0.001}},
              10.0: {"recorded_attack_rate": {"median": 0.004}},
              100.0: {"recorded_attack_rate": {"median": 0.03}}}
    assert mod._lattice_offset(0.004, 1, thetas, parent) == 0
    assert mod._lattice_offset(0.031, 1, thetas, parent) == 1
    assert mod._lattice_offset(0.0001, 1, thetas, parent) == -2
    assert mod._lattice_offset(0.001, 0, thetas, {}) is None


def _parents(tmp_path: Path) -> Path:
    """The first five seeds of each admissible v15 stage-1 row."""
    design = load_design(str(V15_DESIGN))
    parents = {
        cell.key: _parent_payload(cell=cell, rec=20)
        for cell in enumerate_cells(design)
        if cell.theta >= 1.5e11 and cell.seed <= 20201005
    }
    pdir = tmp_path / "parents"
    _write(pdir, parents)
    return pdir


def test_main_scores_rows_and_pairs(tmp_path: Path):
    cells_dir = _synth(tmp_path, arm_rec={"declared": 20, "f050": 10})
    pdir = _parents(tmp_path)
    out = REPO / "telemetry_buffer" / "test_fleet_readout_report.json"
    rc = mod.main([
        "--cells", str(cells_dir),
        "--design", str(FLEET_DESIGN),
        "--parent-design", str(V15_DESIGN),
        "--parent-cells", str(pdir),
        "--arms", "declared", "f050",
        "--out", str(out),
    ])
    assert rc == 0
    report = json.loads(out.read_text())
    out.unlink()
    assert report["cells_found"] == 50
    assert report["audit_failures"] == {}
    assert len(report["rows"]) == 10
    f050_rows = [r for r in report["rows"] if r["arm_id"] == "f050"]
    assert all(r["n_seeds"] == 5 for r in f050_rows)
    assert all(
        r["lattice_notches_up"] == -1 - i
        for i, r in enumerate(
            sorted(f050_rows, key=lambda r: r["theta"]),
        )
    )
    assert all(
        r["v15_comparator"]["median_attack"] == 20 / 3711
        for r in f050_rows
    )
    drift = report["pairing"]["baseline_vs_v15"]
    assert all(abs(s["median"]) < 1e-12 for s in drift.values())
    deltas = report["pairing"]["arm_vs_baseline"]["f050"]
    assert all(
        abs(s["median"] - (10 - 20) / 3711) < 1e-9
        for s in deltas.values()
    )
    assert report["report_immediately"] == []


def test_main_flags_wrong_resolved_fraction(tmp_path: Path):
    design = load_design(str(FLEET_DESIGN))
    payloads: dict[str, dict] = {}
    for cell in enumerate_cells(design):
        if cell.arm_id != "f050" or cell.seed != 20201001:
            continue
        bad = _fleet_payload(cell=cell, rec=10, secretor_fraction=0.5)
        bad["secretor_negative"]["resolved"][
            "secretor_negative_fraction"
        ] = 0.25
        payloads[cell.key] = bad
    cells_dir = tmp_path / "cells"
    _write(cells_dir, payloads)
    out = REPO / "telemetry_buffer" / "test_fleet_readout_audit.json"
    rc = mod.main([
        "--cells", str(cells_dir),
        "--design", str(FLEET_DESIGN),
        "--out", str(out),
    ])
    report = json.loads(out.read_text())
    out.unlink()
    assert rc == 0
    assert len(report["audit_failures"]) == 5
    assert all(
        v == ["secretor_negative resolved 0.25 != declared 0.5"]
        for v in report["audit_failures"].values()
    )
    assert report["report_immediately"][0]["trigger"] == "audit_failures"


def test_main_expect_complete_lists_missing(tmp_path: Path):
    cells_dir = _synth(tmp_path, arm_rec={"declared": 20, "f050": 10})
    out = REPO / "telemetry_buffer" / "test_fleet_readout_missing.json"
    mod.main([
        "--cells", str(cells_dir),
        "--design", str(FLEET_DESIGN),
        "--arms", "declared", "f050",
        "--expect-complete",
        "--out", str(out),
    ])
    report = json.loads(out.read_text())
    out.unlink()
    assert "_missing" in report["audit_failures"]
    assert len(report["audit_failures"]["_missing"]) == 500 - 50
