"""Hull audit tests — structural/invariant checks over synthetic platforms.

Each test builds a minimal platform bundle in tmp_path and asserts on
finding (check, severity, scope) tuples — no golden counts; new checks join
the same harness.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import hull_audit  # noqa: E402


def _zone(zid: str, ztype: str, **kw) -> dict:
    z = {
        "id": zid, "type": ztype, "traffic": "medium",
        "volume_m3": 100.0, "floor_area_m2": 40.0,
        "ceiling_height_m": 2.5, "deck": "main", "max_occupancy": 20,
    }
    z.update(kw)
    return z


def _write_platform(tmp_path: Path, name: str, zones, airflow, manifest=None, notes=None) -> Path:
    d = tmp_path / name
    d.mkdir(parents=True)
    (d / "spatial_layout.json").write_text(json.dumps({
        "platform": name, "nominal_complement": {"passengers": 0, "crew": 30},
        "zones": zones,
    }))
    (d / "air_flow_paths.json").write_text(json.dumps({"platform": name, **airflow}))
    if manifest is not None:
        (d / "crew_manifest.json").write_text(json.dumps(manifest))
    if notes is not None:
        (d / "systems_notes.json").write_text(json.dumps(notes))
    return d


def _mini(tmp_path: Path, name: str = "toy_ship") -> hull_audit.PlatformBundle:
    zones = [
        _zone("Berth", "Room", max_occupancy=30),
        _zone("Mess", "Dining", max_occupancy=15),
        _zone("Head_Main", "Sanitary", max_occupancy=5),
        _zone("Engine_Rm", "Engineering"),
        _zone("Void_Room", "Room"),          # sealed: ungrouped, no paths
        _zone("Sick_Bay", "Medical"),        # no adjacency -> walk-island flag
        _zone("Open_Deck", "Free"),          # ungrouped exterior -> note only
    ]
    airflow = {
        "oa_fraction": 0.2, "hvac_duty": 1.0,
        "hvac_zones": [
            {"id": "HVAC_Accom", "rooms": ["Berth", "Mess"], "ach": 6.0, "oa_fraction": 0.3},
            {"id": "AHU_HD_Head_Main", "rooms": ["Head_Main"], "ach": 19.1,
             "hvac_duty": 0.0, "oa_fraction": 1.0},
            {"id": "VENT_Eng", "rooms": ["Engine_Rm"], "ach": 10.0, "oa_fraction": 0.9},
            {"id": "STARVED", "rooms": ["Sick_Bay"], "ach": 8.0,
             "hvac_duty": 0.0, "oa_fraction": 1.0},
        ],
        "cross_zone_links": [
            {"from": "HVAC_Accom", "to": "AHU_HD_Head_Main", "flow_rate_m3h": 400.0},
            {"from": "HVAC_Accom", "to": "VENT_Eng", "flow_rate_m3h": 50.0},
        ],
        "adjacency": [
            {"from": "Berth", "to": "Mess", "type": "passageway"},
            {"from": "Mess", "to": "Open_Deck", "type": "unmapped_type_x"},
        ],
    }
    manifest = {
        "platform": name,
        "nominal_complement": {"passengers": 0, "crew": 30},
        "manifest": [
            {"class_id": "hands", "role_group": "crew", "count": 30,
             "berth_zone": "Berth", "duty_zone": "Engine_Rm"},
        ],
    }
    notes = {
        "platform": name, "era": "usn_ww2",
        "zone_modes": {
            "Berth": {"mode": "nat_supply", "evidence": "era_rule"},
            "Mess": {"mode": "mech_exhaust", "evidence": "era_rule"},
            "Engine_Rm": {"mode": "mech_supply_exhaust", "evidence": "era_rule"},
        },
    }
    root = _write_platform(tmp_path, name, zones, airflow, manifest, notes)
    return hull_audit.audit_platform(root)


def _findings(b: hull_audit.PlatformBundle) -> set[tuple[str, str, str]]:
    return {(f.check, f.severity, f.scope) for f in b.findings}


def test_sealed_and_starved_detection(tmp_path):
    b = _mini(tmp_path)
    f = _findings(b)
    assert ("flow_closure", "flag", "Void_Room") in f
    assert ("flow_closure", "note", "STARVED") in f
    assert ("topology", "note", "Open_Deck") not in f  # exterior is not a flag


def test_orphan_classification(tmp_path):
    b = _mini(tmp_path)
    f = _findings(b)
    # Authored sanitary head is intentionally orphan -> not a flag
    head_main_severities = {sev for _, sev, scope in f if scope == "Head_Main"}
    assert "flag" not in head_main_severities
    # Medical zone with no passage IS a flag
    assert ("topology", "flag", "Sick_Bay") in f


def test_referential_integrity(tmp_path):
    b = _mini(tmp_path)
    bad = dict(b.manifest)
    bad["manifest"] = [{"class_id": "ghost", "role_group": "crew", "count": 1,
                        "berth_zone": "NOWHERE", "duty_zone": "Berth"}]
    b.manifest = bad
    b.findings.clear()
    hull_audit._check_references(b)
    ghost = [f for f in b.findings if f.scope == "ghost"]
    assert any("berth_zone" in f.message for f in ghost)


def test_mode_group_mismatch(tmp_path):
    b = _mini(tmp_path)
    assert any(s == "Mess" for _, _, s in _findings(b))


def test_metrics_and_berth(tmp_path):
    b = _mini(tmp_path)
    m = b.metrics
    assert m["crew"] == 30
    assert m["dining_seats"] == 15
    assert m["berth_need"] == 30
    assert m["berth_cap"] == 30
    assert m["ach_by_class"]["sanitary"] == pytest.approx(19.1)
    assert m["ach_by_class"]["berthing"] == pytest.approx(6.0)


def test_berth_oversubscription_flag(tmp_path):
    zones = [_zone("Berth", "Room", max_occupancy=10),
             _zone("Mess", "Dining", max_occupancy=15)]
    airflow = {"hvac_zones": [{"id": "G", "rooms": ["Berth", "Mess"], "ach": 6.0}],
               "cross_zone_links": [], "adjacency": [
                   {"from": "Berth", "to": "Mess", "type": "passageway"}]}
    manifest = {"nominal_complement": {"passengers": 0, "crew": 25},
                "manifest": [{"class_id": "c", "role_group": "crew", "count": 25,
                              "berth_zone": "Berth", "duty_zone": "Mess"}]}
    root = _write_platform(tmp_path, "over_ship", zones, airflow, manifest)
    b = hull_audit.audit_platform(root)
    assert ("metrics", "flag", "Berth") in _findings(b)


def test_hot_bunk_sanctions_oversubscription(tmp_path):
    zones = [_zone("Berth", "Room", max_occupancy=10, hot_bunk_ratio=2),
             _zone("Mess", "Dining", max_occupancy=15)]
    airflow = {"hvac_zones": [{"id": "G", "rooms": ["Berth", "Mess"], "ach": 6.0}],
               "cross_zone_links": [], "adjacency": [
                   {"from": "Berth", "to": "Mess", "type": "passageway"}]}
    manifest = {"nominal_complement": {"passengers": 0, "crew": 20},
                "manifest": [{"class_id": "c", "role_group": "crew", "count": 20,
                              "berth_zone": "Berth", "duty_zone": "Mess"}]}
    root = _write_platform(tmp_path, "hotbunk_ship", zones, airflow, manifest)
    b = hull_audit.audit_platform(root)
    assert ("metrics", "flag", "Berth") not in _findings(b)


def test_era_contradiction_and_anachronism(tmp_path):
    a = _mini(tmp_path, "ship_a")
    c = _mini(tmp_path, "ship_b")
    notes = dict(c.systems_notes)
    notes["zone_modes"] = dict(notes["zone_modes"], Mess={"mode": "nat_supply", "evidence": "era_rule"})
    c.systems_notes = notes
    c.findings.clear()
    hull_audit._check_modes(c)
    fleet = hull_audit._era_contradictions([a, c])
    era_scopes = {f.scope for f in fleet if f.check == "era_consistency"}
    assert "usn_ww2/mess" in era_scopes
    # anachronism: mech_ac on a ww2 hull
    a.findings.clear()
    a.systems_notes["zone_modes"]["Berth"] = {"mode": "mech_ac", "evidence": "era_plausible"}
    hull_audit._check_modes(a)
    assert ("modes", "flag", "Berth") in _findings(a)


def test_adjacency_type_coverage(tmp_path):
    b = _mini(tmp_path)
    cov = hull_audit._adjacency_type_coverage([b])
    assert "unmapped_type_x" in cov["unmapped"]
    assert "passageway" not in cov["unmapped"]


def test_render_and_json_out(tmp_path):
    b = _mini(tmp_path)
    md = hull_audit.render_markdown([b], [], hull_audit._adjacency_type_coverage([b]))
    assert "toy_ship" in md
    assert "Fleet panel" in md
    out = tmp_path / "sub" / "audit.json"
    out.parent.mkdir()
    rc = hull_audit.main(["--platforms", "toy_ship", "--platforms-dir", str(tmp_path),
                          "--json-out", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert "toy_ship" in payload["platforms"]


def test_real_fleet_loads(tmp_path):
    """All committed platforms audit without raising — smoke, not a verdict."""
    dirs = hull_audit._collect_platform_dirs(None, hull_audit.PLATFORMS_DIR)
    assert len(dirs) > 10
    for d in dirs:
        b = hull_audit.audit_platform(d)
        assert b.metrics
