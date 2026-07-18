"""
test_contam_flow_compare.py – native vs ContamX per-path flow diagnostic
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.contam_flow_compare import (
    build_flow_compare_report,
    classify_contamx_path_fate,
    contamx_flow_report,
    native_links_report,
)


def _load_destroyer() -> tuple[dict, dict, list]:
    base = REPO_ROOT / "data" / "platforms" / "destroyer_baseline"
    spatial = json.loads((base / "spatial_layout.json").read_text(encoding="utf-8"))
    airflow = json.loads((base / "air_flow_paths.json").read_text(encoding="utf-8"))
    path_map = json.loads(
        (base / "contam" / "path_map.json").read_text(encoding="utf-8"),
    )
    return spatial, airflow, path_map


def test_native_destroyer_has_31_prescribed_links() -> None:
    spatial, airflow, _ = _load_destroyer()
    native = native_links_report(spatial, airflow)
    assert native["n_paths"] == 31
    assert native["by_path_type"]["hvac_recirculation"] == 8
    assert native["by_path_type"]["cross_zone"] == 11
    # Bridge couples via adjacency + cross-zone only (single-room AHS1)
    assert native["zone_degree"]["Bridge"]["out_edges"] >= 4
    assert native["zone_degree"]["Bridge"]["out_m3h"] > 0


def test_classify_skips_ahs_and_envelope() -> None:
    known = {"Bridge", "MedBay"}
    ahs = classify_contamx_path_fate(
        {
            "path_nr": 27, "kind": "ahs_supply", "from_zone": "ahs1(Sup)",
            "to_zone": "Bridge", "ahs_nr": 1, "crusher_transfer": False,
            "is_hvac_ducted": True,
        },
        {27: 100.0},
        known,
    )
    assert ahs["fate"] == "bridge_input"
    leak = classify_contamx_path_fate(
        {
            "path_nr": 1, "kind": "envelope_leak", "from_zone": "Bridge",
            "to_zone": "ambient", "ahs_nr": 0, "crusher_transfer": False,
            "is_hvac_ducted": False,
        },
        {1: 5.0},
        known,
    )
    assert leak["fate"] == "skipped"


def test_zero_sim_flows_isolate_bridge_like_compare_suite() -> None:
    """Reproduce compare-suite topology: only AHS2 synth survives."""
    spatial, airflow, path_map = _load_destroyer()
    known = {z["id"] for z in spatial["zones"]}
    # Zero all Contam paths; synth falls back only when terminals have flow.
    # Give AHS2 terminals non-zero flows (paths 32-37) so 6 synth edges appear.
    flows = {int(e["path_nr"]): 0.0 for e in path_map}
    for e in path_map:
        if int(e.get("ahs_nr") or 0) == 2 and e["kind"] in (
            "ahs_supply", "ahs_return", "ahs_recirc",
        ):
            flows[int(e["path_nr"])] = 200.0
    cx = contamx_flow_report(path_map, flows, known)
    assert cx["n_kept_real_paths"] == 0
    assert cx["n_synth_ahs_paths"] == 6  # 3 rooms × 2 directions
    assert cx["n_crusher_paths"] == 6
    # Bridge not in AHS2 → isolated on ContamX Crusher graph
    assert cx["zone_degree"].get("Bridge", {}).get("out_edges", 0) == 0
    assert "MedBay" in cx["zone_degree"]


def test_build_report_offline_without_sim() -> None:
    report = build_flow_compare_report(
        "destroyer_baseline",
        path_flows_m3h=None,
        inject_zones=["Bridge"],
    )
    assert report["native"]["n_paths"] == 31
    assert report["contamx"]["sim_flows_loaded"] is False
    assert report["connectivity_gap"][0]["zone"] == "Bridge"
    assert any("SIM flows not loaded" in h for h in report["hypotheses"])


def test_kept_real_path_when_sim_nonzero() -> None:
    known = {"Bridge", "MedBay"}
    row = classify_contamx_path_fate(
        {
            "path_nr": 7, "kind": "passageway", "from_zone": "Bridge",
            "to_zone": "MedBay", "ahs_nr": 0, "crusher_transfer": True,
            "is_hvac_ducted": False,
        },
        {7: 15.0},
        known,
    )
    assert row["fate"] == "kept"


def test_contamx_report_kept_links_use_flow_m3h() -> None:
    """Regression: degree loop must not KeyError on kept sim_flow_m3h rows."""
    spatial, _airflow, path_map = _load_destroyer()
    known = {z["id"] for z in spatial["zones"]}
    flows = {int(e["path_nr"]): 0.0 for e in path_map}
    # Non-zero real Bridge→MedBay passageway (path 7) + reverse-signed fan.
    flows[7] = 15.0
    flows[22] = -10.0  # Bridge→Engine_Room in path_map; negative → reverse
    cx = contamx_flow_report(path_map, flows, known)
    assert cx["n_kept_real_paths"] == 2
    assert all("flow_m3h" in link for link in cx["kept_links"])
    assert cx["zone_degree"]["Bridge"]["out_edges"] >= 1
    # Negative Flow0 on path 22: Engine_Room → Bridge
    rev = next(l for l in cx["kept_links"] if l["path_nr"] == 22)
    assert rev["from_zone"] == "Engine_Room"
    assert rev["to_zone"] == "Bridge"
    assert rev["flow_m3h"] == pytest.approx(10.0)
    # Must not raise when building the full report with SIM flows present
    report = build_flow_compare_report(
        "destroyer_baseline",
        path_flows_m3h=flows,
        inject_zones=["Bridge"],
    )
    assert report["contamx"]["n_kept_real_paths"] == 2
    assert report["connectivity_gap"][0]["contamx_out_edges"] >= 1
