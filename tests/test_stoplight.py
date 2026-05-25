"""
test_stoplight.py – Unit tests for the canonical stoplight module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

from __future__ import annotations

import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from crusher_labs.stoplight import (
    STOPLIGHT_ORDER,
    stoplight_from_ct,
    stoplight_from_anomaly,
    stoplight_from_rdt,
    stoplight_from_disruption,
    meets_threshold,
)


class TestStoplightFromCt:
    def test_not_detected(self) -> None:
        assert stoplight_from_ct(25.0, detected=False) == "GREEN"

    def test_none_ct(self) -> None:
        assert stoplight_from_ct(None, detected=True) == "GREEN"

    def test_red_low_ct(self) -> None:
        assert stoplight_from_ct(25.0, detected=True) == "RED"

    def test_red_boundary(self) -> None:
        assert stoplight_from_ct(30.0, detected=True) == "RED"

    def test_amber(self) -> None:
        assert stoplight_from_ct(32.0, detected=True) == "AMBER"

    def test_amber_boundary(self) -> None:
        assert stoplight_from_ct(35.0, detected=True) == "AMBER"

    def test_green_high_ct(self) -> None:
        assert stoplight_from_ct(38.0, detected=True) == "GREEN"


class TestStoplightFromAnomaly:
    def test_green(self) -> None:
        assert stoplight_from_anomaly(0.1) == "GREEN"

    def test_amber_boundary(self) -> None:
        assert stoplight_from_anomaly(0.3) == "AMBER"

    def test_amber(self) -> None:
        assert stoplight_from_anomaly(0.5) == "AMBER"

    def test_red_boundary(self) -> None:
        assert stoplight_from_anomaly(0.7) == "RED"

    def test_red(self) -> None:
        assert stoplight_from_anomaly(1.0) == "RED"

    def test_zero(self) -> None:
        assert stoplight_from_anomaly(0.0) == "GREEN"


class TestStoplightFromRdt:
    def test_positive(self) -> None:
        assert stoplight_from_rdt(True) == "RED"

    def test_negative(self) -> None:
        assert stoplight_from_rdt(False) == "GREEN"


class TestStoplightFromDisruption:
    def test_low(self) -> None:
        assert stoplight_from_disruption(0.1) == "GREEN"

    def test_amber_boundary(self) -> None:
        assert stoplight_from_disruption(0.3) == "AMBER"

    def test_amber(self) -> None:
        assert stoplight_from_disruption(0.5) == "AMBER"

    def test_red_boundary(self) -> None:
        assert stoplight_from_disruption(0.6) == "RED"

    def test_red(self) -> None:
        assert stoplight_from_disruption(0.9) == "RED"


class TestMeetsThreshold:
    def test_green_meets_green(self) -> None:
        assert meets_threshold("GREEN", "GREEN") is True

    def test_amber_meets_green(self) -> None:
        assert meets_threshold("AMBER", "GREEN") is True

    def test_red_meets_green(self) -> None:
        assert meets_threshold("RED", "GREEN") is True

    def test_green_does_not_meet_amber(self) -> None:
        assert meets_threshold("GREEN", "AMBER") is False

    def test_amber_meets_amber(self) -> None:
        assert meets_threshold("AMBER", "AMBER") is True

    def test_red_meets_red(self) -> None:
        assert meets_threshold("RED", "RED") is True

    def test_green_does_not_meet_red(self) -> None:
        assert meets_threshold("GREEN", "RED") is False

    def test_unknown_actual(self) -> None:
        assert meets_threshold("UNKNOWN", "GREEN") is True

    def test_unknown_required(self) -> None:
        assert meets_threshold("GREEN", "UNKNOWN") is True


class TestStoplightOrder:
    def test_ordering(self) -> None:
        assert STOPLIGHT_ORDER["GREEN"] < STOPLIGHT_ORDER["AMBER"]
        assert STOPLIGHT_ORDER["AMBER"] < STOPLIGHT_ORDER["RED"]
