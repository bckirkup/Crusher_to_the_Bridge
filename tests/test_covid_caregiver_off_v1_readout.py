"""Unit coverage for the CAREGIVER-ATTR-01 attribution readout."""

from __future__ import annotations

import pytest

from tools import covid_caregiver_off_v1_readout as mod

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
    caregiver: dict | None = "default",
    caregiver_mode: str = "on",
    draw_mode: str = "once_per_course",
    hand_mode: str = "hygiene_cycle",
    design_id: str = "covid_caregiver_off_v1",
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
    if caregiver == "default":
        delivery["caregiver"] = {
            "mode": caregiver_mode,
            "budget_mode": "zero_sum",
            "roles": {},
        }
    elif caregiver is not None:
        delivery["caregiver"] = caregiver
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


def _declared_for(
    prop_mode: str | None,
    caregiver_mode: str | None = None,
    arm_id: str = "X",
) -> dict:
    overrides: dict = {}
    if prop_mode is not None:
        overrides["participation_propensity"] = {"mode": prop_mode}
    if caregiver_mode is not None:
        overrides["transmission_overrides"] = {
            "caregiver": {"mode": caregiver_mode},
        }
    return mod.declared_propensity_caregiver_block(
        {"arm_id": arm_id, "overrides": overrides},
    )


def test_declared_resolution():
    base = _declared_for(None)
    assert base["propensity_mode"] == "party"
    assert base["caregiver_mode"] == "on"
    off = _declared_for("off", "off")
    assert off["propensity_mode"] == "off"
    assert off["caregiver_mode"] == "off"


def test_audit_cell_clean_on_both_arms():
    base = _declared_for(None)
    assert mod.audit_cell(_payload(), base, THETA) == []
    off = _declared_for("off", "off")
    assert mod.audit_cell(
        _payload(arm="CG_OFF", mode="off", units=0, caregiver_mode="off"),
        off, THETA,
    ) == []


def test_audit_cell_missing_caregiver_echo_is_a_design_defect():
    base = _declared_for(None)
    fails = mod.audit_cell(_payload(caregiver=None), base, THETA)
    assert any("design defect" in f for f in fails)


def test_audit_cell_caregiver_mode_mismatch():
    base = _declared_for(None)
    fails = mod.audit_cell(
        _payload(caregiver_mode="off"), base, THETA,
    )
    assert any("caregiver.mode" in f for f in fails)


def test_audit_cell_off_arm_caregiver_must_echo_off():
    off = _declared_for("off", "off")
    fails = mod.audit_cell(
        _payload(arm="CG_OFF", mode="off", units=0, caregiver_mode="on"),
        off, THETA,
    )
    assert any("caregiver.mode" in f for f in fails)


def test_audit_cell_missing_propensity_echo_is_a_design_defect():
    base = _declared_for(None)
    fails = mod.audit_cell(_payload(prop=None), base, THETA)
    assert any("design defect" in f for f in fails)


def test_audit_cell_off_arm_must_draw_nothing():
    off = _declared_for("off", "off")
    fails = mod.audit_cell(
        _payload(
            arm="CG_OFF", mode="off", units=7, caregiver_mode="off",
        ),
        off, THETA,
    )
    assert any("bit-identity witness" in f for f in fails)


def test_audit_cell_index_geometry():
    base = _declared_for(None)
    payload = _payload()
    payload["index_onset_day"] = 0.0
    fails = mod.audit_cell(payload, base, THETA)
    assert any("index_onset_day" in f for f in fails)


def test_audit_cell_design_id_mismatch():
    base = _declared_for(None)
    fails = mod.audit_cell(
        _payload(design_id="covid_propensity_v1"), base, THETA,
    )
    assert any("design_id" in f for f in fails)


def test_row_stats_caregiver_route_witness():
    d0 = _payload()
    d0["aboard_window_by_route"] = {"caregiver": 41, "aerosol": 10}
    d0["during_quarantine_by_route"] = {"caregiver": 7}
    off = _payload(arm="CG_OFF", mode="off", units=0, caregiver_mode="off")
    stats = mod._row_stats([d0])
    assert stats["caregiver_route_pooled"]["aboard_window"] == 41
    assert stats["caregiver_route_pooled"]["during_quarantine"] == 7
    off_stats = mod._row_stats([off])
    assert off_stats["caregiver_route_pooled"]["aboard_window"] == 0
    assert off_stats["caregiver_route_pooled"]["during_quarantine"] == 0


def test_paired_rows_off_vs_declared():
    rows = {
        (THETA, "D0_declared"): [
            _payload(seed=SEED + i, rec=200, before=34, inf=800.0)
            for i in range(14)
        ],
        (THETA, "CG_OFF"): [
            _payload(
                arm="CG_OFF", seed=SEED + i, rec=150, before=20,
                inf=700.0, mode="off", units=0, caregiver_mode="off",
            )
            for i in range(14)
        ],
    }
    out = mod.PAIR_VS_D0(rows)[f"theta={THETA:.4g}|arm=CG_OFF"]
    assert out["n_paired"] == 14
    assert out["baseline"] == "D0_declared"
    assert out["delta_recorded_onsets"]["median"] == pytest.approx(-50.0)
    assert out["delta_infections_total"]["median"] == pytest.approx(-100.0)
    assert out["delta_before_share"]["median"] == pytest.approx(
        20 / 150 - 34 / 200, abs=1e-9,
    )


def test_row_triggers_fires_on_clause_pass():
    payloads = [
        _payload(seed=SEED + i, rec=197, before=34) for i in range(6)
    ]
    stats = mod._row_stats(payloads)
    trigger = mod._row_triggers(THETA, "D0_declared", stats)
    assert trigger is not None
    assert "CLAUSE-PASS" in trigger["triggers"]


def test_row_triggers_quiet_on_clause_fail():
    payloads = [
        _payload(seed=SEED + i, rec=2300, before=900) for i in range(6)
    ]
    stats = mod._row_stats(payloads)
    assert mod._row_triggers(THETA, "D0_declared", stats) is None
