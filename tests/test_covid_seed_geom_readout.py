"""SEED-GEOM-V1 readout: declared-vs-echo audit and the both-legs test."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tools import covid_seed_geom_readout as mod

DESIGN = (
    Path(__file__).resolve().parents[1]
    / "picard_framework/runs/covid_seed_geom_v1_design.json"
)
THETA = 2.37e11
SEED = 20200205


def _payload(
    arm: str = "D0_declared",
    *,
    theta: float = THETA,
    seed: int = SEED,
    rec: int = 3000,
    before: int = 1800,
    inf: float = 3550.0,
    onset: float | None = -1.0,
    shedding: bool | None = True,
    spec: dict | None = None,
    seeded_count: int = 1,
    hosts: list[dict] | None = None,
    expo_flag: bool | None = None,
    onset_recording: dict | None = None,
    eligibility: list | None = None,
    with_ring: bool = True,
) -> dict:
    p = {
        "cell": {"theta": theta, "arm_id": arm, "seed": seed},
        "observables": {
            "recorded_onsets": rec,
            "onsets_before_split_day": before,
        },
        "infections_total": inf,
        "index_onset_day": onset,
        "index_shedding_at_day0": shedding,
        "exposure_cap_include_fixed_rings": expo_flag,
    }
    if onset_recording is not None:
        p["onset_recording"] = onset_recording
    if eligibility is not None:
        p["onset_eligibility_by_severity"] = eligibility
    if with_ring:
        p["seed_ring"] = {
            "seed_spec": spec
            or {"onset_day": -1.0, "count": 1, "role": "passenger"},
            "seeded_count": seeded_count,
            "seeded_hosts": hosts if hosts is not None else [
                {"role": "passenger"},
            ],
        }
    return p


def _declared_for(overrides: dict | None = None) -> dict:
    return mod._declared({"arm_id": "X", "overrides": overrides or {}})


def test_declared_defaults_and_corners():
    d = _declared_for()
    assert d == {
        "onset_day": -1.0, "count": 1, "role": "passenger",
        "role_removed": False, "include_fixed_rings": None,
        "onset_recording": None, "eligibility": None,
    }
    d = _declared_for({"seed_patch": {"onset_day": 6.0, "count": 8,
                                      "role": None},
                       "transmission_overrides": {
                           "exposure_cap": {"include_fixed_rings": True}},
                       "pathogen_overrides": {"sars_cov2_resp": {
                           "observation_model": {
                               "onset_recording": {"report_probability": 0.56},
                               "syndrome_case_eligibility_by_severity":
                                   [0, 0, 0, 1, 1]}}}})
    assert d["onset_day"] == 6.0 and d["count"] == 8
    assert d["role_removed"] is True and d["include_fixed_rings"] is True
    assert d["onset_recording"] == {"report_probability": 0.56}
    assert d["eligibility"] == [0, 0, 0, 1, 1]


def test_audit_cell_clean_and_each_failure():
    declared = _declared_for()
    assert mod.audit_cell(_payload(), declared) == []
    assert mod.audit_cell(_payload(with_ring=False), declared) == [
        "missing seed_ring block",
    ]
    fails = mod.audit_cell(
        _payload(spec={"onset_day": -2.0, "count": 2,
                       "role": "crew"}, seeded_count=2),
        declared,
    )
    assert any("seed_spec.onset_day" in f for f in fails)
    assert any("seed_spec.count" in f for f in fails)
    assert any("seed_spec.role" in f for f in fails)
    assert any("seeded_count" in f for f in fails)
    fails = mod.audit_cell(
        _payload(hosts=[{"role": "crew"}, {"role": "passenger"}]),
        declared,
    )
    assert fails == ["1 seeded host(s) with role outside 'passenger'"]
    fails = mod.audit_cell(_payload(onset=None), declared)
    assert fails == ["index_onset_day null on a presenting index"]
    fails = mod.audit_cell(_payload(onset=-2.5), declared)
    assert fails and "index_onset_day" in fails[0]
    fails = mod.audit_cell(_payload(expo_flag=True), declared)
    assert fails and "exposure_cap_include_fixed_rings" in fails[0]


def test_audit_cell_role_removed_and_ref_echoes():
    declared = _declared_for({"seed_patch": {"role": None}})
    assert mod.audit_cell(
        _payload(spec={"onset_day": -1.0, "count": 1}), declared,
    ) == []
    fails = mod.audit_cell(
        _payload(spec={"onset_day": -1.0, "count": 1,
                       "role": "crew"}),
        declared,
    )
    assert fails == ["seed_spec.role present on a role-removed arm"]

    ref = _declared_for({
        "pathogen_overrides": {"sars_cov2_resp": {
            "observation_model": {
                "onset_recording": {"report_probability": 0.56},
                "syndrome_case_eligibility_by_severity": [0, 0, 0, 1, 1],
            }}}})
    good = _payload(
        onset_recording={"report_probability": 0.56},
        eligibility=[0, 0, 0, 1, 1],
    )
    assert mod.audit_cell(good, ref) == []
    bad = _payload(
        onset_recording={"report_probability": 0.28},
        eligibility=[0, 0, 1, 1, 1],
    )
    fails = mod.audit_cell(bad, ref)
    assert "onset_recording echo != declared block" in fails
    assert "onset_eligibility_by_severity echo != declared ladder" in fails


def test_row_stats_takeoff_gating_and_bands():
    payloads = [
        _payload(seed=s, rec=3000, before=600, inf=3550.0)
        for s in range(20200205, 20200215)
    ]
    stats = mod._row_stats(payloads)
    assert stats["takeoff_n"] == 10
    assert stats["takeoff_before_share"]["median"] == pytest.approx(0.2)
    assert stats["timing_leg_in_band"] is True
    assert stats["truth_leg_in_band"] is False
    assert stats["both_legs"] is False
    assert stats["index_shedding_day0_fraction"] == 1.0

    stats = mod._row_stats(payloads[:4])
    assert stats["timing_leg_in_band"] is False  # < 5 takeoff seeds

    in_band = [
        _payload(seed=s, rec=200, before=100, inf=800.0)
        for s in range(20200205, 20200215)
    ]
    stats = mod._row_stats(in_band)
    assert stats["truth_leg_in_band"] is True
    assert stats["both_legs"] is False  # bshr 0.5 outside 0.173±0.10

    both = [
        _payload(seed=s, rec=200, before=34, inf=800.0)
        for s in range(20200205, 20200215)
    ]
    stats = mod._row_stats(both)
    assert stats["both_legs"] is True

    payloads = [_payload(rec=0, before=0, inf=0.0, shedding=None)]
    stats = mod._row_stats(payloads)
    assert stats["takeoff_n"] == 0
    assert stats["before_share"]["median"] is None
    assert stats["index_shedding_day0_fraction"] is None


def test_main_end_to_end(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(mod, "REPO_ROOT", str(tmp_path))
    cells_dir = tmp_path / "campaign_results/sgv/cells"
    cells_dir.mkdir(parents=True)
    design_path = tmp_path / "design.json"
    shutil.copy(DESIGN, design_path)

    cells_dir.joinpath("a.json").write_text(json.dumps(_payload()))
    cells_dir.joinpath("b.json").write_text(json.dumps(
        _payload(arm="NOPE", seed=20200206),
    ))
    cells_dir.joinpath("skip.txt").write_text("not json")

    out = tmp_path / "report.json"
    rc = mod.main([
        "--cells", str(cells_dir), "--design", str(design_path),
        "--out", str(out), "--allow-partial",
    ])
    assert rc == 0
    report = json.loads(out.read_text())
    assert report["cells_found"] == 2
    assert list(report["audit_failures"]) == ["b.json"]
    assert "theta=2.37e+11|arm=D0_declared" in report["rows"]

    capsys.readouterr()
    rc = mod.main([
        "--cells", str(cells_dir), "--design", str(design_path),
    ])
    assert rc == 2
    assert "480" in capsys.readouterr().err

    with pytest.raises(ValueError, match="escapes"):
        mod.main([
            "--cells", "/etc", "--design", str(design_path),
            "--allow-partial",
        ])
