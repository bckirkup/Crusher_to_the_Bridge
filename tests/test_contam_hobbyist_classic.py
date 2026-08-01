"""Hobbyist Contam bootstrap for classic_cruise_1900."""

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

_PLATFORM = "classic_cruise_1900"
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


def test_classic_hobbyist_export() -> None:
    spatial, airflow = _load()
    overrides = load_hobbyist_overrides(str(_CONTAM.parent))
    text, path_map = export_contamw34(
        spatial, airflow, hobbyist=True, overrides=overrides,
    )
    assert "(hobbyist)" in text
    assert _section_count(text, "flow paths") == len(path_map)
    assert len(path_map) >= 200


def test_classic_bundled_hobbyist_prj() -> None:
    text = (_CONTAM / "platform.prj").read_text(encoding="utf-8")
    entries = json.loads((_CONTAM / "path_map.json").read_text(encoding="utf-8"))
    assert "(hobbyist)" in text
    assert _section_count(text, "flow paths") == len(entries)
    assert len(path_map_from_prj(text)) == len(entries)
