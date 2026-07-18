"""
contamw34_prj.py – ContamW 3.4 project export / simplify
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Emits ContamW **3.4**-grammar ``.prj`` text ContamX can parse, and
simplifies authentic ContamW 3.4 projects back into Crusher platform JSON.

Prescribed-flow approximation (fiction-ship plausible):
  - ``plr_orfc`` openings for adjacency
  - ``fan_cvf`` constant-volume fans for cross-zone links
  - Simple AHS: Ret/Sup phantoms + system paths (recirc/OA/exhaust) and
    per-room supply/return terminals with design ``Fahs`` (kg/s), ``e#=0``

ContamW name fields are capped at **15 characters** (ContamX buffer).

Native Crusher mass-balance is unchanged; ContamX only supplies the airflow
field when selected. Blueprint→authentic Contam authoring is out of scope.
"""

from __future__ import annotations

import re
import warnings
from typing import Any

from engines.py_contam_bridge import derive_volume_m3

PRJ_SIGNATURE_34 = "ContamW 3.4.0.0 0"
_SENTINEL = "-999"
_DEFAULT_CEILING_HEIGHT_M = 3.0
_DEFAULT_ZONE_TEMP_K = 293.15
_DEFAULT_AIR_DENSITY = 1.2041
# ContamW / ContamX symbolic names (zones, AHS, levels, elements) ≤ 15 chars.
_CONTAM_NAME_MAX = 15

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

# Minimal orifice coefficients (plausible small opening)
_ORIFICE_PARAMS = "2.70811e-05 0.00848528 0.5 0.01 0.112838 0.6 30 0 0"


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
) -> dict[str, Any]:
    """Shared builder for ContamW 3.4 zones, elements, paths, and AHS."""
    zones = list(spatial_layout.get("zones", []))
    hvac_zones = list(air_flow_paths.get("hvac_zones", []))
    cross_links = list(air_flow_paths.get("cross_zone_links", []))
    adjacency = list(air_flow_paths.get("adjacency", []))

    levels = _build_levels(zones)
    level_index = {lvl["name"]: i + 1 for i, lvl in enumerate(levels)}
    deck_order = {lvl["name"]: i for i, lvl in enumerate(levels)}

    used_contam_names: set[str] = set()
    zone_name_to_nr: dict[str, int] = {}
    zone_records: list[dict[str, Any]] = []
    for i, zone in enumerate(zones, start=1):
        name = _unique_contam_name(zone["id"], used_contam_names)
        geo = _fill_zone_geometry(zone, deck_order)
        deck = str(zone.get("deck", "main"))
        display = zone.get("display", {}) or {}
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
            "temp": _DEFAULT_ZONE_TEMP_K,
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

    # Flow elements: 1 = orifice, then one fan per distinct m3/s rate we need
    elements: list[dict[str, Any]] = [
        {
            "nr": 1,
            "type": _ELEM_ORIFICE,
            "symbol": "plr_orfc",
            "name": "Opening",
            "params": _ORIFICE_PARAMS,
        },
    ]
    fan_elem_by_m3s: dict[float, int] = {}

    def _fan_elem(flow_m3h: float) -> int:
        m3s = max(flow_m3h, 0.0) / 3600.0
        # Quantize to avoid float-key explosion
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
        level: int = 1,
        flag: int = 0,
        fahs: float = 0.0,
        wazm: float = -1.0,
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
        })
        path_map.append({
            "path_nr": pnr,
            "from_zone": from_name,
            "to_zone": to_name,
            "is_hvac_ducted": is_hvac_ducted,
            "kind": kind,
            "crusher_transfer": crusher_transfer,
        })
        return pnr

    # 1) Adjacency openings (orifice)
    for adj in adjacency:
        a, b = adj["from"], adj["to"]
        if a not in zone_name_to_nr or b not in zone_name_to_nr:
            continue
        _add_path(
            zone_name_to_nr[a], zone_name_to_nr[b], 1,
            from_name=a, to_name=b,
            kind=adj.get("type", "passageway"),
            is_hvac_ducted=False,
            crusher_transfer=True,
            flag=0,
        )

    # 2) Cross-zone links as fans between representative rooms
    hvac_by_id = {h["id"]: h for h in hvac_info}

    def _resolve_endpoint(token: str) -> str | None:
        if token in zone_name_to_nr and token in {z["orig_id"] for z in zone_records if not z["is_phantom"]}:
            return token
        if token in hvac_by_id:
            return hvac_by_id[token]["rooms"][0]
        # Might already be a room id
        if token in zone_name_to_nr:
            return token
        return None

    for link in cross_links:
        src = _resolve_endpoint(link["from"])
        dst = _resolve_endpoint(link["to"])
        if src is None or dst is None:
            continue
        flow = float(link.get("flow_rate_m3h", 50.0))
        elem = _fan_elem(flow)
        _add_path(
            zone_name_to_nr[src], zone_name_to_nr[dst], elem,
            from_name=src, to_name=dst,
            kind=link.get("path", "cross_zone"),
            is_hvac_ducted=bool(link.get("is_hvac_ducted", False)),
            crusher_transfer=True,
            flag=0,
        )

    # 3) Per-AHS: Contam simple-AHS semantics (match authentic ContamW 3.4)
    # System paths (recirc / OA / exhaust): a#=0, e#=0
    # Zone terminals (supply / return): a#=AHS, e#=0, Fahs=design kg/s
    # AHS record pr/ps/px = recirc / OA / exhaust path numbers
    ahs_records: list[dict[str, Any]] = []
    for ahs_i, info in enumerate(hvac_info, start=1):
        rooms = info["rooms"]
        ach = info["ach"]
        total_vol = sum(
            next(z["volume"] for z in zone_records if z["orig_id"] == r)
            for r in rooms
        )
        total_flow = ach * total_vol  # m³/h
        # Split: 20% OA, 80% recirculation of total ACH flow (bookkeeping;
        # Contam balances system paths from terminal Fahs + OA schedule).
        oa_flow = 0.2 * total_flow
        recirc_flow = 0.8 * total_flow
        per_room_supply = total_flow / max(len(rooms), 1)
        per_room_fahs = _flow_m3h_to_fahs_kg_s(per_room_supply)
        recirc_fahs = _flow_m3h_to_fahs_kg_s(recirc_flow)

        # OA ambient -> supply (from_nr = -1)
        oa_path = _add_path(
            -1, info["sup_nr"], 0,
            from_name="ambient", to_name=info["sup_name"],
            kind="ahs_oa", is_hvac_ducted=True, crusher_transfer=False,
            ahs_nr=0, flag=_PATH_AHS_OA, fahs=0.0, wazm=-1.0,
        )
        # Exhaust return -> ambient
        ex_path = _add_path(
            info["ret_nr"], -1, 0,
            from_name=info["ret_name"], to_name="ambient",
            kind="ahs_exhaust", is_hvac_ducted=True, crusher_transfer=False,
            ahs_nr=0, flag=_PATH_AHS_EXHAUST, fahs=0.0, wazm=-1.0,
        )
        # Recirc return -> supply
        recirc_path = _add_path(
            info["ret_nr"], info["sup_nr"], 0,
            from_name=info["ret_name"], to_name=info["sup_name"],
            kind="ahs_recirc", is_hvac_ducted=True, crusher_transfer=False,
            ahs_nr=0, flag=_PATH_AHS_RECIRC, fahs=recirc_fahs, wazm=-1.0,
        )

        for room in rooms:
            rnr = zone_name_to_nr[room]
            # Supply: Sup -> room
            _add_path(
                info["sup_nr"], rnr, 0,
                from_name=info["sup_name"], to_name=room,
                kind="ahs_supply", is_hvac_ducted=True, crusher_transfer=False,
                ahs_nr=ahs_i, flag=_PATH_AHS_TERMINAL,
                fahs=per_room_fahs, wazm=0.0,
            )
            # Return: room -> Ret
            _add_path(
                rnr, info["ret_nr"], 0,
                from_name=room, to_name=info["ret_name"],
                kind="ahs_return", is_hvac_ducted=True, crusher_transfer=False,
                ahs_nr=ahs_i, flag=_PATH_AHS_TERMINAL,
                fahs=per_room_fahs, wazm=0.0,
            )

        ahs_records.append({
            "nr": ahs_i,
            "ret_nr": info["ret_nr"],
            "sup_nr": info["sup_nr"],
            # ContamW header: pr# = recirculation, ps# = OA, px# = exhaust
            "pr": recirc_path,
            "ps": oa_path,
            "px": ex_path,
            "name": info["ahs_name"],
            "hvac_id": info["id"],
            "rooms": rooms,
            "ach": ach,
            "total_vol": total_vol,
            "oa_flow_m3h": oa_flow,
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
    }


def export_contamw34(
    spatial_layout: dict[str, Any],
    air_flow_paths: dict[str, Any],
) -> tuple[str, list[dict[str, Any]]]:
    """Serialize platform JSON to ContamW 3.4 ``.prj`` text + path_map."""
    net = _assemble_network(spatial_layout, air_flow_paths)
    platform = _sanitize_name(net["platform"])[:_CONTAM_NAME_MAX]
    levels = net["levels"]
    zone_records = net["zone_records"]
    elements = net["elements"]
    paths = net["paths"]
    ahs_records = net["ahs_records"]
    path_map = net["path_map"]
    used_names: set[str] = set(net.get("used_contam_names") or [])

    n_zones = len(zone_records)
    # SketchPad grid sized generously for icon placement
    rows = max(40, n_zones + 20)
    cols = max(40, n_zones + 20)

    lines: list[str] = []
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
    lines.append(f"Crusher platform {platform}")
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
    lines.append("   0    0.75    20     1      0      0      0")
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

    # Contaminants / species (inert tracer — Crusher owns pathogen mass)
    lines.append("1 ! contaminants:")
    lines.append("   1")
    lines.append("1 ! species:")
    lines.append(
        "! # s t   molwt    mdiam       edens       decay         Dm         "
        "CCdef        Cp          Kuv     u[5]      name"
    )
    lines.append(
        "  1 1 0  28.9600  0.0000e+00  0.0000e+00  0.0000e+00  2.0000e-05  "
        "0.0000e+00  1.0000e+03  0.0000e+00 0 0 0 0 0 Air"
    )
    lines.append("default")
    lines.append(_SENTINEL)

    # Levels (+ empty icon data)
    lines.append(f"{len(levels)} ! levels plus icon data:")
    lines.append("! #  refHt   delHt  ni  u  name")
    for i, lvl in enumerate(levels, start=1):
        lvl_name = _unique_contam_name(lvl["name"], used_names)
        lines.append(
            f"  {i} {lvl['refht']:.3f} {lvl['delht']:.3f} 0 0 0 {lvl_name}"
        )
    lines.append(_SENTINEL)

    # Empty / minimal schedule stubs
    lines.append("0 ! day-schedules:")
    lines.append(_SENTINEL)
    lines.append("0 ! week-schedules:")
    lines.append(_SENTINEL)
    lines.append("0 ! wind pressure profiles:")
    lines.append(_SENTINEL)
    lines.append("0 ! kinetic reactions:")
    lines.append(_SENTINEL)
    lines.append("0 ! filter elements:")
    lines.append(_SENTINEL)
    lines.append("0 ! filters:")
    lines.append(_SENTINEL)
    lines.append("0 ! source/sink elements:")
    lines.append(_SENTINEL)

    # Flow elements
    lines.append(f"{len(elements)} ! flow elements:")
    for el in elements:
        el_name = _unique_contam_name(el["name"], used_names)
        lines.append(f"{el['nr']} {el['type']} {el['symbol']} {el_name}")
        lines.append("")
        lines.append(f" {el['params']}")
    lines.append(_SENTINEL)

    lines.append("0 ! duct elements:")
    lines.append(_SENTINEL)
    lines.append("0 ! control super elements:")
    lines.append(_SENTINEL)
    lines.append("0 ! control nodes:")
    lines.append(_SENTINEL)

    # Simple AHS — pr/ps/px are system paths (recirc / OA / exhaust)
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

    # Initial concentrations
    lines.append(f"{len(zone_records)} ! initial zone concentrations:")
    lines.append("! Z#       Air")
    for z in zone_records:
        lines.append(f"   {z['nr']}  0.000e+00")
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
            f"{p['elem_nr']}   0   0   {p['ahs_nr']}   0   0   {p['level']}   "
            f"0.000   0.000   0.000 1 0 0 {wazm_s} {p['fahs']:.8g} 0 0   0  1 "
            f"-1 0 0 0 0 0 0"
        )
    lines.append(_SENTINEL)

    lines.append("0 ! duct junctions:")
    lines.append(_SENTINEL)
    lines.append("0 ! initial junction concentrations:")
    lines.append(_SENTINEL)
    lines.append("0 ! duct segments:")
    lines.append(_SENTINEL)
    lines.append("0 ! source/sinks:")
    lines.append(_SENTINEL)
    lines.append("0 ! occupancy schedules:")
    lines.append(_SENTINEL)
    lines.append("0 ! exposures:")
    lines.append(_SENTINEL)
    lines.append("0 ! annotations:")
    lines.append(_SENTINEL)
    lines.append("* end project file.")
    lines.append("")

    # Crusher metadata comment trailer (ignored by ContamX if after end)
    # Keep path_map in sidecar JSON; embed summary count here.
    lines.append(
        f"! CRUSHER_PATH_MAP_COUNT {len(path_map)} "
        f"zones={sum(1 for z in zone_records if not z['is_phantom'])} "
        f"phantoms={sum(1 for z in zone_records if z['is_phantom'])}"
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
