"""Hull dynamics audit tests — invariants on synthetic platforms.

Drainage fingerprint on a tiny graph; occupancy-smoke helpers
(manifest->agent_classes translation, crew source, spec shape). The
ShipSimulation voyage itself is exercised by the tool, not the unit tier.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import hull_audit  # noqa: E402
from tools import hull_dynamics_audit as dyn  # noqa: E402


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
            _zone("Berth", "Room", max_occupancy=30),
            _zone("Mess", "Dining", max_occupancy=15),
            _zone("Void_Room", "Room"),   # sealed: ungrouped, no paths
            _zone("Open_Deck", "Free"),   # ungrouped exterior
        ],
    }))
    (d / "air_flow_paths.json").write_text(json.dumps({
        "platform": name, "oa_fraction": 0.2, "hvac_duty": 1.0,
        "hvac_zones": [
            {"id": "HVAC_Accom", "rooms": ["Berth", "Mess"],
             "ach": 6.0, "oa_fraction": 0.3},
        ],
        "paths": [],
        "adjacencies": [
            {"zones": ["Berth", "Mess"], "type": "passageway"},
        ],
    }))
    return hull_audit.load_platform(d)


def test_drainage_sealed_zone_retains_its_mass(tmp_path):
    fp = dyn.drainage_fingerprint(_bundle(tmp_path), epochs=24)
    assert fp["zones"] == 4
    retained = {s["zone"]: s["retained_mass"] for s in fp["top_accumulating"]}
    # sealed + exterior zones hold (nearly) all injected mass; HVAC zones drain
    assert retained.get("Void_Room", 0.0) == pytest.approx(1.0, abs=0.05)
    assert fp["retained_frac_final"] < 1.0


def test_drainage_curve_is_monotone_decreasing(tmp_path):
    fp = dyn.drainage_fingerprint(_bundle(tmp_path), epochs=24)
    vals = [c["retained_frac"] for c in fp["curve"]]
    assert all(b <= a + 1e-9 for a, b in zip(vals, vals[1:]))


_MANIFEST = {"manifest": [
    {"class_id": "deck", "role_group": "crew", "count": 10,
     "berth_zone": "Crew_Quarters", "duty_zone": "Bridge"},
    {"class_id": "eng", "role_group": "crew", "count": 5,
     "berth_zone": "Eng_Berthing", "duty_zone": "Engine_Rm"},
]}


def test_manifest_agent_classes_pin_exact_zones(tmp_path):
    b = _bundle(tmp_path)
    b.manifest = _MANIFEST
    classes = dyn._manifest_agent_classes(b)
    assert [c["class_id"] for c in classes] == ["deck", "eng"]
    fracs = [c["fraction"] for c in classes]
    assert sum(fracs) == pytest.approx(1.0)
    assert classes[0]["home_zone_preference"] == "Crew_Quarters"
    assert classes[1]["duty_zone"] == "Engine_Rm"


def test_manifest_agent_classes_none_without_manifest(tmp_path):
    assert dyn._manifest_agent_classes(_bundle(tmp_path)) is None


def test_crew_source_prefers_manifest(tmp_path):
    b = _bundle(tmp_path)
    assert dyn._crew_source(b) == (30, "nominal_complement")
    b.manifest = _MANIFEST
    assert dyn._crew_source(b) == (15, "manifest")


def test_null_infection_spec_nulls_seed_and_removes_nothing():
    spec = dyn._null_infection_spec("mega_cruise_5000", epochs=48,
                                    num_agents=50, seed=7)
    assert spec["run"]["num_epochs"] == 48
    assert spec["run"]["random_seed"] == 7
    pov = spec["pathogen_overrides"]
    assert pov["norwalk_gi"]["initial_infected"] is None
    assert pov.get("remove", []) == []


def test_main_smoke_pce874_manifest_arm(tmp_path):
    """End-to-end: 2-epoch manifest-arm voyage + drainage on pce_874."""
    out = tmp_path / "sm.json"
    md = tmp_path / "sm.md"
    rc = dyn.main([
        "--platforms", "pce_874", "--epochs", "2", "--arms", "manifest",
        "--json-out", str(out), "--md-out", str(md),
    ])
    assert rc == 0
    occ = json.loads(out.read_text())["rows"][0]["occupancy"]
    pins = occ["pin_resolution"]
    duty_pins = {p["pin"] for p in pins["unresolvable_duty_pins"]}
    # Engine_Rm is Engineering-typed: outside the Free+Dining duty domain
    assert "Engine_Rm" in duty_pins
    assert occ["manifest"]["home_on_manifest_berth_frac"] == pytest.approx(1.0)
    assert occ["manifest"]["visited_zones"] > 0
    assert "Drainage fingerprint" in md.read_text()


def test_main_skip_occupancy_runs_drainage_only(tmp_path):
    out = tmp_path / "sm.json"
    rc = dyn.main([
        "--platforms", "pce_874", "--epochs", "2", "--skip-occupancy",
        "--json-out", str(out),
    ])
    assert rc == 0
    row = json.loads(out.read_text())["rows"][0]
    assert "occupancy" not in row
    assert row["drainage"]["retained_frac_final"] < 1.0


def test_render_includes_both_sections():
    rows = [{
        "platform": "toy",
        "drainage": {"zones": 4, "retained_frac_final": 0.5,
                     "curve": [{"epoch": 24, "retained_frac": 0.5}],
                     "top_accumulating": [{"zone": "Z", "retained_mass": 1.0}]},
        "occupancy": {"num_agents": 10, "crew_source": "manifest",
                      "default": {"visited_zones": 3, "never_occupied_interior": ["X"],
                                  "overflow_zones": [], "night_top3": [],
                                  "home_zone_distinct": 2,
                                  "home_on_manifest_berth_frac": 0.5,
                                  "top_home_zones": []}},
    }]
    md = dyn.render_markdown(rows)
    for needle in ("Drainage fingerprint", "Occupancy smoke", "toy", "X"):
        assert needle in md, needle
