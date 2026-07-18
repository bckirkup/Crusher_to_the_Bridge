"""
test_contam_hobbyist_galaxy.py – Galaxy-class hobbyist Contam golden
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
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

_PLATFORM = "enterprise_galaxy_tng"
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


def test_galaxy_hobbyist_export() -> None:
    spatial, airflow = _load()
    overrides = load_hobbyist_overrides(str(_CONTAM.parent))
    text, path_map = export_contamw34(
        spatial, airflow, hobbyist=True, overrides=overrides,
    )
    assert "(hobbyist)" in text
    assert "TurboFwd" in text or "HabTrunk" in text or "CargoLift" in text
    assert "GalaxyACH" in text or "HEPA" in text
    assert "Ten Forward" in text or "Main Engineering" in text
    assert _section_count(text, "duct junctions") >= 5
    assert _section_count(text, "flow paths") == len(path_map)
    assert _section_count(text, "species") == 2


def test_galaxy_bundled_hobbyist_prj() -> None:
    text = (_CONTAM / "platform.prj").read_text(encoding="utf-8")
    entries = json.loads((_CONTAM / "path_map.json").read_text(encoding="utf-8"))
    assert "(hobbyist)" in text
    assert _section_count(text, "flow paths") == len(entries)
    assert "Arboretum" in text or "Ten Forward" in text
