"""
test_contamx_solver.py – opt-in ContamX solver seam tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Covers the ContamX parallel-solver plumbing without requiring the (non
pip-installable, CI-absent) NIST ContamX binary:

- capability detection + fallback (find_contamx, build_transport_engine
  engine selection).
- native ``.SIM`` binary reader against a crafted fixture.
- ContamXTransportEngine airflow-field -> mass-balance behavior and
  parity of interface with the native engine.
- benchmark harness native-only mode.

An integration test that runs the real binary is included but skips
cleanly when no ContamX executable is available.
"""

from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.contamx_runner import (  # noqa: E402
    ContamXUnavailable,
    SimResults,
    find_contamx,
    run_contamx,
)
from engines.contamx_transport import (  # noqa: E402
    ContamXTransportEngine,
    _path_map_from_airflow,
)
from engines.py_contam_bridge import (  # noqa: E402
    UNSOURCED_LEGACY_FILTER_EFFICIENCY,
    ContamTransportEngine,
    build_transport_engine,
)

# ── .SIM fixture writer ──────────────────────────────────────────────────

def _write_sim(
    path: str,
    *,
    path_flows_kg_s: list[float],
    node_densities: list[float],
    node_concentrations: list[list[float]],
    nctm: int = 1,
) -> None:
    """Write a minimal but format-correct binary ``.SIM`` file.

    Layout mirrors py-contam/documentation/SIM_file_format.txt: a 17-int32
    header, three cross-reference tables, then a single output frame.
    """
    nafpt = len(path_flows_kg_s)
    nafnd = len(node_densities) + 1          # +1 ambient node
    nccnd = len(node_concentrations) + 1     # +1 ambient node
    nzone = nafnd - 1

    def i4(*vals: int) -> bytes:
        return struct.pack(f"<{len(vals)}i", *vals)

    def f4(*vals: float) -> bytes:
        return struct.pack(f"<{len(vals)}f", *vals)

    buf = bytearray()
    # 17-int32 header
    buf += i4(
        24,        # version_number
        nzone,     # nzone
        nafpt,     # npath
        nctm,      # nctm
        0,         # njct
        0,         # ndct
        3600,      # time_list
        1, 0,      # date_0, time_0
        1, 3600,   # date_1, time_1
        1, 1, 1,   # pfsave, zfsave, zcsave
        nafnd,     # nafnd
        nccnd,     # nccnd
        nafpt,     # nafpt
    )
    # airflow-node xref (typ, nr) x nafnd
    for n in range(nafnd):
        buf += i4(0, n)
    # contaminant-node xref (typ, nr) x nafnd
    for n in range(nafnd):
        buf += i4(0, n)
    # airflow-path xref (typ, nr) x nafpt  -> nr is 1-based path number
    for p in range(nafpt):
        buf += i4(0, p + 1)

    # ── one output frame ──────────────────────────────────────────────
    # ambient line: dayofy(i2) daytyp(i2) sim_time(i4) + (4+nctm) f4
    buf += struct.pack("<hh", 1, 1)
    buf += i4(3600)
    buf += f4(293.15, 101325.0, 0.0, 0.0, *([0.0] * nctm))
    # airflow paths: nr(i4) dP(f4) Flow0(f4) Flow1(f4)
    for idx, flow in enumerate(path_flows_kg_s):
        buf += i4(idx + 1)
        buf += f4(0.0, flow, flow)
    # airflow nodes (excluding ambient): nr(i4) T(f4) P(f4) D(f4)
    for idx, density in enumerate(node_densities):
        buf += i4(idx + 1)
        buf += f4(293.15, 101325.0, density)
    # contaminant nodes (excluding ambient): nr(i4) + nctm f4
    for idx, conc in enumerate(node_concentrations):
        buf += i4(idx + 1)
        buf += f4(*conc)

    with open(path, "wb") as fh:
        fh.write(bytes(buf))


# ── capability detection + fallback ──────────────────────────────────────

def test_find_contamx_none_by_default():
    assert find_contamx({}) is None
    assert find_contamx(None) is None


def test_find_contamx_config_binary_path(tmp_path):
    fake = tmp_path / "contamx"
    fake.write_text("#!/bin/sh\n")
    os.chmod(fake, 0o700)
    cfg = {"hvac": {"contamx": {"binary_path": str(fake)}}}
    assert find_contamx(cfg) == str(fake.resolve())


def test_find_contamx_env_var(tmp_path, monkeypatch):
    fake = tmp_path / "contamx3"
    fake.write_text("#!/bin/sh\n")
    os.chmod(fake, 0o700)
    monkeypatch.setenv("CONTAMX_BINARY", str(fake))
    assert find_contamx({}) == str(fake.resolve())


def test_run_contamx_raises_without_binary(tmp_path):
    prj = tmp_path / "p.prj"
    prj.write_text("ContamW 3.1\n")
    prj_path = str(prj)
    with pytest.raises(ContamXUnavailable):
        run_contamx(prj_path, binary=None, config={})


def test_build_transport_engine_contamx_falls_back_to_native():
    cfg = {
        "ship_graph": {
            "spatial_layout": "data/platforms/destroyer_baseline/spatial_layout.json",
            "air_flow_paths": "data/platforms/destroyer_baseline/air_flow_paths.json",
        },
        # η is stated because a config no longer inherits one; this test is
        # about engine selection, so it states the legacy non-era value.
        "hvac": {
            "transport_engine": "contamx",
            "filter_efficiency": UNSOURCED_LEGACY_FILTER_EFFICIENCY,
        },
    }
    engine = build_transport_engine(str(REPO_ROOT), cfg)
    # No binary in CI -> falls back to the native engine (not the subclass).
    assert isinstance(engine, ContamTransportEngine)
    assert not isinstance(engine, ContamXTransportEngine)


def test_build_transport_engine_native_default_unchanged():
    cfg = {
        "ship_graph": {
            "spatial_layout": "data/platforms/destroyer_baseline/spatial_layout.json",
            "air_flow_paths": "data/platforms/destroyer_baseline/air_flow_paths.json",
        },
        "hvac": {"filter_efficiency": UNSOURCED_LEGACY_FILTER_EFFICIENCY},
    }
    engine = build_transport_engine(str(REPO_ROOT), cfg)
    assert type(engine) is ContamTransportEngine


# ── .SIM reader ──────────────────────────────────────────────────────────

def test_sim_reader_decodes_header_and_flows(tmp_path):
    sim = tmp_path / "model.sim"
    _write_sim(
        str(sim),
        path_flows_kg_s=[0.12, -0.05],
        node_densities=[1.2, 1.2],
        node_concentrations=[[0.5], [0.25]],
    )
    results = SimResults(str(sim))
    assert results.header["version_number"] == 24
    assert results.header["nafpt"] == 2
    frame = results.steady_state_frame()
    assert frame.path_flow_kg_s == pytest.approx([0.12, -0.05])


def test_sim_reader_volumetric_flow_conversion(tmp_path):
    sim = tmp_path / "model.sim"
    # Flow0 = 1.2041 kg/s at density 1.2041 kg/m^3 -> 1 m^3/s -> 3600 m^3/h
    _write_sim(
        str(sim),
        path_flows_kg_s=[1.2041],
        node_densities=[1.2041],
        node_concentrations=[[0.0]],
    )
    results = SimResults(str(sim))
    flows = results.path_volumetric_flow_m3h()
    assert flows[1] == pytest.approx(3600.0, rel=1e-4)


def test_sim_reader_uses_embedded_path_nr_not_xref():
    """Regression: ContamX destroyer.sim fans must map by record nr.

    Broken xref→index mapping previously assigned AHS 0.1 kg/s onto fan
    path numbers (all kept links ≈300 m³/h). Embedded nr recovers design
    fan_cvf rates (~16.7 / 13.3 / 10 m³/h).
    """
    sim_path = REPO_ROOT / "tests" / "fixtures" / "contam" / "destroyer_baseline.sim"
    assert sim_path.is_file()
    results = SimResults(str(sim_path))
    frame = results.steady_state_frame()
    assert frame.sim_time_s == 3600
    assert float(frame.node_density[frame.node_density > 0].mean()) == pytest.approx(
        1.2, rel=0.01,
    )
    flows = results.path_volumetric_flow_m3h()
    assert flows[14] == pytest.approx(16.67, rel=0.02)   # Fan_25
    assert flows[16] == pytest.approx(13.33, rel=0.02)   # Fan_26
    assert flows[22] == pytest.approx(10.0, rel=0.02)    # Fan_27
    # Must not collapse to the old identical 300 m³/h fingerprint
    assert flows[14] != pytest.approx(300.0, rel=0.05)
    assert flows[12] != pytest.approx(flows[14], rel=0.01)


def test_sim_reader_rejects_truncated_file(tmp_path):
    bad = tmp_path / "bad.sim"
    bad.write_bytes(struct.pack("<3i", 24, 1, 1))  # too short for header
    bad_path = str(bad)
    with pytest.raises(ValueError):
        SimResults(bad_path)


# ── ContamXTransportEngine airflow-field behavior ────────────────────────

_TWO_ZONE_LAYOUT = {
    "zones": [
        {"id": "A", "volume_m3": 100.0},
        {"id": "B", "volume_m3": 100.0},
    ]
}


def test_contamx_engine_positive_flow_moves_mass_forward():
    engine = ContamXTransportEngine.from_flow_field(
        _TWO_ZONE_LAYOUT,
        path_map=[("A", "B", False)],
        path_flows_m3h={1: 3600.0},
        natural_decay_rate=0.0,
    )
    result = engine.transport_step({"A": 1000.0, "B": 0.0})
    assert result["B"] > 0.0
    assert result["A"] < 1000.0


def test_contamx_engine_negative_flow_reverses_direction():
    engine = ContamXTransportEngine.from_flow_field(
        _TWO_ZONE_LAYOUT,
        path_map=[("A", "B", False)],
        path_flows_m3h={1: -3600.0},
        natural_decay_rate=0.0,
    )
    result = engine.transport_step({"A": 0.0, "B": 1000.0})
    assert result["A"] > 0.0
    assert result["B"] < 1000.0


def test_contamx_engine_zero_flow_no_paths():
    engine = ContamXTransportEngine.from_flow_field(
        _TWO_ZONE_LAYOUT,
        path_map=[("A", "B", False)],
        path_flows_m3h={1: 0.0},
    )
    assert engine.airflow_paths == []


def test_contamx_engine_matches_native_interface():
    engine = ContamXTransportEngine.from_flow_field(
        _TWO_ZONE_LAYOUT,
        path_map=[("A", "B", False)],
        path_flows_m3h={1: 100.0},
    )
    summary = engine.get_transport_summary({"A": 500.0, "B": 0.0})
    assert "zone_concentrations" in summary
    assert set(summary["zone_concentrations"]) == {"A", "B"}


def test_path_map_from_airflow_includes_adjacency_and_more():
    spatial = {
        "platform": "t",
        "zones": [
            {"id": "A", "volume_m3": 50, "deck": "main", "display": {"x": 0, "y": 0}},
            {"id": "B", "volume_m3": 50, "deck": "main", "display": {"x": 1, "y": 0}},
            {"id": "C", "volume_m3": 50, "deck": "main", "display": {"x": 2, "y": 0}},
        ],
    }
    airflow = {
        "adjacency": [
            {"from": "A", "to": "B"},
            {"from": "B", "to": "C"},
        ],
        "hvac_zones": [{"id": "hz", "rooms": ["A", "B", "C"], "ach": 6.0}],
        "cross_zone_links": [],
    }
    path_map = _path_map_from_airflow(spatial, airflow)
    # ContamW 3.4 full order: envelope leaks, adjacency, then AHS bookkeeping
    assert ("A", "ambient") in {p[:2] for p in path_map}
    assert ("A", "B") in {p[:2] for p in path_map}
    assert ("B", "C") in {p[:2] for p in path_map}
    assert path_map[0][:2] == ("A", "ambient")  # envelope leaks first
    assert len(path_map) > 5  # 3 leaks + 2 adjacency + AHS paths


# ── benchmark harness (native-only path) ─────────────────────────────────

def test_benchmark_native_only_runs(capsys):
    from tools.contam_benchmark import main

    main([
        "--platform", "data/platforms/destroyer_baseline",
        "--epochs", "3",
        "--inject", "Bridge:1e6",
    ])
    out = capsys.readouterr().out
    assert "ContamX unavailable" in out
    assert "copies/m^3" in out


# ── live-binary integration (skips when absent) ──────────────────────────

@pytest.mark.skipif(
    find_contamx({}) is None,
    reason="ContamX binary not available in this environment",
)
def test_contamx_live_run_smoke():
    from engines.contamx_transport import build_contamx_engine

    cfg = {
        "ship_graph": {
            "spatial_layout": "data/platforms/destroyer_baseline/spatial_layout.json",
            "air_flow_paths": "data/platforms/destroyer_baseline/air_flow_paths.json",
        },
        # η is stated because a config no longer inherits one; this test is
        # about engine selection, so it states the legacy non-era value.
        "hvac": {
            "transport_engine": "contamx",
            "filter_efficiency": UNSOURCED_LEGACY_FILTER_EFFICIENCY,
        },
    }
    engine = build_contamx_engine(str(REPO_ROOT), cfg)
    assert isinstance(engine, ContamXTransportEngine)
    assert engine.zone_nodes
