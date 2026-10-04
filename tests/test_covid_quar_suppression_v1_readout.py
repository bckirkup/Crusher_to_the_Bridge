"""Unit coverage for the DP-BELIEF-01-D4 quarantine-suppression readout."""

from __future__ import annotations

import json

from tools import covid_quar_suppression_v1_readout as mod

THETA = 1e6
SEED = 20200205

SOP017_EXEMPT = [
    "crew_engineering",
    "crew_galley",
    "crew_general",
    "crew_medical",
]


def _witness(
    protocol_id: str = "SOP-017",
    exempt: list | None = "default",
    activated: bool = True,
) -> dict:
    return {
        "activated": activated,
        "activation_epoch": 384,
        "confined_at_activation": 2690,
        "exempt_classes": (
            SOP017_EXEMPT if exempt == "default" else exempt
        ),
        "protocol_id": protocol_id,
        "protocol_ids": [protocol_id],
        "window_days": [16, 30],
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
    during: float | None = 700.0,
    crew: int = 650,
    confined_pax: float | None = 4.0,
    witness: dict | None = "default",
    design_id: str = "covid_quar_suppression_v1",
) -> dict:
    protocol = (
        "SOP-017-ALLHANDS" if arm == "SOP017_ALLHANDS" else "SOP-017"
    )
    if witness == "default":
        witness = _witness(
            protocol_id=protocol,
            exempt=[] if arm == "SOP017_ALLHANDS" else "default",
        )
    return {
        "design_id": design_id,
        "cell": {"theta": theta, "arm_id": arm, "seed": seed, "index": 0},
        "observables": {
            "recorded_onsets": rec,
            "onsets_before_split_day": before,
        },
        "infections_total": inf,
        "infections_before_quarantine": 91.0,
        "infections_during_quarantine": during,
        "infections_after_quarantine": 8.0,
        "during_quarantine_by_role": {"crew": crew, "passenger": 4},
        "confined_passenger_infections_during_window": confined_pax,
        "quarantine_witness": witness,
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
        "delivery": {
            "presentation_draw_mode": "once_per_course",
            "hand_reservoir_mode": "hygiene_cycle",
            "participation_propensity": {
                "mode": "party",
                "distribution": "lognormal",
                "cv": 0.8,
                "applies_to_event_classes": ["discretionary"],
            },
            "caregiver": {
                "mode": "on",
                "budget_mode": "reallocate",
                "roles": {"cleanup": {}, "service": {}, "tending": {}},
            },
        },
    }


def _declared(arm_id: str = "D0_declared"):
    overrides = (
        {"scheduled_protocol_id": "SOP-017-ALLHANDS"}
        if arm_id == "SOP017_ALLHANDS"
        else {}
    )
    return mod.declared_suppression_block(
        {"arm_id": arm_id, "overrides": overrides},
    )


def test_declared_baseline_is_sop017():
    declared = _declared()
    assert declared["protocol_id"] == "SOP-017"
    assert declared["all_hands"] is False


def test_declared_off_arm_is_allhands():
    declared = _declared("SOP017_ALLHANDS")
    assert declared["protocol_id"] == "SOP-017-ALLHANDS"
    assert declared["all_hands"] is True


def test_audit_cell_clean_on_both_arms():
    assert mod.audit_cell(_payload(), _declared(), THETA) == []
    off = _payload(arm="SOP017_ALLHANDS")
    assert mod.audit_cell(
        off, _declared("SOP017_ALLHANDS"), THETA,
    ) == []


def test_audit_cell_witness_protocol_mismatch():
    payload = _payload(
        arm="SOP017_ALLHANDS",
        witness=_witness(protocol_id="SOP-017", exempt="default"),
    )
    fails = mod.audit_cell(
        payload, _declared("SOP017_ALLHANDS"), THETA,
    )
    assert any("protocol_id" in f for f in fails)
    assert any("exempt_classes" in f for f in fails)


def test_audit_cell_allhands_nonempty_exempt_is_defect():
    payload = _payload(
        arm="SOP017_ALLHANDS",
        witness=_witness(
            protocol_id="SOP-017-ALLHANDS", exempt=["crew_galley"],
        ),
    )
    fails = mod.audit_cell(
        payload, _declared("SOP017_ALLHANDS"), THETA,
    )
    assert any("exempt_classes" in f for f in fails)


def test_audit_cell_baseline_empty_exempt_is_defect():
    payload = _payload(witness=_witness(exempt=[]))
    fails = mod.audit_cell(payload, _declared(), THETA)
    assert any("exempt_classes" in f for f in fails)


def test_audit_cell_witness_not_activated():
    payload = _payload(witness=_witness(activated=False))
    fails = mod.audit_cell(payload, _declared(), THETA)
    assert any("activated" in f for f in fails)


def test_audit_cell_witness_missing():
    payload = _payload(witness=None)
    fails = mod.audit_cell(payload, _declared(), THETA)
    assert any("quarantine_witness missing" in f for f in fails)


def test_audit_cell_wrong_arm_id():
    fails = mod.audit_cell(
        _payload(arm="SOP017_PARTIAL"), _declared(), THETA,
    )
    assert any("arm_id" in f for f in fails)


def test_audit_cell_design_id_mismatch():
    fails = mod.audit_cell(
        _payload(design_id="covid_cg_floor_v1"), _declared(), THETA,
    )
    assert any("design_id" in f for f in fails)


def test_row_stats_band_fields():
    stats = mod._row_stats([_payload(during=700.0)])
    assert stats["during_band"] == [150.0, 350.0]
    assert stats["during_median_in_band"] is False
    assert stats["confined_passenger_during_window"]["median"] == 4.0
    assert stats["during_window_crew_share"] == 650.0 / 654.0


def test_row_stats_in_band_read():
    stats = mod._row_stats([_payload(during=200.0)])
    assert stats["during_median_in_band"] is True


def test_row_triggers_band_collapse_on_off_arm():
    payloads = [
        _payload(
            arm="SOP017_ALLHANDS", seed=SEED + i, during=200.0,
        )
        for i in range(6)
    ]
    trigger = mod._row_triggers(
        THETA, "SOP017_ALLHANDS", mod._row_stats(payloads),
    )
    assert trigger is not None
    assert "BAND-COLLAPSE" in trigger["triggers"]


def test_row_triggers_no_band_collapse_on_baseline():
    payloads = [
        _payload(seed=SEED + i, during=200.0) for i in range(6)
    ]
    trigger = mod._row_triggers(
        THETA, "D0_declared", mod._row_stats(payloads),
    )
    assert trigger is None or "BAND-COLLAPSE" not in trigger["triggers"]


def test_row_triggers_silent_when_out_of_band():
    payloads = [
        _payload(
            arm="SOP017_ALLHANDS", seed=SEED + i, during=700.0,
            rec=500, before=10,
        )
        for i in range(6)
    ]
    trigger = mod._row_triggers(
        THETA, "SOP017_ALLHANDS", mod._row_stats(payloads),
    )
    assert trigger is None


def test_suppression_deltas_pair_during_mass_and_crew():
    off = _payload(
        arm="SOP017_ALLHANDS", during=200.0, crew=100,
    )
    off["infections_before_quarantine"] = 95.0
    base = _payload(during=700.0, crew=650)
    deltas = mod._suppression_deltas([off], [base])
    assert deltas["n_paired"] == 1
    assert deltas["delta_infections_during_quarantine"]["median"] == -500.0
    assert deltas["delta_during_crew"]["median"] == -550.0
    assert deltas["delta_infections_before_quarantine"]["median"] == 4.0


def test_pair_suppression_only_off_arm():
    rows = {
        (THETA, "D0_declared"): [_payload()],
        (THETA, "SOP017_ALLHANDS"): [_payload(arm="SOP017_ALLHANDS")],
    }
    paired = mod._pair_suppression(rows)
    assert list(paired) == ["theta=1e+06|arm=SOP017_ALLHANDS"]
    assert paired["theta=1e+06|arm=SOP017_ALLHANDS"]["n_paired"] == 1


def test_replication_check_shared_with_cg_floor(tmp_path):
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
    assert row["bit_identical"] is True
