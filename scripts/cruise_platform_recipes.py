#!/usr/bin/env python3
"""Recipe definitions for cabin-corridor cruise platforms.

Each recipe drives ``generate_cruise_platform_layout.py``. Classic and spirit
recipes are added in stacked follow-up PRs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

_SIDE = {"Port": "P", "Stbd": "S", "Central": "C"}
_POS = {"Fwd": "F", "Mid": "M", "Aft": "A"}


def pax_zone_id(deck: int, side: str, section: str) -> str:
    """Contam-safe ≤15-char passenger corridor id."""
    return f"PC_D{deck}_{_SIDE[side]}_{_POS[section]}"


def crew_zone_id(deck: int, section: str) -> str:
    """Contam-safe ≤15-char crew corridor id."""
    return f"CC_D{deck}_{_POS[section]}"


VentFn = Callable[[int, str, str], str]


@dataclass(frozen=True)
class CorridorRecipe:
    decks: tuple[int, ...]
    sides: tuple[str, ...]
    sections: tuple[str, ...]
    max_occupancy: int
    volume_m3: float
    cabin_size: int
    traffic: str
    deck_label: str  # e.g. "{deck}_Cabins" or "{deck}_Crew"
    ventilation: VentFn
    description_template: str


@dataclass(frozen=True)
class PublicZoneRecipe:
    id: str
    type: str
    traffic: str
    volume_m3: float
    deck: str
    max_occupancy: int
    display: dict[str, float]
    description: str


@dataclass(frozen=True)
class HvacGroupRecipe:
    id: str
    rooms: tuple[str, ...]
    ach: float
    description: str = ""


@dataclass(frozen=True)
class CruisePlatformRecipe:
    platform_id: str
    description: str
    length_m: float
    beam_m: float
    population: int
    graywater_zones: tuple[str, ...]
    pax_corridors: CorridorRecipe
    crew_corridors: CorridorRecipe
    public_zones: tuple[PublicZoneRecipe, ...]
    # Extra HVAC groups beyond auto deck/crew cabin branches.
    # Rooms that are cabin corridors are filled by the generator for
    # AHU_Pax_D* / AHU_Crew* ids listed in auto_* below.
    public_hvac: tuple[HvacGroupRecipe, ...]
    auto_pax_ahu: bool = True
    auto_crew_ahu: bool = True
    # If True, one AHU_Crew covering all crew corridors (expedition).
    # If False, per-deck AHU_Crew_D{n} (classic/spirit).
    crew_ahu_merged: bool = False
    crew_ahu_ach: float = 6.0
    pax_ahu_ach: float = 6.0
    cross_zone_links: tuple[dict[str, Any], ...] = ()
    adjacency: tuple[dict[str, str], ...] = ()
    confinement_isolation_factor: float = 0.05
    corridor_direct_contact_factor: float = 0.15
    # Cross-deck passenger trunk between adjacent pax-deck AHUs (m³/h). 0 = none.
    pax_trunk_m3h: float = 0.0
    crew_trunk_m3h: float = 0.0
    cabin_relief_m3h: float = 0.0
    cabin_relief_target_ahu: str | None = None
    oa_fraction: float = 0.2
    hvac_duty: float = 0.5
    isolation_unit_capacity: int = 0
    # Display layout helpers
    pax_deck_y: dict[int, float] = field(default_factory=dict)
    crew_deck_y: dict[int, float] = field(default_factory=dict)
    side_x: dict[str, float] = field(default_factory=dict)


def _expedition_vent(deck: int, side: str, section: str) -> str:
    # Spec: ~60% balcony (ocean-facing), ~40% interior; no atrium.
    if side in ("Port", "Stbd") and deck >= 5:
        return "balcony_partial"
    return "interior_hvac"


def _expedition_public_zones() -> tuple[PublicZoneRecipe, ...]:
    return (
        PublicZoneRecipe(
            "MainDining", "Dining", "high", 1050.0, "5_Panorama", 300,
            {"x": 40, "y": 40},
            "Main dining room with assigned seating. Deck 5. ~300 seats.",
        ),
        PublicZoneRecipe(
            "BuffetLido", "Dining", "high", 525.0, "7_Sun", 150,
            {"x": 70, "y": 10},
            "Lido buffet (casual). Deck 7. ~150 seats.",
        ),
        PublicZoneRecipe(
            "CrewMess", "Dining", "high", 210.0, "2_Crew", 60,
            {"x": 55, "y": 82},
            "Crew mess. Deck 2. ~60 seats.",
        ),
        PublicZoneRecipe(
            "MainGalley", "Dining", "high", 525.0, "4_Voyager", 40,
            {"x": 35, "y": 55},
            "Main galley (crew-only service). Deck 4.",
        ),
        PublicZoneRecipe(
            "PoolDeck", "Free", "high", 1050.0, "7_Sun", 120,
            {"x": 90, "y": 10},
            "Pool deck, semi-open. Deck 7.",
        ),
        PublicZoneRecipe(
            "ObsLounge", "Free", "medium", 525.0, "7_Sun", 80,
            {"x": 30, "y": 10},
            "Forward observation lounge. Deck 7.",
        ),
        PublicZoneRecipe(
            "TheaterLng", "Free", "high", 1250.0, "5_Panorama", 250,
            {"x": 75, "y": 40},
            "Theater / show lounge (dual purpose). Deck 5.",
        ),
        PublicZoneRecipe(
            "Casino", "Free", "medium", 210.0, "5_Panorama", 40,
            {"x": 105, "y": 40},
            "Small casino. Deck 5.",
        ),
        PublicZoneRecipe(
            "Library", "Free", "low", 105.0, "5_Panorama", 20,
            {"x": 125, "y": 40},
            "Library and card room. Deck 5.",
        ),
        PublicZoneRecipe(
            "Gym", "Free", "medium", 270.0, "6_Explorer", 30,
            {"x": 140, "y": 25},
            "Fitness center. Deck 6.",
        ),
        PublicZoneRecipe(
            "Spa", "Free", "low", 240.0, "6_Explorer", 20,
            {"x": 125, "y": 25},
            "Spa treatment rooms. Deck 6.",
        ),
        PublicZoneRecipe(
            "ExpedLounge", "Free", "medium", 420.0, "6_Explorer", 100,
            {"x": 30, "y": 25},
            "Expedition briefing / lecture lounge. Deck 6.",
        ),
        PublicZoneRecipe(
            "Reception", "Free", "high", 350.0, "4_Voyager", 60,
            {"x": 70, "y": 55},
            "Reception lobby (embarkation / info). Deck 4.",
        ),
        PublicZoneRecipe(
            "Laundry", "Free", "medium", 168.0, "3_Crew", 10,
            {"x": 100, "y": 70},
            "Industrial laundry. Deck 3.",
        ),
        PublicZoneRecipe(
            "Stores", "Free", "low", 420.0, "3_Crew", 5,
            {"x": 120, "y": 70},
            "Provision stores. Deck 3.",
        ),
        PublicZoneRecipe(
            "Engine_Room", "Free", "low", 2520.0, "2_Crew", 15,
            {"x": 50, "y": 88},
            "Main engine room. Deck 2.",
        ),
        PublicZoneRecipe(
            "MedBay", "Medical", "low", 105.0, "4_Voyager", 4,
            {"x": 95, "y": 55},
            "Medical room (~4 beds). Deck 4.",
        ),
    )


def _expedition_adjacency() -> tuple[dict[str, str], ...]:
    links: list[dict[str, str]] = [
        {"from": "ObsLounge", "to": "PoolDeck", "type": "open_deck"},
        {"from": "BuffetLido", "to": "PoolDeck", "type": "doorway"},
        {"from": "Gym", "to": "Spa", "type": "doorway"},
        {"from": "Spa", "to": "ExpedLounge", "type": "passageway"},
        {"from": "MainDining", "to": "TheaterLng", "type": "passageway"},
        {"from": "TheaterLng", "to": "Casino", "type": "doorway"},
        {"from": "Casino", "to": "Library", "type": "passageway"},
        {"from": "MedBay", "to": "Reception", "type": "doorway"},
        {"from": "MainGalley", "to": "MainDining", "type": "service_hatch"},
        {"from": "MainGalley", "to": "CrewMess", "type": "service_stairwell"},
        {"from": "Laundry", "to": "Stores", "type": "service_corridor"},
        {"from": "Stores", "to": "Engine_Room", "type": "service_corridor"},
        {"from": "CrewMess", "to": "Engine_Room", "type": "corridor"},
        {"from": "Reception", "to": "TheaterLng", "type": "stairwell"},
        {"from": "BuffetLido", "to": "MainDining", "type": "stairwell"},
        {"from": "ExpedLounge", "to": "Reception", "type": "stairwell"},
        # Corridor-to-public links (one elevator shaft, two stairwells)
        {"from": "PC_D6_P_F", "to": "Gym", "type": "corridor"},
        {"from": "PC_D6_S_F", "to": "Spa", "type": "corridor"},
        {"from": "PC_D6_P_A", "to": "ExpedLounge", "type": "corridor"},
        {"from": "PC_D5_P_F", "to": "TheaterLng", "type": "corridor"},
        {"from": "PC_D5_S_A", "to": "MainDining", "type": "corridor"},
        {"from": "PC_D4_P_F", "to": "Reception", "type": "corridor"},
        {"from": "PC_D4_S_A", "to": "Reception", "type": "corridor"},
        {"from": "CC_D3_F", "to": "Laundry", "type": "corridor"},
        {"from": "CC_D3_A", "to": "Stores", "type": "corridor"},
        {"from": "CC_D2_F", "to": "CrewMess", "type": "corridor"},
        {"from": "CC_D2_A", "to": "Engine_Room", "type": "ladder_well"},
        # Vertical within cabin stacks (single riser, no multi_deck_void)
        {"from": "PC_D4_P_F", "to": "PC_D5_P_F", "type": "stairwell"},
        {"from": "PC_D5_P_F", "to": "PC_D6_P_F", "type": "stairwell"},
        {"from": "PC_D4_S_A", "to": "PC_D5_S_A", "type": "elevator_bank"},
        {"from": "PC_D5_S_A", "to": "PC_D6_S_A", "type": "elevator_bank"},
        {"from": "CC_D2_F", "to": "CC_D3_F", "type": "stairwell"},
        {"from": "CC_D2_A", "to": "CC_D3_A", "type": "stairwell"},
    ]
    # Same-deck corridor chains
    for deck in (4, 5, 6):
        links.append({
            "from": pax_zone_id(deck, "Port", "Fwd"),
            "to": pax_zone_id(deck, "Port", "Aft"),
            "type": "corridor",
        })
        links.append({
            "from": pax_zone_id(deck, "Stbd", "Fwd"),
            "to": pax_zone_id(deck, "Stbd", "Aft"),
            "type": "corridor",
        })
        links.append({
            "from": pax_zone_id(deck, "Port", "Fwd"),
            "to": pax_zone_id(deck, "Stbd", "Fwd"),
            "type": "passageway",
        })
        links.append({
            "from": pax_zone_id(deck, "Port", "Aft"),
            "to": pax_zone_id(deck, "Stbd", "Aft"),
            "type": "passageway",
        })
    links.append({"from": "CC_D2_F", "to": "CC_D2_A", "type": "corridor"})
    links.append({"from": "CC_D3_F", "to": "CC_D3_A", "type": "corridor"})
    return tuple(links)


EXPEDITION_CRUISE_450 = CruisePlatformRecipe(
    platform_id="expedition_cruise_450",
    description=(
        "Small/medium expedition cruise (~300 passengers + ~150 crew = 450). "
        "Silver Cloud / Le Boréal / Viking Star class archetype: ~160m LOA × 21m beam, "
        "~17,000 GT. Cabin-corridor resolution (12 pax + 4 crew corridors). "
        "Supersedes expedition_cruise_300. CDC Small/Medium AGE target 9.06/100K TD "
        "(calibration deferred)."
    ),
    length_m=160.0,
    beam_m=21.0,
    population=450,
    graywater_zones=("Engine_Room",),
    pax_corridors=CorridorRecipe(
        decks=(4, 5, 6),
        sides=("Port", "Stbd"),
        sections=("Fwd", "Aft"),
        max_occupancy=25,
        volume_m3=600.0,
        cabin_size=2,
        traffic="low",
        deck_label="{deck}_Cabins",
        ventilation=_expedition_vent,
        description_template=(
            "Passenger cabin corridor, Deck {deck} {side} {section}. "
            "~12 cabins, ~25 pax, ventilation={vent}."
        ),
    ),
    crew_corridors=CorridorRecipe(
        decks=(2, 3),
        sides=(),  # unused — sections only
        sections=("Fwd", "Aft"),
        max_occupancy=40,
        volume_m3=450.0,
        cabin_size=3,
        traffic="medium",
        deck_label="{deck}_Crew",
        ventilation=lambda d, s, sec: "interior_hvac",
        description_template=(
            "Crew cabin corridor, Deck {deck} {section}. "
            "~20 crew, interior HVAC."
        ),
    ),
    public_zones=_expedition_public_zones(),
    public_hvac=(
        HvacGroupRecipe(
            "AHU_Public_Fwd",
            ("ObsLounge", "TheaterLng", "Casino", "Library", "Reception", "ExpedLounge"),
            8.0,
            "Forward/mid public venues.",
        ),
        HvacGroupRecipe(
            "AHU_Public_Aft",
            ("PoolDeck", "BuffetLido", "Gym", "Spa"),
            8.0,
            "Aft public venues.",
        ),
        HvacGroupRecipe(
            "AHU_Medical",
            ("MedBay",),
            12.0,
            "Dedicated medical AHU (HEPA via Contam overrides).",
        ),
        HvacGroupRecipe(
            "AHU_Service",
            ("MainGalley", "Laundry", "Stores", "Engine_Room"),
            15.0,
            "Service / galley / engine.",
        ),
        HvacGroupRecipe(
            "AHU_Dining",
            ("MainDining",),
            8.0,
            "Main dining room.",
        ),
        # Crew corridors + mess share one AHU (expedition scale)
        HvacGroupRecipe(
            "AHU_Crew",
            (),  # filled by generator with crew corridors + CrewMess
            6.0,
            "Crew corridors and mess.",
        ),
    ),
    auto_pax_ahu=True,
    auto_crew_ahu=False,  # merged into AHU_Crew above
    crew_ahu_merged=True,
    pax_trunk_m3h=0.0,
    crew_trunk_m3h=0.0,
    cabin_relief_m3h=0.0,
    cross_zone_links=(
        {
            "from": "MainDining",
            "to": "MainGalley",
            "flow_rate_m3h": 8000.0,
            "is_hvac_ducted": False,
            "path": "Dining_Galley_Exhaust",
        },
        {
            "from": "AHU_Medical",
            "to": "AHU_Public_Fwd",
            "flow_rate_m3h": 100.0,
            "is_hvac_ducted": False,
            "path": "MedBay_Door_Leakage",
        },
        {
            "from": "AHU_Pax_D4",
            "to": "AHU_Public_Fwd",
            "flow_rate_m3h": 400.0,
            "is_hvac_ducted": True,
            "path": "Single_Vertical_Riser",
        },
        {
            "from": "BuffetLido",
            "to": "PoolDeck",
            "flow_rate_m3h": 400.0,
            "is_hvac_ducted": False,
            "path": "Lido_Open_Doorway",
        },
    ),
    adjacency=_expedition_adjacency(),
    pax_deck_y={4: 55.0, 5: 40.0, 6: 25.0},
    crew_deck_y={2: 85.0, 3: 70.0},
    side_x={"Port": 110.0, "Stbd": 110.0},
)


def _classic_vent(deck: int, side: str, section: str) -> str:
    # ~50% balcony / ~30% interior / ~20% atrium_view
    if section == "Mid" and deck in (4, 5, 6):
        return "atrium_view"
    if section in ("Fwd", "Aft") and deck >= 5:
        return "balcony_partial"
    if section == "Mid" and deck >= 7:
        return "balcony_partial"
    return "interior_hvac"


def _classic_public_zones() -> tuple[PublicZoneRecipe, ...]:
    return (
        PublicZoneRecipe(
            "MainDining_L", "Dining", "high", 1400.0, "4_Main", 400,
            {"x": 50, "y": 55},
            "Main dining room lower level. Deck 4. ~400 seats.",
        ),
        PublicZoneRecipe(
            "MainDining_U", "Dining", "high", 1400.0, "5_Lounge", 400,
            {"x": 50, "y": 42},
            "Main dining room upper level. Deck 5. ~400 seats.",
        ),
        PublicZoneRecipe(
            "LidoBuffet", "Dining", "high", 1225.0, "9_Lido", 350,
            {"x": 80, "y": 12},
            "Open Lido buffet. Deck 9. ~350 seats.",
        ),
        PublicZoneRecipe(
            "Specialty", "Dining", "medium", 280.0, "5_Lounge", 80,
            {"x": 110, "y": 42},
            "Specialty restaurant. Deck 5. ~80 seats.",
        ),
        PublicZoneRecipe(
            "CrewMess", "Dining", "high", 700.0, "1_Crew", 200,
            {"x": 60, "y": 92},
            "Crew mess. Deck 1. ~200 seats.",
        ),
        PublicZoneRecipe(
            "MainGalley", "Dining", "high", 900.0, "4_Main", 60,
            {"x": 30, "y": 55},
            "Main galley (crew-only). Deck 4.",
        ),
        PublicZoneRecipe(
            "PoolDeck", "Free", "high", 2100.0, "9_Lido", 400,
            {"x": 120, "y": 12},
            "Pool deck. Deck 9.",
        ),
        PublicZoneRecipe(
            "Promenade", "Free", "high", 1800.0, "5_Lounge", 300,
            {"x": 90, "y": 42},
            "Indoor promenade. Deck 5.",
        ),
        PublicZoneRecipe(
            "MainTheater", "Free", "high", 4000.0, "4_Main", 800,
            {"x": 150, "y": 50},
            "Main theater (~800 seats). Decks 4-5.",
        ),
        PublicZoneRecipe(
            "Casino", "Free", "high", 900.0, "5_Lounge", 200,
            {"x": 130, "y": 42},
            "Casino. Deck 5.",
        ),
        PublicZoneRecipe(
            "Library", "Free", "low", 210.0, "7_Cabins", 30,
            {"x": 40, "y": 28},
            "Library. Deck 7.",
        ),
        PublicZoneRecipe(
            "SpaFit", "Free", "medium", 900.0, "9_Lido", 120,
            {"x": 40, "y": 12},
            "Spa and fitness. Deck 9.",
        ),
        PublicZoneRecipe(
            "KidsClub", "Free", "medium", 420.0, "8_Cabins", 60,
            {"x": 40, "y": 20},
            "Kids club. Deck 8.",
        ),
        PublicZoneRecipe(
            "PhotoShops", "Free", "medium", 525.0, "5_Lounge", 80,
            {"x": 160, "y": 42},
            "Photo gallery and shops. Deck 5.",
        ),
        PublicZoneRecipe(
            "Reception", "Free", "high", 1050.0, "4_Main", 150,
            {"x": 90, "y": 55},
            "Reception atrium (2-3 deck void). Deck 4.",
        ),
        PublicZoneRecipe(
            "Laundry", "Free", "medium", 280.0, "1_Crew", 15,
            {"x": 100, "y": 92},
            "Laundry. Deck 1.",
        ),
        PublicZoneRecipe(
            "Engine_Room", "Free", "low", 4200.0, "0_Engine", 20,
            {"x": 70, "y": 105},
            "Engine room. Deck 0.",
        ),
        PublicZoneRecipe(
            "MedCenter", "Medical", "medium", 350.0, "2_Crew", 20,
            {"x": 80, "y": 80},
            "Medical center. Deck 2.",
        ),
        PublicZoneRecipe(
            "IsolRoom", "Medical", "low", 70.0, "2_Crew", 2,
            {"x": 95, "y": 80},
            "Isolation room (~2 beds). Deck 2.",
        ),
    )


def _classic_adjacency() -> tuple[dict[str, str], ...]:
    links: list[dict[str, str]] = [
        {"from": "MainDining_L", "to": "MainDining_U", "type": "stairwell"},
        {"from": "MainDining_L", "to": "MainGalley", "type": "service_hatch"},
        {"from": "MainDining_U", "to": "Specialty", "type": "passageway"},
        {"from": "MainTheater", "to": "Reception", "type": "passageway"},
        {"from": "Reception", "to": "Promenade", "type": "multi_deck_void"},
        {"from": "Promenade", "to": "Casino", "type": "open_front"},
        {"from": "Promenade", "to": "PhotoShops", "type": "open_front"},
        {"from": "Casino", "to": "Specialty", "type": "doorway"},
        {"from": "LidoBuffet", "to": "PoolDeck", "type": "doorway"},
        {"from": "PoolDeck", "to": "SpaFit", "type": "passageway"},
        {"from": "MedCenter", "to": "IsolRoom", "type": "doorway"},
        {"from": "CrewMess", "to": "Laundry", "type": "corridor"},
        {"from": "Laundry", "to": "Engine_Room", "type": "ladder_well"},
        {"from": "KidsClub", "to": "Library", "type": "stairwell"},
        {"from": "Reception", "to": "MainDining_L", "type": "passageway"},
        {"from": "MainGalley", "to": "CrewMess", "type": "service_stairwell"},
        # Public to corridors
        {"from": "PC_D4_P_M", "to": "Reception", "type": "corridor"},
        {"from": "PC_D5_P_M", "to": "Promenade", "type": "corridor"},
        {"from": "PC_D5_S_M", "to": "Casino", "type": "corridor"},
        {"from": "PC_D4_S_F", "to": "MainTheater", "type": "corridor"},
        {"from": "PC_D9_P_A", "to": "PoolDeck", "type": "elevator_bank"},
        {"from": "PC_D9_S_A", "to": "LidoBuffet", "type": "elevator_bank"},
        {"from": "PC_D8_P_F", "to": "KidsClub", "type": "corridor"},
        {"from": "PC_D7_S_F", "to": "Library", "type": "corridor"},
        {"from": "CC_D2_F", "to": "MedCenter", "type": "corridor"},
        {"from": "CC_D1_F", "to": "CrewMess", "type": "corridor"},
        {"from": "CC_D1_A", "to": "Laundry", "type": "corridor"},
        {"from": "CC_D3_F", "to": "CC_D2_F", "type": "stairwell"},
        {"from": "CC_D2_F", "to": "CC_D1_F", "type": "stairwell"},
        {"from": "CC_D3_A", "to": "CC_D2_A", "type": "stairwell"},
        {"from": "CC_D2_A", "to": "CC_D1_A", "type": "stairwell"},
    ]
    for deck in range(4, 10):
        for side in ("Port", "Stbd"):
            links.append({
                "from": pax_zone_id(deck, side, "Fwd"),
                "to": pax_zone_id(deck, side, "Mid"),
                "type": "corridor",
            })
            links.append({
                "from": pax_zone_id(deck, side, "Mid"),
                "to": pax_zone_id(deck, side, "Aft"),
                "type": "corridor",
            })
        links.append({
            "from": pax_zone_id(deck, "Port", "Mid"),
            "to": pax_zone_id(deck, "Stbd", "Mid"),
            "type": "passageway",
        })
        if deck < 9:
            links.append({
                "from": pax_zone_id(deck, "Port", "Mid"),
                "to": pax_zone_id(deck + 1, "Port", "Mid"),
                "type": "elevator_bank",
            })
            links.append({
                "from": pax_zone_id(deck, "Stbd", "Mid"),
                "to": pax_zone_id(deck + 1, "Stbd", "Mid"),
                "type": "stairwell",
            })
    for deck in (1, 2, 3):
        links.append({
            "from": crew_zone_id(deck, "Fwd"),
            "to": crew_zone_id(deck, "Aft"),
            "type": "corridor",
        })
    return tuple(links)


CLASSIC_CRUISE_1900 = CruisePlatformRecipe(
    platform_id="classic_cruise_1900",
    description=(
        "Large classic cruise (~1,350 passengers + ~560 crew = 1,910). "
        "Holland America Veendam / Celebrity Century archetype: ~238m LOA × 32m beam, "
        "~57,000 GT. Cabin-corridor resolution (36 pax + 6 crew corridors). "
        "Key venues: Lido buffet, promenade, multi-deck atrium, kids club, isolation room. "
        "CDC Large AGE target 21.4/100K TD (calibration deferred)."
    ),
    length_m=238.0,
    beam_m=32.0,
    population=1910,
    graywater_zones=("Engine_Room",),
    pax_corridors=CorridorRecipe(
        decks=(4, 5, 6, 7, 8, 9),
        sides=("Port", "Stbd"),
        sections=("Fwd", "Mid", "Aft"),
        max_occupancy=37,
        volume_m3=800.0,
        cabin_size=2,
        traffic="low",
        deck_label="{deck}_Cabins",
        ventilation=_classic_vent,
        description_template=(
            "Passenger cabin corridor, Deck {deck} {side} {section}. "
            "~10 cabins, ~37 pax, ventilation={vent}."
        ),
    ),
    crew_corridors=CorridorRecipe(
        decks=(1, 2, 3),
        sides=(),
        sections=("Fwd", "Aft"),
        max_occupancy=95,
        volume_m3=700.0,
        cabin_size=3,
        traffic="medium",
        deck_label="{deck}_Crew",
        ventilation=lambda d, s, sec: "interior_hvac",
        description_template=(
            "Crew cabin corridor, Deck {deck} {section}. "
            "~95 crew, interior HVAC."
        ),
    ),
    public_zones=_classic_public_zones(),
    public_hvac=(
        HvacGroupRecipe(
            "AHU_Public_Fwd",
            ("MainTheater", "Casino"),
            8.0,
            "Forward public venues.",
        ),
        HvacGroupRecipe(
            "AHU_Public_Mid",
            ("Promenade", "Reception", "PhotoShops", "Library", "KidsClub"),
            8.0,
            "Midship promenade / atrium / shops.",
        ),
        HvacGroupRecipe(
            "AHU_Public_Aft",
            ("PoolDeck", "LidoBuffet", "SpaFit"),
            10.0,
            "Aft pool / buffet / spa.",
        ),
        HvacGroupRecipe(
            "AHU_Dining",
            ("MainDining_L", "MainDining_U", "Specialty"),
            8.0,
            "Main and specialty dining.",
        ),
        HvacGroupRecipe(
            "AHU_Medical",
            ("MedCenter", "IsolRoom"),
            12.0,
            "Medical + isolation.",
        ),
        HvacGroupRecipe(
            "AHU_Service",
            ("MainGalley", "Laundry", "Engine_Room"),
            15.0,
            "Service / galley / engine.",
        ),
        HvacGroupRecipe(
            "AHU_Crew",
            (),
            6.0,
            "Crew corridors and mess.",
        ),
    ),
    auto_pax_ahu=True,
    auto_crew_ahu=False,
    crew_ahu_merged=True,
    pax_trunk_m3h=1200.0,
    crew_trunk_m3h=0.0,
    cabin_relief_m3h=1500.0,
    cabin_relief_target_ahu="AHU_Public_Mid",
    cross_zone_links=(
        {
            "from": "MainDining_L",
            "to": "MainGalley",
            "flow_rate_m3h": 12000.0,
            "is_hvac_ducted": False,
            "path": "Dining_Galley_Exhaust",
        },
        {
            "from": "AHU_Medical",
            "to": "AHU_Public_Mid",
            "flow_rate_m3h": 100.0,
            "is_hvac_ducted": False,
            "path": "Medical_Door_Leakage",
        },
        {
            "from": "LidoBuffet",
            "to": "PoolDeck",
            "flow_rate_m3h": 600.0,
            "is_hvac_ducted": False,
            "path": "Lido_Open_Doorway",
        },
    ),
    adjacency=_classic_adjacency(),
    pax_deck_y={4: 55.0, 5: 45.0, 6: 36.0, 7: 28.0, 8: 20.0, 9: 12.0},
    crew_deck_y={1: 92.0, 2: 80.0, 3: 68.0},
    side_x={"Port": 170.0, "Stbd": 170.0},
)


def _spirit_vent(deck: int, side: str, section: str) -> str:
    # ~55% balcony / ~35% interior / ~10% atrium_view
    if section == "Mid" and deck in (4, 5, 6):
        return "atrium_view"
    if section in ("Fwd", "Aft") and deck >= 5:
        return "balcony_partial"
    return "interior_hvac"


def _spirit_public_zones() -> tuple[PublicZoneRecipe, ...]:
    return (
        PublicZoneRecipe(
            "MainDining_L", "Dining", "high", 1600.0, "4_Main", 500,
            {"x": 55, "y": 58}, "Main dining lower. Deck 4.",
        ),
        PublicZoneRecipe(
            "MainDining_U", "Dining", "high", 1600.0, "5_Lounge", 500,
            {"x": 55, "y": 48}, "Main dining upper. Deck 5.",
        ),
        PublicZoneRecipe(
            "LidoBuffet", "Dining", "high", 1400.0, "10_Lido", 400,
            {"x": 90, "y": 14}, "Lido buffet. Deck 10.",
        ),
        PublicZoneRecipe(
            "PizzaGrill", "Dining", "high", 420.0, "10_Lido", 120,
            {"x": 120, "y": 14}, "Pizzeria / grill quick-service. Deck 10.",
        ),
        PublicZoneRecipe(
            "SpecialtyA", "Dining", "medium", 350.0, "5_Lounge", 80,
            {"x": 120, "y": 48}, "Specialty steakhouse. Deck 5.",
        ),
        PublicZoneRecipe(
            "SpecialtyB", "Dining", "medium", 350.0, "5_Lounge", 80,
            {"x": 140, "y": 48}, "Specialty Italian. Deck 5.",
        ),
        PublicZoneRecipe(
            "SpecialtyC", "Dining", "medium", 350.0, "11_Spa", 80,
            {"x": 40, "y": 8}, "Specialty Asian. Deck 11.",
        ),
        PublicZoneRecipe(
            "CrewMessMain", "Dining", "high", 900.0, "1_Crew", 250,
            {"x": 70, "y": 95}, "Crew mess main. Deck 1.",
        ),
        PublicZoneRecipe(
            "CrewMessOff", "Dining", "medium", 280.0, "2_Crew", 60,
            {"x": 70, "y": 82}, "Officers mess. Deck 2.",
        ),
        PublicZoneRecipe(
            "MainGalley", "Dining", "high", 1100.0, "4_Main", 80,
            {"x": 30, "y": 58}, "Main galley. Deck 4.",
        ),
        PublicZoneRecipe(
            "MainPool", "Free", "high", 2400.0, "10_Lido", 500,
            {"x": 150, "y": 14}, "Main pool deck. Deck 10.",
        ),
        PublicZoneRecipe(
            "AftPool", "Free", "medium", 1200.0, "9_Cabins", 200,
            {"x": 180, "y": 20}, "Aft pool area. Deck 9.",
        ),
        PublicZoneRecipe(
            "Promenade", "Free", "high", 2100.0, "5_Lounge", 400,
            {"x": 95, "y": 48}, "Promenade. Deck 5.",
        ),
        PublicZoneRecipe(
            "MainTheater", "Free", "high", 5000.0, "4_Main", 1200,
            {"x": 170, "y": 53}, "Main theater (~1,200 seats). Decks 4-5.",
        ),
        PublicZoneRecipe(
            "SmallLounge", "Free", "medium", 525.0, "6_Cabins", 100,
            {"x": 40, "y": 38}, "Lounge. Deck 6.",
        ),
        PublicZoneRecipe(
            "Casino", "Free", "high", 1200.0, "6_Cabins", 250,
            {"x": 160, "y": 38}, "Casino. Deck 6.",
        ),
        PublicZoneRecipe(
            "Library", "Free", "low", 210.0, "7_Cabins", 30,
            {"x": 40, "y": 30}, "Library. Deck 7.",
        ),
        PublicZoneRecipe(
            "SpaFit", "Free", "medium", 1050.0, "11_Spa", 150,
            {"x": 80, "y": 8}, "Spa and fitness. Deck 11.",
        ),
        PublicZoneRecipe(
            "KidsClub", "Free", "high", 525.0, "11_Spa", 80,
            {"x": 110, "y": 8}, "Kids club. Deck 11.",
        ),
        PublicZoneRecipe(
            "TeenZone", "Free", "medium", 420.0, "11_Spa", 60,
            {"x": 130, "y": 8}, "Teen zone. Deck 11.",
        ),
        PublicZoneRecipe(
            "Nightclub", "Free", "medium", 700.0, "3_Crew", 150,
            {"x": 150, "y": 70}, "Nightclub. Deck 3.",
        ),
        PublicZoneRecipe(
            "PhotoShops", "Free", "medium", 600.0, "5_Lounge", 100,
            {"x": 180, "y": 48}, "Photo / shops. Deck 5.",
        ),
        PublicZoneRecipe(
            "Reception", "Free", "high", 1400.0, "4_Main", 200,
            {"x": 100, "y": 58}, "Reception atrium (3-deck void). Deck 4.",
        ),
        PublicZoneRecipe(
            "SportsDeck", "Free", "medium", 1800.0, "12_Sports", 120,
            {"x": 100, "y": 2}, "Sports deck (basketball / jogging). Deck 12.",
        ),
        PublicZoneRecipe(
            "ArtGallery", "Free", "low", 350.0, "6_Cabins", 40,
            {"x": 50, "y": 38}, "Art gallery. Deck 6.",
        ),
        PublicZoneRecipe(
            "Laundry", "Free", "medium", 350.0, "1_Crew", 20,
            {"x": 110, "y": 95}, "Laundry. Deck 1.",
        ),
        PublicZoneRecipe(
            "Engine_Room", "Free", "low", 5000.0, "0_Engine", 25,
            {"x": 80, "y": 108}, "Engine room. Deck 0.",
        ),
        PublicZoneRecipe(
            "MedCenter", "Medical", "medium", 420.0, "2_Crew", 30,
            {"x": 90, "y": 82}, "Medical center. Deck 2.",
        ),
        PublicZoneRecipe(
            "IsolWard", "Medical", "low", 140.0, "2_Crew", 4,
            {"x": 110, "y": 82}, "Isolation ward (~4 beds). Deck 2.",
        ),
    )


def _spirit_adjacency() -> tuple[dict[str, str], ...]:
    links: list[dict[str, str]] = [
        {"from": "MainDining_L", "to": "MainDining_U", "type": "stairwell"},
        {"from": "MainDining_L", "to": "MainGalley", "type": "service_hatch"},
        {"from": "MainDining_U", "to": "SpecialtyA", "type": "passageway"},
        {"from": "SpecialtyA", "to": "SpecialtyB", "type": "doorway"},
        {"from": "Reception", "to": "Promenade", "type": "multi_deck_void"},
        {"from": "Promenade", "to": "Casino", "type": "open_front"},
        {"from": "Promenade", "to": "PhotoShops", "type": "open_front"},
        {"from": "MainTheater", "to": "Reception", "type": "passageway"},
        {"from": "LidoBuffet", "to": "MainPool", "type": "doorway"},
        {"from": "LidoBuffet", "to": "PizzaGrill", "type": "passageway"},
        {"from": "MainPool", "to": "AftPool", "type": "open_deck"},
        {"from": "SpaFit", "to": "KidsClub", "type": "passageway"},
        {"from": "KidsClub", "to": "TeenZone", "type": "doorway"},
        {"from": "SpecialtyC", "to": "SpaFit", "type": "corridor"},
        {"from": "MedCenter", "to": "IsolWard", "type": "doorway"},
        {"from": "CrewMessMain", "to": "Laundry", "type": "corridor"},
        {"from": "Laundry", "to": "Engine_Room", "type": "ladder_well"},
        {"from": "CrewMessOff", "to": "MedCenter", "type": "corridor"},
        {"from": "Nightclub", "to": "CC_D3_A", "type": "corridor"},
        {"from": "ArtGallery", "to": "SmallLounge", "type": "passageway"},
        {"from": "SportsDeck", "to": "SpaFit", "type": "stairwell"},
        {"from": "MainGalley", "to": "CrewMessMain", "type": "service_stairwell"},
        {"from": "PC_D4_P_M", "to": "Reception", "type": "corridor"},
        {"from": "PC_D5_P_M", "to": "Promenade", "type": "corridor"},
        {"from": "PC_D5_S_M", "to": "Casino", "type": "corridor"},
        {"from": "PC_D4_S_F", "to": "MainTheater", "type": "corridor"},
        {"from": "PC_D10_P_A", "to": "MainPool", "type": "elevator_bank"},
        {"from": "PC_D10_S_A", "to": "LidoBuffet", "type": "elevator_bank"},
        {"from": "PC_D11_P_F", "to": "KidsClub", "type": "corridor"},
        {"from": "PC_D9_S_A", "to": "AftPool", "type": "corridor"},
        {"from": "PC_D6_P_F", "to": "SmallLounge", "type": "corridor"},
        {"from": "PC_D7_S_F", "to": "Library", "type": "corridor"},
        {"from": "CC_D1_F", "to": "CrewMessMain", "type": "corridor"},
        {"from": "CC_D1_A", "to": "Laundry", "type": "corridor"},
        {"from": "CC_D2_M", "to": "MedCenter", "type": "corridor"},
        {"from": "CC_D2_F", "to": "CrewMessOff", "type": "corridor"},
    ]
    for deck in range(4, 12):
        for side in ("Port", "Stbd"):
            links.append({
                "from": pax_zone_id(deck, side, "Fwd"),
                "to": pax_zone_id(deck, side, "Mid"),
                "type": "corridor",
            })
            links.append({
                "from": pax_zone_id(deck, side, "Mid"),
                "to": pax_zone_id(deck, side, "Aft"),
                "type": "corridor",
            })
        links.append({
            "from": pax_zone_id(deck, "Port", "Mid"),
            "to": pax_zone_id(deck, "Stbd", "Mid"),
            "type": "passageway",
        })
        if deck < 11:
            links.append({
                "from": pax_zone_id(deck, "Port", "Mid"),
                "to": pax_zone_id(deck + 1, "Port", "Mid"),
                "type": "elevator_bank",
            })
            links.append({
                "from": pax_zone_id(deck, "Stbd", "Mid"),
                "to": pax_zone_id(deck + 1, "Stbd", "Mid"),
                "type": "stairwell",
            })
    for deck in (1, 2, 3):
        links.append({
            "from": crew_zone_id(deck, "Fwd"),
            "to": crew_zone_id(deck, "Mid"),
            "type": "corridor",
        })
        links.append({
            "from": crew_zone_id(deck, "Mid"),
            "to": crew_zone_id(deck, "Aft"),
            "type": "corridor",
        })
        if deck < 3:
            for sec in ("Fwd", "Mid", "Aft"):
                links.append({
                    "from": crew_zone_id(deck, sec),
                    "to": crew_zone_id(deck + 1, sec),
                    "type": "stairwell",
                })
    return tuple(links)


SPIRIT_CRUISE_3000 = CruisePlatformRecipe(
    platform_id="spirit_cruise_3000",
    description=(
        "Extra-large Spirit-class cruise (~2,100 passengers + ~900 crew = 3,000). "
        "Carnival Spirit / HAL Vista / Princess Grand archetype: ~290m LOA × 36m beam, "
        "~86,000 GT. Cabin-corridor resolution (48 pax + 9 crew corridors). "
        "Key venues: 3+ specialty restaurants, second pool, teen zone, sports deck, "
        "nightclub, isolation ward. CDC Extra-Large AGE target 22.1/100K TD "
        "(calibration deferred)."
    ),
    length_m=290.0,
    beam_m=36.0,
    population=3000,
    graywater_zones=("Engine_Room",),
    pax_corridors=CorridorRecipe(
        decks=(4, 5, 6, 7, 8, 9, 10, 11),
        sides=("Port", "Stbd"),
        sections=("Fwd", "Mid", "Aft"),
        max_occupancy=44,
        volume_m3=900.0,
        cabin_size=2,
        traffic="low",
        deck_label="{deck}_Cabins",
        ventilation=_spirit_vent,
        description_template=(
            "Passenger cabin corridor, Deck {deck} {side} {section}. "
            "~10 cabins, ~44 pax, ventilation={vent}."
        ),
    ),
    crew_corridors=CorridorRecipe(
        decks=(1, 2, 3),
        sides=(),
        sections=("Fwd", "Mid", "Aft"),
        max_occupancy=100,
        volume_m3=750.0,
        cabin_size=3,
        traffic="medium",
        deck_label="{deck}_Crew",
        ventilation=lambda d, s, sec: "interior_hvac",
        description_template=(
            "Crew cabin corridor, Deck {deck} {section}. "
            "~100 crew, interior HVAC."
        ),
    ),
    public_zones=_spirit_public_zones(),
    public_hvac=(
        HvacGroupRecipe(
            "AHU_Public_Fwd",
            ("MainTheater", "Casino", "Nightclub"),
            8.0,
            "Forward / entertainment.",
        ),
        HvacGroupRecipe(
            "AHU_Public_Mid",
            ("Promenade", "Reception", "PhotoShops", "Library", "SmallLounge", "ArtGallery"),
            8.0,
            "Midship promenade / atrium.",
        ),
        HvacGroupRecipe(
            "AHU_Public_Aft",
            ("MainPool", "AftPool", "LidoBuffet", "PizzaGrill", "SpaFit",
             "KidsClub", "TeenZone", "SpecialtyC", "SportsDeck"),
            10.0,
            "Aft pools / buffet / spa / sports.",
        ),
        HvacGroupRecipe(
            "AHU_Dining",
            ("MainDining_L", "MainDining_U", "SpecialtyA", "SpecialtyB",
             "CrewMessMain", "CrewMessOff"),
            8.0,
            "Dining venues including crew messes.",
        ),
        HvacGroupRecipe(
            "AHU_Medical",
            ("MedCenter", "IsolWard"),
            12.0,
            "Medical + isolation ward.",
        ),
        HvacGroupRecipe(
            "AHU_Service",
            ("MainGalley", "Laundry", "Engine_Room"),
            15.0,
            "Service / galley / engine.",
        ),
    ),
    auto_pax_ahu=True,
    auto_crew_ahu=True,
    crew_ahu_merged=False,
    crew_ahu_ach=6.0,
    pax_trunk_m3h=1200.0,
    crew_trunk_m3h=800.0,
    cabin_relief_m3h=1500.0,
    cabin_relief_target_ahu="AHU_Public_Mid",
    cross_zone_links=(
        {
            "from": "MainDining_L",
            "to": "MainGalley",
            "flow_rate_m3h": 15000.0,
            "is_hvac_ducted": False,
            "path": "Dining_Galley_Exhaust",
        },
        {
            "from": "AHU_Medical",
            "to": "AHU_Public_Mid",
            "flow_rate_m3h": 100.0,
            "is_hvac_ducted": False,
            "path": "Medical_Door_Leakage",
        },
        {
            "from": "LidoBuffet",
            "to": "MainPool",
            "flow_rate_m3h": 800.0,
            "is_hvac_ducted": False,
            "path": "Lido_Open_Doorway",
        },
    ),
    adjacency=_spirit_adjacency(),
    pax_deck_y={
        4: 58.0, 5: 48.0, 6: 38.0, 7: 30.0, 8: 24.0, 9: 18.0, 10: 12.0, 11: 6.0,
    },
    crew_deck_y={1: 95.0, 2: 82.0, 3: 70.0},
    side_x={"Port": 200.0, "Stbd": 200.0},
)


RECIPES: dict[str, CruisePlatformRecipe] = {
    EXPEDITION_CRUISE_450.platform_id: EXPEDITION_CRUISE_450,
    CLASSIC_CRUISE_1900.platform_id: CLASSIC_CRUISE_1900,
    SPIRIT_CRUISE_3000.platform_id: SPIRIT_CRUISE_3000,
}

