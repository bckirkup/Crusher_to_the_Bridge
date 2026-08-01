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


RECIPES: dict[str, CruisePlatformRecipe] = {
    EXPEDITION_CRUISE_450.platform_id: EXPEDITION_CRUISE_450,
}
