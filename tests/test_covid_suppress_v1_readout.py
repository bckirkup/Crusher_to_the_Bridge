"""SUPPRESS-V1 readout: scheduled-slot audit, both-legs, shape triggers."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tools import covid_suppress_v1_readout as mod

DESIGN = (
    Path(__file__).resolve().parents[1]
    / "picard_framework/runs/covid_suppress_v1_design.json"
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
    protocol_id: str = "SOP-017",
    window: tuple[int, int] = (16, 30),
    activated: bool = True,
    confined_at_activation: int | None = 3000,
    during_window: int = 7,
    during_before: int = 3570,
    during_after: int = 0,
    during_zone: dict | None = None,
    onset_curve: dict | None = None,
    acquisition_curve: dict | None = None,
    onset_recording: dict | None = None,
    eligibility: list | None = None,
) -> dict:
    p = {
        "cell": {"theta": theta, "arm_id": arm, "seed": seed},
        "observables": {
            "recorded_onsets": rec,
            "onsets_before_split_day": before,
        },
        "infections_total": inf,
        "infections_before_quarantine": during_before,
        "infections_during_quarantine": during_window if activated else None,
        "infections_after_quarantine": during_after,
        "infections_during_window": during_window,
        "during_window_by_role": {"crew": during_window},
        "during_window_by_zone_class": (
            during_zone if during_zone is not None
            else {"cabin": during_window}
        ),
        "during_window_by_route": {"droplet": during_window},
        "confined_passenger_infections_during_window": 5,
        "quarantine_witness": {
            "protocol_id": protocol_id,
            "protocol_ids": [protocol_id] if activated else None,
            "window_days": list(window),
            "activated": activated,
            "activation_epoch": window[0] * 24 if activated else None,
            "confined_at_activation": confined_at_activation,
            "exempt_classes": ["crew_galley", "crew_general"],
            "invalid_reason": None if activated else "quarantine_never_activated",
        },
        "seed_ring": {
            "seed_spec": {"count": 1, "onset_day": -1.0, "role": "passenger"},
            "seeded_count": 1,
            "seeded_hosts": [{"role": "passenger"}],
            "aboard_window_by_route": {"droplet": 5},
        },
        "onset_curve": onset_curve or {
            "10": {"passenger": 100},
            "11": {"passenger": 90},
            "13": {"passenger": 40},
            "14": {"passenger": 35},
            "15": {"passenger": 15},
            "16": {"passenger": 25, "crew": 5},
            "17": {"passenger": 25, "crew": 5},
            "18": {"passenger": 20, "crew": 5},
            "20": {"crew": 30},
            "21": {"crew": 20},
        },
        "acquisition_curve": acquisition_curve or {
            "total_by_day": {"4": 40, "5": 30, "6": 20,
                             "13": 100, "14": 90, "15": 80,
                             "16": 75, "17": 70, "18": 65},
            "confined_by_day": {"16": 30, "17": 50},
        },
    }
    if onset_recording is not None:
        p["onset_recording"] = onset_recording
    if eligibility is not None:
        p["onset_eligibility_by_severity"] = eligibility
    return p


def _declared_for(overrides: dict | None = None, arm_id: str = "X") -> dict:
    return mod._declared({"arm_id": arm_id, "overrides": overrides or {}})


def test_declared_defaults_and_swap_arms():
    d = _declared_for()
    assert d["protocol_id"] == "SOP-017"
    assert d["window"] == [16, 30]
    assert d["scoring"] is True

    d = _declared_for({
        "scheduled_protocol_window": {"start_day": 12},
        "scheduled_protocol_id": "SOP-009",
    })
    assert d["protocol_id"] == "SOP-009"
    assert d["window"] == [12, 30]

    d = _declared_for({
        "scheduled_protocol_window": {"start_day": 40, "end_day": 45},
    })
    assert d["window"] == [40, 45]

    d = _declared_for(arm_id="SOP017AH_D12")
    assert d["scoring"] is False


def test_audit_cell_clean_and_slot_failures():
    declared = _declared_for()
    assert mod.audit_cell(_payload(), declared, THETA) == []

    retimed = _declared_for({"scheduled_protocol_window": {"start_day": 4}})
    assert mod.audit_cell(
        _payload(window=(4, 30)), retimed, THETA,
    ) == []
    fails = mod.audit_cell(_payload(), retimed, THETA)
    assert any("window_days" in f for f in fails)

    swapped = _declared_for({
        "scheduled_protocol_window": {"start_day": 12},
        "scheduled_protocol_id": "SOP-009",
    })
    assert mod.audit_cell(
        _payload(protocol_id="SOP-009", window=(12, 30)), swapped, THETA,
    ) == []
    fails = mod.audit_cell(
        _payload(protocol_id="SOP-017", window=(12, 30)), swapped, THETA,
    )
    assert any("protocol_id" in f for f in fails)

    fails = mod.audit_cell(
        {**_payload(), "infections_during_window": None},
        declared, THETA,
    )
    assert any("infections_during_window" in f for f in fails)


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


def test_row_stats_both_legs_and_discriminators():
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
    # start 16: post (30+30+25)/3 vs pre (40+35+15)/3.
    assert stats["arm_start_kink"]["post_over_pre_median"] == pytest.approx(
        85.0 / 90.0
    )
    assert stats["infections_during_window"]["median"] == pytest.approx(7.0)
    assert stats["during_window_share"]["median"] == pytest.approx(
        7.0 / 3550.0
    )
    # crew onsets mean ~19.6 vs passengers 12.6 -> lag ~7 days.
    assert stats["crew_lag_days"]["median"] == pytest.approx(
        (5 * 16 + 5 * 17 + 5 * 18 + 30 * 20 + 20 * 21) / 65.0
        - (100 * 10 + 90 * 11 + 40 * 13 + 35 * 14 + 15 * 15
           + 25 * 16 + 25 * 17 + 20 * 18) / 350.0
    )
    assert stats["activated_fraction"] == pytest.approx(1.0)
    assert stats["during_window_by_zone_class_pooled"] == {"cabin": 70}

    in_band = [
        _payload(seed=s, rec=200, before=34, inf=800.0)
        for s in range(20200205, 20200215)
    ]
    assert mod._row_stats(in_band)["both_legs"] is True

    fizzle = [
        _payload(seed=s, rec=0, before=0, inf=0.0)
        for s in range(20200205, 20200215)
    ]
    stats = mod._row_stats(fizzle)
    assert stats["takeoff_n"] == 0
    assert stats["fizzle_majority"] is True


def test_row_stats_truncation_signature():
    truncated = [
        _payload(
            seed=s, rec=200, before=30, inf=800.0,
            during_window=500, during_before=250, during_after=50,
            during_zone={"cabin": 400, "crew_mess": 60, "other": 40},
        )
        for s in range(20200205, 20200215)
    ]
    stats = mod._row_stats(truncated)
    assert stats["during_dominant"] is True
    assert stats["truncation_signature"] is True

    public_pool = [
        _payload(
            seed=s, rec=200, before=30, inf=800.0,
            during_window=500, during_before=250, during_after=50,
            during_zone={"other": 480, "cabin": 20},
        )
        for s in range(20200205, 20200215)
    ]
    stats = mod._row_stats(public_pool)
    assert stats["during_dominant"] is True
    assert stats["truncation_signature"] is False


def test_paired_rows_deltas_vs_d0():
    base = [
        _payload(seed=s, rec=3000, before=600, inf=3550.0,
                 during_window=7, during_before=3570)
        for s in range(20200205, 20200215)
    ]
    arm = [
        _payload(arm="SOP017_D4", seed=s, rec=2500, before=700,
                 inf=3000.0, window=(4, 30), during_window=500,
                 during_before=2500)
        for s in range(20200205, 20200215)
    ]
    rows = {
        (THETA, "D0_declared"): base,
        (THETA, "SOP017_D4"): arm,
    }
    out = mod._paired_rows(rows)
    key = f"theta={THETA:.4g}|arm=SOP017_D4"
    entry = out[key]
    assert entry["n_paired"] == 10
    assert entry["delta_recorded_onsets"]["median"] == pytest.approx(-500.0)
    assert entry["delta_infections_total"]["median"] == pytest.approx(-550.0)
    # Post-start mass at day 4: arm = 20+100+90+80+75+70+65 vs the same
    # day on D0 -- zero when acquisition curves match (the stub's).
    assert entry["delta_post_start_mass"]["median"] == pytest.approx(0.0)


def test_main_end_to_end(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(mod, "REPO_ROOT", str(tmp_path))
    cells_dir = tmp_path / "campaign_results/suppress/cells"
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
    assert "paired_rows" in report

    capsys.readouterr()
    rc = mod.main([
        "--cells", str(cells_dir), "--design", str(design_path),
    ])
    assert rc == 2
    assert "450" in capsys.readouterr().err

    with pytest.raises(ValueError, match="escapes"):
        mod.main([
            "--cells", "/etc", "--design", str(design_path),
            "--allow-partial",
        ])
