"""
engines.contamx_ahs_bridge
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Collapse Contam simple-AHS path flows (Ret/Sup phantoms) into Crusher
star-topology HVAC edges (room → plenum → room).

ContamX is the detailed airflow model; Crusher pathogen mass balance uses
virtual plenums matching Contam AHS mixing, not an N×N room digraph.
"""

from __future__ import annotations

import warnings
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
_RECIRC_DIVERGENCE_RTOL = 1e-3


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
    expose terminal flows), fall back to declared PRJ outdoor-air intent.
    Terminal entries may carry ``declared_oa_fraction``; the fallback is
    the supply-weighted mean of those per-room values, or the scalar
    ``oa_fraction`` when no entry declares one::

        Rec ≈ (1 − oa_effective) · min(ΣR, ΣS)

    When ContamX reports a nonzero Rec that disagrees with declared
    per-entry OA intent, the measured Rec still supersedes it but a
    ``UserWarning`` surfaces the divergence. Scalar-fallback path maps
    keep the previous silent measured-Rec behaviour.

    Single-room AHUs yield return+supply legs (OA + filter removal).
    """
    by_ahs = _group_ahs_terminal_flows(path_map_entries, path_flows_m3h, known_zones)

    paths: list[ContamAirflowPath] = []
    for ahs_nr, group in sorted(by_ahs.items()):
        paths.extend(_ahs_group_star_paths(ahs_nr, group, oa_fraction))
    return paths


def _group_ahs_terminal_flows(
    path_map_entries: list[dict[str, Any]],
    path_flows_m3h: dict[int, float],
    known_zones: set[str],
) -> dict[int, dict[str, Any]]:
    """Bucket AHS return/supply/recirc flows by AHS group number."""
    by_ahs: dict[int, dict[str, Any]] = defaultdict(
        lambda: {
            "returns": {}, "supplies": {}, "recirc": 0.0, "oa_by_room": {},
        }
    )
    for entry in path_map_entries:
        _accumulate_ahs_entry(by_ahs, entry, path_flows_m3h, known_zones)
    return by_ahs


def _accumulate_ahs_entry(
    by_ahs: dict[int, dict[str, Any]],
    entry: dict[str, Any],
    path_flows_m3h: dict[int, float],
    known_zones: set[str],
) -> None:
    """Add one path-map entry's flow and declared OA to its AHS group."""
    ahs_nr = int(entry.get("ahs_nr") or 0)
    if ahs_nr <= 0:
        return
    kind = str(entry.get("kind", ""))
    pnr = int(entry["path_nr"])
    flow = abs(float(path_flows_m3h.get(pnr, 0.0)))

    group = by_ahs[ahs_nr]
    _record_declared_oa(group, entry, kind, known_zones)
    if kind == "ahs_return":
        _add_room_flow(group["returns"], entry["from_zone"], flow, known_zones)
    elif kind == "ahs_supply":
        _add_room_flow(group["supplies"], entry["to_zone"], flow, known_zones)
    elif kind == "ahs_recirc":
        group["recirc"] += flow


def _record_declared_oa(
    group: dict[str, Any],
    entry: dict[str, Any],
    kind: str,
    known_zones: set[str],
) -> None:
    """Store a terminal entry's declared OA fraction for its room."""
    declared_oa = entry.get("declared_oa_fraction")
    if declared_oa is None or kind not in {"ahs_return", "ahs_supply"}:
        return
    room = entry["from_zone"] if kind == "ahs_return" else entry["to_zone"]
    if room in known_zones:
        group["oa_by_room"][room] = float(declared_oa)


def _add_room_flow(
    flows: dict[str, float], room: str, flow: float, known_zones: set[str],
) -> None:
    """Accumulate ``flow`` for ``room`` when the room is known."""
    if room in known_zones:
        flows[room] = flows.get(room, 0.0) + flow


def _ahs_group_star_paths(
    ahs_nr: int,
    group: dict[str, Any],
    oa_fraction: float,
) -> list[ContamAirflowPath]:
    """Star return/supply legs for one AHS group (empty when not viable)."""
    returns: dict[str, float] = group["returns"]
    supplies: dict[str, float] = group["supplies"]
    recirc = float(group["recirc"])
    rooms = sorted(set(returns) | set(supplies))
    if not rooms:
        return []

    sum_r = sum(returns.values())
    sum_s = sum(supplies.values())
    if sum_r < _FLOW_EPS and sum_s < _FLOW_EPS:
        return []

    plenum_id = ahs_plenum_id(ahs_nr)
    # Exhaust-only groups (commissioned-mode head-deck AHUs: supply 0,
    # return ach·V) still emit room → plenum legs — the room drains
    # overboard even though no recirculating supply exists.
    paths = _ahs_return_paths(ahs_nr, plenum_id, returns)
    if sum_s < _FLOW_EPS:
        return paths
    declared_oa = _effective_oa_fraction(group, supplies, oa_fraction)
    declared_recirc = (1.0 - declared_oa) * min(sum_r, sum_s)
    if recirc < _FLOW_EPS:
        # ContamX often reports Rec/OA/exhaust Flow0 as 0 for simple AHS
        # while terminals carry the scheduled duty flow. Recover PRJ
        # recirculation from declared outdoor-air intent.
        recirc = declared_recirc
    elif group.get("oa_by_room") and _recirc_diverges(recirc, declared_recirc):
        warnings.warn(
            f"AHS {ahs_nr} recirc {recirc:.6g} m3/h diverges from "
            f"declared-OA intent {declared_recirc:.6g} m3/h; "
            "using measured ContamX recirc",
            UserWarning,
            stacklevel=3,
        )
    if recirc >= _FLOW_EPS:
        paths.extend(
            _ahs_supply_paths(ahs_nr, plenum_id, supplies, recirc, sum_s)
        )
    return paths


def _clamp_oa(value: float) -> float:
    return min(max(float(value), 0.0), 1.0)


def _effective_oa_fraction(
    group: dict[str, Any], supplies: dict[str, float], fallback: float,
) -> float:
    """Supply-weighted declared OA for one AHS group, else the scalar."""
    fallback_oa = _clamp_oa(fallback)
    oa_by_room = group.get("oa_by_room") or {}
    if not oa_by_room:
        return fallback_oa
    weighted = 0.0
    total_supply = 0.0
    for room, supply in supplies.items():
        if supply < _FLOW_EPS:
            continue
        declared = oa_by_room.get(room)
        oa = _clamp_oa(declared) if declared is not None else fallback_oa
        weighted += oa * supply
        total_supply += supply
    if total_supply < _FLOW_EPS:
        return fallback_oa
    return _clamp_oa(weighted / total_supply)


def _recirc_diverges(measured: float, declared: float) -> bool:
    scale = max(abs(measured), abs(declared))
    return abs(measured - declared) > max(
        _FLOW_EPS, _RECIRC_DIVERGENCE_RTOL * scale,
    )


def _ahs_return_paths(
    ahs_nr: int,
    plenum_id: str,
    returns: dict[str, float],
) -> list[ContamAirflowPath]:
    """room → plenum legs at each room's return flow (unfiltered)."""
    return [
        ContamAirflowPath(
            path_id=f"contamx_ahs{ahs_nr}_ret_{room}",
            from_zone=room,
            to_zone=plenum_id,
            flow_rate_m3h=r_i,
            path_type=PATH_TYPE_HVAC_RETURN,
            is_hvac_ducted=False,
        )
        for room, r_i in returns.items()
        if r_i >= _FLOW_EPS
    ]


def _ahs_supply_paths(
    ahs_nr: int,
    plenum_id: str,
    supplies: dict[str, float],
    recirc: float,
    sum_s: float,
) -> list[ContamAirflowPath]:
    """plenum → room legs carrying the room's share of recirculated air."""
    paths: list[ContamAirflowPath] = []
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
