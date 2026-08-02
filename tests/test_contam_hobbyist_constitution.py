"""
test_contam_hobbyist_constitution.py – Constitution hobbyist Contam golden
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.contam_hobbyist import load_hobbyist_overrides
from tools.contamw34_prj import export_contamw34

_PLATFORM = "enterprise_constitution_tos"
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


def test_constitution_hobbyist_export() -> None:
    spatial, airflow = _load()
    overrides = load_hobbyist_overrides(str(_CONTAM.parent))
    text, path_map = export_contamw34(
        spatial, airflow, hobbyist=True, overrides=overrides,
    )
    assert "(hobbyist)" in text
    assert "Turbolift" in text or "Turbo" in text
    assert "MERV14" in text or "HEPA" in text
    assert "Virus" in text
    assert "PocketDoor" in text or "PressBlk" in text
    assert _section_count(text, "wind pressure profiles") == 1
    assert _section_count(text, "duct junctions") >= 3
    assert _section_count(text, "flow paths") == len(path_map)
    assert len(path_map) >= 300
    assert _section_count(text, "annotations") >= 2


def test_constitution_bundled_hobbyist_prj() -> None:
    text = (_CONTAM / "platform.prj").read_text(encoding="utf-8")
    entries = json.loads((_CONTAM / "path_map.json").read_text(encoding="utf-8"))
    assert "(hobbyist)" in text
    assert _section_count(text, "flow paths") == len(entries)
    assert len(entries) >= 300
    assert "Sickbay" in text or "EngMain" in text
