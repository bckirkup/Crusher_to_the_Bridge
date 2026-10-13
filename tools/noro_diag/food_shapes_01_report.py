#!/usr/bin/env python3
"""NORO-FOOD-SHAPES-01 scored readout — aggregates food_shapes_01_scan rows.

Consumes the JSONL rows emitted by ``food_shapes_01_scan.py`` (one per
voyage) and renders the frozen criteria of
``docs/norovirus/noro_food_shapes_01_sweep_design.md``:

- D1 posting frequency: posted share + Wilson 95% CI per arm, paired
  gained/lost vs the in-campaign ``off`` floor, marginal pp vs the
  0.4-0.9% reference band;
- D2 posted-conditional pax-AR pooled medians per arm (the pooled
  rule — thin cells pool within an arm, not per-voyage votes);
- D3 excursion->posting conversion (excursion = >=1 infection
  dominant-routed common_source_food) vs the in-campaign ``ind`` read;
- D4 burst48 excursion-vs-rest medians + posted-voyage burst48;
- mint census: provisioned_lot objects/cells per arm, windows covered,
  titre draws vs the implicated band, per-window re-mint variance,
  realized channel-presence fraction vs the drawn gate;
- extent bookkeeping on ``declared`` arms: extent_windows draws,
  per-window serving-cap violations, ``extent_met`` placement;
- must-not-move: ``off`` zero-witness, ``ind``/``ind_bg`` zero
  ``object_id`` rows, median inf-AR paired-seed vs ``off``, non-cs
  route-share drift;
- margin diffs: paired-seed posting gained/lost for the frozen margin
  pairs (ship-bg, ship-redraw, ship-fx_wide, ship-fx_narrow, ship-mint,
  bg-bg_mint, redraw-redraw_mint, ind-ind_bg, mint-redraw_mint,
  mint-bg_mint, bg-bg_mint on conversion, redraw_mint vs ind).

Attribution is distribution-level on identical seed lists per the
frozen design; per-seed pairing is used for the binary posting outcome.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from food_score_01_report import _quant, _wilson  # noqa: E402

_ARM_ORDER = (
    "off", "ind", "ind_bg", "ship", "bg", "mint", "bg_mint",
    "redraw", "redraw_mint", "fx_wide", "fx_narrow",
)
_TIER_PREFIX = "fl_exp_12d_scr_"
_IMPLICATED_BAND = (150.0, 5000.0)
_OBJECT_ARMS = (
    "ship", "bg", "mint", "bg_mint", "redraw", "redraw_mint",
    "fx_wide", "fx_narrow",
)
_MINT_ARMS = ("mint", "bg_mint", "redraw_mint")
_MARGIN_PAIRS = (
    ("ship", "bg"), ("ship", "redraw"), ("ship", "fx_wide"),
    ("ship", "fx_narrow"), ("ship", "mint"), ("bg", "bg_mint"),
    ("redraw", "redraw_mint"), ("ind", "ind_bg"),
    ("mint", "bg_mint"), ("mint", "redraw_mint"),
)
_POST_BAND = (0.004, 0.009)


def _arm_of(tier: str) -> str:
    return tier.split("scr_", 1)[-1] if "scr_" in tier else tier




_SEP3 = "|---|---|---|"
_SEP5 = "|---|---|---|---|---|"
_SEP6 = "|---|---|---|---|---|---|"
_SEP7 = "|---|---|---|---|---|---|---|"
_SEP8 = "|---|---|---|---|---|---|---|---|"
_SEP9 = "|---|---|---|---|---|---|---|---|---|"
_SEP10 = "|---|---|---|---|---|---|---|---|---|---|"


def _iqr_med(xs: list[float]) -> str:
    if not xs:
        return "-"
    q1, med, q3 = _quant(xs, 0.25), _quant(xs, 0.5), _quant(xs, 0.75)
    return f"{med:.4f} [{q1:.4f},{q3:.4f}]"


def _pct(k: int, n: int) -> str:
    return f"{100.0 * k / n:.2f}%" if n else "-"


def _cen(row: dict) -> dict:
    return row.get("census") or {}


def _ok(rows: list[dict]) -> list[dict]:
    return [
        r for r in rows
        if r.get("census") and not r["census"].get("error")
    ]


def _excursion(row: dict) -> bool:
    return (row.get("routes") or {}).get("common_source_food", 0) > 0


def load_rows(paths: list[str]) -> dict[str, list[dict]]:
    cells: dict[str, list[dict]] = defaultdict(list)
    seen: dict[str, dict] = {}
    for path in paths:
        with open(path, encoding="utf-8") as fh:  # NOSONAR -- operator-specified row files in a local diagnostic tool
            for line in fh:
                row = json.loads(line)
                if row.get("error"):
                    continue
                # resume races can re-emit a key; prefer the census row
                if seen.get(row["key"], {}).get("census") and not row.get(
                    "census"
                ):
                    continue
                seen[row["key"]] = row
    for row in seen.values():
        arm = _arm_of(row["key"].split("/")[-2])
        cells[arm].append(row)
    return cells


def _coverage(cells: dict[str, list[dict]]) -> list[str]:
    lines = [
        "| arm | rows | censused | posted | posted rate | errors |",
        _SEP6,
    ]
    for arm in _ARM_ORDER:
        rows = cells.get(arm, [])
        cen = _ok(rows)
        k = sum(1 for r in rows if r["posted"])
        err = len(rows) - len(cen)
        lines.append(
            f"| {arm} | {len(rows)} | {len(cen)} | {k}"
            f" | {_pct(k, len(rows))} | {err} |"
        )
    return lines


def _posting_table(cells: dict) -> list[str]:
    lines = [
        "| arm | n | posted | Wilson 95% | paired gained/lost vs off"
        " | marginal pp | in 0.4-0.9% band |",
        _SEP7,
    ]
    off_by_seed = {r["seed"]: r["posted"] for r in cells.get("off", [])}
    off_posted = sum(1 for b in off_by_seed.values() if b)
    for arm in _ARM_ORDER:
        rows = cells.get(arm, [])
        if not rows:
            continue
        lines.append(_posting_row(arm, rows, off_by_seed, off_posted))
    return lines


def _posting_row(
    arm: str, rows: list[dict], off_by_seed: dict, off_posted: int
) -> str:
    n = len(rows)
    k = sum(1 for r in rows if r["posted"])
    lo, hi = _wilson(k, n)
    gained = lost = 0
    for r in rows:
        base = off_by_seed.get(r["seed"])
        if base is None:
            continue
        if r["posted"] and not base:
            gained += 1
        elif base and not r["posted"]:
            lost += 1
    marg = 100.0 * (k - off_posted) / n
    in_band = ""
    if arm not in ("off",):
        in_band = (
            "yes"
            if _POST_BAND[0] * 100 <= marg <= _POST_BAND[1] * 100
            else "no"
        )
    return (
        f"| {arm} | {n} | {k} ({_pct(k, n)})"
        f" | [{100*lo:.2f}%,{100*hi:.2f}%]"
        f" | +{gained}/-{lost} | {marg:+.2f} | {in_band} |"
    )


def _ar_table(cells: dict) -> list[str]:
    lines = [
        "| arm | n_posted | posted pax-AR med [IQR] | p90"
        " | >=0.04 edge |",
        _SEP5,
    ]
    pooled: list[float] = []
    for arm in _ARM_ORDER:
        if arm == "off":
            continue
        ars = [r["rep_pax_ar"] for r in cells.get(arm, []) if r["posted"]]
        if arm in _OBJECT_ARMS:
            pooled += ars
        if ars:
            med = _quant(ars, 0.5)
            lines.append(
                f"| {arm} | {len(ars)} | {_iqr_med(ars)}"
                f" | {_quant(ars, 0.9):.4f}"
                f" | {'yes' if med and med >= 0.04 else 'no'} |"
            )
        else:
            lines.append(f"| {arm} | 0 | - | - | - |")
    lines.append(
        f"| obj pooled | {len(pooled)} | {_iqr_med(pooled)}"
        f" | {_quant(pooled, 0.9):.4f}"
        f" | {'yes' if (_quant(pooled, 0.5) or 0) >= 0.04 else 'no'} |"
    )
    return lines


def _conversion_table(cells: dict) -> list[str]:
    lines = [
        "| arm | exc voy (cs_food>0) | posted | conv % | vs ind"
        " | obj voy | posted | conv % |",
        _SEP8,
    ]
    ind_exc = [_excursion(r) for r in cells.get("ind", [])]
    ind_post_exc = sum(
        1 for r in cells.get("ind", [])
        if _excursion(r) and r["posted"]
    )
    ind_conv = (
        ind_post_exc / sum(1 for b in ind_exc if b) if any(ind_exc) else 0
    )
    for arm in _ARM_ORDER:
        if arm == "off":
            continue
        rows = cells.get(arm, [])
        if not rows:
            continue
        exc = [r for r in rows if _excursion(r)]
        exc_post = sum(1 for r in exc if r["posted"])
        conv = 100.0 * exc_post / len(exc) if exc else 0.0
        obj_rows = [r for r in _ok(rows) if _cen(r).get("n_objects", 0)]
        obj_post = sum(1 for r in obj_rows if r["posted"])
        conv_o = 100.0 * obj_post / len(obj_rows) if obj_rows else 0.0
        ratio = (
            f"{(conv / (ind_conv * 100)):.2f}x" if ind_conv else "-"
        )
        lines.append(
            f"| {arm} | {len(exc)} | {exc_post} | {conv:.2f}"
            f" | {ratio} | {len(obj_rows)} | {obj_post} | {conv_o:.2f} |"
        )
    return lines


def _burst_table(cells: dict) -> list[str]:
    lines = [
        "| arm | exc b48 med [IQR] | rest b48 med [IQR]"
        " | posted b48 med | exc n |",
        _SEP5,
    ]
    for arm in _ARM_ORDER:
        cen = _ok(cells.get(arm, []))
        if not cen:
            continue
        exc = [
            _cen(r).get("burst48") for r in cen
            if _excursion(r) and _cen(r).get("burst48") is not None
        ]
        rest = [
            _cen(r).get("burst48") for r in cen
            if not _excursion(r) and _cen(r).get("burst48") is not None
        ]
        posted = [
            _cen(r).get("burst48") for r in cen
            if r["posted"] and _cen(r).get("burst48") is not None
        ]
        pmed = _quant(posted, 0.5)
        lines.append(
            f"| {arm} | {_iqr_med(exc)} | {_iqr_med(rest)}"
            f" | {f'{pmed:.3f}' if pmed is not None else '-'}"
            f" | {len(exc)} |"
        )
    return lines


def _mint_census(cells: dict) -> list[str]:
    lines = [
        "| arm | cells | lot-obj cells | frac | lot objects"
        " | windows | pans | titre draws | in-band | draw min-max |",
        _SEP10,
    ]
    for arm in _ARM_ORDER:
        cen = _ok(cells.get(arm, []))
        if not cen:
            continue
        lot_cells = sum(
            1 for r in cen if _cen(r).get("lot_obj_voyage")
        )
        objs = [
            o for r in cen for o in _cen(r).get("lot_objects", [])
        ]
        draws = [o["titre"] for o in objs if o.get("titre") is not None]
        pan_n = sum(
            (_cen(r).get("lot_pans") or {}).get("n", 0) for r in cen
        )
        pan_oob = sum(
            (_cen(r).get("lot_pans") or {}).get("oob", 0) for r in cen
        )
        win = sum(int(o.get("w") or 0) for o in objs)
        pans = sum(int(o.get("pans") or 0) for o in objs)
        lo, hi = _IMPLICATED_BAND
        inband = sum(1 for t in draws if lo <= float(t) <= hi)
        rng = (
            f"{min(draws):.1f}-{max(draws):.1f}" if draws else "-"
        )
        lines.append(
            f"| {arm} | {len(cen)} | {lot_cells} | {_pct(lot_cells, len(cen))}"
            f" | {len(objs)} | {win} | {pans}"
            f" | {len(draws)} obj / {pan_n} pan | {inband}/{len(draws)} obj,"
            f" {pan_n - pan_oob}/{pan_n} pan | {rng} |"
        )
    return lines


def _remint_table(cells: dict) -> list[str]:
    lines = [
        "| arm | lot objs w/ pans | multi-window | varying titre"
        " | constant titre |",
        _SEP5,
    ]
    for arm in _ARM_ORDER:
        cen = _ok(cells.get(arm, []))
        rem = [
            e for r in cen for e in _cen(r).get("remint", [])
            if e.get("win", 0)
        ]
        if not rem:
            continue
        multi = [e for e in rem if e["win"] > 1]
        var = [e for e in multi if e["titre_n"] > 1]
        const = [e for e in multi if e["titre_n"] <= 1]
        lines.append(
            f"| {arm} | {len(rem)} | {len(multi)} | {len(var)}"
            f" | {len(const)} |"
        )
    return lines


def _extent_table(cells: dict) -> list[str]:
    lines = [
        "| arm | declared objects | extent_windows draws"
        " | cap violations | extent_met | other closes |",
        _SEP6,
    ]
    for arm in ("fx_wide", "fx_narrow"):
        cen = _ok(cells.get(arm, []))
        ext = [e for r in cen for e in _cen(r).get("extent", [])]
        if not ext:
            lines.append(f"| {arm} | 0 | - | - | - | - |")
            continue
        ews = Counter(e["ext_win"] for e in ext)
        viol = sum(e["cap_viol"] for e in ext)
        met = sum(1 for e in ext if e["extent_met"])
        lines.append(
            f"| {arm} | {len(ext)} | {dict(sorted(ews.items()))}"
            f" | {viol} | {met} | {len(ext) - met} |"
        )
    return lines


def _witness_table(cells: dict) -> list[str]:
    lines = [
        "| arm | objects n | ill_handler | ill_diner | lot"
        " | events n | lot-event voyages | zero-dose ev |",
        _SEP8,
    ]
    for arm in _ARM_ORDER:
        cen = _ok(cells.get(arm, []))
        if not cen:
            continue
        obj_arms = Counter()
        end_r = Counter()
        ev_n = 0
        lot_ev_voy = 0
        zd = 0
        for r in cen:
            c = _cen(r)
            obj_arms.update(c.get("obj_arms") or {})
            end_r.update(c.get("end_reasons") or {})
            ev_n += c.get("n_events", 0)
            zd += c.get("zero_dose_events", 0)
            if c.get("lot_event_voyage"):
                lot_ev_voy += 1
        lines.append(
            f"| {arm} | {sum(obj_arms.values())}"
            f" | {obj_arms.get('ill_handler', 0)}"
            f" | {obj_arms.get('ill_diner', 0)}"
            f" | {obj_arms.get('provisioned_lot', 0)}"
            f" | {ev_n} | {lot_ev_voy} | {zd} |"
        )
    return lines


def _route_totals(rows: list[dict]) -> tuple[Counter, int]:
    counts: Counter = Counter()
    total = 0
    for r in rows:
        counts.update(r.get("routes") or {})
        total += sum((r.get("routes") or {}).values())
    return counts, total


_SHIP_BG_FIELDS = (
    "n_objects", "n_events", "takers_sum", "obj_pans_sum",
    "obj_windows_sum", "n_acq", "cs_acq_n",
)


def _must_not_move(cells: dict) -> list[str]:
    off = cells.get("off", [])
    lines = [_off_witness_line(off)]
    lines += _ind_witness_lines(cells)
    lines += _inf_ar_drift_lines(cells, off)
    lines.append(_route_drift_line(cells, off))
    lines.append(_ship_bg_identity_line(cells))
    return lines


def _off_witness_line(off: list[dict]) -> str:
    off_cen = _ok(off)
    wit = sum(
        _cen(r).get("n_objects", 0) + _cen(r).get("n_events", 0)
        for r in off_cen
    )
    dose = sum(
        float((_cen(r).get("telemetry") or {}).get("dose_credited") or 0)
        for r in off_cen
    )
    return (
        f"- `off` zero-witness: {len(off_cen)} censused cells,"
        f" {wit} object+event rows, dose_credited sum {dose:.6f}"
        f" — {'PASS' if wit == 0 and dose == 0 else 'FAIL'}"
    )


def _ind_witness_lines(cells: dict) -> list[str]:
    lines = []
    for arm in ("ind", "ind_bg"):
        cen = _ok(cells.get(arm, []))
        obj_ev = sum(_cen(r).get("n_obj_events", 0) for r in cen)
        n_obj = sum(_cen(r).get("n_objects", 0) for r in cen)
        lines.append(
            f"- `{arm}` v1-only witness: {obj_ev} object-linked event"
            f" rows, {n_obj} object rows over {len(cen)} cells"
            f" — {'PASS' if obj_ev == 0 and n_obj == 0 else 'FAIL'}"
        )
    return lines


def _inf_ar_drift_lines(cells: dict, off: list[dict]) -> list[str]:
    lines = []
    off_inf = {r["seed"]: r["inf_ar_pax"] for r in off}
    for arm in _ARM_ORDER:
        if arm == "off":
            continue
        rows = cells.get(arm, [])
        deltas = [
            r["inf_ar_pax"] - off_inf[r["seed"]]
            for r in rows if r["seed"] in off_inf
        ]
        if not deltas:
            continue
        med = _quant(deltas, 0.5)
        p90 = _quant([abs(d) for d in deltas], 0.9)
        lines.append(
            f"- `{arm}` median paired Δinf-AR vs off: {med:+.4f}"
            f" (p90 |Δ| {p90:.4f}, n={len(deltas)})"
        )
    return lines


def _route_drift_line(cells: dict, off: list[dict]) -> str:
    base_counts, base_total = _route_totals(off)
    worst_overall = (0.0, "-", "-")
    for arm in _ARM_ORDER:
        if arm == "off":
            continue
        rows = cells.get(arm, [])
        counts, total = _route_totals(rows)
        for route in set(counts) | set(base_counts):
            if route == "common_source_food":
                continue
            shift = (
                (counts.get(route, 0) / total if total else 0)
                - (base_counts.get(route, 0) / base_total if base_total else 0)
            ) * 100
            if abs(shift) > abs(worst_overall[0]):
                worst_overall = (shift, route, arm)
    return (
        f"- worst non-cs route-share drift vs `off` (pooled):"
        f" {worst_overall[0]:+.2f}pp ({worst_overall[1]} on"
        f" `{worst_overall[2]}`)"
    )


def _ship_bg_identity_line(cells: dict) -> str:
    # ship vs bg non-titre-realized field identity (paired seeds)
    bg_by_seed = {r["seed"]: r for r in _ok(cells.get("bg", []))}
    n_pair = n_id = 0
    diffs = Counter()
    for r in _ok(cells.get("ship", [])):
        o = bg_by_seed.get(r["seed"])
        if o is None:
            continue
        n_pair += 1
        same = True
        for f in _SHIP_BG_FIELDS:
            if _cen(r).get(f) != _cen(o).get(f):
                same = False
                diffs[f] += 1
        if (_cen(r).get("obj_arms") or {}) != (_cen(o).get("obj_arms") or {}):
            same = False
            diffs["obj_arms"] += 1
        if (_cen(r).get("end_reasons") or {}) != (_cen(o).get("end_reasons") or {}):
            same = False
            diffs["end_reasons"] += 1
        if same:
            n_id += 1
    return (
        f"- `ship` vs `bg` witness identity (paired seeds): {n_id}/{n_pair}"
        f" identical on object/event counts, takers, pans, windows,"
        f" acquisition counts, obj_arms, end_reasons"
        + (f"; diffs {dict(diffs)}" if diffs else "")
    )


def _margins_table(cells: dict) -> list[str]:
    lines = [
        "| margin pair | paired n | A posted | B posted | gained/lost"
        " | Δposted pp | A exc conv | B exc conv |",
        _SEP8,
    ]
    for a, b in _MARGIN_PAIRS:
        ra = {r["seed"]: r for r in cells.get(a, [])}
        rb = {r["seed"]: r for r in cells.get(b, [])}
        both = sorted(set(ra) & set(rb))
        if not both:
            continue
        ka = sum(1 for s in both if ra[s]["posted"])
        kb = sum(1 for s in both if rb[s]["posted"])
        gained = sum(
            1 for s in both if ra[s]["posted"] and not rb[s]["posted"]
        )
        lost = sum(
            1 for s in both if rb[s]["posted"] and not ra[s]["posted"]
        )
        exca = [s for s in both if _excursion(ra[s])]
        excb = [s for s in both if _excursion(rb[s])]
        conv_a = 100.0 * sum(ra[s]["posted"] for s in exca) / len(exca) if exca else 0
        conv_b = 100.0 * sum(rb[s]["posted"] for s in excb) / len(excb) if excb else 0
        lines.append(
            f"| {a} − {b} | {len(both)} | {ka} | {kb}"
            f" | +{gained}/-{lost} | {100.0 * (ka - kb) / len(both):+.2f}"
            f" | {conv_a:.2f}% (n={len(exca)})"
            f" | {conv_b:.2f}% (n={len(excb)}) |"
        )
    return lines


def _integrity_table(cells: dict) -> list[str]:
    lines = [
        "| arm | ev rows | missing oid | unresolved oid | missing serial"
        " | open objs | srv>lot | non-noro |",
        _SEP8,
    ]
    for arm in _ARM_ORDER:
        tot = Counter()
        for r in _ok(cells.get(arm, [])):
            tot.update(_cen(r).get("integrity") or {})
        if not tot:
            continue
        lines.append(
            f"| {arm} | {tot.get('ev_rows', 0)}"
            f" | {tot.get('ev_missing_oid', 0)}"
            f" | {tot.get('ev_unresolved_oid', 0)}"
            f" | {tot.get('ev_missing_serial', 0)}"
            f" | {tot.get('obj_open', 0)}"
            f" | {tot.get('lot_srv_exceeds', 0)}"
            f" | {tot.get('non_noro_objects', 0)} |"
        )
    return lines


def _echo_table(cells: dict) -> list[str]:
    """Run-parameter override echo vs the arm's frozen override dict."""
    expect = {
        "off": {"mode": "off"},
        "ind": {"lot_mode": "independent", "handler_mode": "independent",
                "diner_mode": "independent"},
        "ind_bg": {"lot_mode": "independent", "handler_mode": "independent",
                   "diner_mode": "independent",
                   "titre_draw_mode": "background"},
        "ship": {"lot_mode": "object", "handler_mode": "object",
                 "diner_mode": "object",
                 "lot_object_probability": [0.001, 0.02]},
        "bg": {"lot_mode": "object", "handler_mode": "object",
               "diner_mode": "object",
               "lot_object_probability": [0.001, 0.02],
               "titre_draw_mode": "background"},
        "mint": {"lot_mode": "object", "handler_mode": "object",
                 "diner_mode": "object",
                 "lot_object_probability": [0.02, 0.15]},
        "bg_mint": {"lot_mode": "object", "handler_mode": "object",
                    "diner_mode": "object",
                    "lot_object_probability": [0.02, 0.15],
                    "titre_draw_mode": "background"},
        "redraw": {"lot_mode": "object", "handler_mode": "object",
                   "diner_mode": "object",
                   "lot_object_probability": [0.001, 0.02],
                   "lot_state_redraw": "per_window"},
        "redraw_mint": {"lot_mode": "object", "handler_mode": "object",
                        "diner_mode": "object",
                        "lot_object_probability": [0.02, 0.15],
                        "lot_state_redraw": "per_window"},
        "fx_wide": {"lot_mode": "object", "handler_mode": "object",
                    "diner_mode": "object",
                    "lot_object_probability": [0.001, 0.02],
                    "lot_extent_mode": "declared",
                    "lot_extent_windows": [12, 24]},
        "fx_narrow": {"lot_mode": "object", "handler_mode": "object",
                      "diner_mode": "object",
                      "lot_object_probability": [0.001, 0.02],
                      "lot_extent_mode": "declared",
                      "lot_extent_windows": [2, 4]},
    }
    lines = ["| arm | echo matches | mismatched |", _SEP3]
    for arm in _ARM_ORDER:
        rows = cells.get(arm, [])
        want = expect.get(arm)
        ok = sum(1 for r in rows if (r.get("cs_echo") or {}) == want)
        lines.append(f"| {arm} | {ok} | {len(rows) - ok} |")
    return lines


def _dose_position_table(paths: list[str] | None) -> list[str]:
    """Per-arm Hill position of delivered doses (entrain_01_dose_audit
    rows): median cumulative dose, Hill p distribution, realized-
    presentation share — posted vs unposted per arm."""
    lines = [
        "| arm | set | acq n | cum med | p med | frac p<0.10"
        " | frac p>0.50 | realized frac |",
        _SEP8,
    ]
    if not paths:
        return lines
    by_arm: dict[str, list[dict]] = defaultdict(list)
    for path in paths:
        with open(path, encoding="utf-8") as fh:  # NOSONAR -- operator-specified row files in a local diagnostic tool
            for line in fh:
                r = json.loads(line)
                if r.get("error"):
                    continue
                for a in r.get("acq") or []:
                    a = dict(a)
                    a["posted"] = r.get("posted")
                    by_arm[r.get("arm") or "?"].append(a)
    for arm in _ARM_ORDER:
        acqs = by_arm.get(arm, [])
        for posted in (False, True):
            sel = [a for a in acqs if a["posted"] == posted]
            if sel:
                lines.append(_dose_line(arm, sel, posted))
    return lines


def _dose_line(arm: str, sel: list[dict], posted: bool) -> str:
    cums = [a["cum"] for a in sel]
    ps = [a["p"] for a in sel]
    prs = [bool(a["pr"]) for a in sel]
    return (
        f"| {arm} | {'posted' if posted else 'unposted'}"
        f" | {len(sel)} | {_quant(cums, 0.5):.1f}"
        f" | {_quant(ps, 0.5):.3f}"
        f" | {sum(1 for p in ps if p < 0.10) / len(ps):.3f}"
        f" | {sum(1 for p in ps if p > 0.50) / len(ps):.3f}"
        f" | {sum(prs) / len(prs):.3f} |"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rows", action="append", required=True,
                    help="JSONL rows file from food_shapes_01_scan.py")
    ap.add_argument("--dose-rows", action="append", default=None,
                    help="entrain_01_dose_audit.py JSONL rows (dose "
                         "position table)")
    args = ap.parse_args()
    cells = load_rows(args.rows)

    print("## coverage\n")
    print("\n".join(_coverage(cells)))
    print("\n## D1 — posting marginal vs in-campaign `off`\n")
    print("\n".join(_posting_table(cells)))
    print("\n## D2 — posted pax-AR pooled medians\n")
    print("\n".join(_ar_table(cells)))
    print("\n## D3 — excursion→posting conversion\n")
    print("\n".join(_conversion_table(cells)))
    print("\n## D4 — burst48 discriminator\n")
    print("\n".join(_burst_table(cells)))
    print("\n## mint census\n")
    print("\n".join(_mint_census(cells)))
    print("\n## re-mint witness (per-window titre variance)\n")
    print("\n".join(_remint_table(cells)))
    print("\n## declared-extent bookkeeping\n")
    print("\n".join(_extent_table(cells)))
    print("\n## witness census\n")
    print("\n".join(_witness_table(cells)))
    print("\n## override echo\n")
    print("\n".join(_echo_table(cells)))
    print("\n## integrity tallies\n")
    print("\n".join(_integrity_table(cells)))
    print("\n## must-not-move\n")
    print("\n".join(_must_not_move(cells)))
    print("\n## margin diffs (paired seeds)\n")
    print("\n".join(_margins_table(cells)))
    print("\n## dose position (delivered-dose Hill)\n")
    print("\n".join(_dose_position_table(args.dose_rows)))


if __name__ == "__main__":
    main()
