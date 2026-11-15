"""Live ContamX controls for commissioned ``plr_bdq`` one-way openings.

The two-zone control isolates the documented NIST TN 1887r1 laminar
coefficient: forward pressure must open the passive path, reverse pressure
must leave it shut, and equal pressures must not leak.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.contamx_runner import (  # noqa: E402
    SimResults,
    find_contamx,
    run_contamx,
)
from tools.contam_prj_bridge import export_prj_with_path_map  # noqa: E402

_CONTAMX = find_contamx({})
pytestmark = pytest.mark.skipif(
    _CONTAMX is None,
    reason="ContamX binary not available in this environment",
)

_SPATIAL: dict[str, Any] = {
    "platform": "bdq_control",
    "zones": [
        {
            "id": "Zone_A",
            "volume_m3": 50.0,
            "floor_area_m2": 20.0,
            "ceiling_height_m": 2.5,
            "deck": "main",
        },
        {
            "id": "Zone_B",
            "volume_m3": 50.0,
            "floor_area_m2": 20.0,
            "ceiling_height_m": 2.5,
            "deck": "main",
        },
    ],
}


def _airflow(
    *,
    drive_from: str | None,
    drive_to: str | None,
    drive_flow_m3h: float = 100.0,
    bdq_flow_m3h: float = 120.0,
) -> dict[str, Any]:
    links: list[dict[str, Any]] = [
        {
            "from": "Zone_A",
            "to": "Zone_B",
            "flow_rate_m3h": bdq_flow_m3h,
            "path": "bdq_under_test",
            "direction": "oneway",
            "mechanism": "pressure_opening",
            "filtered": False,
            "is_hvac_ducted": False,
        },
    ]
    if drive_from is not None and drive_to is not None:
        links.append(
            {
                "from": drive_from,
                "to": drive_to,
                "flow_rate_m3h": drive_flow_m3h,
                "path": "pressure_drive",
                "direction": "oneway",
                "mechanism": "prescribed_flow",
                "filtered": False,
                "is_hvac_ducted": False,
            }
        )
    return {"hvac_zones": [], "cross_zone_links": links}


def _bdq_flow_m3h(
    tmp_path: Path,
    name: str,
    *,
    drive_from: str | None,
    drive_to: str | None,
) -> float:
    airflow = _airflow(drive_from=drive_from, drive_to=drive_to)
    text, path_map = export_prj_with_path_map(
        _SPATIAL,
        airflow,
        hobbyist=False,
        ahs_terminal_mode="commissioned",
    )
    prj = tmp_path / f"{name}.prj"
    prj.write_text(text, encoding="utf-8")
    sim = run_contamx(str(prj), binary=_CONTAMX)
    flows = SimResults(sim).path_volumetric_flow_m3h()
    entry = next(e for e in path_map if e.get("kind") == "bdq_under_test")
    return float(flows.get(int(entry["path_nr"]), 0.0))


def test_forward_pressure_opens_commissioned_oneway_passive_path(
    tmp_path: Path,
) -> None:
    # Fan B->A makes A the upstream side, so the A->B backdraft opening sees
    # forward pressure and must pass flow instead of solving zero.
    flow = _bdq_flow_m3h(
        tmp_path, "forward", drive_from="Zone_B", drive_to="Zone_A",
    )
    assert flow > 10.0
    assert flow < 240.0


def test_reverse_pressure_keeps_commissioned_oneway_passive_path_shut(
    tmp_path: Path,
) -> None:
    flow = _bdq_flow_m3h(
        tmp_path, "reverse", drive_from="Zone_A", drive_to="Zone_B",
    )
    assert abs(flow) <= 1e-6


def test_equal_pressure_has_no_commissioned_oneway_passive_leak(
    tmp_path: Path,
) -> None:
    flow = _bdq_flow_m3h(tmp_path, "equal", drive_from=None, drive_to=None)
    assert abs(flow) <= 1e-6
