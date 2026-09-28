"""FLU-RHYTHM-01 probe + readout unit coverage.

The cell spec must carry the FLU-DELIVERY-01 conditioning verbatim
(isolated arm, explicit passenger pair at epoch 0, declared SOP-017) and
the arm flag must land as exactly ``config_overrides.rhythm.enabled``;
the readout must pool slots honestly and pair seeds on the run stem.
"""

from __future__ import annotations

import math

import pytest

from tools.flu_rhythm_ab_probe import flu_cell_spec
from tools.flu_rhythm_ab_readout import _confined_block, _paired_table
from tools.noro_diag.rhythm_ab_probe import _inject_arm


def test_flu_cell_spec_carries_delivery_conditioning() -> None:
    spec = flu_cell_spec(
        seed=8105, platform="expedition_cruise_450", epochs=24,
    )
    overrides = spec["pathogen_overrides"]
    assert sorted(overrides["remove"]) == ["norwalk_gi", "sars_cov2_resp"]
    assert overrides["influenza_a"] == {"initial_infected": None}
    assert spec["config_overrides"]["initiation"] == {
        "explicit_seeds": [{
            "pathogen": "influenza_a", "count": 2,
            "role": "passenger", "epoch": 0,
        }],
    }
    assert spec["config_overrides"]["scenario_schedule"] == {
        "protocols": [{
            "protocol_id": "SOP-017", "start_day": 1, "end_day": None,
        }],
    }
    assert spec["run"]["random_seed"] == 8105
    assert spec["run"]["num_epochs"] == 24


def test_flu_cell_spec_organic_drops_scenario_schedule() -> None:
    spec = flu_cell_spec(
        seed=8105, platform="expedition_cruise_450", epochs=24,
        confinement="organic",
    )
    assert "scenario_schedule" not in spec["config_overrides"]


def test_arm_injection_lands_on_top_of_conditioning() -> None:
    spec = flu_cell_spec(
        seed=8105, platform="expedition_cruise_450", epochs=24,
    )
    _inject_arm(spec, "on")
    assert spec["config_overrides"]["rhythm"] == {"enabled": True}
    _inject_arm(spec, "off")
    assert spec["config_overrides"]["rhythm"] == {"enabled": False}
    assert spec["config_overrides"]["scenario_schedule"]["protocols"] == [
        {"protocol_id": "SOP-017", "start_day": 1, "end_day": None},
    ]


class _P:
    def __init__(self, name: str) -> None:
        self.stem = name


def _cell(
    slots: int,
    secondaries: int,
    doses: list[float] | None = None,
) -> dict:
    cell = {"confined_slots": slots, "confined_secondaries": secondaries}
    if doses is not None:
        cell["slot_rows"] = [{"delivered_p_dose": d} for d in doses]
    return cell


def test_confined_block_pools_slots_and_flags_band() -> None:
    # The band is derived, not fixed: E[1−exp(−k·D)] over pooled slot doses
    # at the declared k sourced interval (confined_attack_floor_spec.md).
    runs = [
        (_P("a"), {}, {"confined": _cell(30, 2, [200.0] * 30)}),
        (_P("b"), {}, {"confined": _cell(20, 1, [200.0] * 20)}),
    ]
    block = _confined_block(runs)
    assert block["n_slots"] == 50
    assert block["confined_secondaries"] == 3
    assert block["attack"] == pytest.approx(0.06)
    assert block["floor_band"] == pytest.approx(
        [1 - math.exp(-2e-4 * 200.0), 1 - math.exp(-1e-3 * 200.0)],
    )
    assert block["expected_sar"] == pytest.approx(
        1 - math.exp(-6e-4 * 200.0),
    )
    # the internal-consistency gate: declared k lands inside by construction
    assert (
        block["floor_band"][0]
        <= block["expected_sar"]
        <= block["floor_band"][1]
    )
    assert block["in_floor_band"] is True


def test_confined_block_band_comparison_is_n_aware() -> None:
    # FLU-DELIVERY-01's n=34 draw: the point estimate overshoots the band's
    # upper edge but its Wilson interval still overlaps it — consistent.
    runs = [(_P("a"), {}, {"confined": _cell(34, 7, [200.0] * 34)})]
    block = _confined_block(runs)
    assert block["attack"] == pytest.approx(7 / 34)
    assert block["attack"] > block["floor_band"][1]
    assert block["in_floor_band"] is True


def test_confined_block_flags_out_of_band() -> None:
    runs = [(_P("a"), {}, {"confined": _cell(40, 20, [1.0] * 40)})]
    block = _confined_block(runs)
    assert block["attack"] == pytest.approx(0.5)
    assert block["in_floor_band"] is False


def test_confined_block_band_is_none_without_slot_doses() -> None:
    runs = [(_P("a"), {}, {"confined": _cell(40, 20)})]
    block = _confined_block(runs)
    assert block["floor_band"] is None
    assert block["in_floor_band"] is None


def test_paired_table_joins_on_run_stem() -> None:
    off = [
        (_P("s8105"), {}, {"confined": _cell(10, 2)}),
        (_P("s8106"), {}, {"confined": _cell(10, 1)}),
        (_P("s8107"), {}, {"confined": _cell(0, 0)}),
    ]
    on = [
        (_P("s8105"), {}, {"confined": _cell(10, 3)}),
        (_P("s8106"), {}, {"confined": _cell(10, 1)}),
        (_P("s8999"), {}, {"confined": _cell(10, 9)}),
    ]
    paired = _paired_table(off, on)
    assert paired["paired_seeds"] == 2
    assert paired["attack_delta_median"] == pytest.approx(0.05)
