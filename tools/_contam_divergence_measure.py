"""Ad-hoc measurement: native vs ContamX airflow-field deposition divergence.

ContamX (Windows-only) is unavailable here, so its steady-state flow field is
reconstructed analytically from platform.prj: AHS terminals + fan_cvf paths
are prescribed (Fahs/fan rate); every plr_orfc path solves zone-pressure
balance Q = C*|dP|^0.5. The ContamX field is then fed through the REAL
ContamXTransportEngine (path_flows_m3h override) and the native field through
ContamTransportEngine — identical mass-balance propagator, so any divergence
is the airflow field alone.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import fsolve

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from engines.contamx_transport import ContamXTransportEngine  # noqa: E402
from engines.py_contam_bridge import ContamTransportEngine  # noqa: E402

RHO = 1.2041


def _parse_zone_table(lines: list[str], start: int) -> dict[int, dict]:
    zones: dict[int, dict] = {}
    for l in lines[start + 2:]:
        l = l.strip()
        if l.startswith("-999") or not l:
            break
        if l.startswith("!"):
            continue
        t = l.split()
        if len(t) >= 11 and t[0].lstrip("-").isdigit():
            zones[int(t[0])] = {"name": t[10], "vol": float(t[7])}
    return zones


def _coefficient_nums(lines: list[str], header_i: int) -> list[float]:
    nums: list[float] = []
    for j in (header_i + 1, header_i + 2, header_i + 3):
        if j < len(lines) and lines[j].strip():
            for x in lines[j].split():
                try:
                    nums.append(float(x))
                except ValueError:
                    break
            break
    return nums


def _parse_flow_elements(lines: list[str]) -> dict[int, dict]:
    elems: dict[int, dict] = {}
    ei = next(i for i, l in enumerate(lines) if "! flow elements:" in l)
    i = ei + 1
    while i < len(lines):
        l = lines[i].strip()
        if l.startswith("-999"):
            break
        m = re.match(r"^(\d+)\s+(\d+)\s+(\S+)\s+(\S+)", l)
        if m and int(m.group(1)) > 0:
            elems[int(m.group(1))] = {
                "type": m.group(3),
                "nums": _coefficient_nums(lines, i),
            }
        i += 1
    return elems


def _parse_simple_ahs(lines: list[str]) -> dict[int, dict]:
    ahs_recs: dict[int, dict] = {}
    for i, l in enumerate(lines):
        if "simple AHS" not in l:
            continue
        j = i + 2
        while j < len(lines):
            t = lines[j].split()
            if not t or t[0].startswith("-999"):
                break
            if t[0].lstrip("-").isdigit() and len(t) >= 7:
                ahs_recs[int(t[0])] = {"zr": int(t[1]), "zs": int(t[2])}
            j += 1
        break
    return ahs_recs


def _parse_flow_paths(lines: list[str]) -> dict[int, dict]:
    paths: dict[int, dict] = {}
    pi = next(i for i, l in enumerate(lines) if "! flow paths:" in l)
    for l in lines[pi + 2:]:
        l = l.strip()
        if l.startswith("-999") or not l:
            break
        if l.startswith("!"):
            continue
        t = l.split()
        if len(t) > 22 and t[0].lstrip("-").isdigit():
            paths[int(t[0])] = {
                "n": int(t[2]), "m": int(t[3]), "e": int(t[4]),
                "fahs": float(t[18]), "mult": float(t[14]), "dir": int(t[22]),
                "sched": int(t[8]),
            }
    return paths


def parse_prj(prj_path):
    lines = prj_path.read_text().splitlines()
    zi = next(i for i, l in enumerate(lines) if re.search(r"! zones:", l))
    zones = _parse_zone_table(lines, zi)
    elems = _parse_flow_elements(lines)
    ahs_recs = _parse_simple_ahs(lines)
    paths = _parse_flow_paths(lines)
    return zones, elems, paths, ahs_recs


# Midnight snapshot (sim window Jan01 00:00-01:00): HvacDuty=0.5,
# DoorTraff(sched4)=0.08, HatchOcc(sched5)=0.10, ShaftOpen(sched6)=0.85.
SIM_SCHED_MULT = {4: 0.08, 5: 0.10, 6: 0.85}
AHS_DUTY = 0.5


def _junction_zone_ids(ahs_recs: dict) -> set[int]:
    junction: set[int] = set()
    for r in ahs_recs.values():
        junction.update([r["zr"], r["zs"]])
    return junction


def _orifice_coeff(nums: list[float]) -> float:
    if len(nums) > 1:
        return nums[1]
    if nums:
        return nums[0]
    return 0.0


def _elem_lookup(elems: dict, elem_id: int) -> dict:
    return elems.get(elem_id, {"type": "?", "nums": []})


def _accumulate_fan_prescription(
    pre: np.ndarray, idx: dict[int, int], p: dict, e: dict
) -> None:
    q = e["nums"][0] if e["nums"] else 0.0
    if p["n"] in idx:
        pre[idx[p["n"]]] -= q
    if p["m"] in idx:
        pre[idx[p["m"]]] += q


def _collect_prescribed_and_orifices(
    paths: dict, pm: dict, elems: dict, idx: dict[int, int]
) -> tuple[np.ndarray, list[tuple[int, int, float]]]:
    pre = np.zeros(len(idx))
    orifices: list[tuple[int, int, float]] = []
    for pnr, p in paths.items():
        ent = pm.get(pnr)
        if ent and ent["ahs_nr"] > 0:
            continue
        e = _elem_lookup(elems, p["e"])
        if e["type"] == "fan_cvf":
            _accumulate_fan_prescription(pre, idx, p, e)
        else:
            C = _orifice_coeff(e["nums"])
            C *= SIM_SCHED_MULT.get(p["sched"], 1.0)
            orifices.append((p["n"], p["m"], C * p["mult"]))
    return pre, orifices


def _pressure_residual(
    pre: np.ndarray,
    orifices: list[tuple[int, int, float]],
    idx: dict[int, int],
    pressures: np.ndarray,
) -> np.ndarray:
    f = pre.copy()
    for fr, to, C in orifices:
        dp = (pressures[idx[fr]] if fr in idx else 0.0) - (
            pressures[idx[to]] if to in idx else 0.0
        )
        q = C * np.sign(dp) * np.sqrt(abs(dp))
        if fr in idx:
            f[idx[fr]] -= q * RHO
        if to in idx:
            f[idx[to]] += q * RHO
    return f


def _ahs_path_flow(p: dict) -> float:
    return p["fahs"] * AHS_DUTY / RHO * 3600.0


def _fan_path_flow(e: dict) -> float:
    return (e["nums"][0] if e["nums"] else 0.0) / RHO * 3600.0


def _orifice_path_flow(
    p: dict, e: dict, pressure: np.ndarray, idx: dict[int, int],
) -> float:
    coeff = _orifice_coeff(e["nums"])
    C = coeff * p["mult"]
    C *= SIM_SCHED_MULT.get(p["sched"], 1.0)
    dp = (pressure[idx[p["n"]]] if p["n"] in idx else 0.0) - (
        pressure[idx[p["m"]]] if p["m"] in idx else 0.0
    )
    return C * np.sign(dp) * np.sqrt(abs(dp)) * 3600.0


def _path_steady_flow(
    _pnr: int,
    p: dict,
    ent: dict | None,
    elems: dict,
    pressure: np.ndarray,
    idx: dict[int, int],
) -> float:
    e = _elem_lookup(elems, p["e"])
    if ent and ent["ahs_nr"] > 0:
        return _ahs_path_flow(p)
    if e["type"] == "fan_cvf":
        return _fan_path_flow(e)
    return _orifice_path_flow(p, e, pressure, idx)


def contamx_flows(platform):
    """Return dict path_nr -> signed m3/h as ContamX steady-state would report."""
    base = REPO / "data" / "platforms" / platform / "contam"
    pm = {e["path_nr"]: e for e in json.loads((base / "path_map.json").read_text())}
    zones, elems, paths, ahs_recs = parse_prj(base / "platform.prj")

    junction = _junction_zone_ids(ahs_recs)
    idx = {nr: k for k, nr in enumerate(sorted(n for n in zones if n not in junction))}

    pre, orifices = _collect_prescribed_and_orifices(paths, pm, elems, idx)

    def resid(pressures):
        return _pressure_residual(pre, orifices, idx, pressures)

    P = fsolve(resid, np.zeros(len(idx)), full_output=True)[0]
    out = {}
    for pnr, p in paths.items():
        ent = pm.get(pnr)
        out[pnr] = _path_steady_flow(pnr, p, ent, elems, P, idx)
    return out, P, idx, resid(P), zones


def build_engines(platform):
    plat = REPO / "data" / "platforms" / platform
    spatial = json.loads((plat / "spatial_layout.json").read_text())
    airflow = json.loads((plat / "air_flow_paths.json").read_text())
    entries = json.loads((plat / "contam" / "path_map.json").read_text())
    flows, P, idx, res, _ = contamx_flows(platform)
    nat = ContamTransportEngine(spatial, airflow, filter_efficiency=0.50,
                                natural_decay_rate=0.0)
    cx = ContamXTransportEngine(spatial, [], flows, filter_efficiency=0.50,
                                natural_decay_rate=0.0, path_map_entries=entries)
    return nat, cx, P, idx, res


def dose_trace(eng, inject_zone, epochs=24):
    """Time-integrated per-zone concentration (dose proxy) + mass accounting."""
    mass = {z: (1.0 if z == inject_zone else 0.0) for z in eng._real_zone_ids}
    vols = {z: eng.zone_nodes[z].volume_m3 for z in eng._real_zone_ids}
    cum = dict.fromkeys(eng._real_zone_ids, 0.0)
    removed = 0.0
    for _ in range(epochs):
        before = sum(mass.values())
        mass = eng.transport_step(mass, natural_decay_rate=0.0)
        after = sum(mass.values())
        removed += max(0.0, before - after)
        for z in eng._real_zone_ids:
            cum[z] += mass.get(z, 0.0) / vols[z]
    return mass, cum, removed, vols


def compare(platform, inject_zones):
    nat, cx, P, _, res = build_engines(platform)
    print(f"=== {platform} ===")
    print(f"pressure solve: residual max {np.abs(res).max():.2e} kg/s, "
          f"dP range [{P.min():.3g}, {P.max():.3g}] Pa")
    print(f"paths: native {len(nat.airflow_paths)}  contamx {len(cx.airflow_paths)}")
    for zone in inject_zones:
        if zone not in nat.zone_nodes:
            print(f"  (zone {zone} not in layout; skipped)")
            continue
        mn, cn, rn, vols = dose_trace(nat, zone)
        mc, cc, rc, _ = dose_trace(cx, zone)
        print(f"\n  inject {zone} (V={vols[zone]:.0f} m3), 24-epoch trace:")
        print(f"    mass retained after 24h: native {sum(mn.values()):.4f}  "
              f"contamx {sum(mc.values()):.4f}   "
              f"removed: native {rn:.4f} contamx {rc:.4f}")
        dose_ratios = {z: cn[z] / cc[z] for z in cn if cc[z] > 1e-9}
        dr = np.array(list(dose_ratios.values()))
        if len(dr):
            print(f"    integrated-conc ratio native/cx across exposed zones: "
                  f"median {np.median(dr):.3f}  mean {dr.mean():.3f}  "
                  f"min {dr.min():.3f}  max {dr.max():.3f}")
        tot_dose_n = sum(cn.values())
        tot_dose_c = sum(cc.values())
        print(f"    ship-integrated dose proxy: native {tot_dose_n:.4f}  "
              f"contamx {tot_dose_c:.4f}  ratio {tot_dose_n / tot_dose_c:.3f}")
        # biggest per-zone divergences
        both = [(z, cn[z], cc[z]) for z in cn if cn[z] > 1e-6 or cc[z] > 1e-6]
        both.sort(key=lambda t: -abs(t[1] - t[2]))
        print("    largest |dose| divergences (zone, native, cx):")
        for z, a, b in both[:5]:
            print(f"      {z:22s} {a:.4f} {b:.4f}")


if __name__ == "__main__":
    for plat, zones in {
        "expedition_cruise_450": ["MainDining", "PC_D4_P_F", "MainGalley"],
        "classic_cruise_1900": ["MainDining", "GrandLobby"],
        "mega_cruise_5000": ["MainDining", "GrandLobby"],
    }.items():
        try:
            compare(plat, zones)
        except Exception as ex:
            print(f"{plat}: FAILED {type(ex).__name__}: {ex}")
