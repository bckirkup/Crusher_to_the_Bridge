"""Exporter semantics for declared cross-zone direction/mechanism/filtered."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.contam_hobbyist import load_hobbyist_overrides  # noqa: E402
from tools.contam_prj_bridge import export_prj_with_path_map  # noqa: E402

_PLATFORM = "destroyer_baseline"


def _load():
    base = REPO_ROOT / "data" / "platforms" / _PLATFORM
    spatial = json.loads((base / "spatial_layout.json").read_text())
    airflow = json.loads((base / "air_flow_paths.json").read_text())
    return base, spatial, airflow


def _export(links, *, hobbyist=False, ahs_terminal_mode=None):
    base, spatial, airflow = _load()
    air = json.loads(json.dumps(airflow))
    air["cross_zone_links"] = links
    overrides = load_hobbyist_overrides(str(base)) if hobbyist else None
    return export_prj_with_path_map(
        spatial, air, hobbyist=hobbyist, overrides=overrides,
        ahs_terminal_mode=ahs_terminal_mode,
    )


def _symbols_by_path(text, path_map, kinds):
    elem_symbol = {}
    for match in re.finditer(
        r"(?m)^\s*(\d+)\s+(?:23|24|28)\s+(plr_orfc|plr_bdq|fan_cvf)\s+",
        text,
    ):
        elem_symbol[int(match.group(1))] = match.group(2)
    rows = {line.split()[0]: line.split() for line in text.splitlines()
            if line.split() and line.split()[0].isdigit()}
    out = {}
    for entry in path_map:
        if entry.get("kind") not in kinds:
            continue
        toks = rows[str(entry["path_nr"])]
        out[entry["kind"]] = elem_symbol[int(toks[4])]
    return out


def _bdq_params(text):
    """Return ``(lam, Cp, xp, Cn, xn)`` tuples for emitted plr_bdq elements."""
    return [
        tuple(float(tok) for tok in match.group(2).split())
        for match in re.finditer(
            r"(?ms)^\s*(\d+)\s+24\s+plr_bdq\s+\S+\s*\n\s*\n\s*([^\n]+)",
            text,
        )
    ]


def _oneway_link(flow):
    return {
        "from": "MedBay",
        "to": "Mess_Hall",
        "flow_rate_m3h": flow,
        "path": "x1x2_oneway_pressure",
        "direction": "oneway",
        "mechanism": "pressure_opening",
        "filtered": False,
        "is_hvac_ducted": False,
    }


def test_element_type_is_function_of_direction_mechanism_filtered() -> None:
    links = [
        _oneway_link(120.0),
        {
            "from": "Mess_Hall", "to": "Galley", "flow_rate_m3h": 90.0,
            "path": "x1x2_bidir_pressure", "direction": "bidirectional",
            "mechanism": "pressure_opening", "filtered": False,
            "is_hvac_ducted": False,
        },
        {
            "from": "Galley", "to": "MedBay", "flow_rate_m3h": 60.0,
            "path": "x1x2_prescribed", "direction": "oneway",
            "mechanism": "prescribed_flow", "filtered": True,
            "is_hvac_ducted": False,
        },
    ]
    text, path_map = _export(links, hobbyist=True)
    symbols = _symbols_by_path(text, path_map, {l["path"] for l in links})
    assert symbols == {
        "x1x2_oneway_pressure": "plr_bdq",
        "x1x2_bidir_pressure": "plr_orfc",
        "x1x2_prescribed": "fan_cvf",
    }
    prescribed = next(
        e for e in path_map if e["kind"] == "x1x2_prescribed"
    )
    row = next(
        toks for toks in (line.split() for line in text.splitlines())
        if toks[:1] == [str(prescribed["path_nr"])] and len(toks) > 18
    )
    assert int(row[5]) > 0  # filtered selects the PRJ filter element


def test_commissioned_oneway_pressure_opening_has_documented_bdq_params() -> None:
    text, _ = _export(
        [_oneway_link(120.0)], ahs_terminal_mode="commissioned",
    )
    params = _bdq_params(text)
    assert len(params) == 1
    lam, cp, xp, cn, xn = params[0]
    assert lam > 0.0
    assert cp == pytest.approx(120.0 / 3600.0, rel=1e-12)
    assert xp == pytest.approx(0.5)
    assert cn == pytest.approx(0.0)
    assert xn == pytest.approx(0.5)


def test_oneway_flow_scaling_is_graded_and_orientation_stable() -> None:
    flows = (30.0, 60.0, 120.0)
    exports = {
        flow: _export(
            [_oneway_link(flow)], ahs_terminal_mode="commissioned",
        )
        for flow in flows
    }
    params = {}
    for flow, (text, _path_map) in exports.items():
        bdq = _bdq_params(text)
        assert len(bdq) == 1
        params[flow] = bdq[0]

    small, mid, large = (params[flow] for flow in flows)
    small_lam, small_cp = small[0], small[1]
    mid_lam, mid_cp = mid[0], mid[1]
    large_lam, large_cp = large[0], large[1]
    assert small_lam > 0.0
    assert small_cp < mid_cp < large_cp
    assert mid_cp == pytest.approx(2.0 * small_cp, rel=1e-9)
    assert large_cp == pytest.approx(2.0 * mid_cp, rel=1e-9)
    # NIST TN 1887r1 pp. 264-265: for n=0.5 the Re=30 transition
    # coefficient scales as C**1.5, so doubling design flow gives 2**1.5.
    assert mid_lam == pytest.approx((2.0**1.5) * small_lam, rel=1e-9)
    assert large_lam == pytest.approx((2.0**1.5) * mid_lam, rel=1e-9)
    low_rows = {
        (e["from_zone"], e["to_zone"])
        for e in exports[flows[0]][1]
        if e["kind"] == "x1x2_oneway_pressure"
    }
    high_rows = {
        (e["from_zone"], e["to_zone"])
        for e in exports[flows[-1]][1]
        if e["kind"] == "x1x2_oneway_pressure"
    }
    assert low_rows == high_rows == {("MedBay", "Mess_Hall")}
