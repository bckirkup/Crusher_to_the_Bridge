"""Graded-sensitivity tests for hvac.outdoor_air_fraction_override.

The override replaces every HVAC zone's declared ``oa_fraction`` at
operator-build time; absent, the platform's own values are used. These tests
assert invariants and monotone sensitivity, not golden numbers: exact matrix
equality where identity is required, strict ordering where the knob is swept.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pytest

from engines.py_contam_bridge import (
    PATH_TYPE_HVAC_SUPPLY,
    ContamTransportEngine,
    parse_outdoor_air_fraction_override,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLATFORM = os.path.join(REPO_ROOT, "data", "platforms", "mega_cruise_5000")

SOURCE_CABIN = "PC_D6_P_F"
# Peer corridor on the same deck AHU star (AHU_Pax_Deck_D6).
PEER_CABIN = "PC_D6_S_F"
# Passive adjacency pair (stairwell), untouched by the override.
ADJACENCY_FROM = "MainDining_L"
ADJACENCY_TO = "MainDining_U"


def _load(name: str) -> dict:
    with open(os.path.join(PLATFORM, name), encoding="utf-8") as handle:
        return json.load(handle)


def _engine(override: float | None = None) -> ContamTransportEngine:
    return ContamTransportEngine(
        spatial_layout=_load("spatial_layout.json"),
        air_flow_paths=_load("air_flow_paths.json"),
        filter_efficiency=0.5,
        natural_decay_rate=0.0,
        outdoor_air_fraction_override=override,
    )


def _operator(engine: ContamTransportEngine) -> np.ndarray:
    return engine._build_decay_free_operator()


def _arrived_mass(engine: ContamTransportEngine, source: str, target: str) -> float:
    result = engine.transport_step({source: 1.0}, natural_decay_rate=0.0)
    return float(result.get(target, 0.0))


def test_absent_override_preserves_operator() -> None:
    """Key absent must be bit-identical to today's construction."""
    default_engine = ContamTransportEngine(
        spatial_layout=_load("spatial_layout.json"),
        air_flow_paths=_load("air_flow_paths.json"),
        filter_efficiency=0.5,
        natural_decay_rate=0.0,
    )
    assert default_engine.outdoor_air_fraction_override is None
    assert np.array_equal(
        _operator(default_engine), _operator(_engine(None)),
    )


def test_override_equal_to_declared_value_is_identity() -> None:
    """Override 0.2 equals the platform's declared oa_fraction: identical."""
    assert np.array_equal(
        _operator(_engine(None)), _operator(_engine(0.2)),
    )


def test_recirculated_mass_decreases_monotonically() -> None:
    """Peer-corridor arrival on the same AHU star falls strictly with oa."""
    arrivals = [
        _arrived_mass(_engine(oa), SOURCE_CABIN, PEER_CABIN)
        for oa in (0.0, 0.2, 0.5, 0.8)
    ]
    assert all(a > 0.0 for a in arrivals)
    assert all(
        earlier > later
        for earlier, later in zip(arrivals, arrivals[1:])
    )


def test_full_outdoor_air_removes_star_recirculation() -> None:
    """oa 1.0 removes every supply path; passive paths still transport.

    With fully outdoor air no room flow is recirculated, so the plenum→room
    supply legs are never created — no recirculated mass can reach a peer.
    Return legs still drain rooms to the (exhausted) plenum, and declared
    passive adjacency is untouched.
    """
    engine = _engine(1.0)
    assert not any(
        p.path_type == PATH_TYPE_HVAC_SUPPLY for p in engine.airflow_paths
    )
    assert _arrived_mass(engine, SOURCE_CABIN, PEER_CABIN) < (
        _arrived_mass(_engine(0.0), SOURCE_CABIN, PEER_CABIN)
    )
    assert _arrived_mass(engine, ADJACENCY_FROM, ADJACENCY_TO) > 0.0


@pytest.mark.parametrize("bad", [-0.1, 1.1, float("nan"), "0.3"])
def test_invalid_values_raise(bad: object) -> None:
    with pytest.raises(ValueError, match="hvac.outdoor_air_fraction_override"):
        parse_outdoor_air_fraction_override(
            {"outdoor_air_fraction_override": bad},
        )
