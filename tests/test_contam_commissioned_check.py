"""Group-aware declared flows for the commissioned hull→solver check."""

from __future__ import annotations

import pytest

from tools import contam_commissioned_check as check


def _spatial() -> dict:
    return {"zones": [
        {"id": "Room_A", "volume_m3": 100.0},
        {"id": "Room_B", "volume_m3": 50.0},
    ]}


def _airflow() -> dict:
    return {
        "hvac_duty": 0.5,
        "hvac_zones": [
            {"id": "HVAC_Empty", "ach": 99.0, "rooms": ["Missing"]},
            {"id": "HVAC_A", "ach": 2.0, "rooms": ["Room_A"]},
            {
                "id": "HVAC_AB", "ach": 4.0, "hvac_duty": 0.5,
                "rooms": ["Room_A", "Room_B"],
            },
            {
                "id": "HVAC_Exhaust", "ach": 3.0, "hvac_duty": 0.0,
                "rooms": ["Room_B"],
            },
        ],
    }


def _terminal_entries() -> list[dict]:
    return [
        {
            "path_nr": 1, "kind": "ahs_supply", "from_zone": "ahs1(Sup)",
            "to_zone": "Room_A", "ahs_nr": 1, "declared_flow_m3h": 100.0,
        },
        {
            "path_nr": 2, "kind": "ahs_return", "from_zone": "Room_A",
            "to_zone": "ahs1(Ret)", "ahs_nr": 1, "declared_flow_m3h": 100.0,
        },
        {
            "path_nr": 3, "kind": "ahs_supply", "from_zone": "ahs2(Sup)",
            "to_zone": "Room_A", "ahs_nr": 2, "declared_flow_m3h": 200.0,
        },
        {
            "path_nr": 4, "kind": "ahs_return", "from_zone": "Room_A",
            "to_zone": "ahs2(Ret)", "ahs_nr": 2, "declared_flow_m3h": 200.0,
        },
    ]


def test_declared_flows_are_keyed_by_hvac_group() -> None:
    declared = check.declared_terminal_flows(_spatial(), _airflow())

    a1 = declared[(1, "Room_A")]
    assert a1["supply"] == pytest.approx(100.0)
    assert a1["return"] == pytest.approx(100.0)

    a2 = declared[(2, "Room_A")]
    assert a2["supply"] == pytest.approx(200.0)
    assert a2["return"] == pytest.approx(200.0)

    b2 = declared[(2, "Room_B")]
    assert b2["supply"] == pytest.approx(100.0)
    assert b2["return"] == pytest.approx(100.0)

    exhaust = declared[(3, "Room_B")]
    assert exhaust["supply"] == pytest.approx(0.0)
    assert exhaust["return"] == pytest.approx(150.0)

    assert (1, "Room_B") not in declared
    assert (2, "Missing") not in declared


def test_emission_check_uses_hvac_group_not_room_only() -> None:
    declared = check.declared_terminal_flows(_spatial(), _airflow())
    assert check._check_emission(_terminal_entries(), declared) == []

    bad = [dict(entry) for entry in _terminal_entries()]
    bad[0]["declared_flow_m3h"] = 200.0
    errors = check._check_emission(bad, declared)
    assert len(errors) == 1
    assert "ahs1" in errors[0]


def test_solved_check_compares_each_hvac_group_leg() -> None:
    declared = check.declared_terminal_flows(_spatial(), _airflow())
    flows = {1: 100.0, 2: 100.0, 3: 200.0, 4: 200.0}
    errors, rows = check._check_solved(
        _terminal_entries(), declared, flows, 0.05,
    )
    assert errors == []
    assert len(rows) == 4
