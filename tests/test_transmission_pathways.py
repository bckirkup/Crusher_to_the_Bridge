"""
test_transmission_pathways.py – Food and environmental transmission (PR #43)
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from engines.transmission_core import TransmissionCore


class TestTransmissionPathwayPools:
    def test_food_pools_initialized_for_dining_zones(self) -> None:
        profiles = {
            "test_pathogen": {
                "food_contamination": {
                    "enabled": True,
                    "food_zones": ["Galley"],
                },
            },
        }
        core = TransmissionCore(
            rng=np.random.default_rng(42),
            zone_volumes={"Galley": 50.0, "Bridge": 80.0},
            pathogen_profiles=profiles,
            zone_types={"Galley": "Dining", "Bridge": "Free"},
        )
        core.initialize_zones(["Galley", "Bridge"])
        assert "test_pathogen" in core.food_pools
        assert core.food_pools["test_pathogen"]["Galley"] == 0.0

    def test_environmental_load_initialized(self) -> None:
        profiles = {
            "legionella": {
                "environmental_contamination": {
                    "enabled": True,
                    "baseline_environmental_load": 0.01,
                },
            },
        }
        core = TransmissionCore(
            rng=np.random.default_rng(0),
            pathogen_profiles=profiles,
        )
        core.initialize_zones(["Bridge"])
        assert core.environmental_load["legionella"] == 0.01

    def test_food_pools_skipped_when_disabled(self) -> None:
        profiles = {
            "resp_virus": {
                "food_contamination": {"enabled": False},
            },
        }
        core = TransmissionCore(
            rng=np.random.default_rng(0),
            pathogen_profiles=profiles,
            zone_types={"Galley": "Dining"},
        )
        core.initialize_zones(["Galley"])
        assert core.food_pools == {}
