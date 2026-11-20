"""Structural invariants for the ducted relief/medical exhaust authoring row.

Pins the row-5 ``forced_exhaust`` + ``is_hvac_ducted`` class from
``docs/proposals/forced_exhaust_audit_and_fix_plan.md`` §5.5 and the native
filtration semantics those decisions move under N1.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from scipy.linalg import expm

from engines.py_contam_bridge import ContamTransportEngine

REPO_ROOT = Path(__file__).resolve().parents[1]
PLATFORM_ROOT = REPO_ROOT / "data" / "platforms"

ROW5_PATHS = {
    "Cabin_Relief",
    "Corridor_Relief_Exhaust",
    "Dining_to_Galley_Transfer",
    "Galley_Exhaust_Return",
    "galley_exhaust_to_mess",
    "medical_exhaust",
}
EXPECTED_PLATFORM_COUNTS = {
    "classic_cruise_1900": 6,
    "diamond_princess": 5,
    "enterprise_constitution_tos": 3,
    "enterprise_galaxy_tng": 6,
    "expedition_cruise_300": 1,
    "explorer_seas_06": 5,
    "legend_class_nsc": 1,
    "mega_cruise_5000": 10,
    "messy_cruise_500": 3,
    "san_antonio_class_lpd": 2,
    "spirit_cruise_3000": 8,
}
EXPECTED_FILTERED_FALSE = {
    ("legend_class_nsc", "medical_exhaust"),
    ("mega_cruise_5000", "Dining_to_Galley_Transfer"),
    ("messy_cruise_500", "Dining_to_Galley_Transfer"),
    ("san_antonio_class_lpd", "galley_exhaust_to_mess"),
    ("san_antonio_class_lpd", "medical_exhaust"),
}


def _is_row5_path(path: str) -> bool:
    return path in ROW5_PATHS or path.startswith(
        ("Cabin_Relief", "Corridor_Relief_Exhaust")
    )


def _row5_links() -> list[tuple[str, int, dict[str, Any]]]:
    rows: list[tuple[str, int, dict[str, Any]]] = []
    for airflow_path in sorted(PLATFORM_ROOT.glob("*/air_flow_paths.json")):
        platform = airflow_path.parent.name
        airflow = json.loads(airflow_path.read_text(encoding="utf-8"))
        for index, link in enumerate(airflow.get("cross_zone_links", [])):
            path = str(link.get("path", ""))
            if _is_row5_path(path) and link.get("is_hvac_ducted") is True:
                rows.append((platform, index, link))
    return rows


def _transport_engine(
    zones: list[str], links: list[dict[str, Any]],
) -> ContamTransportEngine:
    layout = {"zones": [{"id": zone, "volume_m3": 100.0} for zone in zones]}
    airflow = {
        "hvac_zones": [],
        "adjacency": [],
        "cross_zone_links": links,
    }
    return ContamTransportEngine(
        layout,
        airflow,
        filter_efficiency=0.5,
        natural_decay_rate=0.0,
    )


def _material_time_by_zone(
    engine: ContamTransportEngine,
    source: str,
    *,
    horizon_hours: float = 1.0,
) -> dict[str, float]:
    operator = engine._build_decay_free_operator()
    zone_ids = list(engine._real_zone_ids)
    n = len(zone_ids)
    block = np.zeros((2 * n, 2 * n))
    block[:n, :n] = operator
    block[:n, n:] = np.eye(n)
    start = np.zeros(n)
    start[zone_ids.index(source)] = 1.0
    solution = expm(block * horizon_hours)[:n, n:] @ start
    return {zone: float(solution[index]) for index, zone in enumerate(zone_ids)}


def _prescribed_link(
    source: str,
    destination: str,
    flow_m3h: float,
    *,
    filtered: bool,
) -> dict[str, Any]:
    return {
        "from": source,
        "to": destination,
        "flow_rate_m3h": flow_m3h,
        "path": "ducted_relief_test",
        "direction": "oneway",
        "mechanism": "prescribed_flow",
        "filtered": filtered,
        "is_hvac_ducted": True,
    }


class TestDuctedReliefClassDeclaration:
    def test_row5_class_is_the_expected_45_links(self) -> None:
        rows = _row5_links()
        assert len(rows) == 50
        counts: dict[str, int] = {}
        for platform, _index, link in rows:
            counts[platform] = counts.get(platform, 0) + 1
            assert link["direction"] == "oneway"
            assert link["mechanism"] == "prescribed_flow"
            assert link["is_hvac_ducted"] is True
            assert isinstance(link["filtered"], bool)
            assert float(link["flow_rate_m3h"]) > 0.0
        assert counts == EXPECTED_PLATFORM_COUNTS

    def test_filtered_decisions_match_authored_table(self) -> None:
        observed_false = {
            (platform, str(link.get("path", "")))
            for platform, _index, link in _row5_links()
            if link.get("filtered") is False
        }
        assert observed_false == EXPECTED_FILTERED_FALSE

    def test_medical_exhaust_is_unfiltered_once_through(self) -> None:
        by_key = {
            (platform, str(link.get("path", ""))): link
            for platform, _index, link in _row5_links()
        }
        for key in (
            ("legend_class_nsc", "medical_exhaust"),
            ("san_antonio_class_lpd", "medical_exhaust"),
        ):
            link = by_key[key]
            assert link["filtered"] is False
            assert link["direction"] == "oneway"
            assert link["mechanism"] == "prescribed_flow"
            assert float(link["flow_rate_m3h"]) == pytest.approx(
                100.0 if key[0] == "legend_class_nsc" else 200.0,
            )
            description = str(link.get("description", ""))
            assert "once-through" in description
            assert "no recirculation-filter credit" in description
            assert "CDC VSP 2025 §33.2.1" in description

    def test_recirculated_galley_return_stays_filtered(self) -> None:
        link = next(
            link
            for platform, _index, link in _row5_links()
            if platform == "expedition_cruise_300"
            and link.get("path") == "Galley_Exhaust_Return"
        )
        assert link["filtered"] is True
        assert "stays a filtered prescribed-flow leg" in str(link.get("description", ""))

    def test_san_antonio_galley_leg_keeps_row3_no_credit(self) -> None:
        link = next(
            link
            for platform, _index, link in _row5_links()
            if platform == "san_antonio_class_lpd"
            and link.get("path") == "galley_exhaust_to_mess"
        )
        assert link["filtered"] is False
        assert "no filtration/recirculation credit" in str(link.get("description", ""))

    @pytest.mark.parametrize("platform", ["mega_cruise_5000", "messy_cruise_500"])
    def test_dining_to_galley_transfer_is_an_ambient_sink(self, platform: str) -> None:
        link = next(
            link
            for _platform, _index, link in _row5_links()
            if _platform == platform
            and link.get("path") == "Dining_to_Galley_Transfer"
        )
        assert link["from"] == "AHU_Network_Aft_Dining_Rec"
        assert link["to"] == "ambient"
        assert link["direction"] == "oneway"
        assert link["mechanism"] == "prescribed_flow"
        assert link["filtered"] is False
        assert link["is_hvac_ducted"] is True
        assert float(link["flow_rate_m3h"]) == pytest.approx(15000.0)
        description = str(link.get("description", ""))
        assert "once-through prescribed-flow sink to ambient" in description
        assert "exhausting odors overboard" in description
        assert "no filtration/recirculation credit" in description


class TestDuctedFiltrationResponse:
    def test_filtered_bit_moves_downstream_mass_not_upstream(self) -> None:
        def material_times(filtered: bool) -> dict[str, float]:
            engine = _transport_engine(
                ["A", "B"],
                [_prescribed_link("A", "B", 60.0, filtered=filtered)],
            )
            return _material_time_by_zone(engine, "A")

        unfiltered = material_times(False)
        filtered = material_times(True)
        assert filtered["A"] == pytest.approx(unfiltered["A"], rel=1e-9, abs=1e-12)
        assert filtered["B"] > 0.0
        assert unfiltered["B"] > filtered["B"] + 0.05

    def test_scaled_oneway_flow_changes_downstream_not_upstream(self) -> None:
        def material_times(link_flow_m3h: float) -> dict[str, float]:
            links = [
                _prescribed_link("S", "M", 60.0, filtered=False),
                _prescribed_link("M", "D", link_flow_m3h, filtered=False),
            ]
            engine = _transport_engine(["S", "M", "D"], links)
            return _material_time_by_zone(engine, "S")

        low = material_times(60.0)
        high = material_times(120.0)
        assert high["S"] == pytest.approx(low["S"], rel=1e-9, abs=1e-12)
        assert high["D"] > low["D"] + 0.01
        assert high["M"] != pytest.approx(low["M"], rel=1e-9)
