"""Structural invariants for pressure-directed door/stairwell authoring."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PLATFORM_ROOT = REPO_ROOT / "data" / "platforms"

EXPECTED: tuple[dict[str, Any], ...] = (
    {
        "platform": "expedition_cruise_300",
        "path": "MedBay_Door_Leakage",
        "from": "AHU_2_Main",
        "to": "AHU_MedBay_Dedicated",
        "flow_rate_m3h": 50.0,
        "description_tokens": [
            "MedBay negative-pressure",
            "CDC VSP 2025",
            "ISO 9943",
            "Magnitude unchanged",
        ],
    },
    {
        "platform": "fletcher_class_destroyer",
        "path": "access_trunk_boilers",
        "from": "HVAC_Boiler_Rooms",
        "to": "HVAC_Berthing",
        "flow_rate_m3h": 150.0,
        "description_tokens": [
            "boiler-room positive pressure",
            "ISO 9943:2009 A.2.3",
            "Magnitude unchanged",
        ],
    },
    {
        "platform": "mega_cruise_5000",
        "path": "Crew_to_Engine_Stairwell",
        "from": "AHU_Network_Crew_Accommodation",
        "to": "AHU_Dedicated_Engine",
        "flow_rate_m3h": 4000.0,
        "description_tokens": [
            "engine-room negative pressure",
            "CDC VSP 2025",
            "ISO 9943",
            "Magnitude unchanged",
        ],
    },
    {
        "platform": "mega_cruise_5000",
        "path": "Medical_Door_Leakage",
        "from": "AHU_Network_Crew_Accommodation",
        "to": "AHU_Dedicated_Medical",
        "flow_rate_m3h": 100.0,
        "description_tokens": [
            "negative-pressure regime",
            "CDC VSP 2025",
            "ISO 9943",
            "Magnitude unchanged",
        ],
    },
    {
        "platform": "mega_cruise_5000",
        "path": "Crew_to_Engine_Stairwell",
        "from": "AHU_Crew_Deck_D4",
        "to": "AHU_Dedicated_Engine",
        "flow_rate_m3h": 2000.0,
        "description_tokens": [
            "AHU_Crew_Deck_D4",
            "engine-room negative pressure",
            "CDC VSP 2025",
            "ISO 9943",
            "Magnitude unchanged",
        ],
    },
    {
        "platform": "messy_cruise_500",
        "path": "Crew_to_Engine_Stairwell",
        "from": "AHU_Network_Crew_Accommodation",
        "to": "AHU_Dedicated_Engine",
        "flow_rate_m3h": 4000.0,
        "description_tokens": [
            "engine-room negative pressure",
            "CDC VSP 2025",
            "ISO 9943",
            "Magnitude unchanged",
        ],
    },
    {
        "platform": "messy_cruise_500",
        "path": "Medical_Door_Leakage",
        "from": "AHU_Network_Crew_Accommodation",
        "to": "AHU_Dedicated_Medical",
        "flow_rate_m3h": 100.0,
        "description_tokens": [
            "negative-pressure regime",
            "CDC VSP 2025",
            "ISO 9943",
            "Magnitude unchanged",
        ],
    },
)


def _link(
    platform: str,
    path: str,
    from_zone: str,
    to_zone: str,
) -> dict[str, Any]:
    airflow = json.loads(
        (PLATFORM_ROOT / platform / "air_flow_paths.json").read_text(
            encoding="utf-8",
        ),
    )
    return next(
        link
        for link in airflow["cross_zone_links"]
        if link.get("path") == path
        and link.get("from") == from_zone
        and link.get("to") == to_zone
    )


def test_pressure_directed_row_4_links_keep_declared_sense_and_decisions() -> None:
    assert len(EXPECTED) == 7
    for expected in EXPECTED:
        link = _link(
            expected["platform"],
            expected["path"],
            expected["from"],
            expected["to"],
        )
        assert link["direction"] == "oneway"
        assert link["mechanism"] == "pressure_opening"
        assert link["filtered"] is False
        assert float(link["flow_rate_m3h"]) == pytest.approx(
            expected["flow_rate_m3h"],
        )
        description = str(link.get("description", ""))
        for token in expected["description_tokens"]:
            assert token in description, (
                f"{expected['platform']}: missing {token!r}"
            )
