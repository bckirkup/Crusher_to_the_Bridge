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


def _export(links, *, hobbyist=False):
    base, spatial, airflow = _load()
    air = json.loads(json.dumps(airflow))
    air["cross_zone_links"] = links
    overrides = load_hobbyist_overrides(str(base)) if hobbyist else None
    return export_prj_with_path_map(
        spatial, air, hobbyist=hobbyist, overrides=overrides,
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


def test_oneway_flow_scaling_is_graded_and_orientation_stable() -> None:
    low_text, low_map = _export([_oneway_link(60.0)])
    high_text, high_map = _export([_oneway_link(120.0)])

    def coefficient(text):
        match = re.search(
            r"(?m)^\s*\d+\s+24\s+plr_bdq\s+.*\n\s*0\s+([0-9.eE+-]+)\s+0\.5",
            text,
        )
        assert match is not None
        return float(match.group(1))

    assert coefficient(high_text) == pytest.approx(
        2.0 * coefficient(low_text), rel=1e-9,
    )
    low_rows = {
        (e["from_zone"], e["to_zone"]) for e in low_map
        if e["kind"] == "x1x2_oneway_pressure"
    }
    high_rows = {
        (e["from_zone"], e["to_zone"]) for e in high_map
        if e["kind"] == "x1x2_oneway_pressure"
    }
    assert low_rows == high_rows == {("MedBay", "Mess_Hall")}
