#!/usr/bin/env python3
"""Derived envelope for the fomite areal denominator (NORO-HIGH-TOUCH-AREA-01).

``HIGH_TOUCH_AREA_M2`` is the denominator of every fomite pickup: the pool's
mass enters a touch only as ``mass / A``. Nobody has measured *high-touch*
area per room, so the table is a declared assumption (Grade C). This script
does not measure it either. It **bounds** it, by doing arithmetic nobody in
this repository had done: enumerated high-touch item sets (literature) times
per-item areas (literature where an item was measured, declared geometry where
it was not), evaluated against the actual ``classic_cruise_1900`` zones, with
the measured total object-surface inventories as the ceiling.

Four quantities per zone class, all *derived*, none adopted:

* ``hardware`` -- the narrow reading of "high touch": hand-contact hardware
  only (handles, switches, taps, flush actuators, seats, rails, remotes,
  buttons, utensils). This is the reading the shipped sanitary constant's
  own comment uses ("a hardware area, NOT a footprint").
* ``broad`` -- hardware plus the touched planes of furniture (table tops,
  chair seats and backs, desks, counters), i.e. what an observational
  high-touch study would mark as touched at least once.
* ``shared`` -- the single operational definition of
  NORO-HIGH-TOUCH-DEFINITION-01: the touched extent of surfaces that more
  than one of the zone's occupants touches over an occupancy cycle, i.e.
  the same shared/public-surface set whose touch rates
  ``SURFACE_CONTACTS_PER_HOUR`` already counts (Jin 2022 classes T+R,
  excluding PP/PT; Ackerley 2025 lobby fomites; Carling 2009 shipboard
  restroom objects; Zhang 2018/2021 public-vs-private touch network).
  Derived, Grade C, and adopted nowhere.
* ``ceiling`` -- total object-plus-material surface area of the room from the
  two measured indoor inventories, via the surface-to-volume ratio applied to
  the zone's declared air volume. An area above this is impossible; it is a
  refutation bound, not a target.

The output is an envelope and the per-zone-class multiplier that maps the
shipped table onto each end of it. Those multipliers are the sweep arms of
``docs/ledger/NORO-HIGH-TOUCH-AREA-01.md``. **No constant is changed by this
script.** The item tables themselves now live in ``engines/fomite_surfaces``
(NORO-FOMITE-DISAGG-01) and are re-imported here, so the engine's
default-off per-surface arm and this envelope read one enumeration.

Sources, each recorded at the item or count it supports:

* Park 2015 (DOI 10.1128/aem.01657-15) -- toilet seat sampling surface
  700 cm2; swabbed areas 25.8-645 cm2; cruise-ship cabin and common-area
  swab campaign (92 samples).
* Gerba 2025 -- sampled-object areas from 10 cm2 (toilet flush handle) to
  385-500 cm2 (restroom floor).
* Weir 2016 (DOI 10.1021/acs.est.5b06275) -- a QMRA that declares its fomite
  areas: aluminium 0.017 ft2 = 15.8 cm2, plastic laminate 0.638 ft2 =
  593 cm2, wood laminate 11.25 ft2 = 1.05 m2; fingertip-per-touch area
  0.0108 ft2 = 10.0 cm2 for ten fingers.
* Zambrana 2023 (DOI 10.1021/acsenvironau.3c00025) -- across 275 fomite data
  sets, 26% swabbed <50 cm2, 23% 50-100 cm2, 12% >100 cm2: the object scale
  at which fomite sampling is done.
* Huslage 2010 (DOI 10.1086/655016) -- 5 high-touch surfaces from 50 observed
  interactions. Murphy 2011 (DOI 10.1071/hi11024) -- 7 predefined high-touch
  objects per room over 37 rooms. Heo 2023 (DOI 10.53713/nhsj.v3i2.242) -- a
  38-item high-touch list (questionnaire, not observation).
* Carling 2009 (DOI 10.1086/606058) -- 8,344 objects in 273 public restrooms
  on 56 cruise ships: 30.6 evaluated objects per shipboard public restroom.
* Lei 2017 (DOI 10.1038/s41598-017-13840-z) -- 422 enumerated touchable
  surfaces in a 21-row Boeing 737 economy cabin (126 seats): 3.3 surfaces per
  seat in a dense public seating space.
* Manuja 2019 (DOI 10.1039/c9em00157c) -- 22 rooms measured at ~1 cm
  resolution: surface-to-volume 3.2 +/- 1.2 m^-1 including contents.
  Hodgson 2005 (DOI 10.2172/861239) -- 33 rooms, objects >=300 cm2,
  bedroom S/V 2.3-4.7 m2/m3.

Per-item areas carry a ``src`` tag: ``measured`` (read off a paper),
``qmra`` (declared by a published QMRA), or ``declared`` (this repository's
own geometry for an item nobody measured -- the residual Grade C content of
the envelope, and the reason the envelope is a range and not a value).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.fomite_surfaces import (  # noqa: E402
    ITEM_AREA_M2,
    ZONE_ITEM_SETS,
)
from engines.transmission_core import (  # noqa: E402
    HIGH_TOUCH_AREA_M2,
    SANITARY_HIGH_TOUCH_AREA_M2_PER_WC,
)
from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_child_path,
)

LAYOUT = (
    REPO_ROOT / "data" / "platforms" / "classic_cruise_1900" / "spatial_layout.json"
)

# Measured total object+material surface per unit air volume (the ceiling).
CEILING_S_OVER_V_M2_PER_M3 = {
    "central": 3.2,
    "low": 2.0,
    "high": 4.4,
    "src": "Manuja 2019 3.2 +/- 1.2 m^-1 with contents; Hodgson 2005 bedroom 2.3-4.7",
}
# A stateroom compartment is not a layout zone; its volume is the berth share
# of a Cabin_Corridor block. Declared here only to place the cabin ceiling.
CABIN_COMPARTMENT_VOLUME_M3 = 40.0


def _sum_items(counts: dict[str, float]) -> float:
    return sum(ITEM_AREA_M2[item][0] * n for item, n in counts.items())


def _zone_occupancies(layout_path: Path) -> dict[str, list[dict[str, float]]]:
    """Occupancy and volume of every layout zone, by fomite zone class."""
    layout = json.loads(layout_path.read_text())
    by_class: dict[str, list[dict[str, float]]] = {}
    for zone in layout["zones"]:
        zone_class = _layout_zone_class(zone)
        by_class.setdefault(zone_class, []).append(
            {
                "id": zone["id"],
                "occupancy": float(zone.get("max_occupancy", 0) or 0),
                "volume_m3": float(zone.get("volume_m3", 0.0) or 0.0),
            },
        )
    return by_class


def _layout_zone_class(zone: dict[str, Any]) -> str:
    """Mirror ``TransmissionCore._fomite_zone_class`` over a layout record."""
    lowered = str(zone["id"]).lower()
    zone_type = zone.get("type", "")
    if "galley" in lowered or "service" in lowered:
        return "galley"
    if "crew" in lowered and ("mess" in lowered or "berth" in lowered):
        return "crew_mess"
    if zone_type in ("Cabin_Corridor", "Room"):
        return "cabin"
    if zone_type == "Dining":
        return "dining"
    if zone_type == "Sanitary":
        return "sanitary"
    return "public"


def _representative_occupancy(zone_class: str, zones: list[dict[str, float]]) -> float:
    """Occupancy of the unit the item set is written for.

    Occupancy-weighted, so a class is represented by the zones that actually
    carry its touches rather than by the arithmetic mean of a 400-seat main
    dining room and an 80-seat specialty restaurant.
    """
    if zone_class == "cabin":
        return float(ZONE_ITEM_SETS["cabin"]["occupants"])
    if zone_class == "sanitary":
        return 1.0
    total = sum(z["occupancy"] for z in zones)
    if total <= 0.0:
        return 0.0
    return sum(z["occupancy"] ** 2 for z in zones) / total


def _representative_volume(zone_class: str, zones: list[dict[str, float]]) -> float:
    if zone_class == "cabin":
        return CABIN_COMPARTMENT_VOLUME_M3
    if zone_class == "sanitary":
        volumes = [z["volume_m3"] for z in zones if z["volume_m3"] > 0.0]
        return sum(volumes) / len(volumes) if volumes else 0.0
    weight = sum(z["occupancy"] for z in zones)
    if weight <= 0.0:
        volumes = [z["volume_m3"] for z in zones]
        return sum(volumes) / len(volumes) if volumes else 0.0
    return sum(z["occupancy"] * z["volume_m3"] for z in zones) / weight


def _envelope_for_class(
    zone_class: str, zones: list[dict[str, float]],
) -> dict[str, Any]:
    spec = ZONE_ITEM_SETS[zone_class]
    occupancy = _representative_occupancy(zone_class, zones)
    volume = _representative_volume(zone_class, zones)

    hardware = _sum_items(spec.get("hardware_fixed", {}))
    hardware += occupancy * _sum_items(spec.get("hardware_per_occupant", {}))
    broad = hardware
    broad += _sum_items(spec.get("broad_extra_fixed", {}))
    broad += occupancy * _sum_items(spec.get("broad_extra_per_occupant", {}))

    shared = _sum_items(spec.get("shared_fixed", {}))
    shared += occupancy * _sum_items(spec.get("shared_per_occupant", {}))

    shipped = (
        SANITARY_HIGH_TOUCH_AREA_M2_PER_WC
        if zone_class == "sanitary"
        else HIGH_TOUCH_AREA_M2[zone_class]
    )
    ceiling = volume * CEILING_S_OVER_V_M2_PER_M3["central"]
    return {
        "unit": spec["unit"],
        "count_anchor": spec["count_anchor"],
        "representative_occupancy": occupancy,
        "representative_volume_m3": volume,
        "shipped_m2": shipped,
        "hardware_m2": hardware,
        "broad_m2": broad,
        "shared_m2": shared,
        "ceiling_total_surface_m2": ceiling,
        "scale_to_hardware": hardware / shipped,
        "scale_to_broad": broad / shipped,
        "scale_to_shared": shared / shipped,
        "shared_m2_per_occupant": shared / occupancy if occupancy > 0 else None,
        "shipped_m2_per_occupant": shipped / occupancy if occupancy > 0 else None,
        "shipped_over_ceiling": shipped / ceiling if ceiling > 0.0 else None,
        "shipped_inside_envelope": hardware <= shipped <= broad,
        "zones": [z["id"] for z in zones],
    }


def build_envelope(layout_path: Path = LAYOUT) -> dict[str, Any]:
    by_class = _zone_occupancies(layout_path)
    classes = {}
    for zone_class in ZONE_ITEM_SETS:
        classes[zone_class] = _envelope_for_class(
            zone_class, by_class.get(zone_class, []),
        )
    return {
        "what_this_is": (
            "A derived envelope for the fomite areal denominator, not a "
            "measurement and not an adopted constant. Item counts are "
            "enumerated from published high-touch inventories; item areas are "
            "measured, QMRA-declared or declared here, per ITEM_AREA_M2."
        ),
        "platform": "classic_cruise_1900",
        "ceiling_basis": CEILING_S_OVER_V_M2_PER_M3,
        "item_areas_m2": {
            name: {"area_m2": area, "src": src, "note": note}
            for name, (area, src, note) in ITEM_AREA_M2.items()
        },
        "declared_item_area_share": sum(
            1 for _, src, _ in ITEM_AREA_M2.values() if src == "declared"
        )
        / len(ITEM_AREA_M2),
        "classes": classes,
        "sweep_arms": {
            "hardware": {
                k: round(v["scale_to_hardware"], 3) for k, v in classes.items()
            },
            "broad": {k: round(v["scale_to_broad"], 3) for k, v in classes.items()},
            "shared": {
                k: round(v["scale_to_shared"], 3) for k, v in classes.items()
            },
        },
    }


def _markdown(envelope: dict[str, Any]) -> str:
    lines = [
        "| zone class | unit | rep. occ. | shipped A (m2) | hardware (m2) | "
        "broad (m2) | shared (m2) | ceiling (m2) | x to hardware | x to broad | "
        "x to shared |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, row in envelope["classes"].items():
        lines.append(
            f"| {name} | {row['unit']} | {row['representative_occupancy']:.0f} | "
            f"{row['shipped_m2']:.2f} | {row['hardware_m2']:.2f} | "
            f"{row['broad_m2']:.2f} | {row['shared_m2']:.2f} | "
            f"{row['ceiling_total_surface_m2']:.0f} | "
            f"{row['scale_to_hardware']:.2f} | {row['scale_to_broad']:.2f} | "
            f"{row['scale_to_shared']:.2f} |",
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default="docs/norovirus/noro_high_touch_area_01",
        help="directory for the envelope JSON",
    )
    parser.add_argument(
        "--markdown", action="store_true", help="print the table instead of JSON",
    )
    args = parser.parse_args(argv)

    envelope = build_envelope()
    out_dir = prepare_output_directory(
        str(args.out), allowed_roots=(str(REPO_ROOT),),
    )
    out_path = Path(
        resolve_child_path(str(out_dir), "high_touch_area_envelope.json"),
    )
    out_path.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n")
    print(_markdown(envelope) if args.markdown else json.dumps(envelope, indent=2))
    print(f"\nwrote {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
