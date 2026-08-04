"""Naval zone ontology and ACH defaults for digest prompts / synthesis."""

from __future__ import annotations

# Simulation-scale zones only — ignore hatches, fittings, hand markup.
NAVAL_ZONE_ONTOLOGY: dict[str, dict[str, str | float]] = {
    "Bridge": {"type": "Free", "traffic": "low", "ach": 6.0, "role": "navigation"},
    "CIC": {"type": "Free", "traffic": "low", "ach": 8.0, "role": "combat_info"},
    "Officers_Quarters": {"type": "Room", "traffic": "low", "ach": 6.0, "role": "berthing"},
    "CPO_Quarters": {"type": "Room", "traffic": "low", "ach": 6.0, "role": "berthing"},
    "Enlisted_Berthing": {"type": "Room", "traffic": "high", "ach": 8.0, "role": "berthing"},
    "Enlisted_Berthing_Fwd": {"type": "Room", "traffic": "high", "ach": 8.0, "role": "berthing"},
    "Enlisted_Berthing_Aft": {"type": "Room", "traffic": "high", "ach": 8.0, "role": "berthing"},
    "Mess_Hall": {"type": "Dining", "traffic": "high", "ach": 8.0, "role": "dining"},
    "Galley": {"type": "Dining", "traffic": "medium", "ach": 10.0, "role": "galley"},
    "MedBay": {"type": "Medical", "traffic": "low", "ach": 8.0, "role": "medical"},
    "Sickbay": {"type": "Medical", "traffic": "low", "ach": 8.0, "role": "medical"},
    "Engine_Room": {"type": "Engineering", "traffic": "medium", "ach": 10.0, "role": "engineering"},
    "Machinery_Space": {"type": "Engineering", "traffic": "medium", "ach": 10.0, "role": "engineering"},
    "Hangar": {"type": "Free", "traffic": "medium", "ach": 6.0, "role": "aviation"},
    "Well_Deck": {"type": "Free", "traffic": "medium", "ach": 6.0, "role": "amphibious"},
    "Flight_Deck": {"type": "Free", "traffic": "high", "ach": 4.0, "role": "aviation"},
    "Passageway": {"type": "Free", "traffic": "high", "ach": 6.0, "role": "circulation"},
}

DIGEST_SYSTEM_PROMPT = """\
You are extracting a COARSE naval ship zone model for an epidemic simulation.
The drawings are general arrangements (GAs): dense, often scanned, sometimes
hand-marked. Ignore hatch-level detail, furniture, piping symbols, and hand
markup noise.

Propose ONLY simulation-scale compartments (~10–30 zones total), such as:
Bridge, CIC, berthing banks, mess, galley, medical, engineering, hangar,
well deck, flight deck. Prefer Room-type berthing (well-mixed), never
Cabin_Corridor.

Return STRICT JSON matching the ShipDigest schema. polygon_norm vertices
are normalized [0,1]x[0,1] in page image coordinates (origin top-left).
Zone ids: snake/Pascal with underscores, no spaces. Contam-friendly ids
ideally ≤15 characters when practical.
"""


def ach_for_zone_type(zone_type: str) -> float:
    defaults = {
        "Free": 6.0,
        "Dining": 8.0,
        "Room": 7.0,
        "Medical": 8.0,
        "Engineering": 10.0,
    }
    return float(defaults.get(zone_type, 6.0))


def ontology_prompt_block() -> str:
    lines = ["Known naval zone vocabulary (id → type / traffic / typical ACH):"]
    for zid, meta in NAVAL_ZONE_ONTOLOGY.items():
        lines.append(
            f"- {zid}: type={meta['type']}, traffic={meta['traffic']}, "
            f"ach={meta['ach']}, role={meta['role']}"
        )
    return "\n".join(lines)
