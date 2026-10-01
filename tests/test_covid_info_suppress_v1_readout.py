"""Unit coverage for the INFO-SUPPRESS-V1 readout."""

from __future__ import annotations

import pytest

from tools import covid_info_suppress_v1_readout as mod

THETA = 2.37e11
SEED = 20200205

IS_BLOCK = {
    "enabled": True,
    "trigger_status": "suspected",
    "response_delay_hours": 0.0,
    "self_isolation_scope": "passengers",
    "closed_zones": ["Casino", "Windjammer"],
    "route_scalars": {"direct_contact_scalar": 0.5},
}


def _payload(
    arm: str = "D0_declared",
    *,
    seed: int = SEED,
    rec: int = 3000,
    before: int = 1800,
    inf: float = 3550.0,
    info: dict | None = None,
    theta: float = THETA,
) -> dict:
    return {
        "cell": {"theta": theta, "arm_id": arm, "seed": seed},
        "observables": {
            "recorded_onsets": rec,
            "onsets_before_split_day": before,
        },
        "infections_total": inf,
        "seed_ring": {
            "seed_spec": {"count": 1, "onset_day": -1.0, "role": "passenger"},
            "seeded_count": 1,
            "seeded_hosts": [{"role": "passenger"}],
        },
        "onset_curve": {
            "10": {"passenger": 100},
            "17": {"passenger": 25, "crew": 5},
            "20": {"crew": 30},
        },
        "acquisition_curve": {
            "total_by_day": {"4": 40, "13": 100, "16": 75},
        },
        "info_suppression": info if info is not None else {},
    }


def _armed_info(**over) -> dict:
    block = dict(IS_BLOCK)
    block.update({
        "recognition_epoch": 73,
        "armed_epoch": 73,
        "closed_zones_applied": ["Casino", "Windjammer"],
        "closed_venue_ids_engine": ["Casino", "Windjammer"],
        "self_isolated_count": 700,
    })
    block.update(over)
    return block


def _declared_for(block: dict | None, arm_id: str = "X") -> dict:
    return mod._declared({
        "arm_id": arm_id,
        "overrides": {} if block is None else {"info_suppression": block},
    })


def test_declared_block_resolution():
    base = _declared_for(None)
    assert base["enabled"] is False
    assert base["block"] == {}
    armed = _declared_for(IS_BLOCK)
    assert armed["enabled"] is True
    assert armed["scope"] == "passengers"
    assert armed["closed_zones"] == ["Casino", "Windjammer"]


def test_audit_cell_clean_on_both_kinds():
    base = _declared_for(None)
    assert mod.audit_cell(_payload(info={}), base, THETA) == []
    armed = _declared_for(IS_BLOCK)
    assert mod.audit_cell(_payload(info=_armed_info()), armed, THETA) == []


def test_audit_cell_missing_block():
    armed = _declared_for(IS_BLOCK)
    payload = _payload()
    del payload["info_suppression"]
    fails = mod.audit_cell(payload, armed, THETA)
    assert "missing info_suppression block" in fails


def test_audit_cell_declared_echo_mismatch():
    armed = _declared_for(IS_BLOCK)
    fails = mod.audit_cell(
        _payload(info=_armed_info(trigger_status="confirmed")),
        armed, THETA,
    )
    assert any("trigger_status" in f for f in fails)
    fails = mod.audit_cell(
        _payload(info=_armed_info(closed_zones=["Casino"])),
        armed, THETA,
    )
    assert any("closed_zones" in f for f in fails)


def test_audit_cell_cannot_fire_witness():
    armed = _declared_for(IS_BLOCK)
    fails = mod.audit_cell(
        _payload(info=_armed_info(armed_epoch=None)), armed, THETA,
    )
    assert any("CANNOT-FIRE" in f for f in fails)


def test_audit_cell_fizzle_null_armed_is_not_cannot_fire():
    armed = _declared_for(IS_BLOCK)
    fails = mod.audit_cell(
        _payload(rec=0, before=0, inf=1.0,
                 info=_armed_info(armed_epoch=None)),
        armed, THETA,
    )
    assert not any("CANNOT-FIRE" in f for f in fails)


def test_audit_cell_baseline_armed_is_a_failure():
    base = _declared_for(None)
    fails = mod.audit_cell(_payload(info={"armed_epoch": 5}), base, THETA)
    assert fails == ["D0 cell armed a disabled mechanism"]


def test_audit_cell_zero_isolation_on_scoped_arm():
    armed = _declared_for(IS_BLOCK)
    fails = mod.audit_cell(
        _payload(info=_armed_info(self_isolated_count=0)), armed, THETA,
    )
    assert any("self_isolated_count == 0" in f for f in fails)


def test_audit_cell_seed_ring_bad_role():
    armed = _declared_for(IS_BLOCK)
    payload = _payload(info=_armed_info())
    payload["seed_ring"]["seeded_hosts"] = [{"role": "crew"}]
    fails = mod.audit_cell(payload, armed, THETA)
    assert any("seeded host" in f for f in fails)


def test_row_stats_legs_and_witnesses():
    row = [
        _payload(arm="IS01_dp_replay", seed=SEED + i, rec=200,
                 before=34, inf=800.0, info=_armed_info())
        for i in range(14)
    ]
    stats = mod._row_stats(row)
    assert stats["n"] == 14 and stats["takeoff_n"] == 14
    assert stats["truth_leg_in_band"] is True
    assert stats["timing_leg_in_band"] is True
    assert stats["both_legs"] is True
    assert stats["armed_day"]["median"] == pytest.approx(73 / 24)
    assert stats["self_isolated_count"]["median"] == pytest.approx(700.0)
    # Post-arming mass = acquisitions on/after armed day 3.04.
    assert stats["post_arming_mass"]["median"] == pytest.approx(215.0)


def test_row_stats_fizzle_majority():
    row = [
        _payload(seed=SEED + i, rec=0, before=0, inf=0.0)
        for i in range(14)
    ]
    stats = mod._row_stats(row)
    assert stats["fizzle_majority"] is True
    assert stats["both_legs"] is False


def test_paired_rows_seed_paired_deltas():
    base = [
        _payload(seed=SEED + i, rec=200, before=40, inf=800.0)
        for i in range(14)
    ]
    arm = [
        _payload(arm="IS01_dp_replay", seed=SEED + i, rec=150, before=20,
                 inf=700.0, info=_armed_info())
        for i in range(14)
    ]
    rows = {
        (THETA, "D0_declared"): base,
        (THETA, "IS01_dp_replay"): arm,
    }
    out = mod._paired_rows(rows)
    entry = out[f"theta={THETA:.4g}|arm=IS01_dp_replay"]
    assert entry["n_paired"] == 14
    assert entry["delta_recorded_onsets"]["median"] == pytest.approx(-50.0)
    assert entry["delta_infections_total"]["median"] == pytest.approx(-100.0)
    # before_share: 20/150 - 40/200
    assert entry["delta_before_share"]["median"] == pytest.approx(
        20 / 150 - 40 / 200,
    )


def test_paired_rows_skips_non_takeoff_seeds():
    base = [_payload(seed=SEED, rec=200, before=40, inf=800.0)]
    arm = [_payload(
        arm="IS02_isolation_only", seed=SEED, rec=5, before=2, inf=100.0,
        info=_armed_info(closed_zones=[], closed_zones_applied=[]),
    )]
    rows = {
        (THETA, "D0_declared"): base,
        (THETA, "IS02_isolation_only"): arm,
    }
    entry = mod._paired_rows(rows)[f"theta={THETA:.4g}|arm=IS02_isolation_only"]
    assert entry["n_paired"] == 0


def test_composition_flag_logic():
    stats = {"takeoff_before_share": {"median": 0.30}}
    base = {"takeoff_before_share": {"median": 0.17}}
    paired_straddling = {
        "delta_before_share": {"q05": -0.02, "q95": 0.03},
    }
    paired_moved = {
        "delta_before_share": {"q05": 0.05, "q95": 0.10},
    }
    assert mod._composition_flag(stats, paired_straddling, base) is True
    assert mod._composition_flag(stats, paired_moved, base) is False
    small_move = {"takeoff_before_share": {"median": 0.20}}
    assert mod._composition_flag(small_move, paired_straddling, base) is False
    assert mod._composition_flag(stats, None, base) is False


def test_row_triggers_skip_baseline_and_flag_landings():
    assert mod._row_triggers(THETA, "D0_declared", {}) is None
    stats = {
        "truth_leg_in_band": True,
        "timing_leg_in_band": False,
        "fizzle_majority": False,
        "takeoff_infections_total": {"median": 800.0},
        "takeoff_before_share": {"median": 0.20},
        "armed_day": {"median": 3.0},
        "self_isolated_count": {"median": 700.0},
    }
    trig = mod._row_triggers(THETA, "IS01_dp_replay", stats)
    assert trig["triggers"] == ["TRUTH-IN-BAND"]
