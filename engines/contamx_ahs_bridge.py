"""
engines.contamx_ahs_bridge
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Collapse Contam simple-AHS path flows (Ret/Sup phantoms) into Crusher
star-topology HVAC edges (room → plenum → room).

ContamX is the detailed airflow model; Crusher pathogen mass balance uses
virtual plenums matching Contam AHS mixing, not an N×N room digraph.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from engines.py_contam_bridge import (
    PATH_TYPE_HVAC_RETURN,
    PATH_TYPE_HVAC_SUPPLY,
    PLENUM_PREFIX,
    ContamAirflowPath,
)

_FLOW_EPS = 1e-9
# Contam fiction export / OAFracW default when Rec Flow0 is absent.
_DEFAULT_OA_FRACTION = 0.2


def ahs_plenum_id(ahs_nr: int) -> str:
    """Virtual plenum zone id for Contam AHS group ``ahs_nr``."""
    return f"{PLENUM_PREFIX}ahs{ahs_nr}"


def synthesize_ahs_recirculation_paths(
    path_map_entries: list[dict[str, Any]],
    path_flows_m3h: dict[int, float],
    known_zones: set[str],
    *,
    oa_fraction: float = _DEFAULT_OA_FRACTION,
) -> list[ContamAirflowPath]:
    """Synthesize star HVAC paths from Contam AHS supply/return/recirc.

    For each AHS group with ≥1 real room::

        room_i → plenum   at R_i          (return, unfiltered)
        plenum → room_j   at S_j·(Rec/ΣS) (supply, filtered)

    where ``R_i`` is return flow room→Ret, ``S_j`` is supply Sup→room, and
    ``Rec`` is the recirculation path Ret→Sup (all ContamX volumetric flows).

    When ContamX reports Rec≈0 (common for simple-AHS SIM frames that only
    expose terminal flows), fall back to PRJ outdoor-air intent::

        Rec ≈ (1 − oa_fraction) · min(ΣR, ΣS)

    Single-room AHUs yield return+supply legs (OA + filter removal).
    """
    by_ahs: dict[int, dict[str, Any]] = defaultdict(
        lambda: {"returns": {}, "supplies": {}, "recirc": 0.0}
    )

    for entry in path_map_entries:
        ahs_nr = int(entry.get("ahs_nr") or 0)
        if ahs_nr <= 0:
            continue
        kind = str(entry.get("kind", ""))
        pnr = int(entry["path_nr"])
        flow = abs(float(path_flows_m3h.get(pnr, 0.0)))

        group = by_ahs[ahs_nr]
        if kind == "ahs_return":
            room = entry["from_zone"]
            if room in known_zones:
                group["returns"][room] = group["returns"].get(room, 0.0) + flow
        elif kind == "ahs_supply":
            room = entry["to_zone"]
            if room in known_zones:
                group["supplies"][room] = group["supplies"].get(room, 0.0) + flow
        elif kind == "ahs_recirc":
            group["recirc"] += flow

    paths: list[ContamAirflowPath] = []
    for ahs_nr, group in sorted(by_ahs.items()):
        returns: dict[str, float] = group["returns"]
        supplies: dict[str, float] = group["supplies"]
        recirc = float(group["recirc"])
        rooms = sorted(set(returns) | set(supplies))
        if not rooms:
            continue

        sum_r = sum(returns.values())
        sum_s = sum(supplies.values())
        if sum_r < _FLOW_EPS or sum_s < _FLOW_EPS:
            continue
        if recirc < _FLOW_EPS:
            # ContamX often reports Rec/OA/exhaust Flow0 as 0 for simple AHS
            # while terminals carry the scheduled duty flow. Recover PRJ
            # recirculation: Rec = (1 − oa) · min(ΣR, ΣS).
            oa = min(max(float(oa_fraction), 0.0), 1.0)
            recirc = (1.0 - oa) * min(sum_r, sum_s)
        if recirc < _FLOW_EPS:
            continue

        plenum_id = ahs_plenum_id(ahs_nr)
        for room, r_i in returns.items():
            if r_i < _FLOW_EPS:
                continue
            paths.append(ContamAirflowPath(
                path_id=f"contamx_ahs{ahs_nr}_ret_{room}",
                from_zone=room,
                to_zone=plenum_id,
                flow_rate_m3h=r_i,
                path_type=PATH_TYPE_HVAC_RETURN,
                is_hvac_ducted=False,
            ))

        for room, s_j in supplies.items():
            if s_j < _FLOW_EPS:
                continue
            # Pathogen-carrying supply = share of recirculated air to room.
            supply_flow = s_j * (recirc / sum_s)
            if supply_flow < _FLOW_EPS:
                continue
            paths.append(ContamAirflowPath(
                path_id=f"contamx_ahs{ahs_nr}_sup_{room}",
                from_zone=plenum_id,
                to_zone=room,
                flow_rate_m3h=supply_flow,
                path_type=PATH_TYPE_HVAC_SUPPLY,
                is_hvac_ducted=True,
            ))
    return paths
