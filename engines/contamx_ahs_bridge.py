"""
engines.contamx_ahs_bridge
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Collapse Contam simple-AHS path flows (Ret/Sup phantoms) into effective
room↔room recirculation edges for Crusher pathogen mass balance.

ContamX is the detailed airflow model; Crusher only needs real-zone
exchanges. Native ``ContamTransportEngine`` builds an ACH digraph; this
module recovers the same consumer shape from ContamX SIM flows + path_map.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from engines.py_contam_bridge import ContamAirflowPath

_FLOW_EPS = 1e-9


def synthesize_ahs_recirculation_paths(
    path_map_entries: list[dict[str, Any]],
    path_flows_m3h: dict[int, float],
    known_zones: set[str],
) -> list[ContamAirflowPath]:
    """Synthesize ducted room↔room paths from Contam AHS supply/return/recirc.

    For each AHS group with ≥2 real rooms::

        Q_ij = R_i · (Rec / ΣR) · (S_j / ΣS)     (i ≠ j)

    where ``R_i`` is return flow room→Ret, ``S_j`` is supply Sup→room, and
    ``Rec`` is the recirculation path Ret→Sup (all ContamX volumetric flows).

    Single-room AHUs yield no recirculation edges (matches native).
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
        if flow < _FLOW_EPS and kind != "ahs_recirc":
            # Still record zero terminals so grouping knows membership;
            # recirc may be the only signal when Contam reports tiny flows.
            pass

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
        if len(rooms) < 2:
            continue

        sum_r = sum(returns.values())
        sum_s = sum(supplies.values())
        if recirc < _FLOW_EPS or sum_r < _FLOW_EPS or sum_s < _FLOW_EPS:
            # Contam may not populate recirc path flow when fo≈1; fall back to
            # design-like mixing from terminal magnitudes: Rec ≈ min(ΣR, ΣS).
            recirc = min(sum_r, sum_s)
        if recirc < _FLOW_EPS:
            continue

        for room_from, r_i in returns.items():
            if r_i < _FLOW_EPS:
                continue
            for room_to, s_j in supplies.items():
                if room_from == room_to or s_j < _FLOW_EPS:
                    continue
                pair_flow = r_i * (recirc / sum_r) * (s_j / sum_s)
                if pair_flow < _FLOW_EPS:
                    continue
                paths.append(ContamAirflowPath(
                    path_id=f"contamx_ahs{ahs_nr}_{room_from}_{room_to}",
                    from_zone=room_from,
                    to_zone=room_to,
                    flow_rate_m3h=pair_flow,
                    path_type="hvac_recirculation",
                    is_hvac_ducted=True,
                ))
    return paths
