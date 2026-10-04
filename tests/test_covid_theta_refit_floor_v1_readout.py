"""Unit coverage for the THETA-REFIT-01 floor falsifier readout."""

from __future__ import annotations

from tools import covid_theta_refit_floor_v1_readout as mod

THETA = 1e8
SEED = 20200205


def _payload(
    arm: str = "D0_declared",
    *,
    seed: int = SEED,
    theta: float = THETA,
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
    design_id: str = "covid_theta_refit_floor_v1",
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
        "cell": {"theta": theta, "arm_id": arm, "seed": seed},
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


def _declared(arm_id: str = "D0_declared") -> dict:
    return mod.declared_propensity_caregiver_block(
        {"arm_id": arm_id, "overrides": {}},
    )


def test_declared_resolution_is_the_shipped_default():
    declared = _declared()
    assert declared["propensity_mode"] == "party"
    assert declared["propensity_cv"] == 0.8
    assert declared["caregiver_mode"] == "on"


def test_audit_cell_clean_on_the_baseline_arm():
    assert mod.audit_cell(_payload(), _declared(), THETA) == []


def test_audit_cell_missing_caregiver_echo_is_a_design_defect():
    fails = mod.audit_cell(_payload(caregiver=None), _declared(), THETA)
    assert any("design defect" in f for f in fails)


def test_audit_cell_caregiver_mode_mismatch():
    fails = mod.audit_cell(
        _payload(caregiver_mode="off"), _declared(), THETA,
    )
    assert any("caregiver.mode" in f for f in fails)


def test_audit_cell_missing_propensity_echo_is_a_design_defect():
    fails = mod.audit_cell(_payload(prop=None), _declared(), THETA)
    assert any("design defect" in f for f in fails)


def test_audit_cell_propensity_draw_must_land():
    fails = mod.audit_cell(_payload(units=0), _declared(), THETA)
    assert any("units_drawn" in f for f in fails)


def test_audit_cell_wrong_arm_id():
    fails = mod.audit_cell(_payload(arm="CG_OFF"), _declared(), THETA)
    assert any("arm_id" in f for f in fails)


def test_audit_cell_index_geometry():
    payload = _payload()
    payload["index_onset_day"] = 0.0
    fails = mod.audit_cell(payload, _declared(), THETA)
    assert any("index_onset_day" in f for f in fails)


def test_audit_cell_design_id_mismatch():
    fails = mod.audit_cell(
        _payload(design_id="covid_caregiver_off_v1"), _declared(), THETA,
    )
    assert any("design_id" in f for f in fails)


def test_row_stats_caregiver_route_witness():
    payload = _payload()
    payload["aboard_window_by_route"] = {"caregiver": 41, "aerosol": 10}
    payload["during_quarantine_by_route"] = {"caregiver": 7}
    stats = mod._row_stats([payload])
    assert stats["caregiver_route_pooled"]["aboard_window"] == 41
    assert stats["caregiver_route_pooled"]["during_quarantine"] == 7


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
