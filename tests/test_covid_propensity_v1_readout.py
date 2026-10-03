"""Unit coverage for the PROPENSITY-V1 canary readout."""

from __future__ import annotations

import pytest

from tools import covid_propensity_v1_readout as mod

THETA = 1e9
SEED = 20200205


def _payload(
    arm: str = "D0_declared",
    *,
    seed: int = SEED,
    rec: int = 200,
    before: int = 34,
    inf: float = 2400.0,
    mode: str = "party",
    units: int = 120,
    prop: dict | None = "default",
    draw_mode: str = "once_per_course",
    hand_mode: str = "hygiene_cycle",
    design_id: str = "covid_propensity_v1",
) -> dict:
    delivery = {
        "presentation_draw_mode": draw_mode,
        "hand_reservoir_mode": hand_mode,
    }
    if prop == "default":
        delivery["participation_propensity"] = {
            "mode": mode,
            "distribution": "lognormal",
            "cv": 0.8,
            "applies_to_event_classes": ["discretionary"],
        }
    elif prop is not None:
        delivery["participation_propensity"] = prop
    return {
        "design_id": design_id,
        "cell": {"theta": THETA, "arm_id": arm, "seed": seed},
        "observables": {
            "recorded_onsets": rec,
            "onsets_before_split_day": before,
        },
        "infections_total": inf,
        "index_onset_day": -1.0,
        "index_shedding_at_day0": True,
        "seed_ring": {
            "seed_spec": {
                "count": 1,
                "infection_age_days": 6.8,
                "onset_day": -1.0,
                "departure_day": 5.0,
                "role": "passenger",
            },
            "seeded_count": 1,
            "seeded_hosts": [{"role": "passenger"}],
        },
        "onset_curve": {"10": {"passenger": 50}},
        "acquisition_curve": {"total_by_day": {"4": 40}},
        "propensity_draw": {
            "units_drawn": units,
            "multiplier_q05": 0.35,
            "multiplier_median": 1.0,
            "multiplier_q95": 3.4,
        },
        "delivery": delivery,
    }


def _declared_for(mode: str | None, arm_id: str = "X") -> dict:
    overrides = (
        {} if mode is None
        else {"participation_propensity": {"mode": mode}}
    )
    return mod._declared({"arm_id": arm_id, "overrides": overrides})


def test_declared_resolution():
    assert _declared_for(None)["propensity_mode"] == "party"
    assert _declared_for("off")["propensity_mode"] == "off"
    assert _declared_for("agent")["propensity_mode"] == "agent"


def test_audit_cell_clean_on_both_arms():
    base = _declared_for(None)
    assert mod.audit_cell(_payload(), base, THETA) == []
    off = _declared_for("off")
    assert mod.audit_cell(
        _payload(arm="PROP_OFF", mode="off", units=0), off, THETA,
    ) == []


def test_audit_cell_missing_echo_is_a_design_defect():
    base = _declared_for(None)
    fails = mod.audit_cell(_payload(prop=None), base, THETA)
    assert any("design defect" in f for f in fails)


def test_audit_cell_mode_mismatch():
    base = _declared_for(None)
    fails = mod.audit_cell(_payload(mode="agent"), base, THETA)
    assert any("participation_propensity.mode" in f for f in fails)


def test_audit_cell_off_arm_must_draw_nothing():
    off = _declared_for("off")
    fails = mod.audit_cell(
        _payload(arm="PROP_OFF", mode="off", units=7), off, THETA,
    )
    assert any("bit-identity witness" in f for f in fails)


def test_audit_cell_armed_arm_must_draw():
    base = _declared_for(None)
    fails = mod.audit_cell(_payload(units=0), base, THETA)
    assert any("never landed" in f for f in fails)


def test_audit_cell_fixed_echo_and_geometry():
    base = _declared_for(None)
    fails = mod.audit_cell(
        _payload(draw_mode="every_contact"), base, THETA,
    )
    assert any("presentation_draw_mode" in f for f in fails)
    payload = _payload()
    payload["seed_ring"]["seed_spec"]["onset_day"] = 0.0
    fails = mod.audit_cell(payload, base, THETA)
    assert any("seed_spec.onset_day" in f for f in fails)
    fails = mod.audit_cell(
        _payload(design_id="other"), base, THETA,
    )
    assert any("design_id" in f for f in fails)


def test_row_stats_clause_pass():
    row = [
        _payload(
            seed=SEED + i, rec=190 + i,
            before=int(round((190 + i) * 0.173)),
        )
        for i in range(14)
    ]
    stats = mod._row_stats(row)
    assert stats["takeoff_n"] == 14
    assert stats["clause"]["scored"] is True
    assert stats["clause"]["count_leg"] is True
    assert stats["clause"]["timing_leg"] is True
    assert stats["clause"]["clause_ok"] is True
    assert "PASS" in stats["row_extra"]
    assert (
        stats["propensity_units_drawn"]["median"] == pytest.approx(120.0)
    )


def test_row_stats_unscored_on_fizzles():
    row = [
        _payload(seed=SEED + i, rec=0, before=0, inf=0.0)
        for i in range(14)
    ]
    stats = mod._row_stats(row)
    assert stats["clause"]["scored"] is False
    assert stats["clause"]["clause_ok"] is False
    assert stats["fizzle_majority"] is True


def test_row_stats_clause_fail_on_miss():
    row = [
        _payload(seed=SEED + i, rec=2000, before=1800)
        for i in range(14)
    ]
    stats = mod._row_stats(row)
    assert stats["clause"]["scored"] is True
    assert stats["clause"]["clause_ok"] is False
    assert "FAIL" in stats["row_extra"]


def test_paired_rows_off_vs_declared():
    rows = {
        (THETA, "D0_declared"): [
            _payload(seed=SEED + i, rec=200, before=34, inf=800.0)
            for i in range(14)
        ],
        (THETA, "PROP_OFF"): [
            _payload(
                arm="PROP_OFF", seed=SEED + i, rec=150, before=20,
                inf=700.0, mode="off", units=0,
            )
            for i in range(14)
        ],
    }
    pair = mod._paired_rows(None)(rows)
    key = f"theta={THETA:.4g}|arm=PROP_OFF"
    out = pair[key]
    assert out["n_paired"] == 14
    assert out["delta_recorded_onsets"]["median"] == pytest.approx(-50.0)
    assert out["delta_infections_total"]["median"] == pytest.approx(
        -100.0,
    )
    assert out["delta_before_share"]["median"] == pytest.approx(
        20 / 150 - 34 / 200, abs=1e-9,
    )


def test_row_trigger_on_clause_pass():
    row = [
        _payload(
            seed=SEED + i, rec=190 + i,
            before=int(round((190 + i) * 0.173)),
        )
        for i in range(14)
    ]
    stats = mod._row_stats(row)
    trig = mod._row_triggers(THETA, "D0_declared", stats)
    assert trig is not None
    assert "CLAUSE-PASS" in trig["triggers"]


def test_no_trigger_on_plain_fail():
    row = [
        _payload(seed=SEED + i, rec=2000, before=1800, inf=5000.0)
        for i in range(14)
    ]
    stats = mod._row_stats(row)
    assert mod._row_triggers(THETA, "PROP_OFF", stats) is None
