"""Era-typed systems inference: vent/plumbing markers → airflow enrichment.

GA sheets do draw some of the systems layer — mushroom cowls and ventilators
on weather decks, VENT TRUNK/AIR SHAFT labels, fan rooms, the funnel over the
machinery space, named tanks — while the ductwork and pipe runs themselves
are absent.  This pass maps what the sheet shows through era-typed practice
rules into the airflow document, and records every step in a systems ledger
with its evidence grade: ``sheet_read`` (marker visible on the sheet),
``era_rule`` (mode from the era/zone-type table), ``default`` (no evidence).
"""

from __future__ import annotations

import json
import os
from typing import Any

from simulation_utils.paths import prepare_output_directory, validated_open
from tools.ship_blueprint_import.models import (
    ShipDigest,
    TankMarker,
    VentMarker,
)

# Zone-type → ventilation mode per era.  Modes:
#   mech_supply_exhaust — mechanical supply + exhaust (forced draft)
#   mech_ac             — mechanical recirculating air-conditioning
#   mech_exhaust        — mechanical exhaust, makeup drawn from adjacent spaces
#   fume_exhaust        — dedicated fume/lab exhaust
#   nat_supply          — natural supply via weather cowls, exhaust trunks
#   exhaust_only        — sanitary fixture contract (already wired)
#   open_air            — weather deck, no conditioning
#
# Provenance (repo convention: grade + origin at the point of definition,
# see .agents/skills/model-parameter-provenance and docs/GA_IMPORT_APPROACH.md
# §Era-rule provenance).  These are *practice* tables, not physical constants:
#
# - WW2 USN practice (cowled/mushroom natural supply + mechanical exhaust to
#   galley/heads/machinery; magazine ventilators of mushroom or cowl type):
#   NAVARMEDGUARD "General Instructions" §3109 (~1942), read via HyperWar
#   transcription.  Grade B.  Origin: Tr.
#   BuShips Technical Publication No. 6, "Pointers on Shipboard Ventilation"
#   (1944) is the identified period authority for the same practice; text not
#   retrieved this pass.  Origin: ?nr — do not treat it as a read source.
# - Modern/cold-war USN system taxonomy (mechanical supply & exhaust,
#   recirculating AC with outside-air makeup): NAVSEA S9086-RQ-STM-010
#   (NSTM ch. 510 "Heating, Ventilating, and Air Conditioning Systems for
#   Surface Ships"), ToC/§510-2 read.  Grade B.  Origin: Tr.
#   Corroborating secondary: "Ventilation Systems, US Navy Ships"
#   (bluewaternavy.org, NSTM-derived).  Grade C.  Origin: Sec.
# - RN WW2, NOAA/research, era cutoff years, and the MODE_OA_FRACTION numbers:
#   no source retrieved — declared engineering priors.  Grade C (standing
#   liability; revisit when a BUSHIPS DDS 810-x or Admiralty doc surfaces).
_M_MODES = {
    "Engineering": "mech_supply_exhaust",
    "Dining": "mech_exhaust",
    "Medical": "mech_supply_exhaust",
    "Room": "nat_supply",
    "Sanitary": "exhaust_only",
    "Free": "nat_supply",
}
ERA_RULES: dict[str, dict[str, Any]] = {
    "usn_ww2": {
        "label": "USN WW2 fleet practice",
        "modes": dict(_M_MODES),
        "note": "Cowled natural supply to accommodation; mechanical exhaust for "
        "galley, heads, machinery; magazines exhaust + flooding.",
    },
    "rn_ww2": {
        "label": "Royal Navy WW2 practice",
        "modes": dict(_M_MODES),
        "note": "Mushroom/cowl natural supply; mech exhaust galley/heads/engines; "
        "magazines sprinkled + vented.",
    },
    "usn_coldwar": {
        "label": "USN cold-war / early mechanical AC",
        "modes": {
            **_M_MODES,
            "Room": "mech_ac",
            "Medical": "mech_ac",
            "Dining": "mech_exhaust",
        },
        "note": "Berthing/officers mechanically conditioned; ops/electronics "
        "rooms AC; machinery forced draft.",
    },
    "usn_modern": {
        "label": "USN modern practice",
        "modes": {
            **_M_MODES,
            "Room": "mech_ac",
            "Medical": "mech_ac",
            "Free": "mech_supply_exhaust",
        },
        "note": "Mechanical conditioning shipwide except open weather decks.",
    },
    "noaa_research": {
        "label": "NOAA / research vessel practice",
        "modes": {
            "Engineering": "mech_supply_exhaust",
            "Dining": "mech_exhaust",
            "Medical": "mech_ac",
            "Room": "mech_ac",
            "Sanitary": "exhaust_only",
            "Free": "nat_supply",
        },
        "note": "Hotel spaces AC; laboratories fume-biased exhaust; machinery "
        "forced draft.",
    },
    "merchant_ww2": {
        "label": "Merchant / aux WW2 practice",
        "modes": dict(_M_MODES),
        "note": "Natural cowl supply to accommodation; mechanical exhaust to "
        "galley and machinery spaces.",
    },
    "generic": {
        "label": "Generic mechanical ventilation",
        "modes": {
            **_M_MODES,
            "Room": "mech_supply_exhaust",
            "Medical": "mech_supply_exhaust",
            "Dining": "mech_supply_exhaust",
            "Free": "mech_supply_exhaust",
        },
        "note": "Mechanical supply+exhaust assumed where no era is declared.",
    },
}

# Mode → group-level properties and the outdoor-air fraction a Contam group
# should carry when the mode supplies it.
MODE_OA_FRACTION = {
    "mech_supply_exhaust": 0.4,
    "mech_ac": 0.2,
    "mech_exhaust": 1.0,
    "fume_exhaust": 1.0,
    "nat_supply": 1.0,
    "exhaust_only": 1.0,
    "open_air": 1.0,
}

_KIND_DIRECTION = {
    "funnel": "exhaust",
    "uptake": "exhaust",
    "fan_room": "supply",
    "air_port": "supply",
    "skylight": "supply",
}
_FACING_DIRECTION = {
    "fore": "supply",
    "down": "supply",
    "aft": "exhaust",
    "up": "exhaust",
}

_MODE_PRIORITY = [
    "fume_exhaust",
    "mech_exhaust",
    "exhaust_only",
    "mech_ac",
    "mech_supply_exhaust",
    "nat_supply",
    "open_air",
]

_SANITARY_DRAIN_TYPES = {"Sanitary", "Dining", "Medical"}
_SEWAGE_TOKENS = ("sewage", "waste", "gray", "sullage", "soil", "bilge")
_FRESHWATER_TOKENS = ("f.w.", "fresh", "potable", "reserve")
_FUEL_TOKENS = ("fuel", "f.o.", "diesel", "oil")


def _marker_direction(marker: VentMarker) -> str:
    """Supply/exhaust for a marker: sheet label wins, then facing, then kind."""
    if marker.direction != "unknown":
        return marker.direction
    if marker.facing in _FACING_DIRECTION:
        return _FACING_DIRECTION[marker.facing]
    return _KIND_DIRECTION.get(marker.kind, "unknown")


def _marker_zone_mode(
    direction: str, kind: str, zone_type: str, era_mode: str
) -> str:
    """Marker kind + direction refined against the zone's era baseline.

    A cowled supply on a cabin is natural ventilation; the same gooseneck on
    an engine room is forced draft — the machinery space stays mechanical.
    Natural openings (skylights, air ports) are natural ventilation regardless
    of their resolved airflow direction.
    """
    if zone_type == "Sanitary":
        return "exhaust_only"
    if kind in ("skylight", "air_port"):
        return "nat_supply"
    if kind in ("funnel", "uptake", "fan_room", "air_shaft"):
        return "mech_supply_exhaust"
    if direction == "supply":
        if zone_type == "Engineering":
            return "mech_supply_exhaust"
        return "nat_supply"
    if direction == "exhaust":
        if zone_type == "Engineering":
            return "mech_supply_exhaust"
        return "mech_exhaust"
    return era_mode


def _marker_display(
    marker: VentMarker,
    digest: ShipDigest,
) -> tuple[float, float] | None:
    """Map a marker's normalized sheet position through its deck's plan map."""
    decks = {d.id: d for d in digest.decks}
    deck = decks.get(marker.deck or "") if marker.deck else None
    if deck is None:
        for d in digest.decks:
            if int(d.page) == marker.page:
                deck = d
                break
    if deck is None:
        return None
    bbox = deck.plan_bbox_norm or [0.0, 0.0, 1.0, 1.0]
    x_span = deck.hull_x_span_m or [0.0, digest.length_m]
    y_span = deck.hull_y_span_m or [0.0, digest.beam_m]
    bw = max(bbox[2] - bbox[0], 1e-6)
    bh = max(bbox[3] - bbox[1], 1e-6)
    mx = x_span[0] + (marker.position_norm[0] - bbox[0]) / bw * (
        x_span[1] - x_span[0]
    )
    my = y_span[0] + (marker.position_norm[1] - bbox[1]) / bh * (
        y_span[1] - y_span[0]
    )
    return (mx, my)


def _nearest_zone(
    x: float, y: float, zones_out: list[dict[str, Any]], deck: str | None
) -> str | None:
    cands = [z for z in zones_out if deck is None or z.get("deck") == deck]
    if not cands:
        cands = zones_out
    if not cands:
        return None
    return min(
        cands,
        key=lambda z: (
            (z.get("display", {}).get("x", 0.0) - x) ** 2
            + (z.get("display", {}).get("y", 0.0) - y) ** 2
        ),
    )["id"]


def _resolve_markers(
    digest: ShipDigest, zones_out: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Marker → served zone, direction, display position."""
    out: list[dict[str, Any]] = []
    zone_ids = {z["id"] for z in zones_out}
    for m in digest.systems.vent_markers:
        disp = _marker_display(m, digest)
        serves = m.serves_zone if m.serves_zone in zone_ids else None
        if serves is None and disp is not None:
            serves = _nearest_zone(disp[0], disp[1], zones_out, m.deck)
        out.append(
            {
                "id": m.id,
                "kind": m.kind,
                "facing": m.facing,
                "direction": _marker_direction(m),
                "deck": m.deck,
                "serves_zone": serves,
                "display": None if disp is None else [round(disp[0], 2), round(disp[1], 2)],
                "evidence": m.evidence,
                "notes": m.notes,
            }
        )
    return out


def _zone_modes(
    digest: ShipDigest,
    zones_out: list[dict[str, Any]],
    markers: list[dict[str, Any]],
) -> dict[str, dict[str, str]]:
    """Zone → ventilation mode + the evidence grade the mode came from."""
    era = ERA_RULES[digest.systems.era]
    modes: dict[str, dict[str, str]] = {}
    marker_zones: dict[str, list[dict[str, Any]]] = {}
    for m in markers:
        if m["serves_zone"]:
            marker_zones.setdefault(m["serves_zone"], []).append(m)
    for z in zones_out:
        zid = z["id"]
        if zid in marker_zones:
            marks = marker_zones[zid]
            direction = next(
                (m["direction"] for m in marks if m["direction"] != "unknown"),
                "unknown",
            )
            kind = next(
                (m["kind"] for m in marks if m["direction"] != "unknown"),
                marks[0]["kind"],
            )
            mode = _marker_zone_mode(
                direction,
                kind,
                z["type"],
                era["modes"].get(z["type"], "mech_supply_exhaust"),
            )
            ev = (
                "sheet_read"
                if any(m["evidence"] == "sheet_read" for m in marks)
                else "era_plausible"
            )
            modes[zid] = {"mode": mode, "evidence": ev}
            continue
        modes[zid] = {
            "mode": era["modes"].get(z["type"], "mech_supply_exhaust"),
            "evidence": "era_rule",
        }
    return modes


def _enrich_groups(
    airflow: dict[str, Any],
    zone_modes: dict[str, dict[str, str]],
    declared_oa_ids: set[str],
) -> None:
    for group in airflow.get("hvac_zones", []):
        if str(group.get("id", "")).startswith("AHU_HD_"):
            continue  # exhaust-only sanitary contract — untouched
        members = [
            (zone_modes[r]["mode"], zone_modes[r]["evidence"])
            for r in group.get("rooms", [])
            if r in zone_modes
        ]
        if not members:
            continue
        # A mode a sheet marker actually attributed beats an era-rule mode;
        # among equals, take the strongest-conditioning mode deterministically.
        sheet = [m for m, ev in members if ev == "sheet_read"]
        pool = sheet or [m for m, _ in members]
        mode = min(
            set(pool),
            key=lambda m, p=pool: (p.count(m) * -1, _MODE_PRIORITY.index(m)),
        )
        group["vent_mode"] = mode
        seen = {
            zone_modes[r]["evidence"] for r in group.get("rooms", [])
            if r in zone_modes
        }
        if "sheet_read" in seen:
            group["evidence"] = "sheet_read"
        elif "era_plausible" in seen:
            group["evidence"] = "era_plausible"
        else:
            group["evidence"] = "era_rule"
        # A hint that declares its own oa_fraction wins over the era prior.
        if group["id"] not in declared_oa_ids and "oa_fraction" not in group:
            group["oa_fraction"] = MODE_OA_FRACTION.get(mode, 0.2)


def _tank_kind(label: str) -> str:
    low = label.lower()
    if any(k in low for k in _SEWAGE_TOKENS):
        return "sewage"
    if any(k in low for k in _FRESHWATER_TOKENS):
        return "freshwater"
    if any(k in low for k in _FUEL_TOKENS):
        return "fuel"
    return "unknown"


def _tank_entry(
    t: TankMarker, digest: ShipDigest, zones_out: list[dict[str, Any]]
) -> tuple[dict[str, Any], str | None]:
    disp = _tank_display(t, digest)
    near = (
        _nearest_zone(disp[0], disp[1], zones_out, t.deck)
        if disp is not None else None
    )
    entry = {
        "label": t.label,
        "kind": _tank_kind(t.label),
        "nearest_zone": near,
        "display": (
            None if disp is None else [round(disp[0], 2), round(disp[1], 2)]
        ),
        "deck": t.deck,
        "notes": t.notes,
    }
    return entry, near


def _drain_note(
    z: dict[str, Any],
    zones_out: list[dict[str, Any]],
    sewage_ids: list[str],
) -> str:
    pool = [t for t in zones_out if t["id"] in sewage_ids] or zones_out
    near = _nearest_zone(
        z.get("display", {}).get("x", 0.0),
        z.get("display", {}).get("y", 0.0),
        pool,
        None,
    )
    return (
        f"{z['id']} ({z['type']}) drains soil/gray water to the "
        "collection/sea-discharge system; nearest marked tank: " + str(near)
    )


def _plumbing_notes(
    digest: ShipDigest, zones_out: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Tank labels → collection targets; drain zones → routing notes."""
    zone_ids = {z["id"] for z in zones_out}
    headish = [z for z in zones_out if z["type"] in _SANITARY_DRAIN_TYPES]
    tanks: list[dict[str, Any]] = []
    sewage_zone_ids: list[str] = []
    for t in digest.systems.tanks:
        entry, near = _tank_entry(t, digest, zones_out)
        if entry["kind"] == "sewage" and near in zone_ids:
            sewage_zone_ids.append(near)
        tanks.append(entry)
    drains = [_drain_note(z, zones_out, sewage_zone_ids) for z in headish]
    return tanks, drains, sewage_zone_ids


def _tank_display(
    t: TankMarker, digest: ShipDigest
) -> tuple[float, float] | None:
    marker = VentMarker(
        id="tank", page=t.page, position_norm=t.position_norm, deck=t.deck
    )
    return _marker_display(marker, digest)


def infer_systems(
    digest: ShipDigest,
    zones_out: list[dict[str, Any]],
    airflow: dict[str, Any],
    declared_oa_ids: set[str],
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    """Enrich airflow + build the systems ledger; returns (airflow, notes, extra_graywater)."""
    era = ERA_RULES[digest.systems.era]
    markers = _resolve_markers(digest, zones_out)
    zone_modes = _zone_modes(digest, zones_out, markers)
    _enrich_groups(airflow, zone_modes, declared_oa_ids)
    tanks, drains, sewage_ids = _plumbing_notes(digest, zones_out)
    notes = {
        "platform": digest.platform_id,
        "era": digest.systems.era,
        "era_label": era["label"],
        "era_note": era["note"],
        "vent_markers": markers,
        "zone_modes": zone_modes,
        "tanks": tanks,
        "plumbing_drains": drains,
    }
    return airflow, notes, sewage_ids


def write_systems_notes(
    output_dir: str, notes: dict[str, Any], *, allowed_roots: tuple[str, ...]
) -> None:
    """systems_notes.json (structured) + systems_notes.md (human ledger)."""
    prepare_output_directory(output_dir, allowed_roots=allowed_roots)
    jpath = os.path.join(output_dir, "systems_notes.json")
    with validated_open(jpath, "w", allowed_roots=allowed_roots, encoding="utf-8") as fh:
        json.dump(notes, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    lines = [
        f"# Systems inference notes — {notes['platform']}",
        "",
        f"Era: **{notes['era_label']}** (`{notes['era']}`)",
        "",
        notes["era_note"],
        "",
        "## Ventilation markers",
        "",
        "| marker | kind | facing | direction | serves zone | evidence |",
        "|---|---|---|---|---|---|",
    ]
    for m in notes["vent_markers"]:
        lines.append(
            f"| {m['id']} | {m['kind']} | {m['facing']} | {m['direction']} "
            f"| {m['serves_zone'] or '—'} | {m['evidence']} |"
        )
    lines += ["", "## Zone ventilation modes", "",
              "| zone | mode | evidence |", "|---|---|---|"]
    for zid, zm in sorted(notes["zone_modes"].items()):
        lines.append(f"| {zid} | {zm['mode']} | {zm['evidence']} |")
    if notes["tanks"]:
        lines += ["", "## Tanks read from the sheet", "",
                  "| label | kind | nearest zone |", "|---|---|---|"]
        for t in notes["tanks"]:
            lines.append(
                f"| {t['label']} | {t['kind']} | {t['nearest_zone'] or '—'} |"
            )
    if notes["plumbing_drains"]:
        lines += ["", "## Plumbing drains", ""]
        lines += [f"- {d}" for d in notes["plumbing_drains"]]
    lines += ["", "Evidence grades: `sheet_read` = marker drawn/labeled on the "
              "sheet; `era_rule` = era/zone-type prior; zones with neither are "
              "engineer handwork."]
    mpath = os.path.join(output_dir, "systems_notes.md")
    with validated_open(mpath, "w", allowed_roots=allowed_roots, encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
