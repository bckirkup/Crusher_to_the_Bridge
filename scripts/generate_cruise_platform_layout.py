#!/usr/bin/env python3
"""
Generate cabin-corridor cruise platform spatial_layout.json + air_flow_paths.json.

Usage::

    python3 scripts/generate_cruise_platform_layout.py --platform expedition_cruise_450
    python3 scripts/generate_cruise_platform_layout.py --platform expedition_cruise_450 --dry-run
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from typing import Any

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

from cruise_platform_recipes import (  # noqa: E402
    RECIPES,
    CorridorRecipe,
    CruisePlatformRecipe,
    crew_zone_id,
    pax_zone_id,
)
from derive_sanitary_provisioning import (  # noqa: E402
    sanitary_airflow_augment,
    sanitary_zone_dicts,
)
from platform_generation_guard import ensure_platform_output_dir  # noqa: E402


def _pax_display(
    recipe: CruisePlatformRecipe, deck: int, side: str, section: str,
) -> dict[str, float]:
    base_y = recipe.pax_deck_y.get(deck, 40.0)
    y_off = {"Port": -2.0, "Stbd": 2.0, "Central": 0.0}.get(side, 0.0)
    x_off = {"Fwd": -20.0, "Mid": 0.0, "Aft": 20.0}.get(section, 0.0)
    base_x = recipe.side_x.get(side, recipe.length_m * 0.7)
    return {"x": base_x + x_off, "y": base_y + y_off}


def _crew_display(
    recipe: CruisePlatformRecipe, deck: int, section: str,
) -> dict[str, float]:
    base_y = recipe.crew_deck_y.get(deck, 80.0)
    x_off = {"Fwd": -15.0, "Mid": 0.0, "Aft": 15.0}.get(section, 0.0)
    return {"x": recipe.length_m * 0.55 + x_off, "y": base_y}


def _build_grid_corridors(
    recipe: CruisePlatformRecipe, corr: CorridorRecipe,
) -> list[dict[str, Any]]:
    zones: list[dict[str, Any]] = []
    prefix = corr.id_prefix
    for deck in corr.decks:
        for side in corr.sides:
            for section in corr.sections:
                vent = corr.ventilation(deck, side, section)
                zid = pax_zone_id(deck, side, section, prefix=prefix)
                zones.append({
                    "id": zid,
                    "type": "Cabin_Corridor",
                    "traffic": corr.traffic,
                    "volume_m3": corr.volume_m3,
                    "deck": corr.deck_label.format(deck=deck),
                    "max_occupancy": corr.max_occupancy,
                    "display": _pax_display(recipe, deck, side, section),
                    "cabin_ventilation_type": vent,
                    "cabin_size": corr.cabin_size,
                    "description": corr.description_template.format(
                        deck=deck, side=side, section=section, vent=vent,
                    ),
                })
                if corr.cabin_size_by_class:
                    zones[-1]["cabin_size_by_class"] = dict(
                        corr.cabin_size_by_class,
                    )
    return zones


def _build_linear_corridors(
    recipe: CruisePlatformRecipe, corr: CorridorRecipe,
) -> list[dict[str, Any]]:
    zones: list[dict[str, Any]] = []
    prefix = corr.id_prefix
    for deck in corr.decks:
        for section in corr.sections:
            vent = corr.ventilation(deck, "", section)
            zid = crew_zone_id(deck, section, prefix=prefix)
            zones.append({
                "id": zid,
                "type": "Cabin_Corridor",
                "traffic": corr.traffic,
                "volume_m3": corr.volume_m3,
                "deck": corr.deck_label.format(deck=deck),
                "max_occupancy": corr.max_occupancy,
                "display": _crew_display(recipe, deck, section),
                "cabin_ventilation_type": vent,
                "cabin_size": corr.cabin_size,
                "description": corr.description_template.format(
                    deck=deck, side="", section=section, vent=vent,
                ).replace("  ", " "),
            })
            if corr.cabin_size_by_class:
                zones[-1]["cabin_size_by_class"] = dict(corr.cabin_size_by_class)
    return zones


def _build_corridor_bank(
    recipe: CruisePlatformRecipe, corr: CorridorRecipe,
) -> list[dict[str, Any]]:
    if corr.sides:
        return _build_grid_corridors(recipe, corr)
    return _build_linear_corridors(recipe, corr)


def _build_pax_corridors(recipe: CruisePlatformRecipe) -> list[dict[str, Any]]:
    return _build_corridor_bank(recipe, recipe.pax_corridors)


def _build_crew_corridors(recipe: CruisePlatformRecipe) -> list[dict[str, Any]]:
    return _build_corridor_bank(recipe, recipe.crew_corridors)


def _public_zone_dicts(recipe: CruisePlatformRecipe) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for z in recipe.public_zones:
        assert len(z.id) <= 15, f"Contam zone id too long: {z.id!r}"
        entry: dict[str, Any] = {
            "id": z.id,
            "type": z.type,
            "traffic": z.traffic,
            "volume_m3": z.volume_m3,
            "deck": z.deck,
            "max_occupancy": z.max_occupancy,
            "display": dict(z.display),
            "description": z.description,
        }
        if z.dining_service_type is not None:
            entry["dining_service_type"] = z.dining_service_type
        if z.food_contamination_multiplier is not None:
            entry["food_contamination_multiplier"] = z.food_contamination_multiplier
        if z.meal_seatings is not None:
            entry["meal_seatings"] = z.meal_seatings
        out.append(entry)
    return out


def _weather_exposure_tags(
    zones: list[dict[str, Any]],
    exterior_zones: tuple[str, ...],
) -> list[dict[str, Any]]:
    """Tag ``exposure: weather`` on exterior zones (CONTAM-AMBIENT-WEATHER-01),
    keyed after ``deck`` to match commissioned hull ordering."""
    exterior = set(exterior_zones)
    out: list[dict[str, Any]] = []
    for z in zones:
        if z["id"] not in exterior or "exposure" in z:
            out.append(z)
            continue
        tagged: dict[str, Any] = {}
        for key, value in z.items():
            tagged[key] = value
            if key == "deck":
                tagged["exposure"] = "weather"
        out.append(tagged)
    return out


def build_spatial_layout(recipe: CruisePlatformRecipe) -> dict[str, Any]:
    extra: list[dict[str, Any]] = []
    for bank in recipe.extra_corridors:
        extra.extend(_build_corridor_bank(recipe, bank))
    zones = (
        _public_zone_dicts(recipe)
        + _build_pax_corridors(recipe)
        + _build_crew_corridors(recipe)
        + extra
    )
    zones += sanitary_zone_dicts(zones)
    zones = _weather_exposure_tags(zones, recipe.exterior_zones)
    for z in zones:
        assert len(z["id"]) <= 15, f"Contam zone id too long: {z['id']!r}"
    out: dict[str, Any] = {
        "platform": recipe.platform_id,
        "description": recipe.description,
        "isolation_unit_capacity": recipe.isolation_unit_capacity,
        "deck_dimensions": {
            "length_m": recipe.length_m,
            "beam_m": recipe.beam_m,
        },
        "confinement_isolation_factor": recipe.confinement_isolation_factor,
        "corridor_direct_contact_factor": recipe.corridor_direct_contact_factor,
        "graywater_zones": list(recipe.graywater_zones),
        "zones": zones,
    }
    if recipe.nominal_complement:
        out["nominal_complement"] = dict(recipe.nominal_complement)
    return out


# ---------------------------------------------------------------------------
# Commissioning layer (CONTAM-AMBIENT-WEATHER-CRUISE-01 /
# CONTAM-AMBIENT-MAKEUP-CRUISE-01). Emitted here since explorer_seas_06; the
# earlier commissioned hulls carry the same layer hand-authored.
# open_deck ``exchange_m3h`` is emitted null: it is the ContamX-solved outward
# flow, filled by ``scripts/commission_platform_contam.py`` after export.

_DUCTED_EXHAUST_PREFIXES = (
    "Pax_Trunk_",
    "Crew_Trunk_",
    "Cabin_Relief_",
    "Corridor_Relief_",
)
_PASSIVE_OPENING_MARKERS = ("Door_Leakage", "Open_Doorway")

_GALLEY_TRANSFER_DESCRIPTION = (
    "One-way make-up transfer into the galley while galley exhaust runs "
    "independent to atmosphere (CDC VSP 2025 §33.2.1-§33.2.2; "
    "ISO 9943:2009 §4.1/§5.2/A.2.3). Despite the historical path name this is "
    "transfer air, not recirculated exhaust; magnitude remains "
    "ASSUMED-GALLEY-TRANSFER-MAGNITUDE, Grade C, unchanged."
)
_GALLEY_HOOD_DESCRIPTION = (
    "Galley hood exhaust is a once-through prescribed-flow sink to ambient "
    "(material leaves the ship/domain), separate from the recirculated HVAC "
    "supply and carrying no filtration/recirculation credit (CDC VSP 2025 "
    "§33.2.1-§33.2.2; ISO 9943:2009 §4.1/§5.2/A.2.1/A.2.3). Magnitude remains "
    "Grade C: no retrieved source gives a separate galley exhaust magnitude "
    "and ISO 9943 §5.2 gives no formula, so the declared value is the paired "
    "make-up-transfer magnitude with no invented margin; the make-up side "
    "remains the authored Dining_Galley_Exhaust/Galley_Service_Exhaust link."
)
_OPEN_DECK_DESCRIPTION = (
    "Open weather deck exchange with ambient (CONTAM-AMBIENT-WEATHER-CRUISE-01). "
    "area_m2 is ASSUMED-OPEN-DECK-FACE-AREA, Grade C: no drawing gives the "
    "deck edge, so it is the two opposite side faces of a square-plan deck of "
    "this zone's volume at the exporter's 3 m zone height, 2 * sqrt(V / 3) * 3. "
    "wind_speed_m_s is the declared relative-wind axis [0, 10] m/s at its "
    "committed point 1 m/s (the exporter's wind-pressure-test speed), Grade C, "
    "not a measured wind. exchange_m3h is the ContamX-solved outward flow "
    "through the opening at that point, commissioned lane (D5)."
)


def _commissioned_link_fields(link: dict[str, Any]) -> dict[str, Any]:
    """Explicit direction/mechanism/filtered for a migration-era link class."""
    path = str(link.get("path", ""))
    if link.get("direction") is not None:
        return {}
    if path == "Dining_Galley_Exhaust":
        return {
            "direction": "oneway",
            "mechanism": "prescribed_flow",
            "filtered": False,
        }
    if path.startswith(_DUCTED_EXHAUST_PREFIXES):
        return {
            "direction": "oneway",
            "mechanism": "prescribed_flow",
            "filtered": True,
        }
    if any(marker in path for marker in _PASSIVE_OPENING_MARKERS):
        return {
            "direction": "bidirectional",
            "mechanism": "pressure_opening",
            "filtered": False,
        }
    return {}


def _makeup_louvre_description(source_zone: str, galley_zone: str) -> str:
    return (
        "Ambient make-up path for the prescribed Galley_Hood_Exhaust 18000 "
        "m3/h exhaust demand (CONTAM-AMBIENT-MAKEUP-CRUISE-01). Placed on "
        f"{source_zone}: the zone the paired Dining_Galley_Exhaust transfer "
        "draws the galley make-up air from, which is where the hull's air "
        f"deficit sits ({galley_zone} itself is balanced by that transfer). "
        "Area is ASSUMED-MAKEUP-LOUVRE-AREA, Grade C: no drawing gives a "
        "louvre, so it is the served demand at an assumed 2.5 m/s free-area "
        "face velocity (18000 / 3600 / 2.5). exchange_m3h is 0: the "
        "ContamX-solved flow through both legs is inward only (clean make-up), "
        "so the opening is not a native sink."
    )


def commissioning_augment(
    recipe: CruisePlatformRecipe,
    cross: list[dict[str, Any]],
    zones: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Apply the hand-authored commissioning layer to generated airflow data.

    Decorates migration-era cross-zone links, inserts the
    ``Galley_Hood_Exhaust`` once-through sink when the recipe declares a
    ``Dining_Galley_Exhaust`` transfer, and returns the ``ambient_openings``
    records (galley make-up louvre plus one ``open_deck`` per exterior zone).
    Call AFTER the endpoint filter so the ``to: ambient`` sink survives.
    """
    volumes = {z["id"]: float(z["volume_m3"]) for z in zones}
    galley_source: str | None = None
    galley_zone: str | None = None
    galley_flow = 18000.0
    out: list[dict[str, Any]] = []
    for link in cross:
        extra = _commissioned_link_fields(link)
        if not extra:
            out.append(link)
            continue
        rebuilt = {
            key: link[key]
            for key in ("from", "to", "flow_rate_m3h", "is_hvac_ducted", "path")
            if key in link
        }
        if link.get("path") == "Dining_Galley_Exhaust":
            rebuilt["description"] = _GALLEY_TRANSFER_DESCRIPTION
            galley_source = str(link["from"])
            galley_zone = str(link["to"])
            galley_flow = float(link["flow_rate_m3h"])
        rebuilt.update({k: v for k, v in link.items() if k not in rebuilt})
        rebuilt.update(extra)
        out.append(rebuilt)
        if link.get("path") == "Dining_Galley_Exhaust" and not any(
            cl.get("path") == "Galley_Hood_Exhaust" for cl in cross
        ):
            out.append({
                "from": galley_zone,
                "to": "ambient",
                "flow_rate_m3h": galley_flow,
                "is_hvac_ducted": True,
                "path": "Galley_Hood_Exhaust",
                "description": _GALLEY_HOOD_DESCRIPTION,
                "direction": "oneway",
                "mechanism": "prescribed_flow",
                "filtered": False,
            })

    openings: list[dict[str, Any]] = []
    if galley_source and galley_zone:
        openings.append({
            "zone": galley_source,
            "type": "makeup_louvre",
            "area_m2": 2.0,
            "exchange_m3h": 0.0,
            "schedule": "always_open",
            "description": _makeup_louvre_description(galley_source, galley_zone),
        })
    for zone in recipe.exterior_zones:
        volume = volumes.get(zone)
        if volume is None:
            continue
        openings.append({
            "zone": zone,
            "type": "open_deck",
            "area_m2": round(2 * math.sqrt(volume / 3) * 3, 3),
            "exchange_m3h": None,
            "wind_speed_m_s": 1.0,
            "schedule": "always_open",
            "description": _OPEN_DECK_DESCRIPTION,
        })
    return out, openings


def _pax_corridor_ids(corr: CorridorRecipe) -> list[str]:
    prefix = corr.id_prefix
    if corr.sides:
        return [
            pax_zone_id(deck, side, section, prefix=prefix)
            for deck in corr.decks
            for side in corr.sides
            for section in corr.sections
        ]
    return [
        crew_zone_id(deck, section, prefix=prefix)
        for deck in corr.decks
        for section in corr.sections
    ]


def _crew_corridor_ids(corr: CorridorRecipe) -> list[str]:
    return _pax_corridor_ids(corr)


def _pax_ids_on_deck(corr: CorridorRecipe, deck: int) -> list[str]:
    prefix = corr.id_prefix
    if corr.sides:
        return [
            pax_zone_id(deck, side, section, prefix=prefix)
            for side in corr.sides
            for section in corr.sections
        ]
    return [
        crew_zone_id(deck, section, prefix=prefix) for section in corr.sections
    ]


def _crew_ids_on_deck(corr: CorridorRecipe, deck: int) -> list[str]:
    return _pax_ids_on_deck(corr, deck)


def build_air_flow_paths(
    recipe: CruisePlatformRecipe,
    zone_ids: set[str],
) -> dict[str, Any]:
    hvac: list[dict[str, Any]] = []

    if recipe.auto_pax_ahu:
        for deck in recipe.pax_corridors.decks:
            hvac.append({
                "id": f"{recipe.pax_ahu_prefix}{deck}",
                "rooms": _pax_ids_on_deck(recipe.pax_corridors, deck),
                "ach": recipe.pax_ahu_ach,
                "description": f"Deck {deck} passenger cabin fan-coil branch.",
            })
    extra_ahus: dict[str, dict[str, Any]] = {}
    for bank in recipe.extra_corridors:
        # One AHU per extra bank deck: AHU_{prefix}_D{n}. Banks that share a
        # prefix and deck share that AHU; ids must stay unique.
        for deck in bank.decks:
            ahu_id = f"AHU_{bank.id_prefix}_D{deck}"
            rooms = _pax_ids_on_deck(bank, deck)
            if ahu_id in extra_ahus:
                extra_ahus[ahu_id]["rooms"].extend(rooms)
                continue
            extra_ahus[ahu_id] = {
                "id": ahu_id,
                "rooms": rooms,
                "ach": recipe.pax_ahu_ach,
                "description": f"Deck {deck} {bank.id_prefix} cabin branch.",
            }
            hvac.append(extra_ahus[ahu_id])

    crew_ids = _crew_corridor_ids(recipe.crew_corridors)
    for group in recipe.public_hvac:
        rooms = list(group.rooms)
        if group.id == "AHU_Crew" and recipe.crew_ahu_merged:
            rooms = crew_ids + [r for r in rooms if r]
            if "CrewMess" in zone_ids and "CrewMess" not in rooms:
                rooms.append("CrewMess")
            # Also fold officer mess variants if present
            for mess in ("CrewMess_Officers", "CrewMessMain"):
                if mess in zone_ids and mess not in rooms:
                    rooms.append(mess)
        hvac.append({
            "id": group.id,
            "rooms": rooms,
            "ach": group.ach,
            "description": group.description,
        })

    if recipe.auto_crew_ahu and not recipe.crew_ahu_merged:
        for deck in recipe.crew_corridors.decks:
            hvac.append({
                "id": f"{recipe.crew_ahu_prefix}{deck}",
                "rooms": _crew_ids_on_deck(recipe.crew_corridors, deck),
                "ach": recipe.crew_ahu_ach,
                "description": f"Deck {deck} crew accommodation branch.",
            })

    # Deduplicate rooms across HVAC groups (CrewMess may be listed twice)
    seen_rooms: set[str] = set()
    cleaned: list[dict[str, Any]] = []
    for hz in hvac:
        rooms = []
        for r in hz["rooms"]:
            if r in seen_rooms:
                continue
            seen_rooms.add(r)
            rooms.append(r)
        entry = dict(hz)
        entry["rooms"] = rooms
        cleaned.append(entry)
    hvac = cleaned

    cross = [dict(cl) for cl in recipe.cross_zone_links]
    pax_decks = list(recipe.pax_corridors.decks)
    if recipe.pax_trunk_m3h > 0:
        for i, deck in enumerate(pax_decks[:-1]):
            nxt = pax_decks[i + 1]
            cross.append({
                "from": f"{recipe.pax_ahu_prefix}{deck}",
                "to": f"{recipe.pax_ahu_prefix}{nxt}",
                "flow_rate_m3h": recipe.pax_trunk_m3h,
                "is_hvac_ducted": True,
                "path": f"Pax_Trunk_D{deck}_D{nxt}",
            })
    crew_decks = list(recipe.crew_corridors.decks)
    if recipe.crew_trunk_m3h > 0 and recipe.auto_crew_ahu and not recipe.crew_ahu_merged:
        for i, deck in enumerate(crew_decks[:-1]):
            nxt = crew_decks[i + 1]
            cross.append({
                "from": f"{recipe.crew_ahu_prefix}{deck}",
                "to": f"{recipe.crew_ahu_prefix}{nxt}",
                "flow_rate_m3h": recipe.crew_trunk_m3h,
                "is_hvac_ducted": True,
                "path": f"Crew_Trunk_D{deck}_D{nxt}",
            })
    if recipe.cabin_relief_m3h > 0 and recipe.cabin_relief_target_ahu:
        for deck in pax_decks:
            cross.append({
                "from": f"{recipe.pax_ahu_prefix}{deck}",
                "to": recipe.cabin_relief_target_ahu,
                "flow_rate_m3h": recipe.cabin_relief_m3h,
                "is_hvac_ducted": True,
                "path": f"Cabin_Relief_D{deck}",
            })

    # Sanitary head blocks: one exhaust-only HVAC group each plus a single
    # one-way makeup link from the served space's branch, added before the
    # endpoint filter so the head groups register as valid endpoints.
    layout_zones = build_spatial_layout(recipe)["zones"]
    head_augmented = sanitary_airflow_augment(
        layout_zones,
        {"hvac_zones": hvac, "cross_zone_links": cross},
    )
    hvac = head_augmented["hvac_zones"]
    cross = head_augmented["cross_zone_links"]

    hvac_ids = {hz["id"] for hz in hvac}
    valid_endpoints = zone_ids | hvac_ids
    cross = [
        cl for cl in cross
        if cl["from"] in valid_endpoints and cl["to"] in valid_endpoints
    ]
    cross, ambient_openings = commissioning_augment(recipe, cross, layout_zones)
    adjacency = [
        a for a in recipe.adjacency
        if a["from"] in zone_ids and a["to"] in zone_ids
    ]

    # Every zone must appear in exactly one HVAC group
    covered = {r for hz in hvac for r in hz["rooms"]}
    expected_covered = zone_ids - set(recipe.exterior_zones)
    missing = expected_covered - covered
    if missing:
        raise ValueError(
            f"{recipe.platform_id}: non-exterior zones missing from HVAC rooms: "
            f"{sorted(missing)}"
        )
    covered_exterior = set(recipe.exterior_zones) & covered
    if covered_exterior:
        raise ValueError(
            f"{recipe.platform_id}: exterior zones covered by HVAC rooms: "
            f"{sorted(covered_exterior)}"
        )

    out = {
        "platform": recipe.platform_id,
        "description": (
            f"HVAC for {recipe.platform_id} cabin-corridor layout. "
            f"Population ~{recipe.population}."
        ),
        "oa_fraction": recipe.oa_fraction,
        "hvac_duty": recipe.hvac_duty,
        "hvac_zones": hvac,
        "cross_zone_links": cross,
    }
    if ambient_openings:
        out["ambient_openings"] = ambient_openings
    out["adjacency"] = adjacency
    return out


def write_platform(
    recipe: CruisePlatformRecipe,
    *,
    dry_run: bool = False,
    overwrite: bool = False,
) -> None:
    out_dir = os.path.join(REPO, "data", "platforms", recipe.platform_id)
    ensure_platform_output_dir(
        out_dir,
        platform_id=recipe.platform_id,
        overwrite=overwrite,
        dry_run=dry_run,
    )
    spatial = build_spatial_layout(recipe)
    zone_ids = {z["id"] for z in spatial["zones"]}
    airflow = build_air_flow_paths(recipe, zone_ids)

    n_pax = len(_pax_corridor_ids(recipe.pax_corridors))
    n_crew = len(_crew_corridor_ids(recipe.crew_corridors))
    print(
        f"{recipe.platform_id}: {len(spatial['zones'])} zones "
        f"({n_pax} pax corridors, {n_crew} crew corridors), "
        f"{len(airflow['hvac_zones'])} AHUs, "
        f"{len(airflow['adjacency'])} adjacency links"
    )
    if dry_run:
        return

    os.makedirs(out_dir, exist_ok=True)
    for name, data in (
        ("spatial_layout.json", spatial),
        ("air_flow_paths.json", airflow),
    ):
        path = os.path.join(out_dir, name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")
        print(f"Wrote {path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate cabin-corridor cruise platform layouts.",
    )
    parser.add_argument(
        "--platform",
        required=True,
        choices=sorted(RECIPES.keys()),
        help="Platform recipe id",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing an existing committed platform directory",
    )
    args = parser.parse_args(argv)
    write_platform(
        RECIPES[args.platform],
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
