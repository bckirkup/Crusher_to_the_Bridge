"""Unit coverage for the PROPENSITY-CV-01 cv-screen readout."""

from __future__ import annotations

import pytest

from tools import covid_propensity_cv_screen_readout as mod

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
    cv: float = 0.8,
    units: int = 120,
    prop: dict | None = "default",
    draw_mode: str = "once_per_course",
    hand_mode: str = "hygiene_cycle",
    design_id: str = "covid_propensity_cv_screen",
) -> dict:
    delivery = {
        "presentation_draw_mode": draw_mode,
        "hand_reservoir_mode": hand_mode,
    }
    if prop == "default":
        delivery["participation_propensity"] = {
            "mode": mode,
            "distribution": "lognormal",
            "cv": cv,
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
        "propensity_draw": {
            "units_drawn": units,
            "multiplier_q05": 0.35,
            "multiplier_median": 1.0,
            "multiplier_q95": 3.4,
        },
        "delivery": delivery,
    }


def _declared_for(block: dict | None, arm_id: str = "X") -> dict:
    overrides = (
        {} if block is None
        else {"participation_propensity": block}
    )
    return mod._declared({"arm_id": arm_id, "overrides": overrides})


def test_declared_resolution():
    declared = _declared_for(None)
    assert declared["propensity_mode"] == "party"
    assert declared["propensity_cv"] == pytest.approx(0.8)
    declared = _declared_for({"cv": 0.2})
    assert declared["propensity_mode"] == "party"
    assert declared["propensity_cv"] == pytest.approx(0.2)
    declared = _declared_for({"mode": "off"})
    assert declared["propensity_mode"] == "off"


def test_audit_cell_clean_on_cv_and_off_arms():
    cv_decl = _declared_for({"cv": 1.2})
    assert mod.audit_cell(
        _payload(arm="CV120", cv=1.2), cv_decl, THETA,
    ) == []
    off = _declared_for({"mode": "off"})
    assert mod.audit_cell(
        _payload(arm="PROP_OFF", mode="off", units=0), off, THETA,
    ) == []


def test_audit_cell_missing_echo_is_a_design_defect():
    declared = _declared_for(None)
    fails = mod.audit_cell(_payload(prop=None), declared, THETA)
    assert any("design defect" in f for f in fails)


def test_audit_cell_mode_mismatch():
    declared = _declared_for(None)
    fails = mod.audit_cell(_payload(mode="agent"), declared, THETA)
    assert any("participation_propensity.mode" in f for f in fails)


def test_audit_cell_cv_mismatch():
    declared = _declared_for({"cv": 1.2})
    fails = mod.audit_cell(
        _payload(arm="CV120", cv=0.8), declared, THETA,
    )
    assert any("participation_propensity.cv" in f for f in fails)


def test_audit_cell_cv_echo_tolerates_float_noise():
    declared = _declared_for({"cv": 1.2})
    assert mod.audit_cell(
        _payload(arm="CV120", cv=1.2 + 1e-12), declared, THETA,
    ) == []


def test_audit_cell_off_arm_skips_cv_echo():
    off = _declared_for({"mode": "off"})
    assert mod.audit_cell(
        _payload(arm="PROP_OFF", mode="off", cv=0.8, units=0),
        off, THETA,
    ) == []


def test_audit_cell_off_arm_must_draw_nothing():
    off = _declared_for({"mode": "off"})
    fails = mod.audit_cell(
        _payload(arm="PROP_OFF", mode="off", units=7), off, THETA,
    )
    assert any("bit-identity witness" in f for f in fails)


def test_audit_cell_armed_arm_must_draw():
    declared = _declared_for(None)
    fails = mod.audit_cell(_payload(units=0), declared, THETA)
    assert any("never landed" in f for f in fails)


def test_audit_cell_fixed_echo_and_geometry():
    declared = _declared_for(None)
    fails = mod.audit_cell(
        _payload(draw_mode="every_contact"), declared, THETA,
    )
    assert any("presentation_draw_mode" in f for f in fails)
    payload = _payload()
    payload["seed_ring"]["seed_spec"]["onset_day"] = 0.0
    fails = mod.audit_cell(payload, declared, THETA)
    assert any("seed_spec.onset_day" in f for f in fails)
    fails = mod.audit_cell(
        _payload(design_id="covid_propensity_v1"), declared, THETA,
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


class _Design:
    def __init__(self, arms):
        self.arms = arms


def _design(*cv_arms: tuple[str, float]) -> _Design:
    arms = [
        {"arm_id": arm_id, "overrides": {"participation_propensity": {"cv": cv}}}
        for arm_id, cv in cv_arms
    ]
    arms.append(
        {
            "arm_id": "PROP_OFF",
            "overrides": {"participation_propensity": {"mode": "off"}},
        }
    )
    return _Design(arms)


def test_paired_rows_curve_vs_off_baseline():
    rows = {
        (THETA, "CV040"): [
            _payload(arm="CV040", seed=SEED + i, rec=180, before=30, inf=700.0, cv=0.4)
            for i in range(14)
        ],
        (THETA, "CV200"): [
            _payload(arm="CV200", seed=SEED + i, rec=120, before=14, inf=500.0, cv=2.0)
            for i in range(14)
        ],
        (THETA, "PROP_OFF"): [
            _payload(
                arm="PROP_OFF", seed=SEED + i, rec=200, before=34,
                inf=800.0, mode="off", units=0,
            )
            for i in range(14)
        ],
    }
    design = _design(("CV040", 0.4), ("CV200", 2.0))
    pair = mod._paired_rows(design)(rows)
    assert set(pair) == {
        f"theta={THETA:.4g}|arm=CV040",
        f"theta={THETA:.4g}|arm=CV200",
    }
    out = pair[f"theta={THETA:.4g}|arm=CV040"]
    assert out["cv"] == pytest.approx(0.4)
    assert out["baseline"] == "PROP_OFF"
    assert out["n_paired"] == 14
    assert out["delta_recorded_onsets"]["median"] == pytest.approx(-20.0)
    assert out["delta_infections_total"]["median"] == pytest.approx(-100.0)
    heavy = pair[f"theta={THETA:.4g}|arm=CV200"]
    assert heavy["cv"] == pytest.approx(2.0)
    assert heavy["delta_before_share"]["median"] == pytest.approx(
        14 / 120 - 34 / 200, abs=1e-9,
    )


def test_paired_rows_orders_by_cv():
    rows = {
        (THETA, arm): [_payload(arm=arm, seed=SEED, cv=cv)]
        for arm, cv in (("CV200", 2.0), ("CV040", 0.4), ("CV120", 1.2))
    }
    rows[(THETA, "PROP_OFF")] = [
        _payload(arm="PROP_OFF", seed=SEED, mode="off", units=0)
    ]
    design = _design(("CV040", 0.4), ("CV120", 1.2), ("CV200", 2.0))
    keys = list(mod._paired_rows(design)(rows))
    assert keys == [
        f"theta={THETA:.4g}|arm=CV040",
        f"theta={THETA:.4g}|arm=CV120",
        f"theta={THETA:.4g}|arm=CV200",
    ]


def test_row_trigger_on_clause_pass():
    row = [
        _payload(
            seed=SEED + i, rec=190 + i,
            before=int(round((190 + i) * 0.173)),
        )
        for i in range(14)
    ]
    stats = mod._row_stats(row)
    trig = mod._row_triggers(THETA, "CV040", stats)
    assert trig is not None
    assert "CLAUSE-PASS" in trig["triggers"]


def test_no_trigger_on_plain_fail():
    row = [
        _payload(seed=SEED + i, rec=2000, before=1800, inf=5000.0)
        for i in range(14)
    ]
    stats = mod._row_stats(row)
    assert mod._row_triggers(THETA, "CV200", stats) is None
