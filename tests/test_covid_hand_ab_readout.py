"""COVID-HAND-AB-01 readout: mode echo audit and seed-paired arm deltas."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from tools import covid_hand_ab_readout as mod

DESIGN = (
    Path(__file__).resolve().parents[1]
    / "picard_framework/runs/covid_hand_ab_v1_design.json"
)
THETA = 2.37e11
SEED = 20200205


def _payload(
    arm: str = "hygiene_cycle",
    *,
    theta: float = THETA,
    seed: int = SEED,
    mode: str | None = "hygiene_cycle",
    rec: int = 3000,
    before: int = 500,
    inf: float | None = 3550.0,
    inf_before: float | None = 3400.0,
    inf_during: float | None = 150.0,
    spec: dict | None = None,
    index_onset_day: float = -1.0,
    index_shedding: bool = True,
    aboard_route: dict | None = None,
    during_route: dict | None = None,
) -> dict:
    return {
        "cell": {"theta": theta, "arm_id": arm, "seed": seed},
        "observables": {
            "recorded_onsets": rec,
            "onsets_before_split_day": before,
        },
        "infections_total": inf,
        "infections_before_quarantine": inf_before,
        "infections_during_quarantine": inf_during,
        "during_quarantine_by_route": during_route,
        "aboard_window_by_route": aboard_route,
        "index_onset_day": index_onset_day,
        "index_shedding_at_day0": index_shedding,
        "seed_spec": spec
        or {"count": 1, "onset_day": -1.0, "role": "passenger"},
        "delivery": {"hand_reservoir_mode": mode},
    }


def _declared_for(overrides: dict | None = None) -> dict:
    return mod._declared({"arm_id": "X", "overrides": overrides or {}})


def test_declared_mode_reads_the_transmission_override():
    assert _declared_for()["hand_reservoir_mode"] == "hygiene_cycle"
    d = _declared_for({
        "transmission_overrides": {"hand_reservoir_mode": "spike_decay"},
    })
    assert d["hand_reservoir_mode"] == "spike_decay"


def test_audit_cell_accepts_the_matching_mode():
    declared = _declared_for()
    assert mod.audit_cell(_payload(), declared, THETA) == []


def test_audit_cell_flags_a_mode_mismatch():
    declared = _declared_for({
        "transmission_overrides": {"hand_reservoir_mode": "spike_decay"},
    })
    fails = mod.audit_cell(_payload(mode="hygiene_cycle"), declared, THETA)
    assert fails and "hand_reservoir_mode" in fails[0]


def test_audit_cell_flags_index_geometry_breaks():
    declared = _declared_for()
    fails = mod.audit_cell(
        _payload(index_onset_day=1.0), declared, THETA,
    )
    assert fails and "index_onset_day" in fails[0]
    fails = mod.audit_cell(
        _payload(index_shedding=False), declared, THETA,
    )
    assert fails and "index_shedding_at_day0" in fails[0]
    fails = mod.audit_cell(
        _payload(spec={"count": 2, "onset_day": -1.0, "role": "passenger"}),
        declared, THETA,
    )
    assert fails and "seed_spec.count" in fails[0]


def test_audit_cell_skips_the_spec_when_none_is_emitted():
    # The covid_hand_ab_v1 design does not enable seed_ring_readout, so
    # its cells emit no seed spec anywhere; the spec assertions are
    # inert rather than failing every real payload.
    declared = _declared_for()
    payload = _payload()
    del payload["seed_spec"]
    assert mod.audit_cell(payload, declared, THETA) == []
    nested = _payload()
    del nested["seed_spec"]
    nested["seed_ring"] = {"seed_spec": {"count": 2}}
    fails = mod.audit_cell(nested, declared, THETA)
    assert fails
    assert "seed_spec.count" in fails[0]


def test_main_paired_rows_report_seed_paired_deltas(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "REPO_ROOT", str(tmp_path))
    cells_dir = tmp_path / "cells"
    cells_dir.mkdir()
    design_path = tmp_path / "design.json"
    shutil.copy(DESIGN, design_path)
    for i, seed in enumerate(range(SEED, SEED + 20)):
        cells_dir.joinpath(f"a_{i:03d}.json").write_text(json.dumps(
            _payload(arm="hygiene_cycle", seed=seed, rec=3000, inf=3550.0),
        ))
        cells_dir.joinpath(f"b_{i:03d}.json").write_text(json.dumps(
            _payload(
                arm="spike_decay", seed=seed, rec=2000, inf=3000.0,
                mode="spike_decay",
            ),
        ))
    out = tmp_path / "report.json"
    rc = mod.main([
        "--cells", str(cells_dir), "--design", str(design_path),
        "--out", str(out), "--allow-partial",
    ])
    assert rc == 0
    report = json.loads(out.read_text())
    assert report["cells_found"] == 40
    assert report["cells_expected"] == 60
    assert report["audit_failures"] == {}
    paired = report["paired_rows"]
    key = "theta=2.37e+11|spike_decay_minus_hygiene_cycle"
    assert paired[key]["paired_seeds"] == 20
    # baseline(hygiene)=3000 - arm(spike_decay)=2000 => +1000 delta
    assert paired[key]["delta_recorded_onsets"]["median"] == 1000.0
    assert paired[key]["delta_infections_total"]["median"] == 550.0
    assert paired[key]["takeoff_class_flips"] == 0
    assert set(report["rows"]) == {
        "theta=2.37e+11|arm=hygiene_cycle",
        "theta=2.37e+11|arm=spike_decay",
    }
