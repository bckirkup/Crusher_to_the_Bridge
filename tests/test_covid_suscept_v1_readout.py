"""SUSCEPT-V1 readout: susceptibility audit, both-legs, kink triggers."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tools import covid_suscept_v1_readout as mod

DESIGN = (
    Path(__file__).resolve().parents[1]
    / "picard_framework/runs/covid_suscept_v1_design.json"
)
THETA = 2.37e11
SEED = 20200205
COMPLEMENT = {"passenger": 2666, "crew": 1045}


def _payload(
    arm: str = "D0_declared",
    *,
    theta: float = THETA,
    seed: int = SEED,
    rec: int = 3000,
    before: int = 1800,
    inf: float = 3550.0,
    immune: dict | None = None,
    dose_response: dict | None = None,
    cap_active: bool = True,
    expo_flag: bool | None = None,
    onset_recording: dict | None = None,
    eligibility: list | None = None,
    draw_n: int = 120,
    draw_mean: float = 1e9,
    curve: dict | None = None,
    during: int | None = 7,
    during_before: int | None = 3570,
    confined: int | None = 5,
) -> dict:
    p = {
        "cell": {"theta": theta, "arm_id": arm, "seed": seed},
        "observables": {
            "recorded_onsets": rec,
            "onsets_before_split_day": before,
        },
        "infections_total": inf,
        "infections_before_quarantine": during_before,
        "infections_during_quarantine": during,
        "infections_after_quarantine": 0,
        "confined_passenger_infections_during_quarantine": confined,
        "during_quarantine_by_role": {"crew": during or 0},
        "during_quarantine_by_zone_class": {"cabin": during or 0},
        "during_quarantine_by_route": {"droplet_far": during or 0},
        "ship_graph_immune": immune
        or {
            "declared": {
                "immune_fraction": 0.0,
                "crew_immune_fraction": None,
            },
            "resolved": {
                "immune_ratio": 0.0,
                "crew_immune_ratio": None,
            },
            "realized": {
                "by_role": {},
                "complement_by_role": dict(COMPLEMENT),
            },
        },
        "dose_response": dose_response
        or {
            "model": "beta_poisson",
            "alpha": 0.18,
            "beta": 58.0,
            "susceptibility_scale": theta * (0.18 + 58.0) / 0.18,
        },
        "exposure_cap_active": cap_active,
        "exposure_cap_include_fixed_rings": expo_flag,
        "susceptibility_draw": {
            "n": draw_n, "mean": draw_mean, "q05": 1.0,
        },
        "acquisition_curve": curve or {
            "total_by_day": {"13": 100, "14": 90, "15": 80,
                             "17": 75, "18": 70, "19": 65},
            "confined_by_day": {},
        },
    }
    if onset_recording is not None:
        p["onset_recording"] = onset_recording
    if eligibility is not None:
        p["onset_eligibility_by_severity"] = eligibility
    return p


def _declared_for(overrides: dict | None = None) -> dict:
    return mod._declared({"arm_id": "X", "overrides": overrides or {}})


def test_declared_defaults_and_arm_corners():
    d = _declared_for()
    assert d["immune_fraction"] == pytest.approx(0.0)
    assert d["crew_immune_fraction"] is None
    assert d["frailty_alpha"] == pytest.approx(0.18)
    assert d["frailty_beta"] == pytest.approx(58.0)
    assert d["frailty_arm"] is False
    assert d["cap_enabled"] is True
    assert d["include_fixed_rings"] is None

    d = _declared_for({
        "ship_graph_overrides": {
            "immune_fraction": 0.25, "crew_immune_fraction": 0.9,
        },
        "dose_response_frailty": {"alpha": 0.05},
        "transmission_overrides": {
            "exposure_cap": {"enabled": False},
        },
    })
    assert d["immune_fraction"] == pytest.approx(0.25)
    assert d["crew_immune_fraction"] == pytest.approx(0.9)
    assert d["frailty_alpha"] == pytest.approx(0.05)
    assert d["frailty_arm"] is True
    assert d["cap_enabled"] is False


def test_audit_cell_clean_and_immune_failures():
    declared = _declared_for()
    assert mod.audit_cell(_payload(), declared, THETA) == []

    split = _declared_for({
        "ship_graph_overrides": {
            "immune_fraction": 0.25, "crew_immune_fraction": 0.9,
        },
    })
    good = _payload(immune={
        "declared": {
            "immune_fraction": 0.25, "crew_immune_fraction": 0.9,
        },
        "resolved": {
            "immune_ratio": 0.25, "crew_immune_ratio": 0.9,
        },
        "realized": {
            "by_role": {
                "passenger": int(COMPLEMENT["passenger"] * 0.25),
                "crew": int(COMPLEMENT["crew"] * 0.9),
            },
            "complement_by_role": dict(COMPLEMENT),
        },
    })
    assert mod.audit_cell(good, split, THETA) == []
    bad = _payload(immune={
        "declared": {
            "immune_fraction": 0.25, "crew_immune_fraction": 0.9,
        },
        "resolved": {
            "immune_ratio": 0.25, "crew_immune_ratio": 0.9,
        },
        "realized": {
            "by_role": {"passenger": 10, "crew": 10},
            "complement_by_role": dict(COMPLEMENT),
        },
    })
    fails = mod.audit_cell(bad, split, THETA)
    assert any("realized.by_role.passenger" in f for f in fails)
    assert any("realized.by_role.crew" in f for f in fails)

    pooled = _declared_for({
        "ship_graph_overrides": {"immune_fraction": 0.5},
    })
    good_pool = _payload(immune={
        "declared": {"immune_fraction": 0.5, "crew_immune_fraction": None},
        "resolved": {"immune_ratio": 0.5, "crew_immune_ratio": None},
        "realized": {
            "by_role": {"passenger": 1200, "crew": 655},
            "complement_by_role": dict(COMPLEMENT),
        },
    })
    assert mod.audit_cell(good_pool, pooled, THETA) == []
    bad_pool = _payload(immune={
        "declared": {"immune_fraction": 0.5, "crew_immune_fraction": None},
        "resolved": {"immune_ratio": 0.5, "crew_immune_ratio": None},
        "realized": {
            "by_role": {"passenger": 5, "crew": 5},
            "complement_by_role": dict(COMPLEMENT),
        },
    })
    fails = mod.audit_cell(bad_pool, pooled, THETA)
    assert any("realized total" in f for f in fails)


def test_audit_cell_frailty_and_cap_echoes():
    frail = _declared_for({"dose_response_frailty": {"alpha": 0.05}})
    good = _payload(dose_response={
        "model": "beta_poisson", "alpha": 0.05, "beta": 58.0,
        "susceptibility_scale": THETA * (0.05 + 58.0) / 0.05,
    })
    assert mod.audit_cell(good, frail, THETA) == []
    bad_scale = _payload(dose_response={
        "model": "beta_poisson", "alpha": 0.05, "beta": 58.0,
        "susceptibility_scale": THETA * (0.18 + 58.0) / 0.18,
    })
    fails = mod.audit_cell(bad_scale, frail, THETA)
    assert any("susceptibility_scale" in f for f in fails)
    fails = mod.audit_cell(_payload(draw_n=0), frail, THETA)
    assert any("susceptibility_draw" in f for f in fails)

    cap_off = _declared_for({
        "transmission_overrides": {
            "exposure_cap": {"enabled": False},
        },
    })
    assert mod.audit_cell(
        _payload(cap_active=False), cap_off, THETA,
    ) == []
    fails = mod.audit_cell(_payload(cap_active=True), cap_off, THETA)
    assert any("exposure_cap_active" in f for f in fails)
    cap_fr = _declared_for({
        "transmission_overrides": {
            "exposure_cap": {"include_fixed_rings": True},
        },
    })
    assert mod.audit_cell(
        _payload(expo_flag=True), cap_fr, THETA,
    ) == []


def test_audit_cell_ref_channel_echo():
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
    assert mod.audit_cell(good, ref, THETA) == []
    fails = mod.audit_cell(_payload(), ref, THETA)
    assert "onset_recording echo != declared block" in fails
    assert "onset_eligibility_by_severity echo != declared ladder" in fails


def test_row_stats_both_legs_and_discriminator():
    row = [
        _payload(seed=s, rec=3000, before=600, inf=3550.0)
        for s in range(20200205, 20200215)
    ]
    stats = mod._row_stats(row)
    assert stats["takeoff_n"] == 10
    assert stats["truth_leg_in_band"] is False
    assert stats["timing_leg_in_band"] is True  # 0.2 within tol
    assert stats["both_legs"] is False
    assert stats["fizzle_majority"] is False
    assert stats["during_dominant"] is False
    # The stub's post window (75+70+65)/3=70 vs pre (100+90+80)/3=90.
    assert stats["kink_ratio"]["median"] == pytest.approx(70.0 / 90.0)
    assert stats["during_quarantine"]["median"] == pytest.approx(7.0)
    assert stats["confined_during_quarantine"]["median"] == pytest.approx(5.0)
    assert stats["during_quarantine_by_zone_class_pooled"] == {
        "cabin": 70,
    }

    in_band = [
        _payload(seed=s, rec=200, before=34, inf=800.0)
        for s in range(20200205, 20200215)
    ]
    stats = mod._row_stats(in_band)
    assert stats["both_legs"] is True

    fizzle = [
        _payload(seed=s, rec=0, before=0, inf=0.0)
        for s in range(20200205, 20200215)
    ]
    stats = mod._row_stats(fizzle)
    assert stats["takeoff_n"] == 0
    assert stats["fizzle_majority"] is True
    assert stats["truth_leg_in_band"] is False

    deferred = [
        _payload(seed=s, rec=200, before=30, inf=800.0,
                 during=400, during_before=300)
        for s in range(20200205, 20200215)
    ]
    stats = mod._row_stats(deferred)
    assert stats["during_dominant"] is True


def test_kink_ratio_marks_a_day16_collapse():
    kinked = _payload(curve={
        "total_by_day": {"13": 100, "14": 100, "15": 100,
                         "17": 20, "18": 15, "19": 10},
        "confined_by_day": {},
    })
    assert mod._kink_ratio(kinked) == pytest.approx(0.15)
    silent = _payload(curve={"total_by_day": {}, "confined_by_day": {}})
    assert mod._kink_ratio(silent) is None


def test_main_end_to_end(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(mod, "REPO_ROOT", str(tmp_path))
    cells_dir = tmp_path / "campaign_results/sv1/cells"
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
