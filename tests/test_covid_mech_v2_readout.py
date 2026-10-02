"""COVID-MECH-V2 assay readout: per-arm echo audits, verbatim clause
scoring, seed-paired drift/marginal deltas, and the trigger grammar."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tools import covid_mech_v2_readout as mod

REPO = Path(__file__).resolve().parents[1]
RING_DESIGN = (
    REPO / "picard_framework/runs/covid_ring_cap_v1_design.json"
)
SUSC_DESIGN = (
    REPO / "picard_framework/runs/covid_susc_pool_v1_design.json"
)
SEEDS = list(range(20200205, 20200225))


def _payload(
    *,
    design_id: str,
    theta: float = 1e9,
    seed: int = 20200205,
    arm: str,
    rec: int = 200,
    before: int = 30,
    onset_day: float = -1.0,
    shedding: bool = True,
    draw_mode: str = "once_per_course",
    include_fixed_rings: bool = False,
    secretor_fraction: float | None = None,
    drawn_fraction: float | None = None,
) -> dict:
    declared = {
        "secretor_negative_fraction": secretor_fraction,
        "secretor_negative_relative_susceptibility": (
            0.0 if secretor_fraction is not None else None
        ),
    }
    resolved = {
        "secretor_negative_fraction": secretor_fraction,
        "secretor_negative_relative_susceptibility": (
            0.0 if secretor_fraction is not None else None
        ),
        "innate_nonsusceptible_fraction": 0.0,
    }
    n_agents = 3711
    frac_drawn = (
        drawn_fraction
        if drawn_fraction is not None
        else (secretor_fraction or 0.0)
    )
    drawn = round(frac_drawn * n_agents)
    return {
        "design_id": design_id,
        "cell": {"theta": theta, "arm_id": arm, "seed": seed},
        "observables": {
            "recorded_onsets": rec,
            "onsets_before_split_day": before,
        },
        "infections_total": rec,
        "index_onset_day": onset_day,
        "index_shedding_at_day0": shedding,
        "exposure_cap_include_fixed_rings": (
            include_fixed_rings or None
        ),
        "delivery": {
            "presentation_draw_mode": draw_mode,
            "hand_reservoir_mode": "hygiene_cycle",
            "exposure_cap_include_fixed_rings_engine": include_fixed_rings,
        },
        "secretor_negative": {
            "declared": declared,
            "resolved": resolved,
            "realized": {
                "agents": n_agents,
                "secretor_negative_drawn": drawn,
                "drawn_fraction": drawn / n_agents,
                "zero_susceptibility": drawn,
                "zero_susceptibility_fraction": drawn / n_agents,
            },
        },
    }


def test_arm_expectations_project_each_declared_override():
    arms = {
        a["arm_id"]: mod._arm_expectations(a)
        for a in [
            {"arm_id": "cap_on", "overrides": {}},
            {
                "arm_id": "rings_first",
                "overrides": {
                    "transmission_overrides": {
                        "exposure_cap": {"include_fixed_rings": True},
                    },
                },
            },
            {
                "arm_id": "f050",
                "overrides": {
                    "pathogen_overrides": {
                        "sars_cov2_resp": {
                            "secretor_negative_fraction": 0.5,
                            "secretor_negative_relative_susceptibility": 0.0,
                        },
                    },
                },
            },
        ]
    }
    assert arms["cap_on"] == {
        "include_fixed_rings": False,
        "secretor_fraction": None,
        "secretor_rel_susc": None,
    }
    assert arms["rings_first"]["include_fixed_rings"] is True
    assert arms["f050"]["secretor_fraction"] == pytest.approx(0.5)
    assert arms["f050"]["secretor_rel_susc"] == pytest.approx(0.0)


def _clean_ring(arm: str, **kw) -> dict:
    kw.setdefault("include_fixed_rings", arm == "rings_first")
    return _payload(design_id="covid_ring_cap_v1", arm=arm, **kw)


def test_audit_cell_accepts_a_clean_arm_cell():
    expected = {"include_fixed_rings": True,
                "secretor_fraction": None, "secretor_rel_susc": None}
    assert mod._audit_cell(
        _clean_ring("rings_first"), "covid_ring_cap_v1", expected,
    ) == []


def test_audit_cell_flags_contract_and_echo_breaks():
    expected = {"include_fixed_rings": True,
                "secretor_fraction": None, "secretor_rel_susc": None}
    fails = mod._audit_cell(
        _clean_ring("rings_first", draw_mode="daily_hazard"),
        "covid_ring_cap_v1", expected,
    )
    assert "presentation_draw_mode" in fails[0]
    fails = mod._audit_cell(
        _clean_ring("rings_first", include_fixed_rings=False),
        "covid_ring_cap_v1", expected,
    )
    assert any("include_fixed_rings" in f for f in fails)
    fails = mod._audit_cell(
        _clean_ring("rings_first", onset_day=0.0),
        "covid_ring_cap_v1", expected,
    )
    assert any("index_onset_day" in f for f in fails)


def test_secretor_echo_audit_bounds_declared_resolved_realized():
    expected = {"include_fixed_rings": False,
                "secretor_fraction": 0.5, "secretor_rel_susc": 0.0}
    good = _payload(
        design_id="covid_susc_pool_v1", arm="f050",
        secretor_fraction=0.5,
    )
    assert mod._audit_cell(good, "covid_susc_pool_v1", expected) == []
    # The override never reached the population: resolved/declared right
    # but the realized draw is zero.
    flat = _payload(
        design_id="covid_susc_pool_v1", arm="f050",
        secretor_fraction=0.5, drawn_fraction=0.0,
    )
    fails = mod._audit_cell(flat, "covid_susc_pool_v1", expected)
    assert any("realized draw" in f for f in fails)
    # A baseline arm that drew nonzero is likewise a defect.
    leaked = _payload(
        design_id="covid_susc_pool_v1", arm="declared",
        drawn_fraction=0.1,
    )
    fails = mod._audit_cell(
        leaked, "covid_susc_pool_v1",
        {"include_fixed_rings": False,
         "secretor_fraction": None, "secretor_rel_susc": None},
    )
    assert any("baseline arm drew" in f for f in fails)


def _write_cells(cells_dir: Path, payloads: list[dict]) -> None:
    cells_dir.mkdir(parents=True, exist_ok=True)
    for i, payload in enumerate(payloads):
        (cells_dir / f"cell_{i:04d}.json").write_text(json.dumps(payload))


def test_main_canary_anchor_rows_clean(tmp_path, monkeypatch):
    """The 40-cell anchor canary on both ring arms: clause reads, parent
    pairing shows zero drift on cap_on, no triggers."""
    monkeypatch.setattr(mod, "REPO_ROOT", str(tmp_path))
    design = tmp_path / "ring.json"
    shutil.copy(RING_DESIGN, design)
    payloads = [
        _clean_ring(arm, seed=s, rec=190 + (i % 5) * 8, before=30)
        for arm in ("cap_on", "rings_first")
        for i, s in enumerate(SEEDS)
    ]
    _write_cells(tmp_path / "cells", payloads)
    parents = [
        _payload(design_id="covid_theta_screen_v15_stage2",
                 arm="once_per_course", seed=s,
                 rec=190 + (i % 5) * 8, before=30)
        for i, s in enumerate(SEEDS)
    ]
    _write_cells(tmp_path / "parent", parents)
    out = tmp_path / "report.json"
    rc = mod.main([
        "--cells", str(tmp_path / "cells"), "--design", str(design),
        "--parent-cells", str(tmp_path / "parent"), "--out", str(out),
    ])
    assert rc == 0
    report = json.loads(out.read_text())
    assert report["cells_found"] == 40
    assert report["cells_expected"] == 240
    assert report["baseline_arm"] == "cap_on"
    assert report["audit_failures"] == {}
    assert report["report_immediately"] == []
    assert len(report["unsubmitted_rows"]) == 10
    cap = report["rows"]["theta=1e+09|arm=cap_on"]
    assert cap["clause"]["clause_ok"] is True
    ring = report["rows"]["theta=1e+09|arm=rings_first"]
    assert ring["clause"]["clause_ok"] is True
    pair = report["paired_vs_v15_stage2"]["theta=1e+09|arm=cap_on"]
    assert pair["delta_recorded_onsets_median"] == 0.0
    assert pair["takeoff_class_flips"] == 0
    marg = report["paired_vs_baseline"]["theta=1e+09|arm=rings_first"]
    assert marg["n_paired"] == 20


def test_main_fires_premise_collapse_and_drift(tmp_path, monkeypatch):
    """A scored rings_first anchor FAIL collapses the premise; a cap_on
    delta vs the parent is the drift trigger."""
    monkeypatch.setattr(mod, "REPO_ROOT", str(tmp_path))
    design = tmp_path / "ring.json"
    shutil.copy(RING_DESIGN, design)
    payloads = [
        _clean_ring("cap_on", seed=s, rec=250, before=40)
        for s in SEEDS
    ] + [
        _clean_ring("rings_first", seed=s, rec=2000, before=30)
        for s in SEEDS
    ]
    _write_cells(tmp_path / "cells", payloads)
    parents = [
        _payload(design_id="covid_theta_screen_v15_stage2",
                 arm="once_per_course", seed=s, rec=100, before=20)
        for s in SEEDS
    ]
    _write_cells(tmp_path / "parent", parents)
    out = tmp_path / "report.json"
    rc = mod.main([
        "--cells", str(tmp_path / "cells"), "--design", str(design),
        "--parent-cells", str(tmp_path / "parent"), "--out", str(out),
    ])
    assert rc == 0
    report = json.loads(out.read_text())
    kinds = {t["trigger"] for t in report["report_immediately"]}
    assert "anchor_premise_collapsed" in kinds
    assert "baseline_drift_vs_v15" in kinds
    ring = report["rows"]["theta=1e+09|arm=rings_first"]
    assert ring["clause"]["clause_ok"] is False


def test_main_expect_complete_flags_never_landed(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "REPO_ROOT", str(tmp_path))
    design = tmp_path / "susc.json"
    shutil.copy(SUSC_DESIGN, design)
    payloads = [
        _payload(design_id="covid_susc_pool_v1", arm="declared", seed=s)
        for s in SEEDS
    ]
    _write_cells(tmp_path / "cells", payloads)
    out = tmp_path / "report.json"
    rc = mod.main([
        "--cells", str(tmp_path / "cells"), "--design", str(design),
        "--expect-complete", "--out", str(out),
    ])
    assert rc == 0
    report = json.loads(out.read_text())
    kinds = {t["trigger"] for t in report["report_immediately"]}
    assert "row_never_landed" in kinds
    # declared lands the anchor clause on this fixture -> no collapse
    # trigger (it is the baseline arm, which the grammar does not gate).
    assert "anchor_premise_collapsed" not in kinds
