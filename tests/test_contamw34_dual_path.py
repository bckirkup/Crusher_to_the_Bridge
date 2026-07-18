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


@pytest.mark.parametrize(
    "fixture",
    ["3-Room-OffAt14days.prj", "dcvSimple.prj"],
)
def test_path_map_from_prj_authentic_fixtures(fixture: str) -> None:
    """Path A contract: path_map comes from the PRJ, not JSON export order."""
    from tools.contamw34_prj import path_map_from_prj

    text = (_FIXTURES / fixture).read_text(encoding="utf-8")
    entries = path_map_from_prj(text)
    assert entries
    assert [e["path_nr"] for e in entries] == list(range(1, len(entries) + 1))
    kinds = {e["kind"] for e in entries}
    if fixture.startswith("3-Room"):
        assert "ahs_supply" in kinds or "ahs_return" in kinds
        assert any(int(e.get("ahs_nr") or 0) > 0 for e in entries)
    # Every entry has ContamX bridge fields
    for e in entries:
        assert "from_zone" in e and "to_zone" in e
        assert "crusher_transfer" in e


def test_simplify_cli_writes_path_map(tmp_path) -> None:
    src = _FIXTURES / "3-Room-OffAt14days.prj"
    # Output must stay under the repo root (path containment policy)
    out = REPO_ROOT / "telemetry_buffer" / "_test_contam_simplify"
    if out.exists():
        import shutil
        shutil.rmtree(out)
    try:
        spatial, airflow, pmap = contam_prj_bridge.simplify_prj_to_platform(
            str(src), str(out),
        )
        assert Path(spatial).is_file()
        assert Path(airflow).is_file()
        assert Path(pmap).is_file()
        entries = json.loads(Path(pmap).read_text(encoding="utf-8"))
        assert isinstance(entries, list) and entries
        assert any(e.get("kind", "").startswith("ahs_") for e in entries)
    finally:
        import shutil
        if out.exists():
            shutil.rmtree(out)


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


_AHS_SYSTEM_FLAGS = {16, 32, 64}
_AHS_TERMINAL_FLAG = 8


def _parse_flow_paths(text: str) -> dict[int, dict[str, float | int]]:
    """Parse ContamW flow-path records: nr → flag/e#/a#/Fahs."""
    paths: dict[int, dict[str, float | int]] = {}
    in_section = False
    for line in text.splitlines():
        if "! flow paths:" in line:
            in_section = True
            continue
        if not in_section:
            continue
        if line.strip() == "-999":
            break
        if line.strip().startswith("!"):
            continue
        toks = line.split()
        if len(toks) < 19 or not toks[0].isdigit():
            continue
        paths[int(toks[0])] = {
            "flag": int(toks[1]),
            "elem": int(toks[4]),
            "ahs": int(toks[7]),
            "fahs": float(toks[18]),
        }
    return paths


def _parse_ahs_system_paths(text: str) -> list[tuple[int, int, int, int]]:
    """Return (ahs_nr, pr, ps, px) from the simple-AHS section."""
    rows: list[tuple[int, int, int, int]] = []
    in_section = False
    for line in text.splitlines():
        if "simple AHS:" in line:
            in_section = True
            continue
        if not in_section:
            continue
        if line.strip() == "-999":
            break
        if line.strip().startswith("!"):
            continue
        toks = line.split()
        if len(toks) >= 7 and toks[0].isdigit():
            rows.append(
                (int(toks[0]), int(toks[3]), int(toks[4]), int(toks[5]))
            )
    return rows


def _zone_contam_names(text: str) -> list[str]:
    names: list[str] = []
    in_section = False
    for line in text.splitlines():
        if "! zones:" in line:
            in_section = True
            continue
        if not in_section:
            continue
        if line.strip() == "-999":
            break
        if line.strip().startswith("!"):
            continue
        toks = line.split()
        if len(toks) >= 11 and toks[0].isdigit():
            names.append(toks[10])
    return names


@pytest.mark.parametrize(
    "platform",
    [
        "destroyer_baseline",
        "enterprise_constitution_tos",
        "enterprise_galaxy_tng",
        "mega_cruise_5000",
    ],
)
def test_contamw34_export_contamx_invariants(platform: str) -> None:
    """ContamX-critical grammar: ≤15-char names, AHS a#/e#/Fahs semantics."""
    spatial, airflow = _load_platform(platform)
    text, path_map = contam_prj_bridge.export_prj_with_path_map(spatial, airflow)

    names = _zone_contam_names(text)
    assert names
    assert all(len(n) <= 15 for n in names), [
        n for n in names if len(n) > 15
    ]
    assert len(names) == len(set(names))

    paths = _parse_flow_paths(text)
    assert paths
    for nr, rec in paths.items():
        flag = int(rec["flag"])
        elem = int(rec["elem"])
        ahs = int(rec["ahs"])
        if flag in _AHS_SYSTEM_FLAGS:
            assert ahs == 0, f"path {nr}: system path must have a#=0"
            assert elem == 0, f"path {nr}: system path must have e#=0"
        if flag == _AHS_TERMINAL_FLAG:
            assert ahs > 0, f"path {nr}: terminal must reference an AHS"
            assert elem == 0, f"path {nr}: terminal must have e#=0"
            assert float(rec["fahs"]) > 0, f"path {nr}: terminal Fahs required"

    for ahs_nr, pr, ps, px in _parse_ahs_system_paths(text):
        assert int(paths[pr]["flag"]) == 16, f"ahs {ahs_nr} pr not recirc"
        assert int(paths[ps]["flag"]) == 32, f"ahs {ahs_nr} ps not OA"
        assert int(paths[px]["flag"]) == 64, f"ahs {ahs_nr} px not exhaust"

    real_ids = {z["id"] for z in spatial["zones"]}
    for entry in path_map:
        if entry.get("crusher_transfer"):
            assert entry["from_zone"] in real_ids
            assert entry["to_zone"] in real_ids

    # Every real zone must have an envelope leak to ambient (Jacobian ref)
    leak_zones = {
        e["from_zone"] for e in path_map if e.get("kind") == "envelope_leak"
    }
    assert leak_zones == real_ids
    for entry in path_map:
        if entry.get("kind") == "envelope_leak":
            assert entry["to_zone"] == "ambient"
            assert entry.get("crusher_transfer") is False
            pnr = int(entry["path_nr"])
            assert int(paths[pnr]["elem"]) == 2  # EnvLeak orifice
            assert int(paths[pnr]["ahs"]) == 0

    # OA fraction schedule present; AHS path_map carries ahs_nr for bridging
    assert "OAFracW" in text or "OAFrac" in text
    ahs_entries = [e for e in path_map if str(e.get("kind", "")).startswith("ahs_")]
    assert ahs_entries
    assert all(int(e.get("ahs_nr") or 0) > 0 for e in ahs_entries)

    # Recirc paths reference week schedule 1 (fo)
    flow_paths = _parse_flow_paths(text)
    # Also parse schedule field from raw path lines
    sched_by_nr: dict[int, int] = {}
    in_paths = False
    for line in text.splitlines():
        if "! flow paths:" in line:
            in_paths = True
            continue
        if not in_paths:
            continue
        if line.strip() == "-999":
            break
        if line.strip().startswith("!"):
            continue
        toks = line.split()
        if len(toks) >= 9 and toks[0].isdigit():
            sched_by_nr[int(toks[0])] = int(toks[8])
    for _ahs_nr, pr, _ps, _px in _parse_ahs_system_paths(text):
        assert sched_by_nr.get(pr, 0) >= 1, f"recirc path {pr} missing OA schedule"
        assert int(flow_paths[pr]["flag"]) == 16


def test_unique_contam_name_truncates_and_dedupes() -> None:
    from tools.contamw34_prj import _unique_contam_name

    used: set[str] = set()
    a = _unique_contam_name("zone_saucer_command_bridge", used)
    b = _unique_contam_name("zone_saucer_command_bridge", used)
    assert len(a) <= 15 and len(b) <= 15
    assert a != b
    assert a in used and b in used
