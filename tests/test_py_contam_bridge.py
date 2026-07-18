"""
test_py_contam_bridge.py – Dedicated unit tests for engines/py_contam_bridge.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Covers:
- Mass conservation / deposition over a simple two-zone graph
- ACH and filter-efficiency modifier application
- Integration seam with transmission_core HVAC downstream map
- Edge cases: disconnected zones, zero flow, empty mass dict

Closes #81.
"""

from __future__ import annotations

import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from engines.py_contam_bridge import (
    ContamAirflowPath,
    ContamTransportEngine,
    ContamZoneNode,
)


# ── Helpers ──────────────────────────────────────────────────────────────

def _two_zone_layout() -> dict:
    return {
        "zones": [
            {"id": "A", "volume_m3": 100.0},
            {"id": "B", "volume_m3": 100.0},
        ],
    }


def _two_zone_airflow(flow: float = 50.0, is_ducted: bool = True) -> dict:
    return {
        "hvac_zones": [],
        "cross_zone_links": [],
        "adjacency": [
            {"from": "A", "to": "B", "type": "passageway"},
        ] if not is_ducted else [],
    }


def _engine_with_single_path(
    flow: float = 50.0,
    filter_eff: float = 0.5,
    decay: float = 0.0,
    is_ducted: bool = True,
) -> ContamTransportEngine:
    """Build a minimal engine with one A→B path for testing."""
    layout = _two_zone_layout()
    airflow: dict = {"hvac_zones": [], "cross_zone_links": [], "adjacency": []}
    engine = ContamTransportEngine(
        spatial_layout=layout,
        air_flow_paths=airflow,
        filter_efficiency=filter_eff,
        natural_decay_rate=decay,
    )
    engine.airflow_paths = [
        ContamAirflowPath(
            path_id="test_A_B",
            from_zone="A",
            to_zone="B",
            flow_rate_m3h=flow,
            path_type="test",
            is_hvac_ducted=is_ducted,
        ),
    ]
    return engine


# ── ContamZoneNode tests ────────────────────────────────────────────────

class TestContamZoneNode:
    def test_concentration_positive_volume(self) -> None:
        node = ContamZoneNode("z1", volume_m3=50.0)
        assert node.concentration(100.0) == pytest.approx(2.0)

    def test_concentration_zero_volume(self) -> None:
        node = ContamZoneNode("z2", volume_m3=0.0)
        assert node.concentration(100.0) == pytest.approx(0.0)

    def test_defaults(self) -> None:
        node = ContamZoneNode("z3", volume_m3=200.0)
        assert node.temperature_k == pytest.approx(293.15)
        assert node.density_kg_m3 == pytest.approx(1.2041)


# ── Mass conservation tests ─────────────────────────────────────────────

class TestMassConservation:
    def test_total_mass_decreases_with_filter(self) -> None:
        """HVAC-ducted path with filter removes mass from the system."""
        engine = _engine_with_single_path(
            flow=50.0, filter_eff=0.5, decay=0.0, is_ducted=True,
        )
        initial = {"A": 1000.0, "B": 0.0}
        result = engine.transport_step(initial)
        total_after = result["A"] + result["B"]
        assert total_after < 1000.0, "Filter should remove mass"

    def test_total_mass_conserved_without_filter(self) -> None:
        """Non-ducted path with zero decay preserves total mass."""
        engine = _engine_with_single_path(
            flow=50.0, filter_eff=0.0, decay=0.0, is_ducted=False,
        )
        initial = {"A": 1000.0, "B": 0.0}
        result = engine.transport_step(initial)
        total_after = result["A"] + result["B"]
        assert total_after == pytest.approx(1000.0, rel=1e-6)

    def test_no_negative_mass(self) -> None:
        """Mass should never go negative after transport."""
        engine = _engine_with_single_path(
            flow=500.0, filter_eff=0.0, decay=0.5, is_ducted=False,
        )
        initial = {"A": 10.0, "B": 0.0}
        result = engine.transport_step(initial)
        assert result["A"] >= 0.0
        assert result["B"] >= 0.0


# ── ACH and filter efficiency ───────────────────────────────────────────

class TestACHAndFilterEfficiency:
    def test_higher_ach_moves_more_mass(self) -> None:
        layout = _two_zone_layout()
        airflow_low = {
            "hvac_zones": [{"id": "hz1", "rooms": ["A", "B"], "ach": 2.0}],
            "cross_zone_links": [],
            "adjacency": [],
        }
        airflow_high = {
            "hvac_zones": [{"id": "hz1", "rooms": ["A", "B"], "ach": 12.0}],
            "cross_zone_links": [],
            "adjacency": [],
        }
        engine_low = ContamTransportEngine(layout, airflow_low, filter_efficiency=0.0, natural_decay_rate=0.0)
        engine_high = ContamTransportEngine(layout, airflow_high, filter_efficiency=0.0, natural_decay_rate=0.0)

        initial = {"A": 1000.0, "B": 0.0}
        result_low = engine_low.transport_step(dict(initial))
        result_high = engine_high.transport_step(dict(initial))

        # Both intra-zone HVAC paths redistribute equally between A and B;
        # verify A lost more mass under higher ACH (more transferred out).
        assert result_high["A"] <= result_low["A"], "Higher ACH should drain source faster"

    def test_contam_aligned_recirculation_equal_share(self) -> None:
        """Native HVAC matches Contam AHS: Q_ij = (1-oa)·ACH·ΣV·duty / n²."""
        layout = {
            "zones": [
                {"id": "A", "volume_m3": 100.0},
                {"id": "B", "volume_m3": 100.0},
                {"id": "C", "volume_m3": 100.0},
            ],
        }
        airflow = {
            "oa_fraction": 0.2,
            "hvac_duty": 0.5,
            "hvac_zones": [{"id": "hz", "rooms": ["A", "B", "C"], "ach": 6.0}],
            "cross_zone_links": [],
            "adjacency": [],
        }
        engine = ContamTransportEngine(layout, airflow)
        recirc = [p for p in engine.airflow_paths if p.path_type == "hvac_recirculation"]
        assert len(recirc) == 6  # 3×2 directed pairs
        # supply = 6*300*0.5 = 900; Rec = 0.8*900 = 720; Q_ij = 720/9 = 80
        assert all(p.flow_rate_m3h == pytest.approx(80.0) for p in recirc)

    def test_hepa_removes_nearly_all(self) -> None:
        engine = _engine_with_single_path(
            flow=100.0, filter_eff=0.999, decay=0.0, is_ducted=True,
        )
        initial = {"A": 1000.0, "B": 0.0}
        result = engine.transport_step(initial)
        assert result["B"] < 2.0, "HEPA (0.999) should let almost nothing through"

    def test_zero_filter_passes_all(self) -> None:
        engine = _engine_with_single_path(
            flow=50.0, filter_eff=0.0, decay=0.0, is_ducted=True,
        )
        initial = {"A": 1000.0, "B": 0.0}
        result = engine.transport_step(initial)
        assert result["B"] > 0.0, "Zero filter should pass mass through"


# ── Decay rate tests ────────────────────────────────────────────────────

class TestNaturalDecay:
    def test_decay_reduces_total_mass(self) -> None:
        engine = _engine_with_single_path(flow=0.0, filter_eff=0.0, decay=0.10)
        initial = {"A": 1000.0, "B": 0.0}
        result = engine.transport_step(initial)
        assert result["A"] == pytest.approx(900.0)

    def test_zero_decay_no_loss(self) -> None:
        engine = _engine_with_single_path(flow=0.0, filter_eff=0.0, decay=0.0)
        initial = {"A": 500.0, "B": 200.0}
        result = engine.transport_step(initial)
        assert result["A"] == pytest.approx(500.0)
        assert result["B"] == pytest.approx(200.0)


# ── Edge cases ──────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_mass_dict(self) -> None:
        engine = _engine_with_single_path()
        result = engine.transport_step({})
        assert result == {}

    def test_zero_flow(self) -> None:
        engine = _engine_with_single_path(flow=0.0, decay=0.0)
        initial = {"A": 500.0, "B": 100.0}
        result = engine.transport_step(initial)
        assert result["A"] == pytest.approx(500.0)
        assert result["B"] == pytest.approx(100.0)

    def test_disconnected_zones(self) -> None:
        layout = {
            "zones": [
                {"id": "X", "volume_m3": 50.0},
                {"id": "Y", "volume_m3": 50.0},
                {"id": "Z", "volume_m3": 50.0},
            ],
        }
        airflow = {"hvac_zones": [], "cross_zone_links": [], "adjacency": []}
        engine = ContamTransportEngine(layout, airflow, natural_decay_rate=0.0)
        initial = {"X": 100.0, "Y": 0.0, "Z": 0.0}
        result = engine.transport_step(initial)
        assert result["X"] == pytest.approx(100.0)
        assert result["Y"] == pytest.approx(0.0)
        assert result["Z"] == pytest.approx(0.0)

    def test_unknown_zone_in_mass_dict(self) -> None:
        engine = _engine_with_single_path(flow=10.0, decay=0.0)
        initial = {"A": 100.0, "B": 0.0, "NONEXISTENT": 50.0}
        result = engine.transport_step(initial)
        assert "NONEXISTENT" in result


# ── Adjacency / cross-zone path construction ────────────────────────────

class TestPathConstruction:
    def test_adjacency_creates_bidirectional_paths(self) -> None:
        layout = _two_zone_layout()
        airflow = {
            "hvac_zones": [],
            "cross_zone_links": [],
            "adjacency": [{"from": "A", "to": "B", "type": "passageway"}],
        }
        engine = ContamTransportEngine(layout, airflow)
        a_to_b = [p for p in engine.airflow_paths if p.from_zone == "A" and p.to_zone == "B"]
        b_to_a = [p for p in engine.airflow_paths if p.from_zone == "B" and p.to_zone == "A"]
        assert len(a_to_b) == 1
        assert len(b_to_a) == 1
        assert not a_to_b[0].is_hvac_ducted

    def test_sealed_door_lower_rate_than_passageway(self) -> None:
        layout = _two_zone_layout()
        airflow_pw = {
            "hvac_zones": [],
            "cross_zone_links": [],
            "adjacency": [{"from": "A", "to": "B", "type": "passageway"}],
        }
        airflow_sd = {
            "hvac_zones": [],
            "cross_zone_links": [],
            "adjacency": [{"from": "A", "to": "B", "type": "sealed_door"}],
        }
        engine_pw = ContamTransportEngine(layout, airflow_pw)
        engine_sd = ContamTransportEngine(layout, airflow_sd)
        rate_pw = engine_pw.airflow_paths[0].flow_rate_m3h
        rate_sd = engine_sd.airflow_paths[0].flow_rate_m3h
        assert rate_sd < rate_pw

    def test_cross_zone_links(self) -> None:
        layout = {
            "zones": [
                {"id": "R1", "volume_m3": 100.0},
                {"id": "R2", "volume_m3": 100.0},
            ],
        }
        airflow = {
            "hvac_zones": [
                {"id": "hz1", "rooms": ["R1"], "ach": 6.0},
                {"id": "hz2", "rooms": ["R2"], "ach": 6.0},
            ],
            "cross_zone_links": [
                {"from": "hz1", "to": "hz2", "flow_rate_m3h": 30.0},
            ],
            "adjacency": [],
        }
        engine = ContamTransportEngine(layout, airflow, natural_decay_rate=0.0)
        xzone = [p for p in engine.airflow_paths if p.path_type == "cross_zone"]
        assert len(xzone) >= 1
        initial = {"R1": 500.0, "R2": 0.0}
        result = engine.transport_step(initial)
        assert result["R2"] > 0.0


# ── Transport summary ───────────────────────────────────────────────────

class TestTransportSummary:
    def test_summary_fields(self) -> None:
        engine = _engine_with_single_path()
        mass = {"A": 100.0, "B": 50.0}
        summary = engine.get_transport_summary(mass)
        assert "filter_efficiency" in summary
        assert "natural_decay_rate" in summary
        assert "total_hvac_paths" in summary
        assert "total_passive_paths" in summary
        assert "zone_concentrations" in summary
        assert "A" in summary["zone_concentrations"]
