#!/usr/bin/env python3
"""Fold the flu_present_ab cells: confined SAR vs CABIN-FLOOR-03 band + F1,
plus the presentation/observation surface PRESENT-SHARE-01 moves."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "telemetry_buffer" / "flu_present_ab"

K_LO, K_HI, K_SHIP = 2e-4, 1e-3, 6e-4
F1 = (0.03, 0.38)
SUMMARY_OUT = RUNS / "scored_summary.json"


def _wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - m) / d, (c + m) / d)


def _e_sar(doses: list[float], k: float) -> float:
    return (
        sum(1 - math.exp(-k * d) for d in doses) / len(doses)
        if doses else float("nan")
    )


def _load_cells() -> dict[tuple[str, int], dict]:
    cells: dict[tuple[str, int], dict] = {}
    for path in sorted(RUNS.glob("classic_cruise_1900_s*.json")):
        parts = path.stem.split("_")
        seed = int(parts[3].lstrip("s"))
        mode = "_".join(parts[4:])
        cells[(mode, seed)] = json.loads(path.read_text())
    return cells


def _accumulate_mode(
    cells: dict[tuple[str, int], dict], mode: str
) -> tuple[dict, list[float]]:
    slots = sec = ill = inf = rep = 0
    doses: list[float] = []
    for (m, _seed), s in sorted(cells.items()):
        if m != mode:
            continue
        confined = s["rhythm"]["confined"]
        slots += int(confined["confined_slots"])
        sec += int(confined["confined_secondaries"])
        for row in confined.get("slot_rows") or []:
            doses.append(float(row.get("delivered_p_dose") or 0.0))
        summ = s.get("summary") or {}
        ill += int(summ.get("cumulative_ever_ill_passenger") or 0)
        inf += int(summ.get("cumulative_ever_infected_passenger") or 0)
        rep += int(summ.get("cumulative_reported_cases_passenger") or 0)
    lo, hi = _wilson(sec, slots)
    stats = {
        "confined_slots": slots,
        "confined_secondaries": sec,
        "confined_sar": sec / slots if slots else None,
        "wilson_95": [lo, hi],
        "band_e_sar": [_e_sar(doses, K_LO), _e_sar(doses, K_HI)],
        "e_sar_k_ship": _e_sar(doses, K_SHIP),
        "f1_overlap": bool(lo < F1[1] and hi > F1[0]),
        "dosed_rows": len(doses),
        "ever_ill_pax": ill,
        "ever_infected_pax": inf,
        "reported_pax": rep,
    }
    return stats, doses


def _print_mode(mode: str, stats: dict, doses: list[float]) -> None:
    slots = stats["confined_slots"]
    sec = stats["confined_secondaries"]
    lo, hi = stats["wilson_95"]
    band = stats["band_e_sar"]
    print(f"=== {mode} ===")
    print(
        f"confined SAR {sec}/{slots} = {sec/slots*100:.1f}% "
        f"Wilson [{lo*100:.1f}, {hi*100:.1f}]"
    )
    print(
        f"band [E(k_lo),E(k_hi)] = [{band[0]*100:.1f}%, {band[1]*100:.1f}%]; "
        f"E[SAR]@k=6e-4 = {stats['e_sar_k_ship']*100:.1f}%; "
        f"F1 [{F1[0]*100:.0f},{F1[1]*100:.0f}] "
        f"{'IN' if stats['f1_overlap'] else 'OUT'}"
    )
    if slots:
        median = sorted(doses)[len(doses) // 2] if doses else 0
        print(
            f"dose p50 = {median:.2f} copies over {len(doses)} dosed rows "
            f"({len(doses)/slots:.0%} of slots)"
        )
    inf = stats["ever_infected_pax"]
    if not inf:
        print("no pax infections")
        print()
        return
    print(
        f"ever_ill/ever_infected pax = {stats['ever_ill_pax']}/{inf} "
        f"({stats['ever_ill_pax']/inf:.2f})"
    )
    print(
        f"reported/infected pax = {stats['reported_pax']}/{inf} "
        f"({stats['reported_pax']/inf:.2f}) (F5 ~0.08)"
    )
    print()


def _paired_deltas(cells: dict[tuple[str, int], dict], out: dict) -> None:
    for (m, seed), s in sorted(cells.items()):
        if m != "once_per_course":
            continue
        other = cells.get(("daily_hazard", seed))
        if not other:
            continue
        a = s["rhythm"]["confined"]
        b = other["rhythm"]["confined"]
        sa = a["confined_secondaries"] / max(a["confined_slots"], 1)
        sb = b["confined_secondaries"] / max(b["confined_slots"], 1)
        out["paired"][f"s{seed}"] = {
            "once_per_course": [a["confined_secondaries"], a["confined_slots"]],
            "daily_hazard": [b["confined_secondaries"], b["confined_slots"]],
        }
        print(
            f"s{seed}: once {a['confined_secondaries']}/{a['confined_slots']}"
            f"={sa*100:.1f}% vs daily {b['confined_secondaries']}/"
            f"{b['confined_slots']}={sb*100:.1f}%  d={(sa-sb)*100:+.1f}pp"
        )


def main() -> int:
    out: dict = {"modes": {}, "paired": {}}
    cells = _load_cells()
    for mode in ("once_per_course", "daily_hazard"):
        stats, doses = _accumulate_mode(cells, mode)
        out["modes"][mode] = stats
        _print_mode(mode, stats, doses)
    print("=== paired deltas ===")
    _paired_deltas(cells, out)
    SUMMARY_OUT.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
