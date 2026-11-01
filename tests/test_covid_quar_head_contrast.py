"""
test_covid_quar_head_contrast.py — QUAR-CONTRAST-01 contrast scorer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Offline-safe tests for ``tools/covid_quar_head_contrast.py``: the
arm-contrast (A0 vs A2) scoring of the HEAD engine lanes on the design's
frozen 20/50 attribution criterion. All fixtures are synthetic — no
simulation runs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import covid_quar_head_contrast as ctr  # noqa: E402

THETA = 1e9


def _lane(seed_during: dict[int, float], *, onset: float = 12) -> dict[int, dict]:
    return {
        s: {
            "seed": s,
            "recorded_onsets": onset,
            "infections_during_quarantine": d,
            "infections_total": d * 3,
        }
        for s, d in seed_during.items()
    }


def test_arm_contrast_load_bearing() -> None:
    a0 = _lane({1: 400, 2: 300, 3: 800, 4: 100})
    arm = _lane({1: 100, 2: 80, 3: 120, 4: 40})
    out = ctr._arm_contrast(a0, arm)
    assert out["n_both"] == 4
    assert out["med_ii_a0"] == pytest.approx(350.0)
    assert out["med_ii_arm"] == pytest.approx(90.0)
    assert out["shift"] == pytest.approx(-0.743, rel=1e-3)
    assert out["band"] == "load_bearing"


def test_arm_contrast_non_load_bearing() -> None:
    a0 = _lane({1: 400, 2: 300})
    arm = _lane({1: 390, 2: 330})
    out = ctr._arm_contrast(a0, arm)
    assert out["band"] == "non_load_bearing_shift"
    assert abs(out["shift"]) < 0.2


def test_arm_contrast_indeterminate() -> None:
    a0 = _lane({1: 400, 2: 300})
    arm = _lane({1: 240, 2: 180})
    out = ctr._arm_contrast(a0, arm)
    assert out["shift"] == pytest.approx(-0.4)
    assert out["band"] == "indeterminate"


def test_arm_contrast_no_overlap() -> None:
    a0 = _lane({1: 400}, onset=12)
    arm = _lane({1: 100}, onset=5)
    out = ctr._arm_contrast(a0, arm)
    assert out["n_both"] == 0
    assert out["band"] == "not eligible (no takeoff overlap)"


def test_arm_contrast_zero_a0_median() -> None:
    a0 = _lane({1: 0, 2: 0})
    arm = _lane({1: 10, 2: 20})
    out = ctr._arm_contrast(a0, arm)
    assert out["n_both"] == 2
    assert out["band"] == "not eligible (A0 conditional median 0)"


def test_arm_contrast_load_bearing_needs_all_seed_fall() -> None:
    # Conditional median falls >50% but the arm's all-seed median does
    # not fall below A0's -> indeterminate, not load-bearing.
    a0 = _lane({1: 400, 2: 300, 3: 0}, onset=12)
    a0[4] = {"seed": 4, "recorded_onsets": 5,
             "infections_during_quarantine": 0, "infections_total": 0}
    a0[5] = {"seed": 5, "recorded_onsets": 5,
             "infections_during_quarantine": 0, "infections_total": 0}
    arm = _lane({1: 100, 2: 60, 3: 50})
    arm[4] = {"seed": 4, "recorded_onsets": 15,
              "infections_during_quarantine": 50, "infections_total": 150}
    arm[5] = {"seed": 5, "recorded_onsets": 15,
              "infections_during_quarantine": 60, "infections_total": 180}
    out = ctr._arm_contrast(a0, arm)
    assert out["shift"] <= -0.5
    assert out["all_seed_median"]["arm"] >= out["all_seed_median"]["a0"]
    assert out["band"] == "indeterminate"


def test_engine_parity_median_delta() -> None:
    native = _lane({1: 500, 2: 600, 3: 100})
    probe = _lane({1: 510, 2: 590})
    out = ctr._engine_parity(native, probe)
    assert out["n_shared"] == 2
    assert out["median_delta_during_quarantine"] == pytest.approx(0.0)


def _payload(seed: int, *, during: int = 40, onsets: int = 12,
             engine_class: str = "ContamTransportEngine") -> dict:
    return {
        "infections_total": during * 3,
        "attack_rate": 0.1,
        "observables": {
            "recorded_onsets": onsets,
            "onsets_before_split_day": 3,
        },
        "infections_before_quarantine": 10,
        "infections_during_quarantine": during,
        "infections_after_quarantine": 5,
        "confined_passenger_infections_during_quarantine": 7,
        "quarantine_witness": {"confined_at_activation": 2},
        "during_quarantine_by_role": {"passenger": during},
        "during_quarantine_by_zone_class": {"cabin": during},
        "during_quarantine_by_route": {"droplet": during},
        "transport_engine": {
            "requested": "native",
            "engine_class": engine_class,
            "n_airflow_paths": 2258,
            "total_flow_m3h": 2940000.0,
        },
    }


def test_main_end_to_end(tmp_path, monkeypatch, capsys) -> None:
    from picard_framework.covid_boarding_screen import (
        enumerate_cells,
        load_design,
    )
    design = load_design(
        ctr.ATTRIBUTION_DESIGN_REL, repo_root=str(REPO_ROOT),
    )
    cells_by_arm = {
        arm: [
            c for c in enumerate_cells(design)
            if c.theta == THETA and c.arm_id == arm
        ]
        for arm in ctr.ARMS
    }
    native_dir = tmp_path / "native"
    for arm, cells in cells_by_arm.items():
        for cell in cells[:4]:
            native_dir.mkdir(parents=True, exist_ok=True)
            during = 400 if arm == "A0_declared" else 100
            (native_dir / cell.key).write_text(
                json.dumps(_payload(cell.seed, during=during)),
                encoding="utf-8",
            )
    # S8707-confined outputs must live under the real repo root;
    # results/ is gitignored scratch space.
    out_csv = REPO_ROOT / "results/test_head_contrast/surface.csv"
    out_json = REPO_ROOT / "results/test_head_contrast/summary.json"
    monkeypatch.setattr(sys, "argv", [
        "ctr",
        "--lane", f"native={native_dir}",
        "--out-csv", str(out_csv),
        "--out-json", str(out_json),
        "--repo-root", str(REPO_ROOT),
    ])
    try:
        assert ctr.main() == 0
        summary = json.loads(out_json.read_text(encoding="utf-8"))
        assert (
            summary["lanes"]["native"]["contrast"]["band"]
            == "load_bearing"
        )
        assert summary["lanes"]["native"]["contrast"]["n_both"] == 4
        assert (
            summary["settled_d62f10d_contrast"]["band"] == "load_bearing"
        )
        header = out_csv.read_text(encoding="utf-8").splitlines()[0]
        assert "engine_lane" in header
    finally:
        out_csv.unlink(missing_ok=True)
        out_json.unlink(missing_ok=True)
        (REPO_ROOT / "results/test_head_contrast").rmdir()
    capsys.readouterr()
