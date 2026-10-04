"""Unit coverage for the CG-FLOOR-01 corner-probe readout."""

from __future__ import annotations

import json

from tools import covid_cg_floor_v1_readout as mod

THETA = 1e6
SEED = 20200205


def _tending(
    copresence: list | None = None,
    hours: list | None = None,
) -> dict:
    return {
        "enabled": {"sars_cov2_resp": True, "influenza_a": True},
        "response_probability": [0.5, 0.9],
        "report_probability": [0.3, 0.7],
        "tending_copresence_multiplier": (
            copresence if copresence is not None else [1.5, 3.0]
        ),
        "tending_hours_per_day": (
            hours if hours is not None else [2.0, 6.0]
        ),
    }


def _payload(
    arm: str = "D0_declared",
    *,
    seed: int = SEED,
    theta: float = THETA,
    rec: int = 200,
    before: int = 34,
    inf: float = 2400.0,
    units: int = 120,
    tending: dict | None = "default",
    caregiver: dict | None = "default",
    design_id: str = "covid_cg_floor_v1",
) -> dict:
    delivery = {
        "presentation_draw_mode": "once_per_course",
        "hand_reservoir_mode": "hygiene_cycle",
        "participation_propensity": {
            "mode": "party",
            "distribution": "lognormal",
            "cv": 0.8,
            "applies_to_event_classes": ["discretionary"],
        },
    }
    if caregiver == "default":
        delivery["caregiver"] = {
            "mode": "on",
            "budget_mode": "reallocate",
            "roles": {
                "cleanup": {"enabled": {"norwalk_gi": True}},
                "tending": (
                    _tending() if tending == "default" else tending
                ),
                "service": {"enabled": {"*": True}},
            },
        }
    elif caregiver is not None:
        delivery["caregiver"] = caregiver
    return {
        "design_id": design_id,
        "cell": {"theta": theta, "arm_id": arm, "seed": seed, "index": 0},
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
        "propensity_draw": {"units_drawn": units},
        "delivery": delivery,
    }


def _declared(arm_id: str = "D0_declared", overrides: dict | None = None):
    return mod.declared_corner_block(
        {"arm_id": arm_id, "overrides": overrides or {}},
    )


def _corner_declared():
    return _declared(
        "CG_LOW",
        {
            "transmission_overrides": {
                "caregiver": {
                    "tending": {
                        "tending_copresence_multiplier": [1.5, 1.5],
                        "tending_hours_per_day": [2.0, 2.0],
                    },
                },
            },
        },
    )


def test_declared_baseline_tending_is_the_shipped_range():
    declared = _declared()
    assert declared["tending"]["tending_copresence_multiplier"] == [
        1.5,
        3.0,
    ]
    assert declared["tending"]["tending_hours_per_day"] == [2.0, 6.0]


def test_declared_corner_pins_the_declared_floor():
    declared = _corner_declared()
    assert declared["tending"]["tending_copresence_multiplier"] == [
        1.5,
        1.5,
    ]
    assert declared["tending"]["tending_hours_per_day"] == [2.0, 2.0]


def test_audit_cell_clean_on_baseline_and_corner():
    assert mod.audit_cell(_payload(), _declared(), THETA) == []
    corner = _payload(arm="CG_LOW", tending=_tending([1.5, 1.5], [2.0, 2.0]))
    assert mod.audit_cell(corner, _corner_declared(), THETA) == []


def test_audit_cell_corner_on_shipped_ranges_is_a_defect():
    payload = _payload(arm="CG_LOW")  # shipped ranges, not the corner
    fails = mod.audit_cell(payload, _corner_declared(), THETA)
    assert any("tending_copresence_multiplier" in f for f in fails)
    assert any("tending_hours_per_day" in f for f in fails)


def test_audit_cell_shipped_on_corner_ranges_is_a_defect():
    payload = _payload(tending=_tending([1.5, 1.5], [2.0, 2.0]))
    fails = mod.audit_cell(payload, _declared(), THETA)
    assert any("tending_copresence_multiplier" in f for f in fails)


def test_audit_cell_missing_tending_block_is_a_design_defect():
    payload = _payload(
        caregiver={"mode": "on", "roles": {"cleanup": {}}},
    )
    fails = mod.audit_cell(payload, _declared(), THETA)
    assert any("roles.tending" in f for f in fails)


def test_audit_cell_wrong_arm_id():
    fails = mod.audit_cell(_payload(arm="CG_OFF"), _declared(), THETA)
    assert any("arm_id" in f for f in fails)


def test_audit_cell_design_id_mismatch():
    fails = mod.audit_cell(
        _payload(design_id="covid_theta_refit_v1"), _declared(), THETA,
    )
    assert any("design_id" in f for f in fails)


def test_row_stats_witnesses():
    payload = _payload()
    payload["aboard_window_by_route"] = {"caregiver": 30, "droplet": 70}
    payload["during_quarantine_by_route"] = {"caregiver": 0}
    stats = mod._row_stats([payload])
    assert stats["caregiver_route_pooled"]["aboard_window"] == 30
    assert stats["aboard_window_caregiver_share"] == 0.3


def test_row_stats_aboard_share_none_without_tallies():
    stats = mod._row_stats([_payload()])
    assert stats["aboard_window_caregiver_share"] is None


def test_row_triggers_fires_on_clause_pass():
    payloads = [
        _payload(seed=SEED + i, rec=197, before=34) for i in range(6)
    ]
    trigger = mod._row_triggers(THETA, "CG_LOW", mod._row_stats(payloads))
    assert trigger is not None
    assert "CLAUSE-PASS" in trigger["triggers"]


def test_replication_check_bit_identical(tmp_path):
    own_dir = tmp_path / "own"
    ref_dir = tmp_path / "ref"
    own_dir.mkdir()
    ref_dir.mkdir()
    own = _payload()
    ref = _payload()
    ref["design_id"] = "covid_theta_refit_floor_v1"
    ref["cell"]["index"] = 7
    (own_dir / "cell-0.json").write_text(json.dumps(own))
    (ref_dir / "cell-0.json").write_text(json.dumps(ref))
    rep = mod.replication_check(str(own_dir), {THETA: str(ref_dir)})
    row = rep["theta=1e+06"]
    assert row["n_paired"] == 1
    assert row["n_identical"] == 1
    assert row["bit_identical"] is True


def test_replication_check_reports_leaf_diffs(tmp_path):
    own_dir = tmp_path / "own"
    ref_dir = tmp_path / "ref"
    own_dir.mkdir()
    ref_dir.mkdir()
    own = _payload()
    ref = _payload(rec=199)
    ref["design_id"] = "covid_theta_refit_floor_v1"
    (own_dir / "cell-0.json").write_text(json.dumps(own))
    (ref_dir / "cell-0.json").write_text(json.dumps(ref))
    rep = mod.replication_check(str(own_dir), {THETA: str(ref_dir)})
    row = rep["theta=1e+06"]
    assert row["bit_identical"] is False
    assert row["max_abs_delta"] == 1
    assert row["diff_sample"][0]["path"].endswith("recorded_onsets")


def test_replication_check_skips_missing_ref_dir(tmp_path):
    own_dir = tmp_path / "own"
    own_dir.mkdir()
    (own_dir / "cell-0.json").write_text(json.dumps(_payload()))
    rep = mod.replication_check(
        str(own_dir), {THETA: str(tmp_path / "nope")},
    )
    assert "skipped" in rep["theta=1e+06"]
