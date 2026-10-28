"""
test_contam_fleet_compare.py – fleet native vs ContamX sweep
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Offline-safe tests for ``tools/contam_fleet_compare.py`` and its committed
spec ``data/config/contam_compare/fleet_arms.json``. Live ContamX cells
skip when no binary is present.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.contamx_runner import find_contamx  # noqa: E402
from tools import contam_fleet_compare as cfc  # noqa: E402

_SPEC = REPO_ROOT / "data" / "config" / "contam_compare" / "fleet_arms.json"


def _spec() -> dict:
    return cfc._attach_ids(json.loads(_SPEC.read_text(encoding="utf-8")))


def _load_destroyer() -> tuple[dict, dict]:
    return cfc._load_platform("destroyer_baseline")


def test_spec_and_ops_validate() -> None:
    spec = _spec()
    assert spec["scenarios"]["respiratory"]["natural_decay_rate"] != pytest.approx(0.0)
    assert spec["scenarios"]["chemical_tracer"]["natural_decay_rate"] == pytest.approx(0.0)
    assert "baseline" in spec["arms"]
    for arm_id, arm in spec["arms"].items():
        assert arm["arm_id"] == arm_id
        for op in arm.get("ops", []):
            assert op["op"] in cfc._FIELD_OPS | {
                "set_oa", "set_filter", "set_duty", "scale_ach",
                "drop_links",
            }


def test_field_ops_classification() -> None:
    spec = _spec()
    assert not cfc._arm_needs_field(spec["arms"]["baseline"])
    assert not cfc._arm_needs_field(spec["arms"]["outdoor_air"])
    assert not cfc._arm_needs_field(spec["arms"]["filter_merv13"])
    assert cfc._arm_needs_field(spec["arms"]["ahu_casualty"])
    assert cfc._arm_needs_field(spec["arms"]["ach_surge"])
    assert cfc._arm_needs_field(spec["arms"]["zone_isolation"])


def test_apply_arm_ops_set_oa_mutates_json_and_engine() -> None:
    _spatial, airflow = _load_destroyer()
    spec = _spec()
    air, meta = cfc._apply_arm_ops(
        airflow, spec["arms"]["outdoor_air"]["ops"], {},
    )
    assert air["oa_fraction"] == pytest.approx(1.0)
    for zone in air["hvac_zones"]:
        assert zone["oa_fraction"] == pytest.approx(1.0)
    assert meta["engine_args"]["oa_fraction"] == pytest.approx(1.0)
    assert airflow.get("oa_fraction", 0.2) != pytest.approx(1.0)


def test_apply_arm_ops_ahu_casualty_hits_one_group() -> None:
    _spatial, airflow = _load_destroyer()
    volume = {z["id"]: z["volume_m3"] for z in _spatial["zones"]}
    spec = _spec()
    def _dead_ids(air: dict) -> set[str]:
        default = float(air["hvac_duty"])
        return {
            z["id"] for z in air["hvac_zones"]
            if float(z.get("hvac_duty", default)) == 0.0
        }

    air, meta = cfc._apply_arm_ops(
        airflow, spec["arms"]["ahu_casualty"]["ops"], volume,
    )
    assert len(_dead_ids(air) - _dead_ids(airflow)) == 1
    # top-level default untouched: the casualty hits one group only
    assert air["hvac_duty"] == airflow["hvac_duty"]
    assert meta["edits"]


def test_apply_arm_ops_filter_only_engine_arg() -> None:
    _spatial, airflow = _load_destroyer()
    spec = _spec()
    air, meta = cfc._apply_arm_ops(
        airflow, spec["arms"]["filter_merv13"]["ops"], {},
    )
    assert meta["engine_args"]["filter_efficiency"] == pytest.approx(0.9)
    assert air == airflow  # engine-level knob: no airflow mutation


def test_injection_zone_is_occupied_and_served() -> None:
    spatial, airflow = _load_destroyer()
    zone = cfc._injection_zone(spatial, airflow)
    zone_ids = {z["id"] for z in spatial["zones"]}
    assert zone in zone_ids


def test_response_parity_flags_moves() -> None:
    parity = cfc._response_parity(
        {"z1": 2.0, "z2": 1.0}, {"z1": 1.0, "z2": 1.0},
        {"z1": 1.5, "z2": 1.0}, {"z1": 1.0, "z2": 1.0},
    )
    assert parity["zones_moved_both"] == 1
    assert parity["sign_agreement_frac"] == pytest.approx(1.0)
    assert parity["magnitude_ratio_median"] == pytest.approx(0.5)


def test_engine_params_merge_scenario_and_arm() -> None:
    spec = _spec()
    arm_meta = {"engine_args": {"filter_efficiency": 0.9}}
    params = cfc._engine_params(
        arm_meta, spec["scenarios"]["chemical_tracer"], 0.5, 0.2,
    )
    assert params["decay"] == pytest.approx(0.0)
    assert params["filt"] == pytest.approx(0.9)
    assert params["oa"] == pytest.approx(0.2)


def test_run_platform_native_only_offline(tmp_path) -> None:
    spec = _spec()
    spec["epochs"] = 2
    report = cfc.run_platform(
        "destroyer_baseline", spec,
        arms=["baseline", "zone_isolation"],
        scenarios=["respiratory"], repeats=1, epochs=2,
        binary=None, tmp_root=str(tmp_path),
    )
    cell = report["arms"]["baseline"]["cells"]["respiratory"]
    assert cell["native"]["dose_per_zone"]
    assert report["arms"]["baseline"]["edits"] == []
    parity = report["arms"]["zone_isolation"]["cells"]["respiratory"][
        "response_parity"]
    assert parity["zones_moved_native"] > 0
    assert "divergence" not in cell  # no ContamX binary passed


@pytest.mark.skipif(
    find_contamx() is None, reason="ContamX binary not available",
)
def test_run_platform_live_contamx_cells(tmp_path) -> None:
    spec = _spec()
    report = cfc.run_platform(
        "destroyer_baseline", spec,
        arms=["baseline", "ach_surge"],
        scenarios=["respiratory"], repeats=1, epochs=2,
        binary=find_contamx(), tmp_root=str(tmp_path),
    )
    base = report["arms"]["baseline"]["cells"]["respiratory"]
    assert "contamx" in base
    assert "divergence" in base
    assert "contamx_committed" in base
    surge = report["arms"]["ach_surge"]["cells"]["respiratory"]
    assert surge["response_parity"] is not None
    assert report["arms"]["ach_surge"]["field_seconds"]


def test_main_native_only_writes_outputs(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(cfc, "find_contamx", lambda *a, **k: None)
    out_rel = "telemetry_buffer/contam_fleet_compare/test_cli"
    md_rel = "telemetry_buffer/contam_fleet_compare/test_cli_table.md"
    out_full = REPO_ROOT / out_rel
    md_full = REPO_ROOT / md_rel
    try:
        rc = cfc.main([
            "--platforms", "destroyer_baseline",
            "--arms", "baseline", "zone_isolation",
            "--scenarios", "respiratory",
            "--epochs", "2", "--repeats", "1",
            "--out", out_rel, "--md-out", md_rel,
        ])
        assert rc == 0
        latest = out_full / "fleet_compare_latest.json"
        assert latest.is_file()
        data = json.loads(latest.read_text(encoding="utf-8"))
        assert data["platforms"][0]["platform"] == "destroyer_baseline"
        assert md_full.is_file()
        assert "| destroyer_baseline |" in md_full.read_text(
            encoding="utf-8")
    finally:
        import shutil
        shutil.rmtree(out_full, ignore_errors=True)
        md_full.unlink(missing_ok=True)


def test_main_rejects_unknown_arm_and_scenario() -> None:
    with pytest.raises(SystemExit):
        cfc.main(["--platforms", "destroyer_baseline", "--arms", "bogus"])
    with pytest.raises(SystemExit):
        cfc.main(["--platforms", "destroyer_baseline",
                  "--scenarios", "bogus"])


def test_platform_ids_explicit_and_all() -> None:
    assert cfc._platform_ids(["destroyer_baseline"]) == [
        "destroyer_baseline",
    ]
    all_ids = cfc._platform_ids(None)
    assert len(all_ids) >= 79
    assert "destroyer_baseline" in all_ids
    with pytest.raises(ValueError, match="platform id"):
        cfc._platform_ids(["no/such"])


def test_response_parity_no_overlap() -> None:
    parity = cfc._response_parity(
        {"z1": 1.0}, {"z1": 1.0}, {"z2": 2.0}, {"z2": 1.0},
    )
    assert parity["zones_moved_both"] == 0
    assert parity["sign_agreement_frac"] is None
    assert parity["magnitude_ratio_median"] is None


def test_injection_zone_fallback_without_hvac() -> None:
    spatial = {"zones": [
        {"id": "a", "volume_m3": 10.0},
        {"id": "b", "volume_m3": 50.0},
    ]}
    assert cfc._injection_zone(spatial, {"hvac_zones": []}) == "b"


def test_drop_links_and_scale_ach_ops() -> None:
    _spatial, airflow = _load_destroyer()
    ops = [
        {"op": "drop_links", "key": "cross_zone_links"},
        {"op": "scale_ach", "factor": 2.0},
    ]
    air, meta = cfc._apply_arm_ops(airflow, ops, {})
    assert air["cross_zone_links"] == []
    assert meta["edits"]
    with pytest.raises(ValueError):
        cfc._apply_arm_ops(airflow, [{"op": "bogus"}], {})


def test_arm_response_without_baseline() -> None:
    cell = {"native": {"dose_per_zone": {"z": 1.0},
                       "retained_fraction": 0.5}}
    assert cfc._arm_response(cell, {}, "respiratory") is None


def test_print_platform_summary_handles_empty(capsys) -> None:
    report = {
        "platform": "p", "n_zones": 0, "n_hvac_groups": 0,
        "has_committed_prj": False, "injection_zone": "",
        "inject_mass": 0.0,
        "arms": {"a": {"cells": {}, "errors": ["e1"]}},
        "errors": [],
    }
    cfc._print_platform_summary(report)
    out = capsys.readouterr().out
    assert "=== p " in out
    assert "ERROR a: e1" in out


def _stub_field(spatial, airflow):
    prj_text, entries = cfc.export_prj_with_path_map(
        spatial, airflow, ahs_terminal_mode="commissioned",
    )
    return {
        "entries": entries,
        "flows": {i: 50.0 for i in range(len(entries))},
    }


def _patch_stub_field(monkeypatch) -> None:
    def fake_timed_field(spatial, air, *, tmp_dir, binary,
                         prj_rel=None, repeats=1):
        return _stub_field(spatial, air), {
            "seconds_mean": 0.001, "seconds_values": [0.001],
        }
    monkeypatch.setattr(cfc, "_timed_field", fake_timed_field)


def test_run_platform_stubbed_contamx_lanes(tmp_path, monkeypatch) -> None:
    _patch_stub_field(monkeypatch)
    spec = _spec()
    report = cfc.run_platform(
        "destroyer_baseline", spec,
        arms=["baseline", "ach_surge", "ahu_casualty"],
        scenarios=["respiratory"], repeats=1, epochs=2,
        binary="stub-contamx", tmp_root=str(tmp_path),
    )
    base = report["arms"]["baseline"]["cells"]["respiratory"]
    assert "contamx" in base
    assert "divergence" in base
    assert "contamx_committed" in base
    assert "divergence_committed" in base
    assert report["arms"]["baseline"]["field_seconds"]["seconds_mean"] > 0
    assert report["arms"]["baseline"]["committed_field_seconds"]
    for arm_id in ("ach_surge", "ahu_casualty"):
        cell = report["arms"][arm_id]["cells"]["respiratory"]
        assert "contamx" in cell
        assert cell["response_parity"] is not None


def test_run_platform_stubbed_field_solve_failure(
        tmp_path, monkeypatch) -> None:
    def boom(*a, **k):
        raise ValueError("no solve")
    monkeypatch.setattr(cfc, "_timed_field", boom)
    spec = _spec()
    report = cfc.run_platform(
        "destroyer_baseline", spec,
        arms=["baseline"], scenarios=["respiratory"],
        repeats=1, epochs=2, binary="stub-contamx",
        tmp_root=str(tmp_path),
    )
    arm = report["arms"]["baseline"]
    assert "native" in arm["cells"]["respiratory"]
    assert any("solve failed" in str(e) for e in arm["errors"])
    assert any("unavailable" in str(e) for e in arm["errors"])


def test_run_cell_without_contamx(tmp_path) -> None:
    spatial, airflow = _load_destroyer()
    cell = cfc._run_cell(
        spatial, airflow,
        params={"decay": 0.1, "filt": 0.5, "oa": 0.2},
        initial_mass={z["id"]: 1000.0
                      for z in spatial.get("zones", [])[:1]},
        epochs=2, repeats=1, cx_field=None, binary=None,
    )
    assert set(cell) == {"native"}
