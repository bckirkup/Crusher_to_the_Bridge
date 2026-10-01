"""COVID-GM-RESCORE-01 readout: audits, pooled rows, seed-paired deltas."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tools import covid_gm_rescore_readout as mod

DESIGN = (
    Path(__file__).resolve().parents[1]
    / "picard_framework/runs/covid_gm_rescore_v1_design.json"
)
IMPORTS3_DESIGN = (
    Path(__file__).resolve().parents[1]
    / "picard_framework/runs/covid_gm_rescore_v1_imports3_design.json"
)
THETA = 2.37e11
SEED = 20200205


def _payload(
    arm: str = "hygiene_cycle",
    *,
    theta: float = THETA,
    seed: int = SEED,
    imports: int = 1,
    mode: str | None = "hygiene_cycle",
    rec: int = 300,
    pos: int = 128,
    specimens: int = 217,
    asym_pos: int = 104,
    inf: float | None = 160.0,
    aboard: int = 223,
    first_onset: int | None = 10,
    curve: dict | None = None,
    spec: dict | None = None,
    seeded_count: int = 1,
) -> dict:
    ring_spec = {
        "role": "passenger", "count": imports, "infection_age_days": 0.0,
    }
    if spec is not None:
        ring_spec = spec
    return {
        "design_id": "covid_gm_rescore_v1",
        "cell": {
            "index": 0, "scenario_id": "greg_mortimer_2020",
            "theta": theta, "infection_age_days": 0.0,
            "imports": imports, "seed": seed, "arm_id": arm,
            "key": f"cell_{arm}_{seed}.json",
        },
        "observables": {
            "recorded_onsets": rec,
            "onsets_before_split_day": rec // 2,
            "onsets_on_or_after_split_day": rec - rec // 2,
            "campaign_specimens": specimens,
            "campaign_positives": pos,
            "campaign_asymptomatic_positives": asym_pos,
        },
        "onset_curve": curve if curve is not None else {
            "10": {"passenger": rec, "crew": 0},
        },
        "first_onset_day": first_onset,
        "infections_total": inf,
        "aboard_total": aboard,
        "delivery": {"hand_reservoir_mode": mode},
        "seed_ring": {
            "seed_spec": ring_spec,
            "seeded_count": seeded_count,
            "seeded_hosts": [],
        },
    }


def _declared_for(overrides: dict | None = None) -> dict:
    return mod._declared({"arm_id": "X", "overrides": overrides or {}})


def test_declared_mode_reads_the_transmission_override():
    assert _declared_for()["hand_reservoir_mode"] == "hygiene_cycle"
    d = _declared_for({
        "transmission_overrides": {"hand_reservoir_mode": "spike_decay"},
    })
    assert d["hand_reservoir_mode"] == "spike_decay"


def test_audit_cell_accepts_a_matching_gm_cell():
    assert mod.audit_cell(_payload(), _declared_for(), THETA) == []


def test_audit_cell_flags_each_declared_invariant():
    declared = _declared_for()
    fails = mod.audit_cell(_payload(mode="spike_decay"), declared, THETA)
    assert fails
    assert "hand_reservoir_mode" in fails[0]
    fails = mod.audit_cell(
        _payload(spec={
            "role": "passenger", "count": 2, "infection_age_days": 0.0,
        }),
        declared, THETA,
    )
    assert any("seed_spec.count" in f for f in fails)
    fails = mod.audit_cell(
        _payload(spec={
            "role": "passenger", "count": 1, "infection_age_days": 6.8,
        }),
        declared, THETA,
    )
    assert any("infection_age_days" in f for f in fails)
    fails = mod.audit_cell(
        _payload(spec={
            "role": "crew", "count": 1, "infection_age_days": 0.0,
        }),
        declared, THETA,
    )
    assert any("seed_spec.role" in f for f in fails)
    fails = mod.audit_cell(
        _payload(spec={
            "role": "passenger", "count": 1, "infection_age_days": 0.0,
            "onset_day": -1.0,
        }),
        declared, THETA,
    )
    assert any("onset_day" in f for f in fails)
    fails = mod.audit_cell(_payload(seeded_count=2), declared, THETA)
    assert any("seeded_count" in f for f in fails)
    fails = mod.audit_cell(_payload(aboard=300), declared, THETA)
    assert any("aboard_total" in f for f in fails)


def test_row_stats_scores_the_frozen_anchors():
    payloads = [
        _payload(seed=SEED + i, rec=300, pos=120 + i, asym_pos=104)
        for i in range(20)
    ]
    stats = mod._row_stats(payloads)
    assert stats["n"] == 20
    assert stats["p_takeoff"] == pytest.approx(1.0)
    # Nearest-order-statistic quantile: the 10th of 120..139.
    assert stats["campaign_positives"]["median"] == pytest.approx(130.0)
    # Median inside [64, 256] and the q05-q95 interval brackets 128.
    assert stats["h1_lands"] is True
    assert stats["h2_hit"] is True  # 104/128ish ~ 0.78, inside 0.81 +- 0.10
    assert stats["takeoff_conditional_campaign_positives"]["n"] == 20
    assert stats["attack_share_recorded"]["willebrand_iqr"] == [
        0.0003, 0.015,
    ]
    assert stats["onset_curve_pooled"]["10"] == 20 * 300
    assert stats["median_onset_day"]["median"] == pytest.approx(10.0)


def test_row_stats_below_takeoff_reads_ignition_failure():
    payloads = [
        _payload(seed=SEED + i, rec=2, pos=0, asym_pos=0)
        for i in range(20)
    ]
    stats = mod._row_stats(payloads)
    assert stats["p_takeoff"] == pytest.approx(0.0)
    assert stats["takeoff_conditional_campaign_positives"]["n"] == 0
    assert stats["asymptomatic_share"]["n_defined"] == 0
    assert stats["h1_lands"] is False
    trigger = mod._row_triggers(THETA, "hygiene_cycle", stats)
    assert "DEAD-REGIME" in trigger["triggers"]


def test_h1_lands_triggers_the_report_immediately_row():
    stats = mod._row_stats([
        _payload(seed=SEED + i, rec=300, pos=128, asym_pos=104)
        for i in range(20)
    ])
    trigger = mod._row_triggers(THETA, "hygiene_cycle", stats)
    assert "H1-LANDS" in trigger["triggers"]


def test_seed_paired_delta_reports_paired_fields_and_flips():
    base = {
        SEED + i: _payload(seed=SEED + i, rec=300, pos=128, inf=160.0)
        for i in range(4)
    }
    other = {
        SEED + i: _payload(seed=SEED + i, rec=200, pos=90, inf=100.0)
        for i in range(4)
    }
    # Seed 20200205: the arm takes off? rec 300 vs 200 both >= 10, no flip;
    # seed 20200208 drops below takeoff in the other map -> flip.
    other[SEED + 3] = _payload(seed=SEED + 3, rec=5, pos=0, inf=5.0)
    delta = mod._seed_paired_delta(base, other)
    assert delta["paired_seeds"] == 4
    # Deltas [100, 100, 100, 295]: nearest-order median is 100.
    assert delta["delta_recorded_onsets"]["median"] == pytest.approx(100.0)
    assert delta["delta_campaign_positives"]["median"] is not None
    assert delta["takeoff_class_flips"] == 1


def test_paired_rows_bind_baseline_by_arm_not_load_order():
    rows = {
        (THETA, "spike_decay"): [
            _payload("spike_decay", seed=SEED + i, rec=200, pos=90)
            for i in range(3)
        ],
        (THETA, "hygiene_cycle"): [
            _payload("hygiene_cycle", seed=SEED + i, rec=300, pos=128)
            for i in range(3)
        ],
    }
    paired = mod._paired_rows(rows, None)
    key = "theta=2.37e+11|hygiene_cycle_minus_spike_decay"
    assert key in paired
    assert paired[key]["paired_seeds"] == 3
    # hygiene(300) - spike(200) = +100
    assert paired[key]["delta_recorded_onsets"]["median"] == pytest.approx(100.0)
    assert paired[key]["delta_campaign_positives"]["median"] == pytest.approx(38.0)


def test_paired_rows_external_pairs_the_imports3_diagnostic():
    rows = {
        (THETA, "hygiene_cycle"): [
            _payload("hygiene_cycle", seed=SEED + i, rec=300)
            for i in range(3)
        ],
    }
    external = {
        (THETA, "imports3"): [
            _payload("imports3", seed=SEED + i, rec=380, imports=3)
            for i in range(3)
        ],
    }
    paired = mod._paired_rows(rows, external)
    key = "theta=2.37e+11|hygiene_cycle_minus_external:imports3"
    assert key in paired
    assert paired[key]["paired_seeds"] == 3
    # hygiene(300) - imports3(380) = -80
    assert paired[key]["delta_recorded_onsets"]["median"] == pytest.approx(-80.0)


def test_delta_reversal_trigger_fires_on_positive_medians():
    paired = {
        "theta=2.37e+11|hygiene_cycle_minus_spike_decay": {
            "delta_recorded_onsets": {"median": 5.0},
            "delta_campaign_positives": {"median": 2.0},
            "delta_infections_total": {"median": 7.0},
        },
    }
    trig = mod._delta_reversal_trigger(paired)
    assert trig is not None
    assert "DELTA-REVERSAL" in trig["triggers"]
    paired["theta=2.37e+11|hygiene_cycle_minus_spike_decay"][
        "delta_infections_total"
    ]["median"] = -7.0
    assert mod._delta_reversal_trigger(paired) is None


def test_bucket_external_uses_the_pair_arm_label():
    payloads = {
        "a": _payload(seed=SEED, imports=3),
        "b": _payload(seed=SEED + 1, imports=3),
    }
    rows = mod._bucket_external(payloads, "imports3")
    assert set(rows) == {(THETA, "imports3")}
    assert len(rows[(THETA, "imports3")]) == 2


def test_main_pools_cells_and_pairs_arms(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "REPO_ROOT", str(tmp_path))
    cells_dir = tmp_path / "cells"
    cells_dir.mkdir()
    design_path = tmp_path / "covid_gm_rescore_v1_design.json"
    shutil.copy(DESIGN, design_path)
    for i in range(20):
        cells_dir.joinpath(f"a_{i:03d}.json").write_text(json.dumps(
            _payload(
                "hygiene_cycle", seed=SEED + i, rec=300, pos=128,
                asym_pos=104,
            ),
        ))
        cells_dir.joinpath(f"b_{i:03d}.json").write_text(json.dumps(
            _payload(
                "spike_decay", mode="spike_decay", seed=SEED + i,
                rec=260, pos=110, asym_pos=90,
            ),
        ))
    out = tmp_path / "report.json"
    rc = mod.main([
        "--cells", str(cells_dir),
        "--design", "covid_gm_rescore_v1_design.json",
        "--out", str(out), "--allow-partial",
    ])
    assert rc == 0
    report = json.loads(out.read_text())
    assert report["cells_found"] == 40
    assert report["cells_expected"] == 300
    assert report["audit_failures"] == {}
    assert set(report["rows"]) == {
        "theta=2.37e+11|arm=hygiene_cycle",
        "theta=2.37e+11|arm=spike_decay",
    }
    anchor = report["rows"]["theta=2.37e+11|arm=hygiene_cycle"]
    assert anchor["p_takeoff"] == pytest.approx(1.0)
    assert anchor["campaign_positives"]["median"] == pytest.approx(128.0)
    assert anchor["h1_lands"] is True
    paired = report["paired_rows"][
        "theta=2.37e+11|hygiene_cycle_minus_spike_decay"
    ]
    assert paired["paired_seeds"] == 20
    assert paired["delta_campaign_positives"]["median"] == pytest.approx(18.0)
    # Every trigger read lands in triggered_rows: H1-LANDS here.
    assert any(
        "H1-LANDS" in t.get("triggers", [])
        for t in report["triggered_rows"]
    )


def test_main_refuses_a_partial_read_without_the_flag(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "REPO_ROOT", str(tmp_path))
    cells_dir = tmp_path / "cells"
    cells_dir.mkdir()
    cells_dir.joinpath("one.json").write_text(json.dumps(_payload()))
    design_path = tmp_path / "covid_gm_rescore_v1_design.json"
    shutil.copy(DESIGN, design_path)
    rc = mod.main([
        "--cells", str(cells_dir),
        "--design", "covid_gm_rescore_v1_design.json",
    ])
    assert rc == 2


def test_main_pairs_the_imports3_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "REPO_ROOT", str(tmp_path))
    cells_dir = tmp_path / "cells"
    pair_dir = tmp_path / "pair"
    cells_dir.mkdir()
    pair_dir.mkdir()
    shutil.copy(DESIGN, tmp_path / "covid_gm_rescore_v1_design.json")
    for i in range(3):
        cells_dir.joinpath(f"a_{i}.json").write_text(json.dumps(
            _payload("hygiene_cycle", seed=SEED + i, rec=300),
        ))
        pair_dir.joinpath(f"p_{i}.json").write_text(json.dumps(
            _payload(
                "hygiene_cycle", seed=SEED + i, rec=380, imports=3,
            ),
        ))
    out = tmp_path / "report.json"
    rc = mod.main([
        "--cells", str(cells_dir),
        "--design", "covid_gm_rescore_v1_design.json",
        "--pair-cells", str(pair_dir), "--pair-arm", "imports3",
        "--out", str(out), "--allow-partial",
    ])
    assert rc == 0
    report = json.loads(out.read_text())
    key = "theta=2.37e+11|hygiene_cycle_minus_external:imports3"
    assert report["paired_rows"][key]["paired_seeds"] == 3
