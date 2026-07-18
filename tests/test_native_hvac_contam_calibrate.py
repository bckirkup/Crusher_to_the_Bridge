"""Native HVAC recirculation calibrated toward ContamX / PRJ AHS rates."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.contamx_ahs_bridge import synthesize_ahs_recirculation_paths  # noqa: E402
from engines.contamx_runner import SimResults  # noqa: E402
from engines.py_contam_bridge import ContamTransportEngine  # noqa: E402


def test_destroyer_native_recirc_matches_contamx_ahs_synth() -> None:
    """Destroyer Contam twin: native HVAC ≈ ContamX AHS synth (OA + duty)."""
    spatial = json.loads(
        (REPO_ROOT / "data/platforms/destroyer_baseline/spatial_layout.json").read_text()
    )
    airflow = json.loads(
        (REPO_ROOT / "data/platforms/destroyer_baseline/air_flow_paths.json").read_text()
    )
    assert airflow.get("oa_fraction") == pytest.approx(0.2)
    assert airflow.get("hvac_duty") == pytest.approx(0.5)

    native = ContamTransportEngine(spatial, airflow)
    native_recirc = {
        (p.from_zone, p.to_zone): p.flow_rate_m3h
        for p in native.airflow_paths
        if p.path_type == "hvac_recirculation"
    }
    # Contam-aligned: zone_lower 0.8*0.5*3500/4 = 350; zone_main 0.8*0.5*1800/9 = 80
    assert native_recirc[("Engine_Room", "Berthing")] == pytest.approx(350.0)
    assert native_recirc[("Berthing", "Engine_Room")] == pytest.approx(350.0)
    assert native_recirc[("MedBay", "Mess_Hall")] == pytest.approx(80.0)

    path_map = json.loads(
        (REPO_ROOT / "data/platforms/destroyer_baseline/contam/path_map.json").read_text()
    )
    sim = SimResults(str(REPO_ROOT / "tests/fixtures/contam/destroyer_baseline.sim"))
    flows = sim.path_volumetric_flow_m3h()
    zones = {z["id"] for z in spatial["zones"]}
    synth = synthesize_ahs_recirculation_paths(
        path_map, flows, zones, oa_fraction=0.2,
    )
    synth_recirc = {(p.from_zone, p.to_zone): p.flow_rate_m3h for p in synth}

    for pair, native_q in native_recirc.items():
        assert pair in synth_recirc, f"missing ContamX synth for {pair}"
        # SIM duty ≈ 0.502 of design → allow small relative slack
        assert native_q == pytest.approx(synth_recirc[pair], rel=0.02)
