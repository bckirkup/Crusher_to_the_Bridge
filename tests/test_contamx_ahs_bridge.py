"""
test_contamx_ahs_bridge.py – AHS → room↔room flow synthesis
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.contamx_ahs_bridge import synthesize_ahs_recirculation_paths  # noqa: E402
from engines.contamx_transport import ContamXTransportEngine  # noqa: E402


def test_synthesize_ahs_two_room_mixing() -> None:
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
    assert len(paths) == 2  # A→B and B→A
    by_pair = {(p.from_zone, p.to_zone): p.flow_rate_m3h for p in paths}
    # Q_AB = 100 * (160/200) * (100/200) = 40
    assert by_pair[("A", "B")] == pytest.approx(40.0)
    assert by_pair[("B", "A")] == pytest.approx(40.0)
    assert all(p.is_hvac_ducted for p in paths)
    assert all(p.path_type == "hvac_recirculation" for p in paths)


def test_synthesize_skips_single_room_ahs() -> None:
    entries = [
        {"path_nr": 1, "from_zone": "A", "to_zone": "ahs1(Ret)", "kind": "ahs_return",
         "ahs_nr": 1},
        {"path_nr": 2, "from_zone": "ahs1(Sup)", "to_zone": "A", "kind": "ahs_supply",
         "ahs_nr": 1},
        {"path_nr": 3, "from_zone": "ahs1(Ret)", "to_zone": "ahs1(Sup)", "kind": "ahs_recirc",
         "ahs_nr": 1},
    ]
    flows = {1: 50.0, 2: 50.0, 3: 40.0}
    assert synthesize_ahs_recirculation_paths(entries, flows, {"A"}) == []


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
    # Duty-scaled terminals; Rec path absent/zero (destroyer ContamX SIM pattern)
    flows = {1: 100.0, 2: 100.0, 3: 100.0, 4: 100.0, 5: 0.0}
    paths = synthesize_ahs_recirculation_paths(
        entries, flows, {"A", "B"}, oa_fraction=0.2,
    )
    by_pair = {(p.from_zone, p.to_zone): p.flow_rate_m3h for p in paths}
    # Rec = 0.8 * 200 = 160 → Q_ij = 100 * (160/200) * (100/200) = 40
    assert by_pair[("A", "B")] == pytest.approx(40.0)
    assert by_pair[("B", "A")] == pytest.approx(40.0)


def test_contamx_engine_includes_synthesized_ahs() -> None:
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
    # 1 adjacency + 2 synthesized HVAC
    assert len(eng.airflow_paths) == 3
    kinds = {p.path_type for p in eng.airflow_paths}
    assert "hvac_recirculation" in kinds
    assert "contamx_path" in kinds
