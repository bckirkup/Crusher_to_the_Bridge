#!/usr/bin/env python3
"""Derive shared sanitary (public head) provisioning for every platform.

The provisioning rules are regulatory, not fitted. Each served zone is
classified into one occupancy class, and each class carries a published
fixture ratio:

  galley / food-preparation area
      CDC VSP 2025 Construction Standards Sec. 7.3.1: at least one employee
      toilet room near the work area of all food preparation areas, one
      toilet per 25 employees on the maximum shift, located inside the food
      preparation area or in a passageway immediately outside it.
  child activity centre
      VSP 2025 Sec. 34.1.2: one child-sized toilet per 25 children at
      maximum capacity.
  recreational water facility (pool, waterpark, solarium, sports deck)
      VSP 2025 Sec. 26.5/26.6 place toilet facilities within 60 m walking
      distance of every RWF and every waterslide staircase entrance but
      state no fixture count; the count uses the IPC Table 403.1 ratio for
      indoor pools (1 per 75 male for the first 1,500, 1 per 40 female for
      the first 1,520).
  assembly (theatre, casino, promenade, lounge, library, spa, shops,
  reception, gallery)
      IPC Table 403.1 assembly ratio: 1 per 125 male, 1 per 65 female.
  food service (dining room, buffet, specialty, crew mess)
      IPC Table 403.1 restaurant ratio: 1 per 75 male, 1 per 75 female.
  navigating bridge / machinery space
      MLC 2006 Standard A3.1.11(b): sanitary facilities within easy access of
      the navigating bridge and the machinery space or engine room control
      centre. One toilet each; the watch complement is small.
  service work area (laundry, stores, waste treatment) and medical
      IPC Table 403.1 business ratio, 1 per 25 for the first 50 occupants.

Occupant loads are the layout's own ``max_occupancy``, split 50/50 by sex.
MLC A3.1.11(a) and VSP Sec. 36 require separate facilities for men and for
women, so provisioning is emitted per (deck cluster x sex).

Geometry and ventilation:
  floor area  2.7 m^2 per water closet -- a 0.9 x 1.5 m stall footprint
              doubled to carry the handwashing and circulation share.
              Declared geometry, Grade C: no source measures ship head area.
  height      2.3 m; MLC 2006 Standard A3.1.6 sets a 2.03 m headroom floor.
  volume      2.7 x 2.3 = 6.21 m^3 per water closet.
  ach         ASHRAE 62.1 Table 6-5 public toilets, 70 cfm per water closet
              intermittent = 118.9 m^3/h, i.e. 19.2 ACH independently of the
              fixture count.

This module is the single source of the provisioning arithmetic: the
layout generators (cruise recipes, mega, Enterprise) call
``sanitary_zone_dicts`` / ``sanitary_airflow_augment`` on the zones they
just built, and the hand-authored hulls go through
``augment_platform_files``. ``main`` only reports.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

PLATFORM_ROOT = Path("data/platforms")

FLOOR_AREA_M2_PER_WC = 2.7
CEILING_HEIGHT_M = 2.3
VOLUME_M3_PER_WC = FLOOR_AREA_M2_PER_WC * CEILING_HEIGHT_M
EXHAUST_M3H_PER_WC = 70.0 * 1.699  # 70 cfm -> m^3/h
SANITARY_ACH = EXHAUST_M3H_PER_WC / VOLUME_M3_PER_WC  # ~19.2, fixture-independent
MAX_WC_PER_BLOCK = 10

GALLEY_TOKENS = ("galley",)
CHILD_TOKENS = ("kids", "teen", "school", "youth")
RWF_TOKENS = ("pool", "waterpark", "solarium", "sports", "aqua", "rink")
MACHINERY_TOKENS = ("engine", "engcontrol", "engine_control", "machinery")
BRIDGE_TOKENS = ("bridge", "cic")
SERVICE_TOKENS = ("laundry", "stores", "waste", "hangar", "armory", "brig")
EXCLUDE_TOKENS = ("head", "isol", "airlock", "flight_deck", "well_deck")

_TRAFFIC_RANK = {"low": 0, "medium": 1, "high": 2}


@dataclass(frozen=True)
class SanitaryBlock:
    """One public head block: a deck cluster x sex (x split) provision."""

    zone_id: str
    deck: str
    sex: str  # "male" | "female"
    water_closets: int
    serves: tuple[str, ...]
    classes: tuple[str, ...]
    description: str = ""
    display: dict[str, float] = field(default_factory=dict)
    elevation_m: float | None = None
    traffic: str = "medium"


def classify(zone: dict) -> str | None:
    """Return the provisioning class of a served zone, or None if unserved."""
    zid = zone["id"].lower()
    ztype = zone["type"]
    if ztype == "Sanitary":
        return None  # heads do not provision heads
    if any(t in zid for t in EXCLUDE_TOKENS):
        return None
    if ztype in ("Cabin_Corridor", "Room"):
        return None  # private cabin fittings; MLC A3.1.11(c) exemption
    if zone.get("dining_service_type") == "galley" or any(
        t in zid for t in GALLEY_TOKENS
    ):
        return "galley"
    if any(t in zid for t in CHILD_TOKENS):
        return "child"
    if any(t in zid for t in RWF_TOKENS):
        return "rwf"
    if any(t in zid for t in BRIDGE_TOKENS):
        return "bridge"
    if any(t in zid for t in MACHINERY_TOKENS):
        return "machinery"
    if any(t in zid for t in SERVICE_TOKENS):
        return "service"
    if ztype == "Dining":
        return "food_service"
    if ztype == "Medical":
        return "service"
    if ztype == "Engineering":
        return "machinery"
    return "assembly"


def water_closets(cls: str, occ: int) -> tuple[int, int]:
    """Return (male, female) water closets required for one served zone."""
    half = occ / 2.0
    if cls == "galley":
        total = math.ceil(occ / 25)
        return (math.ceil(total / 2), total - math.ceil(total / 2))
    if cls == "child":
        total = math.ceil(occ / 25)
        return (math.ceil(total / 2), total - math.ceil(total / 2))
    if cls == "rwf":
        return (math.ceil(half / 75), math.ceil(half / 40))
    if cls == "assembly":
        return (math.ceil(half / 125), math.ceil(half / 65))
    if cls == "food_service":
        return (math.ceil(half / 75), math.ceil(half / 75))
    if cls in ("bridge", "machinery"):
        return (1, 0)
    if cls == "service":
        return (math.ceil(half / 25), math.ceil(half / 25))
    raise ValueError(cls)


def _deck_token(deck: str, *, letters_len: int = 1) -> str:
    """A short token for a deck label: leading digits + a letter prefix.

    ``letters_len`` widens the letter prefix for collision resolution, e.g.
    ``saucer_1`` -> ``1S`` vs ``secondary_1`` -> ``1SE``.
    """
    parts = re.findall(r"[A-Za-z]+|\d+", deck)
    digits = [p for p in parts if p.isdigit()]
    letters = [p for p in parts if not p.isdigit()]
    joined = "".join(letters)
    if digits:
        token = digits[0] + joined[:letters_len]
    else:
        token = joined[:7] if letters else re.sub(r"\W", "", deck)[:7]
    return token.upper()


def _unique_deck_tokens(decks: list[str]) -> dict[str, str]:
    """Deterministic deck-label tokens, widened on collision."""
    tokens: dict[str, str] = {}
    for deck in sorted(decks):
        for length in range(1, 10):
            token = _deck_token(deck, letters_len=length)
            if token not in tokens.values():
                break
        if token in tokens.values():
            raise ValueError(f"no unique deck token for {deck!r}")
        tokens[deck] = token
    return tokens


def derive_blocks(zones: list[dict]) -> list[SanitaryBlock]:
    """Provision head blocks for a platform's zones.

    Clusters are the layout's ``deck`` labels; occupant loads are the served
    zone's ``max_occupancy`` (or a volume-implied fallback), split 50/50.
    Blocks over ``MAX_WC_PER_BLOCK`` water closets split into fore/aft pairs.
    ``Sanitary`` zones in *zones* are ignored by the classifier, so this is
    safe to re-run on an already-augmented layout (the same blocks come out).
    """
    clusters: dict[str, dict] = {}
    for zone in zones:
        cls = classify(zone)
        if cls is None:
            continue
        occ = zone.get("max_occupancy")
        if occ is None:
            occ = max(2, int(zone["volume_m3"] / 10))
        male, female = water_closets(cls, int(occ))
        deck = zone.get("deck", "unknown")
        entry = clusters.setdefault(
            deck, {"male": 0, "female": 0, "serves": [], "classes": set()}
        )
        entry["male"] += male
        entry["female"] += female
        entry["serves"].append(zone["id"])
        entry["classes"].add(cls)

    zones_by_id = {z["id"]: z for z in zones}
    tokens = _unique_deck_tokens(sorted(clusters))
    blocks: list[SanitaryBlock] = []
    for deck in sorted(clusters):
        token = tokens[deck]
        entry = clusters[deck]
        for sex in ("male", "female"):
            count = entry[sex]
            if count == 0:
                continue
            splits = math.ceil(count / MAX_WC_PER_BLOCK)
            per = math.ceil(count / splits)
            for i in range(splits):
                suffix = f"_{i + 1}" if splits > 1 else ""
                blocks.append(_block_from(
                    f"HD_{token}_{sex[0].upper()}{suffix}",
                    deck, sex, per, entry, zones_by_id,
                ))
    return blocks


def _block_from(
    zone_id: str,
    deck: str,
    sex: str,
    wc: int,
    cluster: dict,
    zones_by_id: dict[str, dict],
) -> SanitaryBlock:
    served = [zones_by_id[sid] for sid in cluster["serves"] if sid in zones_by_id]
    xs = [float(s.get("display", {}).get("x", 0.0)) for s in served]
    ys = [float(s.get("display", {}).get("y", 0.0)) for s in served]
    elevations = [s["elevation_m"] for s in served if s.get("elevation_m") is not None]
    traffic = max(
        (str(s.get("traffic", "medium")) for s in served),
        key=lambda t: _TRAFFIC_RANK.get(t, 1),
        default="medium",
    )
    serves = tuple(cluster["serves"])
    shown = ", ".join(serves[:4])
    if len(serves) > 4:
        shown += f", +{len(serves) - 4} more"
    return SanitaryBlock(
        zone_id=zone_id,
        deck=deck,
        sex=sex,
        water_closets=wc,
        serves=serves,
        classes=tuple(sorted(cluster["classes"])),
        description=(
            f"Public head ({sex}, {wc} water closet"
            f"{'s' if wc != 1 else ''}) serving {shown}."
        ),
        display={
            "x": (sum(xs) / len(xs)) if xs else 0.0,
            "y": (sum(ys) / len(ys)) - 4.0 if ys else 0.0,
        },
        elevation_m=elevations[0] if elevations else None,
        traffic=traffic,
    )


def block_zone_dict(block: SanitaryBlock) -> dict:
    """The spatial_layout zone record for one head block."""
    zone = {
        "id": block.zone_id,
        "type": "Sanitary",
        "traffic": block.traffic,
        "volume_m3": round(block.water_closets * VOLUME_M3_PER_WC, 2),
        "floor_area_m2": round(block.water_closets * FLOOR_AREA_M2_PER_WC, 2),
        "ceiling_height_m": CEILING_HEIGHT_M,
        "deck": block.deck,
        "base_ach": round(SANITARY_ACH, 1),
        "max_occupancy": block.water_closets,
        "serves": list(block.serves),
        "display": block.display,
        "description": block.description,
    }
    if block.elevation_m is not None:
        zone["elevation_m"] = block.elevation_m
    return zone


def sanitary_zone_dicts(zones: list[dict]) -> list[dict]:
    """Zone records for every provisioned head block over *zones*.

    Blocks whose id is already present are skipped, so this is safe to call
    on a layout that already carries its heads.
    """
    existing = {z["id"] for z in zones}
    return [
        block_zone_dict(b)
        for b in derive_blocks(zones)
        if b.zone_id not in existing
    ]


def _served_ahu(
    block: SanitaryBlock,
    hvac_zones: list[dict],
    zones_by_id: dict[str, dict],
) -> str | None:
    """The HVAC group whose branch carries this head's makeup air.

    Chosen by how many of the block's served rooms sit on the branch; ties
    resolve to the first sorted group id. If no served room is ducted at
    all (an all-exterior cluster), fall back to the branch covering most
    same-deck rooms, then the first group. ``None`` only if no groups exist.
    """
    # A head is exhaust-only and never carries another head's makeup air.
    branches = [
        g for g in hvac_zones if not str(g.get("id", "")).startswith("AHU_HD_")
    ]
    if not branches:
        return None
    serves = set(block.serves)
    scored = sorted(
        branches,
        key=lambda g: (-len(serves & set(g.get("rooms", []))), str(g["id"])),
    )
    if serves & set(scored[0].get("rooms", [])):
        return str(scored[0]["id"])
    # All-exterior cluster (e.g. a pool-deck head): makeup comes from the
    # branch covering most zones on the same deck number, else the first
    # sorted branch.
    deck_no = block.deck.split("_")[0]
    same_deck = {
        z["id"] for z in zones_by_id.values()
        if str(z.get("deck", "")).split("_")[0] == deck_no
    }
    scored = sorted(
        branches,
        key=lambda g: (-len(same_deck & set(g.get("rooms", []))), str(g["id"])),
    )
    if same_deck & set(scored[0].get("rooms", [])):
        return str(scored[0]["id"])
    return str(sorted(branches, key=lambda g: str(g["id"]))[0]["id"])


def sanitary_airflow_augment(
    zones: list[dict],
    airflow: dict,
) -> dict:
    """Append exhaust-only HVAC groups and one-way makeup links for heads.

    Every head block becomes its own ``hvac_zones`` entry (exhaust only:
    ``oa_fraction`` 1.0, ``hvac_duty`` 0, ``ach`` 19.2) and gets exactly one
    directional ``cross_zone_links`` edge from the served space's group to
    the head's -- never a reverse edge and never an ``adjacency`` edge, so a
    head cannot be an air source for the space it serves.
    """
    hvac = list(airflow.get("hvac_zones", []))
    zones_by_id = {z["id"]: z for z in zones}
    # Drop stale or malformed head links: a head AHU is never a link source,
    # and only Sanitary_Makeup edges may end at one.
    cross = [
        c for c in airflow.get("cross_zone_links", [])
        if not (
            str(c.get("from", "")).startswith("AHU_HD_")
            or (
                str(c.get("to", "")).startswith("AHU_HD_")
                and c.get("path") != "Sanitary_Makeup"
            )
        )
    ]
    existing_ahus = {str(g["id"]) for g in hvac}
    wired = {
        str(c["to"]) for c in cross
        if str(c.get("to", "")).startswith("AHU_HD_")
    }
    for block in derive_blocks(zones):
        ahu_id = f"AHU_{block.zone_id}"
        if ahu_id not in existing_ahus:
            hvac.append({
                "id": ahu_id,
                "rooms": [block.zone_id],
                "ach": round(SANITARY_ACH, 1),
                "oa_fraction": 1.0,
                "hvac_duty": 0.0,
                "description": (
                    f"Exhaust-only sanitary branch ({block.zone_id}, "
                    f"{block.water_closets} WC); makeup air enters from the "
                    f"served space's branch and leaves overboard."
                ),
            })
        if ahu_id in wired:
            continue
        source = _served_ahu(block, hvac, zones_by_id)
        if source is not None:
            cross.append({
                "from": source,
                "to": ahu_id,
                "flow_rate_m3h": round(
                    block.water_closets * EXHAUST_M3H_PER_WC, 1,
                ),
                "is_hvac_ducted": False,
                "path": "Sanitary_Makeup",
                "description": (
                    f"Transfer air into {block.zone_id}; the head exhausts "
                    f"overboard, never back to the served space."
                ),
            })
    out = dict(airflow)
    out["hvac_zones"] = hvac
    out["cross_zone_links"] = cross
    return out


def augment_platform_files(platform_dir: Path) -> int:
    """Write head zones + air wiring into a hand-authored platform dir.

    Returns the number of head blocks added.
    """
    layout_path = platform_dir / "spatial_layout.json"
    airflow_path = platform_dir / "air_flow_paths.json"
    layout = json.loads(layout_path.read_text())
    zones = layout["zones"]
    heads = sanitary_zone_dicts(zones)
    if heads:
        layout["zones"] = zones + heads
        layout_path.write_text(json.dumps(layout, indent=2) + "\n")
    if airflow_path.exists():
        airflow = json.loads(airflow_path.read_text())
        augmented = sanitary_airflow_augment(layout["zones"], airflow)
        if augmented != airflow:
            airflow_path.write_text(json.dumps(augmented, indent=2) + "\n")
    return len(heads)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", action="append")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write head zones/air wiring into hand-authored platform dirs.",
    )
    args = parser.parse_args()
    platforms = args.platform or sorted(
        p.name for p in PLATFORM_ROOT.iterdir() if p.is_dir()
    )
    for platform in platforms:
        pdir = PLATFORM_ROOT / platform
        if args.write:
            added = augment_platform_files(pdir)
            print(f"{platform}: wrote {added} head zones")
            continue
        layout = json.loads((pdir / "spatial_layout.json").read_text())
        blocks = derive_blocks(layout["zones"])
        total_wc = sum(b.water_closets for b in blocks)
        total_vol = total_wc * VOLUME_M3_PER_WC
        print(f"== {platform}")
        for b in blocks:
            print(
                f"   {b.deck:<20} {b.sex:<6} wc={b.water_closets:<3} "
                f"vol={b.water_closets * VOLUME_M3_PER_WC:7.1f} "
                f"serves={len(b.serves)}"
            )
        print(
            f"   -> {len(blocks)} head zones, {total_wc} water closets, "
            f"{total_vol:.0f} m^3 total, ach={SANITARY_ACH:.1f}"
        )


if __name__ == "__main__":
    main()
