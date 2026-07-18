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


def test_destroyer_hobbyist_export_section_counts() -> None:
    spatial, airflow = _load_platform()
    overrides = load_hobbyist_overrides(str(_CONTAM.parent))
    text, path_map = export_contamw34(
        spatial, airflow, hobbyist=True, overrides=overrides,
    )
    assert text.startswith("ContamW 3.4")
    assert "(hobbyist)" in text
    assert _section_count(text, "day-schedules") >= 2
    assert _section_count(text, "week-schedules") >= 2
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
    # Destroyer: 6 envelope + 6 adjacency + 3 cross + 3 AHS*(3 system + 2*rooms)
    # rooms: upper=1, main=3, lower=2 → terminals = 2*(1+3+2)=12
    # system = 9; total = 6+6+3+9+12 = 36
    assert len(path_map) == 36


def test_destroyer_hobbyist_typed_orifices_and_temps() -> None:
    spatial, airflow = _load_platform()
    overrides = load_hobbyist_overrides(str(_CONTAM.parent))
    text, path_map = export_contamw34(
        spatial, airflow, hobbyist=True, overrides=overrides,
    )
    assert "Ladder" in text
    assert "Passage" in text or "Opening" in text
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
