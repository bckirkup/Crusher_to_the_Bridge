"""
test_contam_hobbyist_mega.py – Mega cruise hobbyist Contam (scale-safe)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.contam_hobbyist import load_hobbyist_overrides
from tools.contamw34_prj import export_contamw34, path_map_from_prj

_PLATFORM = "mega_cruise_5000"
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


def test_mega_hobbyist_export_scale_safe() -> None:
    spatial, airflow = _load()
    overrides = load_hobbyist_overrides(str(_CONTAM.parent))
    t0 = time.perf_counter()
    text, path_map = export_contamw34(
        spatial, airflow, hobbyist=True, overrides=overrides,
    )
    elapsed = time.perf_counter() - t0
    assert elapsed < 5.0, f"export too slow: {elapsed:.2f}s"
    assert "(hobbyist)" in text
    assert "CabinRel" in text or "ElevBank" in text or "Stairwell" in text
    assert "MERV8" in text or "HEPA" in text
    assert _section_count(text, "flow paths") == len(path_map)
    assert len(path_map) >= 600
    assert _section_count(text, "duct junctions") >= 10
    assert _section_count(text, "species") == 2
    # ContamX-critical: names ≤ 15
    names = []
    in_z = False
    for line in text.splitlines():
        if "! zones:" in line:
            in_z = True
            continue
        if in_z and line.strip() == "-999":
            break
        if in_z and not line.strip().startswith("!") and line.split():
            toks = line.split()
            if toks[0].isdigit() and len(toks) >= 11:
                names.append(toks[10])
    assert names and all(len(n) <= 15 for n in names)


def test_mega_bundled_hobbyist_prj() -> None:
    text = (_CONTAM / "platform.prj").read_text(encoding="utf-8")
    entries = json.loads((_CONTAM / "path_map.json").read_text(encoding="utf-8"))
    assert "(hobbyist)" in text
    assert _section_count(text, "flow paths") == len(entries)
    derived = path_map_from_prj(text)
    assert len(derived) == len(entries)
