#!/usr/bin/env python3
"""NORO-FOOD-SCORE-01 scored readout — aggregates food_score_01_scan rows.

Consumes the JSONL rows emitted by ``food_score_01_scan.py`` (one per
voyage, census fields present where the member was scanned) and renders
the frozen criteria of ``docs/norovirus/noro_food_score_01_sweep_design.md``:

- D1 posting frequency: posted share + Wilson 95% CI per cell, paired
  gained/lost vs the in-campaign ``off`` arm, marginal contribution vs
  the declared E ladder;
- D2 posted-conditional pax-AR: quantiles among posted voyages, pooled
  across object arms per hull per the declared pooling rule;
- D3 hull-scaling: excursion→posting conversion and posted ceilings per
  hull per arm (``ind`` re-measures v1 on the current engine);
- D4 outbreak shape: burst48/burst12 excursion-vs-rest medians per hull
  plus the object-window-aligned acquisition share;
- must-not-move: median infection AR (paired Δ vs ``off``), non-cs route
  shares, ``off``-arm zero-witness, object-integrity tallies.

Attribution is distribution-level on identical seed lists per the frozen
design; per-seed pairing is used only for the binary posting outcome.
"""

from __future__ import annotations

import argparse
import json
import statistics as stats
import sys
from collections import Counter, defaultdict

_ARM_ORDER = ("off", "ind", "ol1", "ol2", "ol3", "ship")
_HULL_ORDER = ("exp", "cls", "spr")
_HULL_LABEL = {
    "expedition_cruise_450": "exp",
    "classic_cruise_1900": "cls",
    "spirit_cruise_3000": "spr",
}
_E_LADDER = {"ol1": 0.0015, "ol2": 0.0035, "ol3": 0.0070, "ship": 0.0105}
_ROUTE_ALARM = "common_source_food"


def _arm_of(tier: str) -> str:
    return tier.rsplit("_", 1)[-1]


def _wilson(k: int, n: int) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    z = 1.959964
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return centre - half, centre + half


def _quant(xs: list[float], q: float) -> float | None:
    if not xs:
        return None
    xs = sorted(xs)
    i = q * (len(xs) - 1)
    lo = int(i)
    if lo + 1 >= len(xs):
        return xs[lo]
    return xs[lo] + (xs[lo + 1] - xs[lo]) * (i - lo)


def _iqr_med(xs: list[float]) -> str:
    if not xs:
        return "-"
    q1, med, q3 = _quant(xs, 0.25), _quant(xs, 0.5), _quant(xs, 0.75)
    return f"{med:.3f} [{q1:.3f},{q3:.3f}]"


def load_rows(paths: list[str]) -> dict[str, dict[str, list[dict]]]:
    cells: dict[str, dict[str, list[dict]]] = defaultdict(
        lambda: defaultdict(list)
    )
    seen: dict[str, dict] = {}
    for path in paths:
        with open(path, encoding="utf-8") as fh:  # NOSONAR -- operator-specified row files in a local diagnostic tool
            for line in fh:
                row = json.loads(line)
                if row.get("error"):
                    continue
                # resume races can re-emit a key; prefer the census row
                prev = seen.get(row["key"])
                if (
                    prev is not None
                    and prev.get("census")
                    and not row.get("census")
                ):
                    continue
                seen[row["key"]] = row
    for row in seen.values():
        hull = _HULL_LABEL.get(row.get("hull", ""), row.get("hull"))
        arm = _arm_of(row["key"].split("/")[-2])
        cells[hull][arm].append(row)
    return cells


def _posting_table(cells: dict) -> list[str]:
    lines = [
        "| hull | arm | n | posted | Wilson 95% | gained/lost vs off |"
        " marginal pp |",
        "|---|---|---|---|---|---|---|",
    ]
    for hull in _HULL_ORDER:
        arms = cells.get(hull, {})
        off_by_seed = {r["seed"]: r["posted"] for r in arms.get("off", [])}
        for arm in _ARM_ORDER:
            rows = arms.get(arm, [])
            if not rows:
                continue
            n = len(rows)
            k = sum(1 for r in rows if r["posted"])
            lo, hi = _wilson(k, n)
            gained = sum(
                1
                for r in rows
                if r["posted"] and not off_by_seed.get(r["seed"], False)
            )
            lost = sum(
                1
                for r in rows
                if not r["posted"] and off_by_seed.get(r["seed"], False)
            )
            k_off = sum(1 for r in arms.get("off", []) if r["posted"])
            marginal = 100.0 * (k - k_off) / n
            lines.append(
                f"| {hull} | {arm} | {n} | {k} ({100*k/n:.2f}%)"
                f" | [{100*lo:.2f},{100*hi:.2f}] | {gained}/{lost}"
                f" | {marginal:+.2f} |"
            )
    return lines


def _ar_tables(cells: dict) -> list[str]:
    lines = [
        "| hull | arm | n_posted | posted pax-AR med [IQR] | p90 |",
        "|---|---|---|---|---|",
    ]
    for hull in _HULL_ORDER:
        arms = cells.get(hull, {})
        pooled: list[float] = []
        for arm in _ARM_ORDER:
            if arm in ("off",):
                continue
            rows = arms.get(arm, [])
            ars = [r["rep_pax_ar"] for r in rows if r["posted"]]
            if arm != "ind":
                pooled += ars
            if len(ars) >= 1:
                lines.append(
                    f"| {hull} | {arm} | {len(ars)} | {_iqr_med(ars)}"
                    f" | {(_quant(ars, 0.9) or 0):.3f} |"
                )
        lines.append(
            f"| {hull} | obj pooled | {len(pooled)} | {_iqr_med(pooled)}"
            f" | {(_quant(pooled, 0.9) or 0):.3f} |"
        )
    return lines


def _conversion_table(cells: dict) -> list[str]:
    lines = [
        "| hull | arm | exc voy (cs_food>0) | posted | conv % | obj voy"
        " (census n) | posted | conv % | ceiling posted % |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for hull in _HULL_ORDER:
        arms = cells.get(hull, {})
        for arm in _ARM_ORDER:
            if arm == "off":
                continue
            rows = arms.get(arm, [])
            if not rows:
                continue
            # excursion voyage = >=1 infection dominant-routed
            # common_source_food (FOOD-01/02 "cs voy"); the summary's
            # common_source_events is a per-delivery counter and is
            # near-universal on big hulls — not the excursion marker.
            exc = [
                r for r in rows
                if (r.get("routes") or {}).get("common_source_food", 0) > 0
            ]
            exc_post = sum(1 for r in exc if r["posted"])
            crows = [
                r for r in rows
                if r.get("census") and not r["census"].get("head_only")
            ]
            obj = [r for r in crows if r["census"].get("n_objects", 0) > 0]
            obj_post = sum(1 for r in obj if r["posted"])
            n = len(rows)
            k = sum(1 for r in rows if r["posted"])
            conv_e = 100.0 * exc_post / len(exc) if exc else 0.0
            conv_o = 100.0 * obj_post / len(obj) if obj else 0.0
            lines.append(
                f"| {hull} | {arm} | {len(exc)} | {exc_post} | {conv_e:.1f}"
                f" | {len(obj)}/{len(crows)} | {obj_post} | {conv_o:.1f}"
                f" | {100.0*k/n:.2f} |"
            )
    return lines


def _must_not_move(cells: dict) -> list[str]:
    lines = [
        "| hull | arm | med inf-AR pax | paired med Δ vs off | cs share %"
        " | top non-cs route share shift pp |",
        "|---|---|---|---|---|---|",
    ]
    for hull in _HULL_ORDER:
        arms = cells.get(hull, {})
        off = arms.get("off", [])
        off_by_seed = {r["seed"]: r["inf_ar_pax"] for r in off}
        off_routes = Counter()
        off_total = 0
        for r in off:
            off_routes.update(r["routes"])
            off_total += sum(r["routes"].values())
        for arm in _ARM_ORDER:
            rows = arms.get(arm, [])
            if not rows:
                continue
            med = stats.median(r["inf_ar_pax"] for r in rows)
            deltas = [
                r["inf_ar_pax"] - off_by_seed[r["seed"]]
                for r in rows
                if r["seed"] in off_by_seed
            ]
            d_med = stats.median(deltas) if deltas else 0.0
            route_counts = Counter()
            total = 0
            for r in rows:
                route_counts.update(r["routes"])
                total += sum(r["routes"].values())
            cs_share = (
                100.0 * route_counts.get(_ROUTE_ALARM, 0) / total
                if total
                else 0.0
            )
            worst = 0.0
            worst_route = "-"
            for route in set(route_counts) | set(off_routes):
                if route == _ROUTE_ALARM:
                    continue
                shift = (
                    route_counts.get(route, 0) / total
                    - (off_routes.get(route, 0) / off_total if off_total else 0)
                ) * 100
                if abs(shift) > abs(worst):
                    worst = shift
                    worst_route = route
            lines.append(
                f"| {hull} | {arm} | {med:.4f} | {d_med:+.4f}"
                f" | {cs_share:.2f} | {worst:+.2f} ({worst_route}) |"
            )
    return lines


def _burst_tables(cells: dict) -> list[str]:
    lines = [
        "| hull | set | n | burst48 med | burst12 med |",
        "|---|---|---|---|---|",
    ]
    for hull in _HULL_ORDER:
        exc_b48, exc_b12, rest_b48, rest_b12 = [], [], [], []
        for arm in ("ol1", "ol2", "ol3", "ship"):
            for r in cells.get(hull, {}).get(arm, []):
                c = r.get("census") or {}
                if c.get("n_acq", 0) < 10:
                    continue
                if r["routes"].get(_ROUTE_ALARM, 0) > 0:
                    exc_b48.append(c["burst48"])
                    exc_b12.append(c["burst12"])
                else:
                    rest_b48.append(c["burst48"])
                    rest_b12.append(c["burst12"])
        med = stats.median
        lines.append(
            f"| {hull} | excursion | {len(exc_b48)}"
            f" | {med(exc_b48):.3f} | {med(exc_b12):.3f} |"
            if exc_b48
            else f"| {hull} | excursion | 0 | - | - |"
        )
        lines.append(
            f"| {hull} | rest | {len(rest_b48)}"
            f" | {med(rest_b48):.3f} | {med(rest_b12):.3f} |"
            if rest_b48
            else f"| {hull} | rest | 0 | - | - |"
        )
    return lines


def _witness_table(cells: dict) -> list[str]:
    lines = [
        "| hull | arm | voy | w/ev % | ev/voy med | lot voy | obj/voy"
        " | pans/obj | win/obj | zero-dose % | arm L/H/D % | takers/ev |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for hull in _HULL_ORDER:
        arms = cells.get(hull, {})
        for arm in _ARM_ORDER:
            rows = [
                r for r in arms.get(arm, [])
                if r.get("census") and not r["census"].get("head_only")
            ]
            if not rows:
                continue
            n = len(rows)
            ev_rows = [r for r in rows if r["census"]["n_events"] > 0]
            lot = sum(1 for r in rows if r["census"]["lot_obj_voyage"])
            n_obj = sum(r["census"]["n_objects"] for r in rows)
            pans = sum(r["census"]["obj_pans_sum"] for r in rows)
            wins = sum(r["census"]["obj_windows_sum"] for r in rows)
            n_ev = sum(r["census"]["n_events"] for r in rows)
            zd = sum(r["census"]["zero_dose_events"] for r in rows)
            tk = sum(r["census"]["takers_sum"] for r in rows)
            armc = Counter()
            for r in rows:
                armc.update(r["census"]["arms"])
            tot = sum(armc.values())
            mix = "/".join(
                f"{100.0*armc.get(k, 0)/tot:.0f}" if tot else "-"
                for k in ("provisioned_lot", "ill_handler", "ill_diner")
            )
            evs = [r["census"]["n_events"] for r in rows]
            objs = [r["census"]["n_objects"] for r in rows]
            obj_voy = sum(1 for o in objs if o > 0)
            base = (
                f"| {hull} | {arm} | {n} | {100.0*len(ev_rows)/n:.1f}"
                f" | {stats.median(evs):g} | {lot} | {obj_voy}"
            )
            if n_obj:
                base += (
                    f" | {pans/n_obj:.1f} | {wins/n_obj:.1f}"
                )
            else:
                base += " | - | -"
            if n_ev:
                base += (
                    f" | {100.0*zd/n_ev:.1f} | {mix} | {tk/n_ev:.1f} |"
                )
            else:
                base += " | - | - | - |"
            lines.append(base)
    return lines


def _integrity_table(cells: dict) -> list[str]:
    lines = [
        "| hull | arm | voy scanned | ev rows | unresolved oid | missing"
        " oid | missing serial | open obj | srv>lot | non-noro |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    tot = Counter()
    for hull in _HULL_ORDER:
        for arm in _ARM_ORDER:
            rows = [
                r for r in cells.get(hull, {}).get(arm, [])
                if r.get("census") and not r["census"].get("head_only")
            ]
            if not rows:
                continue
            agg = Counter()
            for r in rows:
                agg.update(r["census"]["integrity"])
            for k, v in agg.items():
                tot[k] += int(v)
            lines.append(
                f"| {hull} | {arm} | {len(rows)} | {agg['ev_rows']}"
                f" | {agg['ev_unresolved_oid']} | {agg['ev_missing_oid']}"
                f" | {agg['ev_missing_serial']} | {agg['obj_open']}"
                f" | {agg['lot_srv_exceeds']} | {agg['non_noro_objects']} |"
            )
    lines.append(
        f"| **all** |  |  | {tot['ev_rows']} | {tot['ev_unresolved_oid']}"
        f" | {tot['ev_missing_oid']} | {tot['ev_missing_serial']}"
        f" | {tot['obj_open']} | {tot['lot_srv_exceeds']}"
        f" | {tot['non_noro_objects']} |"
    )
    return lines


def _aligned_share(cells: dict) -> list[str]:
    lines = ["| hull | cs acq | in object span | share % |", "|---|---|---|---|"]
    for hull in _HULL_ORDER:
        n_cs = 0
        n_in = 0
        for arm in ("ol1", "ol2", "ol3", "ship"):
            for r in cells.get(hull, {}).get(arm, []):
                c = r.get("census") or {}
                if c.get("head_only"):
                    continue  # no object spans in head mode
                n_cs += int(c.get("cs_acq_n", 0))
                n_in += int(c.get("cs_acq_in_span", 0))
        share = 100.0 * n_in / n_cs if n_cs else 0.0
        lines.append(f"| {hull} | {n_cs} | {n_in} | {share:.1f} |")
    return lines


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rows", nargs="+", help="JSONL scan outputs")
    args = ap.parse_args()
    cells = load_rows(args.rows)
    out: list[str] = []
    for name, fn in (
        ("D1 posting", _posting_table),
        ("D2 posted-conditional pax-AR", _ar_tables),
        ("D3 conversion/ceilings", _conversion_table),
        ("D4 bursts", _burst_tables),
        ("D4 window-aligned share", _aligned_share),
        ("Witness", _witness_table),
        ("Must-not-move", _must_not_move),
        ("Integrity", _integrity_table),
    ):
        out += [f"\n## {name}\n"] + fn(cells)
    print("\n".join(out))
    n_rows = sum(
        len(rows)
        for hull in cells.values()
        for rows in hull.values()
    )
    print(f"\nrows: {n_rows}", file=sys.stderr)


if __name__ == "__main__":
    main()
