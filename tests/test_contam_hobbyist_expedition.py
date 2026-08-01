"""Hobbyist Contam bootstrap for expedition_cruise_450."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.contam_hobbyist import load_hobbyist_overrides
from tools.contamw34_prj import export_contamw34, path_map_from_prj

_PLATFORM = "expedition_cruise_450"
_CONTAM = REPO_ROOT / "data" / "platforms" / _PLATFORM / "contam"


def _load() -> tuple[dict, dict]:
    base = REPO_ROOT / "data" / "platforms" / _PLATFORM
    return (
        json.loads((base / "spatial_layout.json").read_text(encoding="utf-8")),
        json.loads((base / "air_flow_paths.json").read_text(encoding="utf-8")),
    )


def _section_count(text: str, marker: str) -> int:
    m = re.search(rf"^(\d+) ! {re.escape(marker)}:", text, re.M)
    assert m is not None, f"missing {marker}"
    return int(m.group(1))


def _zone_names_from_prj(text: str) -> list[str]:
    names: list[str] = []
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
        if toks and toks[0].isdigit() and len(toks) >= 11:
            names.append(toks[10])
    return names


def test_expedition_hobbyist_export() -> None:
    spatial, airflow = _load()
    overrides = load_hobbyist_overrides(str(_CONTAM.parent))
    text, path_map = export_contamw34(
        spatial, airflow, hobbyist=True, overrides=overrides,
    )
    assert "(hobbyist)" in text
    assert "MERV8" in text or "HEPA" in text
    assert _section_count(text, "flow paths") == len(path_map)
    assert len(path_map) >= 100
    names = _zone_names_from_prj(text)
    assert names and all(len(n) <= 15 for n in names)


def test_expedition_bundled_hobbyist_prj() -> None:
    text = (_CONTAM / "platform.prj").read_text(encoding="utf-8")
    entries = json.loads((_CONTAM / "path_map.json").read_text(encoding="utf-8"))
    assert "(hobbyist)" in text
    assert _section_count(text, "flow paths") == len(entries)
    derived = path_map_from_prj(text)
    assert len(derived) == len(entries)
