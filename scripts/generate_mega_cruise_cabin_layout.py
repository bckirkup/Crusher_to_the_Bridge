#!/usr/bin/env python3
"""
Regenerate mega_cruise_5000 spatial_layout.json and air_flow_paths.json with
cabin-corridor resolution (see docs/PLATFORM_CABIN_REVISION.md).

Usage::

    python3 scripts/generate_mega_cruise_cabin_layout.py
    python3 scripts/generate_mega_cruise_cabin_layout.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from copy import deepcopy
from typing import Any

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEGACY_LAYOUT = os.path.join(REPO, "data", "platforms", "messy_cruise_500", "spatial_layout.json")
OUT_DIR = os.path.join(REPO, "data", "platforms", "mega_cruise_5000")

PAX_DECKS = [6, 7, 8, 9, 10, 11, 12, 13, 14]
PAX_SECTIONS = ("Port", "Stbd", "Central")
PAX_SUBSECTIONS = ("Fwd", "Mid", "Aft")
CREW_DECKS = [1, 2, 3, 4]
CREW_SECTIONS = ("Fwd", "Mid", "Aft")

PAX_DECK_Y = {6: 51.5, 7: 47.0, 8: 42.5, 9: 38.0, 10: 33.5, 11: 29.0, 12: 24.5, 13: 20.0, 14: 15.5}
CREW_DECK_Y = {1: 88, 2: 82, 3: 76, 4: 70}
SECTION_X = {"Port": 320, "Stbd": 320, "Central": 270}


def _pax_zone_id(deck: int, section: str, sub: str) -> str:
    return f"Pax_Corridor_D{deck}_{section}_{sub}"


def _crew_zone_id(deck: int, section: str) -> str:
    return f"Crew_Corridor_D{deck}_{section}"


def _pax_ventilation(deck: int, section: str) -> str:
    if section in ("Port", "Stbd"):
        return "balcony_partial"
    if section == "Central" and deck in (6, 7, 8):
        return "atrium_view"
    return "interior_hvac"


def _pax_display(deck: int, section: str, sub: str) -> dict[str, float]:
    base_y = PAX_DECK_Y[deck]
    y_off = {"Port": -1.5, "Stbd": 1.5, "Central": 0}[section]
    x_off = {"Fwd": -25, "Mid": 0, "Aft": 25}[sub]
    return {"x": SECTION_X[section] + x_off, "y": base_y + y_off}


def _crew_display(deck: int, section: str) -> dict[str, float]:
    x_off = {"Fwd": -20, "Mid": 0, "Aft": 20}[section]
    return {"x": 300 + x_off, "y": CREW_DECK_Y[deck]}


def _public_zones(legacy: dict[str, Any]) -> list[dict[str, Any]]:
    skip_prefixes = ("Passenger_Cabins_", "Crew_Quarters_")
    return [deepcopy(z) for z in legacy["zones"] if not z["id"].startswith(skip_prefixes)]


def _pax_corridor_zones() -> list[dict[str, Any]]:
    zones: list[dict[str, Any]] = []
    for deck in PAX_DECKS:
        for section in PAX_SECTIONS:
            vent = _pax_ventilation(deck, section)
            for sub in PAX_SUBSECTIONS:
                zid = _pax_zone_id(deck, section, sub)
                zones.append({
                    "id": zid,
                    "type": "Cabin_Corridor",
                    "traffic": "low",
                    "volume_m3": 1200,
                    "deck": f"{deck}_Cabins",
                    "max_occupancy": 67,
                    "display": _pax_display(deck, section, sub),
                    "cabin_ventilation_type": vent,
                    "cabin_size": 2,
                    "description": (
                        f"Passenger cabin corridor, Deck {deck} {section} {sub}. "
                        f"~10 cabins, ~67 pax, ventilation={vent}."
                    ),
                })
    return zones


def _crew_corridor_zones() -> list[dict[str, Any]]:
    zones: list[dict[str, Any]] = []
    for deck in CREW_DECKS:
        for section in CREW_SECTIONS:
            zid = _crew_zone_id(deck, section)
            zones.append({
                "id": zid,
                "type": "Cabin_Corridor",
                "traffic": "medium",
                "volume_m3": 900,
                "deck": f"{deck}_Crew",
                "max_occupancy": 170,
                "display": _crew_display(deck, section),
                "cabin_ventilation_type": "interior_hvac",
                "cabin_size": 3,
                "description": (
                    f"Crew cabin corridor, Deck {deck} {section}. "
                    "~35 shared cabins, higher density, interior HVAC."
                ),
            })
    return zones


def build_spatial_layout(legacy: dict[str, Any]) -> dict[str, Any]:
    return {
        "platform": "mega_cruise_5000",
        "description": (
            "Mega cruise ship (~5,000 passengers, ~2,000 crew), Oasis-class scale. "
            "Cabin-corridor resolution: 81 passenger corridor sections (~67 pax each) "
            "and 12 crew corridor sections (~170 crew each). See docs/PLATFORM_CABIN_REVISION.md; "
            "legacy well-mixed topology archived as messy_cruise_500."
        ),
        "isolation_unit_capacity": 0,
        "deck_dimensions": legacy.get("deck_dimensions", {"length_m": 362, "beam_m": 64}),
        "confinement_isolation_factor": 0.05,
        "corridor_direct_contact_factor": 0.15,
        "graywater_zones": ["Engine_Room_Aft"],
        "zones": _public_zones(legacy) + _pax_corridor_zones() + _crew_corridor_zones(),
    }


def _pax_zones_on_deck(deck: int) -> list[str]:
    return [_pax_zone_id(deck, s, sub) for s in PAX_SECTIONS for sub in PAX_SUBSECTIONS]


def _crew_zones_on_deck(deck: int) -> list[str]:
    return [_crew_zone_id(deck, s) for s in CREW_SECTIONS]


def _pax_adjacency() -> list[dict[str, str]]:
    adj: list[dict[str, str]] = []
    for deck in PAX_DECKS:
        for section in PAX_SECTIONS:
            subs = [_pax_zone_id(deck, section, sub) for sub in PAX_SUBSECTIONS]
            for a, b in zip(subs, subs[1:]):
                adj.append({"from": a, "to": b, "type": "corridor"})
            if section != "Central":
                for sub in PAX_SUBSECTIONS:
                    adj.append({
                        "from": _pax_zone_id(deck, section, sub),
                        "to": _pax_zone_id(deck, "Central", sub),
                        "type": "corridor",
                    })
        if deck + 1 in PAX_DECK_Y:
            central_subs = [_pax_zone_id(deck, "Central", sub) for sub in PAX_SUBSECTIONS]
            next_central = [_pax_zone_id(deck + 1, "Central", sub) for sub in PAX_SUBSECTIONS]
            for a, b in zip(central_subs, next_central):
                adj.append({"from": a, "to": b, "type": "elevator_bank"})
        if deck in (6, 7, 8):
            mid = _pax_zone_id(deck, "Central", "Mid")
            adj.append({"from": mid, "to": "Royal_Promenade", "type": "stairwell"})
            adj.append({"from": mid, "to": "Central_Park_Open_Atrium", "type": "stairwell"})
    return adj


def _crew_adjacency() -> list[dict[str, str]]:
    adj: list[dict[str, str]] = []
    for deck in CREW_DECKS:
        sections = [_crew_zone_id(deck, s) for s in CREW_SECTIONS]
        for a, b in zip(sections, sections[1:]):
            adj.append({"from": a, "to": b, "type": "corridor"})
        if deck + 1 in CREW_DECK_Y:
            next_sections = [_crew_zone_id(deck + 1, s) for s in CREW_SECTIONS]
            for a, b in zip(sections, next_sections):
                adj.append({"from": a, "to": b, "type": "stairwell"})
    adj.extend([
        {"from": "Crew_Mess_Main", "to": "Crew_Corridor_D2_Mid", "type": "corridor"},
        {"from": "Crew_Mess_Forward", "to": "Crew_Corridor_D3_Mid", "type": "corridor"},
        {"from": "Medical_Center", "to": "Crew_Corridor_D2_Mid", "type": "corridor"},
        {"from": "Crew_Corridor_D1_Fwd", "to": "Engine_Room_Aft", "type": "ladder_well"},
        {"from": "Crew_Corridor_D1_Fwd", "to": "Engine_Control_Room", "type": "ladder_well"},
        {"from": "Crew_Corridor_D1_Mid", "to": "Central_Stores", "type": "service_corridor"},
        {"from": "Crew_Corridor_D1_Aft", "to": "Laundry_Main", "type": "service_corridor"},
        {"from": "Crew_Corridor_D4_Mid", "to": "Main_Dining_Room_Lower", "type": "service_stairwell"},
    ])
    return adj


def _public_adjacency(legacy_airflow: dict[str, Any]) -> list[dict[str, str]]:
    skip = ("Passenger_Cabins", "Crew_Quarters")
    out = [
        link for link in legacy_airflow.get("adjacency", [])
        if not any(link["from"].startswith(p) or link["to"].startswith(p) for p in skip)
    ]
    out.extend([
        {"from": "Spa_Fitness_Complex", "to": "Pax_Corridor_D14_Central_Mid", "type": "elevator_bank"},
        {"from": "Main_Pool_Deck", "to": "Pax_Corridor_D14_Central_Mid", "type": "elevator_bank"},
        {"from": "Windjammer_Buffet", "to": "Pax_Corridor_D10_Central_Mid", "type": "elevator_bank"},
    ])
    return out


def build_air_flow_paths(legacy_airflow: dict[str, Any], zone_ids: set[str]) -> dict[str, Any]:
    public_hvac: list[dict[str, Any]] = []
    for hz in legacy_airflow["hvac_zones"]:
        if hz["id"].startswith("AHU_Network_Cabins"):
            continue
        entry = dict(hz)
        if entry["id"] == "AHU_Network_Crew_Accommodation":
            entry["rooms"] = [r for r in entry["rooms"] if r.startswith("Crew_Mess")]
        public_hvac.append(entry)

    pax_hvac = [{
        "id": f"AHU_Pax_Deck_D{deck}",
        "rooms": _pax_zones_on_deck(deck),
        "ach": 6.0,
        "description": f"Deck {deck} passenger cabin fan-coil branch.",
    } for deck in PAX_DECKS]

    crew_hvac = [{
        "id": f"AHU_Crew_Deck_D{deck}",
        "rooms": _crew_zones_on_deck(deck),
        "ach": 5.0,
        "description": f"Deck {deck} crew accommodation branch.",
    } for deck in CREW_DECKS]

    cross_links = [
        cl for cl in legacy_airflow.get("cross_zone_links", [])
        if not cl["from"].startswith("AHU_Network_Cabins")
    ]
    for i, deck in enumerate(PAX_DECKS[:-1]):
        nxt = PAX_DECKS[i + 1]
        cross_links.append({
            "from": f"AHU_Pax_Deck_D{deck}",
            "to": f"AHU_Pax_Deck_D{nxt}",
            "flow_rate_m3h": 1200.0,
            "is_hvac_ducted": True,
            "path": f"Pax_Trunk_D{deck}_D{nxt}",
        })
    for i, deck in enumerate(CREW_DECKS[:-1]):
        nxt = CREW_DECKS[i + 1]
        cross_links.append({
            "from": f"AHU_Crew_Deck_D{deck}",
            "to": f"AHU_Crew_Deck_D{nxt}",
            "flow_rate_m3h": 800.0,
            "is_hvac_ducted": True,
            "path": f"Crew_Trunk_D{deck}_D{nxt}",
        })
    for deck in PAX_DECKS:
        cross_links.append({
            "from": f"AHU_Pax_Deck_D{deck}",
            "to": "AHU_Network_Midship_Atrium",
            "flow_rate_m3h": 1500.0,
            "is_hvac_ducted": True,
            "path": f"Cabin_Relief_D{deck}",
        })
    cross_links.append({
        "from": "AHU_Crew_Deck_D4",
        "to": "AHU_Dedicated_Engine",
        "flow_rate_m3h": 2000.0,
        "is_hvac_ducted": False,
        "path": "Crew_to_Engine_Stairwell",
    })

    adjacency = [
        a for a in (_public_adjacency(legacy_airflow) + _pax_adjacency() + _crew_adjacency())
        if a["from"] in zone_ids and a["to"] in zone_ids
    ]

    return {
        "platform": "mega_cruise_5000",
        "description": "HVAC for mega_cruise_5000 cabin-corridor layout.",
        "hvac_zones": public_hvac + pax_hvac + crew_hvac,
        "cross_zone_links": cross_links,
        "adjacency": adjacency,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with open(LEGACY_LAYOUT, encoding="utf-8") as fh:
        legacy = json.load(fh)
    legacy_airflow_path = os.path.join(
        REPO, "data", "platforms", "messy_cruise_500", "air_flow_paths.json",
    )
    with open(legacy_airflow_path, encoding="utf-8") as fh:
        legacy_airflow = json.load(fh)

    spatial = build_spatial_layout(legacy)
    zone_ids = {z["id"] for z in spatial["zones"]}
    airflow = build_air_flow_paths(legacy_airflow, zone_ids)

    print(f"zones: {len(spatial['zones'])}")
    if args.dry_run:
        return 0

    os.makedirs(OUT_DIR, exist_ok=True)
    for name, data in (("spatial_layout.json", spatial), ("air_flow_paths.json", airflow)):
        path = os.path.join(OUT_DIR, name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
