"""
test_contam_fleet_compare.py – fleet native vs ContamX sweep
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Offline-safe tests for ``tools/contam_fleet_compare.py`` and its committed
spec ``data/config/contam_compare/fleet_arms.json``. Live ContamX cells
skip when no binary is present.
"""

from __future__ import annotations

import copy
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
    assert cfc._arm_needs_field(spec["arms"]["outdoor_air"])
    assert cfc._arm_needs_field(spec["arms"]["full_recirc"])
    assert cfc._arm_needs_field(spec["arms"]["filter_merv13"])
    assert cfc._arm_needs_field(spec["arms"]["ahu_casualty"])
    assert cfc._arm_needs_field(spec["arms"]["ach_surge"])
    assert cfc._arm_needs_field(spec["arms"]["zone_isolation"])


def test_scale_ach_remains_field_op() -> None:
    assert "scale_ach" in cfc._FIELD_OPS
    assert cfc._arm_needs_field({"ops": [{"op": "scale_ach", "factor": 1.5}]})


def test_ach_surge_arm_pins_labelled_all_groups_scope() -> None:
    assert _spec()["arms"]["ach_surge"]["ops"] == [
        {"op": "scale_ach", "factor": 2.0, "scope": "all_groups"},
    ]


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


def test_apply_arm_ops_set_oa_preserves_duty0_exhaust_groups() -> None:
    _spatial, airflow = _load_destroyer()
    air, meta = cfc._apply_arm_ops(
        airflow, [{"op": "set_oa", "value": 0.0}], {},
    )
    by_id = {g["id"]: g for g in air["hvac_zones"]}
    for group_id in ("zone_upper", "zone_main", "zone_lower"):
        assert by_id[group_id]["oa_fraction"] == pytest.approx(0.0)
    for group_id in ("AHU_HD_MAIN_M", "AHU_HD_MAIN_F", "AHU_HD_UPPER_M"):
        assert by_id[group_id]["oa_fraction"] == pytest.approx(1.0)
    assert air["oa_fraction"] == pytest.approx(0.0)
    assert meta["engine_args"]["oa_fraction"] == pytest.approx(0.0)


def test_apply_arm_ops_set_oa_supply_sweep_is_graduated() -> None:
    _spatial, airflow = _load_destroyer()
    observed: list[float] = []
    for val in (0.0, 0.5, 1.0):
        air, _meta = cfc._apply_arm_ops(
            airflow, [{"op": "set_oa", "value": val}], {},
        )
        zone_main = next(
            g for g in air["hvac_zones"] if g["id"] == "zone_main"
        )
        observed.append(float(zone_main["oa_fraction"]))
        heads = [
            g for g in air["hvac_zones"]
            if str(g["id"]).startswith("AHU_HD_")
        ]
        assert all(float(g["oa_fraction"]) == pytest.approx(1.0) for g in heads)
    assert observed[0] < observed[1] < observed[2]
    assert observed[1] - observed[0] == pytest.approx(0.5)
    assert observed[2] - observed[1] == pytest.approx(0.5)


def test_apply_arm_ops_set_oa_all_groups_scope_is_labelled_baseline() -> None:
    _spatial, airflow = _load_destroyer()
    air, _meta = cfc._apply_arm_ops(
        airflow,
        [{"op": "set_oa", "value": 0.0, "scope": "all_groups"}],
        {},
    )
    assert all(
        float(g["oa_fraction"]) == pytest.approx(0.0)
        for g in air["hvac_zones"]
    )


def test_apply_arm_ops_set_oa_rejects_unknown_scope() -> None:
    _spatial, airflow = _load_destroyer()
    with pytest.raises(ValueError, match="scope"):
        cfc._apply_arm_ops(
            airflow,
            [{"op": "set_oa", "value": 0.0, "scope": "bogus"}],
            {},
        )


def test_apply_arm_ops_scale_ach_defaults_to_supply_groups() -> None:
    _spatial, airflow = _load_destroyer()
    air, meta = cfc._apply_arm_ops(
        airflow, [{"op": "scale_ach", "factor": 1.5}], {},
    )
    original = {g["id"]: g for g in airflow["hvac_zones"]}
    current = {g["id"]: g for g in air["hvac_zones"]}
    for group_id in ("zone_upper", "zone_main", "zone_lower"):
        assert current[group_id]["ach"] == pytest.approx(
            float(original[group_id]["ach"]) * 1.5
        )
    for group_id in ("AHU_HD_MAIN_M", "AHU_HD_MAIN_F", "AHU_HD_UPPER_M"):
        assert current[group_id]["ach"] == pytest.approx(
            float(original[group_id]["ach"])
        )
    scale_edit = next(edit for edit in meta["edits"] if "ach x1.5" in edit)
    assert "on supply groups" in scale_edit
    assert "duty-0 group(s)" in scale_edit


def test_apply_arm_ops_scale_ach_all_groups_matches_legacy_baseline() -> None:
    _spatial, airflow = _load_destroyer()
    expected = copy.deepcopy(airflow)
    for group in expected["hvac_zones"]:
        group["ach"] = float(group.get("ach", 0.0)) * 2.0
    air, meta = cfc._apply_arm_ops(
        airflow,
        [{"op": "scale_ach", "factor": 2.0, "scope": "all_groups"}],
        {},
    )
    assert air == expected
    assert any("legacy all_groups" in edit for edit in meta["edits"])


def test_apply_arm_ops_scale_ach_rejects_unknown_scope() -> None:
    _spatial, airflow = _load_destroyer()
    with pytest.raises(ValueError, match="scale_ach scope"):
        cfc._apply_arm_ops(
            airflow,
            [{"op": "scale_ach", "factor": 2.0, "scope": "bogus"}],
            {},
        )


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
    entries = cfc._annotate_ahs_declared_oa(entries, airflow)
    flows = {i: 50.0 for i in range(len(entries))}
    for entry in entries:
        if entry.get("kind") in {"ahs_oa", "ahs_exhaust", "ahs_recirc"}:
            flows[int(entry["path_nr"])] = 0.0
    return {"entries": entries, "flows": flows}


def _patch_stub_field(monkeypatch) -> None:
    def fake_timed_field(spatial, air, *, tmp_dir, binary,
                         prj_rel=None, repeats=1, filter_efficiency=None):
        return _stub_field(spatial, air), {
            "seconds_mean": 0.001, "seconds_values": [0.001],
        }
    monkeypatch.setattr(cfc, "_timed_field", fake_timed_field)


def test_contamx_field_export_annotates_declared_oa_and_passes_filter(
        monkeypatch) -> None:
    spatial, airflow = _load_destroyer()
    air, _meta = cfc._apply_arm_ops(
        airflow, [{"op": "set_oa", "value": 0.0}], {},
    )
    entries = [
        {"path_nr": 1, "kind": "ahs_supply", "ahs_nr": 1},
        {"path_nr": 2, "kind": "ahs_return", "ahs_nr": 1},
        {"path_nr": 3, "kind": "ahs_supply", "ahs_nr": 4},
        {"path_nr": 4, "kind": "ahs_return", "ahs_nr": 4},
    ]
    captured: dict = {}

    def fake_export(spatial_arg, airflow_arg, **kwargs):
        captured.update(kwargs)
        return "", [dict(entry) for entry in entries]

    monkeypatch.setattr(cfc, "export_prj_with_path_map", fake_export)
    monkeypatch.setattr(cfc, "_solve_prj", lambda *a, **k: {1: 100.0})
    field = cfc._contamx_field(
        spatial, air, tmp_dir=".", binary="stub", prj_rel=None,
        filter_efficiency=0.9,
    )
    assert captured["filter_efficiency"] == pytest.approx(0.9)
    assert captured["ahs_terminal_mode"] == "commissioned"
    declared = {
        int(e["ahs_nr"]): float(e["declared_oa_fraction"])
        for e in field["entries"]
    }
    assert declared[1] == pytest.approx(0.0)
    assert declared[4] == pytest.approx(1.0)


def test_run_platform_engine_ops_rebuild_field_with_arm_params(
        tmp_path, monkeypatch) -> None:
    seen: list[tuple[str | None, float | None]] = []

    def fake_timed_field(spatial, air, *, tmp_dir, binary,
                         prj_rel=None, repeats=1, filter_efficiency=None):
        seen.append((prj_rel, filter_efficiency))
        return _stub_field(spatial, air), {
            "seconds_mean": 0.001, "seconds_values": [0.001],
        }

    monkeypatch.setattr(cfc, "_timed_field", fake_timed_field)
    spec = _spec()
    spec["epochs"] = 1
    report = cfc.run_platform(
        "destroyer_baseline", spec,
        arms=["baseline", "outdoor_air", "filter_merv13"],
        scenarios=["respiratory"], repeats=1, epochs=1,
        binary="stub-contamx", tmp_root=str(tmp_path),
    )
    export_filters = [f for prj, f in seen if prj is None]
    values = [float(f) for f in export_filters if f is not None]
    assert any(f == pytest.approx(0.5) for f in values)
    assert any(f == pytest.approx(0.9) for f in values)
    filter_field = report["arms"]["filter_merv13"]["field_seconds"]
    assert "reused" not in filter_field
    assert filter_field["seconds_mean"] == pytest.approx(0.001)


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
