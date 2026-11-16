"""Unit tests for the make-up ``ambient_openings`` witness summary helpers."""

from __future__ import annotations

from typing import Any

import pytest

from tools.diag import ambient_makeup_witness as witness


def _path(nr: int, kind: str, flow: float, dp: float) -> dict[str, Any]:
    return {"path_nr": nr, "kind": kind, "from_zone": "A", "flow_m3h": flow, "dp_pa": dp}


def test_opening_summary_splits_inward_from_outward() -> None:
    paths = [
        _path(1, "ambient_opening", -40.0, -9.0),
        _path(2, "ambient_opening", 10.0, 2.0),
        _path(3, "envelope_leak", -500.0, -1.0e5),
    ]
    summary = witness.opening_summary(paths)
    assert [leg["path_nr"] for leg in summary["legs"]] == [1, 2]
    assert summary["inward_m3h"] == pytest.approx(40.0)
    assert summary["outward_m3h"] == pytest.approx(10.0)
    assert summary["max_abs_dp_pa"] == pytest.approx(9.0)


def test_opening_summary_without_openings_is_empty() -> None:
    summary = witness.opening_summary([_path(3, "envelope_leak", -5.0, -1.0)])
    assert summary["legs"] == []
    assert summary["inward_m3h"] == pytest.approx(0.0)
    assert summary["outward_m3h"] == pytest.approx(0.0)
    assert summary["max_abs_dp_pa"] is None


def _lane(max_dp: float, opening_in: float) -> dict[str, Any]:
    return {
        "path_count": 10, "max_abs_dp_pa": max_dp,
        "interior_flowing_max_abs_dp_pa": 1.0, "exhaust_sink_out_m3h": 100.0,
        "envelope_net_inward_m3h": 100.0 - opening_in, "balance_residual_m3h": 0.0,
        "k_field_over_native_median": 1.0,
        "opening": {"inward_m3h": opening_in, "outward_m3h": 0.0, "max_abs_dp_pa": None},
        "whole_hull_material_time_h": {"A/pulse_t0/design": max_dp / 1.0e6},
    }


def _report(max_dp: float, opening_in: float) -> dict[str, Any]:
    flow = {
        "n_path_map": 10, "native_n_paths": 8, "n_kept_real_paths": 4,
        "n_synth_ahs_paths": 2, "n_ambient_opening_paths": 0,
        "ambient_opening_inward_m3h": opening_in, "ambient_opening_sink_out_m3h": 0,
        "native_ambient_exchange": [],
    }
    lanes = {lane: _lane(max_dp, opening_in) for lane in witness.LANES}
    return {"hulls": {"hull_x": {"lanes": lanes, "flow_compare": flow}}}


def test_compare_markdown_reports_each_lane_before_and_after() -> None:
    text = witness.compare_markdown(_report(5.0e5, 0.0), _report(12.0, 99.0))
    rows = [ln for ln in text.splitlines() if ln.startswith("| hull_x | ")]
    lane_rows = [ln for ln in rows if "5e+05 -> 12" in ln]
    assert len(lane_rows) == len(witness.LANES)
    assert all("| 99 |" in ln for ln in lane_rows)
    assert "| hull_x | A/pulse_t0/design | 0.5 | 1.2e-05 |" in text
