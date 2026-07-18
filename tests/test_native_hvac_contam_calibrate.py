"""Native HVAC star topology calibrated toward ContamX / PRJ AHS rates."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.contamx_ahs_bridge import (  # noqa: E402
    ahs_plenum_id,
    synthesize_ahs_recirculation_paths,
)
from engines.contamx_runner import SimResults  # noqa: E402
from engines.py_contam_bridge import (  # noqa: E402
    PATH_TYPE_HVAC_RETURN,
    PATH_TYPE_HVAC_SUPPLY,
    ContamTransportEngine,
)


def test_destroyer_native_star_matches_contamx_ahs_synth() -> None:
    """Destroyer Contam twin: native star HVAC ≈ ContamX AHS star synth."""
    spatial = json.loads(
        (REPO_ROOT / "data/platforms/destroyer_baseline/spatial_layout.json").read_text()
    )
    airflow = json.loads(
        (REPO_ROOT / "data/platforms/destroyer_baseline/air_flow_paths.json").read_text()
    )
    assert airflow.get("oa_fraction") == pytest.approx(0.2)
    assert airflow.get("hvac_duty") == pytest.approx(0.5)

    native = ContamTransportEngine(spatial, airflow)
    native_ret = {
        p.from_zone: p.flow_rate_m3h
        for p in native.airflow_paths
        if p.path_type == PATH_TYPE_HVAC_RETURN
    }
    native_sup = {
        p.to_zone: p.flow_rate_m3h
        for p in native.airflow_paths
        if p.path_type == PATH_TYPE_HVAC_SUPPLY
    }
    # Volume-proportional star: zone_lower ACH=10 duty=0.5
    # Engine_Room V=200 → ret 1000 / sup 800; Berthing V=150 → ret 750 / sup 600
    assert native_ret["Engine_Room"] == pytest.approx(1000.0)
    assert native_sup["Engine_Room"] == pytest.approx(800.0)
    assert native_ret["Berthing"] == pytest.approx(750.0)
    assert native_sup["Berthing"] == pytest.approx(600.0)
    # zone_main MedBay V=45 ACH=8 duty=0.5 → ret 180 / sup 144
    assert native_ret["MedBay"] == pytest.approx(180.0)
    assert native_sup["MedBay"] == pytest.approx(144.0)
    # Single-room AHS included for OA+filter
    assert native_ret["Bridge"] == pytest.approx(240.0)
    assert native_sup["Bridge"] == pytest.approx(192.0)

    path_map = json.loads(
        (REPO_ROOT / "data/platforms/destroyer_baseline/contam/path_map.json").read_text()
    )
    sim = SimResults(str(REPO_ROOT / "tests/fixtures/contam/destroyer_baseline.sim"))
    flows = sim.path_volumetric_flow_m3h()
    zones = {z["id"] for z in spatial["zones"]}
    synth = synthesize_ahs_recirculation_paths(
        path_map, flows, zones, oa_fraction=0.2,
    )
    synth_ret = {
        p.from_zone: p.flow_rate_m3h
        for p in synth
        if p.path_type == PATH_TYPE_HVAC_RETURN
    }
    synth_sup = {
        p.to_zone: p.flow_rate_m3h
        for p in synth
        if p.path_type == PATH_TYPE_HVAC_SUPPLY
    }

    # ContamX AHS terminals are equal-share (not volume-weighted). Compare
    # topology + OA scaling: each multi-room AHS has ret+sup per room.
    assert set(synth_ret) == set(synth_sup)
    for room in synth_ret:
        assert room in native_ret
        # SIM duty ≈ 0.502 of design → supply ≈ 0.8 × return
        assert synth_sup[room] == pytest.approx(0.8 * synth_ret[room], rel=0.02)
        assert any(
            p.to_zone == ahs_plenum_id(n) or p.from_zone == ahs_plenum_id(n)
            for p in synth
            for n in (1, 2, 3)
        )
