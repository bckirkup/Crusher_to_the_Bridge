"""Shared conditioned-array readout machinery: quantiles, splitting,
the audit loop, the anchor legs, and the printed row."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from tools import covid_screen_readout_common as mod


@dataclass
class _Cell:
    theta: float
    arm_id: str
    seed: int


def _payload(theta=2.37e11, arm="A0", seed=1, rec=100, before=20, inf=800.0):
    return {
        "cell": {"theta": theta, "arm_id": arm, "seed": seed},
        "observables": {
            "recorded_onsets": rec,
            "onsets_before_split_day": before,
        },
        "infections_total": inf,
    }


def test_quantile_and_band_stats():
    assert mod.quantile([], 0.5) is None
    assert mod.quantile([5.0], 0.5) == pytest.approx(5.0)
    # Nearest order statistic: round(0.5 * 1) = 0 under round-half-even.
    assert mod.quantile([10.0, 20.0], 0.5) == pytest.approx(10.0)
    stats = mod.band_stats([1.0, 2.0, 3.0])
    assert stats["median"] == pytest.approx(2.0)
    assert stats["q05"] <= stats["median"] <= stats["q95"]


def test_takeoff_split_partitions_on_recorded_onsets():
    payloads = [
        _payload(seed=1, rec=100, before=10, inf=500.0),
        _payload(seed=2, rec=0, before=0, inf=0.0),
        _payload(seed=3, rec=50, before=25, inf=900.0),
    ]
    takeoff, vec = mod.takeoff_split(payloads)
    assert len(takeoff) == 2
    assert vec["t_inf"] == [500.0, 900.0]
    assert vec["t_share"] == [pytest.approx(0.1), pytest.approx(0.5)]
    assert vec["rec"] == [100.0, 0.0, 50.0]
    assert len(vec["shares"]) == 2  # zero-onset cells divide cleanly out


def test_anchor_legs_window_and_minimum_mass():
    legs = mod.anchor_legs(5, [800.0] * 5, [0.17] * 5)
    assert legs["both_legs"] is True
    legs = mod.anchor_legs(4, [800.0] * 4, [0.17] * 4)
    assert legs["both_legs"] is False  # < 5 takeoff seeds
    legs = mod.anchor_legs(5, [3000.0] * 5, [0.17] * 5)
    assert legs["truth_leg_in_band"] is False
    assert legs["timing_leg_in_band"] is True
    legs = mod.anchor_legs(5, [800.0] * 5, [0.6] * 5)
    assert legs["timing_leg_in_band"] is False
    legs = mod.anchor_legs(5, [], [])
    assert legs["both_legs"] is False


def test_audit_all_buckets_and_flags_off_lattice_cells():
    cells = [_Cell(theta=2.37e11, arm_id="A0", seed=1)]
    payloads = {
        "good.json": _payload(seed=1),
        "bad.json": _payload(seed=1, inf=1.0),
        "off.json": _payload(seed=999),
        "unknown_arm.json": _payload(arm="ZZZ", seed=1),
    }

    def audit(payload, declared, theta):
        return [] if payload["infections_total"] == 800.0 else ["bad inf"]

    failures, rows = mod.audit_all(
        payloads, cells, {"A0": {}}, audit,
    )
    assert failures["bad.json"] == ["bad inf"]
    assert "not in the declared lattice" in failures["off.json"][0]
    # arm_id is part of the lattice key, so an undeclared arm reads
    # off-lattice before the unknown-arm branch can fire.
    assert "not in the declared lattice" in failures["unknown_arm.json"][0]
    assert rows == {(2.37e11, "A0"): [
        payloads["good.json"], payloads["bad.json"],
    ]}


def test_default_row_line_marks_the_trigger_flags():
    stats = {
        "takeoff_n": 9, "n": 10,
        "takeoff_infections_total": {
            "median": 800.0, "q05": 700.0, "q95": 900.0,
        },
        "takeoff_before_share": {
            "median": 0.17, "q05": 0.1, "q95": 0.2,
        },
        "takeoff_recorded_onsets": {
            "median": 200.0, "q05": 150.0, "q95": 250.0,
        },
        "truth_leg_in_band": True,
        "timing_leg_in_band": True,
        "fizzle_majority": False,
        "during_dominant": True,
        "row_extra": "during med 3 kink 0.4",
    }
    line = mod._default_row_line("row", stats)
    assert "TRUTH-IN-BAND" in line
    assert "TIMING-IN-BAND" in line
    assert "DURING-DOMINANT" in line
    assert "FIZZLE-MAJORITY" not in line
    assert "during med 3 kink 0.4" in line


def test_resolve_design_arg_confines_to_repo(tmp_path):
    design = tmp_path / "d.json"
    design.write_text("{}")
    assert mod.resolve_design_arg(
        ["--design", str(design)], str(tmp_path),
    ) == str(design)
    with pytest.raises(ValueError):
        mod.resolve_design_arg(["--design", "/etc/passwd"], str(tmp_path))
