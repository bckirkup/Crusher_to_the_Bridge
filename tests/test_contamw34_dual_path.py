"""
test_contamw34_dual_path.py – ContamW 3.4 export / simplify / bundles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Covers Contam dual-path plumbing without requiring the ContamX binary:

- ContamW 3.4 section inventory on export (destroyer + Enterprise + mega)
- path_map length matches flow-path count
- Authentic fixture simplify (BS-2026 supplementary PRJs)
- Bundled platform contam/ assets
- resolve_contam_prj_path prefers bundled / configured PRJ
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.contamx_transport import (  # noqa: E402
    ContamXTransportEngine,
    resolve_contam_prj_path,
)
from tools import contam_prj_bridge  # noqa: E402
from tools.contamw34_prj import simplify_contamw34  # noqa: E402

_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "contam"
_REQUIRED_SECTION_MARKERS = (
    " ! contaminants:",
    " ! species:",
    " ! levels plus icon data:",
    " ! day-schedules:",
    " ! flow elements:",
    " ! simple AHS:",
    " ! zones:",
    " ! flow paths:",
    " ! duct junctions:",
    " ! occupancy schedules:",
)


def _load_platform(name: str) -> tuple[dict, dict]:
    base = REPO_ROOT / "data" / "platforms" / name
    with open(base / "spatial_layout.json", encoding="utf-8") as fh:
        spatial = json.load(fh)
    with open(base / "air_flow_paths.json", encoding="utf-8") as fh:
        airflow = json.load(fh)
    return spatial, airflow


@pytest.mark.parametrize(
    "platform",
    [
        "destroyer_baseline",
        "enterprise_constitution_tos",
        "enterprise_galaxy_tng",
        "mega_cruise_5000",
    ],
)
def test_contamw34_export_has_required_sections(platform: str) -> None:
    spatial, airflow = _load_platform(platform)
    text, path_map = contam_prj_bridge.export_prj_with_path_map(spatial, airflow)
    assert text.startswith("ContamW 3.4")
    assert "steady simulation" in text
    for marker in _REQUIRED_SECTION_MARKERS:
        assert marker in text, f"missing section marker {marker!r}"
    # Flow path count in PRJ matches path_map
    m = re.search(r"^(\d+) ! flow paths:", text, re.M)
    assert m is not None
    assert int(m.group(1)) == len(path_map)
    # Real zones preserved (phantoms are extra)
    m_z = re.search(r"^(\d+) ! zones:", text, re.M)
    assert m_z is not None
    assert int(m_z.group(1)) >= len(spatial["zones"])


def test_bundled_enterprise_and_mega_contam_dirs() -> None:
    for name in (
        "mega_cruise_5000",
        "enterprise_constitution_tos",
        "enterprise_galaxy_tng",
    ):
        contam = REPO_ROOT / "data" / "platforms" / name / "contam"
        prj = contam / "platform.prj"
        pmap = contam / "path_map.json"
        assert prj.is_file(), f"missing {prj}"
        assert pmap.is_file(), f"missing {pmap}"
        text = prj.read_text(encoding="utf-8")
        assert text.startswith("ContamW 3.4")
        entries = json.loads(pmap.read_text(encoding="utf-8"))
        assert isinstance(entries, list) and entries
        m = re.search(r"^(\d+) ! flow paths:", text, re.M)
        assert m is not None
        assert int(m.group(1)) == len(entries)


@pytest.mark.parametrize(
    "fixture",
    ["3-Room-OffAt14days.prj", "dcvSimple.prj"],
)
def test_simplify_authentic_fixtures(fixture: str) -> None:
    path = _FIXTURES / fixture
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    warn: list[str] = []
    spatial, airflow = simplify_contamw34(text, warnings_out=warn)
    assert spatial["zones"], f"{fixture} produced no zones"
    assert "hvac_zones" in airflow
    assert "adjacency" in airflow
    # Controls / schedules present in fixtures should be drop-warned or empty
    assert all(isinstance(z.get("volume_m3"), (int, float)) for z in spatial["zones"])


def test_resolve_contam_prj_path_bundled() -> None:
    spatial = {"platform": "enterprise_galaxy_tng"}
    cfg: dict = {"hvac": {"contamx": {}}}
    resolved = resolve_contam_prj_path(str(REPO_ROOT), cfg, spatial)
    assert resolved is not None
    assert resolved.endswith("enterprise_galaxy_tng/contam/platform.prj")


def test_resolve_contam_prj_path_rejects_traversal_platform() -> None:
    from engines.contamx_runner import ContamXUnavailable

    spatial = {"platform": "../etc"}
    cfg: dict = {"hvac": {"contamx": {}}}
    with pytest.raises(ContamXUnavailable):
        resolve_contam_prj_path(str(REPO_ROOT), cfg, spatial)


def test_resolve_contam_prj_path_explicit_override(tmp_path) -> None:
    # Use an in-repo bundled file as the explicit override target
    bundled = (
        REPO_ROOT / "data" / "platforms" / "enterprise_constitution_tos"
        / "contam" / "platform.prj"
    )
    spatial = {"platform": "enterprise_galaxy_tng"}
    cfg = {
        "hvac": {
            "contamx": {
                "prj_path": str(bundled.relative_to(REPO_ROOT)),
            },
        },
    }
    resolved = resolve_contam_prj_path(str(REPO_ROOT), cfg, spatial)
    assert resolved is not None
    assert "enterprise_constitution_tos" in resolved


def test_contamx_engine_skips_ambient_path_endpoints() -> None:
    spatial, _airflow = _load_platform("destroyer_baseline")
    # path_map index 0 => ContamX path nr 1
    path_map = [
        ("ambient", "Bridge", True),
        ("Bridge", "MedBay", False),
    ]
    flows = {1: 10.0, 2: 5.0}
    engine = ContamXTransportEngine.from_flow_field(
        spatial, path_map, flows,
    )
    # ambient→Bridge skipped; Bridge→MedBay kept
    assert len(engine.airflow_paths) == 1
    assert engine.airflow_paths[0].from_zone == "Bridge"
    assert engine.airflow_paths[0].to_zone == "MedBay"


def test_path_map_not_adjacency_only() -> None:
    spatial, airflow = _load_platform("destroyer_baseline")
    _text, path_map = contam_prj_bridge.export_prj_with_path_map(spatial, airflow)
    assert len(path_map) > len(airflow["adjacency"])
    kinds = {e["kind"] for e in path_map}
    assert "ahs_supply" in kinds or "ahs_oa" in kinds
