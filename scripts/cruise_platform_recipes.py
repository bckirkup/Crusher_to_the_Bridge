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


def pax_zone_id(deck: int, side: str, section: str, *, prefix: str = "PC") -> str:
    """Contam-safe ≤15-char grid corridor id (deck × side × section)."""
    zid = f"{prefix}_D{deck}_{_SIDE[side]}_{_POS[section]}"
    assert len(zid) <= 15, zid
    return zid


def crew_zone_id(deck: int, section: str, *, prefix: str = "CC") -> str:
    """Contam-safe ≤15-char linear corridor id (deck × section)."""
    zid = f"{prefix}_D{deck}_{_POS[section]}"
    assert len(zid) <= 15, zid
    return zid


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
    id_prefix: str = "PC"  # PC/CC cruise; EC/OC/FC starship
    # Per-agent-class berth override (BERTH-01); emitted verbatim when set.
    cabin_size_by_class: dict[str, int] | None = None


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
    # Dining venue fields (SEAT-01/02); emitted only when set.
    dining_service_type: str | None = None
    food_contamination_multiplier: float | None = None
    meal_seatings: int | None = None


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
    exterior_zones: tuple[str, ...] = ()
    # Berth declaration (nominal_complement). The VSP rule scores passenger
    # and crew denominators separately, so hulls that sail scored voyages
    # declare both; None emits no key (Enterprise hulls carry none).
    nominal_complement: dict[str, int] | None = None
    # Optional additional cabin-corridor banks (e.g. Galaxy family suites).
    extra_corridors: tuple[CorridorRecipe, ...] = ()
    auto_pax_ahu: bool = True
    auto_crew_ahu: bool = True
    # If True, one AHU_Crew covering all crew corridors (expedition).
    # If False, per-deck AHU_Crew_D{n} (classic/spirit).
    crew_ahu_merged: bool = False
    crew_ahu_ach: float = 6.0
    pax_ahu_ach: float = 6.0
    # AHU id prefix for auto pax/crew branches (starships may use AHU_EC_D*).
    pax_ahu_prefix: str = "AHU_Pax_D"
    crew_ahu_prefix: str = "AHU_Crew_D"
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
            dining_service_type="mdr", food_contamination_multiplier=1.0,
            meal_seatings=2,
        ),
        PublicZoneRecipe(
            "CasualDining", "Dining", "high", 525.0, "7_Sun", 150,
            {"x": 70, "y": 10},
            "Casual dining (table service / MDR). Deck 7. ~150 seats.",
            dining_service_type="mdr", food_contamination_multiplier=1.0,
            meal_seatings=2,
        ),
        PublicZoneRecipe(
            "CrewMess", "Dining", "high", 210.0, "2_Crew", 60,
            {"x": 55, "y": 82},
            "Crew mess. Deck 2. ~60 seats.",
            dining_service_type="crew_mess", food_contamination_multiplier=1.0,
            meal_seatings=3,
        ),
        PublicZoneRecipe(
            "MainGalley", "Dining", "high", 525.0, "4_Voyager", 40,
            {"x": 35, "y": 55},
            "Main galley (crew-only service). Deck 4.",
            dining_service_type="galley", food_contamination_multiplier=0.5,
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
        PublicZoneRecipe(
            "Bridge", "Free", "low", 180.0, "8_Bridge", 8,
            {"x": 150, "y": 10},
            "Navigating bridge and chartroom. Deck 8.",
        ),
    )


def _expedition_adjacency() -> tuple[dict[str, str], ...]:
    links: list[dict[str, str]] = [
        {"from": "ObsLounge", "to": "PoolDeck", "type": "open_deck"},
        {"from": "Bridge", "to": "ObsLounge", "type": "passageway"},
        {"from": "CasualDining", "to": "PoolDeck", "type": "doorway"},
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
        {"from": "CasualDining", "to": "MainDining", "type": "stairwell"},
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
    nominal_complement={"passengers": 300, "crew": 150},
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
        id_prefix="PC",
    ),
    crew_corridors=CorridorRecipe(
        decks=(2, 3),
        sides=(),  # unused — sections only
        sections=("Fwd", "Aft"),
        max_occupancy=40,
        volume_m3=450.0,
        cabin_size=2,
        traffic="medium",
        deck_label="{deck}_Crew",
        ventilation=lambda d, s, sec: "interior_hvac",
        description_template=(
            "Crew cabin corridor, Deck {deck} {section}. "
            "~20 crew, interior HVAC."
        ),
        id_prefix="CC",
        cabin_size_by_class={"crew_galley": 3},
    ),
    public_zones=_expedition_public_zones(),
    exterior_zones=("PoolDeck",),
    public_hvac=(
        HvacGroupRecipe(
            "AHU_Public_Fwd",
            ("ObsLounge", "TheaterLng", "Casino", "Library", "Reception", "ExpedLounge",
             "Bridge"),
            8.0,
            "Forward/mid public venues.",
        ),
        HvacGroupRecipe(
            "AHU_Public_Aft",
            ("CasualDining", "Gym", "Spa"),
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
            "from": "CasualDining",
            "to": "PoolDeck",
            "flow_rate_m3h": 400.0,
            "is_hvac_ducted": False,
            "path": "CasualDining_Open_Doorway",
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
            dining_service_type="mdr", food_contamination_multiplier=1.0,
            meal_seatings=2,
        ),
        PublicZoneRecipe(
            "MainDining_U", "Dining", "high", 1400.0, "5_Lounge", 400,
            {"x": 50, "y": 42},
            "Main dining room upper level. Deck 5. ~400 seats.",
            dining_service_type="mdr", food_contamination_multiplier=1.0,
            meal_seatings=2,
        ),
        PublicZoneRecipe(
            "LidoBuffet", "Dining", "high", 1225.0, "9_Lido", 350,
            {"x": 80, "y": 12},
            "Open Lido buffet. Deck 9. ~350 seats.",
            dining_service_type="buffet", food_contamination_multiplier=3.0,
            meal_seatings=2,
        ),
        PublicZoneRecipe(
            "Specialty", "Dining", "medium", 280.0, "5_Lounge", 80,
            {"x": 110, "y": 42},
            "Specialty restaurant. Deck 5. ~80 seats.",
            dining_service_type="specialty", food_contamination_multiplier=0.5,
            meal_seatings=2,
        ),
        PublicZoneRecipe(
            "CrewMess", "Dining", "high", 700.0, "1_Crew", 200,
            {"x": 60, "y": 92},
            "Crew mess. Deck 1. ~200 seats.",
            dining_service_type="crew_mess", food_contamination_multiplier=1.0,
            meal_seatings=4,
        ),
        PublicZoneRecipe(
            "MainGalley", "Dining", "high", 900.0, "4_Main", 60,
            {"x": 30, "y": 55},
            "Main galley (crew-only). Deck 4.",
            dining_service_type="galley", food_contamination_multiplier=0.5,
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
        PublicZoneRecipe(
            "Bridge", "Free", "low", 240.0, "10_Bridge", 10,
            {"x": 150, "y": 8},
            "Navigating bridge and chartroom. Deck 10.",
        ),
    )


def _classic_adjacency() -> tuple[dict[str, str], ...]:
    links: list[dict[str, str]] = [
        {"from": "MainDining_L", "to": "MainDining_U", "type": "stairwell"},
        {"from": "MainDining_L", "to": "MainGalley", "type": "service_hatch"},
        {"from": "MainDining_U", "to": "Specialty", "type": "passageway"},
        {"from": "MainTheater", "to": "Reception", "type": "passageway"},
        {"from": "Bridge", "to": "MainTheater", "type": "passageway"},
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
    nominal_complement={"passengers": 1350, "crew": 560},
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
        id_prefix="PC",
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
        id_prefix="CC",
        cabin_size_by_class={
            "crew_galley": 4, "crew_engineering": 2, "crew_medical": 2,
        },
    ),
    public_zones=_classic_public_zones(),
    exterior_zones=("PoolDeck",),
    public_hvac=(
        HvacGroupRecipe(
            "AHU_Public_Fwd",
            ("MainTheater", "Casino", "Bridge"),
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
            ("LidoBuffet", "SpaFit"),
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
            dining_service_type="mdr", food_contamination_multiplier=1.0,
            meal_seatings=2,
        ),
        PublicZoneRecipe(
            "MainDining_U", "Dining", "high", 1600.0, "5_Lounge", 500,
            {"x": 55, "y": 48}, "Main dining upper. Deck 5.",
            dining_service_type="mdr", food_contamination_multiplier=1.0,
            meal_seatings=2,
        ),
        PublicZoneRecipe(
            "LidoBuffet", "Dining", "high", 1400.0, "10_Lido", 400,
            {"x": 90, "y": 14}, "Lido buffet. Deck 10.",
            dining_service_type="buffet", food_contamination_multiplier=3.0,
            meal_seatings=2,
        ),
        PublicZoneRecipe(
            "PizzaGrill", "Dining", "high", 420.0, "10_Lido", 120,
            {"x": 120, "y": 14}, "Pizzeria / grill quick-service. Deck 10.",
            dining_service_type="buffet", food_contamination_multiplier=3.0,
            meal_seatings=2,
        ),
        PublicZoneRecipe(
            "SpecialtyA", "Dining", "medium", 350.0, "5_Lounge", 80,
            {"x": 120, "y": 48}, "Specialty steakhouse. Deck 5.",
            dining_service_type="specialty", food_contamination_multiplier=0.5,
            meal_seatings=2,
        ),
        PublicZoneRecipe(
            "SpecialtyB", "Dining", "medium", 350.0, "5_Lounge", 80,
            {"x": 140, "y": 48}, "Specialty Italian. Deck 5.",
            dining_service_type="specialty", food_contamination_multiplier=0.5,
            meal_seatings=2,
        ),
        PublicZoneRecipe(
            "SpecialtyC", "Dining", "medium", 350.0, "11_Spa", 80,
            {"x": 40, "y": 8}, "Specialty Asian. Deck 11.",
            dining_service_type="specialty", food_contamination_multiplier=0.5,
            meal_seatings=2,
        ),
        PublicZoneRecipe(
            "CrewMessMain", "Dining", "high", 900.0, "1_Crew", 250,
            {"x": 70, "y": 95}, "Crew mess main. Deck 1.",
            dining_service_type="crew_mess", food_contamination_multiplier=1.0,
            meal_seatings=4,
        ),
        PublicZoneRecipe(
            "CrewMessOff", "Dining", "medium", 280.0, "2_Crew", 60,
            {"x": 70, "y": 82}, "Officers mess. Deck 2.",
            dining_service_type="crew_mess", food_contamination_multiplier=1.0,
            meal_seatings=4,
        ),
        PublicZoneRecipe(
            "MainGalley", "Dining", "high", 1100.0, "4_Main", 80,
            {"x": 30, "y": 58}, "Main galley. Deck 4.",
            dining_service_type="galley", food_contamination_multiplier=0.5,
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
        PublicZoneRecipe(
            "Bridge", "Free", "low", 300.0, "13_Bridge", 12,
            {"x": 150, "y": 6},
            "Navigating bridge and chartroom. Deck 13.",
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
        {"from": "Bridge", "to": "MainTheater", "type": "passageway"},
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
    nominal_complement={"passengers": 2100, "crew": 900},
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
        id_prefix="PC",
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
        id_prefix="CC",
        cabin_size_by_class={"crew_engineering": 2, "crew_medical": 2},
    ),
    public_zones=_spirit_public_zones(),
    exterior_zones=("MainPool", "AftPool", "SportsDeck"),
    public_hvac=(
        HvacGroupRecipe(
            "AHU_Public_Fwd",
            ("MainTheater", "Casino", "Nightclub", "Bridge"),
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
            ("LidoBuffet", "PizzaGrill", "SpaFit", "KidsClub", "TeenZone",
             "SpecialtyC"),
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


def _diamond_vent(deck: int, side: str, section: str) -> str:
    # Princess fact sheet: 976 outside / 377 inside staterooms (~72% / 28%).
    # The Port/Stbd grid carries no Central band, so the outside share is set
    # by deck: decks 10-12 and the forward Lido cabins are balcony-dominant,
    # decks 8-9 split by section, and the lower decks keep interior cabins.
    if deck >= 10 or deck == 14:
        return "balcony_partial"
    if deck in (8, 9):
        return "balcony_partial" if section in ("Fwd", "Aft") else "interior_hvac"
    if deck in (5, 6):
        return "balcony_partial" if section == "Fwd" else "interior_hvac"
    return "interior_hvac"


def _diamond_public_zones() -> tuple[PublicZoneRecipe, ...]:
    return (
        PublicZoneRecipe(
            "MedicalCenter", "Medical", "medium", 350.0, "4_Gala", 20,
            {"x": 110, "y": 62},
            "Medical center. Deck 4 (Gala).",
        ),
        PublicZoneRecipe(
            "IsolWard", "Medical", "low", 140.0, "4_Gala", 4,
            {"x": 130, "y": 62},
            "Isolation ward (~4 beds). Deck 4.",
        ),
        PublicZoneRecipe(
            "GrandPlaza", "Free", "high", 6000.0, "5_Plaza", 800,
            {"x": 118, "y": 56},
            "Grand Plaza atrium (multi-deck void, decks 5-7). Deck 5.",
        ),
        PublicZoneRecipe(
            "Vivaldi", "Dining", "high", 2200.0, "5_Plaza", 380,
            {"x": 188, "y": 56},
            "Vivaldi Dining Room (anytime dining). Deck 5. ~380 seats.",
            dining_service_type="mdr", food_contamination_multiplier=1.0,
            meal_seatings=2,
        ),
        PublicZoneRecipe(
            "Savoy", "Dining", "high", 2200.0, "5_Plaza", 380,
            {"x": 168, "y": 56},
            "Savoy Dining Room (traditional). Deck 5. ~380 seats.",
            dining_service_type="mdr", food_contamination_multiplier=1.0,
            meal_seatings=2,
        ),
        PublicZoneRecipe(
            "MainGalley", "Dining", "high", 1100.0, "5_Plaza", 80,
            {"x": 30, "y": 56},
            "Main galley (crew-only service). Deck 5.",
            dining_service_type="galley", food_contamination_multiplier=0.5,
        ),
        PublicZoneRecipe(
            "TheLibrary", "Free", "low", 180.0, "5_Plaza", 30,
            {"x": 58, "y": 56},
            "The Library. Deck 5.",
        ),
        PublicZoneRecipe(
            "InternetCafe", "Free", "low", 140.0, "5_Plaza", 40,
            {"x": 78, "y": 56},
            "Internet Café (snacks and drinks). Deck 5.",
        ),
        PublicZoneRecipe(
            "FineArts", "Free", "low", 250.0, "5_Plaza", 40,
            {"x": 92, "y": 56},
            "Princess Fine Arts Gallery. Deck 5.",
        ),
        PublicZoneRecipe(
            "GoodSpirits", "Free", "medium", 180.0, "5_Plaza", 60,
            {"x": 104, "y": 56},
            "Good Spirits lounge and bar. Deck 5.",
        ),
        PublicZoneRecipe(
            "CaptainCircle", "Free", "low", 120.0, "5_Plaza", 20,
            {"x": 134, "y": 56},
            "Captain's Circle (loyalty lounge). Deck 5.",
        ),
        PublicZoneRecipe(
            "ShoreExcursions", "Free", "low", 100.0, "5_Plaza", 15,
            {"x": 150, "y": 56},
            "Shore Excursions desk. Deck 5.",
        ),
        PublicZoneRecipe(
            "SelfLaundry", "Free", "low", 150.0, "5_Plaza", 10,
            {"x": 205, "y": 56},
            "Self-service laundromat. Deck 5.",
        ),
        PublicZoneRecipe(
            "PrincessTheater", "Free", "high", 5200.0, "6_Fiesta", 1200,
            {"x": 42, "y": 50},
            "Princess Theater (lower level deck 6, upper level deck 7). ~1,200 seats.",
        ),
        PublicZoneRecipe(
            "ChurchillLounge", "Free", "medium", 350.0, "6_Fiesta", 80,
            {"x": 62, "y": 50},
            "Churchill's Cigar Lounge. Deck 6.",
        ),
        PublicZoneRecipe(
            "WeddingChapel", "Free", "low", 120.0, "6_Fiesta", 30,
            {"x": 78, "y": 50},
            "Wedding Chapel. Deck 6.",
        ),
        PublicZoneRecipe(
            "GrandCasino", "Free", "high", 1100.0, "6_Fiesta", 250,
            {"x": 100, "y": 50},
            "Grand Casino. Deck 6.",
        ),
        PublicZoneRecipe(
            "GuestServices", "Free", "low", 200.0, "6_Fiesta", 30,
            {"x": 122, "y": 50},
            "Guest / passenger services desk. Deck 6.",
        ),
        PublicZoneRecipe(
            "PacificMoon", "Dining", "high", 2400.0, "6_Fiesta", 380,
            {"x": 150, "y": 50},
            "Pacific Moon Dining Room (anytime). Deck 6. ~380 seats.",
            dining_service_type="mdr", food_contamination_multiplier=1.0,
            meal_seatings=2,
        ),
        PublicZoneRecipe(
            "SantaFe", "Dining", "high", 2400.0, "6_Fiesta", 380,
            {"x": 166, "y": 50},
            "Santa Fe Dining Room (anytime). Deck 6. ~380 seats.",
            dining_service_type="mdr", food_contamination_multiplier=1.0,
            meal_seatings=2,
        ),
        PublicZoneRecipe(
            "International", "Dining", "high", 2600.0, "6_Fiesta", 400,
            {"x": 190, "y": 50},
            "International Dining Room (traditional). Deck 6 aft. ~400 seats.",
            dining_service_type="mdr", food_contamination_multiplier=1.0,
            meal_seatings=2,
        ),
        PublicZoneRecipe(
            "WakeViewBar", "Free", "low", 120.0, "6_Fiesta", 30,
            {"x": 208, "y": 50},
            "Wake View Bar. Deck 6 aft.",
        ),
        PublicZoneRecipe(
            "WheelhouseBar", "Free", "medium", 200.0, "7_Promenade", 60,
            {"x": 40, "y": 44},
            "Wheelhouse Bar. Deck 7 forward.",
        ),
        PublicZoneRecipe(
            "MeridianBay", "Free", "low", 250.0, "7_Promenade", 40,
            {"x": 58, "y": 44},
            "Meridian Bay lounge. Deck 7.",
        ),
        PublicZoneRecipe(
            "PromGalleria", "Free", "high", 900.0, "7_Promenade", 200,
            {"x": 82, "y": 44},
            "Promenade Galleria / The Shops of Princess. Deck 7.",
        ),
        PublicZoneRecipe(
            "Crooners", "Free", "medium", 200.0, "7_Promenade", 60,
            {"x": 100, "y": 44},
            "Crooners Bar. Deck 7.",
        ),
        PublicZoneRecipe(
            "Facets", "Free", "low", 150.0, "7_Promenade", 40,
            {"x": 116, "y": 44},
            "Facets lounge. Deck 7.",
        ),
        PublicZoneRecipe(
            "ExplorersLounge", "Free", "medium", 350.0, "7_Promenade", 80,
            {"x": 136, "y": 44},
            "Explorers Lounge (dance club). Deck 7.",
        ),
        PublicZoneRecipe(
            "PhotoGallery", "Free", "low", 150.0, "7_Promenade", 30,
            {"x": 152, "y": 44},
            "Photo Gallery. Deck 7.",
        ),
        PublicZoneRecipe(
            "KaiSushi", "Dining", "medium", 280.0, "7_Promenade", 60,
            {"x": 168, "y": 44},
            "Kai Sushi (Japanese). Deck 7. ~60 seats.",
            dining_service_type="specialty", food_contamination_multiplier=0.5,
            meal_seatings=2,
        ),
        PublicZoneRecipe(
            "Sabatini", "Dining", "medium", 320.0, "7_Promenade", 80,
            {"x": 184, "y": 44},
            "Sabatini's Italian Trattoria. Deck 7. ~80 seats.",
            dining_service_type="specialty", food_contamination_multiplier=0.5,
            meal_seatings=2,
        ),
        PublicZoneRecipe(
            "ClubFusion", "Free", "high", 700.0, "7_Promenade", 150,
            {"x": 206, "y": 44},
            "Club Fusion (music and dance club). Deck 7.",
        ),
        PublicZoneRecipe(
            "OceanFront", "Free", "medium", 800.0, "7_Promenade", 150,
            {"x": 120, "y": 47},
            "OceanFront open-deck promenade. Deck 7.",
        ),
        PublicZoneRecipe(
            "TerracePool", "Free", "high", 1500.0, "12_Aloha", 250,
            {"x": 180, "y": 14},
            "Terrace Pool, aft open-air pool deck. Deck 12.",
        ),
        PublicZoneRecipe(
            "PregoPizza", "Dining", "high", 420.0, "14_Lido", 120,
            {"x": 45, "y": 12},
            "Prego Pizzeria (quick service). Deck 14. ~120 seats.",
            dining_service_type="buffet", food_contamination_multiplier=3.0,
            meal_seatings=2,
        ),
        PublicZoneRecipe(
            "NeptunePool", "Free", "high", 2500.0, "14_Lido", 400,
            {"x": 62, "y": 12},
            "Neptune's Reef & Pool (main pool). Deck 14, open-air.",
        ),
        PublicZoneRecipe(
            "MermaidTail", "Free", "medium", 150.0, "14_Lido", 50,
            {"x": 108, "y": 12},
            "The Mermaid's Tail Bar. Deck 14.",
        ),
        PublicZoneRecipe(
            "CalypsoPool", "Free", "high", 1800.0, "14_Lido", 300,
            {"x": 80, "y": 12},
            "Calypso Reef & Pool. Deck 14, open-air.",
        ),
        PublicZoneRecipe(
            "TridentGrill", "Dining", "high", 420.0, "14_Lido", 120,
            {"x": 98, "y": 12},
            "Trident Grill (quick service). Deck 14. ~120 seats.",
            dining_service_type="buffet", food_contamination_multiplier=3.0,
            meal_seatings=2,
        ),
        PublicZoneRecipe(
            "Swirls", "Dining", "medium", 80.0, "14_Lido", 20,
            {"x": 100, "y": 12},
            "Swirls ice cream bar. Deck 14.",
            dining_service_type="buffet", food_contamination_multiplier=3.0,
            meal_seatings=2,
        ),
        PublicZoneRecipe(
            "CalypsoBar", "Free", "medium", 150.0, "14_Lido", 50,
            {"x": 122, "y": 12},
            "Calypso Bar (pool bar). Deck 14.",
        ),
        PublicZoneRecipe(
            "HorizonCourt", "Dining", "high", 3200.0, "14_Lido", 600,
            {"x": 140, "y": 12},
            "Horizon Court buffet. Deck 14. ~600 seats.",
            dining_service_type="buffet", food_contamination_multiplier=3.0,
            meal_seatings=2,
        ),
        PublicZoneRecipe(
            "Churrascaria", "Dining", "medium", 320.0, "14_Lido", 80,
            {"x": 158, "y": 12},
            "Churrascaria Brazilian Grill. Deck 14. ~80 seats.",
            dining_service_type="specialty", food_contamination_multiplier=0.5,
            meal_seatings=2,
        ),
        PublicZoneRecipe(
            "SterlingSteak", "Dining", "medium", 320.0, "14_Lido", 80,
            {"x": 172, "y": 12},
            "Sterling Steakhouse. Deck 14. ~80 seats.",
            dining_service_type="specialty", food_contamination_multiplier=0.5,
            meal_seatings=2,
        ),
        PublicZoneRecipe(
            "OutriggerBar", "Free", "low", 150.0, "14_Lido", 50,
            {"x": 188, "y": 12},
            "Outrigger Bar. Deck 14.",
        ),
        PublicZoneRecipe(
            "HorizonTerrace", "Free", "medium", 600.0, "14_Lido", 100,
            {"x": 205, "y": 12},
            "Horizon Terrace (aft open deck). Deck 14.",
        ),
        PublicZoneRecipe(
            "TheConservatory", "Free", "medium", 700.0, "15_Sun", 120,
            {"x": 40, "y": 10},
            "The Conservatory (forward lounge). Deck 15.",
        ),
        PublicZoneRecipe(
            "FitnessCenter", "Free", "medium", 700.0, "15_Sun", 100,
            {"x": 62, "y": 10},
            "Fitness Center. Deck 15.",
        ),
        PublicZoneRecipe(
            "Aerobics", "Free", "medium", 400.0, "15_Sun", 80,
            {"x": 80, "y": 10},
            "Aerobics studio. Deck 15.",
        ),
        PublicZoneRecipe(
            "LotusSpa", "Free", "medium", 1200.0, "15_Sun", 150,
            {"x": 100, "y": 10},
            "Lotus Spa. Deck 15.",
        ),
        PublicZoneRecipe(
            "BeautySalon", "Free", "low", 150.0, "15_Sun", 20,
            {"x": 118, "y": 10},
            "Beauty Salon. Deck 15.",
        ),
        PublicZoneRecipe(
            "Tradewinds", "Free", "low", 150.0, "15_Sun", 50,
            {"x": 132, "y": 10},
            "Tradewinds Bar. Deck 15.",
        ),
        PublicZoneRecipe(
            "OpenAirCinema", "Free", "medium", 800.0, "15_Sun", 200,
            {"x": 155, "y": 10},
            "Movies Under the Stars (open-air cinema). Deck 15.",
        ),
        PublicZoneRecipe(
            "YouthCenter", "Free", "medium", 400.0, "15_Sun", 80,
            {"x": 175, "y": 10},
            "Youth Center. Deck 15.",
        ),
        PublicZoneRecipe(
            "TeenLounge", "Free", "medium", 300.0, "15_Sun", 60,
            {"x": 192, "y": 10},
            "Teen Lounge (Beach House). Deck 15.",
        ),
        PublicZoneRecipe(
            "IzumiBath", "Free", "low", 500.0, "15_Sun", 40,
            {"x": 210, "y": 10},
            "Izumi Japanese bath. Deck 15.",
        ),
        PublicZoneRecipe(
            "TheSanctuary", "Free", "medium", 800.0, "16_Sports", 120,
            {"x": 90, "y": 8},
            "The Sanctuary (adults-only retreat). Deck 16.",
        ),
        PublicZoneRecipe(
            "OasisBar", "Free", "low", 150.0, "16_Sports", 50,
            {"x": 112, "y": 8},
            "Oasis Bar. Deck 16.",
        ),
        PublicZoneRecipe(
            "SportsCourt", "Free", "medium", 600.0, "16_Sports", 100,
            {"x": 138, "y": 8},
            "Sports court. Deck 16, open-air.",
        ),
        PublicZoneRecipe(
            "Skywalkers", "Free", "high", 500.0, "17_Sky", 150,
            {"x": 90, "y": 6},
            "Skywalkers Nightclub. Deck 17.",
        ),
        PublicZoneRecipe(
            "CenterCourt", "Free", "medium", 400.0, "17_Sky", 80,
            {"x": 140, "y": 6},
            "Center Court sports area. Deck 17, open-air.",
        ),
        PublicZoneRecipe(
            "Bridge", "Free", "low", 300.0, "18_Bridge", 12,
            {"x": 150, "y": 4},
            "Navigating bridge and chartroom. Deck 18.",
        ),
        PublicZoneRecipe(
            "Engine_Room", "Free", "low", 6500.0, "0_Engine", 25,
            {"x": 80, "y": 100},
            "Engine room (diesel-electric plant). Deck 0.",
        ),
        PublicZoneRecipe(
            "CrewMess", "Dining", "high", 900.0, "1_Crew", 250,
            {"x": 70, "y": 95},
            "Crew mess. Deck 1. ~250 seats.",
            dining_service_type="crew_mess", food_contamination_multiplier=1.0,
            meal_seatings=4,
        ),
        PublicZoneRecipe(
            "CrewMessOff", "Dining", "medium", 280.0, "2_Crew", 60,
            {"x": 70, "y": 84},
            "Officers mess. Deck 2. ~60 seats.",
            dining_service_type="crew_mess", food_contamination_multiplier=1.0,
            meal_seatings=4,
        ),
        PublicZoneRecipe(
            "Laundry", "Free", "medium", 300.0, "3_Crew", 15,
            {"x": 110, "y": 72},
            "Industrial laundry. Deck 3.",
        ),
        PublicZoneRecipe(
            "Stores", "Free", "low", 400.0, "3_Crew", 5,
            {"x": 130, "y": 72},
            "Provision stores. Deck 3.",
        ),
    )


def _diamond_adjacency() -> tuple[dict[str, str], ...]:
    links: list[dict[str, str]] = [
        {"from": "GrandPlaza", "to": "TheLibrary", "type": "passageway"},
        {"from": "GrandPlaza", "to": "FineArts", "type": "passageway"},
        {"from": "GrandPlaza", "to": "GoodSpirits", "type": "passageway"},
        {"from": "GrandPlaza", "to": "CaptainCircle", "type": "doorway"},
        {"from": "Vivaldi", "to": "MainGalley", "type": "service_hatch"},
        {"from": "Savoy", "to": "MainGalley", "type": "service_hatch"},
        {"from": "MedicalCenter", "to": "IsolWard", "type": "doorway"},
        {"from": "MedicalCenter", "to": "GrandPlaza", "type": "stairwell"},
        {"from": "PrincessTheater", "to": "ChurchillLounge", "type": "passageway"},
        {"from": "ChurchillLounge", "to": "WeddingChapel", "type": "doorway"},
        {"from": "ChurchillLounge", "to": "GrandCasino", "type": "passageway"},
        {"from": "GrandCasino", "to": "GuestServices", "type": "passageway"},
        {"from": "PacificMoon", "to": "SantaFe", "type": "passageway"},
        {"from": "SantaFe", "to": "International", "type": "passageway"},
        {"from": "International", "to": "WakeViewBar", "type": "passageway"},
        {"from": "WheelhouseBar", "to": "MeridianBay", "type": "passageway"},
        {"from": "MeridianBay", "to": "PromGalleria", "type": "passageway"},
        {"from": "PromGalleria", "to": "Crooners", "type": "passageway"},
        {"from": "Crooners", "to": "Facets", "type": "passageway"},
        {"from": "Facets", "to": "ExplorersLounge", "type": "passageway"},
        {"from": "ExplorersLounge", "to": "PhotoGallery", "type": "passageway"},
        {"from": "PhotoGallery", "to": "KaiSushi", "type": "passageway"},
        {"from": "KaiSushi", "to": "Sabatini", "type": "passageway"},
        {"from": "Sabatini", "to": "ClubFusion", "type": "passageway"},
        {"from": "OceanFront", "to": "PromGalleria", "type": "open_front"},
        {"from": "PregoPizza", "to": "TridentGrill", "type": "passageway"},
        {"from": "PregoPizza", "to": "NeptunePool", "type": "doorway"},
        {"from": "TridentGrill", "to": "CalypsoPool", "type": "doorway"},
        {"from": "NeptunePool", "to": "CalypsoPool", "type": "open_deck"},
        {"from": "CalypsoPool", "to": "CalypsoBar", "type": "doorway"},
        {"from": "NeptunePool", "to": "HorizonCourt", "type": "doorway"},
        {"from": "HorizonCourt", "to": "CalypsoBar", "type": "passageway"},
        {"from": "HorizonCourt", "to": "SterlingSteak", "type": "passageway"},
        {"from": "HorizonCourt", "to": "OutriggerBar", "type": "passageway"},
        {"from": "OutriggerBar", "to": "HorizonTerrace", "type": "passageway"},
        {"from": "MermaidTail", "to": "CalypsoBar", "type": "passageway"},
        {"from": "Swirls", "to": "CalypsoBar", "type": "passageway"},
        {"from": "TheConservatory", "to": "OpenAirCinema", "type": "open_deck"},
        {"from": "OpenAirCinema", "to": "Tradewinds", "type": "passageway"},
        {"from": "FitnessCenter", "to": "LotusSpa", "type": "passageway"},
        {"from": "LotusSpa", "to": "Aerobics", "type": "passageway"},
        {"from": "BeautySalon", "to": "LotusSpa", "type": "passageway"},
        {"from": "YouthCenter", "to": "TeenLounge", "type": "passageway"},
        {"from": "TeenLounge", "to": "IzumiBath", "type": "passageway"},
        {"from": "TheSanctuary", "to": "SportsCourt", "type": "passageway"},
        {"from": "TheSanctuary", "to": "OasisBar", "type": "passageway"},
        {"from": "Skywalkers", "to": "CenterCourt", "type": "passageway"},
        {"from": "Bridge", "to": "Skywalkers", "type": "stairwell"},
        {"from": "CrewMess", "to": "MainGalley", "type": "service_stairwell"},
        {"from": "CrewMessOff", "to": "MainGalley", "type": "service_stairwell"},
        {"from": "Laundry", "to": "Stores", "type": "service_corridor"},
        {"from": "Stores", "to": "Engine_Room", "type": "ladder_well"},
        # Corridor-to-public links
        {"from": "PC_D5_P_M", "to": "GrandPlaza", "type": "corridor"},
        {"from": "PC_D5_S_M", "to": "Savoy", "type": "corridor"},
        {"from": "PC_D6_P_F", "to": "PrincessTheater", "type": "corridor"},
        {"from": "PC_D6_P_M", "to": "PacificMoon", "type": "corridor"},
        {"from": "PC_D6_S_A", "to": "International", "type": "corridor"},
        {"from": "PC_D14_P_F", "to": "HorizonCourt", "type": "corridor"},
        {"from": "PC_D12_S_A", "to": "TerracePool", "type": "corridor"},
        {"from": "CC_D1_F", "to": "CrewMess", "type": "corridor"},
        {"from": "CC_D1_A", "to": "Engine_Room", "type": "ladder_well"},
        {"from": "CC_D2_M", "to": "CrewMessOff", "type": "corridor"},
        {"from": "CC_D3_F", "to": "Laundry", "type": "corridor"},
        {"from": "CC_D3_A", "to": "Stores", "type": "corridor"},
    ]
    # Same-deck corridor chains on every cabin bank (5/6 lower, 8-12 main)
    for deck in (5, 6, 8, 9, 10, 11, 12):
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
    # Vertical trunks: contiguous banks, plus the deck-7 gap (6->8) and the
    # deck-13 void (12->14 forward cabins) which have no corridor zones.
    for d1, d2 in ((5, 6), (8, 9), (9, 10), (10, 11), (11, 12), (6, 8)):
        links.append({
            "from": pax_zone_id(d1, "Port", "Mid"),
            "to": pax_zone_id(d2, "Port", "Mid"),
            "type": "elevator_bank",
        })
        links.append({
            "from": pax_zone_id(d1, "Stbd", "Mid"),
            "to": pax_zone_id(d2, "Stbd", "Mid"),
            "type": "stairwell",
        })
    links.append({
        "from": pax_zone_id(12, "Port", "Fwd"),
        "to": pax_zone_id(14, "Port", "Fwd"),
        "type": "stairwell",
    })
    links.append({
        "from": pax_zone_id(12, "Stbd", "Fwd"),
        "to": pax_zone_id(14, "Stbd", "Fwd"),
        "type": "elevator_bank",
    })
    # Lido forward bank: port/stbd pair only
    links.append({
        "from": pax_zone_id(14, "Port", "Fwd"),
        "to": pax_zone_id(14, "Stbd", "Fwd"),
        "type": "passageway",
    })
    # Crew corridors
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
            for section in ("Fwd", "Mid", "Aft"):
                links.append({
                    "from": crew_zone_id(deck, section),
                    "to": crew_zone_id(deck + 1, section),
                    "type": "stairwell",
                })
    return tuple(links)


DIAMOND_PRINCESS = CruisePlatformRecipe(
    platform_id="diamond_princess",
    nominal_complement={"passengers": 2710, "crew": 1100},
    description=(
        "Diamond Princess cruise ship (~2,710 passengers + ~1,100 crew = 3,810). "
        "Princess Cruises Grand-class, built 2004 by Mitsubishi Heavy Industries: "
        "290m LOA × 37.5m beam, 115,875 GT, twin-funnel silhouette, 18 decks. "
        "1,353 staterooms across 8 cabin decks (5, 6, 8-12, 14; no deck 13); "
        "deck 7 Promenade is all-public. Cabin-corridor resolution "
        "(44 pax + 9 crew corridors). Key venues: five main dining rooms, "
        "Promenade specialty dining, Grand Plaza atrium, Lido pools and buffet, "
        "Sun Deck spa and fitness. CDC Extra-Large AGE target 22.1/100K TD "
        "(calibration deferred). Layout follows the Princess accessible-route "
        "map and cruisedeckplans.com deck plans (2020 configuration: Kai Sushi "
        "and Savoy; the 2026 Crown Grill / Makoto Ocean rebrands are not modeled)."
    ),
    length_m=290.0,
    beam_m=37.5,
    population=3810,
    graywater_zones=("Engine_Room",),
    pax_corridors=CorridorRecipe(
        decks=(8, 9, 10, 11, 12),
        sides=("Port", "Stbd"),
        sections=("Fwd", "Mid", "Aft"),
        max_occupancy=70,
        volume_m3=1300.0,
        cabin_size=2,
        traffic="low",
        deck_label="{deck}_Cabins",
        ventilation=_diamond_vent,
        description_template=(
            "Passenger cabin corridor, Deck {deck} {side} {section}. "
            "~35 cabins, ~70 pax, ventilation={vent}."
        ),
        id_prefix="PC",
    ),
    extra_corridors=(
        CorridorRecipe(
            decks=(5, 6),
            sides=("Port", "Stbd"),
            sections=("Fwd", "Mid", "Aft"),
            max_occupancy=44,
            volume_m3=900.0,
            cabin_size=2,
            traffic="low",
            deck_label="{deck}_Cabins",
            ventilation=_diamond_vent,
            description_template=(
                "Passenger cabin corridor (lower bank), Deck {deck} {side} {section}. "
                "~22 cabins, ~44 pax, ventilation={vent}."
            ),
            id_prefix="PC",
        ),
        CorridorRecipe(
            decks=(14,),
            sides=("Port", "Stbd"),
            sections=("Fwd",),
            max_occupancy=64,
            volume_m3=1300.0,
            cabin_size=2,
            traffic="low",
            deck_label="{deck}_Cabins",
            ventilation=_diamond_vent,
            description_template=(
                "Passenger cabin corridor (Lido forward bank), "
                "Deck {deck} {side} {section}. ~32 cabins, ~64 pax, ventilation={vent}."
            ),
            id_prefix="PC",
        ),
    ),
    crew_corridors=CorridorRecipe(
        decks=(1, 2, 3),
        sides=(),
        sections=("Fwd", "Mid", "Aft"),
        max_occupancy=120,
        volume_m3=800.0,
        cabin_size=3,
        traffic="medium",
        deck_label="{deck}_Crew",
        ventilation=lambda d, s, sec: "interior_hvac",
        description_template=(
            "Crew cabin corridor, Deck {deck} {section}. "
            "~120 crew, interior HVAC."
        ),
        id_prefix="CC",
        cabin_size_by_class={"crew_engineering": 2, "crew_medical": 2},
    ),
    public_zones=_diamond_public_zones(),
    exterior_zones=(
        "OceanFront", "TerracePool", "NeptunePool", "CalypsoPool",
        "HorizonTerrace", "OpenAirCinema", "SportsCourt", "CenterCourt",
    ),
    public_hvac=(
        HvacGroupRecipe(
            "AHU_Public_Fwd",
            ("PrincessTheater", "GrandCasino", "GuestServices", "ChurchillLounge",
             "WeddingChapel", "WakeViewBar", "WheelhouseBar", "Bridge"),
            8.0,
            "Forward / entertainment.",
        ),
        HvacGroupRecipe(
            "AHU_Public_Mid",
            ("GrandPlaza", "PromGalleria", "PhotoGallery", "Crooners", "Facets",
             "ExplorersLounge", "ClubFusion", "MeridianBay", "FineArts",
             "TheLibrary", "InternetCafe", "GoodSpirits", "CaptainCircle",
             "ShoreExcursions"),
            8.0,
            "Midship promenade / atrium / shops.",
        ),
        HvacGroupRecipe(
            "AHU_Public_Aft",
            ("CalypsoBar", "MermaidTail", "OutriggerBar", "FitnessCenter",
             "LotusSpa", "Aerobics", "BeautySalon", "TheConservatory",
             "Tradewinds", "YouthCenter", "TeenLounge", "IzumiBath"),
            10.0,
            "Lido bars / Sun Deck spa / fitness.",
        ),
        HvacGroupRecipe(
            "AHU_Public_Upper",
            ("TheSanctuary", "OasisBar", "Skywalkers"),
            8.0,
            "Sports / Sky decks.",
        ),
        HvacGroupRecipe(
            "AHU_Dining",
            ("Vivaldi", "Savoy", "PacificMoon", "SantaFe", "International",
             "KaiSushi", "Sabatini", "Churrascaria", "SterlingSteak",
             "HorizonCourt", "PregoPizza", "TridentGrill", "Swirls",
             "CrewMess", "CrewMessOff"),
            8.0,
            "Dining venues including crew messes.",
        ),
        HvacGroupRecipe(
            "AHU_Medical",
            ("MedicalCenter", "IsolWard"),
            12.0,
            "Medical + isolation ward.",
        ),
        HvacGroupRecipe(
            "AHU_Service",
            ("MainGalley", "Laundry", "Stores", "Engine_Room", "SelfLaundry"),
            15.0,
            "Service / galley / engine.",
        ),
    ),
    auto_pax_ahu=True,
    auto_crew_ahu=True,
    crew_ahu_merged=False,
    pax_trunk_m3h=1800.0,
    crew_trunk_m3h=900.0,
    cabin_relief_m3h=2000.0,
    cabin_relief_target_ahu="AHU_Public_Mid",
    cross_zone_links=(
        {
            "from": "International",
            "to": "MainGalley",
            "flow_rate_m3h": 18000.0,
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
            "from": "HorizonCourt",
            "to": "NeptunePool",
            "flow_rate_m3h": 1000.0,
            "is_hvac_ducted": False,
            "path": "Lido_Open_Doorway",
        },
    ),
    adjacency=_diamond_adjacency(),
    pax_deck_y={
        5: 56.0, 6: 50.0, 8: 38.0, 9: 32.0, 10: 26.0, 11: 20.0, 12: 14.0,
        14: 12.0,
    },
    crew_deck_y={1: 95.0, 2: 84.0, 3: 72.0},
    side_x={"Port": 200.0, "Stbd": 200.0},
)


RECIPES: dict[str, CruisePlatformRecipe] = {
    EXPEDITION_CRUISE_450.platform_id: EXPEDITION_CRUISE_450,
    CLASSIC_CRUISE_1900.platform_id: CLASSIC_CRUISE_1900,
    SPIRIT_CRUISE_3000.platform_id: SPIRIT_CRUISE_3000,
    DIAMOND_PRINCESS.platform_id: DIAMOND_PRINCESS,
}
