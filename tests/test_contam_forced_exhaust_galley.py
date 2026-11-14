"""Structural invariants for forced-exhaust galley authoring (§5.5 rows 1-3)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PLATFORM_ROOT = REPO_ROOT / "data" / "platforms"

EXPECTED: dict[str, dict[str, Any]] = {
    "classic_cruise_1900": {
        "path": "Dining_Galley_Exhaust",
        "from": "MainDining_L",
        "to": "MainGalley",
        "direction": "oneway",
        "mechanism": "prescribed_flow",
        "filtered": False,
        "description_tokens": [
            "ASSUMED-GALLEY-TRANSFER-MAGNITUDE",
            "CDC VSP 2025",
            "ISO 9943",
        ],
    },
    "diamond_princess": {
        "path": "Dining_Galley_Exhaust",
        "from": "International",
        "to": "MainGalley",
        "direction": "oneway",
        "mechanism": "prescribed_flow",
        "filtered": False,
        "description_tokens": [
            "ASSUMED-GALLEY-TRANSFER-MAGNITUDE",
            "CDC VSP 2025",
            "ISO 9943",
        ],
    },
    "expedition_cruise_450": {
        "path": "Dining_Galley_Exhaust",
        "from": "MainDining",
        "to": "MainGalley",
        "direction": "oneway",
        "mechanism": "prescribed_flow",
        "filtered": False,
        "description_tokens": [
            "ASSUMED-GALLEY-TRANSFER-MAGNITUDE",
            "CDC VSP 2025",
            "ISO 9943",
        ],
    },
    "greg_mortimer": {
        "path": "Dining_Galley_Exhaust",
        "from": "DiningRoom",
        "to": "MainGalley",
        "direction": "oneway",
        "mechanism": "prescribed_flow",
        "filtered": False,
        "description_tokens": [
            "ASSUMED-GALLEY-TRANSFER-MAGNITUDE",
            "CDC VSP 2025",
            "ISO 9943",
        ],
    },
    "spirit_cruise_3000": {
        "path": "Dining_Galley_Exhaust",
        "from": "MainDining_L",
        "to": "MainGalley",
        "direction": "oneway",
        "mechanism": "prescribed_flow",
        "filtered": False,
        "description_tokens": [
            "ASSUMED-GALLEY-TRANSFER-MAGNITUDE",
            "CDC VSP 2025",
            "ISO 9943",
        ],
    },
    "enterprise_constitution_tos": {
        "path": "Galley_Service_Exhaust",
        "from": "Mess_Hall",
        "to": "Galley",
        "direction": "oneway",
        "mechanism": "prescribed_flow",
        "filtered": False,
        "description_tokens": ["ISO 9943:2009 A.2.3", "Grade C"],
    },
    "enterprise_galaxy_tng": {
        "path": "Galley_Service_Exhaust",
        "from": "Mess_Hall",
        "to": "Galley",
        "direction": "oneway",
        "mechanism": "prescribed_flow",
        "filtered": False,
        "description_tokens": ["ISO 9943:2009 A.2.3", "Grade C"],
    },
    "expedition_cruise_300": {
        "path": "Galley_Exhaust_Return",
        "from": "AHU_3_Service",
        "to": "AHU_2_Main",
        "direction": "oneway",
        "mechanism": "prescribed_flow",
        "filtered": True,
        "description_tokens": [
            "non-galley service-area air",
            "100% overboard",
            "Grade C",
        ],
    },
    "san_antonio_class_lpd": {
        "path": "galley_exhaust_to_mess",
        "from": "HVAC_Galley",
        "to": "HVAC_Crew_Habitable",
        "direction": "oneway",
        "mechanism": "prescribed_flow",
        "filtered": False,
        "description_tokens": [
            "naval analogy",
            "no filtration/recirculation credit",
        ],
    },
}


def _link(platform: str, path: str) -> dict[str, Any]:
    airflow = json.loads(
        (PLATFORM_ROOT / platform / "air_flow_paths.json").read_text(
            encoding="utf-8",
        ),
    )
    return next(
        link for link in airflow["cross_zone_links"] if link.get("path") == path
    )


def test_galley_rows_1_3_links_keep_declared_sense_and_decisions() -> None:
    assert len(EXPECTED) == 9
    for platform, expected in EXPECTED.items():
        link = _link(platform, expected["path"])
        assert link["from"] == expected["from"]
        assert link["to"] == expected["to"]
        assert link["direction"] == expected["direction"]
        assert link["mechanism"] == expected["mechanism"]
        assert link["filtered"] is expected["filtered"]
        assert float(link["flow_rate_m3h"]) > 0.0
        description = str(link.get("description", ""))
        for token in expected["description_tokens"]:
            assert token in description, f"{platform}: missing {token!r}"
