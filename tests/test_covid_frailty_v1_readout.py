"""FRAILTY-V1 readout: frailty audit, paired deltas, inert identity."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tools import covid_frailty_v1_readout as mod

DESIGN = (
    Path(__file__).resolve().parents[1]
    / "picard_framework/runs/covid_frailty_v1_design.json"
)
THETA = 2.37e11
SEED = 20200205
SCALE = THETA * (0.18 + 58.0) / 0.18


def _payload(
    arm: str = "D0_declared",
    *,
    theta: float = THETA,
    seed: int = SEED,
    rec: int = 3000,
    before: int = 1800,
    inf: float = 3550.0,
    frailty_block: dict | None = None,
    frailty_present: bool = False,
    draw_n: int = 0,
    draw_mean: float | None = None,
    draw_q05: float = 1.0,
    draw_q95: float = 1.0,
    sus_n: int = 120,
    scale: float | None = None,
    curve: dict | None = None,
    during: int | None = 7,
    during_before: int | None = 3570,
) -> dict:
    dr = {
        "model": "beta_poisson",
        "alpha": 0.18,
        "beta": 58.0,
        "susceptibility_scale": (
            THETA * (0.18 + 58.0) / 0.18 if scale is None else scale
        ),
    }
    if frailty_present or frailty_block is not None:
        dr["frailty"] = frailty_block or {
            "enabled": True, "distribution": "gamma", "cv": 1.0,
        }
    return {
        "cell": {"theta": theta, "arm_id": arm, "seed": seed},
        "observables": {
            "recorded_onsets": rec,
            "onsets_before_split_day": before,
        },
        "infections_total": inf,
        "infections_before_quarantine": during_before,
        "infections_during_quarantine": during,
        "infections_after_quarantine": 0,
        "confined_passenger_infections_during_quarantine": 5,
        "during_quarantine_by_role": {"crew": during or 0},
        "during_quarantine_by_zone_class": {"cabin": during or 0},
        "dose_response": dr,
        "susceptibility_draw": {"n": sus_n, "mean": 1e9, "q05": 1.0},
        "frailty_draw": (
            {"n": 0}
            if draw_n == 0
            else {
                "n": draw_n,
                "mean": draw_mean,
                "q05": draw_q05,
                "q25": draw_q05,
                "q50": (draw_q05 + draw_q95) / 2,
                "q75": draw_q95,
                "q95": draw_q95,
            }
        ),
        "acquisition_curve": curve or {
            "total_by_day": {"13": 100, "14": 90, "15": 80,
                             "17": 75, "18": 70, "19": 65},
            "confined_by_day": {},
        },
    }


def _declared_for(overrides: dict | None = None) -> dict:
    return mod._declared({"arm_id": "X", "overrides": overrides or {}})


def _armed(arm: str = "FRAIL_G10", **kw) -> dict:
    """A clean armed-cell payload at the declared gamma cv 1.0 corner."""
    params = {
        "frailty_present": True, "draw_n": 120, "draw_mean": 1.01,
        "draw_q05": 0.05, "draw_q95": 3.2, "sus_n": 120,
    }
    params.update(kw)
    return _payload(arm=arm, **params)


def test_declared_defaults_and_arm_corners():
    d = _declared_for()
    assert d["frailty_arm"] is False
    assert d["frailty_distribution"] is None
    assert d["frailty_cv"] is None

    d = _declared_for({
        "hazard_frailty": {"distribution": "lognormal", "cv": 2.0},
    })
    assert d["frailty_arm"] is True
    assert d["frailty_distribution"] == "lognormal"
    assert d["frailty_cv"] == pytest.approx(2.0)


def test_audit_cell_baseline_clean_and_frailty_rejects():
    declared = _declared_for()
    assert mod.audit_cell(_payload(), declared, THETA) == []
    # A baseline cell must not carry the frailty surface at all.
    fails = mod.audit_cell(
        _payload(frailty_present=True), declared, THETA,
    )
    assert any("frailty key" in f for f in fails)
    fails = mod.audit_cell(
        _payload(draw_n=5, draw_mean=1.0), declared, THETA,
    )
    assert any("frailty_draw.n > 0" in f for f in fails)


def test_audit_cell_armed_echoes_and_draws():
    declared = _declared_for(
        {"hazard_frailty": {"distribution": "gamma", "cv": 1.0}},
    )
    assert mod.audit_cell(_armed(), declared, THETA) == []

    # The echo must carry the declared corner verbatim.
    fails = mod.audit_cell(
        _armed(
            frailty_block={
                "enabled": True, "distribution": "lognormal", "cv": 1.0,
            },
        ),
        declared, THETA,
    )
    assert any("distribution" in f for f in fails)
    fails = mod.audit_cell(
        _armed(
            frailty_block={
                "enabled": True, "distribution": "gamma", "cv": 2.0,
            },
        ),
        declared, THETA,
    )
    assert any("cv" in f for f in fails)
    fails = mod.audit_cell(
        _armed(
            frailty_block={
                "enabled": False, "distribution": "gamma", "cv": 1.0,
            },
        ),
        declared, THETA,
    )
    assert any("enabled" in f for f in fails)

    # The draw set must be populated, dispersed, mean-pinned, and
    # exactly the challenged set.
    fails = mod.audit_cell(
        _armed(draw_n=0, sus_n=120), declared, THETA,
    )
    assert any("frailty_draw.n == 0" in f for f in fails)
    fails = mod.audit_cell(
        _armed(sus_n=99), declared, THETA,
    )
    assert any("challenged set" in f for f in fails)
    fails = mod.audit_cell(
        _armed(draw_mean=1.6), declared, THETA,
    )
    assert any("pinning band" in f for f in fails)
    fails = mod.audit_cell(
        _armed(draw_q05=2.0, draw_q95=1.0), declared, THETA,
    )
    assert any("degenerate" in f for f in fails)
    fails = mod.audit_cell(
        _armed(scale=THETA * (0.05 + 58.0) / 0.05), declared, THETA,
    )
    assert any("susceptibility_scale" in f for f in fails)


def test_audit_cell_inert_corner_pinned_at_one():
    declared = _declared_for(
        {"hazard_frailty": {"distribution": "gamma", "cv": 0.0}},
    )
    good = _payload(
        arm="FRAIL_INERT", frailty_block={
            "enabled": True, "distribution": "gamma", "cv": 0.0,
        }, draw_n=120, draw_mean=1.0, draw_q05=1.0, draw_q95=1.0,
    )
    assert mod.audit_cell(good, declared, THETA) == []
    bad = _payload(
        arm="FRAIL_INERT", frailty_block={
            "enabled": True, "distribution": "gamma", "cv": 0.0,
        }, draw_n=120, draw_mean=1.0, draw_q05=0.9, draw_q95=1.0,
    )
    fails = mod.audit_cell(bad, declared, THETA)
    assert any("inert corner" in f for f in fails)


def test_row_stats_legs_kink_and_draw_echo():
    row = [
        _armed(seed=s, rec=3000, before=600, inf=3550.0)
        for s in range(20200205, 20200225)
    ]
    stats = mod._row_stats(row)
    assert stats["takeoff_n"] == 20
    assert stats["truth_leg_in_band"] is False
    assert stats["timing_leg_in_band"] is True  # 0.2 within tol
    assert stats["fizzle_majority"] is False
    assert stats["kink_ratio"]["median"] == pytest.approx(70.0 / 90.0)
    assert stats["frailty_draw_mean"]["median"] == pytest.approx(1.01)
    assert stats["frailty_draw_n"]["median"] == pytest.approx(120.0)
    assert stats["frailty_draw_spread_q95_q05"]["median"] == pytest.approx(
        3.15,
    )

    in_band = [
        _armed(seed=s, rec=200, before=34, inf=800.0)
        for s in range(20200205, 20200225)
    ]
    stats = mod._row_stats(in_band)
    assert stats["both_legs"] is True


def test_paired_rows_deltas_and_inert_identity():
    base = [
        _payload(seed=s, rec=3000, before=600, inf=3550.0)
        for s in range(20200205, 20200225)
    ]
    rows = {(THETA, "D0_declared"): base}

    shifted = [
        _armed(seed=s, rec=2900, before=660, inf=3400.0)
        for s in range(20200205, 20200225)
    ]
    rows[(THETA, "FRAIL_G10")] = shifted
    # Bit-identical inert corner.
    inert = [
        _payload(
            arm="FRAIL_INERT", seed=s, rec=3000, before=600, inf=3550.0,
            frailty_block={
                "enabled": True, "distribution": "gamma", "cv": 0.0,
            }, draw_n=120, draw_mean=1.0,
        )
        for s in range(20200205, 20200225)
    ]
    rows[(THETA, "FRAIL_INERT")] = inert

    paired = mod._paired_rows(rows)
    row = paired["theta=2.37e+11|arm=FRAIL_G10"]
    assert row["n_paired"] == 20
    assert row["delta_recorded_onsets"]["median"] == pytest.approx(-100.0)
    assert row["delta_infections_total"]["median"] == pytest.approx(-150.0)
    # 660/2900 - 600/3000 = 0.2276 - 0.2 = +0.0276
    assert row["delta_before_share"]["median"] == pytest.approx(
        660.0 / 2900.0 - 0.2,
    )
    identity = paired["inert_identity"]
    assert identity["identical"] is True
    assert identity["diverged_seeds"] == []
    assert identity["max_abs_delta"]["recorded_onsets"] == pytest.approx(
        0.0, rel=0.0, abs=0.0,
    )


def test_inert_identity_flags_a_diverged_seed():
    base = [
        _payload(seed=s, rec=3000, before=600, inf=3550.0)
        for s in range(20200205, 20200225)
    ]
    inert = [
        _payload(
            arm="FRAIL_INERT", seed=s, rec=3000, before=600, inf=3550.0,
        )
        for s in range(20200205, 20200225)
    ]
    inert[3]["infections_total"] = 3400.0
    inert[7]["observables"]["recorded_onsets"] = 2900
    identity = mod._inert_identity(THETA, inert, base)
    assert identity["identical"] is False
    assert sorted(identity["diverged_seeds"]) == [20200208, 20200212]
    assert identity["max_abs_delta"]["infections_total"] == pytest.approx(
        150.0,
    )
    assert identity["max_abs_delta"]["recorded_onsets"] == pytest.approx(
        100.0,
    )


def test_main_end_to_end(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(mod, "REPO_ROOT", str(tmp_path))
    cells_dir = tmp_path / "campaign_results/fv1/cells"
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
    assert "140" in capsys.readouterr().err

    with pytest.raises(ValueError, match="escapes"):
        mod.main([
            "--cells", "/etc", "--design", str(design_path),
            "--allow-partial",
        ])
