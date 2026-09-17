"""
contamw34_prj.py – ContamW 3.4 parse / simplify / fiction bootstrap
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Primary (PRJ → Crusher):**
  - ``path_map_from_prj`` — ContamX path index alignment from an authentic PRJ
  - ``simplify_contamw34`` — Path B: dumb a full PRJ down to platform JSON

**Fiction bootstrap only (JSON → PRJ):** ``export_contamw34`` synthesizes
plausible ContamW 3.4 text for ships without an authentic Contam model.
With ``hobbyist=True`` it also emits typed orifices, wind, filters, schedules,
duct leakage spines, light controls, annotations, SketchPad coords, and
Air+Virus species from ``data/contam_hobbyist/`` (+ platform overrides).

ContamW name fields are capped at **15 characters** (ContamX buffer).
Crusher consumes ContamX flows via ``engines/contamx_ahs_bridge.py``.
Blueprint→authentic Contam authoring is out of scope.
"""

from __future__ import annotations

import itertools
import math
import re
import warnings
from typing import Any

from engines.py_contam_bridge import derive_volume_m3
from tools import contam_hobbyist as _hobby

PRJ_SIGNATURE_34 = "ContamW 3.4.0.0 0"
_SENTINEL = "-999"
_DEFAULT_CEILING_HEIGHT_M = 3.0
_DEFAULT_ZONE_TEMP_K = 293.15
_DEFAULT_AIR_DENSITY = 1.2041
_ZERO_CONC = "0.000e+00"
# ContamW / ContamX symbolic names (zones, AHS, levels, elements) ≤ 15 chars.
_CONTAM_NAME_MAX = 15
# Outdoor-air fraction fo for simple AHS (Contam week-schedule on recirc path).
_DEFAULT_OA_FRACTION = 0.2
_OA_SCHEDULE_NR = 1  # week-schedule index for skeleton OAFracW

# Element type codes (CONTAM 3.4)
_ELEM_ORIFICE = 23
_ELEM_FAN_CVF = 28

# Zone flags
_ZONE_NORMAL = 3
_ZONE_AHS = 10

# Simple-AHS path flags (CONTAM path flag bits)
_PATH_AHS_TERMINAL = 8   # zone supply or return
_PATH_AHS_RECIRC = 16
_PATH_AHS_OA = 32
_PATH_AHS_EXHAUST = 64

# Minimal orifice coefficients (plausible small opening / doorway)
_ORIFICE_PARAMS = "2.70811e-05 0.00848528 0.5 0.01 0.112838 0.6 30 0 0"
# Smaller envelope leak to ambient — pressure reference for ContamX Jacobian
# (constant-flow fans / AHS Fahs alone yield FATAL Zero on the diagonal).
_ENVELOPE_ORIFICE_PARAMS = (
    "2.70811e-07 8.48528e-05 0.5 0.0001 0.0112838 0.6 30 0 0"
)


def _sanitize_name(name: str) -> str:
    return re.sub(r"\s+", "_", str(name).strip()) or "unnamed"


_WORD_ABBREVS = {
    "Corridor": "Cor",
    "Restaurant": "Rest",
    "Engineering": "Eng",
    "Accommodation": "Accom",
    "Entertainment": "Ent",
    "Cartography": "Carto",
    "Treatment": "Treat",
    "Quarters": "Qtrs",
    "Control": "Ctrl",
    "Complex": "Cx",
    "Block": "Blk",
}


def _abbreviate_for_contam(name: str, max_len: int = _CONTAM_NAME_MAX) -> str:
    """Prefer word abbreviations before hard truncation (Contam ≤15 chars)."""
    name = _sanitize_name(name)
    if len(name) <= max_len:
        return name
    for long, short in _WORD_ABBREVS.items():
        if len(name) <= max_len:
            break
        name = name.replace(long, short)
    if len(name) > max_len:
        name = "".join(name.split("_"))
    return name[:max_len] or "z"


def _unique_contam_name(
    raw: str,
    used: set[str],
    *,
    max_len: int = _CONTAM_NAME_MAX,
) -> str:
    """Return a Contam-safe unique name ≤ *max_len* characters."""
    base = _abbreviate_for_contam(raw, max_len=max_len) or "z"
    candidate = base
    n = 0
    while candidate in used:
        n += 1
        suffix = f"_{n}"
        keep = max_len - len(suffix)
        if keep < 1:
            suffix = str(n)[-max_len:]
            candidate = suffix
        else:
            candidate = base[:keep] + suffix
    used.add(candidate)
    return candidate


def _orifice_area_m2_for_flow_m3h(
    flow_m3h: float,
    *,
    cd: float = 0.6,
    density: float = _DEFAULT_AIR_DENSITY,
    dp_pa: float = 1.0,
) -> float:
    """Orifice area for design volumetric flow at a reference ΔP (Contam plr_orfc)."""
    q_m3s = max(float(flow_m3h), 0.0) / 3600.0
    if q_m3s <= 0.0 or cd <= 0.0 or density <= 0.0 or dp_pa <= 0.0:
        return 1e-6
    return q_m3s / (cd * math.sqrt(2.0 * dp_pa / density))


def _flow_m3h_to_fahs_kg_s(flow_m3h: float) -> float:
    """Contam ``Fahs`` stores AHS design flow as mass flow [kg/s]."""
    return max(float(flow_m3h), 0.0) / 3600.0 * _DEFAULT_AIR_DENSITY


def _fill_zone_geometry(
    zone: dict[str, Any],
    deck_index: dict[str, int],
) -> dict[str, float]:
    """Derive Contam-friendly geometry; does not mutate the source zone."""
    volume = float(
        derive_volume_m3(
            zone.get("volume_m3"),
            zone.get("floor_area_m2"),
            zone.get("ceiling_height_m"),
        )
    )
    ceiling = zone.get("ceiling_height_m")
    if ceiling is None:
        ceiling = _DEFAULT_CEILING_HEIGHT_M
    else:
        ceiling = float(ceiling)
    area = zone.get("floor_area_m2")
    if area is None:
        area = volume / ceiling if ceiling > 0 else volume / _DEFAULT_CEILING_HEIGHT_M
    else:
        area = float(area)
    elev = zone.get("elevation_m")
    if elev is None:
        deck = str(zone.get("deck", "main"))
        elev = float(deck_index.get(deck, 0)) * _DEFAULT_CEILING_HEIGHT_M
    else:
        elev = float(elev)
    return {
        "volume_m3": volume,
        "floor_area_m2": area,
        "ceiling_height_m": ceiling,
        "elevation_m": elev,
    }


def _build_levels(zones: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order: list[str] = []
    members: dict[str, list[dict[str, Any]]] = {}
    for zone in zones:
        deck = str(zone.get("deck", "main"))
        if deck not in members:
            members[deck] = []
            order.append(deck)
        members[deck].append(zone)

    levels: list[dict[str, Any]] = []
    for i, deck in enumerate(order):
        heights = [
            float(z["ceiling_height_m"])
            for z in members[deck]
            if z.get("ceiling_height_m") is not None
        ]
        delht = max(heights) if heights else _DEFAULT_CEILING_HEIGHT_M
        elevations = [
            float(z["elevation_m"])
            for z in members[deck]
            if z.get("elevation_m") is not None
        ]
        refht = (
            min(elevations)
            if elevations
            else float(i) * _DEFAULT_CEILING_HEIGHT_M
        )
        levels.append({"name": deck, "refht": refht, "delht": delht})
    return levels


def build_path_map(
    spatial_layout: dict[str, Any],
    air_flow_paths: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build the Crusher path manifest matching ContamW 3.4 export order.

    Path numbering is 1-based and matches ContamX ``.sim`` path indices.
    Only entries with both endpoints as real zone ids are used by
    ``ContamXTransportEngine``; ambient / phantom paths are still listed
    for solvability bookkeeping (``crusher_transfer`` false).
    """
    return _assemble_network(spatial_layout, air_flow_paths)["path_map"]


def _phantom_zone_record(nr: int, name: str) -> dict[str, Any]:
    """Zero-volume AHS phantom zone (``ahsN(Ret)`` / ``ahsN(Sup)``)."""
    return {
        "nr": nr,
        "flag": _ZONE_AHS,
        "level": 1,
        "rel_ht": 0.0,
        "volume": 0.0,
        "area": 0.0,
        "height": _DEFAULT_CEILING_HEIGHT_M,
        "elevation": 0.0,
        "temp": _DEFAULT_ZONE_TEMP_K,
        "name": name,
        "orig_id": name,
        "type": "Free",
        "traffic": "low",
        "deck": "main",
        "x": 0.0,
        "y": 0.0,
        "is_phantom": True,
    }


def _hobbyist_control_nodes() -> list[dict[str, Any]]:
    """Light controls (portfolio spice — not wired into AHS paths)."""
    return [
        {
            "nr": 1,
            "typ": "set",
            "seq": 1,
            "f": 0,
            "n": 0,
            "c1": 0,
            "c2": 0,
            "name": "OAConst",
            "desc": "Constant OA fraction report node",
            "params": "0.2",
        },
        {
            "nr": 2,
            "typ": "pas",
            "seq": 2,
            "f": 0,
            "n": 1,
            "c1": 1,
            "c2": 0,
            "name": "OAPass",
            "desc": "Passthrough of OA constant",
            "params": "",
        },
        {
            "nr": 3,
            "typ": "set",
            "seq": 3,
            "f": 0,
            "n": 0,
            "c1": 0,
            "c2": 0,
            "name": "DutyConst",
            "desc": "Constant AHU duty report node",
            "params": "1.0",
        },
    ]


class _NetworkBuilder:
    """Scratch state for ``_assemble_network``; one method per PRJ section."""

    def __init__(
        self,
        spatial_layout: dict[str, Any],
        air_flow_paths: dict[str, Any],
        *,
        hobbyist: bool,
        overrides: dict[str, Any] | None,
        pack: dict[str, Any] | None,
        filter_efficiency: float | None,
    ) -> None:
        self.spatial_layout = spatial_layout
        self.zones = list(spatial_layout.get("zones", []))
        self.hvac_zones = list(air_flow_paths.get("hvac_zones", []))
        self.cross_links = list(air_flow_paths.get("cross_zone_links", []))
        self.adjacency = list(air_flow_paths.get("adjacency", []))
        self.overrides = dict(overrides or {})
        self.pack = pack or (_hobby.load_hobbyist_pack() if hobbyist else {})
        self.hobbyist = hobbyist
        self.filter_efficiency = filter_efficiency

        self.levels = _build_levels(self.zones)
        self.level_index = {lvl["name"]: i + 1 for i, lvl in enumerate(self.levels)}
        self.deck_order = {lvl["name"]: i for i, lvl in enumerate(self.levels)}
        deck_dims = spatial_layout.get("deck_dimensions") or {}
        self.beam_m = float(deck_dims.get("beam_m", 15.0) or 15.0)

        self.used_contam_names: set[str] = set()
        self.zone_name_to_nr: dict[str, int] = {}
        self.zone_by_id: dict[str, dict[str, Any]] = {z["id"]: z for z in self.zones}
        self.zone_records: list[dict[str, Any]] = []
        self.hvac_info: list[dict[str, Any]] = []

        self.elements: list[dict[str, Any]] = []
        self.orifice_elem_by_key: dict[str, int] = {"envelope": 2}
        self.fan_elem_by_m3s: dict[float, int] = {}
        self.orifice_elem_by_area: dict[float, int] = {}

        # Hobbyist schedules / wind / filters (indices are 1-based Contam refs)
        self.sched_oa_week = 0
        self.sched_duty_week = 0
        self.wind_nr = 0
        self.filter_nr_by_preset: dict[str, int] = {}
        self.filter_elements: list[dict[str, Any]] = []
        self.filters: list[dict[str, Any]] = []
        self.day_schedules: list[dict[str, Any]] = []
        self.week_schedules: list[dict[str, Any]] = []
        self.wind_profiles: list[dict[str, Any]] = []
        self.control_nodes: list[dict[str, Any]] = []
        self.annotations: list[dict[str, Any]] = []
        self.duct_elements: list[dict[str, Any]] = []
        self.duct_junctions: list[dict[str, Any]] = []
        self.duct_segments: list[dict[str, Any]] = []
        self.species: list[dict[str, Any]] = []
        self.contaminant_indices: list[int] = [1]
        self.day_by_id: dict[str, int] = {}
        self.week_by_id: dict[str, int] = {}

        self.paths: list[dict[str, Any]] = []
        self.path_map: list[dict[str, Any]] = []
        self.ahs_records: list[dict[str, Any]] = []
        self.default_oa = _DEFAULT_OA_FRACTION
        self.oa_week_by_frac: dict[float, int] = {}

    # ── driver ────────────────────────────────────────────────────────────

    def build(self) -> dict[str, Any]:
        self._build_zone_records()
        self._build_ahs_phantoms()
        self._build_flow_elements()
        if self.hobbyist:
            self._build_hobbyist_schedules()
            self._build_hobbyist_extras()
        # 1) Envelope leakage to ambient (pressure-dependent reference).
        self._add_envelope_paths()
        # 2) Adjacency openings (typed orifices when hobbyist)
        self._add_adjacency_paths()
        # 3) Cross-zone links: fan_cvf when HVAC-ducted; sized plr_orfc when passive.
        self._add_cross_zone_paths()
        # 4) Per-AHS: Contam simple-AHS semantics (match authentic ContamW 3.4)
        self._add_ahs_paths()
        # 5) Duct leakage spines (hobbyist): passive Darcy trunks between rooms
        if self.hobbyist and not self.overrides.get("skip_duct_spines"):
            self._build_duct_spines()
        return self._result()

    def _result(self) -> dict[str, Any]:
        return {
            "levels": self.levels,
            "zone_records": self.zone_records,
            "elements": self.elements,
            "paths": self.paths,
            "path_map": self.path_map,
            "ahs_records": self.ahs_records,
            "hvac_info": self.hvac_info,
            "platform": self.spatial_layout.get("platform", "crusher_platform"),
            "zone_name_to_nr": self.zone_name_to_nr,
            "used_contam_names": self.used_contam_names,
            "hobbyist": self.hobbyist,
            "day_schedules": self.day_schedules,
            "week_schedules": self.week_schedules,
            "wind_profiles": self.wind_profiles,
            "filter_elements": self.filter_elements,
            "filters": self.filters,
            "control_nodes": self.control_nodes,
            "annotations": self.annotations,
            "duct_elements": self.duct_elements,
            "duct_junctions": self.duct_junctions,
            "duct_segments": self.duct_segments,
            "species": self.species,
            "contaminant_indices": self.contaminant_indices,
            "day_by_id": self.day_by_id if self.hobbyist else {},
        }

    # ── zones ─────────────────────────────────────────────────────────────

    def _build_zone_records(self) -> None:
        for i, zone in enumerate(self.zones, start=1):
            name = _unique_contam_name(zone["id"], self.used_contam_names)
            geo = _fill_zone_geometry(zone, self.deck_order)
            deck = str(zone.get("deck", "main"))
            display = zone.get("display", {}) or {}
            temp = (
                _hobby.deck_temp_k(deck, self.overrides, _DEFAULT_ZONE_TEMP_K)
                if self.hobbyist
                else _DEFAULT_ZONE_TEMP_K
            )
            self.zone_name_to_nr[zone["id"]] = i
            self.zone_name_to_nr[name] = i
            self.zone_records.append({
                "nr": i,
                "flag": _ZONE_NORMAL,
                "level": self.level_index.get(deck, 1),
                "rel_ht": 0.0,
                "volume": geo["volume_m3"],
                "area": geo["floor_area_m2"],
                "height": geo["ceiling_height_m"],
                "elevation": geo["elevation_m"],
                "temp": temp,
                "name": name,
                "orig_id": zone["id"],
                "type": zone.get("type", "Free"),
                "traffic": zone.get("traffic", "medium"),
                "deck": deck,
                "x": float(display.get("x", 0) or 0),
                "y": float(display.get("y", 0) or 0),
                "is_phantom": False,
            })

    def _build_ahs_phantoms(self) -> None:
        """Map HVAC group id -> (first_room_id, room_ids, ach, ret_nr, sup_nr)."""
        next_zone = len(self.zone_records) + 1
        for hz in self.hvac_zones:
            rooms = [r for r in hz.get("rooms", []) if r in self.zone_name_to_nr]
            if not rooms:
                continue
            ahs_i = len(self.hvac_info) + 1
            ach = float(hz.get("ach", 6.0))
            # Contam-style short phantoms: ahs1(Ret) / ahs1(Sup) (≤ 15 chars)
            ret_name = _unique_contam_name(f"ahs{ahs_i}(Ret)", self.used_contam_names)
            sup_name = _unique_contam_name(f"ahs{ahs_i}(Sup)", self.used_contam_names)
            ahs_name = _unique_contam_name(f"ahs{ahs_i}", self.used_contam_names)
            ret_nr = next_zone
            self.zone_name_to_nr[ret_name] = ret_nr
            self.zone_records.append(_phantom_zone_record(ret_nr, ret_name))
            next_zone += 1
            sup_nr = next_zone
            self.zone_name_to_nr[sup_name] = sup_nr
            self.zone_records.append(_phantom_zone_record(sup_nr, sup_name))
            next_zone += 1
            self.hvac_info.append({
                "id": hz["id"],
                "rooms": rooms,
                "ach": ach,
                "ret_nr": ret_nr,
                "sup_nr": sup_nr,
                "ret_name": ret_name,
                "sup_name": sup_name,
                "ahs_name": ahs_name,
            })

    # ── flow elements ─────────────────────────────────────────────────────

    def _build_flow_elements(self) -> None:
        """1 = Opening (legacy default), 2 = EnvLeak, then typed orifices (hobbyist)."""
        self.elements = [
            {
                "nr": 1,
                "type": _ELEM_ORIFICE,
                "symbol": "plr_orfc",
                "name": "Opening",
                "params": _ORIFICE_PARAMS,
            },
            {
                "nr": 2,
                "type": _ELEM_ORIFICE,
                "symbol": "plr_orfc",
                "name": "EnvLeak",
                "params": _ENVELOPE_ORIFICE_PARAMS,
            },
        ]
        if not self.hobbyist:
            return
        env_area = float(
            self.pack["orifice_catalog"]["envelope_leak"].get("area_m2", 0.0001)
        )
        self.elements[1]["params"] = _hobby.orifice_params_for_area(env_area)
        name_to_elem: dict[str, int] = {}
        for key, spec in self.pack["orifice_catalog"]["types"].items():
            el_label = str(spec.get("name", key))[:15]
            if el_label in name_to_elem:
                self.orifice_elem_by_key[key] = name_to_elem[el_label]
                continue
            nr = len(self.elements) + 1
            area = float(spec.get("area_m2", 0.01))
            self.elements.append({
                "nr": nr,
                "type": _ELEM_ORIFICE,
                "symbol": "plr_orfc",
                "name": el_label,
                "params": _hobby.orifice_params_for_area(area),
            })
            name_to_elem[el_label] = nr
            self.orifice_elem_by_key[key] = nr

    def _fan_elem(self, flow_m3h: float) -> int:
        m3s = max(flow_m3h, 0.0) / 3600.0
        key = round(m3s, 12)
        if key in self.fan_elem_by_m3s:
            return self.fan_elem_by_m3s[key]
        nr = len(self.elements) + 1
        self.elements.append({
            "nr": nr,
            "type": _ELEM_FAN_CVF,
            "symbol": "fan_cvf",
            "name": f"Fan_{nr}",
            "params": f"{m3s:.12g} 3",
            "flow_m3h": flow_m3h,
        })
        self.fan_elem_by_m3s[key] = nr
        return nr

    def _orifice_elem_for_flow(self, flow_m3h: float) -> int:
        """Sized plr_orfc for passive cross-zone design flow at 1 Pa."""
        area = _orifice_area_m2_for_flow_m3h(flow_m3h)
        key = round(area, 10)
        if key in self.orifice_elem_by_area:
            return self.orifice_elem_by_area[key]
        nr = len(self.elements) + 1
        el_name = _unique_contam_name(f"XZOrf_{nr}", self.used_contam_names)
        self.elements.append({
            "nr": nr,
            "type": _ELEM_ORIFICE,
            "symbol": "plr_orfc",
            "name": el_name,
            "params": _hobby.orifice_params_for_area(area),
            "area_m2": area,
            "flow_m3h": flow_m3h,
        })
        self.orifice_elem_by_area[key] = nr
        return nr

    # ── hobbyist schedules / wind / species / controls / annotations ──────

    def _build_hobbyist_schedules(self) -> None:
        templates = self.pack["schedule_templates"]
        defaults = templates["defaults"]
        for i, ds in enumerate(templates["day_schedules"], 1):
            self.day_schedules.append(ds)
            self.day_by_id[ds["id"]] = i
        for i, ws in enumerate(templates["week_schedules"], 1):
            self.week_schedules.append(ws)
            self.week_by_id[ws["id"]] = i
            if ws["id"] == defaults["oa_week"]:
                self.sched_oa_week = i
            if ws["id"] == defaults["duty_week"]:
                self.sched_duty_week = i
        if self.overrides.get("night_setback", True):
            return
        # Drop night-setback week/day if disabled (keep OA + duty + openings)
        self.week_schedules = [
            w for w in self.week_schedules if w["id"] != "NightSetbackW"
        ]
        self.day_schedules = [
            d for d in self.day_schedules if d["id"] != "NightSetback"
        ]
        self.day_by_id.clear()
        self.day_by_id.update(
            {d["id"]: i for i, d in enumerate(self.day_schedules, 1)}
        )
        self.week_by_id.clear()
        self.week_by_id.update(
            {w["id"]: i for i, w in enumerate(self.week_schedules, 1)}
        )
        self.sched_oa_week = self.week_by_id.get(defaults["oa_week"], 0)
        self.sched_duty_week = self.week_by_id.get(defaults["duty_week"], 0)

    def _build_hobbyist_extras(self) -> None:
        # Wind
        wkey = _hobby.resolve_wind_profile_key(self.pack, self.overrides)
        self.wind_profiles.append(self.pack["wind_profiles"]["profiles"][wkey])
        self.wind_nr = 1

        # Species
        self.species = list(self.pack["species_pack"]["species"])
        self.contaminant_indices = list(range(1, len(self.species) + 1))

        self.control_nodes = _hobbyist_control_nodes()

        # Annotations from overrides + deck labels
        ann_map = dict(self.overrides.get("zone_annotations") or {})
        for note in ann_map.values():
            self.annotations.append({"color": -1, "note": str(note)[:60]})
        for lvl in self.levels:
            self.annotations.append({
                "color": 2,
                "note": f"Deck {lvl['name']}"[:60],
            })
        for info in self.hvac_info:
            self.annotations.append({
                "color": 2,
                "note": f"HVAC {info['id']}"[:60],
            })

    # ── flow paths ────────────────────────────────────────────────────────

    def _add_path(
        self,
        from_nr: int,
        to_nr: int,
        elem_nr: int,
        *,
        from_name: str,
        to_name: str,
        kind: str,
        is_hvac_ducted: bool,
        crusher_transfer: bool,
        ahs_nr: int = 0,
        ahs_group: int = 0,
        level: int = 1,
        flag: int = 0,
        fahs: float = 0.0,
        wazm: float = -1.0,
        filter_nr: int = 0,
        wind_p: int = 0,
        sched_nr: int = 0,
        x: float = 0.0,
        y: float = 0.0,
        w_pmod: float = 0.0,
    ) -> int:
        pnr = len(self.paths) + 1
        self.paths.append({
            "nr": pnr,
            "flag": flag,
            "from_nr": from_nr,
            "to_nr": to_nr,
            "elem_nr": elem_nr,
            "ahs_nr": ahs_nr,
            "level": level,
            "fahs": fahs,
            "wazm": wazm,
            "filter_nr": filter_nr,
            "wind_nr": wind_p,
            "sched_nr": sched_nr,
            "x": x,
            "y": y,
            "w_pmod": w_pmod,
        })
        self.path_map.append({
            "path_nr": pnr,
            "from_zone": from_name,
            "to_zone": to_name,
            "is_hvac_ducted": is_hvac_ducted,
            "kind": kind,
            "crusher_transfer": crusher_transfer,
            "ahs_nr": ahs_group or ahs_nr,
        })
        return pnr

    def _add_envelope_paths(self) -> None:
        for z in self.zone_records:
            if z["is_phantom"]:
                continue
            wazm = -1.0
            w_nr = 0
            wmod = 0.0
            if self.hobbyist and self.wind_nr:
                src = self.zone_by_id.get(z["orig_id"], {})
                wazm = _hobby.wall_azimuth_deg(
                    z["orig_id"], src, self.overrides, beam_m=self.beam_m,
                )
                w_nr = self.wind_nr
                wmod = 0.8
            self._add_path(
                z["nr"], -1, 2,
                from_name=z["orig_id"], to_name="ambient",
                kind="envelope_leak",
                is_hvac_ducted=False,
                crusher_transfer=False,
                flag=0,
                level=int(z["level"]),
                wazm=wazm,
                wind_p=w_nr,
                w_pmod=wmod,
                x=float(z["x"]),
                y=float(z["y"]),
            )

    def _adjacency_element(self, adj_type: str) -> tuple[int, int]:
        """(element nr, week-schedule nr) for an adjacency opening."""
        if not self.hobbyist:
            return 1, 0
        okey = _hobby.resolve_orifice_type(adj_type, self.pack, self.overrides)
        elem = self.orifice_elem_by_key.get(okey, 1)
        sched_id = _hobby.resolve_opening_schedule(
            adj_type, self.pack, self.overrides,
        )
        adj_sched = int(self.week_by_id.get(sched_id, 0)) if sched_id else 0
        return elem, adj_sched

    def _add_adjacency_paths(self) -> None:
        for adj in self.adjacency:
            a, b = adj["from"], adj["to"]
            if a not in self.zone_name_to_nr or b not in self.zone_name_to_nr:
                continue
            adj_type = str(adj.get("type", "passageway"))
            elem, adj_sched = self._adjacency_element(adj_type)
            za = self.zone_records[self.zone_name_to_nr[a] - 1]
            zb = self.zone_records[self.zone_name_to_nr[b] - 1]
            self._add_path(
                self.zone_name_to_nr[a], self.zone_name_to_nr[b], elem,
                from_name=a, to_name=b,
                kind=adj_type,
                is_hvac_ducted=False,
                crusher_transfer=True,
                flag=0,
                sched_nr=adj_sched,
                x=0.5 * (float(za["x"]) + float(zb["x"])),
                y=0.5 * (float(za["y"]) + float(zb["y"])),
            )

    def _endpoint_rooms(self, token: str) -> list[str]:
        hvac_by_id = {h["id"]: h for h in self.hvac_info}
        if token in hvac_by_id:
            return list(hvac_by_id[token]["rooms"])
        real_room_ids = {
            z["orig_id"] for z in self.zone_records if not z["is_phantom"]
        }
        if token in real_room_ids:
            return [token]
        if token in self.zone_name_to_nr:
            return [token]
        return []

    def _passive_cross_zone_schedule(self, path_name: str) -> int:
        """Week-schedule nr for passive shafts/hatches (0 = always open)."""
        if not self.hobbyist or not self.week_by_id:
            return 0
        low = str(path_name).lower()
        if "hatch" in low:
            sched_id = "HatchOccasionalW"
        else:
            # ladder wells, shafts, stairwells, corridors
            sched_id = "ShaftOpenW"
        return int(self.week_by_id.get(sched_id, 0))

    def _add_cross_zone_paths(self) -> None:
        """Expansion to room×room pairs matches native ContamTransportEngine."""
        for link in self.cross_links:
            from_rooms = self._endpoint_rooms(link["from"])
            to_rooms = self._endpoint_rooms(link["to"])
            if not from_rooms or not to_rooms:
                continue
            flow = float(link.get("flow_rate_m3h", 50.0))
            n_pairs = len(from_rooms) * len(to_rooms)
            pair_flow = flow / n_pairs if n_pairs > 0 else 0.0
            if pair_flow <= 0.0:
                continue
            kind = link.get("path", "cross_zone")
            ducted = bool(link.get("is_hvac_ducted", False))
            if ducted:
                elem = self._fan_elem(pair_flow)
                sched_nr = 0
            else:
                elem = self._orifice_elem_for_flow(pair_flow)
                sched_nr = self._passive_cross_zone_schedule(str(kind))
            for fr, tr in itertools.product(from_rooms, to_rooms):
                self._add_path(
                    self.zone_name_to_nr[fr], self.zone_name_to_nr[tr], elem,
                    from_name=fr, to_name=tr,
                    kind=kind,
                    is_hvac_ducted=ducted,
                    crusher_transfer=True,
                    flag=0,
                    sched_nr=sched_nr,
                )

    # ── air-handling systems ──────────────────────────────────────────────

    def _ensure_filter(self, preset: str) -> int:
        if preset in self.filter_nr_by_preset:
            return self.filter_nr_by_preset[preset]
        presets = self.pack["filter_presets"]["presets"]
        spec = presets[preset]
        fe_nr = len(self.filter_elements) + 1
        el_name = _unique_contam_name(str(spec["name"]), self.used_contam_names)
        self.filter_elements.append({
            "nr": fe_nr,
            "name": el_name,
            "description": str(spec.get("description", "")),
            "efficiency": float(spec["efficiency"]),
            "area": float(self.pack["filter_presets"].get("face_area_m2", 1.0)),
            "depth": float(self.pack["filter_presets"].get("depth_m", 0.05)),
            "dens": float(self.pack["filter_presets"].get("density_kg_m3", 100.0)),
        })
        f_nr = len(self.filters) + 1
        self.filters.append({"nr": f_nr, "fe": fe_nr, "nsub": 1})
        self.filter_nr_by_preset[preset] = f_nr
        return f_nr

    def _oa_week_schedule_nr(self, oa_frac: float) -> int:
        """Return Contam week-schedule nr for this outdoor-air fraction.

        Default OAFracW covers fo≈0.2. Non-default per-AHU overrides get a
        dedicated day/week pair wired onto that AHS recirculation path.
        """
        if not self.hobbyist:
            return _OA_SCHEDULE_NR
        key = round(float(oa_frac), 6)
        if abs(key - round(self.default_oa, 6)) < 1e-9:
            return self.sched_oa_week or _OA_SCHEDULE_NR
        if key in self.oa_week_by_frac:
            return self.oa_week_by_frac[key]
        pct = int(round(key * 100))
        day_id = f"OAFr_{pct}"
        day_name = f"OAFr_{pct}"[:15]
        week_id = f"OAFr_{pct}W"
        week_name = f"OAFr{pct}W"[:15]
        self.day_schedules.append({
            "id": day_id,
            "name": day_name,
            "description": f"Outdoor-air fraction {key:.3f}",
            "points": [["00:00:00", key], ["24:00:00", key]],
        })
        self.day_by_id[day_id] = len(self.day_schedules)
        self.week_schedules.append({
            "id": week_id,
            "name": week_name,
            "description": f"Week schedule for OA fraction {key:.3f}",
            "day_id": day_id,
        })
        week_nr = len(self.week_schedules)
        self.week_by_id[week_id] = week_nr
        self.oa_week_by_frac[key] = week_nr
        return week_nr

    def _ahs_filter_nr(self, hvac_id: str) -> int:
        if not self.hobbyist:
            return 0
        preset = _hobby.resolve_filter_preset(
            self.pack, self.overrides,
            hvac_id=hvac_id,
            filter_efficiency=self.filter_efficiency,
        )
        return self._ensure_filter(preset)

    def _zone_record_for(self, room: str) -> dict[str, Any]:
        return next(z for z in self.zone_records if z["orig_id"] == room)

    def _add_ahs_system_paths(
        self,
        ahs_i: int,
        info: dict[str, Any],
        *,
        recirc_fahs: float,
        filt_nr: int,
        oa_sched: int,
    ) -> tuple[int, int, int]:
        """OA intake, exhaust, recirculation paths → (ps, px, pr) numbers."""
        oa_path = self._add_path(
            -1, info["sup_nr"], 0,
            from_name="ambient", to_name=info["sup_name"],
            kind="ahs_oa", is_hvac_ducted=True, crusher_transfer=False,
            ahs_nr=0, ahs_group=ahs_i, flag=_PATH_AHS_OA, fahs=0.0, wazm=-1.0,
        )
        ex_path = self._add_path(
            info["ret_nr"], -1, 0,
            from_name=info["ret_name"], to_name="ambient",
            kind="ahs_exhaust", is_hvac_ducted=True, crusher_transfer=False,
            ahs_nr=0, ahs_group=ahs_i, flag=_PATH_AHS_EXHAUST, fahs=0.0, wazm=-1.0,
        )
        recirc_path = self._add_path(
            info["ret_nr"], info["sup_nr"], 0,
            from_name=info["ret_name"], to_name=info["sup_name"],
            kind="ahs_recirc", is_hvac_ducted=True, crusher_transfer=False,
            ahs_nr=0, ahs_group=ahs_i, flag=_PATH_AHS_RECIRC, fahs=recirc_fahs, wazm=-1.0,
            filter_nr=filt_nr,
            sched_nr=oa_sched if self.hobbyist else _OA_SCHEDULE_NR,
        )
        return oa_path, ex_path, recirc_path

    def _add_ahs_terminal_paths(
        self,
        ahs_i: int,
        info: dict[str, Any],
        *,
        per_room_fahs: float,
    ) -> None:
        duty_sched = self.sched_duty_week if self.hobbyist else 0
        for room in info["rooms"]:
            rnr = self.zone_name_to_nr[room]
            zrec = self._zone_record_for(room)
            self._add_path(
                info["sup_nr"], rnr, 0,
                from_name=info["sup_name"], to_name=room,
                kind="ahs_supply", is_hvac_ducted=True, crusher_transfer=False,
                ahs_nr=ahs_i, ahs_group=ahs_i, flag=_PATH_AHS_TERMINAL,
                fahs=per_room_fahs, wazm=0.0,
                sched_nr=duty_sched,
                x=float(zrec["x"]), y=float(zrec["y"]),
            )
            self._add_path(
                rnr, info["ret_nr"], 0,
                from_name=room, to_name=info["ret_name"],
                kind="ahs_return", is_hvac_ducted=True, crusher_transfer=False,
                ahs_nr=ahs_i, ahs_group=ahs_i, flag=_PATH_AHS_TERMINAL,
                fahs=per_room_fahs, wazm=0.0,
                sched_nr=duty_sched,
                x=float(zrec["x"]), y=float(zrec["y"]),
            )

    def _add_ahs_paths(self) -> None:
        if self.hobbyist:
            self.default_oa = float(
                self.pack.get("schedule_templates", {})
                .get("defaults", {})
                .get("oa_fraction", _DEFAULT_OA_FRACTION)
            )
        for ahs_i, info in enumerate(self.hvac_info, start=1):
            rooms = info["rooms"]
            ach = info["ach"]
            total_vol = sum(self._zone_record_for(r)["volume"] for r in rooms)
            total_flow = ach * total_vol  # m³/h
            oa_frac = (
                _hobby.oa_fraction_for_hvac(info["id"], self.overrides, self.default_oa)
                if self.hobbyist else 0.2
            )
            oa_flow = oa_frac * total_flow
            recirc_flow = (1.0 - oa_frac) * total_flow
            per_room_supply = total_flow / max(len(rooms), 1)
            per_room_fahs = _flow_m3h_to_fahs_kg_s(per_room_supply)
            recirc_fahs = _flow_m3h_to_fahs_kg_s(recirc_flow)
            oa_sched = self._oa_week_schedule_nr(oa_frac)
            filt_nr = self._ahs_filter_nr(info["id"])

            oa_path, ex_path, recirc_path = self._add_ahs_system_paths(
                ahs_i, info,
                recirc_fahs=recirc_fahs, filt_nr=filt_nr, oa_sched=oa_sched,
            )
            self._add_ahs_terminal_paths(ahs_i, info, per_room_fahs=per_room_fahs)

            self.ahs_records.append({
                "nr": ahs_i,
                "ret_nr": info["ret_nr"],
                "sup_nr": info["sup_nr"],
                "pr": recirc_path,
                "ps": oa_path,
                "px": ex_path,
                "name": info["ahs_name"],
                "hvac_id": info["id"],
                "rooms": rooms,
                "ach": ach,
                "total_vol": total_vol,
                "oa_flow_m3h": oa_flow,
                "filter_nr": filt_nr,
            })

    # ── duct leakage spines ───────────────────────────────────────────────

    def _build_duct_spines(self) -> None:
        """Naval GA Target B sets skip_duct_spines / empty duct_hvac_ids so
        engineers author real ducts in ContamW (ducts are not on general
        arrangements)."""
        duct_cfg = self.pack["duct_defaults"]
        min_rooms = int(duct_cfg.get("min_rooms_for_trunk", 2))
        allow = self.overrides.get("duct_hvac_ids")
        allow_set = set(allow) if isinstance(allow, list) else None
        hdia = float(duct_cfg.get("hdia_m", 0.3))
        seg_len = float(duct_cfg.get("segment_length_m", 5.0))
        ct = float(duct_cfg.get("terminal_loss_Ct", 0.5))
        area = math.pi * (hdia / 2.0) ** 2

        self.duct_elements.append({
            "nr": 1,
            "icon": 21,
            "dtype": 23,
            "symbol": "dct_dwc",
            "name": str(duct_cfg.get("element_name", "TrunkDWC"))[:15],
            "desc": "Hobbyist Darcy-Colebrook trunk",
            "rough": float(duct_cfg.get("roughness_m", 0.00015)),
            "lam": float(duct_cfg.get("laminar_loss_per_m", 0.001)),
            "hdia": hdia,
            "perim": math.pi * hdia,
            "area": area,
            "qr": float(duct_cfg.get("leakage_Ls_per_m2", 1.0)),
            "pr": float(duct_cfg.get("leakage_Pr_Pa", 250.0)),
        })

        for info in self.hvac_info:
            rooms = info["rooms"]
            if len(rooms) < min_rooms:
                continue
            if allow_set is not None and info["id"] not in allow_set:
                continue
            j_nrs = [self._add_duct_junction(room, area, ct) for room in rooms]
            for a_j, b_j in zip(j_nrs, j_nrs[1:]):
                self.duct_segments.append({
                    "nr": len(self.duct_segments) + 1,
                    "flags": 0,
                    "pjn": a_j,
                    "pjm": b_j,
                    "pe": 1,
                    "length": seg_len,
                })

    def _add_duct_junction(self, room: str, area: float, ct: float) -> int:
        z = self._zone_record_for(room)
        jnr = len(self.duct_junctions) + 1
        self.duct_junctions.append({
            "nr": jnr,
            "flags": 0,
            "jtype": 1,  # terminal
            "pzn": z["nr"],
            "level": int(z["level"]),
            "x": float(z["x"]),
            "y": float(z["y"]),
            "rel_ht": 0.0,
            "temp": float(z["temp"]),
            "Ad": area,
            "Af": area,
            "Ct": ct,
        })
        return jnr


def _assemble_network(
    spatial_layout: dict[str, Any],
    air_flow_paths: dict[str, Any],
    *,
    hobbyist: bool = False,
    overrides: dict[str, Any] | None = None,
    pack: dict[str, Any] | None = None,
    filter_efficiency: float | None = None,
) -> dict[str, Any]:
    """Shared builder for ContamW 3.4 zones, elements, paths, and AHS."""
    return _NetworkBuilder(
        spatial_layout,
        air_flow_paths,
        hobbyist=hobbyist,
        overrides=overrides,
        pack=pack,
        filter_efficiency=filter_efficiency,
    ).build()


def export_contamw34(
    spatial_layout: dict[str, Any],
    air_flow_paths: dict[str, Any],
    *,
    hobbyist: bool = False,
    overrides: dict[str, Any] | None = None,
    pack_dir: str | None = None,
    filter_efficiency: float | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Serialize platform JSON to ContamW 3.4 ``.prj`` text + path_map."""
    pack = _hobby.load_hobbyist_pack(pack_dir) if hobbyist else None
    net = _assemble_network(
        spatial_layout,
        air_flow_paths,
        hobbyist=hobbyist,
        overrides=overrides,
        pack=pack,
        filter_efficiency=filter_efficiency,
    )
    return _render_prj_text(net, hobbyist=hobbyist), net["path_map"]


def _render_prj_text(
    net: dict[str, Any],
    *,
    hobbyist: bool = False,
) -> str:
    """Render an assembled network dict as ContamW 3.4 project text."""
    platform = _sanitize_name(net["platform"])[:_CONTAM_NAME_MAX]
    used_names: set[str] = set(net.get("used_contam_names") or [])
    lines: list[str] = []
    ctx = {
        "net": net,
        "hobbyist": hobbyist,
        "platform": platform,
        "used_names": used_names,
        "levels": net["levels"],
        "zone_records": net["zone_records"],
        "elements": net["elements"],
        "paths": net["paths"],
        "ahs_records": net["ahs_records"],
        "path_map": net["path_map"],
    }
    _append_prj_header(lines, ctx)
    _append_species_section(lines, ctx)
    _append_levels_section(lines, ctx)
    _append_schedule_sections(lines, ctx)
    _append_wind_filter_sections(lines, ctx)
    _append_flow_and_duct_elements(lines, ctx)
    _append_ahs_zones_and_paths(lines, ctx)
    _append_duct_network_and_footer(lines, ctx)
    return "\n".join(lines) + "\n"


def _append_prj_header(lines: list[str], ctx: dict[str, Any]) -> None:
    hobbyist = ctx["hobbyist"]
    platform = ctx["platform"]
    zone_records = ctx["zone_records"]
    n_zones = len(zone_records)
    rows = max(40, n_zones + 20)
    cols = max(40, n_zones + 20)
    ctx["rows"] = rows
    ctx["cols"] = cols
    lines.append(PRJ_SIGNATURE_34)
    lines.append("")
    lines.append("! rows cols ud uf    T   uT     N     wH  u  Ao    a")
    lines.append(
        f"   {rows:3d}  {cols:3d}  0  0 {_DEFAULT_ZONE_TEMP_K:.3f} 2    "
        f"0.00 10.00 0 0.600 0.280"
    )
    lines.append("!  scale     us  orgRow  orgCol  invYaxis showGeom")
    lines.append("  1.000e+00   0       1       1     0        0")
    lines.append("! Ta       Pb      Ws    Wd    rh  day u..")
    lines.append(
        f"{_DEFAULT_ZONE_TEMP_K:.3f} 101325.0  0.000   0.0 0.000 1 2 0 0 1 "
        f"! steady simulation"
    )
    lines.append(
        f"{_DEFAULT_ZONE_TEMP_K:.3f} 101325.0  1.000 270.0 0.000 1 2 0 0 1 "
        f"! wind pressure test"
    )
    lines.append("null ! no weather file")
    lines.append("null ! no contaminant file")
    lines.append("null ! no continuous values file")
    lines.append("null ! no discrete values file")
    lines.append("null ! no WPC file")
    lines.append("null ! no EWC file")
    mode = "hobbyist" if hobbyist else "skeleton"
    lines.append(f"Crusher platform {platform} ({mode})")
    lines.append("!  Xref    Yref    Zref   angle u")
    lines.append("   0.000   0.000   0.000   0.00 0")
    lines.append("! epsP epsS  tShift  dStart dEnd wp mf wpctrig")
    lines.append("  0.01 0.01 00:00:00   1/1   1/1  0  0  0")
    lines.append("! latd  longtd   tznr  altd  Tgrnd u..")
    lines.append(" 40.00  -90.00  -6.00     0 283.15 2 0")
    lines.append("!sim_af afcalc afmaxi afrcnvg afacnvg afrelax uac Pbldg uPb")
    lines.append("     1      1     30   1e-05   1e-06    0.75   0 50.00   0")
    lines.append("!   slae rs aflmaxi aflcnvg aflinit Tadj")
    lines.append("      0   1    100   1e-06      1    0")
    lines.append("!sim_mf slae rs maxi   relcnvg   abscnvg relax gamma ucc")
    lines.append(
        "    2             30  1.00e-04  1.00e-15 1.250         0 ! (cyclic)"
    )
    lines.append(
        "          0   1  100  1.00e-06  1.00e-15 1.100 1.000   0 ! (non-trace)"
    )
    lines.append(
        "          0   1  100  1.00e-06  1.00e-15 1.100 1.000   0 ! (trace)"
    )
    lines.append(
        "          0   1  100  1.00e-06  1.00e-15 1.100         0 ! (cvode)"
    )
    lines.append("!mf_solver sim_1dz sim_1dd   celldx  sim_vjt udx")
    lines.append("     0        1       0     1.00e-01    0     0")
    lines.append("!cvode    rcnvg     acnvg    dtmax")
    lines.append("   0     1.00e-06  1.00e-13   0.00")
    lines.append("!tsdens relax tsmaxi cnvgSS densZP stackD dodMdt")
    # Enable stack effect when hobbyist deck temps differ
    stack = 1 if hobbyist else 0
    lines.append(f"   0    0.75    20     1      0      {stack}      0")
    lines.append("!date_st time_st  date_0 time_0   date_1 time_1    t_step   t_list   t_scrn")
    lines.append(
        "  Jan01 00:00:00  Jan01 00:00:00  Jan01 01:00:00  00:01:00 00:01:00 01:00:00"
    )
    lines.append("!restart  date  time")
    lines.append("    0    Jan01 00:00:00")
    lines.append("!list doDlg pfsave zfsave zcsave")
    lines.append("   1     0      1      1      1")
    lines.append("!vol ach -bw cbw exp -bw age -bw")
    lines.append("  0   0   0   0   0   0   0   0")
    lines.append("!rzf rzm rz1 csm srf log")
    lines.append("  0   0   0   1   1   1")
    lines.append("!bcx dcx pfq zfq zcq")
    lines.append("  0   0   0   0   0")
    lines.append("!dens   grav")
    lines.append(f" {_DEFAULT_AIR_DENSITY} 9.8055")
    lines.append("! 0  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 <- extra[]")
    lines.append("  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0")
    lines.append("0 ! rvals:")
    lines.append("!valZ valD valC")
    lines.append("   0    0    0")
    lines.append("!cfd   cfdcnvg  var zref maxi dtcmo solv smooth   cnvgUVW     cnvgT")
    lines.append("   0  1.00e-02    0    0 1000     1    1      1  1.00e-03  1.00e-03")
    lines.append(_SENTINEL)



def _append_species_section(lines: list[str], ctx: dict[str, Any]) -> None:
    net = ctx["net"]
    # Contaminants / species
    species = net.get("species") or []
    cidxs = net.get("contaminant_indices") or [1]
    if not species:
        species = [{
            "name": "Air", "sflag": 1, "ntflag": 0, "molwt": 28.96,
            "mdiam": 0.0, "edens": 0.0, "decay": 0.0, "Dm": 2.0e-5,
            "CCdef": 0.0, "Cp": 1000.0, "Kuv": 0.0, "description": "default",
        }]
        cidxs = [1]
    lines.append(f"{len(cidxs)} ! contaminants:")
    lines.append("   " + " ".join(str(i) for i in cidxs))
    lines.append(f"{len(species)} ! species:")
    lines.append(
        "! # s t   molwt    mdiam       edens       decay         Dm         "
        "CCdef        Cp          Kuv     u[5]      name"
    )
    for i, sp in enumerate(species, start=1):
        lines.append(
            f"  {i} {int(sp['sflag'])} {int(sp['ntflag'])}  "
            f"{float(sp['molwt']):.4f}  {float(sp['mdiam']):.4e}  "
            f"{float(sp['edens']):.4e}  {float(sp['decay']):.4e}  "
            f"{float(sp['Dm']):.4e}  {float(sp['CCdef']):.4e}  "
            f"{float(sp['Cp']):.4e}  {float(sp['Kuv']):.4e} "
            f"0 0 0 0 0 {sp['name']}"
        )
        lines.append(str(sp.get("description", "")))
    lines.append(_SENTINEL)
    ctx["species"] = species
    ctx["cidxs"] = cidxs
    n_ctm = len(cidxs)
    ctx["zeros"] = "  ".join(_ZERO_CONC for _ in range(n_ctm))


def _append_levels_section(lines: list[str], ctx: dict[str, Any]) -> None:
    hobbyist = ctx["hobbyist"]
    used_names = ctx["used_names"]
    levels = ctx["levels"]
    zone_records = ctx["zone_records"]
    rows = ctx.get("rows", 40)
    cols = ctx.get("cols", 40)
    # Levels (+ optional zone icons for SketchPad)
    real_zones = [z for z in zone_records if not z["is_phantom"]]
    icons_by_level: dict[int, list[tuple[int, int, int, int]]] = {
        i + 1: [] for i in range(len(levels))
    }
    if hobbyist:
        for z in real_zones:
            # icon 1 = zone; col/row from display coords
            col = max(1, min(cols - 1, int(float(z["x"])) + 1))
            row = max(1, min(rows - 1, int(float(z["y"])) + 1))
            icons_by_level[int(z["level"])].append((1, col, row, int(z["nr"])))

    lines.append(f"{len(levels)} ! levels plus icon data:")
    lines.append("! #  refHt   delHt  ni  u  name")
    for i, lvl in enumerate(levels, start=1):
        lvl_name = _unique_contam_name(lvl["name"], used_names)
        icons = icons_by_level.get(i, [])
        lines.append(
            f"  {i} {lvl['refht']:.3f} {lvl['delht']:.3f} {len(icons)} 0 0 {lvl_name}"
        )
        if icons:
            lines.append("!icn col row  #")
            for icn, col, row, nr in icons:
                lines.append(f" {icn:3d} {col:3d} {row:3d} {nr:3d}")
    lines.append(_SENTINEL)



def _append_schedule_sections(lines: list[str], ctx: dict[str, Any]) -> None:
    net = ctx["net"]
    used_names = ctx["used_names"]
    # Day / week schedules
    day_schedules = list(net.get("day_schedules") or [])
    week_schedules = list(net.get("week_schedules") or [])
    day_by_id = dict(net.get("day_by_id") or {})
    if not day_schedules:
        # Skeleton fiction export: constant OA fraction (Contam defaults fo=1
        # without a schedule → no recirculation).
        oa = _DEFAULT_OA_FRACTION
        day_schedules = [{
            "id": "OAFrac",
            "name": "OAFrac",
            "description": "Outdoor-air fraction on AHS recirculation path",
            "points": [["00:00:00", oa], ["24:00:00", oa]],
        }]
        week_schedules = [{
            "id": "OAFracW",
            "name": "OAFracW",
            "description": "Week schedule for outdoor-air fraction",
            "day_id": "OAFrac",
        }]
        day_by_id = {"OAFrac": 1}
    lines.append(f"{len(day_schedules)} ! day-schedules:")
    if day_schedules:
        lines.append("! # npts shap utyp ucnv name")
        for i, ds in enumerate(day_schedules, start=1):
            pts = ds.get("points") or []
            dname = _unique_contam_name(str(ds.get("name", f"D{i}")), used_names)
            lines.append(f"  {i}    {len(pts)}    0    1    0 {dname}")
            lines.append(str(ds.get("description", "")))
            for t, v in pts:
                lines.append(f" {t} {v}")
    lines.append(_SENTINEL)

    lines.append(f"{len(week_schedules)} ! week-schedules:")
    if week_schedules:
        lines.append("! # utyp ucnv name")
        for i, ws in enumerate(week_schedules, start=1):
            wname = _unique_contam_name(str(ws.get("name", f"W{i}")), used_names)
            lines.append(f"  {i}    1    0 {wname}")
            lines.append(str(ws.get("description", "")))
            day_nr = int(day_by_id.get(ws.get("day_id"), 1))
            lines.append(" " + " ".join(str(day_nr) for _ in range(12)))
    lines.append(_SENTINEL)



def _append_wind_filter_sections(lines: list[str], ctx: dict[str, Any]) -> None:
    net = ctx["net"]
    species = ctx.get("species") or [{"name": "Air"}]
    used_names = ctx["used_names"]
    # Wind profiles
    wind_profiles = net.get("wind_profiles") or []
    lines.append(f"{len(wind_profiles)} ! wind pressure profiles:")
    for i, wp in enumerate(wind_profiles, start=1):
        pts = wp.get("points") or []
        wname = _unique_contam_name(str(wp.get("name", f"WPF{i}")), used_names)
        lines.append(f"{i} {len(pts)} {int(wp.get('type', 2))} {wname}")
        lines.append(str(wp.get("description", "")))
        for azm, coef in pts:
            lines.append(f" {float(azm):6.1f}  {float(coef):6.2f}")
    lines.append(_SENTINEL)

    lines.append("0 ! kinetic reactions:")
    lines.append(_SENTINEL)

    # Filters
    filter_elements = net.get("filter_elements") or []
    filters = net.get("filters") or []
    lines.append(f"{len(filter_elements)} ! filter elements:")
    for fe in filter_elements:
        lines.append(
            f"{fe['nr']} cef {fe['area']:.4g} {fe['depth']:.4g} "
            f"{fe['dens']:.4g} 3 3 {fe['name']}"
        )
        lines.append(str(fe.get("description", "")))
        # Efficiency applied to each contaminant species
        n_sp = max(len(species), 1)
        lines.append(f"{n_sp}")
        for sp in species:
            lines.append(f"{sp['name']} {float(fe['efficiency']):.6g}")
    lines.append(_SENTINEL)

    lines.append(f"{len(filters)} ! filters:")
    for flt in filters:
        lines.append(f"{flt['nr']} {flt['fe']} {flt['nsub']}")
        lines.append("0 0")
    lines.append(_SENTINEL)

    lines.append("0 ! source/sink elements:")
    lines.append(_SENTINEL)



def _append_flow_and_duct_elements(lines: list[str], ctx: dict[str, Any]) -> None:
    net = ctx["net"]
    used_names = ctx["used_names"]
    elements = ctx["elements"]
    # Flow elements
    lines.append(f"{len(elements)} ! flow elements:")
    for el in elements:
        el_name = _unique_contam_name(el["name"], used_names)
        lines.append(f"{el['nr']} {el['type']} {el['symbol']} {el_name}")
        lines.append("")
        lines.append(f" {el['params']}")
    lines.append(_SENTINEL)

    # Duct elements (nr icon dtype_symbol name)
    duct_elements = net.get("duct_elements") or []
    lines.append(f"{len(duct_elements)} ! duct elements:")
    for de in duct_elements:
        de_name = _unique_contam_name(de["name"], used_names)
        lines.append(f"{de['nr']} {de['icon']} {de['symbol']} {de_name}")
        lines.append(str(de.get("desc", "")))
        lines.append(f" {de['rough']} {de['lam']} 3")
        lines.append(
            f" {de['hdia']} {de['perim']} {de['area']} 0 0 0 {de['qr']} {de['pr']}"
        )
        lines.append(" 0 3 3 3 3 3 4 0")
    lines.append(_SENTINEL)

    lines.append("0 ! control super elements:")
    lines.append(_SENTINEL)

    control_nodes = net.get("control_nodes") or []
    lines.append(f"{len(control_nodes)} ! control nodes:")
    if control_nodes:
        lines.append("! # typ seq f n  c1  c2 name")
        for cn in control_nodes:
            cname = _unique_contam_name(str(cn["name"]), used_names)
            lines.append(
                f"  {cn['nr']} {cn['typ']}  {cn['seq']} {cn['f']} {cn['n']}   "
                f"{cn['c1']}   {cn['c2']} {cname}"
            )
            lines.append(str(cn.get("desc", "")))
            params = str(cn.get("params", "")).strip()
            if params:
                lines.append(f" {params}")
    lines.append(_SENTINEL)



def _append_ahs_zones_and_paths(lines: list[str], ctx: dict[str, Any]) -> None:
    species = ctx.get("species") or [{"name": "Air"}]
    cidxs = ctx.get("cidxs") or [1]
    zone_records = ctx["zone_records"]
    paths = ctx["paths"]
    ahs_records = ctx["ahs_records"]
    # Simple AHS
    lines.append(f"{len(ahs_records)} ! simple AHS:")
    lines.append("! # zr# zs# pr# ps# px# name")
    for ahs in ahs_records:
        lines.append(
            f"  {ahs['nr']}   {ahs['ret_nr']}   {ahs['sup_nr']}   "
            f"{ahs['pr']}   {ahs['ps']}   {ahs['px']} -1 {ahs['name']}"
        )
        lines.append(f"Crusher HVAC {ahs['hvac_id']} ach={ahs['ach']}")
    lines.append(_SENTINEL)

    # Zones
    lines.append(f"{len(zone_records)} ! zones:")
    lines.append(
        "! Z#  f  s#  c#  k#  l#  relHt    Vol  T0  P0  name  clr uH uT uP uV "
        "axs cdvf <cdvfName> cfd <cfdName> <1dData:>"
    )
    for z in zone_records:
        lines.append(
            f"   {z['nr']}  {z['flag']}   0   0   0   {z['level']}   "
            f"{z['rel_ht']:.3f}  {z['volume']:.6g} {z['temp']:.2f} 0 "
            f"{z['name']} -1 0 2 0 0 0 0 0"
        )
    lines.append(_SENTINEL)

    # Initial concentrations (one column per contaminant).
    # ContamW/ContamX: section header nn must equal n_zones * n_ctm.
    n_ctm = len(cidxs)
    lines.append(
        f"{len(zone_records) * n_ctm} ! initial zone concentrations:"
    )
    header_names = " ".join(sp["name"] for sp in species[:n_ctm])
    lines.append(f"! Z#       {header_names}")
    zeros = "  ".join(_ZERO_CONC for _ in range(n_ctm))
    for z in zone_records:
        lines.append(f"   {z['nr']}  {zeros}")
    lines.append(_SENTINEL)

    # Flow paths
    lines.append(f"{len(paths)} ! flow paths:")
    lines.append(
        "! P#    f  n#  m#  e#  f#  w#  a#  s#  c#  l#    X       Y      "
        "relHt  mult wPset wPmod wazm Fahs Xmax Xmin icn dir u[4] cdvf "
        "<cdvfName> cfd <cfdData[4]>"
    )
    for p in paths:
        wazm = p.get("wazm", -1.0)
        wazm_s = f"{wazm:g}" if wazm != -1.0 else "-1"
        lines.append(
            f"   {p['nr']}    {p['flag']}  {p['from_nr']}   {p['to_nr']}   "
            f"{p['elem_nr']}   {int(p.get('filter_nr', 0))}   "
            f"{int(p.get('wind_nr', 0))}   {p['ahs_nr']}   "
            f"{int(p.get('sched_nr', 0))}   0   {p['level']}   "
            f"{float(p.get('x', 0.0)):.3f}   {float(p.get('y', 0.0)):.3f}   "
            f"0.000 1 0 {float(p.get('w_pmod', 0.0)):g} {wazm_s} "
            f"{p['fahs']:.8g} 0 0   0  1 -1 0 0 0 0 0 0"
        )
    lines.append(_SENTINEL)



def _append_duct_junctions_and_segments(
    lines: list[str],
    net: dict[str, Any],
    zeros: str,
    n_ctm: int,
) -> None:
    """Emit duct junctions, junction concentrations, and duct segments."""
    duct_junctions = net.get("duct_junctions") or []
    duct_segments = net.get("duct_segments") or []
    lines.append(f"{len(duct_junctions)} ! duct junctions:")
    if duct_junctions:
        lines.append(
            "! J#  f  t  z#  d#  k#  s#  c#  l#    X       Y      relHt  "
            "T0  P0  icn clr u[4] ..."
        )
        for j in duct_junctions:
            # ContamX 3.4.0.3 duct-terminal grammar (empirically from compare suite):
            # - Always consumes a vf_node_name *string* after vf_type (even when
            #   vf_type==0). Omitting it shifts fields so Ad lands on bal →
            #   "Bad short integer: <Ad>".
            # - Does *not* accept the ContamW 2.3 "T:" marker (NIST TN 1887r1
            #   still documents it); ContamX reports "Bad integer: T:".
            # Terminal ints follow the name directly: pf pw wPset wPmod wazm bal
            # Ad Af Fdes Ct Cb Cbmax u_A u_F ddir fdir.
            lines.append(
                f"  {j['nr']}  {j['flags']}  {j['jtype']}  {j['pzn']}  0  "
                f"0  0  0  {j['level']}  {j['x']:.3f}  {j['y']:.3f}  "
                f"{j['rel_ht']:.3f}  {j['temp']:.2f} 0  21 -1 0 0 2 0 "
                f"0 none "
                f"0 0 0 0 -1 0 {j['Ad']:.6g} {j['Af']:.6g} 0 "
                f"{j['Ct']:.4g} 0 0 3 3 1 1"
            )
    lines.append(_SENTINEL)

    n_jct = len(duct_junctions)
    # ContamW/ContamX: section header nn must equal n_junctions * n_ctm.
    lines.append(f"{n_jct * n_ctm} ! initial junction concentrations:")
    if n_jct:
        for j in duct_junctions:
            lines.append(f"   {j['nr']}  {zeros}")
    lines.append(_SENTINEL)

    lines.append(f"{len(duct_segments)} ! duct segments:")
    if duct_segments:
        lines.append("! D#  f  n#  m#  e#  f#  s#  c# dir length ...")
        for seg in duct_segments:
            # Match junction vf_type handling: always emit vf_node_name.
            lines.append(
                f"  {seg['nr']}  {seg['flags']}  {seg['pjn']}  {seg['pjm']}  "
                f"{seg['pe']}  0  0  0  1  {seg['length']:.4g} 0 0 0 -1 3 3 0 none"
            )
    lines.append(_SENTINEL)


def _append_duct_network_and_footer(lines: list[str], ctx: dict[str, Any]) -> None:
    net = ctx["net"]
    zeros = ctx.get("zeros") or _ZERO_CONC
    n_ctm = len(ctx.get("cidxs") or [1])
    hobbyist = ctx["hobbyist"]
    zone_records = ctx["zone_records"]
    path_map = ctx["path_map"]
    _append_duct_junctions_and_segments(lines, net, zeros, n_ctm)

    lines.append("0 ! source/sinks:")
    lines.append(_SENTINEL)
    lines.append("0 ! occupancy schedules:")
    lines.append(_SENTINEL)
    lines.append("0 ! exposures:")
    lines.append(_SENTINEL)

    annotations = net.get("annotations") or []
    lines.append(f"{len(annotations)} ! annotations:")
    for i, ann in enumerate(annotations, start=1):
        lines.append(f"{i} {int(ann.get('color', -1))} {ann['note']}")
    lines.append(_SENTINEL)

    lines.append("* end project file.")
    lines.append("")
    n_real = sum(1 for z in zone_records if not z["is_phantom"])
    n_phantom = sum(1 for z in zone_records if z["is_phantom"])
    lines.append(
        f"! CRUSHER_PATH_MAP_COUNT {len(path_map)} "
        f"zones={n_real} "
        f"phantoms={n_phantom} "
        f"hobbyist={int(bool(hobbyist))}"
    )




def path_map_for_engine(
    path_map: list[dict[str, Any]],
) -> list[tuple[str, str, bool]]:
    """Filter path_map to Crusher transfer paths for ContamXTransportEngine."""
    result: list[tuple[str, str, bool]] = []
    for entry in path_map:
        if not entry.get("crusher_transfer", False):
            continue
        result.append(
            (entry["from_zone"], entry["to_zone"], bool(entry["is_hvac_ducted"]))
        )
    return result


def path_map_full_order(
    path_map: list[dict[str, Any]],
) -> list[tuple[str, str, bool]]:
    """Full ContamX path order (1..N), including non-transfer paths.

    Non-transfer endpoints may be ``ambient`` or AHS phantom names; the
    transport engine skips near-zero flows and ignores unknown zone nodes.
    """
    ordered = sorted(path_map, key=lambda e: int(e["path_nr"]))
    return [
        (e["from_zone"], e["to_zone"], bool(e["is_hvac_ducted"]))
        for e in ordered
    ]


# ── ContamW 3.4 simplify (authentic PRJ → JSON) ───────────────────────────

def _is_phantom_zone(flag: int, name: str) -> bool:
    """AHS return/supply phantom zone (flag or Contam-style name)."""
    return (
        flag == _ZONE_AHS
        or "(Ret)" in name
        or "(Sup)" in name
        or name.endswith("_Ret")
        or name.endswith("_Sup")
    )


def _iter_flow_element_records(
    body: list[str],
) -> list[tuple[int, str, list[str] | None]]:
    """``(nr, symbol, params)`` per flow element; params is the next non-empty line."""
    records: list[tuple[int, str, list[str] | None]] = []
    i = 0
    while i < len(body):
        toks = body[i].split()
        if len(toks) < 4 or not toks[0].isdigit():
            i += 1
            continue
        j = i + 1
        while j < len(body) and not body[j].strip():
            j += 1
        params = body[j].split() if j < len(body) else None
        records.append((int(toks[0]), toks[2], params))
        i = j + 1
    return records


def _classify_prj_zones(
    body: list[str],
) -> tuple[dict[int, str], set[int], set[int]]:
    """``zones`` section → (nr→name, phantom nrs, real nrs)."""
    zone_nr_to_id: dict[int, str] = {}
    phantom_nrs: set[int] = set()
    real_nrs: set[int] = set()
    for ln in body:
        if ln.strip().startswith("!"):
            continue
        toks = ln.split()
        if len(toks) < 11 or not toks[0].isdigit():
            continue
        nr = int(toks[0])
        name = toks[10]
        zone_nr_to_id[nr] = name
        if _is_phantom_zone(int(toks[1]), name):
            phantom_nrs.add(nr)
        else:
            real_nrs.add(nr)
    return zone_nr_to_id, phantom_nrs, real_nrs


def _ahs_path_groups(body: list[str]) -> dict[int, int]:
    """``simple AHS`` section → system-path nr (pr/ps/px) → ahs nr."""
    ahs_path_group: dict[int, int] = {}
    for ln in body:
        if ln.strip().startswith("!"):
            continue
        toks = ln.split()
        if len(toks) >= 6 and toks[0].isdigit():
            ahs_nr = int(toks[0])
            for pnr in (int(toks[3]), int(toks[4]), int(toks[5])):
                ahs_path_group[pnr] = ahs_nr
    return ahs_path_group


def _parse_prj_path_row(ln: str) -> tuple[int, int, int, int, int, int] | None:
    """``flow paths`` row → (nr, flag, from, to, elem, ahs) or None."""
    if ln.strip().startswith("!"):
        return None
    toks = ln.split()
    if len(toks) < 11 or not toks[0].isdigit():
        return None
    try:
        return (
            int(toks[0]), int(toks[1]), int(toks[2]),
            int(toks[3]), int(toks[4]), int(toks[7]),
        )
    except ValueError:
        return None


def _classify_path_kind(
    flag: int,
    *,
    from_nr: int,
    to_nr: int,
    from_ph: bool,
    to_ph: bool,
    both_real: bool,
    is_fan: bool,
) -> str:
    if flag == _PATH_AHS_OA:
        return "ahs_oa"
    if flag == _PATH_AHS_EXHAUST:
        return "ahs_exhaust"
    if flag == _PATH_AHS_RECIRC:
        return "ahs_recirc"
    if flag == _PATH_AHS_TERMINAL:
        if from_ph and not to_ph:
            return "ahs_supply"
        if to_ph and not from_ph:
            return "ahs_return"
        return "ahs_terminal"
    if from_nr < 0 or to_nr < 0:
        return "envelope_leak"
    if both_real and is_fan:
        return "cross_zone"
    if both_real:
        return "passageway"
    return "other"


def path_map_from_prj(text: str) -> list[dict[str, Any]]:
    """Build ContamX ``path_map`` entries directly from a ContamW 3.4 ``.prj``.

    This is the Path A / Path B primary contract: authentic PRJs carry their
    own path numbering. Fiction JSON→PRJ export is bootstrap-only.
    """
    if not text.lstrip().startswith("ContamW"):
        raise ValueError(
            "Not a recognized CONTAM .prj file (missing 'ContamW' signature)"
        )
    sections = dict(_section_blocks(text))

    zone_nr_to_id, phantom_nrs, real_nrs = _classify_prj_zones(
        sections.get("zones", [])
    )
    ahs_path_group = _ahs_path_groups(sections.get("simple AHS", []))
    elem_is_fan = {
        nr: "fan" in symbol.lower()
        for nr, symbol, _params in _iter_flow_element_records(
            sections.get("flow elements", [])
        )
    }

    def _endpoint_name(nr: int) -> str:
        if nr < 0:
            return "ambient"
        return zone_nr_to_id.get(nr, f"zone_{nr}")

    path_map: list[dict[str, Any]] = []
    for ln in sections.get("flow paths", []):
        row = _parse_prj_path_row(ln)
        if row is None:
            continue
        pnr, flag, from_nr, to_nr, elem_nr, ahs_field = row
        both_real = (from_nr in real_nrs) and (to_nr in real_nrs)
        kind = _classify_path_kind(
            flag,
            from_nr=from_nr,
            to_nr=to_nr,
            from_ph=from_nr in phantom_nrs or from_nr < 0,
            to_ph=to_nr in phantom_nrs or to_nr < 0,
            both_real=both_real,
            is_fan=elem_is_fan.get(elem_nr, False),
        )
        path_map.append({
            "path_nr": pnr,
            "from_zone": _endpoint_name(from_nr),
            "to_zone": _endpoint_name(to_nr),
            "is_hvac_ducted": kind.startswith("ahs_") or kind == "cross_zone",
            "kind": kind,
            "crusher_transfer": both_real,
            "ahs_nr": ahs_field if ahs_field > 0 else ahs_path_group.get(pnr, 0),
        })

    return sorted(path_map, key=lambda e: int(e["path_nr"]))


# ── ContamW 3.4 simplify (authentic PRJ → JSON) ───────────────────────────


def _is_contamw34(text: str) -> bool:
    first = text.lstrip().splitlines()[0] if text.strip() else ""
    if not first.startswith("ContamW"):
        return False
    # Interchange dialect uses custom !------ section headers
    if "!------ levels" in text or "!------ zones" in text:
        return False
    return " ! zones:" in text or "! zones:" in text


def _parse_section_header(stripped: str) -> tuple[int, str] | None:
    """Parse ``N ! name:`` ContamW section headers without regex backtracking."""
    if "!" not in stripped or not stripped.endswith(":"):
        return None
    left, _, right = stripped.partition("!")
    name = right.strip().rstrip(":").strip()
    count_s = left.strip()
    if not count_s or not name:
        return None
    try:
        return int(count_s), name
    except ValueError:
        return None


def _section_blocks(text: str) -> list[tuple[str, list[str]]]:
    """Split ContamW PRJ into (section_name, body_lines) by ``N ! name:``."""
    lines = text.splitlines()
    sections: list[tuple[str, list[str]]] = []
    i = 0
    # Skip header until first ``N !`` section after rvals sentinel typically
    header_done = False
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()
        header = _parse_section_header(stripped)
        if header is not None and header_done:
            count, name = header
            i += 1
            body: list[str] = []
            # Collect until -999 (not counting nested -999 in weird cases)
            while i < len(lines):
                if lines[i].strip() == _SENTINEL:
                    i += 1
                    break
                body.append(lines[i])
                i += 1
            sections.append((name, body))
            # count is advisory; Contam uses -999 as terminator
            _ = count
            continue
        if stripped == _SENTINEL and not header_done:
            header_done = True
        i += 1
    return sections


_SIMPLIFY_DROPPED_SECTIONS = (
    "day-schedules",
    "week-schedules",
    "wind pressure profiles",
    "kinetic reactions",
    "filter elements",
    "filters",
    "source/sink elements",
    "duct elements",
    "control super elements",
    "control nodes",
    "duct junctions",
    "duct segments",
    "source/sinks",
    "occupancy schedules",
    "exposures",
    "annotations",
)


def _warn_dropped_sections(sections: dict[str, list[str]], warn: list[str]) -> None:
    for dropped in _SIMPLIFY_DROPPED_SECTIONS:
        body = sections.get(dropped)
        if body is not None and any(ln.strip() for ln in body):
            warn.append(f"Dropped Contam section on simplify: {dropped}")


def _parse_level_names(body: list[str]) -> dict[int, str]:
    """``levels plus icon data`` rows: nr refHt delHt ni u u name."""
    level_names: dict[int, str] = {}
    for ln in body:
        toks = ln.split()
        if len(toks) >= 6 and toks[0].isdigit():
            level_names[int(toks[0])] = toks[-1]
    return level_names


def _parse_simplify_zone_row(toks: list[str]) -> tuple[int, int, int, float, str] | None:
    """``zones`` row → (nr, flag, level, volume, name); None when malformed."""
    try:
        nr = int(toks[0])
        flag = int(toks[1])
        level = int(toks[5])
        float(toks[6])  # rel_ht
        vol = float(toks[7])
        float(toks[8])  # temp
        name = toks[10]
    except (ValueError, IndexError):
        return None
    return nr, flag, level, vol, name


def _parse_simplify_zones(
    body: list[str],
    level_names: dict[int, str],
) -> tuple[list[dict[str, Any]], dict[int, str], set[int]]:
    """``zones`` section → (platform zones, nr→name, phantom nrs)."""
    zones: list[dict[str, Any]] = []
    zone_nr_to_id: dict[int, str] = {}
    phantom_nrs: set[int] = set()
    for ln in body:
        if ln.strip().startswith("!"):
            continue
        toks = ln.split()
        if len(toks) < 11:
            continue
        parsed = _parse_simplify_zone_row(toks)
        if parsed is None:
            continue
        nr, flag, level, vol, name = parsed
        zone_nr_to_id[nr] = name
        if _is_phantom_zone(flag, name):
            phantom_nrs.add(nr)
            continue
        zone: dict[str, Any] = {
            "id": name,
            "type": "Free",
            "traffic": "medium",
            "volume_m3": vol if vol > 0 else 100.0,
            "deck": level_names.get(level, f"level_{level}"),
            "display": {"x": float(nr), "y": float(level)},
        }
        if vol > 0:
            zone["ceiling_height_m"] = _DEFAULT_CEILING_HEIGHT_M
            zone["floor_area_m2"] = zone["volume_m3"] / _DEFAULT_CEILING_HEIGHT_M
            zone["elevation_m"] = (level - 1) * _DEFAULT_CEILING_HEIGHT_M
        zones.append(zone)
    return zones, zone_nr_to_id, phantom_nrs


def _parse_flow_elements(
    body: list[str],
) -> tuple[dict[int, bool], dict[int, float]]:
    """``flow elements`` section → (nr→is_fan, fan nr→design flow m³/h)."""
    elem_is_fan: dict[int, bool] = {}
    elem_flow_m3h: dict[int, float] = {}
    for enr, symbol, params in _iter_flow_element_records(body):
        is_fan = "fan" in symbol.lower()
        elem_is_fan[enr] = is_fan
        if not (is_fan and params):
            continue
        try:
            elem_flow_m3h[enr] = float(params[0]) * 3600.0
        except ValueError:
            elem_flow_m3h[enr] = 0.0
    return elem_is_fan, elem_flow_m3h


def _parse_simple_ahs(body: list[str]) -> list[dict[str, Any]]:
    """``simple AHS`` records (+ optional Crusher description with ``ach=``)."""
    hvac_zones: list[dict[str, Any]] = []
    for ai, ln in enumerate(body):
        if ln.strip().startswith("!"):
            continue
        toks = ln.split()
        if len(toks) < 7 or not toks[0].isdigit():
            continue
        name = toks[-1]
        ach = 6.0
        # Description is typically the next non-empty line
        if ai + 1 < len(body):
            desc = body[ai + 1].strip()
            m_ach = re.search(r"ach=([0-9.]+)", desc)
            if m_ach:
                ach = float(m_ach.group(1))
            m_id = re.search(r"Crusher HVAC\s+(\S+)", desc)
            if m_id:
                name = m_id.group(1)
        hvac_zones.append({
            "id": name,
            "rooms": [],
            "ach": ach,
            "_ahs_nr": int(toks[0]),
            "_ret": int(toks[1]),
            "_sup": int(toks[2]),
        })
    return hvac_zones


def _parse_simplify_flow_paths(
    body: list[str],
    *,
    zone_nr_to_id: dict[int, str],
    phantom_nrs: set[int],
    elem_is_fan: dict[int, bool],
    elem_flow_m3h: dict[int, float],
    ahs_zone_set: dict[int, set[str]],
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    """``flow paths`` → (adjacency, cross_zone_links); fills *ahs_zone_set*."""
    adjacency: list[dict[str, str]] = []
    cross_zone_links: list[dict[str, Any]] = []
    for ln in body:
        row = _parse_prj_path_row(ln)
        if row is None:
            continue
        _pnr, _flag, from_nr, to_nr, elem_nr, ahs_nr = row
        from_id = zone_nr_to_id.get(from_nr)
        to_id = zone_nr_to_id.get(to_nr)
        from_phantom = from_nr in phantom_nrs or from_nr < 0
        to_phantom = to_nr in phantom_nrs or to_nr < 0

        # Track room membership via supply/return paths
        if ahs_nr > 0:
            if not from_phantom and to_phantom and from_id:
                ahs_zone_set.setdefault(ahs_nr, set()).add(from_id)
            if from_phantom and not to_phantom and to_id:
                ahs_zone_set.setdefault(ahs_nr, set()).add(to_id)

        if from_phantom or to_phantom or not from_id or not to_id:
            continue

        if elem_is_fan.get(elem_nr, False):
            cross_zone_links.append({
                "from": from_id,
                "to": to_id,
                "flow_rate_m3h": round(elem_flow_m3h.get(elem_nr, 50.0), 6),
                "is_hvac_ducted": True,
                "path": f"contam_path_{from_id}_{to_id}",
            })
        else:
            adjacency.append({
                "from": from_id,
                "to": to_id,
                "type": "passageway",
            })
    return adjacency, cross_zone_links


def _recover_platform_name(text: str) -> str:
    """Platform id from the ``Crusher platform`` WPC description line."""
    platform = "imported_from_contam"
    for ln in text.splitlines()[:20]:
        if ln.startswith("Crusher platform "):
            return ln.split("Crusher platform ", 1)[1].strip() or platform
    return platform


def simplify_contamw34(
    text: str,
    *,
    warnings_out: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Simplify an authentic ContamW 3.4 ``.prj`` into platform JSON.

    Drops controls, schedules, wind profiles, sources, ducts, and exposures
    (logged via *warnings_out* when provided).
    """
    warn = warnings_out if warnings_out is not None else []
    if not text.lstrip().startswith("ContamW"):
        raise ValueError(
            "Not a recognized CONTAM .prj file (missing 'ContamW' signature)"
        )

    sections = dict(_section_blocks(text))
    _warn_dropped_sections(sections, warn)

    level_names = _parse_level_names(sections.get("levels plus icon data", []))
    zones, zone_nr_to_id, phantom_nrs = _parse_simplify_zones(
        sections.get("zones", []), level_names
    )
    elem_is_fan, elem_flow_m3h = _parse_flow_elements(
        sections.get("flow elements", [])
    )
    hvac_zones = _parse_simple_ahs(sections.get("simple AHS", []))
    ahs_zone_set: dict[int, set[str]] = {hz["_ahs_nr"]: set() for hz in hvac_zones}
    adjacency, cross_zone_links = _parse_simplify_flow_paths(
        sections.get("flow paths", []),
        zone_nr_to_id=zone_nr_to_id,
        phantom_nrs=phantom_nrs,
        elem_is_fan=elem_is_fan,
        elem_flow_m3h=elem_flow_m3h,
        ahs_zone_set=ahs_zone_set,
    )

    # Fill HVAC rooms from supply/return path membership
    for hz in hvac_zones:
        ahs_nr = hz.pop("_ahs_nr")
        hz.pop("_ret", None)
        hz.pop("_sup", None)
        hz["rooms"] = sorted(ahs_zone_set.get(ahs_nr, set()))

    # If no AHS recovered, create a single default HVAC zone
    if not hvac_zones and zones:
        hvac_zones = [{
            "id": "zone_all",
            "rooms": [z["id"] for z in zones],
            "ach": 6.0,
        }]

    platform = _recover_platform_name(text)
    description = f"Simplified from ContamW 3.4 .prj ({platform})"
    spatial: dict[str, Any] = {
        "platform": platform,
        "description": description,
        "zones": zones,
    }
    if zones:
        spatial["graywater_zones"] = [zones[0]["id"]]

    airflow: dict[str, Any] = {
        "platform": platform,
        "description": description,
        "hvac_zones": hvac_zones,
        "cross_zone_links": cross_zone_links,
        "adjacency": adjacency,
    }

    if warnings_out is None:
        for w in warn:
            warnings.warn(w, stacklevel=2)

    return spatial, airflow
