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


def _unique_contam_name(
    raw: str,
    used: set[str],
    *,
    max_len: int = _CONTAM_NAME_MAX,
) -> str:
    """Return a Contam-safe unique name ≤ *max_len* characters."""
    base = _sanitize_name(raw)[:max_len] or "z"
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
    zones = list(spatial_layout.get("zones", []))
    hvac_zones = list(air_flow_paths.get("hvac_zones", []))
    cross_links = list(air_flow_paths.get("cross_zone_links", []))
    adjacency = list(air_flow_paths.get("adjacency", []))
    overrides = dict(overrides or {})
    pack = pack or (_hobby.load_hobbyist_pack() if hobbyist else {})

    levels = _build_levels(zones)
    level_index = {lvl["name"]: i + 1 for i, lvl in enumerate(levels)}
    deck_order = {lvl["name"]: i for i, lvl in enumerate(levels)}
    deck_dims = spatial_layout.get("deck_dimensions") or {}
    beam_m = float(deck_dims.get("beam_m", 15.0) or 15.0)

    used_contam_names: set[str] = set()
    zone_name_to_nr: dict[str, int] = {}
    zone_by_id: dict[str, dict[str, Any]] = {z["id"]: z for z in zones}
    zone_records: list[dict[str, Any]] = []
    for i, zone in enumerate(zones, start=1):
        name = _unique_contam_name(zone["id"], used_contam_names)
        geo = _fill_zone_geometry(zone, deck_order)
        deck = str(zone.get("deck", "main"))
        display = zone.get("display", {}) or {}
        temp = (
            _hobby.deck_temp_k(deck, overrides, _DEFAULT_ZONE_TEMP_K)
            if hobbyist
            else _DEFAULT_ZONE_TEMP_K
        )
        zone_name_to_nr[zone["id"]] = i
        zone_name_to_nr[name] = i
        zone_records.append({
            "nr": i,
            "flag": _ZONE_NORMAL,
            "level": level_index.get(deck, 1),
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

    next_zone = len(zone_records) + 1
    # Map HVAC group id -> (first_room_id, room_ids, ach, ret_nr, sup_nr)
    hvac_info: list[dict[str, Any]] = []
    for hz in hvac_zones:
        rooms = [r for r in hz.get("rooms", []) if r in zone_name_to_nr]
        if not rooms:
            continue
        ahs_i = len(hvac_info) + 1
        ach = float(hz.get("ach", 6.0))
        # Contam-style short phantoms: ahs1(Ret) / ahs1(Sup) (≤ 15 chars)
        ret_name = _unique_contam_name(f"ahs{ahs_i}(Ret)", used_contam_names)
        sup_name = _unique_contam_name(f"ahs{ahs_i}(Sup)", used_contam_names)
        ahs_name = _unique_contam_name(f"ahs{ahs_i}", used_contam_names)
        ret_nr = next_zone
        zone_name_to_nr[ret_name] = ret_nr
        zone_records.append({
            "nr": ret_nr,
            "flag": _ZONE_AHS,
            "level": 1,
            "rel_ht": 0.0,
            "volume": 0.0,
            "area": 0.0,
            "height": _DEFAULT_CEILING_HEIGHT_M,
            "elevation": 0.0,
            "temp": _DEFAULT_ZONE_TEMP_K,
            "name": ret_name,
            "orig_id": ret_name,
            "type": "Free",
            "traffic": "low",
            "deck": "main",
            "x": 0.0,
            "y": 0.0,
            "is_phantom": True,
        })
        next_zone += 1
        sup_nr = next_zone
        zone_name_to_nr[sup_name] = sup_nr
        zone_records.append({
            "nr": sup_nr,
            "flag": _ZONE_AHS,
            "level": 1,
            "rel_ht": 0.0,
            "volume": 0.0,
            "area": 0.0,
            "height": _DEFAULT_CEILING_HEIGHT_M,
            "elevation": 0.0,
            "temp": _DEFAULT_ZONE_TEMP_K,
            "name": sup_name,
            "orig_id": sup_name,
            "type": "Free",
            "traffic": "low",
            "deck": "main",
            "x": 0.0,
            "y": 0.0,
            "is_phantom": True,
        })
        next_zone += 1
        hvac_info.append({
            "id": hz["id"],
            "rooms": rooms,
            "ach": ach,
            "ret_nr": ret_nr,
            "sup_nr": sup_nr,
            "ret_name": ret_name,
            "sup_name": sup_name,
            "ahs_name": ahs_name,
        })

    # Flow elements: 1 = Opening (legacy default), 2 = EnvLeak, then typed
    # orifices (hobbyist) and fans.
    elements: list[dict[str, Any]] = [
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
    orifice_elem_by_key: dict[str, int] = {"envelope": 2}
    if hobbyist:
        env_area = float(
            pack["orifice_catalog"]["envelope_leak"].get("area_m2", 0.0001)
        )
        elements[1]["params"] = _hobby.orifice_params_for_area(env_area)
        name_to_elem: dict[str, int] = {}
        for key, spec in pack["orifice_catalog"]["types"].items():
            el_label = str(spec.get("name", key))[:15]
            if el_label in name_to_elem:
                orifice_elem_by_key[key] = name_to_elem[el_label]
                continue
            nr = len(elements) + 1
            area = float(spec.get("area_m2", 0.01))
            elements.append({
                "nr": nr,
                "type": _ELEM_ORIFICE,
                "symbol": "plr_orfc",
                "name": el_label,
                "params": _hobby.orifice_params_for_area(area),
            })
            name_to_elem[el_label] = nr
            orifice_elem_by_key[key] = nr

    fan_elem_by_m3s: dict[float, int] = {}

    def _fan_elem(flow_m3h: float) -> int:
        m3s = max(flow_m3h, 0.0) / 3600.0
        key = round(m3s, 12)
        if key in fan_elem_by_m3s:
            return fan_elem_by_m3s[key]
        nr = len(elements) + 1
        elements.append({
            "nr": nr,
            "type": _ELEM_FAN_CVF,
            "symbol": "fan_cvf",
            "name": f"Fan_{nr}",
            "params": f"{m3s:.12g} 3",
            "flow_m3h": flow_m3h,
        })
        fan_elem_by_m3s[key] = nr
        return nr

    # Hobbyist schedules / wind / filters (indices are 1-based Contam refs)
    sched_oa_week = 0
    sched_duty_week = 0
    wind_nr = 0
    filter_nr_by_preset: dict[str, int] = {}
    filter_elements: list[dict[str, Any]] = []
    filters: list[dict[str, Any]] = []
    day_schedules: list[dict[str, Any]] = []
    week_schedules: list[dict[str, Any]] = []
    wind_profiles: list[dict[str, Any]] = []
    control_nodes: list[dict[str, Any]] = []
    annotations: list[dict[str, Any]] = []
    duct_elements: list[dict[str, Any]] = []
    duct_junctions: list[dict[str, Any]] = []
    duct_segments: list[dict[str, Any]] = []
    species: list[dict[str, Any]] = []
    contaminant_indices: list[int] = [1]
    day_by_id: dict[str, int] = {}

    if hobbyist:
        # Schedules
        for i, ds in enumerate(pack["schedule_templates"]["day_schedules"], 1):
            day_schedules.append(ds)
            day_by_id[ds["id"]] = i
        for i, ws in enumerate(pack["schedule_templates"]["week_schedules"], 1):
            week_schedules.append(ws)
            if ws["id"] == pack["schedule_templates"]["defaults"]["oa_week"]:
                sched_oa_week = i
            if ws["id"] == pack["schedule_templates"]["defaults"]["duty_week"]:
                sched_duty_week = i
        if not overrides.get("night_setback", True):
            # Drop night-setback week/day if disabled (keep OA + duty)
            week_schedules = [
                w for w in week_schedules if w["id"] != "NightSetbackW"
            ]
            day_schedules = [
                d for d in day_schedules if d["id"] != "NightSetback"
            ]
            day_by_id.clear()
            day_by_id.update(
                {d["id"]: i for i, d in enumerate(day_schedules, 1)}
            )
            sched_oa_week = 0
            sched_duty_week = 0
            for i, ws in enumerate(week_schedules, 1):
                if ws["id"] == pack["schedule_templates"]["defaults"]["oa_week"]:
                    sched_oa_week = i
                if ws["id"] == pack["schedule_templates"]["defaults"]["duty_week"]:
                    sched_duty_week = i

        # Wind
        wkey = _hobby.resolve_wind_profile_key(pack, overrides)
        wind_profiles.append(pack["wind_profiles"]["profiles"][wkey])
        wind_nr = 1

        # Species
        species = list(pack["species_pack"]["species"])
        contaminant_indices = list(range(1, len(species) + 1))

        # Light controls (portfolio spice — not wired into AHS paths)
        control_nodes = [
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

        # Annotations from overrides + deck labels
        ann_map = dict(overrides.get("zone_annotations") or {})
        for zid, note in ann_map.items():
            annotations.append({"color": -1, "note": str(note)[:60]})
        for lvl in levels:
            annotations.append({
                "color": 2,
                "note": f"Deck {lvl['name']}"[:60],
            })
        for info in hvac_info:
            annotations.append({
                "color": 2,
                "note": f"HVAC {info['id']}"[:60],
            })

    paths: list[dict[str, Any]] = []
    path_map: list[dict[str, Any]] = []

    def _add_path(
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
        pnr = len(paths) + 1
        paths.append({
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
        path_map.append({
            "path_nr": pnr,
            "from_zone": from_name,
            "to_zone": to_name,
            "is_hvac_ducted": is_hvac_ducted,
            "kind": kind,
            "crusher_transfer": crusher_transfer,
            "ahs_nr": ahs_group or ahs_nr,
        })
        return pnr

    # 1) Envelope leakage to ambient (pressure-dependent reference).
    for z in zone_records:
        if z["is_phantom"]:
            continue
        wazm = -1.0
        w_nr = 0
        wmod = 0.0
        if hobbyist and wind_nr:
            src = zone_by_id.get(z["orig_id"], {})
            wazm = _hobby.wall_azimuth_deg(
                z["orig_id"], src, overrides, beam_m=beam_m,
            )
            w_nr = wind_nr
            wmod = 0.8
        _add_path(
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

    # 2) Adjacency openings (typed orifices when hobbyist)
    for adj in adjacency:
        a, b = adj["from"], adj["to"]
        if a not in zone_name_to_nr or b not in zone_name_to_nr:
            continue
        adj_type = str(adj.get("type", "passageway"))
        elem = 1
        if hobbyist:
            okey = _hobby.resolve_orifice_type(adj_type, pack, overrides)
            elem = orifice_elem_by_key.get(okey, 1)
        za = zone_records[zone_name_to_nr[a] - 1]
        zb = zone_records[zone_name_to_nr[b] - 1]
        _add_path(
            zone_name_to_nr[a], zone_name_to_nr[b], elem,
            from_name=a, to_name=b,
            kind=adj_type,
            is_hvac_ducted=False,
            crusher_transfer=True,
            flag=0,
            x=0.5 * (float(za["x"]) + float(zb["x"])),
            y=0.5 * (float(za["y"]) + float(zb["y"])),
        )

    # 3) Cross-zone links as fan_cvf, expanded to all room×room pairs
    # (matches native ContamTransportEngine._build_cross_zone_paths).
    hvac_by_id = {h["id"]: h for h in hvac_info}
    real_room_ids = {z["orig_id"] for z in zone_records if not z["is_phantom"]}

    def _endpoint_rooms(token: str) -> list[str]:
        if token in hvac_by_id:
            return list(hvac_by_id[token]["rooms"])
        if token in real_room_ids:
            return [token]
        if token in zone_name_to_nr:
            return [token]
        return []

    for link in cross_links:
        from_rooms = _endpoint_rooms(link["from"])
        to_rooms = _endpoint_rooms(link["to"])
        if not from_rooms or not to_rooms:
            continue
        flow = float(link.get("flow_rate_m3h", 50.0))
        n_pairs = len(from_rooms) * len(to_rooms)
        pair_flow = flow / n_pairs if n_pairs > 0 else 0.0
        if pair_flow <= 0.0:
            continue
        elem = _fan_elem(pair_flow)
        kind = link.get("path", "cross_zone")
        ducted = bool(link.get("is_hvac_ducted", False))
        for fr in from_rooms:
            for tr in to_rooms:
                _add_path(
                    zone_name_to_nr[fr], zone_name_to_nr[tr], elem,
                    from_name=fr, to_name=tr,
                    kind=kind,
                    is_hvac_ducted=ducted,
                    crusher_transfer=True,
                    flag=0,
                )

    def _ensure_filter(preset: str) -> int:
        if preset in filter_nr_by_preset:
            return filter_nr_by_preset[preset]
        presets = pack["filter_presets"]["presets"]
        spec = presets[preset]
        fe_nr = len(filter_elements) + 1
        el_name = _unique_contam_name(str(spec["name"]), used_contam_names)
        filter_elements.append({
            "nr": fe_nr,
            "name": el_name,
            "description": str(spec.get("description", "")),
            "efficiency": float(spec["efficiency"]),
            "area": float(pack["filter_presets"].get("face_area_m2", 1.0)),
            "depth": float(pack["filter_presets"].get("depth_m", 0.05)),
            "dens": float(pack["filter_presets"].get("density_kg_m3", 100.0)),
        })
        f_nr = len(filters) + 1
        filters.append({"nr": f_nr, "fe": fe_nr, "nsub": 1})
        filter_nr_by_preset[preset] = f_nr
        return f_nr

    # 4) Per-AHS: Contam simple-AHS semantics (match authentic ContamW 3.4)
    ahs_records: list[dict[str, Any]] = []
    default_oa = float(
        pack.get("schedule_templates", {})
        .get("defaults", {})
        .get("oa_fraction", _DEFAULT_OA_FRACTION)
        if hobbyist else _DEFAULT_OA_FRACTION
    )
    for ahs_i, info in enumerate(hvac_info, start=1):
        rooms = info["rooms"]
        ach = info["ach"]
        total_vol = sum(
            next(z["volume"] for z in zone_records if z["orig_id"] == r)
            for r in rooms
        )
        total_flow = ach * total_vol  # m³/h
        oa_frac = (
            _hobby.oa_fraction_for_hvac(info["id"], overrides, default_oa)
            if hobbyist else 0.2
        )
        oa_flow = oa_frac * total_flow
        recirc_flow = (1.0 - oa_frac) * total_flow
        per_room_supply = total_flow / max(len(rooms), 1)
        per_room_fahs = _flow_m3h_to_fahs_kg_s(per_room_supply)
        recirc_fahs = _flow_m3h_to_fahs_kg_s(recirc_flow)

        filt_nr = 0
        if hobbyist:
            preset = _hobby.resolve_filter_preset(
                pack, overrides,
                hvac_id=info["id"],
                filter_efficiency=filter_efficiency,
            )
            filt_nr = _ensure_filter(preset)

        oa_path = _add_path(
            -1, info["sup_nr"], 0,
            from_name="ambient", to_name=info["sup_name"],
            kind="ahs_oa", is_hvac_ducted=True, crusher_transfer=False,
            ahs_nr=0, ahs_group=ahs_i, flag=_PATH_AHS_OA, fahs=0.0, wazm=-1.0,
        )
        ex_path = _add_path(
            info["ret_nr"], -1, 0,
            from_name=info["ret_name"], to_name="ambient",
            kind="ahs_exhaust", is_hvac_ducted=True, crusher_transfer=False,
            ahs_nr=0, ahs_group=ahs_i, flag=_PATH_AHS_EXHAUST, fahs=0.0, wazm=-1.0,
        )
        recirc_path = _add_path(
            info["ret_nr"], info["sup_nr"], 0,
            from_name=info["ret_name"], to_name=info["sup_name"],
            kind="ahs_recirc", is_hvac_ducted=True, crusher_transfer=False,
            ahs_nr=0, ahs_group=ahs_i, flag=_PATH_AHS_RECIRC, fahs=recirc_fahs, wazm=-1.0,
            filter_nr=filt_nr,
            sched_nr=sched_oa_week if hobbyist else _OA_SCHEDULE_NR,
        )

        for room in rooms:
            rnr = zone_name_to_nr[room]
            zrec = next(z for z in zone_records if z["orig_id"] == room)
            _add_path(
                info["sup_nr"], rnr, 0,
                from_name=info["sup_name"], to_name=room,
                kind="ahs_supply", is_hvac_ducted=True, crusher_transfer=False,
                ahs_nr=ahs_i, ahs_group=ahs_i, flag=_PATH_AHS_TERMINAL,
                fahs=per_room_fahs, wazm=0.0,
                sched_nr=sched_duty_week if hobbyist else 0,
                x=float(zrec["x"]), y=float(zrec["y"]),
            )
            _add_path(
                rnr, info["ret_nr"], 0,
                from_name=room, to_name=info["ret_name"],
                kind="ahs_return", is_hvac_ducted=True, crusher_transfer=False,
                ahs_nr=ahs_i, ahs_group=ahs_i, flag=_PATH_AHS_TERMINAL,
                fahs=per_room_fahs, wazm=0.0,
                sched_nr=sched_duty_week if hobbyist else 0,
                x=float(zrec["x"]), y=float(zrec["y"]),
            )

        ahs_records.append({
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

    # 5) Duct leakage spines (hobbyist): passive Darcy trunks between rooms
    if hobbyist:
        duct_cfg = pack["duct_defaults"]
        min_rooms = int(duct_cfg.get("min_rooms_for_trunk", 2))
        allow = overrides.get("duct_hvac_ids")
        allow_set = set(allow) if isinstance(allow, list) else None
        hdia = float(duct_cfg.get("hdia_m", 0.3))
        rough = float(duct_cfg.get("roughness_m", 0.00015))
        lam = float(duct_cfg.get("laminar_loss_per_m", 0.001))
        seg_len = float(duct_cfg.get("segment_length_m", 5.0))
        qr = float(duct_cfg.get("leakage_Ls_per_m2", 1.0))
        pr = float(duct_cfg.get("leakage_Pr_Pa", 250.0))
        ct = float(duct_cfg.get("terminal_loss_Ct", 0.5))
        perim = math.pi * hdia
        area = math.pi * (hdia / 2.0) ** 2

        duct_elements.append({
            "nr": 1,
            "icon": 21,
            "dtype": 23,
            "symbol": "dct_dwc",
            "name": str(duct_cfg.get("element_name", "TrunkDWC"))[:15],
            "desc": "Hobbyist Darcy-Colebrook trunk",
            "rough": rough,
            "lam": lam,
            "hdia": hdia,
            "perim": perim,
            "area": area,
            "qr": qr,
            "pr": pr,
        })

        for info in hvac_info:
            rooms = info["rooms"]
            if len(rooms) < min_rooms:
                continue
            if allow_set is not None and info["id"] not in allow_set:
                continue
            j_nrs: list[int] = []
            for room in rooms:
                z = next(zr for zr in zone_records if zr["orig_id"] == room)
                jnr = len(duct_junctions) + 1
                duct_junctions.append({
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
                j_nrs.append(jnr)
            for a_j, b_j in zip(j_nrs, j_nrs[1:]):
                snr = len(duct_segments) + 1
                duct_segments.append({
                    "nr": snr,
                    "flags": 0,
                    "pjn": a_j,
                    "pjm": b_j,
                    "pe": 1,
                    "length": seg_len,
                })

    return {
        "levels": levels,
        "zone_records": zone_records,
        "elements": elements,
        "paths": paths,
        "path_map": path_map,
        "ahs_records": ahs_records,
        "hvac_info": hvac_info,
        "platform": spatial_layout.get("platform", "crusher_platform"),
        "zone_name_to_nr": zone_name_to_nr,
        "used_contam_names": used_contam_names,
        "hobbyist": hobbyist,
        "day_schedules": day_schedules,
        "week_schedules": week_schedules,
        "wind_profiles": wind_profiles,
        "filter_elements": filter_elements,
        "filters": filters,
        "control_nodes": control_nodes,
        "annotations": annotations,
        "duct_elements": duct_elements,
        "duct_junctions": duct_junctions,
        "duct_segments": duct_segments,
        "species": species,
        "contaminant_indices": contaminant_indices,
        "day_by_id": day_by_id if hobbyist else {},
    }


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
    net = ctx["net"]
    hobbyist = ctx["hobbyist"]
    platform = ctx["platform"]
    used_names = ctx["used_names"]
    levels = ctx["levels"]
    zone_records = ctx["zone_records"]
    elements = ctx["elements"]
    paths = ctx["paths"]
    ahs_records = ctx["ahs_records"]
    path_map = ctx["path_map"]
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
    hobbyist = ctx["hobbyist"]
    platform = ctx["platform"]
    used_names = ctx["used_names"]
    levels = ctx["levels"]
    zone_records = ctx["zone_records"]
    elements = ctx["elements"]
    paths = ctx["paths"]
    ahs_records = ctx["ahs_records"]
    path_map = ctx["path_map"]
    rows = ctx.get("rows", 40)
    cols = ctx.get("cols", 40)
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
    ctx["zeros"] = "  ".join("0.000e+00" for _ in range(n_ctm))


def _append_levels_section(lines: list[str], ctx: dict[str, Any]) -> None:
    net = ctx["net"]
    hobbyist = ctx["hobbyist"]
    platform = ctx["platform"]
    used_names = ctx["used_names"]
    levels = ctx["levels"]
    zone_records = ctx["zone_records"]
    elements = ctx["elements"]
    paths = ctx["paths"]
    ahs_records = ctx["ahs_records"]
    path_map = ctx["path_map"]
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
    hobbyist = ctx["hobbyist"]
    platform = ctx["platform"]
    used_names = ctx["used_names"]
    levels = ctx["levels"]
    zone_records = ctx["zone_records"]
    elements = ctx["elements"]
    paths = ctx["paths"]
    ahs_records = ctx["ahs_records"]
    path_map = ctx["path_map"]
    rows = ctx.get("rows", 40)
    cols = ctx.get("cols", 40)
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
    cidxs = ctx.get("cidxs") or [1]
    zeros = ctx.get("zeros") or "0.000e+00"
    hobbyist = ctx["hobbyist"]
    platform = ctx["platform"]
    used_names = ctx["used_names"]
    levels = ctx["levels"]
    zone_records = ctx["zone_records"]
    elements = ctx["elements"]
    paths = ctx["paths"]
    ahs_records = ctx["ahs_records"]
    path_map = ctx["path_map"]
    rows = ctx.get("rows", 40)
    cols = ctx.get("cols", 40)
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
    hobbyist = ctx["hobbyist"]
    platform = ctx["platform"]
    used_names = ctx["used_names"]
    levels = ctx["levels"]
    zone_records = ctx["zone_records"]
    elements = ctx["elements"]
    paths = ctx["paths"]
    ahs_records = ctx["ahs_records"]
    path_map = ctx["path_map"]
    rows = ctx.get("rows", 40)
    cols = ctx.get("cols", 40)
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
    net = ctx["net"]
    species = ctx.get("species") or [{"name": "Air"}]
    cidxs = ctx.get("cidxs") or [1]
    zeros = ctx.get("zeros") or "0.000e+00"
    hobbyist = ctx["hobbyist"]
    platform = ctx["platform"]
    used_names = ctx["used_names"]
    levels = ctx["levels"]
    zone_records = ctx["zone_records"]
    elements = ctx["elements"]
    paths = ctx["paths"]
    ahs_records = ctx["ahs_records"]
    path_map = ctx["path_map"]
    rows = ctx.get("rows", 40)
    cols = ctx.get("cols", 40)
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

    # Initial concentrations (one column per contaminant)
    n_ctm = len(cidxs)
    lines.append(f"{len(zone_records)} ! initial zone concentrations:")
    header_names = " ".join(sp["name"] for sp in species[:n_ctm])
    lines.append(f"! Z#       {header_names}")
    zeros = "  ".join("0.000e+00" for _ in range(n_ctm))
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



def _append_duct_network_and_footer(lines: list[str], ctx: dict[str, Any]) -> None:
    net = ctx["net"]
    species = ctx.get("species") or [{"name": "Air"}]
    cidxs = ctx.get("cidxs") or [1]
    zeros = ctx.get("zeros") or "0.000e+00"
    hobbyist = ctx["hobbyist"]
    platform = ctx["platform"]
    used_names = ctx["used_names"]
    levels = ctx["levels"]
    zone_records = ctx["zone_records"]
    elements = ctx["elements"]
    paths = ctx["paths"]
    ahs_records = ctx["ahs_records"]
    path_map = ctx["path_map"]
    rows = ctx.get("rows", 40)
    cols = ctx.get("cols", 40)
    # Duct junctions / segments
    duct_junctions = net.get("duct_junctions") or []
    duct_segments = net.get("duct_segments") or []
    lines.append(f"{len(duct_junctions)} ! duct junctions:")
    if duct_junctions:
        lines.append(
            "! J#  f  t  z#  d#  k#  s#  c#  l#    X       Y      relHt  "
            "T0  P0  icn clr u[4] ..."
        )
        for j in duct_junctions:
            lines.append(
                f"  {j['nr']}  {j['flags']}  {j['jtype']}  {j['pzn']}  0  "
                f"0  0  0  {j['level']}  {j['x']:.3f}  {j['y']:.3f}  "
                f"{j['rel_ht']:.3f}  {j['temp']:.2f} 0  21 -1 0 0 2 0 0 none "
                f"T: 0 0 0 0 -1 0 {j['Ad']:.6g} {j['Af']:.6g} 0 "
                f"{j['Ct']:.4g} 0 0 3 3 1 1"
            )
    lines.append(_SENTINEL)

    n_jct = len(duct_junctions)
    lines.append(f"{n_jct} ! initial junction concentrations:")
    if n_jct:
        for j in duct_junctions:
            lines.append(f"   {j['nr']}  {zeros}")
    lines.append(_SENTINEL)

    lines.append(f"{len(duct_segments)} ! duct segments:")
    if duct_segments:
        lines.append("! D#  f  n#  m#  e#  f#  s#  c# dir length ...")
        for seg in duct_segments:
            lines.append(
                f"  {seg['nr']}  {seg['flags']}  {seg['pjn']}  {seg['pjm']}  "
                f"{seg['pe']}  0  0  0  1  {seg['length']:.4g} 0 0 0 -1 3 3 0 none"
            )
    lines.append(_SENTINEL)

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
    lines.append(
        f"! CRUSHER_PATH_MAP_COUNT {len(path_map)} "
        f"zones={sum(1 for z in zone_records if not z['is_phantom'])} "
        f"phantoms={sum(1 for z in zone_records if z['is_phantom'])} "
        f"hobbyist={int(bool(hobbyist))}"
    )

    return "\n".join(lines) + "\n", path_map



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

def path_map_from_prj(text: str) -> list[dict[str, Any]]:
    """Build ContamX ``path_map`` entries directly from a ContamW 3.4 ``.prj``.

    This is the Path A / Path B primary contract: authentic PRJs carry their
    own path numbering. Fiction JSON→PRJ export is bootstrap-only.
    """
    if not text.lstrip().startswith("ContamW"):
        raise ValueError(
            "Not a recognized CONTAM .prj file (missing 'ContamW' signature)"
        )
    sections = {name: body for name, body in _section_blocks(text)}

    zone_nr_to_id: dict[int, str] = {}
    phantom_nrs: set[int] = set()
    real_nrs: set[int] = set()
    for ln in sections.get("zones", []):
        if ln.strip().startswith("!"):
            continue
        toks = ln.split()
        if len(toks) < 11 or not toks[0].isdigit():
            continue
        nr = int(toks[0])
        flag = int(toks[1])
        name = toks[10]
        zone_nr_to_id[nr] = name
        if (
            flag == _ZONE_AHS
            or "(Ret)" in name
            or "(Sup)" in name
            or name.endswith("_Ret")
            or name.endswith("_Sup")
        ):
            phantom_nrs.add(nr)
        else:
            real_nrs.add(nr)

    # AHS system-path numbers (pr/ps/px) → ahs group
    ahs_path_group: dict[int, int] = {}
    for ln in sections.get("simple AHS", []):
        if ln.strip().startswith("!"):
            continue
        toks = ln.split()
        if len(toks) >= 6 and toks[0].isdigit():
            ahs_nr = int(toks[0])
            for pnr in (int(toks[3]), int(toks[4]), int(toks[5])):
                ahs_path_group[pnr] = ahs_nr

    elem_is_fan: dict[int, bool] = {}
    body = sections.get("flow elements", [])
    i = 0
    while i < len(body):
        toks = body[i].split()
        if len(toks) >= 4 and toks[0].isdigit():
            elem_is_fan[int(toks[0])] = "fan" in toks[2].lower()
            j = i + 1
            while j < len(body) and not body[j].strip():
                j += 1
            i = j + 1
            continue
        i += 1

    def _endpoint_name(nr: int) -> str:
        if nr < 0:
            return "ambient"
        return zone_nr_to_id.get(nr, f"zone_{nr}")

    path_map: list[dict[str, Any]] = []
    for ln in sections.get("flow paths", []):
        if ln.strip().startswith("!"):
            continue
        toks = ln.split()
        if len(toks) < 11 or not toks[0].isdigit():
            continue
        try:
            pnr = int(toks[0])
            flag = int(toks[1])
            from_nr = int(toks[2])
            to_nr = int(toks[3])
            elem_nr = int(toks[4])
            ahs_field = int(toks[7])
        except ValueError:
            continue

        from_name = _endpoint_name(from_nr)
        to_name = _endpoint_name(to_nr)
        from_ph = from_nr in phantom_nrs or from_nr < 0
        to_ph = to_nr in phantom_nrs or to_nr < 0
        both_real = (from_nr in real_nrs) and (to_nr in real_nrs)

        ahs_nr = ahs_field if ahs_field > 0 else ahs_path_group.get(pnr, 0)
        if flag == _PATH_AHS_OA:
            kind = "ahs_oa"
        elif flag == _PATH_AHS_EXHAUST:
            kind = "ahs_exhaust"
        elif flag == _PATH_AHS_RECIRC:
            kind = "ahs_recirc"
        elif flag == _PATH_AHS_TERMINAL:
            if from_ph and not to_ph:
                kind = "ahs_supply"
            elif to_ph and not from_ph:
                kind = "ahs_return"
            else:
                kind = "ahs_terminal"
        elif from_nr < 0 or to_nr < 0:
            kind = "envelope_leak"
        elif both_real and elem_is_fan.get(elem_nr, False):
            kind = "cross_zone"
        elif both_real:
            kind = "passageway"
        else:
            kind = "other"

        path_map.append({
            "path_nr": pnr,
            "from_zone": from_name,
            "to_zone": to_name,
            "is_hvac_ducted": kind.startswith("ahs_") or kind == "cross_zone",
            "kind": kind,
            "crusher_transfer": both_real,
            "ahs_nr": ahs_nr,
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
        m = re.match(r"^(-?\d+)\s+!\s*(.+?):\s*$", stripped)
        if m and header_done:
            count = int(m.group(1))
            name = m.group(2).strip()
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

    sections = {name: body for name, body in _section_blocks(text)}

    for dropped in (
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
    ):
        body = sections.get(dropped)
        if body is not None and any(ln.strip() for ln in body):
            warn.append(f"Dropped Contam section on simplify: {dropped}")

    # Levels
    level_names: dict[int, str] = {}
    for ln in sections.get("levels plus icon data", []):
        toks = ln.split()
        if len(toks) >= 6 and toks[0].isdigit():
            # nr refHt delHt ni u u name
            level_names[int(toks[0])] = toks[-1]

    # Zones
    zones: list[dict[str, Any]] = []
    zone_nr_to_id: dict[int, str] = {}
    phantom_nrs: set[int] = set()
    for ln in sections.get("zones", []):
        if ln.strip().startswith("!"):
            continue
        toks = ln.split()
        if len(toks) < 11:
            continue
        try:
            nr = int(toks[0])
            flag = int(toks[1])
            level = int(toks[5])
            rel_ht = float(toks[6])
            vol = float(toks[7])
            temp = float(toks[8])
            name = toks[10]
        except (ValueError, IndexError):
            continue
        _ = (rel_ht, temp)
        if flag == _ZONE_AHS or "(Ret)" in name or "(Sup)" in name or name.endswith("_Ret") or name.endswith("_Sup"):
            phantom_nrs.add(nr)
            zone_nr_to_id[nr] = name
            continue
        deck = level_names.get(level, f"level_{level}")
        zone: dict[str, Any] = {
            "id": name,
            "type": "Free",
            "traffic": "medium",
            "volume_m3": vol if vol > 0 else 100.0,
            "deck": deck,
            "display": {"x": float(nr), "y": float(level)},
        }
        if vol > 0:
            zone["ceiling_height_m"] = _DEFAULT_CEILING_HEIGHT_M
            zone["floor_area_m2"] = zone["volume_m3"] / _DEFAULT_CEILING_HEIGHT_M
            zone["elevation_m"] = (level - 1) * _DEFAULT_CEILING_HEIGHT_M
        zones.append(zone)
        zone_nr_to_id[nr] = name

    # Flow elements → type lookup
    elem_is_fan: dict[int, bool] = {}
    elem_flow_m3h: dict[int, float] = {}
    body = sections.get("flow elements", [])
    i = 0
    while i < len(body):
        toks = body[i].split()
        if len(toks) >= 4 and toks[0].isdigit():
            enr = int(toks[0])
            symbol = toks[2]
            is_fan = "fan" in symbol.lower()
            elem_is_fan[enr] = is_fan
            # next non-empty line(s) are params
            j = i + 1
            while j < len(body) and not body[j].strip():
                j += 1
            if j < len(body):
                params = body[j].split()
                if is_fan and params:
                    try:
                        m3s = float(params[0])
                        elem_flow_m3h[enr] = m3s * 3600.0
                    except ValueError:
                        elem_flow_m3h[enr] = 0.0
            i = j + 1
            continue
        i += 1

    # Simple AHS (record line + optional Crusher description with ach=)
    hvac_zones: list[dict[str, Any]] = []
    ahs_zone_set: dict[int, set[str]] = {}
    ahs_body = sections.get("simple AHS", [])
    ai = 0
    while ai < len(ahs_body):
        ln = ahs_body[ai]
        if ln.strip().startswith("!"):
            ai += 1
            continue
        toks = ln.split()
        if len(toks) >= 7 and toks[0].isdigit():
            ahs_nr = int(toks[0])
            name = toks[-1]
            ach = 6.0
            # Description is typically the next non-empty line
            if ai + 1 < len(ahs_body):
                desc = ahs_body[ai + 1].strip()
                m_ach = re.search(r"ach=([0-9.]+)", desc)
                if m_ach:
                    ach = float(m_ach.group(1))
                m_id = re.search(r"Crusher HVAC\s+(\S+)", desc)
                if m_id:
                    name = m_id.group(1)
            ahs_zone_set[ahs_nr] = set()
            hvac_zones.append({
                "id": name,
                "rooms": [],
                "ach": ach,
                "_ahs_nr": ahs_nr,
                "_ret": int(toks[1]),
                "_sup": int(toks[2]),
            })
        ai += 1

    # Flow paths
    adjacency: list[dict[str, str]] = []
    cross_zone_links: list[dict[str, Any]] = []
    room_ahs: dict[str, int] = {}

    for ln in sections.get("flow paths", []):
        if ln.strip().startswith("!"):
            continue
        toks = ln.split()
        if len(toks) < 11:
            continue
        try:
            from_nr = int(toks[2])
            to_nr = int(toks[3])
            elem_nr = int(toks[4])
            ahs_nr = int(toks[7])
        except ValueError:
            continue

        from_id = zone_nr_to_id.get(from_nr)
        to_id = zone_nr_to_id.get(to_nr)
        from_phantom = from_nr in phantom_nrs or from_nr < 0
        to_phantom = to_nr in phantom_nrs or to_nr < 0

        # Track room membership via supply/return paths
        if ahs_nr > 0:
            if not from_phantom and to_phantom and from_id:
                room_ahs[from_id] = ahs_nr
                ahs_zone_set.setdefault(ahs_nr, set()).add(from_id)
            if from_phantom and not to_phantom and to_id:
                room_ahs[to_id] = ahs_nr
                ahs_zone_set.setdefault(ahs_nr, set()).add(to_id)

        if from_phantom or to_phantom or from_nr < 0 or to_nr < 0:
            continue
        if not from_id or not to_id:
            continue

        if elem_is_fan.get(elem_nr, False):
            flow = elem_flow_m3h.get(elem_nr, 50.0)
            cross_zone_links.append({
                "from": from_id,
                "to": to_id,
                "flow_rate_m3h": round(flow, 6),
                "is_hvac_ducted": True,
                "path": f"contam_path_{from_id}_{to_id}",
            })
        else:
            adjacency.append({
                "from": from_id,
                "to": to_id,
                "type": "passageway",
            })

    # Fill HVAC rooms from supply/return path membership
    vol_by_id = {z["id"]: float(z["volume_m3"]) for z in zones}
    for hz in hvac_zones:
        ahs_nr = hz.pop("_ahs_nr")
        hz.pop("_ret", None)
        hz.pop("_sup", None)
        rooms = sorted(ahs_zone_set.get(ahs_nr, set()))
        hz["rooms"] = rooms
        _ = vol_by_id  # volumes available for future ACH inference

    # If no AHS recovered, create a single default HVAC zone
    if not hvac_zones and zones:
        hvac_zones = [{
            "id": "zone_all",
            "rooms": [z["id"] for z in zones],
            "ach": 6.0,
        }]

    platform = "imported_from_contam"
    # Try to recover platform from WPC description line
    for ln in text.splitlines()[:20]:
        if ln.startswith("Crusher platform "):
            platform = ln.split("Crusher platform ", 1)[1].strip() or platform
            break

    spatial: dict[str, Any] = {
        "platform": platform,
        "description": f"Simplified from ContamW 3.4 .prj ({platform})",
        "zones": zones,
    }
    if zones:
        spatial["graywater_zones"] = [zones[0]["id"]]

    airflow: dict[str, Any] = {
        "platform": platform,
        "description": f"Simplified from ContamW 3.4 .prj ({platform})",
        "hvac_zones": hvac_zones,
        "cross_zone_links": cross_zone_links,
        "adjacency": adjacency,
    }

    if warnings_out is None:
        for w in warn:
            warnings.warn(w, stacklevel=2)

    return spatial, airflow
