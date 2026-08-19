"""
test_contam_hobbyist_destroyer.py – Hobbyist-plus Contam destroyer golden
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Offline ContamW 3.4 section / invariant checks for destroyer_baseline with
the shared hobbyist pack (no ContamX binary required).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.contam_hobbyist import load_hobbyist_overrides, load_hobbyist_pack
from tools.contamw34_prj import (
    export_contamw34,
    path_map_from_prj,
    simplify_contamw34,
)

_PLATFORM = "destroyer_baseline"
_CONTAM = REPO_ROOT / "data" / "platforms" / _PLATFORM / "contam"


def _load_platform() -> tuple[dict, dict]:
    base = REPO_ROOT / "data" / "platforms" / _PLATFORM
    with open(base / "spatial_layout.json", encoding="utf-8") as fh:
        spatial = json.load(fh)
    with open(base / "air_flow_paths.json", encoding="utf-8") as fh:
        airflow = json.load(fh)
    return spatial, airflow


def _section_count(text: str, marker: str) -> int:
    m = re.search(rf"^(\d+) ! {re.escape(marker)}:", text, re.M)
    assert m is not None, f"missing section {marker!r}"
    return int(m.group(1))


def test_hobbyist_pack_loads() -> None:
    pack = load_hobbyist_pack()
    assert "orifice_catalog" in pack
    assert "ladder" in pack["orifice_catalog"]["types"]
    assert "ship_hull" in pack["wind_profiles"]["profiles"]
    # Physically sized openings (not crack-scale catalog artifacts)
    types = pack["orifice_catalog"]["types"]
    assert types["doorway"]["area_m2"] == pytest.approx(1.8)
    assert types["passageway"]["area_m2"] == pytest.approx(2.0)
    assert types["hatch"]["area_m2"] == pytest.approx(0.36)
    assert types["cabin_relief"]["area_m2"] < 0.05
    assert pack["orifice_catalog"]["envelope_leak"]["area_m2"] == pytest.approx(
        0.0001
    )
    sched = pack["schedule_templates"]
    assert "DoorTrafficW" in {w["id"] for w in sched["week_schedules"]}
    assert sched["opening_schedule_by_type"]["passageway"] == "DoorTrafficW"
    assert sched["opening_schedule_by_type"]["cabin_relief"] is None


def test_destroyer_hobbyist_export_section_counts() -> None:
    spatial, airflow = _load_platform()
    overrides = load_hobbyist_overrides(str(_CONTAM.parent))
    text, path_map = export_contamw34(
        spatial, airflow, hobbyist=True, overrides=overrides,
    )
    assert text.startswith("ContamW 3.4")
    assert "(hobbyist)" in text
    assert _section_count(text, "day-schedules") >= 5
    assert _section_count(text, "week-schedules") >= 5
    assert "DoorTraff" in text
    assert "HatchOcc" in text
    assert "ShaftOpen" in text
    assert _section_count(text, "wind pressure profiles") == 1
    assert _section_count(text, "filter elements") >= 1
    assert _section_count(text, "filters") >= 1
    assert _section_count(text, "duct elements") == 1
    assert _section_count(text, "duct junctions") >= 2
    assert _section_count(text, "duct segments") >= 1
    assert _section_count(text, "control nodes") >= 2
    assert _section_count(text, "annotations") >= 2
    assert _section_count(text, "species") == 2
    assert "Virus" in text
    assert "Bridge CIC" in text or "Eng Rm" in text
    assert _section_count(text, "flow paths") == len(path_map)
    # ContamX: initial-concentration headers are n_items * n_contaminants
    n_zones = _section_count(text, "zones")
    n_ctm = _section_count(text, "contaminants")
    assert _section_count(text, "initial zone concentrations") == n_zones * n_ctm
    n_jct = _section_count(text, "duct junctions")
    assert _section_count(text, "initial junction concentrations") == n_jct * n_ctm
    # ContamX 3.4.0.3: vf_node_name present, no ContamW "T:" marker
    assert re.search(r"\bnone 0 0 0 0 -1 0\b", text)
    assert " T: " not in text
    assert re.search(r"\bT:", text) is None
    # Destroyer with room×room cross-zone expansion: 44 Contam paths
    # (6 envelope + 6 adjacency + 11 cross + 9 AHS system + 12 terminals)
    assert len(path_map) == 44


def test_destroyer_hobbyist_typed_orifices_and_temps() -> None:
    spatial, airflow = _load_platform()
    overrides = load_hobbyist_overrides(str(_CONTAM.parent))
    text, _path_map = export_contamw34(
        spatial, airflow, hobbyist=True, overrides=overrides,
    )
    assert "Ladder" in text
    assert "Passage" in text or "Opening" in text
    # Realistic passageway area appears in plr_orfc params (area then diameter)
    assert "0.5 2 1.5957691 0.6" in text
    assert "0.5 1.8 1.5138795 0.6" in text  # doorway catalog (bundled even if unused)
    # Engine deck hotter than bridge
    temps = {}
    in_zones = False
    for line in text.splitlines():
        if "! zones:" in line:
            in_zones = True
            continue
        if in_zones and line.strip() == "-999":
            break
        if not in_zones or line.strip().startswith("!"):
            continue
        toks = line.split()
        if len(toks) >= 11 and toks[0].isdigit():
            temps[toks[10]] = float(toks[8])
    assert temps.get("Engine_Room", 0) > temps.get("Bridge", 999)


def test_destroyer_adjacency_paths_use_opening_schedules() -> None:
    """Named doors/hatches/shafts get week-schedule multipliers (not always-open)."""
    from tools.contam_hobbyist import load_hobbyist_pack, resolve_opening_schedule

    spatial, airflow = _load_platform()
    overrides = load_hobbyist_overrides(str(_CONTAM.parent))
    pack = load_hobbyist_pack()
    text, path_map = export_contamw34(
        spatial, airflow, hobbyist=True, overrides=overrides,
    )

    week_id_to_nr = {
        w["id"]: i
        for i, w in enumerate(pack["schedule_templates"]["week_schedules"], 1)
    }

    sched_by_nr: dict[int, int] = {}
    in_paths = False
    for line in text.splitlines():
        if "! flow paths:" in line:
            in_paths = True
            continue
        if in_paths and line.strip() == "-999":
            break
        if not in_paths or line.strip().startswith("!"):
            continue
        toks = line.split()
        if len(toks) >= 9 and toks[0].isdigit():
            sched_by_nr[int(toks[0])] = int(toks[8])

    adj_entries = [
        e for e in path_map
        if e["kind"] in {
            "passageway", "doorway", "service_hatch", "hatch",
            "ladder_well", "ladder",
        }
    ]
    assert len(adj_entries) == 6
    for e in adj_entries:
        sched_id = resolve_opening_schedule(e["kind"], pack, overrides)
        assert sched_id is not None, e["kind"]
        assert sched_by_nr[e["path_nr"]] == week_id_to_nr[sched_id]


def test_resolve_opening_schedule_cabin_relief_unscheduled() -> None:
    from tools.contam_hobbyist import load_hobbyist_pack, resolve_opening_schedule

    pack = load_hobbyist_pack()
    assert resolve_opening_schedule("cabin_relief", pack, {}) is None
    assert resolve_opening_schedule("passageway", pack, {}) == "DoorTrafficW"
    assert resolve_opening_schedule(
        "passageway", pack, {"opening_schedule_map": {"passageway": "none"}},
    ) is None



def test_destroyer_bundled_prj_is_hobbyist() -> None:
    prj = _CONTAM / "platform.prj"
    pmap = _CONTAM / "path_map.json"
    assert prj.is_file()
    text = prj.read_text(encoding="utf-8")
    entries = json.loads(pmap.read_text(encoding="utf-8"))
    assert "(hobbyist)" in text
    assert _section_count(text, "flow paths") == len(entries)
    assert _section_count(text, "duct junctions") >= 2
    assert "Virus" in text


def test_path_map_from_prj_matches_export() -> None:
    spatial, airflow = _load_platform()
    overrides = load_hobbyist_overrides(str(_CONTAM.parent))
    text, path_map = export_contamw34(
        spatial, airflow, hobbyist=True, overrides=overrides,
    )
    derived = path_map_from_prj(text)
    assert len(derived) == len(path_map)
    assert all(d["path_nr"] == e["path_nr"] for d, e in zip(derived, path_map))
    kinds = {e["kind"] for e in derived}
    assert "ahs_supply" in kinds or "ahs_return" in kinds
    assert "envelope_leak" in kinds


def test_simplify_hobbyist_drops_fancy_sections() -> None:
    spatial, airflow = _load_platform()
    overrides = load_hobbyist_overrides(str(_CONTAM.parent))
    text, _ = export_contamw34(
        spatial, airflow, hobbyist=True, overrides=overrides,
    )
    warn: list[str] = []
    out_spatial, out_air = simplify_contamw34(text, warnings_out=warn)
    assert len(out_spatial["zones"]) == len(spatial["zones"])
    assert any("duct" in w.lower() or "filter" in w.lower() or "wind" in w.lower()
               for w in warn)
    assert "hvac_zones" in out_air
