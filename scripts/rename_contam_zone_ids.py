#!/usr/bin/env python3
"""One-shot zone ID rename ≤15 chars for ContamW fiction platforms.

Apply Edison CTB PRJ Config Fixes v2 §1 rename maps to JSON/config/docs/tests.
Regenerate Contam PRJs separately via scripts/generate_platform_contam_prj.py.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

_SIDE = {"Port": "P", "Stbd": "S", "Central": "C"}
_POS = {"Fwd": "F", "Mid": "M", "Aft": "A"}


def _pax_corridor(name: str) -> str | None:
    m = re.fullmatch(
        r"Pax_Corridor_D(\d+)_(Port|Stbd|Central)_(Fwd|Mid|Aft)", name,
    )
    if not m:
        return None
    return f"PC_D{m.group(1)}_{_SIDE[m.group(2)]}_{_POS[m.group(3)]}"


def _crew_corridor(name: str) -> str | None:
    m = re.fullmatch(r"Crew_Corridor_D(\d+)_(Fwd|Mid|Aft)", name)
    if not m:
        return None
    return f"CC_D{m.group(1)}_{_POS[m.group(2)]}"


MEGA_AMENITY = {
    "Main_Dining_Room_Lower": "MainDining_L",
    "Main_Dining_Room_Upper": "MainDining_U",
    "Specialty_Restaurant_Block_A": "SpecRest_A",
    "Specialty_Restaurant_Block_B": "SpecRest_B",
    "Specialty_Galley_Block": "SpecGalley",
    "Central_Park_Open_Atrium": "CentralPark",
    "Shopping_Retail_Block": "ShopRetail",
    "Spa_Fitness_Complex": "SpaFitness",
    "Engine_Control_Room": "EngControl",
    "Windjammer_Buffet": "Windjammer",
    "Buffet_Galley_Upper": "BuffetGal_U",
    "Waste_Treatment_Plant": "WasteTreat",
    "Cafe_Bakery_Block": "CafeBakery",
    "Comedy_Club_Lounge": "ComedyClub",
    "Library_Card_Room": "LibraryCard",
    "Crew_Mess_Forward": "CrewMess_Fwd",
}

GALAXY = {
    "Main_Engineering": "MainEng",
    "Stellar_Cartography": "StellarCarto",
}

CONSTITUTION = {
    "Officer_Quarters": "OfficerQtrs",
    "Security_Station": "Security",
    "Transporter_Room": "Transporter",
}


def mega_map(zone_ids: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for zid in zone_ids:
        if zid in MEGA_AMENITY:
            out[zid] = MEGA_AMENITY[zid]
            continue
        mapped = _pax_corridor(zid) or _crew_corridor(zid)
        if mapped:
            out[zid] = mapped
    return out


def _replace_in_text(text: str, mapping: dict[str, str]) -> str:
    # Longest keys first so prefixes don't partially replace.
    for old in sorted(mapping, key=len, reverse=True):
        text = text.replace(old, mapping[old])
    return text


def _rewrite_json_file(path: Path, mapping: dict[str, str]) -> bool:
    raw = path.read_text(encoding="utf-8")
    new = _replace_in_text(raw, mapping)
    if new == raw:
        return False
    # Validate JSON still parses when applicable
    if path.suffix == ".json":
        json.loads(new)
    path.write_text(new, encoding="utf-8")
    return True


def main() -> int:
    spatial = json.loads(
        (REPO / "data/platforms/mega_cruise_5000/spatial_layout.json").read_text()
    )
    mega = mega_map([z["id"] for z in spatial["zones"]])
    assert all(len(v) <= 15 for v in mega.values()), {
        k: v for k, v in mega.items() if len(v) > 15
    }
    assert len(set(mega.values())) == len(mega)

    platforms = {
        "mega_cruise_5000": mega,
        "enterprise_galaxy_tng": GALAXY,
        "enterprise_constitution_tos": CONSTITUTION,
    }

    # Combined map for shared config files (mega + enterprise only).
    combined: dict[str, str] = {}
    for m in platforms.values():
        combined.update(m)

    platform_globs = [
        "spatial_layout.json",
        "air_flow_paths.json",
        "deck_manifest.json",
        "deck_graphics.geojson",
        "contam/path_map.json",
        "contam/hobbyist_overrides.json",
    ]
    changed: list[str] = []
    for plat, mapping in platforms.items():
        base = REPO / "data" / "platforms" / plat
        for rel in platform_globs:
            path = base / rel
            if path.is_file() and _rewrite_json_file(path, mapping):
                changed.append(str(path.relative_to(REPO)))

    # Shared / cross-cutting files (only Contam-platform renames).
    # Do NOT rewrite class_interactions_default/expedition amenity names —
    # messy_cruise_500 / expedition still use long amenity IDs.
    extra_full = [
        "data/platforms/deck_provenance.json",
        "data/templates/enterprise_galaxy_tng.json",
        "data/templates/enterprise_constitution_tos.json",
        "data/config/contam_compare/jobs/mega_cruise_transport.json",
        "presidio/data/social/class_interactions_mega_cruise.json",
        "scripts/generate_mega_cruise_cabin_layout.py",
        "scripts/build_enterprise_platforms.py",
        "scripts/enterprise_deck_graphics.py",
        "tests/test_architectural_graphics.py",
        "tests/test_cabin_corridor_transmission.py",
        "tests/test_shedding_variance_cabin_mates.py",
        "tests/test_graywater_zones.py",
        "docs/PLATFORM_CABIN_REVISION.md",
        "docs/SHEDDING_AND_CABINMATES.md",
    ]
    for rel in extra_full:
        path = REPO / rel
        if path.is_file() and _rewrite_json_file(path, combined):
            changed.append(rel)

    # Constitution-only zone IDs may appear in shared social defaults.
    constitution_only = {
        "Officer_Quarters": "OfficerQtrs",
        "Security_Station": "Security",
        "Transporter_Room": "Transporter",
    }
    for rel in (
        "presidio/data/social/class_interactions_default.json",
        "presidio/data/social/class_interactions_expedition.json",
    ):
        path = REPO / rel
        if path.is_file() and _rewrite_json_file(path, constitution_only):
            changed.append(rel)

    print(f"renamed {len(mega)} mega + {len(GALAXY)} galaxy + {len(CONSTITUTION)} constitution")
    print(f"updated {len(changed)} files")
    for c in changed:
        print(f"  {c}")

    # Sanity: no long IDs remain on Contam platforms
    for plat in platforms:
        ids = [
            z["id"]
            for z in json.loads(
                (REPO / f"data/platforms/{plat}/spatial_layout.json").read_text()
            )["zones"]
        ]
        long = [i for i in ids if len(i) > 15]
        if long:
            print(f"FAIL {plat} still long: {long}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
