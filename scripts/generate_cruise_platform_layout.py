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
        out.append({
            "id": z.id,
            "type": z.type,
            "traffic": z.traffic,
            "volume_m3": z.volume_m3,
            "deck": z.deck,
            "max_occupancy": z.max_occupancy,
            "display": dict(z.display),
            "description": z.description,
        })
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
    for z in zones:
        assert len(z["id"]) <= 15, f"Contam zone id too long: {z['id']!r}"
    return {
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
                "description": f"Deck {deck} cabin fan-coil branch.",
            })
    for bank in recipe.extra_corridors:
        # One AHU per extra bank deck: AHU_{prefix}_D{n}
        for deck in bank.decks:
            hvac.append({
                "id": f"AHU_{bank.id_prefix}_D{deck}",
                "rooms": _pax_ids_on_deck(bank, deck),
                "ach": recipe.pax_ahu_ach,
                "description": f"Deck {deck} {bank.id_prefix} cabin branch.",
            })

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

    hvac_ids = {hz["id"] for hz in hvac}
    valid_endpoints = zone_ids | hvac_ids
    cross = [
        cl for cl in cross
        if cl["from"] in valid_endpoints and cl["to"] in valid_endpoints
    ]
    adjacency = [
        a for a in recipe.adjacency
        if a["from"] in zone_ids and a["to"] in zone_ids
    ]

    # Every zone must appear in exactly one HVAC group
    covered = {r for hz in hvac for r in hz["rooms"]}
    missing = zone_ids - covered
    if missing:
        raise ValueError(
            f"{recipe.platform_id}: zones missing from HVAC rooms: {sorted(missing)}"
        )

    return {
        "platform": recipe.platform_id,
        "description": (
            f"HVAC for {recipe.platform_id} cabin-corridor layout. "
            f"Population ~{recipe.population}."
        ),
        "oa_fraction": recipe.oa_fraction,
        "hvac_duty": recipe.hvac_duty,
        "hvac_zones": hvac,
        "cross_zone_links": cross,
        "adjacency": adjacency,
    }


def write_platform(recipe: CruisePlatformRecipe, *, dry_run: bool = False) -> None:
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

    out_dir = os.path.join(REPO, "data", "platforms", recipe.platform_id)
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
    args = parser.parse_args(argv)
    write_platform(RECIPES[args.platform], dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
