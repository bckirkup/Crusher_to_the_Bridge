"""Bracketed ContamX-surrogate transport field + scalar-rescale test.

Companion to ``_contam_divergence_measure.py``. Reproduces the numbers in
``docs/contam_engine_divergence.md`` (ledger ``CONTAM-DIVERGENCE-01``).

The surrogate spans the solver-bracket the real ContamX solve sits inside:

- ``shunt`` s in [0,1]: fraction of each non-terminal room's AHS return/supply
  legs diverted onto the branch's terminal room. ``s=1`` is the destroyer-SIM
  regime (one room carries the whole branch flow); ``s=0`` is native.
- ``terminal_pick``: ``small`` or ``large`` room per AHS — the solver's choice
  is unknowable without running ContamX, so both corners are reported.
- ``hd_vent``: head-deck zones gain an exhaust path at the PRJ-declared rate
  (ContamX behaviour) vs the native permanent trap.

Reports occupied-class integrated-concentration ratios (cx/native) per
injection site, the best single emission rescale ``r*``, and the residual
anisotropy a scalar cannot absorb.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines.py_contam_bridge import (  # noqa: E402
    PATH_TYPE_HVAC_RETURN,
    PATH_TYPE_HVAC_SUPPLY,
    ContamAirflowPath,
    ContamTransportEngine,
)
from tools._contam_divergence_measure import RHO, dose_trace, parse_prj  # noqa: E402


def build_native(plat: str) -> ContamTransportEngine:
    d = f"data/platforms/{plat}"
    return ContamTransportEngine(
        json.load(open(f"{d}/spatial_layout.json")),
        json.load(open(f"{d}/air_flow_paths.json")),
        filter_efficiency=0.50,
        natural_decay_rate=0.0,
    )


def shunt_field(
    plat: str, s: float, pick: str, hd_vent: bool
) -> ContamTransportEngine:
    d = f"data/platforms/{plat}"
    eng = build_native(plat)
    plen: dict[str, dict[str, list]] = {}
    for p in eng.airflow_paths:
        if p.path_type == PATH_TYPE_HVAC_RETURN:
            plen.setdefault(p.to_zone, {}).setdefault("ret", []).append(p)
        elif p.path_type == PATH_TYPE_HVAC_SUPPLY:
            plen.setdefault(p.from_zone, {}).setdefault("sup", []).append(p)
    for _pl, g in plen.items():
        rooms = [p.from_zone for p in g.get("ret", [])]
        if len(rooms) < 2:
            continue
        vols = {z: eng.zone_nodes[z].volume_m3 for z in rooms}
        t = (
            min(rooms, key=lambda z: vols[z])
            if pick == "small"
            else max(rooms, key=lambda z: vols[z])
        )
        for kind in ("ret", "sup"):
            tot = sum(
                p.flow_rate_m3h
                for p in g.get(kind, [])
                if (p.from_zone if kind == "ret" else p.to_zone) != t
            )
            for p in g.get(kind, []):
                room = p.from_zone if kind == "ret" else p.to_zone
                p.flow_rate_m3h *= (1.0 - s) if room != t else 1.0
            for p in g.get(kind, []):
                room = p.from_zone if kind == "ret" else p.to_zone
                if room == t:
                    p.flow_rate_m3h += s * tot
    if hd_vent:
        zones, _elems, paths, _ahs = parse_prj(Path(f"{d}/contam/platform.prj"))
        zname = {nr: z["name"] for nr, z in zones.items()}
        ex: dict[str, float] = {}
        for _nr, p in paths.items():
            if p["fahs"] > 0 and p["sched"] == 2:
                tgt = zname.get(p["m"], "")
                if tgt.startswith("HD_"):
                    ex[tgt] = ex.get(tgt, 0) + p["fahs"] / RHO * 3600
        exts = [
            z
            for z in eng.zone_nodes
            if "deck" in z.lower() or "pool" in z.lower() or "outdoor" in z.lower()
        ]
        ext = exts[0] if exts else None
        for z, f in ex.items():
            if z in eng.zone_nodes and ext:
                eng.airflow_paths.append(
                    ContamAirflowPath(
                        path_id=f"hdvent_{z}",
                        from_zone=z,
                        to_zone=ext,
                        flow_rate_m3h=f,
                        path_type="cross_zone",
                        is_hvac_ducted=False,
                    )
                )
    return eng


def zclass(z: str) -> str:
    if z.startswith(("PC_", "CC_")):
        return "cabin"
    if z.startswith("HD_"):
        return "head"
    if "Dining" in z or "Buffet" in z or z in (
        "CrewMess",
        "Specialty",
        "CasualDining",
        "LidoBuffet",
    ):
        return "dining"
    if z in ("MainGalley", "Laundry", "Stores", "Engine_Room", "Galley"):
        return "service"
    if z.startswith("Med") or z in ("IsolRoom", "IsolWard"):
        return "medical"
    if z in ("PoolDeck", "Deck", "SunDeck"):
        return "exterior"
    return "public"


OCC = ["cabin", "dining", "public", "service", "medical"]
SITES = {
    "expedition_cruise_450": [
        "PC_D4_P_F",
        "MainDining",
        "MainGalley",
        "TheaterLng",
    ],
    "classic_cruise_1900": [
        "PC_D4_P_F",
        "MainDining_L",
        "MainGalley",
        "Promenade",
    ],
    "spirit_cruise_3000": ["CC_D1_A", "LidoBuffet", "MainGalley", "AftPool"],
}


def main() -> None:
    for plat in SITES:
        nat = build_native(plat)
        variants = {
            "cx_s05_small": shunt_field(plat, 0.5, "small", True),
            "cx_s10_small": shunt_field(plat, 1.0, "small", True),
            "cx_s10_large": shunt_field(plat, 1.0, "large", True),
        }
        print("#" * 12, plat)
        for site in SITES[plat]:
            _mn, cn, _rn, _vols = dose_trace(nat, site, 24)
            nat_d = {
                c: sum(cn[z] for z in cn if zclass(z) == c) for c in OCC
            }
            print(
                f" inject={site}  native occ-dose share: "
                + ", ".join(
                    f"{c}={nat_d[c] / max(sum(nat_d.values()), 1e-12):.0%}"
                    for c in OCC
                )
            )
            for vn, eng in variants.items():
                mc, cc, _rc, _ = dose_trace(eng, site, 24)
                cx_d = {
                    c: sum(cc[z] for z in cc if zclass(z) == c) for c in OCC
                }
                ratios = {
                    c: (cx_d[c] / nat_d[c] if nat_d[c] > 1e-6 else np.nan)
                    for c in OCC
                }
                rr = [v for v in ratios.values() if np.isfinite(v)]
                rstar = (
                    float(np.exp(np.mean(np.log(rr)))) if rr else float("nan")
                )
                resid = (max(rr) / min(rr)) if rr else float("nan")
                print(
                    f"  {vn:13s} ret={sum(mc.values()):.3f} "
                    + " ".join(
                        f"{c}={ratios.get(c, float('nan')):.2f}" for c in OCC
                    )
                    + f" | r*={rstar:.2f} aniso={resid:.1f}x"
                )


if __name__ == "__main__":
    main()
