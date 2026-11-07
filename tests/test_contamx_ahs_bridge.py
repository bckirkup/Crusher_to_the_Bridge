"""
test_contamx_ahs_bridge.py – AHS → star (room↔plenum) flow synthesis
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.contamx_ahs_bridge import (  # noqa: E402
    ahs_plenum_id,
    synthesize_ahs_recirculation_paths,
)
from engines.contamx_transport import ContamXTransportEngine  # noqa: E402
from engines.py_contam_bridge import (  # noqa: E402
    PATH_TYPE_HVAC_RETURN,
    PATH_TYPE_HVAC_SUPPLY,
    is_plenum_zone,
)


def test_synthesize_ahs_two_room_star() -> None:
    entries = [
        {"path_nr": 1, "from_zone": "A", "to_zone": "ahs1(Ret)", "kind": "ahs_return",
         "ahs_nr": 1, "is_hvac_ducted": True},
        {"path_nr": 2, "from_zone": "B", "to_zone": "ahs1(Ret)", "kind": "ahs_return",
         "ahs_nr": 1, "is_hvac_ducted": True},
        {"path_nr": 3, "from_zone": "ahs1(Sup)", "to_zone": "A", "kind": "ahs_supply",
         "ahs_nr": 1, "is_hvac_ducted": True},
        {"path_nr": 4, "from_zone": "ahs1(Sup)", "to_zone": "B", "kind": "ahs_supply",
         "ahs_nr": 1, "is_hvac_ducted": True},
        {"path_nr": 5, "from_zone": "ahs1(Ret)", "to_zone": "ahs1(Sup)", "kind": "ahs_recirc",
         "ahs_nr": 1, "is_hvac_ducted": True},
    ]
    # Equal returns/supplies 100 m³/h each; recirc 160 (80% of 200)
    flows = {1: 100.0, 2: 100.0, 3: 100.0, 4: 100.0, 5: 160.0}
    paths = synthesize_ahs_recirculation_paths(entries, flows, {"A", "B"})
    plenum = ahs_plenum_id(1)
    assert len(paths) == 4  # 2 returns + 2 supplies
    returns = [p for p in paths if p.path_type == PATH_TYPE_HVAC_RETURN]
    supplies = [p for p in paths if p.path_type == PATH_TYPE_HVAC_SUPPLY]
    assert len(returns) == 2
    assert len(supplies) == 2
    by_ret = {p.from_zone: p.flow_rate_m3h for p in returns}
    by_sup = {p.to_zone: p.flow_rate_m3h for p in supplies}
    assert by_ret["A"] == pytest.approx(100.0)
    assert by_ret["B"] == pytest.approx(100.0)
    # supply = S_j * (Rec/ΣS) = 100 * (160/200) = 80
    assert by_sup["A"] == pytest.approx(80.0)
    assert by_sup["B"] == pytest.approx(80.0)
    assert all(p.to_zone == plenum for p in returns)
    assert all(p.from_zone == plenum for p in supplies)
    assert all(not p.is_hvac_ducted for p in returns)
    assert all(p.is_hvac_ducted for p in supplies)


def test_synthesize_includes_single_room_ahs() -> None:
    entries = [
        {"path_nr": 1, "from_zone": "A", "to_zone": "ahs1(Ret)", "kind": "ahs_return",
         "ahs_nr": 1},
        {"path_nr": 2, "from_zone": "ahs1(Sup)", "to_zone": "A", "kind": "ahs_supply",
         "ahs_nr": 1},
        {"path_nr": 3, "from_zone": "ahs1(Ret)", "to_zone": "ahs1(Sup)", "kind": "ahs_recirc",
         "ahs_nr": 1},
    ]
    flows = {1: 50.0, 2: 50.0, 3: 40.0}
    paths = synthesize_ahs_recirculation_paths(entries, flows, {"A"})
    assert len(paths) == 2
    assert paths[0].path_type == PATH_TYPE_HVAC_RETURN
    assert paths[1].path_type == PATH_TYPE_HVAC_SUPPLY
    assert paths[0].flow_rate_m3h == pytest.approx(50.0)
    assert paths[1].flow_rate_m3h == pytest.approx(40.0)


def test_synthesize_rec_zero_applies_oa_fraction() -> None:
    """When ContamX reports Rec Flow0=0, recover Rec=(1-oa)·min(ΣR,ΣS)."""
    entries = [
        {"path_nr": 1, "from_zone": "A", "to_zone": "ahs1(Ret)", "kind": "ahs_return",
         "ahs_nr": 1},
        {"path_nr": 2, "from_zone": "B", "to_zone": "ahs1(Ret)", "kind": "ahs_return",
         "ahs_nr": 1},
        {"path_nr": 3, "from_zone": "ahs1(Sup)", "to_zone": "A", "kind": "ahs_supply",
         "ahs_nr": 1},
        {"path_nr": 4, "from_zone": "ahs1(Sup)", "to_zone": "B", "kind": "ahs_supply",
         "ahs_nr": 1},
        {"path_nr": 5, "from_zone": "ahs1(Ret)", "to_zone": "ahs1(Sup)", "kind": "ahs_recirc",
         "ahs_nr": 1},
    ]
    flows = {1: 100.0, 2: 100.0, 3: 100.0, 4: 100.0, 5: 0.0}
    paths = synthesize_ahs_recirculation_paths(
        entries, flows, {"A", "B"}, oa_fraction=0.2,
    )
    supplies = {
        p.to_zone: p.flow_rate_m3h
        for p in paths
        if p.path_type == PATH_TYPE_HVAC_SUPPLY
    }
    # Rec = 0.8 * 200 = 160 → supply = 100 * (160/200) = 80
    assert supplies["A"] == pytest.approx(80.0)
    assert supplies["B"] == pytest.approx(80.0)


def test_synthesize_rec_zero_uses_declared_oa_per_group() -> None:
    entries = [
        {"path_nr": 1, "from_zone": "A", "to_zone": "ahs1(Ret)",
         "kind": "ahs_return", "ahs_nr": 1, "declared_oa_fraction": 0.2},
        {"path_nr": 2, "from_zone": "ahs1(Sup)", "to_zone": "A",
         "kind": "ahs_supply", "ahs_nr": 1, "declared_oa_fraction": 0.2},
        {"path_nr": 3, "from_zone": "ahs1(Ret)", "to_zone": "ahs1(Sup)",
         "kind": "ahs_recirc", "ahs_nr": 1},
        {"path_nr": 4, "from_zone": "B", "to_zone": "ahs2(Ret)",
         "kind": "ahs_return", "ahs_nr": 2, "declared_oa_fraction": 0.8},
        {"path_nr": 5, "from_zone": "ahs2(Sup)", "to_zone": "B",
         "kind": "ahs_supply", "ahs_nr": 2, "declared_oa_fraction": 0.8},
        {"path_nr": 6, "from_zone": "ahs2(Ret)", "to_zone": "ahs2(Sup)",
         "kind": "ahs_recirc", "ahs_nr": 2},
    ]
    flows = {1: 100.0, 2: 100.0, 3: 0.0, 4: 100.0, 5: 100.0, 6: 0.0}
    paths = synthesize_ahs_recirculation_paths(
        entries, flows, {"A", "B"}, oa_fraction=0.5,
    )
    supplies = {
        p.to_zone: p.flow_rate_m3h
        for p in paths
        if p.path_type == PATH_TYPE_HVAC_SUPPLY
    }
    assert supplies["A"] == pytest.approx(80.0)
    assert supplies["B"] == pytest.approx(20.0)


def test_synthesize_rec_zero_scalar_fallback_is_graduated() -> None:
    entries = [
        {"path_nr": 1, "from_zone": "A", "to_zone": "ahs1(Ret)",
         "kind": "ahs_return", "ahs_nr": 1},
        {"path_nr": 2, "from_zone": "B", "to_zone": "ahs1(Ret)",
         "kind": "ahs_return", "ahs_nr": 1},
        {"path_nr": 3, "from_zone": "ahs1(Sup)", "to_zone": "A",
         "kind": "ahs_supply", "ahs_nr": 1},
        {"path_nr": 4, "from_zone": "ahs1(Sup)", "to_zone": "B",
         "kind": "ahs_supply", "ahs_nr": 1},
        {"path_nr": 5, "from_zone": "ahs1(Ret)", "to_zone": "ahs1(Sup)",
         "kind": "ahs_recirc", "ahs_nr": 1},
    ]
    flows = {1: 100.0, 2: 100.0, 3: 100.0, 4: 100.0, 5: 0.0}
    expected = {0.2: 80.0, 0.8: 20.0}
    for oa, supply_flow in expected.items():
        paths = synthesize_ahs_recirculation_paths(
            entries, flows, {"A", "B"}, oa_fraction=oa,
        )
        supplies = {
            p.to_zone: p.flow_rate_m3h
            for p in paths
            if p.path_type == PATH_TYPE_HVAC_SUPPLY
        }
        assert supplies["A"] == pytest.approx(supply_flow)
        assert supplies["B"] == pytest.approx(supply_flow)


def test_synthesize_nonzero_rec_warns_when_it_diverges_from_declared_oa() -> None:
    entries = [
        {"path_nr": 1, "from_zone": "A", "to_zone": "ahs1(Ret)",
         "kind": "ahs_return", "ahs_nr": 1, "declared_oa_fraction": 0.2},
        {"path_nr": 2, "from_zone": "ahs1(Sup)", "to_zone": "A",
         "kind": "ahs_supply", "ahs_nr": 1, "declared_oa_fraction": 0.2},
        {"path_nr": 3, "from_zone": "ahs1(Ret)", "to_zone": "ahs1(Sup)",
         "kind": "ahs_recirc", "ahs_nr": 1},
    ]
    flows = {1: 100.0, 2: 100.0, 3: 120.0}
    with pytest.warns(UserWarning, match="AHS 1 recirc"):
        paths = synthesize_ahs_recirculation_paths(
            entries, flows, {"A"}, oa_fraction=0.5,
        )
    supplies = [
        p.flow_rate_m3h for p in paths
        if p.path_type == PATH_TYPE_HVAC_SUPPLY
    ]
    assert supplies == [pytest.approx(120.0)]


def test_synthesize_nonzero_rec_matching_declared_oa_does_not_warn() -> None:
    entries = [
        {"path_nr": 1, "from_zone": "A", "to_zone": "ahs1(Ret)",
         "kind": "ahs_return", "ahs_nr": 1, "declared_oa_fraction": 0.2},
        {"path_nr": 2, "from_zone": "ahs1(Sup)", "to_zone": "A",
         "kind": "ahs_supply", "ahs_nr": 1, "declared_oa_fraction": 0.2},
        {"path_nr": 3, "from_zone": "ahs1(Ret)", "to_zone": "ahs1(Sup)",
         "kind": "ahs_recirc", "ahs_nr": 1},
    ]
    flows = {1: 100.0, 2: 100.0, 3: 80.0}
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        paths = synthesize_ahs_recirculation_paths(
            entries, flows, {"A"}, oa_fraction=0.5,
        )
    assert not record
    supplies = [
        p.flow_rate_m3h for p in paths
        if p.path_type == PATH_TYPE_HVAC_SUPPLY
    ]
    assert supplies == [pytest.approx(80.0)]


def test_contamx_engine_includes_synthesized_ahs_star() -> None:
    spatial = {
        "platform": "t",
        "zones": [
            {"id": "A", "volume_m3": 100, "deck": "main", "display": {"x": 0, "y": 0}},
            {"id": "B", "volume_m3": 100, "deck": "main", "display": {"x": 1, "y": 0}},
        ],
    }
    entries = [
        {"path_nr": 1, "from_zone": "A", "to_zone": "B", "kind": "passageway",
         "ahs_nr": 0, "is_hvac_ducted": False, "crusher_transfer": True},
        {"path_nr": 2, "from_zone": "A", "to_zone": "ahs1(Ret)", "kind": "ahs_return",
         "ahs_nr": 1, "is_hvac_ducted": True},
        {"path_nr": 3, "from_zone": "B", "to_zone": "ahs1(Ret)", "kind": "ahs_return",
         "ahs_nr": 1, "is_hvac_ducted": True},
        {"path_nr": 4, "from_zone": "ahs1(Sup)", "to_zone": "A", "kind": "ahs_supply",
         "ahs_nr": 1, "is_hvac_ducted": True},
        {"path_nr": 5, "from_zone": "ahs1(Sup)", "to_zone": "B", "kind": "ahs_supply",
         "ahs_nr": 1, "is_hvac_ducted": True},
        {"path_nr": 6, "from_zone": "ahs1(Ret)", "to_zone": "ahs1(Sup)", "kind": "ahs_recirc",
         "ahs_nr": 1, "is_hvac_ducted": True},
    ]
    flows = {1: 10.0, 2: 80.0, 3: 80.0, 4: 80.0, 5: 80.0, 6: 128.0}
    eng = ContamXTransportEngine.from_flow_field(
        spatial, entries, flows, path_map_entries=entries,
    )
    # 1 adjacency + 4 star HVAC (2 ret + 2 sup)
    assert len(eng.airflow_paths) == 5
    kinds = {p.path_type for p in eng.airflow_paths}
    assert PATH_TYPE_HVAC_RETURN in kinds
    assert PATH_TYPE_HVAC_SUPPLY in kinds
    assert "contamx_path" in kinds
    assert any(is_plenum_zone(zid) for zid in eng.zone_nodes)
    result = eng.transport_step({"A": 1000.0, "B": 0.0})
    assert all(not is_plenum_zone(z) for z in result)
    assert result["B"] > 0.0
