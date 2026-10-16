"""Declared-state audit tests — spec parsing + real runs on one hull.

Invariants: state-spec parsing validates; group selectors resolve on a
synthetic hull; a declared hvac casualty drops the target group's supply
star in the transport engine; a declared lockdown voyage holds agents on
home zones (measured, not asserted); a citadel state on the one hull that
declares a boundary verifies its signature.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import hull_audit  # noqa: E402
from tools import hull_state_audit as st  # noqa: E402
from tools.hull_state_audit import DEFAULT_STATE_SPEC  # noqa: E402


def _zone(zid: str, ztype: str, **kw) -> dict:
    z = {
        "id": zid, "type": ztype, "traffic": "medium",
        "volume_m3": 100.0, "floor_area_m2": 40.0,
        "ceiling_height_m": 2.5, "deck": "main", "max_occupancy": 20,
    }
    z.update(kw)
    return z


def _bundle(tmp_path: Path, name: str = "toy_ship") -> hull_audit.PlatformBundle:
    d = tmp_path / name
    d.mkdir(parents=True)
    (d / "spatial_layout.json").write_text(json.dumps({
        "platform": name, "nominal_complement": {"passengers": 0, "crew": 30},
        "zones": [
            _zone("Berth", "Room", max_occupancy=30, volume_m3=400.0),
            _zone("Mess", "Dining", max_occupancy=15, volume_m3=200.0),
            _zone("Galley", "Room", volume_m3=80.0),
            _zone("Void_Room", "Room"),
        ],
    }))
    (d / "air_flow_paths.json").write_text(json.dumps({
        "platform": name, "oa_fraction": 0.2, "hvac_duty": 1.0,
        "hvac_zones": [
            {"id": "HVAC_Accom", "rooms": ["Berth", "Mess"], "ach": 6.0,
             "oa_fraction": 0.3, "nbc_filter_efficiency": 0.999,
             "description": "citadel protected"},
            {"id": "HVAC_Galley", "rooms": ["Galley"], "ach": 8.0},
        ],
        "cross_zone_links": [
            {"from": "HVAC_Accom", "to": "HVAC_Galley",
             "flow_rate_m3h": 100},
        ],
        "adjacency": [
            {"from": "Berth", "to": "Galley", "type": "passageway"},
            {"from": "Berth", "to": "Mess", "type": "passageway"},
        ],
    }))
    return hull_audit.load_platform(d)


def test_default_state_spec_parses_and_names_three_states():
    spec = st.load_state_spec(DEFAULT_STATE_SPEC)
    assert set(spec["states"]) == {
        "hvac_casualty_main_ahu", "collective_protection", "lockdown_general",
    }
    for sid, state in spec["states"].items():
        assert state.get("expect"), sid


def test_load_state_spec_rejects_empty(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"states": {}}))
    with pytest.raises(ValueError, match="non-empty"):
        st.load_state_spec(bad, allowed_roots=(str(tmp_path),))


def test_selector_largest_supply_and_citadel(tmp_path):
    b = _bundle(tmp_path)
    casualty = st.select_groups(b, b.airflow,
                                {"largest_supply_group": True}, set())
    assert [g["id"] for g in casualty] == ["HVAC_Accom"]
    inside, err = st._citadel_groups(
        b, {"citadel": {"with_field": "nbc_filter_efficiency"}})
    assert err is None
    inside_ids = {g["id"] for g in inside}
    assert inside_ids == {"HVAC_Accom"}
    outside = st.select_groups(
        b, b.airflow,
        {"outside_citadel": True, "supply_only": True}, inside_ids)
    assert [g["id"] for g in outside] == ["HVAC_Galley"]


def test_citadel_unresolvable_flags_cannot_express(tmp_path):
    b = _bundle(tmp_path)
    _, err = st._citadel_groups(
        b, {"citadel": {"description_contains": ["no such text"]}})
    assert err is not None
    assert "no HVAC group" in err


def test_duty_edit_drops_target_star(tmp_path):
    b = _bundle(tmp_path)
    air, filt, edits, notes, unresolved = st.apply_airflow_state(
        b, {"set_hvac_duty": [
            {"select": {"ids": ["HVAC_Galley"]}, "duty": 0.0}]}, [])
    assert unresolved == []
    galley = next(g for g in air["hvac_zones"] if g["id"] == "HVAC_Galley")
    assert galley["hvac_duty"] == pytest.approx(0.0)
    eng, _mass = st._drainage_mass(b, air, filt, 4)
    flows = st._room_supply_in(eng)
    assert flows.get("Galley", {}).get("hvac_supply", 0.0) == pytest.approx(0.0)
    assert flows.get("Berth", {}).get("hvac_supply", 0.0) > 0.0


def test_cps_transform_seals_boundary(tmp_path):
    b = _bundle(tmp_path)
    spec = st.load_state_spec(DEFAULT_STATE_SPEC)
    state = st.merged_state(spec, b.platform_id, "collective_protection")
    inside, err = st._citadel_groups(b, state)
    assert err is None
    air, filt, edits, notes, unresolved = st.apply_airflow_state(
        b, state["airflow"], inside)
    assert unresolved == []
    assert filt == pytest.approx(0.999)
    assert air["cross_zone_links"] == []           # inside->outside duct dropped
    adj_to = {a["to"] for a in air["adjacency"]}
    assert "Galley" not in adj_to                  # hatch to outside room shut
    eng, _m = st._drainage_mass(b, air, filt, 4)
    assert st._boundary_crossings(eng, {"HVAC_Accom"}, {"Berth", "Mess"}) == []


def test_protocol_close_zone_class_resolves(tmp_path):
    b = _bundle(tmp_path)
    p = st._resolve_audit_protocol(
        {"protocol_id": "SOP-900-AUDIT", "name": "x",
         "trigger": {"instrument_class": "scenario_calendar",
                     "stoplight_level": "RED"},
         "modifiers": {"close_zone_class": ["mess"]}}, b)
    assert "close_zone_class" not in p["modifiers"]
    assert p["modifiers"]["close_zones"] == ["Galley", "Mess"]


def test_main_casualty_and_lockdown_pce874(tmp_path):
    """End-to-end: casualty drainage + 2-epoch lockdown voyage on pce_874."""
    out = tmp_path / "st.json"
    md = tmp_path / "st.md"
    rc = st.main([
        "--platforms", "pce_874", "--epochs", "2",
        "--states", "hvac_casualty_main_ahu,lockdown_general",
        "--json-out", str(out), "--md-out", str(md),
    ])
    assert rc == 0
    row = json.loads(out.read_text())["rows"][0]["states"]
    casualty = row["hvac_casualty_main_ahu"]
    assert casualty["verdict"] == "verified"
    names = {c["name"]: c for c in casualty["checks"]}
    assert names["starved_rooms"]["pass"]
    assert names["elevated_retention_in"]["pass"]
    lock = row["lockdown_general"]
    assert lock["verdict"] == "verified"
    assert lock["occupancy"]["confined_share"] >= 0.95
    assert "Declared-state hull audit" in md.read_text()


def test_main_collective_protection_legend(tmp_path):
    """The one hull that declares a citadel boundary verifies."""
    out = tmp_path / "st.json"
    rc = st.main([
        "--platforms", "legend_class_nsc", "--epochs", "4",
        "--states", "collective_protection",
        "--json-out", str(out),
    ])
    assert rc == 0
    cps = json.loads(out.read_text())["rows"][0]["states"][
        "collective_protection"]
    assert cps["verdict"] == "verified"
    names = {c["name"]: c for c in cps["checks"]}
    assert names["supplied_rooms"]["pass"]
    assert names["starved_rooms"]["pass"]
    assert names["no_boundary_paths"]["pass"]
    assert cps["drainage"]["filter_efficiency"] == pytest.approx(0.999)


def test_cannot_express_on_boundary_free_hull(tmp_path):
    out = tmp_path / "st.json"
    rc = st.main([
        "--platforms", "pce_874", "--epochs", "2",
        "--states", "collective_protection",
        "--json-out", str(out),
    ])
    assert rc == 0
    cps = json.loads(out.read_text())["rows"][0]["states"][
        "collective_protection"]
    assert cps["verdict"] == "cannot_express"
    assert cps["blockers"]
