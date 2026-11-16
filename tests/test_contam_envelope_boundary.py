"""CONTAM-FIELD-ENVELOPE-BOUNDARY-01: outward envelope leaks are contaminant sinks."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.contamx_transport import (  # noqa: E402
    ENVELOPE_LEAK_BOUNDARY_SINK,
    ENVELOPE_LEAK_PRESSURE_ONLY,
    ContamXTransportEngine,
    is_outward_envelope_leak,
    resolve_envelope_leak_mode,
)
from tools.contam_flow_compare import (  # noqa: E402
    FATE_BOUNDARY_SINK,
    classify_contamx_path_fate,
    contamx_flow_report,
)
from tools.diag.contam_envelope_leak_enumeration import (  # noqa: E402
    summarize_envelope_leaks,
)

_LAYOUT = {
    "zones": [
        {"id": "A", "volume_m3": 100.0},
        {"id": "B", "volume_m3": 100.0},
    ]
}
_KNOWN = {"A", "B"}


def _entries() -> list[dict[str, Any]]:
    return [
        {
            "path_nr": 1, "kind": "envelope_leak", "from_zone": "A",
            "to_zone": "ambient", "crusher_transfer": False, "is_hvac_ducted": False,
        },
        {
            "path_nr": 2, "kind": "envelope_leak", "from_zone": "B",
            "to_zone": "ambient", "crusher_transfer": False, "is_hvac_ducted": False,
        },
        {
            "path_nr": 3, "kind": "adjacency", "from_zone": "A",
            "to_zone": "B", "crusher_transfer": True, "is_hvac_ducted": False,
        },
    ]


def _engine(flows: dict[int, float], mode: str | None = None) -> ContamXTransportEngine:
    entries = _entries()
    return ContamXTransportEngine(
        _LAYOUT, entries, flows, natural_decay_rate=0.0,
        path_map_entries=entries, envelope_leak_mode=mode,
    )


def _sink_paths(engine: ContamXTransportEngine) -> list[Any]:
    return [p for p in engine.airflow_paths if p.sink]


def test_default_mode_is_boundary_sink() -> None:
    assert resolve_envelope_leak_mode(None) == ENVELOPE_LEAK_BOUNDARY_SINK
    assert _engine({}).envelope_leak_mode == ENVELOPE_LEAK_BOUNDARY_SINK


def test_unknown_mode_is_rejected() -> None:
    with pytest.raises(ValueError, match="envelope_leak_mode"):
        resolve_envelope_leak_mode("leaky")


def test_outward_leak_becomes_sink_with_unchanged_magnitude() -> None:
    sinks = _sink_paths(_engine({1: 36.0, 2: -36.0, 3: 10.0}))
    assert [(p.from_zone, p.flow_rate_m3h) for p in sinks] == [("A", 36.0)]
    assert sinks[0].filtered is False


def test_inward_leak_adds_no_path() -> None:
    engine = _engine({1: -36.0, 2: -36.0, 3: 10.0})
    assert _sink_paths(engine) == []
    assert len(engine.airflow_paths) == 1


def test_pressure_only_baseline_skips_outward_leak() -> None:
    engine = _engine({1: 36.0, 2: -36.0, 3: 10.0}, ENVELOPE_LEAK_PRESSURE_ONLY)
    assert _sink_paths(engine) == []
    assert len(engine.airflow_paths) == 1


def test_inter_zone_paths_identical_across_modes() -> None:
    flows = {1: 36.0, 2: 12.0, 3: -10.0}
    on = _engine(flows)
    off = _engine(flows, ENVELOPE_LEAK_PRESSURE_ONLY)
    def real(engine: ContamXTransportEngine) -> list[tuple[str, str, float]]:
        return [
            (p.from_zone, p.to_zone, p.flow_rate_m3h)
            for p in engine.airflow_paths if not p.sink
        ]
    assert real(on) == real(off) == [("B", "A", 10.0)]


def test_sink_removes_mass_monotonically_in_outward_flow() -> None:
    start = {"A": 1000.0, "B": 0.0}
    retained = []
    for outward in (0.0, 18.0, 36.0, 72.0):
        result = _engine({1: outward}).transport_step(dict(start))
        retained.append(result["A"] + result["B"])
    assert retained[0] == pytest.approx(1000.0)
    assert retained[0] > retained[1] > retained[2] > retained[3] > 0.0


def test_pressure_only_baseline_conserves_mass() -> None:
    engine = _engine({1: 72.0, 3: 10.0}, ENVELOPE_LEAK_PRESSURE_ONLY)
    result = engine.transport_step({"A": 1000.0, "B": 0.0})
    assert result["A"] + result["B"] == pytest.approx(1000.0)


def test_helper_requires_real_source_and_ambient_destination() -> None:
    leak = _entries()[0]
    assert is_outward_envelope_leak(leak, 1.0, _KNOWN)
    assert not is_outward_envelope_leak(leak, -1.0, _KNOWN)
    assert not is_outward_envelope_leak(leak, 0.0, _KNOWN)
    assert not is_outward_envelope_leak(leak, 1.0, {"B"})
    assert not is_outward_envelope_leak(_entries()[2], 1.0, _KNOWN)


def test_compare_fate_matches_engine_filter() -> None:
    flows = {1: 36.0, 2: -36.0, 3: 10.0}
    fates = {
        e["path_nr"]: classify_contamx_path_fate(e, flows, _KNOWN)["fate"]
        for e in _entries()
    }
    assert fates == {1: FATE_BOUNDARY_SINK, 2: "skipped", 3: "kept"}
    report = contamx_flow_report(_entries(), flows, _KNOWN)
    assert report["n_boundary_sink_paths"] == 1
    assert report["boundary_sink_out_m3h"] == pytest.approx(36.0)
    assert report["n_crusher_paths"] == len(_engine(flows).airflow_paths)
    assert report["zone_degree"]["A"]["out_m3h"] == pytest.approx(46.0)
    assert "ambient" not in report["zone_degree"]


def test_compare_pressure_only_baseline_skips_leaks() -> None:
    flows = {1: 36.0, 2: -36.0, 3: 10.0}
    report = contamx_flow_report(
        _entries(), flows, _KNOWN, envelope_leak_mode=ENVELOPE_LEAK_PRESSURE_ONLY,
    )
    assert report["n_boundary_sink_paths"] == 0
    assert report["fate_counts"] == {"skipped": 2, "kept": 1}


def test_compare_without_sim_flows_keeps_leak_skipped() -> None:
    row = classify_contamx_path_fate(_entries()[0], None, _KNOWN)
    assert row["fate"] == "skipped"


def test_enumeration_splits_outward_and_inward() -> None:
    summary = summarize_envelope_leaks(_entries(), {1: 36.0, 2: -12.0, 3: 10.0}, _KNOWN)
    assert summary["envelope_leak_count"] == 2
    assert summary["outward_count"] == 1
    assert summary["outward_total_m3h"] == pytest.approx(36.0)
    assert summary["inward_total_m3h"] == pytest.approx(12.0)
    assert summary["outward"][0]["from_zone"] == "A"
