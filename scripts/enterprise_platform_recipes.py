#!/usr/bin/env python3
"""Cabin-corridor recipes for fiction Enterprise platforms.

Informed guesses at cruise-class (or denser) resolution — see
``docs/ENTERPRISE_CABIN_REVISION.md``.
"""

from __future__ import annotations

from typing import Any

from cruise_platform_recipes import (
    CorridorRecipe,
    CruisePlatformRecipe,
    HvacGroupRecipe,
    PublicZoneRecipe,
    crew_zone_id,
    pax_zone_id,
)


def _interior(_d: int, _s: str, _sec: str) -> str:
    return "interior_hvac"


def _galaxy_family_vent(deck: int, side: str, section: str) -> str:
    # Inner-facing family rings look onto civic voids.
    if section == "Fwd" and deck >= 24:
        return "atrium_view"
    return "interior_hvac"


# --- Constitution public zones -------------------------------------------------

def _tos_public() -> tuple[PublicZoneRecipe, ...]:
    return (
        PublicZoneRecipe("Bridge", "Free", "low", 220, "saucer_1", 12, {"x": 200, "y": 8}, "Main bridge (sealed command volume)."),
        PublicZoneRecipe("BriefRoom", "Free", "low", 120, "saucer_1", 20, {"x": 185, "y": 10}, "Bridge briefing / ready room."),
        PublicZoneRecipe("Comms", "Free", "low", 110, "saucer_2", 10, {"x": 190, "y": 16}, "Subspace communications."),
        PublicZoneRecipe("Library", "Free", "low", 150, "saucer_2", 16, {"x": 170, "y": 18}, "Library / records."),
        PublicZoneRecipe("Sickbay", "Medical", "low", 200, "saucer_3", 16, {"x": 150, "y": 24}, "Primary sickbay ward."),
        PublicZoneRecipe("IsolBay1", "Medical", "low", 60, "saucer_3", 2, {"x": 160, "y": 26}, "Isolation bay 1 (negative pressure)."),
        PublicZoneRecipe("IsolBay2", "Medical", "low", 60, "saucer_3", 2, {"x": 165, "y": 26}, "Isolation bay 2 (negative pressure)."),
        PublicZoneRecipe("Science1", "Free", "low", 180, "saucer_4", 20, {"x": 140, "y": 30}, "Science lab A."),
        PublicZoneRecipe("Science2", "Free", "low", 160, "saucer_4", 18, {"x": 155, "y": 32}, "Science lab B."),
        PublicZoneRecipe("Transprt1", "Free", "low", 90, "saucer_4", 8, {"x": 130, "y": 34}, "Personnel transporter room 1."),
        PublicZoneRecipe("Transprt2", "Free", "low", 90, "saucer_5", 8, {"x": 125, "y": 38}, "Personnel transporter room 2."),
        PublicZoneRecipe("Security", "Free", "low", 100, "saucer_5", 12, {"x": 145, "y": 40}, "Security office."),
        PublicZoneRecipe("Brig", "Room", "low", 80, "saucer_5", 6, {"x": 155, "y": 42}, "Brig cells."),
        PublicZoneRecipe("RecDeck", "Dining", "high", 380, "saucer_6", 80, {"x": 100, "y": 20}, "Recreation / crew lounge."),
        PublicZoneRecipe("Gym", "Free", "medium", 160, "saucer_6", 30, {"x": 115, "y": 22}, "Physical training."),
        PublicZoneRecipe("Galley", "Dining", "high", 160, "saucer_6", 25, {"x": 90, "y": 24}, "Ship's galley (high exhaust)."),
        PublicZoneRecipe("MessHall", "Dining", "high", 280, "saucer_6", 100, {"x": 80, "y": 26}, "Crew mess."),
        PublicZoneRecipe("HeadsMain", "Free", "medium", 90, "saucer_5", 20, {"x": 110, "y": 36}, "Public heads near living ring."),
        PublicZoneRecipe("StoresDry", "Free", "low", 220, "saucer_7", 8, {"x": 70, "y": 44}, "Dry stores."),
        PublicZoneRecipe("StoresCold", "Free", "low", 140, "saucer_7", 4, {"x": 85, "y": 46}, "Cold stores."),
        PublicZoneRecipe("Armory", "Room", "low", 100, "saucer_7", 6, {"x": 95, "y": 48}, "Armory."),
        PublicZoneRecipe("NeckHub", "Free", "medium", 180, "neck", 20, {"x": 60, "y": 55}, "Saucer↔secondary neck / turbolift transfer."),
        PublicZoneRecipe("EngMain", "Engineering", "high", 400, "secondary_1", 40, {"x": 45, "y": 62}, "Main engineering."),
        PublicZoneRecipe("WarpCore", "Engineering", "medium", 320, "secondary_1", 12, {"x": 35, "y": 65}, "Warp core chamber."),
        PublicZoneRecipe("EPSDist", "Engineering", "medium", 200, "secondary_2", 15, {"x": 50, "y": 70}, "EPS distribution."),
        PublicZoneRecipe("Jefferies", "Free", "low", 120, "secondary_2", 8, {"x": 55, "y": 72}, "Jefferies tube nexus."),
        PublicZoneRecipe("Airlock", "Free", "low", 70, "secondary_2", 4, {"x": 40, "y": 74}, "Hull airlock / EVA."),
    )


def _tos_adjacency() -> tuple[dict[str, str], ...]:
    links: list[dict[str, str]] = [
        {"from": "Bridge", "to": "BriefRoom", "type": "pocket_door"},
        {"from": "Bridge", "to": "Comms", "type": "turbolift"},
        {"from": "BriefRoom", "to": "Library", "type": "pocket_door"},
        {"from": "Sickbay", "to": "IsolBay1", "type": "pocket_door"},
        {"from": "Sickbay", "to": "IsolBay2", "type": "pocket_door"},
        {"from": "Sickbay", "to": "Security", "type": "pocket_door"},
        {"from": "Science1", "to": "Science2", "type": "pocket_door"},
        {"from": "Science1", "to": "Transprt1", "type": "pocket_door"},
        {"from": "Transprt1", "to": "Transprt2", "type": "turbolift"},
        {"from": "Security", "to": "Brig", "type": "pocket_door"},
        {"from": "RecDeck", "to": "Gym", "type": "pocket_door"},
        {"from": "RecDeck", "to": "MessHall", "type": "pocket_door"},
        {"from": "Galley", "to": "MessHall", "type": "service_hatch"},
        {"from": "MessHall", "to": "HeadsMain", "type": "pocket_door"},
        {"from": "StoresDry", "to": "StoresCold", "type": "pocket_door"},
        {"from": "StoresDry", "to": "Galley", "type": "service_corridor"},
        {"from": "Armory", "to": "Security", "type": "turbolift"},
        {"from": "NeckHub", "to": "EngMain", "type": "connecting_tube"},
        {"from": "NeckHub", "to": "StoresDry", "type": "pressure_bulkhead"},
        {"from": "EngMain", "to": "WarpCore", "type": "pressure_bulkhead"},
        {"from": "EngMain", "to": "EPSDist", "type": "pocket_door"},
        {"from": "EPSDist", "to": "Jefferies", "type": "service_corridor"},
        {"from": "Jefferies", "to": "Airlock", "type": "hatch"},
        {"from": "Bridge", "to": "NeckHub", "type": "turbolift"},
        {"from": "Sickbay", "to": "EC_D4_P_F", "type": "pocket_door"},
        {"from": "RecDeck", "to": "EC_D6_P_F", "type": "pocket_door"},
        {"from": "MessHall", "to": "EC_D6_S_F", "type": "pocket_door"},
        {"from": "HeadsMain", "to": "EC_D5_P_A", "type": "pocket_door"},
        {"from": "OC_D5_F", "to": "Bridge", "type": "turbolift"},
        {"from": "OC_D6_M", "to": "Library", "type": "pocket_door"},
        {"from": "EC_D4_S_A", "to": "NeckHub", "type": "turbolift"},
    ]

    for deck in (4, 5, 6):
        for side in ("Port", "Stbd"):
            links.append({
                "from": pax_zone_id(deck, side, "Fwd", prefix="EC"),
                "to": pax_zone_id(deck, side, "Aft", prefix="EC"),
                "type": "corridor",
            })
        links.append({
            "from": pax_zone_id(deck, "Port", "Fwd", prefix="EC"),
            "to": pax_zone_id(deck, "Stbd", "Fwd", prefix="EC"),
            "type": "pocket_door",
        })
        if deck < 6:
            links.append({
                "from": pax_zone_id(deck, "Port", "Fwd", prefix="EC"),
                "to": pax_zone_id(deck + 1, "Port", "Fwd", prefix="EC"),
                "type": "turbolift",
            })
    for deck in (5, 6):
        secs = ["Fwd", "Mid", "Aft"]
        for a, b in zip(secs, secs[1:]):
            links.append({
                "from": crew_zone_id(deck, a, prefix="OC"),
                "to": crew_zone_id(deck, b, prefix="OC"),
                "type": "pocket_door",
            })
    links.append({
        "from": crew_zone_id(5, "Mid", prefix="OC"),
        "to": crew_zone_id(6, "Mid", prefix="OC"),
        "type": "turbolift",
    })
    return tuple(links)


CONSTITUTION_TOS = CruisePlatformRecipe(
    platform_id="enterprise_constitution_tos",
    description=(
        "Constitution-class heavy cruiser (NCC-1701 era), cabin-corridor resolution. "
        "Informed fiction ECLSS: ~430 crew, pocket-door adjacency, saucer/secondary "
        "pressure domains, medical HEPA island, engineering high-ACH. See "
        "docs/ENTERPRISE_CABIN_REVISION.md."
    ),
    length_m=289.0,
    beam_m=127.0,
    population=430,
    graywater_zones=("EngMain",),
    pax_corridors=CorridorRecipe(
        decks=(4, 5, 6),
        sides=("Port", "Stbd"),
        sections=("Fwd", "Aft"),
        max_occupancy=32,
        volume_m3=480.0,
        cabin_size=2,
        traffic="medium",
        deck_label="saucer_{deck}",
        ventilation=_interior,
        description_template=(
            "Enlisted cabin corridor, saucer deck {deck} {side} {section}. "
            "~16 cabins, ventilation={vent}."
        ),
        id_prefix="EC",
    ),
    crew_corridors=CorridorRecipe(
        decks=(5, 6),
        sides=(),
        sections=("Fwd", "Mid", "Aft"),
        max_occupancy=14,
        volume_m3=280.0,
        cabin_size=1,
        traffic="low",
        deck_label="saucer_{deck}",
        ventilation=_interior,
        description_template=(
            "Officer stateroom corridor, saucer deck {deck} {section}. "
            "Mostly single occupancy, ventilation={vent}."
        ),
        id_prefix="OC",
    ),
    public_zones=_tos_public(),
    public_hvac=(
        HvacGroupRecipe("AHU_Command", ("Bridge", "BriefRoom", "Comms", "Library"), 10.0, "Command spaces."),
        HvacGroupRecipe("AHU_Ops", ("Science1", "Science2", "Transprt1", "Transprt2", "Security", "Brig", "NeckHub"), 9.0, "Ops / transporters / security."),
        HvacGroupRecipe("AHU_Living", ("RecDeck", "Gym", "MessHall", "HeadsMain"), 8.0, "Living / recreation."),
        HvacGroupRecipe("AHU_Medical", ("Sickbay", "IsolBay1", "IsolBay2"), 12.0, "Sickbay HEPA island."),
        HvacGroupRecipe("AHU_Service", ("Galley", "StoresDry", "StoresCold", "Armory"), 15.0, "Galley exhaust + stores."),
        HvacGroupRecipe("AHU_Engineering", ("EngMain", "WarpCore", "EPSDist", "Jefferies", "Airlock"), 16.0, "Secondary-hull engineering."),
        HvacGroupRecipe("AHU_OC", (), 7.0, "Officer corridors (filled by generator merge)."),
    ),
    auto_pax_ahu=True,
    auto_crew_ahu=False,
    crew_ahu_merged=True,  # reuse AHU_Crew pattern — but we named AHU_OC
    pax_ahu_prefix="AHU_EC_D",
    pax_ahu_ach=7.0,
    pax_trunk_m3h=600.0,
    cabin_relief_m3h=400.0,
    cabin_relief_target_ahu="AHU_Living",
    oa_fraction=0.15,
    hvac_duty=0.5,
    isolation_unit_capacity=8,
    cross_zone_links=(
        {
            "from": "AHU_Command",
            "to": "AHU_Ops",
            "flow_rate_m3h": 200.0,
            "is_hvac_ducted": True,
            "path": "Saucer_Cmd_Ops_Trunk",
        },
        {
            "from": "AHU_Living",
            "to": "AHU_Engineering",
            "flow_rate_m3h": 120.0,
            "is_hvac_ducted": True,
            "path": "Neck_Trunk_Throttled",
        },
        {
            "from": "AHU_Medical",
            "to": "AHU_Ops",
            "flow_rate_m3h": 80.0,
            "is_hvac_ducted": False,
            "path": "Sickbay_Door_Leakage",
        },
        {
            "from": "Galley",
            "to": "MessHall",
            "flow_rate_m3h": 5000.0,
            "is_hvac_ducted": False,
            "path": "Galley_Service_Exhaust",
        },
        {
            "from": "AHU_Engineering",
            "to": "AHU_Service",
            "flow_rate_m3h": 150.0,
            "is_hvac_ducted": True,
            "path": "Eng_to_Stores_Service",
        },
    ),
    adjacency=_tos_adjacency(),
    pax_deck_y={4: 34.0, 5: 28.0, 6: 20.0},
    crew_deck_y={5: 26.0, 6: 18.0},
    side_x={"Port": 160.0, "Stbd": 160.0},
)


# Fix Constitution: crew_ahu_merged looks for AHU_Crew id specifically.
# Patch CONSTITUTION to use AHU_Crew name for officer merge.
def _fix_tos_officer_ahu() -> CruisePlatformRecipe:
    pubs = list(CONSTITUTION_TOS.public_hvac)
    pubs = [g for g in pubs if g.id != "AHU_OC"]
    pubs.append(HvacGroupRecipe("AHU_Crew", (), 7.0, "Officer corridors."))
    return CruisePlatformRecipe(
        **{
            **CONSTITUTION_TOS.__dict__,
            "public_hvac": tuple(pubs),
            "crew_ahu_merged": True,
            "auto_crew_ahu": False,
        }
    )


CONSTITUTION_TOS = _fix_tos_officer_ahu()


# --- Galaxy -------------------------------------------------------------------

def _tng_public() -> tuple[PublicZoneRecipe, ...]:
    return (
        PublicZoneRecipe("Bridge", "Free", "low", 280, "saucer_1", 16, {"x": 280, "y": 6}, "Main bridge."),
        PublicZoneRecipe("BriefRoom", "Free", "low", 140, "saucer_1", 20, {"x": 265, "y": 8}, "Ready room / briefing."),
        PublicZoneRecipe("Comms", "Free", "low", 120, "saucer_2", 12, {"x": 270, "y": 12}, "Communications."),
        PublicZoneRecipe("TenFwd", "Dining", "high", 420, "saucer_10", 120, {"x": 90, "y": 8}, "Ten Forward lounge."),
        PublicZoneRecipe("Arboretum", "Free", "medium", 500, "saucer_14", 80, {"x": 110, "y": 22}, "Arboretum multi-deck void."),
        PublicZoneRecipe("Holodeck1", "Free", "medium", 260, "saucer_9", 40, {"x": 130, "y": 18}, "Holodeck complex A."),
        PublicZoneRecipe("Holodeck2", "Free", "medium", 260, "saucer_11", 40, {"x": 140, "y": 20}, "Holodeck complex B."),
        PublicZoneRecipe("School", "Free", "medium", 200, "saucer_16", 40, {"x": 150, "y": 28}, "Schoolroom."),
        PublicZoneRecipe("CrewLounge", "Free", "medium", 240, "saucer_15", 60, {"x": 160, "y": 24}, "Crew lounge."),
        PublicZoneRecipe("StellarCart", "Free", "low", 180, "saucer_15", 16, {"x": 175, "y": 26}, "Stellar cartography."),
        PublicZoneRecipe("Sickbay", "Medical", "medium", 320, "saucer_12", 30, {"x": 200, "y": 20}, "Sickbay ward."),
        PublicZoneRecipe("IsolBay1", "Medical", "low", 70, "saucer_12", 2, {"x": 210, "y": 22}, "Isolation 1."),
        PublicZoneRecipe("IsolBay2", "Medical", "low", 70, "saucer_12", 2, {"x": 215, "y": 22}, "Isolation 2."),
        PublicZoneRecipe("IsolBay3", "Medical", "low", 70, "saucer_12", 2, {"x": 220, "y": 22}, "Isolation 3."),
        PublicZoneRecipe("Science1", "Free", "low", 220, "saucer_13", 24, {"x": 190, "y": 30}, "Science labs A."),
        PublicZoneRecipe("Science2", "Free", "low", 200, "saucer_13", 20, {"x": 205, "y": 32}, "Science labs B."),
        PublicZoneRecipe("Transprt1", "Free", "low", 100, "saucer_6", 10, {"x": 180, "y": 36}, "Transporter 1."),
        PublicZoneRecipe("Transprt2", "Free", "low", 100, "saucer_6", 10, {"x": 190, "y": 38}, "Transporter 2."),
        PublicZoneRecipe("Security", "Free", "low", 120, "saucer_7", 14, {"x": 170, "y": 40}, "Security."),
        PublicZoneRecipe("Brig", "Room", "low", 90, "saucer_7", 8, {"x": 180, "y": 42}, "Brig."),
        PublicZoneRecipe("Galley", "Dining", "high", 220, "saucer_8", 40, {"x": 120, "y": 34}, "Main galley."),
        PublicZoneRecipe("MessHall", "Dining", "high", 360, "saucer_8", 140, {"x": 100, "y": 36}, "Crew mess."),
        PublicZoneRecipe("HeadsMain", "Free", "medium", 110, "saucer_8", 30, {"x": 135, "y": 38}, "Public heads."),
        PublicZoneRecipe("Gym", "Free", "medium", 200, "saucer_9", 40, {"x": 115, "y": 16}, "Gym."),
        PublicZoneRecipe("StoresDry", "Free", "low", 280, "saucer_17", 10, {"x": 80, "y": 48}, "Dry stores."),
        PublicZoneRecipe("StoresCold", "Free", "low", 180, "saucer_17", 6, {"x": 95, "y": 50}, "Cold stores."),
        PublicZoneRecipe("Armory", "Room", "low", 120, "saucer_17", 8, {"x": 105, "y": 52}, "Armory."),
        PublicZoneRecipe("NeckHub", "Free", "medium", 240, "neck", 30, {"x": 70, "y": 58}, "Saucer↔drive neck hub."),
        PublicZoneRecipe("MainEng", "Engineering", "high", 520, "drive_1", 50, {"x": 50, "y": 68}, "Main engineering."),
        PublicZoneRecipe("WarpCore", "Engineering", "medium", 400, "drive_1", 16, {"x": 40, "y": 70}, "Warp core."),
        PublicZoneRecipe("EPSDist", "Engineering", "medium", 240, "drive_2", 18, {"x": 55, "y": 74}, "EPS distribution."),
        PublicZoneRecipe("Jefferies", "Free", "low", 140, "drive_2", 10, {"x": 60, "y": 76}, "Jefferies nexus."),
        PublicZoneRecipe("Deflector", "Engineering", "medium", 300, "drive_3", 12, {"x": 45, "y": 80}, "Main deflector control."),
        PublicZoneRecipe("ShuttleBay", "Free", "high", 800, "drive_3", 60, {"x": 30, "y": 78}, "Shuttlebay (sealed to space)."),
        PublicZoneRecipe("CargoMain", "Free", "medium", 450, "drive_4", 20, {"x": 55, "y": 84}, "Main cargo."),
        PublicZoneRecipe("CargoAux", "Free", "low", 300, "drive_4", 12, {"x": 65, "y": 86}, "Aux cargo."),
        PublicZoneRecipe("Airlock", "Free", "low", 80, "drive_4", 4, {"x": 35, "y": 88}, "EVA airlock."),
    )


def _tng_adjacency() -> tuple[dict[str, str], ...]:
    links: list[dict[str, str]] = [
        {"from": "Bridge", "to": "BriefRoom", "type": "pocket_door"},
        {"from": "Bridge", "to": "Comms", "type": "turbolift"},
        {"from": "TenFwd", "to": "Arboretum", "type": "multi_deck_void"},
        {"from": "Holodeck1", "to": "Gym", "type": "pocket_door"},
        {"from": "Holodeck2", "to": "CrewLounge", "type": "pocket_door"},
        {"from": "CrewLounge", "to": "School", "type": "pocket_door"},
        {"from": "CrewLounge", "to": "StellarCart", "type": "pocket_door"},
        {"from": "Sickbay", "to": "IsolBay1", "type": "pocket_door"},
        {"from": "Sickbay", "to": "IsolBay2", "type": "pocket_door"},
        {"from": "Sickbay", "to": "IsolBay3", "type": "pocket_door"},
        {"from": "Science1", "to": "Science2", "type": "pocket_door"},
        {"from": "Transprt1", "to": "Transprt2", "type": "pocket_door"},
        {"from": "Security", "to": "Brig", "type": "pocket_door"},
        {"from": "Galley", "to": "MessHall", "type": "service_hatch"},
        {"from": "MessHall", "to": "HeadsMain", "type": "pocket_door"},
        {"from": "StoresDry", "to": "StoresCold", "type": "pocket_door"},
        {"from": "StoresDry", "to": "Galley", "type": "service_corridor"},
        {"from": "NeckHub", "to": "MainEng", "type": "connecting_tube"},
        {"from": "NeckHub", "to": "StoresDry", "type": "pressure_bulkhead"},
        {"from": "MainEng", "to": "WarpCore", "type": "pressure_bulkhead"},
        {"from": "MainEng", "to": "EPSDist", "type": "pocket_door"},
        {"from": "EPSDist", "to": "Jefferies", "type": "service_corridor"},
        {"from": "Jefferies", "to": "Deflector", "type": "service_corridor"},
        {"from": "ShuttleBay", "to": "Airlock", "type": "hatch"},
        {"from": "ShuttleBay", "to": "CargoMain", "type": "pressure_bulkhead"},
        {"from": "CargoMain", "to": "CargoAux", "type": "pocket_door"},
        {"from": "TenFwd", "to": "EC_D10_P_F", "type": "pocket_door"},
        {"from": "Arboretum", "to": "FC_D24_P_F", "type": "pocket_door"},
        {"from": "Sickbay", "to": "EC_D12_S_M", "type": "pocket_door"},
        {"from": "MessHall", "to": "EC_D8_P_A", "type": "pocket_door"},
        {"from": "OC_D8_F", "to": "Bridge", "type": "turbolift"},
        {"from": "EC_D7_S_A", "to": "NeckHub", "type": "turbolift"},
        {"from": "FC_D25_S_A", "to": "School", "type": "pocket_door"},
    ]
    for deck in range(7, 13):
        for side in ("Port", "Stbd"):
            for a, b in (("Fwd", "Mid"), ("Mid", "Aft")):
                links.append({
                    "from": pax_zone_id(deck, side, a, prefix="EC"),
                    "to": pax_zone_id(deck, side, b, prefix="EC"),
                    "type": "corridor",
                })
        links.append({
            "from": pax_zone_id(deck, "Port", "Mid", prefix="EC"),
            "to": pax_zone_id(deck, "Stbd", "Mid", prefix="EC"),
            "type": "pocket_door",
        })
        if deck < 12:
            links.append({
                "from": pax_zone_id(deck, "Port", "Mid", prefix="EC"),
                "to": pax_zone_id(deck + 1, "Port", "Mid", prefix="EC"),
                "type": "turbolift",
            })
    for deck in (23, 24, 25):
        for side in ("Port", "Stbd"):
            links.append({
                "from": pax_zone_id(deck, side, "Fwd", prefix="FC"),
                "to": pax_zone_id(deck, side, "Aft", prefix="FC"),
                "type": "corridor",
            })
        links.append({
            "from": pax_zone_id(deck, "Port", "Fwd", prefix="FC"),
            "to": pax_zone_id(deck, "Stbd", "Fwd", prefix="FC"),
            "type": "pocket_door",
        })
        if deck < 25:
            links.append({
                "from": pax_zone_id(deck, "Port", "Fwd", prefix="FC"),
                "to": pax_zone_id(deck + 1, "Port", "Fwd", prefix="FC"),
                "type": "turbolift",
            })
    for deck in (8, 9):
        for a, b in (("Fwd", "Mid"), ("Mid", "Aft")):
            links.append({
                "from": crew_zone_id(deck, a, prefix="OC"),
                "to": crew_zone_id(deck, b, prefix="OC"),
                "type": "pocket_door",
            })
    links.append({
        "from": crew_zone_id(8, "Mid", prefix="OC"),
        "to": crew_zone_id(9, "Mid", prefix="OC"),
        "type": "turbolift",
    })
    return tuple(links)


GALAXY_TNG = CruisePlatformRecipe(
    platform_id="enterprise_galaxy_tng",
    description=(
        "Galaxy-class explorer (NCC-1701-D era), cabin-corridor resolution. "
        "Informed fiction ECLSS: enlisted + officer + family suite corridors, "
        "pocket doors, saucer/drive pressure domains, civic voids, medical HEPA, "
        "shuttlebay sealed to space. See docs/ENTERPRISE_CABIN_REVISION.md."
    ),
    length_m=642.0,
    beam_m=463.0,
    population=1000,
    graywater_zones=("MainEng",),
    pax_corridors=CorridorRecipe(
        decks=(7, 8, 9, 10, 11, 12),
        sides=("Port", "Stbd"),
        sections=("Fwd", "Mid", "Aft"),
        max_occupancy=28,
        volume_m3=520.0,
        cabin_size=2,
        traffic="medium",
        deck_label="saucer_{deck}",
        ventilation=_interior,
        description_template=(
            "Enlisted cabin corridor, saucer deck {deck} {side} {section}. "
            "ventilation={vent}."
        ),
        id_prefix="EC",
    ),
    crew_corridors=CorridorRecipe(
        decks=(8, 9),
        sides=(),
        sections=("Fwd", "Mid", "Aft"),
        max_occupancy=12,
        volume_m3=260.0,
        cabin_size=1,
        traffic="low",
        deck_label="saucer_{deck}",
        ventilation=_interior,
        description_template=(
            "Officer stateroom corridor, saucer deck {deck} {section}. "
            "ventilation={vent}."
        ),
        id_prefix="OC",
    ),
    extra_corridors=(
        CorridorRecipe(
            decks=(23, 24, 25),
            sides=("Port", "Stbd"),
            sections=("Fwd", "Aft"),
            max_occupancy=36,
            volume_m3=600.0,
            cabin_size=4,
            traffic="medium",
            deck_label="saucer_{deck}",
            ventilation=_galaxy_family_vent,
            description_template=(
                "Family suite corridor, saucer deck {deck} {side} {section}. "
                "cabin_size=4, ventilation={vent}."
            ),
            id_prefix="FC",
        ),
    ),
    public_zones=_tng_public(),
    public_hvac=(
        HvacGroupRecipe("AHU_Command", ("Bridge", "BriefRoom", "Comms"), 10.0),
        HvacGroupRecipe(
            "AHU_Public",
            ("TenFwd", "Arboretum", "Holodeck1", "Holodeck2", "School",
             "CrewLounge", "StellarCart", "Gym"),
            9.0,
        ),
        HvacGroupRecipe(
            "AHU_Ops",
            ("Science1", "Science2", "Transprt1", "Transprt2", "Security", "Brig", "NeckHub"),
            9.0,
        ),
        HvacGroupRecipe("AHU_Medical", ("Sickbay", "IsolBay1", "IsolBay2", "IsolBay3"), 12.0),
        HvacGroupRecipe("AHU_Service", ("Galley", "MessHall", "HeadsMain", "StoresDry", "StoresCold", "Armory"), 14.0),
        HvacGroupRecipe(
            "AHU_Engineering",
            ("MainEng", "WarpCore", "EPSDist", "Jefferies", "Deflector"),
            16.0,
        ),
        HvacGroupRecipe("AHU_Flight", ("ShuttleBay", "CargoMain", "CargoAux", "Airlock"), 12.0),
        HvacGroupRecipe("AHU_Crew", (), 7.0, "Officer corridors."),
    ),
    auto_pax_ahu=True,
    auto_crew_ahu=False,
    crew_ahu_merged=True,
    pax_ahu_prefix="AHU_EC_D",
    pax_ahu_ach=7.0,
    pax_trunk_m3h=900.0,
    cabin_relief_m3h=500.0,
    cabin_relief_target_ahu="AHU_Public",
    oa_fraction=0.15,
    hvac_duty=0.5,
    isolation_unit_capacity=24,
    cross_zone_links=(
        {
            "from": "AHU_Command",
            "to": "AHU_Ops",
            "flow_rate_m3h": 250.0,
            "is_hvac_ducted": True,
            "path": "Saucer_Cmd_Ops_Trunk",
        },
        {
            "from": "AHU_Public",
            "to": "AHU_Engineering",
            "flow_rate_m3h": 150.0,
            "is_hvac_ducted": True,
            "path": "Neck_Trunk_Throttled",
        },
        {
            "from": "AHU_Medical",
            "to": "AHU_Ops",
            "flow_rate_m3h": 100.0,
            "is_hvac_ducted": False,
            "path": "Sickbay_Door_Leakage",
        },
        {
            "from": "AHU_Flight",
            "to": "AHU_Engineering",
            "flow_rate_m3h": 200.0,
            "is_hvac_ducted": True,
            "path": "Drive_Flight_Trunk",
        },
        {
            "from": "Galley",
            "to": "MessHall",
            "flow_rate_m3h": 8000.0,
            "is_hvac_ducted": False,
            "path": "Galley_Service_Exhaust",
        },
    ),
    adjacency=_tng_adjacency(),
    pax_deck_y={
        7: 42.0, 8: 36.0, 9: 30.0, 10: 24.0, 11: 18.0, 12: 14.0,
        23: 50.0, 24: 46.0, 25: 42.0,
    },
    crew_deck_y={8: 34.0, 9: 28.0},
    side_x={"Port": 220.0, "Stbd": 220.0},
)


RECIPES: dict[str, CruisePlatformRecipe] = {
    CONSTITUTION_TOS.platform_id: CONSTITUTION_TOS,
    GALAXY_TNG.platform_id: GALAXY_TNG,
}
