"""FLU-RHYTHM-01 probe + readout unit coverage.

The cell spec must carry the FLU-DELIVERY-01 conditioning verbatim
(isolated arm, explicit passenger pair at epoch 0, declared SOP-017) and
the arm flag must land as exactly ``config_overrides.rhythm.enabled``;
the readout must pool slots honestly and pair seeds on the run stem.
"""

from __future__ import annotations

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


def _cell(slots: int, secondaries: int) -> dict:
    return {"confined_slots": slots, "confined_secondaries": secondaries}


def test_confined_block_pools_slots_and_flags_band() -> None:
    runs = [
        (_P("a"), {}, {"confined": _cell(30, 6)}),
        (_P("b"), {}, {"confined": _cell(20, 4)}),
    ]
    block = _confined_block(runs)
    assert block["n_slots"] == 50
    assert block["confined_secondaries"] == 10
    assert block["attack"] == pytest.approx(0.2)
    assert block["in_floor_band"] is True


def test_confined_block_flags_out_of_band() -> None:
    runs = [(_P("a"), {}, {"confined": _cell(40, 2)})]
    block = _confined_block(runs)
    assert block["attack"] == pytest.approx(0.05)
    assert block["in_floor_band"] is False


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
